# Google Cloud / Gemini stack for Easy FnB (GDG DevFest MienTrung 2026 Mini Hackathon, Đà Nẵng, 14/11/2026)

All pages below were read on **2026-11-04**. Most official pages show no "last updated" date, so the read date is the reference. The fetch tool summarised the official pricing and model pages; check exact numbers on the pages before a pitch slide relies on them.

**URLs have moved since 2025. Old links and tutorials redirect or are stale:**
- `ai.google.dev/gemini-api/docs/*` now redirects (301) to `aistudio.google.com/docs/*`.
- `cloud.google.com/run/docs/*` now redirects to `docs.cloud.google.com/run/docs/*`.
- `google.github.io/adk-docs` now redirects to `adk.dev`.
- Vertex AI was renamed **Gemini Enterprise Agent Platform** on 22 Apr 2026, and Vertex AI Agent Engine is now **Agent Runtime** ([name changes](https://docs.cloud.google.com/gemini-enterprise-agent-platform/vertex-ai-name-changes), [release notes](https://docs.cloud.google.com/gemini-enterprise-agent-platform/release-notes)).

---

## 1. Gemini model lineup (Nov 2026), prices, image/video token accounting, caching, batch

### Takeaway
As of 4 Nov 2026 the lineup is:
- **Flagship:** `gemini-4-argon`
- **Flash:** `gemini-3.8-flash` (stable, Sept 2026)
- **Flash-Lite:** `gemini-3.5-flash-lite` and `gemini-3.1-flash-lite`
- **Pro preview:** `gemini-3.1-pro-preview`
- **Live API:** `gemini-3.8-live`

For Easy FnB:
- Use **Flash-Lite** for the high-volume camera checks.
- Use **3.8 Flash** for the owner agent and the shift summary.
- Batch and Flex cost half. Gemini 3 video costs about **70 tokens per frame** at low/medium resolution.
- **Prices are about to rise.** Argon doubles on 1 Dec 2026 and 3.8 Flash doubles on 1 Jan 2027.
- **Avoid 2.5 Flash and 2.5 Pro.** Both are deprecated, and from 1 Dec 2026 their requests are re-routed to other models.

### Cited Findings
**Model codes and status** ([Models](https://aistudio.google.com/docs/models)):
- `gemini-4-argon` is the flagship, with 1M context and text, image, audio, video and PDF input.
- New: `gemini-3.8-flash`, `gemini-3.8-live`, `gemini-3.8-live-extended-thinking`, `gemini-3.8-flash-tts`, `gemini-3.8-flash-lite-tts`.
- Stable: `gemini-3.6-flash` (previous-generation Flash), `gemini-3.5-flash-lite` ("fastest 3.5 model"), `gemini-3.1-flash-lite` ("cost-efficient multimodal"), `gemini-3.5-transcribe` / `gemini-3.5-transcribe-live`.
- Preview: `gemini-3-flash-preview`, `gemini-3.1-pro-preview`.
- Legacy preview: `gemini-3.1-flash-live-preview`.
- Shut down: `gemini-2.0-flash`, `gemini-2.0-flash-lite`, `gemini-3-pro-preview`, `gemini-3.1-flash-lite-preview`.
- `gemini-2.5-flash` is deprecated; its requests route to `gemini-3.5-flash-lite` from 1 Dec 2026.
- `gemini-2.5-pro` is deprecated; its requests route to `gemini-3.8-flash` from 1 Dec 2026.
- `gemini-2.5-flash-lite` is served only to existing users.

**`gemini-3.8-flash` model card** ([model card](https://aistudio.google.com/docs/models/gemini-3.8-flash)):
- Latest update Sept 2026. Input limit 1,048,576 tokens, output limit 65,536.
- Input: text, image, video, audio, PDF. Output: text.
- Supports batch, caching, code execution, computer use, file search, Flex, function calling, Maps and Search grounding, priority inference, structured outputs and URL context.
- Thinking levels: low, medium and high. The "minimal" level returns an error.
- **No Live API.**

**Paid-tier prices, USD per 1M tokens, Standard tier** ([Pricing](https://aistudio.google.com/docs/pricing)). "→" marks a scheduled change.

| Model | Input | Output | Cache read | Cache storage | Batch/Flex | Free tier? |
|---|---|---|---|---|---|---|
| `gemini-4-argon` | $2.00 → **$4.00 from 1 Dec 2026** | $10 → $20 | $0.10 → $0.20 (implicit only) | – | $1.00/$5 → $2/$10 | No |
| `gemini-3.8-flash` | $0.75 → **$1.50 from 1 Jan 2027** | $3.75 → $7.50 | $0.075 → $0.15 | $0.50 → $1.00 /1M tok/hour | $0.375/$1.875 → $0.75/$3.75 | Yes |
| `gemini-3.6-flash` | same as 3.8 Flash | same | same | same | same | Yes |
| `gemini-3.5-flash-lite` | $0.30 (all modalities) | $2.50 | $0.03 | $1.00/hour | Batch $0.15/$1.25; Flex $0.15/$1.25 (cache $0.02) | Yes |
| `gemini-3.1-flash-lite` | $0.25 (text/img/video), $0.50 (audio) | $1.50 | $0.025 | $1.00/hour | $0.125/$0.75 | Not stated on the pricing page; a third party lists free limits (see §2) |
| `gemini-3.1-pro-preview` | $2.00 (≤200k) / $4.00 (>200k) | $12 / $18 | $0.20 / $0.40 | $4.50/hour | $1.00/$6 | No |
| `gemini-3-flash-preview` | $0.50 (audio $1.00) | $3.00 | $0.05 | $1.00/hour | $0.25/$1.50 | Yes |

**Other pricing notes:**
- Priority tier costs about 1.8× Standard.
- A "Contributor" tier costs about half of Standard on several models.

**Grounding with Google Search:**
- 5,000 requests a month are free, shared across all Gemini 3+ models. After that it costs $14 per 1,000. The default cap is 1,500 a day ([Pricing](https://aistudio.google.com/docs/pricing)).
- URL context is billed as input tokens.

**Media resolution** ([Media resolution](https://aistudio.google.com/docs/media-resolution)):
- **Images, Gemini 4 and 3:** `unspecified` (the default) costs 1,120 tokens per image, `low` 280, `medium` 560, `high` 1,120, `ultra_high` 2,240. `ultra_high` can only be set on an individual content item.
- **Video frames:** 70 tokens each at low, medium or unspecified, and 280 at high.
- **Audio:** fixed at 25 tokens per second.
- **How to set it:** add a `resolution` field to each media part.
- **Recommendations:** `high` for image analysis; `low` or `medium` for video action recognition; `high` for small text in video.

**Video understanding** ([Video understanding](https://aistudio.google.com/docs/video-understanding)):
- **Default sampling** is 1 fps. Custom `fps` (e.g. 0.5) and clipping with `start_offset`/`end_offset` go in the `processing` object and work only in "static" mode.
- **Ways to pass video:**
  - **File API:** files up to 2 GB on the free tier, 20 GB paid.
  - **Inline:** under 100 MB. Another section of the same page says under 20 MB total request.
  - **Cloud Storage registration:** up to 2 GB per file.
  - **YouTube:** public videos only, in preview.
- **Length:** about 3 hours of video at low resolution, or 1 hour at high, with 1M context.
- **Timestamps:** query in MM:SS format.
- **Token conflict:** this page also states about 100 tokens per second (low) or 300 (high), frames at 66 or 258 tokens, and audio at 32 tokens per second. These look like legacy Gemini 2.5 figures and conflict with the media-resolution page (70 tokens per frame, 25 tokens per second of audio for Gemini 3/4). [Video page](https://aistudio.google.com/docs/video-understanding) vs [media-resolution page](https://aistudio.google.com/docs/media-resolution).
- **YouTube on the free tier:** at most 8 hours of YouTube video a day. Up to 10 videos per request on Gemini 2.5+.

**Files API** ([Files API](https://aistudio.google.com/docs/files)):
- 20 GB per project and 2 GB per file. Files are deleted after **48 hours**.
- Uploaded files can't be downloaded back.
- Free of charge in all Gemini API regions.
- Use it when the request is over 100 MB (50 MB for PDF).

**Batch API** ([Rate limits](https://aistudio.google.com/docs/rate-limits)):
- Up to 100 concurrent batch requests, 2 GB input file and 20 GB file storage.
- Tier 1 enqueued-token limits: 3M for the Flash models, 10M for the Flash-Lite models.

### Inferences
- **Recommended model per feature:**
  - **(a) Vision checks:** `gemini-3.5-flash-lite`. It has a free tier for development and costs $0.30/$2.50. `gemini-3.1-flash-lite` is about 25–40% cheaper ($0.25/$1.50) for production.
  - **(b) Owner agent:** `gemini-3.8-flash`.
  - **(c) Shift summary:** `gemini-3.8-flash` through Flex or Batch, at 50% off.
  - **(e) Owner voice:** `gemini-3.8-live`.
- **Skip `gemini-4-argon`.** Nothing in the product needs it, and its price doubles before the hackathon is even judged into 2027.
- **Budget production at 2027 prices.** The hackathon (14 Nov) uses current prices, but a production budget should assume 3.8 Flash at $1.50/$7.50.
- **Thinking tokens:** 3.8 Flash cannot turn thinking fully off (no "minimal" level). Assume thinking tokens are billed as output and add latency. Use `thinking_level=low` for the agent, and Flash-Lite for low-latency checks.
- **Combine cameras into one image.** A 2×2 or 2×3 mosaic of camera frames as a single image costs 1,120 tokens at default resolution, versus 4–6 separate images. That cuts the per-tick cost several-fold.
- **Video for RAG:** 1 fps at 70 tokens per frame is about 4,200 tokens per camera-minute. Sampling at fps=0.2 (one frame every 5 s) is about 840 tokens per camera-minute.
- **Don't rely on the Files API as the clip archive.** Files expire after 48 hours, so keep clips in Cloud Storage and pass them in for analysis.

### Gaps
- Model cards for `gemini-3.5-flash-lite` and `gemini-3.1-flash-lite` were not fetched. Support for structured output, function calling and thinking on those two is assumed from family behaviour and must be confirmed.
- Knowledge cutoffs were not listed.
- The 2.5-era video token figures above conflict with the 3.x figures and are unresolved.
- The price of the Gemini API "File Search" tool (a managed RAG option on 3.8 Flash) was not fetched.

---

## 2. Free tier vs paid tier rate limits; Vertex AI (Agent Platform) vs AI Studio keys; Vietnam availability

### Takeaway
- **Vietnam is a supported country** for the Gemini API and AI Studio.
- **The free tier is too small for a live multi-camera demo.** Flash-Lite allows about 10 RPM and 500 RPD; 3.8 Flash about 5 RPM and 20 RPD. Free-tier prompts may also be used by Google to improve its products.
- **Free Cloud credits don't pay for AI Studio usage.** The $300 trial credit can't pay for Gemini API usage in AI Studio on billing accounts opened after 2 Mar 2026. Promotional Cloud credits apply to the AI Studio Gemini API only once a prepay balance exists.
- **Easiest route for the organizers' credits:** call Gemini through **Agent Platform (the renamed Vertex AI)**, which is billed through normal Cloud Billing.

### Cited Findings
- **Vietnam:** listed among supported countries for the "Gemini API and Google AI Studio" ([Available regions](https://aistudio.google.com/docs/available-regions)).
- **What the official rate-limit page gives:** no RPM/TPM/RPD numbers; it says "View your active rate limits in AI Studio" ([Rate limits](https://aistudio.google.com/docs/rate-limits)). The page does state:
  - Limits apply per project, not per API key.
  - RPD resets at midnight Pacific time.
  - Preview models have tighter limits.
  - Priority tier gets 0.3× the standard limits.
  - Spend limit per rolling 10 minutes: Tier 1 $10, Tier 2 and 3 $200.
- **Tier qualification** ([Rate limits](https://aistudio.google.com/docs/rate-limits), [Billing](https://aistudio.google.com/docs/billing)):

  | Tier | Requirement | Billing cap |
  |---|---|---|
  | Tier 1 | Linked billing account | $250 |
  | Tier 2 | $100 paid and 3 days since first payment | $2,000 |
  | Tier 3 | $1,000 paid and 30 days | $20k–$100k+ |

  At the cap, service pauses for all linked projects until the 1st of the next month.
- **Free-tier limits, third-party, citing the AI Studio limits page** ([ScriptByAI](https://www.scriptbyai.com/gemini-api-free-tier-limits/)):

  | Model | RPM | TPM | RPD |
  |---|---|---|---|
  | `gemini-3.8-flash` | 5 | 250k | 20 |
  | `gemini-3.6-flash` | 5 | 250k | 20 |
  | `gemini-3.5-flash-lite` | 10 | 250k | 500 |
  | `gemini-3.1-flash-lite` | 10 | 250k | 500 |

  The same source gives Tier 1 at about 10,000 RPD for 3.8 Flash and 150,000 RPD for 3.5 Flash-Lite. An older post claims 15 RPM / 1,500 RPD for "Flash"; that is stale ([TinkerLLM](https://tinkerllm.com/blog/gemini-api-free-tier-limits-rate-quotas/)). **Unverified against official numbers.**
- **Data use** ([ScriptByAI](https://www.scriptbyai.com/gemini-api-free-tier-limits/), [Billing](https://aistudio.google.com/docs/billing)):
  - On unpaid requests outside the EEA, UK and Switzerland, Google may use prompts and responses to improve its products, and human reviewers may read some.
  - Paid services don't do this.
  - Once any project has billing enabled, AI Studio prompts fall under the paid terms.
- **Billing model** ([Billing](https://aistudio.google.com/docs/billing)):
  - New users default to **Prepay**: $5 minimum, $5,000 maximum. Credits expire after 12 months. At a $0 balance, requests fail with HTTP 402.
  - Prepay and Postpay took effect 23 Mar 2026.
  - The **$300 Welcome credit can't pay for Gemini API/AI Studio** usage if the Cloud Billing account was opened after 2 Mar 2026.
  - "Prepay users must buy credits before eligible promotional Cloud Credits can be applied."
  - Agent Platform usage is billed on the standard Cloud cycle, and prepay credits can't be applied to it.
- The Free Trial page confirms the trial credit "can't pay for Gemini API in AI Studio costs" ([Free features](https://docs.cloud.google.com/free/docs/free-cloud-features)).
- **Agent Platform pricing and location for 3.8 Flash** ([search summary of Agent Platform pricing page](https://cloud.google.com/gemini-enterprise-agent-platform/generative-ai/pricing)):
  - Introductory price is $0.75/$3.75 on the **global** endpoint through 31 Dec 2026, rising to $1.50/$7.50 from 1 Jan 2027.
  - **Regional (non-global) endpoints cost about 10% more** ($0.825/$4.125).
  - The global endpoint does not guarantee where data is processed ([issoh.co.jp](https://www.issoh.co.jp/tech/details/18410/)).

### Inferences
**AI Studio API key (Gemini Developer API):**
- Fastest to start.
- Has a free tier.
- Billing is prepay, separate from the Cloud credits.

**Agent Platform (Vertex) Gemini:**
- Authenticates with IAM/ADC. On Cloud Run that means the service account, so there is no key to leak.
- Billed through Cloud Billing, so event coupons and trial credit almost certainly apply.
- Offers a global endpoint plus regional endpoints.
- Uses the same `google-genai` SDK with `vertexai=True, location="global"`.

**What to use when:**
- **For the hackathon:** develop on a free AI Studio key, and run the live demo on Agent Platform billed to the organizer credits. As a fallback, link billing to reach Tier 1.
- **Footage:** never send real customers' footage through the free tier, because of the data-use terms.
- **Rate-limit arithmetic:** 4 cameras checked every 5 s is 48 RPM, far above the free 10 RPM. Even a mosaic every 6 s (10 RPM) hits the 500 RPD cap in about 50 minutes.

### Gaps
- Official per-model RPM/TPM/RPD numbers were not visible; they show only inside AI Studio. Quota defaults for Agent Platform were not found.
- Availability of `gemini-3.8-flash` and `gemini-3.5-flash-lite` in the `asia-southeast1` regional endpoint is not confirmed. A Japanese source says 3.8 Flash is not in Tokyo.
- It is not confirmed whether event promotional credits apply to the AI Studio Gemini API without a prepay balance. Treat it as "no" unless the organizers say otherwise.

---

## 3. Gemini Live API: models, pricing, session limits, frame rate, Vietnamese audio; is it fit for camera monitoring or an owner voice assistant?

### Takeaway
- `gemini-3.8-live` is a good fit for a **Vietnamese voice assistant for the owner**, with function calling into the event database.
- It is a **poor fit for continuous camera monitoring**:
  - Video input is limited to 1 fps JPEG.
  - Audio+video sessions end at 2 minutes unless context compression is on.
  - Connections drop after about 10 minutes.
  - Context is 131k tokens.
  - Output is audio only, with no structured output.
  - Every stream is billed per minute.

### Cited Findings
- **`gemini-3.8-live` model card** ([model card](https://aistudio.google.com/docs/models/gemini-3.8-live)):
  - Updated Sept 2026.
  - **131,072 input tokens** and 65,536 output.
  - Input: text, images, audio. "Audio is the only supported response modality."
  - Function calling, asynchronous by default.
  - Search grounding; built-in thinking; proactive audio always on.
  - **No structured outputs**, batch or caching.
  - Affective dialogue has been removed.
  - Video frames are sent by default, so send only the frames you need.
- **Other Live models** ([Models](https://aistudio.google.com/docs/models)):
  - `gemini-3.8-live-extended-thinking`: more background reasoning.
  - `gemini-3.1-flash-live-preview`: legacy.
  - `gemini-2.5-flash-native-audio-preview-12-2025`.
- **Live pricing, per 1M tokens, shared by 3.8 Live, 3.8 Live Extended Thinking and 3.1 Flash Live Preview** ([Pricing](https://aistudio.google.com/docs/pricing)):
  - Input: text $0.75; audio $3.00 (about $0.005/min); image/video $1.00 (about $0.002/min).
  - Output: text $4.50; audio $12 (about $0.018/min).
  - The free tier is free of charge.
- **Transcription models** ([Pricing](https://aistudio.google.com/docs/pricing)):
  - `gemini-3.5-transcribe-live`: about $0.009/min.
  - `gemini-3.5-transcribe`: about $0.005/min.
- **Protocol** ([Live API](https://aistudio.google.com/docs/live)):
  - Stateful WebSocket (WSS).
  - Input audio is 16-bit PCM at 16 kHz; output audio is 16-bit PCM at 24 kHz.
  - **Images/video: JPEG at no more than 1 frame per second.**
  - Tools: function calling and Google Search.
  - Client-to-server connections are "generally better" for audio/video. Use **ephemeral tokens** in production.
  - "Converse in 70 supported languages."
- **Session limits** ([Live session](https://aistudio.google.com/docs/live-session)):
  - Without compression, audio-only sessions last 15 minutes and **audio+video sessions 2 minutes**.
  - `contextWindowCompression` (a sliding window) makes sessions unlimited.
  - A connection lasts about 10 minutes, and a `GoAway` message reports `timeLeft` before it closes.
  - `sessionResumption` handles stay valid for 2 hours.
- **Language and voice** ([Agent Platform Live API language/voice](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/live-api/configure-language-voice)):
  - **Vietnamese (vi-VN)** is in the 24-entry language table.
  - 30 prebuilt voices (Kore, Puck, Charon, Aoede, …), chosen with `voice_name`.
  - Set the language with `speech_config.language_code`, or tell the model in the system instruction to respond in the target language.

### Inferences
**Continuous monitoring is expensive by the per-minute meter.** Six cameras × 14 h × 60 min × 30 days is 151,200 camera-minutes; at $0.002/min that is about **$302 a month** for video input alone. On top of that you'd hold six WebSockets that reconnect every 10 minutes, and the model would answer in audio rather than JSON events. Periodic `generateContent` calls on Flash-Lite with a JSON schema are cheaper and easier to make reliable.

**Owner voice assistant: a good fit.**
- About $0.023 per minute of two-way audio, at most ($0.005 in + $0.018 out).
- Wire it up with Live function calls such as `search_events(time_range, table)` and `get_clip()`.
- Connect browser-to-Live directly with ephemeral tokens issued by the Cloud Run backend.

**Staff spoken alerts:** alerts are short and known in advance, so plain TTS (§8) is simpler than keeping a Live session open.

### Gaps
- Max concurrent Live sessions per project and the free-tier Live limits were not found.
- Vietnamese voice quality was not checked. The AI Studio Live page gives 70 languages while the Agent Platform page gives 24; which list applies to `gemini-3.8-live` in each API is unclear.
- How the "$0.002/min" video figure is derived is not stated. It doesn't match 1 fps × 70–280 tokens at $1/1M.

---

## 4. Video understanding for the owner agent, Gemini embeddings and vector storage on Google Cloud

### Takeaway
**Video RAG design:**
1. Flash-Lite writes short scene descriptions and events as JSON (structured output).
2. Embed them with `gemini-embedding-2`, reduced to 768 or 1,536 dimensions.
3. Store them in **Firestore vector search**: one database for the events, the realtime dashboard and the vectors.
4. Answer owner questions with 3.8 Flash, which re-checks the original clip from Cloud Storage using offsets.

Firestore is the simplest option. AlloyDB/Cloud SQL pgvector and Vector Search 2.0 are overkill for a hackathon.

### Cited Findings
**Video input** ([Video understanding](https://aistudio.google.com/docs/video-understanding)):
- Accepted formats: mp4, mpeg, mov, avi, flv, mpg, webm, wmv, 3gpp.
- Query timestamps as MM:SS.
- Clip with `start_offset`/`end_offset`.
- Custom `fps`.

`gemini-3.8-flash` supports function calling, structured outputs, file search, caching and batch ([model card](https://aistudio.google.com/docs/models/gemini-3.8-flash)).

**Embedding models** ([Embeddings](https://aistudio.google.com/docs/embeddings)):
- **`gemini-embedding-2`** (Apr 2026) is the "first multimodal embedding model in the Gemini API":
  - Inputs: text, image (up to 6 per request), audio (up to 180 s), **video (up to 120 s, at most 32 frames)** and PDF (up to 6 pages), all in one embedding space.
  - 8,192 tokens in total; 100+ languages.
  - Default 3,072 dimensions, adjustable from 128 to 3,072 (768, 1,536 or 3,072 recommended). Truncated vectors are normalised automatically.
  - **No `task_type`.** Put prefixes in the text instead, such as `task: search result | query: …`.
  - Batch costs 50% of the standard price.
- **`gemini-embedding-001`:** text only, 2,048 tokens, has `task_type`. Embeddings from the two models are incompatible.

**Embedding prices** ([Pricing](https://aistudio.google.com/docs/pricing)):
- `gemini-embedding-2`: text $0.20 per 1M tokens; image $0.00012 each; audio $0.00016 per second; video $0.00079 per frame. Batch costs half.
- `gemini-embedding-001`: $0.15 per 1M ($0.075 batch).
- Both have a free tier.

**Storage options:** Google lists Vector Search 2.0, BigQuery, AlloyDB and Cloud SQL ([Embeddings](https://aistudio.google.com/docs/embeddings)).

**Firestore vector search** ([Firestore vector search](https://firebase.google.com/docs/firestore/vector-search)):
- **At most 2,048 dimensions.**
- Flat index, created with `gcloud firestore indexes composite create … vector-config='{"dimension":"768","flat":"{}"}'`.
- Distance measures: EUCLIDEAN, COSINE, DOT_PRODUCT. DOT_PRODUCT on normalised vectors is recommended.
- Equality pre-filters, including `and`/`or`, work with a composite index.
- k ≤ 1,000.
- SDKs: Python, Node, Go and Java only.
- **No realtime listeners on vector queries.**
- Embeddings must be generated outside Firestore.

**Firestore billing** ([Firebase Firestore billing](https://firebase.google.com/docs/firestore/pricing), via search summary):
- A KNN query costs 1 read per 100 index entries scanned, plus 1 read per document returned. Google's example: limit 5 with 1,550 entries costs 5 + 16 reads.
- Free tier: 50k reads, 20k writes and 20k deletes per day, default database only.
- Paid reads about $0.03 per 100k (search summary).

**Firestore free tier** ([Free features](https://docs.cloud.google.com/free/docs/free-cloud-features)): 1 GiB storage, 50k reads, 20k writes and 20k deletes per day per project, and 10 GiB egress per month.

### Inferences
**Owner agent pipeline:**
1. Edge or backend detects an event.
2. Flash-Lite turns it into JSON, e.g. `{camera, table, type, start_ts, end_ts, description_vi}`.
3. The event is written to Firestore. Its clip goes to `gs://…/clips/` and its description is embedded at 768 dimensions.
4. ADK tools answer queries:
   - `search_events`: vector search plus filters on `date` and `camera`.
   - `get_events_between`: a plain Firestore range query.
   - `get_clip_url`: a signed Cloud Storage URL.
   - `inspect_clip`: 3.8 Flash on a Cloud Storage URI with offsets, for "show me" or verification.
5. The answer includes the timestamps and clip links.

**Why 768 dimensions:** they fit Firestore's 2,048 limit and keep index reads cheap.

**Embed text or video?** At $0.00079 per frame, embedding the video directly (up to 32 frames per clip, about $0.025 per clip) is about 100× more expensive than embedding a 100-token description ($0.00002). Embed the descriptions; use video embeddings only for a "find similar scenes" demo.

**Context caching for owner Q&A:** caching 100k tokens costs $0.05 per hour in storage on 3.8 Flash. That only beats re-sending ($0.075 per query, versus $0.0075 cached) when there's more than about 0.75 queries per hour on the same context. RAG keeps the context small anyway, so skip caching.

**Alternative:** the Gemini API "File Search" tool, a managed RAG supported on 3.8 Flash. Its price and limits weren't checked.

### Gaps
- No verified current prices for AlloyDB, Cloud SQL (pgvector) or Vector Search 2.0.
- Firestore storage price per GiB and the exact asia-southeast1 read/write prices were not verified.
- File Search tool pricing is missing.

---

## 5. Google Agent Development Kit (ADK): version, languages, Cloud Run deploy, tools/sessions/streaming; Agent Runtime alternative

### Takeaway
ADK Python is at **v2.13.0** (23 Oct 2026, Python ≥3.11) and **ADK TypeScript 2.0 is GA**. Go, Java and Kotlin SDKs also exist.

`adk deploy cloud_run` deploys an agent in one command. Since the team already uses FastAPI, they can instead embed ADK in their own app with `get_fast_api_app()` and run `gcloud run deploy --source .`.

Sessions are **in-memory by default**, which means they're lost when an instance recycles. Point them at a database or Agent Runtime.

### Cited Findings
- **Versions:** `google-adk` 2.13.0 released 23 Oct 2026. Earlier releases: 2.12.0 (13 Oct), 2.11.0 (2 Oct), 2.10.0 (25 Sep). Requires Python ≥3.11 ([PyPI](https://pypi.org/project/google-adk/)).
- **Languages and features** ([adk.dev](https://adk.dev/)):
  - Banner: "ADK TypeScript 2.0 GA" with graph workflows. Languages: Python, TypeScript/JS, Go, Java, Kotlin.
  - **Tools:** function tools, **MCP tools**, OpenAPI tools, auth, built-in Google Search, action confirmations.
  - **State:** sessions, state, events, memory, artifacts, context compression.
  - **Workflows:** multi-agent (sequential, loop, parallel, routing) and graph workflows.
  - **Voice:** "Live and Voice Agents" (speech-to-speech and cascade).
  - **Deployment:** Agent Runtime, Cloud Run, GKE, or self-hosted.
- **Cloud Run deploy** ([ADK Cloud Run deploy](https://adk.dev/deploy/cloud-run/)):
  - `adk deploy cloud_run --project P --region R [--service_name] [--app_name] [--allow_origins] [--session_service_uri] [--artifact_service_uri] [--memory_service_uri] [--port 8000] [--with_ui] AGENT_PATH`. Pass extra gcloud flags after `--`.
  - Required files: `agent.py` defining `root_agent`, `__init__.py` and `requirements.txt`.
  - Alternative: `gcloud run deploy --source .` with your own `main.py` using `get_fast_api_app()` and a Dockerfile (`python:3.13-slim`).
  - TypeScript: `npx adk deploy cloud_run`, needing `agent.ts` that exports `rootAgent`.
  - Go: `adkgo deploy cloudrun`.
  - **Defaults to in-memory session and artifact services.** Persistent options:
    - Sessions: any SQLAlchemy URL (async driver), or `agentengine://`.
    - Artifacts: `gs://bucket`.
    - Memory: `rag://` or `agentengine://`.
- **Agent Runtime pricing (third-party, not verified on Google's page):** $0.0864 per vCPU-hour, $0.0090 per GB-hour, and $0.25 per 1,000 session/Memory Bank events. Memory Bank billing start dates vary between sources ([search summary incl. betterclaw.io](https://www.betterclaw.io/blog/google-vertex-ai-agent-builder)).

### Inferences
**Recommended setup:**
- One FastAPI app on Cloud Run that does three things:
  - mounts the ADK agent with `get_fast_api_app()`, which gives the `/run` and `/run_sse` endpoints;
  - serves the ingestion endpoints;
  - serves the built Vite `dist/`.
- Store sessions in Firestore-backed custom code, or in SQLite (fine for a demo but lost on redeploy).
- Store artifacts and clips in Cloud Storage.

**Use the team's MCP experience.** Expose the event log as an MCP server and plug it into ADK's MCP toolset. It makes a nice "agentic" talking point for the judges.

**Agent Runtime** isn't needed for a hackathon. It adds per-hour runtime charges, and the requirement is "deploy on Cloud Run".

### Gaps
- The exact streaming API names for ADK bidi streaming with `gemini-3.8-live`, and the supported-model matrix, were not fetched.
- Official Agent Runtime pricing was not verified.

---

## 6. Cloud Run: pricing, free tier, min instances, WebSockets/SSE and timeouts, GPUs, deploying Vite + FastAPI; Firebase Hosting alternative

### Takeaway
- **Cost for this scale:** Cloud Run costs pennies for a hackathon. An always-on backend with min-instances=1 costs about $10 a month while idle, or about $45–57 a month if kept busy on instance-based billing.
- **Timeouts:** WebSockets and SSE work with up to a **60-minute** request timeout, but clients must reconnect.
- **GPUs:** L4 and RTX PRO 6000 GPUs exist in `asia-southeast1`, but they're unnecessary because Gemini does the vision work.
- **Simplest deploy:** one container in which FastAPI serves the Vite build.

### Cited Findings
- **Unit prices, Tier 1, read 12 Oct 2026 from the official page and Billing Catalog API** ([DEV Community worked examples](https://dev.to/elimio/what-cloud-run-costs-with-worked-examples-378i)). The official pricing page is JS-rendered and couldn't be fetched.

  | Item | Request-based (default) | Instance-based |
  |---|---|---|
  | CPU, per vCPU-second | $0.000024 | $0.000018 |
  | Memory, per GiB-second | $0.0000025 | $0.000002 |
  | Requests | $0.40 per million | none |
  | Idle min-instance | $0.0000025 per vCPU-second and per GiB-second | – |
  | Tier 2 regions | 1.4× | 1.2× |
  | Monthly free tier | 180k vCPU-s, 360k GiB-s, 2M requests | 240k vCPU-s, 450k GiB-s (separate pool) |

  The same figures appear in [usage.ai](https://www.usage.ai/blogs/gcp/cloud-run-pricing/). The official Free Tier page confirms the request-based free tier, plus 1 GB/month of North America egress ([Free features](https://docs.cloud.google.com/free/docs/free-cloud-features)).
- **Worked examples** ([DEV](https://dev.to/elimio/what-cloud-run-costs-with-worked-examples-378i)):
  - One idle min-instance (1 vCPU, 512 MiB): about **$9.86 a month**.
  - The same instance always busy on instance-based billing: **$44.71 a month** after the free tier, or $49.93 without it.
  - The same busy instance on request-based billing: $61.14.
- **WebSockets** ([Cloud Run WebSockets](https://docs.cloud.google.com/run/docs/triggering/websockets)):
  - Supported with no extra configuration, but each connection is subject to the request timeout: **default 5 minutes, maximum 60 minutes**. Clients must reconnect.
  - Session affinity is best effort.
  - Up to 1,000 concurrent connections per container.
  - **An instance with an open WebSocket counts as active and is billed.**
  - To sync across instances, use Memorystore Redis Pub/Sub or **Firestore real-time updates**.
- **GPUs** ([Cloud Run GPU](https://docs.cloud.google.com/run/docs/configuring/services/gpu)):
  - NVIDIA L4 (24 GB) and RTX PRO 6000 Blackwell (96 GB), **both available in `asia-southeast1`** (Singapore). Also in us-central1, europe-west4 and others.
  - Minimums: L4 needs 4 CPU and 16 GiB; RTX PRO 6000 needs 20 CPU and 80 GiB.
  - **Instance-based billing required**; scales to zero; about 5 s start with drivers preinstalled.
  - New projects automatically get quota for 3 GPUs.
- **Firebase Hosting, Spark plan** ([Firebase pricing via search](https://firebase.google.com/pricing)):
  - 10 GB storage and **360 MB/day transfer** at no cost.
  - Blaze overage: $0.026/GB storage and $0.15/GB transfer.
  - Some third parties claim 10 GB/month of transfer instead, which conflicts with the official page.

### Inferences
**Deployment for the hackathon:**
- **One Cloud Run service** `easyfnb` in `asia-southeast1`.
  - Multi-stage Dockerfile: `node` builds Vite, then `python` runs FastAPI, which serves `/` from `dist/` with `StaticFiles` and `/api/*` itself.
  - Set `--min-instances=1` on demo day to avoid cold starts, `--timeout=3600` for SSE/WS, and `--cpu 1 --memory 1Gi`.
  - Deploy with `gcloud run deploy --source .`. This clearly satisfies the "deploy on Cloud Run" requirement.
- **Optional second service** for the ADK agent, via `adk deploy cloud_run`.
- **Firebase Hosting** for the frontend is fine but splits the deploy. Its 360 MB/day free transfer is enough for a demo.

**Region tier:** whether `asia-southeast1` is Cloud Run Tier 1 or Tier 2 wasn't verified. If it's Tier 2, request-based prices are 1.4× and instance-based 1.2×.

**SSE vs WebSockets:** SSE from Cloud Run is fine for streaming the owner agent's answers, and ADK provides `/run_sse`. For the live dashboard, prefer Firestore listeners (§7). Then the backend needn't hold connections open, can stay on request-based billing, and can scale to zero after the event.

### Gaps
- The official Cloud Run pricing page couldn't be rendered. Unit prices come from a dated third-party read of the official page.
- The asia-southeast1 tier and GPU per-second prices were not verified.

---

## 7. Real-time push to the dashboard and phones: Firestore listeners vs Realtime Database vs Cloud Run WebSockets/SSE vs Pub/Sub; FCM

### Takeaway
- **Dashboard:** subscribe straight to Firestore with realtime listeners (`onSnapshot`). Google recommends this pattern for syncing Cloud Run instances, and it costs nothing at hackathon scale.
- **Staff phones:** use **Firebase Cloud Messaging**, which is free, as web push to a PWA.
- **Pub/Sub** is only for backend fan-out.
- Use **Cloud Run SSE** only for streaming agent answers.

### Cited Findings
- **Cloud Run guidance** ([Cloud Run WebSockets](https://docs.cloud.google.com/run/docs/triggering/websockets)): Cloud Run instances don't share state. Polling a database is a poor fit because idle instances get no CPU. Google recommends Redis Pub/Sub or Firestore real-time updates.
- **FCM is no-cost:** Firebase lists Cloud Messaging with Analytics and Crashlytics among the products that cost nothing ([Firebase pricing](https://firebase.google.com/pricing)). It works on iOS, Android and web ([SuperTokens](https://supertokens.com/blog/firebase-pricing)).
- **Firestore:** free 50k reads/day per project. Vector queries can't be listened to ([Free features](https://docs.cloud.google.com/free/docs/free-cloud-features), [Firestore vector search](https://firebase.google.com/docs/firestore/vector-search)).
- **Pub/Sub:** free tier of 10 GiB of messages a month ([Free features](https://docs.cloud.google.com/free/docs/free-cloud-features)).

### Inferences
**Firestore read budget:** each document change costs one read per active listener. At 5 dashboards × 2,000 event/state changes a day, that's about 10k reads a day, inside the free 50k. Store a per-table state document (`tables/{id}`) that the dashboard listens to, plus an `alerts` collection.

**Staff phone alerts:**
1. The backend sends an FCM data message.
2. The PWA service worker shows a notification.
3. The app plays a pre-generated Vietnamese TTS clip, e.g. "Bàn 5 cần dọn".

Background audio playback and iOS web-push limits belong to the phone-focused researcher.

### Gaps
- Firebase Realtime Database pricing and limits were not researched. Firestore covers the need.
- iOS PWA push limitations were not checked here.

---

## 8. Google Cloud Text-to-Speech, Vietnamese (brief)

### Takeaway
There are two options for Vietnamese spoken alerts:
- **Cloud TTS Chirp 3 HD:** $30 per 1M characters, with **1M characters free each month**.
- **Gemini TTS:** `gemini-3.8-flash-lite-tts` at about $0.0015 per 10 s of audio, doubling later.

Alerts are templated, so pre-generate them and cache the audio; the cost is close to $0.

### Cited Findings
- **Chirp 3 HD:** $0.00003 per character ($30 per 1M), first 1M characters a month free. Neural2 costs $16 per 1M ([TTS pricing](https://cloud.google.com/text-to-speech/pricing)).
- **Gemini TTS** ([Pricing](https://aistudio.google.com/docs/pricing)). Both have a free tier.
  - `gemini-3.8-flash-tts`: text in $0.50 → $1.00, audio out $9 → $18 per 1M tokens (about $0.00225 → $0.0045 per 10 s).
  - `gemini-3.8-flash-lite-tts`: audio out $6 → $12 (about $0.0015 → $0.003 per 10 s).
  - The effective date of these increases wasn't captured in the fetched summary.

### Gaps
- The list of Vietnamese Chirp 3 HD voices and whether Gemini TTS supports vi-VN were not verified. The pricing results didn't mention vi-VN, so confirm in the voice list at `docs.cloud.google.com/text-to-speech/docs/list-voices-and-types`.

---

## 9. Credits and programs for students and hackathon teams

### Takeaway
- **Organizer credits:** usually a one-time **coupon link per Gmail account** that creates or credits a billing account. Link the hackathon project to *that* billing account, not to a personal card.
- **$300 Free Trial:** lasts 90 days but **does not cover Gemini API in AI Studio** on accounts opened after 2 Mar 2026. Use it, and the event credits, on Cloud Run, Firestore and Agent Platform Gemini.
- **Free tiers:** the Gemini API free tier and the Cloud Always Free tier cover development.

### Cited Findings
- **Free Trial** ([Free features](https://docs.cloud.google.com/free/docs/free-cloud-features)):
  - **$300 credit for 90 days.**
  - Eligibility: never a paying user of Google Cloud, Maps Platform or Firebase.
  - A card is required, with a $0–1 authorization hold.
  - Restrictions: the credit can't pay for **Gemini API in AI Studio** or partner MaaS models. No GPUs on VMs, no Marketplace, no quota increases.
  - When it ends, resources stop, with a 30-day grace period.
- **Always Free tier, monthly** ([Free features](https://docs.cloud.google.com/free/docs/free-cloud-features)):
  - Cloud Run: 2M requests, 180k vCPU-s, 360k GB-s.
  - Firestore: 1 GiB, plus 50k reads, 20k writes and 20k deletes a day.
  - Cloud Storage: 5 GB-month, **US regions only**.
  - Pub/Sub: 10 GiB.
  - Cloud Build: 2,500 build-minutes.
  - Artifact Registry: 0.5 GB.
  - Secret Manager: 6 versions.
  - BigQuery: 1 TiB of queries.
- **Event coupon pattern** ([AI Tinkerers hackathon handbook](https://nyc.aitinkerers.org/hackathons/h_fmkdFOW4QE4)):
  - A private coupon link handed out at the event, usable once per Gmail account.
  - Redeeming it creates a new billing account; link the project to it.
  - "DO NOT use the Google Cloud PROJECT WITH YOUR CREDIT CARD."
- **Developer Program FAQ** ([Google Developer Program benefits FAQ](https://developers.google.com/profile/help/benefits)):
  - Credits apply to a single billing account.
  - Redeeming needs the `billing.accounts.redeemPromotion` role.
- **Other forms:** some event credit forms require redemption by a deadline and use within 2 weeks ([Google form example](https://docs.google.com/forms/d/e/1FAIpQLSc236lhbP0VIXsIsk_GHMgRffW5d-4Y4qGx2JsPUI4fB2VJ4w/viewform)). Google's general redemption codelab: [Redeem credits codelab](https://codelabs.developers.google.com/codelabs/cloud-codelab-credits).
- **Student and Developer Program claims (third-party):**
  - The "Google Cloud for Education – Students" program gives 200 Google Skills credits for labs; faculty-sponsored credits are about $50.
  - Google AI Pro/Ultra subscribers reportedly get $10–100 a month in Developer Program credits.

  Both unverified ([search summary incl. dev.to guide](https://dev.to/behruamm/the-2026-developers-guide-to-free-google-cloud-credits-for-ai-side-projects-1ac5), [klymentiev.com](https://klymentiev.com/blog/gemini-free-credits)).

### Inferences
**Before 14/11:**
1. Each member makes sure one Gmail account has *not* used the trial, in case a spare $300 is needed.
2. When the organizers' coupon arrives, create the project `easyfnb-devfest`, link it to the coupon billing account, and enable Cloud Run, Firestore, Cloud Storage, Agent Platform (aiplatform) and Text-to-Speech.
3. Call Gemini via Agent Platform so the coupon actually pays for it.
4. Set a budget alert.

**Startup credits:** Google for Startups Cloud Program credits only matter after the hackathon, for a registered company. Not verified here.

### Gaps
- The exact credit amount and delivery method for GDG DevFest MienTrung 2026 aren't public in the sources found; ask the organizers.
- Google for Startups program amounts weren't verified on an official page.
- Whether Cloud Run GPUs are allowed during the Free Trial is unclear. The trial restriction names VM GPUs.

---

## 10. Estimated cost: 1-day hackathon demo and one restaurant (4–8 cameras) per month, with a minimal Cloud Run architecture

### Takeaway
- **Demo day:** about **$15–20** of usage, mostly Flash-Lite vision calls. It needs Tier 1 or Agent Platform, because the free tier's 10 RPM / 500 RPD is too low.
- **One restaurant (6 cameras, 14 h a day):**
  - **Lean design** (motion-gated, event-triggered descriptions, request-based Cloud Run): about **$50–70 a month**.
  - **Richer design:** about **$150–170 a month** at Nov 2026 prices; 2027 adds about $12–15.
  - **Cost drivers:** vision-check cadence and the always-on Cloud Run instance dominate.

### Cited Findings (unit prices used, all read 2026-11-04)
- `gemini-3.5-flash-lite`: $0.30 in / $2.50 out. Batch/Flex: $0.15 / $1.25.
- `gemini-3.1-flash-lite`: $0.25 / $1.50.
- `gemini-3.8-flash`: $0.75 / $3.75, becoming $1.50 / $7.50 on 1 Jan 2027.
- `gemini-embedding-2`: $0.20 per 1M text tokens.
- Live audio: $0.005/min in, $0.018/min out.
- `gemini-3.8-flash-lite-tts`: about $0.0015 per 10 s.

Source for all of the above: [Pricing](https://aistudio.google.com/docs/pricing).

- Image tokens: 1,120 (default) or 280 (low). Video: 70 tokens per frame at low/medium ([Media resolution](https://aistudio.google.com/docs/media-resolution)).
- Cloud Run instance-based: $0.000018 per vCPU-s and $0.000002 per GiB-s, with 240k/450k free. Idle min-instance: $0.0000025 ([DEV worked examples](https://dev.to/elimio/what-cloud-run-costs-with-worked-examples-378i)).
- Chirp 3 HD: first 1M characters a month free ([TTS pricing](https://cloud.google.com/text-to-speech/pricing)).
- Firestore free: 50k reads and 20k writes a day ([Free features](https://docs.cloud.google.com/free/docs/free-cloud-features)).

### Inferences: arithmetic (assumptions stated; token counts are estimates)

**A. Hackathon demo day: 4 simulated cameras, 8 hours running (testing plus judging)**

| Item | Assumption | Arithmetic | Cost |
|---|---|---|---|
| Vision checks (3.5 Flash-Lite, structured JSON) | 2×2 mosaic every 3 s = 20 RPM; 8 h = 9,600 calls; 1,520 in (1,120 image + 400 prompt), 150 out | 9,600 × (1,520×0.30 + 150×2.50)/1e6 = 9,600 × $0.000831 | **$7.98** |
| Scene descriptions for RAG (3.5 Flash-Lite) | each camera every 60 s, 10-s clip at 1 fps → 700 + 300 = 1,000 in, 200 out; 4×60×8 = 1,920 calls | 1,920 × (1,000×0.30 + 200×2.50)/1e6 = 1,920 × $0.0008 | $1.54 |
| Embeddings (`gemini-embedding-2`, 768-d) | about 3,900 texts × 100 tokens = 0.39M tokens | 0.39 × $0.20 | $0.08 |
| Owner agent (3.8 Flash) | 150 queries × (8k in + 2k out incl. thinking) | 150 × (8,000×0.75 + 2,000×3.75)/1e6 = 150 × $0.0135 | $2.03 |
| Shift summaries (3.8 Flash) | 10 runs × (40k in + 2k out) | 10 × (0.03 + 0.0075) | $0.38 |
| Spoken alerts | 300 alerts × 3 s = 900 s = 90 × 10 s | 90 × $0.0015 (or Chirp 3 HD: 12k characters, free) | $0.14 |
| Live API owner voice | 30 min two-way audio | 30 × ($0.005 + $0.018) | $0.69 |
| Cloud Run | 1 vCPU / 1 GiB, min-instance 1, 24 h, instance-based | 86,400 × ($0.000018 + $0.000002) = $1.73; covered by free tier (×1.2 if Tier 2) | $0–2.07 |
| Firestore and Cloud Storage | within the free quota; under 1 GB of clips | – | about $0–0.05 |
| **Total** | | | **about $13–15**, so budget $20 |

**Rate-limit check:** 20 RPM is more than the free tier's 10 RPM, and 9,600 calls is more than its 500 RPD. Use Tier 1 or Agent Platform on the event credits.

**B. One real restaurant per month: 6 cameras, open 14 h a day × 30 days = 420 h**

| Item | Rich design | Lean design |
|---|---|---|
| Vision checks | 2×3 mosaic every 10 s = 151,200 ticks, motion-gated to 50% = 75,600 calls on **3.1 Flash-Lite**: 75,600 × (1,520×0.25 + 150×1.50)/1e6 = 75,600 × $0.000605 = **$45.7** (3.5 Flash-Lite: 75,600 × $0.000831 = $62.8) | every 15 s gated to 30% = 30,240 calls × $0.000605 = **$18.3** |
| Scene descriptions | each camera every 2 min, 20-s clip at 1 fps (1,400 + 300 in, 200 out), on **Flex** 3.5 Flash-Lite: 6×30×420 = 75,600 × (1,700×0.15 + 200×1.25)/1e6 = 75,600 × $0.000505 = **$38.2** | only on detected events, about 3,000 a month × $0.000505 = **$1.5** |
| Embeddings | about 125k texts × 100 tokens = 12.6M × $0.20 = **$2.5** (batch $1.26) | about 0.5M tokens = **$0.1** |
| Owner agent (3.8 Flash) | 20 queries/day × 30 = 600 × $0.0135 = **$8.1** (2027: $16.2) | same, $8.1 |
| Shift summaries | 60 × (60k×0.75 + 3k×3.75)/1e6 = 60 × $0.056 = **$3.4** (2027: $6.75; Batch halves it) | Batch: $1.7 |
| Spoken alerts | 150/day × 3 s × 30 = 13,500 s = 1,350 × $0.0015 = **$2.0** | Chirp 3 HD, 180k characters, free tier → **$0** |
| Live owner voice | 10 min/day × 30 × $0.023 = **$6.9** (upper bound) | 3 min/day = $2.1 |
| Cloud Run backend | always busy (WebSockets held), instance-based 1 vCPU / 1 GiB: 2,628,000 s × ($0.000018 + $0.000002) = $52.56 − free ($4.32 + $0.90) = **$47.3** (Tier 2: about $56.8) | request-based + Firestore listeners: idle min-instance about $9.9–12 (1 vCPU / 0.5–1 GiB) + bursts, mostly inside the free tier → **about $12–15** |
| Firestore, Cloud Storage, egress | writes about 6k/day (under the 20k free); clips about 15 GB in Cloud Storage (Singapore price not verified, roughly $0.3–0.5) | about $0.5 |
| **Total / month** | **about $155** (Nov 2026 prices); **about $167–170** after 3.8 Flash doubles on 1 Jan 2027 | **about $45–50**, round up to $50–70 to cover retries and testing |

At 4 cameras, scale the camera-driven lines down by about ⅔ (vision, descriptions); at 8 cameras, up by about 4/3. The Cloud Run and agent lines stay roughly the same.

**Biggest levers on cost:**
1. **Local motion/change gating** (OpenCV frame differencing on an existing PC at the restaurant) before calling Gemini.
2. **Mosaicking** cameras into one image.
3. **Low** `media_resolution` (280 tokens) for simple yes/no checks.
4. Flex/Batch for descriptions and summaries.
5. Firestore listeners instead of an always-on WebSocket server.

### Minimal architecture (fits Cloud Run, no new hardware)

**Capture**
- **Restaurant:** existing IP cameras or NVR over RTSP, read by a small Python "edge relay" on an existing PC or laptop. It does OpenCV motion gating, makes the 2×3 mosaic, cuts 10–20 s clips, and calls `POST /api/ingest`.
- **Hackathon:** laptop or phone webcams in the browser (`getUserMedia`) sending JPEG frames, or replayed restaurant videos.

**Cloud Run service `easyfnb` (asia-southeast1), a FastAPI container:**
- `/api/ingest`: Gemini Flash-Lite with a JSON `response_schema` such as `{tables:[{id, guest_raising_hand, needs_clearing, confidence}], notes}` → writes `tables/{id}` and `alerts` to **Firestore** → clip to **Cloud Storage** → description embedded with `gemini-embedding-2` (768-d) into a Firestore vector field.
- **Alerts:** sends an FCM push to staff and plays a cached vi-VN TTS clip.
- **Owner agent:** ADK agent mounted with `get_fast_api_app()` and `/run_sse`, running 3.8 Flash. Tools: `search_events` (Firestore KNN plus time/camera filters), `get_clip_url` (signed URL), `inspect_clip` (3.8 Flash on a Cloud Storage video with `start_offset`/`end_offset`), `shift_summary`.
- `/api/live-token`: issues ephemeral tokens for the browser's Live API voice session (`gemini-3.8-live`, vi-VN).
- Serves the built React/Vite `dist/`.

**Scheduled work**
- **End-of-shift summary:** a Cloud Run job or scheduled call that reads the shift's events from Firestore and runs 3.8 Flash (Flex/Batch). The result is saved and pushed. Cloud Scheduler and Cloud Run job pricing weren't researched.

**Gemini access**
- Agent Platform on the global endpoint, via the Cloud Run service account and Cloud Billing credits.
- During development, use an AI Studio free-tier key with synthetic footage only.

**Clients**
- **Dashboard:** React with Firestore `onSnapshot` on `tables` and `alerts`, and SSE to the agent.
- **Staff phones:** PWA with FCM web push.

### Gaps
- All token counts per call (prompt size, output size, thinking tokens) are estimates. Measure them with `usage_metadata` on day one.
- The asia-southeast1 Cloud Run tier, Cloud Storage price and Agent Platform regional availability weren't verified.
- Live API per-minute pricing figures are as published; their derivation is unclear.
- USD→VND conversion wasn't sourced.
