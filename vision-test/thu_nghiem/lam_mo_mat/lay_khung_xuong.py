"""T5 bước 1: lấy khung xương yolo26n-pose trên CPU cho ~120 khung mẫu (không dùng GPU).

Không có khung_xuong.npz nào đã lưu (out_b0 chưa chạy), nên chạy lại pose trên CPU.
Kết quả: _cache/<clip>_<khung>.jpg + _cache/khung_xuong.npz
"""
import json
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

HERE = Path(__file__).resolve().parent
VT = HERE.parents[1]
CACHE = HERE / '_cache'
CACHE.mkdir(exist_ok=True)

# clip -> danh sách thời điểm (giây)
MAU = {
    '01_phong_an_goc_cao': list(np.linspace(0.5, 14.5, 14)),
    '06_phuc_vu_ghi_order': list(np.linspace(1, 26, 10)),
    '07_khach_tinh_tien': list(np.linspace(1, 18, 8)),
    '08_quan_cafe_nhieu_nguoi': list(np.linspace(0.5, 12.5, 14)),
    '09_nhom_ban_tron': list(np.linspace(0.5, 11.5, 14)),
    # lúc giơ tay có nhãn: dày hơn
    '10_thay_the_gio_tay_lop_hoc_a': [2, 6, 10, 14] + list(np.arange(16.5, 21.51, 0.25)),
    '12_thay_the_gio_tay_hoi_bai': [0.5, 1.2] + list(np.arange(2.0, 3.31, 0.1)) + [4.5],
}

model = YOLO(str(VT / 'models' / 'yolo26n-pose.pt'))
rows = []
for clip, ts in MAU.items():
    cap = cv2.VideoCapture(str(VT / 'clips' / f'{clip}.mp4'))
    fps = cap.get(cv2.CAP_PROP_FPS)
    for t in ts:
        fi = int(round(t * fps))
        cap.set(cv2.CAP_PROP_POS_FRAMES, fi)
        ok, frame = cap.read()
        if not ok:
            continue
        r = model.predict(frame, classes=[0], conf=0.3, imgsz=960, device='cpu', verbose=False)[0]
        name = f'{clip[:2]}_{fi:04d}'
        cv2.imwrite(str(CACHE / f'{name}.jpg'), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
        rows.append(dict(name=name, clip=clip, t=round(float(fi / fps), 3),
                         boxes=r.boxes.xyxy.numpy().tolist(),
                         kp=r.keypoints.xy.numpy().tolist(), kc=r.keypoints.conf.numpy().tolist()))
        print(name, len(r.boxes), flush=True)
(CACHE / 'khung_xuong.json').write_text(json.dumps(rows), encoding='utf-8')
print('so khung', len(rows), 'so nguoi', sum(len(r['boxes']) for r in rows))
