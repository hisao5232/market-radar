from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette import status
import os
import db
import yfinance as yf
import plotly.graph_objects as go

app = FastAPI(title="Market Radar API v1.2")

# サーバー間通信がメインになるためoriginsは現状維持でOK
origins = [
    "https://go-pro-world.net",
    "https://www.go-pro-world.net",
    "http://localhost:3000",
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

def get_api_key(x_api_key: str = Header(None)):
    if x_api_key == API_KEY:
        return x_api_key
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Invalid API Key"
    )

@app.get("/")
def read_root():
    return {"status": "Market Radar API v1.2 is online"}

@app.get("/articles")
def get_articles(limit: int = None, api_key: str = Depends(get_api_key)):
    try:
        articles = db.get_latest_articles(limit)
        return articles if articles is not None else []
    except Exception as e:
        print(f"Database Error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/market-summary")
def get_market_summary(api_key: str = Depends(get_api_key)):
    tickers = {"nikkei": "^N225", "usdjpy": "JPY=X", "orukan": "2559.T"}
    summary = {}
    for key, symbol in tickers.items():
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1mo")
            if not hist.empty:
                last_7_days = hist['Close'].tail(7).round(2).tolist()
                summary[key] = {"current": last_7_days[-1], "history": last_7_days}
            else:
                summary[key] = {"current": None, "history": []}
        except Exception as e:
            summary[key] = {"current": None, "history": []}
    return summary

# 旧 stock-history を削除し、HTMLを返す stock-chart に差し替え
@app.get("/stock-chart/{ticker}", response_class=HTMLResponse)
def get_stock_chart(ticker: str, x_api_key: str = Header(None)):
    """
    Plotlyを使用してローソク足チャートを生成し、HTMLを返す
    """
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")

    try:
        stock = yf.Ticker(ticker)
        # 直近10営業日分取得して密度を高める
        hist = stock.history(period="1mo").tail(10)
        
        if hist.empty:
            return "<p style='color:gray; font-size:10px;'>No data</p>"

        # Plotly ローソク足の設定
        fig = go.Figure(data=[go.Candlestick(
            x=hist.index.strftime('%m/%d'),
            open=hist['Open'],
            high=hist['High'],
            low=hist['Low'],
            close=hist['Close'],
            increasing_line_color='#10b981', # 上昇: 緑
            decreasing_line_color='#ef4444', # 下落: 赤
            whiskerwidth=0.5
        )])

        # UIデザイン調整: ミニマル・ダーク/ライト対応
        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            height=120,
            xaxis_rangeslider_visible=False,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            showlegend=False,
            xaxis=dict(showgrid=False, tickfont=dict(size=8, color='#94a3b8')),
            yaxis=dict(showgrid=True, gridcolor='#f1f5f9', side='right', tickfont=dict(size=8, color='#94a3b8'))
        )
        
        # HTML文字列として出力 (CDN利用で軽量化、ツールバー非表示)
        chart_html = fig.to_html(
            full_html=False, 
            include_plotlyjs='cdn', 
            config={'displayModeBar': False, 'responsive': True}
        )
        return chart_html

    except Exception as e:
        print(f"Chart Error for {ticker}: {e}")
        return f"<p style='color:red; font-size:10px;'>Chart Error</p>"
