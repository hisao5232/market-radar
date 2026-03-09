from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from starlette import status
import os
import db

app = FastAPI(title="Market Radar API")

origins = [
    "https://go-pro-world.net",         # 本番ドメイン
    "https://*.pages.dev",              # Cloudflare Pagesのプレビュー用
    "http://localhost:3000",            # ローカル開発用
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,              # 許可するオリジン
    allow_credentials=True,
    allow_methods=["*"],                # 全てのメソッド（GET, POSTなど）を許可
    allow_headers=["*"],                # 全てのヘッダー（X-API-Keyなど）を許可
)

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
def get_articles(limit: int = None, api_key: str = Depends(get_api_key)):
    """最新の分析記事を取得する。limitがなければ全件返す"""
    # db.get_latest_articles に limit を渡す（Noneなら全件取得するように db.py も合わせる）
    articles = db.get_latest_articles(limit)
    return articles
