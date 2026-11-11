# Real-time Computer-Vision Edge Stack for Easy FnB (multi-camera restaurant, on-prem, face clustering) — as of Nov 2026

Research date: 2026-11-03. Claims marked **[prior knowledge, not re-verified]** come from the researcher's background knowledge (cutoff mid-2026) and were not confirmed by a source fetched in this session. Treat them as leads and check them before relying on them.

---

## 1. Detection: YOLO11 / YOLO12 / YOLO26 / RT-DETR / RF-DETR / D-FINE / DEIMv2 / open-vocabulary, and the AGPL problem

### Takeaway
YOLO26 (Ultralytics, Jan 2026) is the fastest and simplest option, but it is **AGPL-3.0**: shipping closed-source software on an edge box needs an Ultralytics Enterprise licence. **RF-DETR Nano/Small/Medium/Large (Apache-2.0)** match or beat it on accuracy at similar T4 latency and are the safest commercial default. Fine-tune RF-DETR-S/M on restaurant tableware. Use open-vocabulary models (YOLOE, Grounding DINO) only for auto-labelling, not in the live loop.

### Cited Findings
- **YOLO26** was "released January 2026". The model is natively NMS-free (an optional one-to-one head runs with `nms=False`). DFL is removed; it adds ProgLoss, STAL small-target label assignment and the MuSGD optimizer. Tasks: detect, instance and semantic segmentation, pose, OBB, classification and depth. **YOLOE-26** is a separate open-vocabulary variant (text, visual or prompt-free). Licence: "AGPL-3.0 and an Enterprise license". — [Ultralytics YOLO26 docs](https://docs.ultralytics.com/models/yolo26/)
- YOLO26 COCO results at 640 px (mAP50-95 / CPU ONNX ms / T4 TensorRT10 ms / params) — [Ultralytics YOLO26 docs](https://docs.ultralytics.com/models/yolo26/):
  - n: 40.9 / 38.9 / 1.7 / 2.4M
  - s: 48.6 / 87.2 / 2.5 / 9.5M
  - m: 53.1 / 220 / 4.7 / 20.4M
  - l: 55.0 / 286 / 6.2 / 24.8M
  - x: 57.5 / 526 / 11.8 / 55.7M
  - Also claims up to 43% faster CPU ONNX for YOLO26n vs YOLO11n, and pose "+7.2 AP over YOLO11".
- Release date conflict: one academic analysis says YOLO26 was announced in Sept 2025; the Ultralytics comparison page lists 2026-01-14. An independent arXiv analysis paper (2601.12882) reviewed only Ultralytics' published material and ran no tests of its own. — [arXiv 2601.12882](https://arxiv.org/pdf/2601.12882); [arXiv 2509.25164](https://arxiv.org/html/2509.25164v3); [Ultralytics YOLOv5 vs YOLO26](https://docs.ultralytics.com/compare/yolov5-vs-yolo26)
- **RF-DETR** (Roboflow, DINOv2 backbone) on COCO, T4 TensorRT FP16 batch 1 (AP50:95 / latency / params / input / licence) — [roboflow/rf-detr GitHub](https://github.com/roboflow/rf-detr):
  - Nano: 48.4 / 2.3 ms / 30.5M / 384 / **Apache-2.0**
  - Small: 53.0 / 3.5 ms / 32.1M / 512 / **Apache-2.0**
  - Medium: 54.7 / 4.4 ms / 33.7M / 576 / **Apache-2.0**
  - Large: 56.5 / 6.8 ms / 33.9M / 704 / **Apache-2.0**
  - XL: 58.6 / 11.5 ms and 2XL: 60.1 / 17.2 ms — **Platform Model License (PML 1.0)**
  - Atto, Femto and Pico (30.5–41.6 AP, 1.0–1.7 ms, PE-Core-T backbone) — PML 1.0. Under PML, "commercial self-hosting requires the Enterprise add-on".
- RF-DETR-Seg (Nano–2XL, 40.3–49.9 mask AP, 3.4–21.8 ms) is **all Apache-2.0**. **RF-DETR Keypoint (Preview)** scores 71.8 COCO AP at 9.7 ms, 40.7M params, 576 px, Apache-2.0. The repo describes itself as "designed for fine-tuning" and reports RF100-VL results (e.g. Medium 61.2 AP50:95 on RF100-VL). — [roboflow/rf-detr GitHub](https://github.com/roboflow/rf-detr)
- RF-DETR Nano runs at "roughly 100 frames per second on a T4" in Roboflow's edge write-up. — [Roboflow blog: RF-DETR for the edge](https://blog.roboflow.com/rf-detr-for-the-edge/)
- **DEIMv2** (Sept 2025) builds on the DEIM training pipeline with DINOv3 features. Model sizes S–X: S 50.9 AP, X 57.8 AP, plus Pico/Femto/Atto edge variants. Licence is Apache-2.0 per a Gitee mirror; check the LICENSE file in the official repo. — [DEIMv2 arXiv 2509.20787](https://arxiv.org/html/2509.20787v1); [DEIMv2 GitHub](https://github.com/Intellindust-AI-Lab/DEIMv2); [Gitee mirror](https://gitee.com/ctpactwangke/DEIMv2)
- **D-FINE** and **DEIM** are described by Roboflow as Apache-2.0 (code and weights), "suitable for commercial use". DEIM was accepted at CVPR 2025. — [Roboflow D-FINE vs DEIM](https://playground.roboflow.com/models/compare/d-fine-vs-deim); [Roboflow DEIM](https://roboflow.com/model/deim)
- **YOLOE** (THU-MIG, March 2025) is AGPL-3.0, including network-use obligations. **Grounding DINO** is Apache-2.0. **OWL-ViT** is Apache-2.0 (OWLv2's licence was not confirmed in this search). A July 2024 third-party table lists Grounding DINO at about 1.5 FPS with 172M params (hardware not stated), far slower than YOLO-class models. — [Roboflow Grounding DINO vs YOLOE](https://playground.roboflow.com/models/compare/grounding-dino-vs-yoloe); [Roboflow OWL-ViT vs YOLOE](https://playground.roboflow.com/models/compare/owl-vit-vs-yoloe); [mer.vin vision model comparison (2024)](https://mer.vin/2024/07/vision-models-comparison/)
- Frigate 0.16 added ONNX/OpenVINO detector support for **D-FINE and RF-DETR**. Both therefore already run inside an open-source NVR. — [newreleases.io Frigate v0.16.0-beta1](https://newreleases.io/project/github/blakeblackshear/frigate/release/v0.16.0-beta1)

### Inferences
- Ultralytics AGPL-3.0 in practice: a hackathon demo is fine. A commercial edge box running YOLO11/12/26 or YOLOE must either release the whole application as AGPL source (including network-served parts) or buy an Ultralytics Enterprise licence. Choose **RF-DETR (N/S/M/L, Apache-2.0), D-FINE, DEIM/DEIMv2 or RT-DETR** to avoid this.
- Accuracy vs speed at T4 batch 1:
  - RF-DETR-S (53.0 AP, 3.5 ms) beats YOLO26s (48.6, 2.5 ms) and roughly matches YOLO26m (53.1, 4.7 ms).
  - RF-DETR-M (54.7, 4.4 ms) roughly matches YOLO26l (55.0, 6.2 ms).
  - YOLO26n stays the best choice for CPU-only or very low-end NPUs, because DETR-style models are heavier on CPU. Note that RF-DETR's smallest Apache model already has 30.5M params, against 2.4M for YOLO26n.
- COCO has `bowl`, `cup`, `wine glass`, `fork`, `knife`, `spoon`, `bottle` and `dining table`, but **no `plate` and no `hotpot`** **[prior knowledge, not re-verified]**. A small custom dataset (a few hundred labelled frames from the restaurant's own cameras) is needed. A fast route: auto-label with Grounding DINO or YOLOE prompts, correct the labels by hand, then fine-tune RF-DETR-S. Keep the open-vocabulary models offline only, since Grounding DINO runs at about 1.5 FPS.
- YOLO12 (Feb 2025, attention-centric) is generally not recommended over YOLO11/YOLO26 for production, because of reported training instability and memory cost **[prior knowledge, not re-verified]**. RT-DETR/RT-DETRv2 (Baidu) are Apache-2.0 **[prior knowledge, not re-verified]** but have been overtaken by D-FINE, DEIM and RF-DETR.

### Gaps
- No independent, same-hardware benchmark of YOLO26 vs RF-DETR vs DEIMv2 on Jetson Orin or a consumer RTX card was found. All latencies above are vendor T4 numbers.
- The official DEIMv2 LICENSE file and the OWLv2 licence were not directly verified.
- The cost of an Ultralytics Enterprise licence was not found.

---

## 2. Pose estimation for far-field, top-down CCTV with occlusion

### Takeaway
Use a **multi-person, bottom-up/one-stage** model. **RTMO** (via the Apache-2.0 `rtmlib`, which needs no mmcv) is the best documented choice for crowded scenes, and **RF-DETR Keypoint (Apache-2.0, preview)** is a newer alternative. YOLO26-pose is the fastest to wire up but is AGPL. **MediaPipe Pose is the wrong tool**: it targets close-range, single-person fitness use.

### Cited Findings
- **RTMO** (one-stage, YOLO-style): RTMO-l reaches 74.8% AP on COCO val2017 at 141 FPS on a V100. On **CrowdPose**, RTMO-l scores 73.2 AP, RTMO-m 71.1 and RTMO-s 67.3. It is faster than top-down RTMPose once more than about 4 people are in frame (ONNXRuntime), and once 2 or more are in frame with TensorRT FP16. — [RTMO paper arXiv 2312.07526](https://arxiv.org/pdf/2312.07526.pdf); [MMPose RTMO project mirror](https://cdn05042023.gitlink.org.cn/OpenMMLab/mmpose/src/branch/main/projects/rtmo)
- **rtmlib** is Apache-2.0 and works "WITHOUT any dependencies like mmcv, mmpose, mmdet". Backends: onnxruntime, openvino, opencv, plus optional TensorRT; devices cpu, cuda and mps. Models: RTMPose (17/26 body, hand, face), RTMO, RTMW (133 kpt), DWPose, RTMW3D, ViTPose. Detectors: YOLOX, **RF-DETR**, RTMDet. It ships a `PoseTracker(Body, mode='balanced', det_frequency=10)` helper. Checkpoints are mirrored on Hugging Face in case download.openmmlab.com is down. — [rtmlib GitHub](https://github.com/Tau-J/rtmlib)
- **RF-DETR Keypoint (Preview)**: 71.8 COCO keypoint AP, 9.7 ms on T4, Apache-2.0. — [roboflow/rf-detr GitHub](https://github.com/roboflow/rf-detr)
- **YOLO26-pose** checkpoints (n–x) exist; Ultralytics claims "+7.2 AP over YOLO11" on COCO pose. AGPL-3.0. — [Ultralytics YOLO26 docs](https://docs.ultralytics.com/models/yolo26/)
- **MediaPipe Pose Landmarker** provides 33 3D landmarks with Lite/Full/Heavy variants and a BlazePose-variant detector. `num_poses` defaults to **1**, and the bundle is "optimized for on-device, real-time fitness applications". — [Google AI Edge MediaPipe Pose Landmarker](https://developers.google.com/edge/mediapipe/solutions/vision/pose_landmarker)

### Inferences
- Restaurant CCTV is ceiling- or corner-mounted, with people seated and partly hidden by tables. A one-stage model trained on crowds (RTMO-s/m, CrowdPose variant) or RF-DETR Keypoint will handle this better than MediaPipe. Pose speed then stays roughly constant regardless of head count.
- Pose is optional for the MVP. Run it only on demand (e.g. every 2–5 frames, or only in staff tracks or zones of interest) to save GPU time. Useful signals: raised hand (calling for staff), standing vs seated (table turnover), staff bending at a table (serving).
- ViTPose is top-down and more accurate per person, but it costs more as the number of people grows. It is better for offline analytics than for multi-stream real time (inferred from the RTMO paper's discussion of top-down scaling).

### Gaps
- No published benchmark of these pose models on overhead or far-field restaurant CCTV was found.
- RTMO's Jetson/TensorRT FPS numbers were not found. MMPose maintenance status in 2026 was not checked; rtmlib reduces that risk.

---

## 3. Tracking and multi-camera (MOT, Re-ID, floor-plan homography, MTMC frameworks)

### Takeaway
Per camera, use **ByteTrack or OC-SORT from Roboflow's Apache-2.0 `trackers`** (avoid AGPL BoxMOT in a commercial product). Across cameras, build a light in-house association: a **floor-plan homography of foot points, spatio-temporal gating, OSNet Re-ID embeddings (2.2M params), and face ID when a face is available**. NVIDIA's Metropolis MTMC / DeepStream MV3DT exist but are early-access or developer-preview and not turnkey. They are too heavy for 48 hours.

### Cited Findings
- **Roboflow `trackers`** is Apache-2.0, distributed on PyPI as `trackers`, with "clean-room implementations" of SORT, ByteTrack and OC-SORT. PyPI v2.6.1 lists SORT, ByteTrack, OC-SORT, **BoT-SORT, C-BIoU and McByte**. It plugs into `supervision` through `tracker.update(detections)` and includes HOTA/IDF1/MOTA evaluation and a CLI. — [trackers docs](https://trackers.roboflow.com/latest); [PyPI trackers 2.6.1](https://pypi.org/project/trackers/2.6.1/)
- **BoxMOT** is **AGPL-3.0** (network copyleft). It includes DeepOC-SORT, StrongSORT, OC-SORT, ByteTrack, BoT-SORT and BoostTrack, with OSNet Re-ID weights such as `osnet_x0_25_msmt17.pt`. — [ecosyste.ms BoxMOT listing](https://awesome.ecosyste.ms/projects/github.com%2Fmikel-brostrom%2Fboxmot); [depscope BoxMOT](https://depscope.dev/pkg/pypi/boxmot); [fork listing](https://science.ecosyste.ms/projects/43586)
- **OSNet** has only 2.2M params (vs 24M+ for ResNet50 Re-ID) and reached SOTA on six person Re-ID datasets. It is provided by Torchreid; a third-party port reports Torchreid as MIT and warns that the Re-ID training datasets carry research-only terms. — [OSNet paper arXiv 1905.00953](https://arxiv.org/pdf/1905.00953); [LibreReID OSNet (HF)](https://huggingface.co/LibreYOLO/LibreReID-osnet); [Torchreid repo](https://github.com/KaiyangZhou/deep-person-reid)
- **NVIDIA Multi-Camera Tracking workflow** (Metropolis): DeepStream perception with feature embeddings, a behaviour/tracking microservice using embeddings plus spatio-temporal info, and global ID generation. It is a reference app with an early-access application form. Re-ID models: ReIdentificationNet and ReIdentificationNet_Transformer; detector PeopleNet v2.6, retrainable via TAO. Reported MTMC v1.0 KPI: HOTA ≈ 48.0%, IDF1 ≈ 78.6%. A forum user adapting it to custom classes got no global ID matches. — [NVIDIA MTMC workflow](https://www.nvidia.com/en-us/ai-data-science/ai-workflows/multi-camera-tracking/); [MDX MTMC KPI](https://docs.nvidia.com/mms/text/MDX_Multi_Camera_Tracking_KPI.html); [MDX models](https://docs.nvidia.com/mms/text/MDX_Models.html); [NVIDIA forum: MTMC custom objects](https://forums.developer.nvidia.com/t/how-to-use-mtmc-for-custom-objects/286561)
- **DeepStream 9.0** (docs updated Apr 14, 2026) includes **Multi-View 3D Tracking (MV3DT)** as a *developer preview*. The NvDCF tracker can now filter by class ID. — [DeepStream 9.0 release notes](https://archive.docs.nvidia.com/metropolis/deepstream/9.0/text/DS_Release_notes.html)
- Apple's Photos pipeline notes that upper-body crops "usually show constant characteristics—like clothing—within a specific context". It uses upper-body embeddings only within a time- and location-bounded "moment". — [Apple ML Research: Recognizing People in Photos](https://machinelearning.apple.com/research/recognizing-people-photos)

### Inferences
- Floor-map localisation recipe:
  1. For each camera, click at least 4 points that match floor-plan coordinates (table corners, floor tiles) and compute `cv2.findHomography`.
  2. Project each track's **bottom-centre of the bbox** (the foot point) to plan coordinates.
  3. Smooth with the tracker's Kalman state.
  4. Merge tracks across cameras when overlap zones agree in plan space (distance < ~0.5–1 m) and timing is plausible.
  5. Use OSNet cosine similarity, or face ID, to break ties.

  Camera calibration is a 5-minute admin task per camera **[standard OpenCV practice; prior knowledge]**.
- Apple's "constant clothing within a context" point supports an **appearance embedding being reliable within one shift or one day**. That fits staff tracking well because uniforms are constant. It is weaker for customers across days, where face is needed.
- OSNet weights trained on Market-1501, MSMT17 or DukeMTMC carry research-only dataset terms. Commercially, fine-tune on your own consented staff data or use a commercially licensed model, and flag this risk.
- Skip the NVIDIA MTMC microservices (Kafka, Elasticsearch, Kubernetes-heavy, early access) for the hackathon. The team's own Kafka experience is enough to publish per-camera tracklets to a topic and run a Python "global ID" service.

### Gaps
- No HOTA/IDF1 numbers for ByteTrack vs OC-SORT vs BoT-SORT on MOT17/MOT20/DanceTrack were retrieved this session.
- CLIP-ReID and SOLIDER licences and speed were not researched. Open-source turnkey MTMC frameworks other than NVIDIA's were not found.

---

## 4. Video pipeline frameworks (DeepStream, MediaPipe, GStreamer, Roboflow Inference, Supervision, Frigate, Savant, OpenVINO, Hailo)

### Takeaway
For 48 hours, the fastest working multi-RTSP pipeline is **plain Python: one FFmpeg/OpenCV (or PyAV) reader thread per camera, a latest-frame buffer with reconnect, and batched GPU inference**. Alternatively, Roboflow Inference's `InferencePipeline` accepts a list of RTSP URLs. **DeepStream 8/9** is the production-throughput path on NVIDIA (pyservicemaker, since Python bindings are deprecated), but its learning curve is steep. **Frigate** is a useful reference and NVR, and since 0.16 it does face recognition, but it is built for home security, not restaurant analytics.

### Cited Findings
- **DeepStream 8.0** added Blackwell and **Jetson Thor** support, with a Jetson package on JetPack 7.0 (r38.2 BSP). Release notes are inconsistent: DS 9.0 notes say DS 8.0 used JP 7.1. DLA is not supported on Thor, nveglglessink is deprecated in favour of nv3dsink, and **Inference Builder** (an open-source microservice builder) was introduced. — [DeepStream 8.0 release notes](https://docs.nvidia.com/metropolis/deepstream/8.0/text/DS_Release_notes.html); [NVIDIA/deepstream GitHub](https://github.com/NVIDIA/deepstream)
- **DeepStream 9.0** (docs updated Apr 14, 2026), drawn from [DeepStream 9.0 release notes](https://archive.docs.nvidia.com/metropolis/deepstream/9.0/text/DS_Release_notes.html):
  - Jetson package on JetPack 7.1 (r38.4).
  - dGPU support: Turing, Ampere, Hopper, Ada, Blackwell.
  - **Python bindings deprecated; pyservicemaker recommended**, and it gained Smart-Record.
  - Cosmos Reason 2 VLM via the `nvvllmvlm` plugin.
  - OpenTelemetry/Prometheus metrics, REST health checks, blur-mask in OSD (useful for privacy redaction), OBB support.
  - TensorFlow, UFF and Caffe support were removed in DS 8.0.
  - Known issues: intermittent `g_mutex_clear()` on 60h+ live runs with NvDCF; XID errors above roughly 200 streams.
- NVIDIA DeepStream YOLOv7 sample on AGX-class Orin (1080p): 1 stream at batch 1 reached 124 FPS in deepstream-app; 16 streams at batch 16 reached 145 FPS aggregate. — [NVIDIA-AI-IOT yolo deepstream](https://github.com/NVIDIA-AI-IOT/yolov4_deepstream)
- **Roboflow Inference `InferencePipeline`** accepts RTSP URLs, webcams and MP4s at the same time (a list for `video_reference`), with sinks/callbacks for custom logic (JSON, MQTT). A multi-device licence and enterprise tier are sold separately. — [Roboflow blog: multiple streams](https://blog.roboflow.com/vision-models-multiple-streams/); [Roboflow multiple streams guide](https://roboflow.com/multiple-streams/yolov8)
- **Savant**: an open-source, DeepStream-based, YAML plus Python framework with RTSP, file, USB/CSI and Kafka-Redis source adapters and an "Always-On RTSP Stream Sink". Docker images for x86 and Jetson exist, but a mirror lists 0.2.11 for JetPack 5.1+ as "Production Release (Outdated)". Current 2026 status was not confirmed. — [Savant GitHub](https://github.com/insight-platform/savant)
- **Frigate**:
  - 0.16 added face recognition and LPR (Frigate+ not required). The Hailo-8 detector was refactored by Hailo, the Hailo driver was updated to 1.20.1 and included in the standard image, and ONNX/OpenVINO detectors gained D-FINE and RF-DETR support.
  - The OpenVINO detector runs on Intel and AMD CPUs, Intel GPUs and VPUs.
  - Current docs are for v0.18.

  — [idtechwire Frigate 0.16](https://idtechwire.com/frigate-0-16-adds-facial-and-license-plate-recognition-to-open-source-nvr/); [heise](https://heise.de/-10539498); [Frigate v0.16.0-beta3 notes](https://newreleases.io/project/github/blakeblackshear/frigate/release/v0.16.0-beta3); [Frigate face recognition docs](https://docs.frigate.video/configuration/face_recognition)
- Frigate face recognition uses the **`detect` stream**, not the recording stream. The docs advise choosing a resolution that captures facial detail at your camera's distance, and say CBR gives clearer images than VBR. — [Frigate face recognition docs](https://docs.frigate.video/configuration/face_recognition)

### Inferences
- **RTSP handling (practical):**
  - Run one reader process or thread per camera with `cv2.VideoCapture(url, cv2.CAP_FFMPEG)` or PyAV. Set `OPENCV_FFMPEG_CAPTURE_OPTIONS="rtsp_transport;tcp"`.
  - Keep only the latest frame (drop stale frames). This gives 5–10 fps sampling for free.
  - Use a watchdog: if no frame arrives within N seconds, release and reconnect with exponential backoff.
  - Use **sub-streams** (D1/720p) for detection, tracking and pose, and pull **main-stream** (1080p/4MP) crops only for face recognition.
  - Hikvision URL pattern: `rtsp://user:pass@IP:554/Streaming/Channels/101` (main) / `102` (sub). Dahua (and many Imou devices): `/cam/realmonitor?channel=1&subtype=0|1`. Ezviz/Imou consumer cams may need RTSP/"LAN live view" enabled in the app, and some models lock it down **[prior knowledge, not re-verified]**.
  - Batch the frames from all cameras into one GPU call per tick.
- Cameras' **H.265/H.265+ "smart codec"** settings and VBR can hurt decode stability and face sharpness. Set the cameras to H.264 or plain H.265 with CBR on the stream used for faces (follows the Frigate CBR advice).
- **Google MediaPipe** is good for single-person and on-device (mobile) use, not for a multi-RTSP server. Use it for the staff check-in kiosk (face enrollment on a tablet), not for the CCTV pipeline.
- `supervision` (MIT **[prior knowledge, not re-verified]**) plus `trackers` plus RF-DETR form an all-permissive Python stack that lets 4 people work in parallel without GStreamer expertise.
- Migrate to DeepStream (NVDEC decode, nvstreammux batching, nvinfer TensorRT, NvDCF) only after the MVP, when scaling past roughly 8–16 cameras per box.

### Gaps
- The licence of Roboflow Inference's core package was not confirmed (believed Apache-2.0 core with a separately licensed enterprise folder **[prior knowledge, not re-verified]**).
- No 2026 Savant release was confirmed. Frigate's licence (believed MIT **[prior knowledge]**) was not fetched.

---

## 5. Edge hardware: Jetson (Orin Nano Super / Orin NX / AGX Thor / T4000), RTX mini-PC, Coral, Hailo, Intel NPU — sizing and prices

### Takeaway
**Jetson prices rose 50–101% in July 2026** (Orin Nano Super devkit $249 → **$399**; Orin NX 16GB module $599 → $999; AGX Thor devkit $3,499 → $5,499). The cheap Jetson argument is therefore weaker. For a 6–16-camera restaurant running detection, tracking, pose and face, an **x86 mini-PC or small tower with an RTX-class GPU** gives the most headroom and the easiest Docker/PyTorch dev loop. An Orin NX 16GB suits about 4–8 cameras with a lean pipeline. Hailo-8 suits detection-only boxes. **Google Coral is not a fit**: the Edge TPU is legacy, and the new "Coral NPU" is milliwatt-class IP for ambient sensing, not multi-camera CCTV.

### Cited Findings
- **Jetson price increase (July 22, 2026)**, from NVIDIA's FAQ. No official reason was given; there are LPDDR4 supply/cost hints. — [CNX Software](https://www.cnx-software.com/2026/07/22/nvidia-increases-the-price-of-jetson-modules-and-devkits-by-up-to-101/); [Notebookcheck](https://www.notebookcheck.net/Nvidia-quietly-increases-Jetson-prices-by-up-to-101.1348323.0.html); [HWBusters](https://hwbusters.com/news/nvidia-jetson-prices-jump-up-to-101-the-249-orin-nano-super-is-now-399/)
  - Orin Nano Super Dev Kit: $249 → $399
  - Orin Nano 8GB module: $299 → $399
  - Orin NX 8GB: $399 → $649
  - Orin NX 16GB: $599 → $999
  - AGX Orin Dev Kit: $1,999 → $3,499
  - AGX Orin 64GB module: $1,599 → $2,999
  - AGX Thor Dev Kit: $3,499 → $5,499
  - T5000: $2,999 → $4,999
  - T4000 (Blackwell, 64GB): $1,999 → $2,999
- AGX Thor launched Aug 2025 at $3,499 (T5000 SoM, "2070 TOPS" FP4). — [CNX Software 2025](https://www.cnx-software.com/2025/08/19/3499-nvidia-jetson-agx-thor-developer-kit-2070-tops-jetson-t5000-som-for-robotics-and-edge-ai/?amp=1); [TweakTown](https://www.tweaktown.com/news/106933/nvidias-new-jetson-agx-thor-dev-kit-pre-orders-now-open-3499-looks-like-geforce-rtx-fe-card/index.html)
- **Jetson Orin Nano 2** was announced Aug 25, 2026: about 2× the Orin Nano Super's inference performance, about 40% less power, 78 TOPS, 8GB and an 8-core Arm CPU. The module and devkit are expected in **1H 2027**, so it is not available now. JetPack 7.2.1 shipped Aug 12, 2026, and JetPack 6.2.2 for Orin on Feb 6, 2026. — [JetsonHacks Aug 2026 newsletter](https://jetsonhacks.com/2026/08/26/jetsonhacks-august-2026-newsletter/)
- Orin Nano Super, measured: YOLOX-S FP16 TensorRT at 640 px gave about 25 FPS in Python/OpenCV (15 W mode, jetson_clocks), drawing under 9 W. — [NVIDIA forum](https://forums.developer.nvidia.com/t/expected-fps-for-yolox-s-tensorrt-engine-on-jetson-orin-nano-jetpack-6-2/329875)
- Orin NX 16GB (Ultralytics guide, YOLOv8s 640 px TensorRT): FP32 64 FPS, FP16 126 FPS, INT8 181 FPS. — [Ultralytics DeepStream on Jetson guide](https://docs.ultralytics.com/ko/guides/deepstream-nvidia-jetson/)
- **Hailo** — [electromaker comparison](https://www.electromaker.io/blog/article/hailo-8-vs-hailo-8l-vs-hailo-10h-which-ai-accelerator-should-you-buy); [botmonster Hailo-10H review](https://botmonster.com/hardware/hailo-10-ai-accelerator-edge-inference-review/); [codesota edge register](https://www.codesota.com/embedded-ai); [specpicks](https://specpicks.com/reviews/hailo-8-vs-hailo-8l-vs-coral-tpu-pi-5-2026); [Core Electronics](https://core-electronics.com.au/hailo-8-m2-ai-accelerator-module-26-tops.html.plain.md):
  - Hailo-8: 26 INT8 TOPS, street price about $170 (2026 Frigate-focused review) or about AUD 345 retail.
  - Hailo-10H: 40 TOPS INT4 / 20 INT8, with 4–8GB on-module LPDDR4. Mainly worth it for GenAI.
  - Datasheet: YOLOv8m 140 FPS on Hailo-8 (batch 8).
  - Compiled table: YOLO11m 70 FPS on Hailo-8 vs 95 FPS on 10H; YOLO11n 135 vs 210 FPS (batch 1).
  - One review: Hailo-8 held 30 FPS on each of four 1080p streams with YOLOv8s on a Raspberry Pi 5.
- **Google Coral NPU** (Google Research, Oct 15, 2025): open-source RISC-V IP (Apache-2.0) with an MLIR/IREE toolchain supporting PyTorch, JAX and LiteRT. The base design gives about **512 GOPS at a few milliwatts**, compared with the original Coral Edge TPU's 4 TOPS at about 1 W. It targets ambient sensing and tiny Gemma models. First silicon is in the Synaptics Astra SL2610 (Torq NPU). — [Google Research blog: Coral NPU](https://research.google/blog/coral-npu-a-full-stack-platform-for-edge-ai/); [Google Developers blog](https://developers.googleblog.com/en/introducing-coral-npu-a-full-stack-platform-for-edge-ai/); [InfoQ](https://www.infoq.com/news/2025/10/google-coral-npu-platform)
- Legacy Edge TPU status is unclear. One unofficial wiki (July 2026) says the Edge TPU generation was "wound down", while other 2026 guides still sell the USB accelerator. No Google announcement was found. — [aiwiki Edge TPU](https://aiwiki.ai/wiki/edge_tpu/raw)

### Inferences (sizing; back-of-envelope, not benchmarked)
- Workload for 8 cameras at 10 fps is 80 detector frames/s.
  - On a T4-class GPU, YOLO26s (2.5 ms) or RF-DETR-S (3.5 ms) at batch 1 gives about 285–400 frames/s of detector capacity, before batching gains.
  - Pose on person crops, or RTMO on the full frame at 3–5 fps, plus face embedding on about 1–3 best crops per track per second, adds roughly 30–60% load.
  - Estimate: **one RTX 3060/4060-class (T4-or-better) GPU ≈ 12–20 cameras at 10 fps with detection, tracking, pose and face**. Decode (NVDEC) and Python overhead usually become the bottleneck before the GPU does. Assumes TensorRT FP16 and sub-stream input.
- **Orin NX 16GB** (YOLOv8s FP16 126 FPS) gives roughly 8–10 cameras of detection only at 10 fps, or about **4–6 cameras with pose and face** in Python. More is possible with DeepStream and INT8.
- **Orin Nano Super** (about 25 FPS YOLOX-S in Python) gives roughly **2–3 cameras** at 10 fps in Python, perhaps 4–6 with DeepStream, INT8 and the YOLO26n/RF-DETR-N class. That is too tight for the full feature set.
- **AGX Thor/T4000** is overkill for a single restaurant at $3–5.5k.
- **Hailo-8** (about $170) on an x86 mini-PC or Pi 5 can carry detection for about 4–8 streams. Face, pose and Re-ID would then fall to the CPU or iGPU (OpenVINO), giving a cheap but fragmented, multi-SDK stack.
- **Intel Core Ultra iGPU/NPU via OpenVINO** is a viable mid-cost option for small shops (Frigate supports it). Its throughput for this full pipeline was not measured.
- Coral (legacy Edge TPU: 4 TOPS, TFLite INT8 only, limited operator support) cannot run DETR-style detectors, pose and ArcFace together across many streams. Coral NPU is not a product for this use at all. Recommend against Coral, even though the team prefers Google.

### Gaps
- Vietnam street prices for RTX mini-PCs and Jetson boards (VND) were not researched.
- No measured multi-stream benchmark of detection plus pose plus face on Orin NX, Orin Nano Super or a consumer RTX card was found. The sizing above is inferred.
- NVDEC/NVENC capability of the Orin Nano (it reportedly lacks NVENC) was not verified this session.

---

## 6. Face recognition: InsightFace / ArcFace / AdaFace / DeepFace / MediaPipe / quality assessment / low-res CCTV / Asian bias / commercial alternatives

### Takeaway
**InsightFace code is MIT, but all its pretrained weights (buffalo_l, antelopev2, SCRFD) are non-commercial research only.** They are fine for the hackathon demo; for production, swap them out. Commercially usable options found:
- **AuraFace** (Apache-2.0, ResNet100 ArcFace-style; training data not disclosed)
- **OpenCV Zoo SFace** (Apache-2.0, weaker) plus **YuNet** detector (MIT/Apache)
- **OFIQ** (MIT, ISO/IEC 29794-5 reference implementation) for face quality

CCTV faces are the weakest link: enforce a minimum face size, multi-frame voting and best-crop selection.

### Cited Findings
- The InsightFace model zoo states that "ALL models are available for non-commercial research purposes only". The Python library code is MIT, and users can "replace the pretrained models we provide with your own models". — [InsightFace model zoo README](https://github.com/deepinsight/insightface/blob/e68b8b076fb11e9f75c87244d234385f0f318181/model_zoo/README.md); [PyPI insightface](https://pypi.org/project/insightface/0.6.1/)
- Converting the weights (e.g. buffalo_l/antelopev2 to safetensors) does not change the non-commercial restriction. A suggested commercial swap is **YuNet** detector plus **AuraFace** recognizer; the SCRFD detector bundled with AuraFace is the same file as buffalo_l's and stays non-commercial. — [HF ZenTrainer models note](https://huggingface.co/nynxz/Zentrainer)
- **AuraFace-v1** (fal): Apache-2.0, ResNet100 trained with ArcFace-style angular margin on "commercially and publicly available data" (datasets not named). A community ONNX repack warns that the fal repo also contains InsightFace detection and landmark models, which are non-commercial. — [fal/AuraFace-v1 model card](https://huggingface.co/fal/AuraFace-v1/blob/main/README.md); [imagent/auraface-onnx](https://huggingface.co/imagent/auraface-onnx)
- **OpenCV Zoo**: SFace is Apache-2.0. YuNet is listed as MIT by one source and Apache-2.0 by another; both are permissive. Per-model licences govern. SFace's training data is not stated (the paper used CASIA-WebFace, VGGFace2, MS1M), which leaves residual dataset-licence risk. — [opencv_zoo mirror](https://github.com/Charles-258/opencv_zoo); [mudler face-detect-gguf](https://huggingface.co/mudler/face-detect-gguf); [opencv_zoo HF README](https://huggingface.co/opencv/opencv_zoo/blame/main/README.md)
- **Frigate's production face pipeline (v0.18 docs)**:
  - Face detection uses an OpenCV DNN model on CPU (or a detector that outputs `face` natively); a person must be detected first.
  - Recognition uses a **small FaceNet** model (CPU) or a **large ArcFace** model (GPU/NPU recommended), after landmark alignment.
  - Defaults: min face area **750 px²**, unknown threshold 0.8, recognition threshold 0.9, blur filter on.
  - Recognition is "weighted across many frames by face area", so a single hit does not assign a label.
  - Enrollment advice: 5–10 images per person minimum, 20–30 recommended, 50–100 ideal; start with 1–5 clear frontal photos; avoid bulk uploads (over-fitting).
  - Accuracy is bounded by camera DORI "identification" range.

  — [Frigate face recognition docs](https://docs.frigate.video/configuration/face_recognition)
- Apple's on-device face embedding is AirFace-inspired with MobileNetV3-style blocks, trained with an ArcFace-style angular margin plus "margin-mining softmax". It produces an embedding in under 4 ms on the Neural Engine. Worst/best demographic-subset accuracy went 0.23/0.66 → 0.68/0.84 → **0.86/0.96** with margin-mining and augmentation (including synthetic masks). Training data came from a paid crowd spanning ages, genders and ethnicities. — [Apple ML Research](https://machinelearning.apple.com/research/recognizing-people-photos)
- **NIST demographic effects (NISTIR 8280, 2019 — older)**: false positives were highest for West/East African and East Asian faces on high-quality application photos for many algorithms, but "with a number of algorithms developed in China this effect is reversed". Better image quality reduces false negatives and differentials. — [NISTIR 8280](https://nvlpubs.nist.gov/nistpubs/ir/2019/NIST.IR.8280.pdf); [Scientific American](https://www.scientificamerican.com/article/how-nist-tested-facial-recognition-algorithms-for-racial-bias/); [NIST demographics 1:N slides](https://pages.nist.gov/frvt/html/slides/demographics_1N.pdf)
- **Face image quality**:
  - **OFIQ** (German BSI) is open-source under MIT/liberal licences ("commercial use possible, no copy-left") and the reference implementation of **ISO/IEC 29794-5**. — [Busch OFIQ slides](https://christoph-busch.de/files/Busch-OFIQ-241119.pdf); [BiometricUpdate](https://www.biometricupdate.com/202404/biometric-face-image-quality-standard-draft-released-along-with-assessment-tool); [OFIQ repo](https://github.com/BSI-OFIQ/OFIQ-Project)
  - **MagFace** and SDD-FIQA were shortlisted by NIST for a unified quality score. — [NIST IFPC 2022 OFIQ status](https://pages.nist.gov/ifpc/2022/presentations/4_2022-11-14_IFPC-OFIQ%20implementation%20status.FINAL.pdf)

### Inferences
- **Recommended face pipeline for production (all permissive):**
  1. YuNet (or the person detector plus head-region crop) on main-stream crops of tracked persons.
  2. 5-point alignment.
  3. Quality gate: inter-ocular distance, a Laplacian-variance blur score, yaw/pitch from landmarks. Optionally use OFIQ or the embedding norm (MagFace-style) as the quality score.
  4. AuraFace embedding (512-d), keeping the top-K crops per track.
  5. Average the embeddings per track (a "track template").
  6. Match against a gallery in pgvector/FAISS.

  For the hackathon, InsightFace buffalo_l is acceptable (non-commercial demo) and is the fastest to integrate (`insightface.app.FaceAnalysis`).
- **Low-res CCTV:** the Frigate default of 750 px² is about a 27×27 px face, a practical floor. Recognition is reliable only at roughly 40–60 px+ face height. Place one camera at the entrance or cashier at face height to capture good frontal faces, and let the other ceiling cameras rely on track handover (Re-ID plus floor plan) rather than face. Configure that camera's main stream with CBR and a fast shutter.
- **Asian/Vietnamese bias:** the 2019 NIST data shows demographic differentials depend strongly on the algorithm's training data. Validate on a small consented local test set (e.g. team plus staff, about 20–50 identities) and tune thresholds on it. Do not trust western-benchmark thresholds. Apple's margin-mining result shows the gap is trainable.
- AdaFace (designed for low-quality images, MIT code) and ElasticFace are strong research options, but their public weights are trained on MS1MV2/WebFace4M/12M, which carry research-only dataset terms **[prior knowledge, not re-verified]**. They are not a clean commercial answer.
- DeepFace (Python wrapper, MIT **[prior knowledge]**) is convenient, but each backend model keeps its own licence. It does not solve the licensing problem.
- MediaPipe Face Detector (BlazeFace short-range) is designed for near-camera faces (selfie/kiosk) **[prior knowledge, not re-verified]**. Use it on the staff enrollment tablet, not for far CCTV.
- InsightFace sells commercial licences for its models **[prior knowledge, not re-verified]**. Ask for a quote if AuraFace accuracy is insufficient.

### Gaps
- CR-FIQA and SER-FIQ licences were not found.
- No NIST FRTE results for AuraFace or SFace exist that could be found. No published benchmark on low-resolution Vietnamese CCTV faces was found.
- No recent (2024–2026) NIST demographic update specific to East or Southeast Asian faces was retrieved.

---

## 7. Apple-Photos-style face clustering (online/incremental, merge/split, label propagation; borrowable OSS)

### Takeaway
Combine three ideas:
1. **Apple's two-pass method**: a conservative greedy agglomerative pass inside a "moment" (here, one visit or session) using face plus upper-body, then a face-only HAC pass across moments; assign new faces via multiple exemplars per person.
2. **Immich's incremental DBSCAN-like approach** (core points from "min faces", a max-distance threshold, a nightly re-run).
3. A **Frigate-style face library** for admin naming and training.

Bias towards over-splitting: merging is cheap for the admin, while bad merges are hard to undo.

### Cited Findings
- **Apple Photos (2021 blog; older but still the canonical write-up)** — [Apple ML Research: Recognizing People in Photos Through Private On-Device ML](https://machinelearning.apple.com/research/recognizing-people-photos):
  - **Detection:** one network detects faces and upper bodies, matched by box geometry, and separate networks embed each.
  - **Pass 1:** greedy agglomerative clustering tuned for precision ("many, smaller clusters"). Upper-body is used only within a "moment" (time and location). Distance is D = min(F, α·F + β·T). Each cluster is represented by the running average of its embeddings.
  - **Pass 2:** face-only HAC across moments, with median-distance linkage plus random sampling for large clusters. It runs as fast as single-linkage with accuracy "on par or better than average-linkage HAC". Timing: 3.5 s vs 205.8 s for average linkage at iteration 65.
  - Clustering runs **periodically (overnight while charging)**. A "gallery" of known people is chosen by heuristics on cluster size, distances and **user input**.
  - **New faces are assigned via multiple canonical exemplars per cluster using sparse coding** (min ‖y − Dx‖² + λ‖x‖₁; highest per-cluster energy wins), or marked unknown.
  - An **uncertainty branch** filters false or out-of-distribution detections so they don't pollute the gallery.
- **Immich** — [Immich facial recognition docs](https://docs.immich.app/features/facial-recognition); [Immich PR #5598](https://github.com/immich-app/immich/pull/5598); [Immich archived v2.2.0 docs](https://docs.v2.2.0.archive.immich.app/features/facial-recognition); [Immich discussion #32382](https://github.com/immich-app/immich/discussions/32382):
  - Clustering is "derived from DBSCAN". "Minimum Recognized Faces" sets the core-point threshold, and "Maximum recognition distance" sets the similarity threshold (recommended between **0.3 and 0.7**).
  - A threshold that's too low means merging duplicates later, but one that's too high "can produce unsalvageable results".
  - Unlike textbook DBSCAN it is **incremental**: existing people are kept as new faces arrive, and a full re-run behaves like DBSCAN.
  - It uses top-K vector search (not every neighbour within range), so a **nightly job** handles deferred matching.
  - Known pain point: changing global parameters "destructively affects everything else". Users have asked for a lower-threshold second pass to split wrongly merged people (feature request, not shipped).
- **Frigate face library**: an "Add Face" wizard, plus a Train tab where detected faces show confidence scores and the admin assigns them to a person. Recommended 20–30 images per person; avoid bulk uploads (over-fitting). — [Frigate face recognition docs](https://docs.frigate.video/configuration/face_recognition)

### Inferences
- **Easy FnB clustering design (borrowing from Apple and Immich):**
  1. **Unit = track, not frame.** Per tracked person per visit, keep the top-K quality face crops and average them into a visit template. This plays the role of Apple's "moment", and staff uniforms/upper-body can help within a visit.
  2. **Online assignment:** compare the new visit template against each named person's exemplars (keep about 5–20 diverse exemplars per person, e.g. a k-medoids selection). Assign if cosine similarity ≥ T_high. Mark as "unknown" if below T_low. Queue "maybe" cases between the two thresholds for admin confirmation.
  3. **Unknown pool clustering:** nightly (restaurant closed), run HDBSCAN or agglomerative clustering with average/median linkage on unknown visit templates. Require at least 2–3 visits before proposing a "person" card. This reduces one-off customers and false positives.
  4. **Admin UI (Apple-Photos-like):** person cards with face thumbnails and the actions *Name*, *Merge* ("same person?" suggestions ranked by centroid distance), *Split* (re-cluster that person's faces with a tighter threshold, which is what Immich users asked for), *Not this person* (removes the face and adds a "cannot-link" constraint) and *Hide/forget* (needed for erasure requests).
  5. **Label propagation:** once a person is named, all faces in the cluster inherit the name. Future visits auto-assign via exemplars. Admin corrections become must-link/cannot-link constraints in the next nightly re-clustering. Never auto-merge two named people.
- Libraries: `hdbscan`/`sklearn.cluster.HDBSCAN`, `sklearn` AgglomerativeClustering (distance_threshold, linkage='average'), and FAISS or pgvector for kNN. dlib's **Chinese Whispers** graph clustering is a simple, parameter-light alternative for face graphs **[prior knowledge, not re-verified]**. Immich (AGPL-3.0 **[prior knowledge]**) is a good design reference; read its clustering code for ideas rather than copying it into closed-source code.
- Google Photos face grouping traces back to Google's **FaceNet** (2015), which demonstrated clustering of personal-photo faces via embeddings plus agglomerative clustering **[prior knowledge, not re-verified — arXiv 1503.03832]**. No recent Google blog post detailing the current Google Photos clustering was found.

### Gaps
- No public Google Research post describing Google Photos' current face clustering (2023–2026) was found.
- PhotoPrism's clustering details were not retrieved. No quantitative comparison of DBSCAN vs HDBSCAN vs Chinese Whispers on CCTV-quality faces was found.

---

## 8. Staff identification: uniform/attribute vs face; consent-based enrollment at shift start

### Takeaway
Use a **two-signal approach**. (a) A **uniform classifier** (staff vs customer) on person crops: cheap, works from any angle, needs no biometrics. (b) **Consented face enrollment** at shift start (tablet kiosk) to bind *which* staff member it is, then carry identity via the tracker, Re-ID and floor-plan handover. This also meets the Vietnamese law's requirement that employees "clearly know" the monitoring measure (Art. 25(3), section 9).

### Cited Findings
- Upper-body appearance (clothing) is a stable cue "within a specific context". Apple uses it only within a time-bounded "moment", which matches one work shift. — [Apple ML Research](https://machinelearning.apple.com/research/recognizing-people-photos)
- Frigate requires a `person` detection before attempting face recognition, and weights recognition across frames. — [Frigate face recognition docs](https://docs.frigate.video/configuration/face_recognition)
- PDPL Art. 25(3): employers may apply technology or technical monitoring measures only if they are lawful, protect workers' rights, and **"on the basis that the employee clearly knows that measure"**. Employee data must be deleted when the contract ends unless agreed or required otherwise. — [hethongphapluat: PDPL Art. 25](https://hethongphapluat.com/luat-bao-ve-du-lieu-ca-nhan-2025/dieu-25)
- Law-firm view: consent in employment is "fragile" because of the power imbalance (example: forced fingerprint timekeeping). — [Conventus Law (Aug 2026)](https://conventuslaw.com/report/already-in-breach-three-common-company-practices-vietnams-new-personal-data-protection-law-prohibits/)

### Inferences
- **Uniform classifier options:**
  1. Fine-tune the detector with a separate `staff` class (RF-DETR-S; about 300–500 labelled crops is usually enough when uniforms are distinctive).
  2. A tiny classifier (MobileNet/EfficientNet-B0 or a linear probe on DINOv2/CLIP features) on torso crops.
  3. For a 48-hour MVP, an HSV colour histogram of the torso region compared against the uniform's colour.

  Combine with the "staff-only zone" prior (kitchen/cashier polygons on the floor plan).
- **Shift-start enrollment:** a tablet at the staff entrance shows a consent screen, takes 5–10 frontal photos (MediaPipe/YuNet for the capture UI) and links them to an employee ID. That day's gallery is then active only during the shift. Optionally offer non-biometric fallbacks (a BLE badge or QR check-in plus uniform-plus-tracking) so consent stays genuinely voluntary.
- Once a staff track is identified (by face at the entrance or clock-in point), propagate the ID along the track and across cameras via floor-plan and Re-ID. Re-confirm with a face whenever a good crop appears. Staff floor-map heatmaps and "time at table" then come almost for free.

### Gaps
- No published accuracy figures for uniform-based staff/customer classification in restaurants were found. Effort estimates above are engineering judgement.

---

## 9. Vietnam legal: biometric/face data under PDPL (Law 91/2025/QH15) and Decree 356/2025 (replacing Decree 13/2023)

### Takeaway
From **1 Jan 2026**, the **PDPL (Law 91/2025/QH15)** and **Decree 356/2025/ND-CP** (replacing Decree 13/2023) govern this. **Biometric data is sensitive personal data**, and recognising faces requires **explicit, specific, voluntary, informed consent** (silence is not consent), plus biometric security controls and a **DPIA filed with A05 (Ministry of Public Security)**. Plain security CCTV in public areas can run without consent but **with notice** (Art. 32). Re-using that footage for face recognition of customers (e.g. recognising regulars) is a different purpose and should be **opt-in only**. Keeping video and embeddings on-premise avoids cross-border transfer obligations.

### Cited Findings
- The PDPL was enacted 26 June 2025 and took effect **1 Jan 2026**. Its implementing decree, **Decree 356/2025/ND-CP**, was issued 31 Dec 2025 and took effect 1 Jan 2026. — [Tilleke & Gibbins](https://tilleke.com/insights/vietnams-new-personal-data-protection-law-a-closer-look); [LuatVietnam](https://luatvietnam.vn/legal-updates/the-latest-law-on-personal-data-protection-and-the-guiding-documents-892-106778-article.html); [Thư viện Pháp luật: Nghị định 356/2025](https://thuvienphapluat.vn/van-ban/Quyen-dan-su/Nghi-dinh-356-2025-ND-CP-huong-dan-Luat-Bao-ve-du-lieu-ca-nhan-687428.aspx)
- Decree 356 **replaces Decree 13/2023/ND-CP**. Its Arts. 3–4 list basic and sensitive personal data, with **biometric data in the sensitive list**. — [Vietnam Briefing](https://www.vietnam-briefing.com/news/vietnam-law-on-personal-data-protection-latest-developments-and-insights.html/); [Luật Việt An: Decree 356 vs Decree 13](https://luatvietan.vn/diem-moi-cua-nghi-dinh-356-2025-so-voi-nghi-dinh-13-2023-ve-huong-dan-bao-ve-du-lieu-ca-nhan.html); [official text (vbpl.moj.gov.vn)](https://vbpl.moj.gov.vn/TW/Lists/vbpq/Attachments/187276/ND.356.2025.doc)
- Biometric data including "facial geometry" is "expressly classified as sensitive personal data". It requires "explicit, specific, voluntary and informed consent". — [Conventus Law (Aug 2026)](https://conventuslaw.com/report/already-in-breach-three-common-company-practices-vietnams-new-personal-data-protection-law-prohibits/)
- Silence or non-response is not consent. — [UniConsent PDPL summary (vendor; treat with care)](https://www.uniconsent.com/vietnam-pdpl)
- Decree 356 widens the valid forms of consent, e.g. recorded calls, email, or in-app mechanisms. — [Thư viện Pháp luật/LuatVietnam summaries](https://luatvietnam.vn/dan-su/nghi-dinh-356-2025-nd-cp-quy-dinh-chi-tiet-luat-bao-ve-du-lieu-ca-nhan-422896-d1.html)
- **PDPL Art. 31 (location and biometric data)**: biometric data is defined as data on a person's distinctive, stable physical or biological characteristics used to identify them. Processors must apply **physical security for the devices that store and transmit biometric data, restrict access, run a monitoring system** to prevent and detect breaches, follow law and relevant international standards, and **notify the data subject if processing causes damage**. — [hethongphapluat: PDPL Art. 31](https://hethongphapluat.com/luat-bao-ve-du-lieu-ca-nhan-2025/dieu-31)
- **PDPL Art. 32 (audio and video recording in public places and public activities)** — [hethongphapluat: PDPL Art. 32](https://hethongphapluat.com/luat-bao-ve-du-lieu-ca-nhan-2025/dieu-32):
  - Recording and processing **without consent** is allowed for (a) national defence, security, public order *or protecting lawful rights and interests*, (b) public events, and (c) other cases provided by law.
  - The recorder **must notify** the people being recorded, or otherwise make them aware, unless law says otherwise.
  - The data may be used only for the collection purpose and kept only as long as needed, then deleted.
- **PDPL Art. 25 (employment)**: candidate consent is required. Monitoring tech is allowed only if employees clearly know about it. Data is deleted at contract end. — [hethongphapluat: PDPL Art. 25](https://hethongphapluat.com/luat-bao-ve-du-lieu-ca-nhan-2025/dieu-25)
- **DPIA**: it must be prepared and submitted to **A05** (Dept. of Cybersecurity and High-Tech Crime Prevention, MPS) within **60 days** of starting processing, and refreshed every 6 months if anything changes. — [Conventus Law](https://conventuslaw.com/report/already-in-breach-three-common-company-practices-vietnams-new-personal-data-protection-law-prohibits/)
  - Small businesses and startups may opt out of DPIA for 5 years and household/micro businesses are exempt, **but not if they process sensitive data**. — [Tilleke & Gibbins](https://tilleke.com/insights/vietnams-new-personal-data-protection-law-a-closer-look)
- **Penalties**: up to **VND 3 billion** for general violations; cross-border transfer violations up to **5% of prior-year revenue** (with a VND 3 billion floor); illegal data trading up to 10× the illicit revenue. Individuals face up to half the corporate fine, and criminal liability is possible. — [Tilleke & Gibbins](https://tilleke.com/insights/vietnams-new-personal-data-protection-law-a-closer-look); [Conventus Law](https://conventuslaw.com/report/already-in-breach-three-common-company-practices-vietnams-new-personal-data-protection-law-prohibits/)
- Cloud services (Google Workspace, AWS, etc.) are described as moving data offshore, which triggers the Transfer Impact Assessment (TIA) requirements. — [Conventus Law](https://conventuslaw.com/report/already-in-breach-three-common-company-practices-vietnams-new-personal-data-protection-law-prohibits/)

### Inferences
- **Practical compliance pattern for Easy FnB:**
  1. Signage at the entrance (CCTV notice under Art. 32) covers security CCTV and anonymous analytics such as counting, tableware detection and dwell time.
  2. **Customer face recognition = opt-in loyalty enrollment only**, e.g. "Nhận diện khách quen" via a Zalo/QR form with explicit consent. Faces of non-enrolled customers should not be turned into persistent identity clusters. Two options: run the Apple-style "unknown people" clustering **only within a short retention window**, with automatic purge, or apply it only to enrolled or consenting people. Prefer the conservative reading; the auto-cluster-unknown-customers feature is the legally riskiest part.
  3. **Staff:** written notice and consent for face-based identification, a non-biometric alternative, and deletion of templates at contract end (Art. 25).
  4. Store embeddings encrypted on the edge box, restrict access, keep audit logs (Art. 31). File a DPIA (sensitive data means no SME exemption).
  5. Keep raw video **and** biometric templates on-prem. Send only aggregated, non-identifying metrics to Google Cloud, to avoid TIA and cross-border exposure.
- Art. 32's "protecting lawful rights and interests" ground plausibly covers security CCTV, but it does not obviously extend to biometric identification for marketing. Get a lawyer's opinion before commercial launch.
- Decree 13/2023 also classified biometric data as sensitive **[prior knowledge, not re-verified]**. The 2026 regime keeps and tightens this.

### Gaps
- The exact article numbers in Decree 356 on consent form and on sensitive-data processing, and any specific rule on facial recognition from CCTV, were not read in the primary text (the PwC PDF returned 403; the official .doc was not parsed).
- No official A05 guidance on retail or restaurant facial recognition was found.

---

## 10. Recommended stack and 48-hour build path

### Takeaway
**MVP stack:**
- **Python 3.11 + Docker on an x86 box with an RTX GPU**
- FFmpeg/OpenCV RTSP readers (sub-stream at 5–10 fps)
- **RF-DETR-S** (Apache-2.0) fine-tuned for person/staff/bowl/plate/cup/hotpot (or YOLO26s for the demo, if AGPL is accepted)
- Roboflow **`trackers` ByteTrack/OC-SORT** (Apache-2.0)
- **rtmlib RTMO-s** for pose (Apache-2.0)
- Floor-plan **homography** for localisation
- **InsightFace buffalo_l for the demo → AuraFace + YuNet for production**
- Quality gate plus track-level templates
- **pgvector or FAISS** gallery, with incremental clustering (threshold assignment plus nightly HDBSCAN/agglomerative)
- **Kafka** (team skill) or Redis Streams for events
- FastAPI plus a web admin UI for "People" naming, merging and splitting

DeepStream, Metropolis MTMC and Jetson come later, as scale-out options.

### Cited Findings
- RF-DETR N/S/M/L, Seg and Keypoint are Apache-2.0 and "designed for fine-tuning". — [roboflow/rf-detr](https://github.com/roboflow/rf-detr)
- `trackers` (Apache-2.0) offers `tracker.update(detections)` with supervision and built-in HOTA/IDF1 evaluation. — [trackers docs](https://trackers.roboflow.com/latest)
- rtmlib (Apache-2.0, no mmcv) supports RTMO/RTMPose with an RF-DETR detector and a `PoseTracker` helper. — [rtmlib](https://github.com/Tau-J/rtmlib)
- Roboflow `InferencePipeline` takes a list of RTSP URLs as an off-the-shelf multi-stream reader. — [Roboflow blog](https://blog.roboflow.com/vision-models-multiple-streams/)
- Frigate's face-library UX (upload, train tab, per-person image counts) is a working reference for the admin flow. — [Frigate docs](https://docs.frigate.video/configuration/face_recognition)
- Immich's incremental DBSCAN-variant plus nightly job is a working reference for clustering. — [Immich docs](https://docs.immich.app/features/facial-recognition)
- DeepStream 9 pyservicemaker, NvDCF and blur-mask are the scale-out path; Python bindings are deprecated. — [DeepStream 9.0 notes](https://archive.docs.nvidia.com/metropolis/deepstream/9.0/text/DS_Release_notes.html)

### Inferences (48-hour plan for about 4 people)
- **H0–4 (all):**
  - Freeze the architecture.
  - Get RTSP URLs from 2–4 real cameras, or record 10–15-minute MP4s from them as a fallback demo input. Live demos often fail on venue Wi-Fi.
  - Set up a Docker compose with services `ingest`, `vision`, `identity`, `api`, `ui` and `kafka`/`redis`.
- **Dev A (AI lead), H4–24:**
  - vision worker: batched RF-DETR/YOLO26 → trackers → per-track JSON events (`camera_id, track_id, bbox, class, foot_xy_plan, ts`).
  - Auto-label tableware with Grounding DINO/YOLOE on recorded frames (about 300–800 images), then fine-tune RF-DETR-S (about 1–3 h on one GPU).
- **Dev B, H4–24:**
  - Ingest service: reader per camera, reconnect watchdog, latest-frame queue, sub-/main-stream pairing.
  - Homography calibration tool (click 4+ points per camera on the floor plan, save a 3×3 matrix) and plan-space projection.
- **Dev C, H4–30:**
  - identity service: face detect, align and quality-gate on main-stream crops of person tracks.
  - Embed (buffalo_l now; swappable interface for AuraFace).
  - Track template → gallery match (thresholds tuned on the team's own faces) → unknown pool → nightly or on-demand clustering → merge/split APIs.
  - Staff enrollment endpoint (tablet webcam).
- **Dev D, H4–36:** admin UI covering:
  - live floor map with staff dots (WebSocket);
  - "People" grid (Apple-style) with Name, Merge, Split and Not-this-person;
  - table status from tableware counts (bowls/plates on table → occupied/finished);
  - consent and enrollment screens;
  - CCTV notice text.
- **H24–40 (integration):**
  - Cross-camera global ID: plan-space proximity plus time gating plus OSNet cosine (via torchreid or BoxMOT weights for the demo) plus face override.
  - Uniform classifier (HSV histogram first; small CNN if time allows).
  - Pose (RTMO-s) only for "hand raised" and "standing vs seated" events.
- **H40–48:** harden (reconnect tests, GPU memory), record a backup demo video, prepare the slide on the licensing and compliance path:
  - AGPL → Apache swap.
  - InsightFace → AuraFace.
  - On-prem biometrics.
  - Opt-in customer recognition and DPIA.
- **Production bill of materials for one restaurant (6–12 cams), indicative:**
  - Compute options: an x86 mini-PC/tower with an RTX 4060/5060-class GPU (VND price not researched), **or** Jetson Orin NX 16GB (module now $999 1KU, plus a carrier board) for 4–6 cams.
  - Plus a cheap tablet for enrollment.
  - Avoid Coral. Consider Hailo-8 (about $170) only for detection-only SKUs.

### Gaps
- No end-to-end reference implementation combining all of these components was found. Time estimates are engineering judgement.
- Actual RTSP behaviour and settings of the specific Imou/Ezviz consumer models were not verified.
