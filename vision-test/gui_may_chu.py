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
# Máy chủ mất vài phút rồi có lại: hàng đợi còn tin cũ, gửi dồn lên thì web báo một loạt việc đã nguội
# (máy chủ tính giờ từ lúc nhận). Tin chờ lâu hơn mức này thì bỏ, không gửi nữa (giây chờ trong hàng đợi).
# "Cần dọn" / "đã dọn" không có hạn: bàn vẫn còn bẩn (hoặc đã sạch) thì báo muộn vẫn đúng.
TUOI_TOI_DA_S = {'/api/edge/tables': 5.0, '/api/edge/table-snap': 60.0, '/api/edge/evidence': 60.0,
                 '/api/edge/event': 60.0}
SU_KIEN_KHONG_HAN = ('can_don', 'da_don')


def qua_han(path, body, tuoi):
    """Tin đã chờ `tuoi` giây trong hàng đợi có còn đáng gửi không."""
    han = TUOI_TOI_DA_S.get(path)
    if han is None or tuoi <= han:
        return False
    return not (path == '/api/edge/event' and isinstance(body, dict) and body.get('kind') in SU_KIEN_KHONG_HAN)


def _poly(pts):
    return [[round(float(x), 1), round(float(y), 1)] for x, y in pts]


def _sig_ban(z):
    """Dấu riêng của vùng bàn: chỉ khi dấu này đổi thì pipeline mới dựng lại các bàn (mất trạng thái bàn)."""
    return json.dumps([z.get('frame_w'), z.get('frame_h'),
                       [[t['id'], _poly(t['polygon'])] for t in z.get('tables') or []]])


def _sig(z):
    """Dấu của cả bộ vùng (bàn, vùng khác, trạng thái an ninh) để biết có đổi không (bỏ qua sai số làm tròn)."""
    return json.dumps([_sig_ban(z),
                       [[a.get('id'), a.get('type'), a.get('name'), _poly(a.get('polygon') or [])]
                        for a in z.get('areas') or [] if isinstance(a, dict)],
                       an_ninh_tu(z)], sort_keys=True)


# Máy chủ cũ chưa trả `an_ninh`, hoặc thiếu trường: quán coi như đang mở, mọi tính năng an ninh tắt, vẫn che mặt.
AN_NINH_MAC_DINH = dict(closed=False, after_hours=False, restricted=False, item_taken=False, delivery_now=False,
                        blur_faces=True)


def an_ninh_tu(z):
    """Trạng thái an ninh trong câu trả lời GET /api/zones, đã điền mặc định an toàn."""
    out = dict(AN_NINH_MAC_DINH)
    src = (z or {}).get('an_ninh')
    if isinstance(src, dict):
        for k in out:
            if isinstance(src.get(k), bool):
                out[k] = src[k]
    return out


def _b64(img):
    """Ảnh BGR (OpenCV) hoặc JPEG bytes -> base64 của JPEG; None nếu rỗng."""
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


