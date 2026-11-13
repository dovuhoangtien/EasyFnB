import { useEffect, useSyncExternalStore } from 'react';
import { apiUrl, getState } from './api';
import type { Alert, Camera, CameraZones, LogEntry, Settings, Staff, State, TableState } from './types';

/**
 * Kho dữ liệu trực tiếp: một kết nối SSE tới /api/stream dùng chung cho mọi trang.
 * Sự kiện tới dồn vào bản nháp, giao diện chỉ vẽ lại tối đa khoảng 8 lần mỗi giây
 * (camera có thể gửi 4 sự kiện mỗi giây cho mỗi camera).
 */

export type ConnStatus = 'connecting' | 'live' | 'offline';

export interface LiveSnapshot {
  status: ConnStatus;
  /** đã nhận ít nhất một snapshot từ máy chủ */
  loaded: boolean;
  error: string | null;
  /** giờ máy chủ trừ giờ máy này, để tính tuổi việc cho đúng */
  offset: number;
  /** nhân viên đang gắn với kết nối (?staff=), null với màn hình quản lý */
  staffId: string | null;
  settings: Settings | null;
  cameras: Camera[];
  zones: CameraZones[];
  tables: TableState[];
  /** mới nhất ở đầu */
  alerts: Alert[];
  staff: Staff[];
  /** mới nhất ở đầu */
  log: LogEntry[];
}

/** Gọi mỗi khi một việc được tạo hoặc đổi trạng thái (không chờ nhịp vẽ) */
export type AlertListener = (next: Alert, prev: Alert | undefined) => void;

const NOTIFY_MS = 120;
const MAX_ALERTS = 300;
const MAX_LOG = 500;
const CLOSE_GRACE_MS = 2500;
const MAX_RETRY_MS = 10000;

const EMPTY: LiveSnapshot = {
  status: 'connecting',
  loaded: false,
  error: null,
  offset: 0,
  staffId: null,
  settings: null,
  cameras: [],
  zones: [],
  tables: [],
  alerts: [],
  staff: [],
  log: [],
};

function upsertById<T extends { id: string }>(list: T[], item: T): T[] {
  const i = list.findIndex((x) => x.id === item.id);
  if (i < 0) return [...list, item];
  const next = list.slice();
  next[i] = item;
  return next;
}

// Bàn của hai camera có thể trùng tên, nên khoá là camera + id
function upsertTable(list: TableState[], item: TableState): TableState[] {
  const i = list.findIndex((x) => x.id === item.id && x.camera === item.camera);
  if (i < 0) return [...list, item];
  const next = list.slice();
  next[i] = item;
  return next;
}

function alertChanged(a: Alert, b: Alert) {
  return a.status !== b.status || a.assigned_to !== b.assigned_to || a.verify.state !== b.verify.state || a.repeats !== b.repeats || a.escalated !== b.escalated;
}

class LiveStore {
  private snap: LiveSnapshot = EMPTY;
  private work: LiveSnapshot = EMPTY;
  private listeners = new Set<() => void>();
  private alertListeners = new Set<AlertListener>();
  private holders: { staff: string | null }[] = [];
  private es: EventSource | null = null;
  private url: string | null = null;
  private gen = 0;
  private retry = 0;
  private retryTimer: number | undefined;
  private closeTimer: number | undefined;
  private notifyTimer: number | undefined;
  private lastNotify = 0;

  constructor() {
    if (typeof window === 'undefined') return;
    // Điện thoại tắt màn hình thường làm rớt kết nối: mở lại ngay khi quay lại
    const wake = () => {
      if (document.visibilityState !== 'visible' || !this.holders.length) return;
      if (!this.es || this.es.readyState === EventSource.CLOSED) this.reconnectNow();
    };
    document.addEventListener('visibilitychange', wake);
    window.addEventListener('online', wake);
  }

  // ---------- cho React ----------
  subscribe = (fn: () => void) => {
    this.listeners.add(fn);
    return () => {
      this.listeners.delete(fn);
    };
  };

  getSnapshot = () => this.snap;

  onAlertChange(fn: AlertListener) {
    this.alertListeners.add(fn);
    return () => {
      this.alertListeners.delete(fn);
    };
  }

  /** Giờ máy chủ ước tính (ms) */
  serverNow() {
    return Date.now() + this.work.offset;
  }

  // ---------- kết nối ----------
  /** Giữ kết nối mở khi còn trang cần; trả về hàm nhả ra */
  retain(staff: string | null) {
    const holder = { staff };
    this.holders.push(holder);
    window.clearTimeout(this.closeTimer);
    this.ensure();
    return () => {
      const i = this.holders.indexOf(holder);
      if (i >= 0) this.holders.splice(i, 1);
      if (this.holders.length) this.ensure();
      else {
        window.clearTimeout(this.closeTimer);
        this.closeTimer = window.setTimeout(() => this.close(), CLOSE_GRACE_MS);
      }
    };
  }

