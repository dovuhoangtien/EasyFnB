"""Gọi Gemini qua REST (generateContent): kiểm tra ảnh cắt, trả lời câu hỏi về ca, viết tóm tắt ca.

Đặt biến môi trường GEMINI_API_KEY (không bao giờ ghi khoá vào code). Đổi model bằng GEMINI_MODEL.

Thử nhanh khoá và model:
    python -m server.gemini                 # gọi một câu chữ
    python -m server.gemini anh.jpg call    # kiểm tra một ảnh cắt (call hoặc needs_clearing)
"""
import asyncio
import base64
import json
import os
import re
import sys
import time

import httpx

URL = 'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'

# Mỗi request xác minh gồm nhiều ảnh, mỗi ảnh một vai trò và một mức phân giải riêng:
#   strip     dải 2x2 bốn khung quanh sự kiện (crop người hoặc bàn)   MEDIUM (~560 token)
#   overview  toàn cảnh thu nhỏ, khung đỏ quanh người/bàn cần xét       LOW    (~280 token)
#   clean_ref (chỉ "cần dọn") cùng bàn lúc sạch                         LOW    (~280 token)
#   crop      (đường lui) một ảnh cắt lúc báo, khi gói ảnh không tới kịp  MEDIUM
ROLE_RES = {'strip': 'MEDIUM', 'overview': 'LOW', 'clean_ref': 'LOW', 'crop': 'MEDIUM'}
LOAI_TRU_GOI = ('vươn vai, vuốt hoặc chỉnh tóc, gãi đầu, chỉnh kính hoặc mũ, uống hoặc ăn, nâng ly chúc, '
                'nghe hoặc chụp điện thoại, chỉ tay khi nói chuyện, chống cằm, vẫy chào bạn cùng bàn, '
                'nhân viên (đồng phục, bưng khay)')
DO_CUA_QUAN = 'lọ gia vị, hộp giấy ăn, ống đũa, menu, ly úp sẵn'
VERIFY_PROMPT = {
    'call': (
        'Kiểm tra cảnh báo từ camera quán ăn. Ảnh 1: 4 khung trong 1,5 giây (trái sang phải, trên xuống dưới), '
        'cắt quanh MỘT người. Ảnh 2: toàn cảnh, khung đỏ là người đó. Chỉ xét người trong khung đỏ.\n'
        'GOI: giơ tay ngang hoặc trên đầu, hướng ra quán để gọi nhân viên, giữ hoặc vẫy qua ít nhất 2 khung.\n'
        f'KHONG_GOI nếu là: {LOAI_TRU_GOI}.\n'
        'KHONG_CHAC: ảnh không đủ rõ để kết luận. Không đoán.\n'
        'Điền checklist trước, rồi verdict. reason: tiếng Việt, tối đa 12 chữ.'
    ),
    'needs_clearing': (
        'Kiểm tra cảnh báo "bàn cần dọn" từ camera quán ăn. Ảnh 1: 4 khung trong 1,5 giây cắt quanh bàn {ban}. '
        'Ảnh 2: toàn cảnh, khung đỏ là bàn đó.{ref} Chỉ xét bàn trong khung đỏ.\n'
        'CAN_DON: không ai ngồi, còn chén đĩa, ly đã dùng, thức ăn thừa, giấy bẩn.\n'
        f'SACH: không còn đồ đã dùng. Đồ của quán không tính: {DO_CUA_QUAN}.\n'
        'personal_belongings_present: túi, điện thoại, áo khoác, ví của khách còn trên bàn hoặc ghế.\n'
        'KHONG_CHAC: ảnh không đủ rõ. Không đoán.\n'
        'Điền checklist trước, rồi verdict. reason: tiếng Việt, tối đa 12 chữ.'
    ),
}
REF_SENTENCE = ' Ảnh 3: cùng bàn lúc sạch; chỉ tính đồ KHÔNG có trong ảnh 3.'
# Đường lui khi gói ảnh từ camera không tới kịp: chỉ có một ảnh cắt lúc báo. Cùng schema, cùng luật quyết định.
VERIFY_PROMPT_ONE = {
    'call': (
        'Kiểm tra cảnh báo từ camera quán ăn. Chỉ có 1 ảnh cắt quanh MỘT người, người cần xét ở giữa ảnh. '
        'Vì chỉ có 1 khung, held_or_waved_across_frames điền giống hand_above_head.\n'
        'GOI: giơ tay ngang hoặc trên đầu, hướng ra quán để gọi nhân viên.\n'
        + VERIFY_PROMPT['call'].split('\n', 2)[2]
    ),
    'needs_clearing': (
        'Kiểm tra cảnh báo "bàn cần dọn" từ camera quán ăn. Chỉ có 1 ảnh cắt quanh bàn {ban}.\n'
        + VERIFY_PROMPT['needs_clearing'].split('\n', 1)[1]
    ),
}
QUALITY = ['ok', 'toi', 'mo', 'bi_che', 'qua_nho']
ALT_CALL = ['vuon_vai', 'chinh_toc', 'uong_an', 'nang_ly', 'dien_thoai', 'chi_tay', 'vay_ban', 'nhan_vien',
            'khac', 'none']
