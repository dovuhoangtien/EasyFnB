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
  stage: 'seated' | 'greeted' | 'served' | 'finished' | 'left' | null;  // meal stage of the current seating (server/giai_doan.py)
  stage_since: number | null; // ms, when that stage started
  nudge: 'greet' | 'food' | 'bill' | null;  // soft reminder currently shown for this table
  nudge_at: number | null;
  snap_at: number | null;     // ms, latest table snapshot received (GET /api/tables/{id}/snap.jpg)
}

interface Zone {               // one table polygon in a camera image
  id: string;                 // "B2"
  polygon: [number, number][];// camera pixel coordinates
}

interface CameraZones {
  camera: string;
  frame_w: number;            // size of the image the polygons were drawn on
  frame_h: number;
  tables: Zone[];             // giữ nguyên {id, polygon}; các phiên khác chỉ THÊM trường tuỳ chọn vào Zone
  areas?: Area[];             // vùng không phải bàn (an ninh). PUT không gửi thì coi là rỗng
  an_ninh?: AnNinhView;       // chỉ có trong GET (tính mỗi lần hỏi), không lưu, PUT bỏ qua
}

interface Area {              // server/an_ninh.py
  id: string;                 // duy nhất trong camera
  type: 'quay' | 'kho' | 'giu_xe' | 'cua';   // quầy thu ngân | kho, bếp (cấm khách) | chỗ giữ xe | cửa
  name: string;               // tên hiện trên màn hình; bỏ trống thì máy chủ đặt theo loại
  polygon: [number, number][];
}

