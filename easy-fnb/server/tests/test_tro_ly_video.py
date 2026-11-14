"""Trợ lý xem lại: video, chuyện của một bàn, bàn đang ở bước nào, ngày khác (server/xem_lai.py).

Chạy (trong easy-fnb):  python -m unittest server.tests.test_tro_ly_video -v
Không gọi mạng, không cần máy camera: kho clip thật chạy trên thư mục tạm, máy camera được đóng giả bằng tay.
"""
import asyncio
import tempfile
import time
import unittest
from unittest import mock
from datetime import datetime
from pathlib import Path

from server import tro_ly as tl
from server import xem_lai as xl
from server.clips import Clips
from server.hub import Hub, clock, now_ms
from server.timeline import VN, day_of


class NoGemini:
    enabled = False
    model = None


class GeminiGia:
    ten = 'Gemini'
    enabled = True
    model = 'gemini-khong-co-that'


def mp4(n=2000):
    return b'\x00\x00\x00\x18ftypisom' + b'x' * n


def ms(y, mo, d, h, mi=0):
    return int(datetime(y, mo, d, h, mi, tzinfo=VN).timestamp() * 1000)


def ev(eid=None, kind='goi_phuc_vu', table='B1', camera='cam1'):
    return dict(camera=camera, kind=kind, table=table, score=0.9, **({'eid': eid} if eid else {}))


T = ms(2026, 11, 13, 14, 0)      # thứ sáu 13/11/2026, 14:00 giờ Việt Nam


class DocGio(unittest.TestCase):
    """Đọc giờ, ngày trong câu hỏi (câu đã bỏ dấu)."""

    def gio(self, cau, t=T):
        return xl.doc_gio(tl.bo_dau(cau), t)

    def test_gio_dong_ho(self):
        for cau in ('lúc 12h30 bàn 3 có gì', 'cho xem 12:30', 'xem lại lúc 12 giờ 30', 'khoảng 12 giờ rưỡi',
                    'video 12h30'):
            g = self.gio(cau)
            self.assertEqual((g['loai'], g['luc'], g['ten']), ('phut', ms(2026, 11, 13, 12, 30), '12:30'), cau)
            self.assertFalse(g['tuong_lai'])
        self.assertEqual(self.gio('lúc 12h có gì')['luc'], ms(2026, 11, 13, 12))
        self.assertEqual(self.gio('lúc 1 giờ chiều')['luc'], ms(2026, 11, 13, 13))
        self.assertEqual(self.gio('9 giờ sáng có ai gọi không')['luc'], ms(2026, 11, 13, 9))
        self.assertEqual(self.gio('lúc 12 giờ kém 15')['luc'], ms(2026, 11, 13, 11, 45))

    def test_khong_phai_gio(self):
        for cau in ('bàn 12 hôm nay thế nào', 'tóm tắt ca', 'có 5 giờ làm', 'ai nhanh nhất', 'nhân viên B12 giỏi'):
            self.assertIsNone(self.gio(cau), cau)

    def test_khoang_va_buoi(self):
        g = self.gio('kể lại từ 12:00 đến 12:30')
        self.assertEqual((g['loai'], g['tu'], g['den']), ('khoang', ms(2026, 11, 13, 12), ms(2026, 11, 13, 12, 30)))
        g = self.gio('trưa nay có chuyện gì')
        self.assertEqual((g['loai'], g['tu'], g['den'], g['ten']),
                         ('khoang', ms(2026, 11, 13, 11), ms(2026, 11, 13, 13, 30), 'trưa nay'))
        g = self.gio('tối nay thế nào')               # mới 14:00: chưa tới tối
        self.assertTrue(g['tuong_lai'])

    def test_luc_nay_va_lui_lai(self):
        g = self.gio('lúc nãy bàn 3 có gì')
        self.assertEqual((g['loai'], g['tu'], g['den']), ('gan', T - 600_000, T))
        g = self.gio('cho xem 5 phút trước')
        self.assertEqual((g['loai'], g['luc']), ('truoc', T - 300_000))
        self.assertEqual(self.gio('nửa tiếng trước có gì')['luc'], T - 1800_000)
        self.assertEqual(self.gio('2 giờ trước')['luc'], T - 7200_000)

    def test_ngay_khac(self):
        g = self.gio('hôm qua lúc 12:30 có gì')
        self.assertEqual((g['day'], g['luc'], g['ten']), ('2026-11-12', ms(2026, 11, 12, 12, 30), '12:30 hôm qua'))
        self.assertTrue(g['ro_ngay'])
        self.assertEqual(xl.doc_cac_ngay(tl.bo_dau('hôm qua so với hôm nay'), T), ['2026-11-12', '2026-11-13'])
        self.assertEqual(xl.doc_cac_ngay(tl.bo_dau('thứ hai thế nào'), T), ['2026-11-09'])
        self.assertEqual(xl.doc_cac_ngay(tl.bo_dau('thứ sáu tuần trước'), T), ['2026-11-06'])
        self.assertEqual(xl.doc_cac_ngay(tl.bo_dau('chủ nhật đông không'), T), ['2026-11-08'])
        self.assertEqual(xl.doc_cac_ngay(tl.bo_dau('ngày 10/11 ra sao'), T), ['2026-11-10'])
        self.assertEqual(xl.doc_cac_ngay(tl.bo_dau('2026-11-01'), T), ['2026-11-01'])
        self.assertEqual(xl.doc_cac_ngay(tl.bo_dau('ngày 28 thế nào'), T), ['2026-10-28'])
        self.assertEqual(xl.doc_cac_ngay(tl.bo_dau('tối qua đông không'), T), ['2026-11-12'])
        self.assertEqual(xl.doc_cac_ngay(tl.bo_dau('bàn 3 gọi 2 lần'), T), [])

    def test_gio_chua_toi(self):
        self.assertTrue(self.gio('cho xem lúc 18:00')['tuong_lai'])
        self.assertFalse(self.gio('cho xem lúc 14:00')['tuong_lai'])

    def test_qua_nua_dem(self):
        t = ms(2026, 11, 14, 0, 20)                  # 00:20, quán còn mở
        g = self.gio('cho xem lúc 23:50', t)
        self.assertEqual((g['day'], g['luc'], g['tuong_lai']), ('2026-11-13', ms(2026, 11, 13, 23, 50), False))
        self.assertEqual(self.gio('10 phút trước', t)['day'], '2026-11-13')     # trước 4 giờ sáng vẫn là ngày 13 của quán
        self.assertEqual(self.gio('30 phút trước', t)['day'], '2026-11-13')
        g = self.gio('cho xem lúc 08:00', t)             # 8 giờ sáng của chính ngày làm việc này, đã qua
        self.assertEqual((g['luc'], g['tuong_lai']), (ms(2026, 11, 13, 8, 0), False))
        self.assertTrue(self.gio('cho xem lúc 02:00', t)['tuong_lai'])


