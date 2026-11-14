"""Clip video của camera: clip của từng việc và clip xin theo khoảng thời gian.

Máy camera tự ghi hình (vision-test/ghi_video.py) và giữ video ở quán. Máy chủ chỉ giữ các clip ngắn:

  - Clip sự kiện: khoảng 16 giây sau mỗi sự kiện tạo việc, camera gửi POST /api/edge/clip?eid=... Máy chủ gắn
    clip vào việc sinh ra từ `eid` đó (theo hub.eids, y như gói ảnh xác minh): việc có thêm `clip: true`, xem ở
    GET /api/alerts/{id}/clip.mp4. Sự kiện đã gộp vào việc cũ thì clip gắn vào việc cũ; việc đã có clip thì giữ
    clip đầu; việc đã đóng vẫn nhận clip. Chưa thấy việc nào mang `eid` đó thì giữ clip EARLY_S giây rồi bỏ.
  - Clip theo yêu cầu: POST /api/clips {camera, t_from, t_to} xếp một việc `clip` cho máy camera (GET
    /api/edge/jobs); camera cắt rồi gửi POST /api/edge/clip?job=..., hoặc trả lỗi qua POST /api/edge/jobs/{id}.

Tệp nằm trong DATA_DIR/clips, tên do máy chủ đặt (không bao giờ ghép đường dẫn từ dữ liệu gửi lên). Thư mục có
trần dung lượng, đầy thì xoá clip cũ nhất. "Bắt đầu ca mới" (reset) xoá hết clip trên máy chủ, như ảnh cắt;
video gốc trên máy camera không bị đụng tới nên vẫn xin lại được clip.
"""
import asyncio
import os
import shutil
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse

from .hub import now_ms

MAX_UPLOAD = 40 * 1024 * 1024      # một clip gửi lên
MAX_CLIP_MS = 60_000               # clip theo yêu cầu dài nhất
EARLY_S = 30.0                     # clip của eid chưa có việc: giữ chừng này rồi bỏ
WAIT_S = 30.0                      # chờ máy camera trả clip theo yêu cầu
MAX_REQ = 50                       # số yêu cầu clip còn nhớ
GOC_TTL_S = 24 * 3600             # clip gốc (không che mặt) trên máy chủ: tự xoá sau chừng này, trừ khi giữ làm bằng chứng
MAX_DIR = int(float(os.environ.get('CLIPS_MAX_MB') or 2000) * 1024 * 1024)   # trần dung lượng thư mục clips


