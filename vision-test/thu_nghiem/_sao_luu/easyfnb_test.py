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

from fnb_common import pad_box, rect_size, square

HERE = Path(__file__).resolve().parent

# Đồ thường còn lại trên bàn sau khi khách ăn xong (mã lớp COCO)
ITEMS = {39: 'chai', 40: 'ly', 41: 'cốc', 42: 'nĩa', 43: 'dao', 44: 'muỗng', 45: 'tô',
         46: 'chuối', 47: 'táo', 48: 'bánh mì', 49: 'cam', 50: 'rau', 51: 'cà rốt',
         52: 'xúc xích', 53: 'pizza', 54: 'bánh', 55: 'bánh ngọt'}
NOSE, LSH, RSH, LEL, REL, LWR, RWR = 0, 5, 6, 7, 8, 9, 10

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


def hand_lift(kp, kc, box):
    """Luật nới lỏng: cổ tay cao hơn vai bao nhiêu (theo bề ngang vai), không xét khuỷu tay, mũi.

    Dùng để model nhỏ không báo giơ tay khi khung xương cho thấy tay vẫn ở dưới vai.
    Trả None khi không thấy rõ vai hoặc cổ tay nào (người bị che, ở mép hình).
    """
    x1, y1, x2, y2 = box
    sh = [kp[i] for i in (LSH, RSH) if kc[i] > 0.5]
    wr = [kp[i] for i in (LWR, RWR) if kc[i] > 0.3]
    if not sh or not wr:
        return None
    ref = max(abs(kp[LSH][0] - kp[RSH][0]), 0.1 * (y2 - y1)) if len(sh) == 2 else 0.3 * (x2 - x1)
    return float((min(p[1] for p in sh) - min(p[1] for p in wr)) / ref)


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


def nearest_table(tables, pt, scale):
    """Bàn gần điểm pt nhất, nếu cách mép bàn không quá `scale` pixel."""
    best, bd = None, -1e9
    for t in tables:
        d = cv2.pointPolygonTest(t.poly, pt, True)
        if d > bd:
            best, bd = t, d
    return best if bd > -scale else None


