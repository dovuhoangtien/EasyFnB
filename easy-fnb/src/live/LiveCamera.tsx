import { useEffect, useMemo, useRef, useState } from 'react';
import { frameUrl } from './api';
import { useServerNow } from './store';
import { cameraLive, clockTime, TABLE_STATE_LABEL } from './text';
import type { Alert, Camera, CameraZones, TableState } from './types';

/** Không tải ảnh nhanh hơn 4 khung mỗi giây */
const MIN_FRAME_MS = 250;

interface Shown {
  src: string;
  w: number;
  h: number;
}

/**
 * Tải khung hình mới nhất của camera mỗi khi frame_version tăng.
 * Chỉ một ảnh đang tải tại một thời điểm; ảnh cũ giữ nguyên tới khi ảnh mới tải xong.
 * Component cha đặt key theo id camera nên đổi camera là làm lại từ đầu.
 */
function useLatestFrame(camera: string, version: number) {
  const [shown, setShown] = useState<Shown | null>(null);
  const [failed, setFailed] = useState(false);
  const want = useRef(version);
  const pumpRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    let alive = true;
    let loading = false;
    let loaded = Number.NaN;
    let lastStart = 0;
    let timer: number | undefined;

    const pump = () => {
      if (!alive || loading) return;
      const v = want.current;
      if (v === loaded) return;
      const wait = MIN_FRAME_MS - (performance.now() - lastStart);
      if (wait > 0) {
        window.clearTimeout(timer);
        timer = window.setTimeout(pump, wait);
        return;
      }
      loading = true;
      lastStart = performance.now();
      const img = new Image();
      const src = frameUrl(camera, v);
      img.onload = () => {
        loading = false;
        loaded = v;
        if (!alive) return;
        setShown({ src, w: img.naturalWidth, h: img.naturalHeight });
        setFailed(false);
        pump();
      };
      img.onerror = () => {
        loading = false;
        loaded = v;
        if (!alive) return;
        setFailed(true);
        pump();
      };
      img.src = src;
    };

    pumpRef.current = pump;
    pump();
    return () => {
      alive = false;
      window.clearTimeout(timer);
      pumpRef.current = null;
    };
  }, [camera]);

  useEffect(() => {
    want.current = version;
    pumpRef.current?.();
  }, [version]);

  return { shown, failed };
}

function centroid(points: [number, number][]) {
  let x = 0;
  let y = 0;
  for (const [px, py] of points) {
    x += px;
    y += py;
  }
  const n = Math.max(1, points.length);
  return [x / n, y / n] as const;
}

interface Props {
  camera: Camera;
  zones: CameraZones | undefined;
  tables: TableState[];
  /** việc đang mở, để tô đỏ bàn đang gọi */
  alerts: Alert[];
}

/** Hình camera trực tiếp, phủ vùng bàn tô màu theo trạng thái */
export function LiveCamera({ camera, zones, tables, alerts }: Props) {
  const { shown, failed } = useLatestFrame(camera.id, camera.frame_version);
  const online = cameraLive(camera, useServerNow());

  const w = shown?.w ?? camera.frame_w ?? zones?.frame_w ?? 16;
  const h = shown?.h ?? camera.frame_h ?? zones?.frame_h ?? 9;

  const calling = useMemo(() => {
    const set = new Set<string>();
    for (const a of alerts) if (a.kind === 'call' && a.table && a.camera === camera.id) set.add(a.table);
    return set;
  }, [alerts, camera.id]);

  const stateOf = useMemo(() => {
    const map = new Map<string, TableState>();
    for (const t of tables) if (t.camera === camera.id || !map.has(t.id)) map.set(t.id, t);
    return map;
  }, [tables, camera.id]);

  const zw = zones?.frame_w || w;
  const zh = zones?.frame_h || h;
  const zoneList = zones?.tables ?? [];

  return (
    <div className="live-cam" style={{ aspectRatio: `${w} / ${h}` }}>
      {shown ? (
        <img className="live-cam-img" src={shown.src} alt={`Khung hình mới nhất của ${camera.name}`} draggable={false} />
      ) : zoneList.length === 0 ? (
        <div className="cam-offline">
          <h3>{failed ? 'Chưa có khung hình từ camera này' : 'Đang chờ khung hình đầu tiên'}</h3>
          <p>Máy camera gửi ảnh về máy chủ khi đang chạy.</p>
        </div>
      ) : null}

      {zoneList.length > 0 && (
        <>
          <svg className="zones" viewBox={`0 0 ${zw} ${zh}`} preserveAspectRatio="none" aria-hidden="true">
            {zoneList.map((z) => {
              const st = stateOf.get(z.id);
              return (
                <polygon
                  key={z.id}
                  className="zone"
                  data-state={st?.state ?? 'unknown'}
                  data-hot={calling.has(z.id) || undefined}
                  points={z.polygon.map((p) => p.join(',')).join(' ')}
                  vectorEffect="non-scaling-stroke"
                />
              );
            })}
          </svg>
          <ul className="zone-labels" aria-label="Trạng thái các bàn trên hình">
            {zoneList.map((z) => {
              const st = stateOf.get(z.id);
              const [cx, cy] = centroid(z.polygon);
              const hot = calling.has(z.id);
              return (
                <li
                  key={z.id}
                  className="zone-label"
                  data-state={st?.state ?? 'unknown'}
                  data-hot={hot || undefined}
                  style={{ left: `${(cx / zw) * 100}%`, top: `${(cy / zh) * 100}%` }}
                >
                  <b>{z.id}</b>
                  <span>
                    {hot ? 'đang gọi' : st ? (st.state === 'occupied' && st.people > 0 ? `${st.people} khách` : TABLE_STATE_LABEL[st.state].toLowerCase()) : 'chưa rõ'}
                  </span>
                </li>
              );
            })}
          </ul>
        </>
      )}

      <div className="cam-hud cam-hud--top">
        <span className="hud-tag">
          {online ? <span className="live-dot" aria-hidden="true" /> : null}
          {camera.name || camera.id}, {online ? 'trực tiếp' : 'mất tín hiệu'}
        </span>
        {camera.fps !== null && online && <span className="hud-tag measured">{camera.fps.toFixed(1)} khung/giây</span>}
      </div>
      <div className="cam-hud cam-hud--bottom">
        {camera.source ? <span className="hud-tag hud-src">{camera.source}</span> : !shown && zoneList.length > 0 ? <span className="hud-tag">Chưa có hình, chỉ hiện vùng bàn</span> : <span />}
        {camera.last_frame_at !== null && <span className="hud-tag measured">{clockTime(camera.last_frame_at)}</span>}
      </div>
    </div>
  );
}
