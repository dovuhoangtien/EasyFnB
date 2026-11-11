"""Train lớp nhỏ "giơ tay" trên đặc trưng CLIP (bản đang dùng: models/giotay_clip_v1.pt).

Dữ liệu là thư mục do build_hand_v2.py tạo (train/ và val/, mỗi bên gio_tay/ và khong/).
Tên file cho biết nguồn: "th*_" = ảnh từ video thường đã gán nhãn, "nh_" = ảnh người nhà hàng,
còn lại = ảnh lớp học SCB. Ảnh SCB rất nhiều nên chỉ lấy mẫu, còn ảnh giơ tay từ video thường
được tăng trọng số để model không học lối tắt "ảnh kiểu SCB = giơ tay".

    python train_tay_clip.py <thư mục dữ liệu> --out models/giotay_clip_v1.pt
"""
import argparse
import random
import sys
from pathlib import Path

import cv2
import numpy as np
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from clip_cls import BACKBONES, ClipCls  # noqa: E402


def groups(d):
    vid = lambda c: sorted(f for f in (d / c).glob('*.jpg') if f.name.startswith(('th', 'nh_')))
    scb = lambda c: sorted(f for f in (d / c).glob('*.jpg') if not f.name.startswith(('th', 'nh_')))
    return {'video_gio': vid('gio_tay'), 'video_khong': vid('khong'), 'scb_gio': scb('gio_tay'), 'scb_khong': scb('khong')}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('data', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--C', type=float, default=0.3)
    ap.add_argument('--scb', type=int, default=2500, help='số ảnh SCB mỗi lớp lấy vào train')
    ap.add_argument('--trong-so-video', type=float, default=10.0, help='trọng số ảnh giơ tay từ video thường')
    ap.add_argument('--backbone', default='b32_laion', choices=list(BACKBONES))
    args = ap.parse_args()
    from sklearn.linear_model import LogisticRegression
    random.seed(0)
    ct = ClipCls(backbone_key=args.backbone)

    def feats(fs):
        return np.concatenate([ct.features([cv2.imread(str(f)) for f in fs[i:i + 128]]).cpu().numpy()
                               for i in range(0, len(fs), 128)])

    tr, va = groups(args.data / 'train'), groups(args.data / 'val')
    # ảnh giơ tay video thường đã được chép nhiều lần (th0_, th1_...): chỉ lấy một bản, trọng số lo phần còn lại
    tr['video_gio'] = sorted({f.name.split('_', 1)[1] if f.name.startswith('th') else f.name: f
                              for f in tr['video_gio']}.values())
    tr['scb_gio'] = random.sample(tr['scb_gio'], min(args.scb, len(tr['scb_gio'])))
    tr['scb_khong'] = random.sample(tr['scb_khong'], min(args.scb, len(tr['scb_khong'])))
    print('ảnh train:', {k: len(v) for k, v in tr.items()})
    X = {k: feats(v) for k, v in tr.items()}
    Xa = np.concatenate([X['video_gio'], X['scb_gio'], X['video_khong'], X['scb_khong']])
    y = np.r_[np.ones(len(X['video_gio']) + len(X['scb_gio'])), np.zeros(len(X['video_khong']) + len(X['scb_khong']))]
    w = np.r_[np.full(len(X['video_gio']), args.trong_so_video), np.ones(len(Xa) - len(X['video_gio']))]
    lr = LogisticRegression(C=args.C, max_iter=3000).fit(Xa, y, sample_weight=w)
    for th in (0.5, 0.3):
        parts = []
        for k, fs in va.items():
            p = lr.predict_proba(feats(fs))[:, 1] if fs else np.zeros(0)
            parts.append(f'{k}: báo giơ {int((p >= th).sum())}/{len(fs)}')
        print(f'val, ngưỡng {th}: ' + ' | '.join(parts))
    torch.save({'w': torch.tensor(lr.coef_[0], dtype=torch.float32), 'b': torch.tensor(lr.intercept_[0], dtype=torch.float32),
                'classes': ['khong', 'gio_tay'], 'backbone': args.backbone}, args.out)
    print('đã lưu', args.out)


if __name__ == '__main__':
    main()
