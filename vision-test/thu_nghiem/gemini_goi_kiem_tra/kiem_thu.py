"""T4 phần B: kiểm luật quyết định, timeout, circuit breaker trên Hub thật (server/hub.py) với Gemini giả.

Chạy:  python kiem_thu.py            (unittest, ~10 s, không cần mạng, không cần key)
"""
import asyncio
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import xac_minh_v2 as xm  # noqa: E402
from server.gemini import GeminiError  # noqa: E402

JPEG = b'\xff\xd8\xff\xe0fake\xff\xd9'
IMAGES = [{'role': 'strip', 'jpeg': JPEG}, {'role': 'overview', 'jpeg': JPEG}]


def call_resp(verdict, q='ok', hand=True, held=True, staff=False, alt='none'):
    return dict(checklist=dict(hand_above_head=hand, held_or_waved_across_frames=held, wearing_staff_uniform=staff),
                alt=alt, image_quality=q, verdict=verdict, reason='mẫu')


def table_resp(verdict, q='ok', used=True, people=False, bel=False):
    return dict(checklist=dict(used_items_left=used, people_at_table=people, differs_from_clean_ref=used),
                personal_belongings_present=bel, image_quality=q, verdict=verdict, reason='mẫu')


class FakeClock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


class FakeGemini:
    """Gemini giả: mỗi lần gọi lấy một hành vi trong `script` (dict = trả JSON, 'hang' = treo 30 s, 'err' = lỗi)."""
    enabled = True
    model = 'gia-lap'

    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    async def verify(self, kind, images, table=None):
        self.calls.append(dict(kind=kind, roles=[im['role'] for im in images], table=table))
        b = self.script.pop(0) if len(self.script) > 1 else self.script[0]
        if b == 'hang':
            await asyncio.sleep(30)
        if b == 'err':
            raise GeminiError('HTTP 503: giả lập')
        return xm.normalize(b, 5)


async def wait_verified(hub, aid, timeout=5.0):
    t0 = time.perf_counter()
    while hub.alerts[aid]['verify']['state'] == 'pending':
        if time.perf_counter() - t0 > timeout:
            raise AssertionError('quá hạn chờ xác minh')
        await asyncio.sleep(0.02)
    return time.perf_counter() - t0


def ev(kind='goi_phuc_vu', table='B1', images=True):
    e = dict(kind=kind, camera='cam1', table=table, box=[100, 100, 200, 300], crop_jpeg=JPEG)
    if images:
        e['images'] = list(IMAGES)
    return e


# ====================================================================== luật quyết định
class TestDecide(unittest.TestCase):
    def test_call(self):
        cases = [
            (call_resp('GOI'), ('confirm', 'confirmed')),
            (call_resp('KHONG_GOI', hand=False), ('reject', 'rejected')),
            (call_resp('KHONG_GOI', held=False), ('reject', 'rejected')),
            (call_resp('KHONG_GOI', staff=True), ('reject', 'rejected')),
            (call_resp('KHONG_GOI', alt='vuon_vai'), ('reject', 'rejected')),
            (call_resp('KHONG_GOI'), ('unverified', 'inconsistent')),        # checklist nói "đang gọi"
            (call_resp('KHONG_GOI', alt='khac'), ('unverified', 'inconsistent')),
            (call_resp('KHONG_GOI', q='toi', hand=False), ('unverified', 'poor_image')),
            (call_resp('KHONG_GOI', q='bi_che', hand=False), ('unverified', 'poor_image')),
            (call_resp('KHONG_CHAC'), ('unverified', 'uncertain')),
            ({'verdict': 'abc'}, ('unverified', 'uncertain')),                # JSON lạ: giữ cảnh báo
            ({}, ('unverified', 'uncertain')),
        ]
        for d, want in cases:
            with self.subTest(d=d):
                self.assertEqual(xm.decide('call', d), want)

    def test_only_consistent_khong_goi_cancels(self):
        """Duyệt mọi tổ hợp: chỉ KHONG_GOI + ok + có lý do bác trong checklist mới ra 'reject'."""
        for v in ('GOI', 'KHONG_GOI', 'KHONG_CHAC'):
            for q in xm.QUALITY:
                for hand in (True, False):
                    for held in (True, False):
                        for staff in (True, False):
                            for alt in xm.ALT_CALL:
                                a, _ = xm.decide('call', call_resp(v, q, hand, held, staff, alt))
                                reason = (not hand) or (not held) or staff or alt not in ('none', 'khac')
                                self.assertEqual(a == 'reject', v == 'KHONG_GOI' and q == 'ok' and reason)

    def test_table(self):
        cases = [
            (table_resp('CAN_DON'), ('confirm', 'confirmed')),
            (table_resp('CAN_DON', bel=True), ('unverified', 'belongings')),
            (table_resp('CAN_DON', people=True), ('unverified', 'inconsistent')),
            (table_resp('CAN_DON', used=False), ('unverified', 'inconsistent')),
            (table_resp('CAN_DON', q='mo'), ('unverified', 'poor_image')),
            (table_resp('SACH', used=False), ('reject', 'rejected')),
            (table_resp('SACH', used=True), ('unverified', 'inconsistent')),
            (table_resp('SACH', used=False, q='toi'), ('unverified', 'poor_image')),
            (table_resp('KHONG_CHAC'), ('unverified', 'uncertain')),
        ]
        for d, want in cases:
            with self.subTest(d=d):
                self.assertEqual(xm.decide('needs_clearing', d), want)


