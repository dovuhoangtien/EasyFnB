#!/usr/bin/env python
"""Chạy thử phần "mắt tại quán" của Easy FnB trên clip có sẵn.

YOLO pose + ByteTrack tìm và bám từng người, YOLO detect tìm đồ trên bàn,
rồi vài luật đơn giản sinh sự kiện: khách giơ tay gọi, khách mới vào bàn,
khách rời bàn, bàn cần dọn. Mỗi sự kiện lưu kèm ảnh cắt: đó chính là ảnh
sẽ gửi Gemini xác minh ở bản thật.

    python easyfnb_test.py clips/                  # chạy hết, kết quả vào out/
    python easyfnb_test.py clips/02_x.mp4 --device cpu
"""
import argparse
import json
import math
import os
import shutil
import signal
import subprocess
import time
from collections import deque
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFont
from ultralytics import YOLO

from fnb_common import (TILE, blur_faces, grow_box, make_overview, make_strip, pad_box,
                        rect_size, square)

HERE = Path(__file__).resolve().parent

# Đồ thường còn lại trên bàn sau khi khách ăn xong (mã lớp COCO)
ITEMS = {39: 'chai', 40: 'ly', 41: 'cốc', 42: 'nĩa', 43: 'dao', 44: 'muỗng', 45: 'tô',
         46: 'chuối', 47: 'táo', 48: 'bánh mì', 49: 'cam', 50: 'rau', 51: 'cà rốt',
         52: 'xúc xích', 53: 'pizza', 54: 'bánh', 55: 'bánh ngọt'}
# Các nhãn đã được đóng vào engine YOLOE TensorRT. ``glass`` bị loại vì thử nghiệm cho thấy
# nó gây báo nhầm; đồ cá nhân/đồ cố định của quán cũng không làm bàn thành "cần dọn".
YOLOE_VI = {
    'plate': 'dĩa', 'bowl': 'chén', 'cup': 'ly', 'bottle': 'chai', 'can': 'lon',
    'chopsticks': 'đũa', 'spoon': 'muỗng', 'fork': 'nĩa', 'knife': 'dao',
    'napkin': 'khăn giấy', 'tissue': 'khăn giấy', 'tray': 'khay', 'food': 'thức ăn',
    'leftovers': 'thức ăn thừa', 'paper': 'giấy', 'wrapper': 'vỏ gói',
}
NOSE, LSH, RSH, LEL, REL, LWR, RWR = 0, 5, 6, 7, 8, 9, 10
LHI, RHI, LKN, RKN, LAN, RAN = 11, 12, 13, 14, 15, 16   # hông, đầu gối, cổ chân (COCO)

BGR = {
    'trong': (90, 200, 90),
    'co_khach': (230, 150, 60),
    'can_don': (0, 160, 255),
    'goi': (40, 40, 230),
    'di': (170, 170, 170),
    'nv': (200, 80, 200),
    'item': (0, 200, 255),
}
STATE_VI = {'trong': 'trống', 'co_khach': 'có khách', 'can_don': 'cần dọn'}
CODE = {'trong': 'T', 'co_khach': 'C', 'can_don': 'D'}
EVENT_VI = {
    'goi_phuc_vu': 'Khách giơ tay gọi',
    'khach_moi': 'Khách mới vào bàn',
    'khach_roi': 'Khách rời bàn',
    'can_don': 'Bàn cần dọn',
    'da_don': 'Bàn đã dọn',
    'nv_den': 'Nhân viên tới bàn',
}


