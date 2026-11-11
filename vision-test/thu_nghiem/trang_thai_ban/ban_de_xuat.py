"""Bản đề xuất thay class Table trong easyfnb_test.py (chưa áp dụng vào pipeline).

Giống Table cũ ở phần có khách (trung bình trượt trong win, ngưỡng 0,8 / 0,2), thêm:
- độ bẩn lọc mũ (EMA, tau = 0,5 win) và có trễ: thành bẩn khi >= 0,5, chỉ thành sạch khi < 0,35;
- khách mới phải có mặt liên tục GIU_VAO giây, khách rời phải vắng liên tục GIU_RA giây
  (trong lúc chờ, bàn vẫn hiện "có khách": người bị che vài giây không sinh khach_roi + khach_moi);
- đã dọn chỉ báo khi bàn sạch liên tục GIU_SACH giây.
Thời gian giữ tính bằng giây ngoài đời; toc = số giây ngoài đời trong 1 giây video (1 với camera thật,
~30 với clip 01 time-lapse).
"""
import math
from collections import deque

import numpy as np


class Table:
    GIU_VAO, GIU_RA, GIU_SACH = 1.0, 5.0, 3.0   # giây ngoài đời
    BAN, SACH, TAU = 0.5, 0.35, 0.5              # ngưỡng bẩn vào / ra, hằng số EMA (bội số của win)

    def __init__(self, name, pts, toc=1.0):
        self.name = name
        self.poly = np.array(pts, np.float32)
        self.toc = toc
        self.state = None
        self.people = deque()  # (t, số người ngồi)
        self.n_now = 0
        self.dirty_now = None  # quan sát độ bẩn gần nhất
        self.dirty_f = None    # độ bẩn đã lọc
        self.t_dirty = None
        self.is_dirty = False
        self.t_vao = self.t_ra = self.t_sach = None

    def update(self, t, n, dirty_obs, win):
        """Cập nhật một khung hình, trả về danh sách (loại sự kiện, chi tiết)."""
        self.n_now = n
        self.people.append((t, n))
        while self.people and self.people[0][0] < t - win:
            self.people.popleft()
        if dirty_obs is not None:
            self.dirty_now = dirty_obs
            if self.dirty_f is None:
                self.dirty_f = dirty_obs
            else:
                a = 1 - math.exp(-(t - self.t_dirty) / (self.TAU * win))
                self.dirty_f += a * (dirty_obs - self.dirty_f)
            self.t_dirty = t
            if self.is_dirty and self.dirty_f < self.SACH:
                self.is_dirty = False
            elif not self.is_dirty and self.dirty_f >= self.BAN:
                self.is_dirty = True
        if t - self.people[0][0] < 0.9 * win:
            return []  # chưa đủ một cửa sổ để kết luận

        occ = np.mean([k > 0 for _, k in self.people])
        dirty = self.is_dirty
        heads = int(np.median([k for _, k in self.people if k > 0] or [0]))
        held = lambda t0, s: t - t0 >= s / self.toc - 1e-9
        ev = []
        if self.state is None:  # đầu clip: chỉ ghi nhận trạng thái
            self.state = 'co_khach' if occ >= 0.5 else ('can_don' if dirty else 'trong')
            if self.state == 'can_don':
                ev.append(('can_don', 'đầu clip đã có đồ trên bàn, không có khách'))
            return ev
        if self.state != 'co_khach':
            if occ >= 0.8:
                self.t_vao = t if self.t_vao is None else self.t_vao
                if held(self.t_vao, self.GIU_VAO):
                    self.state = 'co_khach'
                    self.t_vao = self.t_ra = self.t_sach = None
                    return [('khach_moi', f'{heads} người')]
            else:
                self.t_vao = None
        if self.state == 'co_khach':
            if occ <= 0.2:
                self.t_ra = t if self.t_ra is None else self.t_ra
                if held(self.t_ra, self.GIU_RA):
                    ev.append(('khach_roi', ''))
                    self.state = 'can_don' if dirty else 'trong'
                    self.t_ra = self.t_sach = None
                    if dirty:
                        ev.append(('can_don', 'còn đồ trên bàn sau khi khách đi'))
            else:
                self.t_ra = None
        elif self.state == 'can_don':
            if not dirty and occ <= 0.2:
                self.t_sach = t if self.t_sach is None else self.t_sach
                if held(self.t_sach, self.GIU_SACH):
                    self.state = 'trong'
                    self.t_sach = None
                    ev.append(('da_don', ''))
            else:
                self.t_sach = None
        return ev
