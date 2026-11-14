"""Phòng chat, ảnh thanh toán đọc bằng Gemini (giả), đối chiếu với lượt khách.

Chạy (trong easy-fnb):  python -m unittest server.tests.test_chat -v
"""
import asyncio
import tempfile
import time
import unittest
from datetime import datetime
from unittest import mock
from pathlib import Path

from server import doi_chieu
from server.chat import Phong, khoa_ban
from server.hub import Hub
from server.timeline import VN, day_of

JPEG = b'\xff\xd8' + b'0' * 200


class FakeLlm:
    ten = 'Gemini'
    enabled = True
    model = 'gia-lap'

    def __init__(self, script):
        self.script = list(script)
        self.calls = 0

    async def json(self, parts, schema, image=False):
        self.calls += 1
        r = self.script.pop(0)
        if r == 'err':
            raise RuntimeError('lỗi mạng')
        if r == 'hang':
            await asyncio.sleep(5)
        return r


class FakeTroLy:
    def __init__(self):
        self.asked = []

    async def hoi(self, q, session=None, che_do='chu'):
        self.asked.append((q, session, che_do))
        return dict(answer='Bàn 3 có khách từ 13:41.')


def ocr(**kw):
    r = dict(loai='chuyen_khoan', so_tien=245000, gio='14:32', ban='', ngan_hang='Vietcombank',
             nguoi_chuyen='NGUYEN VAN A', noi_dung='BAN 3', ma_giao_dich='FT123', so_hoa_don='', mon=[], khong_chac=[])
    r.update(kw)
    return r


class Base(unittest.IsolatedAsyncioTestCase):
    def make(self, script=(), tro_ly=None, timeout=1.0):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.llm = FakeLlm(script)
        self.hub = Hub(Path(self.tmp.name), self.llm)
        self.addCleanup(self.hub.close)
        self.hub.staff = [dict(id='lan', name='Lan', role='serve'), dict(id='minh', name='Minh', role='cashier')]
        self.hub.zones = {'cam1': dict(camera='cam1', tables=[dict(id='3'), dict(id='9'), dict(id='VIP 2')])}
        self.p = Phong(self.hub, self.llm, tro_ly, ocr_timeout_s=timeout)
        self.q = asyncio.Queue()
        self.p.subs.add(self.q)
        return self.p


class TestChat(Base):
    async def test_post_and_list(self):
        p = self.make()
        m1 = p.post('lan', 'Bàn 5 xin thêm đá')
        m2 = p.post('chu', '@Minh mang đá ra', to=['minh'])
        self.assertEqual([m['id'] for m in p.messages()], [m1['id'], m2['id']])
        self.assertEqual([m['id'] for m in p.messages(since=m1['id'])], [m2['id']])
        self.assertEqual(m2['to'], ['minh'])
        self.assertEqual(self.q.get_nowait()[0], 'message')

    async def test_rejects_bad_sender_and_empty(self):
        p = self.make()
        with self.assertRaises(ValueError):
            p.post('ai-do', 'xin chào')
        with self.assertRaises(ValueError):
            p.post('lan', '   ')
        with self.assertRaises(ValueError):
            p.post('lan', 'x' * 1001)

    async def test_ai_answers_only_when_called(self):
        tl = FakeTroLy()
        p = self.make(tro_ly=tl)
        p.post('lan', 'không gọi ai cả, ai cũng bận')
        await asyncio.sleep(0.05)
        self.assertEqual(tl.asked, [])
        m = p.post('lan', '@AI bàn 3 vào lúc nào?')
        await asyncio.gather(*p.tasks)
        last = p.messages()[-1]
        self.assertEqual(last['sender'], 'ai')
        self.assertEqual(last['reply_to'], m['id'])
        self.assertIn('bàn 3 vào lúc nào', tl.asked[0][0])
        self.assertTrue(tl.asked[0][1].startswith('phong-'))
        self.assertEqual(tl.asked[0][2], 'phong')         # phòng chat không có công cụ cài đặt
        p.post('chu', 'AI ơi tóm tắt ca')
        await asyncio.gather(*p.tasks)
        self.assertEqual(len(tl.asked), 2)
        for cau in ('@Tam bàn nào chờ lâu?', 'Tam ơi tóm tắt ca', '@tam có ai rảnh không'):
            p.post('lan', cau)
            await asyncio.gather(*p.tasks)
        self.assertEqual(len(tl.asked), 5)
        self.assertNotIn('@Tam', tl.asked[2][0].split(']')[-1])
        p.post('lan', 'tam giác bánh để ở quầy, @Tâm lấy giúp')   # chữ "tam" giữa câu, @Tâm là nhân viên: không gọi
        p.post('lan', '@Mâm ơi')                        # tên cũ không còn gọi
        await asyncio.gather(*p.tasks)
        self.assertEqual(len(tl.asked), 5)


