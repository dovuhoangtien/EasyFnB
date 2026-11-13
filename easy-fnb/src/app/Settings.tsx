import { useState } from 'react';
import { useSearchParams } from 'react-router';
import { Copy, PlugZap, Plus, RotateCcw, Trash } from 'lucide-react';
import { AlertDialog } from '@astryxdesign/core/AlertDialog';
import { Badge } from '@astryxdesign/core/Badge';
import { Banner } from '@astryxdesign/core/Banner';
import { Button } from '@astryxdesign/core/Button';
import { Card } from '@astryxdesign/core/Card';
import { EmptyState } from '@astryxdesign/core/EmptyState';
import { IconButton } from '@astryxdesign/core/IconButton';
import { NumberInput } from '@astryxdesign/core/NumberInput';
import { Selector } from '@astryxdesign/core/Selector';
import { StatusDot } from '@astryxdesign/core/StatusDot';
import { Switch } from '@astryxdesign/core/Switch';
import { Tab, TabList } from '@astryxdesign/core/TabList';
import { Text } from '@astryxdesign/core/Text';
import { TextInput } from '@astryxdesign/core/TextInput';
import { useToast } from '@astryxdesign/core/Toast';
import { putSettings, putStaff, resetShift, testAi, type AiTest, type Info } from '../live/api';
import { useInfo, useRun, useTitle } from '../live/hooks';
import { live, useLive, useServerNow } from '../live/store';
import { CAMERA_AGENT_CMD, cameraLive, ROLE_LABEL, slugify } from '../live/text';
import { ROLES, type Role, type SettingsPatch, type StaffInput } from '../live/types';
import { ZoneEditor } from '../live/ZoneEditor';
import { QrCode } from './QrCode';
import { SectionTitle, voiceText } from './ui';

const TABS = [
  { value: 'vung-ban', label: 'Vùng bàn' },
  { value: 'nhan-vien', label: 'Nhân viên' },
  { value: 'camera', label: 'Kết nối' },
];

// ---------- nhân viên ----------
interface Row {
  key: number;
  /** null: người mới, mã tạo từ tên lúc lưu */
  id: string | null;
  name: string;
  role: Role;
}
let rowKey = 1000;

function StaffEditor() {
  const staff = useLive((s) => s.staff);
  const { busy, run } = useRun();
  const [rows, setRows] = useState<Row[] | null>(null);
  const view: Row[] = rows ?? staff.map((s, i) => ({ key: i, id: s.id, name: s.name, role: s.role }));
  const dirty = rows !== null;
  const hasEmpty = view.some((r) => !r.name.trim());
  const update = (key: number, patch: Partial<Row>) => setRows(view.map((r) => (r.key === key ? { ...r, ...patch } : r)));

  const save = async () => {
    const used = new Set(view.filter((r) => r.id).map((r) => r.id as string));
    const list: StaffInput[] = view.map((r) => {
      let id = r.id;
      if (!id) {
        const base = slugify(r.name) || 'nv';
        id = base;
        for (let n = 2; used.has(id); n++) id = `${base}${n}`;
        used.add(id);
      }
      return { id, name: r.name.trim(), role: r.role };
    });
    const out = await run('staff', () => putStaff(list), `Đã lưu ${list.length} nhân viên`);
    if (out) {
      live.setStaff(out);
      setRows(null);
    }
  };

  return (
    <Card padding={4}>
      <div className="flex flex-col gap-4" style={{ maxWidth: 620 }}>
        <SectionTitle end={<Button label="Thêm người" variant="secondary" size="sm" icon={<Plus size={15} />} onClick={() => setRows([...view, { key: rowKey++, id: null, name: '', role: 'serve' }])} />}>
          Nhân viên trong ca
        </SectionTitle>
        <Text type="supporting" color="secondary" as="p">
          Việc gọi phục vụ và khách mới giao cho người Phục vụ, bàn cần dọn giao cho người Dọn bàn. Link app của từng người nằm ở nút App nhân viên trên thanh trên cùng.
        </Text>
        {view.length === 0 && <EmptyState isCompact title="Chưa có nhân viên" description="Thêm ít nhất một người để hệ thống có người giao việc." />}
        {view.map((r) => (
          <div key={r.key} className="fx-staff-row">
            <TextInput label="Tên" isLabelHidden placeholder="Tên, ví dụ Lan" value={r.name} onChange={(v) => update(r.key, { name: v.slice(0, 30) })} />
            <Selector label="Vai trò" isLabelHidden value={r.role} options={ROLES.map((role) => ({ value: role, label: ROLE_LABEL[role] }))} onChange={(v) => update(r.key, { role: v as Role })} />
            <IconButton label={`Bỏ ${r.name || 'dòng này'}`} tooltip="Bỏ" variant="ghost" icon={<Trash size={16} />} onClick={() => setRows(view.filter((x) => x.key !== r.key))} />
          </div>
        ))}
        {dirty && (
          <div className="flex items-center gap-2">
            <Button label="Lưu" variant="primary" isLoading={busy === 'staff'} isDisabled={hasEmpty} onClick={() => void save()} />
            <Button label="Bỏ thay đổi" variant="ghost" onClick={() => setRows(null)} />
            {hasEmpty && (
              <Text type="supporting" color="secondary">
                Còn dòng chưa có tên.
              </Text>
            )}
          </div>
        )}
      </div>
    </Card>
  );
}

