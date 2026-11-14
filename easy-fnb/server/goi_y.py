"""Phân tích ca và gợi ý cho chủ quán, tính thẳng từ số liệu trong `hub` (không dùng LLM, không bịa số).

  xep_ca(hub)       từng quãng giờ: bao nhiêu việc, mấy người trong ca, mấy lần khách chờ lâu, nên thêm hay bớt người.
  goi_y(hub)        danh sách điều nên đổi cho ca sau, mỗi điều kèm mã các sự kiện làm bằng chứng.
  khoi_goi_y, khoi_xep_ca   hai khối hiển thị cho trang Ca hôm nay và cho trợ lý.

Tốc độ phục vụ nói bằng chữ (nhanh, hơi chậm, chậm) như mọi màn hình khác, không nêu số giây.
"""
from collections import Counter

from .hub import CLOSED, clock, now_ms
from .tro_ly import cau_dem, khoi_bang, khoi_su_kien, muc, nhan_xet, ten_nv, viec, wait_s

ROLE_SERVE = ('serve', 'clean')


def _bo_lo(a):
    """Khách gọi mà camera không thấy nhân viên nào tới bàn (cùng cách tính với hub.report)."""
    return (a['status'] == 'done' and a['kind'] != 'needs_clearing' and not a.get('arrived_at')
            and a['done_by'] == 'camera')


def _cham(a, t):
    """Khách phải chờ lâu ở việc này: chờ tới mức chậm, hoặc không ai tới."""
    if a['status'] == 'cancelled':
        return False
    w = wait_s(a, t)
    return _bo_lo(a) or (w is not None and muc(w) == 'slow')


def _gio(ms, step_s):
    c = clock(ms)
    return c if step_s < 60 else c[:5]


def _trong_ca(hub, t0, t1, t):
    """Tên những người có mặt trong ca ở quãng [t0, t1)."""
    out = []
    for s in hub.staff:
        for ses in hub.attendance.get(s['id'], []):
            if ses['in'] < t1 and (ses['out'] or t) > t0:
                out.append(s['name'])
                break
    return out


def xep_ca(hub):
    """Mỗi quãng giờ một dòng: dict(t, label, tasks, staff, late, verdict). verdict: thieu, du, thua, vang."""
    tl = hub.report().get('timeline')
    if not tl:
        return []
    t = now_ms()
    step = tl['step_s']
    al = [a for a in viec(hub) if a['status'] != 'cancelled']
    rows = []
    for p in tl['points']:
        t0, t1 = p['t'], p['t'] + step * 1000
        if t0 > t:
            break
        mine = [a for a in al if t0 <= a['created_at'] < t1]
        late = [a for a in mine if _cham(a, t)]
        staff = _trong_ca(hub, t0, t1, t)
        if not mine:
            verdict = 'thua' if len(staff) >= 2 else 'vang'
        elif late and len(late) / len(mine) >= 0.3:
            verdict = 'thieu'
        else:
            verdict = 'du'
        rows.append(dict(t=t0, label=f'{_gio(t0, step)} đến {_gio(t1, step)}', tasks=len(mine), staff=len(staff),
                         late=len(late), verdict=verdict, ids=[a['id'] for a in late]))
    return rows


XEP_CA_VI = {'thieu': 'Thiếu người, nên thêm 1', 'du': 'Vừa đủ', 'thua': 'Vắng việc, có thể bớt người', 'vang': 'Vắng'}


def khoi_xep_ca(hub):
    rows = [r for r in xep_ca(hub) if r['tasks'] or r['staff']]
    if not any(r['tasks'] for r in rows):
        return None
    return khoi_bang('Xếp ca theo từng quãng giờ', ['Quãng giờ', 'Việc', 'Người trong ca', 'Lần khách chờ lâu', 'Gợi ý'],
                     [[r['label'], str(r['tasks']), str(r['staff']), str(r['late']), XEP_CA_VI[r['verdict']]]
                      for r in rows])


