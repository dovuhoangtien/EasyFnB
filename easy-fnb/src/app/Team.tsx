import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { Camera, CircleCheck, CircleHelp, ListChecks, MessagesSquare, Sparkles } from 'lucide-react';
import { Avatar } from '@astryxdesign/core/Avatar';
import { Badge } from '@astryxdesign/core/Badge';
import { Banner } from '@astryxdesign/core/Banner';
import { Button } from '@astryxdesign/core/Button';
import { ChatComposer, ChatLayout, ChatMessage, ChatMessageBubble, ChatMessageList, ChatMessageMetadata } from '@astryxdesign/core/Chat';
import { Dialog, DialogHeader } from '@astryxdesign/core/Dialog';
import { EmptyState } from '@astryxdesign/core/EmptyState';
import { IconButton } from '@astryxdesign/core/IconButton';
import { Markdown } from '@astryxdesign/core/Markdown';
import { Text } from '@astryxdesign/core/Text';
import { errorMessage } from '../live/api';
import { chatImageUrl, clockText, money, patchPayment, PAYMENT_TYPE_LABEL, postMessage, useChatRoom, voidPayment, type ChatMsg, type Payment, type PaymentFields } from '../live/chat';
import { useTitle } from '../live/hooks';
import { useLive } from '../live/store';
import type { Staff } from '../live/types';
import { PaymentForm, ScanFlow } from './Scan';
import { Shot } from './ui';

const OWNER = 'chu';
/** Tên trợ lý trong phòng chat (khớp AI_NAME ở server/chat.py) */
const AI_NAME = 'Tam';

function nameOf(staff: Staff[], id: string) {
  if (id === OWNER) return 'Chủ quán';
  if (id === 'ai') return AI_NAME;
  return staff.find((s) => s.id === id)?.name ?? id;
}

/** Chủ quán: màn hình quản lý ("chu") hoặc nhân viên có vai trò owner (server/an_ninh.py) */
const isOwner = (staff: Staff[], id: string) => id === OWNER || staff.find((s) => s.id === id)?.role === 'owner';

const fold = (s: string) =>
  s
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/đ/g, 'd')
    .replace(/Đ/g, 'D')
    .toLowerCase();

/** "@Minh mang đá ra" thì chỉ gửi cho Minh; không nhắc ai thì gửi cả quán */
function recipients(text: string, staff: Staff[]): string[] {
  const t = fold(text);
  const ids = staff.filter((s) => t.includes(`@${fold(s.name)}`)).map((s) => s.id);
  if (t.includes('@chu')) ids.push(OWNER, ...staff.filter((s) => s.role === 'owner').map((s) => s.id));
  return ids.length ? ids : ['*'];
}

/** Chọn ảnh từ camera sau rồi mở màn quét. `children` nhận hàm mở camera. */
export function Scanner({ me, onSent, children }: { me: string; onSent?: (m: ChatMsg) => void; children: (open: () => void) => ReactNode }) {
  const input = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [key, setKey] = useState(0);
  const open = () => {
    if (input.current) input.current.value = '';
    input.current?.click();
  };
  return (
    <>
      <input
        ref={input}
        type="file"
        accept="image/*"
        capture="environment"
        hidden
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) {
            setFile(f);
            setKey((k) => k + 1);
          }
        }}
      />
      {children(open)}
      {file && (
        <ScanFlow
          key={key}
          me={me}
          file={file}
          onClose={() => setFile(null)}
          onRetake={() => {
            setFile(null);
            open();
          }}
          onSent={(m) => {
            setFile(null);
            onSent?.(m);
          }}
        />
      )}
    </>
  );
}

function EditPayment({ p, me, onClose }: { p: Payment; me: string; onClose: () => void }) {
  const [v, setV] = useState<PaymentFields>(p);
  const [busy, setBusy] = useState<'save' | 'void' | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const run = async (what: 'save' | 'void') => {
    setBusy(what);
    setErr(null);
    try {
      if (what === 'save') await patchPayment(p.id, me, v);
      else await voidPayment(p.id, me, 'Huỷ trong phòng chat');
      onClose();
    } catch (e) {
      setErr(errorMessage(e));
      setBusy(null);
    }
  };
  return (
    <>
      <DialogHeader title="Sửa thanh toán" subtitle="Mọi lần sửa đều được ghi lại." onOpenChange={onClose} />
      <div className="flex flex-col gap-4" style={{ paddingInline: 16, paddingBottom: 12 }}>
        <PaymentForm value={v} onChange={setV} />
        {err && <Banner status="error" title={err} collapsible={false} />}
        <div className="flex justify-between gap-2">
          <Button label="Huỷ thanh toán này" variant="ghost" isLoading={busy === 'void'} onClick={() => void run('void')} />
          <Button label="Lưu" variant="primary" isLoading={busy === 'save'} onClick={() => void run('save')} />
        </div>
      </div>
    </>
  );
}

