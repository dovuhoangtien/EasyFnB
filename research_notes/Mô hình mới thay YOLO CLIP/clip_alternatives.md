# CLIP ViT-B-32 alternatives for zero-/few-shot classification of CCTV crops on edge hardware (as of Nov 2026)

Scope note: baseline is OpenCLIP ViT-B-32 `laion2b_s34b_b79k`. The user measured it at about 40 ms per crop on a Ryzen 7 6800H CPU and a few ms on an RTX 3050 4 GB. Every number below names its source. "Vendor-reported" means the model's authors published it. Older results (before 2025) are dated.

---

## Is CLIP ViT-B-32 still a good choice, and what should replace it?

### Takeaway
No, not on accuracy. Several models released in 2025 beat ViT-B-32 laion2b by 5 to 12 pp zero-shot ImageNet (66.6%), several at similar or lower cost:
- MobileCLIP2-S0 (71.5%) and S2 (77.2%)
- SigLIP 2 B/32-256 (74.0%) and B/16-224 (78.2%)
- PE-Core-B16 (78.4%)

The best drop-in candidates for a CPU-only box are MobileCLIP2-S0/S2 (fast, but check the license) and SigLIP 2 B/32 or B/16 (Apache-2.0, multilingual). PE-Core-B16 has the best robustness numbers among base-size models (ObjectNet, ImageNet-A), but it costs roughly 3 to 4 times more image compute than B/32.

