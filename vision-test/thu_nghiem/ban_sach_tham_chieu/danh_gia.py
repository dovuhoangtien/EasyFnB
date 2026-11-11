"""Bước 3: chấm các cách "so với ảnh bàn sạch tham chiếu" và so với bộ phân loại hiện tại (PE-Core S/16 không train).

Cách chọn ảnh tham chiếu cho mỗi ảnh test (không bao giờ là chính ảnh đó, luôn cách thời điểm ảnh test >= 1 s):
  rai     : k ảnh lấy ngẫu nhiên trong các khung T sạch của cùng bàn (50 lần rút), như bấm "Chụp bàn sạch" vài lần
            vào các lúc khác nhau.
  mot_lan : k khung liền nhau (cách 0,125 s) từ MỘT lần bấm; thử mọi thời điểm bấm hợp lệ. Bi quan hơn: bàn có thể
            được bày lại khác đi sau lần bấm (đặt ly, trải khăn).
Ngưỡng: chọn theo kiểu chừa một bàn (leave-one-table-out): ngưỡng cho bàn B1 chỉ học từ ảnh test của B2 và B4, v.v.
Bộ phân loại hiện tại giữ ngưỡng 0,5 như trong pipeline.

    python thu_nghiem/ban_sach_tham_chieu/danh_gia.py
"""
import json
from math import comb

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

from chung import BANS, CACHE, HERE, NGUOI_CHE

N_RUT = 50
KS = (1, 3, 5)
CACH = {  # tên: (đặc trưng, bộ nhớ vá, chỉ chấm vá trên mặt bàn)
    'toan_anh': ('G', None, None),
    'va_pe_cuoi': ('pe_last', 'msk', True),
    'va_pe_giua': ('pe_mid', 'msk', True),
    'va_dino': ('dino', 'msk', True),
    'va_dino_tron': ('dino', 'all', False),  # AnomalyDINO nguyên bản: cả ảnh, không mặt nạ bàn
}


def load():
    Q = json.loads((CACHE / 'queries.json').read_text(encoding='utf-8'))
    F = np.load(CACHE / 'feat.npz')
    D = {}
    for v in ('chat', 'vuong'):
        for b in BANS:
            z = np.load(CACHE / f'D_{v}_{b}.npz')
            D[(v, b)] = {k: z[k] for k in z.files}
            D[(v, b)]['row'] = {int(q): r for r, q in enumerate(z['qi'])}
    return Q, F['p'], D


def draws(ref_t, t, k, mode, rng):
    ok = np.where(np.abs(ref_t - t) >= 0.999)[0]
    if mode == 'rai':
        return np.stack([rng.choice(ok, k, replace=False) for _ in range(N_RUT)])
    out = []
    for s in range(len(ref_t) - k + 1):
        idx = np.arange(s, s + k)
        if np.all(np.isin(idx, ok)) and ref_t[idx[-1]] - ref_t[idx[0]] <= 0.126 * (k - 1) + 1e-6:
            out.append(idx)
    return np.stack(out)


def score(d, r, S, cach):
    feat, bank, qmask = CACH[cach]
    if feat == 'G':
        return d['G'][r][S].astype(np.float32).min(1)
    x = d[f'{feat}_{bank}'][r][S].astype(np.float32).min(1)  # [rút, vá]
    if qmask:
        x = x[:, d[f'qm_{feat}'][r]]
    n = max(1, int(np.ceil(0.01 * x.shape[1])))
    return -np.sort(-x, 1)[:, :n].mean(1)


def best_thr(s, y, w):
    o = np.argsort(s)
    s, y, w = s[o], y[o], w[o]
    # dự đoán bẩn khi s > ngưỡng; thử mọi điểm cắt
    acc_cut = np.r_[0, np.cumsum(w * (y == 0))] + np.r_[np.cumsum((w * (y == 1))[::-1])[::-1], 0]
    i = int(np.argmax(acc_cut))
    lo = s[i - 1] if i > 0 else s[0] - 1e-3
    hi = s[i] if i < len(s) else s[-1] + 1e-3
    return (lo + hi) / 2


def mcnemar(ok_old, ok_new):
    b = int((ok_new & ~ok_old).sum())
    c = int((ok_old & ~ok_new).sum())
    n = b + c
    p = min(1.0, 2 * sum(comb(n, i) for i in range(0, min(b, c) + 1)) / 2 ** n) if n else 1.0
    return b, c, p


