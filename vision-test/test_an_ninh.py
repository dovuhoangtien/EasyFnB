"""Test an_ninh.py (ngoài giờ, khu cấm, lấy đồ) bằng dữ liệu bám người giả: không cần GPU, model hay mạng.

    python -m unittest test_an_ninh -v
"""
import unittest

import numpy as np

from an_ninh import AnNinh, tam_chan

FPS = 10
MO = dict(closed=False, after_hours=True, restricted=True, item_taken=True, delivery_now=False, blur_faces=True)
DONG = dict(MO, closed=True)
QUAY = dict(id='quay1', type='quay', name='Quầy thu ngân', poly=[[0, 400], [300, 400], [300, 720], [0, 720]])
CUA = dict(id='cua1', type='cua', name='Cửa', poly=[[1000, 400], [1280, 400], [1280, 720], [1000, 720]])
BAN = 'B3'
TUI = [600, 300, 660, 360]       # túi trên bàn B3


def nguoi(tid, box, staff=False, ban=None, ngoi=False, chan=None, tay=None, da_xet=True):
    """Một người như pipeline đưa vào: khung xương chỉ có cổ chân / cổ tay khi cho trước."""
    kp = np.zeros((17, 2), np.float32)
    kc = np.zeros(17, np.float32)
    if chan is not None:
        kp[15] = kp[16] = chan
        kc[15] = kc[16] = 0.9
    if tay is not None:
        kp[9] = tay
        kc[9] = 0.9
    return dict(id=tid, box=list(map(float, box)), kp=kp, kc=kc, staff=staff, da_xet=da_xet,
                walking=not ngoi, dung=not ngoi, ban=ban)


def chay(an, t0, t1, ham, cfg, areas=()):
    """Gọi cap_nhat mỗi khung từ t0 tới t1, ham(t) -> danh sách người. Trả mọi sự kiện."""
    out = []
    for k in range(int(round((t1 - t0) * FPS))):
        t = t0 + k / FPS
        out += [dict(e, _t=t) for e in an.cap_nhat(t, ham(t), cfg, areas)]
    return out


class TamChan(unittest.TestCase):
    def test_tam_chan(self):
        p = nguoi(1, [100, 100, 200, 400], chan=(150, 390))
        self.assertEqual(tam_chan(p['kp'], p['kc'], p['box']), (150.0, 390.0))
        p = nguoi(1, [100, 100, 200, 400])           # không thấy cổ chân: đáy khung
        self.assertEqual(tam_chan(p['kp'], p['kc'], p['box']), (150.0, 400.0))


class NgoaiGio(unittest.TestCase):
    def test_dong_cua_co_nguoi_3_giay_thi_bao_mot_lan(self):
        an = AnNinh()
        ev = chay(an, 0, 10, lambda t: [nguoi(5, [1050, 300, 1150, 600], chan=(1100, 590))], DONG, [CUA, QUAY])
        self.assertEqual(len(ev), 1)
        e = ev[0]
        self.assertEqual((e['loai'], e['nguoi'], e['area'], e['ban']), ('co_nguoi_ngoai_gio', 5, 'cua1', None))
        self.assertAlmostEqual(e['_t'], 3.0, delta=0.15)
        # cả camera 5 phút mới báo lại một lần, kể cả người khác (đỡ cắt clip liên tục)
        ev = chay(an, 10, 70, lambda t: [nguoi(6, [1050, 300, 1150, 600], chan=(1100, 590))], DONG, [CUA])
        self.assertEqual(ev, [])
        ev = chay(an, 300, 306, lambda t: [nguoi(5, [1050, 300, 1150, 600], chan=(1100, 590))], DONG, [CUA])
        self.assertEqual(len(ev), 1)

    def test_thoang_qua_duoi_3_giay_hoac_quan_mo_thi_khong_bao(self):
        an = AnNinh()
        self.assertEqual(chay(an, 0, 2.5, lambda t: [nguoi(1, [500, 300, 600, 600])], DONG), [])
        self.assertEqual(chay(an, 10, 20, lambda t: [nguoi(2, [500, 300, 600, 600])], MO), [])
        self.assertEqual(chay(an, 20, 30, lambda t: [nguoi(3, [500, 300, 600, 600])], dict(DONG, after_hours=False)), [])
        # không ở vùng nào: area None
        ev = chay(an, 30, 34, lambda t: [nguoi(4, [500, 100, 600, 300])], DONG, [CUA])
        self.assertEqual([(e['loai'], e['area']) for e in ev], [('co_nguoi_ngoai_gio', None)])

    def test_mat_dau_ngan_van_tinh_lien_tuc(self):
        an = AnNinh()
        # khung 1,5-1,9 s không thấy người (bị che): vẫn liên tục, báo ở 3 s
        ev = chay(an, 0, 5, lambda t: [] if 1.5 <= t < 2.0 else [nguoi(7, [500, 300, 600, 600])], DONG)
        self.assertEqual(len(ev), 1)
        self.assertAlmostEqual(ev[0]['_t'], 3.0, delta=0.15)


