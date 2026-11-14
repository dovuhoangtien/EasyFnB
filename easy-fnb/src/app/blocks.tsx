import { useEffect, useMemo, useState, type CSSProperties } from 'react';
import { Play, VideoOff } from 'lucide-react';
import { Avatar } from '@astryxdesign/core/Avatar';
import { Badge } from '@astryxdesign/core/Badge';
import { Button } from '@astryxdesign/core/Button';
import { StatusDot } from '@astryxdesign/core/StatusDot';
import { Table } from '@astryxdesign/core/Table';
import { Text } from '@astryxdesign/core/Text';
import { alertClipUrl, ApiError, apiUrl, errorMessage, getClip, requestClip } from '../live/api';
import { useLive } from '../live/store';
import { anyKindLabel, clockTime, shiftText, KIND_LABEL, ROLE_LABEL, SECURITY_LABEL, SPEED_LABEL, speedOf, tableText } from '../live/text';

const WAIT_NOTE = { fast: 'chờ ngắn', ok: 'chờ hơi lâu', slow: 'chờ lâu' } as const;
const speedWord = (s: number | null | undefined) => {
  const k = speedOf(s);
  return k ? SPEED_LABEL[k] : 'chưa có';
};
import type {
  AlertKind,
  Block,
  ChartBlock,
  EventItem,
  EventsBlock,
  InsightsBlock,
  StaffBlock,
  StatsBlock,
  TableBlock,
  TimelineBlock,
  VideoBlock,
  VideoItem,
} from '../live/types';
import { Flipbook, KindBadge, Shot, toneColor } from './ui';
import { BanReview, ChupSetup, ConfirmSetup, QrSetup } from './setupBlocks';

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

// ---------- video camera ----------
const WAIT_CLIP_MS = 40_000; // chờ máy camera cắt clip lâu nhất chừng này
const EVENT_CLIP_MS = 20_000; // clip của một việc tới sau sự kiện khoảng 16 giây

/** Lời báo của máy chủ hay máy camera, nói lại cho chủ quán dễ hiểu */
function clipError(e: string | null | undefined) {
  const s = (e ?? '').toLowerCase();
  if (s.includes('không chạy') || s.includes('đang tắt')) return 'Máy camera đang tắt nên chưa lấy được video.';
  if (s.includes('ghi hình')) return 'Máy camera chưa ghi hình lúc đó.';
  if (s.includes('chưa tới giờ')) return 'Chưa tới giờ đó nên chưa có video.';
  if (s.includes('không trả lời') || s.includes('không gửi')) return 'Máy camera không trả lời nên chưa lấy được video.';
  if (s.includes('kết nối') || s.includes('máy chủ')) return e as string;
  return 'Chưa lấy được video lúc đó.';
}

type ClipState = { status: 'idle' | 'loading' | 'ready' | 'failed'; src?: string; error?: string };

/**
 * Lấy video cho một mục: clip đã sẵn thì dùng ngay; clip đang chờ máy camera thì hỏi lại mỗi giây;
 * chưa xin thì xin khi mục được mở (`active`). Clip của việc tới sau (qua luồng trực tiếp) cũng được bắt.
 */
