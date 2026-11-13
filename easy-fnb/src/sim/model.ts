import { hms } from './util';

export type Phase =
  | 'empty'
  | 'seated'
  | 'ordering'
  | 'waiting_food'
  | 'eating'
  | 'finishing'
  | 'wants_bill'
  | 'leaving'
  | 'needs_clearing';

export const PHASE_LABEL: Record<Phase, string> = {
  empty: 'Trống',
  seated: 'Mới ngồi',
  ordering: 'Đang gọi món',
  waiting_food: 'Chờ món',
  eating: 'Đang ăn',
  finishing: 'Sắp xong',
  wants_bill: 'Muốn tính tiền',
  leaving: 'Đang về',
  needs_clearing: 'Cần dọn',
};

export type Zone = 'A' | 'B' | 'C';

export interface TableDef {
  id: number;
  x: number;
  y: number;
  w: number;
  h: number;
  seats: number;
  zone: Zone;
  round?: boolean;
}

/** Mặt bằng quán, đơn vị: 50 đơn vị = 1 mét */
export const FLOOR = { w: 1000, h: 640 };
export const UNITS_PER_METER = 50;

export const TABLES: TableDef[] = [
  { id: 1, x: 60, y: 92, w: 120, h: 74, seats: 4, zone: 'A' },
  { id: 2, x: 212, y: 92, w: 120, h: 74, seats: 4, zone: 'A' },
  { id: 3, x: 60, y: 216, w: 120, h: 74, seats: 4, zone: 'A' },
  { id: 4, x: 212, y: 216, w: 120, h: 74, seats: 4, zone: 'A' },
  { id: 5, x: 60, y: 340, w: 120, h: 74, seats: 2, zone: 'A' },
  { id: 6, x: 212, y: 340, w: 120, h: 74, seats: 2, zone: 'A' },
  { id: 7, x: 404, y: 112, w: 108, h: 108, seats: 6, zone: 'B', round: true },
  { id: 8, x: 548, y: 112, w: 108, h: 108, seats: 4, zone: 'B', round: true },
  { id: 9, x: 404, y: 272, w: 108, h: 108, seats: 4, zone: 'B', round: true },
  { id: 10, x: 548, y: 272, w: 108, h: 108, seats: 4, zone: 'B', round: true },
  { id: 11, x: 722, y: 92, w: 240, h: 82, seats: 8, zone: 'C' },
  { id: 12, x: 722, y: 206, w: 240, h: 82, seats: 6, zone: 'C' },
  { id: 13, x: 722, y: 320, w: 112, h: 82, seats: 4, zone: 'C' },
  { id: 14, x: 850, y: 320, w: 112, h: 82, seats: 4, zone: 'C' },
];

export const tableDef = (id: number) => TABLES[id - 1];

export const ZONES: { zone: Zone; label: string; x: number; y: number }[] = [
  { zone: 'A', label: 'Khu A, cạnh cửa sổ', x: 60, y: 64 },
  { zone: 'B', label: 'Khu B', x: 404, y: 92 },
  { zone: 'C', label: 'Khu C, lẩu', x: 722, y: 64 },
];

export interface Area {
  id: string;
  label: string;
  x: number;
  y: number;
  w: number;
  h: number;
}

export const AREAS: Area[] = [
  { id: 'pass', label: 'Quầy ra món', x: 404, y: 18, w: 252, h: 44 },
  { id: 'door', label: 'Cửa ra vào', x: 30, y: 556, w: 190, h: 66 },
  { id: 'staff', label: 'Phòng nhân viên', x: 240, y: 556, w: 150, h: 66 },
  { id: 'counter', label: 'Quầy thu ngân', x: 722, y: 556, w: 240, h: 66 },
];

export function center(id: number) {
  const d = tableDef(id);
  return { x: d.x + d.w / 2, y: d.y + d.h / 2 };
}

