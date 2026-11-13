import { useState, type CSSProperties, type ReactNode } from 'react';

/* Biểu đồ của trang "Ca hôm nay", tự vẽ bằng HTML và CSS, không dùng thư viện.
 * Mỗi nhóm (loại việc, mức tốc độ) có một màu cố định; chỉ vào cột hay thanh nào thì hiện con số của nó,
 * và mỗi biểu đồ có kèm một bảng số cho trình đọc màn hình. */

export interface Series {
  id: string;
  label: string;
  /** tên token màu, ví dụ "var(--fx-k-guest)" */
  color: string;
}

export const KIND_SERIES: Series[] = [
  { id: 'new_guest', label: 'Khách mới', color: 'var(--fx-k-guest)' },
  { id: 'call', label: 'Gọi phục vụ', color: 'var(--fx-k-call)' },
  { id: 'needs_clearing', label: 'Cần dọn bàn', color: 'var(--fx-k-clear)' },
];

export const SPEED_SERIES: Series[] = [
  { id: 'fast', label: 'Nhanh', color: 'var(--fx-fast)' },
  { id: 'ok', label: 'Hơi chậm', color: 'var(--fx-ok)' },
  { id: 'slow', label: 'Chậm', color: 'var(--fx-slow)' },
  { id: 'missed', label: 'Không ai tới', color: 'var(--fx-missed)' },
];

type Values = Record<string, number | undefined>;

const sum = (series: Series[], v: Values) => series.reduce((n, s) => n + (v[s.id] ?? 0), 0);
const spoken = (series: Series[], v: Values, unit: string) =>
  series
    .filter((s) => v[s.id])
    .map((s) => `${v[s.id]} ${s.label.toLowerCase()}`)
    .join(', ') || `không có ${unit} nào`;

/** Mốc trên cùng của trục: số chẵn gọn, để vạch giữa cũng là số nguyên */
function niceTop(max: number): number {
  const step = max <= 10 ? 2 : max <= 20 ? 4 : max <= 50 ? 10 : 20;
  return Math.max(2, Math.ceil(max / step) * step);
}

export function Legend({ series }: { series: Series[] }) {
  return (
    <ul className="fx-legend">
      {series.map((s) => (
        <li key={s.id}>
          <i className="fx-swatch" style={{ background: s.color }} />
          {s.label}
        </li>
      ))}
    </ul>
  );
}

/** Ô số hiện ra khi chỉ vào một cột hay một thanh: tổng đứng trước, rồi tới từng nhóm */
function Tip({ title, series, values, unit, edge }: { title: string; series: Series[]; values: Values; unit: string; edge?: 'start' | 'end' }) {
  const total = sum(series, values);
  return (
    <div className="fx-tip" data-edge={edge} aria-hidden="true">
      <p className="fx-tip-title">{title}</p>
      <p className="fx-tip-total">
        <b>{total}</b> {unit}
      </p>
      {total > 0 && (
        <ul>
          {series
            .filter((s) => values[s.id])
            .map((s) => (
              <li key={s.id}>
                <i className="fx-swatch" style={{ background: s.color }} />
                <span>{s.label}</span>
                <b>{values[s.id]}</b>
              </li>
            ))}
        </ul>
      )}
    </div>
  );
}

export interface TimePoint {
  /** nhãn dưới trục, ví dụ "14:05" */
  label: string;
  /** tên đầy đủ của cột trong ô số, ví dụ "14:05 đến 14:10" */
  title: string;
  values: Values;
}

