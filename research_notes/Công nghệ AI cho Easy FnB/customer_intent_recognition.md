# Recognizing Restaurant Customers' Service Needs from CCTV (gestures, actions, attention, intent) — research notes, as of 2026-11-03

Scope: vision-only detection of "customer needs a server" events from ceiling-mounted CCTV (raise hand, "check please" mime, hold up empty glass, wave, look around for a waiter, stand up). Speed target is seconds, with high precision. Google / open-source preferred. Hackathon: 48 h, about 4 people.

Note on method: I ran about 25 searches and fetches. Numbers below come from primary docs and papers where I could fetch them. Numbers from search-result summaries are marked as such. Anything I could not source is under "Gaps" or labelled as an inference.

---

## 1. Skeleton/pose-based action recognition SOTA (PoseC3D, ST-GCN family, CTR-GCN, 2025–2026 work, MMAction2/pyskl): practicality for few-shot custom gestures; accuracy and latency

### Takeaway
Skeleton action recognition is mature. On NTU-120 (cross-subject) the best numbers sit around 86–91%, and 2025 papers add only marginal gains. The practical open-source toolkits (pyskl, MMPose/MMAction2) are Apache-2.0 but are maintained slowly or not at all. For a 48-hour build with a few hundred self-recorded clips, a pose extractor (RTMPose/RTMO or YOLO-pose) plus a small classifier over keypoint sequences (ST-GCN++ fine-tuned from NTU weights, or simply a GRU/MLP over hand-crafted keypoint features) is the realistic path. Full PoseC3D training is heavier than the timeline allows.

