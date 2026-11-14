"""Bản demo tự chạy (DEMO_FEED=1): phát lần lượt các clip đã che mặt làm hình camera, tạo việc đúng lúc trong
clip như camera thật đã báo, và cho nhân viên ảo nhận rồi làm xong việc. Người xem mở trang là thấy quán
đang hoạt động mà không cần máy camera hay điện thoại.

- Web nhận clip đang phát qua trường `demo` của camera ({file, started_at, duration_ms}) và tự phát video.
- Việc giao cho nhân viên đang mở app thật (điện thoại người xem) thì để người đó tự bấm, không làm thay.
- Có camera thật gửi hình thì tạm dừng.
"""
import asyncio
import json
import random
import sqlite3
from pathlib import Path

from .hub import CLOSED, TASK_KINDS, now_ms

CAM = 'cam1'
CLIP_MS = 16000
EXTRA_STAFF = [dict(id='minh', name='Minh', role='serve'), dict(id='tu', name='Tú', role='clean')]
EDGE = {'call': 'goi_phuc_vu', 'new_guest': 'khach_moi', 'needs_clearing': 'can_don'}


def _events(data: Path, index):
    """Việc camera đã báo trong từng clip (đọc từ lịch sử demo): {file: (giây trong clip, loại, bàn)}."""
    f = data / 'timeline.db'
    if not f.exists():
        return {}
    c = sqlite3.connect(f)
    try:
        rows = c.execute("select ts, `table`, data from timeline where kind='alert_created'").fetchall()
    except sqlite3.Error:
        return {}
    finally:
        c.close()
    out = {}
    for v in index:
        t0, t1 = v['t_from'] / 1000, v['t_to'] / 1000
        for ts, table, d in rows:
            kind = json.loads(d or '{}').get('alert_kind')
            if t0 <= ts <= t1 and kind in EDGE:
                out[v['file']] = (max(2.0, min(12.0, ts - t0)), kind, table)
                break
    return out


def playlist(data: Path):
    """Danh sách phát: mỗi clip khách gọi kèm một clip khách mới và hai clip thường, để hai lần gọi cùng bàn
    cách nhau hơn một phút (máy chủ gộp lần gọi lại trong một phút sau khi xong)."""
    d = data / 'video_demo'
    try:
        index = [x for x in json.loads((d / 'index.json').read_text(encoding='utf-8'))
                 if x['camera'] == CAM and (d / x['file']).exists()]
    except (OSError, ValueError):
        return []
    ev = _events(data, index)
    calls = [x['file'] for x in index if ev.get(x['file'], (0, ''))[1] == 'call']
    guests = [x['file'] for x in index if ev.get(x['file'], (0, ''))[1] == 'new_guest']
    plain = [x['file'] for x in index if x['file'] not in ev]
    if not calls:      # lịch sử không khớp clip: vẫn phát, tạo việc giữa clip
        files = [x['file'] for x in index]
        return [dict(file=f, event=(7.0, 'call' if i % 4 == 0 else 'new_guest' if i % 4 == 1 else None, '09'))
                for i, f in enumerate(files)]
    fill = plain or guests
    out = []
    for i, f in enumerate(calls):
        out.append(dict(file=f, event=ev[f]))
        if guests:
            g = guests[i % len(guests)]
            out.append(dict(file=g, event=ev[g]))
        for k in range(2):
            out.append(dict(file=fill[(2 * i + k) % len(fill)], event=None, clear=k == 1))
    return out


