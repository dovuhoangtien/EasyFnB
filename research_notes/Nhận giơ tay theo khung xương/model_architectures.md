# Skeleton-based action recognition architectures for a small real-time "raise hand to call staff" classifier (2D COCO-17, RTX 3050 4 GB / Ryzen 7 6800H CPU)

Scope note: these notes compare model families (RNN/TCN/MLP baselines, GCNs, skeleton transformers, Mamba/SSM, heatmap 3D-CNNs) using published benchmark numbers, model-zoo tables and repo licences. Most numbers are self-reported by the authors. Where two sources disagree (especially on FLOPs) both are given. Benchmark abbreviations: NTU60 X-Sub/X-View, NTU120 X-Sub/X-Set, top-1 %. "J" = joint stream, "2s/4s/6s" = 2-, 4- or 6-stream ensemble.

## Q1. How do simple baselines (GRU/LSTM, TCN, MLP) compare with GCNs and skeleton transformers on accuracy vs size, and what are the top 2024–2026 entries on NTU-120?

### Takeaway
On the big 60/120-class benchmarks, RNN baselines are 20–35 points behind modern GCNs (e.g. ST-LSTM 55.7 vs CTR-GCN about 89 on NTU120 X-Sub). But 2021→2025 progress among GCNs and transformers is small: about +2 points on NTU120 X-Sub (CTR-GCN 88.9 → ProtoGCN/Hyper-GCN 90.9), and it mostly comes from 4–6-stream ensembles. All of the leading models have only about 1.4–2.7 M parameters. For a binary or few-class upper-body task, the 2024–2026 state-of-the-art models add complexity without a clear payoff. The practically relevant step up from a GRU is a pretrained ST-GCN++/CTR-GCN-class model.

