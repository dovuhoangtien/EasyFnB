#!/usr/bin/env python
"""Phát lại logic bàn trên chi_tiet.json (không chạy lại model nào), và chấm điểm.

    python thu_nghiem/trang_thai_ban/phat_lai.py            # kiểm tra: phát lại class Table cũ trên out_v4, out_v3
    python thu_nghiem/trang_thai_ban/phat_lai.py --out out_v4

Thư viện chung cho bien_the.py: đọc dump, tính lại người nào thuộc bàn nào, chấm trạng thái
(chặt, cho trễ), đếm đổi trạng thái thừa, sự kiện thừa, khach_moi trùng.
"""
import argparse
import json
from bisect import bisect_right
from collections import deque
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
VT = HERE.parents[1]          # thư mục vision-test
CODE = {'trong': 'T', 'co_khach': 'C', 'can_don': 'D'}
LABELLED = ['01_phong_an_goc_cao', '02_quan_ngoai_troi_nhieu_ban']


# ---------------------------------------------------------------- class Table cũ, chép nguyên từ easyfnb_test.py

class TableCu:
    def __init__(self, name, pts):
        self.name = name
        self.poly = np.array(pts, np.float32)
        self.state = None
        self.people = deque()
        self.dirty = deque()
        self.n_now = 0
        self.dirty_now = None

    def update(self, t, n, dirty_obs, win, **_):
        self.n_now = n
        self.people.append((t, n))
        while self.people and self.people[0][0] < t - win:
            self.people.popleft()
        if dirty_obs is not None:
            self.dirty.append((t, dirty_obs))
            self.dirty_now = dirty_obs
        while self.dirty and self.dirty[0][0] < t - win:
            self.dirty.popleft()
        if t - self.people[0][0] < 0.9 * win:
            return []

        occ = np.mean([k > 0 for _, k in self.people])
        dirty = bool(self.dirty) and np.mean([v for _, v in self.dirty]) >= 0.5
        heads = int(np.median([k for _, k in self.people if k > 0] or [0]))
        ev = []
        if self.state is None:
            self.state = 'co_khach' if occ >= 0.5 else ('can_don' if dirty else 'trong')
            if self.state == 'can_don':
                ev.append(('can_don', 'đầu clip đã có đồ trên bàn, không có khách'))
        elif self.state != 'co_khach' and occ >= 0.8:
            self.state = 'co_khach'
            ev.append(('khach_moi', f'{heads} người'))
        elif self.state == 'co_khach' and occ <= 0.2:
            ev.append(('khach_roi', ''))
            self.state = 'can_don' if dirty else 'trong'
            if dirty:
                ev.append(('can_don', 'còn đồ trên bàn sau khi khách đi'))
        elif self.state == 'can_don' and not dirty and occ <= 0.2:
            self.state = 'trong'
            ev.append(('da_don', ''))
        return ev


# ---------------------------------------------------------------- đọc dữ liệu

