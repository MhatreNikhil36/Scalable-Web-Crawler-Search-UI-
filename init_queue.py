#!/usr/bin/env python
import sys, redis, hashlib, os
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
def url_fingerprint(url: str) -> str:
    return hashlib.sha1(url.encode()).hexdigest()
if len(sys.argv) < 2:
    print("Usage: python init_queue.py <root_url>")
    sys.exit(1)
root_url = sys.argv[1].rstrip('/')
fp = url_fingerprint(root_url)
if not r.sismember("visited", fp):
    r.rpush("url_queue", root_url)
    print(f"Seeded frontier with {root_url}")
else:
    print("Root URL already visited or queued.")
