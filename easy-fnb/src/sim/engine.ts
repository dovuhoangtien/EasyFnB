import {
  PEOPLE,
  PHASE_LABEL,
  STAFF,
  TABLES,
  TASK_INFO,
  UNITS_PER_METER,
  ZONE_CAMERA,
  approachPoint,
  center,
  prior,
  staffDef,
  tableDef,
  type Person,
  type Phase,
  type TaskKind,
} from './model';
import { dec, durText, hms, median, mulberry32 } from './util';

export interface PhaseMark {
  phase: Phase;
  t: number;
}

export interface TableState {
  id: number;
  phase: Phase;
  since: number;
  party: number;
  person?: string;
  seatedAt?: number;
  orderedAt?: number;
  servedAt?: number;
  foodDue?: number;
  nextAt: number;
  clearingUntil?: number;
  lastVisit?: number;
  lastStaff?: string;
  hand?: number;
  glassLow: boolean;
  platesEmpty: boolean;
  late: boolean;
  broken: boolean;
  urgency: number;
  tier: 0 | 1 | 2 | 3;
  reason: string;
  ratio: number;
  history: PhaseMark[];
}

export type StaffStatus = 'idle' | 'enroute' | 'serving' | 'break';

export interface StaffState {
  id: string;
  x: number;
  y: number;
  tx: number;
  ty: number;
  status: StaffStatus;
  task?: string;
  busyUntil: number;
  /** Lúc bắt đầu đi tới bàn: cần vài giây để nghe thông báo và xong việc đang làm */
  departAt: number;
  handled: number;
  responses: number[];
  breaks: { from: number; to?: number }[];
}

export type TaskStatus = 'open' | 'assigned' | 'done' | 'cancelled';

export interface Task {
  id: string;
  kind: TaskKind;
  table: number;
  priority: 1 | 2 | 3;
  created: number;
  status: TaskStatus;
  assignee?: string;
  assignedAt?: number;
  arrivedAt?: number;
  why?: string;
  escalated?: boolean;
  person?: string;
  spoken?: string;
  whyEn?: string;
}

export type EventKind =
  | 'arrive'
  | 'seat'
  | 'regular'
  | 'order'
  | 'food'
  | 'food_late'
  | 'hand'
  | 'bill'
  | 'leave'
  | 'cleared'
  | 'balk'
  | 'wait'
  | 'assign'
  | 'confirm'
  | 'escalate'
  | 'refill'
  | 'plates'
  | 'broken'
  | 'break'
  | 'clock';

export type Tone = 'plain' | 'bad' | 'ok';

export interface SimEvent {
  id: number;
  t: number;
  kind: EventKind;
  who?: string;
  text: string;
  table?: number;
  staff?: string;
  person?: string;
  camera: string;
  tone: Tone;
}

export interface Spoken {
  id: number;
  t: number;
  staff: string;
  /** Câu đọc tiếng Việt */
  text: string;
  /** Cùng câu đó bằng tiếng Anh */
  textEn: string;
  table: number;
  priority: 1 | 2 | 3;
  /** Giờ thật (ms) lúc phát, 0 với thông báo trong phần lịch sử chạy trước */
  wall: number;
}

export interface Check {
  id: number;
  t: number;
  table: number;
  signal: string;
  verdict: 'confirmed' | 'rejected';
  confidence: number;
  ms: number;
  camera: string;
  note: string;
}

export interface Visit {
  person: string;
  table: number;
  arrived: number;
  left?: number;
  party: number;
}

export interface Meal {
  table: number;
  party: number;
  seatedAt: number;
  orderedAt: number;
  servedAt: number;
}

export interface WaitGroup {
  id: number;
  party: number;
  since: number;
  person?: string;
}

interface Arrival {
  t: number;
  person: string;
  party: number;
  prefer?: number;
}

interface EmitOptions {
  who?: string;
  table?: number;
  staff?: string;
  person?: string;
  camera?: string;
  tone?: Tone;
  at?: number;
}

const WALK = 75; // đơn vị bản đồ mỗi giây, khoảng 1,5 m/s
export const SHIFT_START = hms(17, 0, 0);
export const LIVE_START = hms(19, 20, 0);

export type Trigger = 'hand' | 'bill' | 'regular' | 'balk' | 'glass' | 'broken';

export class Engine {
  t = SHIFT_START;
  speed = 5;
  running = true;
  version = 0;
  live = false;
  /** Giờ thật (ms), vòng lặp hiển thị cập nhật mỗi khung hình */
  wall = 0;
  tables: TableState[];
  staff: StaffState[];
  people: Person[] = PEOPLE.map((p) => ({ ...p, past: [...p.past] }));
  tasks: Task[] = [];
  events: SimEvent[] = [];
  spoken: Spoken[] = [];
  checks: Check[] = [];
  visits: Visit[] = [];
  meals: Meal[] = [];
  seatings: { t: number; table: number; party: number }[] = [];
  waitlist: WaitGroup[] = [];
  balks = 0;
  onSpeak?: (s: Spoken) => void;