# ====================================================================== breaker đơn lẻ
class TestBreaker(unittest.TestCase):
    def test_open_after_3_then_half_open_after_60s(self):
        c = FakeClock()
        b = xm.CircuitBreaker(3, 60, c)
        for _ in range(2):
            self.assertTrue(b.allow()); b.failure()
        self.assertEqual(b.state, 'closed')
        self.assertTrue(b.allow()); b.failure()
        self.assertEqual(b.state, 'open')
        self.assertFalse(b.allow())
        c.t += 59.9
        self.assertFalse(b.allow())
        c.t += 0.1
        self.assertEqual(b.state, 'half_open')
        self.assertTrue(b.allow())          # một lời gọi thử
        self.assertFalse(b.allow())         # lời gọi thứ hai trong lúc thử: chặn
        b.failure()                         # thử hỏng: mở lại 60 s
        self.assertEqual(b.state, 'open')
        c.t += 60
        self.assertTrue(b.allow()); b.success()
        self.assertEqual(b.state, 'closed')

    def test_success_resets_count(self):
        b = xm.CircuitBreaker(3, 60, FakeClock())
        b.failure(); b.failure(); b.success(); b.failure(); b.failure()
        self.assertEqual(b.state, 'closed')


# ====================================================================== Hub thật + Gemini giả
class HubCase(unittest.IsolatedAsyncioTestCase):
    def make(self, script, timeout_s=2.5):
        self.tmp = tempfile.TemporaryDirectory()
        self.clock = FakeClock()
        self.g = FakeGemini(script)
        return xm.HubV2(Path(self.tmp.name), self.g, clock=self.clock, timeout_s=timeout_s)

    def tearDown(self):
        self.tmp.cleanup()


