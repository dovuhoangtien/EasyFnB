import { useMemo, useState, type ReactNode } from 'react';
import { MessagesSquare, ReceiptText, Sparkles, UserX } from 'lucide-react';
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
import { clockTime, KIND_LABEL, ROLE_LABEL, SPEED_LABEL, SPEED_VARIANT, verdictOf, type SpeedCounts } from '../live/text';
import { ALERT_KINDS, type Report, type Staff } from '../live/types';
import { Roll } from './motion';
import { SpeedBar, SpeedMeter } from './SpeedMeter';
import { SectionTitle } from './ui';

interface Figure {
  label: string;
  value: number;
  note: string;
  icon: ReactNode;
  tone: 'accent' | 'error' | 'success';
}

const speedOfShift = (r: Report): SpeedCounts => r.speed ?? { fast: 0, ok: 0, slow: 0, missed: r.no_arrival ?? 0 };

/** Hai con số đi kèm thước đo tốc độ: ca bận cỡ nào, có việc nào bị bỏ lỡ */
function figures(r: Report): Figure[] {
  const total = ALERT_KINDS.reduce((n, k) => n + (r.counts[k] ?? 0), 0);
  const kinds = ALERT_KINDS.filter((k) => r.counts[k]).map((k) => `${r.counts[k]} ${KIND_LABEL[k].toLowerCase()}`);
  if (r.cancelled) kinds.push(`${r.cancelled} báo nhầm`);
  const missed = r.no_arrival ?? 0;
  return [
    { label: 'Việc trong ca', value: total, note: kinds.join(', ') || 'chưa có việc nào', icon: <ReceiptText size={16} aria-hidden="true" />, tone: 'accent' },
    {
      label: 'Việc không ai tới',
      value: missed,
      note: missed ? 'khách gọi mà không thấy nhân viên tới bàn' : 'việc nào cũng có người tới',
      icon: <UserX size={16} aria-hidden="true" />,
      tone: missed ? 'error' : 'success',
    },
  ];
}

interface Row {
  id: string;
  name: string;
  role: string;
  done: number;
  acked: number;
  speed: SpeedCounts;
  since: string;
}

/** Người đã vào ca hoặc đã nhận việc; ai làm xong nhiều việc đứng trước */
function staffRows(r: Report, staff: Staff[]): { rows: Row[]; idle: string[] } {
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
      speed: { fast: p.fast ?? 0, ok: p.ok ?? 0, slow: p.slow ?? 0, missed: 0 },
      since: s?.first_in ? clockTime(s.first_in).slice(0, 5) : 'chưa vào',
    });
  }
  rows.sort((a, b) => b.done - a.done);
  return { rows, idle };
}

function StaffTable({ rows }: { rows: Row[] }) {
  return (
    <div className="fx-staff-wrap">
      <table className="fx-staff">
        <thead>
          <tr>
            <th scope="col">Nhân viên</th>
            <th scope="col">Việc đã xong</th>
            <th scope="col">Tốc độ nhận việc</th>
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
                <td className="fx-staff-num">{p.done}</td>
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
                <td className="fx-staff-wide fx-staff-time">{p.since}</td>
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
  const provider = useLive((s) => s.settings?.provider ?? 'Gemini');
  const aiOn = useLive((s) => !!s.settings?.gemini);
  const { busy, run } = useRun();
  const [summary, setSummary] = useState<string | null>(null);
  const nums = useMemo(() => (report ? figures(report) : []), [report]);
  const people = useMemo(() => (report ? staffRows(report, staff) : { rows: [], idle: [] }), [report, staff]);
  const total = report ? ALERT_KINDS.reduce((n, k) => n + (report.counts[k] ?? 0), 0) : 0;
  const hasData = !!report && (total > 0 || people.rows.length > 0);

  const write = async () => {
    const out = await run('summary', () => writeSummary());
    if (out) setSummary(out.text);
  };

  return (
    <div className="fx-page" style={{ maxWidth: 960 }}>
      <header className="fx-head">
        <div className="min-w-0">
          <h1>Ca hôm nay</h1>
          <p className="fx-head-sub">
            {report ? `Từ ${clockTime(report.from).slice(0, 5)} đến ${clockTime(report.to).slice(0, 5)}` : 'Đang lấy số liệu của ca.'}
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

      {report && !hasData ? (
        <Card padding={5}>
          <EmptyState title="Ca chưa có việc nào" description="Khi camera ghi nhận khách gọi, khách mới hay bàn cần dọn, số liệu của ca sẽ hiện ở đây." />
        </Card>
      ) : null}

      {report && hasData && (
        <>
          <div className="fx-shift-top">
            <SpeedMeter speed={speedOfShift(report)} />
            <div className="fx-strip" data-cols="1">
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
