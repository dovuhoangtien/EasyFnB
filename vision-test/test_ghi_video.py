"""Ghi hình và cắt clip (ghi_video.py): chạy ffmpeg thật trên khung hình giả.

Chạy (trong vision-test, bằng python của camera):  python -m unittest test_ghi_video -v
"""
import http.server
import json
import os
import shutil
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import numpy as np

import ghi_video
from ghi_video import GhiVideo

FFMPEG = ghi_video.tim_ffmpeg()
FFPROBE = FFMPEG and str(Path(FFMPEG).with_name('ffprobe' + Path(FFMPEG).suffix))


def khung(i, w=1280, h=720):
    img = np.zeros((h, w, 3), np.uint8)
    img[:, :, 0] = (i * 7) % 255
    x = (i * 23) % (w - 80)
    img[100:180, x:x + 80] = 255
    return img


def nguoi_mau():
    """Một người, đầu ở (640, 200) trên khung 1280x720: (kps, kcs, boxes) như pipeline đưa vào."""
    kps = np.zeros((1, 17, 2), np.float32)
    kps[0, :5] = [[640, 200], [625, 185], [655, 185], [605, 195], [675, 195]]
    kcs = np.zeros((1, 17), np.float32)
    kcs[0, :5] = 0.9
    return kps, kcs, np.float32([[540, 120, 740, 700]])


