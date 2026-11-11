"""Bước 1: cắt ảnh bàn sạch tham chiếu (và bản "vuông có cảnh xung quanh") từ clip 01.

- Ảnh tham chiếu: mọi khung cách nhau 0,125 s trong các đoạn đáp án là T (trống, sạch hoặc đã bày sẵn)
  của từng bàn, đúng các đoạn T mà danh_gia/tao_anh_ban_test.py dùng. Bàn B3 không có đoạn T nào
  trong clip 01 (chỉ C, D, x) nên không có ảnh tham chiếu.
- Mỗi ảnh cắt hai kiểu:
    chat  = giống hệt ảnh test: khung bao bàn nới 10%, thêm viền xám thành hình vuông, thu về 256x256
    vuong = khung vuông quanh bàn (cạnh = cạnh dài khung bao + 20%), lấy cảnh thật thay cho viền xám
- Cắt lại cả 83 ảnh test của clip 01 theo hai kiểu (kiểu chat dùng để kiểm khung hình có khớp ảnh test cũ).
- Chạy YOLO (models/yolo26s.pt) tìm người trên mọi khung đã cắt, ghi phần diện tích bàn bị khung người
  che (để chọn ảnh tham chiếu không bị che và tìm ảnh "người che bàn" cho phần kiểm độ bền).

    python thu_nghiem/ban_sach_tham_chieu/cat_anh.py
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
VT = HERE.parents[1]
sys.path.insert(0, str(VT))
from fnb_common import square  # noqa: E402

OUT = HERE / 'anh'
CLIP = '01_phong_an_goc_cao'
ZONES = json.loads((VT / 'zones.json').read_text(encoding='utf-8'))[CLIP]['ban']
# đoạn T của từng bàn (giống tao_anh_ban_test.py)
T = {'B1': (1.25, 15.0), 'B2': (7.25, 15.0), 'B4': (1.25, 8.6)}
STEP = 0.125
SIZE = 256


def tight_box(pts, W, H, pad=0.10):
    x, y, w, h = cv2.boundingRect(np.array(pts, np.int32))
    return max(0, int(x - pad * w)), max(0, int(y - pad * h)), min(W, int(x + w + pad * w)), min(H, int(y + h + pad * h))


def square_box(pts, W, H, pad=0.10):
    x, y, w, h = cv2.boundingRect(np.array(pts, np.int32))
    s = int(round(max(w, h) * (1 + 2 * pad)))
    cx, cy = x + w / 2, y + h / 2
    x1 = int(round(min(max(0, cx - s / 2), W - s)))
    y1 = int(round(min(max(0, cy - s / 2), H - s)))
    return x1, y1, x1 + s, y1 + s


def to_input(im, box):
    x1, y1, x2, y2 = box
    return square(im[y1:y2, x1:x2], SIZE)


def poly_in_input(pts, box):
    """Toạ độ đa giác bàn trong ảnh 256x256 (sau khi thêm viền xám và thu nhỏ)."""
    x1, y1, x2, y2 = box
    w, h = x2 - x1, y2 - y1
    s = max(w, h)
    ox, oy = (s - w) // 2, (s - h) // 2
    k = SIZE / s
    return [[(px - x1 + ox) * k, (py - y1 + oy) * k] for px, py in pts]


def coverage(pts, boxes, W, H):
    m = np.zeros((H, W), np.uint8)
    cv2.fillPoly(m, [np.array(pts, np.int32)], 1)
    area = m.sum()
    if not boxes:
        return 0.0
    c = np.zeros_like(m)
    for x1, y1, x2, y2 in boxes:
        c[int(y1):int(y2), int(x1):int(x2)] = 1
    return float((m & c).sum() / area)


def main():
    from ultralytics import YOLO
    det = YOLO(str(VT / 'models' / 'yolo26s.pt'))
    cap = cv2.VideoCapture(str(VT / 'clips' / f'{CLIP}.mp4'))
    fps = cap.get(cv2.CAP_PROP_FPS)
    # việc cần làm theo số khung: (loại, bàn, thời điểm)
    jobs = {}
    for b, (a, e) in T.items():
        for t in np.arange(a, e - 1e-6, STEP):
            if t * fps > cap.get(cv2.CAP_PROP_FRAME_COUNT) - 1:
                continue
            jobs.setdefault(int(round(t * fps)), []).append(('ref', b, round(float(t), 3)))
    test_dir = VT / 'danh_gia' / 'anh_ban_test'
    for lab in ('sach', 'ban'):
        for f in sorted((test_dir / lab).glob('c01_*.jpg')):
            _, b, t = f.stem.split('_')
            jobs.setdefault(int(round(float(t) * fps)), []).append(('test', b, round(float(t), 3), lab, f))
    for k in ('chat', 'vuong'):
        (OUT / k).mkdir(parents=True, exist_ok=True)
    meta, diffs = [], []
    idx = -1
    last = max(jobs)
    while idx < last:
        ok, im = cap.read()
        idx += 1
        if not ok:
            break
        if idx not in jobs:
            continue
        H, W = im.shape[:2]
        r = det.predict(im, imgsz=1280, conf=0.3, classes=[0], half=True, verbose=False)[0]
        boxes = r.boxes.xyxy.cpu().numpy().tolist()
        for job in jobs[idx]:
            kind, b, t = job[:3]
            pts = ZONES[b]
            name = f"{'ref' if kind == 'ref' else 'test'}_{b}_{t:.3f}"
            rec = dict(ten=name, loai=kind, ban=b, t=t, khung=idx, che=round(coverage(pts, boxes, W, H), 3),
                       nguoi=[[round(v) for v in bx] for bx in boxes])
            for k, fn in (('chat', tight_box), ('vuong', square_box)):
                box = fn(pts, W, H)
                inp = to_input(im, box)
                cv2.imwrite(str(OUT / k / f'{name}.jpg'), inp, [cv2.IMWRITE_JPEG_QUALITY, 95])
                rec[f'hop_{k}'] = list(box)
                rec[f'da_giac_{k}'] = [[round(v, 1) for v in p] for p in poly_in_input(pts, box)]
            if kind == 'test':
                rec['nhan'], rec['file_goc'] = job[3], str(job[4].relative_to(VT)).replace('\\', '/')
                old = cv2.imread(str(job[4])).astype(np.float32)
                new = cv2.imread(str(OUT / 'chat' / f'{name}.jpg')).astype(np.float32)
                diffs.append(float(np.abs(old - new).mean()))
            meta.append(rec)
    (HERE / 'anh_meta.json').write_text(json.dumps(meta, ensure_ascii=False, indent=0), encoding='utf-8')
    n_ref = sum(m['loai'] == 'ref' for m in meta)
    print(f'{n_ref} ảnh tham chiếu, {len(meta) - n_ref} ảnh test cắt lại')
    print('lệch trung bình (0-255) giữa ảnh test cũ và cắt lại kiểu chat: '
          f'tb {np.mean(diffs):.2f}, lớn nhất {np.max(diffs):.2f}')
    for b in T:
        c = [m['che'] for m in meta if m['loai'] == 'ref' and m['ban'] == b]
        print(b, len(c), 'khung,', sum(x > 0.02 for x in c), 'khung có người che >2% mặt bàn')


if __name__ == '__main__':
    main()
