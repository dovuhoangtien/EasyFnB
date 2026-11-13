"""Việc thiết lập mà trang Cài đặt trên web nhờ máy camera làm, trên khung hình camera đang có.

  find_tables   tìm bàn bằng model phát hiện vật thể đang chạy (lớp "dining table" của COCO). Có `box`
                (chủ quán khoanh thô một vùng) thì chỉ tìm quanh vùng đó và trả đúng một bàn.
  staff_photo   cắt ảnh người đứng gần giữa khung hình nhất, làm ảnh nhận dạng nhân viên.

ThuVienNV: nhận nhân viên theo ảnh chụp sẵn (--nv-theo-anh). So ảnh cắt từng người với ảnh cả người của
nhân viên bằng chính phần ảnh của model nhân viên (PE-Core). Mức giống quy ra điểm bằng hai mốc --nv-anh-lo
và --nv-anh-hi; hai mốc này CHƯA đo trên clip thật.
"""
import base64

import cv2
import numpy as np


def _reading_order(tables, H):
    """Trái sang phải, trên xuống dưới; hai bàn lệch nhau dưới 12% chiều cao ảnh coi như cùng hàng."""
    rows = []
    for t in sorted(tables, key=lambda t: t['cy']):
        if rows and t['cy'] - rows[-1][0]['cy'] < 0.12 * H:
            rows[-1].append(t)
        else:
            rows.append([t])
    return [t for r in rows for t in sorted(r, key=lambda t: t['cx'])]


def _iou(a, b):
    iw = min(a[2], b[2]) - max(a[0], b[0])
    ih = min(a[3], b[3]) - max(a[1], b[1])
    if iw <= 0 or ih <= 0:
        return 0.0
    inter = iw * ih
    return inter / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter)


def _overlap(a, b):
    """Phần chung so với khung nhỏ hơn (khung nằm lọt trong khung khác cho 1)."""
    iw = min(a[2], b[2]) - max(a[0], b[0])
    ih = min(a[3], b[3]) - max(a[1], b[1])
    if iw <= 0 or ih <= 0:
        return 0.0
    return iw * ih / min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]))


def find_tables(det, frame, box=None, frame_w=0, frame_h=0, predict_kw=None, conf=0.2):
    H, W = frame.shape[:2]
    cls = next((k for k, v in (getattr(det, 'names', None) or {}).items() if v == 'dining table'), None)
    if cls is None:
        return dict(error='model của camera không nhận được bàn')
    x0 = y0 = 0
    img = frame
    bx = None
    if box:
        sx = W / frame_w if frame_w else 1.0
        sy = H / frame_h if frame_h else 1.0
        bx = [min(box[0], box[2]) * sx, min(box[1], box[3]) * sy, max(box[0], box[2]) * sx, max(box[1], box[3]) * sy]
        pad = 0.3 * max(bx[2] - bx[0], bx[3] - bx[1])
        x0, y0 = int(max(0, bx[0] - pad)), int(max(0, bx[1] - pad))
        x1, y1 = int(min(W, bx[2] + pad)), int(min(H, bx[3] + pad))
        if x1 - x0 < 16 or y1 - y0 < 16:
            return dict(frame_w=W, frame_h=H, tables=[])
        img = frame[y0:y1, x0:x1]
    r = det.predict(img, classes=[cls], conf=conf, verbose=False, **(predict_kw or {}))[0]
    found = []
    for (a, b, c, d), s in zip(r.boxes.xyxy.cpu().numpy().tolist(), r.boxes.conf.cpu().numpy().tolist()):
        a, b, c, d = a + x0, b + y0, c + x0, d + y0
        if (c - a) * (d - b) < 0.003 * W * H:
            continue
        found.append(dict(xyxy=(a, b, c, d), cx=(a + c) / 2, cy=(b + d) / 2, score=round(float(s), 3)))
    # một bàn hay bị bắt thành vài khung chồng nhau: giữ khung điểm cao nhất
    kept = []
    for t in sorted(found, key=lambda t: -t['score']):
        if all(_overlap(t['xyxy'], k['xyxy']) < 0.45 for k in kept):
            kept.append(t)
    found = kept
    if bx:
        found = sorted(found, key=lambda t: -_iou(t['xyxy'], bx))[:1]
        found = [t for t in found if _iou(t['xyxy'], bx) > 0.1]
    else:
        found = _reading_order(found, H)
    return dict(frame_w=W, frame_h=H,
                tables=[dict(polygon=[[round(a, 1), round(b, 1)], [round(c, 1), round(b, 1)],
                                      [round(c, 1), round(d, 1)], [round(a, 1), round(d, 1)]], score=t['score'])
                        for t in found for a, b, c, d in [t['xyxy']]])


def staff_photo(frame, boxes):
    H, W = frame.shape[:2]
    best, best_v = None, 0.0
    for b in boxes:
        x1, y1, x2, y2 = [float(v) for v in b[:4]]
        off = abs((x1 + x2) / 2 - W / 2) / W          # càng gần giữa càng được chọn
        v = (x2 - x1) * (y2 - y1) * (1.0 - 1.5 * min(off, 0.5))
        if v > best_v:
            best, best_v = (x1, y1, x2, y2), v
    if best is None:
        return dict(error='không thấy ai trước camera')
    x1, y1, x2, y2 = best
    px, py = 0.08 * (x2 - x1), 0.08 * (y2 - y1)
    crop = frame[int(max(0, y1 - py)):int(min(H, y2 + py)), int(max(0, x1 - px)):int(min(W, x2 + px))]
    ok, buf = cv2.imencode('.jpg', crop, [cv2.IMWRITE_JPEG_QUALITY, 90])
    if not ok:
        return dict(error='không cắt được ảnh')
    return dict(jpeg_b64=base64.b64encode(buf.tobytes()).decode())


def do_job(job, frame, boxes, det, predict_kw=None):
    try:
        if job.get('kind') == 'find_tables':
            return find_tables(det, frame, job.get('box'), job.get('frame_w') or 0, job.get('frame_h') or 0, predict_kw)
        if job.get('kind') == 'staff_photo':
            return staff_photo(frame, boxes)
        return dict(error=f"máy camera chưa biết việc {job.get('kind')!r}")
    except Exception as e:  # việc thiết lập hỏng không được làm dừng camera
        return dict(error=f'{e.__class__.__name__}: {e}')


class ThuVienNV:
    """Ảnh cả người của nhân viên (đã đồng ý), để nhận nhân viên theo ảnh."""

    def __init__(self, clip, lo=0.70, hi=0.90):
        self.clip, self.lo, self.hi = clip, lo, hi
        self.emb = None

    def load(self, refs):
        """refs: [(mã nhân viên, kind, JPEG bytes)]. Chỉ dùng ảnh cả người; ảnh mặt chưa dùng."""
        imgs = [cv2.imdecode(np.frombuffer(j, np.uint8), cv2.IMREAD_COLOR) for _, kind, j in refs if kind == 'body']
        imgs = [im for im in imgs if im is not None and im.size]
        self.emb = self.clip.features(imgs) if imgs else None
        print(f'  nhận nhân viên theo ảnh: {len(imgs)} ảnh cả người')

    def probs(self, crops):
        if self.emb is None or not crops:
            return [None] * len(crops)
        sim = (self.clip.features(crops) @ self.emb.T).max(dim=1).values.cpu().tolist()
        return [float(min(1.0, max(0.0, (s - self.lo) / (self.hi - self.lo)))) for s in sim]
