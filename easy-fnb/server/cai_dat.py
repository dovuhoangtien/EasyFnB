"""Trợ lý cài đặt quán ngay trong khung chat (spec: docs/superpowers/specs/2026-11-13-tro-ly-setup-design.md).

Các hàm ở đây chỉ DỰNG KHỐI, không ghi gì vào hub. Dữ liệu chỉ đổi khi chủ quán bấm Lưu trong khối:
giao diện gọi thẳng các API cài đặt có sẵn (PUT /api/staff, PUT /api/zones, PUT /api/settings,
POST /api/staff/{id}/photos/camera). Vì vậy model có nói gì cũng không sửa được dữ liệu.

Bốn khối:
  qr        mã QR nối điện thoại làm camera, hoặc mở app nhân viên
  ban       bàn camera vừa tìm thấy, vẽ trên ảnh camera, chờ bấm Lưu
  xac_nhan  thay đổi nhân viên hoặc luật báo, sửa được tại chỗ, chờ bấm Lưu
  chup      chụp ảnh nhận dạng một nhân viên bằng camera quán
"""
import asyncio
import re

from .tro_ly import bo_dau

TIM_BAN_S = 12.0                 # chờ máy camera tìm bàn lâu nhất chừng này (như /api/zones/suggest)
LOAI_KHOI = ('qr', 'ban', 'xac_nhan', 'chup')
# câu nói như đã làm xong, trong khi dữ liệu chỉ đổi khi chủ quán bấm Lưu
NOI_DA_LUU = re.compile(r'(?i)(?<!\w)đã\s+(?:được\s+)?(?:lưu|cập nhật|thêm|bỏ|xoá|xóa|đổi|cài|thiết lập|ghi|áp dụng|xong|chỉnh|sửa|đặt|bật|tắt|'
                        r'thực hiện|làm|tạo|chụp|giúp)')
GOI_Y_CAI_DAT = ['Nối camera', 'Tìm bàn', 'Thêm nhân viên', 'Mở app nhân viên', 'Đổi luật báo']
ROLE_VI = {'serve': 'phục vụ', 'clean': 'dọn bàn', 'cashier': 'thu ngân', 'owner': 'chủ quán'}

# từ chỉ vai trò (đã bỏ dấu), dài trước để "don ban" không bị "ban" ăn mất
_VAI = [('thu ngan', 'cashier'), ('tinh tien', 'cashier'), ('dung quay', 'cashier'), ('cashier', 'cashier'),
        ('chay ban', 'serve'), ('phuc vu', 'serve'), ('bung be', 'serve'), ('order', 'serve'), ('serve', 'serve'),
        ('don ban', 'clean'), ('don dep', 'clean'), ('rua chen', 'clean'), ('rua bat', 'clean'), ('don', 'clean'),
        ('clean', 'clean'), ('chu quan', 'owner'), ('quan ly', 'owner'), ('owner', 'owner')]


def vai_tro(s, mac_dinh='serve'):
    """'chạy bàn' -> serve, 'dọn' -> clean, 'thu ngân' -> cashier, 'quản lý' -> owner."""
    q = bo_dau(s)
    return next((r for k, r in _VAI if re.search(rf'(?<![a-z]){k}(?![a-z])', q)), mac_dinh)


def ma_nv(ten, da_co):
    """Mã nhân viên từ tên: bỏ dấu, chỉ chữ và số, không trùng mã đã có ('Lan' -> 'lan', rồi 'lan2')."""
    goc = re.sub(r'[^a-z0-9]+', '', bo_dau(ten)) or 'nv'
    ma, n = goc, 2
    while ma in da_co:
        ma, n = f'{goc}{n}', n + 1
    return ma


def _tim_nv(hub, ten):
    """So có dấu trước ("Tư" không phải "Tú"); gõ không dấu thì so không dấu."""
    k = re.sub(r'\s+', ' ', _bo_xung_ho(str(ten or ''))).strip().lower()
    if not k:
        return None
    khong_dau = bo_dau(k) == k
    return next((s for s in hub.staff if s['name'].lower() == k or s['id'] == k
                 or (khong_dau and bo_dau(s['name']) == k)), None)


def _bo_xung_ho(s):
    """'anh Tư' -> 'Tư', 'chị Mai' -> 'Mai'."""
    return re.sub(r'(?i)^\s*(?:anh|chị|chi|em|cô|co|chú|chu|bạn|ban|bé|be|dì|di)\s+(?=\S)', '', s)


def _ten_dep(s):
    s = re.sub(r'\s+', ' ', _bo_xung_ho(str(s or ''))).strip(' .,:;-')
    return ' '.join(w[:1].upper() + w[1:] for w in s.split(' ')) if s else ''


