import { useCallback, useEffect, useState } from 'react';
import { ArrowLeftRight, CircleHelp, Coins, Users } from 'lucide-react';
import { Button } from '@astryxdesign/core/Button';
import { Text } from '@astryxdesign/core/Text';
import { errorMessage } from '../live/api';
import { getRevenue, money, noteVisit, type Revenue } from '../live/chat';
import { Roll } from './motion';
import { SectionTitle } from './ui';

/** Phần "Tiền" của Ca hôm nay: tổng thu từ ảnh thanh toán đã gửi vào nhóm, và lượt khách chưa thấy thanh toán */
export function MoneySection() {
  const [rv, setRv] = useState<Revenue | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setRv(await getRevenue());
      setErr(null);
    } catch (e) {
      setErr(errorMessage(e));
    }
  }, []);

  useEffect(() => {
    void load();
    const t = window.setInterval(() => void load(), 15000);
    return () => window.clearInterval(t);
  }, [load]);

  if (!rv) return err ? <Text type="supporting" color="secondary" as="p">Chưa lấy được số tiền: {err}</Text> : null;
  if (rv.count === 0 && rv.review.length === 0) return null;

  const cells = [
    { label: 'Đã thu', value: money(rv.total), note: `${rv.count} lần thanh toán`, icon: <Coins size={15} /> },
    { label: 'Chuyển khoản', value: String(rv.transfers), note: rv.count ? `${Math.round((rv.transfers / rv.count) * 100)}% số lần` : '', icon: <ArrowLeftRight size={15} /> },
    { label: 'Trung bình mỗi khách', value: rv.per_guest ? money(rv.per_guest) : 'Chưa rõ', note: `${rv.visits} lượt khách camera thấy`, icon: <Users size={15} /> },
    { label: 'Cần xem lại', value: String(rv.review.length), note: rv.review.length ? 'Bên dưới' : 'Không có', icon: <CircleHelp size={15} />, warn: rv.review.length > 0 },
  ];

  const markFree = async (visit: string) => {
    setBusy(visit);
    try {
      await noteVisit(visit, 'chu', 'không thu tiền');
      await load();
    } catch (e) {
      setErr(errorMessage(e));
    } finally {
      setBusy(null);
    }
  };

  return (
    <>
      <SectionTitle>Tiền</SectionTitle>
      <div className="fx-strip">
        {cells.map((c) => (
          <div key={c.label} className="fx-strip-cell">
            <span className="flex items-center gap-2">
              <span className="fx-ico" data-tone={c.warn ? 'warning' : undefined}>
                {c.icon}
              </span>
              <Text type="supporting" color="secondary">
                {c.label}
              </Text>
            </span>
            <span className="fx-strip-value">
              <Roll value={c.value} />
            </span>
            <Text type="supporting" color="secondary">
              {c.note}
            </Text>
          </div>
        ))}
      </div>
      {rv.review.length > 0 && (
        <ul className="fx-review" aria-label="Cần xem lại">
          {rv.review.map((r) => (
            <li key={r.visit ?? `p${r.payment_id}`}>
              <Text type="body" as="span">
                {r.text}
              </Text>
              {r.kind === 'no_payment' && r.visit && (
                <Button label="Không thu tiền" variant="ghost" size="sm" isLoading={busy === r.visit} onClick={() => void markFree(r.visit!)} />
              )}
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