class KhuCam(unittest.TestCase):
    def test_khach_trong_quay_3_giay(self):
        an = AnNinh()
        ev = chay(an, 0, 10, lambda t: [nguoi(8, [100, 300, 200, 600], chan=(150, 590))], MO, [QUAY, CUA])
        self.assertEqual([(e['loai'], e['area'], e['nguoi']) for e in ev], [('vao_khu_cam', 'quay1', 8)])
        self.assertAlmostEqual(ev[0]['_t'], 3.0, delta=0.15)

    def test_nhan_vien_giao_hang_quan_dong_vung_khac_thi_khong_bao(self):
        an = AnNinh()
        o_quay = lambda **kw: (lambda t: [nguoi(9, [100, 300, 200, 600], chan=(150, 590), **kw)])
        self.assertEqual(chay(an, 0, 10, o_quay(staff=True), MO, [QUAY]), [])
        self.assertEqual(chay(an, 10, 20, o_quay(da_xet=False), MO, [QUAY]), [])      # chưa chấm nhân viên/khách
        self.assertEqual(chay(an, 20, 30, o_quay(), dict(MO, delivery_now=True), [QUAY]), [])
        self.assertEqual(chay(an, 30, 40, o_quay(), dict(MO, restricted=False), [QUAY]), [])
        # quán đóng: chỉ báo ngoài giờ, không báo khu cấm
        self.assertEqual({e['loai'] for e in chay(an, 40, 50, o_quay(), DONG, [QUAY])}, {'co_nguoi_ngoai_gio'})
        # vùng cửa không phải khu cấm; tâm chân ngoài quầy dù khung người chạm quầy
        self.assertEqual(chay(an, 50, 60, lambda t: [nguoi(10, [1050, 300, 1150, 600], chan=(1100, 590))], MO, [CUA]), [])
        self.assertEqual(chay(an, 60, 70, lambda t: [nguoi(11, [250, 100, 350, 390], chan=(300, 385))], MO, [QUAY]), [])

    def test_doi_vung_va_bao_lai_sau_60_giay(self):
        an = AnNinh()
        kho = dict(id='kho1', type='kho', name='Kho', poly=[[400, 400], [700, 400], [700, 720], [400, 720]])
        di = lambda t: [nguoi(12, [100, 300, 200, 600], chan=(150, 590))] if t < 5 else \
            [nguoi(12, [500, 300, 600, 600], chan=(550, 590))]
        ev = chay(an, 0, 10, di, MO, [QUAY, kho])
        self.assertEqual([e['area'] for e in ev], ['quay1', 'kho1'])
        ev = chay(an, 10, 75, lambda t: [nguoi(12, [500, 300, 600, 600], chan=(550, 590))], MO, [QUAY, kho])
        self.assertEqual(len(ev), 1)      # lần báo trước ở kho lúc ~8 s: báo lại sau 60 giây


