#!/usr/bin/env python
"""Thử các biến thể bộ trạng thái bàn trên dữ liệu đã ghi (không chạy model), so với Table cũ.

    python thu_nghiem/trang_thai_ban/bien_the.py              # chạy hết, ghi ket_qua.json
    python thu_nghiem/trang_thai_ban/bien_the.py --nhanh      # bỏ phần thử nhiễu giả (nhanh hơn)

Bốn nhóm số đo cho mỗi biến thể:
1. Clip có đáp án (01 time-lapse, 02): đúng chặt / cho trễ 0,5 s, số lần đổi trạng thái so với số lần
   đổi thật, đổi thừa, đổi bị sót, sự kiện thừa, khach_moi thừa, đoạn trạng thái quá ngắn.
2. Ba clip quay thường khách ngồi suốt (06, 07, 09; vùng bàn vẽ thô trong vung_ban_them.json):
   mọi sự kiện đều là báo nhầm.
3. Nhiễu giả trên các bàn có khách suốt (02, 06, 07, 09): chèn những lần mất người 1-4 s; và một bàn
   trống giả có người đứng tạm 0,5-3 s. Đếm sự kiện nhầm.
4. Độ trễ trên tín hiệu sạch giả (thời gian thật): khách tới, khách đi để lại đồ, nhân viên dọn.
"""
import argparse
import json
import time

import numpy as np

from ban_moi import BanMoi, MAC_DINH
from phat_lai import (HERE, VT, LABELLED, TableCu, load_json, load_run, people_on_tables, table_obs, replay,
                      score_states, change_metrics, event_metrics, short_segments)

GT = load_json(VT / 'danh_gia' / 'dap_an.json')['ban']
EXTRA_Z = load_json(HERE / 'vung_ban_them.json')
EXTRA = [k for k in EXTRA_Z if k != 'ghi_chu']
TOC01 = 30.0  # clip 01: 0,5 s video = 15-30 s ngoài đời -> 30-60 lần; lấy 30 (cận dưới, bất lợi nhất cho thời gian giữ)

_CACHE = {}


def data(out, clip, anchor='cu'):
    key = (out, clip, anchor)
    if key not in _CACHE:
        run = load_run(VT / out, clip, zones=EXTRA_Z if clip in EXTRA else None)
        obs = _CACHE.get((out, clip, 'obs')) or table_obs(run)
        _CACHE[(out, clip, 'obs')] = obs
        n, who = people_on_tables(run, anchor)
        _CACHE[key] = (run, obs, n, who)
    return _CACHE[key]


def maker(params, toc):
    if params is None:
        return TableCu
    return lambda name, pts: BanMoi(name, pts, **dict(params, toc=toc))


def subset_gt(g, names):
    idx = [g['thu_tu'].index(n) for n in names]
    return dict(thu_tu=names, moc={t: ''.join(c[i] for i in idx) for t, c in g['moc'].items()})


def eval_labelled(params, out='out_v4', anchor='cu', toc01=TOC01, tables=None):
    tot = dict(dung=0, dung_tre=0, tong=0, doi_may=0, doi_that=0, doi_thua=0, bo_sot=0,
               su_kien=0, su_kien_can=0, khach_moi=0, khach_moi_thua=0, ngan=0)
    detail = {}
    for clip in LABELLED:
        run, obs, n, who = data(out, clip, anchor)
        toc = toc01 if clip.startswith('01') else 1.0
        tl, ev = replay(run, maker(params, toc), n_by_table=n, obs=obs, who=who)
        g = GT[clip]
        if tables is not None:
            names = [x for x in g['thu_tu'] if (clip, x) in tables]
            if not names:
                continue
            g = subset_gt(g, names)
            ev = [e for e in ev if e['ban'] in names]
        s = score_states(tl, run['order'], g)
        c = change_metrics(tl, run['order'], g)
        e = event_metrics(ev, g, run['frames'][-1]['t'])
        min_s = 0.25 if clip.startswith('01') else 2.0  # đoạn ngắn hơn khoảng giữa hai mốc đáp án (01) / 2 s (02)
        idx = [run['order'].index(x) for x in g['thu_tu']]
        tl_sub = [[t, ''.join(codes[i] for i in idx)] for t, codes in tl]
        ngan = short_segments(tl_sub, g['thu_tu'], min_s)
        for k in ('dung', 'dung_tre', 'tong'):
            tot[k] += s[k]
        for k in ('doi_may', 'doi_that', 'doi_thua', 'bo_sot'):
            tot[k] += c[k]
        for k in ('su_kien', 'su_kien_can', 'khach_moi', 'khach_moi_thua'):
            tot[k] += e[k]
        tot['ngan'] += ngan
        detail[clip] = dict(sai=s['sai'], su_kien=[(x['t'], x['loai'], x['ban']) for x in ev])
    tot['su_kien_thua'] = tot['su_kien'] - tot['su_kien_can']
    return tot, detail


