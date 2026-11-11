"""Chấm báo "khách giơ tay gọi" theo từng sự kiện, trên dữ liệu tự quay đã gán nhãn.

    # 1. chạy pipeline trên các phiên đã quay (mỗi phiên một thư mục trong du_lieu_quay/)
    python easyfnb_test.py du_lieu_quay/ --out out_quay --no-video ...
    # 2. chấm
    python danh_gia/cham_su_kien.py out_quay                    # đọc nhãn trong du_lieu_quay/
    python danh_gia/cham_su_kien.py out_v4 --dap-an-cu          # bộ 11 clip cũ (danh_gia/dap_an.json)
    python danh_gia/cham_su_kien.py out_quay --ten v4           # lưu vào danh_gia/su_kien_v4.json

Đo những gì nhân viên cảm nhận được:
- Bắt được bao nhiêu lần gọi (kèm khoảng tin cậy 95%), chia theo loại gọi, loại ghế, người, cỡ người.
- Trễ: từ lúc tay lên đỉnh (nhãn S) tới lúc máy báo.
- Báo nhầm mỗi giờ, và báo nhầm do cử chỉ nào (vuốt tóc 2/40 lần...). Không báo nhầm lần nào trong T giờ
  chỉ cho biết tỉ lệ thật dưới khoảng 3/T mỗi giờ (quy tắc số 3).
- Báo trùng: một lần gọi mà máy báo nhiều lần.
"""
import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / 'quay'))
from cu_chi import LA_GOI  # noqa: E402

BO_QUA_VO_TAY = (-1.0, 3.0)  # quanh lúc vỗ tay đồng bộ: không tính


def wilson(k, n, z=1.96):
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return round(max(0.0, c - h), 3), round(min(1.0, c + h), 3)


def co_nguoi(h):
    return 'nhỏ (<120 px)' if h < 120 else 'vừa (120-250 px)' if h < 250 else 'to (>250 px)'


def doc_quay(du_lieu):
    """Các phiên tự quay: [(tên video, nhãn, (từ giây, đến giây) cần chấm, loại phiên)]."""
    phien = []
    for f in sorted(du_lieu.glob('*/phien.json')):
        p = json.loads(f.read_text(encoding='utf-8'))
        nf = f.parent / 'nhan.json'
        n = json.loads(nf.read_text(encoding='utf-8')) if nf.exists() else None
        if n is None and p.get('loai') != 'binh_thuong':
            print(f'  bỏ qua {f.parent.name}: chưa gán nhãn (chưa có nhan.json)')
            continue
        n = n or dict(su_kien=[], vo_tay_s=None, video=p.get('video'))
        nhap = sum(e['trang_thai'] == 'nhap' for e in n['su_kien'])
        if nhap:
            print(f'  {f.parent.name}: còn {nhap} sự kiện nháp chưa xác nhận, không tính')
        ghe = p.get('ghe', {})
        labels = []
        for e in n['su_kien']:
            if e['trang_thai'] != 'ok':
                continue
            g = ghe.get(e['ghe'], {})
            labels.append(dict(loai=e['loai'], la_goi=LA_GOI[e['loai']], ghe=e['ghe'],
                               nguoi=e.get('nguoi') or g.get('nguoi', '?'), loai_ghe=g.get('loai', '?'),
                               tu=e['tu'], dinh=e['dinh'], den=e['den'], x=e['x'], y=e['y'], box=e['box'],
                               xr=None))
        v0 = n.get('vo_tay_s')
        dai = p.get('da_chay_s') or p.get('thoi_luong_s')
        cua_so = (v0 + BO_QUA_VO_TAY[1], v0 + dai) if v0 is not None and dai else None
        ten = Path(n.get('video') or p.get('video') or f'{f.parent.name}.mp4').stem
        phien.append(dict(ten=ten, nhan=labels, cua_so=cua_so, vo_tay=v0, loai=p.get('loai', 'lenh')))
    return phien


