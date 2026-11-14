"""Test độ bền của pipeline camera (easyfnb_test.py) ở các tình huống xấu, không cần GPU, model hay camera.

    python -m unittest test_do_ben -v

Camera rớt rồi có lại, khung hỏng / rỗng, đổi độ phân giải giữa chừng, không có bàn nào, vùng bàn lệch ra ngoài
khung hình, hình đứng nhiều giây (đồng hồ nhảy), lịch chạy model theo số khung đã xử lý.
"""
import unittest

import numpy as np

import easyfnb_test as ef
from easyfnb_test import Table


class CapGia:
    """Thay cv2.VideoCapture: trả lần lượt các khung trong `khung` (None = đọc hỏng)."""

    def __init__(self, khung, mo=True):
        self.khung = list(khung)
        self.mo = mo
        self.da_dong = False

    def isOpened(self):
        return self.mo

    def read(self):
        if not self.khung:
            return False, None
        f = self.khung.pop(0)
        return (f is not None), f

    def set(self, *a):
        return True

    def release(self):
        self.da_dong = True


ANH = np.zeros((72, 128, 3), np.uint8)


class DongHoGia:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def ngu(self, s):
        self.t += s


class TestCameraRot(unittest.TestCase):
    def test_khung_hop_le(self):
        self.assertTrue(ef.khung_hop_le(ANH))
        self.assertFalse(ef.khung_hop_le(None))
        self.assertFalse(ef.khung_hop_le(np.zeros((0, 0, 3), np.uint8)))      # khung rỗng
        self.assertFalse(ef.khung_hop_le(np.zeros((72, 128), np.uint8)))      # khung hỏng: thiếu kênh màu

    def test_hong_vai_khung_roi_doc_lai_duoc(self):
        cap = CapGia([None, np.zeros((0, 0, 3), np.uint8), ANH])
        dh = DongHoGia()
        cap2, frame = ef.doc_lai_camera(cap, lambda: self.fail('chưa cần mở lại'), 60, ngu=dh.ngu, dong_ho=dh)
        self.assertIs(cap2, cap)
        self.assertIs(frame, ANH)

    def test_rot_han_thi_mo_lai(self):
        cu = CapGia([])
        lan = []

        def mo():
            lan.append(1)
            return CapGia([ANH]) if len(lan) >= 3 else CapGia([], mo=False)   # hai lần đầu camera chưa lên
        dh = DongHoGia()
        cap2, frame = ef.doc_lai_camera(cu, mo, 60, ngu=dh.ngu, dong_ho=dh)
        self.assertTrue(cu.da_dong)
        self.assertIs(frame, ANH)
        self.assertEqual(len(lan), 3)
        self.assertIsNot(cap2, cu)

    def test_mat_luon_thi_thoi_sau_han(self):
        dh = DongHoGia()
        cap2, frame = ef.doc_lai_camera(CapGia([]), lambda: CapGia([], mo=False), 30, ngu=dh.ngu, dong_ho=dh)
        self.assertIsNone(frame)
        self.assertGreaterEqual(dh.t, 30)
        self.assertLess(dh.t, 60)          # không chờ mãi

    def test_mo_lai_nem_loi_khong_lam_sap(self):
        dh = DongHoGia()

        def mo():
            raise OSError('driver camera lỗi')
        cap2, frame = ef.doc_lai_camera(CapGia([]), mo, 10, ngu=dh.ngu, dong_ho=dh)
        self.assertIsNone(frame)

    def test_dung_giua_chung(self):
        dh = DongHoGia()
        dung = []

        def ngu(s):
            dh.ngu(s)
            dung.append(1)                 # Ctrl+C trong lúc chờ
        cap2, frame = ef.doc_lai_camera(CapGia([]), lambda: CapGia([], mo=False), 600, dung=dung, ngu=ngu, dong_ho=dh)
        self.assertIsNone(frame)
        self.assertLess(dh.t, 30)


