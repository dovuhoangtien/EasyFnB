"""Xem lại cho trợ lý của chủ quán: video, chuyện của một bàn, bàn đang ở bước nào, và số liệu ngày khác.

Mọi thứ ở đây đọc từ ba nguồn có thật, không bịa:
  - việc đang có trong RAM của Hub (ca hiện tại),
  - dòng thời gian lâu dài (hub.timeline, còn sau khi khởi động lại và sau "bắt đầu ca mới"),
  - kho clip (server/clips.py): clip của từng việc, và clip xin máy camera cắt theo khoảng thời gian.

Dùng chung cho hai đường của trợ lý: đường không AI (tra_loi) và công cụ của tác tử ADK (server/tro_ly.py).

Khối `video`:    {type, title, items: [MucVideo]}
Khối `timeline`: {type, title, items: [{t, text, tone, table, alert_id, video: MucVideo | None}]}
MucVideo: {label, t, table, alert_id, src, clip_id, poster, note, camera, t_from, t_to, error}
  src       đường dẫn mp4 đã sẵn (clip của việc)
  clip_id   yêu cầu clip đang chờ máy camera: màn hình hỏi GET /api/clips/{id} tới khi xong
  error     câu tiếng Việt vì sao không có video (máy camera tắt, chưa ghi hình lúc đó, chưa tới giờ...)
  cả ba đều trống: màn hình tự xin clip [t_from, t_to] của `camera` khi người xem bấm vào
"""
import asyncio
import concurrent.futures
import re
from collections import Counter
from datetime import datetime, timedelta

from .giai_doan import ACTIVE, NUDGE_VI
from .hub import CLOSED, KIND_VI, clock, now_ms, where, where_l
from .timeline import DOI_NGAY_H, VN, day_of
from .tro_ly import (FAST_S, MUC_TONE, MUC_VI, _cung_ban, bo_dau, cau_dem, cau_su_kien, cho_mo, chu_cho,
                     khoi_bang, khoi_su_kien, loc_su_kien, muc, nhan_xet, ten_nv, viec, wait_s)

TRUOC_MS, SAU_MS = 8_000, 12_000     # clip quanh một sự kiện: 8 giây trước tới 12 giây sau
MAX_MS = 60_000                      # clip dài nhất máy chủ cho xin
MAX_VIDEO = 6                        # số clip nhiều nhất trong một khối
XIN_NGAY = 2                         # chỉ xin sẵn chừng này clip; clip còn lại xin khi người xem bấm vào
GIU_VIDEO_MS = 26 * 3600_000         # máy camera giữ video khoảng một ngày
MAX_DONG = 40                        # số dòng nhiều nhất của khối dòng thời gian
SAP_CO_CLIP_MS = 20_000              # việc mới hơn mức này: clip sự kiện sắp tới, màn hình tự chờ

VIEC_VI = {'call': 'Khách gọi phục vụ', 'needs_clearing': 'Bàn cần dọn', 'new_guest': 'Báo nhân viên ra đón khách'}
BUOC_VI = {'seated': 'Mới ngồi, chờ nhân viên ra tiếp', 'greeted': 'Đã có người tiếp, chờ món',
           'served': 'Đã lên món, đang ăn', 'finished': 'Đã ăn xong'}
NHAC_VI = {'greet': 'Chưa ai ra tiếp', 'food': 'Chờ món lâu', 'bill': 'Có thể đang chờ tính tiền'}
BUOI = {'sang': (6, 0, 11, 0), 'trua': (11, 0, 13, 30), 'chieu': (13, 30, 18, 0), 'toi': (18, 0, 23, 0),
        'dem': (21, 0, 23, 59)}
BUOI_VI = {'sang': 'sáng', 'trua': 'trưa', 'chieu': 'chiều', 'toi': 'tối', 'dem': 'đêm'}
THU = {'hai': 0, '2': 0, 'ba': 1, '3': 1, 'tu': 2, '4': 2, 'nam': 3, '5': 3, 'sau': 4, '6': 4, 'bay': 5, '7': 5}
THU_VI = ['thứ hai', 'thứ ba', 'thứ tư', 'thứ năm', 'thứ sáu', 'thứ bảy', 'chủ nhật']
SO = {'mot': 1, 'hai': 2, 'ba': 3, 'bon': 4, 'nam': 5, 'sau': 6, 'bay': 7, 'tam': 8, 'chin': 9, 'muoi': 10,
      'vai': 3, 'may': 3, 'nua': 0.5}
DON_VI_S = {'giay': 1, 'phut': 60, 'tieng': 3600, 'gio': 3600}

TU_XEM = ('video', 'clip', 'xem lai', 'cho xem', 'cho toi xem', 'cho minh xem', 'quay lai', 'coi lai', 'phat lai',
          'chieu lai', 'tua lai', 'show me', 'doan phim', 'mo lai')
TU_KE = ('ke lai', 'ke cho', 'dien bien', 'chuyen gi', 'da xay ra', 'xay ra gi', 'tu luc khach vao', 'tu luc vao',
         'dong thoi gian', 'lich su ban', 'tung buoc', 'tu dau den cuoi', 'tu dau toi cuoi')
TU_BUOC = ('dang cho', 'cho mon', 'cho tinh tien', 'tinh tien', 'chua ai tiep', 'chua duoc tiep', 'chua ai ra',
           'ra tiep', 'giai doan', 'toi dau', 'den dau', 'an xong', 'len mon', 'co mon chua', 'dang the nao',
           'dang ra sao', 'cac ban the nao', 'dang o buoc')


# ====================================================================== ngày và giờ trong câu hỏi
def _ngay(t=None):
    return datetime.strptime(hom_nay(t), '%Y-%m-%d').date()


def hom_nay(t=None):
    return day_of((t or now_ms()) / 1000)


def ten_ngay(day, t=None):
    """'hôm nay', 'hôm qua', 'hôm kia' hoặc 'ngày 12/11'."""
    d = datetime.strptime(day, '%Y-%m-%d').date()
    lech = (_ngay(t) - d).days
    return {0: 'hôm nay', 1: 'hôm qua', 2: 'hôm kia'}.get(lech, f'ngày {d.day:02d}/{d.month:02d}')


def dau_ngay_s(day):
    """Giây epoch lúc ngày đó của quán bắt đầu (4 giờ sáng giờ Việt Nam, xem timeline.DOI_NGAY_H)."""
    return datetime.strptime(day, '%Y-%m-%d').replace(tzinfo=VN).timestamp() + DOI_NGAY_H * 3600


def ms_cua(day, h, m=0):
    """Giờ đồng hồ h:m trong ngày của quán; 0 tới 4 giờ sáng thuộc về đêm của ngày đó."""
    nua_dem = dau_ngay_s(day) - DOI_NGAY_H * 3600
    return int((nua_dem + h * 3600 + m * 60 + (86400 if h < DOI_NGAY_H else 0)) * 1000)


