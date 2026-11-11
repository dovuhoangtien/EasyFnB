"""Train một model phân loại ảnh nhỏ (YOLO-cls) rồi chép bản tốt nhất vào models/.

    python train_cls.py <thư mục dữ liệu có train/ và val/> <tên model ra> [--epochs 25] [--base yolo26n-cls.pt]

Thư mục dữ liệu: train/<lớp>/*.jpg và val/<lớp>/*.jpg, ảnh đã đưa về hình vuông (to_square.py).
"""
import argparse
import shutil
from pathlib import Path

from ultralytics import YOLO

HERE = Path(__file__).resolve().parent
MODELS = HERE.parent / 'models'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('data', type=Path)
    ap.add_argument('name')
    ap.add_argument('--epochs', type=int, default=25)
    ap.add_argument('--imgsz', type=int, default=224)
    ap.add_argument('--batch', type=int, default=64)
    ap.add_argument('--base', nargs='+', default=['yolo26n-cls.pt', 'yolo11n-cls.pt'])
    ap.add_argument('--runs', type=Path, default=None, help='nơi lưu log train (mặc định: cạnh thư mục dữ liệu)')
    ap.add_argument('--scale', type=float, default=0.1,
                    help='cắt ngẫu nhiên khi train giữ lại từ (1 - scale) diện tích; nhỏ để không cắt mất tay giơ')
    ap.add_argument('--erasing', type=float, default=0.1)
    args = ap.parse_args()

    model = None
    for b in args.base:
        try:
            model = YOLO(str(MODELS / b))
            break
        except Exception as e:
            print('không tải được', b, e)
    runs = args.runs or args.data.parent / 'runs'
    model.train(data=str(args.data), epochs=args.epochs, imgsz=args.imgsz, batch=args.batch, device=0,
                workers=2, project=str(runs), name=args.name, exist_ok=True, patience=8, verbose=False,
                plots=True, seed=0, scale=args.scale, erasing=args.erasing)
    best = runs / args.name / 'weights' / 'best.pt'
    shutil.copy(best, MODELS / f'{args.name}.pt')
    m = YOLO(str(MODELS / f'{args.name}.pt'))
    res = m.val(data=str(args.data), imgsz=args.imgsz, batch=args.batch, device=0, verbose=False, plots=False)
    print(f'{args.name}: val top1 = {res.top1:.3f}')
    cm = res.confusion_matrix.matrix
    names = list(m.names.values())
    print('ma trận nhầm (hàng = máy đoán, cột = đáp án):', names)
    for i, n in enumerate(names):
        print(f'  {n:>10}', [int(v) for v in cm[i][:len(names)]])


if __name__ == '__main__':
    main()
