import type { Engine, SimEvent } from './engine';
import { SHIFT_START } from './engine';
import { STAFF, ZONE_CAMERA, prior, tableDef } from './model';
import { clock, durText, fold, median, mmss } from './util';

/**
 * Trợ lý cho chủ quán. Bản demo trả lời bằng cách tra thẳng nhật ký sự kiện của bộ mô phỏng;
 * bản thật là agent Google ADK gọi các tool tương tự trên Postgres và pgvector.
 */

export interface Clip {
  id: string;
  t: number;
  camera: string;
  table?: number;
  title: string;
}

export type Seg = string | { clip: Clip };

export interface Answer {
  paragraphs: Seg[][];
  tools: string[];
  clips: Clip[];
  link?: { to: string; label: string };
}

interface Moment {
  t: number;
  camera: string;
  table?: number;
}

const HONORIFICS = new Set(['anh', 'chi', 'em', 'co', 'chu', 'ong', 'ba', 'nguoi']);

function hasWord(text: string, word: string) {
  return new RegExp(`(^|[^\\p{L}\\p{N}])${word}([^\\p{L}\\p{N}]|$)`, 'u').test(text);
}

export const SUGGESTIONS = [
  'Anh John đến lúc mấy giờ, ngồi bàn nào?',
  'Hôm nay bàn nào phải chờ món lâu nhất?',
  'Ai làm vỡ bát chiều nay?',
  'Có bao nhiêu khách bỏ về ở cửa?',
  'Lan đã xử lý bao nhiêu việc trong ca?',
  'Tóm tắt ca tối đến giờ',
];