// ---------- kết nối: camera, AI, quy tắc, ca ----------
const LOCAL = new Set(['localhost', '127.0.0.1', '[::1]']);

/** Địa chỉ máy chủ để máy camera gửi về: trên Cloud Run là chính địa chỉ trang, chạy ở quán là địa chỉ Wi-Fi */
function serverUrl(info: Info | null) {
  if (!LOCAL.has(location.hostname)) return location.origin;
  const port = import.meta.env.DEV ? '8080' : location.port || '80';
  return `http://${info?.lan_ip ?? 'localhost'}:${port}`;
}

function CopyBlock({ text, label }: { text: string; label: string }) {
  const toast = useToast();
  const copy = () => {
    navigator.clipboard
      .writeText(text)
      .then(() => toast({ body: 'Đã chép' }))
      .catch(() => toast({ body: 'Không chép được, hãy bôi đen rồi chép tay.', type: 'error', isAutoHide: true }));
  };
  return (
    <div className="flex items-start gap-2">
      <pre className="fx-code">{text}</pre>
      <IconButton label={label} tooltip={label} variant="secondary" icon={<Copy size={16} />} onClick={copy} />
    </div>
  );
}

function CameraCard({ info }: { info: Info | null }) {
  const cameras = useLive((s) => s.cameras);
  const now = useServerNow();
  const url = serverUrl(info);
  const cmd = CAMERA_AGENT_CMD.replace('http://<địa chỉ máy chủ>:8080', url) + (info?.edge_key ? ' --khoa <khoá EDGE_KEY>' : '');
  return (
    <Card padding={4}>
      <div className="flex flex-col gap-3">
        <SectionTitle>Camera</SectionTitle>
        {cameras.length === 0 && (
          <Text type="body" color="secondary" as="p">
            Chưa có camera nào gửi hình về máy chủ.
          </Text>
        )}
        {cameras.map((c) => {
          const on = cameraLive(c, now);
          return (
            <div key={c.id} className="flex items-center gap-3">
              <StatusDot variant={on ? 'success' : 'neutral'} label={on ? 'Đang gửi hình' : 'Không có hình'} isPulsing={on} />
              <Text type="label" weight="semibold">
                {c.name || c.id}
              </Text>
              <Text type="supporting" color="secondary" hasTabularNumbers>
                {on ? `đang gửi hình${c.fps ? `, ${Math.round(c.fps)} khung/giây` : ''}` : 'không có hình'}
              </Text>
            </div>
          );
        })}
        <Text type="supporting" color="secondary" as="p">
          Để nối một camera, chạy lệnh này trên máy có camera, trong thư mục <code>vision-test</code>. Địa chỉ máy chủ đã điền sẵn.
        </Text>
        <CopyBlock text={cmd} label="Chép lệnh" />
        <PhoneCameraQr info={info} />
        {info?.edge_key && (
          <Text type="supporting" color="secondary" as="p">
            Máy chủ đang yêu cầu khoá cho máy camera chạy lệnh (EDGE_KEY).
          </Text>
        )}
      </div>
    </Card>
  );
}

const PHONE_CAMS = ['cam1', 'cam2', 'cam3', 'cam4'];

