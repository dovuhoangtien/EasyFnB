import os
import socket


def lan_ip():
    """Địa chỉ của máy này trong mạng wifi (không gửi gói tin nào ra ngoài). None khi chạy trên Cloud Run."""
    if os.environ.get('K_SERVICE'):
        return None
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
        return None if ip.startswith('127.') else ip
    except OSError:
        return None
    finally:
        s.close()
