import { useEffect } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { ChevronRight, HeadphoneOff, Headphones, ScanEye } from 'lucide-react';
import { StaffApp } from '../components/StaffApp';
import { STAFF } from '../sim/model';
import { STAFF_TEXT } from '../sim/staffText';
import { useSim } from '../sim/store';
import { listenOnly, setLang, setListen, useVoice, type Lang } from '../sim/voice';

function LangSwitch({ lang }: { lang: Lang }) {
  return (
    <div className="seg" role="group" aria-label="Ngôn ngữ / Language">
      <button type="button" aria-pressed={lang === 'vi'} onClick={() => setLang('vi')}>
        VI
      </button>
      <button type="button" aria-pressed={lang === 'en'} onClick={() => setLang('en')}>
        EN
      </button>
    </div>
  );
}

/** App nhân viên mở trên điện thoại: chỉ một người, chỉ việc của người đó */
export default function StaffPhone() {
  const { id } = useParams();
  const navigate = useNavigate();
  const e = useSim();
  const v = useVoice();
  const L = STAFF_TEXT[v.lang];
  const sd = STAFF.find((s) => s.id === id);
  const listening = !!sd && v.listening.includes(sd.id);
  const last = sd ? e.spoken.filter((x) => x.staff === sd.id).at(-1) : undefined;
  const lastId = last?.wall ? last.id : undefined;
  const lastPriority = last?.priority;

  useEffect(() => {
    document.title = sd ? `${sd.name}, Easy FnB` : 'Easy FnB cho nhân viên';
  }, [sd]);

  // Rung máy khi có việc mới, việc gấp rung hai lần
  useEffect(() => {
    if (lastId === undefined || !listening) return;
    navigator.vibrate?.(lastPriority === 1 ? [90, 60, 90] : 70);
  }, [lastId, lastPriority, listening]);

  return (
    <div className="phone">
      <header className="phone-bar">
        <span className="brand">
          <span className="brand-mark" aria-hidden="true">
            <ScanEye size={16} strokeWidth={2.2} />
          </span>
          Easy FnB
        </span>
        {sd && (
          <>
            <label className="visually-hidden" htmlFor="who">
              {L.switchStaff}
            </label>
            <select id="who" className="input phone-select" value={sd.id} onChange={(ev) => navigate(`/nv/${ev.target.value}`)}>
              {STAFF.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </>
        )}
        <LangSwitch lang={v.lang} />
      </header>

      {!sd ? (
        <section className="panel phone-who" aria-labelledby="who-title">
          <div className="panel-head">
            <h1 id="who-title">{L.who}</h1>
          </div>
          <p className="small muted px-4 pt-3">{L.whoHint}</p>
          <ul>
            {STAFF.map((s) => (
              <li key={s.id}>
                <Link to={`/nv/${s.id}`}>
                  <span className="avatar avatar--sm" aria-hidden="true">
                    {s.name.charAt(0)}
                  </span>
                  <span className="flex flex-col">
                    <span className="ink2">{s.name}</span>
                    <span className="tiny muted">{L.role(s.role, s.zone)}</span>
                  </span>
                  <ChevronRight size={18} aria-hidden="true" className="ml-auto muted" />
                </Link>
              </li>
            ))}
          </ul>
        </section>
      ) : (
        <>
          {!listening ? (
            <section className="panel phone-sound" aria-labelledby="sound-title">
              <h1 id="sound-title">{L.soundTitle}</h1>
              <p className="small ink2">{L.soundBody}</p>
              <button type="button" className="btn btn--primary btn--lg" onClick={() => listenOnly(sd.id)}>
                <Headphones size={18} aria-hidden="true" />
                {L.soundOn}
              </button>
            </section>
          ) : (
            <button type="button" className="btn btn--ghost self-start" onClick={() => setListen(sd.id, false)}>
              <HeadphoneOff size={16} aria-hidden="true" />
              {L.soundOff}
            </button>
          )}
          <StaffApp id={sd.id} variant="phone" />
        </>
      )}

      <p className="tiny muted phone-foot">
        {L.sim} <Link to="/app-nhan-vien">{L.back}</Link>
      </p>
    </div>
  );
}