def khung_co_mat(i, w=1280, h=720):
    """Khung có ô bàn cờ to (dễ thấy khi bị che) ở chỗ mặt và một ô bàn cờ ở góc dưới (không bao giờ che)."""
    img = np.full((h, w, 3), 90, np.uint8)
    o = (np.indices((h, w)).sum(axis=0) // 16 % 2 * 255).astype(np.uint8)
    for y1, y2, x1, x2 in ((140, 260, 580, 700), (520, 700, 40, 420)):
        img[y1:y2, x1:x2] = o[y1:y2, x1:x2, None]
    img[0:20, (i * 9) % (w - 20):(i * 9) % (w - 20) + 20] = 255     # có chuyển động
    return img


def doc_khung(path, w=960, h=540):
    r = subprocess.run([FFMPEG, '-loglevel', 'error', '-i', str(path), '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-'],
                       capture_output=True, check=True)
    return list(np.frombuffer(r.stdout, np.uint8).reshape(-1, h, w, 3))


def probe(path):
    r = subprocess.run([FFPROBE, '-v', 'error', '-select_streams', 'v:0', '-count_frames', '-show_entries',
                        'stream=codec_name,pix_fmt,width,height,nb_read_frames:format=duration', '-of', 'json',
                        str(path)], capture_output=True, text=True, check=True)
    j = json.loads(r.stdout)
    s = j['streams'][0]
    return dict(codec=s['codec_name'], pix=s['pix_fmt'], w=s['width'], h=s['height'],
                frames=int(s['nb_read_frames']), dur=float(j['format']['duration']))


def ghi(gv, giay, fps=20, w=1280, h=720):
    het = time.monotonic() + giay
    i = 0
    while time.monotonic() < het:
        gv.khung(khung(i, w, h))
        i += 1
        time.sleep(1 / fps)


@unittest.skipUnless(FFMPEG, 'máy này không có ffmpeg')
class CoBan(unittest.TestCase):
    """Một lần ghi 7 giây (đoạn 2 giây) dùng chung cho các test cắt."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix='ghi_video_')
        cls.gv = GhiVideo(cls.tmp, fps=10, seg_s=2)
        cls.t0 = time.time()
        ghi(cls.gv, 7.0)
        cls.t1 = time.time()

    @classmethod
    def tearDownClass(cls):
        cls.gv.dong()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_1_dang_ghi_cat_duoc_ca_doan_chua_dong(self):
        # clip sự kiện xin khi đoạn cuối còn đang ghi: cut() chờ một chút rồi vẫn lấy được tới sát hiện tại
        self.assertTrue(self.gv.on)
        now = time.time()
        f = self.gv.cut(now - 3, now)
        self.assertIsNotNone(f)
        p = probe(f)
        self.assertEqual((p['codec'], p['pix']), ('h264', 'yuv420p'))
        self.assertAlmostEqual(p['dur'], 3.0, delta=1.01)

    def test_2_cac_doan_dung_do_dai_va_dung_gio(self):
        ds = self.gv.doan()
        self.assertGreaterEqual(len(ds), 3)
        self.assertAlmostEqual(ds[0]['start'], self.t0, delta=1.0)
        for a, b in zip(ds, ds[1:]):
            self.assertAlmostEqual(b['start'] - a['start'], 2.0, places=3)
        p = probe(ds[0]['path'])     # đoạn đã đóng: đúng 2 giây, 10 khung/giây, thu nhỏ còn 960 px
        self.assertEqual((p['codec'], p['pix'], p['w'], p['h']), ('h264', 'yuv420p', 960, 540))
        self.assertEqual(p['frames'], 20)

    def test_3_cat_giua_dung_do_dai(self):
        f = self.gv.cut(self.t0 + 1.5, self.t0 + 5.5)     # vắt qua ba đoạn
        p = probe(f)
        self.assertEqual((p['codec'], p['pix']), ('h264', 'yuv420p'))
        self.assertAlmostEqual(p['dur'], 4.0, delta=1.0)
        self.assertGreater(p['frames'], 35)
        with open(f, 'rb') as fh:    # faststart: moov nằm trước mdat, trình duyệt phát được ngay
            dau = fh.read(4096)
        self.assertEqual(dau[4:8], b'ftyp')
        self.assertLess(dau.find(b'moov'), 200)
        self.assertGreater(dau.find(b'moov'), 0)

    def test_4_su_kien_sat_luc_bat_dau_thi_clip_ngan_hon(self):
        r = self.gv.cat(self.t0 - 6, self.t0 + 2.5)
        self.assertIsNotNone(r)
        f, a, b = r
        self.assertGreaterEqual(a, self.t0 - 1.0)
        self.assertAlmostEqual(probe(f)['dur'], 2.5, delta=1.0)

    def test_5_luc_chua_ghi_thi_khong_co_clip(self):
        self.assertIsNone(self.gv.cut(self.t0 - 3600, self.t0 - 3590))
        self.assertIsNone(self.gv.cut(self.t0 + 5, self.t0 + 5))
        self.assertIsNone(self.gv.cut(self.t0 + 5, self.t0 + 1))

    def test_6_toi_da_60_giay(self):
        r = self.gv.cat(self.t0, self.t0 + 9999, cho=False)
        self.assertLessEqual(r[2] - r[1], 60.0)

    def test_7_gui_clip_su_kien_va_clip_theo_yeu_cau(self):
        nhan = []

        class H(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                body = self.rfile.read(int(self.headers['Content-Length']))
                nhan.append((urlparse(self.path), dict(self.headers), body))
                self.send_response(200)
                self.send_header('Content-Length', '2')
                self.end_headers()
                self.wfile.write(b'{}')

            def log_message(self, *a):
                pass

        srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.shutdown)

        class MC:
            url = f'http://127.0.0.1:{srv.server_address[1]}'
            on_event = None
            xong = []

            class s:
                headers = {'X-Edge-Key': 'khoa'}

            def job_done(self, jid, res):
                self.xong.append((jid, res))

        mc = MC()
        tam = set((Path(self.tmp) / '_cat').glob('*.mp4'))
        self.gv.noi(mc)
        self.addCleanup(setattr, self.gv, 'mc', None)
        # sự kiện "khách mới" không có eid: được đặt eid; sự kiện không tạo việc thì bỏ qua
        e = dict(loai='khach_moi', eid=None)
        mc.on_event(dict(loai='khach_roi', eid=None))
        mc.on_event(dict(loai='nhin_quanh', eid=None))
        self.gv.su_kien(e, t=self.t0 + 3)
        self.assertTrue(e['eid'])
        with self.gv._lock:
            self.assertEqual(len(self.gv._viec), 1)
            self.gv._viec[0]['luc'] = 0          # không chờ 8 giây trong test
        self.gv.viec(dict(id='j1', kind='clip', t_from=int((self.t0 + 1) * 1000), t_to=int((self.t0 + 4) * 1000)))
        self.gv.viec(dict(id='j2', kind='clip', t_from=int((self.t0 - 900) * 1000), t_to=int((self.t0 - 890) * 1000)))
        het = time.monotonic() + 15
        while time.monotonic() < het and (len(nhan) < 2 or not mc.xong):
            time.sleep(0.1)
        self.assertEqual(len(nhan), 2)
        q = [parse_qs(u.query) for u, _, _ in nhan]
        ev = next(x for x in q if 'eid' in x)
        self.assertEqual(ev['eid'], [e['eid']])
        self.assertEqual(ev['camera'], ['cam1'])
        self.assertAlmostEqual(int(ev['t_to'][0]) / 1000, self.t1, delta=1.5)   # t+8 chưa ghi tới: lấy tới hết phần đã ghi
        self.assertEqual(next(x for x in q if 'job' in x)['job'], ['j1'])
        for _, h, body in nhan:
            self.assertEqual(h.get('X-Edge-Key'), 'khoa')
            self.assertEqual(body[4:8], b'ftyp')
        self.assertEqual(mc.xong, [('j2', dict(error='chưa ghi hình lúc đó'))])
        self.assertEqual(set((Path(self.tmp) / '_cat').glob('*.mp4')), tam)   # clip tạm đã xoá sau khi gửi

    def test_8_khong_bat_ghi_hinh_thi_viec_clip_bao_loi(self):
        xong = []

        class MC:
            def job_done(self, jid, res):
                xong.append((jid, res))

        ghi_video.viec_clip(None, MC(), dict(id='j9', kind='clip'))
        self.assertEqual(xong[0][0], 'j9')
        self.assertIn('không ghi hình', xong[0][1]['error'])


@unittest.skipUnless(FFMPEG, 'máy này không có ffmpeg')
class TinhHuong(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='ghi_video_')
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def make(self, **kw):
        gv = GhiVideo(self.tmp, **dict(dict(fps=10, seg_s=2), **kw))
        self.addCleanup(gv.dong)
        return gv

    def test_nguon_cham_va_nguon_nhanh_van_dung_gio(self):
        for fps_nguon in (2, 120):
            gv = GhiVideo(Path(self.tmp) / str(fps_nguon), fps=10, seg_s=2)
            t0 = time.time()
            ghi(gv, 4.0, fps=fps_nguon)
            gv.dong()
            ds = gv.doan()
            tong = sum(probe(d['path'])['frames'] for d in ds)
            self.assertAlmostEqual(tong, 40, delta=8, msg=f'nguồn {fps_nguon} khung/giây')
            self.assertAlmostEqual(ds[-1]['end'] - t0, 4.0, delta=1.0)

    def test_doi_co_anh_giua_chung_mo_luot_ghi_moi(self):
        gv = self.make()
        ghi(gv, 2.5, w=1280, h=720)
        t_doi = time.time()
        ghi(gv, 2.5, w=640, h=480)
        gv.dong()
        self.assertIsNone(gv.ly_do_tat)
        ds = gv.doan()
        self.assertEqual(len({d['run'] for d in ds}), 2)
        self.assertEqual(probe(ds[0]['path'])['w'], 960)
        self.assertEqual((probe(ds[-1]['path'])['w'], probe(ds[-1]['path'])['h']), (640, 480))
        sau = gv.cut(t_doi + 0.5, t_doi + 2.5)
        self.assertEqual(probe(sau)['w'], 640)
        self.assertEqual(probe(gv.cut(t_doi - 2.0, t_doi - 0.5))['w'], 960)

    def test_ffmpeg_chet_mot_lan_thi_mo_lai_hai_lan_lien_thi_tat(self):
        gv = self.make()
        ghi(gv, 1.5)
        run1 = gv._run
        gv._proc.kill()
        ghi(gv, 2.5)
        self.assertTrue(gv.on)
        self.assertNotEqual(gv._run, run1)
        self.assertEqual(gv._proc.poll(), None)
        gv._proc.kill()
        ghi(gv, 1.0)
        self.assertFalse(gv.on)
        self.assertIn('ffmpeg', gv.ly_do_tat)
        gv.khung(khung(0))               # đã tắt: pipeline gọi tiếp vẫn không sao
        # đoạn ghi trước khi ffmpeg bị giết (tệp chưa đóng) vẫn cắt được
        self.assertIsNotNone(gv.cut(run1 / 1000, run1 / 1000 + 1.5))

    def test_dong_ho_bi_chinh_thi_mo_luot_ghi_theo_gio_moi(self):
        gv = self.make()
        ghi(gv, 1.5)
        gv._gio = lambda: time.time() + 3600
        ghi(gv, 2.5)
        gv.dong()
        runs = sorted({d['run'] for d in gv.doan()})
        self.assertEqual(len(runs), 2)
        self.assertAlmostEqual((runs[1] - runs[0]) / 1000, 3600, delta=5)
        self.assertIsNotNone(gv.cut(runs[1] / 1000, runs[1] / 1000 + 2, cho=False))

    def test_don_theo_tuoi_va_dung_luong_tep_dang_bi_doc_thi_de_lai(self):
        d = Path(self.tmp)
        now = time.time()
        cu = d / f'r{int((now - 30 * 3600) * 1000)}_00000.mp4'       # 30 giờ trước
        moi = d / f'r{int((now - 3600) * 1000)}_00000.mp4'           # 1 giờ trước
        khoa = d / f'r{int((now - 40 * 3600) * 1000)}_00000.mp4'     # cũ nhưng đang có người đọc
        for f in (cu, moi, khoa):
            f.write_bytes(b'x' * 1000)
        (d / 'index.json').write_text(json.dumps(dict(runs={cu.stem[1:-6]: dict(seg_s=2, end_ms=1)})))
        with open(khoa, 'rb'):
            gv = self.make(gio=24)
            con = {Path(x['path']).name for x in gv.doan()}
            if os.name == 'nt':          # Windows không cho xoá tệp đang mở: bỏ qua, không lỗi
                self.assertEqual(con, {moi.name, khoa.name})
            else:
                self.assertEqual(con, {moi.name})
        gv._don_dep()
        self.assertEqual({Path(x['path']).name for x in gv.doan()}, {moi.name})
        self.assertEqual(gv._runs, {})   # lượt ghi không còn tệp thì bỏ khỏi chỉ mục: chỉ mục không lớn mãi
        # theo dung lượng: giới hạn 2500 byte, ba tệp 1000 byte -> xoá tệp cũ nhất
        for k in (2, 3):
            (d / f'r{int((now - k * 3600) * 1000)}_00000.mp4').write_bytes(b'x' * 1000)
        gv.gb = 2500 / 2**30
        gv._don_dep()
        ten = sorted(Path(x['path']).name for x in gv.doan())
        self.assertEqual(len(ten), 2)
        self.assertIn(moi.name, ten)

    def test_ghi_ban_goc_va_vi_tri_mat(self):
        gv = self.make()
        img = np.random.default_rng(0).integers(0, 255, (720, 1280, 3), dtype=np.uint8)
        ro, mat0 = GhiVideo._chuan_bi(gv, (img, None, None, None))
        goc, mat = GhiVideo._chuan_bi(gv, (img, *nguoi_mau()))
        self.assertEqual(goc.shape, (540, 960, 3))
        self.assertEqual(np.abs(ro.astype(int) - goc.astype(int)).sum(), 0)   # bản ghi KHÔNG che
        self.assertIsNone(mat0['m'])                                          # không có dữ liệu người
        self.assertEqual(len(mat['m']), 1)
        cx, cy = mat['m'][0][:2]
        self.assertAlmostEqual(cx, 480, delta=10)                             # đầu (640, 200) thu nhỏ 0,75
        self.assertAlmostEqual(cy, 150, delta=25)
        che = ghi_video.che_khung(goc.copy(), mat)
        khac = np.abs(goc.astype(int) - che.astype(int)).sum(axis=2) > 0
        self.assertGreater(khac[120:180, 450:510].mean(), 0.5)    # vùng đầu bị che
        self.assertEqual(khac[400:, :].sum(), 0)                  # chỗ khác giữ nguyên
        toan = ghi_video.che_khung(goc.copy(), mat0)              # không có dữ liệu: che cả khung
        self.assertGreater((np.abs(goc.astype(int) - toan.astype(int)).sum(axis=2) > 0).mean(), 0.9)
        # có người mà không có khung xương: che cả khung người
        _, m2 = GhiVideo._chuan_bi(gv, (img, None, None, np.float32([[540, 120, 740, 700]])))
        self.assertEqual((m2['m'], len(m2['b'])), ([], 1))

    def test_cat_co_che_theo_tep_vi_tri_mat(self):
        gv = self.make()
        t0 = time.time()
        het = time.monotonic() + 4.5
        i = 0
        while time.monotonic() < het:
            f = khung_co_mat(i)
            # giây 2,0-2,6 tính từ lúc bắt đầu: pipeline không đưa dữ liệu người -> khung đó phải che cả khung
            co = not (2.0 <= time.monotonic() - (het - 4.5) < 2.6)
            gv.khung(f, *(nguoi_mau() if co else (None, None, None)))
            i += 1
            time.sleep(0.05)
        gv.dong()
        ds = gv.doan()
        self.assertTrue(all(Path(d['path'][:-4] + '.mat.jsonl').exists() for d in ds))
        goc = gv.cut(t0 + 0.5, t0 + 4.0, cho=False)
        che = gv.cut(t0 + 0.5, t0 + 4.0, cho=False, che=True)
        self.assertIsNotNone(goc)
        self.assertIsNotNone(che)
        p = probe(che)
        self.assertEqual((p['codec'], p['pix'], p['w'], p['h']), ('h264', 'yuv420p', 960, 540))
        self.assertAlmostEqual(p['dur'], 3.5, delta=0.6)
        with open(che, 'rb') as fh:
            dau = fh.read(4096)
        self.assertEqual(dau[4:8], b'ftyp')
        self.assertGreater(dau.find(b'moov'), 0)
        A, B = doc_khung(goc), doc_khung(che)
        self.assertGreater(len(B), 25)
        dau_ro = [float(f[120:180, 450:510].std()) for f in A]
        dau_che = [float(f[120:180, 450:510].std()) for f in B]
        self.assertGreater(min(dau_ro), 40)                     # bản gốc thấy rõ ô bàn cờ ở chỗ mặt
        self.assertLess(max(dau_che), 25, dau_che)              # bản che: mọi khung đều mờ chỗ mặt
        toan = [k for k, f in enumerate(B) if float(f[400:520, 50:300].std()) < 25]
        self.assertGreater(len(toan), 2, 'khung không có dữ liệu người phải che cả khung')
        self.assertLess(len(toan), len(B) - 10, 'khung có dữ liệu mặt thì chỉ che mặt')

    def test_viec_clip_goc_khong_che_su_kien_an_ninh_dai_hon(self):
        gv = self.make()
        goi = []
        gv.cat = lambda a, b, cho=True, che=False: goi.append((round(b - a), che)) or None

        class MC:
            xong = []
            che = True

            def an_ninh(self):
                return dict(blur_faces=self.che)

            def job_done(self, jid, res):
                self.xong.append(jid)

        mc = MC()
        gv.noi(mc)
        gv._lam_viec(dict(job=dict(id='j1', t_from=0, t_to=5000, goc=True)))
        gv._lam_viec(dict(job=dict(id='j2', t_from=0, t_to=5000)))
        mc.che = False                                     # chủ quán tắt che mặt
        gv._lam_viec(dict(job=dict(id='j3', t_from=0, t_to=5000, goc=False)))
        gv.mo_mat = False                                  # --khong-mo-mat
        mc.che = True
        gv._lam_viec(dict(job=dict(id='j4', t_from=0, t_to=5000)))
        self.assertEqual([c for _, c in goi], [False, True, False, False])
        gv.mo_mat = True
        with gv._lock:
            gv._viec.clear()
        gv.su_kien(dict(loai='lay_do', eid='cam1:9'), t=1000.0)
        gv.su_kien(dict(loai='goi_phuc_vu', eid='cam1:10'), t=1000.0)
        v = {x['eid']: x for x in gv._viec}
        self.assertEqual((v['cam1:9']['t_from'], v['cam1:9']['t_to']), (990.0, 1020.0))
        self.assertEqual((v['cam1:10']['t_from'], v['cam1:10']['t_to']), (994.0, 1008.0))
        gv._lam_viec(v['cam1:9'])
        self.assertEqual(goi[-1], (30, True))

    def test_don_dep_xoa_ca_tep_vi_tri_mat(self):
        d = Path(self.tmp)
        cu = d / f'r{int((time.time() - 30 * 3600) * 1000)}_00000.mp4'
        cu.write_bytes(b'x' * 1000)
        mat = Path(str(cu)[:-4] + '.mat.jsonl')
        mat.write_text('{"t":1,"m":[]}\n')
        le = d / 'r123_00001.mat.jsonl'                    # không còn đoạn video
        le.write_text('{"t":1,"m":[]}\n')
        self.make(gio=24)
        self.assertFalse(cu.exists())
        self.assertFalse(mat.exists())
        self.assertFalse(le.exists())


class KhongCoFfmpeg(unittest.TestCase):
    def test_thieu_ffmpeg_thi_tu_tat_pipeline_van_chay(self):
        with tempfile.TemporaryDirectory() as tmp:
            gv = GhiVideo(tmp, ffmpeg=str(Path(tmp) / 'khong_co_ffmpeg.exe'))
            self.assertFalse(gv.on)
            self.assertIn('ffmpeg', gv.ly_do_tat)
            gv.khung(khung(0))
            gv.su_kien(dict(loai='goi_phuc_vu', eid='x:1'))
            self.assertIsNone(gv.cut(time.time() - 5, time.time()))
            gv.dong()


if __name__ == '__main__':
    unittest.main()
