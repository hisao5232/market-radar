# Market Radar 📈

PR TIMESのRSSを監視し、キーワードに合致したニュースをAI（Gemini / Groq）で証券分析するシステムです。

## 特徴
- **冗長構成**: メインAI（Gemini 2.0 Flash）が制限（429）に達した場合、爆速のサブAI（Groq/Llama 3.3）へ自動で切り替えます。
- **DB保存**: PostgreSQLを使用して重複記事を排除。
- **コンテナ化**: Docker ComposeでDBとPython環境を一発起動。

## 技術スタック
- Python 3.12
- PostgreSQL
- Docker / Docker Compose
- Google Gemini API & Groq API
- Tailwind CSS v4 (Planned for UI)
