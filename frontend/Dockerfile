# ステージ1: ビルド環境
FROM node:22-alpine AS builder
WORKDIR /app

# 先にpackage.jsonだけコピーしてライブラリをインストール（キャッシュ効かせる）
COPY package*.json ./
RUN npm install --frozen-lockfile

# ソースコードをコピー
COPY . .

# ビルド引数の注入
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

# Next.jsのビルド
RUN npm run build

# ステージ2: 実行環境 (ここが劇的に軽くなる)
FROM node:22-alpine AS runner
WORKDIR /app

# 修正ポイント: next.config.* とすることで .js も .mjs も拾えるようにします
COPY --from=builder /app/next.config.* ./
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

# ポート3000で待機
EXPOSE 3000
CMD ["npm", "start"]