class Base(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # đồng hồ chạy từ 12 giờ trưa hôm nay: chạy test lúc vừa qua nửa đêm, việc "vài phút trước" không rơi sang hôm qua
        that = time.time
        lech = datetime.now(VN).replace(hour=12, minute=0, second=0, microsecond=0).timestamp() - that()
        p = mock.patch('time.time', side_effect=lambda: that() + lech)
        p.start()
        self.addCleanup(p.stop)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.hub = Hub(self.dir, NoGemini())
        self.clips = Clips(self.hub, self.dir)
        self.tro_ly = tl.TroLy(self.hub, NoGemini())
        self.tro_ly.clips = self.clips

    def camera_chay(self, cid='cam1'):
        self.hub.edge_frame(cid, 'jpg', b'\xff\xd8')

    def viec(self, table='B1', kind='goi_phuc_vu', truoc_s=0, eid=None, ack=None, sau_s=10):
        """Một việc tạo cách đây `truoc_s` giây; `ack` là nhân viên nhận sau `sau_s` giây."""
        aid = self.hub.edge_event(ev(eid, kind, table))
        a = self.hub.alerts[aid]
        a['created_at'] -= truoc_s * 1000
        if ack:
            self.hub.staff_online(ack, +1)
            self.hub.ack(aid, ack)
            a['acked_at'] = a['created_at'] + sau_s * 1000
        return aid

    async def hoi(self, q, session=None):
        r = await self.tro_ly.hoi(q, session)
        self.assertEqual(set(r), {'answer', 'blocks', 'suggestions', 'refs', 'engine', 'model', 'ms'})
        self.assertTrue(r['answer'])
        self.assertNotRegex(r['answer'], r'[*#`_]|\d+\s*giây|\d+ ?s\b')     # không markdown, không số giây
        for b in r['blocks']:
            self.assertTrue(b['items'] if 'items' in b else b.get('rows') or b.get('points'), b)
        return r, {b['type']: b for b in r['blocks']}

    async def may_camera_tra(self, clip_id, loi=None):
        """Đóng giả máy camera trả lời yêu cầu clip: gửi clip, hoặc báo lỗi."""
        rec = self.clips.get(clip_id)
        if loi is None:
            self.clips.add_job_clip(rec['job'], rec['t_from'], rec['t_to'], mp4())
        else:
            self.hub.job_result(rec['job'], dict(error=loi))
        for _ in range(3):
            await asyncio.sleep(0)
        return self.clips.view(rec)


class Video(Base):
    async def test_viec_da_co_clip_thi_phat_ngay(self):
        aid = self.viec('B2', eid='cam1:1', ack='lan')
        self.clips.add_event_clip('cam1:1', 'cam1', now_ms() - 8000, now_ms(), mp4())
        r, by = await self.hoi('Cho xem video khúc bàn B2 gọi')
        self.assertEqual(r['engine'], 'rules')
        it = by['video']['items'][0]
        self.assertEqual((it['alert_id'], it['table'], it['src']), (aid, 'B2', f'/api/alerts/{aid}/clip.mp4'))
        self.assertIsNone(it['clip_id'])
        self.assertIsNone(it['error'])
        self.assertEqual(it['label'], 'Bàn B2 gọi phục vụ')
        self.assertIn('Lan nhận nhanh', it['note'])
        self.assertIn('Video ở ngay bên dưới', r['answer'])
        self.assertEqual(by['events']['items'][0]['clip_url'], f'/api/alerts/{aid}/clip.mp4')
        self.assertEqual(r['refs'], [dict(alert_id=aid, t=it['t'], table='B2')])

    async def test_viec_chua_co_clip_thi_xin_may_camera_roi_cho(self):
        self.camera_chay()
        aid = self.viec('B3', truoc_s=300, ack='minh', sau_s=90)
        self.viec('B1', truoc_s=200, ack='lan', sau_s=5)
        r, by = await self.hoi('Cho xem lại lần khách chờ lâu nhất')
        it = by['video']['items'][0]
        self.assertEqual(it['alert_id'], aid)
        self.assertIsNone(it['src'])
        self.assertTrue(r['answer'].startswith('Bàn B3 chờ lâu nhất, lúc'), r['answer'])
        self.assertIn('phục vụ chậm', r['answer'])
        a = self.hub.alerts[aid]
        self.assertEqual((it['t_from'], it['t_to']), (a['created_at'] - 8000, a['created_at'] + 12000))
        self.assertEqual(self.clips.view(self.clips.get(it['clip_id']))['status'], 'pending')
        self.assertEqual(self.hub.take_jobs('cam1')[0]['kind'], 'clip')
        # clip tới sau khi câu trả lời đã hiện: màn hình hỏi lại GET /api/clips/{id} là thấy
        v = await self.may_camera_tra(it['clip_id'])
        self.assertEqual((v['status'], v['url']), ('ready', f"/api/clips/{it['clip_id']}.mp4"))

    async def test_clip_dang_cho_roi_hong(self):
        self.camera_chay()
        self.viec('B3', truoc_s=300, ack='minh', sau_s=90)
        r, by = await self.hoi('cho xem video lần khách chờ lâu nhất')
        v = await self.may_camera_tra(by['video']['items'][0]['clip_id'], 'chưa ghi hình lúc đó')
        self.assertEqual(v['status'], 'failed')
        self.assertEqual(xl.loi_de_hieu(v['error']), 'Máy camera chưa ghi hình lúc đó.')
        self.assertEqual(xl.loi_de_hieu('Máy camera không trả lời.'), 'Máy camera không trả lời nên chưa lấy được video.')
        self.assertEqual(xl.loi_de_hieu('máy camera đang không ghi hình (chạy thêm --ghi-hinh)'),
                         'Máy camera chưa ghi hình lúc đó.')

    async def test_may_camera_tat(self):
        aid = self.viec('B3', truoc_s=300, ack='minh', sau_s=90)
        r, by = await self.hoi('cho xem video bàn B3')
        it = by['video']['items'][0]
        self.assertEqual(it['error'], 'Máy camera đang tắt nên chưa lấy được video.')
        self.assertIsNone(it['clip_id'])
        self.assertIn('Máy camera đang tắt nên chưa lấy được video', r['answer'])
        self.assertEqual(by['events']['items'][0]['alert_id'], aid)      # vẫn còn ảnh camera để xem

    async def test_chua_bat_luu_video_thi_con_anh(self):
        self.tro_ly.clips = None
        self.viec('B3', truoc_s=300, ack='minh', sau_s=90)
        gio = clock(now_ms() - 300_000)[:5]
        r, by = await self.hoi(f'cho xem video lúc {gio}')
        self.assertNotIn('video', by)
        self.assertIn('events', by)
        self.assertIn('chỉ có ảnh camera', r['answer'])

    async def test_gio_khong_co_su_kien_van_xem_duoc_hinh(self):
        self.camera_chay()
        gio = clock(now_ms() - 900_000)[:5]
        r, by = await self.hoi(f'lúc {gio} bàn 3 có gì')          # chưa biết bàn 3
        self.assertIn('Chưa thấy bàn 3', r['answer'])
        self.assertEqual(r['blocks'], [])
        r, by = await self.hoi(f'cho xem lúc {gio}')
        self.assertIn('không ghi sự kiện nào', r['answer'])
        it = by['video']['items'][0]
        self.assertTrue(it['clip_id'])
        self.assertIsNone(it['alert_id'])
        self.assertEqual(it['t_to'] - it['t_from'], 30_000)
        self.assertEqual(it['label'], 'Toàn cảnh camera')

    async def test_gio_chua_toi(self):
        self.camera_chay()
        t = now_ms()
        if clock(t)[:2] >= '22':
            self.skipTest('gần nửa đêm')
        r, by = await self.hoi(f'cho xem video lúc {int(clock(t)[:2]) + 2}:00')
        self.assertIn('Chưa tới', r['answer'])
        self.assertEqual(r['blocks'], [])

    async def test_ban_la_va_cach_goi_ban(self):
        self.camera_chay()
        self.viec('B3', truoc_s=120, ack='lan')
        r, _ = await self.hoi('cho xem video bàn Z9')
        self.assertIn('Chưa thấy bàn Z9', r['answer'])
        self.assertEqual(r['blocks'], [])
        for cau in ('cho xem video bàn 3', 'cho xem video B3', 'cho xem video b3', 'xem lại bàn b3'):
            r, by = await self.hoi(cau)
            self.assertEqual(by['video']['items'][0]['table'], 'B3', cau)

    async def test_nhieu_su_kien_thi_gioi_han(self):
        self.camera_chay()
        for i in range(10):
            self.viec(f'B{i + 1}', truoc_s=600 - i * 40, ack='lan')
        r, by = await self.hoi('cho xem lại những lần khách gọi')
        items = by['video']['items']
        self.assertEqual(len(items), xl.MAX_VIDEO)
        self.assertEqual([it['t'] for it in items], sorted((it['t'] for it in items), reverse=True))   # mới trước
        self.assertEqual(sum(1 for it in items if it['clip_id']), xl.XIN_NGAY)      # chỉ xin sẵn hai clip đầu
        self.assertEqual(len(self.clips.req), xl.XIN_NGAY)
        for it in items[xl.XIN_NGAY:]:      # clip còn lại màn hình xin khi bấm: đủ camera và khoảng giờ
            self.assertEqual((it['camera'], it['error'], it['src']), ('cam1', None, None))
            self.assertEqual(it['t_to'] - it['t_from'], 20_000)

    async def test_viec_vua_xay_ra_thi_cho_clip_su_kien(self):
        self.camera_chay()
        aid = self.viec('B1', eid='cam1:9')
        r, by = await self.hoi('cho xem video bàn B1')
        it = by['video']['items'][0]
        self.assertEqual((it['alert_id'], it['src'], it['clip_id'], it['error']), (aid, None, None, None))
        self.assertEqual(self.clips.req, {})        # không xin thêm: clip của việc sắp tới nơi

    async def test_hai_cau_lien_tiep_cung_phien(self):
        self.camera_chay()
        self.viec('B3', truoc_s=300, ack='minh', sau_s=90)
        r1, by1 = await self.hoi('cho xem lại lần khách chờ lâu nhất', 'phien1')
        r2, by2 = await self.hoi('cho xem lại lần khách chờ lâu nhất', 'phien1')
        self.assertNotEqual(by1['video']['items'][0]['clip_id'], by2['video']['items'][0]['clip_id'])
        self.assertIsNot(r1['blocks'], r2['blocks'])
        r3, by3 = await self.hoi('Tóm tắt ca hôm nay', 'phien1')
        self.assertNotIn('video', by3)

    async def test_adk_loi_thi_van_co_video(self):
        self.camera_chay()
        self.viec('B3', truoc_s=300, ack='minh', sau_s=90)
        t = tl.TroLy(self.hub, GeminiGia())
        t.clips = self.clips
        t._adk = (None, None, None)

        async def hong(question, sid):
            raise TimeoutError('quá giờ')
        t._hoi_adk = hong
        r = await t.hoi('cho xem lại lần khách chờ lâu nhất')
        self.assertEqual(r['engine'], 'rules')
        self.assertEqual(r['blocks'][0]['type'], 'video')
        self.assertTrue(r['blocks'][0]['items'][0]['clip_id'])


class KeLai(Base):
    def bua_an(self, ban='B2', truoc_s=3000, hub=None):
        """Ghi một bữa ăn của một bàn vào dòng thời gian, bắt đầu cách đây `truoc_s` giây."""
        hub = hub or self.hub
        t0 = now_ms() / 1000 - truoc_s
        tlx = hub.timeline
        tlx.add('stage', ts=t0, table=ban, camera='cam1', stage='seated', prev=None, via='table')
        tlx.add('nudge', ts=t0 + 200, table=ban, camera='cam1', nudge='greet', stage='seated', text='x')
        tlx.add('stage', ts=t0 + 240, table=ban, camera='cam1', stage='greeted', prev='seated', via='staff', prev_s=240)
        tlx.add('stage', ts=t0 + 700, table=ban, camera='cam1', stage='served', prev='greeted', via='ai', prev_s=460)
        tlx.add('alert_created', ts=t0 + 900, table=ban, camera='cam1', alert_id='a7', alert_kind='call', status='open')
        tlx.add('alert_acked', ts=t0 + 915, table=ban, camera='cam1', alert_id='a7', staff='lan', wait_s=15.0)
        tlx.add('alert_done', ts=t0 + 930, table=ban, camera='cam1', alert_id='a7', staff='lan', wait_s=15.0)
        tlx.add('stage', ts=t0 + 1500, table=ban, camera='cam1', stage='finished', prev='served', via='ai')
        tlx.add('stage', ts=t0 + 1800, table=ban, camera='cam1', stage='left', prev='finished', via='table')
        tlx.add('alert_created', ts=t0 + 1810, table=ban, camera='cam1', alert_id='a8', alert_kind='needs_clearing',
                status='open')
        tlx.add('alert_done', ts=t0 + 1900, table=ban, camera='cam1', alert_id='a8', staff='minh', wait_s=40.0)
        return t0

    async def test_ke_lai_mot_ban(self):
        self.camera_chay()
        t0 = self.bua_an('B2')
        r, by = await self.hoi('Kể lại bàn B2 từ lúc khách vào')
        self.assertEqual(r['engine'], 'rules')
        viec_ = [x['text'] for x in by['timeline']['items']]
        self.assertEqual(viec_, ['Khách vào bàn', 'Ngồi khá lâu mà chưa ai ra tiếp',
                                 'Nhân viên ra tiếp, sau khi khách ngồi khá lâu', 'Món đã lên',
                                 'Khách gọi phục vụ, Lan nhận nhanh', 'Khách ăn xong', 'Khách rời bàn',
                                 'Bàn cần dọn, Minh nhận hơi chậm', 'Bàn đã dọn xong'])
        self.assertEqual([x['tone'] for x in by['timeline']['items']],
                         [None, 'warn', 'warn', 'good', 'good', None, None, 'warn', 'good'])
        self.assertEqual(by['timeline']['items'][0]['t'], int(t0 * 1000))
        gio = clock(int(t0 * 1000))[:5]
        self.assertIn(f'khách vào lúc {gio}', r['answer'])
        self.assertIn('món lên lúc', r['answer'])
        self.assertIn('khách gọi phục vụ 1 lần', r['answer'])
        # mỗi dòng mở được video; khối video kèm các lúc chính
        self.assertTrue(all(x['video'] and x['video']['camera'] == 'cam1' for x in by['timeline']['items']))
        self.assertEqual([it['label'] for it in by['video']['items']], ['Bàn B2 gọi phục vụ', 'Bàn B2 cần dọn'])
        self.assertTrue(all(it['clip_id'] for it in by['video']['items']))

    async def test_ban_chua_co_gi(self):
        self.hub.edge_tables('cam1', [dict(id='B4', state='trong', people=0)])
        r, by = await self.hoi('kể lại bàn B4')
        self.assertIn('Bàn B4 hôm nay chưa có gì được ghi lại', r['answer'])
        self.assertEqual(r['blocks'], [])
        r, _ = await self.hoi('kể lại bàn Z9 từ lúc khách vào')
        self.assertIn('Chưa thấy bàn Z9', r['answer'])

    async def test_may_chu_khoi_dong_lai_van_tra_loi_tu_lich_su(self):
        t0 = self.bua_an('B2', truoc_s=3000)
        self.hub.timeline.close()
        hub2 = Hub(self.dir, NoGemini())           # việc trong RAM mất hết, dòng thời gian còn
        self.assertEqual(hub2.alerts, {})
        clips2 = Clips(hub2, self.dir)
        hub2.edge_frame('cam1', 'jpg', b'\xff\xd8')
        self.hub, self.clips = hub2, clips2
        self.tro_ly = tl.TroLy(hub2, NoGemini())
        self.tro_ly.clips = clips2
        r, by = await self.hoi('Kể lại bàn B2 từ lúc khách vào')
        self.assertEqual(len(by['timeline']['items']), 9)
        self.assertTrue(all(x['alert_id'] is None for x in by['timeline']['items']))
        # xem video theo giờ: việc lấy từ lịch sử, clip xin máy camera theo khoảng thời gian
        gio = clock(int((t0 + 900) * 1000))[:5]
        r, by = await self.hoi(f'cho xem lúc {gio} bàn B2')
        it = by['video']['items'][0]
        self.assertEqual((it['label'], it['alert_id'], it['table']), ('Bàn B2 gọi phục vụ', None, 'B2'))
        self.assertEqual(it['t'], int((t0 + 900) * 1000))
        self.assertTrue(it['clip_id'])
        self.assertNotIn('events', by)             # không còn ảnh trong RAM
        self.assertIn('Lan nhận nhanh', r['answer'])
        r, by = await self.hoi('cho xem lại lần khách chờ lâu nhất')
        self.assertEqual(by['video']['items'][0]['label'], 'Bàn B2 cần dọn')
        self.assertIn('phục vụ hơi chậm', r['answer'])
        r, by = await self.hoi('Tóm tắt ca hôm nay')
        self.assertIn('Trước đó trong ngày', r['answer'])
        self.assertIn('1 lần khách gọi', r['answer'])
        self.assertIn('stats', by)
        # mã việc bắt đầu lại từ a1: việc mới không bị lẫn với việc cũ cùng mã
        for i in range(7):
            aid = self.viec(f'C{i}', truoc_s=5)
        self.assertEqual(aid, 'a7')
        r, by = await self.hoi(f'cho xem lúc {gio} bàn B2')
        self.assertIsNone(by['video']['items'][0]['alert_id'])


class BanLucNay(Base):
    async def test_ban_dang_cho_gi(self):
        self.hub.edge_tables('cam1', [dict(id='B1', state='co_khach', people=2), dict(id='B2', state='co_khach', people=3),
                                      dict(id='B3', state='trong', people=0)])
        self.hub.stages.st['B2']['nudge'] = 'greet'
        self.hub.stages._sync('B2')
        r, by = await self.hoi('Bàn nào đang chờ lâu?')
        self.assertIn('Đang có 2 bàn có khách', r['answer'])
        self.assertIn('bàn B2 ngồi khá lâu mà chưa ai ra tiếp', r['answer'])
        self.assertEqual(by['table']['rows'][0][0], 'Bàn B2')            # bàn cần để ý đứng trước
        self.assertEqual(by['table']['rows'][0][3], 'Chưa ai ra tiếp')
        self.assertEqual(by['table']['rows'][1][:2], ['Bàn B1', 'Mới ngồi, chờ nhân viên ra tiếp'])
        r, by = await self.hoi('bàn B2 đang chờ món hay sao?')
        self.assertIn('Bàn B2 đang có khách: mới ngồi', r['answer'])
        r, by = await self.hoi('bàn B3 có món chưa')
        self.assertIn('Bàn B3 lúc này đang trống', r['answer'])

    async def test_khong_co_ban_nao(self):
        r, by = await self.hoi('Bàn nào đang chờ món?')
        self.assertIn('Camera chưa gửi trạng thái bàn', r['answer'])
        self.assertEqual(r['blocks'], [])

    async def test_viec_chua_ai_nhan_di_kem(self):
        self.hub.edge_tables('cam1', [dict(id='B1', state='co_khach', people=2)])
        aid = self.viec('B1', truoc_s=100)
        r, by = await self.hoi('bàn nào đang chờ?')
        self.assertIn('bàn B1 gọi phục vụ, chờ quá lâu', r['answer'])
        self.assertEqual(by['events']['items'][0]['alert_id'], aid)


class NgayKhac(Base):
    def ngay(self, lui, viec_):
        """Ghi việc vào một ngày trước: viec_ là [(giờ, bàn, loại, giây chờ hoặc None là không ai tới)]."""
        d0 = xl.dau_ngay_s(day_of(now_ms() / 1000 - lui * 86400)) - xl.DOI_NGAY_H * 3600    # 00:00 của ngày đó
        for i, (h, ban, kind, w) in enumerate(viec_):
            ts, aid = d0 + h * 3600 + i, f'a{i + 1}'
            self.hub.timeline.add('alert_created', ts=ts, table=ban, camera='cam1', alert_id=aid, alert_kind=kind)
            if w is None:
                self.hub.timeline.add('alert_auto_closed', ts=ts + 200, table=ban, camera='cam1', alert_id=aid)
            else:
                self.hub.timeline.add('alert_acked', ts=ts + w, table=ban, camera='cam1', alert_id=aid, staff='lan',
                                      wait_s=w)
                self.hub.timeline.add('alert_done', ts=ts + w + 30, table=ban, camera='cam1', alert_id=aid, wait_s=w)

    async def test_hom_qua(self):
        self.ngay(1, [(11, 'B1', 'call', 10), (12, 'B2', 'call', 80), (12, 'B2', 'needs_clearing', 20),
                      (12, 'B3', 'new_guest', None), (13, 'B1', 'call', 12)])
        r, by = await self.hoi('Hôm qua thế nào?')
        self.assertTrue(r['answer'].startswith('Hôm qua có 3 lần khách gọi, 1 lần bàn cần dọn và 1 lượt khách mới.'))
        self.assertIn('3 việc nhanh, 1 việc chậm, 1 việc không ai tới', r['answer'])
        self.assertIn('Bận nhất khoảng 12:00', r['answer'])
        self.assertEqual([p['value'] for p in by['chart']['points']], [1, 3, 1])
        self.assertEqual(by['stats']['items'][0]['value'], '3')
        r, by = await self.hoi('hôm qua bàn B2 thế nào')
        self.assertIn('Hôm qua bàn B2: gọi phục vụ 1 lần, cần dọn 1 lần', r['answer'])
        r, by = await self.hoi('trưa hôm qua lúc 12:00 có gì')
        self.assertIn('Quanh 12:00 hôm qua có 3 sự kiện', r['answer'])

    async def test_ngay_khong_co_du_lieu(self):
        r, by = await self.hoi('hôm kia thế nào')
        self.assertIn('Hôm kia hệ thống không ghi được việc nào', r['answer'])
        self.assertEqual(r['blocks'], [])
        r, by = await self.hoi('So sánh hôm qua với hôm kia')
        self.assertIn('đều không ghi được việc nào', r['answer'])

    async def test_so_sanh_voi_hom_nay(self):
        self.ngay(1, [(11, 'B1', 'call', 10), (12, 'B2', 'call', 80)])
        self.viec('B1', truoc_s=200, ack='lan', sau_s=5)
        r, by = await self.hoi('Hôm qua so với hôm nay thế nào?')
        self.assertIn('Hôm qua có 2 việc, hôm nay tới giờ có 1 việc', r['answer'])
        self.assertEqual(by['table']['columns'], ['Chỉ số', 'Hôm qua', 'Hôm nay'])
        self.assertEqual(by['table']['rows'][0], ['Khách gọi phục vụ', '2', '1'])
        r, by = await self.hoi('so sánh hôm kia với hôm nay')
        self.assertIn('Hôm kia hệ thống không ghi được việc nào nên chưa so được', r['answer'])

    async def test_video_ngay_qua_cu_thi_noi_ro(self):
        self.camera_chay()
        self.ngay(3, [(12, 'B1', 'call', 10)])
        ngay = datetime.fromtimestamp(now_ms() / 1000 - 3 * 86400, VN)
        r, by = await self.hoi(f'cho xem video lúc 12:00 ngày {ngay.day}/{ngay.month}')
        self.assertEqual(by['video']['items'][0]['error'],
                         'Máy camera chỉ giữ video khoảng một ngày, nên không còn hình lúc đó.')
        self.assertEqual(self.clips.req, {})


class CongCu(Base):
    """Công cụ của tác tử ADK, gọi thẳng (không cần mạng)."""

    def setUp(self):
        super().setUp()
        self.box = dict(blocks=[])
        self.tools = {f.__name__: f for f in self.tro_ly.tools(self.box)}

    async def test_xem_video(self):
        self.camera_chay()
        self.tro_ly._loop = asyncio.get_running_loop()
        a1 = self.viec('B3', truoc_s=300, ack='minh', sau_s=90)
        a2 = self.viec('B1', truoc_s=200, ack='lan', sau_s=5)
        kq = self.tools['xem_video'](ma_su_kien=f'{a2}, {a1}', tieu_de='Hai lần gọi')
        self.assertTrue(kq['co_video'])
        self.assertEqual([c['ban'] for c in kq['clip']], ['B1', 'B3'])
        b = self.box['blocks'][0]
        self.assertEqual((b['type'], b['title']), ('video', 'Hai lần gọi'))
        self.assertTrue(all(it['clip_id'] for it in b['items']))
        kq = self.tools['xem_video'](cho_lau_nhat=True)
        self.assertEqual(self.box['blocks'][1]['items'][0]['alert_id'], a1)
        kq = self.tools['xem_video'](ban='b3', gio=clock(self.hub.alerts[a1]['created_at'])[:5])
        self.assertEqual(self.box['blocks'][2]['items'][0]['alert_id'], a1)
        self.assertIn('Bàn B3 gọi phục vụ', kq['tom_tat'])
        self.assertIn('Hệ thống không theo dõi bàn', self.tools['xem_video'](ban='Z9')['ket_qua'])
        self.assertEqual(len(self.box['blocks']), 3)

    async def test_xem_video_khi_camera_tat(self):
        self.viec('B3', truoc_s=300, ack='minh', sau_s=90)
        kq = self.tools['xem_video'](ban='B3')
        self.assertFalse(kq['co_video'])
        self.assertEqual(kq['clip'][0]['ly_do_khong_co_video'], 'Máy camera đang tắt nên chưa lấy được video.')

    async def test_dong_thoi_gian_va_ban(self):
        KeLai.bua_an(self, 'B2')
        kq = self.tools['dong_thoi_gian'](ban='B2')
        self.assertEqual(kq['cac_buoc'][0]['viec'], 'Khách vào bàn')
        self.assertEqual(len(kq['cac_buoc']), 9)
        self.assertEqual(self.box['blocks'][0]['type'], 'timeline')
        self.hub.edge_tables('cam1', [dict(id='B1', state='co_khach', people=2)])
        kq = self.tools['ban_dang_the_nao']()
        self.assertEqual(kq['ban'][0]['ban'], 'B1')
        self.assertEqual(kq['ban'][0]['bua_an'], 'Mới ngồi, chờ nhân viên ra tiếp')
        n = len(self.box['blocks'])
        self.tools['ban_dang_the_nao'](hien=True)
        self.assertEqual(self.box['blocks'][n]['type'], 'table')

    async def test_so_sanh_ngay(self):
        NgayKhac.ngay(self, 1, [(11, 'B1', 'call', 10), (12, 'B2', 'call', 80)])
        kq = self.tools['so_sanh_ngay']('hôm qua')
        self.assertEqual((kq['ngay'][0]['goi_phuc_vu'], kq['ngay'][0]['gio_ban_nhat']), (2, '11:00'))
        self.assertEqual([b['type'] for b in self.box['blocks']], ['stats', 'chart'])
        kq = self.tools['so_sanh_ngay']('hôm qua', 'hôm nay')
        self.assertEqual([x['co_du_lieu'] for x in kq['ngay']], [True, False])
        self.assertIn('Không hiểu ngày nào', self.tools['so_sanh_ngay']('bao giờ')['ket_qua'])


if __name__ == '__main__':
    unittest.main()
