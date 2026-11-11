"""Đổi mọi ảnh .jpg trong một thư mục (kể cả thư mục con) thành hình vuông 256 px có viền xám, ghi đè tại chỗ."""
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fnb_common import square  # noqa: E402


def one(f):
    im = cv2.imread(str(f))
    if im is not None and not (im.shape[0] == im.shape[1] == 256):
        cv2.imwrite(str(f), square(im, 256), [cv2.IMWRITE_JPEG_QUALITY, 92])


files = list(Path(sys.argv[1]).rglob('*.jpg'))
with ThreadPoolExecutor(8) as ex:
    list(ex.map(one, files))
print(len(files), 'ảnh')