  private rnd = mulberry32(20261103);
  private seq = 1;
  private listeners = new Set<() => void>();
  private flags = new Set<string>();
  private schedule: Arrival[] = [
    { t: hms(18, 5, 12), person: 'john', party: 2, prefer: 2 },
    { t: hms(18, 41, 30), person: 'mai', party: 3, prefer: 5 },
    { t: hms(18, 58, 0), person: 'p4', party: 2 },
    { t: hms(19, 22, 40), person: 'khoa', party: 6, prefer: 11 },
  ];

  constructor() {
    this.tables = TABLES.map((d) => this.blankTable(d.id));
    this.staff = STAFF.map((s) => ({
      id: s.id,
      x: s.home.x,
      y: s.home.y,
      tx: s.home.x,
      ty: s.home.y,
      status: 'idle',
      busyUntil: 0,
      departAt: 0,
      handled: 0,
      responses: [],
      breaks: [],
    }));
    for (const s of STAFF) {
      if (s.clockIn <= SHIFT_START) {
        this.emit('clock', 'vào ca, chấm công tự động ở Cam 1', { who: s.name, staff: s.id, camera: 'cam1', at: s.clockIn });
      }
    }
    // Chạy nhanh lịch sử từ đầu ca tới lúc demo bắt đầu
    while (this.t < LIVE_START) this.step(1);
    this.live = true;
  }

  // ---------- kết nối với React ----------
  subscribe = (fn: () => void) => {
    this.listeners.add(fn);
    return () => {
      this.listeners.delete(fn);
    };
  };

  notify() {
    this.version++;
    this.listeners.forEach((fn) => fn());
  }

  // ---------- tiện ích ----------
  private range(a: number, b: number) {
    return a + (b - a) * this.rnd();
  }

  private chance(perSecond: number, dt: number) {
    return this.rnd() < perSecond * dt;
  }

  private blankTable(id: number): TableState {
    return {
      id,
      phase: 'empty',
      since: this.t,
      party: 0,
      nextAt: Infinity,
      glassLow: false,
      platesEmpty: false,
      late: false,
      broken: false,
      urgency: 0,
      tier: 0,
      reason: '',
      ratio: 0,
      history: [],
    };
  }

  person(id: string) {
    return this.people.find((p) => p.id === id);
  }

  personName(id: string) {
    const p = this.person(id);
    return p?.name ?? `Người #${id.slice(1)}`;
  }

  /** Tên khách cho câu tiếng Anh: bỏ danh xưng Anh, Chị */
  personNameEn(id: string) {
    const p = this.person(id);
    return p?.name ? p.name.replace(/^(Anh|Chị|Cô|Chú|Bác|Em)\s+/, "") : `Guest #${id.slice(1)}`;
  }

  staffName(id: string) {
    return id === 'bep' ? 'Bếp' : staffDef(id).name;
  }

  table(id: number) {
    return this.tables[id - 1];
  }

  private emit(kind: EventKind, text: string, o: EmitOptions = {}) {
    const camera = o.camera ?? (o.table ? ZONE_CAMERA[tableDef(o.table).zone] : 'cam1');
    this.events.push({
      id: this.seq++,
      t: o.at ?? this.t,
      kind,
      who: o.who,
      text,
      table: o.table,
      staff: o.staff,
      person: o.person,
      camera,
      tone: o.tone ?? 'plain',
    });
    if (this.events.length > 2500) this.events.splice(0, 500);
  }

  private check(table: number, signal: string, verdict: Check['verdict'], note: string) {
    this.checks.push({
      id: this.seq++,
      t: this.t,
      table,
      signal,
      verdict,
      confidence: verdict === 'confirmed' ? this.range(0.86, 0.97) : this.range(0.08, 0.3),
      ms: Math.round(this.range(850, 2300)),
      camera: ZONE_CAMERA[tableDef(table).zone],
      note,
    });
    if (this.checks.length > 300) this.checks.splice(0, 100);
  }

  private setPhase(tb: TableState, phase: Phase) {
    tb.phase = phase;
    tb.since = this.t;
    tb.history.push({ phase, t: this.t });
  }

