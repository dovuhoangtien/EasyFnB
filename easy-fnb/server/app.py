"""Máy chủ Easy FnB: nhận sự kiện từ camera, điều phối việc cho nhân viên, Gemini kiểm tra và trả lời.

Chạy (từ thư mục easy-fnb):
    python -m server                       # cổng 8080, mọi địa chỉ mạng (điện thoại trong cùng wifi vào được)
    python -m server --port 8080 --reload

Biến môi trường:
    KIE_API_KEY       khoá kie.ai; có khoá này thì dùng kie.ai thay Gemini (xem server/llm.py)
    KIE_MODEL         mặc định deepseek-v4-1-flash
    GEMINI_API_KEY   khoá Gemini; trợ lý ADK luôn dùng khoá này (kiểm tra ảnh/tóm tắt chỉ dùng khi không có KIE_API_KEY; không có thì vẫn chạy, chỉ không kiểm tra ảnh và không có trợ lý AI)
    GEMINI_MODEL     mặc định gemini-3.5-flash-lite
    (các biến trên có thể ghi trong tệp easy-fnb/.env, xem .env.example)
    EDGE_KEY         nếu đặt, camera phải gửi header X-Edge-Key giống vậy (nên đặt khi chạy trên Cloud Run)
    DATA_DIR         nơi lưu cấu hình và ảnh cắt, mặc định server/data
Hợp đồng API: server/API.md
"""
import asyncio
import base64
import json
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Body, Depends, FastAPI, Header, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse

from .gemini import Gemini, GeminiError
from .hub import Hub, clock, now_ms
from .llm import Llm
from .net import lan_ip
from .tro_ly import TroLy
from .tts import Tts

HERE = Path(__file__).resolve().parent
DIST = HERE.parent / 'dist'
DATA = Path(os.environ.get('DATA_DIR', HERE / 'data'))
EDGE_KEY = os.environ.get('EDGE_KEY', '').strip()
CLOUD = bool(os.environ.get('K_SERVICE'))   # K_SERVICE có sẵn khi chạy trên Cloud Run
STARTED = time.monotonic()

# Chọn nhà cung cấp LLM: có KIE_API_KEY thì dùng kie.ai, không thì Gemini (nếu có GEMINI_API_KEY).
# Cả hai cùng giao diện nên phần còn lại của máy chủ không phải biết bên nào đang chạy.
gemini = Llm() if os.environ.get('KIE_API_KEY', '').strip() else Gemini()
# kie.ai chậm hơn Gemini nhiều (mỗi lượt 20-80 giây vì model luôn suy luận), nên mặc định chỉ dùng
# nó để HỎI ĐÁP và TÓM TẮT CA; việc báo cho nhân viên thì để camera trên máy tự quyết cho tức thì.
# Muốn bật lại kiểm tra ảnh thì tích trong trang Cài đặt (máy chủ vẫn nới hạn xác minh 100 giây).
if isinstance(gemini, Llm):
    hub = Hub(DATA, gemini, verify_timeout_s=100.0,
              defaults=dict(verify_kinds=[], hold_until_verified=[]))
elif gemini.decision:
    # Gemini Decision trả lời trong vài phần mười giây, nên mọi loại việc đều chờ kiểm tra xong mới báo nhân viên.
    hub = Hub(DATA, gemini, defaults=dict(hold_until_verified=['call', 'needs_clearing']))
else:
    hub = Hub(DATA, gemini)
tts = Tts(DATA / 'tts')
tro_ly = TroLy(hub, gemini)


@asynccontextmanager
async def lifespan(_app):
    task = asyncio.create_task(hub.tick_forever())
    asyncio.create_task(tts.warm([f"Bàn {t['id']}" for z in hub.zones.values() for t in z.get('tables', [])]))  # giọng đọc sẵn sàng ngay, câu đầu không phải chờ 3-4 giây khởi động Piper
    if tro_ly.adk_wanted:            # nạp google-adk sẵn (vài giây) để câu hỏi đầu tiên không phải chờ
        asyncio.create_task(asyncio.to_thread(tro_ly.load_adk))
    khoa = 'KIE_API_KEY' if isinstance(gemini, Llm) else 'GEMINI_API_KEY'
    kiem = f', kiểm tra ảnh bằng {gemini.verify_model}' if getattr(gemini, 'decision', False) else ''
    hub.add_log('system', 'Máy chủ khởi động' + (f', {gemini.ten} bật ({gemini.model}{kiem})' if gemini.enabled
                                                  else f', {gemini.ten} tắt (chưa có {khoa})'))
    yield
    task.cancel()
    tts.close()


app = FastAPI(title='Easy FnB', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])


