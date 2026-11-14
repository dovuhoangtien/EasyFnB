import { useCallback, useEffect, useState } from 'react';
import { useToast } from '@astryxdesign/core/Toast';
import { errorMessage, getInfo, getReport, savedPin, type Info } from './api';
import type { Report } from './types';

/** Số liệu ca từ /api/report, tự làm mới theo chu kỳ */
export function useReport(intervalMs = 10000) {
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    let alive = true;
    const load = () => {
      getReport()
        .then((r) => {
          if (!alive) return;
          setReport(r);
          setError(null);
        })
        .catch((err: unknown) => {
          if (alive) setError(errorMessage(err));
        });
    };
    load();
    const timer = window.setInterval(load, intervalMs);
    return () => {
      alive = false;
      window.clearInterval(timer);
    };
  }, [intervalMs, nonce]);

  const refresh = useCallback(() => setNonce((n) => n + 1), []);
  return { report, error, loading: report === null && error === null, refresh };
}

/**
 * Chạy một thao tác gọi máy chủ: nhớ nút nào đang chờ, báo lỗi bằng toast.
 * Trả về kết quả, hoặc undefined nếu lỗi.
 */
export function useRun() {
  const toast = useToast();
  const [busy, setBusy] = useState<string | null>(null);
  const run = useCallback(
    async <T>(key: string, fn: () => Promise<T>, okMessage?: string): Promise<T | undefined> => {
      setBusy(key);
      try {
        const out = await fn();
        if (okMessage) toast({ body: okMessage });
        return out;
      } catch (err) {
        toast({ body: errorMessage(err), type: 'error', isAutoHide: true, autoHideDuration: 6000 });
        return undefined;
      } finally {
        setBusy((b) => (b === key ? null : b));
      }
    },
    [toast],
  );
  return { busy, run };
}

/** Tiêu đề tab trình duyệt */
export function useTitle(title: string) {
  useEffect(() => {
    const before = document.title;
    document.title = title;
    return () => {
      document.title = before;
    };
  }, [title]);
}

/** Tình trạng hệ thống từ /api/info, tự làm mới; null khi chưa lấy được */
export function useInfo(intervalMs = 15000) {
  const [info, setInfo] = useState<Info | null>(null);
  const [nonce, setNonce] = useState(0);
  useEffect(() => {
    let alive = true;
    const load = () => {
      getInfo()
        .then((i) => {
          if (alive) setInfo(i);
        })
        .catch(() => {
          // mất kết nối: giữ số cũ, thanh trạng thái đã báo
        });
    };
    load();
    const timer = window.setInterval(load, intervalMs);
    return () => {
      alive = false;
      window.clearInterval(timer);
    };
  }, [intervalMs, nonce]);
  const refresh = useCallback(() => setNonce((n) => n + 1), []);
  return { info, refresh };
}

/**
 * Chạy một việc cần PIN chủ quán: đã nhập trong phiên này thì chạy luôn, chưa thì mở hộp hỏi PIN.
 * Trả về withPin và pinProps để gắn vào <PinDialog {...pinProps} />.
 */
export function useOwnerPin() {
  const [pending, setPending] = useState<{ fn: (pin: string) => void } | null>(null);
  const withPin = useCallback((fn: (pin: string) => void) => {
    const p = savedPin();
    if (p) fn(p);
    else setPending({ fn });
  }, []);
  const pinProps = {
    isOpen: pending !== null,
    onClose: () => setPending(null),
    onOk: (pin: string) => {
      const fn = pending?.fn;
      setPending(null);
      fn?.(pin);
    },
  };
  return { withPin, pinProps };
}
