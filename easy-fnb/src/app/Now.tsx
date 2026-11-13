import { useMemo, useState, type CSSProperties, type ReactNode } from 'react';
import { BellRing, BrushCleaning, Check, Plus, TriangleAlert, UserCheck, Users, Video, X } from 'lucide-react';
import { Avatar } from '@astryxdesign/core/Avatar';
import { Badge } from '@astryxdesign/core/Badge';
import { Banner } from '@astryxdesign/core/Banner';
import { Button } from '@astryxdesign/core/Button';
import { Card } from '@astryxdesign/core/Card';
import { Dialog, DialogHeader } from '@astryxdesign/core/Dialog';
import { DropdownMenu } from '@astryxdesign/core/DropdownMenu';
import { EmptyState } from '@astryxdesign/core/EmptyState';
import { SegmentedControl, SegmentedControlItem } from '@astryxdesign/core/SegmentedControl';
import { Selector } from '@astryxdesign/core/Selector';
import { Skeleton } from '@astryxdesign/core/Skeleton';
import { Text } from '@astryxdesign/core/Text';
import { assignAlert, cancelAlert, createAlert, doneAlert } from '../live/api';
import { useReport, useRun, useTitle } from '../live/hooks';
import { LiveCamera } from '../live/LiveCamera';
import { live, useLive, useServerNow } from '../live/store';
import { ageText, shiftText, byName, byUrgency, cameraLive, clockTime, isActive, isClosed, KIND_LABEL, ROLE_LABEL, statusText, TABLE_STATE_LABEL, tableText, waitWord } from '../live/text';
import { ALERT_KINDS, type Alert, type AlertKind, type Staff } from '../live/types';
import { AnimatedList, Roll } from './motion';
import { SpeedMeter } from './SpeedMeter';
import { alertMedia, KindBadge, SectionTitle, Shot } from './ui';

/** Chỉ hạ chữ đầu, để tên người (Lan, Tú) giữ chữ hoa */
const lowerFirst = (t: string) => t.charAt(0).toLowerCase() + t.slice(1);
/** Việc vừa tới trong khoảng này thì thẻ sáng lên một nhịp */
const FRESH_MS = 4000;
const DAY = new Intl.DateTimeFormat('vi-VN', { weekday: 'long', day: 'numeric', month: 'long' });

// ---------- một việc đang mở ----------
function TaskCard({ a, staff, now, provider, escalateS }: { a: Alert; staff: Staff[]; now: number; provider: string; escalateS: number }) {
  const { busy, run } = useRun();
  const act = async (key: string, fn: () => Promise<Alert>, ok?: string) => {
    const out = await run(`${key}-${a.id}`, fn, ok);
    if (out) live.upsertAlert(out);
  };
  const waiting = now - a.created_at;
  const urgent = a.escalated || (a.kind === 'call' && a.status === 'open' && waiting > 60_000);
  const wait = waitWord(waiting, a.status === 'acked');
  const others = staff.filter((s) => s.id !== a.assigned_to);
  // thanh chờ: chạy dần tới lúc máy chủ nhắc lại hoặc chuyển người
  const limit = escalateS > 0 && a.status === 'open' ? escalateS * 1000 : 0;
  const p = limit ? Math.min(1, waiting / limit) : 0;
  const level = a.status === 'acked' ? undefined : (limit ? p >= 1 : waiting > 120_000) ? 'late' : (limit ? p > 0.6 : waiting > 60_000) ? 'warn' : undefined;

  return (
    <article className="fx-task" data-kind={a.kind} data-fresh={waiting < FRESH_MS || undefined} data-urgent={urgent || undefined} aria-label={`${KIND_LABEL[a.kind]}, ${tableText(a.table)}`}>
      <Shot media={alertMedia(a)} size={72} />
      <div className="min-w-0 flex-1 flex flex-col gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          <KindBadge kind={a.kind} />
          {a.escalated && <Badge variant="error" label="Gấp" icon={<TriangleAlert size={12} aria-hidden="true" />} />}
          {a.verify.state === 'pending' && <Badge variant="neutral" label={`${provider} đang kiểm tra`} />}
          {a.verify.state === 'confirmed' && <Badge variant="success" label={`${provider} xác nhận`} icon={<Check size={12} aria-hidden="true" />} />}
          <span className="fx-age ml-auto" data-level={wait.level} title={`Báo cách đây ${ageText(waiting)}`}>
            {wait.label}
          </span>
        </div>
        <div>
          <Text type="large" weight="semibold" as="p">
            {tableText(a.table)}
          </Text>
          <Text type="supporting" color="secondary" as="p">
            {statusText(a, staff, provider)}
          </Text>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <Button label="Xong" size="sm" variant="primary" isLoading={busy === `done-${a.id}`} onClick={() => void act('done', () => doneAlert(a.id, 'manager'))} />
          {others.length > 0 && a.status !== 'verifying' && (
            <DropdownMenu
              button={{ label: a.assigned_to ? 'Chuyển người' : 'Giao việc', size: 'sm', variant: 'secondary' }}
              items={others.map((s) => ({
                label: s.name,
                description: `${ROLE_LABEL[s.role]}${s.online ? '' : ', chưa mở app'}`,
                onClick: () => void act('assign', () => assignAlert(a.id, s.id), `Đã giao ${tableText(a.table)} cho ${s.name}`),
              }))}
            />
          )}
          <Button label="Báo nhầm" size="sm" variant="ghost" isLoading={busy === `cancel-${a.id}`} onClick={() => void act('cancel', () => cancelAlert(a.id, 'manager', 'báo nhầm'))} />
        </div>
      </div>
      {limit > 0 && (
        <span className="fx-wait" data-level={level} aria-hidden="true">
          <i style={{ '--p': p } as CSSProperties} />
        </span>
      )}
    </article>
  );
}

