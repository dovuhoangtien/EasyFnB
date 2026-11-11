"""Chấm luật "bàn bẩn nếu thấy đồ trong danh sách với conf >= x" trên 91 ảnh bàn (59 sạch, 32 bẩn).

Đọc ket_qua/phat_hien.json (chay_yoloe.py) và ket_qua/pe_core_s16_91.json (pe_core_tung_anh.py).
In bảng và ghi ket_qua/diem_91.json.

Ngưỡng báo cáo chính: 0,25 (mặc định của Ultralytics và của pipeline), chọn TRƯỚC khi xem điểm.
Cột "tốt nhất" quét ngưỡng trên chính 91 ảnh nên đẹp hơn thực tế; AUC không cần ngưỡng.
"""
import json
from collections import Counter

import numpy as np

from chay_yoloe import test_items
from chung import CACHE, COCO_ITEMS, RULE, iou

# Luật cho bản không câu nhắc (-pf, 4.585 tên có sẵn): các tên cùng nghĩa với RULE, đặt trước khi xem kết quả
PF_RULE = {'plate', 'dish', 'bowl', 'cup', 'mug', 'coffee cup', 'teacup', 'glass', 'wine glass', 'drinking glass',
           'beer glass', 'bottle', 'water bottle', 'beer bottle', 'wine bottle', 'chopsticks', 'napkin', 'tissue',
           'paper towel', 'tray', 'food', 'leftover', 'snack', 'meal', 'dessert', 'candy', 'can', 'drink',
           'beverage', 'saucer'}
TH_MAIN = 0.25
SNAP_DAU = {'B1': 'sach/c01_B1_1.250', 'B2': 'sach/c01_B2_7.250', 'B4': 'sach/c01_B4_1.250'}   # ảnh sạch đầu tiên
SNAP_CUOI = {'B1': 'sach/c01_B1_14.750', 'B2': 'sach/c01_B2_14.750', 'B4': 'sach/c01_B4_8.250'}  # ảnh sạch cuối


def rule_of(cfg):
    if cfg.startswith('coco'):
        return set(COCO_ITEMS.values())
    if cfg.startswith('pf'):
        return PF_RULE
    return set(RULE)


def score(dets, rule, allow=None, th=0.0):
    """Độ bẩn = conf cao nhất của đồ trong luật (0 nếu không có). allow: đồ trên ảnh chụp bàn sạch để bỏ qua."""
    s = 0.0
    for n, c, b in dets:
        if n not in rule or c < th:
            continue
        if allow is not None and allow(n, b):
            continue
        s = max(s, c)
    return s


def auc(y, p):
    y, p = np.asarray(y), np.asarray(p)
    pos, neg = p[y == 1], p[y == 0]
    return float(((pos[:, None] > neg[None]).sum() + 0.5 * (pos[:, None] == neg[None]).sum()) / (len(pos) * len(neg)))


def summarize(items, s, th):
    pred = {k: v >= th and v > 0 for k, v in s.items()}
    r = dict(dung=0, sach=0, n_sach=0, ban=0, n_ban=0, ban_c01=0, n_ban_c01=0, ban_c03=0, n_ban_c03=0)
    for it in items:
        ok = pred[it['key']] == bool(it['y'])
        r['dung'] += ok
        if it['y']:
            r['ban'] += ok
            r['n_ban'] += 1
            sub = 'c03' if it['clip'].startswith('03') else 'c01'
            r[f'ban_{sub}'] += ok
            r[f'n_ban_{sub}'] += 1
        else:
            r['sach'] += ok
            r['n_sach'] += 1
    r['tong'] = len(items)
    return r


def best(items, s):
    ths = sorted(set([v for v in s.values() if v > 0]) | {0.05})
    b = max(ths, key=lambda t: summarize(items, s, t)['dung'])
    return b, summarize(items, s, b)


