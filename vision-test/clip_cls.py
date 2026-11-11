"""Phân loại ảnh cắt bằng CLIP (model đã học sẵn hình ảnh + chữ), dùng cho bàn và người.

Hai cách dùng:
- không train: so ảnh với câu mô tả (hiện có sẵn câu cho bàn sạch / bàn bẩn)
- có train: học thêm một lớp nhỏ (hồi quy logistic) trên đặc trưng CLIP từ ảnh đã gán nhãn

    python clip_cls.py thu <thư mục có sach/ và ban/>                       # bàn, không train
    python clip_cls.py train <thư mục train> --lop sach ban --out models/ban_clip.pt
    python clip_cls.py train <thư mục train> --lop khach nhan_vien --out models/nhanvien_clip.pt
    python clip_cls.py thu <thư mục> --model models/nhanvien_clip.pt         # chấm model đã học

Lớp thứ hai trong --lop là lớp "dương": model trả xác suất của lớp đó.
"""
import argparse
import sys
from pathlib import Path

import cv2
import numpy as np
import torch

from fnb_common import square

# Các bộ mã hoá ảnh-chữ dùng được (tên ngắn -> tên trong open_clip). Bản đầu tiên là bản cũ.
BACKBONES = {
    'b32_laion': ('ViT-B-32', 'laion2b_s34b_b79k'),
    'b32_datacomp': ('ViT-B-32', 'datacomp_xl_s13b_b90k'),
    'siglip2_b32': ('ViT-B-32-SigLIP2-256', 'webli'),
    'siglip2_b16': ('ViT-B-16-SigLIP2', 'webli'),
    'mobileclip2_s0': ('MobileCLIP2-S0', 'dfndr2b'),
    'mobileclip2_s2': ('MobileCLIP2-S2', 'dfndr2b'),
    'mobileclip2_b': ('MobileCLIP2-B', 'dfndr2b'),
    'pe_core_s16': ('PE-Core-S-16-384', 'meta'),
    'pe_core_b16': ('PE-Core-B-16', 'meta'),
    'dfn_b16': ('ViT-B-16', 'dfn2b'),
    'siglip2_l16': ('ViT-L-16-SigLIP2-256', 'webli'),
    'pe_core_l14': ('PE-Core-L-14-336', 'meta'),
}
DEFAULT = 'b32_laion'
ARCH, WEIGHTS = BACKBONES[DEFAULT]
PROMPTS = {
    'sach': ['a photo of a clean empty table', 'a photo of a neatly set restaurant table with clean plates and glasses',
             'a photo of an empty dining table ready for guests'],
    'ban': ['a photo of a dirty table with leftover food and used dishes',
            'a photo of a messy restaurant table after a meal with crumpled napkins',
            'a photo of a table with food and drinks on it'],
}
_BACKBONE = {}


def set_default(key):
    """Đổi bộ mã hoá mặc định (dùng cho bàn không train và khi train lớp nhỏ mới)."""
    global DEFAULT
    if key not in BACKBONES:
        raise ValueError(f'không có bộ mã hoá {key}; có: {list(BACKBONES)}')
    DEFAULT = key


def safe_load_patch():
    """safetensors 0.8 trên Windows có lúc crash khi nạp cả file lớn một lần lúc máy thiếu RAM.
    Nạp từng tensor tốn ít RAM hơn. Máy còn quá ít RAM thì vẫn có thể crash: đừng chạy nhiều việc cùng lúc."""
    import safetensors.torch as st
    from safetensors import safe_open
    if getattr(st.load_file, '_tung_phan', False):
        return

    def load_file(filename, device='cpu', **_):
        with safe_open(filename, framework='pt', device=str(device)) as f:
            return {k: f.get_tensor(k) for k in f.keys()}
    load_file._tung_phan = True
    st.load_file = load_file


def backbone(dev, key=None):
    """Phần ảnh của một bộ mã hoá, dùng chung cho mọi bộ phân loại cùng bộ mã hoá.

    Chỉ giữ phần ảnh (trên GPU thì ở FP16). Phần chữ chỉ dùng một lần để tính sẵn câu mô tả bàn
    sạch/bẩn rồi bỏ đi: phần chữ của vài model mới (PE-Core, SigLIP 2) còn to hơn phần ảnh.
    Trả (phần ảnh, cách chuẩn bị ảnh, vector câu mô tả [sach, ban]).
    """
    key = key or DEFAULT
    if (dev, key) not in _BACKBONE:
        import gc

        import open_clip
        safe_load_patch()
        arch, pre = BACKBONES[key]
        model, _, prep = open_clip.create_model_and_transforms(arch, pretrained=pre, device='cpu')
        model.eval()
        tok = open_clip.get_tokenizer(arch)
        with torch.no_grad():
            text = torch.stack([torch.nn.functional.normalize(torch.nn.functional.normalize(
                model.encode_text(tok(PROMPTS[k])).float(), dim=-1).mean(0), dim=-1) for k in ('sach', 'ban')])
        visual = model.visual.to(dev).eval()
        if dev == 'cuda':
            visual.half()
        del model
        gc.collect()
        _BACKBONE[(dev, key)] = (visual, prep, text.to(dev))
    return _BACKBONE[(dev, key)]


