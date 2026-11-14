"""Test khớp bàn (khop_ban.py), không cần GPU, model hay máy chủ.

    python -m unittest test_khop_ban -v
"""
import json
import threading
import unittest

import numpy as np

import khop_ban as kb


class Ban:
    def __init__(self, name, x1, y1, x2, y2):
        self.name = name
        self.poly = np.array([[x1, y1], [x2, y1], [x2, y2], [x1, y2]], np.float32)


def nguoi(cx, cy_neo, h=100, w=50):
    """Khung người có điểm neo (60% chiều cao) ở (cx, cy_neo)."""
    y1 = cy_neo - 0.6 * h
    return [cx - w / 2, y1, cx + w / 2, y1 + h]


class TestGanBan(unittest.TestCase):
    def setUp(self):
        self.b1, self.b2 = Ban('B1', 0, 0, 100, 100), Ban('B2', 200, 0, 300, 100)
        self.g = kb.GanBan([self.b1, self.b2])

    def test_trong_ban(self):
        self.assertEqual(self.g.gan(1, nguoi(50, 50), None, None, 0.0), (self.b1, None))

    def test_ngoi_lech_ra_ngoai_vung_van_tinh(self):
        # cách mép 50 px, người cao 100: luật cũ (0,45 lần chiều cao) bỏ, luật mới (0,6) nhận
        self.assertIs(self.g.gan(1, nguoi(150, 50), None, None, 0.0)[0], self.b1)

    def test_dung_canh_ban_khong_tinh(self):
        self.assertIsNone(self.g.gan(1, nguoi(150, 50), None, None, 0.0, dung=True)[0])

    def test_nguoi_bi_che_lay_co_theo_be_ngang(self):
        # chỉ còn đầu vai: khung thấp (40) mà rộng (80) -> cỡ 96, cách mép 50 vẫn nhận
        b = [110, 30, 190, 70]   # neo (150, 54)
        self.assertIs(self.g.gan(1, b, None, None, 0.0)[0], self.b1)

    def test_hai_ban_sat_nut_la_khong_chac(self):
        ban, ung = self.g.gan(1, nguoi(150, 50, h=200), None, None, 0.0)
        self.assertIsNotNone(ban)
        self.assertEqual({b.name for b in ung}, {'B1', 'B2'})

    def test_khong_chac_khi_dung_thi_khong_hoi(self):
        g = kb.GanBan([self.b1, self.b2])
        g.gan(1, nguoi(150, 50, h=200), None, None, 0.0, dung=True)
        g.gan(1, nguoi(150, 50, h=200), None, None, 5.0, dung=True)
        self.assertEqual(g.can_hoi(5.0), [])

    def test_hoi_sau_2s_va_khong_hoi_lai(self):
        g = kb.GanBan([self.b1, self.b2])
        for t in (0.0, 1.0):
            g.gan(1, nguoi(150, 50, h=200), None, None, t)
        self.assertEqual(g.can_hoi(1.0), [])
        g.gan(1, nguoi(150, 50, h=200), None, None, 2.0)
        hoi = g.can_hoi(2.0)
        self.assertEqual([p for p, _ in hoi], [1])
        g.da_hoi(1, 2.0)
        g.gan(1, nguoi(150, 50, h=200), None, None, 10.0)
        self.assertEqual(g.can_hoi(10.0), [])

    def test_chot_giu_toi_khi_di(self):
        g = kb.GanBan([self.b1, self.b2])
        g.gan(1, nguoi(150, 50, h=200), None, None, 0.0)
        g.chot(1, 'B2')
        self.assertIs(g.gan(1, nguoi(140, 50, h=200), None, None, 1.0)[0], self.b2)   # hơi lệch về B1 vẫn giữ B2
        g.gan(1, nguoi(50, 50), None, None, 2.0, di=True)                              # đứng dậy đi: hết chốt,
        self.assertIs(g.gan(1, nguoi(50, 50), None, None, 2.5, di=True)[0], self.b1)  # đổi bàn như thường

    def test_ngoi_lau_khong_doi_ban_vi_voi_tay(self):
        g = kb.GanBan([self.b1, self.b2])
        for t in range(7):
            g.gan(1, nguoi(90, 50), None, None, float(t))
        # tay với làm khung lệch sang B2 vài giây: vẫn là B1
        for t in range(7, 10):
            self.assertIs(g.gan(1, nguoi(210, 50), None, None, float(t))[0], self.b1)

    def test_chua_ngoi_lau_thi_doi_sau_04s(self):
        g = kb.GanBan([self.b1, self.b2])
        g.gan(1, nguoi(50, 50), None, None, 0.0, dung=True)
        self.assertIs(g.gan(1, nguoi(250, 50), None, None, 0.1, dung=True)[0], self.b1)
        self.assertIs(g.gan(1, nguoi(250, 50), None, None, 0.6, dung=True)[0], self.b2)

    def test_roi_ban_ve_none_cung_co_tre(self):
        g = kb.GanBan([self.b1, self.b2])
        g.gan(1, nguoi(50, 50), None, None, 0.0, dung=True)
        self.assertIs(g.gan(1, nguoi(150, 500), None, None, 0.1, dung=True)[0], self.b1)
        self.assertIsNone(g.gan(1, nguoi(150, 500), None, None, 0.6, dung=True)[0])

    def test_tu_khong_ban_sang_ban_cung_co_tre(self):
        # nhân viên đi ngang lướt qua mép bàn: không được nhận bàn ngay (lỗi đo được trên m10)
        g = kb.GanBan([self.b1, self.b2])
        g.gan(1, nguoi(150, 500), None, None, 0.0, dung=True)
        self.assertIsNone(g.gan(1, nguoi(50, 50), None, None, 0.1, dung=True)[0])
        self.assertIs(g.gan(1, nguoi(50, 50), None, None, 0.6, dung=True)[0], self.b1)

    def test_toc_time_lapse(self):
        g = kb.GanBan([self.b1, self.b2], toc=30)
        g.gan(1, nguoi(150, 50, h=200), None, None, 0.0)
        g.gan(1, nguoi(150, 50, h=200), None, None, 0.1)   # 0,1 s video = 3 s thật
        self.assertEqual(len(g.can_hoi(0.1)), 1)

    def test_khong_co_ban(self):
        self.assertEqual(kb.GanBan([]).gan(1, nguoi(50, 50), None, None, 0.0), (None, None))

    def test_quen(self):
        self.g.gan(1, nguoi(50, 50), None, None, 0.0)
        self.g.gan(2, nguoi(50, 50), None, None, 9.0)
        self.g.quen(11.0)
        self.assertEqual(set(self.g.st), {2})


