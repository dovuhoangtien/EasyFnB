"""Xác minh Gemini: luật quyết định, timeout, circuit breaker, gói ảnh xác minh (eid), trên Hub thật.

Chuyển từ phép thử bản thử vision-test/thu_nghiem/gemini_goi_kiem_tra/kiem_thu.py sang server thật,
thêm phần gói ảnh gửi sau sự kiện (POST /api/edge/evidence). Không cần mạng, không cần khoá.

Chạy (trong easy-fnb):  python -m unittest server.tests.test_xac_minh -v
"""
import asyncio
import json
import tempfile
import time
import unittest
from pathlib import Path

import httpx

from server.gemini import ALT_CALL, QUALITY, Gemini, GeminiError, decide
from server.hub import CircuitBreaker, Hub

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
        d = dict(b)
        d['reason'] = str(d.get('reason') or '')[:120]
        d['ms'] = 5
        return d


async def wait_verified(hub, aid, timeout=6.0):
    t0 = time.perf_counter()
    while hub.alerts[aid]['verify']['state'] == 'pending':
        if time.perf_counter() - t0 > timeout:
            raise AssertionError('quá hạn chờ xác minh')
        await asyncio.sleep(0.02)
    return time.perf_counter() - t0


def ev(kind='goi_phuc_vu', table='B1', images=True, eid=None, items=None):
    e = dict(kind=kind, camera='cam1', table=table, box=[100, 100, 200, 300], crop_jpeg=JPEG)
    if images:
        e['images'] = list(IMAGES)
    if eid:
        e['eid'] = eid
    if items is not None:
        e['items'] = items
    return e


def evidence(eid, ref=True, items=None):
    return dict(camera='cam1', eid=eid, strip_jpeg=JPEG + b'S', overview_jpeg=JPEG + b'O',
                ref_jpeg=JPEG + b'R' if ref else None, items=items)


# ====================================================================== luật quyết định
class TestDecide(unittest.TestCase):
    def test_call(self):
        cases = [
            (call_resp('GOI'), ('confirm', 'confirmed')),
            (call_resp('KHONG_GOI', hand=False), ('reject', 'rejected')),
            (call_resp('KHONG_GOI', held=False), ('reject', 'rejected')),
            (call_resp('KHONG_GOI', staff=True), ('reject', 'rejected')),
            (call_resp('KHONG_GOI', alt='vuon_vai'), ('reject', 'rejected')),
            (call_resp('KHONG_GOI'), ('unverified', 'inconsistent')),
            (call_resp('KHONG_GOI', alt='khac'), ('unverified', 'inconsistent')),
            (call_resp('KHONG_GOI', q='toi', hand=False), ('unverified', 'poor_image')),
            (call_resp('KHONG_GOI', q='bi_che', hand=False), ('unverified', 'poor_image')),
            (call_resp('KHONG_CHAC'), ('unverified', 'uncertain')),
            ({'verdict': 'abc'}, ('unverified', 'uncertain')),
            ({}, ('unverified', 'uncertain')),
        ]
        for d, want in cases:
            with self.subTest(d=d):
                self.assertEqual(decide('call', d), want)

    def test_only_consistent_khong_goi_cancels(self):
        """Duyệt mọi tổ hợp: chỉ KHONG_GOI + ok + có lý do bác trong checklist mới ra 'reject'."""
        for v in ('GOI', 'KHONG_GOI', 'KHONG_CHAC'):
            for q in QUALITY:
                for hand in (True, False):
                    for held in (True, False):
                        for staff in (True, False):
                            for alt in ALT_CALL:
                                a, _ = decide('call', call_resp(v, q, hand, held, staff, alt))
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
                self.assertEqual(decide('needs_clearing', d), want)


