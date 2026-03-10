import os
from datetime import datetime, timedelta
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
            
def get_latest_articles(limit=None):
    conn = get_connection()
    cur = conn.cursor()
    
    if limit:
        query = "SELECT title, analysis, created_at, url FROM articles ORDER BY created_at DESC LIMIT %s"
        cur.execute(query, (limit,))
    else:
        # limit が指定されていない場合は全件取得
        query = "SELECT title, analysis, created_at, url FROM articles ORDER BY created_at DESC"
        cur.execute(query)
        
    rows = cur.fetchall()
    
    # フロントエンド（Tailwind）で扱いやすいように辞書形式にする
    articles = []
    for row in rows:
        articles.append({
            "title": row[0],
            "analysis": row[1],
            "created_at": row[2].isoformat(),
            "url": row[3]
        })
    
    cur.close()
    conn.close()
    return articles

def delete_old_articles():
    conn = get_connection()
    cur = conn.cursor()
    # 7日以上前のデータを削除
    one_week_ago = datetime.now() - timedelta(days=7)
    cur.execute("DELETE FROM articles WHERE created_at < %s", (one_week_ago,))
    conn.commit()
    print(f"[{datetime.now()}] Deleted old articles before {one_week_ago}")
    cur.close()
    conn.close()
                    