### Cited Findings
**Baseline (OpenCLIP results CSV; models from 2021–2022)**
- ViT-B-32 laion2b_s34b_b79k [Source](https://raw.githubusercontent.com/mlfoundations/open_clip/main/docs/openclip_results.csv):

  | IN-1k ZS | IN-A | IN-R | IN-Sketch | IN-v2 | ObjectNet | 38-dataset avg | Params | GFLOPs (image + text) |
  |---|---|---|---|---|---|---|---|---|
  | 66.56 | 26.27 | 76.43 | 53.66 | 58.14 | 48.83 | 56.94 | 151.28M | 14.78 |

- Other rows from the same CSV [Source](https://raw.githubusercontent.com/mlfoundations/open_clip/main/docs/openclip_results.csv):

  | Model | IN-1k ZS | IN-A | ObjectNet | 38-dataset avg | GFLOPs |
  |---|---|---|---|---|---|
  | ViT-B-32 openai | 63.32 | — | 44.31 | 52.45 | — |
  | ViT-B-32 datacomp_xl_s13b_b90k | 69.17 | — | 55.10 | 57.95 | 14.78 |
  | ViT-B-32-quickgelu metaclip_fullcc | 67.66 | — | — | 55.77 | — |
  | ViT-B-16 openai | 68.34 | — | — | 56.26 | 41.09 |
  | ViT-B-16 dfn2b | 76.24 | 48.20 | 63.19 | 60.92 | 41.09 |
  | EVA02-B-16 merged2b | 74.72 | 53.96 | 62.14 | 58.90 | 41.09 |
  | ViT-B-16-quickgelu metaclip_fullcc | 72.12 | — | — | 60.41 | — |
  | ViT-B-16-SigLIP webli (224) | 76.04 | 45.41 | 55.09 | 62.32 | 46.44 (203M params) |
  | ViT-B-16-SigLIP-256 | 76.53 | — | — | — | 57.84 |
  | ViT-L-14-quickgelu dfn2b | 81.41 | — | 73.97 | 66.87 | 175.33 (428M params) |

  The CSV has no SigLIP 2, MobileCLIP, PE-Core or TinyCLIP rows.

**SigLIP 2 (Google, released 20 Feb 2025; arXiv 2502.14786, Table 1)** [Source](https://arxiv.org/html/2502.14786v1)

| Model | IN-1k | IN-v2 | ReaL | ObjectNet | 10-shot |
|---|---|---|---|---|---|
| B/16 @224 | 78.2 | 71.4 | 84.8 | 73.6 | 72.1 |
| B/16 @256 | 79.1 | 72.5 | 85.4 | 74.5 | 73.1 |
| B/32 @256 | 74.0 | 66.9 | 81.4 | 66.1 | 66.6 |
| L/16 @256 | 82.5 | 76.8 | 87.3 | 83.0 | 78.8 |
| So/14 @224 | 83.2 | 77.7 | 87.8 | 84.6 | 79.5 |

  - The original SigLIP B/16 @224 scores 76.2 on IN-1k and 69.9 on 10-shot.
  - B/16-224 baselines in the same table:

    | Model | IN-1k | ObjectNet |
    |---|---|---|
    | OpenAI CLIP | 68.3 | 55.3 |
    | MetaCLIP | 72.4 | 60.0 |
    | EVA-CLIP | 74.7 | 62.3 |
    | DFN | 76.2 | 63.2 |

    The paper notes DFN's filter network was fine-tuned on ImageNet, COCO and Flickr.

  - Sizes: ViT-B 86M, L 303M, So400m 400M, g 1B [Source](https://arxiv.org/abs/2502.14786).
  - NaFlex is a single checkpoint that keeps the native aspect ratio. B/16 NaFlex at 256 tokens scores 78.5 vs 79.1 for the fixed-resolution model [Source](https://arxiv.org/html/2502.14786v1).
  - The 10-shot column is "10-shot classification on the validation set". The paper does not call it a linear probe.

**MobileCLIP2 (Apple; TMLR 2025, weights released 28 Aug 2025) and MobileCLIP (CVPR 2024)** [Source](https://github.com/apple/ml-mobileclip)

All figures are vendor-reported. Latencies are image + text, in ms.

| Model | IN-1k ZS | 38-dataset avg | Params (img + txt) | Latency (img + txt) |
|---|---|---|---|---|
| MobileCLIP2-S0 | 71.5 | 59.7 | 11.4M + 63.4M | 1.5 + 3.3 |
| MobileCLIP2-S2 | 77.2 | 64.1 | 35.7M + 63.4M | 3.6 + 3.3 |
| MobileCLIP2-B | 79.4 | 65.8 | 86.3M + 63.4M | 10.4 + 3.3 |
| MobileCLIP2-S3 | 80.7 | 66.8 | 125.1M + 123.6M | 8.0 + 6.6 |
| MobileCLIP2-S4 | 81.9 | 67.5 | 321.6M + 123.6M | 19.6 + 6.6 |
| MobileCLIP2-L/14 | 81.9 | 67.8 | 304.3M + 123.6M | 57.9 + 6.6 |
| MobileCLIP-S0 (2024) | 67.8 | 58.1 | 11.4M + 42.4M | 1.5 + 1.6 |
| MobileCLIP-S1 (2024) | 72.6 | 61.3 | 21.5M + 63.4M | 2.5 + 3.3 |
| MobileCLIP-S2 (2024) | 74.4 | 63.7 | — | — |
| MobileCLIP-B (2024) | 76.8 | 65.2 | — | — |
| MobileCLIP-B (LT) (2024) | 77.2 | — | — | — |

  - Abstract claims [Source](https://arxiv.org/abs/2508.20691):
    - MobileCLIP2-B is +2.2% on IN-1k over MobileCLIP-B.
    - MobileCLIP2-S4 matches SigLIP-SO400M/14 zero-shot at about half the size.
    - MobileCLIP2-S4 beats DFN ViT-L/14 at about 2.5× lower latency.
    - The original MobileCLIP family is "3-15ms latency" at 50 to 150M params.
  - MobileCLIP abstract: MobileCLIP-S2 is "2.3× faster while more accurate" than the previous best ViT-B/16 CLIP [Source](https://arxiv.org/abs/2311.17049).

**Perception Encoder PE-Core (Meta; released 17 Apr 2025; T/S added 11 Jul 2025)** [Source](https://github.com/facebookresearch/perception_models)

| Model | Resolution | IN-1k | IN-v2 | IN-A | ObjectNet |
|---|---|---|---|---|---|
| T/16 | 384 | 62.1 | 54.7 | 21.1 | 43.9 |
| S/16 | 384 | 72.7 | 65.0 | 49.5 | 60.0 |
| B/16 | 224 | 78.4 | 71.7 | 62.4 | 71.9 |
| L/14 | 336 | 83.5 | 77.9 | 89.0 | 84.7 |
| G/14 | 448 | 85.4 | 80.2 | 92.6 | 88.2 |

  - Tower sizes: B/16 vision 0.09B + text 0.31B; L/14 0.32B + 0.31B; G/14 1.88B + 0.47B [Source](https://huggingface.co/facebook/PE-Core-S16-384).
  - The repo labels these "Vision-Language Benchmarks". They are zero-shot CLIP evaluations, but the page does not say "zero-shot top-1" explicitly.

**TIPS / TIPSv2 (Google DeepMind; TIPS ICLR 2025, TIPSv2 CVPR 2026, arXiv 2604.12012)** [Source](https://github.com/google-deepmind/tips)
- Sizes (vision / text):

  | Model | Params | Versions |
  |---|---|---|
  | S/14 | 21.6M / 33.6M | v1 only |
  | B/14 | 85.7M / 109.6M | v1, v2 |
  | L/14 | 303.2M / 183.9M | v1, v2 |

- ImageNet k-NN: TIPSv2-B/14 79.8, TIPS-S/14-HR 75.1.
- The repo reports no zero-shot ImageNet accuracy, only k-NN, retrieval and dense tasks.
- TIPSv2 is the only clearly 2026 image-text encoder release found in this pass.

**TinyCLIP (Microsoft, ICCV 2023)** [Source](https://github.com/wkcn/TinyCLIP)

| Model | IN-1k | MACs | Throughput |
|---|---|---|---|
| ViT-63M/32 + Text-31M (LAION+YFCC) | 64.5 | 5.6 G | 2,909 pairs/s |
| ViT-45M/32 + Text-18M | 62.7 | — | — |
| ViT-39M/16 + Text-19M (YFCC) | 63.5 | 9.5 G | — |
| ViT-22M/32 + Text-10M | 53.7 | 1.9 G | — |

  - The README does not state the throughput hardware.

**Newer releases**
- One search found no 2026 CLIP-style encoder that clearly beats SigLIP 2 on zero-shot ImageNet [Source](https://faculty.cc.gatech.edu/~zk15/teaching/AY2026_cs8803vlm_fall/assets/L4_CLIP_to_SigLIP2.pdf). That source is a secondary course deck saying SigLIP 2 SO400m is the default VLM vision tower.

### Inferences
**Accuracy**
- Every 2025 family above beats ViT-B-32 laion2b zero-shot ImageNet:
  - MobileCLIP2-S0: +4.9 pp
  - SigLIP 2 B/32-256: +7.4 pp
  - MobileCLIP2-S2: +10.6 pp
  - SigLIP 2 B/16-224: +11.6 pp
  - PE-Core-B16: +11.8 pp
- They also beat it on robustness. ObjectNet is 48.8 for B-32 vs 71.9 for PE-Core-B16 and 73.6 for SigLIP 2 B/16 (different eval pipelines; see Gaps).
- TinyCLIP (2023) does not beat ViT-B-32 laion2b on accuracy, so it is not worth switching to.

**Compute**
- Only the image tower runs per crop, because text embeddings for the fixed prompts are computed once. Text-tower size (63M to 310M) barely matters at runtime.
- Patch-16 models at 224 (SigLIP 2 B/16, PE-Core-B16, DFN B/16, EVA02-B/16) have 196 tokens vs 49 for B/32. The OpenCLIP CSV shows 41.09 vs 14.78 total GFLOPs (image + text) for B/16 vs B/32, so image-tower compute is roughly 3–4× higher.
- On the 6800H that projects to about 120–160 ms per crop at fp32 PyTorch, unless the runtime is optimized (ONNX/OpenVINO) or the crops are batched. This is an extrapolation, not a measurement.
- SigLIP 2 B/32-256 has 64 tokens vs 49, so roughly 1.3× B/32 compute for +7.4 pp ImageNet. It is the closest compute-neutral upgrade with a permissive license.
- MobileCLIP2-S0/S2 should be the fastest per crop. Their vendor latencies are 1.5 ms and 3.6 ms vs 10.4 ms for a ViT-B/16-class image tower on the same Apple device.

**Robustness**
- PE-Core-S16 at 384 px (576 tokens) is not cheap despite its "S" size. Its compute is likely similar to a ViT-B/16 at 224.

**Recommendation for the demo**
- Do not swap without testing. A/B test on the user's own 91 CCTV table crops and 105 person val crops with:
  - MobileCLIP2-S2 (or S0) via open_clip
  - SigLIP 2 B/16-224 and B/32-256
  - optionally PE-Core-B16
- Measure CPU latency with the same harness.

### Gaps
- **Eval protocols disagree.** For SigLIP B/16-224 ObjectNet, OpenCLIP's CSV gives 55.09 but the SigLIP 2 paper gives 70.7. Compare only within one source.
- **MobileCLIP latency device.** The README does not state the device behind the latency columns. It mentions an iPhone 12 Pro Max only in a highlight. My recollection is that the MobileCLIP paper measured on an iPhone 12 Pro Max via Core ML; this was not re-verified here. No x86 CPU or RTX 3050 latency figures were found for SigLIP 2, PE-Core, MobileCLIP2 or DINOv3.
- **Missing values.** No PE-Core parameter counts were found for the T/S models. No zero-shot ImageNet numbers were found for TIPS, MetaCLIP 2 distilled models, or TinyCLIP's teacher. No standardized 38-dataset linear-probe table covering all of these models was found.

---

## For few-shot linear probes on small labeled sets with domain shift, do self-supervised features (DINOv2/DINOv3) beat CLIP-style features? Is there evidence on fine-grained state recognition?

### Takeaway
The evidence is mixed and indirect. DINOv2/v3 often win plain linear probes and dense tasks. Language supervision (CLIP-style) is reported to be clearly better on fine-grained categories. DINO also has no text tower in its small variants, so it cannot do the zero-shot "clean vs dirty" prompts the table task depends on. No published study tests "dirty vs clean" or "hand raised vs not" under stock-to-CCTV shift; the user has to test it.

### Cited Findings
- **Matched-training comparison** ("Data or Language Supervision: What Makes CLIP Better than DINO?", arXiv 2510.11835, Oct 2025). CLIP and DINO perform similarly on general and robustness benchmarks, but CLIP is clearly stronger on fine-grained tasks. Example: Stanford Cars 74.7% vs 54.1% [Source](https://arxiv.org/html/2510.11835v1). The figure comes from the search-result summary; the full paper was not fetched.
- **Counter-evidence** (DINOv2 favored):
  - Some papers report that linear classifiers on DINOv2 features beat those on CLIP features [Source](https://arxiv.org/pdf/2407.10366). That snippet came via a search summary and the datasets are unspecified.
  - An anecdotal k-NN test on a small car-generation dataset found CLIP ViT-L about 59% vs DINOv2-Giant about 41% [Source](https://reddit.sentinel-team.org/posts/1uqtamz/snapshots/2026-07-09T20%3A50%3A09.14801Z). This is informal and low quality.
- **DINOv3 (Meta, Aug 2025; arXiv 2508.10104)** [Source](https://github.com/facebookresearch/dinov3)
  - Distilled small backbones:

    | Model | Params |
    |---|---|
    | ViT-S/16 | 21M |
    | ViT-S+/16 | 29M |
    | ViT-B/16 | 86M |
    | ViT-L/16 | 300M |
    | ConvNeXt-T | 29M |
    | ConvNeXt-S | 50M |
    | ConvNeXt-B | 89M |
    | ConvNeXt-L | 198M |

  - The only text-aligned variant is dino.txt, built on ViT-L/16.
- **DINOv3 model-card benchmarks** [Source](https://huggingface.co/facebook/dinov3-vits16-pretrain-lvd1689m)

  | Model | IN-ReaL | IN-R | ObjectNet | ADE20k |
  |---|---|---|---|---|
  | ViT-S/16 | 87.0 | 60.4 | 50.9 | 47.0 |
  | ViT-S+/16 | 88.0 | 68.8 | 54.6 | 48.8 |
  | ViT-B/16 | 89.3 | 76.7 | 64.1 | 51.8 |
  | ViT-L/16 | 90.2 | 88.1 | 74.8 | — |
  | ConvNeXt-T @256 | 86.6 | 73.7 | 52.6 | — |

  - The card does not name the protocol; the paper uses frozen-feature linear evaluation.
  - The card's ConvNeXt-S row repeats ConvNeXt-T's IN-R and ObjectNet values, which may be a formatting error.
- DINOv3 ViT-L/16 recipe target: 82.0% k-NN and 83.5% linear on IN-1k [Source](https://github.com/facebookresearch/dinov3).
- TIPS/TIPSv2 sits between the two camps: image-text training plus spatial and self-distillation losses. TIPS-S/14 has a 21.6M vision tower and 75.1 ImageNet k-NN. TIPSv2-B/14 reaches 79.8 k-NN and 84.0 PASCAL segmentation [Source](https://github.com/google-deepmind/tips).
- SigLIP 2 also adds self-distillation and masked-prediction losses and reports "significant improvements on localization and dense prediction tasks" over SigLIP [Source](https://arxiv.org/abs/2502.14786).

### Inferences
- **Staff vs customer** (97% val already). DINOv3 ViT-S/16 or ConvNeXt-T (21–29M params) are plausible cheaper probe backbones. Uniforms and colors are coarse appearance cues where SSL features do well. The expected gain is small, because the task is near ceiling.
- **Table clean vs dirty.** Zero-shot text prompts beat the probe trained on stock photos, so a text-aligned model must stay in the loop. Only CLIP-family models (SigLIP 2, MobileCLIP2, PE-Core) or dino.txt (ViT-L, too large) qualify. A hybrid is possible: a DINOv3 probe trained on a few real CCTV crops, ensembled with SigLIP 2/MobileCLIP2 zero-shot.
- **Hand raise.** Pose already gates the question (wrist above shoulder), so the embedding mostly has to tell "deliberate raise" from "eating or drinking". That is a fine-grained, body-configuration task where language-supervised models are reported to do better. Keypoint geometry features may matter more than the backbone choice (untested).

### Gaps
- No paper or benchmark found on clean/dirty surface state, "holding object vs empty hand", or hand-raise recognition from CCTV with any of these models.
- No few-shot (10–300 label) DINOv3-vs-SigLIP 2 comparison under domain shift was found.
- DINOv2 small-model linear-probe numbers were not fetched.

---

## Which models are fastest at near-CLIP-B accuracy? What latency figures are published, and on what hardware?

### Takeaway
MobileCLIP2-S0 (11.4M image params, 71.5% IN-1k) and MobileCLIP2-S2 (35.7M, 77.2%) are the speed-accuracy leaders. Their vendor-reported image latencies are 1.5 ms and 3.6 ms on Apple mobile hardware. No first-party x86 CPU or RTX 3050 numbers exist for any candidate, so the user has to benchmark on the 6800H and RTX 3050.

### Cited Findings
- **MobileCLIP2 image + text latency** (vendor-reported, ms):

  | Model | Latency |
  |---|---|
  | S0 | 1.5 + 3.3 |
  | S2 | 3.6 + 3.3 |
  | S3 | 8.0 + 6.6 |
  | B | 10.4 + 3.3 |
  | S4 | 19.6 + 6.6 |
  | L/14 | 57.9 + 6.6 |
  | MobileCLIP-S1 (2024) | 2.5 + 3.3 |

  The README does not state the device; it mentions an iPhone 12 Pro Max only in a highlight [Source](https://github.com/apple/ml-mobileclip).
- **Community ONNX export of MobileCLIP2-S0** (not vendor) [Source](https://huggingface.co/felixhrdyn/mobileclip2-s0-onnx):
  - Reports 112 ms vision and 10 ms text on an unnamed CPU, plus "25.0 ms per frame" frame embedding. The two figures are internally inconsistent and the hardware is unspecified.
  - Recommends keeping the FastViT vision tower in FP32, because dynamic INT8 adds overhead on depthwise convs. The hybrid package is 105 MB.
- **TinyCLIP throughput** (no hardware stated) [Source](https://github.com/wkcn/TinyCLIP):

  | Model | Throughput | IN-1k |
  |---|---|---|
  | ViT-22M/32 | 5,504 pairs/s | 53.7 |
  | ViT-63M/32 | 2,909 pairs/s | 64.5 |

- **OpenCLIP GFLOPs** (image + text) as a hardware-independent proxy [Source](https://raw.githubusercontent.com/mlfoundations/open_clip/main/docs/openclip_results.csv):

  | Model | GFLOPs |
  |---|---|
  | ViT-B-32 | 14.78 |
  | ViT-B-16 | 41.09 |
  | SigLIP B/16-224 | 46.44 |
  | SigLIP B/16-256 | 57.84 |

- **PE-Core small models**: S/16 reaches 72.7% and T/16 62.1%, but both at 384 px [Source](https://github.com/facebookresearch/perception_models).
- **User baseline**: CLIP ViT-B-32 at about 40 ms per crop on a Ryzen 7 6800H CPU and a few ms on an RTX 3050 (from the assignment brief, not a published figure).

### Inferences
- **Ranking at near-CLIP-B or better accuracy** (projected, not measured, ordered by expected CPU cost per crop):
  1. MobileCLIP2-S0: 71.5%, already above B-32's 66.6%
  2. MobileCLIP2-S2: 77.2%
  3. SigLIP 2 B/32-256: 74.0%
  4. PE-Core-S16-384: 72.7%
  5. SigLIP 2 B/16-224 / PE-Core-B16 / MobileCLIP2-B: 78–79%
- **On the RTX 3050**, all of these base-size models should run in a few ms per crop at fp16, so the GPU path is not the constraint. This is an inference from B-32 running in a few ms.
- **FastViT/MCi caveat**: MobileCLIP's FastViT/MCi hybrid backbones are optimized for Apple's Neural Engine and Core ML. Their x86 CPU advantage over a plain ViT-B/32 may be smaller than the iPhone ratio suggests. The community ONNX card hints at this: depthwise-conv INT8 overhead and 112 ms vision.

### Gaps
- No published Ryzen, Intel or RTX 3050 latency for MobileCLIP2, SigLIP 2, PE-Core, DINOv3 or TIPS.
- No first-party OpenVINO benchmarks for any of these models.

---

## Do any of them handle Vietnamese prompts well (SigLIP 2 multilingual, MetaCLIP 2)?

### Takeaway
SigLIP 2 (Apache-2.0) and MetaCLIP 2 (non-commercial CC-BY-NC) are the multilingual options. SigLIP 2 roughly doubles multilingual retrieval over SigLIP at B/16. For a fixed set of developer-written class prompts, English prompts work fine and avoid any multilingual penalty; Vietnamese is mainly useful if staff will type free-text queries.

### Cited Findings
- **SigLIP 2 training data**: WebLI, about 10B images and 12B alt-texts in 109 languages, 90% English and 10% non-English pages. It uses the multilingual Gemma tokenizer (256k vocab) with text length 64 [Source](https://arxiv.org/html/2502.14786v1).
- **SigLIP 2 vs SigLIP on XM3600 retrieval** (recall@1) [Source](https://arxiv.org/html/2502.14786v1):

  | Model | T→I | I→T |
  |---|---|---|
  | SigLIP 2 B/16-224 | 40.3 | 50.7 |
  | SigLIP B/16-224 | 22.4 | 29.3 |
  | SigLIP 2 B/32-256 | 38.3 | 49.0 |

- **MetaCLIP 2 (Jul 2025; NeurIPS 2025 spotlight)**:
  - ViT-H/14 beats its English-only counterpart by 0.8% and mSigLIP by 0.7% on zero-shot ImageNet. It reports CVQA 57.4%, Babel-ImageNet 50.2% and XM3600 I→T 64.3% [Source](https://arxiv.org/abs/2507.22062v3).
  - Distilled models (released 21 Nov 2025) use the XLM-V tokenizer. CVQA-LOCAL zero-shot scores [Source](https://github.com/facebookresearch/MetaCLIP):

    | Model | CVQA-LOCAL ZS |
    |---|---|
    | ViT-S-16 | 46.9 |
    | ViT-M-16 | 49.3 |
    | ViT-B-32 | 49.1 |
    | ViT-B-16 | 50.9 |
    | ViT-L-14 | 56.5 |

  - License: "The majority of Meta CLIP is licensed under CC-BY-NC" [Source](https://github.com/facebookresearch/MetaCLIP).
- **SigLIP 2 B/16-224 model card**: license Apache-2.0. It loads via `pipeline(task="zero-shot-image-classification")` or `AutoModel`/`AutoProcessor`. The card gives no multilingual usage notes [Source](https://huggingface.co/google/siglip2-base-patch16-224).

### Inferences
- Use SigLIP 2 if Vietnamese text matters. It is the only permissively licensed multilingual option among those checked; MetaCLIP 2's CC-BY-NC rules it out for a commercial restaurant product.
- MobileCLIP/MobileCLIP2, PE-Core, OpenAI/OpenCLIP CLIP and TinyCLIP are English-centric. That is fine because the class prompts ("a clean empty restaurant table", "a table with dirty dishes and leftover food") are written by the developers. Vietnamese can be handled at the UI layer.
- Prompt ensembling (several English paraphrases per class, averaged) is likely a better use of effort than Vietnamese prompts for the clean/dirty task.

### Gaps
- I did not verify whether XM3600 includes Vietnamese, or find a Vietnamese-specific score for SigLIP 2 or MetaCLIP 2. My understanding is that XM3600 covers 36 languages including Vietnamese, but this was not checked in this session.
- No evidence was found on PE-Core's multilingual ability.

---

## Which parameter-efficient adaptation methods (CoOp/CoCoOp, Tip-Adapter, CLIP-Adapter, WiSE-FT, LP + zero-shot ensembling) help most with 50–300 labels, and by how much?

### Takeaway
With few labels and a train/deploy domain shift (stock video to CCTV), keep the zero-shot classifier in the model:
- zero-shot-initialized linear probe (ZS-LP)
- CLAP, a class-adaptive constrained linear probe (CVPR 2024)
- WiSE-FT-style interpolation between zero-shot and fine-tuned weights

A randomly initialized logistic probe is the worst option under shift. Its loss to zero-shot matches the user's observation that the probe trained on stock photos did worse than zero-shot on CCTV.

### Cited Findings
- **CLAP benchmark, 11-dataset average, ResNet-50 CLIP, fixed hyperparameters (no per-task validation tuning)** [Source](https://arxiv.org/html/2312.12730):

  | Method | 1-shot | 4-shot | 16-shot |
  |---|---|---|---|
  | Zero-shot | 57.71 | 57.71 | 57.71 |
  | Random-init LP | 30.42 | 51.69 | 67.54 |
  | CoOp | 59.56 | 66.47 | 73.33 |
  | CLIP-Adapter | 58.43 | 66.18 | 73.35 |
  | Tip-Adapter | 58.86 | 61.49 | 64.61 |
  | Tip-Adapter-F | 60.29 | 65.32 | 71.40 |
  | TaskRes(e) | 61.44 | 68.35 | 74.42 |
  | ZS-LP | 61.28 | 67.98 | 74.37 |
  | CLAP | 62.79 | 69.13 | 74.57 |

  - CoOp numbers are taken from prior literature, not re-run.
  - The gap between methods shrinks at 16 shots.
- **Domain generalization, ImageNet source to average of V2/Sketch/A/R, ViT-B/16** [Source](https://arxiv.org/html/2312.12730):

  | Method | Target average |
  |---|---|
  | Zero-shot | 57.17 |
  | Random-init LP | 40.41 |
  | CLIP-Adapter | 50.72 |
  | Tip-Adapter | 41.55 |
  | Tip-Adapter-F | 35.58 |
  | TaskRes(e) | 55.35 |
  | ZS-LP | 53.65 |
  | CLAP | 60.04 |

  - CLAP is the only method that consistently improves on zero-shot under shift on both backbones.
  - With ResNet-50, random-init LP falls to 24.61 vs zero-shot 40.61.
- The paper says CLIP-Adapter and Tip-Adapter lose substantial accuracy without test- or validation-tuned hyperparameters. Earlier efficient-transfer methods often "underperform standard zero-shot predictions" under distributional drift [Source](https://arxiv.org/abs/2312.12730).
- **WiSE-FT** (weight-space ensembling of zero-shot and fine-tuned models; CVPR 2022, older) [Source](https://arxiv.org/abs/2109.01903):
  - +4 to 6 pp accuracy under distribution shift over prior work, with ImageNet accuracy up 1.6 pp.
  - Robustness gains of 2 to 23 pp on six further shifts.
  - +0.8 to 3.3 pp over standard fine-tuning on seven transfer datasets.

### Inferences
- **What 50–300 labels means here.** These are binary tasks, so 50–300 labels is about 25–150 shots per class. That is beyond the 16-shot regime where the CLAP/ZS-LP/TaskRes/CoOp numbers converge, so ranking among methods matters less than handling the stock-to-CCTV shift.
- **Table clean/dirty**:
  - Initialize the logistic head from the zero-shot text embeddings (ZS-LP), or train the probe and then interpolate. For example, logits = α·zero-shot + (1−α)·probe, or the WiSE-style weights θ = (1−α)·θ_zs + α·θ_probe.
  - Tune α on a handful of real CCTV crops; even 20–50 labeled CCTV crops are more valuable than more stock crops.
  - Expected gain: a few pp over pure zero-shot, going by the +2.9 pp target-domain gain for CLAP with ViT-B/16. Not guaranteed.
- **Avoid Tip-Adapter(-F) and CLIP-Adapter for the demo.** They are hyperparameter-sensitive and degrade under shift: Tip-Adapter-F reaches 35.58 vs 57.17 zero-shot target accuracy with ViT-B/16.
- **CoOp/CoCoOp prompt learning** needs backprop through the text encoder. It is fine on the RTX 3050 but adds training-pipeline complexity for little expected gain at 25–150 shots per class.
- **Staff/customer and hand-raise probes** have no zero-shot prior. Keep the logistic probe and add a few real CCTV crops to training; this targets the shift itself.

### Gaps
- No ImageNet-only few-shot numbers for these methods with SigLIP 2, MobileCLIP2 or PE-Core backbones were found. All adaptation numbers are for OpenAI CLIP RN50/ViT-B/16, and only the 11-dataset averages were fetched.
- CoCoOp was not in the fetched CLAP table.
- LP++ (CVPR 2024) was not fetched.

---

## What are each model's weight licenses, how are they loaded (open_clip, timm, transformers), and is there ONNX/OpenVINO export support?

### Takeaway
For a commercial product, the safe licenses are:
- SigLIP 2: Apache-2.0
- PE-Core: Apache-2.0
- TIPS: Apache-2.0 code, CC-BY-4.0 other materials

The others need care:
- DINOv3 uses a custom Meta license that allows use but bans military and other listed end uses, and the weights are gated.
- MobileCLIP2 weights use the "Apple ML Research Model TOU". Its terms were not read; verify commercial permissibility before shipping.
- MetaCLIP 2 is mostly CC-BY-NC, so non-commercial.

### Cited Findings
**Licenses**
- SigLIP 2 B/16-224: Apache-2.0. Loads via transformers `AutoModel`/`AutoProcessor`, `get_image_features`, or the zero-shot pipeline [Source](https://huggingface.co/google/siglip2-base-patch16-224).
- PE-Core:
  - License badge Apache-2.0 [Source](https://github.com/facebookresearch/perception_models); HF card license apache-2.0 [Source](https://huggingface.co/facebook/PE-Core-S16-384).
  - Loads with `pe.CLIP.from_config("PE-Core-B16-224", pretrained=True)` from the perception_models repo, or vision-only with `pe.VisionTransformer.from_config`.
  - Integrated into timm on 28 May 2025 [Source](https://github.com/facebookresearch/perception_models).
  - HF IDs: `facebook/PE-Core-{T16-384,S16-384,B16-224,L14-336,G14-448}`.
- MobileCLIP/MobileCLIP2 [Source](https://github.com/apple/ml-mobileclip):
  - Code MIT; models "Apple ML Research Model TOU"; DataCompDR/DFNDR data CC-BY-NC-ND.
  - open_clip tags: `datacompdr` (MobileCLIP-S1/S2/B), `datacompdr_lt` (B-LT), `dfndr2b` (MobileCLIP2-S0/S2/B/S3/S4/L-14). MobileCLIP-S0/S3/S4/L-14 v1 need the `mobileclip` package.
  - HF repos: `apple/MobileCLIP2-*`.
  - Some MobileCLIP2 variants need image mean (0,0,0) and std (1,1,1) overrides.
  - Call `reparameterize_model` before inference or export.
- DINOv3 License [Source](https://github.com/facebookresearch/dinov3/blob/main/LICENSE.md):
  - Custom Meta agreement granting a non-exclusive, worldwide, royalty-free limited license to use, reproduce, distribute and modify. It does not explicitly exclude commercial use.
  - Bans ITAR-controlled, military/warfare, nuclear, espionage and weapons uses. Requires trade-control compliance, redistribution under the same agreement, and acknowledgment in published research.
- DINOv3 access and loading:
  - HF weights are gated (users must agree to share their information) [Source](https://huggingface.co/facebook/dinov3-vits16-pretrain-lvd1689m).
  - Loading: torch.hub, transformers ≥ 4.56.0 (`AutoModel`), timm ≥ 1.0.20 [Source](https://github.com/facebookresearch/dinov3).
- MetaCLIP 2:
  - "majority … licensed under CC-BY-NC" [Source](https://github.com/facebookresearch/MetaCLIP).
  - Loading: `create_model_and_transforms('ViT-B-32-worldwide@WorldWideCLIP', pretrained='metaclip2_worldwide')` with tokenizer `facebook/xlm-v-base`. Added to open_clip and HF on 25 Aug 2025.
- TIPS/TIPSv2: software Apache-2.0, other materials CC-BY-4.0. PyTorch and JAX checkpoints; TIPSv2 in the HF collection `google/tipsv2` [Source](https://github.com/google-deepmind/tips).
- TinyCLIP: open_clip configs plus checkpoints in GitHub releases and the HF TinyCLIP collection. The README does not name the license [Source](https://github.com/wkcn/TinyCLIP).

**ONNX/OpenVINO**
- The only concrete evidence is the community MobileCLIP2-S0 ONNX/INT8 export [Source](https://huggingface.co/felixhrdyn/mobileclip2-s0-onnx).
- Apple's README says nothing about ONNX or Core ML export beyond `reparameterize_model` [Source](https://github.com/apple/ml-mobileclip).

### Inferences
- Plain ViT encoders (SigLIP 2, PE-Core, DINOv3 ViT-S/B, OpenCLIP ViTs) export to ONNX with `torch.onnx.export` or HF Optimum, and run in OpenVINO, in the usual way for ViTs. This is general knowledge, not verified for each model here.
- MobileCLIP2's FastViT/MCi blocks need reparameterization first, and INT8 quantization may not speed them up on x86.
- Lowest-friction path from the current code: stay in open_clip and swap the model name to MobileCLIP2-S2 or SigLIP 2. This assumes open_clip ships `ViT-B-16-SigLIP2`/`ViT-B-32-SigLIP2-256` with pretrained='webli', which I believe it does but did not verify here; otherwise use transformers.

### Gaps
- **Apple's terms were not read.** The ML Research Model TOU may restrict use to research; check it before using MobileCLIP2 commercially.
- **Unverified licenses**: the OpenCLIP laion2b weights (commonly MIT), EVA-CLIP, DFN (Apple) and TinyCLIP.
- **Unverified names**: exact open_clip names for SigLIP 2 and timm names for PE-Core and SigLIP 2.
- **No first-party ONNX/OpenVINO guides** were found for SigLIP 2, PE-Core or DINOv3.
