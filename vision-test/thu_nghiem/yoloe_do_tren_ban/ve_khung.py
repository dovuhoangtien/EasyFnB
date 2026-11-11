"""Vẽ khung hình mẫu (clip 01, 03, 09) ở các mốc có đáp án: YOLOE-26s câu nhắc chữ / YOLOE-26s không câu nhắc /
yolo26s COCO, cùng cỡ 1280, conf >= 0,25. Ghi anh_mau/*.jpg và ket_qua/so_sanh_khung.json.

    python ve_khung.py
"""
import json

import cv2
import numpy as np
import torch

from chung import CACHE, COCO_ITEMS, HERE, Frames, labels, load_coco, load_yoloe, owner, run, zones

torch.cuda.set_per_process_memory_fraction(1.5 * 2 ** 30 / torch.cuda.get_device_properties(0).total_memory)
OUT = HERE / 'anh_mau'
OUT.mkdir(exist_ok=True)
MOC = [('01_phong_an_goc_cao', 0.25), ('01_phong_an_goc_cao', 2.75), ('01_phong_an_goc_cao', 6.25),
       ('01_phong_an_goc_cao', 7.75), ('01_phong_an_goc_cao', 10.25),
       ('03_ban_an_xong_tu_tren', 0.5), ('03_ban_an_xong_tu_tren', 4.5),
       ('09_nhom_ban_tron', 1.0), ('09_nhom_ban_tron', 6.0)]
# bản không câu nhắc thấy cả bàn, ghế, người, sàn...: bỏ khi liệt kê đồ trên bàn
PF_BO = {'table', 'dining table', 'coffee table', 'kitchen table', 'desk', 'person', 'man', 'woman', 'chair',
         'floor', 'wood', 'restaurant', 'cafe', 'furniture', 'stool', 'bench', 'tablecloth', 'hand', 'girl', 'boy'}
STATE = {'T': 'trống', 'C': 'có khách', 'D': 'cần dọn', 'x': 'đang đổi'}


def draw(im, tables, dets, title):
    vis = im.copy()
    for name, poly in tables.items():
        cv2.polylines(vis, [np.array(poly, np.int32)], True, (90, 200, 90), 2)
        x, y = poly[0]
        cv2.putText(vis, name, (int(x), int(y) - 4), 0, 0.6, (90, 200, 90), 2)
    for n, c, b in dets:
        on = owner(b, tables) is not None
        col = (0, 200, 255) if on else (150, 150, 150)
        cv2.rectangle(vis, (int(b[0]), int(b[1])), (int(b[2]), int(b[3])), col, 1)
        if on:
            cv2.putText(vis, f'{n} {c:.2f}', (int(b[0]), int(b[1]) - 2), 0, 0.4, col, 1)
    cv2.rectangle(vis, (0, 0), (vis.shape[1], 34), (0, 0, 0), -1)
    cv2.putText(vis, title, (8, 24), 0, 0.75, (255, 255, 255), 2)
    return vis


def main():
    fr = Frames()
    Z, L = zones(), labels()['ban']
    ims = {m: fr.get(*m) for m in MOC}
    res = {f'{c}@{t}': {} for c, t in MOC}
    panels = {m: [] for m in MOC}
    for key, title in (('e26s', 'YOLOE-26s, cau nhac chu'), ('pf26s', 'YOLOE-26s-pf, khong cau nhac'),
                       ('coco', 'yolo26s COCO (pipeline)')):
        m = {'e26s': lambda: load_yoloe('yoloe-26s-seg.pt'), 'pf26s': lambda: load_yoloe('yoloe-26s-seg-pf.pt'),
             'coco': load_coco}[key]()
        for (clip, t), im in ims.items():
            dets = run(m, im, 1280, 0.25, classes=list(COCO_ITEMS) if key == 'coco' else None)
            if key == 'pf26s':
                dets = [d for d in dets if d[0] not in PF_BO]
            tables = Z[clip]['ban']
            panels[(clip, t)].append(draw(im, tables, dets, f'{title}  |  {clip[:2]} t={t}s'))
            per = {}
            for name in tables:
                per[name] = sorted([(n, round(c, 2)) for n, c, b in dets if owner(b, tables) == name],
                                   key=lambda x: -x[1])
            res[f'{clip}@{t}'][key] = per
        del m
        torch.cuda.empty_cache()
    for (clip, t), ps in panels.items():
        small = [cv2.resize(p, (960, 540), interpolation=cv2.INTER_AREA) for p in ps]
        cv2.imwrite(str(OUT / f'{clip[:2]}_{t:05.2f}.jpg'), np.vstack(small), [cv2.IMWRITE_JPEG_QUALITY, 85])
    # đáp án
    for clip, t in MOC:
        g = L.get(clip)
        if g:
            code = g['moc'].get(f'{t:g}') or g['moc'].get(str(t))
            res[f'{clip}@{t}']['dap_an'] = {b: STATE.get(c, c) for b, c in zip(g['thu_tu'], code)} if code else None
        elif clip.startswith('03'):
            res[f'{clip}@{t}']['dap_an'] = {'B1': 'cần dọn (đồ ăn thừa, không có đáp án theo mốc)'}
        else:
            res[f'{clip}@{t}']['dap_an'] = {'B1': 'có khách (không có đáp án theo mốc)'}
    (CACHE / 'so_sanh_khung.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
    for k, v in res.items():
        print(f'\n## {k}  đáp án {v.get("dap_an")}')
        for b in v['e26s']:
            def f(x):
                return ', '.join(f'{n} {c}' for n, c in v[x][b]) or '—'
            print(f'  {b}: YOLOE: {f("e26s")}\n      PF: {f("pf26s")}\n      COCO: {f("coco")}')


if __name__ == '__main__':
    main()
