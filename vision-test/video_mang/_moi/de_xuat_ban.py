"""Đề xuất vùng bàn cho clip mới: chạy YOLO tìm 'dining table' trên vài khung, gộp các hộp trùng,
ghi ảnh kiểm tra (khung + hộp + lưới toạ độ) và một tờ ảnh trích 12 khung để xem nội dung clip.
    python de_xuat_ban.py <clip.mp4> [<clip2.mp4> ...]
Kết quả: _moi/<tên>_ban.jpg, _moi/<tên>_to.jpg, _moi/de_xuat.json (cộng dồn)."""
import json, sys
from pathlib import Path
import cv2, numpy as np
from ultralytics import YOLO

HERE = Path(__file__).resolve().parent
OUT = HERE / 'de_xuat.json'
m = YOLO(str(HERE.parent.parent / 'models' / 'yolo26s.pt'))

def iou(a, b):
    x1, y1, x2, y2 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    i = max(0, x2 - x1) * max(0, y2 - y1)
    return i / ((a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - i + 1e-6)

res = json.loads(OUT.read_text(encoding='utf-8')) if OUT.exists() else {}
for p in map(Path, sys.argv[1:]):
    cap = cv2.VideoCapture(str(p)); n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)); fps = cap.get(cv2.CAP_PROP_FPS) or 25
    frames = []
    for k in range(12):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(n * (k + 0.5) / 12)); ok, f = cap.read()
        if ok: frames.append((int(n * (k + 0.5) / 12) / fps, f))
    H, W = frames[0][1].shape[:2]
    boxes = []  # [box, count, conf]
    for _, f in frames:
        r = m.predict(f, imgsz=1280, conf=0.25, classes=[60], verbose=False)[0]
        for b, c in zip(r.boxes.xyxy.cpu().numpy(), r.boxes.conf.cpu().numpy()):
            for bb in boxes:
                if iou(bb[0], b) > 0.4:
                    bb[0] = (bb[0] * bb[1] + b) / (bb[1] + 1); bb[1] += 1; bb[2] = max(bb[2], c); break
            else:
                boxes.append([b, 1, c])
    keep = [b for b in boxes if b[1] >= 3]
    keep.sort(key=lambda b: (b[0][1] + b[0][3]) / 2, reverse=True)  # gần camera trước
    ban = {}
    for i, (b, cnt, c) in enumerate(keep, 1):
        x1, y1, x2, y2 = [int(v) for v in b]
        ban[f'B{i}'] = [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
    res[p.stem] = dict(ghi_chu=f'{W}x{H}, de xuat tu dong (YOLO dining table, thay o >=3/12 khung). Can xem lai.', xac_nhan_s=1.0, ban=ban)
    # ảnh kiểm tra
    img = frames[len(frames)//2][1].copy()
    for x in range(0, W, 80): cv2.line(img, (x, 0), (x, H), (80, 80, 80), 1); cv2.putText(img, str(x), (x+2, 14), 0, .4, (255,255,255), 1)
    for y in range(0, H, 80): cv2.line(img, (0, y), (W, y), (80, 80, 80), 1); cv2.putText(img, str(y), (2, y+14), 0, .4, (255,255,255), 1)
    for k, poly in ban.items():
        cv2.polylines(img, [np.array(poly)], True, (0, 220, 255), 2); cv2.putText(img, k, tuple(poly[0]), 0, .8, (0, 220, 255), 2)
    cv2.imwrite(str(HERE / f'{p.stem}_ban.jpg'), cv2.resize(img, (1280, int(1280 * H / W))), [cv2.IMWRITE_JPEG_QUALITY, 80])
    tw = 426; th = int(tw * H / W); sheet = np.zeros((th * 4, tw * 3, 3), np.uint8)
    for k, (t, f) in enumerate(frames):
        s = cv2.resize(f, (tw, th)); cv2.putText(s, f'{t:.0f}s', (6, 22), 0, .7, (0, 255, 255), 2)
        sheet[(k // 3) * th:(k // 3 + 1) * th, (k % 3) * tw:(k % 3 + 1) * tw] = s
    cv2.imwrite(str(HERE / f'{p.stem}_to.jpg'), sheet, [cv2.IMWRITE_JPEG_QUALITY, 80])
    print(p.stem, f'{W}x{H} {n/fps:.0f}s', len(ban), 'ban')
OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
