# Scalable Web Crawler & Search UI (v2)

**What’s new?**  
* Seed crawl URLs **directly from the sidebar**  
* Live metrics: queue length, visited count, indexed pages  
* Search and crawling in one Streamlit app

## Quick start

```bash
docker compose build
docker compose up        # open http://localhost:8501

docker compose up --build --scale crawler={number of crawlers}
```

# architecture
![image](https://github.com/user-attachments/assets/80b3de58-a448-49c6-9a66-27aa7e3ff28a)


  User → Streamlit → Redis: Add root URL

Crawler workers

  dequeue URL → fetch from Redis → extract links → enqueue new links back to Redis
  
  save page → Postgres → tsvector index
