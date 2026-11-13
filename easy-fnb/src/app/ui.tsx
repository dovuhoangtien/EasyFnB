import { useEffect, useState, type ReactNode } from 'react';
import { BrushCleaning, Hand, ImageOff, UserPlus } from 'lucide-react';
import { Badge } from '@astryxdesign/core/Badge';
import { Lightbox, type LightboxMedia } from '@astryxdesign/core/Lightbox';
import { StatusDot } from '@astryxdesign/core/StatusDot';
import { Text } from '@astryxdesign/core/Text';
import { apiUrl, getInfo, type Info } from '../live/api';
import type { ConnStatus } from '../live/store';
import { KIND_LABEL, tableText } from '../live/text';
import type { Alert, AlertKind, Tone } from '../live/types';

export const KIND_ICON = { call: Hand, needs_clearing: BrushCleaning, new_guest: UserPlus } as const;
const KIND_VARIANT = { call: 'error', needs_clearing: 'warning', new_guest: 'info' } as const;

export function KindBadge({ kind }: { kind: AlertKind }) {
  const I = KIND_ICON[kind];
  return <Badge variant={KIND_VARIANT[kind]} label={KIND_LABEL[kind]} icon={<I size={12} aria-hidden="true" />} />;
}

/** Trạng thái kết nối tới máy chủ, gọn để đặt trên thanh trên cùng */
export function Conn({ status }: { status: ConnStatus }) {
  const label = status === 'live' ? 'Trực tiếp' : status === 'offline' ? 'Mất kết nối' : 'Đang kết nối';
  return (
    <span className="inline-flex items-center gap-2" role="status" aria-live="polite">
      <StatusDot
        variant={status === 'live' ? 'success' : status === 'offline' ? 'error' : 'neutral'}
        label={label}
        isPulsing={status === 'live'}
      />
      <Text type="supporting" color="secondary">
        {label}
      </Text>
    </span>
  );
}

/** Giọng đọc trên điện thoại nhân viên lấy từ đâu */
export function voiceText(info: Info | null) {
  if (!info?.tts) return 'Đang kiểm tra';
  if (!info.tts.enabled || !info.tts.engine) return 'Giọng có sẵn trên điện thoại';
  return `Giọng ${info.tts.voice ?? info.tts.engine}, đọc từ máy chủ`;
}

export const toneColor = (tone: Tone | undefined) =>
  tone === 'good' ? 'var(--color-text-success)' : tone === 'warn' ? 'var(--color-text-warning)' : tone === 'bad' ? 'var(--color-text-error)' : undefined;

/** Ảnh bằng chứng của một việc để mở trong Lightbox: ảnh cắt, dải 4 khung, toàn cảnh */
export function alertMedia(a: Pick<Alert, 'crop_url' | 'evidence' | 'table' | 'kind'>): LightboxMedia[] {
  const what = `${KIND_LABEL[a.kind]}, ${tableText(a.table)}`;
  const out: LightboxMedia[] = [];
  if (a.crop_url) out.push({ src: apiUrl(a.crop_url), alt: `Ảnh camera: ${what}`, caption: 'Ảnh camera lúc xảy ra' });
  if (a.evidence?.strip) out.push({ src: apiUrl(a.evidence.strip), alt: `Bốn khung hình quanh sự kiện: ${what}`, caption: 'Bốn khung hình quanh sự kiện' });
  if (a.evidence?.overview) out.push({ src: apiUrl(a.evidence.overview), alt: `Toàn cảnh: ${what}`, caption: 'Toàn cảnh, chỗ xảy ra được khoanh lại' });
  return out;
}

/** Ảnh nhỏ bấm vào thì phóng to; không có ảnh thì hiện ô trống */
export function Shot({ media, size = 64, className = '' }: { media: LightboxMedia[]; size?: number | 'fill'; className?: string }) {
  const [open, setOpen] = useState(false);
  const [failed, setFailed] = useState(false);
  const first = media[0];
  const box = size === 'fill' ? undefined : { width: size, height: size };
  if (!first || failed) {
    return (
      <span className={`fx-shot fx-shot--empty ${className}`} style={box} aria-hidden="true">
        <ImageOff size={18} />
      </span>
    );
  }
  return (
    <>
      <button type="button" className={`fx-shot ${className}`} style={box} onClick={() => setOpen(true)} aria-label={`Phóng to: ${first.alt}`}>
        <img src={first.src} alt="" loading="lazy" onError={() => setFailed(true)} />
      </button>
      {open && <Lightbox isOpen onOpenChange={setOpen} media={media} hasZoom />}
    </>
  );
}

/**
 * "Clip" ngắn từ dải 2x2 (4 khung quanh sự kiện): chiếu lần lượt từng khung.
 * Đây không phải video thật, chỉ là 4 ảnh máy camera đã gửi.
 */
export function Flipbook({ src, alt, fallback }: { src: string; alt: string; fallback?: ReactNode }) {
  const [frame, setFrame] = useState(0);
  const [ratio, setRatio] = useState<number | null>(null);
  const [failed, setFailed] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const img = new Image();
    img.onload = () => setRatio(img.naturalWidth / Math.max(1, img.naturalHeight));
    img.onerror = () => setFailed(true);
    img.src = src;
  }, [src]);

  useEffect(() => {
    if (ratio === null || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const t = window.setInterval(() => setFrame((f) => (f + 1) % 4), 550);
    return () => window.clearInterval(t);
  }, [ratio]);

  if (failed) return <>{fallback ?? null}</>;
  return (
    <>
      <button
        type="button"
        className="fx-flip"
        style={{
          aspectRatio: String(ratio ?? 16 / 9),
          backgroundImage: ratio === null ? undefined : `url("${src}")`,
          backgroundPosition: `${(frame % 2) * 100}% ${Math.floor(frame / 2) * 100}%`,
        }}
        onClick={() => setOpen(true)}
        aria-label={`Xem lớn: ${alt}`}
      >
        <span className="fx-flip-tag">Khung {frame + 1}/4</span>
      </button>
      {open && <Lightbox isOpen onOpenChange={setOpen} media={{ src, alt, caption: 'Bốn khung hình quanh sự kiện' }} hasZoom />}
    </>
  );
}

const LOCAL_HOSTS = new Set(['localhost', '127.0.0.1', '[::1]']);

/** Gốc link cho điện thoại: đang mở bằng localhost thì đổi sang địa chỉ Wi-Fi của máy chủ */
export function usePhoneBase() {
  const [base, setBase] = useState(location.origin);
  useEffect(() => {
    if (!LOCAL_HOSTS.has(location.hostname)) return;
    let alive = true;
    getInfo()
      .then((i) => {
        if (alive && i.lan_ip) setBase(`${location.protocol}//${i.lan_ip}${location.port ? `:${location.port}` : ''}`);
      })
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, []);
  return base;
}

/** Tiêu đề một khối trong trang: chữ vừa, không viết hoa cả câu */
export function SectionTitle({ children, end }: { children: ReactNode; end?: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3 min-h-8">
      <Text type="label" weight="semibold" as="h2">
        {children}
      </Text>
      {end}
    </div>
  );
}