class ClipCls:
    """Trả xác suất lớp "dương" cho danh sách ảnh cắt (BGR).

    head=None: không train, so với câu mô tả bàn bẩn. head=file .pt: lớp nhỏ đã học.
    """

    def __init__(self, head=None, device=None, backbone_key=None):
        self.dev = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        d = torch.load(head, map_location='cpu', weights_only=True) if head else None
        # lớp nhỏ ghi lại nó được train trên bộ mã hoá nào; file cũ không ghi = bản cũ b32_laion
        self.key = (d.get('backbone', 'b32_laion') if d else None) or backbone_key or DEFAULT
        self.visual, self.prep, self.text = backbone(self.dev, self.key)
        self.head, self.classes = None, ['sach', 'ban']
        if d:
            self.head = (d['w'].to(self.dev), d['b'].to(self.dev))
            self.classes = list(d.get('classes', self.classes))

    @property
    def names(self):
        return dict(enumerate(self.classes))

    @torch.no_grad()
    def features(self, crops, bs=64):
        from PIL import Image
        out = []
        for i in range(0, len(crops), bs):
            x = torch.stack([self.prep(Image.fromarray(cv2.cvtColor(square(c), cv2.COLOR_BGR2RGB)))
                             for c in crops[i:i + bs]]).to(self.dev)
            f = self.visual(x.half() if self.dev == 'cuda' else x)
            out.append(torch.nn.functional.normalize(f.float(), dim=-1))
        return torch.cat(out) if out else torch.zeros((0, 1), device=self.dev)

    @torch.no_grad()
    def p_pos(self, crops):
        if not crops:
            return []
        f = self.features(crops)
        if self.head is not None:
            w, b = self.head
            return torch.sigmoid(f @ w + b).cpu().tolist()
        return (100 * f @ self.text.T).softmax(-1)[:, 1].cpu().tolist()


def load_dir(d, classes):
    files, ys = [], []
    for y, cls in enumerate(classes):
        for f in sorted((d / cls).glob('*.jpg')):
            files.append(f)
            ys.append(y)
    return files, np.array(ys)


def read(files):
    return [cv2.imread(str(f)) for f in files]


def report(name, ys, p, classes, th=0.5):
    pred = (np.array(p) >= th).astype(int)
    parts = [f'{c} đúng {((pred == k) & (ys == k)).sum()}/{(ys == k).sum()}' for k, c in enumerate(classes)]
    acc = (pred == ys).mean()
    print(f'{name}: đúng {acc:.1%}  | ' + '  | '.join(parts))
    return acc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('lenh', choices=['thu', 'train'])
    ap.add_argument('data', type=Path, nargs='+')
    ap.add_argument('--model', type=Path, default=None)
    ap.add_argument('--lop', nargs=2, default=['sach', 'ban'], help='lớp âm, lớp dương')
    ap.add_argument('--out', type=Path, default=None)
    ap.add_argument('--C', type=float, default=1.0)
    ap.add_argument('--backbone', default=DEFAULT, choices=list(BACKBONES))
    args = ap.parse_args()
    set_default(args.backbone)
    if args.lenh == 'thu':
        ct = ClipCls(head=args.model)
        for d in args.data:
            files, ys = load_dir(d, ct.classes)
            report(f'{d.name} ({"có train" if args.model else "không train"})', ys, ct.p_pos(read(files)), ct.classes)
        return
    from sklearn.linear_model import LogisticRegression
    ct = ClipCls()
    X, Y = [], []
    for d in args.data:
        files, ys = load_dir(d, args.lop)
        X.append(ct.features(read(files)).cpu().numpy())
        Y.append(ys)
    X, Y = np.concatenate(X), np.concatenate(Y)
    print('ảnh train:', len(Y), ', '.join(f'{c} {int((Y == k).sum())}' for k, c in enumerate(args.lop)))
    lr = LogisticRegression(C=args.C, class_weight='balanced', max_iter=2000).fit(X, Y)
    report('trên chính tập train', Y, lr.predict_proba(X)[:, 1], args.lop)
    torch.save({'w': torch.tensor(lr.coef_[0], dtype=torch.float32), 'b': torch.tensor(lr.intercept_[0], dtype=torch.float32),
                'classes': args.lop, 'backbone': args.backbone}, args.out)
    print('đã lưu', args.out)


if __name__ == '__main__':
    sys.exit(main())
