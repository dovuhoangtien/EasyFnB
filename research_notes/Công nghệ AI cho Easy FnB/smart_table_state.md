# Smart (AI-driven) Table-State Tracking for Easy FnB — beyond fixed timers

Scope: (a) visual meal-phase / table-state recognition from ceiling CCTV, (b) predictive/adaptive service-need and table-turnover models, plus service standards, proactive signals, competitor products, urgency-score design, and a 48-hour vs. production plan. Research date: 2026-11-03. Older items are marked [older].

---

## 1. Visual cues and models for meal-phase / table-state recognition

### Takeaway
No public dataset or canonical paper covers full dining-stage recognition (seated → ordered → eating → finished → dirty). Published work stops at occupancy (person-in-table-polygon), tableware detection, and leftover estimation. So the workable 2026 approach is hybrid: a fast permissive-license detector + tracker for people/tableware per table polygon (Apache-2.0 RF-DETR, or Ultralytics if AGPL/Enterprise is acceptable), with a Google VLM (Gemini API in the cloud, or Gemma 4 / PaliGemma 2 open weights) classifying cropped table images into a fixed JSON schema of meal-phase cues at low frequency or when events trigger it.

### Cited Findings
**Occupancy / table-state papers (mostly 2025, low-tier venues)**
- JAIDA paper "Real-Time Table Occupancy Detection in Restaurants Using Object Detection and Computer Vision Techniques" counts the people near each table to get occupancy and compares the result with manual counts. It reports 94% table occupancy detection accuracy in a real restaurant — [JAIDA](https://dergipark.org.tr/en/pub/jaida/article/1613993); [JAIDA PDF](https://dergipark.org.tr/tr/download/article-file/4495676)
- IJRASET 2025, "Real-Time Restaurant Table Occupancy Monitoring System": YOLOv8 detects tables and people, with a Django web dashboard — [ResearchGate](https://www.researchgate.net/publication/394155718_Real-Time_Restaurant_Table_Occupancy_Monitoring_System)
- PETI paper: YOLOv8 + SORT tracking + geometric overlap. It checks customer centroids against table polygons rather than predicting table state directly, and this held up better in crowded scenes — [IMETI/PETI](https://ojs.imeti.org/index.php/PETI/article/download/15704/1856)
- Search found no canonical peer-reviewed paper on dining-stage detection (seating/ordering/check-out). The closest material is vendor writing, such as Roboflow's blog on overhead cameras tracking milestones like seating, menu handling and table resets — [Roboflow blog](https://blog.roboflow.com/computer-vision-restaurant-industry/)
- Open-source: ChronoDine uses YOLOv11 + pose estimation to tell seated guests from standing staff, and tracks occupancy, dwell time and turnover velocity from security cameras — [GitHub chrono-dine](https://github.com/Mashood-Basharat/chrono-dine). A second repo classifies tables as available or occupied from CCTV — [GitHub](https://github.com/sanaulislamzihad/Restaurant-Table-Occupancy-Detection)
- [older, 2017] "Grab, Pay and Eat: Semantic Food Detection for Smart Restaurants" — food detection for smart-restaurant/self-checkout settings — [arXiv 1711.05128](https://arxiv.org/pdf/1711.05128)

**Tableware / plate-state detection**
- Tableware Scene dataset (arXiv 2503.04322): YOLOv8m detects plates, glasses, cups and utensils. 16,451 hand-labelled boxes over 474 images, F1 = 0.83. Small, tightly packed objects were the hardest case, which matters for top-down CCTV of a crowded hotpot table — [arXiv 2503.04322](https://arxiv.org/pdf/2503.04322)
- EasyChair 2024 preprint: YOLOv5 decides whether a restaurant plate holds food. Too little dish variety hurt performance, so the authors used saliency detection to generate more varied training data — [EasyChair](https://easychair.org/publications/preprint/Jjl6G)
- Roboflow Universe has several public tableware/dish datasets (tableware incl. cups; dishes-detection with cups/plates/bread; "ceramic" with bowls/cups/plates/pots; kitchen-object-detection under CC BY 4.0). Labels and licences mostly unverified. Clean vs. dirty and empty vs. full would need custom labels — [Tableware](https://universe.roboflow.com/republic-polytechnic-oo1p7/tableware-97quf/dataset/2); [dishes-detection](https://universe.roboflow.com/foodscanner-kov42/dishes-detection); [ceramic](https://universe.roboflow.com/sliit-deypn/ceramic-yot3f); [kitchen-object-detection](https://universe.roboflow.com/kitchenobjectdetection/kitchen-object-detection-acyvk)

**Food-leftover / plate-emptiness estimation**
- LeFoodSet (hospital, 2025): presented as a large open dataset for leftover estimation, with leftover rates, food types, and before/after weights from digital scales. Baseline is multi-task learning — [PMC12087991](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12087991/)
- FLIC (university canteen, 2026): 401 paired full/leftover tray images over 22 days, with pixel-precise masks and measured food mass. Baselines are U-Net, DABNet, DINOv2+FeatUp and SAM for food/no-food segmentation — [Piccoli et al. 2026, Applied Sciences](https://boa.unimib.it/retrieve/b2859b17-2a0e-4581-b46c-b8d0d58c1079/Piccoli%20et%20al-2026-Applied%20Sciences%20%28Switzerland%29-VoR.pdf)
- University dining-hall case study (2025): plate-level waste from segmentation of pre/post-meal RGB images across five dishes. The authors call it a framework evaluation, not an exact measure — [arXiv 2507.14662](https://arxiv.org/pdf/2507.14662)
- A 2026 restaurant food-waste ML paper says public datasets pairing measured waste with operational data are still scarce — [arXiv 2609.08078](https://arxiv.org/pdf/2609.08078)
- [older, 2022] Thai thesis: Mask R-CNN + area-ratio leftover estimation on 141 plate images — [NU repository](https://nuir.lib.nu.ac.th/dspace/handle/123456789/5625)

**People eating vs. idle (intake-gesture recognition)**
- OREBA: 9,069 intake gestures from 180 participants over 202 sessions, with synchronized frontal video + wrist IMU. Access needs a signed agreement — [OREBA on PapersWithCode](https://www.paperswithcode.com/paper/oreba-a-dataset-for-objectively-recognizing); [arXiv 2007.15831](https://arxiv.org/pdf/2007.15831.pdf)
- Video intake detection on 360° video of 102 participants found appearance features matter more than motion, and multi-frame temporal context is essential for top performance — [Newcastle repository](https://ogma.newcastle.edu.au/vital/access/%20/manager/Repository/uon:38695)
- EatSense combines RGB + skeleton for intake-gesture classification. Skeleton methods mostly work on trimmed clips, which limits them on untrimmed CCTV — [arXiv 2504.10635](https://arxiv.org/pdf/2504.10635)
- Most intake-behaviour studies use dedicated private datasets — [arXiv 2504.10635](https://arxiv.org/pdf/2504.10635)

**Google VLMs (current docs, fetched Nov 2026)**
- Gemini returns bounding boxes as `box_2d` = `[ymin, xmin, ymax, xmax]`, normalized to 0–1000, and takes custom instructions (e.g. "boxes for all X"). Segmentation returns `box_2d`, `label` and a base64 PNG probability mask, and is supported from Gemini 2.5. Docs advise `thinking_level: "minimal"` for segmentation and a JSON schema (`response_format`, Pydantic/Zod) for parseable output. Examples use `gemini-3.8-flash` — [Gemini image understanding](https://aistudio.google.com/docs/image-understanding)
- Image cost: an image with both sides ≤384 px is 258 tokens. Larger images are tiled at 768×768, 258 tokens per tile; a 960×540 frame is 6 tiles. Up to 3,600 images per request, 20 MB inline limit — [Gemini image understanding](https://aistudio.google.com/docs/image-understanding)
- Video: default sampling is 1 fps, configurable (e.g. `fps: 0.5`), with clipping via `start_offset`/`end_offset`. 66 tokens/frame at low media resolution, 258 otherwise (~100 or ~300 tokens/s including audio). Timestamps use MM:SS. 1M-context models take up to ~3 h of video at low res. An opt-in "agentic" mode is listed for Gemini 4 Argon, 3.8 Flash, 3.6 Flash and 3.5 Flash Lite — [Gemini video understanding](https://aistudio.google.com/docs/video-understanding)
- Gemini Live API (Vertex/Gemini Enterprise Agent Platform) takes video as discrete JPEG frames at about 1 FPS. 768×768 at 1 FPS is recommended, and media resolution can be low/medium/high — [Google Cloud Live API docs](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/live-api/send-audio-video-streams)
- Gemma 4 is reported as Apache 2.0, multimodal (text + image in; audio on smaller models), with E2B (~2.3B effective) and E4B (~4.5B effective) edge models for phones and boards (Raspberry Pi, Qualcomm NPUs, WebGPU). Secondary sources disagree on the full lineup (12B / 26B MoE / 31B) — [emelia.io](https://emelia.io/hub/gemma-4-open-source-guide); [thekodelab](https://thekodelab.com/en/posts/google-gemma-4/); [mindstudio](https://www.mindstudio.ai/blog/what-is-gemma-4-apache-2-multimodal)
- PaliGemma 2: "detect" / "segment" task prefixes, sizes 3B/10B/28B at 224/448 px. "mix" checkpoints work out of the box, "pt" checkpoints are for fine-tuning (big_vision code + notebook). Gemma licence, which permits commercial use under the Prohibited Use Policy, with gated HF access — [HF model card](https://huggingface.co/google/paligemma2-3b-mix-448/blob/main/README.md); [Voxel51 plugin](https://docs.voxel51.com/plugins/plugins_ecosystem/paligemma2.html); [arXiv 2412.03555](https://arxiv.org/html/2412.03555v1)
- Gemini zero-shot detection works best on common objects (2025 tutorial) — [Roboflow blog](https://blog.roboflow.com/gemini-2-5-object-detection-segmentation/)

**Detector licences**
- RF-DETR Nano/Small/Medium/Large are Apache 2.0. Atto/Femto/Pico/XL/2XL are under Roboflow Platform Model License 1.0. The segmentation family is Apache 2.0 at all sizes — [Roboflow RF-DETR licence](https://roboflow.com/model-licenses/rf-detr); [Roboflow licensing](https://roboflow.com/licensing); [Roboflow blog](https://roboflow.com/blog/rf-detr-is-free-to-use-commercially)
- Ultralytics YOLO11/YOLO26: AGPL-3.0 or a paid Enterprise licence. Both are recommended for stable production. Free use carries AGPL obligations, including releasing project source — [Ultralytics docs](https://docs.ultralytics.com/)
- YOLO-World: GPL-3.0 per the project README / Roboflow comparison, AGPL-3.0 per another Roboflow page (conflict) — [Roboflow compare](https://playground.roboflow.com/models/compare/sam-3-vs-yolo-world); [HF README](https://huggingface.co/spaces/csmithxc/YOLO-World3/blame/e346a5d632f4ab6a9ea47c036df8437014a3cbf6/README.md)
- Grounding DINO and OWL-ViT are reported as Apache 2.0 (secondary source). SAM 3's licence is "Custom" on Roboflow but "Apache 2.0" in a third-party post (unresolved conflict) — [Lightly blog](https://www.lightly.ai/blog/best-ultralytics-alternatives-in-2026); [builderai.tools](https://builderai.tools/blog/real-time-object-detection-rf-detr-yolo-sam-3); [Roboflow compare](https://playground.roboflow.com/models/compare/sam-3-vs-yolo-world)

### Inferences
- **Cue → phase mapping, all observable top-down.** It should be a structured VLM output, not free text:
  - `empty`: no persons in polygon, no tableware or only a clean set-up.
  - `seated_unattended`: ≥1 seated person, no staff visit yet, menu possibly open.
  - `ordering`: staff standing at the table edge, maybe holding a tablet/notepad, or a POS order event.
  - `waiting_food`: POS order exists, no or few food plates, drinks may be present.
  - `eating`: food-bearing plates/bowls present, hands-to-mouth motion, hotpot steaming or pot present.
  - `finishing`: plate fill falling, utensils down, phones out, people leaning back.
  - `wants_bill`: bill folder/receipt or card in hand, a raised hand, coats on.
  - `leaving`: people standing up with bags.
  - `needs_clearing`: no persons but plates/glasses/napkins remain.
  - `resetting`: staff wiping or carrying a tray.
  This matches the state sets used by vendors (SciForce: Available, Waiting for Greeting, Choosing Meals, Waiting for Waiter, Waiting for Food, Needs Cleaning; see Q5).
- **Two-tier perception.**
  - Tier 1, every frame or 2–5 fps on an edge box: detector + tracker over table polygons, using the published centroid-in-polygon geometric rule. Staff vs. guest comes from uniform colour/pose/standing-vs-seated, as ChronoDine and SciForce do. Tier 1 emits low-level events (sit, stand, staff_enter_zone, object_count_change).
  - Tier 2, event-triggered or every 15–60 s per table: crop the table, send it to Gemini Flash (or local Gemma 4 E4B / PaliGemma 2) with a JSON schema such as `{phase, plates_with_food:int, empty_plates:int, glasses_low:int, bill_folder:bool, menus_open:bool, hand_raised:bool, people_standing:int, phones_out:int, hotpot_present:bool, confidence}`.
- **Gemini cost estimate (from cited token rules).** A ≤384×384 table crop costs 258 tokens. 20 tables × 1 crop per 30 s = 40 crops/min ≈ 10.3k input tokens/min ≈ 0.62M tokens/hour, before output tokens. Batching several crops into one request (allowed, up to 3,600 images) cuts request overhead. Short 5–10 s clips at `fps: 1–2` and low media resolution (66 tokens/frame) suit motion cues like eating vs. idle or waving.
- **Plate emptiness.** The leftover literature (LeFoodSet, FLIC) uses close-up tray photos and scale ground truth, which ceiling CCTV doesn't provide. For Easy FnB, a coarse 3–4 level ordinal ("full / partly eaten / nearly empty / empty") per plate from a VLM or a small classifier on detector crops is realistic. Exact percentage estimation isn't.
- **Eating vs. idle.** Intake-gesture work stresses temporal context, so single frames won't do. Use a short clip to Gemini, or pose keypoints with hand-to-face distance over ~5 s windows, as a cheap heuristic.
- **Licence choice for a commercial path.** Prefer RF-DETR (N–L, Apache 2.0) + Gemma 4 (Apache 2.0) + Gemini API. Ultralytics is fine for a hackathon demo but carries AGPL-3.0 obligations (or a paid Enterprise licence) once commercialised.

### Gaps
- No public dataset for top-down CCTV dining-stage classification, hotpot tables, or Vietnamese tableware (bát, đĩa, nồi lẩu) was found.
- No published accuracy for Gemini/Gemma/PaliGemma zero-shot "table phase" classification. Easy FnB will need its own small evaluation set.
- Gemini API per-token prices for the current Flash models weren't retrieved. The licence texts for SAM 3 and Grounding DINO weren't verified at primary source.
- Gemma 4's exact lineup and the image-resolution limits of its edge models need checking against Google's official model card.

---

## 2. Replacing fixed timers: adaptive thresholds, survival/hazard models, sequence models, industry practice

### Takeaway
Industry wait-time systems (Yelp Waitlist) use gradient-boosted trees (XGBoost) on contextual features and handle cold start with partial features. Academic turn-time work shows survival (proportional-hazards) models give only small gains over linear regression. Party size and meal period are consistently significant predictors of duration. For Easy FnB, alerts should fire on "time in state is abnormal for this context": a conditional quantile or hazard threshold per state × party size × daypart × restaurant, seeded from service standards and updated from collected data. Ship it with dark-launch/slow rollout, as Yelp did.

### Cited Findings
- Yelp Waitlist (Dec 2019) [older]:
  - Wait estimates come from **XGBoost**, trained offline on Spark over tens of millions of instances and served by a Java model server.
  - Live restaurant state (people in line) comes from MySQL, batch features from Cassandra, and closing time caps the estimate.
  - Cold start uses partial features that improve with retraining.
  - Models were dark-launched, then rolled out slowly because of feedback loops: the quote changes when guests arrive, which contaminates the labels.
  - The tracked metric is the % of diners waiting >5 min beyond the quote, balanced against empty tables and host overload.
  — [Yelp Engineering](https://engineeringblog.yelp.com/2019/12/architecting-wait-time-estimations.html)
- Legg, Tang, Hancer & Slevitch, "Using Survival Modeling for Turn-Time Predictions in Foodservice Settings," J. Foodservice Business Research 22 (2018/19):
  - Compared linear regression with five proportional-hazards survival models on simulated dine-in data.
  - Survival models gave small gains, and regression performed "adequately".
  - Survival models are recommended for operators with mature revenue-management systems who want incremental improvement.
  — [Penn State Pure](https://pure.psu.edu/en/publications/using-survival-modeling-for-turn-time-predictions-in-foodservice-/); [core.ac.uk](https://core.ac.uk/download/13606347.pdf)
- Thai hotpot study (ACM, ~2023): a Random Forest classifier on historical POS data (pre-COVID) predicts dining-time class in 4 bins: short / normal / long / too long. Dining duration depends on restaurant type, and predicted waits can be shown on a queue display. It also notes earlier reservation wait-time systems didn't report accuracy — [ACM DL](https://dl.acm.org/doi/fullHtml/10.1145/3594300.3594303) (full text 403; summary via search)
- Bloom et al. (2012), casual full-service chain: meal period and party size have a statistically significant effect on meal duration, used to build a predictive model — [UCF STARS](https://stars.library.ucf.edu/scopus2010/5520)
- Korean family-restaurant study: dinner is much longer than lunch, and larger parties stay longer at dinner and on weekdays — [KoreaScience](https://koreascience.kr/article/JAKO201111436239006.page?lang=en)
- Bell & Pliner (2003) [older]:
  - Group size correlates positively with meal duration.
  - Cafeteria means were 12.6 / 23.0 / 33.0 / 41.1 / 44.0 min for 1 / 2 / 3 / 4 / 5+ diners.
  - Durations were longest in the moderately priced restaurant and shortest in fast food.
  — [Zenodo PDF](https://zenodo.org/record/1259941/files/article.pdf)
- Kimes (Cornell CHR) [older]:
  - Duration-management levers are reducing uncertainty of arrival, reducing uncertainty of duration, and reducing the time between meals.
  - Reducing variation in meal duration increases predictability, which improves seating decisions.
  - Kimes & Robson (2004): table type and location affect spend-per-minute; booths are slightly above average, banquettes below.
  — [Cornell eCommons](https://ecommons.cornell.edu/server/api/core/bitstreams/e4a944d8-bdad-4220-9281-df8203ba1e8c/content); [Hospitality Net](https://www.hospitalitynet.org/news/4018612.html)
- Pace caveats [older]: fine-dining guests are more sensitive to pacing than casual guests (Noone et al. 2007). A 1,200-scenario simulation found the revenue gain from shorter dining is under ¼ of what the common assumption predicts — [Cornell eCommons](https://ecommons.cornell.edu/server/api/core/bitstreams/e4a944d8-bdad-4220-9281-df8203ba1e8c/content); [typeset.io](https://typeset.io/pdf/mythical-revenue-benefits-of-reducing-dining-duration-in-2wke3n4f8i.pdf)
- Patents: US 2021/0201213, "Reservation and waitlist management using precision table turn-time analysis," estimates turn times from restaurant and customer history — [Justia](https://patents.justia.com/patent/20210201213). A USPTO patent covers reservation wait-time estimation with event/video data — [USPTO 10990909](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10990909); [USPTO 7756745](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/7756745)
- Vendor claim (unverified): Bitwise reports 87% accuracy predicting order wait time for a large full-service dining company — [Bitwise](https://www.bitwiseglobal.com/insights/predicting-order-wait-time-using-machine-learning)

### Inferences
**Adaptive threshold design, replacing "5 min"**
- For each state transition s→s' (e.g. seated→greeted, ordered→food_arrived, finished→bill_requested, vacated→cleared), keep an empirical duration distribution per (restaurant, daypart, party-size bucket, table zone, restaurant type).
- Alert when `time_in_state > Q_p(context)` (e.g. p75 = "nudge", p90 = "alert"). With no data yet, use a Bayesian/shrinkage prior centred on service-standard targets (Q3), e.g. greet target 60–120 s.
- As data accumulates, blend toward local quantiles: `θ = (n0·prior + n·local)/(n0+n)`.

**Hazard view**
- Fit a Weibull/Cox (or gradient-boosted survival, e.g. XGBoost AFT) model for "time until guest needs X". Cox/Weibull are the survival-model family; Legg et al. tested proportional-hazards variants.
- Covariates: party size, daypart, weekday, POS items ordered/amount, restaurant type (hotpot/buffet/casual), current occupancy %, staff-on-floor count, and visual phase features.
- Alert on hazard or conditional-survival crossing, i.e. P(need service in next 60 s | still waiting) > τ. This alerts earlier for contexts where need arrives quickly, such as a party of 2 at lunch rush, and later for long hotpot dinners.

**Sequence models**
- Treat the table as an HMM / hidden semi-Markov model. Hidden states = meal phases. Observations = detector counts + VLM cue vectors + POS events. Explicit duration distributions per state (semi-Markov) give both smoothing (no flicker between "eating" and "finishing") and remaining-time prediction.
- Later, a small GRU/transformer over event streams can predict next event and time-to-event once logs exist.
- These are standard methods; no restaurant-specific HSMM paper was found.

**Table-free prediction**
- `ETA_free = now + E[remaining eating | phase, elapsed, party size] + E[bill+pay] + E[clear]`, with each term learned. This feeds a waitlist estimate in the Yelp style.
- Quote intervals rather than points (e.g. conformal or quantile regression), and log the feedback-loop effect as Yelp warns.

**Anomaly detection**
- Flag waits that are robust-z-score or isolation-forest outliers vs. the same context.
- Flag sudden drops in staff visits per table per hour (understaffing).

**Rollout**
- Copy Yelp's dark-launch then slow-rollout pattern. Run the predictive model silently alongside the rule-based baseline, measure precision/lead-time of alerts, then switch.

### Gaps
- No public details on OpenTable, Resy, SevenRooms or Toast turn-time models were retrieved (marketing pages only). A single Toast-attributed staff guide was found without timing data.
- Full-text metrics (C-index, MAE) of Legg et al., Bloom et al. and the Thai hotpot RF paper were not accessible (403 / paywall).
- No published HMM/HSMM application to restaurant meal phases was found.

---

## 3. Service standards and typical phase durations (inputs for dynamic thresholds)

### Takeaway
Industry SOPs set a short greet window (host within ~30 s, server within ~60 s to 2 min, "2-minute rule"), a check-back about 2 min or 2 bites after food lands, and check delivery within a few minutes of request. Hotpot/buffet durations are best modelled from time-limit policies: Singapore buffets publish 90/120/150-min caps by party size. No Vietnamese chain policy was found.

### Cited Findings
- Greeting timing varies by source:
  - A sample SOP gives 30 s for the host to greet arriving guests and 60 s for the server to greet the table — [Restroworks](https://www.restroworks.com/blog/?p=17849); [Cuboh](https://cuboh.com/blog/steps-of-service)
  - Server-training flashcards cite a "two-minute rule" for greeting and a "two bites, two minutes" check-back — [Brainscape](https://brainscape.com/flashcards/servers-steps-of-service-9949998/packs/17469973)
  - A server ebook says guests start wondering whether their server knows they're there within a couple of minutes, and sets a 2-minute approach target — [RealServerTraining ebook](https://realservertraining.com/content/files/2023/07/GREETING-YOUR-TABLE-EBOOK---FOR-SERVERS-BY-SERVERS.pdf)
  - A Q&A page says ~1 min; a forum says 3–5 min (least authoritative) — [calendar-uk FAQ](https://www.calendar-uk.co.uk/frequently-asked-questions/how-should-a-server-greet-a-table); [Slickdeals forum](https://slickdeals.net/f/805355-retired-how-to-be-a-good-server-in-a-restaurant?p=11033950)
  - Dummies uses 2 minutes for greeting a bar patron — [Dummies](https://www.dummies.com/article/business-careers-money/careers/hospitality-careers/how-to-establish-service-standards-in-bars-152712/)
- Check-back: within ~2 min after food arrives, to catch quality/temperature issues, or 2–3 min / 2–3 bites per course — [Xenia](https://xenia.team/articles/steps-of-service-restaurant); [FoodDocs](https://www.fooddocs.com/food-safety-templates/restaurant-steps-of-service)
- Typical 7-step structure: welcome/greet → drinks/menu → order → delivery → check-ins → dessert → check → reset/clear. One SOP sets a 6-min target for delivering the check — [Restroworks](https://www.restroworks.com/blog/?p=17849); [GloriaFood](https://gloriafood.com/restaurant-steps-of-service); [Qvalon](https://qvalon.com/blog/the-7-steps-of-restaurant-service-key-standards-for-exceptional-guest-experience/)
- A vendor CV deployment used alert rules of no waiter approach within **3 min** of seating, and a dirty table uncleaned for **10 min** — [SciForce case study](https://www.sciforce.solutions/case-studies/computer-vision-restaurant-service-optimization)
- Buffet/hotpot time limits (Singapore): 90 min (2 pax) / 120 min (3–6 pax) / 150 min (>7 pax). Guo Fu hotpot buffet: 90 min (3 pax) / 120 min (>4 pax). Typical buffet limits are about 60–90 min — [TheSmartLocal](https://thesmartlocal.com/read/best-buffets-singapore/); [TheSmartLocal value buffets](https://thesmartlocal.com/read/5-best-value-buffets-in-singapore/amp/)
- Vietnam: listings for HP3 Buffet Lẩu, Kichi Kichi, Manwah and Hutong show opening hours and prices (e.g. HP3 ~89–99k VND/person) but no stated eating-time cap — [Foody HP3](https://www.foody.vn/ha-noi/hp3-buffet-lau); [Mytour Kichi Kichi](https://mytour.vn/vi/blog/am-thuc/top-14-quan-lau-ngon-o-phuong-cau-giay-ha-noi-mytour.html); [Mia.vn Manwah](https://mia.vn/cam-nang-du-lich/8-quan-buffet-da-nang-13902)
- Planning assumption used in revenue-management examples: ~1 h average dining time (100 seats, $20 check) — [Cornell eCommons](https://ecommons.cornell.edu/server/api/core/bitstreams/019c3aa9-4744-4709-9d77-d18dd8abfa30/content)

### Inferences
Suggested **prior** targets per state. These are starting points, to be overridden per restaurant by learned quantiles (Q2):

| Transition | Casual dining prior | Hotpot (à la carte) | Buffet / buffet-lẩu |
|---|---|---|---|
| seated → first staff contact | nudge 60 s, alert 120 s, escalate 180 s | same | same (explain rules, set up pot) |
| order → first dish/drink | 8–15 min (POS-item dependent) | broth/pot within ~5 min | pot + first tray ~5–8 min |
| food landed → check-back | 2 min / "2 bites" | 3–5 min after pot boils | periodic sweep ~10 min |
| eating duration | learn from party size × daypart (Bell & Pliner trend) | longer; dinner > lunch | capped by time limit (90/120/150 min by party size as analog) |
| finished cue → bill offered | 2–5 min | 2–5 min | at time-limit −10 min: "last order" call |
| bill requested → bill delivered | ≤6 min (SOP) | same | same |
| vacated → cleared | alert 3–5 min, escalate 10 min (vendor rule) | longer reset (pot/burner cleaning) | same |

Make thresholds **load-aware**: when occupancy is above ~80% or the waitlist is non-empty, tighten clearing/bill thresholds (turnover matters). When the waitlist is empty, relax pacing alerts (Noone: don't rush guests).

### Gaps
- No authoritative casual-dining, hotpot, or Vietnamese-specific measured phase durations were found. The Bloom et al. coefficients and Thai hotpot durations weren't accessible.
- No Vietnamese hospitality SOP (e.g. from Golden Gate / Redsun chains) on greet timing was found.

---

## 4. Proactive service signals (empty glasses, empty plates in buffet/hotpot, broth low, finished-but-no-bill)

### Takeaway
Proactive cues are object-state questions about glass fill, plate fill, pot level, bill folder, and posture. Detectors can find the objects (tableware work reaches F1 0.83 for plates/glasses/cups, weaker on small packed items). The state ("empty", "low") is better judged by a VLM on a crop or a small trained classifier. Hotpot broth level from a ceiling camera is hard. The Haidilao pot weight sensor shows a non-vision sensor may be more reliable.

### Cited Findings
- Tableware detection of plates, glasses, cups and utensils: F1 0.83, with small, closely packed objects hardest — [arXiv 2503.04322](https://arxiv.org/pdf/2503.04322)
- A plate-has-food classifier (YOLOv5) is feasible but needs dish variety (saliency-based augmentation) — [EasyChair](https://easychair.org/publications/preprint/Jjl6G)
- Haidilao's Beijing smart restaurant (2018) [older]: weight sensing in hotpot pots adjusts heat automatically, projected to save ≥10% electricity — [SCMP](https://amp.scmp.com/tech/article/2171402/first-hand-review-haidilaos-smart-hotpot-restaurant-beijing)
- Haidilao's 2024 annual report reportedly says AI "smart checks" cover 100% of stores with >95% recognition accuracy (company-reported, method unknown) — [index.vn](https://index.vn/en/news/1400-stores-100percent-ai-coverage-across-haidilao-network-how-the-chain-is-overcoming-bottlenecks-across-thousands-of-outlets)
- Kura Sushi (Japan): AI cameras have counted plates since end-2021 (monitoring cover open/close). After the 2023 "sushi terrorism" incidents they were upgraded to identify plate and seat number, with HQ staff phoning the store to act — [Japankuru](https://www.japankuru.com/en/aaa/e3808.html); [Yahoo News](https://news.yahoo.com/ai-camera-helps-sushi-restaurant-184453147.html)
- Gemini can return per-object boxes + labels + masks with custom instructions (e.g. "box every glass and say if it is empty"), output as JSON schema — [Gemini image understanding](https://aistudio.google.com/docs/image-understanding)
- Ziosk (tablet) targets the time for a guest to request, receive, and pay the check. It's a non-vision answer to "finished but no bill" — [Wikipedia Ziosk](https://en.wikipedia.org/wiki/Ziosk)

### Inferences
**Signal → detector → action**

| Signal | Detector | Action |
|---|---|---|
| Empty or low glass | Glass box + VLM "fill level: empty/low/half/full" (clear glasses on dark tables are hard; use a 2–3 frame vote) | "Refill drinks T7" (upsell) |
| Buffet/hotpot empty plates | Count trays/plates with no food ≥ N for ≥ 60 s, while guests still in `eating` and within the time limit | "Offer next round / clear empties T3" |
| Hotpot broth low / pot unattended | Weak visually. Proxy: pot present + no steam/visible liquid in the VLM crop + elapsed time since broth refill > learned p75. Better: induction-cooker power or pot weight (Haidilao) | "Top up broth T5" |
| Finished but no bill | ≥80% of plates empty or utensils down + no hand-to-mouth motion for ≥ 3–5 min + no bill folder + POS not closed | Gentle "check on T9 / offer dessert or bill". Priority rises with waitlist length |
| Wants attention | Raised hand or sustained gaze at staff, from pose keypoints (wrist above shoulder for > 1.5 s), confirmed by a VLM clip | Immediate, highest-weight event |
| Leaving / unpaid risk | People standing + coats/bags + POS still open | Alert cashier |

**Prioritisation**: proactive signals (refill, empties) should rank below reactive needs (hand raised, unattended new table, bill requested) but above routine checks. See the Q6 scoring.

### Gaps
- No published method or dataset was found for broth-level estimation or glass-fill estimation from overhead CCTV.
- No validated "finished eating" detector was found. It's an inference from leftover-estimation + intake-gesture literature.

---

## 5. Existing products/startups doing CV analytics for restaurants (2023–2026) and positioning

### Takeaway
Commercial products mostly do occupancy, vacancy/uncleared-table alerts, waiter response time and turnover metrics on existing CCTV, with fixed configurable targets (e.g. a 3-min greet alert, 10-min dirty-table alert; FlowLinks ~60 s vacancy-to-alert). None found publicly claims VLM-based meal-phase understanding (eating/finished/wants-bill) or predictive, context-adaptive thresholds. That is Easy FnB's differentiation space. No Vietnamese vendor offering restaurant table analytics was found.

### Cited Findings
- **FlowLinks**:
  - Uses existing CCTV for table vacancy detection (starts the turnover clock), uncleared-table alerts after a target time (e.g. "Table 7 — uncleared 8 min, alert sent to floor"), clean verification before reseating, turnover per table/shift, and multi-outlet comparison.
  - Claims ~60 s from vacancy to staff alert, from **$35/camera/month**.
  - Setup: map table zones + set a target clearance time.
  - No eating/finished phase detection.
  — [FlowLinks table turnover](https://www.flowlinks.ai/restaurants-cafes/table-turnover); [FlowLinks restaurants](https://www.flowlinks.ai/restaurants-cafes)
- **SciForce case study** (full-service chain, ~1,200 locations, 30+ countries):
  - Stack: YOLO + DeepSORT + POS integration. Each table is a fixed zone with a Table ID linking video and POS.
  - Events: seating, departure, waiter approach, order (POS), food delivery (tray/dish in hand), clearing.
  - States: Available, Waiting for Greeting, Choosing Meals, Waiting for Waiter, Waiting for Food, Needs Cleaning.
  - Alerts: no approach within 3 min, dirty table for 10 min.
  - Staff vs. guest by uniform + movement patterns (kitchen-to-table routes).
  - Claimed: waiter response >5 min → <2 min, cleanup 15 → <5 min, Google rating 4.5 → 4.7. No detection-accuracy figures.
  — [SciForce](https://www.sciforce.solutions/case-studies/computer-vision-restaurant-service-optimization); [Medium](https://medium.com/sciforce/optimizing-multi-zone-restaurant-service-with-computer-vision-for-hospitality-3316f009ec5b)
- **Slinai**: table occupancy and turn-time analytics; dwell per table zone, seat utilisation, bottlenecks — [Slinai](https://slinai.com/industries/restaurants-qsr-video-analytics)
- **Presto Vision** (2019, piloted at Outback Steakhouse) [older]:
  - Tags hosts/staff/guests in real time, measures host availability, wait times, bounce rate and a forecast "guest experience score", and flags long waits, untidy lobbies and absent hosts.
  - Privacy: no PII, individuals modelled as abstracted entities, data deleted after 30 days.
  - Pilot started in the lobby, with dining expansion planned.
  — [BusinessWire](https://www.businesswire.com/news/home/20191016005058/en/); [Hospitality Tech](https://hospitalitytech.com/presto-pilots-computer-vision-product)
- **Nova/NovaTab guide (2025)**: pose estimation for queues and anonymized tracking for dwell, extended to table turnover. It mentions a Yum Brands × NVIDIA vision-AI initiative (pilots across ~500 locations), mainly drive-thru/kitchen — [NovaTab](https://www.novatab.com/blog/vision-ai-in-restaurants)
- **Industry claims (unverified)**: 10–15% turnover increase with video analytics; one case with +12% turnover and −25% average wait — [Kuyper Creative](https://kuyperscreative.com/video-analytics-matters-why-your-cameras-are-the-secret-to-faster-table-turns/)
- A 2025 trend piece: cameras detect vacated-but-not-cleared tables and alert staff (no vendor named) — [Restaurant Technology News](https://restauranttechnologynews.com/2025/06/how-restaurants-are-building-invisible-support-teams-with-ai-chatbots-and-smart-cameras/). A Griddl briefing argues cameras are the most underused restaurant tech — [Griddl](https://griddl.ai/briefing/your-cameras-may-be-the-most-underused-technology-in-the-restaurant)
- **Asia**:
  - Kura Sushi (Japan) AI cameras for plate counting and tamper alerts by seat — [Japankuru](https://www.japankuru.com/en/aaa/e3808.html)
  - Haidilao (China) smart restaurants and AI smart checks (company-reported) — [SCMP](https://amp.scmp.com/tech/article/2171402/first-hand-review-haidilaos-smart-hotpot-restaurant-beijing); [index.vn](https://index.vn/en/news/1400-stores-100percent-ai-coverage-across-haidilao-network-how-the-chain-is-overcoming-bottlenecks-across-thousands-of-outlets)
  - A Haidilao Taiwan post defended unnamed "related equipment" as protecting dining rights and service quality (privacy controversy) — [Taiwan News](https://www.taiwannews.com.tw/en/news/4185123)
- **Vietnam**:
  - No restaurant table-state CV vendor was found.
  - Hanet makes on-camera-AI-chip "AI Camera Office" for access/attendance, not tables — [VnExpress](https://vnexpress.net/ai-camera-ho-tro-phong-chong-covid-19-4291788.html); [VietnamNet](https://vietnamnet.vn/en/sci-tech-environment/vn-startup-uses-ai-for-surveillance-cameras-743471.html)
  - Vietnamese trade press discusses "AI trong nhà hàng" generally — [BrandsVietnam](https://www.brandsvietnam.com/congdong/topic/341418-ai-trong-nha-hang-tuong-lai-cua-trai-nghiem-an-uong-thong-minh)
  - Ultralytics publishes a Vietnamese-language blog on restaurant vision AI — [Ultralytics VI](https://www.ultralytics.com/vi/blog/streamlining-operations-using-vision-ai-in-restaurants)

### Inferences
- **Positioning**: "FlowLinks/SciForce measure *when* things happen with fixed targets. Easy FnB understands *what phase* each table is in (VLM), predicts *when* it will need service or free up (context-adaptive hazard), and ranks *who to serve next* (urgency score)." Key Vietnam fit: hotpot/buffet phases (pot set-up, broth refills, tray rounds, time limits) aren't covered by Western products.
- Borrow from Presto: an abstracted-entity, no-face-recognition privacy stance with short retention (30 days). This matters for Vietnam's personal-data regime and for diner acceptance (Haidilao Taiwan backlash).
- Borrow from FlowLinks: the per-camera monthly price anchor (~$35) and zero-new-hardware setup by drawing table polygons.

### Gaps
- No info on Wobot.ai, Hoptix, Agot, PreciTaste or Winnow for front-of-house table analytics (searches returned nothing relevant). Most of these are kitchen/drive-thru focused.
- No Korean, Singaporean or Thai front-of-house table-CV vendors were found, and no Vietnamese POS (iPOS, KiotViet, Sapo FnB) CV integrations.
- Vendor ROI figures are self-reported and unverified.

---

## 6. Priority / urgency score design fusing multiple signals

### Takeaway
No restaurant-specific published urgency framework was found. The closest analogue is clinical alarm management:
- crisis vs. warning tiers with immediate vs. delayed routing,
- context-dependent sub-priority (the same alarm ranks differently by patient profile),
- time-based escalation to a second responder,
- continuous tuning to staffing and time of day, which reduced alarm load (~43% in one study) without losing sensitivity.
Easy FnB should copy this: tiered events, context-normalised lateness, escalation ladders, and alert-fatigue controls.

### Cited Findings
- Johns Hopkins alarm practice:
  - Escalation pathways are highly customised (who gets the alarm, when it escalates, who gets the second notice, when it stops).
  - Rules are tuned continually to staffing, patients per nurse and time of day.
  - Crisis alarms go to the nurse immediately, while warning/technical alarms can be delayed, silenced or auto-corrected.
  — [Becker's Hospital Review](https://www.beckershospitalreview.com/healthcare-information-technology/5-technology-tools-for-reducing-alarm-fatigue.html)
- Alarm-fatigue patents: patient information adjusts an alarm's sub-priority (e.g. the same alarm is H2 for an adult, H1 for a dehydrated neonate). Escalation-timing rules move an alarm from one sub-priority to the next, and vital signs can adjust priority — [USPTO 11380186](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11380186); [USPTO 11763659](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11763659)
- Vendors: Ascom "advanced alarm filtering" with clinical rules, thresholds and early-warning scores; PerfectServe "Dynamic Intelligent Routing" with escalation policies so urgent alerts are handled within set timeframes — [Ascom guide](https://www.ascom.com/globalassets/ahp/animations_ahp_2023/smart-alarm-management-buying-guide.pdf); [PerfectServe](https://www.perfectserve.com/blog/fight-alarm-fatigue-nurse/)
- Evidence (secondary): customising alarm parameters cut alarm load by 43%, nurses responded more when load fell, and sensitivity/specificity didn't drop — [Scribd action plan](https://www.scribd.com/document/420459926/An-action-Plan-pdf)
- Restaurant analogue: Presto forecasts a "guest experience score" from host availability, wait time and bounce — [BusinessWire](https://www.businesswire.com/news/home/20191016005058/en/)

### Inferences
**Proposed Easy FnB urgency score (0–100), recomputed every ~5 s per table**

```
lateness   = clip( time_in_state / Q_p75(state | party, daypart, venue_type), 0, 3 )   # context-normalised (Q2)
hazard     = P(needs service within 60 s | features)          # once a survival model exists; else 0
event      = max(hand_raised*1.0, bill_requested*0.9, new_table_unattended*0.8,
                 complaint_cue*1.0, empty_glasses*0.4, empty_plates_buffet*0.4, broth_low*0.5,
                 finished_no_bill*0.5, dirty_vacant*0.6*waitlist_factor)
staff_damp = exp(-t_since_last_staff_visit_s / τ) * (staff_within_1.5m ? 1 : 0)        # suppress if staff is there/just left
value      = 1 + 0.3*VIP_or_regular + 0.2*large_party + 0.2*waitlist_pressure
score      = 100 * sigmoid( w1*lateness + w2*hazard + w3*event - w4*staff_damp + b ) * value
```

- **Tiers**:
  - P1 "crisis" (hand raised, unattended new table > p90, suspected walk-out): push to the nearest free staff immediately, escalate to the manager after 60–90 s unacknowledged.
  - P2 (bill requested, food waiting at pass, dirty table with waitlist): push to the assigned section server.
  - P3 proactive (refills, empties, check-back): batch into the server's "next round" list, never as a buzz. This avoids alarm fatigue.
- **Fatigue controls**: per-staff rate limit, de-duplication (one active alert per table per need), hysteresis (the state must persist across 2–3 detections or 5–10 s before alerting), and acknowledge/snooze buttons. Log acknowledgements as labels for learning.
- **Weights**:
  - Start hand-set by the owner (rule-based, explainable).
  - Then learn from logs: target = "staff attended within X s and guest outcome good" (no complaint, tip/rating, re-visit). Use logistic regression or pairwise ranking (which table did the manager pick first).
  - Keep the weights explainable for the demo ("T7: 2.1× slower than usual greet for a party of 4 at dinner").
- **Assignment**: with multiple staff and alerts, greedily assign by `score / (walking_distance + ε)` or solve a small assignment problem (Hungarian) every few seconds.

### Gaps
- No published validated urgency framework for restaurant floor service, or retail customer-assistance prioritisation, was found. The design above is an analogy-based proposal.
- No primary peer-reviewed source for the 43% alarm-load reduction was retrieved; it's secondary.

---

## 7. Practical recommendations: 48-hour build (zero training data) vs. a few days of data vs. production

### Takeaway
In 48 hours, build a robust rule + geometry tracker (people/staff/tableware per table polygon). Add Gemini Flash JSON-schema classification of table crops on events or every 15–60 s. Put a priority score on top, with thresholds seeded from service standards and scaled by party size/daypart. That alone beats "5-minute fixed timer" and demos "AI understands the meal phase". With 3–7 days of logged data, replace priors with per-restaurant quantiles, fit a simple survival/GBM model for time-to-next-event and time-to-free, and fine-tune a small detector/classifier on auto-labelled crops (VLM as teacher). Production moves VLM inference partly on-edge (Gemma 4 E4B / PaliGemma 2) for cost and privacy.

### Cited Findings
- Existing CCTV + table-zone polygon mapping + target time is the industry setup pattern (no new hardware) — [FlowLinks](https://www.flowlinks.ai/restaurants-cafes/table-turnover); [SciForce](https://www.sciforce.solutions/case-studies/computer-vision-restaurant-service-optimization)
- Centroid-in-polygon geometry with YOLOv8+SORT is robust in crowded scenes — [PETI](https://ojs.imeti.org/index.php/PETI/article/download/15704/1856). YOLOv11 + pose separates seated guests from standing staff — [chrono-dine](https://github.com/Mashood-Basharat/chrono-dine)
- Gemini structured detection/segmentation output with JSON schema; a 258-token cost for ≤384 px crops; video at configurable fps; Live API at 1 FPS / 768×768 — [Gemini image](https://aistudio.google.com/docs/image-understanding); [Gemini video](https://aistudio.google.com/docs/video-understanding); [Live API](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/live-api/send-audio-video-streams)
- Cold start with partial features, then retrain; dark-launch before exposing predictions — [Yelp Engineering](https://engineeringblog.yelp.com/2019/12/architecting-wait-time-estimations.html)
- Linear regression is adequate for turn-time and survival models give incremental gains, so start simple — [Penn State Pure](https://pure.psu.edu/en/publications/using-survival-modeling-for-turn-time-predictions-in-foodservice-/)
- A Random Forest on POS history can bin hotpot dining time (short/normal/long/too long) — [ACM DL](https://dl.acm.org/doi/fullHtml/10.1145/3594300.3594303)
- Permissive licences for a commercial path: RF-DETR N–L Apache 2.0; Gemma 4 Apache 2.0 (secondary); PaliGemma 2 Gemma licence; Ultralytics AGPL-3.0/Enterprise — [Roboflow](https://roboflow.com/model-licenses/rf-detr); [emelia.io](https://emelia.io/hub/gemma-4-open-source-guide); [HF PaliGemma 2](https://huggingface.co/google/paligemma2-3b-mix-448/blob/main/README.md); [Ultralytics](https://docs.ultralytics.com/)
- Privacy pattern: abstracted entities, no PII, 30-day deletion — [BusinessWire Presto](https://www.businesswire.com/news/home/20191016005058/en/)

### Inferences
**48-hour plan (team of 4)**
1. *Perception (AI lead, ~16 h)*:
   - Pretrained COCO detector (RF-DETR-S/M Apache, or YOLO11/26 for speed in the demo) gives person, cup, wine glass, bowl, dining table, cell phone, handbag, backpack. These are COCO classes.
   - ByteTrack/DeepSORT tracking. Hand-drawn table polygons per camera.
   - Staff = uniform-colour histogram classifier or "standing + moving between tables" heuristic.
   - Optional pose (YOLO-pose / MediaPipe) for hand-raise and standing-up.
2. *Event engine (~8 h)*:
   - Per-table finite-state machine with hysteresis: guards on N consecutive frames, minimum dwell 5–10 s.
   - Transitions from geometry (persons seated in polygon), staff-in-zone dwell > 10 s (counts as a visit), POS webhook (order placed / bill printed / paid; mock it if no POS), and tableware count deltas (food arrived = sudden +k bowls/plates).
3. *VLM verification (~8 h)*:
   - On every candidate transition, plus a heartbeat every 30–60 s, send the table crop (≤384 px → 258 tokens) to Gemini Flash with a strict JSON schema of cues (Q1).
   - Use the VLM to confirm or veto ambiguous transitions (eating vs. finished, needs_clearing vs. guests stepped away) and to emit proactive cues (empty glasses, empty buffet plates, bill folder).
   - Cache, rate-limit, and show the VLM's one-line rationale in the UI for the "AI wow".
4. *Smart thresholds + urgency (~6 h)*: Q3 table priors × context multipliers (party size via person count, daypart, venue type hotpot/buffet/casual, occupancy %) → Q6 score → tiered alerts to a staff mobile/web view. Firebase/FCM fits the Google preference.
5. *Prediction demo (~4 h)*:
   - "Table free in ~N min" from phase-conditional heuristics: remaining = prior meal duration(party, daypart) − elapsed, clipped by phase (finishing → ≤10 min, wants_bill → ≤6 min, leaving → ≤2 min), shown as an interval.
   - Mark this as "will be learned per restaurant".
6. *Demo data*: record 20–40 min of staged footage (team members acting the phases at 2–3 tables) to replay deterministically. Live CCTV is risky.

**After 3–7 days of collected data**
- Per-restaurant duration quantiles by state × party × daypart (replace priors). Kaplan–Meier curves per state. A Weibull/Cox or XGBoost-AFT model for time-to-next-event, plus a GBM/RF for "time-to-free" (Thai hotpot study style) using POS features.
- **VLM-as-teacher auto-labelling**: run Gemini on thousands of crops, keep high-confidence labels, have humans spot-check ~5%. Train a small classifier (RF-DETR-seg/cls head, or fine-tune PaliGemma 2 "pt") for plate-full/empty, glass-empty, bill-folder, phase. This cuts API cost and latency.
- HSMM smoothing of phases and an evaluation harness: alert precision, lead time vs. staff-observed need, % tables greeted within target, false-alarm rate per staff-hour.
- Tune urgency weights from acknowledgement logs (which alerts staff acted on).

**Production path**
- Edge box (Jetson/NUC) running detector + tracker + FSM. VLM calls only on events. Optionally Gemma 4 E4B / PaliGemma 2 on-prem for privacy and offline resilience, with Gemini for hard cases.
- No face recognition by default. VIP/regular status comes from POS/loyalty or reservation, not faces. Short retention, blurred storage.
- Dark-launch every new model alongside rules (Yelp pattern), and roll out per restaurant.
- Multi-outlet benchmarking dashboards (FlowLinks/Presto feature parity) plus Vietnam-specific hotpot/buffet modules (pot set-up, refill rounds, time-limit "last order" alerts).

### Gaps
- Gemini API pricing, rate limits and latency for current Flash models weren't retrieved, so the cost per table-hour can't be computed in VND yet.
- Real-world accuracy of VLM verification on low-resolution, top-down, fisheye CCTV crops is unknown. A pilot evaluation is needed.
- Vietnam personal-data rules for CCTV analytics in restaurants weren't researched here; another researcher may cover them.