// ---------- tạo việc bằng tay ----------
function CreateTask({ onClose, camera }: { onClose: () => void; camera: string }) {
  const zones = useLive((s) => s.zones);
  const { busy, run } = useRun();
  const [kind, setKind] = useState<AlertKind>('call');
  const [table, setTable] = useState('');
  const names = useMemo(() => [...new Set(zones.flatMap((z) => z.tables.map((t) => t.id)))].sort(byName), [zones]);

  const submit = async () => {
    const t = table || null;
    const cam = (t && zones.find((z) => z.tables.some((x) => x.id === t))?.camera) || camera;
    const out = await run('create', () => createAlert(kind, t, cam), `Đã tạo việc ${KIND_LABEL[kind].toLowerCase()}${t ? ` cho bàn ${t}` : ''}`);
    if (out) {
      live.upsertAlert(out);
      onClose();
    }
  };

  return (
    <>
      <DialogHeader title="Tạo việc" subtitle="Việc tạo tay không qua AI, báo ngay cho nhân viên." onOpenChange={onClose} />
      <div className="flex flex-col gap-4" style={{ paddingInline: 16, paddingBottom: 8 }}>
        <SegmentedControl label="Loại việc" value={kind} onChange={(v) => setKind(v as AlertKind)} layout="fill">
          {ALERT_KINDS.map((k) => (
            <SegmentedControlItem key={k} value={k} label={KIND_LABEL[k]} />
          ))}
        </SegmentedControl>
        <Selector
          label="Bàn"
          placeholder={names.length ? 'Chọn bàn' : 'Chưa vẽ bàn nào'}
          options={names.map((n) => ({ value: n, label: `Bàn ${n}` }))}
          value={table}
          onChange={(v) => setTable(v ?? '')}
          hasClear
          width="100%"
        />
        <div className="flex justify-end gap-2">
          <Button label="Huỷ" variant="ghost" onClick={onClose} />
          <Button label="Tạo việc" variant="primary" isLoading={busy === 'create'} onClick={() => void submit()} />
        </div>
      </div>
    </>
  );
}

type IconTone = 'accent' | 'info' | 'warning' | 'success' | 'error';

function StripCell({
  label,
  value,
  note,
  tone,
  ready,
  icon,
  iconTone,
}: {
  label: string;
  value: ReactNode;
  note: string;
  tone?: 'warn' | 'bad';
  ready: boolean;
  icon: ReactNode;
  iconTone: IconTone;
}) {
  return (
    <div className="fx-strip-cell">
      <span className="flex items-center gap-2">
        <span className="fx-ico" data-tone={iconTone}>
          {icon}
        </span>
        <Text type="supporting" color="secondary">
          {label}
        </Text>
      </span>
      <span className="fx-strip-value" data-tone={tone}>
        {ready ? value : <Skeleton width={56} height={30} />}
      </span>
      <Text type="supporting" color="secondary" maxLines={1}>
        {ready ? note : 'Đang tải'}
      </Text>
    </div>
  );
}

