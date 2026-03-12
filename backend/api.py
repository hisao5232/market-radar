from fastapi import FastAPI, Depends, HTTPException, Header  # Headerを追加
from fastapi.middleware.cors import CORSMiddleware
from starlette import status
import os
import db
import yfinance as yf

app = FastAPI(title="Market Radar API")

# CORS設定：Traefik経由での自分のドメインを許可
# サーバーサイド取得がメインになればここは厳格でも大丈夫になります
origins = [
    "https://go-pro-world.net",
    "https://www.go-pro-world.net",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.pages\.dev",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = os.getenv("API_KEY", "hisao_secure_radar_2026")

# 【変更点】ヘッダーから X-API-Key を読み取る認証関数
def get_api_key(x_api_key: str = Header(None)):
    if x_api_key == API_KEY:
        return x_api_key
    else:
        # 認証失敗時のログをバックエンドに残すとデバッグが捗ります
        print(f"Auth Failed: received {x_api_key}") 
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API Key"
        )

@app.get("/")
def read_root():
    return {"status": "Market Radar is running"}

@app.get("/articles")
def get_articles(limit: int = None, api_key: str = Depends(get_api_key)):
    # db.pyの結果がNoneの場合に備えてガードを入れるのが現場流
    articles = db.get_latest_articles(limit)
    return articles if articles is not None else []

@app.get("/market-summary")
def get_market_summary(api_key: str = Depends(get_api_key)):
    tickers = {
        "nikkei": "^N225",
        "usdjpy": "JPY=X",
        "orukan": "2559.T"
    }
    summary = {}
    for key, symbol in tickers.items():
        try:
            ticker = yf.Ticker(symbol)
            # グラフ描画用に1ヶ月分取って7日分出す（土日を挟んでも確実にデータを確保するため）
            hist = ticker.history(period="1mo")
            if not hist.empty:
                last_7_days = hist['Close'].tail(7).round(2).tolist()
                summary[key] = {
                    "current": last_7_days[-1],
                    "history": last_7_days
                }
            else:
                summary[key] = {"current": None, "history": []}
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            summary[key] = {"current": None, "history": []}
    return summary
