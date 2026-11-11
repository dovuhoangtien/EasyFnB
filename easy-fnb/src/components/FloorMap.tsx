import type { KeyboardEvent } from 'react';
import { AREAS, FLOOR, PHASE_LABEL, TABLES, ZONES, seatPoints, staffDef } from '../sim/model';
import { useSim } from '../sim/store';

interface Props {
  selected?: number;
  onSelect: (id: number) => void;
}

/** Sơ đồ quán trực tiếp: mỗi bàn tô màu theo điểm khẩn cấp, nhân viên di chuyển theo camera */
export function FloorMap({ selected, onSelect }: Props) {
  const e = useSim();
  const door = AREAS.find((a) => a.id === 'door')!;

  const onKey = (ev: KeyboardEvent, id: number) => {
    if (ev.key === 'Enter' || ev.key === ' ') {
      ev.preventDefault();
      onSelect(id);
    }
  };

  return (
    <svg
      className="floor"
      viewBox={`0 0 ${FLOOR.w} ${FLOOR.h}`}
      role="group"
      aria-label="Sơ đồ quán. Mỗi bàn được tô màu theo mức khẩn cấp, chấm tròn là nhân viên."
    >
      <rect className="wall" x={8} y={8} width={FLOOR.w - 16} height={FLOOR.h - 16} rx={10} />
      {ZONES.map((z) => (
        <text key={z.zone} className="zone-label" x={z.x} y={z.y}>
          {z.label}
        </text>
      ))}
      {AREAS.map((a) => (
        <g key={a.id}>
          <rect className="area" x={a.x} y={a.y} width={a.w} height={a.h} rx={6} />
          <text className="area-label" x={a.x + 12} y={a.y + a.h / 2 + 5}>
            {a.label}
          </text>
        </g>
      ))}
      {e.waitlist.length > 0 && (
        <text className="wait-label" x={door.x + 12} y={door.y - 10}>
          {e.waitlist.length} nhóm đang chờ
        </text>
      )}

      {TABLES.map((d) => {
        const tb = e.table(d.id);
        const cx = d.x + d.w / 2;
        const cy = d.y + d.h / 2;
        const seats = tb.phase === 'empty' || tb.phase === 'needs_clearing' ? [] : seatPoints(d, tb.party);
        const regular = tb.person ? e.personName(tb.person) : undefined;
        return (
          <g
            key={d.id}
            className="tbl"
            data-phase={tb.phase}
            data-tier={tb.tier}
            role="button"
            tabIndex={0}
            aria-pressed={selected === d.id}
            aria-label={`Bàn ${d.id}, ${PHASE_LABEL[tb.phase]}${tb.party ? `, ${tb.party} khách` : ''}${tb.tier ? `, điểm khẩn cấp ${tb.urgency}` : ''}`}
            onClick={() => onSelect(d.id)}
            onKeyDown={(ev) => onKey(ev, d.id)}
          >
            {tb.hand !== undefined &&
              (d.round ? (
                <circle className="pulse" cx={cx} cy={cy} r={d.w / 2 + 6} />
              ) : (
                <rect className="pulse" x={d.x - 6} y={d.y - 6} width={d.w + 12} height={d.h + 12} rx={12} />
              ))}
            {seats.map((p, i) => (
              <circle key={i} className="seat" cx={p.x} cy={p.y} r={5} />
            ))}
            {d.round ? (
              <circle className="shape" cx={cx} cy={cy} r={d.w / 2} />
            ) : (
              <rect className="shape" x={d.x} y={d.y} width={d.w} height={d.h} rx={8} />
            )}
            <text className="tbl-num" x={cx} y={cy + (regular ? -6 : 2)} textAnchor="middle">
              {d.id}
            </text>
            <text className="tbl-phase" x={cx} y={cy + (regular ? 12 : 20)} textAnchor="middle">
              {PHASE_LABEL[tb.phase]}
              {tb.party ? `, ${tb.party} khách` : ''}
            </text>
            {regular && (
              <text className="regular-tag" x={cx} y={cy + 28} textAnchor="middle">
                {regular}
              </text>
            )}
            {tb.tier > 0 && (
              <text className="tbl-score" x={d.round ? cx + d.w / 2 - 4 : d.x + d.w - 8} y={d.round ? d.y + 10 : d.y + 16} textAnchor="end">
                {tb.urgency}
              </text>
            )}
          </g>
        );
      })}

      {e.staff.map((s) =>
        s.status === 'enroute' ? <line key={`p-${s.id}`} className="staff-path" x1={s.x} y1={s.y} x2={s.tx} y2={s.ty} /> : null,
      )}
      {e.staff.map((s) => {
        const sd = staffDef(s.id);
        return (
          <g key={s.id} className="staff-dot" data-status={s.status} transform={`translate(${s.x.toFixed(1)} ${s.y.toFixed(1)})`}>
            <circle r={13} />
            <text className="initial" textAnchor="middle" y={4.5}>
              {sd.name.charAt(0)}
            </text>
            <text className="name" x={18} y={5}>
              {sd.name}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
