# Small VLMs, Gemini verification and temporal gesture recognition for Easy FnB (restaurant CCTV), as of Nov 2026

Research date: 2026-11-04. All Google pages were fetched that day. The Gemini API docs have moved: `ai.google.dev/gemini-api/docs/*` now returns 301 redirects to `aistudio.google.com/docs/*`. The model line-up is much newer than mid-2025 knowledge: Gemini 3.x and 4 models exist, and Gemini 2.5 Flash is deprecated. Page content was read through a summarising fetch tool, so key prices should be rechecked on the live page before the demo.

## Q1. Gemini options for verifying event crops (models, latency, price, image tokens, rate limits, multi-image, Live API, Gemini API vs Vertex on Cloud Run)

### Takeaway
The best verifier is **`gemini-3.5-flash-lite`** (GA, stable). Google's own docs recommend it with the default `MINIMAL` thinking level for "high-throughput classification, routing, or JSON extraction". It costs $0.30 per 1M input tokens and $2.50 per 1M output tokens. One low-resolution image is 280 tokens, so a single event check costs about **$0.0002**. `gemini-2.5-flash-lite` ($0.10 / $0.40) is still served and costs about 5× less, which makes it the cheapest fallback. The Live API is a poor fit for CCTV: it takes at most 1 fps, and audio+video sessions are capped at 2 minutes.

