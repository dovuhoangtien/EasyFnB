"""Chạy: python -m unittest test_nhin_quanh"""
import unittest

import numpy as np

from nhin_quanh import NhinQuanh


def nguoi(tid, x, yaw=0.0, cui=0.0, staff=False, table=None, walking=False):
    kp, kc = np.zeros((17, 2)), np.zeros(17)
    kp[3], kp[4] = (x + 10, 100), (x - 10, 100)                  # hai tai
    kp[0] = (x + 10 * yaw, 100 + 20 * cui)                       # mũi
    kp[5], kp[6] = (x + 30, 140), (x - 30, 140)
    kc[[0, 3, 4, 5, 6]] = 0.9
    return dict(id=tid, box=(x - 40, 60, x + 40, 300), kp=kp, kc=kc, staff=staff, walking=walking,
                calling=False, table=table)


def chay(yaw_fn, khac=(), giay=8.0, **kw):
    nq, ra = NhinQuanh(), []
    for i in range(int(giay * 10)):
        t = i / 10
        ra += nq.update(t, [nguoi(1, 300, yaw_fn(t), **kw), *khac])
    return ra


class T(unittest.TestCase):
    def test_nhin_thang_khong_bao(self):
        self.assertEqual(chay(lambda t: 0.0), [])

    def test_quay_qua_lai_thi_bao_mot_lan(self):
        ra = chay(lambda t: 1.0 if int(t) % 2 else -1.0)
        self.assertEqual(len(ra), 1)
        self.assertIn('qua lại', ra[0][2])

    def test_cui_xem_dien_thoai_khong_bao(self):
        self.assertEqual(chay(lambda t: 1.0 if int(t) % 2 else -1.0, cui=1.5), [])

    def test_nhin_ve_nhan_vien_thi_bao(self):
        ra = chay(lambda t: 1.0, khac=[nguoi(9, 700, staff=True)])
        self.assertEqual(len(ra), 1)
        self.assertIn('nhân viên', ra[0][2])

    def test_noi_chuyen_voi_nguoi_cung_ban_khong_bao(self):
        ban = object()
        ra = chay(lambda t: 1.0 if int(t) % 2 else -1.0, table=ban,
                  khac=[nguoi(2, 450, table=ban), nguoi(3, 150, table=ban)])
        self.assertEqual([p['id'] for p, _, _ in ra if p['id'] == 1], [])

    def test_dang_di_khong_bao(self):
        self.assertEqual(chay(lambda t: 1.0 if int(t) % 2 else -1.0, walking=True), [])
