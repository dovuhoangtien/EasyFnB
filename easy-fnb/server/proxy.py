"""Cổng https tự ký chuyển tiếp vào máy chủ http nội bộ.

Máy chủ chính vẫn chạy http ở cổng 8080 (pipeline, bảng điều khiển dùng thẳng, nhanh, không
cần chứng chỉ). Cổng 8443 chỉ để điện thoại mở trang /phat bằng https — Safari chỉ cho dùng
camera ở https. Mọi thứ đi qua đây được chuyển nguyên xi vào 127.0.0.1:8080.
"""
import asyncio
import ssl


async def _pipe(reader, writer):
    try:
        while True:
            data = await reader.read(65536)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    except Exception:
        pass
    finally:
        try:
            writer.close()
        except Exception:
            pass


async def _handle(reader, writer, backend):
    try:
        br, bw = await asyncio.open_connection(*backend)
    except Exception:
        writer.close()
        return
    await asyncio.gather(_pipe(reader, bw), _pipe(br, writer), return_exceptions=True)


async def _serve(cert, key, port, backend):
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(str(cert), str(key))
    server = await asyncio.start_server(lambda r, w: _handle(r, w, backend), '0.0.0.0', port, ssl=ctx)
    async with server:
        await server.serve_forever()


def start_https(cert, key, port, backend_host='127.0.0.1', backend_port=8080):
    """Chạy trong luồng riêng; trả về luồng (daemon) để chương trình chính tự thoát theo."""

    def run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_serve(cert, key, port, (backend_host, backend_port)))

    import threading

    t = threading.Thread(target=run, name='https', daemon=True)
    t.start()
    return t