  // ---------- vòng mô phỏng ----------
  step(dt: number) {
    this.t += dt;
    const t = this.t;

    while (this.schedule.length && this.schedule[0].t <= t) {
      const a = this.schedule.shift()!;
      this.arriveGroup(a.party, a.person, a.prefer);
    }
    if (this.chance(this.arrivalRate(), dt)) this.arriveGroup(this.partySize());

    for (const g of [...this.waitlist]) {
      if (t - g.since > 720) {
        this.waitlist = this.waitlist.filter((x) => x !== g);
        this.balks++;
        this.emit('balk', `Nhóm ${g.party} khách chờ ${durText(t - g.since)} ở cửa rồi rời đi`, { camera: 'cam1', tone: 'bad' });
      }
    }

    this.scripted();
    for (const tb of this.tables) this.advance(tb, dt);
    this.moveStaff(dt);

    for (const k of this.tasks) {
      if (k.status === 'open' && !k.escalated && t - k.created > 45) {
        k.escalated = true;
        this.emit('escalate', `Bàn ${k.table} ${TASK_INFO[k.kind].label}: chưa có ai rảnh sau 45 giây, đã báo quản lý ca`, {
          table: k.table,
          tone: 'bad',
        });
      }
    }
    this.dispatch();
    for (const tb of this.tables) this.score(tb);
  }

  private arrivalRate() {
    const h = this.t / 3600;
    if (h < 18) return 1 / 320;
    if (h < 20.5) return 1 / 230;
    return 1 / 330;
  }

  private partySize() {
    const r = this.rnd();
    if (r < 0.35) return 2;
    if (r < 0.5) return 3;
    if (r < 0.8) return 4;
    if (r < 0.88) return 5;
    return 6;
  }

  private once(key: string, at: number, fn: () => boolean | void) {
    if (!this.flags.has(key) && this.t >= at) {
      if (fn() !== false) this.flags.add(key);
    }
  }

  private scripted() {
    this.once('hung-clock', hms(17, 4, 5), () => {
      this.emit('clock', 'vào ca, chấm công tự động ở Cam 1', { who: 'Hùng', staff: 'hung', camera: 'cam1' });
    });
    this.once('broken-9', hms(18, 12, 40), () => this.breakAt(9));
    this.once('minh-break', hms(18, 30, 0), () => this.startBreak('minh'));
    this.once('minh-back', hms(18, 45, 10), () => this.endBreak('minh'));
  }

  private startBreak(id: string) {
    const s = this.staff.find((x) => x.id === id)!;
    if (s.status !== 'idle') return false;
    s.status = 'break';
    s.tx = 315;
    s.ty = 590;
    s.breaks.push({ from: this.t });
    this.emit('break', 'bắt đầu nghỉ giải lao', { who: staffDef(id).name, staff: id, camera: 'cam1' });
  }

  private endBreak(id: string) {
    const s = this.staff.find((x) => x.id === id)!;
    if (s.status !== 'break') return;
    s.status = 'idle';
    const home = staffDef(id).home;
    s.tx = home.x;
    s.ty = home.y;
    const last = s.breaks[s.breaks.length - 1];
    if (last) last.to = this.t;
    this.emit('break', `nghỉ xong, quay lại khu ${staffDef(id).zone ?? ''}`.trim(), { who: staffDef(id).name, staff: id, camera: 'cam1' });
  }

  private findTable(party: number, prefer?: number) {
    if (prefer) {
      const p = this.table(prefer);
      if (p.phase === 'empty' && tableDef(prefer).seats >= party) return p;
    }
    const fits = this.tables
      .filter((tb) => tb.phase === 'empty' && tableDef(tb.id).seats >= party)
      .sort((a, b) => tableDef(a.id).seats - tableDef(b.id).seats);
    if (!fits.length) return undefined;
    const smallest = tableDef(fits[0].id).seats;
    const same = fits.filter((tb) => tableDef(tb.id).seats === smallest);
    return same[Math.floor(this.rnd() * same.length)];
  }

  private arriveGroup(party: number, person?: string, prefer?: number) {
    const tb = this.findTable(party, prefer);
    if (tb) {
      if (!person) this.emit('arrive', `Nhóm ${party} khách vào quán`, { camera: 'cam1' });
      this.seat(tb, party, person);
      return;
    }
    if (this.waitlist.length < 3) {
      this.waitlist.push({ id: this.seq++, party, since: this.t, person });
      this.emit('wait', `Nhóm ${party} khách đang chờ ở cửa, chưa có bàn phù hợp`, { camera: 'cam1' });
      return;
    }
    this.balks++;
    this.emit('balk', `Nhóm ${party} khách đứng ở cửa ${durText(this.range(35, 110))} rồi rời đi`, { camera: 'cam1', tone: 'bad' });
  }

