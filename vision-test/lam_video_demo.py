"""Ghép video demo ngắn từ kết quả pipeline, mỗi đoạn có dòng chú thích.

    python lam_video_demo.py out_v3 demo_v3.mp4
"""
import argparse
import shutil
import subprocess
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

from easyfnb_test import load_font

# (clip, từ giây, đến giây, chú thích)
DOAN = [
    ('01_phong_an_goc_cao', 0, 15, 'Trạng thái bàn: xanh lá = trống, xanh dương = có khách, cam = cần dọn. '
                                   'Model ảnh xem bàn sạch hay bẩn, nên lọ gia vị, ly bày sẵn không còn bị tính là "cần dọn"'),
    ('06_phuc_vu_ghi_order', 0, 8, 'Khung tím "NV" = nhân viên: không đếm là khách của bàn, '
                                    'nhân viên giơ tay đưa đồ không bị báo là khách gọi'),
    ('04_phuc_vu_toi_khach_moi', 2, 8, 'Nhận nhân viên phục vụ đi tới bàn khách mới'),
    ('10_thay_the_gio_tay_lop_hoc_a', 15.5, 21.5, 'Giơ tay gọi (cảnh thay thế, chưa có clip quán): '
                                                   'khung đỏ "GỌI" = báo nhân viên'),
    ('12_thay_the_gio_tay_hoi_bai', 0.5, 4.6, 'Giơ tay nhanh ngang đầu'),
    ('09_nhom_ban_tron', 0, 6, 'Khách cầm ly, nói chuyện, chỉ tay: không báo nhầm'),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out', type=Path)
    ap.add_argument('dst', type=Path)
    args = ap.parse_args()
    W, H = 1280, 720
    font = load_font(26)
    raw = args.dst.with_suffix('.raw.mp4')
    vw = cv2.VideoWriter(str(raw), cv2.VideoWriter_fourcc(*'mp4v'), 25, (W, H))
    for clip, a, b, text in DOAN:
        cap = cv2.VideoCapture(str(args.out / clip / 'video_ket_qua.mp4'))
        fps = cap.get(cv2.CAP_PROP_FPS) or 25
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(a * fps))
        # chú thích dài thì xuống dòng
        words, lines, cur = text.split(), [], ''
        probe = ImageDraw.Draw(Image.new('RGB', (10, 10)))
        for w in words:
            if probe.textlength(cur + ' ' + w, font=font) > W - 40:
                lines.append(cur)
                cur = w
            else:
                cur = (cur + ' ' + w).strip()
        lines.append(cur)
        n = int((b - a) * fps)
        step = fps / 25
        k = 0.0
        frames = []
        for _ in range(n):
            ok, f = cap.read()
            if not ok:
                break
            frames.append(f)
        cap.release()
        while k < len(frames):
            f = cv2.resize(frames[int(k)], (W, H))
            img = Image.fromarray(cv2.cvtColor(f, cv2.COLOR_BGR2RGB))
            dr = ImageDraw.Draw(img, 'RGBA')
            h = 14 + 34 * len(lines)
            dr.rectangle((0, H - h - 8, W, H), fill=(0, 0, 0, 180))
            for j, ln in enumerate(lines):
                dr.text((20, H - h + j * 34), ln, font=font, fill=(255, 255, 255))
            vw.write(cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR))
            k += step
    vw.release()
    if shutil.which('ffmpeg'):
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', str(raw), '-c:v', 'libx264', '-preset', 'veryfast',
                        '-crf', '26', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(args.dst)], check=True)
        raw.unlink()
    else:
        raw.rename(args.dst)
    print('xong', args.dst)


if __name__ == '__main__':
    main()