class PhatDemo:
    def __init__(self, hub, data: Path):
        self.hub = hub
        self.data = Path(data)
        self.list = playlist(self.data)
        self.plan = {}       # alert id -> [(lúc làm, việc)]
        self.sim = set()     # nhân viên ảo đang "mở app"

    def _staff_ready(self):
        ids = {s['id'] for s in self.hub.staff}
        add = [s for s in EXTRA_STAFF if s['id'] not in ids]
        if len(self.hub.staff) < 3 and add:
            self.hub.set_staff([*self.hub.staff, *add[:3 - len(self.hub.staff)]])
        for s in self.hub.staff:
            if s['role'] in ('serve', 'clean') and s['id'] not in self.sim:
                self.sim.add(s['id'])
                self.hub.staff_online(s['id'], +1)

    def _real_camera(self):
        return any(self.hub.camera_live(c) for c in self.hub.cameras)

    def _tables(self, items):
        try:
            self.hub.edge_tables(CAM, [dict(id=t, state=s, people=p) for t, s, p in items])
        except Exception as e:
            print('demo: bàn lỗi', e)

    def _event(self, kind, table):
        try:
            self.hub.edge_event(dict(kind=kind, camera=CAM, table=table))
        except Exception as e:
            print('demo: sự kiện lỗi', e)

    def _show(self, item):
        c = self.hub._camera(CAM)
        c['demo'] = dict(file=item['file'], url=f"/api/demo/clip/{item['file']}", started_at=now_ms(),
                         duration_ms=CLIP_MS)
        c['online'] = True
        c['frame_w'], c['frame_h'] = 960, 540
        self.hub.publish('camera', c)

    def _hide(self):
        c = self.hub.cameras.get(CAM)
        if c and c.pop('demo', None) is not None:
            self.hub.publish('camera', c)

    def _handle(self):
        """Nhân viên ảo: nhận việc sau vài giây, rồi tới bàn (camera đóng việc) hoặc bấm xong."""
        t = now_ms()
        for a in list(self.hub.alerts.values()):
            if a['status'] in CLOSED or a['kind'] not in TASK_KINDS or a['id'] in self.plan:
                continue
            sid = a['assigned_to']
            if not sid or sid not in self.sim or self.hub.online[sid] > 1:
                continue    # chưa ai được giao, hoặc người đó đang mở app thật
            ack = t + random.randint(3000, 6000)
            fin = ack + random.randint(5000, 9000)
            last = ('cleared' if a['kind'] == 'needs_clearing' else
                    'arrive' if a['table'] and random.random() < 0.6 else 'done')
            self.plan[a['id']] = [(ack, 'ack', sid), (fin, last, sid)]
        for aid, steps in list(self.plan.items()):
            a = self.hub.alerts.get(aid)
            if a is None or a['status'] in CLOSED:
                del self.plan[aid]
                continue
            while steps and steps[0][0] <= t:
                _, what, sid = steps.pop(0)
                try:
                    if what == 'ack':
                        self.hub.ack(aid, sid)
                    elif what == 'arrive':
                        self._event('nv_den', a['table'])
                    elif what == 'cleared':
                        self._event('da_don', a['table'])
                        self._tables([(a['table'], 'trong', 0)])
                    else:
                        self.hub.done(aid, sid)
                except Exception as e:
                    print('demo: nhân viên ảo lỗi', e)

    async def run(self):
        if not self.list:
            print('demo: không có clip trong video_demo, tắt phát demo')
            return
        await asyncio.sleep(2)
        self._staff_ready()
        self._tables([('09', 'co_khach', 3), ('B1', 'co_khach', 2), ('B2', 'trong', 0)])
        i = 0
        while True:
            try:
                if self._real_camera():
                    self._hide()
                    await asyncio.sleep(5)
                    continue
                item = self.list[i % len(self.list)]
                i += 1
                self._show(item)
                start = now_ms()
                ev = item.get('event')
                fired = not (ev and ev[1])
                if item.get('clear'):
                    self._tables([('B2', 'co_khach', 2)])
                cleared = not item.get('clear')
                while now_ms() - start < CLIP_MS:
                    el = (now_ms() - start) / 1000
                    if not fired and el >= ev[0]:
                        fired = True
                        if ev[1] == 'new_guest':
                            self._tables([(ev[2] or '09', 'co_khach', random.randint(2, 4))])
                        self._event(EDGE[ev[1]], ev[2])
                    if not cleared and el >= 9:
                        cleared = True
                        self._tables([('B2', 'can_don', 0)])
                        self._event('can_don', 'B2')
                    self._handle()
                    await asyncio.sleep(0.5)
            except asyncio.CancelledError:
                raise
            except Exception as e:     # không để vòng phát demo chết
                print('demo lỗi:', e)
                await asyncio.sleep(2)