  private seat(tb: TableState, party: number, person?: string) {
    Object.assign(tb, this.blankTable(tb.id));
    tb.phase = 'seated';
    tb.since = this.t;
    tb.party = party;
    tb.person = person;
    tb.seatedAt = this.t;
    tb.history = [{ phase: 'seated', t: this.t }];
    this.seatings.push({ t: this.t, table: tb.id, party });
    if (person) {
      const p = this.person(person)!;
      this.visits.push({ person, table: tb.id, arrived: this.t, party });
      this.emit('regular', `vừa vào quán, nhận diện ở cửa, lần ghé thứ ${p.visits}`, {
        who: this.personName(person),
        person,
        camera: 'cam1',
      });
    }
    this.emit('seat', `Nhóm ${party} khách ngồi vào bàn ${tb.id}`, { table: tb.id, person });
    this.addTask('greet', tb.id, person ? { person } : {});
  }

  private seatWaiting() {
    for (const g of [...this.waitlist]) {
      const tb = this.findTable(g.party);
      if (!tb) continue;
      this.waitlist = this.waitlist.filter((x) => x !== g);
      this.seat(tb, g.party, g.person);
    }
  }

  private advance(tb: TableState, dt: number) {
    const t = this.t;
    const zone = tableDef(tb.id).zone;
    switch (tb.phase) {
      case 'ordering': {
        if (t < tb.nextAt) break;
        tb.orderedAt = t;
        this.setPhase(tb, 'waiting_food');
        let wait = this.range(420, 880) * (zone === 'C' ? 0.65 : 1);
        if (tb.id === 12 && t > hms(18, 0) && t < hms(18, 50)) wait = 1390;
        tb.foodDue = t + wait;
        this.emit('order', `Bàn ${tb.id} đã gọi món`, { table: tb.id });
        break;
      }
      case 'waiting_food': {
        const waited = t - (tb.orderedAt ?? t);
        const p = prior('waiting_food', tb.party);
        if (!tb.late && waited > p * 1.5) {
          tb.late = true;
          this.addTask('food_late', tb.id);
          this.emit('food_late', `Bàn ${tb.id} chờ món ${Math.round(waited / 60)} phút, chậm ${dec(waited / p)}× so với thường lệ. Đã báo bếp`, {
            table: tb.id,
            tone: 'bad',
          });
        }
        if (t >= (tb.foodDue ?? Infinity)) {
          tb.servedAt = t;
          this.meals.push({ table: tb.id, party: tb.party, seatedAt: tb.seatedAt ?? t, orderedAt: tb.orderedAt ?? t, servedAt: t });
          this.closeTasks(tb.id, ['food_late'], 'done');
          this.setPhase(tb, 'eating');
          tb.nextAt = t + this.range(1500, 2500) * (0.85 + tb.party * 0.05);
          this.emit('food', `Món đã lên bàn ${tb.id} sau ${durText(waited)}`, { table: tb.id });
        }
        break;
      }
      case 'eating': {
        if (tb.hand === undefined && this.chance(1 / 1100, dt)) this.raiseHand(tb);
        if (!tb.glassLow && this.chance(1 / 1500, dt)) this.lowGlass(tb);
        if (zone === 'C' && !tb.platesEmpty && this.chance(1 / 1300, dt)) this.emptyPlates(tb);
        if (this.chance(1 / 2400, dt)) this.rejectedSignal(tb);
        if (t >= tb.nextAt) {
          this.setPhase(tb, 'finishing');
          tb.nextAt = t + this.range(150, 360);
        }
        break;
      }
      case 'finishing':
        if (t >= tb.nextAt) this.requestBill(tb);
        break;
      case 'leaving': {
        if (t < tb.nextAt) break;
        this.setPhase(tb, 'needs_clearing');
        tb.hand = undefined;
        tb.glassLow = false;
        tb.platesEmpty = false;
        this.closeTasks(tb.id, ['call', 'refill', 'plates'], 'cancelled');
        const v = this.visits.find((x) => x.table === tb.id && x.left === undefined && x.person === tb.person);
        if (v) v.left = t;
        this.emit('leave', `Khách bàn ${tb.id} đã rời đi, trên bàn còn bát đĩa`, { table: tb.id, person: tb.person });
        this.addTask('clear', tb.id);
        break;
      }
      case 'needs_clearing':
        if (tb.clearingUntil !== undefined && t >= tb.clearingUntil) {
          this.emit('cleared', `Bàn ${tb.id} đã dọn xong, sẵn sàng đón khách`, { table: tb.id, tone: 'ok' });
          Object.assign(tb, this.blankTable(tb.id));
          this.seatWaiting();
        }
        break;
      default:
        break;
    }
  }