class TestDoiDoPhanGiai(unittest.TestCase):
    def test_ve_dung_co(self):
        to = np.zeros((144, 256, 3), np.uint8)
        f = ef.ve_co(to, 128, 72)
        self.assertEqual(f.shape, (72, 128, 3))
        self.assertIs(ef.ve_co(ANH, 128, 72), ANH)     # đúng cỡ thì không đụng


class TestVungBan(unittest.TestCase):
    W, H = 1280, 720

    def test_khong_co_ban(self):
        self.assertEqual(ef.loc_ban({}, self.W, self.H), {})
        self.assertIsNone(ef.nearest_table([], (10.0, 10.0), 50))

    def test_ban_lech_mot_phan_van_dung(self):
        ban = {'B1': [[-200, 100], [150, 100], [150, 300], [-200, 300]],          # lệch trái
               'B2': [[1100, 600], [1500, 600], [1500, 900], [1100, 900]]}        # lệch góc dưới phải
        tot = ef.loc_ban(ban, self.W, self.H)
        self.assertEqual(set(tot), {'B1', 'B2'})
        frame = np.zeros((self.H, self.W, 3), np.uint8)
        for pts in tot.values():
            c = ef.table_crop(frame, Table('x', pts).poly)
            self.assertGreater(c.size, 0)

    def test_ban_ngoai_khung_bi_bo(self):
        ban = {'B1': [[100, 100], [300, 100], [300, 300], [100, 300]],
               'NGOAI': [[2000, 100], [2300, 100], [2300, 300], [2000, 300]],     # nằm hẳn ngoài khung
               'MEP': [[1277, 100], [1500, 100], [1500, 300], [1277, 300]],       # chỉ còn 3 px trong khung
               'HONG': [[10, 10], [20, 20]],                                      # chưa đủ 3 điểm
               'NAN': [[float('nan'), 1], [5, 5], [9, 9]]}
        self.assertEqual(set(ef.loc_ban(ban, self.W, self.H)), {'B1'})

    def test_anh_cat_rong_khong_lam_sap_model(self):
        class ModelGia:
            classes = ['sach', 'ban']

            def p_pos(self, crops):
                assert all(c.size for c in crops), 'model không được nhận ảnh rỗng'
                return [0.1] * len(crops)
        rong = np.zeros((0, 5, 3), np.uint8)
        self.assertEqual(ef.class_probs(ModelGia(), [rong, ANH, None], 'ban'), [0.1, 0.1, 0.1])


def chay(tb, t0, t1, n, dirty, fps=10.0, win=1.0):
    """Cho bàn xem liên tục từ t0 tới t1 với n người và độ bẩn dirty; trả mọi sự kiện."""
    ev = []
    for k in range(int(round((t1 - t0) * fps))):
        ev += [e for e, _ in tb.update(t0 + k / fps, n, dirty, win)]
    return ev


