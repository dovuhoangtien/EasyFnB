"""Bản thử (T4) của luồng xác minh Gemini mới. KHÔNG sửa server; chỉ import và kế thừa.

Gồm:
- prompt + schema enum cho 'call' (GOI / KHONG_GOI / KHONG_CHAC) và 'needs_clearing' (CAN_DON / SACH / KHONG_CHAC)
- dựng thân request generateContent với độ phân giải riêng cho từng ảnh
- ước tính token, chi phí
- luật quyết định `decide()`
- CircuitBreaker
- GeminiV2 (kế thừa server.gemini.Gemini) và HubV2 (kế thừa server.hub.Hub): timeout + breaker + trạng thái
  "Chưa xác minh" (verify.state = 'unverified', verify.path ghi đường đi của cảnh báo)
"""
import asyncio
import base64
import copy
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'easy-fnb'))

from server.gemini import Gemini, GeminiError, _parse_json, _text  # noqa: E402
from server.hub import Hub, KIND_VI, where_l  # noqa: E402

# ------------------------------------------------------------------ prompt
# Mỗi ảnh có một vai trò; độ phân giải đặt theo vai trò.
ROLE_RES = {'strip': 'MEDIUM', 'overview': 'LOW', 'clean_ref': 'LOW'}
IMG_TOKENS = {'LOW': 280, 'MEDIUM': 560, 'HIGH': 1120}   # Gemini 3, theo tài liệu media resolution

LOAI_TRU_GOI = ('vươn vai, vuốt hoặc chỉnh tóc, gãi đầu, chỉnh kính hoặc mũ, uống hoặc ăn, nâng ly chúc, '
                'nghe hoặc chụp điện thoại, chỉ tay khi nói chuyện, chống cằm, vẫy chào bạn cùng bàn, '
                'nhân viên (đồng phục, bưng khay)')
DO_CUA_QUAN = 'lọ gia vị, hộp giấy ăn, ống đũa, menu, ly úp sẵn'

PROMPT_CALL = (
    'Kiểm tra cảnh báo từ camera quán ăn. Ảnh 1: 4 khung trong 1,5 giây (trái sang phải, trên xuống dưới), '
    'cắt quanh MỘT người. Ảnh 2: toàn cảnh, khung đỏ là người đó. Chỉ xét người trong khung đỏ.\n'
    'GOI: giơ tay ngang hoặc trên đầu, hướng ra quán để gọi nhân viên, giữ hoặc vẫy qua ít nhất 2 khung.\n'
    f'KHONG_GOI nếu là: {LOAI_TRU_GOI}.\n'
    'KHONG_CHAC: ảnh không đủ rõ để kết luận. Không đoán.\n'
    'Điền checklist trước, rồi verdict. reason: tiếng Việt, tối đa 12 chữ.'
)

PROMPT_TABLE = (
    'Kiểm tra cảnh báo "bàn cần dọn" từ camera quán ăn. Ảnh 1: 4 khung trong 1,5 giây cắt quanh bàn {ban}. '
    'Ảnh 2: toàn cảnh, khung đỏ là bàn đó.{ref} Chỉ xét bàn trong khung đỏ.\n'
    'CAN_DON: không ai ngồi, còn chén đĩa, ly đã dùng, thức ăn thừa, giấy bẩn.\n'
    f'SACH: không còn đồ đã dùng. Đồ của quán không tính: {DO_CUA_QUAN}.\n'
    'personal_belongings_present: túi, điện thoại, áo khoác, ví của khách còn trên bàn hoặc ghế.\n'
    'KHONG_CHAC: ảnh không đủ rõ. Không đoán.\n'
    'Điền checklist trước, rồi verdict. reason: tiếng Việt, tối đa 12 chữ.'
)
REF_SENTENCE = ' Ảnh 3: cùng bàn lúc sạch; chỉ tính đồ KHÔNG có trong ảnh 3.'

QUALITY = ['ok', 'toi', 'mo', 'bi_che', 'qua_nho']
ALT_CALL = ['vuon_vai', 'chinh_toc', 'uong_an', 'nang_ly', 'dien_thoai', 'chi_tay', 'vay_ban', 'nhan_vien',
            'khac', 'none']

