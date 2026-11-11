"""Gọi kie.ai (OpenAI Responses API): kiểm tra ảnh cắt, trả lời câu hỏi về ca, viết tóm tắt ca.

Cùng giao diện với `server.gemini.Gemini` (`enabled`, `model`, `ten`, `verify`, `answer`, `summary`)
nên máy chủ đổi nhà cung cấp bằng biến môi trường, phần còn lại không phải sửa. Prompt, schema và
luật quyết định (`gemini.decide`) dùng lại của Gemini để kết quả hai bên so sánh được.

Đặt `KIE_API_KEY` (không bao giờ ghi khoá vào code). Đổi model bằng `KIE_MODEL`.

Thử nhanh:
    python -m server.llm                 # gọi một câu chữ
    python -m server.llm anh.jpg call    # kiểm tra một ảnh cắt (call hoặc needs_clearing)
"""
import base64
import json
import os
import re
import sys
import time

import httpx

from .gemini import (ANSWER_SCHEMA, REF_SENTENCE, VERIFY_PROMPT, VERIFY_PROMPT_ONE, VERIFY_SCHEMA,
                     GeminiError)

URL = 'https://api.kie.ai/openai/v1/responses'
CHI_JSON = ' Chỉ trả một đối tượng JSON hợp lệ, không thêm chữ nào ngoài JSON.'


class LlmError(GeminiError):
    """Lỗi của kie.ai. Kế thừa GeminiError để chỗ nào đang bắt lỗi Gemini vẫn bắt được."""
    pass


class Llm:
    ten = 'kie.ai'

    def __init__(self):
        self.key = os.environ.get('KIE_API_KEY', '').strip()
        self.model = os.environ.get('KIE_MODEL', 'deepseek-v4-1-flash')
        self.effort = os.environ.get('KIE_EFFORT', 'minimal')   # model luôn suy luận; để thấp nhất cho nhanh
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0))
        self.drop = set()   # trường nào API không nhận thì bỏ ở các lần sau (đổi model vẫn chạy được)

    @property
    def enabled(self):
        return bool(self.key)

    async def _goi(self, noi_dung, max_tokens=400, schema=None):
        """Gửi một lượt (chữ + ảnh) và trả phần chữ. Đọc được cả SSE lẫn JSON thường.
        Có `schema` thì ép JSON đúng dạng bằng text.format của Responses API; API không nhận thì
        bỏ trường đó, lần sau nhét schema vào lời nhắc (xem `verify`, `answer`)."""
        if not self.enabled:
            raise LlmError('chưa đặt KIE_API_KEY')
        body = dict(model=self.model, input=[{'role': 'user', 'content': noi_dung}],
                    max_output_tokens=max_tokens, reasoning={'effort': self.effort})
        if schema is not None and 'json_schema' not in self.drop:
            body['text'] = {'format': {'type': 'json_schema', 'name': 'kq', 'schema': schema}}
        headers = {'Authorization': f'Bearer {self.key}', 'Content-Type': 'application/json'}
        last = None
        for lan in range(2):
            try:
                async with self.client.stream('POST', URL, json=body, headers=headers) as r:
                    if r.status_code != 200:
                        raw = (await r.aread()).decode('utf-8', 'replace')[:300]
                        last = f'HTTP {r.status_code}: {raw}'
                        # API từ chối cách ép JSON: bỏ trường, lần sau nhét schema vào lời nhắc
                        if r.status_code == 400 and 'json_schema' not in self.drop and 'text' in body \
                                and ('format' in raw or 'text' in raw or 'schema' in raw):
                            self.drop.add('json_schema')
                            body.pop('text', None)
                            continue
                        if r.status_code in (429, 500, 502, 503) and lan == 0:
                            continue
                        raise LlmError(last)
                    ctype = r.headers.get('content-type', '')
                    if 'event-stream' not in ctype:
                        return _text(json.loads(await r.aread()))
                    ra, hong = [], None
                    async for line in r.aiter_lines():
                        if not line.startswith('data:'):
                            continue
                        payload = line[5:].strip()
                        if not payload or payload == '[DONE]':
                            continue
                        try:
                            ev = json.loads(payload)
                        except json.JSONDecodeError:
                            continue
                        ty = ev.get('type') or ''
                        if ty == 'response.output_text.delta':
                            ra.append(ev.get('delta') or '')
                        elif ty == 'response.completed':
                            break
                        elif ty in ('response.failed', 'error'):
                            hong = json.dumps(ev.get('response') or ev, ensure_ascii=False)[:300]
                            break
                    if hong:
                        raise LlmError(f'kie.ai báo lỗi: {hong}')
                    text = ''.join(ra)
                    if text:
                        return text
                    last = 'kie.ai trả về rỗng'
            except httpx.HTTPError as e:
                last = f'{type(e).__name__}: {e}'
                if lan:
                    break
        raise LlmError(last or 'kie.ai không trả lời')

    async def generate(self, noi_dung, max_tokens=400):
        return await self._goi(noi_dung, max_tokens)

    async def json(self, noi_dung, max_tokens=400, schema=None):
        return _parse_json(await self._goi(noi_dung, max_tokens, schema))

    async def verify(self, kind, images, table=None):
        """images: list[dict(role, jpeg)] (strip, overview, clean_ref; hoặc một 'crop') hoặc bytes (một crop).
        Trả JSON cùng dạng Gemini (verdict, checklist, image_quality, ...) kèm ms. Quyết định nằm ở decide()."""
        if isinstance(images, (bytes, bytearray)):
            images = [{'role': 'crop', 'jpeg': bytes(images)}]
        t0 = time.perf_counter()
        package = any(im['role'] == 'strip' for im in images)
        prompt = (VERIFY_PROMPT if package else VERIFY_PROMPT_ONE)[kind]
        if kind == 'needs_clearing':
            has_ref = package and any(im['role'] == 'clean_ref' for im in images)
            prompt = prompt.format(ban=table or '', ref=REF_SENTENCE if has_ref else '')
        if 'json_schema' in self.drop:   # API không ép JSON được: nói rõ dạng cần trả
            prompt += ' Trả JSON đúng dạng: ' + json.dumps(VERIFY_SCHEMA[kind], ensure_ascii=False)
        noi_dung = [{'type': 'input_text', 'text': prompt + CHI_JSON}]
        for im in images:
            # Không đặt được mức phân giải theo từng ảnh như Gemini; ảnh đã được camera thu nhỏ từ trước.
            noi_dung.append({'type': 'input_image',
                              'image_url': 'data:image/jpeg;base64,' + base64.b64encode(im['jpeg']).decode()})
        d = await self.json(noi_dung, max_tokens=500, schema=VERIFY_SCHEMA[kind])
        d['reason'] = str(d.get('reason') or '')[:120]
        d['ms'] = int((time.perf_counter() - t0) * 1000)
        return d

    async def answer(self, question, context):
        prompt = (
            'Bạn là trợ lý của quản lý một quán ăn. Dưới đây là nhật ký ca hôm nay do hệ thống camera AI ghi lại '
            '(giờ Việt Nam). Trả lời câu hỏi bằng tiếng Việt, ngắn gọn, đúng số liệu trong nhật ký; '
            'nói rõ khi nhật ký không đủ thông tin. Liệt kê trong refs các sự kiện đã dùng (mã [aN], bàn, giờ).\n\n'
            f'SỐ LIỆU CA:\n{context["report"]}\n\nNHẬT KÝ:\n{context["log"] or "(chưa có sự kiện)"}\n\n'
            f'CÂU HỎI: {question}'
        )
        if 'json_schema' in self.drop:
            prompt += ' Trả JSON đúng dạng: ' + json.dumps(ANSWER_SCHEMA, ensure_ascii=False)
        return await self.json([{'type': 'input_text', 'text': prompt}], max_tokens=700, schema=ANSWER_SCHEMA)

    async def summary(self, report, log):
        prompt = (
            'Viết tóm tắt cuối ca cho chủ quán ăn, tiếng Việt, 5 đến 8 câu ngắn, giọng trung tính. '
            'Nêu: số lần khách gọi, thời gian phản hồi, bàn hoặc giờ bận nhất, báo nhầm đã được lọc, '
            'việc bị chậm (chuyển người), và một gợi ý cụ thể cho ca sau. Chỉ dùng số liệu có trong dữ liệu.\n\n'
            f'SỐ LIỆU CA:\n{report}\n\nNHẬT KÝ:\n{log or "(chưa có sự kiện)"}'
        )
        return (await self._goi([{'type': 'input_text', 'text': prompt}], max_tokens=800)).strip()