class LayDo(unittest.TestCase):
    """Khách A (#1) ngồi bàn B3, để túi lên bàn. Rồi có người cầm túi đi."""

    def dung_canh(self, an, vector=None):
        a = lambda t: [nguoi(1, [560, 250, 700, 520], ban=BAN, ngoi=True)]
        an.cap_nhat(0, a(0), MO)
        chup = lambda p: np.full((40, 20, 3), 7, np.uint8)
        t = 0.0
        while t < 25:                         # A ngồi 25 giây; túi thấy mỗi giây
            an.cap_nhat(t, a(t), MO, chup=chup)
            if abs(t - round(t)) < 1e-6:
                self.assertEqual(an.quet_do(t, BAN, [('túi xách', TUI)]), [])
            t = round(t + 0.1, 3)
        self.assertIn(1, an.nguoi_ban[BAN])
        self.assertTrue(an.do_ban[BAN][0]['cua_ban'])
        return t

    def lay(self, an, t, tid, staff=False, quet_tu=None):
        """Người tid đi tới, đưa tay vào túi lúc t+1, cầm đi; quét đồ mỗi giây (từ t+2 túi không còn)."""
        out = []
        for k in range(80):
            tt = round(t + k / FPS, 3)
            if tt < t + 1.5:
                p = [nguoi(tid, [640, 200, 760, 600], staff=staff, tay=(630, 330))]
            else:
                p = [nguoi(tid, [900, 200, 1020, 600], staff=staff, tay=(910, 400))]   # đã đi khỏi bàn
            an.cap_nhat(tt, p, MO)
            if abs(tt - round(tt)) < 1e-6:
                out += an.quet_do(tt, BAN, [('túi xách', TUI)] if tt < t + 1.5 else [], lay_anh=lambda b, t_: np.ones((4, 4, 3), np.uint8))
        return out

    def test_nguoi_la_lay_tui_thi_bao(self):
        an = AnNinh()
        t = self.dung_canh(an)
        ev = self.lay(an, t, 2)
        self.assertEqual(len(ev), 1)
        e = ev[0]
        self.assertEqual((e['loai'], e['ban'], e['nguoi'], e['chi_tiet']), ('lay_do', BAN, 2, 'túi xách'))
        self.assertIsNotNone(e['ref'])                    # ảnh người ngồi bàn (A)
        self.assertLess(e['t_lay'], t + 1.5)
        self.assertEqual(an.do_ban[BAN], [])

    def test_chinh_khach_hoac_nhan_vien_lay_thi_khong_bao(self):
        an = AnNinh()
        t = self.dung_canh(an)
        self.assertEqual(self.lay(an, t, 1), [])          # A tự cầm túi của mình
        an = AnNinh()
        t = self.dung_canh(an)
        self.assertEqual(self.lay(an, t, 3, staff=True), [])
        self.assertIn('nhân viên', an.nhat_ky[-1][1])

    def test_nguoi_dat_do_xuong_tu_lay_lai_thi_khong_bao(self):
        """Khách #5 vừa tới, đứng đặt túi lên bàn, 12 giây sau cầm túi đi đổi bàn: chưa ngồi đủ lâu để là người
        của bàn, nhưng chính họ đặt túi xuống nên không báo. Người khác (#2) cầm thì vẫn báo."""
        for nguoi_lay, so_bao in ((5, 0), (2, 1)):
            an = AnNinh()
            t = 0.0
            while t < 12:
                # #5 đặt túi rồi ra quầy gọi món từ giây thứ 8
                an.cap_nhat(t, [nguoi(5, [640, 200, 760, 600], tay=(630, 330))] if t < 8 else [], MO)
                if abs(t - round(t)) < 1e-6:
                    self.assertEqual(an.quet_do(t, BAN, [('túi xách', TUI)]), [])
                t = round(t + 0.1, 3)
            self.assertEqual(an.do_ban[BAN][0]['dat'], 5)
            self.assertEqual(len(self.lay(an, t, nguoi_lay)), so_bao)

    def test_khach_quay_lai_ma_bam_moi_giong_vector_thi_khong_bao(self):
        an = AnNinh(vector=lambda img: np.ones(4, np.float32) / 2)     # ai cũng "giống" nhau
        t = self.dung_canh(an)
        self.assertEqual(self.lay(an, t, 44), [])
        an = AnNinh(vector=lambda img: (np.array([1, 0, 0, 0], np.float32) if img.shape[0] == 40
                                        else np.array([0, 1, 0, 0], np.float32)))   # khác hẳn
        t = self.dung_canh(an)
        self.assertEqual(len(self.lay(an, t, 44)), 1)

    def test_do_chua_dung_yen_du_lau_hoac_bi_che_thi_khong_tinh(self):
        an = AnNinh()
        an.cap_nhat(0, [], MO)
        for k in range(5):                     # túi mới thấy 5 giây rồi mất: chưa là đồ của bàn
            an.quet_do(float(k), BAN, [('túi xách', TUI)])
        an.cap_nhat(5.0, [nguoi(2, [640, 200, 760, 600], tay=(630, 330))], MO)
        an.cap_nhat(6.0, [], MO)
        for k in range(6, 10):
            self.assertEqual(an.quet_do(float(k), BAN, []), [])
        self.assertEqual(an.do_ban[BAN], [])
        # đồ của bàn bị một người đứng che: không đếm là mất
        an = AnNinh()
        t = self.dung_canh(an)
        che = [nguoi(1, [560, 250, 700, 520], ban=BAN, ngoi=True)]
        for k in range(10):
            an.cap_nhat(t + k, che, MO)
            self.assertEqual(an.quet_do(t + k, BAN, []), [])
        self.assertEqual(an.do_ban[BAN][0]['mat'], 0)

    def test_khong_ai_o_gan_thi_khong_bao_va_xoa_ban(self):
        an = AnNinh()
        t = self.dung_canh(an)
        for k in range(1, 5):                  # túi biến mất (khuất góc) mà không có cổ tay nào gần
            an.cap_nhat(t + k, [nguoi(9, [100, 100, 200, 400], tay=(150, 200))], MO)
            self.assertEqual(an.quet_do(t + k, BAN, []), [])
        self.assertIn('không rõ ai', an.nhat_ky[-1][1])
        an.xoa_ban(BAN)
        self.assertNotIn(BAN, an.nguoi_ban)

    def test_tat_item_taken_thi_khong_thanh_nguoi_cua_ban(self):
        an = AnNinh()
        for k in range(300):
            an.cap_nhat(k / FPS, [nguoi(1, [560, 250, 700, 520], ban=BAN, ngoi=True)], dict(MO, item_taken=False))
        self.assertEqual(an.nguoi_ban, {})

    def test_ban_chua_chac_thi_chua_thanh_nguoi_cua_ban(self):
        an = AnNinh()
        for k in range(300):         # khop_ban chưa chốt bàn (ban_chac False): 30 giây vẫn chưa gắn
            p = dict(nguoi(1, [560, 250, 700, 520], ban=BAN, ngoi=True), ban_chac=False)
            an.cap_nhat(k / FPS, [p], MO)
        self.assertEqual(an.nguoi_ban, {})
        for k in range(300, 600):    # đã chốt: thành người của bàn như cũ
            p = dict(nguoi(1, [560, 250, 700, 520], ban=BAN, ngoi=True), ban_chac=True)
            an.cap_nhat(k / FPS, [p], MO)
        self.assertIn(1, an.nguoi_ban.get(BAN, {}))

    def test_anh_bang_chung(self):
        an = AnNinh()
        W, H = 1280, 720
        buf = [(k / FPS, np.full((H, W, 3), k, np.uint8)) for k in range(50)]
        ev = chay(an, 0, 4, lambda t: [nguoi(5, [500, 300, 600, 600])], DONG)
        crop, strip, ov = an.anh_bang_chung(buf, ev[0], W, H)
        self.assertEqual(strip.shape, (768, 576, 3))
        self.assertEqual(ov.shape[1], 768)
        self.assertGreater(crop.size, 0)
        self.assertIsNone(an.anh_bang_chung([], ev[0], W, H))


if __name__ == '__main__':
    unittest.main()
