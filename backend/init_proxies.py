import redis
import os

WORKER_ID = int(os.getenv("WORKER_ID", 0))
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

def initialize_proxy_queue(r):
    """Initialize the Redis proxy queue (run this once to populate)"""
    possible_paths = ['/proxies/proxies.txt', './proxies.txt', 'proxies.txt']
    
    for path in possible_paths:
        try:
            with open(path, 'r') as f:
                proxies = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            
            if proxies:
                r.delete("proxy_queue")
                r.delete("proxy_failed")
                r.rpush("proxy_queue", *proxies)
                print(f"[INIT] 📋 Loaded {len(proxies)} proxies into queue")
                return True
        except FileNotFoundError:
            continue
        except Exception as e:
            print(f"[INIT] ❌ Error loading proxies from {path}: {e}")
            continue
    
    print("[INIT] ⚠️ No proxy file found")
    return False

def main():
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        r.ping()
    except Exception as e:
        print(f"[INIT] ❌ Could not connect to Redis: {e}")
        return

    initialize_proxy_queue(r)

if __name__ == "__main__":
    main()