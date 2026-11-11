"""T5 bước 2: chạy blur_faces trên ~100 khung mẫu, đo tốc độ, tay giơ bị mờ, ghép ảnh trước/sau để xem bằng mắt.

    python danh_gia.py            # đọc _cache/khung_xuong.json (từ lay_khung_xuong.py)
"""
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from lam_mo_mat import HEAD, LEL, LSH, LWR, REL, RSH, RWR, blur_faces, head_ellipse  # noqa: E402

VT = HERE.parents[1]
CACHE = HERE / '_cache'
OUT = HERE / 'anh'
OUT.mkdir(exist_ok=True)
MODE = sys.argv[1] if len(sys.argv) > 1 else 'pixel'

rows = json.loads((CACHE / 'khung_xuong.json').read_text(encoding='utf-8'))
labels = json.loads((VT / 'danh_gia' / 'dap_an.json').read_text(encoding='utf-8'))['gio_tay']

# ---------------------------------------------------------------- tốc độ
ms, ms_inplace, npeople = [], [], []
frames = {}
for r in rows:
    img = cv2.imread(str(CACHE / f"{r['name']}.jpg"))
    frames[r['name']] = img
    kp, kc, bx = np.array(r['kp']).reshape(-1, 17, 2), np.array(r['kc']).reshape(-1, 17), np.array(r['boxes']).reshape(-1, 4)
    for _ in range(3):
        blur_faces(img, kp, kc, bx, mode=MODE)
    t0 = time.perf_counter()
    for _ in range(20):
        blur_faces(img, kp, kc, bx, mode=MODE)
    ms.append((time.perf_counter() - t0) / 20 * 1000)
    buf = img.copy()
    t0 = time.perf_counter()
    for _ in range(20):
        blur_faces(buf, kp, kc, bx, mode=MODE, inplace=True)
    ms_inplace.append((time.perf_counter() - t0) / 20 * 1000)
    npeople.append(len(bx))
ms, ms_inplace, npeople = map(np.array, (ms, ms_inplace, npeople))
le10 = npeople <= 10
speed = dict(khung=len(ms), nguoi_tb=round(float(npeople.mean()), 1), nguoi_max=int(npeople.max()),
             ms_tb_copy=round(float(ms.mean()), 3), ms_p95_copy=round(float(np.percentile(ms, 95)), 3),
             ms_max_copy=round(float(ms.max()), 3),
             ms_tb_inplace=round(float(ms_inplace.mean()), 3), ms_p95_inplace=round(float(np.percentile(ms_inplace, 95)), 3),
             ms_tb_le10=round(float(ms_inplace[le10].mean()), 3))
print('toc do', speed)

