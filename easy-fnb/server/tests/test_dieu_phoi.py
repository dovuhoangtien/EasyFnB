"""Điều phối: chống trùng (kể cả nhiều camera), chia việc, điểm danh, chuyển việc khi mất kết nối, tự đóng.

Chạy (trong easy-fnb):  python -m unittest server.tests.test_dieu_phoi -v
"""
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from server.hub import Hub


class NoGemini:
    enabled = False
    model = None


def ev(kind='goi_phuc_vu', table='B1', camera='cam1', eid=None, box=None):
    return dict(camera=camera, kind=kind, table=table, score=0.9, eid=eid, box=box)


class DieuPhoi(unittest.TestCase):
    def drop(self, hub, sid, wait_s=20):
        hub.staff_online(sid, -1)
        if sid in hub.pending_off:
            hub.pending_off[sid] -= wait_s * 1000
        hub.tick()

    def make(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        return Hub(Path(self.tmp.name), NoGemini())

    def open_alerts(self, hub):
        return [a for a in hub.alerts.values() if a['status'] not in ('done', 'cancelled')]

    def test_same_eid_sent_three_times_is_one_alert(self):
        hub = self.make()
        ids = {hub.edge_event(ev(eid='x1')) for _ in range(3)}
        self.assertEqual(len(ids), 1)
        self.assertEqual(len(self.open_alerts(hub)), 1)

    def test_same_table_jitter_is_one_alert(self):
        hub = self.make()
        for _ in range(5):
            hub.edge_event(ev(table='B3'))
        self.assertEqual(len(self.open_alerts(hub)), 1)

    def test_same_table_from_two_cameras_is_one_alert(self):
        hub = self.make()
        hub.edge_event(ev(table='B4', camera='cam1'))
        hub.edge_event(ev(table='B4', camera='cam2'))
        self.assertEqual(len(self.open_alerts(hub)), 1)

    def test_no_table_two_cameras_stay_separate(self):
        hub = self.make()
        hub.edge_event(ev(table=None, camera='cam1', box=[100, 100, 200, 300]))
        hub.edge_event(ev(table=None, camera='cam2', box=[100, 100, 200, 300]))
        self.assertEqual(len(self.open_alerts(hub)), 2)

    def test_load_is_spread_over_online_staff_only(self):
        hub = self.make()
        hub.staff_online('lan', +1)
        hub.staff_online('minh', +1)
        for i in range(1, 7):
            hub.edge_event(ev(table=f'B{i}'))
        per = Counter(a['assigned_to'] for a in self.open_alerts(hub))
        self.assertEqual(per, Counter(lan=3, minh=3))

    def test_helper_role_takes_overflow(self):
        hub = self.make()
        for s in ('lan', 'minh', 'tu'):
            hub.staff_online(s, +1)
        for i in range(1, 11):
            hub.edge_event(ev(table=f'B{i}'))
        per = Counter(a['assigned_to'] for a in self.open_alerts(hub))
        self.assertGreater(per['tu'], 0)
        self.assertLess(max(per.values()), 6)

    def test_open_work_moves_when_staff_goes_offline(self):
        hub = self.make()
        hub.staff_online('lan', +1)
        hub.staff_online('minh', +1)
        aid = hub.edge_event(ev(table='B1'))
        first = hub.alerts[aid]['assigned_to']
        self.drop(hub, first)
        self.assertNotEqual(hub.alerts[aid]['assigned_to'], first)

    def test_work_stays_if_nobody_else_is_online(self):
        hub = self.make()
        hub.staff_online('lan', +1)
        aid = hub.edge_event(ev(table='B1'))
        self.drop(hub, 'lan')
        self.assertEqual(hub.alerts[aid]['assigned_to'], 'lan')

    def test_attendance(self):
        hub = self.make()
        before = {s['id']: s for s in hub.staff_view()}
        self.assertIsNone(before['lan']['first_in'])
        hub.staff_online('lan', +1)
        on = {s['id']: s for s in hub.staff_view()}['lan']
        self.assertIsNotNone(on['first_in'])
        self.assertIsNotNone(on['on_since'])
        self.drop(hub, 'lan')
        off = {s['id']: s for s in hub.staff_view()}['lan']
        self.assertIsNone(off['on_since'])
        self.assertEqual(off['first_in'], on['first_in'])
        self.assertTrue(any('vào ca' in e['text'] for e in hub.log))

    def test_short_disconnect_is_not_leaving(self):
        hub = self.make()
        hub.staff_online('lan', +1)
        hub.staff_online('minh', +1)
        aid = hub.edge_event(ev(table='B1'))
        who = hub.alerts[aid]['assigned_to']
        hub.staff_online(who, -1)
        hub.tick()
        hub.staff_online(who, +1)
        hub.tick()
        self.assertEqual(hub.alerts[aid]['assigned_to'], who)
        self.assertEqual(len(hub.attendance[who]), 1)
        self.assertIsNone(hub.attendance[who][0]['out'])

    def test_second_connection_does_not_double_count(self):
        hub = self.make()
        hub.staff_online('lan', +1)
        hub.staff_online('lan', +1)
        hub.staff_online('lan', -1)
        self.assertIsNotNone({s['id']: s for s in hub.staff_view()}['lan']['on_since'])
        self.assertEqual(len(hub.attendance['lan']), 1)

    def test_calls_auto_close_but_clearing_does_not(self):
        hub = self.make()
        hub.settings['auto_close_s'] = 1
        call = hub.edge_event(ev(table='B1'))
        clear = hub.edge_event(ev(kind='can_don', table='B2'))
        for a in hub.alerts.values():
            a['created_at'] -= 5000
        hub.tick()
        self.assertEqual(hub.alerts[call]['status'], 'done')
        self.assertEqual(hub.alerts[clear]['status'], 'open')

    def test_no_escalation_by_default(self):
        hub = self.make()
        hub.staff_online('lan', +1)
        hub.staff_online('minh', +1)
        aid = hub.edge_event(ev(kind='can_don', table='B2'))
        who = hub.alerts[aid]['assigned_to']
        hub.alerts[aid]['created_at'] -= 600000
        hub.alerts[aid]['_assigned_at'] -= 600000
        hub.tick()
        self.assertEqual(hub.alerts[aid]['assigned_to'], who)
        self.assertFalse(hub.alerts[aid]['escalated'])

    def test_staff_arrival_closes_call_and_measures_response(self):
        hub = self.make()
        hub.staff_online('lan', +1)
        call = hub.edge_event(ev(table='B1'))
        guest = hub.edge_event(ev(kind='khach_moi', table='B1'))
        other = hub.edge_event(ev(table='B2'))
        hub.alerts[call]['created_at'] -= 12000
        hub.edge_event(ev(kind='nv_den', table='B1'))
        a = hub.alerts[call]
        self.assertEqual(a['status'], 'done')
        self.assertEqual(a['done_by'], 'camera')
        self.assertAlmostEqual(a['arrived_s'], 12, delta=1)
        self.assertEqual(a['acked_by'], 'lan')
        self.assertEqual(hub.alerts[guest]['status'], 'done')
        self.assertEqual(hub.alerts[other]['status'], 'open')
        r = hub.report()
        self.assertEqual(r['arrived'], 2)
        self.assertIsNotNone(r['response_s']['mean'])
        # xếp loại tốc độ: việc nhận sau 12 giây là nhanh, không việc nào chậm hay bị bỏ lỡ
        sp = r['speed']
        self.assertEqual(sp['fast'] + sp['ok'] + sp['slow'], sum(1 for x in hub.alerts.values() if x['acked_at']))
        self.assertGreaterEqual(sp['fast'], 1)
        self.assertEqual((sp['slow'], sp['missed']), (0, 0))
        lan = next(x for x in r['per_staff'] if x['id'] == 'lan')
        self.assertEqual(lan['fast'] + lan['ok'] + lan['slow'], lan['acked'])
        self.assertEqual(sum(lan['kinds'].values()), lan['acked'])
        # diễn biến theo thời gian: mọi việc chưa huỷ nằm trong một cột, tốc độ từng cột cộng lại bằng cả ca
        tl = r['timeline']
        self.assertGreaterEqual(len(tl['points']), 6)
        self.assertEqual(sum(p['call'] + p['needs_clearing'] + p['new_guest'] for p in tl['points']),
                         sum(1 for x in hub.alerts.values() if x['status'] != 'cancelled'))
        self.assertEqual(sum(p['fast'] for p in tl['points']), sp['fast'])
        b1 = next(x for x in r['per_table'] if x['table'] == 'B1')
        self.assertGreaterEqual(b1['fast'], 1)
        self.assertEqual(b1['missed'], 0)

    def test_staff_arrival_does_not_finish_clearing(self):
        hub = self.make()
        aid = hub.edge_event(ev(kind='can_don', table='B2'))
        hub.edge_event(ev(kind='nv_den', table='B2'))
        self.assertEqual(hub.alerts[aid]['status'], 'acked')
        self.assertIsNotNone(hub.alerts[aid]['arrived_s'])
        hub.edge_event(ev(kind='da_don', table='B2'))
        self.assertEqual(hub.alerts[aid]['status'], 'done')

    def test_repeated_arrival_is_harmless(self):
        hub = self.make()
        self.assertIsNone(hub.edge_event(ev(kind='nv_den', table='B3')))
        aid = hub.edge_event(ev(table='B3'))
        hub.edge_event(ev(kind='nv_den', table='B3'))
        t = hub.alerts[aid]['arrived_at']
        hub.edge_event(ev(kind='nv_den', table='B3'))
        self.assertEqual(hub.alerts[aid]['arrived_at'], t)
        self.assertEqual(len([a for a in hub.alerts.values()]), 1)

    def test_auto_close_without_arrival_is_counted(self):
        hub = self.make()
        hub.settings['auto_close_s'] = 1
        aid = hub.edge_event(ev(table='B1'))
        hub.alerts[aid]['created_at'] -= 5000
        hub.tick()
        self.assertEqual(hub.report()['no_arrival'], 1)
        self.assertIsNone(hub.alerts[aid].get('arrived_s'))


class VungBan(unittest.TestCase):
    """Vùng bàn sai không được ghi đè vùng đang dùng."""
    def test_tu_choi_vung_sai_va_giu_vung_cu(self):
        with tempfile.TemporaryDirectory() as tmp:
            hub = Hub(Path(tmp), NoGemini())
            tot = dict(camera='cam1', frame_w=640, frame_h=360,
                       tables=[dict(id='B1', polygon=[[0, 0], [10, 0], [10, 10]])])
            hub.set_zones(tot)
            for sai in ([dict(id='B9', polygon=[[0, 0], [1, 1]])],
                        [dict(id=' ', polygon=[[0, 0], [10, 0], [10, 10]])],
                        [dict(id='B1', polygon=[[0, 0], [10, 0], [10, 10]])] * 2):
                with self.assertRaises(ValueError):
                    hub.set_zones(dict(tot, tables=sai))
            self.assertEqual([t['id'] for t in hub.get_zones('cam1')['tables']], ['B1'])


class GhiCong(unittest.TestCase):
    def test_camera_dong_viec_thi_ghi_cong_nguoi_da_nhan(self):
        with tempfile.TemporaryDirectory() as tmp:
            hub = Hub(Path(tmp), NoGemini())
            hub.staff_online('lan', +1)
            aid = hub.edge_event(ev('khach_moi', table='B5'))
            hub.ack(aid, 'lan')
            hub.edge_event(dict(camera='cam1', kind='nv_den', table='B5'))
            self.assertEqual(hub.alerts[aid]['done_by'], 'camera')
            lan = next(x for x in hub.report()['per_staff'] if x['id'] == 'lan')
            self.assertEqual((lan['acked'], lan['done']), (1, 1))


if __name__ == '__main__':
    unittest.main()


class NapEnv(unittest.TestCase):
    def test_doc_env_khong_de_bien_da_co(self):
        import os
        import tempfile
        from server import nap_env
        with tempfile.TemporaryDirectory() as d:
            f = os.path.join(d, '.env')
            with open(f, 'w', encoding='utf-8') as fh:
                fh.write('# ghi chú\nEZ_THU_A="mot hai"\nexport EZ_THU_B=2\nEZ_THU_C=\nEZ_THU_D=moi\nkhong hop le\n')
            os.environ['EZ_THU_D'] = 'cu'
            try:
                self.assertEqual(nap_env(f), ['EZ_THU_A', 'EZ_THU_B'])
                self.assertEqual(os.environ['EZ_THU_A'], 'mot hai')
                self.assertEqual(os.environ['EZ_THU_B'], '2')
                self.assertNotIn('EZ_THU_C', os.environ)
                self.assertEqual(os.environ['EZ_THU_D'], 'cu')   # biến đã đặt sẵn thắng tệp .env
            finally:
                for k in ('EZ_THU_A', 'EZ_THU_B', 'EZ_THU_D'):
                    os.environ.pop(k, None)
        self.assertEqual(nap_env(os.path.join(d, 'khong_co')), [])
