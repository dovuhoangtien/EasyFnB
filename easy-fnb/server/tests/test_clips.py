"""Clip video: clip của từng việc (theo eid) và clip xin theo khoảng thời gian.

Chạy (trong easy-fnb):  python -m unittest server.tests.test_clips -v
"""
import asyncio
import os
import tempfile
import unittest
from pathlib import Path

_tmp = tempfile.TemporaryDirectory()
os.environ.setdefault('DATA_DIR', _tmp.name)   # đặt trước khi nạp server.app, để không đụng dữ liệu thật
os.environ.pop('K_SERVICE', None)

from fastapi import FastAPI, Header, HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from server import clips as clips_module  # noqa: E402
from server.clips import Clips, router  # noqa: E402
from server.hub import Hub, now_ms  # noqa: E402


class NoGemini:
    enabled = False
    model = None


def mp4(n=2000, fill=b'x'):
    return b'\x00\x00\x00\x18ftypisom' + fill * n


def ev(eid, kind='goi_phuc_vu', table='B1', camera='cam1'):
    return dict(kind=kind, camera=camera, table=table, eid=eid)


class Base(unittest.IsolatedAsyncioTestCase):
    def make(self, **kw):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.hub = Hub(self.dir, NoGemini())
        self.t = 1000.0
        self.clips = Clips(self.hub, self.dir, clock=lambda: self.t, **kw)
        return self.hub, self.clips

    def files(self):
        return sorted((self.dir / 'clips').glob('*.mp4'))


