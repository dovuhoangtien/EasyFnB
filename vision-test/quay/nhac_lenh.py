"""Nhắc lệnh cho người diễn khi quay dữ liệu giơ tay.

Máy tính đặt trước mặt người diễn (ngoài khung camera), hiện lệnh to trên màn hình kèm tiếng bíp:
"Ghế G2, Lan: vuốt tóc". Lệnh bốc ngẫu nhiên, nên thứ tự không đoán trước được. Lịch lệnh lưu lại
thành nhãn nháp: lúc gán nhãn chỉ cần chỉnh lại thời điểm, không phải đoán ai làm cử chỉ gì.

    # phiên có lệnh, 5 phút, 3 ghế (mã=tên:loại ghế; loại: gan, xa, mep)
    python quay/nhac_lenh.py --phien 0611_p01 --ghe G1=Tien:gan G2=Lan:xa G3=Minh:mep

    # phiên ăn uống bình thường 15 phút (không lệnh, dùng để đếm báo nhầm mỗi giờ)
    python quay/nhac_lenh.py --phien 0611_bt01 --ghe G1=Tien:gan G2=Lan:xa --binh-thuong --phut 15

    # chỉ in lịch, không mở cửa sổ (để đọc to hoặc in ra giấy)
    python quay/nhac_lenh.py --phien thu --ghe G1=A:gan G2=B:xa --chi-in

Cách dùng trên màn hình: bật quay video trên camera trước, rồi bấm SPACE. Đếm 3-2-1, màn hình hiện
"VỖ TAY": mọi người vỗ tay MỘT cái trước ngực (mốc để khớp giờ với video). Esc để dừng sớm.
"""
import argparse
import json
import random
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from cu_chi import LA_GOI, LOAI_GHE, MA, NHAC, TI_TRONG, phong_chu  # noqa: E402

HIEN_S = 3.5  # mỗi lệnh hiện bao lâu trên màn hình


def doc_ghe(items):
    ghe = {}
    for s in items:
        try:
            ma, rest = s.split('=', 1)
            ten, loai = rest.rsplit(':', 1)
        except ValueError:
            sys.exit(f'--ghe sai dạng: "{s}". Đúng dạng: G1=Tien:gan')
        if loai not in LOAI_GHE:
            sys.exit(f'loại ghế "{loai}" không hợp lệ, chọn một trong {LOAI_GHE}')
        ghe[ma] = dict(nguoi=ten, loai=loai)
    return ghe


def tao_lich(ghe, thoi_luong, nhip, cach_ghe, ti_le_goi, seed):
    """Bốc lệnh ngẫu nhiên: trung bình mỗi `nhip` giây một lệnh, cùng một ghế cách nhau ít nhất
    `cach_ghe` giây, khoảng `ti_le_goi` số lệnh là gọi phục vụ."""
    rng = random.Random(seed)
    goi = [m for m in MA if LA_GOI[m]]
    am = [m for m in MA if not LA_GOI[m]]
    last = {g: -1e9 for g in ghe}
    last_loai = {g: None for g in ghe}
    lich, t = [], 5.0
    while True:
        t += rng.uniform(0.6, 1.4) * nhip
        free = [g for g in ghe if t - last[g] >= cach_ghe]
        if not free:
            t = min(last.values()) + cach_ghe
            free = [g for g in ghe if t - last[g] >= cach_ghe]
        if t > thoi_luong - 6:
            break
        # ghế chờ lâu hơn thì dễ được gọi hơn, để các ghế đều nhau
        g = rng.choices(free, weights=[min(t - last[x], 60) for x in free])[0]
        nhom = goi if rng.random() < ti_le_goi else am
        while True:
            loai = rng.choices(nhom, weights=[TI_TRONG[m] for m in nhom])[0]
            if loai != last_loai[g] or len(nhom) == 1:
                break
        last[g], last_loai[g] = t, loai
        lich.append(dict(t=round(t, 2), ghe=g, nguoi=ghe[g]['nguoi'], loai=loai))
    return lich


def bip(freq=1200, ms=150):
    def run():
        try:
            import winsound
            winsound.Beep(freq, ms)
        except Exception:
            print('\a', end='', flush=True)
    threading.Thread(target=run, daemon=True).start()


class ManHinh:
    W, H = 1280, 720

    def __init__(self):
        self.f_to, self.f_vua, self.f_nho = phong_chu(64), phong_chu(40), phong_chu(26)

    def ve(self, dong_to=(), dong_nho='', nen=(20, 20, 20)):
        """dong_to: các cặp (dòng tiêu đề, dòng lệnh)."""
        img = Image.new('RGB', (self.W, self.H), nen)
        d = ImageDraw.Draw(img)
        y = 60
        for tieu_de, lenh in dong_to:
            d.text((60, y), tieu_de, font=self.f_vua, fill=(255, 210, 90))
            y += 56
            for line in self._xuong_dong(d, lenh, self.f_to, self.W - 120):
                d.text((60, y), line, font=self.f_to, fill=(255, 255, 255))
                y += 78
            y += 30
        if dong_nho:
            d.text((60, self.H - 60), dong_nho, font=self.f_nho, fill=(170, 170, 170))
        return cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)

    @staticmethod
    def _xuong_dong(d, text, font, width):
        lines, cur = [], ''
        for w in text.split():
            if d.textlength((cur + ' ' + w).strip(), font=font) > width and cur:
                lines.append(cur)
                cur = w
            else:
                cur = (cur + ' ' + w).strip()
        return lines + [cur]


