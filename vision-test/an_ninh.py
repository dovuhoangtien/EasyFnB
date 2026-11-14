"""An ninh, chống trộm tại camera (spec docs/superpowers/specs/2026-11-13-an-ninh-design.md, mục 4-5).

Logic thuần trên kết quả pipeline đã có (khung người, khung xương, mã bám, nhân viên/khách, bàn), không chạy
model nào, nên test được không cần GPU (test_an_ninh.py). easyfnb_test.py gọi khi chạy với --an-ninh.

Ba loại sự kiện gửi máy chủ (POST /api/edge/event):
  - co_nguoi_ngoai_gio: quán đang đóng (an_ninh.closed) và bật after_hours: một người có mặt liên tục >= 3 giây.
  - vao_khu_cam: bật restricted, quán đang mở, ngoài khung giờ giao hàng: người được chấm là KHÁCH có tâm chân
    trong vùng `quay` hoặc `kho` >= 3 giây.
  - lay_do: bật item_taken: đồ có giá trị (túi, ba lô, va li, laptop, điện thoại) đứng yên ở bàn >= 10 giây rồi
    biến mất 3 lần quét liên tiếp; người có cổ tay gần đồ nhất trong 3 giây trước đó là "người lấy". Người lấy là
    người của bàn (ngồi bàn đó >= 20 giây, hoặc giống ảnh người của bàn theo vector PE-Core) thì bỏ qua; là nhân
    viên thì chỉ in ra; còn lại thì báo.
Mỗi người (mã bám) chỉ báo lại sau 60 giây; máy chủ còn gộp trùng 5 phút.

Ảnh người của bàn và vector chỉ nằm trong RAM, xoá khi bàn đã dọn (hết lượt khách) hoặc người đó rời bàn quá lâu.
Mọi ảnh trả ra ở đây cắt từ khung pipeline đưa vào: pipeline phải đưa khung ĐÃ che mặt.
"""
from collections import deque

import cv2
import numpy as np

from fnb_common import grow_box, make_overview, make_strip

LAN_KHU_CAM = ('quay', 'kho')           # loại vùng cấm khách (quầy thu ngân, kho/bếp)
# đồ có giá trị (mã lớp COCO của yolo26s)
DO_GIA_TRI = {24: 'ba lô', 26: 'túi xách', 28: 'va li', 63: 'laptop', 67: 'điện thoại'}
LWR, RWR, LAN, RAN = 9, 10, 15, 16
TILE_NGUOI = (288, 384)                 # ô dải ảnh quanh người, 3:4 như 'call'


def tam_chan(kp, kc, box, th=0.3):
    """Điểm chân của một người: trung điểm hai cổ chân; thấy một bên thì lấy bên đó; không thấy thì đáy khung."""
    ok = [k for k in (LAN, RAN) if kc is not None and kp is not None and float(kc[k]) >= th]
    if ok:
        return float(np.mean([kp[k][0] for k in ok])), float(np.mean([kp[k][1] for k in ok]))
    x1, y1, x2, y2 = map(float, box[:4])
    return (x1 + x2) / 2, y2


def trong(pt, poly):
    return cv2.pointPolygonTest(np.asarray(poly, np.float32).reshape(-1, 1, 2), (float(pt[0]), float(pt[1])), False) >= 0


def _tam(b):
    return (float(b[0]) + float(b[2])) / 2, (float(b[1]) + float(b[3])) / 2


def _iou(a, b):
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    i = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i
    return i / u if u > 0 else 0.0


def _cach_hop(pt, b):
    """Khoảng cách từ điểm tới hình chữ nhật b (0 nếu nằm trong)."""
    dx = max(float(b[0]) - pt[0], 0.0, pt[0] - float(b[2]))
    dy = max(float(b[1]) - pt[1], 0.0, pt[1] - float(b[3]))
    return float(np.hypot(dx, dy))


NGOAI_GIO_LAP_S = 300.0     # ngoài giờ: cả camera chỉ báo một lần mỗi 5 phút (khớp máy chủ), đỡ cắt clip liên tục


