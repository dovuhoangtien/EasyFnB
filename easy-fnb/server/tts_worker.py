"""Tiến trình đọc tiếng Việt (Piper) giữ model trong bộ nhớ.

Chạy bằng Python riêng có piper-tts (onnxruntime không tải được từ đường dẫn quá dài của .venv):
    C:\\fnb-tts\\Scripts\\python.exe server\\tts_worker.py <model.onnx>
Mỗi dòng stdin là JSON {"text": ..., "out": <đường dẫn .wav>}; trả "ok" hoặc "err: ..." trên một dòng.
"""
import json
import sys
import wave

from piper import PiperVoice

voice = PiperVoice.load(sys.argv[1])
print('ready', flush=True)
for line in sys.stdin:
    try:
        req = json.loads(line)
        with wave.open(req['out'], 'wb') as w:
            voice.synthesize_wav(req['text'], w)
        print('ok', flush=True)
    except Exception as e:  # noqa: BLE001
        print(f'err: {e}', flush=True)
