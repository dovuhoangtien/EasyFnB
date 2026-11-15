import { createContext, useContext, useState, type ReactNode } from 'react';
import { CheckCircle2, X } from 'lucide-react';
import { Banner } from '@astryxdesign/core/Banner';
import { Button } from '@astryxdesign/core/Button';
import { IconButton } from '@astryxdesign/core/IconButton';
import { NumberInput } from '@astryxdesign/core/NumberInput';
import { Selector } from '@astryxdesign/core/Selector';
import { StatusDot } from '@astryxdesign/core/StatusDot';
import { Switch } from '@astryxdesign/core/Switch';
import { Text } from '@astryxdesign/core/Text';
import { TextInput } from '@astryxdesign/core/TextInput';
import { deleteStaffPhoto, putSettings, putStaff, putZones, shootStaffPhoto, snapshotUrl, staffPhotoUrl } from '../live/api';
import { useInfo, useRun } from '../live/hooks';
import { LiveCamera } from '../live/LiveCamera';
import { live, useLive, useServerNow } from '../live/store';
import { cameraLive, ROLE_LABEL, slugify } from '../live/text';
import type { BanBlock, ChupBlock, ConfirmBlock, QrBlock, Role, RuleRow, Settings, SettingsPatch, Staff, StaffChangeRow, StaffInput } from '../live/types';
import { CopyBlock, phoneCameraUrl, usePhonesLive } from './connect';
import { QrCode } from './QrCode';
import { usePhoneBase } from './ui';

/**
 * Khối cài đặt trong trợ lý.
 * Máy chủ chỉ dựng khối; dữ liệu chỉ đổi khi chủ quán bấm Lưu ở đây, bằng đúng các API trang Cài đặt dùng.
 */

interface SetupActions {
  /** gửi một câu vào chat như chủ quán tự gõ */
  ask: (question: string) => void;
  /** báo cho trợ lý biết vừa lưu gì, gửi kèm câu hỏi kế tiếp */
  saved: (note: string) => void;
}
export const SetupContext = createContext<SetupActions>({ ask: () => {}, saved: () => {} });

const ROLE_OPTIONS = (['serve', 'clean', 'cashier', 'owner'] as Role[]).map((r) => ({ value: r, label: ROLE_LABEL[r] }));
const STALE = 'Dữ liệu vừa đổi ở nơi khác. Hỏi lại để có đề xuất mới.';

function Title({ children }: { children: string }) {
  return (
    <Text type="label" weight="semibold" as="h3">
      {children}
    </Text>
  );
}

/** Khối đã xong: thu lại một dòng cho chat gọn */
function Done({ text, children }: { text: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <CheckCircle2 size={16} aria-hidden="true" style={{ color: 'var(--color-icon-green)' }} />
        <Text type="body">{text}</Text>
      </div>
      {children}
    </div>
  );
}

function Cancelled() {
  return (
    <Text type="supporting" color="secondary" as="p">
      Đã huỷ, không đổi gì.
    </Text>
  );
}

// ---------- mã QR ----------
export function QrSetup({ b }: { b: QrBlock }) {
  return b.kind === 'camera' && b.camera ? <CameraQr cam={b.camera} title={b.title} /> : <StaffQr people={b.staff} title={b.title} />;
}