  private raiseHand(tb: TableState) {
    tb.hand = this.t;
    this.check(tb.id, 'Giơ tay', 'confirmed', 'Khách giơ tay hướng về phía nhân viên');
    this.emit('hand', `Khách bàn ${tb.id} giơ tay gọi phục vụ`, { table: tb.id });
    this.addTask('call', tb.id);
  }

  private lowGlass(tb: TableState) {
    tb.glassLow = true;
    this.check(tb.id, 'Ly cạn', 'confirmed', 'Hai ly gần cạn, khách vẫn đang ăn');
    this.emit('refill', `Bàn ${tb.id} có ly đã cạn`, { table: tb.id });
    this.addTask('refill', tb.id);
  }

  private emptyPlates(tb: TableState) {
    tb.platesEmpty = true;
    this.emit('plates', `Bàn ${tb.id} đã hết đĩa thịt, nồi lẩu vẫn đang sôi`, { table: tb.id });
    this.addTask('plates', tb.id);
  }

  private rejectedSignal(tb: TableState) {
    const notes = ['Khách vươn vai', 'Khách chỉnh tóc', 'Khách nâng ly chúc mừng', 'Khách chỉ tay vào điện thoại'];
    this.check(tb.id, 'Giơ tay', 'rejected', notes[Math.floor(this.rnd() * notes.length)]);
  }

  private requestBill(tb: TableState) {
    this.setPhase(tb, 'wants_bill');
    this.check(tb.id, 'Ra hiệu tính tiền', 'confirmed', 'Khách làm động tác ký lên lòng bàn tay');
    this.emit('bill', `Khách bàn ${tb.id} ra hiệu tính tiền`, { table: tb.id, person: tb.person });
    this.addTask('bill', tb.id);
  }

  private breakAt(id: number) {
    const tb = this.table(id);
    tb.broken = true;
    this.check(id, 'Đồ vỡ', 'confirmed', 'Mảnh bát vỡ trên sàn cạnh ghế phía cửa sổ');
    this.emit('broken', `Phát hiện đồ vỡ dưới bàn ${id}`, { table: id, tone: 'bad' });
    this.addTask('broken', id);
  }

  // ---------- việc và điều phối ----------
  addTask(kind: TaskKind, table: number, extra: Partial<Task> = {}) {
    if (this.tasks.some((k) => k.table === table && k.kind === kind && (k.status === 'open' || k.status === 'assigned'))) return;
    const info = TASK_INFO[kind];
    const task: Task = { id: `k${this.seq++}`, kind, table, priority: info.priority, created: this.t, status: 'open', ...extra };
    if (kind === 'clear' && this.waitlist.length) task.priority = 1;
    if (kind === 'food_late') {
      task.status = 'assigned';
      task.assignee = 'bep';
      task.assignedAt = this.t;
      task.why = 'Món chờ quá ngưỡng thường lệ, báo màn hình bếp';
    }
    this.tasks.push(task);
    this.dispatch();
  }

  private closeTasks(table: number, kinds: TaskKind[], status: 'done' | 'cancelled') {
    for (const k of this.tasks) {
      if (k.table !== table || !kinds.includes(k.kind)) continue;
      if (k.status !== 'open' && k.status !== 'assigned') continue;
      k.status = status;
      const s = this.staff.find((x) => x.task === k.id);
      if (s) this.freeStaff(s);
    }
  }

  private freeStaff(s: StaffState) {
    s.status = 'idle';
    s.task = undefined;
    const home = staffDef(s.id).home;
    s.tx = home.x;
    s.ty = home.y;
  }

  spokenText(task: Task) {
    const n = task.table;
    switch (task.kind) {
      case 'greet':
        return task.person
          ? `${this.personName(task.person)} vừa tới bàn ${n}, mời chào khách`
          : `bàn ${n} có khách mới, mời chào bàn`;
      case 'call':
        return `bàn ${n} gọi phục vụ`;
      case 'bill':
        return `bàn ${n} muốn tính tiền`;
      case 'clear':
        return this.waitlist.length ? `bàn ${n} cần dọn ngay, cửa đang có khách chờ` : `bàn ${n} cần dọn`;
      case 'refill':
        return `bàn ${n} cần thêm nước`;
      case 'plates':
        return `bàn ${n} hết món, mời gọi thêm`;
      case 'broken':
        return `có đồ vỡ ở bàn ${n}, cần dọn ngay`;
      default:
        return `bàn ${n} món ra chậm`;
    }
  }

