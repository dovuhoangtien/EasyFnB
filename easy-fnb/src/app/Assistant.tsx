import { useRef, useState } from 'react';
import { Sparkles } from 'lucide-react';
import { Button } from '@astryxdesign/core/Button';
import { ChatComposer, ChatDictationButton, ChatLayout, ChatMessage, ChatMessageBubble, ChatMessageList, useSpeechRecognition } from '@astryxdesign/core/Chat';
import { EmptyState } from '@astryxdesign/core/EmptyState';
import { Markdown } from '@astryxdesign/core/Markdown';
import { Text } from '@astryxdesign/core/Text';
import { askAssistant, errorMessage } from '../live/api';
import { useTitle } from '../live/hooks';
import type { AssistantAnswer } from '../live/types';
import { Blocks } from './blocks';
import { SetupContext } from './setupBlocks';

const STARTERS = [
  'Cho xem lại lần khách chờ lâu nhất',
  'Bàn nào đang chờ lâu?',
  'Nên đổi gì cho ca sau?',
  'Hôm nay nhân viên làm việc thế nào?',
  'Hôm nay thu được bao nhiêu?',
];

/** câu cài đặt: chữ chờ là "Đang làm…" (tìm bàn mất tới 12 giây) */
const SETUP_WORDS = /cài|setup|thiết lập|nối camera|tìm bàn|thêm|bỏ nhân viên|mã qr|luật báo|chụp/i;

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


/** Hỏi đáp về ca làm: câu trả lời kèm số liệu, biểu đồ, sự kiện có hình, bảng */
export default function Assistant() {
  useTitle('Trợ lý, Easy FnB');
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [busy, setBusy] = useState(false);
  const [draft, setDraft] = useState('');
  const seq = useRef(1);
  /** việc vừa bấm Lưu trong khối cài đặt, gửi kèm câu hỏi kế tiếp để trợ lý biết dữ liệu đã đổi */
  const notes = useRef<string[]>([]);
  const [doing, setDoing] = useState(false);

  const ask = async (q: string) => {
    const question = q.trim();
    if (!question || busy) return;
    setDraft('');
    setBusy(true);
    setDoing(SETUP_WORDS.test(question));
    setMsgs((m) => [...m, { id: seq.current++, role: 'user', text: question }]);
    try {
      const note = notes.current.splice(0).join('; ');
      const answer = await askAssistant(question, sessionId(), note || undefined);
      setMsgs((m) => [...m, { id: seq.current++, role: 'assistant', text: answer.answer, answer }]);
    } catch (err) {
      setMsgs((m) => [...m, { id: seq.current++, role: 'assistant', text: errorMessage(err), failed: true }]);
    } finally {
      setBusy(false);
    }
  };

  const last = msgs.at(-1);
  // hỏi bằng lời: nói xong một câu thì gửi luôn
  const dictation = useSpeechRecognition({ lang: 'vi-VN', onResult: (text) => void ask(text) });

  return (
    <div className="fx-chat-page">
      <SetupContext.Provider value={{ ask: (q) => void ask(q), saved: (n) => void notes.current.push(n) }}>
      <ChatLayout
        composer={<ChatComposer value={draft} onChange={setDraft} onSubmit={(v) => void ask(v)} placeholder="Hỏi về ca hôm nay hoặc bất cứ chuyện gì của quán" isDisabled={busy} sendActions={<ChatDictationButton dictation={dictation} label="Hỏi bằng lời" isHiddenWhenUnsupported />} />}
        emptyState={
          <EmptyState
            icon={<Sparkles size={28} />}
            title="Hỏi gì cũng được"
            description="Trợ lý xem lại mọi việc camera đã ghi, khuyên nên đổi gì cho ca sau, và trả lời cả chuyện quản lý quán. Câu trả lời về ca kèm số liệu, biểu đồ và hình lúc xảy ra."
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
                <ChatMessage key={m.id} sender="assistant" name="Trợ lý">
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
                      {doing ? 'Đang làm…' : 'Đang xem lại ca…'}
                    </Text>
                  </span>
                </ChatMessageBubble>
              </ChatMessage>
            )}
          </ChatMessageList>
        )}
      </ChatLayout>
      </SetupContext.Provider>
    </div>
  );
}
