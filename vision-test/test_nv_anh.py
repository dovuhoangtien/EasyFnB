"""Nhận nhân viên theo ảnh: học thêm dáng từ camera mà không trôi sang người khác."""
import unittest
from unittest import mock

import cv2
import numpy as np
import torch

import thiet_lap


def vec(goc_do):
    """Véc-tơ đơn vị lệch `goc_do` độ so với ảnh mẫu (độ giống = cos của góc)."""
    r = np.radians(goc_do)
    return [float(np.cos(r)), float(np.sin(r)), 0.0]


class Gia:
    """Model giả: mỗi 'ảnh' là một véc-tơ có sẵn."""

    def features(self, imgs):
        return torch.tensor([im for im in imgs], dtype=torch.float32)


class TestThuVienNV(unittest.TestCase):
    def tv(self):
        tv = thiet_lap.ThuVienNV(Gia())
        tv.goc = tv.emb = torch.tensor([vec(0)], dtype=torch.float32)
        return tv

    def test_chua_co_anh(self):
        self.assertEqual(thiet_lap.ThuVienNV(Gia()).probs([vec(0)]), [None])

    def test_hoc_them_dang_moi(self):
        tv = self.tv()
        with mock.patch('time.monotonic', return_value=100.0):
            p = tv.probs([vec(25)])            # giống 0,906: chắc là nhân viên, dáng hơi khác
        self.assertGreater(p[0], 0.9)
        self.assertEqual(len(tv.them), 1)
        with mock.patch('time.monotonic', return_value=102.0):
            # dáng lệch 40 độ so với ảnh mẫu (0,77) trước đây chưa đủ điểm; giờ gần dáng vừa học (lệch 15 độ)
            self.assertGreater(tv.probs([vec(40)])[0], 0.9)

    def test_khong_hoc_nguoi_la(self):
        tv = self.tv()
        with mock.patch('time.monotonic', return_value=100.0):
            self.assertEqual(tv.probs([vec(50)]), [0.0])       # giống 0,64: khách
        self.assertEqual(tv.them, [])

    def test_khong_troi_dan(self):
        """Dáng học thêm phải còn giống ẢNH GỐC, nên không thể học nối đuôi nhau ra xa mãi."""
        tv = self.tv()
        for i, goc in enumerate((25, 40, 60, 80)):
            with mock.patch('time.monotonic', return_value=100.0 + 2 * i):
                tv.probs([vec(goc)])
        self.assertLessEqual(len(tv.them), 2)                  # 60 và 80 độ đã quá khác ảnh gốc
        with mock.patch('time.monotonic', return_value=200.0):
            self.assertLess(tv.probs([vec(90)])[0], 0.5)

    def test_moi_giay_mot_dang_va_co_tran(self):
        tv = self.tv()
        with mock.patch('time.monotonic', return_value=100.0):
            tv.probs([vec(25)])
        with mock.patch('time.monotonic', return_value=100.3):
            tv.probs([vec(-25)])
        self.assertEqual(len(tv.them), 1)
        tv.them = [tv.them[0]] * tv.HOC_TOI_DA
        with mock.patch('time.monotonic', return_value=110.0):
            tv.probs([[float(np.cos(0.44)), 0.0, float(np.sin(0.44))]])
        self.assertEqual(len(tv.them), tv.HOC_TOI_DA)

    def test_doi_anh_mau_thi_quen_dang_cu(self):
        tv = self.tv()
        with mock.patch('time.monotonic', return_value=100.0):
            tv.probs([vec(25)])
        ok, jpg = cv2.imencode('.jpg', np.zeros((8, 8, 3), np.uint8))
        with mock.patch.object(Gia, 'features', return_value=torch.tensor([vec(0)])):
            tv.load([('lan', 'body', jpg.tobytes())])
        self.assertEqual(tv.them, [])
        self.assertEqual(tuple(tv.emb.shape), (1, 3))


if __name__ == '__main__':
    unittest.main()
