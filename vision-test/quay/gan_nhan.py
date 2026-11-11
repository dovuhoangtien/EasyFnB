"""Gán nhãn sự kiện cho video đã quay (giơ tay gọi và các cử chỉ dễ nhầm).

    python quay/gan_nhan.py du_lieu_quay/0611_p01

Thư mục phiên có <phien>.mp4, phien.json và lich.json (do nhac_lenh.py tạo). Nhãn ghi vào nhan.json.

Cách làm, theo thứ tự:
 1. Tua tới lúc mọi người vỗ tay, bấm C. Máy đặt sẵn mọi lệnh trong lịch thành sự kiện nháp.
 2. Bấm ] để nhảy tới sự kiện tiếp theo. Xem người ở ghế đó làm gì:
    - A tại khung tay bắt đầu nhấc, S tại khung tay lên cao nhất (đỉnh), D tại khung tay hạ xong.
    - Lần đầu gặp mỗi ghế: kéo chuột vẽ khung quanh người đó (các sự kiện sau cùng ghế tự dùng lại).
    - Enter để xác nhận. X nếu người đó không làm (bỏ sự kiện).
    Cử chỉ dễ nhầm không cần chính xác từng khung: chỉ cần A và D bao trọn cử chỉ.
    Giơ tay gọi thì S phải đúng khung tay lên đỉnh, vì độ trễ được đo từ đó.
 3. Thấy cử chỉ ngoài lịch (ai đó tự gọi, tự vuốt tóc): N tạo sự kiện mới, K đổi loại, G đổi ghế.

Phím:
  SPACE chạy/dừng    , .  lùi/tiến 1 khung    J L  lùi/tiến 1 giây   Shift+J/L  5 giây
  [ ]  sự kiện trước/sau    P  xem lại sự kiện đang chọn    - +  tốc độ
  C  đánh dấu vỗ tay   A S D  bắt đầu/đỉnh/hạ tay   K  đổi loại   G  đổi ghế
  Enter  xác nhận   X  bỏ   N  sự kiện mới   W  lưu   Q / Esc  lưu và thoát
  Chuột: bấm = chấm vào người, kéo = khung quanh người
"""
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from cu_chi import LA_GOI, MA, phong_chu  # noqa: E402

TOC_DO = [0.25, 0.5, 1.0, 2.0]
MAU = {'nhap': (150, 150, 150), 'ok': (80, 200, 80), 'bo': (60, 60, 160)}


class Video:
    def __init__(self, path):
        self.cap = cv2.VideoCapture(str(path))
        if not self.cap.isOpened():
            sys.exit(f'Không mở được video {path}')
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30
        self.n = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.W = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.H = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.i, self.frame = -1, None

    @property
    def dai_s(self):
        return self.n / self.fps

    def lay(self, i):
        i = int(min(max(i, 0), self.n - 1))
        if i == self.i and self.frame is not None:
            return self.frame
        if i != self.i + 1:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ok, f = self.cap.read()
        if ok:
            self.i, self.frame = i, f
        return self.frame


