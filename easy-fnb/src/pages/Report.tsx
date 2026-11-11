import { Copy, Send } from 'lucide-react';
import { Stat, useToast } from '../components/ui';
import { SHIFT_START } from '../sim/engine';
import { STAFF } from '../sim/model';
import { useSim } from '../sim/store';
import { clock, dec, mmss } from '../sim/util';

function HourlyChart({ hours, now }: { hours: { h: number; guests: number }[]; now: number }) {
  const max = Math.max(1, ...hours.map((x) => x.guests));
  const W = 560;
  const H = 220;
  const pad = { l: 8, r: 8, t: 26, b: 30 };
  const bw = (W - pad.l - pad.r) / hours.length;
  return (
    <svg className="bars" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Số khách theo giờ: ${hours.map((x) => `${x.h} giờ ${x.guests} khách`).join(', ')}`}>
      <line x1={pad.l} x2={W - pad.r} y1={H - pad.b} y2={H - pad.b} />
      {hours.map((x, i) => {
        const h = ((H - pad.t - pad.b) * x.guests) / max;
        const bx = pad.l + i * bw + bw * 0.18;
        const isNow = x.h === Math.floor(now / 3600);
        return (
          <g key={x.h}>
            <rect className="bar" data-now={isNow} x={bx} y={H - pad.b - h} width={bw * 0.64} height={Math.max(h, 1)} rx={3} />
            <text className="val" x={bx + bw * 0.32} y={H - pad.b - h - 8} textAnchor="middle">
              {x.guests}
            </text>
            <text x={bx + bw * 0.32} y={H - 8} textAnchor="middle">
              {x.h}h{isNow ? ', đang diễn ra' : ''}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

export default function Report() {
  const e = useSim();
  const toast = useToast();

  const guests = e.seatings.reduce((s, x) => s + x.party, 0);
  const turns = e.seatings.length / 14;
  const med = e.medianResponse();
  const longest = [...e.meals].sort((a, b) => b.servedAt - b.orderedAt - (a.servedAt - a.orderedAt))[0];
  const longestMin = longest ? Math.round((longest.servedAt - longest.orderedAt) / 60) : 0;
  const broken = e.events.filter((ev) => ev.kind === 'broken');
  const escalations = e.events.filter((ev) => ev.kind === 'escalate');
  const balkEvents = e.events.filter((ev) => ev.kind === 'balk');

  const hours: { h: number; guests: number }[] = [];
  for (let h = SHIFT_START / 3600; h <= Math.floor(e.t / 3600); h++) {
    hours.push({ h, guests: e.seatings.filter((s) => Math.floor(s.t / 3600) === h).reduce((sum, s) => sum + s.party, 0) });
  }

  const staffRows = STAFF.map((def) => {
    const s = e.staff.find((x) => x.id === def.id)!;
    return { def, s, med: e.staffMedian(def.id) };
  });
  const withMed = staffRows.filter((r) => !Number.isNaN(r.med));
  const fastest = [...withMed].sort((a, b) => a.med - b.med)[0];
  const busiest = [...staffRows].sort((a, b) => b.s.handled - a.s.handled)[0];
  const servers = withMed.filter((r) => r.def.role === 'serve');
  const slowest = [...servers].sort((a, b) => b.med - a.med)[0];
  const fastestServer = [...servers].sort((a, b) => a.med - b.med)[0];

  const regularsToday = [...new Set(e.visits.map((v) => v.person))].map((id) => e.personName(id));

  const byHour = new Map<number, number>();
  for (const ev of balkEvents) byHour.set(Math.floor(ev.t / 3600), (byHour.get(Math.floor(ev.t / 3600)) ?? 0) + 1);
  const balkPeak = [...byHour.entries()].sort((a, b) => b[1] - a[1])[0];
  const minh = e.staff.find((s) => s.id === 'minh')!;
  const minhBreak = minh.breaks[0];

  const narrative = [
    `Ca tối tính đến ${clock(e.t, false)} đón ${guests} khách qua ${e.seatings.length} lượt ngồi bàn, mỗi bàn lật trung bình ${dec(turns)} lần. Từ lúc camera phát hiện khách cần phục vụ tới khi có nhân viên ở bàn mất trung vị ${mmss(med)}.`,
    longest
      ? `Điểm cần chú ý nhất là bàn ${longest.table} phải chờ món ${longestMin} phút, và ${e.balks} nhóm khách bỏ về ở cửa${balkPeak ? `, nhiều nhất trong khung ${balkPeak[0]} đến ${balkPeak[0] + 1} giờ` : ''}.`
      : `Có ${e.balks} nhóm khách bỏ về ở cửa.`,
    `${fastest ? `${fastest.def.name} phản hồi nhanh nhất (trung vị ${mmss(fastest.med)}), ` : ''}${busiest.def.name} xử lý nhiều việc nhất (${busiest.s.handled} việc).${regularsToday.length ? ` Khách quen đã ghé: ${regularsToday.join(', ')}.` : ''}`,
  ];

  const suggestions: string[] = [];
  if (balkPeak && balkPeak[1] >= 2) {
    suggestions.push(`Khung ${balkPeak[0]} đến ${balkPeak[0] + 1} giờ có ${balkPeak[1]} nhóm bỏ về ở cửa. Nên thêm một phục vụ trong khung này hoặc nhận đặt bàn trước qua Zalo.`);
  }
  if (longestMin >= 15) {
    suggestions.push(`Bàn ${longest!.table} chờ món ${longestMin} phút lúc ${clock(longest!.orderedAt, false)}. Nên xem lại khâu ra món của bếp trong khung giờ đó.`);
  }
  if (minhBreak && minhBreak.from >= 18 * 3600) {
    suggestions.push(`Minh nghỉ giải lao từ ${clock(minhBreak.from, false)}, trùng lúc khách bắt đầu đông. Nên dời giờ nghỉ sang trước 18:00.`);
  }
  if (slowest && fastestServer && slowest !== fastestServer && slowest.med > fastestServer.med * 1.3) {
    suggestions.push(
      `${slowest.def.name} phản hồi chậm nhất trong nhóm phục vụ (trung vị ${mmss(slowest.med)}, so với ${mmss(fastestServer.med)} của ${fastestServer.def.name}). Khu ${slowest.def.zone} có thể đang quá đông vào giờ cao điểm.`,
    );
  }
  if (regularsToday.length) {
    suggestions.push(`${regularsToday.join(', ')} đã ghé hôm nay. Có thể gửi lời cảm ơn kèm ưu đãi cho lần sau.`);
  }

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Báo cáo ca tối</h1>
          <p>
            Ngày 03/11/2026, từ {clock(SHIFT_START, false)} đến <span className="measured cool">{clock(e.t, false)}</span>
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            className="btn"
            onClick={() => {
              navigator.clipboard?.writeText(narrative.join('\n\n')).then(
                () => toast('Đã sao chép bản tóm tắt.'),
                () => toast('Không sao chép được, trình duyệt đã chặn quyền truy cập bộ nhớ tạm.'),
              );
            }}
          >
            <Copy size={16} aria-hidden="true" />
            Sao chép
          </button>
          <button type="button" className="btn btn--primary" onClick={() => toast('Bản demo không gửi thật. Bản chạy ở quán gửi báo cáo này qua Zalo cho chủ quán lúc hết ca.')}>
            <Send size={16} aria-hidden="true" />
            Gửi qua Zalo
          </button>
        </div>
      </div>

      <section className="panel" aria-labelledby="sum-title">
        <div className="panel-head">
          <h2 id="sum-title">Tóm tắt ca</h2>
          <span className="sub">Viết tự động từ nhật ký sự kiện của camera</span>
        </div>
        <div className="narrative">
          {narrative.map((p) => (
            <p key={p}>{p}</p>
          ))}
        </div>
      </section>

      <section className="panels figs" aria-label="Số liệu ca">
        <Stat label="Lượt khách" value={guests} sub={`${e.seatings.length} lượt ngồi bàn`} />
        <Stat label="Lật bàn trung bình" value={`${dec(turns)} lần`} sub="trên 14 bàn" />
        <Stat label="Phản hồi trung vị" value={mmss(med)} sub="từ phát hiện tới khi nhân viên có mặt" />
        <Stat label="Món chờ lâu nhất" value={longest ? `${longestMin} phút` : 'chưa có'} sub={longest ? `bàn ${longest.table}, gọi lúc ${clock(longest.orderedAt, false)}` : undefined} />
        <Stat label="Khách bỏ về ở cửa" value={`${e.balks} nhóm`} sub="đứng chờ rồi rời đi" />
        <Stat label="Sự cố" value={broken.length + escalations.length} sub={`${broken.length} đồ vỡ, ${escalations.length} lần báo quản lý`} />
      </section>

      <div className="split">
        <section className="panel" aria-labelledby="chart-title">
          <div className="panel-head">
            <h2 id="chart-title">Khách theo giờ</h2>
            <span className="sub">Tính theo lượt ngồi bàn</span>
          </div>
          <div className="panel-body">
            <HourlyChart hours={hours} now={e.t} />
          </div>
        </section>
        <section className="panel" aria-labelledby="tips-title">
          <div className="panel-head">
            <h2 id="tips-title">Gợi ý cho ca sau</h2>
          </div>
          <ol className="suggest-list small">
            {suggestions.length ? suggestions.map((s) => <li key={s}>{s}</li>) : <li>Ca này chưa có điểm nào cần điều chỉnh.</li>}
          </ol>
        </section>
      </div>

      <section className="panel" aria-labelledby="team-title">
        <div className="panel-head">
          <h2 id="team-title">Nhân viên</h2>
        </div>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th scope="col">Nhân viên</th>
                <th scope="col" className="num">
                  Vào ca
                </th>
                <th scope="col" className="num">
                  Việc đã xử lý
                </th>
                <th scope="col" className="num">
                  Phản hồi trung vị
                </th>
                <th scope="col">Ghi chú</th>
              </tr>
            </thead>
            <tbody>
              {staffRows.map(({ def, s, med: m }) => (
                <tr key={def.id}>
                  <td className="ink2">{def.name}</td>
                  <td className="num">{clock(def.clockIn, false)}</td>
                  <td className="num">{s.handled}</td>
                  <td className="num">{Number.isNaN(m) ? 'chưa có' : mmss(m)}</td>
                  <td>
                    {def.id === fastest?.def.id
                      ? 'Phản hồi nhanh nhất ca'
                      : def.id === busiest.def.id
                        ? 'Xử lý nhiều việc nhất ca'
                        : s.breaks.length
                          ? `Nghỉ giải lao ${s.breaks.map((b) => `${clock(b.from, false)} đến ${b.to ? clock(b.to, false) : 'bây giờ'}`).join(', ')}`
                          : ''}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
