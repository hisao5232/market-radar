'use client';

import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { Sparkline } from '../components/MarketDashboard';

interface ImpactedCompany {
  name: string;
  ticker: string;
  reason: string;
  chartHtml?: string;
  debugInfo?: string;
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

export default function Home() {

  const baseUrl =
    process.env.NEXT_PUBLIC_API_URL ||
    'https://radar-api.go-pro-world.net';

  const apiKey =
    process.env.NEXT_PUBLIC_API_KEY ||
    'hisao_secure_radar_2026';

  const [articles, setArticles] = useState<Article[]>([]);
  const [market, setMarket] = useState<MarketData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [debug, setDebug] = useState<string>("");

  useEffect(() => {

    const fetchWithTimeout = async (url: string, timeout = 8000) => {
      const controller = new AbortController();
      const id = setTimeout(() => controller.abort(), timeout);

      const res = await fetch(url, { signal: controller.signal });
      clearTimeout(id);
      return res;
    };

    const fetchData = async () => {

      try {

        setLoading(true);

        /* ---------- 基本データ取得 ---------- */

        const [articlesRes, marketRes] = await Promise.all([
          fetchWithTimeout(`${baseUrl}/articles?limit=20&api_key=${apiKey}`),
          fetchWithTimeout(`${baseUrl}/market-summary?api_key=${apiKey}`)
        ]);

        if (!articlesRes.ok)
          throw new Error(`Articles API Status: ${articlesRes.status}`);

        const fetchedArticles: Article[] = await articlesRes.json();

        if (marketRes.ok) {
          const marketData = await marketRes.json();
          setMarket(marketData);
        }

        setDebug(`
API OK
articles: ${fetchedArticles.length}
baseUrl: ${baseUrl}
apiKey: ${apiKey}
`);

        /* ---------- chart API負荷制限 ---------- */

        const limitedArticles = fetchedArticles.slice(0, 8);

        const updatedArticles = await Promise.all(

          limitedArticles.map(async (article) => {

            if (!article.impacted_companies)
              return article;

            const updatedCompanies = await Promise.all(

              article.impacted_companies.map(async (co) => {

                const isPublic =
                  co.ticker &&
                  co.ticker.toLowerCase() !== 'none';

                if (!isPublic)
                  return co;

                try {

                  const chartRes = await fetchWithTimeout(
                    `${baseUrl}/stock-chart/${co.ticker}?api_key=${apiKey}`
                  );

                  if (!chartRes.ok) {

                    return {
                      ...co,
                      chartHtml: "",
                      debugInfo: `HTTP ${chartRes.status}`
                    };

                  }

                  const chartHtml = await chartRes.text();

                  return {
                    ...co,
                    chartHtml,
                    debugInfo: `OK ${chartHtml.length}`
                  };

                } catch {

                  return {
                    ...co,
                    chartHtml: "",
                    debugInfo: "fetch failed"
                  };

                }

              })

            );

            return {
              ...article,
              impacted_companies: updatedCompanies
            };

          })

        );

        setArticles(updatedArticles);

      } catch (err: any) {

        setError(err.message);

        setDebug(`
FETCH ERROR
${err.message}
baseUrl: ${baseUrl}
`);

      } finally {

        setLoading(false);

      }

    };

    fetchData();

  }, [baseUrl, apiKey]);

  return (
    <main className="min-h-screen bg-slate-50 p-6 md:p-12 font-sans text-slate-900">

      <div className="max-w-4xl mx-auto">

        {/* ---------- HEADER ---------- */}

        <header className="mb-12 border-b-2 border-slate-200 pb-8">

          <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">

            <div>
              <h1 className="text-4xl font-black tracking-tighter italic">
                MARKET RADAR
                <span className="text-blue-600 not-italic"> v1.3</span>
              </h1>

              <p className="text-slate-500 font-medium">
                2026 AI-Driven Market Intelligence
              </p>
            </div>

            {(error || loading) && (
              <div
                className={`text-[10px] font-mono p-3 rounded-lg border
                ${error
                    ? 'bg-red-50 text-red-600'
                    : 'bg-blue-50 text-blue-600 animate-pulse'
                  }`}
              >
                {error
                  ? `[SYSTEM_ALERT]: ${error}`
                  : '[SCANNING_MARKETS...]'}
              </div>
            )}

          </div>

          {/* ---------- MARKET ---------- */}

          {market && (

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-8">

              {[
                { label: "日経平均", data: market.nikkei, unit: "円" },
                { label: "USD/JPY", data: market.usdjpy, unit: "円", fixed: 2 },
                { label: "オルカン", data: market.orukan, unit: "円" }
              ].map((item, idx) => (

                <div
                  key={idx}
                  className="bg-white p-5 rounded-2xl shadow-sm border"
                >

                  <p className="text-[10px] text-slate-400 mb-1 uppercase">
                    {item.label}
                  </p>

                  <p className="text-2xl font-black">

                    {item.data?.current
                      ? (item.fixed
                        ? item.data.current.toFixed(item.fixed)
                        : item.data.current.toLocaleString())
                      : "---"}

                    <span className="text-sm text-slate-300 ml-1">
                      {item.unit}
                    </span>

                  </p>

                  <Sparkline data={item.data?.history || []} />

                </div>

              ))}

            </div>

          )}

        </header>

        {/* ---------- DEBUG ---------- */}

        {debug && (
          <div className="bg-black text-green-400 text-xs p-3 rounded font-mono whitespace-pre-wrap mb-6">
            {debug}
          </div>
        )}

        {/* ---------- ARTICLES ---------- */}

        <div className="space-y-8">

          {articles.map((article) => (

            <article
              key={article.id}
              className="bg-white rounded-3xl shadow-sm border"
            >

              <div className="p-8">

                <h2 className="text-2xl font-black mb-6">
                  {article.title}
                </h2>

                {article.impacted_companies?.map((co, i) => (

                  <div key={i} className="mb-4 border rounded-xl p-4">

                    <div className="text-xs font-bold mb-1">
                      {co.ticker}
                    </div>

                    <div className="text-xs text-slate-500 mb-2">
                      {co.reason}
                    </div>

                    {co.debugInfo && (
                      <div className="text-[10px] font-mono text-slate-400">
                        API: {co.debugInfo}
                      </div>
                    )}

                    {co.chartHtml && (

                      <iframe
                        srcDoc={co.chartHtml}
                        className="w-full h-[180px] border-none"
                        sandbox="allow-scripts"
                      />

                    )}

                  </div>

                ))}

                <ReactMarkdown>
                  {article.analysis}
                </ReactMarkdown>

              </div>

            </article>

          ))}

        </div>

      </div>

    </main>
  );
}
