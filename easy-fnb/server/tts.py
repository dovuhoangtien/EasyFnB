"""Giọng đọc tiếng Việt cho điện thoại nhân viên khi máy không có giọng Việt (chạy trên máy chủ).

Hai bộ đọc, chọn bằng biến môi trường TTS_ENGINE:
  vieneu  VieNeu-TTS v3 Turbo (mặc định khi đã cài ở C:\\fnb-tts2), giọng tự nhiên, 48 kHz, chạy CPU.
  piper   Piper vi_VN-vais1000-medium (cũ), tự dùng thay khi VieNeu chưa cài hoặc không khởi động được.
  off     tắt giọng đọc.
Không có bộ nào: app vẫn chạy, chỉ không có giọng.
"""
import asyncio
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

HERE = Path(__file__).parent
PIPER_PYTHON = Path(os.environ.get('PIPER_PYTHON', r'C:\fnb-tts\Scripts\python.exe'))
MODEL = Path(os.environ.get('PIPER_MODEL', HERE / 'voices' / 'vi_VN-vais1000-medium.onnx'))
VIENEU_PYTHON = Path(os.environ.get('VIENEU_PYTHON', r'C:\fnb-tts2\Scripts\python.exe'))
VIENEU_VOICE = os.environ.get('VIENEU_VOICE', 'Thiện Minh')
TTS_ENGINE = os.environ.get('TTS_ENGINE', 'auto').strip().lower()
MAX_CHARS = 200
RETRY_AFTER = 300  # giây: bộ đọc khởi động lỗi thì nghỉ chừng này rồi mới thử lại


class _Engine:
    """Một tiến trình đọc sống lâu, nói chuyện qua stdin/stdout theo dòng."""

    def __init__(self, name: str, voice: str, cmd: list[str], env_tries: list[dict]):
        self.name, self.voice, self.cmd, self.env_tries = name, voice, cmd, env_tries
        self.proc = None
        self.dead_until = 0.0

    @property
    def alive(self) -> bool:
        return time.monotonic() >= self.dead_until

    def key(self, text: str) -> str:
        return hashlib.sha1(f'{self.name}|{self.voice}|{text}'.encode('utf-8')).hexdigest()[:20] + '.wav'

    def _start(self):
        for extra in self.env_tries:
            proc = subprocess.Popen(
                self.cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True, encoding='utf-8', bufsize=1, env={**os.environ, 'PYTHONIOENCODING': 'utf-8', **extra})
            if proc.stdout.readline().strip() == 'ready':
                self.proc = proc
                return
            proc.kill()
        self.dead_until = time.monotonic() + RETRY_AFTER
        raise RuntimeError(f'{self.name} không khởi động được')

    def render(self, text: str, out: Path):
        if self.proc is None or self.proc.poll() is not None:
            self._start()
        tmp = out.with_suffix('.tmp.wav')
        try:
            self.proc.stdin.write(json.dumps(dict(text=text, out=str(tmp))) + '\n')
            self.proc.stdin.flush()
            reply = self.proc.stdout.readline().strip()
        except OSError as e:
            raise RuntimeError(f'{self.name} dừng: {e}')
        if reply != 'ok':
            raise RuntimeError(reply or f'{self.name} dừng')
        tmp.replace(out)

    def close(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()


def _engines() -> list[_Engine]:
    found = {}
    if VIENEU_PYTHON.exists() and (VIENEU_PYTHON.parent.parent / 'Lib' / 'site-packages' / 'vieneu').is_dir():
        # Thử không cần mạng trước (model đã tải về), không được mới cho tải từ Hugging Face.
        found['vieneu'] = _Engine('vieneu', VIENEU_VOICE,
                                  [str(VIENEU_PYTHON), str(HERE / 'tts_worker_vieneu.py'), VIENEU_VOICE],
                                  [{'HF_HUB_OFFLINE': '1'}, {'HF_HUB_OFFLINE': '0'}])
    if PIPER_PYTHON.exists() and MODEL.exists():
        found['piper'] = _Engine('piper', MODEL.stem, [str(PIPER_PYTHON), str(HERE / 'tts_worker.py'), str(MODEL)], [{}])
    order = {'off': [], 'none': [], 'piper': ['piper']}.get(TTS_ENGINE, ['vieneu', 'piper'])
    return [found[n] for n in order if n in found]


class Tts:
    def __init__(self, cache_dir: Path):
        self.cache = Path(cache_dir)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.engines = _engines()  # theo thứ tự ưu tiên; cái sau là dự phòng
        self.enabled = bool(self.engines)
        self._lock = asyncio.Lock()

    def status(self) -> dict:
        live = [e for e in self.engines if e.alive]
        e = live[0] if live else None
        return dict(enabled=self.enabled, engine=e.name if e else None, voice=e.voice if e else None,
                    engines=[x.name for x in self.engines])

    def _cached(self, text: str) -> Path | None:
        """Ưu tiên bản của bộ đọc chính; bản của bộ dự phòng chỉ dùng khi bộ chính đang hỏng."""
        for e in self.engines:
            if e.alive:
                f = self.cache / e.key(text)
                return f if f.exists() else None
        return None

    def _render(self, text: str) -> Path:
        err = None
        for e in self.engines:
            if not e.alive:
                continue
            out = self.cache / e.key(text)
            if out.exists():
                return out
            try:
                e.render(text, out)
                return out
            except RuntimeError as ex:  # thử bộ dự phòng
                err = ex
        raise err or RuntimeError('giọng đọc tạm nghỉ')

    async def wav(self, text: str) -> Path | None:
        text = ' '.join(text.split())[:MAX_CHARS]
        if not self.enabled or not text:
            return None
        out = self._cached(text)
        if out:
            return out
        async with self._lock:  # một câu một lúc; câu đã có sẵn không phải chờ
            return self._cached(text) or await asyncio.to_thread(self._render, text)

    async def warm(self, texts=()):
        """Tổng hợp sẵn các cụm hay đọc lúc khởi động (VieNeu nạp model mất khoảng 15 giây).
        App nhân viên đọc từng cụm một ("Bàn B2", rồi "gọi phục vụ"), nên làm sẵn tên bàn và tên việc
        thì lời báo đầu tiên của ca cũng phát ngay."""
        if not self.enabled:
            return
        for t in ('gọi phục vụ', 'cần dọn', 'có khách mới', 'Gấp', *texts):
            try:
                await self.wav(t)
            except Exception:
                return

    def close(self):
        for e in self.engines:
            e.close()
