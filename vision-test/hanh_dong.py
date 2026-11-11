"""Tỉ lệ hành động của từng người (ngồi ăn, uống, xem điện thoại, giơ tay gọi, vươn vai, đi, đứng,
bưng bê, dọn bàn), không cần train.

Cách làm: model ảnh-chữ PE-Core (đang chạy sẵn cho model giơ tay và model nhân viên) so ảnh cắt của
người với vài câu mô tả cho mỗi hành động, ra tỉ lệ. Rồi gộp với những gì camera đã biết chắc hơn từ
khung xương (đang đi, đứng hay ngồi, giơ hai tay, đang gọi, là nhân viên) và làm mượt theo thời gian,
để con số không nhảy từng khung.

Giới hạn: chỉ nhìn một khung hình, nên hành động phân biệt bằng chuyển động (ngáp, vươn vai) kém hơn.
Train model theo chuỗi khung xương (ví dụ trên NTU-120) là bước sau.

    python hanh_dong.py tao                      # tính sẵn vector câu mô tả (một lần, cần mạng lần đầu)
    python hanh_dong.py thu <ảnh.jpg> ...        # in tỉ lệ cho vài ảnh cắt người
"""
import math
import sys
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
KEY = 'pe_core_b16'
CACHE = HERE / 'models' / f'hanh_dong_{KEY}.pt'

# (mã, tên hiện trên màn hình, câu mô tả tiếng Anh: model hiểu tiếng Anh tốt hơn)
ACTIONS = [
    ('ngoi_an', 'ngồi ăn', ['a photo of a person sitting at a table eating a meal',
                            'a photo of a person eating food with chopsticks',
                            'a photo of a customer eating at a restaurant table']),
    ('uong', 'uống', ['a photo of a person drinking from a glass',
                      'a photo of a person drinking coffee from a cup']),
    ('dien_thoai', 'xem điện thoại', ['a photo of a person looking at a smartphone',
                                     'a photo of a person sitting and using a mobile phone']),
    ('tro_chuyen', 'trò chuyện', ['a photo of a person sitting and talking with friends at a table',
                                  'a photo of people chatting at a cafe table']),
    ('goi', 'giơ tay gọi', ['a photo of a person raising one hand to call a waiter',
                            'a photo of a customer raising a hand in a restaurant']),
    ('vuon_vai', 'vươn vai / ngáp', ['a photo of a person stretching both arms above the head',
                                    'a photo of a person yawning and stretching']),
    ('di', 'đi lại', ['a photo of a person walking', 'a photo of a person walking through a restaurant']),
    ('dung', 'đứng', ['a photo of a person standing still', 'a photo of a person standing next to a table']),
    ('phuc_vu', 'bưng / phục vụ', ['a photo of a waiter serving food to a table',
                                  'a photo of a waiter carrying a tray of drinks']),
    ('don_ban', 'dọn bàn', ['a photo of a person wiping a table',
                           'a photo of a waiter clearing dirty dishes from a table']),
]
CODES = [a[0] for a in ACTIONS]
LABELS = {a[0]: a[1] for a in ACTIONS}
IDX = {c: k for k, c in enumerate(CODES)}
NGOI = ('ngoi_an', 'uong', 'dien_thoai', 'tro_chuyen')


def tao():
    """Tính vector câu mô tả bằng phần chữ của PE-Core rồi lưu, để lúc chạy camera chỉ cần phần ảnh."""
    import open_clip

    from clip_cls import BACKBONES, safe_load_patch
    safe_load_patch()
    arch, pre = BACKBONES[KEY]
    model, _, _ = open_clip.create_model_and_transforms(arch, pretrained=pre, device='cpu')
    model.eval()
    tok = open_clip.get_tokenizer(arch)
    with torch.no_grad():
        text = torch.stack([torch.nn.functional.normalize(
            torch.nn.functional.normalize(model.encode_text(tok(p)).float(), dim=-1).mean(0), dim=-1)
            for _, _, p in ACTIONS])
        scale = float(model.logit_scale.exp())
    torch.save({'text': text, 'scale': scale, 'codes': CODES, 'backbone': KEY}, CACHE)
    print(f'đã lưu {CACHE.name}: {len(CODES)} hành động, scale {scale:.1f}')


