"""Tiến trình đọc tiếng Việt bằng VieNeu-TTS v3 Turbo (ONNX, chạy CPU), giữ model trong bộ nhớ.

Chạy bằng Python riêng ở đường dẫn ngắn (pip install vieneu):
    C:\\fnb-tts2\\Scripts\\python.exe server\\tts_worker_vieneu.py "<tên giọng>"
Cùng giao thức với tts_worker.py: mỗi dòng stdin là JSON {"text": ..., "out": <đường dẫn .wav>};
trả "ok" hoặc "err: ..." trên một dòng. Số và mã bàn ("B1" -> "bê một") do bộ chuẩn hoá của VieNeu tự đọc.
"""
import json
import os
import sys
import unicodedata
import wave

# Thư viện có thể in linh tinh ra stdout: giữ riêng kênh giao thức, còn lại đẩy sang stderr.
proto = os.fdopen(os.dup(1), 'w', encoding='utf-8', buffering=1)
os.dup2(2, 1)
sys.stdin.reconfigure(encoding='utf-8')
os.environ.setdefault('HF_HUB_DISABLE_SYMLINKS_WARNING', '1')

import numpy as np  # noqa: E402
from vieneu import Vieneu  # noqa: E402


def plain(s: str) -> str:
    """'Thùy Dung' -> 'thuy dung' để chọn giọng không cần gõ dấu."""
    s = unicodedata.normalize('NFD', s.replace('đ', 'd').replace('Đ', 'D'))
    return ' '.join(''.join(c for c in s if unicodedata.category(c) != 'Mn').lower().split())


def pick_voice(tts, want: str) -> str:
    names = [v[1] if isinstance(v, (tuple, list)) else str(v) for v in tts.list_preset_voices()]
    for n in names:
        if plain(n) == plain(want):
            return n
    print(f'không có giọng "{want}", dùng "{names[0]}". Có: {names}', file=sys.stderr)
    return names[0]


def sane(audio: np.ndarray, sr: int, text: str) -> bool:
    """Model lấy mẫu ngẫu nhiên, thỉnh thoảng ra câu cụt hoặc kéo dài: loại bản lỗi trước khi lưu vào cache."""
    if audio.size == 0 or not np.isfinite(audio).all():
        return False
    dur = audio.size / sr
    n = max(len(text), 4)
    return 0.03 * n <= dur <= 0.25 * n + 1.5 and float(np.sqrt(np.mean(audio ** 2))) > 0.01


def synth(tts, voice: str, text: str) -> np.ndarray:
    audio = None
    for _ in range(3):
        audio = np.asarray(tts.infer(text, voice=voice), dtype=np.float32).reshape(-1)
        if sane(audio, tts.sample_rate, text):
            break
    else:
        if audio is None or audio.size == 0:
            raise RuntimeError('model không ra âm thanh')
    peak = float(np.abs(audio).max())
    if peak > 0:
        audio = audio * (0.89 / peak)  # âm lượng đều giữa các câu, không vỡ tiếng
    return audio


def main():
    tts = Vieneu()
    voice = pick_voice(tts, sys.argv[1] if len(sys.argv) > 1 else 'Thùy Dung')
    sr = int(tts.sample_rate)
    proto.write('ready\n')
    for line in sys.stdin:
        try:
            req = json.loads(line)
            pcm = (synth(tts, voice, req['text']) * 32767).astype('<i2')
            with wave.open(req['out'], 'wb') as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(sr)
                w.writeframes(pcm.tobytes())
            proto.write('ok\n')
        except Exception as e:  # noqa: BLE001
            proto.write('err: ' + ' '.join(str(e).split()) + '\n')


main()
