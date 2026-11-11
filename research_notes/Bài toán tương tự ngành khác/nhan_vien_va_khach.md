# Cross-industry analogues: telling staff apart from customers/visitors in CCTV (role recognition) — for Easy FnB

Scope: retail footfall staff exclusion, uniform/clothing and pedestrian attribute recognition (PAR), sports team/referee assignment, kitchen-uniform and PPE detection, operating-room role recognition, behaviour/trajectory cues, few-shot enrolment + ReID, face-library opt-in, and open-vocabulary/VLM approaches. Research date: 5 Nov 2026. Vendor claims are labelled **[VENDOR]**; academic/independent measurements are labelled **[ACADEMIC]**. Items older than 2023 carry their year.

---

## Q1. What are the best current methods (2023–2026), and which are practical in real time on a 4 GB GPU for ~10–30 people per frame?

### Takeaway
Industry uses five families of methods, often combined: (1) a cue the staff wear (uniform, apron, lanyard, badge, patterned tag) plus a per-site detector or classifier tuned on sample images; (2) wearable radio tags (BLE/UWB) or IR shoulder tags; (3) behaviour, zone and trajectory rules; (4) ReID or face enrolment against a staff gallery; (5) unsupervised clustering of appearance embeddings (the sports "team classifier"). The approach most practical on a 4 GB GPU with existing CCTV is to reuse the embedding Easy FnB already computes (CLIP/PE-Core) per track, average it over the tracklet, and match it against a gallery of staff crops enrolled at the start of each shift. That score is then fused with zone and behaviour priors. Zero-shot text prompts such as "person wearing an apron" are the weakest of these options.