function useClip(item: VideoItem, active: boolean) {
  const eventClip = useLive((s) => !!item.alert_id && (s.alerts.some((a) => a.id === item.alert_id && a.created_at === item.t && !!a.clip) || s.security.some((a) => a.id === item.alert_id && a.created_at === item.t && !!a.clip)));
  const [attempt, setAttempt] = useState(0);
  const [directBad, setDirectBad] = useState(false);
  const [st, setSt] = useState<ClipState>({ status: 'idle' });
  const direct = directBad ? null : item.src ? apiUrl(item.src) : eventClip && item.alert_id ? alertClipUrl(item.alert_id) : null;

  useEffect(() => {
    if (direct || !active) return;
    const first = attempt === 0 && !directBad;
    if (item.error && (first || !item.camera)) {
      setSt({ status: 'failed', error: item.error });
      return;
    }
    let dead = false;
    let timer: number | undefined;
    let asked = false;
    setSt({ status: 'loading' });
    const fail = (error: string) => {
      if (!dead) setSt({ status: 'failed', error });
    };
    const poll = (id: string, until: number) => {
      getClip(id)
        .then((c) => {
          if (dead) return;
          if (c.status === 'ready' && c.url) setSt({ status: 'ready', src: apiUrl(c.url) });
          else if (c.status === 'failed') fail(clipError(c.error));
          else if (Date.now() > until) fail('Máy camera không trả lời nên chưa lấy được video.');
          else timer = window.setTimeout(() => poll(id, until), 1000);
        })
        .catch((err: unknown) => {
          if (dead) return;
          // máy chủ không còn nhớ yêu cầu này (vừa khởi động lại): xin lại một lần
          if (err instanceof ApiError && err.status === 404 && !asked) ask();
          else if (Date.now() > until) fail(clipError(errorMessage(err)));
          else timer = window.setTimeout(() => poll(id, until), 1500);
        });
    };
    const ask = () => {
      asked = true;
      requestClip(item.camera, item.t_from, item.t_to)
        .then((c) => {
          if (dead) return;
          if (c.status === 'ready' && c.url) setSt({ status: 'ready', src: apiUrl(c.url) });
          else if (c.status === 'failed') fail(clipError(c.error));
          else poll(c.id, Date.now() + WAIT_CLIP_MS);
        })
        .catch((err: unknown) => fail(clipError(errorMessage(err))));
    };
    if (first && item.clip_id) poll(item.clip_id, Date.now() + WAIT_CLIP_MS);
    else {
      // việc vừa xảy ra: chờ clip của chính việc đó tới trước, quá lâu mới xin máy camera cắt
      const wait = first && item.alert_id ? Math.min(item.t + EVENT_CLIP_MS - Date.now(), EVENT_CLIP_MS) : 0;
      if (wait > 0) timer = window.setTimeout(ask, wait);
      else ask();
    }
    return () => {
      dead = true;
      window.clearTimeout(timer);
    };
  }, [item, active, attempt, direct, directBad]);

  const state: ClipState = direct ? { status: 'ready', src: direct } : active ? st : { status: 'idle' };
  return {
    ...state,
    retry: () => setAttempt((n) => n + 1),
    /** trình duyệt không tải được tệp: clip sẵn thì thử xin máy camera cắt lại, không thì báo */
    broken: () => (direct ? setDirectBad(true) : setSt({ status: 'failed', error: 'Không phát được video này.' })),
  };
}

const reducedMotion = () => typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

function videoCaption(item: VideoItem) {
  const where = item.table && !item.label.includes(item.table) ? `${tableText(item.table)}, ` : '';
  return `${where}${item.label}`;
}