def cau_xep_ca(hub):
    """Một hai câu kết luận về xếp ca."""
    rows = xep_ca(hub)
    if not any(r['tasks'] for r in rows):
        return 'Ca chưa có việc nào nên chưa có căn cứ để gợi ý xếp ca.'
    thieu = [r for r in rows if r['verdict'] == 'thieu']
    thua = [r for r in rows if r['verdict'] == 'thua']
    dinh = max(rows, key=lambda r: r['tasks'])
    s = f"Đông nhất là quãng {dinh['label']} với {dinh['tasks']} việc, lúc đó có {dinh['staff']} người trong ca."
    if thieu:
        s += (' Nên thêm một người vào ' + ', '.join(f"quãng {r['label']}" for r in thieu[:3])
              + ': ở các quãng này khách phải chờ lâu.')
    else:
        s += ' Không quãng nào thiếu người: khách không phải chờ lâu.'
    if thua:
        s += f" Có {len(thua)} quãng vắng việc mà vẫn đủ người, có thể cho nghỉ giữa ca hoặc bớt người."
    return s


def goi_y(hub):
    """Danh sách gợi ý, điều nặng nhất đứng trước. Mỗi mục: dict(id, tone, title, text, action, ids)."""
    t = now_ms()
    al = viec(hub)
    song = [a for a in al if a['status'] != 'cancelled']
    out = []

    def them(id, tone, title, text, action, ids=()):
        out.append(dict(id=id, tone=tone, title=title, text=text, action=action, ids=list(ids)[:3]))

    # 1. quãng giờ thiếu người
    rows = xep_ca(hub)
    thieu = sorted((r for r in rows if r['verdict'] == 'thieu'), key=lambda r: -r['late'])
    if thieu:
        r = thieu[0]
        them('thieu_nguoi', 'bad', f"Thiếu người quãng {r['label']}",
             f"Quãng này có {r['tasks']} việc, {r['staff']} người trong ca, {r['late']} lần khách phải chờ lâu.",
             'Ca sau xếp thêm một người phục vụ vào quãng này.', r['ids'])

    # 2. khách gọi mà không ai tới
    lo = [a for a in song if _bo_lo(a)]
    if lo:
        them('khong_ai_toi', 'bad', f'{len(lo)} lần khách gọi mà không ai tới bàn',
             'Camera không thấy nhân viên nào tới các bàn này sau khi khách gọi.',
             'Nhắc cả ca: nghe báo trong tai nghe thì tới bàn ngay, không chờ người khác.', [a['id'] for a in lo])

    # 3. bàn hay bị chờ
    theo_ban = {}
    for a in song:
        if a['table']:
            theo_ban.setdefault(a['table'], []).append(a)
    te = [(sum(1 for a in xs if _cham(a, t)), len(xs), tb, xs) for tb, xs in theo_ban.items()]
    te = [x for x in te if x[0] >= 2]
    if te:
        n, tong, tb, xs = max(te, key=lambda x: (x[0], x[0] / x[1]))
        them('ban_bi_cho', 'warn', f'Bàn {tb} hay phải chờ',
             f'{n} trên {tong} lần bàn {tb} cần phục vụ thì khách phải chờ lâu.',
             f'Phân một người đứng gần bàn {tb}, hoặc dời vị trí chờ của nhân viên về phía khu này.',
             [a['id'] for a in xs if _cham(a, t)])

    # 4. dọn bàn chậm
    don = [a for a in song if a['kind'] == 'needs_clearing']
    don_cham = []
    for a in don:
        w = (a['done_at'] - a['created_at']) / 1000 if a['done_at'] else (t - a['created_at']) / 1000
        if muc(w) == 'slow':
            don_cham.append(a)
    if don_cham:
        them('don_cham', 'warn', f'{len(don_cham)} trên {len(don)} lần bàn bẩn phải chờ dọn lâu',
             'Bàn chưa dọn thì khách mới không có chỗ ngồi, quán mất lượt khách lúc đông.',
             'Giao hẳn việc dọn bàn cho một người trong giờ đông.', [a['id'] for a in don_cham])

    # 5. việc dồn vào một người
    per = [s for s in hub.report()['per_staff'] if hub.attendance.get(s['id'])]
    tong = sum(s['acked'] for s in per)
    if len(per) >= 2 and tong >= 4:
        nhieu, it = max(per, key=lambda s: s['acked']), min(per, key=lambda s: s['acked'])
        if nhieu['acked'] / tong >= 0.6:
            them('lech_tai', 'warn', f"Việc dồn vào {nhieu['name']}",
                 f"{nhieu['name']} nhận {nhieu['acked']} trên {tong} việc của ca, {it['name']} nhận {it['acked']}.",
                 'Chia lại khu vực phụ trách để việc đều hơn giữa các nhân viên.',
                 [a['id'] for a in song if a['acked_by'] == nhieu['id']][-3:])

    # 6. bàn hay báo nhầm
    huy = Counter(a['table'] for a in al if a['status'] == 'cancelled' and a['table'])
    if huy and huy.most_common(1)[0][1] >= 2:
        tb, n = huy.most_common(1)[0]
        them('bao_nham', 'warn', f'Bàn {tb} bị báo nhầm {n} lần',
             'Vùng bàn có thể đang lấn sang lối đi hoặc bàn bên cạnh nên camera nhận nhầm.',
             f'Vào Cài đặt, mục Vùng bàn, vẽ lại vùng của bàn {tb}.',
             [a['id'] for a in al if a['status'] == 'cancelled' and a['table'] == tb])

    # 7. khách nhìn quanh tìm nhân viên
    nhin = Counter(e['table'] for e in hub.log if e['kind'] == 'looking' and e['table'])
    if sum(nhin.values()) >= 2:
        tb, n = nhin.most_common(1)[0]
        them('nhin_quanh', 'warn', f'Khách nhìn quanh tìm nhân viên {sum(nhin.values())} lần',
             f'Nhiều nhất ở bàn {tb} ({n} lần). Khách cần hỗ trợ nhưng chưa giơ tay gọi.',
             'Nhắc nhân viên chủ động ghé bàn khi thấy khách ngẩng lên nhìn quanh.')

    # 8. việc còn tồn lúc này
    mo = [a for a in song if a['status'] not in CLOSED and not a['acked_by'] and muc(wait_s(a, t) or 0) != 'fast']
    if mo:
        them('dang_ton', 'bad', f'{len(mo)} việc đang chờ lâu mà chưa ai nhận',
             'Khách ở các bàn này vẫn đang chờ.', 'Giao việc ngay cho người đang rảnh.', [a['id'] for a in mo])

    # 9. người đáng khen
    gioi = [s for s in per if s['fast'] + s['ok'] + s['slow'] >= 3
            and nhan_xet(dict(fast=s['fast'], ok=s['ok'], slow=s['slow'])) == 'fast']
    if gioi:
        s = max(gioi, key=lambda s: s['fast'])
        them('khen', 'good', f"{s['name']} phục vụ nhanh", f"{s['name']} nhận {cau_dem(s, 'việc')}.",
             f"Khen {s['name']} trước cả ca để mọi người làm theo.",
             [a['id'] for a in song if a['acked_by'] == s['id']][-2:])

    if not out and song:
        them('em', 'good', 'Ca chạy êm', 'Không có quãng nào thiếu người, không bàn nào bị chờ lâu.',
             'Giữ cách xếp ca này cho ca sau.')
    return out


