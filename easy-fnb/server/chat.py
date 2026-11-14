"""Phòng chat của quán (nhân viên + chủ + AI) và ảnh thanh toán đọc bằng Gemini.

- Tin nhắn và thanh toán lưu ở DATA_DIR/quan.db (SQLite, mở-ghi-đóng như timeline.db), ảnh ở DATA_DIR/chat/<ngày>/.
- Đẩy về giao diện bằng luồng SSE riêng GET /api/chat/stream (không đụng luồng /api/stream của việc camera).
- AI chỉ nói khi có người gọi "@AI" (hoặc mở đầu "AI ơi"). Trả lời bằng chữ trong phòng, không đọc to.
- Ảnh thanh toán: POST /api/chat/scan (Gemini đọc, chờ tối đa 20 giây) -> điện thoại hiện kết quả, người chụp sửa
  nếu cần và BẤM XÁC NHẬN -> POST /api/chat/scan/{id}/send đăng vào phòng (ảnh + thẻ) và lưu thanh toán.
  Chỗ nào người chụp sửa so với Gemini đọc thì ghi vào payment_edits.

Spec: docs/superpowers/specs/2026-11-13-chatroom-hoa-don-design.md
"""
import asyncio
import base64
import json
import re
import secrets
import sqlite3
import threading
import time
import unicodedata
from contextlib import closing
from pathlib import Path

from fastapi import APIRouter, Body, HTTPException, Query, Request
from fastapi.responses import FileResponse, StreamingResponse

from . import doi_chieu
from .hub import CircuitBreaker, now_ms
from .timeline import day_of

SCHEMA = '''
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT, ts INTEGER NOT NULL, day TEXT NOT NULL, sender TEXT NOT NULL,
    "to" TEXT NOT NULL, kind TEXT NOT NULL, text TEXT, image TEXT, payment_id INTEGER, reply_to INTEGER);
CREATE INDEX IF NOT EXISTS messages_day ON messages (day, id);
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT, ts INTEGER NOT NULL, day TEXT NOT NULL, staff TEXT, status TEXT NOT NULL,
    type TEXT, amount INTEGER, paid_at TEXT, "table" TEXT, items TEXT, bank TEXT, sender_name TEXT, memo TEXT,
    txn_id TEXT, receipt_no TEXT, image TEXT, ocr TEXT, visit TEXT, visit_by TEXT, confirmed_by TEXT, note TEXT);
CREATE INDEX IF NOT EXISTS payments_day ON payments (day, id);
CREATE TABLE IF NOT EXISTS payment_edits (
    payment_id INTEGER NOT NULL, ts INTEGER NOT NULL, by TEXT, field TEXT, old TEXT, new TEXT);
CREATE INDEX IF NOT EXISTS payment_edits_pid ON payment_edits (payment_id);
CREATE TABLE IF NOT EXISTS visit_notes (
    visit TEXT PRIMARY KEY, by TEXT, reason TEXT, ts INTEGER);
'''
MSG_FIELDS = ('id', 'ts', 'day', 'sender', 'to', 'kind', 'text', 'image', 'payment_id', 'reply_to')
PAY_FIELDS = ('id', 'ts', 'day', 'staff', 'status', 'type', 'amount', 'paid_at', 'table', 'items', 'bank',
              'sender_name', 'memo', 'txn_id', 'receipt_no', 'image', 'ocr', 'visit', 'visit_by', 'confirmed_by',
              'note')
PAY_COLS = ', '.join(f'"{f}"' for f in PAY_FIELDS)
EDITABLE = ('type', 'amount', 'paid_at', 'table', 'items', 'bank', 'sender_name', 'memo', 'txn_id', 'receipt_no')
TYPES = ('chuyen_khoan', 'hoa_don', 'phieu_thu', 'khac')
TYPE_VI = {'chuyen_khoan': 'Chuyển khoản', 'hoa_don': 'Hoá đơn', 'phieu_thu': 'Phiếu thu', 'khac': 'Ảnh'}

MAX_TEXT = 1000
MAX_IMAGE = 3 * 1024 * 1024
OCR_TIMEOUT_S = 20.0
AI_TIMEOUT_S = 35.0
DRAFT_TTL_S = 3600
AMOUNT_MIN, AMOUNT_MAX = 5_000, 50_000_000
DUP_S = 180
AI_NAME = 'Tam'     # tên trợ lý trong phòng chat, viết không dấu
# gọi trợ lý: "@Tam", "Tam ơi"; "@AI", "AI ơi" vẫn nhận cho ai quen gõ vậy
AI_CALL = re.compile(r'(^|\s)@(ai|tam)(?!\w)|^\s*(ai|tam)\s+(ơi|oi)\b', re.IGNORECASE)

