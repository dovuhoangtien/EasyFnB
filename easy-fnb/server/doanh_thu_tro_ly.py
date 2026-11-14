"""Trợ lý trả lời về tiền thu: đọc sổ thanh toán của phòng chat (server/chat.py) và phần đối chiếu với lượt khách.

Mọi con số do máy chủ tính (Phong.revenue), model chỉ viết câu. Dùng cho cả trợ lý của chủ quán (hiện khối) và
đường không AI. Tiền chỉ là những khoản nhân viên đã chụp gửi vào nhóm, nên câu trả lời luôn nói rõ điều đó.
"""
import json

from . import xem_lai
from .doi_chieu import hhmm, money

TU_TIEN = ('doanh thu', 'thu duoc', 'thu ve', 'bao nhieu tien', 'tien thu', 'thanh toan', 'chuyen khoan', 'hoa don',
           'tra tien', 'chua tra', 'quen tra', 'tinh tien chua', 'ban duoc', 'moi khach chi', 'thu ngan',
           'thu bao nhieu', 'revenue', 'sales', 'how much')
GOI_Y = ['Bàn nào khách về mà chưa thấy thanh toán?', 'Hôm nay thu so với hôm qua thế nào?',
         'Khoản lớn nhất hôm nay là bàn nào?', 'Hôm nay thu được bao nhiêu?']
TYPE_VI = {'chuyen_khoan': 'chuyển khoản', 'hoa_don': 'hoá đơn', 'phieu_thu': 'phiếu thu', 'khac': 'ảnh'}


def la_hoi_tien(q):
    """q đã bỏ dấu."""
    return any(x in q for x in TU_TIEN)


def _ten_ngay(day, nay):
    if day == nay:
        return 'hôm nay'
    if day == str(xem_lai.doc_cac_ngay('hom qua')[0]):
        return 'hôm qua'
    return f'ngày {day[8:10]}/{day[5:7]}'


def _ngay(cau):
    """Ngày (YYYY-MM-DD) nhắc trong câu đã bỏ dấu; None là hôm nay."""
    ds = xem_lai.doc_cac_ngay(cau) if str(cau or '').strip() else []
    return [str(d) for d in ds]


def doc(phong, day=None):
    """Số liệu tiền của một ngày, gọn cho model: không kèm ảnh hay dữ liệu thô."""
    r = phong.revenue(day)
    pays = r['payments']
    huy = [p for p in phong.payments(r['day']) if p['status'] == 'void']
    theo_ban = {}
    for p in pays:
        if p.get('table'):
            theo_ban[p['table']] = theo_ban.get(p['table'], 0) + (p['amount'] or 0)
    lon = max(pays, key=lambda p: p['amount'] or 0, default=None)
    sua = []
    for p in pays:      # khoản nhân viên sửa số tiền so với máy đọc
        for cu, moi, ai in phong.kho.all('SELECT old, new, by FROM payment_edits WHERE payment_id = ? AND field = ? ORDER BY ts, rowid',
                               (p['id'], 'amount')):
            sua.append(dict(ban=p.get('table'), luc=hhmm(p['ts'] / 1000), tu=cu, thanh=moi, nguoi_sua=ai, so_tien_hien_nay=p['amount']))
    return dict(
        ngay=r['day'], tong=r['total'], so_thanh_toan=r['count'], chuyen_khoan=r['transfers'],
        hoa_don_va_khac=r['count'] - r['transfers'], luot_khach=r['visits'], tb_moi_khach=r['per_guest'],
        lon_nhat=dict(so_tien=lon['amount'], ban=lon.get('table'), luc=hhmm(lon['ts'] / 1000),
                      loai=TYPE_VI.get(lon['type'], lon['type'])) if lon else None,
        tong_ca_ngay_theo_ban=sorted(theo_ban.items(), key=lambda x: -x[1]),   # cộng mọi lượt khách của bàn trong ngày
        theo_gio=[(h['hour'], h['amount'], h['visits']) for h in r['hours']],
        can_xem_lai=[x['text'] for x in r['review']],
        da_sua_so_tien=sua,
        da_huy=[dict(so_tien=p['amount'], ban=p.get('table'), luc=hhmm(p['ts'] / 1000), ly_do=p.get('note') or None)
                for p in huy])


