import type { CSSProperties } from 'react';
import { Avatar } from '@astryxdesign/core/Avatar';
import { Badge } from '@astryxdesign/core/Badge';
import { StatusDot } from '@astryxdesign/core/StatusDot';
import { Table } from '@astryxdesign/core/Table';
import { Text } from '@astryxdesign/core/Text';
import { apiUrl } from '../live/api';
import { clockTime, shiftText, KIND_LABEL, ROLE_LABEL, SPEED_LABEL, speedOf, tableText } from '../live/text';

const WAIT_NOTE = { fast: 'chờ ngắn', ok: 'chờ hơi lâu', slow: 'chờ lâu' } as const;
const speedWord = (s: number | null | undefined) => {
  const k = speedOf(s);
  return k ? SPEED_LABEL[k] : 'chưa có';
};
import type { Block, ChartBlock, EventsBlock, StaffBlock, StatsBlock, TableBlock } from '../live/types';
import { Flipbook, KindBadge, Shot, toneColor } from './ui';

const NUM = new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 1 });

function BlockTitle({ children }: { children: string | null }) {
  if (!children) return null;
  return (
    <Text type="label" weight="semibold" as="h3">
      {children}
    </Text>
  );
}

// ---------- số liệu ----------
function Stats({ b }: { b: StatsBlock }) {
  return (
    <div className="flex flex-col gap-3">
      <BlockTitle>{b.title}</BlockTitle>
      <div className="fx-stat-row">
        {b.items.map((it) => (
          <div key={it.label} className="fx-stat-tile">
            <Text type="supporting" color="secondary">
              {it.label}
            </Text>
            <span className="fx-stat-value" style={{ color: toneColor(it.tone) }}>
              {it.value}
            </span>
            {it.note && (
              <Text type="supporting" color="secondary">
                {it.note}
              </Text>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------- biểu đồ ----------
function Chart({ b }: { b: ChartBlock }) {
  // phần trăm thì thanh chạy trên thang 100 và viết liền số: 80%
  const pct = b.unit === '%';
  const max = pct ? 100 : Math.max(1, ...b.points.map((p) => p.value));
  const unit = pct ? '%' : b.unit ? ` ${b.unit}` : '';
  const summary = `${b.title}: ${b.points.map((p) => `${p.label} ${NUM.format(p.value)}${unit}`).join(', ')}`;

  if (!b.points.length) {
    return (
      <div className="fx-block">
        <BlockTitle>{b.title}</BlockTitle>
        <Text type="supporting" color="secondary">
          Chưa có số liệu để vẽ.
        </Text>
      </div>
    );
  }

  if (b.kind === 'bar') {
    return (
      <div className="fx-block">
        <BlockTitle>{b.title}</BlockTitle>
        <div className="fx-ch-bar" role="img" aria-label={summary}>
          {b.points.map((p, i) => (
            <div key={p.label} className="contents">
              <span>{p.label}</span>
              <span className="fx-ch-bar-track">
                <span className="fx-ch-bar-fill block" style={{ width: `${(p.value / max) * 100}%`, '--i': Math.min(i, 8) } as CSSProperties} />
              </span>
              <span className="fx-ch-num">
                {NUM.format(p.value)}
                {unit}
                {p.note ? <span className="font-normal text-secondary">, {p.note}</span> : null}
              </span>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (b.kind === 'line' && b.points.length > 1) {
    const W = 600;
    const H = 160;
    const pad = 8;
    const step = (W - pad * 2) / (b.points.length - 1);
    const xy = b.points.map((p, i) => [pad + i * step, H - pad - (p.value / max) * (H - pad * 2 - 12)] as const);
    const line = xy.map((p) => p.join(',')).join(' ');
    return (
      <div className="fx-block">
        <div className="flex items-baseline justify-between gap-3">
          <BlockTitle>{b.title}</BlockTitle>
          <Text type="supporting" color="secondary">
            Cao nhất {NUM.format(max)}
            {unit}
          </Text>
        </div>
        <svg className="fx-ch-line" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" role="img" aria-label={summary}>
          <line x1={0} x2={W} y1={H - pad} y2={H - pad} vectorEffect="non-scaling-stroke" />
          <polygon className="fx-ch-area" points={`${pad},${H - pad} ${line} ${W - pad},${H - pad}`} />
          <polyline points={line} pathLength={1} vectorEffect="non-scaling-stroke" />
        </svg>
        <div className="fx-ch-axis">
          {b.points.map((p) => (
            <span key={p.label}>{p.label}</span>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="fx-block">
      <BlockTitle>{b.title}</BlockTitle>
      <div className="fx-ch-col" role="img" aria-label={summary}>
        {b.points.map((p, i) => (
          <div key={p.label} className="fx-ch-col-item" title={p.note ?? undefined}>
            <div className="fx-ch-col-fill" style={{ height: `${(p.value / max) * 100}%`, '--i': Math.min(i, 16) } as CSSProperties}>
              <span className="fx-ch-col-val">{NUM.format(p.value)}</span>
            </div>
          </div>
        ))}
      </div>
      <div className="fx-ch-axis">
        {b.points.map((p) => (
          <span key={p.label}>{p.label}</span>
        ))}
      </div>
      {b.unit && !pct && (
        <Text type="supporting" color="secondary">
          Đơn vị: {b.unit}
        </Text>
      )}
    </div>
  );
}

// ---------- sự kiện kèm hình ----------
const STATUS_TEXT: Record<string, string> = {
  verifying: 'đang kiểm tra',
  open: 'chưa ai nhận',
  acked: 'đang xử lý',
  done: 'đã xong',
  cancelled: 'đã huỷ',
};

function Events({ b }: { b: EventsBlock }) {
  return (
    <div className="fx-block">
      <BlockTitle>{b.title}</BlockTitle>
      <div>
        {b.items.map((e) => {
          const what = `${KIND_LABEL[e.kind] ?? e.kind}, ${tableText(e.table)}`;
          const crop = e.crop_url ? [{ src: apiUrl(e.crop_url), alt: `Ảnh camera: ${what}` }] : [];
          const hasMedia = !!(e.strip_url || e.crop_url);
          return (
            <div key={e.alert_id} className="fx-ev" data-media={hasMedia || undefined}>
              {e.strip_url ? (
                <Flipbook src={apiUrl(e.strip_url)} alt={what} fallback={<Shot media={crop} size="fill" className="aspect-video w-full" />} />
              ) : e.crop_url ? (
                <Shot media={crop} size="fill" className="aspect-video w-full" />
              ) : null}
              <div className="min-w-0 flex flex-col gap-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <Text type="label" weight="semibold" hasTabularNumbers>
                    {clockTime(e.t)}
                  </Text>
                  {KIND_LABEL[e.kind] ? <KindBadge kind={e.kind} /> : <Badge label={e.kind} />}
                  <Text type="label">{tableText(e.table)}</Text>
                </div>
                <Text type="body" as="p">
                  {e.text}
                </Text>
                <Text type="supporting" color="secondary" as="p">
                  {[
                    STATUS_TEXT[e.status] ?? e.status,
                    e.wait_s != null ? WAIT_NOTE[speedOf(e.wait_s) ?? 'fast'] : null,
                    e.staff ? `người xử lý: ${e.staff}` : null,
                  ]
                    .filter(Boolean)
                    .join(', ')}
                </Text>
              </div>
            </div>
          );
        })}
        {!b.items.length && (
          <Text type="supporting" color="secondary">
            Không có sự kiện nào khớp.
          </Text>
        )}
      </div>
    </div>
  );
}

// ---------- bảng ----------
function DataTable({ b }: { b: TableBlock }) {
  const data = b.rows.map((r, i) => {
    const row: Record<string, unknown> = { id: String(i) };
    r.forEach((v, j) => {
      row[`c${j}`] = v;
    });
    return row;
  });
  return (
    <div className="fx-block">
      <BlockTitle>{b.title}</BlockTitle>
      <Table data={data} idKey="id" density="compact" columns={b.columns.map((c, j) => ({ key: `c${j}`, header: c }))} />
    </div>
  );
}

// ---------- nhân viên ----------
function StaffCards({ b }: { b: StaffBlock }) {
  return (
    <div className="fx-block">
      <BlockTitle>{b.title}</BlockTitle>
      <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))' }}>
        {b.items.map((s) => (
          <div key={s.id} className="flex flex-col gap-3 rounded-[var(--radius-element)] border border-border p-3">
            <div className="flex items-center gap-3">
              <Avatar name={s.name} size="md" tooltip={false} />
              <div className="min-w-0 flex-1">
                <Text type="label" weight="semibold" as="p">
                  {s.name}
                </Text>
                <Text type="supporting" color="secondary" as="p">
                  {(ROLE_LABEL as Record<string, string>)[s.role] ?? s.role}
                </Text>
              </div>
              <StatusDot variant={s.online ? 'success' : 'neutral'} label={s.online ? 'Đang trong ca' : 'Không mở app'} tooltip={s.online ? 'Đang trong ca' : 'Không mở app'} />
            </div>
            <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-[length:var(--text-supporting-size)]">
              <dt className="text-secondary">Vào ca</dt>
              <dd className="text-right tabular-nums">{s.first_in ? clockTime(s.first_in).slice(0, 5) : 'chưa vào'}</dd>
              <dt className="text-secondary">Đã làm</dt>
              <dd className="text-right tabular-nums">{s.worked_s > 0 ? shiftText(s.worked_s * 1000) : 'chưa có'}</dd>
              <dt className="text-secondary">Việc đã xong</dt>
              <dd className="text-right tabular-nums">
                {s.done} / {s.acked} đã nhận
              </dd>
              <dt className="text-secondary">Tốc độ nhận việc</dt>
              <dd className="text-right">{speedWord(s.mean_response_s)}</dd>
            </dl>
          </div>
        ))}
      </div>
    </div>
  );
}

/** Vẽ các khối trả lời của trợ lý; khối lạ thì bỏ qua thay vì làm vỡ trang */
export function Blocks({ blocks }: { blocks: Block[] }) {
  return (
    <div className="fx-blocks">
      {blocks.map((b, i) => {
        switch (b.type) {
          case 'stats':
            return <Stats key={i} b={b} />;
          case 'chart':
            return <Chart key={i} b={b} />;
          case 'events':
            return <Events key={i} b={b} />;
          case 'table':
            return <DataTable key={i} b={b} />;
          case 'staff':
            return <StaffCards key={i} b={b} />;
          default:
            return null;
        }
      })}
    </div>
  );
}
