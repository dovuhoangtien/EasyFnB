"""Ghi hình camera liên tục, cắt clip theo giờ đồng hồ, gửi clip của từng sự kiện lên máy chủ.

Cách làm:
  - Pipeline đưa khung hình vào một ô "khung mới nhất" (không hàng đợi dài, không bao giờ chờ). Một luồng riêng
    thu nhỏ (tối đa 960 px ngang) rồi đẩy cho ffmpeg qua stdin, đúng `fps` khung mỗi giây đồng hồ
    (nguồn chậm hơn thì lặp khung cũ, nhanh hơn thì bỏ bớt). Nhờ vậy giây thứ n của video luôn là giây thứ n
    ngoài đời, và "cho tôi 12:30:05 đến 12:30:20" quy ra được đúng đoạn.
  - Ghi BẢN GỐC, không che mặt (chỉ ở máy quán). Cạnh mỗi đoạn có tệp vị trí mặt r<..>_<k>.mat.jsonl: mỗi dòng
    {"t": giờ ms của khung, "m": [[cx, cy, a, b], ...] elip đầu từng người (từ khung xương pose, như blur_faces),
    "b": [[x1, y1, x2, y2], ...] khung người không tính được elip}; "m": null là khung không có dữ liệu người.
    Khi cắt clip để gửi đi mà đang che mặt: giải mã, che theo tệp này, nén lại. Khung không tìm được dòng nào
    thì che cả khung hình: không bao giờ gửi khung chưa che. Việc clip có `goc: true` (chủ quán xem bản gốc,
    có PIN) thì chép luồng như cũ, không che.
  - ffmpeg nén H.264 (libx264 veryfast, yuv420p), cắt thành các đoạn MP4 10 giây, mỗi giây một khung khoá.
    Đoạn là MP4 phân mảnh: đang ghi dở vẫn đọc được tới giây gần nhất, ffmpeg chết giữa chừng không hỏng tệp.
  - Tên tệp chính là chỉ mục: r<giờ bắt đầu lượt ghi, ms>_<số thứ tự>.mp4, đoạn thứ k bắt đầu ở giờ đó + k*10 s.
    index.json bên cạnh ghi thêm lúc kết thúc của từng lượt ghi (một lượt = một lần chạy ffmpeg).
  - Dọn theo CẢ tuổi (mặc định 24 giờ) lẫn tổng dung lượng (mặc định 5 GB), xoá đoạn cũ nhất trước.
  - cut(t_from, t_to): ghép các đoạn phủ khoảng đó (chép luồng, không nén lại), tối đa 60 giây.
    cut(..., che=True): như trên nhưng che mặt (nén lại libx264 veryfast).
  - Sự kiện tạo việc (gọi phục vụ, cần dọn, khách mới): 8 giây sau cắt [t-6 s, t+8 s] và gửi
    POST /api/edge/clip theo `eid`. Sự kiện an ninh (lấy đồ, ngoài giờ, khu cấm): [t-10 s, t+20 s].
    Web xin clip bất kỳ qua việc `clip` của GET /api/edge/jobs.

Không có ffmpeg, ffmpeg chết hai lần liền, hay ổ đĩa đầy: in một dòng rồi tự tắt, pipeline chạy tiếp.
"""
import json
import os
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path

import bisect

import cv2
import numpy as np

from fnb_common import head_ellipse

HERE = Path(__file__).resolve().parent
FFMPEG_DU_PHONG = r'C:\ffmpeg\bin\ffmpeg.exe'
SEG_S = 10               # độ dài một đoạn (giây)
MAX_CLIP_S = 60.0        # clip dài nhất cho một lần cắt
TRUOC_S, SAU_S = 6.0, 8.0  # clip sự kiện: từ t-6 s tới t+8 s
TRE_S = 1.5              # đoạn đang ghi chỉ đọc được tới khung khoá gần nhất: chờ thêm chừng này rồi mới cắt
CHO_TOI_DA_S = 6.0       # cut() chờ đoạn cuối tối đa bấy nhiêu
LOAI_AN_NINH = ('lay_do', 'co_nguoi_ngoai_gio', 'vao_khu_cam')
TRUOC_AN_NINH_S, SAU_AN_NINH_S = 10.0, 20.0   # clip sự kiện an ninh: từ t-10 s tới t+20 s
LOAI_CO_CLIP = ('goi_phuc_vu', 'can_don', 'khach_moi', 'nhin_quanh') + LOAI_AN_NINH
TEN_DOAN = re.compile(r'r(\d+)_(\d+)\.mp4')
_AN = dict(creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP) if os.name == 'nt' else {}
# ^ ffmpeg con không nhận Ctrl+C của cửa sổ lệnh: để pipeline tự đóng nó cho tệp cuối được ghi trọn