class TestHubVerdicts(HubCase):
    async def run_one(self, resp, kind='goi_phuc_vu'):
        hub = self.make([resp])
        aid = hub.edge_event(ev(kind))
        a = hub.alerts[aid]
        before = (a['status'], a['assigned_to'])
        await wait_verified(hub, aid)
        return hub, a, before

    async def test_goi_confirms(self):
        hub, a, before = await self.run_one(call_resp('GOI'))
        self.assertEqual(before[0], 'open'); self.assertIsNotNone(before[1])   # báo trước, xác minh sau
        self.assertEqual((a['status'], a['verify']['state']), ('open', 'confirmed'))

    async def test_khong_goi_ok_consistent_cancels(self):
        hub, a, _ = await self.run_one(call_resp('KHONG_GOI', hand=False, alt='chinh_toc'))
        self.assertEqual((a['status'], a['verify']['state']), ('cancelled', 'rejected'))
        self.assertIn('Gemini', a['cancel_reason'])

    async def test_khong_goi_dark_keeps_alert(self):
        hub, a, _ = await self.run_one(call_resp('KHONG_GOI', q='toi', hand=False))
        self.assertEqual((a['status'], a['verify']['state'], a['verify']['path']), ('open', 'unverified', 'poor_image'))

    async def test_khong_goi_inconsistent_keeps_alert(self):
        hub, a, _ = await self.run_one(call_resp('KHONG_GOI'))
        self.assertEqual((a['status'], a['verify']['state'], a['verify']['path']), ('open', 'unverified', 'inconsistent'))

    async def test_khong_chac_marks_unverified(self):
        hub, a, _ = await self.run_one(call_resp('KHONG_CHAC'))
        self.assertEqual((a['status'], a['verify']['state']), ('open', 'unverified'))
        self.assertTrue(any('Chưa xác minh' in e['text'] for e in hub.log))

    async def test_table_can_don_assigns_after_verify(self):
        hub = self.make([table_resp('CAN_DON')])
        aid = hub.edge_event(ev('can_don'))
        a = hub.alerts[aid]
        self.assertEqual((a['status'], a['assigned_to']), ('verifying', None))   # "cần dọn" giữ tới khi xác nhận
        await wait_verified(hub, aid)
        self.assertEqual((a['status'], a['verify']['state']), ('open', 'confirmed'))
        self.assertIsNotNone(a['assigned_to'])

    async def test_table_sach_cancels(self):
        hub, a, _ = await self.run_one(table_resp('SACH', used=False), 'can_don')
        self.assertEqual((a['status'], a['verify']['state']), ('cancelled', 'rejected'))

    async def test_table_belongings_unverified(self):
        hub, a, _ = await self.run_one(table_resp('CAN_DON', bel=True), 'can_don')
        self.assertEqual((a['status'], a['verify']['state'], a['verify']['path']), ('open', 'unverified', 'belongings'))

    async def test_images_reach_gemini(self):
        hub = self.make([table_resp('CAN_DON')])
        e = ev('can_don')
        e['images'] = IMAGES + [{'role': 'clean_ref', 'jpeg': JPEG}]
        aid = hub.edge_event(e)
        await wait_verified(hub, aid)
        self.assertEqual(self.g.calls[0], dict(kind='needs_clearing', roles=['strip', 'overview', 'clean_ref'],
                                               table='B1'))

    async def test_legacy_single_crop_still_works(self):
        hub = self.make([call_resp('GOI')])
        aid = hub.edge_event(ev(images=False))
        await wait_verified(hub, aid)
        self.assertEqual(self.g.calls[0]['roles'], ['strip'])


class TestHubResilience(HubCase):
    async def test_hang_call_unverified_within_3s(self):
        hub = self.make(['hang'], timeout_s=2.5)
        t0 = time.perf_counter()
        aid = hub.edge_event(ev())
        a = hub.alerts[aid]
        t_push = time.perf_counter() - t0
        self.assertEqual(a['status'], 'open'); self.assertIsNotNone(a['assigned_to'])
        dt = await wait_verified(hub, aid)
        self.assertEqual((a['status'], a['verify']['state'], a['verify']['path']), ('open', 'unverified', 'timeout'))
        self.assertLessEqual(dt, 3.0)
        print(f'\n  [treo] việc tới nhân viên sau {t_push * 1000:.1f} ms; "Chưa xác minh" sau {dt:.2f} s')

    async def test_hang_table_released_within_3s(self):
        hub = self.make(['hang'], timeout_s=2.5)
        aid = hub.edge_event(ev('can_don'))
        a = hub.alerts[aid]
        dt = await wait_verified(hub, aid)
        self.assertEqual((a['status'], a['verify']['state']), ('open', 'unverified'))
        self.assertIsNotNone(a['assigned_to'])
        self.assertLessEqual(dt, 3.0)
        print(f'\n  [treo, cần dọn] mở việc sau {dt:.2f} s')

    async def test_breaker_5_errors(self):
        hub = self.make(['err'])
        aids = []
        for i in range(5):
            aid = hub.edge_event(ev(table=f'B{i}'))
            await wait_verified(hub, aid)
            aids.append(aid)
        self.assertEqual(len(self.g.calls), 3)               # lần 4, 5 không gọi
        paths = [hub.alerts[x]['verify']['path'] for x in aids]
        self.assertEqual(paths, ['error', 'error', 'error', 'breaker_open', 'breaker_open'])
        self.assertTrue(all(hub.alerts[x]['status'] == 'open' for x in aids))
        self.assertEqual(hub.breaker.state, 'open')
        self.clock.t += 59
        aid = hub.edge_event(ev(table='B6')); await wait_verified(hub, aid)
        self.assertEqual(len(self.g.calls), 3)
        # 60 s sau khi mở: thử lại một lần; Gemini đã khỏe
        self.clock.t += 1
        self.g.script = [call_resp('GOI')]
        aid = hub.edge_event(ev(table='B7')); await wait_verified(hub, aid)
        self.assertEqual(len(self.g.calls), 4)
        self.assertEqual(hub.alerts[aid]['verify']['state'], 'confirmed')
        self.assertEqual(hub.breaker.state, 'closed')

    async def test_breaker_counts_timeouts_and_failed_trial_reopens(self):
        hub = self.make(['hang'], timeout_s=0.2)
        for i in range(3):
            aid = hub.edge_event(ev(table=f'B{i}')); await wait_verified(hub, aid)
        self.assertEqual(hub.breaker.state, 'open')
        self.clock.t += 60
        aid = hub.edge_event(ev(table='B3')); await wait_verified(hub, aid)   # lần thử, vẫn treo
        self.assertEqual(hub.alerts[aid]['verify']['path'], 'timeout')
        self.assertEqual(hub.breaker.state, 'open')
        aid = hub.edge_event(ev(table='B4')); await wait_verified(hub, aid)
        self.assertEqual(hub.alerts[aid]['verify']['path'], 'breaker_open')
        self.assertEqual(len(self.g.calls), 4)


