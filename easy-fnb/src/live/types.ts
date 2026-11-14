/**
 * Kiểu dữ liệu của máy chủ Easy FnB, chép đúng theo easy-fnb/server/API.md.
 * Mọi mốc thời gian là mili giây epoch, trừ tên kết thúc bằng _s (giây).
 */

export type Kind = 'call' | 'needs_clearing' | 'new_guest' | 'guest_left' | 'cleared';
export type AlertKind = 'call' | 'needs_clearing' | 'new_guest';
export const ALERT_KINDS: AlertKind[] = ['call', 'needs_clearing', 'new_guest'];
/** Cảnh báo an ninh: lấy đồ của khách, có người ngoài giờ, khách vào quầy/kho. Tách khỏi việc phục vụ. */
export type SecurityKind = 'item_taken' | 'after_hours' | 'restricted';
export const SECURITY_KINDS: SecurityKind[] = ['item_taken', 'after_hours', 'restricted'];

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
  /** chỉ với item_taken: ảnh "người ngồi bàn" lúc ngồi (đã che mặt) */
  person?: string | null;
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
  /** true khi đã có clip video của việc này: xem bằng alertClipUrl(id) */
  clip?: boolean;
  /** 'security' với cảnh báo an ninh; việc phục vụ không có */
  group?: 'security' | null;
}

/** Cảnh báo an ninh: cùng dạng với việc, thêm vùng và danh sách người nhận. assigned_to luôn null. */
export interface SecurityAlert extends Omit<Alert, 'kind' | 'group'> {
  kind: SecurityKind;
  group?: 'security' | null;
  /** id vùng (quầy, kho, cửa...) và tên vùng, nếu sự kiện nằm trong một vùng */
  area?: string | null;
  area_name?: string | null;
  /** id những nhân viên nhận cảnh báo này */
  notify?: string[];
}

/** Một mục trong state.alerts hay luồng 'alert': việc phục vụ hoặc cảnh báo an ninh */
export type AnyAlert = Alert | SecurityAlert;

export const isSecurity = (a: AnyAlert): a is SecurityAlert =>
  a.group === 'security' || (SECURITY_KINDS as string[]).includes(a.kind);

/** Clip xin theo khoảng thời gian (mốc thời gian là mili giây epoch). Hỏi lại bằng getClip tới khi hết 'pending'. */
export interface ClipRequest {
  id: string;
  status: 'pending' | 'ready' | 'failed';
  camera: string;
  t_from: number;
  t_to: number;
  /** có khi 'ready', ví dụ "/api/clips/c3.mp4": đưa qua apiUrl() rồi gắn vào <video> */
  url: string | null;
  /** lời báo tiếng Việt khi 'failed' */
  error: string | null;
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
  /** giai đoạn bữa ăn của lượt khách hiện tại; null khi bàn chưa có khách */
  stage?: TableStage | null;
  /** lúc vào giai đoạn này (ms) */
  stage_since?: number | null;
  /** lời nhắc mềm đang hiện cho bàn: chưa ai ra tiếp, chờ món lâu, có thể đang chờ tính tiền */
  nudge?: 'greet' | 'food' | 'bill' | null;
  nudge_at?: number | null;
  /** khách tạm rời nhưng còn để đồ ở bàn (đi vệ sinh, nghe máy): chưa cần dọn */
  away?: boolean;
  /** lúc nhận ảnh bàn mới nhất (GET /api/tables/{id}/snap.jpg) */
  snap_at?: number | null;
}

export type TableStage = 'seated' | 'greeted' | 'served' | 'finished' | 'left';

export type Point = [number, number];

export interface Zone {
  id: string;
  polygon: Point[];
}

/** Loại vùng không phải bàn: quầy thu ngân, kho/bếp (cấm khách), chỗ giữ xe, cửa */
export type AreaType = 'quay' | 'kho' | 'giu_xe' | 'cua';
export const AREA_TYPES: AreaType[] = ['quay', 'kho', 'giu_xe', 'cua'];

export interface Area {
  id: string;
  type: AreaType;
  name?: string;
  polygon: Point[];
}

export interface CameraZones {
  camera: string;
  frame_w: number;
  frame_h: number;
  tables: Zone[];
  /** vùng không phải bàn; máy chủ cũ không gửi */
  areas?: Area[];
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
  /** bản demo tự chạy: clip đã che mặt đang phát làm hình camera */
  demo?: { file: string; url: string; started_at: number; duration_ms: number };
}

/** owner: chủ quán, chỉ nhận cảnh báo an ninh, không nhận việc phục vụ */
export type Role = 'serve' | 'clean' | 'cashier' | 'owner';
export const ROLES: Role[] = ['serve', 'clean', 'cashier', 'owner'];

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

export type LogKind = Kind | SecurityKind | 'ack' | 'arrived' | 'done' | 'cancel' | 'escalate' | 'verify' | 'system' | 'looking' | 'nudge';

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
  /** cách nhau bấy nhiêu giây thì AI xem ảnh bàn một lần để biết bữa ăn tới đâu; 0 là tắt */
  table_check_s?: number;
  /** khách ngồi quá bấy nhiêu giây mà chưa ai ra tiếp / chưa có món / ăn xong chưa ai ghé thì nhắc một lần; 0 là tắt */
  wait_greet_s?: number;
  wait_food_s?: number;
  wait_bill_s?: number;
  // ---------- an ninh ----------
  sec_after_hours?: boolean;
  sec_restricted?: boolean;
  sec_item_taken?: boolean;
  /** giờ mở và đóng cửa, "HH:MM" */
  open_time?: string;
  close_time?: string;
  /** nút "Trông quán": bật tay là coi như quán đóng */
  guard_mode?: boolean;
  /** khung giờ giao hàng không báo khách vào quầy/kho, "HH:MM" hoặc "" */
  delivery_from?: string;
  delivery_to?: string;
  /** che mặt trong ảnh và clip; tắt cần PIN chủ quán */
  blur_faces?: boolean;
  /** giây giữ bàn khi khách tạm rời còn để đồ */
  hold_s?: number;
  /** chỉ đọc: đã đặt PIN chủ quán chưa; quán đang đóng (ngoài giờ hoặc đang trông quán) */
  owner_pin_set?: boolean;
  closed?: boolean;
}

