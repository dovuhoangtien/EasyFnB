# Face detection and recognition for returning-customer recognition in Vietnamese restaurant CCTV (Easy FnB, as of Nov 2026)

Scope: detector, alignment, embedding model, quality filter, clustering/matching, licences (code vs weights), Vietnamese law (Law 91/2025/QH15, Decree 356/2025/ND-CP, Decree 330/2026/ND-CP), and managed-cloud alternatives. Research date: 4 Nov 2026. Target hardware: RTX 3050 4 GB laptop or a CPU-only PC, a few faces per second.

**Main points for the report writer:**
1. **Licensing.** No widely used, accurate face *recognition* model has pretrained weights that are clearly cleared for commercial use. InsightFace, LVFace, EdgeFace and CR-FIQA weights are all marked non-commercial. AdaFace says to "follow the license of the training dataset". OpenCV Zoo's SFace (Apache-2.0) and YuNet (MIT) are the only mainstream options whose distributor applies a permissive licence to the weights.
2. **Law.** Since 1 Jan 2026, biometric data is legally *sensitive* personal data in Vietnam (Decree 356/2025, Art. 4(1)(dd)). Since 19 Aug 2026 there is a specific penalty decree (330/2026). A small restaurant that processes face templates loses the household/micro-enterprise exemptions.
3. **Design.** The "Apple Photos-style unnamed clusters of everyone who walks in" idea is the main legal risk. Building templates of customers who have not consented is processing sensitive data without consent. The recommended design is opt-in enrolment first, then 1:N matching only against enrolled members, and immediate discard of every non-matching embedding.

---

## 1. Face detection: which detector (accuracy on WIDER FACE Hard, CPU speed, licence)?

### Takeaway
SCRFD-10G/34G and YOLO-face variants are the most accurate on WIDER FACE Hard (about 83–85 AP). But SCRFD weights are non-commercial (InsightFace), and YOLO-face weights inherit Ultralytics AGPL-3.0. OpenCV's **YuNet** is lower on Hard (about 75 AP) but MIT-licensed, tiny and millisecond-level on CPU. That is adequate for a face-height entrance camera. For small ceiling-camera faces, SCRFD or YOLO-face would be noticeably better but carry licence costs.

