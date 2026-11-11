import { memo, useMemo, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router";
import {
  Check,
  ExternalLink,
  Plus,
  Settings2,
  TriangleAlert,
  X,
} from "lucide-react";
import { Empty, Stat } from "../../components/ui";
import {
  assignAlert,
  cancelAlert,
  createAlert,
  doneAlert,
} from "../../live/api";
import { useReport, useRun, useTitle } from "../../live/hooks";
import { LiveCamera } from "../../live/LiveCamera";
import {
  live,
  useLive,
  useLiveConnection,
  useServerNow,
} from "../../live/store";
import {
  ageText,
  byName,
  cameraLive,
  byUrgency,
  clockTime,
  isActive,
  isClosed,
  KIND_LABEL,
  ROLE_LABEL,
  secText,
  statusText,
  TABLE_STATE_CHIP,
  TABLE_STATE_LABEL,
  tableText,
} from "../../live/text";
import {
  AgentCommand,
  CropImg,
  EvidenceView,
  ItemsLeft,
  KindChip,
  VerifyChip,
} from "../../live/ui";
import {
  ALERT_KINDS,
  type Alert,
  type AlertKind,
  type Staff,
  type TableState,
} from "../../live/types";

// ---------- một việc trong hàng đợi ----------
function AlertCard({
  a,
  staff,
  now,
}: {
  a: Alert;
  staff: Staff[];
  now: number;
}) {
  const { busy, run } = useRun();
  const ten = useLive((s) => s.settings?.provider) ?? "Gemini";
  const age = now - a.created_at;
  const label = `${KIND_LABEL[a.kind]}, ${tableText(a.table)}`;

  const act = async (key: string, fn: () => Promise<Alert>) => {
    const out = await run(`${key}-${a.id}`, fn);
    if (out) live.upsertAlert(out);
  };

  return (
    <li
      className="acard"
      data-kind={a.kind}
      data-status={a.status}
      data-escalated={a.escalated || undefined}
    >
      <div className="acard-top">
        <KindChip kind={a.kind} />
        <span className="acard-table">{tableText(a.table)}</span>
        <span
          className="acard-age measured"
          aria-label={`Đã chờ ${ageText(age)}`}
        >
          {ageText(age)}
        </span>
      </div>
      <div className="acard-body">
        <CropImg
          url={a.crop_url}
          alt={`Ảnh camera lúc báo: ${label}`}
          className="acard-crop"
        />
        <div className="acard-info">
          <p className="small ink2">{statusText(a, staff, ten)}</p>
          <div className="acard-chips">
            <VerifyChip verify={a.verify} ten={ten} />
            {a.repeats > 0 && (
              <span className="chip">lặp lại ×{a.repeats}</span>
            )}
            {a.escalated && (
              <span className="chip chip--bad">
                <TriangleAlert size={12} aria-hidden="true" />
                Quá hạn, đã chuyển người
              </span>
            )}
          </div>
          {a.verify.reason && a.verify.state !== "pending" && (
            <p
              className={`tiny ${a.verify.state === "rejected" ? "bad" : "muted"}`}
            >
              {ten}: {a.verify.reason}
            </p>
          )}
          {a.kind === "needs_clearing" && <ItemsLeft items={a.items} />}
          {a.detail && <p className="tiny muted">{a.detail}</p>}
        </div>
      </div>
      <EvidenceView evidence={a.evidence} label={label} />
      <div className="acard-actions">
        <label className="acard-assign">
          <span className="visually-hidden">Giao {label} cho</span>
          <select
            className="input"
            value={a.assigned_to ?? ""}
            disabled={!staff.length || busy !== null}
            onChange={(ev) =>
              ev.target.value &&
              void act("assign", () => assignAlert(a.id, ev.target.value))
            }
          >
            <option value="" disabled>
              {staff.length ? "Chọn người làm" : "Chưa có nhân viên"}
            </option>
            {a.assigned_to && !staff.some((s) => s.id === a.assigned_to) && (
              <option value={a.assigned_to}>{a.assigned_to}</option>
            )}
            {staff.map((s) => (
              <option key={s.id} value={s.id}>
                {s.online ? "● " : "○ "}
                {s.name}, {ROLE_LABEL[s.role].toLowerCase()}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          className="btn btn--sm"
          disabled={busy !== null}
          onClick={() => void act("done", () => doneAlert(a.id, "manager"))}
        >
          <Check size={14} aria-hidden="true" />
          Xong
        </button>
        <button
          type="button"
          className="btn btn--sm btn--ghost"
          disabled={busy !== null}
          onClick={() =>
            void act("cancel", () => cancelAlert(a.id, "manager", "báo nhầm"))
          }
        >
          <X size={14} aria-hidden="true" />
          Báo nhầm
        </button>
      </div>
    </li>
  );
}

function closedAt(a: Alert) {
  return a.done_at ?? a.cancelled_at ?? a.created_at;
}

// ---------- tạo việc bằng tay ----------
function ManualCreate({ camera }: { camera: string }) {
  const zones = useLive((s) => s.zones);
  const { busy, run } = useRun();
  const [kind, setKind] = useState<AlertKind>("call");
  const [table, setTable] = useState("");
  const names = useMemo(
    () =>
      [...new Set(zones.flatMap((z) => z.tables.map((t) => t.id)))].sort(
        byName,
      ),
    [zones],
  );
  const cameraOf = (id: string) =>
    zones.find((z) => z.tables.some((t) => t.id === id))?.camera ?? camera;

  const submit = async (ev: FormEvent) => {
    ev.preventDefault();
    const t = table.trim() || null;
    const out = await run(
      "create",
      () => createAlert(kind, t, t ? cameraOf(t) : camera),
      `Đã tạo việc ${KIND_LABEL[kind].toLowerCase()}${t ? ` cho bàn ${t}` : ""}`,
    );
    if (out) {
      live.upsertAlert(out);
      setTable("");
    }
  };

  return (
    <details className="manual">
      <summary>
        <Plus size={14} aria-hidden="true" />
        Tạo việc thủ công
      </summary>
      <form className="manual-form" onSubmit={(ev) => void submit(ev)}>
        <div className="seg" role="group" aria-label="Loại việc">
          {ALERT_KINDS.map((k) => (
            <button
              key={k}
              type="button"
              aria-pressed={kind === k}
              onClick={() => setKind(k)}
            >
              {KIND_LABEL[k]}
            </button>
          ))}
        </div>
        <div className="flex gap-2">
          <label className="visually-hidden" htmlFor="manual-table">
            Bàn
          </label>
          <input
            id="manual-table"
            className="input"
            list="manual-tables"
            placeholder={
              names.length ? `Bàn, ví dụ ${names[0]}` : "Tên bàn, ví dụ B2"
            }
            value={table}
            onChange={(ev) => setTable(ev.target.value)}
          />
          <datalist id="manual-tables">
            {names.map((n) => (
              <option key={n} value={n} />
            ))}
          </datalist>
          <button
            type="submit"
            className="btn btn--primary"
            disabled={busy !== null}
          >
            Tạo việc
          </button>
        </div>
        <p className="tiny muted">
          Việc tạo tay không qua AI, báo ngay cho nhân viên.
        </p>
      </form>
    </details>
  );
}

// ---------- hàng đợi việc ----------
const AlertQueue = memo(function AlertQueue({
  camera,
  full,
}: {
  camera: string;
  full: boolean;
}) {
  const alerts = useLive((s) => s.alerts);
  const staff = useLive((s) => s.staff);
  const ten = useLive((s) => s.settings?.provider) ?? "Gemini";
  const now = useServerNow();
  const active = useMemo(
    () => alerts.filter(isActive).sort(byUrgency),
    [alerts],
  );
  const closed = useMemo(
    () =>
      alerts
        .filter(isClosed)
        .sort((a, b) => closedAt(b) - closedAt(a))
        .slice(0, 20),
    [alerts],
  );
  const calls = active.filter((a) => a.kind === "call").length;

  return (
    <section className="panel live-alerts" aria-labelledby="queue-title">
      <div className="panel-head">
        <h2 id="queue-title">Việc đang chờ ({active.length})</h2>
        <span className="sub">
          {calls ? `${calls} khách đang gọi` : "Gọi phục vụ luôn ở trên cùng"}
        </span>
      </div>
      <div className="scroll live-queue">
        {active.length ? (
          <ul
            className="list"
            aria-label="Việc đang chờ, gọi phục vụ trước, chờ lâu trước"
          >
            {active.map((a) => (
              <AlertCard key={a.id} a={a} staff={staff} now={now} />
            ))}
          </ul>
        ) : (
          <Empty title="Không có việc nào đang chờ">
            <p>
              Khi camera thấy khách giơ tay, bàn cần dọn hoặc khách mới ngồi,
              việc sẽ hiện ở đây và điện thoại nhân viên sẽ kêu.
            </p>
          </Empty>
        )}
        {closed.length > 0 && (
          <details className="closed">
            <summary>Đã xong gần đây ({closed.length})</summary>
            <ol className="closed-list">
              {closed.map((a) => (
                <li key={a.id}>
                  <time className="measured cool">
                    {clockTime(closedAt(a))}
                  </time>
                  <span className="min-w-0">
                    <span className="ink2">
                      {tableText(a.table)}, {KIND_LABEL[a.kind].toLowerCase()}
                    </span>
                    <span
                      className={`tiny ${a.status === "cancelled" ? "bad" : "muted"}`}
                    >
                      {" "}
                      {statusText(a, staff, ten)}
                    </span>
                  </span>
                </li>
              ))}
            </ol>
          </details>
        )}
      </div>
      {full && <ManualCreate camera={camera} />}
    </section>
  );
});

// ---------- bàn ----------
interface Row {
  id: string;
  st: TableState | undefined;
}

const TablesPanel = memo(function TablesPanel() {
  const zones = useLive((s) => s.zones);
  const tables = useLive((s) => s.tables);
  const now = useServerNow();
  const rows = useMemo<Row[]>(() => {
    const map = new Map<string, Row>();
    for (const z of zones)
      for (const t of z.tables) map.set(t.id, { id: t.id, st: undefined });
    for (const t of tables) map.set(t.id, { id: t.id, st: t });
    return [...map.values()].sort((a, b) => byName(a.id, b.id));
  }, [zones, tables]);

  return (
    <section className="panel" aria-labelledby="tables-title">
      <div className="panel-head">
        <h2 id="tables-title">Bàn</h2>
        <span className="sub">
          {rows.filter((r) => r.st?.state === "occupied").length} bàn có khách
        </span>
      </div>
      {rows.length ? (
        <div className="table-wrap scroll live-scroll">
          <table className="table">
            <thead>
              <tr>
                <th scope="col">Bàn</th>
                <th scope="col">Trạng thái</th>
                <th scope="col" className="num">
                  Khách
                </th>
                <th scope="col" className="num">
                  Đã bao lâu
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map(({ id, st }) => (
                <tr key={id}>
                  <td className="ink2">{id}</td>
                  <td>
                    <span className={TABLE_STATE_CHIP[st?.state ?? "unknown"]}>
                      {TABLE_STATE_LABEL[st?.state ?? "unknown"]}
                    </span>
                  </td>
                  <td className="num">{st ? st.people : ""}</td>
                  <td className="num">{st ? ageText(now - st.since) : ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <Empty title="Chưa có bàn nào">
          <p>
            Vẽ vùng bàn trên hình camera ở trang{" "}
            <Link to="/truc-tiep/cai-dat">Cài đặt</Link> để camera biết khách
            ngồi bàn nào.
          </p>
        </Empty>
      )}
    </section>
  );
});

// ---------- nhân viên ----------
const clockVN = (ms: number) =>
  new Date(ms).toLocaleTimeString("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Asia/Ho_Chi_Minh",
  });

/** Điểm danh: "Vào ca 08:12, đã làm 2 giờ 5 phút" */
function attendanceText(s: Staff, now: number) {
  if (!s.first_in) return "Chưa vào ca";
  const worked = (s.worked_s ?? 0) * 1000 + (s.on_since ? now - s.on_since : 0);
  return `${s.on_since ? "Đang trực" : "Đã ra ca"}, vào ca ${clockVN(s.first_in)}, đã làm ${ageText(worked)}`;
}

const StaffPanel = memo(function StaffPanel() {
  const staff = useLive((s) => s.staff);
  const now = useServerNow();
  return (
    <section className="panel" aria-labelledby="staff-title">
      <div className="panel-head">
        <h2 id="staff-title">Nhân viên</h2>
        <span className="sub">
          {staff.filter((s) => s.online).length} người đang mở app
        </span>
      </div>
      {staff.length ? (
        <ul className="staff-list scroll live-scroll">
          {staff.map((s) => (
            <li key={s.id}>
              <span
                className="online-dot"
                data-online={s.online}
                aria-label={s.online ? "Đang mở app" : "Chưa mở app"}
              />
              <span className="min-w-0 flex-1">
                <span className="ink2">{s.name}</span>
                <span className="tiny muted"> {ROLE_LABEL[s.role]}</span>
                <span className="tiny muted block">
                  {attendanceText(s, now)}
                </span>
              </span>
              <span className={s.open_tasks ? "chip chip--p2" : "chip"}>
                {s.open_tasks ? `${s.open_tasks} việc` : "rảnh"}
              </span>
              <Link
                className="btn btn--icon btn--ghost"
                to={`/nv-tt/${s.id}`}
                target="_blank"
                rel="noopener"
                aria-label={`Mở app điện thoại của ${s.name}`}
              >
                <ExternalLink size={15} aria-hidden="true" />
              </Link>
            </li>
          ))}
        </ul>
      ) : (
        <Empty title="Chưa có nhân viên">
          <p>
            Thêm tên và vai trò ở trang{" "}
            <Link to="/truc-tiep/cai-dat">Cài đặt</Link>, rồi mở link app trên
            điện thoại từng người.
          </p>
        </Empty>
      )}
    </section>
  );
});

// ---------- nhật ký ----------
const LOG_TONE: Partial<Record<string, string>> = {
  escalate: "bad",
  cancel: "bad",
  call: "call",
  arrived: "ok",
};

const EventLog = memo(function EventLog() {
  const log = useLive((s) => s.log);
  const shown = log.slice(0, 80);
  return (
    <section className="panel" aria-labelledby="log-title">
      <div className="panel-head">
        <h2 id="log-title">Nhật ký sự kiện</h2>
        <span className="sub">Mới nhất ở trên</span>
      </div>
      {shown.length ? (
        <ol className="trail scroll live-scroll">
          {shown.map((e) => (
            <li key={e.id}>
              <time>{clockTime(e.t)}</time>
              <span className="ev" data-tone={LOG_TONE[e.kind]}>
                {e.text}
              </span>
            </li>
          ))}
        </ol>
      ) : (
        <Empty title="Chưa có sự kiện nào trong ca">
          <p>
            Mỗi lần camera thấy khách vào, giơ tay, rời bàn hay bàn đã dọn sẽ
            ghi một dòng ở đây.
          </p>
        </Empty>
      )}
    </section>
  );
});

// ---------- số liệu ca ----------
const ShiftStats = memo(function ShiftStats() {
  const { report, error } = useReport(10000);
  const alerts = useLive((s) => s.alerts);
  const tables = useLive((s) => s.tables);
  const settings = useLive((s) => s.settings);
  const active = alerts.filter(isActive);
  const calling = active.filter((a) => a.kind === "call").length;
  const occupied = tables.filter((t) => t.state === "occupied").length;
  const dirty = tables.filter((t) => t.state === "needs_clearing").length;
  const wait = report ? null : error ? "chưa có" : "…";

  return (
    <section className="panels stats" aria-label="Số liệu ca hiện tại">
      <Stat
        label="Lượt gọi phục vụ"
        value={wait ?? report!.counts.call}
        sub={
          report
            ? `${report.counts.needs_clearing} lượt dọn bàn, ${report.counts.new_guest} lượt khách mới`
            : (error ?? "đang lấy số liệu")
        }
      />
      <Stat
        label="Phản hồi trung bình"
        value={wait ?? secText(report!.response_s.mean)}
        sub={
          report?.arrived
            ? `từ lúc báo tới lúc camera thấy nhân viên ở bàn (${report.arrived} lượt)`
            : "từ lúc báo tới lúc camera thấy nhân viên ở bàn"
        }
      />
      <Stat
        label={`Báo nhầm ${settings?.provider ?? "Gemini"} chặn`}
        value={wait ?? report!.rejected_by_gemini}
        sub={
          settings
            ? settings.gemini
              ? `kiểm tra bằng ${settings.model}`
              : `${settings.provider ?? "Gemini"} chưa bật trên máy chủ`
            : "chưa rõ"
        }
      />
      <Stat
        label="Việc đang mở"
        value={active.length}
        sub={calling ? `${calling} khách đang gọi` : "không có khách đang gọi"}
      />
      <Stat
        label="Bàn có khách"
        value={`${occupied}/${tables.length}`}
        sub={dirty ? `${dirty} bàn cần dọn` : "không có bàn chờ dọn"}
      />
    </section>
  );
});

// ---------- trang ----------
export default function LiveDashboard() {
  useLiveConnection();
  useTitle("Trực tiếp, Easy FnB");
  const status = useLive((s) => s.status);
  const loaded = useLive((s) => s.loaded);
  const error = useLive((s) => s.error);
  const cameras = useLive((s) => s.cameras);
  const zones = useLive((s) => s.zones);
  const tables = useLive((s) => s.tables);
  const alerts = useLive((s) => s.alerts);
  const [params, setParams] = useSearchParams();

  const now = useServerNow();
  const fallback = cameras.find((c) => cameraLive(c, now)) ?? cameras[0];
  const cam = cameras.find((c) => c.id === params.get("cam")) ?? fallback;
  const camZones = cam ? zones.find((z) => z.camera === cam.id) : undefined;
  const active = useMemo(() => alerts.filter(isActive), [alerts]);
  const anyOnline = cameras.some((c) => cameraLive(c, now));
  // Mặc định chỉ hiện camera và việc đang chờ; số liệu ca, bàn, nhân viên, nhật ký nằm sau nút "Xem thêm"
  const [full, setFull] = useState(() => {
    try {
      return localStorage.getItem("fnb-dash-full") === "1";
    } catch {
      return false;
    }
  });
  const toggleFull = () =>
    setFull((v) => {
      try {
        localStorage.setItem("fnb-dash-full", v ? "0" : "1");
      } catch {
        // không lưu được thì thôi
      }
      return !v;
    });

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Trực tiếp</h1>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <button
            type="button"
            className="btn btn--sm btn--ghost"
            aria-pressed={full}
            onClick={toggleFull}
          >
            {full ? "Thu gọn" : "Xem thêm"}
          </button>
          <Link className="btn btn--sm" to="/truc-tiep/cai-dat">
            <Settings2 size={14} aria-hidden="true" />
            Cài đặt
          </Link>
        </div>
      </div>

      {status !== "live" && (
        <div
          className="panel live-banner"
          role="alert"
          data-tone={loaded ? "warn" : "bad"}
        >
          <TriangleAlert size={18} aria-hidden="true" />
          <div>
            <p className="ink2">
              {error ?? "Đang kết nối tới máy chủ Easy FnB."}
            </p>
            <p className="tiny muted">
              {loaded
                ? "Số liệu bên dưới có thể đã cũ. Trang tự nối lại khi máy chủ chạy tiếp."
                : "Bật máy chủ Easy FnB (thư mục easy-fnb/server, cổng 8080). Trang sẽ tự kết nối khi máy chủ chạy."}
            </p>
          </div>
        </div>
      )}

      {full && <ShiftStats />}

      <div className="live-main">
        <section className="panel" aria-labelledby="cam-title">
          <div className="panel-head">
            <h2 id="cam-title">Camera</h2>
            {full && cameras.length > 1 && (
              <div className="seg" role="group" aria-label="Chọn camera">
                {cameras.map((c) => (
                  <button
                    key={c.id}
                    type="button"
                    aria-pressed={c.id === cam?.id}
                    onClick={() => setParams({ cam: c.id }, { replace: true })}
                  >
                    <span
                      className="online-dot"
                      data-online={cameraLive(c, now)}
                      aria-hidden="true"
                    />
                    {c.name || c.id}
                  </button>
                ))}
              </div>
            )}
            {full && (
              <div className="legend" aria-label="Chú giải màu bàn">
                <span className="chip">Trống</span>
                <span className="chip chip--cool">Có khách</span>
                <span className="chip chip--p2">Cần dọn</span>
                <span className="chip chip--p1">Đang gọi</span>
              </div>
            )}
          </div>
          <div className="panel-body flex flex-col gap-3">
            {cam ? (
              <>
                <LiveCamera
                  key={cam.id}
                  camera={cam}
                  zones={camZones}
                  tables={tables}
                  alerts={active}
                />
                {full && !camZones?.tables.length && (
                  <p className="small muted">
                    Camera này chưa có vùng bàn.{" "}
                    <Link
                      to={`/truc-tiep/cai-dat?cam=${encodeURIComponent(cam.id)}`}
                    >
                      Vẽ vùng bàn
                    </Link>{" "}
                    để biết khách ngồi bàn nào.
                  </p>
                )}
                {!anyOnline && (
                  <div className="flex flex-col gap-2">
                    <p className="small ink2">
                      Không có camera nào đang gửi hình. Chạy máy camera bằng
                      lệnh:
                    </p>
                    <AgentCommand />
                  </div>
                )}
              </>
            ) : (
              <div className="flex flex-col gap-3">
                <Empty title="Chưa có camera nào gửi hình">
                  <p>
                    Máy camera chạy mô hình thị giác trên video rồi gửi khung
                    hình và sự kiện về máy chủ. Chạy lệnh sau trên máy có video:
                  </p>
                </Empty>
                <AgentCommand />
              </div>
            )}
          </div>
        </section>

        <AlertQueue camera={cam?.id ?? "cam1"} full={full} />
      </div>

      {full && (
        <>
          <div className="live-grid">
            <TablesPanel />
            <StaffPanel />
            <EventLog />
          </div>
          <p className="tiny muted">
            Đang dùng dữ liệu thật. Bản mô phỏng vẫn ở trang{" "}
            <Link to="/">Tổng quan</Link>.
          </p>
        </>
      )}
    </div>
  );
}
