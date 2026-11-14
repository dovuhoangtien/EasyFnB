"""Test gui_may_chu.MayChu khi máy chủ mất rồi có lại: không đụng mạng (session giả).

    python -m unittest test_gui_may_chu -v
"""
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path

import numpy as np
import requests

import gui_may_chu
from gui_may_chu import MayChu, an_ninh_tu, qua_han


class PhienGia:
    """Thay requests.Session: máy chủ "mất" thì mọi lệnh gọi ném ConnectionError, "có" thì ghi lại rồi trả 200."""

    def __init__(self):
        self.headers = {}
        self.song = False
        self.da_gui = []

    def request(self, method, url, **kw):
        if not self.song:
            raise requests.ConnectionError('mất máy chủ')
        self.da_gui.append((url.split('/api/')[-1], kw.get('json')))
        return self._tra()

    def get(self, url, **kw):
        if not self.song:
            raise requests.ConnectionError('mất máy chủ')
        return self._tra()

    put = get

    @staticmethod
    def _tra():
        r = requests.Response()
        r.status_code = 200
        r._content = b'{}'
        return r


def su_kien(loai, t=1.0, ban='B1'):
    return dict(loai=loai, ban=ban, t=t, chi_tiet='', eid=None)


def cho(dk, toi_da=5.0):
    het = time.monotonic() + toi_da
    while time.monotonic() < het:
        if dk():
            return True
        time.sleep(0.02)
    return False


class TestQuaHan(unittest.TestCase):
    def test_luat(self):
        self.assertFalse(qua_han('/api/edge/event', dict(kind='goi_phuc_vu'), 1.0))
        self.assertTrue(qua_han('/api/edge/event', dict(kind='goi_phuc_vu'), 61.0))
        self.assertTrue(qua_han('/api/edge/event', dict(kind='nv_den'), 61.0))
        self.assertFalse(qua_han('/api/edge/event', dict(kind='can_don'), 3600.0))   # bàn còn bẩn: báo muộn vẫn đúng
        self.assertFalse(qua_han('/api/edge/event', dict(kind='da_don'), 3600.0))
        self.assertTrue(qua_han('/api/edge/tables', {}, 6.0))
        self.assertFalse(qua_han('/api/edge/jobs/abc', {}, 3600.0))                  # kết quả việc web nhờ: luôn gửi


class TestMatMayChu(unittest.TestCase):
    def setUp(self):
        self.cu = dict(gui_may_chu.TUOI_TOI_DA_S)
        self.s = PhienGia()
        self.mc = MayChu('http://khong-co.invalid', 'cam_test', session=self.s)

    def tearDown(self):
        self.s.song = True
        self.mc.close(wait=2.0)
        gui_may_chu.TUOI_TOI_DA_S.clear()
        gui_may_chu.TUOI_TOI_DA_S.update(self.cu)

    def test_mat_may_chu_khong_treo_hang_doi_co_gioi_han(self):
        t0 = time.monotonic()
        for k in range(2000):                       # nhiều hơn sức chứa hàng đợi (500)
            self.mc.event(su_kien('goi_phuc_vu', t=k))
        self.assertLess(time.monotonic() - t0, 2.0, 'pipeline không được chờ mạng')
        self.assertLessEqual(self.mc.q.qsize(), 500)
        self.assertTrue(self.mc.t.is_alive())
        self.assertEqual(self.s.da_gui, [])

    def test_co_lai_khong_gui_don_tin_cu(self):
        gui_may_chu.TUOI_TOI_DA_S['/api/edge/event'] = 0.3
        gui_may_chu.TUOI_TOI_DA_S['/api/edge/tables'] = 0.3
        # máy chủ "treo": tin đầu giữ luồng gửi cho tới khi mở cổng, các tin sau nằm chờ trong hàng đợi
        cong, that = threading.Event(), self.mc._send
        self.mc._send = lambda *a, **k: (cong.wait(5.0), that(*a, **k)) if not cong.is_set() else that(*a, **k)
        self.mc.event(su_kien('goi_phuc_vu', t=0))
        self.assertTrue(cho(lambda: self.mc.q.empty()))     # luồng gửi đã cầm tin đầu
        for k in range(1, 20):
            self.mc.event(su_kien('goi_phuc_vu', t=k))      # sẽ quá hạn khi tới lượt
        self.mc.event(su_kien('can_don', t=20, ban='B2'))   # không có hạn
        self.mc._put(('POST', '/api/edge/tables', dict(camera='cam_test', tables=[])))
        time.sleep(0.5)
        self.s.song = True                                  # máy chủ có lại
        cong.set()
        time.sleep(0.2)
        self.mc.event(su_kien('goi_phuc_vu', t=99, ban='B9'))   # tin mới sau khi có lại
        self.assertTrue(cho(lambda: self.mc.q.empty() and any(b and b.get('table') == 'B9' for _, b in self.s.da_gui)))
        loai = [(p, b.get('kind'), b.get('table')) for p, b in self.s.da_gui if p == 'edge/event']
        self.assertIn(('edge/event', 'can_don', 'B2'), loai)
        self.assertIn(('edge/event', 'goi_phuc_vu', 'B9'), loai)
        loai = [x for x in loai if x != ('edge/event', 'goi_phuc_vu', 'B1') or 0]   # tin đầu (đang gửi dở lúc treo) có thể tới
        self.assertLessEqual(len([x for x in self.s.da_gui if x[0] == 'edge/event']), 3, 'tin cũ không được gửi dồn')
        self.assertEqual(len(loai), 2, f'tin cũ không được gửi dồn: {loai}')
        self.assertFalse(any(p == 'edge/tables' for p, _ in self.s.da_gui))
        self.assertGreaterEqual(self.mc.bo_cu, 19)

    def test_day_thi_bo_tin_cu_nhat(self):
        self.mc.stop.set()                                  # dừng luồng gửi để hàng đợi đứng yên
        self.mc.t.join(timeout=2.0)
        while not self.mc.q.empty():
            self.mc.q.get_nowait()
        for k in range(505):
            self.mc._put(('POST', '/api/edge/event', dict(kind='goi_phuc_vu', video_t=k)))
        self.assertEqual(self.mc.q.qsize(), 500)
        dau = self.mc.q.get_nowait()[1][2]['video_t']
        self.assertEqual(dau, 5, 'phải bỏ 5 tin cũ nhất, giữ tin mới')


