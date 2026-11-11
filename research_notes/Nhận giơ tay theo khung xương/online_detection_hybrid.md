# Online (streaming) action detection, early gesture spotting, and hybrid RGB+pose — relevance to a <0.5 s, near-zero-false-alarm hand-raise alert (Easy FnB)

Scope note: research done 5 Nov 2026. Benchmarks for online action detection (OAD) are dominated by RGB/flow-feature methods on THUMOS'14/TVSeries/EPIC; I found **no dedicated 2024–2026 skeleton-only online-detection paper on PKU-MMD/OAD**. The most transferable evidence for this project is (a) the OAD training insights (train/inference mismatch, recurrent state), (b) the gesture-spotting "detector gate → classifier → single-time activation" pattern, (c) keyword-spotting false-alarm-per-hour calibration practice, and (d) RGB+skeleton score-level fusion under occlusion.

## Q1. State of the art in online action detection 2024–2026: which architecture choices matter, and which are light enough for CPU / 4 GB GPU?

### Takeaway
Top THUMOS'14 numbers have plateaued around 71–73% per-frame mAP (CMeRT CVPR 2025: 73.2; JOADAA 72.6; MiniROAD 71.8), and a minimal GRU (MiniROAD) matches the big long/short-memory transformers at a tiny fraction of the compute. The main lever identified by both MiniROAD and CMeRT is fixing the **mismatch between how the model is trained (outputs at all time steps / short-memory of varying length) and how it is used at inference (only the latest frame, full context)**, not architectural size. Long memory (128–256 s) matters for THUMOS-style sports/cooking video, not for a 1–2 s gesture.

