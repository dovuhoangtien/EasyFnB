import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router';
import { Check, Copy, ExternalLink, Plus, RotateCcw, Save, Trash, TriangleAlert, Undo2 } from 'lucide-react';
import { useToast } from '../../components/ui';
import { getInfo, putSettings, putStaff, resetShift } from '../../live/api';
import { useRun, useTitle } from '../../live/hooks';
import { live, useLive, useLiveConnection } from '../../live/store';
import { KIND_LABEL, ROLE_LABEL, slugify } from '../../live/text';
import { AgentCommand } from '../../live/ui';
import { ZoneEditor } from '../../live/ZoneEditor';
import { ALERT_KINDS, ROLES, type Role, type StaffInput } from '../../live/types';

// ---------- nhân viên ----------
interface StaffRow {
  key: number;
  /** null: người mới, mã tạo từ tên lúc lưu */
  id: string | null;
  name: string;
  role: Role;
}

let rowKey = 1000;

const LOCAL_HOSTS = new Set(['localhost', '127.0.0.1', '[::1]']);

/** Gốc link cho điện thoại: mở bằng localhost thì đổi sang địa chỉ wifi của máy chủ, điện thoại mới vào được */
function usePhoneBase() {
  const [base, setBase] = useState(location.origin);
  useEffect(() => {
    if (!LOCAL_HOSTS.has(location.hostname)) return;
    let alive = true;
    getInfo()
      .then((i) => {
        if (alive && i.lan_ip) setBase(`${location.protocol}//${i.lan_ip}${location.port ? `:${location.port}` : ''}`);
      })
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, []);
  return base;
}

function CopyLink({ url, label }: { url: string; label: string }) {
  const toast = useToast();
  const [done, setDone] = useState(false);
  return (
    <button
      type="button"
      className="btn btn--icon btn--ghost"
      aria-label={label}
      title={label}
      onClick={() => {
        navigator.clipboard
          .writeText(url)
          .then(() => {
            setDone(true);
            window.setTimeout(() => setDone(false), 1500);
          })
          .catch(() => toast('Không chép được, hãy chép tay đường link.'));
      }}
    >
      {done ? <Check size={15} aria-hidden="true" /> : <Copy size={15} aria-hidden="true" />}
    </button>
  );
}

function StaffEditor() {
  const base = usePhoneBase();
  const phoneLink = (id: string) => `${base}/nv-tt/${encodeURIComponent(id)}`;
  const staff = useLive((s) => s.staff);
  const loaded = useLive((s) => s.loaded);
  const { busy, run } = useRun();
  const [rows, setRows] = useState<StaffRow[] | null>(null);
  const view: StaffRow[] = rows ?? staff.map((s, i) => ({ key: i, id: s.id, name: s.name, role: s.role }));
  const dirty = rows !== null;
  const empty = view.some((r) => !r.name.trim());

  const update = (key: number, patch: Partial<StaffRow>) => setRows(view.map((r) => (r.key === key ? { ...r, ...patch } : r)));

  const save = async () => {
    const used = new Set(view.filter((r) => r.id).map((r) => r.id as string));
    const list: StaffInput[] = view.map((r) => {
      let id = r.id;
      if (!id) {
        const base = slugify(r.name);
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
    <section className="panel" aria-labelledby="staff-edit-title">
      <div className="panel-head">
        <h2 id="staff-edit-title">Nhân viên trong ca</h2>
        <span className="sub">Mỗi người mở link riêng trên điện thoại</span>
      </div>
      <div className="panel-body flex flex-col gap-3">
        {view.length ? (
          <ul className="staff-edit">
            {view.map((r) => {
              const st = r.id ? staff.find((s) => s.id === r.id) : undefined;
              return (
                <li key={r.key}>
                  <div className="staff-edit-row">
                    <span className="online-dot" data-online={!!st?.online} aria-label={st?.online ? 'Đang mở app' : 'Chưa mở app'} />
                    <label className="visually-hidden" htmlFor={`sn-${r.key}`}>
                      Tên
                    </label>
                    <input
                      id={`sn-${r.key}`}
                      className="input"
                      placeholder="Tên, ví dụ Lan"
                      autoFocus={r.id === null}
                      value={r.name}
                      maxLength={30}
                      onChange={(ev) => update(r.key, { name: ev.target.value })}
                    />
                    <label className="visually-hidden" htmlFor={`sr-${r.key}`}>
                      Vai trò
                    </label>
                    <select id={`sr-${r.key}`} className="input staff-role" value={r.role} onChange={(ev) => update(r.key, { role: ev.target.value as Role })}>
                      {ROLES.map((role) => (
                        <option key={role} value={role}>
                          {ROLE_LABEL[role]}
                        </option>
                      ))}
                    </select>
                    <button
                      type="button"
                      className="btn btn--icon btn--ghost"
                      aria-label={`Bỏ ${r.name || 'dòng này'}`}
                      onClick={() => setRows(view.filter((x) => x.key !== r.key))}
                    >
                      <Trash size={15} aria-hidden="true" />
                    </button>
                  </div>
                  <div className="staff-link">
                    {r.id && st ? (
                      <>
                        <a className="measured cool" href={phoneLink(r.id)} target="_blank" rel="noopener">
                          {phoneLink(r.id)}
                        </a>
                        <CopyLink url={phoneLink(r.id)} label={`Chép link app của ${r.name}`} />
                        <Link className="btn btn--icon btn--ghost" to={`/nv-tt/${r.id}`} target="_blank" rel="noopener" aria-label={`Mở app của ${r.name}`}>
                          <ExternalLink size={15} aria-hidden="true" />
                        </Link>
                      </>
                    ) : (
                      <span className="tiny muted">Lưu để có link app điện thoại</span>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        ) : (
          <p className="small muted">{loaded ? 'Chưa có nhân viên nào. Thêm ít nhất một người phục vụ để camera có người giao việc.' : 'Chưa đọc được danh sách từ máy chủ.'}</p>
        )}
        {empty && <p className="small bad">Mỗi người cần có tên.</p>}
        <div className="flex gap-2 flex-wrap">
          <button type="button" className="btn" onClick={() => setRows([...view, { key: rowKey++, id: null, name: '', role: 'serve' }])}>
            <Plus size={16} aria-hidden="true" />
            Thêm người
          </button>
          <button type="button" className="btn btn--primary" disabled={!dirty || empty || busy !== null} onClick={() => void save()}>
            <Save size={16} aria-hidden="true" />
            Lưu nhân viên
          </button>
          {dirty && (
            <button type="button" className="btn btn--ghost" onClick={() => setRows(null)}>
              <Undo2 size={16} aria-hidden="true" />
              Bỏ thay đổi
            </button>
          )}
        </div>
        <p className="tiny muted">
          Điện thoại phải dùng cùng mạng Wi-Fi với máy chạy web. Link dùng địa chỉ trang đang mở; nếu đang mở bằng localhost, hãy mở trang này bằng địa chỉ IP của máy
          trước khi gửi link.
        </p>
      </div>
    </section>
  );
}

// ---------- cài đặt LLM và giao việc ----------
interface SettingsForm {
  escalate: string;
  dedup: string;
  verify: string[];
  hold: string[];
}

function toggle(list: string[], k: string, on: boolean) {
  return on ? [...new Set([...list, k])] : list.filter((x) => x !== k);
}

function SettingsPanel() {
  const settings = useLive((s) => s.settings);
  const ten = settings?.provider ?? 'Gemini';
  const { busy, run } = useRun();
  const [form, setForm] = useState<SettingsForm | null>(null);
  const view: SettingsForm | null =
    form ??
    (settings
      ? { escalate: String(settings.escalate_s), dedup: String(settings.dedup_s), verify: settings.verify_kinds, hold: settings.hold_until_verified }
      : null);

  const escalate = Number(view?.escalate);
  const dedup = Number(view?.dedup);
  const invalid = !view || !Number.isFinite(escalate) || escalate < 5 || !Number.isFinite(dedup) || dedup < 0;

  const save = async () => {
    if (!view || invalid) return;
    const out = await run(
      'settings',
      () =>
        putSettings({
          escalate_s: Math.round(escalate),
          dedup_s: Math.round(dedup),
          verify_kinds: view.verify,
          // chỉ chờ được Gemini với loại việc có gửi Gemini kiểm tra
          hold_until_verified: view.hold.filter((k) => view.verify.includes(k)),
        }),
      'Đã lưu cài đặt',
    );
    if (out) {
      live.setSettings(out);
      setForm(null);
    }
  };

  return (
    <section className="panel" aria-labelledby="settings-title">
      <div className="panel-head">
        <h2 id="settings-title">{ten} và giao việc</h2>
        {settings &&
          (settings.gemini ? (
            <span className="chip chip--ok">{ten} đã bật, {settings.model}</span>
          ) : (
            <span className="chip chip--bad">{ten} chưa bật</span>
          ))}
      </div>
      {!view ? (
        <div className="panel-body">
          <p className="small muted">Chưa đọc được cài đặt vì chưa kết nối máy chủ.</p>
        </div>
      ) : (
        <div className="panel-body flex flex-col gap-4">
          {settings && !settings.gemini && (
            <p className="small ink2">
              Máy chủ chưa có <span className="measured">KIE_API_KEY</span> (hoặc <span className="measured">GEMINI_API_KEY</span>), nên mọi việc báo thẳng theo camera, không kiểm tra lại. Thêm khoá vào máy chủ rồi chạy lại để bật.
            </p>
          )}
          <div className="settings-grid">
            <label htmlFor="esc" className="small ink2">
              Chuyển cho người khác nếu chưa ai nhận sau
            </label>
            <span className="flex items-center gap-2">
              <input
                id="esc"
                type="number"
                min={5}
                step={5}
                className="input num-input"
                value={view.escalate}
                onChange={(ev) => setForm({ ...view, escalate: ev.target.value })}
              />
              <span className="small muted">giây</span>
            </span>
            <label htmlFor="dedup" className="small ink2">
              Gộp các lần báo trùng của cùng bàn trong
            </label>
            <span className="flex items-center gap-2">
              <input
                id="dedup"
                type="number"
                min={0}
                step={5}
                className="input num-input"
                value={view.dedup}
                onChange={(ev) => setForm({ ...view, dedup: ev.target.value })}
              />
              <span className="small muted">giây</span>
            </span>
          </div>

          <fieldset className="checks">
            <legend className="small ink2">Gửi ảnh cho {ten} kiểm tra lại</legend>
            {ALERT_KINDS.map((k) => (
              <label key={k} className="check">
                <input type="checkbox" checked={view.verify.includes(k)} onChange={(ev) => setForm({ ...view, verify: toggle(view.verify, k, ev.target.checked) })} />
                {KIND_LABEL[k]}
              </label>
            ))}
          </fieldset>

          <fieldset className="checks">
            <legend className="small ink2">Chờ {ten} xác nhận rồi mới báo nhân viên</legend>
            {ALERT_KINDS.map((k) => {
              const can = view.verify.includes(k);
              return (
                <label key={k} className="check" data-disabled={!can || undefined}>
                  <input
                    type="checkbox"
                    disabled={!can}
                    checked={can && view.hold.includes(k)}
                    onChange={(ev) => setForm({ ...view, hold: toggle(view.hold, k, ev.target.checked) })}
                  />
                  {KIND_LABEL[k]}
                </label>
              );
            })}
            <p className="tiny muted">Gọi phục vụ nên báo ngay: nếu {ten} thấy là báo nhầm, việc tự huỷ trên điện thoại nhân viên.</p>
          </fieldset>

          {invalid && <p className="small bad">Thời gian chuyển người tối thiểu 5 giây, thời gian gộp không được âm.</p>}
          <div className="flex gap-2 flex-wrap">
            <button type="button" className="btn btn--primary" disabled={form === null || invalid || busy !== null} onClick={() => void save()}>
              <Save size={16} aria-hidden="true" />
              Lưu cài đặt
            </button>
            {form && (
              <button type="button" className="btn btn--ghost" onClick={() => setForm(null)}>
                <Undo2 size={16} aria-hidden="true" />
                Bỏ thay đổi
              </button>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

// ---------- xoá dữ liệu ca ----------
function ResetPanel() {
  const { busy, run } = useRun();
  const [confirm, setConfirm] = useState(false);
  const doReset = async () => {
    const out = await run('reset', () => resetShift(), 'Đã xoá dữ liệu ca. Vùng bàn, nhân viên và cài đặt vẫn giữ nguyên.');
    if (out !== undefined) setConfirm(false);
  };
  return (
    <section className="panel" aria-labelledby="reset-title">
      <div className="panel-head">
        <h2 id="reset-title">Bắt đầu ca mới</h2>
      </div>
      <div className="panel-body flex flex-col gap-3">
        <p className="small ink2">Xoá mọi việc, nhật ký, trạng thái bàn và ảnh cắt của ca này. Vùng bàn, nhân viên và cài đặt được giữ lại.</p>
        {confirm ? (
          <div className="reset-confirm" role="alertdialog" aria-labelledby="reset-q">
            <p id="reset-q" className="small flex items-center gap-2">
              <TriangleAlert size={15} aria-hidden="true" className="bad shrink-0" />
              Xoá hẳn dữ liệu ca? Không lấy lại được.
            </p>
            <div className="flex gap-2">
              <button type="button" className="btn btn--danger" disabled={busy !== null} onClick={() => void doReset()}>
                Xoá hẳn
              </button>
              <button type="button" className="btn btn--ghost" onClick={() => setConfirm(false)}>
                Huỷ
              </button>
            </div>
          </div>
        ) : (
          <button type="button" className="btn self-start" onClick={() => setConfirm(true)}>
            <RotateCcw size={16} aria-hidden="true" />
            Xoá dữ liệu ca
          </button>
        )}
      </div>
    </section>
  );
}

export default function LiveSetup() {
  useLiveConnection();
  useTitle('Cài đặt trực tiếp, Easy FnB');
  const status = useLive((s) => s.status);
  const error = useLive((s) => s.error);
  const [params] = useSearchParams();

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Cài đặt trực tiếp</h1>
          <p>Vẽ bàn trên hình camera, thêm nhân viên và chỉnh cách AI kiểm tra trước khi mở ca.</p>
        </div>
      </div>

      {status !== 'live' && (
        <div className="panel live-banner" role="alert" data-tone="bad">
          <TriangleAlert size={18} aria-hidden="true" />
          <div>
            <p className="ink2">{error ?? 'Đang kết nối tới máy chủ Easy FnB.'}</p>
            <p className="tiny muted">Chưa kết nối thì vẫn vẽ được bàn trên video trong máy, nhưng chỉ lưu được khi máy chủ chạy.</p>
          </div>
        </div>
      )}

      <ZoneEditor initialCamera={params.get('cam')} />

      <div className="live-grid live-grid--2">
        <StaffEditor />
        <SettingsPanel />
      </div>

      <div className="live-grid live-grid--2">
        <section className="panel" aria-labelledby="agent-title">
          <div className="panel-head">
            <h2 id="agent-title">Chạy máy camera</h2>
            <span className="sub">Đường ống thị giác gửi sự kiện về máy chủ</span>
          </div>
          <div className="panel-body flex flex-col gap-2">
            <p className="small ink2">Trên máy có video hoặc camera, chạy lệnh dưới đây. Máy camera đọc vùng bàn đã lưu ở trên khi khởi động.</p>
            <AgentCommand />
          </div>
        </section>
        <ResetPanel />
      </div>
    </div>
  );
}
