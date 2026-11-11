import { useState } from 'react';
import { Check, Copy, ImageOff, Loader, WifiOff } from 'lucide-react';
import { useToast } from '../components/ui';
import { apiUrl } from './api';
import type { ConnStatus } from './store';
import { CAMERA_AGENT_CMD, KIND_CHIP, KIND_LABEL, verifyBadge } from './text';
import type { AlertKind, Evidence, LeftItem, Verify } from './types';

/** Trạng thái kết nối tới máy chủ */
export function ConnBadge({ status }: { status: ConnStatus }) {
  return (
    <span role="status" aria-live="polite" className="conn">
      {status === 'live' ? (
        <span className="chip chip--ok">
          <span className="live-dot" aria-hidden="true" />
          Trực tiếp
        </span>
      ) : status === 'offline' ? (
        <span className="chip chip--bad">
          <WifiOff size={13} aria-hidden="true" />
          Mất kết nối
        </span>
      ) : (
        <span className="chip">
          <Loader size={13} aria-hidden="true" className="spin" />
          Đang kết nối
        </span>
      )}
    </span>
  );
}

export function KindChip({ kind }: { kind: AlertKind }) {
  return <span className={KIND_CHIP[kind]}>{KIND_LABEL[kind]}</span>;
}

export function VerifyChip({ verify, ten }: { verify: Verify | null | undefined; ten?: string }) {
  const b = verifyBadge(verify, ten);
  return (
    <span className={b.cls} title={verify?.reason ?? undefined}>
      {b.label}
    </span>
  );
}

/** Ảnh cắt của sự kiện; ảnh lỗi thì hiện ô trống thay vì biểu tượng vỡ */
export function CropImg({ url, alt, className }: { url: string | null; alt: string; className?: string }) {
  const [failed, setFailed] = useState<string | null>(null);
  if (!url || failed === url) {
    return (
      <span className={`crop crop--empty ${className ?? ''}`} aria-hidden={!url}>
        <ImageOff size={18} aria-hidden="true" />
        <span className="visually-hidden">Không có ảnh</span>
      </span>
    );
  }
  return <img className={`crop ${className ?? ''}`} src={apiUrl(url)} alt={alt} loading="lazy" onError={() => setFailed(url)} />;
}

/** Đồ còn trên bàn, ví dụ "2 dĩa, 1 chai"; không có gì để nói thì không hiện */
export function ItemsLeft({ items }: { items: LeftItem[] | null | undefined }) {
  if (!items?.length) return null;
  return (
    <p className="small ink2 items-left">
      Còn trên bàn:{' '}
      {items.map((it, i) => (
        <span key={it.name}>
          {i > 0 && ', '}
          <span className="measured">{it.count}</span> {it.name}
        </span>
      ))}
    </p>
  );
}

const EVIDENCE_LABEL: { key: keyof Evidence; label: string }[] = [
  { key: 'strip', label: 'Dải 4 khung quanh sự kiện' },
  { key: 'overview', label: 'Toàn cảnh, khách khoanh đỏ' },
  { key: 'ref', label: 'Ảnh bàn sạch để so' },
];

/** Ảnh bằng chứng Gemini đã xem; chỉ hiện khi camera có gửi */
export function EvidenceView({ evidence, label }: { evidence: Evidence | null | undefined; label: string }) {
  const shown = EVIDENCE_LABEL.filter((e) => evidence?.[e.key]);
  if (!evidence || !shown.length) return null;
  return (
    <details className="evidence">
      <summary className="small">Xem ảnh bằng chứng</summary>
      <div className="evidence-grid">
        {shown.map((e) => (
          <figure key={e.key} className="evidence-fig">
            <CropImg url={evidence[e.key]} alt={`${e.label}: ${label}`} className="crop--lg" />
            <figcaption className="tiny muted">{e.label}</figcaption>
          </figure>
        ))}
      </div>
    </details>
  );
}

/** Hộp lệnh chạy máy camera, có nút chép */
export function AgentCommand({ compact = false }: { compact?: boolean }) {
  const toast = useToast();
  const [copied, setCopied] = useState(false);
  const host = typeof location !== 'undefined' ? location.hostname : 'localhost';
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(CAMERA_AGENT_CMD);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      toast('Không chép được, hãy bôi đen lệnh rồi chép tay.');
    }
  };
  return (
    <div className="agent-cmd">
      <div className="flex items-start gap-2">
        <pre className="code flex-1 min-w-0" aria-label="Lệnh chạy máy camera">
          {CAMERA_AGENT_CMD}
        </pre>
        <button type="button" className="btn btn--icon" onClick={() => void copy()} aria-label="Chép lệnh">
          {copied ? <Check size={16} aria-hidden="true" /> : <Copy size={16} aria-hidden="true" />}
        </button>
      </div>
      {!compact && (
        <p className="tiny muted mt-2">
          Chạy trong thư mục <span className="measured">vision-test</span>. Nếu máy chủ chạy trên chính máy này, địa chỉ là{' '}
          <span className="measured cool">http://{host === 'localhost' || host === '127.0.0.1' ? 'localhost' : host}:8080</span>.
        </p>
      )}
    </div>
  );
}
