"""Đối chiếu thanh toán (ảnh chuyển khoản, hoá đơn) với lượt khách camera thấy.

Lượt khách dựng từ dòng thời gian (kind `stage`): bàn chuyển sang `seated` mở lượt, `left` đóng lượt. Số khách lấy
lớn nhất trong các dòng `table` của bàn trong khoảng đó. Khoá lượt là "<bàn>@<giờ ngồi ms>" (không dùng số `seat`
vì số này đếm lại sau mỗi lần máy chủ khởi động).

Gắn thanh toán vào lượt (theo thứ tự):
1. Người gắn tay luôn thắng.
2. Có bàn: lượt của bàn đó mà [giờ ngồi - 5 phút, giờ rời + 15 phút] chứa giờ thanh toán; nhiều lượt thì lấy lượt
   có giờ rời gần nhất.
3. Không có bàn: chỉ gắn khi đúng một lượt rời trong ±10 phút và lượt đó chưa có thanh toán.
"""
from datetime import datetime

from .timeline import DOI_NGAY_H, VN

BEFORE_S = 5 * 60
AFTER_S = 15 * 60
NO_TABLE_S = 10 * 60
VISIT_MIN_S = 10 * 60       # lượt ngắn hơn thế này không đòi thanh toán (đứng lên lấy đồ, khách hỏi đường)
GRACE_S = 15 * 60           # khách rời bao lâu mới coi là "chưa thấy thanh toán"


def day_range(day):
    d = datetime.strptime(day, '%Y-%m-%d').replace(tzinfo=VN)
    t0 = d.timestamp() + DOI_NGAY_H * 3600      # ngày của quán bắt đầu lúc 4 giờ sáng
    return t0, t0 + 86400


SPAN_S = 6 * 3600          # đọc thêm chừng này trước 0 giờ: khách ngồi từ tối hôm trước, rời sau nửa đêm


def visits(timeline, day, now_s):
    """Các lượt khách trong ngày, cũ trước: dict(key, table, start, end (None khi còn ngồi), people, finished).
    Lượt ngồi từ trước 0 giờ mà rời (hoặc còn ngồi) sau 0 giờ cũng tính cho ngày này."""
    t0, t1 = day_range(day)
    rows = timeline.query(since=t0 - SPAN_S, until=t1, kinds=['stage', 'table'], limit=5000)
    open_, out, people = {}, [], {}
    for r in rows:
        table = r.get('table')
        if not table:
            continue
        d = r.get('data') or {}
        if r['kind'] == 'table':
            people[table] = int(d.get('people') or 0)
            v = open_.get(table)
            if v:
                v['people'] = max(v['people'], people[table])
            continue
        st = d.get('stage')
        if st == 'seated':
            if table in open_:          # lượt cũ chưa đóng (máy chủ khởi động lại giữa bữa): đóng ở đây
                open_.pop(table)['end'] = r['ts']
            v = dict(key=f"{table}@{int(r['ts'] * 1000)}", table=table, start=r['ts'], end=None,
                     people=people.get(table, 0), finished=False)
            open_[table] = v
            out.append(v)
        elif table in open_:
            v = open_[table]
            if st == 'finished':
                v['finished'] = True
            elif st == 'left':
                v['end'] = r['ts']
                open_.pop(table)
    return [v for v in out if v['start'] >= t0 or v['end'] is None or v['end'] >= t0]


def _pay_ts(p):
    """Giờ của thanh toán: giờ in trên ảnh (cùng ngày với lúc gửi), không có thì lúc gửi."""
    ts = p['ts'] / 1000
    hhmm = p.get('paid_at') or ''
    try:
        h, m = (int(x) for x in hhmm.split(':')[:2])
        sent = datetime.fromtimestamp(ts, VN)
        t = sent.replace(hour=h, minute=m, second=0, microsecond=0).timestamp()
        if abs(t - ts) <= 6 * 3600:     # giờ đọc sai hẳn (khác hơn 6 tiếng) thì bỏ, dùng lúc gửi
            return t
    except (ValueError, TypeError):
        pass
    return ts


def match(payments, vs, now_s):
    """Gắn từng thanh toán (chưa huỷ) vào một lượt. Trả {payment_id: visit_key | None}."""
    by_key = {v['key']: v for v in vs}
    got, used = {}, set()
    live = [p for p in payments if p.get('status') != 'void']
    for p in live:
        if p.get('visit') and p.get('visit_by') not in (None, 'auto') and p['visit'] in by_key:
            got[p['id']] = p['visit']
            used.add(p['visit'])
    for p in live:
        if p['id'] in got or not p.get('table'):
            continue
        t = _pay_ts(p)
        best = None
        for v in vs:
            if v['table'] != p['table']:
                continue
            end = v['end'] if v['end'] is not None else now_s
            if v['start'] - BEFORE_S <= t <= end + AFTER_S:
                if best is None or abs(end - t) < abs((best['end'] or now_s) - t):
                    best = v
        got[p['id']] = best['key'] if best else None
        if best:
            used.add(best['key'])
    for p in live:
        if p['id'] in got:
            continue
        t = _pay_ts(p)
        near = [v for v in vs if v['end'] is not None and abs(v['end'] - t) <= NO_TABLE_S and v['key'] not in used]
        got[p['id']] = near[0]['key'] if len(near) == 1 else None
        if len(near) == 1:
            used.add(near[0]['key'])
    return got


def hhmm(ts):
    return datetime.fromtimestamp(ts, VN).strftime('%H:%M')


def review(payments, vs, got, notes, now_s):
    """Danh sách cần chủ xem lại."""
    out = []
    paid = set(k for k in got.values() if k)
    for v in vs:
        if v['key'] in paid or v['key'] in notes or v['end'] is None:
            continue
        if v['end'] - v['start'] < VISIT_MIN_S or now_s - v['end'] < GRACE_S:
            continue
        khach = f", {v['people']} khách" if v['people'] else ''
        out.append(dict(kind='no_payment', visit=v['key'], table=v['table'], start=hhmm(v['start']),
                        end=hhmm(v['end']), people=v['people'],
                        text=f"Bàn {v['table']}, {hhmm(v['start'])} đến {hhmm(v['end'])}{khach}, chưa thấy thanh toán"))
    for p in payments:
        if p.get('status') == 'void':
            continue
        if p.get('table') and not got.get(p['id']):
            out.append(dict(kind='no_visit', payment_id=p['id'], table=p['table'],
                            text=f"{money(p.get('amount'))} bàn {p['table']}: camera không thấy khách (có thể là mang về)"))
    return out


def money(n):
    if n is None:
        return 'chưa rõ số tiền'
    return f"{int(n):,}".replace(',', '.') + ' đ'
