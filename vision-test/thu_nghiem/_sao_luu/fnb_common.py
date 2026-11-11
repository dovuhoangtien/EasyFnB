"""Hàm dùng chung cho pipeline và các script train."""
import math

import cv2
import numpy as np


def square(img, size=None, color=114):
    """Thêm viền xám cho ảnh thành hình vuông (không cắt mất phần nào).

    YOLO-cls thu cạnh ngắn rồi cắt giữa, nên ảnh người cao 2:1 sẽ mất đầu và tay giơ.
    Đưa về hình vuông trước khi train và khi chạy thì không mất gì.
    """
    h, w = img.shape[:2]
    s = max(h, w)
    out = np.full((s, s, 3), color, np.uint8)
    y, x = (s - h) // 2, (s - w) // 2
    out[y:y + h, x:x + w] = img
    if size and s != size:
        out = cv2.resize(out, (size, size), interpolation=cv2.INTER_AREA if s > size else cv2.INTER_LINEAR)
    return out


def pad_box(frame, b, pad=0.08):
    """Cắt khung b, nới `pad` theo kích thước khung (giống lúc tạo dữ liệu train)."""
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = b
    bw, bh = x2 - x1, y2 - y1
    x1, y1 = max(0, int(x1 - pad * bw)), max(0, int(y1 - pad * bh))
    x2, y2 = min(w, int(x2 + pad * bw)), min(h, int(y2 + pad * bh))
    return frame[y1:y2, x1:x2]


def rect_size(w, h, size, stride=32):
    """Cỡ ảnh [cao, rộng] mà YOLO dùng khi thu cạnh dài về `size`. Model đã xuất (TensorRT, ONNX...)
    có cỡ cố định, nên phải đưa đúng cỡ này."""
    s = size / max(w, h)
    return [int(math.ceil(h * s / stride) * stride), int(math.ceil(w * s / stride) * stride)]