### Cited Findings
**Classic non-GCN baselines (NTU60 X-Sub / X-View; NTU120 X-Sub / X-Set)**
- HBRNN (CVPR15) 59.1 / 64.0; ST-LSTM (ECCV16) 69.2 / 77.7; STA-LSTM (AAAI17) 73.4 / 81.2; HCN (CNN, IJCAI18) 86.5 / 91.1; VA-fusion (TPAMI19) 89.4 / 95.0; AGC-LSTM (CVPR19) 89.2 / 95.0 — [EfficientGCN paper, Table 5](https://arxiv.org/pdf/2106.15125)
- NTU120: PA-LSTM 25.5 / 26.3; ST-LSTM 55.7 / 57.9; FSNet 59.9 / 62.4; SGN 79.2 / 81.5 — [EfficientGCN, Table 6](https://arxiv.org/pdf/2106.15125)
- AGC-LSTM, the strongest LSTM entry, has 22.89 M parameters (reported by its authors), about 79× EfficientGCN-B0 — [EfficientGCN, Table 7](https://arxiv.org/pdf/2106.15125)
- EfficientGCN says an earlier lightweight CNN-block network "is not as accurate as GCN models" — [EfficientGCN](https://arxiv.org/pdf/2106.15125)

**GCN and transformer progression (joint-modality table compiled by SkeletonAgent, Nov 2025; NTU60 X-Sub / X-View / NTU120 X-Sub / X-Set)** — [SkeletonAgent, Table 1](https://arxiv.org/html/2511.22433)
- ST-GCN (AAAI18) 81.5 / 88.3 / 70.7 / 73.2
- 2s-AGCN (CVPR19) 88.5 / 95.1 / 82.5 / 84.2
- MS-G3D (CVPR20) 91.5 / 96.2 / 86.9 / 88.4
- CTR-GCN (ICCV21) 92.4 / 96.8 / 88.9 / 90.6
- InfoGCN (CVPR22) 93.0 / 97.1 / 89.8 / 91.2
- PYSKL / ST-GCN++ (ACM MM22) 92.6 / 97.4 / 88.6 / 90.8
- FR-Head (CVPR23) 92.8 / 96.8 / 89.5 / 90.9
- HD-GCN (ICCV23) 93.4 / 97.2 / 90.1 / 91.6
- DS-GCN (AAAI24) 93.1 / 97.5 / 89.2 / 91.1
- BlockGCN (CVPR24) 93.1 / 97.0 / 90.3 / 91.5
- SkateFormer (ECCV24) 93.5 / 97.8 / 89.8 / 91.4
- ProtoGCN (CVPR25) 93.8 / 97.8 / 90.9 / 92.2
- Hyper-GCN (ICCV25) 93.7 / 97.8 / 90.9 / 92.0
- SkeletonAgent (an LLM-in-the-loop "agentic" framework, its own claim, not yet in a peer-reviewed venue in the table) 6-ensemble 94.5 / 98.2 / 91.7 / 93.1; 2-ensemble 90.5 on NTU120 X-Sub
- Caveat: the ProtoGCN headline (90.9 NTU120 X-Sub) is a 6-stream ensemble. Its 2-ensemble is 89.7 and its 4-ensemble 90.4, and no single-stream number appears in the main table. The ablation gives 89.0 for bone-only against an 87.8 baseline — [ProtoGCN](https://arxiv.org/html/2411.18941)
- SkateFormer (a skeletal-temporal transformer) by number of streams: J 87.7, J+B 89.4, 4s 89.8 on NTU120 X-Sub. On NW-UCLA it gets 98.3 — [SkateFormer](https://arxiv.org/html/2403.09508)
- Mamba/SSM entries: SkelMamba reports 89.9 / 91.5 on NTU120 X-Sub / X-Set — [SkelMamba](https://arxiv.org/abs/2411.19544v1). TSkel-Mamba (Dec 2025) reports 87.4 on NTU120 X-Sub with the joint stream (87.9 with CPKD), against 86.9 for BlockGCN joint — [TSkel-Mamba overview](https://www.alphaxiv.org/overview/2512.11503). Simba (Mamba-augmented U-ShiftGCN, 2024) claims SOTA on NTU60/120/NW-UCLA, but I did not retrieve its numbers — [Simba](https://arxiv.org/abs/2404.07645)
- Kinetics-Skeleton (top-1): ST-GCN 30.7, MS-G3D 38.0 (OpenPose skeletons), MS-G3D++ with HRNet 2D skeletons 45.1, PoseConv3D J+L 47.7 — [PoseConv3D, Table 8](https://arxiv.org/pdf/2104.13586). ProtoGCN 6s 51.9 (2s 49.9) — [ProtoGCN](https://arxiv.org/html/2411.18941)
- NW-UCLA (1,494 clips, 10 classes, per [Simba](https://arxiv.org/abs/2404.07645)): CTR-GCN 96.5, InfoGCN 96.0, HD-GCN 96.9 — [FreqMixFormer table](https://arxiv.org/pdf/2407.12322). BlockGCN 96.6, and BlockGCN's own reproduction of InfoGCN gives 96.5 — [BlockGCN arXiv](https://arxiv.org/pdf/2305.11468). SkateFormer 98.3 — [SkateFormer](https://arxiv.org/html/2403.09508)

### Inferences
- Since about 2021 the SOTA race has gained roughly 1 point per year on NTU120 X-Sub, mostly from ensembles. A single-stream 2024–2026 model is only about 1–2 points better than a single-stream CTR-GCN or ST-GCN++. For a 2–5-class task that gap will probably fall within noise, so choosing among SOTA models is not where the hackathon's accuracy will come from.
- The 20–35-point GRU/LSTM-vs-GCN gap comes from 60–120 fine-grained classes on 25-joint 3D data with around 40k training clips. For "raised hand held for ≥1 s" vs a handful of distractors, a small GRU over normalized upper-body keypoints can plausibly be competitive. Its real weakness is the lack of pretraining: no NTU or Kinetics weights exist for a custom 22k-param GRU. That transfer advantage, not raw architecture, is the main argument for trying a GCN.
- I found no paper that benchmarks a plain MLP over a flattened window on NTU. Treat it as a quick sanity baseline only.

### Gaps
- No exact params/FLOPs found for Hyper-GCN, ProtoGCN (the paper reports none), DeGCN, Simba or SkelMamba. I found no DeGCN accuracy numbers at all in this pass.
- I did not retrieve Papers-with-Code leaderboard snapshots, since the site has been retired or mirrored. The SkeletonAgent compiled table is used instead and is self-reported.
- No source found for a 1D-TCN (e.g. Res-TCN) row in the retrieved tables.

## Q2. Which lightweight models exist and what are their params / FLOPs / latency?

### Takeaway
Every mainstream skeleton GCN or transformer is already "small" by detector standards: 0.24–3 M parameters and roughly 0.6–10 GFLOPs per clip, compared with about 22k params for the planned GRU. The genuinely lightweight options are EfficientGCN-B0 (0.29 M, 2.73 GFLOPs, 90.2 NTU60 X-Sub), SGN (0.69 M, 89.0), ST-GCN++ (1.39 M, 1.95 GFLOPs with 2D input) and Pose-X3D-s (0.24 M, 0.6 GFLOPs, 92.3). FLOP counts across papers are inconsistent, and no paper reports CPU latency on hardware comparable to a Ryzen 6800H.

### Cited Findings
**Params / FLOPs / time table (NTU, per clip as defined by each paper)**
| Model | Params | FLOPs | Acc (as reported) | Source |
|---|---|---|---|---|
| EfficientGCN-B0 | 0.29 M | 2.73 G | 90.2 NTU60 X-Sub; 86.6 NTU120 X-Sub | [EfficientGCN T5–T7](https://arxiv.org/pdf/2106.15125) |
| EfficientGCN-B2 | 0.51 M | 4.05 G | 91.4; 88.0 | [EfficientGCN](https://arxiv.org/pdf/2106.15125) |
| EfficientGCN-B4 | 1.10 M | 8.36 G | 92.1; 88.7 | [EfficientGCN](https://arxiv.org/pdf/2106.15125) |
| SGN | 0.69 M | n/a (EfficientGCN omits it because SGN resamples to ~20 frames) | 89.0 NTU60 X-Sub; 79.2 NTU120 X-Sub; "188 sequences/(second*GPU)" | [EfficientGCN](https://arxiv.org/pdf/2106.15125) |
| 4s-Shift-GCN | 2.76 M | 10.0 G (4 streams) | 90.7 | [EfficientGCN T7](https://arxiv.org/pdf/2106.15125) |
| Shift-GCN (single stream) | — | 2.5 G (1.1 G spatial + 1.4 G temporal shift conv) | — | [Shift-GCN supplement](https://openaccess.thecvf.com/content_CVPR_2020/supplemental/Cheng_Skeleton-Based_Action_Recognition_CVPR_2020_supplemental.pdf) |
| ST-GCN | 3.10 M | 16.32 G | 81.5 | [EfficientGCN T7](https://arxiv.org/pdf/2106.15125) |
| 2s-AGCN | 6.94 M | 37.32 G | 88.5 | [EfficientGCN T7](https://arxiv.org/pdf/2106.15125) |
| MS-G3D | 6.40 M / 48.88 G (EfficientGCN count) vs 2.8 M / 16.7 G (PoseConv3D count, single model on 2D NTU60) | — | 91.5 / 91.9 | [EfficientGCN T7](https://arxiv.org/pdf/2106.15125); [PoseConv3D T3](https://arxiv.org/pdf/2104.13586) |
| ST-GCN++ (2D, 100 frames) | 1.39 M | 1.95 G | 89.29 J / 92.30 B on NTU60 X-Sub 2D | [MMAction2 stgcnpp](https://github.com/open-mmlab/mmaction2/blob/main/configs/skeleton/stgcnpp/README.md) |
| ST-GCN++ (3D) | 1.4 M | 2.96 G | 89.14 J | [MMAction2 stgcnpp](https://github.com/open-mmlab/mmaction2/blob/main/configs/skeleton/stgcnpp/README.md) |
| CTR-GCN | 1.46 M | 1.97 G | 84.9 NTU120 X-Sub (J) | [FreqMixFormer table](https://arxiv.org/pdf/2407.12322); [CTR-GCN supp.](https://openaccess.thecvf.com/content/ICCV2021/supplemental/Chen_Channel-Wise_Topology_Refinement_ICCV_2021_supplemental.pdf) |
| InfoGCN | 1.56–1.57 M | 1.68 G (FreqMixFormer) vs 3.34 G (SkateFormer); 12.97 ms | 85.7 NTU120 avg (J) | [FreqMixFormer](https://arxiv.org/pdf/2407.12322); [SkateFormer T3](https://arxiv.org/html/2403.09508) |
| HD-GCN | 1.66–1.68 M | 1.60 G vs 3.44 G; **72.81 ms** | 86.5 NTU120 avg (J) | same two sources |
| FR-Head | 1.45 M | 3.60 G; 18.49 ms | 86.4 | [SkateFormer T3](https://arxiv.org/html/2403.09508) |
| Koopman | 5.38 M | 8.76 G; 17.86 ms | 86.6 | [SkateFormer T3](https://arxiv.org/html/2403.09508) |
| Hyperformer | 2.71 M | 9.64 G; 18.07 ms | 87.3 | [SkateFormer T3](https://arxiv.org/html/2403.09508) |
| DSTA-Net | 3.45 M | 16.18 G; 13.80 ms | — | [SkateFormer T3](https://arxiv.org/html/2403.09508) |
| SkateFormer | 2.03 M | 3.62 G; 11.46 ms | 88.5 NTU120 avg (J) | [SkateFormer T3](https://arxiv.org/html/2403.09508) |
| BlockGCN | ~1.5 M | — | 96.6 NW-UCLA | [BlockGCN arXiv](https://arxiv.org/pdf/2305.11468) |
| Pose-SlowOnly (PoseConv3D) | 2.0 M | 15.9 G | 93.7 NTU60 X-Sub (2D heatmaps) | [PoseConv3D T2](https://arxiv.org/pdf/2104.13586) |
| Pose-X3D | 531 K | 1.1 G | 92.6 | [PoseConv3D T2](https://arxiv.org/pdf/2104.13586) |
| Pose-X3D-s | 241 K | 0.6 G | 92.3 | [PoseConv3D T2/T10](https://arxiv.org/pdf/2104.13586) |
| C3D-s (PoseConv3D) | 3.4 M | 16.8 G | 92.9 | [PoseConv3D T2](https://arxiv.org/pdf/2104.13586) |

- SkateFormer's timing column was compiled "using publicly available official code", but the timing GPU is not stated; only an A100 is named, for training — [SkateFormer](https://arxiv.org/html/2403.09508)
- EfficientGCN-B0 SG-variant: 3.08 GFLOPs, 0.32 M params, 89.9 X-Sub (from the repo mirror README) — [EfficientGCNv1 gitee mirror](https://gitee.com/yfsong0709/EfficientGCNv1)
- TSkel-Mamba claims about 1/5 of ST-TR's parameters and about 1/31 of its FLOPs, but gives no absolute counts on the overview page. Code: github.com/ryannus2025-ai/TSkel-Mamba — [TSkel-Mamba overview](https://www.alphaxiv.org/overview/2512.11503)
- SkelMamba claims lower complexity than prior transformer SOTA, but I did not retrieve absolute numbers — [SkelMamba](https://arxiv.org/abs/2411.19544v1)
- **Streaming inference:** Continual ST-GCN (CoST-GCN, CoAGCN, CoS-TR) reformulates ST-GCN for frame-by-frame online prediction without reprocessing the window. It reports "up to 109x reduction in time complexity", "on-hardware accelerations of 26x" and 52% less peak memory, with similar accuracy on NTU60/120 and Kinetics — [CoST-GCN](https://arxiv.org/abs/2203.11009)
- PYSKL ships a real-time gesture-recognition demo built on ST-GCN++, which its README says runs in real time on CPU — [PYSKL README](https://github.com/kennymckormick/pyskl)

### Inferences
- FLOPs scale roughly linearly with frames × joints × persons. The 2D ST-GCN++ model (17 joints) costs 1.95 G against 2.96 G for 3D (25 joints), and 17/25 × 2.96 ≈ 2.0 G, which is consistent. By that rule, a 16–32-frame, single-person window should cost about 0.3–0.6 GFLOPs with ST-GCN++. This is my extrapolation, and I have not checked whether MMAction2 counts FLOPs for 1 or 2 persons. At that size, a Ryzen 7 6800H should run it in single-digit milliseconds per tracked person with ONNX Runtime or PyTorch CPU. This is an estimate, not a measurement, so benchmark it locally.
- VRAM is a non-issue for every GCN or transformer listed (≤3 M params, i.e. a few MB of weights). The binding constraints are YOLO26-pose and the CLIP encoder, not the temporal head.
- The only explicit latency outlier is HD-GCN (72.81 ms vs about 11–18 ms for its peers in the same table). Avoid it for real-time use.
- If per-frame updates are needed (re-scoring each person every frame), the continual or online formulation (CoST-GCN), or simply a GRU with carried hidden state, avoids recomputing the whole window. Sliding-window GCN inference at 5–25 fps on a few people is cheap enough either way.

### Gaps
- No source gives measured CPU latency (e.g. ms/clip on a laptop Ryzen) for ST-GCN++, CTR-GCN, EfficientGCN or PoseConv3D. Absolute numbers for CoST-GCN hardware were also not on the abstract page.
- The InfoGCN and HD-GCN FLOPs conflict by about 2× between the FreqMixFormer and SkateFormer tables (1.6–1.7 G vs 3.3–3.4 G). The cause is probably a different frame count, or MACs vs FLOPs, but neither paper says so.
- No params or FLOPs found for Hyper-GCN, ProtoGCN, DeGCN, Simba or SkelMamba.

## Q3. How much accuracy is lost going from 3D to 2D COCO-17 keypoints, and from many training samples to few?

### Takeaway
With good 2D keypoints (HRNet, COCO-17, x/y/score), there is essentially no loss vs Kinect 3D. On NTU60, 2D is often better, and on NTU120 it is within about 0.5–1.5 points for the 2-/4-stream models (single streams can differ by up to about 3.6 either way). Merely projecting noisy 3D onto 2D costs about 2 points. Pose-estimator quality and especially person-box quality matter more than 2D vs 3D. For small data, I found no direct "hundreds of clips" study per family. Semi-supervised NTU60 results at 1% labels (on the order of 400 clips over 60 classes) are only about 33–50%, while NW-UCLA (about 1.5k clips, 10 classes) still trains to about 96–98% from scratch.

### Cited Findings
- **ST-GCN++, PYSKL, 3D vs HRNet-2D** (J / B / 2s / 4s):
  - NTU60 X-Sub: 3D 89.3 / 90.1 / 91.4 / 92.1 vs 2D 89.3 / 92.3 / 92.8 / 93.2
  - NTU60 X-View: 3D 95.6 / 95.5 / 96.7 / 97.0 vs 2D 97.4 / 97.2 / 98.4 / 98.5
  - NTU120 X-Sub: 3D 83.2 / 85.6 / 87.0 / 87.5 vs 2D 84.4 / 84.8 / 86.4 / 86.4
  - NTU120 X-Set: 3D 85.6 / 87.5 / 89.1 / 89.8 vs 2D 88.1 / 88.5 / 90.0 / 90.3
  - Source: [PYSKL ST-GCN++ model zoo](https://github.com/kennymckormick/pyskl/blob/main/configs/stgcn++/README.md)
- **CTR-GCN, PYSKL, 3D vs HRNet-2D** (J / B / 2s / 4s):
  - NTU60 X-Sub: 89.6 / 90.0 / 91.5 / 92.1 vs 90.6 / 92.7 / 93.3 / 93.6
  - NTU60 X-View: 95.6 / 95.4 / 96.6 / 97.0 vs 96.9 / 97.6 / 98.4 / 98.4
  - NTU120 X-Sub: 84.0 / 85.9 / 87.5 / 88.1 vs 82.2 / 84.6 / 85.8 / 86.6
  - NTU120 X-Set: 85.9 / 87.4 / 89.2 / 89.9 vs 84.5 / 88.6 / 89.0 / 90.1
  - Source: [PYSKL CTR-GCN model zoo](https://github.com/kennymckormick/pyskl/blob/main/configs/ctrgcn/README.md)
- MMAction2 ST-GCN++ NTU60 X-Sub: 2D J 89.29, B 92.30, 2s 92.61, 4s 92.77 vs 3D J 89.14, B 90.21, 2s 91.39, 4s 91.87 — [MMAction2 stgcnpp](https://github.com/open-mmlab/mmaction2/blob/main/configs/skeleton/stgcnpp/README.md)
- MS-G3D on NTU60: Kinect-3D 89.4 vs HRNet-2D 91.9 vs MobileNet-2D 90.2. On FineGYM, estimated 3D (DOPE 76.3, VIBE 87.0) is worse than HRNet-2D 92.0, and lifting to 3D "doesn't help in recognition" — [PoseConv3D, Table 13a/b](https://arxiv.org/pdf/2104.13586)
- **Pure dimensionality loss:** 2D-projection of Kinect 3D + MS-G3D gives 86.8, against 88.8 with full 3D. With PoseConv3D the 2D projection gives 89.2 — [PoseConv3D, Table 16](https://arxiv.org/pdf/2104.13586)
- The 2D skeletons for NTU in PoseConv3D/PYSKL come from a top-down HRNet trained on COCO-keypoints. They are stored as coordinate-triplets (x, y, score) with K = 17 COCO keypoints, the same layout as YOLO-pose output — [PoseConv3D](https://arxiv.org/pdf/2104.13586)
- **Pose estimator quality (NTU60, PoseConv3D):** HRNet top-down (COCO AP 0.746) → 93.6; HRNet bottom-up (AP 0.654) → 93.0; MobileNet top-down (AP 0.646) → 92.0 — [PoseConv3D, Table 13c](https://arxiv.org/pdf/2104.13586)
- **Person-box quality** (FineGYM, mean top-1): poses from detection boxes 75.8, from tracking boxes 85.3, from GT boxes 92.0 — [PoseConv3D, Table 13d](https://arxiv.org/pdf/2104.13586)
- **Train/test pose-source mismatch** (FineGYM): MS-G3D HQ→LQ 79.3, LQ→HQ 87.9, LQ→LQ 89.0 vs PoseConv3D 86.5 / 91.6 / 90.7 — [PoseConv3D, Table 5a](https://arxiv.org/pdf/2104.13586)
- **Small labelled fractions (NTU60, self-/semi-supervised pretrain then fine-tune):**
  - MS2L: 33.1 (1%) and 65.2 (10%) X-Sub — [VCL 2026, comparison table](https://arxiv.org/pdf/2601.07666)
  - ASSL: 57.3 / 63.6 (5%) and 64.3 / 69.8 (10%) X-Sub / X-View — [Hi-TRS](https://arxiv.org/pdf/2207.09644)
  - Hi-TRS: 70.7 / 74.8 at 10% (as listed in a later AMR paper) — [AMR](https://arxiv.org/pdf/2606.11450)
  - VCL (2026): 49.4 / 52.4 at 1% and 76.0 / 80.2 at 10% — [VCL](https://arxiv.org/pdf/2601.07666)
- For scale, the NTU60 X-View training split alone is 37,920 clips, so 1% is a few hundred clips spread over 60 classes — [EfficientGCN](https://arxiv.org/pdf/2106.15125)
- **Small datasets trained from scratch:** NW-UCLA (1,494 clips, 10 classes — [Simba](https://arxiv.org/abs/2404.07645)) is solved to 96–98% by CTR-GCN 96.5, HD-GCN 96.9, BlockGCN 96.6 and SkateFormer 98.3 — [FreqMixFormer](https://arxiv.org/pdf/2407.12322); [BlockGCN](https://arxiv.org/pdf/2305.11468); [SkateFormer](https://arxiv.org/html/2403.09508)
- **Transfer helps on small skeleton datasets:** PoseConv3D pretrained on Kinetics-400 skeletons and fine-tuned reaches HMDB51 69.3 and UCF101 87.0. From scratch it gets 58.6 / 79.1, and with a frozen backbone plus linear head 64.9 / 83.1 — [PoseConv3D, Table 14](https://arxiv.org/pdf/2104.13586)
- Task-adjacent evidence for a GRU on 2D keypoints: ST-TGR feeds RTMPose keypoints to a GRU-based "MoGRU" and reports 93.5% on its own teacher-gesture dataset (different task, no GCN comparison) — [ST-TGR, Sensors 2024](https://www.mdpi.com/1424-8220/24/8/2589)

### Inferences
- The 3D→2D concern is largely moot for this project. The NTU-pretrained 2D checkpoints use the same COCO-17 (x, y, score) layout YOLO26-pose emits. The real domain gaps are:
  - the pose estimator (HRNet vs YOLO26-pose)
  - viewpoint (NTU's frontal lab cameras vs elevated restaurant CCTV)
  - seated people with lower bodies occluded by tables
  - box/track quality: PoseConv3D shows detection- vs GT-box poses cost 16 points on FineGYM
- Because ByteTrack-based crops are "tracking boxes", expect accuracy close to the tracking row rather than the GT row of PoseConv3D's Table 13d. Train on clips produced by the same YOLO26-pose + ByteTrack pipeline that runs at inference, not on hand-cropped or clean data.
- Few-shot from scratch on hundreds of clips is risky for any 1–2 M-param model. Fine-tuning a pretrained NTU60-2D GCN (freeze early layers, or train only the head plus the last block) is the standard mitigation, as the PoseConv3D Kinetics→HMDB transfer shows. A 22k-param GRU, by contrast, is unlikely to overfit badly but also gets no transfer.
- NW-UCLA's about 1.5k clips / 10 classes giving 96–98% suggests several hundred clips per class for 2–5 classes is a workable regime for a GCN, though that is clean 3D Kinect data.

### Gaps
- I found no study that trains GRU vs GCN vs transformer on the *same* small 2D dataset (a few hundred clips), so the relative small-data ranking of families is unknown.
- No NTU numbers using YOLO-family pose (vs HRNet) were found.
- No published results were found for upper-body-only keypoints (joints 0–10 plus hips) on NTU.

## Q4. PoseConv3D and RGBPoseConv3D: accuracy, cost, robustness to noisy/missing keypoints, and practicality on a 4 GB GPU

### Takeaway
PoseConv3D (3D-CNN over stacked 2D keypoint heatmaps) is the most robust family to dropped or noisy keypoints and to pose-estimator changes. It loses under 1 point when one limb keypoint per frame is dropped, against 14.3 points for MS-G3D. The tiny X3D-s variant has 0.24 M params and 0.6 GFLOPs at 92.3 NTU60 X-Sub. The cost is per-person heatmap rendering (17×T×56×56) and 3D convolutions. Weights are small enough for a 4 GB GPU, but it is more pipeline work than a coordinate-input GCN. RGBPoseConv3D adds an RGB pathway, which is accurate but too heavy for this deployment.

### Cited Findings
- **Pose-SlowOnly vs MS-G3D (same 2D input):**
  - FineGYM: MS-G3D 92.0 (2.8 M params, 24.7 GFLOPs) vs PoseConv3D 92.4 / 93.2 (1-clip / 10-clip) with 2.0 M params and 15.9 GFLOPs
  - NTU60: 91.9 vs 93.1 / 93.7
  - NTU120: 84.8 vs 85.1 / 86.0
  - Source: [PoseConv3D, Table 3](https://arxiv.org/pdf/2104.13586)
- **Keypoint-drop robustness** (FineGYM mean top-1, one limb keypoint dropped per frame with probability p = 0, 1/8, 1/4, 1/2, 1):
  - MS-G3D: 92.0, 91.0, 90.2, 86.5, 77.7
  - MS-G3D + robust (dropout-style) training: 90.9, 91.0, 91.0, 91.0, 90.6
  - Pose-SlowOnly: 92.4, 92.4, 92.3, 92.1, 91.5
  - Source: [PoseConv3D, Table 4](https://arxiv.org/pdf/2104.13586)
- Robust training lets the GCN recover almost fully under drops (-1.4 at p = 1), at the price of 1.1 points on clean input — [PoseConv3D](https://arxiv.org/pdf/2104.13586)
- **Variants (NTU60 X-Sub):** SlowOnly 93.7 (15.9 G, 2.0 M); C3D 93.0 (25.2 G, 6.9 M); C3D-s 92.9 (16.8 G, 3.4 M); X3D 92.6 (1.1 G, 531 K); X3D-s 92.3 (0.6 G, 241 K). The paper says lightweight 3D backbones cost "≤ 0.3%" — [PoseConv3D, Table 2](https://arxiv.org/pdf/2104.13586)
- **PYSKL checkpoints:**
  - SlowOnly-R50: NTU60 X-Sub J 93.7 / 2s 94.1; NTU60 X-View 96.9 (2s); NTU120 X-Sub 86.7 (2s); NTU120 X-Set 90.3 (2s); K400 49.1 (2s)
  - C3D-light: NTU60 X-Sub 93.3 (2s)
  - X3D-Shallow: NTU60 X-Sub 92.4 (2s)
  - All are trained for 240 epochs on 8 GPUs. The README notes `num_clips=1` speeds up testing with a possible small accuracy drop.
  - Source: [PYSKL PoseC3D zoo](https://github.com/kennymckormick/pyskl/blob/main/configs/posec3d/README.md)
- MMAction2 PoseC3D (SlowOnly-R50, 48-frame uniform sampling, 10-clip): NTU60 X-Sub keypoint 93.6 / limb 93.5 / fusion 94.0 at 20.6 GFLOPs and 2.0 M params; K400 47.4 at 19.1 GFLOPs, 3.2 M — [MMAction2 posec3d](https://github.com/open-mmlab/mmaction2/blob/main/configs/skeleton/posec3d/README.md)
- **Multi-person cost:** for 13 persons, a GCN's params/FLOPs are 2.8 M and 7.2 G (13×), while one PoseConv3D heatmap volume for all persons uses 0.52 M params and 1.6 GFLOPs at 91.3% on Volleyball — [PoseConv3D](https://arxiv.org/pdf/2104.13586)
- **RGBPoseConv3D (RGB + pose):** NTU60 X-Sub / X-View 97.0 / 99.6 and NTU120 X-Sub / X-Set 95.3 / 96.4 — [PoseConv3D, Table 9a](https://arxiv.org/pdf/2104.13586)
- GCN-DevLSTM reports that under a 47% frame-drop rate on NTU60 X-Sub its accuracy falls by 6.07 points, against 18.18 for CTR-GCN (the authors' own experiments) — [GCN-DevLSTM](https://arxiv.org/pdf/2403.15212)

### Inferences
- **Robustness:** For occluded, seated customers with noisy wrist/elbow points, the most transferable lesson is that training-time keypoint dropout/noise ("robust training") nearly closes the GCN's robustness gap. The same augmentation should be applied to whichever model is used, GRU included: randomly zero low-confidence joints, jitter coordinates, drop frames.
- **4 GB GPU:** the weights are tiny (0.24–2 M), so inference memory is dominated by activations of a (1×17×T×56×56) input per person. That is plausible alongside YOLO on 4 GB, but it is not measured. Training SlowOnly-R50 at 48 frames with the default batch of 16 per GPU on 4 GB would likely need a much smaller batch or gradient accumulation (inference from configs, not tested).
- For a 9-day hackathon, PoseConv3D-X3D-s would be the "robust" alternative to a GCN. But only the NTU60 X-Sub and FineGYM X3D-s checkpoints exist in PYSKL, and the heatmap-generation pipeline adds integration work. A coordinate-input GCN or GRU with dropout augmentation is the lower-risk path.
- RGBPoseConv3D is not practical here: it needs an RGB video pathway per person on top of YOLO and CLIP.

### Gaps
- No measured latency or VRAM numbers for PoseConv3D inference on consumer 4 GB GPUs or laptop CPUs were found.
- No robustness benchmark specifically on missing *lower-body* joints (the table-occlusion case) was found. The PoseConv3D experiment drops limb keypoints including knees and ankles.

## Q5. Which repos give ready pretrained 2D COCO-17 checkpoints that can be fine-tuned quickly, and under what licences?

### Takeaway
PYSKL (Apache-2.0, now unmaintained) and MMAction2 (Apache-2.0) are the only sources found with ready NTU60/120 checkpoints trained on HRNet-2D COCO-17 keypoints. These cover ST-GCN++, PoseConv3D and other models. Most 2023–2025 SOTA repos (HD-GCN MIT, BlockGCN Apache-2.0, SkateFormer MIT, ProtoGCN MIT) ship code for 3D Kinect NTU only. CTR-GCN, Shift-GCN and 2s-AGCN are CC BY-NC 4.0, which is acceptable for a hackathon.

### Cited Findings
- **PYSKL:** supports ST-GCN, ST-GCN++, AAGCN, MS-G3D, CTR-GCN, DG-STGCN and PoseConv3D. It provides HRNet 2D skeletons for every supported dataset (NTU60/120, K400, UCF101, HMDB51, FineGYM, Diving48), is licensed Apache-2.0, and the README states "This repo is currently not maintained by the developer" — [PYSKL](https://github.com/kennymckormick/pyskl)
- **PYSKL ST-GCN++** has per-modality checkpoints (j/b/jm/bm) for NTU60 X-Sub/X-View and NTU120 X-Sub/X-Set in both "3dkp" and "hrnet" variants, at download.openmmlab.com/mmaction/pyskl/ckpt/stgcnpp/stgcnpp_ntu60_xsub_hrnet/j.pth and similar paths — [PYSKL ST-GCN++ zoo](https://github.com/kennymckormick/pyskl/blob/main/configs/stgcn++/README.md)
- **PYSKL PoseConv3D** checkpoints (all HRNet 2D): slowonly_r50 / c3d_light / x3d_shallow for ntu60_xsub; slowonly_r50 for ntu60_xview, ntu120_xsub/xset, K400 and GYM; K400-pretrained UCF101/HMDB51 — [PYSKL PoseC3D zoo](https://github.com/kennymckormick/pyskl/blob/main/configs/posec3d/README.md)
- **MMAction2 ST-GCN++** checkpoints for NTU60 X-Sub 2D (joint, bone, joint-motion, bone-motion), e.g. stgcnpp_8xb16-joint-u100-80e_ntu60-xsub-keypoint-2d_20221228-86e1e77a.pth, at 1.39 M params / 1.95 GFLOPs — [MMAction2 stgcnpp](https://github.com/open-mmlab/mmaction2/blob/main/configs/skeleton/stgcnpp/README.md)
- **MMAction2 PoseC3D** checkpoints: NTU60 X-Sub keypoint and limb, FineGYM, K400, and UCF101/HMDB51 (K400-pretrained) — [MMAction2 posec3d](https://github.com/open-mmlab/mmaction2/blob/main/configs/skeleton/posec3d/README.md)
- **Licences** (GitHub API `license` field, Nov 2026, plus LICENSE file heads where the API said NOASSERTION):
  - PYSKL — Apache-2.0 ([repo](https://github.com/kennymckormick/pyskl))
  - MMAction2 — Apache-2.0 ([repo](https://github.com/open-mmlab/mmaction2))
  - CTR-GCN — "Attribution-NonCommercial 4.0 International" ([repo](https://github.com/Uason-Chen/CTR-GCN))
  - Shift-GCN — CC BY-NC 4.0 ([repo](https://github.com/kchengiva/Shift-GCN))
  - 2s-AGCN — CC BY-NC 4.0 ([repo](https://github.com/lshiwjx/2s-AGCN))
  - MS-G3D — MIT ([repo](https://github.com/kenziyuliu/MS-G3D))
  - HD-GCN — MIT ([repo](https://github.com/Jho-Yonsei/HD-GCN))
  - BlockGCN — Apache-2.0 ([repo](https://github.com/ZhouYuxuanYX/BlockGCN))
  - Hyperformer — Apache-2.0 ([repo](https://github.com/ZhouYuxuanYX/Hyperformer))
  - SkateFormer — MIT, last push Sep 2026 ([repo](https://github.com/KAIST-VICLab/SkateFormer))
  - ProtoGCN — MIT ([repo](https://github.com/firework8/ProtoGCN))
  - SGN — MIT ([repo](https://github.com/microsoft/SGN))
  - original ST-GCN — BSD-2-Clause ([repo](https://github.com/yysijie/st-gcn))
  - InfoGCN — no licence file detected ([repo](https://github.com/stnoah1/infogcn))
  - EfficientGCNv1 — no licence detected ([gitee mirror](https://gitee.com/yfsong0709/EfficientGCNv1))
- ProtoGCN is built on the PYSKL codebase and follows its preprocessing, but reports no HRNet-2D results — [ProtoGCN](https://arxiv.org/html/2411.18941)
- BlockGCN's README describes data preparation only for NTU60/120 Kinect skeletons and NW-UCLA — [BlockGCN repo](https://github.com/ZhouYuxuanYX/BlockGCN)

### Inferences
- **Fastest path to a pretrained 2D model:** take the PYSKL or MMAction2 ST-GCN++ NTU60 X-Sub HRNet-2D joint checkpoint. Replace the 60-way FC with a 2–5-way head and fine-tune on clips produced by the YOLO26-pose + ByteTrack pipeline.
  - Feed (x, y, score) with the same normalization PYSKL uses; I did not verify its exact centering/scaling steps.
  - The ST-GCN++ graph (COCO-17 layout) matches YOLO-pose joint order. Verify the index order: both should be the standard COCO order, but this is not confirmed here.
- MMAction2 v1.x is the better-maintained runtime, since PYSKL is unmaintained. Both are Apache-2.0, so licence is not a blocker for any of the PYSKL/MMAction2 options, or even for later commercial use.
- Using CTR-GCN, Shift-GCN or 2s-AGCN code directly would be CC BY-NC (fine for the hackathon, a problem if Easy FnB is later commercialized). The CTR-GCN implementation and checkpoints inside PYSKL fall under PYSKL's Apache-2.0 licence, though the original CTR-GCN is NC. Check with a lawyer before any commercial use.

### Gaps
- I verified checkpoint URLs for PYSKL ST-GCN++ and PoseConv3D and for MMAction2 ST-GCN++ and PoseC3D. I did not open the PYSKL CTR-GCN, MS-G3D, AAGCN or DG-STGCN READMEs' link columns. The PYSKL CTR-GCN README fetch returned accuracies but not checkpoint links, so their availability is likely but unconfirmed.
- I did not check MMAction2's ST-GCN / 2s-AGCN 2D checkpoints, or MMAction2's skeleton demo, for exact keypoint normalization.
- The licence of the TSkel-Mamba repository (github.com/ryannus2025-ai/TSkel-Mamba) is unknown.

## Q6. For fine-grained upper-body gestures (hand waving vs touching head vs drinking, etc.), which models do best on these specific classes?

### Takeaway
Per-class data is sparse. The available numbers show:
- "touch head (headache)" is a weak class for all GCNs (about 81–83% on NTU60 X-Sub), because the hand overlaps the head joints.
- "brushing hair" (about 89–93%) and "hand waving" (about 92–93% on NTU120) are easier.
- The hardest NTU classes are subtle two-hand or object actions (writing, reading, phone, typing), and newer models (ProtoGCN, SkeletonAgent) gain most on those.

No NTU class is literally "raise hand to call staff", so the distractor set (hair touch, head scratch, drinking, pointing, waving) maps onto NTU classes rather than the target itself.

### Cited Findings
- **NTU60 X-Sub class-wise accuracy (FR-Head CVPR23 supplement, values from a search-result snippet; the PDF returned HTTP 403 so I could not verify directly)** — [FR-Head supplement](https://openaccess.thecvf.com/content/CVPR2023/supplemental/Zhou_Learning_Discriminative_Representations_CVPR_2023_supplemental.pdf):
  - touch head: ST-GCN 81.16, 2s-AGCN 82.97, CTR-GCN 81.52, FR-Head 82.97
  - brushing hair: 89.74 / 89.38 / 91.58 / 92.67
  - hand waving (NTU120 X-Sub): 91.61 / 91.61 / 93.07 / 91.97
- GECNN notes that in class 44 (touch head) the hand overlaps the head joint, and suspects joint overlap lowers node-convolution (GCN) accuracy — [GECNN](https://arxiv.org/pdf/1805.06184)
- Skeleton-OOD lists "clapping" and "hand waving" as similar actions with subtle distinctions — [Skeleton-OOD](https://arxiv.org/pdf/2405.20633)
- **Hard classes (NTU60 X-Sub, CTR-GCN / FR-Head / ProtoGCN / SkeletonAgent)** — [SkeletonAgent, Table 6](https://arxiv.org/html/2511.22433):
  - play with phone 69.1 / 73.8 / 75.3 / 78.2
  - writing 56.6 / 59.2 / 63.2 / 68.0
  - wear a shoe 79.5 / 78.8 / 85.7 / 93.4
  - take off a shoe 75.6 / 77.7 / 83.8 / 88.3
- **ProtoGCN gains by class-difficulty group (NTU120, baseline → ProtoGCN)** — [ProtoGCN, Table 5](https://arxiv.org/html/2411.18941):
  - hardest 10 classes 64.1 → 67.1
  - classes 11–30: 78.6 → 81.1
  - classes 31–60: 88.6 → 89.7
  - classes 61–120: 96.0 → 96.4
- EfficientGCN's failure analysis: reading, writing, playing with phone and typing on a keyboard are confused because they involve "slight shaking of two hands". This "is mainly caused by the lack of joints to represent two hands" — [EfficientGCN](https://arxiv.org/pdf/2106.15125)
- EfficientGCN-B4's activated-joint visualisations include drinking water and waving — [EfficientGCN, Fig. 11](https://arxiv.org/pdf/2106.15125)

### Inferences
- COCO-17 has only a wrist per hand (no fingers). Like NTU's sparse hand joints, it cannot separate fine finger configurations: pointing vs open palm, or a raised hand vs a raised hand holding a cup. "Raised hand to call staff" vs "touching or brushing hair" therefore has to be separated mainly by:
  - wrist height relative to the head/shoulders
  - elbow angle (extended arm vs bent arm near the head)
  - wrist-to-nose/ear distance
  - dwell time with a stable wrist (a call is held; hair-touch and head-scratch involve the wrist staying near the head with oscillation)

  These are geometric and temporal cues that a small GRU over well-chosen normalized features (or a GCN) can learn. The GCN-specific weakness on head-touching (joint overlap) suggests adding explicit relative features (wrist–nose, wrist–ear, elbow–shoulder vectors) to the input of whichever model is used.
- Waving to a friend vs calling staff is mostly a semantic or contextual difference (who the person looks at, for how long). It may be inseparable from skeleton alone, so a heuristic or tie-break with gaze/head orientation or staff proximity may be needed.
- Because NTU60 contains drink water (A1), brushing hair (A4), hand waving (A23), pointing (A31) and touch head (A44), an NTU60-2D-pretrained GCN already encodes most of the distractors. This is a concrete reason to prefer fine-tuning a pretrained ST-GCN++ over a from-scratch model if labelled data is scarce. Class numbering is from general NTU knowledge, not verified in this pass.

### Gaps
- No source found with per-class numbers for "drink water", "pointing to something", "salute" or "head scratch" across several models. I could not access the full FR-Head supplement tables (HTTP 403).
- No public benchmark was found for "restaurant/customer hand raising for service" from 2D skeletons. Classroom hand-raising work exists (e.g. the R-FCN RGB detector, skeleton+LSTM/Transformer theses), but I found no LSTM-vs-GCN comparison on the same hand-raising dataset.
- I did not confirm whether any NTU-120 class corresponds to "raise hand".