def doc_cac_ngay(q, t=None):
    """Các ngày được nhắc trong câu (đã bỏ dấu), theo thứ tự xuất hiện: ['2026-11-12', ...]."""
    nay = _ngay(t)
    got = []

    def them(pos, d):
        if d is not None and all(d != x for _, x in got):
            got.append((pos, d))

    def ngay(y, mo, d):
        try:
            return datetime(int(y), int(mo), int(d)).date()
        except ValueError:
            return None

    for m in re.finditer(r'(?<!\d)(\d{4})-(\d{1,2})-(\d{1,2})(?!\d)', q):
        them(m.start(), ngay(*m.groups()))
    for m in re.finditer(r'(?<![\d/:.-])(\d{1,2})\s*/\s*(\d{1,2})(?:\s*/\s*(\d{4}))?(?![\d/])', q):
        d = ngay(m.group(3) or nay.year, m.group(2), m.group(1))
        if d and not m.group(3) and d > nay:
            d = ngay(nay.year - 1, m.group(2), m.group(1))
        them(m.start(), d)
    for m in re.finditer(r'\bngay\s+(\d{1,2})(?:\s+thang\s+(\d{1,2}))?(?![\d/:h])', q):
        d = ngay(nay.year, m.group(2) or nay.month, m.group(1))
        if d and d > nay:        # "ngày 28" hỏi vào ngày 13: là tháng trước
            truoc = (nay.replace(day=1) - timedelta(days=1))
            d = ngay(nay.year - 1, m.group(2), m.group(1)) if m.group(2) else ngay(truoc.year, truoc.month, m.group(1))
        them(m.start(), d)
    for m in re.finditer(r'\bhom kia\b', q):
        them(m.start(), nay - timedelta(days=2))
    for m in re.finditer(r'\b(?:hom qua|yesterday|(?:sang|trua|chieu|toi|dem) (?:hom )?qua)\b', q):
        them(m.start(), nay - timedelta(days=1))
    for m in re.finditer(r'\b(?:hom nay|today|(?:sang|trua|chieu|toi|dem) nay)\b', q):
        them(m.start(), nay)
    for m in re.finditer(r'\b(?:thu\s*(hai|ba|tu|nam|sau|bay|[2-7])|(chu nhat))\b(?!\s*lan)(\s+tuan truoc)?', q):
        wd = 6 if m.group(2) else THU[m.group(1)]
        lui = (nay.weekday() - wd) % 7
        if m.group(3):
            lui += 7 if lui < nay.weekday() + 1 else 0
            lui = lui or 7
        them(m.start(), nay - timedelta(days=lui))
    return [d.strftime('%Y-%m-%d') for _, d in sorted(got, key=lambda x: x[0])]


def _cac_gio(q):
    """Các giờ đồng hồ trong câu: [(vị trí đầu, vị trí cuối, giờ, phút)]. '12:30', '12h30', '12h', '12 giờ rưỡi',
    '3 giờ chiều', '12 giờ kém 15'. '5 giờ' trơ trọi chỉ tính khi có chữ chỉ thời điểm đi kèm (lúc, khoảng, sáng...)."""
    out = []
    for m in re.finditer(r'(?<![a-z0-9:/.,-])(\d{1,2})\s*(:|gio|h|g)(?:\s*(\d{2}(?!\d)|ruoi))?', q):
        h, sep, ph = int(m.group(1)), m.group(2), m.group(3)
        end = m.end()
        sau = q[end:end + 24]
        if ph is None:
            if sep in (':', 'g'):
                continue
            if re.match(r'[a-z]', sau):                 # '12 hôm', '5 giỏi': không phải giờ
                continue
            if re.match(r'\s*(truoc|vua qua|vua roi|dong ho)', sau):
                continue                                # '2 giờ trước' là khoảng lùi lại, đọc ở chỗ khác
            truoc = q[max(0, m.start() - 14):m.start()]
            if sep == 'gio' and not (re.search(r'(luc|khoang|quanh|tam|tu|den|toi|hoi|vao)\s*$', truoc)
                                     or re.match(r'\s*(sang|trua|chieu|toi|dem|kem)\b', sau)):
                continue
        elif re.match(r'[a-z0-9]', sau) and ph != 'ruoi':
            continue
        mi = 30 if ph == 'ruoi' else int(ph or 0)
        k = re.match(r'\s*kem\s*(\d{1,2})', sau)
        if k:
            h, mi = h - 1, 60 - int(k.group(1))
            end += k.end()
            sau = q[end:end + 24]
        b = re.match(r'\s*(?:buoi\s+)?(sang|trua|chieu|toi|dem)\b', sau)
        if b:
            buoi = b.group(1)
            if buoi in ('chieu', 'toi') and h < 12:
                h += 12
            elif buoi == 'trua' and h <= 3:
                h += 12
            elif buoi == 'dem':
                h = 0 if h == 12 else h + 12 if 6 <= h < 12 else h
        if 0 <= h < 24 and 0 <= mi < 60:
            out.append((m.start(), end, h, mi))
    return out


def doc_gio(q, t=None):
    """Thời điểm hoặc khoảng thời gian được hỏi (câu đã bỏ dấu). None nếu câu không nhắc giờ nào.

    Trả dict(day, ro_ngay, loai, luc, tu, den, ten, tuong_lai), các mốc là mili giây epoch:
      loai 'phut'    một thời điểm theo giờ đồng hồ ("12:30", "12h30", "12 giờ rưỡi"): luc
      loai 'truoc'   lùi lại từ bây giờ ("5 phút trước"): luc
      loai 'gan'     vừa mới đây ("lúc nãy", "vừa rồi"): tu..den là 10 phút gần nhất
      loai 'khoang'  một khoảng ("từ 12:00 đến 12:30", "trưa nay"): tu..den
    """
    t = t or now_ms()
    ngay = doc_cac_ngay(q, t)
    day = ngay[0] if ngay else hom_nay(t)
    kq = dict(day=day, ro_ngay=bool(ngay), loai=None, luc=None, tu=None, den=None, ten='', tuong_lai=False)
    duoi = '' if day == hom_nay(t) else ' ' + ten_ngay(day, t)

    m = re.search(r'(?<![a-z0-9])(\d{1,3}|mot|hai|ba|bon|nam|sau|bay|tam|chin|muoi|vai|may|nua)\s*'
                  r'(giay|phut|tieng|gio)\s*(?:dong ho\s*)?(?:truoc|vua qua|vua roi)', q)
    if m:
        n = float(m.group(1)) if m.group(1).isdigit() else SO[m.group(1)]
        luc = t - int(n * DON_VI_S[m.group(2)] * 1000)
        return dict(kq, day=day_of(luc / 1000), loai='truoc', luc=luc, ten=clock(luc)[:5])

    gio = _cac_gio(q)
    if len(gio) >= 2 and re.search(r'\b(den|toi)\b|-', q[gio[0][1]:gio[1][0]]):
        tu, den = ms_cua(day, gio[0][2], gio[0][3]), ms_cua(day, gio[1][2], gio[1][3])
        if den > tu:
            ten = f'từ {gio[0][2]:02d}:{gio[0][3]:02d} đến {gio[1][2]:02d}:{gio[1][3]:02d}{duoi}'
            return dict(kq, loai='khoang', tu=tu, den=min(den, t), ten=ten, tuong_lai=tu > t)
    if gio:
        _, _, h, mi = gio[0]
        luc = ms_cua(day, h, mi)
        if luc > t + 60_000 and not ngay and datetime.fromtimestamp(t / 1000, VN).hour < 6 and h >= 18:
            day = day_of(t / 1000 - 86400)          # quá nửa đêm mà hỏi "23:50": là tối hôm qua
            luc, duoi = ms_cua(day, h, mi), ' hôm qua'
        return dict(kq, day=day, loai='phut', luc=luc, ten=f'{h:02d}:{mi:02d}{duoi}', tuong_lai=luc > t + 60_000)

    m = re.search(r'\b(?:buoi\s+)?(sang|trua|chieu|toi|dem)\s+(?:hom\s+)?(nay|qua|kia)\b|\bbuoi\s+(sang|trua|chieu|toi)\b', q)
    if m:
        b = m.group(1) or m.group(3)
        h0, m0, h1, m1 = BUOI[b]
        tu, den = ms_cua(day, h0, m0), ms_cua(day, h1, m1)
        ten = f'{BUOI_VI[b]} {ten_ngay(day, t)}' if day != hom_nay(t) else f'{BUOI_VI[b]} nay'
        return dict(kq, loai='khoang', tu=tu, den=min(den, t), ten=ten, tuong_lai=tu > t)

    if re.search(r'\b(luc nay|vua nay|vua roi|vua xong|moi day|hoi nay|khi nay|vua qua|just now)\b', q):
        return dict(kq, day=hom_nay(t), loai='gan', tu=t - 600_000, den=t, ten='vừa rồi')
    return None


