"""Đo tốc độ model người và model đồ vật theo từng cách chạy (PyTorch, TensorRT, ONNX Runtime, OpenVINO).

Đo trên khung hình thật của một clip (mặc định clip 08, đông người), tính cả phần chuẩn bị ảnh và xử lý kết quả,
giống hệt lúc pipeline chạy.

    python danh_gia/do_toc_do.py xuat              # xuất các model sang TensorRT / ONNX / OpenVINO vào models/
    python danh_gia/do_toc_do.py do --gpu          # đo trên GPU
    python danh_gia/do_toc_do.py do --cpu          # đo trên CPU
"""
import argparse
import json
import math
import sys
import time
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
M = HERE.parent / 'models'
CLIP = HERE.parent / 'clips' / '08_quan_cafe_nhieu_nguoi.mp4'


def rect(w, h, size, stride=32):
    """Cỡ ảnh thật sự đưa vào model khi thu cạnh dài về `size` (giống YOLO khi chạy PyTorch)."""
    s = size / max(w, h)
    return [int(math.ceil(h * s / stride) * stride), int(math.ceil(w * s / stride) * stride)]


def frames(n=80):
    cap = cv2.VideoCapture(str(CLIP))
    out = []
    while len(out) < n:
        ok, f = cap.read()
        if not ok:
            break
        out.append(f)
    return out


# (tên model .pt, cỡ ảnh cạnh dài)
JOBS = [('yolo26n-pose', 960), ('yolo26s-pose', 960), ('yolo26s', 1280), ('yolo26s', 960)]


def export(args):
    from ultralytics import YOLO
    fr = frames(1)[0]
    h, w = fr.shape[:2]
    for name, size in JOBS:
        sz = rect(w, h, size)
        tag = f'{name}_{sz[0]}x{sz[1]}'
        m = YOLO(str(M / f'{name}.pt'))
        if args.gpu and not (M / f'{tag}_fp16.engine').exists():
            p = m.export(format='engine', half=True, imgsz=sz, device=0, workspace=2, verbose=False)
            Path(p).rename(M / f'{tag}_fp16.engine')
        if args.cpu and not (M / f'{tag}.onnx').exists():
            p = YOLO(str(M / f'{name}.pt')).export(format='onnx', imgsz=sz, simplify=True, verbose=False)
            Path(p).rename(M / f'{tag}.onnx')
        if args.cpu and not (M / f'{tag}_openvino_model').exists():
            p = YOLO(str(M / f'{name}.pt')).export(format='openvino', imgsz=sz, verbose=False)
            Path(p).rename(M / f'{tag}_openvino_model')
        print('đã xuất', tag, flush=True)


def bench(model, fr, sz, device, task, half=False, n_warm=8):
    kw = dict(imgsz=sz, device=device, verbose=False, conf=0.3 if task == 'pose' else 0.25, half=half)
    if task == 'pose':
        kw['classes'] = [0]
    for f in fr[:n_warm]:
        model.predict(f, **kw)
    ts, n_obj = [], []
    for f in fr[n_warm:]:
        t0 = time.perf_counter()
        r = model.predict(f, **kw)[0]
        ts.append((time.perf_counter() - t0) * 1000)
        n_obj.append(len(r.boxes))
    return round(float(np.median(ts)), 1), round(float(np.mean(n_obj)), 1)


def measure(args):
    from ultralytics import YOLO
    fr = frames(args.n)
    h, w = fr[0].shape[:2]
    out_f = HERE / 'toc_do.json'
    res = json.loads(out_f.read_text(encoding='utf-8')) if out_f.exists() else {}
    for name, size in JOBS:
        sz = rect(w, h, size)
        tag = f'{name}_{sz[0]}x{sz[1]}'
        task = 'pose' if 'pose' in name else 'detect'
        runs = []
        if args.gpu:
            runs += [('GPU PyTorch', M / f'{name}.pt', '0'), ('GPU PyTorch FP16', M / f'{name}.pt', '0h'),
                     ('GPU TensorRT FP16', M / f'{tag}_fp16.engine', '0')]
        if args.cpu:
            runs += [('CPU PyTorch', M / f'{name}.pt', 'cpu'), ('CPU ONNX Runtime', M / f'{tag}.onnx', 'cpu'),
                     ('CPU OpenVINO', M / f'{tag}_openvino_model', 'cpu')]
        for label, path, dev in runs:
            if not path.exists():
                print('  thiếu', path.name)
                continue
            model = YOLO(str(path), task=task)
            half = dev.endswith('h')
            ms, n = bench(model, fr, sz, dev.rstrip('h'), task, half=half)
            key = f'{name} @{size} | {label}'
            res[key] = dict(ms=ms, so_vat_tb=n, anh=f'{sz[0]}x{sz[1]}')
            print(f'{key:45s} {ms:7.1f} ms   (trung bình {n} vật/khung)', flush=True)
            out_f.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('lenh', choices=['xuat', 'do'])
    ap.add_argument('--gpu', action='store_true')
    ap.add_argument('--cpu', action='store_true')
    ap.add_argument('--n', type=int, default=80, help='số khung đo')
    args = ap.parse_args()
    (export if args.lenh == 'xuat' else measure)(args)


if __name__ == '__main__':
    sys.exit(main())