def main():
    D = json.loads((CACHE / 'phat_hien.json').read_text(encoding='utf-8'))
    pe = json.loads((CACHE / 'pe_core_s16_91.json').read_text(encoding='utf-8'))
    items = test_items()
    y = [it['y'] for it in items]
    out = {}

    print(f'== 91 ảnh: luật "bẩn nếu thấy đồ trong danh sách, conf >= {TH_MAIN}" ==')
    print(f'{"cấu hình":22s} {"đúng":>6s} {"sạch":>6s} {"bẩn":>6s} {"bẩn c01":>8s} {"bẩn c03":>8s} {"AUC":>5s}  tốt nhất (ngưỡng)')
    pe_pred = {k: v >= 0.5 for k, v in pe.items()}
    r = summarize(items, {k: (1.0 if v else 0.0) for k, v in pe_pred.items()}, 0.5)
    print(f'{"PE-Core S/16 (hiện tại)":22s} {r["dung"]:>3d}/91 {r["sach"]:>3d}/59 {r["ban"]:>3d}/32 {r["ban_c01"]:>5d}/24 '
          f'{r["ban_c03"]:>5d}/8 {auc(y, [pe[it["key"]] for it in items]):.3f}')
    out['pe_core_s16'] = r
    for cfg in D:
        rule = rule_of(cfg)
        s = {it['key']: score(D[cfg][it['key']], rule) for it in items}
        r = summarize(items, s, TH_MAIN)
        bt, br = best(items, s)
        r['auc'] = round(auc(y, [s[it['key']] for it in items]), 3)
        r['tot_nhat'] = dict(nguong=round(bt, 3), dung=br['dung'], sach=br['sach'], ban=br['ban'])
        out[cfg] = r
        print(f'{cfg:22s} {r["dung"]:>3d}/91 {r["sach"]:>3d}/59 {r["ban"]:>3d}/32 {r["ban_c01"]:>5d}/24 '
              f'{r["ban_c03"]:>5d}/8 {r["auc"]:.3f}  {br["dung"]}/91 ({bt:.2f})')

    # --- đồ nhìn thấy trên bàn sạch (đồ của quán) và bàn bẩn, theo lớp
    print('\n== Đồ (trong luật, conf >= 0,25) thấy trên bàn SẠCH / BẨN: số ảnh có lớp đó ==')
    out['lop'] = {}
    for cfg in D:
        if not cfg.endswith(('full1280', 'crop640')):
            continue
        rule = rule_of(cfg)
        cs, cb = Counter(), Counter()
        for it in items:
            names = {n for n, c, _ in D[cfg][it['key']] if c >= TH_MAIN and n in rule}
            (cb if it['y'] else cs).update(names)
        out['lop'][cfg] = dict(sach=dict(cs.most_common()), ban=dict(cb.most_common()))
        print(f'{cfg}: sạch {dict(cs.most_common(8))}\n{"":{len(cfg) + 2}}bẩn  {dict(cb.most_common(8))}')

    # --- danh sách đồ của quán học từ một ảnh chụp bàn sạch
    print('\n== Danh sách đồ của quán (từ ảnh chụp bàn sạch), chấm trên 85 ảnh còn lại (bỏ 6 ảnh dùng làm ảnh chụp) ==')
    snap_keys = set(SNAP_DAU.values()) | set(SNAP_CUOI.values())
    items88 = [it for it in items if it['key'] not in snap_keys]
    out['danh_sach_quan'] = {}
    print(f'{"cấu hình":22s} {"cách":26s} {"đúng":>6s} {"sạch":>6s} {"bẩn":>6s}')
    n_s = sum(1 for it in items88 if not it['y'])
    n_b = len(items88) - n_s
    for cfg in D:
        if not cfg.endswith(('full1280', 'crop640')):
            continue
        rule = rule_of(cfg)
        res = {}
        for snap_name, SNAP in (('không', None), ('vị trí, ảnh đầu', SNAP_DAU), ('vị trí, ảnh cuối', SNAP_CUOI),
                                ('loại đồ, ảnh đầu', SNAP_DAU), ('loại đồ, ảnh cuối', SNAP_CUOI)):
            s = {}
            for it in items88:
                allow = None
                if SNAP and it['ban'] in SNAP:
                    ref = [d for d in D[cfg][SNAP[it['ban']]] if d[1] >= 0.15 and d[0] in rule]
                    if snap_name.startswith('vị trí'):
                        allow = lambda n, b, ref=ref: any(iou(b, rb) >= 0.3 for _, _, rb in ref)
                    else:
                        names = {d[0] for d in ref}
                        allow = lambda n, b, names=names: n in names
                s[it['key']] = score(D[cfg][it['key']], rule, allow)
            r = summarize(items88, s, TH_MAIN)
            res[snap_name] = dict(dung=r['dung'], sach=r['sach'], ban=r['ban'], tong=len(items88))
            print(f'{cfg:22s} {snap_name:26s} {r["dung"]:>3d}/{len(items88)} {r["sach"]:>3d}/{n_s} {r["ban"]:>3d}/{n_b}')
        out['danh_sach_quan'][cfg] = res
    pe85 = summarize(items88, {k: (1.0 if pe_pred[k] else 0.0) for k in pe_pred}, 0.5)
    print(f'{"PE-Core S/16":22s} {"":26s} {pe85["dung"]:>3d}/{len(items88)} {pe85["sach"]:>3d}/{n_s} {pe85["ban"]:>3d}/{n_b}')
    out['pe_core_s16_85'] = pe85

    # --- kết hợp với PE-Core S/16
    print('\n== Kết hợp với PE-Core S/16 (91 ảnh) ==')
    out['ket_hop'] = {}
    for cfg in D:
        if not cfg.endswith(('full1280', 'crop640')):
            continue
        rule = rule_of(cfg)
        yo = {it['key']: score(D[cfg][it['key']], rule) >= TH_MAIN for it in items}
        for name, f in (('VÀ', lambda a, b: a and b), ('HOẶC', lambda a, b: a or b)):
            s = {k: float(f(pe_pred[k], yo[k])) for k in yo}
            r = summarize(items, s, 0.5)
            out['ket_hop'][f'{cfg} {name}'] = dict(dung=r['dung'], sach=r['sach'], ban=r['ban'])
            print(f'PE-Core {name:4s} {cfg:18s} {r["dung"]:>3d}/91 sạch {r["sach"]}/59 bẩn {r["ban"]}/32')
        both_wrong = [it['key'] for it in items if pe_pred[it['key']] != bool(it['y']) and yo[it['key']] != bool(it['y'])]
        print(f'   cả hai cùng sai: {len(both_wrong)} {both_wrong}')

    # --- ảnh sai của cấu hình chính, để xem bằng mắt
    out['anh_sai'] = {}
    for cfg in ('e26s_full1280', 'e26s_crop640', 'coco26s_full1280'):
        if cfg not in D:
            continue
        rule = rule_of(cfg)
        wrong = []
        for it in items:
            s = score(D[cfg][it['key']], rule)
            if (s >= TH_MAIN) != bool(it['y']):
                top = sorted([d for d in D[cfg][it['key']] if d[0] in rule], key=lambda d: -d[1])[:3]
                wrong.append(dict(anh=it['key'], do=[(n, c) for n, c, _ in top]))
        out['anh_sai'][cfg] = wrong
    (CACHE / 'diem_91.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
