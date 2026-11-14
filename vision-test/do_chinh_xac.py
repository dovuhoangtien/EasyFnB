#!/usr/bin/env python
"""Đo độ chính xác của camera AI trên các clip đã gán nhãn (nhan_su_kien.json), lặp lại được.

Chạy pipeline (cấu hình demo của chay_camera.bat, KHÔNG gửi máy chủ, không cửa sổ) trên từng clip, mỗi clip
một tiến trình, rồi so sự kiện với nhãn. In theo từng loại sự kiện: precision, recall, báo nhầm mỗi phút,
độ trễ, kèm số đếm; thêm trạng thái bàn theo mốc (danh_gia/dap_an.json) và tốc độ.

    python do_chinh_xac.py --out out_do/goc                  # chạy + chấm (clip đã có kết quả thì không chạy lại)
    python do_chinh_xac.py --out out_do/goc --chi-cham       # chỉ chấm lại
    python do_chinh_xac.py --out out_do/thu --clip 10_ m10   # chỉ vài clip (tên chứa chuỗi)
    python do_chinh_xac.py --out out_do/b2 -- --buoc 2       # tham số sau "--" đưa thẳng cho easyfnb_test.py
    python do_chinh_xac.py --so out_do/goc out_do/moi        # bảng so hai lần đo

Bộ clip nhỏ (xem "so_mau" in ra): chênh 1-2 ca có thể chỉ là may, đừng chỉnh ngưỡng theo các số này.
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NHAN = HERE / 'nhan_su_kien.json'
NHAN_BAN = HERE / 'nhan_ban_nguoi.json'   # nhãn người–bàn ở vài khung (chấm khớp bàn)
# Cấu hình demo (chay_camera.bat), bỏ phần máy chủ / thời gian thực / ghi hình
CAU_HINH = ['--no-video', '--dump',
            '--hand-model', 'giotay_pe_b16.pt', '--hand-th', '0.35', '--staff-model', 'nhanvien_pe_b16.pt',
            '--table-model', 'clip', '--clip-backbone', 'pe_core_s16',
            '--pose-models', 'yolo26n-pose_544x960_fp16.engine', '--det-models', 'yolo26s_736x1280_fp16.engine',
            '--pose-refine', 'rtmpose-m', '--refine-mode', 'luot', '--det-every', '100', '--staff-every', '20',
            '--tich-luy', '--yoloe', '--hanh-dong']
LOAI = ('goi_phuc_vu', 'can_don', 'khach_moi', 'nv_den', 'da_don')
SOM = 0.5          # sự kiện được sớm hơn nhãn tối đa bấy nhiêu giây (nhãn gán bằng mắt, sai số)
LE_X = 80          # nới khoảng x của người giơ tay (pixel của video gốc)


def bo_qua(e, loai, c):
    """Sự kiện rơi vào vùng "bo_qua" của clip (bàn / khoảng giờ người gán nhãn không xác định được) thì không chấm."""
    for b in c.get('bo_qua', []):
        if 'loai' in b and loai not in b['loai']:
            continue
        if 'ban' in b and e.get('ban') != b['ban']:
            continue
        if b.get('tu', -1e9) <= e['t'] <= b.get('den', 1e9):
            return True
    return False


def chay(nhan, out, loc, them, lai):
    """Chạy pipeline trên từng clip, mỗi clip một tiến trình (nạp model lúc thiếu RAM có khi crash: thử 3 lần)."""
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    out.mkdir(parents=True, exist_ok=True)
    for ten, c in nhan['clip'].items():
        if loc and not any(s in ten for s in loc):
            continue
        if (out / ten / 'su_kien.json').exists() and not lai:
            continue
        cmd = [sys.executable, str(HERE / 'easyfnb_test.py'), str(HERE / c['tep']), '--out', str(out)] + CAU_HINH + them
        for lan in (1, 2, 3):
            with open(out / f'{ten}.log', 'w', encoding='utf-8') as log:
                r = subprocess.run(cmd, cwd=HERE, env=env, stdout=log, stderr=subprocess.STDOUT)
            if r.returncode == 0:
                break
            print(f'  {ten}: lần {lan} lỗi (mã {r.returncode}), xem {out / (ten + ".log")}', flush=True)
        print(f'  xong {ten}', flush=True)


def khop(e, n, loai, tre):
    """Sự kiện e (t đã quy về giây của tệp) có khớp nhãn n không."""
    if not (n['tu'] - SOM <= e['t'] <= n['den'] + tre):
        return False
    if loai == 'goi_phuc_vu':
        if 'ban' in n and e.get('ban') != n['ban']:   # nhãn có bàn: gọi đúng người mà sai bàn vẫn là sai
            return False
        if not e.get('box') or 'x' not in n:
            return True
        cx = (e['box'][0] + e['box'][2]) / 2
        return n['x'][0] - LE_X <= cx <= n['x'][1] + LE_X
    ban = n.get('ban')   # một bàn, hoặc danh sách bàn khi người gán không chắc người đó đứng ở bàn nào
    return e.get('ban') in ban if isinstance(ban, list) else e.get('ban') == ban


def cham(nhan, out, loc=None):
    zones = json.loads((HERE / 'zones.json').read_text(encoding='utf-8'))
    kq = {k: dict(nhan=0, bat=0, bao=0, dung=0, nham=0, trung=0, tre=[], sot=[], ct_nham=[]) for k in LOAI}
    phut = {k: 0.0 for k in LOAI}        # số phút video có chấm loại này (mẫu số của báo nhầm mỗi phút)
    fps, thieu, tong_s = [], [], 0.0
    for ten, c in nhan['clip'].items():
        if loc and not any(s in ten for s in loc):
            continue
        f = out / ten / 'su_kien.json'
        if not f.exists():
            thieu.append(ten)
            continue
        r = json.loads(f.read_text(encoding='utf-8'))
        dau = float(zones.get(ten, {}).get('bat_dau_s', 0))   # pipeline tính giờ từ sau đoạn bỏ qua
        toc = float(zones.get(ten, {}).get('toc', 1.0))
        dai = r['do_dai_s']
        if c.get('cham_den'):                 # đoạn cuối tệp không chấm (vd bảng quảng cáo): bỏ sự kiện sau mốc này
            dai = min(dai, c['cham_den'] - dau)
        tong_s += dai
        co_ban = ten in zones                 # clip chưa vẽ vùng bàn: pipeline chỉ báo được giơ tay
        if r.get('fps_thuc'):
            fps.append((ten, r['fps_thuc'], r.get('khung_moi_giay'), r.get('nguoi_tb'),
                        round(r['so_khung'] / r['do_dai_s'], 1) if r['do_dai_s'] else None))
        for loai in LOAI:
            if loai in c.get('khong_cham', []) or (loai != 'goi_phuc_vu' and not co_ban):
                continue
            k = kq[loai]
            phut[loai] += dai / 60
            tre = c.get('tre_toi_da', {}).get(loai, 1.0)
            evs = [dict(e, t=e['t'] + dau) for e in r['su_kien'] if e['loai'] == loai]
            evs = [e for e in evs if e['t'] <= c.get('cham_den', 1e9) and not bo_qua(e, loai, c)]
            # nhãn "tuy_chon": người xem không chắc nên có báo hay không -> sự kiện khớp không tính đúng, không tính nhầm
            for n in (n for n in c.get(loai, []) if n.get('tuy_chon')):
                evs = [e for e in evs if not khop(e, n, loai, tre)]
            nh = [n for n in c.get(loai, []) if not n.get('tuy_chon')]
            # Mỗi sự kiện gán cho MỘT nhãn: nhãn khớp có tâm x gần nhất (hai người ngồi sát nhau cùng giơ tay thì
            # khoảng x chồng nhau). Nhãn được tính "bắt" khi có sự kiện gán cho nó; sự kiện thứ hai trở đi là "trùng".
            cua = {}
            for i, e in enumerate(evs):
                ung = [j for j, n in enumerate(nh) if khop(e, n, loai, tre)]
                if ung:
                    cx = (e['box'][0] + e['box'][2]) / 2 if e.get('box') else 0
                    cua[i] = min(ung, key=lambda j: abs(cx - sum(nh[j]['x']) / 2) if 'x' in nh[j] else 0)
            for j, n in enumerate(nh):
                k['nhan'] += 1
                moi = [i for i, jj in cua.items() if jj == j]
                if moi:
                    k['bat'] += 1
                    # "tu_tre": mốc tính trễ khi khác đầu cửa sổ khớp (vd bàn bẩn từ lúc khách đứng dậy, cần dọn từ lúc khách đi hẳn)
                    k['tre'].append(round((evs[moi[0]]['t'] - n.get('tu_tre', n['tu'])) * toc, 2))
                    k['trung'] += len(moi) - 1
                else:
                    k['sot'].append(f"{ten[:3]} {n.get('ai') or n.get('ban')} @{n['tu']}s")
            k['bao'] += len(evs)
            k['dung'] += len(cua)
            for i, e in enumerate(evs):
                if i in cua:
                    continue
                k['nham'] += 1
                at = next((a['mo_ta'] for a in c.get('am_tinh', [])
                           if a['tu'] - 1 <= e['t'] <= a['den'] + 2), None)
                k['ct_nham'].append(f"{ten[:3]} {e['t']:.1f}s bàn={e.get('ban')} {e.get('chi_tiet', '')}"
                                    + (f' [{at}]' if at else ''))
    for loai, k in kq.items():
        k['precision'] = round(k['dung'] / k['bao'], 3) if k['bao'] else None
        k['recall'] = round(k['bat'] / k['nhan'], 3) if k['nhan'] else None
        k['nham_moi_phut'] = round(k['nham'] / phut[loai], 3) if phut[loai] else None
        k['phut'] = round(phut[loai], 1)
        k['tre_tb_s'] = round(sum(k['tre']) / len(k['tre']), 2) if k['tre'] else None
    # trạng thái bàn theo mốc và giơ tay theo đáp án cũ (danh_gia/dap_an.json), để so với các lần đo trước
    sys.path.insert(0, str(HERE / 'danh_gia'))
    ban = None
    try:
        import cham_diem
        gt = json.loads((HERE / 'danh_gia' / 'dap_an.json').read_text(encoding='utf-8'))
        if all((out / t / 'su_kien.json').exists() for t in gt['ban']):
            ban = cham_diem.score_tables(gt['ban'], out)
    except Exception as e:   # thiếu đáp án cũ: bỏ phần này
        print(f'  không chấm được trạng thái bàn: {e}')
    return dict(loai=kq, ban=ban, fps=fps, thieu=thieu, tong_phut=round(tong_s / 60, 1), khop_ban=cham_khop_ban(out, loc))


def _iou(a, b):
    iw = min(a[2], b[2]) - max(a[0], b[0])
    ih = min(a[3], b[3]) - max(a[1], b[1])
    if iw <= 0 or ih <= 0:
        return 0.0
    i = iw * ih
    return i / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i)


def cham_khop_ban(out, loc=None):
    """Người được gán đúng bàn không (nhãn: nhan_ban_nguoi.json, kết quả: chi_tiet.json của --dump).
    Mỗi người có nhãn ghép với người của pipeline ở khung gần nhất (lệch không quá 0,25 s) có khung chồng từ 0,5.
    Người "được đếm" ở một bàn = gán bàn đó và không đi, không đứng, không là nhân viên (đúng như cách đếm khách)."""
    if not NHAN_BAN.exists():
        return None
    nhan = json.loads(NHAN_BAN.read_text(encoding='utf-8'))
    k = dict(ngoi=0, dung_ban=0, dem_dung=0, bo_sot=0, sai_ban=0, khac=0, dem_nham=0, khong_thay=0, hoi=0, ct=[])
    for ten, frames in nhan['clip'].items():
        if loc and not any(s in ten for s in loc):
            continue
        f = out / ten / 'chi_tiet.json'
        if not f.exists():
            continue
        khung = json.loads(f.read_text(encoding='utf-8'))['khung']
        k['hoi'] += sum(len(kh.get('hoi_ban') or ()) for kh in khung)
        for fr in frames:
            kh = min(khung, key=lambda x: abs(x['t'] - fr['t']))
            if abs(kh['t'] - fr['t']) > 0.25:
                k['khong_thay'] += len(fr['nguoi'])
                continue
            for p in fr['nguoi']:
                m = max(kh['nguoi'], key=lambda q: _iou(q['box'], p['box']), default=None)
                if m is None or _iou(m['box'], p['box']) < 0.5:
                    k['khong_thay'] += 1
                    continue
                dem = m.get('ban') is not None and not (m['di'] or m['dung'] or m['nv'])
                ghi = f"{ten[:3]} @{fr['t']}s #{m['id']} nhãn={p['nhan']} máy={m.get('ban')}" + ('' if dem else ' (không đếm)')
                if p['nhan'].startswith('B'):
                    k['ngoi'] += 1
                    if m.get('ban') == p['nhan']:
                        k['dung_ban'] += 1
                        k['dem_dung'] += dem
                        if not dem:
                            k['ct'].append('không đếm ' + ghi)
                    elif m.get('ban') is None:
                        k['bo_sot'] += 1
                        k['ct'].append('bỏ sót ' + ghi)
                    else:
                        k['sai_ban'] += 1
                        k['ct'].append('sai bàn ' + ghi)
                else:
                    k['khac'] += 1
                    if dem:
                        k['dem_nham'] += 1
                        k['ct'].append('đếm nhầm ' + ghi)
    return k


def in_bang(d, ten=''):
    print(f'\n== {ten}  ({d["tong_phut"]} phút video' + (f', THIẾU kết quả: {d["thieu"]}' if d['thieu'] else '') + ')')
    print(f"{'loại':<12} {'precision':>14} {'recall':>12} {'nhầm/phút':>16} {'trễ tb (s)':>11} {'trùng':>6}")
    for loai, k in d['loai'].items():
        p = '-' if k['precision'] is None else f"{k['precision']:.2f} ({k['dung']}/{k['bao']})"
        r = '-' if k['recall'] is None else f"{k['recall']:.2f} ({k['bat']}/{k['nhan']})"
        fp = '-' if k['nham_moi_phut'] is None else f"{k['nham_moi_phut']:.2f} ({k['nham']}/{k['phut']}p)"
        tr = '-' if k['tre_tb_s'] is None else f"{k['tre_tb_s']:.2f}"
        print(f'{loai:<12} {p:>14} {r:>12} {fp:>16} {tr:>11} {k["trung"]:>6}')
    if d['ban']:
        b = d['ban']
        print(f"trạng thái bàn theo mốc: {b['dung']}/{b['tong']} chấm chặt, {b['dung_cho_tre']}/{b['tong']} cho trễ 0,5 s")
    if kb := d.get('khop_ban'):
        print(f"khớp bàn: khách ngồi gán đúng bàn {kb['dung_ban']}/{kb['ngoi']} (đếm đúng {kb['dem_dung']}), "
              f"bỏ sót {kb['bo_sot']}, sai bàn {kb['sai_ban']}; đứng/nhân viên/ngoài bị đếm là khách "
              f"{kb['dem_nham']}/{kb['khac']}; không thấy người {kb['khong_thay']}; hỏi Decision {kb['hoi']} lần")
    if d['fps']:
        v = [f[1] for f in d['fps']]
        cham_nhat = min(d['fps'], key=lambda f: f[1])
        m = [f[2] for f in d['fps'] if f[2]]
        print(f"tốc độ thật (khung video/giây, đã gồm khung bỏ qua nếu --buoc): trung bình {sum(v) / len(v):.1f}, "
              f"chậm nhất {cham_nhat[1]} ({cham_nhat[0]}, {cham_nhat[3]} người/khung); "
              f"tính theo thời gian model: trung bình {sum(m) / max(len(m), 1):.1f} khung xử lý/giây ({len(v)} clip)")
    for loai, k in d['loai'].items():
        for s in k['sot']:
            print(f'   sót  {loai}: {s}')
        for s in k['ct_nham']:
            print(f'   nhầm {loai}: {s}')
        if k['tre']:
            print(f'   trễ  {loai}: {k["tre"]}')
    for s in (d.get('khop_ban') or {}).get('ct', []):
        print(f'   bàn  {s}')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', type=Path, default=HERE / 'out_do' / 'moi')
    ap.add_argument('--chi-cham', action='store_true', help='không chạy pipeline, chỉ chấm kết quả đã có')
    ap.add_argument('--lai', action='store_true', help='chạy lại cả clip đã có kết quả')
    ap.add_argument('--clip', nargs='*', default=None, help='chỉ các clip có tên chứa một trong các chuỗi này')
    ap.add_argument('--so', nargs=2, type=Path, default=None, help='so hai thư mục kết quả (gốc, mới)')
    ap.add_argument('them', nargs='*', help='sau "--": tham số thêm cho easyfnb_test.py')
    args = ap.parse_args()
    nhan = json.loads(NHAN.read_text(encoding='utf-8'))
    if args.so:
        for o in args.so:
            in_bang(cham(nhan, o, args.clip), str(o))
        return
    if not args.chi_cham:
        chay(nhan, args.out, args.clip, args.them, args.lai)
    d = cham(nhan, args.out, args.clip)
    in_bang(d, str(args.out))
    (args.out / 'do_chinh_xac.json').write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