def doc_cu():
    """Bộ 11 clip cũ: mỗi lần giơ tay có khoảng x (pixel) và thời gian, không có đỉnh riêng."""
    gt = json.loads((HERE / 'dap_an.json').read_text(encoding='utf-8'))['gio_tay']
    phien = []
    for clip, raises in gt.items():
        if clip == 'khong_ai_gio_tay':
            continue
        labels = [dict(loai='goi_mot_tay', la_goi=True, ghe=g['ai'], nguoi=g['ai'], loai_ghe=g['kho'],
                       tu=g['tu'], dinh=g['tu'], den=g['den'], x=None, y=None, box=None, xr=g['x'])
                  for g in raises]
        phien.append(dict(ten=clip, nhan=labels, cua_so=None, vo_tay=None, loai='lenh'))
    for clip in gt.get('khong_ai_gio_tay', []):
        phien.append(dict(ten=clip, nhan=[], cua_so=None, vo_tay=None, loai='binh_thuong'))
    return phien


def khop(e, L, truoc, sau, le, le_x):
    if not (L['tu'] - truoc <= e['t'] <= L['den'] + sau):
        return False
    x1, y1, x2, y2 = e['box']
    if L['xr'] is not None:
        cx = (x1 + x2) / 2
        return L['xr'][0] - le_x <= cx <= L['xr'][1] + le_x
    w, h = x2 - x1, y2 - y1
    if L['box']:
        # nhãn có khung: khung báo phải chồng đủ lên khung nhãn, hoặc tâm nằm trong khung nhãn.
        # (Không dùng "điểm nhãn nằm trong khung báo": người ngồi trước to, khung trùm lên người phía sau.)
        bx1, by1, bx2, by2 = L['box']
        bw, bh = bx2 - bx1, by2 - by1
        ix = max(0.0, min(x2, bx2) - max(x1, bx1))
        iy = max(0.0, min(y2, by2) - max(y1, by1))
        iou = ix * iy / (w * h + bw * bh - ix * iy)
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        return iou >= 0.2 or (bx1 - le * bw <= cx <= bx2 + le * bw and by1 - le * bh <= cy <= by2 + le * bh)
    # nhãn chỉ có một điểm: điểm nằm trong khung báo và không quá xa tâm khung
    inside = x1 - le * w <= L['x'] <= x2 + le * w and y1 - le * h <= L['y'] <= y2 + le * h
    return inside and xa(e, L) < 0.75


def xa(e, L):
    """Độ lệch vị trí giữa người được báo và người trong nhãn (tính theo cỡ người), để khi nhiều người
    giơ tay gần nhau, mỗi lần báo được tính cho đúng người gần nhất."""
    x1, y1, x2, y2 = e['box']
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    if L['xr'] is not None:
        return abs(cx - (L['xr'][0] + L['xr'][1]) / 2) / max(1.0, L['xr'][1] - L['xr'][0])
    lx, ly = ((L['box'][0] + L['box'][2]) / 2, (L['box'][1] + L['box'][3]) / 2) if L['box'] else (L['x'], L['y'])
    return math.hypot(cx - lx, cy - ly) / max(1.0, y2 - y1)


