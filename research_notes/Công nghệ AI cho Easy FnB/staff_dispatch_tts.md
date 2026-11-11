# Staff Dispatch & Spoken Vietnamese Alerts for Easy FnB (camera events → right staff member → Bluetooth earbud + counter dashboard)

Research date: 2026-11-03. All "accessed" dates below = 2026-11-03 unless noted. Items marked **[unverified / training knowledge]** were NOT confirmed by a source this session and must be checked before being stated as fact.

---

## 1. Vietnamese TTS options (Google Cloud TTS, Gemini TTS, Android on-device, open-source) and pre-generated vs dynamic synthesis

### Takeaway
Google Cloud TTS has 40 vi-VN voices as of Nov 2026, including **30 Chirp 3 HD voices**. That makes Chirp 3 HD the top-quality Google option for Vietnamese. It costs $30 per 1M characters, and the first 1M characters each month are free, so a full pre-generated phrase library costs ≈$0. Gemini TTS (gemini-3.8-flash-tts / flash-lite-tts) also lists Vietnamese and supports streaming PCM, which suits dynamic phrases such as customer names. For offline fallback, use the phone's own Android TTS (Google Speech Services lists Vietnamese) or, on a server, Piper vi_VN (MIT) or VieNeu-TTS (Apache-2.0). Avoid MMS-TTS-vie in a commercial product because it is non-commercial (CC-BY-NC).

