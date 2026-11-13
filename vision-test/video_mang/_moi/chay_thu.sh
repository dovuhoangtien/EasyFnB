# Chạy camera AI (cấu hình v5 như chay_camera.bat) trên từng clip, không gửi máy chủ, kết quả vào out_moi/<clip>/
cd /d/Dev/easy-fnb-workspace/vision-test
export PYTHONIOENCODING=utf-8
PY=~/.easy-fnb/venv/Scripts/python.exe
for c in "$@"; do
  s=$(date +%s)
  $PY easyfnb_test.py "video_mang/_moi/15fps/$c.mp4" --out out_moi --zones video_mang/_moi/zones_moi.json --no-video \
    --hand-model giotay_pe_b16.pt --hand-th 0.35 --staff-model nhanvien_pe_b16.pt \
    --table-model clip --clip-backbone pe_core_s16 \
    --pose-models yolo26n-pose_544x960_fp16.engine --det-models yolo26s_736x1280_fp16.engine \
    --pose-refine rtmpose-m --refine-mode luot --det-every 100 --staff-every 20 --tich-luy --yoloe --hanh-dong \
    > "out_moi/$c.log" 2>&1
  echo "$c xong sau $(( $(date +%s) - s )) s, ma thoat $?"
done
