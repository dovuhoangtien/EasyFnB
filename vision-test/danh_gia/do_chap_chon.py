"""Đo độ chập chờn từ chi_tiet.json (chạy easyfnb_test.py với --dump).

    python danh_gia/do_chap_chon.py out_x [out_y ...]

In cho từng clip và tổng: số lần nhãn nhân viên đổi qua lại trên cùng một người (mỗi phút-người),
số track sinh ra so với số người trung bình (đứt track), số lần số khách của một bàn đổi (mỗi phút-bàn),
và số sự kiện bàn. Số càng nhỏ càng ổn định. Đây là độ ổn định, không phải độ đúng.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path


def do(clip_dir):
    f = clip_dir / 'chi_tiet.json'
    if not f.exists():
        return None
    d = json.loads(f.read_text(encoding='utf8'))
    fr = d['khung'] if isinstance(d, dict) else d
    if not fr:
        return None
    dur = fr[-1]['t'] - fr[0]['t']
    tr = defaultdict(list)
    for k in fr:
        for p in k['nguoi']:
            tr[p['id']].append((k['t'], p.get('nv'), p.get('di'), p.get('ban')))
    nv_doi = di_doi = ban_doi = 0
    phut_nguoi = 0.0
    lan_lon = 0
    for xs in tr.values():
        phut_nguoi += (xs[-1][0] - xs[0][0]) / 60
        nv = [x[1] for x in xs]
        nv_doi += sum(a != b for a, b in zip(nv, nv[1:]))
        di = [x[2] for x in xs]
        di_doi += sum(a != b for a, b in zip(di, di[1:]))
        bn = [x[3] for x in xs]
        ban_doi += sum(a != b for a, b in zip(bn, bn[1:]))
        lan_lon += 0 < sum(nv) < len(nv)
    n_doi = 0
    bans = list(fr[0].get('ban') or {})
    for b in bans:
        ns = [k['ban'][b].get('nh', k['ban'][b]['n']) for k in fr if b in k.get('ban', {})]
        n_doi += sum(a != c for a, c in zip(ns, ns[1:]))
    tb = sum(len(k['nguoi']) for k in fr) / len(fr)
    return dict(clip=clip_dir.name, giay=round(dur, 1), nguoi_tb=round(tb, 1), track=len(tr),
                track_moi_nguoi=round(len(tr) / max(tb, 0.1), 1),
                nv_doi=nv_doi, nv_doi_phut=round(nv_doi / max(phut_nguoi, 1e-6), 1), track_lan_nhan=lan_lon,
                di_doi_phut=round(di_doi / max(phut_nguoi, 1e-6), 1),
                ban_doi_phut=round(ban_doi / max(phut_nguoi, 1e-6), 1),
                so_ban=len(bans), n_doi_phut_ban=round(n_doi / max(dur / 60 * max(len(bans), 1), 1e-6), 1) if bans else None)


for root in sys.argv[1:]:
    print('==', root)
    for c in sorted(Path(root).iterdir()):
        if c.is_dir() and (r := do(c)):
            print('  ', r)
