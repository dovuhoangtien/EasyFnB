"""Thiết lập: việc nhờ máy camera (tìm bàn, chụp nhân viên) và ảnh nhận dạng nhân viên.

Chạy (trong easy-fnb):  python -m unittest server.tests.test_thiet_lap -v
"""
import tempfile
import unittest
from pathlib import Path

from server.hub import Hub


class NoGemini:
    enabled = False
    model = None


NV = [dict(id='lan', name='Lan', role='serve'), dict(id='huy', name='Huy', role='clean')]


class ThietLap(unittest.IsolatedAsyncioTestCase):
    def make(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        return Hub(self.dir, NoGemini())

    async def test_job_goes_to_its_camera_once_and_result_comes_back(self):
        hub = self.make()
        jid, fut = hub.new_job('cam1', 'find_tables', box=[1, 2, 3, 4])
        self.assertEqual(hub.take_jobs('cam2'), [])
        self.assertEqual(hub.take_jobs('cam1'), [dict(id=jid, kind='find_tables', box=[1, 2, 3, 4])])
        self.assertEqual(hub.take_jobs('cam1'), [])
        self.assertTrue(hub.job_result(jid, dict(tables=[])))
        self.assertEqual(await fut, dict(tables=[]))
        self.assertFalse(hub.job_result(jid, dict(tables=[])))

    def test_camera_live_only_after_a_frame(self):
        hub = self.make()
        self.assertFalse(hub.camera_live('cam1'))
        hub.edge_frame('cam1', 'live', b'\xff\xd8x')
        self.assertTrue(hub.camera_live('cam1'))

    def test_photos_survive_staff_edit_and_go_when_staff_removed(self):
        hub = self.make()
        hub.set_staff(NV)
        pid = hub.add_staff_photo('lan', 'body', 'upload')
        f = hub.staff_photo_file('lan', pid)
        f.write_bytes(b'\xff\xd8x')
        hub.staff_photos_changed()
        hub.set_staff([dict(id='lan', name='Lan Anh', role='serve'), NV[1]])
        lan = next(s for s in hub.staff_view() if s['id'] == 'lan')
        self.assertEqual([p['id'] for p in lan['photos']], [pid])
        self.assertEqual(lan['name'], 'Lan Anh')
        # mở lại máy chủ: ảnh vẫn còn trong cấu hình
        again = Hub(self.dir, NoGemini())
        self.assertEqual(next(s for s in again.staff if s['id'] == 'lan')['photos'][0]['id'], pid)
        hub.set_staff([NV[1]])
        self.assertFalse(f.exists())

    def test_refs_only_for_staff_who_agreed(self):
        hub = self.make()
        hub.set_staff(NV)
        a = hub.add_staff_photo('lan', 'body', 'upload')
        hub.add_staff_photo('huy', 'face', 'upload')
        self.assertEqual(hub.staff_refs()['refs'], [])
        hub.set_staff([dict(NV[0], consent=True), NV[1]])
        refs = hub.staff_refs()
        self.assertEqual([(r['staff'], r['id'], r['kind']) for r in refs['refs']], [('lan', a, 'body')])
        v = refs['version']
        hub.del_staff_photo('lan', a)
        self.assertNotEqual(hub.staff_refs()['version'], v)

    def test_photo_file_name_cannot_leave_the_folder(self):
        hub = self.make()
        f = hub.staff_photo_file('../../x', '..\y')
        self.assertEqual(f.parent, self.dir / 'staff')


if __name__ == '__main__':
    unittest.main()
