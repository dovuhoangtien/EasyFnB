"""Trợ lý trả lời về tiền thu (server/doanh_thu_tro_ly.py), đường không AI, dùng sổ giả."""
import unittest

from server import doanh_thu_tro_ly as dt


class Kho:
    def all(self, sql, args=()):
        return [('1250000', '125000', 'hoa')] if args[0] == 2 else []


class Phong:
    kho = Kho()

    def _pays(self):
        return [dict(id=1, amount=300000, table='B3', ts=1_000_000, type='chuyen_khoan', status='confirmed'),
                dict(id=2, amount=125000, table='B6', ts=2_000_000, type='hoa_don', status='confirmed')]

    def revenue(self, day=None):
        # Sổ giả: mọi ngày đều có tiền (kể cả "hôm nay" thật), trừ 1/11 là ngày trống
        day = day or '2026-11-13'
        if day == '2026-11-01':
            return dict(day=day, total=0, count=0, transfers=0, visits=0, per_guest=None, hours=[], review=[], payments=[])
        return dict(day=day, total=425000, count=2, transfers=1, visits=3, per_guest=85000,
                    hours=[dict(hour='12', amount=300000, visits=2), dict(hour='17', amount=125000, visits=1)],
                    review=[dict(text='Bàn B5, 12:15 đến 13:01, 2 khách, chưa thấy thanh toán')], payments=self._pays())

    def payments(self, day):
        return self._pays() + [dict(id=3, amount=236000, table='B3', ts=3_000_000, type='hoa_don', status='void', note='gửi trùng')]


class DoanhThu(unittest.TestCase):
    def test_hom_nay(self):
        ans, bs = dt.tra_loi(Phong(), 'hom nay doanh thu bao nhieu')
        self.assertIn('425.000', ans)
        self.assertIn('chưa thấy thanh toán', ans)
        self.assertEqual([b['type'] for b in bs], ['stats', 'chart', 'table'])

    def test_ngay_chua_toi_va_ngay_trong(self):
        ans, bs = dt.tra_loi(Phong(), 'doanh thu ngay mai bao nhieu')
        self.assertIn('chưa tới', ans)
        self.assertEqual(bs, [])
        ans, bs = dt.tra_loi(Phong(), 'doanh thu 2026-11-01')
        self.assertIn('chưa có thanh toán', ans)

    def test_huy_va_sua(self):
        d = dt.doc(Phong(), '2026-11-13')
        self.assertEqual(d['da_huy'][0]['ly_do'], 'gửi trùng')
        self.assertEqual(d['da_sua_so_tien'][0]['so_tien_hien_nay'], 125000)
        self.assertEqual(d['lon_nhat']['ban'], 'B3')

    def test_nhan_ra_cau_hoi_tien(self):
        self.assertTrue(dt.la_hoi_tien('hom nay thu bao nhieu'))
        self.assertFalse(dt.la_hoi_tien('ban nao dang cho lau'))


if __name__ == '__main__':
    unittest.main()