def load_font(size):
    for f in ('C:/Windows/Fonts/segoeui.ttf', 'C:/Windows/Fonts/arial.ttf',
              '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            pass
    return ImageFont.load_default()


def load_model(names):
    """Thử lần lượt các tên model, dùng cái đầu tiên tải được."""
    (HERE / 'models').mkdir(exist_ok=True)
    err = None
    for n in names:
        try:
            return YOLO(str(HERE / 'models' / n)), n
        except Exception as e:  # tên model chưa có trong bản ultralytics này
            err = e
    raise err


_CLIP = {}


def is_clip_head(path):
    """File lớp nhỏ trên CLIP (hoặc bộ mã hoá ảnh khác) là dict có 'w', 'b', 'classes'; file YOLO thì không."""
    try:
        d = torch.load(path, map_location='cpu', weights_only=True)
    except Exception:
        return False
    return isinstance(d, dict) and 'w' in d and 'classes' in d


def load_small_model(name):
    """Model nhỏ trên ảnh cắt: YOLO-cls trong models/, hoặc CLIP.

    'clip' = CLIP không train (so với câu mô tả bàn sạch/bẩn);
    tên có chữ 'clip' và đuôi .pt = CLIP + lớp nhỏ đã học (bàn hoặc người).
    """
    if not name:
        return None
    if name != 'clip' and not is_clip_head(HERE / 'models' / name):
        return load_model([name])[0]
    if name not in _CLIP:
        from clip_cls import ClipCls
        _CLIP[name] = ClipCls(head=None if name == 'clip' else str(HERE / 'models' / name))
    return _CLIP[name]


def class_probs(model, crops, cls_name):
    """Xác suất lớp `cls_name` cho từng ảnh cắt (None hết nếu không bật model).

    Ảnh được thêm viền thành hình vuông trước, vì YOLO-cls cắt giữa ảnh và sẽ làm mất
    phần đầu, tay giơ của ảnh người cao.
    """
    if model is None or not crops:
        return [None] * len(crops)
    if hasattr(model, 'p_pos'):  # CLIP: trả xác suất lớp dương (bàn "bẩn", người "nhan_vien")
        if model.classes[1] != cls_name:
            raise ValueError(f'model CLIP này phân loại {model.classes}, không có lớp dương {cls_name}')
        return model.p_pos(crops)
    idx = next(k for k, v in model.names.items() if v == cls_name)
    rs = model.predict([square(c) for c in crops], imgsz=224, verbose=False)
    return [float(r.probs.data[idx]) for r in rs]


def table_crop(frame, poly, pad=0.10):
    x, y, w, h = cv2.boundingRect(poly.astype(np.int32))
    return pad_box(frame, (x, y, x + w, y + h), pad)


# ---------------------------------------------------------------- gói bằng chứng cho Gemini
# Sự kiện 'goi_phuc_vu' / 'can_don' gửi ngay kèm ảnh cắt (đường lui), rồi ~1 giây sau gửi
# POST /api/edge/evidence qua MayChu.evidence(): dải 2x2 bốn khung quanh sự kiện (crop
# người 3:4 hoặc bàn 4:3), toàn cảnh 768 px có khung đỏ, và (chỉ 'can_don') ảnh bàn lúc
# sạch lưu trước đó (clean_ref). Mọi ảnh đều từ bản đã làm mờ mặt (an_danh()).
# Cùng cách cắt với thu_nghiem/gemini_goi_kiem_tra/dung_goi.py: bốn khung ở t-1.0, t-0.5,
# t, t+0.5 (giữ tay đã thấy ở t-0.5..t+1.0; khung trước t-1.0 không thấy tay nên bị bỏ).
EVIDENCE_OFFSETS = (-1.0, -0.5, 0.0, 0.5)
EVIDENCE_DELAY_S = 1.0          # chờ thêm 1 giây video rồi mới gói ảnh (giống dung_goi.py 'quanh')
KIND_GEMINI = {'goi_phuc_vu': 'call', 'can_don': 'needs_clearing'}   # loai sự kiện -> vai trò Tile


def _hien_items(items):
    """Đồ trên bàn: đếm theo tên tiếng Việt để đưa kèm sự kiện 'can_don' (hiển thị cho nhân viên).

    Chưa có YOLOE trong pipeline này: tên lấy từ model COCO hiện dùng (ITEMS)."""
    if not items:
        return None
    dem = {}
    for it in items:
        ten = ITEMS.get(it[0])
        if ten:
            dem[ten] = dem.get(ten, 0) + 1
    return [{'name': k, 'count': v} for k, v in dem.items()] or None


def _hien_yoloe(items):
    """Đếm các nhãn YOLOE còn trên một bàn thành danh sách tiếng Việt cho nhân viên."""
    dem = {}
    for name, *_ in items or []:
        vi = YOLOE_VI.get(name)
        if vi:
            dem[vi] = dem.get(vi, 0) + 1
    return [{'name': k, 'count': v} for k, v in dem.items()] or None


def _text_items(items):
    return ', '.join(f"{x['count']} {x['name']}" for x in items or [])


def load_yoloe(path):
    """Mở engine YOLOE đã xuất sẵn; không tải model hay phụ thuộc mạng lúc chạy camera."""
    if not path or not Path(path).exists():
        return None
    return YOLO(str(path), task='segment')


def yoloe_table_items(model, frame, table, args):
    """Nhận đồ còn lại của một bàn đúng một lần sau khi khách rời.

    Trả None nếu model không chạy được, để pipeline giữ hành vi cũ thay vì tự làm mất cảnh báo.
    Từng món được gán cho bàn chứa tâm món sâu nhất, tránh lẫn đồ của bàn sát bên.
    """
    if model is None:
        return None
    try:
        r = model.predict(frame, imgsz=args.yoloe_imgsz, conf=args.yoloe_conf,
                          device=args.device, verbose=False, half=args.half)[0]
        if r.boxes is None:
            return []
        names, found = r.names, []
        for cls, conf, box in zip(r.boxes.cls.cpu().numpy(), r.boxes.conf.cpu().numpy(),
                                  r.boxes.xyxy.cpu().numpy()):
            name = names[int(cls)]
            if name not in YOLOE_VI:
                continue
            cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
            if cv2.pointPolygonTest(table.poly, (float(cx), float(cy)), True) > -12:
                found.append((name, float(conf), box))
        return found
    except Exception as exc:
        print(f'  YOLOE không chạy được, giữ luật cũ: {exc}')
        return None


def _dong_goi(mc, eid, kind, ban, buf, t0, W, H, clean_ref, items, box=None, poly=None):
    """Gói bằng chứng của một sự kiện và gửi lên máy chủ (không đợi phản hồi).

    strip: dải 2x2 cắt quanh người (thấy box) hoặc quanh bàn (poly+grow). overview:
    toàn cảnh 768 px, khung đỏ quanh người/bàn. ref: ảnh bàn lúc sạch nếu có. Mọi ảnh
    đều từ bản đã làm mờ mặt (buf chụp từ an_danh() trong vòng lặp chính)."""
    if not eid or not buf:
        return
    gkind = KIND_GEMINI.get(kind)
    if gkind is None or gkind not in TILE:
        return
    if box is None and poly is None:
        return
    if box is not None:
        text = 'nguoi can xet'
    else:
        text = f'Ban {ban}' if ban else 'Ban can xet'
    if box is not None:
        x1, y1, x2, y2 = box
        b = (x1, y1, x2, y2)
    else:
        x, y, w_, h_ = cv2.boundingRect(poly.astype(np.int32))
        b = (x, y, x + w_, y + h_)
    tw, th = TILE[gkind]
    sq = grow_box(b, W, H, tw / th)
    frames = []
    for dt in EVIDENCE_OFFSETS:
        tt = t0 + dt
        cand = sorted(buf, key=lambda c: abs(c[0] - tt))
        frames.append((dt, cand[0][1]))
    strip = make_strip(frames, sq, (tw, th))
    tt = min(buf, key=lambda c: abs(c[0] - t0))
    overview = make_overview(tt[1], box=box if box is not None else None,
                             poly=poly if box is None else None, text=text)
    ref = None
    if kind == 'can_don' and clean_ref is not None:
        ref = clean_ref.get(ban)
    mc.evidence(eid, strip, overview, ref_jpg=ref, items=items)


# ---------------------------------------------------------------- luật

def hand_up(kp, kc, box):
    """Điểm giơ tay của một người (0 là không giơ).

    Giơ tay gọi: cổ tay cao hơn vai rõ rệt, khuỷu tay ngang vai trở lên,
    cổ tay cao hơn mũi nếu thấy mặt (để không nhầm với uống nước, nghe điện thoại).
    """
    x1, y1, x2, y2 = box
    sh = [kp[i] for i in (LSH, RSH) if kc[i] > 0.5]
    if not sh:
        return 0.0
    sh_y = min(p[1] for p in sh)
    if kc[LSH] > 0.5 and kc[RSH] > 0.5:
        ref = max(abs(kp[LSH][0] - kp[RSH][0]), 0.1 * (y2 - y1))
    else:
        ref = 0.3 * (x2 - x1)
    best = 0.0
    for el, wr in ((LEL, LWR), (REL, RWR)):
        if kc[wr] < 0.5 or kc[el] < 0.4:
            continue
        lift = (sh_y - kp[wr][1]) / ref
        elbow_ok = kp[el][1] < sh_y + 0.35 * ref
        above_head = kc[NOSE] < 0.5 or kp[wr][1] < kp[NOSE][1]
        if lift > 0.6 and elbow_ok and above_head and kp[wr][1] < kp[el][1]:
            best = max(best, lift)
    return best


def hand_lift(kp, kc, box, tren_mui=False):
    """Luật nới lỏng: cổ tay cao hơn vai bao nhiêu (theo bề ngang vai), không xét khuỷu tay.

    Dùng để model nhỏ không báo giơ tay khi khung xương cho thấy tay vẫn ở dưới vai.
    tren_mui=True: chỉ tính khi cổ tay cao hơn mũi (người đang ăn/uống đưa tay lên miệng
    cũng qua vai, nên phải chặt hơn mới không báo nhầm).
    Trả None khi không thấy rõ vai hoặc cổ tay nào (người bị che, ở mép hình).
    """
    x1, y1, x2, y2 = box
    sh = [kp[i] for i in (LSH, RSH) if kc[i] > 0.5]
    wr = [kp[i] for i in (LWR, RWR) if kc[i] > 0.3]
    if not sh or not wr:
        return None
    if tren_mui and kc[NOSE] > 0.5 and min(p[1] for p in wr) >= kp[NOSE][1]:
        return None
    ref = max(abs(kp[LSH][0] - kp[RSH][0]), 0.1 * (y2 - y1)) if len(sh) == 2 else 0.3 * (x2 - x1)
    return float((min(p[1] for p in sh) - min(p[1] for p in wr)) / ref)


def tu_the(kp, kc):
    """Đứng hay ngồi, theo đùi: đứng thì đùi gần thẳng đứng (đầu gối thấp hơn hông nhiều so với chiều dài
    thân), ngồi thì đùi nằm ngang. Trả 'dung', 'ngoi', hoặc None khi không thấy rõ vai, hông, đầu gối
    (người ngồi sau bàn thường bị che chân: coi như không biết)."""
    sh = [kp[i][1] for i in (LSH, RSH) if kc[i] > 0.4]
    hp = [kp[i][1] for i in (LHI, RHI) if kc[i] > 0.4]
    if not sh or not hp:
        return None
    than = np.mean(hp) - np.mean(sh)
    if than <= 1:
        return None
    goi = [kp[i][1] for i in (LKN, RKN) if kc[i] > 0.4]
    if goi:
        dui = (np.mean(goi) - np.mean(hp)) / than
        if dui > 0.6:
            return 'dung'
        if dui < 0.35:
            return 'ngoi'
    co_chan = [kp[i][1] for i in (LAN, RAN) if kc[i] > 0.4]
    if co_chan and (np.mean(co_chan) - np.mean(hp)) / than > 1.3:
        return 'dung'
    return None


def hai_tay(kp, kc, box):
    """Giơ cả hai tay (vươn vai, duỗi người). Khách gọi thường chỉ giơ một tay.
    Vươn vai thì cổ tay hay ra sau đầu và bị che, nên xét khuỷu tay: hai khuỷu cùng cao hơn vai;
    hoặc hai cổ tay cùng cao hơn vai."""
    x1, y1, x2, y2 = box
    if min(kc[LSH], kc[RSH]) < 0.4:
        return False
    ref = max(abs(kp[LSH][0] - kp[RSH][0]), 0.1 * (y2 - y1))
    sh_y = (kp[LSH][1] + kp[RSH][1]) / 2
    khuyu = min(kc[LEL], kc[REL]) >= 0.3 and kp[LEL][1] < sh_y and kp[REL][1] < sh_y
    # hai cổ tay phải cùng cao hơn đầu: khách gọi một tay, tay kia hay đưa lên ngang mặt (thử trên m01)
    dau = kp[NOSE][1] if kc[NOSE] >= 0.5 else sh_y - 0.6 * ref
    co_tay = min(kc[LWR], kc[RWR]) >= 0.3 and max(kp[LWR][1], kp[RWR][1]) < dau
    return bool(khuyu or co_tay)


# RTMPose (MMPose) chạy trên từng khung người do YOLO tìm: mỗi người được phóng lên 256x192 trước khi tìm khớp,
# nên người ở xa, người bị cắt ở mép vẫn có khung xương. File ONNX tải từ OpenMMLab (bản body7).
RTMPOSE = {
    'rtmpose-s': 'https://download.openmmlab.com/mmpose/v1/projects/rtmposev1/onnx_sdk/'
                 'rtmpose-s_simcc-body7_pt-body7_420e-256x192-acd4a1ef_20230504.zip',
    'rtmpose-m': 'https://download.openmmlab.com/mmpose/v1/projects/rtmposev1/onnx_sdk/'
                 'rtmpose-m_simcc-body7_pt-body7_420e-256x192-e48f03d0_20230504.zip',
    'rtmpose-l': 'https://download.openmmlab.com/mmpose/v1/projects/rtmposev1/onnx_sdk/'
                 'rtmpose-l_simcc-body7_pt-body7_420e-256x192-4dba18fc_20230504.zip',
}


def load_rtmpose(name, device):
    if not name:
        return None
    from rtmlib import RTMPose
    return RTMPose(onnx_model=RTMPOSE[name], model_input_size=(192, 256), backend='onnxruntime',
                   device='cpu' if device == 'cpu' else 'cuda')


def refine_pose(rtm, frame, boxes, kps, kcs, mode):
    """Thay khung xương YOLO bằng khung xương RTMPose. mode 'tat_ca': mọi người;
    'yeu': chỉ người mà YOLO không thấy rõ vai hoặc cổ tay;
    'gan_vai': người YOLO không thấy rõ, hoặc có cổ tay đã lên gần vai (người có thể sắp giơ tay)."""
    if rtm is None or not len(boxes):
        return kps, kcs
    if mode == 'tat_ca':
        sel = list(range(len(boxes)))
    else:
        lim = 1e9 if mode == 'yeu' else -0.6
        sel = [k for k in range(len(boxes))
               if (hl := hand_lift(kps[k], kcs[k], boxes[k])) is None or hl > lim]
    if not sel:
        return kps, kcs
    kp2, sc2 = rtm(frame, bboxes=[list(map(float, boxes[k])) for k in sel])
    kps, kcs = kps.copy(), kcs.copy()
    for j, k in enumerate(sel):
        kps[k] = kp2[j]
        kcs[k] = np.clip(sc2[j], 0, 1)
    return kps, kcs


def refine_luot(rtm, frame, boxes, ids, kps, kcs, cache, fi, k_max=4, max_age=6):
    """RTMPose theo lượt: mỗi khung chỉ chạy RTMPose cho tối đa K người. Người lâu chưa được chạy nhất đi trước;
    người nhỏ (box cao < 150 px), thiếu vai/cổ tay, hoặc cổ tay đã lên gần vai được cộng 2 lượt ưu tiên.
    Người không tới lượt dùng lại khung xương RTMPose lần trước (dời, co giãn theo box hiện tại) nếu chưa quá
    `max_age` khung; không thì giữ khung xương YOLO."""
    if rtm is None or not len(boxes):
        return kps, kcs
    pri = []
    for k in range(len(boxes)):
        tid = int(ids[k])
        age = fi - cache[tid][0] if tid in cache else 99
        hl = hand_lift(kps[k], kcs[k], boxes[k])
        crit = (boxes[k][3] - boxes[k][1]) < 150 or hl is None or hl > -0.6
        pri.append((age + (2 if crit else 0), k))
    sel = [k for _, k in sorted(pri, reverse=True)[:k_max]]
    kps, kcs = kps.copy(), kcs.copy()
    if sel:
        kp2, sc2 = rtm(frame, bboxes=[list(map(float, boxes[k])) for k in sel])
        for j, k in enumerate(sel):
            kps[k] = kp2[j]
            kcs[k] = np.clip(sc2[j], 0, 1)
            cache[int(ids[k])] = (fi, boxes[k].copy(), kps[k].copy(), kcs[k].copy())
    for k in range(len(boxes)):
        tid = int(ids[k])
        if k in sel or tid not in cache or fi - cache[tid][0] > max_age:
            continue
        _, b0, kp0, kc0 = cache[tid]
        b = boxes[k]
        s = (b[3] - b[1]) / max(1.0, b0[3] - b0[1])
        c0 = np.array([(b0[0] + b0[2]) / 2, (b0[1] + b0[3]) / 2])
        c1 = np.array([(b[0] + b[2]) / 2, (b[1] + b[3]) / 2])
        kps[k] = (kp0 - c0) * s + c1
        kcs[k] = kc0
    return kps, kcs


def nearest_table(tables, pt, scale):
    """Bàn gần điểm pt nhất, nếu cách mép bàn không quá `scale` pixel."""
    best, bd = None, -1e9
    for t in tables:
        d = cv2.pointPolygonTest(t.poly, pt, True)
        if d > bd:
            best, bd = t, d
    return best if bd > -scale else None


def ban_on_dinh(state, pid, moi, t, giu_s=0.4):
    """Bàn của một người, có trễ: người đứng giữa hai bàn làm bàn gần nhất nhảy qua lại từng khung,
    nên chỉ đổi bàn khi bàn mới là bàn gần nhất liên tục `giu_s` giây. state: pid -> [bàn, bàn chờ, từ lúc]."""
    st = state.get(pid)
    if st is None:
        state[pid] = [moi, None, t]
        return moi
    if moi is st[0]:
        st[1] = None
        return moi
    if st[1] is not moi:
        st[1], st[2] = moi, t
    if t - st[2] >= giu_s:
        st[0], st[1] = moi, None
    return st[0]


def _iou(a, b):
    x1, y1, x2, y2 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    giao = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    return giao / max(1e-6, (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - giao)


def noi_danh_tinh(ids, boxes, t, alias, seen, giu_s=3.0):
    """Nối mã bám bị đứt thành một người. Bộ bám hay cấp mã mới cho cùng một người sau khi bị che
    một lúc, làm mọi thứ nhớ theo người (nhân viên hay khách, đang giơ tay, bàn đang ngồi) mất sạch
    và nhấp nháy. Mã mới xuất hiện đè lên chỗ một người vừa mất dấu (trong `giu_s` giây) thì coi là
    người đó. alias: mã bám -> mã người; seen: mã người -> (t, box) lần cuối thấy."""
    pids = [alias.get(int(k)) if k >= 0 else int(k) for k in ids]
    dang_co = {p for p in pids if p is not None}
    for k, (tid, b) in enumerate(zip(ids, boxes)):
        if pids[k] is not None:
            continue
        tid = int(tid)
        h = b[3] - b[1]
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        best, bs = None, 0.0
        for pid, (t0, b0) in seen.items():
            if pid in dang_co or t - t0 > giu_s:
                continue
            h0 = b0[3] - b0[1]
            if not 0.6 < h / max(1.0, h0) < 1.6:
                continue
            d = np.hypot(cx - (b0[0] + b0[2]) / 2, cy - (b0[1] + b0[3]) / 2) / max(1.0, h)
            giao = _iou(b, b0)
            diem = max(giao, 0.6 - d) if (giao >= 0.3 or d < 0.25) else 0.0
            if diem > bs:
                best, bs = pid, diem
        pid = tid if best is None else best
        alias[tid] = pid
        pids[k] = pid
        dang_co.add(pid)
    for pid, b in zip(pids, boxes):
        if pid >= 0:
            seen[pid] = (t, b)
    if len(seen) > 400:
        for pid in [p for p, (t0, _) in seen.items() if t - t0 > giu_s]:
            del seen[pid]
    return pids


class Table:
    """Trạng thái một bàn (bản v5, thu_nghiem/trang_thai_ban). Độ bẩn lọc mũ và có trễ (bẩn từ 0,5, sạch
    dưới 0,35); khách mới phải có mặt 1 s, khách rời phải vắng liên tục 5 s (trong lúc chờ bàn vẫn "có khách"),
    đã dọn phải sạch liên tục 3 s. Thời gian giữ là giây ngoài đời; toc = giây ngoài đời / giây video
    (1 với camera thật, ~30 với clip time-lapse, khai trong zones.json)."""
    GIU_VAO, GIU_RA, GIU_SACH = 1.0, 5.0, 3.0   # giây ngoài đời
    BAN, SACH, TAU = 0.5, 0.35, 0.5              # ngưỡng bẩn vào / ra, hằng số EMA (bội số của win)

    def __init__(self, name, pts, toc=1.0):
        self.name = name
        self.poly = np.array(pts, np.float32)
        self.toc = toc
        self.state = None
        self.hien_thi = None   # trạng thái gần nhất đã kết luận: vẫn hiện trên web khi đang dựng lại sau khi video lặp
        self.seam = None       # lúc video lặp: im lặng một lúc rồi nhận trạng thái mới, không phát sự kiện
        self.bo_qua_da_don = False  # bàn bẩn sẵn lúc video lặp: "đã dọn" đầu tiên không phải việc mới
        self.people = deque()  # (t, số người ngồi)
        self.n_now = 0
        self.n_hien = 0        # số người để hiển thị: trung vị cả cửa sổ, không nhảy từng khung
        self.dirty_now = None  # quan sát độ bẩn gần nhất
        self.dirty_f = None    # độ bẩn đã lọc
        self.t_dirty = None
        self.is_dirty = False
        self.t_vao = self.t_ra = self.t_sach = None
        self.nv_t0 = self.nv_last = None   # nhân viên đứng ở bàn: lúc bắt đầu, lúc thấy gần nhất
        self.nv_gui = -1e9                 # lúc gửi "nhân viên tới bàn" gần nhất

    def nhan_vien_toi(self, t, co_mat):
        """Nhân viên (không đang đi ngang) đứng ở bàn đủ 1 s ngoài đời thì báo "nhân viên tới bàn".
        Còn đứng đó thì gửi lại mỗi 5 s, để việc vừa mở trong lúc nhân viên đang ở bàn cũng được đóng.
        Trả None (không gửi), True (lần đầu của lượt tới này) hoặc False (gửi lại)."""
        if not co_mat:
            return None
        if self.nv_last is None or t - self.nv_last > 0.7 / self.toc:   # vắng quá 0,7 s: lượt tới mới
            self.nv_t0 = t
            self.nv_gui = -1e9
        self.nv_last = t
        if t - self.nv_t0 < 1.0 / self.toc or t - self.nv_gui < 5.0 / self.toc:
            return None
        lan_dau = self.nv_gui < 0
        self.nv_gui = t
        return lan_dau

    def reset(self, t=None):
        """Video lặp lại (cảnh quay về đầu clip): dựng lại trạng thái trong im lặng.
        Xoá cửa sổ quan sát, đặt state về None và mở cửa sổ im lặng (seam) để mỗi vòng lặp
        không báo hàng loạt khách rời / khách mới / đã dọn. Trạng thái đang hiện vẫn giữ ở
        hien_thi cho web khỏi nhấp nháy."""
        self.hien_thi = self.state or self.hien_thi
        self.state = None
        self.seam = t
        self.people.clear()
        self.dirty_f = None
        self.t_dirty = None
        self.is_dirty = False
        self.t_vao = self.t_ra = self.t_sach = None
        self.nv_t0 = self.nv_last = None
        self.nv_gui = -1e9

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
        self.n_hien = int(round(float(np.median([k for _, k in self.people]))))
        if t - self.people[0][0] < 0.9 * win:
            return []  # chưa đủ một cửa sổ để kết luận

        occ = np.mean([k > 0 for _, k in self.people])
        dirty = self.is_dirty
        heads = int(np.median([k for _, k in self.people if k > 0] or [0]))
        held = lambda t0, s: t - t0 >= s / self.toc - 1e-9
        if self.seam is not None:
            # Vừa lặp video: nhận trạng thái mới trong im lặng, không phát sự kiện.
            # Chờ đủ lâu để độ bẩn lọc kịp ổn định, nếu không bàn nào cũng "đã dọn xong" một loạt.
            self.hien_thi = 'co_khach' if occ >= 0.5 else ('can_don' if dirty else 'trong')
            if t - self.seam < 4 * win:
                return []
            self.state = self.hien_thi
            self.t_vao = self.t_ra = self.t_sach = None
            # Bàn đã bẩn sẵn ngay khi video quay lại đầu clip: dọn xong cũng không phải việc mới.
            self.bo_qua_da_don = self.state == 'can_don'
            self.seam = None
            return []
        ev = []
        if self.state is None:  # đầu clip: chỉ ghi nhận trạng thái, không báo
            self.state = 'co_khach' if occ >= 0.5 else ('can_don' if dirty else 'trong')
            # Không báo "cần dọn" cho bàn đã bẩn sẵn lúc bật camera: đó không phải việc mới phát sinh,
            # mà bật máy giữa ca thì sẽ báo cả loạt bàn cùng lúc.
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
                    if self.bo_qua_da_don:   # bàn bẩn sẵn lúc video lặp: không phải việc mới
                        self.bo_qua_da_don = False
                    else:
                        ev.append(('da_don', ''))
            else:
                self.t_sach = None
        return ev


# ---------------------------------------------------------------- chạy một clip

def crop(frame, x1, y1, x2, y2, pad):
    h, w = frame.shape[:2]
    x1, y1 = max(0, int(x1 - pad)), max(0, int(y1 - pad))
    x2, y2 = min(w, int(x2 + pad)), min(h, int(y2 + pad))
    return frame[y1:y2, x1:x2]


def run_clip(path, zones, args, out_root, mc=None):
    """path: file video (Path) hoặc camera (chuỗi: số thứ tự webcam, rtsp://..., http://...).
    mc: MayChu để gửi sự kiện, khung hình, trạng thái bàn lên máy chủ (None: chỉ chạy tại chỗ)."""
    is_cam = isinstance(path, str)
    name = args.camera if is_cam else path.stem
    src_name = path if is_cam else path.name
    out = out_root / name
    (out / 'anh_su_kien').mkdir(parents=True, exist_ok=True)
    cfg = zones.get(name, {})
    win = float(cfg.get('xac_nhan_s', args.confirm))
    toc = float(cfg.get('toc', 1.0))  # clip tua nhanh: số giây ngoài đời trong 1 giây video

    pose, pose_name = load_model(args.pose_models)
    det, det_name = load_model(args.det_models)
    hand_m = load_small_model(args.hand_model)
    table_m = load_small_model(args.table_model)
    yoloe_m = load_yoloe(HERE / 'models' / args.yoloe_model) if args.yoloe else None
    if args.yoloe and yoloe_m is None:
        print(f'  không thấy YOLOE {args.yoloe_model}; dùng luật cũ')
    dump = []  # ghi chi tiết từng khung (--dump) để thử ngưỡng mà không phải chạy lại model
    kx = []    # khung xương từng người từng khung (--luu-khung-xuong), dữ liệu train lớp theo thời gian
    staff_m = load_small_model(args.staff_model)
    rtm = load_rtmpose(args.pose_refine, args.device)
    hd = None   # tỉ lệ hành động từng người (--hanh-dong), dùng chung phần ảnh PE-Core với model giơ tay/nhân viên
    if args.hanh_dong:
        from hanh_dong import KEY as HD_KEY, HanhDong
        nen = next((m for m in (hand_m, staff_m) if getattr(m, 'key', None) == HD_KEY), None)
        if nen is None:
            print(f'  --hanh-dong cần model giơ tay hoặc nhân viên dùng {HD_KEY}; bỏ qua')
        else:
            hd = HanhDong(nen)
            from hanh_dong import IDX as HD_IDX
    hand_mode = args.hand_mode or ('hop' if hand_m else 'luat')
    staff_hist = {}  # track id -> deque[(t, xác suất là nhân viên)]
    ms_cls = []
    # Nguồn qua mạng (RTSP camera IP, MJPEG của điện thoại): bảo ffmpeg đừng đệm.
    # Mặc định ffmpeg giữ vài trăm ms đến vài giây để chống giật, ta cần hình gần thời gian thực.
    if is_cam and str(path).startswith(('rtsp://', 'rtmp://', 'http://', 'https://')):
        os.environ.setdefault(
            'OPENCV_FFMPEG_CAPTURE_OPTIONS',
            'rtsp_transport;tcp|fflags;nobuffer|flags;low_delay|max_delay;0|analyzeduration;0',
        )
    cap = cv2.VideoCapture(int(path) if is_cam and path.isdigit() else str(path))
    if is_cam:
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # chỉ giữ khung mới nhất
    if not cap.isOpened():
        raise SystemExit(f'Không mở được nguồn video: {path}')
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    W, H = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    # clip tải trên mạng hay có đoạn giới thiệu ở đầu: bỏ qua (bat_dau_s trong zones.json), nếu không lúc cảnh
    # quán hiện ra mọi bàn cùng báo "khách mới". Thời gian sự kiện tính từ sau đoạn bỏ qua.
    bo_dau = 0 if is_cam else int(float(cfg.get('bat_dau_s', 0)) * fps)
    if bo_dau:
        cap.set(cv2.CAP_PROP_POS_FRAMES, bo_dau)
    ban = cfg.get('ban', {})
    if mc is not None:  # vùng bàn vẽ trên web (máy chủ) được ưu tiên
        ban = mc.load_zones(ban, W, H)
    tables = [Table(k, v, toc=toc) for k, v in ban.items()]
    # model đã xuất có cỡ ảnh cố định: đưa đúng [cao, rộng]; model .pt thì để YOLO tự tính
    pose_sz = args.imgsz if pose_name.endswith('.pt') else rect_size(W, H, args.imgsz)
    det_sz = args.det_imgsz if det_name.endswith('.pt') else rect_size(W, H, args.det_imgsz)
    raw = out / 'raw.mp4'
    vw = None if args.no_video else cv2.VideoWriter(str(raw), cv2.VideoWriter_fourcc(*'mp4v'), fps, (W, H))
    font, small = load_font(22), load_font(16)
    gpu = args.device != "cpu"
    fp16 = dict(half=True) if args.half else {}  # chỉ truyền khi bật, Ultralytics mới báo half là tham số cũ
    # làm mờ mặt trên mọi ảnh rời máy (crop sự kiện, khung live, khung gốc) và trên video kết quả;
    # ảnh sự kiện lưu tại chỗ (anh_su_kien/) để nguyên để còn soát lỗi
    mo_mat = not args.khong_mo_mat

    hist = {}        # track id -> deque[(t, điểm giơ tay, tâm, chiều cao)]
    weak_hist = {}   # track id -> deque[(t, xác suất giơ tay khi cổ tay đã lên trên vai, không thì 0)]
    rtm_cache = {}   # --refine-mode luot: track id -> (khung, box, khung xương RTMPose lần trước)
    last_call = {}   # track id -> lúc báo gọi gần nhất
    alias, seen = {}, {}   # nối mã bám bị đứt thành một người (xem noi_danh_tinh)
    staff_on = {}    # mã người -> đang coi là nhân viên (có trễ: bật từ --staff-on, tắt dưới --staff-off)
    lan_di = {}      # mã người -> lúc gần nhất thấy đang đi (để phân biệt nhân viên vừa tới với người ngồi sẵn)
    the_hist = {}    # mã người -> deque[(t, 'dung'|'ngoi')] trong 1,5 s gần nhất
    vuon_vai = {}    # mã người -> lúc gần nhất giơ cả hai tay (vươn vai)
    hai_tay_q = {}   # mã người -> deque[lúc thấy dáng giơ hai tay] trong 1 s
    ban_truoc = {}   # mã người -> [bàn, bàn chờ đổi, từ lúc] (xem ban_on_dinh)
    # --- gói bằng chứng cho Gemini (chỉ khi có máy chủ): mẫu khung đã làm mờ mặt + bàn sạch
    ev_buf = deque(maxlen=90)      # (t, frame anon) ~3 giây tại 30 fps (đủ cho dải 2x2 quanh sự kiện)
    ev_seq = 0                     # đếm eid của sự kiện cần gói ảnh
    pending_ev = []                # việc đang chờ đủ t+... để gói: dict(t, kind, ban, eid, box, poly, items)
    clean_ref = {}                 # ban -> frame anon lúc bàn mới Trống (để so ảnh 'can_don')
    last_clean_t = {}              # ban -> lúc chụp clean_ref, tránh chụp liên tục
    events, banner = [], []
    ms_pose, ms_det, people_per_frame = [], [], []
    items = []
    track_ids = set()
    timeline = []    # [(t, "TCCD")] trạng thái từng bàn mỗi khung, để chấm điểm
    i = 0
    t_start = time.perf_counter()
    last_live = last_tables = last_raw = -1e9
    proc_fps, t_prev = None, None
    t_wall5 = i_wall5 = None
    stop = []  # Ctrl+C: dừng vòng lặp nhưng vẫn ghi kết quả và gửi nốt sự kiện
    old_sigint = signal.signal(signal.SIGINT, lambda *_: stop.append(1))
    while not stop:
        if args.thoi_gian_thuc and not is_cam:
            # chạy file video đúng tốc độ thật: nhanh quá thì chờ, chậm quá thì bỏ khung như camera thật
            lag = (time.perf_counter() - t_start) - i / fps
            if lag < 0:
                time.sleep(-lag)
            elif lag > 2 / fps:
                for _ in range(int(lag * fps)):
                    if not cap.grab():
                        break
                    i += 1
        ok, frame = cap.read()
        if not ok and args.lap and not is_cam and i > 0:
            cap.set(cv2.CAP_PROP_POS_FRAMES, bo_dau)  # hết video: quay lại đầu, thời gian vẫn chạy tiếp
            ok, frame = cap.read()
            if ok:
                # Cảnh quay về đầu clip nên mọi bàn đổi trạng thái cùng một khung: dựng lại trong im lặng,
                # nếu không mỗi vòng lặp sẽ báo "khách rời" cả loạt rồi "khách mới" cả loạt.
                for tb in tables:
                    tb.reset(i / fps)
                hist.clear()
                weak_hist.clear()
                rtm_cache.clear()
                last_call.clear()
                seen.clear()
                lan_di.clear()
                the_hist.clear()
                vuon_vai.clear()
                hai_tay_q.clear()
                if hd is not None:
                    hd.xoa()
                ban_truoc.clear()
                clean_ref.clear()
                last_clean_t.clear()
        if not ok:
            break
        t = (time.perf_counter() - t_start) if is_cam else i / fps
        now_w = time.perf_counter()
        if t_wall5 is None and i >= 5:
            t_wall5, i_wall5 = now_w, i  # đo fps thật (cả đọc video, model nhỏ, luật, gửi) từ khung thứ 5 (chế độ thời gian thực có thể bỏ khung qua mốc 5)
        if t_prev is not None:
            inst = 1.0 / max(1e-3, now_w - t_prev)
            proc_fps = inst if proc_fps is None else 0.9 * proc_fps + 0.1 * inst
        t_prev = now_w

        t0 = time.perf_counter()
        r = pose.track(frame, persist=True, tracker=args.tracker, classes=[0], conf=0.3,
                       imgsz=pose_sz, device=args.device, verbose=False, **fp16)[0]
        boxes = r.boxes.xyxy.cpu().numpy()
        ids = r.boxes.id.int().cpu().numpy() if r.boxes.id is not None else -np.arange(1, len(boxes) + 1)
        kps = r.keypoints.xy.cpu().numpy() if r.keypoints is not None else np.zeros((len(boxes), 17, 2))
        kcs = r.keypoints.conf.cpu().numpy() if r.keypoints is not None and r.keypoints.conf is not None \
            else np.ones((len(boxes), 17))
        if args.refine_mode == 'luot':
            kps, kcs = refine_luot(rtm, frame, boxes, ids, kps, kcs, rtm_cache, i, args.refine_k)
        else:
            kps, kcs = refine_pose(rtm, frame, boxes, kps, kcs, args.refine_mode)
        dt_pose = (time.perf_counter() - t0) * 1000
        track_ids.update(int(k) for k in ids)
        if len(boxes) and not args.khong_noi:
            ids = np.array(noi_danh_tinh(ids, boxes, t, alias, seen), dtype=int)
        anon = None  # khung đã làm mờ mặt: chỉ tính (một lần mỗi khung) khi có ảnh cần gửi đi hoặc cần vẽ

        def an_danh():
            nonlocal anon
            if anon is None:
                anon = blur_faces(frame, kps, kcs, boxes) if mo_mat else frame
            return anon

        # mẫu khung đã làm mờ mặt cho gói bằng chứng (chỉ khi có máy chủ và có việc đang chờ)
        if mc is not None and i % 2 == 0:
            ev_buf.append((t, an_danh().copy()))

        new_items = None
        if i % args.det_every == 0:
            t0 = time.perf_counter()
            d = det.predict(frame, classes=list(ITEMS), conf=0.25, imgsz=det_sz, **fp16,
                            device=args.device, verbose=False)[0]
            items = [(int(c), *b) for c, b in zip(d.boxes.cls.cpu().numpy(), d.boxes.xyxy.cpu().numpy())]
            new_items = items
            if i >= 5:
                ms_det.append((time.perf_counter() - t0) * 1000)
        if i >= 5:  # bỏ vài khung đầu (khởi động GPU)
            ms_pose.append(dt_pose)
        people_per_frame.append(len(boxes))

        # --- model nhỏ trên ảnh cắt từng người: có giơ tay không, có phải nhân viên không
        t0 = time.perf_counter()
        pcrops = [pad_box(frame, b, 0.08) for b in boxes] if (hand_m or staff_m) else [None] * len(boxes)
        if hand_m is not None and hand_mode == 'hop':
            # chỉ hỏi model giơ tay với người có cổ tay đã lên trên vai (và trên cả mũi nếu thấy mặt):
            # ít người, nên chạy được cả CLIP trên CPU
            sel = [k for k, (b, kp, kc) in enumerate(zip(boxes, kps, kcs))
                   if (hl := hand_lift(kp, kc, b, tren_mui=True)) is not None and hl > 0.3]
            p_hand = [None] * len(boxes)
            for k, v in zip(sel, class_probs(hand_m, [pcrops[k] for k in sel], 'gio_tay')):
                p_hand[k] = v
        else:
            p_hand = class_probs(hand_m, pcrops, 'gio_tay')
        # nhân viên hay khách không đổi từng khung: xét mỗi N khung rồi lấy trung bình 3 giây theo từng người
        # Người mới (chưa đủ 3 lần xét) được xét dồn mỗi 3 khung, để không phải chờ tới lượt mới có nhãn.
        p_staff = [None] * len(boxes)
        if staff_m is not None and len(boxes):
            ca = i % args.staff_every == 0
            # người bị mép khung cắt mất nửa người cho điểm nhân viên cao bất thường: không xét, giữ nhãn cũ
            chon = [k for k, tid in enumerate(ids)
                    if (ca or (i % 3 == 0 and len(staff_hist.get(int(tid), ())) < 3))
                    and boxes[k][0] > 3 and boxes[k][2] < W - 3]
            for k, v in zip(chon, class_probs(staff_m, [pcrops[k] for k in chon], 'nhan_vien')):
                p_staff[k] = v
        if (hand_m or staff_m) and i >= 5 and len(boxes):
            ms_cls.append((time.perf_counter() - t0) * 1000)

        # --- từng người: giơ tay? nhân viên? đang đi hay ngồi? thuộc bàn nào?
        persons = []
        for b, tid, kp, kc, ph, pst in zip(boxes, ids, kps, kcs, p_hand, p_staff):
            tid = int(tid)
            if args.luu_khung_xuong:
                kx.append((t, tid, b, kp, kc, np.nan if ph is None else ph, np.nan if pst is None else pst))
            x1, y1, x2, y2 = b
            h = y2 - y1
            anchor = (float((x1 + x2) / 2), float(y1 + 0.6 * h))
            score = hand_up(kp, kc, b)
            if hand_mode == 'luat':
                up = score > 0
            elif hand_mode == 'model':
                up = (ph or 0) >= args.hand_th
            elif hand_mode == 'ket_hop':  # cách cũ: model chắc chắn, hoặc luật thấy giơ và model không phản đối
                up = (ph or 0) >= args.hand_th or (score > 0 and (ph or 0) >= 0.3)
            else:  # 'hop': luật chặt thấy giơ, HOẶC model thấy giơ (model chỉ chạy khi cổ tay đã lên trên vai)
                up = score > 0 or (ph or 0) >= args.hand_th
            # giơ cả hai tay là vươn vai: không tính là gọi, và chặn thêm 2 s sau đó (lúc hạ tay có khi còn một tay)
            # cần thấy dáng giơ hai tay ít nhất 3 khung trong 1 s, một khung lẻ có thể là khung xương sai
            vq = hai_tay_q.setdefault(tid, deque())
            if hai_tay(kp, kc, b):
                vq.append(t)
            while vq and vq[0] < t - 1.0:
                vq.popleft()
            if len(vq) >= 3:
                vuon_vai[tid] = t
            if t - vuon_vai.get(tid, -1e9) <= 2.0:
                up = False
            q = hist.setdefault(tid, deque())
            q.append((t, up, anchor, h, ph))
            while q and q[0][0] < t - max(1.0, args.hand_s):
                q.popleft()
            moved = np.hypot(q[-1][2][0] - q[0][2][0], q[-1][2][1] - q[0][2][1])
            # đang đi: dời hơn 0,25 chiều cao trong 1 s. Không thêm trễ: thử rồi, khách vừa ngồi xuống
            # bị coi là còn đi thêm ~1 s nên bàn báo "có khách" chậm; số người đã lấy trung vị nên đủ ổn.
            walking = (q[-1][0] - q[0][0]) > 0.5 and moved > 0.25 * h
            if walking or tid not in lan_di:
                lan_di[tid] = t if walking else -1e9
            # đứng hay ngồi (1,5 s gần nhất): người đứng cạnh bàn không phải khách đang ngồi ăn
            th = the_hist.setdefault(tid, deque())
            if (tt_ := tu_the(kp, kc)) is not None:
                th.append((t, tt_))
            while th and th[0][0] < t - 1.5:
                th.popleft()
            n_dung = sum(1 for _, v in th if v == 'dung')
            dung = n_dung >= 2 and n_dung > len(th) - n_dung
            # nhân viên: trung bình 10 s, bật từ --staff-on và chỉ tắt dưới --staff-off, nên không nhấp nháy.
            # Ngưỡng chỉnh cho nhanvien_pe_b16 (nhân viên 0,37-0,68, khách thường dưới 0,35; xem
            # danh_gia/so_nhan_vien.py). Model nhanvien_clip_v1 cũ không tách được: nhân viên và khách đều ~0,4-0,6.
            sq = staff_hist.setdefault(tid, deque())
            if pst is not None:
                sq.append((t, pst))
            while sq and sq[0][0] < t - args.staff_win:
                sq.popleft()
            if sq:
                m_nv = float(np.mean([v for _, v in sq]))
                if staff_on.get(tid):
                    staff_on[tid] = m_nv > args.staff_off
                else:
                    staff_on[tid] = m_nv >= args.staff_on and (len(sq) >= 2 or m_nv >= 0.85)
            staff = bool(staff_on.get(tid))
            recent = [u for tt, u, *_ in q if tt >= t - args.hand_s]
            # chỉ khách đang ngồi mới tính là gọi: người đứng với tay lên kệ, trẻ con trèo ghế không phải gọi phục vụ
            calling = (not staff and not dung and q[-1][0] - q[0][0] >= 0.8 * args.hand_s and np.mean(recent) >= 0.7)
            manh = 0.0  # bằng chứng mạnh nhất của khung này, để hiển thị cho nhân viên
            if args.tich_luy and hand_mode == 'hop':
                # tích luỹ bằng chứng yếu: model chỉ hơi tin (trung bình 1 s >= weak-th) nhưng cổ tay phải
                # cao hơn mũi, nếu không người đang ăn/uống cũng đủ điều kiện và báo nhầm liên tục
                nang = hand_lift(kp, kc, b, tren_mui=True)
                wq = weak_hist.setdefault(tid, deque())
                wq.append((t, (ph or 0) if (nang is not None and nang > 0.3) else 0.0))
                while wq and wq[0][0] < t - 1.0:
                    wq.popleft()
                if (not calling and not staff and not dung and t - vuon_vai.get(tid, -1e9) > 2.0
                        and nang is not None and nang > 0.3 and wq[-1][0] - wq[0][0] >= 0.8
                        and np.mean([v for _, v in wq]) >= args.weak_th):
                    calling = True
                    manh = float(np.mean([v for _, v in wq]))
            # kiểm tra chéo bằng model hành động: giơ tay mà model ảnh không thấy giống "gọi phục vụ" (trẻ con với tay,
            # khách vươn vai, người với lên kệ) thì không báo. Người mới chưa có số thì không chặn.
            # Người bị mép khung cắt thì không chặn: ảnh cắt mất nửa người, model ảnh nhìn không ra là đang giơ tay.
            if calling and hd is not None and b[0] > 3 and b[2] < W - 3:
                kt = hd.hien(('kt', tid))
                if kt is not None and kt[HD_IDX['goi']] < args.hanh_dong_goi:
                    calling = False
            score_show = max(score, float(ph or 0), manh)  # điểm thật sự đã kích hoạt, không phải điểm luật = 0
            tb = ban_on_dinh(ban_truoc, tid, nearest_table(tables, anchor, 0.45 * h), t) if tables else None
            persons.append(dict(id=tid, box=b, kp=kp, kc=kc, walking=walking, staff=staff, t_di=lan_di[tid], dung=dung,
                                calling=calling, score=score_show, table=tb))
            if calling and t - last_call.get(tid, -1e9) > args.call_cooldown:
                last_call[tid] = t
                ev_seq += 1
                eid = f'{name}:{ev_seq}'
                events.append(dict(t=round(t, 2), loai='goi_phuc_vu', ban=tb.name if tb else None,
                                   nguoi=tid, chi_tiet=f'điểm giơ tay {score_show:.2f}',
                                   box=[round(float(v)) for v in b],
                                   diem=round(float(score_show), 3),
                                   eid=eid, _crop=crop(frame, x1, y1, x2, y2, 0.15 * h)))
                if mc is not None:
                    mc.event(events[-1], crop(an_danh(), x1, y1, x2, y2, 0.15 * h))
                    pending_ev.append(dict(t0=t, kind='goi_phuc_vu', ban=tb.name if tb else None,
                                           eid=eid, box=[round(float(v)) for v in b],
                                           poly=None, items=None))

        # --- tỉ lệ hành động từng người: model ảnh-chữ mỗi N khung, gộp với khung xương, làm mượt
        if hd is not None and persons and i % args.hanh_dong_every == 0:
            ok_k = [k for k, c in enumerate(pcrops) if c is not None and c.size]
            for k, pr in zip(ok_k, hd.clip_probs([pcrops[k] for k in ok_k])):
                p = persons[k]
                vuon = t - vuon_vai.get(p['id'], -1e9) <= 2.0
                hd.cap_nhat(p['id'], t, hd.gop(pr, di=p['walking'], dung=p['dung'], nv=p['staff'],
                                                goi=p['calling'], vuon=vuon))
                # bản không dựa vào bộ giơ tay, để kiểm tra chéo trước khi báo "gọi phục vụ"
                hd.cap_nhat(('kt', p['id']), t, hd.gop(pr, di=p['walking'], dung=p['dung'], nv=p['staff'],
                                                       goi=None, vuon=vuon))

        # --- từng bàn: đếm người ngồi (bỏ người đang đi), đếm đồ trên bàn.
        # Mỗi món đồ chỉ thuộc một bàn (bàn chứa tâm món đồ sâu nhất), để ly của
        # bàn bên cạnh nằm sát mép không làm bàn này "bẩn" mãi.
        owner = {}
        if new_items is not None and tables:
            for k, it in enumerate(new_items):
                c = ((it[1] + it[3]) / 2, (it[2] + it[4]) / 2)
                best = max(tables, key=lambda tb: cv2.pointPolygonTest(tb.poly, c, True))
                if cv2.pointPolygonTest(best.poly, c, True) > -12:
                    owner[k] = best
        p_dirty = [None] * len(tables)
        if table_m is not None and tables and i % args.table_every == 0:
            p_dirty = class_probs(table_m, [table_crop(frame, tb.poly) for tb in tables], 'ban')
        yoloe_left = {}  # bàn -> danh sách đồ YOLOE, chỉ có sau sự kiện khách rời của khung này
        for tb, pd in zip(tables, p_dirty):
            n = sum(1 for p in persons if p['table'] is tb and not p['walking'] and not p['staff'] and not p['dung'])
            # nhân viên đứng ở bàn: máy chủ dùng để đóng việc gọi / khách mới và đo thời gian phản hồi
            # chỉ tính người vừa đi tới (đi trong 15 s qua): model nhân viên có lúc nhầm khách ngồi sẵn ở bàn
            # là nhân viên, và khi đó việc của chính bàn đó sẽ bị đóng sai
            nv = [p for p in persons if p['table'] is tb and p['staff'] and not p['walking']
                  and t - p['t_di'] <= 15.0 / tb.toc]
            lan_dau = tb.nhan_vien_toi(t, bool(nv))
            if lan_dau is not None:
                x, y, w_, h_ = cv2.boundingRect(tb.poly.astype(np.int32))
                e_nv = dict(t=round(t, 2), loai='nv_den', ban=tb.name, nguoi=nv[0]['id'],
                            chi_tiet=f'{len(nv)} nhân viên ở bàn', box=[x, y, x + w_, y + h_], eid=None)
                if lan_dau:   # chỉ ghi lần đầu mỗi lượt tới; các lần gửi lại chỉ để máy chủ biết
                    events.append(dict(e_nv, _crop=crop(frame, x, y, x + w_, y + h_, 80)))
                if mc is not None:
                    mc.event(e_nv)
            obs = None
            if table_m is not None:
                obs = pd
            elif new_items is not None:
                obs = float(any(owner.get(k) is tb for k in range(len(new_items))))
            # ảnh bàn lúc sạch: lưu khi bàn mới Trống (để so với ảnh lúc 'can_don')
            if (mc is not None and tb.state == 'trong' and tb.name not in clean_ref
                    and t - last_clean_t.get(tb.name, -1e9) >= 2.0):
                clean_ref[tb.name] = an_danh().copy()
                last_clean_t[tb.name] = t
            for kind, detail in tb.update(t, n, obs, win):
                # YOLOE chỉ chạy khi bàn vừa được xác định là khách đã rời. Với config demo
                # (classifier bàn + --yoloe), bàn bẩn cần cả hai tín hiệu độc lập.
                yoloe_items = yoloe_left.get(tb.name)
                if kind == 'khach_roi' and yoloe_m is not None:
                    yoloe_items = yoloe_table_items(yoloe_m, frame, tb, args)
                    yoloe_left[tb.name] = yoloe_items
                if kind == 'can_don' and yoloe_m is not None:
                    if yoloe_items is None:
                        yoloe_items = yoloe_table_items(yoloe_m, frame, tb, args)
                    if table_m is not None and yoloe_items == []:
                        tb.state = 'trong'
                        continue
                x, y, w_, h_ = cv2.boundingRect(tb.poly.astype(np.int32))
                hoan_thanh = kind == 'da_don'    # bàn đã dọn: chụp clean_ref mới cho lần sau
                ev_seq += 1
                eid = f'{name}:{ev_seq}' if kind in ('goi_phuc_vu', 'can_don') else None
                items_ev = (_hien_yoloe(yoloe_items) if yoloe_items is not None else _hien_items(items)) \
                    if kind == 'can_don' else None
                if kind == 'can_don' and items_ev:
                    detail = f"{detail}: {_text_items(items_ev)}"
                events.append(dict(t=round(t, 2), loai=kind, ban=tb.name, nguoi=None, chi_tiet=detail,
                                   box=[x, y, x + w_, y + h_], eid=eid,
                                   items=items_ev,
                                   _crop=crop(frame, x, y, x + w_, y + h_, 80)))
                if mc is not None:
                    mc.event(events[-1], crop(an_danh(), x, y, x + w_, y + h_, 80))
                    if eid:
                        pending_ev.append(dict(t0=t, kind=kind, ban=tb.name, eid=eid,
                                               box=[x, y, x + w_, y + h_],
                                               poly=tb.poly, items=items_ev))
                if hoan_thanh and mc is not None:
                    clean_ref[tb.name] = an_danh().copy()
                    last_clean_t[tb.name] = t
        if tables:
            timeline.append([round(t, 3), ''.join(CODE.get(tb.state, '?') for tb in tables)])
        if args.dump:
            dump.append(dict(
                t=round(t, 3),
                nguoi=[dict(id=p['id'], box=[round(float(v)) for v in p['box']], luat=round(float(hand_up(p['kp'], p['kc'], p['box'])), 3),
                            nang=None if (hl := hand_lift(p['kp'], p['kc'], p['box'])) is None else round(hl, 3),
                            ph=None if ph is None else round(ph, 3), pst=None if ps is None else round(ps, 3),
                            di=bool(p['walking']), nv=bool(p['staff']), goi=bool(p['calling']), dung=bool(p['dung']),
                            hd=None if hd is None else [[c, round(v, 3)] for c, v in __import__('hanh_dong').top(hd.hien(p['id']), 3)],
                            kt=None if hd is None or hd.hien(('kt', p['id'])) is None
                            else round(float(hd.hien(('kt', p['id']))[HD_IDX['goi']]), 3),
                            ban=p['table'].name if p['table'] else None)
                       for p, ph, ps in zip(persons, p_hand, p_staff)],
                ban={tb.name: dict(n=sum(1 for p in persons if p['table'] is tb and not p['walking'] and not p['staff'] and not p['dung']), nh=tb.n_hien,
                                   pd=None if pd is None else round(pd, 3),
                                   do=None if new_items is None else int(any(owner.get(k) is tb for k in range(len(new_items)))))
                     for tb, pd in zip(tables, p_dirty)}))

        send_live = False
        if mc is not None:
            now_w = time.perf_counter()
            if (nz := mc.new_zones()) is not None:  # vừa vẽ/sửa vùng bàn trên web: áp dụng từ khung sau
                tables = [Table(k, v, toc=toc) for k, v in nz.items()]
                timeline = []  # thứ tự bàn đã đổi
                last_tables = -1e9
            if tables and now_w - last_tables >= 1.0:
                mc.tables(tables)
                last_tables = now_w
            if now_w - last_raw >= 30:  # ảnh gốc không vẽ gì, để vẽ vùng bàn trên web
                mc.frame_raw(an_danh(), source=src_name)
                last_raw = now_w
            send_live = now_w - last_live >= 0.25
            # gói bằng chứng tới hạn (chờ đủ t+... để có khung t+0.5)
            if pending_ev and ev_buf and t - min(p['t0'] for p in pending_ev) >= EVIDENCE_DELAY_S:
                buf = list(ev_buf)
                keep = []
                for p in pending_ev:
                    if t - p['t0'] >= EVIDENCE_DELAY_S:
                        _dong_goi(mc, p['eid'], p['kind'], p['ban'], buf, p['t0'],
                                  W, H, clean_ref, p.get('items'), box=p.get('box'), poly=p.get('poly'))
                    else:
                        keep.append(p)
                pending_ev = keep
        if vw is None and not send_live:  # chỉ chấm điểm: bỏ phần vẽ và ghi video
            i += 1
            continue
        # --- vẽ
        vis = an_danh().copy()
        for tb in tables:
            col = BGR.get(tb.state or 'trong')
            cv2.polylines(vis, [tb.poly.astype(np.int32)], True, col, 3)
        for it in items:
            _, a, b_, c, d_ = it
            cv2.rectangle(vis, (int(a), int(b_)), (int(c), int(d_)), BGR['item'], 1)
        for p in persons:
            x1, y1, x2, y2 = map(int, p['box'])
            col = (BGR['goi'] if p['calling'] else BGR['nv'] if p['staff'] else BGR['di'] if p['walking']
                   else BGR['co_khach'])
            cv2.rectangle(vis, (x1, y1), (x2, y2), col, 4 if p['calling'] else 2)
            if p['calling']:
                for a, b_ in ((LSH, LEL), (LEL, LWR), (RSH, REL), (REL, RWR)):
                    if p['kc'][a] > 0.4 and p['kc'][b_] > 0.4:
                        cv2.line(vis, tuple(map(int, p['kp'][a])), tuple(map(int, p['kp'][b_])), BGR['goi'], 3)
        if hd is not None:
            from hanh_dong import LABELS as HD_LABELS, top as hd_top
        newest = [e for e in events if e['t'] > t - 2.5]
        img = Image.fromarray(cv2.cvtColor(vis, cv2.COLOR_BGR2RGB))
        dr = ImageDraw.Draw(img)
        for tb in tables:
            x, y = tb.poly[0]
            label = f'{tb.name}: {STATE_VI.get(tb.state, "đang xem")}' + (f' ({tb.n_now})' if tb.n_now else '')
            dr.text((x, y - 24), label, font=small, fill=BGR[tb.state or 'trong'][::-1],
                    stroke_width=3, stroke_fill=(0, 0, 0))
        for p in persons:
            x1, y1 = p['box'][:2]
            tag = f"#{p['id']}" + (' GỌI' if p['calling'] else ' NV' if p['staff'] else ' đi' if p['walking'] else '')
            dr.text((x1 + 3, y1 + 2), tag, font=small, fill=(255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))
            if hd is not None:
                for k, (c, v) in enumerate(hd_top(hd.hien(p['id']), 2)):
                    dr.text((x1 + 3, y1 + 24 + 20 * k), f'{HD_LABELS[c]} {v:.0%}', font=small,
                            fill=(255, 235, 120) if k == 0 else (220, 220, 220), stroke_width=2, stroke_fill=(0, 0, 0))
        for k, e in enumerate(newest[-3:]):
            msg = f"{e['t']:.1f}s  {EVENT_VI[e['loai']]}" + (f" (bàn {e['ban']})" if e['ban'] else '')
            dr.rectangle((10, 10 + k * 34, 30 + dr.textlength(msg, font=font), 40 + k * 34), fill=(200, 30, 30))
            dr.text((20, 12 + k * 34), msg, font=font, fill=(255, 255, 255))
        perf = (f"{'GPU' if gpu else 'CPU'}  người+khung xương {dt_pose:.0f} ms"
                + (f"  đồ trên bàn {ms_det[-1]:.0f} ms" if ms_det else '')
                + (f"  model nhỏ {ms_cls[-1]:.0f} ms" if ms_cls else ''))
        dr.text((10, H - 28), perf, font=small, fill=(255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))
        bgr = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)
        if vw is not None:
            vw.write(bgr)
        if send_live:
            mc.frame_live(bgr, fps=proc_fps, source=src_name)
            last_live = time.perf_counter()
        i += 1

    t_wall_end = time.perf_counter()
    signal.signal(signal.SIGINT, old_sigint)
    # gói bằng chứng còn sót (sự kiện ở cuối clip, chưa đủ t+...): gói với khung đã có
    if mc is not None and pending_ev and ev_buf:
        buf = list(ev_buf)
        for p in pending_ev:
            _dong_goi(mc, p['eid'], p['kind'], p['ban'], buf, p['t0'],
                      W, H, clean_ref, p.get('items'), box=p.get('box'), poly=p.get('poly'))
        pending_ev = []
    if stop:
        print('  đã dừng (Ctrl+C)')
    cap.release()
    if vw is not None:
        vw.release()
        final = out / 'video_ket_qua.mp4'
        if shutil.which('ffmpeg'):
            subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', str(raw), '-c:v', 'libx264', '-preset',
                            'veryfast', '-crf', '26', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(final)],
                           check=True)
            raw.unlink()
        else:
            raw.rename(final)

    for k, e in enumerate(events, 1):
        f = out / 'anh_su_kien' / f"{k:02d}_{e['t']:05.1f}s_{e['loai']}.jpg"
        cv2.imwrite(str(f), e.pop('_crop'))
        e['anh'] = f.relative_to(out_root).as_posix()
    mp = float(np.mean(ms_pose)) if ms_pose else 0.0
    md = float(np.mean(ms_det)) if ms_det else 0.0
    summary = dict(
        clip=src_name, so_khung=i, do_dai_s=round(i / fps, 1), thiet_bi='GPU' if gpu else 'CPU',
        model_nguoi=pose_name, model_do_vat=det_name,
        model_gio_tay=args.hand_model, cach_gio_tay=hand_mode, model_ban=args.table_model,
        model_nhan_vien=args.staff_model, bo_bam=Path(args.tracker).name, bo_ma_hoa_ban=args.clip_backbone,
        khung_xuong_them=args.pose_refine and f'{args.pose_refine} ({args.refine_mode})',
        ms_nguoi=round(mp, 1), ms_do_vat=round(md, 1),
        ms_model_nho=round(float(np.mean(ms_cls)), 1) if ms_cls else None,
        khung_moi_giay=round(1000 / (mp + md / args.det_every), 1) if mp else None,
        fps_thuc=round((i - i_wall5) / (t_wall_end - t_wall5), 1) if t_wall5 is not None and i - i_wall5 > 5 else None,
        vram_torch_mb=round(torch.cuda.max_memory_reserved() / 2**20) if gpu and torch.cuda.is_available() else None,
        nguoi_tb=round(float(np.mean(people_per_frame)), 1) if people_per_frame else 0,
        nguoi_max=int(max(people_per_frame, default=0)), so_track=len(track_ids),
        co_vung_ban=bool(tables), su_kien=events,
        trang_thai_ban=dict(thu_tu=[tb.name for tb in tables], khung=timeline) if tables else None,
    )
    (out / 'su_kien.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    if args.dump:
        (out / 'chi_tiet.json').write_text(json.dumps(dict(fps=fps, win=win, khung=dump), ensure_ascii=False),
                                           encoding='utf-8')
    if args.luu_khung_xuong:
        # mỗi dòng là một người ở một khung: thời điểm, mã track, khung người, 17 điểm (x, y), độ tin cậy,
        # điểm model giơ tay (NaN khi không hỏi), điểm nhân viên (NaN khi không xét)
        cols = list(zip(*kx)) if kx else [[]] * 7
        np.savez_compressed(
            out / 'khung_xuong.npz',
            t=np.asarray(cols[0], np.float32), id=np.asarray(cols[1], np.int32),
            box=np.asarray(cols[2], np.float32).reshape(-1, 4), kp=np.asarray(cols[3], np.float32).reshape(-1, 17, 2),
            kc=np.asarray(cols[4], np.float32).reshape(-1, 17), ph=np.asarray(cols[5], np.float32),
            pst=np.asarray(cols[6], np.float32), fps=fps, rong=W, cao=H)
    return summary


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('src', help='file video, thư mục chứa video, hoặc camera: số webcam (0) / rtsp://... / http://...')
    ap.add_argument('--zones', type=Path, default=HERE / 'zones.json', help='vùng bàn của từng clip')
    ap.add_argument('--out', type=Path, default=HERE / 'out')
    ap.add_argument('--device', default='0' if torch.cuda.is_available() else 'cpu')
    ap.add_argument('--imgsz', type=int, default=960, help='cỡ ảnh cho model người')
    ap.add_argument('--det-imgsz', type=int, default=1280, help='cỡ ảnh cho model đồ vật (đồ nhỏ cần ảnh to)')
    ap.add_argument('--det-every', type=int, default=3, help='chạy model đồ vật mỗi N khung')
    ap.add_argument('--confirm', type=float, default=1.0, help='giây xác nhận đổi trạng thái bàn')
    ap.add_argument('--hand-s', type=float, default=0.6, help='giây giơ tay liên tục mới báo')
    ap.add_argument('--call-cooldown', type=float, default=5.0)
    ap.add_argument('--pose-models', nargs='+', default=['yolo26n-pose.pt', 'yolo11n-pose.pt'])
    ap.add_argument('--det-models', nargs='+', default=['yolo26s.pt', 'yolo11s.pt'])
    ap.add_argument('--hand-model', default=None, help='model nhỏ "có giơ tay không" trong models/, ví dụ gio_tay_v1.pt')
    ap.add_argument('--hand-mode', choices=['luat', 'model', 'ket_hop', 'hop'], default=None,
                    help='luat: chỉ khung xương; model: chỉ model nhỏ; ket_hop: cách cũ (báo nhầm nhiều); '
                         'hop: luật, hoặc model + cổ tay trên vai (mặc định khi có model)')
    ap.add_argument('--hand-th', type=float, default=0.5, help='ngưỡng xác suất giơ tay của model nhỏ')
    ap.add_argument('--table-model', default=None,
                    help='model "bàn sạch hay bẩn" thay cho luật đếm đồ: file YOLO-cls trong models/, '
                         '"clip" (CLIP không train) hoặc ban_clip_*.pt (CLIP + lớp nhỏ đã học)')
    ap.add_argument('--yoloe', action='store_true',
                    help='sau khi khách rời, xác nhận đồ còn trên bàn bằng YOLOE trước khi báo cần dọn')
    ap.add_argument('--yoloe-model', default='yoloe-26s-seg_21lop_736x1280_fp16.engine',
                    help='engine YOLOE trong models/ đã xuất cho GPU này')
    ap.add_argument('--yoloe-imgsz', type=int, default=1280, help='cỡ ảnh YOLOE (chỉ chạy sau khách rời)')
    ap.add_argument('--yoloe-conf', type=float, default=0.25, help='ngưỡng nhận đồ YOLOE')
    ap.add_argument('--dump', action='store_true', help='ghi chi_tiet.json (từng người, từng bàn, từng khung)')
    ap.add_argument('--luu-khung-xuong', action='store_true',
                    help='ghi khung_xuong.npz: 17 điểm của từng người từng khung, để train lớp theo thời gian')
    ap.add_argument('--table-every', type=int, default=4, help='chạy model bàn mỗi N khung')
    ap.add_argument('--staff-model', default=None,
                    help='model "nhân viên hay khách": file YOLO-cls hoặc nhanvien_clip_*.pt (CLIP + lớp nhỏ)')
    ap.add_argument('--staff-win', type=float, default=10.0, help='nhớ kết quả nhân viên/khách trong bao nhiêu giây')
    ap.add_argument('--staff-on', type=float, default=0.40, help='điểm nhân viên trung bình để bật nhãn nhân viên')
    ap.add_argument('--staff-off', type=float, default=0.32, help='điểm trung bình dưới mức này thì tắt nhãn nhân viên')
    ap.add_argument('--khong-noi', action='store_true', help='tắt nối mã bám bị đứt thành một người (để so sánh)')
    ap.add_argument('--staff-every', type=int, default=6, help='xét nhân viên/khách mỗi N khung')
    ap.add_argument('--half', action='store_true', help='chạy model .pt bằng FP16 trên GPU')
    ap.add_argument('--no-video', action='store_true', help='không ghi video kết quả (chỉ cần chấm điểm)')
    ap.add_argument('--pose-refine', choices=list(RTMPOSE), default=None,
                    help='chạy thêm RTMPose trên từng người để có khung xương tốt hơn')
    ap.add_argument('--refine-mode', choices=['tat_ca', 'yeu', 'gan_vai', 'luot'], default='tat_ca',
                    help='tat_ca: mọi người; yeu: chỉ người YOLO không thấy rõ vai/cổ tay; '
                         'gan_vai: thêm người có cổ tay đã lên gần vai; '
                         'luot: tối đa --refine-k người mỗi khung theo lượt, người khác dùng lại khung xương lần trước')
    ap.add_argument('--refine-k', type=int, default=4, help='luot: số người chạy RTMPose mỗi khung')
    ap.add_argument('--hanh-dong', action='store_true',
                    help='hiện tỉ lệ hành động từng người (ngồi ăn, uống, điện thoại, gọi, vươn vai, đi, đứng...)')
    ap.add_argument('--hanh-dong-every', type=int, default=10, help='tính tỉ lệ hành động mỗi N khung')
    ap.add_argument('--hanh-dong-goi', type=float, default=0.25,
                    help='với --hanh-dong: chỉ báo gọi khi model hành động cho "giơ tay gọi" từ mức này (0 = tắt kiểm tra chéo)')
    ap.add_argument('--tich-luy', action='store_true',
                    help='thêm đường báo giơ tay khi model chỉ hơi tin nhưng kéo dài: trung bình 1 s >= --weak-th '
                         'với cổ tay đã lên trên vai')
    ap.add_argument('--weak-th', type=float, default=0.25, help='ngưỡng của --tich-luy')
    ap.add_argument('--tracker', default='bytetrack.yaml',
                    help='bộ bám người: bytetrack.yaml, botsort.yaml, tracktrack.yaml... hoặc file .yaml trong models/')
    ap.add_argument('--may-chu', default=None,
                    help='địa chỉ máy chủ Easy FnB, ví dụ http://localhost:8080: gửi sự kiện, hình, trạng thái bàn lên web')
    ap.add_argument('--camera', default='cam1', help='mã camera trên máy chủ')
    ap.add_argument('--khong-mo-mat', action='store_true',
                    help='không làm mờ mặt khách trên ảnh gửi máy chủ / video kết quả (chỉ để soát lỗi)')
    ap.add_argument('--khoa', default=os.environ.get('EDGE_KEY'), help='X-Edge-Key nếu máy chủ có đặt EDGE_KEY')
    ap.add_argument('--thoi-gian-thuc', action='store_true',
                    help='chạy file video đúng tốc độ thật (như camera đang quay), dùng khi demo với máy chủ')
    ap.add_argument('--lap', action='store_true', help='hết video thì chạy lại từ đầu (demo liên tục), Ctrl+C để dừng')
    ap.add_argument('--clip-backbone', default='b32_laion',
                    help='bộ mã hoá cho bàn không train (--table-model clip); lớp nhỏ .pt tự nhớ bộ mã hoá của nó')
    args = ap.parse_args()
    from clip_cls import set_default
    set_default(args.clip_backbone)
    if (HERE / 'models' / args.tracker).exists():
        args.tracker = str(HERE / 'models' / args.tracker)

    zones = json.loads(args.zones.read_text(encoding='utf-8')) if args.zones.exists() else {}
    src = Path(args.src)
    if args.src.isdigit() or '://' in args.src:
        clips = [args.src]  # camera thật
    elif src.is_dir():
        # tìm cả trong thư mục con (du_lieu_quay/<phiên>/<phiên>.mp4), bỏ video kết quả của chính pipeline
        out_dir = args.out.resolve()
        clips = sorted(p for p in src.rglob('*.mp4')
                       if out_dir not in p.resolve().parents and p.name not in ('video_ket_qua.mp4', 'raw.mp4'))
    else:
        clips = [src]
    mc = None
    if args.may_chu:
        from gui_may_chu import MayChu
        mc = MayChu(args.may_chu, args.camera, args.khoa)
        print(f'Gửi kết quả lên {args.may_chu} (camera {args.camera})')
    args.out.mkdir(parents=True, exist_ok=True)
    results = []
    for c in clips:
        s = run_clip(c, zones, args, args.out, mc)
        n = len(s['su_kien'])
        print(f"{s['clip']}: {s['so_khung']} khung, người {s['ms_nguoi']} ms + đồ vật {s['ms_do_vat']} ms, "
              f"~{s['khung_moi_giay']} khung/giây (thật {s['fps_thuc']}), {n} sự kiện", flush=True)
        for e in s['su_kien']:
            print(f"    {e['t']:6.2f}s  {EVENT_VI[e['loai']]:<18} bàn={e['ban']}  {e['chi_tiet']}")
        results.append(s)
    if mc is not None:
        mc.close()
    tag = 'cpu' if args.device == 'cpu' else 'gpu'
    (args.out / f'tong_hop_{tag}.json').write_text(json.dumps(results, ensure_ascii=False, indent=2),
                                                  encoding='utf-8')


if __name__ == '__main__':
    main()