# ====================================================================== mã QR
def khoi_qr_camera(hub, camera='cam1'):
    cam = _ma_cam(camera)
    return dict(type='qr', kind='camera', title=f'Nối camera {cam}', camera=cam, staff=[])


def khoi_qr_nhan_vien(hub, ten=''):
    """Mã QR mở app cho một người, hoặc mọi người khi ten rỗng. None nếu không có ai."""
    if str(ten or '').strip():
        s = _tim_nv(hub, ten)
        ds = [s] if s else []
    else:
        ds = list(hub.staff)
    if not ds:
        return None
    return dict(type='qr', kind='staff', title='Mở app nhân viên', camera=None,
                staff=[dict(id=s['id'], name=s['name']) for s in ds])


def _ma_cam(camera):
    m = re.search(r'(\d+)', str(camera or ''))
    return f'cam{int(m.group(1))}' if m else 'cam1'


# ====================================================================== tìm bàn
def _hop(poly):
    xs, ys = [p[0] for p in poly], [p[1] for p in poly]
    return min(xs), min(ys), max(xs), max(ys)


def _chong(a, b):
    """Phần chồng của hai khung bao so với khung nhỏ hơn (như overlap trong ZoneEditor)."""
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    w, h = min(ax2, bx2) - max(ax1, bx1), min(ay2, by2) - max(ay1, by1)
    if w <= 0 or h <= 0:
        return 0.0
    nho = min((ax2 - ax1) * (ay2 - ay1), (bx2 - bx1) * (by2 - by1))
    return w * h / nho if nho > 0 else 0.0


def _ten_tiep(dung):
    n = 1
    while f'B{n}' in dung:
        n += 1
    return f'B{n}'


def khoi_ban(hub, camera, ket_qua):
    """Khối duyệt bàn từ kết quả find_tables của máy camera ({frame_w, frame_h, tables: [{polygon}]},
    đã theo thứ tự đọc). Có vùng cũ thì kèm thêm phương án "chỉ thêm bàn mới". None nếu không thấy bàn nào."""
    fw, fh = int(ket_qua.get('frame_w') or 0), int(ket_qua.get('frame_h') or 0)
    tim = [[[float(x), float(y)] for x, y in t['polygon']] for t in ket_qua.get('tables') or [] if len(t['polygon']) >= 3]
    if not tim or not fw or not fh:
        return None
    thay = [dict(id=f'B{i + 1}', polygon=p) for i, p in enumerate(tim)]
    cu = hub.get_zones(camera)
    co = cu.get('tables') or []
    them = None
    if co and cu.get('frame_w') and cu.get('frame_h'):
        sx, sy = fw / cu['frame_w'], fh / cu['frame_h']
        giu = [dict(id=t['id'], polygon=[[x * sx, y * sy] for x, y in t['polygon']]) for t in co]
        dung = {t['id'].strip().upper() for t in giu}
        moi = []
        for p in tim:
            if any(_chong(_hop(p), _hop(t['polygon'])) > 0.4 for t in giu + moi):
                continue
            ten = _ten_tiep(dung)
            dung.add(ten)
            moi.append(dict(id=ten, polygon=p))
        them = giu + moi
    return dict(type='ban', title=f'Bàn camera {camera} tìm thấy', camera=camera, frame_w=fw, frame_h=fh,
                tables=thay, merged=them, existing=[t['id'] for t in co])


async def tim_ban(hub, camera='cam1', cho_s=TIM_BAN_S):
    """(câu trả lời, các khối). Nhờ máy camera tìm bàn; camera chưa chạy thì đưa mã QR để nối."""
    cam = _ma_cam(camera)
    if not hub.camera_live(cam):
        return (f'Camera {cam} chưa gửi hình về nên chưa tìm bàn được. Quét mã này bằng điện thoại để nối, '
                'nối xong bấm Tìm bàn.'), [khoi_qr_camera(hub, cam)]
    jid, fut = hub.new_job(cam, 'find_tables', box=None, frame_w=0, frame_h=0)
    try:
        res = await asyncio.wait_for(fut, cho_s)
    except asyncio.TimeoutError:
        hub.jobs.pop(jid, None)
        return f'Máy camera {cam} chưa trả lời. Kiểm tra máy camera còn chạy rồi hỏi lại.', []
    if not isinstance(res, dict) or res.get('error'):
        loi = res.get('error') if isinstance(res, dict) else 'kết quả sai dạng'
        return f'Camera chưa tìm được bàn: {loi}.', []
    b = khoi_ban(hub, cam, res)
    if b is None:
        return (f'Camera {cam} chưa thấy bàn nào. Chỉnh camera thấy rõ mặt bàn rồi thử lại, hoặc vẽ tay '
                'ở Cài đặt, mục Vùng bàn.'), []
    n = len(b['tables'])
    ans = f'Camera thấy {n} bàn, đặt tên B1 tới B{n} từ trái sang phải. Xem hình rồi bấm Lưu.'
    if b['merged'] is not None:
        moi = len(b['merged']) - len(b['existing'])
        ans = (f"Camera thấy {n} bàn; {cam} đang có {len(b['existing'])} bàn, "
               + (f'{moi} bàn là mới.' if moi else 'không có bàn nào mới.') + ' Chọn thay hết hoặc chỉ thêm bàn mới.')
    return ans, [b]


