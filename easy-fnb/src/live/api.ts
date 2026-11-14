import type {
  Alert,
  AlertKind,
  AssistantAnswer,
  CameraZones,
  ClipRequest,
  Point,
  Report,
  Settings,
  SettingsPatch,
  Staff,
  StaffInput,
  StaffPhoto,
  State,
} from './types';

/**
 * Gọi máy chủ Easy FnB. Khi chạy dev, Vite chuyển /api sang cổng 8080;
 * khi triển khai, cùng một dịch vụ Cloud Run phục vụ cả web lẫn /api.
 * VITE_API_BASE chỉ cần khi web và máy chủ nằm ở hai địa chỉ khác nhau.
 */
const BASE = String(import.meta.env.VITE_API_BASE ?? '').replace(/\/$/, '');

/** Đường dẫn đầy đủ tới một tài nguyên của máy chủ, ví dụ ảnh cắt "/api/crops/a12.jpg" */
export function apiUrl(path: string) {
  return path.startsWith('/') ? `${BASE}${path}` : path;
}

export const frameUrl = (camera: string, version: number) =>
  apiUrl(`/api/camera/${encodeURIComponent(camera)}/frame.jpg?v=${version}`);

export const snapshotUrl = (camera: string, bust: number) =>
  apiUrl(`/api/camera/${encodeURIComponent(camera)}/snapshot.jpg?t=${bust}`);

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

/** Lời báo lỗi tiếng Việt từ phản hồi của máy chủ (FastAPI trả {"detail": ...}) */
async function errorText(res: Response) {
  let body = '';
  try {
    body = await res.text();
  } catch {
    // bỏ qua, dùng mã lỗi
  }
  if (body) {
    try {
      const parsed: unknown = JSON.parse(body);
      if (parsed && typeof parsed === 'object' && 'detail' in parsed) {
        const detail = (parsed as { detail: unknown }).detail;
        if (typeof detail === 'string') return detail;
      }
    } catch {
      if (body.length < 200 && !body.trimStart().startsWith('<')) return body;
    }
  }
  if (res.status === 502 || res.status === 503 || res.status === 504 || (res.status >= 500 && !body)) {
    return `Máy chủ không phản hồi (mã ${res.status}). Kiểm tra máy chủ Easy FnB đang chạy.`;
  }
  if (res.status === 404) return 'Máy chủ không có dữ liệu này (mã 404).';
  return `Máy chủ báo lỗi (mã ${res.status}).`;
}

