"""Phóng to vài người để xem kỹ: python soi.py 06_0233#0 06_0164#0 ..."""
import json, sys
from pathlib import Path
import cv2, numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from lam_mo_mat import blur_faces, head_ellipse
rows = {r['name']: r for r in json.loads((HERE / '_cache' / 'khung_xuong.json').read_text(encoding='utf-8'))}
tiles = []
for arg in sys.argv[2:]:
    name, k = arg.split('#'); k = int(k)
    r = rows[name]; img = cv2.imread(str(HERE / '_cache' / f'{name}.jpg'))
    kp, kc, bx = np.array(r['kp']).reshape(-1, 17, 2), np.array(r['kc']).reshape(-1, 17), np.array(r['boxes']).reshape(-1, 4)
    out = blur_faces(img, kp, kc, bx)
    cx, cy, a, b, src = head_ellipse(kp[k], kc[k], bx[k])
    s = max(a, b) * 2.2; H, W = img.shape[:2]
    x0, y0, x1, y1 = int(max(0, cx - s)), int(max(0, cy - s)), int(min(W, cx + s)), int(min(H, cy + s))
    bef = img.copy()
    cv2.ellipse(bef, (int(cx), int(cy)), (int(a), int(b)), 0, 0, 360, (0, 255, 0), 1)
    for i in range(5):
        if kc[k][i] > 0.3: cv2.circle(bef, tuple(map(int, kp[k][i])), 2, (0, 0, 255), -1)
    p = np.hstack([cv2.resize(bef[y0:y1, x0:x1], (240, 240)), cv2.resize(out[y0:y1, x0:x1], (240, 240))])
    cv2.putText(p, arg, (3, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
    tiles.append(p)
while len(tiles) % 3: tiles.append(np.zeros_like(tiles[0]))
cv2.imwrite(sys.argv[1], np.vstack([np.hstack(tiles[i:i + 3]) for i in range(0, len(tiles), 3)]))
