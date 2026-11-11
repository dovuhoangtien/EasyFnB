"""T4 phần A: dựng gói request Gemini từ sự kiện v4 (KHÔNG gửi).

Mỗi sự kiện 'goi_phuc_vu' / 'can_don':
  dai_2x2.jpg   4 khung ở t-1.5, t-1, t-0.5, t (crop người hoặc bàn, nới 30%, làm vuông), 768x768, mức MEDIUM
  toan_canh.jpg cả khung thu nhỏ 768x432, khung đỏ quanh người/bàn, mức LOW
  ban_sach.jpg  (chỉ 'can_don') cùng vùng bàn ở mốc 'T' gần nhất trong dap_an.json, 512x512, mức LOW
  request.json  thân generateContent đầy đủ (base64); request_xem.json bản đọc được
  xem_nhanh.jpg ghép để người xem

Chạy:  python dung_goi.py
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import xac_minh_v2 as xm  # noqa: E402
from server.gemini import VERIFY_PROMPT, VERIFY_SCHEMA  # noqa: E402

VT = HERE.parents[1]
OUT = HERE / 'goi_mau'
CLIPS = {'10_thay_the_gio_tay_lop_hoc_a': 'call', '12_thay_the_gio_tay_hoi_bai': 'call',
         '01_phong_an_goc_cao': 'needs_clearing'}
OFFSETS = {'truoc': (-1.5, -1.0, -0.5, 0.0),     # theo thiết kế V01: chỉ dùng quá khứ, gửi ngay
           'quanh': (-0.5, 0.0, 0.5, 1.0)}      # biến thể: chờ 1 s sau sự kiện rồi mới gửi
TILE = {'call': (288, 384), 'needs_clearing': (384, 288)}   # (rộng, cao) mỗi ô: người 3:4, bàn 4:3
STRIP_Q = 85


def read_frame(cap, fps, t):
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(round(t * fps)))
    ok, f = cap.read()
    if not ok:
        raise RuntimeError(f'không đọc được khung t={t}')
    return f


def grow_box(b, W, H, aspect, grow=0.30):
    """Nới box thêm 30% (15% mỗi bên), rồi chỉ nới cạnh ngắn cho đúng tỉ lệ ô (rộng/cao), dịch vào trong khung.
    Không làm vuông: crop vuông quanh người đứng kéo cả người bên cạnh (đang giơ tay) vào ô."""
    x1, y1, x2, y2 = map(float, b)
    w, h = (x2 - x1) * (1 + grow), (y2 - y1) * (1 + grow)
    if w / h < aspect:
        w = h * aspect
    else:
        h = w / aspect
    w, h = min(w, W), min(h, H)
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    x1 = int(np.clip(cx - w / 2, 0, W - w))
    y1 = int(np.clip(cy - h / 2, 0, H - h))
    return x1, y1, int(x1 + w), int(y1 + h)


def label(img, text, org=(6, 24), scale=0.6):
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, 2)
    x, y = org
    cv2.rectangle(img, (x - 4, y - th - 6), (x + tw + 4, y + 6), (0, 0, 0), -1)
    cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, scale, (255, 255, 255), 2, cv2.LINE_AA)


def jpg(img, q=STRIP_Q):
    return cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, q])[1].tobytes()


def make_strip(cap, fps, t, sq, tile_wh, offsets, dur):
    t0 = t + offsets[0]
    times = [t + o for o in offsets]
    if t0 < 0:                                   # đầu clip: rải đều phần đã có
        times = list(np.linspace(0.0, t + offsets[-1], 4))
    times = [min(tt, dur - 0.05) for tt in times]
    x1, y1, x2, y2 = sq
    tiles = []
    TW, TH = tile_wh
    for tt in times:
        f = read_frame(cap, fps, tt)
        tile = cv2.resize(f[y1:y2, x1:x2], (TW, TH), interpolation=cv2.INTER_AREA)
        label(tile, f't{tt - t:+.1f}s' if abs(tt - t) > 1e-6 else 't (su kien)')
        tiles.append(tile)
    strip = np.vstack([np.hstack(tiles[:2]), np.hstack(tiles[2:])])
    cv2.line(strip, (TW, 0), (TW, 2 * TH), (255, 255, 255), 2)
    cv2.line(strip, (0, TH), (2 * TW, TH), (255, 255, 255), 2)
    return strip, [round(tt, 2) for tt in times]


def make_overview(frame, box=None, poly=None, text=''):
    f = frame.copy()
    if poly is not None:
        cv2.polylines(f, [np.int32(poly)], True, (0, 0, 255), 5)
        x, y = np.int32(poly).min(0)
    else:
        x1, y1, x2, y2 = map(int, box)
        cv2.rectangle(f, (x1, y1), (x2, y2), (0, 0, 255), 5)
        x, y = x1, y1
    f = cv2.resize(f, (768, 432), interpolation=cv2.INTER_AREA)
    if text:
        s = 768 / frame.shape[1]
        label(f, text, (max(6, int(x * s)), max(22, int(y * s) - 8)), 0.55)
    return f


def clean_ref_time(dap, clip, table, t):
    ban = dap['ban'][clip]
    i = ban['thu_tu'].index(table)
    cands = [float(k) for k, v in ban['moc'].items() if v[i] == 'T']
    if not cands:
        return None
    before = [c for c in cands if c <= t]
    return max(before) if before else min(cands, key=lambda c: abs(c - t))


def main():
    OUT.mkdir(exist_ok=True)
    dap = json.loads((VT / 'danh_gia' / 'dap_an.json').read_text(encoding='utf-8'))
    zones = json.loads((VT / 'zones.json').read_text(encoding='utf-8'))
    summary = []
    n = 0
    for clip, kind in CLIPS.items():
        ev_all = json.loads((VT / 'out_v4' / clip / 'su_kien.json').read_text(encoding='utf-8'))['su_kien']
        want = 'goi_phuc_vu' if kind == 'call' else 'can_don'
        cap = cv2.VideoCapture(str(VT / 'clips' / f'{clip}.mp4'))
        fps = cap.get(cv2.CAP_PROP_FPS)
        W, H = int(cap.get(3)), int(cap.get(4))
        dur = cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps
        for ev in [e for e in ev_all if e['loai'] == want]:
            n += 1
            t = ev['t']
            poly = None
            if kind == 'call':
                box = ev['box']
                text = 'nguoi can xet'
            else:
                poly = zones[clip]['ban'][ev['ban']]
                p = np.array(poly)
                box = [p[:, 0].min(), p[:, 1].min(), p[:, 0].max(), p[:, 1].max()]
                text = f"Ban {ev['ban']}"
            tw, th = TILE[kind]
            sq = grow_box(box, W, H, tw / th)
            frame_t = read_frame(cap, fps, t)
            over = make_overview(frame_t, box=box, poly=poly, text=text)
            over_j = jpg(over, 80)
            ref_j = ref_t = None
            if kind == 'needs_clearing':
                ref_t = clean_ref_time(dap, clip, ev['ban'], t)
                if ref_t is not None:
                    x1, y1, x2, y2 = sq
                    ref = cv2.resize(read_frame(cap, fps, ref_t)[y1:y2, x1:x2], (512, 384),
                                     interpolation=cv2.INTER_AREA)
                    label(ref, f'ban sach (t={ref_t:g}s)')
                    ref_j = jpg(ref)
            name = f"{n:02d}_{clip[:2]}_{t:05.2f}s_{'goi' if kind == 'call' else 'can_don_' + ev['ban']}"
            d = OUT / name
            d.mkdir(exist_ok=True)
            (d / 'toan_canh.jpg').write_bytes(over_j)
            if ref_j:
                (d / 'ban_sach.jpg').write_bytes(ref_j)
            variants = ['truoc', 'quanh'] if kind == 'call' else ['truoc']
            for var in variants:
                sfx = '' if var == 'truoc' else '_quanh'
                strip, times = make_strip(cap, fps, t, sq, TILE[kind], OFFSETS[var], dur)
                images = [{'role': 'strip', 'jpeg': jpg(strip)}, {'role': 'overview', 'jpeg': over_j}]
                if ref_j:
                    images.append({'role': 'clean_ref', 'jpeg': ref_j})
                (d / f'dai_2x2{sfx}.jpg').write_bytes(images[0]['jpeg'])
                body = xm.build_body(kind, images, ev.get('ban'))
                (d / f'request{sfx}.json').write_text(json.dumps(body, ensure_ascii=False), encoding='utf-8')
                (d / f'request{sfx}_xem.json').write_text(json.dumps(xm.redact(body), ensure_ascii=False, indent=1),
                                                          encoding='utf-8')
                # ghép xem nhanh: dải | toàn cảnh (+ bàn sạch)
                right = [over]
                if ref_j:
                    right.append(cv2.imdecode(np.frombuffer(ref_j, np.uint8), 1))
                rw = 768
                right = np.vstack([cv2.copyMakeBorder(r, 0, 0, 0, rw - r.shape[1], cv2.BORDER_CONSTANT) for r in right])
                hh = max(strip.shape[0], right.shape[0])
                pad = lambda im: cv2.copyMakeBorder(im, 0, hh - im.shape[0], 0, 0, cv2.BORDER_CONSTANT)
                cv2.imwrite(str(d / f'xem_nhanh{sfx}.jpg'), np.hstack([pad(strip), pad(right)]),
                            [cv2.IMWRITE_JPEG_QUALITY, 80])
                tok = xm.estimate_tokens(body)
                tok3 = xm.estimate_tokens(body, 3.0)
                summary.append(dict(goi=name, bien_the=var, clip=clip, kind=kind, t=t, ban=ev.get('ban'),
                                    box=ev.get('box'), khung_s=times, vung_cat=list(sq), ban_sach_t=ref_t,
                                    co_tham_chieu=ref_j is not None,
                                    dai_px=[strip.shape[1], strip.shape[0]],
                                    anh_byte={im['role']: len(im['jpeg']) for im in images},
                                    request_byte=len((d / f'request{sfx}.json').read_bytes()),
                                    token=tok, token_neu_3_ky_tu=tok3['total']))
                print(name, var, times, tok['total'], 'tok;', summary[-1]['anh_byte'], summary[-1]['dai_px'])
    # đường cơ sở: request hiện tại (một crop LOW)
    old = {}
    for kind in ('call', 'needs_clearing'):
        chars = len(VERIFY_PROMPT[kind]) + len(json.dumps(VERIFY_SCHEMA[kind], separators=(',', ':')))
        old[kind] = dict(image=280, text=round(chars / 4), total=280 + round(chars / 4))
    (OUT / 'tong_hop.json').write_text(json.dumps(dict(goi=summary, request_cu=old), ensure_ascii=False, indent=1),
                                       encoding='utf-8')
    print('request cũ:', old)


if __name__ == '__main__':
    main()