class Table:
    def __init__(self, name, pts):
        self.name = name
        self.poly = np.array(pts, np.float32)
        self.state = None
        self.people = deque()  # (t, số người ngồi)
        self.dirty = deque()   # (t, độ bẩn 0..1): có đồ hay không (luật) hoặc xác suất "bẩn" (model)
        self.n_now = 0
        self.dirty_now = None

    def update(self, t, n, dirty_obs, win):
        """Cập nhật một khung hình, trả về danh sách (loại sự kiện, chi tiết)."""
        self.n_now = n
        self.people.append((t, n))
        while self.people and self.people[0][0] < t - win:
            self.people.popleft()
        if dirty_obs is not None:
            self.dirty.append((t, dirty_obs))
            self.dirty_now = dirty_obs
        while self.dirty and self.dirty[0][0] < t - win:
            self.dirty.popleft()
        if t - self.people[0][0] < 0.9 * win:
            return []  # chưa đủ một cửa sổ để kết luận

        occ = np.mean([k > 0 for _, k in self.people])
        dirty = bool(self.dirty) and np.mean([v for _, v in self.dirty]) >= 0.5
        heads = int(np.median([k for _, k in self.people if k > 0] or [0]))
        ev = []
        if self.state is None:  # đầu clip: chỉ ghi nhận trạng thái
            self.state = 'co_khach' if occ >= 0.5 else ('can_don' if dirty else 'trong')
            if self.state == 'can_don':
                ev.append(('can_don', 'đầu clip đã có đồ trên bàn, không có khách'))
        elif self.state != 'co_khach' and occ >= 0.8:
            self.state = 'co_khach'
            ev.append(('khach_moi', f'{heads} người'))
        elif self.state == 'co_khach' and occ <= 0.2:
            ev.append(('khach_roi', ''))
            self.state = 'can_don' if dirty else 'trong'
            if dirty:
                ev.append(('can_don', 'còn đồ trên bàn sau khi khách đi'))
        elif self.state == 'can_don' and not dirty and occ <= 0.2:
            self.state = 'trong'
            ev.append(('da_don', ''))
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

    pose, pose_name = load_model(args.pose_models)
    det, det_name = load_model(args.det_models)
    hand_m = load_small_model(args.hand_model)
    table_m = load_small_model(args.table_model)
    dump = []  # ghi chi tiết từng khung (--dump) để thử ngưỡng mà không phải chạy lại model
    kx = []    # khung xương từng người từng khung (--luu-khung-xuong), dữ liệu train lớp theo thời gian
    staff_m = load_small_model(args.staff_model)
    rtm = load_rtmpose(args.pose_refine, args.device)
    hand_mode = args.hand_mode or ('hop' if hand_m else 'luat')
    staff_hist = {}  # track id -> deque[(t, xác suất là nhân viên)]
    ms_cls = []
    cap = cv2.VideoCapture(int(path) if is_cam and path.isdigit() else str(path))
    if not cap.isOpened():
        raise SystemExit(f'Không mở được nguồn video: {path}')
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    W, H = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    ban = cfg.get('ban', {})
    if mc is not None:  # vùng bàn vẽ trên web (máy chủ) được ưu tiên
        ban = mc.load_zones(ban, W, H)
    tables = [Table(k, v) for k, v in ban.items()]
    # model đã xuất có cỡ ảnh cố định: đưa đúng [cao, rộng]; model .pt thì để YOLO tự tính
    pose_sz = args.imgsz if pose_name.endswith('.pt') else rect_size(W, H, args.imgsz)
    det_sz = args.det_imgsz if det_name.endswith('.pt') else rect_size(W, H, args.det_imgsz)
    raw = out / 'raw.mp4'
    vw = None if args.no_video else cv2.VideoWriter(str(raw), cv2.VideoWriter_fourcc(*'mp4v'), fps, (W, H))
    font, small = load_font(22), load_font(16)
    gpu = args.device != "cpu"
    fp16 = dict(half=True) if args.half else {}  # chỉ truyền khi bật, Ultralytics mới báo half là tham số cũ

    hist = {}        # track id -> deque[(t, điểm giơ tay, tâm, chiều cao)]
    last_call = {}   # track id -> lúc báo gọi gần nhất
    events, banner = [], []
    ms_pose, ms_det, people_per_frame = [], [], []
    items = []
    track_ids = set()
    timeline = []    # [(t, "TCCD")] trạng thái từng bàn mỗi khung, để chấm điểm
    i = 0
    t_start = time.perf_counter()
    last_live = last_tables = last_raw = -1e9
    proc_fps, t_prev = None, None
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
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # hết video: quay lại đầu, thời gian vẫn chạy tiếp
            ok, frame = cap.read()
        if not ok:
            break
        t = (time.perf_counter() - t_start) if is_cam else i / fps
        now_w = time.perf_counter()
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
        kps, kcs = refine_pose(rtm, frame, boxes, kps, kcs, args.refine_mode)
        dt_pose = (time.perf_counter() - t0) * 1000

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
            # chỉ hỏi model giơ tay với người có cổ tay đã lên trên vai: ít người, nên chạy được cả CLIP trên CPU
            sel = [k for k, (b, kp, kc) in enumerate(zip(boxes, kps, kcs))
                   if (hl := hand_lift(kp, kc, b)) is not None and hl > 0.3]
            p_hand = [None] * len(boxes)
            for k, v in zip(sel, class_probs(hand_m, [pcrops[k] for k in sel], 'gio_tay')):
                p_hand[k] = v
        else:
            p_hand = class_probs(hand_m, pcrops, 'gio_tay')
        # nhân viên hay khách không đổi từng khung: xét mỗi N khung rồi lấy trung bình 3 giây theo từng người
        p_staff = class_probs(staff_m if i % args.staff_every == 0 else None, pcrops, 'nhan_vien')
        if (hand_m or staff_m) and i >= 5 and len(boxes):
            ms_cls.append((time.perf_counter() - t0) * 1000)

        # --- từng người: giơ tay? nhân viên? đang đi hay ngồi? thuộc bàn nào?
        persons = []
        for b, tid, kp, kc, ph, pst in zip(boxes, ids, kps, kcs, p_hand, p_staff):
            tid = int(tid)
            track_ids.add(tid)
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
            q = hist.setdefault(tid, deque())
            q.append((t, up, anchor, h, ph))
            while q and q[0][0] < t - max(1.0, args.hand_s):
                q.popleft()
            moved = np.hypot(q[-1][2][0] - q[0][2][0], q[-1][2][1] - q[0][2][1])
            walking = (q[-1][0] - q[0][0]) > 0.5 and moved > 0.25 * h
            sq = staff_hist.setdefault(tid, deque())
            if pst is not None:
                sq.append((t, pst))
            while sq and sq[0][0] < t - 3.0:
                sq.popleft()
            staff = bool(sq) and np.mean([v for _, v in sq]) >= 0.5
            recent = [u for tt, u, *_ in q if tt >= t - args.hand_s]
            calling = (not staff and q[-1][0] - q[0][0] >= 0.8 * args.hand_s and np.mean(recent) >= 0.7)
            tb = nearest_table(tables, anchor, 0.45 * h) if tables else None
            persons.append(dict(id=tid, box=b, kp=kp, kc=kc, walking=walking, staff=staff,
                                calling=calling, score=score if hand_mode == 'luat' else (ph or 0), table=tb))
            if calling and t - last_call.get(tid, -1e9) > args.call_cooldown:
                last_call[tid] = t
                events.append(dict(t=round(t, 2), loai='goi_phuc_vu', ban=tb.name if tb else None,
                                   nguoi=tid, chi_tiet=f'điểm giơ tay {score:.2f}',
                                   box=[round(float(v)) for v in b],
                                   diem=round(float(ph if ph is not None else score), 3),
                                   _crop=crop(frame, x1, y1, x2, y2, 0.15 * h)))
                if mc is not None:
                    mc.event(events[-1], events[-1]['_crop'])

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
        for tb, pd in zip(tables, p_dirty):
            n = sum(1 for p in persons if p['table'] is tb and not p['walking'] and not p['staff'])
            obs = None
            if table_m is not None:
                obs = pd
            elif new_items is not None:
                obs = float(any(owner.get(k) is tb for k in range(len(new_items))))
            for kind, detail in tb.update(t, n, obs, win):
                x, y, w_, h_ = cv2.boundingRect(tb.poly.astype(np.int32))
                events.append(dict(t=round(t, 2), loai=kind, ban=tb.name, nguoi=None, chi_tiet=detail,
                                   box=[x, y, x + w_, y + h_], _crop=crop(frame, x, y, x + w_, y + h_, 80)))
                if mc is not None:
                    mc.event(events[-1], events[-1]['_crop'])
        if tables:
            timeline.append([round(t, 3), ''.join(CODE.get(tb.state, '?') for tb in tables)])
        if args.dump:
            dump.append(dict(
                t=round(t, 3),
                nguoi=[dict(id=p['id'], box=[round(float(v)) for v in p['box']], luat=round(float(hand_up(p['kp'], p['kc'], p['box'])), 3),
                            nang=None if (hl := hand_lift(p['kp'], p['kc'], p['box'])) is None else round(hl, 3),
                            ph=None if ph is None else round(ph, 3), pst=None if ps is None else round(ps, 3),
                            di=bool(p['walking']), ban=p['table'].name if p['table'] else None)
                       for p, ph, ps in zip(persons, p_hand, p_staff)],
                ban={tb.name: dict(n=sum(1 for p in persons if p['table'] is tb and not p['walking'] and not p['staff']),
                                   pd=None if pd is None else round(pd, 3),
                                   do=None if new_items is None else int(any(owner.get(k) is tb for k in range(len(new_items)))))
                     for tb, pd in zip(tables, p_dirty)}))

        send_live = False
        if mc is not None:
            now_w = time.perf_counter()
            if (nz := mc.new_zones()) is not None:  # vừa vẽ/sửa vùng bàn trên web: áp dụng từ khung sau
                tables = [Table(k, v) for k, v in nz.items()]
                timeline = []  # thứ tự bàn đã đổi
                last_tables = -1e9
            if tables and now_w - last_tables >= 1.0:
                mc.tables(tables)
                last_tables = now_w
            if now_w - last_raw >= 30:  # ảnh gốc không vẽ gì, để vẽ vùng bàn trên web
                mc.frame_raw(frame, source=src_name)
                last_raw = now_w
            send_live = now_w - last_live >= 0.25
        if vw is None and not send_live:  # chỉ chấm điểm: bỏ phần vẽ và ghi video
            i += 1
            continue
        # --- vẽ
        vis = frame.copy()
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

    signal.signal(signal.SIGINT, old_sigint)
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
    ap.add_argument('--dump', action='store_true', help='ghi chi_tiet.json (từng người, từng bàn, từng khung)')
    ap.add_argument('--luu-khung-xuong', action='store_true',
                    help='ghi khung_xuong.npz: 17 điểm của từng người từng khung, để train lớp theo thời gian')
    ap.add_argument('--table-every', type=int, default=4, help='chạy model bàn mỗi N khung')
    ap.add_argument('--staff-model', default=None,
                    help='model "nhân viên hay khách": file YOLO-cls hoặc nhanvien_clip_*.pt (CLIP + lớp nhỏ)')
    ap.add_argument('--staff-every', type=int, default=6, help='xét nhân viên/khách mỗi N khung')
    ap.add_argument('--half', action='store_true', help='chạy model .pt bằng FP16 trên GPU')
    ap.add_argument('--no-video', action='store_true', help='không ghi video kết quả (chỉ cần chấm điểm)')
    ap.add_argument('--pose-refine', choices=list(RTMPOSE), default=None,
                    help='chạy thêm RTMPose trên từng người để có khung xương tốt hơn')
    ap.add_argument('--refine-mode', choices=['tat_ca', 'yeu', 'gan_vai'], default='tat_ca',
                    help='tat_ca: mọi người; yeu: chỉ người YOLO không thấy rõ vai/cổ tay; '
                         'gan_vai: thêm người có cổ tay đã lên gần vai')
    ap.add_argument('--tracker', default='bytetrack.yaml',
                    help='bộ bám người: bytetrack.yaml, botsort.yaml, tracktrack.yaml... hoặc file .yaml trong models/')
    ap.add_argument('--may-chu', default=None,
                    help='địa chỉ máy chủ Easy FnB, ví dụ http://localhost:8080: gửi sự kiện, hình, trạng thái bàn lên web')
    ap.add_argument('--camera', default='cam1', help='mã camera trên máy chủ')
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
              f"~{s['khung_moi_giay']} khung/giây, {n} sự kiện", flush=True)
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