SCHEMA_CALL = {'type': 'object', 'properties': {
    'checklist': {'type': 'object', 'properties': {
        'hand_above_head': {'type': 'boolean'},
        'held_or_waved_across_frames': {'type': 'boolean'},
        'wearing_staff_uniform': {'type': 'boolean'}},
        'required': ['hand_above_head', 'held_or_waved_across_frames', 'wearing_staff_uniform']},
    'alt': {'type': 'string', 'enum': ALT_CALL},
    'image_quality': {'type': 'string', 'enum': QUALITY},
    'verdict': {'type': 'string', 'enum': ['GOI', 'KHONG_GOI', 'KHONG_CHAC']},
    'reason': {'type': 'string'}},
    'required': ['checklist', 'alt', 'image_quality', 'verdict', 'reason']}

SCHEMA_TABLE = {'type': 'object', 'properties': {
    'checklist': {'type': 'object', 'properties': {
        'used_items_left': {'type': 'boolean'},
        'people_at_table': {'type': 'boolean'},
        'differs_from_clean_ref': {'type': 'boolean'}},
        'required': ['used_items_left', 'people_at_table']},
    'personal_belongings_present': {'type': 'boolean'},
    'image_quality': {'type': 'string', 'enum': QUALITY},
    'verdict': {'type': 'string', 'enum': ['CAN_DON', 'SACH', 'KHONG_CHAC']},
    'reason': {'type': 'string'}},
    'required': ['checklist', 'personal_belongings_present', 'image_quality', 'verdict', 'reason']}

SCHEMA = {'call': SCHEMA_CALL, 'needs_clearing': SCHEMA_TABLE}


def prompt_for(kind, table=None, has_ref=False):
    if kind == 'call':
        return PROMPT_CALL
    return PROMPT_TABLE.format(ban=table or '', ref=REF_SENTENCE if has_ref else '')


def _b64(jpeg):
    return base64.b64encode(jpeg).decode()


def build_parts(kind, images, table=None):
    """images: list[dict(role, jpeg)] theo thứ tự strip, overview, clean_ref. Mỗi phần ảnh có mức phân giải riêng."""
    has_ref = any(im['role'] == 'clean_ref' for im in images)
    parts = [{'text': prompt_for(kind, table, has_ref)}]
    for im in images:
        parts.append({'inline_data': {'mime_type': 'image/jpeg', 'data': _b64(im['jpeg'])},
                      'mediaResolution': {'level': f"MEDIA_RESOLUTION_{ROLE_RES[im['role']]}"}})
    return parts


def build_body(kind, images, table=None, drop=()):
    """Thân request generateContent (giống Gemini._body nhưng độ phân giải theo từng ảnh)."""
    parts = build_parts(kind, images, table)
    gc = {'responseMimeType': 'application/json',
          ('responseSchema' if 'jsonSchema' in drop else 'responseJsonSchema'): SCHEMA[kind]}
    if 'mediaResolution' in drop:
        # API không nhận mức theo từng ảnh: bỏ đi và đặt một mức chung MEDIUM cho cả request
        for p in parts:
            p.pop('mediaResolution', None)
        gc['mediaResolution'] = 'MEDIA_RESOLUTION_MEDIUM'
    if 'thinkingConfig' not in drop:
        gc['thinkingConfig'] = {'thinkingLevel': 'MINIMAL'}
    return {'contents': [{'role': 'user', 'parts': parts}], 'generationConfig': gc}


# ------------------------------------------------------------------ token, chi phí
PRICE_IN, PRICE_OUT, VND = 0.30 / 1e6, 2.50 / 1e6, 26000


def estimate_tokens(body, chars_per_token=4.0):
    """Token vào ≈ token ảnh theo mức phân giải + (chữ prompt + schema) / 4."""
    img = txt_chars = 0
    for p in body['contents'][0]['parts']:
        if 'text' in p:
            txt_chars += len(p['text'])
        else:
            lv = (p.get('mediaResolution') or {}).get('level', body['generationConfig'].get(
                'mediaResolution', 'MEDIA_RESOLUTION_HIGH'))
            img += IMG_TOKENS[lv.rsplit('_', 1)[-1]]
    gc = body['generationConfig']
    schema = gc.get('responseJsonSchema') or gc.get('responseSchema')
    schema_chars = len(json.dumps(schema, ensure_ascii=False, separators=(',', ':')))
    return dict(image=img, prompt_chars=txt_chars, schema_chars=schema_chars,
                text=round((txt_chars + schema_chars) / chars_per_token),
                total=img + round((txt_chars + schema_chars) / chars_per_token))


def cost_vnd(tok_in, tok_out):
    usd = tok_in * PRICE_IN + tok_out * PRICE_OUT
    return usd, usd * VND