VERIFY_SCHEMA = {
    'call': {'type': 'object', 'properties': {
        'checklist': {'type': 'object', 'properties': {
            'hand_above_head': {'type': 'boolean'},
            'held_or_waved_across_frames': {'type': 'boolean'},
            'wearing_staff_uniform': {'type': 'boolean'}},
            'required': ['hand_above_head', 'held_or_waved_across_frames', 'wearing_staff_uniform']},
        'alt': {'type': 'string', 'enum': ALT_CALL},
        'image_quality': {'type': 'string', 'enum': QUALITY},
        'verdict': {'type': 'string', 'enum': ['GOI', 'KHONG_GOI', 'KHONG_CHAC']},
        'reason': {'type': 'string'}},
        'required': ['checklist', 'alt', 'image_quality', 'verdict', 'reason']},
    'needs_clearing': {'type': 'object', 'properties': {
        'checklist': {'type': 'object', 'properties': {
            'used_items_left': {'type': 'boolean'},
            'people_at_table': {'type': 'boolean'},
            'differs_from_clean_ref': {'type': 'boolean'}},
            'required': ['used_items_left', 'people_at_table']},
        'personal_belongings_present': {'type': 'boolean'},
        'image_quality': {'type': 'string', 'enum': QUALITY},
        'verdict': {'type': 'string', 'enum': ['CAN_DON', 'SACH', 'KHONG_CHAC']},
        'reason': {'type': 'string'}},
        'required': ['checklist', 'personal_belongings_present', 'image_quality', 'verdict', 'reason']},
}
ANSWER_SCHEMA = {'type': 'object', 'properties': {
    'answer': {'type': 'string'},
    'refs': {'type': 'array', 'items': {'type': 'object', 'properties': {
        'alert_id': {'type': 'string'}, 'table': {'type': 'string'}, 'time': {'type': 'string'}}}}},
    'required': ['answer']}


class GeminiError(RuntimeError):
    pass


class Gemini:
    ten = 'Gemini'

    def __init__(self):
        self.key = os.environ.get('GEMINI_API_KEY', '').strip()
        self.model = os.environ.get('GEMINI_MODEL', 'gemini-3.5-flash-lite')
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(25.0, connect=10.0))
        # trường nào API không nhận thì bỏ đi ở các lần sau (đổi phiên bản API vẫn chạy được)
        self.drop = set()

    @property
    def enabled(self):
        return bool(self.key)

    def _body(self, parts, schema, image):
        gc = {}
        if schema is not None:
            gc['responseMimeType'] = 'application/json'
            gc['responseSchema' if 'jsonSchema' in self.drop else 'responseJsonSchema'] = schema
        if image and 'mediaResolution' in self.drop:
            # API không nhận mức phân giải theo từng ảnh: bỏ ở từng ảnh, đặt một mức chung
            parts = [{k: v for k, v in p.items() if k != 'mediaResolution'} for p in parts]
            gc['mediaResolution'] = 'MEDIA_RESOLUTION_MEDIUM'
        if 'thinkingConfig' not in self.drop:
            gc['thinkingConfig'] = {'thinkingLevel': 'MINIMAL'}
        return {'contents': [{'role': 'user', 'parts': parts}], 'generationConfig': gc}

    async def generate(self, parts, schema=None, image=False):
        if not self.enabled:
            raise GeminiError('chưa đặt GEMINI_API_KEY')
        last = None
        for _ in range(4):
            body = self._body(parts, schema, image)
            r = await self.client.post(URL.format(model=self.model), json=body,
                                       headers={'x-goog-api-key': self.key})
            if r.status_code == 200:
                return _text(r.json())
            msg = r.text[:400]
            last = f'HTTP {r.status_code}: {msg}'
            if r.status_code != 400:
                break
            # 400 vì một trường cấu hình: bỏ trường đó rồi thử lại
            if 'thinking' in msg.lower() and 'thinkingConfig' not in self.drop:
                self.drop.add('thinkingConfig')
            elif 'resolution' in msg.lower() and 'mediaResolution' not in self.drop:
                self.drop.add('mediaResolution')
            elif ('response_json_schema' in msg.lower() or 'responsejsonschema' in msg.lower()) \
                    and 'jsonSchema' not in self.drop:
                self.drop.add('jsonSchema')
            else:
                break
        raise GeminiError(last)

    async def json(self, parts, schema, image=False):
        return _parse_json(await self.generate(parts, schema, image))

    async def verify(self, kind, images, table=None):
        """images: list[dict(role, jpeg)] (strip, overview, clean_ref; hoặc một 'crop') hoặc bytes (một crop).
        Trả JSON của Gemini (verdict, checklist, image_quality, ...) kèm ms. Quyết định nằm ở decide()."""
        if isinstance(images, (bytes, bytearray)):
            images = [{'role': 'crop', 'jpeg': bytes(images)}]
        t0 = time.perf_counter()
        package = any(im['role'] == 'strip' for im in images)
        prompt = (VERIFY_PROMPT if package else VERIFY_PROMPT_ONE)[kind]
        if kind == 'needs_clearing':
            has_ref = package and any(im['role'] == 'clean_ref' for im in images)
            prompt = prompt.format(ban=table or '', ref=REF_SENTENCE if has_ref else '')
        parts = [{'text': prompt}]
        for im in images:
            parts.append({'inline_data': {'mime_type': 'image/jpeg', 'data': base64.b64encode(im['jpeg']).decode()},
                          'mediaResolution': {'level': f"MEDIA_RESOLUTION_{ROLE_RES.get(im['role'], 'LOW')}"}})
        d = await self.json(parts, VERIFY_SCHEMA[kind], image=True)
        d['reason'] = str(d.get('reason') or '')[:120]
        d['ms'] = int((time.perf_counter() - t0) * 1000)
        return d

    async def answer(self, question, context):
        prompt = (
            'Bạn là trợ lý của quản lý một quán ăn. Dưới đây là nhật ký ca hôm nay do hệ thống camera AI ghi lại '
            '(giờ Việt Nam). Trả lời câu hỏi bằng tiếng Việt, ngắn gọn, đúng số liệu trong nhật ký; '
            'nói rõ khi nhật ký không đủ thông tin. Liệt kê trong refs các sự kiện đã dùng (mã [aN], bàn, giờ).\n\n'
            f'SỐ LIỆU CA:\n{context["report"]}\n\nNHẬT KÝ:\n{context["log"] or "(chưa có sự kiện)"}\n\n'
            f'CÂU HỎI: {question}')
        return await self.json([{'text': prompt}], ANSWER_SCHEMA)

    async def summary(self, report, log):
        prompt = (
            'Viết tóm tắt cuối ca cho chủ quán ăn, tiếng Việt, 5 đến 8 câu ngắn, giọng trung tính. '
            'Nêu: số lần khách gọi, thời gian phản hồi, bàn hoặc giờ bận nhất, báo nhầm đã được lọc, '
            'việc bị chậm (chuyển người), và một gợi ý cụ thể cho ca sau. Chỉ dùng số liệu có trong dữ liệu.\n\n'
            f'SỐ LIỆU CA:\n{report}\n\nNHẬT KÝ:\n{log or "(chưa có sự kiện)"}')
        return (await self.generate([{'text': prompt}])).strip()


