# Compute options for real-time restaurant CV without buying new hardware (Easy FnB)

Researched 2026-11-04. Assumptions used in all cost arithmetic (stated once, reused everywhere):
- **Exchange rate: 26,400 VND/USD.** This is an assumption. The most recent quote I found was BIDV at 26,140–26,367 VND/USD on 13/10. The article did not clearly state the year. [stockbiz.vn](https://stockbiz.vn/tin-tuc/ty-gia-hom-nay-1310-gia-usd-chua-dut-chuoi-giam/35977855). I found no Vietcombank quote for November 2026.
- **Operating hours: 12 h/day × 30 days = 360 h/month.** "24/7" means 730 h/month.
- **Restaurant: 8 cameras** (the top of the 4–8 range), so per-restaurant cost = 8 × the per-camera cost.
- **Gemini call shape:** ~200 text prompt tokens. Output is a short JSON of ~60 tokens, or ~150 tokens when one call covers several cameras. Thinking is assumed minimal or off; output prices include thinking tokens, so leaving thinking on would raise cost.

---

## Option A — Existing restaurant PC (CPU-only or Intel/AMD iGPU): fps and camera capacity

### Takeaway
With OpenVINO, an ordinary 8th–12th-gen Intel PC can run a nano/tiny YOLO-class detector at 320 px for an 8-camera restaurant at 3–5 fps. The published iGPU latencies are ~6–35 ms per inference, which works out to roughly 28–160 detections/s in total. Top-down pose on *every* person in every frame does **not** fit on such a PC. Pose (or Gemini) has to run only on candidate people or events. RF-DETR-Nano is Apache-2.0 but 4–5× slower than YOLO-tiny on Intel iGPUs. YOLO26 is AGPL-3.0.

### Cited Findings
**Detector latency on Intel/AMD integrated graphics, from Frigate NVR's hardware table (ms per inference, OpenVINO / ROCm)** — [Frigate hardware docs](https://docs.frigate.video/frigate/hardware)
- Intel HD 620 (typical of 7th/8th-gen laptop i5, e.g. i5-8250U): MobileNetV2 15–25 ms; YOLO-NAS-320 ~35 ms.
- Intel HD 630 (typical of 7th–9th-gen desktop i3/i5): MobileNetV2 ~15 ms; YOLO-NAS-320 ~30 ms.
- Intel UHD 730 (12th-gen desktop i3/i5): YOLOv9-t-320 14 ms; YOLOv9-s-320 24 ms; YOLOv9-t-640 34 ms; YOLOv9-s-640 65 ms; YOLO-NAS-320 ~19 ms.
- Intel UHD 770: YOLOv9-t-320 ~16 ms; YOLOv9-s-320 ~20 ms; YOLOv9-s-640 ~40 ms.
- Intel Iris Xe (11th/12th-gen laptop): YOLOv9-t-320 6 ms; YOLOv9-s-320 8 ms; YOLOv9-s-640 16 ms; **RF-DETR-Nano-320 33 ms**.
- Intel N100: YOLOv9-s-320 30 ms (one detector instance only).
- Intel NPU: YOLOv9-s-320 11 ms; RF-DETR-Nano-320 40 ms.
- AMD Radeon 780M iGPU (Ryzen 7040/8040 APUs): YOLOv9-t-320 ~14 ms; YOLOv9-s-320 20 ms; YOLO-NAS-320 ~25 ms.
- AMD 9060XT (discrete): RF-DETR-Nano-320 ~90 ms, versus YOLOv9-t-320 ~4 ms. RF-DETR performs poorly on AMD ROCm.
- Frigate's capacity rule of thumb is max detections/s = 1000 / inference ms. Its example: "inference speed of 10 … top out at 1000/10=100" fps. — [Frigate hardware docs](https://docs.frigate.video/frigate/hardware)
- Frigate says the CPU detector is "not recommended for actual use", OpenVINO in CPU mode is often more efficient, and YOLO-NAS runs poorly on integrated GPUs via ONNX. For OpenVINO it recommends YOLOv9 (or a custom ONNX model). — [Frigate object detectors](https://docs.frigate.video/configuration/object_detectors/)
- Frigate says a mini PC like the Beelink EQ13 (N100/N150 class) handles "several 1080p cameras with low-medium activity". — [Frigate hardware docs](https://docs.frigate.video/frigate/hardware)

**Ultralytics YOLO26 (released Jan 2026) numbers** — [Ultralytics YOLO26](https://docs.ultralytics.com/models/yolo26/)
- At 640 px: YOLO26n has 40.9 mAP, 38.9 ms CPU ONNX, 1.7 ms T4 TensorRT10, 2.4 M params and 5.5 GFLOPs. YOLO26s has 48.6 mAP, 87.2 ms CPU ONNX, 2.5 ms T4, 9.5 M params and 20.9 GFLOPs. The CPU used for the table is not named. Elsewhere the page cites an Intel Xeon @ 2.00 GHz, where YOLO26n is "up to 43% faster" on CPU ONNX than YOLO11n.
- License: AGPL-3.0 or paid Enterprise license.

**Ultralytics OpenVINO benchmarks on recent Intel laptop chips (OpenVINO 2026.2.1), ms per image** — [Ultralytics OpenVINO integration](https://docs.ultralytics.com/integrations/openvino/)
- Core Ultra 7 155H (Meteor Lake, 2023–24 laptop): YOLO26n takes 33.19 ms in PyTorch CPU, 9.13 ms with OpenVINO FP32 and 5.79 ms with OpenVINO INT8. YOLO26s takes 70.92 / 16.37 / 9.27 ms.
- Core Ultra 7 258V (Lunar Lake): YOLO26n with OpenVINO takes 3.33 ms (FP32) / 3.46 ms (INT8).
- Core Ultra X7 358H (Panther Lake): YOLO26n with OpenVINO takes 4.09 ms (FP32) / 4.24 ms (INT8).
- The page does not label which device (CPU, iGPU or NPU) each OpenVINO row ran on. These are 2024–2026 chips, not 8th–12th-gen i3/i5.
- An older Ultralytics doc version measured YOLO11n with OpenVINO FP32 at ~11.49 ms on a desktop Core i9-12900KS CPU (≈87 fps). This comes from a search snippet, date not shown. — [Ultralytics OpenVINO (search snippet)](https://docs.ultralytics.com/integrations/openvino/)

**RF-DETR (Roboflow)** — [RF-DETR GitHub](https://github.com/roboflow/rf-detr)
- Nano: 48.4 AP50:95, 2.3 ms on T4 TensorRT FP16, 30.5 M params, 384×384 input. Small: 53.0 AP, 3.5 ms, 512×512. Medium: 54.7 AP, 4.4 ms. Large: 56.5 AP, 6.8 ms. No CPU latency is published.
- License: Nano/Small/Medium/Large detection, all segmentation sizes and the Keypoint (preview) model are **Apache-2.0**. Atto, Femto, Pico, XL and 2XL are under **PML 1.0**: commercial self-hosting needs Roboflow's Enterprise add-on.
- RF-DETR Keypoint preview (Apache-2.0): 71.8 AP50:95, 9.7 ms on T4, 40.7 M params, 576×576 input. This is a possible single-stage person + pose model, but it is GPU-class in cost.
- The paper is arXiv 2511.09554 (Nov 2025), at ICLR 2026.

**RTMPose / RTMDet (OpenMMLab)** — [MMPose RTMPose project](https://github.com/open-mmlab/mmpose/tree/main/projects/rtmpose)
- Latency per person crop (17 keypoints, 256×192 input), ONNX Runtime on an Intel i7-11700 CPU: RTMPose-t 3.20 ms, RTMPose-s 4.48 ms, RTMPose-m 11.06 ms, RTMPose-l 18.85 ms.
- Full pipeline (RTMDet-nano detector + pose), ORT on i7-11700: 12.4 ms (t), 16.7 ms (s), 26.6 ms (m), 36.3 ms (l).
- Headline claim: RTMPose-m "90+ FPS on an Intel i7-11700 CPU".
- RTMO (one-stage multi-person pose): published latencies are GPU only. RTMO-s 8.9 ms, RTMO-m 12.4 ms, RTMO-l 19.1 ms; RTMO-l reaches 74.8 AP at 141 fps on a V100. ONNX models are available. — [MMPose RTMO project (mirror)](https://cdn05042023.gitlink.org.cn/OpenMMLab/mmpose/src/branch/main/projects/rtmo)
- rtmlib runs RTMO / RTMPose on CPU using only numpy, opencv and onnxruntime, with RTMO at 640×640 input. — [rtmlib GitHub](https://github.com/mprib/rtmlib)

**MediaPipe Pose Landmarker** — [MediaPipe Pose Landmarker docs](https://developers.google.com/edge/mediapipe/solutions/vision/pose_landmarker)
- Runs on Android, Python and Web (JS). `num_poses` defaults to 1. The detector input is 224×224 and the landmarker input is 256×256. There are Lite/Full/Heavy float16 bundles and 33 landmarks. No latency benchmarks are on the page.
- A user reported 27.14 fps average with the Python GPU delegate on a webcam. — [mediapipe issue #6041](https://github.com/google-ai-edge/mediapipe/issues/6041)

### Inferences
- **Detection capacity at 3–5 fps per camera**, using Frigate's 1000/ms rule (detection only; RTSP decode and tracking also cost CPU):
  - HD 620 laptop, YOLO-NAS-320 ~35 ms → ~28 det/s → **~7 cams @ 4 fps** (5 cams @ 5 fps).
  - HD 630 desktop, ~30 ms → ~33 det/s → **~8 cams @ 4 fps**.
  - UHD 730 (12th-gen i3/i5 desktop), YOLOv9-t-320 14 ms → ~71 det/s → **~17 cams @ 4 fps**.
  - Iris Xe laptop, YOLOv9-s-320 8 ms → 125 det/s → **~31 cams @ 4 fps**. RF-DETR-Nano-320 at 33 ms → ~30 det/s → **~7 cams @ 4 fps**.
  - AMD 780M, YOLOv9-t-320 ~14 ms → ~71 det/s → **~17 cams @ 4 fps**.
  - CPU-only on an older i5 with no OpenVINO iGPU: YOLO26n at 640 px CPU ONNX ≈ 38.9 ms (unnamed CPU) → ~25 det/s → ~6 cams @ 4 fps. A 320 px input has ~¼ the FLOPs, so a few-times speedup is plausible, but I found no measurement.
- **Pose on every person does not fit.** Example: 8 cams × 4 fps × 10 people × RTMPose-t 3.2 ms = 1.02 s of compute per second. That saturates even a desktop i7-11700, and an 8th-gen laptop i5 is slower. Pose has to be gated to a few candidate tracks (e.g., people seated at tables showing upper-body motion). Alternatively, skip pose locally and let Gemini judge the crop.
- **Model and license choice for the CPU/iGPU tier:**
  - YOLO26n/YOLO11n is fastest and well supported by OpenVINO, but AGPL-3.0. A closed-source SaaS would need the Ultralytics Enterprise license or would have to open-source the code.
  - RF-DETR-Nano is Apache-2.0 but ~4–5× slower on Intel iGPU (33 ms vs 6–8 ms).
  - RTMDet/RTMPose are part of MMPose (Apache-2.0 per the repo; the license was not visible in the fetched snippet, so verify).
  - MobileNetV2-SSD (Frigate's CPU default) is lighter but much less accurate.
- MediaPipe Pose (256×256 crop, default 1 pose) suits close-range single subjects. It will likely struggle with many small people in a wide CCTV frame unless it is fed detector crops. This is inferred from the input sizes; there is no published CCTV benchmark.
- **Cost of Option A ≈ 0 USD in hardware.** Extra electricity: assume ~40 W extra × 360 h = 14.4 kWh/month. At an assumed ~2,500–3,000 VND/kWh business tariff (not verified), that is ≈ 36,000–43,000 VND/month (≈ $1.4–1.6) per restaurant, or ≈ $0.2/camera/month at 8 cams.

### Gaps
- No published benchmark of YOLO26n/YOLO11n/RF-DETR-Nano on a specific 8th–10th-gen Core i3/i5 *CPU* (not iGPU) with OpenVINO INT8 at 320 px. The team should measure with `benchmark_app` or the Ultralytics `benchmark()` on their own laptops.
- No CPU benchmark for RTMO, and no MoveNet MultiPose CPU number in current sources.
- No measured fps for running 8 RTSP decodes plus detection concurrently on an office PC that also runs a POS app.

---

## Option B — Cloud GPU (Cloud Run L4 vs Compute Engine L4/T4 spot): availability, pricing, suitability, cost per camera

### Takeaway
Cloud Run offers NVIDIA L4 in **asia-southeast1 (Singapore)**. GPU billing is instance-based and pay-per-second, and the service can scale to zero with ~5 s GPU startup. The default quota is 3 L4 per region. Continuous video keeps the instance alive, though. The GPU alone costs ~$0.67/h, or ≈ $242/month at 12 h/day. That is **≈ $30/camera/month if one restaurant has its own instance**, and only ~$3/camera/month if ~10 restaurants share one GPU. A single L4 is massively over-provisioned for 8 cameras at 4 fps. Cloud GPU only makes sense multi-tenant, or as a demo.

### Cited Findings
- **GPU types and regions on Cloud Run.** L4 (24 GB) and RTX PRO 6000 Blackwell (96 GB), one GPU per instance.
  - L4 regions: asia-southeast1 (Singapore), asia-south1 (Mumbai, invitation only), europe-west1, europe-west4, us-central1 and us-east4.
  - RTX PRO 6000 regions: asia-southeast1, asia-south2, europe-west4 and us-central1.
  - — [Cloud Run GPU docs](https://docs.cloud.google.com/run/docs/configuring/services/gpu)
- **Minimum instance size for L4:** 4 vCPU and 16 GiB (8 vCPU / 32 GiB recommended). — [Cloud Run GPU docs](https://docs.cloud.google.com/run/docs/configuring/services/gpu)
- **Startup:** GPU instances with pre-installed drivers start in about 5 seconds. — [Cloud Run GPU docs](https://docs.cloud.google.com/run/docs/configuring/services/gpu)
- **Billing and scaling.** Instance-based billing is required for GPUs, and the GPU is billed for the entire instance lifecycle. Services can scale to zero. Minimum instances are charged at the full rate even when idle. — [Cloud Run GPU docs](https://docs.cloud.google.com/run/docs/configuring/services/gpu)
- **Quota.** The default is 3 L4 GPUs per region on first deployment, with zonal redundancy off. Max instances cannot exceed the quota, and more needs a quota request. — [Cloud Run GPU docs](https://docs.cloud.google.com/run/docs/configuring/services/gpu)
- **Zonal redundancy** is on by default and costs more per GPU-second. Turning it off is cheaper and best-effort, and its quota is granted faster. — [Cloud Run GPU docs](https://docs.cloud.google.com/run/docs/configuring/services/gpu)
- **Cloud Run L4 price:** $0.0001867 per GPU-second without zonal redundancy and $0.0002909 per GPU-second with it. This comes from a search snippet of the Cloud Run pricing table and the region/tier is not confirmed. One snippet tied the figure to us-west8, and a third-party mirror lists $0.000233/GPU-s for "Tier 1" and places asia-southeast1 in Tier 1. **The Singapore rate needs confirmation in the Cloud console or calculator.** — [Cloud Run pricing (snippet)](https://cloud.google.com/functions/pricing-1stgen?authuser=0000&hl=he); [Cloud Run pricing](https://cloud.google.com/run/pricing)
- **GPU jobs and worker pools.** Cloud Run GPU **jobs** support only non-zonal-redundancy pricing. **Worker pools**, Cloud Run's resource for continuous non-HTTP pull workloads, also support GPUs. — [Cloud Run jobs GPU](https://docs.cloud.google.com/run/docs/configuring/jobs/gpu); [Cloud Run worker pools GPU](https://docs.cloud.google.com/run/docs/configuring/workerpools/gpu)
- **Compute Engine g2-standard-4** (1× L4, 4 vCPU, 16 GB) in asia-southeast1: **$0.872/h on-demand ($636.57/month)**, **$0.5233/h spot**. 1-yr CUD $401.04/month; 3-yr CUD $286.46/month. The cheapest spot is asia-northeast3 (Seoul) at $0.2915/h; us-east4 on-demand is $0.7045/h. Data updated 2026-11-01 (third-party aggregator, accuracy not guaranteed). — [gcloud-compute.com g2-standard-4](https://gcloud-compute.com/g2-standard-4.html)
- **Throughput.** YOLO26n runs 1.7 ms and YOLO26s 2.5 ms on a T4 with TensorRT10. RF-DETR-Nano runs 2.3 ms on a T4 (TensorRT FP16). — [Ultralytics YOLO26](https://docs.ultralytics.com/models/yolo26/); [RF-DETR](https://github.com/roboflow/rf-detr)

### Inferences
- **Cloud Run L4 GPU-only arithmetic** (CPU and memory are extra, see Gaps):
  - $0.0001867 × 3600 = **$0.672/h**.
  - 12 h/day: $0.672 × 360 = **$241.96/month** (≈ 6.39 M VND). 24/7: $0.672 × 730 = $490.6/month.
  - With zonal redundancy: $0.0002909 × 3600 = $1.047/h, i.e. $377.0/month at 12 h/day.
- **Per camera on Cloud Run:**
  - Dedicated instance, 8 cams: $241.96 / 8 = **$30.25/cam/month (≈ 798,600 VND)** plus CPU/memory.
  - Shared by 10 restaurants (80 cams): **$3.02/cam/month (≈ 79,800 VND)**.
- **Compute Engine comparison** (price includes vCPU and RAM):
  - Spot, 12 h/day: $0.5233 × 360 = $188.39/month → $23.55/cam (8 cams) or **$2.35/cam (80 cams)**.
  - On-demand, 12 h/day: $0.872 × 360 = $313.92 → $39.24/cam (8 cams).
  - 24/7 on-demand: $636.57 / 80 = $7.96/cam.
  - Spot VMs can be preempted, so a fallback is needed.
- **Capacity:** 8 cams × 4 fps = 32 inferences/s. At ~2 ms/inference that uses ~6% of one T4/L4-class GPU. One L4 could cover on the order of hundreds of cameras' detection compute. The real limits would be video decode, network ingress and per-tenant isolation. This is inferred from T4 latencies; L4 is generally at least T4-class.
- **Suitability for continuous streams.** Cloud Run services are request-driven. Restaurant cameras sit behind NAT, so Cloud Run cannot pull RTSP directly, and a local relay must push frames or streams (WebSocket/WebRTC/HTTP batches) to the cloud.
  - A continuously fed GPU instance never scales to zero during opening hours, so the scale-to-zero benefit applies only to closed hours.
  - Worker pools (pull-based) fit a "consume frames from Pub/Sub" design better than HTTP services.
- **Bandwidth (assumption, not sourced).** A 640×360 H.264 substream is often ~0.25–0.5 Mbps, so 8 cams ≈ 2–4 Mbps of continuous uplink per restaurant. That is feasible on Vietnamese fibre but adds a failure mode. Sending JPEG frames at 4 fps instead of H.264 would need several times more bandwidth.

### Gaps
- Official Cloud Run L4 price for **asia-southeast1 specifically** and the instance-based vCPU-second / GiB-second rates. The pricing page is JS-rendered and could not be fetched. If 2025-era Tier-1 instance-based rates still apply (~$0.000018/vCPU-s and ~$0.000002/GiB-s, from memory and unverified), the 4 vCPU / 16 GiB minimum adds ≈ $0.37/h. Verify in the calculator.
- Whether the hackathon credits can be spent on GPUs, and whether a fresh project gets L4 quota in asia-southeast1 without a request.
- T4 (n1 + T4) spot pricing in asia-southeast1 was not retrieved.
- Network RTT Đà Nẵng → Singapore was not measured (typically tens of ms, unverified).

---

## Option C — Gemini directly on frames (Flash-Lite / Flash, media_resolution, batching, Live API)

### Takeaway
Polling every camera continuously is affordable for a demo but expensive at scale. With current **Gemini 3.1 Flash-Lite** ($0.25 per M input / $1.50 per M output) and `media_resolution: low` (280 tokens/image):
- 1 frame per 2 s ≈ **$136/camera/month** (≈ 3.6 M VND), or ≈ $45 for image tokens alone.
- 1 frame per 5 s ≈ **$54/camera/month**.
- A 2×2 mosaic of 4 cameras per call drops this to ≈ $22/camera/month at 1 frame/5 s.

The Live API ingests only **1 fps**, limits audio+video sessions to 2 min without compression, and costs ~$0.002/min of video. That is ≈ $43/camera/month at 12 h/day, so it is not cheaper than polling. Event-triggered calls on crops cost well under $1/camera/month.

### Cited Findings
- **Paid Standard-tier prices per 1M tokens (input text/image/video → output):**
  - Gemini 2.5 Flash-Lite $0.10 → $0.40 (listed **deprecated**).
  - Gemini 2.5 Flash $0.30 → $2.50 (deprecated; from Dec 1, 2026 its requests route to Gemini 3.5 Flash-Lite).
  - **Gemini 3.1 Flash-Lite $0.25 → $1.50**.
  - Gemini 3.5 Flash-Lite $0.30 → $2.50.
  - Gemini 3 Flash Preview $0.50 → $3.00.
  - Gemini 3.6 / 3.8 Flash $0.75 → $3.75 until Dec 31, 2026, then $1.50 → $7.50 from Jan 1, 2027.
  - Output prices include thinking tokens.
  - — [Gemini API pricing](https://aistudio.google.com/docs/pricing)
- **Batch mode** is ~50% cheaper (e.g., 3.1 Flash-Lite $0.125 / $0.75) but is not available on the free tier. — [Gemini API pricing](https://aistudio.google.com/docs/pricing)
- **Free tier:** Standard-tier input and output are free for the listed Flash/Flash-Lite models, with "limited access" and no rate limits stated. **Free-tier content is used to improve Google's products.** — [Gemini API pricing](https://aistudio.google.com/docs/pricing)
- **Image tokens for Gemini 3 / Gemini 4 by `media_resolution`:**
  - low 280; medium 560; high 1120 (also the default when unspecified); ultra_high 2240.
  - Video tokens per frame: 70 at low or medium, 280 at high.
  - Per-part media resolution is supported only on Gemini 3 and 4 models.
  - — [Gemini media resolution docs](https://aistudio.google.com/docs/media-resolution)
- **Live API pricing** (`gemini-3.8-live`, `gemini-3.1-flash-live-preview`, etc.): image/video input $1.00 per M tokens or **$0.002/min**; text input $0.75/M; text output $4.50/M; audio output $12/M or $0.018/min. — [Gemini API pricing](https://aistudio.google.com/docs/pricing)
- **Live API limits:**
  - Video input is **1 fps**, with 768×768 recommended. It is "unsuitable" for fast-changing video.
  - Audio+video sessions last **~2 min without context-window compression** (audio-only ~15 min). Connections last ~10 min, with a GoAway warning ~60 s before.
  - Context window is 128k tokens.
  - 1,000 concurrent sessions per project on the Agent Platform (Vertex) Gemini API. Developer-API concurrency depends on the usage tier.
  - — [Firebase AI Logic Live API limits](https://firebase.google.cn/docs/ai-logic/live-api/limits-and-specs); [Gemini Live session management](https://aistudio.google.com/docs/live-session)
- **Session length.** Context-window compression (sliding window) allows unlimited session length. Session-resumption tokens are valid for 2 h. — [Gemini Live session management](https://aistudio.google.com/docs/live-session)

### Inferences
**Per-frame cost on Gemini 3.1 Flash-Lite, low resolution, one camera per call**
- Input: (280 image + 200 prompt) = 480 tokens × $0.25/M = $0.000120.
- Output: 60 × $1.50/M = $0.000090.
- **Total ≈ $0.00021 per frame (≈ 5.5 VND).**

| Sampling | Frames/h | $/cam/hour | $/cam/day (12 h) | $/cam/month (360 h) | VND/cam/month |
|---|---|---|---|---|---|
| 1 frame / 2 s | 1,800 | 1,800 × 0.00021 = $0.378 | $4.54 | 648,000 × 0.00021 = **$136.08** | ≈ 3.59 M |
| 1 frame / 5 s | 720 | $0.151 | $1.81 | 259,200 × 0.00021 = **$54.43** | ≈ 1.44 M |
| Image tokens only, 1 f/2 s (floor) | 1,800 | 280 × 0.25e-6 = $0.00007/frame → $0.126 | $1.51 | **$45.36** | ≈ 1.20 M |
| Image tokens only, 1 f/5 s (floor) | 720 | $0.050 | $0.60 | **$18.14** | ≈ 0.48 M |

At 8 cams and 1 f/5 s that is ≈ $435/restaurant/month (≈ 11.5 M VND), more than an L4 VM.

**Batching several cameras per call (1 f/5 s, 3.1 Flash-Lite)**
- **4 separate low-res images in one request:**
  - Input (4 × 280 + 200) = 1,320 tokens × 0.25e-6 = $0.00033.
  - Output 150 × 1.5e-6 = $0.000225.
  - Total $0.000555 / 4 = **$0.000139 per camera-frame** → $36.0/cam/month (≈ 950k VND).
- **2×2 mosaic in one 280-token image:**
  - (280 + 200) × 0.25e-6 + 150 × 1.5e-6 = $0.000345 per 4 cams = **$0.000086 per camera-frame** → **$22.4/cam/month (≈ 590k VND)** at 1 f/5 s, or $55.9 at 1 f/2 s.
  - Each camera then gets only ~¼ of the already low effective resolution.

**Other model choices**
- **Gemini 3.5 Flash-Lite** ($0.30/$2.50): 480 × 0.30e-6 + 60 × 2.5e-6 = $0.000294/frame → $76/cam/month at 1 f/5 s.
- **Deprecated 2.5 Flash-Lite** ($0.10/$0.40) would be ~3× cheaper. It should not be a production dependency given the deprecation notice.

**Live API cost**
- $0.002/min × 60 = $0.12/h per camera stream → × 360 h = **$43.2/cam/month (≈ 1.14 M VND)** for video input alone, plus output tokens.
- It needs one session per camera, with reconnects every ~10 min and compression on.
- At 1 fps it reacts faster than 1 f/5 s polling, but it is designed for conversational agents, not 8-way passive monitoring.
- The $0.002/min rate implies ~2,000 tokens/min ≈ 33 tokens/frame at 1 fps. That does not match the 70 tokens/frame for standard video. I could not reconcile the Live per-frame token count, so treat $0.002/min as the published figure.

**Accuracy (inference, not tested)**
- A 280-token "low" image of a wide CCTV view probably makes a raised hand on a distant person tiny. A 4-camera mosaic is worse.
- Accuracy will be much better if a local detector crops the person or table region and Gemini sees that crop at medium (560 tokens) or high.

**Privacy and compliance**
- The free tier uses content to improve Google's products, so do not send real customer CCTV on the free tier. That matters under Vietnam's personal-data rules; legal specifics were not researched here.

### Gaps
- **No published evaluation** of Gemini judging raised hands, table state (occupied / dirty / waiting) or "stretch vs raised hand" from single wide CCTV frames. The team must build a small labelled test set (e.g., 100 frames) and measure.
- Pixel dimensions corresponding to "low = 280 tokens" are not stated. Gemini 2.5-era rules (258 tokens per image ≤384 px, 768×768 tiles beyond) are from older docs not re-verified here, and 2.5 is deprecated.
- **No measured Gemini 3.1 Flash-Lite latency** (time to first token or full response) for an image request from Vietnam. Expect roughly 1–3 s (unverified); measure it.
- Free-tier rate limits (RPM/RPD) for 3.1 Flash-Lite were not shown on the pricing page.

---

## Option D — On-device in a browser tab (MediaPipe WebGPU/WASM) or an old Android phone

### Takeaway
Technically possible for 1–2 cameras, but a poor fit for 4–8 CCTV streams:
- Browsers cannot open RTSP, so a local relay is still needed.
- MediaPipe Pose is built for 1 close-range person per crop.
- No current browser or WebGPU fps benchmarks exist for the Tasks API.

An old flagship phone (Snapdragon 865 class) can run RTMPose-s at ~72 fps per crop, so a spare phone could serve 1–2 cameras as a native app. Treat it as a demo or fallback, not the main path.

### Cited Findings
- MediaPipe Pose Landmarker runs on **Web (JavaScript)**, Android and Python. It has IMAGE/VIDEO/LIVE_STREAM modes, a 224×224 detector, a 256×256 landmarker and `num_poses` default 1. — [MediaPipe Pose Landmarker](https://developers.google.com/edge/mediapipe/solutions/vision/pose_landmarker)
- The only browser benchmark found is from **2021** (TF.js BlazePose, MediaPipe runtime with WASM + GPU on a 2019 MacBook Pro). It uses an older API, not the current Tasks API or WebGPU. — [TensorFlow blog, May 2021](https://blog.tensorflow.org/2021/05/high-fidelity-pose-tracking-with-mediapipe-blazepose-and-tfjs.html)
- Native Python Pose Landmarker with the GPU delegate on a webcam: ~27 fps (user report). — [mediapipe issue #6041](https://github.com/google-ai-edge/mediapipe/issues/6041)
- On a Snapdragon 865 (2020 flagship SoC) with ncnn FP16: RTMPose-t 9.02 ms and RTMPose-s 13.89 ms per crop ("70+ FPS"). — [MMPose RTMPose](https://github.com/open-mmlab/mmpose/tree/main/projects/rtmpose)

### Inferences
- **Browser path:** NVR → local relay (e.g., go2rtc/MediaMTX converting RTSP to WebRTC) → browser tab → MediaPipe Object Detector/Pose via WASM/WebGPU → events to Cloud Run.
  - The relay is software on the same PC, so this is "no new hardware" but not "no install".
  - A background browser tab may be throttled by the OS or browser, which makes it unreliable for 24/7 monitoring.
  - Inferred; no source found on throttling for this use case.
- **Phone path:** a native Android app (ONNX Runtime Mobile / ncnn / LiteRT) pulls 1–2 RTSP substreams and runs a nano detector plus gated pose.
  - Thermals, battery-swelling risk from 24/7 charging, and Wi-Fi reliability are the practical problems (inferred).
- **Hackathon demo:** a browser MediaPipe demo on a webcam (one person raising a hand) is visually compelling and cheap to build. It just doesn't scale to real CCTV.

### Gaps
- No current (2025–2026) benchmark of MediaPipe Tasks Object Detector or Pose Landmarker fps in Chrome WebGPU on an Intel iGPU laptop.
- No data on running multiple video streams in one browser tab.

---

## Hybrid recommendations: when to call Gemini, event triggering, and detection latency

### Takeaway
The best no-new-hardware architecture is a **cascade**:
1. Cheap local motion gating plus a nano detector and ByteTrack on the existing PC's iGPU/CPU at 2–4 fps.
2. Rules over the tracks (e.g., person at a table, upper-body motion, arm above shoulder for ≥1 s; table vacated) raise *candidate* events.
3. Only candidates are cropped and sent to Gemini 3.1 Flash-Lite for verification.

At realistic trigger rates Gemini costs **< $1–5 per camera per month**. End-to-end notice latency should be about 2–5 s.

### Cited Findings
- Frigate itself uses motion detection to decide when to run object detection, and recommends tuning motion masks when detection fps nears the detector's ceiling. — [Frigate hardware docs](https://docs.frigate.video/frigate/hardware)
- Nano detectors on common Intel iGPUs take 6–35 ms at 320 px. — [Frigate hardware docs](https://docs.frigate.video/frigate/hardware)
- Gemini 3.1 Flash-Lite costs $0.25/M input and $1.50/M output. Medium image resolution is 560 tokens. — [Gemini API pricing](https://aistudio.google.com/docs/pricing); [media resolution](https://aistudio.google.com/docs/media-resolution)
- The Live API's 1 fps / 2-min session limits make it a poor always-on monitor. — [Firebase Live API limits](https://firebase.google.cn/docs/ai-logic/live-api/limits-and-specs)

### Inferences
**Event-triggered Gemini cost**
- One crop at medium resolution: (560 + 200) × 0.25e-6 = $0.00019 input + 80 × 1.5e-6 = $0.00012 output = **$0.00031 per verification (≈ 8.2 VND)**.
- 50 triggers/camera/day → 1,500/month → **$0.47/cam/month (≈ 12,300 VND)**; ×8 cams = $3.72/restaurant.
- 500 triggers/camera/day (a very noisy trigger) → $4.65/cam/month (≈ 123k VND).
- Optional periodic table-state snapshot, 1 mosaic per 30 s per 4 cams, 12 h: 1,440 calls/day × 0.000345 = $0.50/day per 4 cams → $3.73/cam/month.

**Latency budget for a raised hand**
| Step | Time |
|---|---|
| Frame sampling at 4 fps | ≤ 0.25 s |
| Detector + tracker | ≤ 0.05 s |
| Persistence rule (hand up ≥ 1 s) | 1 s |
| Upload crop to Cloud Run + Gemini call (unverified, measure) | ~1–3 s |
| Push to staff app (FCM/WebSocket) | < 0.5 s |
| **Total** | **≈ 2.5–5 s** |

Optionally, alert staff immediately on high local confidence and let Gemini only *confirm or cancel* the alert.

**Cost comparison per camera per month** (8-camera restaurant, 12 h/day, 26,400 VND/USD)

| Architecture | USD/cam/month | VND/cam/month | Notes |
|---|---|---|---|
| A. Existing PC, local detection only | ≈ $0.2 (electricity, assumed tariff) | ≈ 5k | Hardware cost 0; capacity depends on iGPU |
| A + Gemini on events (50/cam/day) | ≈ $0.7 | ≈ 18k | **Recommended** |
| A + Gemini on events (500/cam/day) | ≈ $4.9 | ≈ 128k | Noisy-trigger worst case |
| C. Gemini polling, 2×2 mosaic, 1 f/5 s | $22.4 | ≈ 590k | Weak small-object detail |
| C. Gemini polling, 1 cam/call, 1 f/5 s | $54.4 | ≈ 1.44 M | |
| C. Gemini polling, 1 cam/call, 1 f/2 s | $136.1 | ≈ 3.59 M | |
| C. Live API, 1 fps continuous | $43.2 + output | ≈ 1.14 M+ | 2-min A/V session limit without compression |
| B. Cloud Run L4 dedicated per restaurant | $30.25 + CPU/mem | ≈ 799k+ | Only 32 inf/s needed; GPU mostly idle |
| B. Cloud Run L4 shared by 10 restaurants | $3.02 + CPU/mem | ≈ 80k+ | Needs multi-tenant streaming infra, 2–4 Mbps uplink/restaurant |
| B. GCE L4 spot shared by 10 restaurants | $2.35 | ≈ 62k | Preemptible; Singapore spot $0.5233/h |

### Gaps
- Real trigger rates (false candidates per camera per hour) in a Vietnamese restaurant are unknown and must be measured. They dominate the Gemini cost.
- Gemini verification accuracy on crops has not been measured.

---

## Hackathon (GDG DevFest MienTrung, 14/11/2026): simplest buildable architecture in ~10 days

### Takeaway
Build **edge agent on the team's own laptop + CPU-only Cloud Run backend + Gemini 3.1 Flash-Lite verification**. Skip cloud GPUs:
- **Laptop agent (Python):** OpenCV reads an RTSP substream, recorded restaurant video or a webcam. YOLO26n or RF-DETR-Nano runs via OpenVINO/ONNX Runtime at 320–384 px, 3–4 fps, with ByteTrack (e.g., via `supervision`). It applies simple rules and posts candidate crops.
- **Cloud Run CPU service (FastAPI):** calls Gemini with structured JSON output, stores events in Firestore, and serves a dashboard plus staff notifications. This meets "Gemini API + Cloud Run" without GPU quota risk.

### Cited Findings
- Cloud Run L4 default quota is 3 GPUs/region and needs ≥ 4 vCPU / 16 GiB. GPU is billed for the whole instance lifetime. — [Cloud Run GPU docs](https://docs.cloud.google.com/run/docs/configuring/services/gpu)
- YOLO26n via OpenVINO runs 3.3–9.1 ms on recent Intel laptops (FP32), and 5.8 ms INT8 on a Core Ultra 7 155H. Iris Xe laptops run YOLOv9-t-320 in 6 ms. — [Ultralytics OpenVINO](https://docs.ultralytics.com/integrations/openvino/); [Frigate hardware](https://docs.frigate.video/frigate/hardware)
- YOLO26 is AGPL-3.0; RF-DETR Nano/Small/Medium/Large are Apache-2.0. — [Ultralytics YOLO26](https://docs.ultralytics.com/models/yolo26/); [RF-DETR](https://github.com/roboflow/rf-detr)
- Gemini 3.1 Flash-Lite is $0.25/$1.50 per M tokens, and the free tier covers Flash-Lite Standard-tier usage, though content is used for product improvement. — [Gemini API pricing](https://aistudio.google.com/docs/pricing)
- Per-part `media_resolution` (low 280 / medium 560 / high 1120 tokens) is available on Gemini 3 models. — [media resolution](https://aistudio.google.com/docs/media-resolution)

### Inferences
**Hackathon budget**
- 3 days of testing × 8 h × 4 cams × 1 trigger/min = 5,760 calls × $0.00031 = **≈ $1.8**.
- Even polling 4 cams at 1 f/5 s for 8 h × 3 days: 4 × 720 × 24 = 69,120 frames × $0.00021 = $14.5.
- Either fits easily in hackathon credits. Use paid tier or credits for any real-restaurant footage.

**Suggested 10-day split for 2–3 people**
| Days | Work |
|---|---|
| 1–2 | Laptop agent: detector + tracker on recorded video, with a fps counter to measure the team's own laptops |
| 3–4 | Rule engine: table zones as polygons, hand-raise heuristic from RTMPose-t/MediaPipe on gated crops or from Gemini only, "table vacated" timer |
| 5–6 | Cloud Run FastAPI + Gemini prompt with JSON schema, evaluated against ~100 labelled crops |
| 7–8 | Dashboard and staff notification (FCM / web push) on Cloud Run |
| 9–10 | End-to-end latency measurement, cost slide (use the tables above), demo video |

**Pitch line:** "Zero new hardware. Runs on the cashier PC's iGPU, with Gemini called only on uncertain events. ≈ 18k VND/camera/month in AI cost versus ≈ 1.4–3.6 M VND/camera/month for naive frame polling."

**License choice for the demo:** prefer RF-DETR-Nano (Apache-2.0) if its CPU/iGPU speed is acceptable on the team's laptops. Frigate shows RF-DETR-Nano-320 at 33 ms on Iris Xe, i.e. ~7 cams @ 4 fps. Otherwise use YOLO26n under AGPL for the hackathon and note the Enterprise license as a commercialization cost.

### Gaps
- Whether the organizers' credits cover the Gemini API (AI Studio billing) versus Vertex/Agent Platform Gemini, and whether they allow GPU SKUs.
- No first-hand measurement on the team's actual laptops. Run benchmarks on day 1.