/** Vị trí ghế quanh bàn, dùng để vẽ khách */
export function seatPoints(d: TableDef, n: number) {
  const pts: { x: number; y: number }[] = [];
  const cx = d.x + d.w / 2;
  const cy = d.y + d.h / 2;
  if (d.round) {
    const r = d.w / 2 + 15;
    for (let i = 0; i < n; i++) {
      const a = -Math.PI / 2 + (i * 2 * Math.PI) / n;
      pts.push({ x: cx + Math.cos(a) * r, y: cy + Math.sin(a) * r });
    }
    return pts;
  }
  const top = Math.ceil(n / 2);
  const bottom = n - top;
  for (let i = 0; i < top; i++) pts.push({ x: d.x + (d.w * (i + 1)) / (top + 1), y: d.y - 15 });
  for (let i = 0; i < bottom; i++) pts.push({ x: d.x + (d.w * (i + 1)) / (bottom + 1), y: d.y + d.h + 15 });
  return pts;
}

/** Điểm nhân viên đứng để phục vụ: mép bàn gần phía nhân viên nhất */
export function approachPoint(d: TableDef, from: { x: number; y: number }) {
  const m = 20;
  const x0 = d.x - m;
  const x1 = d.x + d.w + m;
  const y0 = d.y - m;
  const y1 = d.y + d.h + m;
  let x = Math.min(Math.max(from.x, x0), x1);
  let y = Math.min(Math.max(from.y, y0), y1);
  if (x > x0 && x < x1 && y > y0 && y < y1) {
    const dl = x - x0;
    const dr = x1 - x;
    const dt = y - y0;
    const db = y1 - y;
    const min = Math.min(dl, dr, dt, db);
    if (min === dl) x = x0;
    else if (min === dr) x = x1;
    else if (min === dt) y = y0;
    else y = y1;
  }
  return { x, y };
}

export type Role = 'serve' | 'cashier' | 'clean';
export const ROLE_LABEL: Record<Role, string> = { serve: 'Phục vụ', cashier: 'Thu ngân', clean: 'Dọn bàn' };

export interface StaffDef {
  id: string;
  name: string;
  role: Role;
  zone?: Zone;
  home: { x: number; y: number };
  clockIn: number;
}

export const STAFF: StaffDef[] = [
  { id: 'lan', name: 'Lan', role: 'serve', zone: 'A', home: { x: 272, y: 470 }, clockIn: hms(16, 45, 12) },
  { id: 'minh', name: 'Minh', role: 'serve', zone: 'B', home: { x: 530, y: 462 }, clockIn: hms(16, 52, 40) },
  { id: 'hung', name: 'Hùng', role: 'serve', zone: 'C', home: { x: 690, y: 466 }, clockIn: hms(17, 4, 5) },
  { id: 'thao', name: 'Thảo', role: 'cashier', home: { x: 842, y: 530 }, clockIn: hms(16, 40, 30) },
  { id: 'tu', name: 'Tú', role: 'clean', home: { x: 470, y: 560 }, clockIn: hms(16, 58, 2) },
];

export const staffDef = (id: string) => STAFF.find((s) => s.id === id)!;

export type TaskKind = 'greet' | 'call' | 'bill' | 'clear' | 'refill' | 'plates' | 'food_late' | 'broken';

export const TASK_INFO: Record<TaskKind, { label: string; priority: 1 | 2 | 3; roles: Role[]; service: number }> = {
  call: { label: 'gọi phục vụ', priority: 1, roles: ['serve'], service: 50 },
  broken: { label: 'có đồ vỡ', priority: 1, roles: ['clean', 'serve'], service: 70 },
  greet: { label: 'khách mới ngồi', priority: 2, roles: ['serve'], service: 130 },
  bill: { label: 'muốn tính tiền', priority: 2, roles: ['cashier', 'serve'], service: 95 },
  clear: { label: 'cần dọn bàn', priority: 2, roles: ['clean', 'serve'], service: 100 },
  food_late: { label: 'món ra chậm', priority: 2, roles: [], service: 0 },
  refill: { label: 'cần thêm nước', priority: 3, roles: ['serve', 'clean'], service: 30 },
  plates: { label: 'hết món, mời gọi thêm', priority: 3, roles: ['serve'], service: 45 },
};