class HanhDong:
    """Dùng chung phần ảnh với một ClipCls cùng bộ mã hoá (model giơ tay / nhân viên)."""

    def __init__(self, clip_model):
        if getattr(clip_model, 'key', None) != KEY:
            raise ValueError(f'cần model cùng bộ mã hoá {KEY}')
        if not CACHE.exists():
            tao()
        d = torch.load(CACHE, map_location='cpu', weights_only=True)
        if list(d['codes']) != CODES:
            tao()
            d = torch.load(CACHE, map_location='cpu', weights_only=True)
        self.m = clip_model
        self.text = d['text'].to(clip_model.dev)
        self.scale = d['scale']
        self.ema = {}   # mã người -> (t, vector tỉ lệ đã làm mượt)

    @torch.no_grad()
    def clip_probs(self, crops):
        if not crops:
            return np.zeros((0, len(CODES)))
        f = self.m.features(crops)
        return (self.scale * f @ self.text.T).softmax(-1).cpu().numpy()

    @staticmethod
    def gop(p, di=False, dung=False, nv=False, goi=None, vuon=False):
        """Gộp tỉ lệ của model ảnh với điều camera đã biết từ khung xương và model khác (nhân hệ số rồi chuẩn hoá).
        goi=None: không dùng kết luận "đang gọi" của bộ giơ tay (bản này dùng để kiểm tra chéo bộ giơ tay)."""
        w = np.ones(len(CODES))

        def mul(codes, k):
            for c in codes:
                w[IDX[c]] *= k
        if di:
            mul(['di'], 4)
            mul(NGOI + ('dung',), 0.3)
        elif dung:
            mul(['dung'], 2)
            mul(NGOI, 0.4)
            mul(['di'], 0.5)
        else:   # ngồi hoặc không rõ chân (thường là ngồi sau bàn)
            mul(['di'], 0.2)
            mul(['dung'], 0.3)
        if nv:
            mul(['phuc_vu', 'don_ban'], 3)
            mul(list(NGOI), 0.2)
            mul(['goi'], 0.02)   # nhân viên bưng khay giơ cao trông giống giơ tay, mà nhân viên không gọi phục vụ
        else:
            mul(['phuc_vu', 'don_ban'], 0.3)
        if vuon:
            mul(['vuon_vai'], 5)
            mul(['goi'], 0.2)
        elif goi:
            mul(['goi'], 5)
        elif goi is False:
            mul(['goi'], 0.4)
        q = p * w
        return q / q.sum()

    def cap_nhat(self, pid, t, p, tau=1.5):
        """Làm mượt theo thời gian (hằng số tau giây), trả vector tỉ lệ hiện tại của người pid."""
        old = self.ema.get(pid)
        if old is None:
            v = p
        else:
            a = 1 - math.exp(-max(0.0, t - old[0]) / tau)
            v = old[1] + a * (p - old[1])
        self.ema[pid] = (t, v)
        return v

    def hien(self, pid):
        v = self.ema.get(pid)
        return None if v is None else v[1]

    def xoa(self):
        self.ema.clear()


def top(v, k=3):
    if v is None:
        return []
    o = np.argsort(-v)[:k]
    return [(CODES[i], float(v[i])) for i in o]


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == 'tao':
        tao()
        return
    if len(sys.argv) >= 3 and sys.argv[1] == 'thu':
        import cv2

        from clip_cls import ClipCls
        hd = HanhDong(ClipCls(head=str(HERE / 'models' / 'giotay_pe_b16.pt')))
        ims = [cv2.imread(f) for f in sys.argv[2:]]
        for f, p in zip(sys.argv[2:], hd.clip_probs(ims)):
            print(Path(f).name, ', '.join(f'{LABELS[c]} {v:.0%}' for c, v in top(p, 4)))
        return
    print(__doc__)


if __name__ == '__main__':
    main()
