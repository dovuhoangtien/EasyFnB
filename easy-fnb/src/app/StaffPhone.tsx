import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { Link as RouterLink, useParams } from 'react-router';
import { BellRing, Check, ChevronRight, Footprints, ScanEye, SquarePlus, TriangleAlert, X } from 'lucide-react';
import { Avatar } from '@astryxdesign/core/Avatar';
import { Badge } from '@astryxdesign/core/Badge';
import { Banner } from '@astryxdesign/core/Banner';
import { Button } from '@astryxdesign/core/Button';
import { Card } from '@astryxdesign/core/Card';
import { Link } from '@astryxdesign/core/Link';
import { Text } from '@astryxdesign/core/Text';
import { ackAlert, apiUrl, cancelAlert, doneAlert } from '../live/api';
import { useRun, useTitle } from '../live/hooks';
import { createNotifier } from '../live/notifier';
import { live, useLive, useLiveConnection, useServerNow } from '../live/store';
import { byUrgency, ROLE_LABEL, securityOpen, securitySpeech, staffName, tableText, waitWord } from '../live/text';
import type { Alert, AlertKind, SecurityAlert } from '../live/types';
import { beep, hasVietnameseVoice, speak, speechSupported, unlockAudio, vibrate } from '../live/voice';
import { AnimatedList } from './motion';
import { SecurityCard } from './security';
import { StaffTeam } from './Team';
import { alertMedia, Conn, KindBadge, Shot } from './ui';

/** Việc nói bằng lời cho nhân viên */
const KIND_TODO: Record<AlertKind, string> = {
  call: 'Khách giơ tay gọi phục vụ',
  needs_clearing: 'Bàn cần dọn',
  new_guest: 'Khách mới ngồi, chào và đưa thực đơn',
};
/** Việc quản lý tạo tay thì không nói là camera thấy */
const todoText = (a: Alert) => (a.detail === 'Quản lý tạo' && a.kind === 'call' ? 'Quản lý nhờ ra bàn phục vụ' : KIND_TODO[a.kind]);
const NOTICE_MS = 7000;
const mineActive = (a: Alert, me: string) => a.assigned_to === me && (a.status === 'open' || a.status === 'acked');
/** Cảnh báo an ninh gửi cho người này và còn mở */
const secForMe = (a: SecurityAlert, me: string) => !!a.notify?.includes(me) && securityOpen(a);

function PhoneFrame({ children }: { children: ReactNode }) {
  const status = useLive((s) => s.status);
  return (
    <div className="fx-phone-app">
      <header className="fx-phone-head">
        <span className="inline-flex items-center gap-2">
          <span className="fx-mark">
            <ScanEye size={17} strokeWidth={2.4} aria-hidden="true" />
          </span>
          <Text type="label" weight="semibold">
            Easy FnB
          </Text>
        </span>
        <Conn status={status} />
      </header>
      {children}
    </div>
  );
}

// ---------- thêm vào màn hình chính ----------
interface InstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

/** Manifest riêng của người này: cài vào màn hình chính xong, chạm icon là mở đúng /nv/<mã> */
function useStaffManifest(id: string) {
  useEffect(() => {
    const link = document.querySelector<HTMLLinkElement>('link[rel="manifest"]');
    if (!link) return;
    const before = link.getAttribute('href');
    link.setAttribute('href', apiUrl(`/api/manifest/nv/${encodeURIComponent(id)}`));
    return () => {
      if (before) link.setAttribute('href', before);
    };
  }, [id]);
}

const isStandalone = () => window.matchMedia('(display-mode: standalone)').matches || (navigator as Navigator & { standalone?: boolean }).standalone === true;
const isIos = () => /iphone|ipad|ipod/i.test(navigator.userAgent);

/** Android/Chrome: một nút cài ngay. iPhone không có nút, chỉ hướng dẫn được. Đã cài rồi thì không hiện gì */
function InstallHint() {
  const [prompt, setPrompt] = useState<InstallPromptEvent | null>(null);
  const [installed, setInstalled] = useState(isStandalone);
  useEffect(() => {
    const onPrompt = (e: Event) => {
      e.preventDefault();
      setPrompt(e as InstallPromptEvent);
    };
    const onInstalled = () => setInstalled(true);
    window.addEventListener('beforeinstallprompt', onPrompt);
    window.addEventListener('appinstalled', onInstalled);
    return () => {
      window.removeEventListener('beforeinstallprompt', onPrompt);
      window.removeEventListener('appinstalled', onInstalled);
    };
  }, []);
  if (installed) return null;
  if (prompt) {
    return (
      <Button
        label="Thêm vào màn hình chính"
        variant="secondary"
        size="lg"
        icon={<SquarePlus size={18} />}
        onClick={() => {
          void prompt.prompt();
          void prompt.userChoice.then(() => setPrompt(null));
        }}
      />
    );
  }
  if (isIos()) {
    return (
      <Text type="supporting" color="secondary" as="p">
        Để lần sau chạm một cái là vào: bấm nút Chia sẻ của Safari, chọn “Thêm vào MH chính”.
      </Text>
    );
  }
  // Android qua http ở quán: trình duyệt không cho nút cài (chỉ https hợp lệ mới có), nhưng menu vẫn tạo được lối tắt
  if (/android/i.test(navigator.userAgent)) {
    return (
      <Text type="supporting" color="secondary" as="p">
        Để lần sau chạm một cái là vào: mở menu ⋮ của trình duyệt, chọn “Thêm vào màn hình chính”.
      </Text>
    );
  }
  return null;
}

