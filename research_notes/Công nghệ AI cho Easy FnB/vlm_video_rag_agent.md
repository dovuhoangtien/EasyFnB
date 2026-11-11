# VLM scene understanding, Video RAG and owner chat agent for Easy FnB (Google stack + open source, as of Nov 2026)

> Research date: 2026-11-03. Google's docs have moved: ai.google.dev/gemini-api/docs/* now 301-redirects to **aistudio.google.com/docs/***, and Vertex AI docs now redirect to **docs.cloud.google.com**. The Vertex data-governance page now calls the product **"Gemini Enterprise Agent Platform"**, and ADK calls its managed deploy target **"Agent Runtime (Agent Platform)"**, which appears to replace "Vertex AI Agent Engine". Neither page says outright that this is a rename.
> Method caveat: page contents were pulled with a fetch tool that summarizes pages using a small model. Exact numbers came from official pages, but they should be spot-checked before anything is committed to slides or code. Items marked **[prior knowledge, not re-fetched]** come from my training data (cutoff mid-2026) and were not re-verified this session.

## 1. Which Gemini models to use for video understanding, and how video is tokenized, limited, parameterized and priced

### Takeaway
As of Nov 2026 the current Gemini line is **Gemini 4 Argon** (top), **Gemini 3.8 Flash** (released Sept 2, 2026, GA, video is a headline strength), **3.6 Flash**, and the **3.5 / 3.1 Flash-Lite** models. Gemini 2.5 Pro/Flash are deprecated and auto-route to newer models on Dec 1, 2026. In the default "static" mode, video costs about **100 tokens/s at low media resolution or about 300 tokens/s at default resolution** (1 fps, 66 or 258 tokens per frame, plus 32 tokens/s of audio). A new **"agentic" video processing mode** navigates long videos itself and can use up to 88% fewer tokens. For bulk CCTV captioning pick **3.1 Flash-Lite or 2.5 Flash-Lite on the Batch API**. For clip re-inspection and agent reasoning pick **3.8 Flash**.