def cham(ket_qua, phien, truoc, sau, le, le_x):
    pos = []          # mỗi lần gọi thật: dict(nhãn, bắt được?, trễ)
    nham = []         # mỗi lần báo nhầm: dict(phiên, t, do)
    trung = 0
    gio, gio_bt = 0.0, 0.0
    am_dem = Counter()
    thieu = []
    for p in phien:
        f = ket_qua / p['ten'] / 'su_kien.json'
        if not f.exists():
            thieu.append(p['ten'])
            continue
        r = json.loads(f.read_text(encoding='utf-8'))
        a, b = p['cua_so'] or (0.0, r['do_dai_s'])
        b = min(b, r['do_dai_s'])
        gio += max(0.0, b - a) / 3600
        if p['loai'] == 'binh_thuong':
            gio_bt += max(0.0, b - a) / 3600
        evs = sorted((e for e in r['su_kien'] if e['loai'] == 'goi_phuc_vu' and e.get('box')),
                     key=lambda e: e['t'])
        labels = p['nhan']
        for L in labels:
            if not L['la_goi']:
                am_dem[L['loai']] += 1
        bat = {}  # chỉ số nhãn -> thời điểm báo đầu tiên
        for e in evs:
            if not (a <= e['t'] <= b):
                continue
            ung = [k for k, L in enumerate(labels) if khop(e, L, truoc, sau, le, le_x)]
            goi = [k for k in ung if labels[k]['la_goi']]
            if goi:
                k = min(goi, key=lambda k: (round(xa(e, labels[k]), 1), abs(labels[k]['dinh'] - e['t'])))
                if k in bat:
                    trung += 1
                else:
                    bat[k] = e['t']
            else:
                do = labels[min(ung, key=lambda k: xa(e, labels[k]))]['loai'] if ung else 'không rõ'
                nham.append(dict(phien=p['ten'], t=e['t'], do=do, bt=p['loai'] == 'binh_thuong',
                                 x=int((e['box'][0] + e['box'][2]) / 2)))
        for k, L in enumerate(labels):
            if L['la_goi']:
                cao = (L['box'][3] - L['box'][1]) if L['box'] else None
                pos.append(dict(phien=p['ten'], loai=L['loai'], ghe=L['ghe'], nguoi=L['nguoi'],
                                loai_ghe=L['loai_ghe'], cao=cao, bat=k in bat,
                                tre_dinh=round(bat[k] - L['dinh'], 2) if k in bat else None,
                                tre_tu=round(bat[k] - L['tu'], 2) if k in bat else None,
                                t=L['tu']))
    return pos, nham, trung, gio, gio_bt, am_dem, thieu


def tom_tat(pos, nham, trung, gio, gio_bt, am_dem):
    n, k = len(pos), sum(p['bat'] for p in pos)
    tre = sorted(p['tre_dinh'] for p in pos if p['bat'])

    def pv(q):
        return tre[min(len(tre) - 1, int(q * len(tre)))] if tre else None

    def nhom(key):
        g = defaultdict(lambda: [0, 0])
        for p in pos:
            v = p[key] if key != 'cao' else (co_nguoi(p['cao']) if p['cao'] else 'không rõ')
            g[v][0] += p['bat']
            g[v][1] += 1
        return {kk: f'{a}/{b}' for kk, (a, b) in sorted(g.items())}

    n_nham = len(nham)
    nham_bt = [x for x in nham if x['bt']]
    do = Counter(x['do'] for x in nham)
    return dict(
        goi_that=n, bat_duoc=k, recall=round(k / n, 3) if n else None, ci95=wilson(k, n),
        tre_tb_s=round(sum(tre) / len(tre), 2) if tre else None, tre_trung_vi_s=pv(0.5), tre_p90_s=pv(0.9),
        theo_loai_goi=nhom('loai'), theo_loai_ghe=nhom('loai_ghe'), theo_nguoi=nhom('nguoi'), theo_co_nguoi=nhom('cao'),
        bao_trung=trung, bao_nham=n_nham, so_gio=round(gio, 3),
        nham_moi_gio=round(n_nham / gio, 2) if gio else None,
        nham_moi_gio_tran95=round(3 / gio, 2) if gio and n_nham == 0 else None,
        gio_binh_thuong=round(gio_bt, 3), nham_binh_thuong=len(nham_bt),
        nham_theo_cu_chi={c: f'{do.get(c, 0)}/{am_dem[c]}' for c in sorted(set(am_dem) | set(do) - {'không rõ'})},
        nham_khong_ro=do.get('không rõ', 0),
        bo_sot=[f"{p['phien']} {p['t']:.1f}s ghế {p['ghe']} ({p['loai']}, {p['loai_ghe']})" for p in pos if not p['bat']],
        chi_tiet_nham=[f"{x['phien']} {x['t']}s x={x['x']} do {x['do']}" for x in nham],
    )



