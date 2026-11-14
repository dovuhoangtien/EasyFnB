"""An ninh: ba loại cảnh báo, người nhận, gộp trùng, giờ đóng cửa, không vào số liệu ca, mã PIN, luật Gemini.

Chạy (trong easy-fnb):  python -m unittest server.tests.test_an_ninh -v
"""
import asyncio
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from server import an_ninh as sec
from server.gemini import _decide_probs
from server.hub import Hub

STAFF = [dict(id='lan', name='Lan', role='serve'), dict(id='thu', name='Thu', role='cashier'),
         dict(id='chu', name='Chủ', role='owner'), dict(id='tu', name='Tú', role='clean')]


class NoGemini:
    enabled = False
    model = None


class DecisionGemini:
    """Gemini Decision giả: trả xác suất cho sẵn."""
    enabled = True
    decision = True
    model = 'gemini-decision-1'
    ten = 'Gemini'

    def __init__(self, probs):
        self.probs, self.calls = probs, []

    async def verify(self, kind, images, table=None):
        self.calls.append((kind, [im['role'] for im in images]))
        return dict(probs=self.probs, model=self.model, reason='x', ms=5)


def ev(kind, **kw):
    return dict(dict(camera='cam1', kind=kind, table=None, score=0.9), **kw)


class Base(unittest.TestCase):
    def make(self, gemini=None):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        hub = Hub(Path(self.tmp.name), gemini or NoGemini())
        hub.set_staff(STAFF)
        hub.set_zones(dict(camera='cam1', frame_w=100, frame_h=100, tables=[],
                           areas=[dict(id='q1', type='quay', polygon=[[0, 0], [10, 0], [10, 10]])]))
        return hub


class Luat(unittest.TestCase):
    def test_closed_by_hours_and_overnight(self):
        s = dict(sec.DEFAULTS, open_time='07:00', close_time='22:00')
        self.assertFalse(sec.is_closed(s, datetime(2026, 11, 13, 12, 0)))
        self.assertTrue(sec.is_closed(s, datetime(2026, 11, 13, 23, 0)))
        self.assertTrue(sec.is_closed(s, datetime(2026, 11, 13, 6, 59)))
        s = dict(s, open_time='16:00', close_time='02:00')      # quán mở qua nửa đêm
        self.assertFalse(sec.is_closed(s, datetime(2026, 11, 13, 1, 0)))
        self.assertTrue(sec.is_closed(s, datetime(2026, 11, 13, 3, 0)))

    def test_guard_mode_always_closed(self):
        self.assertTrue(sec.is_closed(dict(sec.DEFAULTS, guard_mode=True), datetime(2026, 11, 13, 12, 0)))

    def test_bad_settings_rejected(self):
        for bad in (dict(open_time='25:00'), dict(guard_mode='yes'), dict(hold_s=1), dict(delivery_from='7h')):
            with self.assertRaises(ValueError):
                sec.check_settings(bad)
        sec.check_settings(dict(delivery_from='', open_time='06:30', hold_s=60))

    def test_pin(self):
        h = sec.hash_pin('1234')
        self.assertTrue(sec.pin_ok(h, '1234'))
        self.assertFalse(sec.pin_ok(h, '1235'))
        self.assertFalse(sec.pin_ok(None, '1234'))
        self.assertFalse(sec.valid_pin('12a4'))

    def test_decide_item_taken(self):
        self.assertEqual(_decide_probs('item_taken', dict(item_taken=0.9, same_person_as_reference=0.1,
                                                          image_clear=0.9))[0], 'confirm')
        self.assertEqual(_decide_probs('item_taken', dict(item_taken=0.9, same_person_as_reference=0.85,
                                                          image_clear=0.9))[0], 'reject')
        self.assertEqual(_decide_probs('item_taken', dict(item_taken=0.9, same_person_as_reference=0.1,
                                                          wearing_staff_uniform=0.9, image_clear=0.9))[0], 'reject')
        self.assertEqual(_decide_probs('item_taken', dict(item_taken=0.5, same_person_as_reference=0.1,
                                                          image_clear=0.9))[0], 'unverified')

    def test_decide_after_hours_staff_still_reported(self):
        self.assertEqual(_decide_probs('after_hours', dict(real_person_present=0.9, wearing_staff_uniform=0.95,
                                                           image_clear=0.9))[0], 'confirm')
        self.assertEqual(_decide_probs('after_hours', dict(real_person_present=0.1, image_clear=0.9))[0], 'reject')

    def test_decide_restricted(self):
        self.assertEqual(_decide_probs('restricted', dict(person_in_marked_area=0.9, wearing_staff_uniform=0.8,
                                                          image_clear=0.9))[0], 'reject')
        self.assertEqual(_decide_probs('restricted', dict(person_in_marked_area=0.9, delivery_person=0.1,
                                                          wearing_staff_uniform=0.1, image_clear=0.9))[0], 'confirm')


