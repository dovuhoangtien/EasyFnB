# Easy FnB live API (contract)

One FastAPI service. In production it also serves the built web app (`easy-fnb/dist`) so the whole
system is one Cloud Run service. In development the Vite dev server proxies `/api` to
`http://localhost:8080`.

All times are epoch milliseconds (`number`) unless the name ends in `_s` (seconds).
JSON field names are English snake_case. UI text is Vietnamese and lives in the web app.

## Types

```ts
type Kind = 'call' | 'needs_clearing' | 'new_guest' | 'guest_left' | 'cleared';
// call            khách giơ tay gọi phục vụ          -> task for role 'serve'
// needs_clearing  bàn cần dọn                         -> task for role 'clean' (fallback 'serve')
// new_guest       khách mới vào bàn                   -> task for role 'serve' (chào, đưa menu)
// guest_left      khách rời bàn                       -> log only, no task
// cleared         camera thấy bàn đã dọn              -> log only; auto-closes open needs_clearing alert of that table

type AlertStatus =
  | 'verifying'   // waiting for Gemini before notifying staff (only kinds in settings.hold_until_verified)
  | 'open'        // notified, nobody accepted yet
  | 'acked'       // a staff member pressed "Đang tới"
  | 'done'        // finished
  | 'cancelled';  // false alarm (Gemini rejected, or manager/staff cancelled)

type VerifyState = 'pending' | 'confirmed' | 'rejected' | 'skipped' | 'error';

interface Verify {
  state: VerifyState;
  confidence: number | null; // 0..1
  reason: string | null;     // short Vietnamese reason from Gemini
  ms: number | null;         // Gemini latency
  model: string | null;
}

interface Alert {
  id: string;                 // "a12"
  kind: 'call' | 'needs_clearing' | 'new_guest';
  table: string | null;       // table id from zones, e.g. "B2"; null if no zones / person not at a table
  camera: string;             // "cam1"
  created_at: number;
  video_t: number | null;     // seconds into the source video when the edge fired (for linking to footage)
  box: [number, number, number, number] | null; // person/table box in camera pixels
  score: number | null;       // edge score (hand model / rule)
  detail: string;             // edge detail text (Vietnamese)
  crop_url: string | null;    // "/api/crops/a12.jpg"
  status: AlertStatus;
  assigned_to: string | null; // staff id
  acked_at: number | null;
  acked_by: string | null;
  done_at: number | null;
  done_by: string | null;
  cancelled_at: number | null;
  cancel_reason: string | null;
  escalated: boolean;         // nobody accepted within settings.escalate_s; reassigned
  repeats: number;            // duplicate edge events merged into this alert
  verify: Verify;
}

interface TableState {
  id: string;                 // "B2"
  camera: string;
  state: 'empty' | 'occupied' | 'needs_clearing' | 'unknown';
  people: number;
  since: number;              // when the current state started
  dirty: number | null;       // 0..1 table model score, if any
}

interface Zone {               // one table polygon in a camera image
  id: string;                 // "B2"
  polygon: [number, number][];// camera pixel coordinates
}

interface CameraZones {
  camera: string;
  frame_w: number;            // size of the image the polygons were drawn on
  frame_h: number;
  tables: Zone[];
}

interface Camera {
  id: string;                 // "cam1"
  name: string;               // "Cam 1"
  online: boolean;            // a frame arrived in the last 5 s
  last_frame_at: number | null;
  frame_version: number;      // increments on every live frame (use as cache buster)
  has_snapshot: boolean;      // a raw (no overlay) frame is available for drawing zones
  frame_w: number | null;
  frame_h: number | null;
  fps: number | null;         // processing fps reported by the edge
  source: string | null;      // video file name or camera url reported by the edge
}

type Role = 'serve' | 'clean' | 'cashier';
interface Staff {
  id: string;                 // "lan"
  name: string;               // "Lan"
  role: Role;
  online: boolean;            // has an open /api/stream?staff=<id> connection
  open_tasks: number;         // alerts assigned and not done/cancelled
}

interface LogEntry {
  id: number;
  t: number;
  kind: Kind | 'ack' | 'done' | 'cancel' | 'escalate' | 'verify' | 'system';
  table: string | null;
  camera: string | null;
  alert_id: string | null;
  text: string;               // Vietnamese sentence, ready to display
}

interface Settings {
  gemini: boolean;            // an LLM key is set: KIE_API_KEY (kie.ai) or GEMINI_API_KEY
  provider: string;           // "kie.ai" when KIE_API_KEY is set, otherwise "Gemini"
  model: string;              // e.g. "deepseek-v4-1-flash" or "gemini-3.5-flash-lite"
  verify_kinds: string[];     // kinds sent to the LLM, default ["call","needs_clearing"]; [] when running on kie.ai
  hold_until_verified: string[]; // default ["needs_clearing"]; "call" is notified at once, retracted if rejected
  escalate_s: number;         // default 45
  dedup_s: number;            // default 20
}

interface State {
  server_time: number;
  settings: Settings;
  cameras: Camera[];
  zones: CameraZones[];
  tables: TableState[];
  alerts: Alert[];            // newest first, at most 300
  staff: Staff[];
  log: LogEntry[];            // newest first, at most 500
}
```

## Reading

