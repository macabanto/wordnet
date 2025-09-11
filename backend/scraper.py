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

# Anti-bot detection improvements
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0"
]

ACCEPT_LANGUAGES = [
    "en-US,en;q=0.9",
    "en-GB,en;q=0.8,fr;q=0.6",
    "en-US,en;q=0.8,es;q=0.6",
    "en-CA,en;q=0.9,fr;q=0.7",
    "en-AU,en;q=0.9"
]

REFERERS = [
    "https://www.google.com/",
    "https://www.bing.com/",
    "https://duckduckgo.com/",
    "https://www.collinsdictionary.com/",
    ""  # Sometimes no referer
]

# Global variables
current_proxy = None
scraper_instance = None
proxy_failure_count = 0
MAX_PROXY_FAILURES = 3  # Max failures before getting a new proxy


def get_working_proxy():
    """Get a working proxy from Redis queue with health tracking"""
    global current_proxy, proxy_failure_count
    
    # If current proxy is still good, keep using it
    if current_proxy and proxy_failure_count < MAX_PROXY_FAILURES:
        return current_proxy
    
    try:
        # Try to get a fresh proxy from the queue
        proxy = r.lpop("proxy_queue")
        
        if not proxy:
            # No proxies available, check if any failed proxies can be recycled
            failed_count = r.llen("proxy_failed")
            if failed_count > 0:
                print(f"[{WORKER_ID}] 🔄 No fresh proxies, recycling {failed_count} failed proxies")
                # Move all failed proxies back to main queue
                while r.llen("proxy_failed") > 0:
                    failed_proxy = r.lpop("proxy_failed")
                    if failed_proxy:
                        r.rpush("proxy_queue", failed_proxy)
                # Try again
                proxy = r.lpop("proxy_queue")
        
        if proxy:
            current_proxy = proxy
            proxy_failure_count = 0
            print(f"[{WORKER_ID}] 🌐 Switched to new proxy: {proxy.split(':')[0]}:***")
            return proxy
        else:
            print(f"[{WORKER_ID}] ⚠️ No proxies available, using direct connection")
            current_proxy = None
            return None
            
    except Exception as e:
        print(f"[{WORKER_ID}] ❌ Error getting proxy from Redis: {e}")
        return None

def mark_proxy_failed():
    """Mark current proxy as failed and move it to failed queue"""
    global current_proxy, proxy_failure_count, scraper_instance
    
    if not current_proxy:
        return
    
    proxy_failure_count += 1
    
    if proxy_failure_count >= MAX_PROXY_FAILURES:
        try:
            # Move proxy to failed queue
            r.rpush("proxy_failed", current_proxy)
            print(f"[{WORKER_ID}] ❌ Proxy {current_proxy.split(':')[0]}:*** marked as failed after {proxy_failure_count} failures")
            
            # Reset current proxy and scraper
            current_proxy = None
            scraper_instance = None
            proxy_failure_count = 0
            
        except Exception as e:
            print(f"[{WORKER_ID}] ❌ Error marking proxy as failed: {e}")

def get_proxy_stats():
    """Get current proxy queue statistics"""
    try:
        available = r.llen("proxy_queue")
        failed = r.llen("proxy_failed")
        return available, failed
    except:
        return 0, 0

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
def get_random_headers():
    """Generate random headers to avoid detection"""
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': random.choice(ACCEPT_LANGUAGES),
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': random.choice(['none', 'cross-site', 'same-origin']),
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
        'Referer': random.choice(REFERERS) if random.random() > 0.3 else None  # 70% chance of referer
    }

def create_proxy_scraper():
    """Create a cloudscraper instance with dynamic proxy configuration"""
    global scraper_instance
    
    # Get a working proxy from Redis queue
    proxy_url = get_working_proxy()
    
    # If we have a scraper and proxy hasn't changed, reuse it
    if scraper_instance is not None and proxy_url == current_proxy:
        return scraper_instance
    
    # Create new scraper instance
    try:
        scraper_instance = cloudscraper.create_scraper()
        
        if not proxy_url:
            print(f"[{WORKER_ID}] 🔄 Using direct connection")
            return scraper_instance
        
        # Parse the proxy URL format: host:port:username:password
        parts = proxy_url.split(":")
        if len(parts) >= 4:
            proxy_host = parts[0]
            proxy_port = parts[1]
            proxy_username = parts[2]
            proxy_password = parts[3]
            
            # Construct proxy URL for requests
            proxy_auth_url = f"http://{proxy_username}:{proxy_password}@{proxy_host}:{proxy_port}"
            
            scraper_instance.proxies = {
                'http': proxy_auth_url,
                'https': proxy_auth_url
            }
            
            print(f"[{WORKER_ID}] 🌐 Using proxy: {proxy_host}:{proxy_port}")
            return scraper_instance
        else:
            print(f"[{WORKER_ID}] ⚠️ Invalid proxy format: {proxy_url}")
            return scraper_instance
            
    except Exception as e:
        print(f"[{WORKER_ID}] ❌ Error setting up proxy scraper: {e}")
        print(f"[{WORKER_ID}] 🔄 Falling back to direct connection")
        scraper_instance = cloudscraper.create_scraper()
        return scraper_instance