class GanNhan:
    """Trạng thái và thao tác gán nhãn, tách khỏi cửa sổ để thử được không cần màn hình."""

    def __init__(self, folder, video):
        self.folder = Path(folder)
        self.v = video
        phien = self._doc('phien.json', {})
        self.ghe = phien.get('ghe') or {'?': dict(nguoi='?', loai='gan')}
        self.lich = self._doc('lich.json', [])
        self.nhan = self._doc('nhan.json', None) or dict(
            video=phien.get('video', ''), rong=video.W, cao=video.H, fps=video.fps, vo_tay_s=None, su_kien=[])
        self.i = 0          # khung hiện tại
        self.chon = None    # chỉ số sự kiện đang chọn
        self.chay = False
        self.toc_do = 2
        self.thong_bao = 'Tua tới lúc vỗ tay rồi bấm C' if self.nhan['vo_tay_s'] is None else ''

    def _doc(self, name, default):
        f = self.folder / name
        return json.loads(f.read_text(encoding='utf-8')) if f.exists() else default

    # --- thời gian
    @property
    def t(self):
        return self.i / self.v.fps

    def toi(self, t):
        self.i = int(round(min(max(t, 0), self.v.dai_s - 1 / self.v.fps) * self.v.fps))

    # --- sự kiện
    @property
    def sk(self):
        return self.nhan['su_kien']

    def hien_tai(self):
        return self.sk[self.chon] if self.chon is not None and self.chon < len(self.sk) else None

    def danh_dau_vo_tay(self):
        cu = self.nhan['vo_tay_s']
        self.nhan['vo_tay_s'] = round(self.t, 3)
        if cu is None:
            for k, c in enumerate(self.lich):
                ls = round(self.t + c['t'], 3)
                self.sk.append(dict(id=k + 1, loai=c['loai'], ghe=c['ghe'], nguoi=c['nguoi'], lenh_s=ls,
                                    tu=round(ls + 0.5, 3), dinh=round(ls + 1.3, 3), den=round(ls + 3.0, 3),
                                    box=None, x=None, y=None, trang_thai='nhap'))
            self.thong_bao = f'Đã tạo {len(self.lich)} sự kiện nháp từ lịch. Bấm ] để bắt đầu.'
        else:  # đánh dấu lại: dời các sự kiện còn nháp theo
            d = self.t - cu
            for e in self.sk:
                if e['trang_thai'] == 'nhap' and e.get('lenh_s') is not None:
                    for k in ('lenh_s', 'tu', 'dinh', 'den'):
                        e[k] = round(e[k] + d, 3)
            self.thong_bao = f'Dời các sự kiện nháp {d:+.2f} s'
        self.luu()

    def _sap_xep(self):
        e = self.hien_tai()
        self.sk.sort(key=lambda x: x['tu'])
        if e is not None:
            self.chon = next(k for k, x in enumerate(self.sk) if x is e)

    def nhay(self, buoc):
        if not self.sk:
            return
        if self.chon is None:
            # sự kiện đầu tiên sau thời điểm hiện tại
            self.chon = next((k for k, e in enumerate(self.sk) if e['tu'] >= self.t - 0.5), len(self.sk) - 1)
        else:
            self.chon = min(max(self.chon + buoc, 0), len(self.sk) - 1)
        e = self.sk[self.chon]
        self._goi_y_vi_tri(e)
        self.toi(e['tu'] - 1.0)
        self.chay = False

    def nhay_chua_xong(self):
        """Tới sự kiện nháp kế tiếp (sau khi xác nhận hoặc bỏ)."""
        start = (self.chon or 0) + 1
        k = next((k for k in range(start, len(self.sk)) if self.sk[k]['trang_thai'] == 'nhap'), None)
        if k is None:
            self.thong_bao = 'Hết sự kiện nháp phía sau.'
            return
        self.chon = k - 1
        self.nhay(1)

    def _goi_y_vi_tri(self, e):
        """Ghế cố định trong một phiên: dùng lại khung của sự kiện đã xác nhận gần nhất cùng ghế."""
        if e['box'] is not None or e['x'] is not None:
            return
        cung = [x for x in self.sk if x['ghe'] == e['ghe'] and x['trang_thai'] == 'ok' and
                (x['box'] is not None or x['x'] is not None)]
        if cung:
            g = min(cung, key=lambda x: abs(x['tu'] - e['tu']))
            e['box'], e['x'], e['y'] = g['box'], g['x'], g['y']

    def dat(self, key):
        e = self.hien_tai()
        if e is None:
            self.thong_bao = 'Chưa chọn sự kiện nào (bấm ] hoặc N).'
            return
        e[key] = round(self.t, 3)
        if key == 'tu' and e['dinh'] < e['tu']:
            e['dinh'] = e['tu']
        if e['den'] < e['dinh']:
            e['den'] = e['dinh']
        self._sap_xep()

    def doi_loai(self, buoc):
        e = self.hien_tai()
        if e is not None:
            e['loai'] = MA[(MA.index(e['loai']) + buoc) % len(MA)]

    def doi_ghe(self, buoc):
        e = self.hien_tai()
        if e is not None:
            ds = list(self.ghe)
            e['ghe'] = ds[(ds.index(e['ghe']) + buoc) % len(ds)] if e['ghe'] in ds else ds[0]
            e['nguoi'] = self.ghe[e['ghe']]['nguoi']

    def vi_tri(self, x1, y1, x2=None, y2=None):
        """Toạ độ theo pixel của video gốc. Một điểm (bấm) hoặc một khung (kéo)."""
        e = self.hien_tai()
        if e is None:
            self.thong_bao = 'Chọn sự kiện trước khi chấm vị trí.'
            return
        if x2 is None or abs(x2 - x1) < 8 or abs(y2 - y1) < 8:
            e['box'], e['x'], e['y'] = None, int(x1), int(y1)
        else:
            b = [int(min(x1, x2)), int(min(y1, y2)), int(max(x1, x2)), int(max(y1, y2))]
            e['box'], e['x'], e['y'] = b, (b[0] + b[2]) // 2, (b[1] + b[3]) // 2

    def xac_nhan(self, trang_thai='ok'):
        e = self.hien_tai()
        if e is None:
            return
        if trang_thai == 'ok' and e['x'] is None:
            self.thong_bao = 'Chưa có vị trí người: bấm hoặc kéo khung quanh người đó.'
            return
        e['trang_thai'] = trang_thai
        self.thong_bao = ''
        self.luu()
        self.nhay_chua_xong()

    def moi(self):
        g = next(iter(self.ghe))
        e = dict(id=max([x['id'] for x in self.sk], default=0) + 1, loai=MA[0], ghe=g,
                 nguoi=self.ghe[g]['nguoi'], lenh_s=None, tu=round(self.t, 3), dinh=round(self.t + 0.8, 3),
                 den=round(self.t + 2.5, 3), box=None, x=None, y=None, trang_thai='nhap')
        self.sk.append(e)
        self.chon = len(self.sk) - 1
        self._sap_xep()
        self.thong_bao = 'Sự kiện mới: K đổi loại, G đổi ghế, A S D chỉnh giờ, chấm vị trí, Enter.'

    def luu(self):
        f = self.folder / 'nhan.json'
        f.write_text(json.dumps(self.nhan, ensure_ascii=False, indent=1), encoding='utf-8')

    def dem(self):
        n = {'nhap': 0, 'ok': 0, 'bo': 0}
        for e in self.sk:
            n[e['trang_thai']] += 1
        return n

    # --- vẽ
    def ve(self, frame, s, f_to, f_nho, keo=None):
        """s: hệ số thu nhỏ khi hiển thị. keo: khung đang kéo (toạ độ màn hình)."""
        H, W = frame.shape[:2]
        img = cv2.resize(frame, (int(W * s), int(H * s)))
        for k, e in enumerate(self.sk):
            if e['x'] is None or not (e['tu'] - 0.5 <= self.t <= e['den'] + 0.5):
                continue
            chon = k == self.chon
            col = (60, 60, 230) if LA_GOI[e['loai']] else (40, 200, 230)
            if e['trang_thai'] == 'bo':
                col = (120, 120, 120)
            if e['box']:
                x1, y1, x2, y2 = (int(v * s) for v in e['box'])
                cv2.rectangle(img, (x1, y1), (x2, y2), col, 3 if chon else 1)
            cv2.circle(img, (int(e['x'] * s), int(e['y'] * s)), 7 if chon else 4, col, -1)
        if keo:
            cv2.rectangle(img, keo[:2], keo[2:], (255, 255, 255), 1)
        bar_h = 120
        canvas = np.zeros((img.shape[0] + bar_h, img.shape[1], 3), np.uint8)
        canvas[:img.shape[0]] = img
        # dòng thời gian: mỗi sự kiện một vạch, màu theo trạng thái
        y0 = img.shape[0] + 8
        L = img.shape[1] - 20
        for k, e in enumerate(self.sk):
            x = 10 + int(L * e['tu'] / self.v.dai_s)
            cv2.line(canvas, (x, y0), (x, y0 + (16 if k == self.chon else 10)), MAU[e['trang_thai']], 2)
        x = 10 + int(L * self.t / self.v.dai_s)
        cv2.line(canvas, (x, y0 - 4), (x, y0 + 18), (255, 255, 255), 1)
        pil = Image.fromarray(cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB))
        d = ImageDraw.Draw(pil)
        n = self.dem()
        d.text((10, 6), f"{self.t:7.2f} s   {'CHẠY' if self.chay else 'DỪNG'}   x{TOC_DO[self.toc_do]}   "
                        f"vỗ tay: {self.nhan['vo_tay_s']}   xong {n['ok']}, bỏ {n['bo']}, còn nháp {n['nhap']}",
               font=f_nho, fill=(255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))
        e = self.hien_tai()
        if e:
            g = self.ghe.get(e['ghe'], {})
            loai = f"{e['loai']} ({'GỌI' if LA_GOI[e['loai']] else 'dễ nhầm'})"
            d.text((10, y0 + 22), f"#{self.chon + 1}/{len(self.sk)}  ghế {e['ghe']} ({g.get('nguoi', '?')}, "
                                  f"{g.get('loai', '?')})   {loai}   [{e['trang_thai']}]", font=f_to,
                   fill=(255, 255, 255))
            moc = (f"lệnh {e['lenh_s']}   " if e['lenh_s'] is not None else '') + \
                  f"A bắt đầu {e['tu']:.2f}   S đỉnh {e['dinh']:.2f}   D hạ {e['den']:.2f}   " \
                  f"vị trí {'có' if e['x'] is not None else 'CHƯA'}"
            d.text((10, y0 + 52), moc, font=f_nho, fill=(220, 220, 220))
        d.text((10, y0 + 80), self.thong_bao or 'Enter xác nhận   X bỏ   ] tiếp   N mới   W lưu   Q thoát',
               font=f_nho, fill=(255, 210, 90))
        return cv2.cvtColor(np.asarray(pil), cv2.COLOR_RGB2BGR)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('phien', type=Path, help='thư mục phiên, ví dụ du_lieu_quay/0611_p01')
    ap.add_argument('--rong', type=int, default=1280, help='bề rộng cửa sổ hiển thị')
    args = ap.parse_args()
    phien = json.loads((args.phien / 'phien.json').read_text(encoding='utf-8')) \
        if (args.phien / 'phien.json').exists() else {}
    vp = args.phien / phien.get('video', '')
    if not vp.is_file():
        vids = sorted(args.phien.glob('*.mp4')) + sorted(args.phien.glob('*.MP4')) + sorted(args.phien.glob('*.mov'))
        if not vids:
            sys.exit(f'Không thấy video trong {args.phien}')
        vp = vids[0]
    v = Video(vp)
    g = GanNhan(args.phien, v)
    g.nhan['video'] = vp.name
    s = min(1.0, args.rong / v.W)
    f_to, f_nho = phong_chu(22), phong_chu(17)
    ten = 'Gan nhan Easy FnB'
    cv2.namedWindow(ten, cv2.WINDOW_AUTOSIZE)
    keo = {'dang': None, 'hien': None}

    def chuot(ev, x, y, flags, _):
        if ev == cv2.EVENT_LBUTTONDOWN:
            keo['dang'] = (x, y)
        elif ev == cv2.EVENT_MOUSEMOVE and keo['dang']:
            keo['hien'] = (*keo['dang'], x, y)
        elif ev == cv2.EVENT_LBUTTONUP and keo['dang']:
            x0, y0 = keo['dang']
            if y < v.H * s and y0 < v.H * s:
                g.vi_tri(x0 / s, y0 / s, x / s, y / s)
            keo['dang'] = keo['hien'] = None

    cv2.setMouseCallback(ten, chuot)
    xem_den = None  # đang xem lại một sự kiện: tự dừng ở mốc này
    while True:
        frame = v.lay(g.i)
        cv2.imshow(ten, g.ve(frame, s, f_to, f_nho, keo['hien']))
        wait = max(1, int(1000 / (v.fps * TOC_DO[g.toc_do]))) if g.chay else 30
        k = cv2.waitKeyEx(wait)
        if g.chay:
            g.i = min(g.i + 1, v.n - 1)
            if xem_den is not None and g.t >= xem_den:
                g.chay, xem_den = False, None
        if k == -1:
            continue
        c = chr(k) if 0 <= k < 256 else ''
        if not c:  # phím mũi tên, phím chức năng: bỏ qua
            continue
        if k == 27 or c in 'qQ':
            g.luu()
            break
        if c == ' ':
            g.chay = not g.chay
        elif c == ',':
            g.chay, g.i = False, max(g.i - 1, 0)
        elif c == '.':
            g.chay, g.i = False, min(g.i + 1, v.n - 1)
        elif c in 'jlJL':
            g.toi(g.t + {'j': -1, 'l': 1, 'J': -5, 'L': 5}[c])
        elif c == '[':
            g.nhay(-1)
        elif c == ']':
            g.nhay(1)
        elif c in 'pP' and g.hien_tai():
            e = g.hien_tai()
            g.toi(e['tu'] - 1.0)
            g.chay, xem_den = True, e['den'] + 1.0
        elif c == '-':
            g.toc_do = max(0, g.toc_do - 1)
        elif c in '+=':
            g.toc_do = min(len(TOC_DO) - 1, g.toc_do + 1)
        elif c in 'cC':
            g.danh_dau_vo_tay()
        elif c in 'aA':
            g.dat('tu')
        elif c in 'sS':
            g.dat('dinh')
        elif c in 'dD':
            g.dat('den')
        elif c == 'k':
            g.doi_loai(1)
        elif c == 'K':
            g.doi_loai(-1)
        elif c == 'g':
            g.doi_ghe(1)
        elif c == 'G':
            g.doi_ghe(-1)
        elif k == 13:
            g.xac_nhan('ok')
        elif c in 'xX':
            g.xac_nhan('bo')
        elif c in 'nN':
            g.moi()
        elif c in 'wW':
            g.luu()
            g.thong_bao = 'Đã lưu.'
    cv2.destroyAllWindows()
    n = g.dem()
    print(f"Đã lưu {args.phien / 'nhan.json'}: xong {n['ok']}, bỏ {n['bo']}, còn nháp {n['nhap']}")


if __name__ == '__main__':
    main()
