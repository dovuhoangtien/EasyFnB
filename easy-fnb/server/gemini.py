"""Gọi Gemini qua REST (generateContent): kiểm tra ảnh cắt, trả lời câu hỏi về ca, viết tóm tắt ca.

Đặt biến môi trường GEMINI_API_KEY (không bao giờ ghi khoá vào code). Đổi model bằng GEMINI_MODEL.
Đặt GEMINI_VERIFY_MODEL=gemini-decision-1 thì việc kiểm tra ảnh dùng Gemini Decision (Decisions API):
hỏi vài câu có/không, nhận xác suất, quyết định theo ngưỡng. Xem DECISION_QUESTIONS và _decide_probs().

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

# ---------------------------------------------------------------- Gemini Decision (Decisions API)
# Đặt GEMINI_VERIFY_MODEL=gemini-decision-1 thì việc kiểm tra ảnh đi đường này thay cho generateContent:
# gửi ảnh kèm vài câu hỏi có/không, nhận về xác suất "có" (0,01 đến 0,99) cho từng câu, không có chữ.
# Trợ lý và tóm tắt ca vẫn dùng GEMINI_MODEL.
DECISIONS_URL = 'https://generativelanguage.googleapis.com/v1beta/decisions'
P_YES, P_NO = 0.7, 0.3          # từ P_YES trở lên coi là "có", từ P_NO trở xuống coi là "không"; ở giữa là chưa chắc
Q_CLEAR = 'Ảnh có đủ sáng, đủ nét và không bị che khuất để trả lời chắc chắn các câu hỏi còn lại không?'
DECISION_QUESTIONS = {
    'call': {
        'hand_above_head': dict(
            instructions='Người cần xét có đang giơ tay ngang đầu hoặc cao hơn đầu, hướng ra quán để gọi nhân viên không?',
            criteria=dict(true_description='Giơ tay để gọi nhân viên.',
                          false_description=f'Không giơ tay, hoặc chỉ là: {LOAI_TRU_GOI}.')),
        'held_or_waved_across_frames': dict(
            instructions='Tay giơ có được giữ hoặc vẫy qua ít nhất 2 trong 4 khung của ảnh 1 không?'),
        'wearing_staff_uniform': dict(
            instructions='Người cần xét có phải nhân viên của quán (mặc đồng phục, bưng khay) không?'),
        'image_clear': dict(instructions=Q_CLEAR),
    },
    'needs_clearing': {
        'used_items_left': dict(
            instructions='Trên bàn cần xét có còn chén đĩa, ly đã dùng, thức ăn thừa hoặc giấy bẩn không? '
                         f'Đồ của quán không tính: {DO_CUA_QUAN}.'),
        'people_at_table': dict(instructions='Có người đang ngồi ở bàn cần xét không?'),
        'personal_belongings_present': dict(
            instructions='Có túi, điện thoại, áo khoác hoặc ví của khách còn trên bàn cần xét hoặc ghế của bàn đó không?'),
        'image_clear': dict(instructions=Q_CLEAR),
    },
}
# Câu mô tả ảnh gửi kèm: (loại việc, có gói ảnh đầy đủ hay chỉ một ảnh cắt)
DECISION_CONTEXT = {
    ('call', True): 'Camera quán ăn báo có khách gọi phục vụ. Ảnh 1: 4 khung trong 1,5 giây (trái sang phải, '
                    'trên xuống dưới), cắt quanh MỘT người. Ảnh 2: toàn cảnh, khung đỏ là người đó. '
                    'Chỉ xét người trong khung đỏ.',
    ('call', False): 'Camera quán ăn báo có khách gọi phục vụ. Chỉ có 1 ảnh cắt quanh MỘT người, '
                     'người cần xét ở giữa ảnh.',
    ('needs_clearing', True): 'Camera quán ăn báo bàn {ban} cần dọn. Ảnh 1: 4 khung trong 1,5 giây cắt quanh bàn đó. '
                              'Ảnh 2: toàn cảnh, khung đỏ là bàn đó.{ref} Chỉ xét bàn trong khung đỏ.',
    ('needs_clearing', False): 'Camera quán ăn báo bàn {ban} cần dọn. Chỉ có 1 ảnh cắt quanh bàn đó.',
}
Q_VI = {'hand_above_head': 'Giơ tay gọi', 'held_or_waved_across_frames': 'Giữ tay qua nhiều khung',
        'wearing_staff_uniform': 'Là nhân viên', 'used_items_left': 'Còn đồ đã dùng',
        'people_at_table': 'Còn người ngồi', 'personal_belongings_present': 'Còn đồ cá nhân',
        'image_clear': 'Ảnh đủ rõ'}
DECISION_VERDICT = {'call': {'confirm': 'GOI', 'reject': 'KHONG_GOI'},
                    'needs_clearing': {'confirm': 'CAN_DON', 'reject': 'SACH'}}


class GeminiError(RuntimeError):
    pass


class Gemini:
    ten = 'Gemini'

    def __init__(self):
        self.key = os.environ.get('GEMINI_API_KEY', '').strip()
        self.model = os.environ.get('GEMINI_MODEL', 'gemini-3.5-flash-lite')
        # model riêng cho việc kiểm tra ảnh; tên bắt đầu bằng "gemini-decision" thì gọi Decisions API
        self.verify_model = os.environ.get('GEMINI_VERIFY_MODEL', '').strip()
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(25.0, connect=10.0))
        # trường nào API không nhận thì bỏ đi ở các lần sau (đổi phiên bản API vẫn chạy được)
        self.drop = set()

    @property
    def enabled(self):
        return bool(self.key)

    @property
    def decision(self):
        """True khi việc kiểm tra ảnh dùng Gemini Decision (hỏi có/không, nhận xác suất)."""
        return self.verify_model.startswith('gemini-decision')

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
        if self.decision:
            return await self._verify_decision(kind, images, table)
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

    async def _verify_decision(self, kind, images, table):
        """Hỏi Gemini Decision các câu có/không của loại việc này trong một lượt. Trả cùng dạng với verify()
        (verdict, checklist, image_quality, reason, ms) kèm `probs` là xác suất "có" của từng câu."""
        if not self.enabled:
            raise GeminiError('chưa đặt GEMINI_API_KEY')
        t0 = time.perf_counter()
        package = any(im['role'] == 'strip' for im in images)
        has_ref = package and any(im['role'] == 'clean_ref' for im in images)
        text = DECISION_CONTEXT[(kind, package)].format(ban=table or '', ref=REF_SENTENCE if has_ref else '')
        blocks = [{'type': 'text', 'text': text}]
        for im in images:
            blocks.append({'type': 'image', 'mime_type': 'image/jpeg', 'data': base64.b64encode(im['jpeg']).decode(),
                           'resolution': ROLE_RES.get(im['role'], 'LOW').lower()})
        questions = {k: dict(type='noul', **q) for k, q in DECISION_QUESTIONS[kind].items()
                     if package or k != 'held_or_waved_across_frames'}     # một ảnh thì không hỏi "qua nhiều khung"
        r = await self.client.post(DECISIONS_URL, headers={'x-goog-api-key': self.key},
                                   json={'model': self.verify_model, 'input': blocks, 'questions': questions})
        if r.status_code != 200:
            raise GeminiError(f'HTTP {r.status_code}: {r.text[:400]}')
        resp = r.json()
        block = (resp.get('prompt_feedback') or {}).get('block_reason')
        if block:
            raise GeminiError(f'Gemini Decision từ chối ảnh ({block})')
        answers = resp.get('answers') or {}
        probs = {k: float(v['noul']) for k, v in answers.items()
                 if k in questions and isinstance(v, dict) and isinstance(v.get('noul'), (int, float))}
        if not probs:
            raise GeminiError('Gemini Decision không trả câu trả lời nào')
        action, _, key = _decide_probs(kind, probs)
        return dict(probs=probs, model=self.verify_model,
                    verdict=DECISION_VERDICT[kind].get(action, 'KHONG_CHAC'),
                    checklist={k: p >= 0.5 for k, p in probs.items() if k != 'image_clear'},
                    image_quality='ok' if probs.get('image_clear', 1.0) >= 0.5 else 'mo',
                    reason=f'{Q_VI[key]}: {probs[key]:.0%}' if key in probs else 'thiếu câu trả lời',
                    ms=int((time.perf_counter() - t0) * 1000))

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
    Không dùng confidence. Kết quả của Gemini Decision (có `probs`) thì quyết định theo ngưỡng xác suất."""
    if d.get('probs'):
        return _decide_probs(kind, d['probs'])[:2]
    v, q, c =d.get('verdict'), d.get('image_quality'), d.get('checklist') or {}
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