function CameraQr({ cam, title }: { cam: string; title: string }) {
  const { ask } = useContext(SetupContext);
  const { info } = useInfo();
  const { url, secure } = phoneCameraUrl(info, cam);
  const cameras = useLive((s) => s.cameras);
  const zones = useLive((s) => s.zones);
  const tables = useLive((s) => s.tables);
  const now = useServerNow();
  const phones = usePhonesLive([cam]);
  const connected = cameras.find((c) => c.id === cam && cameraLive(c, now));
  if (connected) {
    return (
      <div className="fx-block">
        <div className="flex items-center gap-2">
          <StatusDot variant="success" label="Đã nối" isPulsing />
          <Title>{`Đã nối ${cam}`}</Title>
        </div>
        <div className="fx-cam-frame">
          <LiveCamera camera={connected} zones={zones.find((z) => z.camera === cam)} tables={tables} alerts={[]} />
        </div>
        <div className="flex">
          <Button label="Tìm bàn" variant="primary" size="sm" onClick={() => ask(`tìm bàn ở ${cam}`)} />
        </div>
      </div>
    );
  }
  return (
    <div className="fx-block">
      <Title>{title}</Title>
      <div className="flex flex-wrap items-center gap-4">
        <QrCode value={url} size={150} label={`Mã QR mở điện thoại làm camera ${cam}`} />
        <div className="flex min-w-0 flex-1 flex-col gap-2" style={{ minWidth: 200 }}>
          <div className="flex items-center gap-2">
            <StatusDot variant={phones[cam] ? 'warning' : 'neutral'} label={phones[cam] ? 'Đang phát' : 'Đang chờ'} isPulsing={!phones[cam]} />
            <Text type="supporting" color="secondary">
              {phones[cam] ? 'Điện thoại đang phát, chờ camera AI đọc hình…' : 'Đang chờ điện thoại…'}
            </Text>
          </div>
          <Text type="supporting" color="secondary" as="p">
            Quét mã bằng điện thoại, bấm “Bắt đầu phát”, dựng máy nhìn bao quát các bàn và cắm sạc.
          </Text>
          <CopyBlock text={url} label="Chép link camera" />
        </div>
      </div>
      {!secure && (
        <Banner status="warning" title="Link này là http nên điện thoại sẽ chặn camera" description="Chạy máy chủ với --https, hoặc dùng bản đã triển khai trên Cloud Run." collapsible={false} />
      )}
    </div>
  );
}

function StaffQr({ people, title }: { people: { id: string; name: string }[]; title: string }) {
  const base = usePhoneBase();
  const staff = useLive((s) => s.staff);
  const [pick, setPick] = useState(people[0]?.id ?? '');
  const person = people.find((p) => p.id === pick) ?? people[0];
  if (!person) return null;
  const url = `${base}/nv/${encodeURIComponent(person.id)}`;
  const online = (id: string) => staff.find((s) => s.id === id)?.online === true;
  return (
    <div className="fx-block">
      <Title>{title}</Title>
      {people.length > 1 && (
        <div className="flex flex-wrap gap-2" role="group" aria-label="Chọn nhân viên">
          {people.map((p) => (
            <Button
              key={p.id}
              label={p.name}
              size="sm"
              variant={p.id === person.id ? 'primary' : 'secondary'}
              icon={online(p.id) ? <StatusDot variant="success" label="Đã mở app" /> : undefined}
              onClick={() => setPick(p.id)}
            />
          ))}
        </div>
      )}
      <div className="flex flex-wrap items-center gap-4">
        <QrCode value={url} size={150} label={`Mã QR mở app của ${person.name}`} />
        <div className="flex min-w-0 flex-1 flex-col gap-2" style={{ minWidth: 200 }}>
          <div className="flex items-center gap-2">
            <StatusDot variant={online(person.id) ? 'success' : 'neutral'} label={online(person.id) ? 'Đã mở app' : 'Chưa mở app'} />
            <Text type="supporting" color="secondary">
              {online(person.id) ? `${person.name} đã mở app` : `${person.name} quét mã bằng điện thoại của mình`}
            </Text>
          </div>
          <CopyBlock text={url} label="Chép link nhân viên" />
        </div>
      </div>
    </div>
  );
}

