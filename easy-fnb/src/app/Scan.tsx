import { useEffect, useMemo, useRef, useState } from 'react';
import { Camera, Check, RotateCcw, Sparkles, X } from 'lucide-react';
import { Banner } from '@astryxdesign/core/Banner';
import { Button } from '@astryxdesign/core/Button';
import { IconButton } from '@astryxdesign/core/IconButton';
import { NumberInput } from '@astryxdesign/core/NumberInput';
import { ProgressBar } from '@astryxdesign/core/ProgressBar';
import { Selector } from '@astryxdesign/core/Selector';
import { Text } from '@astryxdesign/core/Text';
import { TextInput } from '@astryxdesign/core/TextInput';
import { errorMessage } from '../live/api';
import { money, PAYMENT_TYPE_LABEL, scanPayment, sendScan, shrinkPhoto, type ChatMsg, type PaymentFields, type PaymentType, type ScanResult } from '../live/chat';
import { useLive } from '../live/store';
import { byName } from '../live/text';
import { Roll } from './motion';

type Step = 'scanning' | 'result' | 'error';

/** Các chặng của thanh tiến trình: tải ảnh lên (thật) rồi chờ máy chủ đọc ảnh (ước lượng, chậm dần, không bao giờ tự đầy) */
const UPLOAD_SHARE = 30;
const READ_CAP = 94;
const READ_TAU_MS = 3200;

function stageText(p: number) {
  if (p < UPLOAD_SHARE) return 'Đang gửi ảnh lên máy chủ';
  if (p < 60) return 'Đang tìm số tiền';
  if (p < 85) return 'Đang đọc chi tiết';
  return 'Đang kiểm tra lại';
}

interface TableChoice {
  id: string;
  /** đang có khách theo camera */
  busy: boolean;
  /** khách đã ăn xong, có thể đang chờ tính tiền */
  paying: boolean;
}

/** Bàn để chọn: bàn đã ăn xong lên đầu, rồi bàn đang có khách, rồi bàn trống */
function useTableChoices(): TableChoice[] {
  const zones = useLive((s) => s.zones);
  const states = useLive((s) => s.tables);
  return useMemo(() => {
    const ids = [...new Set(zones.flatMap((z) => z.tables.map((t) => t.id)))];
    const out = ids.map((id) => {
      const st = states.filter((t) => t.id === id);
      return { id, busy: st.some((t) => t.state === 'occupied' || !!t.stage), paying: st.some((t) => t.stage === 'finished') };
    });
    const rank = (t: TableChoice) => (t.paying ? 0 : t.busy ? 1 : 2);
    return out.sort((a, b) => rank(a) - rank(b) || byName(a.id, b.id));
  }, [zones, states]);
}

/** Bàn nào vừa ăn xong (đúng một bàn) thì gợi ý luôn: hoá đơn thường không in số bàn */
export function useLikelyTable(): string | null {
  const choices = useTableChoices();
  const paying = choices.filter((t) => t.paying);
  return paying.length === 1 ? paying[0].id : null;
}

/** Chạm chọn bàn, không bắt buộc. Chạm lại bàn đang chọn thì bỏ chọn. */
function TablePicker({ value, onChange, warning }: { value: string | null; onChange: (v: string | null) => void; warning?: string }) {
  const choices = useTableChoices();
  const pick = (v: string | null) => onChange(v);
  return (
    <fieldset className="fx-table-pick">
      <legend>
        <Text type="label">Bàn</Text>
        <Text type="supporting" color="secondary">
          {warning ? ` ${warning}` : ', để trống cũng được'}
        </Text>
      </legend>
      <div className="fx-table-pick-row">
        {choices.map((t) => (
          <button key={t.id} type="button" aria-pressed={value === t.id} data-busy={t.busy || undefined} onClick={() => pick(value === t.id ? null : t.id)}>
            {t.id}
            {t.paying && <span className="fx-table-pick-note">ăn xong</span>}
          </button>
        ))}
      </div>
    </fieldset>
  );
}

