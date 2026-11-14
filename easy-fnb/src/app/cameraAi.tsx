import { useEffect, useState } from 'react';
import { Button } from '@astryxdesign/core/Button';
import { Text } from '@astryxdesign/core/Text';
import { errorMessage, getCameraAi, isPinError, savedPin, setCameraAi, type CameraAi } from '../live/api';
import { PinDialog } from './ownerPin';

/**
 * Nút bật/tắt camera AI chạy trên chính máy chủ. Có điện thoại đang phát ở /phat thì dùng điện thoại,
 * không thì chạy video mẫu. Máy chủ không chạy được (Cloud Run) thì không hiện gì.
 * Model cần ~20 giây để nạp, nên sau khi bấm hiện "Đang mở" cho tới khi hình về.
 */
export function CameraAiButton({ live, size = 'sm' }: { live: boolean; size?: 'sm' | 'md' }) {
  const [st, setSt] = useState<CameraAi | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [askPin, setAskPin] = useState<null | boolean>(null);

  useEffect(() => {
    let stop = false;
    const load = () => getCameraAi().then((s) => !stop && setSt(s), () => undefined);
    load();
    const t = window.setInterval(load, 5000);
    return () => {
      stop = true;
      window.clearInterval(t);
    };
  }, []);

  // camera đang có hình mà không do nút này bật (chạy tay bằng chay_camera.bat): ẩn để không mở trùng
  if (!st?.available || (live && !st.running)) return null;

  const run = async (on: boolean, pin = savedPin()) => {
    setBusy(true);
    setError(null);
    try {
      setSt(await setCameraAi(on, pin));
    } catch (err) {
      if (isPinError(err)) setAskPin(on);
      else setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const starting = st.running && !live;
  return (
    <div className="flex items-center gap-2 flex-wrap">
      {st.running ? (
        <Button label="Tắt camera AI" variant="ghost" size={size} isDisabled={busy} onClick={() => run(false)} />
      ) : (
        <Button label="Bật camera AI" variant="primary" size={size} isDisabled={busy} onClick={() => run(true)} />
      )}
      {starting && (
        <Text type="supporting" color="secondary" aria-live="polite">
          Đang mở camera AI{st.source === 'phone' ? ' với điện thoại' : ' với video mẫu'}, hình sẽ hiện sau khoảng 20 giây.
        </Text>
      )}
      {error && (
        <Text type="supporting" color="secondary" role="alert">
          {error}
        </Text>
      )}
      <PinDialog
        isOpen={askPin !== null}
        subtitle="Chỉ chủ quán bật hay tắt được camera AI."
        onClose={() => setAskPin(null)}
        onOk={(pin) => {
          const on = askPin;
          setAskPin(null);
          if (on !== null) void run(on, pin);
        }}
      />
    </div>
  );
}
