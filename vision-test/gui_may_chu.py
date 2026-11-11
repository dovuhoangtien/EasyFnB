"""Gửi kết quả của pipeline lên máy chủ Easy FnB (easy-fnb/server, hợp đồng trong server/API.md).

Gửi bằng một luồng nền: sự kiện và trạng thái bàn đi theo hàng đợi; khung hình chỉ giữ cái mới nhất
(mạng chậm thì bỏ khung cũ chứ không dồn ứ). Pipeline không bao giờ phải chờ mạng.

Vùng bàn: lấy từ máy chủ lúc bắt đầu, rồi cứ vài giây hỏi lại. Vẽ hay sửa vùng trên web thì camera
áp dụng ngay, không phải chạy lại. Vùng nhận được cũng lưu vào vung_ban_may_chu.json, để máy chủ
khởi động lại (Cloud Run) thì camera đẩy lên lại được.

Gói bằng chứng cho Gemini: mỗi sự kiện có `eid` riêng. Sự kiện gọi phục vụ / cần dọn được gửi ngay, rồi
khoảng 1 giây sau gửi thêm POST /api/edge/evidence {camera, eid, strip_jpeg_b64, overview_jpeg_b64,
ref_jpeg_b64, items} cùng hàng đợi. Mọi ảnh gửi đi đã được pipeline làm mờ mặt trước khi tới đây.
"""
import base64
import json
import queue
import threading
import time
from pathlib import Path

import cv2
import requests

CACHE = Path(__file__).resolve().parent / 'vung_ban_may_chu.json'


def _sig(z):
    """Dấu của một bộ vùng bàn để biết có đổi không (bỏ qua sai số làm tròn)."""
    return json.dumps([z.get('frame_w'), z.get('frame_h'),
                       [[t['id'], [[round(float(x), 1), round(float(y), 1)] for x, y in t['polygon']]]
                        for t in z.get('tables') or []]])