# ====================================================================== nhân viên
def _tach(x):
    if isinstance(x, str):
        return [p for p in re.split(r'[;\n]+', x) if p.strip()]
    return [str(p) for p in x or [] if str(p).strip()]


def khoi_nhan_vien(hub, them=(), bo=(), doi=()):
    """(khối xac_nhan, lời báo). them: 'Tên | vai trò'; bo: tên hoặc mã; doi: 'tên | tên mới | vai trò mới'.
    Khối chứa các dòng thay đổi; `base` là danh sách lúc dựng để giao diện biết dữ liệu có vừa bị sửa không."""
    dung = {s['id'] for s in hub.staff}
    rows, bao = [], []
    for x in _tach(them):
        phan = [p.strip() for p in x.split('|')]
        ten = _ten_dep(phan[0])
        if not ten:
            continue
        if _tim_nv(hub, ten):
            bao.append(f'{ten} đã có trong danh sách')
            continue
        ma = ma_nv(ten, dung)
        dung.add(ma)
        rows.append(dict(change='them', id=ma, name=ten, role=vai_tro(phan[1] if len(phan) > 1 else ''),
                         old_name=None, old_role=None, photos=0))
    for x in _tach(bo):
        s = _tim_nv(hub, x)
        if s is None:
            bao.append(f'không có ai tên {x.strip()}')
            continue
        rows.append(dict(change='bo', id=s['id'], name=s['name'], role=s['role'], old_name=s['name'],
                         old_role=s['role'], photos=len(s.get('photos') or [])))
    for x in _tach(doi):
        phan = [p.strip() for p in x.split('|')]
        s = _tim_nv(hub, phan[0])
        if s is None:
            bao.append(f'không có ai tên {phan[0]}')
            continue
        ten = _ten_dep(phan[1]) if len(phan) > 1 and phan[1] else s['name']
        role = vai_tro(phan[2], s['role']) if len(phan) > 2 and phan[2] else s['role']
        if ten == s['name'] and role == s['role']:
            continue
        rows.append(dict(change='doi', id=s['id'], name=ten, role=role, old_name=s['name'], old_role=s['role'],
                         photos=len(s.get('photos') or [])))
    if not rows:
        return None, '; '.join(bao) or 'Không có thay đổi nào.'
    return dict(type='xac_nhan', kind='staff', title='Nhân viên', rows=rows,
                base=[dict(id=s['id'], name=s['name'], role=s['role']) for s in hub.staff]), '; '.join(bao)


def khoi_them_trong(hub):
    """Khối thêm một người với ô trống, khi không đọc được tên từ câu."""
    return dict(type='xac_nhan', kind='staff', title='Thêm nhân viên',
                rows=[dict(change='them', id='', name='', role='serve', old_name=None, old_role=None, photos=0)],
                base=[dict(id=s['id'], name=s['name'], role=s['role']) for s in hub.staff])


def doc_them_nv(cau):
    """'thêm nhân viên Lan phục vụ, Hoa với anh Tư dọn bàn' -> ['Lan | serve', 'Hoa | serve', 'Tư | clean'].
    Đọc từ câu có dấu; người không nói vai trò lấy vai trò của người kế sau (nói gộp), không có thì phục vụ."""
    m = re.search(r'(?:thêm|them)\s+(?:nhân viên|nhan vien|người|nguoi|bạn|ban)?\s*(.+)$', cau or '', re.I)
    if not m:
        return []
    phan = [p for p in re.split(r'\s*(?:,|;|\bvà\b|\bva\b|\bvới\b|\bvoi\b)\s*', m.group(1), flags=re.I) if p.strip()]
    out = []
    for p in phan:
        q = bo_dau(p)
        role = next((r for k, r in _VAI if re.search(rf'(?<![a-z]){k}(?![a-z])', q)), None)
        ten = p
        for w in sorted({k for k, _ in _VAI}, key=len, reverse=True):     # bỏ từ vai trò khỏi tên
            ten = re.sub(rf'(?i)(?<![^\W\d_])' + _mau_co_dau(w) + r'(?![^\W\d_])', ' ', ten)
        ten = re.sub(r'(?i)^\s*(?:anh|chị|chi|em|cô|co|chú|chu|bạn|ban|lo|làm|lam)\s+', '', ten)
        ten = re.sub(r'(?i)\s+(?:lo|làm|lam)\s*$', '', ten)
        ten = _ten_dep(ten)
        if ten and len(ten) <= 30 and bo_dau(ten) not in ('nguoi', 'nhan vien', 'ban', 'moi', 'nguoi moi'):
            out.append([ten, role])
    for i in range(len(out) - 2, -1, -1):          # "Lan với Hoa chạy bàn": Lan cũng chạy bàn
        if out[i][1] is None:
            out[i][1] = out[i + 1][1]
    return [f"{t} | {r or 'serve'}" for t, r in out]


