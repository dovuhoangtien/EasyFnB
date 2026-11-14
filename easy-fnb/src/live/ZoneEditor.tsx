import { useEffect, useMemo, useRef, useState, type ChangeEvent, type MouseEvent as ReactMouseEvent, type PointerEvent as ReactPointerEvent } from 'react';
import { Camera as CameraIcon, Film, ListOrdered, RefreshCw, Save, ScanSearch, Trash, Undo2 } from 'lucide-react';
import { putZones, snapshotUrl, suggestZones } from './api';
import { useRun } from './hooks';
import { live, useLive } from './store';
import { AREA_LABEL, byName } from './text';
import { AREA_TYPES, type Area, type AreaType, type CameraZones, type Point } from './types';

interface Size {
  w: number;
  h: number;
}

interface EditTable {
  key: number;
  /** tên bàn; với vùng khác thì là mã vùng (quay, kho2...) */
  id: string;
  polygon: Point[];
  /** 'table' là bàn như cũ; còn lại là vùng quầy, kho, giữ xe, cửa */
  type: ShapeType;
  /** tên hiện cho vùng không phải bàn */
  name?: string;
}

type ShapeType = 'table' | AreaType;
const SHAPE_LABEL: Record<ShapeType, string> = { table: 'Bàn', ...AREA_LABEL };
const isTable = (t: EditTable) => t.type === 'table';

/** Mã vùng mới: quay, quay2, quay3... */
function nextAreaId(list: EditTable[], type: AreaType) {
  const used = new Set(list.map((t) => t.id));
  if (!used.has(type)) return type;
  let n = 2;
  while (used.has(`${type}${n}`)) n++;
  return `${type}${n}`;
}

interface Bg extends Size {
  src: string;
}

const DEFAULT_SPACE: Size = { w: 1280, h: 720 };
let nextKey = 1000;

function scaleTables(list: EditTable[], from: Size, to: Size): EditTable[] {
  if (from.w === to.w && from.h === to.h) return list;
  const sx = to.w / from.w;
  const sy = to.h / from.h;
  return list.map((t) => ({ ...t, polygon: t.polygon.map(([x, y]) => [x * sx, y * sy] as Point) }));
}

/** Tên bàn mới: B1, B2... số nhỏ nhất chưa dùng */
function nextName(list: EditTable[]) {
  const used = new Set(list.map((t) => t.id.trim().toUpperCase()));
  let n = 1;
  while (used.has(`B${n}`)) n++;
  return `B${n}`;
}

type Box = [number, number, number, number];

const boxOf = (poly: Point[]): Box => {
  const xs = poly.map((p) => p[0]);
  const ys = poly.map((p) => p[1]);
  return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
};

/** Phần chung so với khung nhỏ hơn: hai bàn trùng nhau cho gần 1 */
function overlap(a: Box, b: Box) {
  const w = Math.min(a[2], b[2]) - Math.max(a[0], b[0]);
  const h = Math.min(a[3], b[3]) - Math.max(a[1], b[1]);
  if (w <= 0 || h <= 0) return 0;
  return (w * h) / Math.min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]));
}

/** Thứ tự đọc: trên xuống dưới, trái sang phải; lệch nhau dưới 12% chiều cao coi như cùng hàng */
function readingOrder(list: EditTable[], h: number): EditTable[] {
  const mid = (t: EditTable) => {
    const b = boxOf(t.polygon);
    return [(b[0] + b[2]) / 2, (b[1] + b[3]) / 2];
  };
  const rows: EditTable[][] = [];
  for (const t of [...list].sort((a, b) => mid(a)[1] - mid(b)[1])) {
    const row = rows[rows.length - 1];
    if (row && mid(t)[1] - mid(row[0])[1] < 0.12 * h) row.push(t);
    else rows.push([t]);
  }
  return rows.flatMap((row) => row.sort((a, b) => mid(a)[0] - mid(b)[0]));
}

type Drag =
  | { kind: 'corner'; key: number; idx: number; moved: boolean }
  | { kind: 'move'; key: number; last: Point; moved: boolean }
  | { kind: 'box'; start: Point; moved: boolean };