/** Ô nhập của một thanh toán: dùng cho màn xác nhận sau khi quét và khi sửa sau này */
export function PaymentForm({ value, onChange, unsure = [] }: { value: PaymentFields; onChange: (v: PaymentFields) => void; unsure?: (keyof PaymentFields)[] }) {
  const set = <K extends keyof PaymentFields>(k: K, v: PaymentFields[K]) => onChange({ ...value, [k]: v });
  const warn = (k: keyof PaymentFields, msg = 'Chưa chắc, xem lại') => (unsure.includes(k) ? { type: 'warning' as const, message: msg } : undefined);
  const isTransfer = value.type === 'chuyen_khoan';
  const isBill = value.type === 'hoa_don' || value.type === 'phieu_thu';
  const itemsTotal = value.items.reduce((s, i) => s + i.qty * i.price, 0);
  return (
    <div className="fx-scan-form">
      <Selector
        label="Loại"
        value={value.type}
        onChange={(v) => set('type', v as PaymentType)}
        options={(['chuyen_khoan', 'hoa_don', 'phieu_thu', 'khac'] as PaymentType[]).map((t) => ({ value: t, label: PAYMENT_TYPE_LABEL[t] }))}
      />
      {value.type !== 'khac' && (
        <>
          <NumberInput
            label="Số tiền"
            value={value.amount}
            hasClear
            onChange={(v) => set('amount', v)}
            units="đ"
            isIntegerOnly
            min={0}
            size="lg"
            formatValue={(n) => n.toLocaleString('vi-VN')}
            status={warn('amount', value.amount ? 'Chưa chắc số này, xem lại ảnh' : 'Nhập số tiền')}
          />
          <TablePicker value={value.table} onChange={(v) => set('table', v)} warning={unsure.includes('table') ? 'chọn lại' : undefined} />
          <TextInput label="Giờ trên ảnh" value={value.paid_at ?? ''} placeholder="14:30" inputMode="numeric" onChange={(v) => set('paid_at', v || null)} status={warn('paid_at')} />
          {isTransfer && (
            <>
              <div className="fx-scan-pair">
                <TextInput label="Ngân hàng" value={value.bank ?? ''} onChange={(v) => set('bank', v || null)} status={warn('bank')} />
                <TextInput label="Người chuyển" value={value.sender_name ?? ''} onChange={(v) => set('sender_name', v || null)} status={warn('sender_name')} />
              </div>
              <TextInput label="Nội dung chuyển khoản" value={value.memo ?? ''} onChange={(v) => set('memo', v || null)} status={warn('memo')} />
            </>
          )}
          {isBill && <TextInput label="Số hoá đơn" value={value.receipt_no ?? ''} onChange={(v) => set('receipt_no', v || null)} status={warn('receipt_no')} />}
          {isBill && value.items.length > 0 && (
            <details className="fx-scan-items">
              <summary>
                <Text type="label">
                  {value.items.length} món, cộng lại {money(itemsTotal)}
                </Text>
              </summary>
              <ul>
                {value.items.map((it, i) => (
                  <li key={i}>
                    <span>
                      {it.qty} × {it.name}
                    </span>
                    <span className="fx-num">{money(it.qty * it.price)}</span>
                  </li>
                ))}
              </ul>
            </details>
          )}
        </>
      )}
    </div>
  );
}

/**
 * Quét một ảnh thanh toán: thanh tiến trình trong lúc máy chủ đọc ảnh, rồi màn kết quả.
 * Luôn phải bấm "Xác nhận và gửi" thì mới lưu và đăng vào nhóm.
 */
