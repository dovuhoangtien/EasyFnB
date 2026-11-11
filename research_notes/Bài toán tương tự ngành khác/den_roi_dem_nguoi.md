# Cross-industry analogues: arrival/departure in a zone, people counting, dwell time, queue analytics (for Easy FnB table events)

> Scope: how retail, airports, transit, smart buildings and video-analytics SDKs decide that a person "entered / left a zone", how they suppress flip-flopping and duplicate events, which multi-object tracker fits a 4 GB GPU in crowded/occluded indoor scenes, real-world accuracy of commercial counters (vendor claims vs independent), datasets/models with licenses, pitfalls, and what Easy FnB (YOLO26n-pose + ByteTrack, RTX 3050 4 GB, 12–22 fps, demo 14 Nov 2026) can borrow.
> Research date: 5 Nov 2026. Sources older than 2023 are labelled with their year.

## Q1. Best current methods for robust per-zone "arrival" / "departure" events (suppressing flip-flop and duplicate events)

### Takeaway
Every mature system separates (a) a noisy per-frame signal from (b) a debounced event layer with **asymmetric timers**: a short "probation" before confirming an arrival and a longer "grace/shadow" period before confirming a departure, with zone membership tested on a single anchor point (usually bottom-centre of the box; for seated people a hip keypoint is used instead). The closest analogue to Easy FnB (open-source restaurant monitors) uses a **per-table count-based state machine** (Empty/Occupied, 2 s to confirm occupied, 5 s to confirm empty) that does not depend on persistent person IDs at all — which directly removes the "ID switch → duplicate 'new guest'" failure mode.

