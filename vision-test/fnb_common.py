"""Hàm dùng chung cho pipeline và các script train."""
import math

import cv2
import numpy as np


def square(img, size=None, color=114):
    """Thêm viền xám cho ảnh thành hình vuông (không cắt mất phần nào).

    YOLO-cls thu cạnh ngắn rồi cắt giữa, nên ảnh người cao 2:1 sẽ mất đầu và tay giơ.
    Đưa về hình vuông trước khi train và khi chạy thì không mất gì.
    """
    h, w = img.shape[:2]
    s = max(h, w)
    out = np.full((s, s, 3), color, np.uint8)
    y, x = (s - h) // 2, (s - w) // 2
    out[y:y + h, x:x + w] = img
    if size and s != size:
        out = cv2.resize(out, (size, size), interpolation=cv2.INTER_AREA if s > size else cv2.INTER_LINEAR)
    return out


def pad_box(frame, b, pad=0.08):
    """Cắt khung b, nới `pad` theo kích thước khung (giống lúc tạo dữ liệu train)."""
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = b
    bw, bh = x2 - x1, y2 - y1
    x1, y1 = max(0, int(x1 - pad * bw)), max(0, int(y1 - pad * bh))
    x2, y2 = min(w, int(x2 + pad * bw)), min(h, int(y2 + pad * bh))
    return frame[y1:y2, x1:x2]


def rect_size(w, h, size, stride=32):
    """Cỡ ảnh [cao, rộng] mà YOLO dùng khi thu cạnh dài về `size`. Model đã xuất (TensorRT, ONNX...)
    có cỡ cố định, nên phải đưa đúng cỡ này."""
    s = size / max(w, h)
    return [int(math.ceil(h * s / stride) * stride), int(math.ceil(w * s / stride) * stride)]


# ---------------------------------------------------------------- làm mờ mặt (thu_nghiem/lam_mo_mat)
# Làm mờ mặt khách từ khung xương pose (keypoint 0-4: mũi, 2 mắt, 2 tai), không cần model mặt.
# Chỉ làm trên bản sao gửi khỏi máy (crop sự kiện, khung live, khung gốc, gói xác minh), không đụng ảnh pipeline dùng.
NOSE, LEYE, REYE, LEAR, REAR, LSH, RSH, LEL, REL, LWR, RWR = 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
HEAD = (NOSE, LEYE, REYE, LEAR, REAR)


def _dist(kp, kc, a, b, th):
    if kc[a] >= th and kc[b] >= th:
        return float(np.hypot(*(kp[a] - kp[b])))
    return None


def head_ellipse(kp, kc, box, th=0.3, img_wh=None):
    """(cx, cy, a, b, nguon) của elip che đầu một người, hoặc None nếu không đoán được."""
    x1, y1, x2, y2 = map(float, box)
    bw, bh = x2 - x1, y2 - y1
    # cỡ đầu: lấy lớn nhất trong các ước lượng có được (thà che rộng hơn còn hơn hở mặt)
    est = []
    if (d := _dist(kp, kc, LEAR, REAR, th)) is not None:
        est.append(0.75 * d)
    if (d := _dist(kp, kc, LEYE, REYE, th)) is not None:
        est.append(1.6 * d)
    for ear in (LEAR, REAR):  # mặt nghiêng: hai mắt gần nhau, tai-mũi mới cho cỡ đầu
        if (d := _dist(kp, kc, NOSE, ear, th)) is not None:
            est.append(0.6 * d)
    sw = _dist(kp, kc, LSH, RSH, th)
    if sw is not None:
        est.append(0.32 * sw)
    est.append(0.08 * bh)                 # sàn: người bị bàn che chỉ còn nửa trên
    r = max(est)
    r = min(r, 0.6 * bw if bw > 0 else r, 0.25 * bh if bh > 0 else r)
    r = max(r, 0.05 * bh, 5.0)

    vis = [i for i in HEAD if kc[i] >= th]
    if vis:
        cx = float(np.mean([kp[i][0] for i in vis]))
        cy = float(np.mean([kp[i][1] for i in vis]))
        face = [i for i in (NOSE, LEYE, REYE) if kc[i] >= th]
        ears = [i for i in (LEAR, REAR) if kc[i] >= th]
        if face:
            # mặt nằm phía dưới mắt: dời tâm xuống; cúi đầu (mũi thấp hơn tai nhiều) thì dời thêm xuống
            cy += 0.25 * r
            if ears and kc[NOSE] >= th:
                cy += 0.5 * max(0.0, float(kp[NOSE][1] - np.mean([kp[i][1] for i in ears])))
        # mọi điểm đầu phải nằm trong elip, chừa thêm lề (mũi ở mặt nghiêng hay bị sát mép)
        a = max(1.2 * r, max(abs(kp[i][0] - cx) for i in vis) + 0.45 * r)
        b = max(1.6 * r, max(abs(kp[i][1] - cy) for i in vis) + 0.6 * r)
        return cx, cy, a, b, 'kp'
    sh = [i for i in (LSH, RSH) if kc[i] >= th]
    if sh:  # không thấy điểm đầu: đầu nằm trên vai
        sx = float(np.mean([kp[i][0] for i in sh]))
        sy = float(min(kp[i][1] for i in sh))
        if len(sh) == 1:
            sx = (sx + (x1 + x2) / 2) / 2
        return sx, sy - 1.3 * r, 1.2 * r, 1.6 * r, 'vai'
    # không thấy điểm đầu lẫn vai:
    # - chỉ thấy chân (box "người" là chân dưới gầm bàn) -> đầu bị bàn che, không có gì để che
    if kc[:11].max() < 0.1 and kc[11:].max() >= 0.15:
        return None
    # - thấy tay mà box chạm mép ảnh -> đầu nằm ngoài khung; che phần trên box chỉ làm mờ cánh tay đang giơ
    if img_wh is not None and kc[5:11].max() >= th and (x1 <= 2 or y1 <= 2 or x2 >= img_wh[0] - 2):
        return None
    # còn lại: che phần trên của box
    return (x1 + x2) / 2, y1 + 0.12 * bh, 0.5 * bw, 0.14 * bh, 'box'


