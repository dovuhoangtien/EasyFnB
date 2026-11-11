# Cross-industry analogues: "Is this fixed spot empty, occupied, or holding leftover items?" (seat/desk, parking, retail shelf, abandoned object, food waste, room cleaning, foundation-model region state)

Scope note: research done 5 Nov 2026 for Easy FnB (GDG DevFest MienTrung, demo 14 Nov 2026). Sources from 2023–2026 are preferred. Older sources carry their year. "Vendor claim" means the company reports the number itself. "Independent" means a peer-reviewed paper or a third party. Search-engine snippets that could not be opened are marked as such.

---

## Q1. Best current methods (2023–2026) for per-region state classification from a fixed camera, and what works under occlusion by people

### Takeaway
Parking-space occupancy is the most mature analogue. The pattern there is one manually drawn polygon per spot, plus either a per-ROI classifier or one backbone pass over the whole image with RoI pooling. These reach about 98% on unseen lots, and self-supervised pretraining recently pushed cross-lot accuracy to about 97–98% without target-lot labels. For items left in a region, the strongest transferable ideas come from two fields:
- **Abandoned-object detection:** a long-term plus short-term background model, with an explicit "occluded" state that freezes timers.
- **Few-shot industrial anomaly detection:** AnomalyDINO, which does nearest-neighbour comparison of patch features against reference images of the "normal" (clean) state.

Retail out-of-stock work suggests that detecting the target state directly works better than enumerating objects and inferring the state. I found no peer-reviewed paper on restaurant "dirty table" detection itself. The field is GitHub prototypes, vendor pages and patents.

### Cited Findings

