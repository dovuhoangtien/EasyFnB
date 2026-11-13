/**
 * Kiểu dữ liệu của máy chủ Easy FnB, chép đúng theo easy-fnb/server/API.md.
 * Mọi mốc thời gian là mili giây epoch, trừ tên kết thúc bằng _s (giây).
 */

export type Kind = 'call' | 'needs_clearing' | 'new_guest' | 'guest_left' | 'cleared';
export type AlertKind = 'call' | 'needs_clearing' | 'new_guest';
export const ALERT_KINDS: AlertKind[] = ['call', 'needs_clearing', 'new_guest'];

export type AlertStatus = 'verifying' | 'open' | 'acked' | 'done' | 'cancelled';
export type VerifyState = 'pending' | 'confirmed' | 'rejected' | 'skipped' | 'error' | 'unverified';

export interface Verify {
  state: VerifyState;
  confidence: number | null;
  reason: string | null;
  ms: number | null;
  model: string | null;
  path?: string | null;
  verdict?: string | null;
  image_quality?: string | null;
  source?: 'evidence' | 'crop' | null;
}

/** Đồ còn trên bàn do camera nhận (tiếng Việt), chỉ có với việc dọn bàn */
export interface LeftItem {
  name: string;
  count: number;
}

/** Ảnh bằng chứng camera gửi sau sự kiện: dải 4 khung, toàn cảnh khoanh đỏ, ảnh bàn sạch để so */
export interface Evidence {
  strip: string | null;
  overview: string | null;
  ref: string | null;
}

export type Box = [number, number, number, number];

export interface Alert {
  id: string;
  kind: AlertKind;
  table: string | null;
  camera: string;
  created_at: number;
  video_t: number | null;
  box: Box | null;
  score: number | null;
  detail: string;
  crop_url: string | null;
  items: LeftItem[] | null;
  evidence: Evidence | null;
  status: AlertStatus;
  assigned_to: string | null;
  acked_at: number | null;
  acked_by: string | null;
  done_at: number | null;
  done_by: string | null;
  cancelled_at: number | null;
  cancel_reason: string | null;
  escalated: boolean;
  repeats: number;
  verify: Verify;
  /** lúc camera thấy nhân viên đứng ở bàn, và số giây kể từ lúc báo (thời gian phản hồi thật) */
  arrived_at?: number | null;
  arrived_s?: number | null;
  close_reason?: string | null;
}

export type TableStateKind = 'empty' | 'occupied' | 'needs_clearing' | 'unknown';

export interface TableState {
  id: string;
  camera: string;
  state: TableStateKind;
  people: number;
  since: number;
  dirty: number | null;
  /** lúc camera thấy khách bàn này nhìn quanh tìm nhân viên (tín hiệu mềm) */
  looking_at?: number | null;
}

export type Point = [number, number];

export interface Zone {
  id: string;
  polygon: Point[];
}

export interface CameraZones {
  camera: string;
  frame_w: number;
  frame_h: number;
  tables: Zone[];
}

export interface Camera {
  id: string;
  name: string;
  online: boolean;
  last_frame_at: number | null;
  frame_version: number;
  has_snapshot: boolean;
  frame_w: number | null;
  frame_h: number | null;
  fps: number | null;
  source: string | null;
}

export type Role = 'serve' | 'clean' | 'cashier';
export const ROLES: Role[] = ['serve', 'clean', 'cashier'];

/** Ảnh để camera nhận ra nhân viên: mặt, hoặc cả người (thấy đồng phục) */
export interface StaffPhoto {
  id: string;
  kind: 'face' | 'body';
  source: 'upload' | 'camera';
}

export interface Staff {
  id: string;
  name: string;
  role: Role;
  /** Người này đã đồng ý cho dùng ảnh để nhận dạng */
  consent?: boolean;
  photos?: StaffPhoto[];
  online: boolean;
  open_tasks: number;
  /** Điểm danh: lúc vào ca đầu tiên, lúc mở app lượt hiện tại (null nếu đã ra), và giây đã làm ở các lượt đã kết thúc */
  first_in?: number | null;
  on_since?: number | null;
  worked_s?: number;
}

export type StaffInput = Pick<Staff, 'id' | 'name' | 'role' | 'consent'>;

export type LogKind = Kind | 'ack' | 'arrived' | 'done' | 'cancel' | 'escalate' | 'verify' | 'system' | 'looking';