/** Địa chỉ trang /phat cho một camera. Camera điện thoại bắt buộc https: trên Cloud Run đã có sẵn, chạy ở quán thì cần cổng https của máy chủ. */
function phoneCameraUrl(info: Info | null, cam: string) {
  const path = `/phat?cam=${encodeURIComponent(cam)}`;
  if (!LOCAL.has(location.hostname)) {
    // mở dashboard bằng địa chỉ wifi qua http mà máy chủ có cổng https: mã QR phải trỏ sang cổng https đó
    if (location.protocol !== 'https:' && info?.https_port) return { url: `https://${location.hostname}:${info.https_port}${path}`, secure: true };
    return { url: `${location.origin}${path}`, secure: location.protocol === 'https:' };
  }
  const host = info?.lan_ip ?? 'localhost';
  if (info?.https_port) return { url: `https://${host}:${info.https_port}${path}`, secure: true };
  const port = import.meta.env.DEV ? '8080' : location.port || '80';
  return { url: `http://${host}:${port}${path}`, secure: false };
}

function PhoneCameraQr({ info }: { info: Info | null }) {
  const [cam, setCam] = useState(PHONE_CAMS[0]);
  const { url, secure } = phoneCameraUrl(info, cam);
  return (
    <div className="flex flex-col gap-3">
      <Text type="label" weight="semibold" as="p">
        Dùng điện thoại làm camera
      </Text>
      <div className="flex flex-wrap gap-2" role="group" aria-label="Chọn camera">
        {PHONE_CAMS.map((c) => (
          <Button key={c} label={c} size="sm" variant={c === cam ? 'primary' : 'secondary'} onClick={() => setCam(c)} />
        ))}
      </div>
      <div className="flex flex-wrap items-center gap-4">
        <QrCode value={url} size={150} label={`Mã QR mở điện thoại làm camera ${cam}`} />
        <div className="flex min-w-0 flex-1 flex-col gap-2" style={{ minWidth: 200 }}>
          <Text type="supporting" color="secondary" as="p">
            Quét mã bằng điện thoại sẽ dùng, rồi bấm “Bắt đầu phát”. Dựng điện thoại cố định nhìn xuống các bàn và cắm sạc.
          </Text>
          <CopyBlock text={url} label="Chép link camera" />
        </div>
      </div>
      {!secure && (
        <Banner
          status="warning"
          title="Link này là http nên điện thoại sẽ chặn camera"
          description="Chạy máy chủ với --https (cổng 8443, trình duyệt sẽ cảnh báo chứng chỉ tự ký), hoặc dùng bản đã triển khai trên Cloud Run."
          collapsible={false}
        />
      )}
    </div>
  );
}

