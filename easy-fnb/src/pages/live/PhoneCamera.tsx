import { useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router';
import { Camera, CameraOff } from 'lucide-react';
import { useTitle } from '../../live/hooks';
import { apiUrl } from '../../live/api';

const FPS = 6;
const WIDTH = 960;
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

  const stop = () => {
    stream.current?.getTracks().forEach((t) => t.stop());
    stream.current = null;
    socket.current?.close();
    socket.current = null;
    setState('idle');
  };

  useEffect(() => stop, []);

  const start = async () => {
    try {
      const s = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: 'environment' }, width: { ideal: 1920 }, height: { ideal: 1080 } },
        audio: false,
      });
      stream.current = s;
      const v = video.current!;
      v.srcObject = s;
      await v.play();
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
      const w = Math.min(WIDTH, v.videoWidth);
      const h = Math.round((v.videoHeight * w) / v.videoWidth);
      if (canvas.width !== w) {
        canvas.width = w;
        canvas.height = h;
        setSize(`${w}×${h}`);
      }
      canvas.getContext('2d')!.drawImage(v, 0, 0, w, h);
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
          Dựng điện thoại cố định nhìn xuống các bàn, cắm sạc, để màn hình sáng. Camera này gửi hình về máy chủ; không lưu video.
        </p>
        <video ref={video} playsInline muted className="crop crop--lg" style={{ display: state === 'live' ? 'block' : 'none' }} />
        {state === 'live' ? (
          <>
            <p className="small amber" role="status">
              Đang phát {size} · đã gửi {sent} khung{fails ? ` · lỗi ${fails}` : ''}
              {carrier === 'http' ? ' · đang dùng đường dự phòng, hơi chậm' : ''}
            </p>
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