const isTyping = (el: EventTarget | null) =>
  el instanceof HTMLElement && (el.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(el.tagName));

/** Ảnh nền để vẽ: chụp từ camera, hoặc lấy một khung từ video/ảnh trên máy */
function useBackground(camera: string) {
  const [mode, setMode] = useState<'snapshot' | 'file'>('snapshot');
  const [bust, setBust] = useState(() => Date.now());
  const [bg, setBg] = useState<Bg | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [video, setVideo] = useState<{ src: string; duration: number; t: number } | null>(null);
  const objectUrls = useRef<string[]>([]);

  const track = (url: string) => {
    objectUrls.current.push(url);
    return url;
  };

  useEffect(
    () => () => {
      objectUrls.current.forEach((u) => URL.revokeObjectURL(u));
    },
    [],
  );

  // Ảnh chụp thô (không vẽ chồng) từ camera
  useEffect(() => {
    if (mode !== 'snapshot') return;
    let alive = true;
    const img = new Image();
    const src = snapshotUrl(camera, bust);
    img.onload = () => {
      if (!alive) return;
      setBg({ src, w: img.naturalWidth, h: img.naturalHeight });
      setNote(null);
    };
    img.onerror = () => {
      if (!alive) return;
      setBg(null);
      setNote('Chưa có ảnh chụp từ camera này. Hãy chạy máy camera, hoặc chọn một video hay ảnh chụp từ đúng góc camera trên máy.');
    };
    img.src = src;
    return () => {
      alive = false;
    };
  }, [camera, bust, mode]);

  const pickFile = (ev: ChangeEvent<HTMLInputElement>) => {
    const file = ev.target.files?.[0];
    ev.target.value = '';
    if (!file) return;
    const url = track(URL.createObjectURL(file));
    if (file.type.startsWith('image/')) {
      setVideo(null);
      const img = new Image();
      img.onload = () => {
        setBg({ src: url, w: img.naturalWidth, h: img.naturalHeight });
        setNote(null);
      };
      img.onerror = () => setNote('Không mở được ảnh này.');
      img.src = url;
    } else {
      setVideo({ src: url, duration: 0, t: 0 });
      setNote('Đang mở video…');
    }
  };

  const grab = (el: HTMLVideoElement) => {
    if (!el.videoWidth) return;
    const canvas = document.createElement('canvas');
    canvas.width = el.videoWidth;
    canvas.height = el.videoHeight;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.drawImage(el, 0, 0);
    canvas.toBlob(
      (blob) => {
        if (!blob) return;
        setBg({ src: track(URL.createObjectURL(blob)), w: canvas.width, h: canvas.height });
        setNote(null);
      },
      'image/jpeg',
      0.9,
    );
  };

  return {
    mode,
    setMode,
    bg,
    note,
    video,
    setVideo,
    setNote,
    refresh: () => setBust(Date.now()),
    pickFile,
    grab,
  };
}

