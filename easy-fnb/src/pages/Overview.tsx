import { Link, useSearchParams } from 'react-router';
import { Cctv, DoorOpen, GlassWater, Hand, Receipt, TriangleAlert, UserCheck } from 'lucide-react';
import { FloorMap } from '../components/FloorMap';
import { Empty, PriorityChip, Stat } from '../components/ui';
import { PHASE_LABEL, TASK_INFO, ZONE_CAMERA, prior, tableDef } from '../sim/model';
import type { Engine, Task, Trigger } from '../sim/engine';
import { useSim } from '../sim/store';
import { clock, durText, mmss } from '../sim/util';
import { cameraLabel } from '../sim/agent';

function taskTitle(e: Engine, k: Task) {
  if (k.kind === 'greet' && k.person) return `${e.personName(k.person)} vừa tới`;
  return TASK_INFO[k.kind].label;
}

function TaskList({ e, onSelect }: { e: Engine; onSelect: (id: number) => void }) {
  const open = e.openTasks();
  if (!open.length) {
    return (
      <Empty title="Không có việc nào đang chờ">
        <p>Camera sẽ báo ngay khi có khách giơ tay, bàn mới ngồi hoặc bàn cần dọn. Dùng bảng điều khiển bên dưới để tạo một tình huống.</p>
      </Empty>
    );
  }
  return (
    <ul className="list" aria-label="Việc đang chờ, sắp theo mức ưu tiên">
      {open.map((k) => (
        <li key={k.id} className="task">
          <PriorityChip p={k.priority} />
          <span className="task-title">
            <button type="button" onClick={() => onSelect(k.table)}>
              Bàn {k.table}
            </button>{' '}
            {taskTitle(e, k)}
          </span>
          <span className="measured cool" aria-label={`Đã chờ ${durText(e.t - k.created)}`}>
            {mmss(e.t - k.created)}
          </span>
          <span className="task-meta">
            {k.assignee === 'bep' ? (
              <>Đã báo màn hình bếp</>
            ) : k.assignee ? (
              <>
                <span className="amber">{e.staffName(k.assignee)}</span> đang tới. {k.why}
              </>
            ) : k.escalated ? (
              <span className="bad">Chưa có ai rảnh, đã báo quản lý ca</span>
            ) : (
              <>Đang tìm nhân viên phù hợp</>
            )}
          </span>
        </li>
      ))}
    </ul>
  );
}

function TableDetail({ e, id }: { e: Engine; id: number }) {
  const tb = e.table(id);
  const d = tableDef(id);
  const cam = ZONE_CAMERA[d.zone];
  if (tb.phase === 'empty') {
    return (
      <Empty title={`Bàn ${id} đang trống`}>
        <p>
          {d.seats} chỗ, khu {d.zone}. Bàn sẽ được xếp cho nhóm khách tiếp theo vừa số chỗ.
        </p>
      </Empty>
    );
  }
  const base = tb.phase === 'waiting_food' ? tb.orderedAt ?? tb.since : tb.since;
  const reading = e.reading(tb);
  const daypart = e.t / 3600 >= 17 ? 'buổi tối' : 'buổi trưa';
  return (
    <div>
      <div className="detail-section">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="chip">{PHASE_LABEL[tb.phase]}</span>
          <span className="small ink2">{tb.party} khách</span>
          {tb.person && <span className="small amber">{e.personName(tb.person)}</span>}
        </div>
        <div className="flex items-end gap-3 mt-4">
          <span className="reading">{tb.urgency}</span>
          <span className="small muted pb-1">điểm khẩn cấp trên 100</span>
        </div>
        <p className="mt-2 ink2">{tb.reason}</p>
      </div>
      <div className="detail-section">
        <dl className="kv">
          <dt>Thời gian ở giai đoạn này</dt>
          <dd>{mmss(e.t - base)}</dd>
          <dt>
            Ngưỡng thường lệ (nhóm {tb.party}, {daypart})
          </dt>
          <dd>{mmss(prior(tb.phase, tb.party))}</dd>
          <dt>Nhân viên ghé gần nhất</dt>
          <dd>{tb.lastVisit && tb.lastStaff ? `${e.staffName(tb.lastStaff)}, ${mmss(e.t - tb.lastVisit)} trước` : 'chưa có'}</dd>
          <dt>Camera theo dõi</dt>
          <dd>{cameraLabel(cam)}</dd>
        </dl>
      </div>
      <div className="detail-section">
        <h3 className="small muted mb-2">Mô hình thị giác đọc bàn</h3>
        <pre className="code" aria-label="Kết quả JSON của mô hình thị giác">
          {'{\n'}
          {Object.entries(reading).map(([k, v], i, arr) => (
            <span key={k}>
              {'  '}
              <span className="k">"{k}"</span>: <span className="v">{typeof v === 'string' ? `"${v}"` : String(v)}</span>
              {i < arr.length - 1 ? ',\n' : '\n'}
            </span>
          ))}
          {'}'}
        </pre>
      </div>
      <div className="detail-section">
        <h3 className="small muted mb-2">Diễn biến bàn {id}</h3>
        <ol className="spine">
          {tb.history.map((h, i) => (
            <li key={`${h.phase}-${h.t}`} data-current={i === tb.history.length - 1}>
              <span>{PHASE_LABEL[h.phase]}</span>
              <span className="measured cool">{clock(h.t)}</span>
            </li>
          ))}
        </ol>
        <Link className="btn mt-4" to={`/camera?cam=${cam}`}>
          <Cctv size={16} aria-hidden="true" />
          Xem {cameraLabel(cam)}
        </Link>
      </div>
    </div>
  );
}

