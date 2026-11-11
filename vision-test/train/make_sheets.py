"""Ghép ảnh cắt thành bảng 5x5 có đánh số 1-25 để người (hoặc AI) gán nhãn nhanh.

    python make_sheets.py <danh sách file .txt> <thư mục ra> [--prefix ban]

Mỗi bảng NNN.jpg có NNN.txt kèm theo: dòng thứ k là file ảnh ở ô số k.
"""
import argparse
from pathlib import Path

import cv2
import numpy as np

CELL, GRID = 200, 5


def cell(path):
    im = cv2.imread(str(path))
    out = np.full((CELL, CELL, 3), 255, np.uint8)
    if im is None:
        return out
    s = (CELL - 4) / max(im.shape[:2])
    im = cv2.resize(im, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    h, w = im.shape[:2]
    y, x = (CELL - h) // 2, (CELL - w) // 2
    out[y:y + h, x:x + w] = im
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('listfile', type=Path)
    ap.add_argument('out', type=Path)
    ap.add_argument('--prefix', default='s')
    args = ap.parse_args()
    files = [l.strip() for l in args.listfile.read_text(encoding='utf-8').splitlines() if l.strip()]
    args.out.mkdir(parents=True, exist_ok=True)
    per = GRID * GRID
    for si in range(0, len(files), per):
        chunk = files[si:si + per]
        board = np.full((GRID * CELL, GRID * CELL, 3), 255, np.uint8)
        for k, f in enumerate(chunk):
            r, c = divmod(k, GRID)
            board[r * CELL:(r + 1) * CELL, c * CELL:(c + 1) * CELL] = cell(f)
            cv2.rectangle(board, (c * CELL, r * CELL), ((c + 1) * CELL - 1, (r + 1) * CELL - 1), (200, 200, 200), 1)
            cv2.rectangle(board, (c * CELL, r * CELL), (c * CELL + 34, r * CELL + 26), (0, 0, 0), -1)
            cv2.putText(board, str(k + 1), (c * CELL + 3, r * CELL + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.65,
                        (255, 255, 255), 2)
        name = f'{args.prefix}_{si // per + 1:03d}'
        cv2.imwrite(str(args.out / f'{name}.jpg'), board, [cv2.IMWRITE_JPEG_QUALITY, 88])
        (args.out / f'{name}.txt').write_text('\n'.join(chunk), encoding='utf-8')
    print('bảng:', (len(files) + per - 1) // per)


if __name__ == '__main__':
    main()
