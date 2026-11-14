import { useState } from 'react';
import { Button } from '@astryxdesign/core/Button';
import { Dialog, DialogHeader } from '@astryxdesign/core/Dialog';
import { TextInput } from '@astryxdesign/core/TextInput';
import { checkOwnerPin, errorMessage, isPinError, rememberPin } from '../live/api';

/** Hỏi mã PIN chủ quán, kiểm với máy chủ rồi nhớ trong phiên (dùng cùng useOwnerPin) */
export function PinDialog({ isOpen, onClose, onOk, subtitle = 'Chỉ chủ quán xem được video không che mặt.' }: { isOpen: boolean; onClose: () => void; onOk: (pin: string) => void; subtitle?: string }) {
  const [pin, setPin] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const close = () => {
    setPin('');
    setError(null);
    onClose();
  };
  const submit = async () => {
    if (!/^\d{4,8}$/.test(pin)) return setError('Mã PIN gồm 4 đến 8 chữ số.');
    setBusy(true);
    try {
      const out = await checkOwnerPin(pin);
      if (!out.ok) return setError('Mã PIN không đúng.');
      rememberPin(pin);
      setPin('');
      setError(null);
      onOk(pin);
    } catch (err) {
      setError(isPinError(err) ? 'Mã PIN không đúng.' : errorMessage(err));
    } finally {
      setBusy(false);
    }
  };
  return (
    <Dialog isOpen={isOpen} onOpenChange={(o) => !o && close()} width={380} purpose="form">
      <DialogHeader title="Nhập mã PIN chủ quán" subtitle={subtitle} onOpenChange={(o) => !o && close()} />
      <div className="flex flex-col gap-3" style={{ paddingInline: 16, paddingBottom: 12 }}>
        <TextInput
          label="Mã PIN"
          type="password"
          inputMode="numeric"
          autoComplete="off"
          hasAutoFocus
          value={pin}
          onChange={(v) => setPin(v.replace(/\D/g, '').slice(0, 8))}
          onEnter={() => void submit()}
          status={error ? { type: 'error', message: error } : undefined}
        />
        <div className="flex justify-end gap-2">
          <Button label="Thôi" variant="ghost" onClick={close} />
          <Button label="Mở" variant="primary" isLoading={busy} onClick={() => void submit()} />
        </div>
      </div>
    </Dialog>
  );
}