OCR_PROMPT = '''Bạn là bộ đọc ảnh thanh toán của một quán ăn ở Việt Nam. Ảnh có thể là: ảnh chụp màn hình chuyển khoản
ngân hàng hoặc ví điện tử (chuyen_khoan), hoá đơn in hoặc viết tay của quán (hoa_don), phiếu thu (phieu_thu), hoặc
không phải thanh toán (khac).

Quy tắc:
- Tiền Việt Nam, dấu chấm hoặc dấu phẩy là phân cách nghìn: "245.000", "245,000đ", "245.000 VND" đều là 245000.
- Chuyển khoản: so_tien là số tiền ĐÃ CHUYỂN, không phải số dư tài khoản, không phải phí. Lấy tên ngân hàng hoặc ví,
  tên người chuyển (nếu thấy), nội dung chuyển khoản nguyên văn, mã giao dịch.
- Hoá đơn: so_tien là dòng "Tổng cộng", "Thành tiền", "Tổng thanh toán" hoặc "Khách phải trả"; KHÔNG lấy "Tiền khách
  đưa" hay "Tiền thừa / trả lại". Liệt kê món (tên, số lượng, đơn giá) nếu đọc được.
- gio: giờ trên ảnh dạng HH:MM (24 giờ). ban: số hoặc tên bàn nếu có (trên hoá đơn, hoặc trong nội dung chuyển khoản
  như "BAN 3", "b3", "ban so 3"), chỉ ghi tên bàn, ví dụ "3".
- Ô nào không thấy thì để chuỗi rỗng (số tiền để 0), danh sách món rỗng. KHÔNG đoán.
- khong_chac: liệt kê các ô bạn đọc được nhưng chưa chắc (chữ mờ, bị che, viết tay khó đọc).
- KHÔNG ghi số tài khoản ngân hàng.'''

OCR_SCHEMA = {
    'type': 'object',
    'properties': {
        'loai': {'type': 'string', 'enum': list(TYPES)},
        'so_tien': {'type': 'integer'},
        'gio': {'type': 'string'},
        'ban': {'type': 'string'},
        'ngan_hang': {'type': 'string'},
        'nguoi_chuyen': {'type': 'string'},
        'noi_dung': {'type': 'string'},
        'ma_giao_dich': {'type': 'string'},
        'so_hoa_don': {'type': 'string'},
        'mon': {'type': 'array', 'items': {'type': 'object', 'properties': {
            'ten': {'type': 'string'}, 'sl': {'type': 'integer'}, 'gia': {'type': 'integer'}},
            'required': ['ten', 'sl', 'gia']}},
        'khong_chac': {'type': 'array', 'items': {'type': 'string', 'enum': [
            'so_tien', 'gio', 'ban', 'ngan_hang', 'nguoi_chuyen', 'noi_dung', 'ma_giao_dich', 'so_hoa_don', 'mon']}},
    },
    'required': ['loai', 'so_tien', 'gio', 'ban', 'ngan_hang', 'nguoi_chuyen', 'noi_dung', 'ma_giao_dich',
                 'so_hoa_don', 'mon', 'khong_chac'],
}
# tên ô trong kết quả Gemini -> tên trường thanh toán
OCR_FIELD = {'so_tien': 'amount', 'gio': 'paid_at', 'ban': 'table', 'ngan_hang': 'bank', 'nguoi_chuyen': 'sender_name',
             'noi_dung': 'memo', 'ma_giao_dich': 'txn_id', 'so_hoa_don': 'receipt_no', 'mon': 'items'}


def bo_dau(s):
    s = unicodedata.normalize('NFD', str(s or '')).replace('đ', 'd').replace('Đ', 'D')
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()


def khoa_ban(s):
    """'Bàn 03' -> '3', 'B3' -> '3', 'VIP 2' -> 'vip2'. Để so tên bàn đọc từ ảnh với tên bàn đã khai."""
    s = re.sub(r'[^a-z0-9]', '', bo_dau(s))
    s = re.sub(r'^(ban|b)(?=\d)', '', s)
    return s.lstrip('0') or s