**Parking-space occupancy (closest mature analogue)**
- ACPDS (2021) has 293 images and 11,236 parking-space views, 48% of them occupied. Each image comes from a unique viewpoint, and train/val/test are split by parking lot, so the test lots are unseen. Images were taken with a GoPro mounted about 12 m high, like a lamppost. — [Marek, ACPDS paper arXiv 2107.12207](https://arxiv.org/html/2107.12207)
- ACPDS baselines. Both detect occupancy on unseen lots at about 98%:
  - **"R-CNN" style:** crop a 128×128 patch per space and classify it with ResNet-50. Test accuracy 97.97% ± 0.07.
  - **Faster R-CNN FPN:** one ResNet-50+FPN pass over the whole image, then 7×7 RoI pooling per space. Test accuracy 98.51% ± 0.10.

  — [arXiv 2107.12207](https://arxiv.org/html/2107.12207)
- ACPDS, occlusion and context:
  - The model tolerates moderate occlusion but fails under heavy occlusion: a large vehicle across spaces, neighbouring cars, or trees.
  - Per-patch crops "never exchange information", which makes occlusion reasoning hard. The whole-image model lets information flow between spaces.
  - **Square pooling that includes surrounding pixels beat tight quadrilateral pooling in every configuration.**

  — [arXiv 2107.12207](https://arxiv.org/html/2107.12207)
- ACPDS, cost: per-crop inference time grows linearly with the number of spaces. The whole-image FPN model has nearly constant time because the backbone dominates. The authors still prefer per-crop for deployment because it handles different resolutions and camera setups more flexibly. — [arXiv 2107.12207](https://arxiv.org/html/2107.12207)
- Self-supervised parking-spot occupancy (IEEE SMC 2026, arXiv June 2026):
  - Uses SimCLR with ResNet-50, pretrained on unlabeled generic data and then on unlabeled target data, then fine-tuned with generic parking labels only.
  - Leave-one-dataset-out average accuracy is 97.2% on PKLot / CNRPark-EXT / PLds.
  - Adding a "Specialized Model" trained on unlabeled images from the **first N days of deployment** raises this to 97.8%. Code and models are public.

  — [Kujavski, Laroca, de Almeida, arXiv 2606.20886](https://arxiv.org/abs/2606.20886)
- An ensemble of convolutional autoencoders, used as frozen feature extractors with few labelled target samples, reports 93–96% accuracy "in data-constrained scenarios" across PKLot and CNRPark. — [arXiv 2609.03258 (Sept 2026)](https://arxiv.org/abs/2609.03258)
- A search snippet states that "a global model trained on PKLot and CNRPark-EXT generalizes to unseen parking lots with an average accuracy of 92.8%". I could not confirm which paper this sentence comes from. It appeared in the same result set as [arXiv 2609.03258](https://arxiv.org/pdf/2609.03258).
- Ultralytics' off-the-shelf "Parking Management" solution works like this:
  - Users draw polygons in a GUI (`ParkingPtsSelection`), saved as `bounding_boxes.json`.
  - Occupancy is decided by whether a detected vehicle's box centre falls inside the polygon. This rule comes from an Ultralytics staff comment, not the main docs.
  - No temporal smoothing or debouncing parameter is documented.

  — [Ultralytics docs](https://docs.ultralytics.com/guides/parking-management/)

**Seat / desk occupancy and "seat hogging"**
- A 2023 library-seat paper defines the hogging problem: "a person puts personal belongings on the seat to indicate that the seat is occupied, but the owner is not on the seat". It proposes a "serial dual-channel" pipeline: a Faster R-CNN detector plus a transfer-learning classifier, trained on mixed Unreal Engine 5 synthetic images and real images. The abstract gives **no accuracy numbers** and no occlusion or temporal method. — [Yang et al., arXiv 2306.16080](https://arxiv.org/pdf/2306.16080) ([abstract page](https://arxiv.org/abs/2306.16080))
- A granted US patent describes the same decision order as Easy FnB needs. The camera first checks for a person in each seat area. If there is none, it checks for belongings in or around the area and marks the seat occupied if it finds any; otherwise it marks the seat vacant. — [US 12,380,725 "Seating position management system"](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12380725) (from a search snippet; I did not read the full patent text)
- Open-source camera prototypes:
  - [asumansaree/Library-Seat-Occupancy-Detection](https://github.com/asumansaree/Library-Seat-Occupancy-Detection) uses YOLOv7 to time how long a seat holds belongings with no person present. No accuracy is reported.
  - [RexxarCHL/library-seat-detection](https://github.com/RexxarCHL/library-seat-detection) reuses existing surveillance cameras.
  - [kennyvoo/SmartLib](https://github.com/kennyvoo/SmartLib-Cz3002-) alerts librarians to hogged seats.
- Sensor (non-camera) baselines, older:
  - A 2015-era capacitance+IR study reported it "can clearly distinguish between human occupancy and seat hogging". — [ResearchGate: Real-time Detection of Seat Occupancy & Hogging](https://www.researchgate.net/publication/301464193_Real-time_Detection_Of_Seat_Occupancy_Hogging)
  - An 8-week, 36-seat deployment reported 91.2% accuracy. — [ResearchGate: Small Scale Deployment of Seat Occupancy Detectors](https://www.researchgate.net/publication/304533277_Small_Scale_Deployment_of_Seat_Occupancy_Detectors)
  - Both figures come from search snippets.

**Restaurant table state (direct analogue, mostly non-academic)**
- [TableWatch (GitHub)](https://github.com/gpradeep7898/Table-Watch-):
  - Pipeline: YOLOX-Nano person detection, then a ByteTrack-style tracker, then polygon zones per table. It supports per-camera anchor choice (feet or body centre).
  - A person standing in an overlap of two zones is "ambiguous" and counts for neither table. Camera-offline time is excluded from occupancy stats.
  - **"The camera alone never claims that a table was served or cleaned"**: staff confirm cleaning with one tap.
  - No restaurant footage has been used, so table-state accuracy on real CCTV is unverified.
- Other GitHub student projects detect seated people in table polygons with YOLO and use a debounced state machine to avoid flicker. — [sanaulislamzihad/Restaurant-Table-Occupancy-Detection](https://github.com/sanaulislamzihad/Restaurant-Table-Occupancy-Detection), [sahidirfan884/RestoMan-Ai](https://github.com/sahidirfan884/RestoMan-Ai)
- A USPTO patent on "active/inactive state detection" for dining tables mentions reminding service staff to clean the table. — [US 11,070,771](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11070771)

**Abandoned / left-behind object detection (items left on a region)**
- Zhou & Xu (Sensors, Oct 2024) is an adaptive **dual-background** method:
  - Long-term and short-term Gaussian mixture models with different learning rates. The rates adapt to foreground ratio and to a frame-entropy lighting-change term.
  - An improved pixel finite-state machine (PFSM) gives each pixel one of: static background, **occluded**, static foreground, or moving foreground.
  - Two counters run: time the object has stayed still, and time it has been occluded. Thresholds decide when to flag "abandoned" and when to absorb an occluder into the background.
  - A small "SAO-YOLO" detector (1.7M params, 18.2 GFLOPs) then filters candidates by class.

  — [Sensors 24(20):6572, PMC11510867](https://pmc.ncbi.nlm.nih.gov/articles/PMC11510867/)
- In the same paper, **PFSM alone (background modelling without a class filter) reached only 58.3% precision on PETS2006 and 43% on AVSS2007**. It falsely flags stationary pedestrians. With the detector filter, average precision is 91.1% at 100% recall across ABODA / PETS2006 / AVSS2007. — [PMC11510867](https://pmc.ncbi.nlm.nih.gov/articles/PMC11510867/)
- Older lineage:
  - Porikli's dual foregrounds, long-term and short-term backgrounds (2007/2008). — [ResearchGate](https://www.researchgate.net/publication/26512796_Robust_Abandoned_Object_Detection_Using_Dual_Foregrounds)
  - Dual background plus a Mask R-CNN classifier. — [ResearchGate](https://www.researchgate.net/publication/340960768_Detection_of_Abandoned_and_Stolen_Objects_Based_on_Dual_Background_Model_and_Mask_R-CNN)
  - Two-stage "find static region, then classify" for abandoned luggage (2018). — [arXiv 1803.01160](https://arxiv.org/pdf/1803.01160)

**Reference-image change detection and few-shot anomaly detection (compare "now" against "clean table" snapshot)**
- AnomalyDINO (WACV 2025) is training-free:
  - It stores DINOv2 patch features from one or a few "normal" reference images in a memory bank.
  - Each test patch is scored by cosine distance to its nearest normal patch, and the image score is **the mean of the top 1% patch distances**.
  - It optionally uses DINOv2's zero-shot masking to drop background, and reference images can be augmented.
  - One-shot MVTec-AD AUROC is 96.6% (prior best 93.1%). Code is at github.com/dammsi/AnomalyDINO.

  — [arXiv 2405.14529](https://arxiv.org/pdf/2405.14529); [WACV 2025 open access](https://openaccess.thecvf.com/content/WACV2025/html/Damm_AnomalyDINO_Boosting_Patch-Based_Few-Shot_Anomaly_Detection_with_DINOv2_WACV_2025_paper.html)
- "The Change You Want to See" (CYWS, WACV 2023):
  - A co-attention model that outputs **bounding boxes of object-level changes between two images**, designed to tolerate viewpoint and lighting differences.
  - Trained on change pairs synthesised from existing segmentation datasets, with zero-shot generalisation reported.
  - CYWS-3D (ICCV Workshops 2023) uses "register and difference" on frozen self-supervised embeddings, is class-agnostic, and is trained on synthetic data. Code is at github.com/ragavsachdeva/CYWS-3D.

  — [CVF WACV 2023](https://openaccess.thecvf.com/content/WACV2023/html/Sachdeva_The_Change_You_Want_To_See_WACV_2023_paper.html); [CYWS-3D summary](https://deepai.org/publication/the-change-you-want-to-see-now-in-3d)
- Zero-shot scene change detection, 2024–2025:
  - ZSSCD (AAAI 2025) is training-free and uses a tracking model (DEVA + SAM). Code is at [github.com/kyusik-cho/ZSSCD](https://github.com/kyusik-cho/ZSSCD).
  - GeSCF (CVPR 2025) is a SAM-based zero-shot method with a new generalisable benchmark (GeSCD). — [CVPR 2025 paper](https://openaccess.thecvf.com/content/CVPR2025/papers/Kim_Towards_Generalizable_Scene_Change_Detection_CVPR_2025_paper.pdf) (PDF returned 403, so this comes from a search snippet)
  - ZeroSCD (arXiv Sept 2024) combines place recognition with semantic segmentation. — [arXiv 2409.15255](https://arxiv.org/abs/2409.15255)

  — [AAAI 2025](https://ojs.aaai.org/index.php/AAAI/article/view/32253)

**Retail shelf out-of-stock (OOS)**
- Šikić et al. (Sensors 2024): "all product detection-based methods performed significantly worse than direct detection-based methods, achieving 20% to 25% lower AP on the normal OOS class". In other words, **directly detecting the "gap" state beat detecting all products and inferring gaps.** — [Sensors 24(2):693](https://www.mdpi.com/1424-8220/24/2/693)
- ShelfChange3D (arXiv, Oct 2026) does object-level change detection from paired shelf observations: mAP 93.0 / 81.7 / 48.3 at IoU 0.25 / 0.5 / 0.7. It notes that existing OOS methods "mainly operate in image space". — [arXiv 2610.01283](https://arxiv.org/html/2610.01283v1)
- Earlier (~2022) superpixel-graph gap segmentation reached ~70–85% mIoU. — [Pattern Recognition, ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S003132032200108X)
- Focal Systems' patent describes periodically captured on-shelf images for OOS detection. — [US10949799B2](https://patents.google.com/patent/US10949799)

**Open-vocabulary detection for "items on table"**
- YOLOE (ICCV 2025) supports three prompt modes: text, visual (including **cross-image visual prompts**, i.e. a reference crop), and prompt-free. — [THU-MIG/yoloe](https://github.com/THU-MIG/yoloe); [arXiv 2503.07465](https://arxiv.org/pdf/2503.07465)
  - Fixed AP on LVIS minival, text/visual prompts: S 27.9/26.2, M 32.6/31.0, L 35.9/34.2. Prompt-free: S 21.0.
  - YOLOE-v8-S beats YOLO-Worldv2-S by 3.5 AP with 1.4× faster inference.
  - The Ultralytics docs say the prompt-free built-in vocabulary has 4,585 names. — [Ultralytics YOLOE docs](https://docs.ultralytics.com/models/yoloe)
- A 2024 study finds open-vocabulary detectors (including YOLO-World) face robustness problems under distribution shift. — [arXiv 2405.14874](https://arxiv.org/html/2405.14874v3)

**Foundation-model embeddings for few-shot region state**
- I found **no paper applying CLIP / SigLIP / DINO zero-shot or few-shot to parking-space or seat occupancy**. The search returned only general CLIP few-shot adaptation work. Examples: transductive zero-/few-shot CLIP (CVPR 2024) and a 2025 critique of 13 frozen-CLIP adapter methods in the inductive setting. — [CVPR 2024](https://openaccess.thecvf.com/content/CVPR2024/papers/Martin_Transductive_Zero-Shot_and_Few-Shot_CLIP_CVPR_2024_paper.pdf); [arXiv 2507.20834](https://arxiv.org/pdf/2507.20834)
- AnomalyDINO's authors chose DINOv2 for "strong patch-level features and masking ability". — [arXiv 2405.14529](https://arxiv.org/pdf/2405.14529)

**VLMs as the per-region judge**
- I found no paper evaluating GPT-4V or Gemini on parking or seat occupancy. One preprint reports zero-shot Gemini Flash 2.5 at 52.3% accuracy on "diverse product categories" detection versus supervised YOLO. It is a non-peer-reviewed preprint, and some of its GPT-4V figures are "estimated". — [arXiv 2510.11302](https://arxiv.org/html/2510.11302v1)

### Inferences
- **Per-ROI classification is the right abstraction**, as parking shows. Two ACPDS details transfer directly to Easy FnB's table polygons:
  - Use a context-padded square crop instead of the tight polygon.
  - Prefer one backbone pass over the full frame with RoI pooling of patch tokens per table, which has roughly constant cost no matter how many tables there are.
- **The "leftover items" sub-problem is closer to abandoned-object detection and few-shot anomaly detection than to object detection.** Restaurant-owned items (condiment caddy, napkin holder, menu stand, chopstick tube) are part of the "normal" scene. A per-table memory bank of clean-table patch features (AnomalyDINO-style) treats them as normal automatically. A COCO detector cannot know they are not leftovers.
- **Retail evidence supports classifying the state directly** ("needs clearing" vs "clean") rather than counting cups and bowls. It also suggests using item detections only as secondary evidence.
- **Under occlusion, the field's answer is mostly "don't judge"**, not "judge better". The PFSM occluded state freezes timers, on-street parking marks frames unreliable (see Q2), and ACPDS reports failure under heavy occlusion. For Easy FnB this means masking person pixels and requiring a minimum visible fraction of the table before updating clean/dirty.
- Background-subtraction-only change detection would be weak in a busy restaurant: precision was 43–58% even on surveillance benchmarks (PFSM alone). Use it, if at all, only as a cheap "something changed since the clean snapshot" trigger combined with an embedding check.

### Gaps
- No peer-reviewed paper or public dataset for restaurant "dirty/uncleared table" classification from CCTV.
- No camera-based seat-hogging study with reported accuracy for the "belongings, no person" class.
- No published evaluation of CLIP/SigLIP/PE-Core/DINOv3 few-shot classifiers on per-ROI occupancy (parking, seat or table).
- No found numbers on how SAM-based zero-shot change detectors (GeSCF, ZSSCD, AnyChange) perform indoors on tabletop clutter, or on their runtime on small GPUs.
- Train and bus seat occupancy from onboard cameras was not covered: there were no search results in my budget.

---

## Q2. How do these fields stabilise the decision over time (hysteresis, HMM, voting, "only judge when unoccluded", reference snapshot)?

### Takeaway
Across parking, abandoned-object and restaurant prototypes, the stabilisers are:
- Temporal filters such as median, trimmed mean or HMM over per-frame scores.
- Marking occluded frames as unreliable and freezing timers rather than voting on them.
- Requiring minimum dwell or track durations before a state change.
- A causal order between events: vacancy, then a cleaning timer, then cleared only with confirmation.

None of the sources uses a plain 1-second majority vote without occlusion gating, which is Easy FnB's current design and the likely cause of its flicker.

### Cited Findings
- An on-street parking patent applies **temporal filtering across frames** to discard transient outliers such as occlusion by passing traffic and camera shake. It lists median filtering, trim-mean, approximate median, MLE and **HMM estimation** as options. — [US20160093214A1 (Google Patents)](https://patents.google.com/patent/US20160093214); [USPTO PDF 10325165](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10325165)
- A video-based on-street occupancy system treats **a foreground blob partially inside and partially outside the parking region as occlusion and marks those frames as unreliable** for occupancy estimation. — [ResearchGate: Video-based real-time on-street parking occupancy detection system](https://www.researchgate.net/publication/273872719_Video-based_real-time_on-street_parking_occupancy_detection_system) (from a search snippet)
- A double-parking patent uses double frame-differencing to detect motion and discard regions occluded by moving vehicles. — [US 11,244,171](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11244171)
- An edge-AI parking system (2020) changes a slot's state only from **object tracks**. A track starting inside and ending outside means vacant; the reverse means occupied. There is a minimum track duration, and tracking removes background-subtraction noise. — [arXiv 2001.00269](https://arxiv.org/pdf/2001.00269)
- A patent covers parking-occupancy determination "robust against abrupt camera field of view changes". — [US 9,716,837](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/9716837) (title only)
- In abandoned-object detection, the PFSM keeps an **"occluded" pixel state with its own counter**. It is separate from the "static for N frames" counter, so occlusion pauses rather than resets the decision. A threshold controls when a long-standing occluder is absorbed into the background. — [Sensors 2024, PMC11510867](https://pmc.ncbi.nlm.nih.gov/articles/PMC11510867/)
- On the restaurant side:
  - TableWatch uses "temporal evidence", timers and escalation, treats ambiguous zone overlaps as neither table, and requires **staff one-tap confirmation for "cleaned"**. — [TableWatch](https://github.com/gpradeep7898/Table-Watch-)
  - FlowLinks starts a clearing timer when guests leave and alerts if the table is not cleared within the target time. It claims alerts "within 60 seconds of vacancy" (vendor claim). — [FlowLinks](https://www.flowlinks.ai/restaurants-cafes/table-turnover)
- Seat-hogging logic is causally ordered: check for a person first, then belongings only if no person is present. — [US 12,380,725](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12380725)
- Self-supervised parking work adapts to each deployment by training a "Specialized Model" on unlabeled images from the first N days. This is a site-calibration step, not temporal smoothing, but it improved the cross-lot average from 97.2% to 97.8%. — [arXiv 2606.20886](https://arxiv.org/abs/2606.20886)

### Inferences
These are concrete stabiliser designs suggested by the analogues.
1. **Occlusion gate.** For each table and frame, compute the visible fraction, i.e. the polygon area not covered by person boxes or masks from YOLO26-pose. If it is below about 60–70%, emit "no observation" instead of a clean/dirty vote. Alternatively, score only the visible patches and require at least K of them. This mirrors the parking "unreliable frame" idea and the PFSM occluded state.
2. **Hysteresis on a continuous score, not a vote on hard labels.** Keep a leaky-integrated or EMA dirty score per table, updated only on visible frames. Switch to dirty when it rises above T_high and back to clean when it falls below T_low, with T_low < T_high. Also require a minimum dwell, for example 3–5 s of accumulated visible evidence. A 2-state HMM with "sticky" transition probabilities (e.g. P(stay) ≥ 0.99 per frame) is the formal version, as listed in the parking patent.
3. **Semantic prior on transitions.** A table should not go from "needs clearing" to "cleared" unless a staff track (or any person) touched or stood at the table in between. Mirror TableWatch, where the camera never claims "cleaned" alone, and the parking track-based transitions. Without that, require long, unoccluded clean evidence such as ≥10 s. This alone should remove the "needs clearing then cleared within 1 s" flicker.
4. **Event order.** Evaluate "needs clearing" only after a confirmed "guest left" transition with a dwell of, say, 10–20 s with no seated guest. Run the timer as FlowLinks does.
5. **Reference snapshot.** Store a per-table clean-state reference, ideally several snapshots across lighting conditions. Refresh it when staff confirm "cleaned", similar to the slow-adapting long-term background.

### Gaps
- None of the sources reports false-alarm rates with versus without temporal smoothing, so the size of the improvement from hysteresis or HMM over voting is not quantified.
- Dwell-time values (seconds) used in commercial restaurant products are not published (TableWatch keeps them in a config file I could not see).

---

## Q3. Real-world accuracy, false-alarm rates, speed and hardware: vendor claims vs independent results

### Takeaway
Independent, peer-reviewed numbers exist mainly for parking (about 92–98% depending on cross-lot setting) and for abandoned-object benchmarks (high recall, 85–100% precision on small benchmark sets with few events). In every commercial category I checked, accuracy numbers are vendor-reported, with no third-party audit found:
- Occupancy sensors: about 95%.
- Retail OOS (Focal): about 95%.
- Food-waste vision (Winnow): about 80%.
- Restaurant table tracking: no numbers at all.

### Cited Findings

**Independent / academic**
- Parking (ACPDS, unseen lots): 97.97% (per-crop ResNet-50) and 98.51% (whole-image FPN). Training ran at about 40 s per epoch on an RTX 2080 Ti at full resolution. — [arXiv 2107.12207](https://arxiv.org/html/2107.12207)
- Parking cross-environment: 97.2% to 97.8% average, self-supervised. — [arXiv 2606.20886](https://arxiv.org/abs/2606.20886)
- Parking with limited labels: 93–96%. — [arXiv 2609.03258](https://arxiv.org/abs/2609.03258)
- A 2023 review argues that even the combined quality of PKLot, ACMPS, CNRPark and ACPDS "remains far from being satisfactory". — [ResearchGate: Revising deep learning methods in parking lot occupancy detection](https://www.researchgate.net/publication/371376123_Revising_deep_learning_methods_in_parking_lot_occupancy_detection) (from a search snippet)
- Abandoned objects (Sensors 2024), with recall 100% throughout:

  | Dataset | Precision | Notes |
  |---|---|---|
  | ABODA | 85.7% | 12 true positives, 2 false positives |
  | PETS2006 | 87.5% | |
  | AVSS2007 | 100% | |
  | ABODA, VisDrone re-splits | 71–75% | |

  The authors warn the benchmarks have few events and real-world results may differ. Hardware was an "NVIDIA GTX 3060", and **no FPS is reported**. — [PMC11510867](https://pmc.ncbi.nlm.nih.gov/articles/PMC11510867/)
- AnomalyDINO: 96.6% one-shot and 97.7% four-shot image AUROC on MVTec-AD, which is industrial close-ups and not CCTV. — [arXiv 2405.14529](https://arxiv.org/pdf/2405.14529) (the 4-shot figure comes from a search snippet)
- Retail OOS (Sensors 2024): direct OOS detection beats product-detection-based inference by 20–25% AP. — [MDPI](https://www.mdpi.com/1424-8220/24/2/693)
- YOLOE speed:
  - On a T4 with TensorRT, text-prompt models run at S 305.8 / M 156.7 / L 102.5 FPS, and visual-prompt models at S 64.3 / M 41.7 / L 27.2 FPS.
  - On a T4 with PyTorch, prompt-free models run at S 95.8 / M 45.9 / L 25.3 FPS.
  - Parameters: v8-S has 12–13M, and YOLOE-11-S has 10–12M.

  — [THU-MIG/yoloe](https://github.com/THU-MIG/yoloe)
- Seat sensors (non-camera, 2016-era): 91.2% accuracy over 36 seats and 8 weeks. — [ResearchGate](https://www.researchgate.net/publication/304533277_Small_Scale_Deployment_of_Seat_Occupancy_Detectors) (from a search snippet)

**Vendor claims (not independently verified)**
- Workplace occupancy sensors:
  - Butlr claims 95% accuracy "consistent across all lighting and environmental conditions". — [Butlr blog](https://www.butlr.com/blog/vergesense-vs-density)
  - VergeSense claims 95%+. — [VergeSense compare page](https://www.vergesense.com/resources/compare/vergesense-vs-butlr)
  - Density calls its radar "highest accuracy" with no test cited. Density's competitor page also alleges VergeSense "may count phone, laptop, smartwatch belonging to 1 person as 3 people". That is an unverified claim by a competitor. — [Density competitors page](https://density.io/competitors)
  - I found no independent test, and nothing for Xovis.
- Retail shelf: Focal Systems claims "95% accuracy according to both our own regular audits and store associate measurement". Walmart Canada rolled it out after a 70-store test, but no accuracy was published. — [Focal shelf cameras](https://focal.systems/shelf-cameras/); [Vision Systems Design](https://www.vision-systems.com/non-factory/article/14283989/vision-system-at-walmart-canada-tracks-inventory-on-store-shelves)
- Food-waste vision: Winnow Vision claims ">80% of food waste correctly identified" and says this exceeds human logging, which it puts at about 70–75%. It uses a camera, an NVIDIA Jetson TX2 and a scale under the bin. The pilot started in Jan 2018 with IKEA and Emaar. The claimed 70% waste reduction comes from Winnow case studies. Leanpath reportedly relies on manual item entry. — [The Spoon](https://thespoon.tech/winnow-launches-computer-vision-ai-tool-to-help-commercial-kitchens-fight-food-waste/); [Computer Weekly](https://www.computerweekly.com/news/252465110/How-computer-vision-powered-by-Nvidia-helped-Winnow-tackle-food-waste); [Hospitality Net](https://www.hospitalitynet.org/news/4092645.html)
- Restaurant table tracking: FlowLinks claims it works on existing CCTV with "0 new cameras", alerts within 60 s of vacancy, costs from $35 per camera per month and sets up in "days". It gives **no accuracy or false-alarm figures and names no customers** on the page. — [FlowLinks](https://www.flowlinks.ai/restaurants-cafes/table-turnover)
- Hospital beds: a vendor page cites an estimate of about 2 hours lost per room turnover after discharge (vendor framing). — [Kontakt.io](https://kontakt.io/?p=17819)

### Inferences
- Pitch-level numbers for Easy FnB should be framed as "parking-style per-spot classifiers reach ~95–98% on fixed cameras (peer-reviewed), but restaurant tables are harder because of people occluding and small, varied items". There is no independent restaurant benchmark to quote.
- Commercial categories converge on about 95% vendor claims, which is not evidence. A small self-labelled test on demo footage, e.g. 100–200 table-state clips with a confusion matrix and false-alarm count per hour, would be more convincing to judges than any borrowed number.
- On an RTX 3050 4GB, YOLOE-S class models (about 10–13M params) are in the same range as YOLO26s, so they are plausibly feasible. SAM-based change detectors are likely too heavy for per-frame use. This is an inference, and I did not measure it.

### Gaps
- No independent field evaluation of any restaurant table-state product (FlowLinks, Wobot, HeadRandom).
- No false-alarm-per-hour figures in any analogue domain from real deployments.
- No measured FPS for AnomalyDINO, CYWS, GeSCF or ZSSCD on consumer GPUs.
- I could not open the 2025 café-table YOLOv11 paper (PDF did not decode). A search snippet says it reports "92% human detection accuracy" with YOLOv11, with no detail on items. — [IJANSER PDF](https://as-proceeding.com/index.php/ijanser/article/download/3011/2863/5820)

---

## Q4. Commercial products, open-source projects and key papers

### Takeaway
The commercial landscape for restaurant "uncleared table" alerts on existing CCTV is thin: FlowLinks, HeadRandom and Wobot-style SOP analytics. Presto reportedly dropped its vision product. Adjacent mature commercial categories are workplace occupancy, retail shelf cameras and food-waste vision. Open-source work is mostly prototypes, plus reusable building blocks: ACPDS code, Ultralytics ParkingManagement, AnomalyDINO, YOLOE, CYWS-3D and ZSSCD.

### Cited Findings

**Commercial: restaurant**
- FlowLinks: table vacancy, "uncleared" and "cleared/wiped" verification on existing CCTV, plus a turnover clock. — [FlowLinks](https://www.flowlinks.ai/restaurants-cafes/table-turnover)
- HeadRandom describes an edge-AI table tracker with a "Vacant & Dirty" state for when guests have left but tableware remains. — [HeadRandom](https://headrandom.com/edge-ai-camera-restaurant-table-tracker)
- Wobot.ai offers QSR video analytics on existing CCTV, focused on SOP, hygiene and service-speed compliance. I could not confirm a specific dirty-table alert. — [Wobot QSR](https://wobot.ai/industry/qsr)
- Presto Vision: Presto piloted computer vision from Oct 2019. — [Wikipedia](https://en.wikipedia.org/wiki/Presto_(restaurant_technology_platform)). Restaurant Business reportedly says Presto later dropped vision to focus on voice AI. — [Restaurant Business](https://www.restaurantbusinessonline.com/technology/restaurants-take-closer-look-computer-vision). This page returned 403, so the claim comes from a search snippet, and the two sources conflict.
- A case study (unverified marketing) describes states such as "empty, occupied, in service, clearing". — [webdesignstudio.london](https://webdesignstudio.london/case-studies/real-time-table-intelligence)
- Ultralytics has a blog post on restaurant vision AI. — [Ultralytics blog](https://www.ultralytics.com/blog/streamlining-operations-using-vision-ai-in-restaurants)

**Commercial: adjacent**
- Workplace occupancy: Butlr (thermal), VergeSense, Density (radar). — [Butlr](https://www.butlr.com/blog/vergesense-vs-density), [VergeSense](https://www.vergesense.com/resources/compare/vergesense-vs-butlr), [Density](https://density.io/competitors)
- Retail: Focal Systems shelf cameras, deployed at Walmart Canada. — [Focal](https://focal.systems/shelf-cameras/)
- Food waste: Winnow Vision (camera, scale, Jetson); Leanpath (manual entry, per a trade article). — [The Spoon](https://thespoon.tech/winnow-launches-computer-vision-ai-tool-to-help-commercial-kitchens-fight-food-waste/)
- Hospital beds: Nyckel sells a pretrained image classifier "Identify if a hospital bed needs cleaned". — [Nyckel](https://www.nyckel.com/pretrained-classifiers/if-a-hospital-bed-needs-cleaned/)
- Hospital patents:
  - Camera recognition of cleaning tools to flag missed areas. — [US 9,204,823](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/9204823)
  - Vision-based mapping of cleaning behaviour to surfaces. — [US 12,243,229](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12243229)
  - Occupancy data triggering room cleaning. — [US 2017/0109481](https://uspto.report/patent/app/20170109481)

**Open-source**
- [TableWatch](https://github.com/gpradeep7898/Table-Watch-) (restaurant; YOLOX-Nano + ByteTrack-style + polygons + state machine; Apache-2.0 / MIT dependencies and no AGPL weights, per its README).
- [ACPDS code](https://github.com/martin-marek/parking-space-occupancy) (MIT).
- [Self-supervised parking](https://github.com/LoanMaikon/Parking-Spot-Occupancy-Recognition) (SimCLR; license not checked).
- [AnomalyDINO](https://github.com/dammsi/AnomalyDINO) (license not checked).
- [YOLOE](https://github.com/THU-MIG/yoloe) (AGPL-3.0).
- [CYWS-3D](https://github.com/ragavsachdeva/CYWS-3D) (license not checked).
- [ZSSCD](https://github.com/kyusik-cho/ZSSCD) (license not checked).
- [Ultralytics ParkingManagement](https://docs.ultralytics.com/guides/parking-management/).
- Library seat prototypes: [asumansaree](https://github.com/asumansaree/Library-Seat-Occupancy-Detection), [RexxarCHL](https://github.com/RexxarCHL/library-seat-detection).
- Plate-waste hackathon project (YOLOv5 + Streamlit). — [massarrahelenna/plate-waste-detector](https://github.com/massarrahelenna/plate-waste-detector)

**Key papers (2023–2026 unless noted)**
- ACPDS (2021). — [arXiv 2107.12207](https://arxiv.org/html/2107.12207)
- Self-supervised parking occupancy (SMC 2026). — [arXiv 2606.20886](https://arxiv.org/abs/2606.20886)
- Autoencoder-ensemble parking (2026). — [arXiv 2609.03258](https://arxiv.org/abs/2609.03258)
- Library seat hogging (2023). — [arXiv 2306.16080](https://arxiv.org/pdf/2306.16080)
- Dual-background abandoned objects (2024). — [PMC11510867](https://pmc.ncbi.nlm.nih.gov/articles/PMC11510867/)
- AnomalyDINO (WACV 2025). — [arXiv 2405.14529](https://arxiv.org/pdf/2405.14529)
- CYWS (WACV 2023) and CYWS-3D (ICCVW 2023). — [CVF](https://openaccess.thecvf.com/content/WACV2023/html/Sachdeva_The_Change_You_Want_To_See_WACV_2023_paper.html)
- ZSSCD (AAAI 2025). — [AAAI](https://ojs.aaai.org/index.php/AAAI/article/view/32253)
- GeSCF (CVPR 2025). — [CVF](https://openaccess.thecvf.com/content/CVPR2025/papers/Kim_Towards_Generalizable_Scene_Change_Detection_CVPR_2025_paper.pdf)
- OOS detection (Sensors 2024). — [MDPI](https://www.mdpi.com/1424-8220/24/2/693)
- ShelfChange3D (2026). — [arXiv 2610.01283](https://arxiv.org/html/2610.01283v1)
- YOLOE (ICCV 2025). — [arXiv 2503.07465](https://arxiv.org/pdf/2503.07465)
- Canteen plate waste with YOLOv11 (Applied Sciences 2025). — [doi 10.3390/app15137137](https://doi.org/10.3390/app15137137)

### Inferences
- No competitor publishes accuracy for "uncleared table". A small honest evaluation on the demo restaurant's footage would therefore be a differentiator.
- TableWatch's "camera never claims cleaned alone" plus one-tap staff confirmation is a pragmatic, defensible product choice that Easy FnB can copy for the demo UI.

### Gaps
- I could not verify Wobot's or HeadRandom's dirty-table detection method or accuracy.
- I found no hotel-housekeeping vision product with public details.

---

## Q5. Downloadable datasets and pretrained models (with licenses)

### Takeaway
No public restaurant table-state dataset was found. The usable public resources are:
- Parking datasets: PKLot (CC BY 4.0), CNRPark-EXT (reportedly ODbL), ACPDS (MIT) and MetaPKLot. These are for method prototyping, not transfer.
- Abandoned-object benchmarks: ABODA (public on GitHub), PETS2006 and AVSS2007.
- Before/after plate datasets: EcoPlate, FLIC, LeFoodSet and the YOLOv11 canteen set. Their licenses were not verified.

Among models:
- PE-Core is Apache-2.0, and DINOv2 is Apache-2.0.
- DINOv3 uses a custom Meta license with gated weights.
- YOLOE is AGPL-3.0, which is fine for a hackathon.

COCO's 80 classes lack "plate", "tray" and "napkin", which matters for Easy FnB's current detector.

### Cited Findings

**Datasets**
- **PKLot:** CC BY 4.0, per Roboflow and the MetaPKLot HF page. The original 2015 paper said "available for research purposes upon request". — [Roboflow PKLot](https://public.roboflow.com/object-detection/pklot); [MetaPKLot HF](https://huggingface.co/datasets/DSBD-Research/MetaPKLot-Dataset)
- **CNRPark-EXT:** stated as ODbL v1.0 on the MetaPKLot page. This was not confirmed on cnrpark.it. One source puts the size at 144,965 parking-space images from 9 cameras in varied weather, with harder occlusion (street lights, trees). — [MetaPKLot HF](https://huggingface.co/datasets/DSBD-Research/MetaPKLot-Dataset); size from a search snippet in [this result set](https://www.researchgate.net/publication/371376123_Revising_deep_learning_methods_in_parking_lot_occupancy_detection)
- **MetaPKLot:** more than 1.3M new annotations over PKLot, CNRPark-EXT and PLds, plus segmentation masks and timestamps for dwell time. — [HF dataset](https://huggingface.co/datasets/DSBD-Research/MetaPKLot-Dataset)
- **ACPDS:** 293 images, 11,236 spaces, MIT license (dataset, code and models). — [arXiv 2107.12207](https://arxiv.org/html/2107.12207); [GitHub](https://github.com/martin-marek/parking-space-occupancy)
- **Abandoned-object benchmarks:** ABODA (11 scenarios, public on GitHub), PETS2006 and AVSS2007 / i-LIDS (availability not stated). The paper's own data statement says one of the three abandoned-object datasets "is not currently available". — [PMC11510867](https://pmc.ncbi.nlm.nih.gov/articles/PMC11510867/)
- **Plate and tray before/after datasets (licenses not checked):**
  - EcoPlate: 313 plate pairs, 626 images, from an Indian hostel mess. — [IEEE DataPort](https://ieee-dataport.org/documents/ecoplate-paired-multimodal-dataset-indian-cafeteria-food-instance-segmentation)
  - FLIC: 401 full-tray and 401 leftover acquisitions, with weighed ground truth. — [MDPI Applied Sciences 16(11):5465](https://www.mdpi.com/2076-3417/16/11/5465)
  - LeFoodSet: 524 before/after pairs across 34 categories. — [ResearchGate](https://www.researchgate.net/publication/339168692_Automatic_Food_Leftover_Estimation_in_Tray_Box_Using_Image_Segmentation)
  - Canteen YOLOv11 custom set, plus TossIt Plates, Finding Defects and FoodWasteDetectionV2. — [Applied Sciences 2025](https://doi.org/10.3390/app15137137)
- **COCO** (CC BY 4.0) has cup, bowl, bottle, wine glass, fork, knife, spoon and dining table, but **no plate, tray or napkin class**. Chopsticks are also absent from the 80-class list. — [Ultralytics COCO docs](https://docs.ultralytics.com/datasets/detect/coco/)

**Models**
- **PE-Core-S16-384** (Meta Perception Encoder): Apache-2.0. The paper is dated 17 Apr 2025. — [HF model card](https://huggingface.co/facebook/PE-Core-S16-384)
- **DINOv3:** custom "DINOv3 License" (Aug 2025), "non-exclusive, worldwide, non-transferable and royalty-free limited license". The weights need sign-up. DINOv2, by contrast, was Apache-2.0. — [Meta DINOv3 License](https://ai.meta.com/resources/models-and-libraries/dinov3-license); [timm DINOv3 LICENSE copy](https://huggingface.co/timm/vit_small_plus_patch16_dinov3.lvd1689m/blob/main/LICENSE.md); [GitHub issue #31](https://github.com/facebookresearch/dinov3/issues/31)
- **YOLOE:** AGPL-3.0, sizes S/M/L from 10M to 50M params, with text, visual and prompt-free modes. — [THU-MIG/yoloe](https://github.com/THU-MIG/yoloe)
- **Grounding DINO:** Roboflow keeps a licensing page. — [Roboflow](https://roboflow.com/model-licenses/grounding-dino) (not opened)

### Inferences
- With **COCO lacking "plate" and "chopsticks"**, two of the most common leftovers in Vietnamese restaurants, a COCO-only YOLO26s will systematically under-detect leftovers. It may also flicker as plates get mis-labelled as "bowl" frame to frame. Alternatives include YOLOE text prompts such as "plate, chopsticks, napkin, tissue, food scraps, tray", YOLOE visual prompts from a reference crop, or a reference-diff approach that is class-agnostic.
- For hackathon use the license constraints are loose. PE-Core and DINOv2 are Apache-2.0, which is safest. DINOv3's custom license is fine for non-commercial demo use but needs gated download. YOLOE is AGPL.

### Gaps
- Licenses for EcoPlate, FLIC, LeFoodSet, the canteen YOLOv11 set, AnomalyDINO, CYWS-3D, ZSSCD, OWLv2, Florence-2 and SigLIP 2 were not verified in this pass.
- I found no public dataset of restaurant dining tables labelled empty / occupied / needs-clearing from CCTV, and no public "seat hogging" dataset.

---

## Q6. Pitfalls: camera angle, lighting, layout changes, people blocking the view, tablecloth and plate colours, reflections, restaurant-owned items

### Takeaway
The recurring pitfalls across analogues are:
- Heavy occlusion by neighbours or people, where models fail rather than degrade gracefully.
- Domain shift across sites and cameras, which costs roughly 2–6 accuracy points in parking cross-lot settings.
- Camera movement breaking fixed ROIs.
- Lighting changes fooling background models.
- Stationary people being mistaken for objects.
- Fixed-vocabulary detectors missing the actual items present.

Restaurant-owned items are a problem only for detector-based approaches. Reference-snapshot approaches absorb them.

### Cited Findings
- **Heavy occlusion:** ACPDS fails under heavy occlusion from adjacent vehicles, large vehicles or trees. Context-including square pooling helps. — [arXiv 2107.12207](https://arxiv.org/html/2107.12207)
- **Camera shift:** a search snippet states the PKLot UFPR04 camera "is moved at a certain point in time", breaking the fixed-camera assumption. — snippet from the [parking search results](https://arxiv.org/pdf/2404.14198) (exact source paper unverified). Patents explicitly address "abrupt camera field of view changes". — [US 9,716,837](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/9716837)
- **Lighting:** standard Gaussian mixture background models misclassify pixels after lighting changes. The 2024 method adds an entropy-based lighting term, but shows its effect only qualitatively. — [PMC11510867](https://pmc.ncbi.nlm.nih.gov/articles/PMC11510867/). Illumination change is described as "one major source of noise" in outdoor video. — [US 9,761,275](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/9761275)
- **Stationary people mistaken for objects:** a background-model-only pipeline flagged stationary pedestrians, with precision of 43–58%. Crowded scenes also make detectors miss partially occluded pedestrians. — [PMC11510867](https://pmc.ncbi.nlm.nih.gov/articles/PMC11510867/)
- **Ambiguous zone membership:** people standing in overlapping table zones. TableWatch counts them for neither table and makes the anchor point per camera angle. — [TableWatch](https://github.com/gpradeep7898/Table-Watch-)
- **Device and belonging miscounting** in occupancy sensing. This is a competitor's allegation that VergeSense counts a phone, laptop and watch as people. — [Density](https://density.io/competitors) (unverified)
- **Open-vocabulary detectors under distribution shift:** documented robustness drops. — [arXiv 2405.14874](https://arxiv.org/html/2405.14874v3)
- **Fixed vocabulary:** COCO has no plate, tray or napkin class. — [Ultralytics COCO](https://docs.ultralytics.com/datasets/detect/coco/)
- **Few-shot reference sensitivity:** reviewers note that AnomalyDINO's performance varies with which reference samples are chosen, and that it targets low-level, sensory anomalies. — [themoonlight.io review](https://themoonlight.io/review/anomalydino-boosting-patch-based-few-shot-anomaly-detection-with-dinov2) (secondary source)
- **Privacy and legal issues** are cited for camera-based seat occupancy. — [search summary of arXiv 2306.16080 and related](https://arxiv.org/pdf/2306.16080) (snippet)

### Inferences
These are mapped to Easy FnB.
- **Restaurant-owned items** (menus, condiments, napkin holders, chopstick boxes, sauce bottles): a COCO detector will count "bottle" (fish-sauce or chilli bottles) as a leftover. **This is a probable cause of false "needs clearing" alerts.** Fixes:
  - A per-table clean-reference memory bank, so owned items count as normal.
  - Or a static-object whitelist per table polygon, learned from clean snapshots.
- **Tablecloth and plate colours / reflections:** white plates on white or steel tables are low-contrast at an oblique CCTV angle. Patch-feature distance against a reference is more robust to this than pixel differencing. Glossy or steel tables reflect lights, which argues for multiple reference snapshots across times of day.
- **Layout changes** (tables pushed together, moved): polygons go stale. Detect this, for example when the clean-reference distance stays high for a long time with no people and no event, then ask the manager to re-snapshot or re-draw. This is the restaurant version of "camera FOV change" handling.
- **People blocking the view:** gate decisions on visible fraction (Q2). A seated guest's arms and torso over the table should make the frame "no observation" for clean/dirty, not "dirty".
- **Staff clearing:** a staff member standing at the table is both the occluder and the causal signal for "cleared". Use the staff track as the trigger, then wait for an unoccluded clean confirmation.

### Gaps
- I found no quantitative study of how oblique ceiling angles affect tabletop item detection accuracy.
- I found no source on tablecloth or plate colour effects specifically.

---

## Q7. Concrete application to Easy FnB: which stage each idea replaces or adds, and effort before vs after 14 Nov

### Takeaway
The highest-value, lowest-effort borrowings for the 9 days before the demo:
- **(a) Occlusion gating plus a hysteresis or sticky-HMM state machine** with a semantic "cleared needs staff visit" rule. This replaces the 1-second vote and directly targets the flicker.
- **(b) A per-table clean-reference patch memory bank, AnomalyDINO-style**, on top of the PE-Core (or DINOv2) features already in the pipeline. This replaces or augments the clean/dirty classifier head and handles restaurant-owned items.
- **(c) Context-padded square ROI crops**, from ACPDS.

Open-vocabulary YOLOE prompts for plate, chopsticks and napkin are a medium-effort optional add-on. SAM-based change detectors and self-supervised site adaptation are post-hackathon work.

### Cited Findings
These are the evidence each recommendation rests on, collected from Q1–Q6:
- Occlusion means unreliable frames and timers freeze. — [ResearchGate on-street parking](https://www.researchgate.net/publication/273872719_Video-based_real-time_on-street_parking_occupancy_detection_system); [PMC11510867](https://pmc.ncbi.nlm.nih.gov/articles/PMC11510867/)
- Temporal filters, including HMM. — [US20160093214A1](https://patents.google.com/patent/US20160093214)
- Track-based transitions with minimum duration. — [arXiv 2001.00269](https://arxiv.org/pdf/2001.00269)
- "Camera never claims cleaned alone", plus one-tap confirmation. — [TableWatch](https://github.com/gpradeep7898/Table-Watch-)
- Timer from vacancy, then an "uncleared" alert. — [FlowLinks](https://www.flowlinks.ai/restaurants-cafes/table-turnover)
- Person first, then belongings. — [US 12,380,725](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12380725)
- Patch memory bank with top-1% mean cosine distance, one-shot. — [AnomalyDINO](https://arxiv.org/pdf/2405.14529)
- Square context pooling, and whole-image backbone with RoI pooling. — [ACPDS](https://arxiv.org/html/2107.12207)
- Direct state detection beats enumerating objects. — [Sensors 2024 OOS](https://www.mdpi.com/1424-8220/24/2/693)
- COCO lacks plate, tray and napkin. — [Ultralytics COCO](https://docs.ultralytics.com/datasets/detect/coco/)
- YOLOE visual and text prompts, speeds and AGPL. — [THU-MIG/yoloe](https://github.com/THU-MIG/yoloe)
- Unlabeled first-N-days site specialisation. — [arXiv 2606.20886](https://arxiv.org/abs/2606.20886)
- PE-Core is Apache-2.0. — [HF](https://huggingface.co/facebook/PE-Core-S16-384)

### Inferences
These are recommendations derived from the analogues. Effort estimates are mine, for a 2-person team.

**A. Before 14 Nov (demo-critical)**

| # | Change | Stage affected | Analogue source | Est. effort |
|---|---|---|---|---|
| A1 | **Occlusion gate.** Per table and frame, visible fraction = 1 − (union of person boxes or pose-derived masks ∩ polygon) / polygon. Below a threshold such as 0.6, emit `NO_OBS` and do not vote. | Before the clean/dirty voting | On-street parking "unreliable frames"; PFSM occluded state | 2–4 h |
| A2 | **Replace the 1-s majority vote with a continuous score + hysteresis + min-dwell.** EMA of p(dirty) over `NO_OBS`-free frames. Dirty if > 0.7 for ≥ 3 s of visible time, clean if < 0.3 for ≥ 5–10 s. Optionally a 2-state HMM with sticky transitions. | State machine | Parking temporal filtering / HMM patent | 3–6 h |
| A3 | **Semantic transition rules.** (i) "needs clearing" only after a confirmed "guest left" with no seated guest for ≥ 10–20 s. (ii) "cleared" only if a staff track visited the table since "needs clearing" AND visible clean evidence persists ≥ N s. Otherwise keep "needs clearing". (iii) Optional one-tap staff confirm in the web UI. | Event generator | TableWatch; FlowLinks; seat-hogging patent | 3–6 h |
| A4 | **Context-padded square crop** around each polygon, instead of the tight polygon crop, for the PE-Core classifier. | Crop step | ACPDS square pooling | 1 h |
| A5 | **Clean-reference memory bank.** A manager button "snapshot: table clean now" stores PE-Core S/16 (or DINOv2-S, Apache-2.0) patch tokens per table, ideally 3–5 snapshots across lighting. Dirty score = mean of top-k% cosine distances of visible patches (mask out person-covered patches) to their nearest reference patch. Calibrate the threshold per table from a few clean and dirty frames. Use it as a second vote alongside the existing head, or replace the head. | Clean/dirty classifier | AnomalyDINO; abandoned-object long-term background | 1–2 days incl. UI button and calibration |
| A6 | **Detector role demotion and vocab fix.** Use COCO detections only as supporting evidence, e.g. bowls or cups present while no person is present. Optionally trial YOLOE-S text prompts ("plate", "chopsticks", "tissue", "food waste", "tray"). AGPL is OK for a hackathon. | Item detector | Retail OOS evidence; COCO class gap; YOLOE | 0.5–1 day (optional) |
| A7 | **Gemini verification at event time only**, sending both the current crop and the stored clean reference for a pairwise "what changed / are there leftovers?" judgement. Not per frame. | Verifier | CYWS pairwise change idea (concept only; no VLM evaluation found) | 2–4 h |
| A8 | **Mini evaluation.** Label about 100–200 table-state clips from demo footage. Report a confusion matrix and false alarms per hour, before vs after A1–A5. | Demo/pitch | No independent restaurant benchmark exists | 0.5 day |

**B. After the hackathon**
- Self-supervised site adaptation on unlabeled restaurant footage (SimCLR- or DINO-style), with a "first N days" specialised model as in arXiv 2606.20886.
- A small labelled restaurant table-state dataset, since none exists publicly.
- Pairwise change detectors (CYWS / CYWS-3D; SAM-based GeSCF / ZSSCD) evaluated offline. They are probably too heavy for a 4 GB GPU at frame rate, but could run on event-triggered crops.
- A dual long/short-term background model per table as a cheap CPU "something new is static on the table" trigger, with detector or embedding confirmation, because pure background modelling had 43–58% precision.
- Layout-change and camera-shift detection, i.e. persistent reference mismatch with no people present, prompting re-calibration.
- A learned HMM or transition probabilities from logged data.

Rationale notes:
- A5 is the single change most likely to cut false "needs clearing" alerts caused by restaurant-owned items. A1–A3 are the changes most likely to cut flicker.
- Both reuse the existing PE-Core backbone, so VRAM on the RTX 3050 4GB should stay roughly the same. This is an inference and not measured.

### Gaps
- No source validates any of these combinations on restaurant CCTV. The effort estimates and thresholds above are engineering judgement, not cited results.
- I did not verify that PE-Core S/16 patch tokens are as locally discriminative as DINOv2 patch tokens for the kNN memory-bank approach. AnomalyDINO used DINOv2 specifically for its patch features. A quick A/B on demo footage is advisable.
