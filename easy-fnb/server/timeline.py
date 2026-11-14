"""Dòng thời gian lâu dài của quán: mọi việc đã xảy ra, lưu bằng SQLite ở DATA_DIR/timeline.db.

Khác với nhật ký trong RAM của Hub (500 dòng, mất khi khởi động lại, xoá khi bắt đầu ca mới), dòng thời gian
giữ qua nhiều ca và nhiều lần khởi động lại.

Ghi rẻ: add() chỉ thêm vào bộ đệm trong RAM; flush() (Hub gọi mỗi giây ở vòng lặp nền, và trước mỗi lần đọc)
mới mở tệp, ghi cả lô trong một giao dịch rồi đóng lại. Không giữ kết nối mở, nên Windows xoá được thư mục
dữ liệu bất cứ lúc nào (các test dùng thư mục tạm). Mọi lỗi SQLite hay ổ đĩa đều bị nuốt (in ra một lần):
Hub không bao giờ hỏng vì dòng thời gian.

Một dòng: id, ts (giây epoch), day ('YYYY-MM-DD' giờ Việt Nam), camera, table, kind, alert_id, staff, text,
data (dict các trường thêm). Các kind đang dùng:
    log                 một dòng nhật ký của Hub; data.log_kind là loại dòng (call, done, verify, system...)
    alert_created       việc mới; staff = người được giao (nếu có); data: alert_kind, status, verify
    alert_verified | alert_rejected | alert_unverified      kết quả AI kiểm tra; data: alert_kind, path, reason
    alert_assigned      đổi người được giao sau khi tạo; staff = người mới
    alert_acked         có người nhận hoặc camera thấy nhân viên tới; data: wait_s, by_camera
    alert_done | alert_auto_closed | alert_cancelled         đóng việc; data: by, reason, wait_s, total_s
    table               bàn đổi trạng thái; data: state, prev, people
    staff_online | staff_offline
    stage               bàn đổi giai đoạn bữa ăn (server/giai_doan.py); data: stage, prev, via, seat, prev_s
    nudge               lời nhắc mềm khi một giai đoạn kéo quá lâu; data: nudge (greet|food|bill), stage, seat
    table_check         một lần Gemini Decision xem ảnh bàn; data: xác suất từng câu hỏi
    shift_reset         quản lý bấm "bắt đầu ca mới" (dòng thời gian KHÔNG bị xoá)
"""
import json
import sqlite3
import threading
import time
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path

VN = timezone(timedelta(hours=7))
SCHEMA = '''
CREATE TABLE IF NOT EXISTS timeline (
    id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL NOT NULL, day TEXT NOT NULL, camera TEXT, "table" TEXT,
    kind TEXT NOT NULL, alert_id TEXT, staff TEXT, text TEXT, data TEXT);
CREATE INDEX IF NOT EXISTS timeline_ts ON timeline (ts);
CREATE INDEX IF NOT EXISTS timeline_table_ts ON timeline ("table", ts);
CREATE INDEX IF NOT EXISTS timeline_day ON timeline (day);
'''
INSERT = 'INSERT INTO timeline (ts, day, camera, "table", kind, alert_id, staff, text, data) VALUES (?,?,?,?,?,?,?,?,?)'
FIELDS = ('id', 'ts', 'day', 'camera', 'table', 'kind', 'alert_id', 'staff', 'text', 'data')
MAX_BUFFER = 5000       # ổ đĩa hỏng lâu: giữ tối đa chừng này dòng chờ ghi, bỏ dòng cũ nhất
FLUSH_AT = 100          # bộ đệm đầy mức này thì ghi luôn, không chờ vòng lặp nền
CLOSED = ('done', 'cancelled')


DOI_NGAY_H = 4      # ngày của quán đổi lúc 4 giờ sáng: ca tối kéo qua nửa đêm vẫn là một ngày


def day_of(ts):
    return datetime.fromtimestamp(ts - DOI_NGAY_H * 3600, VN).strftime('%Y-%m-%d')