# ====================================================================== bàn và camera
def cac_ban(hub):
    """Tên các bàn hệ thống đang biết: vùng bàn đã vẽ, bàn camera đang báo, bàn có việc trong ca."""
    s = {x['id'] for x in hub.tables.values()} | {a['table'] for a in viec(hub) if a['table']}
    for z in hub.zones.values():
        s |= {str(tb['id']) for tb in z.get('tables', [])}
    return s


def _ban_lich_su(hub):
    rows = hub.timeline.query(kinds=['table', 'stage', 'alert_created'], limit=3000, newest_first=True)
    return {r['table'] for r in rows if r['table']}


def tim_ban(hub, q):
    """Bàn được nhắc trong câu (đã bỏ dấu): 'bàn 3', 'bàn B3', hoặc 'b3' đứng riêng. Trả (tên bàn, có biết bàn này
    không). Không nhắc bàn nào: (None, False). Bàn lạ: (tên như người hỏi gõ, False)."""
    m = re.search(r'\bban\s*(?:so\s*)?([a-z]{0,2}\d{1,3})\b', q)
    keys = [m.group(1)] if m else []
    le = [k for k in re.findall(r'(?<![a-z0-9])([a-z]{1,2}\d{1,3})(?![a-z0-9])', q) if k not in keys]
    biet = sorted(cac_ban(hub), key=str)
    for k in keys + le:
        for tb in biet:
            if _cung_ban(k, tb):
                return tb, True
    if not keys:
        return None, False
    for tb in sorted(_ban_lich_su(hub), key=str):      # máy chủ vừa khởi động lại: bàn chỉ còn trong lịch sử
        if _cung_ban(keys[0], tb):
            return tb, True
    return keys[0].upper(), False


def camera_mac_dinh(hub):
    live = [c for c in hub.cameras if hub.camera_live(c)]
    if live:
        return sorted(live)[0]
    return sorted(hub.cameras)[0] if hub.cameras else sorted(hub.zones)[0] if hub.zones else 'cam1'


def camera_cua_ban(hub, ban):
    """Camera nào nhìn thấy bàn này: camera đang chạy trước, rồi vùng bàn đã vẽ, rồi lịch sử."""
    if not ban:
        return camera_mac_dinh(hub)
    cams = [x['camera'] for x in hub.tables.values() if x['id'] == ban]
    cams += [c for c, z in hub.zones.items() if any(str(tb['id']) == ban for tb in z.get('tables', []))]
    for c in cams:
        if hub.camera_live(c):
            return c
    if cams:
        return cams[0]
    rows = hub.timeline.query(table=ban, limit=20, newest_first=True)
    return next((r['camera'] for r in rows if r['camera']), None) or camera_mac_dinh(hub)


# ====================================================================== việc đọc từ dòng thời gian
def viec_lich_su(hub, since_s, until_s, ban=None):
    """Các việc tạo trong [since_s, until_s] (giây epoch), đọc từ dòng thời gian nên còn cả sau khi khởi động lại
    và của ngày khác. Mỗi việc: dict(t, ban, camera, kind, aid, wait_s, ket, nv, ly_do, t_xong);
    ket: mo | nhan | xong | bo_lo | huy. Cũ trước."""
    rows = hub.timeline.query(since=since_s, until=until_s + 3600, table=ban, kinds='alert_*', limit=5000)
    cur, out = {}, []
    for r in rows:
        d, aid = r['data'], r['alert_id']
        if r['kind'] == 'alert_created':
            if r['ts'] > until_s:
                cur.pop(aid, None)      # mã việc bắt đầu lại từ a1 sau mỗi ca: việc mới này không thuộc khoảng hỏi
                continue
            rec = dict(t=int(r['ts'] * 1000), ban=r['table'], camera=r['camera'], kind=d.get('alert_kind'), aid=aid,
                       wait_s=None, ket='mo', nv=r['staff'], ly_do=None, t_xong=None)
            cur[aid] = rec
            out.append(rec)
            continue
        rec = cur.get(aid)
        if rec is None:
            continue
        if r['kind'] == 'alert_assigned':
            rec['nv'] = r['staff'] or rec['nv']
        elif r['kind'] == 'alert_acked':
            rec['wait_s'] = d.get('wait_s')
            rec['nv'] = r['staff'] or rec['nv']
            if rec['ket'] == 'mo':
                rec['ket'] = 'nhan'
        elif r['kind'] == 'alert_done':
            rec['ket'], rec['t_xong'] = 'xong', int(r['ts'] * 1000)
            if rec['wait_s'] is None:
                rec['wait_s'] = d.get('wait_s')
            rec['nv'] = r['staff'] or rec['nv']
        elif r['kind'] == 'alert_auto_closed':
            rec['ket'], rec['t_xong'] = 'bo_lo', int(r['ts'] * 1000)
        elif r['kind'] == 'alert_cancelled':
            rec['ket'], rec['ly_do'] = 'huy', d.get('reason')
    return [r for r in out if r['kind'] in KIND_VI]


def viec_ram(hub, rec):
    """Việc còn trong RAM ứng với một việc đọc từ lịch sử. Mã việc lặp lại sau mỗi ca nên phải khớp cả giờ tạo."""
    a = hub.alerts.get(rec['aid']) if rec.get('aid') else None
    return a if a is not None and abs(a['created_at'] - rec['t']) < 1500 else None


def _rec(a):
    """Việc trong RAM, đổi sang cùng dạng với việc đọc từ lịch sử."""
    da_nhan = bool(a['acked_at']) or a.get('arrived_s') is not None
    if a['status'] == 'cancelled':
        ket = 'huy'
    elif a['status'] == 'done':
        bo_lo = a['kind'] != 'needs_clearing' and not a.get('arrived_at') and a['done_by'] == 'camera'
        ket = 'bo_lo' if bo_lo else 'xong'
    else:
        ket = 'nhan' if da_nhan else 'mo'
    return dict(t=a['created_at'], ban=a['table'], camera=a['camera'], kind=a['kind'], aid=a['id'],
                wait_s=wait_s(a) if da_nhan else None, ket=ket, nv=a['acked_by'] or a['assigned_to'],
                ly_do=a['cancel_reason'], t_xong=a['done_at'])


def viec_trong_khoang(hub, since_s, until_s, ban=None):
    """Mọi việc tạo trong [since_s, until_s]: việc của ca hiện tại lấy từ RAM (đủ và mới nhất), việc của các ca
    trước và ngày trước lấy từ dòng thời gian. Cũ trước."""
    ram = viec(hub)
    moc = min(a['created_at'] for a in ram) - 2000 if ram else None
    out = [r for r in viec_lich_su(hub, since_s, until_s, ban)
           if not (moc is not None and r['aid'] in hub.alerts and r['t'] >= moc)]
    out += [_rec(a) for a in ram if since_s * 1000 <= a['created_at'] <= until_s * 1000
            and (not ban or a['table'] == ban)]
    return sorted(out, key=lambda r: r['t'])


def duoi_viec(hub, rec):
    """Phần sau của câu về một việc: ai nhận, nhanh hay chậm. '' nếu không rõ kết quả."""
    a = viec_ram(hub, rec)
    if a is not None:
        cau = cau_su_kien(hub, a)
        return cau.split(', ', 1)[1] if ', ' in cau else ''
    nv = ten_nv(hub, rec['nv']) or 'nhân viên'
    if rec['ket'] == 'huy':
        return 'báo nhầm, đã huỷ'
    if rec['ket'] == 'bo_lo':
        return f'{nv} đã nhận nhưng không tới bàn' if rec['wait_s'] is not None and rec['nv'] else 'không ai tới'
    if rec['ket'] in ('nhan', 'xong') and rec['wait_s'] is not None:
        return f"{nv} nhận {MUC_VI[muc(rec['wait_s'])]}"
    return 'đã xong' if rec['ket'] == 'xong' else ''


def tone_viec(hub, rec):
    a = viec_ram(hub, rec)
    if a is not None:
        if a['status'] == 'cancelled':
            return None
        if a['status'] not in CLOSED and not a['acked_at'] and a.get('arrived_s') is None:
            return 'warn'
        w = wait_s(a)
        return MUC_TONE.get(muc(w)) if w is not None else None
    if rec['ket'] == 'bo_lo':
        return 'bad'
    if rec['ket'] in ('nhan', 'xong') and rec['wait_s'] is not None:
        return MUC_TONE[muc(rec['wait_s'])]
    return None


