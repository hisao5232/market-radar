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
    """
    AIが抽出した企業名リストをCSVと照合して正確なティッカーを付与する。
    部分一致の精度を高め、最も適切な候補を選択するように改良。
    """
    csv_path = os.path.join(os.path.dirname(__file__), "stock_list.csv")
    if not os.path.exists(csv_path):
        return raw_companies

    # CSV読み込み
    df = pd.read_csv(csv_path)
    # 辞書化（完全一致用：高速化）
    ticker_map = dict(zip(df['name'], df['ticker']))
    
    verified = []
    for co in raw_companies:
        name = co.get("name", "").strip()
        if not name:
            continue
            
        ticker = None
        verified_name = name

        # 1. 完全一致で検索
        if name in ticker_map:
            ticker = ticker_map[name]
        
        # 2. ヒットしない場合、部分一致で検索
        else:
            # AIが抜いた名前（例：「トヨタ」）がCSVの社名（例：「トヨタ自動車」）に含まれているか
            # またはその逆（CSVの社名がAIの抜いた名前に含まれているか）
            mask = df['name'].str.contains(name, na=False, case=False)
            matches = df[mask]
            
            if not matches.empty:
                # 複数の候補がある場合、AIが抜いた名前に「最も文字数が近い」ものを採用（精度の向上）
                # 例：「日本テレビ」に対して「日本テレビ放送網」と「日本放送協会」があれば、近い方を狙う
                matches = matches.copy()
                matches['name_len_diff'] = matches['name'].str.len() - len(name)
                best_match = matches.sort_values(by='name_len_diff').iloc[0]
                
                ticker = best_match['ticker']
                verified_name = best_match['name']

        # 3. ティッカーの整形（4桁数字なら .T を付与）
        final_ticker = "None"
        if ticker:
            s_ticker = str(ticker)
            if s_ticker.isdigit() and len(s_ticker) == 4:
                final_ticker = f"{s_ticker}.T"
            else:
                final_ticker = s_ticker

        verified.append({
            "name": verified_name,
            "ticker": final_ticker,
            "reason": co.get("reason", "")
        })
        
    return verified

def analyze_with_groq(title, text):
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    
    # プロンプトを「企業名の抽出」に集中させるよう修正
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
   - 創作した専門用語や、不自然な漢字変換（例：放引、府徳など）は絶対に使用禁止。
3. 関連企業 (companies): 
   - 記事に登場、または直接関連する「日本企業」を最大3社。
   - name: 「株式会社」などを除いた正式な社名（例：トヨタ自動車、LayerX）。
   - reason: 影響の理由を1文で。

【出力形式】
必ず有効なJSONのみ出力してください。

{{
 "score": 0,
 "analysis": "ここに自然な日本語で分析を記述",
 "companies":[
   {{"name": "企業名", "reason": "理由を記述"}}
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
    # 起動時のDBリセットは運用に合わせて調整（毎回消したくない場合はコメントアウト）
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
                    # --- 【重要】Python側でティッカーを確定させる ---
                    raw_companies = result.get("companies", [])
                    verified_companies = get_verified_companies(raw_companies)
                    
                    # ★ ここに確認用のログを追加
                    print(f"DEBUG: 照合結果 -> {json.dumps(verified_companies, ensure_ascii=False, indent=2)}")
                    
                    db.save_article(
                        link, 
                        title, 
                        result.get("analysis", ""), 
                        verified_companies # 照合済みのリストを渡す
                    )
                    print(f"分析完了: {len(verified_companies)}社特定")
                
                time.sleep(2)
            except Exception as e:
                print(f"処理エラー: {e}")

if __name__ == "__main__":
    main()
