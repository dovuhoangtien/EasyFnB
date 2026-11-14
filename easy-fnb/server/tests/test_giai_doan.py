"""Giai đoạn bữa ăn của bàn (seated -> greeted -> served -> finished -> left), ảnh bàn định kỳ và lời nhắc.

Không cần mạng, không cần khoá: Gemini Decision giả lập bằng httpx.MockTransport, giờ giả bằng FakeClock.
Chạy (trong easy-fnb):  python -m unittest server.tests.test_giai_doan -v
"""
import asyncio
import base64
import json
import os
import tempfile
import unittest
from pathlib import Path

import httpx

_tmp = tempfile.TemporaryDirectory()
os.environ.setdefault('DATA_DIR', _tmp.name)   # đặt trước khi nạp server.app, để không đụng dữ liệu thật

from server import giai_doan  # noqa: E402
from server.hub import Hub  # noqa: E402
from server.tests.test_xac_minh import JPEG, FakeClock, FakeGemini, decision_gemini, decision_json, ev  # noqa: E402

FOOD = dict(people_at_table=0.9, food_or_drink_on_table=0.92, plates_mostly_empty=0.1, menu_in_hand=0.05,
            image_clear=0.95)
NO_FOOD = dict(FOOD, food_or_drink_on_table=0.08)
EMPTY = dict(FOOD, plates_mostly_empty=0.9)
UNSURE = dict(FOOD, food_or_drink_on_table=0.5, plates_mostly_empty=0.5)
BLURRY = dict(EMPTY, image_clear=0.1)


def occupied(hub, cam='cam1', table='B1', state='co_khach', people=2):
    hub.edge_tables(cam, [dict(id=table, state=state, people=people)])


async def drain(hub):
    while hub.stages.tasks:
        await asyncio.gather(*list(hub.stages.tasks), return_exceptions=True)
        await asyncio.sleep(0)


class Base(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.c = FakeClock()
        self.replies = []          # mỗi lần hỏi lấy một phần tử: dict xác suất hoặc httpx.Response
        self.asked = []

    def handler(self, req):
        self.asked.append(json.loads(req.content))
        r = self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]
        return r if isinstance(r, httpx.Response) else decision_json(**r)

    def hub(self, decision=True, **defaults):
        g = decision_gemini(self.handler) if decision else FakeGemini([{}])
        return Hub(Path(self.tmp.name), g, clock=self.c, defaults=defaults or None)

    async def read(self, hub, step=60, table='B1', cam='cam1'):
        """Một ảnh bàn tới sau `step` giây; chờ Gemini trả lời xong. Trả lý do có/không hỏi."""
        self.c.t += step
        r = hub.stages.snap(cam, table, JPEG)
        await drain(hub)
        return r.get('check') or r.get('reason')

    def stage(self, hub, table='B1', cam='cam1'):
        return hub.tables[f'{cam}/{table}']['stage']

    def stage_rows(self, hub, **kw):
        return [(r['data']['prev'], r['data']['stage'], r['data']['via'])
                for r in hub.timeline.query(kinds='stage', **kw)]


