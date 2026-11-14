import { useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router';
import { Camera, CameraOff } from 'lucide-react';
import { useTitle } from '../../live/hooks';
import { apiUrl } from '../../live/api';

const FPS = 12; // mạng wifi trong quán chịu được; chủ quán xem hình gốc mượt hơn
// Khung gửi đi luôn ngang và cùng một cỡ: xoay máy hay đổi ống kính giữa chừng thì camera AI vẫn nhận đúng cỡ cũ,
// không vỡ hình, vùng bàn không lệch. Cầm dọc thì hình nằm giữa, hai bên viền đen.
const OUT_W = 960;
const OUT_H = 540;
/** ống kính góc siêu rộng (0.5×) trên iPhone/Android: tên thiết bị có chữ ultra, siêu rộng, 0.5 */
const ULTRA = /ultra|siêu rộng|sieu rong|0[.,]5/i;
type Lens = 'main' | 'wide';
const QUALITY = 0.62;
const MAX_PENDING = 1_200_000; // chờ gửi quá 1,2 MB thì bỏ khung, không dồn hàng đợi
const MAX_POSTS = 3; // nếu không dùng được WebSocket thì gửi chồng 3 ảnh một lúc

/** Dùng điện thoại làm camera: gửi từng khung JPEG lên máy chủ, pipeline đọc lại như camera IP. Mở bằng HTTPS (Safari chặn camera ở http). */
export default function PhoneCamera() {
  useTitle('Điện thoại làm camera, Easy FnB');
  const [params] = useSearchParams();
  const cam = params.get('cam') || 'cam1';
  const video = useRef<HTMLVideoElement>(null);
  const stream = useRef<MediaStream | null>(null);
  const socket = useRef<WebSocket | null>(null);
  const [state, setState] = useState<'idle' | 'live' | 'error'>('idle');
  const [error, setError] = useState('');
  const [carrier, setCarrier] = useState<'ws' | 'http' | ''>('');
  const [sent, setSent] = useState(0);
  const [fails, setFails] = useState(0);
  const [size, setSize] = useState('');
  const [lens, setLens] = useState<Lens>('main');
  const [note, setNote] = useState('');

  const stop = () => {
    stream.current?.getTracks().forEach((t) => t.stop());
    stream.current = null;
    socket.current?.close();
    socket.current = null;
    setState('idle');
  };

  useEffect(() => stop, []);

  /** Mở camera sau. wide: tìm ống góc siêu rộng theo tên (tên chỉ đọc được sau lần cho phép đầu), không có thì thử zoom nhỏ nhất. */
  const open = async (want: Lens) => {
    const size = { width: { ideal: 1920 }, height: { ideal: 1080 } };
    let c: MediaTrackConstraints = { facingMode: { ideal: 'environment' }, ...size };
    let ultra: MediaDeviceInfo | undefined;
    if (want === 'wide') {
      ultra = (await navigator.mediaDevices.enumerateDevices()).find((d) => d.kind === 'videoinput' && ULTRA.test(d.label));
      if (ultra) c = { deviceId: { exact: ultra.deviceId }, ...size };
    }
    stream.current?.getTracks().forEach((t) => t.stop());
    const s = await navigator.mediaDevices.getUserMedia({ video: c, audio: false });
    let got: Lens = want;
    setNote('');
    if (want === 'wide' && !ultra) {
      const track = s.getVideoTracks()[0];
      const zoom = (track.getCapabilities?.() as { zoom?: { min: number } } | undefined)?.zoom;
      if (zoom && zoom.min < 1) {
        await track.applyConstraints({ advanced: [{ zoom: zoom.min } as MediaTrackConstraintSet] }).catch(() => undefined);
      } else {
        got = 'main';
        setNote('Máy này không cho trang web dùng ống 0.5×, đang dùng ống thường.');
      }
    }
    stream.current = s;
    const v = video.current!;
    v.srcObject = s;
    await v.play();
    setLens(got);
  };

  const switchLens = async (want: Lens) => {
    try {
      await open(want);
    } catch (e) {
      setNote(`Không đổi được ống kính: ${(e as Error).message}`);
      await open('main').catch(() => setState('error'));
    }
  };

  const start = async () => {
    try {
      await open('main');
      setState('live');
      void navigator.wakeLock?.request('screen').catch(() => {});
    } catch (e) {
      setError(
        window.isSecureContext
          ? `Không mở được camera: ${(e as Error).message}. Cho phép camera cho trang này trong Cài đặt Safari.`
          : 'Trang này đang mở bằng http nên Safari chặn camera. Mở lại bằng địa chỉ https (xem HUONG_DAN.md, phần điện thoại làm camera).',
      );
      setState('error');
    }
  };

  // Một kết nối WebSocket: gửi liền từng khung, không phải chờ máy chủ trả lời như POST.
  useEffect(() => {
    if (state !== 'live') return;
    const u = new URL(apiUrl(`/api/phone/${encodeURIComponent(cam)}/ws`), window.location.href);
    u.protocol = u.protocol === 'https:' ? 'wss:' : 'ws:';
    let closed = false;
    const open = () => {
      if (closed) return;
      try {
        const ws = new WebSocket(u.toString());
        ws.binaryType = 'arraybuffer';
        ws.onopen = () => setCarrier('ws');
        ws.onclose = () => {
          socket.current = null;
          if (!closed) {
            setCarrier('http');
            window.setTimeout(open, 2000); // nối lại sau 2 s; trong lúc đó vẫn gửi bằng POST
          }
        };
        ws.onerror = () => ws.close();
        socket.current = ws;
      } catch {
        setCarrier('http');
      }
    };
    open();
    return () => {
      closed = true;
      socket.current?.close();
      socket.current = null;
      setCarrier('');
    };
  }, [state, cam]);

  useEffect(() => {
    if (state !== 'live') return;
    const v = video.current!;
    const canvas = document.createElement('canvas');
    let pending = 0;
    const timer = window.setInterval(() => {
      if (!v.videoWidth) return;
      const ws = socket.current;
      const live = ws?.readyState === WebSocket.OPEN;
      if (!live && pending >= MAX_POSTS) return;
      if (live && ws!.bufferedAmount > MAX_PENDING) return; // mạng chậm: bỏ khung cũ, không dồn
      if (canvas.width !== OUT_W) {
        canvas.width = OUT_W;
        canvas.height = OUT_H;
      }
      // vừa khít khung ngang cố định, giữ đúng tỉ lệ; phần thừa tô đen
      const k = Math.min(OUT_W / v.videoWidth, OUT_H / v.videoHeight);
      const dw = Math.round(v.videoWidth * k);
      const dh = Math.round(v.videoHeight * k);
      const g = canvas.getContext('2d')!;
      g.fillStyle = '#000';
      g.fillRect(0, 0, OUT_W, OUT_H);
      g.drawImage(v, (OUT_W - dw) / 2, (OUT_H - dh) / 2, dw, dh);
      const portrait = v.videoHeight > v.videoWidth;
      setSize((old) => {
        const next = portrait ? 'dọc' : 'ngang';
        return old === next ? old : next;
      });
      pending += 1;
      canvas.toBlob(
        (blob) => {
          if (!blob) {
            pending -= 1;
            return;
          }
          if (ws?.readyState === WebSocket.OPEN) {
            ws.send(blob);
            pending -= 1;
            setSent((n) => n + 1);
          } else {
            fetch(apiUrl(`/api/phone/${encodeURIComponent(cam)}/frame`), {
              method: 'POST',
              body: blob,
              headers: { 'content-type': 'image/jpeg' },
            })
              .then((r) => (r.ok ? setSent((n) => n + 1) : setFails((n) => n + 1)))
              .catch(() => setFails((n) => n + 1))
              .finally(() => {
                pending -= 1;
              });
          }
        },
        'image/jpeg',
        QUALITY,
      );
    }, 1000 / FPS);
    return () => window.clearInterval(timer);
  }, [state, cam]);

  return (
    <div className="phone">
      <section className="panel phone-sound">
        <h1>Điện thoại làm camera {cam}</h1>
        <p className="small ink2">
          Dựng điện thoại cố định nhìn xuống các bàn, cắm sạc, để màn hình sáng. Quay ngang hay dọc đều được, ngang thấy nhiều bàn hơn.
        </p>
        <video ref={video} playsInline muted className="crop crop--lg" style={{ display: state === 'live' ? 'block' : 'none' }} />
        {state === 'live' ? (
          <>
            <p className="small amber" role="status">
              Đang phát, đã gửi {sent} khung{fails ? `, lỗi ${fails}` : ''}
              {carrier === 'http' ? '. Đang dùng đường dự phòng, hơi chậm' : ''}
            </p>
            {size === 'dọc' && <p className="small ink2">Đang cầm dọc. Xoay ngang máy để thấy được nhiều bàn hơn.</p>}
            <div className="flex gap-2" role="group" aria-label="Ống kính">
              <button type="button" className={`btn${lens === 'wide' ? ' btn--primary' : ''}`} aria-pressed={lens === 'wide'} onClick={() => void switchLens('wide')}>
                0.5×
              </button>
              <button type="button" className={`btn${lens === 'main' ? ' btn--primary' : ''}`} aria-pressed={lens === 'main'} onClick={() => void switchLens('main')}>
                1×
              </button>
            </div>
            {note && <p className="small ink2">{note}</p>}
            <button type="button" className="btn btn--lg" onClick={stop}>
              <CameraOff size={18} aria-hidden="true" />
              Dừng
            </button>
          </>
        ) : (
          <button type="button" className="btn btn--primary btn--lg" onClick={() => void start()}>
            <Camera size={18} aria-hidden="true" />
            Bắt đầu phát
          </button>
        )}
        {state === 'error' && <p className="small bad">{error}</p>}
      </section>
    </div>
  );
}
