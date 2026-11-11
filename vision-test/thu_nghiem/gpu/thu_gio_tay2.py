"""T1 phần CPU: phát lại chi_tiet.json, thử các cách giữ tay hai mức / tích luỹ / đường chỉ RGB.

    python thu_nghiem/gpu/thu_gio_tay2.py thu_nghiem/gpu/out_t1

Chỉ dùng được ph (xác suất giơ tay) của những người pipeline đã hỏi model; bản chạy với --cong-mem hỏi
nhiều người hơn (cổng mềm + người mép hình), nên phát lại trên đầu ra đó bao được mọi biến thể dưới đây.
Đáp án chỉ có 7 lần giơ tay: chọn biến thể theo bảng này là chỉnh theo chính tập test.
"""
import argparse
import json
import sys
import tempfile
from collections import deque
from pathlib import Path

import numpy as np

VT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(VT / 'danh_gia'))
from cham_diem import score_hands  # noqa: E402

TH = 0.35


def simulate2(d, ro_s=0.6, mo_s=1.5, rgb_s=1.0, rgb_th=0.6, weak_th=0.25, ro_fn=None, use_rgb=True,
              use_weak=True, use_mo=True, old_gate_only=False, cooldown=5.0):
    hist, staff_hist, last, ev = {}, {}, {}, []
    for k in d['khung']:
        t = k['t']
        for p in k['nguoi']:
            ph = p['ph']
            nang = p.get('nang')
            if old_gate_only and not (nang is not None and nang > 0.3):
                ph = None  # bỏ ph do cổng mềm/đường RGB mới hỏi
            luat = p['luat']
            up = luat > 0 or (ph or 0) >= TH
            ro = ro_fn(luat, ph) if ro_fn else (luat > 0 and (ph or 0) >= 0.6)
            rgb = use_rgb and p.get('rgb', False) and (ph or 0) >= rgb_th
            weak = (ph or 0) if (nang is not None and nang > 0.3) else 0.0
            q = hist.setdefault(p['id'], deque())
            q.append((t, ro, up, rgb, weak))
            while q and q[0][0] < t - 2.0:
                q.popleft()
            sq = staff_hist.setdefault(p['id'], deque())
            if p.get('pst') is not None:
                sq.append((t, p['pst']))
            while sq and sq[0][0] < t - 3.0:
                sq.popleft()
            staff = bool(sq) and np.mean([v for _, v in sq]) >= 0.5

            def held(sec, j, th):
                if q[-1][0] - q[0][0] < 0.8 * sec:
                    return False
                return np.mean([e[j] for e in q if e[0] >= t - sec]) >= th
            path = None
            if not staff:
                if held(ro_s, 1, 0.7):
                    path = 'ro'
                elif use_mo and held(mo_s, 2, 0.7):
                    path = 'mo_ho'
                elif use_rgb and held(rgb_s, 3, 0.7):
                    path = 'rgb'
                elif use_weak and nang is not None and nang > 0.3 and held(1.0, 4, weak_th):
                    path = 'tich_luy'
            if path and t - last.get(p['id'], -1e9) > cooldown:
                last[p['id']] = t
                ev.append(dict(t=round(t, 2), loai='goi_phuc_vu', box=p['box'], duong=path))
    return ev


BIEN_THE = {
    'v4 (hop: luật hoặc model>=0.35, giữ 0.6 s)': dict(ro_fn=lambda l, ph: l > 0 or (ph or 0) >= TH, use_mo=False,
                                                       use_rgb=False, use_weak=False, old_gate_only=True),
    'v4 + cổng mềm (cùng luật giữ)': dict(ro_fn=lambda l, ph: l > 0 or (ph or 0) >= TH, use_mo=False,
                                          use_rgb=False, use_weak=False),
    'T1 đủ (rõ 0.6 s, mơ hồ 1.5 s, RGB 1.0 s, tích luỹ)': dict(),
    'T1, mơ hồ 2.0 s': dict(mo_s=2.0),
    'T1 bỏ tích luỹ': dict(use_weak=False),
    'T1 bỏ đường RGB': dict(use_rgb=False),
    'T1 chỉ cổng cũ (không cổng mềm, không RGB)': dict(old_gate_only=True, use_rgb=False),
    'rõ = như v4 (0.6 s) + RGB 1.0 s + tích luỹ': dict(ro_fn=lambda l, ph: l > 0 or (ph or 0) >= TH, use_mo=False),
    'v4 + chỉ tích luỹ (cổng cũ, không RGB, không mơ hồ)': dict(ro_fn=lambda l, ph: l > 0 or (ph or 0) >= TH,
                                                            use_mo=False, use_rgb=False, old_gate_only=True),
    'v4 + chỉ tích luỹ, ngưỡng 0.30': dict(ro_fn=lambda l, ph: l > 0 or (ph or 0) >= TH, use_mo=False,
                                           use_rgb=False, old_gate_only=True, weak_th=0.30),
    'v4 + chỉ tích luỹ, ngưỡng 0.20': dict(ro_fn=lambda l, ph: l > 0 or (ph or 0) >= TH, use_mo=False,
                                           use_rgb=False, old_gate_only=True, weak_th=0.20),
    'rõ = như v4 (0.6 s) + RGB 1.0 s': dict(ro_fn=lambda l, ph: l > 0 or (ph or 0) >= TH, use_mo=False,
                                           use_weak=False),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out', type=Path)
    args = ap.parse_args()
    gt = json.loads((VT / 'danh_gia' / 'dap_an.json').read_text(encoding='utf-8'))['gio_tay']
    dumps = {f.parent.name: json.loads(f.read_text(encoding='utf-8')) for f in args.out.glob('*/chi_tiet.json')}
    print(f'{len(dumps)} clip: {sorted(dumps)}\n')
    rows = {}
    for name, kw in BIEN_THE.items():
        with tempfile.TemporaryDirectory() as tmp:
            duong = {}
            for clip, d in dumps.items():
                (Path(tmp) / clip).mkdir()
                ev = simulate2(d, **kw)
                for e in ev:
                    duong[e['duong']] = duong.get(e['duong'], 0) + 1
                (Path(tmp) / clip / 'su_kien.json').write_text(json.dumps({'su_kien': ev}), encoding='utf-8')
            s = score_hands(gt, Path(tmp))
        rows[name] = dict(bat=s['bat_duoc'], tong=s['tong'], nham=s['bao_nham'], tre_tb=s['tre_tb_s'],
                          tre=s['tre_tung_lan'], sot=s['bo_sot'], chi_tiet_nham=s['chi_tiet_nham'], duong=duong)
        print(f"{name:<55} bắt {s['bat_duoc']}/{s['tong']}  nhầm {s['bao_nham']}  trễ tb {s['tre_tb_s']} "
              f"{s['tre_tung_lan']}  đường {duong}")
        print(f"{'':<8}sót {s['bo_sot']}  nhầm {s['chi_tiet_nham']}")
    (args.out / 'thu_gio_tay2.json').write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