def raised_hand_zones(kp, kc, r, box, th=0.3):
    """Đoạn (p, q, bán kính) quanh cổ tay đang giơ cao hơn mũi/mắt: không được làm mờ chỗ này."""
    out = []
    head_y = [kp[i][1] for i in HEAD if kc[i] >= th]
    sh_y = [kp[i][1] for i in (LSH, RSH) if kc[i] >= th]
    for el, wr in ((LEL, LWR), (REL, RWR)):
        if kc[wr] < th:
            continue
        w = kp[wr]
        if head_y:
            above = w[1] < min(head_y) - 0.3 * r
        elif sh_y:
            above = w[1] < min(sh_y) - 1.5 * r
        else:  # không thấy đầu lẫn vai (người ở mép hình): cổ tay nằm ở phần trên của box là tay giơ
            above = w[1] < box[1] + 0.35 * (box[3] - box[1])
        if not above:
            continue
        d = w - kp[el] if kc[el] >= th else np.array([0.0, -1.0])
        d = d / (np.hypot(*d) + 1e-6)
        tip = w + 1.0 * r * d       # bàn tay dài cỡ một mặt, kéo dài theo cẳng tay
        out.append((w, tip, 0.45 * r))  # vừa đủ bàn tay: rộng quá sẽ hở mặt người đứng sau tay
    return out