def _text(d):
    """Phần chữ của một phản hồi Responses API không streaming."""
    ra = []
    for item in d.get('output') or []:
        if item.get('type') != 'message':
            continue
        for p in item.get('content') or []:
            if p.get('type') in ('output_text', 'text'):
                ra.append(p.get('text') or '')
    if not ra and d.get('output_text'):
        ra.append(d['output_text'])
    if not ra:
        raise LlmError(f'kie.ai không trả nội dung: {json.dumps(d, ensure_ascii=False)[:200]}')
    return ''.join(ra)


def _parse_json(text):
    t = text.strip()
    t = re.sub(r'^```(?:json)?\s*|\s*```$', '', t)
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        m = re.search(r'\{.*\}', t, re.S)
        if m:
            return json.loads(m.group(0))
        raise LlmError(f'kie.ai trả về không phải JSON: {text[:120]}')


async def _main():
    llm = Llm()
    if not llm.enabled:
        sys.exit('Chưa đặt KIE_API_KEY. Ví dụ (PowerShell): $env:KIE_API_KEY = "<khoá của bạn>"')
    print('model:', llm.model)
    if len(sys.argv) >= 2:
        kind = sys.argv[2] if len(sys.argv) > 2 else 'call'
        r = await llm.verify(kind, open(sys.argv[1], 'rb').read())
        from .gemini import decide
        print(r, decide(kind, r))
    else:
        print(await llm.generate([{'type': 'input_text', 'text': 'Trả lời đúng một chữ: xin chào bằng tiếng Việt.'}]))


if __name__ == '__main__':
    import asyncio
    asyncio.run(_main())
