import { useCallback, useEffect, useLayoutEffect, useState } from 'react';
import { useLocation, useNavigate, useSearchParams } from 'react-router';
import { Button } from '@astryxdesign/core/Button';
import { Text } from '@astryxdesign/core/Text';
import { useLive } from '../live/store';

interface Step {
  path: string;
  /** phần tử được làm nổi; không thấy (thanh bên đang ẩn trên điện thoại) thì hiện hộp giữa màn hình */
  target?: string;
  title: string;
  body: string;
}

const STEPS: Step[] = [
  {
    path: '/',
    title: 'Chào mừng tới Easy FnB',
    body: 'Đây là bản demo đang chạy thật: camera AI trông quán và báo việc tới điện thoại nhân viên. Hình là clip quay ở quán thử, mặt người đã được che. Xem nhanh 6 bước nhé.',
  },
  {
    path: '/',
    target: '[data-tour="cam"]',
    title: 'Camera của quán',
    body: 'AI theo dõi từng bàn đã khoanh. Bàn có khách, cần dọn hay đang gọi phục vụ được tô màu ngay trên hình.',
  },
  {
    path: '/',
    target: '[data-tour="tasks"]',
    title: 'Việc tự hiện khi camera thấy',
    body: 'Khách giơ tay gọi, khách mới vào, bàn cần dọn: máy chủ tạo việc và giao cho nhân viên rảnh. Trong demo, nhân viên trong clip nhận việc trên điện thoại rồi tới bàn, camera tự đóng việc. Bạn cũng có thể bấm Xong, Chuyển người hay Tạo việc.',
  },
  {
    path: '/',
    target: '[data-tour="strip"]',
    title: 'Quán lúc này trong một dòng',
    body: 'Số việc đang chờ, bàn có khách, bàn cần dọn và nhân viên đang trực, cập nhật trực tiếp.',
  },
  {
    path: '/',
    target: '[data-tour="staff-app"]',
    title: 'App trên điện thoại nhân viên',
    body: 'Mở mục này, quét mã QR bằng điện thoại để làm nhân viên: máy rung và đọc to “Bàn B6 gọi phục vụ”, bấm Nhận rồi Xong. Việc giao cho bạn sẽ chờ bạn bấm.',
  },
  {
    path: '/tro-ly',
    target: '.fx-chat-page',
    title: 'Hỏi trợ lý bằng tiếng Việt',
    body: 'Thử hỏi: “Hôm nay quán thế nào?”, “Ai phục vụ nhanh nhất?”, “Có ai nhận việc mà không tới bàn không?”. Trợ lý dùng Gemini, trả lời kèm số liệu và clip.',
  },
  {
    path: '/ca',
    target: '.fx-page',
    title: 'Ca hôm nay',
    body: 'Cuối ca chủ quán xem tốc độ phục vụ, ai làm bao nhiêu việc, việc nào bị chậm. Vậy là xong, giờ bạn tự khám phá nhé!',
  },
];

const KEY = 'easyfnb.tour.v1';
const PAD = 8;

/** Hướng dẫn từng bước cho người mới mở bản demo; lần đầu tự hiện, sau đó mở lại bằng nút Hướng dẫn */
export function useTour() {
  const [open, setOpen] = useState(false);
  const [params, setParams] = useSearchParams();
  const loaded = useLive((s) => s.loaded);
  useEffect(() => {
    if (!loaded) return;
    if (params.get('tour') === '1') {
      params.delete('tour');
      setParams(params, { replace: true });
      setOpen(true);
    } else if (!localStorage.getItem(KEY)) setOpen(true);
  }, [loaded]); // eslint-disable-line react-hooks/exhaustive-deps
  return { open, start: () => setOpen(true), stop: () => setOpen(false) };
}

function useRect(selector: string | undefined, path: string) {
  const [rect, setRect] = useState<DOMRect | null>(null);
  useLayoutEffect(() => {
    setRect(null);
    if (!selector) return;
    let scrolled = false;
    const measure = () => {
      const el = document.querySelector(selector);
      const r = el?.getBoundingClientRect();
      if (!el || !r || r.width === 0 || r.height === 0) return setRect(null);
      if (!scrolled) {
        scrolled = true;
        el.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      }
      setRect((old) => (old && old.x === r.x && old.y === r.y && old.width === r.width && old.height === r.height ? old : r));
    };
    measure();
    const t = window.setInterval(measure, 250);
    window.addEventListener('resize', measure);
    return () => {
      window.clearInterval(t);
      window.removeEventListener('resize', measure);
    };
  }, [selector, path]);
  return rect;
}

export function Tour({ onClose }: { onClose: () => void }) {
  const [i, setI] = useState(0);
  const step = STEPS[i];
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const here = pathname === step.path;
  const rect = useRect(here ? step.target : undefined, pathname);

  useEffect(() => {
    if (!here) navigate(step.path);
  }, [here, step.path, navigate]);

  const close = useCallback(() => {
    localStorage.setItem(KEY, 'done');
    onClose();
  }, [onClose]);

  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close();
      else if (e.key === 'ArrowRight') setI((n) => Math.min(STEPS.length - 1, n + 1));
      else if (e.key === 'ArrowLeft') setI((n) => Math.max(0, n - 1));
    };
    window.addEventListener('keydown', key);
    return () => window.removeEventListener('keydown', key);
  }, [close]);

  const last = i === STEPS.length - 1;
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const w = Math.min(380, vw - 24);
  let pos: React.CSSProperties;
  if (!rect || vw < 640) {
    pos = rect ? { left: 12, right: 12, bottom: 12 } : { left: (vw - w) / 2, top: Math.max(12, vh / 2 - 140) };
  } else {
    const below = vh - rect.bottom > 230;
    const right = vw - rect.right > w + 24;
    pos = right && rect.height > 200
      ? { left: rect.right + 16, top: Math.min(Math.max(12, rect.top), vh - 260) }
      : below
        ? { left: Math.min(Math.max(12, rect.left), vw - w - 12), top: rect.bottom + 14 }
        : { left: Math.min(Math.max(12, rect.left), vw - w - 12), top: Math.max(12, rect.top - 244) };
  }

  return (
    <div className="fx-tour" role="dialog" aria-modal="true" aria-labelledby="fx-tour-title">
      {rect ? (
        <div
          className="fx-tour-hole"
          style={{ left: rect.left - PAD, top: rect.top - PAD, width: rect.width + 2 * PAD, height: rect.height + 2 * PAD }}
          aria-hidden="true"
        />
      ) : (
        <div className="fx-tour-dim" aria-hidden="true" />
      )}
      <div className="fx-tour-card" style={{ ...pos, width: vw < 640 && rect ? undefined : w }}>
        <Text type="supporting" color="secondary" as="p">
          Bước {i + 1}/{STEPS.length}
        </Text>
        <Text type="large" weight="semibold" as="h2" id="fx-tour-title">
          {step.title}
        </Text>
        <Text type="body" as="p">
          {step.body}
        </Text>
        <div className="flex items-center gap-2" style={{ marginTop: 4 }}>
          <Button label="Bỏ qua" variant="ghost" size="sm" onClick={close} />
          <span className="flex-1" />
          {i > 0 && <Button label="Quay lại" variant="secondary" size="sm" onClick={() => setI(i - 1)} />}
          <Button label={last ? 'Bắt đầu dùng' : i === 0 ? 'Xem hướng dẫn' : 'Tiếp'} variant="primary" size="sm" 
            onClick={() => {
              if (!last) return setI(i + 1);
              close();
              navigate('/');
            }}
          />
        </div>
      </div>
    </div>
  );
}
