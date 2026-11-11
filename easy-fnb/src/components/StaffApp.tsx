import { Link } from 'react-router';
import { ExternalLink, HeadphoneOff, Headphones, Play, Volume2 } from 'lucide-react';
import { PriorityChip } from './ui';
import type { Spoken } from '../sim/engine';
import { staffDef } from '../sim/model';
import { STAFF_TEXT } from '../sim/staffText';
import { useSim } from '../sim/store';
import { clock } from '../sim/util';
import { replay, setListen, textFor, useVoice } from '../sim/voice';

/** Thông báo vừa tới trong 4 giây thật gần nhất thì được tô sáng */
const FRESH_MS = 4000;

interface Props {
  id: string;
  /** tile: một ô trong lưới các kênh; phone: toàn màn hình trên điện thoại */
  variant?: 'tile' | 'phone';
}

/** Màn hình app của một nhân viên: việc hiện tại và những gì đã nghe trong tai nghe */
export function StaffApp({ id, variant = 'tile' }: Props) {
  const e = useSim();
  const v = useVoice();
  const L = STAFF_TEXT[v.lang];
  const sd = staffDef(id);
  const s = e.staff.find((x) => x.id === id)!;
  const task = e.tasks.find((k) => k.id === s.task);
  const heard = e.spoken.filter((x) => x.staff === id).slice(variant === 'phone' ? -12 : -6).reverse();
  const isFresh = (x: Spoken) => x.wall > 0 && e.wall - x.wall < FRESH_MS;
  const latest = heard[0];
  const alert = latest && isFresh(latest) ? latest.priority : undefined;
  const listening = v.listening.includes(id);
  const talking = v.speaking?.staff === id;

  let status = { label: L.status.idle, cls: 'chip chip--ok' };
  if (s.status === 'break') status = { label: L.status.break, cls: 'chip' };
  else if (task && s.status === 'enroute')
    status = { label: e.t < s.departAt ? L.status.departing(task.table) : L.status.enroute(task.table), cls: 'chip chip--p2' };
  else if (task && s.status === 'serving') status = { label: L.status.serving(task.table), cls: 'chip chip--cool' };

  return (
    <section className="sapp" data-variant={variant} data-alert={alert} aria-labelledby={`sapp-${id}`}>
      <header className="sapp-head">
        <span className="avatar avatar--sm" aria-hidden="true">
          {sd.name.charAt(0)}
        </span>
        <div className="min-w-0">
          <h2 id={`sapp-${id}`}>{sd.name}</h2>
          <p className="tiny muted">{L.role(sd.role, sd.zone)}</p>
        </div>
        {talking ? (
          <span className="chip chip--p2 sapp-status">
            <Volume2 size={13} aria-hidden="true" />
            {L.talking}
          </span>
        ) : (
          <span className={`${status.cls} sapp-status`}>{status.label}</span>
        )}
      </header>

      <div className="sapp-now" aria-live={variant === 'phone' ? 'assertive' : 'off'}>
        {task ? (
          <>
            <div className="flex items-center gap-2 flex-wrap">
              <PriorityChip p={task.priority} />
              <span className="tiny muted">
                {L.assignedAt} <span className="measured cool">{clock(task.assignedAt ?? task.created)}</span>
              </span>
            </div>
            <p className="sapp-table">
              {L.table} {task.table}
            </p>
            <p className="sapp-what">{task.kind === 'greet' && task.person ? `${v.lang === 'en' ? e.personNameEn(task.person) : e.personName(task.person)}, ${L.task(task.kind).toLowerCase()}` : L.task(task.kind)}</p>
            <p className="small muted">{v.lang === 'en' ? task.whyEn : task.why}</p>
            <p className="tiny muted mt-auto">{task.arrivedAt !== undefined ? L.confirmed : L.autoConfirm}</p>
          </>
        ) : (
          <>
            <p className="sapp-table sapp-idle">{s.status === 'break' ? L.onBreak : L.free}</p>
            <p className="small muted">{L.nextHint}</p>
          </>
        )}
      </div>

      <div className="sapp-feed">
        <h3>{L.heard}</h3>
        {heard.length ? (
          <ol>
            {heard.map((h) => {
              const text = textFor(h, v.lang);
              return (
                <li key={h.id} data-fresh={isFresh(h)} data-p={h.priority}>
                  <time className="measured cool">{clock(h.t)}</time>
                  <span className="sapp-line">{text}</span>
                  <button type="button" className="btn btn--ghost btn--icon sapp-replay" aria-label={L.replay(text)} onClick={() => replay(h)}>
                    <Play size={13} aria-hidden="true" />
                  </button>
                </li>
              );
            })}
          </ol>
        ) : (
          <p className="small muted">{L.empty}</p>
        )}
      </div>

      {variant === 'tile' && (
        <footer className="sapp-foot">
          <button type="button" className="btn" aria-pressed={listening} onClick={() => setListen(id, !listening)}>
            {listening ? <Headphones size={16} aria-hidden="true" /> : <HeadphoneOff size={16} aria-hidden="true" />}
            {listening ? L.listening : L.listen}
          </button>
          <Link className="btn btn--icon" to={`/nv/${id}`} target="_blank" rel="noopener" aria-label={L.openPhone(sd.name)} title={L.openPhone(sd.name)}>
            <ExternalLink size={16} aria-hidden="true" />
          </Link>
        </footer>
      )}
    </section>
  );
}
