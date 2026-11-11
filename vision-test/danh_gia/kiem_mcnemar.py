"""Kiểm xem bộ mã hoá mới hơn cũ thật hay do may (kiểm định McNemar trên cùng tập ảnh).

Đếm số ảnh mới đúng mà cũ sai (b) và ngược lại (c). Nếu chênh lệch là do may, b và c sẽ gần bằng nhau.

    python danh_gia/kiem_mcnemar.py --cache <thư mục đặc trưng> --cu b32_laion --moi pe_core_s16 pe_core_b16
"""
import argparse
import sys
from math import comb
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from clip_cls import PROMPTS  # noqa: E402
from so_clip import Enc  # noqa: E402


def mcnemar(ok_old, ok_new):
    b = int((ok_new & ~ok_old).sum())
    c = int((ok_old & ~ok_new).sum())
    n = b + c
    p = min(1.0, 2 * sum(comb(n, k) for k in range(0, min(b, c) + 1)) / 2 ** n) if n else 1.0
    return b, c, p


def table_ok(key, F):
    enc = Enc(key, 'cuda' if torch.cuda.is_available() else 'cpu')
    txt = enc.texts(PROMPTS)
    X = np.concatenate([F['ban_sach'], F['ban_ban']])
    y = np.r_[np.zeros(len(F['ban_sach'])), np.ones(len(F['ban_ban']))]
    p = torch.tensor(100 * X @ txt.T).softmax(-1)[:, 1].numpy()
    del enc
    torch.cuda.empty_cache()
    return (p >= 0.5) == y


def hand_scores(F):
    from sklearn.linear_model import LogisticRegression
    Xa = np.concatenate([F['tr_video_gio'], F['tr_scb_gio'], F['tr_video_khong'], F['tr_scb_khong']])
    ya = np.r_[np.ones(len(F['tr_video_gio']) + len(F['tr_scb_gio'])),
               np.zeros(len(F['tr_video_khong']) + len(F['tr_scb_khong']))]
    w = np.r_[np.full(len(F['tr_video_gio']), 10.0), np.ones(len(Xa) - len(F['tr_video_gio']))]
    lr = LogisticRegression(C=0.3, max_iter=5000).fit(Xa, ya, sample_weight=w)
    return lr.predict_proba(F['va_video_gio'])[:, 1], lr.predict_proba(F['va_video_khong'])[:, 1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cache', type=Path, required=True)
    ap.add_argument('--cu', default='b32_laion')
    ap.add_argument('--moi', nargs='+', required=True)
    args = ap.parse_args()
    Fo = dict(np.load(args.cache / f'{args.cu}.npz'))
    t_old = table_ok(args.cu, Fo)
    g_old, k_old = hand_scores(Fo)
    for key in args.moi:
        F = dict(np.load(args.cache / f'{key}.npz'))
        b, c, p = mcnemar(t_old, table_ok(key, F))
        print(f'{key}: bàn: mới đúng mà cũ sai {b}, cũ đúng mà mới sai {c}, p = {p:.3f}')
        # giơ tay: so ở cùng mức báo nhầm 1% và 3% trên ảnh "không giơ"
        g_new, k_new = hand_scores(F)
        for fp in (0.01, 0.03):
            ok_o = g_old > np.quantile(k_old, 1 - fp)
            ok_n = g_new > np.quantile(k_new, 1 - fp)
            b, c, p = mcnemar(ok_o, ok_n)
            print(f'    giơ tay ở mức báo nhầm {fp:.0%}: mới bắt mà cũ sót {b}, cũ bắt mà mới sót {c}, p = {p:.3f}')
        # và số ảnh "không giơ" bị báo khi giữ nguyên số ca giơ tay bắt được như bản cũ ở ngưỡng 0.3
        n_hit = int((g_old >= 0.3).sum())
        th_new = np.sort(g_new)[::-1][n_hit - 1]
        print(f'    bắt {n_hit}/{len(g_old)} ca giơ tay như bản cũ: cũ báo nhầm {(k_old >= 0.3).sum()}, '
              f'mới báo nhầm {(k_new >= th_new).sum()} / {len(k_old)} ảnh')


if __name__ == '__main__':
    main()