def human_like_delay():
    """Add human-like delays between requests"""
    # Base delay with some randomness
    base_delay = random.uniform(1.5, 4.0)
    
    # Occasionally add longer pauses (simulating reading/thinking)
    if random.random() < 0.15:  # 15% chance
        extra_delay = random.uniform(2.0, 8.0)
        print(f"[{WORKER_ID}] 🤔 Taking a longer break ({base_delay + extra_delay:.1f}s)")
        base_delay += extra_delay
    
    time.sleep(base_delay)

def should_randomly_skip_word():
    """Randomly skip some words to simulate human behavior"""
    return random.random() < 0.03  # 3% chance to skip

def fetch_html_with_backoff(word, max_retries=3):
    """Fetch HTML with exponential backoff on failures and anti-detection measures"""
    url_safe_word = word.replace(" ", "-")
    url = BASE_URL + url_safe_word
    scraper = create_proxy_scraper()
    
    for attempt in range(max_retries):
        try:
            # Get random headers for this request
            headers = get_random_headers()
            # Remove None values from headers
            headers = {k: v for k, v in headers.items() if v is not None}
            
            # Update scraper headers
            scraper.headers.update(headers)
            
            response = scraper.get(url, timeout=20)  # Increased timeout for proxy
            if response.status_code == 200:
                return BeautifulSoup(response.text, "html.parser")
            elif response.status_code == 429:  # Rate limited
                # More human-like backoff for rate limiting
                wait_time = random.uniform(10, 30) + (attempt * random.uniform(5, 15))
                print(f"[{WORKER_ID}] ⏳ Rate limited, waiting {wait_time:.1f}s")
                time.sleep(wait_time)
                continue
            elif response.status_code in [407, 502, 503, 504]:  # Proxy-related errors
                print(f"[{WORKER_ID}] 🌐 Proxy error {response.status_code}")
                mark_proxy_failed()  # Mark current proxy as problematic
                wait_time = random.uniform(5, 15)
                print(f"[{WORKER_ID}] 🔄 Getting new proxy, waiting {wait_time:.1f}s")
                time.sleep(wait_time)
                scraper = create_proxy_scraper()  # Get new proxy
                continue
            elif response.status_code == 403:  # Forbidden - possible bot detection
                print(f"[{WORKER_ID}] 🚫 Access forbidden (possible bot detection)")
                mark_proxy_failed()  # This proxy might be burned
                wait_time = random.uniform(20, 60)
                print(f"[{WORKER_ID}] 🔄 Switching proxy, waiting {wait_time:.1f}s")
                time.sleep(wait_time)
                scraper = create_proxy_scraper()  # Get new proxy and session
                continue
            else:
                print(f"[{WORKER_ID}] ❌ HTTP {response.status_code} for {url}")
                return None
        except Exception as e:
            wait_time = random.uniform(3, 10) + (attempt * random.uniform(2, 6))
            print(f"[{WORKER_ID}] ❌ Request error for {word} (attempt {attempt + 1}): {e}")
            
            # If it's a connection error, might be proxy issue
            if "ProxyError" in str(e) or "ConnectionError" in str(e):
                print(f"[{WORKER_ID}] 🌐 Connection issue, marking proxy as failed")
                mark_proxy_failed()
                scraper = create_proxy_scraper()  # Get new proxy
            
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

def get_redis_queue_words():
    """Get all words currently in the Redis queue (non-destructive peek)"""
    try:
        # Get all items in the list without removing them
        queue_words = set(r.lrange("word_queue", 0, -1))
        return queue_words
    except Exception as e:
        print(f"[{WORKER_ID}] ❌ Error reading Redis queue: {e}")
        return set()