function PaymentCard({ p, canEdit, me }: { p: Payment; canEdit: boolean; me: string }) {
  const [editing, setEditing] = useState(false);
  const isVoid = p.status === 'void';
  const media = p.image ? [{ src: chatImageUrl(p.image), alt: `Ảnh ${PAYMENT_TYPE_LABEL[p.type].toLowerCase()} ${money(p.amount)}`, caption: PAYMENT_TYPE_LABEL[p.type] }] : [];
  const detail = [p.bank, p.sender_name, p.memo ? `“${p.memo}”` : null, p.receipt_no ? `Số ${p.receipt_no}` : null].filter(Boolean).join(', ');
  return (
    <div className="fx-pay" data-void={isVoid || undefined}>
      <Shot media={media} size={76} />
      <div className="fx-pay-body">
        <div className="flex flex-wrap items-center gap-2">
          <Text type="label" color="secondary">
            {PAYMENT_TYPE_LABEL[p.type]}
            {p.table ? `, bàn ${p.table}` : ''}
            {p.paid_at ? `, ${p.paid_at}` : ''}
          </Text>
          {isVoid && <Badge variant="error" label="Đã huỷ" />}
        </div>
        <p className="fx-pay-amount fx-num">{money(p.amount)}</p>
        {detail && (
          <Text type="supporting" color="secondary" as="p" className="fx-pay-detail">
            {detail}
          </Text>
        )}
        {!isVoid && p.match && (
          <span className="fx-pay-match" data-ok={p.match.ok || undefined}>
            {p.match.ok ? <CircleCheck size={14} aria-hidden="true" /> : <CircleHelp size={14} aria-hidden="true" />}
            {p.match.text}
          </span>
        )}
        {canEdit && !isVoid && (
          <div>
            <Button label="Sửa" variant="ghost" size="sm" onClick={() => setEditing(true)} />
          </div>
        )}
      </div>
      {editing && (
        <Dialog isOpen onOpenChange={(o) => !o && setEditing(false)} width={460} purpose="form">
          <EditPayment p={p} me={me} onClose={() => setEditing(false)} />
        </Dialog>
      )}
    </div>
  );
}

function Bubble({ m, me, staff }: { m: ChatMsg; me: string; staff: Staff[] }) {
  const mine = m.sender === me;
  const isAi = m.sender === 'ai';
  const name = nameOf(staff, m.sender);
  const toLine = m.to.includes('*') ? null : `Gửi ${m.to.map((id) => nameOf(staff, id)).join(', ')}`;
  const meta = <ChatMessageMetadata timestamp={clockText(m.ts)} footer={toLine ?? undefined} />;
  const avatar = isAi ? (
    <span className="fx-ai-avatar" aria-hidden="true">
      <Sparkles size={15} />
    </span>
  ) : (
    <Avatar name={name} size="sm" tooltip={false} />
  );
  let body: ReactNode;
  if (m.kind === 'payment' && m.payment) {
    body = (
      <ChatMessageBubble variant="ghost" width="100%">
        <PaymentCard p={m.payment} me={me} canEdit={isOwner(staff, me) || m.payment.staff === me} />
      </ChatMessageBubble>
    );
  } else if (m.kind === 'photo' && m.image) {
    body = (
      <ChatMessageBubble variant="ghost">
        <div className="flex flex-col gap-2">
          <Shot media={[{ src: chatImageUrl(m.image), alt: `Ảnh ${name} gửi` }]} size={160} />
          {m.text ? <span>{m.text}</span> : null}
        </div>
      </ChatMessageBubble>
    );
  } else if (isAi) {
    body = (
      <ChatMessageBubble variant="ghost">
        <Markdown density="compact">{m.text ?? ''}</Markdown>
      </ChatMessageBubble>
    );
  } else {
    body = <ChatMessageBubble>{m.text}</ChatMessageBubble>;
  }
  return (
    <ChatMessage sender={mine ? 'user' : 'assistant'} name={mine ? undefined : name} avatar={mine ? undefined : avatar} metadata={meta}>
      {body}
    </ChatMessage>
  );
}

type Room = ReturnType<typeof useChatRoom>;

/** Phòng chat của quán. `me` là "chu" (chủ quán) hoặc id nhân viên. */
export function TeamRoom({ me }: { me: string }) {
  return <RoomView me={me} room={useChatRoom()} />;
}

