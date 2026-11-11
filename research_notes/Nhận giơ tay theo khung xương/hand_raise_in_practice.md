# Hand-raise / call-for-service detection in practice (classrooms, restaurants, hospitals, meetings), 2020–2026

Scope note: Most published work is classroom hand-raise detection (China, Vietnam, Germany). I found no peer-reviewed restaurant "raise hand to call waiter" system with published accuracy. The closest restaurant material is a Canon patent, a gesture-recognition patent application, and a Korean serving-robot patent claim. All classroom numbers come from the authors' own datasets, often private or research-only. Different datasets, metrics (mAP, accuracy, F1) and label sets make cross-paper comparison unreliable.

## Q1. Classroom hand-raising detection: which approach works best, do sequence models beat single-frame detectors, and how are small back-row students handled?

### Takeaway
Single-frame RGB detectors trained on a "hand-raising" class reach about 0.79–0.87 AP@0.5 on the public SCB datasets. Video, skeleton and sequence systems report about 90% frame-wise or class accuracy on controlled data, but only F1 = 0.76 on real uncontrolled classrooms (Bühler et al. 2023). No paper I found compares a sequence model against a single-frame model on the same hand-raise data, so "sequence beats frame" is unproven. The strongest real-world pattern is hybrid: a per-frame detector or pose, then tracking and temporal aggregation to recover frames lost to occlusion and to fire at the event level.