async function request<T>(method: string, path: string, body?: unknown, extra?: Record<string, string>): Promise<T> {
  let res: Response;
  try {
    res = await fetch(apiUrl(path), {
      method,
      headers: { Accept: 'application/json', ...(body === undefined ? {} : { 'Content-Type': 'application/json' }), ...extra },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError('Không kết nối được máy chủ. Kiểm tra mạng và máy chủ Easy FnB.', 0);
  }
  if (!res.ok) throw new ApiError(await errorText(res), res.status);
  const text = await res.text();
  try {
    return (text ? JSON.parse(text) : {}) as T;
  } catch {
    throw new ApiError('Máy chủ trả về dữ liệu không đọc được.', res.status);
  }
}

/** Thông điệp lỗi gọn để hiện lên toast */
export function errorMessage(err: unknown) {
  if (err instanceof Error && err.message) return err.message;
  return 'Có lỗi không rõ khi gọi máy chủ.';
}

// ---------- đọc ----------
export const getState = () => request<State>('GET', '/api/state');
export const getZones = (camera: string) => request<CameraZones>('GET', `/api/zones?camera=${encodeURIComponent(camera)}`);
export const getStaff = () => request<Staff[]>('GET', '/api/staff');
export const getReport = () => request<Report>('GET', '/api/report');
/** Tình trạng các phần của hệ thống (máy chủ, AI, giọng đọc) */
export interface Info {
  lan_ip: string | null;
  /** cổng https của máy chủ (chỉ khi chạy với --https), để camera điện thoại dùng được */
  https_port?: number | null;
  gemini: boolean;
  provider?: string;
  model: string | null;
  /** tên biến môi trường chứa khoá AI mà máy chủ đang đọc */
  key_name?: string;
  assistant?: 'adk' | 'rules';
  assistant_model?: string | null;
  tts?: { enabled: boolean; engine: string | null; voice: string | null };
  cloud?: boolean;
  edge_key?: boolean;
  uptime_s?: number;
  subscribers?: number;
}
export const getInfo = () => request<Info>('GET', '/api/info');

export interface AiTest {
  ok: boolean;
  provider?: string;
  model?: string | null;
  ms?: number;
  reply?: string;
  error?: string;
}
export const testAi = () => request<AiTest>('POST', '/api/ai/test');

// ---------- việc ----------
const alertPath = (id: string, action: string) => `/api/alerts/${encodeURIComponent(id)}/${action}`;

export const ackAlert = (id: string, staff: string) => request<Alert>('POST', alertPath(id, 'ack'), { staff });
export const doneAlert = (id: string, staff: string) => request<Alert>('POST', alertPath(id, 'done'), { staff });
export const cancelAlert = (id: string, by: string, reason: string) => request<Alert>('POST', alertPath(id, 'cancel'), { by, reason });
export const assignAlert = (id: string, staff: string) => request<Alert>('POST', alertPath(id, 'assign'), { staff });
export const createAlert = (kind: AlertKind, table: string | null, camera: string) =>
  request<Alert>('POST', '/api/alerts', { kind, table, camera });

// ---------- clip video ----------
/** Clip của một việc (chỉ có khi alert.clip === true) */
export const alertClipUrl = (id: string) => apiUrl(alertPath(id, 'clip.mp4'));
/** Xin clip của một camera trong khoảng [t_from, t_to] (mili giây epoch, tối đa 60 giây) */
export const requestClip = (camera: string, t_from: number, t_to: number) =>
  request<ClipRequest>('POST', '/api/clips', { camera, t_from, t_to });
export const getClip = (id: string) => request<ClipRequest>('GET', `/api/clips/${encodeURIComponent(id)}`);

// ---------- cài đặt ----------
export const putZones = (zones: CameraZones) => request<CameraZones>('PUT', '/api/zones', zones);
export const putStaff = (staff: StaffInput[]) => request<Staff[]>('PUT', '/api/staff', { staff });

/** Bàn do camera tự tìm, theo cỡ khung hình của camera */
export interface TableSuggestion {
  frame_w: number;
  frame_h: number;
  tables: { polygon: Point[]; score: number }[];
}
/** Nhờ camera tìm bàn. Có `box` [x1, y1, x2, y2] thì chỉ tìm bàn trong vùng vừa khoanh. */
export const suggestZones = (body: { camera: string; frame_w: number; frame_h: number; box?: number[] }) =>
  request<TableSuggestion>('POST', '/api/zones/suggest', body);

// ---------- ảnh nhận dạng nhân viên ----------
const staffPath = (sid: string) => `/api/staff/${encodeURIComponent(sid)}/photos`;
export const staffPhotoUrl = (sid: string, pid: string) => apiUrl(`${staffPath(sid)}/${encodeURIComponent(pid)}.jpg`);
export const shootStaffPhoto = (sid: string, camera: string) => request<Staff[]>('POST', `${staffPath(sid)}/camera`, { camera });
export const deleteStaffPhoto = (sid: string, pid: string) => request<Staff[]>('DELETE', `${staffPath(sid)}/${encodeURIComponent(pid)}`);
export async function uploadStaffPhoto(sid: string, kind: StaffPhoto['kind'], jpeg: Blob): Promise<Staff[]> {
  let res: Response;
  try {
    res = await fetch(apiUrl(`${staffPath(sid)}?kind=${kind}`), { method: 'POST', headers: { 'Content-Type': 'image/jpeg' }, body: jpeg });
  } catch {
    throw new ApiError('Không kết nối được máy chủ. Kiểm tra mạng và máy chủ Easy FnB.', 0);
  }
  if (!res.ok) throw new ApiError(await errorText(res), res.status);
  return (await res.json()) as Staff[];
}

/** Đổi cài đặt. Tắt che mặt (blur_faces) cần PIN chủ quán: truyền pin để gửi kèm header X-Owner-Pin. */
export const putSettings = (patch: SettingsPatch, pin?: string | null) =>
  request<Settings>('PUT', '/api/settings', patch, pin ? pinHeader(pin) : undefined);
export const resetShift = () => request<Record<string, never>>('POST', '/api/reset');

// ---------- Gemini ----------
/** ghi_chu: việc chủ quán vừa bấm Lưu trong khối cài đặt, gửi kèm để trợ lý biết dữ liệu đã đổi */
export const askAssistant = (question: string, session?: string, ghi_chu?: string) =>
  request<AssistantAnswer>('POST', '/api/assistant', { question, ...(session ? { session } : {}), ...(ghi_chu ? { ghi_chu } : {}) });
export const writeSummary = () => request<{ text: string }>('POST', '/api/report/summary');

// ---------- PIN chủ quán, clip bản gốc (không che mặt) ----------
const PIN_KEY = 'easyfnb.owner_pin';
const pinHeader = (pin: string) => ({ 'X-Owner-Pin': pin });

/** PIN đã nhập trong phiên này (chỉ sessionStorage: đóng trình duyệt là quên) */
export function savedPin(): string | null {
  try {
    return sessionStorage.getItem(PIN_KEY);
  } catch {
    return null;
  }
}
export function rememberPin(pin: string | null) {
  try {
    if (pin) sessionStorage.setItem(PIN_KEY, pin);
    else sessionStorage.removeItem(PIN_KEY);
  } catch {
    // trình duyệt chặn lưu: lần sau hỏi lại
  }
}
/** Máy chủ từ chối PIN (sai hoặc đã đổi) */
export const isPinError = (err: unknown) => err instanceof ApiError && (err.status === 401 || err.status === 403);

/** Đặt PIN lần đầu, hoặc đổi PIN (phải đúng PIN cũ) */
export const setOwnerPin = (pin: string, old_pin?: string) =>
  request<{ ok: boolean }>('PUT', '/api/owner/pin', old_pin ? { pin, old_pin } : { pin });
export const checkOwnerPin = (pin: string) => request<{ ok: boolean }>('POST', '/api/owner/pin/check', { pin });

/** Xin máy camera cắt clip bản gốc của một cảnh báo; theo dõi bằng getClip(id) */
export const requestOriginalClip = (alertId: string, pin: string) =>
  request<ClipRequest>('POST', alertPath(alertId, 'clip-goc'), {}, pinHeader(pin));
/** Giữ clip gốc làm bằng chứng, không tự xoá sau 24 giờ */
export const keepClip = (clipId: string, pin: string) =>
  request<ClipRequest>('POST', `/api/clips/${encodeURIComponent(clipId)}/keep`, {}, pinHeader(pin));

/** Tải clip gốc kèm header PIN (thẻ <video> không gửi header được), trả về blob để phát bằng object URL */
export async function fetchOriginalClip(url: string, pin: string): Promise<Blob> {
  let res: Response;
  try {
    res = await fetch(apiUrl(url), { headers: pinHeader(pin) });
  } catch {
    throw new ApiError('Không kết nối được máy chủ. Kiểm tra mạng và máy chủ Easy FnB.', 0);
  }
  if (!res.ok) throw new ApiError(await errorText(res), res.status);
  return res.blob();
}