def _mau_co_dau(w):
    """Mẫu regex khớp một từ khoá không dấu với chữ có dấu ('don ban' khớp 'dọn bàn')."""
    nhom = {'a': '[aàáảãạăằắẳẵặâầấẩẫậ]', 'e': '[eèéẻẽẹêềếểễệ]', 'i': '[iìíỉĩị]', 'o': '[oòóỏõọôồốổỗộơờớởỡợ]',
            'u': '[uùúủũụưừứửữự]', 'y': '[yỳýỷỹỵ]', 'd': '[dđ]', ' ': r'\s+'}
    return ''.join(nhom.get(ch, re.escape(ch)) for ch in w)


# ====================================================================== luật báo
# Mỗi dòng: (khoá trong khối, nhãn, đơn vị, khoá cài đặt, nhỏ nhất, lớn nhất, nhóm).
# Đơn vị: bat_tat (công tắc), giay, phut (cài đặt giữ giây, khối hiện phút), gio ("HH:MM").
# Khoá cài đặt None: ba công tắc AI, đổi qua verify_kinds / hold_until_verified.
# Không bao giờ có blur_faces ở đây: khoá đó cần PIN chủ quán, chỉ đổi ở trang Cài đặt.
# Thêm cài đặt mới (vùng ngồi...) thì thêm một dòng ở đây và một tham số ở THAM_SO_LUAT.
LUAT = [
    ('verify_call', 'AI kiểm tra báo "khách gọi"', 'bat_tat', None, None, None, 'phuc_vu'),
    ('verify_clear', 'AI kiểm tra báo "cần dọn bàn"', 'bat_tat', None, None, None, 'phuc_vu'),
    ('hold_clear', 'Chờ AI xác nhận rồi mới báo dọn bàn', 'bat_tat', None, None, None, 'phuc_vu'),
    ('escalate_s', 'Nhắc lại nếu chưa ai nhận sau', 'giay', 'escalate_s', 0, 900, 'phuc_vu'),
    ('auto_close_s', 'Tự đóng việc không ai nhận sau', 'giay', 'auto_close_s', 0, 3600, 'phuc_vu'),
    ('table_check_s', 'AI xem lại mỗi bàn sau', 'phut', 'table_check_s', 0, 60, 'phuc_vu'),
    ('wait_greet_s', 'Nhắc khi khách ngồi mà chưa ai tiếp sau', 'phut', 'wait_greet_s', 0, 120, 'phuc_vu'),
    ('wait_food_s', 'Nhắc khi khách chờ món quá', 'phut', 'wait_food_s', 0, 240, 'phuc_vu'),
    ('wait_bill_s', 'Nhắc khi khách ăn xong mà chưa ai ghé sau', 'phut', 'wait_bill_s', 0, 240, 'phuc_vu'),
    ('open_time', 'Giờ mở cửa', 'gio', 'open_time', None, None, 'an_ninh'),
    ('close_time', 'Giờ đóng cửa', 'gio', 'close_time', None, None, 'an_ninh'),
    ('guard_mode', 'Trông quán (coi như quán đang đóng)', 'bat_tat', 'guard_mode', None, None, 'an_ninh'),
    ('sec_after_hours', 'Báo khi có người trong quán ngoài giờ', 'bat_tat', 'sec_after_hours', None, None, 'an_ninh'),
    ('sec_restricted', 'Báo khi người lạ vào quầy hay kho', 'bat_tat', 'sec_restricted', None, None, 'an_ninh'),
    ('sec_item_taken', 'Báo khi có người cầm đồ của khách', 'bat_tat', 'sec_item_taken', None, None, 'an_ninh'),
    ('delivery_from', 'Giờ giao hàng từ (không báo vào kho)', 'gio', 'delivery_from', None, None, 'an_ninh'),
    ('delivery_to', 'Giờ giao hàng tới', 'gio', 'delivery_to', None, None, 'an_ninh'),
    ('hold_s', 'Giữ bàn khi khách tạm rời còn để đồ', 'phut', 'hold_s', 1, 1440, 'an_ninh'),
]
CAN_AI = ('verify_call', 'verify_clear', 'hold_clear')
GIO_TRONG_DUOC = ('delivery_from', 'delivery_to')       # để trống là không có khung giờ giao hàng
# tên tham số của công cụ (tiếng Việt) -> khoá trong khối
THAM_SO_LUAT = dict(kiem_tra_khach_goi='verify_call', kiem_tra_don_ban='verify_clear',
                    cho_ai_roi_moi_bao_don='hold_clear', nhac_lai_sau_giay='escalate_s',
                    tu_dong_sau_giay='auto_close_s', ai_xem_ban_moi_phut='table_check_s',
                    nhac_chua_tiep_phut='wait_greet_s', nhac_cho_mon_phut='wait_food_s',
                    nhac_tinh_tien_phut='wait_bill_s', gio_mo_cua='open_time', gio_dong_cua='close_time',
                    trong_quan='guard_mode', bao_ngoai_gio='sec_after_hours', bao_vao_quay_kho='sec_restricted',
                    bao_cam_do_khach='sec_item_taken', giao_hang_tu='delivery_from', giao_hang_den='delivery_to',
                    giu_ban_phut='hold_s')


