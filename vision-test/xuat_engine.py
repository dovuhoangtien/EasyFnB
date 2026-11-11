"""Xuất lại ba engine TensorRT bản demo dùng, cho đúng phiên bản TensorRT đang cài.

Engine TensorRT chỉ chạy với đúng phiên bản TensorRT đã xuất ra nó. Cài lại venv (hoặc chép dự án
sang máy khác) thì chạy file này một lần, khoảng 5-10 phút:

    python xuat_engine.py            # bỏ qua engine đã chạy được
    python xuat_engine.py --lai      # xuất lại tất cả

Engine cũ không mở được thì đổi tên thành .engine.cu, không xoá.
"""
import argparse
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
M = HERE / 'models'
YOLOE_DIR = HERE / 'thu_nghiem' / 'yoloe_do_tren_ban'

# (file engine, cách xuất)
JOBS = [
    ('yolo26n-pose_544x960_fp16.engine', 'yolo26n-pose.pt', [544, 960]),
    ('yolo26s_736x1280_fp16.engine', 'yolo26s.pt', [736, 1280]),
    ('yoloe-26s-seg_21lop_736x1280_fp16.engine', 'yoloe', [736, 1280]),
]


def mo_duoc(path, task):
    from ultralytics import YOLO
    try:
        import numpy as np
        YOLO(str(path), task=task).predict(np.zeros((720, 1280, 3), np.uint8), verbose=False)
        return True
    except Exception as e:  # noqa: BLE001
        print(f'  {path.name}: không mở được ({type(e).__name__})')
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--lai', action='store_true', help='xuất lại cả engine đang chạy được')
    args = ap.parse_args()
    import tensorrt
    print('TensorRT', tensorrt.__version__)
    for out, src, sz in JOBS:
        f = M / out
        task = 'segment' if src == 'yoloe' else ('pose' if 'pose' in out else 'detect')
        if f.exists() and not args.lai and mo_duoc(f, task):
            print(f'  {out}: đã chạy được, bỏ qua')
            continue
        if f.exists():
            f.rename(f.with_suffix('.engine.cu'))
        if src == 'yoloe':
            sys.path.insert(0, str(YOLOE_DIR))
            from chung import load_yoloe   # câu nhắc 21 loại đồ trên bàn được "nướng" vào model
            m = load_yoloe('yoloe-26s-seg.pt')
        else:
            from ultralytics import YOLO
            m = YOLO(str(M / src))
        cwd = os.getcwd()
        os.chdir(M)
        try:
            p = m.export(format='engine', half=True, imgsz=sz, device=0, workspace=2, verbose=False)
        finally:
            os.chdir(cwd)
        Path(p).replace(f)
        print(f'  {out}: xuất xong, {"mở được" if mo_duoc(f, task) else "VẪN LỖI"}')


if __name__ == '__main__':
    main()