/** Cột xếp chồng theo thời gian: mỗi cột một quãng giờ, mỗi đoạn màu một nhóm */
export function TimeColumns({
  title,
  note,
  series,
  points,
  unit = 'việc',
}: {
  title: string;
  note?: ReactNode;
  series: Series[];
  points: TimePoint[];
  unit?: string;
}) {
  const [hot, setHot] = useState<number | null>(null);
  const totals = points.map((p) => sum(series, p.values));
  const top = niceTop(Math.max(1, ...totals));
  const every = Math.ceil(points.length / 7);

  return (
    <section className="fx-chart">
      <header className="fx-chart-head">
        <div className="min-w-0">
          <h3 className="fx-chart-title">{title}</h3>
          {note && <p className="fx-chart-note">{note}</p>}
        </div>
        <Legend series={series} />
      </header>

      <div className="fx-plot" onPointerLeave={() => setHot(null)}>
        <div className="fx-plot-grid" aria-hidden="true">
          {[top, top / 2].map((t) => (
            <span key={t} className="fx-plot-tick" style={{ bottom: `${(t / top) * 100}%` }}>
              <b>{t}</b>
            </span>
          ))}
        </div>
        <div className="fx-plot-cols">
          {points.map((p, i) => {
            const shown = series.filter((s) => p.values[s.id]);
            const h = (totals[i] / top) * 100;
            return (
              <div
                key={p.label + i}
                className="fx-col"
                tabIndex={0}
                role="img"
                aria-label={`${p.title}: ${spoken(series, p.values, unit)}`}
                data-dim={(hot !== null && hot !== i) || undefined}
                style={{ '--h': `${h}%`, '--i': i } as CSSProperties}
                onPointerEnter={() => setHot(i)}
                onFocus={() => setHot(i)}
                onBlur={() => setHot(null)}
              >
                <div className="fx-col-stack">
                  {shown.map((s, n) => (
                    <i key={s.id} data-top={n === shown.length - 1 || undefined} style={{ flexGrow: p.values[s.id], background: s.color }} />
                  ))}
                </div>
                {hot === i && (
                  <Tip
                    title={p.title}
                    series={series}
                    values={p.values}
                    unit={unit}
                    edge={i < 2 ? 'start' : i > points.length - 3 ? 'end' : undefined}
                  />
                )}
              </div>
            );
          })}
        </div>
      </div>
      <div className="fx-plot-axis" aria-hidden="true">
        {points.map((p, i) => (
          <span key={p.label + i}>{i % every === 0 ? p.label : ''}</span>
        ))}
      </div>

      <table className="sr-only">
        <caption>{title}</caption>
        <thead>
          <tr>
            <th scope="col">Lúc</th>
            {series.map((s) => (
              <th key={s.id} scope="col">
                {s.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {points.map((p, i) => (
            <tr key={p.label + i}>
              <th scope="row">{p.title}</th>
              {series.map((s) => (
                <td key={s.id}>{p.values[s.id] ?? 0}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

/** Một thanh ngang xếp chồng, dài theo tổng so với `max`. Chỉ vào thì hiện số của từng nhóm. */
export function StackBar({ title, series, values, max, unit = 'việc' }: { title: string; series: Series[]; values: Values; max: number; unit?: string }) {
  const [on, setOn] = useState(false);
  const total = sum(series, values);
  const shown = series.filter((s) => values[s.id]);
  return (
    <span
      className="fx-hbar"
      tabIndex={0}
      role="img"
      aria-label={`${title}: ${spoken(series, values, unit)}`}
      onPointerEnter={() => setOn(true)}
      onPointerLeave={() => setOn(false)}
      onFocus={() => setOn(true)}
      onBlur={() => setOn(false)}
    >
      <span className="fx-hbar-fill" style={{ flexBasis: `${(total / Math.max(1, max)) * 100}%` }}>
        {shown.map((s, n) => (
          <i key={s.id} data-end={n === shown.length - 1 || undefined} style={{ flexGrow: values[s.id], background: s.color }} />
        ))}
      </span>
      {on && <Tip title={title} series={series} values={values} unit={unit} edge="start" />}
    </span>
  );
}

export interface BarRow {
  id: string;
  label: string;
  values: Values;
  /** phần đứng cuối hàng, ví dụ nhãn "Nhanh" */
  end?: ReactNode;
}

/** Danh sách thanh ngang: mỗi hàng một bàn hay một người, hàng nhiều việc nhất dài nhất */
export function BarList({ title, note, series, rows, unit = 'việc' }: { title: string; note?: ReactNode; series: Series[]; rows: BarRow[]; unit?: string }) {
  const max = Math.max(1, ...rows.map((r) => sum(series, r.values)));
  return (
    <section className="fx-chart">
      <header className="fx-chart-head">
        <div className="min-w-0">
          <h3 className="fx-chart-title">{title}</h3>
          {note && <p className="fx-chart-note">{note}</p>}
        </div>
        <Legend series={series} />
      </header>
      <ul className="fx-barlist">
        {rows.map((r) => (
          <li key={r.id}>
            <span className="fx-barlist-name">{r.label}</span>
            <StackBar title={r.label} series={series} values={r.values} max={max} unit={unit} />
            <b className="fx-barlist-num">{sum(series, r.values)}</b>
            <span className="fx-barlist-end">{r.end}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
