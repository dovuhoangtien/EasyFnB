"""Bước 2: tính đặc trưng và khoảng cách giữa mỗi ảnh cần chấm với mọi ảnh tham chiếu của cùng bàn.

Một lần chạy PE-Core S/16 (đúng như danh_gia/so_clip.py: cả model, autocast FP16) cho ra:
  - vector toàn ảnh (dùng cho bộ phân loại hiện tại: so với câu mô tả bàn sạch/bẩn) và cách "toàn ảnh",
  - vá (patch) 24x24 ở lớp cuối và lớp 8/12 cho cách "bộ nhớ vá" kiểu AnomalyDINO.
Thêm DINOv2-S/14 (timm, Apache-2.0) ở 448x448 = 32x32 vá, giống AnomalyDINO.

Với mỗi cặp (ảnh chấm, ảnh tham chiếu cùng bàn) lưu khoảng cách gần nhất của từng vá tới các vá của ảnh tham chiếu
(1 - cos). Khi chọn k ảnh tham chiếu, khoảng cách tới bộ nhớ gộp = min theo k ảnh, nên thử bao nhiêu cách chọn
cũng không cần chạy lại model.

    python thu_nghiem/ban_sach_tham_chieu/tinh_dac_trung.py
"""
import json
import time

import numpy as np
import torch
from PIL import Image

from chung import (ANH_SANG, BANS, CACHE, HERE, KHONG_LAM_THAM_CHIEU, TEST_DIR, grid_mask, load, meta,
                   relight)
import cv2

MID = 7  # lớp 8 trên 12 (khoảng 2/3 độ sâu), chọn trước khi chạy, không dò theo điểm


class Encoders:
    def __init__(self, dev='cuda'):
        import timm
        from clip_cls import PROMPTS
        from so_clip import Enc
        self.dev = dev
        self.pe = Enc('pe_core_s16', dev)
        self.txt = torch.tensor(self.pe.texts(PROMPTS), device=dev)
        self.dino = timm.create_model('vit_small_patch14_dinov2.lvd142m', pretrained=True, num_classes=0,
                                      img_size=448).to(dev).eval().half()
        self.mean = torch.tensor([0.485, 0.456, 0.406], device=dev).view(1, 3, 1, 1)
        self.std = torch.tensor([0.229, 0.224, 0.225], device=dev).view(1, 3, 1, 1)

    @torch.no_grad()
    def __call__(self, imgs):
        rgb = [Image.fromarray(cv2.cvtColor(im, cv2.COLOR_BGR2RGB)) for im in imgs]
        x = torch.stack([self.pe.prep(r) for r in rgb]).to(self.dev)
        v = self.pe.model.visual
        with torch.autocast('cuda', dtype=torch.float16):
            last, inter = v.trunk.forward_intermediates(x, indices=[MID], norm=False, output_fmt='NLC')
            g = v.head(v.trunk.forward_head(last))
        g = torch.nn.functional.normalize(g.float(), dim=-1)
        p = (100 * g @ self.txt.T).softmax(-1)[:, 1]
        npt = v.trunk.num_prefix_tokens
        tl = torch.nn.functional.normalize(last[:, npt:].float(), dim=-1).half()
        tm = inter[0]
        tm = torch.nn.functional.normalize((tm[:, npt:] if tm.shape[1] == 577 else tm).float(), dim=-1).half()
        xd = torch.stack([torch.from_numpy(np.asarray(r.resize((448, 448), Image.BICUBIC))) for r in rgb])
        xd = ((xd.to(self.dev).permute(0, 3, 1, 2).float() / 255 - self.mean) / self.std).half()
        fd = self.dino.forward_features(xd)[:, self.dino.num_prefix_tokens:]
        td = torch.nn.functional.normalize(fd.float(), dim=-1).half()
        return dict(g=g, p=p, pe_last=tl, pe_mid=tm, dino=td)


GRID = {'pe_last': 24, 'pe_mid': 24, 'dino': 32}


def nn_dist(q, R, rmask):
    """q [P,C], R [n,P,C], rmask [n,P] -> khoảng cách gần nhất từng vá của q tới từng ảnh R: (tất cả vá, chỉ vá bàn)."""
    n, P, C = R.shape
    out_all, out_msk = [], []
    for i in range(0, n, 16):
        s = (q @ R[i:i + 16].reshape(-1, C).T).view(q.shape[0], -1, P).float()  # [Pq, b, P]
        out_all.append(1 - s.max(-1).values)
        s.masked_fill_(~rmask[i:i + 16].unsqueeze(0), -2)
        out_msk.append(1 - s.max(-1).values)
    return torch.cat(out_all, 1).T, torch.cat(out_msk, 1).T  # [n, Pq]