def cau_viec(hub, rec):
    """Một câu cho một việc, ví dụ "Bàn B2 gọi phục vụ, Lan nhận nhanh"."""
    s = f"{where(rec['ban'], rec['camera'])} {KIND_VI[rec['kind']]}"
    d = duoi_viec(hub, rec)
    return f'{s}, {d}' if d else s


# ====================================================================== video
def loi_de_hieu(err):
    """Lời báo của kho clip hay máy camera, nói lại cho chủ quán dễ hiểu."""
    e = bo_dau(err or '')
    if 'khong chay' in e or 'dang tat' in e:
        return 'Máy camera đang tắt nên chưa lấy được video.'
    if 'chua ghi hinh' in e or 'khong ghi hinh' in e:
        return 'Máy camera chưa ghi hình lúc đó.'
    if 'khong tra loi' in e or 'khong gui' in e:
        return 'Máy camera không trả lời nên chưa lấy được video.'
    if 'chua toi gio' in e:
        return 'Chưa tới giờ đó nên chưa có video.'
    if 'khong co video luu' in e:
        return 'Không có video lưu lại cho lúc đó.'
    return 'Chưa lấy được video lúc đó.'


def xin_clip(clips, camera, t_from, t_to, loop=None):
    """Xin kho clip cắt một đoạn. Trả ClipRequest (dict) hoặc None nếu không xin được ngay (màn hình sẽ tự xin).
    Kho clip phải được gọi trong vòng lặp asyncio; công cụ ADK có thể chạy ở luồng khác nên chuyển về vòng lặp."""
    def goi():
        try:
            return clips.request(camera, int(t_from), int(t_to))
        except ValueError as e:
            return dict(id=None, status='failed', error=str(e), t_from=t_from, t_to=t_to)
        except Exception as e:      # noqa: BLE001  kho clip hỏng không được làm hỏng câu trả lời
            return dict(id=None, status='failed', error=f'{type(e).__name__}', t_from=t_from, t_to=t_to)
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        if loop is None or not loop.is_running():
            return None
        f = concurrent.futures.Future()
        loop.call_soon_threadsafe(lambda: f.set_result(goi()))
        try:
            return f.result(2.0)
        except Exception:           # noqa: BLE001
            return None
    return goi()


class Xin:
    """Ngữ cảnh dựng video của một câu trả lời: kho clip, vòng lặp, và số clip đã xin sẵn."""

    def __init__(self, hub, clips=None, loop=None):
        self.hub, self.clips, self.loop, self.da_xin = hub, clips, loop, 0

    def muc(self, t, camera, ban=None, a=None, label='', note=None, tu=None, den=None, xin=True):
        """Một mục video quanh thời điểm `t` (ms). `a` là việc trong RAM nếu có (để lấy clip sẵn và ảnh)."""
        tu = int(tu if tu is not None else t - TRUOC_MS)
        den = int(den if den is not None else t + SAU_MS)
        den = min(den, tu + MAX_MS)
        ev = (a.get('evidence') or {}) if a else {}
        it = dict(label=label, t=int(t), table=ban, alert_id=a['id'] if a else None, src=None, clip_id=None,
                  poster=(ev.get('overview') or a.get('crop_url')) if a else None, note=note,
                  camera=camera, t_from=tu, t_to=den, error=None)
        now = now_ms()
        if a and a.get('clip'):
            it['src'] = f"/api/alerts/{a['id']}/clip.mp4"
        elif self.clips is None:
            it['error'] = 'Máy chủ chưa bật lưu video, nên chỉ có ảnh camera lúc đó.'
        elif tu > now:
            it['error'] = 'Chưa tới giờ đó nên chưa có video.'
        elif now - den > GIU_VIDEO_MS:
            it['error'] = 'Máy camera chỉ giữ video khoảng một ngày, nên không còn hình lúc đó.'
        elif a and now - a['created_at'] < SAP_CO_CLIP_MS:
            pass                    # clip của việc sắp tới nơi: màn hình chờ, quá lâu thì tự xin
        elif xin and self.da_xin < XIN_NGAY:
            self.da_xin += 1
            r = xin_clip(self.clips, camera, tu, min(den, now), self.loop)
            if r is not None and r.get('status') == 'failed':
                it['error'] = loi_de_hieu(r.get('error'))
            elif r is not None:
                it.update(clip_id=r['id'], t_from=r['t_from'], t_to=r['t_to'])
        return it

    def muc_viec(self, rec, xin=True):
        a = viec_ram(self.hub, rec)
        d = duoi_viec(self.hub, rec)
        return self.muc(rec['t'], rec['camera'] or camera_cua_ban(self.hub, rec['ban']), rec['ban'], a,
                        label=f"{where(rec['ban'], rec['camera'])} {KIND_VI[rec['kind']]}",
                        note=(d[:1].upper() + d[1:]) if d else None, xin=xin)


def khoi_video(title, items):
    items = [it for it in items if it][:MAX_VIDEO]
    return dict(type='video', title=title or 'Video camera', items=items) if items else None


def co_video(b):
    """Khối video có ít nhất một clip xem được (sẵn, đang lấy, hoặc xin được khi bấm) không."""
    return bool(b) and any(not it['error'] for it in b['items'])


def _cau_video(b, mot='Video ở ngay bên dưới.', nhieu='Video từng lần ở ngay bên dưới.'):
    """Câu nói về video trong câu trả lời: có thì chỉ xuống dưới, không thì nói vì sao."""
    if b is None:
        return ''
    if co_video(b):
        return ' ' + (mot if len(b['items']) == 1 else nhieu)
    return ' ' + b['items'][0]['error']