/** Trình vẽ vùng bàn cho một camera */
function ZoneCanvas({ camera, stored, autoFind }: { camera: string; stored: CameraZones | undefined; autoFind?: boolean }) {
  const back = useBackground(camera);
  const { busy, run } = useRun();
  const [edit, setEdit] = useState<{ space: Size; tables: EditTable[] } | null>(null);
  const [draft, setDraft] = useState<Point[]>([]);
  const [hover, setHover] = useState<Point | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [tool, setTool] = useState<'box' | 'points'>('box');
  const [shape, setShape] = useState<ShapeType>('table');
  const [box, setBox] = useState<[Point, Point] | null>(null);
  const [found, setFound] = useState<number | null>(null);
  const [px, setPx] = useState(800);
  const stageRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const drag = useRef<Drag | null>(null);
  const justDragged = useRef(false);

  const storedSpace: Size | null = stored && stored.frame_w > 0 && stored.frame_h > 0 ? { w: stored.frame_w, h: stored.frame_h } : null;
  const space: Size = back.bg ?? storedSpace ?? DEFAULT_SPACE;

  const sw = space.w;
  const sh = space.h;
  // Bàn đang hiện, quy về toạ độ của hình nền hiện tại
  const view = useMemo<EditTable[]>(() => {
    const to = { w: sw, h: sh };
    if (edit) return scaleTables(edit.tables, edit.space, to);
    if (!stored || !(stored.frame_w > 0 && stored.frame_h > 0)) return [];
    const list: EditTable[] = [
      ...stored.tables.map((t, i) => ({ key: i, id: t.id, polygon: t.polygon, type: 'table' as const })),
      ...(stored.areas ?? [])
        .filter((a) => AREA_TYPES.includes(a.type))
        .map((a, i) => ({ key: 500 + i, id: a.id, polygon: a.polygon, type: a.type, name: a.name ?? AREA_LABEL[a.type] })),
    ];
    return scaleTables(list, { w: stored.frame_w, h: stored.frame_h }, to);
  }, [edit, stored, sw, sh]);

  const dirty = edit !== null;
  const drawing = draft.length > 0;
  const k = space.w / Math.max(1, px); // đơn vị ảnh trên mỗi điểm ảnh màn hình

  // Đo bề rộng hình đang hiện để vẽ điểm tròn và chữ đúng cỡ
  useEffect(() => {
    const el = stageRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setPx(el.clientWidth || 800));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const commit = (tables: EditTable[]) => setEdit({ space, tables });

  /** Hình mới theo loại đang chọn: bàn đặt tên B1, B2...; vùng khác lấy tên theo loại */
  const newShape = (list: EditTable[], polygon: Point[]): EditTable =>
    shape === 'table'
      ? { key: nextKey++, id: nextName(list), polygon, type: 'table' }
      : { key: nextKey++, id: nextAreaId(list, shape), polygon, type: shape, name: AREA_LABEL[shape] };

  const closeDraft = () => {
    if (draft.length < 3) return;
    const t = newShape(view, draft);
    commit([...view, t]);
    setDraft([]);
    setHover(null);
    setSelected(t.key);
  };

  const removeTable = (key: number) => {
    commit(view.filter((t) => t.key !== key));
    if (selected === key) setSelected(null);
  };

  // Camera chỉ tìm được bàn trên chính hình nó đang quay, không phải trên video hay ảnh chọn từ máy
  const fromCamera = back.mode === 'snapshot' && back.bg !== null;

  /** Bàn camera tìm được, quy về toạ độ đang vẽ */
  const fit = (poly: Point[], from: Size, to: Size) => poly.map(([x, y]) => [(x * to.w) / from.w, (y * to.h) / from.h] as Point);

  const findTables = async () => {
    const out = await run('find', () => suggestZones({ camera, frame_w: space.w, frame_h: space.h }));
    if (!out) return;
    const list = [...view];
    for (const f of out.tables) {
      const polygon = fit(f.polygon, { w: out.frame_w, h: out.frame_h }, space);
      if (list.some((t) => isTable(t) && overlap(boxOf(t.polygon), boxOf(polygon)) > 0.4)) continue;
      list.push({ key: nextKey++, id: nextName(list), polygon, type: 'table' });
    }
    if (list.length > view.length) commit(list);
    setFound(list.length - view.length);
  };

  // mở từ nút "Tự tìm bàn" trên màn hình chính: tìm luôn một lần khi đã có hình camera
  const autoDone = useRef(false);
  useEffect(() => {
    if (!autoFind || autoDone.current || !fromCamera || busy !== null) return;
    autoDone.current = true;
    void findTables();
  });

  /** Khoanh thô một vùng: thêm bàn ngay theo khung vừa kéo, rồi để camera ôm sát bàn nằm trong đó */
  const addBox = (a: Point, b: Point) => {
    const [x1, y1, x2, y2] = [Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.max(a[0], b[0]), Math.max(a[1], b[1])];
    const rough: Point[] = [[x1, y1], [x2, y1], [x2, y2], [x1, y2]];
    const t = newShape(view, rough);
    commit([...view, t]);
    setSelected(t.key);
    setFound(null);
    // camera chỉ biết ôm sát bàn; quầy, kho, cửa giữ đúng khung vừa kéo
    if (!fromCamera || !isTable(t)) return;
    suggestZones({ camera, frame_w: space.w, frame_h: space.h, box: [x1, y1, x2, y2] })
      .then((out) => {
        const hit = out.tables[0];
        if (!hit) return;
        // chỉ ôm sát khi chủ quán chưa tự chỉnh bàn này trong lúc chờ
        setEdit((cur) => cur && { ...cur, tables: cur.tables.map((q) => (q.key === t.key && q.polygon === rough ? { ...q, polygon: fit(hit.polygon, { w: out.frame_w, h: out.frame_h }, cur.space) } : q)) });
      })
      .catch(() => undefined);
  };

  const renumber = () => {
    const order = readingOrder(view.filter(isTable), space.h);
    commit(view.map((t) => (isTable(t) ? { ...t, id: `B${order.indexOf(t) + 1}` } : t)));
  };

  const focusName = (key: number) => {
    const el = document.getElementById(`zn-${key}`);
    if (el instanceof HTMLInputElement) {
      el.focus();
      el.select();
    }
  };

  const rename = (key: number, id: string) => commit(view.map((t) => (t.key === key ? (isTable(t) ? { ...t, id } : { ...t, name: id }) : t)));

  // Phím tắt: Enter khép vùng, Backspace xoá điểm vừa chấm, Esc huỷ
  useEffect(() => {
    const onKey = (ev: KeyboardEvent) => {
      if (isTyping(ev.target)) return;
      if (ev.key === 'Enter' && draft.length >= 3) {
        ev.preventDefault();
        closeDraft();
      } else if (ev.key === 'Backspace' && draft.length) {
        ev.preventDefault();
        setDraft((d) => d.slice(0, -1));
      } else if (ev.key === 'Escape') {
        if (draft.length) setDraft([]);
        else setSelected(null);
      } else if (ev.key === 'Delete' && selected !== null && !draft.length) {
        removeTable(selected);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  });

  const toPoint = (ev: { clientX: number; clientY: number }): Point | null => {
    const svg = svgRef.current;
    const ctm = svg?.getScreenCTM();
    if (!svg || !ctm) return null;
    const p = new DOMPoint(ev.clientX, ev.clientY).matrixTransform(ctm.inverse());
    return [Math.min(space.w, Math.max(0, p.x)), Math.min(space.h, Math.max(0, p.y))];
  };

  const onStageClick = (ev: ReactMouseEvent<SVGSVGElement>) => {
    if (justDragged.current) {
      justDragged.current = false;
      return;
    }
    if (tool === 'box') {
      setSelected(null);
      return;
    }
    const p = toPoint(ev);
    if (!p) return;
    if (draft.length >= 3) {
      const [fx, fy] = draft[0];
      if (Math.hypot(p[0] - fx, p[1] - fy) < 12 * k) {
        closeDraft();
        return;
      }
    }
    setSelected(null);
    setDraft((d) => [...d, p]);
  };

  const onMove = (ev: ReactPointerEvent<SVGSVGElement>) => {
    const d = drag.current;
    if (d) {
      const p = toPoint(ev);
      if (!p) return;
      if (d.kind === 'box') {
        d.moved = true;
        setBox([d.start, p]);
      } else if (d.kind === 'corner') {
        d.moved = true;
        commit(view.map((t) => (t.key === d.key ? { ...t, polygon: t.polygon.map((q, i) => (i === d.idx ? p : q)) } : t)));
      } else {
        const [dx, dy] = [p[0] - d.last[0], p[1] - d.last[1]];
        if (!d.moved && Math.hypot(dx, dy) < 4 * k) return; // bấm chọn chứ chưa kéo
        d.moved = true;
        d.last = p;
        commit(view.map((t) => (t.key === d.key ? { ...t, polygon: t.polygon.map(([x, y]) => [x + dx, y + dy] as Point) } : t)));
      }
      return;
    }
    if (draft.length) setHover(toPoint(ev));
  };

  /** Kéo trên nền hình (không trúng bàn nào) khi đang ở chế độ khoanh vùng */
  const startBox = (ev: ReactPointerEvent<SVGSVGElement>) => {
    if (tool !== 'box' || ev.button !== 0) return;
    const p = toPoint(ev);
    if (!p) return;
    ev.currentTarget.setPointerCapture(ev.pointerId);
    drag.current = { kind: 'box', start: p, moved: false };
  };

  const startMove = (ev: ReactPointerEvent<SVGPolygonElement>, key: number) => {
    if (drawing || ev.button !== 0) return;
    const p = toPoint(ev);
    if (!p) return;
    ev.stopPropagation();
    ev.currentTarget.setPointerCapture(ev.pointerId);
    setSelected(key);
    drag.current = { kind: 'move', key, last: p, moved: false };
  };

  const startDrag = (ev: ReactPointerEvent<SVGCircleElement>, key: number, idx: number) => {
    ev.stopPropagation();
    ev.currentTarget.setPointerCapture(ev.pointerId);
    drag.current = { kind: 'corner', key, idx, moved: false };
  };

  const endDrag = (ev: ReactPointerEvent<SVGSVGElement>) => {
    const d = drag.current;
    drag.current = null;
    if (!d) return;
    if (d.moved) justDragged.current = true;
    if (d.kind !== 'box') return;
    setBox(null);
    const p = toPoint(ev);
    if (p && Math.abs(p[0] - d.start[0]) > 14 * k && Math.abs(p[1] - d.start[1]) > 14 * k) addBox(d.start, p);
  };

  const problems = useMemo(() => {
    const out: string[] = [];
    const names = view.filter(isTable).map((t) => t.id.trim());
    if (names.some((n) => !n)) out.push('Có bàn chưa có tên.');
    const dup = names.filter((n, i) => n && names.indexOf(n) !== i);
    if (dup.length) out.push(`Tên bàn bị trùng: ${[...new Set(dup)].join(', ')}.`);
    return out;
  }, [view]);

  const save = async () => {
    const round = (poly: Point[]) => poly.map(([x, y]) => [Math.round(x), Math.round(y)] as Point);
    const areas: Area[] = view
      .filter((t) => !isTable(t))
      .map((t) => ({ id: t.id, type: t.type as AreaType, name: t.name?.trim() || AREA_LABEL[t.type as AreaType], polygon: round(t.polygon) }));
    const body: CameraZones = {
      camera,
      frame_w: Math.round(space.w),
      frame_h: Math.round(space.h),
      tables: view.filter(isTable).map((t) => ({ id: t.id.trim(), polygon: round(t.polygon) })),
      areas,
    };
    const out = await run('save', () => putZones(body), `Đã lưu ${body.tables.length} bàn${areas.length ? `, ${areas.length} khu vực` : ''} cho ${camera}`);
    if (out) {
      live.upsertZones({ ...out, areas: out.areas ?? areas });
      setEdit(null);
    }
  };

  // bàn trước, rồi tới quầy, kho, giữ xe, cửa
  const sorted = [...view].sort((a, b) => Number(!isTable(a)) - Number(!isTable(b)) || byName(a.id, b.id));
  const r = 6 * k;

  return (
    <div className="zone-editor">
      <div className="zone-toolbar">
        <div className="seg seg--icons" role="group" aria-label="Nguồn hình nền">
          <button type="button" aria-pressed={back.mode === 'snapshot'} onClick={() => back.setMode('snapshot')}>
            <CameraIcon size={14} aria-hidden="true" />
            Ảnh từ camera
          </button>
          <button type="button" aria-pressed={back.mode === 'file'} onClick={() => back.setMode('file')}>
            <Film size={14} aria-hidden="true" />
            Video hoặc ảnh trên máy
          </button>
        </div>
        <div className="seg" role="group" aria-label="Loại vùng sẽ vẽ">
          {(['table', ...AREA_TYPES] as ShapeType[]).map((k) => (
            <button key={k} type="button" aria-pressed={shape === k} onClick={() => setShape(k)}>
              {SHAPE_LABEL[k]}
            </button>
          ))}
        </div>
        <div className="seg" role="group" aria-label="Cách vẽ bàn">
          <button type="button" aria-pressed={tool === 'box'} onClick={() => { setTool('box'); setDraft([]); }}>
            Khoanh vùng
          </button>
          <button type="button" aria-pressed={tool === 'points'} onClick={() => setTool('points')}>
            Chấm từng góc
          </button>
        </div>
        <button type="button" className="btn btn--sm btn--primary" disabled={!fromCamera || busy !== null} onClick={() => void findTables()}>
          <ScanSearch size={14} aria-hidden="true" />
          {busy === 'find' ? 'Đang tìm…' : 'Tự tìm bàn'}
        </button>
        {back.mode === 'snapshot' ? (
          <button type="button" className="btn btn--sm" onClick={back.refresh}>
            <RefreshCw size={14} aria-hidden="true" />
            Chụp lại
          </button>
        ) : (
          <label className="btn btn--sm file-btn">
            <Film size={14} aria-hidden="true" />
            Chọn file
            <input type="file" accept="video/*,image/*" className="visually-hidden" onChange={back.pickFile} />
          </label>
        )}
        {back.mode === 'file' && back.video && back.video.duration > 0 && (
          <label className="zone-seek small muted">
            <span>Khung lúc</span>
            <input
              type="range"
              min={0}
              max={back.video.duration}
              step={0.1}
              value={back.video.t}
              onChange={(ev) => {
                const t = Number(ev.target.value);
                back.setVideo((v) => (v ? { ...v, t } : v));
                if (videoRef.current) videoRef.current.currentTime = t;
              }}
            />
            <span className="measured cool">{back.video.t.toFixed(1)} giây</span>
          </label>
        )}
        {back.mode === 'file' && back.video && (
          <video
            ref={videoRef}
            className="visually-hidden"
            src={back.video.src}
            muted
            playsInline
            preload="auto"
            onLoadedMetadata={(ev) => {
              const el = ev.currentTarget;
              const duration = Number.isFinite(el.duration) ? el.duration : 0;
              const t = Math.min(1, duration / 2);
              back.setVideo((v) => (v ? { ...v, duration, t } : v));
              el.currentTime = t;
            }}
            onSeeked={(ev) => back.grab(ev.currentTarget)}
            onError={() => back.setNote('Trình duyệt không mở được video này. Hãy thử file .mp4 (H.264), hoặc chụp màn hình rồi chọn ảnh.')}
          />
        )}
      </div>

      {back.note && <p className="small muted">{back.note}</p>}

      <div className="zone-layout">
        <div ref={stageRef} className="zone-stage" style={{ aspectRatio: `${space.w} / ${space.h}` }} data-drawing={drawing || undefined}>
          {back.bg ? <img src={back.bg.src} alt={`Hình nền của ${camera} để vẽ vùng bàn`} draggable={false} /> : <div className="zone-blank">Chưa có hình nền</div>}
          <svg
            ref={svgRef}
            viewBox={`0 0 ${space.w} ${space.h}`}
            preserveAspectRatio="none"
            onClick={onStageClick}
            onPointerDown={startBox}
            onPointerMove={onMove}
            onPointerUp={endDrag}
            onPointerCancel={endDrag}
            onPointerLeave={() => setHover(null)}
            role="application"
            aria-label={tool === 'box' ? 'Kéo một khung quanh bàn để thêm bàn. Kéo bàn để dời, bấm đúp để đặt tên.' : 'Bấm để chấm góc bàn. Enter khép vùng, Backspace xoá điểm vừa chấm, Esc huỷ.'}
          >
            {view.map((t) => {
              const [cx, cy] = t.polygon.reduce<[number, number]>((acc, [x, y]) => [acc[0] + x / t.polygon.length, acc[1] + y / t.polygon.length], [0, 0]);
              const isSel = t.key === selected;
              return (
                <g key={t.key} className="ez-table" data-selected={isSel || undefined} data-area={isTable(t) ? undefined : t.type}>
                  <polygon
                    points={t.polygon.map((p) => p.join(',')).join(' ')}
                    vectorEffect="non-scaling-stroke"
                    onPointerDown={(ev) => startMove(ev, t.key)}
                    onDoubleClick={() => focusName(t.key)}
                    onClick={(ev) => {
                      if (drawing) return;
                      ev.stopPropagation();
                      justDragged.current = false;
                      setSelected(t.key);
                    }}
                  />
                  <text x={cx} y={cy} fontSize={14 * k} strokeWidth={4 * k} textAnchor="middle" dominantBaseline="middle">
                    {(isTable(t) ? t.id : t.name || AREA_LABEL[t.type as AreaType]) || '?'}
                  </text>
                  {isSel &&
                    t.polygon.map(([x, y], i) => (
                      <circle
                        key={i}
                        className="zone-handle"
                        cx={x}
                        cy={y}
                        r={r * 1.2}
                        vectorEffect="non-scaling-stroke"
                        onPointerDown={(ev) => startDrag(ev, t.key, i)}
                        onClick={(ev) => {
                          ev.stopPropagation();
                          justDragged.current = false;
                        }}
                      />
                    ))}
                </g>
              );
            })}
            {box && (
              <rect
                className="ez-box"
                x={Math.min(box[0][0], box[1][0])}
                y={Math.min(box[0][1], box[1][1])}
                width={Math.abs(box[1][0] - box[0][0])}
                height={Math.abs(box[1][1] - box[0][1])}
                vectorEffect="non-scaling-stroke"
              />
            )}
            {drawing && (
              <g className="ez-draft">
                <polyline points={[...draft, ...(hover ? [hover] : [])].map((p) => p.join(',')).join(' ')} vectorEffect="non-scaling-stroke" />
                {draft.map(([x, y], i) => (
                  <circle key={i} cx={x} cy={y} r={i === 0 && draft.length >= 3 ? r * 1.6 : r} data-first={i === 0 || undefined} vectorEffect="non-scaling-stroke" />
                ))}
              </g>
            )}
          </svg>
        </div>

        <aside className="zone-side">
          <p className="small ink2" aria-live="polite">
            {found !== null
              ? found > 0
                ? `Camera tìm thêm được ${found} bàn. Kéo để chỉnh, bấm đúp để đặt tên.`
                : 'Camera không tìm thêm được bàn nào. Hãy kéo một khung quanh bàn.'
              : drawing
                ? `Đang vẽ bàn mới: ${draft.length} điểm. ${draft.length >= 3 ? 'Bấm lại điểm đầu hoặc Enter để khép vùng.' : 'Chấm tiếp các góc bàn.'}`
                : shape !== 'table'
                  ? `Đang vẽ vùng ${SHAPE_LABEL[shape]}: ${tool === 'box' ? 'kéo một khung' : 'chấm từng góc'} quanh chỗ đó.`
                : tool === 'box'
                  ? 'Kéo một khung quanh bàn, camera sẽ ôm sát bàn đó. Kéo bàn để dời, kéo chấm tròn để chỉnh góc, bấm đúp để đặt tên.'
                  : 'Bấm lên hình để chấm từng góc bàn, bấm lại điểm đầu hoặc Enter để khép vùng.'}
          </p>
          {drawing && (
            <div className="flex gap-2">
              <button type="button" className="btn btn--sm btn--primary" disabled={draft.length < 3} onClick={closeDraft}>
                Khép vùng
              </button>
              <button type="button" className="btn btn--sm" onClick={() => setDraft((d) => d.slice(0, -1))}>
                Xoá điểm cuối
              </button>
              <button type="button" className="btn btn--sm btn--ghost" onClick={() => setDraft([])}>
                Huỷ
              </button>
            </div>
          )}

          {sorted.length ? (
            <ul className="zone-list" aria-label="Các bàn đã vẽ">
              {sorted.map((t) => (
                <li key={t.key} data-selected={t.key === selected || undefined}>
                  <button type="button" className="zone-pick" aria-pressed={t.key === selected} onClick={() => setSelected(t.key)} aria-label={isTable(t) ? `Chọn bàn ${t.id}` : `Chọn vùng ${t.name ?? t.id}`}>
                    {isTable(t) ? <span className="tiny muted">{t.polygon.length} góc</span> : <span className="zone-type-tag">{SHAPE_LABEL[t.type]}</span>}
                  </button>
                  <label className="visually-hidden" htmlFor={`zn-${t.key}`}>
                    {isTable(t) ? 'Tên bàn' : 'Tên vùng'}
                  </label>
                  <input
                    id={`zn-${t.key}`}
                    className="input zone-name"
                    value={isTable(t) ? t.id : (t.name ?? '')}
                    maxLength={isTable(t) ? 12 : 30}
                    onChange={(ev) => rename(t.key, ev.target.value)}
                    onFocus={() => setSelected(t.key)}
                  />
                  <button type="button" className="btn btn--icon btn--ghost" aria-label={`Xoá ${isTable(t) ? `bàn ${t.id}` : `vùng ${t.name ?? t.id}`}`} onClick={() => removeTable(t.key)}>
                    <Trash size={15} aria-hidden="true" />
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="small muted">Camera {camera} chưa có bàn nào.</p>
          )}

          {sorted.filter(isTable).length > 1 && (
            <button type="button" className="btn btn--sm btn--ghost zone-renumber" onClick={renumber}>
              <ListOrdered size={14} aria-hidden="true" />
              Đánh số lại B1, B2…
            </button>
          )}

          {problems.map((p) => (
            <p key={p} className="small bad">
              {p}
            </p>
          ))}

          <div className="flex gap-2 flex-wrap mt-auto">
            <button type="button" className="btn btn--primary" disabled={!dirty || problems.length > 0 || busy !== null} onClick={() => void save()}>
              <Save size={16} aria-hidden="true" />
              Lưu vùng
            </button>
            <button
              type="button"
              className="btn btn--ghost"
              disabled={!dirty}
              onClick={() => {
                setEdit(null);
                setDraft([]);
                setSelected(null);
              }}
            >
              <Undo2 size={16} aria-hidden="true" />
              Bỏ thay đổi
            </button>
          </div>
          <p className="tiny muted">
            Lưu theo cỡ ảnh {Math.round(space.w)}×{Math.round(space.h)}. Máy camera tự đổi tỉ lệ nếu video có cỡ khác.
          </p>
        </aside>
      </div>
    </div>
  );
}

/** Chọn camera rồi vẽ vùng bàn cho camera đó */
export function ZoneEditor({ initialCamera, autoFind }: { initialCamera: string | null; autoFind?: boolean }) {
  const cameras = useLive((s) => s.cameras);
  const zones = useLive((s) => s.zones);
  const ids = useMemo(() => {
    const set = new Set<string>([...cameras.map((c) => c.id), ...zones.map((z) => z.camera)]);
    if (!set.size) set.add('cam1');
    return [...set].sort(byName);
  }, [cameras, zones]);
  const [picked, setPicked] = useState<string | null>(initialCamera);
  const camera = picked && ids.includes(picked) ? picked : ids[0];
  const stored = zones.find((z) => z.camera === camera);

  return (
    <section className="panel" aria-labelledby="zones-title">
      <div className="panel-head">
        <h2 id="zones-title">Vùng bàn và khu vực trên hình camera</h2>
        <label className="flex items-center gap-2 small muted">
          Camera
          <select className="input phone-select" value={camera} onChange={(ev) => setPicked(ev.target.value)}>
            {ids.map((id) => (
              <option key={id} value={id}>
                {cameras.find((c) => c.id === id)?.name ?? id}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="panel-body">
        <ZoneCanvas key={camera} camera={camera} stored={stored} autoFind={autoFind && camera === initialCamera} />
      </div>
    </section>
  );
}