def khoi(d, ten):
    """Các khối hiển thị cho một ngày."""
    if not d['so_thanh_toan'] and not d['luot_khach']:
        return []
    items = [
        dict(label='Tiền đã ghi', value=money(d['tong']), tone=None,
             note=f"{d['so_thanh_toan']} thanh toán, {d['chuyen_khoan']} chuyển khoản"),
        dict(label='Lượt khách', value=str(d['luot_khach']), note='camera đếm theo bàn', tone=None),
    ]
    if d['tb_moi_khach']:
        items.append(dict(label='Mỗi khách chi', value=money(d['tb_moi_khach']), note='trung bình', tone=None))
    if d['lon_nhat']:
        ln = d['lon_nhat']
        items.append(dict(label='Khoản lớn nhất', value=money(ln['so_tien']), tone=None,
                          note=(f"bàn {ln['ban']}, " if ln['ban'] else '') + f"lúc {ln['luc']}"))
    n = len(d['can_xem_lai'])
    items.append(dict(label='Cần xem lại', value=str(n), tone='warn' if n else 'good',
                      note='lượt khách chưa thấy thanh toán hoặc khoản chưa khớp bàn' if n else 'tiền và khách khớp nhau'))
    bs = [dict(type='stats', title=f'Tiền thu {ten}', items=items)]
    gio = [(h, a, v) for h, a, v in d['theo_gio'] if a]
    if len(gio) > 1:
        bs.append(dict(type='chart', title=f'Tiền thu theo giờ, {ten}', kind='column', unit='nghìn đ',
                       points=[dict(label=f'{int(h)}h', value=round(a / 1000), note=f'{v} lượt khách' if v else None)
                               for h, a, v in d['theo_gio']]))
    if n:
        bs.append(dict(type='table', title='Cần xem lại', columns=['Việc cần xem'],
                       rows=[[x] for x in d['can_xem_lai'][:12]]))
    return bs


def cau(d, ten):
    if not d['so_thanh_toan']:
        if d['luot_khach']:
            return (f"{ten.capitalize()} camera thấy {d['luot_khach']} lượt khách nhưng chưa có thanh toán nào được chụp "
                    f"gửi vào nhóm.")
        return f'{ten.capitalize()} chưa có thanh toán nào được chụp gửi vào nhóm.'
    s = (f"{ten.capitalize()} đã ghi {money(d['tong'])} từ {d['so_thanh_toan']} thanh toán "
         f"({d['chuyen_khoan']} chuyển khoản), {d['luot_khach']} lượt khách.")
    if d['can_xem_lai']:
        s += f" Có {len(d['can_xem_lai'])} chỗ cần xem lại: {d['can_xem_lai'][0]}."
    return s


def so_sanh(a, ten_a, b, ten_b):
    def pt(x, y):
        if not y:
            return ''
        k = round((x - y) * 100 / y)
        return f" ({'+' if k >= 0 else ''}{k}%)"
    rows = [['Tiền đã ghi', money(b['tong']), money(a['tong']) + pt(a['tong'], b['tong'])],
            ['Số thanh toán', str(b['so_thanh_toan']), str(a['so_thanh_toan'])],
            ['Lượt khách', str(b['luot_khach']), str(a['luot_khach']) + pt(a['luot_khach'], b['luot_khach'])],
            ['Mỗi khách chi', money(b['tb_moi_khach']) if b['tb_moi_khach'] else 'chưa có',
             money(a['tb_moi_khach']) if a['tb_moi_khach'] else 'chưa có']]
    return dict(type='table', title=f'Tiền thu {ten_b} và {ten_a}', columns=['Chỉ số', ten_b.capitalize(), ten_a.capitalize()],
                rows=rows)


