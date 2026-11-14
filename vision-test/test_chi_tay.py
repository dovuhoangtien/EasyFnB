"""Luật "chỉ tay ngang không phải giơ tay gọi" (easyfnb_test.chi_tay)."""
import unittest

import numpy as np

import easyfnb_test as ef


def nguoi(co_tay):
    kp = np.zeros((17, 2), np.float32)
    kc = np.zeros(17, np.float32)
    kp[ef.LSH], kp[ef.RSH] = (100, 200), (160, 200)
    kp[ef.RWR] = co_tay
    kc[[ef.LSH, ef.RSH, ef.RWR]] = 0.9
    return kp, kc


class ChiTay(unittest.TestCase):
    def test_gio_thang_va_gio_cheo_la_goi(self):
        self.assertFalse(ef.chi_tay(*nguoi((165, 110))))     # giơ thẳng lên
        self.assertFalse(ef.chi_tay(*nguoi((230, 125))))     # giơ chéo cỡ 45 độ

    def test_duoi_ngang_la_chi_tay(self):
        self.assertTrue(ef.chi_tay(*nguoi((280, 170))))      # duỗi ngang, chỉ hơi cao hơn vai

    def test_tay_duoi_vai_hoac_khong_thay_thi_khong_ket_luan(self):
        self.assertFalse(ef.chi_tay(*nguoi((250, 260))))     # tay dưới vai: không phải việc của luật này
        kp, kc = nguoi((280, 170))
        kc[ef.RWR] = 0.1
        self.assertFalse(ef.chi_tay(kp, kc))


if __name__ == '__main__':
    unittest.main()
