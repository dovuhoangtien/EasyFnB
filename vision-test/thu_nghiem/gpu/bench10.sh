#!/bin/bash
# bench10.sh <tên> <số lần> <cờ thêm...>: chạy clip 10 (v4 nhạy + cờ thêm), in fps thật mỗi lần
N="$1"; R="$2"; shift 2
V4="--no-video --hand-model giotay_pe_b16.pt --hand-th 0.35 --staff-model nhanvien_clip_v1.pt --table-model clip --clip-backbone pe_core_s16 --pose-models yolo26n-pose_544x960_fp16.engine --det-models yolo26s_736x1280_fp16.engine --pose-refine rtmpose-m"
for r in $R; do
  ./run_gpu.sh bench/${N}_$r clips/10_thay_the_gio_tay_lop_hoc_a.mp4 $V4 "$@" 2>&1 | grep -a -E "khung/giây|VRAM" | sed "s/^/$N#$r /"
done
