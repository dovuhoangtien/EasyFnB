"""Kết nối điện thoại: manifest riêng từng nhân viên (thêm vào màn hình chính) và cổng https trong /api/info.

Chạy (trong easy-fnb):  python -m unittest server.tests.test_ket_noi -v
"""
import os
import tempfile
import unittest

_tmp = tempfile.TemporaryDirectory()
os.environ['DATA_DIR'] = _tmp.name        # đặt trước khi nạp server.app, để không đụng dữ liệu thật
os.environ.pop('K_SERVICE', None)

from fastapi.testclient import TestClient  # noqa: E402

from server import app as app_module  # noqa: E402


class KetNoi(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app_module.app)

    def test_manifest_cua_nhan_vien_tro_ve_dung_app_cua_ho(self):
        sid = app_module.hub.staff[0]['id']
        r = self.client.get(f'/api/manifest/nv/{sid}')
        self.assertEqual(r.status_code, 200)
        self.assertIn('manifest+json', r.headers['content-type'])
        m = r.json()
        self.assertEqual(m['start_url'], f'/nv/{sid}')
        self.assertEqual(m['id'], m['start_url'])      # mỗi người một bản cài riêng
        self.assertEqual(m['display'], 'standalone')
        self.assertTrue(m['start_url'].startswith(m['scope']))
        self.assertTrue(any(i['sizes'] == '512x512' and i.get('purpose') != 'maskable' for i in m['icons']))
        self.assertTrue(any(i.get('purpose') == 'maskable' for i in m['icons']))

    def test_manifest_ma_co_ky_tu_la_duoc_ma_hoa(self):
        cu = app_module.hub.staff
        self.addCleanup(app_module.hub.set_staff, cu)
        app_module.hub.set_staff([dict(id='tú 2', name='Tú', role='serve')])
        r = self.client.get('/api/manifest/nv/t%C3%BA%202')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['start_url'], '/nv/t%C3%BA%202')

    def test_manifest_nhan_vien_khong_co_la_404(self):
        self.assertEqual(self.client.get('/api/manifest/nv/khong-ai-ca').status_code, 404)

    def test_info_bao_cong_https_khi_co(self):
        os.environ.pop('HTTPS_PORT', None)
        self.assertIsNone(self.client.get('/api/info').json()['https_port'])
        os.environ['HTTPS_PORT'] = '8443'
        self.addCleanup(os.environ.pop, 'HTTPS_PORT', None)
        self.assertEqual(self.client.get('/api/info').json()['https_port'], 8443)


if __name__ == '__main__':
    unittest.main()