def load_json(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def nearest_table(polys, pt, scale):
    """Giống easyfnb_test.nearest_table: bàn có pointPolygonTest lớn nhất, nếu > -scale."""
    best, bd = None, -1e9
    for name, poly in polys.items():
        d = cv2.pointPolygonTest(poly, pt, True)
        if d > bd:
            best, bd = name, d
    return best if bd > -scale else None


def load_run(out_dir, clip, zones=None):
    """Đọc dump của một clip. Thời điểm t tính lại = chỉ số khung / fps (dump làm tròn 3 số lẻ).

    Trả dict: fps, win, tables {tên: polygon}, frames [dict(t, persons, ban)], events, timeline (bản chạy thật).
    Nếu clip không có bàn trong lúc chạy thật (dump ban rỗng) mà `zones` có bàn cho clip này
    (ví dụ zones tự vẽ thêm cho clip chưa gán nhãn), bàn được gán lại từ khung người như pipeline.
    """
    out_dir = Path(out_dir)
    d = load_json(out_dir / clip / 'chi_tiet.json')
    s = load_json(out_dir / clip / 'su_kien.json')
    zones = zones if zones is not None else load_json(VT / 'zones.json')
    cfg = zones.get(clip, {})
    polys = {k: np.array(v, np.float32) for k, v in cfg.get('ban', {}).items()}
    fps = d['fps']
    frames = []
    for i, f in enumerate(d['khung']):
        assert abs(f['t'] - i / fps) < 2e-3, (clip, i, f['t'])
        frames.append(dict(t=i / fps, persons=f['nguoi'], ban=f['ban']))
    run = dict(clip=clip, fps=fps, win=float(cfg.get('xac_nhan_s', d['win'])), tables=polys, frames=frames,
               events=[e for e in s['su_kien'] if e['loai'] != 'goi_phuc_vu'],
               timeline=(s.get('trang_thai_ban') or {}).get('khung'),
               order=(s.get('trang_thai_ban') or {}).get('thu_tu') or list(polys))
    run['staff'] = staff_flags(frames)
    return run


def staff_flags(frames, hold=3.0, th=0.5):
    """Tính lại cờ nhân viên của từng người từng khung như pipeline: trung bình pst trong 3 giây >= 0.5."""
    hist, out = {}, []
    for f in frames:
        t, row = f['t'], []
        for p in f['persons']:
            sq = hist.setdefault(p['id'], deque())
            if p['pst'] is not None:
                sq.append((t, p['pst']))
            while sq and sq[0][0] < t - hold:
                sq.popleft()
            row.append(bool(sq) and float(np.mean([v for _, v in sq])) >= th)
        out.append(row)
    return out


def people_on_tables(run, anchor='cu'):
    """Số người ngồi từng bàn từng khung, theo cách gắn người vào bàn.

    'cu'   : dùng đúng cột ban của dump (nearest_table, điểm neo (giữa, y1+0,6h), cách mép <= 0,45h).
    'trong': điểm neo phải nằm trong đa giác bàn nới thêm 0,15h (gần với "hông nằm trong bàn").
    'phu'  : khung người phủ ít nhất 15% diện tích bàn và điểm neo cách mép <= 0,45h.
    Trả {bàn: np.array số người}, đồng thời {bàn: list[list[(id, staff, walking)]]} người gắn với bàn.
    """
    polys = run['tables']
    n = {k: np.zeros(len(run['frames']), int) for k in polys}
    who = {k: [[] for _ in run['frames']] for k in polys}
    for i, (f, st) in enumerate(zip(run['frames'], run['staff'])):
        for p, staff in zip(f['persons'], st):
            x1, y1, x2, y2 = p['box']
            h = y2 - y1
            pt = (float((x1 + x2) / 2), float(y1 + 0.6 * h))
            if anchor == 'cu':
                tb = p['ban'] if f['ban'] else nearest_table(polys, pt, 0.45 * h)
            elif anchor == 'trong':
                tb = nearest_table(polys, pt, 0.15 * h)
            elif anchor == 'phu':
                tb = nearest_table(polys, pt, 0.45 * h)
                if tb is not None and box_cover(polys[tb], p['box']) < 0.15:
                    tb = None
            else:
                raise ValueError(anchor)
            if tb is None:
                continue
            who[tb][i].append((p['id'], staff, p['di']))
            if not p['di'] and not staff:
                n[tb][i] += 1
    return n, who


_MASK = {}


def poly_mask(poly):
    key = poly.tobytes()
    if key not in _MASK:
        x, y, w, h = cv2.boundingRect(poly.astype(np.int32))
        m = np.zeros((h + 1, w + 1), np.uint8)
        cv2.fillPoly(m, [(poly - [x, y]).astype(np.int32)], 1)
        _MASK[key] = (x, y, m.astype(bool))
    return _MASK[key]


def box_cover(poly, box):
    return cover_frac(poly, [box])


def cover_frac(poly, boxes):
    """Phần diện tích đa giác bàn bị các khung người che (hợp các khung)."""
    x, y, m = poly_mask(poly)
    if not boxes:
        return 0.0
    c = np.zeros_like(m)
    H, W = m.shape
    for x1, y1, x2, y2 in boxes:
        a, b = max(0, int(x1) - x), max(0, int(y1) - y)
        cc, dd = min(W, int(x2) - x), min(H, int(y2) - y)
        if cc > a and dd > b:
            c[b:dd, a:cc] = True
    return float((c & m).sum() / max(1, m.sum()))


def table_obs(run):
    """Quan sát từng bàn từng khung: pd (xác suất bẩn hoặc None), do (cờ đồ vật hoặc None), cover (phần bàn bị che)."""
    out = {}
    for name, poly in run['tables'].items():
        pd, do, cov = [], [], []
        for f in run['frames']:
            b = f['ban'].get(name, {})
            pd.append(b.get('pd'))
            do.append(b.get('do'))
            cov.append(cover_frac(poly, [p['box'] for p in f['persons']]))
        out[name] = dict(pd=pd, do=do, cover=np.array(cov), has_pd=any(v is not None for v in pd))
    return out


# ---------------------------------------------------------------- phát lại

def replay(run, make_table, n_by_table=None, obs=None, who=None, cfg=None):
    """Chạy bộ trạng thái bàn trên từng khung. make_table(tên, polygon) -> đối tượng có update().

    Trả timeline [(t, 'TCCD')], events [dict(t, loai, ban, chi_tiet)].
    """
    order = run['order']
    if n_by_table is None:
        n_by_table = {k: np.array([f['ban'][k]['n'] for f in run['frames']]) for k in order}
    if obs is None:
        obs = table_obs(run)
    tables = [make_table(k, run['tables'][k]) for k in order]
    timeline, events = [], []
    for i, f in enumerate(run['frames']):
        t = f['t']
        for tb in tables:
            o = obs[tb.name]
            # pipeline v3/v4 dùng model bàn: quan sát bẩn = pd (None ở khung không chạy model)
            dirty_obs = o['pd'][i] if o['has_pd'] else (
                None if o['do'][i] is None else float(o['do'][i]))
            extra = dict(cover=float(o['cover'][i]),
                         visitors=who[tb.name][i] if who is not None else None)
            for kind, detail in tb.update(t, int(n_by_table[tb.name][i]), dirty_obs, run['win'], **extra):
                events.append(dict(t=round(t, 2), loai=kind, ban=tb.name, chi_tiet=detail))
        timeline.append([round(t, 3), ''.join(CODE.get(tb.state, '?') for tb in tables)])
    return timeline, events


# ---------------------------------------------------------------- chấm điểm

def score_states(timeline, order, g, lag=0.5):
    """Như danh_gia/cham_diem.score_tables, cho một clip, trên timeline trong bộ nhớ."""
    times = [x[0] for x in timeline]
    total = ok = ok_lag = 0
    wrong = []
    for t_str, codes in g['moc'].items():
        t = float(t_str)
        k = bisect_right(times, t) - 1
        pred = timeline[k][1] if k >= 0 else '?' * len(order)
        for name, want in zip(g['thu_tu'], codes):
            if want == 'x':
                continue
            j = order.index(name)
            total += 1
            ok += pred[j] == want
            k2 = bisect_right(times, t + lag)
            ok_lag += any(timeline[m][1][j] == want for m in range(max(k, 0), k2))
            if pred[j] != want:
                wrong.append(f'{t:5.2f}s {name}: đúng {want}, máy {pred[j]}')
    return dict(dung=ok, dung_tre=ok_lag, tong=total, sai=wrong)


def segments(timeline, j):
    """Các đoạn trạng thái liên tục của bàn thứ j: [(t_bắt_đầu, t_kết_thúc, mã)], bỏ đoạn '?' đầu clip."""
    segs = []
    for t, codes in timeline:
        c = codes[j]
        if c == '?':
            continue
        if segs and segs[-1][2] == c:
            segs[-1][1] = t
        else:
            segs.append([t, t, c])
    return segs


def gt_transitions(g, name):
    """Các lần đổi trạng thái thật theo đáp án: [(t_trước, t_sau, cũ, mới)], bỏ qua mốc 'x'."""
    j = g['thu_tu'].index(name)
    pts = sorted((float(t), c[j]) for t, c in g['moc'].items())
    pts = [(t, c) for t, c in pts if c != 'x']
    return [(a[0], b[0], a[1], b[1]) for a, b in zip(pts, pts[1:]) if a[1] != b[1]], pts


def change_metrics(timeline, order, g, lag=0.5):
    """Đổi trạng thái của máy so với số lần đổi thật.

    Mỗi lần đổi thật (cũ→mới giữa hai mốc liền nhau) được khớp với lần đổi của máy sang đúng
    trạng thái mới trong khoảng [mốc trước, mốc sau + lag]. Đổi thật D→C cho phép máy đi qua T
    (đã dọn rồi khách mới ngồi). Lần đổi không khớp được là đổi thừa (nhấp nháy).
    """
    res = dict(doi_may=0, doi_that=0, doi_thua=0, bo_sot=0)
    for name in g['thu_tu']:
        j = order.index(name)
        trans, pts = gt_transitions(g, name)
        segs = segments(timeline, j)
        changes = [(segs[k][0], segs[k - 1][2], segs[k][2]) for k in range(1, len(segs))]
        res['doi_may'] += len(changes)
        res['doi_that'] += len(trans)
        used = set()
        for (ta, tb_, old, new) in trans:
            hit = [k for k, (t, o, nw) in enumerate(changes)
                   if k not in used and ta - 1e-9 <= t <= tb_ + lag and nw == new]
            if hit:
                used.add(hit[0])
                # cho phép bước trung gian hợp lý ngay trước đó trong cùng khoảng (D→T→C)
                for k in range(hit[0] - 1, -1, -1):
                    t, o, nw = changes[k]
                    if k in used or not (ta - 1e-9 <= t) or not (old == 'D' and new == 'C' and nw == 'T'):
                        break
                    used.add(k)
            else:
                res['bo_sot'] += 1
        res['doi_thua'] += len(changes) - len(used)
    return res


def event_metrics(events, g, t_end, lag=0.5):
    """Sự kiện của máy so với các phiên thật theo đáp án.

    Phiên có khách = chuỗi mốc C liền nhau (mốc x ở giữa không ngắt). Mỗi phiên bắt đầu sau đầu
    clip cần đúng 1 khach_moi; phiên có sẵn từ đầu clip cần 0. khach_moi thừa = số khach_moi
    trong phiên (từ mốc trước phiên tới mốc cuối phiên + lag) trừ số cần.
    Tổng sự kiện thừa = tổng sự kiện của máy - số sự kiện cần theo đáp án (tối thiểu).
    """
    out = dict(khach_moi=0, khach_moi_thua=0, su_kien=0, su_kien_can=0)
    for name in g['thu_tu']:
        trans, pts = gt_transitions(g, name)
        ev = [e for e in events if e['ban'] == name]
        out['su_kien'] += len(ev)
        km = [e['t'] for e in ev if e['loai'] == 'khach_moi']
        out['khach_moi'] += len(km)
        # sự kiện cần: C→D: khach_roi + can_don; C→T: khach_roi; D→T: da_don; T→C: khach_moi;
        # D→C: da_don + khach_moi (dọn rồi khách mới); đầu clip là D: can_don
        need = {('C', 'D'): 2, ('C', 'T'): 1, ('D', 'T'): 1, ('T', 'C'): 1, ('D', 'C'): 2, ('T', 'D'): 1}
        out['su_kien_can'] += sum(need[(o, n)] for *_, o, n in trans) + (pts[0][1] == 'D')
        # phiên có khách
        sess, cur = [], None
        for k, (t, c) in enumerate(pts):
            if c == 'C':
                if cur is None:
                    cur = [pts[k - 1][0] if k else -1e9, t, k == 0]
                cur[1] = t
            elif cur is not None:
                sess.append((cur[0], t, cur[2]))   # tới mốc kế tiếp không phải C
                cur = None
        if cur is not None:
            sess.append((cur[0], t_end + 1, cur[2]))
        for a, b, at_start in sess:
            cnt = sum(1 for t in km if a - 1e-9 <= t <= b + lag)
            out['khach_moi_thua'] += max(0, cnt - (0 if at_start else 1))
    out['su_kien_thua'] = out['su_kien'] - out['su_kien_can']
    return out


def short_segments(timeline, order, min_s):
    """Số đoạn trạng thái ở giữa clip ngắn hơn min_s giây (nhấp nháy, ví dụ can_don rồi da_don ngay)."""
    cnt = 0
    for j in range(len(order)):
        segs = segments(timeline, j)
        dt = np.diff([s[0] for s in segs]) if len(segs) > 1 else []
        cnt += sum(1 for k in range(1, len(segs) - 1) if dt[k] < min_s)
    return cnt


# ---------------------------------------------------------------- kiểm tra phát lại

def check(out_dir):
    gt = load_json(VT / 'danh_gia' / 'dap_an.json')['ban']
    for clip in LABELLED:
        run = load_run(VT / out_dir, clip)
        tl, ev = replay(run, TableCu)
        real = run['timeline']
        diff = [(a[0], a[1], b[1]) for a, b in zip(tl, real) if a[1] != b[1]]
        ev_real = [(e['t'], e['loai'], e['ban']) for e in run['events']]
        ev_mine = [(e['t'], e['loai'], e['ban']) for e in ev]
        sc = score_states(tl, run['order'], gt[clip])
        sc_real = score_states(real, run['order'], gt[clip])
        print(f'{out_dir} {clip}: {len(tl)} khung, khác bản chạy thật {len(diff)} khung; '
              f'sự kiện giống: {ev_real == ev_mine} ({len(ev_mine)} sự kiện); '
              f'điểm phát lại {sc["dung"]}/{sc["tong"]} chặt, {sc["dung_tre"]} cho trễ; '
              f'bản thật {sc_real["dung"]}/{sc_real["tong"]}, {sc_real["dung_tre"]}')
        for x in diff[:10]:
            print('   khác:', x)
        if ev_real != ev_mine:
            print('   thật :', ev_real)
            print('   phát lại:', ev_mine)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', nargs='+', default=['out_v4', 'out_v3'])
    a = ap.parse_args()
    for o in a.out:
        check(o)


if __name__ == '__main__':
    main()
