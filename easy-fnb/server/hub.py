"""Trạng thái của cả hệ thống và luật điều phối việc cho nhân viên.

Mọi thay đổi chạy trong vòng lặp asyncio của server (một luồng), nên không cần khoá.
Mỗi thay đổi được phát cho mọi trình duyệt đang nghe /api/stream.
"""
import asyncio
import uuid
import json
import statistics
import time
from collections import Counter, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import an_ninh as sec
from .gemini import decide
from .giai_doan import GiaiDoan
from .hoi_ban import HoiBan
from .timeline import Ghi, Timeline

VN = timezone(timedelta(hours=7))

EDGE_KIND = {'goi_phuc_vu': 'call', 'can_don': 'needs_clearing', 'khach_moi': 'new_guest',
             'khach_roi': 'guest_left', 'da_don': 'cleared', 'nv_den': 'staff_arrived',
             'nhin_quanh': 'looking', **sec.EDGE_KIND}
LOOKING_SURE = 0.9      # camera chấm dưới mức này thì hỏi thêm Gemini Decision (nếu bật) trước khi nhắc
TASK_KINDS = ('call', 'needs_clearing', 'new_guest')
KIND_VI = {'call': 'gọi phục vụ', 'needs_clearing': 'cần dọn', 'new_guest': 'có khách mới',
           'guest_left': 'khách đã rời', 'cleared': 'đã dọn xong', 'staff_arrived': 'nhân viên tới bàn',
           'looking': 'có khách nhìn quanh, có thể đang cần hỗ trợ', **sec.KIND_VI}
ROLES = {'call': ['serve', 'clean'], 'needs_clearing': ['clean', 'serve'], 'new_guest': ['serve', 'clean'],
         **{k: [] for k in sec.SEC_KINDS}}     # an ninh không giao theo vai trò: xem sec.recipients
PRIORITY = {'call': 1, 'needs_clearing': 2, 'new_guest': 2}
TABLE_STATE = {'trong': 'empty', 'co_khach': 'occupied', 'can_don': 'needs_clearing', None: 'unknown'}
CLOSED = ('done', 'cancelled')

DEFAULT_STAFF = [
    dict(id='lan', name='Lan', role='serve'),
    dict(id='minh', name='Minh', role='serve'),
    dict(id='tu', name='Tú', role='clean'),
]
DEFAULT_SETTINGS = dict(verify_kinds=['call', 'needs_clearing'], hold_until_verified=['needs_clearing'],
                        escalate_s=0, dedup_s=20, evidence_wait_s=2.5, auto_close_s=90,
                        # giai đoạn bữa ăn của bàn (server/giai_doan.py), đều tính bằng giây, 0 = tắt:
                        # nhịp nhờ AI xem ảnh bàn; nhắc khi khách ngồi mà chưa ai tới, đã có người tới mà chưa
                        # có món, ăn xong mà còn ngồi chờ
                        table_check_s=60, wait_greet_s=180, wait_food_s=900, wait_bill_s=600,
                        **sec.DEFAULTS)      # an ninh: công tắc, giờ mở cửa, "Trông quán", che mặt (server/an_ninh.py)
STAGE_SETTING_KEYS = ('table_check_s', 'wait_greet_s', 'wait_food_s', 'wait_bill_s')
SETTING_KEYS = ('verify_kinds', 'hold_until_verified', 'escalate_s', 'dedup_s', 'evidence_wait_s', 'auto_close_s',
                *STAGE_SETTING_KEYS, *sec.SETTING_KEYS)
CALL_QUIET_S = 60              # bàn vừa xong việc gọi: bấy nhiêu giây sau không tạo việc gọi mới
OFFLINE_GRACE_S = 15           # rớt kết nối ngắn hơn mức này không tính là ra ca
VERIFY_TIMEOUT_S = 2.5          # LLM chậm hơn thế thì cảnh báo thành "Chưa xác minh" (kie.ai cần ~20 s)


def unverified_vi(path, ten='Gemini'):
    """Câu giải thích vì sao chưa xác minh được, theo tên nhà cung cấp LLM đang dùng."""
    return {'uncertain': f'{ten} không chắc', 'poor_image': 'ảnh kém',
            'inconsistent': 'trả lời không khớp', 'belongings': 'còn đồ cá nhân, có thể khách ra ngoài tạm',
            'timeout': f'{ten} quá hạn', 'error': f'{ten} lỗi',
            'breaker_open': f'tạm ngừng gọi {ten} sau nhiều lỗi liên tiếp',
            'no_image': 'không có ảnh để kiểm tra'}.get(path, path)


# Gói ảnh xác minh camera gửi sau sự kiện (POST /api/edge/evidence): vai trò trên URL -> vai trò gửi LLM
EVIDENCE_ROLES = {'strip': 'strip', 'overview': 'overview', 'ref': 'clean_ref', 'person': 'person'}
EARLY_EVIDENCE_S = 30           # gói ảnh tới trước sự kiện (hiếm): giữ chờ tối đa chừng này giây


def clean_items(items):
    """[{name, count}] đồ còn trên bàn (tiếng Việt). None nếu camera không gửi."""
    if items is None:
        return None
    if not isinstance(items, list):
        raise ValueError('items phải là danh sách {name, count}')
    out = []
    for it in items[:12]:
        name = str(it.get('name') or '').strip()[:40] if isinstance(it, dict) else ''
        if name:
            out.append(dict(name=name, count=max(1, int(it.get('count') or 1))))
    return out


class CircuitBreaker:
    """Sau `fails` lỗi liên tiếp (lỗi hoặc quá hạn) thì ngừng gọi trong `cooldown_s`, rồi cho thử đúng một lần."""

    def __init__(self, fails=3, cooldown_s=60.0, clock=time.monotonic):
        self.fails, self.cooldown_s, self.clock = fails, cooldown_s, clock
        self.n, self.opened_at, self.trial = 0, None, False

    @property
    def state(self):
        if self.opened_at is None:
            return 'closed'
        return 'half_open' if self.clock() - self.opened_at >= self.cooldown_s else 'open'

    def allow(self):
        st = self.state
        if st == 'half_open' and not self.trial:
            self.trial = True
            return True
        return st == 'closed'

    def success(self):
        self.n, self.opened_at, self.trial = 0, None, False

    def failure(self):
        self.n += 1
        if self.trial or self.n >= self.fails:
            self.opened_at, self.trial = self.clock(), False


def now_ms():
    return int(time.time() * 1000)


def clock(ms):
    return datetime.fromtimestamp(ms / 1000, VN).strftime('%H:%M:%S')


def where(table, camera):
    return f'Bàn {table}' if table else 'Một khách chưa rõ bàn'


def where_l(table, camera):
    return f'bàn {table}' if table else 'một khách chưa rõ bàn'


