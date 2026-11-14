import argparse
import os
from pathlib import Path

import uvicorn

from server.net import lan_ip

ap = argparse.ArgumentParser(description='Chạy máy chủ Easy FnB')
ap.add_argument('--host', default='0.0.0.0', help='0.0.0.0 để điện thoại cùng wifi vào được')
ap.add_argument('--port', type=int, default=int(os.environ.get('PORT', 8080)))
ap.add_argument('--https', action='store_true',
                help='thêm cổng https tự ký cho camera điện thoại (Safari chặn camera ở http)')
ap.add_argument('--https-port', type=int, default=8443)
ap.add_argument('--reload', action='store_true')
args = ap.parse_args()

if not os.environ.get('K_SERVICE'):          # K_SERVICE có sẵn khi chạy trên Cloud Run
    ip = lan_ip()
    print(f'Easy FnB đang chạy: http://localhost:{args.port}', flush=True)
    if ip and args.host == '0.0.0.0':
        print(f'Điện thoại (cùng wifi): http://{ip}:{args.port}', flush=True)

if args.https:
    from server.proxy import start_https
    from server.tls import ensure_cert

    os.environ['HTTPS_PORT'] = str(args.https_port)   # để /api/info báo cho trang Cài đặt làm mã QR camera
    cert, key = ensure_cert(Path(os.environ.get('DATA_DIR') or '.data') / 'certs')
    start_https(cert, key, args.https_port, backend_port=args.port)
    if not os.environ.get('K_SERVICE'):
        ip = lan_ip() or 'localhost'
        print(f'Camera điện thoại (https): https://{ip}:{args.https_port}/phat?cam=cam1', flush=True)
        print('  Lần đầu iPhone cảnh báo chứng chỉ: Show details > visit this website > Visit Website.', flush=True)

uvicorn.run('server.app:app', host=args.host, port=args.port, reload=args.reload, log_level='warning')