# ------------------------------------------------------------------ luật quyết định
def decide(kind, d):
    """Trả (action, path). action: 'confirm' | 'reject' | 'unverified'.

    Gọi phục vụ: chỉ rút khi KHONG_GOI + ảnh ok + checklist khớp (có ít nhất một lý do bác trong checklist
    hoặc alt là một kiểu loại trừ cụ thể). Mọi trường hợp khác không chắc thì giữ cảnh báo, "Chưa xác minh".
    Cần dọn: chỉ giao việc khi CAN_DON + ảnh ok + còn đồ đã dùng + không người + không đồ cá nhân;
    chỉ huỷ khi SACH + ảnh ok + không còn đồ đã dùng + không có người.
    """
    v = d.get('verdict')
    q = d.get('image_quality')
    c = d.get('checklist') or {}
    if kind == 'call':
        if v == 'GOI':
            return 'confirm', 'confirmed'
        if v == 'KHONG_GOI':
            if q != 'ok':
                return 'unverified', 'poor_image'
            alt = d.get('alt')
            has_reason = (c.get('hand_above_head') is False or c.get('held_or_waved_across_frames') is False
                          or c.get('wearing_staff_uniform') is True or (alt not in (None, 'none', 'khac')))
            return ('reject', 'rejected') if has_reason else ('unverified', 'inconsistent')
        return 'unverified', 'uncertain'
    # needs_clearing
    if q != 'ok' and v in ('CAN_DON', 'SACH'):
        return 'unverified', 'poor_image'
    if v == 'CAN_DON':
        if d.get('personal_belongings_present'):
            return 'unverified', 'belongings'
        if c.get('used_items_left') is True and c.get('people_at_table') is False:
            return 'confirm', 'confirmed'
        return 'unverified', 'inconsistent'
    if v == 'SACH':
        if c.get('used_items_left') is False and c.get('people_at_table') is False:
            return 'reject', 'rejected'
        return 'unverified', 'inconsistent'
    return 'unverified', 'uncertain'


PATH_VI = {'uncertain': 'Gemini không chắc', 'poor_image': 'ảnh kém', 'inconsistent': 'trả lời không khớp checklist',
           'belongings': 'còn đồ cá nhân, có thể khách ra ngoài tạm', 'timeout': 'Gemini quá hạn',
           'error': 'Gemini lỗi', 'breaker_open': 'tạm ngừng gọi Gemini sau nhiều lỗi liên tiếp'}


# ------------------------------------------------------------------ circuit breaker
class CircuitBreaker:
    """Sau `fails` lỗi liên tiếp thì mở (không gọi) trong `cooldown_s`, rồi cho thử đúng một lần (half-open)."""

    def __init__(self, fails=3, cooldown_s=60.0, clock=time.monotonic):
        self.fails, self.cooldown_s, self.clock = fails, cooldown_s, clock
        self.n = 0
        self.opened_at = None
        self.trial = False

    @property
    def state(self):
        if self.opened_at is None:
            return 'closed'
        return 'half_open' if self.clock() - self.opened_at >= self.cooldown_s else 'open'

    def allow(self):
        st = self.state
        if st == 'closed':
            return True
        if st == 'half_open' and not self.trial:
            self.trial = True          # chỉ một lời gọi thử
            return True
        return False

    def success(self):
        self.n, self.opened_at, self.trial = 0, None, False

    def failure(self):
        self.n += 1
        if self.trial or self.n >= self.fails:
            self.opened_at, self.trial = self.clock(), False


# ------------------------------------------------------------------ client
class GeminiV2(Gemini):
    async def verify(self, kind, images, table=None):
        """images: bytes (kiểu cũ: một crop) hoặc list[dict(role, jpeg)]. Trả dict từ Gemini + ms + action/path."""
        if isinstance(images, (bytes, bytearray)):
            images = [{'role': 'strip', 'jpeg': bytes(images)}]
        t0 = time.perf_counter()
        last = None
        for _ in range(4):
            body = build_body(kind, images, table, self.drop)
            r = await self.client.post(f'https://generativelanguage.googleapis.com/v1beta/models/'
                                       f'{self.model}:generateContent', json=body,
                                       headers={'x-goog-api-key': self.key})
            if r.status_code == 200:
                d = _parse_json(_text(r.json()))
                break
            msg = r.text[:400]
            last = f'HTTP {r.status_code}: {msg}'
            low = msg.lower()
            if r.status_code == 400 and 'resolution' in low and 'mediaResolution' not in self.drop:
                self.drop.add('mediaResolution')
            elif r.status_code == 400 and 'thinking' in low and 'thinkingConfig' not in self.drop:
                self.drop.add('thinkingConfig')
            elif r.status_code == 400 and 'responsejsonschema' in low.replace('_', '') \
                    and 'jsonSchema' not in self.drop:
                self.drop.add('jsonSchema')
            else:
                raise GeminiError(last)
        else:
            raise GeminiError(last)
        return normalize(d, int((time.perf_counter() - t0) * 1000))


