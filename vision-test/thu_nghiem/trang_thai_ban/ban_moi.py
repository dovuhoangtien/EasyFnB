"""Bộ trạng thái bàn có thể bật/tắt từng ý tưởng, để so với class Table cũ.

Với tham số mặc định, BanMoi cho ra đúng từng khung như Table cũ (đã kiểm tra trong bien_the.py).

Hai loại hằng số thời gian:
- Lọc nhiễu (tau_khach, tau_ban): tính theo bội số của `win` (cửa sổ xác nhận từng clip, mặc định 1 s,
  clip 01 time-lapse 0,5 s), vì nhiễu là nhiễu từng khung hình.
- Hành vi (giu_vao, giu_ra, giu_sach, giu_sach_lau): tính bằng GIÂY NGOÀI ĐỜI, chia cho `toc`
  (số giây ngoài đời trong 1 giây video: 1 với video thường, ~30-60 với clip 01 time-lapse).
"""
import math

import numpy as np
from collections import deque

MAC_DINH = dict(
    loc_khach='cua_so',  # 'cua_so': trung bình trượt trong win (như cũ); 'ema': trung bình mũ
    tau_khach=0.5,       # hằng số thời gian EMA có khách, bội số của win
    khach_vao=0.8,       # tỉ lệ có khách (đã lọc) >= ngưỡng này: coi là có khách
    khach_ra=0.2,        # <= ngưỡng này: coi là không còn khách
    loc_ban='cua_so',    # như trên, cho độ bẩn; thêm 'trung_vi': trung vị trượt trong win
    tau_ban=0.5,
    ban_ban=0.5,         # độ bẩn đã lọc >= ngưỡng này: bàn bẩn
    ban_sach=0.5,        # bàn đang bẩn chỉ thành sạch khi độ bẩn < ngưỡng này (trễ: ban_sach < ban_ban)
    giu_vao=0.0,         # giây ngoài đời phải có khách liên tục mới báo khách mới
    giu_ra=0.0,          # giây ngoài đời phải vắng liên tục mới báo khách rời
    giu_sach=0.0,        # giây ngoài đời bàn phải sạch liên tục mới báo đã dọn
    che=None,            # bàn bị khung người che > tỉ lệ này: bỏ quan sát độ bẩn khung đó (giữ nguyên)
    can_ghe=None,        # None: không xét; 'ai_do': phải có người tới bàn lúc cần dọn; 'nhan_vien': phải là nhân viên
    giu_sach_lau=None,   # nếu can_ghe mà không thấy ai tới: vẫn báo đã dọn khi sạch liên tục chừng này giây (None: không bao giờ)
    xet_sau_roi=False,   # True: quyết định cần dọn/trống bằng quan sát lúc đang chờ xác nhận khách rời (bàn không bị che)
    toc=1.0,             # giây ngoài đời / giây video
)