def main():
    CACHE.mkdir(exist_ok=True)
    M = meta()
    by = {m['ten']: m for m in M}
    enc = Encoders()
    torch.cuda.reset_peak_memory_stats()
    # ---- danh sách ảnh cần chấm
    Q, imgs = [], []
    for lab, y in (('sach', 0), ('ban', 1)):
        for f in sorted((TEST_DIR / lab).glob('*.jpg')):
            parts = f.stem.split('_')
            if parts[0] == 'c01':
                b, t = parts[1], float(parts[2])
                m = by[f'test_{b}_{t:.3f}']
                Q.append(dict(bo='test', ten=f.stem, ban=b, t=t, y=y, ref='chat', poly=m['da_giac_chat']))
                base = load(f)
                imgs.append(base)
                Q.append(dict(bo='vuong', ten=f.stem, ban=b, t=t, y=y, ref='vuong', poly=m['da_giac_vuong']))
                imgs.append(load(HERE / 'anh' / 'vuong' / f'test_{b}_{t:.3f}.jpg'))
                if b in BANS:
                    for k, fn in ANH_SANG.items():
                        Q.append(dict(bo=f'as_{k}', ten=f.stem, ban=b, t=t, y=y, ref='chat', poly=m['da_giac_chat']))
                        imgs.append(relight(base,m['hop_chat'], fn))
            else:
                Q.append(dict(bo='test', ten=f.stem, ban=None, t=None, y=y, ref=None, poly=None))
                imgs.append(load(f))
    for m in M:
        if m['loai'] == 'ref':
            Q.append(dict(bo='pool', ten=m['ten'], ban=m['ban'], t=m['t'], y=0, ref='chat', poly=m['da_giac_chat']))
            imgs.append(load(HERE / 'anh' / 'chat' / f"{m['ten']}.jpg"))
    print(len(Q), 'ảnh cần chấm', flush=True)
    # ---- ảnh tham chiếu theo bàn và kiểu cắt
    refs = {}
    for v in ('chat', 'vuong'):
        for b in BANS:
            ms = [m for m in M if m['loai'] == 'ref' and m['ban'] == b and m['t'] not in KHONG_LAM_THAM_CHIEU[b]]
            feats = {k: [] for k in ('g', 'pe_last', 'pe_mid', 'dino')}
            for i in range(0, len(ms), 16):
                o = enc([load(HERE / 'anh' / v / f"{m['ten']}.jpg") for m in ms[i:i + 16]])
                for k in feats:
                    feats[k].append(o[k])
            feats = {k: torch.cat(x) for k, x in feats.items()}
            feats['mask'] = {k: torch.tensor(np.stack([grid_mask(m[f'da_giac_{v}'], GRID[k], dilate=1) for m in ms]),
                                             device='cuda') for k in GRID}
            feats['t'] = [m['t'] for m in ms]
            refs[(v, b)] = feats
    print('ảnh tham chiếu:', {f'{v}_{b}': len(r['t']) for (v, b), r in refs.items()}, flush=True)
    # ---- chấm
    P = np.zeros(len(Q), np.float32)
    G = np.zeros((len(Q), 512), np.float32)
    out = {key: dict(qi=[], G=[], **{f'{k}_{a}': [] for k in GRID for a in ('all', 'msk')}, **{f'qm_{k}': [] for k in GRID})
           for key in refs}
    t0 = time.time()
    for i in range(0, len(Q), 16):
        o = enc(imgs[i:i + 16])
        P[i:i + 16] = o['p'].cpu().numpy()
        G[i:i + 16] = o['g'].cpu().numpy()
        for j in range(len(o['p'])):
            q = Q[i + j]
            if q['ban'] not in BANS:
                continue
            r = refs[(q['ref'], q['ban'])]
            d = out[(q['ref'], q['ban'])]
            d['qi'].append(i + j)
            d['G'].append((1 - o['g'][j] @ r['g'].T).cpu().numpy().astype(np.float16))
            for k in GRID:
                a, mk = nn_dist(o[k][j], r[k], r['mask'][k])
                d[f'{k}_all'].append(a.cpu().numpy().astype(np.float16))
                d[f'{k}_msk'].append(mk.cpu().numpy().astype(np.float16))
                d[f'qm_{k}'].append(grid_mask(q['poly'], GRID[k]))
    print(f'chấm xong {time.time() - t0:.0f}s, GPU đỉnh {torch.cuda.max_memory_allocated() / 2**20:.0f} MB', flush=True)
    for (v, b), d in out.items():
        np.savez(CACHE / f'D_{v}_{b}.npz', ref_t=np.array(refs[(v, b)]['t']),
                 **{k: np.stack(x) for k, x in d.items()})
    np.savez(CACHE / 'feat.npz', p=P, g=G)
    (CACHE / 'queries.json').write_text(json.dumps([{k: v for k, v in q.items() if k != 'poly'} for q in Q],
                                                   ensure_ascii=False), encoding='utf-8')
    # ---- kiểm tra lại số cũ
    tq = [k for k, q in enumerate(Q) if q['bo'] == 'test']
    y = np.array([Q[k]['y'] for k in tq])
    pred = P[tq] >= 0.5
    print(f'PE-Core S/16 không train, 91 ảnh: đúng {(pred == y).sum()}/{len(y)}, '
          f'sạch {(~pred & (y == 0)).sum()}/{(y == 0).sum()}, bẩn {(pred & (y == 1)).sum()}/{y.sum()}')
    files = sorted((TEST_DIR / 'sach').glob('*.jpg')) + sorted((TEST_DIR / 'ban').glob('*.jpg'))
    g2 = enc.pe.images(files)
    p2 = (100 * torch.tensor(g2) @ enc.txt.cpu().T).softmax(-1)[:, 1].numpy()
    print('đúng theo đúng code so_clip.py:', int(((p2 >= 0.5) == y).sum()), '| lệch xác suất lớn nhất giữa hai cách:',
          float(np.abs(p2 - P[tq]).max()))


if __name__ == '__main__':
    main()
