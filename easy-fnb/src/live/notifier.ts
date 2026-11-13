/**
 * Xếp hàng thông báo cho điện thoại nhân viên, để nhiều việc đến cùng lúc không thành một tràng đọc liên tục:
 * - gom các việc đến trong BATCH_MS thành một câu ("Bàn B2 và B3, gọi phục vụ. Bàn B1, cần dọn.");
 * - việc gọi phục vụ đọc trước, rồi dọn bàn, rồi khách mới;
 * - giữa hai lần đọc cách nhau ít nhất GAP_MS;
 * - việc đã đóng hay đã chuyển người trước lúc đọc thì bỏ;
 * - một việc chỉ đọc một lần.
 */
import { speechLine, tableText } from './text';
import type { Alert, AlertKind } from './types';
import { announce } from './voice';

const PRIORITY: Record<AlertKind, number> = { call: 0, needs_clearing: 1, new_guest: 2 };
const WORD: Record<AlertKind, string> = { call: 'gọi phục vụ', needs_clearing: 'cần dọn', new_guest: 'có khách mới' };
const BATCH_MS = 1500;
const FIRST_MS = 150; // đang yên ắng: đọc ngay việc đầu tiên, chỉ chờ 150 ms để gộp việc cùng lúc
const GAP_MS = 4000;
const MAX_NAMES = 4;

function phrase(kind: AlertKind, list: Alert[]) {
  const names = list.filter((a) => a.table).map((a) => tableText(a.table).replace(/^Bàn\s*/i, ''));
  const unnamed = list.length - names.length;
  const parts: string[] = [];
  if (names.length) {
    const shown = names.slice(0, MAX_NAMES);
    const more = names.length - shown.length;
    const joined = more > 0 || shown.length === 1 ? shown.join(', ') : `${shown.slice(0, -1).join(', ')} và ${shown.at(-1)}`;
    parts.push(`Bàn ${joined}${more > 0 ? ` và ${more} bàn nữa` : ''}, ${WORD[kind]}`);
  }
  if (unnamed) parts.push(`${unnamed === 1 ? 'Một khách' : `${unnamed} khách`} ${WORD[kind]}`);
  return parts.join('. ');
}

export function createNotifier(stillMine: (a: Alert) => boolean) {
  const pending = new Map<string, Alert>();
  const said = new Set<string>();
  let timer: number | null = null;
  let lastAt = 0;

  const flush = () => {
    timer = null;
    const list = [...pending.values()]
      .filter(stillMine)
      .sort((a, b) => PRIORITY[a.kind] - PRIORITY[b.kind] || a.created_at - b.created_at);
    pending.clear();
    if (!list.length) return;
    lastAt = Date.now();
    const urgent = list.some((a) => a.kind === 'call' || a.escalated);
    if (list.length === 1) {
      announce(speechLine(list[0]), urgent);
      return;
    }
    const text = (Object.keys(PRIORITY) as AlertKind[])
      .sort((a, b) => PRIORITY[a] - PRIORITY[b])
      .map((k) => ({ k, items: list.filter((a) => a.kind === k) }))
      .filter((g) => g.items.length)
      .map((g) => phrase(g.k, g.items))
      .join('. ');
    announce(text, urgent);
  };

  return {
    push(a: Alert) {
      if (said.has(a.id)) return;
      said.add(a.id);
      pending.set(a.id, a);
      if (timer !== null) return;
      timer = window.setTimeout(
        flush,
        Date.now() - lastAt >= GAP_MS ? FIRST_MS : Math.max(BATCH_MS, lastAt + GAP_MS - Date.now()),
      );
    },
    stop() {
      if (timer !== null) window.clearTimeout(timer);
      timer = null;
      pending.clear();
    },
  };
}