def chay_man_hinh(lich, phien, thoi_luong, binh_thuong, cua_so):
    """Trả về số giây đã chạy tính từ lúc vỗ tay (để biết dừng sớm)."""
    mh = ManHinh()
    ten = 'Nhac lenh Easy FnB'
    cv2.namedWindow(ten, cv2.WINDOW_NORMAL)
    if cua_so:
        cv2.resizeWindow(ten, 960, 540)
    else:
        cv2.setWindowProperty(ten, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    def show(img, wait=30):
        cv2.imshow(ten, img)
        return cv2.waitKey(wait) & 0xFF

    while True:
        k = show(mh.ve([(f'Phiên {phien}', 'Bật quay video trên camera, rồi bấm SPACE')],
                       'Esc: thoát'), 50)
        if k == 32:
            break
        if k == 27:
            cv2.destroyAllWindows()
            return 0.0
    for n in (3, 2, 1):
        bip(800, 120)
        end = time.perf_counter() + 1
        while time.perf_counter() < end:
            show(mh.ve([('Chuẩn bị', str(n))]))
    t0 = time.perf_counter()
    bip(1500, 400)
    next_beep = 0
    da_chay = 0.0
    while True:
        now = time.perf_counter() - t0
        da_chay = now
        if now > thoi_luong:
            break
        while next_beep < len(lich) and lich[next_beep]['t'] <= now:
            bip()
            next_beep += 1
        if now < 2.0:
            dong = [('Mọi người', 'VỖ TAY một cái trước ngực')]
        elif binh_thuong:
            dong = [('Ăn uống, nói chuyện bình thường', 'Không ai gọi phục vụ. Lỡ gọi thì ghi lại giờ.')]
        else:
            dong = [(f"Ghế {c['ghe']}, {c['nguoi']}", NHAC[c['loai']])
                    for c in lich if c['t'] <= now < c['t'] + HIEN_S][:3]
        con = int(thoi_luong - now)
        k = show(mh.ve(dong, f'{int(now) // 60:02d}:{int(now) % 60:02d}   còn {con // 60}:{con % 60:02d}'
                                f'   Esc: dừng'))
        if k == 27:
            break
    bip(600, 500)
    while True:
        k = show(mh.ve([('Xong', 'Dừng quay video. Bấm phím bất kỳ để đóng.')]), 50)
        if k != 255:
            break
    cv2.destroyAllWindows()
    return round(da_chay, 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--phien', required=True, help='tên phiên, ví dụ 0611_p01 (ngày tháng + số phiên)')
    ap.add_argument('--ghe', nargs='+', required=True, help='mã=tên:loại, ví dụ G1=Tien:gan G2=Lan:xa')
    ap.add_argument('--phut', type=float, default=5, help='độ dài phiên (phút)')
    ap.add_argument('--nhip', type=float, default=5, help='trung bình bao nhiêu giây một lệnh (cả phòng)')
    ap.add_argument('--cach-ghe', type=float, default=9, help='cùng một ghế cách nhau ít nhất bao nhiêu giây')
    ap.add_argument('--ti-le-goi', type=float, default=0.35, help='tỉ lệ lệnh gọi phục vụ')
    ap.add_argument('--binh-thuong', action='store_true', help='phiên ăn uống bình thường, không có lệnh')
    ap.add_argument('--seed', type=int, default=None)
    ap.add_argument('--chi-in', action='store_true', help='chỉ tạo và in lịch, không mở màn hình')
    ap.add_argument('--cua-so', action='store_true', help='mở cửa sổ nhỏ thay vì toàn màn hình')
    ap.add_argument('--du-lieu', type=Path, default=HERE.parent / 'du_lieu_quay')
    args = ap.parse_args()

    ghe = doc_ghe(args.ghe)
    thoi_luong = args.phut * 60
    seed = args.seed if args.seed is not None else random.randrange(10 ** 6)
    lich = [] if args.binh_thuong else tao_lich(ghe, thoi_luong, args.nhip, args.cach_ghe, args.ti_le_goi, seed)
    folder = args.du_lieu / args.phien
    if (folder / 'lich.json').exists() and not args.chi_in:
        sys.exit(f'{folder} đã có lich.json. Đặt tên phiên khác để khỏi ghi đè.')
    folder.mkdir(parents=True, exist_ok=True)
    phien = dict(phien=args.phien, loai='binh_thuong' if args.binh_thuong else 'lenh', ghe=ghe,
                 thoi_luong_s=thoi_luong, seed=seed, tao_luc=datetime.now().isoformat(timespec='seconds'),
                 video=f'{args.phien}.mp4')
    (folder / 'lich.json').write_text(json.dumps(lich, ensure_ascii=False, indent=1), encoding='utf-8')
    (folder / 'phien.json').write_text(json.dumps(phien, ensure_ascii=False, indent=1), encoding='utf-8')

    n_goi = sum(LA_GOI[c['loai']] for c in lich)
    print(f'Phiên {args.phien}: {len(lich)} lệnh trong {args.phut:g} phút, {n_goi} lệnh gọi phục vụ, '
          f'{len(lich) - n_goi} cử chỉ dễ nhầm.')
    for g in ghe:
        print(f"  ghế {g} ({ghe[g]['nguoi']}, {ghe[g]['loai']}): {sum(c['ghe'] == g for c in lich)} lệnh")
    if args.chi_in:
        for c in lich:
            print(f"  {int(c['t']) // 60:02d}:{c['t'] % 60:05.2f}  ghế {c['ghe']} ({c['nguoi']}): {NHAC[c['loai']]}")
        return
    da_chay = chay_man_hinh(lich, args.phien, thoi_luong, args.binh_thuong, args.cua_so)
    phien['da_chay_s'] = da_chay
    (folder / 'phien.json').write_text(json.dumps(phien, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'Đã chạy {da_chay:.0f} giây. Chép video vào {folder / phien["video"]}')


if __name__ == '__main__':
    main()
