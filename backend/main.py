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
    AIが抽出した企業名リストをCSVと照合して正確なティッカーを付与する
    """
    csv_path = os.path.join(os.path.dirname(__file__), "stock_list.csv")
    if not os.path.exists(csv_path):
        return raw_companies # CSVがなければそのまま返す

    df = pd.read_csv(csv_path)
    # 検索を高速化するために辞書化 (名前 -> ティッカー)
    ticker_map = dict(zip(df['name'], df['ticker']))
    
    verified = []
    for co in raw_companies:
        name = co.get("name", "")
        # 1. 完全一致で検索
        ticker = ticker_map.get(name)
        
        # 2. ヒットしない場合、部分一致で検索 (例: 「トヨタ」で「トヨタ自動車」を探す)
        if not ticker:
            match = df[df['name'].str.contains(name, na=False)]
            if not match.empty:
                # 最も文字数が近い、あるいは最初のものを採用
                ticker = match.iloc[0]['ticker']
                name = match.iloc[0]['name'] # 名称も正式なものに補正
        
        verified.append({
            "name": name,
            "ticker": ticker if ticker else "None", # リストにない（東芝等）はNone
            "reason": co.get("reason", "")
        })
    return verified

def analyze_with_groq(title, text):
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    
    # プロンプトを「企業名の抽出」に集中させるよう修正
    prompt = f"""
あなたはプロの証券アナリストです。以下のニュースを読み、影響を受ける日本企業を抽出してください。

【出力ルール】
1. analysis: 
   - 「AI分析スコア」を0-100で提示。スコアの理由と今後の展望を200文字程度の日本語で。
2. companies: 影響を受ける企業（最大3社）
   - name: 日本の上場企業なら「正式な社名」を抜き出してください。（例：トヨタ ではなく トヨタ自動車）
   - reason: 影響の理由を1行で。
   ※ティッカー(証券コード)を推測する必要はありません。

【ニュース詳細】
タイトル: {title}
本文: {text[:4000]}

【JSONフォーマット】
{{
  "analysis": "### 🤖 AI分析スコア: 75\\n\\n理由: ...",
  "companies": [
    {{"name": "企業名", "reason": "〇〇による収益拡大"}}
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
