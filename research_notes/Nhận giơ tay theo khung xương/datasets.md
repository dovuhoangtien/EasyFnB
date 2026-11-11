# Public datasets for skeleton-based "raise hand to call staff" vs confusable gestures (2D COCO-17 sequences)

Research date: 2026-11-05. Link checks: the OpenMMLab pickle URLs below returned HTTP 200 to `curl -I` on 2026-11-05. Other links were fetched or searched on that date unless marked otherwise.

Deployment target for comparison: YOLO26-pose 2D COCO-17 (x, y, conf), ByteTrack IDs, 5–25 fps, high-angle ceiling cameras, seated people with tables hiding the lower body.

---

## Q1. NTU RGB+D 60/120: relevant classes, counts, PYSKL/MMAction2 2D COCO-17 pickles, approval process

### Takeaway
NTU RGB+D 120 has the richest set of confusable negatives: drink, eat, brush hair, flick hair, glasses, phone call, headache, wipe face, yawn, stretch, salute, point, and others. It also has "hand waving" as the closest positive. OpenMMLab hosts HRNet-extracted 2D COCO-17 pickles as direct, login-free downloads (ntu60_2d.pkl 705 MB, ntu120_2d.pkl 1.24 GB), so the data can be used the same day. The official NTU approval process has no published turnaround time. NTU's licence is academic-only and forbids derived datasets without permission, so the pickles are a legal grey area and should not ship in a commercial product.

