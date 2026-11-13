import type { Alert, AlertKind, AlertStatus, Camera, Role, Staff, TableStateKind, Verify } from './types';

/** Lệnh chạy máy camera (đường ống thị giác) gửi sự kiện về máy chủ. Sửa cờ ở đây là đủ. */
export const CAMERA_AGENT_CMD =
  'python easyfnb_test.py <video hoặc thư mục> --may-chu http://<địa chỉ máy chủ>:8080 --camera cam1 --thoi-gian-thuc';

export const KIND_LABEL: Record<AlertKind, string> = {
  call: 'Gọi phục vụ',
  needs_clearing: 'Cần dọn bàn',
  new_guest: 'Khách mới',
};

/** Câu đọc trên điện thoại, sau "Bàn B2 ..." */
const KIND_SPEECH: Record<AlertKind, string> = {
  call: 'gọi phục vụ',
  needs_clearing: 'cần dọn',
  new_guest: 'có khách mới',
};

export const KIND_CHIP: Record<AlertKind, string> = {
  call: 'chip chip--p1',
  needs_clearing: 'chip chip--p2',
  new_guest: 'chip chip--cool',
};

/** Gọi phục vụ trước, rồi dọn bàn, rồi chào khách mới */
export const KIND_RANK: Record<AlertKind, number> = { call: 0, needs_clearing: 1, new_guest: 2 };

/** Vai trò nhận từng loại việc (khớp API.md) */
export const KIND_ROLE: Record<AlertKind, Role> = { call: 'serve', needs_clearing: 'clean', new_guest: 'serve' };

export const ROLE_LABEL: Record<Role, string> = { serve: 'Phục vụ', clean: 'Dọn bàn', cashier: 'Thu ngân' };

export const TABLE_STATE_LABEL: Record<TableStateKind, string> = {
  empty: 'Trống',
  occupied: 'Có khách',
  needs_clearing: 'Cần dọn',
  unknown: 'Chưa rõ',
};

export const TABLE_STATE_CHIP: Record<TableStateKind, string> = {
  empty: 'chip',
  occupied: 'chip chip--cool',
  needs_clearing: 'chip chip--p2',
  unknown: 'chip',
};

/**
 * Camera còn gửi hình không. Máy chủ chỉ gửi sự kiện camera khi có khung mới,
 * nên khi máy camera tắt, cờ online có thể không kịp về: xét thêm tuổi khung cuối.
 */
export function cameraLive(c: Camera, now: number) {
  return c.online && c.last_frame_at !== null && now - c.last_frame_at < 8000;
}

export const ACTIVE: AlertStatus[] = ['verifying', 'open', 'acked'];
export const isActive = (a: Alert) => a.status === 'verifying' || a.status === 'open' || a.status === 'acked';
export const isClosed = (a: Alert) => a.status === 'done' || a.status === 'cancelled';

/** Sắp việc: gọi phục vụ trước, cùng loại thì việc chờ lâu nhất trước */
export function byUrgency(a: Alert, b: Alert) {
  return KIND_RANK[a.kind] - KIND_RANK[b.kind] || a.created_at - b.created_at;
}

/** So tên bàn tự nhiên: B2 trước B10 */
export const byName = (a: string, b: string) => a.localeCompare(b, 'vi', { numeric: true, sensitivity: 'base' });

export const tableText = (table: string | null) => (table ? `Bàn ${table}` : 'Chưa rõ bàn');

/** Khi không biết bàn nào */
const KIND_SPEECH_NO_TABLE: Record<AlertKind, string> = {
  call: 'Có khách gọi phục vụ',
  needs_clearing: 'Có bàn cần dọn',
  new_guest: 'Có khách mới vào',
};

export function speechLine(a: Alert) {
  // dấu phẩy là chỗ giọng đọc ngắt một nhịp (xem voice.ts)
  const head = a.table ? `Bàn ${a.table}, ${KIND_SPEECH[a.kind]}` : KIND_SPEECH_NO_TABLE[a.kind];
  return a.escalated ? `Gấp. ${head}` : head;
}

export function staffName(staff: Staff[], id: string | null | undefined) {
  if (!id) return null;
  if (id === 'manager') return 'Quản lý';
  if (id === 'camera') return 'camera';
  return staff.find((s) => s.id === id)?.name ?? id;
}

/** Trạng thái việc bằng lời, có tên người */
export function statusText(a: Alert, staff: Staff[], ten = 'Gemini') {
  const who = staffName(staff, a.status === 'acked' ? (a.acked_by ?? a.assigned_to) : a.assigned_to);
  switch (a.status) {
    case 'verifying':
      return `Chờ ${ten} kiểm tra rồi mới báo`;
    case 'open':
      return who ? `Đã báo ${who}, chờ nhận` : 'Chưa giao cho ai';
    case 'acked':
      if (a.arrived_s != null) return `Nhân viên ${ARRIVED[speedOf(a.arrived_s) ?? 'fast']}`;
      return who ? `${who} đang tới` : 'Đang có người tới';
    case 'done':
      if (a.arrived_s != null) return `Xong, nhân viên ${ARRIVED[speedOf(a.arrived_s) ?? 'fast']}`;
      return `Xong${a.done_by ? `, ${staffName(staff, a.done_by)}` : ''}`;
    case 'cancelled':
      return `Đã huỷ${a.cancel_reason ? `: ${a.cancel_reason}` : ''}`;
  }
}

