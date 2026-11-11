import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react';
import { RefreshCw, Send, Sparkles } from 'lucide-react';
import { Empty } from '../../components/ui';
import { askAssistant, errorMessage, writeSummary } from '../../live/api';
import { useReport, useRun, useTitle } from '../../live/hooks';
import { useLive, useLiveConnection } from '../../live/store';
import { byName, clockTime, KIND_LABEL, secText, statusText, tableText } from '../../live/text';
import { CropImg, KindChip, VerifyChip } from '../../live/ui';
import type { AssistantRef, Report } from '../../live/types';

interface Msg {
  id: number;
  role: 'user' | 'ai' | 'error';
  text: string;
  refs?: AssistantRef[];
}

const SUGGESTIONS = [
  'Bàn nào gọi nhiều nhất?',
  'Thời gian phản hồi trung bình là bao nhiêu?',
  'Có báo nhầm nào không?',
  'Ai nhận nhiều việc nhất?',
  'Bàn nào đang cần dọn?',
];

// Giữ hội thoại và bản tóm tắt khi chuyển qua lại giữa các trang
let saved: Msg[] = [];
let savedSummary: string | null = null;

const refKey = (r: AssistantRef) => `${r.alert_id ?? ''}|${r.t}|${r.table ?? ''}`;

/** Chi tiết sự kiện mà câu trả lời nhắc tới */
function RefDetail({ focus }: { focus: AssistantRef }) {
  const alerts = useLive((s) => s.alerts);
  const staff = useLive((s) => s.staff);
  const settings = useLive((s) => s.settings);
  const log = useLive((s) => s.log);
  const alert = focus.alert_id ? alerts.find((a) => a.id === focus.alert_id) : undefined;
  const near = useMemo(
    () => log.filter((e) => Math.abs(e.t - focus.t) <= 60000 && (!focus.table || e.table === focus.table)).slice(0, 8),
    [log, focus.t, focus.table],
  );

  return (
    <div className="panel-body flex flex-col gap-3">
      {alert ? (
        <>
          <CropImg url={alert.crop_url} alt={`Ảnh camera: ${KIND_LABEL[alert.kind]}, ${tableText(alert.table)}`} className="crop--lg" />
          <div className="flex items-center gap-2 flex-wrap">
            <KindChip kind={alert.kind} />
            <span className="ink2">{tableText(alert.table)}</span>
            <span className="measured cool">{clockTime(alert.created_at)}</span>
          </div>
          <p className="small ink2">{statusText(alert, staff, settings?.provider)}</p>
          <div className="flex gap-2 flex-wrap">
            <VerifyChip verify={alert.verify} ten={settings?.provider} />
            {alert.repeats > 0 && <span className="chip">lặp lại ×{alert.repeats}</span>}
          </div>
          {alert.verify.reason && <p className="tiny muted">{settings?.provider ?? 'Gemini'}: {alert.verify.reason}</p>}
          {alert.video_t !== null && <p className="tiny muted">Ở giây {alert.video_t.toFixed(1)} của video gốc ({alert.camera}).</p>}
        </>
      ) : (
        <p className="small ink2">
          {tableText(focus.table)}, lúc <span className="measured cool">{clockTime(focus.t)}</span>
        </p>
      )}
      {near.length > 0 && (
        <div>
          <h3 className="small muted mb-1">Nhật ký quanh thời điểm đó</h3>
          <ol className="trail trail--flush">
            {near.map((e) => (
              <li key={e.id}>
                <time>{clockTime(e.t)}</time>
                <span className="ev">{e.text}</span>
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}

function ReportPanel({ report, error, loading, refresh }: { report: Report | null; error: string | null; loading: boolean; refresh: () => void }) {
  const ten = useLive((s) => s.settings?.provider) ?? 'Gemini';
  const perTable = report ? [...report.per_table].sort((a, b) => b.calls - a.calls || byName(a.table, b.table)) : [];
  return (
    <section className="panel" aria-labelledby="rep-title">
      <div className="panel-head">
        <h2 id="rep-title">Số liệu ca</h2>
        <button type="button" className="btn btn--sm btn--ghost" onClick={refresh} aria-label="Làm mới số liệu">
          <RefreshCw size={14} aria-hidden="true" />
          Làm mới
        </button>
      </div>
      {!report ? (
        <div className="panel-body">
          <p className="small muted">{loading ? 'Đang lấy số liệu…' : (error ?? 'Chưa có số liệu.')}</p>
        </div>
      ) : (
        <>
          <div className="detail-section">
            <p className="tiny muted mb-2">
              Từ <span className="measured cool">{clockTime(report.from)}</span> đến <span className="measured cool">{clockTime(report.to)}</span>
            </p>
            <dl className="kv">
              <dt>Gọi phục vụ</dt>
              <dd>{report.counts.call}</dd>
              <dt>Cần dọn bàn</dt>
              <dd>{report.counts.needs_clearing}</dd>
              <dt>Khách mới</dt>
              <dd>{report.counts.new_guest}</dd>
              <dt>Đã huỷ</dt>
              <dd>{report.cancelled}</dd>
              <dt>{ten} chặn báo nhầm</dt>
              <dd>{report.rejected_by_gemini}</dd>
              <dt>Quá hạn, phải chuyển người</dt>
              <dd>{report.escalated}</dd>
            </dl>
          </div>
          <div className="detail-section">
            <h3 className="small muted mb-2">Từ lúc báo tới lúc nhân viên nhận</h3>
            <dl className="kv">
              <dt>Trung bình</dt>
              <dd>{secText(report.response_s.mean)}</dd>
              <dt>Trung vị</dt>
              <dd>{secText(report.response_s.median)}</dd>
              <dt>9 trên 10 việc dưới</dt>
              <dd>{secText(report.response_s.p90)}</dd>
            </dl>
            <h3 className="small muted mb-2 mt-4">Từ lúc báo tới lúc xong</h3>
            <dl className="kv">
              <dt>Trung bình</dt>
              <dd>{secText(report.done_s.mean)}</dd>
              <dt>Trung vị</dt>
              <dd>{secText(report.done_s.median)}</dd>
            </dl>
          </div>
          {report.per_staff.length > 0 && (
            <div className="table-wrap">
              <table className="table">
                <caption className="visually-hidden">Theo nhân viên</caption>
                <thead>
                  <tr>
                    <th scope="col">Nhân viên</th>
                    <th scope="col" className="num">
                      Nhận
                    </th>
                    <th scope="col" className="num">
                      Xong
                    </th>
                    <th scope="col" className="num">
                      Phản hồi
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {report.per_staff.map((s) => (
                    <tr key={s.id}>
                      <td className="ink2">{s.name}</td>
                      <td className="num">{s.acked}</td>
                      <td className="num">{s.done}</td>
                      <td className="num">{secText(s.mean_response_s)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {perTable.length > 0 && (
            <div className="table-wrap">
              <table className="table">
                <caption className="visually-hidden">Theo bàn</caption>
                <thead>
                  <tr>
                    <th scope="col">Bàn</th>
                    <th scope="col" className="num">
                      Gọi
                    </th>
                    <th scope="col" className="num">
                      Dọn
                    </th>
                    <th scope="col" className="num">
                      Khách
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {perTable.map((t) => (
                    <tr key={t.table}>
                      <td className="ink2">{t.table}</td>
                      <td className="num">{t.calls}</td>
                      <td className="num">{t.clearings}</td>
                      <td className="num">{t.guests}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </section>
  );
}

export default function LiveAssistant() {
  useLiveConnection();
  useTitle('Trợ lý AI, Easy FnB');
  const settings = useLive((s) => s.settings);
  const ten = settings?.provider ?? 'Gemini';
  const rep = useReport(10000);
  const { busy: summaryBusy, run } = useRun();
  const [msgs, setMsgs] = useState<Msg[]>(saved);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [focus, setFocus] = useState<AssistantRef | null>(null);
  const [summary, setSummary] = useState<string | null>(savedSummary);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    saved = msgs;
    savedSummary = summary;
  }, [msgs, summary]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: 'nearest' });
  }, [msgs, busy]);

  const ask = async (q: string) => {
    const question = q.trim();
    if (!question || busy) return;
    const id = (msgs.at(-1)?.id ?? 0) + 1;
    setMsgs((m) => [...m, { id, role: 'user', text: question }]);
    setInput('');
    setBusy(true);
    try {
      const a = await askAssistant(question);
      const refs = Array.isArray(a.refs) ? a.refs : [];
      setMsgs((m) => [...m, { id: id + 1, role: 'ai', text: a.answer || 'Trợ lý không có câu trả lời.', refs }]);
      if (refs[0]) setFocus(refs[0]);
    } catch (err) {
      setMsgs((m) => [...m, { id: id + 1, role: 'error', text: errorMessage(err) }]);
    } finally {
      setBusy(false);
    }
  };

  const submit = (ev: FormEvent) => {
    ev.preventDefault();
    void ask(input);
  };

  const summarize = async () => {
    const out = await run('summary', () => writeSummary());
    if (out) setSummary(out.text || `${ten} không viết được tóm tắt.`);
  };

  return (
    <div className="page">
      <div className="split">
        <section className="panel chat" aria-labelledby="chat-title">
          <div className="panel-head">
            <h1 id="chat-title">Trợ lý AI</h1>
            {settings ? (
              settings.gemini ? (
                <span className="chip chip--ok">{settings.model}</span>
              ) : (
                <span className="chip chip--bad">{ten} chưa bật</span>
              )
            ) : (
              <span className="sub">Trả lời từ nhật ký ca, kèm mốc giờ</span>
            )}
          </div>
          <div className="msgs" aria-live="polite">
            {msgs.length === 0 && (
              <div className="flex flex-col gap-3 max-w-xl">
                <h2>Hỏi về ca làm việc đang diễn ra</h2>
                <p className="muted">
                  Câu trả lời dựa trên nhật ký và danh sách việc thật của ca này: bàn nào gọi nhiều, ai phản hồi nhanh, có báo nhầm không. Bấm mốc giờ để xem ảnh camera lúc đó.
                  {settings && !settings.gemini && ` ${ten} chưa bật nên trợ lý chỉ trả lời được vài câu cơ bản tính sẵn.`}
                </p>
                <div className="suggestions">
                  {SUGGESTIONS.map((s) => (
                    <button key={s} type="button" className="btn btn--sm" onClick={() => void ask(s)}>
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {msgs.map((m) =>
              m.role === 'user' ? (
                <div key={m.id} className="msg-user">
                  {m.text}
                </div>
              ) : (
                <div key={m.id} className="msg-ai">
                  {m.text.split(/\n{2,}/).map((p, i) => (
                    <p key={i} className={m.role === 'error' ? 'bad' : undefined} style={{ whiteSpace: 'pre-line' }}>
                      {p}
                    </p>
                  ))}
                  {m.refs && m.refs.length > 0 && (
                    <div className="refs" aria-label="Sự kiện được nhắc tới">
                      {m.refs.map((r) => (
                        <button
                          key={refKey(r)}
                          type="button"
                          className="cite"
                          aria-pressed={focus !== null && refKey(focus) === refKey(r)}
                          aria-label={`Xem sự kiện ${tableText(r.table)} lúc ${clockTime(r.t)}`}
                          onClick={() => setFocus(r)}
                        >
                          {r.table ? `${r.table} · ` : ''}
                          {clockTime(r.t)}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              ),
            )}
            {busy && (
              <div className="msg-ai" aria-label="Đang tra nhật ký ca">
                <span className="small muted">Đang tra nhật ký ca</span>
                <div className="skeleton" style={{ width: '62%' }} />
                <div className="skeleton" style={{ width: '48%' }} />
              </div>
            )}
            <div ref={endRef} />
          </div>
          {msgs.length > 0 && (
            <div className="suggestions px-3 pb-2">
              {SUGGESTIONS.slice(0, 3).map((s) => (
                <button key={s} type="button" className="btn btn--sm btn--ghost" onClick={() => void ask(s)} disabled={busy}>
                  {s}
                </button>
              ))}
            </div>
          )}
          <form className="composer" onSubmit={submit}>
            <label htmlFor="live-ask" className="visually-hidden">
              Câu hỏi cho trợ lý
            </label>
            <input id="live-ask" className="input" value={input} placeholder="Ví dụ: Bàn B2 gọi mấy lần?" onChange={(ev) => setInput(ev.target.value)} />
            <button type="submit" className="btn btn--primary" disabled={!input.trim() || busy}>
              <Send size={16} aria-hidden="true" />
              Gửi
            </button>
          </form>
        </section>

        <aside className="flex flex-col gap-3 min-w-0">
          <section className="panel" aria-labelledby="ref-title">
            <div className="panel-head">
              <h2 id="ref-title">Sự kiện được nhắc tới</h2>
            </div>
            {focus ? (
              <RefDetail focus={focus} />
            ) : (
              <Empty title="Chưa chọn sự kiện">
                <p>Bấm vào một mốc giờ trong câu trả lời để xem ảnh camera và nhật ký lúc đó.</p>
              </Empty>
            )}
          </section>

          <section className="panel" aria-labelledby="sum-title">
            <div className="panel-head">
              <h2 id="sum-title">Tóm tắt ca</h2>
            </div>
            <div className="panel-body flex flex-col gap-3">
              <button type="button" className="btn btn--primary self-start" disabled={summaryBusy !== null} onClick={() => void summarize()}>
                <Sparkles size={16} aria-hidden="true" />
                {summaryBusy ? `${ten} đang viết…` : `Viết tóm tắt ca bằng ${ten}`}
              </button>
              {summary ? (
                <div className="summary">
                  {summary.split(/\n{2,}/).map((p, i) => (
                    <p key={i} style={{ whiteSpace: 'pre-line' }}>
                      {p}
                    </p>
                  ))}
                </div>
              ) : (
                <p className="small muted">
                  {ten} đọc số liệu và nhật ký rồi viết vài đoạn ngắn cho chủ quán.
                  {settings && !settings.gemini && ` ${ten} chưa bật nên máy chủ sẽ dùng mẫu có sẵn.`}
                </p>
              )}
            </div>
          </section>

          <ReportPanel report={rep.report} error={rep.error} loading={rep.loading} refresh={rep.refresh} />
        </aside>
      </div>
    </div>
  );
}