def _decide_probs(kind, p):
    """Luật quyết định theo xác suất "có" của từng câu hỏi. Trả (action, path, câu hỏi quyết định).
    Cùng tinh thần với decide(): chỉ bác khi khá chắc là nhầm; lưng chừng hay ảnh kém thì vẫn báo nhân viên."""
    if p.get('image_clear', 1.0) < 0.5:
        return 'unverified', 'poor_image', 'image_clear'
    if kind == 'call':
        hand, held, staff = p.get('hand_above_head'), p.get('held_or_waved_across_frames'), \
            p.get('wearing_staff_uniform', 0.0)
        if hand is None:
            return 'unverified', 'uncertain', 'hand_above_head'
        if staff >= P_YES:
            return 'reject', 'rejected', 'wearing_staff_uniform'
        if hand <= P_NO:
            return 'reject', 'rejected', 'hand_above_head'
        if held is not None and held <= P_NO:
            return 'reject', 'rejected', 'held_or_waved_across_frames'
        if hand < P_YES:
            return 'unverified', 'uncertain', 'hand_above_head'
        if staff >= 0.5:
            return 'unverified', 'uncertain', 'wearing_staff_uniform'
        if held is not None and held < 0.5:
            return 'unverified', 'uncertain', 'held_or_waved_across_frames'
        return 'confirm', 'confirmed', 'hand_above_head'
    used, people, bel = p.get('used_items_left'), p.get('people_at_table'), p.get('personal_belongings_present', 0.0)
    if used is None or people is None:
        return 'unverified', 'uncertain', 'used_items_left' if used is None else 'people_at_table'
    if people >= P_YES:
        return 'unverified', 'inconsistent', 'people_at_table'
    if people > P_NO:
        return 'unverified', 'uncertain', 'people_at_table'
    if used <= P_NO:
        return 'reject', 'rejected', 'used_items_left'
    if used < P_YES:
        return 'unverified', 'uncertain', 'used_items_left'
    if bel >= 0.5:
        return 'unverified', 'belongings', 'personal_belongings_present'
    return 'confirm', 'confirmed', 'used_items_left'


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
    print('model:', g.model, '| kiểm tra ảnh:', g.verify_model or g.model)
    if len(sys.argv) >= 2:
        kind = sys.argv[2] if len(sys.argv) > 2 else 'call'
        r = await g.verify(kind, open(sys.argv[1], 'rb').read())
        print(r, decide(kind, r))
    else:
        print(await g.generate([{'text': 'Trả lời đúng một chữ: xin chào bằng tiếng Việt.'}]))
    print('bỏ trường:', g.drop or 'không')


if __name__ == '__main__':
    asyncio.run(_main())
