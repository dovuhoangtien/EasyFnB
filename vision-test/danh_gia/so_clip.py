"""So CLIP đang dùng với các bộ mã hoá ảnh mới hơn, trên đúng 3 việc của Easy FnB, cùng dữ liệu, cùng cách chấm.

1. Bàn sạch / bẩn: không train, so ảnh với câu mô tả, trên 91 ảnh bàn cắt từ clip test 01.
2. Nhân viên / khách: train lớp nhỏ trên 332 ảnh, chấm trên 105 ảnh.
3. Giơ tay: train lớp nhỏ theo đúng công thức train/train_tay_clip.py, chấm trên ảnh video thường
   (26 giơ tay, 1.668 không giơ).
Ngoài ra đo thời gian chạy phần ảnh của model trên GPU và CPU.

    python danh_gia/so_clip.py --data <thư mục data> [--models b32_laion siglip2_b32 ...] [--no-cpu]
"""
import argparse
import json
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from clip_cls import BACKBONES as MODELS  # noqa: E402
from clip_cls import PROMPTS, safe_load_patch  # noqa: E402
from fnb_common import square  # noqa: E402

# Câu mô tả bản 2: viết thêm theo hai lỗi đã biết (bàn bày sẵn ly, lọ gia vị bị coi là bẩn), không chỉnh theo điểm.
PROMPTS_V2 = {
    'sach': PROMPTS['sach'] + ['a photo of a restaurant table set with glasses, cutlery and condiment bottles, no food',
                               'a security camera photo of a clean empty restaurant table'],
    'ban': PROMPTS['ban'] + ['a photo of a table with dirty bowls, plates and leftovers after customers left',
                             'a photo of a cluttered table with used cups, napkins and plates'],
}


def jpgs(d):
    return sorted(Path(d).glob('*.jpg'))


def hand_sets(root, n_scb=2500, n_scb_val=400):
    """Giống train_tay_clip.py: ảnh video thường giữ hết, ảnh lớp học SCB lấy mẫu cố định."""
    rnd = random.Random(0)
    vid = lambda d: [f for f in jpgs(d) if f.name.startswith(('th', 'nh_'))]
    scb = lambda d: [f for f in jpgs(d) if not f.name.startswith(('th', 'nh_'))]
    tr, va = root / 'train', root / 'val'
    vg = sorted({f.name.split('_', 1)[1] if f.name.startswith('th') else f.name: f for f in vid(tr / 'gio_tay')}.values())
    sets = {
        'tr_video_gio': vg, 'tr_video_khong': vid(tr / 'khong'),
        'tr_scb_gio': rnd.sample(scb(tr / 'gio_tay'), n_scb), 'tr_scb_khong': rnd.sample(scb(tr / 'khong'), n_scb),
        'va_video_gio': vid(va / 'gio_tay'), 'va_video_khong': vid(va / 'khong'),
        'va_scb_gio': rnd.sample(scb(va / 'gio_tay'), n_scb_val), 'va_scb_khong': rnd.sample(scb(va / 'khong'), n_scb_val),
    }
    return sets


class Enc:
    def __init__(self, key, dev):
        import open_clip
        safe_load_patch()
        arch, pre = MODELS[key]
        self.key, self.dev = key, dev
        self.model, _, self.prep = open_clip.create_model_and_transforms(arch, pretrained=pre, device=dev)
        self.model.eval()
        self.tok = open_clip.get_tokenizer(arch)
        self.size = tuple(self.prep(Image.new('RGB', (300, 200))).shape[-2:])

    def _load(self, f):
        img = cv2.imread(str(f))
        return self.prep(Image.fromarray(cv2.cvtColor(square(img), cv2.COLOR_BGR2RGB)))

    @torch.no_grad()
    def images(self, files, bs=64):
        out = []
        with ThreadPoolExecutor(8) as ex:
            for i in range(0, len(files), bs):
                x = torch.stack(list(ex.map(self._load, files[i:i + bs]))).to(self.dev)
                with torch.autocast('cuda', dtype=torch.float16, enabled=self.dev == 'cuda'):
                    f = self.model.encode_image(x)
                out.append(torch.nn.functional.normalize(f.float(), dim=-1).cpu())
        return torch.cat(out).numpy() if out else np.zeros((0, 1), np.float32)

    @torch.no_grad()
    def texts(self, prompts):
        t = []
        for k in ('sach', 'ban'):
            with torch.autocast('cuda', dtype=torch.float16, enabled=self.dev == 'cuda'):
                e = self.model.encode_text(self.tok(prompts[k]).to(self.dev))
            t.append(torch.nn.functional.normalize(torch.nn.functional.normalize(e.float(), dim=-1).mean(0), dim=-1))
        return torch.stack(t).cpu().numpy()

    @torch.no_grad()
    def bench(self, dev, bs, n, half=False):
        m = self.model.visual.to(dev)
        m = m.half() if half else m.float()
        x = torch.randn(bs, 3, *self.size, device=dev, dtype=torch.float16 if half else torch.float32)
        for _ in range(3):
            m(x)
        if dev == 'cuda':
            torch.cuda.synchronize()
        t0 = time.perf_counter()
        for _ in range(n):
            m(x)
        if dev == 'cuda':
            torch.cuda.synchronize()
        m.float()
        return (time.perf_counter() - t0) / n * 1000


