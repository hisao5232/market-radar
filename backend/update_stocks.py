import pandas as pd
import requests
import os

def update_jpx_csv():
    # 提示いただいた最新のURL
    url = "https://www.jpx.co.jp/markets/statistics-equities/misc/tvdivq0000001vg2-att/data_j.xls"
    csv_path = "stock_list.csv" 
    temp_file = "temp.xls"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        print(f"Downloading from: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        with open(temp_file, "wb") as f:
            f.write(response.content)
        
        print("Processing Excel data (.xls) with engine='xlrd'...")
        # .xls形式なので engine="xlrd" を使用します
        df = pd.read_excel(temp_file, engine="xlrd")
        
        # 列名のクレンジング
        df.columns = [str(c).replace('\n', '').strip() for c in df.columns]

        # 必要な列を特定（コード、銘柄名、33業種区分）
        code_col = [c for c in df.columns if 'コード' in c][0]
        name_col = [c for c in df.columns if '銘柄名' in c][0]
        sector_col = [c for c in df.columns if '33業種区分' in c][0]

        # ティッカー形式 (1234.T) に整形
        # 数値として読み込まれる場合があるためint変換してから文字列へ
        df['ticker'] = df[code_col].astype(str).str.split('.').str[0] + ".T"
        
        df_clean = df[['ticker', name_col, sector_col]]
        df_clean.columns = ['ticker', 'name', 'sector']
        
        # 保存
        df_clean.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print(f"✅ Success! Updated: {os.path.abspath(csv_path)}")
        print(f"Total stocks: {len(df_clean)}")
        
    except Exception as e:
        print(f"⚠️ Error: {e}")
        
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

if __name__ == "__main__":
    update_jpx_csv()
    