"""Trợ lý nhìn lại nhiều ngày (tuần này, 7 ngày qua, tháng trước) và nhân viên của một ngày đã qua.

Mọi thứ đọc từ lịch sử lâu dài: dòng thời gian (server/timeline.py, tệp timeline.db) cho việc và giờ vào ra ca,
sổ thanh toán (server/chat.py, tệp quan.db) cho tiền. Không cần ca còn trong RAM, nên khởi động lại vẫn hỏi được.
"""
import re
from datetime import datetime, timedelta

from . import xem_lai
from .doi_chieu import hhmm, money
from .tro_ly import MUC_VI, bo_dau, khoi_bang, muc, nhan_xet, ten_nv

TOI_DA_NGAY = 62
THU = ('T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN')


def khoang(q, t=None):
    """Khoảng ngày nhắc trong câu đã bỏ dấu: (ngày đầu, ngày cuối, tên gọi) dạng YYYY-MM-DD, hoặc None."""
    nay = xem_lai._ngay(t)
    m = re.search(r'(\d{1,2}) ngay (?:qua|gan day|vua roi|gan nhat|vua qua)', q)
    if m:
        n = max(2, min(int(m.group(1)), TOI_DA_NGAY))
        a, b, ten = nay - timedelta(days=n - 1), nay, f'{n} ngày qua'
    elif re.search(r'tuan (?:truoc|roi|vua roi)', q):
        b = nay - timedelta(days=nay.weekday() + 1)
        a, ten = b - timedelta(days=6), 'tuần trước'
    elif re.search(r'tuan (?:nay|qua)|ca tuan|trong tuan|may ngay (?:nay|qua)|nhung ngay (?:qua|gan day)', q):
        a, b, ten = (nay - timedelta(days=6), nay, '7 ngày qua') if 'tuan nay' not in q else \
            (nay - timedelta(days=nay.weekday()), nay, 'tuần này')
    elif re.search(r'thang (?:truoc|roi|vua roi)', q):
        b = nay.replace(day=1) - timedelta(days=1)
        a, ten = b.replace(day=1), f'tháng {b.month}'
    elif re.search(r'thang nay|ca thang|trong thang', q):
        a, b, ten = nay.replace(day=1), nay, 'tháng này'
    elif re.search(r'nhung ngay nao|ngay nao co du lieu|luu (?:duoc )?bao nhieu ngay|tat ca cac ngay|luu bao lau', q):
        a, b, ten = nay - timedelta(days=TOI_DA_NGAY - 1), nay, 'các ngày đã lưu'
    else:
        ds = [datetime.strptime(str(x), '%Y-%m-%d').date() for x in xem_lai.doc_cac_ngay(q, t)]
        if len(ds) < 2 or not re.search(r'\b(?:den|toi|-)\b', q):
            return None
        a, b = min(ds[0], ds[1]), max(ds[0], ds[1])
        ten = f'từ {a.day:02d}/{a.month:02d} đến {b.day:02d}/{b.month:02d}'
    if (b - a).days >= TOI_DA_NGAY:
        a = b - timedelta(days=TOI_DA_NGAY - 1)
    return str(a), str(b), ten


def _nhan(day, t=None):
    d = datetime.strptime(day, '%Y-%m-%d').date()
    ten = xem_lai.ten_ngay(day, t)
    return f'{THU[d.weekday()]} {d.day:02d}/{d.month:02d}' + (f' ({ten})' if not ten.startswith('ngày') else '')


def tong_hop(hub, phong, d_from, d_to, t=None):
    """Mỗi ngày có dữ liệu trong khoảng một dòng: việc, khách mới, tốc độ, tiền, lượt khách. Cũ trước."""
    a, b = (datetime.strptime(x, '%Y-%m-%d').date() for x in (d_from, d_to))
    co_viec = set(hub.timeline.days())
    out = []
    for i in range((b - a).days + 1):
        day = str(a + timedelta(days=i))
        rev = phong.revenue(day) if phong is not None else None
        if day not in co_viec and not (rev and rev['count']):
            continue
        tk = xem_lai.tong_ket_ngay(hub, day, t)
        if not tk['n'] and not (rev and (rev['count'] or rev['visits'])):
            continue
        sp = tk['speed']
        do = sp['fast'] + sp['ok'] + sp['slow'] + sp['missed']
        out.append(dict(
            ngay=day, nhan=_nhan(day, t), viec=tk['n'], goi_phuc_vu=tk['call'], can_don=tk['needs_clearing'],
            khach_moi=tk['new_guest'], toc_do=MUC_VI.get(nhan_xet(sp)), viec_nhanh=sp['fast'],
            viec_cham_hoac_bo_lo=sp['slow'] + sp['missed'], phan_tram_nhanh=round(sp['fast'] * 100 / do) if do else None,
            gio_ban_nhat=f"{tk['dinh']:02d}:00" if tk['dinh'] is not None else None,
            tien=rev['total'] if rev else None, so_thanh_toan=rev['count'] if rev else None,
            luot_khach=rev['visits'] if rev else None,
            chua_thay_thanh_toan=len(rev['review']) if rev else None))
    return out