def tim_ffmpeg():
    return shutil.which('ffmpeg') or (FFMPEG_DU_PHONG if Path(FFMPEG_DU_PHONG).exists() else None)


def ten_an_toan(s):
    return ''.join(ch for ch in str(s) if ch.isalnum() or ch in '_-') or 'cam'


def vi_tri_mat(kps, kcs, boxes, W, H, th=0.3):
    """Dòng vị trí mặt cho một khung (toạ độ đã thu nhỏ): dict(m=[elip đầu], b=[khung người không tính được]).
    boxes None (pipeline không đưa người) -> m None: lúc cắt sẽ che cả khung."""
    if boxes is None:
        return dict(m=None, b=[])
    m, b = [], []
    for k, box in enumerate(boxes):
        try:
            e = head_ellipse(np.asarray(kps[k], np.float32), np.asarray(kcs[k], np.float32), box[:4], th, (W, H))
        except Exception:     # thiếu khung xương: che cả khung người
            b.append([int(v) for v in box[:4]])
            continue
        if e is not None:
            m.append([round(float(v), 1) for v in e[:4]])
    return dict(m=m, b=b)


def _vo(roi, khoi):
    sm = cv2.resize(roi, (max(1, roi.shape[1] // khoi), max(1, roi.shape[0] // khoi)), interpolation=cv2.INTER_AREA)
    return cv2.resize(sm, (roi.shape[1], roi.shape[0]), interpolation=cv2.INTER_NEAREST)


def che_khung(img, dong):
    """Che mặt trên img (sửa tại chỗ) theo một dòng vị trí mặt. dong None hoặc m None: che cả khung hình."""
    H, W = img.shape[:2]
    if dong is None or dong.get('m') is None:
        img[:] = _vo(img, max(8, W // 24))
        return img
    for x1, y1, x2, y2 in dong.get('b') or []:
        x1, y1, x2, y2 = max(0, int(x1)), max(0, int(y1)), min(W, int(x2)), min(H, int(y2))
        if x2 - x1 >= 2 and y2 - y1 >= 2:
            img[y1:y2, x1:x2] = _vo(img[y1:y2, x1:x2], max(4, (x2 - x1) // 6))
    for cx, cy, a, b in dong['m']:
        x0, y0 = max(0, int(cx - a - 1)), max(0, int(cy - b - 1))
        x1, y1 = min(W, int(cx + a + 2)), min(H, int(cy + b + 2))
        if x1 - x0 < 2 or y1 - y0 < 2:
            continue
        m = np.zeros((y1 - y0, x1 - x0), np.uint8)
        cv2.ellipse(m, (int(round(cx - x0)), int(round(cy - y0))), (int(round(a)), int(round(b))), 0, 0, 360, 255, -1)
        roi = img[y0:y1, x0:x1]
        cv2.copyTo(_vo(roi, max(2, int(2 * a / 5))), m, roi)
    return img


class GhiVideo:
    def __init__(self, thu_muc, camera='cam1', fps=10, max_w=960, gio=24.0, gb=5.0, mo_mat=True,
                 ffmpeg='auto', seg_s=SEG_S):
        self.dir = Path(thu_muc)
        self.camera = camera
        self.fps = max(1, min(30, int(round(fps))))
        self.max_w = max_w
        self.gio, self.gb = float(gio), float(gb)
        self.mo_mat = mo_mat         # False (--khong-mo-mat): không bao giờ che khi cắt
        self.che = None              # hàm() -> cài đặt "che mặt" trên máy chủ (noi() gắn vào); None: luôn che
        self.seg_s = int(seg_s)
        self.ffmpeg = tim_ffmpeg() if ffmpeg == 'auto' else ffmpeg
        self.mc = None
        self.on = False              # đang ghi (False: chưa bật được hoặc đã tự tắt)
        self.ly_do_tat = None
        self._gio = time.time        # đồng hồ treo tường (test thay được)
        self._lock = threading.Lock()
        self._slot = None            # khung mới nhất chưa ghi: (frame, kps, kcs, boxes)
        self._last_in = -1e9
        self._proc = None
        self._log = None
        self._img = None             # khung đã thu nhỏ (bản gốc), đang được lặp lại cho ffmpeg
        self._mat = None             # dòng vị trí mặt của self._img
        self._mat_moi = False        # self._img vừa đổi: ghi dòng vị trí mặt mới
        self._mat_f = None           # (số đoạn, tệp .mat.jsonl đang mở)
        self._wh = None
        self._wall0 = self._mono0 = 0.0
        self._run = None             # mã lượt ghi hiện tại = giờ bắt đầu (ms)
        self._n = 0                  # số khung đã đưa cho ffmpeg trong lượt này
        self._hong_luc = -1e9        # lần ffmpeg chết gần nhất
        self._runs = {}              # mã lượt -> dict(fps, seg_s, w, h, end_ms)
        self._viec = []              # việc cắt và gửi đang chờ: dict(luc, eid|job, t_from, t_to)
        self._seq = 0
        self._stop = threading.Event()
        self._ghi = self._lam = None
        if not self.ffmpeg or not Path(self.ffmpeg).exists() and not shutil.which(self.ffmpeg):
            self._tat('không tìm thấy ffmpeg (PATH hoặc C:\\ffmpeg\\bin)')
            return
        try:
            self.dir.mkdir(parents=True, exist_ok=True)
            (self.dir / '_cat').mkdir(exist_ok=True)
            self._nap_index()
            self._don_dep()
        except OSError as e:
            self._tat(f'không dùng được thư mục {self.dir}: {e}')
            return
        if self.ly_do_tat:
            return
        self.on = True
        self._ghi = threading.Thread(target=self._vong_ghi, daemon=True)
        self._ghi.start()
        self._lam = threading.Thread(target=self._vong_viec, daemon=True)
        self._lam.start()
        print(f'  ghi hình: {self.dir} ({self.fps} khung/giây, giữ {self.gio:g} giờ hoặc {self.gb:g} GB)')

    # ------------------------------------------------------------ pipeline gọi (không bao giờ chờ)
    def khung(self, frame, kps=None, kcs=None, boxes=None):
        """Đưa một khung của pipeline. Chỉ giữ tham chiếu khung mới nhất; thu nhỏ và làm mờ mặt làm ở luồng ghi."""
        if not self.on:
            return
        t = time.monotonic()
        if t - self._last_in < 0.9 / self.fps:
            return
        self._last_in = t
        self._slot = (frame, None if kps is None else np.array(kps, np.float32),
                      None if kcs is None else np.array(kcs, np.float32),
                      None if boxes is None else np.array(boxes, np.float32))

    def noi(self, mc):
        """Nối với luồng gửi máy chủ: mỗi sự kiện gửi đi thì hẹn cắt clip cho nó; che mặt theo cài đặt trên máy chủ."""
        self.mc = mc
        mc.on_event = self.su_kien
        if callable(getattr(mc, 'an_ninh', None)):
            self.che = lambda: bool(mc.an_ninh().get('blur_faces', True))

    def can_che(self):
        """Clip gửi đi (không phải bản gốc) có phải che mặt không."""
        if not self.mo_mat:
            return False
        try:
            return True if self.che is None else bool(self.che())
        except Exception:     # không đọc được cài đặt: che
            return True

    def su_kien(self, e, t=None):
        """Sự kiện pipeline vừa phát (dict có loai, eid): hẹn SAU_S giây nữa cắt [t-6, t+8] (an ninh: [t-10, t+20])
        và gửi theo eid. 'khach_moi' chưa có eid thì đặt luôn ở đây, để máy chủ ghép được clip với việc."""
        if e.get('loai') not in LOAI_CO_CLIP or self.mc is None:
            return
        if not self.on and not self._runs:
            return
        if not e.get('eid'):
            if e.get('loai') != 'khach_moi':
                return
            self._seq += 1
            e['eid'] = f'{self.camera}:km{int(self._gio())}-{self._seq}'
        t = self._gio() if t is None else t
        truoc, sau = (TRUOC_AN_NINH_S, SAU_AN_NINH_S) if e.get('loai') in LOAI_AN_NINH else (TRUOC_S, SAU_S)
        with self._lock:
            if len(self._viec) < 50:     # máy chủ mất lâu: không dồn việc vô hạn
                self._viec.append(dict(luc=t + sau + TRE_S, eid=str(e['eid']), t_from=t - truoc, t_to=t + sau))

    def viec(self, job):
        """Việc `clip` từ máy chủ: {id, t_from, t_to} (ms). Cắt và gửi ở luồng riêng."""
        with self._lock:
            self._viec.append(dict(luc=0, job=job))

    # ------------------------------------------------------------ luồng ghi
    def _chuan_bi(self, item):
        """(khung đã thu nhỏ, KHÔNG che; dòng vị trí mặt theo toạ độ đã thu nhỏ)."""
        frame, kps, kcs, boxes = item
        H, W = frame.shape[:2]
        w = max(2, min(self.max_w, W) & ~1)
        h = max(2, int(round(H * w / W)) & ~1)
        img = cv2.resize(frame, (w, h), interpolation=cv2.INTER_AREA) if (w, h) != (W, H) else frame.copy()
        if boxes is None:
            mat = vi_tri_mat(None, None, None, w, h)
        else:
            sx, sy = w / W, h / H
            n = len(boxes)
            mat = vi_tri_mat(None if kps is None else kps * np.float32([sx, sy]),
                             np.zeros((n, 17), np.float32) if kcs is None else kcs,
                             boxes[:, :4] * np.float32([sx, sy, sx, sy]) if n else boxes, w, h)
            if kps is None and n:     # có người mà không có khung xương: che cả khung người
                mat = dict(m=[], b=[[int(v) for v in b] for b in boxes[:, :4] * np.float32([sx, sy, sx, sy])])
        return np.ascontiguousarray(img), mat

    def _ghi_mat(self):
        """Ghi dòng vị trí mặt của khung thứ self._n (sắp đưa cho ffmpeg) vào tệp của đoạn chứa khung đó."""
        k = self._n // (self.fps * self.seg_s)
        if self._mat_f is None or self._mat_f[0] != k:
            self._dong_mat()
            self._mat_f = (k, open(self.dir / f'r{self._run}_{k:05d}.mat.jsonl', 'a', encoding='utf-8'))
        dong = dict(self._mat or dict(m=None, b=[]), t=int(round((self._wall0 + self._n / self.fps) * 1000)))
        self._mat_f[1].write(json.dumps(dong, separators=(',', ':')) + '\n')
        self._mat_f[1].flush()
        self._mat_moi = False

    def _dong_mat(self):
        f, self._mat_f = self._mat_f, None
        if f is not None:
            try:
                f[1].close()
            except OSError:
                pass

    def _mo(self, w, h):
        self._dong_ffmpeg()
        self._wall0, self._mono0 = self._gio(), time.monotonic()
        self._run = int(self._wall0 * 1000)
        self._wall0 = self._run / 1000
        self._n = 0
        self._wh = (w, h)
        self._runs[self._run] = dict(fps=self.fps, seg_s=self.seg_s, w=w, h=h, end_ms=self._run)
        self._mat_moi = True
        self._log = open(self.dir / 'ffmpeg.log', 'wb')
        cmd = [self.ffmpeg, '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{w}x{h}',
               '-r', str(self.fps), '-i', '-', '-an', '-c:v', 'libx264', '-preset', 'veryfast',
               '-tune', 'zerolatency', '-pix_fmt', 'yuv420p', '-crf', '28',
               '-g', str(self.fps), '-keyint_min', str(self.fps), '-sc_threshold', '0',
               '-f', 'segment', '-segment_time', str(self.seg_s), '-segment_time_delta', '0.02',
               '-segment_format', 'mp4',
               '-segment_format_options', 'movflags=+frag_keyframe+empty_moov+default_base_moof:flush_packets=1', '-flush_packets', '1',
               '-reset_timestamps', '1', str(self.dir / f'r{self._run}_%05d.mp4')]
        self._proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=self._log, **_AN)

    def _dong_ffmpeg(self):
        self._dong_mat()
        p, self._proc = self._proc, None
        if p is not None:
            try:
                p.stdin.close()
            except OSError:
                pass
            try:
                p.wait(timeout=8)
            except subprocess.TimeoutExpired:
                p.kill()
            if self._run in self._runs:
                self._runs[self._run]['end_ms'] = int((self._wall0 + self._n / self.fps) * 1000)
            self._luu_index()
        if self._log is not None:
            self._log.close()
            self._log = None

    def _hong(self, vi_sao):
        """ffmpeg chết hoặc không ghi được: mở lại một lần; chết lần nữa trong vòng 30 giây thì tắt hẳn."""
        try:
            loi = (self.dir / 'ffmpeg.log').read_text(encoding='utf-8', errors='replace').strip().splitlines()[-1][:160]
        except (OSError, IndexError):
            loi = ''
        self._dong_ffmpeg()
        if time.monotonic() - self._hong_luc < 30:
            self._tat(f'ffmpeg dừng hai lần liền ({vi_sao}{": " + loi if loi else ""})')
            return
        self._hong_luc = time.monotonic()
        print(f'  [ghi hình] ffmpeg dừng ({vi_sao}{": " + loi if loi else ""}), mở lại')
        self._don_dep()          # ổ đĩa đầy thì dọn bớt trước khi thử lại

    def _tat(self, ly_do):
        self.on = False
        if not self.ly_do_tat:
            self.ly_do_tat = ly_do
            print(f'  [ghi hình] TẮT: {ly_do}. Pipeline vẫn chạy bình thường, chỉ không có video.')

    def _vong_ghi(self):
        don_luc = luu_luc = time.monotonic()
        while not self._stop.is_set() and self.on:
            item, self._slot = self._slot, None
            if item is not None:
                try:
                    img, mat = self._chuan_bi(item)
                except Exception:      # hỏng thì vẫn ghi khung nhưng không có dữ liệu mặt: lúc cắt sẽ che cả khung
                    img, mat = None, None
                    try:
                        img = self._chuan_bi((item[0], None, None, None))[0]
                    except Exception:
                        pass
                if img is not None:
                    wh = (img.shape[1], img.shape[0])
                    if self._proc is not None and wh != self._wh:   # camera nối lại với cỡ ảnh khác: lượt ghi mới
                        self._dong_ffmpeg()
                    self._img = img
                    self._mat = mat
                    self._mat_moi = True
            if self._img is None:
                time.sleep(0.02)
                continue
            try:
                if self._proc is None:
                    self._mo(self._img.shape[1], self._img.shape[0])
                elif self._proc.poll() is not None:
                    self._hong(f'mã thoát {self._proc.returncode}')
                    continue
                troi = time.monotonic() - self._mono0
                if abs((self._gio() - self._wall0) - troi) > 2.0:   # đồng hồ máy vừa bị chỉnh: lượt ghi mới theo giờ mới
                    self._dong_ffmpeg()
                    continue
                can = int(troi * self.fps) + 1 - self._n
                if can > self.fps * 3:      # máy treo hoặc ngủ một lúc: không bù hàng loạt khung, mở lượt ghi mới
                    self._dong_ffmpeg()
                    continue
                if can <= 0:
                    time.sleep(min(0.02, 0.5 / self.fps))
                else:
                    buf = self._img.data
                    moi_doan = self.fps * self.seg_s
                    for _ in range(can):
                        if self._mat_moi or self._n % moi_doan == 0:   # đầu mỗi đoạn ghi lại dòng đang dùng
                            self._ghi_mat()
                        self._proc.stdin.write(buf)
                        self._n += 1
                    self._proc.stdin.flush()
            except OSError as e:           # ống tới ffmpeg vỡ, ổ đĩa đầy, không mở được ffmpeg
                self._hong(e.__class__.__name__)
                continue
            t = time.monotonic()
            if t - luu_luc >= self.seg_s:
                luu_luc = t
                self._runs[self._run]['end_ms'] = int((self._wall0 + self._n / self.fps) * 1000)
                self._luu_index()
            if t - don_luc >= 60:
                don_luc = t
                self._don_dep()
        self._dong_ffmpeg()

    # ------------------------------------------------------------ chỉ mục, dọn dẹp
    def _nap_index(self):
        try:
            runs = json.loads((self.dir / 'index.json').read_text(encoding='utf-8')).get('runs', {})
            self._runs = {int(k): v for k, v in runs.items()}
        except (OSError, ValueError, AttributeError):
            self._runs = {}

    def _luu_index(self):
        try:
            tmp = self.dir / 'index.json.tmp'
            tmp.write_text(json.dumps(dict(camera=self.camera, runs={str(k): v for k, v in self._runs.items()})),
                           encoding='utf-8')
            os.replace(tmp, self.dir / 'index.json')
        except OSError:
            pass

    def doan(self):
        """Các đoạn đang có trên đĩa, cũ trước: dict(start, end, path, run, k, size). Giờ tính bằng giây epoch."""
        out = []
        try:
            entries = list(os.scandir(self.dir))
        except OSError:
            return out
        for e in entries:
            m = TEN_DOAN.fullmatch(e.name)
            if not m:
                continue
            try:
                st = e.stat()
            except OSError:
                continue
            run, k = int(m.group(1)), int(m.group(2))
            seg = (self._runs.get(run) or {}).get('seg_s') or self.seg_s
            start = run / 1000 + k * seg
            out.append(dict(start=start, end=start + seg, path=e.path, run=run, k=k, size=st.st_size, mtime=st.st_mtime))
        out.sort(key=lambda d: (d['run'], d['k']))
        for i, d in enumerate(out):
            if i + 1 < len(out) and out[i + 1]['run'] == d['run']:
                continue
            # đoạn cuối của một lượt ghi thường ngắn hơn seg_s
            if d['run'] == self._run and self._proc is not None:
                het = self._wall0 + self._n / self.fps
            else:
                het = ((self._runs.get(d['run']) or {}).get('end_ms') or 0) / 1000
                if het <= d['start']:      # lượt ghi bị ngắt đột ngột: lấy giờ sửa tệp
                    het = d['mtime']
            d['end'] = max(d['start'], min(d['end'], het))
        return out

    def _don_dep(self):
        """Xoá đoạn quá tuổi hoặc khi tổng vượt dung lượng, cũ nhất trước. Tệp đang bị đọc (Windows khoá) thì để lần sau."""
        now = self._gio()
        ds = self.doan()
        tong = sum(d['size'] for d in ds)
        con = set()
        for d in ds:
            dang_ghi = d['run'] == self._run and self._proc is not None and d['end'] >= self._wall0 + self._n / self.fps - 2 * self.seg_s
            if not dang_ghi and (now - d['end'] > self.gio * 3600 or tong > self.gb * 2**30):
                try:
                    os.unlink(d['path'])
                    tong -= d['size']
                    Path(d['path'][:-4] + '.mat.jsonl').unlink(missing_ok=True)
                    continue
                except OSError:
                    pass
            con.add(d['run'])
        for f in self.dir.glob('r*_*.mat.jsonl'):    # tệp vị trí mặt không còn đoạn video
            m = re.fullmatch(r'r(\d+)_(\d+)\.mat\.jsonl', f.name)
            if m and int(m.group(1)) != self._run and not f.with_name(f.name[:-10] + '.mp4').exists():
                try:
                    f.unlink()
                except OSError:
                    pass
        for r in [r for r in self._runs if r not in con and r != self._run]:
            del self._runs[r]
        for f in (self.dir / '_cat').glob('*'):      # clip cắt tạm còn sót
            try:
                if now - f.stat().st_mtime > 600:
                    f.unlink()
            except OSError:
                pass
        self._luu_index()
        try:
            if shutil.disk_usage(self.dir).free < 200 * 2**20:
                self._tat('ổ đĩa gần đầy (còn dưới 200 MB)')
        except OSError:
            pass

    # ------------------------------------------------------------ cắt
    def cut(self, t_from, t_to, cho=True, che=False):
        """Clip MP4 (H.264, mở được trên trình duyệt) cho khoảng [t_from, t_to] giây epoch. None nếu lúc đó chưa ghi.
        che: che mặt theo tệp vị trí mặt (nén lại); False: bản gốc, chép luồng."""
        r = self.cat(t_from, t_to, cho, che)
        return r[0] if r else None

    def cat(self, t_from, t_to, cho=True, che=False):
        """Như cut() nhưng trả (đường dẫn, giờ bắt đầu thật, giờ kết thúc thật)."""
        if self.ffmpeg is None or not t_to > t_from:
            return None
        t_to = min(t_to, t_from + MAX_CLIP_S)
        if cho and self.on:    # đoạn cuối còn đang ghi: chờ nó ghi tới t_to
            het = time.monotonic() + min(CHO_TOI_DA_S, max(0.0, t_to + TRE_S - self._gio()))
            while time.monotonic() < het and self.on:
                time.sleep(0.1)
        ds = [d for d in self.doan() if d['end'] > t_from and d['start'] < t_to and d['size'] > 0]
        if not ds:
            return None
        # một clip chỉ lấy trong một lượt ghi (giữa hai lượt có khoảng trống): chọn lượt phủ nhiều nhất
        phu = {}
        for d in ds:
            phu[d['run']] = phu.get(d['run'], 0.0) + min(d['end'], t_to) - max(d['start'], t_from)
        run = max(phu, key=phu.get)
        ds = [d for d in ds if d['run'] == run]
        dau = ds[0]['start']
        a, b = max(t_from, dau), min(t_to, ds[-1]['end'])
        if b - a < 0.5:
            return None
        ss = float(int(a - dau))         # lùi về khung khoá (mỗi giây một cái) ngay trước chỗ cần
        dai = b - (dau + ss)
        ten = f'c{int(a * 1000)}_{os.getpid()}_{threading.get_ident() % 100000}_{int(time.monotonic() * 1000) % 100000}'
        lst, out = self.dir / '_cat' / f'{ten}.txt', self.dir / '_cat' / f'{ten}.mp4'
        seg = (self._runs.get(run) or {}).get('seg_s') or self.seg_s
        dong = []
        for i, d in enumerate(ds):
            p = d['path'].replace('\\', '/').replace("'", "'\\''")
            dong.append(f"file '{p}'")
            if i + 1 < len(ds):
                dong.append(f'duration {seg:.3f}')
        try:
            lst.write_text('\n'.join(dong) + '\n', encoding='utf-8')
            if che:
                return self._cat_che(lst, ds, run, dau, a, b, out)
            dau_lenh = [self.ffmpeg, '-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', str(lst),
                        '-ss', f'{ss:.3f}', '-t', f'{dai:.3f}', '-an']
            cuoi = ['-movflags', '+faststart', str(out)]
            for ma in (['-c', 'copy'], ['-c:v', 'libx264', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', '-crf', '28']):
                try:
                    r = subprocess.run(dau_lenh + ma + cuoi, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                       timeout=40, **_AN)
                except subprocess.TimeoutExpired:
                    continue
                if r.returncode == 0 and out.exists() and out.stat().st_size > 1000:
                    return str(out), dau + ss, b
            out.unlink(missing_ok=True)
            return None
        except OSError:
            return None
        finally:
            lst.unlink(missing_ok=True)

    def _doc_mat(self, run, ds):
        """Các dòng vị trí mặt (sắp theo giờ) của những đoạn ds, cộng đoạn ngay trước (dòng đang dùng lúc đầu đoạn)."""
        ks = {d['k'] for d in ds} | {ds[0]['k'] - 1}
        dong = []
        for k in sorted(ks):
            try:
                with open(self.dir / f'r{run}_{k:05d}.mat.jsonl', encoding='utf-8') as f:
                    for line in f:
                        try:
                            x = json.loads(line)
                            dong.append((int(x['t']), x))
                        except (ValueError, KeyError, TypeError):
                            continue      # dòng ghi dở (máy tắt ngang): bỏ, khung đó sẽ che cả khung
            except OSError:
                continue
        dong.sort(key=lambda x: x[0])
        return dong

    def _cat_che(self, lst, ds, run, dau, a, b, out):
        """Giải mã [a, b], che mặt từng khung theo tệp vị trí mặt, nén lại. Lỗi ở bất cứ bước nào: None (không gửi)."""
        info = self._runs.get(run) or {}
        w, h, fps = info.get('w'), info.get('h'), int(info.get('fps') or self.fps)
        if not w or not h:
            return None
        dong = self._doc_mat(run, ds)
        moc = [x[0] for x in dong]
        ss = a - dau
        dec = [self.ffmpeg, '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', str(lst),
               '-ss', f'{ss:.3f}', '-t', f'{b - a:.3f}', '-an', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-']
        enc = [self.ffmpeg, '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{w}x{h}',
               '-r', str(fps), '-i', '-', '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-pix_fmt', 'yuv420p',
               '-crf', '28', '-g', str(fps), '-movflags', '+faststart', str(out)]
        p1 = subprocess.Popen(dec, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, **_AN)
        p2 = subprocess.Popen(enc, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **_AN)
        hong = threading.Timer(60.0, lambda: (p1.kill(), p2.kill()))   # ffmpeg treo: giết, clip này bỏ
        hong.start()
        n, co = 0, w * h * 3
        try:
            while True:
                buf = p1.stdout.read(co)
                if not buf or len(buf) < co:
                    break
                img = np.frombuffer(buf, np.uint8).reshape(h, w, 3).copy()
                t_ms = (a + n / fps) * 1000 + 500 / fps
                i = bisect.bisect_right(moc, t_ms) - 1
                che_khung(img, dong[i][1] if i >= 0 else None)
                p2.stdin.write(img.tobytes())
                n += 1
            p2.stdin.close()
            p2.wait(timeout=40)
            p1.wait(timeout=10)
        except (OSError, ValueError, subprocess.TimeoutExpired):
            p1.kill()
            p2.kill()
            out.unlink(missing_ok=True)
            return None
        finally:
            hong.cancel()
            p1.stdout.close()
        if p2.returncode == 0 and n > 0 and out.exists() and out.stat().st_size > 1000:
            return str(out), a, a + n / fps
        out.unlink(missing_ok=True)
        return None

    # ------------------------------------------------------------ luồng cắt và gửi
    def _vong_viec(self):
        while True:
            dung = self._stop.is_set()
            now = self._gio()
            with self._lock:
                # đang dừng: làm nốt việc còn lại ngay với phần đã ghi được (clip có thể ngắn hơn)
                v = next((x for x in self._viec if dung or x['luc'] <= now), None)
                if v is not None:
                    self._viec.remove(v)
            if v is None:
                if dung:
                    return
                time.sleep(0.2)
                continue
            try:
                self._lam_viec(v)
            except Exception as e:    # việc cắt, gửi hỏng không được làm dừng luồng
                print(f'  [ghi hình] lỗi cắt/gửi clip: {e.__class__.__name__}: {e}')

    def _lam_viec(self, v):
        job = v.get('job')
        if job is not None:
            try:
                t_from, t_to = float(job['t_from']) / 1000, float(job['t_to']) / 1000
            except (KeyError, TypeError, ValueError):
                return self.mc.job_done(job.get('id'), dict(error='việc clip thiếu t_from, t_to'))
            che = not job.get('goc') and self.can_che()   # goc: chủ quán xem bản gốc (máy chủ đã kiểm PIN)
            r = self.cat(t_from, t_to, che=che)
            if r is None:
                return self.mc.job_done(job['id'], dict(error='chưa ghi hình lúc đó' if not che or not self._co_doan(
                    t_from, t_to) else 'không che mặt được clip này'))
            if not self._gui(r, job=job['id']):
                self.mc.job_done(job['id'], dict(error='máy camera không gửi được clip lên máy chủ'))
            return
        r = self.cat(v['t_from'], v['t_to'], cho=False, che=self.can_che())
        if r is not None:
            self._gui(r, eid=v['eid'])

    def _co_doan(self, t_from, t_to):
        return any(d['end'] > t_from and d['start'] < t_to and d['size'] > 0 for d in self.doan())

    def _gui(self, r, eid=None, job=None):
        import requests
        path, a, b = r
        params = dict(camera=self.camera, t_from=int(a * 1000), t_to=int(b * 1000))
        if eid:
            params['eid'] = eid
        if job:
            params['job'] = job
        headers = {'Content-Type': 'video/mp4'}
        key = self.mc.s.headers.get('X-Edge-Key')
        if key:
            headers['X-Edge-Key'] = key
        try:
            data = Path(path).read_bytes()
            for lan in range(3):
                try:
                    res = requests.post(f'{self.mc.url}/api/edge/clip', params=params, data=data, headers=headers,
                                        timeout=30)
                    if res.status_code < 500:
                        if res.status_code >= 400:
                            print(f'  [ghi hình] máy chủ không nhận clip: HTTP {res.status_code} {res.text[:120]}')
                        return res.status_code < 400
                except requests.RequestException:
                    pass
                if self._stop.is_set():
                    break
                time.sleep(2)
            return False
        except OSError:
            return False
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass

    def dong(self, cho=10.0):
        """Dừng ghi (đóng tệp cuối cho trọn), cắt và gửi nốt clip sự kiện còn chờ."""
        self._stop.set()
        if self._ghi is not None:
            self._ghi.join(timeout=12)
        if self._lam is not None:
            self._lam.join(timeout=cho)
        self.on = False


def tao(args, camera, mc=None):
    """GhiVideo theo cờ dòng lệnh của easyfnb_test.py, hoặc None khi không bật --ghi-hinh."""
    if not getattr(args, 'ghi_hinh', False):
        return None
    goc = Path(args.ghi_hinh_dir) if getattr(args, 'ghi_hinh_dir', None) else HERE / 'ghi_hinh'
    gv = GhiVideo(goc / ten_an_toan(camera), camera=camera, fps=args.ghi_hinh_fps, gio=args.ghi_hinh_gio,
                  gb=args.ghi_hinh_gb, mo_mat=not getattr(args, 'khong_mo_mat', False))
    if mc is not None:
        gv.noi(mc)
    return gv


def viec_clip(gv, mc, job):
    """Việc `clip` máy chủ nhờ (web xin clip một khoảng thời gian)."""
    if gv is None or gv.mc is None:
        mc.job_done(job.get('id'), dict(error='máy camera đang không ghi hình (chạy thêm --ghi-hinh)'))
    else:
        gv.viec(job)