def decide(kind, d):
    """Luật quyết định từ JSON của Gemini. Trả (action, path); action: confirm | reject | unverified.
    Gọi phục vụ: chỉ rút khi KHONG_GOI + ảnh ok + checklist có lý do bác. Cần dọn: chỉ giao việc khi
    CAN_DON + ảnh ok + còn đồ đã dùng + không người + không đồ cá nhân; chỉ huỷ khi SACH + ok + checklist khớp.
    Không dùng confidence."""
    v, q, c = d.get('verdict'), d.get('image_quality'), d.get('checklist') or {}
    if kind == 'call':
        if v == 'GOI':
            return 'confirm', 'confirmed'
        if v == 'KHONG_GOI':
            if q != 'ok':
                return 'unverified', 'poor_image'
            why = (c.get('hand_above_head') is False or c.get('held_or_waved_across_frames') is False
                   or c.get('wearing_staff_uniform') is True or d.get('alt') not in (None, 'none', 'khac'))
            return ('reject', 'rejected') if why else ('unverified', 'inconsistent')
        return 'unverified', 'uncertain'
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


def _text(resp):
    try:
        parts = resp['candidates'][0]['content']['parts']
    except (KeyError, IndexError, TypeError):
        reason = (resp.get('promptFeedback') or {}).get('blockReason') if isinstance(resp, dict) else None
        raise GeminiError(f'Gemini không trả nội dung{f" ({reason})" if reason else ""}')
    text = ''.join(p.get('text', '') for p in parts if not p.get('thought'))
    if not text:
        raise GeminiError('Gemini trả về rỗng')
    return text


def _parse_json(text):
    t = text.strip()
    t = re.sub(r'^```(?:json)?\s*|\s*```$', '', t)
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        m = re.search(r'\{.*\}', t, re.S)
        if m:
            return json.loads(m.group(0))
        raise GeminiError(f'Gemini trả về không phải JSON: {text[:120]}')


async def _main():
    g = Gemini()
    if not g.enabled:
        sys.exit('Chưa đặt GEMINI_API_KEY. Ví dụ (PowerShell): $env:GEMINI_API_KEY = "<khoá của bạn>"')
    print('model:', g.model)
    if len(sys.argv) >= 2:
        kind = sys.argv[2] if len(sys.argv) > 2 else 'call'
        r = await g.verify(kind, open(sys.argv[1], 'rb').read())
        print(r, decide(kind, r))
    else:
        print(await g.generate([{'text': 'Trả lời đúng một chữ: xin chào bằng tiếng Việt.'}]))
    print('bỏ trường:', g.drop or 'không')


if __name__ == '__main__':
    asyncio.run(_main())