/** Một đoạn video: đang lấy thì hiện ảnh camera và lời chờ, không lấy được thì nói rõ vì sao, không bao giờ để khung hỏng */
export function ClipPlayer({ item, active = true, autoPlay = false, onOpen }: { item: VideoItem; active?: boolean; autoPlay?: boolean; onOpen?: () => void }) {
  const clip = useClip(item, active);
  const poster = item.poster ? apiUrl(item.poster) : undefined;
  const [posterBad, setPosterBad] = useState(false);
  const hasPoster = !!poster && !posterBad;
  return (
    <figure className="fx-vid">
      <div className="fx-vid-stage" data-status={clip.status} data-poster={hasPoster || undefined}>
        {clip.status === 'ready' ? (
          <video
            key={clip.src}
            src={clip.src}
            poster={hasPoster ? poster : undefined}
            controls
            playsInline
            muted
            preload="metadata"
            autoPlay={autoPlay && !reducedMotion()}
            onError={clip.broken}
            aria-label={`Video camera: ${videoCaption(item)}, lúc ${clockTime(item.t).slice(0, 5)}`}
          />
        ) : (
          <>
            {hasPoster && <img src={poster} alt="" onError={() => setPosterBad(true)} />}
            {clip.status === 'idle' && (
              <button type="button" className="fx-vid-open" onClick={onOpen} aria-label={`Xem video: ${videoCaption(item)}`}>
                <Play size={22} aria-hidden="true" />
              </button>
            )}
            {clip.status === 'loading' && (
              <div className="fx-vid-note" role="status">
                <span className="fx-vid-spin" aria-hidden="true" />
                <span>Đang lấy video từ máy camera, chờ một chút</span>
              </div>
            )}
            {clip.status === 'failed' && (
              <div className="fx-vid-note" role="status">
                <VideoOff size={18} aria-hidden="true" />
                <span>
                  {clip.error}
                  {hasPoster ? ' Đây là ảnh camera lúc đó.' : ''}
                </span>
                {!item.error && <Button label="Thử lại" size="sm" variant="secondary" onClick={clip.retry} />}
              </div>
            )}
          </>
        )}
      </div>
      <figcaption className="fx-vid-cap">
        <Text type="label" weight="semibold" hasTabularNumbers>
          {clockTime(item.t).slice(0, 5)}
        </Text>
        <Text type="label">{videoCaption(item)}</Text>
        {item.note && (
          <Text type="supporting" color="secondary" as="p">
            {item.note}
          </Text>
        )}
      </figcaption>
    </figure>
  );
}

