import os, time, hashlib, logging, requests
import redis, sqlalchemy as sa
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from db import engine, init_db

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

init_db()

def url_fingerprint(url: str) -> str:
    return hashlib.sha1(url.encode()).hexdigest()

def save_page(conn, url, title, text):
    conn.execute(sa.text(
        "INSERT INTO pages (url, title, content) VALUES (:u, :t, :c) ON CONFLICT (url) DO NOTHING"
    ), {"u": url, "t": title, "c": text})

def crawl_once():
    item = r.blpop("url_queue", timeout=10)
    if item is None:
        return
    url = item[1]
    fp = url_fingerprint(url)
    if r.sismember("visited", fp):
        return
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "MiniCrawler/0.1"})
        if resp.status_code != 200 or 'text/html' not in resp.headers.get('content-type',''):
            r.sadd("visited", fp)
            return
        soup = BeautifulSoup(resp.text, 'html.parser')
        title = (soup.title.string.strip() if soup.title and soup.title.string else '')[:255]
        text = soup.get_text(" ", strip=True)
        with engine.begin() as conn:
            save_page(conn, url, title, text)

        parsed_root = urlparse(url)
        for a in soup.find_all('a', href=True):
            link = urljoin(url, a['href'])
            p = urlparse(link)
            if p.scheme.startswith('http') and p.netloc == parsed_root.netloc:
                lfp = url_fingerprint(link)
                if not r.sismember("visited", lfp):
                    r.rpush("url_queue", link)
        logging.info(f"Crawled {url}")
    except Exception as e:
        logging.error(f"Error fetching {url}: {e}")
    finally:
        r.sadd("visited", fp)

if __name__ == "__main__":
    while True:
        crawl_once()
