import { useRef, useState } from 'react';
import { Sparkles } from 'lucide-react';
import { Button } from '@astryxdesign/core/Button';
import { ChatComposer, ChatLayout, ChatMessage, ChatMessageBubble, ChatMessageList } from '@astryxdesign/core/Chat';
import { EmptyState } from '@astryxdesign/core/EmptyState';
import { Markdown } from '@astryxdesign/core/Markdown';
import { Text } from '@astryxdesign/core/Text';
import { askAssistant, errorMessage } from '../live/api';
import { useTitle } from '../live/hooks';
import type { AssistantAnswer } from '../live/types';
import { Blocks } from './blocks';

const STARTERS = [
  'Hôm nay nhân viên làm việc thế nào?',
  'Hôm nay có gì đáng chú ý không?',
  'Khách phải chờ lâu nhất ở bàn nào?',
  'Việc theo từng giờ trong ca',
  'Ai vào ca lúc mấy giờ?',
];

interface Msg {
  id: number;
  role: 'user' | 'assistant';
  text: string;
  answer?: AssistantAnswer;
  failed?: boolean;
}

/** Một mã phiên cho mỗi tab, để trợ lý nhớ câu trước (hỏi tiếp "còn Vy thì sao?") */
function sessionId() {
  try {
    let id = sessionStorage.getItem('ez-assistant');
    if (!id) {
      id = crypto.randomUUID?.() ?? String(Date.now());
      sessionStorage.setItem('ez-assistant', id);
    }
    return id;
  } catch {
    return undefined;
  }
}

function engineNote(a: AssistantAnswer) {
  const took = a.ms != null ? `, ${(a.ms / 1000).toLocaleString('vi-VN', { maximumFractionDigits: 1 })} giây` : '';
  if (a.engine === 'adk') return `${a.model ?? 'Gemini'} qua Google ADK${took}`;
  if (a.engine === 'rules') return 'Trả lời từ số liệu của ca, chưa dùng AI';
  return undefined;
}

/** Hỏi đáp về ca làm: câu trả lời kèm số liệu, biểu đồ, sự kiện có hình, bảng */
export default function Assistant() {
  useTitle('Trợ lý, Easy FnB');
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [busy, setBusy] = useState(false);
  const [draft, setDraft] = useState('');
  const seq = useRef(1);

  const ask = async (q: string) => {
    const question = q.trim();
    if (!question || busy) return;
    setDraft('');
    setBusy(true);
    setMsgs((m) => [...m, { id: seq.current++, role: 'user', text: question }]);
    try {
      const answer = await askAssistant(question, sessionId());
      setMsgs((m) => [...m, { id: seq.current++, role: 'assistant', text: answer.answer, answer }]);
    } catch (err) {
      setMsgs((m) => [...m, { id: seq.current++, role: 'assistant', text: errorMessage(err), failed: true }]);
    } finally {
      setBusy(false);
    }
  };

  const last = msgs.at(-1);

  return (
    <div className="fx-chat-page">
      <ChatLayout
        composer={<ChatComposer value={draft} onChange={setDraft} onSubmit={(v) => void ask(v)} placeholder="Hỏi về ca hôm nay, ví dụ: bàn nào chờ lâu nhất?" isDisabled={busy} />}
        emptyState={
          <EmptyState
            icon={<Sparkles size={28} />}
            title="Hỏi bất cứ điều gì về ca hôm nay"
            description="Trợ lý xem lại toàn bộ việc camera đã ghi: ai làm gì, bàn nào chờ lâu, lúc nào đông. Câu trả lời kèm số liệu, biểu đồ và hình lúc xảy ra."
            actions={
              <div className="fx-suggest justify-center">
                {STARTERS.map((s) => (
                  <Button key={s} label={s} variant="secondary" size="sm" onClick={() => void ask(s)} />
                ))}
              </div>
            }
          />
        }
      >
        {msgs.length > 0 && (
          <ChatMessageList isStreaming={busy}>
            {msgs.map((m) =>
              m.role === 'user' ? (
                <ChatMessage key={m.id} sender="user">
                  <ChatMessageBubble>{m.text}</ChatMessageBubble>
                </ChatMessage>
              ) : (
                <ChatMessage key={m.id} sender="assistant" name="Trợ lý" metadata={m.answer ? engineNote(m.answer) : undefined}>
                  <ChatMessageBubble variant="ghost" width="100%">
                    <div className="flex flex-col gap-3 min-w-0">
                      {m.failed ? (
                        <Text type="body" color="secondary" as="p">
                          Chưa trả lời được: {m.text}
                        </Text>
                      ) : (
                        <Markdown density="compact">{m.text}</Markdown>
                      )}
                      {m.answer?.blocks?.length ? <Blocks blocks={m.answer.blocks} /> : null}
                      {m === last && !busy && m.answer?.suggestions?.length ? (
                        <div className="fx-suggest">
                          {m.answer.suggestions.map((s) => (
                            <Button key={s} label={s} variant="secondary" size="sm" onClick={() => void ask(s)} />
                          ))}
                        </div>
                      ) : null}
                    </div>
                  </ChatMessageBubble>
                </ChatMessage>
              ),
            )}
            {busy && (
              <ChatMessage sender="assistant" name="Trợ lý">
                <ChatMessageBubble variant="ghost">
                  <span className="fx-thinking" role="status">
                    <span className="fx-thinking-dots" aria-hidden="true">
                      <i />
                      <i />
                      <i />
                    </span>
                    <Text type="body" color="secondary">
                      Đang xem lại ca…
                    </Text>
                  </span>
                </ChatMessageBubble>
              </ChatMessage>
            )}
          </ChatMessageList>
        )}
      </ChatLayout>
    </div>
  );
}