class ClipSuKien(Base):
    async def test_clip_gan_vao_viec_cua_eid_va_bao_cho_man_hinh(self):
        hub, clips = self.make()
        q = asyncio.Queue()
        hub.subs.add(q)
        aid = hub.edge_event(ev('cam1:1'))
        self.assertNotIn('clip', hub.alerts[aid])
        self.assertIsNone(clips.alert_file(aid))
        self.assertEqual(clips.add_event_clip('cam1:1', 'cam1', 1000, 15000, mp4()), aid)
        self.assertIs(hub.alerts[aid]['clip'], True)
        self.assertEqual(clips.alert_file(aid).read_bytes(), mp4())
        got = []
        while not q.empty():
            got.append(q.get_nowait())
        self.assertEqual(got[-1][0], 'alert')
        self.assertIs(got[-1][1]['clip'], True)
        self.assertTrue(hub.state()['alerts'][0]['clip'])

    async def test_clip_toi_truoc_viec_thi_giu_roi_gan_khi_viec_xuat_hien(self):
        hub, clips = self.make()
        self.assertIsNone(clips.add_event_clip('cam1:7', 'cam1', 1, 2, mp4()))
        self.assertEqual(len(self.files()), 1)
        aid = hub.edge_event(ev('cam1:7'))
        self.t += 5
        clips.sweep()
        self.assertIs(hub.alerts[aid]['clip'], True)
        self.assertEqual(clips.early, {})
        self.assertIsNotNone(clips.alert_file(aid))

    async def test_eid_la_thi_giu_mot_luc_roi_bo(self):
        hub, clips = self.make(early_s=30)
        clips.add_event_clip('ma-la', 'cam1', 1, 2, mp4())
        self.t += 29
        clips.sweep()
        self.assertEqual(len(self.files()), 1)
        self.t += 2
        clips.sweep()
        self.assertEqual(self.files(), [])
        self.assertEqual(clips.early, {})

    async def test_gui_trung_va_su_kien_gop_thi_giu_clip_dau(self):
        hub, clips = self.make()
        aid = hub.edge_event(ev('cam1:1'))
        self.assertEqual(hub.edge_event(ev('cam1:2')), aid)       # khách vẫn gọi: gộp vào việc cũ
        clips.add_event_clip('cam1:1', 'cam1', 1, 2, mp4(fill=b'a'))
        clips.add_event_clip('cam1:1', 'cam1', 1, 2, mp4(fill=b'b'))   # gửi lại cùng eid
        self.assertEqual(clips.add_event_clip('cam1:2', 'cam1', 3, 4, mp4(fill=b'c')), aid)
        self.assertEqual(len(self.files()), 1)
        self.assertEqual(clips.alert_file(aid).read_bytes(), mp4(fill=b'a'))
        # gửi trùng khi việc chưa có: cũng chỉ giữ một tệp
        clips.add_event_clip('x', 'cam1', 1, 2, mp4())
        clips.add_event_clip('x', 'cam1', 1, 2, mp4())
        self.assertEqual(len(self.files()), 2)

    async def test_viec_da_dong_van_nhan_clip(self):
        hub, clips = self.make()
        aid = hub.edge_event(ev('cam1:1'))
        hub.done(aid, None)
        self.assertEqual(clips.add_event_clip('cam1:1', 'cam1', 1, 2, mp4()), aid)
        self.assertIs(hub.alerts[aid]['clip'], True)
        self.assertEqual(hub.alerts[aid]['status'], 'done')

    async def test_hai_camera_moi_viec_mot_clip(self):
        hub, clips = self.make()
        a1 = hub.edge_event(ev('cam1:1', table='B1', camera='cam1'))
        a2 = hub.edge_event(ev('cam2:1', table='C1', camera='cam2'))
        self.assertNotEqual(a1, a2)
        clips.add_event_clip('cam1:1', 'cam1', 1, 2, mp4(fill=b'1'))
        clips.add_event_clip('cam2:1', 'cam2', 1, 2, mp4(fill=b'2'))
        self.assertEqual(clips.alert_file(a1).read_bytes(), mp4(fill=b'1'))
        self.assertEqual(clips.alert_file(a2).read_bytes(), mp4(fill=b'2'))

    async def test_ca_moi_xoa_clip_tren_may_chu(self):
        hub, clips = self.make()
        aid = hub.edge_event(ev('cam1:1'))
        clips.add_event_clip('cam1:1', 'cam1', 1, 2, mp4())
        clips.add_event_clip('chua-co', 'cam1', 1, 2, mp4())
        hub.reset()
        clips.reset()
        self.assertEqual(self.files(), [])
        self.assertIsNone(clips.alert_file(aid))
        self.assertEqual((clips.by_alert, clips.early, clips.req), ({}, {}, {}))

    async def test_thu_muc_day_thi_xoa_clip_cu_nhat(self):
        hub, clips = self.make(max_bytes=5000)
        a1 = hub.edge_event(ev('cam1:1', table='B1'))
        a2 = hub.edge_event(ev('cam1:2', table='B2'))
        a3 = hub.edge_event(ev('cam1:3', table='B3'))
        clips.add_event_clip('cam1:1', 'cam1', 1, 2, mp4(2000))
        os.utime(clips.alert_file(a1), (1, 1))           # cũ nhất
        clips.add_event_clip('cam1:2', 'cam1', 1, 2, mp4(2000))
        os.utime(clips.alert_file(a2), (2, 2))
        clips.add_event_clip('cam1:3', 'cam1', 1, 2, mp4(2000))
        self.assertIsNone(clips.alert_file(a1))
        self.assertIs(hub.alerts[a1]['clip'], False)
        self.assertIsNotNone(clips.alert_file(a2))
        self.assertIsNotNone(clips.alert_file(a3))
        self.assertEqual(len(self.files()), 2)

    async def test_tep_dang_bi_doc_khong_lam_hong_viec_don(self):
        hub, clips = self.make(max_bytes=3000)
        a1 = hub.edge_event(ev('cam1:1', table='B1'))
        hub.edge_event(ev('cam1:2', table='B2'))
        clips.add_event_clip('cam1:1', 'cam1', 1, 2, mp4(2000))
        f = clips.alert_file(a1)
        os.utime(f, (1, 1))
        with open(f, 'rb'):         # trình duyệt đang tải clip này (Windows không cho xoá)
            clips.add_event_clip('cam1:2', 'cam1', 1, 2, mp4(2000))
            clips.reset()
        clips.reset()
        self.assertEqual(self.files(), [])

    async def test_clip_cua_lan_chay_truoc_bi_xoa_khi_khoi_dong(self):
        hub, clips = self.make()
        (self.dir / 'clips' / 'cu.mp4').write_bytes(mp4())
        Clips(hub, self.dir)
        self.assertEqual(self.files(), [])


