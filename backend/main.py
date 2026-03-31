import os
import json
import time
import feedparser
import requests
import pandas as pd  # 追加
from bs4 import BeautifulSoup
from groq import Groq
import db

# --- 銘柄照合用の関数 ---
def get_verified_companies(raw_companies):
    csv_path = os.path.join(os.path.dirname(__file__), "stock_list.csv")
    if not os.path.exists(csv_path):
        return raw_companies

    df = pd.read_csv(csv_path)

    # --- ここを強化：全角・半角スペースを完全に除去 ---
    # CSV側の「第 一 生 命」を「第一生命」に変換して比較用にする
    df['clean_name'] = df['name'].str.replace(r'[\s　]+', '', regex=True)

    verified = []
    for co in raw_companies:
        raw_name = co.get("name", "").strip()
        if not raw_name: continue

        # AIが出した名前からも全角・半角スペースを除去
        import re
        search_name = re.sub(r'[\s　]+', '', raw_name)

        ticker = None
        verified_name = raw_name

        # 1. 完全一致（スペースなし同士）
        match = df[df['clean_name'] == search_name]

        # 2. ヒットしない場合、部分一致
        if match.empty:
            mask = df['clean_name'].str.contains(search_name, na=False, case=False)
            match = df[mask]

        if not match.empty:
            match = match.copy()
            match['name_len_diff'] = (match['clean_name'].str.len() - len(search_name)).abs()
            best_match = match.sort_values(by='name_len_diff').iloc[0]
            ticker = best_match['ticker']
            verified_name = best_match['name']

        # 3. ティッカーの整形（4桁数字なら .T を付与）
        final_ticker = "None"
        if ticker:
            s_ticker = str(ticker).strip()
            # すでに .T がついている場合や、数字4桁の場合を考慮
            if s_ticker.isdigit() and len(s_ticker) == 4:
                final_ticker = f"{s_ticker}.T"
            elif ".T" in s_ticker:
                final_ticker = s_ticker
            else:
                # リート(REIT)などで4桁でない場合も想定してそのまま返す
                final_ticker = s_ticker

        verified.append({
            "name": verified_name,
            "ticker": final_ticker,
            "reason": co.get("reason", "")
        })
        
    return verified

def analyze_with_groq(title, text):
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    
    prompt = f"""
あなたは日本株専門の証券アナリストです。
提供されたニュースを読み、日本の株式市場への影響を客観的に評価してください。

【ニュース】
タイトル: {title}
本文: {text[:3000]}

【出力ルール】
1. AI分析スコア (score): 0〜100で評価。
2. 要約・影響 (analysis): 
   - ニュースの本質と市場への影響を2〜3文の「自然な日本語」で記述。
3. 関連企業 (companies): 
   - 記事に登場、または直接関連する「日本企業」を最大3社。
   - name: 「株式会社」などを除いた正式な社名。
   - ticker: 4桁の証券コード（例: 8750.T）。不明なら "none"。
   - reason: 影響の理由を1文で。

【出力形式】
必ず有効なJSONのみ出力してください。
{{
 "score": 0,
 "analysis": "...",
 "companies":[
   {{"name": "企業名", "ticker": "8750.T または none", "reason": "..."}}
 ]
}}
"""
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "出力は必ず純粋なJSON形式のみで行ってください。"},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"Groq分析エラー: {e}")
        return None

def main():
    # 起動時のDBリセット設定
    # db.init_db() 
    
    with open(os.path.join(os.path.dirname(__file__), "keywords.txt"), 'r') as f:
        target_keywords = [line.strip() for line in f if line.strip()]

    feed = feedparser.parse("https://prtimes.jp/index.rdf")
    for entry in feed.entries:
        title = entry.get('title', '')
        link = entry.get('link', '')
        
        if any(kw in title.lower() for kw in target_keywords):
            if db.is_processed(link): continue
            
            print(f"★重要ニュース発見: {title}")
            try:
                res = requests.get(link, timeout=10)
                soup = BeautifulSoup(res.text, 'html.parser')
                body = soup.select_one('.press-release-body-v3-0-0') or soup.body
                
                result = analyze_with_groq(title, body.get_text())
                
                if result:
                    raw_companies = result.get("companies", [])
                    verified_companies = []

                    for co in raw_companies:
                        ticker = co.get("ticker", "none")
                        
                        # --- ハイブリッド照合ロジック ---
                        # 1. AIが有効なティッカー（xxxx.T）を返してきた場合
                        if ticker and ticker.lower() != "none":
                            print(f"DEBUG: AIにより特定 -> {co['name']} ({ticker})")
                            verified_companies.append(co)
                        
                        # 2. AIが特定できなかった(none)場合、CSVから補完を試みる
                        else:
                            print(f"DEBUG: AI未特定のためCSV照合開始 -> {co['name']}")
                            # get_verified_companies はリストを受け取る仕様なので [co] で渡す
                            v_list = get_verified_companies([co])
                            if v_list and v_list[0].get("ticker") != "None":
                                print(f"DEBUG: CSVにより補完成功 -> {v_list[0]['name']} ({v_list[0]['ticker']})")
                                verified_companies.append(v_list[0])
                            else:
                                # CSVでもダメなら、そのまま（ticker="None"）追加
                                verified_companies.append(v_list[0] if v_list else co)
                    
                    # 最終的な保存処理
                    db.save_article(
                        link, 
                        title, 
                        result.get("analysis", ""), 
                        verified_companies 
                    )
                    print(f"分析完了: {len(verified_companies)}社特定済")
                
                time.sleep(2)
            except Exception as e:
                print(f"処理エラー: {e}")

if __name__ == "__main__":
    main()
