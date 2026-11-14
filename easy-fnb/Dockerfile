# Easy FnB: một dịch vụ Cloud Run gồm máy chủ (FastAPI) và web app (React) đã build.
# Build: gcloud run deploy --source .   (Cloud Build tự dùng file này)

# ---- 1. build web app
FROM node:24-slim AS web
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npm run build

# ---- 2. Litestream: sao lưu SQLite lên Cloud Storage (deploy/start.sh, ADR-0003)
FROM debian:bookworm-slim AS litestream
ADD https://github.com/benbjohnson/litestream/releases/download/v0.3.13/litestream-v0.3.13-linux-amd64.tar.gz /tmp/ls.tgz
RUN tar -xzf /tmp/ls.tgz -C /usr/local/bin litestream

# ---- 3. máy chủ
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    PIP_NO_CACHE_DIR=1 \
    DATA_DIR=/tmp/easyfnb
WORKDIR /app
COPY server/requirements.txt server/requirements.txt
RUN pip install -r server/requirements.txt
COPY server ./server
COPY --from=web /app/dist ./dist
COPY --from=litestream /usr/local/bin/litestream /usr/local/bin/litestream
COPY deploy ./deploy
RUN sed -i 's/\r$//' deploy/start.sh && chmod +x deploy/start.sh
# Cloud Run truyền cổng qua biến PORT; server/__main__.py đọc biến này. Không có BACKUP_BUCKET thì start.sh chạy thẳng máy chủ.
CMD ["/app/deploy/start.sh"]