export interface LogEntry {
  id: number;
  t: number;
  kind: LogKind;
  table: string | null;
  camera: string | null;
  alert_id: string | null;
  text: string;
}

export interface Settings {
  gemini: boolean;
  /** Tên nhà cung cấp LLM để hiện cho người dùng: "Gemini" hoặc "kie.ai". */
  provider?: string;
  model: string;
  verify_kinds: string[];
  hold_until_verified: string[];
  escalate_s: number;
  dedup_s: number;
  /** sau bấy nhiêu giây nhân viên đã nhận mà chưa bấm Xong thì việc tự đóng; 0 là tắt */
  auto_close_s?: number;
}

export type SettingsPatch = Partial<Pick<Settings, 'verify_kinds' | 'hold_until_verified' | 'escalate_s' | 'dedup_s' | 'auto_close_s'>>;

export interface State {
  server_time: number;
  settings: Settings;
  cameras: Camera[];
  zones: CameraZones[];
  tables: TableState[];
  alerts: Alert[];
  staff: Staff[];
  log: LogEntry[];
}

export interface AssistantRef {
  alert_id: string | null;
  t: number;
  table: string | null;
}

export type Tone = 'good' | 'warn' | 'bad' | null;

export interface StatsBlock {
  type: 'stats';
  title: string | null;
  items: { label: string; value: string; note: string | null; tone: Tone }[];
}
export interface ChartBlock {
  type: 'chart';
  title: string;
  /** bar: thanh ngang (người, bàn); column: cột theo giờ; line: đường theo giờ */
  kind: 'bar' | 'column' | 'line';
  unit: string;
  points: { label: string; value: number; note: string | null }[];
}
export interface EventItem {
  alert_id: string;
  kind: AlertKind;
  table: string | null;
  t: number;
  status: string;
  wait_s: number | null;
  staff: string | null;
  text: string;
  crop_url: string | null;
  /** dải 2x2 gồm 4 khung quanh sự kiện, dùng làm "clip" ngắn */
  strip_url: string | null;
  video_t: number | null;
}
export interface EventsBlock {
  type: 'events';
  title: string;
  items: EventItem[];
}
export interface TableBlock {
  type: 'table';
  title: string;
  columns: string[];
  rows: string[][];
}
export interface StaffBlock {
  type: 'staff';
  title: string;
  items: {
    id: string;
    name: string;
    role: string;
    online: boolean;
    acked: number;
    done: number;
    mean_response_s: number | null;
    worked_s: number;
    first_in: number | null;
  }[];
}
export type Block = StatsBlock | ChartBlock | EventsBlock | TableBlock | StaffBlock;

export interface AssistantAnswer {
  answer: string;
  refs: AssistantRef[];
  /** Các khối trả lời nhiều dạng; máy chủ cũ không gửi */
  blocks?: Block[];
  suggestions?: string[];
  /** 'adk': Gemini qua Google ADK; 'rules': trả lời theo luật, không dùng AI */
  engine?: 'adk' | 'rules';
  model?: string | null;
  ms?: number;
}

export interface TimelinePoint extends Record<AlertKind, number> {
  t: number;
  fast: number;
  ok: number;
  slow: number;
  missed: number;
}

export interface Report {
  from: number;
  to: number;
  counts: Record<AlertKind, number>;
  cancelled: number;
  rejected_by_gemini: number;
  response_s: { mean: number | null; median: number | null; p90: number | null };
  done_s: { mean: number | null; median: number | null };
  escalated: number;
  /** số việc được nhận nhanh, hơi chậm, chậm, và số việc không ai tới; máy chủ cũ không gửi */
  speed?: { fast: number; ok: number; slow: number; missed: number; fast_s: number; slow_s: number };
  per_staff: {
    id: string;
    name: string;
    acked: number;
    done: number;
    mean_response_s: number | null;
    fast?: number;
    ok?: number;
    slow?: number;
    /** số việc đã nhận, chia theo loại việc */
    kinds?: Partial<Record<AlertKind, number>>;
  }[];
  per_table: { table: string; calls: number; clearings: number; guests: number; fast?: number; ok?: number; slow?: number; missed?: number }[];
  /** việc của ca chia theo từng quãng giờ: mỗi cột dài step_s giây, t là lúc cột bắt đầu */
  timeline?: { step_s: number; points: TimelinePoint[] } | null;
  /** số việc camera thấy nhân viên tới bàn; số việc tự đóng mà không thấy ai tới */
  arrived?: number;
  no_arrival?: number;
}
