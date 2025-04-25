CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE TABLE IF NOT EXISTS pages (
    id SERIAL PRIMARY KEY,
    url TEXT UNIQUE,
    title TEXT,
    content TEXT,
    crawled_at TIMESTAMPTZ DEFAULT NOW(),
    tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', coalesce(title,'') || ' ' || content)) STORED
);
CREATE INDEX IF NOT EXISTS idx_pages_tsv ON pages USING GIN(tsv);
