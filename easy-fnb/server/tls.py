"""Chứng chỉ https tự ký cho mạng LAN.

Safari trên iPhone chỉ cho trang web dùng camera khi địa chỉ là https. Máy chủ chạy trong
quán thì không cần internet, nên ta tự tạo chứng chỉ cho địa chỉ IP trong Wi-Fi. iPhone sẽ
hiện cảnh báo "không xác minh được" ở lần mở đầu tiên: bấm "Vẫn tiếp tục" là dùng được.
"""
import shutil
import subprocess
from pathlib import Path

from .net import lan_ip

CERT = 'cert.pem'
KEY = 'key.pem'
SAN = 'san.txt'

_OPENSSL_FALLBACKS = (
    r'C:\Program Files\Git\mingw64\bin\openssl.exe',
    r'C:\Program Files\Git\usr\bin\openssl.exe',
    r'C:\Program Files\OpenSSL-Win64\bin\openssl.exe',
)


def _openssl():
    found = shutil.which('openssl')
    if found:
        return found
    for p in _OPENSSL_FALLBACKS:
        if Path(p).exists():
            return p
    return None


def _san(ip):
    names = ['DNS:localhost', 'IP:127.0.0.1']
    if ip:
        names.append(f'IP:{ip}')
    return ','.join(names)


def ensure_cert(folder):
    """Trả về (cert, key). Tạo mới khi chưa có hoặc khi đổi Wi-Fi (đổi IP)."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    cert, key, san = folder / CERT, folder / KEY, folder / SAN
    want = _san(lan_ip())
    if cert.exists() and key.exists() and san.exists() and san.read_text(encoding='utf-8').strip() == want:
        return cert, key

    exe = _openssl()
    if not exe:
        raise SystemExit(
            'Không tìm thấy openssl để tạo chứng chỉ https.\n'
            'Cài Git for Windows (có sẵn openssl) rồi chạy lại, hoặc dùng đường hầm Cloudflare.'
        )
    subprocess.run(
        [exe, 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-sha256', '-days', '3650',
         '-subj', '/CN=Easy FnB', '-addext', f'subjectAltName={want}',
         '-keyout', str(key), '-out', str(cert)],
        check=True, capture_output=True,
    )
    san.write_text(want, encoding='utf-8')
    return cert, key
