"""Dải ảnh theo từng lần giơ tay có nhãn (dap_an.json): vùng x của nhãn, trước | sau làm mờ, mỗi khung mẫu trong khoảng."""
import json, sys
from pathlib import Path
import cv2, numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from lam_mo_mat import blur_faces
VT = HERE.parents[1]
rows = json.loads((HERE / '_cache' / 'khung_xuong.json').read_text(encoding='utf-8'))
lab = json.loads((VT / 'danh_gia' / 'dap_an.json').read_text(encoding='utf-8'))['gio_tay']
for clip, items in lab.items():
    if not isinstance(items, list) or not items or not isinstance(items[0], dict):
        continue
    for j, l in enumerate(items):
        tiles = []
        for r in rows:
            if r['clip'] != clip or not (l['tu'] <= r['t'] <= l['den']):
                continue
            img = cv2.imread(str(HERE / '_cache' / f"{r['name']}.jpg"))
            out = blur_faces(img, np.array(r['kp']).reshape(-1, 17, 2), np.array(r['kc']).reshape(-1, 17), np.array(r['boxes']).reshape(-1, 4))
            H, W = img.shape[:2]
            x0, x1 = max(0, l['x'][0] - 60), min(W, l['x'][1] + 60)
            y1 = int(0.75 * H)
            t = np.hstack([img[:y1, x0:x1], np.full((y1, 4, 3), 255, np.uint8), out[:y1, x0:x1]])
            s = 220 / t.shape[0]
            t = cv2.resize(t, (int(t.shape[1] * s), 220))
            cv2.putText(t, f"{r['name']} t={r['t']}", (3, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
            tiles.append(t)
        if not tiles:
            continue
        w = max(t.shape[1] for t in tiles)
        tiles = [np.pad(t, ((0, 0), (0, w - t.shape[1]), (0, 0))) for t in tiles]
        cols = max(1, 1500 // w)
        while len(tiles) % cols:
            tiles.append(np.zeros_like(tiles[0]))
        g = np.vstack([np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)])
        cv2.imwrite(str(HERE / 'anh' / f'nhan_{clip[:2]}_{j}.jpg'), g, [cv2.IMWRITE_JPEG_QUALITY, 85])
        print(clip[:2], j, l['ai'], len([1 for r in rows if r['clip'] == clip and l['tu'] <= r['t'] <= l['den']]), g.shape)