def normalize(d, ms=None):
    d = dict(d)
    d['reason'] = str(d.get('reason') or '')[:120]
    d['ms'] = ms
    return d


# ------------------------------------------------------------------ Hub
class HubV2(Hub):
    """Hub với: nhiều ảnh mỗi sự kiện, timeout, circuit breaker, luật enum, trạng thái 'unverified'."""

    VERIFY_TIMEOUT_S = 2.5

    def __init__(self, data_dir, gemini, clock=time.monotonic, timeout_s=None):
        super().__init__(data_dir, gemini)
        self.media = {}     # alert id -> list[dict(role, jpeg)]
        self.breaker = CircuitBreaker(3, 60.0, clock)
        if timeout_s is not None:
            self.VERIFY_TIMEOUT_S = timeout_s

    def edge_event(self, ev):
        aid = super().edge_event(ev)
        if aid and aid not in self.media:
            imgs = list(ev.get('images') or [])
            if not imgs and ev.get('crop_jpeg'):
                imgs = [{'role': 'strip', 'jpeg': ev['crop_jpeg']}]
            self.media[aid] = imgs
        return aid

    def _unverified(self, a, path, detail=''):
        a['verify'].update(state='unverified', path=path, reason=detail or PATH_VI.get(path, path))
        if a['status'] == 'verifying':          # việc đang giữ (cần dọn): vẫn giao cho nhân viên
            a['status'] = 'open'
            self._assign(a)
        self.add_log('verify', f'Chưa xác minh {where_l(a["table"], a["camera"])} {KIND_VI[a["kind"]]}: '
                               f'{PATH_VI.get(path, path)}', a['table'], a['camera'], a['id'])
        self._pub_alert(self._public(a))

    async def _verify(self, aid):
        a = self.alerts.get(aid)
        if a is None:
            return
        await asyncio.sleep(0)   # để edge_event lưu xong ảnh
        if not self.breaker.allow():
            return self._unverified(a, 'breaker_open')
        imgs = self.media.get(aid) or [{'role': 'strip', 'jpeg': self.crops[aid]}]
        try:
            r = await asyncio.wait_for(self.gemini.verify(a['kind'], imgs, a['table']), self.VERIFY_TIMEOUT_S)
        except asyncio.TimeoutError:
            self.breaker.failure()
            return self._unverified(a, 'timeout', f'Gemini quá {self.VERIFY_TIMEOUT_S:g} s')
        except Exception as e:  # lỗi mạng, lỗi API, JSON hỏng
            self.breaker.failure()
            return self._unverified(a, 'error', f'Gemini lỗi: {str(e)[:120]}')
        self.breaker.success()
        action, path = decide(a['kind'], r)
        a['verify'].update(verdict=r.get('verdict'), image_quality=r.get('image_quality'),
                           checklist=r.get('checklist'), reason=r.get('reason'), ms=r.get('ms'), path=path)
        if action == 'unverified':
            return self._unverified(a, path, r.get('reason') or '')
        if action == 'confirm':
            a['verify']['state'] = 'confirmed'
            extra = ''
            if a['status'] == 'verifying':
                a['status'] = 'open'
                s = self._assign(a)
                extra = f', giao cho {s["name"]}' if s else ''
            self.add_log('verify', f'Gemini xác nhận: {where_l(a["table"], a["camera"])} {KIND_VI[a["kind"]]}{extra}',
                         a['table'], a['camera'], aid)
        else:  # reject
            a['verify']['state'] = 'rejected'
            if a['status'] in ('verifying', 'open'):
                self._close(a, 'cancelled', 'gemini', f'Gemini: {r.get("reason") or "báo nhầm"}', publish=False)
            else:
                self.add_log('verify', f'Gemini cho là báo nhầm ({r.get("reason")}), nhưng nhân viên đã nhận việc',
                             a['table'], a['camera'], aid)
        self._pub_alert(self._public(a))


def redact(body):
    """Bản để đọc: thay base64 bằng cỡ ảnh."""
    b = copy.deepcopy(body)
    for p in b['contents'][0]['parts']:
        if 'inline_data' in p:
            n = len(base64.b64decode(p['inline_data']['data']))
            p['inline_data']['data'] = f'<JPEG {n} byte, base64>'
    return b
