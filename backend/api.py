from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from starlette import status
import os
import db

app = FastAPI(title="Market Radar API")

# ヘッダーの名前を定義
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# .env などから読み込む（なければデフォルト値）
API_KEY = os.getenv("API_KEY", "your-super-secret-key-123")

def get_api_key(header_api_key: str = Security(api_key_header)):
    if header_api_key == API_KEY:
        return header_api_key
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials"
        )

@app.get("/")
def read_root():
    return {"status": "Market Radar is running"}

# 認証が必要なエンドポイントに Depends(get_api_key) を追加
@app.get("/articles")
def get_articles(limit: int = 10, api_key: str = Depends(get_api_key)):
    """最 新 の 分 析 記 事 を 取 得 す る (認証必須)"""
    articles = db.get_latest_articles(limit)
    return articles
