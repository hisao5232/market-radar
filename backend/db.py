import os
import psycopg2
from psycopg2.extras import DictCursor

def get_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST"),
        database=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD")
    )

def init_db():
    """テーブル作成"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS articles (
                    id SERIAL PRIMARY KEY,
                    url TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    analysis TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()

def is_processed(url):
    """処理済みチェック"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT 1 FROM articles WHERE url = %s', (url,))
            return cur.fetchone() is not None

def save_article(url, title, analysis):
    """結果の保存"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'INSERT INTO articles (url, title, analysis) VALUES (%s, %s, %s) ON CONFLICT (url) DO NOTHING',
                (url, title, analysis)
            )
            conn.commit()
            
def get_latest_articles(limit=10):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT title, analysis, created_at FROM articles ORDER BY created_at DESC LIMIT %s",
        (limit,)
    )
    rows = cur.fetchall()
    
    # フロントエンド（Tailwind）で扱いやすいように辞書形式にする
    articles = []
    for row in rows:
        articles.append({
            "title": row[0],
            "analysis": row[1],
            "created_at": row[2].isoformat()
        })
    
    cur.close()
    conn.close()
    return articles
                