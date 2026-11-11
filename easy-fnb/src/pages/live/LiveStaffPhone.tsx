import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { Link, useParams } from 'react-router';
import { BellRing, ChevronRight, ScanEye, TriangleAlert } from 'lucide-react';
import { useTitle } from '../../live/hooks';
import { live, useLive, useLiveConnection, useServerNow } from '../../live/store';
import { ageText, byUrgency, ROLE_LABEL, staffName, tableText } from '../../live/text';
import { ConnBadge, CropImg, ItemsLeft, KindChip } from '../../live/ui';
import { createNotifier } from '../../live/notifier';
import { beep, hasVietnameseVoice, speak, speechSupported, unlockAudio, vibrate } from '../../live/voice';
import type { Alert, AlertKind } from '../../live/types';

/** Việc nói bằng lời cho nhân viên */
const KIND_TODO: Record<AlertKind, string> = {
  call: 'Khách giơ tay gọi phục vụ',
  needs_clearing: 'Bàn cần dọn',
  new_guest: 'Khách mới ngồi, chào và đưa thực đơn',
};

const NOTICE_MS = 7000;

const mineActive = (a: Alert, me: string) => a.assigned_to === me && (a.status === 'open' || a.status === 'acked');

function PhoneBar({ children }: { children?: ReactNode }) {
  return (
    <header className="phone-bar">
      <span className="brand">
        <span className="brand-mark" aria-hidden="true">
          <ScanEye size={16} strokeWidth={2.2} />
        </span>
        Easy FnB
      </span>
      {children}
    </header>
  );
}

// ---------- chọn tên ----------
function PickStaff() {
  useLiveConnection();
  useTitle('Easy FnB cho nhân viên');
  const status = useLive((s) => s.status);
  const loaded = useLive((s) => s.loaded);
  const staff = useLive((s) => s.staff);

  return (
    <div className="phone">
      <PhoneBar>
        <ConnBadge status={status} />
      </PhoneBar>
      <section className="panel phone-who" aria-labelledby="who-title">
        <div className="panel-head">
          <h1 id="who-title">Bạn là ai?</h1>
        </div>
        {staff.length ? (
          <>
            <p className="small muted px-4 pt-3">Chọn tên để nhận việc của mình trên điện thoại này.</p>
            <ul>
              {staff.map((s) => (
                <li key={s.id}>
                  <Link to={`/nv-tt/${s.id}`}>
                    <span className="avatar avatar--sm" aria-hidden="true">
                      {s.name.charAt(0)}
                    </span>
                    <span className="flex flex-col">
                      <span className="ink2">{s.name}</span>
                      <span className="tiny muted">
                        {ROLE_LABEL[s.role]}
                        {s.online ? ', đang mở app' : ''}
                      </span>
                    </span>
                    <ChevronRight size={18} aria-hidden="true" className="ml-auto muted" />
                  </Link>
                </li>
              ))}
            </ul>
          </>
        ) : (
          <p className="small muted p-4">
            {loaded ? 'Chưa có nhân viên nào. Nhờ quản lý thêm tên ở trang Cài đặt trực tiếp.' : 'Đang kết nối tới máy chủ của quán…'}
          </p>
        )}
      </section>
      <p className="tiny muted phone-foot">App nhân viên, dữ liệu thật từ camera của quán.</p>
    </div>
  );
}

// ---------- một việc ----------
function TaskCard({ a, big, now }: { a: Alert; big: boolean; now: number }) {
  return (
    <article className="panel pcard" data-big={big || undefined} data-kind={a.kind} aria-label={`${KIND_TODO[a.kind]}, ${tableText(a.table)}`}>
      <div className="flex items-center gap-2 flex-wrap">
        <KindChip kind={a.kind} />
        {a.escalated && (
          <span className="chip chip--bad">
            <TriangleAlert size={12} aria-hidden="true" />
            Gấp
          </span>
        )}
        {a.verify.state === 'pending' && <span className="chip chip--cool">AI đang kiểm tra</span>}
        {a.verify.state === 'unverified' && <span className="chip chip--p2">Chưa xác minh</span>}
        <span className="measured cool ml-auto" aria-label={`Đã chờ ${ageText(now - a.created_at)}`}>
          {ageText(now - a.created_at)}
        </span>
      </div>
      <p className="sapp-table">{tableText(a.table)}</p>
      <p className={big ? 'sapp-what' : 'ink2'}>{KIND_TODO[a.kind]}</p>
      {a.kind === 'needs_clearing' && <ItemsLeft items={a.items} />}
      {a.kind === 'call' && a.crop_url && <CropImg url={a.crop_url} alt={`Ảnh camera lúc khách gọi, ${tableText(a.table)}`} className={big ? 'crop--lg' : 'crop--md'} />}
    </article>
  );
}

// ---------- ca làm của một người ----------
interface Notice {
  id: number;
  text: string;
  tone: 'bad' | 'info';
}