def edge_auth(x_edge_key: str | None = Header(default=None)):
    if EDGE_KEY and x_edge_key != EDGE_KEY:
        raise HTTPException(401, 'sai X-Edge-Key')


def find(aid):
    try:
        return hub.get_alert(aid)
    except KeyError:
        raise HTTPException(404, f'không có việc {aid}')


# ------------------------------------------------------------------ đọc
@app.get('/api/state')
async def get_state():
    return hub.state()


def sse(event, data):
    return f'event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n'


@app.get('/api/health')
async def health():
    """Cho Cloud Run và người vận hành: máy chủ còn sống không. Không đụng tới AI hay ổ đĩa."""
    return dict(ok=True, uptime_s=int(time.monotonic() - STARTED))


def tro_ly_engine():
    """Trợ lý đang trả lời bằng gì: 'adk' (Gemini qua Google ADK) hay 'rules' (tính từ số liệu, không AI)."""
    return 'adk' if tro_ly.adk_wanted and tro_ly._adk is not False else 'rules'


@app.get('/api/info')
async def info():
    """Tình trạng các phần của hệ thống, cho bảng "Hệ thống" trên thanh trên cùng và trang Cài đặt.
    lan_ip: địa chỉ wifi của máy chủ, để đưa link cho điện thoại (localhost thì điện thoại không mở được)."""
    return dict(lan_ip=None if CLOUD else lan_ip(), gemini=gemini.enabled, provider=gemini.ten,
                model=gemini.model if gemini.enabled else None,
                key_name='KIE_API_KEY' if isinstance(gemini, Llm) else 'GEMINI_API_KEY',
                assistant=tro_ly_engine(), assistant_model=tro_ly.model if tro_ly_engine() == 'adk' else None,
                tts=tts.status(), cloud=CLOUD, edge_key=bool(EDGE_KEY),
                uptime_s=int(time.monotonic() - STARTED), subscribers=len(hub.subs))


@app.post('/api/ai/test')
async def ai_test():
    """Gọi thử AI một câu ngắn để biết khoá và model có dùng được không (nút "Thử kết nối" trong Cài đặt)."""
    if not gemini.enabled:
        return dict(ok=False, provider=gemini.ten, error='Chưa có khoá AI trên máy chủ.')
    t0 = time.perf_counter()
    try:
        cau = 'Trả lời đúng một chữ: OK'
        goi = gemini.generate([{'type': 'input_text', 'text': cau}] if isinstance(gemini, Llm) else [{'text': cau}])
        text = await asyncio.wait_for(goi, timeout=40)
    except asyncio.TimeoutError:
        return dict(ok=False, provider=gemini.ten, model=gemini.model, error='Quá 40 giây chưa có trả lời.')
    except (GeminiError, OSError, ValueError) as e:
        return dict(ok=False, provider=gemini.ten, model=gemini.model, error=str(e)[:300])
    except Exception as e:  # lỗi mạng của httpx: báo gọn, không để 500
        return dict(ok=False, provider=gemini.ten, model=gemini.model, error=f'{type(e).__name__}: {e}'[:300])
    return dict(ok=True, provider=gemini.ten, model=gemini.model, ms=int((time.perf_counter() - t0) * 1000),
                reply=str(text).strip()[:40])