class Timeline:
    def __init__(self, path):
        self.path = Path(path)
        self._buf = []
        self._lock = threading.Lock()
        self._ready = False         # đã tạo bảng trong lần chạy này chưa
        self._warned = False

    def _connect(self):
        c = sqlite3.connect(str(self.path), timeout=0.5)
        if not self._ready:
            c.execute('PRAGMA journal_mode=WAL')
            c.executescript(SCHEMA)
            self._ready = True
        c.execute('PRAGMA synchronous=NORMAL')
        return c

    def _error(self, e):
        self._ready = False         # tệp có thể đã bị xoá hoặc hỏng: lần sau tạo lại bảng
        if not self._warned:
            self._warned = True
            print(f'dòng thời gian lỗi (máy chủ vẫn chạy, chỉ thiếu lịch sử): {type(e).__name__}: {e}')

    def add(self, kind, ts=None, table=None, camera=None, alert_id=None, staff=None, text=None, **data):
        """Thêm một dòng. Không bao giờ ném lỗi."""
        try:
            ts = float(ts) if ts is not None else time.time()
            row = (ts, day_of(ts), camera, table, str(kind), alert_id, staff, text,
                   json.dumps(data, ensure_ascii=False, default=str) if data else None)
            with self._lock:
                self._buf.append(row)
                if len(self._buf) > MAX_BUFFER:
                    del self._buf[:len(self._buf) - MAX_BUFFER]
                full = len(self._buf) >= FLUSH_AT and not self._warned
            if full:
                self.flush()
        except Exception as e:      # dữ liệu lạ không được làm hỏng Hub
            self._error(e)

    def flush(self):
        """Ghi bộ đệm ra tệp. Lỗi (tệp bị khoá, ổ đĩa đầy) thì giữ lại để lần sau ghi tiếp. Trả True nếu ổn."""
        with self._lock:
            if not self._buf:
                return True
            try:
                with closing(self._connect()) as c:
                    with c:
                        c.executemany(INSERT, self._buf)
                self._buf.clear()
                self._warned = False
                return True
            except Exception as e:
                self._error(e)
                return False

    def query(self, since=None, until=None, table=None, kinds=None, alert_id=None, limit=500, newest_first=False):
        """Các dòng thoả điều kiện, cũ trước (newest_first=True thì mới trước), tối đa `limit` dòng.
        since/until: giây epoch. kinds: một chuỗi hoặc danh sách; 'alert_*' khớp mọi kind bắt đầu bằng 'alert_'."""
        self.flush()
        where, args = [], []
        if since is not None:
            where.append('ts >= ?'); args.append(float(since))
        if until is not None:
            where.append('ts <= ?'); args.append(float(until))
        if table:
            where.append('"table" = ?'); args.append(str(table))
        if alert_id:
            where.append('alert_id = ?'); args.append(str(alert_id))
        if kinds:
            ks = [kinds] if isinstance(kinds, str) else list(kinds)
            ors = []
            for k in ks:
                if k.endswith('*'):
                    ors.append("kind LIKE ? ESCAPE '\\'")
                    args.append(k[:-1].replace('\\', '\\\\').replace('_', '\\_').replace('%', '\\%') + '%')
                else:
                    ors.append('kind = ?'); args.append(k)
            where.append('(' + ' OR '.join(ors) + ')')
        order = 'DESC' if newest_first else 'ASC'
        sql = (f'SELECT id, ts, day, camera, "table", kind, alert_id, staff, text, data FROM timeline'
               f"{' WHERE ' + ' AND '.join(where) if where else ''} ORDER BY ts {order}, id {order} LIMIT ?")
        try:
            with self._lock, closing(self._connect()) as c:
                rows = c.execute(sql, args + [max(1, min(int(limit), 5000))]).fetchall()
        except Exception as e:
            self._error(e)
            return []
        out = []
        for r in rows:
            d = dict(zip(FIELDS, r))
            try:
                d['data'] = json.loads(d['data']) if d['data'] else {}
            except ValueError:
                d['data'] = {}
            out.append(d)
        return out

    def days(self):
        """Các ngày (giờ Việt Nam) có dữ liệu, cũ trước."""
        self.flush()
        try:
            with self._lock, closing(self._connect()) as c:
                return [r[0] for r in c.execute('SELECT DISTINCT day FROM timeline ORDER BY day')]
        except Exception as e:
            self._error(e)
            return []

    def close(self):
        self.flush()