### Cited Findings
**Restaurant-specific open source (closest analogues)**
- RestoMan-AI (YOLOv8-Pose + OpenCV): each table has two states, Empty/Occupied; a table flips to Occupied only after people are present for 2.0 s (`OCCUPIED_DEBOUNCE_SECONDS`), and back to Empty only after the zone stays empty for 5.0 s (`EMPTY_GRACE_SECONDS`); entry/exit time and visit duration are logged on those transitions; the stated goal is to stop flicker from e.g. a waiter walking through a zone — [RestoMan-AI GitHub](https://github.com/sahidirfan884/RestoMan-Ai)
- RestoMan-AI assigns a person to a table zone by the **midpoint of the hips**, counts only **seated** people (knee angle hip–knee–ankle < 140° = sitting, `SITTING_KNEE_ANGLE_THRESHOLD`), and falls back to a bounding-box aspect-ratio check when legs are hidden; it does **not** use a multi-object tracker with persistent IDs (the "tracker" is a per-table `TableTracker` class); staff re-ID is only listed as a future extension; no license is stated — [RestoMan-AI GitHub](https://github.com/sahidirfan884/RestoMan-Ai)
- ChronoDine (YOLOv11) reports per-table occupancy, dwell time and turnover from security cameras and filters out people who are standing or walking through a table zone to avoid false occupancy triggers — [chrono-dine GitHub](https://github.com/Mashood-Basharat/chrono-dine)
- ai-restaurant-cctv-monitoring uses YOLOv8 + ByteTrack, draws table zones as virtual fences, tests the person centroid with a ray-casting point-in-polygon test, and infers waiter visits per table — [ai-restaurant-cctv-monitoring GitHub](https://github.com/anuj1611/ai-restaurant-cctv-monitoring)

**Video-analytics SDK patterns (track birth / death hysteresis)**
- NVIDIA DeepStream NvDCF tracker: a new track starts in a *Tentative* mode for `probationAge` frames; if, during probation, the "shadow-tracking age" (frames without matched detection) reaches `earlyTerminationAge`, the track is killed (removes false positives); after confirmation, a track can coast without detections until `maxShadowTrackingAge`, which NVIDIA recommends raising to help re-association after missed detections; NVIDIA advises increasing probationAge and/or decreasing earlyTerminationAge when false detections are common — [NVIDIA NvMultiObjectTracker Parameter Tuning Guide](https://docs.nvidia.com/metropolis/deepstream-nvaie30/dev-guide/text/DS_plugin_NvMultiObjectTracker_parameter_tuning_guide.html)
- NVIDIA DeepStream nvdsanalytics provides ROI filtering, overcrowding (`object-threshold` count), direction detection and line crossing; ROI analytics work on raw detector output, but direction and line crossing **require a tracker ID** upstream — [NVIDIA nvdsanalytics docs](https://docs.nvidia.com/metropolis/deepstream/dev-guide/text/DS_plugin_gst-nvdsanalytics.html)
- nvdsanalytics ROI membership is decided by the bottom-centre point of each bounding box (reported in NVIDIA docs/forum answers); users have reported line crossings counted for objects far from the line, attributed to `mode`/line-placement settings — [NVIDIA nvdsanalytics docs](https://docs.nvidia.com/metropolis/deepstream/dev-guide/text/DS_plugin_gst-nvdsanalytics.html); [NVIDIA forum: false line crossings](https://forums.developer.nvidia.com/t/nvdsanalytics-sometimes-counts-line-crossing-that-haven-t-happened/166133)
- Ultralytics trackers expose `track_buffer` = number of frames a lost track is kept alive before removal ("higher value means more tolerance for occlusion") and `new_track_thresh` for track creation — [Ultralytics Track docs](https://docs.ultralytics.com/modes/track)

**Retail dwell-time pattern (Roboflow, Aug 2026)**
- Roboflow's dwell-time tutorial (published 4 Aug 2026) defines dwell as time from the frame a tracked ID enters a polygon to the frame it leaves; zone trigger anchor = `BOTTOM_CENTER`; "Reset Out of Zone Detections" resets a person's timer when they leave; tracker = ByteTrack with Minimum Consecutive Frames = 2 (a birth debounce), Lost Track Buffer = 60, Track Activation Threshold = 0.3, Min IoU 0.4; detector RF-DETR Small. The article does **not** discuss hysteresis, minimum dwell thresholds or ID-loss handling beyond tracker settings — [Roboflow blog: Dwell Time and Zone Analytics](https://roboflow.com/blog/dwell-time-and-zone-analytics)
- Roboflow Workflows "Time in Zone" block attaches `time_in_zone` (seconds) to each detection, supports multiple polygons (in zone if inside any), and requires tracking upstream — [Roboflow Time in Zone block docs](https://docs.roboflow.com/workflows/blocks/blocks/video-processing/timein-zone)
- Ultralytics `QueueManager` keeps each track's position history and counts a track as in the queue when its latest point falls inside the region polygon (no built-in hysteresis described) — [Ultralytics queue_management reference](https://docs.ultralytics.com/reference/solutions/queue_management)

**Airport queue pattern ("in the queue" vs "passing by")**
- Xovis states its automated queue detection counts only passengers actually standing in a given queue and excludes passers-by when measuring waiting and process times; it reports queue length, actual and predictive waiting time and throughput per queue, and can measure total waiting time or only waiting after check-in starts (vendor press material) — [airport-suppliers.com Xovis release](https://www.airport-suppliers.com/supplier-press-release/passenger-tracking-systems-passenger-counting-systems-waiting-time-measurements-11)
- Xovis announced the ability to measure waiting in "unstructured" (non-roped) situations (vendor news) — [startupticker.ch](https://startupticker.ch/en/news/xovis-can-now-measure-waiting-of-passengers-in-unstructured-situations)
- Philadelphia airport's queue system measures "passenger dwell time" with a fusion of sensors placed from the start of the queue to the end of screening — [PhillyVoice](https://www.phillyvoice.com/phl-tsa-security-line-wait-time-philadelphia-international/)
- San Antonio (2015): cameras at security entrance and exit points estimate the wait for the last person in line (entry/exit time-stamping rather than continuous tracking) — [AviationPros (2015)](https://www.aviationpros.com/airport-business/airport-infrastructure-operations/airports-municipalities/press-release/12062104/video-based-queue-measurement-system-approved-for-sat)
- Academic airport study (2017): counting at a queue exit had ~4% error, but counts alone did not reveal queue state, and ground truth (boarding-pass scans at entry) did not map cleanly to exit counts — [arXiv 1705.00027 (2017)](https://arxiv.org/pdf/1705.00027)

**"Party" / group arrival**
- Zone-based clustering of detected pedestrian coordinates to form groups was evaluated on MOT17 (IEEE Access, Jan 2024) — [DOAJ: IEEE Access 2024](https://doaj.org/article/9a471ae8ac1d40d18b344953f99aa0f3)
- Moving-flock (group) detection with RNN/LSTM/Transformer pair classifiers applied over trajectories; notes that density-based clustering struggles when group sizes and motion change over time (arXiv Feb 2025, v2 Aug 2025) — [arXiv 2502.15252](https://arxiv.org/pdf/2502.15252v2)
- A 2024 Charles University thesis reports a sociologically-informed group-detection algorithm comparable to Time-sequence DBSCAN and agglomerative clustering with Hausdorff distance on the DIAMOR dataset — [Charles University thesis 2024](https://dspace.cuni.cz/handle/20.500.11956/188480)
- In retail door counting, "groups" are inferred from spacing, path and heading — a heuristic; SMS Storetraffic publishes no group accuracy figure because group boundaries cannot be audited (vendor article) — [storetraffic.com accuracy article](https://storetraffic.com/people-counter-accuracy/)

### Inferences
- The common recipe across RestoMan, NvDCF, Roboflow and Xovis is: **(1) membership on one robust anchor point → (2) per-zone presence signal → (3) asymmetric debounce (short confirm-arrival, long confirm-departure) → (4) emit events only on state transitions.** Easy FnB's current "1-second window, ≥0.8 / ≤0.2" is a symmetric, very short hysteresis band; at 12–22 fps a 1 s window is only 12–22 samples, so a brief occlusion or ID switch easily crosses both thresholds. That explains the repeated "new guest" events.
- Duplicate "new guest" events disappear if events are keyed to a **table session** (one session per Empty→Occupied transition) instead of to track IDs, and if, while a table is OCCUPIED, count changes only produce a separate "party size changed" update after a sustained change (not a new arrival event). This is my design inference from the RestoMan count-based model plus the NvDCF probation/shadow concept.
- Restaurant departures need a much longer grace than RestoMan's 5 s (guests go to the restroom, lean back out of the polygon, get occluded by staff). A practical range is 20–60 s for "guest left" plus a separate "needs clearing" state; this is an inference, not a measured value — should be tuned on Easy FnB's own footage.
- For an oblique ceiling camera, bbox bottom-centre (Roboflow/nvdsanalytics default) is a poor anchor for seated diners because the table hides legs and feet; the hip-midpoint keypoint (RestoMan) is the better anchor, with shoulder midpoint as fallback when hips are occluded.
- The airport "queue vs passer-by" logic is the same problem as "guest seated vs staff standing at table": both are solved by requiring a *behavioural* condition (standing in line / seated) plus a minimum dwell, not mere polygon overlap.

### Gaps
- I found no peer-reviewed paper (2023–2026) that specifically evaluates hysteresis/debounce parameters for zone entry/exit events; the evidence is from SDK docs, vendor material and open-source code.
- The Sciforce/Medium restaurant case study (≈1,200-location chain flagging "sat down / left" events) could not be fetched (fetch failed); only its search snippet was seen — [Medium/Sciforce](https://medium.com/sciforce/optimizing-multi-zone-restaurant-service-with-computer-vision-for-hospitality-3316f009ec5b). Its thresholds and accuracy are unknown.
- No source found for how Xovis technically excludes passers-by (dwell threshold? velocity?) — only the marketing statement.

## Q2. Which tracker gives the best accuracy/speed trade-off on a 4 GB GPU in crowded, occluded indoor scenes? Is ReID worth it?

### Takeaway
On independent-harness numbers (BoxMOT, same detector/eval for all trackers), appearance-aware trackers beat ByteTrack mainly on identity (IDF1): BoT-SORT 82.3 vs ByteTrack 79.2 IDF1 on MOT17-ablation, and the new OccluBoost (BoostTrack + OccluTrack-style occlusion-aware Kalman) reaches 85.3 IDF1 / 71.1 HOTA. Learned/end-to-end trackers (MOTIP, CAMELTrack) lead DanceTrack but run at ~13 FPS with large detectors and are not realistic on an RTX 3050 alongside pose. For Easy FnB the cheapest real upgrade is inside Ultralytics itself: current Ultralytics ships TrackTrack (CVPR 2025, now the default), BoT-SORT, OC-SORT, Deep OC-SORT and FastTracker, plus `with_reid: True, model: auto` that reuses YOLO detector features for ReID at "minimal overhead".

### Cited Findings
**Independent-harness comparison (BoxMOT, AGPL-3.0)**
- BoxMOT README benchmark (Python scores; MOT17 ablation split HOTA / MOTA / IDF1): OccluBoost 71.10 / 78.50 / 85.28; BoT-SORT 69.68 / 78.23 / 82.33; BoostTrack 69.25 / 75.91 / 83.20; StrongSORT 68.05 / 76.19 / 80.76; Deep OC-SORT 67.95 / 75.83 / 80.54; ByteTrack 67.68 / 78.04 / 79.16; Hybrid-SORT 67.31 / 74.09 / 78.87; OC-SORT 66.44 / 74.55 / 77.90; SFSORT 62.65 / 76.87 / 69.18. SportsMOT val HOTA: OccluBoost 83.17, Hybrid-SORT 81.14, StrongSORT 79.80, Deep OC-SORT 79.51, BoT-SORT 76.93, ByteTrack 67.93. License AGPL-3.0. FPS and hardware are not stated on the current README — [BoxMOT GitHub](https://github.com/mikel-brostrom/boxmot)
- An earlier BoxMOT release table (v17.0.0) listed BoT-SORT ≈69.4 HOTA at 12 FPS and BoostTrack ≈69.3 HOTA at 13 FPS (appearance-based, full pipeline), and a variant table listed ByteTrack (67.7 HOTA) and OC-SORT (66.4 HOTA) at >1,000 FPS — i.e., motion-only association cost is negligible vs. the detector; FPS numbers differ by version/config — [BoxMOT on PyPI 17.0.0](https://pypi.org/project/boxmot/17.0.0/)
- OccluBoost = BoostTrack + OccluTrack-style Abnormal Motion Suppression Kalman filter that protects tracks during partial occlusion; docs report MOT17-ablation HOTA 70.47 / MOTA 78.32 / IDF1 84.14 vs BoT-SORT HOTA 69.44; **requires a ReID model**; ships a native C++17 backend (`--tracker-backend cpp`); AMS settings were tuned on MOT17-ablation and should be retuned per dataset; tracks shorter than 15 frames gain nothing — [BoxMOT OccluBoost docs](https://mikel-brostrom.github.io/boxmot/trackers/occluboost/); underlying idea: [OccluTrack, arXiv 2309.10360 (2023)](https://arxiv.org/abs/2309.10360)

**Ultralytics built-in trackers (what Easy FnB already uses)**
- Ultralytics track mode now includes BoT-SORT, ByteTrack, OC-SORT, Deep OC-SORT, FastTracker and TrackTrack; the docs say `tracktrack.yaml` is used when no tracker is passed (i.e., default) — [Ultralytics Track docs](https://docs.ultralytics.com/modes/track); an Ultralytics Academy lesson also says TrackTrack is default, while older doc text said BoT-SORT — [Ultralytics Academy](https://academy.ultralytics.com/courses/yolo-in-production/tracking-with-bytetrack-and-botsort)
- ReID is off by default "to minimize overhead"; `with_reid: True` enables it (supported by BoT-SORT, Deep OC-SORT, TrackTrack); `model: auto` uses native YOLO detector features with "minimal overhead", falling back to `yolo26n-cls.pt`; dedicated ONNX ReID encoders exist: YOLO26n-reid 2.8 M params / 2.0 GFLOPs, YOLO26s-reid 7.5 M / 6.6 GFLOPs (448 px input); ReID train/val/predict modes are still under development — [Ultralytics Track docs](https://docs.ultralytics.com/modes/track)

**TrackTrack (CVPR 2025, MIT license)**
- "Focusing on Tracks for Online Multi-Object Tracking" (Shim et al., KAIST, CVPR 2025): Track-Perspective-Based Association (prioritises local matching precision; joint + single-stage association) and Track-Aware Initialization (does not start new tracks from detections that heavily overlap active tracks or more confident detections — directly targets duplicate IDs in crowds); slides motivate it by "occlusion can make detector miss objects and cause ID changes" — [CVPR 2025 slides](https://cvpr.thecvf.com/media/cvpr-2025/Slides/35174.pdf); [mlanthology](https://mlanthology.org/cvpr/2025/shim2025cvpr-focusing)
- Official code: YOLOX detector + FastReID, MIT license — [TrackTrack GitHub](https://github.com/kamkyu94/TrackTrack)
- Mirror leaderboards list TrackTrack at 65.7 HOTA (MOT20) and 67.1 HOTA (board likely MOT17), both "with extra data" — **unverified against the paper** — [paperswithcode2 board 50152](https://paperswithcode2.com/benchmark/50152); [paperswithcode2 board 50143](https://paperswithcode2.com/benchmark/50143)

**Learned / end-to-end trackers (2024–2025) — numbers as reported by CAMELTrack paper**
- DanceTrack test HOTA / AssA / IDF1: ByteTrack 47.7/32.1/53.9; OC-SORT 55.1/38.0/54.2; Deep OC-SORT 61.3/45.2/61.5; DiffMOT 62.3/48.8/64.0; Hybrid-SORT 65.7/–/67.4; CAMELTrack 66.1/54.0/71.1; MOTIP 67.5/57.6/72.2; CAMELTrack + keypoints 69.3/58.9/74.9 — [CAMELTrack arXiv 2505.01257](https://arxiv.org/html/2505.01257v1)
- MOT17 test (online only) HOTA/IDF1: ByteTrack 62.8/77.1; OC-SORT 61.7/76.2; MOTRv2 62.0/75.0; CAMELTrack 62.4/76.5 — i.e., on pedestrian MOT17 the learned tracker does **not** beat ByteTrack — [CAMELTrack arXiv 2505.01257](https://arxiv.org/html/2505.01257v1)
- Speed: CAMELTrack ≈13 FPS on MOT17 (YOLOX-x 24.4 ms + RTMPose 16.8 ms + BPBReID 16 ms + CAMEL 18 ms per frame); in the same table ByteTrack 30 FPS, OC-SORT 28 FPS, MOTRv2 6.9 FPS, MOTR 7.5 FPS; inference GPU not named; code/weights released (TrackingLaboratory/CAMELTrack) — [CAMELTrack arXiv 2505.01257](https://arxiv.org/html/2505.01257v1)
- CAMELTrack's keypoint cue helps on DanceTrack but hurts on SportsMOT (noisy pose from distant views); its numbers are listed as "claimed, not independently verified" — [CAMELTrack arXiv](https://arxiv.org/html/2505.01257v1); [SOTAVerified](https://sotaverified.org/papers/cameltrack-context-aware-multi-cue-1)
- MOTIP (CVPR 2025) treats association as in-context ID prediction (end-to-end); DanceTrack HOTA reported 67.5–70.0 depending on DETR variant and version (69.6 in arXiv v2, no extra data); SportsMOT 71.9–72.6; no FPS found — [CVF open access](https://openaccess.thecvf.com/content/CVPR2025/html/Gao_Multiple_Object_Tracking_as_ID_Prediction_CVPR_2025_paper.html); [arXiv 2403.16848v2](https://arxiv.org/abs/2403.16848v2)
- DanceTrack (2022) was built because association, not detection, is the bottleneck when people look alike and move non-linearly — analogous to similarly-dressed staff — [DanceTrack arXiv (2021/2022)](https://arxiv.org/pdf/2111.14690)

### Inferences
- **Recommendation for ≤14 Nov:** stay tracking-by-detection with YOLO26n-pose; switch `tracker=` from `bytetrack.yaml` to `tracktrack.yaml` or `botsort.yaml` with `with_reid: True, model: auto`, and raise `track_buffer` to ~3–5 s worth of frames (≈60–100 at 20 fps). This is a config change, so the risk is low; the gain expected from BoxMOT is +3 IDF1 points (BoT-SORT vs ByteTrack) — modest. OccluBoost (+6 IDF1) needs BoxMOT integration and a separate ReID network — more GPU and integration work; better post-hackathon.
- ReID is "worth it" mainly for **identity-dependent** features (who raised a hand, keeping staff labelled as staff across occlusion, per-person dwell). For **table arrival/departure**, a count-based per-table state machine (Q1) makes the system largely insensitive to ID switches, so ReID is not the first fix.
- End-to-end trackers (MOTIP, SambaMOTR, MOTRv2) and CAMELTrack are not a fit for an RTX 3050 4 GB running pose at 12–22 fps: CAMELTrack's own pipeline is ~13 FPS with YOLOX-x on an unspecified (likely larger) GPU, and MOTR-family runs ~7 FPS in the same table.
- Benchmarks are on street/dance/sports video; none is "ceiling CCTV of seated diners". Seated diners move very little, so motion-model trackers should work better than on MOT17 except during occlusion by staff walking between camera and table — exactly the case where TrackTrack's Track-Aware Initialization (no new track from a box overlapping an existing track) and longer `track_buffer` help.
- Because frame rate varies 12–22 fps, express all buffers and debounce timers in **seconds** (convert using measured fps), otherwise behaviour changes with load.

### Gaps
- No verified primary numbers for TrackTrack (paper results are in images on the slides; mirror leaderboard values unverified).
- No FPS measurements for any of these trackers on an RTX 3050 4 GB; no source gives Ultralytics `model: auto` ReID overhead in ms. Must be measured locally.
- SambaMOTR, SMILEtrack, Hybrid-SORT speed, and DiffMOT speed were not verified in this research (DiffMOT and Hybrid-SORT accuracy appears only via CAMELTrack's tables and BoxMOT).
- FastTracker (in Ultralytics) — no details collected.
- No head/top-view tracking benchmark comparison collected beyond CroHD (Q5).

## Q3. Real-world accuracy of commercial people counters and dwell/occupancy analytics (vendor claims vs independent audits)

### Takeaway
Almost all published accuracy figures are vendor claims (typically 95–99%), measured by the vendor's own audit rules, often at single doorways. I found no public, independent head-to-head audit. The few semi-independent data points show large site-to-site variance (a same-type overhead 3D counter undercounting 11.7–19.2% at one store) and that "accuracy" depends on definition (net vs absolute). Group, child and occlusion accuracy is generally not published.

### Cited Findings
- Indivd (vendor) distinguishes **net** accuracy (in/out errors can cancel, hiding miscounts) from **absolute** accuracy (errors don't cancel) and lists six questions to ask vendors (what/how much/where measured, ground truth, who ran the test, evidence retention); recommends manual person-by-person review of recorded footage in quiet and peak periods and re-verification after camera moves, lighting or fixture changes — [Indivd: people counting accuracy](https://www.indivd.com/insights/people-counting-accuracy-testing-vendor-claims)
- Indivd reports a home-improvement benchmark where four stores used the same overhead 3D counter type: one store undercounted daily by 11.7%–19.2%, another drifted from a 4.4% overcount to a 14.8% undercount (data reported by a competitor vendor) — [Indivd](https://www.indivd.com/insights/people-counting-accuracy-testing-vendor-claims)
- Indivd's own QA: min absolute accuracy 97.78% over 3,101 visitors, 54 h, 10 counting lines, 5 cameras (fashion store); ~99% absolute accuracy in a customer-commissioned review executed by KPMG — but KPMG applied Indivd's QA method, so "independent in execution, not methodology" — [Indivd](https://www.indivd.com/insights/people-counting-accuracy-testing-vendor-claims)
- SMS Storetraffic (vendor, Sept 2026): "98% accurate" = the vendor's count checked against the vendor's own rules on a sample of audited footage; their 3D stereo counter: 99%+ best, 98% typical, 95% floor guaranteed for 2 years; IR beam 95–98% for single-file adults; overhead thermal door counters 85–95% (citing an unnamed thermal vendor); no third-party test results are presented; groups and children accuracy not published — [storetraffic.com](https://storetraffic.com/people-counter-accuracy/)
- Storetraffic's balance check 1 − |IN − OUT| / (IN + OUT) can miss errors that occur equally on entry and exit — [storetraffic.com](https://storetraffic.com/people-counter-accuracy/); [storetraffic accuracy calculator](https://help.storetraffic.com/accuracy-calculator)
- RetailNext advertises 95–99% accurate counting, manually audited at every installation (vendor claim) — [RetailNext blog](https://retailnext.net/blog/how-accurate-is-your-people-counter)
- Buyer roundups state published vendor claims cluster around 95–99.96% and that accuracy figures are vendors' own statements not tested independently (roundups are themselves written by vendors) — [storetraffic best people counters](https://storetraffic.com/best-people-counters/); [getdor comparison](https://www.getdor.com/compare/best-people-counters)
- Axis does not publish an overall accuracy number ("would be correct only in a laboratory test setup"); the AXIS People Counter app's built-in "Test accuracy" should give ≥95% under normal circumstances, otherwise fine-tune; Axis recommends its 3D P8815-2 for crowded scenes and difficult light; the app also has a "naive occupancy mode" = in − out — [Axis whitepaper](https://whitepapers.axis.com/ko/axis-people-counting-technologies); [AXIS People Counter manual](https://www.manualslib.com/manual/2357351/Axis-P8815-2.html?page=18)
- Xovis: vendor material cites a "sample rate" up to 98% (share of passengers registered in the covered area) and separation of people 7 in. apart; JFK AirTrain deployment reported >98% accuracy "in all situations" in a press-release-style article; Xovis' CEO argues LiDAR misses counts in queues due to occlusion (vendor argument) — [AviationPros Xovis PTS](https://www.aviationpros.com/home/product/12392627/xovis-ag-xovis-pts); [startupticker JFK/Vienna](https://www.startupticker.ch/en/news/xovis-sensors-will-measure-passenger-flow-in-vienna-and-new-york); [International Airport Review](https://www.internationalairportreview.com/why-xovis-doesnt-use-lidar/539071.article)
- Density (occupancy sensors) argues a single headline "99%" is misleading and uses "Time Within Tolerance" for Open Area sensors; claims to be "the only provider that validates its platform's accuracy" (vendor claim); sensor needs clear line of sight and correct rotation for validation; one sensor covers >1,325 sq ft mounted up to 20 ft — [Density: truth behind 99% accurate](https://density.io/resources/the-truth-behind-99-accurate-occupancy-sensors); [Density product overview PDF](https://www.solutionzinc.com/hubfs/603ee8372ec54a47d690d734_density-product-overview.pdf)
- Crowd-monitoring validation is hard because ground truth is hard to establish (ESGI study group report) — [ESGI CrowdVision report](https://miis.maths.ox.ac.uk/755/1/esgi-crowdvision-draft-v1.pdf)
- Restaurant vendors: NWarch AI claims a 15% increase in table turnover (marketing, unverified); FlowLinks claims it detects when guests leave and starts the turnover clock on existing cameras; a web-studio case study describes four overhead cameras + on-prem edge device classifying tables as empty/occupied/in service/clearing, updating every 30 s, no accuracy figure — [NWarch AI](https://datenwissen.com/nwarch-ai/occupancy-monitoring/); [FlowLinks](https://www.flowlinks.ai/restaurants-cafes/table-turnover); [webdesignstudio case study](https://webdesignstudio.london/case-studies/real-time-table-intelligence)

### Inferences
- Even dedicated overhead 3D sensors at controlled doorways are sold on a ~95% floor; Easy FnB uses an oblique, crowded, occluded CCTV view — a much harder setting — so the judges' realistic expectation should be event-level precision/recall, not "99%". Reporting **absolute** (not net) event accuracy against a hand-labelled clip would make the demo more credible than any vendor-style claim.
- Density's "time within tolerance" is a good model for Easy FnB's metric: e.g., "% of arrivals detected within ±15 s of ground truth" and "% of time the table state is correct".
- The restaurant-specific vendor that updates table state only every 30 s suggests commercial table analytics accept coarse latency in exchange for stability — Easy FnB can likewise trade a few seconds of latency for no flip-flops.

### Gaps
- No public independent (third-party-designed) audit of Xovis, Axis, Hikvision, Sensormatic/ShopperTrak, RetailNext or Density was found.
- No accuracy data found for Hikvision or Sensormatic/ShopperTrak counters (not searched in depth due to budget).
- No published accuracy for any restaurant table-occupancy product.
- The Budapest airport video queue system reportedly reached 96% accuracy on waiting time in a 3-week field test, but I could not pin the original source page — treat as unverified.

## Q4. Commercial products, open-source projects and key papers (who uses what)

### Takeaway
Commercial counting/queue analytics lean on dedicated overhead (often 3D stereo) sensors with on-device processing (Xovis, Axis P8815-2, Storetraffic 3D), whereas software stacks for existing CCTV (Roboflow Workflows/supervision, Ultralytics Solutions, NVIDIA DeepStream nvdsanalytics, BoxMOT) provide zone/line primitives but leave hysteresis and session logic to the integrator. Restaurant-table open-source projects already combine pose-based "seated" checks with zone debounce.

### Cited Findings
- **Xovis** (airports: e.g., JFK AirTrain, Toronto Pearson, Milan Bergamo, Vienna): ceiling-mounted 3D sensors; no video leaves the sensor; software reports queue length, waiting time, throughput, predictive waiting; PT3/PC3 for halls up to 20 m ceiling — [startupticker](https://www.startupticker.ch/en/news/xovis-sensors-will-measure-passenger-flow-in-vienna-and-new-york); [State Aviation Journal: Toronto Pearson](https://stateaviationjournal.com/index.php/international-news/toronto-pearson-airport-features-xovis-3d-sensors-and-software-to-reduce-queue-wait-times); [AviationPros: Milan Bergamo](https://www.aviationpros.com/airport-business/airport-infrastructure-operations/press-release/12297874/xovis-ag-milan-bergamo-airport-counts-on-xovis-to-optimize-passenger-flow); [airport-suppliers.com](https://www.airport-suppliers.com/supplier-press-release/passenger-tracking-systems-passenger-counting-systems-waiting-time-measurements-11)
- **Axis**: 2D People Counter app (≥95% target in its own accuracy test) and 3D P8815-2 for crowded/difficult light — [Axis whitepaper](https://whitepapers.axis.com/ko/axis-people-counting-technologies)
- **Density**: Open Area occupancy sensors, "Time Within Tolerance" metric — [Density](https://density.io/resources/the-truth-behind-99-accurate-occupancy-sensors)
- **SMS Storetraffic**: excludes staff with worn UWB tags (excluded without identifying the wearer); notes staff exclusion matters mainly at low traffic with extreme staff:visitor ratios — [storetraffic.com](https://storetraffic.com/people-counter-accuracy/)
- **Roboflow** (RF-DETR + ByteTrack + Time in Zone block), Aug 2026 tutorial — [Roboflow blog](https://roboflow.com/blog/dwell-time-and-zone-analytics)
- **Ultralytics Solutions**: QueueManager (region polygon count) — [Ultralytics docs](https://docs.ultralytics.com/reference/solutions/queue_management); trackers incl. TrackTrack, ReID encoders — [Ultralytics Track docs](https://docs.ultralytics.com/modes/track)
- **NVIDIA DeepStream** nvdsanalytics (ROI, overcrowding, direction, line crossing) + NvDCF tracker with probation/shadow-tracking — [nvdsanalytics docs](https://docs.nvidia.com/metropolis/deepstream/dev-guide/text/DS_plugin_gst-nvdsanalytics.html); [NvDCF tuning guide](https://docs.nvidia.com/metropolis/deepstream-nvaie30/dev-guide/text/DS_plugin_NvMultiObjectTracker_parameter_tuning_guide.html)
- **BoxMOT** (AGPL-3.0): pluggable trackers incl. OccluBoost, BoT-SORT, BoostTrack, StrongSORT, Deep OC-SORT, ByteTrack, Hybrid-SORT, OC-SORT, SFSORT; works with detection, segmentation and pose models — [BoxMOT GitHub](https://github.com/mikel-brostrom/boxmot)
- **Restaurant OSS**: RestoMan-AI, ChronoDine, ai-restaurant-cctv-monitoring (see Q1) — [RestoMan-AI](https://github.com/sahidirfan884/RestoMan-Ai); [chrono-dine](https://github.com/Mashood-Basharat/chrono-dine); [ai-restaurant-cctv-monitoring](https://github.com/anuj1611/ai-restaurant-cctv-monitoring)
- **Key papers**: TrackTrack (CVPR 2025) — [mlanthology](https://mlanthology.org/cvpr/2025/shim2025cvpr-focusing); CAMELTrack (2025) — [arXiv 2505.01257](https://arxiv.org/html/2505.01257v1); MOTIP (CVPR 2025) — [CVF](https://openaccess.thecvf.com/content/CVPR2025/html/Gao_Multiple_Object_Tracking_as_ID_Prediction_CVPR_2025_paper.html); OccluTrack (2023) — [arXiv 2309.10360](https://arxiv.org/abs/2309.10360); CroHD head tracking (CVPR 2021) — [arXiv 2103.13516](https://arxiv.org/abs/2103.13516)

### Inferences
- The "Xovis approach" (top-down 3D sensor, on-device, track-based queue membership) is what Easy FnB would ideally emulate, but with existing oblique CCTV the practical substitute is pose-based behaviour filtering (seated vs standing) + debounced zone logic.
- Of the software stacks, Ultralytics is already Easy FnB's stack; Roboflow supervision/Workflows and DeepStream add nothing essential for a 9-day hackathon beyond patterns worth copying.

### Gaps
- Hikvision, Sensormatic/ShopperTrak product mechanics were not researched in detail (budget).
- No details on Roboflow `supervision` library's own `PolygonZone` triggering options were collected (only the Workflows block).

## Q5. Downloadable datasets and models (with licenses) — head / top-view / crowded

### Takeaway
Head-level data is the standard remedy for crowded, occluded scenes (heads stay visible when bodies don't). SCUT-HEAD (academic-only) includes classroom CCTV — the closest indoor, oblique, seated analogue; CrowdHuman (non-commercial research) adds full/visible/head boxes for crowds; CroHD is the head-tracking benchmark. All are fine for non-commercial hackathon use.

### Cited Findings
- **SCUT-HEAD**: Part A = 2,000 images from **classroom monitoring videos** (67,321 heads); Part B = 2,405 web images (43,930 heads); free for academic research use only — [V7 Labs SCUT-HEAD page](https://www.v7labs.com/open-datasets/scut-head); [Dataset Ninja](https://datasetninja.com/scut-head)
- **CrowdHuman**: ~24k images, 1–391 heads per frame, ~339,566 head annotations — [RPEE-HEADS paper (2024)](https://arxiv.org/pdf/2411.18164); download terms: non-commercial research and educational use only, no redistribution; Hugging Face mirrors tag CC BY-NC 4.0; some Roboflow re-uploads mislabel as CC BY 4.0 — [CrowdHuman on Hugging Face](https://huggingface.co/datasets/ShantyCam/crowdhuman); [CrowdHuman paper (2018)](https://arxiv.org/pdf/1805.00123)
- **CroHD** (CVPR 2021): 9 sequences, 11,463 frames, head boxes for tracking, ~178 heads/frame, >2 M heads; train stations/streets (not indoor dining) — [arXiv 2103.13516 (2021)](https://arxiv.org/abs/2103.13516); [RPEE-HEADS (2024)](https://arxiv.org/pdf/2411.18164)
- **RPEE-HEADS** (Nov 2024): new benchmark for pedestrian head detection in crowd videos — [arXiv 2411.18164](https://arxiv.org/pdf/2411.18164)
- **Tracking benchmarks**: MOT17/MOT20 (MOT20 = highly crowded scenes), DanceTrack (100 group-dance videos, similar appearance) — [TrackTrack CVPR 2025 slides](https://cvpr.thecvf.com/media/cvpr-2025/Slides/35174.pdf); [DanceTrack arXiv](https://arxiv.org/pdf/2111.14690)
- **Models**: Ultralytics YOLO26n/s ReID ONNX encoders (2.8 M / 7.5 M params) — [Ultralytics Track docs](https://docs.ultralytics.com/modes/track); TrackTrack code (MIT) — [GitHub](https://github.com/kamkyu94/TrackTrack); CAMELTrack code + weights — [arXiv 2505.01257](https://arxiv.org/html/2505.01257v1); BoxMOT (AGPL-3.0) — [GitHub](https://github.com/mikel-brostrom/boxmot)

### Inferences
- SCUT-HEAD Part A (classroom CCTV: seated people, oblique ceiling view, many occluded bodies) is the best public proxy for a restaurant dining room; a head detector/fine-tune on it is the natural "older approach from another field + new component" swap (e.g., YOLO26n fine-tuned on SCUT-HEAD + CrowdHuman heads), useful as a **second counting signal** per table when pose fails under occlusion. This is post-hackathon effort (training + integration), not for 14 Nov.
- License-wise, all three are acceptable for a non-commercial hackathon but would block commercial deployment without re-collection.

### Gaps
- No dedicated public dataset of restaurant dining rooms with table-occupancy or arrival/departure labels was found.
- No top-view (ceiling, vertical) dataset was verified in this research (e.g., top-view person datasets) — budget exhausted; CroHD license terms not confirmed.

## Q6. Pitfalls reported across industries (occlusion, ID switches, near-but-not-in-zone, staff, groups, camera angle)

### Takeaway
The recurring failure modes are: anchor-point choice (bottom-centre box point misplaces seated/occluded people), short tracks/ID switches creating phantom entries, passers-by and staff counted as zone occupants, groups merged or split, and camera placement/lighting changes silently degrading accuracy. Each industry fixes these with behavioural filters (standing-in-queue / seated), dwell minimums, longer track survival, and periodic re-audits.

### Cited Findings
- Occlusion makes detectors miss objects and causes ID changes — "critical factor" for MOT degradation (TrackTrack authors) — [CVPR 2025 slides](https://cvpr.thecvf.com/media/cvpr-2025/Slides/35174.pdf)
- Mounting height, angle, placement, entrance width, backlight, lighting and dense group traffic change accuracy; same technology can perform differently at different entrances; re-verify after camera moves/refocus/new fixtures — [Indivd](https://www.indivd.com/insights/people-counting-accuracy-testing-vendor-claims)
- Groups are inferred heuristically (spacing/path/heading) and are not auditable; children <130 cm classified with ±5% height error; staff using an uncounted back door cause IN/OUT imbalance — [storetraffic.com](https://storetraffic.com/people-counter-accuracy/)
- Passers-by must be excluded from queue waiting time (Xovis queue detection) — [airport-suppliers.com](https://www.airport-suppliers.com/supplier-press-release/passenger-tracking-systems-passenger-counting-systems-waiting-time-measurements-11)
- Standing/walking people inside a table zone are filtered out to avoid false occupancy (ChronoDine); waiters walking through a zone cause flicker unless debounced (RestoMan) — [chrono-dine](https://github.com/Mashood-Basharat/chrono-dine); [RestoMan-AI](https://github.com/sahidirfan884/RestoMan-Ai)
- Seated staff would be counted as customers in a seated-only filter (RestoMan has no staff ID) — [RestoMan-AI](https://github.com/sahidirfan884/RestoMan-Ai)
- Line-crossing false counts for objects far from the line (DeepStream users) — [NVIDIA forum](https://forums.developer.nvidia.com/t/nvdsanalytics-sometimes-counts-line-crossing-that-haven-t-happened/166133)
- Pose keypoints help association on DanceTrack but hurt on SportsMOT due to noisy pose from distant views — relevant to a far, oblique CCTV — [CAMELTrack arXiv](https://arxiv.org/html/2505.01257v1)
- OccluBoost's occlusion handling gives no gain for tracks shorter than 15 frames and its parameters need per-dataset retuning — [BoxMOT OccluBoost docs](https://mikel-brostrom.github.io/boxmot/trackers/occluboost/)
- Density sensors need clear line of sight and correct rotation for data validation — [Density product overview](https://www.solutionzinc.com/hubfs/603ee8372ec54a47d690d734_density-product-overview.pdf)
- Density-based clustering for groups struggles when group sizes/motion change over time — [arXiv 2502.15252](https://arxiv.org/pdf/2502.15252v2)

### Inferences
- Easy FnB-specific pitfall map: (1) staff standing beside a table overlaps the table polygon → require seated + hip anchor inside a **seat polygon** (chair area), not the table-top polygon; (2) staff walking between camera and table occludes guests → long departure grace; (3) adjacent tables in an oblique view overlap in image space → assign by hip point to the nearest *seat* polygon, with per-table polygons drawn on the floor/seat plane rather than the table top; (4) a guest briefly standing (to take off a jacket, greet someone) → don't count as departure while within grace; (5) seated staff (e.g., cashier break at a table) → needs uniform/role classification, out of scope for 14 Nov.

### Gaps
- No quantitative study found on staff-vs-customer classification accuracy from CCTV (vendors use tags; open-source projects use standing/walking filters).

## Q7. Concrete application to Easy FnB — which stage each idea replaces/adds, and effort (before vs after 14 Nov 2026)

### Takeaway
Highest value per hour for the demo: replace the 1-second ≥0.8/≤0.2 rule with a per-table, time-based (seconds) state machine with asymmetric debounce and table-session keyed events, using hip-keypoint anchors in seat polygons and a seated filter; then flip the tracker to Ultralytics TrackTrack/BoT-SORT with longer buffer (+ optional `model: auto` ReID). These are ~1–2 days of work for two people and directly target all three observed problems. Head detectors, OccluBoost/BoxMOT, group detection and staff classifiers are post-hackathon.

### Cited Findings
- Count-based table state machine with 2 s occupied-debounce / 5 s empty-grace, hip-midpoint zone assignment and knee-angle seated test already works in an open-source restaurant monitor without a persistent-ID tracker — [RestoMan-AI](https://github.com/sahidirfan884/RestoMan-Ai)
- Probation (confirm) / shadow-tracking (coast) concept and tuning advice — [NVIDIA NvDCF tuning guide](https://docs.nvidia.com/metropolis/deepstream-nvaie30/dev-guide/text/DS_plugin_NvMultiObjectTracker_parameter_tuning_guide.html)
- Minimum consecutive frames for track activation (2) and lost-track buffer (60) as used in a 2026 dwell-time pipeline — [Roboflow blog](https://roboflow.com/blog/dwell-time-and-zone-analytics)
- Ultralytics trackers selectable by YAML (TrackTrack default; BoT-SORT/Deep OC-SORT/TrackTrack support `with_reid`; `model: auto` uses detector features; `track_buffer` controls occlusion tolerance) — [Ultralytics Track docs](https://docs.ultralytics.com/modes/track)
- Independent-harness identity gains: BoT-SORT IDF1 82.33 vs ByteTrack 79.16; OccluBoost 85.28 (needs ReID) — [BoxMOT GitHub](https://github.com/mikel-brostrom/boxmot)
- Retail audit method (manual review of recorded footage over quiet and peak periods, absolute accuracy) — [Indivd](https://www.indivd.com/insights/people-counting-accuracy-testing-vendor-claims); "time within tolerance" metric idea — [Density](https://density.io/resources/the-truth-behind-99-accurate-occupancy-sensors)
- Classroom-CCTV head dataset for occlusion-robust counting — [SCUT-HEAD](https://www.v7labs.com/open-datasets/scut-head)

### Inferences
**Proposed pipeline changes (my synthesis; parameters are starting points to tune on own footage)**

| # | Stage | Change (borrowed from) | Fixes | Effort | When |
|---|---|---|---|---|---|
| 1 | Event logic | Per-table FSM: `EMPTY → PENDING_ARRIVAL (seated_count≥1 for ≥3–5 s) → OCCUPIED → PENDING_LEAVE (seated_count=0 for ≥20–60 s) → NEEDS_CLEARING (if leftover items) → EMPTY`. Emit "new guest" only on PENDING_ARRIVAL→OCCUPIED; one `session_id` per occupancy; no second "new guest" while OCCUPIED (RestoMan, NvDCF probation/shadow) | Flip-flop, duplicate "new guest" (2–3×) | 0.5–1 day | Before 14 Nov |
| 2 | Presence signal | Use rolling **median/mode of seated count** over 3–5 s (time-based, fps-independent) instead of 1 s fraction; "party size changed" only after sustained change ≥10 s | Flicker from single-frame misses | 2–3 h | Before |
| 3 | Zone membership | Anchor = hip midpoint (COCO kp 11/12), fallback shoulder midpoint; polygons drawn over **seats/chairs** per table, not table top; nearest-table only if inside seat polygon (RestoMan) | Staff standing at table edge; adjacent tables in oblique view | 3–4 h (redraw zones) | Before |
| 4 | Role filter | Seated test (knee angle <140° or hip-to-shoulder vertical ratio + bbox aspect fallback); standing/walking persons never count toward arrival; separate "staff visited table" event from standing person near table for >N s (ChronoDine, RestoMan) | Staff counted as guests | 3–4 h | Before |
| 5 | Tracker | `tracker="tracktrack.yaml"` or `botsort.yaml` with `with_reid: True`, `model: auto`; `track_buffer` ≈ 3–5 s × fps (Ultralytics, BoxMOT evidence) | ID switches (affects hand-raise attribution and staff label persistence) | 1–2 h + fps test | Before (measure fps on RTX 3050 first) |
| 6 | Evaluation | Hand-label 2–3 recorded clips (quiet + busy) for arrival/departure times; report event precision/recall within ±15 s and % time table state correct (Indivd, Density) | Credibility with judges | 0.5 day | Before (if time) |
| 7 | Detector | Fine-tune head detector on SCUT-HEAD (+ CrowdHuman heads) as second count signal per table | Pose failures under occlusion | 2–4 days | After |
| 8 | Tracker | BoxMOT OccluBoost (+ReID) or TrackTrack official (FastReID) | Further IDF1 gain | 1–3 days | After |
| 9 | Party grouping | Persons who become seated at the same table within a window (e.g., 2 min) = one party; optional entrance co-arrival clustering (IEEE Access 2024, DBSCAN-style) | Party size, turnover per party | 1–2 days | After |
| 10 | Staff ID | Uniform-colour/appearance classifier or ReID gallery of staff; (retail analogue: UWB tags) | Seated staff, staff at table | 2–5 days | After |

- With items 1–4 in place, arrival/departure no longer depends on stable track IDs, so items 5 and 8 mainly improve hand-raise attribution and staff tracking rather than table events.
- Keep all thresholds in seconds and expose them in a config so they can be tuned live during the demo.

### Gaps
- No source provides validated threshold values for restaurant departure grace periods; 20–60 s is a reasoned starting point, not evidence-based.
- RTX 3050 4 GB throughput with YOLO26n-pose + TrackTrack/BoT-SORT + `model: auto` ReID is unmeasured; must be benchmarked locally before switching.
- Ultralytics' software license was not confirmed on the pages fetched in this research (BoxMOT is AGPL-3.0; TrackTrack official code is MIT).