class MayChu:
    def __init__(self, url, camera, key=None, frame_width=960, poll_s=3.0, cache=CACHE):
        self.url = url.rstrip('/')
        self.camera = camera
        self.s = requests.Session()
        if key:
            self.s.headers['X-Edge-Key'] = key
        self.frame_width = frame_width
        self.q = queue.Queue(maxsize=500)
        self._live = None            # (jpeg, params) mới nhất chưa gửi
        self._raw = None
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.loi = 0
        self.poll_s = poll_s
        self.cache = cache
        self._zones_sig = None       # None: chưa nạp vùng bàn, chưa hỏi lại
        self._current = None         # vùng bàn camera đang dùng (dạng của máy chủ)
        self._zones_new = None       # vùng bàn mới từ máy chủ, chờ pipeline lấy
        self._last_poll = time.monotonic()
        self.t = threading.Thread(target=self._run, daemon=True)
        self.t.start()

    # ------------------------------------------------------------ vùng bàn
    def load_zones(self, local, W, H):
        """Vùng bàn theo pixel của video này. Máy chủ có thì dùng (co giãn theo cỡ ảnh lúc vẽ).
        Máy chủ chưa có thì đẩy lên vùng có sẵn: zones.json của clip, hoặc vùng đã lưu lần trước."""
        self.W, self.H = W, H
        body = None
        if local:
            body = dict(camera=self.camera, frame_w=W, frame_h=H,
                        tables=[dict(id=k, polygon=v) for k, v in local.items()])
            msg = 'đã đẩy vùng bàn trong zones.json lên máy chủ'
        elif (old := self._cached()) and old.get('tables'):
            body = old
            msg = 'máy chủ chưa có vùng bàn, đã đẩy lên vùng lưu lần trước'
        self._current = body
        self._zones_sig = ''         # bật hỏi lại định kỳ
        try:
            z = self._get_zones()
        except (requests.RequestException, ValueError) as e:
            print(f'  chưa kết nối được máy chủ ({e.__class__.__name__}); dùng vùng bàn có sẵn, kết nối được sẽ tự đồng bộ')
            return self._scale(body) if body else {}
        if z.get('frame_w'):         # máy chủ đã có vùng bàn cho camera này (kể cả khi đã xoá hết)
            self._use(z)
            print(f"  vùng bàn từ máy chủ: {', '.join(t['id'] for t in z['tables']) or 'chưa có bàn nào'}")
            return self._scale(z)
        if body is None:
            self._zones_sig = _sig(z)
            print('  chưa có vùng bàn: mở trang Cài đặt trên web để vẽ, camera sẽ tự áp dụng')
            return {}
        try:
            z = self.s.put(f'{self.url}/api/zones', json=body, timeout=5).json()
            print(f"  {msg}: {', '.join(t['id'] for t in z['tables'])}")
            self._use(z)
        except (requests.RequestException, ValueError, KeyError):
            pass
        return self._scale(body)

    def _use(self, z):
        self._zones_sig = _sig(z)
        self._current = z
        self._remember(z)

    def new_zones(self):
        """Vùng bàn mới nếu trên web vừa vẽ/sửa (dict, có thể rỗng); None nếu không đổi."""
        with self.lock:
            z, self._zones_new = self._zones_new, None
        return None if z is None else self._scale(z)

    def _get_zones(self):
        r = self.s.get(f'{self.url}/api/zones', params=dict(camera=self.camera), timeout=5)
        r.raise_for_status()
        return r.json()

    def _scale(self, z):
        sx = self.W / z['frame_w'] if z.get('frame_w') else 1.0
        sy = self.H / z['frame_h'] if z.get('frame_h') else 1.0
        return {t['id']: [[x * sx, y * sy] for x, y in t['polygon']] for t in z.get('tables') or []}

    def _cached(self):
        try:
            return json.loads(self.cache.read_text(encoding='utf-8')).get(self.camera)
        except (OSError, ValueError):
            return None

    def _remember(self, z):
        try:
            all_ = json.loads(self.cache.read_text(encoding='utf-8')) if self.cache.exists() else {}
            all_[self.camera] = z
            self.cache.write_text(json.dumps(all_, ensure_ascii=False), encoding='utf-8')
        except (OSError, ValueError):
            pass

    def _poll_zones(self):
        if self._zones_sig is None or time.monotonic() - self._last_poll < self.poll_s:
            return
        self._last_poll = time.monotonic()
        try:
            z = self._get_zones()
        except (requests.RequestException, ValueError):
            return
        if not z.get('frame_w'):
            # máy chủ không có bản ghi nào (vừa khởi động lại, hoặc lúc đầu chưa kết nối được),
            # khác với người dùng xoá hết bàn: đẩy lên vùng camera đang dùng, camera giữ nguyên
            if self._current and self._current.get('tables'):
                try:
                    self._use(self.s.put(f'{self.url}/api/zones', json=self._current, timeout=5).json())
                    print('  máy chủ chưa có vùng bàn, đã đẩy lên vùng camera đang dùng')
                except (requests.RequestException, ValueError, KeyError):
                    pass
            return
        if _sig(z) == self._zones_sig:
            return
        self._use(z)
        with self.lock:
            self._zones_new = z
        print(f"  vùng bàn trên web vừa đổi: {', '.join(t['id'] for t in z.get('tables') or []) or 'không còn bàn nào'}")

    # ------------------------------------------------------------ gửi
    def event(self, e, crop_bgr=None):
        b64 = None
        if crop_bgr is not None and crop_bgr.size:
            ok, buf = cv2.imencode('.jpg', crop_bgr, [cv2.IMWRITE_JPEG_QUALITY, 85])
            b64 = base64.b64encode(buf.tobytes()).decode() if ok else None
        body = dict(camera=self.camera, kind=e['loai'], table=e.get('ban'), video_t=e.get('t'),
                    box=e.get('box'), score=e.get('diem'), detail=e.get('chi_tiet') or '', crop_jpeg_b64=b64,
                    eid=e.get('eid'))
        if e.get('items'):
            body['items'] = e['items']
        self._put(('POST', '/api/edge/event', body))

    def evidence(self, eid, strip_jpg, overview_jpg, ref_jpg=None, items=None):
        """Gói bằng chứng của sự kiện `eid` (JPEG bytes đã làm mờ mặt). Hàng đợi đã dài (máy chủ chậm/mất)
        thì bỏ gói này: sự kiện vẫn tới, chỉ thiếu phần xác minh."""
        if self.q.qsize() > 50:
            self._loi('/api/edge/evidence: hàng đợi dài, bỏ gói bằng chứng')
            return
        def b64(img):
            if img is None:
                return None
            if not isinstance(img, (bytes, bytearray)):  # ảnh BGR từ OpenCV: mã hoá JPEG
                if not getattr(img, 'size', 0):
                    return None
                ok, buf = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 85])
                if not ok:
                    return None
                img = buf.tobytes()
            return base64.b64encode(img).decode() if img else None
        body = dict(camera=self.camera, eid=eid, strip_jpeg_b64=b64(strip_jpg), overview_jpeg_b64=b64(overview_jpg),
                    ref_jpeg_b64=b64(ref_jpg), items=items or None)
        self._put(('POST', '/api/edge/evidence', body))

    def tables(self, tables):
        body = dict(camera=self.camera, tables=[dict(id=tb.name, state=tb.state or tb.hien_thi, people=int(tb.n_hien),
                                                     dirty=None if tb.dirty_now is None else float(tb.dirty_now))
                                                for tb in tables])
        self._put(('POST', '/api/edge/tables', body))

    def frame_live(self, img, fps=None, source=None):
        self._set_frame('live', img, fps, source)

    def frame_raw(self, img, source=None):
        self._set_frame('raw', img, None, source)

    def _set_frame(self, kind, img, fps, source):
        h, w = img.shape[:2]
        if w > self.frame_width:
            img = cv2.resize(img, (self.frame_width, int(h * self.frame_width / w)), interpolation=cv2.INTER_AREA)
        ok, buf = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 72 if kind == 'live' else 90])
        if not ok:
            return
        params = dict(camera=self.camera, kind=kind, w=w, h=h)
        if fps:
            params['fps'] = round(float(fps), 1)
        if source:
            params['source'] = source
        with self.lock:
            if kind == 'raw':
                self._raw = (buf.tobytes(), params)
            else:
                self._live = (buf.tobytes(), params)

    def _put(self, item):
        try:
            self.q.put_nowait(item)
        except queue.Full:
            pass

    def _run(self):
        while not self.stop.is_set() or not self.q.empty():
            sent = False
            try:
                method, path, body = self.q.get(timeout=0.05)
                self._send(method, path, json=body)
                sent = True
            except queue.Empty:
                pass
            with self.lock:
                fr, self._live = self._live, None
                raw, self._raw = self._raw, None
            for f in (raw, fr):
                if f is not None:
                    self._send('POST', '/api/edge/frame', data=f[0], params=f[1],
                               headers={'Content-Type': 'image/jpeg'})
                    sent = True
            if not self.stop.is_set():
                self._poll_zones()
            if not sent:
                time.sleep(0.02)

    def _send(self, method, path, **kw):
        try:
            r = self.s.request(method, self.url + path, timeout=5, **kw)
            if r.status_code >= 400:
                self._loi(f'{path}: HTTP {r.status_code} {r.text[:120]}')
            else:
                self.loi = 0
        except requests.RequestException as e:
            self._loi(f'{path}: {e.__class__.__name__}')

    def _loi(self, msg):
        self.loi += 1
        if self.loi in (1, 10, 100):
            print(f'  [máy chủ] lỗi gửi ({self.loi} lần liên tiếp): {msg}')

    def close(self, wait=5.0):
        self.stop.set()
        self.t.join(timeout=wait)
