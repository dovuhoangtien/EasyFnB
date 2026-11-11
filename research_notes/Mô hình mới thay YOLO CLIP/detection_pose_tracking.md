# Real-time Detection, Pose Estimation & Multi-Object Tracking alternatives to Ultralytics YOLO26 (as of Nov 2026) — for Easy FnB edge restaurant CCTV

Context recap (from assignment): current stack = yolo26n-pose @960 px + ByteTrack (people, raised hands) and yolo26s COCO detect @1280 px every 3rd frame (cups/bowls/food). Measured: RTX 3050 4 GB laptop: pose 22 ms + detect 26 ms (~31 fps total); Ryzen 7 6800H CPU: pose ~75 ms, detect ~138 ms @960. Pain points: small/distant/edge-cut people get no usable keypoints; ID switches under occlusion → duplicate events.

Note on numbers: almost all GPU latencies below are vendor/author-reported on an NVIDIA T4 with TensorRT FP16, batch 1, at 640 px unless stated — not on an RTX 3050 and not at 960/1280 px. CPU numbers are scarce and very hardware-dependent.

## 1. Detection: RF-DETR, D-FINE, DEIM/DEIMv2, RT-DETRv4, LW-DETR, YOLOv12/v13, YOLO26, YOLO-NAS and newer — COCO AP vs latency; best for small objects and for CPU

### Takeaway
On GPU (T4/TensorRT), the Apache-2.0 DETR family now matches or beats YOLO26 at equal latency: RF-DETR-S 53.0 AP @3.5 ms and D-FINE-S 50.6 AP @3.5 ms vs YOLO26-S 47.7–48.6 AP @2.5–2.6 ms; RT-DETRv4 (Apache-2.0, ECCV 2026) and DEIMv2 are in the same band. On CPU, however, YOLO26n/s remain far faster (DETR-type models are roughly 7–10x slower on CPU in the only third-party table found), so for a CPU-only restaurant PC YOLO26 (or an Apache-2.0 small YOLO-like/DEIMv2-N) stays the practical choice; the main reason to switch is licensing (AGPL-3.0) rather than accuracy. YOLO27 is announced but not released.