def _gio(v):
    """'7h', '07:00', '7:5', '22h30' -> '07:00', '07:05', '22:30'; sai thì None."""
    m = re.fullmatch(r'\s*(\d{1,2})\s*(?:[:h]|gio)?\s*(\d{1,2})?\s*', bo_dau(str(v or '')))
    if not m or int(m.group(1)) > 23 or int(m.group(2) or 0) > 59:
        return None
    return f'{int(m.group(1)):02d}:{int(m.group(2) or 0):02d}'


def gia_tri_luat(st):
    """Giá trị hiện tại của từng dòng luật, theo đơn vị hiện trên khối."""
    from .an_ninh import DEFAULTS as AN_NINH
    out = dict(verify_call='call' in st.get('verify_kinds', []),
               verify_clear='needs_clearing' in st.get('verify_kinds', []),
               hold_clear='needs_clearing' in st.get('hold_until_verified', []))
    for k, _, dv, key, *_ in LUAT:
        if not key:
            continue
        v = st.get(key, AN_NINH.get(key))
        out[k] = (bool(v) if dv == 'bat_tat' else str(v or '') if dv == 'gio'
                  else round((v or 0) / 60, 1) if dv == 'phut' else int(v or 0))
    return out


def khoi_luat(hub, doi=None, nhom='phuc_vu'):
    """(khối xac_nhan, lỗi). doi: {khoá trong khối: giá trị mới}; rỗng thì hiện mọi dòng của `nhom`
    (phuc_vu hoặc an_ninh) để tự chỉnh."""
    cu = gia_tri_luat(hub.settings)
    doi = dict(doi or {})
    co_hoi = bool(doi)          # có hỏi đổi mục nào không (khác với "cho xem để tự chỉnh")
    loi = []
    for k, v in list(doi.items()):
        dong = next((d for d in LUAT if d[0] == k), None)
        if dong is None:
            doi.pop(k)
            continue
        _, nhan, dv, _, lo, hi, _ = dong
        if dv == 'bat_tat':
            if not isinstance(v, bool):
                v = bo_dau(str(v)) in ('true', 'bat', 'co', '1', 'on')
            if k in CAN_AI and not hub.gemini.enabled and v:
                loi.append(f'"{nhan}" cần AI, mà máy chủ chưa có khoá AI')
                doi.pop(k)
                continue
            doi[k] = v
        elif dv == 'gio':
            g = '' if k in GIO_TRONG_DUOC and not str(v or '').strip() else _gio(v)
            if g is None:
                loi.append(f'"{nhan}" phải là giờ dạng HH:MM, ví dụ 07:00')
                doi.pop(k)
                continue
            doi[k] = g
        else:
            try:
                v = float(v)
            except (TypeError, ValueError):
                loi.append(f'"{nhan}" phải là số')
                doi.pop(k)
                continue
            if not lo <= v <= hi:
                loi.append(f'"{nhan}" phải từ {lo} tới {hi} {"phút" if dv == "phut" else "giây"}')
                doi.pop(k)
                continue
            doi[k] = int(v) if dv == 'giay' else v
    if co_hoi:
        doi = {k: v for k, v in doi.items() if v != cu[k]}
        if not doi:
            return None, '; '.join(loi) or 'Luật báo đã đúng như vậy rồi, không cần đổi.'
    rows = [dict(key=k, label=nhan, unit=dv, setting=key, before=cu[k], after=doi.get(k, cu[k]), min=lo, max=hi,
                 needs_ai=k in CAN_AI, optional=k in GIO_TRONG_DUOC, group=g)
            for k, nhan, dv, key, lo, hi, g in LUAT if (k in doi if doi else g == nhom)]
    title = 'An ninh' if all(r['group'] == 'an_ninh' for r in rows) else 'Luật báo'
    return dict(type='xac_nhan', kind='settings', title=title, rows=rows, base=cu, ai=hub.gemini.enabled), \
        '; '.join(loi)


