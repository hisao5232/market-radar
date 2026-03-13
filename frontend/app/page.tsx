import React from 'react';
import ReactMarkdown from 'react-markdown';
import { Sparkline } from '../components/MarketDashboard';

interface ImpactedCompany {
  name: string;
  ticker: string;
  reason: string;
  chartHtml?: string; // バックエンドから受け取るHTML文字列
}

interface Article {
  id: number;
  title: string;
  analysis: string;
  created_at: string;
  url?: string;
  impacted_companies?: ImpactedCompany[];
}

interface MarketData {
  nikkei: { current: number; history: number[] };
  usdjpy: { current: number; history: number[] };
  orukan: { current: number; history: number[] };
}

const formatJST = (dateString: string) => {
  const date = new Date(dateString);
  return new Intl.DateTimeFormat('ja-JP', {
    timeZone: 'Asia/Tokyo',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  }).format(date).replace(/\//g, '-');
};

export default async function Home() {
  const baseUrl = 'https://radar-api.go-pro-world.net';
  const apiKey = 'hisao_secure_radar_2026';
  let articles: Article[] = [];
  let market: MarketData | null = null;
  let error: string | null = null;

  try {
    const [articlesRes, marketRes] = await Promise.all([
      fetch(`${baseUrl}/articles`, {
        headers: { 'X-API-Key': apiKey },
        cache: 'no-store',
      }),
      fetch(`${baseUrl}/market-summary`, {
        headers: { 'X-API-Key': apiKey },
        cache: 'no-store',
      })
    ]);

    if (!articlesRes.ok) throw new Error(`Articles API: ${articlesRes.status}`);
    articles = await articlesRes.json();
    if (marketRes.ok) market = await marketRes.json();

    // --- バックエンドで生成されたチャートHTMLを一括取得 ---
    articles = await Promise.all(articles.map(async (article) => {
      if (!article.impacted_companies) return article;

      const updatedCompanies = await Promise.all(article.impacted_companies.map(async (co) => {
        const isPublic = co.ticker && co.ticker.toLowerCase() !== 'none';
        if (!isPublic) return co;

        try {
          // 生データではなく、描画済みのHTMLをリクエスト
          const chartRes = await fetch(`${baseUrl}/stock-chart/${co.ticker}`, {
            headers: { 'X-API-Key': apiKey },
            next: { revalidate: 3600 } 
          });
          const chartHtml = chartRes.ok ? await chartRes.text() : "";
          return { ...co, chartHtml };
        } catch (err) {
          console.error(`Chart Fetch Error for ${co.ticker}:`, err);
          return { ...co, chartHtml: "" };
        }
      }));

      return { ...article, impacted_companies: updatedCompanies };
    }));

  } catch (err: any) {
    console.error("Server Fetch Error:", err);
    error = err.message;
  }

  return (
    <main className="min-h-screen bg-slate-50 p-6 md:p-12 font-sans text-slate-900">
      <div className="max-w-4xl mx-auto">
        <header className="mb-12 border-b-2 border-slate-200 pb-8">
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
            <div>
              <h1 className="text-4xl font-black text-slate-900 mb-2 tracking-tighter italic">
                MARKET RADAR <span className="text-blue-600 not-italic">v1.3</span>
              </h1>
              <p className="text-slate-500 font-medium">2026.03 AI-Driven Market Intelligence</p>
            </div>
            {error && (
              <div className="bg-red-50 text-red-600 text-[10px] font-mono p-3 rounded-lg border border-red-100">
                [SYSTEM_ALERT]: {error}
              </div>
            )}
          </div>
          {market && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-8">
              {[
                { label: "日経平均株価", data: market.nikkei, unit: "円" },
                { label: "米ドル / 円", data: market.usdjpy, unit: "円", fixed: 2 },
                { label: "オルカン (2559.T)", data: market.orukan, unit: "円" }
              ].map((item, idx) => (
                <div key={idx} className="bg-white p-5 rounded-2xl shadow-sm border border-slate-200 hover:border-blue-400 transition-colors">
                  <p className="text-[10px] font-bold text-slate-400 mb-1 uppercase tracking-widest">{item.label}</p>
                  <p className="text-2xl font-black">
                    {item.data?.current ? (item.fixed ? item.data.current.toFixed(item.fixed) : item.data.current.toLocaleString()) : "---"}
                    <span className="text-sm font-normal text-slate-300 ml-1">{item.unit}</span>
                  </p>
                  <Sparkline data={item.data?.history || []} />
                </div>
              ))}
            </div>
          )}
        </header>

        <div className="space-y-8">
          {articles.length === 0 ? (
            <div className="p-20 bg-white rounded-3xl border-2 border-dashed border-slate-200 text-center text-slate-400">
              No signals detected
            </div>
          ) : (
            articles.map((article) => (
              <article key={article.id} className="bg-white rounded-3xl shadow-sm border border-slate-200 overflow-hidden hover:shadow-md transition-shadow">
                <div className="p-8">
                  <h2 className="text-2xl font-black mb-6 leading-tight tracking-tight text-slate-800">{article.title}</h2>
                  
                  {article.impacted_companies && article.impacted_companies.length > 0 && (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
                      {article.impacted_companies.map((co, i) => {
                        const isPublic = co.ticker && co.ticker.toLowerCase() !== 'none';
                        const tagClasses = isPublic 
                          ? "bg-blue-50 border-blue-100 group hover:border-blue-400 shadow-sm"
                          : "bg-slate-50 border-slate-100 cursor-default opacity-80";
                        
                        return (
                          <div key={i} className={`flex flex-col p-4 rounded-2xl border transition-all ${tagClasses}`}>
                            <div className="flex items-center justify-between mb-2">
                              <div className="flex items-center gap-2">
                                <span className={`font-mono text-[10px] font-black uppercase tracking-tighter ${isPublic ? 'text-blue-600' : 'text-slate-400'}`}>
                                  {isPublic ? co.ticker : 'PRIVATE'}
                                </span>
                                <span className={`font-bold text-xs ${isPublic ? 'text-slate-800' : 'text-slate-500'}`}>
                                  {co.name}
                                </span>
                              </div>
                              <span className={`w-2 h-2 rounded-full ${isPublic ? 'bg-blue-400 animate-pulse' : 'bg-slate-300'}`} />
                            </div>

                            <p className="text-[10px] text-slate-500 leading-snug mb-3 italic">
                              {co.reason}
                            </p>

                            {/* バックエンドで描画済みのHTMLを安全に埋め込む */}
                            {isPublic && co.chartHtml && (
                              <div 
                                className="mt-3 overflow-hidden rounded-xl border border-slate-100 bg-white min-h-[120px]"
                                dangerouslySetInnerHTML={{ __html: co.chartHtml }} 
                              />
                            )}
                            
                            {isPublic && (
                              <a 
                                href={co.ticker.includes('.T') 
                                  ? `https://finance.yahoo.co.jp/quote/${co.ticker}` 
                                  : `https://finance.yahoo.com/quote/${co.ticker}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="mt-2 text-right text-[9px] font-black text-blue-500 hover:text-blue-700 uppercase tracking-widest"
                              >
                                View Details →
                              </a>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}

                  <div className="flex flex-wrap items-center gap-4 mb-8 pt-4 border-t border-slate-50">
                    {article.url && (
                      <a href={article.url} target="_blank" rel="noopener noreferrer"
                         className="bg-slate-900 text-white px-5 py-2 rounded-xl text-[10px] font-black tracking-widest hover:bg-blue-600 transition-colors shadow-sm">
                        READ SOURCE
                      </a>
                    )}
                    <div className="flex items-center gap-2 text-slate-400 text-[10px] font-bold">
                      <span className="opacity-50 tracking-tighter uppercase">Received:</span>
                      <span className="font-mono bg-slate-100 px-2 py-1 rounded text-slate-500">
                        {formatJST(article.created_at)}
                      </span>
                    </div>
                  </div>

                  <div className="bg-slate-50/80 rounded-2xl p-6 md:p-8 border border-slate-100">
                    <div className="prose prose-slate max-w-none text-slate-600 text-sm leading-relaxed prose-strong:text-blue-700 prose-strong:font-black">
                      <ReactMarkdown>{article.analysis}</ReactMarkdown>
                    </div>
                  </div>
                </div>
              </article>
            ))
          )}
        </div>

        <footer className="mt-20 text-center pb-12 border-t border-slate-200 pt-12">
          <p className="text-slate-300 text-[10px] font-bold tracking-[0.5em] uppercase mb-4">Global Pro Maintenance Protocol</p>
          <p className="text-slate-400 text-xs italic">&copy; 2026 Hisao. Market Radar v1.3.</p>
        </footer>
      </div>
    </main>
  );
}
