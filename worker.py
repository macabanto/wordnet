import os
import time
import redis
import random
import pymongo
import cloudscraper
from bs4 import BeautifulSoup
import signal
import sys

# === Config ===
WORKER_ID = int(os.getenv("WORKER_ID", 0))
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017")
BASE_URL = "https://www.collinsdictionary.com/dictionary/english-thesaurus/"

# Global variables for cleanup
r = None
mongo = None

def signal_handler(sig, frame):
    """Handle graceful shutdown"""
    print(f"[{WORKER_ID}] Shutting down gracefully...")
    if mongo:
        mongo.close()
    sys.exit(0)

# Setup signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# === Setup clients ===
def setup_connections():
    global r, mongo
    
    # Redis connection
    print(f"[{WORKER_ID}] Connecting to Redis...")
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        r.ping()
        print(f"[{WORKER_ID}] ✅ Connected to Redis")
    except Exception as e:
        print(f"[{WORKER_ID}] ❌ Redis connection failed: {e}")
        sys.exit(1)
    
    # MongoDB connection
    print(f"[{WORKER_ID}] Connecting to MongoDB...")
    try:
        mongo = pymongo.MongoClient(MONGO_URI)
        # Test the connection
        mongo.admin.command('ping')
        print(f"[{WORKER_ID}] ✅ Connected to MongoDB")
    except Exception as e:
        print(f"[{WORKER_ID}] ❌ MongoDB connection failed: {e}")
        sys.exit(1)
    
    return mongo["lemmas"]["entries"]

# === Helpers ===
def fetch_html_with_backoff(word, max_retries=3):
    """Fetch HTML with exponential backoff on failures"""
    url = BASE_URL + word
    scraper = cloudscraper.create_scraper()
    
    for attempt in range(max_retries):
        try:
            response = scraper.get(url, timeout=10)
            if response.status_code == 200:
                return BeautifulSoup(response.text, "html.parser")
            elif response.status_code == 429:  # Rate limited
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                print(f"[{WORKER_ID}] ⏳ Rate limited, waiting {wait_time:.1f}s")
                time.sleep(wait_time)
                continue
            else:
                print(f"[{WORKER_ID}] ❌ HTTP {response.status_code} for {url}")
                return None
        except Exception as e:
            wait_time = (2 ** attempt) + random.uniform(0, 1)
            print(f"[{WORKER_ID}] ❌ Request error for {word} (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                print(f"[{WORKER_ID}] ⏳ Retrying in {wait_time:.1f}s")
                time.sleep(wait_time)
            else:
                return None
    
    return None



def parse_lemma(word, soup):
    """Parse lemma data from the soup"""
    lemma_list = []
    british_div = soup.select_one('div.blockThes-british')
    if not british_div:
        return []

    for sense in british_div.select('div.sense.opened.moreAnt.moreSyn'):
        pos = sense.select_one("span.headerSensePos")
        pos_text = pos.text.strip().replace("(", "").replace(")", "") if pos else "unknown"

        definition = sense.select_one(".def")
        def_text = definition.text.strip() if definition else "no definition"

        # Get all <span class="orth"> within .form.type-syn
        synonym_spans = sense.select("div.form.type-syn span.orth")
        synonyms = [span.text.strip().replace(" ", "-") for span in synonym_spans if span.text.strip()]

        lemma = {
            "term": word,
            "part_of_speech": pos_text,
            "definition": def_text,
            "synonyms": synonyms
        }
        lemma_list.append(lemma)

    return lemma_list

def safe_insert_lemma(collection, lemma):
    """Safely insert lemma with duplicate handling"""
    try:
        # Try to insert the document
        result = collection.insert_one(lemma)
        print(f"[{WORKER_ID}] ✅ Inserted {lemma['term']} ({lemma['definition'][:30]}...)")
        return True
    except pymongo.errors.DuplicateKeyError:
        print(f"[{WORKER_ID}] ⚠️ Duplicate found for {lemma['term']} (shouldn't happen with auto _id)")
        return False
    except Exception as e:
        print(f"[{WORKER_ID}] ❌ Mongo insert error for {lemma['term']}: {e}")
        return False

# === Main Loop ===
def main():
    """Main processing loop"""
    collection = setup_connections()
    consecutive_empty = 0
    max_empty_before_longer_sleep = 5
    
    print(f"[{WORKER_ID}] 🚀 Starting main processing loop")
    
    while True:
        try:
            word = r.lpop("word_queue")
            if not word:
                consecutive_empty += 1
                if consecutive_empty >= max_empty_before_longer_sleep:
                    print(f"[{WORKER_ID}] 💤 Queue empty for {consecutive_empty} attempts, sleeping longer")
                    time.sleep(10)
                else:
                    print(f"[{WORKER_ID}] 💤 Queue empty")
                    time.sleep(2)
                continue
            
            # Reset empty counter when we get work
            consecutive_empty = 0
            
            print(f"[{WORKER_ID}] 🔍 Processing '{word}'")
            soup = fetch_html_with_backoff(word)
            if not soup:
                continue

            lemmas = parse_lemma(word, soup)
            if not lemmas:
                print(f"[{WORKER_ID}] ⚠️ No lemmas found for {word}")
                continue

            # Process lemmas in batch
            success_count = 0
            for lemma in lemmas:
                if safe_insert_lemma(collection, lemma):
                    success_count += 1
            
            print(f"[{WORKER_ID}] 📊 Processed {word}: {success_count}/{len(lemmas)} lemmas saved")
            
            # Adaptive sleep based on success rate
            base_sleep = 0.5
            if success_count == len(lemmas):
                time.sleep(base_sleep)
            else:
                # Sleep longer if we had issues
                time.sleep(base_sleep * 2)
                
        except KeyboardInterrupt:
            signal_handler(signal.SIGINT, None)
        except Exception as e:
            print(f"[{WORKER_ID}] ❌ Unexpected error in main loop: {e}")
            time.sleep(5)  # Sleep before continuing

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)
    finally:
        if mongo:
            mongo.close()