# ====================================================================== breaker đơn lẻ
class TestBreaker(unittest.TestCase):
    def test_open_after_3_then_half_open_after_60s(self):
        c = FakeClock()
        b = CircuitBreaker(3, 60, c)
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
        self.assertTrue(b.allow())
        self.assertFalse(b.allow())
        b.failure()
        self.assertEqual(b.state, 'open')
        c.t += 60
        self.assertTrue(b.allow()); b.success()
        self.assertEqual(b.state, 'closed')

    def test_success_resets_count(self):
        b = CircuitBreaker(3, 60, FakeClock())
        b.failure(); b.failure(); b.success(); b.failure(); b.failure()
        self.assertEqual(b.state, 'closed')


# ====================================================================== Hub thật + Gemini giả
class HubCase(unittest.IsolatedAsyncioTestCase):
    def make(self, script, timeout_s=2.5, evidence_wait_s=None):
        self.tmp = tempfile.TemporaryDirectory()
        self.clock = FakeClock()
        self.g = FakeGemini(script)
        hub = Hub(Path(self.tmp.name), self.g, clock=self.clock, verify_timeout_s=timeout_s)
        if evidence_wait_s is not None:
            hub.settings['evidence_wait_s'] = evidence_wait_s
        return hub

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
        self.assertEqual(hub.report()['unverified'], 1)

    async def test_table_can_don_assigns_after_verify(self):
        hub = self.make([table_resp('CAN_DON')])
        aid = hub.edge_event(ev('can_don'))
        a = hub.alerts[aid]
        self.assertEqual((a['status'], a['assigned_to']), ('verifying', None))
        await wait_verified(hub, aid)
        self.assertEqual((a['status'], a['verify']['state']), ('open', 'confirmed'))
        self.assertIsNotNone(a['assigned_to'])

    async def test_table_sach_cancels(self):
        hub, a, _ = await self.run_one(table_resp('SACH', used=False), 'can_don')
        self.assertEqual((a['status'], a['verify']['state']), ('cancelled', 'rejected'))

    async def test_table_belongings_unverified(self):
        hub, a, _ = await self.run_one(table_resp('CAN_DON', bel=True), 'can_don')
        self.assertEqual((a['status'], a['verify']['state'], a['verify']['path']), ('open', 'unverified', 'belongings'))

    async def test_belongings_holds_table_instead_of_clearing(self):
        # khách để máy ở bàn rồi đi vệ sinh: không giao việc dọn, vẫn là lượt khách cũ
        from server import giai_doan
        hub = self.make([table_resp('CAN_DON', bel=True)])
        hub.edge_tables('cam1', [dict(id='B1', state='co_khach', people=1)])
        seat = hub.stages.st['B1']['seat']
        hub.edge_tables('cam1', [dict(id='B1', state='can_don', people=0)])
        aid = hub.edge_event(ev('can_don'))
        a = hub.alerts[aid]
        await wait_verified(hub, aid)
        self.assertEqual((a['status'], a['verify']['path'], a['assigned_to']), ('cancelled', 'belongings', None))
        self.assertIn('để đồ', a['cancel_reason'])
        self.assertTrue(hub.tables['cam1/B1']['away'])
        self.clock.t += giai_doan.LEFT_GRACE_S + 5
        hub.tick()
        self.assertEqual(hub.stages.st['B1']['stage'], 'seated')
        hub.edge_tables('cam1', [dict(id='B1', state='co_khach', people=1)])     # khách quay lại
        self.assertEqual((hub.stages.st['B1']['seat'], hub.tables['cam1/B1']['away']), (seat, False))

    async def test_belongings_hold_expires_then_clearing_task(self):
        from server import giai_doan
        hub = self.make([table_resp('CAN_DON', bel=True)])
        hub.edge_tables('cam1', [dict(id='B1', state='co_khach', people=1)])
        hub.edge_tables('cam1', [dict(id='B1', state='can_don', people=0)])
        aid = hub.edge_event(ev('can_don'))
        await wait_verified(hub, aid)
        self.clock.t += giai_doan.HOLD_S + 1
        hub.alerts[aid]['created_at'] -= int(giai_doan.HOLD_S * 1000)       # luật gộp trùng tính theo giờ thật
        hub.tick()
        self.assertEqual(hub.stages.st['B1']['stage'], 'left')
        new = [x for x in hub.alerts.values() if x['id'] != aid and x['kind'] == 'needs_clearing']
        self.assertEqual(len(new), 1)
        await wait_verified(hub, new[0]['id'])
        self.assertEqual(new[0]['status'], 'open')                          # lần này giao cho nhân viên

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
        self.assertEqual(self.g.calls[0]['roles'], ['crop'])
        self.assertEqual(hub.alerts[aid]['verify']['source'], 'crop')


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
        self.assertEqual(len(self.g.calls), 3)
        paths = [hub.alerts[x]['verify']['path'] for x in aids]
        self.assertEqual(paths, ['error', 'error', 'error', 'breaker_open', 'breaker_open'])
        self.assertTrue(all(hub.alerts[x]['status'] == 'open' for x in aids))
        self.assertEqual(hub.breaker.state, 'open')
        self.clock.t += 59
        aid = hub.edge_event(ev(table='B6')); await wait_verified(hub, aid)
        self.assertEqual(len(self.g.calls), 3)
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
        aid = hub.edge_event(ev(table='B3')); await wait_verified(hub, aid)
        self.assertEqual(hub.alerts[aid]['verify']['path'], 'timeout')
        self.assertEqual(hub.breaker.state, 'open')
        aid = hub.edge_event(ev(table='B4')); await wait_verified(hub, aid)
        self.assertEqual(hub.alerts[aid]['verify']['path'], 'breaker_open')
        self.assertEqual(len(self.g.calls), 4)


