"""Chấm riêng phần "nhìn bàn": ở mỗi mốc có đáp án, máy nói bàn sạch hay bẩn có đúng không.

Bàn trống (T) là sạch, bàn cần dọn (D) là bẩn; mốc bàn có khách (C) bỏ qua vì lúc đó bàn có đồ ăn là bình thường.
Đọc chi_tiet.json (chạy pipeline với --dump). Lấy kết quả model bàn gần nhất trước mỗi mốc.

    python danh_gia/nhin_ban.py out_v3 [--luat]     # --luat: chấm luật cũ "có đồ trên bàn = bẩn"
"""
import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out', type=Path, nargs='+')
    ap.add_argument('--luat', action='store_true', help='chấm luật đếm đồ thay cho model bàn')
    args = ap.parse_args()
    gt = json.loads((HERE / 'dap_an.json').read_text(encoding='utf-8'))['ban']
    for out in args.out:
        n = ok = n_s = ok_s = n_b = ok_b = 0
        for clip, g in gt.items():
            f = out / clip / 'chi_tiet.json'
            if not f.exists():
                continue
            frames = json.loads(f.read_text(encoding='utf-8'))['khung']
            key = 'do' if args.luat else 'pd'
            for t_str, codes in g['moc'].items():
                t = float(t_str)
                for name, want in zip(g['thu_tu'], codes):
                    if want not in 'TD':
                        continue
                    val = None
                    for k in frames:
                        if k['t'] > t:
                            break
                        v = k['ban'].get(name, {}).get(key)
                        if v is not None:
                            val = v
                    if val is None:
                        continue
                    dirty = val >= 0.5
                    right = dirty == (want == 'D')
                    n += 1
                    ok += right
                    if want == 'T':
                        n_s += 1
                        ok_s += right
                    else:
                        n_b += 1
                        ok_b += right
        print(f'{out.name}: đúng {ok}/{n}  | bàn sạch {ok_s}/{n_s}  | bàn bẩn {ok_b}/{n_b}')


if __name__ == '__main__':
    main()
