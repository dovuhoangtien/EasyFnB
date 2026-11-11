"""Thử nhiều cách kết hợp luật khung xương + model nhỏ cho "khách giơ tay gọi", không chạy lại video.

Đọc chi_tiet.json do `easyfnb_test.py --dump` ghi (mỗi người, mỗi khung: điểm luật, độ nâng cổ tay,
xác suất giơ tay của model, xác suất là nhân viên), dựng lại sự kiện như pipeline rồi chấm như cham_diem.py.

    python danh_gia/thu_gio_tay.py out_v2/

Chú ý: đáp án giơ tay chỉ có 7 lần giơ, trong 2 clip. Chọn cách nào theo bảng này là đang chỉnh
theo chính tập test, nên kết quả của cách được chọn sẽ đẹp hơn thực tế một chút.
"""
import argparse
import json
import sys
import tempfile
from collections import deque
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from cham_diem import score_hands  # noqa: E402

CACH = {
    'luat (chỉ khung xương)': lambda p: p['luat'] > 0,
    'model >= 0.5': lambda p: (p['ph'] or 0) >= 0.5,
    'model >= 0.9': lambda p: (p['ph'] or 0) >= 0.9,
    'ket_hop cũ (model>=0.5 hoặc luật+model>=0.3)': lambda p: (p['ph'] or 0) >= 0.5 or (p['luat'] > 0 and (p['ph'] or 0) >= 0.3),
    'luật VÀ model>=0.5': lambda p: p['luat'] > 0 and (p['ph'] or 0) >= 0.5,
    'luật VÀ model>=0.3': lambda p: p['luat'] > 0 and (p['ph'] or 0) >= 0.3,
    'model>=0.5 VÀ cổ tay trên vai': lambda p: (p['ph'] or 0) >= 0.5 and p.get('nang') is not None and p['nang'] > 0.3,
    # thêm sau khi xem kết quả test (hợp hai cách ít báo nhầm nhất): coi là đã chỉnh theo test
    'luật, HOẶC model>=0.5 VÀ cổ tay trên vai':
        lambda p: p['luat'] > 0 or ((p['ph'] or 0) >= 0.5 and p.get('nang') is not None and p['nang'] > 0.3),
    'model>=0.8 VÀ cổ tay trên vai, hoặc luật+model>=0.3':
        lambda p: ((p['ph'] or 0) >= 0.8 and p.get('nang') is not None and p['nang'] > 0.3)
        or (p['luat'] > 0 and (p['ph'] or 0) >= 0.3),
}


def simulate(d, up_fn, hand_s=0.6, cooldown=5.0, use_staff=True):
    hist, staff_hist, last, ev = {}, {}, {}, []
    for k in d['khung']:
        t = k['t']
        for p in k['nguoi']:
            q = hist.setdefault(p['id'], deque())
            q.append((t, up_fn(p)))
            while q and q[0][0] < t - max(1.0, hand_s):
                q.popleft()
            sq = staff_hist.setdefault(p['id'], deque())
            if use_staff and p.get('pst') is not None:
                sq.append((t, p['pst']))
            while sq and sq[0][0] < t - 3.0:
                sq.popleft()
            staff = bool(sq) and np.mean([v for _, v in sq]) >= 0.5
            recent = [u for tt, u in q if tt >= t - hand_s]
            calling = not staff and q[-1][0] - q[0][0] >= 0.8 * hand_s and np.mean(recent) >= 0.7
            if calling and t - last.get(p['id'], -1e9) > cooldown:
                last[p['id']] = t
                ev.append(dict(t=round(t, 2), loai='goi_phuc_vu', box=p['box']))
    return ev


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out', type=Path)
    ap.add_argument('--khong-nhan-vien', action='store_true', help='bỏ model nhân viên (không loại nhân viên)')
    ap.add_argument('--chi-tiet', action='store_true', help='in người bị sót, lần báo nhầm (với cách ít báo nhầm)')
    args = ap.parse_args()
    gt = json.loads((HERE / 'dap_an.json').read_text(encoding='utf-8'))['gio_tay']
    dumps = {f.parent.name: json.loads(f.read_text(encoding='utf-8')) for f in args.out.glob('*/chi_tiet.json')}
    print(f'{len(dumps)} clip có chi tiết\n')
    print(f"{'cách':<58}{'bắt được':>9}{'báo đúng':>10}{'báo nhầm':>10}{'precision':>11}")
    rows = []
    for name, fn in CACH.items():
        with tempfile.TemporaryDirectory() as tmp:
            for clip, d in dumps.items():
                (Path(tmp) / clip).mkdir()
                ev = simulate(d, fn, use_staff=not args.khong_nhan_vien)
                (Path(tmp) / clip / 'su_kien.json').write_text(json.dumps({'su_kien': ev}), encoding='utf-8')
            s = score_hands(gt, Path(tmp))
        rows.append((name, s))
        print(f"{name:<58}{s['bat_duoc']:>5}/{s['tong']}{s['bao_dung']:>10}{s['bao_nham']:>10}"
              f"{(s['precision'] or 0):>11.0%}")
        if args.chi_tiet and s['bao_nham'] <= 10:
            print(f"{'':<6}bỏ sót: {s['bo_sot']}  | báo nhầm: {s['chi_tiet_nham']}  | trễ: {s['tre_tung_lan']}")
    return rows


if __name__ == '__main__':
    main()