# ====================================================================== gói ảnh gửi sau sự kiện (eid)
class TestEvidence(HubCase):
    async def test_evidence_within_wait_is_used(self):
        hub = self.make([table_resp('CAN_DON')])
        aid = hub.edge_event(ev('can_don', images=False, eid='e1', items=[]))
        self.assertEqual(hub.alerts[aid]['status'], 'verifying')
        await asyncio.sleep(0.3)
        self.assertEqual(self.g.calls, [])                    # còn chờ gói ảnh
        items = [{'name': 'dĩa', 'count': 2}, {'name': 'chai', 'count': 1}]
        self.assertEqual(hub.edge_evidence(evidence('e1', items=items)), aid)
        await wait_verified(hub, aid)
        a = hub.alerts[aid]
        self.assertEqual(self.g.calls[0]['roles'], ['strip', 'overview', 'clean_ref'])
        self.assertEqual((a['status'], a['verify']['state'], a['verify']['source']), ('open', 'confirmed', 'evidence'))
        self.assertEqual(a['items'], items)
        self.assertEqual(a['evidence'], {'strip': f'/api/alerts/{aid}/evidence/strip.jpg',
                                         'overview': f'/api/alerts/{aid}/evidence/overview.jpg',
                                         'ref': f'/api/alerts/{aid}/evidence/ref.jpg'})
        self.assertEqual(hub.evidence_file(aid, 'strip').read_bytes(), JPEG + b'S')
        self.assertIsNone(hub.evidence_file(aid, 'nope'))
        self.assertNotIn(aid, hub.media)                      # ảnh không giữ trong bộ nhớ sau khi xác minh

    async def test_no_evidence_falls_back_to_crop_after_wait(self):
        hub = self.make([call_resp('GOI')], evidence_wait_s=0.4)
        t0 = time.perf_counter()
        aid = hub.edge_event(ev(images=False, eid='e2'))
        self.assertIsNotNone(hub.alerts[aid]['assigned_to'])  # gọi phục vụ vẫn báo ngay
        await wait_verified(hub, aid)
        self.assertGreaterEqual(time.perf_counter() - t0, 0.35)
        self.assertEqual(self.g.calls[0]['roles'], ['crop'])
        self.assertEqual(hub.alerts[aid]['verify']['source'], 'crop')
        self.assertIsNone(hub.alerts[aid]['evidence'])

    async def test_late_evidence_still_stored_for_dashboard(self):
        hub = self.make([call_resp('GOI')], evidence_wait_s=0.1)
        aid = hub.edge_event(ev(images=False, eid='e3'))
        await wait_verified(hub, aid)
        hub.edge_evidence(evidence('e3', ref=False))
        a = hub.alerts[aid]
        self.assertEqual(a['evidence']['strip'], f'/api/alerts/{aid}/evidence/strip.jpg')
        self.assertIsNone(a['evidence']['ref'])
        self.assertEqual(len(self.g.calls), 1)                # không gọi Gemini lần hai

    async def test_dedup_maps_eid_to_existing_alert(self):
        hub = self.make([call_resp('GOI')])
        a1 = hub.edge_event(ev(images=False, eid='e4'))
        a2 = hub.edge_event(ev(images=False, eid='e5'))       # cùng người, trong 20 s: gộp vào a1
        self.assertEqual(a1, a2)
        self.assertEqual(hub.alerts[a1]['repeats'], 1)
        self.assertEqual(hub.eids, {'e4': a1, 'e5': a1})
        self.assertEqual(hub.edge_evidence(evidence('e5', ref=False)), a1)   # gói của sự kiện đã gộp
        await wait_verified(hub, a1)
        self.assertEqual(self.g.calls[0]['roles'], ['strip', 'overview'])
        hub.edge_evidence(dict(evidence('e4'), strip_jpeg=b'khac'))          # đã có dải: giữ ảnh đầu, lấp ảnh còn thiếu
        self.assertEqual(hub.evidence_file(a1, 'strip').read_bytes(), JPEG + b'S')
        self.assertEqual(hub.alerts[a1]['evidence']['ref'], f'/api/alerts/{a1}/evidence/ref.jpg')

    async def test_dedup_updates_items(self):
        hub = self.make([table_resp('CAN_DON')], evidence_wait_s=0.1)
        aid = hub.edge_event(ev('can_don', images=False, eid='e6', items=[{'name': 'dĩa', 'count': 3}]))
        hub.edge_event(ev('can_don', images=False, eid='e7', items=[{'name': 'dĩa', 'count': 2}]))
        self.assertEqual(hub.alerts[aid]['items'], [{'name': 'dĩa', 'count': 2}])
        await wait_verified(hub, aid)

    async def test_evidence_before_event_is_kept(self):
        hub = self.make([call_resp('GOI')])
        self.assertIsNone(hub.edge_evidence(evidence('e8', ref=False)))
        aid = hub.edge_event(ev(images=False, eid='e8'))
        await wait_verified(hub, aid)
        self.assertEqual(self.g.calls[0]['roles'], ['strip', 'overview'])

    async def test_breaker_open_does_not_wait_for_evidence(self):
        hub = self.make(['err'], evidence_wait_s=2.5)
        for i in range(3):
            aid = hub.edge_event(ev(table=f'B{i}')); await wait_verified(hub, aid)
        self.assertEqual(hub.breaker.state, 'open')
        aid = hub.edge_event(ev('can_don', table='B9', images=False, eid='e9'))
        dt = await wait_verified(hub, aid)
        a = hub.alerts[aid]
        self.assertLess(dt, 0.5)
        self.assertEqual((a['status'], a['verify']['path']), ('open', 'breaker_open'))
        self.assertIsNotNone(a['assigned_to'])

    async def test_no_crop_no_evidence_is_unverified(self):
        hub = self.make([call_resp('GOI')], evidence_wait_s=0.1)
        e = ev(images=False, eid='e10')
        e['crop_jpeg'] = None
        aid = hub.edge_event(e)
        await wait_verified(hub, aid)
        self.assertEqual(hub.alerts[aid]['verify']['path'], 'no_image')
        self.assertEqual(self.g.calls, [])
        self.assertEqual(hub.breaker.state, 'closed')

    async def test_reset_clears_evidence(self):
        hub = self.make([call_resp('GOI')], evidence_wait_s=0.1)
        aid = hub.edge_event(ev(images=False, eid='e11'))
        hub.edge_evidence(evidence('e11'))
        await wait_verified(hub, aid)
        hub.reset()
        self.assertEqual(list((Path(self.tmp.name) / 'evidence').glob('*.jpg')), [])
        self.assertEqual(hub.eids, {})

    async def test_reset_restarts_attendance(self):
        hub = self.make([], evidence_wait_s=0.1)
        hub.staff = [dict(id='lan', name='Lan', role='serve'), dict(id='minh', name='Minh', role='serve')]
        hub.staff_online('lan', +1)
        hub.staff_online('minh', +1)
        hub.staff_online('minh', -1)
        del hub.pending_off['minh']   # như vòng lặp nền làm khi hết thời gian chờ
        hub._finish_off('minh')
        hub.attendance['lan'][0]['in'] -= 3600_000  # Lan vào ca từ một tiếng trước
        hub.reset()
        v = {x['id']: x for x in hub.staff_view()}
        self.assertIsNone(v['minh']['first_in'])            # không mở app: ca mới chưa vào
        self.assertEqual(v['minh']['worked_s'], 0)
        self.assertTrue(v['lan']['online'])                 # đang mở app: tính lại từ lúc bắt đầu ca mới
        self.assertLess(abs(v['lan']['first_in'] - v['lan']['on_since']), 1)
        self.assertGreater(v['lan']['first_in'], hub.attendance['lan'][0]['in'] - 1)
        self.assertEqual(v['lan']['worked_s'], 0)


