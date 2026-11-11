"""Chạy YOLOE-26 (câu nhắc chữ và không câu nhắc) và yolo26s COCO trên các khung hình của 91 ảnh bàn,
lưu mọi phát hiện (conf >= 0,05) vào ket_qua/phat_hien.json để chấm điểm nhiều ngưỡng mà không chạy lại.

Hai cách nhìn:
  full : cả khung hình 1280x720, đưa vào model ở cỡ 640 hoặc 1280, đồ thuộc bàn nào theo tâm (như pipeline)
  crop : cắt riêng vùng bàn (nới 10%, giống anh_ban_test) từ khung gốc, phóng lên 640

    python chay_yoloe.py                  # tất cả
    python chay_yoloe.py --chi e26s pf26s # vài model
    python chay_yoloe.py --tieng-viet     # chỉ thử câu nhắc tiếng Việt
"""
import argparse
import json
import re
import time

import cv2
import numpy as np
import torch

from chung import (CACHE, PROMPTS, VT, COCO_ITEMS, Frames, load_coco, load_yoloe, owner, run, table_crop_box,
                   zones)

MODELS = {
    'e26s': 'yoloe-26s-seg.pt',
    'e26n': 'yoloe-26n-seg.pt',
    'pf26s': 'yoloe-26s-seg-pf.pt',
    'pf26n': 'yoloe-26n-seg-pf.pt',
    'coco26s': 'yolo26s.pt',
}
RUNS = [('full', 640), ('full', 1280), ('crop', 640)]


def test_items():
    """91 ảnh bàn -> (khoá, clip, bàn, giây, nhãn). Nhãn 1 = bẩn."""
    out = []
    for lab, sub in ((1, 'ban'), (0, 'sach')):
        for f in sorted((VT / 'danh_gia' / 'anh_ban_test' / sub).glob('*.jpg')):
            m = re.match(r'c01_(B\d)_([\d.]+)$', f.stem)
            if m:
                out.append(dict(key=f'{sub}/{f.stem}', clip='01_phong_an_goc_cao', ban=m[1], t=float(m[2]), y=lab))
            else:
                t = float(re.match(r'c03_([\d.]+)$', f.stem)[1])
                out.append(dict(key=f'{sub}/{f.stem}', clip='03_ban_an_xong_tu_tren', ban='B1', t=t, y=lab))
    return out


def detect(model, im, imgsz, is_coco):
    if is_coco:
        return run(model, im, imgsz, 0.05, classes=list(COCO_ITEMS))
    return run(model, im, imgsz, 0.05)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--chi', nargs='+', default=list(MODELS))
    ap.add_argument('--tieng-viet', action='store_true')
    args = ap.parse_args()
    if args.tieng_viet:
        return thu_tieng_viet()
    items = test_items()
    Z = zones()
    fr = Frames()
    frames = {}
    for it in items:
        k = (it['clip'], it['t'])
        if k not in frames:
            frames[k] = fr.get(*k)
    print(f'{len(items)} ảnh bàn, {len(frames)} khung hình khác nhau', flush=True)
    out_f = CACHE / 'phat_hien.json'
    res = json.loads(out_f.read_text(encoding='utf-8')) if out_f.exists() else {}
    for key in args.chi:
        is_coco = key.startswith('coco')
        model = load_coco() if is_coco else load_yoloe(MODELS[key])
        for mode, sz in RUNS:
            cfg = f'{key}_{mode}{sz}'
            t0 = time.time()
            res[cfg] = {}
            if mode == 'full':
                cache = {}
                for (clip, t), im in frames.items():
                    cache[(clip, t)] = detect(model, im, sz, is_coco)
                for it in items:
                    tables = Z[it['clip']]['ban']
                    dets = cache[(it['clip'], it['t'])]
                    res[cfg][it['key']] = [d for d in dets if owner(d[2], tables) == it['ban']]
            else:
                for it in items:
                    im = frames[(it['clip'], it['t'])]
                    H, W = im.shape[:2]
                    poly = Z[it['clip']]['ban'][it['ban']]
                    x1, y1, x2, y2 = table_crop_box(poly, W, H)
                    dets = detect(model, im[y1:y2, x1:x2], sz, is_coco)
                    dets = [(n, s, [b[0] + x1, b[1] + y1, b[2] + x1, b[3] + y1]) for n, s, b in dets]
                    res[cfg][it['key']] = [d for d in dets if owner(d[2], {it['ban']: poly}) == it['ban']]
            n = sum(len(v) for v in res[cfg].values())
            print(f'{cfg}: {n} phát hiện trên bàn, {time.time() - t0:.1f} s', flush=True)
        del model
        torch.cuda.empty_cache()
        out_f.write_text(json.dumps(res, ensure_ascii=False), encoding='utf-8')
    print('đỉnh VRAM PyTorch (MB):', round(torch.cuda.max_memory_reserved() / 2 ** 20))