### Cited Findings
**Current model lineup (AI Studio / Gemini API models page)**
- Gemini 4: `gemini-4-argon`, 1M context, max output "65K / 1M tokens", inputs Text/Image/Audio/Video/PDF — [Gemini models page](https://aistudio.google.com/docs/models)
- Gemini 3 family, current: `gemini-3.8-flash` (New), `gemini-3.8-live` and `gemini-3.8-live-extended-thinking` (Live API), `gemini-3.6-flash` (Stable), `gemini-3.5-flash-lite` (Stable), `gemini-3.1-flash-lite` (Stable), `gemini-3.1-pro-preview`, `gemini-3-flash-preview` (Preview), `gemini-3.1-flash-live-preview` (legacy; docs say move to 3.8 Live) — [Gemini models page](https://aistudio.google.com/docs/models)
- Gemini 2.5: `gemini-2.5-pro` is deprecated and routes to `gemini-3.8-flash` on Dec 1, 2026. `gemini-2.5-flash` is deprecated and routes to `gemini-3.5-flash-lite` on Dec 1, 2026. `gemini-2.5-flash-lite` is served "until further notice". Shut down: Gemini 2.0 Flash/Flash-Lite, Gemini 3 Pro Preview, 3.1 Flash-Lite Preview — [Gemini models page](https://aistudio.google.com/docs/models)
- Gemini 3.8 Flash on the Cloud side: model ID `gemini-3.8-flash`, GA, **1,048,576-token context, 65,536 max output**, input text/image/audio/video, output text. "Interactive video understanding" is named as a primary focus. Thinking levels are LOW / MEDIUM (default) / HIGH, and HIGH is suggested for "multi-step reasoning across 60+ minute videos". **`thinking_level="MINIMAL"` is not available** on 3.8 Flash. 3.8 Flash "consumes more tokens than 3.7 Flash", and the guide recommends 3.7 Flash when compute efficiency is the priority. Migrating to it means removing `temperature`/`top_p`/`top_k` etc. and swapping integer `thinking_budget` for a `thinking_level` enum — [Google Cloud developer guide: Gemini 3.8 Flash](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/guides/gemini-3-8-flash)
- Release date Sept 2, 2026. LVBench (long-video benchmark) scores reported as **87.8% in agentic mode and 87.1% in static mode** for 3.8 Flash, against 82.1% for GPT-5.6 Sol and 75.4% for Claude Opus 5. One caveat: Google reportedly gave Gemini/GPT 1,024 frames but Claude only 300 — [Vellum](https://www.vellum.ai/blog/gemini-3-8-flash-benchmarks-explained); [Emergent](https://emergent.sh/learn/gemini-3-8-flash-benchmarks). These are secondary sources; I did not reach Google's own eval page.

**Video tokenization and parameters (official video-understanding doc)**
- "All Gemini models can process video." Static processing is the default for every model, Gemini 4 included — [Video understanding docs](https://aistudio.google.com/docs/video-understanding)
- **Static mode:** frames are sampled at **1 FPS** with a timestamp added every second. Each frame costs **66 tokens at low `media_resolution`, otherwise 258 tokens**. Audio costs **32 tokens/s** (1 Kbps mono). The total is **about 100 tokens/s at low resolution and about 300 tokens/s at high resolution**, plus metadata. Fast action may lose detail at 1 FPS — [Video understanding docs](https://aistudio.google.com/docs/video-understanding)
- **Agentic mode** is supported on Gemini 4 Argon, 3.8 Flash, 3.6 Flash, 3.5 Flash-Lite and later. The model navigates the video itself. Reasoning is billed as `total_thought_tokens` and loaded frames/audio/transcript as `total_tool_use_tokens`. Google claims "up to 88% fewer" tokens and "~7% higher quality" on long-form content. On clips under 5 minutes or broad queries it may increase time-to-first-token and total tokens. The guidance is static for clips under 5 minutes and agentic for videos over 5–10 minutes or targeted queries. In stateless agentic conversations, all `processing_call`/`processing_result` steps must be sent back, or the video context is silently lost — [Video understanding docs](https://aistudio.google.com/docs/video-understanding)
- **Max length:** 1M-context models handle **up to 3 hours at low media resolution, or 1 hour at high/default resolution**. The page does not mention a 2M context — [Video understanding docs](https://aistudio.google.com/docs/video-understanding). Note that the page labels low resolution as the "(default)" here, which conflicts with its own token text saying "otherwise 258". Treat which resolution is the default as uncertain and set `media_resolution` explicitly.
- **Timestamps:** prompts use the `MM:SS` format (e.g. `01:15`) — [Video understanding docs](https://aistudio.google.com/docs/video-understanding)
- **Clipping and FPS:** `start_offset`/`end_offset` and `fps` (e.g. `"fps": 0.5`, one frame every 2 s) are set inside a `processing` object, **in static mode only**. The page's examples use 1200/1500 for the offsets but never state the units — [Video understanding docs](https://aistudio.google.com/docs/video-understanding). The older API used `videoMetadata` with offsets as strings like `"1250s"` [prior knowledge, not re-fetched], so check the field names against the SDK version you install.
- **Upload limits:** Files API maximum is **20 GB per file on paid, 2 GB on free**. A Cloud Storage registration option allows 2 GB per file with no storage cap. Inline data is listed as "<100MB" in the table, but the text says to use the Files API above 20 MB, so the page contradicts itself. Up to **10 videos per request** on Gemini 2.5 and later. MIME types: mp4, mpeg, mov, avi, x-flv, mpg, webm, wmv, 3gpp. YouTube URLs are in preview, public videos only. Put the text prompt after the video part. Use streaming or background execution for long requests — [Video understanding docs](https://aistudio.google.com/docs/video-understanding)

**Pricing (Gemini API, USD per 1M tokens; "→" marks a scheduled increase)** — all rows from [Gemini API pricing](https://aistudio.google.com/docs/pricing)

| Model | Input (text/img/video) | Output | Cache | Batch in / out | Free tier |
|---|---|---|---|---|---|
| Gemini 4 Argon | $2.00 → $4.00 | $10 → $20 | $0.10 → $0.20 | $1.00 / $5 (→ double) | No |
| Gemini 3.8 Flash / 3.6 Flash | $0.75 → $1.50 | $3.75 → $7.50 | $0.075 (+$0.50/hr storage) | $0.375 / $1.875 | Yes |
| Gemini 3.5 Flash-Lite | $0.30 | $2.50 | $0.03 | $0.15 / $1.25 | Yes |
| Gemini 3.1 Flash-Lite | $0.25 (audio $0.50) | $1.50 | $0.025 | $0.125 / $0.75 | Yes |
| Gemini 3.1 Pro Preview | $2.00 (≤200k) / $4.00 | $12 / $18 | $0.20 / $0.40 | $1.00 / $6 | No |
| Gemini 3 Flash Preview | $0.50 (audio $1.00) | $3.00 | $0.05 | $0.25 / $1.50 | Yes |
| Gemini 2.5 Flash-Lite | $0.10 (audio $0.30) | $0.40 | $0.01 | $0.05 / $0.20 | Yes |

- Scheduled changes: the page says most prices **double on Jan 1, 2027**, and Gemini 4 Argon's double on Dec 1, 2026 — [Gemini API pricing](https://aistudio.google.com/docs/pricing). A blanket doubling is unusual, so verify on the page before quoting it.
- The Batch API is about 50% of standard. On the free tier, "models may use your content to improve Google's products" — [Gemini API pricing](https://aistudio.google.com/docs/pricing)

### Inferences
- **Per-minute video cost at static 1 fps with no audio** (CCTV usually has none): low-res is 66 tok/s, about 4,000 tokens/min. That is about **$0.001/min on 3.1 Flash-Lite**, $0.0004/min on 2.5 Flash-Lite and $0.003/min on 3.8 Flash at current prices. Default resolution (258 tok/frame) costs about 3.9× more. Using `fps` 0.2–0.5 scales this down linearly.
- Fit for the three uses:
  - **(a) Verifying an alert clip** (a 10–30 s clip at 1–2 fps and default resolution, structured JSON verdict): 3.8 Flash, or 3.5 Flash-Lite for cost.
  - **(b) Background captioning:** 3.1 Flash-Lite or 2.5 Flash-Lite, with thinking off where possible, on the Batch API.
  - **(c) Agent "re-inspect what happened at table 5 at 20:00":** 3.8 Flash. Use static mode with clip offsets for windows under 5 minutes, and agentic mode for 20–60 minute windows.
- Gemini's timestamps are **relative to the clip** (MM:SS). The backend has to convert them to wall-clock time (clip_start + offset) before showing the owner. Never let the LLM do that arithmetic in free text.
- Since `gemini-2.5-*` IDs reroute on Dec 1, 2026, the hackathon code should pin current IDs: `gemini-3.8-flash`, `gemini-3.5-flash-lite` / `gemini-3.1-flash-lite`.

### Gaps
- I found no official per-model Video-MME, MLVU or EgoSchema numbers for the 3.x/4 models. LVBench figures come from secondary sources only.
- The units for `start_offset`/`end_offset` in the new `processing` object are not stated.
- I found no official Gemini latency numbers (TTFT per video length).
- I found no Vietnamese-specific quality evaluation of Gemini video captioning. The embeddings doc only says "100+ languages".

## 2. Gemini Live API for real-time CCTV streaming

### Takeaway
The Live API is built for interactive voice and video conversations, not passive multi-camera monitoring. Sessions are capped by a 128k context window (about 2 minutes of audio+video by default), connections last about 10 minutes, and keeping them going requires context-window compression and resumption. Don't use it for continuous CCTV. Use it at most as an optional "talk to the restaurant live" demo feature.

### Cited Findings
- Live models: `gemini-3.8-live` (low-latency voice), `gemini-3.8-live-extended-thinking`, and legacy `gemini-3.1-flash-live-preview` and `gemini-2.5-flash-native-audio-preview-12-2025` — [Gemini models page](https://aistudio.google.com/docs/models)
- 3.8 Live pricing: text input $0.75/M; audio $3.00/M or $0.005/min; **image/video $1.00/M or $0.002/min**. Output text $4.50/M, audio $12.00/M — [Gemini API pricing](https://aistudio.google.com/docs/pricing)
- Live sessions have a **128k-token context window**. Streamed data counts at **25 tokens/s for audio and 258 tokens/s for video**. That gives approximate session caps of **15 minutes audio-only and 2 minutes video+audio**. Connections last about **10 minutes**, with a GoAway notice about 60 s before the end. `contextWindowCompression` enables longer sessions — [Firebase AI Logic: Live API limits](https://firebase.google.com/docs/ai-logic/live-api/limits-and-specs); [Firebase: manage Live sessions](https://firebase.google.com/docs/ai-logic/live-api/sessions). These are Firebase pages and may lag behind 3.8 Live.
- Live API session resumption is off by default and must stay off for zero data retention — [Data governance](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/data-governance)

### Inferences
- Eight cameras would mean eight always-on WebSocket sessions that reconnect every ~10 minutes and lose context unless compressed. The model also only answers when prompted, so it produces no structured event log by itself. Edge YOLO plus event-triggered `generateContent` calls is simpler and cheaper.
- At $0.002/min, 8 cameras × 12 h is 5,760 min/day, or about **$11.5/day** in video input alone, before output and reconnect overhead. That is more than sparse batch captioning (see §8). Note that the per-minute and per-token prices don't reconcile (258 tok/s × 60 s × $1/M ≈ $0.0155/min), so Live may sample video below 1 fps. Unverified.

### Gaps
- I found no official latency figures for 3.8 Live, and no official session-length table for 3.8 Live itself; the aistudio Live docs URL returned 404.
- Vietnamese voice support in 3.8 Live is not confirmed. 3.5 Live Translate claims 70+ languages — [Gemini models page](https://aistudio.google.com/docs/models)

## 3. Embeddings and vector stores for indexing segments and frames

### Takeaway
**Gemini Embedding 2** (`gemini-embedding-2`) is now a unified multimodal embedding model covering text, image, video, audio and PDF, with 128–3072 output dimensions and Matryoshka support. Video embedding is limited to 2-minute clips and is priced high at $12/M tokens. For a hackathon, **embed the Vietnamese/English text captions plus one keyframe image per segment** at 768 or 1536 dimensions, and store them in **Supabase Postgres + pgvector**, which the team already uses. Don't embed raw video.

### Cited Findings
- `gemini-embedding-2` puts text, images, video, audio and documents in one embedding space and supports "over 100 languages". The input limit is **8,192 tokens shared across modalities**, and longer input is silently truncated. Images: up to 6 per request (PNG/JPEG). **Video: up to 120 s (MP4/MOV; H264/H265/AV1/VP9). Clips of 32 s or less are sampled at 1 fps; longer ones are uniformly sampled to 32 frames. Audio tracks are not processed.** For longer videos the docs say to chunk into overlapping segments. Output is 128–3072 dims (default 3072; recommended 768/1536/3072) via `output_dimensionality` (MRL), and truncated dims are auto-normalized. There is no `task_type` field; you use text prefixes instead (asymmetric: search result / question answering / fact checking). Separate `Content` objects return separate embeddings, while multiple parts in one content return a single aggregated embedding. Batch costs 50% — [Embeddings docs](https://aistudio.google.com/docs/embeddings)
- `gemini-embedding-001`: text only, 2,048 tokens, has `task_type`. **Its embedding space is incompatible with Embedding 2**, so switching means re-embedding everything — [Embeddings docs](https://aistudio.google.com/docs/embeddings)
- Pricing for Gemini Embedding 2 per 1M tokens: **text $0.20, image $0.45, audio $6.50, video $12.00**, with batch at half that. Embedding 001 costs $0.15 — [Gemini API pricing](https://aistudio.google.com/docs/pricing)
- Google-recommended stores: "Gemini Enterprise Agent Platform Vector Search 2.0", BigQuery, AlloyDB and Cloud SQL. Third-party: ChromaDB, Qdrant, Weaviate, Pinecone — [Embeddings docs](https://aistudio.google.com/docs/embeddings)
- NVIDIA's VSS uses **Cosmos-Embed1** for video, image and live RTSP embeddings — [NVIDIA VSS architecture](https://docs.nvidia.com/vss/latest/content/architecture.html)
- pgvector's HNSW index supports up to 2,000 dimensions for `vector` and 4,000 for `halfvec` — [pgvector GitHub](https://github.com/pgvector/pgvector) [prior knowledge, not re-fetched]

### Inferences
- **Recommended for the hackathon: pgvector on Supabase.** It has time-range filters, camera/table/person joins with the event tables, and `tsvector` keyword search, all in one SQL query. That makes hybrid search (SQL filter, then vector rank) trivial. Use `vector(768)` or `vector(1536)`; 3072 dims exceeds the HNSW `vector` limit unless you use `halfvec`. Vertex Vector Search 2.0 and BigQuery are overkill for 48 hours. AlloyDB is the "production on Google" path.
- Rough embedding costs (assumptions in §8):
  - Text captions: 11,520 segments/day × ~200 tokens ≈ 2.3M tokens, or **$0.46/day**.
  - Keyframes: 11,520 images × ~258 tokens (an assumption; the embedding doc doesn't give per-image token counts) ≈ $1.34/day.
  - Raw 30-s video embeddings: at a guessed ~258 tokens/frame × 30 frames ≈ 7.7k tokens/clip × $12/M ≈ $0.09/clip, so **about $1,000/day for 8 cameras**. That is prohibitive under this assumption, so embed captions and frames instead. Treat this number as assumption-sensitive.
- A free local option for frame embeddings is **SigLIP 2**, a multilingual image-text encoder ([arXiv 2502.14786](https://arxiv.org/abs/2502.14786), [prior knowledge, not re-fetched]), or Cosmos-Embed1. Run it on the edge box and store the vectors in pgvector. Text queries in Vietnamese would need SigLIP 2's multilingual text tower, or translation to English first.

### Gaps
- Token count per image/frame for Gemini Embedding 2 is not documented in what I fetched, so the video-embedding cost is an estimate.
- I found no Vietnamese retrieval benchmark for Gemini Embedding 2.
- Whether Gemini Embedding 2 is available in asia-southeast1 is not confirmed (see §9).

## 4. Open and on-device models for local captioning on an edge GPU

### Takeaway
The strongest Apache-2.0 options are **Gemma 4** (Apr 2, 2026: E2B/E4B with 128k context and text/image/video/audio input; 12B Unified; 26B-A4B MoE; 31B dense; with function calling) and **Qwen3-VL** (2B/4B/8B/32B dense plus 30B-A3B and 235B-A22B MoE, 256k context expandable to 1M, second-level timestamp grounding, vLLM support). NVIDIA's VSS blueprint ships Cosmos Reason 1/2 and Qwen3-VL as its swappable VLMs. For an edge box: Qwen3-VL-4B/8B or Gemma 4 E4B for 10–30 s clip captions, and the 26B-A4B MoE if a 24 GB+ GPU is available.

### Cited Findings
- **Gemma 4** (released **April 2, 2026**, Apache 2.0) — [Hugging Face blog: Welcome Gemma 4](https://huggingface.co/blog/gemma4):

  | Model | Parameters | Context | Modalities |
  |---|---|---|---|
  | E2B | 2.3B effective (5.1B with embeddings) | 128k | text/image/video/audio |
  | E4B | 4.5B effective (8B with embeddings) | 128k | text/image/video/audio |
  | 12B Unified | 11.95B dense, encoder-free | 256K | text/image/video/audio |
  | 26B A4B | MoE, 4B active | 256K | text/image/video |
  | 31B | dense | 256K | text/image/video |

  - Image token budgets: 70/140/280/560/1120.
  - MMMU-Pro: 31B 76.9%, 26B-A4B 73.8%, 12B 69.1%, E4B 52.6%, E2B 44.2%. MMMLU: 88.4 / 86.3 / 83.4 / 76.6 / 67.4.
  - Supports text and multimodal **function calling**.
  - Runtimes: transformers, llama.cpp, MLX, mistral.rs, transformers.js (WebGPU), SGLang.
  - The blog gives no video fps or length limits.
- Secondary sources say Gemma 4 video is limited to "a maximum of 60 seconds assuming images are processed at one frame per second". Sources disagree on whether the edge models support video — [Unsloth Gemma 4 guide](https://unsloth.ai/docs/models/gemma-4); [Remote OpenClaw](https://www.remoteopenclaw.com/blog/gemma-4-google-open-model)
- Gemma 4 is listed as available on the Gemini API free tier only, not the paid tier — [Gemini API pricing](https://aistudio.google.com/docs/pricing)
- **Qwen3-VL** — [QwenLM/Qwen3-VL GitHub](https://github.com/QwenLM/Qwen3-VL):
  - Releases: 235B-A22B (2025-09-23); 30B-A3B plus FP8 (2025-10-04); 4B/8B (2025-10-15); 2B/32B (2025-10-21). Each comes in Instruct and Thinking editions. Tech report is [arXiv 2511.21631](https://arxiv.org/abs/2511.21631).
  - Native **256K context, "expandable to 1M"** with YaRN.
  - Handles hours-long video with "full recall and second-level indexing", and **text-timestamp alignment** for event localization.
  - Video processor defaults to **2 fps**, configurable via `fps` or `num_frames`, `min_pixels`/`max_pixels` and `total_pixels` (keep below 24576×32×32). 256–1280 visual tokens per image.
  - OCR covers 32 languages, but Vietnamese is not named. Apache-2.0. Requires **vLLM ≥ 0.11.0**, and FP8 needs H100+.
- NVIDIA VSS 3.3.0 names **Cosmos Reason1/2 and Qwen3-VL** as swappable VLMs. Edge targets named are **DGX Spark, IGX Thor, AGX Thor** — [NVIDIA VSS architecture](https://docs.nvidia.com/vss/latest/content/architecture.html)

### Inferences
- **Throughput sketch (an inference, not measured):** 8 cameras each producing one 30 s caption every 30 s means about 0.27 clips/s. For Qwen3-VL-4B/8B in vLLM on one RTX 4090-class GPU, assume about 8–16 frames per clip at reduced pixels (≈2–4k visual tokens), about 150 output tokens and batched prefill. That plausibly sustains a few seconds per clip, so 8 cameras is borderline-feasible on one 24 GB GPU at sparse sampling. Benchmark on day 1 before committing.
- Local vs cloud: local keeps frames on-prem and has zero per-token cost, but captions are weaker in Vietnamese and fine-grained details. A pragmatic split is **local captions plus embeddings by default, and Gemini 3.8 Flash only for verification and on-demand re-inspection** of short clips.
- For the hackathon, the cloud-first path (Gemini 3.1 Flash-Lite batch) is faster to build. Keep the local path as a "privacy mode" toggle in the pitch.

### Gaps
- Not researched this session: Gemma 3n, PaliGemma 2, InternVL3/3.5, LLaVA-Video, VideoLLaMA3, Video-XL. Qwen3.5 / Qwen3.5-VL updates are also unverified.
- I found no measured tokens/s or clips/s for Qwen3-VL or Gemma 4 on RTX 4090 or Jetson Orin/Thor, and no Video-MME/MLVU/LongVideoBench numbers for these open models (the Qwen README shows them only as images).
- I found no Vietnamese captioning quality comparison between open VLMs and Gemini.

## 5. Video RAG and long-video QA: state of the art, and the best design for multi-camera, multi-day surveillance QA

### Takeaway
The 2025–2026 research trend is to turn video into **compact structured memory** (event logs, event or scene graphs, entity memory) plus captions and embeddings, then retrieve and **re-inspect raw frames only on demand**. That is exactly the "edge event DB + semantic captions + VLM re-inspection" hybrid. Production references are **NVIDIA's VSS blueprint** (dense captions plus Context-Aware RAG over vector and graph stores, and an Alerts microservice in which a VLM verifies alerts) and Gemini's own **agentic video mode**. For Easy FnB: **event-triggered captioning plus low-rate background captioning**, a structured Postgres event DB as the primary source of truth, and on-demand clip inspection.

### Cited Findings
- **Semantic Event Graphs** (arXiv 2601.06097, Jan 2026): replaces raw frames with **compact temporal interaction logs** as a symbolic interface between video and LLM. A short-context baseline limited to the last 30 s "collapses to 2.5% accuracy" on long-form QA — [arXiv 2601.06097](https://arxiv.org/abs/2601.06097)
- **Event-Causal RAG** (arXiv 2605.06185, May 2026): stores event graphs in a **dual vector + graph memory**. Bidirectional graph retrieval recovers predecessor and successor events at QA time. Introduces the hour-scale causal benchmark ECV-1H — [arXiv 2605.06185](https://arxiv.org/abs/2605.06185)
- **Rethinking RAG in Long Videos** (arXiv 2606.13141): builds V-RAGBench (query, evidence chunk, answer triplets from hour-scale egocentric video) to study what to retrieve and how to use it — [arXiv 2606.13141](https://arxiv.org/html/2606.13141v1)
- **R4DSG** (arXiv 2608.11017, ACM MM 2026): relative 4D scene-graph memory for object-centric QA in long egocentric video, evaluated on an EgoLifeQA object subset — [arXiv 2608.11017](https://arxiv.org/abs/2608.11017)
- **VideoRAG** (HKUDS, arXiv 2502.01549): RAG over "extreme long-context videos" — [arXiv 2502.01549](https://arxiv.org/pdf/2502.01549). The GitHub repo is HKUDS/VideoRAG [prior knowledge, not re-fetched].
- Earlier agent and memory baselines [prior knowledge, not re-fetched]:
  - **VideoAgent, memory-augmented** ([arXiv 2403.11481](https://arxiv.org/abs/2403.11481)): temporal caption memory plus an **object memory queried via SQL**. This is the closest academic analogue to "query_events SQL plus captions".
  - **VideoAgent, LLM as agent** ([arXiv 2403.10517](https://arxiv.org/abs/2403.10517)): iteratively selects a few frames to answer EgoSchema-style questions.
  - **Video-RAG** ([arXiv 2411.13093](https://arxiv.org/abs/2411.13093)): retrieves auxiliary texts (OCR, ASR, object detection) aligned to the video.
  - **Deep Video Discovery** ([arXiv 2505.18079](https://arxiv.org/abs/2505.18079)): agentic search tools over segmented video and strong LVBench results.
- **NVIDIA VSS** [2.4.1 docs](https://docs.nvidia.com/vss/2.4.1/content/architecture.html) and [blueprint card](https://build.nvidia.com/nvidia/video-search-and-summarization/blueprintcard):
  - Ingestion produces VLM captions and scene descriptions plus audio transcripts, stored in **vector and graph databases**.
  - **Context-Aware RAG (CA-RAG)** handles summarization and Q&A. Retrieved context is reranked by NeMo before the answer is generated.
  - Summaries are built by **recursively summarizing dense chunk captions with an LLM**.
  - The 2.4 coverage says chunks are captioned by Cosmos Reason and an LLM builds a knowledge graph of entities, events and relationships — [hyper.ai (secondary)](https://hyper.ai/en/stories/d83d6e876212bfd6c0feaea67105b0d1)
- **NVIDIA VSS 3.3.0** (current docs) — [VSS architecture (latest)](https://docs.nvidia.com/vss/latest/content/architecture.html):
  - Real-time CV via DeepStream (RT-DETR, Grounding DINO, Sparse4D multi-camera 3D tracking) and RT-Embedding via Cosmos-Embed1 on RTSP streams.
  - RT-VLM for captions and incident/anomaly detection.
  - An **Alerts microservice** pulls the matching video segment and has a VLM verify each alert, giving **confirmed / rejected / unverified** with reasoning traces, written to Elasticsearch and optionally Kafka.
  - Behavior Analytics covers tripwire, ROI entry/exit and rule violations, from Kafka/Redis/MQTT metadata.
- Gemini's built-in **agentic video processing** is itself a form of on-demand long-video retrieval, with up to 88% fewer tokens on long-form content — [Video understanding docs](https://aistudio.google.com/docs/video-understanding)

### Inferences
- **Recommended Easy FnB indexing design:**
  1. **Primary layer: structured events (source of truth).** The edge box (YOLO, tracking, pose, face/staff re-ID, table-zone polygons) writes rows such as `events(id, ts_start, ts_end, camera_id, type, table_id, person_id, track_id, confidence, clip_uri)` and derived tables (`table_sessions`: seat → order → served → paid/leave, with wait times; `person_presence`: first_seen, last_seen, cameras). Most owner questions — "when did John arrive", "which table", "waits over 10 minutes" — are **pure SQL**. No VLM needed.
  2. **Event-triggered VLM** for semantic and verification events (drop/break, fall, spill, argument, a table flagged for a long wait). Send a clip of event ±10 s at 1–2 fps and default resolution to Gemini (3.5 Flash-Lite or 3.8 Flash). Request **structured JSON**: `{verdict: confirmed|rejected|uncertain, description_vi, actors, objects, evidence_timestamps}`. This mirrors the VSS Alerts verdict pattern.
  3. **Low-rate background captions** (e.g. one 60 s segment per camera at 0.2–0.5 fps and low resolution, via the Batch API or a local Qwen3-VL). These catch things the detectors don't model ("someone moved a chair to table 5"). Store `segments(camera_id, start, end, caption_vi, caption_en, tags, table_ids, keyframe_uri, embedding)`.
  4. **Hierarchical summaries:** hourly rollups per camera, then shift/day summaries, stored as rows. They serve the agent for broad questions and feed the end-of-shift report.
  5. **On-demand re-inspection:** when the retrieved evidence is ambiguous, the agent calls Gemini on the original clip (static mode with clip offsets for under 5 minutes, agentic mode for longer windows) and answers from that.
- Fixed-interval vs event-triggered: fixed-interval gives coverage, while event-triggered gives precision and low cost. The hybrid above, with sparse background and dense on events, is the best fit for 8 cameras and a modest budget.
- Multi-camera, multi-day: key everything by wall-clock time (one timezone, Asia/Ho_Chi_Minh), camera_id and zone/table_id, so that "table 5 at 20:00" resolves to camera(s) plus a time window through a static camera→table mapping.

### Gaps
- I found no surveillance- or restaurant-specific video-RAG benchmark. The research uses egocentric or movie long-video benchmarks (EgoSchema, LVBench, Video-MME, MLVU, LongVideoBench); leaderboard numbers were not collected this session.
- I didn't collect other open-source GitHub projects for natural-language CCTV search (beyond VSS and VideoRAG), or Twelve Labs details.
- The VSS GitHub repo URL and license were not shown on the fetched page. It is believed to be github.com/NVIDIA-AI-Blueprints/video-search-and-summarization [prior knowledge, not re-fetched].

## 6. Agent framework (ADK / Agent Runtime / function calling), tool design, and grounding answers in timestamps

### Takeaway
Use **Google ADK** (`pip install google-adk`) with an LlmAgent on `gemini-3.8-flash`, or `gemini-3.5-flash-lite` for cheaper turns. Expose a small set of **typed, parameterized tools** over Postgres plus clip and VLM tools; don't let the model write raw SQL. Deploy on **Cloud Run** for the hackathon, since it's simpler than Agent Runtime. Grounding comes from the rule that every answer cites `event_id`/`segment_id` with wall-clock timestamps and a clip link generated by the backend, plus an explicit "no evidence found" path.

### Cited Findings
- ADK (adk.dev): **ADK TypeScript 2.0 GA** with Graph Workflows ("New in ADK 2.0"); Go v2.x. Languages: Python, TypeScript, Go, Java, Kotlin — [ADK docs](https://adk.dev/)
  - Agents: LlmAgent, Sequential/Parallel/Loop workflow agents, graph workflows, agent routing.
  - Tools: function tools, **MCP tools**, OpenAPI tools, auth, built-ins such as Google Search.
  - State and context: sessions, state, memory, artifacts, events, **context compression and context caching**.
  - "Live and Voice Agents" (audio/video).
  - Deploy: **Agent Runtime (Agent Platform), Cloud Run, GKE**, or self-host.
  - Also: evaluation (criteria, user simulation), **A2A**, Dev UI (`adk web`) with a Visual Builder, API server, Cloud Trace observability.
- Gemini 3.8 Flash function-calling rules: each `FunctionResponse` must match the preceding `FunctionCall`'s id, name and count. **Multimodal assets belong inside the function response payload**, which is how a tool can return keyframes or clips for the model to look at — [Gemini 3.8 Flash guide](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/guides/gemini-3-8-flash)
- Google's "MCP Toolbox for Databases" (googleapis/genai-toolbox) exposes Postgres/AlloyDB/Cloud SQL queries as MCP tools — [GitHub](https://github.com/googleapis/genai-toolbox) [prior knowledge, not re-fetched; the ADK home page did not mention it]

### Inferences
- **Proposed tool set** (all return rows with `event_id`/`segment_id`, `camera_id`, `ts_start`/`ts_end` in Asia/Ho_Chi_Minh time, and `clip_url`):
  1. `resolve_entities(text)` — maps "John", "anh Minh", "bàn 5", "chiều nay" (this afternoon) to person_id, table_id and a time range, using a staff/regular roster and the restaurant's shift config.
  2. `query_events(type?, table_id?, person_id?, camera_id?, t_from, t_to, limit)` — a parameterized SQL template. If free SQL is ever needed, use a read-only DB role, views only, and a statement timeout.
  3. `person_timeline(person_id, date)` — first/last seen, zones and tables visited.
  4. `table_timeline(table_id, t_from, t_to)` — seat, order, serve and leave events with computed wait times.
  5. `wait_time_report(date, threshold_min)` — answers "did any table wait more than 10 minutes" deterministically.
  6. `semantic_scene_search(query_vi, t_from?, t_to?, camera_id?, k)` — hybrid search: SQL filter, then pgvector cosine on caption/keyframe embeddings, plus tsvector keywords.
  7. `get_clip(camera_id, t_start, t_end)` — returns a signed URL; the app UI renders the player.
  8. `inspect_clip_with_vlm(camera_id, t_start, t_end, question)` — calls Gemini 3.8 Flash on that clip (static mode with offsets or agentic mode) and returns structured JSON with evidence offsets, which the backend converts to absolute times.
  9. `get_shift_summary(date, shift)`.
- **Anti-hallucination rules:**
  - The system prompt requires every factual sentence to cite IDs and times returned by tools.
  - The backend renders timestamps and clip links from the cited IDs, so the LLM never invents them.
  - If a tool returns nothing, answer "Không tìm thấy bằng chứng trong dữ liệu camera" (no evidence found in the camera data) and suggest an inspection.
  - Accusation-type questions ("who broke a bowl") must go through `inspect_clip_with_vlm` before naming a person, and the answer is phrased with confidence ("có vẻ là" / "it appears to be") plus the clip.
  - Log tool traces in ADK for the demo.
- Use ADK's `adk web` for a 48-hour demo, with FastAPI/Cloud Run as the backend for the owner app and a Zalo webhook. Agent Runtime is optional.

### Gaps
- I didn't fetch ADK's specific docs on the Gemini Live/bidi-streaming integration, Agent Runtime pricing, or regional availability.
- I found no published grounding or hallucination evaluation for video-QA agents in a surveillance setting.

## 7. End-of-shift / end-of-day summaries

### Takeaway
Compute metrics deterministically in SQL first (covers, table turns, average and maximum wait, tables over 10 minutes, staff presence, incidents with verified verdicts). Then have the LLM write a short Vietnamese narrative **only from that JSON plus the verified-incident list**, with hierarchical rollups (hourly, then shift). This matches NVIDIA VSS's recursive dense-caption summarization while keeping the numbers exact.

### Cited Findings
- VSS summarization: VLM captions and audio transcripts are summarized together by an LLM into an aggregated summary. The agent **recursively summarizes dense captions with an LLM until all chunk captions are processed** — [VSS 2.4.1 architecture](https://docs.nvidia.com/vss/2.4.1/content/architecture.html); [NVIDIA blueprint card](https://build.nvidia.com/nvidia/video-search-and-summarization/blueprintcard)
- Semantic Event Graphs show that compact temporal interaction logs work as LLM input for long-form reasoning — [arXiv 2601.06097](https://arxiv.org/abs/2601.06097)
- The Batch API halves cost for latency-tolerant jobs such as nightly summaries — [Gemini API pricing](https://aistudio.google.com/docs/pricing)

### Inferences
- **Pipeline at shift end** (cron or Supabase scheduled function):
  1. Run SQL metrics into JSON.
  2. Pull hourly caption rollups and all `confirmed`/`uncertain` incidents with clip links.
  3. Call Gemini (3.5 Flash-Lite is enough) with a fixed Vietnamese template:
     - headline KPIs
     - service issues (tables over the wait threshold, with times)
     - incidents (with clips)
     - staff notes (late arrival / absence)
     - recommendations
  4. Validate that every number in the narrative appears in the JSON (a regex check), and regenerate if not.
  5. Send to Zalo OA / the app with deep links to clips.
- Cost is negligible: about 20–50k input tokens per summary is a fraction of a cent on Flash-Lite.

### Gaps
- I found no published best-practice study specific to restaurant shift reports. The recommendations are synthesized from the VSS pattern and general LLM practice.
- Zalo OA messaging API details were not researched here.

## 8. Cost estimate: 8 cameras × 12 h/day, Gemini vs local

### Takeaway
At current (Nov 2026) prices, **sparse cloud captioning is cheap**: about $1–3/day (about $30–90/month) at 0.2 fps low resolution on 2.5 or 3.1 Flash-Lite, and about $3.4–9.5/day at 1 fps low resolution. Event-triggered verification on 3.8 Flash adds about $2/day, and agent Q&A about $1/day. Prices reportedly double from Jan 1, 2027. Local Qwen3-VL/Gemma 4 has zero token cost but needs a 24 GB-class GPU, and its throughput is unverified.

### Cited Findings
- Token rates — [Video understanding docs](https://aistudio.google.com/docs/video-understanding):
  - 66 tokens/frame at low resolution, 258 at default; 1 fps default; 32 tok/s audio.
  - Configurable `fps` (e.g. 0.5).
- Prices per 1M input/output tokens — [Gemini API pricing](https://aistudio.google.com/docs/pricing):

  | Model | Standard (in / out) | Batch (in / out) |
  |---|---|---|
  | 2.5 Flash-Lite | $0.10 / $0.40 | $0.05 / $0.20 |
  | 3.1 Flash-Lite | $0.25 / $1.50 | $0.125 / $0.75 |
  | 3.5 Flash-Lite | $0.30 / $2.50 | $0.15 / $1.25 |
  | 3.8 Flash | $0.75 / $3.75 (→ $1.50 / $7.50 on Jan 1, 2027) | $0.375 / $1.875 |

### Inferences (all numbers are my calculations; assumptions stated)
- **Assumptions:**
  - 8 cameras × 12 h = 96 camera-hours = **345,600 camera-seconds/day**. No audio.
  - Continuous mode uses 30 s segments (11,520 requests/day) with about 400 prompt tokens and about 150 caption tokens each. Sparse mode uses 60 s segments (5,760 requests/day).
  - Thinking off or minimal on Flash-Lite. Static-mode metadata and timestamp tokens are ignored, so add about 10%.
- **Scenario A: 1 fps, low resolution (66 tok/frame), 30 s segments.** Video ≈ 22.8M plus prompts 4.6M ≈ **27.4M input**, plus **1.73M output** tokens/day.
  - 2.5 Flash-Lite: ≈ **$3.4/day** (~$103/mo); batch ≈ $1.7/day
  - 3.1 Flash-Lite: ≈ **$9.5/day** (~$283/mo); batch ≈ $4.7/day
  - 3.8 Flash: ≈ $27/day (~$810/mo), plus thinking tokens, since 3.8 Flash has no MINIMAL level; it doubles in 2027.
- **Scenario A′: 1 fps, default resolution (258 tok/frame)** ≈ 89.2M video tokens/day. Roughly 3.3× Scenario A's input cost (e.g. ≈ $26/day on 3.1 Flash-Lite).
- **Scenario B: 0.2 fps (1 frame every 5 s), low resolution, 60 s segments.** Video ≈ 4.56M plus prompts 2.3M ≈ **6.9M input**, plus **0.86M output** tokens/day.
  - 2.5 Flash-Lite: ≈ **$1.0/day** (~$31/mo)
  - 3.1 Flash-Lite: ≈ **$3.0/day** (~$90/mo); batch ≈ $1.5/day
  - 3.8 Flash: ≈ $8.4/day
- **Scenario C: event-triggered verification only.** 400 clips/day × 20 s × 1 fps × 258 tokens ≈ 2.06M plus prompts 0.2M input; output ≈ 0.08M.
  - 3.1 Flash-Lite: ≈ $0.7/day
  - **3.8 Flash: ≈ $2.0/day** (~$60/mo)
- **Agent Q&A:** 30 questions/day × (≈10k context tokens plus one 2-minute clip inspection ≈ 31k tokens) ≈ 1.2M input on 3.8 Flash, or ≈ **$1/day**.
- **Embeddings:** text captions ≈ $0.46/day; keyframes ≈ $1.3/day; raw-video embeddings are prohibitive (see §3).
- **Recommended combination for production:** B (background, batch, 3.1 Flash-Lite) + C (3.8 Flash) + Q&A + embeddings ≈ **$5–6/day, about $150–180/month** at current prices for 8 cameras. Expect it to roughly double after Jan 2027 if the scheduled increases happen.
- **Hackathon:** a demo with a few hours of footage from 2–4 cameras costs under $5 on paid tier. The free tier is available for Flash/Flash-Lite, but **free-tier content may be used to improve Google products**, so use only staged or demo footage there.
- **Local alternative:** one 24 GB GPU edge box (e.g. RTX 4090-class) running Qwen3-VL-4B/8B or Gemma 4 E4B via vLLM or llama.cpp. Marginal cost is electricity plus hardware amortization. It is feasible at Scenario B density, while Scenario A density for 8 cameras is uncertain. Keep Gemini only for C and Q&A (hybrid).

### Gaps
- I found no measured local VLM throughput or power figures, and no Vietnam electricity or hardware prices, so I can't give a local cost in VND.
- How long the Jan 2027 price doubling will last is unverified.

## 9. Privacy, data governance and region (asia-southeast1)

### Takeaway
On the paid Gemini API and Vertex / "Gemini Enterprise Agent Platform", Google says it **won't train on customer data without permission**. Prompts may be logged for abuse detection, and implicit caching keeps data for up to 24 hours unless disabled. The **free AI Studio tier may use content to improve products**, so never use real customer CCTV on the free tier. Singapore (asia-southeast1) appears in the location tables for the Gemini 3.x and Embedding 2 rows, but availability per model was not confirmed, and endpoints carry **no in-region ML processing guarantee** unless listed under data residency. Gemini 3.8 Flash's guide lists only Global and Multi-region endpoints. Best privacy posture: keep video and faces on-prem, send only short event clips or blurred keyframes to the cloud, and keep identity mapping local.

### Cited Findings
- "Google won't train or fine-tune models on your data without prior permission or instruction", covering all managed models including pre-GA — [Data governance (docs.cloud.google.com)](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/data-governance)
- Implicit caching is on by default, in two tiers — [Data governance](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/data-governance):
  - in-memory, "deleted no later than 24 hours after it's written"
  - durable, at rest, deleted within 24 hours
  - Disable it with a PATCH to `cacheConfig` setting `"disableCache": true` (requires `roles/aiplatform.admin`), or keep in-memory only with `retentionType: EPHEMERAL`.
- Google "may log prompts to detect potential abuse" — [Data governance](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/data-governance)
- Zero-data-retention steps — [Data governance](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/data-governance):
  - keep request-response logging off (the default)
  - set `store=false` on the Interactions API (default `true`)
  - leave Live API session resumption off
  - disable caching
  - avoid Grounding with Google Search, which keeps logs for 3 days and can't be disabled
- With the global endpoint, requests and cached data "can be served from any region" — [Data governance](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/data-governance)
- The free tier on the Gemini API: "models may use your content to improve Google's products" — [Gemini API pricing](https://aistudio.google.com/docs/pricing)
- The locations page has a Singapore (asia-southeast1) column with rows for Gemini 3.8 Flash, 3.6 Flash, 3.5 Flash-Lite, 3.1 Flash-Lite, 3.1 Pro (preview), 2.5 Flash, 2.5 Flash-Lite, Gemini Embedding 2 and Embeddings for Multimodal. The availability cells could not be read. The page says "Endpoints don't guarantee data residency or in-region ML processing", and advises against the global endpoint "if you have ML processing requirements" — [Vertex/Agent Platform locations](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/locations)
- Gemini 3.8 Flash locations: "Global" and "Multi-region", with asia-southeast1 not listed. The quickstart uses `location="global"` — [Gemini 3.8 Flash guide](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/guides/gemini-3-8-flash)
- The Singapore region was reported (Oct 2025) among the first with expanded data residency guarantees for enterprise AI services, including Gemini 2.5 Flash on Vertex — [TechEdt](https://www.techedt.com/google-cloud-expands-gemini-ai-footprint-in-singapore-with-new-commitments) (secondary source)

### Inferences
- **Recommended posture:**
  - Raw video and the face-embedding/identity table stay on the edge box or in the restaurant's storage.
  - The cloud sees only short event clips or keyframes, optionally with faces blurred, keyed by pseudonymous `person_id`. The name mapping is resolved locally or in the app DB, never in the prompt.
  - Use the paid tier or Vertex with caching disabled.
  - Use Supabase hosted in Singapore for the DB.
  - Offer the "on-prem mode" (local Qwen3-VL/Gemma 4) as a selling point.
- Vietnam's Personal Data Protection Law (Law 91/2025/QH15, effective Jan 1, 2026) and Decree 13/2023 treat biometric/face data as sensitive and regulate cross-border transfer. [prior knowledge, not re-fetched; another researcher may cover legal.] This strengthens the case for on-prem face recognition and sending only de-identified clips abroad, since Singapore counts as cross-border.

### Gaps
- Exact per-model availability in asia-southeast1 couldn't be read from the locations table, and whether Gemini 3.8 Flash is served regionally in Singapore is unconfirmed.
- I didn't fetch the AI Studio paid-tier Gemini API terms (data logging and retention on the paid tier) directly.
- Vietnamese legal requirements on CCTV/biometric cross-border transfer were not verified in this session.
