"""Đo tốc độ và bộ nhớ GPU của YOLOE-26 trên RTX 3050 4 GB, và thử xuất sang ONNX / TensorRT với câu nhắc cố định.

    python do_toc_do.py do        # PyTorch FP16, n và s, 640 và 1280, có và không câu nhắc, kèm yolo26s COCO
    python do_toc_do.py xuat      # set_classes rồi export ONNX + TensorRT FP16 (736x1280 và 384x640), đo, so kết quả

Mỗi số ms tính cả chuẩn bị ảnh và xử lý kết quả (gọi model.predict), trung bình 40 khung clip 01 sau 5 khung khởi động.
VRAM: đỉnh bộ nhớ PyTorch giữ (max_memory_reserved), chưa tính ~300 MB ngữ cảnh CUDA của tiến trình.
"""
import json
import sys
import time

import numpy as np
import torch

from chung import CACHE, COCO_ITEMS, PROMPTS, WEIGHTS, Frames, load_coco, load_yoloe, run

N_WARM, N = 5, 40
CAP_GB = 1.5  # GPU dùng chung: chặn PyTorch ở 1,5 GB, vượt thì ghi là không chạy được
if torch.cuda.is_available():
    torch.cuda.set_per_process_memory_fraction(CAP_GB * 2 ** 30 / torch.cuda.get_device_properties(0).total_memory)


def frames():
    fr = Frames()
    return [fr.get('01_phong_an_goc_cao', t) for t in np.linspace(0.2, 14.5, N_WARM + N)]


def bench(model, ims, imgsz, classes=None, half=True):
    torch.cuda.synchronize()
    ts = []
    for i, im in enumerate(ims):
        t0 = time.perf_counter()
        run(model, im, imgsz, 0.25, classes=classes, half=half)
        torch.cuda.synchronize()
        if i >= N_WARM:
            ts.append((time.perf_counter() - t0) * 1000)
    return round(float(np.mean(ts)), 1), round(float(np.percentile(ts, 90)), 1)


def do():
    ims = frames()
    out = {}
    for key, name in (('e26n', 'yoloe-26n-seg.pt'), ('e26s', 'yoloe-26s-seg.pt'), ('pf26n', 'yoloe-26n-seg-pf.pt'),
                      ('pf26s', 'yoloe-26s-seg-pf.pt'), ('coco26s', None)):
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()
        t0 = time.perf_counter()
        m = load_coco() if name is None else load_yoloe(name)
        t_load = time.perf_counter() - t0
        for sz in (640, 1280):
            torch.cuda.empty_cache()
            torch.cuda.reset_peak_memory_stats()
            try:
                ms, p90 = bench(m, ims, sz, classes=list(COCO_ITEMS) if name is None else None)
            except torch.OutOfMemoryError:
                out[f'{key}@{sz}'] = dict(loi=f'vượt {CAP_GB} GB')
                print(f'{key}@{sz}: vượt {CAP_GB} GB VRAM', flush=True)
                continue
            vram = torch.cuda.max_memory_reserved() / 2 ** 20
            out[f'{key}@{sz}'] = dict(ms=ms, p90=p90, vram_mb=round(vram), nap_s=round(t_load, 1))
            print(f'{key}@{sz}: {ms} ms (p90 {p90}), VRAM PyTorch đỉnh {vram:.0f} MB, nạp + mã hoá chữ {t_load:.1f} s',
                  flush=True)
        del m
    f = CACHE / 'toc_do.json'
    old = json.loads(f.read_text(encoding='utf-8')) if f.exists() else {}
    old.update(out)
    f.write_text(json.dumps(old, ensure_ascii=False, indent=1), encoding='utf-8')


def xuat():
    ims = frames()
    out = {}
    ref = load_yoloe('yoloe-26s-seg.pt')
    for shape in ([736, 1280], [384, 640]):
        tag = f'{shape[0]}x{shape[1]}'
        for fmt in ('onnx', 'engine'):
            key = f'e26s_{fmt}_{tag}'
            try:
                m = load_yoloe('yoloe-26s-seg.pt')  # set_classes(PROMPTS) rồi mới export: câu nhắc được "nướng" vào model
                t0 = time.perf_counter()
                kw = dict(format=fmt, imgsz=shape, half=fmt == 'engine', device=0)
                if fmt == 'engine':
                    kw['workspace'] = 1
                path = m.export(**kw)
                t_exp = time.perf_counter() - t0
                from ultralytics import YOLO
                e = YOLO(path, task='segment')
                torch.cuda.reset_peak_memory_stats()
                ms, p90 = bench(e, ims, shape, half=fmt == 'engine')
                # có cho cùng kết quả với PyTorch không? so trên 10 khung
                same = []
                for im in ims[N_WARM:N_WARM + 10]:
                    a = run(ref, im, max(shape), 0.25)
                    b = run(e, im, shape, 0.25, half=fmt == 'engine')
                    same.append((len(a), len(b), sorted(x[0] for x in a) == sorted(x[0] for x in b)))
                out[key] = dict(ok=True, file=str(path), xuat_s=round(t_exp), ms=ms, p90=p90,
                                ten_lop=list(e.names.values())[:5] + ['...'],
                                so_do_pt_vs_xuat=[s[:2] for s in same], cung_lop=sum(s[2] for s in same))
                print(key, out[key], flush=True)
                del e, m
            except Exception as ex:  # noqa: BLE001
                out[key] = dict(ok=False, loi=f'{type(ex).__name__}: {ex}'[:500])
                print(key, 'LỖI', out[key]['loi'], flush=True)
            torch.cuda.empty_cache()
    f = CACHE / 'toc_do.json'
    old = json.loads(f.read_text(encoding='utf-8')) if f.exists() else {}
    old.update(out)
    f.write_text(json.dumps(old, ensure_ascii=False, indent=1), encoding='utf-8')


if __name__ == '__main__':
    {'do': do, 'xuat': xuat}[sys.argv[1]]()