### Cited Findings
**Scale and setup**
- NTU RGB+D (60) has 60 classes and 56,880 samples. NTU RGB+D 120 has 120 classes and 114,480 samples. Both were captured by three Kinect V2 cameras at the same time. — [ROSE Lab NTU page](https://rose1.ntu.edu.sg/dataset/actionRecognition/)
- NTU60 has 40 subjects aged 10–35. In each setup the three cameras sit at the same height, at −45°, 0° and +45°. Camera height and distance change between the 17 setups. — [NTU RGB+D paper (CVPR'16, ar5iv)](https://ar5iv.labs.arxiv.org/html/1604.02808)
- NTU60 setup table (height, distance in m):

  | Setup | Height | Distance | Setup | Height | Distance |
  |---|---|---|---|---|---|
  | S001 | 1.7 | 3.5 | S010 | 1.8 | 3.0 |
  | S002 | 1.7 | 2.5 | S011 | 1.9 | 3.0 |
  | S003 | 1.4 | 2.5 | S012 | 2.0 | 3.0 |
  | S004 | 1.2 | 3.0 | S013 | 2.1 | 3.0 |
  | S005 | 1.2 | 3.0 | S014 | 2.2 | 3.0 |
  | S006 | 0.8 | 3.5 | S015 | 2.3 | 3.5 |
  | S007 | 0.5 | 4.5 | S016 | 2.7 | 3.5 |
  | S008 | 1.4 | 3.5 | S017 | 2.5 | 3.0 |
  | S009 | 0.8 | 2.0 | | | |

  — [NTU RGB+D paper, Table 2](https://ar5iv.labs.arxiv.org/html/1604.02808)
- NTU120 has 106 subjects from 15 countries, aged 10–57 and 1.3–1.9 m tall. Each subject performs each action twice, once towards the left camera and once towards the right. The comparison table lists 155 views for NTU120. — [NTU RGB+D 120 paper (TPAMI, ar5iv)](https://ar5iv.labs.arxiv.org/html/1905.04757)
- Raw 3D skeletons have 25 Kinect joints per frame. Skeleton downloads are 5.8 GB for NTU60 and 5.8 + 4.5 GB for NTU120. RGB is 1920×1080. — [ROSE Lab NTU page](https://rose1.ntu.edu.sg/dataset/actionRecognition/)

**Relevant classes.** The official ID is A-number. Below, `→ label N` means label = A − 1, which is the convention assumed for the pickle `label` field (see Gaps).

*Positive or near-positive*
- A23 hand waving (→22)
- A22 cheer up (→21, both arms up)
- A95 capitulate (→94, both hands raised, "surrender")
- A38 salute (→37, a hand raised to the forehead; a hard negative)
- A31 point to something (→30)
- A54 point finger (→53, two-person)

*Hand-to-head and hand-to-face negatives*
- A4 brush hair (→3)
- A68 flick hair (→67)
- A44 headache (→43, hand on head)
- A47 neck pain (→46)
- A37 wipe face (→36)
- A18 put on glasses (→17)
- A19 take off glasses (→18)
- A20 put on hat (→19)
- A21 take off hat (→20)
- A61 put on headphone (→60)
- A62 take off headphone (→61)
- A67 hush (→66)
- A79 sniff/smell (→78)
- A85 apply cream on face (→84)
- A103 yawn (→102)
- A105 blow nose (→104)
- A41 sneeze/cough (→40)
- A3 brush teeth (→2)
- A49 fan self (→48)

*Eating, drinking and phone negatives*
- A1 drink water (→0)
- A2 eat meal (→1)
- A28 phone call (→27)
- A29 play with phone/tablet (→28)
- A32 taking a selfie (→31)
- A33 check time from watch (→32)
- A113 cheers and drink (→112, two-person)

*Arm-motion negatives*
- A104 stretch oneself (→103)
- A97 arm circles (→96)
- A98 arm swings (→97)
- A10 clapping (→9)
- A34 rub two hands (→33)
- A39 put palms together (→38)
- A40 cross hands in front (→39)
- A96 cross arms (→95)
- A69 thumb up (→68)
- A72 victory sign (→71)
- A71 OK sign (→70)
- A77 snap fingers (→76)
- A35 nod head/bow (→34)
- A36 shake head (→35)

*Table-top "background" activity*
- A11 reading (→10)
- A12 writing (→11)
- A30 type on keyboard (→29)
- A74 counting money (→73)

— [ROSE Lab NTU class list](https://rose1.ntu.edu.sg/dataset/actionRecognition/)

**Pre-extracted 2D COCO-17 pickles (OpenMMLab)**
- MMAction2 hosts `ntu60_2d.pkl`, `ntu60_3d.pkl`, `ntu120_2d.pkl`, `ntu120_3d.pkl`, `gym_2d.pkl`, `ucf101_2d.pkl`, `hmdb51_2d.pkl`, `diving48_2d.pkl` and `k400_2d.pkl` at `https://download.openmmlab.com/mmaction/v1.0/skeleton/data/`. — [MMAction2 skeleton data README](https://github.com/open-mmlab/mmaction2/blob/main/tools/data/skeleton/README.md)
- Extraction pipeline: Faster R-CNN (ResNet-50) person detector, then top-down HRNet-w32 with the COCO config `coco/hrnet_w32_coco_256x192`. FineGYM uses ground-truth boxes instead. — [MMAction2 skeleton data README](https://github.com/open-mmlab/mmaction2/blob/main/tools/data/skeleton/README.md); also [PoseConv3D paper](https://ar5iv.labs.arxiv.org/html/2104.13586)
- Pickle format: a dict with `split` (split name → list of video IDs) and `annotations` (a list). Each annotation has these fields:
  - `frame_dir`
  - `total_frames`
  - `img_shape` and `original_shape`
  - `label` (int)
  - `keypoint` with shape M×T×V×C, where V = 17 for COCO and C = 2 for 2D
  - `keypoint_score` with shape M×T×V

  — [MMAction2 skeleton data README](https://github.com/open-mmlab/mmaction2/blob/main/tools/data/skeleton/README.md)
- PYSKL hosts the same data under different names: `.../mmaction/pyskl/data/nturgbd/ntu60_hrnet.pkl`, `ntu120_hrnet.pkl`, `ntu60_3danno.pkl` and `ntu120_3danno.pkl`. — [PYSKL tools/data README](https://github.com/kennymckormick/pyskl/blob/main/tools/data/README.md)
- Measured sizes (HTTP HEAD, 2026-11-05):

  | File | Bytes | Approx. |
  |---|---|---|
  | `ntu60_2d.pkl` | 705,401,771 | 705 MB |
  | `ntu120_2d.pkl` | 1,238,461,428 | 1.24 GB |
  | `ntu120_3d.pkl` | 2,079,477,249 | 2.08 GB |
  | `k400_2d.pkl` | 1,159,782,864 | 1.16 GB |

  `ntu60_hrnet.pkl` and `ntu120_hrnet.pkl` from PYSKL have identical byte sizes to the MMAction2 files, so they are almost certainly the same files. Last-Modified is 22 Dec 2022. All URLs returned HTTP 200. — direct check of [download.openmmlab.com](https://download.openmmlab.com/mmaction/v1.0/skeleton/data/ntu120_2d.pkl)
- Neither the PYSKL nor the MMAction2 README states any licence or terms for the pickle files, and neither mentions NTU approval. Both just point to the official NTU repository for raw `.skeleton` files. — [PYSKL README](https://github.com/kennymckormick/pyskl/blob/main/tools/data/README.md); [MMAction2 README](https://github.com/open-mmlab/mmaction2/blob/main/tools/data/skeleton/README.md)

**Official NTU access and licence**
- Access process: register an account, submit the request form and accept the Release Agreement. ROSE Lab then validates the request and approves the download. One login covers both datasets. The page does not state a turnaround time. — [ROSE Lab NTU page](https://rose1.ntu.edu.sg/dataset/actionRecognition/)
- The GitHub FAQ says request submission sometimes fails with "500 – Internal server error" and asks users to email the team. — [shahroudy/NTURGB-D GitHub](https://github.com/shahroudy/NTURGB-D)
- Licence: academic research only, free for non-commercial use by educational or research institutes. Redistribution, deriving or generating a new dataset, and commercial use without ROSE Lab permission are "considered illegal". Subject images may only be shown in academic publications and presentations. — [ROSE Lab NTU page](https://rose1.ntu.edu.sg/dataset/actionRecognition/)

### Inferences
- **Sample counts.** The averages are 56,880/60 ≈ 948 samples per class (NTU60) and 114,480/120 = 954 per class (NTU120). Each relevant class therefore has roughly 950 clips across 40 or 106 subjects. A23 hand waving alone gives about 950 positives. Exact per-class counts weren't verified; NTU has a few hundred known missing or empty skeleton samples.
- **Pickle IDs encode the setup.** `frame_dir` follows the NTU naming `SsssCcccPpppRrrrAaaa`. You can filter by setup ID to keep the highest cameras (NTU60 S013–S017 are 2.1–2.7 m), which are closest to a ceiling view. Even 2.7 m is only mildly downward-looking compared with a restaurant ceiling camera.
- **Format compatibility.** The 2D pickles are already COCO-17 from HRNet, in the same keypoint order YOLO-pose uses. No joint remapping is needed; only coordinate normalisation and fps resampling (NTU is about 30 fps) to the 5–25 fps deployment range.
- **Legal status.** The OpenMMLab pickles bypass the NTU approval step in practice. Legally, they are a derivative of NTU, and NTU's terms forbid deriving datasets and commercial use without permission. For a hackathon demo this is likely tolerable. Do not ship weights trained on NTU in a commercial Easy FnB product without ROSE Lab permission.
- **Missing positive.** NTU has no explicit "raise one hand and hold it to call someone" class. A23 (waving), A22/A95 (both hands up) and A38 (salute) are proxies or hard negatives. The true positive must come from BK-SAD hand-raising, UAV-Human "put up hands", and the team's own clips.
- **Domain gap.** NTU 2D crops are full-body, standing-heavy, roughly eye-level, with frontal and ±45° views. At training time, zero out or drop hip, knee and ankle keypoints (conf = 0) and apply random perspective or rotation to mimic seated, occluded, high-angle input.

### Gaps
- No source states how long NTU approval takes. Plan as if it won't arrive before 14 Nov.
- It wasn't confirmed that the pickle `label` is 0-indexed (A − 1). This is the usual PYSKL convention; check it after download by matching against the `Aaaa` suffix in `frame_dir`.
- Which NTU actions were performed seated wasn't verified (likely reading, writing and typing). The paper text retrieved doesn't say.
- No explicit licence was found for the OpenMMLab-hosted pickles.

---

## Q2. Kinetics skeletons (k400_2d from PYSKL/MMAction2): relevant classes and noise

### Takeaway
Kinetics-400 has no "waving hand" or "raising hand" class. Waving hand only appears in Kinetics-600/700, and no pre-extracted skeletons for those were found. K400 skeletons are noisy (skeleton-only top-1 accuracy is 47.7%), and the keypoints come as a separate large download. Use K400 only as an optional source of in-the-wild negatives such as drinking, eating, brushing or fixing hair, and yawning.

### Cited Findings
- `k400_2d.pkl` holds only the table of contents. The keypoints come as `k400_kpfiles_2d.zip` from OpenXLab (`openxlab.org.cn/datasets/OpenMMLab/Kinetics400-skeleton`), extracted to `data/skeleton/kpfiles`. — [MMAction2 skeleton README](https://github.com/open-mmlab/mmaction2/blob/main/tools/data/skeleton/README.md)
- PYSKL distributes the K400 kpfiles via a SharePoint link instead. The K400 annotation adds `raw_file`, `frame_inds`, `box_score` and `valid` fields. — [PYSKL tools/data README](https://github.com/kennymckormick/pyskl/blob/main/tools/data/README.md)
- **Noise level.** PoseConv3D's skeleton-only top-1 accuracy on K400 is 47.7%. PoseConv3D uses top-down Faster R-CNN R50 plus HRNet pretrained on COCO-keypoint for all datasets except FineGYM. — [PoseConv3D paper](https://ar5iv.labs.arxiv.org/html/2104.13586)
- Relevant K400 classes (0-indexed lines of MMAction2 `label_map_k400.txt`):
  - applauding 3
  - braiding hair 32
  - brushing hair 36
  - clapping 57
  - curling hair 80
  - drinking 100
  - eating burger … eating watermelon 109–117
  - fixing hair 128
  - front raises 134
  - shaking hands 288
  - shaking head 289
  - sign language interpreting 303
  - sneezing 319
  - stretching arm 333
  - tasting food 353
  - texting 355
  - yawning 397

  There is no waving, raising-hand or pointing class. — [MMAction2 label_map_k400.txt](https://raw.githubusercontent.com/open-mmlab/mmaction2/main/tools/data/kinetics/label_map_k400.txt)
- K600 adds, among others: adjusting glasses 2, combing hair 104, looking at phone 265, scrubbing face 435, talking on cell phone 516, **waving hand 581**. — [label_map_k600.txt](https://raw.githubusercontent.com/open-mmlab/mmaction2/main/tools/data/kinetics/label_map_k600.txt)
- K700 has adjusting glasses 2, combing hair 116, looking at phone 302, **saluting 500**, scrubbing face 507, talking on cell phone 608, **waving hand 680**. — [label_map_k700.txt](https://raw.githubusercontent.com/open-mmlab/mmaction2/main/tools/data/kinetics/label_map_k700.txt)
- Kinetics-700 is almost a superset of Kinetics-600. Some new classes were taken from AVA and EPIC-Kitchens verb lists. — [Kinetics-700 note (arXiv 1907.06987)](https://arxiv.org/pdf/1907.06987v2.pdf)

### Inferences
- Using K600/K700 "waving hand" would mean downloading YouTube clips (many are dead) and running YOLO26-pose yourself. That is not realistic within 1–2 days.
- K400 skeletons are multi-person, cut by camera edits and full of low-confidence joints. They help mostly as diverse negatives, and the download is very large.

### Gaps
- The size of `k400_kpfiles_2d.zip` and whether the OpenXLab link is currently alive weren't checked.
- No public pre-extracted 2D skeletons were found for K600/K700.
- The Kinetics annotation licence wasn't verified in this session.

---

## Q3. Classroom hand-raising datasets (BK-SAD, SCB, SAV, others)

### Takeaway
BK-SAD (Hanoi University of Science and Technology, HUST) is the closest match to the target domain:
- real Vietnamese classrooms
- students seated at desks
- elevated corner cameras
- 2,723 hand-raising videos with per-student keypoints
- a direct zip download with no registration

Its keypoints are an 18-point format (BK-Pose, COCO-trained) and need remapping to COCO-17. SCB-dataset is images with boxes, not sequences. SAV is video-only.

### Cited Findings
**BK-SAD (BK-Student Activity Dataset)**
- 3 classes: hand raising, doze-off, normal. It contains over 2,700 hand-raising, 1,700 dozing and 8,500 normal videos. — [BK-SAD paper, JST Smart Systems & Devices 33(3), 2023](https://storage.googleapis.com/jst-journals/articles/ssad/168/23021_1.3m.pdf) ([DOI page](https://jst.hust.edu.vn/journals/jst.168.ssad.2023.33.3.3))
- Videos per class (Table 1):

  | Class | Train | Test | Share |
  |---|---|---|---|
  | Doze | 1,217 | 522 | 13.32% |
  | Hand-raising | 1,996 | 727 | 20.85% |
  | Normal | 6,018 | 2,579 | 65.83% |
  | **Total** | **9,231** | **3,828** | |

  — [BK-SAD paper](https://storage.googleapis.com/jst-journals/articles/ssad/168/23021_1.3m.pdf)
- Collection: Chu Van An Secondary School, Long Bien District (Hanoi). 10 classes of at least 30 students each, 20 minutes per class. Desks were in rounded groups. At least four 3MP cameras sat at the top, left, right and back corners of the room. Each scripted action was repeated 100 times, with 5-second videos. — [BK-SAD paper](https://storage.googleapis.com/jst-journals/articles/ssad/168/23021_1.3m.pdf)
- Labelling and keypoints: bounding boxes and per-frame activity labels were done in CVAT. Long videos were cut into 10-second clips of 250 frames (about 25 fps). Keypoints come from the "BK-Pose" model trained on COCO, which gives **18 keypoints** per student inside the manually drawn box. — [BK-SAD paper](https://storage.googleapis.com/jst-journals/articles/ssad/168/23021_1.3m.pdf)
- Dataset page details:
  - 48,457 hand-raising, 34,762 dozing and 171,940 normal labelled frames (255,159 total)
  - released as per-student cropped images with keypoint coordinate text files
  - direct `BK-SAD.zip` link with no registration form or approval step
  - no licence or citation shown

  The page mentions **three** cameras (front, left, right), while the paper says at least four. — [visedu.vn BK-SAD page](https://visedu.vn/en/bk-sad-dataset)

**SCB-dataset (Student Classroom Behavior)**
- Classes are hand-raising, reading and writing. Downloads are on Baidu Netdisk (several extraction codes) and a Hugging Face mirror at `huggingface.co/datasets/wintonYF/SCB-Dataset`. The repo says the university-classroom version (SCB-dataset3) is being "remade". — [SCB-dataset GitHub](https://github.com/Whiffe/SCB-dataset)
- Licence: academic research, personal learning and non-commercial use; commercial use needs written permission; "All rights reserved". The repo has no video or sequence version. — [SCB-dataset GitHub](https://github.com/Whiffe/SCB-dataset)
- An earlier SCB hand-raising method used Faster R-CNN plus OpenPose keypoints. — [search summary of SCB paper arXiv 2304.02488](https://arxiv.org/abs/2304.02488v3)

**SAV (Student Action Video)**
- 4,324 trimmed clips from 758 classrooms, 15 student actions, multi-label, "varied shooting angles". It is video-only with no skeletons. Code and data are at `github.com/Ritatanz/SAV`. — [arXiv 2409.00926](https://arxiv.org/abs/2409.00926)

### Inferences
- **Keypoint mapping.** BK-SAD's 18 points are very likely the OpenPose/CMU COCO-18 layout (COCO-17 plus a neck). That layout is: nose, neck, R-shoulder, R-elbow, R-wrist, L-shoulder, L-elbow, L-wrist, R-hip, R-knee, R-ankle, L-hip, L-knee, L-ankle, R-eye, L-eye, R-ear, L-ear. If so, mapping to COCO-17 means dropping the neck and reordering, about 20 lines of code. Confirm on the files.
- **Domain match.** BK-SAD matches the target on seated people, desks hiding the lower body, elevated corner cameras, Vietnamese subjects and about 25 fps. Its hand-raising class is the closest public "raise hand to get attention" positive.
- **Negatives.** "Normal" is a weak negative: it doesn't specifically contain hair-touching or drinking. Combine it with NTU hard negatives.
- **SCB.** SCB images can train a single-frame "hand raised" pose prior, either by running YOLO26-pose on them or as an auxiliary check. They can't train temporal models.

### Gaps
- It's unconfirmed whether BK-SAD's released files keep per-student track or sequence IDs. The page describes cropped images plus keypoint text files, so turning them back into sequences may depend on filenames.
- BK-SAD's exact 18-keypoint order, the zip size and the licence are unverified (none is shown on the page).
- SCB per-class counts and the annotation file format (likely YOLO boxes) weren't confirmed from the repo page.
- SAV's 15 class names weren't retrieved.
- EduNet and other classroom datasets weren't researched (time budget).

---

## Q4. Other datasets: PKU-MMD, UAV-Human, Toyota Smarthome, ETRI-Activity3D, AVA, BABEL/AMASS, MPOSE2021

### Takeaway
UAV-Human is the most useful extra skeleton source:
- high-angle aerial views
- 17-keypoint skeletons
- classes "wave hands", "put up hands", "touch the hair", "headache", "make a phone call", "drink", "point somewhere"

PKU-MMD (direct Google Drive) gives untrimmed NTU-style sequences for online detection. Toyota Smarthome and ETRI-Activity3D need approval or membership. AVA and BABEL need heavy conversion. MPOSE2021 is a tiny, instant pip download.

### Cited Findings
**UAV-Human (SUTD, CVPR 2021)**
- 155 classes (A000–A154). Relevant ones:
  - A000 drink
  - A002 brush hair
  - A013 put on glasses
  - A014 take off glasses
  - A019 wave hands
  - A024 make a phone call
  - A026 point somewhere
  - A028 rub hands
  - A030 shake head
  - A037 touch the hair
  - A055 put up hands
  - A067 headache
  - A073 stretch body
  - A132 wave a goodbye
  - A143 call for help

  The README says "available for Download now" via `sutdcv.github.io/uav-human-web`, and that consent forms were obtained from all subjects. No licence is stated. — [UAV-Human GitHub README](https://github.com/sutdcv/UAV-Human)
- Action recognition has 22,476 × 3 sequences (Azure Kinect, fisheye, night-vision) with 119 subjects. Data was collected in urban and rural areas, day and night. "The skeleton modality stores the positions of 17 major key-points." A pose subset has 22,476 frames manually labelled with 17 joints. — [UAV-Human paper (ar5iv)](https://ar5iv.labs.arxiv.org/html/2104.00946)

**PKU-MMD**
- Phase 1: 1,076 long videos, 51 classes (41 daily, 10 interaction), 66 subjects, 3 views, about 21,545 action instances, 30 fps, 3–4 minutes per video. Phase 2: 1,009 videos, 41 classes, 13 subjects. Skeletons are Kinect v2, 25 joints, 3D. Downloads are on Google Drive (Phase 1) and Google Drive or BaiduYun (Phase 2), with no approval step mentioned. — [PKU-MMD project mirror](https://struct002.github.io/PKUMMD)
- The phase 2 numbers conflict: the official ICST page reportedly says "2000 short video sequences in 49 action categories". — [search summary of ICST page](https://www.icst.pku.edu.cn/struct/Projects/PKUMMD.html); contradicted by [struct002 mirror](https://struct002.github.io/PKUMMD)
- Cameras were at −45°, 0° and +45°, all at 120 cm height. Example actions include drinking, waving hand and putting on glasses. — [PKU-MMD paper arXiv 1703.07475](https://arxiv.org/pdf/1703.07475); [mirror](https://struct002.github.io/PKUMMD)
- An IRISA mirror offers a single `PKUMMD.zip` with split files. — [IRISA OAD datasets](https://www-intuidoc.irisa.fr/oad-datasets/)

**Toyota Smarthome**
- Content:
  - 16,115 trimmed clips covering 31 activities, plus Untrimmed (TSU) with 536 videos of about 21 minutes and 51 activities
  - 18 seniors aged 60–80
  - 7 Kinect v1 cameras at 640×480
  - RGB, depth and 3D skeleton extracted from RGB

  — [Toyota Smarthome project page](https://project.inria.fr/toyotasmarthome/)
- Access: online form with a work or institutional email (Gmail is ignored unless institutional). If there's no reply within 3 days, email toyotasmarthome@inria.fr. "Provided for academic research only." — [Toyota Smarthome project page](https://project.inria.fr/toyotasmarthome/)
- The skeletons come from LCR-Net (LCR-Net++). Activities include drink from can, bottle, glass or cup (coarse label "drink"), watch TV, sit down, read book and clean dishes. Subjects were not told how to perform activities, and recordings cover 3 scenes. — [Toyota Smarthome ICCV'19 paper](https://openaccess.thecvf.com/content_ICCV_2019/papers/Das_Toyota_Smarthome_Real-World_Activities_of_Daily_Living_ICCV_2019_paper.pdf)

**ETRI-Activity3D**
- 112,620 samples, 55 classes (52 elderly daily activities plus 3 human–robot interaction), 100 subjects (50 elderly aged 70+, 50 young adults in their 20s). Captured with Kinect v2 (RGB, depth, skeleton) in an apartment. Camera heights were 70 cm and 120 cm (robot view). Subjects were encouraged to vary posture, for example taking medicine while sitting or standing. — [ETRI-Activity3D paper arXiv 2003.01920](https://arxiv.org/pdf/2003.01920)
- Download needs membership on the ETRI AI4Robot site; contact dhkim008@etri.re.kr. — [search summary of ai4robot page](https://ai4robot.github.io/etri-activity3d-en); [ETRI NANUM](https://nanum.etri.re.kr/share/judekim/HMI?lang=En_us)

**AVA v2.2**
- 80 classes. Relevant ones:
  - hand wave (69)
  - point to (an object) (43)
  - drink (27)
  - eat (29)
  - answer phone (15)
  - text on/look at a cellphone (57)
  - touch (an object) (59)
  - hand clap (67)
  - sit (11)
  - talk to (79)

  There is no "raise hand", "scratch" or "stretch" class. — [AVA action list v2.2](https://research.google.com/ava/download/ava_action_list_v2.2.pbtxt)

**BABEL (labels over AMASS mocap)**
- About 37.5 hours of densely labelled mocap (about 42 hours including the extra labels), released as JSON (`train`, `val`, `test`, `extra_train`, `extra_val`). Motion comes from AMASS (`feat_p` = path to the AMASS motion file). — [BABEL data page](https://babel.is.tue.mpg.de/data.html)
- Relevant raw labels sit under the "arm movements" category: "raise arms up", "wave arms", "both hand touch head", "point right arm forward", "stretch arms up wide", "scratch under left arm pit". "Drink" (#50) and "eat" (#54) are their own categories. — [BABEL action categories](https://babel.is.tue.mpg.de/actionsrawlabels.html)

**MPOSE2021**
- 15,429 samples, 20 actions, 100 subjects, 20–30 frames per sample. Poses come from OpenPose and PoseNet, plus MoveNet in later package versions. Install with `pip install mpose` (v1.2, 9 Nov 2023). PyPI lists the licence as MIT. — [PyPI mpose](https://pypi.org/project/mpose/)
- The GitHub repo shows a GPL-v3 badge and says the data is "intended for scientific research purposes" (conflicts with MIT on PyPI). Sources are Weizmann, i3DPost, IXMAS, KTH, UTKinect, UTD-MHAD and ISLD. — [MPOSE2021 GitHub](https://github.com/PIC4SeR/MPOSE2021_Dataset)
- The AcT paper uses 13 OpenPose keypoints or 17 PoseNet keypoints, each with x, y, vx, vy, and T = 30. — [Action Transformer paper (ar5iv 2107.00606)](https://ar5iv.labs.arxiv.org/html/2107.00606)

**Restaurant-specific data**
- No public skeleton dataset for "raise hand to call a waiter" or attention-seeking gestures was found. The closest were pedestrian, taxi-hailing and hand-gesture datasets. — [search: e.g., pedestrian gesture paper arXiv 2602.08479](https://arxiv.org/pdf/2602.08479)

### Inferences
- **UAV-Human** fits better than NTU for both viewing angle and class semantics: "put up hands", "wave hands", "touch the hair", "headache". If its 17 keypoints are in COCO order, they map directly. Check the joint order and whether the data is 2D or 3D before relying on it.
- **PKU-MMD** classes overlap NTU's. Because it's untrimmed, it suits training a streaming detector's background and "no-action" segments. You'd still need Kinect-25 → COCO-17 mapping (no eyes or ears) and 3D → 2D projection.
- **Kinect-25 → COCO-17 mapping** (0-indexed Kinect joints):

  | COCO | Kinect joint |
  |---|---|
  | nose | Head (3), approximate |
  | L/R shoulder | 4 / 8 |
  | L/R elbow | 5 / 9 |
  | L/R wrist | 6 / 10 |
  | L/R hip | 12 / 16 |
  | L/R knee | 13 / 17 |
  | L/R ankle | 14 / 18 |
  | eyes, ears | not available (set conf = 0 or synthesise from Head) |

- **AVA and BABEL** are poor value for a 9-day hackathon:
  - AVA is box annotations on movie keyframes, so it needs video download plus pose extraction.
  - BABEL needs AMASS/SMPL-H body-model processing and virtual-camera 2D projection.
- **MPOSE2021** is tiny, instantly available, single-person and standing-heavy. It's mostly useful as a smoke test or extra negatives.

### Gaps
- Not verified:
  - UAV-Human: actual download procedure (form?), licence, skeleton file format (2D vs 3D, joint order), per-class sample counts
  - PKU-MMD: full 51-class list with IDs and licence
  - Toyota: full 31-class list and LCR-Net joint count (believed 13; not confirmed)
  - ETRI: class list, approval time and licence
  - BABEL/AMASS: registration and licence terms (license page not read)
  - MPOSE2021: the exact 20 class labels (believed to include wave, point, scratch-head, check-watch, cross-arms; unconfirmed)
- Not researched (time budget): Charades, JHMDB, InHARD, NTU-X, HumanML3D, EduNet. JHMDB is believed to include "wave", "sit", "pour" and "brush_hair" with 15-joint puppet masks, but no source was retrieved.
- No public pre-extracted 2D keypoints for AVA were found.

---

## Q5. Which datasets have seated people and high camera angles (closest to restaurant CCTV)?

### Takeaway
BK-SAD is the only public source found that combines seated people, table occlusion and elevated corner cameras with an explicit hand-raising class. UAV-Human gives steep top-down angles, but its subjects mostly stand outdoors. NTU's higher setups (up to 2.7 m) give a mild downward view. PKU-MMD (1.2 m) and ETRI (0.7/1.2 m) are low eye- or robot-level views. Toyota Smarthome has realistic seated eating and drinking, but camera mounting isn't documented in the sources read.

### Cited Findings
- BK-SAD: students seated at desks in rounded groups, cameras at the top, left, right and back corners. — [BK-SAD paper](https://storage.googleapis.com/jst-journals/articles/ssad/168/23021_1.3m.pdf)
- UAV-Human: footage from a flying UAV with varied flying attitudes, occlusions and camera motion. — [UAV-Human paper](https://ar5iv.labs.arxiv.org/html/2104.00946)
- NTU60 camera heights range from 0.5 to 2.7 m across 17 setups, at distances of 2–4.5 m. — [NTU paper Table 2](https://ar5iv.labs.arxiv.org/html/1604.02808)
- PKU-MMD cameras are at 120 cm height. — [PKU-MMD paper](https://arxiv.org/pdf/1703.07475)
- ETRI-Activity3D cameras are at 70 and 120 cm, with sitting or standing variants. — [ETRI paper](https://arxiv.org/pdf/2003.01920)
- Toyota Smarthome has unscripted daily activities such as drinking, reading and watching TV, across 7 views in 3 scenes. — [Toyota ICCV'19 paper](https://openaccess.thecvf.com/content_ICCV_2019/papers/Das_Toyota_Smarthome_Real-World_Activities_of_Daily_Living_ICCV_2019_paper.pdf)

### Inferences
- No public dataset matches restaurant CCTV exactly. The best fit is BK-SAD (seated, elevated, hand raising) plus NTU 2D hard negatives, with geometric augmentation:
  - random rotation and perspective warp toward a top-down view
  - scale jitter
  - lower-body keypoint dropout to simulate tables
  - temporal resampling to 5–25 fps
  - keypoint confidence noise to match YOLO26-pose
- Re-running YOLO26-pose on the team's own 60 clips (and on BK-SAD frames, if raw frames are available) aligns the keypoint error distribution with deployment.

### Gaps
- Toyota Smarthome camera mounting heights and NTU seated or standing posture per class were not confirmed.

---

## Q6. Recommended combination, expected effort, and mapping to COCO-17

### Takeaway
Within 1–2 days, use:
- **(a)** `ntu120_2d.pkl` (1.24 GB, direct download, already COCO-17)
- **(b)** BK-SAD.zip (direct download, seated, hand-raising positives; 18 → 17 remap)
- **(c)** the team's 60 self-recorded clips via YOLO26-pose
- **(d) optional:** UAV-Human skeletons for high-angle "put up hands" / "wave hands" / "touch hair", if downloadable without delay

Skip anything needing approval or video re-processing: official NTU raw data, Toyota, ETRI, AVA, Kinetics-700 and BABEL.

### Cited Findings
- `ntu120_2d.pkl` (1,238,461,428 bytes) and `ntu60_2d.pkl` (705,401,771 bytes) are live at download.openmmlab.com with no login. — [MMAction2 README](https://github.com/open-mmlab/mmaction2/blob/main/tools/data/skeleton/README.md); HEAD check 2026-11-05
- The pickles are in COCO-17 format (V = 17) from HRNet-w32 top-down. — [MMAction2 README](https://github.com/open-mmlab/mmaction2/blob/main/tools/data/skeleton/README.md)
- BK-SAD is a direct `BK-SAD.zip` from visedu.vn with no registration. — [visedu.vn](https://visedu.vn/en/bk-sad-dataset)
- BK-SAD keypoints are 18 points from BK-Pose. — [BK-SAD paper](https://storage.googleapis.com/jst-journals/articles/ssad/168/23021_1.3m.pdf)
- Toyota and NTU raw data need request and approval, with no guaranteed timing (Toyota: "contact us if no response in 3 days"). — [Toyota page](https://project.inria.fr/toyotasmarthome/); [NTU page](https://rose1.ntu.edu.sg/dataset/actionRecognition/)

### Inferences
**Suggested label scheme for NTU120 2D**
- **Positive:** A23 hand waving.
- **Optional soft positive or separate class:** A22 cheer up and A95 capitulate. Both are two-hands-up; decide whether "both hands up" counts as calling staff.
- **Hard negatives:** A1, A2, A4, A18, A19, A28, A29, A31, A32, A33, A37, A38, A41, A44, A47, A49, A67, A68, A79, A85, A103, A104, A105.
- **Easy negatives:** A11, A12, A30, A10, A34, A39, A40.

This gives about 950 positive and over 20k negative clips. Subsample negatives or use class weights.

**Effort estimate (2-person team)**
- NTU pickle: download 1.24 GB plus a filter, resample and normalise script, about 0.5 day. Filter by A-number, choose the main person (M index), crop to the upper body, resample 30 fps to 5–25 fps, and normalise relative to the shoulders.
- BK-SAD: download, inspect, remap 18 → 17, rebuild sequences from per-student files, about 0.5–1 day. The risk is sequence reconstruction.
- Own clips: YOLO26-pose + ByteTrack export to the same format, about 0.5 day.
- UAV-Human: 0.5 day if the download is accessible. Otherwise skip.

**COCO-17 targets**
- The NTU 2D pickle is already COCO-17.
- BK-SAD: drop the neck and reorder.
- Any Kinect-25 source: use the table in Q4 with eye and ear confidence set to 0.
- At train time, mask hip, knee and ankle keypoints with high probability to match table occlusion. Many teams just use the 13 upper-body plus head keypoints.

**Evaluation**
- Keep the team's own 60 clips (2 actors) strictly for evaluation or fine-tuning, split by actor. Public data is for pretraining only.

**Licensing**
- NTU (academic only, no derivatives), SCB (non-commercial) and Toyota (academic only) all rule out commercial deployment.
- For the 14 Nov demo this is acceptable as a non-commercial prototype. Document it, and plan to retrain on owned data before any commercial pilot.

### Gaps
- BK-SAD file format and zip size, UAV-Human download mechanics, and the exact NTU label indexing should be verified on first download. These couldn't be confirmed from web pages alone.