export function ScanFlow({ me, file, onClose, onSent, onRetake }: { me: string; file: File; onClose: () => void; onSent: (m: ChatMsg) => void; onRetake: () => void }) {
  const [step, setStep] = useState<Step>('scanning');
  const [progress, setProgress] = useState(2);
  const [result, setResult] = useState<ScanResult | null>(null);
  const likely = useLikelyTable();
  const likelyRef = useRef(likely);
  useEffect(() => {
    likelyRef.current = likely;
  }, [likely]);
  const [fields, setFields] = useState<PaymentFields | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);
  const [preview, setPreview] = useState('');
  const dialog = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  useEffect(() => {
    dialog.current?.focus();
    const ctl = new AbortController();
    let readStart = 0;
    let timer = 0;
    const tick = () => {
      if (!readStart) return;
      const t = performance.now() - readStart;
      setProgress(UPLOAD_SHARE + (READ_CAP - UPLOAD_SHARE) * (1 - Math.exp(-t / READ_TAU_MS)));
      timer = window.setTimeout(tick, 120);
    };
    (async () => {
      try {
        const jpeg = await shrinkPhoto(file);
        const r = await scanPayment(me, jpeg, null, (f) => {
          setProgress(2 + (UPLOAD_SHARE - 2) * f);
          if (f >= 1 && !readStart) {
            readStart = performance.now();
            tick();
          }
        }, ctl.signal);
        window.clearTimeout(timer);
        readStart = 0;
        setProgress(100);
        setResult(r);
        setFields({ ...r.fields, table: r.fields.table ?? likelyRef.current });
        window.setTimeout(() => setStep('result'), 380);
      } catch (e) {
        window.clearTimeout(timer);
        readStart = 0;
        if (ctl.signal.aborted) return;
        setError(errorMessage(e));
        setStep('error');
      }
    })();
    return () => {
      ctl.abort();
      window.clearTimeout(timer);
    };
  }, [file, me]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !sending) onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose, sending]);

  const confirm = async () => {
    if (!result || !fields) return;
    if (fields.type !== 'khac' && !fields.amount) {
      setSendError('Nhập số tiền trước khi gửi.');
      return;
    }
    setSending(true);
    setSendError(null);
    try {
      onSent(await sendScan(result.scan_id, me, fields));
    } catch (e) {
      setSendError(errorMessage(e));
      setSending(false);
    }
  };

  const pct = Math.round(progress);
  return (
    <div className="fx-scan" role="dialog" aria-modal="true" aria-label="Quét ảnh thanh toán" ref={dialog} tabIndex={-1}>
      <header className="fx-scan-head">
        <Text type="label" weight="semibold">
          {step === 'result' ? 'Kiểm tra rồi xác nhận' : 'Quét ảnh thanh toán'}
        </Text>
        <IconButton label="Đóng" variant="ghost" icon={<X size={18} />} onClick={onClose} isDisabled={sending} />
      </header>

      {step !== 'result' && (
        <div className="fx-scan-stage">
          <div className="fx-scan-photo" data-state={step}>
            {preview && <img src={preview} alt="Ảnh vừa chụp" />}
            {step === 'scanning' && <span className="fx-scan-beam" aria-hidden="true" />}
          </div>
          {step === 'scanning' && (
            <div className="fx-scan-progress" aria-live="polite">
              <div className="flex items-baseline justify-between gap-3">
                <Text type="label" weight="semibold">
                  <Sparkles size={14} aria-hidden="true" className="fx-scan-spark" /> {stageText(progress)}
                </Text>
                <span className="fx-num fx-scan-pct">{pct}%</span>
              </div>
              <ProgressBar label="Tiến độ đọc ảnh" isLabelHidden value={pct} max={100} />
            </div>
          )}
          {step === 'error' && (
            <div className="flex flex-col gap-3">
              <Banner status="error" title="Chưa đọc được ảnh" description={error ?? undefined} collapsible={false} />
              <Button label="Chụp lại" variant="primary" size="lg" icon={<Camera size={18} />} onClick={onRetake} />
            </div>
          )}
        </div>
      )}

      {step === 'result' && result && fields && (
        <div className="fx-scan-result">
          <div className="fx-scan-summary">
            {preview && <img src={preview} alt="Ảnh vừa chụp" className="fx-scan-thumb" />}
            <div className="min-w-0">
              {result.engine !== 'gemini' && (
                <Text type="supporting" color="secondary" as="p">
                  {result.error ?? 'Nhập tay giúp'}
                </Text>
              )}
              <p className="fx-scan-amount fx-num">{fields.amount ? <Roll value={money(fields.amount)} /> : 'Chưa rõ số tiền'}</p>
              <Text type="supporting" color="secondary" as="p">
                {PAYMENT_TYPE_LABEL[fields.type]}
                {fields.table ? `, bàn ${fields.table}` : ''}
              </Text>
            </div>
          </div>
          {result.warnings.map((w) => (
            <Banner key={w} status="warning" title={w} collapsible={false} />
          ))}
          <PaymentForm value={fields} onChange={setFields} unsure={result.unsure} />
          {sendError && <Banner status="error" title={sendError} collapsible={false} />}
        </div>
      )}

      {step === 'result' && (
        <footer className="fx-scan-foot">
          <Button label="Chụp lại" variant="secondary" size="lg" icon={<RotateCcw size={18} />} onClick={onRetake} isDisabled={sending} />
          <Button label={sending ? 'Đang gửi' : 'Xác nhận và gửi'} variant="primary" size="lg" icon={<Check size={18} />} onClick={() => void confirm()} isDisabled={sending} />
        </footer>
      )}
    </div>
  );
}
