# Pretrained skeleton encoders, few/zero-shot, augmentation and synthetic data for hand-raise recognition with very few labels (2024–2026)

Scope: per-person 2D COCO-17 keypoints (YOLO26-pose plus ByteTrack), seated customers with occluded lower bodies, about 60 self-recorded clips. Does a pretrained encoder plus a small head beat a tiny GRU/TCN trained from scratch, and which data tricks help most?

Important framing for the report writer: almost every 2024–2026 self-supervised, zero-shot and few-shot benchmark number below is on **3D NTU-25 skeletons** from Kinect, with 60–120-way classification. Our task is **2D COCO-17**, seen from a high CCTV angle, and needs only a 2–8-way decision. The numbers show relative trends (pretraining beats scratch by X points), not the accuracy we should expect.

---

## Q1. Pretrained / self-supervised skeleton encoders: which accept 2D COCO-17, how big and fast, and how well with 1%/10% labels? Do they beat training from scratch?

### Takeaway
Two pretrained encoders take 2D COCO-style keypoints with little work and have public checkpoints. **ST-GCN++ trained on NTU-60 2D HRNet keypoints** (MMAction2/PYSKL, 1.39M params) uses the same 17-joint COCO-style input. **MotionBERT / MotionBERT-Lite** takes H36M-17, converted from COCO by permutation and interpolation. The strongest self-supervised encoders of 2024–2026 (MAMP, S-JEPA, MacDiff, GFP, AMR, SLiM) are all benchmarked on 3D NTU-25 and do not take COCO-17 2D input out of the box. Pretraining clearly helps when labels are scarce: about +6 points in one-shot and more than 15 points at 1% labels over scratch. Those comparisons are on 60–120-way tasks, though.

