"""Phát hiện khách ngồi nhìn quanh tìm nhân viên (chưa giơ tay), chỉ từ khung xương.

Mỗi khung, mỗi khách ngồi yên: đầu quay sang bên nào trong ảnh (trái / thẳng / phải), có ngẩng không,
bên đó có nhân viên không, bên đó có người cùng bàn không (đang nói chuyện thì không tính).
Giữ ~6 giây gần nhất của từng người rồi chấm điểm theo 2 đường:
  A. nhìn về phía nhân viên phần lớn thời gian
  B. quay đầu qua lại trái/phải nhiều lần mà không phải về phía người cùng bàn
Đây là tín hiệu mềm: chỉ để nhắc trên màn hình quản lý, không giao việc, không đọc loa.
Ngưỡng đặt theo suy luận hình học, CHƯA chỉnh trên clip quán thật.
"""
from collections import defaultdict, deque

import numpy as np

NOSE, LEAR, REAR, LSH, RSH = 0, 3, 4, 5, 6


def huong_dau(kp, kc, box, th=0.35):
    """Trả (yaw, cui). yaw: -1 quay hẳn sang trái ảnh, 0 nhìn thẳng máy quay, +1 sang phải ảnh; None = không rõ
    (quay lưng, mất mũi). cui: mũi thấp hơn đường tai bao nhiêu lần bề ngang đầu (lớn = đang cúi)."""
    if kc[NOSE] < th:
        return None, None
    le, re = kc[LEAR] >= th, kc[REAR] >= th
    if not (le or re):
        return None, None
    nx, ny = kp[NOSE]
    vai = abs(kp[LSH][0] - kp[RSH][0]) if kc[LSH] >= th and kc[RSH] >= th else 0.0
    co = max(0.3 * vai, 0.08 * (box[3] - box[1]), 1.0)          # cỡ đầu ước lượng, tránh chia cho số quá nhỏ
    if le and re:
        mx, my = (kp[LEAR][0] + kp[REAR][0]) / 2, (kp[LEAR][1] + kp[REAR][1]) / 2
        nua = max(abs(kp[LEAR][0] - kp[REAR][0]) / 2, 0.35 * co)
        return float(np.clip((nx - mx) / nua, -1.5, 1.5)), float((ny - my) / max(2 * nua, co))
    ex, ey = kp[LEAR] if le else kp[REAR]                       # chỉ thấy một tai: đang quay nghiêng
    return (1.0 if nx > ex else -1.0), float((ny - ey) / co)


class NhinQuanh:
    def __init__(self, win=6.0, min_span=3.0, cooldown=30.0, th=0.6, yaw_on=0.45, yaw_off=0.25, cui_max=0.6):
        self.win, self.min_span, self.cooldown, self.th = win, min_span, cooldown, th
        self.yaw_on, self.yaw_off, self.cui_max = yaw_on, yaw_off, cui_max
        self.q = defaultdict(deque)      # id -> (t, bên, hướng về nhân viên, ngẩng)
        self.ben = {}                    # bên đang giữ của từng người (có trễ để khỏi nhấp nháy)
        self.last = {}                   # lần báo gần nhất
        self.diem = {}                   # điểm hiện tại, để vẽ nhãn

    def clear(self):
        self.q.clear(), self.ben.clear(), self.last.clear(), self.diem.clear()

    def _ben(self, tid, yaw):
        b = self.ben.get(tid, 0)
        if abs(yaw) >= self.yaw_on:
            b = 1 if yaw > 0 else -1
        elif abs(yaw) <= self.yaw_off:
            b = 0
        self.ben[tid] = b
        return b

    def update(self, t, persons):
        """persons: dict có id, box, kp, kc, staff, walking, calling, table. Trả danh sách (person, điểm, lý do)
        vừa vượt ngưỡng ở khung này (đã tính thời gian nghỉ giữa hai lần báo)."""
        out, con = [], set()
        tam = {p['id']: ((p['box'][0] + p['box'][2]) / 2, (p['box'][1] + p['box'][3]) / 2) for p in persons}
        for p in persons:
            tid = p['id']
            con.add(tid)
            if p['staff'] or p['walking'] or p['calling']:
                self.q[tid].clear()
                self.diem[tid] = 0.0
                continue
            yaw, cui = huong_dau(p['kp'], p['kc'], p['box'])
            q = self.q[tid]
            if yaw is None:
                q.append((t, None, False, False))
            else:
                ben = self._ben(tid, yaw)
                x, y = tam[tid]
                w = p['box'][2] - p['box'][0]
                phia = lambda o: ben and (tam[o['id']][0] - x) * ben > 0.5 * w     # người kia nằm bên mình đang quay
                nv = any(o['staff'] and phia(o) for o in persons if o['id'] != tid)
                # người cùng bàn (hoặc ngồi sát, khi chưa vẽ bàn) ở bên đó: coi là đang nói chuyện
                ban = any(not o['staff'] and o['id'] != tid and phia(o) and
                          (o['table'] is p['table'] if p['table'] is not None
                           else abs(tam[o['id']][0] - x) < 3 * w and abs(tam[o['id']][1] - y) < 1.5 * w)
                          for o in persons)
                q.append((t, 0 if ban and not nv else ben, nv, cui <= self.cui_max))
            while q and t - q[0][0] > self.win:
                q.popleft()
            d, ly_do = self._cham(q)
            self.diem[tid] = d
            if d >= self.th and t - self.last.get(tid, -1e9) > self.cooldown:
                self.last[tid] = t
                out.append((p, d, ly_do))
        for tid in [k for k in self.q if k not in con]:              # người đã ra khỏi khung
            del self.q[tid]
            self.ben.pop(tid, None), self.diem.pop(tid, None)
        return out

    def _cham(self, q):
        ro = [s for s in q if s[1] is not None]
        if len(q) < 5 or q[-1][0] - q[0][0] < self.min_span or len(ro) < 0.6 * len(q):
            return 0.0, ''
        ngang = float(np.mean([s[3] for s in ro]))
        if ngang < 0.6:                                              # cúi nhiều: ăn, xem điện thoại
            return 0.0, ''
        ve_nv = float(np.mean([s[2] for s in ro]))                   # A: bao nhiêu phần thời gian hướng về nhân viên
        a = min(1.0, ve_nv / 0.5)
        # B: số lần đổi bên trái <-> phải, chỉ tính lượt quay giữ được từ 0,3 giây
        luot, bd = [], None
        for s in ro + [(ro[-1][0] + 1, 2, False, False)]:
            if bd is None or s[1] != bd[1]:
                if bd is not None and bd[1] and truoc - bd[0] >= 0.3 and (not luot or luot[-1] != bd[1]):
                    luot.append(bd[1])
                bd = s
            truoc = s[0]
        b = min(1.0, max(0, len(luot) - 1) / 2)                      # trái-phải-trái (2 lần đổi) là đủ điểm
        if a >= b:
            return a, f'nhìn về phía nhân viên {ve_nv:.0%} thời gian'
        return b, f'quay đầu qua lại {len(luot)} lượt'
