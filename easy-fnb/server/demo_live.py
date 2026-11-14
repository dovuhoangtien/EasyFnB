"""Camera demo: phát lần lượt các clip thật (đã che mặt) trong du_lieu_demo/video_demo như một camera đang chạy,
và tới đúng giây trong clip thì báo sự kiện vào Hub y như máy camera AI báo (khách mới, giơ tay gọi, nhân viên
tới, cần dọn, nhìn quanh, tạm rời). Nhờ vậy màn hình trực tiếp, điện thoại nhân viên, dòng thời gian và trợ lý
đều chạy thật mà không cần máy camera (Cloud Run không có GPU).

Bật: tự bật trên Cloud Run, hoặc đặt DEMO_LIVE=1. Tắt: DEMO_LIVE=0. Chỉ phát khi có người đang mở web, và nhường
ngay khi có camera thật gửi hình vào cùng mã camera. Thiếu opencv thì im lặng không chạy.
"""
import asyncio
import os
import time
from pathlib import Path

from .hub import CLOSED, now_ms

CAM = 'cam1'
NGUON = 'Camera quán (phát lại clip thật)'
FPS = 8
RONG = 640
BAN_NEN = {'B1': ('co_khach', 3), 'B2': ('co_khach', 1), 'B3': ('co_khach', 2), 'B4': ('trong', 0),
           'B5': ('co_khach', 2), 'B6': ('trong', 0), 'B7': ('co_khach', 2), 'B8': ('co_khach', 2)}
_XA = [[200, 130], [450, 130], [450, 300], [200, 300]]          # bàn tròn phía xa (khung 1024x576)
_GAN = [[0, 380], [560, 290], [1024, 380], [1024, 576], [0, 576]]   # bàn ngay trước camera

# Mỗi bước: (giây trong clip, việc, tham số...). Việc: ban (trạng thái, số người) | sk (loại sự kiện của máy
# camera) | nhan (nhân viên bấm nhận) | toi (camera thấy nhân viên tới bàn) | bo_lo | tam_roi
KICH_BAN = [
    dict(file='x02_khach_moi.mp4', ban='B6', w=960, h=540, poly=[[265, 140], [470, 140], [470, 275], [265, 275]],
         dau=('trong', 0), buoc=[(14, 'ban', 'co_khach', 2), (15, 'sk', 'khach_moi', 'hoa'), (19, 'nhan', 'hoa'),
                                 (26, 'toi')]),
    dict(file='x03_goi_nhanh.mp4', ban='B6', w=960, h=540, poly=[[265, 140], [470, 140], [470, 275], [265, 275]],
         dau=('co_khach', 1), buoc=[(6.5, 'sk', 'goi_phuc_vu', 'hoa'), (9, 'nhan', 'hoa'), (13, 'toi')]),
    dict(file='x04_goi_toi.mp4', ban='B2', w=1024, h=576, poly=_GAN,
         dau=('co_khach', 1), buoc=[(14.5, 'sk', 'goi_phuc_vu', 'lan'), (17, 'nhan', 'lan'), (21, 'toi')]),
    dict(file='x06_nhin_quanh.mp4', ban='B5', w=1024, h=576, poly=_XA,
         dau=('co_khach', 2), buoc=[(4, 'sk', 'nhin_quanh')]),
    dict(file='x05_khach_moi_goi.mp4', ban='B4', w=1024, h=576, poly=_GAN,
         dau=('co_khach', 1), buoc=[(6, 'ban', 'co_khach', 2), (7, 'sk', 'khach_moi', 'ngoc'), (12.5, 'sk', 'goi_phuc_vu', 'ngoc'),
                                    (15, 'nhan', 'ngoc'), (27, 'toi')]),
    dict(file='x07_can_don.mp4', ban='B7', w=1024, h=576, poly=_XA,
         dau=('co_khach', 2), buoc=[(7, 'sk', 'khach_roi'), (7.5, 'ban', 'can_don', 0), (8, 'sk', 'can_don', 'minh'),
                                    (11, 'nhan', 'minh')]),
    dict(file='x08_tam_roi.mp4', ban='B8', w=1024, h=576, poly=_XA,
         dau=('co_khach', 2), buoc=[(9, 'tam_roi')]),
    dict(file='x01_goi_khong_toi.mp4', ban='B3', w=960, h=540, poly=[[60, 250], [340, 250], [340, 410], [60, 410]],
         dau=('co_khach', 2), buoc=[(25, 'sk', 'goi_phuc_vu', 'minh'), (28, 'nhan', 'minh'), (43.5, 'bo_lo')]),
]


def bat():
    v = os.environ.get('DEMO_LIVE', '').strip()
    return v == '1' or (v != '0' and bool(os.environ.get('K_SERVICE')))