  private wantedStaff() {
    for (let i = this.holders.length - 1; i >= 0; i--) {
      const s = this.holders[i].staff;
      if (s) return s;
    }
    return null;
  }

  private streamUrl(staff: string | null) {
    return apiUrl(`/api/stream${staff ? `?staff=${encodeURIComponent(staff)}` : ''}`);
  }

  private ensure() {
    const staff = this.wantedStaff();
    const url = this.streamUrl(staff);
    if (this.url === url && (this.es || this.retryTimer !== undefined)) return;
    this.open(staff);
  }

  private reconnectNow() {
    window.clearTimeout(this.retryTimer);
    this.retryTimer = undefined;
    this.open(this.wantedStaff());
  }

  private teardown() {
    this.gen++;
    this.es?.close();
    this.es = null;
    window.clearTimeout(this.retryTimer);
    this.retryTimer = undefined;
  }

  private close() {
    if (this.holders.length) return;
    this.teardown();
    this.url = null;
    this.set({ status: 'connecting' });
  }

  private open(staff: string | null) {
    this.teardown();
    const gen = this.gen;
    const url = this.streamUrl(staff);
    this.url = url;
    this.set({ staffId: staff, status: this.work.loaded && this.work.status === 'live' ? 'live' : 'connecting' });

    let es: EventSource;
    try {
      es = new EventSource(url);
    } catch {
      this.set({ status: 'offline', error: 'Trình duyệt không mở được luồng sự kiện.' });
      return;
    }
    this.es = es;

    const on = <T>(name: string, fn: (data: T) => void) => {
      es.addEventListener(name, (ev) => {
        if (gen !== this.gen) return;
        let data: T;
        try {
          data = JSON.parse((ev as MessageEvent<string>).data) as T;
        } catch {
          return;
        }
        fn(data);
      });
    };

    on<State>('snapshot', (s) => {
      this.retry = 0;
      this.applyState(s, true);
    });
    on<Alert>('alert', (a) => this.upsertAlert(a));
    on<TableState>('table', (t) => this.set({ tables: upsertTable(this.work.tables, t) }));
    on<Camera>('camera', (c) => this.set({ cameras: upsertById(this.work.cameras, c) }));
    on<CameraZones>('zones', (z) => {
      const rest = this.work.zones.filter((x) => x.camera !== z.camera);
      // bàn vừa bị xoá khỏi vùng vẽ thì bỏ luôn trạng thái của nó
      const keep = new Set(z.tables.map((t) => t.id));
      const tables = this.work.tables.filter((t) => t.camera !== z.camera || keep.has(t.id));
      this.set({ zones: [...rest, z], tables });
    });
    on<Staff[]>('staff', (list) => this.set({ staff: Array.isArray(list) ? list : [] }));
    on<LogEntry>('log', (e) => this.addLog(e));
    on<Settings>('settings', (s) => this.set({ settings: s }));
    on<Record<string, never>>('reset', () => void this.onReset(gen));

    es.onerror = () => {
      if (gen !== this.gen) return;
      this.set({
        status: 'offline',
        error: this.work.loaded ? 'Mất kết nối tới máy chủ, đang thử lại.' : 'Chưa kết nối được máy chủ Easy FnB, đang thử lại.',
      });
      // Máy chủ trả lỗi (ví dụ 502 khi chưa chạy) thì trình duyệt không tự thử lại
      if (es.readyState === EventSource.CLOSED) {
        es.close();
        if (this.es === es) this.es = null;
        const wait = Math.min(MAX_RETRY_MS, 1000 * 2 ** this.retry);
        this.retry++;
        this.retryTimer = window.setTimeout(() => {
          this.retryTimer = undefined;
          if (this.holders.length) this.open(this.wantedStaff());
        }, wait);
      }
    };
  }

  // ---------- áp sự kiện ----------
  private applyState(s: State, announce: boolean) {
    const before = announce && this.work.loaded ? new Map(this.work.alerts.map((a) => [a.id, a])) : null;
    const serverTime = typeof s.server_time === 'number' ? s.server_time : Date.now();
    this.set({
      status: 'live',
      loaded: true,
      error: null,
      offset: serverTime - Date.now(),
      settings: s.settings ?? null,
      cameras: s.cameras ?? [],
      zones: s.zones ?? [],
      tables: s.tables ?? [],
      alerts: (s.alerts ?? []).slice(0, MAX_ALERTS),
      staff: s.staff ?? [],
      log: (s.log ?? []).slice(0, MAX_LOG),
    });
    this.schedule(true);
    // Sau khi nối lại: báo những việc đã đổi trong lúc mất kết nối
    if (before) {
      for (const a of s.alerts ?? []) {
        const prev = before.get(a.id);
        if (!prev || alertChanged(prev, a)) this.emitAlert(a, prev);
      }
    }
  }