def logit(p):
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def main():
    Q, P, D = load()
    rng = np.random.default_rng(0)
    res = {}
    sets = {'test': 'chat', 'vuong': 'vuong', 'pool': 'chat', **{f'as_{k}': 'chat' for k in
                                                                   ('toi_60', 'sang_140', 'den_vang', 'toi_vang')}}
    idx = {s: [i for i, q in enumerate(Q) if q['bo'] == s and q['ban'] in BANS] for s in sets}
    test_all = [i for i, q in enumerate(Q) if q['bo'] == 'test']
    no_ref = [i for i in test_all if Q[i]['ban'] not in BANS]
    y_all = np.array([Q[i]['y'] for i in test_all])
    ok_cls_all = (P[test_all] >= 0.5) == y_all
    print(f"Bộ phân loại hiện tại (PE-Core S/16, ngưỡng 0,5): {ok_cls_all.sum()}/91; trên 78 ảnh bàn có tham chiếu: "
          f"{((P[idx['test']] >= 0.5) == np.array([Q[i]['y'] for i in idx['test']])).sum()}/78")
    # ---- tính điểm cho mọi (ảnh, lần rút)
    # Chuẩn hoá theo từng bàn, chỉ dùng chính các ảnh tham chiếu (không cần nhãn): chia điểm cho khoảng cách trung bình
    # giữa hai ảnh tham chiếu của bàn đó. pair[(b, c)][m, n] = điểm của ảnh tham chiếu m khi chỉ so với ảnh tham chiếu n.
    pair = {}
    for b in BANS:
        d = D[('chat', b)]
        rows = {Q[i]['t']: r for i, r in d['row'].items() if Q[i]['bo'] == 'pool'}
        rr = [rows[t] for t in d['ref_t']]
        nr = len(rr)
        for c in CACH:
            pair[(b, c)] = np.stack([score(d, rr[m], np.arange(nr)[:, None], c) for m in range(nr)])
    S = {}  # (mode, k, cach, set) -> list theo ảnh của mảng điểm
    for mode in ('rai', 'mot_lan'):
        for k in KS:
            for sname, v in sets.items():
                if mode == 'mot_lan' and sname not in ('test', 'vuong'):
                    continue
                norm = v == 'chat' and k > 1
                for c in CACH:
                    S[(mode, k, c, sname)] = []
                    if norm:
                        S[(mode, k, c + '/chuan', sname)] = []
                for i in idx[sname]:
                    q = Q[i]
                    d = D[(v, q['ban'])]
                    Sx = draws(d['ref_t'], q['t'], k, mode, rng)
                    for c in CACH:
                        s = score(d, d['row'][i], Sx, c)
                        S[(mode, k, c, sname)].append(s)
                        if norm:
                            pm = pair[(q['ban'], c)]
                            den = np.array([(pm[np.ix_(x, x)].sum()) / (k * (k - 1)) for x in Sx])
                            S[(mode, k, c + '/chuan', sname)].append(s / np.maximum(den, 1e-3))
    # ---- ngưỡng chừa một bàn + kết hợp
    out_rows = []
    for (mode, k, c, sname), sc in S.items():
        cal_set = 'vuong' if sname == 'vuong' else 'test'
        cal = S[(mode, k, c, cal_set)]
        ci = idx[cal_set]
        ii = idx[sname]
        y = np.array([Q[i]['y'] for i in ii])
        thr, lr = {}, {}
        for b in BANS:
            tr = [j for j, i in enumerate(ci) if Q[i]['ban'] != b]
            s_tr = np.concatenate([cal[j] for j in tr])
            y_tr = np.concatenate([np.full(len(cal[j]), Q[ci[j]]['y']) for j in tr])
            w_tr = np.concatenate([np.full(len(cal[j]), 1 / len(cal[j])) for j in tr])
            p_tr = np.concatenate([np.full(len(cal[j]), P[ci[j]]) for j in tr])
            thr[b] = best_thr(s_tr, y_tr, w_tr)
            lr[b] = LogisticRegression(C=1.0, max_iter=2000).fit(
                np.c_[logit(p_tr), s_tr / thr[b]], y_tr, sample_weight=w_tr)
        # đúng/sai theo từng ảnh, từng lần rút
        ok_ref, ok_tb, ok_lr = [], [], []
        for j, i in enumerate(ii):
            b, s = Q[i]['ban'], sc[j]
            ok_ref.append((s > thr[b]) == y[j])
            tb = 0.5 * P[i] / 0.5 + 0.5 * s / thr[b]
            ok_tb.append((tb > 1) == y[j])
            pl = lr[b].predict_proba(np.c_[np.full(len(s), logit(P[i])), s / thr[b]])[:, 1]
            ok_lr.append((pl >= 0.5) == y[j])
        for name, ok in ((c, ok_ref), (c + '+pl_tb', ok_tb), (c + '+pl_lr', ok_lr)):
            exp = np.array([o.mean() for o in ok])
            row = dict(cach_chon=mode, k=k, cach=name, bo=sname, n=len(ii),
                       dung=round(float(exp.sum()), 1),
                       sach_dung=round(float(exp[y == 0].sum()), 1), n_sach=int((y == 0).sum()),
                       ban_dung=round(float(exp[y == 1].sum()), 1), n_ban=int((y == 1).sum()),
                       bao_nham_ban=round(float((1 - exp[y == 0]).sum()), 1),
                       sot_ban=round(float((1 - exp[y == 1]).sum()), 1))
            for b in BANS:
                m = np.array([Q[i]['ban'] == b for i in ii])
                row[f'dung_{b}'] = round(float(exp[m].sum()), 1)
                row[f'n_{b}'] = int(m.sum())
            if '+' not in name and sname in ('test', 'vuong'):
                if mode == 'rai':
                    row['auc'] = round(float(np.mean([roc_auc_score(y, [sc[j][r] for j in range(len(ii))])
                                                      for r in range(N_RUT)])), 3)
                else:
                    row['auc'] = round(float(roc_auc_score(np.concatenate([np.full(len(s), y[j]) for j, s in enumerate(sc)]),
                                                           np.concatenate(sc),
                                                           sample_weight=np.concatenate([np.full(len(s), 1 / len(s)) for s in sc]))), 3)
            if sname == 'pool':
                occ = np.array([Q[i]['t'] in NGUOI_CHE[Q[i]['ban']] for i in ii])
                row['bao_nham_khi_nguoi_che'] = round(float((1 - exp[occ]).sum()), 1)
                row['n_nguoi_che'] = int(occ.sum())
                row['bao_nham_khi_khong_che'] = round(float((1 - exp[~occ]).sum()), 1)
                row['n_khong_che'] = int((~occ).sum())
            # cả 91 ảnh (ảnh không có tham chiếu: B3 và clip 03 dùng bộ phân loại) + McNemar với bộ phân loại
            if sname == 'test' and mode == 'rai':
                pos = {i: j for j, i in enumerate(ii)}
                tot, bs, cs, ps = [], [], [], []
                for r in range(N_RUT):
                    okr = np.array([ok[pos[i]][r] if i in pos else ok_cls_all[n] for n, i in enumerate(test_all)])
                    tot.append(okr.sum())
                    b_, c_, p_ = mcnemar(ok_cls_all, okr)
                    bs.append(b_), cs.append(c_), ps.append(p_)
                row.update(dung_91=round(float(np.mean(tot)), 1), dung_91_min=int(min(tot)), dung_91_max=int(max(tot)),
                           mcnemar_moi_dung_cu_sai=round(float(np.mean(bs)), 1),
                           mcnemar_cu_dung_moi_sai=round(float(np.mean(cs)), 1),
                           mcnemar_p_trung_vi=round(float(np.median(ps)), 3),
                           ty_le_lan_rut_p_duoi_005=round(float(np.mean(np.array(ps) < 0.05)), 2))
            out_rows.append(row)
    # ---- bộ phân loại trên các bộ ảnh phụ
    cls = {}
    for sname in sets:
        ii = idx[sname]
        y = np.array([Q[i]['y'] for i in ii])
        pr = P[ii] >= 0.5
        cls[sname] = dict(dung=int((pr == y).sum()), n=len(ii), bao_nham_ban=int((pr & (y == 0)).sum()),
                          sot_ban=int((~pr & (y == 1)).sum()))
        if sname == 'pool':
            occ = np.array([Q[i]['t'] in NGUOI_CHE[Q[i]['ban']] for i in ii])
            cls[sname].update(bao_nham_khi_nguoi_che=int(pr[occ].sum()), n_nguoi_che=int(occ.sum()),
                              bao_nham_khi_khong_che=int(pr[~occ].sum()), n_khong_che=int((~occ).sum()))
        if sname in ('test', 'vuong'):
            cls[sname]['auc'] = round(float(roc_auc_score(y, P[ii])), 3)
            for b in BANS:
                m = np.array([Q[i]['ban'] == b for i in ii])
                cls[sname][f'dung_{b}'] = int((pr[m] == y[m]).sum())
    no_ref_ok = int(ok_cls_all[[test_all.index(i) for i in no_ref]].sum())
    res = dict(phan_loai=cls, khong_tham_chieu=dict(n=len(no_ref), dung=no_ref_ok), ket_qua=out_rows)
    (HERE / 'ket_qua.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
    # ---- in gọn
    print('phân loại:', json.dumps(cls, ensure_ascii=False))
    print('ảnh không có tham chiếu (B3 + clip 03):', no_ref_ok, '/', len(no_ref))
    for r in out_rows:
        if r['bo'] == 'test':
            print(f"{r['cach_chon']:7s} k={r['k']} {r['cach']:22s} 78: {r['dung']:5.1f} (sạch {r['sach_dung']:4.1f}/59 "
                  f"bẩn {r['ban_dung']:4.1f}/19) auc {r.get('auc', '-')}"
                  + (f" | 91: {r['dung_91']} [{r['dung_91_min']}-{r['dung_91_max']}] McN +{r['mcnemar_moi_dung_cu_sai']}"
                     f"/-{r['mcnemar_cu_dung_moi_sai']} p~{r['mcnemar_p_trung_vi']}" if 'dung_91' in r else ''))


if __name__ == '__main__':
    main()