class Clips:
    def __init__(self, hub, data_dir, max_bytes=MAX_DIR, wait_s=WAIT_S, early_s=EARLY_S, clock=time.monotonic):
        self.hub = hub
        self.dir = Path(data_dir) / 'clips'
        self.dir.mkdir(parents=True, exist_ok=True)
        self.keep_dir = Path(data_dir) / 'bang_chung'   # clip giữ làm bằng chứng: "Bắt đầu ca mới" không xoá
        self.max_bytes, self.wait_s, self.early_s, self.clock = max_bytes, wait_s, early_s, clock
        self.by_alert = {}   # alert id -> dict(file, camera, t_from, t_to)
        self.early = {}      # eid -> dict(file, camera, t_from, t_to, at) khi chưa có việc nào mang eid này
        self.req = {}        # id yêu cầu -> dict(id, status, camera, t_from, t_to, error, file, job)
        self._watch = None
        self._bg = set()
        # clip có sẵn theo giờ (dữ liệu demo, đã che mặt): xin xem lại khoảng nào có clip thì trả luôn, không cần camera
        self.demo_dir = Path(data_dir) / 'video_demo'
        try:
            import json
            self.demo = [x for x in json.loads((self.demo_dir / 'index.json').read_text(encoding='utf-8'))
                         if (self.demo_dir / x['file']).exists()]
        except (OSError, ValueError, KeyError, TypeError):
            self.demo = []
        for f in self.dir.glob('*.mp4'):    # việc nằm trong RAM: clip của lần chạy trước không còn ai trỏ tới
            self._unlink(f)

    @staticmethod
    def _unlink(f):
        """Xoá tệp; tệp đang được gửi cho trình duyệt (Windows khoá) thì thôi, lần dọn sau xoá."""
        try:
            Path(f).unlink(missing_ok=True)
            return True
        except OSError:
            return False

    def _save(self, data):
        f = self.dir / f'{uuid.uuid4().hex}.mp4'
        f.write_bytes(data)
        return f

    # ------------------------------------------------------------ clip sự kiện
    def add_event_clip(self, eid, camera, t_from, t_to, data):
        """Clip của sự kiện `eid`. Trả alert id đã gắn, hoặc None (chưa có việc: giữ tạm)."""
        eid = str(eid)
        self.sweep()
        meta = dict(camera=camera, t_from=t_from, t_to=t_to)
        aid = self.hub.eids.get(eid)
        a = self.hub.alerts.get(aid) if aid else None
        if a is None:
            old = self.early.pop(eid, None)       # gửi lại cùng eid: giữ bản mới
            if old:
                self._unlink(old['file'])
            self.early[eid] = dict(meta, file=self._save(data), at=self.clock())
            self._start_watch()
            self._trim()
            return None
        if a['id'] not in self.by_alert:          # việc đã có clip (gửi trùng, hoặc sự kiện gộp): giữ clip đầu
            self._attach(a, dict(meta, file=self._save(data)))
            self._trim()
        return a['id']

    def _attach(self, a, meta):
        if a['id'] in self.by_alert:
            self._unlink(meta['file'])
            return
        self.by_alert[a['id']] = meta
        a['clip'] = True
        self.hub.publish('alert', self.hub._public(a))

    def sweep(self):
        """Clip tới trước việc: gắn khi việc xuất hiện, quá early_s thì bỏ."""
        t = self.clock()
        for eid, m in list(self.early.items()):
            aid = self.hub.eids.get(eid)
            a = self.hub.alerts.get(aid) if aid else None
            if a is not None:
                del self.early[eid]
                self._attach(a, {k: v for k, v in m.items() if k != 'at'})
            elif t - m['at'] > self.early_s:
                del self.early[eid]
                self._unlink(m['file'])

    def _start_watch(self):
        async def watch():
            while self.early:
                await asyncio.sleep(1)
                self.sweep()
        if self._watch is None or self._watch.done():
            try:
                self._watch = asyncio.get_running_loop().create_task(watch())
            except RuntimeError:      # không có vòng lặp (gọi từ test đồng bộ): lần gửi sau sẽ quét
                pass

    def alert_file(self, aid):
        m = self.by_alert.get(aid)
        return m['file'] if m and aid in self.hub.alerts and m['file'].exists() else None

    # ------------------------------------------------------------ clip theo yêu cầu
    def view(self, r):
        return dict(id=r['id'], status=r['status'], camera=r['camera'], t_from=r['t_from'], t_to=r['t_to'],
                    url=f"/api/clips/{r['id']}.mp4" if r['status'] == 'ready' else None, error=r['error'],
                    **(dict(goc=True, kept=bool(r.get('kept'))) if r.get('goc') else {}))

    def request(self, camera, t_from, t_to, goc=False):
        """Xin clip [t_from, t_to] (ms) của một camera. goc=True: bản gốc không che mặt (chỉ chủ quán, có PIN). Phải gọi trong vòng lặp asyncio. ValueError nếu khoảng sai."""
        try:
            t_from, t_to = int(t_from), int(t_to)
        except (TypeError, ValueError):
            raise ValueError('cần t_from và t_to (mili giây)')
        if not isinstance(camera, str) or not camera:
            raise ValueError('cần mã camera')
        now = now_ms()
        if t_to <= t_from:
            raise ValueError('t_to phải sau t_from')
        if t_from > now:
            raise ValueError('chưa tới giờ đó nên chưa có hình')
        t_to = min(t_to, t_from + MAX_CLIP_MS, now)
        if t_to - t_from < 500:
            raise ValueError('khoảng thời gian quá ngắn')
        self.purge_goc()
        r = dict(id='c' + uuid.uuid4().hex[:12], status='pending', camera=camera, t_from=t_from, t_to=t_to,
                 error=None, file=None, job=None, goc=bool(goc), at=time.time())
        self.req[r['id']] = r
        d = self._tim_demo(camera, t_from, t_to)
        if d is not None:
            r.update(status='ready', file=self.demo_dir / d['file'], t_from=d['t_from'], t_to=d['t_to'], demo=True)
        for old in list(self.req)[:-MAX_REQ]:
            if self.req[old]['file'] and not self.req[old].get('demo'):
                self._unlink(self.req[old]['file'])
            del self.req[old]
        if r['status'] == 'ready':
            return self.view(r)
        if not self.hub.camera_live(camera) and self.demo:
            r.update(status='failed', error='Không có video lưu lại cho lúc đó.')
            return self.view(r)
        if not self.hub.camera_live(camera):
            r.update(status='failed', error=f'Camera {camera} đang không chạy nên chưa lấy được clip.')
            return self.view(r)
        r['job'], fut = self.hub.new_job(camera, 'clip', t_from=t_from, t_to=t_to, **({'goc': True} if goc else {}))
        task = asyncio.get_running_loop().create_task(self._wait(r, fut))
        self._bg.add(task)
        task.add_done_callback(self._bg.discard)
        return self.view(r)

    async def _wait(self, r, fut):
        try:
            res = await asyncio.wait_for(fut, self.wait_s)
        except asyncio.TimeoutError:
            self.hub.jobs.pop(r['job'], None)
            if r['status'] == 'pending':
                r.update(status='failed', error='Máy camera không trả lời.')
            return
        if r['status'] == 'pending':     # camera trả lỗi qua POST /api/edge/jobs/{id} (clip tốt thì đã là ready)
            err = res.get('error') if isinstance(res, dict) else None
            r.update(status='failed', error=str(err or 'Máy camera không gửi clip.')[:200])

    def _tim_demo(self, camera, t_from, t_to):
        """Clip demo của camera phủ khoảng [t_from, t_to] (ms) nhiều nhất; không có clip nào chạm khoảng đó thì None."""
        best, phu = None, 0
        for x in self.demo:
            if x.get('camera', 'cam1') != camera:
                continue
            p = min(x['t_to'], t_to) - max(x['t_from'], t_from)
            if p > phu:
                best, phu = x, p
        return best

    def add_job_clip(self, job, t_from, t_to, data):
        """Clip máy camera gửi cho việc `job`. Trả id yêu cầu, hoặc None nếu không còn yêu cầu nào chờ việc đó."""
        r = next((x for x in self.req.values() if x['job'] == job), None)
        if r is None or r['status'] == 'ready':
            return None
        r.update(status='ready', error=None, file=self._save(data), t_from=t_from, t_to=t_to)
        self.hub.job_result(job, dict(ok=True))
        self._trim()
        return r['id']

    def get(self, cid):
        return self.req.get(cid)

    # ------------------------------------------------------------ clip gốc không che mặt
    def purge_goc(self):
        """Clip gốc quá GOC_TTL_S thì xoá tệp (bản giữ làm bằng chứng nằm ở thư mục khác, không bị xoá)."""
        t = time.time()
        for r in self.req.values():
            if r.get('goc') and r['file'] and t - r['at'] > GOC_TTL_S:
                self._unlink(r['file'])
                r.update(status='failed', file=None, error='Clip gốc đã tự xoá sau 24 giờ.')

    def keep(self, cid):
        """Giữ một clip làm bằng chứng: chép sang DATA_DIR/bang_chung. Trả tên tệp."""
        r = self.req.get(cid)
        if r is None or r['status'] != 'ready' or not r['file'] or not Path(r['file']).exists():
            raise KeyError(cid)
        self.keep_dir.mkdir(parents=True, exist_ok=True)
        f = self.keep_dir / f'{cid}.mp4'
        shutil.copyfile(r['file'], f)
        r['kept'] = True
        return f

    def kept_file(self, cid):
        f = self.keep_dir / f"{''.join(ch for ch in cid if ch.isalnum())}.mp4"
        return f if f.exists() else None

    # ------------------------------------------------------------ dọn
    def reset(self):
        """Bắt đầu ca mới: xoá mọi clip trên máy chủ (việc cũng đã xoá). Video trên máy camera còn nguyên."""
        self.by_alert.clear()
        self.early.clear()
        for r in self.req.values():
            if r['status'] == 'pending':
                r.update(status='failed', error='Đã bắt đầu ca mới.')
        self.req.clear()
        for f in self.dir.glob('*.mp4'):
            self._unlink(f)

    def _trim(self):
        """Thư mục vượt trần thì xoá clip cũ nhất trước; việc và yêu cầu trỏ tới clip đã xoá được cập nhật."""
        files = []
        for f in self.dir.glob('*.mp4'):
            try:
                st = f.stat()
                files.append((st.st_mtime, st.st_size, f))
            except OSError:
                pass
        total = sum(s for _, s, _ in files)
        gone = set()
        for _, size, f in sorted(files, key=lambda x: x[0]):
            if total <= self.max_bytes:
                break
            if self._unlink(f):
                total -= size
                gone.add(f)
        if not gone:
            return
        for aid, m in list(self.by_alert.items()):
            if m['file'] in gone:
                del self.by_alert[aid]
                a = self.hub.alerts.get(aid)
                if a is not None:
                    a['clip'] = False
                    self.hub.publish('alert', self.hub._public(a))
        for eid, m in list(self.early.items()):
            if m['file'] in gone:
                del self.early[eid]
        for r in self.req.values():
            if r['file'] in gone:
                r.update(status='failed', file=None, error='Clip đã bị xoá vì hết chỗ lưu, hãy xin lại.')