class TestBanVaDongHo(unittest.TestCase):
    def test_binh_thuong(self):
        tb = Table('B1', [[0, 0], [10, 0], [10, 10], [0, 10]])
        self.assertEqual(chay(tb, 0, 3, 0, 0.1), [])                 # khởi động: không báo gì
        self.assertEqual(chay(tb, 3, 6, 2, 0.1), ['khach_moi'])
        ev = chay(tb, 6, 14, 0, 0.9)                                 # khách đi, bàn còn đồ
        self.assertEqual(ev, ['khach_roi', 'can_don'])
        self.assertEqual(chay(tb, 14, 22, 0, 0.05), ['da_don'])

    def test_khoi_dong_khong_bao_ban_ban_san(self):
        tb = Table('B1', [[0, 0], [10, 0], [10, 10], [0, 10]])
        self.assertEqual(chay(tb, 0, 10, 0, 0.9), [])                # bật máy giữa ca: bàn bẩn sẵn không phải việc mới
        self.assertEqual(tb.state, 'can_don')

    def test_hinh_dung_30_giay_khong_bao_khach_roi_oan(self):
        """Khách bị che 0,3 s ngay trước khi camera rớt 30 s. Không dựng lại thì khung đầu tiên sau khi có hình
        thấy "vắng liên tục 30 s" và báo khách rời + cần dọn dù chỉ nhìn thấy bàn vắng vài khung."""
        tb = Table('B1', [[0, 0], [10, 0], [10, 10], [0, 10]])
        chay(tb, 0, 3, 0, 0.9)
        tb.state = 'co_khach'
        chay(tb, 3, 8, 2, 0.9)
        chay(tb, 8, 9.5, 0, 0.9)                                     # bị che ngay trước lúc rớt
        self.assertEqual(tb.state, 'co_khach')
        t_sau = 40.0
        self.assertTrue(ef.hinh_dung(9.5, t_sau))
        tb.reset(t_sau)                                              # pipeline làm việc này khi hinh_dung
        ev = chay(tb, t_sau, t_sau + 10, 2, 0.9)                     # khách vẫn ngồi đó
        self.assertEqual(ev, [])
        self.assertEqual(tb.state, 'co_khach')

    def test_hinh_dung(self):
        self.assertFalse(ef.hinh_dung(None, 5.0))
        self.assertFalse(ef.hinh_dung(5.0, 5.2))
        self.assertTrue(ef.hinh_dung(5.0, 5.0 + ef.MAT_HINH_S + 0.1))
        self.assertTrue(ef.hinh_dung(50.0, 5.0))                     # thời gian lùi: cũng dựng lại

    def test_nv_den_mot_lan_moi_luot(self):
        tb = Table('B1', [[0, 0], [10, 0], [10, 10], [0, 10]])
        ra = [tb.nhan_vien_toi(k / 10, True) for k in range(0, 80)]
        self.assertEqual(ra.count(True), 1)                          # lần đầu của lượt tới
        self.assertGreaterEqual(ra.count(False), 1)                  # gửi lại mỗi 5 s cho máy chủ


class TestGiuCho(unittest.TestCase):
    """Khách để đồ cá nhân lại bàn rồi ra ngoài: không báo khách rời / cần dọn, khách về không báo khách mới."""

    def ban(self):
        tb = Table('B1', [[0, 0], [10, 0], [10, 10], [0, 10]])
        chay(tb, 0, 3, 0, 0.1)
        self.assertEqual(chay(tb, 3, 8, 2, 0.9), ['khach_moi'])
        return tb

    def roi(self, tb, t0):
        """Chạy tới lúc bàn báo khách rời, như pipeline: thấy đồ cá nhân thì giữ chỗ. Trả lúc đó."""
        for k in range(200):
            t = t0 + k / 10
            ev = [e for e, _ in tb.update(t, 0, 0.9, 1.0)]
            if 'khach_roi' in ev:
                self.assertFalse(tb.het_giu)
                tb.giu_cho(t)
                return t
        self.fail('không thấy khách rời')

    def test_khach_ve_van_la_luot_cu(self):
        tb = self.ban()
        t = self.roi(tb, 8)
        self.assertEqual(tb.state, 'co_khach')
        self.assertEqual(chay(tb, t, t + 120, 0, 0.9), [])            # vắng 2 phút, đồ còn đó: im lặng
        self.assertEqual(tb.state, 'co_khach')
        self.assertEqual(chay(tb, t + 120, t + 130, 2, 0.9), [])      # khách về: không báo khách mới
        self.assertIsNone(tb.t_giu)
        ev = chay(tb, t + 130, t + 140, 0, 0.9)                       # lần này đi thật (pipeline không giữ nữa)
        self.assertEqual(ev, ['khach_roi', 'can_don'])

    def test_qua_han_thi_ve_luat_cu(self):
        tb = self.ban()
        t = self.roi(tb, 8)
        ev = chay(tb, t, t + Table.GIU_DO_S + 10, 0, 0.9)
        self.assertEqual(ev, ['khach_roi', 'can_don'])
        self.assertTrue(tb.het_giu)                                   # pipeline thấy cờ này thì không giữ chỗ lần nữa
        self.assertEqual(tb.state, 'can_don')

    def test_khong_giu_thi_nhu_cu(self):
        tb = self.ban()
        self.assertEqual(chay(tb, 8, 20, 0, 0.9), ['khach_roi', 'can_don'])
        self.assertFalse(tb.het_giu)

    def test_do_thuoc_ban_nao(self):
        b1 = Table('B1', [[100, 100], [300, 100], [300, 200], [100, 200]])
        b2 = Table('B2', [[400, 100], [600, 100], [600, 200], [400, 200]])
        ts = [b1, b2]
        self.assertTrue(ef.thuoc_ban(ts, b1, (200, 150)))             # trên bàn
        self.assertTrue(ef.thuoc_ban(ts, b1, (200, 225)))             # túi trên ghế sát bàn
        self.assertFalse(ef.thuoc_ban(ts, b1, (200, 400)))            # xa bàn
        self.assertFalse(ef.thuoc_ban(ts, b1, (390, 150)))            # sát bàn bên cạnh hơn
        self.assertTrue(ef.thuoc_ban(ts, b2, (390, 150)))

    def test_model_loi_thi_khong_giu(self):
        class Hong:
            def predict(self, *a, **k):
                raise RuntimeError('model hỏng')

        class A:
            device, yoloe_imgsz, half = 'cpu', 640, False
        tb = Table('B1', [[0, 0], [10, 0], [10, 10], [0, 10]])
        self.assertEqual(ef.do_ca_nhan(Hong(), Hong(), ANH, tb, [tb], A(), 640, {}), [])