class TestChonBan(unittest.TestCase):
    def test_chac(self):
        self.assertEqual(kb.chon_ban({'B3': 0.76, 'B4': 0.13}), 'B3')

    def test_lung_chung(self):
        self.assertIsNone(kb.chon_ban({'B2': 0.6, 'B1': 0.18}))
        self.assertIsNone(kb.chon_ban({'B2': 0.8, 'B1': 0.4}))
        self.assertIsNone(kb.chon_ban({}))


class TestAnhHoi(unittest.TestCase):
    def test_anh_jpeg(self):
        f = np.zeros((720, 1280, 3), np.uint8)
        j = kb.anh_hoi(f, [100, 100, 200, 300], [Ban('B1', 150, 200, 400, 300).poly, Ban('B2', 150, 320, 400, 420).poly])
        self.assertEqual(j[:2], b'\xff\xd8')


class TraLoi:
    def __init__(self, code, d):
        self.status_code, self.d = code, d

    def json(self):
        return self.d


class PhienGia:
    def __init__(self, tra=None, loi=None):
        self.headers, self.tra, self.loi, self.goi = {}, tra, loi, []
        self.xong = threading.Event()

    def post(self, url, json=None, timeout=None):
        self.goi.append((url, json))
        self.xong.set()
        if self.loi:
            raise self.loi
        return self.tra


class TestHoiBan(unittest.TestCase):
    def cho(self, h):
        for _ in range(100):
            if r := h.ket_qua():
                return r
            threading.Event().wait(0.02)
        return []

    def test_gui_va_nhan(self):
        s = PhienGia(TraLoi(200, dict(ok=True, probs={'B3': 0.8, 'B4': 0.1})))
        h = kb.HoiBan('http://x/', 'cam1', key='k', session=s)
        self.assertTrue(h.gui(7, b'jpg', ['B3', 'B4']))
        self.assertEqual(self.cho(h), [(7, 'B3', {'B3': 0.8, 'B4': 0.1})])
        url, body = s.goi[0]
        self.assertEqual(url, 'http://x/api/edge/table-ask')
        self.assertEqual(body['tables'], [dict(table='B3', color='cam'), dict(table='B4', color='xanh dương')])
        self.assertEqual(s.headers['X-Edge-Key'], 'k')
        h.close()

    def test_gioi_han_moi_10s(self):
        t = [0.0]
        h = kb.HoiBan('http://x', 'c', session=PhienGia(TraLoi(200, {})), dong_ho=lambda: t[0])
        self.assertTrue(h.gui(1, b'j', ['B1', 'B2']))
        self.assertFalse(h.gui(2, b'j', ['B1', 'B2']))
        t[0] = 10.0
        self.assertTrue(h.gui(2, b'j', ['B1', 'B2']))
        h.close()

    def test_loi_mang_khong_chot(self):
        h = kb.HoiBan('http://x', 'c', session=PhienGia(loi=OSError('mất mạng')))
        h.gui(1, b'j', ['B1', 'B2'])
        self.assertEqual(self.cho(h), [(1, None, {})])
        h.close()

    def test_may_chu_tu_choi(self):
        h = kb.HoiBan('http://x', 'c', session=PhienGia(TraLoi(200, dict(ok=False, reason='decision_off'))))
        h.gui(1, b'j', ['B1', 'B2'])
        self.assertEqual(self.cho(h)[0][1], None)
        h.close()


if __name__ == '__main__':
    unittest.main()