def router(clips, edge_auth):
    """Các đường API của clip. Gắn vào app trước đường bắt-mọi-thứ của web."""
    r = APIRouter()
    mp4 = dict(media_type='video/mp4', headers={'Cache-Control': 'private, max-age=3600'})

    @r.post('/api/edge/clip', dependencies=[Depends(edge_auth)])
    async def edge_clip(request: Request, camera: str = Query(...), t_from: int = Query(...),
                        t_to: int = Query(...), eid: str | None = None, job: str | None = None):
        """Máy camera gửi một clip MP4 (thân yêu cầu là tệp thô): của sự kiện `eid`, hoặc của việc clip `job`."""
        if not eid and not job:
            raise HTTPException(400, 'cần eid hoặc job')
        n = request.headers.get('content-length', '')
        if n.isdigit() and int(n) > MAX_UPLOAD:
            raise HTTPException(413, 'clip quá lớn (tối đa 40 MB)')
        data = bytearray()
        async for chunk in request.stream():
            data += chunk
            if len(data) > MAX_UPLOAD:
                raise HTTPException(413, 'clip quá lớn (tối đa 40 MB)')
        if len(data) < 16 or data[4:8] != b'ftyp':
            raise HTTPException(400, 'cần tệp MP4')
        if job:
            cid = clips.add_job_clip(job, t_from, t_to, bytes(data))
            if cid is None:
                raise HTTPException(404, 'không còn yêu cầu clip nào chờ việc này')
            return dict(ok=True, clip_id=cid)
        return dict(ok=True, alert_id=clips.add_event_clip(eid, camera, t_from, t_to, bytes(data)))

    @r.get('/api/alerts/{aid}/clip.mp4')
    async def alert_clip(aid: str):
        f = clips.alert_file(aid)
        if f is None:
            raise HTTPException(404, 'việc này chưa có clip')
        return FileResponse(f, **mp4)

    @r.post('/api/clips')
    async def request_clip(body: dict = Body(...)):
        try:
            return clips.request(body.get('camera') or 'cam1', body.get('t_from'), body.get('t_to'))
        except ValueError as e:
            raise HTTPException(400, str(e))

    def need_pin(pin):
        if not clips.hub.pin_ok(pin):
            raise HTTPException(403, 'Cần mã PIN chủ quán')

    @r.get('/api/clips/{name}')
    async def get_clip(name: str, pin: str | None = None, x_owner_pin: str | None = Header(default=None)):
        """/api/clips/{id} trả trạng thái; /api/clips/{id}.mp4 trả tệp. Clip gốc (không che mặt) cần mã PIN
        (header X-Owner-Pin, hoặc ?pin= vì thẻ <video> không gửi được header)."""
        cid = name.removesuffix('.mp4')
        rec = clips.get(cid)
        if rec is None:
            kept = clips.kept_file(cid) if name.endswith('.mp4') else None
            if kept is None:
                raise HTTPException(404, 'không có yêu cầu clip này')
            need_pin(x_owner_pin or pin)
            return FileResponse(kept, **dict(mp4, headers={'Cache-Control': 'no-store'}))
        if not name.endswith('.mp4'):
            return clips.view(rec)
        if rec.get('goc'):
            need_pin(x_owner_pin or pin)
        if rec['status'] != 'ready' or not rec['file'] or not rec['file'].exists():
            raise HTTPException(404, 'clip chưa sẵn sàng')
        return FileResponse(rec['file'], **(dict(mp4, headers={'Cache-Control': 'no-store'}) if rec.get('goc') else mp4))

    @r.post('/api/alerts/{aid}/clip-goc')
    async def raw_clip(aid: str, x_owner_pin: str | None = Header(default=None)):
        """Chủ quán xin bản gốc không che mặt của clip một việc. Mỗi lần xin đều ghi vào nhật ký."""
        need_pin(x_owner_pin)
        a = clips.hub.alerts.get(aid)
        if a is None:
            raise HTTPException(404, 'không có việc này')
        m = clips.by_alert.get(aid)
        t_from, t_to = (m['t_from'], m['t_to']) if m else (a['created_at'] - 10_000, a['created_at'] + 20_000)
        try:
            v = clips.request(a['camera'], t_from, t_to, goc=True)
        except ValueError as e:
            raise HTTPException(400, str(e))
        clips.hub.add_log('privacy', f'Chủ quán xem bản gốc không che mặt ({clips.hub._label(a)})',
                          a['table'], a['camera'], aid)
        return v

    @r.post('/api/clips/{cid}/keep')
    async def keep_clip(cid: str, x_owner_pin: str | None = Header(default=None)):
        need_pin(x_owner_pin)
        try:
            clips.keep(cid)
        except KeyError:
            raise HTTPException(404, 'clip chưa sẵn sàng')
        clips.hub.add_log('privacy', f'Chủ quán giữ clip {cid} làm bằng chứng')
        return clips.view(clips.get(cid))

    return r
