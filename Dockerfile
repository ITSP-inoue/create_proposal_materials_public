# PDF 生成（WeasyPrint）に必要なネイティブ依存をコンテナ内に閉じる
FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY mkdocs.yml ./
COPY docs ./docs
COPY scripts ./scripts
COPY agent ./agent

# ビルドと PDF 生成（実行時に上書きする場合はボリュームマウント）
RUN mkdocs build --strict

CMD ["python", "scripts/html_to_pdf.py", "--site-dir", "site", "--single-document", "-o", "dist/proposal.pdf"]