@app.get('/api/stream')
async def stream(request: Request, staff: str | None = None):
    q = asyncio.Queue(maxsize=2000)
    hub.subs.add(q)
    if staff:
        hub.staff_online(staff, +1)

    async def gen():
        try:
            yield sse('snapshot', hub.state())
            while True:
                if await request.is_disconnected():
                    break
                try:
                    ev, data = await asyncio.wait_for(q.get(), timeout=15)
                    yield sse(ev, data)
                except asyncio.TimeoutError:
                    yield ': ping\n\n'
        finally:
            hub.subs.discard(q)
            if staff:
                hub.staff_online(staff, -1)

    return StreamingResponse(gen(), media_type='text/event-stream',
                             headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


@app.get('/api/camera/{cid}/frame.jpg')
async def camera_frame(cid: str):
    img = hub.frames.get(cid, {}).get('live')
    if img is None:
        raise HTTPException(404, 'camera chưa gửi hình')
    return Response(img, media_type='image/jpeg', headers={'Cache-Control': 'no-store'})


@app.get('/api/camera/{cid}/snapshot.jpg')
async def camera_snapshot(cid: str):
    img = hub.frames.get(cid, {}).get('raw') or hub.frames.get(cid, {}).get('live')
    if img is None:
        raise HTTPException(404, 'camera chưa gửi hình')
    return Response(img, media_type='image/jpeg', headers={'Cache-Control': 'no-store'})


@app.get('/api/crops/{name}')
async def crop(name: str):
    aid = name.removesuffix('.jpg')
    img = hub.crops.get(aid)
    if img is None:
        f = DATA / 'crops' / f'{aid}.jpg'
        if not f.exists():
            raise HTTPException(404)
        img = f.read_bytes()
    return Response(img, media_type='image/jpeg', headers={'Cache-Control': 'max-age=3600'})


@app.get('/api/alerts/{aid}/evidence/{name}')
async def evidence(aid: str, name: str):
    """Ảnh của gói xác minh: strip.jpg (dải 2x2), overview.jpg (toàn cảnh), ref.jpg (bàn lúc sạch)."""
    f = hub.evidence_file(aid, name.removesuffix('.jpg'))
    if f is None:
        raise HTTPException(404, 'không có ảnh này')
    return FileResponse(f, media_type='image/jpeg', headers={'Cache-Control': 'max-age=3600'})


# ------------------------------------------------------------------ nhân viên, quản lý
def nhan_vien(body):
    """Mã nhân viên trong body phải có trong danh sách, không thì việc 'đang xử lý' mà không ai làm."""
    sid = body.get('staff')
    if not any(s['id'] == sid for s in hub.staff):
        raise HTTPException(400, f'không có nhân viên {sid!r}')
    return sid


@app.post('/api/alerts/{aid}/ack')
async def ack(aid: str, body: dict = Body(...)):
    find(aid)
    return hub.ack(aid, nhan_vien(body))


@app.post('/api/alerts/{aid}/done')
async def done(aid: str, body: dict = Body(...)):
    find(aid)
    return hub.done(aid, body.get('staff'))


@app.post('/api/alerts/{aid}/cancel')
async def cancel(aid: str, body: dict = Body(...)):
    find(aid)
    return hub.cancel(aid, body.get('by') or 'manager', body.get('reason') or 'báo nhầm')


@app.post('/api/alerts/{aid}/assign')
async def assign(aid: str, body: dict = Body(...)):
    find(aid)
    return hub.assign_to(aid, nhan_vien(body))


@app.post('/api/alerts')
async def manual(body: dict = Body(...)):
    try:
        return hub.manual(body.get('kind'), body.get('table'), body.get('camera'))
    except ValueError:
        raise HTTPException(400, 'kind phải là call, needs_clearing hoặc new_guest')


# ------------------------------------------------------------------ cài đặt
@app.get('/api/zones')
async def get_zones(camera: str = Query('cam1')):
    return hub.get_zones(camera)


@app.put('/api/zones')
async def put_zones(body: dict = Body(...)):
    try:
        return hub.set_zones(body)
    except (KeyError, TypeError, ValueError) as e:
        raise HTTPException(400, f'vùng bàn sai dạng: {e}')


@app.get('/api/staff')
async def get_staff():
    return hub.staff_view()


@app.put('/api/staff')
async def put_staff(body: dict = Body(...)):
    items = body.get('staff') or []
    if any(s.get('role') not in ('serve', 'clean', 'cashier') or not s.get('id') or not s.get('name')
           for s in items):
        raise HTTPException(400, 'mỗi nhân viên cần id, name, role (serve, clean, cashier)')
    return hub.set_staff(items)


@app.put('/api/settings')
async def put_settings(body: dict = Body(...)):
    return hub.update_settings(body)


@app.post('/api/reset')
async def reset():
    hub.reset()
    return {}


# ------------------------------------------------------------------ LLM (Gemini hoặc kie.ai)
def report_text(r):
    rs = r['response_s']
    lines = [f"Từ {clock(r['from'])} đến {clock(r['to'])}",
             f"Gọi phục vụ: {r['counts']['call']}, cần dọn: {r['counts']['needs_clearing']}, "
             f"khách mới: {r['counts']['new_guest']}",
             f"Thời gian từ lúc báo tới lúc nhân viên nhận: trung bình {rs['mean']} giây, trung vị {rs['median']} "
             f"giây, 90% dưới {rs['p90']} giây",
             f"Huỷ (báo nhầm): {r['cancelled']}, trong đó {gemini.ten} lọc {r['rejected_by_gemini']}; "
             f"{gemini.ten} chưa xác minh được (vẫn báo nhân viên): {r['unverified']}; "
             f"chuyển người vì chưa ai nhận: {r['escalated']}"]
    for s in r['per_staff']:
        lines.append(f"Nhân viên {s['name']}: nhận {s['acked']}, xong {s['done']}, phản hồi trung bình "
                     f"{s['mean_response_s']} giây")
    for t in r['per_table']:
        lines.append(f"Bàn {t['table']}: gọi {t['calls']}, cần dọn {t['clearings']}, khách mới {t['guests']}")
    return '\n'.join(lines)


def plain_summary(r):
    rs = r['response_s']
    busiest = max(r['per_table'], key=lambda t: t['calls'] + t['clearings'], default=None)
    s = (f"Ca có {r['counts']['call']} lần khách gọi phục vụ, {r['counts']['needs_clearing']} lần bàn cần dọn "
         f"và {r['counts']['new_guest']} lượt khách mới. ")
    if rs['mean'] is not None:
        s += f"Nhân viên nhận việc sau trung bình {rs['mean']} giây (90% dưới {rs['p90']} giây). "
    if r['cancelled']:
        s += f"{r['cancelled']} báo động bị huỷ vì báo nhầm. "
    if r['escalated']:
        s += f"{r['escalated']} việc phải chuyển người vì chưa ai nhận kịp. "
    if busiest:
        s += f"Bàn bận nhất: {busiest['table']}."
    return s.strip()


@app.post('/api/assistant')
async def assistant(body: dict = Body(...)):
    """Trợ lý nhiều dạng trả lời (chữ, chỉ số, biểu đồ, sự kiện có ảnh, bảng, thẻ nhân viên). Tác tử Google ADK
    khi có GEMINI_API_KEY; không thì trả lời theo luật, không dùng AI. Xem server/tro_ly.py."""
    q = body.get('question')
    q = q.strip() if isinstance(q, str) else ''
    if not q:
        raise HTTPException(400, 'thiếu câu hỏi')
    return await tro_ly.hoi(q[:500], body.get('session'))


# ------------------------------------------------------------------ điện thoại làm camera
# Trang /phat trên iPhone gửi từng khung JPEG lên đây; pipeline đọc lại thành luồng MJPEG
# (chay_camera.bat http://localhost:8080/api/phone/cam1/mjpeg) như một camera IP bình thường.
phone_frames: dict[str, dict] = {}


@app.post('/api/phone/{cam}/frame')
async def phone_frame(cam: str, request: Request):
    body = await request.body()
    if not body.startswith(b'\xff\xd8') or len(body) > 3_000_000:
        raise HTTPException(400, 'cần ảnh JPEG nhỏ hơn 3 MB')
    cur = phone_frames.setdefault(cam, dict(jpeg=b'', seq=0, at=0.0))
    cur.update(jpeg=body, seq=cur['seq'] + 1, at=asyncio.get_event_loop().time())
    return dict(ok=True, seq=cur['seq'])


@app.websocket('/api/phone/{cam}/ws')
async def phone_ws(websocket: WebSocket, cam: str):
    """Kết nối liên tục: mỗi khung JPEG là một gói tin, không phải chờ máy chủ trả lời.

    Qua đường hầm internet, gửi từng ảnh bằng POST tốn ~0,4 s mỗi ảnh; WebSocket chỉ tốn
    một lần bắt tay rồi gửi liền, nên giữ được 5-8 khung/giây.
    """
    await websocket.accept()
    cur = phone_frames.setdefault(cam, dict(jpeg=b'', seq=0, at=0.0))
    loop = asyncio.get_event_loop()
    try:
        while True:
            body = await websocket.receive_bytes()
            if body.startswith(b'\xff\xd8') and len(body) < 3_000_000:
                cur.update(jpeg=body, seq=cur['seq'] + 1, at=loop.time())
    except (WebSocketDisconnect, RuntimeError):
        pass


@app.get('/api/phone/{cam}/status')
async def phone_status(cam: str):
    cur = phone_frames.get(cam)
    age = None if not cur else round(asyncio.get_event_loop().time() - cur['at'], 1)
    return dict(live=age is not None and age < 3, frames=cur['seq'] if cur else 0, age_s=age)


@app.get('/api/phone/{cam}/mjpeg')
async def phone_mjpeg(cam: str):
    async def gen():
        last = -1
        idle = 0
        while True:
            cur = phone_frames.get(cam)
            if cur and cur['seq'] != last:
                last, idle = cur['seq'], 0
                yield (b'--frame\r\nContent-Type: image/jpeg\r\nContent-Length: ' + str(len(cur['jpeg'])).encode()
                       + b'\r\n\r\n' + cur['jpeg'] + b'\r\n')
            else:
                idle += 1
                if idle > 1200:  # 60 s không có khung mới: đóng luồng để pipeline tự nối lại
                    return
            await asyncio.sleep(0.05)
    return StreamingResponse(gen(), media_type='multipart/x-mixed-replace; boundary=frame')


@app.get('/api/tts/status')
async def tts_status():
    return tts.status()


@app.get('/api/tts')
async def tts_wav(text: str = Query(..., max_length=200)):
    """Đọc tiếng Việt cho máy không có giọng Việt; 404 nếu máy chủ chưa cài Piper."""
    try:
        f = await tts.wav(text)
    except RuntimeError as e:
        raise HTTPException(502, str(e))
    if f is None:
        raise HTTPException(404, 'máy chủ chưa có giọng đọc')
    return FileResponse(f, media_type='audio/wav', headers={'Cache-Control': 'public, max-age=86400'})


@app.get('/api/report')
async def report():
    return hub.report()


@app.post('/api/report/summary')
async def report_summary():
    r = hub.report()
    if not gemini.enabled:
        return dict(text=plain_summary(r) + f' ({gemini.ten} chưa bật, đây là bản tóm tắt tự động.)')
    try:
        return dict(text=await gemini.summary(report_text(r), hub.log_text()))
    except GeminiError as e:
        raise HTTPException(502, f'{gemini.ten} lỗi: {e}')


# ------------------------------------------------------------------ camera (máy chạy pipeline) gửi lên
@app.post('/api/edge/event', dependencies=[Depends(edge_auth)])
async def edge_event(body: dict = Body(...)):
    b64 = body.get('crop_jpeg_b64')
    try:
        body['crop_jpeg'] = base64.b64decode(b64) if b64 else None
        # nhiều ảnh cho LLM: [{"role": "strip"|"overview"|"clean_ref", "jpeg_b64": "..."}]
        body['images'] = [dict(role=str(im['role']), jpeg=base64.b64decode(im['jpeg_b64']))
                          for im in body.get('images') or []]
        return dict(alert_id=hub.edge_event(body))
    except (KeyError, ValueError, TypeError) as e:
        raise HTTPException(400, str(e))


@app.post('/api/edge/evidence', dependencies=[Depends(edge_auth)])
async def edge_evidence(body: dict = Body(...)):
    """Gói ảnh xác minh của một sự kiện (gửi sau sự kiện ~1-1.5 s, cùng eid)."""
    try:
        if not body.get('eid'):
            raise ValueError('thiếu eid')
        for role in ('strip', 'overview', 'ref'):
            b64 = body.get(f'{role}_jpeg_b64')
            body[f'{role}_jpeg'] = base64.b64decode(b64) if b64 else None
        return dict(alert_id=hub.edge_evidence(body))
    except (KeyError, ValueError, TypeError) as e:
        raise HTTPException(400, str(e))


@app.post('/api/edge/frame', dependencies=[Depends(edge_auth)])
async def edge_frame(request: Request, camera: str = Query(...), kind: str = Query('live'),
                     fps: float | None = None, source: str | None = None, w: int | None = None,
                     h: int | None = None):
    data = await request.body()
    if not data:
        raise HTTPException(400, 'thiếu ảnh')
    hub.edge_frame(camera, 'raw' if kind == 'raw' else 'live', data, fps, source, w, h)
    return dict(ok=True)


@app.post('/api/edge/tables', dependencies=[Depends(edge_auth)])
async def edge_tables(body: dict = Body(...)):
    tables = body.get('tables') or []
    if not isinstance(body.get('camera'), str) or not isinstance(tables, list) or             not all(isinstance(t, dict) and 'id' in t for t in tables):
        raise HTTPException(400, 'cần camera (chuỗi) và tables là danh sách {id, state, people}')
    try:
        hub.edge_tables(body['camera'], tables)
    except (TypeError, ValueError) as e:
        raise HTTPException(400, f'trạng thái bàn sai dạng: {e}')
    return dict(ok=True)


# ------------------------------------------------------------------ web app đã build (một dịch vụ Cloud Run)
@app.get('/{path:path}', include_in_schema=False)
async def spa(path: str):
    if path.startswith('api/'):
        return JSONResponse({'detail': 'Not Found'}, status_code=404)
    if not DIST.exists():
        return JSONResponse({'detail': 'Chưa build web app: chạy npm run build trong easy-fnb'}, status_code=404)
    f = (DIST / path).resolve()
    if path and f.is_file() and DIST.resolve() in f.parents:
        # tệp trong assets/ có mã băm trong tên nên giữ được lâu; các tệp khác hỏi lại mỗi lần
        cache = 'public, max-age=31536000, immutable' if path.startswith('assets/') else 'no-cache'
        return FileResponse(f, headers={'Cache-Control': cache})
    return FileResponse(DIST / 'index.html', headers={'Cache-Control': 'no-cache'})