function AiCard({ info }: { info: Info | null }) {
  const settings = useLive((s) => s.settings);
  const [testing, setTesting] = useState(false);
  const [result, setResult] = useState<AiTest | null>(null);
  const on = settings?.gemini ?? info?.gemini ?? false;
  const provider = settings?.provider ?? info?.provider ?? 'Gemini';
  const keyName = info?.key_name ?? 'GEMINI_API_KEY';

  const test = async () => {
    setTesting(true);
    setResult(null);
    try {
      setResult(await testAi());
    } catch (err) {
      setResult({ ok: false, error: err instanceof Error ? err.message : 'Không gọi được máy chủ.' });
    } finally {
      setTesting(false);
    }
  };

  return (
    <Card padding={4}>
      <div className="flex flex-col gap-3">
        <SectionTitle end={<Badge variant={on ? 'success' : 'neutral'} label={on ? 'Đã nối' : 'Chưa có khoá'} />}>AI</SectionTitle>
        <div>
          <div className="fx-kv">
            <div className="min-w-0">
              <Text type="label" weight="semibold" as="p">
                Kiểm tra báo động
              </Text>
              <Text type="supporting" color="secondary" as="p">
                {on ? 'AI xem ảnh camera để lọc báo nhầm trước khi tới nhân viên.' : 'Đang tắt: mọi việc camera báo sẽ tới thẳng nhân viên.'}
              </Text>
            </div>
            <Text type="supporting" hasTabularNumbers>
              {on ? `${provider}${settings?.model ? `, ${settings.model}` : ''}` : 'Tắt'}
            </Text>
          </div>
          <div className="fx-kv">
            <div className="min-w-0">
              <Text type="label" weight="semibold" as="p">
                Trợ lý
              </Text>
              <Text type="supporting" color="secondary" as="p">
                {info?.assistant === 'adk' ? 'Hỏi bằng lời thường, AI tự tra số liệu của ca.' : 'Trả lời theo số liệu ca với các câu hỏi thường gặp.'}
              </Text>
            </div>
            <Text type="supporting">{info?.assistant === 'adk' ? `Gemini qua ADK${info.assistant_model ? `, ${info.assistant_model}` : ''}` : 'Theo số liệu'}</Text>
          </div>
          <div className="fx-kv">
            <div className="min-w-0">
              <Text type="label" weight="semibold" as="p">
                Giọng đọc cho nhân viên
              </Text>
              <Text type="supporting" color="secondary" as="p">
                Lời báo việc đọc qua tai nghe của nhân viên.
              </Text>
            </div>
            <Text type="supporting">{voiceText(info)}</Text>
          </div>
        </div>

        {!on && (
          <Text type="supporting" color="secondary" as="p">
            Để bật AI: thêm dòng <code>{keyName}=khoá của bạn</code> vào tệp <code>easy-fnb/.env</code> rồi chạy lại máy chủ. Trên Cloud Run, đặt biến môi trường <code>{keyName}</code> cho dịch vụ.
          </Text>
        )}

        <div className="flex items-center gap-3 flex-wrap">
          <Button label="Thử kết nối" variant="secondary" icon={<PlugZap size={15} />} isLoading={testing} isDisabled={!on} onClick={() => void test()} />
          {!on && (
            <Text type="supporting" color="secondary">
              Cần có khoá mới thử được.
            </Text>
          )}
        </div>
        <div aria-live="polite">
          {result &&
            (result.ok ? (
              <Banner status="success" title={`${result.provider ?? provider} trả lời sau ${result.ms ?? 0} ms`} description={result.model ? `Model ${result.model} dùng được.` : undefined} collapsible={false} />
            ) : (
              <Banner status="error" title="Chưa gọi được AI" description={result.error ?? 'Không rõ lỗi.'} collapsible={false} />
            ))}
        </div>
      </div>
    </Card>
  );
}

function RulesCard() {
  const settings = useLive((s) => s.settings);
  const { run } = useRun();
  const [draft, setDraft] = useState<{ escalate_s?: number; auto_close_s?: number }>({});
  if (!settings) return null;
  const ai = settings.gemini;
  const provider = settings.provider ?? 'Gemini';

  const save = async (patch: SettingsPatch, ok: string) => {
    const out = await run('settings', () => putSettings(patch), ok);
    if (out) live.setSettings(out);
  };
  const toggle = (list: string[], kind: string, on: boolean) => (on ? [...new Set([...list, kind])] : list.filter((k) => k !== kind));
  const commit = (key: 'escalate_s' | 'auto_close_s') => {
    const v = draft[key];
    if (v === undefined || v === (settings[key] ?? 0)) return;
    void save({ [key]: v }, 'Đã lưu').then(() => setDraft((d) => ({ ...d, [key]: undefined })));
  };

  return (
    <Card padding={4}>
      <div className="flex flex-col gap-4" style={{ maxWidth: 620 }}>
        <SectionTitle>Quy tắc báo việc</SectionTitle>
        {!ai && (
          <Text type="supporting" color="secondary" as="p">
            Ba công tắc đầu cần AI. Khi chưa có khoá, việc được báo thẳng cho nhân viên.
          </Text>
        )}
        <Switch
          label={`${provider} kiểm tra báo "khách gọi"`}
          description="Lọc các lần giơ tay nhầm như vuốt tóc, cầm điện thoại."
          value={settings.verify_kinds.includes('call')}
          isDisabled={!ai}
          changeAction={(on) => save({ verify_kinds: toggle(settings.verify_kinds, 'call', on) }, on ? 'Đã bật kiểm tra khách gọi' : 'Đã tắt kiểm tra khách gọi')}
        />
        <Switch
          label={`${provider} kiểm tra báo "cần dọn bàn"`}
          description="Xem ảnh bàn để chắc khách đã về và bàn còn bừa."
          value={settings.verify_kinds.includes('needs_clearing')}
          isDisabled={!ai}
          changeAction={(on) => save({ verify_kinds: toggle(settings.verify_kinds, 'needs_clearing', on) }, on ? 'Đã bật kiểm tra dọn bàn' : 'Đã tắt kiểm tra dọn bàn')}
        />
        <Switch
          label="Chờ AI xác nhận rồi mới báo dọn bàn"
          description="Tắt thì báo ngay, AI thấy nhầm sẽ huỷ sau."
          value={settings.hold_until_verified.includes('needs_clearing')}
          isDisabled={!ai || !settings.verify_kinds.includes('needs_clearing')}
          changeAction={(on) => save({ hold_until_verified: toggle(settings.hold_until_verified, 'needs_clearing', on) }, 'Đã lưu')}
        />
        <div className="grid gap-4 sm:grid-cols-2">
          <NumberInput
            label="Nhắc lại nếu chưa ai nhận sau"
            description="Hết giờ thì chuyển người khác. 0 là tắt."
            units="giây"
            min={0}
            max={900}
            isIntegerOnly
            value={draft.escalate_s ?? settings.escalate_s}
            onChange={(v) => setDraft((d) => ({ ...d, escalate_s: v }))}
            onBlur={() => commit('escalate_s')}
            onEnter={() => commit('escalate_s')}
          />
          <NumberInput
            label="Tự đóng việc không ai nhận sau"
            description="Khách gọi và khách mới. 0 là tắt."
            units="giây"
            min={0}
            max={3600}
            isIntegerOnly
            value={draft.auto_close_s ?? settings.auto_close_s ?? 0}
            onChange={(v) => setDraft((d) => ({ ...d, auto_close_s: v }))}
            onBlur={() => commit('auto_close_s')}
            onEnter={() => commit('auto_close_s')}
          />
        </div>
      </div>
    </Card>
  );
}

