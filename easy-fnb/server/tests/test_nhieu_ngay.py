"""Nhìn lại nhiều ngày và nhân viên ngày cũ (server/nhieu_ngay.py), đọc từ dòng thời gian thật trong thư mục tạm."""
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from server import nhieu_ngay
from server.hub import Hub
from server.timeline import VN

T = int(datetime(2026, 11, 13, 15, 0, tzinfo=VN).timestamp() * 1000)     # thứ sáu


def s(day, h, m=0):
    return datetime(2026, 11, day, h, m, tzinfo=VN).timestamp()


class NhieuNgay(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.hub = Hub(Path(self.tmp.name), None)
        tl = self.hub.timeline
        for day, wait in ((10, 200), (12, 20)):
            tl.add('staff_online', ts=s(day, 7), staff='lan', text='Lan')
            tl.add('staff_offline', ts=s(day, 15), staff='lan', text='Lan')
            for i in range(3):
                aid = f'a{i}'
                tl.add('alert_created', ts=s(day, 12, i), table='B1', alert_id=aid, alert_kind='call')
                tl.add('alert_acked', ts=s(day, 12, i) + wait, table='B1', alert_id=aid, staff='lan', wait_s=wait)
                tl.add('alert_done', ts=s(day, 12, i) + wait + 30, table='B1', alert_id=aid, staff='lan', wait_s=wait)

    def tearDown(self):
        self.hub.timeline.close()
        self.tmp.cleanup()

    def test_khoang(self):
        self.assertEqual(nhieu_ngay.khoang('tuan nay thu bao nhieu', T)[:2], ('2026-11-09', '2026-11-13'))
        self.assertEqual(nhieu_ngay.khoang('7 ngay qua the nao', T)[:2], ('2026-11-07', '2026-11-13'))
        self.assertEqual(nhieu_ngay.khoang('thang truoc the nao', T)[:2], ('2026-10-01', '2026-10-31'))
        self.assertEqual(nhieu_ngay.khoang('tu 6/11 den 10/11', T)[:2], ('2026-11-06', '2026-11-10'))
        self.assertIsNone(nhieu_ngay.khoang('hom qua the nao', T))
        self.assertIsNone(nhieu_ngay.khoang('ban nao cho lau', T))

    def test_tong_hop_bo_ngay_trong_va_thay_xu_huong(self):
        ans, bs, rows = nhieu_ngay.tra_loi(self.hub, None, '2026-11-07', '2026-11-13', '7 ngày qua', T)
        self.assertEqual([r['ngay'] for r in rows], ['2026-11-10', '2026-11-12'])
        self.assertEqual((rows[0]['toc_do'], rows[1]['toc_do']), ('chậm', 'nhanh'))
        self.assertIn('nhanh lên', ans)
        self.assertEqual([b['type'] for b in bs], ['chart', 'table'])

    def test_khoang_khong_co_du_lieu(self):
        ans, bs, rows = nhieu_ngay.tra_loi(self.hub, None, '2026-10-01', '2026-10-31', 'tháng 10', T)
        self.assertIn('chưa ghi được ngày nào', ans)
        self.assertEqual(bs, [])

    def test_nhan_vien_ngay_cu(self):
        ans, bs, rows = nhieu_ngay.nhan_vien_ngay(self.hub, '2026-11-12', T)
        self.assertEqual((rows[0]['ten'], rows[0]['vao_ca'], rows[0]['ra_ca'], rows[0]['viec_nhan'], rows[0]['nhanh']),
                         ('Lan', '07:00', '15:00', 3, 3))
        self.assertEqual(nhieu_ngay.nhan_vien_ngay(self.hub, '2026-11-11', T)[2], [])


if __name__ == '__main__':
    unittest.main()
