"""Gán người vào bàn (khớp bàn). Xem docs/superpowers/specs/2026-11-13-khop-ban-design.md.

Bước 1, hình học (không gọi AI):
- Điểm neo vẫn ở 60% khung người (neo theo hông đã thử, kém hơn: xem diem_neo).
- Khoảng cách tới bàn tính theo cỡ người, kể cả người bị che chỉ còn đầu vai (co_nguoi). Người không đứng được
  nới xa hơn trước (ghế ở ngoài vùng bàn vẽ sát mặt bàn), người đứng thì chặt (đứng cạnh bàn không phải khách).
- Hai bàn gần như bằng nhau thì đánh dấu "không chắc".
- Đã ngồi ở một bàn đủ lâu thì giữ bàn đó tới khi đứng dậy đi, không đổi vì tay với sang bàn bên.

Bước 2, Gemini Decision (HoiBan): người đang ngồi mà "không chắc" quá 2 s thì hỏi máy chủ một lần, máy chủ hỏi
Gemini Decision. Một bàn từ 0,7 trở lên và mọi bàn khác từ 0,3 trở xuống thì chốt người đó vào bàn này tới khi
đứng dậy đi. Mất mạng, lỗi, lưng chừng: giữ kết quả hình học.
"""
import base64
import queue
import threading
import time

import cv2
import numpy as np

R_DUNG = 0.45           # người đứng: như luật cũ (nhân viên đứng cạnh bàn vẫn tính là tới bàn); không đếm là khách
R_NGOI = 0.6            # người không đứng (ngồi, hoặc không rõ vì chân bị bàn che); luật cũ 0,45 lần chiều cao
R_CHOT = 1.2            # bàn đã chốt (Decision hoặc ngồi lâu): còn trong tầm này thì giữ
SAT_NUT = 0.15          # hai bàn chênh dưới bấy nhiêu lần cỡ người: "không chắc"
DOI_BAN_S = 0.4         # đổi bàn (chưa ngồi lâu): bàn mới phải thắng liên tục bấy nhiêu giây (giây video)
GIU_NGOI_S = 5.0        # ngồi ở một bàn bấy nhiêu giây ngoài đời thì giữ bàn đó tới khi đứng dậy đi
HOI_SAU_S = 2.0         # không chắc liên tục bấy nhiêu giây ngoài đời thì hỏi Decision
HOI_LAI_S = 60.0        # cùng một người không hỏi lại trong bấy nhiêu giây ngoài đời
P_CO, P_KHONG = 0.7, 0.3


def diem_neo(kp, kc, box):
    """Điểm đại diện chỗ người đó ngồi/đứng: giữa khung, cách đỉnh 60% chiều cao. Trả (x, y).
    Đã thử neo theo hông (khung xương) trên 67 khách có nhãn (nhan_ban_nguoi.json): đúng 48-62, kém neo này (58-66),
    vì người ngồi sau bàn hay bị che hông và khung xương đoán hông lệch. Nên giữ neo theo khung."""
    x1, y1, x2, y2 = [float(v) for v in box[:4]]
    return (x1 + x2) / 2, y1 + 0.6 * (y2 - y1)


def co_nguoi(box):
    """Cỡ người (pixel). Người bị mép khung hoặc bàn che chỉ còn đầu vai: khung thấp mà rộng, lấy theo bề ngang."""
    x1, y1, x2, y2 = box[:4]
    return max(float(y2 - y1), 1.2 * float(x2 - x1), 1.0)


