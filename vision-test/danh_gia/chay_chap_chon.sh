#!/bin/bash
# Chạy bản demo trên bộ clip đo chập chờn rồi in số đo.  danh_gia/chay_chap_chon.sh <thư mục out> [tham số thêm]
# Crash lúc nạp model (safetensors thiếu RAM, xem clip_cls.py) thì chạy lại clip đó, tối đa 3 lần.
cd "$(dirname "$0")/.."
export PYTHONIOENCODING=utf-8
PY=~/.easy-fnb/venv/Scripts/python.exe
OUT=$1; shift
for f in video_mang/m01_bbq_vn_ban_an.mp4 video_mang/m02_bbq_han_dong_khach.mp4 video_mang/m03_cafe_san_vuon_vn.mp4 video_mang/m04_cafe_quay_pa.mp4 clips/04_phuc_vu_toi_khach_moi.mp4 clips/06_phuc_vu_ghi_order.mp4 $CLIP_THEM; do
  for lan in 1 2 3; do
    "$PY" easyfnb_test.py "$f" --out "$OUT" --dump --no-video --hand-model giotay_pe_b16.pt --hand-th 0.35 \
      --staff-model nhanvien_pe_b16.pt --table-model clip --clip-backbone pe_core_s16 \
      --pose-models yolo26n-pose_544x960_fp16.engine --det-models yolo26s_736x1280_fp16.engine \
      --pose-refine rtmpose-m --refine-mode luot --det-every 100 --staff-every 20 --tich-luy --yoloe "$@" \
      > "$OUT.log.tmp" 2>&1 && break
    echo "$(basename "$f"): lần $lan crash, chạy lại"
  done
  grep -a -E "khung/giây|^ +[0-9.]+s " "$OUT.log.tmp"
done
rm -f "$OUT.log.tmp"
"$PY" danh_gia/do_chap_chon.py "$OUT"
