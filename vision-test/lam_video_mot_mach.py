"""Dựng một video demo hoàn chỉnh từ kết quả pipeline m01: khung nhận diện có sẵn,
thêm thanh tiêu đề, thẻ việc hiện dần theo đúng mốc video, và giọng đọc tiếng Việt.

    python lam_video_mot_mach.py <video_ket_qua.mp4> <thu_muc_ra> <video.mp4>

Sự kiện lấy từ máy chủ đang chạy ở http://localhost:8081 (chạy pipeline với --may-chu).
"""
import asyncio
import json
import os
import subprocess
import sys
import urllib.request
import wave
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

SERVER_DIR = Path(r'C:\Users\sosar\AppData\Local\Claude-Data\claude_pzs8sxrjxfjjc\scratch-workspaces\7d58fbbd-096b-4aa8-b0a4-c7271da52073\92788678-51d2-48a1-83fc-577b6251a8c7\scratch-2026-10-31-4fd720\easy-fnb')
API = 'http://localhost:8081'
FONT = 'C:/Windows/Fonts/segoeui.ttf'
FONT_B = 'C:/Windows/Fonts/segoeuib.ttf'
W_TARGET = 1280

KIND_VI = {'call': 'gọi phục vụ', 'needs_clearing': 'cần dọn', 'new_guest': 'có khách mới'}
KIND_COLOR = {'call': (220, 38, 38), 'needs_clearing': (234, 140, 10), 'new_guest': (37, 99, 235)}


def font(size, bold=False):
    for p in ((FONT_B if bold else FONT), FONT):
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            pass
    return ImageFont.load_default()


def get_state():
    with urllib.request.urlopen(API + '/api/state', timeout=30) as r:
        return json.load(r)


def lay_su_kien():
    st = get_state()
    ten = {s['id']: s['name'] for s in st['staff']}
    ev = []
    for a in st['alerts']:
        if a.get('video_t') is None:
            continue
        ev.append(dict(t=float(a['video_t']), kind=a['kind'], table=a.get('table'),
                       who=ten.get(a.get('assigned_to')) or None))
    ev.sort(key=lambda e: e['t'])
    # gộp các "khách mới" sát nhau thành một câu
    out = []
    for e in ev:
        if e['kind'] == 'new_guest' and out and out[-1]['kind'] == 'new_guest' and e['t'] - out[-1]['t'] < 3.0:
            out[-1]['tables'].append(e['table'])
            out[-1]['t'] = min(out[-1]['t'], e['t'])
        elif e['kind'] == 'new_guest':
            out.append(dict(t=e['t'], kind=e['kind'], tables=[e['table']], who=e['who']))
        else:
            out.append(dict(t=e['t'], kind=e['kind'], tables=[e['table']] if e['table'] else [], who=e['who']))
    return out


def cau_noi(e):
    b = ', '.join(x for x in e['tables'] if x)
    if e['kind'] == 'new_guest':
        return f'{b} có khách mới' if b else 'Có khách mới'
    if e['kind'] == 'call':
        return f'{b} gọi phục vụ' if b else 'Khách gọi phục vụ'
    if e['kind'] == 'needs_clearing':
        return f'{b} cần dọn' if b else 'Có bàn cần dọn'
    return ''


def cau_hien(e):
    b = ', '.join(x for x in e['tables'] if x)
    if e['kind'] == 'new_guest':
        return (b + ' có khách mới') if b else 'Có khách mới'
    if e['kind'] == 'call':
        return (b + ' gọi phục vụ') if b else 'Khách gọi phục vụ'
    if e['kind'] == 'needs_clearing':
        return (b + ' cần dọn') if b else 'Có bàn cần dọn'
    return ''


async def tao_giong(cau_list, cache):
    sys.path.insert(0, str(SERVER_DIR))
    from server.tts import Tts
    tts = Tts(cache)
    if not tts.enabled:
        print('KHÔNG có Piper — video sẽ không có tiếng')
        return {}
    out = {}
    for c in cau_list:
        p = await tts.wav(c)
        if p:
            out[c] = p
        print('giọng:', c)
    tts.close()
    return out


def doc_wav(p):
    with wave.open(str(p), 'rb') as w:
        n, sr = w.getnframes(), w.getframerate()
        data = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0
        if w.getnchannels() == 2:
            data = data.reshape(-1, 2).mean(axis=1)
    return data, sr


def tron_am(ev, wavs, giay):
    sr = 22050
    for p in wavs.values():
        _, sr = doc_wav(p)
        break
    buf = np.zeros(int(sr * (giay + 4)), dtype=np.float32)
    for e in ev:
        c = cau_noi(e)
        if not c or c not in wavs:
            continue
        d, _ = doc_wav(wavs[c])
        i = int((e['t'] + 0.2) * sr)
        j = min(len(buf), i + len(d))
        if j > i:
            buf[i:j] += d[:j - i]
    peak = float(np.max(np.abs(buf))) or 1.0
    if peak > 0.92:
        buf *= 0.92 / peak
    return (buf * 32767).astype(np.int16), sr


