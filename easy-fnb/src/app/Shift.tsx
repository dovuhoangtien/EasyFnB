import { useMemo, useState, type ReactNode } from 'react';
import { BellRing, MessagesSquare, Sparkles, UserPlus, UserX, UtensilsCrossed } from 'lucide-react';
import { Avatar } from '@astryxdesign/core/Avatar';
import { Badge } from '@astryxdesign/core/Badge';
import { Banner } from '@astryxdesign/core/Banner';
import { Button } from '@astryxdesign/core/Button';
import { Card } from '@astryxdesign/core/Card';
import { EmptyState } from '@astryxdesign/core/EmptyState';
import { Markdown } from '@astryxdesign/core/Markdown';
import { Skeleton } from '@astryxdesign/core/Skeleton';
import { Text } from '@astryxdesign/core/Text';
import { writeSummary } from '../live/api';
import { useReport, useRun, useTitle } from '../live/hooks';
import { useLive } from '../live/store';
import { clockTime, ROLE_LABEL, shiftText, SPEED_LABEL, SPEED_VARIANT, verdictOf, type SpeedCounts } from '../live/text';
import { ALERT_KINDS, type Report, type Staff, type TableState } from '../live/types';
import { BarList, KIND_SERIES, SPEED_SERIES, StackBar, TimeColumns, type BarRow, type TimePoint } from './charts';
import { Roll } from './motion';
import { SpeedBar, SpeedMeter } from './SpeedMeter';
import { SectionTitle } from './ui';
import { MoneySection } from './Revenue';

interface Figure {
  label: string;
  value: number;
  note: string;
  icon: ReactNode;
  tone: 'accent' | 'info' | 'warning' | 'error' | 'success';
}

const speedOfShift = (r: Report): SpeedCounts => r.speed ?? { fast: 0, ok: 0, slow: 0, missed: r.no_arrival ?? 0 };
const hhmm = (t: number) => clockTime(t).slice(0, 5);

/** Bốn con số đầu trang: khách vào, khách gọi, bàn cần dọn, và việc bị bỏ lỡ */
function figures(r: Report): Figure[] {
  const missed = r.no_arrival ?? 0;
  return [
    { label: 'Khách mới', value: r.counts.new_guest ?? 0, note: 'lượt khách vào bàn', icon: <UserPlus size={16} aria-hidden="true" />, tone: 'info' },
    { label: 'Khách gọi phục vụ', value: r.counts.call ?? 0, note: 'lần khách giơ tay gọi', icon: <BellRing size={16} aria-hidden="true" />, tone: 'accent' },
    {
      label: 'Bàn cần dọn',
      value: r.counts.needs_clearing ?? 0,
      note: 'lần khách về, bàn còn bẩn',
      icon: <UtensilsCrossed size={16} aria-hidden="true" />,
      tone: 'warning',
    },
    {
      label: 'Việc không ai tới',
      value: missed,
      note: missed ? 'khách gọi mà không thấy nhân viên tới bàn' : 'việc nào cũng có người tới',
      icon: <UserX size={16} aria-hidden="true" />,
      tone: missed ? 'error' : 'success',
    },
  ];
}

/** Độ dài một cột của biểu đồ theo giờ, nói bằng chữ */
const stepText = (s: number) => (s >= 3600 ? `${s / 3600} giờ` : `${s / 60} phút`);

/** Việc của ca theo từng quãng giờ, chia theo loại việc và theo mức tốc độ */
function timePoints(r: Report): { points: TimePoint[]; busy: string; slow: string } | null {
  const tl = r.timeline;
  if (!tl || !tl.points.length) return null;
  type P = (typeof tl.points)[number];
  const load = (p: P) => p.new_guest + p.call + p.needs_clearing;
  const late = (p: P) => p.slow + p.missed;
  const peak = tl.points.reduce((a, b) => (load(b) > load(a) ? b : a));
  const worst = tl.points.reduce((a, b) => (late(b) > late(a) ? b : a));
  return {
    points: tl.points.map((p) => ({
      label: hhmm(p.t),
      title: `${hhmm(p.t)} đến ${hhmm(p.t + tl.step_s * 1000)}`,
      values: { ...p },
    })),
    busy: `Mỗi cột ${stepText(tl.step_s)}. Đông nhất lúc ${hhmm(peak.t)}, có ${load(peak)} việc.`,
    slow: late(worst) ? `Chậm nhất lúc ${hhmm(worst.t)}: ${late(worst)} việc khách phải chờ lâu.` : 'Không lúc nào khách phải chờ lâu.',
  };
}