// ---------- chọn tên ----------
function PickStaff() {
  useLiveConnection();
  useTitle('Easy FnB cho nhân viên');
  const loaded = useLive((s) => s.loaded);
  const staff = useLive((s) => s.staff);
  return (
    <PhoneFrame>
      <div className="flex flex-col gap-1 pt-4">
        <h1 className="fx-phone-hello">Bạn là ai?</h1>
        <Text type="body" color="secondary" as="p">
          {staff.length ? 'Chọn tên để nhận việc của mình trên điện thoại này.' : loaded ? 'Chưa có nhân viên nào. Nhờ quản lý thêm tên trong Cài đặt.' : 'Đang kết nối tới máy chủ của quán…'}
        </Text>
      </div>
      <div className="flex flex-col gap-2">
        {staff.map((s) => (
          <RouterLink key={s.id} to={`/nv/${encodeURIComponent(s.id)}`} className="fx-phone-pick">
            <Avatar name={s.name} size="md" tooltip={false} />
            <span className="min-w-0 flex-1 flex flex-col">
              <Text type="label" weight="semibold">
                {s.name}
              </Text>
              <Text type="supporting" color="secondary">
                {ROLE_LABEL[s.role]}
                {s.online ? ', đang mở app' : ''}
              </Text>
            </span>
            <ChevronRight size={18} aria-hidden="true" />
          </RouterLink>
        ))}
      </div>
    </PhoneFrame>
  );
}

// ---------- một việc ----------
function TaskCard({ a, big, now, me }: { a: Alert; big: boolean; now: number; me: string }) {
  const { busy, run } = useRun();
  const going = a.status === 'acked';
  const media = alertMedia(a);
  return (
    <article className="fx-phone-task" data-big={big || undefined} data-kind={a.kind} data-fresh={now - a.created_at < 4000 || undefined} aria-label={`${todoText(a)}, ${tableText(a.table)}`}>
      <div className="flex items-center gap-2 flex-wrap">
        <KindBadge kind={a.kind} />
        {a.escalated && <Badge variant="error" label="Gấp" icon={<TriangleAlert size={12} aria-hidden="true" />} />}
        {going && <Badge variant="success" label="Bạn đang tới" />}
        {!going && (
          <span className="fx-age ml-auto" data-level={waitWord(now - a.created_at, false).level}>
            {waitWord(now - a.created_at, false).label}
          </span>
        )}
      </div>
      <div className="flex items-center gap-3">
        <div className="min-w-0 flex-1">
          <p className="fx-phone-table">{tableText(a.table)}</p>
          <Text type={big ? 'body' : 'supporting'} as="p">
            {todoText(a)}
          </Text>
          {a.kind === 'needs_clearing' && a.items?.length ? (
            <Text type="supporting" color="secondary" as="p">
              Còn trên bàn: {a.items.map((i) => `${i.count} ${i.name}`).join(', ')}
            </Text>
          ) : null}
        </div>
        {media.length > 0 && <Shot media={media} size={big ? 96 : 64} />}
      </div>
      <div className="grid gap-2" style={{ gridTemplateColumns: going ? '1fr' : '1fr 1fr' }}>
        {!going && (
          <Button
            label="Tôi đang tới"
            variant="secondary"
            size="lg"
            icon={<Footprints size={18} />}
            isLoading={busy === 'ack'}
            onClick={() => void run('ack', () => ackAlert(a.id, me).then((x) => live.upsertAlert(x)))}
          />
        )}
        <Button
          label="Xong"
          variant="primary"
          size="lg"
          icon={<Check size={18} />}
          isLoading={busy === 'done'}
          onClick={() => void run('done', () => doneAlert(a.id, me).then((x) => live.upsertAlert(x)))}
        />
      </div>
      <Button
        label="Báo nhầm, không có việc này"
        variant="ghost"
        size="md"
        icon={<X size={16} />}
        isLoading={busy === 'cancel'}
        onClick={() => void run('cancel', () => cancelAlert(a.id, me, 'nhân viên báo nhầm').then((x) => live.upsertAlert(x)))}
      />
    </article>
  );
}

