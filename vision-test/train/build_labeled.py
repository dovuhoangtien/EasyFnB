"""Gom nhãn từ các bảng ảnh thành bộ dữ liệu train/val cho YOLO-cls.

    python build_labeled.py <thư mục bảng> <file nhãn ...> --out <thư mục ra> --kind ban|nguoi

File nhãn: mỗi dòng "ban_001: ssbbx..." (xem HUONG_DAN_GAN_NHAN.md). Các file nhãn sau
ghi đè file trước (dùng để sửa nhãn). Chia train/val theo clip (khoảng 80/20), để ảnh
cùng một clip không nằm ở cả hai bên.
"""
import argparse
import hashlib
import re
import shutil
from collections import Counter
from pathlib import Path

CLASSES = {'ban': {'s': 'sach', 'b': 'ban'}, 'nguoi': {'n': 'nhan_vien', 'k': 'khach'}}


def clip_of(path):
    return Path(path).stem.split('_')[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('sheets', type=Path)
    ap.add_argument('labels', type=Path, nargs='+')
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--kind', choices=list(CLASSES), required=True)
    ap.add_argument('--val', type=float, default=0.2)
    args = ap.parse_args()
    lab = {}
    for f in args.labels:
        for line in f.read_text(encoding='utf-8').splitlines():
            m = re.match(r'\s*([a-z]+_\d+)\s*:\s*([a-z]+)', line)
            if m and m.group(1).startswith(args.kind):
                lab[m.group(1)] = m.group(2)
    cmap = CLASSES[args.kind]
    count = Counter()
    for sheet, codes in sorted(lab.items()):
        lst = args.sheets / f'{sheet}.txt'
        if not lst.exists():
            print('không thấy bảng', sheet)
            continue
        files = [l.strip() for l in lst.read_text(encoding='utf-8').splitlines() if l.strip()]
        if len(codes) != len(files):
            print(f'{sheet}: {len(codes)} nhãn cho {len(files)} ảnh, bỏ qua phần lệch')
        for f, c in zip(files, codes):
            if c not in cmap:
                count['bo'] += 1
                continue
            h = int(hashlib.md5(clip_of(f).encode()).hexdigest(), 16) % 100
            split = 'val' if h < args.val * 100 else 'train'
            d = args.out / split / cmap[c]
            d.mkdir(parents=True, exist_ok=True)
            shutil.copy(f, d / Path(f).name)
            count[f'{split}/{cmap[c]}'] += 1
    print(dict(count))


if __name__ == '__main__':
    main()