function RoomView({ me, room }: { me: string; room: Room }) {
  const staff = useLive((s) => s.staff);
  const { messages, loaded, aiBusy, merge } = room;
  const [draft, setDraft] = useState('');
  const [sending, setSending] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const send = async (text: string) => {
    const t = text.trim();
    if (!t || sending) return;
    setSending(true);
    setErr(null);
    try {
      merge([await postMessage(me, t, recipients(t, staff))]);
      setDraft('');
    } catch (e) {
      setErr(errorMessage(e));
    } finally {
      setSending(false);
    }
  };

  const visible = useMemo(() => messages.filter((m) => m.to.includes('*') || m.to.includes(me) || m.sender === me || isOwner(staff, me)), [messages, me, staff]);

  return (
    <Scanner me={me} onSent={(m) => merge([m])}>
      {(openCamera) => (
        <ChatLayout
          composer={
            <ChatComposer
              value={draft}
              onChange={setDraft}
              onSubmit={(v) => void send(v)}
              placeholder="Nhắn cả quán, @tên để gửi riêng, @Tam để hỏi"
              isDisabled={sending}
              status={err ? { type: 'error', message: err } : undefined}
              sendActions={<IconButton label="Chụp chuyển khoản hoặc hoá đơn" tooltip="Chụp thanh toán" variant="ghost" icon={<Camera size={18} />} onClick={openCamera} />}
            />
          }
          emptyState={
            loaded ? (
              <EmptyState
                icon={<MessagesSquare size={28} />}
                title="Chưa có tin nào hôm nay"
                description="Nhắn cả quán, chụp chuyển khoản hay hoá đơn để gửi vào đây. Gõ @Tam để hỏi về ca."
                actions={<Button label="Chụp thanh toán" variant="secondary" icon={<Camera size={16} />} onClick={openCamera} />}
              />
            ) : (
              <EmptyState title="Đang tải tin nhắn" />
            )
          }
        >
          {visible.length > 0 && (
            <ChatMessageList isStreaming={aiBusy}>
              {visible.map((m) => (
                <Bubble key={m.id} m={m} me={me} staff={staff} />
              ))}
              {aiBusy && (
                <ChatMessage sender="assistant" name={AI_NAME}>
                  <ChatMessageBubble variant="ghost">
                    <span className="fx-thinking" role="status">
                      <span className="fx-thinking-dots" aria-hidden="true">
                        <i />
                        <i />
                        <i />
                      </span>
                      <Text type="body" color="secondary">
                        {AI_NAME} đang trả lời
                      </Text>
                    </span>
                  </ChatMessageBubble>
                </ChatMessage>
              )}
            </ChatMessageList>
          )}
        </ChatLayout>
      )}
    </Scanner>
  );
}

/** Trang "Nhắn nhóm" của chủ quán */
export default function TeamPage() {
  useTitle('Nhắn nhóm, Easy FnB');
  return (
    <div className="fx-chat-page">
      <TeamRoom me={OWNER} />
    </div>
  );
}

const seenKey = (me: string) => `ez-chat-seen-${me}`;
function readSeen(me: string) {
  try {
    return Number(localStorage.getItem(seenKey(me)) ?? 0) || 0;
  } catch {
    return 0;
  }
}

/**
 * App nhân viên: thanh dưới "Việc / Nhóm / Chụp". `children` là màn hình việc hiện có.
 * Tin chat không đọc to; tin gửi đích danh mình thì rung nhẹ một lần.
 */
export function StaffTeam({ me, children }: { me: string; children: ReactNode }) {
  const room = useChatRoom();
  const [tab, setTabState] = useState<'viec' | 'nhom'>('viec');
  const [seen, setSeen] = useState(() => readSeen(me));
  const lastId = room.messages.at(-1)?.id ?? 0;
  const latest = room.messages.at(-1);
  const unread = tab === 'nhom' ? 0 : room.messages.filter((m) => m.id > seen && m.sender !== me && (m.to.includes('*') || m.to.includes(me))).length;

  // rời hoặc vào mục Nhóm thì coi như đã đọc hết tin tới lúc đó
  const setTab = (next: 'viec' | 'nhom') => {
    if (next !== tab && lastId) {
      setSeen(lastId);
      try {
        localStorage.setItem(seenKey(me), String(lastId));
      } catch {
        // trình duyệt chặn bộ nhớ: chỉ mất số tin chưa đọc
      }
    }
    setTabState(next);
  };

  const buzzed = useRef(0);
  useEffect(() => {
    if (!latest || latest.id <= buzzed.current) return;
    const first = buzzed.current === 0;
    buzzed.current = latest.id;
    if (!first && latest.sender !== me && latest.to.includes(me) && 'vibrate' in navigator) navigator.vibrate(120);
  }, [latest, me]);

  return (
    <>
      {tab === 'viec' ? (
        children
      ) : (
        <div className="fx-phone-room">
          <RoomView me={me} room={room} />
        </div>
      )}
      <div className="fx-phone-tabs-space" aria-hidden="true" />
      <Scanner me={me} onSent={(m) => {
        room.merge([m]);
        setTab('nhom');
      }}>
        {(openCamera) => (
          <nav className="fx-phone-tabs" aria-label="Chuyển màn hình">
            <button type="button" aria-current={tab === 'viec' ? 'page' : undefined} onClick={() => setTab('viec')}>
              <ListChecks size={20} aria-hidden="true" />
              <span>Việc</span>
            </button>
            <button type="button" aria-current={tab === 'nhom' ? 'page' : undefined} onClick={() => setTab('nhom')}>
              <MessagesSquare size={20} aria-hidden="true" />
              <span>Nhóm</span>
              {unread > 0 && tab !== 'nhom' && <span className="fx-phone-tabs-count">{unread > 9 ? '9+' : unread}</span>}
            </button>
            <button type="button" className="fx-phone-tabs-shoot" onClick={openCamera}>
              <Camera size={20} aria-hidden="true" />
              <span>Chụp</span>
            </button>
          </nav>
        )}
      </Scanner>
    </>
  );
}