export function verifyBadge(v: Verify | null | undefined, ten = 'Gemini'): { label: string; cls: string } {
  switch (v?.state) {
    case 'pending':
      return { label: `${ten} đang kiểm tra`, cls: 'chip chip--cool' };
    case 'confirmed':
      return { label: `${ten} xác nhận`, cls: 'chip chip--ok' };
    case 'rejected':
      return { label: `${ten}: báo nhầm`, cls: 'chip chip--bad' };
    case 'unverified':
      return { label: 'Chưa xác minh', cls: 'chip chip--p2' };
    case 'error':
      return { label: `${ten} lỗi, chưa kiểm tra`, cls: 'chip' };
    default:
      return { label: 'Chưa kiểm tra', cls: 'chip' };
  }
}

// ---------- tốc độ bằng chữ ----------
// Màn hình không hiện số giây: người xem chỉ cần biết nhanh hay chậm. Mốc khớp với máy chủ (hub.py).
export type SpeedKind = 'fast' | 'ok' | 'slow' | 'missed';
export type SpeedCounts = Record<SpeedKind, number>;
export const FAST_S = 30;
export const SLOW_S = 60;

export const SPEED_LABEL: Record<SpeedKind, string> = { fast: 'Nhanh', ok: 'Hơi chậm', slow: 'Chậm', missed: 'Không ai tới' };
export const SPEED_VARIANT = { fast: 'success', ok: 'warning', slow: 'error', missed: 'error' } as const;
const ARRIVED = { fast: 'tới nhanh', ok: 'tới hơi chậm', slow: 'tới chậm' } as const;

/** Một khoảng chờ (giây) là nhanh, hơi chậm hay chậm */
export function speedOf(s: number | null | undefined): Exclude<SpeedKind, 'missed'> | null {
  if (s === null || s === undefined || !Number.isFinite(s)) return null;
  return s <= FAST_S ? 'fast' : s <= SLOW_S ? 'ok' : 'slow';
}

/** Nhận xét chung cho một nhóm việc: phần lớn nhanh thì là nhanh, nhiều việc chậm hay bị bỏ lỡ thì là chậm */
export function verdictOf(c: SpeedCounts): Exclude<SpeedKind, 'missed'> | null {
  const total = c.fast + c.ok + c.slow + c.missed;
  if (!total) return null;
  const fast = c.fast / total;
  const bad = (c.slow + c.missed) / total;
  if (fast >= 0.7 && bad <= 0.1) return 'fast';
  if (bad >= 0.3 || fast < 0.4) return 'slow';
  return 'ok';
}

/** Một việc đang mở đã chờ bao lâu, nói bằng chữ */
export function waitWord(ms: number, acked: boolean): { label: string; level?: 'ok' | 'warn' | 'late' } {
  if (acked) return { label: 'Đã nhận', level: 'ok' };
  if (ms < 20_000) return { label: 'Vừa báo' };
  if (ms < 45_000) return { label: 'Đang chờ' };
  if (ms < 90_000) return { label: 'Chờ hơi lâu', level: 'warn' };
  return { label: 'Chờ quá lâu', level: 'late' };
}

// ---------- thời gian ----------
/** Tuổi một việc: "12 giây", "3 phút", "1 giờ 5 phút" */
export function ageText(ms: number) {
  const s = Math.max(0, Math.floor(ms / 1000));
  if (s < 60) return `${s} giây`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m} phút`;
  const h = Math.floor(m / 60);
  return m % 60 ? `${h} giờ ${m % 60} phút` : `${h} giờ`;
}

/** Thời gian làm trong ca: tính theo phút, không hiện số giây */
export const shiftText = (ms: number) => (ms < 60_000 ? 'chưa tới 1 phút' : ageText(ms));

/** Số giây của báo cáo: "23 giây", "1 phút 5 giây", hoặc "chưa có" */
export function secText(s: number | null | undefined) {
  if (s === null || s === undefined || !Number.isFinite(s)) return 'chưa có';
  const v = Math.round(s);
  if (v < 60) return `${v} giây`;
  const m = Math.floor(v / 60);
  return v % 60 ? `${m} phút ${v % 60} giây` : `${m} phút`;
}

const TIME = new Intl.DateTimeFormat('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });

/** Giờ trong ngày kiểu Việt Nam: 19:24:05 */
export const clockTime = (t: number) => TIME.format(t);

/** Mã nhân viên từ tên: "Thảo Vy" -> "thaovy" */
export function slugify(name: string) {
  return (
    name
      .normalize('NFD')
      .replace(/[̀-ͯ]/g, '')
      .replace(/đ/g, 'd')
      .replace(/Đ/g, 'D')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '')
      .slice(0, 24) || 'nv'
  );
}