/** Mỗi bàn một thanh: bàn nhiều việc nhất đứng trên, cuối hàng là nhận xét bàn đó được phục vụ nhanh hay chậm */
function tableRows(r: Report): BarRow[] {
  return r.per_table
    .map((t) => {
      const v = verdictOf({ fast: t.fast ?? 0, ok: t.ok ?? 0, slow: t.slow ?? 0, missed: t.missed ?? 0 });
      return {
        id: t.table,
        label: `Bàn ${t.table}`,
        total: t.guests + t.calls + t.clearings,
        values: { new_guest: t.guests, call: t.calls, needs_clearing: t.clearings },
        end: v ? <Badge variant={SPEED_VARIANT[v]} label={SPEED_LABEL[v]} /> : null,
      };
    })
    .filter((t) => t.total > 0)
    .sort((a, b) => b.total - a.total);
}

/** Câu nói quán đang có khách ở mấy bàn, theo camera lúc này */
function seatedText(tables: TableState[]): string | undefined {
  if (!tables.length) return undefined;
  const busy = tables.filter((t) => t.state === 'occupied');
  const people = busy.reduce((n, t) => n + t.people, 0);
  return busy.length ? `Lúc này ${busy.length} trên ${tables.length} bàn có khách, khoảng ${people} người.` : `Lúc này cả ${tables.length} bàn đều trống.`;
}

interface Row {
  id: string;
  name: string;
  role: string;
  done: number;
  acked: number;
  kinds: Record<string, number | undefined>;
  speed: SpeedCounts;
  since: string;
  worked: string;
}

/** Người đã vào ca hoặc đã nhận việc; ai làm xong nhiều việc đứng trước */
function staffRows(r: Report, staff: Staff[]): { rows: Row[]; idle: string[] } {
  const now = r.to;
  const rows: Row[] = [];
  const idle: string[] = [];
  for (const p of r.per_staff) {
    const s = staff.find((x) => x.id === p.id);
    if (!p.acked && !p.done && !s?.first_in) {
      idle.push(p.name);
      continue;
    }
    rows.push({
      id: p.id,
      name: p.name,
      role: s ? ROLE_LABEL[s.role] : '',
      done: p.done,
      acked: p.acked,
      kinds: p.kinds ?? {},
      speed: { fast: p.fast ?? 0, ok: p.ok ?? 0, slow: p.slow ?? 0, missed: 0 },
      since: s?.first_in ? hhmm(s.first_in) : 'chưa vào',
      worked: s?.first_in ? shiftText((s.on_since ? Math.max(0, now - s.on_since) : 0) + (s.worked_s ?? 0) * 1000) : '',
    });
  }
  rows.sort((a, b) => b.acked - a.acked || b.done - a.done);
  return { rows, idle };
}

