"""An ninh và chống trộm: luật của ba loại cảnh báo, giờ mở cửa, vùng không phải bàn, mã PIN chủ quán.

Ba loại cảnh báo:
  - item_taken  (camera gửi `lay_do`): người không thuộc bàn cầm đồ của khách đi.
  - after_hours (`co_nguoi_ngoai_gio`): có người trong quán khi quán đóng.
  - restricted  (`vao_khu_cam`): người không phải nhân viên vào quầy, kho.

Cảnh báo an ninh nằm chung `hub.alerts` (để dùng lại xác minh Gemini, gói ảnh, clip, dòng thời gian, nút trên web),
nhưng có `group='security'`, không giao theo vai trò phục vụ (`assigned_to` luôn None), báo cho danh sách `notify`,
và không tính vào số liệu ca. Module này chỉ giữ phần luật thuần, hub.py gọi vào.
"""
import hashlib
import hmac
import os
from datetime import datetime

SEC_KINDS = ('item_taken', 'after_hours', 'restricted')
EDGE_KIND = {'lay_do': 'item_taken', 'co_nguoi_ngoai_gio': 'after_hours', 'vao_khu_cam': 'restricted'}
KIND_VI = {'item_taken': 'có người lạ cầm đồ của khách', 'after_hours': 'có người trong quán ngoài giờ',
           'restricted': 'có người không phải nhân viên vào khu cấm'}
SETTING_FLAG = {'item_taken': 'sec_item_taken', 'after_hours': 'sec_after_hours', 'restricted': 'sec_restricted'}
AREA_TYPES = {'quay': 'Quầy thu ngân', 'kho': 'Kho, bếp', 'giu_xe': 'Chỗ giữ xe', 'cua': 'Cửa'}
FORBIDDEN_AREAS = ('quay', 'kho')
ROLES = ('serve', 'clean', 'cashier', 'owner')

DEFAULTS = dict(sec_item_taken=True, sec_after_hours=True, sec_restricted=True,
                open_time='07:00', close_time='22:00', guard_mode=False,
                delivery_from='', delivery_to='', blur_faces=True, hold_s=600)
SETTING_KEYS = tuple(DEFAULTS)
AFTER_HOURS_GAP_S = 300       # cùng camera, trong bấy nhiêu giây: gộp vào cảnh báo ngoài giờ cũ, không chuông lại
RESTRICTED_OWNER_S = 30       # khu cấm: thu ngân chưa bấm "Đã biết" sau bấy nhiêu giây thì báo thêm chủ quán
PIN_KEY = '_owner_pin'        # trong settings, không bao giờ gửi ra web


def _hm(s):
    """'HH:MM' -> phút trong ngày; sai định dạng -> None."""
    try:
        h, m = str(s).split(':')
        h, m = int(h), int(m)
    except (ValueError, AttributeError):
        return None
    return h * 60 + m if 0 <= h < 24 and 0 <= m < 60 else None


def _in_range(now_min, a, b):
    """now trong [a, b); khung qua nửa đêm (22:00 tới 06:00) cũng đúng. a == b: rỗng."""
    if a is None or b is None or a == b:
        return False
    return a <= now_min < b if a < b else (now_min >= a or now_min < b)


def _now_min(now):
    return now.hour * 60 + now.minute


def is_closed(settings, now=None):
    """Quán đang đóng: bật "Trông quán", hoặc ngoài giờ mở cửa."""
    if settings.get('guard_mode'):
        return True
    now = now or datetime.now()
    o, c = _hm(settings.get('open_time')), _hm(settings.get('close_time'))
    if o is None or c is None or o == c:
        return False                   # không đặt giờ (hoặc mở cả ngày): chỉ đóng khi bật tay
    return not _in_range(_now_min(now), o, c)


def in_delivery(settings, now=None):
    now = now or datetime.now()
    return _in_range(_now_min(now), _hm(settings.get('delivery_from')), _hm(settings.get('delivery_to')))