interface AnNinhView {        // cho máy camera
  closed: boolean;            // quán đang đóng (ngoài open_time..close_time, hoặc guard_mode)
  after_hours: boolean; restricted: boolean; item_taken: boolean;   // công tắc từng tính năng
  delivery_now: boolean;      // trong khung giờ giao hàng: không báo vao_khu_cam
  blur_faces: boolean;
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
  kind: Kind | 'ack' | 'done' | 'cancel' | 'escalate' | 'verify' | 'system' | 'nudge';  // nudge = soft reminder, no task, not read aloud
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
  table_check_s: number;      // default 60: seconds between Gemini Decision looks at one occupied table; 0 = off
  wait_greet_s: number;       // default 180: seated this long with nobody coming → one nudge (+ a new_guest task if the table has no open task); 0 = off
  wait_food_s: number;        // default 900: greeted this long and a snapshot showed no food → one nudge; 0 = off
  wait_bill_s: number;        // default 600: finished eating this long and no staff came → one nudge; 0 = off
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
- `GET /api/manifest/nv/{id}` → Web App Manifest (`application/manifest+json`) for one staff member: `start_url` is `/nv/{id}`, `display` is `standalone`. The staff page points `<link rel="manifest">` here so "Add to Home Screen" opens that person's own app. 404 if the id is not in the staff list.
- `GET /api/info` → `{lan_ip: string | null, https_port: number | null, gemini: boolean, provider: string, model: string | null}`. `lan_ip` is the server's Wi-Fi address (null on Cloud Run), used to build staff phone links when the manager opened the app via localhost. `https_port` is set only when the server runs with `--https`; Settings uses it for the phone-camera QR code (phones block the camera on plain http). `gemini` means "an LLM is enabled"; `provider` is the display name (`Gemini` or `kie.ai`).
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
- `GET /api/tables/{table}/snap.jpg?camera=` → latest table snapshot from the camera (faces blurred; 404 if none)
- `GET /api/timeline?since=&until=&table=&kind=&alert_id=&limit=&newest=` → `{ rows: TimelineRow[] }`. The lasting
  history (SQLite `DATA_DIR/timeline.db`), kept across restarts and `POST /api/reset`. `since`/`until` are epoch
  seconds, `kind` is a comma list (a trailing `*` matches a prefix, e.g. `alert_*`), `limit` default 500 (max 5000),
  oldest first unless `newest=1`.
  ```ts
  interface TimelineRow { id: number; ts: number /* epoch s */; day: string /* "2026-11-13", Vietnam time */;
    camera: string | null; table: string | null; kind: string; alert_id: string | null; staff: string | null;
    text: string | null; data: Record<string, unknown> }
  ```
  Kinds: `log` (every LogEntry; `data.log_kind`), `alert_created`, `alert_verified` | `alert_rejected` |
  `alert_unverified` (`data.path, reason, ms`), `alert_assigned` (`data.prev`), `alert_acked` (`data.wait_s, by_camera`),
  `alert_done` | `alert_auto_closed` (`data.by, reason, wait_s, total_s`), `alert_cancelled` (`data.reason, total_s`),
  `table` (`data.state, prev, people`; only when the state changes), `staff_online`, `staff_offline`,
  `stage` (`data.stage, prev, via, seat, prev_s`), `nudge` (`data.nudge, stage, seat, waited_s`),
  `table_check` (one Gemini Decision reading: the five probabilities + `used`, or `error`), `shift_reset`.
- `GET /api/timeline/days` → `{ days: string[] }` days that have rows

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
- `POST /api/zones/suggest` body `{ camera, frame_w, frame_h, box?: [x1,y1,x2,y2] }` → `{ frame_w, frame_h, tables: [{ polygon, score }] }`
  The camera machine finds tables on its current frame (polygons in the camera's own frame size). With `box`
  it looks only around that rough rectangle and returns at most one table. 409 if the camera is not
  sending frames, 504 if it does not answer in 12 s.
- `PUT /api/staff` body `{ "staff": [{ "id", "name", "role", "consent"? }] }` → `Staff[]`
  `Staff` also carries `consent: boolean` and `photos: [{ id, kind: 'face'|'body', source: 'upload'|'camera' }]`.
  Photos are kept when a person is edited and deleted when the person is removed.
- `POST /api/staff/{id}/photos?kind=face|body` body: raw JPEG (max 3 MB, max 8 photos per person) → `Staff[]`
- `POST /api/staff/{id}/photos/camera` body `{ camera }` → `Staff[]` (the camera crops the person nearest the
  middle of its frame, saved as a `body` photo)
- `GET /api/staff/{id}/photos/{photo}.jpg`, `DELETE /api/staff/{id}/photos/{photo}` → `Staff[]`
- `PUT /api/settings` body `Partial<Pick<Settings, 'verify_kinds'|'hold_until_verified'|'escalate_s'|'dedup_s'|'table_check_s'|'wait_greet_s'|'wait_food_s'|'wait_bill_s'>>` → `Settings`
  - An ninh (cùng đường này): `sec_item_taken`, `sec_after_hours`, `sec_restricted`, `guard_mode`, `blur_faces` (bool);
    `open_time`, `close_time` ("HH:MM"); `delivery_from`, `delivery_to` ("HH:MM" hoặc ""); `hold_s` (10..86400).
    Chỉ đổi `blur_faces` mới cần header `X-Owner-Pin` (403 nếu thiếu hoặc sai); các khoá khác không cần PIN.
    `Settings` trả thêm `owner_pin_set`, `closed`; không bao giờ trả mã PIN.
- `PUT /api/owner/pin` `{pin, old_pin?}` (4-8 chữ số; đã có PIN thì old_pin phải đúng, không thì 403);
  `POST /api/owner/pin/check` `{pin}` → `{ok}`.
- Vai trò nhân viên (`PUT /api/staff`): `serve` | `clean` | `cashier` | `owner` (chủ quán: chỉ nhận cảnh báo an ninh).
- Cảnh báo an ninh: `Alert.kind` `item_taken` | `after_hours` | `restricted`, `group: 'security'`, `area`, `area_name`,
  `notify: string[]` (người nhận; `assigned_to` luôn null), `evidence.person`. Không tính vào `/api/report`.
  Camera gửi `lay_do`, `co_nguoi_ngoai_gio`, `vao_khu_cam` (cần `area`) qua `POST /api/edge/event`, ảnh kèm trong `images`.
- Clip gốc không che mặt: `POST /api/alerts/{id}/clip-goc` (X-Owner-Pin) → như `POST /api/clips`;
  `GET /api/clips/{id}.mp4` của clip gốc cần X-Owner-Pin hoặc `?pin=`; `POST /api/clips/{id}/keep` giữ làm bằng chứng.
  Việc `clip` cho máy camera có thêm `goc: true` khi là bản gốc.
- Lịch sử an ninh cho trợ lý/phòng chat: `server/an_ninh_tro_ly.py` `lich_su(timeline, since, until)`.
- Nhiều ngày và nhân viên ngày cũ: `server/nhieu_ngay.py` (công cụ `nhieu_ngay(khoang_ngay)` cho "tuần này", "7 ngày qua", "tháng trước", "6/11 đến 10/11"; `nhan_vien_ngay_cu(ngay)` cho giờ vào ra ca và tốc độ từng người). Đường không AI cũng trả lời câu nhiều ngày.
- Dữ liệu lâu dài nằm ở hai tệp SQLite trong thư mục dữ liệu: `timeline.db` (một bảng `timeline`: mỗi dòng một sự kiện có `ts, day, camera, table, kind, alert_id, staff, text, data`; chỉ mục theo `ts`, `(table, ts)`, `day`) và `quan.db` (`messages`, `payments`, `payment_edits`, `visit_notes`). Cột `day` là ngày của quán, đổi lúc 04:00. Số liệu ca đang chạy nằm trong RAM và mất khi khởi động lại; câu hỏi về ngày cũ luôn đọc từ hai tệp này.
- Tiền thu cho trợ lý/phòng chat: `server/doanh_thu_tro_ly.py` (công cụ `doanh_thu(ngay, so_voi_ngay, hien)`, đọc `Phong.revenue`; đường không AI cũng trả lời được). Gemini báo 429 thì thử lại một lần rồi mới rơi về đường không AI.
  (the last four must be numbers from 0 to 86400, otherwise 400 and nothing is changed)
- `POST /api/reset` → `{}` clears alerts, log, table states, table snapshots, crops (keeps zones, staff, settings and
  the timeline, which gets a `shift_reset` row)

## AI (Gemini, Google ADK)

- `POST /api/assistant` body `{ "question": "Bàn nào chờ lâu nhất?", "session"?: string }`
  The owner's assistant. The answer is a short sentence plus display blocks the UI renders (stats, chart, events with
  photos, table, staff cards). `session` keeps the conversation context (ADK only); any string, default one shared session.
  ```ts
  { answer: string,                 // 1-3 Vietnamese sentences, no markdown
    blocks: Block[],                // 0-5 blocks, in display order
    suggestions: string[],          // up to 3 follow-up questions
    refs: { alert_id: string | null, t: number, table: string | null }[],   // every event shown in an `events` block
    engine: 'adk' | 'rules',        // 'adk' = Google ADK agent on Gemini; 'rules' = computed without AI
    model: string | null,           // Gemini model when engine is 'adk', otherwise null
    ms: number }
  type Tone = 'good' | 'warn' | 'bad' | null;
  type Block =
    | { type: 'stats', title: string | null,
        items: { label: string, value: string, note: string | null, tone: Tone }[] }
    | { type: 'chart', title: string, kind: 'bar' | 'column' | 'line', unit: string,   // bar = compare, column/line = over time
        points: { label: string, value: number, note: string | null }[] }
    | { type: 'events', title: string,
        items: { alert_id: string, kind: 'call' | 'needs_clearing' | 'new_guest', table: string | null, t: number,
                 status: string, wait_s: number | null,      // arrived_s if the camera measured it, else acked - created; open tasks count to now
                 staff: string | null, text: string,
                 crop_url: string | null, strip_url: string | null, video_t: number | null,
                 clip_url: string | null }[] }                // "/api/alerts/{id}/clip.mp4" when the event clip is stored
    | { type: 'table', title: string, columns: string[], rows: string[][] }
    | { type: 'staff', title: string,
        items: { id: string, name: string, role: string, online: boolean, acked: number, done: number,
                 mean_response_s: number | null, worked_s: number, first_in: number | null }[] }
    | { type: 'video', title: string, items: VideoItem[] }    // at most 6 clips, the first is the one to play
    | { type: 'timeline', title: string,                      // the story of a table or a time range, oldest first
        items: { t: number, text: string, tone: Tone, table: string | null, alert_id: string | null,
                 video: VideoItem | null }[] }
  // One camera clip. Exactly one way to get it: `src` is ready to play; `clip_id` is an on-demand request the server
  // already made (poll GET /api/clips/{clip_id} until it is not 'pending'); both null with no `error` means ask with
  // POST /api/clips {camera, t_from, t_to} when the viewer opens it. `error` is a plain Vietnamese reason when there is
  // certainly no video (camera off, time not reached, nothing recorded); show it with `poster`, never a broken player.
  type VideoItem = { label: string, t: number, table: string | null, alert_id: string | null,
                     src: string | null, clip_id: string | null, poster: string | null, note: string | null,
                     camera: string, t_from: number, t_to: number, error: string | null };
  ```
  Video questions ("cho xem lại lúc 12:30 ở bàn 3", "lần khách chờ lâu nhất", "kể lại bàn B2", "bàn nào đang chờ lâu",
  "hôm qua so với hôm nay") are answered in `server/xem_lai.py` on the rules path and by the ADK tools `xem_video`,
  `dong_thoi_gian`, `ban_dang_the_nao`, `so_sanh_ngay`. `refs` also lists every clip of a `video` block. After a server
  restart the alerts are gone from RAM but the timeline rows remain, so earlier events are still found (their clips are
  then cut on demand from the camera's recording).
  With `GEMINI_API_KEY` set the answer comes from a Google ADK agent (`server/tro_ly.py`): Gemini picks which tools to
  call, the server fills every number and block, so figures are never copied by the model. Without the key, or when
  ADK fails or takes over 30 s, the same blocks are built by keyword rules; the call still returns 200 with
  `engine: 'rules'`. 400 when `question` is empty.
- `GET /api/report` → shift metrics, computed without AI:
  ```ts
  { from: number, to: number,
    counts: Record<'call'|'needs_clearing'|'new_guest', number>,
    cancelled: number, rejected_by_gemini: number,
    response_s: { mean: number|null, median: number|null, p90: number|null }, // created -> acked
    // how many tasks were picked up fast (<= fast_s), a bit slow (<= slow_s), slow (> slow_s), or by nobody
    speed: { fast: number, ok: number, slow: number, missed: number, fast_s: 30, slow_s: 60 },
    done_s: { mean: number|null, median: number|null },                     // created -> done
    escalated: number,
    per_staff: { id: string, name: string, acked: number, done: number, mean_response_s: number|null,
                 fast: number, ok: number, slow: number,
                 kinds: Record<'call'|'needs_clearing'|'new_guest', number> }[],   // tasks this person picked up, by kind
    per_table: { table: string, calls: number, clearings: number, guests: number,
                 fast: number, ok: number, slow: number, missed: number }[],       // how fast this table was served
    // the shift in equal time buckets (step_s seconds each, at least 6): tasks by kind and pick-up speed.
    // null before the first task
    timeline: { step_s: number,
                points: { t: number, call: number, needs_clearing: number, new_guest: number,
                          fast: number, ok: number, slow: number, missed: number }[] } | null }
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
- `POST /api/edge/table-snap` JSON `{ camera, table, ts?, jpeg_b64 }` (edge sends one per occupied table every
  `--chup-ban` seconds, default 20; max 1 MB) → `{ ok: true, check }` or `{ ok: false, reason: 'unknown_table' }`.
  The server keeps only the latest image per table and, when due, asks Gemini Decision what stage the meal is at.
  `check` says what happened: `started | not_due | busy | off | not_needed | rate_limited | breaker_open`.
  `ts` is ignored (the server uses its own clock). 400 if the image is missing or not a JPEG.
- `POST /api/edge/table-ask` JSON `{ camera, jpeg_b64, tables: [{ table, color: 'cam'|'xanh dương'|'xanh lá' }] }`
  (2-3 tables). The edge sends this when a seated guest sits between tables it cannot tell apart; the image has a
  red box on the person and each candidate table outlined in its color. The server asks Gemini Decision and returns
  `{ ok: true, probs: { B3: 0.76, B4: 0.13 }, seated, ms, tokens }`, or `{ ok: false, reason }` with reason
  `decision_off | too_often | breaker_open | timeout | error | not_seated`. At most one call per camera per 8 s.
  The edge decides: it pins the guest to a table only when one is ≥ 0.7 and every other ≤ 0.3.
- `GET /api/edge/jobs?camera=cam1` → `{ jobs: [{ id, kind: 'find_tables'|'staff_photo'|'clip', ... }] }` setup work the
  web asked this camera to do; each job is handed out once (the edge polls every second).
  `POST /api/edge/jobs/{id}` body = the result (`{ frame_w, frame_h, tables }`, `{ jpeg_b64 }` or `{ error }`).
- `GET /api/edge/staff-refs` → `{ version, refs: [{ staff, name, id, kind, url }] }` photos of staff who agreed;
  the edge re-reads them when `version` changes (only with `--nv-theo-anh`).
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

### Video clips (camera started with `--ghi-hinh`)

The camera machine records its own video (faces blurred, 10 s H.264 segments, kept 24 h / 5 GB on that machine)
and cuts clips out of it. All times are epoch milliseconds. Clips are H.264 MP4, max 60 s, served with `Range`
support (206), so `<video src>` works on phones.

- `Alert.clip?: boolean` is `true` once the clip of that event is on the server (about 10 to 15 s after the alert:
  6 s before to 8 s after the event). It arrives as a normal `alert` SSE update.
  `GET /api/alerts/{id}/clip.mp4` → the MP4, 404 while there is none.
- `POST /api/clips` body `{ camera, t_from, t_to }` → `ClipRequest` `{ id, status: 'pending'|'ready'|'failed',
  camera, t_from, t_to, url: string|null, error: string|null }`. Longer than 60 s is cut to the first 60 s; a `t_to`
  in the future is cut to now. 400 if `t_to <= t_from` or `t_from` is in the future. If the camera is not
  running the answer is 200 with `status: 'failed'` and a Vietnamese `error` straight away.
- `GET /api/clips/{id}` → `ClipRequest` (poll about once a second; `ready` normally within 2 to 8 s, `failed` with
  `error` "chưa ghi hình lúc đó" when nothing was recorded then, or "Máy camera không trả lời." after 30 s).
  When `ready`, `url` is `/api/clips/{id}.mp4` and `t_from`/`t_to` are what the clip really covers.
- Edge: on-demand requests reach the camera as a job `{ id, kind: 'clip', t_from, t_to }` on `GET /api/edge/jobs`.
  `POST /api/edge/clip?camera=cam1&t_from=..&t_to=..&eid=<event id>` (or `&job=<job id>`), body = raw MP4 (max 40 MB,
  413 above) → `{ ok, alert_id }` or `{ ok, clip_id }`. A clip whose event is not known yet is kept 30 s, then dropped;
  a second clip for the same alert is ignored. If nothing was recorded the camera answers the job with `{ error }`.
- `POST /api/reset` deletes every clip on the server (the camera's own recording is kept, so a time range can be
  asked for again). The server keeps at most `CLIPS_MAX_MB` (default 2000) of clips, oldest deleted first, and
  starts with an empty clips folder.
## Phân tích ca

Không có đường API riêng: gợi ý cho ca sau (khối `insights`; mỗi mục có `id, tone, title, text, action, events[]`) và bảng xếp ca (khối `table`) chỉ đi qua trợ lý `POST /api/assistant`. Số liệu tính trong `server/goi_y.py`.