function Clock({ now }: { now: number }) {
  const [hh, mm] = clockTime(now).split(':');
  return (
    <div className="flex flex-col items-end gap-1">
      <span className="fx-clock" aria-label={`Bây giờ là ${hh} giờ ${mm}`}>
        {hh}
        <span className="fx-clock-colon">:</span>
        {mm}
      </span>
      <Text type="supporting" color="secondary">
        {DAY.format(now)}
      </Text>
    </div>
  );
}

function attendance(s: Staff, now: number) {
  if (s.on_since) return `Trong ca ${shiftText(now - s.on_since + (s.worked_s ?? 0) * 1000)}`;
  if (s.first_in) return `Đã ra, làm ${shiftText((s.worked_s ?? 0) * 1000)}`;
  return 'Chưa vào ca';
}

/** Màn hình chính của chủ quán: camera, bàn, việc đang chờ và nhân viên trong một trang */
export default function Now() {
  useTitle('Quán lúc này, Easy FnB');
  const status = useLive((s) => s.status);
  const loaded = useLive((s) => s.loaded);
  const error = useLive((s) => s.error);
  const cameras = useLive((s) => s.cameras);
  const zones = useLive((s) => s.zones);
  const tables = useLive((s) => s.tables);
  const alerts = useLive((s) => s.alerts);
  const staff = useLive((s) => s.staff);
  const settings = useLive((s) => s.settings);
  const now = useServerNow();
  const provider = settings?.provider ?? 'Gemini';

  const [camId, setCamId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const camera = cameras.find((c) => c.id === camId) ?? cameras.find((c) => cameraLive(c, now)) ?? cameras[0];

  const active = useMemo(() => alerts.filter(isActive).sort(byUrgency), [alerts]);
  const closed = useMemo(
    () =>
      alerts
        .filter(isClosed)
        .sort((a, b) => (b.done_at ?? b.cancelled_at ?? b.created_at) - (a.done_at ?? a.cancelled_at ?? a.created_at))
        .slice(0, 4),
    [alerts],
  );
  const calling = useMemo(() => new Set(active.filter((a) => a.kind === 'call' && a.table).map((a) => a.table as string)), [active]);

  const tableNames = useMemo(() => [...new Set([...zones.flatMap((z) => z.tables.map((t) => t.id)), ...tables.map((t) => t.id)])].sort(byName), [zones, tables]);
  const stateOf = (id: string) => tables.find((t) => t.id === id);
  const occupied = tables.filter((t) => t.state === 'occupied').length;
  const dirty = tables.filter((t) => t.state === 'needs_clearing').length;
  const online = staff.filter((s) => s.online).length;
  // việc chưa ai nhận mới là việc khách đang phải chờ
  const waitingOn = active.filter((a) => a.status !== 'acked');
  const oldest = waitingOn.length ? Math.max(...waitingOn.map((a) => now - a.created_at)) : 0;
  const wait = waitWord(oldest, false).level;
  const { report } = useReport();
  const speed = report?.speed && report.speed.fast + report.speed.ok + report.speed.slow + report.speed.missed > 0 ? report.speed : null;
  const camOn = cameras.some((c) => cameraLive(c, now));
  const callers = [...calling].sort(byName);
  const headline = !loaded
    ? status === 'offline'
      ? 'Chưa kết nối được máy chủ'
      : 'Đang kết nối tới quán…'
    : callers.length === 1
      ? `Bàn ${callers[0]} đang gọi phục vụ`
      : callers.length > 1
        ? `${callers.length} bàn đang gọi phục vụ`
        : active.length
          ? `${active.length} việc đang chờ`
          : 'Mọi bàn đang ổn';
  const sub = !loaded
    ? 'Số liệu sẽ hiện ngay khi nối được máy chủ.'
    : active.length
      ? !waitingOn.length
        ? 'Việc nào cũng đã có người nhận.'
        : wait === 'late'
          ? 'Có việc chờ quá lâu, cần người tới ngay.'
          : wait === 'warn'
            ? 'Có việc đã chờ hơi lâu.'
            : 'Việc vừa báo, đang chờ nhân viên nhận.'
      : camOn
        ? 'Camera đang theo dõi, có việc sẽ báo ngay cho nhân viên.'
        : 'Chưa có camera gửi hình. Bạn vẫn tạo việc bằng tay được.';

  return (
    <div className="fx-page">
      {status === 'offline' && (
        <Banner status="error" title="Mất kết nối tới máy chủ" description={error ?? 'Trang sẽ tự kết nối lại. Số liệu bên dưới có thể đã cũ.'} collapsible={false} />
      )}

      <header className="fx-head">
        <div className="min-w-0">
          <h1>{headline}</h1>
          <p className="fx-head-sub">{sub}</p>
        </div>
        <Clock now={now} />
      </header>

      <div className="fx-strip">
        <StripCell
          ready={loaded}
          label="Việc đang chờ"
          value={<Roll value={active.length} />}
          icon={<BellRing size={16} aria-hidden="true" />}
          iconTone={wait === 'late' ? 'error' : wait === 'warn' ? 'warning' : 'accent'}
          tone={wait === 'late' ? 'bad' : wait === 'warn' ? 'warn' : undefined}
          note={
            !active.length
              ? 'Không ai phải chờ'
              : !waitingOn.length
                ? 'Đều đã có người nhận'
                : wait === 'late'
                  ? 'Có việc chờ quá lâu'
                  : wait === 'warn'
                    ? 'Có việc chờ hơi lâu'
                    : 'Vừa mới báo'
          }
        />
        <StripCell
          ready={loaded}
          label="Bàn có khách"
          icon={<Users size={16} aria-hidden="true" />}
          iconTone="info"
          value={
            <>
              <Roll value={occupied} />
              <small>/{tableNames.length}</small>
            </>
          }
          note={tableNames.length ? `${Math.max(0, tableNames.length - occupied - dirty)} bàn trống` : 'Chưa vẽ bàn'}
        />
        <StripCell
          ready={loaded}
          label="Bàn cần dọn"
          icon={<BrushCleaning size={16} aria-hidden="true" />}
          iconTone="warning"
          value={<Roll value={dirty} />}
          tone={dirty ? 'warn' : undefined}
          note={dirty ? 'Đang chờ người dọn' : 'Không bàn nào cần dọn'}
        />
        <StripCell
          ready={loaded}
          label="Nhân viên đang trực"
          icon={<UserCheck size={16} aria-hidden="true" />}
          iconTone="success"
          value={
            <>
              <Roll value={online} />
              <small>/{staff.length}</small>
            </>
          }
          note={staff.length ? (online ? 'Đang mở app trên điện thoại' : 'Chưa ai mở app') : 'Chưa thêm nhân viên'}
        />
      </div>

      <div className="fx-now-grid">
        {/* Cột trái: camera và bàn */}
        <div className="flex flex-col gap-4 min-w-0">
          <Card padding={3}>
            <div className="flex flex-col gap-3">
              <SectionTitle
                end={
                  cameras.length > 1 && camera ? (
                    <SegmentedControl label="Chọn camera" size="sm" value={camera.id} onChange={setCamId}>
                      {cameras.map((c) => (
                        <SegmentedControlItem key={c.id} value={c.id} label={c.name || c.id} />
                      ))}
                    </SegmentedControl>
                  ) : undefined
                }
              >
                Camera
              </SectionTitle>
              {camera ? (
                <div className="fx-cam-frame">
                  <LiveCamera camera={camera} zones={zones.find((z) => z.camera === camera.id)} tables={tables} alerts={active} />
                </div>
              ) : !loaded ? (
                <Skeleton height={320} />
              ) : (
                <div className="fx-cam-wait">
                  <div className="fx-cam-wait-body">
                    <Video size={26} aria-hidden="true" />
                    <Text type="large" weight="semibold" as="p">
                      Đang chờ hình từ camera
                    </Text>
                    <Text type="supporting" color="secondary" as="p">
                      Chạy máy camera, hoặc mở trang /phat trên một điện thoại để dùng nó làm camera. Hình sẽ hiện ở đây ngay khi có.
                    </Text>
                    <Button label="Xem cách nối camera" variant="secondary" size="sm" href="/cai-dat?tab=camera" />
                  </div>
                </div>
              )}
              {tableNames.length > 0 && (
                <ul className="flex flex-wrap gap-2" aria-label="Trạng thái các bàn">
                  {tableNames.map((id) => {
                    const st = stateOf(id);
                    const hot = calling.has(id);
                    const text = hot
                      ? 'đang gọi'
                      : !st
                        ? 'chưa rõ'
                        : st.state === 'occupied'
                          ? st.people > 0
                            ? `${st.people} khách`
                            : 'có khách'
                          : TABLE_STATE_LABEL[st.state].toLowerCase();
                    return (
                      <li key={id} className="fx-table-chip" data-state={st?.state ?? 'unknown'} data-hot={hot || undefined}>
                        <i className="fx-table-dot" aria-hidden="true" />
                        <b>{id}</b>
                        <span>{text}</span>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          </Card>
          {speed && <SpeedMeter speed={speed} title="Tốc độ phục vụ trong ca" />}
        </div>

        {/* Cột phải: việc và người */}
        <div className="fx-now-side flex flex-col gap-4 min-w-0">
          <Card padding={3}>
            <div className="flex flex-col gap-3">
              <SectionTitle end={<Button label="Tạo việc" size="sm" variant="secondary" icon={<Plus size={15} />} onClick={() => setCreating(true)} />}>
                Việc cần làm{active.length ? ` (${active.length})` : ''}
              </SectionTitle>
              {!loaded && (
                <div className="fx-list">
                  <Skeleton height={104} />
                  <Skeleton height={104} />
                </div>
              )}
              <AnimatedList items={active} getKey={(a) => a.id} className="fx-list" label="Việc đang chờ">
                {(a) => <TaskCard a={a} staff={staff} now={now} provider={provider} escalateS={settings?.escalate_s ?? 0} />}
              </AnimatedList>
              {loaded && active.length === 0 && (
                <div className="fx-item">
                  <EmptyState
                    isCompact
                    icon={<Check size={24} />}
                    title="Không có việc nào đang chờ"
                    description="Khi camera thấy khách gọi, bàn cần dọn hay khách mới, việc sẽ hiện ở đây và báo cho nhân viên."
                  />
                </div>
              )}
              {closed.length > 0 && (
                <div className="flex flex-col gap-1 pt-1">
                  <Text type="supporting" color="secondary">
                    Vừa xong
                  </Text>
                  {closed.map((a) => (
                    <div key={a.id} className="fx-done-row fx-item" data-cancelled={a.status === 'cancelled' || undefined}>
                      {a.status === 'cancelled' ? <X size={14} aria-hidden="true" /> : <Check size={14} aria-hidden="true" />}
                      <Text type="supporting" color="secondary" hasTabularNumbers>
                        {clockTime(a.done_at ?? a.cancelled_at ?? a.created_at).slice(0, 5)}
                      </Text>
                      <Text type="supporting" maxLines={1}>
                        {tableText(a.table)}, {KIND_LABEL[a.kind].toLowerCase()}: {lowerFirst(statusText(a, staff, provider))}
                      </Text>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </Card>

          <Card padding={3}>
            <div className="flex flex-col gap-2">
              <SectionTitle>Nhân viên</SectionTitle>
              {!loaded ? (
                <Skeleton height={96} />
              ) : staff.length ? (
                staff.map((s) => (
                  <div key={s.id} className="flex items-center gap-3 py-1">
                    <span className="fx-person" data-online={s.online || undefined} title={s.online ? 'Đang mở app' : 'Chưa mở app'}>
                      <Avatar name={s.name} size="md" tooltip={false} />
                    </span>
                    <div className="min-w-0 flex-1">
                      <Text type="label" weight="semibold" as="p">
                        {s.name}
                      </Text>
                      <Text type="supporting" color="secondary" as="p" maxLines={1}>
                        {ROLE_LABEL[s.role]}, {attendance(s, now).toLowerCase()}
                        <span className="sr-only">, {s.online ? 'đang mở app' : 'chưa mở app'}</span>
                      </Text>
                    </div>
                    {s.open_tasks > 0 && <Badge variant="warning" label={`${s.open_tasks} việc`} />}
                  </div>
                ))
              ) : (
                <EmptyState
                  isCompact
                  title="Chưa có nhân viên"
                  description="Thêm người để camera có người giao việc."
                  actions={<Button label="Thêm nhân viên" variant="secondary" href="/cai-dat?tab=nhan-vien" />}
                />
              )}
            </div>
          </Card>
        </div>
      </div>

      <Dialog isOpen={creating} onOpenChange={setCreating} width={440} purpose="form">
        <CreateTask onClose={() => setCreating(false)} camera={camera?.id ?? 'cam1'} />
      </Dialog>
    </div>
  );
}