def camera_view(settings, now=None):
    """Phần `an_ninh` gửi kèm GET /api/zones cho máy camera."""
    return dict(closed=is_closed(settings, now), after_hours=bool(settings.get('sec_after_hours')),
                restricted=bool(settings.get('sec_restricted')), item_taken=bool(settings.get('sec_item_taken')),
                delivery_now=in_delivery(settings, now), blur_faces=bool(settings.get('blur_faces', True)))


def check_settings(patch):
    """Kiểm tra các khoá an ninh trong PUT /api/settings. ValueError nếu sai."""
    for k in ('sec_item_taken', 'sec_after_hours', 'sec_restricted', 'guard_mode', 'blur_faces'):
        if k in patch and not isinstance(patch[k], bool):
            raise ValueError(f'{k} phải là true hoặc false')
    for k in ('open_time', 'close_time'):
        if k in patch and _hm(patch[k]) is None:
            raise ValueError(f'{k} phải có dạng HH:MM')
    for k in ('delivery_from', 'delivery_to'):
        if k in patch and patch[k] != '' and _hm(patch[k]) is None:
            raise ValueError(f'{k} phải có dạng HH:MM hoặc để trống')
    if 'hold_s' in patch:
        v = patch['hold_s']
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not 10 <= v <= 86400:
            raise ValueError('hold_s phải là số giây từ 10 tới 86400')


def clean_areas(areas):
    """Vùng không phải bàn từ PUT /api/zones. ValueError nếu sai."""
    out = []
    for a in areas or []:
        t = a.get('type')
        if t not in AREA_TYPES:
            raise ValueError(f'loại vùng không hợp lệ: {t}')
        aid = str(a.get('id') or '').strip()
        poly = [[float(x), float(y)] for x, y in a.get('polygon') or []]
        if not aid or len(poly) < 3:
            raise ValueError(f'vùng {aid or "(không tên)"} cần tên và ít nhất 3 điểm')
        out.append(dict(id=aid, type=t, name=str(a.get('name') or '').strip() or AREA_TYPES[t], polygon=poly))
    if len({a['id'] for a in out}) != len(out):
        raise ValueError('có hai vùng trùng tên')
    return out


def area_of(zones, camera, aid):
    for a in (zones.get(camera) or {}).get('areas') or []:
        if a['id'] == aid:
            return a
    return None


def text_vi(a, clock):
    """Một câu ngắn cho nhật ký và màn hình."""
    k, where = a['kind'], a.get('area_name')
    if k == 'item_taken':
        what = a.get('detail') or 'đồ'
        return f"Bàn {a['table']}: có người lạ cầm {what} của khách" if a.get('table') else f'Có người lạ cầm {what}'
    if k == 'after_hours':
        return f"Có người trong quán lúc {clock(a['created_at'])[:5]}" + (f' ({where})' if where else '')
    return f'Có người không phải nhân viên vào {where or "khu cấm"}'


def recipients(staff, online, kind, escalated=False):
    """Ai nhận cảnh báo. item_taken: phục vụ đang online và chủ quán; after_hours: chủ quán (không có thì mọi người);
    restricted: thu ngân đang online, thêm chủ quán khi đã quá RESTRICTED_OWNER_S hoặc không có thu ngân online."""
    owners = [s['id'] for s in staff if s['role'] == 'owner']
    on = lambda s: online.get(s['id'], 0) > 0     # noqa: E731
    if kind == 'item_taken':
        return [s['id'] for s in staff if s['role'] == 'serve' and on(s)] + owners
    if kind == 'after_hours':
        return owners or [s['id'] for s in staff]
    cashiers = [s['id'] for s in staff if s['role'] == 'cashier' and on(s)]
    return cashiers + owners if escalated or not cashiers else cashiers


# ------------------------------------------------------------ mã PIN chủ quán
def hash_pin(pin, salt=None):
    salt = salt or os.urandom(8).hex()
    return f"{salt}${hashlib.sha256((salt + str(pin)).encode()).hexdigest()}"


def pin_ok(stored, pin):
    if not stored or pin is None:
        return False
    salt, _, _ = stored.partition('$')
    return hmac.compare_digest(stored, hash_pin(pin, salt))


def valid_pin(pin):
    return isinstance(pin, str) and pin.isdigit() and 4 <= len(pin) <= 8
