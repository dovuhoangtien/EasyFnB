import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError, apiUrl } from './api';

/**
 * Phòng chat của quán và ảnh thanh toán (server/chat.py).
 * Luồng SSE riêng /api/chat/stream, không đụng luồng việc camera /api/stream.
 */

export type PaymentType = 'chuyen_khoan' | 'hoa_don' | 'phieu_thu' | 'khac';
export const PAYMENT_TYPE_LABEL: Record<PaymentType, string> = {
  chuyen_khoan: 'Chuyển khoản',
  hoa_don: 'Hoá đơn',
  phieu_thu: 'Phiếu thu',
  khac: 'Ảnh thường',
};

export interface PaymentItem {
  name: string;
  qty: number;
  price: number;
}

export interface PaymentFields {
  type: PaymentType;
  amount: number | null;
  paid_at: string | null;
  table: string | null;
  items: PaymentItem[];
  bank: string | null;
  sender_name: string | null;
  memo: string | null;
  txn_id: string | null;
  receipt_no: string | null;
}

export interface PaymentMatch {
  visit: string | null;
  ok: boolean;
  text: string;
}

export interface Payment extends PaymentFields {
  id: number;
  ts: number;
  day: string;
  staff: string;
  status: 'confirmed' | 'void';
  image: string | null;
  visit: string | null;
  confirmed_by: string | null;
  note: string | null;
  match?: PaymentMatch | null;
}

export interface ChatMsg {
  id: number;
  ts: number;
  day: string;
  sender: string;
  to: string[];
  kind: 'text' | 'photo' | 'payment' | 'ai' | 'summary' | 'reminder';
  text: string | null;
  image: string | null;
  payment_id: number | null;
  reply_to: number | null;
  payment?: Payment;
}

export interface ScanResult {
  scan_id: string;
  image: string;
  engine: 'gemini' | 'manual';
  error: string | null;
  ms: number;
  fields: PaymentFields;
  unsure: (keyof PaymentFields)[];
  warnings: string[];
  is_payment: boolean;
}

export interface RevenueReview {
  kind: 'no_payment' | 'no_visit';
  text: string;
  visit?: string;
  payment_id?: number;
  table: string;
}

export interface Revenue {
  day: string;
  total: number;
  count: number;
  transfers: number;
  visits: number;
  per_guest: number | null;
  hours: { hour: string; amount: number; visits: number }[];
  review: RevenueReview[];
  payments: Payment[];
}

export const chatImageUrl = (name: string) => apiUrl(`/api/chat/image/${name}`);
export const money = (n: number | null | undefined) => (n == null ? 'Chưa rõ' : `${n.toLocaleString('vi-VN')} đ`);
export const clockText = (ms: number) => new Date(ms).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Ho_Chi_Minh' });

async function call<T>(method: string, path: string, body?: unknown): Promise<T> {
  let res: Response;
  try {
    res = await fetch(apiUrl(path), {
      method,
      headers: body === undefined ? { Accept: 'application/json' } : { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError('Không kết nối được máy chủ. Kiểm tra mạng.', 0);
  }
  const text = await res.text();
  let data: unknown = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    // giữ null
  }
  if (!res.ok) {
    const detail = data && typeof data === 'object' && 'detail' in data ? String((data as { detail: unknown }).detail) : `Máy chủ báo lỗi (mã ${res.status}).`;
    throw new ApiError(detail, res.status);
  }
  return data as T;
}

export const postMessage = (from: string, text: string, to?: string[]) => call<ChatMsg>('POST', '/api/chat', { from, text, to });
export const sendScan = (scanId: string, by: string, fields: Partial<PaymentFields>, text?: string) =>
  call<ChatMsg>('POST', `/api/chat/scan/${encodeURIComponent(scanId)}/send`, { by, fields, text });
export const patchPayment = (id: number, by: string, fields: Partial<PaymentFields>) => call<Payment>('PATCH', `/api/payments/${id}`, { by, ...fields });
export const voidPayment = (id: number, by: string, reason: string) => call<Payment>('POST', `/api/payments/${id}/void`, { by, reason });
export const getRevenue = (day?: string) => call<Revenue>('GET', `/api/revenue${day ? `?day=${encodeURIComponent(day)}` : ''}`);
export const noteVisit = (visit: string, by: string, reason: string) => call<{ ok: boolean }>('POST', `/api/visits/${encodeURIComponent(visit)}/note`, { by, reason });

/** Gửi ảnh để Gemini đọc. Dùng XHR để có tiến độ tải lên thật (0..1) cho thanh tiến trình. */
export function scanPayment(staff: string, jpeg: Blob, table: string | null, onUpload: (f: number) => void, signal?: AbortSignal): Promise<ScanResult> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const q = new URLSearchParams({ staff });
    if (table) q.set('table', table);
    xhr.open('POST', apiUrl(`/api/chat/scan?${q}`));
    xhr.setRequestHeader('Content-Type', 'image/jpeg');
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onUpload(e.loaded / e.total);
    };
    xhr.upload.onload = () => onUpload(1);
    xhr.onload = () => {
      let data: unknown = null;
      try {
        data = JSON.parse(xhr.responseText);
      } catch {
        // để null
      }
      if (xhr.status >= 200 && xhr.status < 300) resolve(data as ScanResult);
      else {
        const detail = data && typeof data === 'object' && 'detail' in data ? String((data as { detail: unknown }).detail) : `Máy chủ báo lỗi (mã ${xhr.status}).`;
        reject(new ApiError(detail, xhr.status));
      }
    };
    xhr.onerror = () => reject(new ApiError('Không gửi được ảnh. Kiểm tra mạng.', 0));
    xhr.onabort = () => reject(new ApiError('Đã huỷ', 0));
    signal?.addEventListener('abort', () => xhr.abort());
    xhr.send(jpeg);
  });
}