function StaffShift({ id }: { id: string }) {
  const [started, setStarted] = useState(false);
  useLiveConnection(started ? id : null);
  const status = useLive((s) => s.status);
  const loaded = useLive((s) => s.loaded);
  const staff = useLive((s) => s.staff);
  const alerts = useLive((s) => s.alerts);
  const now = useServerNow();
  const me = staff.find((s) => s.id === id);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [noVoice, setNoVoice] = useState(false);
  const wake = useRef<WakeLockSentinel | null>(null);
  const staffRef = useRef(staff);
  useTitle(me ? `${me.name}, Easy FnB` : 'Easy FnB cho nhân viên');

  useEffect(() => {
    staffRef.current = staff;
  }, [staff]);

  const mine = useMemo(() => alerts.filter((a) => mineActive(a, id)).sort(byUrgency), [alerts, id]);

  // Có việc mới thì kêu, rung, đọc; việc bị huỷ hay chuyển thì báo ngắn
  const alertsRef = useRef(alerts);
  useEffect(() => {
    alertsRef.current = alerts;
  }, [alerts]);

  useEffect(() => {
    if (!started) return;
    // gom, xếp thứ tự ưu tiên và giãn cách các thông báo (xem live/notifier.ts)
    const notifier = createNotifier((a) => {
      const cur = alertsRef.current.find((x) => x.id === a.id) ?? a;
      return mineActive(cur, id);
    });
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
        const byGemini = next.verify.state === 'rejected';
        const reason = byGemini ? 'báo nhầm' : (next.cancel_reason ?? 'báo nhầm');
        const why = byGemini && next.verify.reason ? ` AI: ${next.verify.reason}.` : '';
        beep('cancel');
        vibrate(220);
        setNotice({ id: Date.now(), tone: 'bad', text: `Đã huỷ: ${reason}. ${where}.${why}` });
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

  // Thông báo ngắn tự ẩn
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
        // bỏ qua: máy không cho giữ màn hình
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
    window.setTimeout(() => {
      setNoVoice(!speechSupported() || !hasVietnameseVoice());
      beep('normal');
      speak(n ? `Bắt đầu ca. Bạn có ${n} việc đang chờ.` : 'Bắt đầu ca. Có việc mới điện thoại sẽ đọc to.');
    }, 150);
  };

  if (loaded && !me) {
    return (
      <div className="phone">
        <PhoneBar>
          <ConnBadge status={status} />
        </PhoneBar>
        <section className="panel phone-sound">
          <h1>Không tìm thấy nhân viên “{id}”</h1>
          <p className="small ink2">Có thể quản lý đã đổi danh sách nhân viên. Chọn lại tên của bạn.</p>
          <Link className="btn btn--primary btn--lg" to="/nv-tt">
            Chọn tên
          </Link>
        </section>
      </div>
    );
  }

  if (!started) {
    return (
      <div className="phone">
        <PhoneBar>
          <ConnBadge status={status} />
        </PhoneBar>
        <section className="panel phone-sound" aria-labelledby="start-title">
          <h1 id="start-title">{me ? `Chào ${me.name}` : status === 'offline' ? 'Chưa kết nối được máy chủ' : 'Đang kết nối…'}</h1>
          {!me && status === 'offline' ? (
            <p className="small ink2">Kiểm tra điện thoại đang dùng cùng Wi-Fi với máy chủ của quán. Trang sẽ tự kết nối lại.</p>
          ) : (
            <p className="small ink2">
              Bấm Bắt đầu ca để điện thoại kêu, rung và đọc to khi có việc cho bạn. Giữ trang này mở và để âm lượng to trong suốt ca.
            </p>
          )}
          {me && <p className="tiny muted">Vai trò: {ROLE_LABEL[me.role]}</p>}
          <button type="button" className="btn btn--primary btn--lg" disabled={!me} onClick={start}>
            <BellRing size={18} aria-hidden="true" />
            Bắt đầu ca
          </button>
        </section>
        <p className="tiny muted phone-foot">
          Không phải bạn? <Link to="/nv-tt">Chọn tên khác</Link>
        </p>
      </div>
    );
  }

  const [top, ...rest] = mine;

  return (
    <div className="phone">
      <PhoneBar>
        <ConnBadge status={status} />
      </PhoneBar>
      <div className="phone-me">
        <span className="avatar avatar--sm" aria-hidden="true">
          {me?.name.charAt(0)}
        </span>
        <div className="min-w-0 flex-1">
          <p className="ink2">{me?.name}</p>
          <p className="tiny muted">{me ? ROLE_LABEL[me.role] : ''}</p>
        </div>
      </div>

      {noVoice && <p className="tiny muted">Máy chưa có giọng đọc tiếng Việt, chỉ có tiếng chuông và rung.</p>}

      <div aria-live="assertive">
        {notice && (
          <div key={notice.id} className="panel phone-notice" data-tone={notice.tone} role="alert">
            {notice.text}
          </div>
        )}
      </div>

      {status === 'offline' && (
        <div className="panel phone-notice" data-tone="bad">
          Mất kết nối tới máy chủ, đang thử lại. Việc mới có thể chưa hiện.
        </div>
      )}

      {top ? (
        <>
          <TaskCard a={top} big now={now} />
          {rest.length > 0 && (
            <section className="phone-section" aria-labelledby="more-title">
              <h2 id="more-title">Việc tiếp theo ({rest.length})</h2>
              {rest.map((a) => (
                <TaskCard key={a.id} a={a} big={false} now={now} />
              ))}
            </section>
          )}
        </>
      ) : (
        <section className="panel phone-idle">
          <p className="sapp-table sapp-idle">Chưa có việc</p>
          <p className="small muted">Điện thoại sẽ kêu và đọc to khi camera thấy khách cần bạn. Giữ màn hình mở.</p>
        </section>
      )}

      <p className="tiny muted phone-foot">Dữ liệu thật từ camera của quán.</p>
    </div>
  );
}

/** App nhân viên chạy thật: /nv-tt để chọn tên, /nv-tt/:id cho từng người */
export default function LiveStaffPhone() {
  const { id } = useParams();
  if (!id) return <PickStaff />;
  return <StaffShift key={id} id={id} />;
}
