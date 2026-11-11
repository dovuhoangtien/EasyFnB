"""So hai model nhân viên trên cùng một clip: mỗi người (theo mã bám) một ảnh cắt, kèm điểm trung bình
của từng model, để nhìn bằng mắt ai là nhân viên và model nào tách được.

    python danh_gia/so_nhan_vien.py <video> <out model A> <out model B> <ảnh ra.jpg>
(out model X là thư mục --out của easyfnb_test.py chạy với --dump; mã bám giống nhau vì model
nhân viên không ảnh hưởng tới bám người.)
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np


def doc(out, clip):
    fr = json.loads((Path(out) / clip / 'chi_tiet.json').read_text(encoding='utf-8'))
    fr = fr['khung'] if isinstance(fr, dict) else fr
    diem, khung = defaultdict(list), defaultdict(list)
    for k in fr:
        for p in k['nguoi']:
            khung[p['id']].append((k['t'], p['box']))
            if p['pst'] is not None:
                diem[p['id']].append(p['pst'])
    return diem, khung


def main():
    video, a, b, ra = sys.argv[1:5]
    clip = Path(video).stem
    da, ka = doc(a, clip)
    db, _ = doc(b, clip)
    ids = [i for i in sorted(ka, key=lambda i: -len(ka[i])) if len(ka[i]) >= 30][:16]
    cap = cv2.VideoCapture(video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    zones = json.loads((Path(__file__).parent.parent / 'zones.json').read_text(encoding='utf-8'))
    bo = float(zones.get(clip, {}).get('bat_dau_s', 0))
    o = []
    for i in ids:
        t, box = ka[i][len(ka[i]) // 2]   # giữa đời của người đó
        cap.set(cv2.CAP_PROP_POS_FRAMES, int((t + bo) * fps))
        ok, f = cap.read()
        if not ok:
            continue
        x1, y1, x2, y2 = [int(v) for v in box]
        c = f[max(0, y1):y2, max(0, x1):x2]
        if not c.size:
            continue
        c = cv2.resize(c, (int(160 * c.shape[1] / c.shape[0]) or 1, 160))
        c = cv2.copyMakeBorder(c, 0, 50, 0, max(0, 150 - c.shape[1]), cv2.BORDER_CONSTANT, value=(255, 255, 255))
        ma, mb = np.mean(da[i]) if da[i] else -1, np.mean(db[i]) if db[i] else -1
        cv2.putText(c, f'#{i} t{t:.0f}', (3, 178), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        cv2.putText(c, f'A {ma:.2f} B {mb:.2f}', (3, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 200), 1)
        o.append(c)
        print(f'{clip} #{i}: {len(ka[i])} khung, A {ma:.2f} ({len(da[i])} lần), B {mb:.2f} ({len(db[i])} lần)')
    if o:
        w = max(x.shape[1] for x in o)
        o = [cv2.copyMakeBorder(x, 0, 0, 0, w - x.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255)) for x in o]
        rows = [np.hstack(o[k:k + 8] + [np.full_like(o[0], 255)] * (8 - len(o[k:k + 8]))) for k in range(0, len(o), 8)]
        cv2.imwrite(ra, np.vstack(rows))


if __name__ == '__main__':
    main()
