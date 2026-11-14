"""Thử phần phân tích và gợi ý cho ca sau (server/goi_y.py) và các câu hỏi mới của trợ lý.

Chạy (trong easy-fnb):  python -m unittest server.tests.test_goi_y -v
"""
import tempfile
import unittest

from server import goi_y
from server import tro_ly as tl
from server.hub import clock
from server.tests.test_tro_ly import ev, tao_ca


class GoiY(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.hub = tao_ca(self.tmp.name)[0]

    def test_xep_ca_dem_viec_va_nguoi(self):
        rows = goi_y.xep_ca(self.hub)
        self.assertEqual(sum(r['tasks'] for r in rows), 4)          # 5 việc, 1 việc đã huỷ
        self.assertTrue(all(r['staff'] >= 1 for r in rows if r['tasks']))   # Lan vào từ trước, Minh vừa vào
        self.assertIn('thieu', {r['verdict'] for r in rows})        # B2: Minh nhận chậm
        b = goi_y.khoi_xep_ca(self.hub)
        self.assertEqual(b['type'], 'table')
        self.assertEqual(len(b['columns']), 5)

    def test_goi_y_co_bang_chung(self):
        gy = goi_y.goi_y(self.hub)
        self.assertEqual(gy[0]['id'], 'thieu_nguoi')
        self.assertTrue(gy[0]['ids'])
        b = goi_y.khoi_goi_y(self.hub)
        self.assertEqual(b['type'], 'insights')
        self.assertTrue(b['items'][0]['events'])
        self.assertNotRegex(' '.join(i['text'] + i['action'] for i in b['items']), r'\d+ giây')

    def test_ca_trong(self):
        self.hub.reset()
        self.assertEqual(goi_y.goi_y(self.hub), [])
        self.assertIsNone(goi_y.khoi_goi_y(self.hub))
        self.assertIsNone(goi_y.khoi_xep_ca(self.hub))

    def test_bao_nham_nhieu_lan_o_mot_ban(self):
        for _ in range(2):
            aid = self.hub.edge_event(ev(table='B7'))
            self.hub.cancel(aid, 'manager', 'báo nhầm')
            self.hub.alerts[aid]['created_at'] -= 600_000       # lùi về trước để lần sau không bị gộp
            for k in ('done_at', 'cancelled_at'):
                if self.hub.alerts[aid].get(k):
                    self.hub.alerts[aid][k] -= 600_000
        self.assertEqual(sum(1 for a in self.hub.alerts.values() if a['table'] == 'B7'), 2)
        self.assertIn('bao_nham', [g['id'] for g in goi_y.goi_y(self.hub)])

    def test_tro_ly_tra_loi_xep_ca_va_goi_y(self):
        ans, blocks = tl.tra_loi_rules(self.hub, 'Ca sau nên xếp người thế nào?')
        self.assertIn('Đông nhất', ans)
        self.assertEqual(blocks[0]['type'], 'table')
        ans, blocks = tl.tra_loi_rules(self.hub, 'Nên đổi gì cho ca sau?')
        self.assertEqual(blocks[0]['type'], 'insights')

    def test_tro_ly_xem_lai_theo_gio(self):
        a = next(a for a in self.hub.alerts.values() if a['table'] == 'B1')
        gio = clock(a['created_at'])[:5]
        ans, blocks = tl.tra_loi_rules(self.hub, f'cho xem lúc {gio} bàn B1')
        self.assertEqual(blocks[0]['type'], 'events')
        self.assertEqual({i['table'] for i in blocks[0]['items']}, {'B1'})
        ans, blocks = tl.tra_loi_rules(self.hub, 'lúc 03:07 có gì')
        self.assertIn('không ghi sự kiện nào', ans)


if __name__ == '__main__':
    unittest.main()
