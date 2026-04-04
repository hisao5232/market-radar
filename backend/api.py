from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette import status
from contextlib import asynccontextmanager
import os
import db
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import numpy as np

# --- lifespan (起動時処理) の定義 ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # アプリ起動時に実行される処理
    print("Initializing database...")
    try:
        db.init_db() # ここでテーブル作成を実行
        print("Database initialized successfully.")
    except Exception as e:
        print(f"Failed to initialize database: {e}")
    
    yield
    # アプリ終了時に実行したい処理があればここに記述（今回は不要）

# FastAPIの引数に lifespan を追加
app = FastAPI(title="Market Radar API v1.2", lifespan=lifespan)

# サーバー間通信がメインになるためoriginsは現状維持でOK
origins = [
    "https://market-radar.pages.dev", # Cloudflareのドメイン
    "https://go-pro-world.net",       # 独自ドメイン
    "https://www.go-pro-world.net",
    "https://market-radar.go-pro-world.net",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    # go-pro-world.net の全サブドメイン と Cloudflare Pages の全ドメインを許可
    allow_origin_regex=r"https://.*\.go-pro-world\.net|https://.*\.pages\.dev",
    allow_credentials=True,
    allow_methods=["*", "OPTIONS"], # OPTIONSを明示的に許可
    allow_headers=["*"],
)

API_KEY = os.getenv("API_KEY")

def get_api_key(x_api_key: str = Header(None)):
    # API_KEYが設定されていない、または一致しない場合は拒否
    if API_KEY and x_api_key == API_KEY:
        return x_api_key
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Invalid or Missing API Key"
    )

@app.get("/")
def read_root():
    return {"status": "Market Radar API v1.2 is online"}

@app.get("/articles")
def get_articles(limit: int = 50, api_key: str = Depends(get_api_key)):
    """
    最新の記事を取得する（デフォルト50件）
    """
    try:
        # DB操作関数にlimitを渡す
        articles = db.get_latest_articles(limit)
        return articles if articles is not None else []
    except Exception as e:
        print(f"Database Error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/market-summary")
def get_market_summary(api_key: str = Depends(get_api_key)):
    """
    日経平均、ドル円、オルカンのサマリーを取得。
    JSON compliantにするため、NaN(非数)を厳格に排除。
    """
    tickers = {"nikkei": "^N225", "usdjpy": "JPY=X", "orukan": "2559.T"}
    summary = {}
    
    for key, symbol in tickers.items():
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1mo")
            
            if not hist.empty:
                # 終値を取得し、小数点2桁で丸める
                series = hist['Close'].tail(7).round(2)
                
                # 【重要】NaNをNone(JSONのnull)に置換する絶縁処理
                # list型に変換する際、pd.isna()で判定してNoneを入れます
                last_7_days = [
                    val if not pd.isna(val) else None 
                    for val in series.tolist()
                ]
                
                # 現在値（リストの最後）を取得
                current_val = last_7_days[-1] if last_7_days else None
                
                summary[key] = {
                    "current": current_val, 
                    "history": last_7_days
                }
            else:
                summary[key] = {"current": None, "history": []}
                
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            summary[key] = {"current": None, "history": []}
            
    return summary

@app.get("/stock-chart/{ticker}", response_class=HTMLResponse)
def get_stock_chart(ticker: str, x_api_key: str = Header(None)):
    """
    Plotlyを使用してローソク足チャートを生成。
    HTMLとして返すため、NaNがあってもPlotly側で処理されるが、
    念のためデータクレンジングを行う。
    """
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
        
    try:
        stock = yf.Ticker(ticker)
        # 直近10営業日分取得
        hist = stock.history(period="1mo").tail(10)
        
        if hist.empty:
            return "<p style='color:gray; font-size:10px; text-align:center;'>No data</p>"

        # ローソク足チャートの生成
        fig = go.Figure(data=[go.Candlestick(
            x=hist.index.strftime('%m/%d'),
            open=hist['Open'],
            high=hist['High'],
            low=hist['Low'],
            close=hist['Close'],
            increasing_line_color='#10b981', # 上昇: 緑 (Tailwind blue-500相当)
            decreasing_line_color='#ef4444', # 下落: 赤 (Tailwind red-500相当)
            whiskerwidth=0.5
        )])

        # ミニマルなデザイン調整
        fig.update_layout(
            margin=dict(l=0, r=0, t=20, b=10), # 余白を詰める
            height=120,
            xaxis_rangeslider_visible=False,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            showlegend=False,
            xaxis=dict(
                showgrid=False, 
                tickfont=dict(size=8, color='#94a3b8'),
                fixedrange=True # ズーム禁止で安定させる
            ),
            yaxis=dict(
                showgrid=True, 
                gridcolor='#f1f5f9', 
                side='right', 
                tickfont=dict(size=8, color='#94a3b8'),
                fixedrange=True
            )
        )

        # HTMLとして出力
        chart_html = fig.to_html(
            full_html=False,
            include_plotlyjs='cdn',
            config={
                'displayModeBar': False, 
                'responsive': True,
                'staticPlot': False # インタラクティブ性は維持
            }
        )
        return chart_html
        
    except Exception as e:
        print(f"Chart Error for {ticker}: {e}")
        return f"<p style='color:red; font-size:10px;'>Chart Error</p>"

