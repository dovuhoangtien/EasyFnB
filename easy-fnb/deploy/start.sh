#!/bin/sh
# Khởi động trên Cloud Run. Có BACKUP_BUCKET thì khôi phục dữ liệu từ Cloud Storage trước khi chạy máy chủ,
# rồi sao lưu liên tục: Litestream cho hai file SQLite, sao_luu_tep.py cho config.json và ảnh (ADR-0003).
set -e
export DATA_DIR="${DATA_DIR:-/tmp/easyfnb}"
mkdir -p "$DATA_DIR"
# Thư mục trong bucket; đổi giá trị (biến backup_prefix của Terraform) để bắt đầu lại từ dữ liệu demo.
export BACKUP_PREFIX="${BACKUP_PREFIX:-data}"
SERVER="python -m server --host 0.0.0.0"

if [ -z "$BACKUP_BUCKET" ]; then
  exec $SERVER
fi

for db in timeline.db quan.db; do
  litestream restore -config /app/deploy/litestream.yml -if-db-not-exists -if-replica-exists "$DATA_DIR/$db"
done
python /app/deploy/sao_luu_tep.py restore
python /app/deploy/sao_luu_tep.py sync &
exec litestream replicate -config /app/deploy/litestream.yml -exec "$SERVER"