class GanBan:
    """Bàn của từng người, có nhớ. tables: danh sách đối tượng có .name và .poly (đa giác float32)."""

    def __init__(self, tables, toc=1.0):
        self.tables = list(tables)
        self.toc = toc
        self.st = {}      # pid -> dict(ban, cho, t_cho, t_ngoi, chot, t_kc, t_hoi, ung)

    def _diem(self, pt, scale):
        return {tb: cv2.pointPolygonTest(tb.poly, pt, True) / scale for tb in self.tables}

    def gan(self, pid, box, kp, kc, t, dung=False, di=False):
        """Trả (bàn hoặc None, danh sách bàn ứng viên khi không chắc hoặc None)."""
        if not self.tables:
            return None, None
        x, y = diem_neo(kp, kc, box)
        # người đứng: cỡ theo chiều cao như luật cũ (khung rộng vì dang tay, bưng khay không được nới thêm)
        d = self._diem((x, y), max(float(box[3] - box[1]), 1.0) if dung else co_nguoi(box))
        r = R_DUNG if dung else R_NGOI
        ung = sorted((tb for tb in self.tables if d[tb] > -r), key=lambda tb: -d[tb])
        moi = ung[0] if ung else None
        if pid not in self.st:                   # người mới thấy: nhận bàn ngay, không chờ
            self.st[pid] = dict(ban=moi, cho=None, t_cho=t, t_ngoi=None, chot=None, t_kc=None, t_hoi=-1e9, ung=None)
        s = self.st[pid]
        s['t_thay'] = t
        ngoi = not dung and not di
        if di:                                   # đứng dậy đi: bỏ mọi thứ đã chốt
            s['chot'], s['t_ngoi'] = None, None
        # bàn đã chốt (Decision) hoặc đã ngồi lâu: giữ khi còn ở gần
        if s['chot'] is not None and d.get(s['chot'], -9) > -R_CHOT:
            s['ban'], s['t_kc'], s['ung'] = s['chot'], None, None
            return s['ban'], None
        if (ngoi and s['ban'] is not None and s['t_ngoi'] is not None
                and t - s['t_ngoi'] >= GIU_NGOI_S / self.toc and d.get(s['ban'], -9) > -R_CHOT):
            ban = s['ban']
        else:
            ban = self._doi(s, moi, t)
        if ngoi and ban is not None:
            s['t_ngoi'] = t if s['t_ngoi'] is None or s.get('ban_ngoi') is not ban else s['t_ngoi']
            s['ban_ngoi'] = ban
        else:
            s['t_ngoi'] = None
        s['ban'] = ban
        # không chắc: bàn thứ hai sát nút
        khong_chac = len(ung) >= 2 and d[ung[0]] - d[ung[1]] < SAT_NUT
        if khong_chac and ngoi:
            s['t_kc'] = t if s['t_kc'] is None else s['t_kc']
            s['ung'] = [tb for tb in ung[:3] if d[ung[0]] - d[tb] < SAT_NUT]
        else:
            s['t_kc'], s['ung'] = None, None
        return ban, s['ung']

    def _doi(self, s, moi, t):
        """Như ban_on_dinh cũ: bàn mới (kể cả từ "không bàn" sang một bàn) phải thắng liên tục DOI_BAN_S giây mới đổi."""
        if moi is s['ban']:
            s['cho'] = None
            return moi
        if s['cho'] is None or s['cho'][0] is not moi:     # cho = (bàn chờ đổi sang,) để phân biệt "chờ sang None"
            s['cho'], s['t_cho'] = (moi,), t
        if t - s['t_cho'] >= DOI_BAN_S:
            s['cho'] = None
            return moi
        return s['ban']

    def can_hoi(self, t):
        """Những người cần hỏi Decision ngay bây giờ: [(pid, [bàn ứng viên])]. Gọi xong thì đánh dấu đã hỏi."""
        ra = []
        for pid, s in self.st.items():
            if (s['ung'] and s['chot'] is None and s['t_kc'] is not None
                    and t - s['t_kc'] >= HOI_SAU_S / self.toc and t - s['t_hoi'] >= HOI_LAI_S / self.toc):
                ra.append((pid, list(s['ung'])))
        return ra

    def da_hoi(self, pid, t):
        if pid in self.st:
            self.st[pid]['t_hoi'] = t

    def chot(self, pid, ten_ban):
        """Decision đã trả lời chắc: người pid ngồi ở bàn tên ten_ban."""
        s = self.st.get(pid)
        tb = next((b for b in self.tables if b.name == ten_ban), None)
        if s is not None and tb is not None:
            s['chot'], s['ban'], s['ung'], s['t_kc'] = tb, tb, None, None

    def quen(self, t, giu_s=10.0):
        """Bỏ người không thấy quá giu_s giây (video)."""
        for pid in [p for p, s in self.st.items() if t - s.get('t_thay', t) > giu_s]:
            del self.st[pid]


# ---------------------------------------------------------------- bước 2: hỏi Gemini Decision qua máy chủ
MAU = [(0, 200, 255), (255, 120, 0), (0, 220, 0)]      # BGR: cam, xanh dương, xanh lá (đỏ dành cho khung người)
TEN_MAU = ['cam', 'xanh dương', 'xanh lá']