  spokenTextEn(task: Task) {
    const n = task.table;
    switch (task.kind) {
      case "greet":
        return task.person ? `${this.personNameEn(task.person)} just sat at table ${n}, please greet them` : `new guests at table ${n}, please greet them`;
      case "call":
        return `table ${n} is calling for service`;
      case "bill":
        return `table ${n} is asking for the bill`;
      case "clear":
        return this.waitlist.length ? `clear table ${n} now, guests are waiting at the door` : `table ${n} needs clearing`;
      case "refill":
        return `table ${n} needs a water refill`;
      case "plates":
        return `table ${n} is out of food, offer to order more`;
      case "broken":
        return `broken dish at table ${n}, please clean it up now`;
      default:
        return `food for table ${n} is running late`;
    }
  }

  private dispatch() {
    const open = this.tasks
      .filter((k) => k.status === 'open')
      .sort((a, b) => a.priority - b.priority || a.created - b.created);
    for (const task of open) {
      const def = tableDef(task.table);
      const target = center(task.table);
      const roles = TASK_INFO[task.kind].roles;
      let best: { s: StaffState; cost: number; meters: number; sameZone: boolean } | undefined;
      for (const s of this.staff) {
        if (s.status !== 'idle') continue;
        const sd = staffDef(s.id);
        const rank = roles.indexOf(sd.role);
        if (rank < 0) continue;
        const meters = Math.hypot(s.x - target.x, s.y - target.y) / UNITS_PER_METER;
        const sameZone = !sd.zone || sd.zone === def.zone;
        const cost = meters + (sameZone ? 0 : 2.5) + rank * 3 + s.handled * 0.02;
        if (!best || cost < best.cost) best = { s, cost, meters, sameZone };
      }
      if (!best) continue;
      const { s, meters, sameZone } = best;
      const sd = staffDef(s.id);
      task.status = 'assigned';
      task.assignee = s.id;
      task.assignedAt = this.t;
      const where = meters < 1.2 ? 'Đang đứng ngay cạnh bàn' : `Gần nhất, cách ${dec(meters)} m`;
      task.why = `${where}, đang rảnh${sd.zone && sameZone ? `, phụ trách khu ${def.zone}` : ''}`;
      task.whyEn = `${meters < 1.2 ? 'Right next to the table' : `Closest, ${meters.toFixed(1)} m away`}, free${sd.zone && sameZone ? `, covers zone ${def.zone}` : ''}`;
      s.status = 'enroute';
      s.task = task.id;
      s.departAt = this.t + (meters < 1.2 ? this.range(2, 5) : task.priority === 1 ? this.range(5, 12) : this.range(9, 24));
      const p = approachPoint(def, s);
      s.tx = p.x;
      s.ty = p.y;
      task.spoken = `${sd.name}, ${this.spokenText(task)}`;
      this.emit('assign', `nhận việc bàn ${task.table}: ${TASK_INFO[task.kind].label}`, { who: sd.name, staff: s.id, table: task.table });
      const said: Spoken = {
        id: this.seq++,
        t: this.t,
        staff: s.id,
        text: task.spoken,
        textEn: `${sd.name}, ${this.spokenTextEn(task)}`,
        table: task.table,
        priority: task.priority,
        wall: this.live ? this.wall : 0,
      };
      this.spoken.push(said);
      if (this.spoken.length > 400) this.spoken.splice(0, 100);
      if (this.live) this.onSpeak?.(said);
    }
  }

  private moveStaff(dt: number) {
    for (const s of this.staff) {
      if (s.status === 'enroute' && this.t < s.departAt) continue;
      const dx = s.tx - s.x;
      const dy = s.ty - s.y;
      const d = Math.hypot(dx, dy);
      const stepLen = WALK * dt;
      if (d <= stepLen) {
        s.x = s.tx;
        s.y = s.ty;
        if (s.status === 'enroute') this.arrive(s);
      } else {
        s.x += (dx / d) * stepLen;
        s.y += (dy / d) * stepLen;
      }
      if (s.status === 'serving' && this.t >= s.busyUntil) this.freeStaff(s);
    }
  }

