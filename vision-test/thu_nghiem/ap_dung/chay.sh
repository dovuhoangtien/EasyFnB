#!/bin/bash
# chay.sh <ten_out> <args...>: chạy easyfnb_test.py (bản đã áp dụng) vào thu_nghiem/ap_dung/<ten_out>,
# lấy mẫu VRAM mỗi giây, rồi chấm bằng cham_diem.py và cham_su_kien.py --dap-an-cu.
VT="C:/Users/sosar/AppData/Local/Claude-Data/claude_pzs8sxrjxfjjc/scratch-workspaces/7d58fbbd-096b-4aa8-b0a4-c7271da52073/92788678-51d2-48a1-83fc-577b6251a8c7/scratch-2026-10-31-4fd720/vision-test"
PY="C:/Users/sosar/AppData/Local/Temp/claude/1b786dcbf0e637ab/f67f1de8-0865-4511-a089-2102e7e2e299/scratchpad/venv/Scripts/python.exe"
export PYTHONIOENCODING=utf-8
cd "$VT"
OUT="thu_nghiem/ap_dung/$1"; shift
mkdir -p "$OUT"
nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits > "$OUT/vram_truoc.txt"
nvidia-smi --query-gpu=timestamp,memory.used,utilization.gpu --format=csv,noheader -l 1 > "$OUT/vram.csv" &
SMI=$!
"$PY" ${SCRIPT:-easyfnb_test.py} --out "$OUT" "$@" > "$OUT/log.txt" 2>&1
RC=$?
kill $SMI 2>/dev/null; sleep 1; taskkill //F //IM nvidia-smi.exe >/dev/null 2>&1
echo "rc=$RC"
grep -E "khung/giây|Traceback|Error" "$OUT/log.txt" | head -20
echo "VRAM trước: $(cat $OUT/vram_truoc.txt) MB; đỉnh: $(awk -F', ' '{gsub(/ MiB/,"",$2); v=$2+0; if(v>m)m=v} END{print m}' $OUT/vram.csv) MB"
"$PY" danh_gia/cham_diem.py "$OUT" > "$OUT/cham_diem.txt" 2>&1
"$PY" danh_gia/cham_su_kien.py "$OUT" --dap-an-cu > "$OUT/cham_su_kien.txt" 2>&1
