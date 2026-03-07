// frontend/src/app/page.tsx

export default async function Home() {
  // 1. バックエンドからデータを取得（Fetch）
  // サーバーサイドで実行されるので、安全にAPIキーを使えます
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/articles?limit=5`, {
    headers: {
      'X-API-Key': process.env.API_KEY || '',
    },
    // キャッシュを1分間保持（サーバー負荷軽減）
    next: { revalidate: 60 } 
  });

  if (!res.ok) {
    return <main className="p-8">データの取得に失敗しました。APIキーやURLを確認してください。</main>;
  }

  const articles = await res.json();

  return (
    <main className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto">
        <header className="mb-12">
          <h1 className="text-4xl font-extrabold text-slate-900 mb-2">Market Radar</h1>
          <p className="text-slate-500">AIによる最新市場ニュース分析</p>
        </header>
        
        <div className="grid gap-8">
          {articles.map((article: any) => (
            <article key={article.id} className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 hover:shadow-md transition-shadow">
              <h2 className="text-xl font-bold text-slate-800 mb-3 leading-tight">
                {article.title}
              </h2>
              <div className="flex items-center gap-4 text-xs text-slate-400 mb-4">
                <span className="bg-slate-100 px-2 py-1 rounded">ID: {article.id}</span>
                <span>{new Date(article.created_at).toLocaleString('ja-JP')}</span>
              </div>
              <div className="bg-blue-50/50 p-4 rounded-xl border border-blue-100">
                <h3 className="text-sm font-semibold text-blue-800 mb-2">🤖 AI分析スコア & 理由</h3>
                <p className="text-slate-700 text-sm whitespace-pre-wrap leading-relaxed">
                  {article.analysis}
                </p>
              </div>
            </article>
          ))}
        </div>
      </div>
    </main>
  );
}