def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('ket_qua', type=Path, help='thư mục kết quả của easyfnb_test.py')
    ap.add_argument('--du-lieu', type=Path, default=ROOT / 'du_lieu_quay')
    ap.add_argument('--dap-an-cu', action='store_true', help='chấm trên bộ 11 clip cũ thay cho dữ liệu tự quay')
    ap.add_argument('--truoc', type=float, default=0.2, help='báo sớm hơn lúc bắt đầu nhấc tay tối đa (giây)')
    ap.add_argument('--sau', type=float, default=0.5, help='báo muộn hơn lúc hạ tay tối đa (giây)')
    ap.add_argument('--le', type=float, default=0.1, help='nới khung người khi so vị trí (tỉ lệ)')
    ap.add_argument('--le-x', type=float, default=80, help='nới khoảng x của nhãn cũ (pixel)')
    ap.add_argument('--ten', default=None, help='lưu vào danh_gia/su_kien_<ten>.json')
    args = ap.parse_args()

    phien = doc_cu() if args.dap_an_cu else doc_quay(args.du_lieu)
    if not phien:
        sys.exit(f'Không có phiên nào đã gán nhãn trong {args.du_lieu}')
    pos, nham, trung, gio, gio_bt, am_dem, thieu = cham(args.ket_qua, phien, args.truoc, args.sau, args.le, args.le_x)
    for t in thieu:
        print(f'  chưa có kết quả pipeline cho {t} (thiếu {args.ket_qua / t / "su_kien.json"})')
    s = tom_tat(pos, nham, trung, gio, gio_bt, am_dem)

    ci = f" (95%: {s['ci95'][0]:.0%} đến {s['ci95'][1]:.0%})" if s['ci95'] else ''
    print(f"Gọi phục vụ: bắt {s['bat_duoc']}/{s['goi_that']}{ci}")
    print(f"  trễ từ lúc tay lên đỉnh: trung bình {s['tre_tb_s']} s, trung vị {s['tre_trung_vi_s']} s, "
          f"90% dưới {s['tre_p90_s']} s")
    for key, ten in (('theo_loai_goi', 'loại gọi'), ('theo_loai_ghe', 'loại ghế'), ('theo_co_nguoi', 'cỡ người'),
                     ('theo_nguoi', 'người')):
        print(f'  theo {ten}: ' + ', '.join(f'{k} {v}' for k, v in s[key].items()))
    tran = f" (0 lần: tỉ lệ thật dưới {s['nham_moi_gio_tran95']}/giờ)" if s['nham_moi_gio_tran95'] else ''
    print(f"Báo nhầm: {s['bao_nham']} lần trong {s['so_gio'] * 60:.1f} phút = {s['nham_moi_gio']}/giờ{tran}; "
          f"riêng phiên ăn uống bình thường: {s['nham_binh_thuong']} lần trong {s['gio_binh_thuong'] * 60:.1f} phút")
    if s['nham_theo_cu_chi']:
        print('  bị báo nhầm / số lần làm: ' + ', '.join(f'{k} {v}' for k, v in s['nham_theo_cu_chi'].items()))
    print(f"  báo nhầm không rõ do cử chỉ nào: {s['nham_khong_ro']}")
    print(f"Báo trùng (một lần gọi, máy báo nhiều lần): {s['bao_trung']}")
    for m in s['bo_sot']:
        print('    sót: ' + m)
    for m in s['chi_tiet_nham']:
        print('    nhầm: ' + m)
    if args.ten:
        (HERE / f'su_kien_{args.ten}.json').write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