# ====================================================================== chuyện của một bàn, một quãng giờ
def dong_thoi_gian(hub, since_s, until_s, ban=None, xin=None):
    """Các dòng kể lại [since_s, until_s]: khách vào, nhân viên ra tiếp, món lên, khách gọi, ăn xong, rời, dọn.
    Mỗi dòng: dict(t, text, tone, table, alert_id, video, _loai). Cũ trước. `ban` trống thì kể mọi bàn (câu có tên bàn)."""
    def gioi_han(key):
        try:
            return float(hub.settings.get(key) or 0)
        except (TypeError, ValueError):
            return 0

    rows = hub.timeline.query(since=since_s, until=until_s, table=ban, kinds=['stage', 'nudge', 'log', 'table'],
                              limit=5000)
    out = []

    def them(ts_ms, text, tone, tb, cam, loai, rec=None):
        if not ban:
            text = f'Bàn {tb}: {text[:1].lower()}{text[1:]}' if tb else text
        v = None
        if xin is not None and xin.clips is not None:
            v = xin.muc_viec(rec, xin=False) if rec else xin.muc(ts_ms, cam or camera_cua_ban(hub, tb), tb,
                                                              label=text, xin=False)
            if v['error']:
                v = None
        a = viec_ram(hub, rec) if rec else None
        out.append(dict(t=int(ts_ms), text=text, tone=tone, table=tb, alert_id=a['id'] if a else None, video=v,
                        _loai=loai))

    for r in rows:
        d, tb = r['data'], r['table']
        ts = r['ts'] * 1000
        if r['kind'] == 'stage':
            st, prev_s = d.get('stage'), d.get('prev_s') or 0
            if st == 'seated':
                them(ts, 'Khách vào bàn', None, tb, r['camera'], 'vao')
            elif st == 'greeted':
                cham = 0 < gioi_han('wait_greet_s') < prev_s
                them(ts, 'Nhân viên ra tiếp' + (', sau khi khách ngồi khá lâu' if cham else ''),
                     'warn' if cham else 'good', tb, r['camera'], 'tiep')
            elif st == 'served':
                cham = d.get('prev') == 'greeted' and 0 < gioi_han('wait_food_s') < prev_s
                them(ts, 'Món đã lên' + (', sau khi khách chờ khá lâu' if cham else ''),
                     'warn' if cham else 'good', tb, r['camera'], 'mon')
            elif st == 'finished':
                them(ts, 'Khách ăn xong', None, tb, r['camera'], 'an_xong')
            elif st == 'left':
                them(ts, 'Khách rời bàn', None, tb, r['camera'], 'roi')
        elif r['kind'] == 'nudge':
            cau = NUDGE_VI.get(d.get('nudge'))
            if cau:
                them(ts, cau[:1].upper() + cau[1:], 'warn', tb, r['camera'], 'nhac')
        elif r['kind'] == 'log' and d.get('log_kind') == 'cleared' and tb:
            them(ts, 'Bàn đã dọn xong', 'good', tb, r['camera'], 'don')
        elif r['kind'] == 'log' and d.get('log_kind') == 'looking' and tb:
            them(ts, 'Khách nhìn quanh tìm nhân viên', 'warn', tb, r['camera'], 'nhin')
        elif r['kind'] == 'table' and d.get('away') and tb:
            them(ts, 'Khách tạm rời, còn để đồ ở bàn nên chưa báo dọn', None, tb, r['camera'], 'tam_roi')
    for rec in viec_trong_khoang(hub, since_s, until_s, ban):
        d = duoi_viec(hub, rec)
        them(rec['t'], VIEC_VI.get(rec['kind'], KIND_VI.get(rec['kind'], rec['kind'])) + (f', {d}' if d else ''), tone_viec(hub, rec), rec['ban'], rec['camera'],
             'viec_' + rec['kind'], rec)
        if rec['kind'] == 'needs_clearing' and rec['ket'] == 'xong' and rec['t_xong'] and rec['t_xong'] / 1000 <= until_s:
            them(rec['t_xong'], 'Bàn đã dọn xong', 'good', rec['ban'], rec['camera'], 'don')
    out.sort(key=lambda x: x['t'])
    gon = []
    for x in out:       # camera báo "đã dọn" và việc dọn đóng cùng lúc: chỉ giữ một dòng
        if x['_loai'] == 'don' and any(y['_loai'] == 'don' and y['table'] == x['table'] and x['t'] - y['t'] < 5000
                                       for y in gon[-4:]):
            continue
        gon.append(x)
    return gon


def khoi_dong_thoi_gian(title, dong):
    """Khối `timeline` từ các dòng của dong_thoi_gian. Quá dài thì giữ phần mới nhất."""
    if not dong:
        return None
    items = [{k: v for k, v in x.items() if not k.startswith('_')} for x in dong[-MAX_DONG:]]
    return dict(type='timeline', title=title, items=items)


def _luot_khach(hub, ban, d0, d1, quanh_s=None):
    """(đầu, cuối) của một lượt khách ở bàn: từ lúc khách vào tới trước lượt sau (gồm cả lúc dọn bàn).
    Có `quanh_s` thì lấy lượt chứa thời điểm đó, không thì lấy lượt mới nhất. None nếu chưa có lượt nào."""
    seats = [r['ts'] for r in hub.timeline.query(since=d0, until=d1, table=ban, kinds='stage', limit=5000)
             if r['data'].get('stage') == 'seated']
    if not seats:
        return None
    i = len(seats) - 1
    if quanh_s is not None:
        truoc = [k for k, ts in enumerate(seats) if ts <= quanh_s + 60]
        i = truoc[-1] if truoc else 0
    return seats[i] - 5, (seats[i + 1] - 1 if i + 1 < len(seats) else d1)


def ke_lai(hub, ban=None, gio=None, day=None, xin=None, t=None):
    """Kể lại chuyện của một bàn hoặc một quãng giờ. Trả (câu trả lời, khối, các dòng)."""
    t = t or now_ms()
    day = day or (gio['day'] if gio else hom_nay(t))
    d0 = dau_ngay_s(day)
    d1 = min(d0 + 86400 - 0.001, t / 1000)
    ten_d = ten_ngay(day, t)
    if gio and gio['tuong_lai']:
        return f"Chưa tới {gio['ten']} nên chưa có gì để kể lại.", [], []
    if gio and gio['loai'] in ('khoang', 'gan'):
        since, until, quang = gio['tu'] / 1000, gio['den'] / 1000, gio['ten']
    elif gio and ban:
        luot = _luot_khach(hub, ban, d0, d1, gio['luc'] / 1000)
        since, until = luot or (gio['luc'] / 1000 - 1800, gio['luc'] / 1000 + 1800)
        quang = f"quanh {gio['ten']}"
    elif gio:
        since, until, quang = gio['luc'] / 1000 - 300, gio['luc'] / 1000 + 300, f"quanh {gio['ten']}"
    elif ban:
        since, until = _luot_khach(hub, ban, d0, d1) or (d0, d1)
        quang = ten_d
    else:
        since, until, quang = d0, d1, ten_d
    until = min(until, t / 1000)
    dong = dong_thoi_gian(hub, since, until, ban, xin)
    dau = f'Bàn {ban}' if ban else 'Quán'
    if not dong:
        return f'{dau} {quang} chưa có gì được ghi lại.', [], []

    def luc(loai):
        x = next((x for x in dong if x['_loai'] == loai), None)
        return clock(x['t'])[:5] if x else None

    buoc = [(f'khách vào lúc {luc("vao")}', luc('vao')), (f'nhân viên ra tiếp lúc {luc("tiep")}', luc('tiep')),
            (f'món lên lúc {luc("mon")}', luc('mon')), (f'ăn xong lúc {luc("an_xong")}', luc('an_xong')),
            (f'khách rời lúc {luc("roi")}', luc('roi')), (f'bàn dọn xong lúc {luc("don")}', luc('don'))]
    buoc = [c for c, co in buoc if co]
    goi = sum(1 for x in dong if x['_loai'] == 'viec_call')
    nhac = [x for x in dong if x['_loai'] == 'nhac']
    if ban and buoc:
        ans = f'Bàn {ban} {quang}: ' + ', '.join(buoc) + '.'
        if goi:
            ans += f' Trong lúc đó khách gọi phục vụ {goi} lần.'
        if nhac:
            ans += f" Có lúc khách phải chờ khá lâu: {nhac[0]['text'][:1].lower()}{nhac[0]['text'][1:]}."
    else:
        ans = f'{dau} {quang} có {len(dong)} việc được ghi lại'
        ans += f', trong đó khách gọi phục vụ {goi} lần.' if goi else '.'
        ans += ' Từng bước ở bên dưới.'
    blocks = [khoi_dong_thoi_gian(f'{dau} {quang}, từng bước', dong)]
    if xin is not None and xin.clips is not None:
        chinh = [x for x in dong if x['_loai'].startswith('viec_') and x['video']][-3:] or \
                [x for x in dong if x['_loai'] == 'vao' and x['video']][-1:]
        items = []
        for x in chinh:
            v = dict(x['video'])
            if not v['src'] and xin.da_xin < XIN_NGAY and not (v['alert_id'] and t - v['t'] < SAP_CO_CLIP_MS):
                xin.da_xin += 1
                r = xin_clip(xin.clips, v['camera'], v['t_from'], min(v['t_to'], t), xin.loop)
                if r is not None and r.get('status') == 'failed':
                    v['error'] = loi_de_hieu(r.get('error'))
                elif r is not None:
                    v.update(clip_id=r['id'], t_from=r['t_from'], t_to=r['t_to'])
            items.append(v)
        vb = khoi_video('Video các lúc chính', items)
        if vb:
            blocks.append(vb)
            if co_video(vb):
                ans += ' Có video các lúc chính ở dưới.'
    return ans, blocks, dong