def eval_static(params, out='out_v4', anchor='cu'):
    """Clip quay thường, khách ngồi suốt: số sự kiện (đều là nhầm) và số khach_moi."""
    ev_all, km = 0, 0
    names = []
    for clip in EXTRA:
        run, obs, n, who = data(out, clip, anchor)
        tl, ev = replay(run, maker(params, 1.0), n_by_table=n, obs=obs, who=who)
        ev_all += len(ev)
        km += sum(e['loai'] == 'khach_moi' for e in ev)
        names += [f"{clip[:2]} {e['t']} {e['loai']} {e['ban']}" for e in ev]
    return dict(su_kien_nham=ev_all, khach_moi_nham=km, chi_tiet=names)


# ---------------------------------------------------------------- nhiễu giả

def bursts(T, fps, rng, rate, dmin, dmax):
    """Mặt nạ các khung bị chèn nhiễu: số lần ~ Poisson(rate*T), mỗi lần dài U(dmin, dmax) giây."""
    N = int(T * fps)
    m = np.zeros(N, bool)
    for _ in range(rng.poisson(rate * T)):
        s = rng.uniform(0, T)
        d = rng.uniform(dmin, dmax)
        m[int(s * fps):int((s + d) * fps)] = True
    return m


class _Run:
    pass


def stress_tables(out='out_v4'):
    """Các bàn quay thường có khách suốt clip: (run, tên bàn, n, obs)."""
    res = []
    for clip in ['02_quan_ngoai_troi_nhieu_ban'] + EXTRA:
        run, obs, n, who = data(out, clip, 'cu')
        for name in run['order']:
            res.append((run, name, n[name], obs[name]))
    return res


def run_single(params, run, name, n, ob, toc=1.0):
    """Chạy một bàn đơn lẻ với n, quan sát cho trước. Trả (timeline mã trạng thái, sự kiện)."""
    tb = maker(params, toc)(name, run['tables'][name])
    has_pd = any(v is not None for v in ob['pd'])
    evs, states = [], []
    for i, f in enumerate(run['frames']):
        d = ob['pd'][i] if has_pd else None
        for kind, _ in tb.update(f['t'], int(n[i]), d, run['win'], cover=float(ob['cover'][i]), visitors=None):
            evs.append((f['t'], kind))
        states.append(tb.state)
    return states, evs


def eval_stress(params, seeds=20, out='out_v4'):
    """(1) Mất người giả 1-4 s, trung bình 1 lần mỗi 15 s, trên bàn có khách suốt clip.
    (2) Bàn trống giả (lấy bàn trên, đặt n = 0) có người đứng tạm 0,5-3 s, trung bình 1 lần mỗi 15 s."""
    tabs = stress_tables(out)
    ev_drop = ev_phantom = 0
    minutes = 0.0
    for seed in range(seeds):
        rng = np.random.default_rng(seed)
        for run, name, n, ob in tabs:
            T = len(run['frames']) / run['fps']
            minutes += T / 60
            m = bursts(T, run['fps'], rng, 1 / 15, 1.0, 4.0)[:len(n)]
            n1 = n.copy()
            n1[:len(m)][m] = 0
            _, evs = run_single(params, run, name, n1, ob)
            ev_drop += len(evs)
            m2 = bursts(T, run['fps'], rng, 1 / 15, 0.5, 3.0)[:len(n)]
            n2 = np.zeros_like(n)
            n2[:len(m2)][m2] = 1
            ob2 = dict(pd=[None] * len(n), do=ob['do'], cover=np.zeros(len(n)), has_pd=False)
            _, evs2 = run_single(params, run, name, n2, ob2)
            ev_phantom += sum(k == 'khach_moi' for _, k in evs2)
    return dict(su_kien_nham_moi_phut=round(ev_drop / minutes, 3),
                khach_moi_ao_moi_phut=round(ev_phantom / minutes, 3))


# ---------------------------------------------------------------- độ trễ trên tín hiệu sạch