# ====================================================================== chụp ảnh nhân viên
def khoi_chup(hub, ten, camera='cam1'):
    s = _tim_nv(hub, ten)
    if s is None:
        return None
    return dict(type='chup', title=f"Ảnh nhận dạng của {s['name']}", camera=_ma_cam(camera), staff_id=s['id'],
                name=s['name'], consent=bool(s.get('consent')), photos=len(s.get('photos') or []))


# ====================================================================== công cụ ADK
def cong_cu(hub, them):
    """Công cụ cài đặt cho TroLy.tools(); chỉ trợ lý của chủ quán có (che_do='phong' bỏ đi, xem CONG_CU_CHI_CHU
    trong tro_ly.py). `them` là hàm thêm khối hiển thị của phiên đó. Không công cụ nào ghi dữ liệu."""

    def noi_camera(camera: str = 'cam1') -> dict:
        """Hiện mã QR để nối điện thoại làm camera của quán. Camera đã nối thì khối hiện hình camera đang chạy.

        Args:
            camera: cam1, cam2, cam3 hoặc cam4. Bỏ trống là cam1.
        """
        b = khoi_qr_camera(hub, camera)
        return dict(dang_gui_hinh=hub.camera_live(b['camera']), **them(b))

    async def tu_tim_ban(camera: str = 'cam1') -> dict:
        """Nhờ camera tự tìm các bàn trong khung hình rồi hiện khung các bàn trên ảnh camera để chủ quán bấm Lưu. Mất tới 12 giây.

        Args:
            camera: cam1, cam2, cam3 hoặc cam4. Bỏ trống là cam1.
        """
        ans, bs = await tim_ban(hub, camera)
        for b in bs:
            them(b)
        return dict(ket_qua=ans, da_hien=bool(bs))

    def sua_nhan_vien(them_nguoi: list[str] = None, bo_nguoi: list[str] = None,
                      doi_nguoi: list[str] = None) -> dict:
        """Hiện khối thêm, bỏ hoặc đổi nhân viên để chủ quán kiểm rồi bấm Lưu. Đưa ít nhất một danh sách.

        Args:
            them_nguoi: mỗi phần tử "Tên | vai trò", ví dụ ["Lan | phục vụ", "Tư | dọn bàn"]. Vai trò: phục vụ, dọn bàn, thu ngân, chủ quán.
            bo_nguoi: tên những người bỏ khỏi danh sách.
            doi_nguoi: mỗi phần tử "tên hiện tại | tên mới | vai trò mới", để trống phần không đổi, ví dụ ["Minh | | dọn bàn"].
        """
        b, bao = khoi_nhan_vien(hub, them_nguoi or [], bo_nguoi or [], doi_nguoi or [])
        if b is None:
            return dict(ket_qua=bao)
        return dict(**them(b), luu_y=bao or None)

    def ma_qr_nhan_vien(ten: str = '') -> dict:
        """Hiện mã QR để nhân viên quét bằng điện thoại, mở app nhân viên nhận việc.

        Args:
            ten: tên một người; bỏ trống là mọi người.
        """
        return them(khoi_qr_nhan_vien(hub, ten), 'Không có nhân viên nào khớp. Thêm nhân viên trước.')

    def doi_luat_bao(kiem_tra_khach_goi: bool = None, kiem_tra_don_ban: bool = None,
                     cho_ai_roi_moi_bao_don: bool = None, nhac_lai_sau_giay: int = None,
                     tu_dong_sau_giay: int = None, ai_xem_ban_moi_phut: float = None,
                     nhac_chua_tiep_phut: float = None, nhac_cho_mon_phut: float = None,
                     nhac_tinh_tien_phut: float = None, gio_mo_cua: str = None, gio_dong_cua: str = None,
                     trong_quan: bool = None, bao_ngoai_gio: bool = None, bao_vao_quay_kho: bool = None,
                     bao_cam_do_khach: bool = None, giao_hang_tu: str = None, giao_hang_den: str = None,
                     giu_ban_phut: float = None, nhom: str = 'phuc_vu') -> dict:
        """Hiện khối đổi luật báo việc và cài đặt an ninh (trước và sau) để chủ quán bấm Lưu. Chỉ đưa tham số muốn đổi; không đưa gì thì hiện mọi mục của nhóm để tự chỉnh. Không đổi được che mặt (cần mã PIN, chủ quán vào Cài đặt).

        Args:
            kiem_tra_khach_goi: AI xem ảnh kiểm tra báo khách gọi.
            kiem_tra_don_ban: AI xem ảnh kiểm tra báo cần dọn bàn.
            cho_ai_roi_moi_bao_don: chờ AI xác nhận rồi mới báo dọn bàn.
            nhac_lai_sau_giay: chưa ai nhận việc sau bấy nhiêu giây thì chuyển người khác, 0 là tắt, tối đa 900.
            tu_dong_sau_giay: tự đóng việc không ai nhận sau bấy nhiêu giây, 0 là tắt, tối đa 3600.
            ai_xem_ban_moi_phut: AI xem lại ảnh mỗi bàn cách bấy nhiêu phút, 0 là tắt.
            nhac_chua_tiep_phut: khách ngồi bấy nhiêu phút mà chưa ai ra tiếp thì nhắc, 0 là tắt.
            nhac_cho_mon_phut: khách chờ món quá bấy nhiêu phút thì nhắc, 0 là tắt.
            nhac_tinh_tien_phut: khách ăn xong bấy nhiêu phút mà chưa ai ghé thì nhắc, 0 là tắt.
            gio_mo_cua: giờ mở cửa, dạng HH:MM.
            gio_dong_cua: giờ đóng cửa, dạng HH:MM.
            trong_quan: bật thì coi như quán đang đóng, ai vào cũng báo.
            bao_ngoai_gio: báo khi có người trong quán ngoài giờ mở cửa.
            bao_vao_quay_kho: báo khi người không phải nhân viên vào quầy hay kho.
            bao_cam_do_khach: báo khi có người cầm đồ khách để quên.
            giao_hang_tu: đầu khung giờ giao hàng (không báo người vào kho), HH:MM; chuỗi rỗng là bỏ khung giờ.
            giao_hang_den: cuối khung giờ giao hàng, HH:MM.
            giu_ban_phut: giữ bàn bấy nhiêu phút khi khách tạm rời còn để đồ.
            nhom: khi không đưa tham số nào: phuc_vu (luật báo việc) hoặc an_ninh (giờ mở cửa, trông quán, các loại báo an ninh).
        """
        doi = {THAM_SO_LUAT[k]: v for k, v in dict(
            kiem_tra_khach_goi=kiem_tra_khach_goi, kiem_tra_don_ban=kiem_tra_don_ban,
            cho_ai_roi_moi_bao_don=cho_ai_roi_moi_bao_don, nhac_lai_sau_giay=nhac_lai_sau_giay,
            tu_dong_sau_giay=tu_dong_sau_giay, ai_xem_ban_moi_phut=ai_xem_ban_moi_phut,
            nhac_chua_tiep_phut=nhac_chua_tiep_phut, nhac_cho_mon_phut=nhac_cho_mon_phut,
            nhac_tinh_tien_phut=nhac_tinh_tien_phut, gio_mo_cua=gio_mo_cua, gio_dong_cua=gio_dong_cua,
            trong_quan=trong_quan, bao_ngoai_gio=bao_ngoai_gio, bao_vao_quay_kho=bao_vao_quay_kho,
            bao_cam_do_khach=bao_cam_do_khach, giao_hang_tu=giao_hang_tu, giao_hang_den=giao_hang_den,
            giu_ban_phut=giu_ban_phut).items() if v is not None}
        b, loi = khoi_luat(hub, doi, 'an_ninh' if bo_dau(str(nhom or '')).startswith('an') else 'phuc_vu')
        if b is None:
            return dict(ket_qua=loi)
        return dict(**them(b), loi=loi or None)

    def chup_anh_nhan_vien(ten: str, camera: str = 'cam1') -> dict:
        """Hiện khối chụp ảnh nhận dạng một nhân viên bằng camera quán (người đó đứng giữa khung hình, phải đồng ý).

        Args:
            ten: tên nhân viên.
            camera: cam1, cam2, cam3 hoặc cam4.
        """
        b = khoi_chup(hub, ten, camera)
        if b is None:
            return dict(ket_qua=f'Không có nhân viên nào tên {ten}.')
        return dict(dang_gui_hinh=hub.camera_live(b['camera']), **them(b))

    return [noi_camera, tu_tim_ban, sua_nhan_vien, ma_qr_nhan_vien, doi_luat_bao, chup_anh_nhan_vien]