# ====================================================================== xem video
def xem_thoi_diem(hub, gio, ban=None, xin=None, muon_xem=True, t=None):
    """Xem lại một thời điểm hoặc một quãng giờ (có thể kèm bàn). Trả (câu trả lời, khối)."""
    t = t or now_ms()
    o_ban = f' ở bàn {ban}' if ban else ''
    ten = gio['ten']
    quanh = f'Quanh {ten}' if gio['loai'] in ('phut', 'truoc') else ten[:1].upper() + ten[1:]
    if gio['tuong_lai']:
        return f'Chưa tới {ten} nên chưa có gì để xem.', []
    if gio['loai'] in ('phut', 'truoc'):
        lech = 180 if gio['loai'] == 'phut' else 120
        since, until = gio['luc'] / 1000 - lech, min(gio['luc'] / 1000 + lech, t / 1000)
    else:
        since, until = gio['tu'] / 1000, gio['den'] / 1000
    recs = [r for r in viec_trong_khoang(hub, since, until, ban) if r['ket'] != 'huy']
    if gio['luc'] is not None:
        recs.sort(key=lambda r: (abs(r['t'] - gio['luc']), r['t']))
    else:
        recs.sort(key=lambda r: -r['t'])
    blocks = []
    co_kho = xin is not None and xin.clips is not None
    if recs:
        vb = khoi_video(f'{quanh}{o_ban}', [xin.muc_viec(r) for r in recs[:4]]) if co_kho else None
        ids = [a['id'] for a in (viec_ram(hub, r) for r in recs[:8]) if a is not None]
        eb = khoi_su_kien(hub, ids, f'{quanh}{o_ban}')
        blocks += [b for b in (vb, eb) if b]
        ans = f'{quanh}{o_ban} có {len(recs)} sự kiện: ' + '; '.join(cau_viec(hub, r) for r in recs[:3]) + '.'
        if vb:
            ans += _cau_video(vb)
        elif muon_xem and eb:
            ans += ' Máy chủ chưa bật lưu video, nên chỉ có ảnh camera lúc đó.'
        return ans, blocks
    ans = f'{quanh}{o_ban} camera không ghi sự kiện nào.'
    if co_kho:
        if gio['luc'] is not None:
            tu = gio['luc'] if gio['loai'] == 'phut' else gio['luc'] - 15_000
            den = tu + 30_000
        elif gio['loai'] == 'gan':
            tu, den = t - 32_000, t - 2_000
        else:
            tu, den = gio['tu'], gio['tu'] + 30_000
        if den > t:
            tu, den = max(tu - (den - t) - 2_000, tu - 30_000), t - 2_000
        vb = khoi_video(f'{quanh}{o_ban}', [xin.muc((tu + den) // 2, camera_cua_ban(hub, ban), ban,
                                                    label=f'Bàn {ban}' if ban else 'Toàn cảnh camera',
                                                    note='Camera không ghi sự kiện nào quanh lúc này',
                                                    tu=tu, den=den)])
        blocks.append(vb)
        ans += ' Đang lấy hình camera lúc đó, xem ở bên dưới.' if co_video(vb) else ' ' + vb['items'][0]['error']
    return ans, blocks


def xem_su_kien(hub, q, ban=None, xin=None, ids=None, t=None):
    """Xem lại sự kiện không theo giờ: lần chờ lâu nhất, những lần khách gọi, sự kiện của một bàn, hoặc theo mã."""
    t = t or now_ms()
    co = lambda *tu: any(x in q for x in tu)   # noqa: E731
    co_kho = xin is not None and xin.clips is not None
    loai = 'call' if co('goi') else 'needs_clearing' if co('don') else 'new_guest' if co('khach moi', 'khach vao') else ''
    lau_ = co('cho lau', 'doi lau', 'cham', 'lau nhat', 'phai cho', 'phai doi')
    nhat = co('lau nhat', 'cham nhat')
    o_ban = f' ở bàn {ban}' if ban else ''
    recs, ram = [], []
    if ids:
        ram = [hub.alerts[i] for i in ids if i in hub.alerts]
        if not ram:     # mã lấy từ lịch sử (máy chủ đã khởi động lại): tìm việc hôm nay mang mã đó
            d0 = dau_ngay_s(hom_nay(t))
            recs = [r for r in viec_lich_su(hub, d0, t / 1000, ban) if r['aid'] in ids]
    elif viec(hub):
        got = loc_su_kien(hub, loai=loai, ban=ban or '', cho_hon_giay=FAST_S if lau_ and not nhat else 0,
                          sap_xep='cho_lau_nhat' if lau_ else 'moi_nhat', gioi_han=12)
        ram = [a for w, a in got if a['status'] != 'cancelled' and (not lau_ or w is not None)]
    else:       # máy chủ vừa khởi động lại hoặc vừa bắt đầu ca mới: đọc việc hôm nay từ lịch sử
        d0 = dau_ngay_s(hom_nay(t))
        recs = [r for r in viec_lich_su(hub, d0, t / 1000, ban) if r['ket'] != 'huy' and (not loai or r['kind'] == loai)]
        if lau_:
            recs = sorted((r for r in recs if r['wait_s'] is not None and (nhat or r['wait_s'] > FAST_S)),
                          key=lambda r: -r['wait_s'])
        else:
            recs.sort(key=lambda r: -r['t'])
    if ram:
        recs = [_rec(a) for a in ram]
    if lau_ and co_kho and getattr(xin.clips, 'demo', None):     # quán demo: ưu tiên lần có video thật, không ai tới xếp trước
        cv = [r for r in recs if xin.clips._tim_demo(r['camera'] or camera_cua_ban(hub, r['ban']),
                                                     r['t'] - TRUOC_MS, r['t'] + SAU_MS)]
        if cv:
            recs = sorted(cv, key=lambda r: (r['ket'] != 'bo_lo', -(r['wait_s'] or 0)))
            ram = [a for a in ram if any(a['id'] == r['aid'] for r in recs)]
    if nhat:
        recs = recs[:3]
    if not recs:
        if ban and co_kho and not lau_ and not loai:
            vb = khoi_video(f'Bàn {ban} vừa rồi', [xin.muc(t - 15_000, camera_cua_ban(hub, ban), ban,
                                                         label=f'Bàn {ban}', tu=t - 30_000, den=t - 2_000,
                                                         note='Nửa phút vừa qua')])
            return (f'Bàn {ban} hôm nay chưa có sự kiện nào.'
                    + (' Đây là hình camera ở bàn vừa rồi.' if co_video(vb) else ' ' + vb['items'][0]['error'])), [vb]
        return f'Chưa có sự kiện nào{o_ban} khớp để xem lại.', []
    ten = ('Lần khách chờ lâu nhất' if nhat else 'Những lần khách chờ lâu' if lau_ else 'Sự kiện gần đây') \
        + (f' ({KIND_VI[loai]})' if loai else '') + o_ban
    vb = khoi_video(ten, [xin.muc_viec(r) for r in recs[:MAX_VIDEO]]) if co_kho else None
    eb = khoi_su_kien(hub, [a['id'] for a in ram[:8]], ten)
    dau = recs[0]
    if lau_:
        a = viec_ram(hub, dau)
        muc_cho = chu_cho(a, wait_s(a, t)) if a is not None else (
            duoi_viec(hub, dau) if dau['ket'] == 'bo_lo' else f"phục vụ {MUC_VI[muc(dau['wait_s'])]}")
        ans = (f"{where(dau['ban'], dau['camera'])} chờ lâu nhất, lúc {clock(dau['t'])[:5]} "
               f"({KIND_VI[dau['kind']]}): {muc_cho}.")
    else:
        ans = f'Có {len(recs)} sự kiện{o_ban} để xem lại, mới nhất là {cau_viec(hub, dau).lower()}.' \
            if len(recs) > 1 else f'{cau_viec(hub, dau)}, lúc {clock(dau["t"])[:5]}.'
    if vb:
        ans += _cau_video(vb)
    else:
        ans += ' Máy chủ chưa bật lưu video, nên chỉ có ảnh camera lúc đó.'
    return ans, [b for b in (vb, eb) if b]