class BanMoi:
    def __init__(self, name, pts, **p):
        self.name = name
        self.poly = np.array(pts, np.float32)
        self.p = dict(MAC_DINH, **p)
        self.state = None
        self.people = deque()
        self.dirty = deque()
        self.n_now = 0
        self.dirty_now = None
        self.t0 = None
        self.occ_f = None      # EMA có khách
        self.dirty_f = None    # EMA độ bẩn
        self.t_occ = self.t_dirty = None
        self.is_dirty = False  # độ bẩn sau trễ
        self.t_vao = None      # lúc bắt đầu thấy đủ khách (chờ xác nhận khách mới)
        self.t_ra = None       # lúc bắt đầu vắng (chờ xác nhận khách rời)
        self.t_sach = None     # lúc bắt đầu sạch (chờ xác nhận đã dọn)
        self.visited = False
        self.sau_roi = []      # quan sát độ bẩn trong lúc chờ xác nhận khách rời

    # ---- lọc
    def _filter_occ(self, t, n, win):
        p = self.p
        self.people.append((t, n))
        while self.people and self.people[0][0] < t - win:
            self.people.popleft()
        x = float(n > 0)
        if p['loc_khach'] == 'ema':
            if self.occ_f is None:
                self.occ_f = x
            else:
                a = 1 - math.exp(-(t - self.t_occ) / (p['tau_khach'] * win))
                self.occ_f += a * (x - self.occ_f)
            self.t_occ = t
            return self.occ_f
        return float(np.mean([k > 0 for _, k in self.people]))

    def _filter_dirty(self, t, obs, win):
        p = self.p
        if obs is not None:
            self.dirty.append((t, obs))
            self.dirty_now = obs
        while self.dirty and self.dirty[0][0] < t - win:
            self.dirty.popleft()
        if p['loc_ban'] == 'ema':
            if obs is not None:
                if self.dirty_f is None:
                    self.dirty_f = obs
                else:
                    a = 1 - math.exp(-(t - self.t_dirty) / (p['tau_ban'] * win))
                    self.dirty_f += a * (obs - self.dirty_f)
                self.t_dirty = t
            return self.dirty_f
        if not self.dirty:
            return None
        vals = [v for _, v in self.dirty]
        return float(np.median(vals) if p['loc_ban'] == 'trung_vi' else np.mean(vals))

    def update(self, t, n, dirty_obs, win, cover=0.0, visitors=None):
        p = self.p
        toc = p['toc']
        self.n_now = n
        if self.t0 is None:
            self.t0 = t
        if p['che'] is not None and cover > p['che']:
            dirty_obs = None  # bàn bị che: không bỏ phiếu, giữ nguyên độ bẩn
        if dirty_obs is not None and self.t_ra is not None:
            self.sau_roi.append(dirty_obs)
        occ = self._filter_occ(t, n, win)
        d = self._filter_dirty(t, dirty_obs, win)
        if d is not None:
            if self.is_dirty and d < p['ban_sach']:
                self.is_dirty = False
            elif not self.is_dirty and d >= p['ban_ban']:
                self.is_dirty = True
        elif p['loc_ban'] == 'cua_so' and p['che'] is None:
            self.is_dirty = False  # như bản cũ: không có quan sát nào trong cửa sổ thì coi là sạch
        if t - self.people[0][0] < 0.9 * win:
            return []
        dirty = self.is_dirty
        heads = int(np.median([k for _, k in self.people if k > 0] or [0]))
        ev = []
        if self.state is None:
            self.state = 'co_khach' if occ >= 0.5 else ('can_don' if dirty else 'trong')
            if self.state == 'can_don':
                ev.append(('can_don', 'đầu clip đã có đồ trên bàn, không có khách'))
            return ev

        # ---- có khách vào (mọi trạng thái khác co_khach)
        if self.state != 'co_khach':
            if occ >= p['khach_vao']:
                if self.t_vao is None:
                    self.t_vao = t
                if t - self.t_vao >= p['giu_vao'] / toc - 1e-9:
                    self.state = 'co_khach'
                    self.t_vao = self.t_ra = self.t_sach = None
                    ev.append(('khach_moi', f'{heads} người'))
                    return ev
            else:
                self.t_vao = None
        # ---- khách rời
        if self.state == 'co_khach':
            if occ <= p['khach_ra']:
                if self.t_ra is None:
                    self.t_ra = t
                    self.sau_roi = [dirty_obs] if dirty_obs is not None else []
                if t - self.t_ra >= p['giu_ra'] / toc - 1e-9:
                    if p['xet_sau_roi'] and self.sau_roi:
                        dirty = float(np.mean(self.sau_roi)) >= p['ban_ban']
                        self.is_dirty = dirty
                        if p['loc_ban'] == 'ema':
                            self.dirty_f = float(np.mean(self.sau_roi))
                    ev.append(('khach_roi', ''))
                    self.state = 'can_don' if dirty else 'trong'
                    self.t_ra, self.t_sach, self.visited = None, None, False
                    if dirty:
                        ev.append(('can_don', 'còn đồ trên bàn sau khi khách đi'))
            else:
                self.t_ra = None
            return ev
        # ---- cần dọn -> đã dọn
        if self.state == 'can_don':
            if visitors:
                if p['can_ghe'] == 'ai_do' or (p['can_ghe'] == 'nhan_vien' and any(s for _, s, _ in visitors)):
                    self.visited = True
            if not dirty and occ <= p['khach_ra']:
                if self.t_sach is None:
                    self.t_sach = t
                held = t - self.t_sach
                ok = held >= p['giu_sach'] / toc - 1e-9
                if p['can_ghe'] and not self.visited:
                    ok = p['giu_sach_lau'] is not None and held >= p['giu_sach_lau'] / toc - 1e-9
                if ok:
                    self.state = 'trong'
                    self.t_sach = None
                    ev.append(('da_don', ''))
            else:
                self.t_sach = None
        return ev
