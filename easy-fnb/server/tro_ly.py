"""Trợ lý của chủ quán: trả lời câu hỏi về ca bằng nhiều dạng (chữ, chỉ số, biểu đồ, sự kiện có ảnh, bảng, thẻ nhân viên).

Hai đường:
  adk    Tác tử Google ADK chạy Gemini. Tác tử gọi công cụ để đọc số liệu ca, rồi gọi công cụ hiển thị để
         chọn dạng trả lời. Số trong mọi khối do máy chủ điền từ `hub`, model không tự chép số.
  rules  Không dùng AI: chọn khối theo từ khoá trong câu hỏi. Dùng khi thiếu GEMINI_API_KEY, đang chạy
         kie.ai, chưa cài google-adk, hoặc ADK lỗi / quá giờ giữa chừng.

Hợp đồng trả về: xem mục "AI" trong server/API.md.

Thử nhanh đường ADK khi đã đặt GEMINI_API_KEY (từ thư mục easy-fnb):
    python -m server.tro_ly "hôm nay nhân viên làm việc thế nào"
"""
import asyncio
import logging
import os
import re
import time
import unicodedata
from collections import Counter

from .hub import CLOSED, KIND_VI, TASK_KINDS, Hub, clock, now_ms, where
from .an_ninh_tro_ly import an_ninh, cau_an_ninh, tra_loi_an_ninh
from . import an_ninh_tro_ly

log = logging.getLogger('easyfnb.tro_ly')

ADK_TIMEOUT_S = 30.0
ROLE_VI = {'serve': 'phục vụ', 'clean': 'dọn bàn', 'cashier': 'thu ngân'}
STATUS_VI = {'verifying': 'đang kiểm tra', 'open': 'chưa ai nhận', 'acked': 'đang xử lý', 'done': 'đã xong',
             'cancelled': 'đã huỷ'}
TABLE_VI = {'empty': 'trống', 'occupied': 'có khách', 'needs_clearing': 'cần dọn', 'unknown': 'chưa rõ'}
GOI_Y = ['Cho xem lại lần khách chờ lâu nhất', 'Bàn nào đang chờ lâu?', 'Nên đổi gì cho ca sau?',
         'Ca sau nên xếp người thế nào?', 'Hôm nay chất lượng nhân viên thế nào?', 'Hôm qua so với hôm nay thế nào?',
         'Giờ nào bận nhất?', 'Tóm tắt ca hôm nay']
BUCKETS_S = (30, 60, 120, 300, 600, 900, 1800, 3600, 7200)


# ====================================================================== tiện ích
def bo_dau(s):
    """Chữ thường, bỏ dấu tiếng Việt, để so từ khoá."""
    s = unicodedata.normalize('NFD', (s or '').lower().replace('đ', 'd'))
    return ''.join(ch for ch in s if unicodedata.category(ch) != 'Mn')


# Trợ lý không nói số giây: chủ quán chỉ cần biết nhanh hay chậm. Mốc lấy từ hub, khớp với các màn hình.
FAST_S, SLOW_S = Hub.FAST_S, Hub.SLOW_S
MUC_VI = {'fast': 'nhanh', 'ok': 'hơi chậm', 'slow': 'chậm'}
MUC_TONE = {'fast': 'good', 'ok': 'warn', 'slow': 'bad'}
MUC_PHUC_VU = {'fast': 'phục vụ nhanh', 'ok': 'phục vụ hơi chậm', 'slow': 'phục vụ chậm'}


def muc(s):
    """Một khoảng chờ (giây) là nhanh, hơi chậm hay chậm."""
    if s is None:
        return None
    return 'fast' if s <= FAST_S else 'ok' if s <= SLOW_S else 'slow'


def tone_cho(s):
    return MUC_TONE.get(muc(s))


def dem_muc(ws):
    c = Counter(muc(w) for w in ws)
    return dict(fast=c['fast'], ok=c['ok'], slow=c['slow'])


def nhan_xet(c):
    """Nhận xét chung cho một nhóm việc, cùng cách tính với màn hình (verdictOf trong src/live/text.ts)."""
    tong = c['fast'] + c['ok'] + c['slow'] + c.get('missed', 0)
    if not tong:
        return None
    nhanh, te = c['fast'] / tong, (c['slow'] + c.get('missed', 0)) / tong
    if nhanh >= 0.7 and te <= 0.1:
        return 'fast'
    return 'slow' if te >= 0.3 or nhanh < 0.4 else 'ok'


def cau_dem(c, don_vi='lần'):
    """Số đếm theo mức, ví dụ "3 lần nhanh, 1 lần hơi chậm"."""
    phan = [f'{c[k]} {don_vi} {MUC_VI[k]}' for k in ('fast', 'ok', 'slow') if c.get(k)]
    if c.get('missed'):
        phan.append(f"{c['missed']} {don_vi} không ai tới")
    return ', '.join(phan)


def cho_mo(s):
    """Việc còn mở đã chờ bao lâu, nói bằng chữ (khớp waitWord ở màn hình)."""
    return 'vừa báo' if s < 20 else 'đang chờ' if s < 45 else 'chờ hơi lâu' if s < 90 else 'chờ quá lâu'


def chu_cho(a, w):
    """Lần chờ của một việc nói bằng chữ: việc chưa ai nhận thì nói đang chờ ra sao, còn lại nói phục vụ nhanh hay chậm."""
    if a['status'] not in CLOSED and not a['acked_at'] and a.get('arrived_s') is None:
        return cho_mo(w)
    return MUC_PHUC_VU[muc(w)]


def lau(x):
    """Khoảng thời gian không phải tốc độ phục vụ (giờ làm, bàn có khách bao lâu): tính tròn phút."""
    if x is None:
        return 'chưa có'
    x = int(round(x))
    if x < 60:
        return 'chưa tới 1 phút'
    return f'{x // 3600} giờ {x % 3600 // 60:02d} phút' if x >= 3600 else f'{x // 60} phút'


def viec(hub):
    """Việc phục vụ của ca (không gồm cảnh báo an ninh: chúng không vào số liệu ca)."""
    return [a for a in hub.alerts.values() if a['kind'] in TASK_KINDS]


def wait_s(a, t=None):
    """Khách phải chờ bao lâu: ưu tiên lúc camera thấy nhân viên tới bàn, rồi lúc nhân viên bấm nhận;
    việc còn mở thì tính tới hiện tại; việc đã huỷ thì không tính."""
    if a.get('arrived_s') is not None:
        return float(a['arrived_s'])
    if a['acked_at']:
        return round((a['acked_at'] - a['created_at']) / 1000, 1)
    if a['status'] == 'cancelled':
        return None
    if a['done_at']:
        return round((a['done_at'] - a['created_at']) / 1000, 1)
    return round(((t or now_ms()) - a['created_at']) / 1000, 1)


def ten_nv(hub, sid):
    if not sid or sid in ('camera', 'gemini', 'manager'):
        return None
    return hub._staff_name(sid)


def cau_su_kien(hub, a, t=None):
    """Một câu tiếng Việt cho một việc, ví dụ "Bàn B2 gọi phục vụ, Lan nhận nhanh"."""
    if a.get('group') == 'security':
        return cau_an_ninh(hub, a)
    s = f"{where(a['table'], a['camera'])} {KIND_VI[a['kind']]}"
    w = wait_s(a, t)
    nv = ten_nv(hub, a['acked_by'] or a['assigned_to'])
    if a['status'] == 'cancelled':
        return f"{s}, đã huỷ: {a['cancel_reason'] or 'báo nhầm'}"
    if a.get('arrived_s') is not None:
        return f"{s}, nhân viên tới {MUC_VI[muc(w)]} (camera đo)"
    if a['acked_at']:
        return f"{s}, {nv or 'nhân viên'} nhận {MUC_VI[muc(w)]}"
    if a['status'] == 'done':
        return f"{s}, xong {MUC_VI[muc(w)]}"
    if a['status'] == 'verifying':
        return f"{s}, đang kiểm tra ảnh"
    return f"{s}, chưa ai nhận, {cho_mo(w)}" + (f' (giao cho {nv})' if nv else '')


# ====================================================================== dựng khối (thuần Python, không LLM)
def khoi_chi_so(hub, title='Chỉ số ca'):
    r = hub.report()
    t = now_ms()
    al = viec(hub)
    cho = [(wait_s(a, t), a) for a in al if a['status'] != 'cancelled' and wait_s(a, t) is not None]
    mo = [a for a in al if a['status'] not in CLOSED]
    nx = nhan_xet(r['speed'])
    items = [
        dict(label='Khách gọi phục vụ', value=str(r['counts']['call']), note=None, tone=None),
        dict(label='Bàn cần dọn', value=str(r['counts']['needs_clearing']), note=None, tone=None),
        dict(label='Khách mới', value=str(r['counts']['new_guest']), note=None, tone=None),
        dict(label='Tốc độ phục vụ', value=MUC_VI[nx].capitalize() if nx else 'Chưa có',
             note=cau_dem(r['speed'], 'việc') or None, tone=MUC_TONE.get(nx)),
    ]
    if cho:
        w, a = max(cho, key=lambda x: x[0])
        items.append(dict(label='Chờ lâu nhất', value=where(a['table'], a['camera']),
                          note=f"{KIND_VI[a['kind']]} lúc {clock(a['created_at'])[:5]}, {chu_cho(a, w)}",
                          tone=tone_cho(w)))
    items.append(dict(label='Báo nhầm đã lọc', value=str(r['cancelled']),
                      note=f"{hub.ten} bác {r['rejected_by_gemini']}" if r['rejected_by_gemini'] else None, tone=None))
    items.append(dict(label='Việc đang chờ', value=str(len(mo)), note=None, tone='warn' if mo else 'good'))
    return dict(type='stats', title=title, items=items)


def khoi_bieu_do_nhan_vien(hub):
    """Trong các việc mỗi người nhận, bao nhiêu phần trăm là nhận nhanh (thanh ngang). None nếu chưa ai nhận việc nào."""
    pts = [dict(label=s['name'], value=round(100 * s['fast'] / (s['fast'] + s['ok'] + s['slow'])),
                note=cau_dem(s, 'việc'))
           for s in hub.report()['per_staff'] if s['fast'] + s['ok'] + s['slow']]
    if not pts:
        return None
    return dict(type='chart', title='Phần việc nhận nhanh của từng nhân viên', kind='bar', unit='%', points=pts)


def khoi_bieu_do_ban(hub):
    pts = [dict(label=f"Bàn {t['table']}", value=t['calls'] + t['clearings'],
                note=f"gọi {t['calls']}, cần dọn {t['clearings']}, khách mới {t['guests']}")
           for t in hub.report()['per_table']]
    pts = sorted((p for p in pts if p['value']), key=lambda p: -p['value'])[:12]
    if not pts:
        return None
    return dict(type='chart', title='Số lần gọi và cần dọn theo bàn', kind='bar', unit='lần', points=pts)


