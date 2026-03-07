from fastapi import FastAPI
import db

app = FastAPI(title="Market Radar API")

@app.get("/")
def read_root():
    return {"status": "Market Radar is running"}

@app.get("/articles")
def get_articles(limit: int = 10):
    """最新の分析記事を取得する"""
    # db.py に 'get_latest_articles' 関数を作って呼び出す
    articles = db.get_latest_articles(limit)
    return articles
    