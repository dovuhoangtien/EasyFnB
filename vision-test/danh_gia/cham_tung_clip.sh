#!/bin/bash
# Chấm bản demo trên 11 clip thử, mỗi clip một tiến trình, crash lúc nạp model thì chạy lại (tối đa 3 lần).
#   bash danh_gia/cham_tung_clip.sh <thư mục out> <tên điểm> [tham số thêm]
# (safetensors trên Windows có lúc crash khi nạp model lúc máy thiếu RAM, xem clip_cls.py)
cd "$(dirname "$0")/.."
export PYTHONIOENCODING=utf-8
PY=~/.easy-fnb/venv/Scripts/python.exe
OUT=$1; TEN=$2; shift 2
for f in clips/*.mp4; do
  for lan in 1 2 3; do
    "$PY" easyfnb_test.py "$f" --out "$OUT" --dump --no-video --hand-model giotay_pe_b16.pt --hand-th 0.35 \
      --staff-model nhanvien_pe_b16.pt --table-model clip --clip-backbone pe_core_s16 \
      --pose-models yolo26n-pose_544x960_fp16.engine --det-models yolo26s_736x1280_fp16.engine \
      --pose-refine rtmpose-m --refine-mode luot --det-every 100 --staff-every 20 --tich-luy --yoloe "$@" \
      > "$OUT.$(basename "$f" .mp4).log" 2>&1 && break
    echo "$(basename "$f"): lần $lan lỗi (mã $?), chạy lại"
  done
  grep -a "khung/giây" "$OUT.$(basename "$f" .mp4).log"
done
"$PY" danh_gia/cham_diem.py "$OUT/" --ten "$TEN"