- `GET /api/state` → `State`
- `GET /api/info` → `{lan_ip: string | null, gemini: boolean, provider: string, model: string | null}`. `lan_ip` is the server's Wi-Fi address (null on Cloud Run), used to build staff phone links when the manager opened the app via localhost. `gemini` means "an LLM is enabled"; `provider` is the display name (`Gemini` or `kie.ai`).
- `GET /api/stream` → Server-Sent Events. Optional query `staff=<id>` marks that staff member online
  while connected. Event names and `data` (JSON):
  - `snapshot` → `State` (sent first on every connect/reconnect)
  - `alert` → `Alert` (created or changed; upsert by id)
  - `table` → `TableState` (upsert by id)
  - `camera` → `Camera` (upsert by id; sent on every live frame, at most ~4 per second per camera)
  - `zones` → `CameraZones` (replace that camera's zones)
  - `staff` → `Staff[]` (full list)
  - `log` → `LogEntry` (prepend)
  - `settings` → `Settings`
  - `reset` → `{}` (everything cleared; client should refetch `/api/state`)
  - comment lines `: ping` every 15 s
- `GET /api/camera/{camera}/frame.jpg` → latest live frame with overlays (404 if none)
- `GET /api/camera/{camera}/snapshot.jpg` → latest raw frame without overlays (404 if none)
- `GET /api/crops/{alert_id}.jpg` → event crop image

## Staff and manager actions

- `POST /api/alerts/{id}/ack` body `{ "staff": "lan" }` → `Alert` ("Đang tới")
- `POST /api/alerts/{id}/done` body `{ "staff": "lan" }` → `Alert`
- `POST /api/alerts/{id}/cancel` body `{ "by": "manager" | "<staff id>", "reason": "báo nhầm" }` → `Alert`
- `POST /api/alerts/{id}/assign` body `{ "staff": "minh" }` → `Alert`
- `POST /api/alerts` body `{ "kind": "call" | "needs_clearing" | "new_guest", "table": "B2", "camera": "cam1" }`
  → `Alert` (manual alert from the dashboard; no Gemini check)

## Setup

- `GET /api/zones?camera=cam1` → `CameraZones` (empty `tables` if none)
- `PUT /api/zones` body `CameraZones` → `CameraZones`
- `GET /api/staff` → `Staff[]`
- `PUT /api/staff` body `{ "staff": [{ "id", "name", "role" }] }` → `Staff[]`
- `PUT /api/settings` body `Partial<Pick<Settings, 'verify_kinds'|'hold_until_verified'|'escalate_s'|'dedup_s'>>` → `Settings`
- `POST /api/reset` → `{}` clears alerts, log, table states, crops (keeps zones, staff, settings)

## AI (Gemini)

- `POST /api/assistant` body `{ "question": "Bàn B2 gọi mấy lần?" }`
  → `{ "answer": string, "refs": { "alert_id": string | null, "t": number, "table": string | null }[] }`
  Gemini answers from the event log and alerts. When Gemini is off, returns a plain answer computed
  without AI for a few known questions, or a message saying Gemini is not configured.
- `GET /api/report` → shift metrics, computed without AI:
  ```ts
  { from: number, to: number,
    counts: Record<'call'|'needs_clearing'|'new_guest', number>,
    cancelled: number, rejected_by_gemini: number,
    response_s: { mean: number|null, median: number|null, p90: number|null }, // created -> acked
    done_s: { mean: number|null, median: number|null },                     // created -> done
    escalated: number,
    per_staff: { id: string, name: string, acked: number, done: number, mean_response_s: number|null }[],
    per_table: { table: string, calls: number, clearings: number, guests: number }[] }
  ```
- `POST /api/report/summary` → `{ "text": string }` Vietnamese end-of-shift summary written by Gemini
  from `/api/report` and the log (or a plain template when Gemini is off).

## Edge (vision pipeline → server)

All edge requests send header `X-Edge-Key: <EDGE_KEY>` when the server has `EDGE_KEY` set (401 otherwise).

- `POST /api/edge/event` JSON:
  ```ts
  { camera: string, kind: 'goi_phuc_vu'|'can_don'|'khach_moi'|'khach_roi'|'da_don',
    table: string|null, video_t: number|null, box: [x1,y1,x2,y2]|null, score: number|null,
    detail: string, crop_jpeg_b64: string|null }
  ```
  → `{ alert_id: string|null }`. Mapping: goi_phuc_vu→call, can_don→needs_clearing, khach_moi→new_guest,
  khach_roi→guest_left, da_don→cleared.
- `POST /api/edge/frame?camera=cam1&kind=live|raw&fps=12.5&source=clip.mp4` body: raw JPEG bytes
  (`Content-Type: image/jpeg`) → `{ ok: true }`
- `POST /api/edge/tables` JSON `{ camera, tables: [{ id, state: 'trong'|'co_khach'|'can_don'|null, people, dirty }] }`
  → `{ ok: true }` (edge sends ~1 per second; Vietnamese states are mapped to TableState.state)
- `GET /api/zones?camera=cam1` (same as above) — the edge loads table polygons at start.
  If the server has none and the edge has local zones, the edge `PUT`s its local zones.

### Verification evidence and items left on a table

- `POST /api/edge/event` also accepts `eid: string` (event id, dedup key for evidence), `items: [{name, count}]`
  (items left on the table, Vietnamese names, `needs_clearing` only) and `images: [{role: 'strip'|'overview'|'clean_ref', jpeg_b64}]`.
- `POST /api/edge/evidence` JSON `{ camera, eid, strip_jpeg_b64?, overview_jpeg_b64?, ref_jpeg_b64?, items? }`
  sent about 1 s after the event. Returns `{ alert_id }`. The server waits up to `settings.evidence_wait_s` (2.5 s) for it before asking Gemini.
- `Alert.items: {name, count}[] | null`; `Alert.evidence: {strip, overview, ref} | null` with URLs
  `GET /api/alerts/{id}/evidence/{strip|overview|ref}.jpg`.
- `Alert.verify.state` may be `unverified` (Gemini unsure, timeout, error, breaker open, no image); the alert is still raised and the UI shows "Chưa xác minh". `verify.path` and `verify.reason` say why.