import { useSearchParams } from 'react-router';
import { StaffApp } from '../components/StaffApp';
import { ROLE_LABEL, STAFF, TASK_INFO } from '../sim/model';
import type { Engine, StaffState } from '../sim/engine';
import { useSim } from '../sim/store';
import { clock, durText, mmss } from '../sim/util';

function statusOf(e: Engine, s: StaffState) {
  const task = e.tasks.find((k) => k.id === s.task);
  switch (s.status) {
    case 'enroute':
      return e.t < s.departAt
        ? { label: `Vừa nhận việc bàn ${task?.table ?? ''}`.trim(), cls: 'chip chip--p2' }
        : { label: `Đang tới bàn ${task?.table ?? ''}`.trim(), cls: 'chip chip--p2' };
    case 'serving':
      return { label: `Đang ở bàn ${task?.table ?? ''}`.trim(), cls: 'chip chip--cool' };
    case 'break':
      return { label: 'Nghỉ giải lao', cls: 'chip' };
    default:
      return { label: 'Rảnh', cls: 'chip chip--ok' };
  }
}

export default function Staff() {
  const e = useSim();
  const [params, setParams] = useSearchParams();
  const selected = e.staff.find((s) => s.id === params.get('nv')) ?? e.staff[0];
  const log = e.tasks
    .filter((k) => k.assignee && k.assignee !== 'bep')
    .slice(-12)
    .reverse();

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Nhân viên trong ca</h1>
          <p>Mỗi việc được giao cho đúng một người, dựa trên vị trí thật, ai đang rảnh và khu phụ trách.</p>
        </div>
      </div>

      <div className="split">
        <section className="panel" aria-labelledby="staff-title">
          <div className="panel-head">
            <h2 id="staff-title">Danh sách và chấm công</h2>
            <span className="sub">Chấm công tự động khi camera nhận ra nhân viên ở cửa</span>
          </div>
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th scope="col">Nhân viên</th>
                  <th scope="col">Trạng thái</th>
                  <th scope="col" className="num">
                    Việc đã xử lý
                  </th>
                  <th scope="col" className="num">
                    Phản hồi trung vị
                  </th>
                  <th scope="col" className="num">
                    Vào ca
                  </th>
                </tr>
              </thead>
              <tbody>
                {STAFF.map((def) => {
                  const s = e.staff.find((x) => x.id === def.id)!;
                  const st = statusOf(e, s);
                  const med = e.staffMedian(def.id);
                  return (
                    <tr key={def.id} aria-selected={def.id === selected.id}>
                      <td>
                        <button type="button" className="row-btn" onClick={() => setParams({ nv: def.id }, { replace: true })}>
                          {def.name}
                        </button>
                        <div className="tiny muted">
                          {ROLE_LABEL[def.role]}
                          {def.zone ? `, khu ${def.zone}` : ''}
                        </div>
                      </td>
                      <td>
                        <span className={st.cls}>{st.label}</span>
                      </td>
                      <td className="num">{s.handled}</td>
                      <td className="num">{Number.isNaN(med) ? 'chưa có' : mmss(med)}</td>
                      <td className="num">{clock(def.clockIn, false)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>

        <StaffApp id={selected.id} />
      </div>

      <section className="panel" aria-labelledby="log-title">
        <div className="panel-head">
          <h2 id="log-title">Nhật ký giao việc</h2>
          <span className="sub">Vì sao hệ thống chọn người đó</span>
        </div>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th scope="col" className="num">
                  Lúc giao
                </th>
                <th scope="col">Việc</th>
                <th scope="col">Giao cho</th>
                <th scope="col">Lý do chọn</th>
                <th scope="col" className="num">
                  Tới bàn sau
                </th>
              </tr>
            </thead>
            <tbody>
              {log.map((k) => (
                <tr key={k.id}>
                  <td className="num">{clock(k.assignedAt ?? k.created)}</td>
                  <td>
                    Bàn {k.table}, {TASK_INFO[k.kind].label}
                  </td>
                  <td className="amber">{e.staffName(k.assignee!)}</td>
                  <td>{k.why}</td>
                  <td className="num">{k.arrivedAt ? durText(k.arrivedAt - k.created) : k.status === 'cancelled' ? 'đã hủy' : 'đang tới'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
