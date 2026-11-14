import { useState, type ChangeEvent } from 'react';
import { useSearchParams } from 'react-router';
import { Camera as CameraIcon, PlugZap, Plus, RotateCcw, Trash, Upload, X } from 'lucide-react';
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
import { TimeInput, type ISOTimeString } from '@astryxdesign/core/TimeInput';
import { useToast } from '@astryxdesign/core/Toast';
import { deleteStaffPhoto, errorMessage, isPinError, putSettings, putStaff, rememberPin, resetShift, savedPin, setOwnerPin, shootStaffPhoto, staffPhotoUrl, testAi, uploadStaffPhoto, type AiTest, type Info } from '../live/api';
import { useInfo, useOwnerPin, useRun, useTitle } from '../live/hooks';
import { live, useLive, useServerNow } from '../live/store';
import { CAMERA_AGENT_CMD, cameraLive, ROLE_LABEL, slugify } from '../live/text';
import { ROLES, type Role, type SettingsPatch, type Staff, type StaffInput, type StaffPhoto } from '../live/types';
import { ZoneEditor } from '../live/ZoneEditor';
import { LiveCamera } from '../live/LiveCamera';
import { QrCode } from './QrCode';
import { PinDialog } from './ownerPin';
import { SectionTitle, usePhoneBase, voiceText } from './ui';
import { CopyBlock, LOCAL, PHONE_CAMS, phoneCameraUrl, usePhonesLive } from './connect';

