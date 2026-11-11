# Easy FnB: một dịch vụ Cloud Run gồm máy chủ (FastAPI) và web app (React) đã build.
# Build: gcloud run deploy --source .   (Cloud Build tự dùng file này)

# ---- 1. build web app
FROM node:24-slim AS web
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npm run build

# ---- 2. máy chủ
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
# Cloud Run truyền cổng qua biến PORT; server/__main__.py đọc biến này
CMD ["python", "-m", "server", "--host", "0.0.0.0"]
