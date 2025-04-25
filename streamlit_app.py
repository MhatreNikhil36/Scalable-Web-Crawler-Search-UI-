import os, redis, hashlib, sqlalchemy as sa, pandas as pd, streamlit as st

DB_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://crawler:crawler@localhost:5432/crawlerdb")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

engine = sa.create_engine(DB_URL, pool_pre_ping=True)
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

st.set_page_config(page_title="Mini Crawler & Search", layout="wide")
st.title("🕷️ Mini Web Crawler")

def url_fingerprint(u: str) -> str:
    return hashlib.sha1(u.encode()).hexdigest()

# Sidebar: Crawl controls
st.sidebar.header("🚀 Crawl controls")
with st.sidebar.form("seed_form"):
    seed_url = st.text_input("Root URL to crawl", placeholder="https://example.com")
    submitted = st.form_submit_button("Add to frontier")
    if submitted:
        if seed_url:
            seed_url = seed_url.rstrip('/')
            fp = url_fingerprint(seed_url)
            if r.sismember("visited", fp):
                st.sidebar.info("URL already crawled or queued.")
            else:
                r.rpush("url_queue", seed_url)
                st.sidebar.success("Added to queue!")
        else:
            st.sidebar.error("Please enter a URL.")

# Live metrics
queue_len = r.llen("url_queue")
visited_cnt = r.scard("visited")
with engine.begin() as conn:
    pages_cnt = conn.scalar(sa.text("SELECT COUNT(*) FROM pages"))
st.sidebar.metric("📥 In queue", queue_len)
st.sidebar.metric("✅ Visited", visited_cnt)
st.sidebar.metric("📄 Indexed pages", pages_cnt)

st.markdown("---")

# Search
st.subheader("🔎 Search the index")
query = st.text_input("Enter keywords and press Enter", key="search_box")
if query:
    with engine.begin() as conn:
        rows = conn.execute(sa.text(
            """
            SELECT url, title,
                    ts_rank_cd(tsv, plainto_tsquery(:q)) AS rank
            FROM pages
            WHERE tsv @@ plainto_tsquery(:q)
            ORDER BY rank DESC
            LIMIT 25
            """), {"q": query}).mappings().all()
    if rows:
        df = pd.DataFrame(rows)
        for _, row in df.iterrows():
            title = row['title'] or row['url']
            st.markdown(f"**[{title}]({row['url']})**  Rank: {row['rank']:.3f}", unsafe_allow_html=True)
    else:
        st.info("No results yet — the crawler may still be working.")
else:
    st.write("Seed a URL and wait for pages to be indexed, then search here.")
