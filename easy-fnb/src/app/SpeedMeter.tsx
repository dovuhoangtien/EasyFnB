import { useState, type CSSProperties } from 'react';
import { SPEED_LABEL, verdictOf, type SpeedCounts, type SpeedKind } from '../live/text';
import { Roll } from './motion';

/* Thước đo tốc độ phục vụ: một thanh xếp chồng, mỗi đoạn là một mức (nhanh, hơi chậm, chậm, không ai tới).
 * Chỉ vào mức nào thì mức đó sáng lên, các mức khác lùi lại, và dòng chữ lớn đổi sang số việc của mức ấy.
 *
 * Dựng lại từ block "Context meter" của Bencho (https://bencho.dev/blocks/context-meter), giấy phép MIT,
 * Copyright (c) 2026 Lorenzo Cabra: cách chia thanh, bo góc, làm mờ khi chỉ vào và chữ số bật lên là của block gốc. */

const KINDS: { id: SpeedKind; hint: string }[] = [
  { id: 'fast', hint: 'việc có người nhận trong nửa phút' },
  { id: 'ok', hint: 'việc phải chờ gần một phút' },
  { id: 'slow', hint: 'việc phải chờ hơn một phút' },
  { id: 'missed', hint: 'việc không ai tới' },
];

/** Góc của thanh: tròn ở hai đầu, gần vuông ở chỗ hai đoạn chạm nhau */
function corners(first: boolean, last: boolean): CSSProperties {
  const a = first ? 6 : 2;
  const b = last ? 6 : 2;
  return { borderTopLeftRadius: a, borderBottomLeftRadius: a, borderTopRightRadius: b, borderBottomRightRadius: b };
}

/** Thanh nhỏ không có chữ, dùng trong một hàng của bảng */
export function SpeedBar({ speed, label }: { speed: SpeedCounts; label: string }) {
  const shown = KINDS.filter((k) => (speed[k.id] ?? 0) > 0);
  return (
    <span className="fx-meter-bar" data-size="sm" role="img" aria-label={label}>
      {shown.map((k, n) => (
        <i key={k.id} className="fx-meter-seg" data-kind={k.id} style={{ flexGrow: speed[k.id], ...corners(n === 0, n === shown.length - 1) }} />
      ))}
    </span>
  );
}

export function SpeedMeter({ speed, title = 'Tốc độ phục vụ' }: { speed: SpeedCounts; title?: string }) {
  const [hot, setHot] = useState<SpeedKind | null>(null);
  const total = KINDS.reduce((n, k) => n + (speed[k.id] ?? 0), 0);
  const verdict = verdictOf(speed);
  const shown = KINDS.filter((k) => (speed[k.id] ?? 0) > 0);
  const hotKind = KINDS.find((k) => k.id === hot);
  const summary = `${title}: ${verdict ? SPEED_LABEL[verdict] : 'chưa có việc'}. ${shown.map((k) => `${speed[k.id]} ${k.hint}`).join(', ')}`;

  return (
    <section className="fx-meter" data-hot={hot ?? undefined} onPointerLeave={() => setHot(null)} aria-label={summary}>
      <h2 className="fx-meter-title">{title}</h2>
      <p className="fx-meter-figure" aria-hidden="true">
        {hotKind ? (
          <>
            <span className="fx-meter-num" data-kind={hotKind.id}>
              <Roll value={speed[hotKind.id] ?? 0} />
            </span>
            <span className="fx-meter-of">{hotKind.hint}</span>
          </>
        ) : verdict ? (
          <>
            <span className="fx-meter-num" data-kind={verdict}>
              {SPEED_LABEL[verdict]}
            </span>
            <span className="fx-meter-of">
              {speed.fast} trên {total} việc có người nhận trong nửa phút
            </span>
          </>
        ) : (
          <>
            <span className="fx-meter-num">Chưa có</span>
            <span className="fx-meter-of">chưa việc nào được nhận</span>
          </>
        )}
      </p>
      <div className="fx-meter-bar" aria-hidden="true">
        {shown.length === 0 && <i className="fx-meter-seg fx-meter-room" style={{ flexGrow: 1, ...corners(true, true) }} />}
        {shown.map((k, n) => (
          <i
            key={k.id}
            className="fx-meter-seg"
            data-kind={k.id}
            data-dim={(hot !== null && hot !== k.id) || undefined}
            style={{ flexGrow: speed[k.id], '--i': n, ...corners(n === 0, n === shown.length - 1) } as CSSProperties}
            onPointerEnter={() => setHot(k.id)}
          />
        ))}
      </div>
      <ul className="fx-meter-chips" aria-hidden="true">
        {KINDS.map((k) => (
          <li
            key={k.id}
            className="fx-meter-chip"
            data-on={hot === k.id || undefined}
            data-empty={!speed[k.id] || undefined}
            onPointerEnter={() => setHot(speed[k.id] ? k.id : null)}
          >
            <i className="fx-swatch" data-kind={k.id} />
            {k.id === 'missed' ? 'Không ai tới' : SPEED_LABEL[k.id]}
            <b>{speed[k.id] ?? 0}</b>
          </li>
        ))}
      </ul>
    </section>
  );
}
