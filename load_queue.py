# load_queue.py
import redis

r = redis.Redis(
    host='localhost',
    port=6379,
    password='supersecretpassword',  # 👈 add this
    decode_responses=True
)
with open("word_list.txt") as f:
    for line in f:
        word = line.strip()
        if word:
            r.rpush("word_queue", word)
            print(r.lrange("word_queue", 0, -1))