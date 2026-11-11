import { Fragment, type ReactNode } from 'react';
import { RotateCw } from 'lucide-react';
import { AREAS, TABLES, seatPoints, staffDef, type CameraDef, type TableDef } from '../sim/model';
import type { TableState } from '../sim/engine';
import { useSim } from '../sim/store';
import { clock, dec } from '../sim/util';
import { useToast } from './ui';

const conf = (seed: number) => dec(0.86 + ((seed * 53) % 12) / 100, 2);

function Label({ x, y, text, kind }: { x: number; y: number; text: string; kind?: 'staff' | 'alert' }) {
  const w = text.length * 6.6 + 8;
  return (
    <g>
      <rect className="det-label-bg" x={x} y={y - 12} width={w} height={15} rx={3} />
      <text className={`det-label${kind ? ` det-label--${kind}` : ''}`} x={x + 4} y={y}>
        {text}
      </text>
    </g>
  );
}

function objectsFor(tb: TableState) {
  switch (tb.phase) {
    case 'waiting_food':
      return { n: tb.party, label: 'ly' };
    case 'eating':
    case 'finishing':
    case 'wants_bill':
    case 'leaving':
      return { n: tb.party + 1, label: 'bát' };
    case 'needs_clearing':
      return { n: tb.party + 2, label: 'bát' };
    default:
      return { n: 0, label: '' };
  }
}

function TableDetections({ d, tb }: { d: TableDef; tb: TableState }) {
  const out: ReactNode[] = [];
  const obj = objectsFor(tb);
  const inner = d.round ? { x: d.x + d.w * 0.2, y: d.y + d.h * 0.2, w: d.w * 0.6 } : { x: d.x + 10, y: d.y + 10, w: d.w - 20 };
  const cols = Math.max(2, Math.floor(inner.w / 22));
  for (let k = 0; k < Math.min(obj.n, 8); k++) {
    const x = inner.x + (k % cols) * 22;
    const y = inner.y + Math.floor(k / cols) * 22;
    out.push(<rect key={`o${k}`} className="det det--obj" x={x} y={y} width={15} height={15} rx={2} />);
  }
  if (obj.n > 0) out.push(<Label key="ol" x={inner.x} y={inner.y - 4} text={`${obj.label} ${conf(d.id + 7)}`} />);

  const people = tb.phase === 'empty' || tb.phase === 'needs_clearing' ? [] : seatPoints(d, tb.party);
  people.forEach((p, i) => {
    const raised = tb.hand !== undefined && i === 0;
    out.push(
      <Fragment key={`p${i}`}>
        <circle className="cam-person" cx={p.x} cy={p.y} r={9} />
        {raised ? (
          <>
            <rect className="det det--alert" x={p.x - 17} y={p.y - 32} width={36} height={50} rx={3} />
            <line className="bone" x1={p.x - 8} y1={p.y + 3} x2={p.x + 8} y2={p.y + 3} />
            <line className="bone" x1={p.x + 8} y1={p.y + 3} x2={p.x + 13} y2={p.y - 11} />
            <line className="bone" x1={p.x + 13} y1={p.y - 11} x2={p.x + 14} y2={p.y - 26} />
            <circle className="joint" cx={p.x + 14} cy={p.y - 26} r={3} />
            <circle className="joint" cx={p.x + 13} cy={p.y - 11} r={2.5} />
            <Label x={p.x - 17} y={p.y - 36} text={`giơ tay ${conf(d.id)}`} kind="alert" />
          </>
        ) : (
          <rect className="det" x={p.x - 15} y={p.y - 15} width={30} height={30} rx={3} />
        )}
        {i === 0 && !raised && <Label x={p.x - 15} y={p.y - 19} text={`người ${conf(d.id + i)}`} />}
      </Fragment>,
    );
  });
  return <>{out}</>;
}

interface Props {
  cam: CameraDef;
  highlight?: number;
  still?: number;
  compact?: boolean;
}