class ClipTheoYeuCau(Base):
    def live(self, cam='cam1'):
        self.hub.edge_frame(cam, 'live', b'\xff\xd8x')

    async def test_khong_co_camera_thi_that_bai_ngay(self):
        hub, clips = self.make()
        now = now_ms()
        r = clips.request('cam9', now - 20000, now - 5000)
        self.assertEqual(r['status'], 'failed')
        self.assertIn('cam9', r['error'])
        self.assertIsNone(r['url'])
        self.assertEqual(hub.jobs, {})

    async def test_camera_cat_va_gui_thi_san_sang(self):
        hub, clips = self.make()
        self.live('cam1')
        self.live('cam2')
        now = now_ms()
        r = clips.request('cam1', now - 20000, now - 5000)
        self.assertEqual((r['status'], r['url'], r['error']), ('pending', None, None))
        self.assertEqual(hub.take_jobs('cam2'), [])              # việc chỉ tới đúng camera
        jobs = hub.take_jobs('cam1')
        self.assertEqual(jobs, [dict(id=jobs[0]['id'], kind='clip', t_from=now - 20000, t_to=now - 5000)])
        self.assertEqual(clips.add_job_clip(jobs[0]['id'], now - 20500, now - 5000, mp4()), r['id'])
        await asyncio.sleep(0.01)
        v = clips.view(clips.get(r['id']))
        self.assertEqual((v['status'], v['url'], v['t_from']), ('ready', f"/api/clips/{r['id']}.mp4", now - 20500))
        self.assertEqual(clips.get(r['id'])['file'].read_bytes(), mp4())
        self.assertIsNone(clips.add_job_clip(jobs[0]['id'], 1, 2, mp4()))    # gửi lại: không nhận nữa
        self.assertIsNone(clips.add_job_clip('j999', 1, 2, mp4()))
        self.assertEqual(len(self.files()), 1)

    async def test_camera_bao_chua_ghi_hinh_luc_do(self):
        hub, clips = self.make()
        self.live()
        now = now_ms()
        r = clips.request('cam1', now - 20000, now - 5000)
        jid = hub.take_jobs('cam1')[0]['id']
        hub.job_result(jid, dict(error='chưa ghi hình lúc đó'))
        await asyncio.sleep(0.01)
        v = clips.view(clips.get(r['id']))
        self.assertEqual((v['status'], v['error'], v['url']), ('failed', 'chưa ghi hình lúc đó', None))

    async def test_camera_khong_tra_loi_thi_het_han(self):
        hub, clips = self.make(wait_s=0.05)
        self.live()
        now = now_ms()
        r = clips.request('cam1', now - 20000, now - 5000)
        await asyncio.sleep(0.15)
        v = clips.view(clips.get(r['id']))
        self.assertEqual((v['status'], v['error']), ('failed', 'Máy camera không trả lời.'))
        self.assertEqual(hub.jobs, {})

    async def test_khoang_thoi_gian_sai_bi_tu_choi_dai_qua_bi_cat(self):
        hub, clips = self.make()
        self.live()
        now = now_ms()
        for a, b in ((now - 5000, now - 5000), (now - 5000, now - 9000), (now + 60000, now + 70000),
                     ('x', now), (None, None)):
            with self.assertRaises(ValueError):
                clips.request('cam1', a, b)
        self.assertEqual(clips.req, {})
        r = clips.request('cam1', now - 300000, now - 100000)       # 200 giây -> 60 giây
        self.assertEqual(r['t_to'] - r['t_from'], 60000)
        r = clips.request('cam1', now - 10000, now + 50000)         # kết thúc ở tương lai -> tới bây giờ
        self.assertLessEqual(r['t_to'], now_ms())
        self.assertGreaterEqual(r['t_to'], now)

    async def test_chi_nho_mot_so_yeu_cau_gan_nhat(self):
        hub, clips = self.make()
        now = now_ms()
        ids = [clips.request('cam9', now - 9000, now - 1000)['id'] for _ in range(clips_module.MAX_REQ + 5)]
        self.assertEqual(len(clips.req), clips_module.MAX_REQ)
        self.assertIsNone(clips.get(ids[0]))
        self.assertIsNotNone(clips.get(ids[-1]))


