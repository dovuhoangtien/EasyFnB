"""Làm mờ mặt khách từ khung xương pose (keypoint 0-4: mũi, 2 mắt, 2 tai). Không cần model mặt.

blur_faces(img, kpts, kconf, boxes) -> ảnh mới đã làm mờ (img giữ nguyên).
Chỉ làm trên bản sao gửi đi (crop sự kiện, khung live, khung gốc), không đụng ảnh pipeline dùng.
"""
import cv2
import numpy as np

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