const TRIGGERS: { kind: Trigger; label: string; icon: typeof Hand }[] = [
  { kind: 'hand', label: 'Khách giơ tay', icon: Hand },
  { kind: 'regular', label: 'Khách quen tới', icon: UserCheck },
  { kind: 'bill', label: 'Ra hiệu tính tiền', icon: Receipt },
  { kind: 'glass', label: 'Ly đã cạn', icon: GlassWater },
  { kind: 'broken', label: 'Có đồ vỡ', icon: TriangleAlert },
  { kind: 'balk', label: 'Khách bỏ về ở cửa', icon: DoorOpen },
];

export default function Overview() {
  const e = useSim();
  const [params, setParams] = useSearchParams();
  const selected = params.get('ban') ? Number(params.get('ban')) : undefined;
  const view = selected && params.get('xem') !== 'viec' ? 'ban' : 'viec';
  const open = e.openTasks();
  const p1 = open.filter((k) => k.priority === 1).length;
  const occupied = e.tables.filter((tb) => tb.phase !== 'empty').length;
  const soon = e.soonFree()[0];
  const med = e.medianResponse();

  const select = (id: number) => setParams({ ban: String(id) }, { replace: true });

  return (
    <div className="page">
      <h1 className="visually-hidden">Tổng quan ca tối</h1>
      <section className="panels stats" aria-label="Số liệu ca hiện tại">
        <Stat label="Khách đang ngồi" value={e.guestsSeated()} sub={`${occupied} trên 14 bàn có khách`} />
        <Stat label="Phản hồi trung vị" value={Number.isNaN(med) ? 'chưa có' : mmss(med)} sub="từ lúc camera phát hiện tới khi có nhân viên" />
        <Stat label="Việc đang mở" value={open.length} sub={p1 ? `${p1} việc khẩn cấp` : 'không có việc khẩn cấp'} />
        <Stat
          label="Đang chờ ở cửa"
          value={`${e.waitlist.length} nhóm`}
          sub={soon ? `Bàn ${soon.table} trống sau khoảng ${Math.max(1, Math.round(soon.eta / 60))} phút` : 'Chưa có bàn sắp trống'}
        />
        <Stat label="Khách bỏ về ở cửa" value={e.balks} sub={`nhóm, tính từ ${clock(17 * 3600, false)}`} />
      </section>

      <div className="overview">
        <section className="panel" aria-labelledby="floor-title">
          <div className="panel-head">
            <h2 id="floor-title">Sơ đồ quán</h2>
            <div className="legend" aria-label="Chú giải màu">
              <span className="chip">Bình thường</span>
              <span className="chip chip--p2">Cần chú ý</span>
              <span className="chip chip--p1">Khẩn cấp</span>
              <span className="small muted">Chấm vàng là nhân viên</span>
            </div>
          </div>
          <div className="floor-wrap">
            <FloorMap selected={selected} onSelect={select} />
          </div>
        </section>

        <aside className="panel" aria-label="Việc đang chờ và chi tiết bàn">
          <div className="panel-head">
            <div className="seg" role="tablist" aria-label="Chọn nội dung">
              <button
                type="button"
                role="tab"
                aria-selected={view === 'viec'}
                onClick={() => setParams(selected ? { ban: String(selected), xem: 'viec' } : {}, { replace: true })}
              >
                Việc đang chờ ({open.length})
              </button>
              {selected && (
                <button type="button" role="tab" aria-selected={view === 'ban'} onClick={() => select(selected)}>
                  Bàn {selected}
                </button>
              )}
            </div>
            {selected && (
              <button type="button" className="btn btn--ghost btn--sm" onClick={() => setParams({}, { replace: true })}>
                Bỏ chọn
              </button>
            )}
          </div>
          <div className="scroll" style={{ maxHeight: 'min(72vh, 640px)' }} role="tabpanel">
            {view === 'ban' && selected ? <TableDetail e={e} id={selected} /> : <TaskList e={e} onSelect={select} />}
          </div>
        </aside>
      </div>

      <div className="split">
        <section className="panel" aria-labelledby="events-title">
          <div className="panel-head">
            <h2 id="events-title">Nhật ký sự kiện</h2>
            <span className="sub">Mới nhất ở trên</span>
          </div>
          <ol className="trail scroll" style={{ maxHeight: 320 }}>
            {e.events
              .slice(-24)
              .reverse()
              .map((ev) => (
                <li key={ev.id}>
                  <time>{clock(ev.t)}</time>
                  <span className="ev" data-tone={ev.tone}>
                    {ev.who && <span className="who">{ev.who} </span>}
                    {ev.text}
                  </span>
                </li>
              ))}
          </ol>
        </section>
        <section className="panel" aria-labelledby="demo-title">
          <div className="panel-head">
            <h2 id="demo-title">Tạo tình huống</h2>
            <span className="sub">Dùng khi trình diễn</span>
          </div>
          <div className="panel-body grid grid-cols-2 gap-2">
            {TRIGGERS.map(({ kind, label, icon: Icon }) => (
              <button key={kind} type="button" className="btn btn--start" onClick={() => e.trigger(kind)}>
                <Icon size={16} aria-hidden="true" />
                {label}
              </button>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
