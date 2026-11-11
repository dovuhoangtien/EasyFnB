"""Chấm kết quả của easyfnb_test.py theo đáp án người gán (dap_an.json).

    python danh_gia/cham_diem.py out/            # đọc out/<clip>/su_kien.json
    python danh_gia/cham_diem.py out/ --ten v2   # lưu điểm vào danh_gia/diem_v2.json

In ra:
- Trạng thái bàn: tỉ lệ khung đúng (T trống, C có khách, D cần dọn), và lỗi theo từng loại.
- Giơ tay: bắt được bao nhiêu lần giơ tay thật, báo nhầm bao nhiêu, trễ bao lâu.
"""
import argparse
import json
from bisect import bisect_right
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(out, clip):
    f = out / clip / 'su_kien.json'
    return json.loads(f.read_text(encoding='utf-8')) if f.exists() else None


def score_tables(gt, out, lag=0.5):
    """Chấm chặt (đúng tại đúng mốc) và chấm cho phép trễ `lag` giây (máy đổi đúng trạng thái
    trong vòng `lag` giây sau mốc). Clip 01 là time-lapse nên 0,5 s ở đây là 15-30 s ngoài đời."""
    total, ok, ok_lag = 0, 0, 0
    confusion = Counter()
    wrong = []
    for clip, g in gt.items():
        r = load(out, clip)
        if not r or not r.get('trang_thai_ban'):
            print(f'  thiếu kết quả bàn cho {clip}')
            continue
        tl = r['trang_thai_ban']['khung']
        times = [x[0] for x in tl]
        order = r['trang_thai_ban']['thu_tu']
        for t_str, codes in g['moc'].items():
            t = float(t_str)
            k = bisect_right(times, t) - 1
            pred = tl[k][1] if k >= 0 else '?' * len(order)
            for name, want in zip(g['thu_tu'], codes):
                if want == 'x':
                    continue
                j = order.index(name)
                got = pred[j]
                total += 1
                ok += got == want
                k2 = bisect_right(times, t + lag)
                ok_lag += any(tl[m][1][j] == want for m in range(max(k, 0), k2))
                confusion[(want, got)] += 1
                if got != want:
                    wrong.append(f'{clip[:2]} {t:5.2f}s {name}: đúng {want}, máy {got}')
    per = {}
    for cls in 'TCD':
        n = sum(v for (a, _), v in confusion.items() if a == cls)
        per[cls] = f"{confusion[(cls, cls)]}/{n}"
    return dict(dung=ok, tong=total, ti_le=round(ok / total, 3) if total else None, theo_loai=per,
                dung_cho_tre=ok_lag, ti_le_cho_tre=round(ok_lag / total, 3) if total else None,
                nham=dict((f'{a}->{b}', n) for (a, b), n in confusion.items() if a != b),
                chi_tiet_sai=wrong)


def score_hands(gt, out, margin=80, late=0.5):
    caught, total, latency = 0, 0, []
    tp_events, fp_events = 0, []
    missed = []
    for clip, raises in gt.items():
        if clip == 'khong_ai_gio_tay':
            continue
        r = load(out, clip)
        evs = [e for e in (r or {}).get('su_kien', []) if e['loai'] == 'goi_phuc_vu' and e.get('box')]
        used = set()
        for g in raises:
            total += 1
            hit = None
            for k, e in enumerate(evs):
                cx = (e['box'][0] + e['box'][2]) / 2
                if g['tu'] - 0.2 <= e['t'] <= g['den'] + late and g['x'][0] - margin <= cx <= g['x'][1] + margin:
                    hit = k if hit is None else hit
                    used.add(k)
            if hit is not None:
                caught += 1
                latency.append(round(evs[hit]['t'] - g['tu'], 2))
            else:
                missed.append(f"{clip[:2]} {g['ai']} ({g['kho']})")
        tp_events += len(used)
        fp_events += [f"{clip[:2]} {e['t']}s x={int((e['box'][0] + e['box'][2]) / 2)}"
                      for k, e in enumerate(evs) if k not in used]
    for clip in gt.get('khong_ai_gio_tay', []):
        r = load(out, clip)
        fp_events += [f"{clip[:2]} {e['t']}s" for e in (r or {}).get('su_kien', []) if e['loai'] == 'goi_phuc_vu']
    n_ev = tp_events + len(fp_events)
    return dict(bat_duoc=caught, tong=total, recall=round(caught / total, 3) if total else None,
                bao_dung=tp_events, bao_nham=len(fp_events),
                precision=round(tp_events / n_ev, 3) if n_ev else None,
                tre_tb_s=round(sum(latency) / len(latency), 2) if latency else None,
                tre_tung_lan=latency, bo_sot=missed, chi_tiet_nham=fp_events)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out', type=Path)
    ap.add_argument('--ten', default=None, help='tên lần chạy, lưu điểm vào danh_gia/diem_<ten>.json')
    args = ap.parse_args()
    gt = json.loads((HERE / 'dap_an.json').read_text(encoding='utf-8'))
    tb = score_tables(gt['ban'], args.out)
    hd = score_hands(gt['gio_tay'], args.out)
    print(f"Trạng thái bàn: đúng {tb['dung']}/{tb['tong']} = {tb['ti_le']:.0%} (chấm chặt), "
          f"{tb['dung_cho_tre']}/{tb['tong']} = {tb['ti_le_cho_tre']:.0%} (cho trễ 0,5 s)   "
          f"theo loại, chấm chặt (trống T, có khách C, cần dọn D): {tb['theo_loai']}   nhầm: {tb['nham']}")
    for w in tb['chi_tiet_sai']:
        print('    ' + w)
    print(f"Giơ tay: bắt {hd['bat_duoc']}/{hd['tong']} (recall {hd['recall']}), "
          f"báo đúng {hd['bao_dung']}, báo nhầm {hd['bao_nham']} (precision {hd['precision']}), "
          f"trễ trung bình {hd['tre_tb_s']} s {hd['tre_tung_lan']}")
    for m in hd['bo_sot']:
        print('    sót: ' + m)
    for m in hd['chi_tiet_nham']:
        print('    nhầm: ' + m)
    if args.ten:
        (HERE / f'diem_{args.ten}.json').write_text(
            json.dumps(dict(ban=tb, gio_tay=hd), ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
