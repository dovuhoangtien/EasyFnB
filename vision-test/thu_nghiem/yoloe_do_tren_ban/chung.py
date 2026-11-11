"""Hàm dùng chung cho thử nghiệm YOLOE-26 nhìn đồ trên bàn.

Không sửa pipeline: chỉ đọc clips/, zones.json, danh_gia/ và model yolo26s có sẵn.
Model YOLOE tải về thư mục weights/ cạnh file này.
"""
import json
import os
import sys
import types
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
VT = HERE.parents[1]                      # vision-test/
WEIGHTS = HERE / 'weights'
CACHE = HERE / 'ket_qua'
CLIPS = VT / 'clips'
WEIGHTS.mkdir(exist_ok=True)
CACHE.mkdir(exist_ok=True)

# Ultralytics mã hoá chữ cho YOLOE bằng MobileCLIP (TorchScript) + bộ tách từ của OpenAI CLIP (gói `clip`).
# Venv không có gói `clip` và Ultralytics sẽ tự pip install từ GitHub nếu thiếu. Để không đụng vào venv dùng chung,
# mình mượn bộ tách từ của open_clip (cùng file BPE của OpenAI, cùng cách làm sạch chữ, cùng độ dài 77).
if 'clip' not in sys.modules:
    try:
        import clip  # noqa: F401
    except ImportError:
        from open_clip import tokenizer as _oct
        _m, _s = types.ModuleType('clip'), types.ModuleType('clip.clip')
        _s.tokenize = lambda texts, context_length=77, truncate=True: _oct.tokenize(texts, context_length)
        _m.clip, _m.tokenize = _s, _s.tokenize
        sys.modules['clip'], sys.modules['clip.clip'] = _m, _s

# Câu nhắc (tiếng Anh: bộ mã hoá chữ chỉ học tiếng Anh, xem thu_tieng_viet trong chay_yoloe.py)
PROMPTS = ['plate', 'bowl', 'cup', 'glass', 'bottle', 'can', 'chopsticks', 'spoon', 'fork', 'knife',
           'napkin', 'tissue', 'tray', 'food', 'leftovers', 'phone', 'bag', 'menu', 'teapot', 'paper', 'wrapper']
# Luật "bàn bẩn" đề bài đưa ra
RULE = ['plate', 'bowl', 'cup', 'glass', 'bottle', 'chopsticks', 'napkin', 'tray', 'food', 'leftovers']

# COCO: lớp đồ trên bàn mà pipeline đang dùng (easyfnb_test.ITEMS)
COCO_ITEMS = {39: 'bottle', 40: 'wine glass', 41: 'cup', 42: 'fork', 43: 'knife', 44: 'spoon', 45: 'bowl',
              46: 'banana', 47: 'apple', 48: 'sandwich', 49: 'orange', 50: 'broccoli', 51: 'carrot',
              52: 'hot dog', 53: 'pizza', 54: 'donut', 55: 'cake'}

# Bàn tròn clip 09 không có trong zones.json: vẽ tay mặt bàn (chỉ để lọc đồ cho phần xem bằng mắt)
EXTRA_ZONES = {
    '09_nhom_ban_tron': {'ban': {'B1': [[0, 470], [1225, 470], [1225, 610], [0, 610]]}},
    # clip 03: cả khung hình là một bàn
    '03_ban_an_xong_tu_tren': {'ban': {'B1': [[0, 0], [1280, 0], [1280, 720], [0, 720]]}},
}


def zones():
    z = json.loads((VT / 'zones.json').read_text(encoding='utf-8'))
    z.update(EXTRA_ZONES)
    return z


def labels():
    return json.loads((VT / 'danh_gia' / 'dap_an.json').read_text(encoding='utf-8'))


def clip_path(name):
    return CLIPS / f'{name}.mp4'


class Frames:
    """Đọc khung hình theo giây (giống tao_anh_ban_test.py: làm tròn số khung)."""

    def __init__(self):
        self.caps = {}

    def get(self, clip, t):
        if clip not in self.caps:
            cap = cv2.VideoCapture(str(clip_path(clip)))
            self.caps[clip] = (cap, cap.get(cv2.CAP_PROP_FPS))
        cap, fps = self.caps[clip]
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(round(t * fps)))
        ok, im = cap.read()
        return im if ok else None


def table_crop_box(poly, W, H, pad=0.10):
    """Khung cắt bàn giống danh_gia/tao_anh_ban_test.py (nới 10%)."""
    x, y, w, h = cv2.boundingRect(np.array(poly, np.int32))
    x1, y1 = max(0, int(x - pad * w)), max(0, int(y - pad * h))
    x2, y2 = min(W, int(x + w + pad * w)), min(H, int(y + h + pad * h))
    return x1, y1, x2, y2


def owner(box, tables, margin=12):
    """Bàn sở hữu món đồ: bàn chứa tâm món đồ sâu nhất, cho lệch mép tối đa `margin` px (như pipeline)."""
    c = ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)
    best, bd = None, -1e9
    for name, poly in tables.items():
        d = cv2.pointPolygonTest(np.array(poly, np.float32), c, True)
        if d > bd:
            best, bd = name, d
    return best if bd > -margin else None


def load_yoloe(name, classes=PROMPTS):
    """YOLOE có câu nhắc chữ (name không có -pf) hoặc YOLOE không câu nhắc (-pf, 4.585 lớp có sẵn)."""
    from ultralytics import YOLOE
    cwd = os.getcwd()
    os.chdir(WEIGHTS)  # MobileCLIP được tải về thư mục hiện tại
    try:
        m = YOLOE(str(WEIGHTS / name))
        if not name.endswith('-pf.pt') and classes:
            m.set_classes(list(classes))
    finally:
        os.chdir(cwd)
    return m


def load_coco(engine=False):
    from ultralytics import YOLO
    if engine and (VT / 'models' / 'yolo26s_736x1280_fp16.engine').exists():
        return YOLO(str(VT / 'models' / 'yolo26s_736x1280_fp16.engine'), task='detect')
    return YOLO(str(VT / 'models' / 'yolo26s.pt'))


def run(model, im, imgsz, conf, classes=None, half=True):
    """Chạy một ảnh, trả về list (tên lớp, conf, [x1,y1,x2,y2])."""
    kw = dict(imgsz=imgsz, conf=conf, verbose=False, half=half, device=0)
    if classes is not None:
        kw['classes'] = classes
    r = model.predict(im, **kw)[0]
    names = r.names
    out = []
    if r.boxes is not None and len(r.boxes):
        for c, s, b in zip(r.boxes.cls.cpu().numpy(), r.boxes.conf.cpu().numpy(), r.boxes.xyxy.cpu().numpy()):
            out.append((names[int(c)], round(float(s), 4), [round(float(v), 1) for v in b]))
    return out


def iou(a, b):
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0