def tra_loi(hub, phong, d_from, d_to, ten, t=None):
    """(câu trả lời, khối, các dòng) cho một khoảng ngày."""
    rows = tong_hop(hub, phong, d_from, d_to, t)
    if not rows:
        return f'{ten.capitalize()} hệ thống chưa ghi được ngày nào có dữ liệu.', [], rows
    tien = sum(r['tien'] or 0 for r in rows)
    khach = sum(r['luot_khach'] or 0 for r in rows)
    dong = max(rows, key=lambda r: (r['luot_khach'] or 0, r['viec']))
    ans = f"{ten.capitalize()} có dữ liệu của {len(rows)} ngày"
    if tien:
        cao = max(rows, key=lambda r: r['tien'] or 0)
        ans += f", đã ghi {money(tien)} từ {khach} lượt khách. Thu cao nhất là {cao['nhan']} với {money(cao['tien'])}."
    else:
        ans += f", {sum(r['viec'] for r in rows)} việc. Đông nhất là {dong['nhan']}."
    pt = [r for r in rows if r['phan_tram_nhanh'] is not None]
    if len(pt) >= 2 and abs(pt[-1]['phan_tram_nhanh'] - pt[0]['phan_tram_nhanh']) >= 10:
        ans += (' Phục vụ đang nhanh lên' if pt[-1]['phan_tram_nhanh'] > pt[0]['phan_tram_nhanh'] else ' Phục vụ đang chậm đi')
        ans += f": {pt[0]['nhan']} có {pt[0]['phan_tram_nhanh']}% việc nhanh, {pt[-1]['nhan']} có {pt[-1]['phan_tram_nhanh']}%."
    bs = []
    if len(rows) > 1:
        co_tien = any(r['tien'] for r in rows)
        bs.append(dict(type='chart', kind='column', title=('Tiền thu' if co_tien else 'Số việc') + f' từng ngày, {ten}',
                       unit='nghìn đ' if co_tien else 'việc',
                       points=[dict(label=r['nhan'][:8], value=round((r['tien'] or 0) / 1000) if co_tien else r['viec'],
                                    note=f"{r['luot_khach']} lượt khách" if r['luot_khach'] else None)
                               for r in rows[-31:]]))
    bs.append(khoi_bang(f'Từng ngày, {ten}', ['Ngày', 'Tiền thu', 'Lượt khách', 'Khách gọi', 'Phục vụ', 'Chậm hoặc bỏ lỡ'],
                        [[r['nhan'], money(r['tien']) if r['tien'] else 'chưa có',
                          str(r['luot_khach']) if r['luot_khach'] is not None else '', str(r['goi_phuc_vu']),
                          r['toc_do'] or 'chưa có', str(r['viec_cham_hoac_bo_lo'])] for r in rows[-40:]]))
    return ans, bs, rows