def check_word_exists_in_mongo(collection, word):
    """Check if a word already exists in MongoDB"""
    try:
        # Clean the word for consistent checking
        clean_word = word.lower().strip()
        count = collection.count_documents({"term": clean_word}, limit=1)
        return count > 0
    except Exception as e:
        print(f"[{WORKER_ID}] ❌ Error checking MongoDB for '{word}': {e}")
        return True  # Assume it exists to avoid errors

def process_synonyms_for_new_words(collection, synonyms):
    """Process synonyms and add new words to Redis queue"""
    if not synonyms:
        return 0
    
    # Get current queue state
    queue_words = get_redis_queue_words()
    
    new_words_added = 0
    words_to_add = []
    
    for synonym in synonyms:
        # Clean and validate the synonym
        clean_synonym = synonym.lower().strip().replace("-", " ")
        
        # Skip if empty, too short, or contains non-alphabetic characters
        if (not clean_synonym or 
            len(clean_synonym) < 2 or 
            not clean_synonym.replace(" ", "").replace("-", "").isalpha()):
            continue
        
        # Skip if already in queue
        if clean_synonym in queue_words:
            continue
            
        # Skip if already exists in MongoDB
        if check_word_exists_in_mongo(collection, clean_synonym):
            continue
            
        words_to_add.append(clean_synonym)
    
    # Add new words to Redis queue in batch
    if words_to_add:
        try:
            # Use rpush to add to the end of the queue
            r.rpush("word_queue", *words_to_add)
            new_words_added = len(words_to_add)
            print(f"[{WORKER_ID}] 📝 Added {new_words_added} new words to queue: {', '.join(words_to_add[:3])}{'...' if len(words_to_add) > 3 else ''}")
        except Exception as e:
            print(f"[{WORKER_ID}] ❌ Error adding words to Redis queue: {e}")
    
    return new_words_added

# === Main Loop ===
def main():
    """Main processing loop"""
    collection = setup_connections()
    consecutive_empty = 0
    max_empty_before_longer_sleep = 5
    
    
    while True:
        try:
            word = r.lpop("word_queue")
            if not word:
                consecutive_empty += 1
                if consecutive_empty >= max_empty_before_longer_sleep:
                    available, failed = get_proxy_stats()
                    print(f"[{WORKER_ID}] 💤 Queue empty for {consecutive_empty} attempts, sleeping longer (Proxies: {available} available, {failed} failed)")
                    time.sleep(random.uniform(15, 30))  # Randomized longer sleep
                else:
                    print(f"[{WORKER_ID}] 💤 Queue empty")
                    time.sleep(random.uniform(3, 8))  # Randomized short sleep
                continue
            
            # Reset empty counter when we get work
            consecutive_empty = 0
            
            # Randomly skip some words to simulate human behavior
            if should_randomly_skip_word():
                print(f"[{WORKER_ID}] 🤷 Randomly skipping '{word}' (simulating human behavior)")
                continue
            
            print(f"[{WORKER_ID}] 🔍 Processing '{word}'")
            
            # Add human-like delay before each request
            human_like_delay()
            
            soup = fetch_html_with_backoff(word)
            if not soup:
                # Occasionally "give up" on failed words like a human would
                if random.random() < 0.7:  # 70% chance to give up on failed words
                    print(f"[{WORKER_ID}] 😔 Giving up on '{word}' after failures")
                    continue
                else:
                    print(f"[{WORKER_ID}] 🔄 Will retry '{word}' later, adding back to queue")
                    r.rpush("word_queue", word)
                    continue

            lemmas = parse_lemma(word, soup)
            if not lemmas:
                print(f"[{WORKER_ID}] ⚠️ No lemmas found for {word}")
                continue

            # Process lemmas in batch
            success_count = 0
            total_new_words = 0
            
            for lemma in lemmas:
                if safe_insert_lemma(collection, lemma):
                    success_count += 1
                    # Process synonyms for new words to add to queue
                    new_words_count = process_synonyms_for_new_words(collection, lemma['synonyms'])
                    total_new_words += new_words_count
            
            available, failed = get_proxy_stats()
            print(f"[{WORKER_ID}] 📊 Processed {word}: {success_count}/{len(lemmas)} lemmas saved, {total_new_words} new words queued (Proxies: {available}/{failed})")
            
            # Small random delay after processing (simulating reading time)
            time.sleep(random.uniform(0.5, 2.0))
                
        except KeyboardInterrupt:
            signal_handler(signal.SIGINT, None)
        except Exception as e:
            print(f"[{WORKER_ID}] ❌ Unexpected error in main loop: {e}")
            # Longer sleep on unexpected errors
            time.sleep(random.uniform(8, 15))

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)
    finally:
        if mongo:
            mongo.close()