### Cited Findings
**Single-frame RGB detectors (YOLO family, SCB dataset)**
- SCB-dataset (2023): 4,003 images and 11,248 labels focused on hand-raising. YOLOv7 reached up to 85.3% mAP. The image count varies across versions (4,001 / 4,003 / 4.2k) — [arXiv 2304.02488](https://arxiv.org/html/2304.02488v2)
- YOLOv7-BRA (bi-level routing attention) reported 87.1% mAP@0.5 on SCB, +2.2 points — [arXiv 2305.07825](https://arxiv.org/abs/2305.07825)
- "Improved YOLOv7" (BRA + Wise-IoU) on a 3-class SCB version (hand-raising, reading, writing). Baseline YOLOv7: P 72.0%, R 73.9%, mAP50 77.2%. Best variant: mAP50 79.0% (+1.8), with a precision gain of +5.7 points. YOLOv7 inference is 6.9 ms/image — [arXiv 2306.03318](https://arxiv.org/html/2306.03318v2) (text extracted from the PDF)
- SCB-Dataset3 (2025 work): 5,686 images and 45,578 annotations over 6 classes. Hand-raising had the best class mAP50, 0.854 — [Springer Discover AI 2025, improved YOLOv11](https://link.springer.com/article/10.1007/s44163-025-00492-6) (from a search snippet)
- PLA-YOLO11n (Sensors 2025): "raising hands" AP 0.822, overall mAP@0.5 0.721 — [Sensors 25(17):5386](https://doi.org/10.3390/s25175386) (search snippet)
- SCB-YOLO (Scientific Reports 2026): "Raise hand" mAP 80.0% on the elementary subset SCB-Dataset3-S, overall 0.718 — [Sci Rep 2026](https://www.nature.com/articles/s41598-026-43753-9) (search snippet)
- A 2024 fusion model on online-teaching footage: hand-raising accuracy only 74.8% (recall 86.2%) versus 97.3% for upright sitting — [J. Intelligent Systems, DOI 10.1515/JISYS-2023-0236](https://unpaywall.org/10.1515%2FJISYS-2023-0236) (search snippet)
- Hybrid ViT classroom model (Sci Rep 2026): hand-raising F1 92.4%. Misclassifications often involve overlapping actions, e.g. hand-raising predicted as "speaking" — [Sci Rep 2026, s41598-026-36633-9](https://www.nature.com/articles/s41598-026-36633-9) (search snippet)

**Pose / skeleton approaches**
- Sensors 2021, pose + person-box fusion. OpenPose 18 joints feed a 26-dim feature: 16 normalised joint coordinates, 5 joint distances, 5 bone angles. Eyes, ears, hips, knees and ankles are dropped. The classifier is a 4-layer DNN (128-64-16-4). Training: 11,500 single-person images, 4 classes including "asking" (hand raised). Fusing with YOLOv4 person boxes raised average precision about 15% and recall about 12% over skeleton-only in complex rooms. Classroom 4 skeleton-only precision was 57.6%; Classroom 5 fused precision was 90.2%. Cost: 100 ms/frame skeleton-only versus 335 ms fused — [Sensors 21(16):5314 / PMC8401214](https://pmc.ncbi.nlm.nih.gov/articles/PMC8401214/)
- The same Sensors 2021 work reports per-posture accuracies of 0.959 for hand-raising, 0.933 standing and 0.772 sitting (search snippet; these figures were not on the PMC page I read) — [Sensors 21(16):5314](https://www.mdpi.com/1424-8220/21/16/5314)
- YOLOv11-Pose keypoints + geometric features + MLP: 99.048% accuracy on 8,400 images of 4 postures including hand raising. This is static images on a controlled dataset — [Springer 2026 chapter](https://link.springer.com/chapter/10.1007/978-3-032-18138-1_17) (search snippet)
- Bühler et al. (AIED 2023, LNCS 13916): an LSTM on body-pose embeddings, "view-invariant, occlusion-robust", tested on 36 real classroom videos with 127 students (grades 5–12) and 2,442 annotated hand-raising events. F1 = 0.76. Hand-raises per student per lesson had MAE 3.76 — [ECR Hub summary](https://ecrhub.org/publications/automated-hand-raising-detection-classroom-videos-view-invariant-and-occlusion-robust); [DOI 10.1007/978-3-031-36272-9_9](https://doi.org/10.1007/978-3-031-36272-9_9)
- ST-TGR (Sensors 2024), teacher-gesture recognition: RTMPose keypoints into a GRU-style classifier (MoGRU), 93.5% accuracy. This is the closest published analogue to "YOLO-pose + tiny GRU" — [Sensors 24(8):2589 / PMC11054209](https://pmc.ncbi.nlm.nih.gov/articles/PMC11054209/) (search snippet)
- Zhou et al. (ACML 2018): an improved R-FCN hand-raise detector, plus PAF pose with "scale search", plus heuristic matching of raised hands to students. 83% accuracy identifying who raised a hand, on 6 real classroom videos — [PMLR v95 zhou18a](https://proceedings.mlr.press/v95/zhou18a.html)

**Video / temporal models**
- BK-SAD (Vietnam, HUST, 2023), 3 classes. Overall accuracy: ConvNet+LSTM 93.7%, Two-Stream (RGB + optical flow) 94.3%. Two-Stream per-class: hand-raising 91.5%, doze 85.3%, normal 97.0%. Hand-raising true-class row in the confusion matrix (counts): 13,259 correct, 899 as doze, 379 as normal. False positives into hand-raising: 1,187 from doze, 1,074 from normal — [BK-SAD paper, JST: Smart Systems and Devices 33(3) 2023](https://storage.googleapis.com/jst-journals/articles/ssad/168/23021_1.3m.pdf) (PDF text extracted); dataset at [visedu.vn/en/bk-sad-dataset](https://visedu.vn/en/bk-sad-dataset)
- Le et al. (Vietnam J. Comp. Sci. 2023), two stages. Stage 1 detects the static hand-raising posture with a relative-position-aware non-local network: +7.68 / +5.76 / +0.35 mAP over Faster-RCNN / Libra-RCNN / Libra-RCNN+RDA. Stage 2 uses detection and tracking across consecutive frames to recover detections lost to occlusion and decide at the event level. Results: 90.0% frame-wise accuracy, 84.4% temporal IoU, 84.3% Levenshtein score — [DOAJ listing, DOI 10.1142/S2196888822500397](https://doaj.org/article/c1b6a16aaf4d4cb98eb529d0529a58cc)
- SAV dataset (2024): 4,324 three-second clips from 758 classrooms, 15 multi-label actions including raising hand, from fixed surveillance-style cameras. Overall mAP: proposed ViT method 67.90%, VideoMAE 66.56%, MViTv2 45.11%, SlowFast-R50 34.97%, YOWOv2 24.99%. No per-class raising-hand number appears in the text — [arXiv 2409.00926](https://arxiv.org/html/2409.00926v2)

**Small / back-row students**
- SAV: most boxes cover under 1% of the frame. Existing methods "focus on large front-row students and neglect smaller back-row students". Grad-CAM shows VideoMAE attending to front rows and background — [arXiv 2409.00926](https://arxiv.org/html/2409.00926v2)
- SCB authors: a scale variation of about 25× between rows. As written, front row is ~40×40 px and back row ~200×200 px, which looks inverted (probably a typo). They used CrowdHuman-trained YOLOv7 weights for person detection in dense rooms, with only qualitative evidence for back rows. BRA attention and Wise-IoU are claimed to help with "small objects far back in the classroom" (Grad-CAM, qualitative) — [arXiv 2305.07825v2](https://arxiv.org/html/2305.07825v2); [arXiv 2306.03318](https://arxiv.org/html/2306.03318v2)
- Zhou 2018: "low resolution of the back row for keypoints detection", addressed by multi-scale "scale search" in pose estimation — [PMLR v95](https://proceedings.mlr.press/v95/zhou18a.html)
- YOLOv8n_BT adds an occlusion block and a "Tiny Object Detection Layer" for back-row students. YOLOv8-MHSA (MDPI Information 2025) says plain YOLOv8 misses partly hidden back-row students — [ResearchGate YOLOv8n_BT](https://www.researchgate.net/publication/378818281_YOLOv8n_BT_Research_on_Classroom_Learning_Behavior_Recognition_Algorithm_Based_on_Improved_YOLOv8n); [Information 16(11):934](https://doi.org/10.3390/info16110934) (search snippets)

**VLMs**
- A zero-shot VLM benchmark (CV4Edu @ CVPR 2026) scored scene-level engagement labels derived from SCB (1,168 images), not per-person hand-raise detection. Accuracy: GPT-4o 67.9%, CLIP 67.3%, Qwen2.5-VL-7B 64.9%, LLaVA-1.5-7B (4-bit, about 4 GB) 49.2%. Accuracy is highly prompt-sensitive: CLIP's SCB accuracy swings 52.9 points across prompts. GPT-4o gives the same answer on all three runs for only 68% of images. No hand-raise metrics or latency are reported — [arXiv 2606.21861](https://arxiv.org/html/2606.21861)
- In other work, a VLM (Qwen2.5-VL-7B) is used as an interpretation layer on top of YOLOv11 detections, not as the detector — [ACM DL 10.1145/3785987.3786101](https://dl.acm.org/doi/10.1145/3785987.3786101) (search snippet)

### Inferences
- On real, uncontrolled footage, expect performance well below lab numbers. The only real-classroom, event-level pose+LSTM result is F1 0.76. Controlled datasets (BK-SAD acted repetitions, single-person crops) give 90–99%. A restaurant demo with acted raises will look like the controlled case; live footage will look like the Bühler case.
- The evidence favours per-frame detection or pose plus tracking-based temporal persistence (Le et al.; SCB multi-model fusion with DeepSort) over a heavy end-to-end video model. End-to-end video models (SlowFast, VideoMAE) struggle with small, dense subjects (SAV) and are too heavy for a 4 GB GPU.
- A tiny GRU over 1–1.5 s of keypoints is in line with ST-TGR (RTMPose + GRU, 93.5%) and Bühler (LSTM on pose). But no source shows it beating a well-tuned rule plus duration hold on hand-raise specifically. Treat it as a false-positive filter after the rule gate, not a replacement for it.
- VLMs are not a viable primary detector here: no per-person hand-raise numbers, high prompt sensitivity, low self-consistency, and 7B models need about 4 GB just in 4-bit. At most, use one as an occasional off-line or cloud verifier of a crop.

### Gaps
- No same-dataset head-to-head of single-frame versus sequence models for hand-raise.
- Per-class hand-raise numbers for SAV, and the Bühler paper's pose estimator and window length, were not accessible (abstract-level only).
- BK-SAD numbers are two-stream RGB/flow, not skeleton, despite the paper extracting skeletons with BK-Pose. Download terms on visedu.vn were not checked.
- The Sci Rep 2026, PLA-YOLO11n and Springer 2026 figures come from search snippets; I did not verify them in the full text.

## Q2. Restaurant waiter-call, retail, hospital and meeting hand-raise systems: how they work and what they claim

### Takeaway
I found no shipped restaurant product with a published accuracy or latency for "raise hand to call waiter" from CCTV. Patents and adjacent products converge on one recipe:
- detect the hand in a region above the head, scaled by face or head size, or wrist above shoulder from pose;
- require the raise to persist for N frames or seconds;
- exclude registered staff;
- keep the request open until a staff member is observed at the table.

### Cited Findings
- **Canon US10984249B2** (priority Jan 2018, granted Apr 2021, restaurant embodiment), the closest match to Easy FnB.
  - Raised-hand rule: a hand region is computed from face width w, face height h and face centre, using coefficients α, β1, β2 that mark where a hand would be if a person with that face raised it. A hand detected in that region means "raising hand". Hand detection can be ML-based or skin-colour.
  - Staff exclusion: a registered-person database of face features, uniform appearance or beacon. Matches are staff and never support targets.
  - Request lifecycle: the requester becomes a "watched person" and is tracked until support completes. Support completes when registered staff stay in the person's surrounding region for a set time, or a support action is detected (taking an order, a gesture). If staff leave without serving, the request stays open.
  - Display and grouping: a back-of-house display shows tables needing help, ordered by priority. One request can cover a whole table group.
  - No accuracy reported — [Google Patents US10984249B2](https://patents.google.com/patent/US10984249B2/en)
- US app. 20210110144, "Method and system for detecting customers needing attention via gesture recognition": restaurants can use existing security cameras; customer movement is matched to predetermined gestures and a notification with location is sent. Full text was blocked (403), so this is from a snippet only — [Justia 20210110144](https://patents.justia.com/patent/20210110144)
- A search snippet describes a related filing (numbered 11984249 in the snippet; unverified) that infers staff are attending a customer from the staff arm-bending angle and held objects (terminal, order sheet) — [USPTO 10984249 PDF, scanned](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10984249) (snippet; could not OCR)
- Everybot (Korean serving-robot maker) filed patents in Feb 2024 for calling a serving robot with a gesture, "like raising a hand to call a waiter". It claims recognition accuracy more than 2× its previous generation. Marketing claim, no absolute numbers — [Asia Economy (CN), Feb 2024](https://view.asiae.co.kr/cn/article/2024021309535598984)
- AxxonSoft VMS, "Hands up" detector (commercial video analytics). Built on pose detection; fires when a person with one or both hands raised is in a zone. Settings: minimum consecutive frames (2–20) and mode (both hands, one hand, left only, right only, left-or-right), plus detection and skip zones. No accuracy claims — [AxxonSoft docs](https://docs.axxonsoft.com/confluence/x/6NQIDg)
- Hospital: the "Video monitoring system" patent family describes skeleton-based patient monitoring where e.g. "raising a hand for more than five seconds may initiate a nurse call". No accuracy published — [USPTO 9204823](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/9204823) (search snippet)
- A robot patent notes that a partial raise may not clear the threshold, so the system "may erroneously estimate that the person does not raise his/her hand" — [USPTO 9990540](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/9990540) (search snippet)
- Google Meet hand-raise gesture (Nov 2023), a meeting product. Guidance: camera on, hand visible and "away from your face and body". Off by default. Doesn't trigger while you are the active speaker. Lowering requires a click. Press reports a loading icon, then the raise triggers "after a few seconds", i.e. a hold-to-confirm debounce. No accuracy published — [Google Workspace Updates](https://workspaceupdates.googleblog.com/2023/11/google-meet-hand-raise-gesture-detection.html); [Tom's Guide](https://tomsguide.com/news/google-meet-can-now-recognize-when-you-raise-your-hand-via-ai-heres-how-it-works)
- An open-source MediaPipe gesture-control prototype for video calls requires each gesture to be held steady for 650 ms before it fires — [OpenVidu blog, Aug 2026](https://openvidu.io/blog/2026/08/11/control-video-calls-with-gestures-free-ai/)
- Restaurant CV deployments that are documented publicly do table-state monitoring (e.g. Available → Waiting for Waiter via a rule engine; tables dirty but unserved), not hand-raise recognition — [Sciforce / Medium](https://medium.com/sciforce/optimizing-multi-zone-restaurant-service-with-computer-vision-for-hospitality-3316f009ec5b); [Restaurant Technology News 2025](https://restauranttechnologynews.com/2025/06/how-restaurants-are-building-invisible-support-teams-with-ai-chatbots-and-smart-cameras/)
- Hikvision/Dahua classroom-analysis cameras: I found no published hand-raise accuracy (search returned only academic papers).

### Inferences
- Three design ideas from the Canon patent transfer directly: (1) hand region relative to face or head size, which is scale-invariant across near and far tables; (2) staff exclusion by uniform appearance; (3) a request lifecycle closed when staff dwell at the table. The last also removes duplicate alerts.
- The usual "hold" time in real systems ranges from about 0.65 s (MediaPipe demo) through "a few seconds" (Meet) to 5 s (nurse call). For a restaurant, a 0.7–1.5 s hold plus a per-track cooldown is consistent with practice.
- Because no restaurant product publishes numbers, the demo can honestly claim novelty in the restaurant setting. Any accuracy claim must come from the team's own test clips.

### Gaps
- No commercial restaurant, retail or hospital system with independently verified precision, recall or latency.
- The Justia 20210110144 and 11984249 details could not be read (403 error, scanned PDF).

## Q3. Which features matter (wrist height, elbow angle, extension, duration, motion, hand openness), and can hand keypoints separate "open hand raised" from "touching hair"?

### Takeaway
Published systems lean on three cues: wrist or hand position above the head or face, normalised by face size (Canon) or by shoulder/head joints (pose rules); a minimum hold duration (frames or seconds); and, in learned classifiers, joint distances and bone angles (elbow and shoulder angles). I found no paper that uses 21-point hand keypoints (RTMW or MediaPipe hands) to separate a raised open hand from touching hair in CCTV-resolution footage.

### Cited Findings
- Canon: the hand-position region is defined relative to face width, height and centre, via coefficients — [US10984249B2](https://patents.google.com/patent/US10984249B2/en)
- Sensors 2021: the feature vector is 16 normalised joint coordinates + 5 joint distances + 5 bone angles. Lower-body joints (hips, knees, ankles), eyes and ears are deliberately dropped. This matters for seated people occluded by tables — [PMC8401214](https://pmc.ncbi.nlm.nih.gov/articles/PMC8401214/)
- YOLOv11-Pose + "geometric features" + MLP gets 99% on controlled images, which shows simple geometry suffices when keypoints are clean — [Springer 2026](https://link.springer.com/chapter/10.1007/978-3-032-18138-1_17) (snippet)
- AxxonSoft and the hospital patent rely on pose plus temporal persistence (minimum 2–20 frames; >5 s) — [AxxonSoft](https://docs.axxonsoft.com/confluence/x/6NQIDg); [USPTO 9204823](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/9204823)
- Raising an arm distorts pose estimation itself ("motion distortion"). Zhou 2018 added a directional-vector weight metric for limb connections to counter it — [PMLR v95](https://proceedings.mlr.press/v95/zhou18a.html)
- A Japanese hand-raise patent: a hand above the head can be confused with the head location (fingertip versus head). It separates them by noting the head is not at the end of the arm ellipse the way a fingertip is — [JP6728865B2](https://patents.google.com/patent/JP6728865B2/en) (search snippet)
- YOLOv7-BRA qualitative examples show it does not mistake a hand resting on the head for a raised hand, whereas baseline YOLOv7 "would misidentify other actions as raising hands". There is no quantitative breakdown — [arXiv 2305.07825v2](https://arxiv.org/html/2305.07825v2)
- RTMW (whole-body: 133 keypoints including 2×21 hand points) reaches 70.2 mAP on COCO-WholeBody (RTMW-l). The authors say feature resolution is crucial for hand and face accuracy, a concern for small CCTV subjects. They also say MediaPipe's accuracy is "not entirely satisfactory" — [arXiv 2407.08634](https://arxiv.org/html/2407.08634v1)
- A micro-gesture benchmark has separate classes for "touching the back of the head or hair" and "touching the forehead", i.e. self-touch is treated as its own category, not a hand-raise variant — [arXiv 2608.14854 (Zero-MELO)](https://arxiv.org/pdf/2608.14854) (search snippet)
- Google Meet asks users to keep the hand "away from your face and body". This is an implicit acknowledgement that hand-near-face is the main confounder — [Google Workspace Updates](https://workspaceupdates.googleblog.com/2023/11/google-meet-hand-raise-gesture-detection.html)

### Inferences
- With COCO-17 only, the most discriminative cues against hair-touching or head-scratching are:
  - (a) wrist clearly above the top of the head, e.g. wrist_y < nose_y − k·(shoulder width or head size), not just above the shoulder;
  - (b) wrist horizontally displaced from the head centre (hand away from face, Meet's guidance);
  - (c) elbow extension angle (straight-ish arm when raising; sharply flexed with the wrist near the head when touching hair or scratching);
  - (d) hold duration and low wrist jitter, versus the oscillatory motion of scratching or waving.
  These are inferences combining the Canon, Meet, Sensors 2021 and JP patent evidence, not validated results.
- Hand keypoints (RTMW) are likely unreliable for small or far customers, since resolution is the authors' own stated bottleneck. If used, apply them only to near or large tracks (e.g. person box height above a threshold) as an optional "open palm" verifier.

### Gaps
- No published study quantifies hand-openness or 21-point hand features for raise-versus-self-touch in surveillance video.
- No published confusion numbers for drinking, pointing, stretching, waving to a friend, or staff carrying trays specifically.

## Q4. Documented failure modes and fixes

### Takeaway
The recurring failures are small or low-resolution far subjects, occlusion (desks, other people), dense scenes causing wrong skeleton joins, similar-looking actions, and viewpoint and angle changes. The documented fixes are:
- person-box/skeleton fusion;
- multi-scale or tiled inference, and a crowd-trained person detector;
- attention modules and small-object heads;
- tracking-based temporal filling;
- staff registries and zone masks.

### Cited Findings
- Wrong skeleton connections in crowds: matching joints to YOLO person boxes and deleting joints outside a person's box cut incorrect connections from 18 to 3 in one frame and raised precision and recall about 12–15%. Cost: 3.35× processing time — [PMC8401214](https://pmc.ncbi.nlm.nih.gov/articles/PMC8401214/)
- Far students and corner cameras: more bad connections; the authors suggest more cameras. Occlusion "remains unresolved"; a moving-average filter smooths corrupted keypoints — [PMC8401214](https://pmc.ncbi.nlm.nih.gov/articles/PMC8401214/)
- Occlusion causing missed frames: fixed by tracking across consecutive frames and event-level decisions — [Le et al. VJCS 2023](https://doaj.org/article/c1b6a16aaf4d4cb98eb529d0529a58cc)
- Desks and front-row students occlude hands and faces; models neglect small back-row subjects — [arXiv 2409.00926](https://arxiv.org/html/2409.00926v2)
- Other actions misidentified as hand-raising, and small hand-raises missed (YOLOv7). Fixes: BRA attention and Wise-IoU (+5.7 points precision); CrowdHuman person-detector weights for dense rooms — [arXiv 2306.03318](https://arxiv.org/html/2306.03318v2); [arXiv 2305.07825v2](https://arxiv.org/html/2305.07825v2)
- Low back-row resolution for keypoints, fixed with multi-scale "scale search"; arm-raise pose distortion, fixed with a modified limb-connection weighting — [PMLR v95](https://proceedings.mlr.press/v95/zhou18a.html)
- Low hand resolution, hand occlusion, varied backgrounds and viewpoint changes are named as the core difficulties — [DOAJ, Le et al. 2023](https://doaj.org/article/c1b6a16aaf4d4cb98eb529d0529a58cc)
- Staff versus customer: exclude registered staff (face, uniform, beacon) and close requests when staff dwell nearby — [US10984249B2](https://patents.google.com/patent/US10984249B2/en)
- Partial or low raises are missed by threshold rules — [USPTO 9990540](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/9990540) (snippet)
- Single-camera validation doesn't transfer: an open-source YOLOv8 hand-raise detector notes it was validated only on one fixed front camera and warns of lower accuracy at other angles or with occlusion — [GitHub Symooomzip](https://github.com/Symooomzip/student-behavior-detection-yolov8) (snippet)
- In BK-SAD, the biggest hand-raise false-positive sources were doze (1,187) and normal (1,074) frames, about 14.6% of all hand-raise predictions. This shows ordinary postures leak into the class even at 94% overall accuracy — [BK-SAD PDF](https://storage.googleapis.com/jst-journals/articles/ssad/168/23021_1.3m.pdf)

### Inferences
For the Easy FnB setup (ceiling CCTV, seated customers, tables hiding the lower body):
- drop the lower-body joints;
- require head and shoulder confidence and gate on upper-body keypoint confidence;
- tile or upscale crops of small or far tracks before pose;
- use ByteTrack plus a per-track state machine (raise must persist N of M frames; brief occlusion gaps tolerated);
- mask staff by uniform colour or a "standing and moving" heuristic, and mask aisle and kitchen zones;
- treat partly out-of-frame people as low-confidence (no alert unless head, shoulder and wrist are all visible).

### Gaps
- No paper measures the effect of steep ceiling-angle foreshortening on wrist-above-shoulder rules. Classroom cameras are typically front, side or back, at moderate height.

## Q5. Data collection and labelling protocols, and how many samples were needed

### Takeaway
Published datasets range from a few thousand annotated images (SCB, about 4–5.7k images) to thousands of short clips (BK-SAD about 13k clips, SAV 4.3k clips). The best-documented protocol (BK-SAD, Vietnam) used multiple corner cameras, scripted repetitions, position swapping and per-frame CVAT labels. No paper reports a learning curve showing how few samples suffice for a pose-sequence hand-raise classifier.

### Cited Findings
- **BK-SAD (Chu Van An Secondary School, Hanoi)**
  - Setup: 10 classes of ≥30 students each, recorded for 20 minutes per class. At least four 3MP cameras at top, left, right and back corners.
  - Protocol: 100 repetitions per action (hand raising, doze-off, normal), 5 s per recording. Students were systematically swapped across positions and action order was randomised to avoid bias. "Normal" clips were captured concurrently with the target actions.
  - Labelling: long videos cut into 10 s / 250-frame clips, giving 1,200 CVAT tasks. Each frame got a per-student box and activity label. One task took about half a day for one person; 10 people needed 2 months. Inter-annotator agreement 0.92.
  - Keypoints: BK-Pose extracted 18 keypoints per student from the manual boxes.
  - Splits: hand-raising 1,996 train / 727 test; doze 1,217 / 522; normal 6,018 / 2,579.
  — [BK-SAD PDF](https://storage.googleapis.com/jst-journals/articles/ssad/168/23021_1.3m.pdf)
- Bühler et al.: 36 real lesson videos, 127 students, 2,442 hand-raise events annotated manually (event level) — [ECR Hub](https://ecrhub.org/publications/automated-hand-raising-detection-classroom-videos-view-invariant-and-occlusion-robust)
- SAV: 4,324 three-second clips from 758 classrooms (public videos), labelled on the middle keyframe with 1–5 labels per person. The authors note "accurate annotation of actions requires temporal context" — [arXiv 2409.00926](https://arxiv.org/html/2409.00926v2)
- SCB: 4,003 images / 11,248 labels (hand-raising focus). SCB-Dataset3: 5,686 images / 45,578 labels, 6 classes. Licence: academic, personal and non-commercial use only; distributed via Baidu Netdisk and Hugging Face (wintonYF/SCB-Dataset) — [arXiv 2304.02488](https://arxiv.org/html/2304.02488v2); [GitHub Whiffe/SCB-dataset](https://github.com/Whiffe/SCB-dataset)
- Sensors 2021: 11,500 single-person images over 4 classes (70/30 split). Tested on six classrooms × 300 images, front and corner cameras — [PMC8401214](https://pmc.ncbi.nlm.nih.gov/articles/PMC8401214/)
- YOLOv11-Pose + MLP: 8,400 images, 4 postures — [Springer 2026](https://link.springer.com/chapter/10.1007/978-3-032-18138-1_17) (snippet)
- SAV code and data are released at github.com/Ritatanz/SAV; the dataset licence is not stated — [arXiv 2409.00926](https://arxiv.org/html/2409.00926v2)

### Inferences
- BK-SAD's protocol scales down well for a 2-person, 9-day hackathon:
  - a few actors who rotate seats across tables near and far from the camera;
  - scripted repetitions of the positive class and of each confuser (hair-touch, scratching, drinking, pointing, stretching, waving to a friend, staff carrying trays), in randomised order, with "normal" captured in between;
  - clip-level or start/end-frame labels rather than per-frame boxes, since the tracker supplies boxes.
- Even 100 repetitions per action per setup is a reasonable target given BK-SAD used that number.
- Because Bühler shows real-world F1 drops to about 0.76, hold out at least one full camera view or seating position for testing to avoid over-optimistic numbers.
- BK-SAD and SCB (non-commercial) could be used for pre-training or sanity checks under hackathon use. They differ in viewpoint (classroom front, side, back) from a restaurant ceiling camera.

### Gaps
- No source gives a sample-size and accuracy curve for skeleton-sequence hand-raise classifiers.
- No restaurant-specific hand-raise dataset was found.

## Q6. Most effective approach for seated, occluded, high-angle scenes (synthesis)

### Takeaway
The evidence supports the team's planned hybrid design:
1. person detection with a crowd-robust detector;
2. upper-body pose, gated by keypoint confidence;
3. a rule gate: wrist above the head or shoulder, normalised by head or shoulder size (Canon-style), with the arm extended and the hand away from the face;
4. a per-track temporal hold of about 0.7–1.5 s with occlusion-gap tolerance (Le et al., AxxonSoft, Meet, MediaPipe);
5. a lightweight second-stage verifier (crop classifier and/or tiny GRU) trained on confusers;
6. staff exclusion plus a request lifecycle closed on staff arrival (Canon).

### Cited Findings
- The fusion of person detection and pose improves precision and recall over pose alone in cluttered rooms — [PMC8401214](https://pmc.ncbi.nlm.nih.gov/articles/PMC8401214/)
- Tracking-based event detection recovers occluded frames, giving 90% frame-wise accuracy and 84.4% temporal IoU — [Le et al. 2023](https://doaj.org/article/c1b6a16aaf4d4cb98eb529d0529a58cc)
- Pose plus LSTM in real classrooms gives F1 0.76, the realistic ceiling for an uncontrolled environment without per-site data — [Bühler et al. 2023](https://doi.org/10.1007/978-3-031-36272-9_9)
- Commercial pose "hands up" detectors use rule plus minimum-frame persistence — [AxxonSoft](https://docs.axxonsoft.com/confluence/x/6NQIDg)
- Restaurant patent: face-scaled hand region, staff registry, request closed on staff dwell — [US10984249B2](https://patents.google.com/patent/US10984249B2/en)
- A single-frame YOLO "hand-raising" class reaches about 0.80–0.87 AP@0.5 on SCB but confuses similar actions and misses small hands without architectural fixes — [arXiv 2306.03318](https://arxiv.org/html/2306.03318v2); [arXiv 2305.07825](https://arxiv.org/abs/2305.07825)

### Inferences
- For a 4 GB RTX 3050 or CPU, use YOLO-pose (nano or small) + ByteTrack + rules + a tiny GRU or MLP over a 1–1.5 s keypoint window. This is consistent with ST-TGR and Bühler and far cheaper than video transformers (SAV) or VLMs.
- The crop classifier is most useful as a confuser rejector (hair-touch, drinking, tray-carrying) on near or medium tracks. Far tracks should rely on keypoints plus duration.
- Report the demo with event-level metrics (alerts correct, missed, false per hour) rather than mAP, mirroring Le et al.'s event-level evaluation and Bühler's per-lesson counts.