def nhan_vien_ngay(hub, day, t=None):
    """Từng nhân viên trong một ngày, đọc từ lịch sử: vào ca, ra ca, số việc nhận, nhanh hay chậm. (câu, khối, dòng)"""
    tk = xem_lai.tong_ket_ngay(hub, day, t)
    d0 = xem_lai.dau_ngay_s(day)
    ca = {}
    for r in hub.timeline.query(since=d0, until=d0 + 86400 - 0.001, kinds='staff_*', limit=5000):
        c = ca.setdefault(r['staff'], dict(vao=None, ra=None, ten=r['text']))
        if r['kind'] == 'staff_online' and c['vao'] is None:
            c['vao'] = r['ts']
        elif r['kind'] == 'staff_offline':
            c['ra'] = r['ts']
        if r['kind'] == 'staff_online' and c['ra'] is not None and r['ts'] > c['ra']:
            c['ra'] = None          # vào lại sau khi nghỉ: chưa ra ca
    viec = {}
    for r in tk['recs']:
        if r['nv'] and r['nv'] not in ('camera', 'gemini', 'manager'):
            v = viec.setdefault(r['nv'], dict(n=0, fast=0, ok=0, slow=0, missed=0))
            v['n'] += 1
            if r['ket'] != 'bo_lo' and r['wait_s'] is not None:
                v[muc(r['wait_s'])] += 1
    ten = xem_lai.ten_ngay(day, t)
    rows = []
    for sid in sorted(set(ca) | set(viec), key=lambda s: -(viec.get(s, {}).get('n', 0))):
        c, v = ca.get(sid, {}), viec.get(sid, dict(n=0, fast=0, ok=0, slow=0, missed=0))
        rows.append(dict(ten=c.get('ten') or ten_nv(hub, sid) or sid, vao_ca=hhmm(c['vao']) if c.get('vao') else None,
                         ra_ca=hhmm(c['ra']) if c.get('ra') else None, viec_nhan=v['n'], nhanh=v['fast'],
                         hoi_cham=v['ok'], cham=v['slow'], toc_do=MUC_VI.get(nhan_xet(v))))
    if not rows:
        return f'{ten.capitalize()} hệ thống không ghi được nhân viên nào vào ca hay nhận việc.', [], rows
    co_viec = [r for r in rows if r['viec_nhan']]
    ans = f"{ten.capitalize()} có {len(rows)} nhân viên được ghi lại."
    if co_viec:
        tot = max(co_viec, key=lambda r: (r['nhanh'] / r['viec_nhan'], r['viec_nhan']))
        ans += f" {tot['ten']} nhận việc nhanh nhất: {tot['nhanh']} trong {tot['viec_nhan']} việc được nhận nhanh."
    b = khoi_bang(f'Nhân viên {ten}', ['Nhân viên', 'Vào ca', 'Ra ca', 'Việc nhận', 'Nhanh', 'Hơi chậm', 'Chậm', 'Nhìn chung'],
                  [[r['ten'], r['vao_ca'] or '', r['ra_ca'] or '', str(r['viec_nhan']), str(r['nhanh']), str(r['hoi_cham']),
                    str(r['cham']), r['toc_do'] or 'chưa có'] for r in rows])
    return ans, [b], rows


def cong_cu(hub, phong, them):
    """Hai công cụ ADK."""

    def nhieu_ngay(khoang_ngay: str) -> dict:
        """Nhìn lại nhiều ngày một lúc, đọc từ lịch sử lâu dài: mỗi ngày có tiền thu, lượt khách, số lần khách gọi, tốc độ phục vụ, số việc chậm hoặc bỏ lỡ, phần trăm việc nhanh. Hiện luôn biểu đồ và bảng cho chủ quán. Dùng cho câu hỏi về cả tuần, cả tháng, mấy ngày qua, xu hướng, ngày nào đông nhất hay thu cao nhất, hệ thống đang lưu những ngày nào.

        Args:
            khoang_ngay: "tuần này", "tuần trước", "7 ngày qua", "30 ngày qua", "tháng này", "tháng trước", "10/11 đến 13/11", hoặc "những ngày nào" để xem mọi ngày đã lưu.
        """
        k = khoang(bo_dau(khoang_ngay))
        if not k:
            return dict(ket_qua='Không hiểu khoảng ngày. Đưa "tuần này", "7 ngày qua", "tháng trước" hoặc "10/11 đến 13/11".')
        ans, bs, rows = tra_loi(hub, phong, *k)
        for b in bs:
            them(b)
        return dict(tom_tat=ans, tu_ngay=k[0], den_ngay=k[1], so_ngay_co_du_lieu=len(rows), tung_ngay=rows,
                    luu_y='Chỉ có những ngày hệ thống đã chạy. Ngày không có trong danh sách là chưa có dữ liệu.')

    def nhan_vien_ngay_cu(ngay: str) -> dict:
        """Nhân viên trong một ngày ĐÃ QUA, đọc từ lịch sử: ai vào ca, ra ca lúc mấy giờ, mỗi người nhận bao nhiêu việc, nhanh hay chậm. Hiện luôn bảng. Hôm nay thì dùng các công cụ đọc ca hiện tại.

        Args:
            ngay: "hôm qua", "hôm kia", "12/11" hoặc dạng YYYY-MM-DD.
        """
        ds = xem_lai.doc_cac_ngay(bo_dau(ngay))
        if not ds:
            return dict(ket_qua='Không hiểu ngày nào. Đưa "hôm qua", "12/11" hoặc dạng YYYY-MM-DD.')
        ans, bs, rows = nhan_vien_ngay(hub, str(ds[0]))
        for b in bs:
            them(b)
        return dict(tom_tat=ans, nhan_vien=rows)

    return [nhieu_ngay, nhan_vien_ngay_cu]