### Cited Findings
- CMeRT (Pang, Sener, Yao, CVPR 2025) Table 2, THUMOS'14 mAP: LSTR 69.5, GateHUB 70.7, TeSTra 71.2, MAT 71.6, MAT-rw 71.7, JOADAA ("JOAAD") 72.6, **CMeRT 73.2**; also CrossTask (CMeRT 35.9 vs MAT 33.9) and EPIC-Kitchens-100 action top-5 recall (CMeRT 27.6 vs MAT 26.3). — [CMeRT arXiv HTML](https://arxiv.org/html/2503.18359v1); [CVF page](https://openaccess.thecvf.com/content/CVPR2025/html/Pang_Context-Enhanced_Memory-Refined_Transformer_for_Online_Action_Detection_CVPR_2025_paper.html)
- CMeRT efficiency table (THUMOS'14, features pre-extracted): LSTR 58.8 params / 4.70 GFLOPs / 140.8 FPS; TeSTra 58.9 / 4.72 / 135.1 FPS; MAT 107.4 / 6.62 / 102.0 FPS; CMeRT 94.5 / 5.36 / 126.6 FPS (133.3 FPS with cached compression). Param units not stated on the page (presumably millions). — [CMeRT arXiv HTML](https://arxiv.org/html/2503.18359v1)
- CMeRT memory settings for THUMOS'14: long memory 256 s, short memory 4 s, anticipation 2 s, near-past 0.5 s; inputs are two-stream features at 4 FPS (ResNet-50 RGB + BN-Inception optical flow). — [CMeRT arXiv HTML](https://arxiv.org/html/2503.18359v1)
- CMeRT's key insight: "The training uses varying lengths of short-term memory, while inference relies on a full-length short-term memory"; early frames in the short-term window get little context during training and learn poorly; the authors also argue MAT's anticipation branch leaks non-causal future information. MAT evaluated in a "stream" setting drops to 58.1 mAP (vs 71.6). — [CMeRT arXiv HTML](https://arxiv.org/html/2503.18359v1)
- MiniROAD (ICCV 2023, Apache-2.0 code): THUMOS'14 71.8 mAP (Kinetics features), 68.4 (nv_kinetics), TVSeries 89.6 mcAP, FineAction 37.1 mAP. — [MiniROAD GitHub](https://github.com/jbistanbul/MiniROAD)
- MiniROAD claims it needs "only about 0.4% of the computational power" of the previous SOTA while performing equal or better; the authors attribute RNNs' previous under-performance to the training/inference discrepancy and fix it by **weighting the loss at each time step** (non-uniform loss weighting). — [MiniROAD ICCV 2023 paper (via search excerpt)](https://openaccess.thecvf.com/content/ICCV2023/papers/An_MiniROAD_Minimal_RNN_Framework_for_Online_Action_Detection_ICCV_2023_paper.pdf); [project page](https://sites.google.com/view/joungbinan/projects/miniroad)
- A third-party benchmark page lists MiniROAD at 15.8 MFLOPs per prediction on THUMOS'14 (not verified against the paper). — [PapersWithCode mirror](https://astro.paperswithcode.com/paper/miniroad-minimal-rnn-framework-for-online)
- TLS-RWKV (Neural Processing Letters, 2024): an RWKV (linear-attention recurrent) model with temporal label smoothing for real-time OAD reports 71.8% mAP THUMOS'14 and 89.7% mcAP TVSeries. — [Springer](https://link.springer.com/article/10.1007/s11063-024-11540-0)
- MALT (2024) multi-scale action learning transformer reports gains on THUMOS'14 and TVSeries (absolute values not retrieved). — [arXiv 2405.20892](https://arxiv.org/pdf/2405.20892)
- SSM "State-Specific Model" (arXiv 2510.10682, v3 Oct 2026, not peer-reviewed): compresses memory into representative states + graph reasoning + cross-temporal interaction; a search snippet reports 72.1% (Kinetics) / 71.8% (ANet) on THUMOS'14 — I could not confirm from the paper itself. — [arXiv 2510.10682](https://arxiv.org/abs/2510.10682)
- LSTR (2021) baseline improved prior SOTA on THUMOS'14 by 3.7/2.4 mAP and TVSeries by 2.8/2.7 cAP (ANet/Kinetics features). — [LSTR arXiv](https://arxiv.org/pdf/2107.03377)

### Inferences
- All of these benchmark numbers are for **heads on top of pre-extracted two-stream (RGB + optical flow) features at 4 FPS**; the "100–140 FPS" figures exclude backbone and flow extraction, which would dominate cost on an RTX 3050 / CPU. For Easy FnB, the YOLO26-pose keypoints and PE-Core probe score already *are* the per-frame features, so the OAD "head" is the only extra cost — a GRU of the MiniROAD type over ~17×3 keypoint inputs is effectively free (sub-millisecond) on CPU.
- Long/short memory transformers (LSTR, TeSTra, MAT, CMeRT; 4–256 s windows) solve problems of long untrimmed video context that do not exist for a 1–2 s hand raise; the planned **tiny GRU over 1–1.5 s** is consistent with the best-efficiency end of the SOTA (MiniROAD).
- Practical lesson to copy from MiniROAD/CMeRT: if the GRU is trained on clips and supervised at every step, the early steps (little context) are noisy targets; either (a) train with the same fixed window used at inference and supervise only the last frame (sliding-window classifier — no mismatch by construction), or (b) train a stateful GRU on long continuous per-track sequences and down-weight the loss on the first N steps (MiniROAD-style).
- Recurrent state vs sliding window at this scale: a sliding window of 30–45 frames re-run each frame costs almost nothing for keypoint input and is easier to reset when a track ID switches; a stateful GRU is cheaper but needs explicit reset on track loss/ID switch. Both are fine compute-wise; sliding window is the lower-risk choice for a 9-day hackathon (inference, not sourced).
- "MAT-stream 58.1 vs MAT 71.6" is a warning that reported OAD numbers can depend on evaluation protocol details; always evaluate the alert system on continuous footage exactly as deployed.

### Gaps
- Could not retrieve MiniROAD's own GFLOPs/params/FPS table (paper PDF returned 403) — only the 0.4% compute claim and an unverified 15.8 MFLOPs figure.
- No verified TVSeries mcAP for 2025–2026 methods; CMeRT does not report TVSeries.
- No 2024–2026 OAD paper found that reports **latency-to-detection in seconds** or **false alarms per hour**; standard OAD metrics (per-frame mAP, cAP) do not measure either directly.

## Q2. Skeleton-based online detection and continuous gesture spotting: best methods and how they segment start/end

### Takeaway
Skeleton-specific online detection is a thin literature: the reference design is still JCR-RNN (ECCV 2016, OAD dataset) with joint frame-wise classification + start/end regression; recent skeleton "foundation" models evaluate PKU-MMD detection offline. The most directly reusable design is from continuous hand-gesture spotting (Köpüklü et al. 2019): a cheap, high-recall **detector** gates an expensive **classifier**, detector outputs are median-filtered, classifier scores are weighted to ignore the ambiguous "preparation" phase, and a **single-time activation** fires once per gesture — essentially the Easy FnB pipeline, with well-documented parameters.

### Cited Findings
- JCR-RNN (Li et al., ECCV 2016) detects actions in streaming skeleton data "as early as possible", trained end-to-end on frame-wise classification plus temporal-localization regression; it forecasts start and end of actions; introduced the OAD dataset and evaluated with F1, Start Localization Score (SL-Score) and End Localization Score (EL-Score) vs sliding-window SVM baselines. — [arXiv 1604.05633](https://ar5iv.labs.arxiv.org/html/1604.05633); [PapersWithCode](https://astro.paperswithcode.com/paper/online-human-action-detection-using-joint)
- PKU-MMD (2017) is a large continuous multi-modal benchmark (~20,000 action instances) built partly to support online detection. — [PKU-MMD arXiv](https://arxiv.org/pdf/1703.07475)
- USDRL skeleton foundation model (arXiv 2508.12586): PKU-MMD I x-sub detection mAP_a 75.7% / mAP_v 74.9% at overlap 0.5 (DSTE encoder), but detection is **offline** (sliding windows + post-processing); 94.9M params for the chosen 2-layer DSTE; 1.74–2.54 GFLOPs for the STTR variant. — [arXiv 2508.12586](https://arxiv.org/html/2508.12586v1)
- Köpüklü et al. "Real-time Hand Gesture Detection and Classification Using CNNs" (FG 2019): detector = ResNet-10 3D-CNN with ≈862K params on 8-frame windows; classifier = ResNeXt-101 (or C3D) only activated when detector fires; detector softmax pushed into a queue of size k=4 and **median filtered** (best of mean / exp-weighted / median); classifier scores multiplied by a sigmoid weight w_j = 1/(1+exp(−0.2(j−t))), t = ⌊µ/(4s)⌋ (t=9 frames for EgoGesture µ=38.4) so decisions are made after the gesture "nucleus" because "several gestures can contain a similar preparation part"; **early detection** fires when the margin between the two top weighted-average class scores ≥ τ_early, otherwise **late detection** when detector switches off if top score ≥ τ_late = 0.15. — [arXiv 1901.10323](https://arxiv.org/abs/1901.10323) (full PDF text read)
- Same paper: Levenshtein accuracy (counts misclassifications, missed and multiple detections) 91.04% EgoGesture, 77.39% nvGesture; τ_early = 0.4 on EgoGesture gives activations **9 frames earlier on average for only 1.71% Levenshtein-accuracy loss**; speed 460 fps when only detector runs, 62 fps (ResNeXt-101) with both, Titan Xp, batch 8. — [arXiv 1901.10323](https://arxiv.org/abs/1901.10323)
- Same paper: on nvGesture the 8-frame **RGB** detector had only 70.22% recall / 80.31% precision vs **depth** 97.30% / 97.41% — appearance-only detectors were much weaker gates. — [arXiv 1901.10323](https://arxiv.org/abs/1901.10323)
- IPN Hand (ICPR 2020) benchmark evaluates continuous HGR on unsegmented streams mixing gesture and non-gesture segments, with both online detection and early detection; an extended IPN HandS adds hand-skeleton annotations (counts differ between sources: ~700K vs >800K). — [IPN Hand arXiv](https://arxiv.org/pdf/2005.02134); [GitHub](https://github.com/GibranBenitez/IPN-hand)
- A recurrent online finger-gesture spotting architecture paired with a 3D-CNN classifier ran in real time at 53 fps and improved online temporal segmentation (search excerpt). — [IPN Hand search result / ResearchGate](https://www.researchgate.net/publication/341175756_IPN_Hand_A_Video_Dataset_and_Benchmark_for_Real-Time_Continuous_Hand_Gesture_Recognition)

### Inferences
- The Easy FnB pipeline (wrist-above-shoulder rule → PE-Core crop probe → hold-time) is structurally the Köpüklü detector/classifier/single-activation design. The cheap gate should be tuned for **very high recall** (they explicitly assume "the detector should not miss any gesture"), with precision delegated to the classifier + temporal logic. A strict geometric gate (wrist above shoulder) likely causes the edge-cut miss when the shoulder/wrist keypoint is missing — consider a looser gate (e.g., wrist above nose OR elbow above shoulder OR missing-keypoint fallback to classifier-only) and let the temporal model reject.
- Use **Levenshtein-style event-level evaluation** on continuous demo footage: count missed raises, duplicate alerts per raise, and false alerts — this matches what staff experience better than per-frame AP.
- The sigmoid weighting and τ_early margin give a concrete, tunable latency/accuracy knob that can be ported to the GRU output: alert when weighted-average P(raise) − P(best confuser) ≥ τ_early.

### Gaps
- No 2024–2026 skeleton-only online detection method with reported PKU-MMD online/OAD-dataset results was found; exact SL/EL-score formulas not retrieved.
- No recent (2024–2026) continuous body-gesture spotting paper with latency numbers for "call-the-waiter" style gestures was found.

## Q3. Post-processing: hysteresis, minimum duration, smoothing, per-track state machines; latency vs false positives; calibrating at a fixed false-alarm rate per hour

### Takeaway
Practitioners use a small, standard toolkit: smooth per-frame posteriors over a short window (median or mean), fire on threshold crossing (often a margin vs the runner-up), enforce single activation + **lockout/refractory period**, and choose the threshold on held-out continuous negative footage to hit a target **false alarms per hour** (keyword spotting typically reports miss rate at 0.1–1 FA/hr). Latency is bought back by lowering the early-fire threshold, at a measurable accuracy cost.

### Cited Findings
- Max-pooling-loss LSTM keyword spotting: posteriors smoothed over a 30-frame window, fire when smoothed keyword posterior crosses threshold, **40-frame lockout** after each firing, 20-frame allowed latency window for scoring. — [arXiv 1705.02411](https://arxiv.org/pdf/1705.02411)
- Seq-to-seq keyword spotting: average of n consecutive frames (n=12 shown in ROC); main metric = false-reject rate at **0.1 false alarms per hour**. — [arXiv 1811.00348](https://arxiv.org/pdf/1811.00348)
- CRNN small-footprint KWS reports accuracy at fixed low false-alarm rates (e.g., 97.71% at 0.5 FA/hour at 5 dB SNR); other work fixes FA at a target such as 1 FA/hr. — [arXiv 1703.05390](https://arxiv.org/pdf/1703.05390v3.pdf)
- 2025 KWS review: overlapping windows can make one keyword trigger multiple times; lockout/suppression addresses duplicates; alternatives are thresholding smoothed posteriors or taking the max posterior in a sliding window. — [arXiv 2506.11169](https://arxiv.org/pdf/2506.11169)
- Gesture spotting: median filter on a queue of k=4 detector outputs "clears out most of the misclassifications in consecutive predictions"; single-time activation via τ_early margin / τ_late; τ_early=0.4 → 9 frames earlier for −1.71% accuracy. — [arXiv 1901.10323](https://arxiv.org/abs/1901.10323)
- Classroom hand-raise detection uses "the frequency of a raised hand detected in previous frames" to eliminate false positives; geometric rules such as arm slope between 45° and 135° are used for raised-hand classification. — [Hand-raiser seeking, PMLR v95](http://proceedings.mlr.press/v95/zhou18a/zhou18a.pdf); [Chiang, MVA 2013](https://www.mva-org.jp/Proceedings/2013USB/papers/04-07.pdf)
- TLS-RWKV uses temporal label smoothing for smoother online predictions; an earlier OAD paper targets "temporally smooth" OAD via cycle-consistent future anticipation. — [TLS-RWKV](https://link.springer.com/article/10.1007/s11063-024-11540-0); [arXiv 2104.08030](https://arxiv.org/html/2104.08030v1)

### Inferences
- Recommended per-track state machine (synthesis of the above, not a published spec): IDLE → CANDIDATE (gate true and smoothed score ≥ T_on) → ALERT once when CANDIDATE persists ≥ N_hold frames *or* the margin ≥ τ_early → COOLDOWN (lockout, e.g., 5–10 s per track/table) → IDLE only after score < T_off (< T_on; hysteresis) for M frames. Reset on track loss/ID switch. Use median filtering over 3–5 frames of the per-frame score before the state machine.
- At 15–30 fps, a 0.5 s budget is 7–15 frames; median-of-5 + hold of 4–6 frames fits if the classifier is confident at the gesture apex.
- Calibration recipe: record ≥1 h of continuous "negative" restaurant footage (eating, drinking, phone, hair-touching, scratching head, pointing, stretching, waving at friends) plus the positive set; sweep T_on/N_hold/τ_early; pick the lowest-latency setting with 0 false alerts on negatives (report as "0 FA in X h", and miss rate/median latency on positives). This mirrors KWS "FRR at fixed FA/hr".
- Duplicate-alert suppression (lockout per track and per table) matters as much as false alarms for staff trust.

### Gaps
- No 2024–2026 engineering write-up of a deployed vision-based hand-raise or fall alert system with published FA/hour and latency numbers was found; the KWS analogy is the best-documented methodology.

## Q4. Early action prediction from partial skeleton sequences: how early can a hand raise be recognised reliably?

### Takeaway
Generic skeleton early-recognition is weak at small observation ratios (NTU-60: ~25–28% accuracy at 10% observed, ~67–74% at 50%, ~82–85% at 100%), and gesture-spotting work explicitly delays decisions past the shared "preparation" phase. For hand raise vs confusers (hair touch, head scratch, drinking), the arm-lift onset is shared, so reliable decisions should be expected only once the distinctive "nucleus" (hand above head, arm extended, held still) is visible — the hold-time rule is effectively waiting for it.

### Cited Findings
- NTU-60 action prediction, accuracy vs observation ratio (Table VI of the USDRL foundation-model paper): USDRL-DSTE 25.5 (10%), 36.8 (20%), 54.8 (30%), 66.7 (40%), 73.6 (50%), 81.4 (70%), 85.2 (100%); P-TSL 27.8 / 35.8 / 46.3 / 58.5 / 67.4 / … / 82.0. The paper notes certain actions can be predicted within the first 10%. — [arXiv 2508.12586](https://arxiv.org/html/2508.12586v1)
- Skeleton early-prediction methods in 2024–2025 include adversarial GCN (features of partial sequences pushed toward full-sequence features; SOTA at some observation ratios) and teacher–student TS-GCN (APSIPA 2025). — [Adversarial GCN, JCST](https://link.springer.com/article/10.1007/s11390-023-2638-7); [APSIPA 2025](https://apsipa.org/proceedings/2025/papers/APSIPA2025_P207.pdf)
- Gesture spotting: "several gestures can contain a similar preparation part which creates an ambiguity at the beginning of the gestures"; weighting the decision toward the nucleus fixed this; early detection 9 frames earlier on average at τ_early=0.4 cost 1.71% accuracy. — [arXiv 1901.10323](https://arxiv.org/abs/1901.10323)
- SASI (2026) studies sub-action semantics for robust early action recognition in human–robot interaction (details not retrieved). — [arXiv 2604.27508](https://arxiv.org/pdf/2604.27508)

### Inferences
- A natural raise takes roughly 0.3–0.6 s from rest to apex (estimate, not sourced); with alert budget ~0.5 s from apex, the practical target is "alert within ~0.3–0.5 s after the hand reaches the apex and is held", not "predict during the lift".
- Useful discriminative features for a tiny GRU (inference): wrist height relative to head top/nose normalized by shoulder width, elbow angle (extended vs bent near head), wrist velocity → near-zero (held), wrist–head distance (hair touch/scratch keep the hand on/near the head), hand-object/mouth proximity (drinking), and duration of the static apex. Pointing is mostly horizontal; stretching is usually bilateral and brief.
- Because NTU-style early prediction is a 60-class problem, binary raise-vs-confuser accuracy should be higher at equal observation; but no direct evidence was found.

### Gaps
- No paper found that measures early recognition specifically for hand raising or "call the waiter" gestures, or reports typical raise durations.

## Q5. Hybrid RGB+pose (RGBPoseConv3D, two-stream late fusion, feeding image-classifier scores into the temporal model): gain vs cost, especially when keypoints are unreliable

### Takeaway
Fusing RGB and skeleton consistently beats either alone, and the gain is largest when skeletons are degraded; the cheapest effective form is **score/probability-level late fusion** (averaging log-probs or a tiny learned head), which costs nothing extra if the RGB crop classifier is already running. Heavy joint models (RGBPoseConv3D) improve accuracy on NTU (≈97.0% vs 94.1% pose-only) but are 3D-CNN two-pathway models unsuited to a shared 4 GB GPU / CPU in a 9-day timeline.

### Cited Findings
- PoseConv3D (Duan et al., CVPR 2022) uses 3D heatmap volumes from 2D poses; claimed more robust to pose-estimation noise and better cross-dataset than GCNs; NTU60-XSub pose-only 94.1% (J+L) vs MS-G3D++ 92.2%; **RGBPoseConv3D 97.0% on NTU60 X-Sub (RGB+Pose)** and 95.6% on FineGYM-99 — figures from a secondary review, not verified against the paper table. — [CVPR 2022 paper](https://openaccess.thecvf.com/content/CVPR2022/html/Duan_Revisiting_Skeleton-Based_Action_Recognition_CVPR_2022_paper.html); [liner review](https://liner.com/review/revisiting-skeletonbased-action-recognition); [PYSKL](https://www.github.com/kennymckormick/pyskl)
- Probability-level fusion of frozen RGB (C3D) and skeleton (PoseC3D SlowOnly R50, 17 kp, 48 frames) on UCF-101 (student journal NHSJS, Aug 2026, single split, synthetic occlusion): clean — RGB 83.08, skeleton 86.81, avg-prob 92.62, **avg-log-prob 94.08**; 40% occlusion — RGB 36.82, skeleton 62.38, avg-log-prob 74.12, learned head trained at matched occlusion **79.12**; 70% occlusion — RGB 10.84, skeleton 31.64, learned matched 53.29; a head trained only on clean outputs generalises poorly under heavy occlusion (59.82 at 40%); learned head ≈20.5K params. — [NHSJS 2026](https://nhsjs.com/2026/lightweight-probability-level-fusion-for-occlusion-robust-human-activity-recognition-from-rgb-and-skeleton-data/)
- Gesture spotting evidence that the gate modality matters: RGB 8-frame detector recall 70.22% vs depth 97.30% on nvGesture. — [arXiv 1901.10323](https://arxiv.org/abs/1901.10323)
- iPay (2026) uses multimodal networks with adaptive spatial prior learning for payment-action recognition (retail-adjacent multimodal action recognition; details not retrieved). — [arXiv 2605.10732](https://arxiv.org/pdf/2605.10732)

### Inferences
- For Easy FnB, the best cost/benefit hybrid is **feeding the per-frame PE-Core probe probability (and keypoint confidences/visibility mask) as extra input channels to the tiny GRU**, or late-fusing GRU log-prob with the probe's smoothed log-prob. This is "two-stream late fusion" at ~zero extra compute, since the probe already runs.
- Train the fusion with **matched degradation** (random keypoint dropping, edge truncation, downscaled crops) — the NHSJS result suggests a fusion head trained only on clean data is brittle exactly where Easy FnB currently fails (distant/truncated people).
- When keypoints are missing (edge-cut person), the fusion should fall back to the RGB probe; when the crop is tiny (distant person), keypoint geometry may still be informative but noisy — an explicit "keypoint reliability" input lets the model choose. A gate that requires both shoulder and wrist keypoints prevents the RGB stream from ever helping in these cases.
- Video-crop models (X3D-XS, MoViNet-A0, small VideoMAE) would add a second backbone on a shared 4 GB GPU, require per-track clip buffers, and need labelled video clips — unlikely to pay off in 9 days compared with score-level fusion of models already running (inference; no direct benchmark found at this budget).

### Gaps
- No verified FLOPs/latency for RGBPoseConv3D or for X3D-XS / MoViNet-A0 on RTX 3050 / Ryzen 6800H were retrieved in this pass.
- No study found that quantifies RGB+pose fusion benefit specifically for small/distant or frame-edge-truncated people in CCTV.

## Q6. Handling missing keypoints, truncated bodies and low-resolution people online

### Takeaway
Recent work treats missing/low-confidence joints as a training-distribution problem: simulate realistic pose-estimator failures (occlusion, low-confidence dropout, left/right swaps) during training, use relative/normalized coordinates, and optionally impute or distil from high-quality skeletons; at inference, score-level fusion with RGB is the simplest fallback.

### Cited Findings
- Cormier et al. (WACV 2024 workshop): augmentations mimicking real pose-estimator failures — occlusion simulation, dropping low-confidence keypoints, keypoint mirror-swapping — plus reconstruction of occluded keypoints; argued to resemble real failures better than uniform masking (exact gains not retrieved; PDF 403). — [WACV 2024W](https://openaccess.thecvf.com/content/WACV2024W/RWS/papers/Cormier_Enhancing_Skeleton-Based_Action_Recognition_in_Real-World_Scenarios_Through_Realistic_Data_WACVW_2024_paper.pdf)
- Self-supervised skeleton benchmark under realistic occlusion masks joints by the dataset's real missing-joint distribution and finds **relative coordinates more robust** on occluded sequences. — [arXiv 2309.12029](https://arxiv.org/pdf/2309.12029)
- Low-quality-skeleton recognition (arXiv 2404.18206): transfers knowledge from high-quality to low-quality (missing/inaccurate joints) skeletons; recognition degrades as occlusion rate rises. — [arXiv 2404.18206](https://arxiv.org/pdf/2404.18206)
- Imputation approaches: GAIN + masked-autoencoder two-stage framework (Neurocomputing 2025); recognition-guided generative imputation applied only to uncertain samples (2026). — [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0925231225001055); [MDPI Informatics](https://www.mdpi.com/2227-9709/13/9/140)
- Classroom hand-raise systems: missing keypoints of the raised hand/arm cause raised-hand-to-student matching errors; a temporal model on body-pose embeddings reached F1 0.76 on 36 real classroom videos (127 students, 2,442 annotated hand-raise events), showing real-world difficulty. — [PMLR v95](http://proceedings.mlr.press/v95/zhou18a/zhou18a.pdf); [ECR Hub](https://ecrhub.org/publications/automated-hand-raising-detection-classroom-videos-view-invariant-and-occlusion-robust)
- PoseConv3D's heatmap input is claimed more robust to pose noise than coordinate GCNs. — [CVPR 2022](https://openaccess.thecvf.com/content/CVPR2022/html/Duan_Revisiting_Skeleton-Based_Action_Recognition_CVPR_2022_paper.html)

### Inferences
- Cheap, implementable-in-days measures for the GRU: (1) input = normalized coords relative to neck/shoulder midpoint scaled by shoulder width or bbox height, plus per-joint confidence and a binary visibility mask (zero-fill missing coords); (2) train-time augmentation: random joint dropout weighted toward wrists/elbows, simulated frame-edge truncation (drop all joints beyond a random image border), Gaussian jitter scaled inversely with bbox size, left/right swap; (3) short-gap interpolation (≤3 frames) of lost keypoints per track before the GRU; (4) reset/hold state on ByteTrack ID switch.
- For distant small people: run pose (or the crop classifier) on an upscaled crop of the person bbox when bbox height is below a threshold (a second-pass "zoom"), only for seated tracks in table zones — targeted, low-cost. For edge-truncated people: if the shoulder is out of frame, gate on the RGB probe + upper-arm/wrist cues alone.
- Report results stratified by person size and truncation so the demo can honestly state the operating envelope (e.g., "reliable when person bbox height ≥ X px").

### Gaps
- No quantitative numbers retrieved for the WACV 2024W augmentation gains or for 2404.18206.
- No source found giving a minimum person height (pixels) for reliable COCO-17 wrist/shoulder keypoints from YOLO-pose models.