/** Khung hình camera đã qua AI: hộp phát hiện, tư thế và nhãn do mô hình trả về */
export function CameraView({ cam, highlight, still, compact }: Props) {
  const e = useSim();
  const toast = useToast();

  if (!cam.view) {
    return (
      <div className="cam" role="img" aria-label={`${cam.name}, ${cam.place}: mất tín hiệu`}>
        <div className="cam-offline">
          <h3>
            {cam.name}, {cam.place}
          </h3>
          <span className="chip chip--bad">Mất tín hiệu</span>
          {!compact && (
            <>
              <p>Luồng RTSP không phản hồi. Hệ thống tự thử kết nối lại sau mỗi 30 giây; các camera khác vẫn chạy bình thường.</p>
              <button type="button" className="btn btn--sm" onClick={() => toast('Đang thử kết nối lại Cam 5...')}>
                <RotateCw size={14} aria-hidden="true" />
                Thử kết nối lại
              </button>
            </>
          )}
        </div>
      </div>
    );
  }

  const v = cam.view;
  const inView = (x: number, y: number) => x >= v.x && x <= v.x + v.w && y >= v.y && y <= v.y + v.h;
  const tables = TABLES.filter((d) => d.x < v.x + v.w && d.x + d.w > v.x && d.y < v.y + v.h && d.y + d.h > v.y);
  const staff = still === undefined ? e.staff.filter((s) => inView(s.x, s.y)) : [];
  const areas = AREAS.filter((a) => a.x < v.x + v.w && a.x + a.w > v.x && a.y < v.y + v.h && a.y + a.h > v.y);
  const door = AREAS.find((a) => a.id === 'door')!;
  const waiting = still === undefined && inView(door.x + 40, door.y + 20) ? e.waitlist : [];

  let people = 0;
  let objects = 0;
  if (still === undefined) {
    for (const d of tables) {
      const tb = e.table(d.id);
      if (tb.phase !== 'empty' && tb.phase !== 'needs_clearing') people += tb.party;
      objects += objectsFor(tb).n;
    }
    people += staff.length + waiting.reduce((s, g) => s + g.party, 0);
  }

  return (
    <div className="cam" role="img" aria-label={`${cam.name}, ${cam.place}${still !== undefined ? `, khung hình lúc ${clock(still)}` : `, ${people} người trong khung hình`}`}>
      <svg viewBox={`${v.x} ${v.y} ${v.w} ${v.h}`} preserveAspectRatio="xMidYMid slice" aria-hidden="true">
        <rect className="cam-scene" x={v.x} y={v.y} width={v.w} height={v.h} />
        {Array.from({ length: 12 }, (_, i) => (
          <line key={i} className="cam-floor-line" x1={v.x} x2={v.x + v.w} y1={v.y + ((i + 1) * v.h) / 12} y2={v.y + ((i + 1) * v.h) / 12} />
        ))}
        {areas.map((a) => (
          <rect key={a.id} className="cam-table" x={a.x} y={a.y} width={a.w} height={a.h} rx={4} />
        ))}
        {tables.map((d) => {
          const tb = e.table(d.id);
          const hl = highlight === d.id;
          return (
            <g key={d.id}>
              {d.round ? (
                <circle className="cam-table" cx={d.x + d.w / 2} cy={d.y + d.h / 2} r={d.w / 2} />
              ) : (
                <rect className="cam-table" x={d.x} y={d.y} width={d.w} height={d.h} rx={6} />
              )}
              <text className="cam-roi" x={d.x + d.w / 2} y={d.y + d.h / 2 + 4} textAnchor="middle">
                bàn {d.id}
              </text>
              {still === undefined && <TableDetections d={d} tb={tb} />}
              {hl && (
                <>
                  <rect className="det det--alert" x={d.x - 22} y={d.y - 22} width={d.w + 44} height={d.h + 44} rx={6} />
                  <Label x={d.x - 22} y={d.y - 26} text={`bàn ${d.id}`} kind="alert" />
                </>
              )}
            </g>
          );
        })}
        {waiting.map((g, gi) =>
          Array.from({ length: Math.min(g.party, 4) }, (_, i) => {
            const x = door.x + 30 + i * 30 + gi * 8;
            const y = door.y - 30 - gi * 26;
            return (
              <g key={`${g.id}-${i}`}>
                <circle className="cam-person" cx={x} cy={y} r={9} />
                <rect className="det" x={x - 13} y={y - 13} width={26} height={26} rx={3} />
                {i === 0 && <Label x={x - 13} y={y - 17} text={`đang chờ ${gi + 1}`} />}
              </g>
            );
          }),
        )}
        {staff.map((s) => (
          <g key={s.id}>
            <circle className="cam-person" cx={s.x} cy={s.y} r={10} />
            <rect className="det det--staff" x={s.x - 16} y={s.y - 18} width={32} height={36} rx={3} />
            <Label x={s.x - 16} y={s.y - 22} text={`${staffDef(s.id).name}, nhân viên`} kind="staff" />
          </g>
        ))}
      </svg>
      <div className="cam-hud cam-hud--top">
        <span className="hud-tag">
          {cam.name}
          {!compact && <span className="muted">{cam.place}</span>}
        </span>
        {!compact && <span className="hud-tag measured">{clock(still ?? e.t)}</span>}
      </div>
      {!compact && still === undefined && (
        <div className="cam-hud cam-hud--bottom">
          <span className="hud-tag">
            {people} người, {objects} vật thể
          </span>
          <span className="hud-tag measured">5 fps</span>
        </div>
      )}
    </div>
  );
}