/** Thu nhỏ ảnh chụp còn cạnh dài 1600 px, JPEG 0.85 (khoảng 250 KB) trước khi gửi */
export async function shrinkPhoto(file: Blob, maxSide = 1600): Promise<Blob> {
  const bmp = await createImageBitmap(file);
  const k = Math.min(1, maxSide / Math.max(bmp.width, bmp.height));
  const w = Math.round(bmp.width * k);
  const h = Math.round(bmp.height * k);
  const canvas = document.createElement('canvas');
  canvas.width = w;
  canvas.height = h;
  canvas.getContext('2d')!.drawImage(bmp, 0, 0, w, h);
  bmp.close();
  return new Promise((resolve, reject) => canvas.toBlob((b) => (b ? resolve(b) : reject(new Error('Không xử lý được ảnh'))), 'image/jpeg', 0.85));
}

/** Tin trong phòng, cập nhật trực tiếp. Trả thêm `aiBusy` khi AI đang soạn câu trả lời. */
export function useChatRoom() {
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [aiBusy, setAiBusy] = useState(false);
  const [online, setOnline] = useState(false);
  const last = useRef(0);

  const merge = useCallback((list: ChatMsg[]) => {
    if (!list.length) return;
    setMessages((cur) => {
      const map = new Map(cur.map((m) => [m.id, m]));
      for (const m of list) map.set(m.id, m);
      const out = [...map.values()].sort((a, b) => a.id - b.id).slice(-300);
      last.current = out.at(-1)?.id ?? last.current;
      return out;
    });
  }, []);

  useEffect(() => {
    let alive = true;
    const es = new EventSource(apiUrl('/api/chat/stream'));
    const fetchNew = async () => {
      try {
        const r = await call<{ messages: ChatMsg[]; ai_busy: boolean }>('GET', `/api/chat${last.current ? `?since=${last.current}&limit=200` : ''}`);
        if (!alive) return;
        merge(r.messages);
        setAiBusy(r.ai_busy);
        setLoaded(true);
      } catch {
        // thử lại khi luồng nối lại
      }
    };
    es.addEventListener('hello', () => {
      setOnline(true);
      void fetchNew();
    });
    es.addEventListener('message', (ev) => merge([JSON.parse((ev as MessageEvent<string>).data) as ChatMsg]));
    es.addEventListener('payment', (ev) => {
      const p = JSON.parse((ev as MessageEvent<string>).data) as Payment;
      setMessages((cur) => cur.map((m) => (m.payment_id === p.id ? { ...m, payment: p } : m)));
    });
    es.addEventListener('ai', (ev) => setAiBusy(Boolean((JSON.parse((ev as MessageEvent<string>).data) as { busy: boolean }).busy)));
    es.onerror = () => setOnline(false);
    return () => {
      alive = false;
      es.close();
    };
  }, [merge]);

  return { messages, loaded, aiBusy, online, merge };
}