# ====================================================================== bàn đang ở bước nào
def ban_dang_the_nao(hub):
    """Các bàn đang có khách và bữa ăn tới đâu: [dict(ban, buoc, stage, tu_luc, luu_y, nudge, so_nguoi)], bàn cần
    để ý đứng trước."""
    by = {}
    for x in hub.tables.values():
        cu = by.get(x['id'])
        if cu is None or (x['state'] == 'occupied' and cu['state'] != 'occupied'):
            by[x['id']] = x
    out = []
    for x in by.values():
        st = x.get('stage')
        if st not in ACTIVE and x['state'] != 'occupied':
            continue
        nd = x.get('nudge')
        luc = x.get('stage_since') or x.get('since')
        out.append(dict(ban=x['id'], stage=st if st in ACTIVE else None, buoc=BUOC_VI.get(st, 'Đang có khách'),
                        tu_luc=clock(luc)[:5] if luc else None, nudge=nd, luu_y=NHAC_VI.get(nd), so_nguoi=x['people']))
    out.sort(key=lambda r: (r['nudge'] is None, str(r['ban'])))
    return out


def tra_loi_ban_luc_nay(hub, ban=None, biet=True, t=None):
    """Bàn nào đang chờ gì. Trả (câu trả lời, khối)."""
    t = t or now_ms()
    ds = ban_dang_the_nao(hub)
    mo = [a for a in viec(hub) if a['status'] not in CLOSED and not a['acked_by'] and a['status'] != 'verifying']
    blocks = []
    if ban:
        r = next((x for x in ds if x['ban'] == ban), None)
        viec_ban = [a for a in mo if a['table'] == ban]
        if r is None:
            st = next((x for x in hub.tables.values() if x['id'] == ban), None)
            if st is None:
                return ((f'Camera chưa gửi trạng thái bàn {ban}.' if biet
                         else f'Chưa thấy bàn {ban} trong các bàn camera đang theo dõi.'), [])
            ans = f"Bàn {ban} lúc này {dict(empty='đang trống', needs_clearing='cần dọn').get(st['state'], 'chưa rõ')}."
        else:
            ans = f"Bàn {ban} đang có khách: {r['buoc'][:1].lower()}{r['buoc'][1:]}"
            ans += f", từ {r['tu_luc']}." if r['tu_luc'] else '.'
            if r['luu_y']:
                ans += f" Cần để ý: {NUDGE_VI[r['nudge']]}."
        if viec_ban:
            ans += ' ' + '; '.join(cau_su_kien(hub, a, t) for a in viec_ban[:2]) + '.'
            blocks.append(khoi_su_kien(hub, [a['id'] for a in viec_ban[:4]], f'Việc đang chờ ở bàn {ban}'))
        return ans, [b for b in blocks if b]
    if not ds and not mo:
        return ('Lúc này không bàn nào có khách và không có việc nào đang chờ.' if hub.tables
                else 'Camera chưa gửi trạng thái bàn, và không có việc nào đang chờ.'), []
    c = Counter(r['stage'] for r in ds)

    def nhom(stage, ten):
        bs = [r['ban'] for r in ds if r['stage'] == stage]
        return f"{len(bs)} bàn {ten} ({', '.join(bs[:4])})" if bs else None

    phan = [p for p in (nhom('seated', 'mới ngồi, chờ nhân viên ra tiếp'), nhom('greeted', 'chờ món'),
                        nhom('served', 'đang ăn'), nhom('finished', 'đã ăn xong')) if p]
    ans = f'Đang có {len(ds)} bàn có khách' + (': ' + ', '.join(phan) + '.' if phan else '.') if ds else \
        'Camera chưa báo bàn nào có khách.'
    can = [f"bàn {r['ban']} {NUDGE_VI[r['nudge']]}" for r in ds if r['nudge']]
    cho = [a for a in mo if wait_s(a, t) is not None and wait_s(a, t) >= 45]
    if can:
        ans += ' Cần để ý: ' + '; '.join(can[:3]) + '.'
    if cho:
        ans += ' Việc chưa ai nhận: ' + '; '.join(
            f"{where_l(a['table'], a['camera'])} {KIND_VI[a['kind']]}, {cho_mo(wait_s(a, t))}" for a in cho[:3]) + '.'
    if not can and not cho:
        ans += ' Lúc này không bàn nào phải chờ lâu.'
    if ds:
        blocks.append(khoi_bang('Các bàn đang có khách', ['Bàn', 'Bữa ăn tới đâu', 'Từ lúc', 'Cần để ý'],
                                [[f"Bàn {r['ban']}", r['buoc'], r['tu_luc'] or '', r['luu_y'] or ''] for r in ds]))
    blocks.append(khoi_su_kien(hub, [a['id'] for a in (cho or mo)[:6]], 'Việc chưa ai nhận'))
    return ans, [b for b in blocks if b]


# ====================================================================== ngày khác
def tong_ket_ngay(hub, day, t=None):
    """Số liệu một ngày đọc từ dòng thời gian: số việc từng loại, bao nhiêu việc nhanh, chậm, bỏ lỡ, giờ bận nhất."""
    t = t or now_ms()
    d0 = dau_ngay_s(day)
    recs = viec_trong_khoang(hub, d0, min(d0 + 86400 - 0.001, t / 1000))
    tinh =[r for r in recs if r['ket'] != 'huy']
    sp = dict(fast=0, ok=0, slow=0, missed=0)
    for r in tinh:
        if r['ket'] == 'bo_lo':
            sp['missed'] += 1
        elif r['wait_s'] is not None:
            sp[muc(r['wait_s'])] += 1
    gio = Counter(datetime.fromtimestamp(r['t'] / 1000, VN).hour for r in tinh)
    c = Counter(r['kind'] for r in tinh)
    dinh = max(gio.items(), key=lambda kv: (kv[1], -kv[0]))[0] if gio else None
    return dict(day=day, ten=ten_ngay(day, t), n=len(tinh), call=c['call'], needs_clearing=c['needs_clearing'],
                new_guest=c['new_guest'], speed=sp, huy=len(recs) - len(tinh), gio=gio, dinh=dinh, recs=tinh)


def _hoa(s):
    return s[:1].upper() + s[1:]


def cau_ngay(tk):
    ten = _hoa(tk['ten'])
    if not tk['n']:
        return f'{ten} hệ thống không ghi được việc nào: có thể quán nghỉ, hoặc camera chưa chạy hôm đó.'
    s = (f"{ten} có {tk['call']} lần khách gọi, {tk['needs_clearing']} lần bàn cần dọn và {tk['new_guest']} lượt "
         f'khách mới.')
    nx = nhan_xet(tk['speed'])
    if nx:
        s += f" Phục vụ nhìn chung {MUC_VI[nx]}: {cau_dem(tk['speed'], 'việc')}."
    if tk['dinh'] is not None:
        s += f" Bận nhất khoảng {tk['dinh']:02d}:00."
    return s


def khoi_ngay(tk):
    """Hai khối cho một ngày: ô chỉ số và cột số việc theo giờ. [] nếu ngày đó không có dữ liệu."""
    if not tk['n']:
        return []
    nx = nhan_xet(tk['speed'])
    items = [dict(label='Khách gọi phục vụ', value=str(tk['call']), note=None, tone=None),
             dict(label='Bàn cần dọn', value=str(tk['needs_clearing']), note=None, tone=None),
             dict(label='Khách mới', value=str(tk['new_guest']), note=None, tone=None),
             dict(label='Tốc độ phục vụ', value=MUC_VI[nx].capitalize() if nx else 'Chưa có',
                  note=cau_dem(tk['speed'], 'việc') or None, tone=MUC_TONE.get(nx)),
             dict(label='Giờ bận nhất', value=f"{tk['dinh']:02d}:00", note=f"{tk['gio'][tk['dinh']]} việc", tone=None),
             dict(label='Báo nhầm đã lọc', value=str(tk['huy']), note=None, tone=None)]
    h0, h1 = min(tk['gio']), max(tk['gio'])
    pts = [dict(label=f'{h:02d}:00', value=tk['gio'].get(h, 0), note=None) for h in range(h0, h1 + 1)]
    return [dict(type='stats', title=f"Số liệu {tk['ten']}", items=items),
            dict(type='chart', title=f"Số việc theo giờ, {tk['ten']}", kind='column', unit='việc', points=pts)]