def khoi_bieu_do_cho_theo_ban(hub):
    """Mỗi bàn có bao nhiêu lần khách phải chờ lâu, tức là không được phục vụ nhanh (thanh ngang)."""
    t = now_ms()
    dem = {}
    for a in viec(hub):
        w = wait_s(a, t)
        if a['table'] and w is not None and a['status'] != 'cancelled' and muc(w) != 'fast':
            dem.setdefault(a['table'], Counter())[muc(w)] += 1
    pts = [dict(label=f'Bàn {tb}', value=c['ok'] + c['slow'], note=cau_dem(c))
           for tb, c in sorted(dem.items(), key=lambda kv: -(kv[1]['ok'] + kv[1]['slow']))[:12]]
    if not pts:
        return None
    return dict(type='chart', title='Số lần khách phải chờ lâu theo bàn', kind='bar', unit='lần', points=pts)


def _khoang(hub):
    """(bắt đầu, độ dài một khoảng, [số sự kiện mỗi khoảng theo loại]) sao cho ra khoảng 6 đến 12 cột."""
    al = [a for a in viec(hub) if a['status'] != 'cancelled']
    if not al:
        return None
    t0, t1 = min(a['created_at'] for a in al) // 1000, max(a['created_at'] for a in al) // 1000
    size = next((b for b in BUCKETS_S if (t1 - t0) / b < 12), BUCKETS_S[-1])
    t0 -= t0 % size                                   # mốc tròn: 12:00, 12:05, ...
    n = max(6, (t1 - t0) // size + 1)                 # ca vừa bắt đầu vẫn có đủ 6 cột để đọc được
    cot = [Counter() for _ in range(n)]
    for a in al:
        cot[(a['created_at'] // 1000 - t0) // size][a['kind']] += 1
    return t0, size, cot


def khoi_bieu_do_thoi_gian(hub, kind='column'):
    k = _khoang(hub)
    if k is None:
        return None
    t0, size, cot = k
    pts = []
    for i, c in enumerate(cot):
        label = clock((t0 + i * size) * 1000)
        pts.append(dict(label=label if size < 60 else label[:5], value=sum(c.values()),
                        note=', '.join(f'{KIND_VI[kd]} {c[kd]}' for kd in TASK_KINDS if c[kd]) or None))
    ten = 'nửa phút' if size < 60 else f'{size // 60} phút' if size < 3600 else f'{size // 3600} giờ'
    return dict(type='chart', title=f'Số sự kiện theo thời gian (mỗi cột {ten})', kind=kind, unit='sự kiện',
                points=pts)


def khoi_su_kien(hub, ids, title='Sự kiện'):
    """Danh sách sự kiện có ảnh từ mã việc (a1, a2, ...). Mã không có thì bỏ qua."""
    t = now_ms()
    items, seen = [], set()
    for aid in ids:
        aid = str(aid).strip().strip('[]')
        a = hub.alerts.get(aid)
        if a is None or aid in seen:
            continue
        seen.add(aid)
        strip = (a.get('evidence') or {}).get('strip')
        items.append(dict(alert_id=aid, kind=a['kind'], table=a['table'], t=a['created_at'], status=a['status'],
                          wait_s=wait_s(a, t), staff=ten_nv(hub, a['acked_by'] or a['assigned_to']),
                          text=cau_su_kien(hub, a, t), crop_url=a['crop_url'], strip_url=strip or None,
                          video_t=a['video_t'],
                          clip_url=f'/api/alerts/{aid}/clip.mp4' if a.get('clip') else None))
    if not items:
        return None
    return dict(type='events', title=title, items=items)


def khoi_nhan_vien(hub, ids=None, title='Nhân viên'):
    """Thẻ nhân viên kèm chấm công. ids rỗng thì lấy mọi người."""
    t = now_ms()
    per = {s['id']: s for s in hub.report()['per_staff']}
    want = {bo_dau(x) for x in ids or []}
    items = []
    for s in hub.staff_view():
        if want and bo_dau(s['id']) not in want and bo_dau(s['name']) not in want:
            continue
        p = per.get(s['id'], {})
        mo = (t - s['on_since']) // 1000 if s.get('on_since') else 0     # lượt đang mở tính tới hiện tại
        items.append(dict(id=s['id'], name=s['name'], role=s['role'], online=bool(s['online']),
                          acked=p.get('acked', 0), done=p.get('done', 0),
                          mean_response_s=p.get('mean_response_s'), worked_s=int(s.get('worked_s') or 0) + int(mo),
                          first_in=s.get('first_in')))
    if not items:
        return None
    return dict(type='staff', title=title, items=items)


def khoi_bang(title, columns, rows):
    """Bảng tự do. rows: list[list[str]] hoặc list[str] với các ô nối bằng " | "."""
    cols = [str(c) for c in columns][:8]
    out = []
    for r in rows[:40]:
        cells = [c.strip() for c in r.split('|')] if isinstance(r, str) else [str(c) for c in r]
        if cols:
            cells = (cells + [''] * len(cols))[:len(cols)]
        out.append(cells)
    if not cols or not out:
        return None
    return dict(type='table', title=title or 'Bảng', columns=cols, rows=out)


def khoi_bang_ban(hub):
    t = now_ms()
    rows = [[f"Bàn {x['id']}", TABLE_VI.get(x['state'], x['state']), str(x['people']),
             lau((t - x['since']) / 1000) if x.get('since') else '']
            for x in sorted(hub.tables.values(), key=lambda x: str(x['id']))]
    return khoi_bang('Các bàn lúc này', ['Bàn', 'Trạng thái', 'Số người', 'Đã được'], rows)


# ====================================================================== đọc dữ liệu (dùng chung cho ADK và rules)
LS_GHI_CHU = ('Ca trong bộ nhớ chưa có việc nào (máy chủ vừa khởi động lại); đây là số liệu của cả ngày hôm nay '
              'đọc từ lịch sử đã lưu. Trả lời như số liệu hôm nay bình thường, không nói là chưa có gì.')
LOAI_K = {'goi': 'call', 'goi_phuc_vu': 'call', 'call': 'call', 'can_don': 'needs_clearing', 'don': 'needs_clearing',
          'needs_clearing': 'needs_clearing', 'khach_moi': 'new_guest', 'new_guest': 'new_guest'}


def hom_nay_lich_su(hub):
    """Ca trong RAM trống (máy chủ vừa khởi động, ví dụ Cloud Run) mà hôm nay đã có việc trong lịch sử: số liệu ca
    lấy từ lịch sử, cùng dạng với so_lieu_ca. None nếu RAM đã có việc hoặc hôm nay chưa ghi gì."""
    if viec(hub):
        return None
    day = xem_lai.hom_nay()
    tk = xem_lai.tong_ket_ngay(hub, day)
    if not tk['n']:
        return None
    sp = tk['speed']
    theo_ban = {}
    cot = {'call': 'goi', 'needs_clearing': 'can_don', 'new_guest': 'khach_moi'}
    for r in tk['recs']:
        if r['kind'] in cot:      # cảnh báo an ninh (ngoài giờ, lấy đồ...) không tính vào số liệu từng bàn
            b = theo_ban.setdefault(r['ban'] or '?', dict(ban=r['ban'], goi=0, can_don=0, khach_moi=0))
            b[cot[r['kind']]] += 1
    chu_y = [dict(ma=r['aid'], ban=r['ban'], gio=clock(r['t'])[:5], nhan_vien=ten_nv(hub, r['nv']),
                  chuyen=f"Khách gọi, {ten_nv(hub, r['nv'])} bấm nhận trên điện thoại sau {r['wait_s']:.0f} giây "
                         'nhưng không tới bàn; khách chờ rồi thôi gọi', co_video=True) for r in nghe_khong_toi(tk['recs'])]
    try:
        nv = nhieu_ngay.nhan_vien_ngay(hub, day)[2]
    except Exception:  # noqa: BLE001  thiếu số liệu nhân viên thì vẫn trả phần còn lại
        nv = []
    return dict(ghi_chu=LS_GHI_CHU, so_lan=dict(goi_phuc_vu=tk['call'], can_don=tk['needs_clearing'],
                                               khach_moi=tk['new_guest']),
                toc_do_phuc_vu=dict(nhan_xet=MUC_VI.get(nhan_xet(sp)), viec_nhanh=sp['fast'], viec_hoi_cham=sp['ok'],
                                    viec_cham=sp['slow'], viec_khong_ai_toi=sp['missed']),
                bao_nham_da_huy=tk['huy'], gio_ban_nhat=f"{tk['dinh']:02d}:00" if tk['dinh'] is not None else None,
                viec_dang_cho=0, theo_nhan_vien=nv, theo_ban=list(theo_ban.values()),
                can_chu_y=chu_y, nhac=('Có chuyện cần chủ quán biết: kể ngắn từng chuyện trong can_chu_y (giờ, bàn, ai) '
                                       'và nói video đã hiện bên dưới.') if chu_y else None)


def nghe_khong_toi(recs):
    """Các việc nhân viên đã bấm nhận mà không tới bàn (camera đóng vì khách thôi gọi)."""
    return [r for r in recs if r['ket'] == 'bo_lo' and r['wait_s'] is not None and r['nv']
            and r['kind'] in ('call', 'new_guest')]


def khoi_hom_nay_lich_su(hub):
    """Ca trong RAM trống mà hôm nay đã có việc trong lịch sử: [ô chỉ số, cột số việc theo giờ]. [] nếu không."""
    if viec(hub):
        return []
    return xem_lai.khoi_ngay(xem_lai.tong_ket_ngay(hub, xem_lai.hom_nay()))


def su_kien_lich_su(hub, loai='', ban='', nhan_vien='', tu_gio='', den_gio='', cho_hon_giay=0, sap_xep='moi_nhat',
                    gioi_han=10):
    """Như tim_su_kien nhưng đọc việc hôm nay từ lịch sử (khi ca trong RAM trống)."""
    k = LOAI_K.get(bo_dau(loai).replace(' ', '_'))
    ban_k = _khoa_ban(ban)
    nv = bo_dau(nhan_vien)
    out = []
    for r in xem_lai.tong_ket_ngay(hub, xem_lai.hom_nay())['recs']:
        if (k and r['kind'] != k) or (ban_k and not _cung_ban(ban_k, r['ban'])):
            continue
        if nv and nv not in (bo_dau(r['nv'] or ''), bo_dau(ten_nv(hub, r['nv']) or '')):
            continue
        gio = clock(r['t'])[:5]
        if (tu_gio and gio < tu_gio[:5]) or (den_gio and gio > den_gio[:5]):
            continue
        if cho_hon_giay and (r['wait_s'] is None or r['wait_s'] <= cho_hon_giay):
            continue
        out.append(r)
    if sap_xep == 'cho_lau_nhat':
        out.sort(key=lambda r: -(r['wait_s'] or 0))
    else:
        out.sort(key=lambda r: -r['t'])
    out = out[:max(1, min(30, int(gioi_han or 10)))]
    kq = {'xong': 'đã xong', 'nhan': 'đã nhận', 'mo': 'đang chờ', 'bo_lo': 'không ai tới', 'huy': 'đã huỷ'}
    kq_nhan = 'đã bấm nhận nhưng không tới bàn'
    return dict(ghi_chu=LS_GHI_CHU, tong=len(out), su_kien=[dict(
        ma=r['aid'], loai=KIND_VI[r['kind']], ban=r['ban'], gio=clock(r['t']),
        toc_do=MUC_VI.get(muc(r['wait_s'])) if r['wait_s'] is not None else None,
        nhan_vien=ten_nv(hub, r['nv']) if r['nv'] else None,
        trang_thai=kq_nhan if r in nghe_khong_toi([r]) else kq.get(r['ket']), ly_do_huy=r.get('ly_do'),
        co_video=True) for r in out])


def loc_su_kien(hub, loai='', ban='', nhan_vien='', tu_gio='', den_gio='', cho_hon_giay=0, sap_xep='moi_nhat',
                gioi_han=10):
    t = now_ms()
    loai = {'goi': 'call', 'goi_phuc_vu': 'call', 'call': 'call', 'can_don': 'needs_clearing', 'don': 'needs_clearing',
            'needs_clearing': 'needs_clearing', 'khach_moi': 'new_guest', 'new_guest': 'new_guest'}.get(
                bo_dau(loai).replace(' ', '_'))
    ban_k = _khoa_ban(ban)
    nv = bo_dau(nhan_vien)
    out = []
    for a in viec(hub):
        if loai and a['kind'] != loai:
            continue
        if ban_k and not _cung_ban(ban_k, a['table']):
            continue
        if nv:
            sid = a['acked_by'] or a['assigned_to']
            if nv not in (bo_dau(sid), bo_dau(ten_nv(hub, sid))):
                continue
        gio = clock(a['created_at'])[:5]
        if (tu_gio and gio < tu_gio[:5]) or (den_gio and gio > den_gio[:5]):
            continue
        w = wait_s(a, t)
        if cho_hon_giay and (w is None or w <= cho_hon_giay):
            continue
        out.append((w, a))
    if sap_xep == 'cho_lau_nhat':
        out.sort(key=lambda x: -(x[0] if x[0] is not None else -1))
    else:
        out.sort(key=lambda x: -x[1]['created_at'])
    return out[:max(1, min(int(gioi_han or 10), 30))]


def _khoa_ban(s):
    """'Bàn B5', 'b5', '5' -> khoá so sánh. Chỉ có số thì so theo số ('5' khớp 'B5')."""
    s = re.sub(r'^ban\s*', '', bo_dau(str(s or '')).strip())
    s = re.sub(r'[^a-z0-9]', '', s)
    return s


def _cung_ban(k, table):
    """Khoá bàn người hỏi gõ có chỉ đúng bàn này không. Chỉ gõ số thì so theo số ('5' khớp 'B5'); bàn tên chỉ có
    số thì gõ kèm chữ vẫn khớp ('B09' khớp '09', vì mô hình hay tự thêm chữ B)."""
    kb = _khoa_ban(table)
    return bool(kb) and (kb == k or (k.isdigit() and re.sub(r'\D', '', kb) == k)
                         or (kb.isdigit() and re.sub(r'\D', '', k) == kb))


def _khop_ban(hub, cau):
    """Tìm bàn được nhắc trong câu hỏi (đã bỏ dấu). Trả mã bàn thật trong hub hoặc None."""
    m = re.search(r'\bban\s*(?:so\s*)?([a-z]{0,2}\d{1,3})\b', cau)
    if not m:
        return None
    k = m.group(1)
    co = {a['table'] for a in viec(hub) if a['table']} | {x['id'] for x in hub.tables.values()}
    for tb in sorted(co, key=str):
        if _cung_ban(k, tb):
            return tb
    return k.upper()


def tom_tat(hub):
    r = hub.report()
    c = r['counts']
    if not sum(c.values()):
        return 'Ca chưa có sự kiện nào: camera chưa báo khách gọi, bàn cần dọn hay khách mới.'
    s = (f"Từ {clock(r['from'])[:5]} tới giờ có {c['call']} lần khách gọi, {c['needs_clearing']} lần bàn cần dọn "
         f"và {c['new_guest']} lượt khách mới.")
    nx = nhan_xet(r['speed'])
    if nx:
        s += f" Phục vụ nhìn chung {MUC_VI[nx]}: {cau_dem(r['speed'], 'việc')}."
    if r['cancelled']:
        s += f" {r['cancelled']} báo động bị huỷ vì báo nhầm."
    ban = max(r['per_table'], key=lambda x: x['calls'] + x['clearings'], default=None)
    if ban and ban['calls'] + ban['clearings']:
        s += f" Bàn bận nhất là bàn {ban['table']}."
    return s


# ====================================================================== đường không AI
def tra_loi_rules(hub, question, clips=None, loop=None, phong=None):
    """(answer, blocks) chọn theo từ khoá. Dùng chính các hàm dựng khối ở trên.
    `clips` là kho clip (server/clips.py) để câu trả lời kèm được video; không có thì chỉ kèm ảnh."""
    q = bo_dau(question)
    # vài từ tiếng Anh hay gặp: thêm từ tiếng Việt tương ứng để các nhánh dưới bắt được
    for en, vi in (('staff', 'nhan vien'), ('employee', 'nhan vien'), ('longest', 'cho lau'), ('wait', 'cho lau'),
                   ('busy', 'cao diem'), ('peak', 'cao diem'), ('summary', 'tom tat'), ('summarize', 'tom tat'),
                   ('right now', 'luc nay'), ('free table', 'ban trong'), ('false alarm', 'bao nham'),
                   ('unassigned', 'chua ai nhan'), ('new guest', 'khach moi'), ('check in', 'vao ca'),
                   ('weather', 'thoi tiet'), ('revenue', 'doanh thu'), ('table ', 'ban ')):
        if re.search(rf'\b{en}', q):
            q += ' ' + vi
    t = now_ms()
    al = viec(hub)
    blocks = []
    s = _khop_nv(hub, question)

    def them(*bs):
        blocks.extend(b for b in bs if b)

    def co(*tu):
        return any(x in q for x in tu)

    def tu(*ws):
        """Khớp nguyên từ, để 'mon' không dính vào 'mong'."""
        return any(re.search(rf'(?<![a-z]){re.escape(w)}(?![a-z])', q) for w in ws)

    # nhiều ngày: cả tuần, cả tháng, mấy ngày qua (đọc lịch sử lâu dài)
    kn = nhieu_ngay.khoang(q)
    if kn:
        return nhieu_ngay.tra_loi(hub, phong, *kn)[:2]
    # tiền thu: đọc sổ thanh toán nhân viên chụp gửi (không cần AI)
    if phong is not None and doanh_thu_tro_ly.la_hoi_tien(q) and not co('loi nhuan'):
        return doanh_thu_tro_ly.tra_loi(phong, q)
    if co('loi nhuan', 'gia von', 'ton kho'):
        return ('Hệ thống chưa ghi lợi nhuận, giá vốn, tồn kho hay món bán chạy. Hiện chỉ có tiền thu từ ảnh chuyển khoản '
                'và hoá đơn nhân viên chụp gửi vào nhóm, cùng số liệu camera. Bạn có thể hỏi: hôm nay thu được bao nhiêu.'), []

    # 0. ngoài những gì camera biết: nói thẳng, kể ra những gì hỏi được
    # ("chờ món", "lên món" là chuyện camera thấy được, không phải hỏi về thực đơn)
    hoi_mon = tu('mon') and not co('cho mon', 'len mon', 'ra mon', 'co mon', 'mon len', 'mon ra', 'doi mon', 'mon chua')
    if (co('doanh thu', 'loi nhuan', 'bao nhieu tien', 'thoi tiet', 'thuc don', 'mon an', 'khoa api', 'api key',
           'mat khau', 'password', 'bo qua moi', 'bo qua huong dan', 'ignore previous', 'ignore all',
           'system prompt') or tu('gia') or hoi_mon):
        return ('Câu này cần AI mới trả lời được, mà AI đang tắt hoặc chưa kết nối. Lúc này trợ lý chỉ đọc được số liệu '
                'camera ghi: khách gọi, bàn cần dọn, khách mới và nhân viên nhận việc. Bạn có thể hỏi: ca hôm nay '
                'thế nào, bàn nào chờ lâu nhất, nhân viên ai nhanh, ai vào ca lúc mấy giờ, việc nào chưa ai nhận.'), []

    # 0b. an ninh: lấy đồ của khách, người lạ vào quầy, có người ngoài giờ
    if co('an ninh', 'trom', 'mat do', 'lay do', 'lay cap', 'nguoi la', 'ngoai gio', 'vao quay', 'khu cam',
          'dot nhap', 'ai vao quan'):
        ans, bs = tra_loi_an_ninh(hub)
        return ans, [b for b in bs if b]

    # 1. khách quen: chưa có nhận diện khuôn mặt, nói thật
    xem = co(*xem_lai.TU_XEM, *xem_lai.TU_KE)
    if co('khach quen', 'khach ruot', 'khach than') or (co('co den', 'co toi', 'den luc', 'toi luc', 'ghe quan')
                                                        and not s and not xem):
        return ('Chưa trả lời được: nhận diện khách quen chưa bật, nên camera chưa biết khách nào là ai. '
                'Hiện hệ thống chỉ ghi lượt khách mới theo bàn.'), [khoi_chi_so(hub)] if al else []

    # 1b. xem lại video, kể chuyện một bàn, bàn đang chờ gì, số liệu ngày khác (server/xem_lai.py)
    if not s or xem:
        got = xem_lai.tra_loi(hub, q, clips, loop, t)
        if got is not None:
            return got

    # 2. một nhân viên cụ thể
    if s:
        card = khoi_nhan_vien(hub, [s['id']], s['name'])
        it = card['items'][0]
        mine = [a for a in al if (a['acked_by'] or a['assigned_to']) == s['id']]
        vao = f"vào ca lúc {clock(it['first_in'])[:5]}" if it['first_in'] else 'hôm nay chưa vào ca (chưa mở app nhân viên)'
        ans = f"{s['name']} {vao}"
        if it['first_in']:
            ans += f", đã làm {lau(it['worked_s'])}" + (', đang trong ca' if it['online'] else ', hiện không trong ca')
        ans += f". Nhận {it['acked']} việc, xong {it['done']}"
        ans += f", nhìn chung nhận việc {MUC_VI[muc(it['mean_response_s'])]}." if it['mean_response_s'] is not None else '.'
        them(card, khoi_su_kien(hub, [a['id'] for a in sorted(mine, key=lambda a: -a['created_at'])[:8]],
                                f"Việc của {s['name']}"))
        return ans, blocks

    # 2b. xem lại một thời điểm: "lúc 12:15", "12h15 bàn 5 có gì"
    m = re.search(r'(?<!\d)(\d{1,2})\s*(?::|h|gio)\s*(\d{2})(?!\d)', q)
    if m and int(m.group(1)) < 24 and int(m.group(2)) < 60:
        phut = int(m.group(1)) * 60 + int(m.group(2))
        tb = _khop_ban(hub, q)
        gan = []
        for a in al:
            c = clock(a['created_at'])
            lech = abs(int(c[:2]) * 60 + int(c[3:5]) - phut)
            if lech <= 3 and (not tb or a['table'] == tb):
                gan.append((lech, a))
        gio = f'{int(m.group(1)):02d}:{m.group(2)}'
        o_ban = f' ở bàn {tb}' if tb else ''
        if not gan:
            return f'Quanh {gio} camera không ghi sự kiện nào{o_ban}.', []
        gan.sort(key=lambda x: (x[0], x[1]['created_at']))
        them(khoi_su_kien(hub, [a['id'] for _, a in gan[:8]], f'Quanh {gio}{o_ban}'))
        return (f'Quanh {gio}{o_ban} có {len(gan)} sự kiện: '
                + '; '.join(cau_su_kien(hub, a, t) for _, a in gan[:3]) + '.'), blocks

    # 3. một bàn cụ thể
    tb = _khop_ban(hub, q)
    if tb:
        mine = [a for a in al if a['table'] == tb]
        if not mine:
            st = next((x for x in hub.tables.values() if x['id'] == tb), None)
            return (f'Bàn {tb} hôm nay chưa có sự kiện nào'
                    + (f", hiện {TABLE_VI.get(st['state'], st['state'])}." if st else '.')), []
        c = Counter(a['kind'] for a in mine)
        cho = [w for a in mine if a['status'] != 'cancelled' and (w := wait_s(a, t)) is not None]
        ans = (f"Bàn {tb} hôm nay: gọi phục vụ {c['call']} lần, cần dọn {c['needs_clearing']} lần, "
               f"khách mới {c['new_guest']} lượt.")
        if cho:
            ans += f' Về tốc độ phục vụ: {cau_dem(dem_muc(cho))}.'
        them(khoi_su_kien(hub, [a['id'] for a in sorted(mine, key=lambda a: -a['created_at'])[:10]],
                          f'Sự kiện ở bàn {tb}'))
        return ans, blocks

    # 3b. chấm công: ai vào ca lúc nào (không cần có việc)
    if co('vao ca', 'cham cong', 'di lam', 'den lam', 'gio vao', 'ai dang trong ca', 'ai dang lam'):
        card = khoi_nhan_vien(hub, title='Chấm công')
        if not card:
            return 'Chưa có nhân viên nào trong danh sách. Thêm ở Cài đặt, mục Nhân viên.', []
        it = sorted(card['items'], key=lambda x: (x['first_in'] is None, x['first_in'] or 0))
        vao = [x for x in it if x['first_in']]
        chua = [x['name'] for x in it if not x['first_in']]
        ans = ('; '.join(f"{x['name']} vào lúc {clock(x['first_in'])[:5]}" + ('' if x['online'] else ' (đã nghỉ)')
                         for x in vao) + '.') if vao else 'Chưa ai vào ca (chưa ai mở app nhân viên).'
        if vao and chua:
            ans += ' Chưa vào: ' + ', '.join(chua) + '.'
        them(khoi_bang('Chấm công', ['Nhân viên', 'Vào ca', 'Đã làm', 'Lúc này'],
                       [[x['name'], clock(x['first_in'])[:5] if x['first_in'] else 'chưa vào',
                         lau(x['worked_s']) if x['worked_s'] else 'chưa làm',
                         'đang trong ca' if x['online'] else 'không mở app'] for x in it]))
        return ans, blocks

    if not al:
        # máy chủ vừa khởi động lại hoặc vừa bắt đầu ca mới: việc trước đó trong ngày vẫn còn trong dòng thời gian
        return xem_lai.hom_nay_tu_lich_su(hub, t) or (tom_tat(hub), [])

    # 3b2. xếp ca: quãng nào thiếu người, quãng nào thừa
    if co('xep ca', 'xep nguoi', 'xep lich', 'thieu nguoi', 'them nguoi', 'bot nguoi', 'thua nguoi', 'du nguoi',
          'may nguoi', 'bao nhieu nguoi', 'lich lam', 'staffing'):
        them(goi_y.khoi_xep_ca(hub), khoi_bieu_do_thoi_gian(hub))
        return goi_y.cau_xep_ca(hub), blocks

    # 3b3. gợi ý cải thiện cho ca sau
    if co('goi y', 'cai thien', 'nen doi', 'nen lam gi', 'nen sua', 'can sua', 'ngay mai', 'ca sau', 'rut kinh nghiem',
          'khuyen', 'loi khuyen', 'tot hon', 'improve', 'suggest'):
        gy = goi_y.goi_y(hub)
        ans = (f'Có {len(gy)} điều nên xem cho ca sau. Trước hết: {gy[0]["title"].lower()}. {gy[0]["action"]}'
               if gy else 'Chưa đủ số liệu để gợi ý.')
        them(goi_y.khoi_goi_y(hub), goi_y.khoi_xep_ca(hub))
        return ans, blocks

    # 3b4. xem lại hình: "cho xem lại lúc khách gọi", "xem clip bàn cần dọn"
    if co('xem lai', 'cho xem', 'cho toi xem', 'video', 'clip', 'hinh anh', 'show me'):
        loai = 'call' if co('goi') else 'needs_clearing' if co('don') else 'new_guest' if co('khach moi') else ''
        lau_ = co('cho lau', 'doi lau', 'cham', 'lau nhat')
        got = loc_su_kien(hub, loai=loai, cho_hon_giay=FAST_S if lau_ else 0,
                          sap_xep='cho_lau_nhat' if lau_ else 'moi_nhat', gioi_han=8)
        got = [a for _, a in got if a['status'] != 'cancelled' and (a['crop_url'] or a.get('evidence'))]
        if not got:
            return 'Chưa có sự kiện nào có hình khớp với câu hỏi.', []
        ten = ('Những lần khách chờ lâu' if lau_ else 'Sự kiện gần đây') + (f' ({KIND_VI[loai]})' if loai else '')
        them(khoi_su_kien(hub, [a['id'] for a in got], ten))
        return f'Đây là {len(got)} sự kiện kèm hình camera, mới nhất là {cau_su_kien(hub, got[0], t).lower()}.', blocks

    # 3c. báo nhầm đã huỷ
    if co('bao nham', 'bao sai', 'nhan nham', 'da huy', 'bi huy') or tu('nham'):
        huy = [a for a in al if a['status'] == 'cancelled']
        if not huy:
            return 'Ca này chưa có báo nhầm nào bị huỷ.', []
        ans = f"Có {len(huy)} báo nhầm đã huỷ: " + ', '.join(
            f"{where(a['table'], a['camera'])} lúc {clock(a['created_at'])[:5]}" for a in huy[-5:]) + '.'
        them(khoi_su_kien(hub, [a['id'] for a in huy[-8:]], 'Báo nhầm đã huỷ'))
        return ans, blocks

    # 3d. việc chưa xong
    if co('chua ai nhan', 'chua nhan', 'chua xu ly', 'chua xong', 'viec ton', 'con ton', 'dang cho xu ly',
          'viec dang cho', 'con viec'):
        mo = [a for a in al if a['status'] not in CLOSED]
        if not mo:
            return 'Không còn việc nào tồn: mọi việc đã xong hoặc đã huỷ.', []
        chua = [a for a in mo if not a['acked_by']]
        ans = f'Còn {len(mo)} việc chưa xong'
        ans += (f", {len(chua)} việc chưa ai nhận: " + ', '.join(
            f"{where(a['table'], a['camera'])} ({KIND_VI[a['kind']]}, {cho_mo(wait_s(a, t))})" for a in chua[:4])
                + '.') if chua else ', đều đã có người nhận.'
        them(khoi_su_kien(hub, [a['id'] for a in chua][:8], 'Chưa ai nhận'),
             khoi_su_kien(hub, [a['id'] for a in mo if a['acked_by']][:8], 'Đang xử lý'))
        return ans, blocks

    # 3e. khách mới
    if co('khach moi', 'luot khach', 'bao nhieu khach', 'may khach', 'so khach'):
        r = hub.report()
        n = r['counts'].get('new_guest', 0)
        ans = f'Ca này có {n} lượt khách mới vào bàn.'
        ban = max(r['per_table'], key=lambda x: x['guests'], default=None)
        if ban and ban['guests']:
            ans += f" Bàn đón nhiều khách nhất là bàn {ban['table']} ({ban['guests']} lượt)."
        pts = sorted((dict(label=f"Bàn {x['table']}", value=x['guests'], note=None) for x in r['per_table']
                      if x['guests']), key=lambda p: -p['value'])[:12]
        if pts:
            them(dict(type='chart', title='Lượt khách mới theo bàn', kind='bar', unit='lượt', points=pts))
        return ans, blocks

    # 4. chờ lâu nhất
    if co('lau nhat', 'cham nhat', 'cho lau', 'doi lau', 'phai cho', 'phai doi'):
        top = loc_su_kien(hub, sap_xep='cho_lau_nhat', gioi_han=5)
        top = [(w, a) for w, a in top if w is not None and a['status'] != 'cancelled']
        if not top:
            return 'Chưa có lần chờ nào được ghi lại.', []
        w, a = top[0]
        dang_cho = a['status'] not in CLOSED and not a['acked_by']       # câu sau đã nói khách còn đang chờ
        ans = (f"{where(a['table'], a['camera'])} chờ lâu nhất, lúc {clock(a['created_at'])[:5]} "
               f"({KIND_VI[a['kind']]})" + ('.' if dang_cho else f': {chu_cho(a, w)}.'))
        if a['status'] not in CLOSED:
            ans += ((' Bàn vẫn chưa ai dọn.' if a['kind'] == 'needs_clearing' else ' Việc này vẫn chưa ai nhận, khách còn đang chờ.')
                    if not a['acked_by'] else ' Đã có người nhận nhưng chưa xong.')
        them(khoi_su_kien(hub, [x['id'] for _, x in top], 'Những lần khách chờ lâu nhất'),
             khoi_bieu_do_cho_theo_ban(hub))
        return ans, blocks

    # 5. nhân viên nói chung
    if co('nhan vien', 'chat luong', 'hieu suat', 'phuc vu the nao', 'phuc vu ra sao', 'ai lam', 'khen thuong',
          'nen thuong', 'thuong cho', 'thuong ai', 'gioi nhat', 'tot nhat', 'xuat sac', 'nhanh nhat'):
        ps = [s for s in hub.report()['per_staff'] if s['mean_response_s'] is not None]
        if ps:
            nhanh, cham = min(ps, key=lambda s: s['mean_response_s']), max(ps, key=lambda s: s['mean_response_s'])
            ans = f"{nhanh['name']} phản hồi nhanh nhất"
            the_nao = {'fast': 'nhưng vẫn nhanh', 'ok': 'đôi lúc để khách chờ hơi lâu',
                       'slow': 'thường để khách chờ lâu'}[muc(cham['mean_response_s'])]
            ans += (f"; {cham['name']} chậm nhất, {the_nao}." if cham is not nhanh and cham['mean_response_s'] > nhanh['mean_response_s'] else '.')
        else:
            ans = 'Chưa nhân viên nào bấm nhận việc trên app, nên chưa so được từng người.'
        nx = nhan_xet(hub.report()['speed'])
        if nx:
            ans += f' Cả ca phục vụ nhìn chung {MUC_VI[nx]}.'
        them(khoi_chi_so(hub), khoi_bieu_do_nhan_vien(hub), khoi_nhan_vien(hub))
        return ans, blocks

    # 6. giờ bận nhất
    if co('gio nao', 'ban nhat', 'cao diem', 'dong nhat', 'dong khach', 'luc nao', 'khi nao'):
        ch = khoi_bieu_do_thoi_gian(hub)
        dinh = max(ch['points'], key=lambda p: p['value'])
        ans = f"Bận nhất quanh {dinh['label']}: {dinh['value']} sự kiện" + (f" ({dinh['note']})." if dinh['note'] else '.')
        ban = max(hub.report()['per_table'], key=lambda x: x['calls'] + x['clearings'], default=None)
        if ban:
            ans += f" Bàn có nhiều việc nhất là bàn {ban['table']}."
        them(ch, khoi_bieu_do_ban(hub))
        return ans, blocks

    # 7. đáng chú ý
    if co('dang chu y', 'co gi', 'bat thuong', 'su co', 'van de', 'chuyen gi', 'noi bat'):
        cham = [a for w, a in loc_su_kien(hub, sap_xep='cho_lau_nhat', cho_hon_giay=FAST_S, gioi_han=4)
                if a['status'] != 'cancelled']
        huy = [a for a in al if a['status'] == 'cancelled'][-3:]
        mo = [a for a in al if a['status'] not in CLOSED]
        phan = []
        if cham:
            phan.append(f'{len(cham)} lần khách phải chờ lâu')
        if huy:
            phan.append(f"{sum(1 for a in al if a['status'] == 'cancelled')} báo nhầm đã được lọc")
        if mo:
            phan.append(f'{len(mo)} việc đang chờ')
        ans = ('Đáng chú ý: ' + ', '.join(phan) + '.') if phan else \
            'Ca chạy êm: không có lần nào khách phải chờ lâu, không có báo nhầm, không còn việc tồn.'
        them(khoi_su_kien(hub, [a['id'] for a in cham], 'Khách chờ lâu'),
             khoi_su_kien(hub, [a['id'] for a in mo][:6], 'Việc đang chờ'),
             khoi_su_kien(hub, [a['id'] for a in huy], 'Báo nhầm đã lọc'), khoi_chi_so(hub))
        return ans, blocks

    # 8. các bàn lúc này
    if co('luc nay', 'bay gio', 'hien tai', 'ban trong', 'con trong', 'dang cho'):
        ds = list(hub.tables.values())
        mo = [a for a in al if a['status'] not in CLOSED]
        c = Counter(x['state'] for x in ds)
        ans = (f"Lúc này {c['occupied']} bàn có khách, {c['empty']} bàn trống, {c['needs_clearing']} bàn cần dọn; "
               f"{len(mo)} việc đang chờ.") if ds else f'Camera chưa gửi trạng thái bàn. {len(mo)} việc đang chờ.'
        them(khoi_bang_ban(hub) if ds else None, khoi_su_kien(hub, [a['id'] for a in mo][:8], 'Việc đang chờ'))
        return ans, blocks

    # 9. tóm tắt (mặc định)
    them(khoi_chi_so(hub), khoi_bieu_do_thoi_gian(hub), khoi_bieu_do_ban(hub))
    return tom_tat(hub), blocks


def _khop_nv(hub, question):
    """Nhân viên được nhắc tên trong câu hỏi. So có dấu trước ("Tú" không khớp chữ "từ"); câu gõ không dấu
    thì so không dấu."""
    co_dau = (question or '').lower()
    khong_dau = bo_dau(question)
    go_khong_dau = co_dau == khong_dau

    def co(k, cau):
        return bool(k) and re.search(rf'(?<![^\W_]){re.escape(k)}(?![^\W_])', cau) is not None

    for s in hub.staff:
        if co(s['name'].lower(), co_dau) or (go_khong_dau and (co(bo_dau(s['name']), khong_dau)
                                                              or co(bo_dau(s['id']), khong_dau))):
            return s
    return None


# ====================================================================== tác tử Google ADK
LOI_DAN = """Bạn là trợ lý của chủ một quán ăn. Hệ thống camera AI Easy FnB ghi lại ca làm việc hôm nay (giờ Việt Nam):
khách giơ tay gọi phục vụ, bàn cần dọn, khách mới vào bàn, nhân viên nhận việc và tới bàn, chấm công nhân viên.

Cách làm việc:
1. Câu hỏi về quán, ca hôm nay, khách, bàn, nhân viên: luôn gọi công cụ đọc dữ liệu trước (so_lieu_ca, tim_su_kien, trang_thai_ban, ban_dang_the_nao, nhan_vien_va_cham_cong, phan_tich_ca). Chỉ dùng số liệu công cụ trả về, không bịa.
2. Chọn dạng hiển thị hợp với câu hỏi bằng công cụ hiển thị. Mỗi lần gọi thêm một khối vào câu trả lời, số liệu trong khối do hệ thống tự điền:
   - Câu hỏi chung (ca thế nào, chất lượng nhân viên, tóm tắt): hien_chi_so và một hoặc hai hien_bieu_do. Hỏi về nhân viên thì thêm hien_nhan_vien.
   - Câu hỏi cụ thể (bàn nào, lúc nào, lần nào, ai): hien_su_kien với đúng các mã sự kiện liên quan, để chủ quán xem ảnh camera.
   - Hỏi về xu hướng theo giờ: hien_bieu_do('thoi_gian'). So sánh bàn: hien_bieu_do('ban'). So sánh người: hien_bieu_do('nhan_vien').
   - Hỏi nên đổi gì, cải thiện gì, lời khuyên cho ca sau: đọc phan_tich_ca rồi hien_goi_y. Hỏi xếp ca, thiếu hay thừa người, nên thêm mấy người, giờ nào cần ai: đọc phan_tich_ca rồi hien_xep_ca.
   - Hệ thống có lưu video camera. Hễ câu hỏi có ý muốn xem (xem, xem lại, video, clip, quay lại, lúc đó ra sao, chuyện gì xảy ra lúc mấy giờ, lần nào đó thế nào): gọi xem_video để video hiện ngay trong câu trả lời. Biết mã sự kiện (từ tim_su_kien) thì đưa mã; hỏi theo giờ hoặc theo bàn thì đưa giờ, bàn; hỏi lần khách chờ lâu nhất thì đặt cho_lau_nhat. Không bao giờ nói là không xem được video khi chưa gọi xem_video; công cụ báo không có video thì nói lại đúng lý do nó đưa.
   - Kể lại chuyện của một bàn hoặc một quãng giờ (khách vào lúc nào, ai ra tiếp, món lên, ăn xong, rời bàn, dọn bàn): gọi dong_thoi_gian, nó hiện từng bước kèm video.
   - Bàn nào đang chờ, đang chờ món, chờ tính tiền, chưa ai ra tiếp, bữa ăn tới đâu: gọi ban_dang_the_nao.
   - Hỏi về ngày khác (hôm qua, thứ hai, ngày 12/11) hoặc so hai ngày: gọi so_sanh_ngay. Các công cụ còn lại chỉ đọc ca hôm nay.
   - Hỏi về nhiều ngày (tuần này, tuần trước, 7 ngày qua, tháng này, tháng trước, từ ngày này đến ngày kia, xu hướng, ngày nào đông nhất, hệ thống lưu những ngày nào): gọi nhieu_ngay. Lịch sử được lưu lâu dài, không được nói là hệ thống chỉ lưu hôm nay.
   - Hỏi về nhân viên của một ngày đã qua (hôm qua ai vào ca lúc mấy giờ, ngày 12/11 ai làm nhanh nhất): gọi nhan_vien_ngay_cu.
   - Hỏi về an ninh, trộm, mất đồ, ai lấy đồ của khách, người lạ vào quầy hay kho, có ai vào quán ngoài giờ (đêm qua, lúc đóng cửa): gọi an_ninh, nó hiện các cảnh báo kèm ảnh và video.
   - Hỏi về doanh thu, tiền thu, thanh toán, hoá đơn, chuyển khoản, khoản lớn nhất, mỗi khách chi bao nhiêu, khách về mà chưa trả tiền, khoản đã huỷ: gọi doanh_thu (ngày khác thì đưa ngay; so hai ngày thì đưa thêm so_voi_ngay), nó tự hiện số liệu và biểu đồ. Đang nói chuyện tiền mà chủ quán hỏi tiếp "so với hôm qua thì sao" thì vẫn gọi doanh_thu với so_voi_ngay, không gọi so_sanh_ngay. Câu hỏi hẹp (khoản bị huỷ, khoản lớn nhất, một bàn, bao nhiêu chuyển khoản) thì đặt tham số hien là false và chỉ trả lời bằng câu. Ngày của quán tính tới 4 giờ sáng: khách và tiền sau nửa đêm vẫn thuộc hôm nay (xem theo_gio các giờ 00 đến 03), không phải hôm qua. Khoản nhân viên đã sửa số tiền nằm ở da_sua_so_tien. Số tiền viết đầy đủ kiểu 6.805.000 đ. Tiền này chỉ gồm khoản nhân viên đã chụp gửi vào nhóm.
   - Danh sách có nhiều cột mà các khối trên không hợp: hien_bang.
   Dùng tối đa 4 khối, không lặp lại cùng một khối.
3. Sau đó viết câu trả lời bằng tiếng Việt, 1 đến 3 câu (câu hỏi xin lời khuyên thì tối đa 6 câu), đi thẳng vào kết luận kèm con số chính. Tốc độ phục vụ thì nói bằng chữ như công cụ trả về (nhanh, hơi chậm, chậm, không ai tới), không nêu số giây hay số phút chờ. Văn bản thường có viết hoa đầu câu, giờ viết dạng 12:07, không markdown, không gạch đầu dòng, không nhắc tên công cụ hay mã sự kiện.
4. Thiếu dữ liệu thì nói thẳng. Hệ thống CHƯA nhận diện khách quen theo khuôn mặt: câu hỏi kiểu "anh Nam hôm nay có tới không" thì trả lời là chưa bật nhận diện khách quen, trừ khi tên đó là nhân viên.
5. Chủ quán hỏi gì cũng trả lời. Câu hỏi ngoài dữ liệu camera (kinh nghiệm quản lý quán, giữ chân nhân viên, xử lý khách phàn nàn, thực đơn, khuyến mãi, quảng cáo, luật lao động, tính toán, kiến thức chung) thì trả lời thẳng bằng hiểu biết của bạn, thực tế và hợp với quán ăn ở Việt Nam, không cần gọi công cụ hiển thị. Nếu số liệu ca giúp lời khuyên sát hơn thì đọc công cụ và dẫn ra. Riêng số liệu của chính quán mà hệ thống không ghi (món bán chạy, tồn kho, lợi nhuận, giá vốn) thì nói rõ là hệ thống chưa ghi, không bịa số, rồi gợi ý cách làm chung.
6. Chủ quán muốn cài đặt thì làm luôn trong chat, không bảo họ vào trang Cài đặt: nối camera, cài camera điện thoại: noi_camera. Tìm bàn, vẽ bàn, đặt bàn: tu_tim_ban. Thêm, bỏ, đổi tên hay vai trò nhân viên: sua_nhan_vien (vai trò: phục vụ, dọn bàn, thu ngân, chủ quán). Điện thoại nhân viên, mã QR, app nhân viên: ma_qr_nhan_vien. Đổi luật báo, nhắc lại, chờ AI xác nhận, nhắc khách chờ, giờ mở hay đóng cửa, trông quán, các loại báo an ninh, giờ giao hàng: doi_luat_bao, chỉ đưa tham số muốn đổi. Che mặt cần mã PIN: bảo chủ quán vào Cài đặt. Ảnh nhận dạng nhân viên: chup_anh_nhan_vien. Các công cụ này chỉ hiện khối, dữ liệu chỉ đổi khi chủ quán bấm Lưu trong khối: nói ngắn "kiểm lại rồi bấm Lưu", KHÔNG BAO GIỜ nói đã lưu hay đã xong. Công cụ báo lỗi (camera chưa nối...) thì nói đúng lý do. Câu chung chung như "giúp tôi setup" thì hỏi một câu xem họ muốn cài gì, không gọi công cụ. Không nhận và không nhắc lại khoá API: khoá đặt trong tệp .env hoặc biến môi trường của máy chủ. Câu bắt đầu bằng [Hệ thống: ...] là ghi chú việc chủ quán vừa bấm Lưu, dùng để biết dữ liệu đã đổi."""


# Công cụ chỉ chủ quán dùng (cài đặt), không có trong phòng chat của quán (che_do='phong')
CONG_CU_CHI_CHU = {'noi_camera', 'tu_tim_ban', 'sua_nhan_vien', 'ma_qr_nhan_vien', 'doi_luat_bao', 'chup_anh_nhan_vien'}


class TroLy:
    def __init__(self, hub, llm):
        self.hub = hub
        self.llm = llm
        la_gemini = getattr(llm, 'ten', '') == 'Gemini'   # máy chủ có thể đang dùng kie.ai cho việc khác
        self.model = (os.environ.get('GEMINI_MODEL', '').strip() or (la_gemini and getattr(llm, 'model', None))
                      or 'gemini-3.5-flash-lite')
        self._adk = None          # module đã nạp: (Agent, Runner, types), False nếu nạp lỗi
        self._sessions = None
        self._runners = {}        # session id -> (Runner, hộp chứa khối của lượt đang chạy)
        self._locks = {}
        self.phong = None         # phòng chat giữ sổ thanh toán (server/chat.py), app.py gắn vào; None thì không trả lời về tiền
        self.clips = None         # kho clip (server/clips.py), app.py gắn vào sau khi tạo; None thì trả lời chỉ kèm ảnh
        self._loop = None         # vòng lặp asyncio của máy chủ: kho clip phải được gọi trong vòng lặp này

    # ---------------------------------------------------------------- chọn đường
    @property
    def adk_wanted(self):
        """Dùng ADK khi có khoá Gemini, kể cả lúc máy chủ đang dùng kie.ai cho việc khác (ADK chỉ chạy với Gemini)."""
        if getattr(self.llm, 'ten', '') == 'Gemini':
            return bool(getattr(self.llm, 'enabled', False))
        return bool(os.environ.get('GEMINI_API_KEY', '').strip())

    def load_adk(self):
        """Nạp google-adk (mất vài giây lần đầu). Trả False nếu chưa cài hoặc lỗi."""
        if self._adk is None:
            try:
                from google.adk.agents import Agent
                from google.adk.runners import Runner
                from google.adk.sessions import InMemorySessionService
                from google.genai import types
                self._adk = (Agent, Runner, types)
                self._sessions = InMemorySessionService()
            except Exception as e:   # noqa: BLE001  thiếu gói hay gói lỗi đều đi đường rules
                log.warning('Không nạp được google-adk, trợ lý chạy không AI: %s', e)
                self._adk = False
        return self._adk

    # ---------------------------------------------------------------- công cụ của tác tử
    def tools(self, box, che_do='chu'):
        """Công cụ cho một phiên. `box['blocks']` là nơi các công cụ hiển thị bỏ khối vào; mỗi lượt hỏi
        gán một list mới. che_do='phong' (phòng chat của quán, có cả nhân viên): bỏ công cụ cài đặt và công cụ
        hiển thị khối, chỉ giữ công cụ đọc số liệu."""
        hub = self.hub

        def them(b, khong_co='Không có dữ liệu để hiện.'):
            if b is None:
                return dict(ket_qua=khong_co)
            if len(box['blocks']) >= 5:
                return dict(ket_qua='Đã đủ khối, không thêm nữa.')
            khoa = lambda x: (x.get('type'), [(i.get('alert_id'), i.get('t')) for i in x.get('items') or []])
            if b.get('type') in ('video', 'events', 'timeline') and any(khoa(x) == khoa(b) for x in box['blocks']):
                return dict(ket_qua='Khối này đã hiện rồi, không hiện lại.')   # mô hình đôi khi gọi hai lần cùng một video
            if any(x.get('type') == b.get('type') and x.get('title') == b.get('title') and x.get('title')
                   for x in box['blocks']):
                return dict(ket_qua='Khối này đã hiện rồi, không hiện lại.')   # hai công cụ cùng dựng một biểu đồ
            box['blocks'].append(b)
            return dict(ket_qua='Đã hiện cho chủ quán.')

        def so_lieu_ca() -> dict:
            """Số liệu tổng của ca hôm nay: số lần khách gọi, bàn cần dọn, khách mới, tốc độ phục vụ (bao nhiêu việc nhanh, hơi chậm, chậm, không ai tới), báo nhầm, số liệu từng nhân viên và từng bàn."""
            ls = hom_nay_lich_su(hub)
            if ls is not None:
                return ls
            r = hub.report()
            sp = r['speed']
            return dict(tu=clock(r['from']), den=clock(r['to']), so_lan=dict(
                            goi_phuc_vu=r['counts']['call'], can_don=r['counts']['needs_clearing'],
                            khach_moi=r['counts']['new_guest']),
                        toc_do_phuc_vu=dict(nhan_xet=MUC_VI.get(nhan_xet(sp)), viec_nhanh=sp['fast'],
                                            viec_hoi_cham=sp['ok'], viec_cham=sp['slow'],
                                            viec_khong_ai_toi=sp['missed']),
                        bao_nham_da_huy=r['cancelled'],
                        viec_dang_cho=sum(1 for a in viec(hub) if a['status'] not in CLOSED),
                        theo_nhan_vien=[dict(ma=s['id'], ten=s['name'], nhan=s['acked'], xong=s['done'],
                                             toc_do_nhan_viec=MUC_VI.get(muc(s['mean_response_s'])),
                                             viec_nhanh=s['fast'], viec_hoi_cham=s['ok'], viec_cham=s['slow'])
                                        for s in r['per_staff']],
                        theo_ban=[dict(ban=x['table'], goi=x['calls'], can_don=x['clearings'], khach_moi=x['guests'])
                                  for x in r['per_table']])

        def hien_chu_y():
            """Hôm nay có lần nhân viên bấm nhận mà không tới bàn: hiện video và dòng thời gian quanh lần gần nhất."""
            rs = nghe_khong_toi(xem_lai.tong_ket_ngay(hub, xem_lai.hom_nay())['recs'])
            if not rs:
                return {}
            r = rs[-1]
            xin = xem_lai.Xin(hub, self.clips, self._loop)
            ten = f"Bàn {r['ban']} lúc {clock(r['t'])[:5]}: {xem_lai.duoi_viec(hub, r)}"
            _, bs = xem_lai.xem_su_kien(hub, '', r['ban'], xin, ids=[r['aid']])
            for b in bs:
                if b['type'] == 'video':
                    them(dict(b, title=ten))
            g = xem_lai.doc_gio(bo_dau(f"tu {clock(r['t'] - 240_000)[:5]} den {clock(r['t'] + 180_000)[:5]}"))
            if g:
                for b in xem_lai.ke_lai(hub, r['ban'], g, None, xin)[1]:
                    them(b)
            return dict(can_chu_y=[dict(gio=clock(x['t'])[:5], ban=x['ban'], nhan_vien=ten_nv(hub, x['nv']),
                                        chuyen='bấm nhận trên điện thoại nhưng không tới bàn') for x in rs],
                        da_hien_video=ten)

        def tim_su_kien(loai: str = '', ban: str = '', nhan_vien: str = '', tu_gio: str = '', den_gio: str = '',
                        cho_hon_giay: int = 0, sap_xep: str = 'moi_nhat', gioi_han: int = 10) -> dict:
            """Tìm sự kiện trong ca. Mọi tham số đều tuỳ chọn, bỏ trống là không lọc.

            Args:
                loai: goi_phuc_vu, can_don hoặc khach_moi.
                ban: mã bàn, ví dụ B2.
                nhan_vien: tên hoặc mã nhân viên nhận việc.
                tu_gio: chỉ lấy từ giờ này, dạng HH:MM.
                den_gio: chỉ lấy tới giờ này, dạng HH:MM.
                cho_hon_giay: chỉ lấy sự kiện khách phải chờ lâu hơn số giây này. 30 là từ hơi chậm trở lên, 60 là chậm.
                sap_xep: moi_nhat hoặc cho_lau_nhat.
                gioi_han: số sự kiện tối đa, nhiều nhất 30.
            """
            if not viec(hub):
                return su_kien_lich_su(hub, loai, ban, nhan_vien, tu_gio, den_gio, cho_hon_giay, sap_xep, gioi_han)
            got = loc_su_kien(hub, loai, ban, nhan_vien, tu_gio, den_gio, cho_hon_giay, sap_xep, gioi_han)
            return dict(tong=len(got), su_kien=[dict(
                ma=a['id'], loai=KIND_VI[a['kind']], ban=a['table'], gio=clock(a['created_at']),
                toc_do=chu_cho(a, w) if w is not None else None,
                nhan_vien=ten_nv(hub, a['acked_by'] or a['assigned_to']), trang_thai=STATUS_VI.get(a['status']),
                ly_do_huy=a['cancel_reason'], co_anh=bool(a['crop_url'] or a.get('evidence'))) for w, a in got])

        def trang_thai_ban() -> dict:
            """Trạng thái từng bàn ngay lúc này (trống, có khách, cần dọn) và số người đang ngồi."""
            t = now_ms()
            return dict(ban=[dict(ban=x['id'], trang_thai=TABLE_VI.get(x['state'], x['state']), so_nguoi=x['people'],
                                  da_duoc=lau((t - x['since']) / 1000) if x.get('since') else None)
                             for x in hub.tables.values()])

        def nhan_vien_va_cham_cong() -> dict:
            """Danh sách nhân viên: vai trò, có đang trong ca không, giờ vào ca đầu tiên, tổng thời gian làm, số việc đã nhận và đã xong, nhận việc nhanh hay chậm."""
            if not viec(hub):
                ans, _, rows = nhieu_ngay.nhan_vien_ngay(hub, xem_lai.hom_nay())
                if rows:
                    return dict(ghi_chu=LS_GHI_CHU, tom_tat=ans, nhan_vien=rows)
            return _nhan_vien_va_cham_cong()

        def _nhan_vien_va_cham_cong() -> dict:
            b = khoi_nhan_vien(hub) or dict(items=[])
            return dict(nhan_vien=[dict(ma=s['id'], ten=s['name'], vai_tro=ROLE_VI.get(s['role'], s['role']),
                                        dang_trong_ca=s['online'],
                                        vao_ca_luc=clock(s['first_in']) if s['first_in'] else None,
                                        da_lam=lau(s['worked_s']), nhan=s['acked'], xong=s['done'],
                                        toc_do_nhan_viec=MUC_VI.get(muc(s['mean_response_s'])))
                                   for s in b['items']])

        def phan_tich_ca() -> dict:
            """Phân tích ca để khuyên chủ quán: danh sách vấn đề kèm việc nên làm (thiếu người quãng nào, bàn hay phải chờ, dọn bàn chậm, việc dồn vào một người, bàn hay báo nhầm, ai đáng khen) và bảng xếp ca theo từng quãng giờ (số việc, số người trong ca, số lần khách chờ lâu, thiếu hay thừa người)."""
            return goi_y.du_lieu(hub)

        def hien_goi_y() -> dict:
            """Hiện cho chủ quán các gợi ý cho ca sau, mỗi gợi ý kèm việc nên làm và hình camera làm bằng chứng."""
            return them(goi_y.khoi_goi_y(hub), 'Chưa đủ số liệu để gợi ý.')

        def hien_xep_ca() -> dict:
            """Hiện bảng xếp ca: từng quãng giờ có bao nhiêu việc, mấy người trong ca, khách chờ lâu mấy lần, nên thêm hay bớt người."""
            return them(goi_y.khoi_xep_ca(hub), 'Ca chưa có việc nào để xếp ca.')

        def hien_chi_so() -> dict:
            """Hiện cho chủ quán một hàng ô chỉ số của ca (số lần gọi, cần dọn, khách mới, tốc độ phục vụ, bàn chờ lâu nhất, báo nhầm, việc đang chờ). Hôm nay có lần nhân viên bấm nhận mà không tới bàn thì hiện luôn video và dòng thời gian lúc đó."""
            ls = khoi_hom_nay_lich_su(hub)
            if ls:      # ca trong bộ nhớ trống (máy chủ vừa khởi động): ô chỉ số và cột theo giờ của cả hôm nay
                kq = [them(b) for b in ls]
                return dict(kq[0], ghi_chu=LS_GHI_CHU, da_hien_them='biểu đồ số việc theo giờ', **hien_chu_y())
            return them(khoi_chi_so(hub))

        def hien_bieu_do(chu_de: str) -> dict:
            """Hiện một biểu đồ cho chủ quán.

            Args:
                chu_de: nhan_vien (phần việc nhận nhanh của từng người), ban (số lần gọi và cần dọn từng bàn), thoi_gian (số sự kiện theo thời gian trong ca) hoặc cho_theo_ban (số lần khách phải chờ lâu ở từng bàn).
            """
            f = {'nhan_vien': khoi_bieu_do_nhan_vien, 'ban': khoi_bieu_do_ban, 'thoi_gian': khoi_bieu_do_thoi_gian,
                 'cho_theo_ban': khoi_bieu_do_cho_theo_ban}.get(bo_dau(chu_de).replace(' ', '_'))
            if f is None:
                return dict(ket_qua='chu_de phải là nhan_vien, ban, thoi_gian hoặc cho_theo_ban.')
            ls = khoi_hom_nay_lich_su(hub)
            if ls and f is khoi_bieu_do_thoi_gian:
                return dict(them(ls[1]), ghi_chu=LS_GHI_CHU)
            if ls and f is khoi_bieu_do_nhan_vien:
                return hien_nhan_vien([])
            b = f(hub)
            kq = them(b, 'Chưa có số liệu cho biểu đồ này.')
            if b and b.get('points'):     # đưa lại số trong biểu đồ để câu trả lời không nói khác hình
                cao = max(b['points'], key=lambda p: p['value'])
                kq = dict(kq, tieu_de=b['title'], cao_nhat=dict(nhan=cao['label'], gia_tri=cao['value']),
                          cac_cot=[(p['label'], p['value']) for p in b['points']][:24])
            return kq

        def hien_su_kien(tieu_de: str, ma_su_kien: list[str]) -> dict:
            """Hiện danh sách sự kiện kèm ảnh camera, giờ và mức chờ (nhanh hay chậm).

            Args:
                tieu_de: tiêu đề ngắn của danh sách, ví dụ "Những lần bàn B2 gọi".
                ma_su_kien: các mã sự kiện lấy từ tim_su_kien, ví dụ ["a3", "a7"]. Tối đa 10 mã.
            """
            return them(khoi_su_kien(hub, list(ma_su_kien)[:10], tieu_de or 'Sự kiện'), 'Không có mã sự kiện nào đúng.')

        def hien_nhan_vien(ma_nhan_vien: list[str]) -> dict:
            """Hiện thẻ nhân viên (chấm công, số việc, nhận việc nhanh hay chậm).

            Args:
                ma_nhan_vien: mã hoặc tên các nhân viên cần hiện. Danh sách rỗng là hiện mọi người.
            """
            if not viec(hub):     # ca trong bộ nhớ trống: bảng nhân viên hôm nay đọc từ lịch sử
                ans, bs, rows = nhieu_ngay.nhan_vien_ngay(hub, xem_lai.hom_nay())
                if rows:
                    return dict(them(bs[0]), tom_tat=ans, tung_nguoi=rows, ghi_chu=LS_GHI_CHU)
            return them(khoi_nhan_vien(hub, list(ma_nhan_vien or [])), 'Không có nhân viên nào khớp.')

        def hien_bang(tieu_de: str, cot: list[str], hang: list[str]) -> dict:
            """Hiện một bảng tự do. Chỉ dùng khi các khối khác không hợp.

            Args:
                tieu_de: tiêu đề bảng.
                cot: tên các cột.
                hang: mỗi phần tử là một hàng, các ô nối bằng " | ", ví dụ "B2 | 3 lần | hơi chậm".
            """
            return them(khoi_bang(tieu_de, list(cot), list(hang)), 'Bảng trống.')

        def tim_ban(ban):
            """(mã bàn thật, None) hoặc (None, lời báo cho mô hình) khi không có bàn đó."""
            if not str(ban or '').strip():
                return None, None
            tb, biet = xem_lai.tim_ban(hub, 'ban ' + _khoa_ban(ban))
            return (tb, None) if biet else (None, f'Hệ thống không theo dõi bàn nào tên {ban}.')

        def cau_gio(tu_gio, den_gio, ngay):
            tu_gio, den_gio = str(tu_gio or '').strip(), str(den_gio or '').strip()
            if bo_dau(tu_gio) in xem_lai.BUOI and not den_gio:      # "trưa", "tối": cả buổi đó
                return bo_dau(f'{tu_gio} {ngay or "nay"}').strip()
            gio = f'tu {tu_gio} den {den_gio}' if tu_gio and den_gio else f'luc {tu_gio or den_gio}' if tu_gio or den_gio else ''
            return bo_dau(f'{gio} {ngay or ""}').strip()

        def xem_video(ma_su_kien: str = '', ban: str = '', gio: str = '', den_gio: str = '', ngay: str = '',
                      loai: str = '', cho_lau_nhat: bool = False, tieu_de: str = '') -> dict:
            """Hiện video camera cho chủ quán xem ngay trong câu trả lời. Dùng mỗi khi chủ quán muốn xem lại một lúc nào đó. Mọi tham số đều tuỳ chọn.

            Args:
                ma_su_kien: các mã sự kiện lấy từ tim_su_kien, cách nhau bằng dấu phẩy, ví dụ "a3,a7". Có mã thì bỏ qua các tham số lọc khác.
                ban: mã bàn, ví dụ B2.
                gio: giờ muốn xem, dạng HH:MM, hoặc "5 phút trước", "vừa rồi".
                den_gio: nếu muốn xem cả một quãng thì đây là giờ kết thúc, dạng HH:MM.
                ngay: bỏ trống là hôm nay; hoặc "hôm qua", hoặc dạng YYYY-MM-DD. Video chỉ được giữ khoảng một ngày.
                loai: goi_phuc_vu, can_don hoặc khach_moi, khi muốn xem các sự kiện gần đây của một loại.
                cho_lau_nhat: true để xem lần khách phải chờ lâu nhất.
                tieu_de: tiêu đề ngắn cho khối video.
            """
            xin = xem_lai.Xin(hub, self.clips, self._loop)
            ids = [x for x in re.split(r'[,;\s]+', str(ma_su_kien or '').strip('[] ')) if x]
            tb, loi = tim_ban(ban)
            if loi and not ids:
                return dict(ket_qua=loi)
            g = xem_lai.doc_gio(cau_gio(gio, den_gio, ngay)) if (gio or den_gio) and not ids else None
            if g:
                ans, bs = xem_lai.xem_thoi_diem(hub, g, tb, xin)
            else:
                cau = bo_dau(loai).replace('_', ' ') + (' cho lau nhat' if cho_lau_nhat else '')
                ans, bs = xem_lai.xem_su_kien(hub, cau, tb, xin, ids=ids or None)
            vb = next((b for b in bs if b['type'] == 'video'), None)
            b = vb or next((b for b in bs if b['type'] == 'events'), None)
            if b is None:
                return dict(ket_qua=ans, co_video=False)
            if tieu_de:
                b = dict(b, title=tieu_de)
            kq = them(b)
            return dict(ket_qua=kq['ket_qua'], tom_tat=ans, co_video=xem_lai.co_video(vb),
                        clip=[dict(gio=clock(it['t'])[:5], ban=it['table'], noi_dung=it['label'],
                                   ly_do_khong_co_video=it['error']) for it in (vb or dict(items=[]))['items']])

        def dong_thoi_gian(ban: str = '', tu_gio: str = '', den_gio: str = '', ngay: str = '') -> dict:
            """Kể lại từng bước chuyện của một bàn hoặc một quãng giờ (khách vào, nhân viên ra tiếp, món lên, khách gọi, ăn xong, rời bàn, dọn bàn) và hiện cho chủ quán dòng thời gian kèm video. Đọc được cả ngày khác.

            Args:
                ban: mã bàn, ví dụ B2. Bỏ trống là mọi bàn.
                tu_gio: từ giờ này, dạng HH:MM; chủ quán nói một buổi thì đưa đúng chữ đó: "sáng", "trưa", "chiều" hoặc "tối". Chỉ đưa bàn mà bỏ trống giờ thì lấy lượt khách mới nhất của bàn.
                den_gio: tới giờ này, dạng HH:MM.
                ngay: bỏ trống là hôm nay; hoặc "hôm qua", hoặc dạng YYYY-MM-DD.
            """
            tb, loi = tim_ban(ban)
            if loi:
                return dict(ket_qua=loi)
            cau = cau_gio(tu_gio, den_gio, ngay)
            ngays = xem_lai.doc_cac_ngay(cau)
            ans, bs, dong = xem_lai.ke_lai(hub, tb, xem_lai.doc_gio(cau) if (tu_gio or den_gio) else None,
                                           ngays[0] if ngays else None, xem_lai.Xin(hub, self.clips, self._loop))
            for b in bs:
                them(b)
            return dict(tom_tat=ans, da_hien=bool(bs),
                        cac_buoc=[dict(gio=clock(x['t'])[:5], ban=x['table'], viec=x['text']) for x in dong[-30:]])

        an_ninh_ca = an_ninh_tro_ly.cong_cu(hub, them)     # server/an_ninh_tro_ly.py

        def ban_dang_the_nao(hien: bool = False) -> dict:
            """Các bàn đang có khách lúc này và bữa ăn tới đâu (mới ngồi chờ nhân viên ra tiếp, đã có người tiếp và chờ món, đã lên món, đã ăn xong), bàn nào cần để ý vì chờ lâu, và việc nào chưa ai nhận.

            Args:
                hien: true để hiện luôn bảng các bàn cho chủ quán.
            """
            ans, bs = xem_lai.tra_loi_ban_luc_nay(hub)
            if hien:
                for b in bs:
                    them(b)
            return dict(tom_tat=ans, ban=[dict(ban=r['ban'], bua_an=r['buoc'], tu_luc=r['tu_luc'], can_de_y=r['luu_y'],
                                               so_nguoi=r['so_nguoi']) for r in xem_lai.ban_dang_the_nao(hub)])

        def so_sanh_ngay(ngay: str, ngay_khac: str = '') -> dict:
            """Số liệu của một ngày khác, hoặc so hai ngày với nhau, đọc từ lịch sử lâu dài; hiện luôn cho chủ quán.

            Args:
                ngay: ngày cần xem: "hôm qua", "thứ hai", "12/11" hoặc dạng YYYY-MM-DD.
                ngay_khac: ngày đem ra so. Bỏ trống thì chỉ xem một ngày; "hôm nay" để so với hôm nay.
            """
            d1 = xem_lai.doc_cac_ngay(bo_dau(ngay))
            d2 = xem_lai.doc_cac_ngay(bo_dau(ngay_khac)) if str(ngay_khac or '').strip() else []
            if not d1:
                return dict(ket_qua='Không hiểu ngày nào. Đưa "hôm qua", "thứ hai", "12/11" hoặc dạng YYYY-MM-DD.')
            ans, bs, tks = xem_lai.so_sanh_ngay(hub, d1[0], d2[0] if d2 else d1[0])
            for b in bs:
                them(b)
            return dict(tom_tat=ans, ngay=[dict(
                ngay=tk['ten'], co_du_lieu=bool(tk['n']), goi_phuc_vu=tk['call'], can_don=tk['needs_clearing'],
                khach_moi=tk['new_guest'], toc_do_phuc_vu=MUC_VI.get(nhan_xet(tk['speed'])),
                viec_nhanh=tk['speed']['fast'], viec_hoi_cham=tk['speed']['ok'], viec_cham=tk['speed']['slow'],
                viec_khong_ai_toi=tk['speed']['missed'],
                gio_ban_nhat=f"{tk['dinh']:02d}:00" if tk['dinh'] is not None else None) for tk in tks])

        cai_dat_cu = cai_dat.cong_cu(hub, them)     # cài đặt (server/cai_dat.py): chỉ chủ quán, xem CONG_CU_CHI_CHU

        ds = [so_lieu_ca, tim_su_kien, trang_thai_ban, nhan_vien_va_cham_cong, phan_tich_ca,
              hien_goi_y, hien_xep_ca, hien_chi_so, hien_bieu_do, hien_su_kien, hien_nhan_vien, hien_bang,
              xem_video, dong_thoi_gian, ban_dang_the_nao, so_sanh_ngay, an_ninh_ca,
              *cai_dat_cu]
        if self.phong is not None:
            ds += nhieu_ngay.cong_cu(hub, self.phong, them)            # cả tuần, cả tháng, nhân viên ngày cũ
            ds.append(doanh_thu_tro_ly.cong_cu(self.phong, them))     # tiền thu (server/doanh_thu_tro_ly.py)
        if che_do == 'phong':
            ds = [f for f in ds if getattr(f, '__name__', '') not in CONG_CU_CHI_CHU
                  and not getattr(f, '__name__', '').startswith('hien_')]
        return ds

    def agent(self, box, che_do='chu'):
        Agent, _, types = self.load_adk()
        return Agent(name='tro_ly_easy_fnb', model=self.model, instruction=LOI_DAN, tools=self.tools(box, che_do),
                     description='Trợ lý trả lời chủ quán về ca làm việc từ dữ liệu camera AI.',
                     generate_content_config=types.GenerateContentConfig(temperature=0.2))

    # ---------------------------------------------------------------- một lượt hỏi
    async def _hoi_adk(self, question, sid, che_do='chu'):
        _, Runner, types = self._adk
        if sid not in self._runners:
            if len(self._runners) > 200:      # demo: không để phiên cũ chiếm bộ nhớ mãi
                self._runners.clear()
            box = dict(blocks=[])
            self._runners[sid] = (Runner(app_name='easy_fnb', agent=self.agent(box, che_do),
                                         session_service=self._sessions), box)
        runner, box = self._runners[sid]
        if await self._sessions.get_session(app_name='easy_fnb', user_id='chu_quan', session_id=sid) is None:
            await self._sessions.create_session(app_name='easy_fnb', user_id='chu_quan', session_id=sid)
        box['blocks'] = blocks = []
        text = ''
        msg = types.Content(role='user', parts=[types.Part(text=question)])
        async for ev in runner.run_async(user_id='chu_quan', session_id=sid, new_message=msg):
            if ev.error_code and not (ev.content and ev.content.parts):
                raise RuntimeError(f'{ev.error_code}: {ev.error_message}')
            if ev.is_final_response() and ev.content and ev.content.parts:
                text = ''.join(p.text or '' for p in ev.content.parts if not getattr(p, 'thought', False))
        if not text.strip() and not blocks:
            raise RuntimeError('ADK không trả nội dung')
        if re.search(r'\{\s*\w+\s*\(', text):      # model viết tên công cụ vào câu thay vì gọi: coi như hỏng
            raise RuntimeError('ADK viết công cụ vào câu trả lời')
        return _go_markdown(text) or 'Số liệu ở bên dưới.', blocks

    async def _hoi_adk_thu_lai(self, cau, sid, che_do):
        """Gemini báo hết lượt trong phút (429) thì chờ một nhịp rồi thử lại đúng một lần."""
        for lan in (1, 2):
            try:
                return await (self._hoi_adk(cau, sid) if che_do == 'chu' else self._hoi_adk(cau, sid, che_do))
            except Exception as e:   # noqa: BLE001
                if lan == 2 or 'RESOURCE_EXHAUSTED' not in str(e):
                    raise
                self._runners.pop(sid, None)
                await asyncio.sleep(4)

    async def hoi(self, question, session=None, ghi_chu=None, che_do='chu'):
        """ghi_chu: dòng giao diện gửi kèm sau khi chủ quán bấm Lưu trong khối cài đặt (ví dụ "đã lưu 3 nhân viên"),
        để tác tử biết dữ liệu vừa đổi. Đường không AI bỏ qua.
        che_do='phong': câu hỏi từ phòng chat của quán (server/chat.py), không có công cụ cài đặt. Phiên phòng chat
        phải dùng mã phiên riêng (ví dụ 'phong-<ngày>') vì bộ công cụ gắn theo phiên."""
        t0 = time.perf_counter()
        sid = re.sub(r'[^A-Za-z0-9_-]', '', str(session or ''))[:64] or 'mac_dinh'
        engine, answer, blocks, ban = 'rules', None, [], False
        self._loop = asyncio.get_running_loop()
        if self.adk_wanted and self.load_adk():
            lock = self._locks.setdefault(sid, asyncio.Lock())   # một phiên chỉ chạy một lượt một lúc
            try:
                async with lock:
                    cau = f'[Hệ thống: {str(ghi_chu)[:300]}] {question}' if ghi_chu else question
                    answer, blocks = await asyncio.wait_for(self._hoi_adk_thu_lai(cau, sid, che_do), ADK_TIMEOUT_S)
                engine = 'adk'
            except Exception as e:   # noqa: BLE001  lỗi mạng, khoá sai, quá giờ: vẫn trả lời bằng rules
                log.warning('Trợ lý ADK lỗi (%s: %s), trả lời không AI', type(e).__name__, str(e)[:300])
                self._runners.pop(sid, None)
                ban = True
        if engine == 'rules':
            got = await cai_dat.tra_loi(self.hub, question) if che_do != 'phong' else None   # câu cài đặt: dựng khối, không dùng AI
            answer, blocks = got if got is not None else tra_loi_rules(self.hub, question, self.clips, self._loop, self.phong)
            if ban:      # AI có bật nhưng đang bận hoặc lỗi mạng: nói đúng như vậy
                answer = (answer or '').replace('mà AI đang tắt hoặc chưa kết nối', 'mà AI đang bận, bạn thử lại sau ít phút')
        refs, da_co = [], set()
        for b in sorted(blocks, key=lambda b: b['type'] != 'events'):      # sự kiện trước, rồi tới video
            for it in b['items'] if b['type'] in ('events', 'video') else []:
                if (it['alert_id'], it['t']) not in da_co:
                    da_co.add((it['alert_id'], it['t']))
                    refs.append(dict(alert_id=it['alert_id'], t=it['t'], table=it['table']))
        if any(b['type'] in ('ban', 'xac_nhan', 'chup') for b in blocks) and cai_dat.NOI_DA_LUU.search(answer or ''):
            answer = 'Kiểm lại rồi bấm Lưu để áp dụng.'      # chưa ai bấm Lưu: model không được nói như đã xong
        qn = bo_dau(question).strip(' ?')
        cai = cai_dat.la_cai_dat(question) or any(b['type'] in cai_dat.LOAI_KHOI for b in blocks)
        tien = self.phong is not None and (doanh_thu_tro_ly.la_hoi_tien(qn) or any(
            str(b.get('title') or '').startswith('Tiền thu') for b in blocks))
        return dict(answer=answer, blocks=blocks,
                    suggestions=[g for g in (cai_dat.GOI_Y_CAI_DAT if cai else doanh_thu_tro_ly.GOI_Y if tien else GOI_Y)
                                 if bo_dau(g).strip(' ?') != qn][:3],
                    refs=refs, engine=engine, model=self.model if engine == 'adk' else None,
                    ms=int((time.perf_counter() - t0) * 1000))


def _go_markdown(s):
    s = re.sub(r'[*_`#]+', '', s or '')
    s = re.sub(r'^\s*[-•]\s+', '', s, flags=re.M)
    return re.sub(r'\n{2,}', '\n', s).strip()


from . import goi_y  # noqa: E402  goi_y dùng các hàm ở trên, nên nạp sau cùng
from . import xem_lai  # noqa: E402  cũng vậy
from . import cai_dat  # noqa: E402  cũng vậy
from . import nhieu_ngay  # noqa: E402
from . import doanh_thu_tro_ly  # noqa: E402  cũng vậy


async def _main():
    """Thử đường ADK với Gemini thật trên một ca giả nhỏ."""
    import json
    import sys
    import tempfile
    from pathlib import Path

    from .gemini import Gemini
    from .hub import Hub
    g = Gemini()
    if not g.enabled:
        sys.exit('Chưa đặt GEMINI_API_KEY. Ví dụ (PowerShell): $env:GEMINI_API_KEY = "<khoá của bạn>"')
    with tempfile.TemporaryDirectory() as tmp:
        hub = Hub(Path(tmp), type('Tat', (), dict(enabled=False, model=None))())
        hub.staff_online('lan', +1)
        for i, (kind, table) in enumerate([('goi_phuc_vu', 'B1'), ('khach_moi', 'B2'), ('goi_phuc_vu', 'B3'),
                                           ('can_don', 'B4')]):
            aid = hub.edge_event(dict(camera='cam1', kind=kind, table=table, score=0.9))
            hub.alerts[aid]['created_at'] -= (40 - 8 * i) * 1000
            if i < 3:
                hub.ack(aid, 'lan')
        tl = TroLy(hub, g)
        for q in sys.argv[1:] or ['Hôm nay chất lượng nhân viên thế nào?', 'Bàn nào phải chờ lâu nhất?']:
            r = await tl.hoi(q, 'thu')
            print('\nHỎI:', q, f"\n[{r['engine']}, {r['model']}, {r['ms']} ms]", r['answer'])
            print('khối:', json.dumps([(b['type'], b.get('title')) for b in r['blocks']], ensure_ascii=False))


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_main())