export function answer(e: Engine, question: string): Answer {
  const q = fold(question);
  const lower = question.toLowerCase();
  const clips: Clip[] = [];
  const tools: string[] = [];
  const cite = (m: Moment, title: string): Seg => {
    const clip: Clip = { id: `${m.camera}-${Math.round(m.t)}-${clips.length}`, t: m.t, camera: m.camera, table: m.table, title };
    clips.push(clip);
    return { clip };
  };
  const tableCam = (table: number) => ZONE_CAMERA[tableDef(table).zone];
  const done = (paragraphs: Seg[][], link?: Answer['link']): Answer => ({ paragraphs, tools, clips, link });

  // 1. Khách quen
  for (const p of e.people) {
    const name = p.name ?? '';
    const keys = fold(name)
      .split(/\s+/)
      .filter((w) => w && !HONORIFICS.has(w));
    const numbered = hasWord(q, `nguoi #?${p.id.slice(1)}`);
    const hit = keys.some((k) => hasWord(q, k) && !(k === 'mai' && q.includes('ngay mai'))) || numbered;
    if (!hit) continue;
    const label = e.personName(p.id);
    tools.push(`resolve_entities("${question.trim().slice(0, 40)}") → person:${p.id}`);
    tools.push(`person_timeline(person:${p.id}, hôm nay)`);
    const visits = e.visits.filter((v) => v.person === p.id);
    const last = visits[visits.length - 1];
    if (!last) {
      const past = p.past[0];
      return done([
        [`Hôm nay camera chưa thấy ${label}.`],
        past
          ? [`Lần gần nhất là ngày ${past.date} lúc ${past.time}, ngồi bàn ${past.table}, đi ${past.party} người. Tổng cộng đã ghé ${p.visits} lần.`]
          : [`Tổng cộng đã ghé ${p.visits} lần.`],
      ]);
    }
    const cam = tableCam(last.table);
    tools.push(`get_clip(cam1, ${clock(last.arrived - 10)} đến ${clock(last.arrived + 10)})`);
    const first: Seg[] = [
      `${label} vào quán lúc `,
      cite({ t: last.arrived, camera: 'cam1' }, `${label} vào quán`),
      `, đi ${last.party} người và ngồi bàn ${last.table}.`,
    ];
    const greet = e.tasks.find((k) => k.kind === 'greet' && k.table === last.table && k.person === p.id && k.created >= last.arrived - 1);
    if (greet?.arrivedAt && greet.assignee) {
      first.push(
        ` ${e.staffName(greet.assignee)} tới chào sau ${durText(greet.arrivedAt - greet.created)} `,
        cite({ t: greet.arrivedAt, camera: cam, table: last.table }, `${e.staffName(greet.assignee)} chào bàn ${last.table}`),
        '.',
      );
    }
    if (last.left) {
      first.push(` ${label} rời quán lúc `, cite({ t: last.left, camera: cam, table: last.table }, `${label} rời bàn`), `, ở lại ${durText(last.left - last.arrived)}.`);
    } else {
      first.push(` Hiện vẫn đang ngồi ở bàn ${last.table}.`);
    }
    const second: Seg[] = [`Đây là lần ghé thứ ${p.visits}.${p.note ? ` Ghi chú của quán: ${p.note}.` : ''}`];
    return done([first, second], { to: `/khach-quen?nguoi=${p.id}`, label: `Mở hồ sơ ${label}` });
  }

  // 2. Đồ vỡ
  if (q.includes('do vo') || (hasWord(q, 'vo') && /bat|dia|ly|coc|do/.test(q))) {
    tools.push('query_events(loại=đồ vỡ, hôm nay)');
    const broken = e.events.filter((ev) => ev.kind === 'broken');
    if (!broken.length) return done([['Hôm nay camera chưa ghi nhận đồ vỡ nào.']]);
    const paragraphs: Seg[][] = [];
    for (const ev of broken.slice(-3)) {
      const table = ev.table ?? 0;
      tools.push(`inspect_clip_with_vlm(${ev.camera}, ${clock(ev.t - 15)} đến ${clock(ev.t)})`);
      paragraphs.push([`${cameraLabel(ev.camera)} phát hiện đồ vỡ dưới bàn ${table} lúc `, cite(ev, `Đồ vỡ dưới bàn ${table}`), '.']);
      if (table === 9 && ev.t < e.t - 600) {
        paragraphs.push([
          'Mô hình thị giác xem lại 15 giây trước mốc đó: một khách ngồi ghế phía cửa sổ của bàn 9 vô tình gạt tay làm bát rơi khi đang rót nước. Không thấy ai bị thương.',
        ]);
      } else {
        paragraphs.push(['Khoảnh khắc rơi nằm trong 15 giây trước mốc này. Bấm vào mốc giờ để xem lại đoạn clip gốc.']);
      }
      const k = e.tasks.find((x) => x.kind === 'broken' && x.table === table && x.created >= ev.t - 1);
      if (k?.arrivedAt && k.assignee) {
        paragraphs.push([
          `${e.staffName(k.assignee)} được giao dọn và tới sau ${durText(k.arrivedAt - k.created)} `,
          cite({ t: k.arrivedAt, camera: ev.camera, table }, `${e.staffName(k.assignee)} dọn đồ vỡ`),
          '.',
        ]);
      }
    }
    return done(paragraphs);
  }

  // 3. Khách bỏ về ở cửa
  if (q.includes('bo ve') || q.includes('roi di') || (q.includes('cua') && q.includes('khach'))) {
    tools.push(`query_events(loại=khách bỏ về, từ ${clock(SHIFT_START, false)})`);
    const balks = e.events.filter((ev) => ev.kind === 'balk');
    if (!balks.length) return done([[`Từ ${clock(SHIFT_START, false)} chưa có nhóm khách nào bỏ về ở cửa.`]]);
    const list: Seg[] = [`Từ ${clock(SHIFT_START, false)} có ${balks.length} nhóm khách bỏ về ở cửa, lúc `];
    balks.slice(-5).forEach((ev, i, arr) => {
      list.push(cite(ev, 'Khách bỏ về ở cửa'));
      list.push(i < arr.length - 1 ? ', ' : '.');
    });
    const byHour = new Map<number, number>();
    for (const ev of balks) byHour.set(Math.floor(ev.t / 3600), (byHour.get(Math.floor(ev.t / 3600)) ?? 0) + 1);
    const peak = [...byHour.entries()].sort((a, b) => b[1] - a[1])[0];
    return done([
      list,
      [`Nhiều nhất là khung ${peak[0]} đến ${peak[0] + 1} giờ (${peak[1]} nhóm), lúc các bàn 4 người đều đã có khách. Có thể nhận đặt bàn trước hoặc báo thời gian chờ ước tính ngay ở cửa.`],
    ]);
  }

  // 4. Chờ món lâu
  if ((q.includes('cho') && (q.includes('mon') || q.includes('lau'))) || q.includes('cham')) {
    tools.push('query_events(loại=gọi món, món lên bàn, hôm nay)', 'wait_time_report(giai đoạn=chờ món)');
    const meals = [...e.meals].sort((a, b) => b.servedAt - b.orderedAt - (a.servedAt - a.orderedAt));
    if (!meals.length) return done([['Chưa có bàn nào được lên món trong ca này.']]);
    const top = meals[0];
    const wait = top.servedAt - top.orderedAt;
    const usual = prior('waiting_food', top.party);
    const cam = tableCam(top.table);
    const paragraphs: Seg[][] = [
      [
        `Lâu nhất là bàn ${top.table}: gọi món lúc `,
        cite({ t: top.orderedAt, camera: cam, table: top.table }, `Bàn ${top.table} gọi món`),
        ', món lên lúc ',
        cite({ t: top.servedAt, camera: cam, table: top.table }, `Món lên bàn ${top.table}`),
        `, chờ ${durText(wait)}. Thường lệ cho nhóm ${top.party} người là khoảng ${Math.round(usual / 60)} phút.`,
      ],
    ];
    const next = meals.slice(1, 3);
    if (next.length) {
      paragraphs.push([
        `Tiếp theo là ${next.map((m) => `bàn ${m.table} (${Math.round((m.servedAt - m.orderedAt) / 60)} phút)`).join(' và ')}.`,
      ]);
    }
    const waitingNow = e.tables.filter((tb) => tb.phase === 'waiting_food').sort((a, b) => (a.orderedAt ?? 0) - (b.orderedAt ?? 0));
    if (waitingNow[0]) {
      const w = waitingNow[0];
      paragraphs.push([`Hiện bàn ${w.id} đang chờ món được ${durText(e.t - (w.orderedAt ?? e.t))}.`]);
    }
    return done(paragraphs);
  }

  // 5. Nhân viên
  for (const s of STAFF) {
    if (!hasWord(lower, s.name.toLowerCase())) continue;
    const st = e.staff.find((x) => x.id === s.id)!;
    tools.push(`person_timeline(staff:${s.id}, hôm nay)`, `query_events(nhân viên=${s.name})`);
    const clockIn = e.events.find((ev) => ev.kind === 'clock' && ev.staff === s.id);
    const first: Seg[] = [`${s.name} vào ca lúc `];
    first.push(clockIn ? cite(clockIn, `${s.name} vào ca`) : clock(s.clockIn), ', chấm công tự động ở Cam 1.');
    const med = median(st.responses);
    const second: Seg[] = [
      `Đến giờ ${s.name} đã xử lý ${st.handled} việc. Thời gian từ lúc hệ thống giao việc tới khi ${s.name} có mặt ở bàn có trung vị ${Number.isNaN(med) ? 'chưa đủ dữ liệu' : mmss(med)}.`,
    ];
    const br = st.breaks;
    const third: Seg[] = [
      br.length
        ? `Đã nghỉ giải lao ${br.length} lần: ${br.map((b) => `${clock(b.from, false)} đến ${b.to ? clock(b.to, false) : 'bây giờ'}`).join(', ')}.`
        : 'Chưa nghỉ giải lao lần nào.',
    ];
    return done([first, second, third], { to: `/nhan-vien?nv=${s.id}`, label: `Xem ${s.name} trong trang nhân viên` });
  }

  // 6. Một bàn cụ thể
  const tableMatch = q.match(/ban\s*(\d{1,2})/);
  if (tableMatch) {
    const id = Number(tableMatch[1]);
    if (id >= 1 && id <= 14) {
      tools.push(`table_timeline(bàn ${id}, hôm nay)`);
      const seats = e.seatings.filter((s) => s.table === id);
      const cam = tableCam(id);
      const list: Seg[] = [`Từ ${clock(SHIFT_START, false)} bàn ${id} đã đón ${seats.length} lượt khách`];
      if (seats.length) {
        list.push(': ');
        seats.slice(-4).forEach((s, i, arr) => {
          list.push(cite({ t: s.t, camera: cam, table: id }, `Khách ngồi bàn ${id}`), ` (${s.party} người)`);
          list.push(i < arr.length - 1 ? ', ' : '.');
        });
      } else list.push('.');
      const tb = e.table(id);
      return done([list, [tb.phase === 'empty' ? `Hiện bàn ${id} đang trống.` : `Hiện tại: ${tb.reason.charAt(0).toLowerCase()}${tb.reason.slice(1)}, điểm khẩn cấp ${tb.urgency}.`]], {
        to: `/?ban=${id}`,
        label: `Mở bàn ${id} trên sơ đồ`,
      });
    }
  }

  // 7. Tóm tắt
  if (q.includes('tom tat') || q.includes('bao cao') || q.includes('ca toi')) {
    tools.push('shift_metrics(từ 17:00)', 'query_events(mức=quan trọng)');
    const guests = e.seatings.reduce((s, x) => s + x.party, 0);
    const med = e.medianResponse();
    const longest = [...e.meals].sort((a, b) => b.servedAt - b.orderedAt - (a.servedAt - a.orderedAt))[0];
    const p: Seg[][] = [
      [`Từ ${clock(SHIFT_START, false)} đến ${clock(e.t, false)}, quán đón ${guests} khách qua ${e.seatings.length} lượt ngồi bàn. Thời gian từ lúc camera phát hiện tới khi nhân viên có mặt có trung vị ${mmss(med)}.`],
    ];
    if (longest) {
      p.push([
        `Điểm cần chú ý: bàn ${longest.table} chờ món ${Math.round((longest.servedAt - longest.orderedAt) / 60)} phút, món lên lúc `,
        cite({ t: longest.servedAt, camera: tableCam(longest.table), table: longest.table }, `Món lên bàn ${longest.table}`),
        `, và ${e.balks} nhóm khách bỏ về ở cửa.`,
      ]);
    }
    return done(p, { to: '/bao-cao', label: 'Mở báo cáo ca đầy đủ' });
  }

  // 8. Tìm theo từ khóa trong mô tả cảnh
  tools.push(`semantic_scene_search("${question.trim().slice(0, 48)}")`);
  const words = q.split(/[^a-z0-9]+/).filter((w) => w.length >= 3);
  const scored: { ev: SimEvent; n: number }[] = [];
  if (words.length) {
    for (const ev of e.events) {
      const text = fold(`${ev.who ?? ''} ${ev.text}`);
      const n = words.filter((w) => hasWord(text, w)).length;
      if (n) scored.push({ ev, n });
    }
  }
  scored.sort((a, b) => b.n - a.n || b.ev.t - a.ev.t);
  const hits = scored.slice(0, 4);
  if (!hits.length) {
    return done([
      ['Mình không tìm thấy bằng chứng nào trong nhật ký camera cho câu hỏi này.'],
      ['Bạn thử hỏi về một bàn, một nhân viên hoặc một khách quen cụ thể, ví dụ "Bàn 7 tối nay thế nào?".'],
    ]);
  }
  return done([
    ['Mình tìm thấy các khoảnh khắc liên quan nhất:'],
    ...hits.map(({ ev }) => [cite(ev, ev.who ? `${ev.who} ${ev.text}` : ev.text), ` ${ev.who ? `${ev.who} ` : ''}${ev.text}.`]),
  ]);
}

export function cameraLabel(id: string) {
  return `Cam ${id.replace('cam', '')}`;
}