/**
 * Ngưỡng "thường lệ" (phân vị 75) cho mỗi giai đoạn, tính bằng giây.
 * Bản thật học từ dữ liệu của quán; bản demo dùng giá trị khởi tạo từ chuẩn phục vụ.
 */
export function prior(phase: Phase, party: number) {
  switch (phase) {
    case 'seated':
      return 60;
    case 'ordering':
      return 360;
    case 'waiting_food':
      return 540 + party * 40;
    case 'eating':
      return 2100 + party * 120;
    case 'finishing':
      return 300;
    case 'wants_bill':
      return 120;
    case 'leaving':
      return 180;
    case 'needs_clearing':
      return 180;
    default:
      return Infinity;
  }
}

export interface CameraDef {
  id: string;
  name: string;
  place: string;
  view?: { x: number; y: number; w: number; h: number };
}

export const CAMERAS: CameraDef[] = [
  { id: 'cam1', name: 'Cam 1', place: 'Cửa ra vào', view: { x: 0, y: 400, w: 427, h: 240 } },
  { id: 'cam2', name: 'Cam 2', place: 'Khu A', view: { x: 10, y: 60, w: 640, h: 360 } },
  { id: 'cam3', name: 'Cam 3', place: 'Khu B', view: { x: 210, y: 40, w: 640, h: 360 } },
  { id: 'cam4', name: 'Cam 4', place: 'Khu C và quầy thu ngân', view: { x: 289, y: 150, w: 711, h: 400 } },
  { id: 'cam5', name: 'Cam 5', place: 'Bếp' },
];

export const ZONE_CAMERA: Record<Zone, string> = { A: 'cam2', B: 'cam3', C: 'cam4' };
export const cameraDef = (id: string) => CAMERAS.find((c) => c.id === id)!;

export interface PastVisit {
  date: string;
  time: string;
  table: number;
  party: number;
}

export interface Person {
  id: string;
  name?: string;
  visits: number;
  faces: number;
  note?: string;
  consent: 'yes' | 'pending';
  expiresInDays?: number;
  past: PastVisit[];
}

export const PEOPLE: Person[] = [
  {
    id: 'john',
    name: 'Anh John',
    visits: 12,
    faces: 48,
    note: 'Hay ngồi bàn cạnh cửa sổ, thích lẩu Thái ít cay',
    consent: 'yes',
    past: [
      { date: '31/10', time: '18:52', table: 2, party: 2 },
      { date: '27/10', time: '19:10', table: 1, party: 3 },
      { date: '20/10', time: '18:40', table: 2, party: 2 },
    ],
  },
  {
    id: 'mai',
    name: 'Chị Mai',
    visits: 8,
    faces: 31,
    note: 'Dị ứng tôm',
    consent: 'yes',
    past: [
      { date: '29/10', time: '12:15', table: 5, party: 2 },
      { date: '22/10', time: '18:30', table: 6, party: 3 },
    ],
  },
  {
    id: 'khoa',
    name: 'Anh Khoa',
    visits: 5,
    faces: 22,
    note: 'Hay đi nhóm 6 người vào cuối tuần',
    consent: 'yes',
    past: [
      { date: '01/11', time: '19:30', table: 11, party: 6 },
      { date: '25/10', time: '19:05', table: 12, party: 5 },
    ],
  },
  { id: 'p4', visits: 6, faces: 19, consent: 'yes', past: [{ date: '30/10', time: '18:20', table: 8, party: 2 }] },
  { id: 'p5', visits: 4, faces: 12, consent: 'yes', past: [{ date: '28/10', time: '19:45', table: 9, party: 4 }] },
  { id: 'p6', visits: 3, faces: 9, consent: 'pending', expiresInDays: 23, past: [{ date: '26/10', time: '18:05', table: 3, party: 2 }] },
  { id: 'p7', visits: 2, faces: 5, consent: 'pending', expiresInDays: 27, past: [{ date: '30/10', time: '20:10', table: 13, party: 3 }] },
];