def ve_khung(img, t, ev, w, h, ten_file):
    dr = ImageDraw.Draw(img, 'RGBA')
    # thanh tiêu đề
    dr.rectangle((0, 0, w, 46), fill=(12, 15, 20, 205))
    dr.text((18, 10), 'Easy FnB', font=font(22, True), fill=(255, 255, 255))
    dr.text((140, 14), 'AI camera cho quán ăn  ·  video CCTV thật (m01)', font=font(17),
            fill=(200, 208, 220))
    dr.text((w - 92, 14), 'demo', font=font(17, True), fill=(120, 220, 170))
    # chú giải màu bàn
    dr.text((18, 54), 'bàn: xanh lá = trống · xanh dương = có khách · cam = cần dọn',
            font=font(15), fill=(255, 255, 255))
    # thẻ việc đang hiện (mới nhất ở trên, tối đa 3)
    dang = [e for e in ev if e['t'] <= t <= e['t'] + 4.2]
    dang = dang[-3:][::-1]
    y = h - 16
    for e in dang:
        cau = cau_hien(e)
        if not cau:
            continue
        phu = f"đã giao {e['who']}" if e['who'] else 'đã báo nhân viên'
        f1, f2 = font(21, True), font(14)
        tw = max(dr.textlength(cau, font=f1), dr.textlength(phu, font=f2))
        bw, bh = int(tw) + 54, 62
        x0, y0 = 18, y - bh
        dr.rounded_rectangle((x0, y0, x0 + bw, y0 + bh), 10, fill=(12, 15, 20, 215))
        dr.rounded_rectangle((x0, y0, x0 + 8, y0 + bh), 4, fill=KIND_COLOR[e['kind']])
        dr.text((x0 + 22, y0 + 9), cau, font=f1, fill=(255, 255, 255))
        dr.text((x0 + 22, y0 + 36), phu, font=f2, fill=(170, 180, 195))
        y = y0 - 10
    # tiêu đề mở đầu
    if t < 2.4:
        a = 1.0 if t < 1.8 else max(0.0, (2.4 - t) / 0.6)
        dr.rectangle((0, h // 2 - 62, w, h // 2 + 62), fill=(8, 10, 14, int(190 * a)))
        dr.text((w // 2, h // 2 - 44), 'Camera thấy việc, điện thoại nhân viên báo ngay',
                font=font(30, True), fill=(255, 255, 255, int(255 * a)), anchor='ma')
        dr.text((w // 2, h // 2 + 4), 'Không cần nhân viên đứng nhìn camera',
                font=font(20), fill=(200, 210, 225, int(255 * a)), anchor='ma')
    # nhãn file nhỏ góc dưới phải
    dr.text((w - 14, h - 22), ten_file, font=font(13), fill=(255, 255, 255, 150), anchor='ra')


def main():
    src, work, dst = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    work.mkdir(parents=True, exist_ok=True)
    ev = lay_su_kien()
    print('sự kiện:', [(round(e['t'], 1), e['kind'], e['tables']) for e in ev])

    cap = cv2.VideoCapture(str(src))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    w0, h0 = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    giay = n / fps
    print(f'video {w0}x{h0} {fps:.2f} fps {giay:.1f}s')

    cau = [cau_noi(e) for e in ev]
    wavs = asyncio.run(tao_giong(sorted(set(c for c in cau if c)), work / 'tts'))
    pcm, sr = tron_am(ev, wavs, giay)
    wav_out = work / 'tieng.wav'
    with wave.open(str(wav_out), 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())

    cmd = ['ffmpeg', '-loglevel', 'error', '-y',
           '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{w0}x{h0}', '-r', f'{fps:g}', '-i', '-',
           '-i', str(wav_out), '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '22',
           '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '128k', '-shortest', '-movflags', '+faststart',
           str(dst)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    i = 0
    while True:
        ok, f = cap.read()
        if not ok:
            break
        if w0 != W_TARGET:
            f = cv2.resize(f, (W_TARGET, round(h0 * W_TARGET / w0)))
        img = Image.fromarray(cv2.cvtColor(f, cv2.COLOR_BGR2RGB))
        ve_khung(img, i / fps, ev, img.width, img.height, src.parent.name)
        proc.stdin.write(cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR).tobytes())
        i += 1
        if i % 250 == 0:
            print('khung', i, '/', n)
    cap.release()
    proc.stdin.close()
    proc.wait()
    print('xong', dst)


if __name__ == '__main__':
    main()
