"use client";
import React from 'react';
import { LineChart, Line, ResponsiveContainer, YAxis } from 'recharts';

export const Sparkline = ({ data }: { data: number[] }) => {
  if (!data || data.length === 0) return <div className="h-10" />;
  const chartData = data.map((val, i) => ({ index: i, value: val }));
  const isUp = data[0] <= data[data.length - 1];

  return (
    <div className="mt-4">
      {/* おしゃれなトレンドラベル */}
      <div className="flex justify-between items-center mb-1">
        <span className="text-[9px] font-black text-slate-400 tracking-widest uppercase opacity-70">
          Trend / Past 7 Days
        </span>
        <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${isUp ? 'bg-emerald-50 text-emerald-600' : 'bg-rose-50 text-rose-600'}`}>
          {isUp ? '▲ UP' : '▼ DOWN'}
        </span>
      </div>
      
      <div className="h-10 w-full opacity-80">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <YAxis domain={['dataMin', 'dataMax']} hide />
            <Line
              type="monotone"
              dataKey="value"
              stroke={isUp ? "#10b981" : "#ef4444"}
              strokeWidth={2.5}
              dot={false}
              isAnimationActive={true}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