### Cited Findings
- **PoseC3D (PoseConv3D) on HRNet-2D keypoints, pyskl model zoo:** NTU-60 XSub 94.1% (two-stream; 93.7% joint only, SlowOnly-R50), NTU-60 XView 96.9%, NTU-120 XSub 86.7%, NTU-120 XSet 90.3%, FineGYM 94.1% mean-class. Lighter backbones (C3D-light 93.3%, X3D-Shallow 92.4% on NTU-60 XSub) lose only about 1 point. The example test pipeline uses `UniformSampleFrames clip_len=48`. 10-clip testing is slower, and `num_clips=1` speeds inference with a small accuracy loss. — [pyskl PoseC3D README](https://github.com/kennymckormick/pyskl/blob/main/configs/posec3d/README.md)
- **pyskl status:** supports ST-GCN, ST-GCN++, CTR-GCN, AAGCN, MS-G3D, DG-STGCN, PoseConv3D and RGBPoseConv3D. Licence Apache-2.0. The README says it is "currently not maintained by the developer", and the last changelog entry is 2023-03-20. It includes a **real-time gesture-recognition demo on CPU built on ST-GCN++** (added 2023-02-10), a notebook for extracting 2D skeletons from arbitrary RGB video with HRNet, and a script that estimates each model's inference speed. — [pyskl GitHub](https://github.com/kennymckormick/pyskl)
- **2025 state of the art:** LSTC-MDA (arXiv 2509.14619, Sep 2025) self-reports 90.4% NTU-120 XSub and 92.0% XSet, claimed SOTA on NTU-60/120 and NW-UCLA (not independently verified). — [arXiv 2509.14619](https://arxiv.org/html/2509.14619v1)
- A 2025 review (arXiv 2506.00915) tabulates 2022–2023 GCN and Transformer methods (e.g., Hi-TRS, Hyperformer) at roughly 89–91% NTU-120 XSub. It notes that NTU-60 is near saturation while NTU-120 remains harder. (Table extraction was messy, so figures are approximate.) — [3D Skeleton-Based Action Recognition: A Review, arXiv 2506.00915](https://arxiv.org/pdf/2506.00915)
- **Pose extractors (inputs to skeleton models):**
  - RTMPose-m: 75.8% AP on COCO, 90+ FPS on an Intel i7-11700 CPU, 430+ FPS on a GTX 1660 Ti (top-down, per person). — [RTMPose, arXiv 2303.07399](https://arxiv.org/abs/2303.07399)
  - RTMO (one-stage, CVPR 2024): largest variant 74.8% AP on COCO val2017 at 141 FPS on a V100. With TensorRT FP16 it is faster than RTMPose once two or more people are in frame, which suits multi-person dining rooms. — [RTMO, arXiv 2312.07526](https://arxiv.org/html/2312.07526v2); [CVPR 2024 open access](https://openaccess.thecvf.com/content/CVPR2024/html/Lu_RTMO_Towards_High-Performance_One-Stage_Real-Time_Multi-Person_Pose_Estimation_CVPR_2024_paper.html)
  - MMPose (home of RTMPose/RTMO/RTMW/RTMW3D): Apache-2.0. Latest release shown is v1.3.0 (4 Jan 2024), with ~1,159 commits and 308 open issues. — [open-mmlab/mmpose](https://github.com/open-mmlab/mmpose)
  - Ultralytics YOLO26-pose (n/s/m/l/x, COCO-Pose 17 keypoints) ships in the `ultralytics` package. It is **dual-licensed AGPL-3.0 / commercial Enterprise**, and Ultralytics positions the Enterprise licence for commercial products. — [Ultralytics docs](https://docs.ultralytics.com/); [PyPI ultralytics](https://pypi.org/project/ultralytics); [Replicate yolo26-pose](https://replicate.com/ultralytics/yolo26-pose). A third-party write-up claims Ultralytics reads AGPL as covering internal and API deployment as well. I could not verify this against Ultralytics' own text. — [ki-syndikat.de](https://www.ki-syndikat.de/tools/yolo/)

### Inferences
- The target gestures (hand above head, waving, standing up) are coarse, high-amplitude upper-body motions, close to NTU-style classes on which GCNs exceed 90%. The hard ones are "check please" (a small hand mime) and "holding up an empty glass" (needs an object). Pure body keypoints (17 COCO joints, no fingers) cannot see the "check" mime. That needs whole-body or hand keypoints (RTMW: 133 keypoints), or an RGB/VLM verifier.
- Few-shot recipe: initialise ST-GCN++/CTR-GCN from NTU-60/120 2D-HRNet checkpoints in pyskl, then fine-tune on about 200–500 clips per class. Alternatively, skip deep models and train a 1D-CNN/GRU or gradient-boosted tree on 1–2 s windows of normalized keypoints. This is a few hours of work. PoseC3D is the most robust to noisy 2D keypoints (heatmap volumes), but training is heavier.
- Licensing for deployment: RTMPose/RTMO via MMPose (Apache-2.0), or the lightweight `rtmlib` ONNX wrappers, avoid Ultralytics' AGPL. YOLO26-pose is the fastest path in a hackathon. It is fine under AGPL for a demo but needs an Enterprise licence (or a switch) for a closed commercial product.
- Because pyskl is unmaintained, expect dependency friction (old mmcv/PyTorch). In 48 hours, a self-written PyTorch GCN/GRU over keypoints may be faster than installing pyskl.

### Gaps
- I found no published accuracy for few-shot fine-tuning on a few hundred custom clips, and no 2025–2026 benchmark of CTR-GCN/BlockGCN/ProtoGCN on small custom gesture sets. Not fetched: CTR-GCN's exact NTU numbers and per-clip GCN latency on CPU (the pyskl README only says CPU real-time for ST-GCN++).
- Whether MMAction2 and MMPose had releases after early 2024 was not confirmed.

---

## 2. Rule-based keypoint heuristics vs learned classifiers vs zero-shot VLMs; can a VLM verify a 2–3 s clip? VLM benchmarks on fine-grained action

### Takeaway
VLMs are good at coarse, web-style actions but weak at fine-grained, cross-view, compositional ones. Gemini's default video sampling is 1 FPS, and the Live API also takes 1 FPS. So a VLM should not be the always-on detector. Use it as a second-stage verifier on a candidate clip: send a few high-res frames or a short clip only when the cheap pose/rule stage fires. The best accuracy-per-latency split is rules plus a small learned classifier for triggering, and a VLM for verification and explanation.

### Cited Findings
- **ECCV-W 2024 study (Ali, Yang, Brémond), zero-shot Top-1:** on Toyota Smarthome CS, CLIP 10.1%, X-CLIP 16.5%, ViFi-CLIP 19.6%, LanguageBind 16.9%. On Penn Action, ViFi-CLIP 87.1% and LanguageBind 90.4%. On UAV-Human (aerial / oblique view), 1.2–5.9%. On an NTU-10 subset, 13.8–33.4%, rising to 42.9% for ViFi-CLIP with richer descriptions. The authors conclude that vision-language foundation models "are good with basic actions (similar to the web action classes), but struggle with fine-grained actions". Weak areas are cross-view and compositional actions. They recommend adding skeleton modality and better temporal modelling. — [arXiv 2410.17149](https://arxiv.org/html/2410.17149v1); [ECCVW 2024 entry](https://mlanthology.org/eccvw/2024/ali2024eccvw-visuallanguage)
- **FineBench (arXiv 2605.19846, May 2026):** 199,420 QA pairs over 64 long-form human-centric videos with dense spatio-temporal grounding. The best proprietary models peak at about 77% accuracy, and the largest gaps are spatial reasoning and nuanced action interpretation. The paper also proposes a modular "FineAgent" framework that improves open VLMs. (From search summary plus abstract.) — [arXiv 2605.19846](https://arxiv.org/html/2605.19846v3); [alphaXiv](https://www.alphaxiv.org/abs/2605.19846)
- **Gemini API video handling (official doc, fetched 2026-11-03):**
  - Default sampling is **1 FPS** in "static" mode, and the doc warns "fast action sequences might lose detail due to the 1 FPS sampling rate".
  - FPS can be set in a `processing` object (the doc's example is `fps: 0.5`), along with `start_offset`/`end_offset`.
  - Token cost is about 100 tokens/s of video at low media resolution (66 tokens/frame) and about 300 tokens/s at high (258 tokens/frame).
  - Inline upload is recommended under a 20 MB total request and suits videos under 1 minute. The File API handles larger files.
  - The doc lists agentic video processing for "Gemini 4 Argon, 3.8 Flash, 3.6 Flash, 3.5 Flash Lite".
  - For long requests the doc recommends streaming or background execution because of possible timeouts.
  - (The old ai.google.dev/gemini-api/docs URL now 301-redirects to aistudio.google.com/docs.) — [Gemini video understanding doc](https://aistudio.google.com/docs/video-understanding)
- **Gemini Live API (Firebase AI Logic docs):** video arrives as discrete frames at **1 FPS**, with 768×768 native resolution recommended. The docs say this makes it unsuitable for fast-changing video. Pages disagree on session limits (2 minutes for video+audio vs about 10 minutes per connection). — [Firebase Live API limits & specs](https://firebase.google.com/docs/ai-logic/live-api/limits-and-specs)
- **Gemma 4** (released 2 April 2026) is **Apache 2.0**, a change from Gemma 3's custom Gemma Terms of Use. Variants are E2B and E4B (edge), a 26B MoE and a 31B dense model. All accept images and video, and the E2B/E4B models also take native audio. One source says video input runs at up to 1 FPS for up to 60 s. Context length is reported as 128K (edge) to 256K (large), and sources conflict on this. — [Wikipedia: Gemma](https://en.wikipedia.org/wiki/Gemma_(language_model)); [Datature blog on Gemma 4 for CV engineers](https://datature.io/blog/gemma-4-what-computer-vision-engineers-actually-need-to-know); [WaveSpeed explainer](https://wavespeed.ai/blog/posts/what-is-google-gemma-4/)
- **Open VLMs on edge for video:** an ETRI paper compressed **Qwen3-VL-2B** with 4-bit quantization and TensorRT-LLM for real-time video anomaly detection. Per-segment latency fell to **0.25 s** (7.4× faster, 55% less memory than the PyTorch baseline), but accuracy was below server-side methods. — [ETRI KSP paper](https://ksp.etri.re.kr/ksp/article/file/72982.pdf). A Feb 2026 paper studies Qwen3-VL variants for on-device episodic-memory QA on an edge GPU. — [HF papers 2602.22455](https://huggingface.co/papers/2602.22455.md)

### Inferences
- **Rules** (e.g., wrist y < nose y for more than 0.8 s, wrist oscillation for waving, hip-height rise for standing) take zero training, have near-zero latency and are explainable. They are brittle to camera angle and to near-misses: stretching, touching hair, fixing glasses, a child playing. They are good as stage-1 triggers with high recall.
- **A learned classifier on keypoint windows** captures temporal shape (a wave vs a stretch) and is cheap: milliseconds per window on CPU. It needs about 100+ positive and many more hard-negative clips per class. It is the best cost-to-precision ratio for the always-on loop.
- **VLM verifier:** a 2–3 s clip at 1 FPS gives only 2–3 frames, which is fine for static poses (hand held high, glass raised, person standing and looking around) but not for motion-defined gestures (waving, the "check" mime). Better: crop the person or table region at higher resolution and send 4–8 sampled frames as images, or a short clip with a higher fps if the API allows it. Ask a constrained yes/no plus JSON question ("Is the seated customer at table 5 trying to get a server's attention? answer yes/no + which gesture"). Cost at about 100–300 tokens per second of video, or per frame as images, is small if it is called only on triggers.
- **Latency:** a Gemini Flash-class call is likely about 1–3 s round trip (not measured here). That fits a "seconds, not 5 minutes" requirement only when used as a verifier. Gemma 4 E4B or Qwen3-VL-2B/4B on a local GPU box can verify on-premise with no cloud cost or privacy exposure, and Gemma 4's Apache-2.0 licence makes it deployable commercially.
- VLMs are weakest at exactly what UAV-Human (overhead, small, oblique people) represents, scoring under 6% zero-shot. Ceiling CCTV is a similar regime, so crop and upscale before asking a VLM.

### Gaps
- No benchmark found for VLM *verification* of short clips (binary "is this a hand raise?") on CCTV footage, and no measured Gemini or Gemma 4 latency numbers for 2–3 s clips.
- Not confirmed: whether the current Gemini API allows fps above 1 (the doc example only shows 0.5), and Gemma 4 video benchmarks on action recognition (MVBench-style scores).
- Not covered: PaliGemma 2, InternVL3, SmolVLM2 on fine-grained action. No primary numbers fetched.

---

## 3. Google MediaPipe (Gesture Recognizer, Pose Landmarker, Holistic, Face Landmarker): suitability for far-field ceiling CCTV; current naming

### Takeaway
MediaPipe Tasks are built for near-field, selfie/webcam-scale subjects. The models are tiny (pose landmarker input 256×256, gesture classifier input 192/224), default to one person or one hand, and the docs give no far-field guarantees. For a ceiling camera with small, oblique, table-occluded people, use a multi-person detector or pose model on the full frame (RTMO, YOLO26-pose, RTMPose). Then run MediaPipe Pose/Hands only on upscaled per-person crops if finger-level detail is needed. Docs have moved from ai.google.dev/edge to developers.google.com/edge.

### Cited Findings
- **Pose Landmarker:** Lite, Full and Heavy float16 bundles, 33 3D landmarks plus world coordinates and an optional segmentation mask. Pose detector input is 224×224 and landmarker input is 256×256. `num_poses` defaults to 1. Running modes are IMAGE, VIDEO and LIVE_STREAM (async `result_callback`). **No guidance on camera distance or small or far people**, and no latency table on the page. Model card: BlazePose GHUM 3D. — [MediaPipe Pose Landmarker guide](https://developers.google.com/edge/mediapipe/solutions/vision/pose_landmarker)
- **Gesture Recognizer canned gestures:** None, Closed_Fist, Open_Palm, Pointing_Up, Thumb_Down, Thumb_Up, Victory, ILoveYou. `num_hands` defaults to 1, and the classifier input is 192×192 or 224×224. Whole-pipeline latency on a Pixel 6 is 16.76 ms on CPU and 20.87 ms on GPU. Custom gestures are trained via Model Maker into a `.task` bundle. No range limits or small-hand notes. — [MediaPipe Gesture Recognizer guide](https://developers.google.com/edge/mediapipe/solutions/vision/gesture_recognizer)
- **Naming / status:** fetching ai.google.dev/edge/mediapipe/... returned a 301 to developers.google.com/edge/mediapipe/... The pages call these "MediaPipe ... task" and do not mention LiteRT on the Pose page. — [redirect observed; Pose Landmarker page](https://developers.google.com/edge/mediapipe/solutions/vision/pose_landmarker)
- **Crowded scenes:** the SCB classroom-dataset authors argue that pose-estimation-based behaviour algorithms are "not applicable for behavior detection in overcrowded classrooms". They use direct bounding-box detection of the behaviour instead. — [SCB-Dataset3, arXiv 2310.02522](https://arxiv.org/pdf/2310.02522)

### Inferences
- "Open_Palm" and "Pointing_Up" are the closest canned gestures to "raise hand". On a 1080p ceiling camera, a hand 4–6 m away is a few dozen pixels, below what the palm detector was designed for. Expect poor recall unless you crop and upscale. Treat MediaPipe Gesture Recognizer as a near-camera demo tool, for example a webcam on the demo table.
- The two-stage pattern is: full-frame person detection and pose (multi-person), then per-person crop, then MediaPipe Hands/Pose for fine detail. This is standard practice and keeps the Google stack in the loop.
- Holistic and Face Landmarker (478 face landmarks) need frontal, reasonably large faces. From a ceiling angle, head yaw from body keypoints (nose, eyes, ears) or a head-pose net on crops is more reliable.

### Gaps
- No official far-field or minimum-pixel-height spec exists for MediaPipe models. Not fetched: Holistic or Face Landmarker pages, or the current LiteRT/MediaPipe roadmap (whether legacy Holistic moved to Tasks).
- No published evaluation of MediaPipe on overhead CCTV found.

---

## 4. Head pose and gaze from CCTV (6DRepNet, L2CS-Net, Gaze360, recent models): can "looking around for a waiter" be detected? Research on help-seeking / waiting-for-service behaviour

### Takeaway
Exact gaze from ceiling CCTV is unrealistic: eyes are a few pixels. Coarse head orientation (yaw bins) is feasible with full-range head-pose models (6DRepNet360) or from body and face keypoints. "Searching for a waiter" is best modelled as a temporal pattern: high head-yaw variance or repeated sweeps over 3–5 s while seated with no food interaction, optionally oriented toward the service area. There is little academic work on exactly this. The closest evidence is retail patents that use head movement toward an attendant plus pose to flag customers needing help.

### Cited Findings
- **Gaze-LLE (CVPR 2025):** gaze-target estimation with a frozen DINOv2 encoder plus a light decoder with person-specific positional prompts. Reported SOTA on GazeFollow, VideoAttentionTarget and ChildPlay. Code at github.com/fkryan/gazelle. — [CVPR 2025 open access](https://openaccess.thecvf.com/content/CVPR2025/html/Ryan_Gaze-LLE_Gaze_Target_Estimation_via_Large-Scale_Learned_Encoders_CVPR_2025_paper.html); [arXiv 2412.09586](https://arxiv.org/abs/2412.09586v2)
- **6DRepNet:** 3.61° MAE on AFLW2000. **6DRepNet360** is trained on CMU Panoptic plus 300W-LP to cover full-range rotation, which matters when faces point away from the camera. (From search summaries.) — [6DRepNet360 overview, arXiv 2309.07654](https://www.alphaxiv.org/overview/2309.07654); [arXiv 2309.07654 PDF](https://arxiv.org/pdf/2309.07654v1.pdf)
- **L2CS-Net:** 3.92° gaze error on MPIIGaze and 10.41° on Gaze360. — [Papers with Code: L2CS-Net](https://astro.paperswithcode.com/paper/l2cs-net-fine-grained-gaze-estimation-in)
- **Low-resolution surveillance:** older work notes that surveillance heads are so small that head pose is "often estimated in coarse discrete directional bins of the azimuthal angle". — [SciTePress 2016 paper](https://www.scitepress.org/Papers/2016/57869/57869.pdf). A 2026 Sensors paper notes keypoint-based head-pose methods accumulate error under occlusion, low resolution and large rotations. — [MDPI Sensors 26(10):3266](https://www.mdpi.com/1424-8220/26/10/3266/htm)
- **Help-seeking in retail:**
  - A family of US patents on retail notification systems describes detecting customers who need help at self-checkout from repeated scan attempts, **head movements directed toward the attendant**, and pose-based frustration estimation. It uses a distress watch list and a **two-stage alert validation before notifying staff**. — [USPTO 10592944](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10592944) (related: [11257135](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11257135))
  - Another patent treats wandering within one zone as a sign a shopper is looking for a product or staff. — [USPTO 9472074](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/9472074)
- **Business value evidence:** Musalem, Olivares and Schilkrut (MSOM) used in-store video to measure assistance. Assistance while browsing or trying on accounts for about half of a staffing-driven sales lift, and it has a significant positive effect on conversion and ticket size. — [INFORMS MSOM](https://pubsonline.informs.org/doi/10.1287/msom.2020.0865)

### Inferences
- **Practical "looking around" detector:** per tracked seated person, estimate coarse yaw each frame. Use the nose/eye/ear keypoint geometry from the pose model (free), or 6DRepNet360 on upscaled head crops (better for oblique views). Flag "searching" when yaw range exceeds about 90° with two or more direction reversals within about 4 s, the person is not eating (hands away from mouth and plate), and no staff member is within N metres. Optionally require yaw toward the counter or kitchen. Gaze-LLE-style gaze-target models could check "looking at a staff member", but need face-visible crops and a GPU.
- This behaviour is inherently ambiguous: people look around while chatting or people-watching. It should be a **low-weight signal** that raises priority when combined with a gesture or a long wait since last service, rather than a standalone alert. That is consistent with the two-stage validation used in the retail patents.

### Gaps
- No peer-reviewed paper found on "searching for a waiter" or "waiting for service" detection in restaurants or airports. No benchmark of 6DRepNet/L2CS on overhead CCTV crops. Licences for 6DRepNet, L2CS-Net and Gaze-LLE repos were not verified.

---

## 5. Multi-signal fusion to cut false positives; published restaurant / retail call-for-service systems (papers, startups, demos)

### Takeaway
I found no published, evaluated vision system specifically for restaurant "call for service" gestures. Existing work is either table-occupancy and waiter-visit analytics from CCTV (open-source demos), button/IoT waiter-call systems, or retail patents. Robust designs share a staged, persistence-gated, context-aware pipeline.

### Cited Findings
- **Open-source restaurant CCTV demo:** "ai-restaurant-cctv-monitoring" uses YOLO plus ByteTrack and spatio-temporal behavioural inference to track table occupancy, customer dwell time and waiter visits. It tracks service rather than customer gestures. — [GitHub anuj1611/ai-restaurant-cctv-monitoring](https://github.com/anuj1611/ai-restaurant-cctv-monitoring)
- **Non-vision baseline:** IoT sit-in restaurant waiter-alert systems use buttons and Bluetooth, which is the incumbent that Easy FnB replaces. — [ResearchGate: IoT-Based Sit-in Restaurant Waiter Alert Systems](https://www.researchgate.net/publication/376748707_IoT-Based_Sit-in_Restaurant_Waiter_Alert_Systems)
- **Waiter-robot literature** notes that existing service robots cannot find waving customers, so recognising beckoning customers is an open problem there too. — [Autonomous Waiter Robot System (ResearchGate)](https://www.researchgate.net/publication/378949615_Autonomous_Waiter_Robot_System_for_Recognizing_Customers_Taking_Orders_and_Serving_Food)
- **CCTV hand-gesture recognition for security alerts** (IEEE Access 12:84548–84555, 2024, DOI 10.1109/ACCESS.2024.3412930) shows the gesture-from-CCTV pattern in another domain. — [ResearchGate](https://www.researchgate.net/publication/381367221_Real-Time_Security_Risk_Assessment_From_CCTV_Using_Hand_Gesture_Recognition)
- **Retail two-stage validation:** the notification-system patents validate an alert in a second stage before notifying staff, and combine head direction toward the attendant with pose. — [USPTO 10592944](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10592944)

### Inferences (recommended fusion design)
1. **Track first:** person detection, multi-object tracking (ByteTrack/BoT-SORT) and per-person pose. Assign each track to a table via a static table polygon map drawn once per camera. Classify staff and customer tracks. A uniform-colour classifier or "track enters kitchen/counter zone" heuristic is easiest; a small re-ID or uniform classifier is optional.
2. **Per-signal detectors with persistence:**
   - hand-up: wrist above shoulder or nose for 0.8 s or more, in at least about 70% of frames in the window
   - wave: lateral wrist oscillation, two or more cycles within 1.5 s
   - standing: hip-keypoint rise relative to the seated baseline for 1 s or more, while still in the table zone (not walking away)
   - looking-around: yaw-variance rule as in §4
   - glass-up: hand above shoulder plus a cup or glass box from the detector (COCO has "cup" and "wine glass") overlapping the wrist
3. **Temporal smoothing:** an EMA or majority vote over per-frame scores, plus hysteresis (trigger at high, release at low) and a per-table cooldown (e.g., 60 s after an alert, or until a staff track enters the table zone).
4. **Context gating and suppression:**
   - suppress when a staff track is within the table zone or approaching (distance decreasing)
   - suppress during the first N seconds after food delivery, or while the person is mid-eating motion
   - boost priority by time since last staff visit
   - whole-table aggregation, so one alert per table and no duplicate alerts per person
5. **Stage-2 verifier (optional):** on trigger, send a person or table crop sequence to Gemini Flash, or to local Gemma 4 E4B / Qwen3-VL. Ask a constrained yes/no question, then push to the staff app with a snapshot so the server sees *why*.
6. **Human-in-the-loop:** staff "acknowledge / false alarm" buttons provide labels for continual improvement. This feedback loop also serves as the evaluation metric in the pilot.

### Gaps
- No startup or case study with published precision/recall for restaurant gesture-based service calls was found. The search did not surface named commercial products; the Vietnam market was not specifically searched.

---

## 6. Datasets for pre-training / evaluation

### Takeaway
Classroom hand-raising datasets (SCB family) are the closest public analog: overhead-ish, crowded, seated people raising hands, with bounding-box labels only. Skeleton pre-training should use NTU RGB+D 60/120 2D-HRNet skeletons, which pyskl distributes. A restaurant-specific set must be self-recorded.

### Cited Findings
- **SCB-dataset (arXiv 2304.02488):** 4,003 images, 11,248 labels, focused on hand-raising from real classroom monitoring. YOLOv7 reaches up to 85.3% mAP. Download via the Whiffe/SCB-dataset GitHub. — [arXiv 2304.02488](https://arxiv.org/abs/2304.02488v3)
- **SCB-Dataset3 (arXiv 2310.02522):** 5,686 images, 45,578 labels, six behaviours (hand-raising, reading, writing, using phone, bowing head, leaning over table). YOLOv5/v7/v8 reach up to 80.3% mAP. — [arXiv 2310.02522](https://arxiv.org/pdf/2310.02522); [HF papers](https://huggingface.co/papers/2310.02522)
- Earlier SCB version: 4.2k images, 18.4k labels, three behaviours (hand-raising, reading, writing), improved YOLOv7. — [arXiv 2306.03318](https://arxiv.org/html/2306.03318v2)
- SCB labels are boxes, and **no keypoint annotations** were found for these datasets. Some related classroom datasets (e.g., ActRec-Classroom, 5,126 images) are not public. — [arXiv 2305.07825](https://arxiv.org/html/2305.07825v2)
- **NTU RGB+D 60/120:** pyskl provides pre-processed HRNet 2D skeletons for all supported datasets (and Kinect 3D for NTU). — [pyskl GitHub](https://github.com/kennymckormick/pyskl)
- **Overhead / oblique evaluation:** UAV-Human is the dataset on which zero-shot VLMs scored only 1.2–5.9%, making it a stress test for the CCTV-like viewpoint. — [arXiv 2410.17149](https://arxiv.org/html/2410.17149v1)
- **Fine-grained human-activity QA for VLMs:** FineBench (2026). — [arXiv 2605.19846](https://arxiv.org/html/2605.19846v3)

### Inferences
- NTU-60 includes classes such as "hand waving", "pointing to something with finger", "standing up" and "sitting down", and NTU-120 adds more hand gestures. (From background knowledge; verify against the NTU class list.) A model pre-trained on NTU then fine-tuned should transfer for wave, stand-up and point.
- SCB hand-raising images can fine-tune a **YOLO detector for a "hand-raised person" class** directly, a bypass of pose that works in crowded, occluded scenes. This is a useful parallel baseline to the pose pipeline.
- Eating and dining datasets (e.g., EPIC-Kitchens, or meal-intake datasets) were not researched here. They are useful mainly as hard negatives ("eating ≠ calling").

### Gaps
- Not verified: NTU class IDs and names, the Kinetics-400/700 "waving hand"-type classes, and the existence of a public restaurant or dining CCTV dataset with service-request labels (none found).
- The SCB dataset licence was not checked.

---

## 7. Recommended 48-hour plan (out of the box vs fine-tune, data volume, evaluation)

### Takeaway
Ship a **two-stage, track-centric pipeline**:
- **Stage 1 (always-on, edge):** YOLO26-pose or RTMO plus ByteTrack plus table-zone mapping plus rule and persistence detectors for hand-up, wave and stand.
- **Stage 1b:** a tiny learned keypoint-window classifier trained on self-recorded clips to cut false positives.
- **Stage 2 (on trigger):** a Gemini Flash or Gemma 4 verifier on a cropped multi-frame snippet that returns gesture type plus confidence.

Measure precision/recall per event and time-to-alert on a held-out recorded session.

### Cited Findings (supporting facts)
- RTMPose-m runs 90+ FPS on a desktop CPU, so per-person pose on a CPU edge box is feasible. RTMO is faster for multi-person scenes with TensorRT FP16. — [arXiv 2303.07399](https://arxiv.org/abs/2303.07399); [arXiv 2312.07526](https://arxiv.org/html/2312.07526v2)
- YOLO26-pose n–x weights are available via `pip install ultralytics` under AGPL-3.0 / Enterprise. — [Ultralytics docs](https://docs.ultralytics.com/); [PyPI](https://pypi.org/project/ultralytics)
- pyskl has a ready CPU real-time ST-GCN++ gesture demo and HRNet skeleton-extraction scripts (Apache-2.0, unmaintained). — [pyskl](https://github.com/kennymckormick/pyskl)
- Gemini's 1 FPS default sampling (configurable via `processing.fps`), about 100–300 tokens per second of video, and inline upload under 20 MB suit short verifier clips. — [Gemini video doc](https://aistudio.google.com/docs/video-understanding)
- Gemma 4 E2B/E4B are Apache-2.0 open weights with video input, for an on-prem verifier. — [Wikipedia: Gemma](https://en.wikipedia.org/wiki/Gemma_(language_model))
- MediaPipe Gesture Recognizer supports custom gestures via Model Maker and runs about 17–21 ms per frame on a Pixel 6, but is designed for near-field hands. — [MediaPipe Gesture Recognizer](https://developers.google.com/edge/mediapipe/solutions/vision/gesture_recognizer)

### Inferences (concrete plan)

**Hours 0–6: setup and data.** Mount one camera (or a phone on a tripod at about 2.5–3 m height, angled down) over 2–3 tables in a mock restaurant. Draw table polygons. Record scripted sessions: 4 people × multiple seats × each gesture class (hand-up, wave, check-please mime, glass-up, stand-up, look-around). Aim for about **30–60 positive clips per class per camera view (about 150–300 total)**. Record at least 2–3× as many **hard negatives**: eating, drinking, stretching, phone use, touching hair or face, pointing at a menu, toasting with glasses, chatting with hand gestures. Hard negatives drive precision.

**Hours 6–18: Stage 1.**
- YOLO26-pose (or RTMO via rtmlib/ONNX for licence-clean) plus ByteTrack at 10–15 FPS.
- Assign tracks to tables.
- Implement rule detectors with persistence (hand-up ≥0.8 s, wave ≥2 oscillations, stand ≥1 s), hysteresis, per-table cooldown, and staff-nearby suppression (staff = tracks crossing the counter zone, or a uniform colour).

**Hours 18–30: Stage 1b and the learned classifier.**
- Extract 1.5–2 s keypoint windows (normalized to the torso), then train a GRU/1D-CNN or LightGBM.
- If time allows, fine-tune ST-GCN++ from NTU weights in pyskl.
- Fine-tune a YOLO "hand-raised" detector on SCB-dataset plus your own frames as a second opinion.

**Hours 24–36: Stage 2 verifier.** On trigger, crop the person/table at up to 768 px, take 4–6 frames over the last 2–3 s, and call Gemini Flash (fastest to integrate, Google-preferred) with a strict JSON schema prompt. A Gemma 4 E4B local fallback works via Ollama, llama.cpp or vLLM if a GPU is available. Use it for the "check please", glass-up and look-around classes, where keypoints are insufficient.

**Hours 30–42: app integration.** Push alerts (table #, gesture type, snapshot, timestamp) to a staff web/mobile app (e.g., Firebase) with Acknowledge / False-alarm buttons.

**Hours 42–48: evaluation and demo.** Hold out one recorded session (different people or seat positions). Report:
- per-class precision, recall and F1 at the event level (an alert within ±2 s of the ground-truth start counts as TP)
- **false alarms per table-hour** on a long "normal dining" negative recording (e.g., 20–30 min)
- **median time-to-alert**, from gesture start to notification; stage 1 should be about 1–1.5 s, plus about 1–3 s if the verifier is used
- an ablation: rules only vs +classifier vs +VLM verifier

**What to use out of the box vs fine-tune:**
- Out of the box: pose model, tracker, COCO cup/glass detection, Gemini/Gemma verifier.
- Fine-tune: the keypoint-window classifier (must), and optionally the YOLO hand-raised detector on SCB plus your own data.
- Skip: training PoseC3D from scratch, gaze models (use keypoint yaw instead), MediaPipe on full-frame CCTV.

**Deployment path:**
- Edge box (Jetson Orin / x86 plus a small GPU) runs stage 1 at under 50 ms/frame.
- Stage 2 runs on cloud Gemini or local Gemma 4 depending on privacy and cost.
- Swap Ultralytics for MMPose RTMO/RTMPose (Apache-2.0) if commercial and closed-source.

### Gaps
- None of the timings above (Gemini round-trip latency, Jetson FPS for YOLO26-pose/RTMO) were measured or sourced here. They are engineering estimates to validate during the build.
- Data-volume recommendations are heuristic. No source gives a sample-size curve for few-shot skeleton gesture fine-tuning.
- Vietnam-specific considerations (Decree 13/2023 on personal data and camera use, which the team should check) were outside this research scope.