def thu_tieng_viet():
    """Bộ mã hoá chữ MobileCLIP2 có hiểu tiếng Việt không? So độ giống (cosine) của câu nhắc Việt với từ Anh,
    rồi chạy thử cả hai bộ câu nhắc trên cùng khung hình."""
    pairs = [('dĩa', 'plate'), ('đĩa', 'plate'), ('chén', 'bowl'), ('tô', 'bowl'), ('ly', 'glass'), ('cốc', 'cup'),
             ('chai', 'bottle'), ('đũa', 'chopsticks'), ('muỗng', 'spoon'), ('khăn giấy', 'napkin'),
             ('khay', 'tray'), ('đồ ăn thừa', 'leftovers'), ('lon', 'can')]
    from ultralytics.nn.text_model import build_text_model
    import os
    from chung import WEIGHTS
    os.chdir(WEIGHTS)
    tm = build_text_model('mobileclip2:b', device=torch.device('cuda'))
    vi = [p[0] for p in pairs]
    en = [p[1] for p in pairs]
    fv = torch.nn.functional.normalize(tm.encode_text(tm.tokenize(vi)), dim=-1)
    fe = torch.nn.functional.normalize(tm.encode_text(tm.tokenize(sorted(set(en)))), dim=-1)
    ens = sorted(set(en))
    sim = (fv @ fe.T).cpu().numpy()
    rows = []
    hit = 0
    for i, (v, e) in enumerate(pairs):
        best = ens[int(sim[i].argmax())]
        hit += best == e
        rows.append(dict(vi=v, en_dung=e, giong_nhat=best, cos_dung=round(float(sim[i][ens.index(e)]), 3),
                         cos_cao_nhat=round(float(sim[i].max()), 3)))
        print(f'{v:12s} -> gần nhất "{best}" ({sim[i].max():.2f}); đúng phải là "{e}" ({sim[i][ens.index(e)]:.2f})')
    print(f'chọn đúng nghĩa: {hit}/{len(pairs)}')
    del tm
    # chạy thật trên khung có bàn bẩn và bàn trống
    fr = Frames()
    Z = zones()
    det = {}
    for lang, cls in (('vi', vi), ('en', en)):
        m = load_yoloe('yoloe-26s-seg.pt', classes=list(dict.fromkeys(cls)))
        for clip, t in (('01_phong_an_goc_cao', 0.25), ('03_ban_an_xong_tu_tren', 0.5), ('01_phong_an_goc_cao', 7.75)):
            im = fr.get(clip, t)
            d = [x for x in run(m, im, 1280, 0.15) if owner(x[2], Z[clip]['ban'])]
            det[f'{lang} {clip[:2]}@{t}'] = d
            print(lang, clip[:2], t, [(n, s) for n, s, _ in sorted(d, key=lambda x: -x[1])])
        del m
    (CACHE / 'tieng_viet.json').write_text(json.dumps(dict(cosine=rows, chon_dung=f'{hit}/{len(pairs)}', phat_hien=det),
                                                      ensure_ascii=False, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
