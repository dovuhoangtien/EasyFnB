import { useEffect, useState, type ReactNode } from 'react';
import { NavLink, useLocation } from 'react-router';
import {
  Cctv,
  FileText,
  Headphones,
  LayoutGrid,
  Menu,
  MessagesSquare,
  Pause,
  Play,
  Radio,
  ScanEye,
  Settings2,
  Sparkles,
  UserRound,
  Users,
  Volume2,
  VolumeX,
  X,
} from 'lucide-react';
import { ConnBadge } from '../live/ui';
import { useLive, useServerNow } from '../live/store';
import { clockTime } from '../live/text';
import { useSim } from '../sim/store';
import { setListenAll, useVoice } from '../sim/voice';
import { clock } from '../sim/util';
import { useToast } from './ui';

// Chạy thật: dữ liệu từ máy chủ và camera
const LIVE_LINKS = [
  { to: '/truc-tiep', label: 'Bảng trực tiếp', icon: Radio },
  { to: '/truc-tiep/cai-dat', label: 'Cài đặt camera', icon: Settings2 },
  { to: '/truc-tiep/tro-ly', label: 'Trợ lý AI', icon: Sparkles },
];

// Bản mô phỏng
const LINKS = [
  { to: '/', label: 'Tổng quan', icon: LayoutGrid },
  { to: '/camera', label: 'Camera AI', icon: Cctv },
  { to: '/nhan-vien', label: 'Nhân viên', icon: Users },
  { to: '/app-nhan-vien', label: 'App nhân viên', icon: Headphones },
  { to: '/khach-quen', label: 'Khách quen', icon: UserRound },
  { to: '/tro-ly', label: 'Trợ lý AI', icon: MessagesSquare },
  { to: '/bao-cao', label: 'Báo cáo ca', icon: FileText },
];

const SPEEDS = [1, 5, 20];

function Brand() {
  return (
    <NavLink to="/" className="brand" aria-label="Easy FnB, về trang tổng quan">
      <span className="brand-mark" aria-hidden="true">
        <ScanEye size={16} strokeWidth={2.2} />
      </span>
      <span className="brand-text">Easy FnB</span>
    </NavLink>
  );
}

const SIM_NOTE = 'Bản demo chưa nối camera thật. Mọi số liệu do bộ mô phỏng tạo ra theo thời gian thực.';
const LIVE_NOTE = 'Dữ liệu thật: camera gửi sự kiện về máy chủ, nhân viên nhận việc trên điện thoại.';

/** Đồng hồ thật và trạng thái kết nối, thay cho đồng hồ mô phỏng ở các trang trực tiếp */
function LiveShift({ menu }: { menu: ReactNode }) {
  const now = useServerNow();
  const status = useLive((s) => s.status);
  return (
    <>
      <div className="shift">
        <span className="shift-label small muted">Giờ hiện tại</span>
        <span className="measured cool" aria-label="Giờ hiện tại">
          {clockTime(now)}
        </span>
      </div>
      <div className="topbar-tools">
        <ConnBadge status={status} />
        {menu}
      </div>
    </>
  );
}

export function Shell({ children }: { children: ReactNode }) {
  const e = useSim();
  const voice = useVoice();
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const location = useLocation();
  const isLive = location.pathname === '/truc-tiep' || location.pathname.startsWith('/truc-tiep/');

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [location.pathname]);

  const anyChannel = voice.listening.length > 0;
  const toggleVoice = () => {
    setListenAll(!anyChannel);
    if (anyChannel) return;
    if (!voice.supported) toast('Trình duyệt này không đọc được giọng nói, chỉ có tiếng chuông.');
    else if (!voice.hasVoice && voice.lang === 'vi') toast('Máy chưa có giọng tiếng Việt. Vào App nhân viên để chuyển sang English.');
    else toast('Đang nghe tất cả kênh. Chọn từng người ở trang App nhân viên.');
  };

  const navGroup = (title: string, list: typeof LINKS) => (
    <div className="nav-group" role="group" aria-label={title}>
      <span className="nav-label" aria-hidden="true">
        {title}
      </span>
      {list.map(({ to, label, icon: Icon }) => (
        <NavLink key={to} to={to} end={to === '/' || to === '/truc-tiep'}>
          <Icon size={16} aria-hidden="true" />
          {label}
        </NavLink>
      ))}
    </div>
  );
  const links = (
    <>
      {navGroup('Trực tiếp', LIVE_LINKS)}
      {navGroup('Mô phỏng', LINKS)}
    </>
  );

  const menuToggle = (
    <button
      type="button"
      className="btn btn--icon menu-toggle"
      aria-expanded={open}
      aria-controls="mobile-nav"
      aria-label={open ? 'Đóng menu' : 'Mở menu'}
      onClick={() => setOpen((v) => !v)}
    >
      {open ? <X size={18} aria-hidden="true" /> : <Menu size={18} aria-hidden="true" />}
    </button>
  );

  return (
    <div className="app">
      <aside className="side">
        <Brand />
        <nav className="nav" aria-label="Điều hướng chính">
          {links}
        </nav>
        <div className="side-foot">
          {isLive ? <span className="chip chip--ok">Dữ liệu thật</span> : <span className="chip chip--cool">Dữ liệu mô phỏng</span>}
          <p>{isLive ? LIVE_NOTE : SIM_NOTE}</p>
        </div>
      </aside>

      <div className="main-col">
        <header className="topbar">
          <Brand />
          {isLive ? (
            <LiveShift menu={menuToggle} />
          ) : (
            <>
              <div className="shift">
                <span className="shift-label small muted">Ca tối, giờ hiện tại</span>
                <span className="measured cool" aria-label="Giờ trong ca">
                  {clock(e.t)}
                </span>
              </div>
              <div className="topbar-tools">
                <div className="seg speed" role="group" aria-label="Tốc độ mô phỏng">
                  {SPEEDS.map((s) => (
                    <button
                      key={s}
                      type="button"
                      aria-pressed={e.speed === s}
                      onClick={() => e.setSpeed(s)}
                    >
                      {s}×
                    </button>
                  ))}
                </div>
                <button
                  type="button"
                  className="btn btn--icon"
                  aria-label={e.running ? 'Tạm dừng mô phỏng' : 'Chạy tiếp mô phỏng'}
                  onClick={() => e.toggleRunning()}
                >
                  {e.running ? <Pause size={16} aria-hidden="true" /> : <Play size={16} aria-hidden="true" />}
                </button>
                <button type="button" className="btn" aria-pressed={anyChannel} aria-label="Giọng đọc thông báo" onClick={toggleVoice}>
                  {anyChannel ? <Volume2 size={16} aria-hidden="true" /> : <VolumeX size={16} aria-hidden="true" />}
                  <span className="voice-label">Giọng đọc</span>
                </button>
                {menuToggle}
              </div>
            </>
          )}
          <nav id="mobile-nav" className="nav mobile-nav" data-open={open} aria-label="Điều hướng chính" onClick={() => setOpen(false)}>
            {links}
            <p className="tiny muted px-3 py-2">{isLive ? LIVE_NOTE : SIM_NOTE}</p>
          </nav>
        </header>
        <main>{children}</main>
      </div>
    </div>
  );
}
