from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from starlette import status
import os
import db
import yfinance as yf

app = FastAPI(title="Market Radar API v1.1")

# CORS設定：ブラウザからの直接アクセスを制限しつつ、開発環境やPagesを許可
origins = [
    "https://go-pro-world.net",
    "https://www.go-pro-world.net",
    "http://localhost:3000", # ローカル開発用
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.pages\.dev",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# APIキーは環境変数から取得。なければデフォルト（開発用）
API_KEY = os.getenv("API_KEY", "hisao_secure_radar_2026")

def get_api_key(x_api_key: str = Header(None)):
    if x_api_key == API_KEY:
        return x_api_key
    else:
        print(f"Auth Failed: received {x_api_key}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API Key"
        )

@app.get("/")
def read_root():
    return {"status": "Market Radar API v1.1 is online", "version": "1.1"}

@app.get("/articles")
def get_articles(limit: int = None, api_key: str = Depends(get_api_key)):
    """
    最新の記事一覧を銘柄情報付きで取得
    db.pyの get_latest_articles は既に辞書形式+銘柄リストを含んで返します
    """
    try:
        articles = db.get_latest_articles(limit)
        return articles if articles is not None else []
    except Exception as e:
        print(f"Database Error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/market-summary")
def get_market_summary(api_key: str = Depends(get_api_key)):
    """
    主要指数のサマリーを取得
    """
    tickers = {
        "nikkei": "^N225",
        "usdjpy": "JPY=X",
        "orukan": "2559.T"
    }
    summary = {}
    for key, symbol in tickers.items():
        try:
            ticker = yf.Ticker(symbol)
            # 1ヶ月分取得し、直近7営業日の終値を抽出
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
