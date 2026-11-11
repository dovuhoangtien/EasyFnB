"""Tìm người có mặt mà pose bỏ sót ở conf 0.3: chạy lại conf 0.1 (CPU), lấy người mới (IoU < 0.3 với người cũ)
có điểm đầu >= 0.3, cắt ảnh ra lưới để xem bằng mắt mặt có lộ không."""
import json, sys
from pathlib import Path
import cv2, numpy as np
from ultralytics import YOLO
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from lam_mo_mat import blur_faces, head_ellipse
rows = json.loads((HERE / '_cache' / 'khung_xuong.json').read_text(encoding='utf-8'))
m = YOLO(str(HERE.parents[1] / 'models' / 'yolo26n-pose.pt'))
def iou(a, b):
    x1, y1, x2, y2 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    i = max(0, x2 - x1) * max(0, y2 - y1)
    return i / ((a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - i + 1e-6)
tiles, extra, low = [], [], {}
for r in rows:
    img = cv2.imread(str(HERE / '_cache' / f"{r['name']}.jpg"))
    q = m.predict(img, classes=[0], conf=0.1, imgsz=960, device='cpu', verbose=False)[0]
    bx, kp, kc, cf = q.boxes.xyxy.numpy(), q.keypoints.xy.numpy(), q.keypoints.conf.numpy(), q.boxes.conf.numpy()
    old = np.array(r['boxes']).reshape(-1, 4)
    out = blur_faces(img, np.array(r['kp']).reshape(-1, 17, 2), np.array(r['kc']).reshape(-1, 17), old)
    low[r['name']] = dict(boxes=bx[cf < 0.3].tolist(), kp=kp[cf < 0.3].tolist(), kc=kc[cf < 0.3].tolist())
    for b, p, c, s in zip(bx, kp, kc, cf):
        if s >= 0.3 or any(iou(b, o) > 0.3 for o in old) or c[:5].max() < 0.3:
            continue
        e = head_ellipse(p, c, b, img_wh=(1280, 720))
        cx, cy, a, bb = e[:4]
        z = max(a, bb) * 2.5
        x0, y0, x1, y1 = int(max(0, cx - z)), int(max(0, cy - z)), int(min(1280, cx + z)), int(min(720, cy + z))
        t = np.hstack([cv2.resize(img[y0:y1, x0:x1], (128, 128)), cv2.resize(out[y0:y1, x0:x1], (128, 128))])
        cv2.putText(t, f"{r['name']} {s:.2f}", (2, 10), cv2.FONT_HERSHEY_SIMPLEX, 0.33, (0, 255, 255), 1)
        tiles.append(t); extra.append(dict(khung=r['name'], conf=round(float(s), 2), box=[round(float(v)) for v in b]))
(HERE / '_cache' / 'nguoi_conf_thap.json').write_text(json.dumps(low), encoding='utf-8')
print('so nguoi them (conf 0.1-0.3, co diem dau):', len(extra))
for e in extra: print(e)
while len(tiles) % 6: tiles.append(np.zeros_like(tiles[0]))
cv2.imwrite(str(HERE / 'anh' / 'nguoi_bi_sot.jpg'), np.vstack([np.hstack(tiles[i:i+6]) for i in range(0, len(tiles), 6)]))
