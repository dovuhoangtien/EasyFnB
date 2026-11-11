# Privacy-preserving people analytics on old cameras and cheap hardware: edge processing, anonymisation and non-camera sensors (analogues for Easy FnB)

Scope note: research done 5 Nov 2026. Sources are labelled as **[vendor]**, **[community]**, **[independent/academic]** or **[legal/primary]**. Numbers from vendors were not checked independently unless stated. About 35 searches and fetches were made, so some subtopics have gaps, listed in each Gaps section.

---

## Q1. Edge video analytics on cheap hardware (2023–2026): runtimes, accelerators, real throughput, reference architectures

### Takeaway
NVR and smart-building systems that run in production (Frigate is the clearest open-source reference) all use the same pattern. They decode the camera **sub-stream**, run a very cheap **motion detector** first, and send only the moving regions to a small detector at about **5 fps**. The detector runs on an iGPU, NPU or small accelerator (Intel OpenVINO iGPU/NPU, Hailo-8/8L, RK3588 NPU), not on the plain CPU. With that design, one cheap box handles several 1080p cameras. Measured numbers below suggest a YOLO26n/YOLOv9-t-class model costs about 6–15 ms per inference on Intel iGPU/NPU or Hailo, about 9 ms with OpenVINO FP32 (about 6 ms INT8) on a Core Ultra laptop, and about 4–5 ms on a Jetson Orin Nano Super with TensorRT.