def khoi_goi_y(hub, title='Gợi ý cho ca sau', gioi_han=5):
    """Khối hiển thị: mỗi gợi ý kèm tối đa 3 sự kiện có ảnh làm bằng chứng."""
    items = []
    for g in goi_y(hub)[:gioi_han]:
        ev = khoi_su_kien(hub, g['ids']) if g['ids'] else None
        items.append(dict(id=g['id'], tone=g['tone'], title=g['title'], text=g['text'], action=g['action'],
                          events=ev['items'] if ev else []))
    if not items:
        return None
    return dict(type='insights', title=title, items=items)


def du_lieu(hub):
    """Bản gọn cho tác tử đọc: gợi ý và bảng xếp ca, không kèm ảnh."""
    return dict(goi_y=[dict(van_de=g['title'], chi_tiet=g['text'], nen_lam=g['action'], ma_su_kien=g['ids'])
                       for g in goi_y(hub)],
                xep_ca=[dict(quang_gio=r['label'], so_viec=r['tasks'], nguoi_trong_ca=r['staff'],
                             lan_khach_cho_lau=r['late'], nhan_xet=XEP_CA_VI[r['verdict']]) for r in xep_ca(hub)],
                ai_trong_ca=[ten_nv(hub, s['id']) for s in hub.staff if hub.online[s['id']] > 0])