### Cited Findings
**YuNet (OpenCV Zoo)**
- **Licence: MIT, not Apache-2.0** as the brief assumed. The model directory says "All files in this directory are licensed under MIT License". The OpenCV Zoo as a whole is Apache-2.0 but tells users to "refer to the licenses of the individual models". — [OpenCV Zoo YuNet](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet); [OpenCV Zoo README](https://github.com/opencv/opencv_zoo)
- **Accuracy (WIDER FACE val):** Easy 0.8844, Medium 0.8656, Hard 0.7503. The int8 quantised version scores 0.8810 / 0.8629 / 0.7503, and the block-quantised version is the same as fp32. The page's intro text gives older, lower figures (0.834 / 0.824 / 0.708) without explanation. — [OpenCV Zoo YuNet](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet)
- **Face sizes:** detects faces of about 10×10 to 300×300 px.
- **Model files:** `face_detection_yunet_2023mar.onnx` (fixed input, OpenCV 4.x DNN), int8 and int8-block-quantised variants, and a new default `face_detection_yunet_2026may.onnx` with dynamic height and width for the OpenCV 5.x ONNX Runtime engine. — [OpenCV Zoo YuNet](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet)
- **Landmarks:** 5 points only, which is enough for ArcFace-style alignment. — [OpenCV Zoo SFace](https://github.com/opencv/opencv_zoo/tree/main/models/face_recognition_sface)
- **Paper:** "YuNet: A tiny millisecond-level face detector" (Machine Intelligence Research, 2023). Per-device latency is published only as an image (`benchmark/color_table.svg`). The benchmark hardware includes an Intel i7-12700K, Raspberry Pi 4B and Jetson boards; timings are batch 1, mean of 10 runs, including pre- and post-processing. — [OpenCV Zoo YuNet](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet); [OpenCV Zoo README](https://github.com/opencv/opencv_zoo)

**SCRFD (InsightFace)**

WIDER FACE AP and latency at VGA resolution:

| Model | Easy | Medium | Hard | Params | Infer |
|---|---|---|---|---|---|
| SCRFD_500M | 90.57 | 88.12 | 68.51 | 0.57 M | 3.6 ms |
| SCRFD_1G | 92.38 | 90.57 | 74.80 | – | 4.1 ms |
| SCRFD_2.5G | 93.78 | 92.16 | 77.87 | 0.67 M | 4.2 ms |
| SCRFD_10G | 95.16 | 93.87 | 83.05 | 3.86 M | 4.9 ms |
| SCRFD_34G | 96.06 | 94.92 | 85.29 | 9.80 M | 11.7 ms |

- The README does not name the hardware used for the latency figures. — [SCRFD README](https://github.com/deepinsight/insightface/tree/master/detection/scrfd)

**RetinaFace (CVPR 2020), from the same SCRFD comparison table**

| Backbone | Easy | Medium | Hard | Params | Infer |
|---|---|---|---|---|---|
| MobileNet0.25 | 87.78 | 81.16 | **47.32** | – | 7.9 ms |
| ResNet50 | 94.92 | 91.90 | **64.17** | 29.5 M | 21.7 ms |

- On this table, RetinaFace is clearly worse than SCRFD on Hard. Note this is SCRFD's own comparison. — [SCRFD README](https://github.com/deepinsight/insightface/tree/master/detection/scrfd)

**SCRFD licence**
- SCRFD-10GF is the detector inside the `buffalo_l` and `antelopev2` packs, and SCRFD-500MF is inside `buffalo_s` and `buffalo_sc`. The InsightFace model zoo states "ALL models are available for non-commercial research purposes only". — [InsightFace model_zoo](https://github.com/deepinsight/insightface/tree/master/model_zoo)

**YOLO face variants**
- **YOLO11n face model (Hugging Face):** Easy ≈ 0.942, Medium ≈ 0.921, Hard ≈ 0.810. The card says its code and weights derive from Ultralytics YOLO11 (AGPL-3.0). Using it in a product or network service requires AGPL compliance or an Ultralytics enterprise licence. — [HackerNoon YOLOv11n-face](https://hackernoon.com/yolov11n-face-detection-lightweight-face-detection-with-yolov11); [HF face-model](https://huggingface.co/Banaxi-Tech/face-model)
- **zjykzj/yolo11face** (YOLO11-pose based) reports Hard AP 0.852. The repo itself is Apache-2.0 (2025) but it builds on Ultralytics. — [ecosyste.ms yolo11face](https://awesome.ecosyste.ms/projects/github.com%2Fzjykzj%2Fyolo11face)
- **YOLOv8-face** checkpoints on HF are listed as AGPL-3.0. — [PromptLayer yolov8-face](https://www.promptlayer.com/models/yolov8-face-detection)

**Training data (affects almost all detectors)**
- The Hugging Face metadata for WIDER FACE lists **CC BY-NC-ND 4.0**. Third-party mirrors (Roboflow "Public Domain", Kaggle "CC0") conflict and are not authoritative. — [HF wider_face](https://huggingface.co/datasets/CUHK-CSE/wider_face)

### Inferences
- **For the face-height entrance camera:** faces will usually be 60–200 px, so YuNet's lower Hard-set score (which is driven by tiny and occluded faces) matters little. Its MIT licence and ms-level CPU speed make it the default.
- **For ceiling-camera faces:** SCRFD-10G or YOLO11-face would find many more small faces (Hard 83–85 vs 75). But those faces are generally too small and angled for reliable *recognition* anyway (see section 2). Recognition should rely on the entrance camera, and ceiling cameras should do person counting and tracking only.
- **Residual risk:** nearly every public face detector (YuNet, SCRFD, YOLO-face) is trained on WIDER FACE, which HF lists as non-commercial. A permissive weight licence from the distributor (MIT for YuNet) is the best available assurance, but it is not proof that commercial use is risk-free.
- **Throughput:** on an RTX 3050 or a modern CPU, any of these detectors at VGA resolution should easily exceed "a few faces per second". The bottleneck will be the recognition model and the decoding of multiple streams. This is not benchmarked here.

### Gaps
- No verified CPU latency numbers (ms) for YuNet, SCRFD or YOLO-face on a specific laptop CPU. The OpenCV Zoo benchmark is an image, and SCRFD does not name its hardware.
- BlazeFace / MediaPipe Face Detector: not researched in this session (licence, WIDER FACE numbers). From background knowledge, MediaPipe is Apache-2.0 and its short-range model targets selfie distance, so it is likely poorly suited to CCTV. This is unverified.
- No verified "new 2025–2026 detector" that beats SCRFD-34G on WIDER FACE Hard with a commercial licence was found. YOLO26 face variants were not found in the searches.
- The official WIDER FACE homepage terms (shuoyang1213.me/WIDERFACE) were not retrieved.

---

## 2. Face recognition embeddings: accuracy (incl. low-resolution), size and speed, licences (code vs weights)

### Takeaway
State-of-the-art accuracy on IJB-C at TAR@FAR=1e-4 is about 97.3–97.7%: LVFace (ICCV 2025), AdaFace R100 WebFace12M, InsightFace buffalo_l R50, and TopoFR. **None of these pretrained weights is cleared for commercial use.** Their code is MIT, but the weights are non-commercial or bound to the training-dataset terms. The only mainstream permissively licensed weights are OpenCV Zoo **SFace** (MobileFaceNet, Apache-2.0), which is less accurate. Low-resolution and surveillance performance drops sharply for every model, so face-height entrance capture is essential.

### Cited Findings
**InsightFace packs** — [InsightFace model_zoo](https://github.com/deepinsight/insightface/tree/master/model_zoo)

| Pack | Detector | Recognition model (training data) | Size |
|---|---|---|---|
| buffalo_l (default) | SCRFD-10GF | ResNet50 (WebFace600K) | 326 MB |
| buffalo_m | SCRFD-2.5GF | ResNet50 (WebFace600K) | 313 MB |
| buffalo_s | SCRFD-500MF | MBF (WebFace600K) | 159 MB |
| buffalo_sc | SCRFD-500MF | MBF (WebFace600K), no landmarks or attributes | 16 MB |
| antelopev2 | SCRFD-10GF | ResNet100 (Glint360K) | 407 MB |

All packs except buffalo_sc also include 2d106 / 3d68 landmarks and gender/age models.

| Pack | MR-ALL | East Asian | LFW | CFP-FP | AgeDB-30 | IJB-C (1e-4) |
|---|---|---|---|---|---|---|
| buffalo_l | 91.25 | **74.96** | 99.83 | 99.33 | 98.23 | 97.25 |
| buffalo_s | 71.87 | **51.03** | 99.70 | 98.00 | 96.58 | 95.02 |

- buffalo_l's per-race MR-ALL scores are African 90.29, Caucasian 94.70, South Asian 93.16, East Asian 74.96.
- buffalo_m has the same accuracy as buffalo_l, and buffalo_sc the same as buffalo_s. No accuracy is published for antelopev2.

**InsightFace licence (code vs weights)**
- **Code:** MIT, "no limitation for both academic and commercial usage".
- **Weights and training data:** "available for non-commercial research purposes only". This applies to both manually downloaded and auto-downloaded models.
- **Commercial route:** a 2025-11-24 update says that for the open-sourced recognition models, e.g. buffalo_l, you should "contact recognition-oss-pack@insightface.ai for licensing". InspireFace SDK and advanced models: contact@insightface.ai. — [InsightFace GitHub](https://github.com/deepinsight/insightface)
- **2026 releases:** InsightFace 1.0 (2026-05-23, desktop GUI), 2.0 (2026-09-09: RGB liveness add-on, "PrivateFrame" local video blur/mosaic tool, raccoon_s/l packs), InsightFace Server (2026-07-27: INT8 embedding quantisation, 50M+ image search on one RTX 5090), and 2.1 (2026-10-03: PersonAnalysis with person detection, face recognition and body ReID; cheetah_s/l packs). No licence is stated for the cheetah or raccoon packs. — [InsightFace GitHub](https://github.com/deepinsight/insightface)

**AdaFace (CVPR 2022)**
- **Licence:** repo is MIT. The page does not say whether the Google-Drive weights share that licence. The HF CVLFace AdaFace IR101-WebFace12M card says only "follow the license of the training dataset". — [AdaFace GitHub](https://github.com/mk-minchul/AdaFace); [HF cvlface_adaface_ir101_webface12m](https://huggingface.co/minchul/cvlface_adaface_ir101_webface12m)
- **IJB-B / IJB-C (TAR@FAR=1e-4):**

| Backbone | Training data | IJB-B | IJB-C |
|---|---|---|---|
| R100 | WebFace12M | 96.41 | 97.66 |
| R100 | WebFace4M | 96.03 | 97.39 |
| R100 | MS1MV2 | 95.67 | 96.89 |
| R50 | WebFace4M | 95.44 | 96.98 |
| R18 | WebFace4M | 93.03 | 94.99 |

- **TinyFace rank-1 / rank-5:** R100 WebFace12M 72.29 / 74.97; R100 MS1MV2 68.21 / 71.54.
- **Quality signal:** AdaFace works by "approximating the image quality with feature norms". — [AdaFace GitHub](https://github.com/mk-minchul/AdaFace)

**EdgeFace (Idiap, IJCB 2023 compact-track winner)**
- **Variants:**

| Variant | Params | MFLOPs | LFW | CFP-FP | AgeDB-30 |
|---|---|---|---|---|---|
| base | 18.23 M | 1399 | 99.83 | 97.01 | 97.60 |
| s_gamma_05 | 3.65 M | 306 | – | – | – |
| xs_gamma_06 | 1.77 M | 154 | 99.73 | 94.71 | 96.08 |
| xxs | 1.24 M | 94.7 | – | – | – |

- **IJB:** the abstract reports IJB-B 92.67 / IJB-C 94.85 for the 1.77 M model.
- **Licence:** code is **BSD-3-Clause**, but the HF weights (EdgeFace-Base) are **CC BY-NC-SA 4.0**, i.e. non-commercial. Training data: WebFace260M (12M and 4M subsets). — [EdgeFace GitHub](https://github.com/otroshi/edgeface); [EdgeFace LICENSE](https://raw.githubusercontent.com/otroshi/edgeface/main/LICENSE); [HF Idiap/EdgeFace-Base](https://huggingface.co/Idiap/EdgeFace-Base)

**SFace (OpenCV Zoo)**
- **Licence:** "All files in this directory are licensed under Apache 2.0 License". No separate weight terms are given, so the weights are distributed under Apache-2.0.
- **Model:** MobileFaceNet trained with SFace loss. ONNX converted by a contributor. Uses 5-landmark alignment (the YuNet output).
- **Accuracy:** the page reports 0.9940 (int8: 0.9932; block-int8: 0.9942) from `tools/eval`, without naming the dataset. The page does not give LFW/CFP/AgeDB/IJB numbers, training data, size or thresholds. — [OpenCV Zoo SFace](https://github.com/opencv/opencv_zoo/tree/main/models/face_recognition_sface)

**LVFace (ByteDance, ICCV 2025)**
- **Architecture:** ViT-based with "Progressive Cluster Optimization"; claims 1st place in the ICCV-21 MFR-Ongoing academic track.
- **Accuracy (Glint360K-trained):** LVFace-B IJB-C 97.70 (1e-4), 97.00 (1e-5), 90.06 (1e-6); IJB-B 96.51. LVFace-T IJB-C 96.67.
- **Licence:** code MIT; weights "for non-commercial research purposes only". — [LVFace GitHub](https://github.com/bytedance/LVFace); [LVFace arXiv 2501.13420](https://arxiv.org/html/2501.13420v1)

**TopoFR (NeurIPS 2024)**
- Topology-alignment training. Self-reported to beat AdaFace and match or beat ViT-based TransFace on IJB-B/C, and SOTA when trained on Glint360K. Code via FaceChain. — [TopoFR arXiv 2410.10587](https://arxiv.org/html/2410.10587v2)

**Low-resolution and surveillance benchmarks**
- **TinyFace:** face heights 6–32 px, average 20 px, vs ≥100 px in popular benchmarks. The authors report "a significant gap" between performance on standard benchmarks and on TinyFace (2018 paper). — [TinyFace arXiv 1811.08965](https://arxiv.org/abs/1811.08965)
- **QMUL-SurvFace (2018):** 463,507 images of 15,573 identities from real surveillance. The best 2018 baseline (CentreFace) reached only ≈53.3% TAR@FAR=1% and ≈26.8% TAR@FAR=0.1%. — [QMUL-SurvFace arXiv 1804.09691](https://arxiv.org/pdf/1804.09691)
- A later leaderboard entry, DiscFace, reaches 35.9 TAR@FAR=0.1%. — [HyperAI SurvFace leaderboard](https://hyper.ai/en/sota/tasks/face-verification/benchmark/face-verification-on-qmul-survface)
- **SwinFR (FG 2025):** treats low-quality face recognition as domain adaptation (pre-train then fine-tune). Claims SOTA on IJB-B/C, TinyFace, IJB-S and BRIAR, and finds that "architecture and training dataset matter more than the choice of loss function" for low-resolution performance. — [SwinFR FG2025 PDF](https://kartik-3004.github.io/portfolio/papers/FG2025_SwinFR.pdf)

**Training data and licensing in general**
- No source was found that confirms commercial use of weights trained on MS1M, WebFace260M or VGGFace2. The InsightFace statement ties trained models to the non-commercial data terms. — [search summary incl. Talgin/facerec mirror of InsightFace README](https://github.com/Talgin/facerec); [WebFace260M paper](https://ar5iv.labs.arxiv.org/html/2204.10149)

**On-device speed reference**
- Apple's on-device Photos face embedding runs in "less than 4ms" on the Apple Neural Engine. — [Apple ML Research](https://machinelearning.apple.com/research/recognizing-people-photos)

### Inferences
**Licence picture**

| Model | Code licence | Weights licence |
|---|---|---|
| InsightFace buffalo_l / antelopev2 | MIT | Non-commercial; commercial licence on request |
| AdaFace | MIT | Training-data terms (WebFace / MS1M: research-only) |
| EdgeFace | BSD-3 | CC BY-NC-SA 4.0 |
| LVFace | MIT | Non-commercial |
| CR-FIQA (quality, see section 3) | CC BY-NC 4.0 | CC BY-NC 4.0 |
| SFace | Apache-2.0 | Apache-2.0 (as distributed by OpenCV) |

- **Practical choices:**
  - (a) A hackathon demo arguably falls under "non-commercial research". But the product is commercial, so building on buffalo_l creates a re-platforming or licence-purchase obligation later.
  - (b) SFace (Apache-2.0) gives a commercially defensible default.
  - (c) Buy a commercial licence (InsightFace) or use a managed API (section 6).
- **East Asian accuracy:** buffalo_l's East Asian MR-ALL score (74.96) is far below its Caucasian score (94.70), and buffalo_s's is only 51.03. A Vietnamese customer base is largely East / Southeast Asian. Expect more confusion between similar-looking customers than headline LFW/IJB-C numbers suggest, and calibrate thresholds on local data.
- **Small faces:** the TinyFace and SurvFace results imply that 20-px ceiling-camera faces cannot reliably identify a returning customer even with the best models (rank-1 of about 72% on TinyFace for AdaFace R100). The entrance camera should give ≥ about 80–112 px faces, close to the standard 112×112 aligned crop. This threshold is inferred, not cited.
- **Hardware fit:** an R50 (buffalo_l-class) model fits on an RTX 3050 4 GB. On CPU-only hardware a MobileFaceNet-class model (SFace, buffalo_s MBF, EdgeFace-xs) is the realistic choice for several faces per second. This is inferred from model sizes and FLOPs; not benchmarked.

### Gaps
- Not researched or verified in this session: ElasticFace, TransFace, GhostFaceNet and FaceNet512 (deepface) licences and numbers.
- No IJB-B/IJB-C or TinyFace numbers for SFace were found; its relative accuracy vs ArcFace R50 is unquantified here.
- From background knowledge (unverified): the OpenCV `FaceRecognizerSF` sample uses cosine ≈ 0.363 and L2 ≈ 1.128 thresholds.
- No CPU latency (ms) measurements for SFace, buffalo_l R50 or EdgeFace on a laptop CPU were found.
- NIST FRTE (FRVT) 2026 leaderboards were not consulted; vendor rankings are not covered.
- No public price for an InsightFace commercial licence.
- The SFace training dataset and its terms were not verified.
- No permissively licensed model trained purely on synthetic data was found.

---

## 3. Face image quality assessment (FIQA) and multi-frame aggregation

### Takeaway
The strongest research FIQA methods are CR-FIQA (NIST FATE-Quality 1st/2nd) and MagFace/AdaFace feature norms. CR-FIQA is CC BY-NC (non-commercial). The **BSI OFIQ** library, the reference implementation for ISO/IEC 29794-5, is open source under a liberal MIT-style licence and is the commercially safest FIQA. A cheap, licence-free alternative is simple gating (detector score, face size, landmark-based pose, blur) plus quality-weighted averaging of several frames per visit.

### Cited Findings
- **CR-FIQA:** licensed "Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)". CR-FIQA(L) is iResNet100 on MS1MV2; CR-FIQA(S) is iResNet50 on CASIA-WebFace. It ranked 1st/2nd in NIST FATE Quality. — [CR-FIQA GitHub](https://github.com/fdbtrs/CR-FIQA)
- **AdaFace feature norm:** the method approximates image quality with feature norms. Low-norm embeddings indicate low-quality inputs and can be used as a quality score. — [AdaFace GitHub](https://github.com/mk-minchul/AdaFace)
- **OFIQ (Open Source Face Image Quality, BSI):**
  - It is the "software-side implementation" of the algorithms in the upcoming revision of ISO/IEC 29794-5. — [BSI OFIQ](https://www.bsi.bund.de/dok/OFIQ1-e)
  - It is C/C++, cross-platform, funded by BSI and implemented by secunet. — [Busch OFIQ slides 2024](https://www.christoph-busch.de/files/Busch-OFIQ-240326.pdf)
  - Licence is described as "open source with liberal license (MIT)" (Busch, 2024) and "no copyleft, so commercial use possible" (NIST IFPC 2025). Repo: github.com/BSI-OFIQ/OFIQ-Project. — [Busch OFIQ slides 2024](https://www.christoph-busch.de/files/Busch-OFIQ-240326.pdf); [NIST IFPC 2025](https://pages.nist.gov/ifpc/2025/presentations/05.pdf); [Busch projects page](https://christoph-busch.de/projects-ofiq.html)
- **Apple Photos:**
  - Filters false-positive and out-of-distribution detections so they do not contaminate the gallery.
  - Uses an "embedding confidence" branch, trained on non-face and out-of-domain crops, to flag unreliable embeddings.
  - Represents each cluster by a "running average of its embeddings".
  - [Apple ML Research](https://machinelearning.apple.com/research/recognizing-people-photos)
- **Google Cloud Vision** face detection returns blur, under-exposure and headwear likelihoods plus roll/pan/tilt angles. These are quality-type signals, but cloud-side and categorical. — [Google Cloud Vision docs](https://docs.cloud.google.com/vision/docs/detecting-faces)

### Inferences
- **Recommended licence-clean quality gate for Easy FnB:**
  - YuNet confidence ≥ ~0.8–0.9.
  - Inter-ocular distance or face box ≥ a minimum pixel size.
  - Yaw/pitch estimated from the 5 landmarks within about ±30°.
  - A blur metric (e.g. variance of the Laplacian) above a tuned threshold.
  - Optionally, OFIQ's unified quality score (MIT-licensed) if integrating C++ is feasible.
  - All thresholds should be tuned on the restaurant's own footage; they are not from a source.
- **Aggregating frames per visit:** track the person (the existing person tracker or an IoU tracker), keep the top-k (e.g. 3–5) quality frames, L2-normalise each embedding, average them (optionally weighted by quality), then re-normalise. This mirrors Apple's running-average cluster representation and the standard IJB "template" practice. It reduces the effect of single bad frames.
- **Norm as a free quality score:** if an AdaFace- or MagFace-type model were licensed, its embedding norm would provide quality at no extra cost. With SFace, use the external heuristics above.

### Gaps
- SER-FIQ and MagFace licences and comparative numbers (ERC curves) were not retrieved.
- No CPU runtime figures for OFIQ were found. Its exact licence file was not read; the MIT claim comes from presentations.
- No published study specifically on the best number of frames per template for restaurant CCTV.

---

## 4. Clustering and matching for a growing open set

### Takeaway
Apple Photos is the best-documented production design:
- a conservative greedy first pass (high precision, many small clusters);
- a second pass of hierarchical agglomerative clustering with median linkage to raise recall;
- the gallery chosen from the largest clusters;
- new faces assigned by sparse coding over per-cluster exemplars rather than a single centroid;
- re-clustering run periodically offline.

The literature on online video clustering uses "attach to an existing cluster or start a new one" with novelty detection. No published source gives universal thresholds; they must be calibrated on local data.

### Cited Findings
- **Apple Photos two-pass clustering:**
  - Pass 1 is greedy and "fairly conservative because when it joins two instances, they are permanently associated", tuned for "high precision but many, smaller clusters". Each cluster is represented by a running average.
  - Pass 2 is hierarchical agglomerative clustering on face embeddings only, with median-distance linkage (random sampling when large). Runtime is similar to single-linkage and accuracy "on par or better than average-linkage HAC".
  - Distance is the minimum of the face distance and a weighted face + upper-body distance. Thresholds are "carefully tuned" but not published.
  - Processing time at iteration 65 was 3.5 s vs 205.8 s for average-linkage.
  - The gallery is chosen from the largest clusters using cluster-size distribution, inter/intra-cluster distances and user input.
  - New observations are assigned via sparse coding over exemplars, which "provides better accuracy" than nearest-neighbour when clusters are small or split.
  - Clustering runs "typically overnight during device charging".
  - [Apple ML Research](https://machinelearning.apple.com/research/recognizing-people-photos)
- **Online constrained clustering for video (ICIP 2018):** each face either attaches to an existing cluster or starts a new one, using spatio-temporal constraints and FaceNet embeddings. Reported 82.1% and 93.8% accuracy on two video benchmarks. — [Kulshreshtha & Guha, ICIP 2018](https://cs.paperswithcode.com/paper/an-online-algorithm-for-constrained-face)
- **Open-set re-identification for human-robot interaction:** online clustering builds and updates a run-time gallery that "will dynamically increase with time". A novelty-detection step decides whether a probe is already in the gallery. 93.55% / 90.41% re-ID accuracy on TERESA / YTF. — [arXiv 1804.03547](https://arxiv.org/pdf/1804.03547v2)
- **Real-time surveillance online clustering (ISPA 2019):** argues that offline clustering is unsuitable because it assumes all embeddings are available up front; reports 84% accuracy. — [AMiner ISPA 2019](https://www.aminer.org/pub/5e89ae9591e01196bd2ae507/an-online-face-clustering-algorithm-for-face-monitoring-and-retrieval-in-real)

### Inferences
- **If consent allows clustering at all** (see section 5):
  - Online, per visit: aggregate the visit template (section 3). Compare it by cosine similarity with each cluster's exemplars (keep several exemplars per cluster, not just the mean). Attach it only if the best similarity is above a strict threshold T_high *and* clearly ahead of the second-best cluster (a margin rule). Otherwise create a new provisional cluster.
  - Offline, nightly: run an Apple-style HAC with median or average linkage to merge provisional clusters. Show "possible same person?" merge suggestions to the owner instead of auto-merging in the grey zone. This prevents irreversible false merges.
- **For the consent-first design (recommended):**
  - The problem simplifies to 1:N verification against a small enrolled gallery (dozens to hundreds of members).
  - Use 3–5 enrolment images per member; keep all of them as exemplars plus their mean.
  - Pick the threshold for a target false-accept rate (e.g. ≤ 0.1%) on a labelled local validation set. Within the visit, require agreement across ≥ 2 high-quality frames before greeting someone by name.
  - In the uncertain band, show "Possibly: <name>?" to staff rather than asserting an identity.
- **Calibration:** cosine similarities are not probabilities and differ by model (SFace vs ArcFace). Threshold calibration must be redone if the model changes. Embeddings from different models are not interchangeable, so the gallery must be re-enrolled after a model switch.

### Gaps
- No published numeric thresholds for Apple, Google Photos or commercial systems.
- Google Photos' face-grouping internals: no 2025–2026 primary source was retrieved. The FaceNet (2015) lineage is known but was not fetched.
- HDBSCAN, Chinese Whispers and FINCH comparisons for incremental face clustering were not found in these searches.

---

## 5. Vietnam law: is facial biometric data sensitive, what consent is needed, and what a small restaurant must do

### Takeaway
Yes. Under Decree 356/2025/ND-CP (effective 1 Jan 2026, replacing Decree 13/2023), "biometric data and genetic characteristics" are **sensitive personal data**. The Law on Personal Data Protection No. 91/2025/QH15 (effective 1 Jan 2026) requires:
- consent that is voluntary, explicit, specific and per purpose (silence is not consent);
- notification of people recorded in public places;
- deletion once the purpose ends;
- physical and technical security for biometric data.

Because the restaurant would *directly process sensitive data*, it loses the household, micro-enterprise and small-enterprise exemptions (DPIA, DPO). Decree 330/2026/ND-CP (issued and effective 19 Aug 2026) now fines:
- biometric-security failures: 50–70 M VND;
- biometric use beyond the original purpose without consent: up to 150 M VND;
- cameras in customer-service areas without clear notice: 10–20 M VND.

### Cited Findings
**Statute and implementing decree**
- Law 91/2025/QH15 took effect 1 Jan 2026. Implementing Decree 356/2025/ND-CP replaces Decree 13/2023/ND-CP. — [LuatVietnam legal updates](https://luatvietnam.vn/legal-updates/the-latest-law-on-personal-data-protection-and-the-guiding-documents-892-106778-article.html); [LuatVietnam Decree 356 (EN)](https://english.luatvietnam.vn/decree-no-356-2025-nd-cp-dated-december-31-2025-of-the-government-detailing-a-number-of-articles-and-measures-for-the-implementation-of-the-law-on-p-422896-doc1.html)

**Law 91/2025/QH15** — [LuatVietnam Law 91/2025 (EN)](https://english.luatvietnam.vn/dan-su/law-on-personal-data-protection-law-no-91-2025-qh15-405135-d1.html)
- **Art. 2(3):** sensitive data is data "associated with the privacy of individuals"; the full list is delegated to the Government.
- **Art. 31(2):** biometric data is "data on physical attributes and unique and stable biological characteristics of a person".
- **Art. 31(4)(a):** biometric data collectors and processors must "apply physical security measures" to storage and transmission devices, limit access, and run a monitoring system.
- **Art. 31(4)(b):** they must notify the data subject if processing causes damage.
- **Consent (Art. 9):**
  - valid only if voluntary, with clear knowledge of the data type, purpose, controller identity, and the subject's rights and obligations (Art. 9(2));
  - must be explicit and specific, in a form that can be printed or copied to text; electronic or verifiable formats are accepted (Art. 9(3));
  - given per purpose and not bundled with unrelated mandatory conditions; silence or non-response is not consent (Art. 9(4)).
- **Withdrawal (Art. 10):** subjects may withdraw or restrict in writing, including electronically. Withdrawal does not undo prior processing (Art. 10(4)).
- **Deletion (Art. 14):** grounds for deletion are in Art. 14(1).
- **Recording in public places (Art. 32):**
  - recording without consent is allowed only for national defence, security and public order, and for public events (Art. 32(1));
  - recorded persons must be notified or informed (Art. 32(2));
  - footage is kept only as long as needed, then deleted (Art. 32(4)).
- **Exemptions (Art. 38):** small enterprises and start-ups may opt out of DPIA (Arts. 21–22) and designated protection staff (Art. 33(2)) for 5 years. Household businesses and micro-enterprises are not required to comply with those provisions. Neither exemption applies to entities that provide processing services, **directly process sensitive data**, or process data of a large number of subjects.
- **Penalties (Art. 8):** general administrative fine cap VND 3 billion; cross-border transfer violations up to 5% of the previous year's revenue; buying or selling data up to 10× proceeds; individuals pay half the organisational cap.

**Decree 356/2025/ND-CP** (dated 31 Dec 2025) — [LuatVietnam Decree 356 (EN)](https://english.luatvietnam.vn/decree-no-356-2025-nd-cp-dated-december-31-2025-of-the-government-detailing-a-number-of-articles-and-measures-for-the-implementation-of-the-law-on-p-422896-doc1.html)
- **Art. 4(1)(dd):** sensitive personal data includes "Biometric data and genetic characteristics". **Art. 3(6):** "Image" is *basic* personal data.
  - Inference: a plain CCTV image is basic data; a face template used for identification is biometric, hence sensitive.
- **Art. 4(2):** sensitive data processing requires rules on access delegation, procedures and confidentiality.
- **Art. 5 deadlines:** respond to any data-subject request within **2 working days**.
  - Withdrawal of consent, restriction or objection: stop processing within 15 days (20 if a processor is involved); one extension of up to 15 days.
  - Deletion: complete within **20 days** (30 with a processor); one extension of up to 20 days.
  - Access or correction: within 10 days (15 with a processor).
- **Art. 6 consent records:** consent methods must make the subject's identity, the time and the content verifiable. Accepted methods include written consent, recorded calls, SMS syntax and platform mechanisms. Controllers must keep consent records and bear the burden of proof. Default consent is prohibited. Subjects must be told when the data is sensitive.
- **Art. 19 DPIA:** the processing impact assessment dossier (Form 10) is prepared from the start of processing and submitted within 60 days. **Art. 20:** update every 6 months when purposes or parties change.
- **Art. 29 breaches:** for incidents involving biometric or location data, notify affected subjects (and the Ministry of Public Security) within **72 hours**. — also [Rouse, 2026](https://rouse.com/insights/news/2026/vietnam-key-developments-in-personal-data-protection-under-decree-no-356-2025-nd-cp-and-issues-businesses-need-to-review)
- **Art. 41 exemptions:** the small, start-up, household and micro-enterprise exemptions do not apply to those that "directly process sensitive personal data" or reach ≥ **100,000** data subjects (accumulated).
- **Art. 42:** effective 1 Jan 2026; Decree 13/2023 ceases to be effective.
- **AI processing (Art. 10, per Rouse):** requires clear notice, an explanation of core algorithmic principles, and opt-out where automated processing or inferred data may identify individuals. Rouse also notes the list of sensitive data is "non-exhaustive". — [Rouse, 2026](https://rouse.com/insights/news/2026/vietnam-key-developments-in-personal-data-protection-under-decree-no-356-2025-nd-cp-and-issues-businesses-need-to-review)

**Decree 330/2026/ND-CP** (sanctions in cybersecurity and personal data protection; issued 19 Aug 2026, effective on signing) — [GV Lawyers legal alert, Aug 2026](https://gvlawyers.com.vn/wp-content/uploads/2026/08/VN_Legal-alert_-PDP-under-Decree-No.-330.2026-1.pdf); effective date also reported by [VOV](https://vov.vn/chinh-tri/tu-1982026-tu-y-thu-thap-xu-ly-du-lieu-ca-nhan-bi-phat-toi-70-trieu-dong-post1326424.vov)
- **Who is fined how much:** amounts are for organisations; individuals pay half. Household businesses are fined at the individual rate.

| Violation | Fine (organisations, VND) |
|---|---|
| Treating silence as consent | up to 70 M |
| Collecting beyond purpose or scope | 30–50 M (basic data); 50–80 M (sensitive data) |
| Unlawful collection by technical means | 100–800 M |
| Biometric data without proper protection of storage and transmission devices | 50–70 M |
| Biometric data used beyond the original purpose without consent | up to 150 M |
| Cameras or recorders in public spaces or **customer-service areas** without clear notice or warning | 10–20 M |
| Late or inaccurate breach notification (72 h rule) | 50–70 M |
| No designated data-protection staff or unit | 20–30 M |
| No DPIA dossier | 20–30 M |
| No procedure for data-subject requests (2-working-day handling) | 10–20 M |
| AI / automated-decision violations | 50–100 M (oversight and human review); 50–70 M (failure to notify or explain) |

- Additional sanctions reported in news coverage: suspension of systems for 3–6 months for biometric breaches. — [lsvn.vn](https://lsvn.vn/su-dung-du-lieu-sinh-trac-hoc-vuot-muc-dich-ban-dau-bi-phat-den-150-trieu-dong-a178152)

**Practice commentary**
- Commentary on employee face-recognition cameras says facial data is "extremely sensitive" biometric data. It also says:
  - covert facial-recognition cameras disguised as ordinary security cameras are not allowed;
  - a visible "Khu vực có camera giám sát" sign should be placed before the filmed area;
  - written notice should cover location, data type, how the system works and retention;
  - biometric data must be deleted when the purpose ends.
  - This is employee-focused and cites Arts. 25 and 32 of the Law. — [Luật Việt An](https://luatvietan.vn/camera-giam-sat-va-cham-cong-khuon-mat-yeu-cau-bao-ve-du-lieu-nguoi-lao-dong.html)

**Google's own policy (relevant because the demo must use Gemini)**
- Google's Generative AI Prohibited Use Policy forbids "using personal data or biometrics without legally-required consent" and anything that "Tracks or monitors people without their consent". — [Google Gen AI Prohibited Use Policy](https://policies.google.com/terms/generative-ai/use-policy)

### Inferences
- **Clustering everyone is the problem.** Automatically clustering *all* customers' faces across visits into unnamed "People" before they consent means creating biometric templates (sensitive data) of non-consenting people for a commercial loyalty purpose. Art. 32(1) allows consent-less recording only for security, public order and public events, not marketing or loyalty. Decree 330's fines for beyond-purpose biometric use (≤ 150 M) and unlawful collection by technical means (100–800 M) are directly relevant. **Recommendation: drop "cluster everyone, name later" for production. Use opt-in enrolment, then 1:N matching against members only.**
- **Recommended consent and privacy design:**
  1. **Signage at the entrance:** "Khu vực có camera giám sát" plus a second line stating that face recognition is used *only for members who registered*. Include a QR code linking to a privacy notice.
  2. **Opt-in enrolment** (Zalo mini-app or QR, or at the counter with staff), as a separate, unbundled checkbox for "nhận diện khuôn mặt để nhận ưu đãi khách quen" (face recognition for regular-customer perks). The flow:
     - say explicitly that this is sensitive (biometric) data (Decree 356 Art. 6(4));
     - state the purpose, retention period, controller identity and rights;
     - log consent with timestamp, version and content (Art. 6(1)–(2));
     - capture 3–5 selfies or entrance shots at enrolment.
  3. **Store only embeddings,** encrypted, on the edge PC (no raw face crops after enrolment), with access control and an audit log (Law Art. 31(4)). An embedding is still biometric data (it encodes "unique and stable biological characteristics"), so do not treat it as anonymised.
  4. **Non-members:** compute the embedding in memory, compare against the gallery, and discard it immediately if there is no match. Never persist or cluster it. Analytics such as visitor counts use person detection without face templates.
  5. **Withdrawal and deletion:** a one-tap "delete my face" in the mini-app or by asking staff. Acknowledge within 2 working days and delete the template, backups and match logs within 20 days (Decree 356 Art. 5).
  6. **Retention:** auto-delete templates of members inactive for N months (e.g. 12), and state this in the notice.
  7. **Cloud boundary:** keep biometric matching on the edge. Send only pseudonymous member IDs and visit events to Cloud Run and Gemini; never send face crops to Gemini for identification. If templates must go to a foreign region (e.g. GCP asia-southeast1 Singapore or AWS ap-southeast-1), a cross-border transfer impact assessment is needed and violations risk fines of up to 5% of revenue (Law Art. 8(4)).
  8. **Paperwork:** because sensitive data is processed directly, prepare the DPIA dossier (Decree 356 Art. 19, within 60 days), designate a responsible person (Decree 330: 20–30 M fine otherwise), and have a 72-hour breach procedure.
  9. **Hackathon demo:** use team members or volunteers who have signed consent forms. Present the opt-in flow itself as a feature; it is a strong compliance story for judges.

### Gaps
- The exact Decree 330/2026 article numbers for each fine were not read from the official gazette; the figures come from the GV Lawyers alert and news reports. Verify on vbpl.vn or congbao.chinhphu.vn.
- thuvienphapluat.vn returned 403, so the Vietnamese original text was not read directly; English translations (LuatVietnam) were used.
- No specific Vietnamese regulation on CCTV signage format (size, wording) was found beyond Decree 330's "clear notice/warning" duty and commentary.
- Whether a face *embedding* (vs raw image) is legally "biometric data" is not explicitly addressed in the texts found. The inference above is based on the Art. 31(2) definition.
- Whether GCP has a Vietnam region in 2026 was not checked.

---

## 6. Managed cloud alternatives: Google Cloud Vision, AWS Rekognition, Azure Face

### Takeaway
Google Cloud Vision **does not do identification**. Its docs state: "Specific individual Facial Recognition is not supported." AWS Rekognition supports face collections and search: about $0.001 per image for the first 1M Group-1 calls, plus $0.00001 per stored face vector per month, with a 12-month free tier. Azure Face identification and verification are **Limited Access**: registration is required and only Microsoft-managed customers are eligible, which makes it unrealistic for a hackathon team. Any managed service also means cross-border transfer of sensitive data.

### Cited Findings
- **Google Cloud Vision:** "Specific individual Facial Recognition is not supported." It returns bounding boxes, landmarks (x, y, z), roll/pan/tilt, detection confidence, and likelihoods for joy, sorrow, anger and surprise plus under-exposure, blur and headwear. — [Google Cloud Vision: Detect faces](https://docs.cloud.google.com/vision/docs/detecting-faces)
- **AWS Rekognition Image pricing** — [AWS Rekognition pricing](https://aws.amazon.com/rekognition/pricing/)
  - Group 1 APIs (IndexFaces, SearchFaces, SearchFacesByImage, SearchUsers, SearchUsersByImage, CompareFaces, AssociateFaces): $0.0010/image for the first 1M; $0.0008 next 3M; $0.0006 next 30M; $0.0004 above that.
  - DetectFaces is Group 2 (also $0.0010/image for the first 1M).
  - Face and user vector storage: $0.00001 per vector per month.
  - Free tier: 1,000 images/month for each of Group 1 and Group 2, plus 1,000 stored face vectors and 1,000 user vectors, for 12 months. New accounts since 15 Jul 2025 may get up to $200 in credits.
  - Streaming video events: $0.00817/min (US East). Face Liveness: $0.015/check for the first 500k.
- **Azure Face**
  - Face identification and verification are Limited Access. Customers must register via a form and are subject to "Microsoft's sole discretion based on eligibility criteria and a vetting process".
  - It is "available only to customers managed by Microsoft, defined as those customers and partners who are working directly with Microsoft account teams".
  - Only certain use cases qualify; there is no Free (F0) tier for these features; use by or for U.S. police is prohibited.
  - Face Detection is available without registration. Page updated 2026-10-19.
  - [Microsoft Learn: Limited Access Face](https://learn.microsoft.com/en-us/legal/cognitive-services/computer-vision/limited-access-identity)

### Inferences
- **Rough Rekognition cost per restaurant:** about 300 visits/day × 3 searches ≈ 27k Group-1 calls/month, about $27/month after the free tier, plus negligible vector storage. This is cheap but adds internet latency at the entrance and cross-border transfer of biometric data (AWS has no Vietnam region; the nearest is Singapore). Rekognition region availability for Vietnam was not checked.
- **Hackathon constraint (Gemini + Cloud Run):** Google offers no managed face identification, and Gemini's policy bars biometric processing without legally required consent. So face matching should run on the edge with an open model (SFace) or a licensed SDK. Cloud Run hosts the dashboard, member database (pseudonymous IDs) and Gemini-powered summaries.

### Gaps
- Google Cloud Vision face-detection pricing was not retrieved.
- AWS Rekognition per-region price differences and an ap-southeast-1 price check were not done.
- No commercial on-prem SDK pricing (e.g. InspireFace or other vendor SDKs) was found.

---

## 7. Synthesis: recommended pipeline for Easy FnB (derived from the findings above)

### Takeaway
For a **commercially defensible, CPU-capable** pipeline, use:
**entrance camera at face height → YuNet (MIT) detection with 5 landmarks → similarity-transform alignment to 112×112 → quality gate (score, size, pose, blur; optionally OFIQ) → SFace (Apache-2.0) 128-D embedding → quality-weighted visit template → 1:N cosine matching against opt-in members (multiple exemplars, margin rule) → staff UI shows "Khách quen: <name>"; anything uncertain is "possibly <name>".**
- Upgrade path for accuracy: licence InsightFace buffalo_l (SCRFD-10G + ArcFace R50; IJB-C 97.25 vs SFace's lower, unquantified accuracy), or use AWS Rekognition with consent and a cross-border DPIA.
- Do not ship non-commercial weights (buffalo_l, antelopev2, EdgeFace, LVFace, CR-FIQA) in the commercial product without a licence.

### Cited Findings
- YuNet MIT, Hard AP 0.75, 5 landmarks, 10–300 px faces. — [OpenCV Zoo YuNet](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet)
- SFace Apache-2.0, MobileFaceNet, 5-point alignment, int8 variant available. — [OpenCV Zoo SFace](https://github.com/opencv/opencv_zoo/tree/main/models/face_recognition_sface)
- buffalo_l IJB-C 97.25 but non-commercial; licensing contact recognition-oss-pack@insightface.ai. — [InsightFace model_zoo](https://github.com/deepinsight/insightface/tree/master/model_zoo); [InsightFace GitHub](https://github.com/deepinsight/insightface)
- OFIQ as a liberally licensed FIQA. — [NIST IFPC 2025](https://pages.nist.gov/ifpc/2025/presentations/05.pdf)
- Apple's conservative clustering, running-average templates and sparse-coding assignment. — [Apple ML Research](https://machinelearning.apple.com/research/recognizing-people-photos)
- Biometric data is sensitive; consent, notice and fines. — [Decree 356/2025 (EN)](https://english.luatvietnam.vn/decree-no-356-2025-nd-cp-dated-december-31-2025-of-the-government-detailing-a-number-of-articles-and-measures-for-the-implementation-of-the-law-on-p-422896-doc1.html); [GV Lawyers on Decree 330/2026](https://gvlawyers.com.vn/wp-content/uploads/2026/08/VN_Legal-alert_-PDP-under-Decree-No.-330.2026-1.pdf)

### Inferences
- **Hardware mapping:**
  - CPU-only PC: YuNet (int8) + SFace (int8) via OpenCV DNN / ONNX Runtime, entrance stream only, processing a detection every 2–3 frames.
  - RTX 3050 4 GB: same pipeline on CUDA/ORT-GPU, leaving VRAM for the existing YOLO person detector. Or a licensed buffalo_l (R50, about 166 MB ONNX — size inferred from the 326 MB pack total, not cited).
- **Ceiling cameras:** do not attempt identification from ceiling-camera faces. TinyFace and SurvFace results show that even SOTA models fail at 20-px faces. Use ceiling cameras for counting and dwell-time only, without face templates.
- **Implementation detail:** OpenCV ships `FaceDetectorYN` and `FaceRecognizerSF` with `alignCrop` and `match` (cosine / L2). The whole licence-clean pipeline is about 50 lines of Python, which suits a 10-day hackathon timeline. (API names from background knowledge; verify in OpenCV docs.)
- **Demo storytelling:** contrast "ethical-by-design: opt-in, embeddings only, delete in one tap, on-device" with competitors. This turns the legal constraint into a judging advantage.

### Gaps
- No head-to-head accuracy of SFace vs ArcFace R50 on Asian, low-resolution or surveillance data. A quick local test with 10–20 consenting volunteers is recommended before the demo.
- No measured end-to-end FPS on the RTX 3050 laptop or the CPU PC; this must be benchmarked by the team.