# ====================================================================== client thật (httpx giả lập mạng)
def gemini_v2(handler):
    g = xm.GeminiV2()
    g.key = 'khoa-gia'
    g.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return g


def ok_json(d):
    return httpx.Response(200, json={'candidates': [{'content': {'parts': [{'text': json.dumps(d)}]}}]})


class TestClient(unittest.IsolatedAsyncioTestCase):
    async def test_body_and_parse(self):
        seen = []

        def h(req):
            seen.append(json.loads(req.content))
            return ok_json(call_resp('GOI'))
        g = gemini_v2(h)
        r = await g.verify('call', IMAGES)
        self.assertEqual(r['verdict'], 'GOI')
        parts = seen[0]['contents'][0]['parts']
        self.assertEqual([p.get('mediaResolution', {}).get('level') for p in parts[1:]],
                         ['MEDIA_RESOLUTION_MEDIUM', 'MEDIA_RESOLUTION_LOW'])
        gc = seen[0]['generationConfig']
        self.assertNotIn('mediaResolution', gc)
        self.assertEqual(gc['responseJsonSchema']['properties']['verdict']['enum'], ['GOI', 'KHONG_GOI', 'KHONG_CHAC'])

    async def test_fallback_when_per_part_resolution_rejected(self):
        seen = []

        def h(req):
            body = json.loads(req.content)
            seen.append(body)
            if any('mediaResolution' in p for p in body['contents'][0]['parts']):
                return httpx.Response(400, text='Invalid JSON payload: Unknown name "mediaResolution" at parts[1]')
            return ok_json(call_resp('KHONG_CHAC'))
        g = gemini_v2(h)
        r = await g.verify('call', IMAGES)
        self.assertEqual(r['verdict'], 'KHONG_CHAC')
        self.assertEqual(len(seen), 2)
        self.assertEqual(seen[1]['generationConfig']['mediaResolution'], 'MEDIA_RESOLUTION_MEDIUM')

    async def test_real_client_hang_through_hub(self):
        async def h(req):
            await asyncio.sleep(30)
            return ok_json(call_resp('GOI'))
        g = gemini_v2(h)
        with tempfile.TemporaryDirectory() as d:
            hub = xm.HubV2(Path(d), g, timeout_s=2.5)
            aid = hub.edge_event(ev())
            dt = await wait_verified(hub, aid)
            self.assertEqual(hub.alerts[aid]['verify']['path'], 'timeout')
            self.assertLessEqual(dt, 3.0)


# ====================================================================== gói thật đã dựng
class TestPackages(unittest.TestCase):
    def test_built_packages(self):
        s = json.loads((HERE / 'goi_mau' / 'tong_hop.json').read_text(encoding='utf-8'))
        self.assertEqual(sum(1 for g in s['goi'] if g['bien_the'] == 'truoc'), 9)
        for g in s['goi']:
            with self.subTest(g=g['goi'], v=g['bien_the']):
                self.assertLessEqual(g['token']['total'], 1600)
                self.assertLessEqual(max(g['dai_px']), 1024)
                body = json.loads((HERE / 'goi_mau' / g['goi'] / ('request.json' if g['bien_the'] == 'truoc'
                                                                   else 'request_quanh.json')).read_text('utf-8'))
                levels = [p['mediaResolution']['level'] for p in body['contents'][0]['parts'][1:]]
                self.assertEqual(levels[0], 'MEDIA_RESOLUTION_MEDIUM')
                self.assertTrue(all(lv == 'MEDIA_RESOLUTION_LOW' for lv in levels[1:]))


if __name__ == '__main__':
    unittest.main(verbosity=2)