def to_int(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return int(v)
    digits = re.sub(r'\D', '', str(v or ''))
    return int(digits) if digits else None


def hhmm(v):
    m = re.search(r'(\d{1,2})\s*[:hH.]\s*(\d{2})', str(v or ''))
    if not m:
        return None
    h, mi = int(m.group(1)), int(m.group(2))
    return f'{h:02d}:{mi:02d}' if h < 24 and mi < 60 else None


def money(n):
    return doi_chieu.money(n)


class Kho:
    """SQLite quan.db. Mỗi thao tác mở, làm, đóng (như timeline.db) để Windows xoá được thư mục dữ liệu."""

    def __init__(self, path):
        self.path = Path(path)
        self._lock = threading.Lock()
        self._ready = False

    def _connect(self):
        c = sqlite3.connect(str(self.path), timeout=2.0)
        if not self._ready:
            c.execute('PRAGMA journal_mode=WAL')
            c.executescript(SCHEMA)
            self._ready = True
        return c

    def run(self, sql, args=()):
        with self._lock, closing(self._connect()) as c:
            with c:
                cur = c.execute(sql, args)
                return cur.lastrowid

    def all(self, sql, args=()):
        with self._lock, closing(self._connect()) as c:
            return c.execute(sql, args).fetchall()

    def insert(self, table, row):
        cols = ', '.join(f'"{k}"' for k in row)
        return self.run(f'INSERT INTO {table} ({cols}) VALUES ({", ".join("?" * len(row))})', tuple(row.values()))


def _msg(r):
    d = dict(zip(MSG_FIELDS, r))
    d['to'] = json.loads(d['to'] or '["*"]')
    return d


def _pay(r):
    d = dict(zip(PAY_FIELDS, r))
    d['items'] = json.loads(d['items'] or '[]')
    d.pop('ocr', None)          # kết quả gốc của Gemini chỉ trả khi xem chi tiết
    return d


class Phong:
    def __init__(self, hub, llm, tro_ly=None, data_dir=None, ocr_timeout_s=OCR_TIMEOUT_S):
        self.hub = hub
        self.llm = llm
        self.tro_ly = tro_ly
        self.data = Path(data_dir or hub.data)
        self.kho = Kho(self.data / 'quan.db')
        self.subs = set()
        self.drafts = {}            # scan id -> ảnh đã quét, chờ người chụp xác nhận
        self.breaker = CircuitBreaker(3, 60.0, hub.clock)
        self.ocr_timeout_s = ocr_timeout_s
        self.ai_busy = 0
        self.tasks = set()

    # ------------------------------------------------------------ phát
    def publish(self, event, data):
        for q in list(self.subs):
            try:
                q.put_nowait((event, data))
            except asyncio.QueueFull:
                pass

    # ------------------------------------------------------------ người
    def who(self, sid):
        """Người gửi hợp lệ: 'chu' hoặc id một nhân viên đang có trong danh sách."""
        sid = str(sid or '').strip()
        if sid == 'chu' or any(s['id'] == sid for s in self.hub.staff):
            return sid
        raise ValueError(f'không có người gửi "{sid}"')

    def table_names(self):
        return [t['id'] for z in self.hub.zones.values() for t in z.get('tables', []) if t.get('id')]

    def find_table(self, raw):
        raw = str(raw or '').strip()
        if not raw:
            return None
        k = khoa_ban(raw)
        for name in self.table_names():
            if name == raw or khoa_ban(name) == k:
                return name
        return None

    # ------------------------------------------------------------ đọc
    def payment(self, pid, full=False):
        rows = self.kho.all(f'SELECT {PAY_COLS} FROM payments WHERE id = ?',
                            (int(pid),))
        if not rows:
            raise KeyError(pid)
        p = _pay(rows[0])
        if full:
            p['ocr'] = json.loads(rows[0][PAY_FIELDS.index('ocr')] or 'null')
            p['edits'] = [dict(zip(('ts', 'by', 'field', 'old', 'new'), r)) for r in self.kho.all(
                'SELECT ts, by, field, old, new FROM payment_edits WHERE payment_id = ? ORDER BY ts', (int(pid),))]
        return p

    def payments(self, day):
        rows = self.kho.all(f'SELECT {PAY_COLS} FROM payments '
                            'WHERE day = ? ORDER BY id', (day,))
        return [_pay(r) for r in rows]

    def _matches(self, day):
        """Đối chiếu cả ngày: {payment_id: dict(visit, text)}."""
        now_s = time.time()
        vs = doi_chieu.visits(self.hub.timeline, day, now_s)
        pays = self.payments(day)
        got = doi_chieu.match(pays, vs, now_s)
        by_key = {v['key']: v for v in vs}
        out = {}
        for p in pays:
            k = got.get(p['id'])
            if k:
                out[p['id']] = dict(visit=k, ok=True, text=f"Khớp lượt khách bàn {by_key[k]['table']}")
            elif p.get('table') and p.get('status') != 'void':
                out[p['id']] = dict(visit=None, ok=False, text=f"Camera không thấy khách bàn {p['table']} (mang về?)")
        return out

    def _with_payment(self, msgs, day):
        ids = {m['payment_id'] for m in msgs if m.get('payment_id')}
        if not ids:
            return msgs
        pays = {p['id']: p for p in self.payments(day)}
        matches = self._matches(day)
        for m in msgs:
            p = pays.get(m.get('payment_id'))
            if p:
                m['payment'] = dict(p, match=matches.get(p['id']))
        return msgs

    def messages(self, since=None, limit=50, day=None):
        day = day or day_of(time.time())
        limit = max(1, min(int(limit), 200))
        cols = ', '.join(f'"{f}"' for f in MSG_FIELDS)
        if since:
            rows = self.kho.all(f'SELECT {cols} FROM messages WHERE day = ? AND id > ? ORDER BY id LIMIT ?',
                                (day, int(since), limit))
        else:
            rows = self.kho.all(f'SELECT {cols} FROM messages WHERE day = ? ORDER BY id DESC LIMIT ?', (day, limit))[::-1]
        return self._with_payment([_msg(r) for r in rows], day)

    def message(self, mid):
        cols = ', '.join(f'"{f}"' for f in MSG_FIELDS)
        rows = self.kho.all(f'SELECT {cols} FROM messages WHERE id = ?', (int(mid),))
        if not rows:
            raise KeyError(mid)
        m = _msg(rows[0])
        return self._with_payment([m], m['day'])[0]

    # ------------------------------------------------------------ gửi tin
    def _add(self, sender, kind, text, to=None, image=None, payment_id=None, reply_to=None):
        t = now_ms()
        mid = self.kho.insert('messages', dict(ts=t, day=day_of(t / 1000), sender=sender, to=json.dumps(to or ['*']),
                                               kind=kind, text=text, image=image, payment_id=payment_id,
                                               reply_to=reply_to))
        m = self.message(mid)
        self.publish('message', m)
        return m

    def post(self, sender, text, to=None, reply_to=None):
        sender = self.who(sender)
        text = str(text or '').strip()
        if not text:
            raise ValueError('tin trống')
        if len(text) > MAX_TEXT:
            raise ValueError(f'tin dài quá {MAX_TEXT} ký tự')
        to = [str(x) for x in (to or ['*'])][:20]
        m = self._add(sender, 'text', text, to=to, reply_to=reply_to)
        if AI_CALL.search(text) and self.tro_ly is not None:
            self._spawn(self._ai_reply(m))
        return m

    def _spawn(self, coro):
        task = asyncio.get_running_loop().create_task(coro)
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)

    def _money_line(self):
        pays = [p for p in self.payments(day_of(time.time())) if p['status'] != 'void']
        if not pays:
            return 'Hôm nay chưa có thanh toán nào được chụp gửi vào nhóm.'
        ck = sum(1 for p in pays if p['type'] == 'chuyen_khoan')
        tong = sum(p['amount'] or 0 for p in pays)
        return f'Hôm nay đã chụp gửi {len(pays)} thanh toán ({ck} chuyển khoản), tổng {money(tong)}.'

    async def _ai_reply(self, m):
        q = AI_CALL.sub(' ', m['text']).strip(' ,:') or 'Tóm tắt ca hiện tại'
        name = 'chủ quán' if m['sender'] == 'chu' else next(
            (s['name'] for s in self.hub.staff if s['id'] == m['sender']), m['sender'])
        prompt = (f'[Bạn tên là {AI_NAME}, trợ lý trong phòng chat của quán. Người hỏi: {name}. Trả lời bằng chữ, tối đa 3 câu ngắn, '
                  f'không dùng công cụ hiển thị, không cài đặt gì. Tiền thu của quán: hệ thống CÓ ghi, từ ảnh chuyển '
                  f'khoản và hoá đơn nhân viên gửi vào nhóm; hỏi về tiền thì trả lời thẳng bằng số này, không nói là '
                  f'chưa ghi. {self._money_line()}]\n{q}')
        self.ai_busy += 1
        self.publish('ai', dict(busy=True))
        try:
            ans = await asyncio.wait_for(self.tro_ly.hoi(prompt, session=f"phong-{m['day']}", che_do='phong'),
                                         AI_TIMEOUT_S)
            text = str(ans.get('answer') or '').strip()
            if not text or text == 'Số liệu ở bên dưới.':
                text = 'Mình chưa trả lời được câu này, hỏi lại cụ thể hơn giúp mình nhé.'
        except Exception as e:   # noqa: BLE001  AI lỗi không làm hỏng phòng chat
            text = f'{AI_NAME} đang lỗi, chưa trả lời được ({type(e).__name__}).'
        finally:
            self.ai_busy -= 1
            self.publish('ai', dict(busy=self.ai_busy > 0))
        self._add('ai', 'ai', text[:MAX_TEXT], reply_to=m['id'])

    # ------------------------------------------------------------ ảnh thanh toán
    def _img_dir(self, day):
        d = self.data / 'chat' / day
        d.mkdir(parents=True, exist_ok=True)
        return d

    def image_file(self, name):
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}/[A-Za-z0-9_-]+\.jpg', name or ''):
            raise KeyError(name)
        f = self.data / 'chat' / name
        if not f.exists():
            raise KeyError(name)
        return f

    def _prune(self):
        now = time.time()
        for sid, d in list(self.drafts.items()):
            if now - d['t'] > DRAFT_TTL_S:
                self.drafts.pop(sid, None)
                try:
                    (self.data / 'chat' / d['image']).unlink()
                except OSError:
                    pass

    @property
    def ocr_on(self):
        return getattr(self.llm, 'ten', '') == 'Gemini' and bool(getattr(self.llm, 'enabled', False)) \
            and hasattr(self.llm, 'json')

    async def _ocr(self, jpeg):
        parts = [{'text': OCR_PROMPT},
                 {'inline_data': {'mime_type': 'image/jpeg', 'data': base64.b64encode(jpeg).decode()},
                  'mediaResolution': {'level': 'MEDIA_RESOLUTION_HIGH'}}]
        return await self.llm.json(parts, OCR_SCHEMA, image=True)

    def _draft(self, r, table_hint):
        """Kết quả Gemini -> các ô của màn hình xác nhận, kèm ô chưa chắc và lời cảnh báo."""
        loai = r.get('loai') if r.get('loai') in TYPES else 'khac'
        unsure = {OCR_FIELD[k] for k in (r.get('khong_chac') or []) if k in OCR_FIELD}
        items = []
        for it in r.get('mon') or []:
            if isinstance(it, dict) and str(it.get('ten') or '').strip():
                items.append(dict(name=str(it['ten']).strip()[:80], qty=max(1, to_int(it.get('sl')) or 1),
                                  price=to_int(it.get('gia')) or 0))
        amount = to_int(r.get('so_tien')) or None
        raw_table = str(r.get('ban') or '').strip()
        table = table_hint or self.find_table(raw_table)
        d = dict(type=loai, amount=amount, paid_at=hhmm(r.get('gio')), table=table, items=items[:60],
                 bank=str(r.get('ngan_hang') or '').strip()[:60] or None,
                 sender_name=str(r.get('nguoi_chuyen') or '').strip()[:80] or None,
                 memo=str(r.get('noi_dung') or '').strip()[:200] or None,
                 txn_id=str(r.get('ma_giao_dich') or '').strip()[:60] or None,
                 receipt_no=str(r.get('so_hoa_don') or '').strip()[:40] or None)
        warn = []
        if amount is None:
            unsure.add('amount')
            warn.append('Chưa đọc được số tiền')
        elif not AMOUNT_MIN <= amount <= AMOUNT_MAX:
            unsure.add('amount')
            warn.append('Số tiền lạ, kiểm tra lại')
        if items and amount:
            tong = sum(i['qty'] * i['price'] for i in items)
            if tong and abs(tong - amount) > amount * 0.02:
                unsure.add('amount')
                warn.append(f'Tổng các món ({money(tong)}) khác số tiền')
        if raw_table and not table_hint and not table:
            unsure.add('table')
            warn.append(f'Ảnh ghi bàn "{raw_table[:20]}" nhưng quán không có bàn này')
        return d, sorted(unsure), warn

    def duplicates(self, d, exclude=None):
        """Thanh toán đã gửi trùng mã giao dịch / số hoá đơn, hoặc cùng số tiền và bàn trong 3 phút."""
        out = []
        now = now_ms()
        for p in self.payments(day_of(time.time())):
            if p['status'] == 'void' or p['id'] == exclude:
                continue
            same_code = (d.get('txn_id') and p['txn_id'] == d['txn_id']) or \
                        (d.get('receipt_no') and p['receipt_no'] == d['receipt_no'])
            same_amount = d.get('amount') and p['amount'] == d['amount'] and p['table'] == d.get('table') \
                and now - p['ts'] < DUP_S * 1000
            if same_code or same_amount:
                out.append(p)
        return out

    async def scan(self, staff, jpeg, table=None):
        staff = self.who(staff)
        if not jpeg or len(jpeg) < 100 or jpeg[:2] != b'\xff\xd8':
            raise ValueError('cần ảnh JPEG')
        if len(jpeg) > MAX_IMAGE:
            raise ValueError('ảnh quá lớn (tối đa 3 MB)')
        self._prune()
        table_hint = self.find_table(table) if table else None
        sid = secrets.token_hex(6)
        day = day_of(time.time())
        name = f'{day}/{sid}.jpg'
        (self._img_dir(day) / f'{sid}.jpg').write_bytes(jpeg)
        t0 = time.perf_counter()
        raw, engine, error = None, 'manual', None
        if not self.ocr_on:
            error = 'Chưa đọc tự động được, nhập tay giúp'
        elif not self.breaker.allow():
            error = 'Chưa đọc tự động được, nhập tay giúp'
        else:
            try:
                raw = await asyncio.wait_for(self._ocr(jpeg), self.ocr_timeout_s)
                if not isinstance(raw, dict):
                    raise ValueError('kết quả không phải JSON')
                self.breaker.success()
                engine = 'gemini'
            except Exception as e:   # noqa: BLE001  mạng, khoá sai, quá giờ: nhập tay
                self.breaker.failure()
                error = 'Chưa đọc được ảnh, nhập tay giúp'
                raw = None
        if raw is not None:
            draft, unsure, warn = self._draft(raw, table_hint)
        else:
            draft = dict(type='chuyen_khoan', amount=None, paid_at=None, table=table_hint, items=[], bank=None,
                         sender_name=None, memo=None, txn_id=None, receipt_no=None)
            unsure, warn = ['amount'], []
        dups = self.duplicates(draft)
        if dups:
            p = dups[0]
            warn.append(f"Có thể đã gửi rồi lúc {doi_chieu.hhmm(p['ts'] / 1000)} "
                        f"({money(p['amount'])})")
        ms = int((time.perf_counter() - t0) * 1000)
        self.drafts[sid] = dict(t=time.time(), staff=staff, image=name, raw=raw, draft=dict(draft), engine=engine,
                                ms=ms, model=getattr(self.llm, 'model', None) if engine == 'gemini' else None)
        return dict(scan_id=sid, image=name, engine=engine, error=error, ms=ms, fields=draft, unsure=unsure,
                    warnings=warn, is_payment=draft['type'] != 'khac' or raw is None)

    def _clean(self, f):
        """Ô người dùng gửi lên -> giá trị lưu được. Ném ValueError nếu sai."""
        out = {}
        for k in EDITABLE:
            if k not in f:
                continue
            v = f[k]
            if k == 'type':
                if v not in TYPES:
                    raise ValueError('loại không hợp lệ')
            elif k == 'amount':
                v = to_int(v)
                if v is not None and not 0 < v <= AMOUNT_MAX:
                    raise ValueError('số tiền không hợp lệ')
            elif k == 'paid_at':
                v = hhmm(v) if v else None
            elif k == 'table':
                if v:
                    t = self.find_table(v)
                    if not t:
                        raise ValueError(f'quán không có bàn "{v}"')
                    v = t
                else:
                    v = None
            elif k == 'items':
                v = [dict(name=str(i.get('name') or '')[:80], qty=max(1, to_int(i.get('qty')) or 1),
                          price=to_int(i.get('price')) or 0) for i in (v or []) if isinstance(i, dict)][:60]
            else:
                v = (str(v).strip()[:200] or None) if v is not None else None
            out[k] = v
        return out

    def send_scan(self, scan_id, by, fields=None, to=None, text=None):
        """Người chụp đã xem và bấm Xác nhận: lưu thanh toán, đăng ảnh + thẻ vào phòng."""
        by = self.who(by)
        d = self.drafts.pop(scan_id, None)
        if d is None:
            raise KeyError(scan_id)
        final = dict(d['draft'], **self._clean(fields or {}))
        caption = str(text or '').strip()[:MAX_TEXT] or None
        if final['type'] == 'khac':          # không phải thanh toán: gửi như ảnh thường
            return self._add(by, 'photo', caption or '', to=to, image=d['image'])
        if not final.get('amount'):
            self.drafts[scan_id] = d
            raise ValueError('cần số tiền')
        t = now_ms()
        row = dict(ts=t, day=day_of(t / 1000), staff=d['staff'], status='confirmed', image=d['image'],
                   ocr=json.dumps(dict(raw=d['raw'], engine=d['engine'], ms=d['ms'], model=d['model']),
                                  ensure_ascii=False), confirmed_by=by,
                   **{k: (json.dumps(final[k], ensure_ascii=False) if k == 'items' else final[k]) for k in EDITABLE})
        pid = self.kho.insert('payments', row)
        if d['engine'] == 'gemini':
            for k in EDITABLE:
                if final.get(k) != d['draft'].get(k):
                    self._edit(pid, by, k, d['draft'].get(k), final.get(k))
        summary = f"{TYPE_VI[final['type']]} {money(final['amount'])}" + (f", bàn {final['table']}" if final['table'] else '')
        return self._add(by, 'payment', caption or summary, to=to, image=d['image'], payment_id=pid)

    def _edit(self, pid, by, field, old, new):
        enc = lambda v: v if isinstance(v, str) or v is None else json.dumps(v, ensure_ascii=False)  # noqa: E731
        self.kho.insert('payment_edits', dict(payment_id=pid, ts=now_ms(), by=by, field=field, old=enc(old), new=enc(new)))

    def _pub_payment(self, pid):
        p = self.payment(pid)
        p['match'] = self._matches(p['day']).get(pid)
        self.publish('payment', p)
        return p

    def patch_payment(self, pid, by, fields):
        by = self.who(by)
        p = self.payment(pid)
        if p['status'] == 'void':
            raise ValueError('thanh toán đã huỷ')
        new = self._clean(fields or {})
        changed = {k: v for k, v in new.items() if v != p.get(k)}
        if 'amount' in changed and not changed['amount']:
            raise ValueError('cần số tiền')
        if changed:
            sets = ', '.join(f'"{k}" = ?' for k in changed)
            vals = [json.dumps(v, ensure_ascii=False) if k == 'items' else v for k, v in changed.items()]
            self.kho.run(f'UPDATE payments SET {sets} WHERE id = ?', (*vals, int(pid)))
            for k, v in changed.items():
                self._edit(int(pid), by, k, p.get(k), v)
        return self._pub_payment(int(pid))

    def void_payment(self, pid, by, reason=''):
        by = self.who(by)
        self.payment(pid)
        self.kho.run('UPDATE payments SET status = ?, note = ? WHERE id = ?', ('void', str(reason or '')[:200], int(pid)))
        self._edit(int(pid), by, 'status', 'confirmed', 'void')
        return self._pub_payment(int(pid))

    # ------------------------------------------------------------ doanh thu
    def note_visit(self, visit, by, reason=None, payment_id=None):
        by = self.who(by)
        if payment_id is not None:
            self.payment(payment_id)
            self.kho.run('UPDATE payments SET visit = ?, visit_by = ? WHERE id = ?', (visit, by, int(payment_id)))
            return self._pub_payment(int(payment_id))
        self.kho.run('INSERT OR REPLACE INTO visit_notes (visit, by, reason, ts) VALUES (?, ?, ?, ?)',
                     (visit, by, str(reason or 'không thu tiền')[:200], now_ms()))
        return dict(ok=True)

    def revenue(self, day=None):
        day = day or day_of(time.time())
        now_s = time.time()
        pays = [p for p in self.payments(day) if p['status'] != 'void']
        vs = doi_chieu.visits(self.hub.timeline, day, now_s)
        got = doi_chieu.match(pays, vs, now_s)
        notes = {r[0] for r in self.kho.all('SELECT visit FROM visit_notes')}
        total = sum(p['amount'] or 0 for p in pays)
        guests = sum(v['people'] for v in vs if v['key'] in set(got.values()))
        by_hour = {}
        for p in pays:
            h = doi_chieu.hhmm(p['ts'] / 1000)[:2]
            by_hour[h] = by_hour.get(h, 0) + (p['amount'] or 0)
        visits_by_hour = {}
        for v in vs:
            h = doi_chieu.hhmm(v['start'])[:2]
            visits_by_hour[h] = visits_by_hour.get(h, 0) + 1
        # ngày của quán bắt đầu 4 giờ sáng: giờ sau nửa đêm xếp cuối, không xếp đầu
        hours = sorted(set(by_hour) | set(visits_by_hour), key=lambda h: (int(h) - doi_chieu.DOI_NGAY_H) % 24)
        return dict(day=day, total=total, count=len(pays),
                    transfers=sum(1 for p in pays if p['type'] == 'chuyen_khoan'),
                    visits=len(vs), per_guest=round(total / guests) if guests else None,
                    hours=[dict(hour=h, amount=by_hour.get(h, 0), visits=visits_by_hour.get(h, 0)) for h in hours],
                    review=doi_chieu.review(pays, vs, got, notes, now_s),
                    payments=[dict(p, visit=got.get(p['id'])) for p in pays])


