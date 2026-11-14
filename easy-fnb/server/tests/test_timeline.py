"""Dòng thời gian lâu dài (SQLite): ghi, đọc, lọc, còn sau khi khởi động lại, không làm hỏng Hub khi ổ đĩa lỗi.

Chạy (trong easy-fnb):  python -m unittest server.tests.test_timeline -v
"""
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path

from server.hub import Hub
from server.tests.test_xac_minh import FakeGemini, call_resp, ev, wait_verified
from server.timeline import Timeline, day_of


class TestTimeline(unittest.TestCase):
    def test_add_query_filters(self):
        with tempfile.TemporaryDirectory() as d:
            tl = Timeline(Path(d) / 'timeline.db')
            tl.add('log', ts=100.0, table='B1', camera='cam1', text='Bàn B1 gọi phục vụ', log_kind='call')
            tl.add('alert_created', ts=101.0, table='B1', camera='cam1', alert_id='a1', staff='lan', alert_kind='call')
            tl.add('alert_done', ts=130.5, table='B1', alert_id='a1', staff='lan', wait_s=12.5)
            tl.add('stage', ts=140.0, table='B2', stage='seated')
            rows = tl.query()
            self.assertEqual([r['kind'] for r in rows], ['log', 'alert_created', 'alert_done', 'stage'])
            self.assertEqual(set(rows[0]), {'id', 'ts', 'day', 'camera', 'table', 'kind', 'alert_id', 'staff',
                                            'text', 'data'})
            self.assertEqual(rows[0]['data'], {'log_kind': 'call'})
            self.assertEqual(rows[0]['text'], 'Bàn B1 gọi phục vụ')
            self.assertEqual(rows[2]['data']['wait_s'], 12.5)
            self.assertEqual(rows[3]['data'], {'stage': 'seated'})
            self.assertEqual([r['kind'] for r in tl.query(table='B2')], ['stage'])
            self.assertEqual(len(tl.query(alert_id='a1')), 2)
            self.assertEqual(len(tl.query(kinds='alert_*')), 2)
            self.assertEqual(len(tl.query(kinds=['log', 'stage'])), 2)
            self.assertEqual(tl.query(kinds='alert*')[0]['kind'], 'alert_created')
            self.assertEqual([r['ts'] for r in tl.query(since=101, until=131)], [101.0, 130.5])
            self.assertEqual([r['ts'] for r in tl.query(limit=2)], [100.0, 101.0])
            self.assertEqual([r['ts'] for r in tl.query(limit=2, newest_first=True)], [140.0, 130.5])

    def test_days_in_vietnam_time(self):
        self.assertEqual(day_of(0), '1970-01-01')
        self.assertEqual(day_of(17 * 3600), '1970-01-01')       # 00:00 ở Việt Nam: ca tối vẫn thuộc ngày cũ
        self.assertEqual(day_of(21 * 3600), '1970-01-02')       # 04:00 ở Việt Nam: ngày của quán đổi
        with tempfile.TemporaryDirectory() as d:
            tl = Timeline(Path(d) / 'timeline.db')
            self.assertEqual(tl.days(), [])
            tl.add('log', ts=21 * 3600 + 5)
            tl.add('log', ts=10.0)
            self.assertEqual(tl.days(), ['1970-01-01', '1970-01-02'])
            self.assertEqual(tl.query()[0]['day'], '1970-01-01')

    def test_persists_and_dir_can_be_deleted(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / 'timeline.db'
            tl = Timeline(f)
            tl.add('log', text='trước khi tắt')
            tl.close()
            tl2 = Timeline(f)                                    # máy chủ khởi động lại
            tl2.add('log', text='sau khi bật lại')
            self.assertEqual([r['text'] for r in tl2.query()], ['trước khi tắt', 'sau khi bật lại'])
        self.assertFalse(Path(d).exists())                       # không còn kết nối nào giữ tệp (Windows)

    def test_buffer_flushes_when_full(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / 'timeline.db'
            tl = Timeline(f)
            for i in range(150):
                tl.add('log', ts=float(i))
            with sqlite3.connect(f) as c:
                n = c.execute('SELECT COUNT(*) FROM timeline').fetchone()[0]
            c.close()
            self.assertEqual(n, 100)                             # lô đầu đã ghi mà không cần ai gọi flush
            self.assertEqual(len(tl.query(limit=1000)), 150)

    def test_weird_data_never_raises(self):
        with tempfile.TemporaryDirectory() as d:
            tl = Timeline(Path(d) / 'timeline.db')
            tl.add('log', ts='không phải số')                    # bỏ dòng này, không ném lỗi
            tl.add('log', ts=5.0, obj=object(), path=Path('x'), s={1, 2})
            rows = tl.query()
            self.assertEqual(len(rows), 1)
            self.assertIn('obj', rows[0]['data'])

    def test_disk_error_keeps_running(self):
        with tempfile.TemporaryDirectory() as d:
            tl = Timeline(Path(d) / 'khong' / 'co' / 'timeline.db')      # thư mục không tồn tại
            tl.add('log', text='x')
            self.assertFalse(tl.flush())
            self.assertEqual(tl.query(), [])
            self.assertEqual(tl.days(), [])
            (Path(d) / 'khong' / 'co').mkdir(parents=True)                # ổ đĩa có lại: dòng đang chờ được ghi
            self.assertEqual([r['text'] for r in tl.query()], ['x'])

    def test_locked_database_keeps_rows_for_later(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / 'timeline.db'
            tl = Timeline(f)
            tl.add('log', text='một')
            tl.flush()
            other = sqlite3.connect(f, isolation_level=None)
            other.execute('BEGIN EXCLUSIVE')                     # tiến trình khác đang khoá tệp
            try:
                tl.add('log', text='hai')
                t0 = time.perf_counter()
                self.assertFalse(tl.flush())
                self.assertLess(time.perf_counter() - t0, 2.0)   # không treo vòng lặp của máy chủ
            finally:
                other.execute('ROLLBACK')
                other.close()
            self.assertEqual([r['text'] for r in tl.query()], ['một', 'hai'])


class TestHubGhi(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def hub(self, script=(), **defaults):
        return Hub(Path(self.tmp.name), FakeGemini(list(script) or [{}]), defaults=defaults or None)

    def kinds(self, hub, **kw):
        return [r['kind'] for r in hub.timeline.query(**kw)]

    async def test_alert_lifecycle(self):
        hub = self.hub(verify_kinds=[])
        aid = hub.edge_event(ev(images=False))
        hub.ack(aid, 'minh')                                     # người khác nhận: có dòng đổi người
        hub.done(aid, 'minh')
        hub.done(aid, 'minh')                                    # bấm lại không ghi thêm
        rows = hub.timeline.query(alert_id=aid, kinds='alert_*')
        self.assertEqual([r['kind'] for r in rows], ['alert_created', 'alert_assigned', 'alert_acked', 'alert_done'])
        self.assertEqual(rows[0]['staff'], 'lan')
        self.assertEqual(rows[0]['data']['alert_kind'], 'call')
        self.assertEqual((rows[1]['staff'], rows[1]['data']['prev']), ('minh', 'lan'))
        self.assertIsInstance(rows[2]['data']['wait_s'], float)
        self.assertEqual((rows[3]['staff'], rows[3]['data']['by']), ('minh', 'minh'))
        self.assertEqual((rows[3]['table'], rows[3]['camera']), ('B1', 'cam1'))
        logs = hub.timeline.query(kinds='log', table='B1')       # mọi dòng nhật ký của Hub cũng được chép
        self.assertEqual([r['data']['log_kind'] for r in logs], ['call', 'ack', 'done'])
        self.assertEqual(logs[0]['text'], hub.log[-1]['text'])

    async def test_verify_reject_and_unverified(self):
        hub = self.hub([call_resp('KHONG_GOI', hand=False), 'err'], hold_until_verified=['call'])
        a1 = hub.edge_event(ev())
        await wait_verified(hub, a1)
        a2 = hub.edge_event(ev(table='B2'))
        await wait_verified(hub, a2)
        self.assertEqual(self.kinds(hub, alert_id=a1, kinds='alert_*'),
                         ['alert_created', 'alert_rejected', 'alert_cancelled'])
        k2 = self.kinds(hub, alert_id=a2, kinds='alert_*')
        self.assertEqual(k2, ['alert_created', 'alert_unverified', 'alert_assigned'])
        self.assertEqual(hub.timeline.query(alert_id=a2, kinds='alert_unverified')[0]['data']['path'], 'error')

    async def test_camera_arrival_and_auto_close(self):
        hub = self.hub(verify_kinds=[], auto_close_s=1)
        a1 = hub.edge_event(ev(images=False))
        hub.edge_event(dict(kind='nv_den', camera='cam1', table='B1'))
        rows = hub.timeline.query(alert_id=a1, kinds=['alert_acked', 'alert_done'])
        self.assertEqual([r['kind'] for r in rows], ['alert_acked', 'alert_done'])
        self.assertTrue(rows[0]['data']['by_camera'])
        self.assertEqual(rows[1]['data']['by'], 'camera')
        a2 = hub.edge_event(ev(table='B2', images=False))
        hub.alerts[a2]['created_at'] -= 5000                     # không ai nhận, quá hạn tự đóng
        hub.tick()
        self.assertEqual(self.kinds(hub, alert_id=a2, kinds='alert_*'), ['alert_created', 'alert_auto_closed'])

    async def test_table_staff_and_reset_keep_history(self):
        hub = self.hub(verify_kinds=[])
        hub.edge_tables('cam1', [dict(id='B1', state='co_khach', people=2)])
        hub.edge_tables('cam1', [dict(id='B1', state='co_khach', people=3)])     # chỉ đổi số người: không ghi
        hub.edge_tables('cam1', [dict(id='B1', state='can_don', people=0)])
        rows = hub.timeline.query(kinds='table')
        self.assertEqual([(r['data']['prev'], r['data']['state']) for r in rows],
                         [(None, 'occupied'), ('occupied', 'needs_clearing')])
        hub.staff_online('lan', +1)
        hub.staff_online('lan', -1)
        del hub.pending_off['lan']
        hub._finish_off('lan')
        self.assertEqual([(r['kind'], r['staff']) for r in hub.timeline.query(kinds='staff_*')],
                         [('staff_online', 'lan'), ('staff_offline', 'lan')])
        aid = hub.edge_event(ev(images=False))
        n = len(hub.timeline.query(limit=5000))
        hub.reset()                                              # bắt đầu ca mới: lịch sử còn nguyên
        after = hub.timeline.query(limit=5000)
        self.assertGreater(len(after), n)
        self.assertIn('shift_reset', [r['kind'] for r in after])
        self.assertTrue(hub.timeline.query(alert_id=aid))
        a_new = hub.edge_event(ev(images=False))                 # mã việc đếm tiếp, việc mới vẫn được ghi là mới
        self.assertNotEqual(a_new, aid)
        self.assertEqual(self.kinds(hub, alert_id=a_new, kinds='alert_created'), ['alert_created'])
        self.assertEqual(len(hub.timeline.days()), 1)

    async def test_broken_timeline_does_not_break_hub(self):
        hub = self.hub(verify_kinds=[])
        hub.timeline.path = Path(self.tmp.name) / 'mat' / 'timeline.db'          # ổ đĩa hỏng giữa ca
        aid = hub.edge_event(ev(images=False))
        hub.edge_tables('cam1', [dict(id='B1', state='co_khach', people=2)])
        hub.tick()
        hub.done(aid, 'lan')
        hub.reset()
        hub.close()
        self.assertEqual(hub.timeline.query(), [])
        self.assertEqual(hub.log[0]['kind'], 'system')


if __name__ == '__main__':
    unittest.main(verbosity=2)