class DemoLive:
    def __init__(self, hub, clips, thu_muc):
        self.hub, self.clips, self.dir = hub, clips, Path(thu_muc)
        self.viec = {}          # bàn -> mã việc gần nhất do camera demo tạo
        self.don = None         # bàn đang chờ dọn: sang clip sau thì camera "thấy bàn sạch"

    # ------------------------------------------------------------ báo vào Hub như máy camera
    def _ban(self, ban, state, people):
        z = self.hub.zones.pop(CAM, None)     # bàn ngoài khung clip đang phát vẫn có trạng thái trên sơ đồ
        try:
            self.hub.edge_tables(CAM, [dict(id=ban, state=state, people=people)])
        finally:
            if z is not None:
                self.hub.zones[CAM] = z

    def _viec_mo(self, ban):
        a = self.hub.alerts.get(self.viec.get(ban))
        return a if a and a['status'] not in CLOSED else None

    def _lam(self, ban, b):
        hub, viec = self.hub, b[1]
        if viec == 'ban':
            self._ban(ban, b[2], b[3])
        elif viec == 'sk':
            ca, nv = hub.staff, [x for x in hub.staff if len(b) > 3 and x['id'] == b[3]]
            hub.staff = nv or ca           # việc giao đúng người trong clip (người sẽ bấm nhận ở bước sau)
            try:
                aid = hub.edge_event(dict(kind=b[2], camera=CAM, table=ban, score=0.93))
            finally:
                hub.staff = ca
            if aid:
                self.viec[ban] = aid
            if b[2] == 'can_don':
                self.don = ban
        elif viec == 'nhan' and self._viec_mo(ban):
            if any(s['id'] == b[2] for s in hub.staff):
                hub.ack(self.viec[ban], b[2])
        elif viec == 'toi':
            hub.edge_event(dict(kind='nv_den', camera=CAM, table=ban))
        elif viec == 'bo_lo' and self._viec_mo(ban):
            hub._close(self._viec_mo(ban), 'done', 'camera', 'không thấy nhân viên tới, khách đã thôi gọi')
        elif viec == 'tam_roi':
            hub.timeline.add('table', table=ban, camera=CAM, state='occupied', prev='occupied', people=0, away=True)
            hub.add_log('system', f'Bàn {ban}: khách tạm rời, còn để đồ ở bàn nên chưa báo dọn', ban, CAM)

    def _vao_clip(self, k, dai_s):
        hub = self.hub
        if self.don and self.don != k['ban']:      # bàn vừa báo dọn ở clip trước: đã dọn xong
            hub.edge_event(dict(kind='da_don', camera=CAM, table=self.don))
            self._ban(self.don, 'trong', 0)
            self.don = None
        xa = k['w'] * 3        # các bàn khác nằm ngoài khung clip này: vẫn có trên sơ đồ, không vẽ lên hình
        ngoai = [dict(id=b, polygon=[[xa, 0], [xa + 9, 0], [xa + 9, 9]]) for b in BAN_NEN if b != k['ban']]
        z = dict(camera=CAM, frame_w=k['w'], frame_h=k['h'], areas=[],
                 tables=sorted([dict(id=k['ban'], polygon=k['poly'])] + ngoai, key=lambda x: x['id']))
        hub.zones[CAM] = z                 # chỉ trong bộ nhớ: không ghi đè vùng bàn đã lưu của quán
        hub.publish('zones', hub.get_zones(CAM))
        self._ban(k['ban'], *k['dau'])
        t = now_ms()                       # để trợ lý tìm ra đúng clip này khi được hỏi về lúc vừa rồi
        self.clips.demo.append(dict(file=k['file'], camera=CAM, t_from=t, t_to=t + int(dai_s * 1000)))
        del self.clips.demo[:-400]

    # ------------------------------------------------------------ vòng phát
    def _co_nguoi_xem(self):
        c = self.hub.cameras.get(CAM)
        that = c and c.get('online') and c.get('source') not in (None, NGUON)
        return bool(self.hub.subs) and not that

    async def chay(self):
        try:
            import cv2
        except ImportError:
            print('camera demo không chạy: thiếu opencv-python-headless', flush=True)
            return
        self.hub.demo_live = True          # trợ lý đọc cả ngày từ lịch sử (gồm việc camera demo vừa tạo)
        for k in ('wait_greet_s', 'wait_food_s', 'wait_bill_s'):
            self.hub.settings[k] = 0       # bàn nền không có ai phục vụ thật: tắt lời nhắc "ngồi lâu chưa ai tiếp"
        for ban, (st, n) in BAN_NEN.items():
            self._ban(ban, st, n)
        while True:
            for k in KICH_BAN:
                while not self._co_nguoi_xem():
                    await asyncio.sleep(1)
                try:
                    await self._phat(cv2, k)
                except Exception as e:  # noqa: BLE001  một clip hỏng không được làm dừng máy chủ
                    print(f'camera demo lỗi ở {k["file"]}: {type(e).__name__}: {e}', flush=True)
                    await asyncio.sleep(2)

    async def _phat(self, cv2, k):
        f = self.dir / k['file']
        cap = await asyncio.to_thread(cv2.VideoCapture, str(f))
        if not cap.isOpened():
            raise FileNotFoundError(f)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        tong = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
        nhay = max(1, round(fps / FPS))
        cao = round(RONG * k['h'] / k['w'])
        self._vao_clip(k, tong / fps if tong else 30)
        buoc = sorted(k['buoc'], key=lambda b: b[0])

        def doc():
            for _ in range(nhay - 1):
                cap.grab()
            ok, img = cap.read()
            if not ok:
                return None
            img = cv2.resize(img, (RONG, cao), interpolation=cv2.INTER_AREA)
            ok, jpg = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 68])
            return jpg.tobytes() if ok else None

        t0, i = time.monotonic(), 0
        try:
            while True:
                jpg = await asyncio.to_thread(doc)
                if jpg is None:
                    break
                i += 1
                ts = i * nhay / fps
                self.hub.edge_frame(CAM, 'live', jpg, fps / nhay, NGUON, RONG, cao)
                while buoc and buoc[0][0] <= ts:
                    try:
                        self._lam(k['ban'], buoc.pop(0))
                    except Exception as e:  # noqa: BLE001
                        print(f'camera demo: bước lỗi {type(e).__name__}: {e}', flush=True)
                cho = t0 + ts - time.monotonic()
                if cho > 0:
                    await asyncio.sleep(cho)
        finally:
            cap.release()
        for b in buoc:      # clip ngắn hơn kịch bản: vẫn làm nốt các bước còn lại
            self._lam(k['ban'], b)
