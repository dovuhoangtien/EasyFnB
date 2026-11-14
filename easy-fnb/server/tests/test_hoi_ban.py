"""Khớp bàn khi camera không chắc: POST /api/edge/table-ask, máy chủ hỏi Gemini Decision (server/hoi_ban.py).

Không cần mạng, không cần khoá: Gemini Decision giả lập bằng httpx.MockTransport, giờ giả bằng FakeClock.
Chạy (trong easy-fnb):  python -m unittest server.tests.test_hoi_ban -v
"""
import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path

import httpx

_tmp = tempfile.TemporaryDirectory()
os.environ.setdefault('DATA_DIR', _tmp.name)   # đặt trước khi nạp server.app, để không đụng dữ liệu thật

from server.hub import Hub  # noqa: E402
from server.tests.test_xac_minh import JPEG, FakeClock, FakeGemini, decision_gemini, decision_json  # noqa: E402

TABLES = [dict(table='B3', color='cam'), dict(table='B4', color='xanh dương')]


class TestHoiBan(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.c = FakeClock()
        self.asked = []
        self.reply = dict(at_0=0.76, at_1=0.13, seated=0.88, image_clear=0.73)

    def handler(self, req):
        self.asked.append(json.loads(req.content))
        r = self.reply
        return r if isinstance(r, httpx.Response) else decision_json(**r)

    def hub(self, decision=True):
        g = decision_gemini(self.handler) if decision else FakeGemini([{}])
        h = Hub(Path(self.tmp.name), g, clock=self.c)
        self.addCleanup(h.close)
        return h

    async def test_ask_returns_probs_by_table(self):
        hub = self.hub()
        r = await hub.hoi_ban.ask('cam1', JPEG, TABLES)
        self.assertTrue(r['ok'])
        self.assertEqual(r['probs'], {'B3': 0.76, 'B4': 0.13})
        body = self.asked[0]
        self.assertEqual(sorted(body), ['input', 'model', 'questions'])
        self.assertEqual(set(body['questions']), {'at_0', 'at_1', 'seated', 'image_clear'})
        self.assertIn('viền cam', body['questions']['at_0']['instructions'])
        self.assertIn('Viền xanh dương là bàn B4', body['input'][0]['text'])
        self.assertEqual(body['input'][1]['resolution'], 'medium')

    async def test_rate_limit_per_camera(self):
        hub = self.hub()
        await hub.hoi_ban.ask('cam1', JPEG, TABLES)
        self.assertEqual((await hub.hoi_ban.ask('cam1', JPEG, TABLES))['reason'], 'too_often')
        self.assertTrue((await hub.hoi_ban.ask('cam2', JPEG, TABLES))['ok'])     # camera khác vẫn hỏi được
        self.c.t += 8
        self.assertTrue((await hub.hoi_ban.ask('cam1', JPEG, TABLES))['ok'])
        self.assertEqual(len(self.asked), 3)

    async def test_decision_off(self):
        hub = self.hub(decision=False)
        self.assertEqual(await hub.hoi_ban.ask('cam1', JPEG, TABLES), dict(ok=False, reason='decision_off'))

    async def test_not_seated(self):
        self.reply = dict(at_0=0.5, at_1=0.4, seated=0.1, image_clear=0.9)
        r = await self.hub().hoi_ban.ask('cam1', JPEG, TABLES)
        self.assertEqual((r['ok'], r['reason']), (False, 'not_seated'))

    async def test_error_opens_breaker(self):
        self.reply = httpx.Response(500, text='lỗi')
        hub = self.hub()
        for _ in range(3):
            self.assertEqual((await hub.hoi_ban.ask('cam1', JPEG, TABLES))['reason'], 'error')
            self.c.t += 10
        self.assertEqual((await hub.hoi_ban.ask('cam1', JPEG, TABLES))['reason'], 'breaker_open')
        self.assertEqual(len(self.asked), 3)

    async def test_timeout(self):
        hub = self.hub()
        hub.hoi_ban.timeout_s = 0.05

        async def slow(jpeg, pairs):
            await asyncio.sleep(1)
        hub.gemini.table_ask = slow
        self.assertEqual((await hub.hoi_ban.ask('cam1', JPEG, TABLES))['reason'], 'timeout')

    async def test_bad_input(self):
        hub = self.hub()
        for tables in (None, [], TABLES[:1], TABLES * 2, [dict(table='B1', color='đỏ'), TABLES[1]]):
            with self.assertRaises(ValueError):
                await hub.hoi_ban.ask('cam1', JPEG, tables)
        with self.assertRaises(ValueError):
            await hub.hoi_ban.ask('cam1', b'', TABLES)
        self.assertEqual(self.asked, [])


class TestEndpoint(unittest.TestCase):
    def test_route(self):
        import base64

        from fastapi.testclient import TestClient

        from server import app as app_module
        with TestClient(app_module.app) as c:
            r = c.post('/api/edge/table-ask', json=dict(camera='cam1', jpeg_b64=base64.b64encode(JPEG).decode(),
                                                        tables=TABLES))
            self.assertEqual(r.status_code, 200)
            self.assertIn('ok', r.json())
            self.assertEqual(c.post('/api/edge/table-ask', json=dict(camera='cam1', jpeg_b64='', tables=TABLES)).status_code,
                             400)


if __name__ == '__main__':
    unittest.main()