# ---------------------------------------------------------------- chạy, ghép ảnh
src_count = {'kp': 0, 'vai': 0, 'box': 0}
tiles = []          # (clip, idx, tile)  đầu từng người trước|sau
hand_inst = []      # tay giơ: theo nhãn và theo khung xương
for r in rows:
    img = frames[r['name']]
    kp, kc, bx = np.array(r['kp']).reshape(-1, 17, 2), np.array(r['kc']).reshape(-1, 17), np.array(r['boxes']).reshape(-1, 4)
    out, mask = blur_faces(img, kp, kc, bx, mode=MODE, return_mask=True)
    H, W = img.shape[:2]
    # ảnh cả khung trước/sau (thu nhỏ) cho vài khung
    both = np.hstack([img, out])
    cv2.imwrite(str(OUT / f"khung_{r['name']}.jpg"), cv2.resize(both, (both.shape[1] // 2, both.shape[0] // 2)),
                [cv2.IMWRITE_JPEG_QUALITY, 80])
    lab = [l for l in labels.get(r['clip'], []) if l['tu'] <= r['t'] <= l['den']]
    for k, (p, c, b) in enumerate(zip(kp, kc, bx)):
        e = head_ellipse(p, c, b, img_wh=(W, H))
        if e is None:
            src_count['bo_qua'] = src_count.get('bo_qua', 0) + 1
            e = (0, 0, 0, 0, 'bo_qua')
        else:
            src_count[e[4]] += 1
        cx, cy, a, bb, src = e
        s = max(a, bb) * 1.9
        if src == 'bo_qua':
            s = 0
        x0, y0, x1, y1 = int(max(0, cx - s)), int(max(0, cy - s)), int(min(W, cx + s)), int(min(H, cy + s))
        if x1 - x0 > 4 and y1 - y0 > 4:
            bef = img[y0:y1, x0:x1].copy()
            cv2.ellipse(bef, (int(cx - x0), int(cy - y0)), (int(a), int(bb)), 0, 0, 360, (0, 255, 0), 1)
            pair = np.hstack([cv2.resize(bef, (128, 128)), cv2.resize(out[y0:y1, x0:x1], (128, 128))])
            cv2.putText(pair, f"{r['name']}#{k}{src[0]}", (2, 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 255), 1)
            tiles.append(pair)
        # tay giơ: cổ tay cao hơn vai rõ (theo khung xương), hoặc người nằm trong vùng x của nhãn
        sh = [p[i][1] for i in (LSH, RSH) if c[i] >= 0.3]
        ref = abs(p[LSH][0] - p[RSH][0]) if c[LSH] >= 0.3 and c[RSH] >= 0.3 else 0.3 * (b[2] - b[0])
        ref = max(ref, 0.1 * (b[3] - b[1]))
        cxb = (b[0] + b[2]) / 2
        in_lab = [l for l in lab if l['x'][0] - 40 <= cxb <= l['x'][1] + 40]
        for el, wr in ((LEL, LWR), (REL, RWR)):
            if c[wr] < 0.3 or not sh:
                continue
            lift = (min(sh) - p[wr][1]) / ref
            if lift < 0.6:
                continue
            w = p[wr]
            tip = w + 0.45 * (w - p[el]) if c[el] >= 0.3 else w - np.array([0, 0.3 * ref])
            hm = np.zeros((H, W), np.uint8)
            rr = max(3, int(0.25 * ref))
            cv2.line(hm, tuple(map(int, w)), tuple(map(int, tip)), 255, 2 * rr)
            frac = float((mask[hm > 0] > 0).mean()) if (hm > 0).any() else 0.0
            hx0, hy0 = int(max(0, min(w[0], tip[0]) - 3 * rr)), int(max(0, min(w[1], tip[1]) - 3 * rr))
            hx1, hy1 = int(min(W, max(w[0], tip[0]) + 3 * rr)), int(min(H, max(w[1], tip[1]) + 3 * rr))
            hand_inst.append(dict(khung=r['name'], nguoi=k, nhan=in_lab[0]['ai'] if in_lab else None,
                                  nang=round(float(lift), 2), ti_le_mo=round(frac, 3),
                                  anh=(img[hy0:hy1, x0 if False else hx0:hx1], out[hy0:hy1, hx0:hx1])))

# lưới đầu người: 6 cột x 8 hàng mỗi tờ
per = 48
for s in range(0, len(tiles), per):
    chunk = tiles[s:s + per]
    while len(chunk) % 6:
        chunk.append(np.zeros_like(tiles[0]))
    grid = np.vstack([np.hstack(chunk[i:i + 6]) for i in range(0, len(chunk), 6)])
    cv2.imwrite(str(OUT / f"luoi_dau_{s // per:02d}.jpg"), grid, [cv2.IMWRITE_JPEG_QUALITY, 88])

# lưới tay giơ
ht = []
for h in hand_inst:
    a, b = h['anh']
    if a.size == 0:
        continue
    pair = cv2.resize(np.hstack([a, b]), (160, 80))
    cv2.putText(pair, f"{h['khung']}#{h['nguoi']} {h['ti_le_mo']:.2f}", (2, 10), cv2.FONT_HERSHEY_SIMPLEX, 0.3,
                (0, 255, 255), 1)
    ht.append(pair)
for s in range(0, len(ht), 48):
    chunk = ht[s:s + 48]
    while len(chunk) % 6:
        chunk.append(np.zeros_like(ht[0]))
    grid = np.vstack([np.hstack(chunk[i:i + 6]) for i in range(0, len(chunk), 6)])
    cv2.imwrite(str(OUT / f"luoi_tay_{s // 48:02d}.jpg"), grid, [cv2.IMWRITE_JPEG_QUALITY, 88])

for h in hand_inst:
    h.pop('anh')
n_hand = len(hand_inst)
n_lab = [h for h in hand_inst if h['nhan']]
res = dict(che_do=MODE, toc_do=speed, nguon_elip=src_count, so_nguoi=sum(src_count.values()),
           tay_gio=dict(tong=n_hand, bi_mo_tren_10pct=sum(h['ti_le_mo'] > 0.10 for h in hand_inst),
                        bi_mo_bat_ky=sum(h['ti_le_mo'] > 0 for h in hand_inst),
                        theo_nhan=len(n_lab), theo_nhan_bi_mo_tren_10pct=sum(h['ti_le_mo'] > 0.10 for h in n_lab)),
           tay_chi_tiet=hand_inst)
(HERE / f'ket_qua_{MODE}.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
print(json.dumps({k: v for k, v in res.items() if k != 'tay_chi_tiet'}, ensure_ascii=False, indent=1))
print('so o dau', len(tiles), 'so o tay', len(ht))
