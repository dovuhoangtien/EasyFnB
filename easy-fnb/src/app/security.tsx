import { useCallback, useEffect, useMemo, useState } from 'react';
import { Check, Eye, Film, ShieldAlert, X } from 'lucide-react';
import { Badge } from '@astryxdesign/core/Badge';
import { Button } from '@astryxdesign/core/Button';
import { Dialog, DialogHeader } from '@astryxdesign/core/Dialog';
import type { LightboxMedia } from '@astryxdesign/core/Lightbox';
import { Text } from '@astryxdesign/core/Text';
import {
  apiUrl,
  cancelAlert,
  doneAlert,
  errorMessage,
  fetchOriginalClip,
  getClip,
  isPinError,
  keepClip,
  rememberPin,
  requestOriginalClip,
} from '../live/api';
import { useOwnerPin, useRun } from '../live/hooks';
import { live, useLive } from '../live/store';
import { clockTime, SECURITY_LABEL, securityLine, securityOpen } from '../live/text';
import type { SecurityAlert, VideoItem } from '../live/types';
import { ClipPlayer } from './blocks';
import { PinDialog } from './ownerPin';
import { Shot } from './ui';

const SEC_CLIP_BEFORE_MS = 10_000;
const SEC_CLIP_AFTER_MS = 20_000;
const ORIGINAL_WAIT_MS = 60_000;

function securityMedia(a: SecurityAlert): LightboxMedia[] {
  const what = securityLine(a);
  const out: LightboxMedia[] = [];
  if (a.crop_url) out.push({ src: apiUrl(a.crop_url), alt: `Ảnh camera: ${what}`, caption: 'Ảnh camera lúc xảy ra' });
  if (a.evidence?.strip) out.push({ src: apiUrl(a.evidence.strip), alt: `Bốn khung hình: ${what}`, caption: 'Bốn khung hình quanh lúc xảy ra' });
  if (a.evidence?.overview) out.push({ src: apiUrl(a.evidence.overview), alt: `Toàn cảnh: ${what}`, caption: 'Toàn cảnh' });
  return out;
}

/** Ảnh nhỏ có chữ bên dưới */
function Labeled({ media, label, size }: { media: LightboxMedia[]; label: string; size: number }) {
  return (
    <figure className="fx-sec-shot">
      <Shot media={media} size={size} />
      <figcaption>{label}</figcaption>
    </figure>
  );
}

function SecurityShots({ a, size }: { a: SecurityAlert; size: number }) {
  const rest = securityMedia(a);
  if (a.kind === 'item_taken') {
    const person: LightboxMedia[] = a.evidence?.person ? [{ src: apiUrl(a.evidence.person), alt: 'Người ngồi bàn', caption: 'Người ngồi bàn (lúc ngồi)' }] : [];
    // ảnh người cầm đi: dải 4 khung lúc lấy trước, không có thì ảnh cắt
    const strip = a.evidence?.strip ? apiUrl(a.evidence.strip) : null;
    const taker = strip ? [...rest.filter((m) => m.src === strip), ...rest.filter((m) => m.src !== strip)] : rest;
    return (
      <div className="fx-sec-shots">
        <Labeled media={person} label="Người ngồi bàn" size={size} />
        <Labeled media={taker} label="Người cầm đi" size={size} />
      </div>
    );
  }
  return (
    <div className="fx-sec-shots">
      <Shot media={rest} size={size} />
    </div>
  );
}

// ---------- clip ----------
function ClipDialog({ a, onClose }: { a: SecurityAlert; onClose: () => void }) {
  const item = useMemo<VideoItem>(
    () => ({
      label: SECURITY_LABEL[a.kind],
      t: a.created_at,
      table: a.table,
      alert_id: a.id,
      src: null,
      clip_id: null,
      poster: a.crop_url,
      note: null,
      camera: a.camera,
      t_from: a.created_at - SEC_CLIP_BEFORE_MS,
      t_to: a.created_at + SEC_CLIP_AFTER_MS,
      error: null,
    }),
    [a.kind, a.created_at, a.table, a.id, a.crop_url, a.camera],
  );
  return (
    <>
      <DialogHeader title={securityLine(a)} subtitle="Clip quanh lúc xảy ra, mặt người đã được che." onOpenChange={onClose} />
      <div style={{ paddingInline: 16, paddingBottom: 16 }}>
        <ClipPlayer item={item} autoPlay />
      </div>
    </>
  );
}

