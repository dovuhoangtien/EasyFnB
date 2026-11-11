"""Lấy kết quả từng ảnh của bộ phân loại bàn hiện tại (PE-Core S/16, không train, 84/91) để so và kết hợp với YOLOE.

Dùng đặc trưng ảnh đã lưu sẵn từ danh_gia/so_clip.py (--cache), chỉ tính lại câu mô tả trên CPU.

    python pe_core_tung_anh.py --cache <thư mục feats chứa pe_core_s16.npz>
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch

from chung import CACHE, VT

sys.path.insert(0, str(VT))
sys.path.insert(0, str(VT / 'danh_gia'))
from clip_cls import PROMPTS  # noqa: E402
from so_clip import Enc  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cache', type=Path, required=True)
    args = ap.parse_args()
    F = dict(np.load(args.cache / 'pe_core_s16.npz'))
    txt = Enc('pe_core_s16', 'cpu').texts(PROMPTS)
    out = {}
    for sub, k in (('sach', 'ban_sach'), ('ban', 'ban_ban')):
        files = sorted((VT / 'danh_gia' / 'anh_ban_test' / sub).glob('*.jpg'))
        assert len(files) == len(F[k])
        p = torch.tensor(100 * F[k] @ txt.T).softmax(-1)[:, 1].numpy()
        for f, v in zip(files, p):
            out[f'{sub}/{f.stem}'] = round(float(v), 4)
    ok = sum((v >= 0.5) == k.startswith('ban/') for k, v in out.items())
    print(f'PE-Core S/16: đúng {ok}/{len(out)}')
    (CACHE / 'pe_core_s16_91.json').write_text(json.dumps(out, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
