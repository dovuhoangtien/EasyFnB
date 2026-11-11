"""Hàm và danh sách dùng chung cho thử nghiệm "so với ảnh bàn sạch tham chiếu"."""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
VT = HERE.parents[1]
sys.path.insert(0, str(VT))
sys.path.insert(0, str(VT / 'danh_gia'))
from fnb_common import square  # noqa: E402

TEST_DIR = VT / 'danh_gia' / 'anh_ban_test'
CACHE = HERE / '_cache'
BANS = ('B1', 'B2', 'B4')  # bàn có đoạn T để lấy ảnh tham chiếu; B3 không có

# Khung có người / tay che mặt bàn trong đoạn T (người xem từng khung, xem anh_loi/nguoi_che.jpg).
NGUOI_CHE = {'B1': [6.0, 6.125, 6.25, 6.625, 6.75, 7.0, 7.375, 7.5, 7.625, 7.75, 7.875, 8.0, 8.125],
             'B2': [7.375, 7.625], 'B4': [8.5]}
# Không dùng làm ảnh tham chiếu: khung bị che, và khung đang dọn dở (khăn lau, khăn bàn gấp đang đặt xuống).
# Ngoài đời đây là lúc quản lý không bấm "Chụp bàn sạch" (hoặc màn hình cài đặt từ chối vì có người trong vùng bàn).
KHONG_LAM_THAM_CHIEU = {b: set(v) for b, v in NGUOI_CHE.items()}
KHONG_LAM_THAM_CHIEU['B1'] |= {6.875}
KHONG_LAM_THAM_CHIEU['B4'] |= {1.375}

# Đổi ánh sáng giả lập (chỉ đổi phần ảnh thật, không đổi viền xám)
ANH_SANG = {
    'toi_60': lambda x: x * 0.6,
    'sang_140': lambda x: x * 1.4,
    'den_vang': lambda x: x * np.array([0.8, 1.0, 1.15]),  # BGR: bớt xanh, thêm đỏ
    'toi_vang': lambda x: x * np.array([0.8, 1.0, 1.15]) * 0.7,
}


def meta():
    return json.loads((HERE / 'anh_meta.json').read_text(encoding='utf-8'))


def content_rect(box, size=256):
    """Vùng ảnh thật (không phải viền xám) trong ảnh 256x256."""
    x1, y1, x2, y2 = box
    w, h = x2 - x1, y2 - y1
    s = max(w, h)
    k = size / s
    ox, oy = (s - w) // 2, (s - h) // 2
    return int(round(ox * k)), int(round(oy * k)), int(round((ox + w) * k)), int(round((oy + h) * k))


def relight(img, box, fn):
    out = img.copy().astype(np.float32)
    x1, y1, x2, y2 = content_rect(box)
    out[y1:y2, x1:x2] = fn(out[y1:y2, x1:x2])
    return np.clip(out, 0, 255).astype(np.uint8)


def grid_mask(poly256, grid, dilate=0):
    """Ô vá (patch) nằm trong đa giác bàn: phần diện tích trong đa giác >= 50%."""
    if poly256 is None:
        return np.ones(grid * grid, bool)
    R = grid * 16
    m = np.zeros((R, R), np.uint8)
    cv2.fillPoly(m, [np.round(np.array(poly256) * R / 256).astype(np.int32)], 1)
    frac = m.reshape(grid, 16, grid, 16).mean((1, 3))
    g = frac >= 0.5
    if dilate:
        g = cv2.dilate(g.astype(np.uint8), np.ones((2 * dilate + 1, 2 * dilate + 1), np.uint8)) > 0
    return g.reshape(-1)


def load(path):
    img = cv2.imread(str(path))
    return square(img, 256) if img.shape[0] != img.shape[1] else img
