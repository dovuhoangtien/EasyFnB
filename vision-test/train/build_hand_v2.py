"""Bộ dữ liệu giơ tay v2 = ảnh lớp học (SCB) + ảnh người trong nhà hàng.

Model v1 chỉ học ảnh lớp học nên sang nhà hàng thì nhầm người cầm ly, ăn uống,
nghe điện thoại là giơ tay. Ở đây thêm ảnh người cắt từ footage nhà hàng:
- các ảnh model v1 nghi nhất đã được kiểm tra bằng mắt (file nhãn tay_*.txt):
  ô "g" là giơ tay thật -> lớp gio_tay, ô "?" bỏ, còn lại -> lớp khong
- các ảnh còn lại (model v1 không nghi) -> lớp khong
Chia train/val theo clip như build_labeled.py.

Bản v2 chỉ có giơ tay kiểu ảnh camera lớp học (SCB), nên model học lối tắt "ảnh kiểu SCB = giơ tay"
và bỏ sót giơ tay trong video thường. Bản v3 thêm --extra: ảnh ứng viên cắt từ footage Mixkit
(cut_raise_candidates.py), gán từng ô g (giơ tay) / k (không) / x (bỏ).

    python build_hand_v2.py <thư mục SCB đã làm> <thư mục bảng tay_> <nhãn tay_*.txt ...> --crops <ảnh người> --out <ra>
        [--extra <thư mục bảng> <file nhãn g/k/x>]... [--nhan-ban 4]
"""
import argparse
import hashlib
import os
import re
import shutil
from collections import Counter
from pathlib import Path


def link(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy(src, dst)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('scb', type=Path)
    ap.add_argument('sheets', type=Path)
    ap.add_argument('labels', type=Path, nargs='+')
    ap.add_argument('--crops', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--val', type=float, default=0.2)
    ap.add_argument('--extra', nargs=2, action='append', default=[], metavar=('THU_MUC_BANG', 'FILE_NHAN'),
                    help='thêm ảnh đã gán từng ô g/k/x (vd ảnh ứng viên giơ tay cắt từ footage Mixkit)')
    ap.add_argument('--toi-da-moi-clip', type=int, default=12,
                    help='số ảnh giơ tay tối đa lấy từ mỗi clip của --extra (nhiều khung gần giống nhau)')
    ap.add_argument('--nhan-ban', type=int, default=1,
                    help='chép ảnh giơ tay của --extra bao nhiêu lần vào train (để model không bỏ qua chúng)')
    args = ap.parse_args()
    cnt = Counter()
    for f in args.scb.rglob('*.jpg'):
        rel = f.relative_to(args.scb)
        link(f, args.out / rel)
        cnt[f'scb {rel.parts[0]}/{rel.parts[1]}'] += 1

    pos, skip = set(), set()
    for lf in args.labels:
        for line in lf.read_text(encoding='utf-8').splitlines():
            m = re.match(r'\s*(tay_\d+)\s*:\s*g=([\d,\s]*)\?=([\d,\s]*)', line)
            if not m:
                continue
            files = [l.strip() for l in (args.sheets / f'{m.group(1)}.txt').read_text(encoding='utf-8').splitlines()
                     if l.strip()]
            for grp, s in ((2, pos), (3, skip)):
                for c in re.findall(r'\d+', m.group(grp)):
                    s.add(Path(files[int(c) - 1]).name)
    # ảnh thêm (g/k/x từng ô): đọc trước để biết clip nào có người giơ tay thật
    extra, pos_clips = [], set()
    for sheets, lf in args.extra:
        for line in Path(lf).read_text(encoding='utf-8').splitlines():
            m = re.match(r'\s*([a-z]+_\d+)\s*:\s*([gkx]+)', line)
            if not m:
                continue
            files = [l.strip() for l in (Path(sheets) / f'{m.group(1)}.txt').read_text(encoding='utf-8').splitlines()
                     if l.strip()]
            for f, c in zip(files, m.group(2)):
                extra.append((Path(f), c))
                if c == 'g':
                    pos_clips.add(Path(f).stem.split('_')[0])
    verified = set()
    for txt in args.sheets.glob('tay_*.txt'):
        verified |= {Path(l.strip()).name for l in txt.read_text(encoding='utf-8').splitlines() if l.strip()}

    for f in sorted(args.crops.glob('*.jpg')):
        if f.name in skip:
            cnt['bo (?)'] += 1
            continue
        clip = f.stem.split('_')[0]
        if clip in pos_clips and f.name not in verified:
            cnt['bo (clip có người giơ tay, ảnh chưa kiểm tra)'] += 1
            continue
        split = 'val' if int(hashlib.md5(clip.encode()).hexdigest(), 16) % 100 < args.val * 100 else 'train'
        cls = 'gio_tay' if f.name in pos else 'khong'
        link(f, args.out / split / cls / f'nh_{f.name}')
        cnt[f'nha_hang {split}/{cls}'] += 1

    # mỗi clip chỉ lấy tối đa N ảnh giơ tay, cách đều nhau theo thời gian
    by_clip = {}
    for f, c in extra:
        if c == 'g':
            by_clip.setdefault(f.stem.split('_')[0], []).append(f)
    keep = set()
    for v in by_clip.values():
        v = sorted(v, key=lambda f: float(f.stem.split('_')[1]))
        step = max(1, len(v) / args.toi_da_moi_clip)
        keep |= {v[int(i * step)] for i in range(min(len(v), args.toi_da_moi_clip))}
    for f, c in extra:
        if c == 'g' and f not in keep:
            cnt['them bo (giơ tay trùng clip)'] += 1
            continue
        if c == 'x':
            cnt['them bo (x)'] += 1
            continue
        clip = f.stem.split('_')[0]
        split = 'val' if int(hashlib.md5(clip.encode()).hexdigest(), 16) % 100 < args.val * 100 else 'train'
        cls = 'gio_tay' if c == 'g' else 'khong'
        reps = args.nhan_ban if (cls == 'gio_tay' and split == 'train') else 1
        for r in range(reps):
            link(f, args.out / split / cls / f'th{r}_{f.name}')
        cnt[f'them {split}/{cls}'] += 1
    for k, v in sorted(cnt.items()):
        print(f'{k:>24}: {v}')


if __name__ == '__main__':
    main()