const TABS = [
  { value: 'vung-ban', label: 'Vùng bàn' },
  { value: 'nhan-vien', label: 'Nhân viên' },
  { value: 'camera', label: 'Kết nối' },
  { value: 'an-ninh', label: 'An ninh' },
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

/** Thu ảnh về tối đa 1024 điểm ảnh mỗi cạnh, dạng JPEG, trước khi gửi lên */
async function toJpeg(file: File): Promise<Blob> {
  const img = await createImageBitmap(file);
  const scale = Math.min(1, 1024 / Math.max(img.width, img.height));
  const canvas = document.createElement('canvas');
  canvas.width = Math.round(img.width * scale);
  canvas.height = Math.round(img.height * scale);
  canvas.getContext('2d')?.drawImage(img, 0, 0, canvas.width, canvas.height);
  img.close();
  return new Promise((resolve, reject) => canvas.toBlob((b) => (b ? resolve(b) : reject(new Error('Không đọc được ảnh này.'))), 'image/jpeg', 0.88));
}

const PHOTO_LABEL: Record<StaffPhoto['kind'], string> = { body: 'Cả người', face: 'Mặt' };
/** nhãn dưới ảnh: ảnh chụp tại quán là ảnh camera nhận ra tốt nhất */
const photoTag = (p: StaffPhoto) => (p.kind === 'face' ? 'Mặt' : p.source === 'camera' ? 'Chụp ở quán' : 'Tải lên');

/** Ảnh để camera nhận ra một nhân viên: chụp bằng camera quán hoặc tải lên */
function StaffPhotos({ person }: { person: Staff }) {
  const staff = useLive((s) => s.staff);
  const cameras = useLive((s) => s.cameras);
  const now = useServerNow();
  const { busy, run } = useRun();
  const camera = cameras.find((c) => cameraLive(c, now));
  const photos = person.photos ?? [];
  // camera nhìn từ trên cao: ảnh tải lên (chụp ngang tầm mắt) thường không khớp, cần ảnh chụp bằng chính camera quán
  const shotHere = photos.some((p) => p.kind === 'body' && p.source === 'camera');

  const done = (out: Staff[] | undefined) => {
    if (out) live.setStaff(out);
  };
  const setConsent = async (on: boolean) =>
    done(await run('consent', () => putStaff(staff.map((s) => ({ id: s.id, name: s.name, role: s.role, consent: s.id === person.id ? on : s.consent })))));
  const upload = (kind: StaffPhoto['kind']) => async (ev: ChangeEvent<HTMLInputElement>) => {
    const file = ev.target.files?.[0];
    ev.target.value = '';
    if (file) done(await run(kind, async () => uploadStaffPhoto(person.id, kind, await toJpeg(file))));
  };

  return (
    <div className="fx-staff-photos">
      <Switch label="Cho camera nhận dạng" value={person.consent === true} isDisabled={busy === 'consent'} changeAction={(on) => void setConsent(on)} />
      {person.consent && (
        <>
          {photos.length > 0 && (
            <ul className="fx-photo-strip" aria-label={`Ảnh nhận dạng của ${person.name}`}>
              {photos.map((p) => (
                <li key={p.id}>
                  <img src={staffPhotoUrl(person.id, p.id)} alt={`${PHOTO_LABEL[p.kind]} của ${person.name}`} loading="lazy" />
                  <span>{photoTag(p)}</span>
                  <button type="button" aria-label={`Xoá ảnh ${PHOTO_LABEL[p.kind].toLowerCase()} của ${person.name}`} onClick={() => void run(p.id, () => deleteStaffPhoto(person.id, p.id)).then(done)}>
                    <X size={12} aria-hidden="true" />
                  </button>
                </li>
              ))}
            </ul>
          )}
          <div className="flex items-center gap-2 flex-wrap">
            <Button
              label="Chụp bằng camera quán"
              variant={shotHere ? 'secondary' : 'primary'}
              size="sm"
              icon={<CameraIcon size={15} />}
              isLoading={busy === 'shoot'}
              isDisabled={!camera}
              onClick={() => camera && void run('shoot', () => shootStaffPhoto(person.id, camera.id)).then(done)}
            />
            <label className="fx-file-btn" data-busy={busy === 'body' || undefined}>
              <Upload size={15} aria-hidden="true" />
              Ảnh cả người
              <input type="file" accept="image/*" capture="environment" className="visually-hidden" onChange={(ev) => void upload('body')(ev)} />
            </label>
          </div>
          {!shotHere && (
            <Text type="supporting" color="secondary" as="p">
              {camera
                ? `Nhờ ${person.name} đứng trước camera rồi bấm Chụp. Camera nhận ra ${person.name} chắc nhất bằng ảnh do chính nó chụp, ảnh tải lên dễ bị nhận nhầm là khách.`
                : `Bật camera quán rồi chụp ${person.name} tại đây. Ảnh tải lên dễ bị nhận nhầm là khách.`}
            </Text>
          )}
        </>
      )}
    </div>
  );
}

function StaffEditor() {
  const staff = useLive((s) => s.staff);
  const { busy, run } = useRun();
  const [rows, setRows] = useState<Row[] | null>(null);
  const view: Row[] = rows ?? staff.map((s, i) => ({ key: i, id: s.id, name: s.name, role: s.role }));
  const dirty = rows !== null;
  const saved = (id: string | null) => staff.find((s) => s.id === id);
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
          Việc gọi phục vụ và khách mới giao cho người Phục vụ, bàn cần dọn giao cho người Dọn bàn. Chủ quán chỉ nhận cảnh báo an ninh. Link app của từng người nằm ở nút App nhân viên trên thanh trên cùng.
        </Text>
        {view.length === 0 && <EmptyState isCompact title="Chưa có nhân viên" description="Thêm ít nhất một người để hệ thống có người giao việc." />}
        {view.map((r) => (
          <div key={r.key} className="fx-staff-row">
            <TextInput label="Tên" isLabelHidden placeholder="Tên, ví dụ Lan" value={r.name} onChange={(v) => update(r.key, { name: v.slice(0, 30) })} />
            <Selector label="Vai trò" isLabelHidden value={r.role} options={ROLES.map((role) => ({ value: role, label: ROLE_LABEL[role] }))} onChange={(v) => update(r.key, { role: v as Role })} />
            <IconButton label={`Bỏ ${r.name || 'dòng này'}`} tooltip="Bỏ" variant="ghost" icon={<Trash size={16} />} onClick={() => setRows(view.filter((x) => x.key !== r.key))} />
            {saved(r.id) && <StaffPhotos person={saved(r.id) as Staff} />}
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
function serverUrl(info: Info | null) {
  if (!LOCAL.has(location.hostname)) return location.origin;
  const port = import.meta.env.DEV ? '8080' : location.port || '80';
  return `http://${info?.lan_ip ?? 'localhost'}:${port}`;
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

function PhoneCameraQr({ info }: { info: Info | null }) {
  const [cam, setCam] = useState(PHONE_CAMS[0]);
  const { url, secure } = phoneCameraUrl(info, cam);
  const cameras = useLive((s) => s.cameras);
  const now = useServerNow();
  const phones = usePhonesLive();
  /** đã kết nối: camera AI đang gửi kết quả; đang phát: điện thoại gửi hình nhưng camera AI chưa đọc */
  const status = (c: string) =>
    cameras.some((x) => x.id === c && cameraLive(x, now)) ? 'Đã kết nối' : phones[c] ? 'Điện thoại đang phát, camera AI chưa chạy' : null;
  // đã kết nối thì hiện luôn hình camera thay cho mã QR
  const connected = cameras.find((x) => x.id === cam && cameraLive(x, now));
  const [showQr, setShowQr] = useState(false);
  const zones = useLive((s) => s.zones);
  const tables = useLive((s) => s.tables);
  return (
    <div className="flex flex-col gap-3">
      <Text type="label" weight="semibold" as="p">
        Dùng điện thoại làm camera
      </Text>
      <div className="flex flex-wrap gap-2" role="group" aria-label="Chọn camera">
        {PHONE_CAMS.map((c) => {
          const st = status(c);
          return (
            <Button
              key={c}
              label={st === 'Đã kết nối' ? `${c}, đã kết nối` : st ? `${c}, đang phát` : c}
              tooltip={st ?? 'Chưa kết nối'}
              size="sm"
              variant={c === cam ? 'primary' : 'secondary'}
              icon={st ? <StatusDot variant={st === 'Đã kết nối' ? 'success' : 'warning'} label={st} /> : undefined}
              onClick={() => {
                setCam(c);
                setShowQr(false);
              }}
            />
          );
        })}
      </div>
      {status(cam) && status(cam) !== 'Đã kết nối' && (
        <Text type="supporting" color="secondary" as="p">
          {cam}: {status(cam)}.
        </Text>
      )}
      {connected && !showQr ? (
        <div className="flex flex-col gap-2">
          <div className="fx-cam-frame">
            <LiveCamera camera={connected} zones={zones.find((z) => z.camera === cam)} tables={tables} alerts={[]} />
          </div>
          <div className="flex">
            <Button label="Hiện mã QR" variant="ghost" size="sm" onClick={() => setShowQr(true)} />
          </div>
        </div>
      ) : (
      <div className="flex flex-wrap items-center gap-4">
        <QrCode value={url} size={150} label={`Mã QR mở điện thoại làm camera ${cam}`} />
        <div className="flex min-w-0 flex-1 flex-col gap-2" style={{ minWidth: 200 }}>
          <Text type="supporting" color="secondary" as="p">
            Quét mã bằng điện thoại sẽ dùng, rồi bấm “Bắt đầu phát”. Dựng điện thoại cố định nhìn xuống các bàn và cắm sạc.
          </Text>
          <CopyBlock text={url} label="Chép link camera" />
          {connected && <Button label="Xem hình camera" variant="ghost" size="sm" onClick={() => setShowQr(false)} />}
        </div>
      </div>
      )}
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

type StageKey = 'table_check_s' | 'wait_greet_s' | 'wait_food_s' | 'wait_bill_s';

function RulesCard() {
  const settings = useLive((s) => s.settings);
  const { run } = useRun();
  const [draft, setDraft] = useState<{ escalate_s?: number; auto_close_s?: number }>({});
  const [mins, setMins] = useState<Partial<Record<StageKey, number>>>({});
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
  // các mốc theo dõi bữa ăn: máy chủ giữ bằng giây, màn hình hiện bằng phút
  const minutes = (key: StageKey) => mins[key] ?? Math.round(((settings[key] ?? 0) / 60) * 10) / 10;
  const commitMin = (key: StageKey) => {
    const v = mins[key];
    if (v === undefined || !Number.isFinite(v)) return;
    const s = Math.round(v * 60);
    if (s === (settings[key] ?? 0)) return setMins((d) => ({ ...d, [key]: undefined }));
    void save({ [key]: s }, 'Đã lưu').then(() => setMins((d) => ({ ...d, [key]: undefined })));
  };
  const stageInput = (key: StageKey, label: string, description: string, max: number) => (
    <NumberInput
      label={label}
      description={description}
      units="phút"
      min={0}
      max={max}
      value={minutes(key)}
      onChange={(v) => setMins((d) => ({ ...d, [key]: v }))}
      onBlur={() => commitMin(key)}
      onEnter={() => commitMin(key)}
    />
  );

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
        <div className="flex flex-col gap-1">
          <Text type="label" weight="semibold">
            Theo dõi bữa ăn ở từng bàn
          </Text>
          <Text type="supporting" color="secondary" as="p">
            AI xem ảnh bàn để biết khách đã được tiếp, đã có món hay đã ăn xong, và nhắc một lần khi khách chờ lâu. Để 0 là tắt.
          </Text>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          {stageInput('table_check_s', 'AI xem lại mỗi bàn sau', 'Xem càng thưa càng ít tốn.', 60)}
          {stageInput('wait_greet_s', 'Nhắc khi khách ngồi mà chưa ai tiếp sau', 'Tính từ lúc khách ngồi vào bàn.', 120)}
          {stageInput('wait_food_s', 'Nhắc khi khách chờ món quá', 'Tính từ lúc có người ra tiếp.', 240)}
          {stageInput('wait_bill_s', 'Nhắc khi khách ăn xong mà chưa ai ghé sau', 'Khách có thể đang chờ tính tiền.', 240)}
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

/** Điện thoại nhân viên: mỗi người quét mã của mình để nhận việc và nghe đọc qua tai nghe */
function StaffPhonesCard() {
  const staff = useLive((s) => s.staff);
  const base = usePhoneBase();
  const [pick, setPick] = useState<string | null>(null);
  const person = staff.find((s) => s.id === pick) ?? staff[0];
  const url = person ? `${base}/nv/${encodeURIComponent(person.id)}` : '';
  return (
    <Card padding={4}>
      <div className="flex flex-col gap-3">
        <SectionTitle>Điện thoại nhân viên</SectionTitle>
        {!person ? (
          <Text type="supporting" color="secondary" as="p">
            Chưa có nhân viên. Thêm người ở mục Nhân viên trước.
          </Text>
        ) : (
          <>
            <div className="flex flex-wrap gap-2" role="group" aria-label="Chọn nhân viên">
              {staff.map((s) => (
                <Button
                  key={s.id}
                  label={s.online ? `${s.name}, đã kết nối` : s.name}
                  tooltip={s.online ? 'Đang mở app' : 'Chưa mở app'}
                  size="sm"
                  variant={s.id === person.id ? 'primary' : 'secondary'}
                  icon={s.online ? <StatusDot variant="success" label="Đã kết nối" /> : undefined}
                  onClick={() => setPick(s.id)}
                />
              ))}
            </div>
            <div className="flex flex-wrap items-center gap-4">
              <QrCode value={url} size={150} label={`Mã QR mở app của ${person.name}`} />
              <div className="flex min-w-0 flex-1 flex-col gap-2" style={{ minWidth: 200 }}>
                <Text type="supporting" color="secondary" as="p">
                  {person.name} quét mã bằng điện thoại, bấm “Bắt đầu ca”, rồi chạm màn hình một lần để máy được phát tiếng. Đeo tai nghe để nghe đọc việc. Điện thoại cùng Wi-Fi với máy này.
                </Text>
                <CopyBlock text={url} label="Chép link nhân viên" />
              </div>
            </div>
          </>
        )}
      </div>
    </Card>
  );
}

// ---------- an ninh, quyền riêng tư ----------
const asTime = (v: string | undefined) => (v ? (v as ISOTimeString) : undefined);

function SecuritySettings() {
  const settings = useLive((s) => s.settings);
  const { run } = useRun();
  const [holdMin, setHoldMin] = useState<number | undefined>(undefined);
  if (!settings) return null;
  const save = async (patch: SettingsPatch, ok = 'Đã lưu') => {
    const out = await run('sec', () => putSettings(patch), ok);
    if (out) live.setSettings(out);
  };
  const hold = holdMin ?? Math.round(((settings.hold_s ?? 600) / 60) * 10) / 10;
  const commitHold = () => {
    if (holdMin === undefined || !Number.isFinite(holdMin)) return;
    const sec = Math.round(holdMin * 60);
    if (sec === (settings.hold_s ?? 600)) return setHoldMin(undefined);
    void save({ hold_s: sec }).then(() => setHoldMin(undefined));
  };
  return (
    <Card padding={4}>
      <div className="flex flex-col gap-4" style={{ maxWidth: 620 }}>
        <SectionTitle>An ninh</SectionTitle>
        <Switch
          label="Báo khi có người lạ lấy đồ của khách"
          description="Rung máy nhân viên và chủ quán, không đọc to."
          value={settings.sec_item_taken !== false}
          changeAction={(on) => save({ sec_item_taken: on })}
        />
        <Switch
          label="Báo khi có người trong quán ngoài giờ"
          description="Chuông và đọc to trên máy chủ quán."
          value={settings.sec_after_hours !== false}
          changeAction={(on) => save({ sec_after_hours: on })}
        />
        <Switch
          label="Báo khi khách vào quầy thu ngân, kho, bếp"
          description="Cần vẽ vùng Quầy hoặc Kho ở mục Vùng bàn."
          value={settings.sec_restricted !== false}
          changeAction={(on) => save({ sec_restricted: on })}
        />
        <div className="grid gap-4 sm:grid-cols-2">
          <TimeInput label="Giờ mở cửa" hourFormat="24h" value={asTime(settings.open_time)} changeAction={(v) => (v ? save({ open_time: v }) : undefined)} />
          <TimeInput
            label="Giờ đóng cửa"
            description="Từ giờ này tự bật trông quán."
            hourFormat="24h"
            value={asTime(settings.close_time)}
            changeAction={(v) => (v ? save({ close_time: v }) : undefined)}
          />
          <TimeInput
            label="Giao hàng từ"
            description="Trong khung giờ này không báo người vào kho."
            hourFormat="24h"
            hasClear
            value={asTime(settings.delivery_from)}
            changeAction={(v) => save({ delivery_from: v ?? '' })}
          />
          <TimeInput label="Giao hàng tới" hourFormat="24h" hasClear value={asTime(settings.delivery_to)} changeAction={(v) => save({ delivery_to: v ?? '' })} />
          <NumberInput
            label="Giữ bàn khi khách tạm rời"
            description="Khách đi vệ sinh, nghe máy, còn để đồ ở bàn."
            units="phút"
            min={0}
            max={120}
            value={hold}
            onChange={(v) => setHoldMin(v)}
            onBlur={commitHold}
            onEnter={commitHold}
          />
        </div>
      </div>
    </Card>
  );
}

function PrivacySettings() {
  const settings = useLive((s) => s.settings);
  const toast = useToast();
  const { busy, run } = useRun();
  const { withPin, pinProps } = useOwnerPin();
  const [oldPin, setOldPin] = useState('');
  const [pin, setPin] = useState('');
  const [pin2, setPin2] = useState('');
  const [pinBusy, setPinBusy] = useState(false);
  const [pinError, setPinError] = useState<string | null>(null);
  if (!settings) return null;
  const hasPin = settings.owner_pin_set === true;
  const blur = settings.blur_faces !== false;
  const digits = (v: string) => v.replace(/\D/g, '').slice(0, 8);

  const submitPin = async () => {
    if (!/^\d{4,8}$/.test(pin)) return setPinError('Mã PIN gồm 4 đến 8 chữ số.');
    if (pin !== pin2) return setPinError('Hai lần nhập không giống nhau.');
    if (hasPin && !oldPin) return setPinError('Nhập mã PIN đang dùng.');
    setPinBusy(true);
    setPinError(null);
    try {
      await setOwnerPin(pin, hasPin ? oldPin : undefined);
      rememberPin(pin);
      setOldPin('');
      setPin('');
      setPin2('');
      // máy chủ cũng gửi lại cài đặt qua luồng trực tiếp; cập nhật ngay để công tắc che mặt mở khoá
      live.setSettings({ ...settings, owner_pin_set: true });
      toast({ body: hasPin ? 'Đã đổi mã PIN' : 'Đã đặt mã PIN' });
    } catch (err) {
      setPinError(isPinError(err) ? 'Mã PIN đang dùng không đúng.' : errorMessage(err));
    } finally {
      setPinBusy(false);
    }
  };

  const setBlur = async (on: boolean, p: string | null) => {
    const out = await run('blur', () => putSettings({ blur_faces: on }, p), on ? 'Đã bật che mặt' : 'Đã tắt che mặt');
    if (out) live.setSettings(out);
    else if (p && !on) rememberPin(null); // có thể PIN đã đổi: lần sau hỏi lại
  };

  return (
    <Card padding={4}>
      <div className="flex flex-col gap-4" style={{ maxWidth: 620 }}>
        <SectionTitle>Quyền riêng tư</SectionTitle>
        <div className="flex flex-col gap-2">
          <Switch
            label="Che mặt trong video và ảnh"
            description={
              hasPin
                ? 'Bản không che vẫn giữ ở máy quán 24 giờ, chủ quán xem bằng nút "Xem bản gốc".'
                : 'Phải đặt mã PIN chủ quán bên dưới mới tắt được, để người khác không xem được mặt khách.'
            }
            value={blur}
            isDisabled={busy === 'blur' || (!hasPin && blur)}
            changeAction={(on) => {
              if (on) return setBlur(true, savedPin());
              withPin((p) => void setBlur(false, p));
            }}
          />
          <Text type="supporting" color="secondary" as="p">
            Tắt che mặt là quyết định và trách nhiệm của chủ quán. Ảnh gửi AI kiểm tra luôn được che.
          </Text>
        </div>
        <div className="flex flex-col gap-3">
          <Text type="label" weight="semibold" as="p">
            {hasPin ? 'Đổi mã PIN chủ quán' : 'Đặt mã PIN chủ quán'}
          </Text>
          <div className="grid gap-3 sm:grid-cols-3">
            {hasPin && <TextInput label="PIN đang dùng" type="password" inputMode="numeric" autoComplete="off" value={oldPin} onChange={(v) => setOldPin(digits(v))} />}
            <TextInput label="PIN mới" description="4 đến 8 chữ số" type="password" inputMode="numeric" autoComplete="off" value={pin} onChange={(v) => setPin(digits(v))} />
            <TextInput
              label="Nhập lại PIN mới"
              type="password"
              inputMode="numeric"
              autoComplete="off"
              value={pin2}
              onChange={(v) => setPin2(digits(v))}
              onEnter={() => void submitPin()}
            />
          </div>
          {pinError && (
            <Text type="supporting" as="p" style={{ color: 'var(--color-text-error)' }}>
              {pinError}
            </Text>
          )}
          <div>
            <Button label={hasPin ? 'Đổi PIN' : 'Đặt PIN'} variant="secondary" isLoading={pinBusy} isDisabled={!pin} onClick={() => void submitPin()} />
          </div>
        </div>
      </div>
      <PinDialog {...pinProps} />
    </Card>
  );
}

function ConnectPanel() {
  const { info } = useInfo(10000);
  return (
    <div className="flex flex-col gap-5">
      <CameraCard info={info} />
      <StaffPhonesCard />
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
      {tab === 'vung-ban' && <ZoneEditor initialCamera={params.get('cam')} autoFind={params.get('tim') === '1'} />}
      {tab === 'nhan-vien' && (
        <div className="flex flex-col gap-5">
          <StaffEditor />
          <StaffPhonesCard />
        </div>
      )}
      {tab === 'camera' && <ConnectPanel />}
      {tab === 'an-ninh' && (
        <div className="flex flex-col gap-5">
          <SecuritySettings />
          <PrivacySettings />
        </div>
      )}
    </div>
  );
}