  private arrive(s: StaffState) {
    const task = this.tasks.find((k) => k.id === s.task);
    if (!task) {
      this.freeStaff(s);
      return;
    }
    const tb = this.table(task.table);
    const sd = staffDef(s.id);
    task.status = 'done';
    task.arrivedAt = this.t;
    const response = this.t - task.created;
    s.responses.push(response);
    s.handled++;
    s.status = 'serving';
    s.busyUntil = this.t + TASK_INFO[task.kind].service;
    tb.lastVisit = this.t;
    tb.lastStaff = s.id;
    this.emit('confirm', `đã tới bàn ${tb.id} sau ${durText(response)}, camera xác nhận`, {
      who: sd.name,
      staff: s.id,
      table: tb.id,
      tone: 'ok',
    });
    switch (task.kind) {
      case 'greet':
        if (tb.phase === 'seated') {
          this.setPhase(tb, 'ordering');
          tb.nextAt = this.t + this.range(150, 300);
        }
        break;
      case 'call':
        tb.hand = undefined;
        break;
      case 'bill':
        if (tb.phase === 'wants_bill') {
          this.setPhase(tb, 'leaving');
          tb.nextAt = this.t + this.range(60, 150);
        }
        break;
      case 'clear':
        if (tb.phase === 'needs_clearing') tb.clearingUntil = this.t + TASK_INFO.clear.service;
        tb.broken = false;
        break;
      case 'broken':
        tb.broken = false;
        break;
      case 'refill':
        tb.glassLow = false;
        break;
      case 'plates':
        tb.platesEmpty = false;
        break;
      default:
        break;
    }
    // Nhân viên đã ở bàn thì xử lý luôn các yêu cầu nhỏ khác của bàn đó
    if (sd.role === 'serve') {
      if (tb.hand !== undefined) tb.hand = undefined;
      tb.glassLow = false;
      for (const k of this.tasks) {
        if (k.table !== tb.id || k === task || !['call', 'refill'].includes(k.kind)) continue;
        if (k.status !== 'open' && k.status !== 'assigned') continue;
        k.status = 'done';
        k.arrivedAt = this.t;
        const other = this.staff.find((x) => x.task === k.id);
        if (other) this.freeStaff(other);
      }
    }
  }

  // ---------- điểm khẩn cấp ----------
  private score(tb: TableState) {
    if (tb.phase === 'empty') {
      tb.urgency = 0;
      tb.tier = 0;
      tb.reason = '';
      tb.ratio = 0;
      return;
    }
    const t = this.t;
    const base = tb.phase === 'waiting_food' ? tb.orderedAt ?? tb.since : tb.since;
    const inState = t - base;
    const p = prior(tb.phase, tb.party);
    const ratio = inState / p;
    const late = Math.min(3, ratio);
    let ev = 0;
    let reason = '';
    if (tb.hand !== undefined) {
      ev = 3.8;
      reason = `Giơ tay gọi phục vụ ${durText(t - tb.hand)} trước`;
    } else if (tb.broken) {
      ev = 3.4;
      reason = 'Có đồ vỡ cạnh bàn';
    } else if (tb.phase === 'wants_bill') {
      ev = 2;
      reason = `Ra hiệu tính tiền ${durText(inState)} trước`;
    } else if (tb.phase === 'seated') {
      ev = 1.6;
      reason = `Mới ngồi ${durText(inState)}, chưa ai chào`;
    } else if (tb.phase === 'needs_clearing') {
      ev = this.waitlist.length ? 2.2 : 1.3;
      reason = `Bàn bẩn ${durText(inState)}${this.waitlist.length ? ', cửa đang có khách chờ' : ''}`;
    } else if (tb.glassLow) {
      ev = 0.9;
      reason = 'Có ly đã cạn';
    } else if (tb.platesEmpty) {
      ev = 0.9;
      reason = 'Hết đĩa thịt, có thể mời gọi thêm';
    }
    const c = center(tb.id);
    const staffNear = this.staff.some((s) => s.status !== 'break' && Math.hypot(s.x - c.x, s.y - c.y) < 85);
    let x = 1.5 * late + ev - (staffNear ? 2.2 : 0) - 2.6;
    if (tb.person) x += 0.3;
    const score = Math.round(100 / (1 + Math.exp(-x)));
    if (!reason) {
      const label = PHASE_LABEL[tb.phase];
      reason = ratio >= 1 ? `${label} ${durText(inState)}, chậm ${dec(ratio)}× so với thường lệ` : `${label} ${durText(inState)}`;
    }
    tb.urgency = score;
    tb.ratio = ratio;
    tb.reason = reason;
    tb.tier = score >= 75 ? 1 : score >= 50 ? 2 : score >= 35 ? 3 : 0;
  }