class MayChu:
    def __init__(self, url, camera, key=None, frame_width=960, poll_s=3.0, cache=CACHE, session=None):
        self.url = url.rstrip('/')
        self.camera = camera
        self.s = session or requests.Session()   # session: chỉ để test (không đụng mạng)
        self.bo_cu = 0               # số tin đã bỏ vì chờ quá lâu hoặc hàng đợi đầy
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
        self._areas = []             # vùng khác (quầy, kho, giữ xe, cửa) theo pixel lúc vẽ trên web
        self._an_ninh = dict(AN_NINH_MAC_DINH)
        self._last_poll = time.monotonic()
        self._jobs = []              # việc thiết lập web nhờ làm (tìm bàn, chụp nhân viên), chờ pipeline lấy
        self._jobs_every = 1.0
        self._last_jobs = 0.0
        self.want_refs = False       # pipeline bật khi chạy --nv-theo-anh
        self.on_event = None         # ghi_video.py gắn vào: hẹn cắt clip cho từng sự kiện (có thể đặt eid cho sự kiện)
        self._refs_ver = None
        self._refs_new = None
        self._last_refs = -1e9
        self.t = threading.Thread(target=self._run, daemon=True)
        self.t.start()

    # ------------------------------------------------------------ vùng bàn
    def load_zones(self, local, W, H, live=False):
        """Vùng bàn theo pixel của video này. Máy chủ có thì dùng (co giãn theo cỡ ảnh lúc vẽ).
        Máy chủ chưa có thì đẩy lên vùng có sẵn: zones.json của clip, hoặc vùng đã lưu lần trước.
        live (camera thật, điện thoại): không đẩy gì, chủ quán bấm Tự tìm bàn hoặc vẽ trên web."""
        self.W, self.H = W, H
        body = None
        if live:
            pass
        elif local:
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
        cur = {k: v for k, v in z.items() if k != 'an_ninh'}   # an_ninh máy chủ tự tính, không đẩy lên lại
        areas = [a for a in z.get('areas') or [] if isinstance(a, dict) and a.get('id') and a.get('polygon')]
        with self.lock:
            self._current = cur
            self._areas = areas
            self._an_ninh = an_ninh_tu(z)
        self._remember(cur)

    def an_ninh(self):
        """Trạng thái an ninh mới nhất từ máy chủ (dict, luôn đủ trường, mặc định an toàn)."""
        with self.lock:
            return dict(self._an_ninh)

    def areas(self):
        """Vùng khác bàn theo pixel của video này: [dict(id, type, name, poly)]."""
        with self.lock:
            areas, z = list(self._areas), self._current or {}
        W, H = getattr(self, 'W', None), getattr(self, 'H', None)
        sx = W / z['frame_w'] if z.get('frame_w') and W else 1.0
        sy = H / z['frame_h'] if z.get('frame_h') and H else 1.0
        out = []
        for a in areas:
            try:
                poly = [[float(x) * sx, float(y) * sy] for x, y in a['polygon']]
            except (TypeError, ValueError):
                continue
            if len(poly) >= 3:
                out.append(dict(id=str(a['id']), type=a.get('type'), name=a.get('name') or str(a['id']), poly=poly))
        return out

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
        # chỉ vùng khác hay trạng thái an ninh đổi (quán đóng/mở mỗi ngày): không dựng lại bàn
        ban_doi = _sig_ban(z) != _sig_ban(self._current or {})
        an_cu = self.an_ninh()
        self._use(z)
        if ban_doi:
            with self.lock:
                self._zones_new = z
            print(f"  vùng bàn trên web vừa đổi: {', '.join(t['id'] for t in z.get('tables') or []) or 'không còn bàn nào'}")
        a = self.an_ninh()
        if a != an_cu:
            print(f"  an ninh: quán {'ĐÓNG' if a['closed'] else 'mở'}, ngoài giờ {'bật' if a['after_hours'] else 'tắt'}, "
                  f"khu cấm {'bật' if a['restricted'] else 'tắt'}, lấy đồ {'bật' if a['item_taken'] else 'tắt'}, "
                  f"che mặt {'bật' if a['blur_faces'] else 'tắt'}")

    # ------------------------------------------------------------ việc thiết lập, ảnh nhân viên
    def take_jobs(self):
        with self.lock:
            j, self._jobs = self._jobs, []
        return j

    def job_done(self, jid, result):
        self._put(('POST', f'/api/edge/jobs/{jid}', result))

    def new_staff_refs(self):
        """[(mã nhân viên, kind, JPEG bytes)] nếu ảnh nhân viên trên web vừa đổi; None nếu không đổi."""
        with self.lock:
            r, self._refs_new = self._refs_new, None
        return r

    def _poll_jobs(self):
        if time.monotonic() - self._last_jobs < self._jobs_every:
            return
        self._last_jobs = time.monotonic()
        try:
            r = self.s.get(f'{self.url}/api/edge/jobs', params=dict(camera=self.camera), timeout=3)
            if r.status_code == 404:     # máy chủ bản cũ chưa có phần thiết lập: hỏi thưa lại
                self._jobs_every = 30.0
                return
            jobs = (r.json().get('jobs') or []) if r.ok else []
        except (requests.RequestException, ValueError):
            return
        self._jobs_every = 1.0
        if jobs:
            with self.lock:
                self._jobs += jobs

    def _poll_refs(self):
        if not self.want_refs or time.monotonic() - self._last_refs < 5:      # ảnh nhân viên vừa chụp có hiệu lực sau vài giây
            return
        self._last_refs = time.monotonic()
        try:
            r = self.s.get(f'{self.url}/api/edge/staff-refs', timeout=5)
            if not r.ok:
                return
            z = r.json()
            if z.get('version') == self._refs_ver:
                return
            out = []
            for ref in z.get('refs') or []:
                img = self.s.get(self.url + ref['url'], timeout=10)
                if img.ok:
                    out.append((ref['staff'], ref['kind'], img.content))
        except (requests.RequestException, ValueError, KeyError):
            return
        self._refs_ver = z.get('version')
        with self.lock:
            self._refs_new = out

    # ------------------------------------------------------------ gửi
    def event(self, e, crop_bgr=None):
        if self.on_event is not None:
            self.on_event(e)
        b64 = None
        if crop_bgr is not None and crop_bgr.size:
            ok, buf = cv2.imencode('.jpg', crop_bgr, [cv2.IMWRITE_JPEG_QUALITY, 85])
            b64 = base64.b64encode(buf.tobytes()).decode() if ok else None
        body = dict(camera=self.camera, kind=e['loai'], table=e.get('ban'), video_t=e.get('t'),
                    box=e.get('box'), score=e.get('diem'), detail=e.get('chi_tiet') or '', crop_jpeg_b64=b64,
                    eid=e.get('eid'))
        if e.get('items'):
            body['items'] = e['items']
        if 'area' in e:
            body['area'] = e['area']
        if e.get('images'):          # an ninh: ảnh gửi kèm sự kiện, [(vai trò, ảnh BGR hoặc JPEG)], đã che mặt
            body['images'] = [dict(role=r, jpeg_b64=b) for r, img in e['images'] if (b := _b64(img))]
        self._put(('POST', '/api/edge/event', body))

    def evidence(self, eid, strip_jpg, overview_jpg, ref_jpg=None, items=None, person_jpg=None):
        """Gói bằng chứng của sự kiện `eid` (JPEG bytes đã làm mờ mặt). Hàng đợi đã dài (máy chủ chậm/mất)
        thì bỏ gói này: sự kiện vẫn tới, chỉ thiếu phần xác minh."""
        if self.q.qsize() > 50:
            self._loi('/api/edge/evidence: hàng đợi dài, bỏ gói bằng chứng')
            return
        b64 = _b64
        body = dict(camera=self.camera, eid=eid, strip_jpeg_b64=b64(strip_jpg), overview_jpeg_b64=b64(overview_jpg),
                    ref_jpeg_b64=b64(ref_jpg), items=items or None)
        if person_jpg is not None:   # lay_do: ảnh "người ngồi bàn" (đã che mặt)
            body['person_jpeg_b64'] = b64(person_jpg)
        self._put(('POST', '/api/edge/evidence', body))

    def tables(self, tables):
        body = dict(camera=self.camera, tables=[dict(id=tb.name, state=tb.state or tb.hien_thi, people=int(tb.n_hien),
                                                     dirty=None if tb.dirty_now is None else float(tb.dirty_now))
                                                for tb in tables])
        self._put(('POST', '/api/edge/tables', body))

    def table_snap(self, table, img, ts=None):
        """Ảnh một bàn đang có khách (BGR, đã làm mờ mặt) để máy chủ xem bữa ăn tới đâu. Thu về cạnh dài 640,
        JPEG 80. Hàng đợi đang dài (máy chủ chậm/mất) thì bỏ: ảnh sau sẽ thay."""
        if img is None or not getattr(img, 'size', 0) or self.q.qsize() > 20:
            return
        h, w = img.shape[:2]
        k = 640 / max(h, w)
        if k < 1:
            img = cv2.resize(img, (max(1, int(w * k)), max(1, int(h * k))), interpolation=cv2.INTER_AREA)
        ok, buf = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if ok:
            self._put(('POST', '/api/edge/table-snap',
                       dict(camera=self.camera, table=table, ts=ts or time.time(),
                            jpeg_b64=base64.b64encode(buf.tobytes()).decode())))

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
        item = (time.monotonic(), item)
        try:
            self.q.put_nowait(item)
        except queue.Full:
            # đầy (máy chủ mất lâu): bỏ tin cũ nhất chứ không bỏ tin mới, tin mới mới là thứ còn đúng
            try:
                self.q.get_nowait()
                self.bo_cu += 1
                self.q.put_nowait(item)
            except (queue.Empty, queue.Full):
                pass

    def _run(self):
        while not self.stop.is_set() or not self.q.empty():
            sent = False
            try:
                t_put, (method, path, body) = self.q.get(timeout=0.05)
                if qua_han(path, body, time.monotonic() - t_put):
                    self.bo_cu += 1
                    if self.bo_cu in (1, 10, 100):
                        print(f'  [máy chủ] bỏ tin đã chờ quá lâu ({self.bo_cu} tin): {path}')
                    continue
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
                self._poll_jobs()
                self._poll_refs()
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
