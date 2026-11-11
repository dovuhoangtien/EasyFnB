#!/bin/bash
cd "$(dirname "$0")"
for r in 1 2 3; do
  ./bench10.sh A_v4nhay $r --refine-mode tat_ca
  ./bench10.sh B_t2a $r --refine-mode tat_ca --det-every 100 --table-every 20 --staff-every 20
  ./bench10.sh C_ungvien $r --refine-mode ung_vien --det-every 100 --staff-every 20
  ./bench10.sh D_luot $r --refine-mode luot --det-every 100 --staff-every 20
  ./bench10.sh E_t1day $r --refine-mode tat_ca --cong-mem
  ./bench10.sh F_t1tichluy $r --refine-mode tat_ca --tich-luy
  ./bench10.sh G_dexuat $r --refine-mode luot --det-every 100 --staff-every 20 --tich-luy
done
echo BENCH_XONG
