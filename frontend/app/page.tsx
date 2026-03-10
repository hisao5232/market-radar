import ReactMarkdown from 'react-markdown';

export const runtime = 'edge';

// 型定義の強化
interface Article {
  id: number; // バックエンドのJSONに合わせて追加
  title: string;
  analysis: string;
  created_at: string;
  url?: string;
}

export default async function Home() {
  // 1. 環境変数の取得とスラッシュ処理
  const rawBaseUrl = process.env.NEXT_PUBLIC_API_URL || 'https://radar-api.go-pro-world.net';
  const baseUrl = rawBaseUrl.replace(/\/$/, '');
  const apiKey = process.env.API_KEY || 'hisao_secure_radar_2026';

  // 2. バックエンドからデータを取得
  const res = await fetch(`${baseUrl}/articles`, {
    headers: {
      'X-API-Key': apiKey,
    },
    cache: 'no-store' 
  });

  // 3. エラーハンドリング
  if (!res.ok) {
    console.error(`Fetch failed: ${res.status} to ${baseUrl}`);
    return (
      <main className="flex items-center justify-center min-h-screen">
        <div className="p-6 bg-red-50 text-red-700 rounded-lg border border-red-200 shadow-lg text-center">
          <p className="font-bold text-xl mb-2">データの取得に失敗しました</p>
          <p className="text-sm opacity-80">ステータス: {res.status}</p>
          <p className="text-xs mt-2 font-mono">{baseUrl}</p>
        </div>
      </main>
    );
  }

  const articles: Article[] = await res.json();

  // 4. データが 0 件の場合の処理
  if (articles.length === 0) {
    return (
      <main className="flex items-center justify-center min-h-screen">
        <div className="p-6 bg-yellow-50 text-yellow-700 rounded-lg border border-yellow-200 shadow-lg">
          表示できるニュースがまだありません（DBを確認してください）
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-50 p-6 md:p-12">
      <div className="max-w-4xl mx-auto">
        <header className="mb-12 border-b border-slate-200 pb-8 text-center md:text-left">
          <h1 className="text-4xl font-black text-slate-900 mb-3 tracking-tight">
            Market Radar <span className="text-blue-600">v1.1</span>
          </h1>
          <p className="text-slate-600 text-lg">
            AIによる最新市場ニュース分析と株価の変動をリアルタイムでお届けします
          </p>
        </header>

        <div className="grid gap-10">
          {articles.map((article: Article) => (
            <article
              key={article.id}
              className="bg-white rounded-3xl shadow-sm border border-slate-200 overflow-hidden hover:shadow-xl transition-all duration-300"
            >
              <div className="p-8">
                {/* ニュースタイトル */}
                <h2 className="text-2xl font-bold text-slate-800 mb-6 leading-snug">
                  {article.title}
                </h2>

                {/* メタ情報バッジ */}
                <div className="flex flex-wrap items-center gap-3 text-xs font-bold mb-8">
                  {/* 元記事リンクボタン：クリックすると別タブで開く */}
                  {article.url && (
                    <a 
                      href={article.url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-xl transition-all duration-200 flex items-center gap-2 shadow-sm hover:shadow-md active:scale-95 border-b-2 border-blue-800"
                    >
                      <span className="text-sm">🔗</span>
                      <span>ニュース元記事を見る</span>
                    </a>
                  )}
                  
                  {/* 日本時間表示 */}
                  <div className="flex items-center gap-1.5 text-slate-500 bg-slate-50 px-4 py-2 rounded-xl border border-slate-200 shadow-sm">
                    <span>🕒</span>
                    <time dateTime={article.created_at}>
                      {new Date(article.created_at).toLocaleString('ja-JP', {
                        timeZone: 'Asia/Tokyo',
                        year: 'numeric',
                        month: '2-digit',
                        day: '2-digit',
                        hour: '2-digit',
                        minute: '2-digit'
                      })} (JST)
                    </time>
                  </div>
                </div>

                {/* AI分析カード */}
                <div className="bg-blue-50/40 rounded-2xl p-6 md:p-8 border border-blue-100/50">
                  <div className="flex items-center gap-2 mb-6">
                    <span className="text-2xl">🤖</span>
                    <h3 className="text-lg font-bold text-blue-900 tracking-tight">
                      AI分析
                    </h3>
                  </div>

                  <div className="prose prose-slate prose-blue max-w-none
                    text-slate-700
                    prose-headings:text-blue-900 prose-headings:font-bold prose-headings:mt-6 prose-headings:mb-3
                    prose-p:leading-relaxed prose-p:mb-4
                    prose-li:my-1
                    prose-strong:text-blue-800 prose-strong:font-bold">
                    <ReactMarkdown>
                      {article.analysis}
                    </ReactMarkdown>
                  </div>
                </div>
              </div>
            </article>
          ))}
        </div>

        <footer className="mt-20 text-center text-slate-400 text-sm pb-10 border-t border-slate-200 pt-10">
          &copy; Go-into-PG-world Since 2025. All rights reserved.
        </footer>
      </div>
    </main>
  );
}
