"""Bước 4: vì sao cách so tham chiếu thua? AUC trong từng bàn, ảnh sạch bị chấm "xa" nhất, và ảnh lỗi minh hoạ.

Dùng cách chọn "rai", k = 3, cùng 50 lần rút (hạt giống khác danh_gia.py nhưng cùng cách rút).
Ghi anh_loi/*.jpg: ảnh test | ảnh tham chiếu gần nhất | bản đồ "lạ" của từng vá (đỏ = khác tham chiếu).

    python thu_nghiem/ban_sach_tham_chieu/chan_doan.py
"""
import json

import cv2
import numpy as np
from sklearn.metrics import roc_auc_score

from chung import BANS, HERE, NGUOI_CHE, TEST_DIR, load
from danh_gia import CACH, draws, load as load_all, score

K = 3
OUT = HERE / 'anh_loi'


def heat(img, d, qm, grid):
    m = np.zeros(grid * grid, np.float32)
    m[qm] = d[qm]
    m = cv2.resize(m.reshape(grid, grid), (256, 256), interpolation=cv2.INTER_NEAREST)
    m = np.clip(m / 0.6, 0, 1)
    col = cv2.applyColorMap((m * 255).astype(np.uint8), cv2.COLORMAP_JET)
    return cv2.addWeighted(img, 0.5, col, 0.5, 0)


def label(im, text):
    im = im.copy()
    cv2.rectangle(im, (0, 0), (256, 18), (0, 0, 0), -1)
    cv2.putText(im, text, (3, 13), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1)
    return im


def main():
    Q, P, D = load_all()
    rng = np.random.default_rng(1)
    OUT.mkdir(exist_ok=True)
    rep = {}
    ii = [i for i, q in enumerate(Q) if q['bo'] == 'test' and q['ban'] in BANS]
    for c in CACH:
        sc = {}
        for i in ii:
            q = Q[i]
            d = D[('chat', q['ban'])]
            sc[i] = score(d, d['row'][i], draws(d['ref_t'], q['t'], K, 'rai', rng), c).mean()
        r = {}
        for b in BANS:
            jj = [i for i in ii if Q[i]['ban'] == b]
            y = [Q[i]['y'] for i in jj]
            s = [sc[i] for i in jj]
            r[b] = dict(auc_trong_ban=round(roc_auc_score(y, s), 3),
                        sach_tb=round(float(np.mean([x for x, t in zip(s, y) if t == 0])), 3),
                        sach_max=round(float(np.max([x for x, t in zip(s, y) if t == 0])), 3),
                        ban_tb=round(float(np.mean([x for x, t in zip(s, y) if t == 1])), 3),
                        ban_min=round(float(np.min([x for x, t in zip(s, y) if t == 1])), 3))
        y = [Q[i]['y'] for i in ii]
        r['auc_gop'] = round(roc_auc_score(y, [sc[i] for i in ii]), 3)
        r['sach_xa_nhat'] = [(Q[i]['ten'], round(float(sc[i]), 3)) for i in sorted(ii, key=lambda i: -sc[i])
                             if Q[i]['y'] == 0][:6]
        rep[c] = r
        print(c, json.dumps(r, ensure_ascii=False))
    pr = [(Q[i]['ten'], round(float(P[i]), 3)) for i in range(len(Q)) if Q[i]['bo'] == 'test'
          and (P[i] >= 0.5) != Q[i]['y']]
    print('bộ phân loại sai:', pr)
    rep['phan_loai_sai'] = pr
    (HERE / 'chan_doan.json').write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding='utf-8')

    # ---- ảnh minh hoạ: vá PE lớp giữa, k=1 ảnh tham chiếu gần nhất trong 3 ảnh rút
    def sheet(names, fname, feat='pe_mid', bo='test'):
        rows = []
        for nm in names:
            i = next(i for i, q in enumerate(Q) if q['bo'] == bo and q['ten'] == nm)
            q = Q[i]
            d = D[('chat', q['ban'])]
            r = d['row'][i]
            ok = np.where(np.abs(d['ref_t'] - q['t']) >= 0.999)[0]
            S = np.random.default_rng(2).choice(ok, K, replace=False)
            x = d[f'{feat}_msk'][r][S].astype(np.float32)
            dmin = x.min(0)
            j = S[int(np.argmin(d['G'][r][S]))]
            img = load(TEST_DIR / ('sach' if q['y'] == 0 else 'ban') / f"{nm}.jpg") if bo == 'test' else \
                load(HERE / 'anh' / 'chat' / f'{nm}.jpg')
            ref = load(HERE / 'anh' / 'chat' / f"ref_{q['ban']}_{d['ref_t'][j]:.3f}.jpg")
            qm = d[f'qm_{feat}'][r]
            s = score(d, r, S[None], 'va_pe_giua')[0]
            rows.append(np.hstack([label(img, f"{nm} {'SACH' if q['y'] == 0 else 'BAN'} p_ban={P[i]:.2f}"),
                                   label(ref, f"tham chieu t={d['ref_t'][j]:.2f}s"),
                                   label(heat(img, dmin, qm, 24), f'do la vá={s:.2f}')]))
        cv2.imwrite(str(OUT / fname), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 88])

    worst = [n for n, _ in rep['va_pe_giua']['sach_xa_nhat'][:5]]
    sheet(worst, 'sach_bi_cham_la.jpg')
    sheet(['c01_B1_0.250', 'c01_B2_6.350', 'c01_B4_0.500', 'c01_B4_0.875'], 'ban_vi_du.jpg')
    occ = [f'ref_B1_{t:.3f}' for t in (6.25, 7.625, 7.75)] + ['ref_B2_7.625']
    sheet(occ, 'nguoi_che.jpg', bo='pool')


if __name__ == '__main__':
    main()
