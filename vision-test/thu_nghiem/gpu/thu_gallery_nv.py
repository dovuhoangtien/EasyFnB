"""T3: nhân viên theo gallery đăng ký đầu ca + nhãn dính + sự kiện "nhân viên tới bàn".

    python thu_nghiem/gpu/thu_gallery_nv.py thu_nghiem/gpu/out_b0_nhay --nhan thu_nghiem/gpu/nv_that.json

Đọc khung_xuong.npz (box, pst từng track từng khung) của clip 06, 07 (có nhân viên) và 02, 09 (chỉ khách),
đọc lại khung ảnh từ video, cắt phần giữa box (60% ngang x 70% cao từ trên), mã hoá bằng CLIP B/32 và
PE-Core B/16. Gallery = ảnh cắt của track nhân viên trong 2 s đầu track đó xuất hiện (giả lập "đăng ký đầu ca");
kho khách = ảnh cắt của clip chỉ có khách (02, 09; khi chấm chính 02/09 thì bỏ clip đó khỏi kho).
Điểm ảnh = giống nhất với gallery − giống nhất với kho khách. So với probe hiện tại (pst trung bình 3 s >= 0.5).
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
import torch

VT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(VT))
from clip_cls import ClipCls  # noqa: E402

NHAN_VIEN = ['06_phuc_vu_ghi_order', '07_khach_tinh_tien']
KHACH = ['02_quan_ngoai_troi_nhieu_ban', '09_nhom_ban_tron']
LHIP, RHIP = 11, 12


def mid_crop(frame, b):
    x1, y1, x2, y2 = b
    w, h = x2 - x1, y2 - y1
    cx = (x1 + x2) / 2
    a, c = int(max(0, cx - 0.3 * w)), int(min(frame.shape[1], cx + 0.3 * w))
    y_a, y_c = int(max(0, y1)), int(min(frame.shape[0], y1 + 0.7 * h))
    return frame[y_a:y_c, a:c]


def load_clip(out, clip, step):
    """Mỗi dòng: (t, id, box, kp, kc, pst). Ảnh cắt lấy mỗi `step` khung cho mỗi track."""
    z = np.load(out / clip / 'khung_xuong.npz')
    fps = float(z['fps'])
    frames = np.round(z['t'] * fps).astype(int)
    rows = dict(t=z['t'], id=z['id'], box=z['box'], kp=z['kp'], kc=z['kc'], pst=z['pst'], f=frames)
    want = defaultdict(list)  # khung -> chỉ số dòng cần cắt ảnh
    for k, f in enumerate(frames):
        if f % step == 0:
            want[int(f)].append(k)
    crops = {}
    cap = cv2.VideoCapture(str(VT / 'clips' / f'{clip}.mp4'))
    f = 0
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        for k in want.get(f, []):
            c = mid_crop(fr, rows['box'][k])
            if c.size and min(c.shape[:2]) >= 8:
                crops[k] = c
        f += 1
    cap.release()
    return rows, crops, fps


GAL = dict(s=2.0, cuoi=False)
KHO_CUNG = False


def in_gal(t, tid, t0, t1):
    if GAL['cuoi']:
        return t > t1[tid] - GAL['s']
    return t < t0[tid] + GAL['s']


def sticky(ps, hi=0.8, lo=0.3):
    lab, out = False, []
    for p in ps:
        if not lab and p > hi:
            lab = True
        elif lab and p < lo:
            lab = False
        out.append(lab)
    return out


def flips(labs):
    return sum(a != b for a, b in zip(labs, labs[1:]))


def rolling(ts, vs, win):
    out, j, s = [], 0, 0.0
    for i in range(len(ts)):
        s += vs[i]
        while ts[j] < ts[i] - win:
            s -= vs[j]
            j += 1
        out.append(s / (i - j + 1))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out', type=Path)
    ap.add_argument('--nhan', type=Path, required=True, help='json: {clip: [mã track nhân viên]}')
    ap.add_argument('--vung', type=Path, required=True, help='json: {clip: {bàn: polygon}} cho 06, 07')
    ap.add_argument('--toi', type=Path, default=None, help='json: {clip: [[bàn, giây nhân viên vào vùng bàn]]}')
    ap.add_argument('--step', type=int, default=3, help='cắt ảnh mỗi N khung')
    ap.add_argument('--gallery-s', type=float, default=2.0)
    ap.add_argument('--gallery-cuoi', action='store_true',
                    help='lấy gallery ở 2 s CUỐI track nhân viên (giả lập đăng ký từ trước, khác lúc chấm)')
    ap.add_argument('--kho-cung', action='store_true',
                    help='thêm vào kho khách ảnh của các khách KHÁC trong cùng clip (dùng nhãn: cận trên)')
    ap.add_argument('--k', type=float, default=0.03, help='đổi điểm về 0..1: sigmoid(điểm / k)')
    ap.add_argument('--luu', type=Path, default=None)
    args = ap.parse_args()
    global KHO_CUNG
    KHO_CUNG = args.kho_cung
    GAL.update(s=args.gallery_s, cuoi=args.gallery_cuoi)
    nv = json.loads(args.nhan.read_text(encoding='utf-8'))
    vung = json.loads(args.vung.read_text(encoding='utf-8'))
    toi = json.loads(args.toi.read_text(encoding='utf-8')) if args.toi else {}

    data = {c: load_clip(args.out, c, args.step) for c in NHAN_VIEN + KHACH}
    ket_qua = {}
    for key in ('b32_laion', 'pe_core_b16'):
        enc = ClipCls(head=None, backbone_key=key)
        feats = {}
        for c, (rows, crops, fps) in data.items():
            ks = sorted(crops)
            f = enc.features([crops[k] for k in ks]).cpu().numpy() if ks else np.zeros((0, 1))
            feats[c] = dict(zip(ks, f))
        torch.cuda.empty_cache()
        res = dict(track={}, su_kien={}, tong={})
        # gallery: track nhân viên, 2 s đầu (mỗi clip là một ca)
        gal, first = {}, {}
        for c in NHAN_VIEN:
            rows = data[c][0]
            t0, t1 = {}, {}
            for k in range(len(rows['t'])):
                t0.setdefault(int(rows['id'][k]), float(rows['t'][k]))
                t1[int(rows['id'][k])] = float(rows['t'][k])
            first[c] = (t0, t1)
            g = [v for k, v in feats[c].items() if int(rows['id'][k]) in nv.get(c, []) and in_gal(rows['t'][k], int(rows['id'][k]), t0, t1)]
            gal[c] = np.stack(g) if g else None
        all_gal = np.concatenate([g for g in gal.values() if g is not None])
        for c in NHAN_VIEN + KHACH:
            rows, crops, fps = data[c]
            G = gal.get(c, all_gal)  # clip chỉ có khách: dùng gallery của cả hai ca
            bank = np.stack([v for cc in KHACH if cc != c for v in feats[cc].values()])
            cust_same = defaultdict(list)  # kho khách CÙNG camera (dùng nhãn: cận trên, không thật)
            if KHO_CUNG and c in NHAN_VIEN:
                for k, v in feats[c].items():
                    if int(rows['id'][k]) not in nv.get(c, []):
                        cust_same[int(rows['id'][k])].append(v)
            staff_ids = set(nv.get(c, []))
            by_tr = defaultdict(list)
            for k in range(len(rows['t'])):
                by_tr[int(rows['id'][k])].append(k)
            tr_res = {}
            for tid, ks in by_tr.items():
                ks.sort(key=lambda k: rows['t'][k])
                t0 = float(rows['t'][ks[0]])
                ts, sc, pst_l, pst_t, sg, sb = [], [], [], [], [], []
                if cust_same:
                    other = [v for t2, vs in cust_same.items() if t2 != tid for v in vs]
                    bank_t = np.concatenate([bank, np.stack(other)]) if other else bank
                else:
                    bank_t = bank
                for k in ks:
                    if not np.isnan(rows['pst'][k]):
                        pst_t.append(float(rows['t'][k]))
                        pst_l.append(float(rows['pst'][k]))
                    if k not in feats[c]:
                        continue
                    if c in NHAN_VIEN and tid in staff_ids and in_gal(rows['t'][k], tid, *first[c]):
                        continue  # phần đã dùng làm gallery: không chấm
                    f = feats[c][k]
                    sg.append(float(np.max(G @ f)))
                    sb.append(float(np.max(bank_t @ f)))
                    s = sg[-1] - sb[-1]
                    ts.append(float(rows['t'][k]))
                    sc.append(1 / (1 + np.exp(-s / args.k)))
                if not ts:
                    continue
                avg = rolling(ts, sc, 1.0)
                gl = sticky(avg)
                pr = [m >= 0.5 for m in rolling(pst_t, pst_l, 3.0)] if pst_t else []
                tr_res[tid] = dict(that='nv' if tid in staff_ids else 'khach', n=len(ts),
                                   dai_s=round(ts[-1] - t0, 1),
                                   gallery_cuoi=bool(gl[-1]), gallery_tb=round(float(np.mean(sc)), 3),
                                   sim_gallery=round(float(np.mean(sg)), 3), sim_kho=round(float(np.mean(sb)), 3),
                                   gallery_ti_le_nv=round(float(np.mean(gl)), 2), gallery_doi=flips(gl),
                                   probe_cuoi=bool(pr[-1]) if pr else None,
                                   probe_ti_le_nv=round(float(np.mean(pr)), 2) if pr else None,
                                   probe_doi=flips(pr), _ts=ts, _gl=gl, _pt=pst_t, _pr=pr)
            res['track'][c] = tr_res
            # sự kiện "nhân viên tới bàn": track đang mang nhãn nhân viên (gallery dính), điểm hông hoặc
            # điểm neo nằm trong polygon bàn liên tục >= 2 s
            for nguon in ('gallery', 'probe'):
              if c in vung:
                evs = []
                for tid, ks in by_tr.items():
                    lab = tr_res.get(tid)
                    if lab is None:
                        continue
                    lab_t = dict(zip(lab['_ts'], lab['_gl'])) if nguon == 'gallery' else dict(zip(lab['_pt'], lab['_pr']))
                    cur_lab, inside_since, fired = False, {}, set()
                    for k in ks:
                        t = float(rows['t'][k])
                        if t in lab_t:
                            cur_lab = lab_t[t]
                        x1, y1, x2, y2 = rows['box'][k]
                        kp, kc = rows['kp'][k], rows['kc'][k]
                        hips = [kp[j] for j in (LHIP, RHIP) if kc[j] > 0.5]
                        pts = [((x1 + x2) / 2, y1 + 0.6 * (y2 - y1))]
                        if hips:
                            pts.append(tuple(np.mean(hips, 0)))
                        for ban, poly in vung[c].items():
                            P = np.array(poly, np.float32)
                            ins = any(cv2.pointPolygonTest(P, (float(px), float(py)), False) >= 0 for px, py in pts)
                            if ins and cur_lab:
                                inside_since.setdefault(ban, t)
                                if t - inside_since[ban] >= 2.0 and ban not in fired:
                                    fired.add(ban)
                                    evs.append(dict(t=round(t, 2), ban=ban, nguoi=tid, that=lab['that']))
                            else:
                                inside_since.pop(ban, None)
                evs.sort(key=lambda e: e['t'])
                # chấm theo mốc người xem ghi (nếu có)
                gt = toi.get(c, [])
                lat = []
                for ban, t_in in gt:
                    hit = [e for e in evs if e['ban'] == ban and e['that'] == 'nv' and e['t'] >= t_in - 0.5]
                    lat.append(round(hit[0]['t'] - t_in, 2) if hit else None)
                res['su_kien'][f'{c}|{nguon}'] = dict(su_kien=evs, moc=gt, tre=lat,
                                         sai_do_khach=sum(e['that'] == 'khach' for e in evs))
        # tổng: ma trận nhầm theo track, chỉ track có >= 5 điểm chấm
        cm = defaultdict(lambda: defaultdict(int))
        for c, trs in res['track'].items():
            for tid, r in trs.items():
                if r['n'] < 5:
                    continue
                cm['gallery'][f"{r['that']}->{'nv' if r['gallery_cuoi'] else 'khach'}"] += 1
                if r['probe_cuoi'] is not None:
                    cm['probe'][f"{r['that']}->{'nv' if r['probe_cuoi'] else 'khach'}"] += 1
                cm['gallery']['doi_nhan'] += r['gallery_doi']
                cm['probe']['doi_nhan'] += r['probe_doi']
        res['tong'] = {k: dict(v) for k, v in cm.items()}
        for trs in res['track'].values():
            for r in trs.values():
                r.pop('_ts'), r.pop('_gl'), r.pop('_pt'), r.pop('_pr')
        ket_qua[key] = res
        print(f'== {key}')
        print('  tổng:', json.dumps(res['tong'], ensure_ascii=False))
        for c, trs in res['track'].items():
            for tid, r in sorted(trs.items()):
                if r['that'] == 'nv' or r['gallery_ti_le_nv'] > 0 or (r['probe_ti_le_nv'] or 0) > 0:
                    print(f"  {c[:2]} #{tid:<4} thật={r['that']:<5} n={r['n']:<4} dài={r['dai_s']:<5} "
                          f"gallery: cuối={'nv' if r['gallery_cuoi'] else 'kh'} tỉ lệ nv={r['gallery_ti_le_nv']} "
                          f"đổi={r['gallery_doi']} điểm tb={r['gallery_tb']} sim gal/kho={r['sim_gallery']}/{r['sim_kho']} | probe: cuối={r['probe_cuoi']} "
                          f"tỉ lệ nv={r['probe_ti_le_nv']} đổi={r['probe_doi']}")
        for c, s in res['su_kien'].items():
            print(f"  sự kiện {c[:2]} {c.split('|')[1]}: {s['su_kien']}  mốc={s['moc']} trễ={s['tre']} sai do khách={s['sai_do_khach']}")
        del enc
        torch.cuda.empty_cache()
    if args.luu:
        args.luu.write_text(json.dumps(ket_qua, ensure_ascii=False, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
