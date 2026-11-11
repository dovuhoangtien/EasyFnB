"""Ảnh tờ liên tiếp có vẽ box + mã track (từ khung_xuong.npz) để người xem ghi mã track nhân viên."""
import sys
from pathlib import Path
import cv2
import numpy as np
VT = Path(__file__).resolve().parents[2]
out, clip, step, dst = Path(sys.argv[1]), sys.argv[2], float(sys.argv[3]), sys.argv[4]
t_from = float(sys.argv[5]) if len(sys.argv) > 5 else 0
t_to = float(sys.argv[6]) if len(sys.argv) > 6 else 1e9
z = np.load(out / clip / 'khung_xuong.npz')
fps = float(z['fps'])
cap = cv2.VideoCapture(str(VT / 'clips' / f'{clip}.mp4'))
tiles = []
t = t_from
while t <= min(t_to, z['t'].max()):
    f = int(round(t * fps))
    cap.set(cv2.CAP_PROP_POS_FRAMES, f)
    ok, im = cap.read()
    if not ok:
        break
    m = np.abs(z['t'] - f / fps) < 1e-3
    for b, i, ps in zip(z['box'][m], z['id'][m], z['pst'][m]):
        x1, y1, x2, y2 = map(int, b)
        cv2.rectangle(im, (x1, y1), (x2, y2), (0, 255, 255), 3)
        cv2.putText(im, f'#{i}', (x1 + 4, y1 + 40), 0, 1.4, (0, 0, 255), 4)
    cv2.putText(im, f'{t:.1f}s', (20, 60), 0, 2, (255, 255, 255), 5)
    tiles.append(cv2.resize(im, (640, int(640 * im.shape[0] / im.shape[1]))))
    t += step
rows = [cv2.hconcat(tiles[k:k + 3] + [np.zeros_like(tiles[0])] * (3 - len(tiles[k:k + 3]))) for k in range(0, len(tiles), 3)]
cv2.imwrite(dst, cv2.vconcat(rows))
