import ReactMarkdown from 'react-markdown';

export const runtime = 'edge';

// 型を定義しておくとメンテナンスが楽になります
interface Article {
  title: string;
  analysis: string;
  created_at: string;
  url?: string;
}

export default async function Home() {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, ''); // 末尾のスラッシュを削除
  
  if (!baseUrl) {
    console.error("API URL is not defined");
  }

  const res = await fetch(`${baseUrl}/articles`, {
    headers: {
      'X-API-Key': process.env.API_KEY || '',
    },
    cache: 'no-store' 
  });

  if (!res.ok) {
    // 403 Forbidden などのエラー内容をログに出すとデバッグが捗ります
    console.error(`Fetch failed: ${res.status}`);
    return (
      <main className="flex items-center justify-center min-h-screen">
        <div className="p-6 bg-red-50 text-red-700 rounded-lg border border-red-200">
          データの取得に失敗しました。ステータス: {res.status}
        </div>
      </main>
    );
  }

  const articles = await res.json();

  return (
    <main className="min-h-screen bg-slate-50 p-6 md:p-12">
      <div className="max-w-4xl mx-auto">
        <header className="mb-12 border-b border-slate-200 pb-8 text-center md:text-left">
          <h1 className="text-4xl font-black text-slate-900 mb-3 tracking-tight">
            Market Radar <span className="text-blue-600">v1.0</span>
          </h1>
          <p className="text-slate-600 text-lg">
            AIによる最新市場ニュース分析と株価の変動をリアルタイムでお届けします
          </p>
        </header>
        
        <div className="grid gap-10">
          {articles.map((article: any, index: number) => (
            <article 
              // id が取得できていない場合に備え、url または index を含めた一意のキーにする
              key={article.url || index} 
              className="bg-white rounded-3xl shadow-sm border border-slate-200 overflow-hidden hover:shadow-xl transition-all duration-300"
            >
              <div className="p-8">
                <h2 className="text-2xl font-bold text-slate-800 mb-4 leading-snug">
                  {article.title}
                </h2>

                <div className="flex items-center gap-4 text-xs font-medium text-slate-400 mb-8">
                  <time dateTime={article.created_at} className="bg-slate-100 text-slate-600 px-3 py-1 rounded-full uppercase tracking-wider">
                    {new Date(article.created_at).toLocaleString('ja-JP', {
                      year: 'numeric',
                      month: 'long',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </time>
                </div>

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

        <footer className="mt-20 text-center text-slate-400 text-sm pb-10">
          &copy; Go-into-PG-world Since 2025. All rights reserved.
        </footer>
      </div>
    </main>
  );
}