class TestGiaiDoan(Base):
    async def test_camera_signals_only(self):
        """Decision tắt: bàn vẫn đi seated -> greeted -> left theo tín hiệu camera."""
        hub = self.hub(decision=False)
        hub.edge_tables('cam1', [dict(id='B1', state='trong', people=0)])
        self.assertIsNone(self.stage(hub))
        occupied(hub)
        tb = hub.state()['tables'][0]
        self.assertEqual(tb['stage'], 'seated')
        self.assertIsInstance(tb['stage_since'], int)
        self.assertEqual(await self.read(hub), 'off')                     # có ảnh nhưng không hỏi ai
        hub.edge_event(dict(kind='nv_den', camera='cam1', table='B1'))
        self.assertEqual(self.stage(hub), 'greeted')
        hub.edge_event(dict(kind='nv_den', camera='cam1', table='B1'))    # camera gửi lại: không đổi gì
        hub.edge_event(dict(kind='khach_roi', camera='cam1', table='B1'))
        self.assertEqual(self.stage(hub), 'greeted')                      # chưa kết luận ngay, chờ xem khách có ngồi lại không
        self.c.t += giai_doan.LEFT_GRACE_S + 1
        hub.stages.tick()
        self.assertEqual(self.stage(hub), 'left')
        hub.edge_event(dict(kind='nv_den', camera='cam1', table='B1'))    # bàn đã hết khách: không lùi giai đoạn
        self.assertEqual(self.stage(hub), 'left')
        self.assertEqual(self.stage_rows(hub), [(None, 'seated', 'camera'), ('seated', 'greeted', 'staff_arrived'),
                                                ('greeted', 'left', 'camera')])
        self.assertEqual(self.asked, [])

    async def test_staff_pressing_done_counts_as_greeted(self):
        hub = self.hub(decision=False, verify_kinds=[])
        occupied(hub)
        aid = hub.edge_event(ev('khach_moi', images=False))
        hub.done(aid, 'lan')
        self.assertEqual(self.stage(hub), 'greeted')
        self.assertEqual(self.stage_rows(hub)[-1], ('seated', 'greeted', 'staff_done'))

    async def test_served_needs_two_consecutive_readings(self):
        hub = self.hub()
        occupied(hub)
        hub.stages.on_staff('B1')
        self.replies = [FOOD, NO_FOOD, FOOD, UNSURE, BLURRY, FOOD]
        self.assertEqual(await self.read(hub), 'started')
        self.assertEqual(self.stage(hub), 'greeted')                      # mới một lần đọc
        await self.read(hub)                                              # lần sau nói không: đếm lại từ đầu
        await self.read(hub)
        self.assertEqual(self.stage(hub), 'greeted')
        await self.read(hub)                                              # lưng chừng: không tính, không xoá
        await self.read(hub)                                              # ảnh mờ: bỏ qua
        self.assertEqual(self.stage(hub), 'greeted')
        await self.read(hub)
        self.assertEqual(self.stage(hub), 'served')
        self.assertEqual(len(self.asked), 6)
        self.assertEqual(self.stage_rows(hub)[-1], ('greeted', 'served', 'snapshot'))
        checks = hub.timeline.query(kinds='table_check', table='B1')
        self.assertEqual([r['data']['used'] for r in checks], ['ok', 'ok', 'ok', 'ok', 'unclear', 'ok'])
        self.assertEqual(checks[0]['data']['food_or_drink_on_table'], 0.92)

    async def test_request_shape(self):
        hub = self.hub()
        occupied(hub)
        self.replies = [FOOD]
        await self.read(hub)
        body = self.asked[0]
        self.assertEqual(sorted(body), ['input', 'model', 'questions'])
        self.assertEqual([(b['type'], b.get('resolution')) for b in body['input']], [('text', None), ('image', 'medium')])
        self.assertEqual(set(body['questions']), {'people_at_table', 'food_or_drink_on_table', 'plates_mostly_empty',
                                                  'menu_in_hand', 'image_clear'})
        self.assertTrue(all(q['type'] == 'noul' for q in body['questions'].values()))
        self.assertNotIn('camera báo', body['input'][0]['text'].lower())   # câu mô tả trung tính

    async def test_food_implies_service_then_finished(self):
        hub = self.hub()
        occupied(hub)
        self.replies = [FOOD, FOOD, EMPTY, dict(EMPTY, menu_in_hand=0.9), EMPTY, EMPTY, EMPTY]
        await self.read(hub)
        await self.read(hub)
        self.assertEqual(self.stage(hub), 'served')                       # chưa thấy nhân viên nhưng đã có món
        await self.read(hub)
        self.assertEqual(self.stage(hub), 'served')
        await self.read(hub)                                              # đang xem thực đơn gọi thêm: chưa xong
        await self.read(hub)
        self.assertEqual(self.stage(hub), 'served')
        await self.read(hub)
        self.assertEqual(self.stage(hub), 'finished')
        n = len(self.asked)
        self.assertEqual(await self.read(hub), 'not_needed')              # ăn xong rồi: thôi không hỏi nữa
        self.assertEqual(len(self.asked), n)
        self.assertEqual([s for _, s, _ in self.stage_rows(hub)], ['seated', 'served', 'finished'])

    async def test_no_people_reading_is_ignored(self):
        hub = self.hub()
        occupied(hub)
        self.replies = [dict(FOOD, people_at_table=0.1)]
        await self.read(hub)
        await self.read(hub)
        self.assertEqual(self.stage(hub), 'seated')

    async def test_due_logic(self):
        hub = self.hub()
        occupied(hub)
        self.replies = [NO_FOOD, FOOD, FOOD]
        self.assertEqual(await self.read(hub, step=3), 'not_due')         # vừa ngồi: chưa xem
        self.assertEqual(await self.read(hub, step=8), 'started')         # sớm sau khi ngồi
        self.assertEqual(await self.read(hub, step=20), 'not_due')
        self.assertEqual(await self.read(hub, step=20), 'not_due')
        self.assertEqual(await self.read(hub, step=21), 'started')        # rồi mỗi table_check_s (60) giây
        self.assertEqual(await self.read(hub, step=5), 'not_due')
        self.assertEqual(await self.read(hub, step=11), 'started')        # lần trước nói có món: xem lại sớm
        self.assertEqual(self.stage(hub), 'served')
        hub.edge_event(dict(kind='nv_den', camera='cam1', table='B1'))    # nhân viên vừa tới: kéo lượt xem lại gần
        self.assertEqual(await self.read(hub, step=5), 'not_due')
        self.assertEqual(await self.read(hub, step=16), 'started')
        self.assertEqual(len(self.asked), 4)

    async def test_rate_cap_and_off_switch(self):
        hub = self.hub()
        occupied(hub)
        self.replies = [NO_FOOD]
        hub.stages.calls.extend([self.c.t] * giai_doan.MAX_PER_MIN)       # các bàn khác đã dùng hết lượt của phút này
        self.assertEqual(await self.read(hub, step=30), 'rate_limited')
        self.assertEqual(await self.read(hub, step=31), 'started')
        hub.update_settings(dict(table_check_s=0))                        # 0 = tắt
        self.assertEqual(await self.read(hub, step=600), 'off')
        self.assertEqual(len(self.asked), 1)

    async def test_flicker_and_new_seating(self):
        hub = self.hub(decision=False)
        occupied(hub)
        hub.stages.on_staff('B1')
        seat = hub.stages.st['B1']['seat']
        occupied(hub, state='trong', people=0)                            # camera báo trống thoáng qua
        self.c.t += 3
        hub.tick()
        self.assertEqual(self.stage(hub), 'greeted')
        occupied(hub)
        self.c.t += 60
        hub.tick()
        self.assertEqual((self.stage(hub), hub.stages.st['B1']['seat']), ('greeted', seat))
        occupied(hub, state='trong', people=0)                            # trống thật
        self.c.t += giai_doan.LEFT_GRACE_S + 1
        hub.tick()
        self.assertEqual(self.stage(hub), 'left')
        occupied(hub)                                                     # lượt khách mới: bắt đầu lại
        self.assertEqual(self.stage(hub), 'seated')
        self.assertEqual(hub.stages.st['B1']['seat'], seat + 1)
        occupied(hub, state='can_don', people=0)                          # camera báo cần dọn: chờ một nhịp rồi mới kết luận
        self.assertEqual(self.stage(hub), 'seated')
        self.c.t += giai_doan.LEFT_GRACE_S + 1
        hub.tick()
        self.assertEqual(self.stage(hub), 'left')
        self.assertEqual(self.stage_rows(hub)[-2:], [('left', 'seated', 'camera'), ('seated', 'left', 'camera')])

    async def test_two_cameras_same_table(self):
        hub = self.hub(decision=False)
        occupied(hub, 'cam1')
        occupied(hub, 'cam2')
        self.assertEqual(len(self.stage_rows(hub)), 1)                    # một lượt khách, không phải hai
        hub.edge_event(dict(kind='nv_den', camera='cam2', table='B1'))
        self.assertEqual((self.stage(hub, cam='cam1'), self.stage(hub, cam='cam2')), ('greeted', 'greeted'))
        occupied(hub, 'cam1', state='trong', people=0)                    # cam1 bị che, cam2 vẫn thấy khách
        self.c.t += 60
        hub.tick()
        self.assertEqual(self.stage(hub, cam='cam2'), 'greeted')
        occupied(hub, 'cam2', state='trong', people=0)
        self.c.t += 60
        hub.tick()
        self.assertEqual((self.stage(hub, cam='cam1'), self.stage(hub, cam='cam2')), ('left', 'left'))

    async def test_snap_storage_and_unknown_table(self):
        hub = self.hub(decision=False)
        hub.set_zones(dict(camera='cam1', frame_w=100, frame_h=100,
                           tables=[dict(id='B1', polygon=[[0, 0], [10, 0], [10, 10]])]))
        hub.edge_tables('cam1', [dict(id='B1', state='co_khach', people=1), dict(id='B9', state='co_khach', people=1)])
        self.assertEqual(hub.stages.snap('cam1', 'B9', JPEG), dict(ok=False, reason='unknown_table'))   # không có vùng
        self.assertEqual(hub.stages.snap('cam7', 'B1', JPEG)['ok'], False)
        self.assertIsNone(hub.stages.snap_file('B1'))
        with self.assertRaises(ValueError):
            hub.stages.snap('cam1', 'B1', b'khong phai jpeg')
        # giờ camera gửi sai (tương lai, lùi về quá khứ) không ảnh hưởng: máy chủ dùng đồng hồ của mình
        self.assertTrue(hub.stages.snap('cam1', 'B1', JPEG + b'1', ts=9e12)['ok'])
        self.assertTrue(hub.stages.snap('cam1', 'B1', JPEG + b'2', ts=-5)['ok'])
        f = hub.stages.snap_file('B1')
        self.assertEqual(f, Path(self.tmp.name) / 'snaps' / 'cam1_B1.jpg')
        self.assertEqual(f.read_bytes(), JPEG + b'2')                     # chỉ giữ ảnh mới nhất
        self.assertIsNone(hub.stages.snap_file('B1', 'cam2'))
        self.assertIsInstance(hub.tables['cam1/B1']['snap_at'], int)
        hub.reset()
        self.assertFalse(f.exists())

    async def test_snap_while_check_in_flight_and_reset(self):
        gate = asyncio.Event()

        async def slow(req):
            self.asked.append(1)
            await gate.wait()
            return decision_json(**FOOD)
        hub = Hub(Path(self.tmp.name), decision_gemini(slow), clock=self.c)
        occupied(hub)
        self.c.t += 60
        self.assertEqual(hub.stages.snap('cam1', 'B1', JPEG)['check'], 'started')
        await asyncio.sleep(0.01)
        self.c.t += 600
        self.assertEqual(hub.stages.snap('cam1', 'B1', JPEG)['check'], 'busy')    # mỗi bàn một lần hỏi
        hub.reset()                                                       # bắt đầu ca mới khi đang hỏi dở
        occupied(hub)
        gate.set()
        await drain(hub)
        self.assertEqual(len(self.asked), 1)
        self.assertEqual(hub.stages.st['B1']['n_food'], 0)                # kết quả của lượt cũ bị bỏ
        self.assertEqual(self.stage(hub), 'seated')

    async def test_result_after_guests_left_is_dropped(self):
        gate = asyncio.Event()

        async def slow(req):
            await gate.wait()
            return decision_json(**FOOD)
        hub = Hub(Path(self.tmp.name), decision_gemini(slow), clock=self.c)
        occupied(hub)
        hub.stages.st['B1']['n_food'] = 1
        self.c.t += 60
        hub.stages.snap('cam1', 'B1', JPEG)
        await asyncio.sleep(0.01)
        hub.edge_event(dict(kind='khach_roi', camera='cam1', table='B1'))
        self.c.t += giai_doan.LEFT_GRACE_S + 1
        hub.stages.tick()
        gate.set()
        await drain(hub)
        self.assertEqual(self.stage(hub), 'left')

    async def test_errors_never_touch_alerts(self):
        hub = self.hub(verify_kinds=[], table_check_s=20)
        occupied(hub)
        self.replies = [httpx.Response(429, text='quota'),
                        httpx.Response(200, json={'answers': {}, 'prompt_feedback': {'block_reason': 'image_safety'}}),
                        httpx.Response(500, text='hỏng'), FOOD]
        for _ in range(3):
            self.assertEqual(await self.read(hub, step=30), 'started')
        self.assertEqual(self.stage(hub), 'seated')
        self.assertEqual(await self.read(hub, step=30), 'breaker_open')            # ba lỗi liên tiếp: tạm ngừng hỏi ảnh bàn
        self.assertEqual(hub.breaker.state, 'closed')                     # bộ ngắt của cảnh báo không bị đụng
        self.assertTrue(hub.edge_event(ev(images=False)))                 # cảnh báo vẫn chạy bình thường
        errs = [r['data'].get('error') for r in hub.timeline.query(kinds='table_check')]
        self.assertEqual(len(errs), 3)
        self.assertIn('image_safety', errs[1])
        self.c.t += 61                                                    # hết thời gian nghỉ: thử lại một lần
        self.assertEqual(await self.read(hub), 'started')
        self.assertEqual(hub.stages.breaker.state, 'closed')

    async def test_timeout(self):
        async def hang(req):
            await asyncio.sleep(5)
            return decision_json(**FOOD)
        hub = Hub(Path(self.tmp.name), decision_gemini(hang), clock=self.c)
        hub.stages.timeout_s = 0.05
        occupied(hub)
        self.assertEqual(await self.read(hub), 'started')
        self.assertEqual((self.stage(hub), hub.stages.st['B1']['busy'], hub.stages.breaker.n), ('seated', False, 1))

    async def test_alert_breaker_open_skips_table_checks(self):
        hub = self.hub()
        occupied(hub)
        for _ in range(3):
            hub.breaker.failure()                                         # Gemini đang hỏng với cảnh báo
        self.replies = [FOOD]
        self.assertEqual(await self.read(hub, step=30), 'breaker_open')
        self.assertEqual(self.asked, [])

    async def test_restart_mid_seating(self):
        hub = self.hub(decision=False)
        occupied(hub)
        hub.stages.on_staff('B1')
        hub.close()
        hub2 = self.hub(decision=False)                                   # máy chủ khởi động lại giữa bữa
        self.assertEqual(hub2.tables, {})
        hub2.tick()
        self.assertEqual(hub2.stages.snap('cam1', 'B1', JPEG)['ok'], False)
        occupied(hub2)
        self.assertEqual(self.stage(hub2), 'seated')                      # dựng lại từ đầu, không lỗi
        self.assertEqual([s for _, s, _ in self.stage_rows(hub2)], ['seated', 'greeted', 'seated'])   # lịch sử còn

    async def test_settings_validation(self):
        hub = self.hub(decision=False)
        v = hub.update_settings(dict(wait_greet_s=0, wait_food_s=300.5, table_check_s=30))
        self.assertEqual((v['wait_greet_s'], v['wait_food_s'], v['table_check_s'], v['wait_bill_s']), (0, 300.5, 30, 600))
        for bad in (dict(wait_bill_s=-1), dict(table_check_s='60'), dict(wait_greet_s=None), dict(wait_food_s=True),
                    dict(wait_bill_s=1e9)):
            with self.assertRaises(ValueError):
                hub.update_settings(dict(bad, dedup_s=99))
        self.assertEqual(hub.settings['dedup_s'], 20)                     # gói sai thì không áp dụng phần nào