def so_sanh_ngay(hub, day1, day2=None, t=None):
    """So hai ngày (day2 trống thì so với hôm nay). Trả (câu trả lời, khối, [tong_ket])."""
    t = t or now_ms()
    day2 = day2 or hom_nay(t)
    if day1 == day2:
        tk = tong_ket_ngay(hub, day1, t)
        return cau_ngay(tk), khoi_ngay(tk), [tk]
    a, b = tong_ket_ngay(hub, day1, t), tong_ket_ngay(hub, day2, t)
    if not a['n'] and not b['n']:
        return f"Cả {a['ten']} lẫn {b['ten']} hệ thống đều không ghi được việc nào, nên chưa so được.", [], [a, b]
    if not a['n'] or not b['n']:
        trong, co = (a, b) if not a['n'] else (b, a)
        return (f"{_hoa(trong['ten'])} hệ thống không ghi được việc nào nên chưa so được. " + cau_ngay(co),
                khoi_ngay(co), [a, b])

    def toc(tk):
        nx = nhan_xet(tk['speed'])
        return MUC_VI[nx] if nx else 'chưa có'

    def te(tk):
        return str(tk['speed']['slow'] + tk['speed']['missed'])

    ans = (f"{_hoa(a['ten'])} có {a['n']} việc, {b['ten']} " + ('tới giờ ' if day2 == hom_nay(t) else '')
           + f"có {b['n']} việc. Phục vụ {a['ten']} {toc(a)}, {b['ten']} {toc(b)}.")
    rows = [['Khách gọi phục vụ', str(a['call']), str(b['call'])],
            ['Bàn cần dọn', str(a['needs_clearing']), str(b['needs_clearing'])],
            ['Khách mới', str(a['new_guest']), str(b['new_guest'])],
            ['Tốc độ phục vụ', toc(a), toc(b)],
            ['Việc được nhận nhanh', str(a['speed']['fast']), str(b['speed']['fast'])],
            ['Việc chậm hoặc không ai tới', te(a), te(b)],
            ['Giờ bận nhất', f"{a['dinh']:02d}:00", f"{b['dinh']:02d}:00"]]
    return ans, [khoi_bang(f"So sánh {a['ten']} với {b['ten']}", ['Chỉ số', _hoa(a['ten']), _hoa(b['ten'])], rows)], [a, b]


def tra_loi_cac_ngay(hub, t=None):
    """Bảng các ngày gần đây có dữ liệu (tối đa 7 ngày)."""
    days = hub.timeline.days()[-7:]
    tks = [tk for tk in (tong_ket_ngay(hub, d, t) for d in days) if tk['n']]
    if not tks:
        return 'Hệ thống chưa ghi được ngày nào có việc.', []
    ban = max(tks, key=lambda x: x['n'])
    rows = [[_hoa(x['ten']), str(x['call']), str(x['needs_clearing']), str(x['new_guest']),
             MUC_VI.get(nhan_xet(x['speed']), 'chưa có')] for x in tks]
    return (f"Có số liệu của {len(tks)} ngày gần đây. Đông việc nhất là {ban['ten']} với {ban['n']} việc.",
            [khoi_bang('Các ngày gần đây', ['Ngày', 'Khách gọi', 'Cần dọn', 'Khách mới', 'Phục vụ'], rows)])


def hom_nay_tu_lich_su(hub, t=None):
    """Ca hiện tại chưa có việc nào trong RAM (máy chủ vừa khởi động lại, hoặc vừa bắt đầu ca mới) nhưng hôm nay
    đã có việc được ghi: trả (câu trả lời, khối) từ lịch sử. None nếu hôm nay chưa ghi gì."""
    tk = tong_ket_ngay(hub, hom_nay(t), t)
    if not tk['n']:
        return None
    return ('Ca hiện tại chưa có việc nào. Trước đó trong ngày hệ thống đã ghi lại: ' + cau_ngay(tk)[:1].lower()
            + cau_ngay(tk)[1:]), khoi_ngay(tk)


# ====================================================================== đường không AI
def tra_loi(hub, q, clips=None, loop=None, t=None):
    """Các câu hỏi xem lại, cho đường không AI. `q` là câu hỏi đã bỏ dấu. Trả (câu trả lời, khối) hoặc None nếu
    câu hỏi không thuộc phần này (để các luật cũ trong tro_ly.tra_loi_rules trả lời)."""
    t = t or now_ms()
    co = lambda *tu: any(x in q for x in tu)   # noqa: E731
    ngay = doc_cac_ngay(q, t)
    gio = doc_gio(q, t)
    nay = hom_nay(t)
    khac_ngay = any(d != nay for d in ngay) or bool(gio and gio['day'] != nay)
    muon_xem = co(*TU_XEM) or bool(re.search(r'(?<![a-z])(xem|coi)(?![a-z])', q) and (gio or re.search(r'\bban\s*[a-z]{0,2}\d', q)))
    muon_ke = co(*TU_KE)
    ban, biet = tim_ban(hub, q)
    xin = Xin(hub, clips, loop)

    def ban_la():
        return f'Chưa thấy bàn {ban} trong các bàn camera đang theo dõi.', []

    # kể lại chuyện của một bàn hoặc một quãng giờ
    if muon_ke and (ban or gio):
        if ban and not biet:
            return ban_la()
        ans, blocks, _ = ke_lai(hub, ban, gio, ngay[0] if ngay else None, xin, t)
        return ans, blocks
    # xem lại một thời điểm: khi có kho clip, khi hỏi ngày khác, hoặc khi việc không còn trong RAM
    if gio and (muon_xem or clips is not None or khac_ngay or not viec(hub)) and not co('so sanh', 'so voi'):
        if ban and not biet:
            return ban_la()
        if gio['loai'] == 'khoang' and not muon_xem and not ban and khac_ngay:
            pass        # "trưa hôm qua thế nào": hỏi số liệu, để phần ngày khác trả lời
        else:
            return xem_thoi_diem(hub, gio, ban, xin, muon_xem, t)
    if muon_xem and (clips is not None or not viec(hub)) and not khac_ngay:
        if ban and not biet:
            return ban_la()
        return xem_su_kien(hub, q, ban, xin, t=t)
    # bàn nào đang chờ gì
    if co(*TU_BUOC) and not co('viec') and not khac_ngay:
        return tra_loi_ban_luc_nay(hub, ban, biet, t)
    # ngày khác, so sánh ngày
    if co('tuan nay', 'tuan qua', 'tuan truoc', '7 ngay', 'may ngay', 'cac ngay', 'nhung ngay') and not ngay:
        return tra_loi_cac_ngay(hub, t)
    if khac_ngay or (ngay and co('so sanh', 'so voi')):
        if len(ngay) >= 2 or co('so sanh', 'so voi', 'hon hom', 'kem hom'):
            khac = [d for d in ngay if d != nay]
            d1 = ngay[0] if len(ngay) >= 2 else (khac[0] if khac else nay)
            d2 = ngay[1] if len(ngay) >= 2 else nay
            ans, blocks, _ = so_sanh_ngay(hub, d1, d2, t)
            return ans, blocks
        tk = tong_ket_ngay(hub, next(d for d in ([gio['day']] if gio else []) + ngay if d != nay), t)
        if ban:
            tk_ban = [r for r in tk['recs'] if r['ban'] == ban]
            if not tk_ban:
                return f"{_hoa(tk['ten'])} bàn {ban} không có việc nào được ghi lại.", []
            c = Counter(r['kind'] for r in tk_ban)
            return (f"{_hoa(tk['ten'])} bàn {ban}: gọi phục vụ {c['call']} lần, cần dọn {c['needs_clearing']} lần, "
                    f"khách mới {c['new_guest']} lượt."), []
        return cau_ngay(tk), khoi_ngay(tk)
    return None