class Hub_(Base):
    def test_item_taken_notifies_serve_online_and_owner(self):
        hub = self.make()
        hub.staff_online('lan', 1)
        aid = hub.edge_event(ev('lay_do', table='3', detail='túi xách'))
        a = hub.alerts[aid]
        self.assertEqual(a['group'], 'security')
        self.assertIsNone(a['assigned_to'])
        self.assertEqual(a['notify'], ['lan', 'chu'])
        self.assertIn('túi xách', hub.log[0]['text'])

    def test_after_hours_goes_to_owner_and_dedups_5_min(self):
        hub = self.make()
        a1 = hub.edge_event(ev('co_nguoi_ngoai_gio', box=[0, 0, 10, 10]))
        a2 = hub.edge_event(ev('co_nguoi_ngoai_gio', box=[80, 80, 90, 90]))
        self.assertEqual(a1, a2)
        self.assertEqual(hub.alerts[a1]['notify'], ['chu'])
        hub.done(a1, 'chu')
        self.assertEqual(hub.edge_event(ev('co_nguoi_ngoai_gio')), a1)     # vừa bấm "Đã biết": vẫn gộp
        hub.alerts[a1]['created_at'] -= (sec.AFTER_HOURS_GAP_S + 1) * 1000
        a3 = hub.edge_event(ev('co_nguoi_ngoai_gio'))
        self.assertNotEqual(a3, a1)
        hub.cancel(a3, 'chu', 'báo nhầm')
        self.assertNotEqual(hub.edge_event(ev('co_nguoi_ngoai_gio')), a3)   # báo nhầm không che lần sau

    def test_restricted_cashier_then_owner_after_30s(self):
        hub = self.make()
        hub.staff_online('thu', 1)
        aid = hub.edge_event(ev('vao_khu_cam', area='q1'))
        a = hub.alerts[aid]
        self.assertEqual(a['notify'], ['thu'])
        self.assertEqual(a['area_name'], 'Quầy thu ngân')
        a['created_at'] -= 31_000
        hub.tick()
        self.assertEqual(a['notify'], ['thu', 'chu'])
        self.assertEqual(a['status'], 'open')         # không tự đóng như việc phục vụ

    def test_restricted_needs_area_and_respects_delivery_window(self):
        hub = self.make()
        with self.assertRaises(ValueError):
            hub.edge_event(ev('vao_khu_cam'))
        hub.update_settings(dict(delivery_from='00:00', delivery_to='23:59'))
        self.assertIsNone(hub.edge_event(ev('vao_khu_cam', area='q1')))

    def test_feature_off_ignores_event(self):
        hub = self.make()
        hub.update_settings(dict(sec_item_taken=False))
        self.assertIsNone(hub.edge_event(ev('lay_do', table='3')))

    def test_security_not_in_shift_report(self):
        hub = self.make()
        hub.edge_event(ev('lay_do', table='3'))
        hub.edge_event(ev('goi_phuc_vu', table='2'))
        r = hub.report()
        self.assertEqual(sum(r['counts'].values()), 1)
        self.assertNotIn('item_taken', r['counts'])

    def test_zones_carry_areas_and_camera_view(self):
        hub = self.make()
        z = hub.get_zones('cam1')
        self.assertEqual(z['areas'][0]['type'], 'quay')
        self.assertEqual(set(z['an_ninh']), {'closed', 'after_hours', 'restricted', 'item_taken', 'delivery_now',
                                             'blur_faces'})
        hub.update_settings(dict(guard_mode=True))
        self.assertTrue(hub.get_zones('cam1')['an_ninh']['closed'])
        self.assertNotIn('an_ninh', hub.zones['cam1'])      # không lưu vào vùng

    def test_bad_area_type_rejected(self):
        hub = self.make()
        with self.assertRaises(ValueError):
            hub.set_zones(dict(camera='cam1', frame_w=1, frame_h=1, tables=[],
                               areas=[dict(id='x', type='san', polygon=[[0, 0], [1, 0], [1, 1]])]))

    def test_pin_guards_blur_and_never_leaks(self):
        hub = self.make()
        with self.assertRaises(PermissionError):
            hub.update_settings(dict(blur_faces=False))       # chưa có PIN
        hub.set_pin('2468')
        with self.assertRaises(PermissionError):
            hub.update_settings(dict(blur_faces=False), pin='0000')
        self.assertFalse(hub.update_settings(dict(blur_faces=False), pin='2468')['blur_faces'])
        v = hub.settings_view()
        self.assertTrue(v['owner_pin_set'])
        self.assertFalse(any(k.startswith('_') for k in v))
        with self.assertRaises(PermissionError):
            hub.set_pin('1111', old='9999')
        hub.set_pin('1111', old='2468')
        self.assertTrue(hub.pin_ok('1111'))
        # PIN còn sau khi nạp lại cấu hình
        self.assertTrue(Hub(Path(self.tmp.name), NoGemini()).pin_ok('1111'))


