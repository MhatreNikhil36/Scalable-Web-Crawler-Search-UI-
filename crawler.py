import os, json, hashlib, logging, requests
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

def fp(url: str) -> str:
    return hashlib.sha1(url.encode()).hexdigest()

def save_page(conn, url, title, text):
    conn.execute(
        sa.text("INSERT INTO pages (url,title,content) VALUES(:u,:t,:c)"
                "ON CONFLICT (url) DO NOTHING"),
        {"u": url, "t": title, "c": text}
    )

def crawl_once():
    item = r.blpop("url_queue", timeout=10)
    if not item:
        return

    # ── Parse payload (supports old plain-string format) ───────────────────────
    try:
        data = json.loads(item[1])
        url, depth, root, max_depth = (data[k] for k in ("url","depth","root","max_depth"))
    except Exception:
        url, depth, root, max_depth = item[1], 0, item[1], 1_000_000

    # ── Skip if root disabled ─────────────────────────────────────────────────
    if r.sismember("disabled_roots", root):
        return

    # ── Duplicate check ───────────────────────────────────────────────────────
    if r.sismember("visited", fp(url)):
        return

    try:
        resp = requests.get(url, timeout=10,
                            headers={"User-Agent": "MiniCrawler/0.2"})
        if resp.status_code != 200 or "text/html" not in resp.headers.get("content-type",""):
            return
        soup  = BeautifulSoup(resp.text, "html.parser")
        title = (soup.title.string.strip() if soup.title and soup.title.string else "")[:255]
        text  = soup.get_text(" ", strip=True)

        with engine.begin() as conn:
            save_page(conn, url, title, text)

        # ── Enqueue children if depth allows ──────────────────────────────────
        if depth < max_depth:
            dom = urlparse(url).netloc
            for tag in soup.find_all("a", href=True):
                link = urljoin(url, tag["href"])
                if urlparse(link).netloc == dom and link.startswith(("http://", "https://")):
                    if not r.sismember("visited", fp(link)):
                        child = dict(url=link, depth=depth+1,
                                     root=root, max_depth=max_depth)
                        r.rpush("url_queue", json.dumps(child))

        logging.info("Crawled %s (depth %s/%s)", url, depth, max_depth)

    except Exception as e:
        logging.error("Error fetching %s: %s", url, e)

    finally:
        r.sadd("visited", fp(url))

if __name__ == "__main__":
    while True:
        crawl_once()