class TestNhac(Base):
    def nudges(self, hub):
        return [r['data']['nudge'] for r in hub.timeline.query(kinds='nudge')]

    async def test_greet_nudge_once_and_creates_task(self):
        hub = self.hub(decision=False, verify_kinds=[])
        occupied(hub)
        self.c.t += 179
        hub.tick()
        self.assertEqual(self.nudges(hub), [])
        self.c.t += 2
        hub.tick()
        self.assertEqual(self.nudges(hub), ['greet'])
        e = next(x for x in hub.log if x['kind'] == 'nudge')
        self.assertEqual(e['text'], 'Bàn B1 ngồi khá lâu mà chưa ai ra tiếp')    # chữ thường ngày, không có số giây
        tb = hub.tables['cam1/B1']
        self.assertEqual(tb['nudge'], 'greet')
        self.assertIsInstance(tb['nudge_at'], int)
        tasks = list(hub.alerts.values())
        self.assertEqual([(a['kind'], a['table'], a['status']) for a in tasks], [('new_guest', 'B1', 'open')])
        for _ in range(5):                                                # ngồi rất lâu: không nhắc lại
            self.c.t += 3600
            hub.tick()
        self.assertEqual(self.nudges(hub), ['greet'])
        self.assertEqual(len(hub.alerts), 1)
        hub.edge_event(dict(kind='nv_den', camera='cam1', table='B1'))    # có người tới: hết dấu nhắc trên bàn
        self.assertEqual((self.stage(hub), hub.tables['cam1/B1']['nudge']), ('greeted', None))

    async def test_greet_nudge_does_not_duplicate_open_task(self):
        hub = self.hub(decision=False, verify_kinds=[], auto_close_s=0)
        occupied(hub)
        aid = hub.edge_event(ev('khach_moi', images=False))
        self.c.t += 200
        hub.tick()
        self.assertEqual(self.nudges(hub), ['greet'])
        self.assertEqual(list(hub.alerts), [aid])
        self.assertEqual(hub.alerts[aid]['repeats'], 0)

    async def test_wait_settings_zero_turn_nudges_off(self):
        hub = self.hub(decision=False, wait_greet_s=0)
        occupied(hub)
        self.c.t += 99999
        hub.tick()
        self.assertEqual(self.nudges(hub), [])
        self.assertEqual(hub.alerts, {})

    async def test_food_nudge_needs_a_reading(self):
        hub = self.hub(decision=False)
        occupied(hub)
        hub.stages.on_staff('B1')
        self.c.t += 5000
        hub.tick()
        self.assertEqual(self.nudges(hub), [])                            # không có AI xem ảnh: không đoán
        self.tmp2 = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp2.cleanup)
        hub = Hub(Path(self.tmp2.name), decision_gemini(self.handler), clock=self.c)
        occupied(hub)
        hub.stages.on_staff('B1')
        self.replies = [NO_FOOD]
        await self.read(hub, step=800)
        hub.tick()
        self.assertEqual(self.nudges(hub), [])
        self.c.t += 101
        hub.tick()
        self.assertEqual(self.nudges(hub), ['food'])
        self.assertEqual(hub.log[0]['text'], 'Bàn B1 chờ khá lâu mà chưa thấy món lên')
        self.assertEqual(hub.alerts, {})                                  # nhắc mềm: không tạo việc

    async def test_bill_nudge(self):
        hub = self.hub()
        for table in ('B1', 'B2'):
            occupied(hub, table=table)
            hub.stages.on_staff(table)
            self.replies = [FOOD, FOOD, EMPTY, EMPTY]
            for _ in range(4):
                await self.read(hub, table=table)
            self.assertEqual(self.stage(hub, table), 'finished')
        self.c.t += 300
        hub.edge_event(dict(kind='nv_den', camera='cam1', table='B2'))    # B2 đã có nhân viên ghé sau khi ăn xong
        self.c.t += 400
        hub.tick()
        rows = hub.timeline.query(kinds='nudge')
        self.assertEqual([(r['table'], r['data']['nudge']) for r in rows], [('B1', 'bill')])
        self.assertIn('chờ tính tiền', rows[0]['text'])
        self.c.t += 99999
        hub.tick()
        self.assertEqual(len(hub.timeline.query(kinds='nudge')), 1)