class Ghi:
    """Chép các thay đổi Hub phát ra (SSE) vào dòng thời gian. Hub.publish gọi publish() cho mọi sự kiện, nên
    vòng đời của việc và trạng thái bàn được ghi ở đúng một chỗ: so bản mới với bản đã thấy lần trước."""

    def __init__(self, timeline, on_served=None):
        self.tl = timeline
        self.on_served = on_served      # gọi (bàn) khi nhân viên bấm Xong việc gọi/khách mới: bàn đã có người tới
        self.alerts = {}                # id việc -> những trường đã ghi
        self.tables = {}                # "cam/bàn" -> trạng thái đã ghi

    def reset(self):
        self.alerts.clear()
        self.tables.clear()

    def publish(self, event, data):
        try:
            if event == 'alert':
                self._alert(data)
            elif event == 'table':
                self._table(data)
        except Exception as e:
            self.tl._error(e)

    def _table(self, tb):
        key = f"{tb.get('camera')}/{tb.get('id')}"
        prev = self.tables.get(key)
        if prev == tb.get('state'):
            return
        self.tables[key] = tb.get('state')
        self.tl.add('table', table=tb.get('id'), camera=tb.get('camera'), state=tb.get('state'), prev=prev,
                    people=tb.get('people'))

    def _alert(self, a):
        aid = a['id']
        v = a.get('verify') or {}
        now = dict(status=a['status'], verify=v.get('state'), staff=a.get('assigned_to'), acked=a.get('acked_at'))
        old = self.alerts.get(aid)
        self.alerts[aid] = now
        base = dict(table=a.get('table'), camera=a.get('camera'), alert_id=aid)
        kind = a.get('kind')

        def secs(key):
            return round((a[key] - a['created_at']) / 1000, 1) if a.get(key) else None
        if old is None:
            self.tl.add('alert_created', ts=a['created_at'] / 1000, staff=a.get('assigned_to'), **base,
                        alert_kind=kind, status=a['status'], verify=v.get('state'))
            old = dict(status=a['status'], verify=v.get('state') if v.get('state') in ('pending', 'skipped') else None,
                       staff=a.get('assigned_to'), acked=None)
        if now['verify'] != old['verify'] and now['verify'] in ('confirmed', 'rejected', 'unverified'):
            self.tl.add({'confirmed': 'alert_verified', 'rejected': 'alert_rejected',
                         'unverified': 'alert_unverified'}[now['verify']], **base, alert_kind=kind,
                        path=v.get('path'), reason=v.get('reason'), ms=v.get('ms'))
        if now['staff'] and now['staff'] != old['staff']:
            self.tl.add('alert_assigned', staff=now['staff'], **base, alert_kind=kind, prev=old['staff'])
        wait = a.get('arrived_s') if a.get('arrived_s') is not None else secs('acked_at')
        if now['acked'] and not old['acked']:
            self.tl.add('alert_acked', staff=a.get('acked_by') if a.get('acked_by') != 'camera' else None, **base,
                        alert_kind=kind, wait_s=wait, by_camera=bool(a.get('arrived_at')))
        if now['status'] != old['status'] and now['status'] in CLOSED:
            if now['status'] == 'cancelled':
                self.tl.add('alert_cancelled', staff=a.get('assigned_to'), **base, alert_kind=kind,
                            reason=a.get('cancel_reason'), total_s=secs('cancelled_at'))
                return
            by = a.get('done_by')
            missed = by == 'camera' and kind != 'needs_clearing' and not a.get('arrived_at')
            self.tl.add('alert_auto_closed' if missed else 'alert_done',
                        staff=a.get('acked_by') if a.get('acked_by') != 'camera' else a.get('assigned_to'), **base,
                        alert_kind=kind, by=by, reason=a.get('close_reason'), wait_s=wait, total_s=secs('done_at'))
            if self.on_served and a.get('table') and kind != 'needs_clearing' and by not in ('camera', 'gemini', 'manager', None):
                self.on_served(a['table'])
