import os, json, hashlib, redis, sqlalchemy as sa, pandas as pd, streamlit as st

# ───── Config ───────────────────────────────────────────────────────────────────
DB_URL     = os.getenv("DATABASE_URL",
                       "postgresql+psycopg2://crawler:crawler@localhost:5432/crawlerdb")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
# ────────────────────────────────────────────────────────────────────────────────

engine = sa.create_engine(DB_URL, pool_pre_ping=True)
r      = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

st.set_page_config(page_title="Mini Crawler & Search", layout="wide")
st.title("🕷️  Mini Web Crawler")

def fingerprint(url: str) -> str:
    return hashlib.sha1(url.encode()).hexdigest()

# ───────── Sidebar – crawl controls ────────────────────────────────────────────
st.sidebar.header("🚀 Crawl controls")

with st.sidebar.form("seed_form"):
    root_url  = st.text_input("Root URL", placeholder="https://example.com")
    max_depth = st.number_input("Max depth", min_value=0, value=2, step=1)
    if st.form_submit_button("Add to frontier"):
        if root_url:
            root_url = root_url.rstrip("/")
            if r.sismember("visited", fingerprint(root_url)):
                st.sidebar.info("URL already crawled or queued.")
            else:
                item = dict(url=root_url, depth=0,
                            root=root_url, max_depth=int(max_depth))
                r.rpush("url_queue", json.dumps(item))
                r.sadd("roots", root_url)
                st.sidebar.success("Queued!")
        else:
            st.sidebar.error("Please enter a URL.")

# ───────── Sidebar – active roots & delete buttons ────────────────────────────
st.sidebar.subheader("🗑️  Disable a root")
for root in sorted(r.smembers("roots")):
    if st.sidebar.button(f"Remove {root}", key=f"del_{root}"):
        r.sadd("disabled_roots", root)   # mark for workers to ignore
        r.srem("roots", root)
        st.sidebar.success(f"{root} disabled")

# ───────── Sidebar – live metrics ──────────────────────────────────────────────
queue_len   = r.llen("url_queue")
visited_cnt = r.scard("visited")
with engine.begin() as conn:
    pages_cnt = conn.scalar(sa.text("SELECT COUNT(*) FROM pages"))
st.sidebar.metric("📥 In queue",      queue_len)
st.sidebar.metric("✅ Visited",       visited_cnt)
st.sidebar.metric("📄 Indexed pages", pages_cnt)

st.markdown("---")

# ───────── Main – search UI ────────────────────────────────────────────────────
st.subheader("🔎  Search the index")
query = st.text_input("Keywords", key="search_box")

if query:
    sql = """
        SELECT url, title, ts_rank_cd(tsv, plainto_tsquery(:q)) AS rank
        FROM pages
        WHERE tsv @@ plainto_tsquery(:q)
        ORDER BY rank DESC
        LIMIT 25
    """
    with engine.begin() as conn:
        rows = conn.execute(sa.text(sql), {"q": query}).mappings().all()

    if rows:
        df = pd.DataFrame(rows)
        for _, row in df.iterrows():
            title = row["title"] or row["url"]
            st.markdown(f"**[{title}]({row['url']})** &nbsp;&nbsp;Rank {row['rank']:.3f}",
                        unsafe_allow_html=True)
    else:
        st.info("No matches yet — crawler might still be working.")
else:
    st.write("Add a root URL on the left, wait for pages to be indexed, then search.")