class TestDuongApi(unittest.TestCase):
    """Các đường mới trên app thật: ảnh bàn, dòng thời gian, kiểm tra cài đặt."""

    def setUp(self):
        from fastapi.testclient import TestClient
        from server import app as app_module
        self.m = app_module
        self.hub = app_module.hub
        cu, self.hub.gemini = self.hub.gemini, FakeGemini([{}])           # không bao giờ gọi Gemini thật trong test
        self.addCleanup(setattr, self.hub, 'gemini', cu)
        self.addCleanup(self.hub.reset)
        self.client = TestClient(app_module.app)
        self.h = {'X-Edge-Key': app_module.EDGE_KEY} if app_module.EDGE_KEY else {}

    def test_snap_and_timeline_routes(self):
        c, cam = self.client, 'camthu'
        b64 = base64.b64encode(JPEG).decode()
        self.assertEqual(c.get('/api/tables/T1/snap.jpg').status_code, 404)
        r = c.post('/api/edge/table-snap', headers=self.h, json=dict(camera=cam, table='T1', ts=1.0, jpeg_b64=b64))
        self.assertEqual(r.json(), dict(ok=False, reason='unknown_table'))
        c.post('/api/edge/tables', headers=self.h, json=dict(camera=cam, tables=[dict(id='T1', state='co_khach', people=2)]))
        r = c.post('/api/edge/table-snap', headers=self.h, json=dict(camera=cam, table='T1', ts=1.0, jpeg_b64=b64))
        self.assertEqual((r.status_code, r.json()['ok']), (200, True))
        self.assertEqual(c.post('/api/edge/table-snap', headers=self.h, json=dict(camera=cam, table='T1')).status_code, 400)
        self.assertEqual(c.post('/api/edge/table-snap', headers=self.h,
                                json=dict(camera=cam, table='T1', jpeg_b64='!!!')).status_code, 400)
        r = c.get('/api/tables/T1/snap.jpg')
        self.assertEqual((r.status_code, r.content, r.headers['content-type']), (200, JPEG, 'image/jpeg'))
        tb = next(t for t in c.get('/api/state').json()['tables'] if t['camera'] == cam)
        self.assertEqual(tb['stage'], 'seated')
        self.assertIsInstance(tb['stage_since'], int)
        rows = c.get('/api/timeline', params=dict(table='T1', kind='stage,table')).json()['rows']
        self.assertEqual(sorted(r['kind'] for r in rows), ['stage', 'table'])
        self.assertEqual(c.get('/api/timeline', params=dict(table='T1', kind='stage', limit=1, newest=True)).json()
                         ['rows'][0]['data']['stage'], 'seated')
        self.assertEqual(c.get('/api/timeline', params=dict(since=9e12)).json(), dict(rows=[]))
        self.assertEqual(len(c.get('/api/timeline/days').json()['days']), 1)

    def test_settings_route_validates(self):
        cu = dict(self.hub.settings)
        self.addCleanup(self.hub.update_settings, {k: cu[k] for k in ('wait_greet_s', 'table_check_s')})
        r = self.client.put('/api/settings', json=dict(wait_greet_s=120, table_check_s=0))
        self.assertEqual((r.status_code, r.json()['wait_greet_s'], r.json()['table_check_s']), (200, 120, 0))
        self.assertEqual(self.client.put('/api/settings', json=dict(wait_greet_s='lâu')).status_code, 400)


if __name__ == '__main__':
    unittest.main(verbosity=2)