class TestRoomTools(Base):
    async def test_room_mode_has_no_setup_or_display_tools(self):
        from server.tro_ly import CONG_CU_CHI_CHU, TroLy
        self.make()
        tl = TroLy(self.hub, self.llm)
        ten = lambda ds: {f.__name__ for f in ds}  # noqa: E731
        chu, phong = ten(tl.tools(dict(blocks=[]))), ten(tl.tools(dict(blocks=[]), 'phong'))
        self.assertTrue(CONG_CU_CHI_CHU <= chu)
        self.assertFalse(CONG_CU_CHI_CHU & phong)
        self.assertFalse({n for n in phong if n.startswith('hien_')})
        self.assertIn('so_lieu_ca', phong)


class TestScan(Base):
    async def test_transfer_read_confirm_send(self):
        p = self.make([ocr()])
        r = await p.scan('lan', JPEG)
        self.assertEqual(r['engine'], 'gemini')
        f = r['fields']
        self.assertEqual((f['type'], f['amount'], f['paid_at'], f['bank'], f['memo']),
                         ('chuyen_khoan', 245000, '14:32', 'Vietcombank', 'BAN 3'))
        self.assertEqual(r['unsure'], [])
        self.assertEqual(self.p.payments(day_of(time.time())), [])      # chưa xác nhận thì chưa lưu
        m = p.send_scan(r['scan_id'], 'lan', dict(table='3'))
        self.assertEqual(m['kind'], 'payment')
        self.assertEqual(m['payment']['amount'], 245000)
        self.assertEqual(m['payment']['table'], '3')
        self.assertEqual(m['payment']['confirmed_by'], 'lan')
        full = p.payment(m['payment_id'], full=True)
        self.assertEqual([(e['field'], e['old'], e['new']) for e in full['edits']], [('table', None, '3')])
        self.assertEqual(full['ocr']['raw']['so_tien'], 245000)
        with self.assertRaises(KeyError):            # gửi hai lần không được
            p.send_scan(r['scan_id'], 'lan')
        self.assertTrue(Path(self.tmp.name, 'chat', m['image']).exists())

    async def test_table_from_memo_and_names(self):
        p = self.make([ocr(ban='B3'), ocr(ban='vip2'), ocr(ban='12')])
        self.assertEqual((await p.scan('lan', JPEG))['fields']['table'], '3')
        self.assertEqual((await p.scan('lan', JPEG))['fields']['table'], 'VIP 2')
        r = await p.scan('lan', JPEG)
        self.assertIsNone(r['fields']['table'])
        self.assertIn('table', r['unsure'])
        self.assertEqual(khoa_ban('Bàn 03'), '3')

    async def test_receipt_total_mismatch_is_unsure(self):
        p = self.make([ocr(loai='hoa_don', so_tien=100000, mon=[dict(ten='Cà phê', sl=2, gia=30000)])])
        r = await p.scan('lan', JPEG)
        self.assertIn('amount', r['unsure'])
        self.assertTrue(any('Tổng các món' in w for w in r['warnings']))

    async def test_gemini_unsure_fields_and_missing_amount(self):
        p = self.make([ocr(khong_chac=['gio']), ocr(so_tien=0)])
        self.assertEqual((await p.scan('lan', JPEG))['unsure'], ['paid_at'])
        r = await p.scan('lan', JPEG)
        self.assertIsNone(r['fields']['amount'])
        self.assertIn('amount', r['unsure'])
        with self.assertRaises(ValueError):          # không có số tiền thì không gửi được
            p.send_scan(r['scan_id'], 'lan')
        m = p.send_scan(r['scan_id'], 'lan', dict(amount='120.000'))    # sửa tay rồi gửi lại được
        self.assertEqual(m['payment']['amount'], 120000)

    async def test_error_and_timeout_fall_back_to_manual(self):
        p = self.make(['err', 'hang'], timeout=0.05)
        r1 = await p.scan('lan', JPEG)
        r2 = await p.scan('lan', JPEG)
        self.assertEqual((r1['engine'], r2['engine']), ('manual', 'manual'))
        self.assertNotIn('Gemini', r2['error'])
        self.assertIsNone(r2['fields']['amount'])

    async def test_breaker_stops_calling(self):
        p = self.make(['err', 'err', 'err', ocr()])
        for _ in range(4):
            await p.scan('lan', JPEG)
        self.assertEqual(self.llm.calls, 3)

    async def test_duplicate_warning(self):
        p = self.make([ocr(), ocr()])
        r = await p.scan('lan', JPEG)
        p.send_scan(r['scan_id'], 'lan')
        r2 = await p.scan('minh', JPEG)
        self.assertTrue(any('đã gửi rồi' in w for w in r2['warnings']))

    async def test_not_a_payment_sends_photo(self):
        p = self.make([ocr(loai='khac', so_tien=0)])
        r = await p.scan('lan', JPEG)
        self.assertFalse(r['is_payment'])
        m = p.send_scan(r['scan_id'], 'lan')
        self.assertEqual(m['kind'], 'photo')
        self.assertIsNone(m['payment_id'])

    async def test_bad_image_and_sender(self):
        p = self.make()
        with self.assertRaises(ValueError):
            await p.scan('lan', b'not a jpeg' * 20)
        with self.assertRaises(ValueError):
            await p.scan('nguoi-la', JPEG)

    async def test_patch_and_void(self):
        p = self.make([ocr()])
        m = p.send_scan((await p.scan('lan', JPEG))['scan_id'], 'lan')
        pid = m['payment_id']
        got = p.patch_payment(pid, 'chu', dict(amount=254000))
        self.assertEqual(got['amount'], 254000)
        self.assertEqual(p.payment(pid, full=True)['edits'][-1]['by'], 'chu')
        p.void_payment(pid, 'chu', 'gửi nhầm')
        self.assertEqual(p.revenue()['count'], 0)
        with self.assertRaises(ValueError):
            p.patch_payment(pid, 'chu', dict(amount=1000))