### Cited Findings
**Reference architecture (Frigate NVR, open source, MIT)**
- Frigate uses "very low overhead motion detection to determine where to run object detection", so it runs the detector only on regions with motion. — [Frigate README (mirror)](https://github.com/tleyden/frigate) **[community/primary code]**
- In Frigate, motion detection is a "first line check" that decides whether object detection runs. It groups changed pixels into motion boxes. Tunables: `threshold` (default 30, luminance change), `contour_area` (default 10; 10 = high, 30 = medium, 50 = low sensitivity), `lightning_threshold` (default 0.8, the share of the frame that can change before motion recalibrates, used for **IR day/night switches**) and `skip_motion_threshold`. The docs advise separate day and night motion settings. — [Frigate docs: Motion detection](https://docs.frigate.video/configuration/motion_detection) **[primary docs]**
- Frigate hardware guidance: Hailo-8/8L uses YOLOv6n by default. **Google Coral is "no longer recommended for new installs"** except for very low-power cases. OpenVINO runs on Intel iGPU, Arc and NPU. OpenVINO on x86/Arm **CPUs is "generally not recommended"**, and a dedicated detector "greatly reduces CPU load". — [Frigate docs: Hardware](https://docs.frigate.video/frigate/hardware) **[primary docs, community-measured numbers]**
- Frigate inference-time table (approximate, community-reported):
  - Intel N100: ~15 ms (YOLOv9 s-320: 30 ms; "one detector instance only")
  - N150: ~15 ms (s-320: 24 ms)
  - UHD 770: ~15 ms (s-320 ~20 ms, s-640 ~40 ms)
  - Iris Xe: ~10 ms (s-320 8 ms, s-640 16 ms)
  - **Intel NPU: ~6 ms (s-320 11 ms, s-640 30 ms)**
  - Arc A380: ~6 ms
  - **Hailo-8: ~7 ms (YOLOv6n); Hailo-8L: ~11 ms; YOLOv9-tiny-320 18 ms**
  - **RTX 3050: YOLOv9 t-320 8 ms, s-320 10 ms, s-640 28 ms**
  - **RK3588 (3 NPU cores): YOLOv9-tiny ~35 ms, YOLO-NAS-small ~20 ms (typically 25–30 ms), YOLOX-nano 14 ms**
  - RK3566 YOLO-NAS-small ~96 ms

  — [Frigate docs: Hardware](https://docs.frigate.video/frigate/hardware)
- Frigate says detectors do **not** decode video, so hardware-accelerated decoding (hwaccel) is needed even with an accelerator. Higher resolution and fps mean more decoding work, so lower them **on the camera**. Cameras with several sub-streams let you use different resolutions for detection, live view and recording without re-encoding. H.264 gives the best compatibility. — [Frigate docs: Hardware](https://docs.frigate.video/frigate/hardware)
- Community guidance: use the **sub-stream for detect and the main stream for record**. Detection works best at **≤720p and about 5 fps** (5–10 fps is reasonable). — [Frigate configurator guide (third-party)](https://smithery.ai/skills/nodnarbnitram/frigate-configurator) **[community]**
- Sizing rule of thumb: cameras per detector ≈ (1000 / inference_ms) / detect_fps, derated by about 25%. Example: 15 ms at 5 fps gives about 13 cameras, or about 10 after derating. The iGPU is shared with decoding, which reduces headroom. — [hometechops: Coral vs Hailo vs Intel NPU](https://hometechops.com/cameras/coral-vs-hailo-vs-intel-npu) **[community]**
- Coral status: Frigate keeps supporting Coral, but it is no longer the first recommendation because its upstream drivers and runtime are unmaintained and the PCIe driver does not build cleanly on new kernels. Hailo is the usual replacement. One blog says the driver was archived in April 2026 (**unconfirmed**). — [computingforgeeks: Hailo vs Coral for Frigate](https://computingforgeeks.com/hailo-vs-coral-frigate-object-detection/); [aicybr Frigate hardware guide](https://aicybr.com/blog/frigate-nvr-hardware-accelerator-guide) **[community]**

**Intel CPU/iGPU with OpenVINO (Ultralytics, YOLO26)**
- Ultralytics benchmark on an **Intel Core Ultra 7 155H** (Meteor Lake, integrated Arc GPU), openvino 2026.2.1, COCO:
  - YOLO26n: PyTorch CPU 33.19 ms/img; OpenVINO FP32 9.13 ms (mAP50-95 0.4758); FP16 9.07 ms; **INT8 5.79 ms (mAP 0.4573)**
  - YOLO26s: PyTorch 70.92 ms; OpenVINO FP32 16.37 ms (mAP 0.5616); **INT8 9.27 ms (mAP 0.5450)**
  - FPS = 1000/ms, derived by me. The fetched page did not clearly say whether the OpenVINO rows ran on CPU or iGPU. No NPU rows were reported.

  — [Ultralytics docs: OpenVINO integration](https://docs.ultralytics.com/integrations/openvino) **[vendor]**
- Ultralytics v8.3.153 release notes mention benchmark tables for YOLO11 across CPU, GPU and NPU (FP32/INT8) on a Core Ultra 7 265K. The numbers were not retrieved. — [Ultralytics community release notes](https://community.ultralytics.com/t/new-release-ultralytics-v8-3-153/1133) **[vendor]**
- An Intel N100 runs YOLO11 about "7x" faster with OpenVINO (LattePanda Mu tutorial). Only the headline was retrieved. — [DigiKey/Maker.io: YOLO11 7x with OpenVINO on LattePanda Mu](https://www.digikey.com/en/maker/tutorials/2025/yolo11-speed-boosted-by-7x-with-openvino-on-lattepanda-mu) **[community]**

**Hailo (Raspberry Pi ecosystem)**
- Hailo-8L (13 TOPS) on a Seeed reComputer R1000 (CM4): **YOLOv8-pose 640×640 ≈ 27 FPS vs ≈ 0.5 FPS on CPU**, and YOLOv8 detection 29.5 FPS vs 0.75 FPS. — [Seeed wiki: YOLOv8 pose on Hailo-8L](https://wiki.seeedstudio.com/yolov8_pose_estimation_on_recomputer_r1000_with_hailo_8l/); [Seeed wiki: YOLOv8 detection on Hailo-8L](https://wiki.seeedstudio.com/yolov8_object_detection_on_recomputer_r1000_with_hailo_8l/) **[vendor/reseller]**
- **Raspberry Pi AI HAT+ 2** (launched Jan 2026): **Hailo-10H, 40 TOPS, 8 GB LPDDR4X, about US$130**. Reported speeds are >60 FPS YOLOv8m and 30–40 FPS YOLOv8l; a Pi 5 CPU alone does about 5–8 FPS on YOLOv8n. The blog's tables are partly inconsistent. — [raspberry.tips: AI HAT+ 2 with Hailo-10H](https://raspberry.tips/en/raspberrypi-tutorials/raspberry-pi-ai-hat-2-hailo-10h-40-tops-llm) **[community/secondary]**

**Rockchip RK3588 NPU (6 TOPS, 3 cores)**
- Radxa ROCK 5B+ demo: **9 streams** (local video files, not RTSP), YOLOv8n INT8 on all 3 NPU cores, **25.8 ms average NPU inference and 47.1 ms total per frame**. No aggregate FPS was given. — [Radxa docs: YOLOv8 multi-stream](https://docs.radxa.com/en/rock5/rock5b/app-development/ai/yolov8-multi-stream) **[vendor]**
- Khadas Edge2 (RK3588S), YOLOv8n 640: **~31 FPS single-threaded, ~46 FPS using 3 NPU cores in parallel**. The camera was the limit at that point. — [alebal123bal/khadas_yolov8n_multithread (via reader proxy)](https://hn.jakechampion.name/reader/https://github.com/alebal123bal/khadas_yolov8n_multithread) **[community]**

**NVIDIA Jetson Orin Nano Super**
- YOLOv8n 640, batch 1, MAXN_SUPER: **TensorRT FP16 4.43 ms (225 FPS), INT8 286 FPS, PyTorch FP32 47.9 FPS**. — [hokwangchoi/jetson-orin-nano-benchmarks](https://github.com/hokwangchoi/jetson-orin-nano-benchmarks) **[community]**
- YOLO11 TensorRT FP16 is about 4.91 ms on Orin Nano vs 4.85 ms on Orin NX 16GB; the exact variant and power mode were unclear. — [CamThink NeoEdge wiki](https://camthink-ai.github.io/wiki-documents/en/docs/NeoEdge%20NG4500%20Series/Application%20Guide/Object%20Detection) **[vendor]**
- Ultralytics says the Orin Nano Super gives YOLO11 inference times "comparable with, and occasionally better than" an Orin NX 16GB (non-super). — [Ultralytics blog](https://www.ultralytics.com/blog/ultralytics-yolo11-on-nvidia-jetson-orin-nano-super-fast-and-efficient) **[vendor]**

### Inferences
- **Easy FnB's current RTX 3050 laptop is already more than enough.** Frigate's community numbers put an RTX 3050 at about 8–10 ms for a tiny/small model at 320. TensorRT FP16 YOLO26n-pose plus YOLO26s on one GPU should handle several cameras at 5 fps. The bottleneck on a laptop is more likely **decoding (NVDEC/QuickSync must be used)** and Python glue code than inference.
- **CPU-only shop PCs:** the Ultralytics Core Ultra numbers (YOLO26n OpenVINO INT8 ≈ 6 ms, YOLO26s INT8 ≈ 9 ms) come from a 2023/2024 laptop chip. Typical Vietnamese office PCs (older Core i3/i5 or Celeron/N100) will be several times slower; the Frigate N100 entry is about 15 ms for a tiny model on the iGPU. Combining **imgsz 320–416, INT8, iGPU (OpenVINO "GPU" device) instead of CPU, 2–5 fps per camera and motion/zone gating** should make 2–4 cameras feasible on such a PC. That is an estimate and has to be measured on the actual hardware.
- The **YOLO26s detect model is the expensive part**. The analogue from other fields is a cascade: run pose or person detection only when the cheap motion detector fires in a table or entrance zone, and run "leftover item" detection on table ROIs at very low frequency (for example once every 5–10 s, or only after a "guests left" event). Table state changes slowly, so it does not need 4 fps.
- If buying hardware later: **Hailo-8L/Hailo-10H (Pi 5 or M.2 in a mini-PC)** or an **Intel N100/N150/Core Ultra mini-PC with OpenVINO iGPU/NPU** are the mainstream 2025–2026 choices in the Frigate community. Coral should be avoided because of its maintenance status. RK3588 boards are the cheapest per TOPS, but toolchain friction is higher (RKNN conversion, INT8 quantisation, pose model support).

### Gaps
- No independent multi-stream RTSP benchmark (decode plus inference end-to-end) was found for RK3588, Hailo or Intel N100 with **pose** models. All numbers are per-inference or single-stream.
- Exact YOLO11/YOLO26 **NPU** numbers on Intel Core Ultra were not retrieved.
- NVIDIA DeepStream, Intel DL Streamer, Savant, Viseron and Scrypted were not researched in detail; Frigate was used as the reference architecture. Their multi-stream batching numbers are a gap.
- **Laptop thermal throttling** of an RTX 3050 4GB under sustained load: no source found.
- The cost of decoding H.265 versus H.264 on CPU (per stream) was not quantified by any source found.

---

## Q2. Working with old CCTV (DVR/NVR RTSP, sub-streams, low resolution, IR night mode)

### Takeaway
The proven tricks are: pull the DVR/NVR **sub-stream** (low resolution, low fps) for analytics and the main stream only when a high-resolution crop is needed; use hardware decoding; set resolution and fps on the camera or DVR rather than resizing in software; and handle **IR day/night switching** as a motion-recalibration event with separate day and night thresholds.

### Cited Findings
- Sub-streams let you use different resolutions for detection, live view and recording without re-encoding. Lower resolution and fps at the camera reduce decode load. H.264 is the most compatible codec. Hardware acceleration is needed because detectors don't decode video. — [Frigate docs: Hardware](https://docs.frigate.video/frigate/hardware)
- Detect at ≤720p and about 5 fps; give the detect role to the sub-stream and the record role to the main stream. — [Frigate configurator guide](https://smithery.ai/skills/nodnarbnitram/frigate-configurator) **[community]**
- IR/colour mode switches trigger whole-frame "motion". Frigate's `lightning_threshold` (default 0.8) and `skip_motion_threshold` deal with this, and the docs recommend automating separate day and night motion settings. — [Frigate docs: Motion detection](https://docs.frigate.video/configuration/motion_detection)

### Inferences
- For Easy FnB, typical Vietnamese DVRs (Hikvision, Dahua, KBVision and similar) expose a main stream and a sub-stream over RTSP. Running pose and detect on the sub-stream (often D1/640×480 or 720p) and fetching a **single high-resolution frame from the main stream only when an event fires** mirrors Frigate's detect/record split. It would also cut decode cost several-fold on a CPU-only PC.
- Night or IR scenes are grayscale. Staff-vs-customer classification by uniform colour will degrade at night, so it should fall back to track-based or zone-based rules.

### Gaps
- No source was found quantifying detection accuracy loss on D1/720p sub-streams for small or occluded people at oblique ceiling angles.
- Fisheye dewarping practices of retail vendors were not researched.

---

## Q3. Privacy-preserving analytics: metadata-only products, on-device anonymisation tools and licences, and whether anonymisation hurts accuracy

### Takeaway
Privacy-by-design people analytics (Xovis, Butlr, Density) all process on the device and **export only metadata**: counts, positions or tracks, never video. Face anonymisation can be done cheaply on the edge. Academic results (2023) show that **face-only blurring barely hurts pose estimation**, while full-body blurring hurts a lot. Realistic generative anonymisation (DeepPrivacy2) helps but is heavy. For VLMs, blurring hurts questions that depend on the face or identity. No study was found on whether it hurts gesture or table questions.

### Cited Findings
**Metadata-only commercial analogues**
- **Xovis** (airports, retail): 3D stereo sensors process images on the device and output metadata only. The PC series supports up to **four privacy levels**, and a "Pixel Lock" filter makes people visible but not recognisable. Accuracy claims: "98% of all passengers… registered" (2018 article) and ">99%" (reseller), neither independently validated. Mounting height is up to 6 m. — [Passenger Terminal Today (2018)](https://passengerterminaltoday.com/?p=7177); [Manx Tech Group (reseller)](https://www.manxtechgroup.com/?p=9674); [Bumbee Labs on Xovis](https://bumbeelabs.com/solutions/xovis-people-counting-analytics/) **[vendor/reseller]**
- **Butlr** (offices, senior living): low-resolution non-RGB **thermal** sensors (Heatic 2 / 2+, which won a Fast Company 2025 Innovation by Design award). The vendor says this removes privacy concerns at the hardware level. **No accuracy figures are published**; buyers are told to validate against ground truth. Pricing is "custom". The vendor claims total cost of ownership 3–5x below alternatives, which has not been independently checked. — [Butlr: camera-free occupancy sensing 2025](https://www.butlr.com/articles/smart-building-technology-camera-free-occupancy-sensing-2025); [Butlr: Heatic 2+ award](https://www.butlr.com/articles/butlr-occupancy-sensing-privacy-first-smart-buildings-2025); [softwarefinder: Butlr pricing](https://softwarefinder.com/artificial-intelligence/butlr) **[vendor]**
- **Density**: the Open Area sensor uses in-house **radar** ("no cameras… no personally identifiable information"); the Entry sensor uses an infrared laser for depth. The vendor claims "near-perfect accuracy", with no independent test found. — [Density support](https://support.density.io/hc/en-us/articles/1260804189489); [Density: how accurate are occupancy sensors](https://density.io/guides/how-accurate-are-occupancy-sensors); [TechCrunch 2020](https://techcrunch.com/2020/10/08/densitys-open-area-radar-tracks-people-in-a-space-precisely-but-anonymously/) **[vendor]**

**Face detectors and anonymisers you can download, with licences**
- **YuNet** (OpenCV Zoo): **1.45 ms at 160×120 on an Intel CPU and 6.22 ms on a Raspberry Pi CPU**. The OpenCV Zoo repo is **Apache-2.0** ("refer to licenses of different models"). It struggles with small faces, and OpenCV DNN does not support the newest dynamic-shape YuNet version. — [OpenCV Zoo (fork with benchmark table)](https://github.com/Satgoy152/opencv_zoo); [Medium: best face detector](https://medium.com/pythons-gurus/what-is-the-best-face-detector-ab650d8c1225) **[community benchmark]**
- **SCRFD / RetinaFace (InsightFace)**: the code is MIT, but **pretrained weights are "non-commercial research purposes only"**. WIDER FACE (used to train RetinaFace, SCRFD, YOLOv5-Face and YOLOv8-Face) is also for non-commercial research. YOLOv8-Face weights have no LICENSE file in the source repo, so their licence is unclear (AGPL via Ultralytics is likely but unverified). — [InsightFace fork README](https://github.com/thienpn/insightface); [FaceAiSharp SCRFD licence note](https://feed.nuget.org/packages/FaceAiSharp.Models.Scrfd.2dot5g_kps/0.20230205.2/License); [yakhyo/uniface-weights inventory](https://huggingface.co/yakhyo/uniface-weights) **[secondary]**. Non-commercial is acceptable for the hackathon.
- **DeepPrivacy2** (WACV 2023): realistic **face and full-body** anonymisation. **Apache-2.0** except `sg3_torch_utils/` (adapted from NVIDIA StyleGAN2-ADA, separate licence) and the Detectron2-based detector (Detectron2 licence). — [hukkelas/deep_privacy2](https://github.com/hukkelas/deep_privacy2); [WACV 2023 paper](https://openaccess.thecvf.com/content/WACV2023/papers/Hukkelas_DeepPrivacy2_Towards_Realistic_Full-Body_Anonymization_WACV_2023_paper.pdf) **[academic]**

**Does anonymisation hurt downstream accuracy?**
- **Hukkelås & Lindseth, CVPRW 2023**, "Does Image Anonymization Impact Computer Vision Training?": traditional anonymisation (blur and similar) "substantially impacts final model performance, particularly when anonymizing the full body". Realistic anonymisation reduces the drop, with a "minimal performance drop for face anonymization". The supplementary COCO keypoint table shows some blur settings losing about 11–13 AP points at AP50/AP75. The extracted table was garbled, so it is **unclear whether that is face-only or full-body** (most likely full-body). — [arXiv 2306.05135](https://arxiv.org/pdf/2306.05135); [supplementary](https://openaccess.thecvf.com/content/CVPR2023W/WAD/supplemental/Hukkelas_Does_Image_Anonymization_CVPRW_2023_supplemental.pdf) **[academic]**
- **DisguisOR (2023, operating-room video)**: "Human pose estimators are less susceptible to limited modifications of the face area", but head-only anonymisation still has a measurable negative effect on **hip** joint detection. Blackening hurts face detection the most; blurring and pixelation hurt less. — [arXiv 2307.14241](https://arxiv.org/pdf/2307.14241) **[academic]**
- A pose and kinematics study concluded that face blurring "guarantees subject privacy while not degrading the prediction performance" of the pose model. — [PMC9739378](https://pmc.ncbi.nlm.nih.gov/articles/PMC9739378) **[academic; year not captured]**
- **VLMs on anonymised images**: in a 2026 multimodal-RAG paper, **blur and DP-Pix baselines dropped VQA accuracy "toward chance"** on person-related questions (LLaVA-1.5-13B), while their identity-decoupled method reached 85.4%, close to the un-anonymised result. — [arXiv 2604.23584](https://arxiv.org/pdf/2604.23584) **[academic]**. Separately, face-blurring mitigations gave "slightly lower but comparable" accuracy on ImageNet and a MetaCLIP vision-language model. — [Privacy Blur, arXiv 2512.16086](https://arxiv.org/pdf/2512.16086) **[academic]**

### Inferences
- **Key design point for Easy FnB: blur only what leaves the device.** The edge models (pose, detect, PE-Core/CLIP heads, ByteTrack) can keep seeing raw frames locally, so their accuracy is not affected at all. Anonymisation is applied only to (a) crops sent to Cloud Run and Gemini, (b) the 4 fps live preview and (c) anything logged or stored. That is the Xovis/Frigate pattern: process locally, export metadata or masked imagery.
- **Free face localisation:** YOLO26n-pose already outputs COCO keypoints 0–4 (nose, eyes, ears). An ellipse blur or pixelation around those points needs **no extra model and adds under 1 ms**. A YuNet or SCRFD pass on the crop can catch faces the pose model missed (people seen from behind, partial occlusion). Pixelation or a strong Gaussian blur is the cheapest option and, per DisguisOR, hurts less than black boxes if any model later runs on the anonymised image.
- **Hand-raise verification:** this depends on wrist, elbow and shoulder geometry, so face blur should have little effect (consistent with DisguisOR and PMC9739378). **Staff vs customer** depends on uniform and clothing, so face blur is fine, but **full-body anonymisation (DeepPrivacy2-style) would destroy the uniform cue**. Keep to face-only for these tasks.
- **Gemini on blurred crops:** the 2026 MRAG result says blur ruins *person/identity* questions, but Easy FnB asks "is this person raising a hand to call staff?" and "are there leftover dishes on this table?", which do not depend on the face. Degradation should be small, but this has **not been shown in any source**. The team should run a quick A/B test (about 50–100 crops, raw vs blurred, same prompt) before the demo.
- A **skeleton overlay** (keypoints drawn on the blurred crop) is a cheap extra cue that may help Gemini judge the gesture. This is untested and should be included in the A/B test.

### Gaps
- No source measured **VLM or Gemini accuracy on gesture or hand-raise questions with blurred faces**.
- brighter AI (Deep Natural Anonymization), Aura Vision and other retail "never store video" vendors were not researched (time budget).
- The exact licence of YuNet model weights (as opposed to the OpenCV Zoo repo) was not confirmed.
- The exact Hukkelås keypoint-AP numbers for face-only versus full-body blur were not extracted cleanly.
- Skeleton-only privacy-preserving action recognition papers (2023–2026) were not specifically searched.

---

## Q4. What regulators say: EDPB (EU) and Vietnam's PDPL 2025 / Decree 356/2025 (which replaces Decree 13/2023)

### Takeaway
In Vietnam, the **Personal Data Protection Law (Law 91/2025/QH15)** took effect on **1 Jan 2026**, together with **Decree 356/2025/NĐ-CP**, which replaces Decree 13/2023. Art. 32 allows recording in public places without consent only in limited cases, but **always requires notice, purpose limitation and deletion when no longer needed**. Sending guest images to Gemini (Google cloud, abroad) is very likely a **cross-border transfer**, which needs an impact-assessment dossier (Form 09) and notification to the Ministry of Public Security. Violations of cross-border rules can be fined up to **5% of the previous year's revenue**. Small businesses, startups and household businesses get exemptions from some obligations. In the EU, video analytics are governed by EDPB Guidelines 3/2019 (v2.0, 2020).

### Cited Findings
- Law 91/2025/QH15 was passed on 26/06/2025 and is **effective 01/01/2026**. **Art. 32** (recording in public places and public activities):
  - (1) recording and processing without consent is allowed for (a) defence, security, public order and safety or protecting lawful rights and interests, (b) public events, and (c) other cases set by law;
  - (2) people being recorded must be **notified** or otherwise made aware;
  - (3) data may be used **only for the stated purpose**;
  - (4) data may be kept **only as long as needed** and then deleted;
  - (5) data must be protected.

  Related articles: Art. 14 (deletion and de-identification), Art. 19 (processing without consent), **Art. 30 (big data, AI, cloud)**, **Art. 31 (location and biometric data)**, Art. 8 (handling violations). — [hethongphapluat: Điều 32](https://hethongphapluat.com/luat-bao-ve-du-lieu-ca-nhan-2025/dieu-32); [Thư viện pháp luật: Law 91/2025/QH15](https://thuvienphapluat.vn/van-ban/Bo-may-hanh-chinh/Law-91-2025-QH15-Personal-Data-Protection-665440.aspx) **[legal/primary]**
- **Decree 356/2025/NĐ-CP** was issued 31/12/2025, took effect 01/01/2026 and **replaces Decree 13/2023**. Cross-border transfer (Art. 18): prepare an **impact assessment dossier (Form 09)**, notify the Ministry of Public Security (Forms 01a/01b) and sign a written agreement binding the overseas recipient. Internal processing impact assessment uses Form 10. **Breach notification within 72 h** (Form 08). Data-subject request deadlines apply, for example deletion within 20 days. Entities providing **personal data processing services** need a Ministry of Public Security certificate (Art. 22). — [Luật Việt An: điểm mới Nghị định 356/2025](https://luatvietan.vn/diem-moi-cua-nghi-dinh-356-2025-so-voi-nghi-dinh-13-2023-ve-huong-dan-bao-ve-du-lieu-ca-nhan.html); [LuatVietnam: Nghị định 356/2025](https://luatvietnam.vn/dan-su/nghi-dinh-356-2025-nd-cp-quy-dinh-chi-tiet-luat-bao-ve-du-lieu-ca-nhan-422896-d1.html) **[legal secondary]**
- **Exemptions:**
  - Small enterprises and startups may choose whether to apply Arts. 21, 22 and 33(2) for **5 years** from the effective date.
  - **Household businesses and micro-enterprises are exempt** from those articles, **except** those providing data-processing services or **directly processing sensitive data**.
  - Some SMEs, startups and household businesses are exempt from appointing a DPO under conditions.
  - The cross-border impact dossier is prepared once and updated on change, with post-inspection rather than pre-approval.

  — [VnEconomy](https://vneconomy.vn/luat-bao-ve-du-lieu-ca-nhan-du-lieu-la-loai-von-moi-giup-tang-canh-tranh-cho-doanh-nghiep.htm); [G&V Lawyers legal alert](https://gvlawyers.com.vn/wp-content/uploads/2025/09/VN_Legal-alert-_Law-on-PDP-2025.pdf); [EY legal alert July 2025](https://www.ey.com/content/dam/ey-unified-site/ey-com/vi-vn/technical/tax/documents/legal-alert-july-2025-personal-data-protection-law-vn.pdf) **[legal secondary; article text not read directly]**
- **Fines:** up to **5% of the previous year's revenue** for cross-border transfer violations; a reported maximum of **3 billion VND** for other violations by organisations. Sanctions detail is in a separate **Decree 330** (cybersecurity and PDP sanctions), whose exact tiers were not verified. — [Điều 8 Luật BVDLCN 2025](https://hethongphapluat.com/luat-bao-ve-du-lieu-ca-nhan-2025/dieu-8); [EY: Decree 330 sanctions](https://www.ey.com/content/dam/ey-unified-site/ey-com/vi-vn/technical/tax/documents/ey-vn-decree-330-providing-sanctions-for-personal-data-protection.pdf); [VnEconomy: đề xuất phạt 5%](https://vneconomy.vn/de-xuat-phat-toi-5-doanh-thu-neu-de-lo-du-lieu-khach-hang.htm) **[legal secondary]**
- Under Decree 13/2023, **biometric data such as facial images** was treated as **sensitive** personal data, with extra notice duties (Art. 28 per the source). — [Luật Minh Khuê](https://luatminhkhue.vn/du-lieu-ve-sinh-trac-hoc-la-dlcn-nhay-cam-hay-dlcn-co-ban.aspx) **[legal secondary, refers to the old decree]**
- Laodong reports that AI processing of personal data must be classified by risk level under the new framework (headline only). — [Lao Động](https://news.laodong.vn/cong-nghe/xu-ly-du-lieu-ca-nhan-bang-ai-phai-phan-loai-theo-muc-do-rui-ro-1634865.ldo) **[news; detail not read]**
- **EU:** EDPB **Guidelines 3/2019 on processing personal data through video devices**, v2.0, adopted 29 Jan 2020. The examples are non-exhaustive and the reasoning applies to all uses, including retail. A vendor (Flame Analytics) claims a DPIA is mandatory for video analytics in publicly accessible spaces (**unverified vendor claim**). — [EDPB Guidelines 3/2019 PDF](https://www.edpb.europa.eu/sites/default/files/files/file1/edpb_guidelines_201903_video_devices_en.pdf); [Flame Analytics GDPR guide](https://www.flameanalytics.com/en/gdpr-video-analytics-compliance-guide-shopping-malls/) **[legal/primary + vendor]**
- Osler reports that Québec's privacy regulator prohibited a retailer's use of facial recognition for loss prevention (headline-level). — [Osler](https://www.osler.com/en/insights/updates/quebecs-privacy-regulator-prohibits-retailers-use-of-facial-recognition-for-loss-prevention/) **[legal commentary]**

### Inferences
- A restaurant dining room is open to the public, but it is not obvious that Art. 32's no-consent cases ("public order, security, protecting lawful rights" or "public events") cover **service analytics**. The safest position for Easy FnB is to:
  - (a) display **clear notice signage** ("Camera AI hỗ trợ phục vụ; không nhận diện khuôn mặt; không lưu video");
  - (b) do **no face recognition** and store no face embeddings (PE-Core/CLIP embeddings of whole-body crops for staff-vs-customer could arguably be personal data; keep them on the edge and short-lived);
  - (c) set short retention and delete event crops after verification;
  - (d) **anonymise faces before any upload**, which reduces the "sensitive/biometric" exposure and arguably the cross-border transfer burden.
- **Gemini is a cross-border processor.** Under Decree 356 Art. 18, sending identifiable images abroad needs a Form 09 dossier and a contract. Sending only **blurred crops or skeleton/metadata** makes the data much harder to tie to a person; whether that fully removes the obligation is a legal question. Choosing a Gemini/Vertex region does not by itself keep data inside Vietnam (no Vietnam region was confirmed). For the hackathon, the pitch can say "privacy-by-design: faces are blurred on-device before any cloud call; metadata-only by default".
- **Easy FnB as a vendor** may itself become a "personal data processing service" under Decree 356 Art. 22, which needs a Ministry of Public Security certificate. This matters for commercialisation after the hackathon, not for the demo. It needs legal advice.
- Restaurants that are household businesses (hộ kinh doanh) are exempt from several obligations **unless they directly process sensitive data**. Not processing faces or biometrics keeps them in the exempt category, which is a selling point.

### Gaps
- The full text of PDPL Arts. 19, 20, 21, 22, 30 and 31 and Decree 356's sensitive-data list (whether ordinary CCTV images or only *biometric* facial data count as sensitive) was **not read directly**. The PwC and EY PDFs on Decree 356 could not be fetched (403 or encrypted).
- Exact Decree 330 fine tiers were not verified.
- The specific EDPB paragraphs on video analytics, biometrics and anonymous counting were not extracted.
- No Vietnamese regulator guidance specific to in-store or restaurant AI cameras was found.

---

## Q5. Non-camera sensors (mmWave radar, thermal arrays, lidar/ToF) and table buttons as alternatives or complements

### Takeaway
Radar, thermal and lidar sensors are proven in **offices and buildings** for occupancy and counting, and are private by design. However, **independent accuracy data is scarce**, they cost far more per point of coverage than reusing existing CCTV, and none of them reliably detects **hand-raising for service** or **leftover dishes**. Their realistic role for Easy FnB is a later-phase complement, for example per-table presence. For the demo they serve as a comparison point in the pitch.

### Cited Findings
- **TI IWR6843 mmWave:**
  - A diploma thesis at real store entrances found the IWR6843 people counter **within about 3–10% of reference counters** under favourable installation. — [Doria thesis](https://doria.fi/handle/10024/194925?show=full) **[independent/academic]**
  - TI reference designs: tracking out to 6 m (short range) or 14 m (long range); another report gives 15 m range, **±10 cm** location accuracy and about 1 person/m² density. **Tracker accuracy drops as people interact in close proximity.** — [TI TIDUED6](https://ti.com/document-viewer/lit/html/TIDUED6); [TI TIDUE71D test results](https://ti.com/document-viewer/lit/html/TIDUE71D/test-results-id-155d859a-7149-4498-b9e2-f1aa0b8fab03.html) **[vendor]**
- **Thermal (Butlr):** no public accuracy figures and custom pricing (see Q3). Open-plan offices with clustered seating complicate placement. — [Butlr support: choosing sensor technologies](https://support.butlr.io/hc/en-us/articles/41967391784717-Choosing-the-Right-Occupancy-Sensor-Technologies-for-Your-Space) **[vendor]**
- **Radar (Density Open Area):** covers about a 38–40 ft diameter circle per sensor. The vendor claims "near-perfect" counting with no independent validation. — [Density guide](https://density.io/guides/how-accurate-are-occupancy-sensors) **[vendor]**
- **Lidar:** often reports "high single-digit percentage error" in controlled walkways and degrades in crowded or occluded scenes. It **"cannot determine activity (working vs. bag on a chair)"**. The LOADS lidar queue-monitoring prototype emphasises that lidar measures only distances and angles. — [Vantage Space glossary](https://www.vantagespace.com/zh-tw/glossary/occupancy-measurement-methods/lidar-people-counting); [LOADS (UMBC)](https://mdsoar.org/items/bfa46072-8aa4-42ae-9fd1-24fc9043738a) **[vendor glossary + academic]**

### Inferences
- **For table occupancy:** a cheap 60 GHz radar presence module or an 8×8 thermal array under or above each table could give a robust "occupied/empty" signal that works through occlusion and in the dark. It cannot see **leftover dishes**, which needs vision, nor distinguish **staff from guests**. Multiplied by 20–40 tables, the cost and installation effort are far above reusing existing CCTV.
- **For waving for service:** radar gesture recognition exists in research, but it works at short range with a single user and is not suited to a crowded dining room. Cameras or a **physical call button** (table bell or pager, already common in Vietnamese restaurants) remain the practical options. Both are fully private and nearly 100% reliable when pressed, but they need guests to cooperate. Presenting "camera AI vs call button" as a baseline in the pitch is a good framing.
- The privacy story of these products (Xovis, Butlr, Density: "we never produce images") is exactly the message Easy FnB can borrow by exporting only skeletons and metadata.

### Gaps
- No independent accuracy figures were found for Butlr, Density or Vayyar in restaurant or hospitality seating. Vayyar was not researched.
- Unit prices of mmWave or thermal modules and of restaurant call-button systems in Vietnam were not researched.
- No 2023–2026 paper on radar hand-raise detection in crowded rooms was found (not searched specifically).

---

## Q6. Sending less to the cloud: what to send to a VLM and how much it saves

### Takeaway
The cheapest and most private design is: **metadata and events by default**, with **small anonymised crops only for verification**, sent at a **low media resolution**. Gemini 3 charges about **280 tokens per image at `low`, versus 1120 at the default/`high`** setting, a 4x reduction per image. The live preview is the biggest bandwidth and privacy leak, and it can usually be replaced with a rendered "digital twin" (boxes and skeletons on a static background or floor plan) plus on-demand blurred snapshots.

### Cited Findings
- **Gemini 3 (and newer) `media_resolution` image token counts:** `low` = **280**, `medium` = 560, `high` = **1120** (also the default), `ultra_high` = 2240 (per-item only). Per-item resolution is only supported on Gemini 3 and newer. Google recommends `high` for "most image analysis tasks" and `low` when cost and latency matter more than detail. Earlier models (Gemini 2.x) count tokens differently, and the page gives no 2.x numbers. — [Google AI Studio docs: Media resolution](https://aistudio.google.com/docs/media-resolution?hl=en) **[vendor docs]**
- "Question-guided token pruning" has been proposed as a VLM privacy defence ("Don't send what you don't need"). Headline numbers were not retrieved. — [arXiv 2609.15671](https://arxiv.org/pdf/2609.15671) **[academic, 2026]**
- Xovis and Density export only metadata from the device (see Q3). — [Bumbee Labs on Xovis](https://bumbeelabs.com/solutions/xovis-people-counting-analytics/); [Density support](https://support.density.io/hc/en-us/articles/1260804189489)

### Inferences (rough estimates, not measured)
- **Live preview:** 4 fps × 1080p JPEG at roughly 150–300 KB per frame ≈ 0.6–1.2 MB/s, or about 5–10 Mbps per camera, sent continuously. Alternatives:
  - (a) send **only tracks, skeletons and table states as JSON**. 17 keypoints × 3 values ≈ 200 bytes per person; at 4 Hz with 30 people that is about 24 KB/s, roughly 25–50x less;
  - (b) render boxes and skeletons over a **static, people-free background frame** or a floor plan in the dashboard;
  - (c) offer an on-demand, face-blurred snapshot at 1 fps and 640 px for the manager.
- **Gemini verification:** send a tight crop (person plus table ROI), face-blurred, with an optional skeleton overlay, at `media_resolution: low` or `medium`. Compared with full frames at the default 1120 tokens, that is about 2–4x fewer image tokens per call. Calling Gemini only on events, not every frame, saves far more. Check on the A/B set that hand-raise accuracy at `low` holds, because Google recommends `high` for detailed analysis.
- **Logs:** make sure Cloud Run request logs, error traces and any GCS buckets do not keep raw crops. Store only blurred crops with a short TTL. This is the "privacy leaks via logs/crops" pitfall.

### Gaps
- Gemini 2.5 per-image token counts (often quoted as 258 tokens per ≤384 px image, with 768×768 tiles) and **current per-token prices** could not be confirmed from a fetched source.
- No measurement was found of Gemini accuracy at `low` versus `high` for gesture or table-clearing questions.

---

## Q7. Concrete application to Easy FnB: what to borrow, at which stage, and effort before vs after 14 Nov 2026

### Takeaway
With 9 days left, the highest-value privacy and efficiency borrowings are all **software-only changes to the existing pipeline**:
1. head-keypoint face blur on everything that leaves the edge;
2. a metadata or skeleton-first live view;
3. sub-stream decoding plus motion/zone-gated, low-fps inference for a CPU-only profile;
4. Gemini at low media resolution, called on events only, with a quick blurred-vs-raw A/B test;
5. signage, retention and no-face-recognition statements tied to PDPL Art. 32 and Decree 356.

Hardware ports (Hailo, RK3588, Intel NPU), realistic anonymisation (DeepPrivacy2) and non-camera sensors belong after the hackathon.

### Cited Findings (basis for the plan)
- Process locally and export metadata only (Xovis, Density, Butlr). — [Bumbee Labs on Xovis](https://bumbeelabs.com/solutions/xovis-people-counting-analytics/); [Density support](https://support.density.io/hc/en-us/articles/1260804189489)
- Motion gating, sub-stream detection at about 5 fps, day/night thresholds. — [Frigate motion docs](https://docs.frigate.video/configuration/motion_detection); [Frigate hardware docs](https://docs.frigate.video/frigate/hardware)
- Face-only blur barely hurts pose; full-body anonymisation hurts. — [arXiv 2306.05135](https://arxiv.org/pdf/2306.05135); [arXiv 2307.14241](https://arxiv.org/pdf/2307.14241)
- OpenVINO INT8 YOLO26n ≈ 5.8 ms and YOLO26s ≈ 9.3 ms on a Core Ultra 7 155H. — [Ultralytics OpenVINO docs](https://docs.ultralytics.com/integrations/openvino)
- Gemini 3 low = 280 tokens vs high = 1120. — [Media resolution docs](https://aistudio.google.com/docs/media-resolution?hl=en)
- PDPL Art. 32 requires notice, purpose limitation and deletion; Decree 356 Art. 18 requires a cross-border dossier. — [Điều 32](https://hethongphapluat.com/luat-bao-ve-du-lieu-ca-nhan-2025/dieu-32); [Luật Việt An](https://luatvietan.vn/diem-moi-cua-nghi-dinh-356-2025-so-voi-nghi-dinh-13-2023-ve-huong-dan-bao-ve-du-lieu-ca-nhan.html)

### Inferences: plan and effort (team estimates, not sourced)
**Before 14 Nov (demo-critical, about 3–4 person-days in total):**

| # | Change | Pipeline stage | Effort | Risk |
|---|---|---|---|---|
| 1 | **Face blur from pose keypoints 0–4** (ellipse pixelate or blur, radius from the ear–ear or eye–nose distance); YuNet fallback on uploaded crops | Edge, just before encoding crops and preview JPEGs | 0.5 day | Low. Misses heads with no visible keypoints, so add the YuNet pass or blur the top ~20% of the person box as a fallback |
| 2 | **Privacy-mode live view**: send tracks, skeletons and table states as JSON; the dashboard draws them on a static empty-room background; blurred snapshot only on demand | Edge to Cloud Run to dashboard | 1 day | Medium (frontend work). Good demo visual: "we never stream faces" |
| 3 | **Sub-stream for inference, main stream only for event crops**; motion or zone gate (frame-diff on the table and entrance ROIs) before the pose model; leftover-item detect on table ROIs every 5–10 s or after a "left" event | Edge | 1 day | Medium. Check the DVR sub-stream resolution; IR switch false motion needs a `lightning_threshold`-style skip |
| 4 | **Gemini on blurred crops at `media_resolution` low/medium**, event-only; A/B test of 50–100 crops raw vs blurred vs blurred+skeleton | Cloud | 0.5 day | Low. Shows judges that privacy doesn't cost accuracy, or quantifies the cost |
| 5 | **Compliance slide and signage**: notice sign (Art. 32(2)); no face recognition or biometric templates; crop TTL (e.g. delete after 24 h); no raw video stored; cross-border statement (only anonymised crops go to Gemini) | Docs and pitch | 0.5 day | Low |
| 6 | (Optional) **CPU-only demo profile**: OpenVINO INT8, imgsz 320–416, 2–5 fps per camera, iGPU device if available; show fps on a cheap PC | Edge | 0.5–1 day | Medium. Measure first; drop YOLO26s to low-frequency ROI checks |

**After the hackathon:**
- Port to **Hailo-8L/10H** (Pi 5 AI HAT+ or M.2 in a mini-PC) or an **Intel N100/N150/Core Ultra mini-PC with OpenVINO iGPU/NPU**. Avoid Coral. RK3588 is the cheapest option but needs RKNN conversion of the pose model.
- Multi-stream batching (DeepStream, DL Streamer or Savant) for restaurants with 8–16 cameras.
- Realistic anonymisation (DeepPrivacy2, Apache-2.0 with exceptions) if full-body crops ever need to be shared for labelling or training. Keep face-only for the staff-vs-customer cue.
- Optional per-table **mmWave or thermal presence** sensors for premium tiers, and **call-button integration** as a fallback channel.
- Formal PDPL compliance: Decree 356 Form 09 cross-border dossier, Form 10 impact assessment, a DPA with Google, and checking whether Easy FnB needs an Art. 22 processing-service certificate. Get legal advice.

### Gaps
- No real-world measurement of Easy FnB's own pipeline on a CPU-only Vietnamese shop PC exists yet. The effort estimates above are inferences.
- The legal status of whole-body CLIP/PE-Core embeddings (personal data vs biometric) under the PDPL is unresolved.