def tra_loi(phong, question_bo_dau):
    """Đường không AI: (câu trả lời, khối)."""
    nay = phong.revenue()['day']
    if any(x in question_bo_dau for x in ('ngay mai', 'tuan sau', 'thang sau', 'tomorrow')):
        return 'Ngày đó chưa tới nên chưa có tiền thu. Bạn có thể hỏi về hôm nay, hôm qua hoặc một ngày đã qua.', []
    ds = _ngay(question_bo_dau)
    day = ds[0] if ds else nay
    d = doc(phong, day)
    ten = _ten_ngay(day, nay)
    bs = khoi(d, ten)
    ans = cau(d, ten)
    khac = next((x for x in ds[1:] if x != day), None) or (nay if day != nay and 'so voi' in question_bo_dau else None)
    if khac is None and day == nay and any(x in question_bo_dau for x in ('so voi', 'so sanh')):
        khac = str(xem_lai.doc_cac_ngay('hom qua')[0])
    if khac and khac != day:
        e = doc(phong, khac)
        bs.insert(1, so_sanh(d, ten, e, _ten_ngay(khac, nay)))
    return ans, bs[:5]


def cong_cu(phong, them):
    """Công cụ ADK. `them` bỏ khối vào câu trả lời (trong phòng chat của quán thì khối bị bỏ qua, chỉ dùng số)."""

    def doanh_thu(ngay: str = '', so_voi_ngay: str = '', hien: bool = True) -> dict:
        """Tiền quán thu được trong một ngày, đọc từ ảnh chuyển khoản và hoá đơn nhân viên chụp gửi vào nhóm, đã đối chiếu với lượt khách camera thấy: tổng tiền, số thanh toán, bao nhiêu chuyển khoản, số lượt khách, trung bình mỗi khách chi, khoản lớn nhất, tiền theo bàn và theo giờ, lượt khách về mà chưa thấy thanh toán, khoản đã huỷ. Dùng cho mọi câu hỏi về doanh thu, tiền, thanh toán, hoá đơn, chuyển khoản, khách chưa trả tiền.

        Args:
            ngay: bỏ trống là hôm nay; hoặc "hôm qua", "12/11", dạng YYYY-MM-DD.
            so_voi_ngay: ngày đem ra so (ví dụ "hôm qua"). Bỏ trống là không so.
            hien: true để hiện khối số liệu và biểu đồ khi chủ quán hỏi tổng quát về tiền thu; câu hỏi hẹp (một khoản, một bàn, khoản đã huỷ) thì false.
        """
        from .tro_ly import bo_dau
        nay = phong.revenue()['day']
        ds = _ngay(bo_dau(ngay))
        if str(ngay or '').strip() and not ds:
            return dict(ket_qua='Không hiểu ngày nào. Đưa "hôm qua", "12/11" hoặc dạng YYYY-MM-DD.')
        day = ds[0] if ds else nay
        d = doc(phong, day)
        ten = _ten_ngay(day, nay)
        bs = khoi(d, ten)
        out = dict(d, ten_ngay=ten, don_vi='đồng',
                   luu_y='Chỉ gồm khoản nhân viên đã chụp gửi vào nhóm. Không có số liệu món bán chạy hay tồn kho.')
        ks = _ngay(bo_dau(so_voi_ngay)) if str(so_voi_ngay or '').strip() else []
        if ks and ks[0] != day:
            e = doc(phong, ks[0])
            out['so_voi'] = dict(e, ten_ngay=_ten_ngay(ks[0], nay))
            bs.insert(1, so_sanh(d, ten, e, _ten_ngay(ks[0], nay)))
        if hien:
            for b in bs[:3]:
                them(b)
        return json.loads(json.dumps(out, ensure_ascii=False, default=str))

    return doanh_thu