class PhienVung(PhienGia):
    """Máy chủ "có", GET /api/zones trả self.vung."""

    def __init__(self, vung):
        super().__init__()
        self.song = True
        self.vung = vung

    def get(self, url, **kw):
        r = requests.Response()
        r.status_code = 200
        r._content = json.dumps(self.vung if url.endswith('/api/zones') else {}).encode()
        return r


class TestAnNinh(unittest.TestCase):
    BAN = [dict(id='B1', polygon=[[10, 10], [100, 10], [100, 100], [10, 100]])]

    def make(self, vung):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        s = PhienVung(vung)
        mc = MayChu('http://gia.invalid', 'cam_test', session=s, poll_s=0.05, cache=Path(tmp.name) / 'vung.json')
        self.addCleanup(mc.close, 2.0)
        return mc, s

    def test_may_chu_cu_khong_co_an_ninh_thi_mac_dinh_an_toan(self):
        mc, _ = self.make(dict(camera='cam_test', frame_w=640, frame_h=360, tables=self.BAN))
        mc.load_zones({}, 1280, 720, live=True)
        self.assertEqual(mc.an_ninh(), dict(closed=False, after_hours=False, restricted=False, item_taken=False,
                                            delivery_now=False, blur_faces=True))
        self.assertEqual(mc.areas(), [])
        # trường sai kiểu cũng giữ mặc định
        self.assertEqual(an_ninh_tu(dict(an_ninh=dict(closed='yes', blur_faces=None, restricted=True))),
                         dict(gui_may_chu.AN_NINH_MAC_DINH, restricted=True))

    def test_doc_an_ninh_va_vung_co_gian_theo_co_anh(self):
        an = dict(closed=True, after_hours=True, restricted=True, item_taken=False, delivery_now=False, blur_faces=False)
        mc, s = self.make(dict(camera='cam_test', frame_w=640, frame_h=360, tables=self.BAN, an_ninh=an,
                               areas=[dict(id='quay', type='quay', name='Quầy thu ngân',
                                           polygon=[[0, 0], [320, 0], [320, 180], [0, 180]])]))
        ban = mc.load_zones({}, 1280, 720, live=True)
        self.assertEqual(ban['B1'][1], [200.0, 20.0])
        self.assertEqual(mc.an_ninh(), an)
        self.assertEqual(mc.areas(), [dict(id='quay', type='quay', name='Quầy thu ngân',
                                           poly=[[0.0, 0.0], [640.0, 0.0], [640.0, 360.0], [0.0, 360.0]])])
        self.assertNotIn('an_ninh', mc._current)          # không đẩy an_ninh lên lại máy chủ

        # chỉ trạng thái an ninh đổi (quán mở cửa): cập nhật, KHÔNG dựng lại bàn
        s.vung = dict(s.vung, an_ninh=dict(an, closed=False))
        self.assertTrue(cho(lambda: not mc.an_ninh()['closed']))
        self.assertIsNone(mc.new_zones())
        # vùng khác đổi: cũng không dựng lại bàn
        s.vung = dict(s.vung, areas=[dict(id='kho', type='kho', polygon=[[0, 0], [10, 0], [10, 10]])])
        self.assertTrue(cho(lambda: [a['id'] for a in mc.areas()] == ['kho']))
        self.assertIsNone(mc.new_zones())
        # bàn đổi: pipeline lấy vùng bàn mới
        s.vung = dict(s.vung, tables=self.BAN + [dict(id='B2', polygon=[[200, 10], [300, 10], [300, 100]])])
        self.assertTrue(cho(lambda: mc._zones_new is not None))
        self.assertEqual(sorted(mc.new_zones()), ['B1', 'B2'])

    def test_su_kien_an_ninh_gui_kem_area_va_anh(self):
        mc, s = self.make(dict(camera='cam_test'))
        img = np.full((40, 30, 3), 128, np.uint8)
        mc.event(dict(loai='lay_do', ban='B1', t=3.0, chi_tiet='túi xách', eid='cam_test:5', area=None,
                      images=[('person', img), ('strip', img), ('overview', None)]), img)
        mc.event(dict(loai='vao_khu_cam', ban=None, t=4.0, eid='cam_test:6', area='quay'), img)
        self.assertTrue(cho(lambda: len([1 for p, _ in s.da_gui if p == 'edge/event']) == 2))
        a, b = [x for p, x in s.da_gui if p == 'edge/event']
        self.assertEqual((a['kind'], a['table'], a['area'], a['detail']), ('lay_do', 'B1', None, 'túi xách'))
        self.assertEqual([x['role'] for x in a['images']], ['person', 'strip'])
        self.assertTrue(a['crop_jpeg_b64'] and a['images'][0]['jpeg_b64'])
        self.assertEqual((b['kind'], b['area']), ('vao_khu_cam', 'quay'))
        self.assertNotIn('images', b)


if __name__ == '__main__':
    unittest.main()
