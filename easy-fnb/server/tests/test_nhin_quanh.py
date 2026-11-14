"""Tín hiệu mềm "khách nhìn quanh tìm nhân viên": không tạo việc, chỉ ghi nhật ký và đánh dấu bàn."""
import asyncio
import tempfile
import unittest
from pathlib import Path

from server.gemini import decide
from server.hub import Hub
from server.tests.test_xac_minh import FakeGemini, decision_gemini, decision_json, ev


def look_ev(score):
    return dict(ev('nhin_quanh', images=False), score=score)


class TestNhinQuanh(unittest.IsolatedAsyncioTestCase):
    def test_rules(self):
        d = lambda **p: decide('looking', dict(probs=p))[0]
        self.assertEqual(d(looking_around_for_someone=0.85, image_clear=0.9), 'confirm')
        self.assertEqual(d(looking_around_for_someone=0.1, image_clear=0.9), 'reject')
        self.assertEqual(d(looking_around_for_someone=0.5, image_clear=0.9), 'unverified')
        self.assertEqual(d(looking_around_for_someone=0.9, wearing_staff_uniform=0.8), 'reject')

    async def test_soft_signal_marks_table_without_task(self):
        with tempfile.TemporaryDirectory() as d:
            hub = Hub(Path(d), FakeGemini([]))
            hub.edge_tables('cam1', [dict(id='B1', state='co_khach', people=2)])
            self.assertIsNone(hub.edge_event(look_ev(0.7)))
            self.assertEqual(hub.alerts, {})
            self.assertTrue(hub.tables['cam1/B1']['looking_at'])
            self.assertEqual(hub.log[0]['kind'], 'looking')

    async def test_unsure_asks_gemini_and_drops_on_reject(self):
        asked = []

        def h(req):
            asked.append(1)
            return decision_json(looking_around_for_someone=0.08, wearing_staff_uniform=0.05, image_clear=0.9)
        with tempfile.TemporaryDirectory() as d:
            hub = Hub(Path(d), decision_gemini(h))
            hub.edge_tables('cam1', [dict(id='B1', state='co_khach', people=2)])
            hub.edge_event(look_ev(0.7))
            for _ in range(50):
                await asyncio.sleep(0.01)
                if asked:
                    break
            await asyncio.sleep(0.05)
            self.assertEqual(len(asked), 1)
            self.assertNotIn('looking_at', hub.tables['cam1/B1'])
            hub.edge_event(look_ev(1.0))                     # camera đã chắc: không hỏi nữa
            self.assertEqual(len(asked), 1)
            self.assertTrue(hub.tables['cam1/B1']['looking_at'])


class TestGopViecTrung(unittest.IsolatedAsyncioTestCase):
    async def test_repeat_call_merges_while_open(self):
        """Khách vẫn giơ tay sau thời gian gộp: vẫn là một việc, không giao thêm người khác."""
        with tempfile.TemporaryDirectory() as d:
            hub = Hub(Path(d), FakeGemini([]), defaults=dict(verify_kinds=[], dedup_s=0))
            e = dict(ev(table=None, images=False), box=[100, 100, 200, 300])
            a1 = hub.edge_event(e)
            a2 = hub.edge_event(dict(e, box=[160, 100, 260, 300]))       # nhích sang bên một chút
            a3 = hub.edge_event(dict(e, box=[500, 100, 600, 300]))       # người khác, ở chỗ khác
            self.assertEqual(a1, a2)
            self.assertNotEqual(a1, a3)
            self.assertEqual(hub.alerts[a1]['repeats'], 1)