class QuaHttp(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.hub = Hub(Path(self.tmp.name), NoGemini())
        self.clips = Clips(self.hub, Path(self.tmp.name))

        def edge_auth(x_edge_key: str | None = Header(default=None)):
            if x_edge_key != 'khoa':
                raise HTTPException(401, 'sai X-Edge-Key')

        app = FastAPI()
        app.include_router(router(self.clips, edge_auth))

        @app.post('/su-kien')
        async def su_kien(eid: str):       # tạo việc trong vòng lặp của máy chủ thử
            return dict(alert_id=self.hub.edge_event(ev(eid)))

        @app.post('/camera-song')
        async def camera_song():
            self.hub.edge_frame('cam1', 'live', b'\xff\xd8x')
            return {}

        ctx = TestClient(app)
        self.c = ctx.__enter__()
        self.addCleanup(ctx.__exit__, None, None, None)
        self.k = {'X-Edge-Key': 'khoa', 'Content-Type': 'video/mp4'}

    def up(self, data, **params):
        return self.c.post('/api/edge/clip', params=dict(dict(camera='cam1', t_from=1000, t_to=15000), **params),
                           content=data, headers=self.k)

    def check_range(self, url, data):
        r = self.c.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers['content-type'], 'video/mp4')
        self.assertEqual(r.headers.get('accept-ranges'), 'bytes')
        self.assertEqual(r.content, data)
        r = self.c.get(url, headers={'Range': 'bytes=0-99'})       # Safari hỏi từng khúc để tua video
        self.assertEqual(r.status_code, 206)
        self.assertEqual(r.headers['content-range'], f'bytes 0-99/{len(data)}')
        self.assertEqual(r.content, data[:100])
        r = self.c.get(url, headers={'Range': 'bytes=1000-'})
        self.assertEqual(r.status_code, 206)
        self.assertEqual(r.headers['content-range'], f'bytes 1000-{len(data) - 1}/{len(data)}')
        self.assertEqual(r.content, data[1000:])
        r = self.c.get(url, headers={'Range': f'bytes={len(data) + 10}-'})
        self.assertEqual(r.status_code, 416)

    def test_clip_su_kien_gui_len_va_xem_duoc_theo_khuc(self):
        aid = self.c.post('/su-kien', params=dict(eid='cam1:1')).json()['alert_id']
        self.assertEqual(self.c.get(f'/api/alerts/{aid}/clip.mp4').status_code, 404)
        data = mp4(5000)
        r = self.up(data, eid='cam1:1')
        self.assertEqual((r.status_code, r.json()), (200, dict(ok=True, alert_id=aid)))
        self.check_range(f'/api/alerts/{aid}/clip.mp4', data)

    def test_tu_choi_sai_khoa_qua_lon_khong_phai_mp4_thieu_ma(self):
        self.assertEqual(self.c.post('/api/edge/clip', params=dict(camera='cam1', t_from=1, t_to=2, eid='e'),
                                     content=mp4()).status_code, 401)
        self.assertEqual(self.up(mp4()).status_code, 400)                      # không eid, không job
        self.assertEqual(self.up(b'\xff\xd8 day la anh jpeg ' * 10, eid='e').status_code, 400)
        self.assertEqual(self.up(mp4(), job='j404').status_code, 404)
        self.assertEqual(self.c.post('/api/edge/clip', params=dict(camera='cam1', eid='e'), content=mp4(),
                                     headers=self.k).status_code, 422)         # thiếu t_from, t_to
        cu = clips_module.MAX_UPLOAD
        clips_module.MAX_UPLOAD = 3000
        self.addCleanup(setattr, clips_module, 'MAX_UPLOAD', cu)
        self.assertEqual(self.up(mp4(5000), eid='e').status_code, 413)
        self.assertEqual(self.up(mp4(1000), eid='e').status_code, 200)
        self.assertEqual(len(list((Path(self.tmp.name) / 'clips').glob('*'))), 1)

    def test_ma_la_khong_di_ra_ngoai_thu_muc(self):
        (Path(self.tmp.name) / 'bi_mat.mp4').write_bytes(mp4())
        for url in ('/api/clips/..%2Fbi_mat.mp4', '/api/clips/%2E%2E%5Cbi_mat.mp4', '/api/clips/../bi_mat.mp4',
                    '/api/alerts/..%2F..%2Fbi_mat/clip.mp4', '/api/alerts/%2E%2E/clip.mp4', '/api/clips/khong-co',
                    '/api/clips/khong-co.mp4'):
            self.assertEqual(self.c.get(url).status_code, 404, url)
        # eid chứa đường dẫn: chỉ là khoá tra cứu, tên tệp do máy chủ đặt
        self.assertEqual(self.up(mp4(), eid='../../bi_mat').status_code, 200)
        self.assertEqual([f.parent.name for f in Path(self.tmp.name).rglob('*.mp4') if f.name != 'bi_mat.mp4'],
                         ['clips'])

    def test_xin_clip_theo_gio_tu_dau_den_cuoi(self):
        now = now_ms()
        r = self.c.post('/api/clips', json=dict(camera='cam1', t_from=now - 20000, t_to=now - 5000)).json()
        self.assertEqual(r['status'], 'failed')                    # camera chưa chạy
        self.c.post('/camera-song')
        r = self.c.post('/api/clips', json=dict(camera='cam1', t_from=now - 20000, t_to=now - 5000)).json()
        self.assertEqual(r['status'], 'pending')
        cid = r['id']
        self.assertEqual(self.c.get(f'/api/clips/{cid}').json()['status'], 'pending')
        self.assertEqual(self.c.get(f'/api/clips/{cid}.mp4').status_code, 404)
        self.assertEqual(self.c.get('/api/edge/jobs', params=dict(camera='cam1')).status_code, 404)  # app thử không có đường này
        jobs = self.hub.take_jobs('cam1')
        self.assertEqual((jobs[0]['kind'], jobs[0]['t_from'], jobs[0]['t_to']), ('clip', now - 20000, now - 5000))
        data = mp4(4000)
        u = self.up(data, job=jobs[0]['id'], t_from=now - 20000, t_to=now - 5000)
        self.assertEqual((u.status_code, u.json()), (200, dict(ok=True, clip_id=cid)))
        v = self.c.get(f'/api/clips/{cid}').json()
        self.assertEqual(v, dict(id=cid, status='ready', camera='cam1', t_from=now - 20000, t_to=now - 5000,
                                 url=f'/api/clips/{cid}.mp4', error=None))
        self.check_range(v['url'], data)
        self.assertEqual(self.c.post('/api/clips', json=dict(camera='cam1', t_from=now, t_to=now - 1)).status_code, 400)

    def test_clip_goc_can_pin_ghi_nhat_ky_va_giu_bang_chung(self):
        self.c.post('/camera-song')
        aid = self.c.post('/su-kien', params=dict(eid='g1')).json()['alert_id']
        self.assertEqual(self.c.post(f'/api/alerts/{aid}/clip-goc').status_code, 403)     # chưa có PIN
        self.hub.set_pin('2468')
        self.assertEqual(self.c.post(f'/api/alerts/{aid}/clip-goc', headers={'X-Owner-Pin': '1'}).status_code, 403)
        r = self.c.post(f'/api/alerts/{aid}/clip-goc', headers={'X-Owner-Pin': '2468'}).json()
        self.assertEqual((r['status'], r['goc']), ('pending', True))
        self.assertTrue(any('bản gốc' in e['text'] for e in self.hub.log))
        job = self.hub.take_jobs('cam1')[0]
        self.assertTrue(job['goc'])
        data = mp4(3000)
        self.up(data, job=job['id'], t_from=job['t_from'], t_to=job['t_to'])
        self.assertEqual(self.c.get(f"/api/clips/{r['id']}.mp4").status_code, 403)
        self.assertEqual(self.c.get(f"/api/clips/{r['id']}.mp4", params=dict(pin='2468')).content, data)
        self.assertEqual(self.c.post(f"/api/clips/{r['id']}/keep", headers={'X-Owner-Pin': '2468'}).json()['kept'],
                         True)
        self.clips.reset()                                                # bắt đầu ca mới: bằng chứng vẫn còn
        self.assertEqual(self.c.get(f"/api/clips/{r['id']}.mp4", params=dict(pin='2468')).content, data)
        self.assertEqual(self.c.get(f"/api/clips/{r['id']}.mp4").status_code, 403)


class TrongAppThat(unittest.TestCase):
    def test_duong_clip_nam_truoc_duong_bat_moi_thu_va_reset_xoa_clip(self):
        from server import app as app_module
        c = TestClient(app_module.app)
        now = now_ms()
        r = c.post('/api/clips', json=dict(camera='cam-khong-co', t_from=now - 9000, t_to=now - 1000))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['status'], 'failed')
        self.assertEqual(c.get(f"/api/clips/{r.json()['id']}").json()['status'], 'failed')
        self.assertEqual(c.get('/api/alerts/a999/clip.mp4').status_code, 404)
        self.assertEqual(c.get('/api/alerts/a999/clip.mp4').json()['detail'], 'việc này chưa có clip')
        self.assertEqual(c.post('/api/reset').status_code, 200)
        self.assertEqual(app_module.clips.req, {})


if __name__ == '__main__':
    unittest.main()