function VideoClips({ b }: { b: VideoBlock }) {
  const [sel, setSel] = useState(0);
  const item = b.items[Math.min(sel, b.items.length - 1)];
  if (!item) return null;
  return (
    <div className="fx-block">
      <BlockTitle>{b.title}</BlockTitle>
      <ClipPlayer key={sel} item={item} autoPlay />
      {b.items.length > 1 && (
        <ul className="fx-vid-list" aria-label="Các đoạn video khác">
          {b.items.map((it, i) => (
            <li key={`${it.t}-${i}`}>
              <button type="button" className="fx-vid-pick" aria-pressed={i === sel} onClick={() => setSel(i)}>
                <b>{clockTime(it.t).slice(0, 5)}</b>
                <span>{videoCaption(it)}</span>
                {it.error && <small>chưa có video</small>}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ---------- chuyện của một bàn, từng bước ----------
function Timeline({ b }: { b: TimelineBlock }) {
  const [open, setOpen] = useState<number | null>(null);
  return (
    <div className="fx-block">
      <BlockTitle>{b.title}</BlockTitle>
      <ol className="fx-tl">
        {b.items.map((it, i) => (
          <li key={`${it.t}-${i}`} className="fx-tl-row" data-tone={it.tone ?? undefined}>
            <span className="fx-tl-time">{clockTime(it.t).slice(0, 5)}</span>
            <span className="fx-tl-dot" aria-hidden="true" />
            <div className="fx-tl-body">
              <span>{it.text}</span>
              {it.video && (
                <button type="button" className="fx-tl-play" aria-expanded={open === i} onClick={() => setOpen(open === i ? null : i)}>
                  <Play size={12} aria-hidden="true" />
                  {open === i ? 'Đóng video' : 'Xem video'}
                </button>
              )}
              {it.video && open === i && <ClipPlayer item={it.video} autoPlay />}
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}

function EventRow({ e }: { e: EventItem }) {
  const [playing, setPlaying] = useState(false);
  // clip của việc có thể tới sau khi câu trả lời đã hiện: xem thêm ở luồng trực tiếp
  const liveClip = useLive((s) => [...s.alerts, ...s.security].some((a) => a.id === e.alert_id && a.created_at === e.t && !!a.clip));
  const clipSrc = e.clip_url ?? (liveClip ? `/api/alerts/${encodeURIComponent(e.alert_id)}/clip.mp4` : null);
  const what = `${anyKindLabel(e.kind)}, ${tableText(e.table)}`;
  const crop = e.crop_url ? [{ src: apiUrl(e.crop_url), alt: `Ảnh camera: ${what}` }] : [];
  const hasMedia = !!(e.strip_url || e.crop_url);
  const video = useMemo<VideoItem | null>(
    () =>
      clipSrc
        ? {
            label: anyKindLabel(e.kind),
            t: e.t,
            table: e.table,
            alert_id: e.alert_id,
            src: clipSrc,
            clip_id: null,
            poster: e.crop_url,
            note: null,
            camera: '',
            t_from: e.t,
            t_to: e.t,
            error: 'Clip của việc này không còn trên máy chủ.',
          }
        : null,
    [clipSrc, e.kind, e.t, e.table, e.alert_id, e.crop_url],
  );
  return (
            <div className="fx-ev" data-media={hasMedia || undefined}>
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
                  {e.kind in KIND_LABEL ? <KindBadge kind={e.kind as AlertKind} /> : <Badge variant={e.kind in SECURITY_LABEL ? 'error' : undefined} label={anyKindLabel(e.kind)} />}
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
                {clipSrc && (
                  <div>
                    <Button
                      label={playing ? 'Đóng video' : 'Xem video'}
                      size="sm"
                      variant="secondary"
                      icon={<Play size={14} />}
                      onClick={() => setPlaying(!playing)}
                    />
                  </div>
                )}
              </div>
              {video && playing && (
                <div className="fx-ev-video">
                  <ClipPlayer autoPlay item={video} />
                </div>
              )}
            </div>
  );
}

function EventRows({ items }: { items: EventItem[] }) {
  return (
    <>
      {items.map((e) => (
        <EventRow key={e.alert_id} e={e} />
      ))}
    </>
  );
}

function Events({ b }: { b: EventsBlock }) {
  return (
    <div className="fx-block">
      <BlockTitle>{b.title}</BlockTitle>
      <div>
        <EventRows items={b.items} />
        {!b.items.length && (
          <Text type="supporting" color="secondary">
            Không có sự kiện nào khớp.
          </Text>
        )}
      </div>
    </div>
  );
}

// ---------- gợi ý cho ca sau ----------
const TONE_BADGE = { bad: 'error', warn: 'warning', good: 'success' } as const;
const TONE_WORD = { bad: 'Cần sửa', warn: 'Nên xem', good: 'Điểm tốt' } as const;

function Insights({ b }: { b: InsightsBlock }) {
  return (
    <div className="fx-block">
      <BlockTitle>{b.title}</BlockTitle>
      <ol className="fx-insights">
        {b.items.map((it) => (
          <li key={it.id} className="fx-insight">
            <div className="flex items-center gap-2 flex-wrap">
              {it.tone && <Badge variant={TONE_BADGE[it.tone]} label={TONE_WORD[it.tone]} />}
              <Text type="label" weight="semibold" as="p">
                {it.title}
              </Text>
            </div>
            <Text type="body" as="p">
              {it.text}
            </Text>
            <p className="fx-insight-do">{it.action}</p>
            {it.events.length > 0 && (
              <details className="fx-insight-proof">
                <summary>Xem {it.events.length} lần camera ghi lại</summary>
                <div>
                  <EventRows items={it.events} />
                </div>
              </details>
            )}
          </li>
        ))}
      </ol>
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
          case 'insights':
            return <Insights key={i} b={b} />;
          case 'video':
            return <VideoClips key={i} b={b} />;
          case 'timeline':
            return <Timeline key={i} b={b} />;
          case 'qr':
            return <QrSetup key={i} b={b} />;
          case 'ban':
            return <BanReview key={i} b={b} />;
          case 'xac_nhan':
            return <ConfirmSetup key={i} b={b} />;
          case 'chup':
            return <ChupSetup key={i} b={b} />;
          default:
            return null;
        }
      })}
    </div>
  );
}