# ====================================================================== client thật (httpx giả lập mạng)
def real_gemini(handler):
    g = Gemini()
    g.key = 'khoa-gia'
    g.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return g


def ok_json(d):
    return httpx.Response(200, json={'candidates': [{'content': {'parts': [{'text': json.dumps(d)}]}}]})


def decision_gemini(handler):
    g = real_gemini(handler)
    g.verify_model = 'gemini-decision-1'
    return g


def decision_json(**probs):
    return httpx.Response(200, json={
        'answers': {k: {'type': 'noul', 'noul': p, 'confidence': 0.9} for k, p in probs.items()},
        'usage': {'total_input_tokens': 900, 'total_output_tokens': 0, 'total_tokens': 900}})


class TestClient(unittest.IsolatedAsyncioTestCase):
    async def test_body_and_parse(self):
        seen = []

        def h(req):
            seen.append(json.loads(req.content))
            return ok_json(call_resp('GOI'))
        g = real_gemini(h)
        r = await g.verify('call', IMAGES)
        self.assertEqual(r['verdict'], 'GOI')
        parts = seen[0]['contents'][0]['parts']
        self.assertIn('Ảnh 2: toàn cảnh', parts[0]['text'])
        self.assertEqual([p.get('mediaResolution', {}).get('level') for p in parts[1:]],
                         ['MEDIA_RESOLUTION_MEDIUM', 'MEDIA_RESOLUTION_LOW'])
        gc = seen[0]['generationConfig']
        self.assertNotIn('mediaResolution', gc)
        self.assertEqual(gc['responseJsonSchema']['properties']['verdict']['enum'], ['GOI', 'KHONG_GOI', 'KHONG_CHAC'])

    async def test_single_crop_prompt(self):
        seen = []

        def h(req):
            seen.append(json.loads(req.content))
            return ok_json(table_resp('CAN_DON'))
        g = real_gemini(h)
        await g.verify('needs_clearing', JPEG, 'B2')
        parts = seen[0]['contents'][0]['parts']
        self.assertIn('Chỉ có 1 ảnh cắt quanh bàn B2', parts[0]['text'])
        self.assertNotIn('Ảnh 3', parts[0]['text'])
        self.assertEqual(parts[1]['mediaResolution']['level'], 'MEDIA_RESOLUTION_MEDIUM')
        self.assertEqual(seen[0]['generationConfig']['responseJsonSchema']['properties']['verdict']['enum'],
                         ['CAN_DON', 'SACH', 'KHONG_CHAC'])

    async def test_clean_ref_sentence(self):
        seen = []

        def h(req):
            seen.append(json.loads(req.content))
            return ok_json(table_resp('CAN_DON'))
        g = real_gemini(h)
        await g.verify('needs_clearing', IMAGES + [{'role': 'clean_ref', 'jpeg': JPEG}], 'B1')
        text = seen[0]['contents'][0]['parts'][0]['text']
        self.assertIn('quanh bàn B1', text)
        self.assertIn('Ảnh 3: cùng bàn lúc sạch', text)

    async def test_fallback_when_per_part_resolution_rejected(self):
        seen = []

        def h(req):
            body = json.loads(req.content)
            seen.append(body)
            if any('mediaResolution' in p for p in body['contents'][0]['parts']):
                return httpx.Response(400, text='Invalid JSON payload: Unknown name "mediaResolution" at parts[1]')
            return ok_json(call_resp('KHONG_CHAC'))
        g = real_gemini(h)
        r = await g.verify('call', IMAGES)
        self.assertEqual(r['verdict'], 'KHONG_CHAC')
        self.assertEqual(len(seen), 2)
        self.assertEqual(seen[1]['generationConfig']['mediaResolution'], 'MEDIA_RESOLUTION_MEDIUM')
        r = await g.verify('call', IMAGES)                    # lần sau gửi thẳng dạng đã lui, không thử lại
        self.assertEqual(len(seen), 3)

    # ------------------------------------------------------------ Gemini Decision (Decisions API)
    async def test_decision_request_and_confirm(self):
        seen = []

        def h(req):
            seen.append((str(req.url), json.loads(req.content)))
            return decision_json(hand_above_head=0.93, arm_raised_high=0.88,
                                 wearing_staff_uniform=0.04, image_clear=0.97)
        g = decision_gemini(h)
        r = await g.verify('call', IMAGES)
        url, body = seen[0]
        self.assertTrue(url.endswith('/v1beta/decisions'))
        self.assertEqual(sorted(body), ['input', 'model', 'questions'])     # API chỉ nhận đúng ba trường này
        self.assertEqual(body['model'], 'gemini-decision-1')
        self.assertEqual([(b['type'], b.get('resolution')) for b in body['input']],
                         [('text', None), ('image', 'medium'), ('image', 'low')])
        self.assertEqual(set(body['questions']), {'hand_above_head', 'arm_raised_high',
                                                  'wearing_staff_uniform', 'image_clear'})
        self.assertTrue(all(q['type'] == 'noul' for q in body['questions'].values()))
        self.assertEqual((r['verdict'], r['image_quality'], r['model']), ('GOI', 'ok', 'gemini-decision-1'))
        self.assertEqual(decide('call', r), ('confirm', 'confirmed'))

    async def test_decision_single_crop(self):
        seen = []

        def h(req):
            seen.append(json.loads(req.content))
            return decision_json(used_items_left=0.9, people_at_table=0.05,
                                 personal_belongings_present=0.1, image_clear=0.9)
        g = decision_gemini(h)
        r = await g.verify('needs_clearing', JPEG, 'B2')
        self.assertIn('bàn B2', seen[0]['input'][0]['text'])
        self.assertEqual(decide('needs_clearing', r), ('confirm', 'confirmed'))
        await g.verify('call', JPEG)
        self.assertIn('arm_raised_high', seen[1]['questions'])
        self.assertNotIn('held_or_waved_across_frames', seen[1]['questions'])     # camera đã tự đo thời gian giữ tay

    def test_decision_rules(self):
        call = dict(hand_above_head=0.9, arm_raised_high=0.9, wearing_staff_uniform=0.1, image_clear=0.9)
        table = dict(used_items_left=0.9, people_at_table=0.1, personal_belongings_present=0.1, image_clear=0.9)
        cases = [
            ('call', {}, ('confirm', 'confirmed')),
            ('call', dict(hand_above_head=0.12, arm_raised_high=0.11), ('reject', 'rejected')),   # cả hai đều không
            ('call', dict(wearing_staff_uniform=0.85), ('reject', 'rejected')),
            ('call', dict(hand_above_head=0.62, arm_raised_high=0.63), ('confirm', 'confirmed')),  # tay bị che một phần
            ('call', dict(hand_above_head=0.22), ('unverified', 'uncertain')),          # vuốt tóc: tay cao nhưng không gọi
            ('call', dict(hand_above_head=0.28, arm_raised_high=0.34), ('unverified', 'uncertain')),  # gọi thật, ảnh khó
            ('call', dict(wearing_staff_uniform=0.6), ('unverified', 'uncertain')),
            ('call', dict(hand_above_head=0.4), ('unverified', 'uncertain')),          # lưng chừng: vẫn báo
            ('call', dict(hand_above_head=0.1, image_clear=0.3), ('unverified', 'poor_image')),  # ảnh kém: không bác
            ('needs_clearing', {}, ('confirm', 'confirmed')),
            ('needs_clearing', dict(used_items_left=0.1), ('reject', 'rejected')),
            ('needs_clearing', dict(personal_belongings_present=0.8), ('unverified', 'belongings')),
            ('needs_clearing', dict(people_at_table=0.9), ('unverified', 'inconsistent')),
            ('needs_clearing', dict(used_items_left=0.5), ('unverified', 'uncertain')),
        ]
        for kind, change, want in cases:
            probs = dict(call if kind == 'call' else table, **change)
            self.assertEqual(decide(kind, dict(probs=probs)), want, (kind, change))

    async def test_decision_reject_through_hub(self):
        def h(req):
            return decision_json(hand_above_head=0.12, arm_raised_high=0.2,
                                 wearing_staff_uniform=0.05, image_clear=0.95)
        g = decision_gemini(h)
        with tempfile.TemporaryDirectory() as d:
            hub = Hub(Path(d), g, defaults=dict(hold_until_verified=['call', 'needs_clearing']))
            aid = hub.edge_event(ev())
            self.assertEqual(hub.alerts[aid]['status'], 'verifying')     # chờ hỏi xong mới báo nhân viên
            await wait_verified(hub, aid)
            a = hub.alerts[aid]
            self.assertEqual((a['status'], a['verify']['state']), ('cancelled', 'rejected'))
            self.assertEqual(a['verify']['reason'], 'Giơ tay gọi: 12%')
            self.assertEqual(a['verify']['model'], 'gemini-decision-1')
            self.assertEqual(a['verify']['probs']['hand_above_head'], 0.12)

    async def test_decision_blocked_or_error_keeps_alert(self):
        replies = [httpx.Response(200, json={'answers': {}, 'prompt_feedback': {'block_reason': 'image_safety'}}),
                   httpx.Response(429, text='quota')]

        def h(req):
            return replies.pop(0)
        g = decision_gemini(h)
        with tempfile.TemporaryDirectory() as d:
            hub = Hub(Path(d), g, defaults=dict(hold_until_verified=['call']))
            for _ in range(2):
                aid = hub.edge_event(ev(table=f'B{len(replies)}'))
                await wait_verified(hub, aid)
                a = hub.alerts[aid]
                self.assertEqual((a['status'], a['verify']['path']), ('open', 'error'))

    async def test_real_client_hang_through_hub(self):
        async def h(req):
            await asyncio.sleep(30)
            return ok_json(call_resp('GOI'))
        g = real_gemini(h)
        with tempfile.TemporaryDirectory() as d:
            hub = Hub(Path(d), g, verify_timeout_s=2.5)
            aid = hub.edge_event(ev())
            dt = await wait_verified(hub, aid)
            self.assertEqual(hub.alerts[aid]['verify']['path'], 'timeout')
            self.assertLessEqual(dt, 3.0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