// ---------- duyệt bàn ----------
export function BanReview({ b }: { b: BanBlock }) {
  const { ask, saved } = useContext(SetupContext);
  const { busy, run } = useRun();
  const zones = useLive((s) => s.zones);
  const [mode, setMode] = useState<'them' | 'thay'>(b.merged ? 'them' : 'thay');
  const [state, setState] = useState<'cho' | 'xong' | 'cu'>('cho');
  const [bust] = useState(() => Date.now());
  const [imgOk, setImgOk] = useState(true);
  const list = mode === 'them' && b.merged ? b.merged : b.tables;
  if (state === 'xong') return <Done text={`Đã lưu ${list.length} bàn cho ${b.camera}.`} />;

  const save = async () => {
    const cur = zones.find((z) => z.camera === b.camera);
    const now = (cur?.tables ?? []).map((t) => t.id).join(',');
    if (now !== b.existing.join(',')) return setState('cu');
    const out = await run('save', () => putZones({ camera: b.camera, frame_w: b.frame_w, frame_h: b.frame_h, tables: list, areas: cur?.areas }));
    if (!out) return;
    live.upsertZones(out);
    setState('xong');
    saved(`đã lưu ${list.length} bàn cho ${b.camera}: ${list.map((t) => t.id).join(', ')}`);
  };

  const fresh = mode === 'them' ? new Set(list.map((t) => t.id).filter((id) => !b.existing.includes(id))) : null;
  return (
    <div className="fx-block">
      <Title>{b.title}</Title>
      <div className="fx-cam-frame">
        <svg viewBox={`0 0 ${b.frame_w} ${b.frame_h}`} className="fx-ban-review" role="img" aria-label={`${list.length} bàn trên ảnh camera ${b.camera}`}>
          {imgOk && <image href={snapshotUrl(b.camera, bust)} width={b.frame_w} height={b.frame_h} onError={() => setImgOk(false)} />}
          {list.map((t) => {
            const old = fresh !== null && !fresh.has(t.id);
            const xs = t.polygon.map((p) => p[0]);
            const ys = t.polygon.map((p) => p[1]);
            const fs = Math.max(14, b.frame_h / 28);
            return (
              <g key={t.id} className={old ? 'is-old' : undefined}>
                <polygon points={t.polygon.map((p) => p.join(',')).join(' ')} />
                <text x={Math.min(...xs) + fs * 0.3} y={Math.min(...ys) + fs * 1.1} fontSize={fs}>
                  {t.id}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
      {b.merged && (
        <div className="flex flex-wrap gap-2" role="group" aria-label="Cách lưu">
          <Button label="Chỉ thêm bàn mới" size="sm" variant={mode === 'them' ? 'primary' : 'secondary'} onClick={() => setMode('them')} />
          <Button label={`Thay hết bằng ${b.tables.length} bàn`} size="sm" variant={mode === 'thay' ? 'primary' : 'secondary'} onClick={() => setMode('thay')} />
        </div>
      )}
      {state === 'cu' && <Banner status="warning" title={STALE} collapsible={false} />}
      <div className="flex flex-wrap gap-2">
        <Button label={`Lưu ${list.length} bàn`} variant="primary" isLoading={busy === 'save'} isDisabled={state === 'cu'} onClick={() => void save()} />
        <Button label="Tìm lại" variant="ghost" onClick={() => ask(`tìm bàn ở ${b.camera}`)} />
        <Button label="Sửa tay" variant="ghost" href={`/cai-dat?tab=vung-ban&cam=${encodeURIComponent(b.camera)}`} />
      </div>
    </div>
  );
}

// ---------- xác nhận ----------
export function ConfirmSetup({ b }: { b: ConfirmBlock }) {
  return b.kind === 'staff' ? <StaffConfirm b={b} /> : <RulesConfirm b={b} />;
}

type StaffConfirmBlock = Extract<ConfirmBlock, { kind: 'staff' }>;
type RulesConfirmBlock = Extract<ConfirmBlock, { kind: 'settings' }>;

function sameStaff(cur: Staff[], base: StaffConfirmBlock['base']) {
  return cur.length === base.length && cur.every((s, i) => s.id === base[i].id && s.name === base[i].name && s.role === base[i].role);
}

function StaffConfirm({ b }: { b: StaffConfirmBlock }) {
  const { saved } = useContext(SetupContext);
  const { busy, run } = useRun();
  const staff = useLive((s) => s.staff);
  const [rows, setRows] = useState<StaffChangeRow[]>(b.rows);
  const [state, setState] = useState<'cho' | 'xong' | 'huy' | 'cu'>('cho');
  const [added, setAdded] = useState<{ id: string; name: string }[]>([]);
  const valid = rows.length > 0 && rows.every((r) => r.change === 'bo' || r.name.trim());
  const edit = (i: number, patch: Partial<StaffChangeRow>) => setRows(rows.map((r, j) => (j === i ? { ...r, ...patch } : r)));

  if (state === 'huy') return <Cancelled />;
  if (state === 'xong') {
    const n = rows.length;
    return (
      <Done text={`Đã lưu ${n} thay đổi nhân viên.`}>
        {added.length > 0 && <StaffQr people={added} title="Mở app cho người mới" />}
      </Done>
    );
  }

  const save = async () => {
    if (!sameStaff(staff, b.base)) return setState('cu');
    const gone = new Set(rows.filter((r) => r.change === 'bo').map((r) => r.id));
    const edits = new Map(rows.filter((r) => r.change === 'doi').map((r) => [r.id, r]));
    const list: StaffInput[] = staff
      .filter((s) => !gone.has(s.id))
      .map((s) => {
        const e = edits.get(s.id);
        return { id: s.id, name: e ? e.name.trim() : s.name, role: e ? e.role : s.role, consent: s.consent };
      });
    const used = new Set(list.map((s) => s.id));
    const fresh: { id: string; name: string }[] = [];
    for (const r of rows.filter((x) => x.change === 'them')) {
      const root = slugify(r.name) || 'nv';
      let id = root;
      for (let k = 2; used.has(id); k++) id = `${root}${k}`;
      used.add(id);
      list.push({ id, name: r.name.trim(), role: r.role, consent: false });
      fresh.push({ id, name: r.name.trim() });
    }
    const out = await run('save', () => putStaff(list));
    if (!out) return;
    live.setStaff(out);
    setAdded(fresh);
    setState('xong');
    const parts = [
      fresh.length ? `thêm ${fresh.map((x) => x.name).join(', ')}` : '',
      gone.size ? `bỏ ${rows.filter((r) => r.change === 'bo').map((r) => r.name).join(', ')}` : '',
      edits.size ? `đổi ${[...edits.values()].map((r) => `${r.old_name} thành ${r.name} (${ROLE_LABEL[r.role].toLowerCase()})`).join(', ')}` : '',
    ].filter(Boolean);
    saved(`đã lưu nhân viên: ${parts.join('; ')}`);
  };

  return (
    <div className="fx-block">
      <Title>{b.title}</Title>
      <div className="flex flex-col gap-2">
        {rows.map((r, i) =>
          r.change === 'bo' ? (
            <div key={`${r.change}-${r.id}`} className="flex flex-wrap items-center gap-2">
              <Text type="body">
                Bỏ <s>{r.name}</s>
              </Text>
              {r.photos > 0 && (
                <Text type="supporting" color="secondary">
                  ảnh nhận dạng của {r.name} sẽ bị xoá
                </Text>
              )}
            </div>
          ) : (
            <div key={`${r.change}-${r.id}-${i}`} className="fx-setup-row">
              <TextInput label="Tên" isLabelHidden placeholder="Tên, ví dụ Lan" value={r.name} onChange={(v) => edit(i, { name: v.slice(0, 30) })} />
              <Selector label="Vai trò" isLabelHidden value={r.role} options={ROLE_OPTIONS} onChange={(v) => edit(i, { role: v as Role })} />
              {r.change === 'doi' ? (
                <Text type="supporting" color="secondary">
                  trước: {r.old_name}, {ROLE_LABEL[r.old_role ?? 'serve'].toLowerCase()}
                </Text>
              ) : (
                <IconButton label="Bỏ dòng này" tooltip="Bỏ dòng này" variant="ghost" icon={<X size={16} />} onClick={() => setRows(rows.filter((_, j) => j !== i))} />
              )}
            </div>
          ),
        )}
      </div>
      {state === 'cu' && <Banner status="warning" title={STALE} collapsible={false} />}
      <div className="flex flex-wrap gap-2">
        <Button label="Lưu" variant="primary" isLoading={busy === 'save'} isDisabled={!valid || state === 'cu'} onClick={() => void save()} />
        {rows.some((r) => r.change === 'them') && (
          <Button label="Thêm dòng" variant="ghost" onClick={() => setRows([...rows, { change: 'them', id: '', name: '', role: 'serve', old_name: null, old_role: null, photos: 0 }])} />
        )}
        <Button label="Huỷ" variant="ghost" onClick={() => setState('huy')} />
      </div>
    </div>
  );
}

/** Giá trị luật theo đơn vị trên khối, cùng cách tính với gia_tri_luat trong server/cai_dat.py */
function ruleValue(r: RuleRow, s: Settings): RuleRow['after'] | undefined {
  if (r.key === 'verify_call') return s.verify_kinds.includes('call');
  if (r.key === 'verify_clear') return s.verify_kinds.includes('needs_clearing');
  if (r.key === 'hold_clear') return s.hold_until_verified.includes('needs_clearing');
  const v = r.setting ? (s as unknown as Record<string, unknown>)[r.setting] : undefined;
  if (v === undefined) return undefined; // máy chủ cũ chưa gửi khoá này: coi như chưa đổi
  if (r.unit === 'bat_tat') return Boolean(v);
  if (r.unit === 'gio') return String(v ?? '');
  if (r.unit === 'phut') return Math.round((Number(v) / 60) * 10) / 10;
  return Number(v);
}

const HHMM = /^([01]\d|2[0-3]):[0-5]\d$/;
const ruleOk = (r: RuleRow) => r.unit !== 'gio' || HHMM.test(String(r.after)) || (r.optional && r.after === '');

function toPatch(rows: RuleRow[], s: Settings): SettingsPatch {
  const patch: Record<string, unknown> = {};
  const toggle = (list: string[], kind: string, on: boolean) => (on ? [...new Set([...list, kind])] : list.filter((k) => k !== kind));
  let verify = s.verify_kinds;
  let hold = s.hold_until_verified;
  for (const r of rows) {
    if (r.after === r.before) continue;
    if (r.key === 'verify_call') verify = toggle(verify, 'call', Boolean(r.after));
    else if (r.key === 'verify_clear') verify = toggle(verify, 'needs_clearing', Boolean(r.after));
    else if (r.key === 'hold_clear') hold = toggle(hold, 'needs_clearing', Boolean(r.after));
    else if (!r.setting) continue;
    else if (r.unit === 'bat_tat') patch[r.setting] = Boolean(r.after);
    else if (r.unit === 'gio') patch[r.setting] = String(r.after);
    else patch[r.setting] = r.unit === 'phut' ? Math.round(Number(r.after) * 60) : Math.round(Number(r.after));
  }
  if (verify !== s.verify_kinds) patch.verify_kinds = verify;
  if (hold !== s.hold_until_verified) patch.hold_until_verified = hold;
  return patch as SettingsPatch;
}

function RulesConfirm({ b }: { b: RulesConfirmBlock }) {
  const { saved } = useContext(SetupContext);
  const { busy, run } = useRun();
  const settings = useLive((s) => s.settings);
  const [rows, setRows] = useState<RuleRow[]>(b.rows);
  const [state, setState] = useState<'cho' | 'xong' | 'huy' | 'cu'>('cho');
  const changed = rows.filter((r) => r.after !== r.before);
  if (state === 'huy') return <Cancelled />;
  if (state === 'xong') return <Done text={`Đã lưu ${changed.length} thay đổi ${b.title.toLowerCase()}.`} />;
  const edit = (i: number, after: RuleRow['after']) => setRows(rows.map((r, j) => (j === i ? { ...r, after } : r)));
  const word = (r: RuleRow, v: RuleRow['after']) =>
    r.unit === 'bat_tat' ? (v ? 'bật' : 'tắt') : r.unit === 'gio' ? String(v) || 'không có' : v === 0 ? 'tắt' : `${v} ${r.unit === 'phut' ? 'phút' : 'giây'}`;
  const valid = rows.every(ruleOk);

  const save = async () => {
    if (!settings) return;
    if (rows.some((r) => { const v = ruleValue(r, settings); return v !== undefined && v !== b.base[r.key]; })) return setState('cu');
    const out = await run('save', () => putSettings(toPatch(rows, settings)));
    if (!out) return;
    live.setSettings(out);
    setState('xong');
    saved(`đã đổi ${b.title.toLowerCase()}: ${changed.map((r) => `${r.label} ${word(r, r.before)} thành ${word(r, r.after)}`).join('; ')}`);
  };

  return (
    <div className="fx-block">
      <Title>{b.title}</Title>
      <div className="flex flex-col gap-3" style={{ maxWidth: 560 }}>
        {rows.map((r, i) =>
          r.unit === 'bat_tat' ? (
            <Switch
              key={r.key}
              label={r.label}
              description={r.after !== r.before ? `Trước: ${word(r, r.before)}` : undefined}
              value={Boolean(r.after)}
              isDisabled={r.needs_ai && !b.ai}
              changeAction={(on) => edit(i, on)}
            />
          ) : r.unit === 'gio' ? (
            <TextInput
              key={r.key}
              label={r.label}
              description={r.after !== r.before ? `Trước: ${word(r, r.before)}` : r.optional ? 'Để trống là không có.' : undefined}
              placeholder="HH:MM, ví dụ 07:00"
              value={String(r.after)}
              onChange={(v) => edit(i, v.trim().slice(0, 5))}
            />
          ) : (
            <NumberInput
              key={r.key}
              label={r.label}
              description={r.after !== r.before ? `Trước: ${word(r, r.before)}. 0 là tắt.` : '0 là tắt.'}
              units={r.unit === 'phut' ? 'phút' : 'giây'}
              min={r.min ?? 0}
              max={r.max ?? undefined}
              isIntegerOnly={r.unit === 'giay'}
              value={Number(r.after)}
              onChange={(v) => edit(i, Number.isFinite(v) ? v : 0)}
            />
          ),
        )}
      </div>
      {state === 'cu' && <Banner status="warning" title={STALE} collapsible={false} />}
      <div className="flex flex-wrap gap-2">
        <Button label="Lưu" variant="primary" isLoading={busy === 'save'} isDisabled={changed.length === 0 || !valid || state === 'cu'} onClick={() => void save()} />
        <Button label="Huỷ" variant="ghost" onClick={() => setState('huy')} />
      </div>
    </div>
  );
}

// ---------- chụp ảnh nhân viên ----------
export function ChupSetup({ b }: { b: ChupBlock }) {
  const { saved } = useContext(SetupContext);
  const { busy, run } = useRun();
  const staff = useLive((s) => s.staff);
  const cameras = useLive((s) => s.cameras);
  const now = useServerNow();
  const person = staff.find((s) => s.id === b.staff_id);
  const [consent, setConsent] = useState(b.consent);
  const [shot, setShot] = useState<string | null>(null);
  const [kept, setKept] = useState(false);
  const cam = cameras.find((c) => c.id === b.camera && cameraLive(c, now));
  if (!person) return <Text type="supporting" color="secondary" as="p">Không còn nhân viên {b.name} trong danh sách.</Text>;
  if (kept) return <Done text={`Đã lưu ảnh nhận dạng của ${b.name}.`} />;

  const shoot = async () => {
    if (!person.consent) {
      const list = staff.map((s) => ({ id: s.id, name: s.name, role: s.role, consent: s.id === person.id ? true : s.consent }));
      const out = await run('shoot', () => putStaff(list));
      if (!out) return;
      live.setStaff(out);
    }
    const out = await run('shoot', () => shootStaffPhoto(b.staff_id, b.camera));
    if (!out) return;
    live.setStaff(out);
    const photos = out.find((s) => s.id === b.staff_id)?.photos ?? [];
    setShot(photos.at(-1)?.id ?? null);
  };
  const retake = async () => {
    if (shot) {
      const out = await run('shoot', () => deleteStaffPhoto(b.staff_id, shot));
      if (out) live.setStaff(out);
    }
    setShot(null);
    await shoot();
  };

  return (
    <div className="fx-block">
      <Title>{b.title}</Title>
      {shot ? (
        <img className="fx-setup-shot" src={staffPhotoUrl(b.staff_id, shot)} alt={`Ảnh vừa chụp của ${b.name}`} />
      ) : cam ? (
        <div className="fx-cam-frame">
          <LiveCamera camera={cam} zones={undefined} tables={[]} alerts={[]} />
        </div>
      ) : (
        <Banner status="warning" title={`Camera ${b.camera} chưa có hình`} description="Nối camera trước, rồi chụp." collapsible={false} />
      )}
      {!shot && (
        <>
          <Text type="supporting" color="secondary" as="p">
            Nhờ {b.name} đứng giữa khung hình, thấy rõ cả người.
          </Text>
          <Switch label={`${b.name} đồng ý cho camera nhận dạng`} value={consent} changeAction={(on) => setConsent(on)} />
        </>
      )}
      <div className="flex flex-wrap gap-2">
        {shot ? (
          <>
            <Button
              label="Giữ ảnh này"
              variant="primary"
              onClick={() => {
                setKept(true);
                saved(`đã lưu một ảnh nhận dạng cho ${b.name}`);
              }}
            />
            <Button label="Chụp lại" variant="ghost" isLoading={busy === 'shoot'} onClick={() => void retake()} />
          </>
        ) : (
          <Button label="Chụp" variant="primary" isLoading={busy === 'shoot'} isDisabled={!consent || !cam} onClick={() => void shoot()} />
        )}
      </div>
    </div>
  );
}
