import { useEffect, useState } from 'react';
import { Copy } from 'lucide-react';
import { IconButton } from '@astryxdesign/core/IconButton';
import { useToast } from '@astryxdesign/core/Toast';
import { apiUrl, type Info } from '../live/api';

/** Dùng chung cho trang Cài đặt và khối cài đặt trong trợ lý: link mã QR, điện thoại nào đang phát, nút chép */

export const LOCAL = new Set(['localhost', '127.0.0.1', '[::1]']);

export const PHONE_CAMS = ['cam1', 'cam2', 'cam3', 'cam4'];

/** Địa chỉ trang /phat cho một camera. Camera điện thoại bắt buộc https: trên Cloud Run đã có sẵn, chạy ở quán thì cần cổng https của máy chủ. */
export function phoneCameraUrl(info: Info | null, cam: string) {
  const path = `/phat?cam=${encodeURIComponent(cam)}`;
  if (!LOCAL.has(location.hostname)) {
    // mở dashboard bằng địa chỉ wifi qua http mà máy chủ có cổng https: mã QR phải trỏ sang cổng https đó
    if (location.protocol !== 'https:' && info?.https_port) return { url: `https://${location.hostname}:${info.https_port}${path}`, secure: true };
    return { url: `${location.origin}${path}`, secure: location.protocol === 'https:' };
  }
  const host = info?.lan_ip ?? 'localhost';
  if (info?.https_port) return { url: `https://${host}:${info.https_port}${path}`, secure: true };
  const port = import.meta.env.DEV ? '8080' : location.port || '80';
  return { url: `http://${host}:${port}${path}`, secure: false };
}

/** Điện thoại nào đang gửi hình lên máy chủ (hỏi mỗi 2 giây) */
export function usePhonesLive(cams: string[] = PHONE_CAMS) {
  const [on, setOn] = useState<Record<string, boolean>>({});
  const key = cams.join(',');
  useEffect(() => {
    let stop = false;
    const poll = async () => {
      const out: Record<string, boolean> = {};
      await Promise.all(
        key.split(',').map(async (c) => {
          try {
            const r = await fetch(apiUrl(`/api/phone/${c}/status`));
            out[c] = r.ok && (await r.json()).live === true;
          } catch {
            out[c] = false;
          }
        }),
      );
      if (!stop) setOn(out);
    };
    void poll();
    const t = window.setInterval(() => void poll(), 2000);
    return () => {
      stop = true;
      window.clearInterval(t);
    };
  }, [key]);
  return on;
}

export function CopyBlock({ text, label }: { text: string; label: string }) {
  const toast = useToast();
  const copy = () => {
    navigator.clipboard
      .writeText(text)
      .then(() => toast({ body: 'Đã chép' }))
      .catch(() => toast({ body: 'Không chép được, hãy bôi đen rồi chép tay.', type: 'error', isAutoHide: true }));
  };
  return (
    <div className="flex items-start gap-2">
      <pre className="fx-code">{text}</pre>
      <IconButton label={label} tooltip={label} variant="secondary" icon={<Copy size={16} />} onClick={copy} />
    </div>
  );
}