# ====================================================================== đường không AI
TU_CAI_DAT = ('setup', 'set up', 'cai dat', 'thiet lap', 'noi camera', 'ket noi camera', 'them camera',
              'gan camera', 'camera dien thoai', 'tim ban', 'do ban', 'them nhan vien', 'them nguoi',
              'bo nhan vien', 'xoa nhan vien', 'ma qr', 'app nhan vien', 'dien thoai nhan vien', 'luat bao',
              'quy tac bao', 'doi luat', 'chup anh', 'anh nhan dang', 'cai dat an ninh', 'gio mo cua',
              'gio dong cua', 'gio giao hang')


def la_cai_dat(cau):
    q = bo_dau(cau)
    return any(k in q for k in TU_CAI_DAT)


async def tra_loi(hub, cau):
    """(câu trả lời, các khối) cho câu cài đặt, None nếu không phải câu cài đặt. Không dùng AI."""
    q = bo_dau(cau)
    if not la_cai_dat(cau):
        return None
    cam = re.search(r'\bcam(?:era)?\s*(\d+)\b', q)
    cam = f'cam{cam.group(1)}' if cam else 'cam1'
    if any(k in q for k in ('tim ban', 'do ban')):
        return await tim_ban(hub, cam)
    if any(k in q for k in ('chup anh', 'anh nhan dang')):
        s = next((s for s in hub.staff if re.search(rf'(?<![a-z]){re.escape(bo_dau(s["name"]))}(?![a-z])', q)), None)
        if s is None:
            return 'Chụp ảnh cho ai? Ví dụ: chụp ảnh nhận dạng cho Lan.', []
        return f"Nhờ {s['name']} đứng giữa khung hình camera {cam}, bật ô đồng ý rồi bấm Chụp.", [khoi_chup(hub, s['name'], cam)]
    if any(k in q for k in ('ma qr', 'app nhan vien', 'dien thoai nhan vien')) and 'camera' not in q:
        b = khoi_qr_nhan_vien(hub)
        if b is None:
            return 'Chưa có nhân viên nào. Hãy thêm nhân viên trước.', [khoi_them_trong(hub)]
        return 'Mỗi người quét mã của mình bằng điện thoại để mở app nhân viên.', [b]
    if any(k in q for k in ('them nhan vien', 'them nguoi')):
        ds = doc_them_nv(cau)
        b, bao = khoi_nhan_vien(hub, them=ds) if ds else (None, '')
        if b is None:
            return ('Điền tên và vai trò rồi bấm Lưu.' + (f' ({bao})' if bao else '')), [khoi_them_trong(hub)]
        return f"Thêm {len(b['rows'])} người, kiểm lại rồi bấm Lưu." + (f' Lưu ý: {bao}.' if bao else ''), [b]
    if any(k in q for k in ('bo nhan vien', 'xoa nhan vien')):
        ten = [s['name'] for s in hub.staff if re.search(rf'(?<![a-z]){re.escape(bo_dau(s["name"]))}(?![a-z])', q)]
        b, bao = khoi_nhan_vien(hub, bo=ten)
        if b is None:
            return 'Bỏ ai? Ví dụ: bỏ nhân viên Minh.', []
        return 'Kiểm lại rồi bấm Lưu.', [b]
    if any(k in q for k in ('cai dat an ninh', 'gio mo cua', 'gio dong cua', 'trong quan', 'gio giao hang')):
        b, _ = khoi_luat(hub, nhom='an_ninh')
        return 'Chỉnh các mục cần đổi rồi bấm Lưu.', [b]
    if any(k in q for k in ('luat bao', 'quy tac bao', 'doi luat')):
        b, _ = khoi_luat(hub)
        return 'Chỉnh các mục cần đổi rồi bấm Lưu.', [b]
    if any(k in q for k in ('noi camera', 'ket noi camera', 'them camera', 'gan camera', 'camera dien thoai')):
        if hub.camera_live(cam):
            return f'Camera {cam} đang gửi hình rồi. Bấm Tìm bàn để camera tự tìm các bàn.', [khoi_qr_camera(hub, cam)]
        return 'Mở camera điện thoại quét mã này, đặt máy nhìn bao quát các bàn.', [khoi_qr_camera(hub, cam)]
    return 'Bạn muốn cài gì? Bấm một việc bên dưới, hoặc nói thẳng, ví dụ "thêm Lan chạy bàn".', []