class TestNhanVienCanh(unittest.TestCase):
    def test_co_nv_canh(self):
        khach = [100, 100, 200, 300]                                  # cao 200, tâm (150, 200)
        self.assertTrue(ef.co_nv_canh(khach, [(300, 200)], 1.25))     # nhân viên cách 150 px
        self.assertFalse(ef.co_nv_canh(khach, [(600, 200)], 1.25))    # cách 450 px
        self.assertFalse(ef.co_nv_canh(khach, [], 1.25))
        self.assertFalse(ef.co_nv_canh(khach, [(150, 200)], 0))       # 0 = tắt

    def test_da_so_dung(self):
        self.assertTrue(ef.da_so_dung([(0, 'dung'), (1, 'dung'), (2, 'ngoi')]))
        self.assertFalse(ef.da_so_dung([(0, 'dung')]))                # mới thấy một lần: chưa chắc
        self.assertFalse(ef.da_so_dung([(0, 'ngoi'), (1, 'ngoi'), (2, 'dung')]))
        self.assertFalse(ef.da_so_dung(()))


class TestLich(unittest.TestCase):
    def test_lich_theo_khung_da_xu_ly(self):
        """File chạy đúng tốc độ thật bỏ 1 khung giữa hai khung xử lý, bắt đầu ở khung lẻ: "i % 4 == 0" không bao giờ
        tới lượt; tính "có đi qua một bội số của 4 không" thì vẫn đều, đúng nhịp mỗi 4 khung video."""
        video = list(range(1, 400, 2))
        self.assertEqual(sum(1 for i in video if i % 4 == 0), 0)
        self.assertEqual(sum(1 for a, b in zip(video, video[1:]) if ef.toi_luot(b, a, 4)), 99)
        du = list(range(0, 400))                                     # xử lý đủ mọi khung: y như i % N == 0
        for moi in (2, 3, 4, 20, 100):
            self.assertEqual([i for a, i in zip([-1] + du, du) if ef.toi_luot(i, a, moi)],
                             [i for i in du if i % moi == 0])
        self.assertTrue(ef.toi_luot(7, 6, 0))                        # N <= 1: khung nào cũng chạy, không chia cho 0
        self.assertEqual(sum(1 for a, b in zip(range(0, 900, 9), range(9, 900, 9)) if ef.toi_luot(b, a, 4)), 99)


class TestHetBoNho(unittest.TestCase):
    def test_nhan_ra_loi_het_bo_nho_gpu(self):
        self.assertTrue(ef.la_het_bo_nho(RuntimeError('CUDA out of memory. Tried to allocate 20.00 MiB')))
        self.assertFalse(ef.la_het_bo_nho(RuntimeError('lỗi khác')))
        self.assertIn('--device cpu', ef.HET_BO_NHO)


if __name__ == '__main__':
    unittest.main()