  /** Thêm hoặc cập nhật một việc (từ SSE, hoặc từ phản hồi của một thao tác) */
  upsertAlert(a: Alert) {
    const list = this.work.alerts;
    const i = list.findIndex((x) => x.id === a.id);
    const prev = i >= 0 ? list[i] : undefined;
    let next: Alert[];
    if (i >= 0) {
      next = list.slice();
      next[i] = a;
    } else {
      next = [a, ...list];
      if (next.length > MAX_ALERTS) next.length = MAX_ALERTS;
    }
    this.set({ alerts: next });
    if (!prev || alertChanged(prev, a)) this.emitAlert(a, prev);
  }

  /** Cập nhật vùng bàn ngay sau khi lưu, không chờ SSE */
  upsertZones(z: CameraZones) {
    this.set({ zones: [...this.work.zones.filter((x) => x.camera !== z.camera), z] });
  }

  setStaff(list: Staff[]) {
    this.set({ staff: list });
  }

  setSettings(s: Settings) {
    this.set({ settings: s });
  }

  private addLog(e: LogEntry) {
    if (this.work.log.some((x) => x.id === e.id)) return;
    const next = [e, ...this.work.log];
    if (next.length > MAX_LOG) next.length = MAX_LOG;
    this.set({ log: next });
  }

  private async onReset(gen: number) {
    this.set({ alerts: [], log: [], tables: [] });
    this.schedule(true);
    try {
      const s = await getState();
      if (gen === this.gen) this.applyState(s, false);
    } catch {
      // bỏ qua: snapshot lần nối lại sau sẽ đồng bộ
    }
  }

  private emitAlert(next: Alert, prev: Alert | undefined) {
    this.alertListeners.forEach((fn) => {
      try {
        fn(next, prev);
      } catch (err) {
        console.error(err);
      }
    });
  }

  // ---------- công bố cho giao diện theo nhịp ----------
  private set(patch: Partial<LiveSnapshot>) {
    this.work = { ...this.work, ...patch };
    this.schedule();
  }

  private schedule(now = false) {
    if (this.notifyTimer !== undefined) {
      if (!now) return;
      window.clearTimeout(this.notifyTimer);
    }
    const wait = now ? 0 : Math.max(0, NOTIFY_MS - (performance.now() - this.lastNotify));
    this.notifyTimer = window.setTimeout(this.flush, wait);
  }

  private flush = () => {
    this.notifyTimer = undefined;
    this.lastNotify = performance.now();
    if (this.snap === this.work) return;
    this.snap = this.work;
    this.listeners.forEach((fn) => fn());
  };
}

export const live = new LiveStore();

// Chỉ khi chạy dev: soi kho dữ liệu từ console
if (import.meta.env.DEV && typeof window !== 'undefined') Object.assign(window, { __live: live });

/**
 * Đọc một phần dữ liệu trực tiếp. Hàm chọn phải trả về đúng một nhánh có sẵn
 * (ví dụ s => s.alerts), không tạo mảng mới; lọc thêm thì dùng useMemo.
 */
export function useLive<T>(select: (s: LiveSnapshot) => T): T {
  return useSyncExternalStore(live.subscribe, () => select(live.getSnapshot()));
}

/** Mở kết nối SSE khi trang hiện, đóng khi không còn trang nào cần */
export function useLiveConnection(staff: string | null = null, enabled = true) {
  useEffect(() => (enabled ? live.retain(staff) : undefined), [staff, enabled]);
}

// ---------- đồng hồ chung, nhảy mỗi giây ----------
let tick = Date.now();
let tickTimer: number | undefined;
const tickSubs = new Set<() => void>();

function subscribeTick(fn: () => void) {
  tickSubs.add(fn);
  if (tickTimer === undefined) {
    tick = Date.now();
    tickTimer = window.setInterval(() => {
      tick = Date.now();
      tickSubs.forEach((f) => f());
    }, 1000);
  }
  return () => {
    tickSubs.delete(fn);
    if (!tickSubs.size) {
      window.clearInterval(tickTimer);
      tickTimer = undefined;
    }
  };
}

/** Giờ máy chủ ước tính, cập nhật mỗi giây (dùng cho đồng hồ đếm tuổi việc) */
export function useServerNow() {
  const t = useSyncExternalStore(subscribeTick, () => tick);
  const offset = useLive((s) => s.offset);
  return t + offset;
}