### Cited Findings
**Google Cloud Text-to-Speech: vi-VN voice inventory (official voice list, accessed 2026-11-03)**
- vi-VN has **40 voices in total**. The page shows tiers only as "Premium" or "Standard"; the families below are read from the voice names — [Google Cloud TTS supported voices](https://docs.cloud.google.com/text-to-speech/docs/list-voices-and-types)
  - **Chirp3-HD: 30 voices (Premium).** Female (14): Achernar, Aoede, Autonoe, Callirrhoe, Despina, Erinome, Gacrux, Kore, Laomedeia, Leda, Pulcherrima, Sulafat, Vindemiatrix, Zephyr. Male (16): Achird, Algenib, Algieba, Alnilam, Charon, Enceladus, Fenrir, Iapetus, Orus, Puck, Rasalgethi, Sadachbia, Sadaltager, Schedar, Umbriel, Zubenelgenubi. Voice IDs follow the pattern `vi-VN-Chirp3-HD-<Name>` — [same source](https://docs.cloud.google.com/text-to-speech/docs/list-voices-and-types)
  - **Neural2: 2 voices.** vi-VN-Neural2-A (F), vi-VN-Neural2-D (M) — [same source](https://docs.cloud.google.com/text-to-speech/docs/list-voices-and-types)
  - **WaveNet: 4 voices.** vi-VN-Wavenet-A (F), -B (M), -C (F), -D (M) — [same source](https://docs.cloud.google.com/text-to-speech/docs/list-voices-and-types)
  - **Standard: 4 voices.** vi-VN-Standard-A (F), -B (M), -C (F), -D (M) — [same source](https://docs.cloud.google.com/text-to-speech/docs/list-voices-and-types)
  - **There are no vi-VN Studio or Chirp-HD (v2) voices** — [same source](https://docs.cloud.google.com/text-to-speech/docs/list-voices-and-types)
- (The old URL cloud.google.com/text-to-speech/docs/list-voices-and-types now 301-redirects to docs.cloud.google.com.) — [observed redirect](https://cloud.google.com/text-to-speech/docs/list-voices-and-types)

**Google Cloud TTS pricing**
- **Chirp 3 HD costs US$0.00003 per character (= $30 per 1M characters). The first 1M characters each month are free.** This comes from the official pricing page as surfaced in localized versions in search results; my direct fetch of the English page was truncated — [Google Cloud TTS pricing](https://cloud.google.com/text-to-speech/pricing); [German version of the official page](https://cloud.google.com/text-to-speech/pricing?authuser=2&hl=de)
- Third-party pricing trackers say Gemini-TTS is billed per token rather than per character: about **$1.00 per 1M text input tokens and $20.00 per 1M audio output tokens**. The sources are aggregators, and they do not say which Gemini TTS model these rates apply to — [diyai.io](https://diyai.io/ai-tools/audio-generation/google-cloud-text-to-speech-pricing/); [CostBench](https://costbench.com/software/ai-voice-tools/google-cloud-text-to-speech/). CostBench's price-history data is internally inconsistent — [CostBench price history](https://www.costbench.com/software/ai-voice-tools/google-cloud-text-to-speech/price-history/)

**Gemini speech generation (Gemini API docs, accessed 2026-11-03)**
- The TTS models are **`gemini-3.8-flash-tts` and `gemini-3.8-flash-lite-tts`**. The models table also lists `gemini-3.1-flash-tts-preview` and `gemini-2.5-pro-preview-tts`, both labelled preview. The 3.8 models are not labelled preview, but the page does not state GA explicitly — [Gemini API speech generation](https://aistudio.google.com/docs/speech-generation) (redirected from [ai.google.dev](https://ai.google.dev/gemini-api/docs/speech-generation))
- **Vietnamese is listed as supported for both Gemini 3.8 TTS models** — [same](https://aistudio.google.com/docs/speech-generation)
- Output formats:
  - Unary requests return WAV with a RIFF header: 24 kHz, mono, 16-bit LE PCM.
  - **Streaming (`stream: true`) returns headerless raw PCM (`audio/l16`) chunks as they are synthesized.**
  - μ-law and A-law are available at 8 kHz.
  - `sample_rate` can be 24000, 16000 or 8000 Hz.
  - Source: [same](https://aistudio.google.com/docs/speech-generation)
- Voices and limits:
  - 30 prebuilt voices, plus an "Extended Voice Library" of hundreds more via `GET /v1beta/voices`.
  - Custom voices: up to 200 stateful custom voices per project with a 1-year TTL that resets on use. Stateless voice keys have a 7-day TTL.
  - Multi-speaker requests allow at most 2 speakers.
  - Flash-Lite is positioned for high-volume and voice-agent workloads. **The page gives no latency figures.**
  - Source: [same](https://aistudio.google.com/docs/speech-generation)

**Android on-device TTS (Speech Services by Google)**
- Offline voice data can be downloaded from the Speech Services menu (e.g. on Pixel: Settings > Accessibility > TalkBack > Settings > Text-to-speech settings). Menu labels vary by OEM — [9to5Google](https://9to5google.com/?p=465339)
- A 2022 snapshot of Wikipedia lists **Vietnamese (Vietnam)** among the languages Speech Services supports. This is archived, so current status was not re-confirmed — [Wikipedia snapshot (2022)](https://webcf.waybackmachine.org/web/20220324110701/https://en.wikipedia.org/wiki/Speech_Services)
- Speech Services by Google passed 10 billion Play Store installs (Nov 2021), so it is preinstalled or updatable on most GMS Android phones — [9to5Google](https://9to5google.com/2021/11/09/speech-services-by-google-reaches-10-billion-play-store-downloads/)
- Samsung ships its own separate Vietnamese TTS voice pack for the Samsung TTS engine, with versions dated as late as Nov 2025 — [APKMirror listing](https://www.apkmirror.com/apk/samsung-electronics-co-ltd/samsungtts-vietnamese-female/samsungtts-vietnamese-female-3-1-24-15-release/samsung-tts-vietnamese-default-voice-1-3-1-24-15-android-apk-download/)
- An older Stack Overflow thread notes that no Vietnamese engine was installed by default on older devices. It is outdated, but it shows you should check `isLanguageAvailable(vi-VN)` at runtime — [Stack Overflow archive](https://kiwix.lema.org/stackoverflow.com_en_all_2023-11/questions/7030090/android-vietnamese-text-to-speech)
- Sao Mai Center (a Vietnamese accessibility NGO) has published a Vietnamese speech synthesizer for Android, which is an alternative engine — [Sao Mai Center](https://saomaicenter.org/en/news/technology/vietnamese-speech-synthersizer-android-os)

**Open-source Vietnamese TTS**
- **VieNeu-TTS** (pnnbao97, PyPI package `vieneu`, versions up to 2.7.0):
  - License: **Apache 2.0, so commercial use is OK** — [PyPI vieneu](https://pypi.org/project/vieneu/); [PyPI 1.0.1](https://pypi.org/project/vieneu/1.0.1/); [SourcePulse](https://www.sourcepulse.org/projects/20499710)
  - Generates 24 kHz audio and claims real-time synthesis on CPU or GPU. **GGUF Q4/Q8 builds are the CPU-friendly variants** (Q4 fastest, Q8 better quality), and **only the GGUF models support streaming** — [PyPI vieneu](https://pypi.org/project/vieneu/); [sonusahani.com overview](https://sonusahani.com/blogs/vieneu-tts)
  - Independent speed data is weak. tts.ai reports about 7 s per generation for VieNeu-TTS-v2, with clip length and hardware unspecified — [tts.ai](https://tts.ai/voices/vieneu/)
- **Piper `vi_VN-vais1000-medium`**:
  - An ONNX model of ~63.2 MB in the `rhasspy/piper-voices` repo, which is labelled **MIT** — [HF rhasspy/piper-voices vi_VN](https://huggingface.co/rhasspy/piper-voices/tree/main/vi/vi_VN/vais1000/medium)
  - There is a sherpa-onnx port, `csukuangfj/vits-piper-vi_VN-vais1000-medium`, which is useful for running it on-device on Android — [HF csukuangfj](https://huggingface.co/csukuangfj/vits-piper-vi_VN-vais1000-medium/tree/main)
  - A gated community repo has 14 Vietnamese speakers fine-tuned from vais1000-medium, listed as MIT — [HF quangdung/Piper_checkpoint](https://huggingface.co/quangdung/Piper_checkpoint)
  - The per-voice MODEL_CARD (dataset licence) was not read.
- **facebook/mms-tts-vie**: VITS architecture, **CC-BY-NC 4.0 (non-commercial)**, uploaded 2023-09-01 — [HF facebook/mms-tts-vie](https://huggingface.co/facebook/mms-tts-vie)

### Inferences
- **The phrase library is tiny and essentially free.** 60 tables × ~6 task types (gọi phục vụ, dọn bàn, tính tiền, gọi món, mang nước, khách quen) = 360 clips × ~25 characters ≈ 9,000 characters. That is under 1% of Chirp 3 HD's 1M free characters per month, so you can regenerate it with several voices at no cost.
- **Pre-generate whole phrases rather than splicing "Bàn" + number + task.** Vietnamese tone and prosody across word boundaries sound unnatural when spliced, and 360 MP3/OGG files at 24 kHz total only a few MB to ship in the APK or cache on the phone. Playback is local and instant (no network), which also covers LAN or internet outages.
- **Handle dynamic content (regular-customer names) like this:**
  - Synthesize once, when the regular is enrolled ("Khách quen anh John vừa đến, bàn 5" → cache "Khách quen anh John vừa đến" and append the pre-generated "bàn 5" clip).
  - If a name is new at event time, call Chirp 3 HD or Gemini Flash-Lite TTS in streaming mode.
  - As a last resort, use Android `TextToSpeech` with `Locale("vi","VN")` on the phone.
  - Foreign names such as "John" may be mispronounced by Vietnamese voices; store a phonetic Vietnamese spelling (e.g. "Giôn") in the customer profile.
- **Recommended voice:** pick one Chirp 3 HD vi-VN voice (e.g. a clear female voice such as Kore or Aoede) for every alert, and a different voice or an earcon for "VIP / khách quen" alerts so staff can tell the categories apart by ear. Choose by listening tests; no quality benchmark between vi-VN voices was found.
- **Open-source ranking for commercial deployment:** VieNeu-TTS (Apache-2.0, best quality claim, GGUF CPU) > Piper vi_VN (MIT, very small/fast, robotic but intelligible; runs on-device via sherpa-onnx) > MMS-TTS-vie (non-commercial, so avoid).

### Gaps
- **Standard, WaveNet and Neural2 per-character prices and free tiers were not verified this session** because the pricing page fetch was truncated. They were historically ≈$4 (Standard) and ≈$16 (WaveNet/Neural2) per 1M characters **[unverified / training knowledge]**.
- **Gemini 3.8 TTS pricing per model was not verified on an official page.** The token prices above come from aggregators.
- I found no published latency (time-to-first-byte) figures for Cloud TTS Chirp 3 HD or Gemini TTS for vi-VN. Benchmark from Vietnam; the nearest region is likely asia-southeast1 (Singapore).
- Whether Chirp 3 HD vi-VN supports SSML, speaking-rate controls or custom pronunciations was not checked.
- Current Google Speech Services vi-VN offline availability (2026) was not confirmed on an official Google page. Verify on the target cheap phones (Xiaomi, Samsung A-series, OPPO); some Chinese-market ROMs ship without GMS.
- Not researched this session: F5-TTS Vietnamese fine-tunes and viXTTS (XTTS-v2-based). viXTTS inherits the Coqui Public Model License, which is non-commercial **[unverified / training knowledge]**. No measured real-time factors (RTF) on CPU were found for VieNeu, Piper vi or MMS.

---

## 2. Delivering spoken alerts reliably to Bluetooth earbuds (Android FGS, FCM, LAN WebSocket/MQTT, audio routing, iOS limits, framework choice, reference apps)

### Takeaway
On Android, the reliable pattern is a **foreground service started at shift start while the app is visible**, with the user exempting the app from battery optimization. The service holds a **persistent LAN WebSocket/MQTT connection to an on-prem edge server** and plays pre-cached audio. FCM high-priority is a redundant path for when the internet is up, and every FCM message must post a visible notification or FCM will downgrade it. Bluetooth A2DP adds roughly 100–200 ms more than SCO but sounds much better; for one-way alerts that is fine. iOS is a poor fit: there is no equivalent always-on background audio and socket service, and the Critical Alerts entitlement is restricted by Apple.

### Cited Findings
**FCM priority and Doze (Firebase docs)**
- Normal priority: "When the device is in Doze mode, delivery may be delayed to conserve battery until the device exits doze." — [Firebase: Android message priority](https://firebase.google.com/docs/cloud-messaging/android-message-priority)
- High priority: FCM tries to deliver immediately and can wake a sleeping device, allowing limited processing including very limited network access — [same](https://firebase.google.com/docs/cloud-messaging/android-message-priority)
- **Deprioritization:**
  - If FCM sees a pattern of high-priority messages that do not result in user-facing notifications, it may downgrade them to normal priority or hand them to Google Play services.
  - The pattern is judged over **7 days, separately for each app instance**.
  - If the user disabled the notification permission, none of the app's notifications are posted, which leads to downgrading.
  - Source: [same](https://firebase.google.com/docs/cloud-messaging/android-message-priority)
- **Proxied notifications** are the default on Android 10+ with Play services ≥19054000 for HTTP v1 sends: Play services displays the notification without starting the app. You can opt out per message with `proxy: DENY`, which you need if the app's own code must run and play audio — [same](https://firebase.google.com/docs/cloud-messaging/android-message-priority)
- `onMessageReceived` gets only "several seconds" to process the payload (slightly more for high priority), "only expected to be long enough to immediately render a notification". The docs advise against extra network calls before showing the notification — [same](https://firebase.google.com/docs/cloud-messaging/android-message-priority)

**Foreground service (FGS) background-start rules (Android developer docs)**
- Apps targeting Android 12+ cannot start an FGS from the background, except in listed exemptions; otherwise the call throws `ForegroundServiceStartNotAllowedException` — [Android: FGS background-start restrictions](https://developer.android.com/develop/background-work/services/fgs/restrictions-bg-start)
- Relevant exemptions:
  - The app transitions from a user-visible state (activity).
  - **The app receives a high-priority FCM message.** Check `RemoteMessage.getPriority()==PRIORITY_HIGH`; if FCM downgraded the message, the FGS start throws.
  - **The user turns off battery optimizations for the app.**
  - Companion Device Manager permissions.
  - `SYSTEM_ALERT_WINDOW`; on Android 15+ this also requires a currently visible overlay.
  - Device owner / profile owner apps.
  - Source: [same](https://developer.android.com/develop/background-work/services/fgs/restrictions-bg-start)
- On Android 14+, an FGS that needs while-in-use permissions (camera, mic, location) cannot be *created* from the background even with an exemption. It must be started while an activity is visible — [same](https://developer.android.com/develop/background-work/services/fgs/restrictions-bg-start)

**Bluetooth audio routing**
- A2DP has more latency than SCO, "but not too much more (100–200 ms)". SCO gets its low latency by lowering sample rate and channel count, so it sounds like a mono phone call. A2DP is one-way stereo and cannot capture from the BT mic at the same time — [Unity Vivox: Bluetooth profile comparison](https://docs.unity.com/en-us/vivox-core/developer-guide/android/bluetooth-profile-comparison)
- A patent filing cites HFP latency of ~40 ms. A2DP audio travels over L2CAP with asynchronous packet scheduling — [USPTO patent PDF](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12425684)
- On Linux/PulseAudio, the configured latency constants (A2DP 25 ms, SCO 125 ms) differed from measured latency (~25 ms for both). Configured and real delay can diverge — [pulseaudio-discuss](https://lists.freedesktop.org/archives/pulseaudio-discuss/2016-June/026316.html)

**iOS limitations**
- Critical Alerts require a **special entitlement issued by Apple** (`com.apple.developer.usernotifications.critical-alerts`). Developers report it appears as a capability switch in the developer console once approved — [Apple Developer Forums](https://developer.apple.com/forums/thread/794822); [B4X forum](https://www.b4x.com/android/forum/threads/which-entitlement-for-critical-alerts.145219/)
- Apple rejects Critical Alert requests outside a "very restricted set of purposes"; an alarm-app developer reported a rejection — [r/iOSProgramming via redlib](https://redlib.hbubli.cc/r/iOSProgramming/comments/1h7x53c/apple_wont_allow_proper_3rd_party_alarm_apps/mk123cv)

**Reference product: push-to-talk for hospitality**
- **Relay** (relaypro.com) is a screenless push-to-talk device plus app that replaces two-way radios in hotels:
  - 1:1 calls, group channels and broadcast.
  - Automatic Wi-Fi ↔ cellular failover.
  - A panic button (5 quick presses) that sends the sender's name and indoor/outdoor location to responders.
  - Live translation, so each person speaks and hears in their own language.
  - Source: [Relay for Hospitality](https://relaypro.com/solutions/hospitality/); [Hospitality Tech: panic button](https://hospitalitytech.com/relay-adds-panic-button-feature)
- Relay Pro reached 100+ hotel properties within a month of its hospitality launch. Kinseth Hospitality (hotel and restaurant brands) made Relay its exclusive alert-device partner. These figures come from trade press relaying vendor statements — [Hotel Management](https://www.hotelmanagement.net/tech/relay-launches-pro-version-for-active-workers); [Hospitality Upgrade](https://www.hospitalityupgrade.com/partners/relay)
- Pryme sells a wireless PTT badge and headset adapter for hotel staff (a hardware-button alternative to touching the phone) — [Hotel Management: Pryme](https://www.hotelmanagement.net/tech/pryme-launches-wireless-ptt-badge-and-enhanced-headset-adapter)

### Inferences
- **Primary path: LAN.** Run an edge server on a laptop or mini-PC at the counter (the camera inference box). It runs a WebSocket server (or Mosquitto MQTT, QoS 1, a topic per staff member such as `staff/<id>/alerts`) on the restaurant Wi-Fi, so it keeps working when the internet is down. LAN round-trip is typically tens of milliseconds **[unverified / training knowledge]**.
- **On the phone:**
  - Run a foreground service with an ongoing notification ("Easy FnB đang trực ca").
  - Start it from the app's activity at clock-in, which uses the user-visible-state exemption.
  - Ask the user to disable battery optimization. This is itself an FGS exemption and reduces OEM killing (Xiaomi/OPPO/Vivo have aggressive task killers **[unverified / training knowledge]**).
  - Keep the socket alive with ping every 15–30 s and auto-reconnect with backoff.
- **Redundant path: FCM.** When the internet is up, the edge server also sends an FCM HTTP v1 **data + notification** message at high priority (`android.priority=HIGH`, `proxy: DENY`, short TTL ≈ 60 s). Every message must post a visible notification so FCM does not downgrade the app (7-day rule).
  - Deduplicate by `alert_id` on the phone so the alert plays once from whichever path arrives first.
  - Because `onMessageReceived` has only a few seconds, play only **pre-cached** audio there; do not fetch TTS over the network.
- **Audio:**
  - Use `MediaPlayer`/`ExoPlayer` with `AudioAttributes` usage `USAGE_ASSISTANCE_NAVIGATION_GUIDANCE` (or `USAGE_NOTIFICATION_EVENT`), request `AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK`, and let the system route over A2DP.
  - Avoid SCO/HFP: it needs `startBluetoothSco()`/a communication device, sounds phone-grade, and interrupts music.
  - Prepend a ~300–500 ms earcon (a distinct chime per priority) because many earbuds drop the first few hundred ms after their audio link idles **[unverified / training knowledge; test on target earbuds]**.
  - Use `setWakeMode(PARTIAL_WAKE_LOCK)` so playback works with the screen locked.
  - Repeat the alert once after N seconds if the camera has not yet confirmed arrival.
- **Total latency budget:** camera event detection (~0.3–1 s) + dispatch (<10 ms) + LAN push (<100 ms) + local playback start with A2DP (~150–300 ms) ≈ **under 1.5 s** end to end. This is a design estimate, not measured.
- **Framework for 48 h:**
  - **Native Kotlin** (or Flutter with a small Kotlin platform channel) is lowest-risk for FGS + audio focus + TTS + battery-optimization intents.
  - React Native and Flutter can do it, but the FGS, audio-focus and wake-lock code ends up native anyway.
  - The staff app needs very little UI (login, on-shift toggle, last alerts), so a single-Activity Kotlin/Compose app is realistic for one person in 48 h. This is a judgment call; no framework comparison sources were gathered.
- **Why Android:** cheap phones, sideloadable APK, FGS + persistent socket allowed, and no entitlement gatekeeping. iOS can only reliably alert via APNs notification sounds, and getting Critical Alerts approved for restaurant paging is unlikely.

### Gaps
- No measured FCM high-priority delivery latency (p50/p95) was found on official pages; Firebase gives no numbers.
- The exact Android 14/15 FGS type to declare for a "persistent socket + play alert audio" service was not verified (candidates: `mediaPlayback`, `connectedDevice`, `specialUse` with Play Console justification, `dataSync`, which has time limits on Android 15). Check the [FGS types page](https://developer.android.com/develop/background-work/services/fgs/service-types).
- No Android-specific measurements were found for A2DP wake-up and clipping on cheap TWS earbuds.
- iOS background-audio and notification-sound duration limits (e.g. the 30 s custom sound cap) were not verified against Apple docs this session **[training knowledge]**.
- No sources were gathered on dedicated restaurant earbud-alert apps beyond Relay and Pryme. Zello and similar walkie-talkie apps were not researched.

---

## 3. Real-time task assignment / dispatch algorithms (OR-Tools, Hungarian, greedy, online reassignment, escalation, fairness, presence-based ack)

### Takeaway
For one restaurant (≤~20 staff, ≤~10 open tasks), use **greedy priority dispatch with a weighted cost function for each new event**, plus an **optional micro-batch Hungarian / OR-Tools LinearSumAssignment** when several events land within about 1 s. Acknowledgement is **implicit**: the cameras confirm that the assigned person reached the table. Escalation is **timeout-based reassignment**, copied from nurse-call systems: first person → timeout → next best (or broadcast to role) → manager, with "accept-once" dismissal for everyone else.

### Cited Findings
- **OR-Tools Linear Sum Assignment solver:**
  - A specialized solver for simple assignment, "may be faster than the MIP or CP-SAT solver". However, "MIP and CP-SAT solvers can handle a much wider array of problems… in most cases they are the best option" — [OR-Tools: Linear Sum Assignment Solver](https://developers.google.com/optimization/assignment/linear_assignment)
  - The docs' toy example solves in **~0.000147 s** (total cost 265).
  - It returns a POSSIBLE_OVERFLOW status for very large integer costs, so costs must be integers within range.
  - Source: [same](https://developers.google.com/optimization/assignment/linear_assignment)
- **Nurse-call escalation patterns:**
  - Spok Go Nurse Call Flow: the alert goes to the first designated recipient, then to the next after a set interval, cycling until someone accepts. **A decline is treated like a timeout** and moves the alert on — [Spok: Nurse Call Flows](https://knowledge.spok.com/Spok_Products/Spok_Go/Workflows/Workflows_Admin_Guide/002Working_with_Nurse_Call_Flows); [Spok: Managing Alerts and Tasks](https://knowledge.spok.com/Spok_Products/Spok_Go/Messaging/iOS/050Alerts)
  - Ascom Unite Connect for Nurse Call supports **three levels of escalation** to predefined caregivers when the primary cannot respond — [Ascom product sheet](https://epiprod.ascom.com/globalassets/assets/global/unite/unite-connect-nurse-call-product-sheet-00909-07-enx.pdf)
  - A patent describes escalating primary caregiver → designated secondary → **caregiver closest in proximity to the room** — [US patent 11083419 (PDF)](https://patentimages.storage.googleapis.com/e6/6b/3d/e89326f39dba04/US11083419.pdf)
  - Another patent marks caregivers unavailable based on role, qualification or distance — [US10916119B2 "caregiver availability determination"](https://ipiq.io/patents/2676133)
  - Group-role escalation: the alert goes to everyone in the role at once, and **when one person accepts, the alert is dismissed for the others** — [Spok: Managing Alerts and Tasks](https://knowledge.spok.com/Spok_Products/Spok_Go/Messaging/iOS/050Alerts)
  - A human stays in the loop: the dispatch board suggests a responder, and the nurse-in-charge can dispatch or override — [Presencis nurse-call demo](https://cdn.presencis.com/demo/healthcare/nurse-call)
  - These are vendor and patent sources; timeout values and tier counts are facility-configured, not a standard — [Critical Alert workflow designer](https://criticalalert.com/?p=4953)

### Inferences
- **Cost function (lower is better)** for staff *s*, task *t*:
  `cost = w_d·walk_dist(s,t)/v + w_b·busy_penalty(s) + w_z·(zone(s)≠zone(t)) + w_r·role_mismatch(s,t)·BIG + w_l·open_tasks(s) + w_f·tasks_last_30min(s) − w_a·affinity(s,t)`
  - **Walk distance:** distance on the floor plan from the camera position (Euclidean is OK; use an aisle graph if there are obstacles).
  - **Busy penalty:** high if the staff member is currently at another table serving, or carrying a tray. Busy status can be inferred from the camera (stationary at a table for more than X s) or from an open-task list.
  - **Role mismatch:** a hard constraint. "Wants the bill" → cashier or senior waiter; "needs clearing" → busser/runner; "regular customer arrived" → the floor manager or the waiter who served the customer last (affinity).
  - **Fairness:** penalize recent load (`tasks_last_30min`) to spread work. Optionally add a small random tiebreak.
- **Online loop:**
  1. Event arrives. Dedup it: same table + same type within 60 s = same task, so the "raised hand" gesture firing repeatedly does not create duplicates.
  2. Assign with greedy argmin over eligible staff, sorted by task priority (bill / VIP > call > clear).
  3. If ≥2 tasks are pending within 1 s, solve a rectangular assignment with `linear_sum_assignment` (OR-Tools `SimpleLinearSumAssignment` or `scipy.optimize.linear_sum_assignment`). Assignments for ~20×10 matrices take microseconds.
  4. CP-SAT is only worth it if you add constraints such as "at most 1 active task per person" plus time windows. That is overkill for 48 h.
- **Presence-based acknowledgement:**
  - The task becomes `ARRIVED` when the assigned staff track is within radius *r* (~1–1.5 m, or inside the table's floor polygon buffer) for ≥2 s. It becomes `DONE` when the trigger clears (the hand goes down, the table is cleared) or when the staff member leaves after ≥T s.
  - If a *different* staff member arrives first, mark the task done by them and cancel the alert for the assignee. Optionally play "Bàn 7 đã có người phục vụ" to the assignee, which gives "accept-once" semantics.
- **Escalation ladder (configurable):**
  - T0 = assign best staff member and play the alert.
  - T0 + 20 s, no movement toward the table (distance not decreasing): replay the alert.
  - T0 + 45 s: reassign to the 2nd best and notify both.
  - T0 + 90 s: broadcast to the role and flash red on the dashboard.
  - T0 + 180 s: alert the manager.
  - "Moving toward the table" is a useful soft acknowledgement that the camera can detect.
- **Hysteresis and stickiness:** do not reassign a task just because someone else becomes marginally closer. Only reassign on timeout, or when the cost gap exceeds a threshold, to avoid ping-ponging alerts between earbuds.
- **Ride-hailing analogy:** batch matching in short windows plus reassignment is a standard idea, but no ride-hailing or warehouse dispatch sources were gathered this session (see Gaps).

### Gaps
- No primary sources were gathered on ride-hailing batched matching (e.g. Uber/Grab dispatch windows) or warehouse task interleaving. Those claims are from training knowledge only.
- No published restaurant-specific benchmarks were found for response-time SLAs, e.g. a target time to answer a raised hand.
- Recommended nurse-call timeout values are facility-specific; no canonical numbers were found.

---

## 4. Indoor localization of staff: cameras (tracking + re-ID + homography) vs BLE beacons vs UWB; staff identification

### Takeaway
Since the restaurant already has cameras for event detection, **camera-based localization** is the zero-hardware choice: person detection + multi-object tracking + foot-point homography onto the floor plan. Table-level accuracy (about 1 m) is enough. Its weak points are **identity** (which person is which staff member) and occlusion. BLE RSSI beacons give only ~1–5 m. UWB gives ~10–30 cm but needs anchors and tags. For the hackathon, use cameras plus a simple identity cue (uniform colour or name badge, or face enrolment at clock-in). Treat BLE as an optional identity/zone hint, not the main position source.

### Cited Findings
- **BLE:**
  - RSSI-based BLE positioning typically gives **~1–5 m** accuracy, because signal strength is a poor indicator of distance.
  - BLE 5.1 angle-of-arrival can reach sub-meter accuracy, but needs denser and more complex infrastructure.
  - Independent real-world data on BLE Channel Sounding is scarce.
  - Sources: [Mapsted: UWB vs BLE](https://mapsted.com/blog/uwb-vs-ble-which-offers-more-accuracy); [Hubble: UWB vs BLE for RTLS](https://hubble.com/community/comparisons/uwb-vs-ble-for-real-time-location-when-centimeter-accuracy-is-worth-the-battery-and-bom-hit/); [Electronic Design](https://www.electronicdesign.com/technologies/communications/article/21800581/whats-the-difference-between-measuring-location-by-uwb-wi-fi-and-bluetooth)
- **UWB:**
  - Vendor figures are **~10–30 cm**, with some citing 5–10 cm — [Pozyx: UWB vs other technologies](https://pozyx.io/newsroom/uwb-versus-other-technologies)
  - An academic study on mobile robots found UWB was **88.05% more accurate than BLE** and 93.27% more accurate than Wi-Fi for tracking mobile targets — [PMC11991048: experimental evaluation of indoor localization](https://pmc.ncbi.nlm.nih.gov/articles/PMC11991048)
- **Cameras:**
  - Obstacles and blind spots reduce the accuracy of camera-based systems — [PMC11991048](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11991048/)
  - Cameras raise privacy concerns and struggle to tie each tracked object to an identity, whereas UWB tags carry IDs. This point comes from a UWB vendor — [Pozyx](https://pozyx.io/newsroom/uwb-versus-other-technologies)

### Inferences
- **Camera pipeline (48 h):**
  1. Person detection with YOLO (Ultralytics, AGPL-3.0 **[licence: training knowledge]**). For a permissive licence, use RT-DETR or YOLOX (Apache-2.0).
  2. Tracking with ByteTrack or BoT-SORT; Ultralytics has built-in `model.track()`.
  3. Take the bottom-centre of each bounding box (foot point) and project it to the floor plan with a 3×3 homography from `cv2.findHomography`, using four or more floor points per camera that you measure or mark with tape.
  4. Map floor (x, y) to the nearest table polygon or zone.
  - Table spacing in Vietnamese restaurants is often 1–2 m, and the homography error at the foot point is usually under ~0.5 m in a well-calibrated overhead or high-angle view **[training knowledge; measure on site]**.
- **Staff vs customer, and which staff member:**
  - **Easiest:** distinct uniform colour or apron, classified by HSV histogram or a tiny classifier crop. Add a large printed number or ArUco/AprilTag marker on the back or shoulder of the uniform so cameras can read the staff ID. This is cheap, robust and avoids face biometrics.
  - **Medium:** at clock-in, the staff member stands in front of the counter camera to enrol a re-ID embedding (OSNet/FastReID) for the shift, and the system matches tracks to embeddings.
  - **Optional:** face recognition (InsightFace etc.). This needs consent and raises privacy and legal issues; see the next point.
- **Vietnam's personal data rules** (Decree 13/2023/ND-CP and the Personal Data Protection Law effective 2026) likely classify biometric data as sensitive **[unverified / training knowledge]**, so uniform markers are lower risk than faces for staff identification.
- **Hybrid fallback:** the staff phone (which already exists) can scan BLE beacons placed per zone (cheap ESP32 or iBeacon tags) to provide a coarse zone and identity. This disambiguates camera tracks after occlusion. It is not needed for a demo.
- **Multi-camera:** with two or more cameras, fuse floor-plane positions (nearest-neighbour association across cameras in floor coordinates). Re-ID across cameras is the hardest part; the uniform marker solves it cheaply.

### Gaps
- I found no published accuracy figures for camera-based person localization in restaurant-like scenes (MOT/re-ID benchmark numbers such as MOTA/IDF1 were not gathered).
- No sources were gathered on Vietnam's 2026 data-protection rules for workplace video and biometrics. A legal check is needed.
- Ultralytics licence terms (AGPL-3.0 / enterprise) were not re-verified this session.

---

## 5. Shared real-time dashboard (iPad/TV at the counter): tech choice, kiosk mode, offline-first local operation

### Takeaway
No sources were fetched for this question this session, so everything below is design inference from training knowledge and must be verified. For an unreliable internet connection, serve the dashboard **from the same on-prem edge server** (FastAPI/Node + WebSocket or Server-Sent Events) over the LAN. Optionally mirror state to Firebase (Firestore / Realtime Database) for remote viewing when the internet is up. Run it full-screen in a kiosk browser: iPad Guided Access, or Fully Kiosk Browser on an Android TV box / cheap Android tablet.

### Cited Findings
- No sources were gathered this session; see Gaps. (Relay's dashboard, which receives panic alerts with staff location, is a reference for the "dashboard + wearable" pattern — [Relay for Hospitality](https://relaypro.com/solutions/hospitality/).)

### Inferences
- **LAN-first (recommended):**
  - The edge server keeps the authoritative task state in memory or SQLite and pushes diffs over WebSocket or SSE to the dashboard and the staff apps. The same socket server can serve both.
  - The dashboard is a single-page web app showing a floor-plan SVG with tables coloured by state (red = waiting, amber = assigned, green = staff arrived), live staff dots from camera tracking, the task queue with timers, and the escalation level.
  - Plain WebSocket or SSE keeps working with no internet, which matches the "LAN may be unreliable" constraint better than a cloud database. If the Wi-Fi itself is flaky, put the edge server and access point on a dedicated router or SSID for staff devices and give the server a static IP.
- **Firebase option** (the team prefers Google): Firestore and Realtime Database listeners give near-real-time sync and offline caching in the client SDK. However, the source of truth would be in the cloud, so cross-device sync stops during an internet outage. Use Firebase only as a mirror for owner and remote views and analytics **[training knowledge]**.
  - Supabase Realtime (Postgres changes over WebSocket) can be self-hosted on the LAN, but it adds Docker/Postgres overhead for a 48 h build **[training knowledge]**.
- **Kiosk:**
  - iPad: Settings → Accessibility → Guided Access locks to one app (Safari or a home-screen web app); set Auto-Lock to Never.
  - Android TV / tablet: Fully Kiosk Browser, or Chrome in a pinned-screen mode. A TV on HDMI from a mini-PC running Chromium `--kiosk` also works.
  - All of these are **[training knowledge]**.
- **Make the dashboard double as a fallback** for staff without an earbud: optional audible chime on the counter TV, and a big table number.

### Gaps
- Not verified this session: Firestore/RTDB latency numbers, offline-persistence behaviour across tabs, Supabase Realtime limits, iPad Guided Access specifics, Android kiosk apps and their licences/prices.

---

## 6. Existing restaurant staff paging / notification products (wireless calling systems, team comms apps, POS-integrated alerts, Vietnam market)

### Takeaway
The incumbent "low-tech" answer is a **wireless calling system**: table buttons (Call / Pay / Cancel / Order) plus wrist-watch receivers that vibrate and show the table number. They cost a few dollars to a few hundred, with no staff-selection intelligence. Vietnamese POS suites (KiotViet, iPOS/FABi, Sapo FnB) focus on order → kitchen → "dish ready" notifications on staff handhelds, not on camera-triggered, location-aware dispatch. Easy FnB's differentiators are: no button needed (vision), choosing the *best* staff member, spoken audio, and auto-confirmation by presence.

### Cited Findings
- **Retekess and other wireless calling systems:**
  - Table call buttons (e.g. T117) with **4 functions: Call, Cancel, Pay, Order**, or a 3-key Call/Pay/Cancel button.
  - Wrist-watch receivers (TD110, TD112, TD113) display the table number.
  - Listings claim up to 999 channels and ~80 m range, with water resistance from IP54 up to IPX67.
  - Sources: [Retekess TD112 + T117](https://www.retekess.com/td112-watch-receiver-with-t117-call-buttons); [Retekess TD110 + T117](https://retekess.com/waiter-pager-td110-watch-t117-bell); [Retekess service call system](https://www.retekess.com/service-call-system); [Retekess TD113 listing](https://www.desertcart.ma/products/684465080-retekess-td113-staff-pager-system-wireless-calling-system-ipx67-waterproof)
  - Marketplace prices range from about $1.80 for a single basic unit to ~$385 for larger kits. These are marketing claims with no independent reviews found — [Alibaba restaurant calling device](https://electronics.alibaba.com/product/restaurant-calling-device); [Fruugo watch + buttons kit](https://www.fruugo.co.nz/restaurant-pager-system-wireless-1-watch-and-4-buttons/p-439305729-921038153)
  - Typical setup: one call button on each table and a wrist pager on each waiter — [The Caterer: wristwatch-style pager](https://www.thecaterer.com/archive/wristwatch-style-pager)
- **KiotViet Nhân viên Nhà hàng** (iOS/Android staff app): waiters take orders on a phone or tablet, the order goes to the kitchen automatically, and the app shows which dishes are cooking or done for each table — [App Store: KiotViet Nhân viên Nhà hàng](https://apps.apple.com/vn/app/id1320788126)
- **iPOS PDA** (handheld order device): orders are taken on the handheld and synced instantly to kitchen, bar and cashier. iPOS also offers an O2O e-menu (customer self-order) and a CRM — [iPOS PDA](https://ipos.vn/en/san-pham/ipos-pda-thiet-bi-cam-tay-tich-hop-chuc-nang-order/); [iPOS O2O menu](https://ipos.vn/en/san-pham/menu-dien-tu-ipos-o2o/); [iPOS CRM](https://ipos.vn/en/san-pham/phan-mem-cham-soc-khach-hang-ipos-crm/); FABi Order app — [App Store](https://apps.apple.com/vn/app/id6748251910)
- **Sapo FnB:** when the kitchen marks one or all dishes done, a notification is sent immediately to the staff member — [Sapo FnB app](https://www.sapo.vn/app-sapo-fnb-quan-ly.html?campaign=dvkh); [Sapo FnB launch](https://www.sapo.vn/blog/ra-mat-sapo-fnb-phan-mem-quan-ly-nha-hang-quan-cafe/)
- **Relay** (hospitality push-to-talk, panic alerts with location, translation) — see Q2 — [Relay for Hospitality](https://relaypro.com/solutions/hospitality/)

### Inferences
- **Copy the button semantics** into camera event types:
  - Raise hand = "Call"
  - Bill gesture or request = "Pay"
  - Staff presence = "Cancel/ack" (automatic)
  - Plus camera-only events: "table needs clearing" and "VIP arrived".
- **Copy the watch UX:** a short vibration plus a big table number. A Wear OS watch, or even a $10 Retekess watch driven by a 433 MHz transmitter from the edge server, could be a fallback for staff without earbuds. That idea is speculative; there are no sources on Retekess interfacing.
- **Integration:** a real deployment would need POS hooks (KiotViet, iPOS, Sapo) so that "bill requested" pre-opens the bill and "dish ready" from the kitchen becomes another dispatchable task. KiotViet has a public API **[unverified]**; iPOS/Sapo API availability was not checked.
- **Hackathon pitch angle:** button pagers tell *everyone* that table 7 called. Easy FnB tells the *right* person, by voice, and closes the loop automatically.

### Gaps
- Not verified: Toast's staff-alert features; Vietnamese wireless calling vendors (e.g. local distributors of "chuông gọi phục vụ"); KiotViet, iPOS and Sapo open API capabilities for pushing events.
- I found no Vietnamese product doing camera-triggered staff dispatch (absence of evidence, not a confirmed gap in the market).

---

## 7. Recommended design for a 48-hour prototype (synthesis of Q1–Q6)

### Takeaway
Build it **LAN-first**:
- **One edge server** (laptop with GPU or a decent CPU) runs camera inference, a dispatcher and a WebSocket hub.
- **A native Android staff app** runs a foreground service that holds the socket and plays **pre-generated Chirp 3 HD Vietnamese clips** over A2DP earbuds.
- **A web dashboard** is served from the same box.
- FCM high-priority and cloud TTS are bonuses when the internet is up, not dependencies.

### Cited Findings
- Chirp 3 HD has 30 vi-VN voices, costs $30 per 1M characters, and the first 1M characters each month are free — [voices](https://docs.cloud.google.com/text-to-speech/docs/list-voices-and-types); [pricing](https://cloud.google.com/text-to-speech/pricing?authuser=2&hl=de)
- Gemini 3.8 Flash(-Lite) TTS supports Vietnamese and streams 24 kHz PCM — [Gemini speech generation](https://aistudio.google.com/docs/speech-generation)
- An FGS can be started from the background on a high-priority FCM message or after battery optimization is disabled. FCM downgrades high-priority messages that do not show notifications — [Android FGS restrictions](https://developer.android.com/develop/background-work/services/fgs/restrictions-bg-start); [FCM priority](https://firebase.google.com/docs/cloud-messaging/android-message-priority)
- A2DP adds ~100–200 ms over SCO — [Unity Vivox](https://docs.unity.com/en-us/vivox-core/developer-guide/android/bluetooth-profile-comparison)
- OR-Tools LinearSumAssignment solves small problems in sub-millisecond time — [OR-Tools](https://developers.google.com/optimization/assignment/linear_assignment)
- Nurse-call escalation uses timeouts, the next recipient, role broadcast and accept-once — [Spok](https://knowledge.spok.com/Spok_Products/Spok_Go/Messaging/iOS/050Alerts)

### Inferences
- **Architecture (all on restaurant Wi-Fi):**
  1. `vision/`: Python, YOLO + ByteTrack + homography. It emits `{type, table_id, ts, conf}` events and `{staff_id, x, y, state}` positions at 5–10 Hz.
  2. `dispatcher/`: Python asyncio. It does dedup, greedy cost-based assignment with micro-batch `linear_sum_assignment`, the escalation state machine, and presence-based acknowledgement.
  3. `hub/`: FastAPI WebSocket, with topics per staff member and for the dashboard (or Mosquitto MQTT). SQLite stores the event log for the demo replay and KPIs (time-to-arrive per task).
  4. `staff-app/`: Kotlin.
     - Login picks a staff ID, and an "On shift" toggle starts the FGS (from the visible activity), requests `POST_NOTIFICATIONS` and a battery-optimization exemption.
     - It holds a WebSocket with auto-reconnect and plays bundled OGG clips keyed by `phrase_id` (e.g. `call_t07`), falling back to `TextToSpeech(vi-VN)` for unknown text.
     - It shows a heads-up notification for each alert.
  5. `dashboard/`: a single HTML/JS page with a floor-plan SVG, the live task list and timers, served by the hub. It runs in Guided Access on an iPad or in kiosk Chromium on a TV.
  6. `tts-build/`: a one-off script that loops over tables × task types and calls Cloud TTS `vi-VN-Chirp3-HD-<Voice>` to write OGG/MP3 files bundled into the APK. Optionally it calls Gemini TTS for a regular customer's greeting at enrolment.
- **Message schema:**
  `{alert_id, task_id, staff_id, phrase_id, text_vi:"Bàn 7 gọi phục vụ", priority, table_id, created_ts, ttl_s}`
  The phone acknowledges receipt (`delivered`) and playback (`played`) so the dashboard can show that the alert reached the person. The camera supplies `arrived`.
- **Team split (4 people × 48 h):**
  - A: vision and floor homography
  - B: dispatcher, escalation and hub
  - C: Android staff app (FGS, audio, socket)
  - D: dashboard, TTS library generation, demo script and slides
- **Demo risks and mitigations:**
  - BT earbud clipping: add an earcon prefix.
  - OEM battery killer: whitelist the app and use the FGS.
  - Wi-Fi flakiness: bring your own travel router.
  - Gesture false positives: require ≥1 s hold and a dedup window.
  - Identity: coloured vests or number tags.
- **Phase 2 / real deployment:**
  - FCM redundancy.
  - Per-restaurant floor-plan editor.
  - POS integration (bill ready, dish ready → tasks).
  - Fairness analytics (tasks per staff member per hour).
  - Privacy compliance review for video analytics in Vietnam.
  - A cheap Wear OS or vibration-watch fallback.

### Gaps
- End-to-end latency figures above are design estimates; nothing was measured.
- Behaviour on specific cheap Android phones (Xiaomi Redmi, Samsung A0x, OPPO A-series) and TWS earbuds needs on-device testing.