type Original = { status: 'loading' | 'ready' | 'failed'; src?: string; clipId?: string; error?: string };

/** Clip bản gốc (không che mặt): xin máy camera cắt, chờ xong, tải kèm PIN rồi phát */
function OriginalClip({ a, pin, onPinBad }: { a: SecurityAlert; pin: string; onPinBad: () => void }) {
  const [st, setSt] = useState<Original>({ status: 'loading' });
  const [kept, setKept] = useState(false);
  const { busy, run } = useRun();

  useEffect(() => {
    let dead = false;
    let timer: number | undefined;
    let objectUrl: string | null = null;
    const until = Date.now() + ORIGINAL_WAIT_MS;
    const fail = (err: unknown) => {
      if (dead) return;
      if (isPinError(err)) {
        rememberPin(null);
        onPinBad();
        return;
      }
      setSt({ status: 'failed', error: typeof err === 'string' ? err : errorMessage(err) });
    };
    const play = (clipId: string, url: string) =>
      fetchOriginalClip(url, pin)
        .then((blob) => {
          if (dead) return;
          objectUrl = URL.createObjectURL(blob);
          setSt({ status: 'ready', src: objectUrl, clipId });
        })
        .catch(fail);
    const poll = (clipId: string) =>
      getClip(clipId)
        .then((c) => {
          if (dead) return;
          if (c.status === 'ready' && c.url) void play(clipId, c.url);
          else if (c.status === 'failed') fail(c.error ?? 'Chưa lấy được bản gốc.');
          else if (Date.now() > until) fail('Máy camera không trả lời nên chưa lấy được bản gốc.');
          else timer = window.setTimeout(() => void poll(clipId), 1000);
        })
        .catch(fail);
    requestOriginalClip(a.id, pin)
      .then((c) => {
        if (dead) return;
        if (c.status === 'ready' && c.url) void play(c.id, c.url);
        else if (c.status === 'failed') fail(c.error ?? 'Chưa lấy được bản gốc.');
        else void poll(c.id);
      })
      .catch(fail);
    return () => {
      dead = true;
      window.clearTimeout(timer);
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [a.id, pin, onPinBad]);

  const keep = async () => {
    if (!st.clipId) return;
    const out = await run('keep', () => keepClip(st.clipId as string, pin), 'Đã giữ clip làm bằng chứng');
    if (out) setKept(true);
  };

  return (
    <div className="flex flex-col gap-3" style={{ paddingInline: 16, paddingBottom: 16 }}>
      <div className="fx-vid-stage" data-status={st.status}>
        {st.status === 'ready' ? (
          <video src={st.src} controls playsInline muted autoPlay aria-label={`Bản gốc: ${securityLine(a)}`} />
        ) : (
          <div className="fx-vid-note" role="status">
            {st.status === 'loading' && <span className="fx-vid-spin" aria-hidden="true" />}
            <span>{st.status === 'loading' ? 'Đang lấy bản gốc từ máy camera, chờ một chút' : st.error}</span>
          </div>
        )}
      </div>
      <Text type="supporting" color="secondary" as="p">
        Bản gốc tự xoá sau 24 giờ. Mỗi lần xem được ghi vào nhật ký.
      </Text>
      {st.status === 'ready' && (
        <div>
          <Button
            label={kept ? 'Đã giữ làm bằng chứng' : 'Giữ làm bằng chứng'}
            variant="secondary"
            size="sm"
            icon={kept ? <Check size={15} /> : undefined}
            isDisabled={kept}
            isLoading={busy === 'keep'}
            onClick={() => void keep()}
          />
        </div>
      )}
    </div>
  );
}

// ---------- một cảnh báo ----------
export function SecurityCard({
  a,
  actor,
  provider = 'Gemini',
  phone = false,
  canOriginal = false,
  fresh = false,
}: {
  a: SecurityAlert;
  /** ai bấm: 'manager' trên trang chủ quán, id nhân viên trên điện thoại */
  actor: string;
  provider?: string;
  phone?: boolean;
  /** hiện nút "Xem bản gốc" (đang che mặt và đã đặt PIN) */
  canOriginal?: boolean;
  fresh?: boolean;
}) {
  const { busy, run } = useRun();
  const cameras = useLive((s) => s.cameras);
  const [view, setView] = useState<'clip' | 'original' | null>(null);
  const [pin, setPin] = useState<string | null>(null);
  const { withPin, pinProps } = useOwnerPin();
  const act = async (key: string, fn: () => Promise<unknown>) => {
    const out = await run(`${key}-${a.id}`, fn);
    if (out) live.upsertAlert(out as SecurityAlert);
  };
  const camName = cameras.find((c) => c.id === a.camera)?.name || a.camera;
  const v = a.verify?.state;
  const line = securityLine(a);
  const onPinBad = useCallback(() => {
    setView(null);
    setPin(null);
    withPin((p) => {
      setPin(p);
      setView('original');
    });
  }, [withPin]);

  return (
    <article className="fx-sec" data-phone={phone || undefined} data-fresh={fresh || undefined} aria-label={line}>
      <SecurityShots a={a} size={phone ? 96 : 72} />
      <div className="min-w-0 flex-1 flex flex-col gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          <Badge variant="error" label={SECURITY_LABEL[a.kind]} icon={<ShieldAlert size={12} aria-hidden="true" />} />
          {v === 'confirmed' && <Badge variant="success" label={`${provider} xác nhận`} icon={<Check size={12} aria-hidden="true" />} />}
          {(v === 'unverified' || v === 'error') && <Badge variant="warning" label="Chưa xác minh" />}
        </div>
        <div>
          <p className={phone ? 'fx-sec-line fx-sec-line--big' : 'fx-sec-line'}>{line}</p>
          <Text type="supporting" color="secondary" as="p" hasTabularNumbers>
            Lúc {clockTime(a.created_at).slice(0, 5)}, {camName}
          </Text>
        </div>
        <div className={phone ? 'grid grid-cols-2 gap-2' : 'flex items-center gap-2 flex-wrap'}>
          {!phone && <Button label="Xem clip" size="sm" variant="secondary" icon={<Film size={15} />} onClick={() => setView('clip')} />}
          <Button
            label="Đã biết"
            size={phone ? 'lg' : 'sm'}
            variant="primary"
            icon={phone ? <Check size={18} /> : undefined}
            isLoading={busy === `done-${a.id}`}
            onClick={() => void act('done', () => doneAlert(a.id, actor))}
          />
          <Button
            label="Báo nhầm"
            size={phone ? 'lg' : 'sm'}
            variant={phone ? 'secondary' : 'ghost'}
            icon={phone ? <X size={18} /> : undefined}
            isLoading={busy === `cancel-${a.id}`}
            onClick={() => void act('cancel', () => cancelAlert(a.id, actor, 'báo nhầm'))}
          />
          {canOriginal && !phone && (
            <Button
              label="Xem bản gốc"
              size="sm"
              variant="ghost"
              icon={<Eye size={15} />}
              onClick={() =>
                withPin((p) => {
                  setPin(p);
                  setView('original');
                })
              }
            />
          )}
        </div>
      </div>
      <Dialog isOpen={view !== null} onOpenChange={(o) => !o && setView(null)} width={720}>
        {view === 'clip' && <ClipDialog a={a} onClose={() => setView(null)} />}
        {view === 'original' && pin && (
          <>
            <DialogHeader title={`Bản gốc: ${line}`} subtitle="Video không che mặt, chỉ chủ quán xem." onOpenChange={() => setView(null)} />
            <OriginalClip a={a} pin={pin} onPinBad={onPinBad} />
          </>
        )}
      </Dialog>
      <PinDialog {...pinProps} />
    </article>
  );
}

/** Các cảnh báo an ninh còn mở, đặt trên cùng trang "Bây giờ" */
export function SecurityAlerts({ now }: { now: number }) {
  const security = useLive((s) => s.security);
  const settings = useLive((s) => s.settings);
  const open = useMemo(() => security.filter(securityOpen).sort((x, y) => y.created_at - x.created_at), [security]);
  if (!open.length) return null;
  const canOriginal = settings?.blur_faces !== false && !!settings?.owner_pin_set;
  return (
    <section className="flex flex-col gap-2" aria-label="Cảnh báo an ninh">
      {open.map((a) => (
        <SecurityCard key={a.id} a={a} actor="manager" provider={settings?.provider ?? 'Gemini'} canOriginal={canOriginal} fresh={now - a.created_at < 4000} />
      ))}
    </section>
  );
}
