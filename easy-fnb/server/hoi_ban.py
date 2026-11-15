"""Khớp bàn khi camera không chắc: camera gửi ảnh một người đang ngồi giữa 2-3 bàn sát nhau, máy chủ hỏi Gemini
Decision người đó ngồi ở bàn nào (POST /api/edge/table-ask).

Máy chủ chỉ trả xác suất; camera tự quyết (chỉ chốt khi một bàn từ 0,7 trở lên và bàn khác từ 0,3 trở xuống).
Decision tắt, lỗi, quá giờ, hỏi quá dày: trả {ok: false, reason}; camera giữ kết quả hình học.
"""
import asyncio
import time

from .gemini import P_NO

GAP_S = 8.0          # mỗi camera tối đa một câu mỗi bấy nhiêu giây (camera tự giới hạn 10 s; đây là chốt chặn thêm)
TIMEOUT_S = 4.0      # Decision đo được 0,6-1,1 s; quá mức này thì bỏ
COLORS = ('cam', 'xanh dương', 'xanh lá')
MAX_JPEG = 600 * 1024


class HoiBan:
    def __init__(self, hub, breaker, clock=time.monotonic, timeout_s=TIMEOUT_S):
        self.hub, self.breaker, self.clock, self.timeout_s = hub, breaker, clock, timeout_s
        self.last = {}      # camera -> lúc hỏi gần nhất
        self.n = 0          # số lần đã gọi Gemini (để đo chi phí)

    async def ask(self, camera, jpeg, tables):
        """tables: [{table, color}] 2-3 bàn. Trả dict(ok, probs, seated, ms, tokens) hoặc dict(ok=False, reason)."""
        if not isinstance(camera, str) or not camera:
            raise ValueError('cần camera (chuỗi)')
        if not isinstance(tables, list) or not 2 <= len(tables) <= 3:
            raise ValueError('cần 2-3 bàn')
        pairs = []
        for t in tables:
            name, color = (t or {}).get('table'), (t or {}).get('color')
            if not isinstance(name, str) or not name or color not in COLORS:
                raise ValueError(f'bàn sai dạng: {t!r}')
            pairs.append((name, color))
        if not jpeg or len(jpeg) > MAX_JPEG:
            raise ValueError('ảnh rỗng hoặc quá lớn')
        g = self.hub.gemini
        if not (g.enabled and getattr(g, 'decision', False) and hasattr(g, 'table_ask')):
            return dict(ok=False, reason='decision_off')
        now = self.clock()
        if now - self.last.get(camera, -1e9) < GAP_S:
            return dict(ok=False, reason='too_often')
        if not self.breaker.allow():
            return dict(ok=False, reason='breaker_open')
        self.last[camera] = now
        self.n += 1
        try:
            r = await asyncio.wait_for(g.table_ask(jpeg, pairs), self.timeout_s)
        except Exception as e:
            self.breaker.failure()
            self.hub.timeline.add('table_ask', camera=camera, error=f'{type(e).__name__}: {e}'[:160])
            return dict(ok=False, reason='timeout' if isinstance(e, asyncio.TimeoutError) else 'error')
        self.breaker.success()
        self.hub.timeline.add('table_ask', camera=camera, probs=r['probs'], seated=r.get('seated'),
                              ms=r.get('ms'), tokens=r.get('tokens'))
        if r.get('seated') is not None and r['seated'] <= P_NO:
            return dict(ok=False, reason='not_seated', probs=r['probs'], seated=r['seated'], ms=r.get('ms'))
        return dict(ok=True, probs=r['probs'], seated=r.get('seated'), ms=r.get('ms'), tokens=r.get('tokens'))
