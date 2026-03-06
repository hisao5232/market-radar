FROM python:3.11-slim

WORKDIR /app

# 先にrequirements.txtをコピーしてインストール（キャッシュ効率化）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
