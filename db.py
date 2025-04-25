import os, sqlalchemy as sa
DB_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://crawler:crawler@localhost:5432/crawlerdb")
engine = sa.create_engine(DB_URL, pool_size=10, max_overflow=20)
def init_db():
    with engine.begin() as conn:
        with open('create_tables.sql', 'r', encoding='utf-8') as f:
            conn.exec_driver_sql(f.read())