function ShiftCard() {
  const { busy, run } = useRun();
  const [confirm, setConfirm] = useState(false);
  const reset = async () => {
    const out = await run('reset', () => resetShift(), 'Đã bắt đầu ca mới');
    if (out) setConfirm(false);
  };
  return (
    <Card padding={4}>
      <div className="flex flex-col gap-3">
        <SectionTitle>Bắt đầu ca mới</SectionTitle>
        <Text type="body" color="secondary" as="p">
          Xoá toàn bộ việc, nhật ký và số liệu của ca đang chạy. Vùng bàn và danh sách nhân viên được giữ lại.
        </Text>
        <div>
          <Button label="Bắt đầu ca mới" variant="destructive" icon={<RotateCcw size={15} />} onClick={() => setConfirm(true)} />
        </div>
      </div>
      <AlertDialog
        isOpen={confirm}
        onOpenChange={setConfirm}
        title="Xoá dữ liệu của ca đang chạy?"
        description="Việc, nhật ký và số liệu ca sẽ mất, không lấy lại được. Vùng bàn và nhân viên được giữ."
        cancelLabel="Thôi"
        actionLabel="Xoá và bắt đầu ca mới"
        actionVariant="destructive"
        isActionLoading={busy === 'reset'}
        onAction={() => void reset()}
      />
    </Card>
  );
}

function ConnectPanel() {
  const { info } = useInfo(10000);
  return (
    <div className="flex flex-col gap-5">
      <CameraCard info={info} />
      <AiCard info={info} />
      <RulesCard />
      <ShiftCard />
    </div>
  );
}

/** Cài đặt: vùng bàn, nhân viên, và phần kết nối (camera, AI, quy tắc báo việc, ca) */
export default function Settings() {
  useTitle('Cài đặt, Easy FnB');
  const [params, setParams] = useSearchParams();
  const tab = TABS.some((t) => t.value === params.get('tab')) ? (params.get('tab') as string) : 'vung-ban';

  return (
    <div className="fx-page">
      <TabList
        value={tab}
        hasDivider
        onChange={(v) => {
          const next = new URLSearchParams(params);
          next.set('tab', v);
          setParams(next, { replace: true });
        }}
      >
        {TABS.map((t) => (
          <Tab key={t.value} value={t.value} label={t.label} />
        ))}
      </TabList>
      {tab === 'vung-ban' && <ZoneEditor initialCamera={params.get('cam')} />}
      {tab === 'nhan-vien' && <StaffEditor />}
      {tab === 'camera' && <ConnectPanel />}
    </div>
  );
}