class LichSu(Base):
    def test_lich_su_doc_tu_dong_thoi_gian_va_tro_ly(self):
        from server import an_ninh_tro_ly as at
        from server.tro_ly import tra_loi_rules
        hub = self.make()
        a1 = hub.edge_event(ev('lay_do', table='3', detail='túi xách'))
        a2 = hub.edge_event(ev('co_nguoi_ngoai_gio'))
        hub.edge_event(ev('goi_phuc_vu', table='2'))
        hub.cancel(a2, 'chu', 'báo nhầm')
        rows = at.lich_su(hub.timeline)
        self.assertEqual([(r['alert_id'], r['kind'], r['status']) for r in rows],
                         [(a1, 'item_taken', 'open'), (a2, 'after_hours', 'cancelled')])
        self.assertIn('túi xách', rows[0]['text'])
        ans, blocks = tra_loi_rules(hub, 'hôm nay có ai lấy đồ của khách không')
        self.assertIn('1 cảnh báo an ninh', ans)
        self.assertEqual(blocks[0]['type'], 'events')


class XacMinh(Base, unittest.IsolatedAsyncioTestCase):
    async def test_item_taken_held_then_confirmed_with_inline_images(self):
        g = DecisionGemini(dict(item_taken=0.9, same_person_as_reference=0.1, image_clear=0.9))
        hub = self.make(g)
        hub.staff_online('lan', 1)
        imgs = [dict(role=r, jpeg=b'\xff\xd8x') for r in ('person', 'strip', 'overview')]
        aid = hub.edge_event(ev('lay_do', table='3', eid='e1', images=imgs))
        a = hub.alerts[aid]
        self.assertEqual(a['status'], 'verifying')
        self.assertEqual(a['notify'], [])
        self.assertTrue(a['evidence']['person'])
        for _ in range(20):
            await asyncio.sleep(0.01)
            if a['verify']['state'] != 'pending':
                break
        self.assertEqual(a['verify']['state'], 'confirmed')
        self.assertEqual(a['status'], 'open')
        self.assertEqual(a['notify'], ['lan', 'chu'])
        self.assertEqual(g.calls[0][0], 'item_taken')
        self.assertIn('person', g.calls[0][1])

    async def test_item_taken_rejected_when_same_person(self):
        hub = self.make(DecisionGemini(dict(item_taken=0.9, same_person_as_reference=0.9, image_clear=0.9)))
        imgs = [dict(role='strip', jpeg=b'\xff\xd8x')]
        aid = hub.edge_event(ev('lay_do', table='3', eid='e2', images=imgs))
        for _ in range(20):
            await asyncio.sleep(0.01)
        self.assertEqual(hub.alerts[aid]['status'], 'cancelled')


if __name__ == '__main__':
    unittest.main()
