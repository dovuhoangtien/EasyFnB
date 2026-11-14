"""Trợ lý và an ninh: đọc cảnh báo an ninh (ca hiện tại trong RAM, hoặc ngày cũ trong dòng thời gian) và dựng câu
trả lời kèm khối sự kiện (ảnh, clip). tro_ly.py gắn vào bằng vài dòng; phòng chat dùng lại `lich_su()`.

Import tro_ly bên trong hàm để không vòng lặp import (tro_ly import module này).
"""
from .an_ninh import SEC_KINDS


def an_ninh(hub):
    """Cảnh báo an ninh của ca hiện tại, mới trước."""
    return [a for a in reversed(list(hub.alerts.values())) if a.get('group') == 'security']


def cau_an_ninh(hub, a):
    from .tro_ly import ten_nv
    s = hub._label(a, True)
    if a['status'] == 'cancelled':
        return f"{s}; đã bỏ qua: {a['cancel_reason'] or 'báo nhầm'}"
    s += {'confirmed': f', {hub.ten} đã xác nhận', 'unverified': ', chưa xác minh'}.get(a['verify']['state'], '')
    if a['status'] == 'done':
        return f"{s}; {ten_nv(hub, a['done_by']) or 'đã có người'} đã xem"
    return f'{s}; chưa ai bấm đã biết'


def tra_loi_an_ninh(hub):
    """(câu trả lời, các khối) cho câu hỏi về an ninh trong ca."""
    from .tro_ly import khoi_su_kien
    al = an_ninh(hub)
    if not al:
        return ('Ca này chưa có cảnh báo an ninh nào: không ai lấy đồ của khách, không ai vào khu cấm, '
                'không có người ngoài giờ.'), []
    that = [a for a in al if a['status'] != 'cancelled']
    head = f'Ca này có {len(that)} cảnh báo an ninh' + (
        f' (và {len(al) - len(that)} lần báo nhầm đã bỏ qua)' if len(al) > len(that) else '') + '. '
    ans = head + ' '.join(cau_an_ninh(hub, a) + '.' for a in (that or al)[:3])
    b = khoi_su_kien(hub, [a['id'] for a in (that or al)[:6]], title='An ninh')
    return ans, [b] if b else []


def lich_su(timeline, since=None, until=None, limit=200):
    """Cảnh báo an ninh đọc từ dòng thời gian (còn sau khi khởi động lại hay bắt đầu ca mới), cũ trước:
    [dict(ts, alert_id, kind, camera, table, text, status)]. `text` là câu nhật ký lúc báo; `status` là kết cục
    cuối cùng đã ghi (open, done, cancelled)."""
    rows = timeline.query(since=since, until=until, kinds=['alert_created', 'alert_done', 'alert_cancelled', 'log'],
                          limit=5000)
    out, by_id, texts = [], {}, {}
    for r in rows:      # câu nhật ký được ghi ngay trước dòng alert_created, nên gom trước
        if r['kind'] == 'log' and r.get('alert_id') and r['alert_id'] not in texts:
            texts[r['alert_id']] = r['text']
    for r in rows:
        aid, k = r.get('alert_id'), r['kind']
        if k == 'alert_created' and (r['data'] or {}).get('alert_kind') in SEC_KINDS:
            by_id[aid] = dict(ts=r['ts'], alert_id=aid, kind=r['data']['alert_kind'], camera=r['camera'],
                              table=r['table'], text=texts.get(aid), status='open')
            out.append(by_id[aid])
        elif aid in by_id:
            if k == 'alert_done':
                by_id[aid]['status'] = 'done'
            elif k == 'alert_cancelled':
                by_id[aid]['status'] = 'cancelled'
    return out[-limit:]


def cong_cu(hub, them):
    """Công cụ ADK `an_ninh` cho TroLy.tools(). `them` là hàm thêm khối hiển thị của phiên đó."""
    from .hub import clock

    def an_ninh_ca() -> dict:
        """Cảnh báo an ninh của ca (có người lạ cầm đồ của khách, người không phải nhân viên vào quầy hay kho, có người trong quán ngoài giờ), kèm ảnh và video; hiện luôn cho chủ quán."""
        ans, bs = tra_loi_an_ninh(hub)
        for b in bs:
            them(b)
        return dict(tom_tat=ans, canh_bao=[dict(gio=clock(a['created_at'])[:5], noi_dung=cau_an_ninh(hub, a))
                                           for a in an_ninh(hub)[:10]])
    an_ninh_ca.__name__ = 'an_ninh'
    return an_ninh_ca
