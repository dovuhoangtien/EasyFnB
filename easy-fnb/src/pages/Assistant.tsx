import { Fragment, useEffect, useRef, useState, type FormEvent } from 'react';
import { Link } from 'react-router';
import { Play, Send } from 'lucide-react';
import { CameraView } from '../components/CameraView';
import { Empty, useToast } from '../components/ui';
import { SUGGESTIONS, answer, cameraLabel, type Answer, type Clip } from '../sim/agent';
import { cameraDef } from '../sim/model';
import { engine } from '../sim/store';
import { clock } from '../sim/util';

interface Msg {
  id: number;
  role: 'user' | 'ai';
  text?: string;
  answer?: Answer;
}

// Giữ hội thoại khi chuyển qua lại giữa các trang
let saved: Msg[] = [];
let savedClip: Clip | null = null;

export default function Assistant() {
  const toast = useToast();
  const [msgs, setMsgs] = useState<Msg[]>(saved);
  const [input, setInput] = useState('');
  const [clip, setClip] = useState<Clip | null>(savedClip);
  const [busy, setBusy] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    saved = msgs;
    savedClip = clip;
  }, [msgs, clip]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: 'nearest' });
  }, [msgs, busy]);

  const ask = (q: string) => {
    const question = q.trim();
    if (!question || busy) return;
    const id = (msgs.at(-1)?.id ?? 0) + 1;
    setMsgs((m) => [...m, { id, role: 'user', text: question }]);
    setInput('');
    setBusy(true);
    window.setTimeout(() => {
      const a = answer(engine, question);
      setMsgs((m) => [...m, { id: id + 1, role: 'ai', answer: a }]);
      setClip(a.clips[0] ?? null);
      setBusy(false);
    }, 850);
  };

  const submit = (ev: FormEvent) => {
    ev.preventDefault();
    ask(input);
  };

  return (
    <div className="page">
      <div className="split">
        <section className="panel chat" aria-labelledby="chat-title">
          <div className="panel-head">
            <h1 id="chat-title">Trợ lý AI</h1>
            <span className="sub">Trả lời từ mọi thứ camera đã ghi lại, kèm mốc giờ</span>
          </div>
          <div className="msgs" aria-live="polite">
            {msgs.length === 0 && (
              <div className="flex flex-col gap-3 max-w-xl">
                <h2>Hỏi về bất cứ điều gì camera đã ghi lại</h2>
                <p className="muted">Ai tới lúc nào, bàn nào chờ lâu, chuyện gì xảy ra ở một bàn. Mỗi câu trả lời có mốc giờ để mở lại đoạn clip.</p>
                <div className="suggestions">
                  {SUGGESTIONS.map((s) => (
                    <button key={s} type="button" className="btn btn--sm" onClick={() => ask(s)}>
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
                  {m.answer!.paragraphs.map((p, i) => (
                    <p key={i}>
                      {p.map((s, j) =>
                        typeof s === 'string' ? (
                          <Fragment key={j}>{s}</Fragment>
                        ) : (
                          <button
                            key={j}
                            type="button"
                            className="cite"
                            aria-pressed={clip?.id === s.clip.id}
                            aria-label={`Xem clip ${s.clip.title} lúc ${clock(s.clip.t)}`}
                            onClick={() => setClip(s.clip)}
                          >
                            {clock(s.clip.t)}
                          </button>
                        ),
                      )}
                    </p>
                  ))}
                  <div className="tools" aria-label="Công cụ trợ lý đã gọi">
                    {m.answer!.tools.map((t) => (
                      <div key={t}>{t}</div>
                    ))}
                  </div>
                  {m.answer!.link && (
                    <Link className="btn btn--sm justify-self-start" to={m.answer!.link.to}>
                      {m.answer!.link.label}
                    </Link>
                  )}
                </div>
              ),
            )}
            {busy && (
              <div className="msg-ai" aria-label="Đang tra nhật ký camera">
                <span className="small muted">Đang tra nhật ký camera</span>
                <div className="skeleton" style={{ width: '62%' }} />
                <div className="skeleton" style={{ width: '48%' }} />
              </div>
            )}
            <div ref={endRef} />
          </div>
          {msgs.length > 0 && (
            <div className="suggestions px-3 pb-2">
              {SUGGESTIONS.slice(0, 4).map((s) => (
                <button key={s} type="button" className="btn btn--sm btn--ghost" onClick={() => ask(s)} disabled={busy}>
                  {s}
                </button>
              ))}
            </div>
          )}
          <form className="composer" onSubmit={submit}>
            <label htmlFor="ask" className="visually-hidden">
              Câu hỏi cho trợ lý
            </label>
            <input id="ask" className="input" value={input} placeholder="Ví dụ: Bàn 7 tối nay thế nào?" onChange={(ev) => setInput(ev.target.value)} />
            <button type="submit" className="btn btn--primary" disabled={!input.trim() || busy}>
              <Send size={16} aria-hidden="true" />
              Gửi
            </button>
          </form>
        </section>

        <aside className="flex flex-col gap-3 min-w-0">
          <section className="panel" aria-labelledby="clip-title">
            <div className="panel-head">
              <h2 id="clip-title">Đoạn clip</h2>
              {clip && <span className="sub">{cameraLabel(clip.camera)}</span>}
            </div>
            {clip ? (
              <div className="panel-body flex flex-col gap-3">
                <CameraView cam={cameraDef(clip.camera)} still={clip.t} highlight={clip.table} />
                <div>
                  <p className="ink2">{clip.title}</p>
                  <p className="small muted mt-1">
                    Từ <span className="measured cool">{clock(clip.t - 10)}</span> đến <span className="measured cool">{clock(clip.t + 10)}</span>, cắt từ video gốc đủ khung hình
                  </p>
                </div>
                <button type="button" className="btn self-start" onClick={() => toast('Bản demo không có video thật. Bản chạy ở quán sẽ cắt clip từ đầu ghi theo đúng mốc giờ này.')}>
                  <Play size={16} aria-hidden="true" />
                  Phát clip gốc
                </button>
              </div>
            ) : (
              <Empty title="Chưa chọn đoạn clip">
                <p>Bấm vào một mốc giờ trong câu trả lời để xem khung hình tương ứng.</p>
              </Empty>
            )}
          </section>
          <section className="panel" aria-labelledby="how-title">
            <div className="panel-head">
              <h2 id="how-title">Cách trợ lý tìm câu trả lời</h2>
            </div>
            <ol className="suggest-list small">
              <li>Tra nhật ký sự kiện có cấu trúc: ai, bàn nào, làm gì, lúc nào.</li>
              <li>Nếu chưa đủ, tìm theo mô tả cảnh do mô hình thị giác viết sẵn.</li>
              <li>Khi cần chi tiết, cho mô hình xem lại đúng đoạn clip đó.</li>
              <li>Không có bằng chứng thì nói thẳng là không tìm thấy.</li>
            </ol>
          </section>
        </aside>
      </div>
    </div>
  );
}