### Cited Findings
**Retail footfall / staff exclusion (industry methods)**
- FootfallCam documents eight staff-exclusion methods: staff exclusion line, zone + wall button, patterned staff tag (passive stripe tag on upper chest), fabric ToF-reflective shoulder tag, **staff uniform exclusion**, **Re-ID**, time-based adjustment (e.g. "5 staff at 9–10am" or a % deduction) and lanyard detection. Page updated 22 Oct 2026. **[VENDOR]** — [FootfallCam Appendix A – Staff Exclusion Methods](https://footfallcam.com/people-counting/?p=3229)
- FootfallCam's Re-ID staff exclusion (3D Pro2, 2025, fw v5.2.0+) "needs a learning period of a few weeks", works best where staff move across several zones, and may bring limited benefit in small stores. No accuracy figure is given. **[VENDOR]** — [FootfallCam Appendix A](https://footfallcam.com/people-counting/?p=3229)
- FootfallCam's uniform exclusion requires a logo larger than 20×20 cm or a unique pattern/colour, a dominant colour covering ≥70% of the uniform, a colour whitelist/blacklist, and a walk-test video of 20 IN + 20 OUT. The setup turnaround (SLA) is 3–7 days with the video and 14 days without. **[VENDOR]** — [FootfallCam Appendix A](https://footfallcam.com/people-counting/?p=3229)
- Aura Vision runs on existing CCTV ("If you can see it on a CCTV monitor today, Aura Vision can analyse it") on an on-premise unit and sends only aggregated metrics to the cloud. **[VENDOR]** — [Aura Vision: How does it work](https://auravision.ai/knowledge/getting-started/how-does-it-work)
- Aura Vision staff segmentation keys on "a distinctive visual cue — typically a uniform, polo, apron or lanyard". During onboarding the setup team tunes the model with "sample images of your team wearing the chosen cue at the store", and each location is tuned separately. Anyone wearing the cue is classed as staff. **[VENDOR]** — [Aura Vision staff segmentation](https://www.auravisionlabs.com/knowledge/analytics/demographics/staff-segmentation)
- Aura Vision states it does no facial detection or recognition; all data is "from the body". **[VENDOR]** — [Aura Vision overview (search summary)](https://support.auravision.ai/portal/en/kb/articles/an-overview-of-aura-vision)
- Milesight offers three methods. UWB tags with anchors are positioned for high-end retail. A VA04 shoulder/chest badge or epaulet is recognised by VS125 sensors. Lanyard detection uses VA21 (VS125) and VA31 (VS13x). Staff do not need to register IDs or face data. **[VENDOR]** — [Milesight Staff Exclusion](https://www.milesight.com/iot/innovation/ai-people-counting/staff-exclusion)
- V-Count's staff exclusion uses an IR-detected **shoulder tag** read by a top-down Nano AI sensor mounted at 2.8–5 m. Each employee needs a tag and it must be "visible in full". The page was published Dec 2022 and has been updated since. **[VENDOR]** — [V-Count: What is Staff Exclusion](https://v-count.com/what-is-staff-exclusion-in-people-counting-and-how-it-works)
- Xovis (through integrator Vemco) uses tag-based staff exclusion. It is an "Exclude staff" option sold as a licensed extension pack, configured with tag position and mounting height, and is reportedly **not available on the PF-Series**. I did not find Xovis' own docs. **[VENDOR/integrator]** — [Vemco: Xovis adults/children/groups/staff setup](https://intercom.help/vemco/en/articles/15444658-xovis-adults-children-groups-staff-counting-setup)
- RetailNext earlier used "patented Wi-Fi and video analytics" to exclude employees. It later added BLE beacons, worn by associates as "fobs", and promotes UWB as more precise than BLE. **[VENDOR]** — [RetailNext press release (BLE beacons)](https://prnewswire.com/news-releases/retailnext-extends-traffic-counting-and-staffing-optimization-solutions-with-beacon-based-employee-analytics-300133119.html); [UNTUCKit help page listing Aurora camera + fobs](https://techitsupport.untuckit.com/portal/en/kb/articles/elements-of-retail-next-traffic-counting-system)
- Sensormatic/ShopperTrak says it "removes staff movements from your store traffic counts" with overhead devices but does not disclose how. **[VENDOR]** — [Sensormatic Employee Exclusion](https://sensormatic.com/shopper-insights/retail-analytics/employee-exclusion)
- Hikvision supports "Customer Traffic Task Excluding Staff". The operator selects face comparison group(s) and a similarity threshold, and people matching above the threshold are not counted. **[VENDOR doc]** — [Hikvision: Add Customer Traffic Task Excluding Staff](https://enpinfo.hikvision.com/hkwsen/unzip/20230830144955_12918_doc/GUID-515292ED-4EFD-43FB-BDB5-3C872EE37360.html)
- Eocortex can exclude people in a face-database group from unique-visitor counts. It says masked employees are identified "with fairly high accuracy" if the database contains unmasked samples. **[VENDOR doc]** — [Eocortex Unique Visitor Counting](https://doc.eocortex.com/analytics/unique-visitors/overview.htm)
- XXII CORE (France) detects visible signs: uniforms, polos, a badge's presence (not its contents), caps, aprons, hi-vis vests. These are applied as exclusion rules and positioned as non-biometric, with no face recognition and no individual profiles. **[VENDOR]** — [XXII: How to exclude staff from in-store counting](https://xxiiai.com/en/le-blog/comment-exclure-le-personnel-du-comptage-en-magasin)
- FootfallCam (per the Retail Sensing / search summary) also describes recognising staff "by behaviour, not clothing" using travel paths and dwell time behind counters, aimed at shops without uniforms. **[VENDOR]** — [FootfallCam Staff Exclusion technology page](https://www.footfallcam.com/Resources/Technologies/StaffExclusion) (via search summary; page not fetched)

**Behaviour / trajectory / zone cues**
- [ACADEMIC, 2020] Recognises customers vs staff from movement patterns using track heatmaps from a head-detection tracker. It reports 98% accuracy in training and **93% in evaluation on a 24-hour real supermarket recording**. — [arXiv 2005.08009](https://arxiv.org/abs/2005.08009)
- Open-source restaurant CCTV project (YOLOv8n + ByteTrack + Shapely table polygons). A person is a **waiter if they visit ≥3 distinct tables within 2 minutes**. Customers go WALKING → AT_TABLE after a 5 s dwell, with a 2 s occlusion grace. No accuracy reported. — [anuj1611/ai-restaurant-cctv-monitoring](https://github.com/anuj1611/ai-restaurant-cctv-monitoring)
- ChefSight (restaurant CCTV prototype) infers staff from staff-only zones or repeated short table visits. Its README warns accuracy depends on visibility and calibration. — [ChefSight](https://github.com/rubayetkabirzisan/ChefSight) (via search summary)
- restaurant-cv-insights excludes host-stand staff with a polygon zone (YOLO26s, person class only). — [Haseeeb21/restaurant-cv-insights](https://github.com/Haseeeb21/restaurant-cv-insights) (via search summary)
- SmartServe AI (YOLO26) treats raw detections as provisional until temporal checks or staff confirmation support them. — [swapnil3104/YOLO26-Restaurant-Table-Occupancy-Service-Tracker](https://github.com/swapnil3104/YOLO26-Restaurant-Table-Occupancy-Service-Tracker) (via search summary)

**Sports: unsupervised team/role assignment (the "team-clustering trick")**
- Roboflow's basketball pipeline (30 Sep 2025) runs SigLIP embeddings on the **central part of each player box**, to avoid the opponent or crowd in the crop. Embeddings are reduced to 3-D with UMAP and split with KMeans k=2. Fitting uses 1 frame/s from sample videos of the game. The whole pipeline runs at 1–2 FPS on a T4, with SAM2 as the bottleneck rather than the classifier. No clustering accuracy is reported. — [Roboflow blog: identify basketball players](https://roboflow.com/blog/identify-basketball-players)
- The Roboflow `sports` repo (MIT) uses the same SigLIP → UMAP → KMeans team classifier for soccer. — [roboflow/sports soccer example (mirror)](https://github.meowingcats01.workers.dev/roboflow/sports/tree/main/examples/soccer) (via search summary)
- [ACADEMIC, 2024] Multi-task ReID + team affiliation + **role classification (player / goalkeeper / referee / staff)** on SoccerNet-Tracking with an HRNet-W32 BPBReID backbone. Role accuracy is **94.27%** but precision only **74.36%** (class imbalance; focal loss used). Per-video KMeans team accuracy is 91.87% with ReID features alone, 95.17% with a team loss, and 95.6% with team + role losses. Code was "will be released" with no link. — [arXiv 2401.09942](https://arxiv.org/html/2401.09942v1)
- [ACADEMIC, 2024] The SoccerNet Game State Reconstruction baseline runs KMeans (k=2) on **tracklet-level** ReID embeddings for team assignment. — [arXiv 2404.11335](https://arxiv.org/pdf/2404.11335)
- [ACADEMIC, 2025] A follow-up uses **five clusters** (left/right players, referees, left/right goalkeepers), i.e. it separates officials by clustering as well. — [arXiv 2504.06357](https://arxiv.org/pdf/2504.06357)
- [ACADEMIC, 2021] Contrastive unsupervised player classification first removes referees with a CNN, then clusters players. It notes that referees misclassified as players add noise. — [arXiv 2104.10068](https://arxiv.org/html/2104.10068v2)

**PAR / clothing attributes (2023–2026)**
- [ACADEMIC, TCSVT 2024] PromptPAR (CLIP-based, region-aware prompt tuning of only 0.75% of parameters) reports F1 of 90.15 on PA100K, 82.38 on RAPv1 and 81.00 on RAPv2. It also has zero-shot splits (PETA-ZS, RAP-ZS). — [arXiv 2312.10692](https://arxiv.org/abs/2312.10692)
- [ACADEMIC, WACVW 2025] AttriVision uses **vanilla CLIP ViT-B/32** features and reports UPAR mA 89.4 / F1 91.9 and +2.5 mA over the previous best on PA100K. This is the same backbone family Easy FnB already uses. — [AttriVision (CVF open access)](https://openaccess.thecvf.com/content/WACV2025W/V3SC/papers/Sedeh_AttriVision_Advancing_Generalization_in_Pedestrian_Attribute_Recognition_using_CLIP_WACVW_2025_paper.pdf) (numbers via search summary; PDF returned 403 to my fetch)
- [ACADEMIC, 2024/25] CLIP-ResNet50 pretraining raised PA100K mA from 79.92 to 82.39. — [ACM DL: Recognition of Pedestrian Attributes based on Multimodal Features](https://dl.acm.org/doi/10.1145/3697467.3697631)
- [ACADEMIC, 2024] A benchmark of VQA/VLM models for **zero-shot** PAR concludes they give "highly competitive results" without training cost. I could not open the PDF to get the numbers. — [Castrillón-Santana et al., SN Computer Science 2024](https://accedacris.ulpgc.es/bitstream/10553/131973/1/s42979-024-02985-0.pdf)

**Kitchen / hygiene uniform detection (restaurant-adjacent)**
- [ACADEMIC, 2022] YOLOv5l + DeepSORT tracks kitchen staff and flags a missing hat or mask. Trained on 2,000 labelled images, it reports 95.32% hat accuracy. — [MATEC Web of Conf. ICPCM 2022](https://www.matec-conferences.org/articles/matecconf/abs/2022/02/matecconf_icpcm2022_03024/matecconf_icpcm2022_03024.html)
- [ACADEMIC, 2025] An improved YOLOv10n for kitchen hat/mask detection reports only **69.5% mAP@0.5** on 6,508 self-built images with small and occluded targets. — [MDPI Sensors 25(22) 6893](https://www.mdpi.com/1424-8220/25/22/6893)
- [ACADEMIC] A YOLOv5s kitchen standard-dress (chef cap + mask) detector was built on 7,558 images. — [ProQuest record](https://www.proquest.com/docview/2779523766) (via search summary)
- ACTi sells "Missing Chef Hat Detection" analytics. **[VENDOR]** — [ACTi](https://www.acti.com/applications/missing-chef-hat-detection)

**Healthcare / operating room roles**
- A gaze-following OR paper predicts clinical roles self-supervised, with **F1 0.92 for role prediction on 4D-OR**. Its year is unconfirmed. — [chatpaper summary "Where are they looking in the operating room?"](https://chatpaper.com/paper/271615) (secondary source)
- [ACADEMIC, 2026] Self-supervised, uncalibrated multi-view OR video anonymisation finds clinicians and the patient without annotations, using tracking and cross-view association. — [arXiv 2602.02850](https://arxiv.org/html/2602.02850v2)
- A University of Twente PhD project on OR scene understanding covers detecting staff and identifying their role, with explicit privacy attention; the defence is listed for May 2026. — [UTwente project page](https://www.utwente.nl/en/eemcs/mia/research/projects/projectpage-gerats/)
- [2026 preprint] A multi-camera retail/warehouse staff monitoring framework (pose-based tracking, skeleton activity classification, homography cross-view ReID) relies on **face recognition** for identity. The authors themselves say face recognition is weak under CCTV conditions. No accuracy is given. — [Zenodo 20758114 (CC BY 4.0)](https://zenodo.org/records/20758114)

**Compute: what fits on 4 GB**
- OSNet ReID (torchreid model zoo): x1_0 has 2.2M params, 0.98 GFLOPs, Market-1501 R1/mAP 94.2/82.6. **x0_25 has 0.2M params, 0.08 GFLOPs, R1/mAP 91.2/75.0**. — [torchreid MODEL_ZOO](https://kaiyangzhou.github.io/deep-person-reid/MODEL_ZOO)
- BoxMOT auto-downloads ReID weights ranging from lightweight (OSNet, LightMBN, e.g. `osnet_x0_25_market1501.pt`, `lmbn_n_cuhk03_d.pt`) to heavy (CLIP-ReID, `clip_market1501.pt`). It exports to ONNX, OpenVINO, TorchScript and TensorRT. — [BoxMOT on PyPI](https://pypi.org/project/boxmot/10.0.54)
- SigLIP 2 base-patch16-224 is ~0.4B params including the text tower, Apache-2.0, paper Feb 2025. — [HF google/siglip2-base-patch16-224](https://huggingface.co/google/siglip2-base-patch16-224)
- PE-Core is released as G14-448, L14-336 and B16-224 (L and B are distilled from G). The HF checkpoints are tagged Apache-2.0. — [HF facebook/PE-Core-L14-336](https://huggingface.co/facebook/PE-Core-L14-336); [HF pe_core_base_patch16_224_timm README](https://huggingface.co/facebook/pe_core_base_patch16_224_timm/blob/main/README.md)

### Inferences
- The industry splits cleanly. **Purpose-built overhead counters** (Xovis, V-Count, FootfallCam tags, Milesight, RetailNext) mostly rely on a worn tag, because top-down views hide uniforms and logos. **Existing-CCTV analytics** (Aura Vision, XXII, FootfallCam uniform mode) rely on a per-site, per-cue appearance classifier tuned on sample images. Easy FnB is in the second group, so its current "embedding + small linear head" design is the industry-standard shape. The missing parts are per-site enrolment and temporal/behaviour fusion.
- Aura Vision's per-store tuning "with sample images of your team wearing the chosen cue" is effectively few-shot enrolment. Easy FnB can do the same per shift in about 1 minute: each staff member walks past the camera, and the same CLIP/PE-Core embeddings already being computed become a staff-prototype gallery.
- Within a shift, staff do not change clothes. Plain short-term appearance ReID (OSNet or the existing CLIP/PE-Core embedding) is therefore enough, and clothes-changing ReID (Q4) is unnecessary for the hackathon.
- Cost per crop: OSNet x0_25 is ~0.08 GFLOPs, so running it on 30 crops per frame is negligible. ViT-B encoders (CLIP B/32, PE-Core B/16) cost far more per crop (I have no sourced FLOPs or FPS figures for them on an RTX 3050). Running the heavy embedding only every N frames per track and averaging over the tracklet, as Easy FnB already does every ~6 frames, is the right lever. The sports literature also aggregates at tracklet level (SoccerNet GSR).
- The sports results suggest that when staff wear a consistent colour, unsupervised 2-cluster KMeans on tracklet-averaged embeddings can reach ~92–96% separation (soccer numbers), and refereeing roles can be pulled out as an extra cluster. Restaurants are harder than soccer: customer clothing is heterogeneous, so "customers" is not one cluster. A better framing is **one-class / prototype matching for staff** plus "everything else = customer", not k=2.

### Gaps
- No measured FPS for CLIP B/32 or PE-Core B/16 on an RTX 3050 4 GB with 10–30 crops/frame; Easy FnB must benchmark itself.
- Could not retrieve Xovis' own documentation, the internals of Vaidio's or Axis's staff-exclusion features, or how Sensormatic/ShopperTrak filters staff (not disclosed publicly).
- AttriVision's and the VQA-PAR paper's full texts were blocked (HTTP 403); their numbers come from search snippets.

---

## Q2. Real-world accuracy and failure rates (vendor claims vs independent studies), especially with weak uniforms or similar customer clothing

### Takeaway
Almost all published staff-exclusion accuracy numbers are vendor claims ("up to 99%"). The most honest vendor disclosure is FootfallCam's grading: >90% for strong uniforms, 70–90% for distinct colour combinations without a dominant colour, and **<70% for uniforms that meet no requirements**. That last band is exactly the small-Vietnamese-restaurant case (apron or T-shirt only). I found no independent audit of any vendor's staff-exclusion accuracy. The academic evidence is small: 93% for trajectory-only in one supermarket (2020), and ~94% role accuracy but 74% precision in sports.

### Cited Findings
- FootfallCam uniform-exclusion grades: **A >90%** (uniform meets colour/pattern rules), **B 70–90%** (unique colour combination but no unique dominant colour), **C <70%** (meets no requirements). These are a guideline subject to a site assessment. **[VENDOR]** — [FootfallCam Appendix A](https://footfallcam.com/people-counting/?p=3229)
- Milesight: "up to 99%" for UWB tags. No numbers are given for the visual badge or lanyard methods. Its FAQ concedes uniform-based methods are less reliable when customers dress similarly. **[VENDOR]** — [Milesight Staff Exclusion](https://www.milesight.com/iot/innovation/ai-people-counting/staff-exclusion)
- V-Count claims "up to 99%" counting accuracy in general, not specifically for staff exclusion. It also claims competitors "can barely deliver about 85%", without a source. **[VENDOR]** — [V-Count staff exclusion page](https://v-count.com/what-is-staff-exclusion-in-people-counting-and-how-it-works)
- A search summary says another V-Count page cites 90% staff-exclusion accuracy; I did not verify it. **[VENDOR]** — [V-Count Ultima AI page](https://v-count.com/ultima-ai/) (unverified)
- Aura Vision references a 99% staff-recognition figure, but its conditions were on a page I could not retrieve. It also says re-tuning is needed when uniforms change or staff work out of uniform. **[VENDOR]** — [Aura Vision staff segmentation](https://www.auravisionlabs.com/knowledge/analytics/demographics/staff-segmentation)
- RetailNext's self-reported counting accuracy is 95–99% (search summary). **[VENDOR]** — [RetailNext Traffic Analytics brief](https://retailnext.net/hubfs/Briefs/RetailNext_Brief_Traffic_Analytics.pdf?hsLang=en) (via search summary)
- A vendor-neutral guide recommends validating uniform-based methods under real operating conditions and rates fixed staff-only zones as "Medium — inaccurate if staff enter visitor areas". — [Foorir: Why is staff exclusion important](https://www.foorir.com/staff-exclusion-retail-traffic-analytics/) (via search summary)
- [ACADEMIC, 2020] Trajectory-heatmap staff/customer classifier: **93%** evaluation accuracy on a real 24-hour supermarket video (98% training). — [arXiv 2005.08009](https://arxiv.org/abs/2005.08009)
- [ACADEMIC, 2024] Sports role classification (player/goalkeeper/referee/staff): **94.27% accuracy but 74.36% precision**, i.e. the rare class is much harder than the headline number suggests. — [arXiv 2401.09942](https://arxiv.org/html/2401.09942v1)
- [ACADEMIC, WACVW 2024] The UPAR Challenge 2024 tests PAR under domain shift, with MEVID added as a new test domain. Ten teams beat the baseline on attribute recognition, but **none beat it on attribute-based retrieval**, showing how hard cross-domain attribute generalisation is. — [Cormier et al., UPAR Challenge 2024](https://openaccess.thecvf.com/content/WACV2024W/RWS/html/Cormier_UPAR_Challenge_2024_Pedestrian_Attribute_Recognition_and_Attribute-Based_Person_Retrieval_WACVW_2024_paper.html)
- [ACADEMIC, NeurIPS 2026] On MSP60K split by scenario, VLMs' "text-image alignment degrades under covariate shift". **Zero-shot ranking on unseen attributes stays close to chance for every evaluated method**, and the best overall mA is 0.6938 (PerceptPAR). — [Salunkhe, Rathore, Banerjee, NeurIPS 2026](https://neurips.cc/virtual/2026/180070)
- [ACADEMIC, 2023] POAR argues plain CLIP "falls short for fine-grained attribute recognition". — [POAR arXiv 2303.14643](https://arxiv.org/pdf/2303.14643)
- [ACADEMIC, 2025] Even supervised detection of a small uniform item (kitchen hats/masks) reaches only 69.5% mAP@0.5 with small, occluded targets. — [MDPI Sensors 2025](https://www.mdpi.com/1424-8220/25/22/6893)

### Inferences
- With an apron or T-shirt colour only, the realistic expectation for a single-frame appearance classifier is FootfallCam's Grade B–C band (≈70–90% or worse), not 99%. Temporal smoothing per track and fusion with behaviour and zone priors is what recovers usable accuracy. The 93% trajectory-only figure suggests behaviour alone is already competitive.
- For a demo, the most important metric is **false "call" alerts caused by staff**. That means precision on "staff" matters less than recall: a staff member labelled as customer causes a false alert or a false occupancy reading. Easy FnB should tune thresholds and report its own confusion matrix on a held-out clip.
- Zero-shot text prompts ("person wearing an apron") should be treated as a weak prior or bootstrap labeller, not the classifier. The evidence (POAR 2023, NeurIPS 2026) says unseen fine-grained attributes are near chance under domain shift. A linear probe or prototype on the site's own staff crops is the reliable route, consistent with Aura Vision's per-store tuning.

### Gaps
- **No independent (non-vendor) audit of staff-exclusion accuracy found** for Xovis, V-Count, Aura Vision, RetailNext, ShopperTrak, Hikvision or Milesight. IPVM has a "Hikvision People Counting Tested" report ([IPVM](https://ipvm.com/reports/hikvision-people-counting-test)), but it is paywalled and I did not confirm it covers staff exclusion.
- No published accuracy for any restaurant-specific waiter/customer classifier; the GitHub projects found report none.

---

## Q3. Commercial products, open-source projects, key papers

### Takeaway
Commercial: Aura Vision and XXII are closest to Easy FnB (existing CCTV plus a visual cue). FootfallCam has the most transparent menu of methods. Xovis, V-Count, Milesight and RetailNext rely on tags or beacons; Hikvision and Eocortex use face-library exclusion. Open source: Roboflow `sports` for the team-clustering trick, BoxMOT and torchreid for ReID, and several 2026 restaurant-CCTV repos with rule-based waiter detection. Key papers: PromptPAR (2024), AttriVision (2025), SoccerNet GSR team clustering (2024–25), multi-task role classification (2024), and the 2020 supermarket trajectory classifier.

### Cited Findings
**Commercial (all [VENDOR])**
| Vendor | Mechanism | Source |
|---|---|---|
| Aura Vision | Existing CCTV; per-store model tuned on sample images of staff wearing a uniform, polo, apron or lanyard; no face | [staff segmentation](https://www.auravisionlabs.com/knowledge/analytics/demographics/staff-segmentation) |
| XXII CORE | Detects visible signs (uniform, badge presence, cap, apron, hi-vis); non-biometric rules | [XXII blog](https://xxiiai.com/en/le-blog/comment-exclure-le-personnel-du-comptage-en-magasin) |
| FootfallCam | Exclusion line, zone + button, patterned tag, fabric ToF tag, uniform, Re-ID (weeks of learning), time-based, lanyard | [Appendix A](https://footfallcam.com/people-counting/?p=3229) |
| Milesight | UWB tags; VA04 badge/epaulet; VA21/VA31 lanyards | [Milesight](https://www.milesight.com/iot/innovation/ai-people-counting/staff-exclusion) |
| V-Count | IR shoulder tag, top-down sensor 2.8–5 m | [V-Count](https://v-count.com/what-is-staff-exclusion-in-people-counting-and-how-it-works) |
| Xovis | Tag-based "Exclude staff" extension (PC series; not PF series per Vemco) | [Vemco](https://intercom.help/vemco/en/articles/15444658-xovis-adults-children-groups-staff-counting-setup) |
| RetailNext | Wi-Fi + video (earlier), BLE fobs, UWB | [PR Newswire](https://prnewswire.com/news-releases/retailnext-extends-traffic-counting-and-staffing-optimization-solutions-with-beacon-based-employee-analytics-300133119.html) |
| Sensormatic ShopperTrak | Overhead counters, method undisclosed | [Sensormatic](https://sensormatic.com/shopper-insights/retail-analytics/employee-exclusion) |
| Hikvision | Face comparison group + similarity threshold | [Hikvision doc](https://enpinfo.hikvision.com/hkwsen/unzip/20230830144955_12918_doc/GUID-515292ED-4EFD-43FB-BDB5-3C872EE37360.html) |
| Eocortex | Face database groups excluded from counts | [Eocortex](https://doc.eocortex.com/analytics/unique-visitors/overview.htm) |
| Retail Sensing | Anonymous counting, explicitly no facial recognition | [Retail Sensing](https://www.retailsensing.com/definition/staff-exclusion.html) (via search summary) |
| ACTi | Missing chef hat detection (kitchen) | [ACTi](https://www.acti.com/applications/missing-chef-hat-detection) |

**Open source**
- Roboflow `sports` (MIT): SigLIP + UMAP + KMeans team classifier. — [Roboflow blog](https://roboflow.com/blog/identify-basketball-players); [repo mirror](https://github.meowingcats01.workers.dev/roboflow/sports/tree/main/examples/soccer)
- A community HF "team-classifier" ships a SigLIP base with a serialised UMAP + KMeans pipeline. — [HF 7gonzalodm/team-classifier](https://huggingface.co/7gonzalodm/team-classifier/blob/main/README.md) (via search summary)
- BoxMOT: trackers plus a ReID zoo (OSNet, LightMBN, CLIP-ReID) with ONNX/TensorRT export. — [PyPI boxmot](https://pypi.org/project/boxmot/10.0.54)
- torchreid / deep-person-reid: OSNet family with the model zoo. — [MODEL_ZOO](https://kaiyangzhou.github.io/deep-person-reid/MODEL_ZOO)
- Restaurant CCTV repos (2026, no accuracy numbers): [anuj1611/ai-restaurant-cctv-monitoring](https://github.com/anuj1611/ai-restaurant-cctv-monitoring) (≥3 tables in 2 min → waiter); [ChefSight](https://github.com/rubayetkabirzisan/ChefSight); [SmartServe AI / YOLO26](https://github.com/swapnil3104/YOLO26-Restaurant-Table-Occupancy-Service-Tracker); [restaurant-cv-insights](https://github.com/Haseeeb21/restaurant-cv-insights)

**Key papers**
- PromptPAR, CLIP-based PAR, TCSVT 2024 — [arXiv 2312.10692](https://arxiv.org/abs/2312.10692)
- AttriVision, CLIP ViT-B/32 PAR generalisation, WACVW 2025 — [CVF](https://openaccess.thecvf.com/content/WACV2025W/V3SC/papers/Sedeh_AttriVision_Advancing_Generalization_in_Pedestrian_Attribute_Recognition_using_CLIP_WACVW_2025_paper.pdf)
- UPAR Challenge 2024 (domain-shift PAR) — [CVF](https://openaccess.thecvf.com/content/WACV2024W/RWS/html/Cormier_UPAR_Challenge_2024_Pedestrian_Attribute_Recognition_and_Attribute-Based_Person_Retrieval_WACVW_2024_paper.html)
- GZS-DG-PAR / PerceptPAR, NeurIPS 2026 — [NeurIPS](https://neurips.cc/virtual/2026/180070)
- Multi-task ReID + team + role, 2024 — [arXiv 2401.09942](https://arxiv.org/html/2401.09942v1)
- SoccerNet GSR, 2024, and follow-up, 2025 — [arXiv 2404.11335](https://arxiv.org/pdf/2404.11335); [arXiv 2504.06357](https://arxiv.org/pdf/2504.06357)
- SoccerMaster (late 2025): team affiliation from clustering tracklet-averaged ReID embeddings plus pitch coordinates — [arXiv 2512.11016](https://arxiv.org/html/2512.11016v1) (via search summary)
- In-store tracking with staff/customer recognition from track heatmaps, 2020 — [arXiv 2005.08009](https://arxiv.org/abs/2005.08009)
- Clothes-changing ReID, e.g. DIFFER 2025 (EVA2-CLIP-L; PRCC CC R1/mAP 68.5/64.7, LTCC CC 58.2/31.6) — [arXiv 2503.22912](https://arxiv.org/pdf/2503.22912)
- Patents: a US patent learns employee attributes without supervision and classifies people by similarity to an employee model — [USPTO 8694443](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/8694443) (via search summary). A self-checkout patent classifies children / adult customers / staff and notes staff are often identified by uniforms with distinctive colours or logos — [USPTO 12699978](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12699978) (via search summary)

### Inferences
- The unsupervised "employee model" patent and the sports clustering work point to the same idea: the population of staff is small and recurring, while customers are many and transient. Recurrence over a day (the same appearance seen for hours, at many tables) is itself a strong staff signal that per-frame classifiers ignore.

### Gaps
- Could not find public docs for Vaidio's or Axis's staff exclusion internals in this pass.
- No commercial restaurant-specific product found that publicly documents waiter-vs-guest separation on CCTV.

---

## Q4. Downloadable datasets and pretrained models (with licenses)

### Takeaway
Pretrained encoders and ReID models are permissively available: PE-Core and SigLIP 2 are Apache-2.0, and the Roboflow sports code is MIT. Classic PAR datasets (PA-100K, PETA, RAP) are widely described as research-only, but I could not retrieve their official license text. RAP is explicitly non-commercial per a derivative's card. For a restaurant, the only directly relevant labelled data found is a Roboflow Universe "AI Smart Restaurant Surveillance" set with customer/waiter/staff classes (CC BY 4.0 per search summary), plus chef-hat sets. Easy FnB's own enrolment crops will likely beat all of them.

### Cited Findings
- **PE-Core** (B16-224, L14-336, G14-448) HF checkpoints are tagged **Apache-2.0**. A third-party aggregator said the GitHub repo README did not state a license (possibly outdated). — [HF PE-Core-L14-336](https://huggingface.co/facebook/PE-Core-L14-336); [HF pe_core_base_patch16_224_timm](https://huggingface.co/facebook/pe_core_base_patch16_224_timm/blob/main/README.md); [SourcePulse](https://www.sourcepulse.org/projects/2366364)
- **SigLIP 2** base-patch16-224 is **Apache-2.0**, ~0.4B params (paper arXiv 2502.14786, Feb 2025). — [HF google/siglip2-base-patch16-224](https://huggingface.co/google/siglip2-base-patch16-224)
- **OSNet** ReID weights come from the torchreid model zoo; the page shows a copyright line but no license text. — [torchreid MODEL_ZOO](https://kaiyangzhou.github.io/deep-person-reid/MODEL_ZOO)
- **BoxMOT** ReID weights (OSNet x0.25/x1.0, LightMBN, CLIP-ReID Market/MSMT/VehicleID) download automatically. — [PyPI boxmot](https://pypi.org/project/boxmot/10.0.54)
- **Roboflow sports** code is MIT. — [Roboflow sports (mirror)](https://github.meowingcats01.workers.dev/roboflow/sports/tree/main/examples/soccer) (via search summary)
- **PA-100K**: 100,000 surveillance images, 80k/10k/10k split, 26 binary attributes. No license text found. — [paperswithcode2 dataset page](https://paperswithcode2.com/dataset/211) (via search summary)
- **RAP**: a derivative dataset card (RAP-Instruct 260K) states RAP images are for **non-commercial research only** and the uploaders do not own the image rights. The derivative itself is CC BY-NC 4.0. — [HF Hoar012/RAP-260K README](https://www.huggingface.co/datasets/Hoar012/RAP-260K/blob/main/README.md?code=true)
- **UPAR** (harmonised PA100K + PETA + RAPv2 + Market-1501, plus MEVID in 2024) is on GitHub. — [UPAR Challenge 2024 paper](https://openaccess.thecvf.com/content/WACV2024W/RWS/html/Cormier_UPAR_Challenge_2024_Pedestrian_Attribute_Recognition_and_Attribute-Based_Person_Retrieval_WACVW_2024_paper.html) (repo: speckean/upar_challenge, via search summary)
- **MSP60K** (multi-scenario PAR, 2024) is used for the 2026 domain-shift benchmark. — [NeurIPS 2026](https://neurips.cc/virtual/2026/180070)
- **Restaurant**: Roboflow Universe "AI Smart Restaurant Surveillance" has ~3,000 images labelled customers, waiters, staff, food and menu cards, **CC BY 4.0** (per search summary; the page returned 403 to my fetch). — [Roboflow Universe](https://universe.roboflow.com/visionspace-adnsg/ai-smart-restaurant-surveillance-veh3i)
- **Kitchen**: Roboflow chef-hat datasets, e.g. a CC BY 4.0 set with chef-hat / no-hairnet classes. — [Roboflow chef-hat-detection](https://universe.roboflow.com/tp60/chef-hat-detection-fkc1l) (via search summary)
- **SH17** (manufacturing PPE: 8,099 images, 75,994 instances, 17 classes). The paper says it is open for commercial and research use, but arXiv metadata lists CC BY-NC-SA 4.0, so the license **conflicts** between sources. — [arXiv 2407.04590](https://arxiv.org/html/2407.04590v1); [fugumt metadata](https://fugumt.com/fugumt/paper_check/2407.04590v1_enmode)
- **SoccerNet-Tracking** (used for the role/team papers): 100 × 30 s clips at 25 fps. — [arXiv 2401.09942](https://arxiv.org/html/2401.09942v1)

### Inferences
- For a hackathon (non-commercial use is acceptable), any of these can be used. The highest-value data is still Easy FnB's own: ~50–200 crops per staff member from the demo restaurant's camera, plus random customer crops as negatives.
- The Roboflow restaurant set could pre-train a "waiter" vs "customer" detector head. Its camera angles and uniforms almost certainly differ from Vietnamese small restaurants, so expect domain shift (cf. UPAR 2024).

### Gaps
- Official license texts for PA-100K, PETA and RAP were not retrieved.
- The Roboflow restaurant dataset page could not be opened (403), so the class list, image count and license come from a search snippet only.
- The torchreid code license was not confirmed from the page fetched.

---

## Q5. Pitfalls (similar clothing, occlusion, top-down view, colour shifts, no-uniform staff, new staff, two-person crops)

### Takeaway
Failure modes are well documented by vendors. Customers dressing like staff, dark uniform colours collapsing to black, cues hidden by hair or collars or not visible from overhead, low-contrast cues (white lanyard on white shirt), uniform changes needing re-tuning, staff in personal clothing, and zones failing when staff walk among guests. The sports and PAR literature adds crop contamination by neighbours, rare-class imbalance and domain shift.

### Cited Findings
- **Similar customer clothing**: Milesight's FAQ says uniform-based methods may be less reliable when customers dress similarly. — [Milesight](https://www.milesight.com/iot/innovation/ai-people-counting/staff-exclusion)
- **Dark colours**: FootfallCam blacklists Midnight, Navy, Aubergine and Russet because they can look black on camera. Uniforms need a dominant colour covering ≥70%. — [FootfallCam Appendix A](https://footfallcam.com/people-counting/?p=3229)
- **Low-contrast cue**: "a white lanyard against a white shirt is harder for the model to lock onto than a coloured one". — [Aura Vision](https://www.auravisionlabs.com/knowledge/analytics/demographics/staff-segmentation)
- **Uniform change / out of uniform**: requires model re-tuning. — [Aura Vision](https://www.auravisionlabs.com/knowledge/analytics/demographics/staff-segmentation)
- **Occluded cue**: badges and lanyards must not be covered by collars, scarves or hair. Badge-like patterns on customer clothing cause confusion. The VA31 lanyard is not suited to reflective uniforms. Mounting height is restricted to 2.2–4 m. — [Milesight](https://www.milesight.com/iot/innovation/ai-people-counting/staff-exclusion)
- **Tag visibility / geometry**: V-Count tags must be "visible in full", with the sensor at 2.8–5 m. FootfallCam's patterned tag must be worn centrally on the upper chest, upright, not on a lanyard, and works better on plain shirts. — [V-Count](https://v-count.com/what-is-staff-exclusion-in-people-counting-and-how-it-works); [FootfallCam](https://footfallcam.com/people-counting/?p=3229)
- **Zones**: a staff-only exclusion line also removes genuine visitors who cross it, and staff must use their designated path. Fixed zones are "inaccurate if staff enter visitor areas". — [FootfallCam](https://footfallcam.com/people-counting/?p=3229); [Foorir](https://www.foorir.com/staff-exclusion-retail-traffic-analytics/) (via search summary)
- **Behaviour-only weakness**: a vendor says movement-pattern separation (repeated trips, fixed stopping points) works less well when staff wear personal clothing (search summary). — [XXII blog (visitor count)](https://xxiiai.com/en/le-blog/comment-exclure-le-personnel-du-comptage-des-visiteurs-en-magasin) (via search summary; not fetched)
- **ReID needs time / coverage**: FootfallCam Re-ID needs weeks of learning, and its benefit is limited in small stores. — [FootfallCam](https://footfallcam.com/people-counting/?p=3229)
- **Two people in one crop**: Roboflow crops only the central part of the box to reduce noise from opponents and crowd. — [Roboflow blog](https://roboflow.com/blog/identify-basketball-players)
- **Rare-class imbalance**: sports role classification reaches 94% accuracy but 74% precision. — [arXiv 2401.09942](https://arxiv.org/html/2401.09942v1)
- **Referees/officials contaminate clustering**: misclassified referees add noise. — [arXiv 2104.10068 (2021)](https://arxiv.org/html/2104.10068v2)
- **Domain shift**: VLM text-image alignment degrades under covariate shift. — [NeurIPS 2026](https://neurips.cc/virtual/2026/180070); UPAR 2024 retrieval track unbeaten — [CVF](https://openaccess.thecvf.com/content/WACV2024W/RWS/html/Cormier_UPAR_Challenge_2024_Pedestrian_Attribute_Recognition_and_Attribute-Based_Person_Retrieval_WACVW_2024_paper.html)
- **Face recognition on CCTV is weak** per the 2026 staff-monitoring preprint. Eocortex needs unmasked enrolment samples to identify masked staff. — [Zenodo 20758114](https://zenodo.org/records/20758114); [Eocortex](https://doc.eocortex.com/analytics/unique-visitors/overview.htm)
- **Privacy / labour law**: a search summary of CNIL-related guidance says employers may not use video to monitor staff work, and systems tracking employee activity require prior consultation with employee representatives. Staff exclusion framed as statistical filtering is easier to justify. — [XXII blog (visitor count)](https://xxiiai.com/en/le-blog/comment-exclure-le-personnel-du-comptage-des-visiteurs-en-magasin) (via search summary); [Veesion on in-store cameras and privacy](https://veesion.io/en/video-surveillance-cameras-in-stores-how-to-respect-the-privacy-of-customers-whilst-ensuring-their-security/) (via search summary)

### Inferences
- **Top-down/oblique view** hides chest logos and badges. That is why overhead-counter vendors moved to shoulder tags (V-Count, Milesight epaulets, FootfallCam fabric shoulder tag). For Easy FnB, the most camera-robust cheap cue is a **large, saturated, non-dark colour on the shoulders/torso or a cap**, e.g. a bright apron plus a coloured cap. This is a deployment recommendation to restaurant owners, not a model change.
- **Lighting colour shift** (warm restaurant lighting, evening vs daytime) is not addressed numerically by any source found. Per-shift enrolment naturally recalibrates to the current lighting.
- **New staff** is solved by per-shift enrolment, with no retraining of a global classifier: add their crops to the gallery.
- **A waiter's raised arm counted as a "call"**: the role decision should be made at the **track** level and be sticky, so a raised-arm event from a track that was ever confidently staff is suppressed. A seated pose (hip/knee keypoints from YOLO pose) is a strong customer prior.

### Gaps
- No quantitative study found on how much oblique ceiling viewpoints degrade uniform/PAR classification vs frontal views.
- No study found quantifying lighting colour shift effects on staff classification.

---

## Q6. Concrete application to Easy FnB, and effort before vs after 14 Nov 2026

### Takeaway
Before the demo, combine three cheap pieces, all built from things industry and sports already do. (1) **Per-shift enrolment gallery**: the Aura Vision / FootfallCam walk-test idea, matched with the CLIP/PE-Core embeddings already computed. (2) **Track-level, sticky fusion** with zone and behaviour priors (back-of-house entry, ≥3 tables visited within 2 min, standing vs seated). (3) **Central-crop + tracklet averaging** from sports. After the demo: collect site data and train a proper head, optionally add a lightweight ReID (OSNet x0.25), unsupervised "recurring identity" discovery, opt-in face enrolment, or BLE/UWB tags for chains.

### Cited Findings (patterns being borrowed)
- Per-store tuning with sample images of staff wearing the cue — [Aura Vision](https://www.auravisionlabs.com/knowledge/analytics/demographics/staff-segmentation)
- Walk test of 20 IN + 20 OUT for uniform enrolment — [FootfallCam](https://footfallcam.com/people-counting/?p=3229)
- ≥3 distinct tables within 2 min → waiter; 5 s dwell → seated customer; 2 s occlusion grace — [anuj1611 repo](https://github.com/anuj1611/ai-restaurant-cctv-monitoring)
- Staff-only zones and repeated short table visits → staff — [ChefSight](https://github.com/rubayetkabirzisan/ChefSight) (via search summary)
- Central-box crop for embeddings; SigLIP → UMAP(3) → KMeans(2); fit on 1 frame/s — [Roboflow](https://roboflow.com/blog/identify-basketball-players)
- Tracklet-level embedding aggregation before clustering — [SoccerNet GSR arXiv 2404.11335](https://arxiv.org/pdf/2404.11335)
- Extra cluster(s) for officials — [arXiv 2504.06357](https://arxiv.org/pdf/2504.06357)
- Lightweight ReID: OSNet x0_25 (0.2M params, 0.08 GFLOPs) — [torchreid](https://kaiyangzhou.github.io/deep-person-reid/MODEL_ZOO); exportable to TensorRT via BoxMOT — [BoxMOT](https://pypi.org/project/boxmot/10.0.54)
- Face-group exclusion with similarity threshold (opt-in alternative) — [Hikvision](https://enpinfo.hikvision.com/hkwsen/unzip/20230830144955_12918_doc/GUID-515292ED-4EFD-43FB-BDB5-3C872EE37360.html)
- Trajectory-only classifier reached 93% in a real supermarket — [arXiv 2005.08009](https://arxiv.org/abs/2005.08009)

### Inferences (proposed design — my synthesis, not from a source)
**Before 14 Nov (≈9 days, 2 people) — recommended scope**
1. **Shift enrolment (≈0.5–1 day)**: an "Enrol staff" button in the dashboard. Each staff member stands or walks in view for ~10–20 s, giving 30–100 crops per person from different angles. Store the L2-normalised PE-Core/CLIP embeddings, computed on a **central crop** (e.g. the middle 60% width, upper 70% height, to keep torso and apron while dropping neighbours). Optionally also store an average prototype per staff member.
2. **Scoring (≈0.5 day)**: per track, maintain an EMA of embeddings, the same ~6-frame cadence already in use. The staff score is the max cosine similarity to any staff gallery embedding (or kNN vote) minus the similarity to a small customer negative bank (random crops of seated guests from the same day). Keep the existing linear classifier as a second vote. A "few-shot linear probe retrained at enrolment" (seconds on CPU) is a natural upgrade.
3. **Behaviour/zone priors (≈1 day)**: add log-odds to the staff score when the track (a) first appeared at, or passes through, a kitchen/back-of-house/cashier polygon; (b) visits ≥3 distinct table polygons within 2 min; (c) is standing at a table for short bursts (<60 s) repeatedly. Subtract log-odds when the track is **seated** (hip/knee keypoints) for >5 s or entered through the front door without enrolment match.
4. **Sticky track decision (≈0.5 day)**: hysteresis, so staff status is entered at p>0.8 and left only at p<0.3 over many samples. When ByteTrack loses and re-creates an ID near the same position, re-match against recently-seen staff embeddings so status is inherited. Suppress "hand raise" events for staff tracks, and do not count staff toward table occupancy.
5. **Demo hygiene**: have the "staff" in the demo wear a saturated, non-dark apron or cap (FootfallCam/Milesight guidance). Show a confusion matrix on a held-out clip rather than claiming vendor-style 99%.
6. **Optional (≈0.5 day)**: an unsupervised sanity check in the sports style, running KMeans on tracklet-averaged embeddings of *standing* tracks only to see if staff form a tight cluster. Use it for a visual demo slide ("staff cluster"), not as the decision rule, because customers are not one cluster.
- Avoid before the demo: clothes-changing ReID, face recognition (privacy and consent overhead, weak on CCTV), training PAR models on PA-100K/RAP, VLM captioning per person (too slow on 4 GB for 10–30 people).

**After the hackathon**
- Collect a labelled dataset from 2–3 real restaurants (staff vs guest tracks) and train a proper head on frozen PE-Core/SigLIP 2 features, plus a temporal model over track features (embedding EMA, pose, zone sequence). Report per-restaurant precision and recall.
- Add OSNet x0.25 (TensorRT) as a cheap per-frame ReID for re-linking broken tracks. Keep the heavy ViT embedding for periodic role votes.
- **Recurring-identity discovery** (the patent / FootfallCam Re-ID idea): an appearance seen continuously for more than N hours, or at more than M tables per hour, is auto-proposed as staff and the owner confirms with one tap. This removes the need for enrolment in no-uniform shops.
- Opt-in face enrolment (Hikvision/Eocortex style) or BLE/UWB tags (RetailNext/Milesight style) for chains that want near-perfect exclusion, with explicit staff consent and a privacy notice. Vietnamese personal-data regulation was not researched here.
- Zero-shot VLM prompts ("waiter carrying a tray", "person wearing an apron") only as an auxiliary feature or for auto-labelling, given near-chance zero-shot results under domain shift (NeurIPS 2026).

### Gaps
- No source measures the end-to-end benefit of fusing appearance + behaviour for staff exclusion; the fusion weights above are untested design suggestions.
- Effort estimates are my judgement for a 2-person team, not sourced.
- Vietnamese legal requirements (e.g. personal data protection rules) for staff face enrolment were out of scope and not researched.