  // ---------- điều khiển demo ----------
  trigger(kind: Trigger) {
    const occupied = this.tables.filter((tb) => ['eating', 'waiting_food', 'finishing'].includes(tb.phase));
    const pick = (list: TableState[], prefer?: number) =>
      list.find((tb) => tb.id === prefer) ?? list[Math.floor(this.rnd() * list.length)];
    switch (kind) {
      case 'hand': {
        const list = occupied.filter((tb) => tb.hand === undefined);
        const tb = pick(list, 7);
        if (tb) this.raiseHand(tb);
        break;
      }
      case 'bill': {
        const tb = pick(this.tables.filter((x) => x.phase === 'eating' || x.phase === 'finishing'));
        if (tb) this.requestBill(tb);
        break;
      }
      case 'glass': {
        const tb = pick(occupied.filter((x) => !x.glassLow));
        if (tb) this.lowGlass(tb);
        break;
      }
      case 'broken': {
        const tb = pick(occupied.filter((x) => !x.broken));
        if (tb) this.breakAt(tb.id);
        break;
      }
      case 'regular': {
        const here = new Set(this.tables.map((tb) => tb.person).filter(Boolean));
        const waiting = new Set(this.waitlist.map((g) => g.person).filter(Boolean));
        const who = ['mai', 'john', 'p5', 'p4'].find((id) => !here.has(id) && !waiting.has(id));
        if (who) {
          const p = this.person(who)!;
          p.visits += 1;
          this.arriveGroup(2, who, p.past[0]?.table);
        }
        break;
      }
      case 'balk':
        this.balks++;
        this.emit('balk', `Nhóm 3 khách đứng ở cửa ${durText(this.range(40, 90))}, không ai đón, rồi rời đi`, { camera: 'cam1', tone: 'bad' });
        break;
    }
    this.notify();
  }

  setSpeed(speed: number) {
    this.speed = speed;
    this.notify();
  }

  toggleRunning() {
    this.running = !this.running;
    this.notify();
  }

  rename(id: string, name: string) {
    const p = this.person(id);
    if (!p) return;
    p.name = name.trim() || undefined;
    this.notify();
  }

  setNote(id: string, note: string) {
    const p = this.person(id);
    if (!p) return;
    p.note = note;
    this.notify();
  }

  // ---------- số liệu dẫn xuất ----------
  openTasks() {
    return this.tasks
      .filter((k) => k.status === 'open' || k.status === 'assigned')
      .sort((a, b) => a.priority - b.priority || a.created - b.created);
  }

  doneTasks() {
    return this.tasks.filter((k) => k.status === 'done' && k.arrivedAt !== undefined && k.kind !== 'food_late');
  }

  medianResponse() {
    return median(this.doneTasks().map((k) => k.arrivedAt! - k.created));
  }

  guestsSeated() {
    return this.tables.filter((tb) => tb.phase !== 'empty' && tb.phase !== 'needs_clearing').reduce((sum, tb) => sum + tb.party, 0);
  }

  /** Bàn sắp trống và thời gian ước tính, tính từ giai đoạn bữa ăn */
  soonFree() {
    const t = this.t;
    const out: { table: number; eta: number }[] = [];
    for (const tb of this.tables) {
      let eta: number | undefined;
      if (tb.phase === 'finishing') eta = Math.max(0, tb.nextAt - t) + 60 + 110 + 70;
      else if (tb.phase === 'wants_bill') eta = 60 + 110 + 70;
      else if (tb.phase === 'leaving') eta = Math.max(0, tb.nextAt - t) + 70;
      else if (tb.phase === 'needs_clearing') eta = tb.clearingUntil ? Math.max(0, tb.clearingUntil - t) : 90;
      if (eta !== undefined) out.push({ table: tb.id, eta });
    }
    return out.sort((a, b) => a.eta - b.eta);
  }

  staffMedian(id: string) {
    const s = this.staff.find((x) => x.id === id);
    return s ? median(s.responses) : NaN;
  }

  /** Bảng "AI đọc bàn": kết quả mô hình thị giác trả về cho mỗi bàn */
  reading(tb: TableState) {
    const p = tb.party;
    const progress = tb.phase === 'eating' ? Math.min(1, (this.t - tb.since) / Math.max(1, tb.nextAt - tb.since)) : 0;
    let withFood = 0;
    let empty = 0;
    if (tb.phase === 'eating') {
      withFood = Math.max(1, Math.round((p + 1) * (1 - progress * 0.8)));
      empty = p + 1 - withFood;
    } else if (tb.phase === 'finishing' || tb.phase === 'wants_bill' || tb.phase === 'leaving') {
      withFood = 1;
      empty = p + 1;
    } else if (tb.phase === 'needs_clearing') {
      empty = p + 2;
    }
    return {
      phase: tb.phase,
      people: tb.phase === 'needs_clearing' ? 0 : p,
      plates_with_food: withFood,
      empty_plates: empty,
      glasses_low: tb.glassLow ? 2 : 0,
      hand_raised: tb.hand !== undefined,
      bill_folder: tb.phase === 'leaving',
      menus_open: tb.phase === 'seated' || tb.phase === 'ordering',
      hotpot_present: tableDef(tb.id).zone === 'C' && tb.phase !== 'empty',
      confidence: Number((0.8 + ((tb.id * 37) % 15) / 100).toFixed(2)),
    };
  }
}