export type SettingsPatch = Partial<Pick<Settings, 'verify_kinds' | 'hold_until_verified' | 'escalate_s' | 'dedup_s' | 'auto_close_s'
  | 'table_check_s' | 'wait_greet_s' | 'wait_food_s' | 'wait_bill_s'
  | 'sec_after_hours' | 'sec_restricted' | 'sec_item_taken' | 'open_time' | 'close_time' | 'guard_mode'
  | 'delivery_from' | 'delivery_to' | 'blur_faces' | 'hold_s'>>;

export interface State {
  server_time: number;
  settings: Settings;
  cameras: Camera[];
  zones: CameraZones[];
  tables: TableState[];
  /** việc phục vụ lẫn cảnh báo an ninh; kho dữ liệu tách ra bằng isSecurity */
  alerts: AnyAlert[];
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
  kind: AlertKind | SecurityKind;
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
  /** clip video của việc này, có khi máy camera đã gửi clip; máy chủ cũ không gửi */
  clip_url?: string | null;
}
/**
 * Một đoạn video camera trong câu trả lời. Đúng một trong ba cách lấy:
 * `src` đã sẵn; `clip_id` đang chờ máy camera (hỏi getClip tới khi xong);
 * cả hai trống thì xin bằng requestClip(camera, t_from, t_to) khi người xem bấm vào.
 * `error` là lời báo tiếng Việt khi chắc chắn không có video (máy camera tắt, chưa tới giờ...).
 */
export interface VideoItem {
  label: string;
  /** thời điểm chính của đoạn này (mili giây epoch) */
  t: number;
  table: string | null;
  alert_id: string | null;
  src: string | null;
  clip_id: string | null;
  /** ảnh hiện trong lúc chờ video, và thay cho video khi không lấy được */
  poster: string | null;
  note: string | null;
  camera: string;
  t_from: number;
  t_to: number;
  error: string | null;
}
export interface VideoBlock {
  type: 'video';
  title: string;
  items: VideoItem[];
}
/** Chuyện của một bàn hoặc một quãng giờ, từng bước theo thứ tự thời gian */
export interface TimelineBlock {
  type: 'timeline';
  title: string;
  items: { t: number; text: string; tone: Tone; table: string | null; alert_id: string | null; video: VideoItem | null }[];
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
/** Gợi ý cho ca sau: vấn đề, việc nên làm, và vài sự kiện có hình làm bằng chứng */
export interface InsightsBlock {
  type: 'insights';
  title: string;
  items: { id: string; tone: Tone; title: string; text: string; action: string; events: EventItem[] }[];
}
// ---------- khối cài đặt trong trợ lý (server/cai_dat.py): bấm Lưu thì gọi API cài đặt có sẵn ----------
/** Mã QR nối điện thoại làm camera, hoặc mở app nhân viên */
export interface QrBlock {
  type: 'qr';
  kind: 'camera' | 'staff';
  title: string;
  camera: string | null;
  staff: { id: string; name: string }[];
}

/** Bàn camera vừa tìm thấy, chờ chủ quán bấm Lưu. `merged`: vùng cũ cộng bàn mới (khi camera đã có vùng) */
export interface BanBlock {
  type: 'ban';
  title: string;
  camera: string;
  frame_w: number;
  frame_h: number;
  tables: { id: string; polygon: Point[] }[];
  merged: { id: string; polygon: Point[] }[] | null;
  existing: string[];
}

export interface StaffChangeRow {
  change: 'them' | 'bo' | 'doi';
  id: string;
  name: string;
  role: Role;
  old_name: string | null;
  old_role: Role | null;
  photos: number;
}

export interface RuleRow {
  key: string;
  label: string;
  /** gio: "HH:MM" */
  unit: 'bat_tat' | 'giay' | 'phut' | 'gio';
  /** khoá trong Settings; null với ba công tắc AI (đổi qua verify_kinds, hold_until_verified) */
  setting: string | null;
  before: boolean | number | string;
  after: boolean | number | string;
  min: number | null;
  max: number | null;
  needs_ai: boolean;
  /** giờ để trống được (khung giờ giao hàng) */
  optional: boolean;
  group: 'phuc_vu' | 'an_ninh';
}

/** Thay đổi chờ xác nhận. `base`: dữ liệu lúc dựng khối, để biết có ai vừa sửa ở nơi khác không */
export type ConfirmBlock =
  | { type: 'xac_nhan'; kind: 'staff'; title: string; rows: StaffChangeRow[]; base: { id: string; name: string; role: Role }[] }
  | { type: 'xac_nhan'; kind: 'settings'; title: string; rows: RuleRow[]; base: Record<string, boolean | number | string>; ai: boolean };

/** Chụp ảnh nhận dạng một nhân viên bằng camera quán */
export interface ChupBlock {
  type: 'chup';
  title: string;
  camera: string;
  staff_id: string;
  name: string;
  consent: boolean;
  photos: number;
}

export type Block = StatsBlock | ChartBlock | EventsBlock | TableBlock | StaffBlock | InsightsBlock | VideoBlock | TimelineBlock | QrBlock | BanBlock | ConfirmBlock | ChupBlock;

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
