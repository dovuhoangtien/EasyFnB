import { useSearchParams } from 'react-router';
import { CameraView } from '../components/CameraView';
import { Empty } from '../components/ui';
import { CAMERAS, cameraDef } from '../sim/model';
import { useSim } from '../sim/store';
import { clock, dec } from '../sim/util';
import { cameraLabel } from '../sim/agent';

/** Dao động nhỏ, ổn định theo thời gian, cho các số đo mô phỏng */
const wobble = (t: number, k: number) => Math.sin(t * 0.37 * k + k) * 0.5 + Math.sin(t * 0.11 * k) * 0.5;

export default function Camera() {
  const e = useSim();
  const [params, setParams] = useSearchParams();
  const current = cameraDef(params.get('cam') ?? 'cam3') ?? cameraDef('cam3');
  const live = CAMERAS.filter((c) => c.view).length;

  const decode = 5.6 + wobble(e.t, 1) * 0.8;
  const detect = 3.6 + wobble(e.t, 2) * 0.4;
  const pose = 6.8 + wobble(e.t, 3) * 1.1;
  const track = 0.9 + wobble(e.t, 4) * 0.2;
  const total = decode + detect + pose + track;
  const stages = [
    { name: 'Giải mã RTSP', model: `${live} luồng phụ 720p`, ms: decode },
    { name: 'Phát hiện người và bát đĩa', model: 'RF-DETR-S', ms: detect },
    { name: 'Tư thế nhiều người', model: 'RTMO-s', ms: pose },
    { name: 'Bám vết và gán vào bàn', model: 'ByteTrack', ms: track },
  ];
  const checks = e.checks.slice(-8).reverse();
  const latest = checks[0];

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Camera AI</h1>
          <p>Camera an ninh sẵn có, phân tích ngay tại quán ở 5 khung hình mỗi giây. Video gốc vẫn được đầu ghi lưu đủ khung hình.</p>
        </div>
      </div>

      <div className="split">
        <div className="flex flex-col gap-3 min-w-0">
          <CameraView cam={current} />
          <div className="cams" role="group" aria-label="Chọn camera">
            {CAMERAS.map((c) => (
              <button
                key={c.id}
                type="button"
                className="cam-btn"
                aria-pressed={c.id === current.id}
                aria-label={`${c.name}, ${c.place}`}
                onClick={() => setParams({ cam: c.id }, { replace: true })}
              >
                <CameraView cam={c} compact />
              </button>
            ))}
          </div>
        </div>

        <div className="flex flex-col gap-3 min-w-0">
          <section className="panel" aria-labelledby="pipe-title">
            <div className="panel-head">
              <h2 id="pipe-title">Luồng xử lý trên máy tại quán</h2>
              <span className="sub">Số đo mô phỏng</span>
            </div>
            <table className="table">
              <thead>
                <tr>
                  <th scope="col">Bước</th>
                  <th scope="col" className="num">
                    Mỗi khung
                  </th>
                </tr>
              </thead>
              <tbody>
                {stages.map((s) => (
                  <tr key={s.name}>
                    <td>
                      <div className="ink2">{s.name}</div>
                      <div className="tiny muted">{s.model}</div>
                    </td>
                    <td className="num">{dec(s.ms)} ms</td>
                  </tr>
                ))}
                <tr>
                  <td>
                    <div className="ink2">Tổng cộng</div>
                    <div className="tiny muted">GPU tầm RTX 4060, xử lý {live} camera cùng lúc</div>
                  </td>
                  <td className="num">{dec(total)} ms</td>
                </tr>
              </tbody>
            </table>
          </section>

          <section className="panel" aria-labelledby="vlm-title">
            <div className="panel-head">
              <h2 id="vlm-title">Mô hình thị giác xác minh</h2>
              <span className="sub">LLM đọc ảnh, chỉ gọi khi có tín hiệu</span>
            </div>
            {checks.length === 0 ? (
              <Empty title="Chưa có tín hiệu nào cần xác minh">
                <p>Khi tầng real-time thấy khách giơ tay hay ra hiệu tính tiền, đoạn clip 2 giây được gửi đi để xác minh trước khi báo nhân viên.</p>
              </Empty>
            ) : (
              <>
                <ol className="trail">
                  {checks.map((c) => (
                    <li key={c.id}>
                      <time>{clock(c.t)}</time>
                      <span className="ev">
                        Bàn {c.table}, {c.signal.toLowerCase()}:{' '}
                        <span className={c.verdict === 'confirmed' ? 'ok' : 'bad'}>{c.verdict === 'confirmed' ? 'xác nhận' : 'bác bỏ'}</span>
                        <span className="muted">. {c.note}</span>
                      </span>
                    </li>
                  ))}
                </ol>
                {latest && (
                  <div className="detail-section" style={{ borderTop: '1px solid var(--color-rule)' }}>
                    <h3 className="small muted mb-2">Kết quả gần nhất</h3>
                    <pre className="code">
                      {'{\n  '}
                      <span className="k">"table"</span>: <span className="v">{latest.table}</span>
                      {',\n  '}
                      <span className="k">"signal"</span>: <span className="v">"{latest.signal}"</span>
                      {',\n  '}
                      <span className="k">"is_request"</span>: <span className="v">{String(latest.verdict === 'confirmed')}</span>
                      {',\n  '}
                      <span className="k">"confidence"</span>: <span className="v">{latest.confidence.toFixed(2)}</span>
                      {',\n  '}
                      <span className="k">"latency_ms"</span>: <span className="v">{latest.ms}</span>
                      {',\n  '}
                      <span className="k">"camera"</span>: <span className="v">"{cameraLabel(latest.camera)}"</span>
                      {'\n}'}
                    </pre>
                  </div>
                )}
              </>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