def eval_latency(params):
    """Video thường 30 khung/s, win 1 s, model bàn mỗi 4 khung. Kịch bản (giây):
    0-10 bàn trống sạch; 10 khách ngồi; 10-15 đồ ăn dần bày ra (độ bẩn 0,2 -> 0,8); 20 khách đi, để lại đồ;
    30-40 nhân viên đứng ở bàn dọn (che 50% bàn), đồ hết lúc 38; 60 hết."""
    fps, T = 30, 60.0
    run = _Run()
    times = np.arange(int(T * fps)) / fps
    frames = [dict(t=t) for t in times]
    n = ((times >= 10) & (times < 20)).astype(int)
    pd = np.where(times < 10, 0.1, np.where(times < 15, 0.2 + 0.6 * (times - 10) / 5, np.where(times < 38, 0.8, 0.1)))
    cover = np.where(n > 0, 0.6, np.where((times >= 30) & (times < 40), 0.5, 0.0))
    visitors = [[(99, True, False)] if 30 <= t < 40 else [] for t in times]
    tb = maker(params, 1.0)('B', [[0, 0], [1, 0], [1, 1], [0, 1]])
    evs = []
    for i, t in enumerate(times):
        d = float(pd[i]) if i % 4 == 0 else None
        for kind, _ in tb.update(t, int(n[i]), d, 1.0, cover=float(cover[i]), visitors=visitors[i]):
            evs.append((round(t, 2), kind))
    first = lambda k, after: next((t for t, kk in evs if kk == k and t >= after), None)
    lat = lambda t, t0: None if t is None else round(t - t0, 2)
    return dict(tre_khach_moi=lat(first('khach_moi', 10), 10), tre_khach_roi=lat(first('khach_roi', 20), 20),
                tre_can_don=lat(first('can_don', 20), 20), tre_da_don=lat(first('da_don', 30), 38),
                su_kien=evs)


# ---------------------------------------------------------------- các biến thể

def variants():
    V = {}
    V['cu (Table hiện tại)'] = None
    V['cu, viết lại (kiểm tra)'] = {}
    # a. lọc: EMA / trung vị + trễ (hysteresis)
    V['a1 EMA có khách'] = dict(loc_khach='ema', tau_khach=0.5)
    V['a2 EMA độ bẩn'] = dict(loc_ban='ema', tau_ban=0.5)
    V['a3 trễ độ bẩn 0,5/0,35'] = dict(ban_sach=0.35)
    V['a4 EMA bẩn + trễ 0,5/0,35'] = dict(loc_ban='ema', tau_ban=0.5, ban_sach=0.35)
    V['a5 trung vị bẩn + trễ 0,5/0,35'] = dict(loc_ban='trung_vi', ban_sach=0.35)
    V['a6 EMA cả hai + trễ'] = dict(loc_khach='ema', tau_khach=0.5, loc_ban='ema', tau_ban=0.5, ban_sach=0.35)
    # b. giữ lệch: vào nhanh, ra chậm (giây ngoài đời)
    V['b1 ra chậm 5 s'] = dict(giu_ra=5)
    V['b2 ra chậm 10 s'] = dict(giu_ra=10)
    V['b3 vào 1 s, ra 10 s'] = dict(giu_vao=1, giu_ra=10)
    V['b4 vào 2 s, ra 20 s'] = dict(giu_vao=2, giu_ra=20)
    # c. che bàn: bỏ phiếu độ bẩn khi bàn bị che
    V['c1 che > 30%'] = dict(che=0.3)
    V['c2 che > 50%'] = dict(che=0.5)
    V['c3 che > 70%'] = dict(che=0.7)
    V['c4 che > 50% + xét sau khi rời'] = dict(che=0.5, xet_sau_roi=True)
    # d. luật phiên
    V['d1 sạch liên tục 5 s mới đã dọn'] = dict(giu_sach=5)
    V['d2 sạch 10 s'] = dict(giu_sach=10)
    V['d3 phải có người tới bàn, sạch 5 s'] = dict(giu_sach=5, can_ghe='ai_do')
    V['d4 phải có nhân viên tới, sạch 5 s'] = dict(giu_sach=5, can_ghe='nhan_vien')
    V['d5 = d4, không ai tới thì sạch 30 s'] = dict(giu_sach=5, can_ghe='nhan_vien', giu_sach_lau=30)
    V['d6 = d3, không ai tới thì sạch 30 s'] = dict(giu_sach=5, can_ghe='ai_do', giu_sach_lau=30)
    return V