### Cited Findings
**Model names and status (seen 2026-11-04)**
- The models page lists these as current: `gemini-4-argon` ("flagship reasoning model", 1M context), `gemini-3.8-flash` (New, "most intelligent Flash model"), `gemini-3.6-flash` (Stable, previous-generation Flash), `gemini-3.5-flash-lite` (Stable, "Our fastest, most cost-effective 3.5 model for high-throughput execution"), `gemini-3.1-flash-lite` (Stable, "cost-efficient multimodal") and `gemini-3-flash-preview` (Preview). `gemini-3-pro-preview`, `gemini-3.1-flash-lite-preview`, `gemini-2.0-flash` and `gemini-2.0-flash-lite` are shut down. — [Gemini API models (AI Studio docs)](https://aistudio.google.com/docs/models)
- `gemini-2.5-flash` is deprecated and will route to `gemini-3.5-flash-lite` on 1 Dec 2026. `gemini-2.5-pro` will route to `gemini-3.8-flash`. `gemini-2.5-flash-lite` is "served until further notice", but new projects are told to use 3.5 Flash-Lite or 3.8 Flash. — [Gemini API models](https://aistudio.google.com/docs/models); same routing stated on [Gemini API pricing](https://aistudio.google.com/docs/pricing)

**Prices (paid tier, per 1M tokens; text, image and video input are priced the same; seen 2026-11-04)**
- `gemini-3.5-flash-lite`: $0.30 in / $2.50 out; Batch $0.15 / $1.25; free tier available. — [Gemini API pricing](https://aistudio.google.com/docs/pricing)
- `gemini-3.1-flash-lite`: $0.25 in / $1.50 out; Batch $0.125 / $0.75; free tier available. — [Gemini API pricing](https://aistudio.google.com/docs/pricing)
- `gemini-2.5-flash-lite`: $0.10 in / $0.40 out; Batch $0.05 / $0.20; free tier available. — [Gemini API pricing](https://aistudio.google.com/docs/pricing)
- `gemini-3-flash-preview`: $0.50 / $3.00. `gemini-3.6-flash` and `gemini-3.8-flash`: $0.75 / $3.75, **rising to $1.50 / $7.50 on 1 Jan 2027**. `gemini-3.1-pro-preview`: $2 / $12, no free tier. `gemini-4-argon`: $2 / $10, rising to $4 / $20 on 1 Dec 2026, no free tier. — [Gemini API pricing](https://aistudio.google.com/docs/pricing)
- The pricing page lists Gemma 4 as free-tier only (free input and output, no paid tier). It gives no model ID. — [Gemini API pricing](https://aistudio.google.com/docs/pricing)
- Live models (`gemini-3.8-live`, `gemini-3.8-live-extended-thinking`, `gemini-3.1-flash-live-preview`): $0.75 text / $1.00 image-video input per 1M; $4.50 text output; free tier available. — [Gemini API pricing](https://aistudio.google.com/docs/pricing)

**Image token cost and resolution control**
- On Gemini 3 and Gemini 4, `media_resolution` sets tokens per image: `low` = 280, `medium` = 560, `high` = 1120, `ultra_high` = 2240. The default (unspecified) is 1120. Resolution can be set per part (per image) on Gemini 3 and 4. Google calls `high` "Recommended for most image analysis tasks", suggests low or medium for simpler context images, and says to "Always test and evaluate" the effect of each setting. — [Media resolution docs](https://aistudio.google.com/docs/media-resolution)
- Older token rule: an image with both sides ≤384 px costs 258 tokens. Larger images are tiled into 768×768 tiles at 258 tokens each; for example, 960×540 gives 6 tiles, about 1,548 tokens. — [Image understanding docs](https://aistudio.google.com/docs/image-understanding)
- One request can hold up to 3,600 image files. Inline data counts toward a 20 MB total request limit. Several images can go in one `input` array so they are compared in a single prompt. Image input can be combined with a JSON `response_format` plus a schema. Google advises putting the text prompt before the image when there is a single image. — [Image understanding docs](https://aistudio.google.com/docs/image-understanding)

**Structured output, thinking and regions (Vertex / Google Cloud page for 3.5 Flash-Lite)**
- `gemini-3.5-flash-lite` accepts text, image, audio and video input and up to 3,000 images per prompt. Structured output (controlled generation) is supported. Thinking defaults to `MINIMAL`, which Google describes as meant for "high-throughput classification, routing, or JSON extraction tasks". The page warns that minimal thinking can cut multi-step tool use short. ML-processing regions are `us`, `eu` and `asia-south1`; Standard PayGo is `global`, `us` and `eu`. The page gives no numeric latency. — [Google Cloud docs: Gemini 3.5 Flash-Lite](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/3-5-flash-lite)
- The Google Cloud documentation URL now sits under "gemini-enterprise-agent-platform" and refers to an "Agent Platform API". The fetched page does not say whether this is a rename of Vertex AI. — [Google Cloud docs: Gemini 3.5 Flash-Lite](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/3-5-flash-lite)
- A search summary gives 3.5 Flash-Lite's GA date as 21 July 2026, with retirement on or after 21 July 2027. The fetched Google Cloud page did not show these dates, so they are not confirmed against the primary source. — [search summary incl. Google Cloud page](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/3-5-flash-lite), [ai-tldr](https://ai-tldr.dev/models/gemini-3-5-flash-lite/)

**Latency (third-party only; no official figures found)**
- Vercel AI Gateway lists about 0.6 s and 0.9 s latency for two providers of 3.5 Flash-Lite, with 388 and 257 tokens/s throughput. These figures come from a search snippet and were not fetched. — [Vercel AI Gateway latency page](https://vercel.com/ai-gateway/models/gemini-3.5-flash-lite/latency)
- One independent blog measured time-to-first-token of about 1.2 s for Gemini 3.5 Flash at minimal thinking and about 0.62 s for 3.1 Flash-Lite. It also notes that 3.5 Flash-Lite and 3.1 Flash-Lite are different models. This is from a search snippet and is a single author's measurement. — [Nipun Batra blog, 2026-05-20](https://nipunbatra.github.io/blog/posts/2026-05-20-gemini-3.5-flash-and-omni.html)

**Rate limits**
- The rate-limits page does **not** publish per-model RPM/TPM/RPD for the free tier or Tier 1: "Rate limits … can be viewed in Google AI Studio." Limits apply per project, not per API key, and RPD resets at midnight Pacific. Preview and experimental models have tighter limits. Tier 1 has a spend cap of $10 per rolling 10 minutes. The only Tier 1 per-model numbers shown are Batch enqueued-token limits: 3.5 Flash-Lite, 3.1 Flash-Lite and 2.5 Flash-Lite at 10M; 3.6, 3.8 and 2.5 Flash at 3M; 3.1 Pro Preview at 5M. — [Rate limits docs](https://aistudio.google.com/docs/rate-limits)

**Live API**
- Frames are sent as separate JPEG or PNG images at "max 1 frame per second". `mediaResolution` sets tokens per frame. Audio+video sessions are limited to 2 minutes and audio-only sessions to 15 minutes; session management can extend them. Supported models are Gemini 3.8 Live, 3.8 Live Extended Thinking, 3.1 Flash Live Preview and 2.5 Flash Live Preview. Function calling is supported on 3.8 Live (non-blocking by default) but not on 3.1 Flash Live Preview. The page gives no latency figures and does not cover structured output. — [Live API capabilities](https://aistudio.google.com/docs/live-api/capabilities)

**Gemini API vs Vertex AI on Cloud Run**
- The Gemini Developer API and the Vertex AI Gemini API both work through the unified Google Gen AI SDK (`google-genai`), so moving between them is mostly a client-configuration change. The Developer API authenticates with an API key. Vertex authenticates with IAM / Application Default Credentials, and the Cloud Run service account is picked up automatically (`vertexai=True`, project, location). One guide warns that if `GOOGLE_API_KEY` or `GEMINI_API_KEY` is set, the SDK may prefer the key over ADC. — [Google: migrate to cloud](https://ai.google.dev/docs/migrate_to_cloud?hl=vi), [python-genai auth docs (mintlify)](https://mintlify.com/googleapis/python-genai/concepts/authentication), [DEV Community guide](https://dev.to/bravian1/how-to-use-your-google-cloud-credits-for-gemini-again-via-vertex-ai-and-adc-7ei)

### Inferences
- **Cost per verification, worked out from the published prices.** Assume one person crop at `low` (280 tokens), about 150 prompt tokens and about 40 output tokens of JSON.
  - 3.5 Flash-Lite: 430 × $0.30/1M + 40 × $2.50/1M ≈ **$0.00023** per event.
  - 3.1 Flash-Lite: ≈ $0.00017.
  - 2.5 Flash-Lite: crop resized to ≤384 px (258 tokens); ≈ **$0.00004**.

  At 1,000 events per day per restaurant, that is about $0.04–$0.23 per day. Cost is not the constraint; latency and rate limits are.
- **Sending a few frames instead of one crop.** The main confusion is "hand in hair / holding a glass" versus "calling staff". Sending 3 low-res crops in one request (about 0.6 s before, at the peak, about 0.6 s after) plus one `medium` scene crop costs about 1,400 tokens, roughly $0.0005 on 3.5 Flash-Lite. This gives the verifier motion context that a single crop lacks. Per-part `media_resolution` (Gemini 3+) lets the scene crop use a higher setting than the person crops.
- **Schema.** Use a strict response schema with an enum to avoid free-text parsing. For example:
  `{verdict: "calling_staff" | "touching_hair" | "drinking" | "eating" | "phone" | "other", hand_open: bool, confidence: 0–1}`
  For tables: `{state: "needs_clearing" | "set_for_service" | "occupied_eating" | "empty_clean", evidence: [...]}`. The table enum explicitly separates "set glasses/condiments" from "used dishes".
- **Model choice for the demo.** Use `gemini-3.5-flash-lite` with thinking `MINIMAL`. It is GA, it is Google's recommended classification tier, and it is what 2.5 Flash traffic will be routed to. Avoid 3.6/3.8 Flash for per-event checks: they cost about 2.5× more now and their prices double on 1 Jan 2027. Avoid preview models: they have tighter rate limits and can be shut down (3-pro-preview and 3.1-flash-lite-preview already have been).
- **Latency.** Expect about 0.6–1.2 s model time per call (third-party figures) plus the network round trip from Vietnam, so roughly 1–2 s end-to-end. That is fine for a "notify staff" event, but it argues for asynchronous verification: show a provisional alert, then confirm or retract it.
- **Live API.** Not worth using for this system. The 1 fps cap would miss brief raises, the 2-minute audio+video sessions need reconnect logic, and all Live models are preview. Event-triggered `generateContent` calls are simpler and cheaper.
- **Developer API key vs Vertex.** The hackathon says "Gemini API" and the free tier is part of the Developer API, so a Developer API key stored in Secret Manager and called from Cloud Run is the simplest path. Vertex/ADC is cleaner for production IAM. The same `google-genai` code works with either.

### Gaps
- Exact free-tier and Tier 1 RPM/RPD per model. Google only shows these inside AI Studio, so they must be checked in the project's AI Studio rate-limit page.
- Official latency numbers for 3.5 Flash-Lite and 3.1 Flash-Lite with an image input. Only third-party snippets were found; none of them used images.
- Whether the Gemini Developer API serves from an Asia region. The Google Cloud page lists `asia-south1` for ML processing on the Cloud product; the Developer API serving location is undocumented in what was read.
- Accuracy of Gemini Flash-Lite at low resolution (280 tokens) on small CCTV person crops. No benchmark was found; this needs testing on Easy FnB's own clips.
- Whether "Gemini Enterprise Agent Platform" is a rename of Vertex AI. Not confirmed.
- The end of the pricing page (characters 100,000–101,809) was not read.

## Q2. On-device small VLMs: can one replace the Gemini call or CLIP on an RTX 3050 4 GB or a CPU-only PC?

### Takeaway
**Gemma 4 E2B/E4B** (Apache-2.0, released about July 2026, image budgets down to 70 tokens) and **SmolVLM-256M/500M** (0.8 and 1.2 GB VRAM) are the realistic on-device options that fit in 4 GB. Qwen3-VL-2B/4B, LFM2.5-VL and Moondream are other candidates. None has a published benchmark on CCTV-style yes/no questions or on a 4 GB laptop GPU. For the hackathon, keep CLIP as the cheap per-frame filter and Gemini as the verifier. An on-device VLM is an offline fallback, not a proven replacement.

### Cited Findings
- **Gemma 4.** Family sizes are E2B, E4B, 26B A4B and 31B (secondary sources). E2B has 2.3B effective parameters (5.1B with embeddings); E4B has 4.5B effective (8B with embeddings). Both take text, image and audio and use a vision encoder of about 150M parameters. Supported visual-token budgets are **70, 140, 280, 560 and 1120**. License: **Apache 2.0**. Vision benchmarks, E2B / E4B: MMMU-Pro 44.2% / 52.6%, MATH-Vision 52.4% / 59.5%. The model card gives no MMBench, no VQA scores and no speed or memory figures. The technical report is arXiv 2607.02770 (July 2026). — [HF model card google/gemma-4-E2B-it](https://huggingface.co/google/gemma-4-E2B-it)
- Secondary sources agree that Gemma 4 moved from the custom Gemma license to Apache 2.0, and give 128K context for E2B/E4B. — [Simon Willison](https://simonwillison.net/b/9404), [doolpa news (Apr 2026)](https://doolpa.com/news/google-gemma-4-release-april-2026). These secondary sources date the release to April 2026, while the model card's technical report is dated July 2026, so the exact release date is unclear.
- **SmolVLM (Hugging Face).** VRAM for single-image inference: 256M ≈ 0.8 GB, 500M ≈ 1.2 GB, 2.2B ≈ 4.9 GB, so the 2.2B model does not fit a 4 GB GPU in BF16. — [SmolVLM paper arXiv 2504.05299](https://arxiv.org/pdf/2504.05299). The 500M card says 1.23 GB GPU RAM for one image. — [HF SmolVLM-500M-Instruct](https://huggingface.co/HuggingFaceTB/SmolVLM-500M-Instruct). SmolVLM2-500M-Video needs 1.8 GB for video inference. — [HF SmolVLM2-500M-Video-Instruct](https://huggingface.co/HuggingFaceTB/SmolVLM2-500M-Video-Instruct)
- In one informal Jetson test (third-party, single author), SmolVLM2 was the fastest of five compact VLMs at about 12.8 s per run, against 37–80 s for the others. Its answers were "often too generic". This comes from a search summary. — [search result: longform.social post](https://longform.social/post/did:plc:25rdn5elo5izoxrmtis34zuk/3mojvrah6yy42)
- **Liquid AI LFM2-VL** is marked deprecated and replaced by LFM2.5-VL-450M and LFM2.5-VL-1.6B. Liquid says it runs "up to 2× faster" than comparable models; this is vendor-reported. — [HF LFM2-VL-1.6B README](https://huggingface.co/LiquidAI/LFM2-VL-1.6B/blob/125f2f31caac7328be8dae2e9204a06d6cf5b51c/README.md), [Liquid blog](https://www.liquid.ai/blog/lfm2-vl-efficient-vision-language-models). LFM2.5-VL-3B reportedly targets sub-250 ms on-device latency on Snapdragon 8 Elite / Jetson Orin; this is unverified. — [themodelwire](https://themodelwire.com/article/hugging-face-releases-3b-vision-language-model-for-edge-deployment-01KZV4KMXW3M6CF5MAX91NDNYJ)
- **Moondream.** Moondream 3 Preview is described as a mixture-of-experts model with 9B total and 2B active parameters, so all weights must stay in memory; the source is low reliability. — [orcarouter comparison](https://www.orcarouter.ai/it/blog/moondream-3-vs-lfm2-5-vl-3b). Moondream2 at Q4_K_M is *estimated* at about 1.3 GB VRAM (4.2 GB BF16). — [llmrun.dev](https://llmrun.dev/model/vikhyatk-moondream2). A Jan 2025 Reddit thread reported that Moondream2 underperformed badly under llama.cpp compared with transformers; it may since have been fixed. — [r/LocalLLaMA thread (mirror)](https://redlib.hbubli.cc/r/LocalLLaMA/comments/1hxjzol/new_moondream_2b_vision_language_model_release)
- **Qwen3-VL** has dense 2B, 4B, 8B and 32B models and mixture-of-experts 30B-A3B and 235B-A22B, released Oct 2025 (technical report arXiv 2511.21631). — [arXiv 2511.21631](https://arxiv.org/abs/2511.21631v1), [aiwiki](https://www.aiwiki.ai/wiki/qwen3_vl). Sources conflict on the license: aiwiki and datalearner say Apache 2.0; codesota says "Qwen License". — [datalearner](https://www.datalearner.com/en/ai-models/pretrained-models/qwen3-vl-4b-instruct), [codesota](https://codesota.com/model/qwen3-vl-4b)

### Inferences
- **Fit on the RTX 3050 4 GB.** YOLO26-pose and CLIP ViT-B/32 already use part of the 4 GB. SmolVLM-256M/500M (0.8–1.2 GB) clearly fit. Gemma 4 E2B at 4-bit (about 5.1B total parameters with embeddings, so very roughly 3 GB or more at Q4) would be tight; this estimate is not measured. On a CPU-only PC, a 2–5B VLM in GGUF will likely take several seconds per image, so it only makes sense for rare events.
- **Best on-device candidate.** Gemma 4 E2B with the 70- or 140-token image budget is the most promising small model to test as an offline verifier. It is Google-family (it matches the hackathon story), Apache-2.0 (no Gemma-terms friction) and multimodal. The same model is also offered free through the Gemini API pricing page.
- **What an on-device VLM won't fix.** It is unlikely to beat CLIP plus a temporal pose model on the hair-touch/drinking confusion from a single crop. That error comes from the missing time dimension, not from model size. VLM value is highest for table state ("used plates vs set table"), where the reasoning is semantic and CLIP prompt-engineering struggles.
- **Fine-tuned crop classifier.** A cheaper option than any VLM: fine-tune CLIP (linear probe) or a small CNN on a few hundred labelled table crops from the target restaurant with the classes "set_for_service / dirty / eating / empty". This likely fixes "set glasses look dirty" more reliably than zero-shot prompts. This is an inference; it was not benchmarked.

### Gaps
- No sources were retrieved this session for **Gemma 3n, PaliGemma 2, Florence-2, InternVL3-1B/2B or MiniCPM-V**: no latency, accuracy or license figures. Background knowledge (not verified here) suggests Florence-2 is MIT-licensed at about 0.23B/0.77B and PaliGemma 2 uses Gemma terms. Verify before citing.
- No published latency for any small VLM on an RTX 3050 4 GB laptop or a typical desktop CPU with llama.cpp, ONNX or OpenVINO. Must be measured locally.
- OpenCompass / Open VLM Leaderboard scores for the small models were not retrieved.
- No benchmark of small VLMs on CCTV-like binary questions ("is this person calling a waiter?").

## Q3. Skeleton/keypoint-based action recognition and datasets for "raise hand / wave to call staff"

### Takeaway
Use a temporal model over YOLO26 keypoint sequences, covering roughly 1–2 s or 15–60 frames, instead of per-frame rules. Two kinds of model fit:
- **GCN models** (ST-GCN++, CTR-GCN in PYSKL, Apache-2.0). With good training practice these reach about 92–94% on NTU60 X-Sub; the gaps between GCN variants shrink to under 2%.
- **A small GRU/TCN.** Cheap, and suited to a 2–3-class problem.

The most usable public data is **BK-SAD**, a Vietnamese classroom dataset with keypoints, 48,457 hand-raising samples and three camera views, downloadable directly. No public dataset of "calling a waiter" was found.

### Cited Findings
- **PYSKL** (Apache-2.0) implements DG-STGCN, ST-GCN, ST-GCN++, PoseConv3D, AAGCN, MS-G3D and CTR-GCN. It ships HRNet 2D skeletons for every supported dataset and a script to extract 2D skeletons from any RGB video. The README says the repo "is currently not maintained by the developer". A notebook (`examples/inference_speed.ipynb`) estimates each model's inference speed; the README itself gives no speed figures. — [PYSKL GitHub](https://github.com/kennymckormick/pyskl)
- The PYSKL paper re-benchmarks ST-GCN, AAGCN, MS-G3D, CTR-GCN and ST-GCN++ under unified good practices and finds the extreme deviation in top-1 accuracy is under 2%. — [PYSKL paper arXiv 2205.09443](https://arxiv.org/pdf/2205.09443)
- NTU60 X-Sub results reported in the DG-STGCN paper (from search summary):
  - 2D poses: PoseC3D 94.1%, ST-GCN++ 93.2%.
  - 3D skeletons: CTR-GCN 92.4%, ST-GCN++ 92.6%.

  — [DG-STGCN arXiv 2210.05895](https://arxiv.org/pdf/2210.05895)
- MMAction2 also hosts skeleton-model docs (ST-GCN, PoseC3D) with model zoo pages. — [MMAction2 skeleton models](https://mmaction2.readthedocs.io/en/0.x/skeleton_models.html)
- **MediaPipe Gesture Recognizer.**
  - Built-in classes: Closed_Fist, Open_Palm, Pointing_Up, Thumb_Down, Thumb_Up, Victory, ILoveYou, plus Unknown.
  - Pipeline: palm detector, then a 21-point hand landmark model, then a gesture embedding and classifier (192×192 or 224×224 input, float16). The hand landmarker was trained on about 30K real images plus synthetic renders.
  - Latency on Pixel 6: 16.76 ms on CPU and 20.87 ms on GPU for the whole pipeline.
  - Custom gestures can be trained with Model Maker (.task bundle). The page does not say how much data is needed.
  - Platforms: Android, Python and Web. `num_hands` defaults to 1, and confidence thresholds default to 0.5.

  — [MediaPipe Gesture Recognizer docs](https://developers.google.com/edge/mediapipe/solutions/vision/gesture_recognizer)
- **BK-SAD (BK-Student Activity Dataset, Vietnam, visedu.vn).** 255,159 frames. Samples: 48,457 hand-raising, 34,762 dozing, 171,940 normal. Each student is cropped as a keypoint-labelled image with a text file of keypoint coordinates. Three cameras (front, left, right) in a real classroom. The page offers a direct ZIP download, states no license or terms, and has an empty citation section. Funded under Vietnam's Ministry of Science and Technology project KC-4.0-06/19-25. — [BK-SAD dataset page](https://visedu.vn/en/bk-sad-dataset)
- **SCB-dataset** (Student Classroom Behavior): 4,003 images and 11,248 labels focused on hand-raising, with YOLOv7 mAP up to 85.3%. It is image/box-based, not video or skeleton. — [SCB-dataset arXiv 2304.02488](https://ar5iv.labs.arxiv.org/html/2304.02488)
- **Bühler et al. (2023)** used pose estimation plus LSTM on 36 real classroom videos (127 students, grades 5–12, 2,442 annotated hand-raising events). They report a mean absolute error of 3.76 hand-raisings per student per lesson. No public download was found. — [ECR Hub summary](https://ecrhub.org/publications/automated-hand-raising-detection-classroom-videos-view-invariant-and-occlusion-robust), [TUM mediaTUM](https://mediatum.ub.tum.de/node?id=1714242)
- A large-scale student behaviour dataset from 30 schools, labelled with frame-by-frame bounding boxes, includes about 70k hand-raising samples (search summary). — [arXiv 2310.02522](https://arxiv.org/pdf/2310.02522v1.pdf)
- Spatio-temporal (video) student-behaviour detection on SCB data has also been published. — [arXiv 2310.16267](https://arxiv.org/pdf/2310.16267)

### Inferences
- **Input features.** Feed YOLO26's 17 COCO keypoints per tracked person (from the ByteTrack ID) over a sliding window of about 1.0–1.5 s (for example 16–32 frames at 15–25 fps). Normalise coordinates by shoulder width and centre them on the mid-shoulder point. Add derived features:
  - wrist height relative to nose, eyes and shoulders;
  - elbow angle;
  - wrist velocity;
  - whether the wrist stays near the head (hair touching) or moves to the mouth (drinking).
- **Model.** A 2-layer GRU or a small temporal-conv network over about 17×3×T inputs runs in well under 1 ms per track on CPU. ST-GCN++ is the stronger, but heavier, option if data allows.
- **Why a temporal model helps with today's errors.**
  - Hair touching shows the wrist circling or staying at the head with the elbow sideways.
  - Drinking shows the wrist going to the mouth and back.
  - Calling shows the wrist rising above the head, or to head height with the palm outward, often with a pause or a wave.

  These differences are visible in motion, not in one frame. A temporal model also catches brief raises (0.3–0.6 s) without a fixed 0.6 s rule. Take "head-height" raises from the trajectory shape, not only from the "wrist above nose" threshold.
- **Data plan.**
  1. Pretrain or initialise on the BK-SAD hand-raising vs normal keypoints. It is Vietnamese, uses multiple viewpoints and suits a seated person; convert its keypoint format to COCO-17 if needed.
  2. Fine-tune on a few hundred self-recorded restaurant clips covering "call", "wave", "touch hair", "drink", "eat" and "phone".
  3. Augment with mirroring, scaling, temporal jitter and keypoint dropout to simulate occlusion by tables.

  Few hundred clips per class is the typical order of magnitude for a small 2–5-class skeleton classifier. This is an inference, not a sourced figure.
- **MediaPipe on CCTV.** MediaPipe Hand/Gesture is designed for close-up hands, and its palm detector works on a 192–224 px input. On CCTV it is only useful as a second-stage check on a high-resolution hand crop taken around the YOLO wrist keypoint ("Open_Palm" suggests calling; a closed grip suggests holding a glass), and only when the hand covers enough pixels. Treat it as optional.

### Gaps
- No public video dataset found for "raising a hand / waving to call a waiter" in restaurants.
- BK-SAD's license and its keypoint format (number of joints) were not stated on the page; the providers should be asked before commercial use.
- Exact PYSKL 2D model-zoo numbers and per-model inference speed (in the repo notebook) were not retrieved.
- No InfoGCN numbers were retrieved.
- MediaPipe Model Maker data requirements for custom gestures were not on the page fetched.

## Q4. Small video-understanding models (X3D, MoViNet, VideoMAE v2-S, TimeSformer, SlowFast-R50) for 1–2 s clips

### Takeaway
MoViNet-A0 is the lightest well-documented RGB video classifier: 71.5% on Kinetics-600 at 2.71 GFLOPs. Its quantised streaming variant reaches about 200 fps on a Pixel 4 CPU. It still needs fine-tuning on gesture clips. On a 4 GB GPU already running YOLO26 and CLIP, a keypoint temporal model is cheaper and probably more robust to restaurant clutter than any RGB video model.

### Cited Findings
- MoViNet-A0: 71.5% top-1 on Kinetics-600 at 2.71 GFLOPs (50 frames, 172 px). Single-clip X3D-XS: 70.2% at 3.88 GFLOPs (3.8M parameters). Thirty-clip X3D-XS reaches 72.3% but costs 23.3 GFLOPs. The paper states that MoViNet-A0 beats X3D-S on both accuracy and GFLOPs. — [MoViNets paper arXiv 2103.11511](https://arxiv.org/pdf/2103.11511)
- Quantised MoViNet-A0, A1 and A2 (streaming, with Squeeze-and-Excitation layers removed) run at about 200, 120 and 60 fps on a Pixel 4 CPU. Removing SE costs 3–4 percentage points on Kinetics-600, and integer quantisation costs another 2–3 points. — [TensorFlow blog: video classification on edge devices (Apr 2022)](https://blog.tensorflow.org/2022/04/video-classification-on-edge-devices.html)

### Inferences
- **Where a video model fits.** It would only be worth it as a mid-stage check on a 1–2 s person-tube crop (from ByteTrack), run on demand. It would capture hand shape and objects (a glass in hand) that keypoints miss.
- **Data cost.** It needs labelled RGB clips, which cost more to collect than keypoints. A keypoint GRU plus Gemini multi-frame verification likely gives most of the benefit at lower cost.
- **Streaming suits brief gestures.** MoViNet-Stream's causal streaming design processes frame by frame with a state buffer, so it can, in principle, respond to brief gestures without a fixed window.

### Gaps
- No sources were retrieved for VideoMAE v2 (small or distilled), TimeSformer variants or SlowFast-R50 latency.
- No measured X3D or MoViNet latency on an RTX 3050 or a desktop CPU.
- No evidence found on how these models handle partial or brief gestures specifically.

## Q5. Cascade patterns (cheap detector → mid model → VLM verifier) for cutting false alarms, with numbers

### Takeaway
Industry practice is: a CV detector and rules generate candidate alerts, then a VLM verifies short clips with a yes/no verdict. NVIDIA VSS is the clearest public reference design. Published numbers are thin:
- an early-exit YOLO → autoencoder → VLM pipeline cut latency 3× compared with calling the VLM on everything;
- NVIDIA's adaptive sampling cut VLM latency about 20% for about 1% accuracy loss;
- vendor false-alarm reduction claims (30–40%) are unverified.

### Cited Findings
- **NVIDIA VSS Alert Verification workflow.**
  - Pipeline: detection and tracking (Grounding DINO in RTVI CV), then behaviour analytics producing candidate alerts, then the VLM reviewing only the alert clips. This keeps GPU requirements lower, "but depends on an upstream entity to generate 'candidate' alerts".
  - Default VLM: Cosmos Reason 3 Nano Reasoner (BF16); FP8 and NVFP4 variants exist.
  - Verdicts are A/B or Yes/No, mapped to confirmed or rejected. Prompts are configured per alert type, and the YES/NO parser can be replaced with a custom one.
  - Adaptive Efficient Video Sampling reduced VLM latency by about 20% with about a 1% accuracy drop (Cosmos 3 Super FP8, RTX PRO 6000, warehouse data).
  - Default verification timeout is 5 s. If alerts are produced faster than the VLM can verify them, backlog and latency can grow sharply.
  - Clips only a couple of seconds long can hurt VLM accuracy; a minimum-duration threshold exists.
  - No false-positive-reduction figure is published.

  — [NVIDIA VSS docs 3.2.1: Alert Verification](https://docs.nvidia.com/vss/3.2.1/agent-workflow-alert-verification.html)
- An early-exit cascade (YOLO detection, then autoencoder reconstruction scoring, then VLM reasoning) reports about a 3× latency reduction compared with direct VLM inference. This is from a search snippet; no false-alarm figure was seen. — [arXiv 2601.06204](https://arxiv.org/html/2601.06204)
- A 2026 federated weakly-supervised video anomaly detection preprint uses multiple-instance-learning (MIL) scoring to route segments to a frozen VLM. It describes the routing as a cost-saving filter that also reduces reliance on "unstable dense zero-shot VLM behavior". — [arXiv 2609.07455](https://arxiv.org/pdf/2609.07455)
- Linkervision product docs describe detector-gated VLM event confirmation to reduce false alarms (no numbers). — [Linkervision Observ docs](https://linkervision.gitbook.io/observ/advanced-feature/vlm-event-based-detection-beta)
- Vendor claims: Milestone says up to 40% fewer false alarms with AI plus contextual verification, and a visionplatform.ai article cites a 2025 survey at 30%. Neither was traced to a primary study. — [visionplatform.ai](https://visionplatform.ai/?p=8665)

### Inferences
- **Suggested Easy FnB cascade.**
  1. YOLO26-pose and ByteTrack on every frame.
  2. A per-track keypoint temporal classifier (GRU or ST-GCN++, under 1 ms) gives a "call" score. Optionally, the CLIP crop classifier adds features.
  3. Fire a candidate only if the score stays high for at least N frames or matches a wave pattern. A per-table cooldown suppresses repeats.
  4. Gemini 3.5 Flash-Lite verifies 3 low-res frames plus a scene crop with a JSON enum verdict, asynchronously, with a timeout of about 3–5 s, following NVIDIA's 5 s default.
  5. Notify staff. Log the verdict and reason to build a hard-negative dataset for retraining stage 2.
- **Caching.** Cache verdicts per track ID so the same raise is not re-verified.
- **Table cleanliness.** Tables change slowly, so verify on a state change rather than per frame, plus a periodic check every few minutes. This keeps API calls in the single digits per table per hour.
- **Fail-open vs fail-closed.** Define behaviour for when Gemini times out or hits a rate limit. For hand-raise, fail open: notify anyway, labelled "unverified". For table-clearing, fail closed or retry later. NVIDIA's backlog warning means a queue with drop and merge rules is needed.

### Gaps
- No peer-reviewed, quantified false-alarm reduction from VLM verification in restaurant or retail CCTV was found.
- No public numbers on Gemini-as-verifier precision/recall for gestures.