### Cited Findings
**YOLO26 (Ultralytics, released Jan 2026)**
- YOLO26 released January 2026; features: optional NMS-free one-to-one head (`nms=False`), DFL removed, ProgLoss, STAL (Small-Target-Aware Label Assignment, "improves positive label coverage for small objects"), MuSGD optimizer; exports to TensorRT, ONNX, CoreML, LiteRT, OpenVINO; license AGPL-3.0 or Enterprise — [Ultralytics YOLO26 docs](https://docs.ultralytics.com/models/yolo26/)
- YOLO26 COCO detect @640 (vendor): n 40.9 AP (40.1 e2e), CPU ONNX 38.9 ms, T4 TRT10 1.7 ms, 2.4M params, 5.5 GFLOPs; s 48.6 (47.8 e2e), 87.2 ms CPU, 2.5 ms T4, 9.5M, 20.9 GFLOPs; m 53.1, 220 ms CPU, 4.7 ms T4, 20.4M; l 55.0, 286 ms, 6.2 ms, 24.8M; x 57.5, 526 ms, 11.8 ms, 55.7M — [Ultralytics YOLO26 docs](https://docs.ultralytics.com/models/yolo26/)
- Ultralytics claims up to 43% faster CPU ONNX inference for YOLO26n vs YOLO11n on an Intel Xeon @2.00 GHz (vendor claim) — [Ultralytics YOLO26 docs](https://docs.ultralytics.com/models/yolo26/)
- YOLO27: announced at YOLO Vision 2026; 28 models in n/s/m/l across 7 tasks (incl. pose); preview claims 42.3–60.4 COCO mAP (61.2 at 800 px); docs say models "not yet available", no launch date, recommend YOLO26 for current projects — [Ultralytics YOLO27 docs/blog via search](https://docs.ultralytics.com/ru/models/yolo27); [Ultralytics blog](https://www.ultralytics.com/de/blog/key-highlights-from-ultralytics-yolo-vision-2026)

**Roboflow cross-family benchmark (T4, TensorRT FP16, batch 1; Roboflow-measured, i.e. vendor of RF-DETR) — COCO AP50:95 / latency / params / input res / license**
- RF-DETR-N 48.4 / 2.3 ms / 30.5M / 384 / Apache-2.0; RF-DETR-S 53.0 / 3.5 ms / 32.1M / 512 / Apache-2.0; RF-DETR-M 54.7 / 4.4 ms / 33.7M / 576; RF-DETR-L 56.5 / 6.8 ms / 33.9M / 704 (Apache-2.0); RF-DETR-XL 58.6 / 11.5 ms / 126.4M; RF-DETR-2XL 60.1 / 17.2 ms / 126.9M (XL/2XL and tiny A/F/P = PML 1.0 license, not Apache) — [RF-DETR GitHub](https://github.com/roboflow/rf-detr)
- Tiny RF-DETR (PML 1.0): A 30.5 AP / 1.0 ms / 7.4M / 380; F 37.8 / 1.4 ms / 7.9M; P 41.6 / 1.7 ms / 8.4M / 560 — [RF-DETR GitHub](https://github.com/roboflow/rf-detr)
- Same table, YOLO26 as measured by Roboflow: N 40.3 / 1.7 ms; S 47.7 / 2.6 ms; M 52.5 / 4.4 ms; L 54.1 / 5.7 ms; X 56.9 / 9.6 ms (all AGPL-3.0, 640) — [RF-DETR GitHub](https://github.com/roboflow/rf-detr)
- D-FINE (Apache-2.0, 640): N 42.7 / 2.1 ms / 3.8M; S 50.6 / 3.5 ms / 10.2M; M 55.0 / 5.4 ms / 19.2M; L 57.2 / 7.5 ms / 31.0M; X 59.3 / 11.5 ms / 62.0M — [RF-DETR GitHub](https://github.com/roboflow/rf-detr)
- LW-DETR (Apache-2.0, 640): T 42.9 / 1.9 ms / 12.1M; S 48.0 / 2.6 ms / 14.6M; M 52.6 / 4.4 ms / 28.2M; L 56.1 / 6.9 ms / 46.8M; X 58.3 / 13.0 ms / 118M — [RF-DETR GitHub](https://github.com/roboflow/rf-detr)
- YOLO11 (AGPL-3.0, 640): N 37.4 / 2.5 ms; S 44.4 / 3.2 ms; M 48.6 / 5.1 ms; L 49.9 / 6.5 ms; X 50.9 / 10.5 ms (Roboflow-measured; note lower than Ultralytics' own figures) — [RF-DETR GitHub](https://github.com/roboflow/rf-detr)
- RF100-VL (domain-transfer/fine-tuning benchmark) AP50:95: RF-DETR-S 60.2, RF-DETR-M 61.2, D-FINE-S 60.3, YOLO26-S 57.0, YOLO26-N 52.0, RF-DETR-N 57.7 — [RF-DETR GitHub](https://github.com/roboflow/rf-detr)
- Discrepancy: Roboflow measures YOLO26-N at 40.3 AP vs Ultralytics' 40.9 (40.1 e2e); YOLO26-S 47.7 vs 48.6 (47.8 e2e) — [RF-DETR GitHub](https://github.com/roboflow/rf-detr) vs [Ultralytics docs](https://docs.ultralytics.com/models/yolo26/)

**DEIMv2 (Intellindust AI Lab, released 2025-09-26)**
- COCO AP / params / GFLOPs / latency (hardware not named on README; repo uses TensorRT FP16): Atto 23.8 / 0.5M / 0.8 / 1.10 ms; Femto 31.0 / 1.0M / 1.7 / 1.45 ms; Pico 38.5 / 1.5M / 5.2 / 2.13 ms; N 43.0 / 3.6M / 6.8 / 2.32 ms; S 50.9 / 9.7M / 49.5 / 5.78 ms; M 53.0 / 18.1M / 84.1 / 8.80 ms; L 56.0 / 32.2M / 144.5 / 10.47 ms; X 57.8 / 50.3M / 200 / 13.75 ms — [DEIMv2 GitHub](https://github.com/Intellindust-AI-Lab/DEIMv2)
- DEIMv2 2026 updates: TensorRT ≥10.6 needed for correct FP16 (10.4 can give wrong outputs); 2026-08-13 integrated into Intel Geti with OpenVINO export and INT8 optimization; 2026-10-22 FLOPs calc fixed (earlier omitted attention FLOPs — table GFLOPs may be understated); ONNX export script provided — [DEIMv2 GitHub](https://github.com/Intellindust-AI-Lab/DEIMv2)
- DEIMv2 license is described on the README as a "DEIMv2 License", with commercial licensing requiring contact with the authors (could not open the LICENSE file to confirm; treat as NOT plain Apache-2.0 until verified) — [DEIMv2 GitHub](https://github.com/Intellindust-AI-Lab/DEIMv2)

**RT-DETRv4 (ECCV 2026, Apache-2.0)**
- RT-DETRv4 COCO / T4 latency: S 49.8 AP / 3.66 ms (273 FPS); M 53.7 / 5.91 ms; L 55.4 / 8.07 ms; X 57.0 / 12.90 ms; license Apache-2.0; code released 2025-11-17; accepted ECCV 2026 (2026-06-18); ONNX export + TensorRT via trtexec; uses DINOv3 ViT-B/16 as a distillation teacher during training — [RT-DETRv4 GitHub](https://github.com/RT-DETRs/RT-DETRv4)
- RT-DETRv4 paper: RT-DETRv4-L 55.4 AP at 124 FPS vs YOLOv13-L 53.4 AP (8.63 ms) and DEIM-L 54.7 AP; YOLOv13-X 54.8 AP at 14.67 ms (authors' own table, T4 TensorRT FP16) — [RT-DETRv4 arXiv 2510.25257](https://arxiv.org/html/2510.25257) (via search snippet)
- YOLOv13 numbers conflict across sources: a YOLOv14 paper lists YOLOv13s at 48.2 mAP / 2.48 ms — [YOLOv14 arXiv 2608.04720](https://arxiv.org/pdf/2608.04720) (via search snippet)

**EdgeCrafter / ECDet (Intellindust, arXiv 2603.18739, Mar 2026; TMLR 2026)**
- Compact distilled ViT framework for edge dense prediction; ECDet-S 51.7 box AP with <10M params (COCO-only training); X variants with Objects365 pretraining: 59.9 box AP, 49.8 mask AP, 75.9 keypoint AP; ECPose-X 74.8 keypoint AP (COCO only); latency not given on abstract page; code at intellindust-ai-lab.github.io/projects/EdgeCrafter — [EdgeCrafter arXiv](https://arxiv.org/abs/2603.18739); acceptance to TMLR 2026 noted in [DEIMv2 GitHub news](https://github.com/Intellindust-AI-Lab/DEIMv2)

**YOLO-NAS**
- super-gradients framework is Apache-2.0 but YOLO-NAS pretrained weights are under Deci's license "for research and non-commercial use only"; sources conflict on whether from-scratch training is commercially usable; Deci acquired by NVIDIA and super-gradients no longer actively maintained by the original team — [NVIDIA forum thread](https://forums.developer.nvidia.com/t/licensing-and-usage-terms-for-yolo-nas-model/326342); [Roboflow licensing](https://roboflow.com/licensing)

**CPU-only evidence**
- Third-party OpenCV 5 DNN benchmark (OpenCV / ONNX Runtime 1.25.1, ms; model sizes and input resolutions not stated): yolo26n 9.9/9.6 (Intel i9), 24.9/19 (Intel i7), 13.6/30.7 (AMD); RF-DETR 93.3/97.4 (i9), 226.6/227.4 (i7), 73.5/176.9 (AMD); RT-DETR 118.6/99.9 (i9), 313.1/243.8 (i7); YOLOX 24.2/23.8 (i9); YOLOv8 12.4/13.0 (i9) — [OpenCV 5 DNN Benchmarks wiki mirror](https://lab.trianta.dev/mirrors/opencv.opencv/wiki/OpenCV-5-DNN-Benchmarks)
- Roboflow's own CPU cookbook: RF-DETR-Small on a shared Colab vCPU, batch 1: PyTorch eager ~377 ms, ONNX Runtime ~364 ms, OpenVINO FP32 ~357 ms, OpenVINO FP16 ~400 ms (slower); INT8 not measured; differences "within noise" — [RF-DETR CPU cookbook](https://rfdetr.roboflow.com/latest/cookbooks/export-cpu/)
- Frigate NVR docs recommend RF-DETR only on discrete Intel Arc GPUs (not iGPU/CPU) — [Frigate docs commit (via search)](https://git.laurivan.com/Mirrors/blakeblackshear.frigate/commit/18af06237c301cfb6d08eb4b07a97fefe5a5cb0b)

### Inferences
- GPU (RTX 3050 4 GB): every model in the 2–6 ms T4 band should run well above 5 fps/camera even at 960–1280 px. The team's measured 26 ms for yolo26s @1280 is much slower than T4 TensorRT numbers would suggest (2.5 ms @640 → ~10 ms @1280 by pixel scaling), so the biggest cheap win is probably exporting to TensorRT FP16 (and/or the NMS-free head) rather than switching architectures. This is an extrapolation, not measured.
- Accuracy-per-latency on GPU: RF-DETR-S (53.0 AP @3.5 ms, Apache-2.0) and D-FINE-S (50.6 @3.5 ms, Apache-2.0) give +2–5 AP over YOLO26-S at ~1 ms more latency on T4. RF-DETR's higher RF100-VL score (60.2 vs 57.0) suggests it fine-tunes better to new domains like Vietnamese tableware.
- Small objects (cups, chopsticks, napkins): no source gave AP_small per model, so this is judgment: YOLO26's STAL targets small objects explicitly and accepts high input res cheaply; RF-DETR's published configs use low input res (384–704), which hurts tiny objects unless run at higher res (cost grows quadratically for ViT backbones). For chopsticks/napkins, fine-tuning on own data + high-res/tiled inference (SAHI-style crops of table regions) will matter more than the architecture choice.
- CPU-only restaurant PC: DETR models (RF-DETR ~30M params even at "N") are ~7–10x slower than yolo26n on CPU in the only third-party table found; RF-DETR-S at ~360 ms/frame on a vCPU is still under 5 fps. YOLO26n/s (or DEIMv2-N/Pico, 1.5–3.6M params, OpenVINO+INT8 via Intel Geti) are the realistic CPU options. On Intel iGPUs, OpenVINO export is supported by YOLO26 and DEIMv2.
- If AGPL-3.0 is a blocker, the cleanest Apache-2.0 drop-ins for GPU are RF-DETR N/S/M/L, D-FINE, LW-DETR and RT-DETRv4; DEIMv2's license must be checked first.

### Gaps
- No RTX 3050 / laptop-GPU latency numbers found for any model; no Jetson numbers for RF-DETR/D-FINE/DEIMv2 retrieved.
- No COCO AP_small comparison across YOLO26 / RF-DETR / D-FINE / DEIMv2 retrieved.
- YOLOv12 numbers and license not retrieved (YOLOv12/v13 are built on the Ultralytics codebase, likely AGPL-3.0 — unverified in this session).
- DEIMv2 LICENSE file could not be opened (404); DEIM v1 license not retrieved.
- EdgeCrafter latency, sizes other than S/X, and code license not retrieved.
- OpenCV benchmark page does not state model sizes/resolutions, so its RF-DETR vs yolo26n gap is indicative only.

## 2. Pose: RTMPose / RTMO / RTMW (MMPose), DWPose, ViTPose(+), Sapiens, YOLO-pose and 2025–2026 models — accuracy, speed, crowds/small/partial people, hand keypoints

### Takeaway
YOLO26n-pose (57.2 AP @640) is the weakest-accuracy option in the field; at similar GPU cost RTMO-s/m (67.7–72.6 COCO AP, 67.3–71.1 CrowdPose AP) and the top-down RTMPose family (68.5–76.5 COCO AP, 3–19 ms per person crop on CPU) are far more accurate. A top-down RTMPose on detector crops is the most promising fix for small/distant people (each person is re-sampled to 256x192), and RTMW/DWPose (133 whole-body keypoints incl. 21 per hand) or a dedicated RTMPose hand model can distinguish an open palm from a hand holding a cup. Newer 2025–2026 models (RF-DETR Keypoint 71.8 AP, Apache-2.0; ECPose-X 74.8; DETRPose) are GPU-oriented.

### Cited Findings
**YOLO26-pose (Ultralytics, AGPL-3.0)**
- COCO keypoints val @640 (e2e): n 57.2 AP / 83.3 AP50, CPU ONNX 40.3 ms, T4 TRT 1.8 ms, 2.9M params, 7.6 GFLOPs; s 63.0 / 85.3 ms / 2.7 ms / 10.4M; m 68.8 / 218 ms / 5.0 ms / 21.5M; l 70.4 / 275 ms / 6.5 ms / 25.9M; x 71.6 / 565 ms / 12.2 ms / 57.6M; default models predict 17 COCO keypoints with optional visibility/confidence; Hand-Keypoints dataset available for custom training — [Ultralytics Pose docs](https://docs.ultralytics.com/tasks/pose/)
- YOLO26 paper reports up to +7.2 pose AP over YOLO11 using RLE (Residual Log-Likelihood Estimation) — [Ultralytics YOLO26 docs](https://docs.ultralytics.com/models/yolo26/)
- Roboflow-measured YOLO26-pose (T4): N 55.9 / 1.9 ms; S 62.0 / 2.7 ms; M 68.0 / 4.6 ms; L 69.2 / 5.9 ms; X 71.0 / 9.8 ms; YOLO11-pose N 48.9, X 68.6 — [RF-DETR GitHub](https://github.com/roboflow/rf-detr)

**RF-DETR Keypoint (preview, Roboflow, Apache-2.0)**
- COCO person keypoints 71.8 AP (OKS), 9.7 ms T4, 40.7M params, 576 px, Apache-2.0 (preview) — [RF-DETR GitHub](https://github.com/roboflow/rf-detr)

**RTMO (one-stage, MMPose; older, arXiv Dec 2023)**
- COCO val @640, latency on V100 ONNXRuntime: RTMO-s 67.7 AP / 8.9 ms; RTMO-m 70.9 / 12.4 ms; RTMO-l 72.4 / 19.1 ms; trained on body7: s 68.6, m 72.6, l 74.8; RTMO-t (body7, 416) 57.4 AP — [MMPose RTMO](https://github.com/open-mmlab/mmpose/tree/main/projects/rtmo)
- CrowdPose test: RTMO-s 67.3, m 71.1, l 73.2 AP (CrowdPose-trained; AP-hard 59.1/63.4/65.3); RTMO-l body7 83.8 AP — [MMPose RTMO](https://github.com/open-mmlab/mmpose/tree/main/projects/rtmo)
- RTMO "runs faster than RTMPose on images with more than 4 persons"; ONNX via MMDeploy ≥1.3.1, pre-exported ONNX for body7 t/s/m/l; rtmlib supports CPU/GPU via OpenCV, ONNXRuntime, OpenVINO (no RTMO CPU latency given) — [MMPose RTMO](https://github.com/open-mmlab/mmpose/tree/main/projects/rtmo)
- RTMO-l 73.2% CrowdPose AP described as new SOTA for one-stage methods (2023 claim) — [RTMO arXiv 2312.07526](https://arxiv.org/html/2312.07526v2) (via search)

**RTMPose (top-down, MMPose; older, 2023) — per-person-crop latency**
- Body 17-kp, 256x192 (AIC+COCO): RTMPose-t 68.5 AP, 3.34M params, 0.36 GFLOPs, 3.20 ms ONNXRuntime CPU (i7-11700), 1.06 ms TRT FP16 (GTX 1660 Ti), 9.02 ms ncnn (Snapdragon 865); -s 72.2 AP, 5.47M, 4.48 ms CPU, 1.39 ms GPU; -m 75.8 AP, 13.59M, 11.06 ms CPU, 2.29 ms GPU; -l 76.5 AP, 27.66M, 18.85 ms CPU, 3.46 ms GPU; -m/-l @384x288 77.0/77.3; Body8-trained RTMPose-x 78.8 @384x288 — [MMPose RTMPose](https://github.com/open-mmlab/mmpose/tree/main/projects/rtmpose)
- Pipeline RTMDet-nano (320) + RTMPose-t: 12.4 ms ONNXRuntime CPU / 2.47 ms TensorRT; with RTMPose-m: 26.6 ms / 4.31 ms (assuming detection every 5 frames) — [MMPose RTMPose](https://github.com/open-mmlab/mmpose/tree/main/projects/rtmpose)
- Third-party CPU: RTMPose 4.8–15.7 ms (i9/i7, OpenCV/ORT), 5.8–7.3 ms (AMD) — [OpenCV 5 DNN Benchmarks](https://lab.trianta.dev/mirrors/opencv.opencv/wiki/OpenCV-5-DNN-Benchmarks)
- Deployment: MMDeploy → ONNX, TensorRT, ncnn, OpenVINO, CoreML, RKNN, TorchScript; rtmlib runs with OpenCV/ONNXRuntime/OpenVINO without PyTorch/MMCV — [MMPose RTMPose](https://github.com/open-mmlab/mmpose/tree/main/projects/rtmpose)

**Whole-body / hand keypoints (RTMW, DWPose, RTMPose-hand)**
- COCO-WholeBody (133 kp incl. hands/face/feet): RTMPose-m (256x192) 58.2 Whole AP @2.22 GFLOPs; -l (384x288) 64.8; -x 65.3; RTMW (Cocktail14) 58.2 (m, 256x192, 4.3 GFLOPs) to 70.2 Whole AP (x, 384x288, 29.3 GFLOPs); distilled 133-kp models are "powered by DWPose" (e.g. RTMPose-m 60.6 Whole AP on COCO+UBody) — [MMPose RTMPose](https://github.com/open-mmlab/mmpose/tree/main/projects/rtmpose)
- Dedicated hand: RTMDet-nano hand detector 76.0 AP on OneHand10K @320, 0.31 GFLOPs; RTMPose-m hand (21 kp, 256x256) 81.5 PCK@0.2 on COCO-WholeBody-Hand, 96.4 on Hand5, 2.58 GFLOPs — [MMPose RTMPose](https://github.com/open-mmlab/mmpose/tree/main/projects/rtmpose)

**2025–2026 pose models**
- DETRPose (arXiv 2506.13027, 2025; v2 2026): DETRPose-S 67.0 COCO AP, 11.5M params, 2.39 ms (hardware not stated); DETRPose-X 75.1 CrowdPose AP (vs ED-Pose-SwinL 76.6) at 232G vs 3048G FLOPs; compares YOLO11-Pose-X 67.2 AP / 4.93 ms; code github.com/SebastianJanampa/DETRPose (code license not stated) — [DETRPose arXiv](https://arxiv.org/abs/2506.13027)
- ECPose-X (EdgeCrafter, 2026): 74.8 keypoint AP COCO-only, 75.9 with Objects365 pretraining — [EdgeCrafter arXiv](https://arxiv.org/abs/2603.18739)
- FSEM-Pose (2026, CMES journal): YOLOv10-based real-time model evaluated on COCO and CrowdPose; no headline numbers retrieved — [ScienceDirect/CMES](https://www.sciencedirect.com/org/science/article/pii/S1526149226001062) (via search)
- Sapiens (Meta): 0.3B/0.6B/1B/2B params, natively trained at 1024x1024; Sapiens-Lite claims "4x faster" inference; Sapiens2 released (github.com/facebookresearch/sapiens2); license is a project-specific LICENSE file (not named on README) — [Sapiens GitHub](https://github.com/facebookresearch/sapiens)

### Inferences
- Accuracy gap: at the "nano/small" tier, YOLO26n-pose 57.2 AP vs RTMO-s 67.7–68.6 AP (+10 AP) and top-down RTMPose-s 72.2 AP. YOLO26s-pose (63.0) or m (68.8) closes part of the gap within Ultralytics.
- Small/distant people: single-stage models (YOLO-pose, RTMO) see a 30–40 px tall person at the full-frame scale, so keypoint heatmaps/regressions are coarse. Top-down RTMPose upsamples each detected person crop to 256x192, which is the standard way to rescue small people — at a per-person cost (≈3–11 ms per person on CPU for t–m; ≈1–2 ms on a GTX 1660 Ti class GPU). A hybrid (keep YOLO26 person boxes + ByteTrack/TrackTrack, run RTMPose-t/s only on small or "candidate raised-hand" tracks) is likely cheapest. This is a design inference, not a measured result.
- Edge-cut / partial bodies: no source quantified truncation robustness; top-down models still output all 17 points with low confidence for out-of-frame joints, so the raised-hand rule should rely only on wrist/elbow/shoulder confidence, not the full skeleton.
- Crowded dining rooms: RTMO's CrowdPose AP (67–73) and the note that it beats RTMPose speed with >4 people make it the best-documented one-stage option for many people per frame; Apache-2.0 via MMPose (license not re-verified here).
- Open palm vs holding a cup: 17-kp COCO skeletons have no finger points. RTMW/DWPose whole-body (133 kp, 21 per hand) or the RTMPose-m hand model on wrist-centred crops (2.58 GFLOPs) could classify an open hand cheaply, e.g. only when a wrist is above the shoulder. Alternatively, train the Ultralytics Hand-Keypoints task (AGPL).
- Sapiens (0.3–2B params at 1024 px) is far too heavy for ≥5 fps on an RTX 3050 4 GB or CPU.

### Gaps
- No CPU latency for RTMO, RTMW, DETRPose or RF-DETR Keypoint found; RTMO latency is V100 only.
- ViTPose/ViTPose+ numbers and license not retrieved (generally GPU-heavy; not verified this session).
- No benchmark on small-person AP (e.g. COCO AP_M split) or truncated-body robustness across these models.
- Hand AP specifically for RTMW not shown on the page; DWPose standalone repo/license not fetched.
- MMPose/RTMPose/RTMO license (believed Apache-2.0) not explicitly confirmed in fetched pages; Sapiens license text not read.
- RF-DETR Keypoint is a "preview"; no CrowdPose numbers.

## 3. Tracking: ByteTrack vs BoT-SORT, OC-SORT, Deep OC-SORT, StrongSORT, Hybrid-SORT, TrackTrack, McByte, SAM2MOT etc. — ID switches, re-ID cost, cheapest ID-switch reduction

### Takeaway
ByteTrack is the weakest on identity metrics among modern trackers; BoT-SORT (+ReID) adds ~3 IDF1 on MOT17 and, inside Ultralytics, can reuse the detector's own features (near-zero extra cost) or a pre-built yolo26n-reid ONNX. Ultralytics now ships TrackTrack (CVPR 2025, MIT) as its default tracker; its Track-Aware Initialization explicitly suppresses spawning new tracks on detections that overlap existing tracks — directly targeting the "duplicate person/event" problem. Heavier SOTA (SAM2MOT, OccluBoost/BoostTrack with ReID) improve IDF1 further but cost more.

### Cited Findings
- Ultralytics trackers: BoT-SORT, ByteTrack, OC-SORT, Deep OC-SORT, FastTracker, TrackTrack (the last four added from ultralytics 8.4.63); TrackTrack (`tracktrack.yaml`) is the default; BoT-SORT ReID off by default, `with_reid: True`; `model: auto` uses native YOLO backbone features, falls back to `yolo26n-cls.pt`; pre-built ONNX ReID encoders yolo26n-reid.onnx … yolo26x-reid.onnx; custom ReID can be .onnx/.engine/OpenVINO; tunables track_high_thresh, track_low_thresh, new_track_thresh, track_buffer, match_thresh, fuse_score, gmc_method — [Ultralytics Track docs](https://docs.ultralytics.com/modes/track/)
- Secondary source says TrackTrack became Ultralytics default since v8.4.76 (2026-06-24), citing the Ultralytics docs — [Forasoft tracker guide](https://www.forasoft.com/learn/ai-for-video-engineering/articles-ai/multi-object-tracking-deepsort-bytetrack-ocsort)
- TrackTrack (Shim et al., KAIST, CVPR 2025): Track-Perspective-Based Association (TPA) + Track-Aware Initialization (TAI); TAI suppresses new-track initialization for detections heavily overlapping active tracks or more confident detections; authors claim SOTA on MOT17, MOT20, DanceTrack — [mlanthology CVPR 2025](https://mlanthology.org/cvpr/2025/shim2025cvpr-focusing/)
- TrackTrack reference code: MIT license; pipeline uses YOLOX detections + FastReID features — [TrackTrack GitHub](https://github.com/kamkyu94/TrackTrack)
- Paper results, MOT17 test, private detections (MOTA / IDF1 / HOTA): DeepSORT 78.0/74.5/61.2; StrongSORT 78.3/78.5/63.5; ByteTrack 80.3/77.3/63.1; OC-SORT 78.0/77.5/63.2; BoT-SORT-ReID 80.5/80.2/65.0; Deep OC-SORT 79.4/80.6/64.9; DanceTrack HOTA: ByteTrack 47.7, OC-SORT 55.1, Deep OC-SORT 61.3; MOT20 Deep OC-SORT 63.9 HOTA (all pre-2025 paper results) — [Forasoft tracker guide](https://www.forasoft.com/learn/ai-for-video-engineering/articles-ai/multi-object-tracking-deepsort-bytetrack-ocsort)
- Roboflow `trackers` v2.3.0, shared YOLOX detections, default params, HOTA (MOT17 / DanceTrack / SportsMOT): SORT 58.4/47.2/70.8; ByteTrack 60.1/53.3/73.0; OC-SORT 61.9/54.1/71.7; BoT-SORT 63.7/57.8/73.8; McByte 64.1/67.2/76.5 — [Forasoft tracker guide](https://www.forasoft.com/learn/ai-for-video-engineering/articles-ai/multi-object-tracking-deepsort-bytetrack-ocsort)
- BoxMOT benchmark, MOT17 ablation split (HOTA / MOTA / IDF1): OccluBoost 71.10/78.50/85.28; BoT-SORT 69.68/78.23/82.33; BoostTrack 69.25/75.91/83.20; StrongSORT 68.05/76.19/80.76; Deep OC-SORT 67.95/75.83/80.54; ByteTrack 67.68/78.04/79.16; Hybrid-SORT 67.31/74.09/78.87; OC-SORT 66.44/74.55/77.90; SFSORT 62.65/76.87/69.18; BoxMOT is AGPL-3.0; detector/ReID per row not stated; no IDSW/FPS listed — [BoxMOT GitHub](https://github.com/mikel-brostrom/boxmot)
- Cost on CPU (YOLOv8-S, 20 pedestrians, 1280x720): ByteTrack association ≈0.4 ms; BoT-SORT-ReID appearance extraction ≈18 ms + 0.6 ms association; full pipeline 14.4 ms vs 32.6 ms per frame; ≈35 vs 16 streams on a 16-vCPU server — [Forasoft tracker guide](https://www.forasoft.com/learn/ai-for-video-engineering/articles-ai/multi-object-tracking-deepsort-bytetrack-ocsort)
- Licenses: ByteTrack, OC-SORT, BoT-SORT reference repos and TrackTrack code MIT; Roboflow `trackers` Apache-2.0; Ultralytics and BoxMOT AGPL-3.0 (secondary source) — [Forasoft tracker guide](https://www.forasoft.com/learn/ai-for-video-engineering/articles-ai/multi-object-tracking-deepsort-bytetrack-ocsort)
- SAM2MOT (arXiv 2504.04519, 2025): DanceTrack 75.8 HOTA / 83.9 IDF1, +2.1 HOTA / +4.5 IDF1 over next best; built on SAM2 segmentation (heavy) — [SAM2MOT arXiv](https://arxiv.org/html/2504.04519v1)
- AR-MOT (arXiv 2601.01925, 2026, MLLM-based): 66.1 MOTA / 60.7 IDF1 on MOT17, below SOTA; not a practical edge option — [AR-MOT arXiv](https://arxiv.org/pdf/2601.01925)
- 2025 MOT survey: all performant methods use a re-ID model; camera-motion compensation adds ~1.0–1.5 HOTA on MOT17 — [MOT survey arXiv 2506.13457](https://arxiv.org/pdf/2506.13457) (via search)

### Inferences
- Cheapest ID-switch reduction for this stack, in order of cost: (1) switch tracker config to TrackTrack (default in current Ultralytics; TAI targets duplicate-track spawning) and/or raise `track_buffer` so tracks survive short occlusions by waiters/pillars; (2) BoT-SORT with `with_reid: True, model: auto` (reuses YOLO features, near-free) — expected ~+3 IDF1 vs ByteTrack on MOT17-like data; (3) a separate ReID ONNX (yolo26n-reid or OSNet/LightMBN) at ~1 ms/person GPU or ~1 ms/person CPU (≈18 ms for 20 people on CPU per the cited example).
- Fixed CCTV cameras: set `gmc_method: none` to save CPU (camera-motion compensation only helps moving cameras).
- For restaurant events, event-level de-duplication (e.g., one "raised hand" event per table zone per N seconds, keyed to table ID rather than track ID) likely removes more duplicate alerts than any tracker swap; diners are mostly stationary, so table-zone association is a strong prior. This is a design inference.
- Benchmarks are on pedestrians/dancers; restaurant scenes (seated, mostly static people, heavy occlusion by tables/staff) are different, so gains should be validated on own footage.

### Gaps
- TrackTrack's numeric HOTA/IDF1/IDSW on MOT17/MOT20/DanceTrack could not be retrieved (README results are images; CVF PDF returned 403).
- No IDSW counts found in a single consistent table; FastTracker and McByte details (license, cost) not retrieved.
- MOTIP, SAMBA-MOTR and other end-to-end trackers not covered (GPU-heavy; not retrieved).
- No re-ID latency figures for yolo26n-reid.onnx retrieved.

## 4. Open-vocabulary detectors for restaurant objects without training (YOLOE, YOLO-World v2, Grounding DINO 1.5 Edge, OWLv2, Florence-2, SAM 3, DINO-X) — speed, accuracy, and "crumpled napkin / dirty plate / menu / tray"

### Takeaway
YOLOE-26 is the only open-vocab family with first-class edge export (text prompts baked into ONNX/OpenVINO/TensorRT) at YOLO-like cost, with 24.7–40.6 LVIS zero-shot AP; Grounding DINO 1.5 Edge (36.2 LVIS AP, >10 fps on Orin NX at 640) and SAM 3 (48.8 LVIS mask AP but 30 ms on an H200) are heavier. None reliably recognise state attributes such as "dirty" or "crumpled" — YOLOE's docs say prompts describe appearance, not state — so use open-vocab for object classes (tray, menu, napkin, plate) and auto-labelling, then fine-tune a closed-set model or add a crop classifier for state.

### Cited Findings
- YOLOE LVIS minival zero-shot mAP50-95 (text / visual prompt): YOLOE-26n 24.7/21.9; 26s 30.8/28.6; 26m 35.4/33.9; 26l 37.8/36.3; 26x 40.6/38.5; rare-class APr 20.5–37.4; prompt-free (built-in 4,585-name vocabulary) 16.6–29.9 AP — [Ultralytics YOLOE docs](https://docs.ultralytics.com/models/yoloe/)
- YOLO-Worldv2 LVIS AP 24.4 (S) / 32.4 (M) / 35.5 (L); YOLOE-v8s +3.5 AP over YOLO-Worldv2-S at 1.4x inference speed and ~1/3 training cost; YOLOE also outputs masks — [Ultralytics YOLOE docs](https://docs.ultralytics.com/models/yoloe/)
- YOLOE export: call `set_classes()` then export; classes "baked into the exported weights" for ONNX, OpenVINO, TensorRT, CoreML, LiteRT, RKNN; changing classes requires re-export; on CPU (yoloe-26s-seg) forward time grows ~19% from 80→1,203 classes and ~89% at 4,585 classes — [Ultralytics YOLOE docs](https://docs.ultralytics.com/models/yoloe/)
- YOLOE guidance: use everyday category names; prompts describe appearance, not context or state; rare categories are the weak spot; use visual prompts for hard-to-name objects; license AGPL-3.0 or Enterprise (staff comment) — [Ultralytics YOLOE docs](https://docs.ultralytics.com/models/yoloe/)
- Grounding DINO 1.5 Edge: 36.2 zero-shot AP on LVIS-minival; 75.2 FPS with TensorRT (on A100, per secondary summary); >10 FPS on NVIDIA Orin NX at 640x640 (paper); a secondary summary lists 5.5 FPS on Orin NX at 800 px — [Grounding DINO 1.5 arXiv 2405.10300](https://arxiv.org/html/2405.10300v2); [EmergentMind summary](https://api.emergentmind.com/topics/grounding-dino-1-5-edge)
- SAM 3 (Meta, Nov 2025): 30 ms per image with 100+ objects on an H200; zero-shot LVIS mask AP 48.8 vs prior best 38.5 (DINO-X); SA-Co/Gold cgF1 54.1 vs OWLv2 24.6; paper says OWLv2/GroundingDINO suffer low precision and degrade on long-tail concepts — [SAM 3 arXiv 2511.16719](https://arxiv.org/html/2511.16719v2) (via search)
- Florence-2-base ~230M and -large ~770M params (secondary; no speed data found) — [EmergentMind SAM 3 topic (via search)](https://api.emergentmind.com/topics/segment-anything-model-3-sam-3)

### Inferences
- "menu", "tray", "napkin", "plate", "bowl", "chopsticks" are plain nouns and are plausible text prompts for YOLOE-26s/m on the RTX 3050; "dirty plate" and "crumpled napkin" are states, which YOLOE explicitly does not model well. A practical pattern: YOLOE (or SAM 3 offline on a big GPU) to auto-label a few hundred frames of the restaurant → fine-tune YOLO26s / RF-DETR-S / D-FINE-S closed-set with classes like plate_empty, plate_with_food, napkin_used, or run a small crop classifier (CLIP-style) on detected plates. Accuracy for these restaurant prompts is untested.
- On CPU, YOLOE with a small baked vocabulary (≈10–20 classes) should cost close to a regular YOLO26 of the same size; Grounding DINO / OWLv2 / Florence-2 / SAM 3 are not realistic at ≥5 fps on CPU or a 4 GB laptop GPU per camera.

### Gaps
- No measured speeds for OWLv2 or Florence-2 found; T-Rex2/DINO-X are API-centric (not verified this session).
- No YOLOE-26 T4/CPU latency table on the docs page.
- No evaluation of any open-vocab model on restaurant-specific prompts (napkin, menu, tray, dirty plate) found.
- Licenses of Grounding DINO 1.5 Edge (believed API/closed), OWLv2, Florence-2, SAM 3 weights not verified in this session.

## 5. Licenses (Ultralytics AGPL-3.0 confirmation and each alternative)

### Takeaway
Confirmed: Ultralytics YOLO11/YOLO26/YOLOE are AGPL-3.0 with a paid Enterprise license for closed commercial use. Apache-2.0 alternatives with confirmed licenses: RF-DETR N/S/M/L + Seg + Keypoint (but not A/F/P/XL/2XL, which are PML 1.0), D-FINE, LW-DETR, RT-DETRv4. TrackTrack/ByteTrack/OC-SORT/BoT-SORT reference code is MIT; BoxMOT is AGPL-3.0. DEIMv2 and YOLO-NAS weights are NOT simply permissive.

### Cited Findings
- YOLO26: AGPL-3.0 or Enterprise license — [Ultralytics YOLO26 docs](https://docs.ultralytics.com/models/yolo26/)
- YOLOv8/YOLO11/YOLO26 AGPL-3.0; commercial use including network-served use generally requires open-sourcing the application or buying a commercial license (Roboflow's statement) — [RF-DETR GitHub](https://github.com/roboflow/rf-detr)
- YOLOE: production use requires AGPL-3.0 compliance or Enterprise license (Ultralytics staff comment) — [Ultralytics YOLOE docs](https://docs.ultralytics.com/models/yoloe/)
- Apache-2.0: `rfdetr` package, RF-DETR Nano–Large detection, all RF-DETR-Seg sizes, RF-DETR Keypoint, LW-DETR, D-FINE; PML 1.0 (Roboflow Platform Model License): RF-DETR Atto/Femto/Pico/XL/2XL — commercial use included on Roboflow, self-hosted commercial use requires Enterprise add-on — [RF-DETR GitHub](https://github.com/roboflow/rf-detr)
- RT-DETRv4: Apache-2.0 — [RT-DETRv4 GitHub](https://github.com/RT-DETRs/RT-DETRv4)
- DEIMv2: "DEIMv2 License"; commercial licensing via the authors (LICENSE file not verified) — [DEIMv2 GitHub](https://github.com/Intellindust-AI-Lab/DEIMv2)
- YOLO-NAS: super-gradients Apache-2.0, pretrained weights research/non-commercial only (conflicting statements on from-scratch training) — [NVIDIA forum](https://forums.developer.nvidia.com/t/licensing-and-usage-terms-for-yolo-nas-model/326342)
- TrackTrack code MIT — [TrackTrack GitHub](https://github.com/kamkyu94/TrackTrack); BoxMOT AGPL-3.0 — [BoxMOT GitHub](https://github.com/mikel-brostrom/boxmot); ByteTrack/OC-SORT/BoT-SORT reference repos MIT and Roboflow `trackers` Apache-2.0 (secondary) — [Forasoft tracker guide](https://www.forasoft.com/learn/ai-for-video-engineering/articles-ai/multi-object-tracking-deepsort-bytetrack-ocsort)
- Sapiens: project-specific LICENSE (name not shown on README); portions Apache-2.0 — [Sapiens GitHub](https://github.com/facebookresearch/sapiens)
- EdgeCrafter and DETRPose papers are CC BY 4.0 (paper license only; code license not stated) — [EdgeCrafter arXiv](https://arxiv.org/abs/2603.18739); [DETRPose arXiv](https://arxiv.org/abs/2506.13027)

### Inferences
- For a hackathon demo (14/11/2026) AGPL-3.0 is not a blocker; for a commercial SaaS/edge product sold to restaurants, AGPL network/distribution obligations or an Ultralytics Enterprise license apply. A fully permissive stack is feasible: RF-DETR-S/N or D-FINE-S (detect, Apache-2.0) + RTMPose/RTMO via rtmlib (pose; MMPose believed Apache-2.0) + TrackTrack/ByteTrack/OC-SORT (MIT) or Roboflow `trackers` (Apache-2.0) — but note the CPU-speed penalty of DETR detectors.
- Using Ultralytics' built-in TrackTrack implementation still falls under the AGPL `ultralytics` package; the MIT reference repo or Roboflow `trackers` avoids that.

### Gaps
- Not verified in this session: MMPose/RTMPose/RTMO/RTMW/DWPose license (believed Apache-2.0), ViTPose license, YOLOv12/YOLOv13 license (likely AGPL-3.0 via Ultralytics codebase), YOLO-World (believed GPL-3.0), OWLv2, Florence-2 (believed MIT), SAM 3 (custom SAM license), Grounding DINO 1.5 Edge (API), DEIM v1, DEIMv2 exact LICENSE text, Sapiens exact license (believed non-commercial), PML 1.0 full terms.
