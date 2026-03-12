import os
import json
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
    """テーブル作成（銘柄リスト用のJSONBカラムを追加）"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS articles (
                    id SERIAL PRIMARY KEY,
                    url TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    analysis TEXT,
                    impacted_companies JSONB DEFAULT '[]', -- 銘柄情報を構造化データで保存
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

def save_article(url, title, analysis, impacted_companies):
    """
    結果の保存
    impacted_companies: List[Dict] を受け取り、JSONとして保存
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            # PostgreSQLのJSONB型にはjson.dumpsした文字列を渡す
            companies_json = json.dumps(impacted_companies)
            cur.execute(
                '''
                INSERT INTO articles (url, title, analysis, impacted_companies) 
                VALUES (%s, %s, %s, %s) 
                ON CONFLICT (url) DO NOTHING
                ''',
                (url, title, analysis, companies_json)
            )
            conn.commit()

def get_latest_articles(limit=None):
    """最新記事の取得（銘柄情報を含む）"""
    conn = get_connection()
    # DictCursorを使うとカラム名でアクセスできて保守性が上がります
    cur = conn.cursor(cursor_factory=DictCursor)
    
    if limit:
        query = "SELECT title, analysis, created_at, url, impacted_companies FROM articles ORDER BY created_at DESC LIMIT %s"
        cur.execute(query, (limit,))
    else:
        query = "SELECT title, analysis, created_at, url, impacted_companies FROM articles ORDER BY created_at DESC"
        cur.execute(query)
        
    rows = cur.fetchall()
    
    articles = []
    for row in rows:
        articles.append({
            "title": row["title"],
            "analysis": row["analysis"],
            "created_at": row["created_at"].isoformat(),
            "url": row["url"],
            "impacted_companies": row["impacted_companies"] # JSONBは自動的にdict/listとして読み込まれます
        })
    
    cur.close()
    conn.close()
    return articles

def delete_old_articles():
    """7日以上前のデータを削除"""
    conn = get_connection()
    cur = conn.cursor()
    one_week_ago = datetime.now() - timedelta(days=7)
    cur.execute("DELETE FROM articles WHERE created_at < %s", (one_week_ago,))
    conn.commit()
    print(f"[{datetime.now()}] Deleted old articles before {one_week_ago}")
    cur.close()
    conn.close()