### Cited Findings
**MotionBERT (ICCV 2023; still the main 2D-input "motion foundation model" with public weights)**
- Input is 2D skeletons shaped B × T × 17 × 3 (x, y, confidence) in **H36M 17-joint format**, and other formats must be converted first (`lib/data/dataset_wild.py`). Clips can be up to 243 frames. Apache-2.0 licence. Checkpoints are on OneDrive and Hugging Face (`walterzhu/MotionBERT`). Downloads are MotionBERT 162 MB and MotionBERT-Lite 61 MB, and the README says Lite "performs similarly in most use cases, especially with fine-tuning" at lower compute — [MotionBERT GitHub](https://github.com/Walter0807/MotionBERT)
- Architecture: DSTformer with depth N=5, 8 heads, feature and embedding size 512, pretrained on T=243 clips. It handles other input lengths because it is a Transformer. During fine-tuning the backbone learning rate is 0.1× the new head's — [MotionBERT paper](https://arxiv.org/pdf/2210.06551)
- Pretraining recovers 3D motion from corrupted 2D. Data: Human3.6M and AMASS mocap projected **orthographically to 2D**, plus PoseTrack (annotated 2D) and InstaVariety (OpenPose 2D). "We convert keypoints of 2D datasets (COCO and OpenPose format) to Human3.6M using permutation and interpolation." Corruption: **15% of joints randomly zeroed, plus Gaussian/uniform noise** — [MotionBERT paper](https://arxiv.org/pdf/2210.06551)
- Action recognition uses **HRNet 2D skeletons following PoseC3D**, joint modality, 1-clip. NTU-60 X-Sub / X-View: **scratch 87.7 / 94.1, fine-tuned 93.0 / 97.2**, against PoseConv3D at 93.1 / 95.7. **NTU-120 one-shot: scratch 61.0, fine-tuned 67.4.** Comparison methods: SL-DML 50.9, Skeleton-DML 54.2, TCN-OneShot 46.5. The paper says "the pretraining stage accounts for a large performance gain" — [MotionBERT paper](https://arxiv.org/pdf/2210.06551). (The README lists 97.2 / 93.0, and a fetch summary attributed these to X-Sub / X-View the other way round. The paper's table has X-Sub = 93.0 and X-View = 97.2 — [MotionBERT GitHub](https://github.com/Walter0807/MotionBERT).)

**ST-GCN++ on NTU-60 2D keypoints (MMAction2 / PYSKL)**
- MMAction2 ST-GCN++, NTU-60 X-Sub, **2D keypoints**: joint **89.29%**, bone 92.30, joint-motion 87.30, bone-motion 88.76, 2-stream 92.61, 4-stream 92.77. **1.39M params, 1.95 GFLOPs.** Every single-modality row has checkpoint and log links. The 3D-joint version scores 89.14 at 1.4M params and 2.96 GFLOPs. Testing uses 10 clips with uniform 100-frame sampling — [MMAction2 stgcnpp configs](https://github.com/open-mmlab/mmaction2/tree/main/configs/skeleton/stgcnpp)
- PYSKL (Apache-2.0) ships HRNet 2D skeletons "for every dataset we supported" as processed pickle files, and has a notebook for extracting skeletons from arbitrary RGB video. The repo is "currently not maintained", with the last changelog entry on 2023-03-20 — [PYSKL GitHub](https://github.com/kennymckormick/pyskl)

**Self-supervised 3D encoders (NTU-25, 3D) and their low-label numbers**
- Linear evaluation, joint modality, NTU-60 X-Sub / X-View / NTU-120 X-Sub / X-Set / PKU-MMD II: SkeletonMAE 74.8/77.7/72.5/73.5/36.1; **MAMP (ICCV'23)** 84.9/89.1/78.6/79.1/53.8; **S-JEPA (ECCV'24)** 85.3/89.8/79.6/79.9/53.5; **MacDiff (ECCV'24)** 86.4/91.0/79.4/80.2/–; **GFP (ICCV'25)** 85.9/92.0/79.1/80.3/56.2; **AMR (CVPR'26)** 87.4/92.3/81.1/81.9/60.3; **SLiM (2026)** 87.9/93.2/81.2/83.6/59.7 — [SLiM, arXiv 2603.10648](https://arxiv.org/html/2603.10648)
- Semi-supervised NTU-60, X-Sub 1% / 10%, X-View 1% / 10%: SkeletonMAE 54.4/80.6/54.6/83.5; **MAMP 66.0/88.0/68.7/91.5**; **S-JEPA 67.5/88.4/69.1/91.4**; **GFP 71.8/88.7/72.9/92.1**; **SLiM 72.1/88.8/75.8/91.9** — [SLiM, arXiv 2603.10648](https://arxiv.org/html/2603.10648). S-JEPA's own poster gives the same 67.5/88.4/69.1/91.4 — [S-JEPA project page](https://sjepa.github.io/), [ECCV 2024 poster](https://eccv2024.ecva.net/virtual/2024/poster/1076)
- Transfer to PKU-MMD II (frozen encoder, linear probe), pretrained on NTU-60 / NTU-120: MAMP 70.6/73.2, S-JEPA 71.4/74.2, MacDiff 72.2/73.4, SLiM 72.7/75.3 — [SLiM](https://arxiv.org/html/2603.10648)
- MAMP reports that pretraining improves on training from scratch by **more than 15.5% on all NTU-60 subsets** in the semi-supervised setting. Results are averaged over 5 runs — [MAMP paper](https://arxiv.org/pdf/2308.07092). Code: [maoyunyao/MAMP](https://github.com/maoyunyao/MAMP)
- S-JEPA predicts latent representations of masked joints instead of raw coordinates. The ECCV poster said "Codes will be available upon publication", and no confirmed public release turned up — [S-JEPA project](https://moo-osama.github.io/projects/s-jepa), [ECCV poster](https://eccv2024.ecva.net/virtual/2024/poster/1076)
- **SOfA (KAIST, arXiv Sept 2026)**, "One for All: Generalist Foundation Model for Cross-Sensor Skeleton Representation Learning", trains on ten standardized 3D skeleton datasets. It uses learnable "Canonical Joint Slots" to handle different joint counts and text-encoder "Semantic Joint Embeddings" to align joint indices. The abstract claims state of the art across tasks and sensors, but the abstract page gives no numbers and no confirmed code or weights — [arXiv 2609.07078](https://arxiv.org/abs/2609.07078)

### Inferences
- **Usable encoders, by how directly they fit our input:** (1) MMAction2 ST-GCN++ 2D-joint NTU-60 checkpoint: 17 COCO-style joints, 1.39M params, tiny on CPU. (2) MotionBERT-Lite / MotionBERT: needs COCO→H36M conversion (pelvis = hip midpoint, spine/thorax interpolated, head from nose/ears). Its pretraining with 15% joint dropout and noise suits occluded CCTV keypoints. (3) MAMP and the other 3D-NTU self-supervised models would need a 2D or COCO-17 re-pretrain, which is unrealistic in 9 days. Expect PYSKL's 2D pickles to be COCO-17, since HRNet is a COCO model, but check this before relying on it (see Gaps).
- **Size and speed, estimated:** ST-GCN++ runs about 2 GFLOPs per 100-frame clip, so batching every tracked person on a Ryzen 7 6800H CPU is easily real-time at 5–25 fps. MotionBERT's 162 MB checkpoint suggests roughly 40M fp32 parameters and Lite's 61 MB about 15M. This is inferred from file size, not reported. Running full MotionBERT next to YOLO26-pose on a 4 GB RTX 3050 is feasible but much heavier than a GCN. Lite with a short window (e.g. 32–64 frames) is the sensible MotionBERT choice.
- **Pretrained vs scratch:** wherever the literature compares them, pretraining wins in low-label regimes (one-shot 61.0→67.4, more than 15 points at 1% labels). Those are 60–120-way tasks, though. Ours is a near-binary task where a strong geometric cue exists (wrist above shoulder or head, arm extended, held for some time). So a small GRU/TCN over normalized, hand-engineered features may come close to a pretrained model on clean data. The pretrained model's edge should show mostly on the confusable negatives (brushing hair, stretching, waving) and under viewpoint shift. The practical answer is to **train both and compare on a held-out actor**. Evidence favours ST-GCN++ fine-tuned from the NTU-60 2D checkpoint as the strongest cheap option.

### Gaps
- No 2024–2026 self-supervised skeleton model with public weights that is **pretrained on 2D COCO-17** turned up. Every new SSL method (S-JEPA, MacDiff, GFP, AMR, SLiM, SOfA) reports results on 3D NTU-25.
- MotionBERT's exact parameter count, FLOPs and CPU latency weren't retrieved. The ~40M / ~15M figures are inferred from checkpoint sizes.
- The PYSKL/MMAction2 2D keypoint layout isn't explicitly confirmed as COCO-17 in the pages fetched. MMAction2 doesn't mention HRNet or COCO on the stgcnpp page. Check the pickle (`keypoint` shape `[M, T, 17, 2]`) before relying on it.
- Whether MAMP releases pretrained weights wasn't verified (the repo exists). MacDiff, UmURL and Skeleton2vec 1%/10% numbers weren't in the tables retrieved.
- No paper measures pretrained vs scratch for a **binary, 2D, CCTV-angle gesture** task with about 30 clips per class.

---

## Q2. Language-supervised / zero-shot skeleton models: can "raising hand to call a waiter" be defined by text, on 2D COCO keypoints?

### Takeaway
Zero-shot skeleton recognition has improved a lot (NTU-60 55/5 split now about 82–87% top-1). But every method found uses **3D NTU skeletons** with a Shift-GCN/ST-GCN backbone trained on the seen classes, plus a CLIP text encoder. None is released for 2D COCO-17 input. Accuracy also drops to about 41–65% when more classes are unseen. Text-defined zero-shot is not a dependable route for this hackathon; at most it is a demo curiosity.

### Cited Findings
- Zero-shot top-1 (Xsub), NTU-60 55/5 | 48/12 | NTU-120 110/10 | 96/24: SynSE 71.9|31.3|52.4|41.9; SMIE 77.9|41.5|61.3|42.3; **PURLS (CVPR'24) 79.2|41.0|72.0|52.0**; **SA-DVAE (ECCV'24) 82.4|41.4|68.8|46.1**; **STAR (ACM MM'24) 81.4|45.1|63.3|44.3**; TDSM (ICCV'25) 86.5|56.0|74.2|65.1; DVTA (PR'25) 79.3|44.1|74.9|51.8; InfoCPL (TMM'25) 85.9|53.3|74.8|60.1; Neuron (CVPR'25) 86.9|62.7|71.5|57.1; **Flora (CVPR'26) 85.8|61.5|80.7|64.1**, or 86.3|65.3|79.6|66.4 with 4s-Shift-GCN features — [Flora, arXiv 2511.09388](https://arxiv.org/html/2511.09388)
- Generalized ZSL harmonic mean on NTU-60 55/5: SA-DVAE 66.3, STAR 69.4, Neuron 71.4, Flora 76.6 (77.4†). On 48/12 the H values are only 42.6–60.5 — [Flora](https://arxiv.org/html/2511.09388)
- Flora's input is **3D joint coordinates (3 × T × V × M)** with pre-extracted Shift-GCN or ST-GCN features and a **CLIP ViT-L/14@336px** text encoder. Code: github.com/cseeyangchen/Flora — [Flora](https://arxiv.org/html/2511.09388)
- PURLS uses a pretrained CLIP text encoder to align global action text and body-part / temporal sub-movement descriptions with skeleton features — [PURLS, arXiv 2406.13327](https://www.arxiv.org/pdf/2406.13327). DynaPURLS adds adaptive partitioning and test-time adaptation — [arXiv 2512.11941](https://arxiv.org/pdf/2512.11941v1)
- A CVPR 2025 study found that learnable prompts on CLIP give "volatile" gains for skeleton zero-shot recognition, which it attributes to weaker generalization to unseen actions — [Zhu et al., CVPR 2025](https://openaccess.thecvf.com/content/CVPR2025/papers/Zhu_Semantic-guided_Cross-Modal_Prompt_Learning_for_Skeleton-based_Zero-shot_Action_Recognition_CVPR_2025_paper.pdf)
- Under SMIE's random-split protocol, TDSM's per-split NTU-60 55/5 accuracy ranges from about 82.6% to 96.1% (mean 88.88%). So which classes are unseen matters a lot — [TDSM ICCV 2025 supplement](https://openaccess.thecvf.com/content/ICCV2025/supplemental/Do_Bridging_the_Skeleton-Text_ICCV_2025_supplemental.pdf)
- "Towards Universal Skeleton-Based Action Recognition" proposes an open-vocabulary setup across heterogeneous skeleton sources: Kinect, **2D pose estimation**, MoCap. It builds a "HOV-Skeleton" benchmark from NW-UCLA, 2D and 3D NTU-60/120 and HumanML3D, and reports cross-format zero-shot generalization including 2D input. This comes from a secondary review page and wasn't checked against the paper — [review](https://www.themoonlight.io/review/towards-universal-skeleton-based-action-recognition)
- SkeletonContext (arXiv Mar 2026) injects language-derived context such as objects into skeleton features to make up for the missing appearance cues — [arXiv 2603.29692](https://arxiv.org/html/2603.29692v1)

### Inferences
- These methods need (a) a skeleton backbone trained on many seen classes in the same skeleton format and (b) unseen classes that are semantically far apart. "Raise hand to call staff" vs "brush hair" vs "stretch" are fine-grained and look kinematically alike. That is the regime where ZSL is weakest (48/12 and 96/24 splits at 41–66%).
- A cheap use of language: write text descriptions to drive **text-to-motion generation** (Q5), rather than for zero-shot classification.

### Gaps
- No skeleton–text zero-shot model with released weights for **2D COCO-17** input was found. Whether the HOV / universal-skeleton paper's code and checkpoints are public wasn't confirmed.
- No zero-shot results on gesture-level classes like "raise hand to call someone" were found.

---

## Q3. Few-shot (one/five-shot) skeleton action recognition, 2024–2026

### Takeaway
On the standard NTU-120 one-shot protocol (100 base / 20 novel classes), the best 2025 methods reach about **69%** (SkeletonX 69.1, M&C-scale 68.7). MotionBERT's simple pretrain-then-fine-tune reaches **67.4%**, so a good pretrained encoder plus nearest-prototype or fine-tuning is close to the best specialised few-shot method. With 10–50 samples per class and **no** pretraining, GCNs trained from scratch do poorly on 60–120-way NTU (35–67%). SkeletonX-style pair construction adds 5–14 points.

### Cited Findings
- NTU-120 one-shot (100/20) top-1: APSR 45.3, uDTW 49.0, SL-DML 50.9, Skeleton-DML 54.2, SMAM 56.4, JEANIE 57.0, Trans4SOAR 57.1, ALCA-GCN 57.6, STA-MLN 59.9, CrossGLG 62.6, M&C-scale 68.7, **SkeletonX 69.1** (CTR-GCN encoder, 1.53M params, 1.80 GFLOPs) — [SkeletonX, arXiv 2504.11749](https://arxiv.org/html/2504.11749v1)
- PKU-MMD II one-shot: ProtoNet 37.0, FR-Head 34.3, **SkeletonX 38.3**. Plain ST-GCN 31.6, CTR-GCN 32.5 — [SkeletonX](https://arxiv.org/html/2504.11749v1)
- Limited data **from scratch** (baseline → with SkeletonX), NTU-60 X-Sub (60-way), at **10 / 20 / 30 / 50 samples per class**: ST-GCN 34.9→49.0 / 51.7→60.0 / 57.4→64.7 / 66.0→71.5; CTR-GCN 41.5→52.2 / 53.9→61.7 / 60.0→67.0 / 67.5→73.0. NTU-120 at 10/class: ST-GCN 18.9→24.1, CTR-GCN 21.3→26.1. Largest gain is +14.1 (ST-GCN, NTU-60, 10/class). Gains are smaller on the transformer SkateFormer. SkeletonX pairs same-performer/different-action and same-action/different-performer samples to disentangle performer from action features, adding about 0.07M params. Code: github.com/zzysteve/SkeletonX — [SkeletonX](https://arxiv.org/html/2504.11749v1)
- MotionBERT NTU-120 one-shot: **61.0 scratch → 67.4 fine-tuned** from pretrained weights. The authors argue pretrain-finetune suits domain-specific actions that public datasets lack — [MotionBERT paper](https://arxiv.org/pdf/2210.06551)

### Inferences
- About 30 positives and 30 negatives per actor is roughly the "30 samples per class" column. But our problem has 2–8 classes, not 60–120, so absolute accuracy should be far higher than these NTU numbers.
- The main danger with only **2 actors** is the model learning performer identity or style instead of the action. SkeletonX was built for exactly this performer–action entanglement. In our case the cheap equivalent is leave-one-actor-out validation plus strong body-shape and scale augmentation.
- Prototype or metric approaches (nearest-class-mean on frozen MotionBERT or ST-GCN++ embeddings) make a quick baseline that needs no gradient training. A fine-tuned small head will probably beat them once there are about 30 examples per class (MotionBERT shows fine-tuning beating scratch).

### Gaps
- No 2024–2026 five-shot numbers on NTU-120 or NW-UCLA were retrieved. No few-shot results on 2D COCO keypoints were found.
- SkeletonX's per-backbone one-shot numbers aren't reported (CTR-GCN only).

---

## Q4. Skeleton augmentations: which matter most when data is scarce?

### Takeaway
The evidence is thin. No paper found ablates individual augmentations (rotation, shear, scale, flip, speed, joint dropout, mixup) **in a limited-label setting**. The best-supported robustness tricks come from MotionBERT's pretraining recipe (**15% random joint zero-out plus Gaussian/uniform noise**, and **projecting 3D to 2D**) and from standard suites in SkateFormer, LSTC-MDA and SLiM. For our CCTV setting, the augmentations that address actual train/test shifts should matter most: viewpoint (camera elevation and yaw), lower-body occlusion, keypoint jitter and dropout, speed. That ranking is inference, not measured.

### Cited Findings
- MotionBERT trains its encoder on 2D inputs corrupted by **randomly zeroing 15% of joints** and **adding noise from a Gaussian/uniform mixture**. It gets 2D from 3D mocap by **orthographic projection** — [MotionBERT paper](https://arxiv.org/pdf/2210.06551)
- SkateFormer (2024) uses a skeletal augmentation suite of **random shear, rotation, scaling, flipping, coordinate dropout and joint dropout**, with per-dataset settings in its appendix. No limited-label ablation was retrieved — [SkateFormer, arXiv 2403.09508](https://arxiv.org/pdf/2403.09508)
- LSTC-MDA (2025) extends Joint Mixing Data Augmentation with input-level additive mixup **restricted to samples from the same camera view**, aimed at scarce labelled skeleton data on NTU — [arXiv 2509.14619](https://arxiv.org/html/2509.14619v1)
- SLiM (2026) adds "Semantic Tube Masking" and "Skeleton-Aware Augmentations" to masked-feature-prediction pretraining and reaches the best 1%-label NTU-60 numbers (72.1 / 75.8) — [SLiM](https://arxiv.org/html/2603.10648)
- Generative data augmentation (Dong et al., **FG 2026**): a conditional Transformer encoder-decoder generator with a refinement module and dropout-based fidelity/diversity control, evaluated on HumanAct12 and NTU-VIBE. It reportedly "consistently improves" several skeleton recognizers in **few-shot and full-data** settings. The abstract gives no numbers — [arXiv 2604.14933](https://arxiv.org/abs/2604.14933)
- SkeletonX's performer/action pair recombination is effectively a structured feature-level mix and gives up to +14.1 points at 10 samples per class — [SkeletonX](https://arxiv.org/html/2504.11749v1)

### Inferences
- Augmentations ranked by expected value for this project (inferred from the train/test shifts, since no measured ranking exists):
  1. **Lower-body occlusion and joint dropout.** Zero out, or set confidence to 0 for, hips, knees and ankles with high probability, and randomly drop 10–20% of other joints and short runs of frames. This copies MotionBERT's pretraining corruption and the real occlusion by tables.
  2. **Viewpoint.** Rotate or shear 2D within about ±15–30°. Better: if 3D is available (synthetic motion, or MotionBERT lifting), re-project from random high CCTV elevations (about 20–60°) and yaws.
  3. **Keypoint jitter, scaled by bounding-box size**, plus a frame-rate/speed change (0.5–2×) and random temporal crops. This matches the 5–25 fps range and YOLO noise.
  4. **Scale and translation normalisation**, plus mirroring with a left/right joint swap. Either hand raising counts as positive, so mirroring doubles the positives at no cost.
  5. Mixup / CutMix variants: weakest evidence for a binary task. If used, mix only within the same view (LSTC-MDA's restriction).
- Normalising first (centre on the shoulder midpoint, scale by shoulder width) removes most scale and translation variance, so geometric augmentation can then focus on rotation and occlusion.

### Gaps
- No per-augmentation ablation under 1–10% labels or tens of samples per class was found. Exact quantitative gains for SkeleMixCLR, AimCLR-style extreme augmentations and similar methods weren't retrieved.
- No study of "lower-body occlusion" augmentation specifically for seated or table scenes was found.

---

## Q5. Synthetic data: text-to-motion (MDM, MoMask, T2M-GPT, MotionGPT) projected to 2D from random cameras. Does it help?

### Takeaway
Yes, with good evidence for the few-shot case. KineMIC (Dec 2025) reports that adding synthetic motions from **off-the-shelf MDM driven by plain text prompts** raises a 10-shot, 3-class NTU-120 ST-GCN classifier **from 63.1% to 83.9%**. A distilled, fine-tuned generator reaches 86.2% (+23.1 points). Naively LoRA-fine-tuning MDM on the few real samples does worse (75.5%) because it collapses diversity. Projecting 3D mocap to 2D is how MotionBERT built its 2D pretraining data, which supports generating 3D motion and rendering it from random CCTV-like cameras. No study specific to hand-raise or waiter-calling was found.

### Cited Findings
- **KineMIC** (Cazzola & Alboody, arXiv 2512.11654, Dec 2025). Target: NTU-120 cross-subject subset with 3 classes (run on spot A099, side kick A102, stretch on self A104), **10 real samples per class**. Source: HumanML3D. Generator: MDM (8-block transformer, pretrained on HumanML3D) with LoRA rank 16, 5,000 steps, 100 diffusion steps, CFG scale 2.5. Classifier: **ST-GCN following PYSKL practice**. Training set: 30 real plus **1,152 synthetic** clips, 5 seeds — [KineMIC](https://arxiv.org/html/2512.11654v2)
- KineMIC results (top-1): real only **63.1%** (58.4% as reported by Fukushi et al.); **pretrained MDM with text prompts, no fine-tuning: 83.9%** (85.23 ± 3.32 in the ablation); MDM from scratch 73.9%; MDM plus LoRA fine-tuning 75.5% ("overfits and collapses diversity"); **KineMIC 86.2%** (+23.1); Fukushi et al. 86.4%; Kinetic-GAN 81.7%; ACTOR 73.6% — [KineMIC](https://arxiv.org/html/2512.11654v2)
- Limitations KineMIC reports: text similarity doesn't always match kinematic similarity (punch vs kick; a front kick retrieved for a side-kick target), and combining two lower-body actions is unstable. Target skeletons were re-estimated with VIBE and downsampled from 30 to 20 fps into the HumanML3D 263-D representation. No code repository is linked, only a project page — [KineMIC](https://arxiv.org/html/2512.11654v2)
- Dong et al. (FG 2026) generate label-conditioned skeleton sequences and report consistent gains for several recognizers in few-shot and full-data settings (no numbers in the abstract) — [arXiv 2604.14933](https://arxiv.org/abs/2604.14933)
- MotionBERT turns AMASS and Human3.6M 3D mocap into 2D training data by **orthographic projection** and aligns all keypoint definitions to H36M — [MotionBERT paper](https://arxiv.org/pdf/2210.06551)

### Inferences
- **Recipe that works within this time budget:** prompt a pretrained text-to-motion model (MDM or MoMask with HumanML3D weights; any of them should work) with 20–50 paraphrases for each class. Positives: "a seated person raises their right hand above their head to get attention and holds it", "lifts left arm straight up", and so on. Negatives: "touches hair", "scratches head", "drinks from a cup", "points forward", "stretches both arms", "waves to a friend". Generate a few hundred clips per class. Convert SMPL-22 joints to COCO-17: map body joints directly and approximate nose, eyes and ears from the head/neck joints. Then **perspectively project** from random cameras at CCTV heights (about 2.5–3.5 m, pitched 20–60° down, random yaw and distance), add YOLO-like jitter, drop lower-body joints, and resample to 5–25 fps.
- KineMIC's ablation suggests plain text prompting already captures most of the gain. Fancy generator fine-tuning isn't needed for a hackathon, and fine-tuning the generator on 60 clips may hurt (75.5% vs 83.9%).
- HumanML3D motions mostly involve standing or walking. Seated upper-body-only motions may be under-represented, so filter or check generations visually. Lower-body occlusion augmentation hides any leg artefacts anyway.
- Synthetic data is best used to **pretrain or augment and then fine-tune on real clips**, keeping real held-out clips as the only test set.

### Gaps
- No published study using text-to-motion synthetic data for hand-raise, waiter-calling or classroom hand-raising was found.
- No direct evidence on the gain from 2D projection at **high CCTV angles** (vs frontal) for recognition was found.
- MoMask, T2M-GPT and MotionGPT haven't been compared head-to-head as data sources for recognition. KineMIC tested only MDM.

---

## Q6. Practical recommendation: the best-evidenced recipe for about 60 clips plus public data

### Takeaway
The best-evidenced, feasible recipe: start from a **pretrained 2D skeleton encoder that takes COCO-style keypoints**, fine-tune a small head, and grow the training set with public NTU 2D data and **text-to-motion synthetic clips projected to CCTV-like 2D views**. Train under heavy occlusion, viewpoint and noise augmentation. Keep a tiny GRU/TCN on hand-engineered, normalised features as the baseline to beat and as the CPU fallback. Compare them with leave-one-actor-out evaluation.

### Cited Findings
- 2D NTU-60 ST-GCN++ checkpoints exist: 89.29% joint, 1.39M params, 1.95 GFLOPs — [MMAction2](https://github.com/open-mmlab/mmaction2/tree/main/configs/skeleton/stgcnpp). PYSKL provides HRNet 2D skeleton pickles for its datasets — [PYSKL](https://github.com/kennymckormick/pyskl)
- Pretraining gives large gains in low-label settings: MotionBERT one-shot 61.0→67.4, NTU-60 X-Sub 87.7→93.0 — [MotionBERT paper](https://arxiv.org/pdf/2210.06551); MAMP more than 15.5 points over scratch semi-supervised — [MAMP](https://arxiv.org/pdf/2308.07092)
- Off-the-shelf text-to-motion synthetic data: 63.1→83.9% for a 10-shot, 3-class ST-GCN — [KineMIC](https://arxiv.org/html/2512.11654v2)
- Scratch GCNs with 10–30 samples per class do poorly on many-way tasks (NTU-60: 35–60%). Performer/action disentanglement adds 5–14 points — [SkeletonX](https://arxiv.org/html/2504.11749v1)
- Robustness corruption to copy: 15% joint dropout plus noise — [MotionBERT paper](https://arxiv.org/pdf/2210.06551)

### Inferences
Suggested plan (inference, ordered for a 9-day, 2-person timeline):
1. **Day 1–2, baseline.** Per track, build a 1–3 s sliding window. Normalise by the shoulder midpoint and shoulder width. Features: wrist and elbow heights relative to the shoulder/nose, elbow angle, wrist velocity, time held above the head, and keypoint confidences. Classify with a tiny GRU/TCN (or even logistic regression or GBM) plus hysteresis or temporal smoothing. This gives a working demo early.
2. **Day 2–4, pretrained model.** Fine-tune the **MMAction2 ST-GCN++ NTU-60 2D-joint checkpoint** (same 17-joint COCO-style layout as YOLO-pose; verify the order) with a new 2–N-class head. Freeze most layers at first because the data is tiny. Optional alternative: MotionBERT-Lite with COCO→H36M conversion, short windows, and an MLP head on pooled features.
3. **Public data.** Add NTU-60/120 2D HRNet clips for relevant classes as extra positives and negatives (candidate classes are in Gaps; verify them). Upper-body crops or lower-body masking reduce the standing-vs-seated mismatch.
4. **Synthetic.** A few hundred MDM/MoMask clips per class from paraphrased prompts, converted to COCO-17 and projected from random high cameras (Q5).
5. **Augment.** Lower-body dropout, random joint and frame dropout, jitter, viewpoint rotation or re-projection, speed 0.5–2×, mirroring (Q4).
6. **Evaluate.** Leave-one-actor-out on real clips only, and report false alarms per hour on "normal dining" footage. The decision is whether the pretrained model beats the baseline on held-out confusables.
- The two actors are a bigger risk than model choice. If possible, record a few extra people (even 5–10 short clips each) and vary seat, camera angle and clothing. Performer diversity is what SkeletonX-style results show matters most.
- Compute: ST-GCN++ (about 2 GFLOPs per 100-frame clip) and the GRU baseline both run on the Ryzen CPU. MotionBERT-Lite is better kept on the RTX 3050 if used at all.

### Gaps
- **Candidate NTU classes for transfer (from memory of the NTU-60/120 class list, not verified in this research; check against the dataset docs):** NTU-60 includes drink water, brush hair, hand waving, pointing to something with finger, cheer up, wipe face, salute, headache, fan self, and touch head/neck-pain-like classes. NTU-120 adds flick hair, capitulate/hands up, stretch oneself, arm swings, and yawn. Using these as positives or confusable negatives is untested.
- There is no direct evidence on how well NTU-trained 2D models (Kinect-height, mostly standing actors) transfer to seated, high-angle CCTV views. Expect a domain gap, and measure it.
- No reliable latency benchmarks for ST-GCN++ or MotionBERT-Lite on a Ryzen 7 6800H or RTX 3050 were found. Benchmark locally.
