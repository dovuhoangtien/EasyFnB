"""Trợ lý cài đặt trong chat (server/cai_dat.py): công cụ chỉ dựng khối, không bao giờ ghi vào hub.

Chạy (trong easy-fnb):  python -m unittest server.tests.test_tro_ly_setup -v
"""
import asyncio
import copy
import tempfile
import unittest
from pathlib import Path

from server import cai_dat as cd
from server import tro_ly as tl
from server.hub import Hub


class Tat:
    enabled = False
    model = None


class Co:
    enabled = True
    model = 'gia'


def chup(hub):
    return copy.deepcopy((hub.staff, hub.zones, hub.settings))


class CaiDat(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.hub = Hub(Path(self.tmp.name), Tat())

    def tearDown(self):
        self.tmp.cleanup()

    # ------------------------------------------------------------ nhân viên
    def test_them_nhan_vien_tao_ma_khong_dau_khong_trung(self):
        truoc = chup(self.hub)
        b, bao = cd.khoi_nhan_vien(self.hub, them=['Hoa | phục vụ', 'Tú Anh | dọn bàn', 'Bảo | thu ngân'])
        self.assertEqual(chup(self.hub), truoc, 'dựng khối không được ghi gì')
        self.assertEqual([(r['change'], r['id'], r['name'], r['role']) for r in b['rows']],
                         [('them', 'hoa', 'Hoa', 'serve'), ('them', 'tuanh', 'Tú Anh', 'clean'),
                          ('them', 'bao', 'Bảo', 'cashier')])
        self.assertEqual([x['id'] for x in b['base']], [s['id'] for s in self.hub.staff])

    def test_xung_ho_bo_di_va_tu_khac_tu(self):
        b, bao = cd.khoi_nhan_vien(self.hub, them=['anh Tư | dọn', 'chị Mai | thu ngân'])
        self.assertEqual([(r['id'], r['name']) for r in b['rows']], [('tu2', 'Tư'), ('mai', 'Mai')])
        self.assertEqual(bao, '')
        b, bao = cd.khoi_nhan_vien(self.hub, bo=['tu'])          # gõ không dấu thì so không dấu
        self.assertEqual(b['rows'][0]['name'], 'Tú')

    def test_cam_noi_da_luu_khi_chua_bam(self):
        self.assertTrue(cd.NOI_DA_LUU.search('Dạ tôi đã cập nhật danh sách nhân viên'))
        self.assertTrue(cd.NOI_DA_LUU.search('Tôi đã chỉnh luật để sau 60 giây'))
        self.assertTrue(cd.NOI_DA_LUU.search('Quán đã được cài đặt giờ mở cửa'))
        self.assertFalse(cd.NOI_DA_LUU.search('Kiểm lại rồi bấm Lưu nhé'))

    def test_ten_da_co_thi_bao_khong_them(self):
        ten = self.hub.staff[0]['name']
        b, bao = cd.khoi_nhan_vien(self.hub, them=[f'{ten} | phục vụ'])
        self.assertIsNone(b)
        self.assertIn('đã có', bao)

    def test_ma_trung_thi_them_so(self):
        self.assertEqual(cd.ma_nv('Lan', {'lan', 'lan2'}), 'lan3')
        self.assertEqual(cd.ma_nv('Đức', set()), 'duc')

    def test_bo_va_doi_nhan_vien(self):
        s = self.hub.staff[0]
        s.setdefault('photos', []).append(dict(id='b1', kind='body', source='camera'))
        b, _ = cd.khoi_nhan_vien(self.hub, bo=[s['name']], doi=[f"{self.hub.staff[1]['name']} | | dọn bàn"])
        bo = next(r for r in b['rows'] if r['change'] == 'bo')
        self.assertEqual((bo['id'], bo['photos']), (s['id'], 1))
        doi = next(r for r in b['rows'] if r['change'] == 'doi')
        self.assertEqual(doi['role'], 'clean')

    def test_doc_cau_them_nhan_vien(self):
        self.assertEqual(cd.doc_them_nv('thêm nhân viên Lan phục vụ, chị Mai thu ngân và anh Tư dọn bàn'),
                         ['Lan | serve', 'Mai | cashier', 'Tư | clean'])
        self.assertEqual(cd.doc_them_nv('thêm Lan với Hoa chạy bàn'), ['Lan | serve', 'Hoa | serve'])
        self.assertEqual(cd.doc_them_nv('thêm người'), [])

    # ------------------------------------------------------------ luật báo
    def test_luat_bao_truoc_sau_va_gioi_han(self):
        truoc = chup(self.hub)
        b, loi = cd.khoi_luat(self.hub, {'escalate_s': 60, 'wait_food_s': 20, 'auto_close_s': 99999})
        self.assertEqual(chup(self.hub), truoc)
        self.assertEqual({r['key']: (r['before'], r['after']) for r in b['rows']},
                         {'escalate_s': (0, 60), 'wait_food_s': (15.0, 20.0)})
        self.assertIn('từ 0 tới 3600', loi)

    def test_luat_can_ai_khi_tat_ai(self):
        b, loi = cd.khoi_luat(self.hub, {'verify_call': True})
        self.assertIsNone(b)
        self.assertIn('cần AI', loi)

    def test_luat_khong_doi_gi_thi_hien_moi_dong(self):
        b, _ = cd.khoi_luat(self.hub)
        self.assertEqual(len(b['rows']), sum(1 for d in cd.LUAT if d[6] == 'phuc_vu'))

    def test_luat_da_dung_roi(self):
        b, loi = cd.khoi_luat(self.hub, {'escalate_s': 0})
        self.assertIsNone(b)
        self.assertIn('không cần đổi', loi)

    def test_luat_an_ninh_gio_va_cong_tac(self):
        b, loi = cd.khoi_luat(self.hub, {'open_time': '6h30', 'guard_mode': True, 'close_time': '25:00',
                                         'delivery_from': ''})
        self.assertEqual({r['key']: (r['before'], r['after'], r['setting']) for r in b['rows']},
                         {'open_time': ('07:00', '06:30', 'open_time'), 'guard_mode': (False, True, 'guard_mode')})
        self.assertEqual(b['title'], 'An ninh')
        self.assertIn('HH:MM', loi)

    def test_nhom_an_ninh_va_khong_bao_gio_co_che_mat(self):
        b, _ = cd.khoi_luat(self.hub, nhom='an_ninh')
        self.assertTrue(b['rows'] and all(r['group'] == 'an_ninh' for r in b['rows']))
        self.assertNotIn('blur_faces', {d[3] for d in cd.LUAT})
        self.assertTrue(set(cd.THAM_SO_LUAT.values()) <= {d[0] for d in cd.LUAT})

    def test_phong_chat_khong_co_cong_cu_cai_dat(self):
        t = tl.TroLy(self.hub, Co())
        ten = {f.__name__ for f in t.tools(dict(blocks=[]), 'phong')}
        self.assertFalse(ten & tl.CONG_CU_CHI_CHU)
        self.assertEqual({f.__name__ for f in cd.cong_cu(self.hub, lambda b, *_: {})}, tl.CONG_CU_CHI_CHU)

    # ------------------------------------------------------------ camera, bàn
    async def test_tim_ban_khi_camera_chua_noi_dua_ma_qr(self):
        ans, bs = await cd.tim_ban(self.hub, 'cam1')
        self.assertIn('chưa gửi hình', ans)
        self.assertEqual([(b['type'], b['kind']) for b in bs], [('qr', 'camera')])
        self.assertFalse(self.hub.jobs)

    async def test_tim_ban_ra_khoi_ban_khong_ghi(self):
        self.hub.edge_frame('cam1', 'live', b'\xff\xd8x')
        truoc = chup(self.hub)

        async def may_camera():
            while not self.hub.jobs:
                await asyncio.sleep(0.01)
            j = self.hub.take_jobs('cam1')[0]
            self.assertEqual(j['kind'], 'find_tables')
            sq = lambda x: dict(polygon=[[x, 10], [x + 50, 10], [x + 50, 60], [x, 60]], score=0.9)
            self.hub.job_result(j['id'], dict(frame_w=640, frame_h=360, tables=[sq(10), sq(200)]))

        (ans, bs), _ = await asyncio.gather(cd.tim_ban(self.hub, 'cam1', cho_s=2), may_camera())
        self.assertEqual(chup(self.hub), truoc)
        b = bs[0]
        self.assertEqual((b['type'], [t['id'] for t in b['tables']], b['merged']), ('ban', ['B1', 'B2'], None))
        self.assertIn('2 bàn', ans)

    async def test_tim_ban_may_camera_im_lang(self):
        self.hub.edge_frame('cam1', 'live', b'\xff\xd8x')
        ans, bs = await cd.tim_ban(self.hub, 'cam1', cho_s=0.05)
        self.assertIn('chưa trả lời', ans)
        self.assertEqual(bs, [])

    def test_da_co_vung_thi_chi_them_ban_moi(self):
        self.hub.set_zones(dict(camera='cam1', frame_w=1280, frame_h=720, tables=[
            dict(id='B1', polygon=[[20, 20], [120, 20], [120, 120], [20, 120]])]))
        sq = lambda x: dict(polygon=[[x, 10], [x + 50, 10], [x + 50, 60], [x, 60]])
        b = cd.khoi_ban(self.hub, 'cam1', dict(frame_w=640, frame_h=360, tables=[sq(10), sq(300)]))
        self.assertEqual([t['id'] for t in b['merged']], ['B1', 'B2'])     # bàn đầu trùng B1 cũ nên bỏ
        self.assertEqual(b['merged'][0]['polygon'][0], [10.0, 10.0])        # vùng cũ quy về cỡ khung mới
        self.assertEqual(b['existing'], ['B1'])

    # ------------------------------------------------------------ mã QR, chụp ảnh
    def test_qr_nhan_vien(self):
        b = cd.khoi_qr_nhan_vien(self.hub)
        self.assertEqual(len(b['staff']), len(self.hub.staff))
        one = cd.khoi_qr_nhan_vien(self.hub, self.hub.staff[0]['name'])
        self.assertEqual(len(one['staff']), 1)
        self.assertIsNone(cd.khoi_qr_nhan_vien(self.hub, 'Không Có Ai'))

    def test_chup_anh(self):
        b = cd.khoi_chup(self.hub, self.hub.staff[0]['name'], 'camera 2')
        self.assertEqual((b['type'], b['camera'], b['staff_id']), ('chup', 'cam2', self.hub.staff[0]['id']))

    # ------------------------------------------------------------ đường không AI
    async def test_rules_bat_cau_cai_dat(self):
        t = tl.TroLy(self.hub, Tat())
        for cau, loai in [('giúp tôi nối camera', 'qr'), ('thêm nhân viên Hoa phục vụ', 'xac_nhan'),
                          ('đổi luật báo', 'xac_nhan'), ('mã QR app nhân viên', 'qr'), ('thêm người', 'xac_nhan'),
                          ('tìm bàn', 'qr')]:
            r = await t.hoi(cau, 's')
            self.assertEqual(r['engine'], 'rules')
            self.assertEqual([b['type'] for b in r['blocks']], [loai], cau)
            self.assertTrue(set(r['suggestions']) <= set(cd.GOI_Y_CAI_DAT), cau)
        r = await t.hoi('giúp tôi setup', 's')
        self.assertEqual(r['blocks'], [])
        self.assertEqual(r['suggestions'][:2], ['Nối camera', 'Tìm bàn'])

    async def test_cau_so_lieu_khong_bi_bat_nham(self):
        t = tl.TroLy(self.hub, Tat())
        for cau in ('Hôm nay nhân viên làm việc thế nào?', 'Bàn nào đang chờ lâu?', 'Tóm tắt ca hôm nay'):
            self.assertFalse(cd.la_cai_dat(cau), cau)
            r = await t.hoi(cau, 's')
            self.assertFalse(any(b['type'] in cd.LOAI_KHOI for b in r['blocks']))

    async def test_cong_cu_adk_chi_dung_khoi(self):
        t = tl.TroLy(self.hub, Co())
        box = dict(blocks=[])
        f = {x.__name__: x for x in t.tools(box)}
        truoc = chup(self.hub)
        f['noi_camera']('cam1')
        f['sua_nhan_vien'](them_nguoi=['Hoa | phục vụ'])
        f['ma_qr_nhan_vien']()
        f['doi_luat_bao'](nhac_lai_sau_giay=60, kiem_tra_khach_goi=False)
        f['chup_anh_nhan_vien'](self.hub.staff[0]['name'])
        r = await f['tu_tim_ban']('cam1')     # camera chưa nối: báo lý do (hộp đã đủ 5 khối)
        self.assertIn('chưa gửi hình', r['ket_qua'])
        self.assertEqual(chup(self.hub), truoc)
        self.assertEqual([b['type'] for b in box['blocks']], ['qr', 'xac_nhan', 'qr', 'xac_nhan', 'chup'])


if __name__ == '__main__':
    unittest.main()
