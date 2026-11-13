import { useEffect, useLayoutEffect, useReducer, useRef, useState, type CSSProperties, type ReactNode } from 'react';

const reduced = () => typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

interface Entry<T> {
  key: string;
  item: T;
  leaving: boolean;
  until?: number;
}

interface ListProps<T> {
  items: T[];
  getKey: (item: T) => string;
  children: (item: T, leaving: boolean) => ReactNode;
  className?: string;
  /** thời gian giữ lại phần tử đã bị gỡ để chạy hiệu ứng rời đi */
  exitMs?: number;
  label?: string;
}

/**
 * Danh sách có chuyển động: phần tử mới trượt vào, phần tử bị gỡ mờ đi rồi mới biến mất,
 * các phần tử còn lại trượt về chỗ mới (FLIP) thay vì nhảy.
 */
export function AnimatedList<T>({ items, getKey, children, className, exitMs = 240, label }: ListProps<T>) {
  const prev = useRef<Entry<T>[]>([]);
  const tops = useRef(new Map<string, number>());
  const nodes = useRef(new Map<string, HTMLElement>());
  const first = useRef(true);
  const [, bump] = useReducer((n: number) => n + 1, 0);
  const now = performance.now();

  const keys = new Set(items.map(getKey));
  const view: Entry<T>[] = items.map((item) => ({ key: getKey(item), item, leaving: false }));
  prev.current.forEach((e, i) => {
    if (keys.has(e.key)) return;
    const until = e.until ?? now + exitMs;
    if (until > now) view.splice(Math.min(i, view.length), 0, { ...e, leaving: true, until });
  });

  useLayoutEffect(() => {
    prev.current = view;
    const still = reduced();
    const next = new Map<string, number>();
    for (const e of view) {
      const el = nodes.current.get(e.key);
      if (!el) continue;
      const top = el.offsetTop;
      next.set(e.key, top);
      const before = tops.current.get(e.key);
      if (!still && !e.leaving && before !== undefined && Math.abs(before - top) > 1) {
        el.animate([{ transform: `translateY(${before - top}px)` }, { transform: 'translateY(0)' }], {
          duration: 360,
          easing: 'cubic-bezier(0.16, 1, 0.3, 1)',
        });
      }
    }
    tops.current = next;
    first.current = false;
  });

  const nextExit = view.reduce((t, e) => (e.leaving && e.until ? Math.min(t, e.until) : t), Infinity);
  useEffect(() => {
    if (nextExit === Infinity) return;
    const t = window.setTimeout(bump, Math.max(0, nextExit - performance.now()) + 20);
    return () => window.clearTimeout(t);
  }, [nextExit]);

  return (
    <div className={className} aria-label={label} role={label ? 'list' : undefined}>
      {view.map((e, i) => (
        <div
          key={e.key}
          role={label ? 'listitem' : undefined}
          className="fx-item"
          data-leaving={e.leaving || undefined}
          // lần đầu hiện cả danh sách thì so le nhẹ; phần tử tới sau thì vào ngay
          style={first.current ? ({ '--i': Math.min(i, 6) } as CSSProperties) : undefined}
          ref={(el) => {
            if (el) nodes.current.set(e.key, el);
            else nodes.current.delete(e.key);
          }}
        >
          {children(e.item, e.leaving)}
        </div>
      ))}
    </div>
  );
}

/** Một chữ số: có bật lên hay không được chốt lúc nó xuất hiện, vẽ lại không làm nó bật lần nữa */
function Digit({ char, index, animate }: { char: string; index: number; animate: boolean }) {
  const [cls] = useState(animate ? 'fx-roll-in' : undefined);
  return (
    <span className={cls} style={{ '--d': index } as CSSProperties}>
      {char}
    </span>
  );
}

/**
 * Con số đổi thì chỉ những chữ số đổi mới bật lên, so le từ trái sang.
 * Cách bật theo block "Rolling counter" của Bencho (https://bencho.dev), giấy phép MIT, Copyright (c) 2026 Lorenzo Cabra.
 */
export function Roll({ value, className, style }: { value: string | number; className?: string; style?: CSSProperties }) {
  const seen = useRef(false);
  useEffect(() => {
    seen.current = true;
  }, []);
  const text = String(value);
  const chars = [...text];
  return (
    <span className={`fx-roll ${className ?? ''}`} style={style}>
      <span className="sr-only">{text}</span>
      <span aria-hidden="true">
        {chars.map((c, i) => (
          // khoá theo hàng (đơn vị, chục) và giá trị: chữ số nào không đổi thì đứng yên
          <Digit key={`${chars.length - i}-${c}`} char={c} index={i} animate={seen.current} />
        ))}
      </span>
    </span>
  );
}

/** Bọc một trang: mỗi lần đổi đường dẫn nội dung hiện lên nhẹ */
export function RouteFade({ id, children }: { id: string; children: ReactNode }) {
  return (
    <div key={id} className="fx-route">
      {children}
    </div>
  );
}