function StaffTable({ rows }: { rows: Row[] }) {
  const most = Math.max(1, ...rows.map((p) => p.acked));
  return (
    <div className="fx-staff-wrap">
      <table className="fx-staff">
        <thead>
          <tr>
            <th scope="col">Nhân viên</th>
            <th scope="col">Việc đã nhận</th>
            <th scope="col">Tốc độ nhận việc</th>
            <th scope="col" className="fx-staff-wide">
              Việc đã xong
            </th>
            <th scope="col" className="fx-staff-wide">
              Vào ca
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((p) => {
            const v = verdictOf(p.speed);
            return (
              <tr key={p.id}>
                <th scope="row">
                  <span className="flex items-center gap-3">
                    <Avatar name={p.name} size="md" tooltip={false} />
                    <span className="min-w-0">
                      <Text type="label" weight="semibold" as="p">
                        {p.name}
                      </Text>
                      <Text type="supporting" color="secondary" as="p">
                        {p.role}
                      </Text>
                    </span>
                  </span>
                </th>
                <td>
                  <span className="fx-staff-load">
                    <span className="fx-staff-num">{p.acked}</span>
                    <StackBar title={`${p.name} đã nhận`} series={KIND_SERIES} values={p.kinds} max={most} />
                  </span>
                </td>
                <td>
                  {v ? (
                    <span className="fx-staff-speed">
                      <Badge variant={SPEED_VARIANT[v]} label={SPEED_LABEL[v]} />
                      <SpeedBar
                        speed={p.speed}
                        label={`${p.speed.fast} việc nhận nhanh, ${p.speed.ok} hơi chậm, ${p.speed.slow} chậm`}
                      />
                    </span>
                  ) : (
                    <Text type="supporting" color="secondary">
                      Chưa nhận việc nào
                    </Text>
                  )}
                </td>
                <td className="fx-staff-wide fx-staff-time">{p.done}</td>
                <td className="fx-staff-wide fx-staff-time">
                  {p.since}
                  {p.worked && `, đã làm ${p.worked}`}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/** Tổng kết ca: tốc độ phục vụ bằng chữ và màu, ca bận cỡ nào, ai làm ra sao. Chi tiết thì hỏi trợ lý. */
export default function Shift() {
  useTitle('Ca hôm nay, Easy FnB');
  const { report, error, loading } = useReport();
  const staff = useLive((s) => s.staff);
  const tables = useLive((s) => s.tables);
  const provider = useLive((s) => s.settings?.provider ?? 'Gemini');
  const aiOn = useLive((s) => !!s.settings?.gemini);
  const { busy, run } = useRun();
  const [summary, setSummary] = useState<string | null>(null);
  const nums = useMemo(() => (report ? figures(report) : []), [report]);
  const people = useMemo(() => (report ? staffRows(report, staff) : { rows: [], idle: [] }), [report, staff]);
  const time = useMemo(() => (report ? timePoints(report) : null), [report]);
  const byTable = useMemo(() => (report ? tableRows(report) : []), [report]);
  const total = report ? ALERT_KINDS.reduce((n, k) => n + (report.counts[k] ?? 0), 0) : 0;
  const hasData = !!report && (total > 0 || people.rows.length > 0);

  const write = async () => {
    const out = await run('summary', () => writeSummary());
    if (out) setSummary(out.text);
  };

  return (
    <div className="fx-page" style={{ maxWidth: 1180 }}>
      <header className="fx-head">
        <div className="min-w-0">
          <h1>Ca hôm nay</h1>
          <p className="fx-head-sub">
            {report ? `Từ ${hhmm(report.from)} đến ${hhmm(report.to)}${report.cancelled ? `, đã bỏ ${report.cancelled} lần báo nhầm` : ''}` : 'Đang lấy số liệu của ca.'}
          </p>
        </div>
        {hasData && <Button label="Hỏi trợ lý về ca này" variant="secondary" icon={<MessagesSquare size={15} />} href="/tro-ly" />}
      </header>

      {error && <Banner status="error" title="Chưa lấy được số liệu ca" description={error} collapsible={false} />}
      {loading && (
        <div className="flex flex-col gap-3">
          <Skeleton height={200} />
          <Skeleton height={180} />
        </div>
      )}

      <MoneySection />

      {report && !hasData ? (
        <Card padding={5}>
          <EmptyState title="Ca chưa có việc nào" description="Khi camera ghi nhận khách gọi, khách mới hay bàn cần dọn, số liệu của ca sẽ hiện ở đây." />
        </Card>
      ) : null}

      {report && hasData && (
        <>
          <div className="fx-strip">
            {nums.map((f) => (
              <div key={f.label} className="fx-strip-cell">
                <span className="flex items-center gap-2">
                  <span className="fx-ico" data-tone={f.tone}>
                    {f.icon}
                  </span>
                  <Text type="supporting" color="secondary">
                    {f.label}
                  </Text>
                </span>
                <span className="fx-strip-value" data-tone={f.tone === 'error' ? 'bad' : undefined}>
                  <Roll value={f.value} />
                </span>
                <Text type="supporting" color="secondary">
                  {f.note}
                </Text>
              </div>
            ))}
          </div>

          <SectionTitle>Khách</SectionTitle>
          <div className="fx-shift-grid">
            {time && <TimeColumns title="Việc khách cần theo giờ" note={time.busy} series={KIND_SERIES} points={time.points} />}
            {byTable.length > 0 && <BarList title="Bàn nào cần phục vụ nhiều" note={seatedText(tables)} series={KIND_SERIES} rows={byTable} />}
          </div>

          <SectionTitle>Nhân viên</SectionTitle>
          <div className="fx-shift-grid" data-lead="end">
            <SpeedMeter speed={speedOfShift(report)} />
            {time && <TimeColumns title="Tốc độ phục vụ theo giờ" note={time.slow} series={SPEED_SERIES} points={time.points} />}
          </div>

          {people.rows.length > 0 && <StaffTable rows={people.rows} />}
          {people.idle.length > 0 && (
            <Text type="supporting" color="secondary" as="p">
              Chưa vào ca: {people.idle.join(', ')}
            </Text>
          )}

          {aiOn && (
            <Card padding={4}>
              <div className="flex flex-col gap-3">
                <SectionTitle
                  end={
                    <Button
                      label={summary ? 'Viết lại' : 'Viết tóm tắt'}
                      variant={summary ? 'secondary' : 'primary'}
                      size="sm"
                      icon={<Sparkles size={15} />}
                      isLoading={busy === 'summary'}
                      onClick={() => void write()}
                    />
                  }
                >
                  Tóm tắt ca
                </SectionTitle>
                {summary ? (
                  <Markdown density="compact">{summary}</Markdown>
                ) : (
                  <Text type="body" color="secondary" as="p">
                    {provider} đọc số liệu của ca và viết vài dòng nhận xét để gửi cho chủ quán.
                  </Text>
                )}
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