COMBOS = {
    'K1 a4+b3': dict(loc_ban='ema', tau_ban=0.5, ban_sach=0.35, giu_vao=1, giu_ra=10),
    'K2 a4+b3+d1': dict(loc_ban='ema', tau_ban=0.5, ban_sach=0.35, giu_vao=1, giu_ra=10, giu_sach=5),
    'K3 a4+b3+c4+d1': dict(loc_ban='ema', tau_ban=0.5, ban_sach=0.35, giu_vao=1, giu_ra=10, giu_sach=5,
                           che=0.5, xet_sau_roi=True),
    'K4 a6+b3+d1': dict(loc_khach='ema', tau_khach=0.5, loc_ban='ema', tau_ban=0.5, ban_sach=0.35,
                        giu_vao=1, giu_ra=10, giu_sach=5),
    'K6 a4 + vào 1 s, ra 5 s': dict(loc_ban='ema', tau_ban=0.5, ban_sach=0.35, giu_vao=1, giu_ra=5),
    'K7 a4 + vào 1 s, ra 5 s + d1': dict(loc_ban='ema', tau_ban=0.5, ban_sach=0.35, giu_vao=1, giu_ra=5, giu_sach=5),
    'K5 a4+b3+d6': dict(loc_ban='ema', tau_ban=0.5, ban_sach=0.35, giu_vao=1, giu_ra=10, giu_sach=5,
                        can_ghe='ai_do', giu_sach_lau=30),
}


def row(name, params, args, anchor='cu'):
    r = dict(ten=name, tham_so=params, neo=anchor)
    lab, det = eval_labelled(params, 'out_v4', anchor)
    r['v4'] = lab
    r['v4_chi_tiet'] = det
    r['v3'] = eval_labelled(params, 'out_v3', anchor)[0]
    r['toc60'] = eval_labelled(params, 'out_v4', anchor, toc01=60.0)[0]
    r['tinh'] = eval_static(params, 'out_v4', anchor)
    if not args.nhanh:
        r['nhieu'] = eval_stress(params, seeds=args.seeds)
    r['tre'] = {k: v for k, v in eval_latency(params).items() if k != 'su_kien'}
    return r


def fmt(r):
    a, b = r['v4'], r['v3']
    s = (f"{r['ten']:<38} v4 {a['dung']:>3}/{a['tong']} tre {a['dung_tre']:>3} | đổi {a['doi_may']:>2} (thật {a['doi_that']}, "
         f"thừa {a['doi_thua']}, sót {a['bo_sot']}) ngắn {a['ngan']} | sk {a['su_kien']} (cần {a['su_kien_can']}) "
         f"KMthừa {a['khach_moi_thua']} || v3 {b['dung']}/{b['dung_tre']} thừa {b['doi_thua']} "
         f"|| tĩnh sk {r['tinh']['su_kien_nham']} KM {r['tinh']['khach_moi_nham']}")
    if 'nhieu' in r:
        s += f" || nhiễu {r['nhieu']['su_kien_nham_moi_phut']}/ph, KMảo {r['nhieu']['khach_moi_ao_moi_phut']}/ph"
    t = r['tre']
    s += f" || trễ vào {t['tre_khach_moi']} ra {t['tre_khach_roi']} dọn {t['tre_da_don']}"
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--nhanh', action='store_true')
    ap.add_argument('--seeds', type=int, default=20)
    ap.add_argument('--ghi', default=str(HERE / 'ket_qua.json'))
    args = ap.parse_args()
    t0 = time.time()

    # kiểm tra: BanMoi với tham số mặc định cho ra đúng Table cũ, trên mọi dump
    for out in ('out_v4', 'out_v3'):
        for clip in LABELLED + EXTRA:
            run, obs, n, who = data(out, clip, 'cu')
            for toc in (1.0, TOC01):
                a = replay(run, TableCu, n_by_table=n, obs=obs, who=who)
                b = replay(run, maker({}, toc), n_by_table=n, obs=obs, who=who)
                assert a == b, (out, clip)
    print('BanMoi (mặc định) == Table cũ trên mọi clip: OK')

    rows = []
    for name, p in list(variants().items()) + list(COMBOS.items()):
        rows.append(row(name, p, args))
        print(fmt(rows[-1]), flush=True)
    # e. gắn người vào bàn bằng khung người (không có khung xương trong dump)
    for anc, lab in (('trong', 'e1 điểm neo trong bàn (nới 0,15h)'), ('phu', 'e2 khung người phủ >= 15% bàn')):
        rows.append(row(lab, None, args, anchor=anc))
        print(fmt(rows[-1]), flush=True)
    Path_ = HERE / 'ket_qua.json'
    Path_.write_text(json.dumps(rows, ensure_ascii=False, indent=1, default=str), encoding='utf-8')
    print(f'xong trong {time.time() - t0:.0f} s, ghi {Path_}')


if __name__ == '__main__':
    main()