def anh_hoi(frame, box, polys):
    """Ảnh gửi Decision: cắt quanh người và các bàn ứng viên, khung đỏ quanh người, mỗi bàn một màu viền.
    frame nên là ảnh đã che mặt. Trả JPEG bytes."""
    vis = frame.copy()
    for k, p in enumerate(polys):
        cv2.polylines(vis, [np.asarray(p, np.int32)], True, MAU[k], 2)
    x1, y1, x2, y2 = [int(v) for v in box[:4]]
    cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 0, 255), 2)
    pts = np.vstack([np.asarray(p, np.float32) for p in polys] + [np.array([[x1, y1], [x2, y2]], np.float32)])
    ax1, ay1 = pts.min(0)
    ax2, ay2 = pts.max(0)
    pw, ph = 0.25 * (ax2 - ax1), 0.25 * (ay2 - ay1)
    H, W = vis.shape[:2]
    c = vis[int(max(0, ay1 - ph)):int(min(H, ay2 + ph)), int(max(0, ax1 - pw)):int(min(W, ax2 + pw))]
    if c.shape[0] < 400:
        c = cv2.resize(c, None, fx=400 / c.shape[0], fy=400 / c.shape[0])
    if max(c.shape[:2]) > 1024:
        f = 1024 / max(c.shape[:2])
        c = cv2.resize(c, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
    return cv2.imencode('.jpg', c, [cv2.IMWRITE_JPEG_QUALITY, 85])[1].tobytes()


def chon_ban(probs):
    """probs: tên bàn -> xác suất "ngồi ở bàn này". Một bàn chắc và các bàn khác chắc là không: trả tên bàn."""
    if not probs:
        return None
    best = max(probs, key=probs.get)
    if probs[best] >= P_CO and all(p <= P_KHONG for b, p in probs.items() if b != best):
        return best
    return None


class HoiBan:
    """Gửi câu hỏi bàn lên máy chủ (POST /api/edge/table-ask) ở một luồng riêng, không làm chậm camera.
    Mỗi camera tối đa một câu mỗi `gian_s` giây (giờ thật). Lỗi thì bỏ qua: camera giữ kết quả hình học."""

    def __init__(self, url, camera, key=None, gian_s=10.0, session=None, dong_ho=time.monotonic):
        import requests
        self.url, self.camera, self.gian_s, self.dong_ho = url.rstrip('/'), camera, gian_s, dong_ho
        self.s = session or requests.Session()
        if key:
            self.s.headers['X-Edge-Key'] = key
        self.vao, self.ra = queue.Queue(maxsize=2), queue.Queue()
        self.t_gui = -1e9
        self.so_lan = 0
        self.dung = threading.Event()
        self.th = threading.Thread(target=self._chay, daemon=True)
        self.th.start()

    def gui(self, pid, jpeg, cands):
        """cands: tên bàn theo thứ tự màu (cam, xanh dương, xanh lá). Trả True nếu đã nhận để gửi."""
        now = self.dong_ho()
        if now - self.t_gui < self.gian_s:
            return False
        try:
            self.vao.put_nowait((pid, jpeg, list(cands)))
        except queue.Full:
            return False
        self.t_gui = now
        self.so_lan += 1
        return True

    def ket_qua(self):
        """[(pid, tên bàn chốt hoặc None, probs)] đã có trả lời."""
        out = []
        while True:
            try:
                out.append(self.ra.get_nowait())
            except queue.Empty:
                return out

    def _chay(self):
        while not self.dung.is_set():
            try:
                pid, jpeg, cands = self.vao.get(timeout=0.5)
            except queue.Empty:
                continue
            try:
                r = self.s.post(f'{self.url}/api/edge/table-ask', timeout=6, json=dict(
                    camera=self.camera, jpeg_b64=base64.b64encode(jpeg).decode(),
                    tables=[dict(table=b, color=TEN_MAU[k]) for k, b in enumerate(cands)]))
                d = r.json() if r.status_code == 200 else {}
            except Exception as e:   # mất mạng: giữ kết quả hình học
                print(f'  hỏi bàn lỗi: {e.__class__.__name__}', flush=True)
                d = {}
            probs = d.get('probs') or {}
            self.ra.put((pid, chon_ban(probs) if d.get('ok') else None, probs))

    def close(self):
        self.dung.set()