def auc(y, p):
    from sklearn.metrics import roc_auc_score
    return float(roc_auc_score(y, p))


def evaluate(F, txt1, txt2):
    from sklearn.linear_model import LogisticRegression
    res = {}
    # 1. bàn, không train
    Xt = np.concatenate([F['ban_sach'], F['ban_ban']])
    yt = np.r_[np.zeros(len(F['ban_sach'])), np.ones(len(F['ban_ban']))]
    for name, txt in (('ban', txt1), ('ban_v2', txt2)):
        p = torch.tensor(100 * Xt @ txt.T).softmax(-1)[:, 1].numpy()
        pred = p >= 0.5
        res[name] = dict(dung=int((pred == yt).sum()), tong=len(yt), sach=int((~pred & (yt == 0)).sum()),
                         n_sach=int((yt == 0).sum()), ban=int((pred & (yt == 1)).sum()), n_ban=int(yt.sum()),
                         auc=round(auc(yt, p), 3))
    # 2. nhân viên / khách
    Xs = np.concatenate([F['nv_tr_khach'], F['nv_tr_nhan_vien']])
    ys = np.r_[np.zeros(len(F['nv_tr_khach'])), np.ones(len(F['nv_tr_nhan_vien']))]
    lr = LogisticRegression(C=1.0, class_weight='balanced', max_iter=3000).fit(Xs, ys)
    Xv = np.concatenate([F['nv_va_khach'], F['nv_va_nhan_vien']])
    yv = np.r_[np.zeros(len(F['nv_va_khach'])), np.ones(len(F['nv_va_nhan_vien']))]
    p = lr.predict_proba(Xv)[:, 1]
    pred = p >= 0.5
    res['nhan_vien'] = dict(dung=int((pred == yv).sum()), tong=len(yv), khach=int((~pred & (yv == 0)).sum()),
                            n_khach=int((yv == 0).sum()), nv=int((pred & (yv == 1)).sum()), n_nv=int(yv.sum()),
                            auc=round(auc(yv, p), 3))
    # 3. giơ tay (công thức của train_tay_clip.py: C=0.3, ảnh giơ tay video thường trọng số 10)
    Xa = np.concatenate([F['tr_video_gio'], F['tr_scb_gio'], F['tr_video_khong'], F['tr_scb_khong']])
    ya = np.r_[np.ones(len(F['tr_video_gio']) + len(F['tr_scb_gio'])),
               np.zeros(len(F['tr_video_khong']) + len(F['tr_scb_khong']))]
    w = np.r_[np.full(len(F['tr_video_gio']), 10.0), np.ones(len(Xa) - len(F['tr_video_gio']))]
    lr = LogisticRegression(C=0.3, max_iter=5000).fit(Xa, ya, sample_weight=w)
    pg, pk = lr.predict_proba(F['va_video_gio'])[:, 1], lr.predict_proba(F['va_video_khong'])[:, 1]
    sg, sk = lr.predict_proba(F['va_scb_gio'])[:, 1], lr.predict_proba(F['va_scb_khong'])[:, 1]
    h = dict(n_gio=len(pg), n_khong=len(pk), auc_video=round(auc(np.r_[np.ones(len(pg)), np.zeros(len(pk))],
                                                                   np.r_[pg, pk]), 3))
    for th in (0.3, 0.5):
        h[f'gio@{th}'] = int((pg >= th).sum())
        h[f'nham@{th}'] = int((pk >= th).sum())
        h[f'scb@{th}'] = round(float(((sg >= th).sum() + (sk < th).sum()) / (len(sg) + len(sk))), 3)
    # so công bằng không phụ thuộc ngưỡng: đặt ngưỡng sao cho chỉ 1% / 3% ảnh "không giơ" bị báo, đếm số giơ tay bắt được
    for fp in (0.01, 0.03):
        th = np.quantile(pk, 1 - fp)
        h[f'gio@fp{int(fp * 100)}%'] = int((pg > th).sum())
    res['gio_tay'] = h
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', type=Path, required=True, help='thư mục chứa staff_cls/ và hand_v3/')
    ap.add_argument('--models', nargs='+', default=list(MODELS))
    ap.add_argument('--cache', type=Path, default=None, help='thư mục lưu đặc trưng (để chạy lại nhanh)')
    ap.add_argument('--out', type=Path, default=HERE / 'so_clip.json')
    ap.add_argument('--no-cpu', action='store_true', help='không đo tốc độ CPU')
    args = ap.parse_args()
    dev = 'cuda' if torch.cuda.is_available() else 'cpu'
    sets = {'ban_sach': jpgs(HERE / 'anh_ban_test' / 'sach'), 'ban_ban': jpgs(HERE / 'anh_ban_test' / 'ban')}
    for sp in ('tr', 'va'):
        for c in ('khach', 'nhan_vien'):
            sets[f'nv_{sp}_{c}'] = jpgs(args.data / 'staff_cls' / {'tr': 'train', 'va': 'val'}[sp] / c)
    sets.update(hand_sets(args.data / 'hand_v3'))
    print('số ảnh:', {k: len(v) for k, v in sets.items()}, flush=True)
    all_res = json.loads(args.out.read_text(encoding='utf-8')) if args.out.exists() else {}
    for key in args.models:
        t0 = time.time()
        enc = Enc(key, dev)
        cf = args.cache / f'{key}.npz' if args.cache else None
        if cf and cf.exists():
            F = dict(np.load(cf))
        else:
            F = {k: enc.images(v) for k, v in sets.items()}
            if cf:
                cf.parent.mkdir(parents=True, exist_ok=True)
                np.savez(cf, **F)
        r = evaluate(F, enc.texts(PROMPTS), enc.texts(PROMPTS_V2))
        n_par = sum(p.numel() for p in enc.model.visual.parameters()) / 1e6
        big = n_par > 200
        sp = dict(anh=f'{enc.size[0]}x{enc.size[1]}', tham_so_anh_trieu=round(n_par, 1),
                  gpu_ms_1=round(enc.bench('cuda', 1, 30), 2) if dev == 'cuda' else None,
                  gpu_ms_8=round(enc.bench('cuda', 8, 15), 2) if dev == 'cuda' else None,
                  gpu_fp16_ms_8=round(enc.bench('cuda', 8, 15, half=True), 2) if dev == 'cuda' else None)
        if not args.no_cpu:
            sp['cpu_ms_1'] = round(enc.bench('cpu', 1, 3 if big else 10), 1)
            sp['cpu_ms_8'] = round(enc.bench('cpu', 8, 1 if big else 3) / 8, 1)
        r['toc_do'] = sp
        all_res[key] = r
        args.out.write_text(json.dumps(all_res, ensure_ascii=False, indent=1), encoding='utf-8')
        b, b2, s, g = r['ban'], r['ban_v2'], r['nhan_vien'], r['gio_tay']
        print(f"{key:15s} bàn {b['dung']}/{b['tong']} (v2 {b2['dung']}) auc {b['auc']:.3f}/{b2['auc']:.3f} | "
              f"NV {s['dung']}/{s['tong']} auc {s['auc']:.3f} | giơ tay@0.3 {g['gio@0.3']}/{g['n_gio']} nhầm "
              f"{g['nham@0.3']}/{g['n_khong']}, @fp1% {g['gio@fp1%']} @fp3% {g['gio@fp3%']} auc {g['auc_video']:.3f} | "
              f"{sp} | {time.time() - t0:.0f}s", flush=True)
        del enc
        torch.cuda.empty_cache()


if __name__ == '__main__':
    main()