NOON = datetime.now(VN).replace(hour=12, minute=0, second=0, microsecond=0).timestamp()


class TestDoiChieu(Base):
    """Giờ cố định 12:00 hôm nay: chạy test lúc vừa qua nửa đêm thì 'một tiếng trước' vẫn cùng ngày."""

    def setUp(self):
        p = mock.patch('time.time', return_value=NOON)
        p.start()
        self.addCleanup(p.stop)

    def seat(self, table, t0, t1=None, people=4):
        tl = self.hub.timeline
        tl.add('stage', ts=t0, table=table, stage='seated')
        tl.add('table', ts=t0 + 1, table=table, state='occupied', people=people)
        if t1:
            tl.add('stage', ts=t1, table=table, stage='left')

    async def test_visit_without_payment_then_matched(self):
        p = self.make([ocr()])
        now = time.time()
        self.seat('3', now - 3600, now - 1800)              # ngồi 30 phút, rời 30 phút trước
        self.seat('9', now - 3000, now - 2800)              # lượt 200 giây: không đòi thanh toán
        rv = p.revenue()
        self.assertEqual([x['kind'] for x in rv['review']], ['no_payment'])
        self.assertIn('Bàn 3', rv['review'][0]['text'])
        self.assertIn('4 khách', rv['review'][0]['text'])
        r = await p.scan('lan', JPEG)
        p.send_scan(r['scan_id'], 'lan', dict(table='3', paid_at=None))
        # đổi giờ gửi về lúc khách sắp rời để khớp lượt
        p.kho.run('UPDATE payments SET ts = ?', (int((now - 1900) * 1000),))
        rv = p.revenue()
        self.assertEqual(rv['review'], [])
        self.assertEqual(rv['total'], 245000)
        self.assertEqual(rv['per_guest'], 61250)
        msg = p.messages()[-1]
        self.assertTrue(msg['payment']['match']['ok'])

    async def test_payment_without_visit(self):
        p = self.make([ocr()])
        p.send_scan((await p.scan('lan', JPEG))['scan_id'], 'lan', dict(table='9'))
        rv = p.revenue()
        self.assertEqual([x['kind'] for x in rv['review']], ['no_visit'])
        self.assertFalse(p.messages()[-1]['payment']['match']['ok'])

    async def test_no_table_matches_single_nearby_visit(self):
        now = time.time()
        vs = [dict(key='3@1', table='3', start=now - 2000, end=now - 100, people=2, finished=True)]
        pays = [dict(id=1, ts=int(now * 1000), status='confirmed', table=None, paid_at=None)]
        self.assertEqual(doi_chieu.match(pays, vs, now), {1: '3@1'})
        vs.append(dict(key='9@1', table='9', start=now - 2000, end=now - 50, people=2, finished=True))
        self.assertEqual(doi_chieu.match(pays, vs, now), {1: None})     # hai lượt cùng lúc: không đoán

    async def test_note_visit_removes_review(self):
        p = self.make()
        now = time.time()
        self.seat('3', now - 3600, now - 1800)
        key = p.revenue()['review'][0]['visit']
        p.note_visit(key, 'chu', 'khách của quán')
        self.assertEqual(p.revenue()['review'], [])

    async def test_restart_mid_meal_closes_old_visit(self):
        p = self.make()
        now = time.time()
        tl = self.hub.timeline
        tl.add('stage', ts=now - 4000, table='3', stage='seated')
        tl.add('stage', ts=now - 3000, table='3', stage='seated')    # máy chủ khởi động lại, đếm lại từ đầu
        tl.add('stage', ts=now - 2000, table='3', stage='left')
        vs = doi_chieu.visits(tl, day_of(now), now)
        self.assertEqual([(v['start'], v['end']) for v in vs], [(now - 4000, now - 3000), (now - 3000, now - 2000)])

    async def test_visit_across_midnight_counts_for_new_day(self):
        self.make()
        # ngày của quán đổi lúc 4 giờ sáng (timeline.DOI_NGAY_H)
        t0 = datetime.now(VN).replace(hour=4, minute=0, second=0, microsecond=0).timestamp()
        tl = self.hub.timeline
        tl.add('stage', ts=t0 - 1800, table='3', stage='seated')       # 03:30, còn thuộc ngày trước
        tl.add('stage', ts=t0 + 1200, table='3', stage='left')         # 04:20, ngày mới
        tl.add('stage', ts=t0 - 7200, table='9', stage='seated')       # lượt xong hẳn từ hôm trước: không tính
        tl.add('stage', ts=t0 - 3600, table='9', stage='left')
        vs = doi_chieu.visits(tl, day_of(t0 + 60), t0 + 3600)
        self.assertEqual([v['table'] for v in vs], ['3'])


if __name__ == '__main__':
    unittest.main()