// ---------- ca làm của một người ----------
interface Notice {
  id: number;
  text: string;
  tone: 'error' | 'info';
}

function StaffShift({ id }: { id: string }) {
  const [started, setStarted] = useState(false);
  useStaffManifest(id);
  useLiveConnection(started ? id : null);
  const status = useLive((s) => s.status);
  const loaded = useLive((s) => s.loaded);
  const staff = useLive((s) => s.staff);
  const alerts = useLive((s) => s.alerts);
  const security = useLive((s) => s.security);
  const settings = useLive((s) => s.settings);
  const now = useServerNow();
  const me = staff.find((s) => s.id === id);
  // chủ quán chỉ nhận cảnh báo an ninh, không nhận việc phục vụ
  const owner = me?.role === 'owner';
  const [notice, setNotice] = useState<Notice | null>(null);
  const [noVoice, setNoVoice] = useState(false);
  const wake = useRef<WakeLockSentinel | null>(null);
  const staffRef = useRef(staff);
  const alertsRef = useRef(alerts);
  useTitle(me ? `${me.name}, Easy FnB` : 'Easy FnB cho nhân viên');

  useEffect(() => {
    staffRef.current = staff;
    alertsRef.current = alerts;
  }, [staff, alerts]);

  const mine = useMemo(() => (owner ? [] : alerts.filter((a) => mineActive(a, id)).sort(byUrgency)), [alerts, id, owner]);
  const secMine = useMemo(() => security.filter((a) => secForMe(a, id)).sort((x, y) => y.created_at - x.created_at), [security, id]);

  // Cảnh báo an ninh mới: có người ngoài giờ thì chuông và đọc to; lấy đồ, vào khu cấm chỉ rung và chuông nhẹ (không đọc trước mặt khách)
  useEffect(() => {
    if (!started) return;
    const seen = new Set<string>();
    const off = live.onSecurityChange((next, prev) => {
      if (!secForMe(next, id) || (prev && secForMe(prev, id)) || seen.has(next.id)) return;
      seen.add(next.id);
      if (next.kind === 'after_hours') {
        // chuông riêng, rung dài, hết chuông mới đọc
        beep('alarm');
        vibrate([300, 120, 300, 120, 300]);
        window.setTimeout(() => speak(securitySpeech(next)), 1100);
      } else {
        beep('soft');
        vibrate([200, 100, 200, 100, 200]);
      }
    });
    return off;
  }, [started, id]);

  // Có việc mới thì kêu, rung, đọc; việc bị huỷ hay chuyển người thì báo ngắn
  useEffect(() => {
    if (!started) return;
    const notifier = createNotifier((a) => mineActive(alertsRef.current.find((x) => x.id === a.id) ?? a, id));
    const off = live.onAlertChange((next, prev) => {
      const was = prev ? mineActive(prev, id) : false;
      const is = mineActive(next, id);
      const where = tableText(next.table);
      if (is && !was && next.acked_by !== id) {
        notifier.push(next);
        return;
      }
      if (!was || is) return;
      if (next.status === 'cancelled') {
        const byAi = next.verify.state === 'rejected';
        const reason = byAi ? 'báo nhầm' : (next.cancel_reason ?? 'báo nhầm');
        const why = byAi && next.verify.reason ? ` AI: ${next.verify.reason}.` : '';
        beep('cancel');
        vibrate(220);
        setNotice({ id: Date.now(), tone: 'error', text: `Đã huỷ: ${reason}. ${where}.${why}` });
      } else if (next.status === 'done' && next.done_by !== id) {
        setNotice({ id: Date.now(), tone: 'info', text: `${where} đã được đánh dấu xong.` });
      } else if (next.assigned_to && next.assigned_to !== id) {
        setNotice({ id: Date.now(), tone: 'info', text: `${where} đã chuyển cho ${staffName(staffRef.current, next.assigned_to)}.` });
      }
    });
    return () => {
      off();
      notifier.stop();
    };
  }, [started, id]);

  useEffect(() => {
    if (!notice) return;
    const t = window.setTimeout(() => setNotice(null), NOTICE_MS);
    return () => window.clearTimeout(t);
  }, [notice]);

  // Giữ màn hình sáng trong ca (nếu trình duyệt cho)
  useEffect(() => {
    if (!started || !('wakeLock' in navigator)) return;
    let alive = true;
    const lock = async () => {
      try {
        const s = await navigator.wakeLock.request('screen');
        if (alive) wake.current = s;
        else void s.release();
      } catch {
        // máy không cho giữ màn hình
      }
    };
    const onVis = () => {
      if (document.visibilityState === 'visible') void lock();
    };
    void lock();
    document.addEventListener('visibilitychange', onVis);
    return () => {
      alive = false;
      document.removeEventListener('visibilitychange', onVis);
      void wake.current?.release();
      wake.current = null;
    };
  }, [started]);

  const start = () => {
    unlockAudio();
    setStarted(true);
    const n = mine.length;
    const s = secMine.length;
    window.setTimeout(() => {
      setNoVoice(!speechSupported() || !hasVietnameseVoice());
      beep('normal');
      if (n) speak(`Bạn có ${n} việc đang chờ`);
      else if (s) vibrate([200, 100, 200]);
    }, 150);
  };

  if (loaded && !me) {
    return (
      <PhoneFrame>
        <Card padding={4}>
          <div className="flex flex-col gap-3">
            <Text type="display-3" as="h1">
              Không tìm thấy nhân viên “{id}”
            </Text>
            <Text type="body" color="secondary" as="p">
              Có thể quản lý đã đổi danh sách nhân viên. Chọn lại tên của bạn.
            </Text>
            <Button label="Chọn tên" variant="primary" size="lg" href="/nv" />
          </div>
        </Card>
      </PhoneFrame>
    );
  }

  if (!started) {
    return (
      <PhoneFrame>
        <div className="flex flex-1 flex-col justify-center gap-4 py-8">
          <h1 className="fx-phone-hello">{me ? `Chào ${me.name}` : status === 'offline' ? 'Chưa kết nối được máy chủ' : 'Đang kết nối…'}</h1>
          {!me && status === 'offline' && (
            <Text type="body" color="secondary" as="p">
              Kiểm tra điện thoại đang dùng cùng Wi-Fi với máy chủ của quán. Trang sẽ tự kết nối lại.
            </Text>
          )}
          {me && (
            <Text type="body" color="secondary" as="p">
              {ROLE_LABEL[me.role]}
            </Text>
          )}
          <Button label="Bắt đầu ca" variant="primary" size="lg" icon={<BellRing size={18} />} isDisabled={!me} onClick={start} />
          <InstallHint />
          <Text type="supporting" color="secondary" as="p">
            Không phải bạn? <Link href="/nv">Chọn tên khác</Link>
          </Text>
        </div>
      </PhoneFrame>
    );
  }

  const topId = mine[0]?.id;

  return (
    <PhoneFrame>
      <div className="flex items-center gap-3">
        <Avatar name={me?.name ?? id} size="md" tooltip={false} />
        <div className="min-w-0 flex-1">
          <Text type="label" weight="semibold" as="p">
            {me?.name}
          </Text>
          <Text type="supporting" color="secondary" as="p">
            {me ? ROLE_LABEL[me.role] : ''}
            {mine.length ? `, ${mine.length} việc đang chờ` : ''}
            {secMine.length ? `, ${secMine.length} cảnh báo` : ''}
          </Text>
        </div>
      </div>

      <StaffTeam me={id}>
      {noVoice && (
        <Text type="supporting" color="secondary" as="p">
          Máy chưa có giọng đọc tiếng Việt, chỉ có tiếng chuông và rung.
        </Text>
      )}

      <div aria-live="assertive">{notice && <Banner key={notice.id} status={notice.tone} title={notice.text} collapsible={false} />}</div>

      {status === 'offline' && <Banner status="warning" title="Mất kết nối tới máy chủ, đang thử lại" description="Việc mới có thể chưa hiện." collapsible={false} />}

      {secMine.length > 0 && (
        <section className="flex flex-col gap-2" aria-label="Cảnh báo an ninh">
          {secMine.map((a) => (
            <SecurityCard key={a.id} a={a} actor={id} provider={settings?.provider ?? 'Gemini'} phone fresh={now - a.created_at < 4000} />
          ))}
        </section>
      )}

      <AnimatedList items={mine} getKey={(a) => a.id} className="fx-list" label="Việc của bạn">
        {(a) => <TaskCard a={a} big={a.id === topId} now={now} me={id} />}
      </AnimatedList>

      {mine.length === 0 && secMine.length === 0 && (
        <div className="fx-item flex flex-1 flex-col items-center justify-center gap-4 py-10 text-center">
          <div className="fx-radar" aria-hidden="true">
            <i />
            <i />
            <i />
            <span>
              <BellRing size={22} />
            </span>
          </div>
          <Text type="large" weight="semibold" as="p">
            {owner ? 'Đang trông quán, chưa có cảnh báo' : 'Đang trực, chưa có việc'}
          </Text>
        </div>
      )}
      </StaffTeam>
    </PhoneFrame>
  );
}

/** App nhân viên: /nv để chọn tên, /nv/:id cho từng người */
export default function StaffPhone() {
  const { id } = useParams();
  if (!id) return <PickStaff />;
  return <StaffShift key={id} id={id} />;
}