class Hub:
    def __init__(self, data_dir: Path, gemini, clock=time.monotonic, verify_timeout_s=VERIFY_TIMEOUT_S,
                 defaults=None):
        self.data = Path(data_dir)
        (self.data / 'crops').mkdir(parents=True, exist_ok=True)
        (self.data / 'evidence').mkdir(parents=True, exist_ok=True)
        (self.data / 'staff').mkdir(parents=True, exist_ok=True)
        self.verify_timeout_s = verify_timeout_s
        self.gemini = gemini
        self.settings = dict(DEFAULT_SETTINGS, **(defaults or {}))
        self.staff = [dict(s) for s in DEFAULT_STAFF]
        self.zones = {}      # camera -> CameraZones
        self._load_config()
        self.cameras = {}    # id -> Camera
        self.frames = {}     # id -> {'live': bytes, 'raw': bytes}
        self._cam_pub = {}   # id -> lúc phát sự kiện camera gần nhất
        self.tables = {}     # "cam/table" -> TableState
        self.alerts = {}     # id -> Alert (giữ cả ca, theo thứ tự tạo)
        self.crops = {}      # alert id -> jpeg bytes
        self.media = {}      # alert id -> [dict(role, jpeg)] gửi cho LLM (dải 2x2, toàn cảnh, bàn sạch)
        self.eids = {}       # eid của sự kiện camera -> alert id (kể cả sự kiện đã gộp vào việc cũ)
        self._evidence_in = {}   # alert id -> asyncio.Event, bật khi gói ảnh xác minh tới
        self._early = {}     # eid -> (lúc nhận, gói ảnh) khi gói ảnh tới trước sự kiện
        self.breaker = CircuitBreaker(3, 60.0, clock)
        self.clock = clock
        self.timeline = Timeline(self.data / 'timeline.db')     # lịch sử lâu dài, không xoá khi bắt đầu ca mới
        self.stages = GiaiDoan(self, CircuitBreaker(3, 60.0, clock))   # giai đoạn bữa ăn của từng bàn
        self.hoi_ban = HoiBan(self, CircuitBreaker(3, 60.0, clock), clock)   # khớp bàn khi camera không chắc
        self.ghi = Ghi(self.timeline, on_served=lambda table: self.stages.on_staff(table, 'staff_done'))
        self.log = deque(maxlen=500)
        self.subs = set()
        self.online = Counter()
        self.attendance = {}  # id nhân viên -> [{in, out}] các lượt vào ca (kết nối app) trong ngày
        self.pending_off = {}  # id nhân viên vừa rớt kết nối -> lúc rớt; quá OFFLINE_GRACE_S mới tính ra ca
        self.last_assigned = {}
        self._seq_alert = 0
        self._seq_log = 0
        self.jobs = {}       # id -> việc nhờ máy camera làm (tìm bàn, chụp nhân viên), chờ máy camera lấy
        self._seq_job = 0

    @property
    def ten(self):
        """Tên nhà cung cấp LLM để hiện trong câu tiếng Việt ('Gemini' hoặc 'kie.ai')."""
        return getattr(self.gemini, 'ten', 'Gemini')

    # ------------------------------------------------------------ cấu hình (lưu ra đĩa)
    def _load_config(self):
        f = self.data / 'config.json'
        if f.exists():
            c = json.loads(f.read_text(encoding='utf-8'))
            self.settings.update(c.get('settings', {}))
            self.staff = c.get('staff') or self.staff
            self.zones = {z['camera']: z for z in c.get('zones', [])}

    def _save_config(self):
        c = dict(settings=self.settings, staff=self.staff, zones=list(self.zones.values()))
        (self.data / 'config.json').write_text(json.dumps(c, ensure_ascii=False, indent=1), encoding='utf-8')

    # ------------------------------------------------------------ phát sự kiện
    def publish(self, event, data):
        self.ghi.publish(event, data)        # vòng đời việc và trạng thái bàn vào dòng thời gian (không ném lỗi)
        for q in list(self.subs):
            try:
                q.put_nowait((event, data))
            except asyncio.QueueFull:
                pass

    def add_log(self, kind, text, table=None, camera=None, alert_id=None):
        self._seq_log += 1
        e = dict(id=self._seq_log, t=now_ms(), kind=kind, table=table, camera=camera, alert_id=alert_id, text=text)
        self.log.appendleft(e)
        self.timeline.add('log', ts=e['t'] / 1000, table=table, camera=camera, alert_id=alert_id, text=text,
                          log_kind=kind)
        self.publish('log', e)
        return e

    def close(self):
        """Ghi nốt dòng thời gian còn trong bộ đệm (gọi khi máy chủ tắt)."""
        self.timeline.close()

    def settings_view(self):
        pub = {k: v for k, v in self.settings.items() if not k.startswith('_')}   # mã PIN không ra ngoài
        return dict(gemini=self.gemini.enabled, provider=self.ten, model=self.gemini.model, **pub,
                    owner_pin_set=bool(self.settings.get(sec.PIN_KEY)), closed=sec.is_closed(self.settings))

    def staff_view(self):
        open_n = Counter(a['assigned_to'] for a in self.alerts.values()
                         if a['assigned_to'] and a['status'] not in CLOSED)
        t = now_ms()
        out = []
        for s in self.staff:
            ses = self.attendance.get(s['id'], [])
            worked = sum(x['out'] - x['in'] for x in ses if x['out']) // 1000  # chỉ các lượt đã ra ca; lượt đang mở tính ở máy khách từ on_since
            on = ses[-1]['in'] if ses and ses[-1]['out'] is None else None
            out.append(dict(s, online=self.online[s['id']] > 0 or s['id'] in self.pending_off, open_tasks=open_n[s['id']], on_since=on,
                            worked_s=worked, first_in=ses[0]['in'] if ses else None))
        return out

    def state(self):
        return dict(server_time=now_ms(), settings=self.settings_view(), cameras=list(self.cameras.values()),
                    zones=list(self.zones.values()), tables=list(self.tables.values()),
                    alerts=[self._public(a) for a in reversed(list(self.alerts.values()))][:300], staff=self.staff_view(),
                    log=list(self.log))

    def _pub_alert(self, a):
        self.publish('alert', a)
        self.publish('staff', self.staff_view())

    # ------------------------------------------------------------ nhân viên
    def staff_online(self, sid, delta):
        if not any(s['id'] == sid for s in self.staff):
            return
        before = self.online[sid] > 0
        self.online[sid] += delta
        if self.online[sid] <= 0:
            del self.online[sid]
        if delta > 0 and sid in self.pending_off:  # kết nối lại trong thời gian chờ: coi như chưa hề rời ca
            del self.pending_off[sid]
            self.publish('staff', self.staff_view())
            return
        if before != (self.online[sid] > 0):
            if self.online[sid] > 0:  # vào ca: điểm danh, nhận các việc chưa ai nhận
                self.attendance.setdefault(sid, []).append({'in': now_ms(), 'out': None})
                self.add_log('system', f'{self._staff_name(sid)} vào ca')
                self.timeline.add('staff_online', staff=sid, text=self._staff_name(sid))
                for a in self.alerts.values():
                    if a['status'] == 'open' and not a['assigned_to']:
                        self._assign(a)
                        self._pub_alert(self._public(a))
            else:  # rớt kết nối: chờ OFFLINE_GRACE_S giây rồi mới tính là ra ca (mạng chập chờn không làm nhảy việc)
                self.pending_off[sid] = now_ms()
            self.publish('staff', self.staff_view())

    def _finish_off(self, sid):
        """Hết thời gian chờ mà vẫn không kết nối lại: ra ca, chuyển việc đang mở cho người còn online."""
        ses = self.attendance.setdefault(sid, [])
        if ses and ses[-1]['out'] is None:
            ses[-1]['out'] = now_ms()
        self.add_log('system', f'{self._staff_name(sid)} ra ca hoặc mất kết nối')
        self.timeline.add('staff_offline', staff=sid, text=self._staff_name(sid))
        for a in self.alerts.values():
            # chỉ chuyển khi có người khác đang online nhận được; không thì giữ nguyên, người cũ có thể kết nối lại
            others = any(self.online[s['id']] > 0 and s['id'] != sid and s['role'] in ROLES[a['kind']]
                         for s in self.staff)
            if a['status'] == 'open' and a['assigned_to'] == sid and others and a['kind'] not in sec.SEC_KINDS:
                if self._assign(a, exclude=sid) is not None:
                    self._pub_alert(self._public(a))
        self.publish('staff', self.staff_view())

    def set_staff(self, items):
        old = {s['id']: s for s in self.staff}
        # ảnh nhận dạng không đi theo danh sách gửi lên: giữ của người còn lại, xoá của người bị bỏ
        self.staff = [dict(id=str(s['id']), name=str(s['name']), role=s['role'],
                           consent=bool(s.get('consent', old.get(str(s['id']), {}).get('consent', False))),
                           photos=old.get(str(s['id']), {}).get('photos', []))
                      for s in items]
        keep = {s['id'] for s in self.staff}
        for sid, s in old.items():
            if sid not in keep:
                for p in s.get('photos', []):
                    self.staff_photo_file(sid, p['id']).unlink(missing_ok=True)
        self._save_config()
        view = self.staff_view()
        self.publish('staff', view)
        return view

    # ------------------------------------------------------------ ảnh nhận dạng nhân viên
    def staff_photo_file(self, sid, pid):
        safe = ''.join(ch for ch in f'{sid}_{pid}' if ch.isalnum() or ch in '_-')
        return self.data / 'staff' / f'{safe}.jpg'

    def add_staff_photo(self, sid, kind, source):
        """Ghi nhận một ảnh vừa lưu (tệp do app.py ghi). kind: face | body; source: upload | camera."""
        s = next(x for x in self.staff if x['id'] == sid)
        pid = kind[0] + uuid.uuid4().hex[:8]
        s.setdefault('photos', []).append(dict(id=pid, kind=kind, source=source))
        return pid

    def staff_photos_changed(self):
        self._save_config()
        view = self.staff_view()
        self.publish('staff', view)
        return view

    def del_staff_photo(self, sid, pid):
        s = next(x for x in self.staff if x['id'] == sid)
        s['photos'] = [p for p in s.get('photos', []) if p['id'] != pid]
        self.staff_photo_file(sid, pid).unlink(missing_ok=True)
        return self.staff_photos_changed()

    def staff_refs(self):
        """Danh sách ảnh để máy camera nhận nhân viên. Chỉ ảnh của người đã đồng ý."""
        refs = [dict(staff=s['id'], name=s['name'], id=p['id'], kind=p['kind'],
                     url=f"/api/staff/{s['id']}/photos/{p['id']}.jpg")
                for s in self.staff if s.get('consent') for p in s.get('photos', [])]
        return dict(version='|'.join(f"{r['staff']}/{r['id']}" for r in refs), refs=refs)

    # ------------------------------------------------------------ việc nhờ máy camera làm
    def new_job(self, camera, kind, **args):
        """Tạo một việc cho máy camera (nó hỏi GET /api/edge/jobs mỗi giây). Trả (id, future kết quả)."""
        self._seq_job += 1
        jid = f'j{self._seq_job}'
        fut = asyncio.get_running_loop().create_future()
        self.jobs[jid] = dict(id=jid, camera=camera, kind=kind, args=args, taken=False, fut=fut)
        return jid, fut

    def take_jobs(self, camera):
        out = []
        for j in self.jobs.values():
            if j['camera'] == camera and not j['taken']:
                j['taken'] = True
                out.append(dict(id=j['id'], kind=j['kind'], **j['args']))
        return out

    def job_result(self, jid, result):
        j = self.jobs.pop(jid, None)
        if j and not j['fut'].done():
            j['fut'].set_result(result)
        return j is not None

    def camera_live(self, cid):
        c = self.cameras.get(cid)
        return bool(c and c['last_frame_at'] and now_ms() - c['last_frame_at'] < 8000)

    def _staff_name(self, sid):
        return next((s['name'] for s in self.staff if s['id'] == sid), sid or 'quản lý')

    def _label(self, a, cap=False):
        """Tên ngắn của một việc trong câu nhật ký ("bàn 3 gọi phục vụ", hoặc câu của cảnh báo an ninh)."""
        if a.get('group') == 'security':
            t = sec.text_vi(a, clock)
            return t if cap else t[0].lower() + t[1:]
        s = f'{where_l(a["table"], a["camera"])} {KIND_VI[a["kind"]]}'
        return s[0].upper() + s[1:] if cap else s

    def _notify(self, a):
        """Cảnh báo an ninh: không giao một người mà báo cho danh sách `notify`. Trả người đầu tiên (hoặc None)."""
        ids = sec.recipients(self.staff, self.online, a['kind'], a.get('_owner_added', False))
        a['notify'] = list(dict.fromkeys((a.get('notify') or []) + ids))
        a['assigned_to'] = None
        return next((s for s in self.staff if a['notify'] and s['id'] == a['notify'][0]), None)

    def _assign(self, a, exclude=None):
        if a['kind'] in sec.SEC_KINDS:
            return self._notify(a)
        open_n = Counter(x['assigned_to'] for x in self.alerts.values()
                         if x['assigned_to'] and x['status'] not in CLOSED and x is not a)
        # người đúng vai trò trước; vai trò phụ chỉ nhận khi người chính đang gánh nhiều hơn 3 việc
        cands = [(rank, s) for rank, role in enumerate(ROLES[a['kind']]) for s in self.staff
                 if s['role'] == role and s['id'] != exclude]
        if not cands:
            if exclude is None:
                a['assigned_to'] = None
            return None
        pool = [c for c in cands if self.online[c[1]['id']] > 0] or cands
        _, s = min(pool, key=lambda c: (open_n[c[1]['id']] + 3 * c[0], self.last_assigned.get(c[1]['id'], 0)))
        a['assigned_to'] = s['id']
        a['_assigned_at'] = now_ms()
        self.last_assigned[s['id']] = now_ms()
        return s

    # ------------------------------------------------------------ camera
    def _camera(self, cid):
        if cid not in self.cameras:
            digits = ''.join(ch for ch in cid if ch.isdigit())
            self.cameras[cid] = dict(id=cid, name=f'Cam {digits}' if digits else cid, online=False,
                                     last_frame_at=None, frame_version=0, has_snapshot=False,
                                     frame_w=None, frame_h=None, fps=None, source=None)
        return self.cameras[cid]

    def edge_frame(self, cid, kind, jpeg, fps=None, source=None, w=None, h=None):
        c = self._camera(cid)
        self.frames.setdefault(cid, {})[kind] = jpeg
        t = now_ms()
        if kind == 'raw':
            c['has_snapshot'] = True
        else:
            c['frame_version'] += 1
            c['last_frame_at'] = t
        c['online'] = True
        if fps is not None:
            c['fps'] = fps
        if source:
            c['source'] = source
        if w and h:
            c['frame_w'], c['frame_h'] = w, h
        if kind == 'raw' or t - self._cam_pub.get(cid, 0) >= 250:
            self._cam_pub[cid] = t
            self.publish('camera', c)

    def set_zones(self, z):
        z = dict(camera=z['camera'], frame_w=int(z['frame_w']), frame_h=int(z['frame_h']),
                 tables=[dict(id=str(t['id']), polygon=[[float(x), float(y)] for x, y in t['polygon']])
                         for t in z['tables']],
                 areas=sec.clean_areas(z.get('areas')))   # quầy, kho, giữ xe, cửa
        for t in z['tables']:
            if not t['id'].strip() or len(t['polygon']) < 3:
                raise ValueError(f"bàn {t['id'] or '(không tên)'} cần tên và ít nhất 3 điểm")
        if len({t['id'] for t in z['tables']}) != len(z['tables']):
            raise ValueError('có hai bàn trùng tên')
        self.zones[z['camera']] = z
        keep = {f"{z['camera']}/{t['id']}" for t in z['tables']}
        for key in [k for k in self.tables if k.startswith(z['camera'] + '/') and k not in keep]:
            del self.tables[key]     # bàn đã bị xoá khỏi vùng vẽ
        self._save_config()
        self.publish('zones', z)
        self.add_log('system', f"Đã lưu {len(z['tables'])} vùng bàn cho {z['camera']}", camera=z['camera'])
        return z

    def get_zones(self, cid):
        z = self.zones.get(cid) or dict(camera=cid, frame_w=0, frame_h=0, tables=[])
        # trạng thái an ninh tính mỗi lần hỏi (giờ đóng cửa thay đổi theo đồng hồ), không lưu vào vùng
        return dict(z, areas=z.get('areas') or [], an_ninh=sec.camera_view(self.settings))

    def edge_tables(self, cid, items):
        self._camera(cid)
        z = self.zones.get(cid)
        known = {t['id'] for t in z['tables']} if z and z.get('frame_w') else None
        for it in items:
            if known is not None and str(it['id']) not in known:
                continue             # gói cũ gửi trước khi vùng bàn trên web bị sửa
            key = f"{cid}/{it['id']}"
            st = TABLE_STATE.get(it.get('state'), 'unknown')
            people = int(it.get('people') or 0)
            dirty = it.get('dirty')
            old = self.tables.get(key)
            if old and old['state'] == st and old['people'] == people and \
                    (dirty is None or old['dirty'] is None or abs(dirty - old['dirty']) < 0.1):
                continue
            tb = dict(id=str(it['id']), camera=cid, state=st, people=people,
                      since=old['since'] if old and old['state'] == st else now_ms(),
                      dirty=None if dirty is None else round(float(dirty), 3))
            self.stages.on_table(tb)     # giai đoạn bữa ăn: điền stage, stage_since vào tb
            self.tables[key] = tb
            self.publish('table', tb)

    # ------------------------------------------------------------ sự kiện từ camera
    def _dedup(self, kind, camera, table, box):
        def same_place(b):   # không có bàn: coi là cùng một khách khi tâm khung người lệch nhau dưới 150 px
            if not box or not b:
                return not box and not b
            return abs((b[0] + b[2]) - (box[0] + box[2])) / 2 < 150
        t = now_ms()
        if kind == 'after_hours':     # cùng camera trong AFTER_HOURS_GAP_S: vẫn là chuyện cũ, không chuông lại
            return next((a for a in reversed(list(self.alerts.values())) if a['kind'] == kind and a['camera'] == camera
                         and (a['status'] not in CLOSED or (a['status'] == 'done' and    # báo nhầm thì không nuốt lần sau
                              t - a['created_at'] <= sec.AFTER_HOURS_GAP_S * 1000))), None)
        if kind == 'restricted':      # cùng vùng (box ở đây là id vùng), việc còn mở hoặc mới trong dedup_s
            return next((a for a in reversed(list(self.alerts.values())) if a['kind'] == kind and a['camera'] == camera
                         and a.get('area') == box and (a['status'] not in CLOSED or
                                                        t - a['created_at'] <= self.settings['dedup_s'] * 1000)), None)
        for a in reversed(list(self.alerts.values())):
            # bàn đã biết thì gộp cả khi hai camera cùng thấy; không có bàn thì chỉ gộp trong cùng camera
            if a['kind'] != kind or (not table and a['camera'] != camera):
                continue
            if a['table'] != table or (not table and not same_place(a['box'])):
                continue
            # việc còn mở thì lần báo lại là cùng một việc (khách vẫn giơ tay): không tạo việc mới, không giao người khác
            recent = t - a['created_at'] <= self.settings['dedup_s'] * 1000
            # khách gọi vừa được xử lý (hoặc báo nhầm): tay còn giơ, model báo chập chờn thì im thêm một lúc,
            # không làm phiền nhân viên lần nữa
            closed_t = a.get('done_at') or a.get('cancelled_at')
            if kind == 'call' and closed_t and t - closed_t <= CALL_QUIET_S * 1000:
                recent = True
            if recent or a['status'] not in CLOSED:
                return a
        return None

    def edge_event(self, ev):
        kind = EDGE_KIND.get(ev['kind'])
        if kind is None:
            raise ValueError(f"kind không hợp lệ: {ev['kind']}")
        cam = ev['camera']
        self._camera(cam)
        table = ev.get('table')
        if kind == 'staff_arrived':
            self.stages.on_staff(table)
            return self.staff_arrived(table, cam)
        if kind == 'looking':   # tín hiệu mềm: chỉ nhắc trên màn hình quản lý, không tạo việc, không đọc loa
            crop = ev.get('crop_jpeg')
            if crop and getattr(self.gemini, 'decision', False) and float(ev.get('score') or 0) < LOOKING_SURE:
                asyncio.get_running_loop().create_task(self._looking_check(table, cam, crop))
            else:
                self._looking(table, cam)
            return None
        if kind in ('guest_left', 'cleared'):
            self.add_log(kind, f'{where(table, cam)} {KIND_VI[kind]}', table, cam)
            if kind == 'guest_left':
                self.stages.on_left(table)
            if kind == 'cleared':
                for a in self.alerts.values():
                    if a['kind'] == 'needs_clearing' and a['table'] == table and a['camera'] == cam \
                            and a['status'] not in CLOSED:
                        self._close(a, 'done', 'camera', 'Camera thấy bàn đã dọn, tự đóng việc')
            return None
        is_sec = kind in sec.SEC_KINDS
        if is_sec and not self.settings.get(sec.SETTING_FLAG[kind]):
            return None                  # tính năng đang tắt trong Cài đặt (camera chưa kịp biết)
        area = str(ev['area']) if is_sec and ev.get('area') else None
        if kind == 'restricted' and not area:
            raise ValueError('vao_khu_cam cần area')
        if kind == 'restricted' and sec.in_delivery(self.settings):
            return None                  # khung giờ giao hàng: không báo
        items = clean_items(ev.get('items'))
        eid = str(ev['eid']) if ev.get('eid') else None
        dup = self._dedup(kind, cam, table, area if kind == 'restricted' else ev.get('box'))
        if dup:
            dup['repeats'] += 1
            dup['_seen'] = now_ms()      # khách vẫn đang gọi: chưa tính giờ hết hạn
            if items is not None:
                dup['items'] = items
            if eid:   # gói ảnh của sự kiện này sẽ gộp vào việc cũ
                self.eids[eid] = dup['id']
                self._take_early(eid, dup)
            self.publish('alert', self._public(dup))
            return dup['id']
        self._seq_alert += 1
        aid = f'a{self._seq_alert}'
        crop = ev.get('crop_jpeg')
        if crop:
            self.crops[aid] = crop
            (self.data / 'crops' / f'{aid}.jpg').write_bytes(crop)
        images = list(ev.get('images') or [])
        if is_sec:   # an ninh: chỉ Gemini Decision có câu hỏi riêng; có thì luôn giữ lại tới khi kiểm tra xong
            check = self.gemini.enabled and getattr(self.gemini, 'decision', False) and bool(crop or eid or images)
            hold = check
        else:
            check = self.gemini.enabled and kind in self.settings['verify_kinds'] and bool(crop or eid or images)
            hold = check and kind in self.settings['hold_until_verified']
        if check:
            self.media[aid] = images or ([{'role': 'crop', 'jpeg': crop}] if crop else [])
        a = dict(id=aid, kind=kind, table=table, camera=cam, created_at=now_ms(), video_t=ev.get('video_t'),
                 box=ev.get('box'), score=ev.get('score'), detail=ev.get('detail') or '',
                 crop_url=f'/api/crops/{aid}.jpg' if crop else None, items=items, evidence=None,
                 status='verifying' if hold else 'open', assigned_to=None, acked_at=None, acked_by=None,
                 done_at=None, done_by=None, cancelled_at=None, cancel_reason=None, escalated=False, repeats=0,
                 verify=dict(state='pending' if check else 'skipped', confidence=None, reason=None, ms=None,
                             model=self.gemini.model if check else None, path=None, verdict=None,
                             image_quality=None, checklist=None, source=None),
                 _eid=eid, _t0=time.monotonic())
        if is_sec:
            ar = sec.area_of(self.zones, cam, area) if area else None
            a.update(group='security', area=area, area_name=ar['name'] if ar else area, notify=[])
            inline = {im['role']: im['jpeg'] for im in images}
            if inline.get('strip') or inline.get('person'):   # ảnh gửi kèm sự kiện: lưu để web xem, không chờ gói ảnh
                self._attach_evidence(a, {f'{r}_jpeg': inline.get(v) for r, v in EVIDENCE_ROLES.items()},
                                      publish=False)
        self.alerts[aid] = a
        if eid:
            self.eids[eid] = aid
        s = None if hold else self._assign(a)
        text = self._label(a, True) if is_sec else f'{where(table, cam)} {KIND_VI[kind]}'
        if hold:
            text += f', đang nhờ {self.ten} kiểm tra'
        elif s:
            text += f', giao cho {s["name"]}'
        self.add_log(kind, text, table, cam, aid)
        if eid:
            self._take_early(eid, a, publish=False)
        self._pub_alert(self._public(a))
        if check:
            asyncio.get_running_loop().create_task(self._verify(aid))
        return aid

    def _looking(self, table, cam, note=''):
        self.add_log('looking', f'{where(table, cam)}: {KIND_VI["looking"]}{note}', table, cam)
        tb = self.tables.get(f'{cam}/{table}')
        if tb:
            tb['looking_at'] = now_ms()
            self.publish('table', tb)

    async def _looking_check(self, table, cam, crop):
        """Camera chưa chắc: hỏi Gemini Decision. Chỉ bỏ khi Gemini khá chắc là không phải; lỗi hay lưng chừng vẫn nhắc."""
        try:
            r = await asyncio.wait_for(self.gemini.verify('looking', crop, table), self.verify_timeout_s)
        except Exception:
            return self._looking(table, cam)
        action = decide('looking', r)[0]
        if action != 'reject':
            self._looking(table, cam, f' ({self.ten} xác nhận)' if action == 'confirm' else '')

    def staff_arrived(self, table, cam):
        """Camera thấy nhân viên đứng ở bàn: đó là lúc khách được phục vụ thật, nên tính thời gian phản hồi
        tới lúc này. Việc gọi và khách mới đóng luôn; việc dọn bàn chỉ ghi "đang dọn", vì phải chờ camera
        thấy bàn sạch mới xong. Camera gửi lại mỗi vài giây khi nhân viên còn đứng đó, nên việc vừa mở
        trong lúc nhân viên đang ở bàn cũng được đóng. Không biết ai tới, nên ghi cho người đang được giao."""
        if not table:
            return None
        t = now_ms()
        closed = []
        for a in list(self.alerts.values()):
            if a['table'] != table or a['status'] in CLOSED or a['kind'] not in TASK_KINDS:
                continue
            if a.get('arrived_at'):
                continue
            a['arrived_at'] = t
            a['arrived_s'] = round((t - a['created_at']) / 1000, 1)
            if not a['acked_at']:
                a['acked_at'], a['acked_by'] = t, a['assigned_to'] or 'camera'
            if a['kind'] == 'needs_clearing':
                a['status'] = 'acked'
                self.add_log('arrived', f'Nhân viên tới dọn {where_l(table, a["camera"])} sau '
                                        f'{a["arrived_s"]:.0f} giây', table, a['camera'], a['id'])
                self._pub_alert(self._public(a))
            else:
                self._close(a, 'done', 'camera', f'Camera thấy nhân viên tới bàn sau {a["arrived_s"]:.0f} giây')
            closed.append(a['id'])
        if not closed:    # không có việc nào để đóng: vẫn ghi một dòng (camera gửi lại mỗi vài giây nên giãn 60 giây)
            seen = self.__dict__.setdefault('_nv_log', {})
            if t - seen.get((cam, table), 0) > 60_000:
                seen[(cam, table)] = t
                self.add_log('arrived', f'Nhân viên tới {where_l(table, cam)}', table, cam)
        return closed[0] if closed else None

    # ------------------------------------------------------------ gói ảnh xác minh (tới sau sự kiện ~1-1.5 s)
    def edge_evidence(self, ev):
        """ev: camera, eid, strip_jpeg, overview_jpeg, ref_jpeg (bytes hoặc None), items. Trả alert id hoặc None
        (gói tới trước sự kiện: giữ lại, gắn khi sự kiện tới)."""
        eid = str(ev['eid'])
        t = time.monotonic()
        for k in [k for k, (t0, _) in self._early.items() if t - t0 > EARLY_EVIDENCE_S]:
            del self._early[k]
        aid = self.eids.get(eid)
        a = self.alerts.get(aid) if aid else None
        if a is None:
            self._early[eid] = (t, ev)
            return None
        self._attach_evidence(a, ev)
        return a['id']

    def _take_early(self, eid, a, publish=True):
        got = self._early.pop(eid, None)
        if got:
            self._attach_evidence(a, got[1], publish)

    def _attach_evidence(self, a, ev, publish=True):
        aid = a['id']
        jpegs = {role: ev.get(f'{role}_jpeg') for role in EVIDENCE_ROLES}
        have = dict(a['evidence'] or {})
        for role, jpeg in jpegs.items():
            if jpeg and not have.get(role):      # việc đã gộp nhiều sự kiện: giữ ảnh đầu tiên, chỉ lấp chỗ trống
                (self.data / 'evidence' / f'{aid}_{role}.jpg').write_bytes(jpeg)
                have[role] = f'/api/alerts/{aid}/evidence/{role}.jpg'
        if have:
            a['evidence'] = {role: have.get(role) for role in EVIDENCE_ROLES if role != 'person' or have.get(role)}
        items = clean_items(ev.get('items'))
        if items is not None:
            a['items'] = items
        if a['verify']['state'] == 'pending' and jpegs['strip'] and not self._evidence_event(aid).is_set():
            self.media[aid] = [dict(role=EVIDENCE_ROLES[r], jpeg=j) for r, j in jpegs.items() if j]
            self._evidence_event(aid).set()
        if publish:
            self.publish('alert', self._public(a))

    def _evidence_event(self, aid):
        return self._evidence_in.setdefault(aid, asyncio.Event())

    def evidence_file(self, aid, role):
        if role not in EVIDENCE_ROLES:
            return None
        f = self.data / 'evidence' / f'{aid}_{role}.jpg'
        a = self.alerts.get(aid)
        return f if a and (a.get('evidence') or {}).get(role) and f.exists() else None

    def _unverified(self, a, path, detail=None):
        """Không đủ căn cứ để rút hay xác nhận: giữ cảnh báo, gắn "Chưa xác minh"; việc đang giữ thì giao luôn."""
        a['verify'].update(state='unverified', path=path, reason=detail or unverified_vi(path, self.ten))
        if a['status'] == 'verifying':
            a['status'] = 'open'
            self._assign(a)
        self.add_log('verify', f'Chưa xác minh {self._label(a)}: '
                               f'{unverified_vi(path, self.ten)}', a['table'], a['camera'], a['id'])
        self._pub_alert(self._public(a))

    async def _verify(self, aid):
        try:
            await self._verify_inner(aid)
        finally:
            self.media.pop(aid, None)
            self._evidence_in.pop(aid, None)

    async def _verify_inner(self, aid):
        a = self.alerts.get(aid)
        if a is None:
            return
        await asyncio.sleep(0)
        if self.breaker.state == 'open':          # không chờ ảnh: báo "Chưa xác minh" ngay
            return self._unverified(a, 'breaker_open')
        # Camera mới (có eid) gửi gói ảnh sau sự kiện ~1-1.5 s: chờ tối đa evidence_wait_s kể từ lúc báo
        evt = self._evidence_event(aid)
        if a.get('_eid') and not evt.is_set():
            left = float(self.settings.get('evidence_wait_s', 2.5)) - (time.monotonic() - a['_t0'])
            if left > 0:
                try:
                    await asyncio.wait_for(evt.wait(), left)
                except asyncio.TimeoutError:
                    pass
        images = self.media.get(aid) or []
        if not images:
            return self._unverified(a, 'no_image')
        if not self.breaker.allow():
            return self._unverified(a, 'breaker_open')
        a['verify']['source'] = 'evidence' if any(im['role'] == 'strip' for im in images) else 'crop'
        t = self.verify_timeout_s
        try:
            r = await asyncio.wait_for(self.gemini.verify(a['kind'], images, a['table']), t)
        except asyncio.TimeoutError:
            self.breaker.failure()
            return self._unverified(a, 'timeout', f'{self.ten} quá {t:g} giây')
        except Exception as e:  # lỗi mạng, lỗi API, JSON hỏng: không chặn việc
            self.breaker.failure()
            return self._unverified(a, 'error', f'{self.ten} lỗi: {str(e)[:120]}')
        self.breaker.success()
        action, path = decide(a['kind'], r)
        a['verify'].update(verdict=r.get('verdict'), image_quality=r.get('image_quality'),
                           checklist=r.get('checklist'), reason=r.get('reason'), ms=r.get('ms'), path=path)
        if r.get('probs'):                        # Gemini Decision: giữ xác suất của từng câu hỏi và tên model
            a['verify'].update(probs=r['probs'], model=r.get('model') or a['verify']['model'])
        if action == 'unverified':
            if path == 'belongings' and a['status'] in ('verifying', 'open') and self.stages.hold(a['table']):
                # khách để đồ lại (đi vệ sinh, nghe máy): chưa phải khách về, không giao việc dọn
                a['verify'].update(state='unverified', reason='Còn đồ cá nhân ở bàn, khách có thể quay lại')
                self._close(a, 'cancelled', 'gemini', 'khách tạm rời, còn để đồ ở bàn', publish=False)
                return self._pub_alert(self._public(a))
            return self._unverified(a, path, r.get('reason'))
        if action == 'confirm':
            a['verify']['state'] = 'confirmed'
            extra = ''
            if a['status'] == 'verifying':
                a['status'] = 'open'
                s = self._assign(a)
                extra = f', giao cho {s["name"]}' if s else ''
            self.add_log('verify', f'{self.ten} xác nhận: {self._label(a)}{extra}',
                         a['table'], a['camera'], aid)
        else:
            a['verify']['state'] = 'rejected'
            if a['status'] in ('verifying', 'open'):
                self._close(a, 'cancelled', 'gemini', f'{self.ten}: {r.get("reason") or "báo nhầm"}', publish=False)
            else:
                self.add_log('verify', f'{self.ten} cho là báo nhầm ({r.get("reason")}), nhưng nhân viên đã nhận việc',
                             a['table'], a['camera'], aid)
        self._pub_alert(self._public(a))

    # ------------------------------------------------------------ thao tác của nhân viên, quản lý
    def _public(self, a):
        return {k: v for k, v in a.items() if not k.startswith('_')}

    def get_alert(self, aid):
        a = self.alerts.get(aid)
        if a is None:
            raise KeyError(aid)
        return a

    def _close(self, a, status, by, reason=None, publish=True):
        t = now_ms()
        a['status'] = status
        name = self._staff_name(by) if by not in ('camera', 'gemini', 'manager') else \
            {'camera': 'camera', 'gemini': self.ten, 'manager': 'quản lý'}[by]
        if status == 'done':
            a['done_at'], a['done_by'] = t, by
            text = (f'{self._label(a, True)}: {name} đã biết' if a.get('group') else
                    f'{where(a["table"], a["camera"])} {KIND_VI[a["kind"]]}: {reason or "camera tự đóng việc"}'
                    if by == 'camera'
                    else f'{where(a["table"], a["camera"])}: {name} đã xong ({KIND_VI[a["kind"]]})')
            a['close_reason'] = reason
            self.add_log('done', text, a['table'], a['camera'], a['id'])
        else:
            a['cancelled_at'], a['cancel_reason'] = t, reason or 'báo nhầm'
            self.add_log('cancel', f'Huỷ {"cảnh báo" if a.get("group") else "việc"} {self._label(a)}: '
                                   f'{a["cancel_reason"]} ({name})', a['table'], a['camera'], a['id'])
        if publish:
            self._pub_alert(self._public(a))
        return a

    def ack(self, aid, staff):
        a = self.get_alert(aid)
        if a['status'] in CLOSED:
            return self._public(a)
        a['status'], a['acked_at'], a['acked_by'] = 'acked', now_ms(), staff
        a['assigned_to'] = staff
        secs = (a['acked_at'] - a['created_at']) / 1000
        self.add_log('ack', f'{self._staff_name(staff)} đang tới {where_l(a["table"], a["camera"])} '
                            f'(sau {secs:.0f} giây)', a['table'], a['camera'], aid)
        self._pub_alert(self._public(a))
        return self._public(a)

    def done(self, aid, staff):
        a = self.get_alert(aid)
        if a['status'] not in CLOSED:
            if not a['acked_at'] and any(x['id'] == staff for x in self.staff):
                a['acked_at'], a['acked_by'] = now_ms(), staff   # quản lý bấm xong thì không tính vào thời gian phản hồi
            self._close(a, 'done', staff)
        return self._public(a)

    def cancel(self, aid, by, reason):
        a = self.get_alert(aid)
        if a['status'] not in CLOSED:
            self._close(a, 'cancelled', by, reason)
        return self._public(a)

    def assign_to(self, aid, staff):
        a = self.get_alert(aid)
        if a['status'] not in CLOSED:
            a['assigned_to'], a['_assigned_at'] = staff, now_ms()
            self.add_log('system', f'Quản lý giao {where_l(a["table"], a["camera"])} cho '
                                   f'{self._staff_name(staff)}', a['table'], a['camera'], aid)
            self._pub_alert(self._public(a))
        return self._public(a)

    def manual(self, kind, table, camera):
        if kind not in TASK_KINDS:
            raise ValueError('kind')
        self._seq_alert += 1
        aid = f'a{self._seq_alert}'
        a = dict(id=aid, kind=kind, table=table, camera=camera or 'cam1', created_at=now_ms(), video_t=None,
                 box=None, score=None, detail='Quản lý tạo', crop_url=None, items=None, evidence=None,
                 status='open', assigned_to=None,
                 acked_at=None, acked_by=None, done_at=None, done_by=None, cancelled_at=None, cancel_reason=None,
                 escalated=False, repeats=0, verify=dict(state='skipped', confidence=None, reason=None, ms=None,
                                                         model=None, path=None, verdict=None, image_quality=None,
                                                         checklist=None, source=None))
        self.alerts[aid] = a
        s = self._assign(a)
        self.add_log(kind, f'Quản lý tạo việc: {where_l(table, a["camera"])} {KIND_VI[kind]}'
                     + (f', giao cho {s["name"]}' if s else ''), table, a['camera'], aid)
        self._pub_alert(self._public(a))
        return self._public(a)

    def update_settings(self, patch, pin=None):
        sec.check_settings(patch)
        if 'blur_faces' in patch and patch['blur_faces'] != self.settings.get('blur_faces', True):
            if not self.settings.get(sec.PIN_KEY):
                raise PermissionError('Hãy đặt mã PIN chủ quán trước khi đổi che mặt')
            if not sec.pin_ok(self.settings.get(sec.PIN_KEY), pin):
                raise PermissionError('Sai mã PIN')
        for k in STAGE_SETTING_KEYS:     # các mốc giây của giai đoạn bàn: số từ 0 (tắt) tới một ngày
            v = patch.get(k, 0)
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not 0 <= v <= 86400:
                raise ValueError(f'{k} phải là số giây từ 0 tới 86400')
        for k in SETTING_KEYS:
            if k in patch:
                self.settings[k] = patch[k]
        self._save_config()
        v = self.settings_view()
        self.publish('settings', v)
        if 'guard_mode' in patch:
            self.add_log('system', ('Bật' if self.settings['guard_mode'] else 'Tắt') + ' trông quán')
        if 'blur_faces' in patch:
            self.add_log('system', ('Bật' if self.settings['blur_faces'] else 'Tắt') + ' che mặt trong video')
        return v

    # ------------------------------------------------------------ mã PIN chủ quán
    def set_pin(self, pin, old=None):
        if not sec.valid_pin(pin):
            raise ValueError('Mã PIN gồm 4 tới 8 chữ số')
        if self.settings.get(sec.PIN_KEY) and not sec.pin_ok(self.settings[sec.PIN_KEY], old):
            raise PermissionError('Mã PIN cũ không đúng')
        self.settings[sec.PIN_KEY] = sec.hash_pin(pin)
        self._save_config()
        self.add_log('system', 'Đã đặt mã PIN chủ quán')
        self.publish('settings', self.settings_view())

    def pin_ok(self, pin):
        return sec.pin_ok(self.settings.get(sec.PIN_KEY), pin)

    def reset(self):
        self.alerts.clear()
        self.crops.clear()
        self.media.clear()
        self.eids.clear()
        self._early.clear()
        self.tables.clear()
        self.log.clear()
        self.stages.reset()
        self.ghi.reset()
        self.timeline.add('shift_reset', text='Bắt đầu ca mới')   # dòng thời gian không xoá, chỉ đánh dấu mốc
        # chấm công cũng là của ca: ai đang mở app thì tính lại từ lúc bắt đầu ca mới, ai không mở thì xoá
        t = now_ms()
        self.attendance = {sid: [{'in': t, 'out': None}] for sid in self.attendance
                           if self.online.get(sid, 0) > 0 or sid in self.pending_off}
        for f in [*(self.data / 'crops').glob('*.jpg'), *(self.data / 'evidence').glob('*.jpg')]:
            f.unlink()
        self.publish('reset', {})
        self.publish('staff', self.staff_view())
        self.add_log('system', 'Đã xoá dữ liệu ca, bắt đầu ca mới')

    # ------------------------------------------------------------ vòng lặp nền
    async def tick_forever(self):
        while True:
            await asyncio.sleep(1)
            try:
                self.tick()
            except Exception as e:  # không để vòng lặp nền chết
                print('tick lỗi:', e)

    def tick(self):
        self.stages.tick()               # giai đoạn bàn và lời nhắc (tự nuốt lỗi, không ảnh hưởng phần dưới)
        self.timeline.flush()
        t = now_ms()
        for sid in [k for k, t0 in self.pending_off.items() if t - t0 >= OFFLINE_GRACE_S * 1000]:
            del self.pending_off[sid]
            self._finish_off(sid)
        for c in self.cameras.values():
            on = c['last_frame_at'] is not None and t - c['last_frame_at'] < 5000
            if on != c['online']:
                c['online'] = on
                self.publish('camera', c)
        esc = self.settings['escalate_s'] * 1000
        for a in self.alerts.values():
            if a['status'] != 'open':
                continue
            if a['kind'] in sec.SEC_KINDS:     # an ninh: không tự đóng, không chuyển người; khu cấm thì báo thêm chủ quán
                if a['kind'] == 'restricted' and not a.get('_owner_added') and \
                        t - a['created_at'] >= sec.RESTRICTED_OWNER_S * 1000:
                    a['_owner_added'] = True
                    before = list(a.get('notify') or [])
                    self._notify(a)
                    if a['notify'] != before:
                        self.add_log('escalate', f'Chưa ai bấm "Đã biết": báo thêm chủ quán ({self._label(a)})',
                                     None, a['camera'], a['id'])
                        self._pub_alert(self._public(a))
                continue
            if not a['assigned_to']:
                if self._assign(a):
                    self._pub_alert(self._public(a))
                continue
            # nhân viên không bấm nhận: việc gọi và khách mới tự đóng sau auto_close_s (dọn bàn đóng khi camera thấy bàn sạch)
            ac = self.settings.get('auto_close_s', 0) * 1000
            # tính từ lần cuối camera còn thấy khách gọi; đóng là "không ai tới" (báo cáo ca tính là bỏ lỡ)
            if ac and a['kind'] != 'needs_clearing' and t - a.get('_seen', a['created_at']) >= ac:
                self._close(a, 'done', 'camera', 'không thấy nhân viên tới, khách đã thôi gọi')
                continue
            # chuyển người tối đa 2 lần, để việc không bị đẩy qua lại mãi khi quán vắng người (0 = tắt)
            if esc and a.get('_esc_n', 0) < 2 and t - a.get('_assigned_at', a['created_at']) >= esc:
                old = a['assigned_to']
                s = self._assign(a, exclude=old)
                a['escalated'] = True
                a['_esc_n'] = a.get('_esc_n', 0) + 1
                a['_assigned_at'] = t
                to = f', chuyển cho {s["name"]}' if s else ', nhắc lại'
                self.add_log('escalate', f'Chưa ai nhận {where_l(a["table"], a["camera"])} '
                                         f'sau {self.settings["escalate_s"]} giây{to}', a['table'], a['camera'], a['id'])
                self._pub_alert(self._public(a))

    # ------------------------------------------------------------ báo cáo
    # Mốc xếp loại tốc độ nhận việc: tới FAST_S giây là nhanh, tới SLOW_S là hơi chậm, hơn nữa là chậm.
    # Màn hình hiện chữ (nhanh, chậm) thay cho số giây, nên mốc đặt ở một chỗ duy nhất là đây.
    FAST_S, SLOW_S = 30, 60
    # Độ dài một cột của biểu đồ theo thời gian (giây): chọn cột nhỏ nhất mà cả ca vẫn gọn trong 12 cột.
    BUCKETS_S = (60, 120, 300, 600, 900, 1800, 3600, 7200)

    def _speed(self, secs):
        return dict(fast=sum(1 for x in secs if x <= self.FAST_S),
                    ok=sum(1 for x in secs if self.FAST_S < x <= self.SLOW_S),
                    slow=sum(1 for x in secs if x > self.SLOW_S))

    def report(self):
        al = [a for a in self.alerts.values() if a['kind'] in TASK_KINDS]   # cảnh báo an ninh không vào số liệu ca
        t = now_ms()

        def stats(xs):
            xs = sorted(xs)
            if not xs:
                return dict(mean=None, median=None, p90=None)
            return dict(mean=round(statistics.fmean(xs), 1), median=round(statistics.median(xs), 1),
                        p90=round(xs[min(len(xs) - 1, int(0.9 * len(xs)))], 1))

        resp = [(a['acked_at'] - a['created_at']) / 1000 for a in al if a['acked_at']]
        done = [(a['done_at'] - a['created_at']) / 1000 for a in al if a['done_at']]
        per_staff = []
        for s in self.staff:
            mine = [a for a in al if a['acked_by'] == s['id']]
            r = [(a['acked_at'] - a['created_at']) / 1000 for a in mine]
            per_staff.append(dict(id=s['id'], name=s['name'], acked=len(mine),
                                  done=sum(1 for a in al if a['done_by'] == s['id'] or (
                                      # camera thấy người đã nhận việc tới bàn / bàn đã dọn: việc đó là của người ấy
                                      a['done_by'] == 'camera' and a['acked_by'] == s['id']
                                      and not (a.get('close_reason') or '').startswith('Tự đóng'))),
                                  mean_response_s=round(statistics.fmean(r), 1) if r else None,
                                  # người này nhận những loại việc gì
                                  kinds={k: sum(1 for a in mine if a['kind'] == k) for k in TASK_KINDS},
                                  **self._speed(r)))
        tables = sorted({a['table'] for a in al if a['table']})
        per_table = [dict(table=tb, calls=sum(1 for a in al if a['table'] == tb and a['kind'] == 'call'),
                          clearings=sum(1 for a in al if a['table'] == tb and a['kind'] == 'needs_clearing'),
                          guests=sum(1 for a in al if a['table'] == tb and a['kind'] == 'new_guest'))
                     for tb in tables]
        st = stats(resp)

        def bo_lo(a):
            return (a['status'] == 'done' and a['kind'] != 'needs_clearing' and not a.get('arrived_at')
                    and a['done_by'] == 'camera')

        def toc_do(xs):
            # tốc độ của một nhóm việc: việc đã có người nhận xếp theo mốc, cộng số việc không ai tới
            return dict(**self._speed([(a['acked_at'] - a['created_at']) / 1000 for a in xs if a['acked_at']]),
                        missed=sum(1 for a in xs if bo_lo(a)))

        missed = sum(1 for a in al if bo_lo(a))
        for row in per_table:
            row.update(toc_do([a for a in al if a['table'] == row['table']]))
        # diễn biến ca theo từng khoảng thời gian: bao nhiêu việc mỗi loại, phục vụ nhanh hay chậm
        song = [a for a in al if a['status'] != 'cancelled']
        timeline = None
        if song:
            t0, t1 = min(a['created_at'] for a in song) // 1000, max(t // 1000, 1)
            step = next((b for b in self.BUCKETS_S if (t1 - t0) / b < 12), self.BUCKETS_S[-1])
            t0 -= t0 % step                                # mốc tròn: 12:00, 12:05, ...
            cot = [[] for _ in range(max(6, (t1 - t0) // step + 1))]
            for a in song:
                cot[(a['created_at'] // 1000 - t0) // step].append(a)
            timeline = dict(step_s=step, points=[
                dict(t=(t0 + i * step) * 1000, **{k: sum(1 for a in xs if a['kind'] == k) for k in TASK_KINDS},
                     **toc_do(xs)) for i, xs in enumerate(cot)])
        speed = dict(**self._speed(resp), missed=missed, fast_s=self.FAST_S, slow_s=self.SLOW_S)
        return {'from': min((a['created_at'] for a in al), default=t), 'to': t, **dict(
                    counts={k: sum(1 for a in al if a['kind'] == k) for k in TASK_KINDS},
                    cancelled=sum(1 for a in al if a['status'] == 'cancelled'),
                    rejected_by_gemini=sum(1 for a in al if a['verify']['state'] == 'rejected'),
                    unverified=sum(1 for a in al if a['verify']['state'] == 'unverified'),
                    response_s=st, speed=speed, done_s={k: v for k, v in stats(done).items() if k != 'p90'},
                    escalated=sum(1 for a in al if a['escalated']), per_staff=per_staff, per_table=per_table,
                    timeline=timeline,
                    # thời gian phản hồi do camera đo (nhân viên có mặt ở bàn), không cần ai bấm nút
                    arrived=sum(1 for a in al if a.get('arrived_at')),
                    no_arrival=missed)}

    def log_text(self, limit=400):
        """Nhật ký dạng chữ, cũ trước mới sau, để đưa cho LLM đọc."""
        lines = []
        for a in self.alerts.values():
            r = (f", nhân viên tới bàn sau {a['arrived_s']:.0f} giây (camera đo)" if a.get('arrived_at') else
                 f", nhận sau {(a['acked_at'] - a['created_at']) / 1000:.0f} giây" if a['acked_at'] else '')
            v = a['verify']
            vv = '' if v['state'] in ('skipped', 'pending') else ', ' + {
                'confirmed': f'{self.ten} xác nhận', 'rejected': f'{self.ten} bác bỏ',
                'unverified': f"chưa xác minh ({unverified_vi(v.get('path'), self.ten)})"}.get(
                    v['state'], f'{self.ten} lỗi')
            what = ('An ninh: ' + self._label(a, True) if a.get('group')
                    else f"{where(a['table'], a['camera'])} {KIND_VI[a['kind']]}")
            lines.append(f"[{a['id']}] {clock(a['created_at'])} {what}; trạng thái {a['status']}{r}"
                         f"{', người nhận ' + self._staff_name(a['acked_by']) if a['acked_by'] else ''}{vv}"
                         f"{', huỷ: ' + a['cancel_reason'] if a['cancel_reason'] else ''}")
        for e in reversed(self.log):
            if e['kind'] in ('guest_left', 'cleared'):
                lines.append(f"{clock(e['t'])} {e['text']}")
        return '\n'.join(lines[-limit:])
