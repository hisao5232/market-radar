import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'export', // これが必須！
  images: {
    unoptimized: true, // 静的書き出しではNext.jsの画像最適化が使えないため
  },
};

export default nextConfig;