# ------------------------------------------------------------------ API
def router(phong):
    r = APIRouter()

    def bad(e):
        if isinstance(e, KeyError):
            return HTTPException(404, 'không tìm thấy')
        return HTTPException(400, str(e))

    @r.get('/api/chat')
    async def list_messages(since: int | None = None, limit: int = 50, day: str | None = None):
        return dict(messages=phong.messages(since, limit, day), ai_busy=phong.ai_busy > 0, ocr=phong.ocr_on)

    @r.get('/api/chat/stream')
    async def chat_stream(request: Request):
        q = asyncio.Queue(maxsize=500)
        phong.subs.add(q)

        async def gen():
            try:
                yield 'event: hello\ndata: {}\n\n'
                while True:
                    if await request.is_disconnected():
                        break
                    try:
                        ev, data = await asyncio.wait_for(q.get(), timeout=15)
                        yield f'event: {ev}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n'
                    except asyncio.TimeoutError:
                        yield ': ping\n\n'
            finally:
                phong.subs.discard(q)
        return StreamingResponse(gen(), media_type='text/event-stream',
                                 headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})

    @r.post('/api/chat')
    async def post_message(body: dict = Body(...)):
        try:
            return phong.post(body.get('from'), body.get('text'), body.get('to'), body.get('reply_to'))
        except (ValueError, KeyError) as e:
            raise bad(e)

    @r.post('/api/chat/scan')
    async def scan(request: Request, staff: str = Query(...), table: str | None = None):
        n = request.headers.get('content-length', '')
        if n.isdigit() and int(n) > MAX_IMAGE:
            raise HTTPException(413, 'ảnh quá lớn (tối đa 3 MB)')
        try:
            return await phong.scan(staff, await request.body(), table)
        except ValueError as e:
            raise bad(e)

    @r.post('/api/chat/scan/{scan_id}/send')
    async def send_scan(scan_id: str, body: dict = Body(...)):
        try:
            return phong.send_scan(scan_id, body.get('by'), body.get('fields'), body.get('to'), body.get('text'))
        except KeyError:
            raise HTTPException(404, 'ảnh này đã gửi hoặc đã hết hạn, chụp lại giúp')
        except ValueError as e:
            raise bad(e)

    @r.get('/api/chat/image/{day}/{name}')
    async def chat_image(day: str, name: str):
        try:
            f = phong.image_file(f'{day}/{name}')
        except KeyError:
            raise HTTPException(404, 'không có ảnh')
        return FileResponse(f, media_type='image/jpeg', headers={'Cache-Control': 'private, max-age=86400'})

    @r.get('/api/payments/{pid}')
    async def get_payment(pid: int):
        try:
            return phong.payment(pid, full=True)
        except KeyError as e:
            raise bad(e)

    @r.patch('/api/payments/{pid}')
    async def patch_payment(pid: int, body: dict = Body(...)):
        try:
            return phong.patch_payment(pid, body.get('by'), {k: v for k, v in body.items() if k != 'by'})
        except (ValueError, KeyError) as e:
            raise bad(e)

    @r.post('/api/payments/{pid}/void')
    async def void_payment(pid: int, body: dict = Body(...)):
        try:
            return phong.void_payment(pid, body.get('by'), body.get('reason'))
        except (ValueError, KeyError) as e:
            raise bad(e)

    @r.get('/api/revenue')
    async def revenue(day: str | None = None):
        try:
            return phong.revenue(day)
        except ValueError as e:
            raise bad(e)

    @r.post('/api/visits/{visit}/note')
    async def note_visit(visit: str, body: dict = Body(...)):
        try:
            return phong.note_visit(visit, body.get('by'), body.get('reason'), body.get('payment_id'))
        except (ValueError, KeyError) as e:
            raise bad(e)

    return r