class AnNinh:
    def __init__(self, cho_s=3.0, lap_s=60.0, vang_s=1.0, ngoi_s=20.0, yen_s=10.0, mat_lan=3, truoc_s=3.0,
                 giu_s=600.0, giong=0.88, vector=None):
        self.cho_s = cho_s           # có mặt (ngoài giờ) / đứng trong khu cấm bao lâu mới báo
        self.lap_s = lap_s           # một người (một vùng) báo lại sau bấy nhiêu giây
        self.vang_s = vang_s         # mất dấu ngắn hơn mức này vẫn tính là liên tục
        self.ngoi_s = ngoi_s         # ngồi bàn bao lâu thì thành "người của bàn"
        self.yen_s = yen_s           # đồ đứng yên bao lâu thì thành "đồ của bàn"
        self.mat_lan = mat_lan       # đồ không thấy bấy nhiêu lần quét liên tiếp thì coi là đã bị lấy
        self.truoc_s = truoc_s       # tìm người lấy trong bấy nhiêu giây trước lần cuối thấy đồ
        self.giu_s = giu_s           # người của bàn rời bàn quá lâu thì quên (giống HOLD_S của máy chủ)
        self.giong = giong           # cosine vector PE-Core từ mức này coi là cùng người (CHƯA ĐO)
        self.vector = vector         # hàm(ảnh BGR) -> vector đã chuẩn hoá, None: chỉ so mã bám
        self._co_mat = {}            # mã người -> [từ lúc, lần cuối thấy] (ngoài giờ)
        self._khu = {}               # (mã người, vùng) -> [từ lúc, lần cuối thấy] (khu cấm)
        self._da_bao = {}            # (loại, mã người, vùng) -> lúc báo
        self._ngoi = {}              # mã người -> [bàn, từ lúc, lần cuối thấy ngồi]
        self.nguoi_ban = {}          # bàn -> {mã người: dict(t, cuoi, anh, vec)}
        self.do_ban = {}             # bàn -> [dict(ten, box, t_dau, t_cuoi, mat, cua_ban)]
        self._lich_su = deque()      # (t, mã người, box, [cổ tay], nhân viên) mỗi người mỗi khung, 15 giây
        self._hien = []              # khung người của khung mới nhất (để biết đồ có bị che khuất không)
        self.nhat_ky = []            # việc chỉ in ra, không gửi (nhân viên cất đồ, chính khách lấy đồ...)

    # ------------------------------------------------------------ mỗi khung
    def cap_nhat(self, t, persons, cfg, areas=(), chup=None):
        """persons: [dict(id, box, kp, kc, staff, da_xet, walking, dung, ban)]. cfg: an_ninh từ máy chủ.
        areas: [dict(id, type, name, poly)] theo pixel khung. chup(p): ảnh cắt (đã che mặt) của người p, gọi khi
        người đó vừa thành người của bàn. Trả về danh sách sự kiện ngoài giờ / khu cấm."""
        out = []
        self._hien = [p['box'] for p in persons]
        for p in persons:
            wr = [(float(p['kp'][k][0]), float(p['kp'][k][1])) for k in (LWR, RWR)
                  if p.get('kc') is not None and float(p['kc'][k]) >= 0.3]
            self._lich_su.append((t, int(p['id']), [float(v) for v in p['box'][:4]], wr, bool(p.get('staff'))))
        while self._lich_su and self._lich_su[0][0] < t - 15.0:
            self._lich_su.popleft()

        # ---- ngoài giờ
        if cfg.get('closed') and cfg.get('after_hours'):
            for p in persons:
                tid = int(p['id'])
                st = self._lien_tuc(self._co_mat, tid, t)
                if t - st[0] >= self.cho_s and self._chua_bao('co_nguoi_ngoai_gio', '*', None, t, NGOAI_GIO_LAP_S):
                    chan = tam_chan(p.get('kp'), p.get('kc'), p['box'])
                    vung = next((a for a in sorted(areas, key=lambda a: a.get('type') != 'cua') if trong(chan, a['poly'])),
                                None)
                    out.append(dict(loai='co_nguoi_ngoai_gio', ban=None, area=vung['id'] if vung else None,
                                    nguoi=tid, box=[float(v) for v in p['box'][:4]], t=t, poly=vung and vung['poly'],
                                    chi_tiet=f"có người trong quán {t - st[0]:.0f} giây"
                                             + (f", {vung['name']}" if vung else '')))
        else:
            self._co_mat.clear()
        self._bo_cu(self._co_mat, t)

        # ---- khu cấm
        if cfg.get('restricted') and not cfg.get('delivery_now') and not cfg.get('closed'):
            cam = [a for a in areas if a.get('type') in LAN_KHU_CAM]
            for p in persons:
                tid = int(p['id'])
                if p.get('staff') or not p.get('da_xet', True):
                    continue
                chan = tam_chan(p.get('kp'), p.get('kc'), p['box'])
                for a in cam:
                    if not trong(chan, a['poly']):
                        continue
                    st = self._lien_tuc(self._khu, (tid, a['id']), t)
                    if t - st[0] >= self.cho_s and self._chua_bao('vao_khu_cam', tid, a['id'], t):
                        out.append(dict(loai='vao_khu_cam', ban=None, area=a['id'], nguoi=tid,
                                        box=[float(v) for v in p['box'][:4]], t=t, poly=a['poly'],
                                        chi_tiet=f"khách ở {a['name']} {t - st[0]:.0f} giây"))
            # nhân viên (nhãn vừa bật) không được tính tiếp thời gian ở khu cấm
            for p in persons:
                if p.get('staff'):
                    for k in [k for k in self._khu if k[0] == int(p['id'])]:
                        del self._khu[k]
        else:
            self._khu.clear()
        self._bo_cu(self._khu, t)

        # ---- người của bàn (cho lấy đồ)
        if cfg.get('item_taken'):
            for p in persons:
                tid, ban = int(p['id']), p.get('ban')
                # ban_chac False (khop_ban.py): đang lưỡng lự giữa bàn sát nhau, chưa chốt: chưa gắn người vào bàn
                if not ban or p.get('ban_chac') is False or p.get('walking') or p.get('dung') or p.get('staff'):
                    continue
                st = self._ngoi.get(tid)
                if st is None or st[0] != ban or t - st[2] > 2 * self.vang_s + 1.0:
                    st = self._ngoi[tid] = [ban, t, t]
                st[2] = t
                ds = self.nguoi_ban.setdefault(ban, {})
                if tid in ds:
                    ds[tid]['cuoi'] = t
                elif t - st[1] >= self.ngoi_s:
                    anh = chup(p) if chup is not None else None
                    vec = None
                    if self.vector is not None and anh is not None and anh.size:
                        try:
                            vec = np.asarray(self.vector(anh), np.float32).ravel()
                        except Exception as e:    # vector hỏng thì chỉ so mã bám
                            print(f'  [an ninh] không tính được vector người: {e}')
                    ds[tid] = dict(t=t, cuoi=t, anh=anh, vec=vec)
                    print(f'  [an ninh] #{tid} là người của bàn {ban}')
            for ban, ds in self.nguoi_ban.items():
                for tid in [k for k, v in ds.items() if t - v['cuoi'] > self.giu_s]:
                    del ds[tid]
            for tid in [k for k, v in self._ngoi.items() if t - v[2] > 30.0]:
                del self._ngoi[tid]
        return out

    def _lien_tuc(self, d, k, t):
        st = d.get(k)
        if st is None or t - st[1] > self.vang_s:
            st = d[k] = [t, t]
        st[1] = t
        return st

    def _bo_cu(self, d, t):
        for k in [k for k, v in d.items() if t - v[1] > self.vang_s]:
            del d[k]

    def _chua_bao(self, loai, tid, vung, t, lap_s=None):
        k = (loai, tid, vung)
        if t - self._da_bao.get(k, -1e9) < (self.lap_s if lap_s is None else lap_s):
            return False
        self._da_bao[k] = t
        if len(self._da_bao) > 2000:
            for kk in [kk for kk, v in self._da_bao.items() if t - v > self.lap_s]:
                del self._da_bao[kk]
        return True

    def xoa(self):
        """Cảnh nhảy (video lặp lại, camera mất hình): quên hết."""
        for d in (self._co_mat, self._khu, self._ngoi, self.nguoi_ban, self.do_ban):
            d.clear()
        self._lich_su.clear()
        self._hien = []

    def xoa_ban(self, ban):
        """Hết lượt khách của bàn (bàn đã dọn): quên người của bàn và đồ của bàn."""
        self.nguoi_ban.pop(ban, None)
        self.do_ban.pop(ban, None)

    def can_quet(self, ban, co_khach):
        """Bàn này có cần quét đồ không: đang có khách, hoặc còn người / đồ của bàn (khách tạm rời, còn đồ)."""
        return bool(co_khach or self.nguoi_ban.get(ban) or self.do_ban.get(ban))

    # ------------------------------------------------------------ lấy đồ
    def quet_do(self, t, ban, dets, lay_anh=None):
        """Một lần quét đồ của bàn `ban`: dets = [(tên, box)] đồ có giá trị thấy được ở bàn (toạ độ khung).
        lay_anh(box, t): ảnh cắt (đã che mặt) quanh box lúc t, để so vector người lấy với người của bàn.
        Trả về danh sách sự kiện 'lay_do'."""
        ds = self.do_ban.setdefault(ban, [])
        con = list(range(len(ds)))
        for ten, b in dets:
            b = [float(v) for v in b[:4]]
            diag = float(np.hypot(b[2] - b[0], b[3] - b[1]))
            best, k_best = None, None
            for k in con:
                it = ds[k]
                d = float(np.hypot(*np.subtract(_tam(it['box']), _tam(b))))
                if _iou(it['box'], b) >= 0.3 or d < 0.35 * diag:
                    if best is None or d < best:
                        best, k_best = d, k
            if k_best is None:
                ds.append(dict(ten=ten, box=b, t_dau=t, t_cuoi=t, mat=0, cua_ban=False,
                               dat=self._tay_gan(b, t - self.truoc_s, t)))
                continue
            con.remove(k_best)
            it = ds[k_best]
            it.update(box=b, t_cuoi=t, mat=0)
            if not it['cua_ban'] and t - it['t_dau'] >= self.yen_s:
                it['cua_ban'] = True
                print(f"  [an ninh] {it['ten']} ở bàn {ban} là đồ của bàn")
        out, bo = [], []
        for k in con:
            it = ds[k]
            c = _tam(it['box'])
            if any(_cach_hop(c, pb) == 0 for pb in self._hien):
                continue    # có người đứng che chỗ đồ: lần quét này không tính
            it['mat'] += 1
            if it['mat'] < self.mat_lan:
                continue
            bo.append(k)
            if it['cua_ban']:
                e = self._mat_do(t, ban, it, lay_anh)
                if e is not None:
                    out.append(e)
        for k in sorted(bo, reverse=True):
            del ds[k]
        return out

    def _tay_gan(self, do_box, tu, den, tat_ca=False):
        """Người có cổ tay gần món đồ nhất trong khoảng [tu, den]: (khoảng cách, t, mã người, box, nhân viên).
        Không có tat_ca thì chỉ trả mã người (None nếu không ai ở gần)."""
        diag = float(np.hypot(do_box[2] - do_box[0], do_box[3] - do_box[1]))
        best = None
        for tt, tid, box, wr, nv in self._lich_su:
            if tt < tu or tt > den:
                continue
            gan = max(0.5 * diag, 0.2 * (box[3] - box[1]))
            for w in wr:
                d = _cach_hop(w, do_box)
                if d <= gan and (best is None or d < best[0]):
                    best = (d, tt, tid, box, nv)
        return best if tat_ca else (best[2] if best else None)

    def _mat_do(self, t, ban, it, lay_anh):
        best = self._tay_gan(it['box'], it['t_cuoi'] - self.truoc_s, t, tat_ca=True)
        ten = it['ten']
        if best is None:
            self._ghi(t, f'{ten} ở bàn {ban} không còn thấy, không rõ ai cầm (không có cổ tay nào ở gần)')
            return None
        _, t_lay, tid, box, nv = best
        cua = self.nguoi_ban.get(ban, {})
        if tid in cua:
            self._ghi(t, f'#{tid} (người của bàn {ban}) cầm {ten}: bỏ qua')
            return None
        if tid == it.get('dat'):    # khách vừa tới, đặt túi xuống rồi cầm đi đổi bàn: chưa kịp thành người của bàn
            self._ghi(t, f'#{tid} lấy lại {ten} chính mình đặt xuống bàn {ban}: bỏ qua')
            return None
        if nv or any(x[1] == tid and x[4] for x in self._lich_su):
            self._ghi(t, f'nhân viên #{tid} cất {ten} ở bàn {ban}')
            return None
        sim = None
        if self.vector is not None and lay_anh is not None and any(v.get('vec') is not None for v in cua.values()):
            try:
                anh = lay_anh(box, t_lay)
                if anh is not None and anh.size:
                    v = np.asarray(self.vector(anh), np.float32).ravel()
                    sim = max(float(v @ m['vec']) for m in cua.values() if m.get('vec') is not None)
            except Exception as e:
                print(f'  [an ninh] không so được vector người lấy: {e}')
        if sim is not None and sim >= self.giong:
            self._ghi(t, f'#{tid} cầm {ten} ở bàn {ban}: giống người của bàn ({sim:.2f}), bỏ qua')
            return None
        ref = next((m['anh'] for m in sorted(cua.values(), key=lambda m: -m['t'])
                    if m.get('anh') is not None), None)
        msg = f'{ten} ở bàn {ban}'
        print(f'  [an ninh] #{tid} lấy {msg}' + (f' (giống người của bàn {sim:.2f})' if sim is not None else ''))
        return dict(loai='lay_do', ban=ban, area=None, nguoi=tid, box=box, t=t, t_lay=t_lay, ten=ten,
                    do_box=it['box'], ref=ref, sim=sim, chi_tiet=ten)

    def _ghi(self, t, msg):
        print(f'  [an ninh] {msg}')
        self.nhat_ky.append((t, msg))
        del self.nhat_ky[:-200]

    # ------------------------------------------------------------ ảnh bằng chứng
    def box_luc(self, tid, t):
        """Khung của người tid gần lúc t nhất trong lịch sử (None nếu không có)."""
        c = [(abs(tt - t), box) for tt, k, box, _, _ in self._lich_su if k == tid]
        return min(c, key=lambda x: x[0])[1] if c else None

    def anh_bang_chung(self, buf, e, W, H):
        """(crop, strip, overview) cho sự kiện e từ buf = [(t, khung ĐÃ che mặt)]. Dải 4 khung quanh người, khung đỏ
        quanh người ở từng khung; toàn cảnh có khung đỏ và vùng (nếu có). None nếu chưa có khung nào."""
        if not buf:
            return None
        tid = e['nguoi']
        t0 = e.get('t_lay', e['t'])
        offs = (-1.5, -0.5, 0.5, 1.5) if e['loai'] == 'lay_do' else (-3.0, -2.0, -1.0, 0.0)
        frames, hop = [], None
        for dt in offs:
            tt, f = min(buf, key=lambda c: abs(c[0] - (t0 + dt)))
            b = self.box_luc(tid, tt) or e['box']
            f = f.copy()
            cv2.rectangle(f, (int(b[0]), int(b[1])), (int(b[2]), int(b[3])), (0, 0, 255), 3)
            frames.append((tt - e['t'], f))
            hop = list(b) if hop is None else [min(hop[0], b[0]), min(hop[1], b[1]), max(hop[2], b[2]), max(hop[3], b[3])]
        tw, th = TILE_NGUOI
        strip = make_strip(frames, grow_box(hop, W, H, tw / th), (tw, th))
        _, f0 = min(buf, key=lambda c: abs(c[0] - t0))
        b = self.box_luc(tid, t0) or e['box']
        x1, y1, x2, y2 = (int(v) for v in b)
        p = 0.15 * (y2 - y1)
        crop = f0[max(0, int(y1 - p)):min(H, int(y2 + p)), max(0, int(x1 - p)):min(W, int(x2 + p))].copy()
        base = f0.copy()
        if e.get('poly') is not None:
            cv2.polylines(base, [np.int32(e['poly'])], True, (0, 220, 255), 3)
        if e.get('do_box') is not None:
            d = e['do_box']
            cv2.rectangle(base, (int(d[0]), int(d[1])), (int(d[2]), int(d[3])), (0, 220, 255), 2)
        overview = make_overview(base, box=b, text={'lay_do': 'nguoi lay do', 'vao_khu_cam': 'nguoi o khu cam',
                                                    'co_nguoi_ngoai_gio': 'nguoi ngoai gio'}.get(e['loai'], ''))
        return crop, strip, overview