def blur_faces(img, kpts, kconf, boxes, th=0.3, mode='pixel', return_mask=False, inplace=False):
    """Làm mờ đầu từng người. kpts (N,17,2), kconf (N,17), boxes (N,4) cùng hệ toạ độ với img."""
    out = img if inplace else img.copy()
    H, W = img.shape[:2]
    if boxes is None or len(boxes) == 0:
        return (out, np.zeros((H, W), np.uint8)) if return_mask else out
    heads, hands = [], []
    for kp, kc, b in zip(kpts, kconf, boxes):
        kp = np.asarray(kp, np.float32)
        kc = np.asarray(kc, np.float32)
        e = head_ellipse(kp, kc, b, th, (W, H))
        if e is None:
            continue
        heads.append((*e, b))
        hands += raised_hand_zones(kp, kc, min(e[2], e[3]), b, th)
    full = np.zeros((H, W), np.uint8) if return_mask else None
    for cx, cy, a, bb, src, box in heads:
        x0, y0 = max(0, int(cx - a - 1)), max(0, int(cy - bb - 1))
        x1, y1 = min(W, int(cx + a + 2)), min(H, int(cy + bb + 2))
        if x1 - x0 < 2 or y1 - y0 < 2:
            continue
        m = np.zeros((y1 - y0, x1 - x0), np.uint8)
        cv2.ellipse(m, (int(round(cx - x0)), int(round(cy - y0))), (int(round(a)), int(round(bb))), 0, 0, 360, 255, -1)
        for p, q, rr in hands:
            # chừa tay giơ ra, nhưng chỉ khoét elip của chính người giơ (cổ tay nằm trong box của họ) hoặc elip
            # đoán mò (không thấy điểm đầu). Mặt người khác thấy rõ điểm đầu thì luôn che: riêng tư hơn tay.
            if src == 'kp' and not (box[0] <= p[0] <= box[2] and box[1] <= p[1] <= box[3]):
                continue
            cv2.line(m, (int(p[0] - x0), int(p[1] - y0)), (int(q[0] - x0), int(q[1] - y0)), 0, max(1, int(2 * rr)))
        roi = out[y0:y1, x0:x1]
        if mode == 'pixel':
            blk = max(2, int(2 * a / 5))      # ~5 ô ngang đầu
            sm = cv2.resize(roi, (max(1, roi.shape[1] // blk), max(1, roi.shape[0] // blk)), interpolation=cv2.INTER_AREA)
            fx = cv2.resize(sm, (roi.shape[1], roi.shape[0]), interpolation=cv2.INTER_NEAREST)
        else:
            k = int(a) | 1
            fx = cv2.GaussianBlur(roi, (k, k), 0)
        cv2.copyTo(fx, m, roi)
        if full is not None:
            full[y0:y1, x0:x1] |= m
    return (out, full) if return_mask else out


# ---------------------------------------------------------------- gói bằng chứng cho Gemini (thu_nghiem/gemini_goi_kiem_tra)
# Dải 2x2 (4 khung quanh sự kiện, cắt quanh người 3:4 hoặc bàn 4:3), toàn cảnh 768 px có khung đỏ,
# và (bàn cần dọn) ảnh bàn lúc sạch. Cùng cách cắt với dung_goi.py.
TILE = {'call': (288, 384), 'needs_clearing': (384, 288)}   # (rộng, cao) mỗi ô: người 3:4, bàn 4:3


def grow_box(b, W, H, aspect, grow=0.30):
    """Nới box thêm 30% (15% mỗi bên), rồi chỉ nới cạnh ngắn cho đúng tỉ lệ ô (rộng/cao), dịch vào trong khung.
    Không làm vuông: crop vuông quanh người kéo cả người bên cạnh vào ô."""
    x1, y1, x2, y2 = map(float, b)
    w, h = max(2.0, (x2 - x1) * (1 + grow)), max(2.0, (y2 - y1) * (1 + grow))
    if w / h < aspect:
        w = h * aspect
    else:
        h = w / aspect
    w, h = min(w, W), min(h, H)
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    x1 = int(np.clip(cx - w / 2, 0, W - w))
    y1 = int(np.clip(cy - h / 2, 0, H - h))
    return x1, y1, int(x1 + w), int(y1 + h)


def put_label(img, text, org=(6, 24), scale=0.6):
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, 2)
    x, y = org
    cv2.rectangle(img, (x - 4, y - th - 6), (x + tw + 4, y + 6), (0, 0, 0), -1)
    cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, scale, (255, 255, 255), 2, cv2.LINE_AA)


def make_strip(frames, region, tile_wh):
    """frames: 4 cặp (lệch giây so với sự kiện, ảnh). region: vùng cắt (x1, y1, x2, y2) theo toạ độ của ảnh."""
    TW, TH = tile_wh
    x1, y1, x2, y2 = region
    tiles = []
    for dt, f in frames:
        tile = cv2.resize(f[y1:y2, x1:x2], (TW, TH), interpolation=cv2.INTER_AREA)
        put_label(tile, f't{dt:+.1f}s' if abs(dt) > 0.05 else 't (su kien)')
        tiles.append(tile)
    strip = np.vstack([np.hstack(tiles[:2]), np.hstack(tiles[2:])])
    cv2.line(strip, (TW, 0), (TW, 2 * TH), (255, 255, 255), 2)
    cv2.line(strip, (0, TH), (2 * TW, TH), (255, 255, 255), 2)
    return strip


def make_overview(frame, box=None, poly=None, text='', width=768):
    """Cả khung thu về `width` px, khung đỏ quanh người (box) hoặc vùng bàn (poly), toạ độ theo ảnh `frame`."""
    s = width / frame.shape[1]
    f = cv2.resize(frame, (width, int(round(frame.shape[0] * s))), interpolation=cv2.INTER_AREA)
    if poly is not None:
        p = np.int32(np.asarray(poly, np.float32) * s)
        cv2.polylines(f, [p], True, (0, 0, 255), 3)
        x, y = p.min(0)
    else:
        x1, y1, x2, y2 = (int(v * s) for v in box)
        cv2.rectangle(f, (x1, y1), (x2, y2), (0, 0, 255), 3)
        x, y = x1, y1
    if text:
        put_label(f, text, (max(6, int(x)), max(22, int(y) - 8)), 0.55)
    return f
