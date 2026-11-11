# Verifying a camera event before alerting: VLM checks, multi-frame confirmation and human alarm-verification centres, applied to Easy FnB's Gemini step

Scope note: research done 5 Nov 2026. Sources are labelled **[VENDOR]** (company claims, marketing, or company-sponsored), **[INDEP]** (peer-reviewed, academic, standards body, government, or independent press), **[TRADE]** (security trade press, often repeating vendor or police anecdotes), or **[DOCS]** (official product documentation). Items older than 2023 carry their year. Every number below has a link. Where the link is only an abstract or summary page, I say so.

---

## Q1. Which verification designs work best in production, and what false-alarm reduction, latency and cost do they report? (vendor vs independent)

### Takeaway
Every industry I looked at uses the same design: **a cheap detector proposes an event → a second stage looks at a short clip around the event (not one still) → it returns three outcomes (confirmed / rejected / unverified), and "unverified" is downgraded, not dropped**. The second stage can be a human operator, a sequential second sensor, or now a VLM. Commercial vendors claim 90–95% false-alarm reduction, but these are vendor numbers measured against very noisy baselines (motion sensors, door alarms). **I found no independent benchmark of VLM-based alert verification**, and no published latency figures from NVIDIA or any vendor. The independent evidence is mostly about humans and policing, and it shows that human verification is itself imperfect.

### Cited Findings

**A. The human version: alarm-receiving / monitoring centres**
- [INDEP, US DOJ/COPS guide, 2nd ed. c.2011, data c.2002] 94–98% of police burglar-alarm calls are false (higher in some jurisdictions). In 2002 there were about 36M activations at about $1.8B police cost, and false alarms were 10–25% of all police calls — [Sampson, POP Center "False Burglar Alarms" 2nd ed.](https://popcenter.asu.edu/sites/default/files/problems/PDFs/false_alarms_2nded.pdf)
- [VENDOR, 2026] Securitas Technology says up to 98% of activations are not real incidents (no source given). Its video-verification workflow: (1) a sensor or camera triggers, (2) the operator gets **pre- and post-alarm clips or a live feed**, (3) the operator checks for a crime, (4) dispatch happens only after confirmation. In Securitas's own survey (4,540 clients, 17 countries, Nov 2024), 25% use video verification and 27% plan to within 12–18 months — [Securitas Technology 2026 blog (AU mirror)](https://www.securitas-australia.com.au/news2/blog-collection-securitas-technology-report-2026/verified-alarms-how-to-reduce-false-alarms-and-speed-response-in-2026/)
- [INDEP standard, TMA/ANSI] **TMA AVS-01 Alarm Validation Scoring** has 5 levels. 0 = no dispatch. 1 = call for service with limited or no extra information. 2 = confirmed or highly probable human presence. 3 = confirmed threat to property. 4 = confirmed threat to life. Operators score using video, audio, eyewitness and analytics data — [TMA AVS-01 presentation PDF (2024)](https://tma.us/wp-content/uploads/2024/06/AVS-01-Standard-Generic-Presentation.pdf); [Security Sales on AVS-01](https://securitysales.com/business/how-avs-01-is-permanently-changing-the-way-monitoring-centers-operate). Level 1 may get only a private-guard response, while Level 2+ may get public-safety dispatch — [Solink explainer [VENDOR]](https://solink.com/resources/industry-insights/alarm-validation-scoring/). The approval date is unclear: one source says ANSI-approved in Jan 2023, another says it was introduced in June 2024 — [Security Sales](https://securitysales.com/business/how-avs-01-is-permanently-changing-the-way-monitoring-centers-operate); [Rapid Response blog](https://www.rrms.com/?p=3172)
- [INDEP standard, UK] **BS 8243 sequential confirmation**: the first detector raises an "unconfirmed activation". A **second, independent detector within the confirmation time** (not less than 30 and not more than 60 minutes) produces a "sequentially confirmed activation". Detectors must use different technologies or not overlap — [BSI preview via ANSI webstore](https://webstore.ansi.org/preview-pages/BSI/preview_30411821.pdf). Under BS 8243:2021, sequential confirmation became **optional**: "any single or combination of confirmation method(s)" is permitted. The 2010 edition was withdrawn on 30 June 2022 — [NSI Technical Bulletin 0059](https://documents.nsi.org.uk/wp-content/uploads/2021/07/NSI-Technical-Bulletin-No.-0059-Publication-of-BS-8243_2021.pdf); [NSI news](https://nsi.org.uk/publication-of-british-standard-bs-82432021/)
- [INDEP standard, EU] CLC/TS 50131-9:2014 "Alarm verification – Methods and principles" has separate clauses on sequential verification for intruder and hold-up alarms. Alarm verification is also called "alarm confirmation". Verification done purely by the alarm-receiving centre's procedures is covered by EN 50518-3 — [iTeh catalog entry](https://standards.iteh.ai/catalog/standards/clc/d287cb4d-3500-4058-a715-4e48f99b5506/clc-ts-50131-9-2014). I could not read the full text (paywalled).
- [TRADE, 2013–2016] Police "priority response" to video-verified alarms: Charlotte-Mecklenburg enters only video-verified alarms as priority one. Reported response times fell from 39:25 to 2:54 (Salinas) and from 21 to about 7.6 minutes (Boston). These are anecdotal and early — [Security Today 2013](https://securitytoday.com/Articles/2013/10/01/Making-Video-Verified-Response-a-Priority.aspx); [Security Today 2016](https://securitytoday.com/Articles/2016/01/04/Alarm-Response.aspx)
- [VENDOR-sponsored, disputed] A Sonitrol-sponsored study claimed verified response cut police dispatches by 72%. The Security Industry Alarm Coalition disputed parts of it — [Security Sales](https://www.securitysales.com/fire-intrusion/verified-response-successful-in-controversial-study/) (page returned 403 to my fetch; the claim comes from the search snippet)
- [INDEP, 2015, peer-reviewed] **Human operators are not a perfect verifier.** In a 90-minute test with 42 working CCTV operators, detection was about 50% and false alarms were high. Novices and generalists showed a vigilance decline; specialists did not — [Donald, Donald & Thatcher, Applied Ergonomics 2015](https://ro.ecu.edu.au/ecuworkspost2013/922)
- [VENDOR] Deep Sentinel (AI plus live guards): the AI detects in 5–7 s, and a guard typically responds in 30–60 s ("commercially reasonable attempts") — [Deep Sentinel support](https://support.deepsentinel.com/hc/en-us/articles/1500000352621-Guard-Response-Time); the CEO claims under 30 s — [SecurityInfoWatch](https://www.securityinfowatch.com/video-surveillance/article/55294316/deep-sentinel-secures-15m-to-scale-ai-enabled-live-guard-monitoring-across-us)

**B. AI and VLM verification in commercial video security**
- [DOCS] **NVIDIA Metropolis VSS blueprint, Alert Verification.** The Alerts microservice takes an upstream CV alert, **fetches the video segment for the alert timestamp**, asks a VLM whether the alert is real, and stores a verdict of **confirmed / rejected / unverified** with a reasoning trace — [VSS Public Safety release notes](https://docs.nvidia.com/vss/latest/publicsafety-docs/Release-Notes.html). The default VLM is Cosmos Reason 2 8B, with cosmos-reason1-7b and qwen3-vl-8b-instruct as alternatives. Only the default is verified in local NIM mode (VSS 3.0.0 docs, from a search snippet; the page now returns 404). **Known issue: "occasional hallucinations in VLM reasoning" cause intermittent wrong verdicts** — [release notes](https://docs.nvidia.com/vss/latest/publicsafety-docs/Release-Notes.html)
- [DOCS] NVIDIA Warehouse blueprint alerting service:
  - In real-time mode the VLM sees **6-s chunks at 1 fps, 854×480**.
  - Output is strict JSON: `prediction_class_id` (0/1), `prediction_label`, `prediction_answer` (Yes/No), `video_description`.
  - `temperature: 0.0`.
  - An unparseable reply or a VLM, VST or network error gives **`verification-failed` and the original event is preserved**.
  - **No accuracy or latency numbers are published** — [NVIDIA alerting-service doc](https://docs.nvidia.com/vss/vision-agent/agent-workflows/industry-specific-examples/warehouse-operations-blueprint/microservice-configuration/alerting-service.md)
- [VENDOR] Ambient.ai claims 90–95% false-alarm reduction on access-control (PACS) alarms. ServiceNow: 240,831 alarms, 94% auto-cleared, 15,069 triage hours saved. VMware: alarms down more than 93% — [Ambient AI info](https://www.ambient.ai/ai-info); [Ambient press](https://www.ambient.ai/press/ambient-unveils-ambient-pulsar-reasoning-vlm). Its in-house reasoning VLM "Pulsar" is claimed to reach "81% accuracy on real-world threats at 50x the cost efficiency" and to beat GPT-5 and Gemini 2.5 Pro on security tasks. **No benchmark or method is published** — [Carahsoft summary](https://www.carahsoft.com/resources/28140-ambient-pulsar-the-reasoning-engine-powering-agentic-physical-security); [Ambient blog](https://ambient.ai/blog/introducing-ambient-pulsar-agentic-physical-security). Ambient argues that general frontier VLMs can read short segments but are too expensive for continuous use on thousands of streams (same blog). That fits the Easy FnB pattern of calling the VLM only on candidate events.
- [VENDOR] Actuate: "reducing false alarms by over 95%", no method — [Actuate](https://actuate.ai/solutions/false-alarm-reduction/). Lumana: "up to 90%"; its natural-language custom alerts pair its VIA-1 model with VLMs — [Lumana blog](https://www.lumana.ai/blog/how-ai-powered-video-analytics-cut-false-alarms-by-up-to-90). Calipsa: ">90%" in later factsheets but "cut in half" in 2017 customer trials, so the claims are inconsistent — [Calipsa factsheet](https://www.milestonesys.com/globalassets/marketplace/uploaded-assets/0010o00001kjeigqak/calipsa-overview-factsheet_2021_v2.pdf); [IFSEC 2017](https://www.ifsecglobal.com/tag/calipsa/). DeepAlert: ">70% vs conventional edge analytics" — [DeepAlert](https://www.deepalert.ai/news/how-does-ai-assist-with-false-alarm-reduction-in-video-and-alarm-monitoring/)
- [VENDOR/TRADE, 2026] Natural-language VLM alerts are now common:
  - Brivo "Eeva" for Eagle Eye VMS (Mar 2026) uses VLMs and plain-English rules — [Security Today](https://securitytoday.com/articles/2026/03/18/brivo-launches-natural-language-ai-video-agent.aspx)
  - Rhombus Custom Events use LLM-based detection, and customers can choose ChatGPT, Claude, Gemini or Grok — [Rhombus](https://www.rhombus.com/ai-insights/)
  - Verkada's Feb 2026 update was "designed to increase precision and reduce false positives" for AI-powered alerts, with no details or numbers — [Verkada update](https://www.verkada.com/updates/ai-powered-alert-improvements/)
  - Intel has an open-source "Live Video Alert Agent" (OpenVINO VLM, RTSP, natural-language prompts) — [Intel docs](https://docs.openedgeplatform.intel.com/2026.0/edge-ai-suites/live-video-alert-agent/index.html)
- [INDEP check] I found **no IPVM (or other independent) test of VLM alert verification**. The only IPVM hit was an older Verkada intrusion-alarm test — [IPVM](https://ipvm.com/reports/verkada-alarms-test) (paywalled)

**C. Detector→verifier research from other fields (closest quantified analogues)**
- [INDEP, arXiv Dec 2025] Medical endoscopy, "AdaptiveDetector": YOLOv11 detector plus a VLM verifier fine-tuned with GRPO using an **asymmetric, cost-sensitive reward that penalises misses**. Recall rose 14–22 percentage points over YOLO alone, while precision stayed within −0.7 to +1.7 points. This was tested on synthetically degraded images (blur, lighting, occlusion) — [arXiv 2512.12492](https://arxiv.org/abs/2512.12492) (abstract only)
- [INDEP, arXiv 2026] Aerial person tracking: a lightweight verifier stage after the detector cut false positives on person-free footage a further 2.1–3.4×, at under 0.05 ms per frame, with ROC AUC 0.941 — [arXiv 2607.16282](https://arxiv.org/pdf/2607.16282) (from the search snippet)
- [INDEP, thesis] UAV vehicle detection: YOLO plus a VLM verifier cut false positives in bad weather, **but the verifier sometimes rejected true positives** — [DiVA degree project](https://www.diva-portal.org/smash/get/diva2:2001940/FULLTEXT01.pdf)
- [INDEP] Elder-care fall detection:
  - A pretrained VLM used zero-shot reached 92.5% accuracy with 3 false positives on non-fall videos; few-shot calibration reached 100%. The test set was small — [Univ. Hertfordshire](https://researchprofiles.herts.ac.uk/en/publications/visionlanguage-model-for-fall-detection-in-socially-assistive-rob/)
  - In the TigerPlace (Univ. Missouri) thesis, second-stage deep models reduced false alarms, adding YOLOv5 cut them about 11% more, but false alarms persisted — [MoSpace thesis](https://mospace.umsystem.edu/items/89b590ac-ac77-4efd-99bf-2819db9f0f68)
- [INDEP] Classroom hand-raising (the closest gesture analogue): the SCB dataset reports heavy occlusion between students and **several action classes that look very similar to hand-raising**. YOLOv7 reached up to 85.3% mAP — [SCB-dataset arXiv 2304.02488 (2023)](https://ar5iv.labs.arxiv.org/html/2304.02488). The SAV dataset (2024) covers up to 68 students per class; hands are hidden by desks or the front row — [arXiv 2409.00926](https://arxiv.org/pdf/2409.00926). A pose-plus-LSTM method is view-invariant and occlusion-robust (36 real classroom videos) — [Bühler et al., AIED 2023](https://ecrhub.org/publications/automated-hand-raising-detection-classroom-videos-view-invariant-and-occlusion-robust)
- [VENDOR/PoC] Restaurant waiter-call gesture:
  - The eKonobar Vision PoC (MediaPipe on IP cameras) found that the main difficulty was **separating the call gesture from other movement in busy scenes** — [Pangea case study](https://pangea.ai/agencies/boopro-technology/case-studies/ekonobar-vision-case-study)
  - Wobot claims posture-based "wants to order" alerts — [Wobot](https://wobot.ai/blog/dine-in-glossary-wait-times)
  - Sciforce tracked table status (seating, waiter approach, cleanup) for a chain of about 1,200 locations — [Sciforce](https://www.sciforce.solutions/case-studies/computer-vision-restaurant-service-optimization)
  - None of these publishes accuracy.

### Inferences
- The proven pattern is **detector → time window → second opinion on a short clip → three outcomes**. Easy FnB already has detector → one crop → Gemini → two outcomes. The biggest structural gaps are (a) **one frame instead of a short pre/post window** (every monitoring centre and NVIDIA use clips) and (b) **no explicit "unverified" state**.
- The 90–95% vendor numbers are measured against raw motion or door-forced alarms, which are around 98% false. A YOLO-pose "hand up" detector starts far cleaner, so Easy FnB should expect a much smaller relative gain from Gemini. It should measure that gain on its own labelled clips rather than quote vendor figures.
- Human verification detects only about 50% of targets in lab vigilance tests (Donald 2015), and NVIDIA lists hallucination as a known issue. So the VLM step should be presented as "reducing noise", never as "ground truth". Keep the staff "dismiss" button as the real final verifier.
- The AdaptiveDetector result shows a verifier can also be tuned to **recover recall** with a cost-sensitive objective. That matters for "call" alerts, where a miss (an ignored guest) costs more than a false alarm (a staff member walks over).

### Gaps
- No independent (IPVM or academic) measurement of false-alarm reduction from VLM alert verification on real CCTV was found. IPVM is paywalled.
- No vendor or NVIDIA latency figures for VLM verification (p50/p95) were found.
- I could not read the exact clause text of BS 8418 / BS 8243 / CLC/TS 50131-9 / UL 827B / EN 50518 (all paywalled). I found nothing citable on UL 827B or CSAA AVS-01 measured false-alarm rates beyond the standard's level definitions.
- Coram, Spot AI, Genetec, Milestone, Twelve Labs, Chooch ImageChat and Google Vertex AI Vision: no verification-specific numbers were found in this pass.

---

## Q2. How reliable are VLM yes/no judgements on single CCTV crops vs short clips vs annotated frames? Known failure modes

### Takeaway
VLM yes/no answers have a known **"yes" bias** and object hallucination, especially for objects that usually appear together (dishes on tables). **Self-reported (verbalised) confidence is poorly calibrated.** In small VLMs it can be nearly constant (about 0.9) whether the answer is right or wrong. Gemini 3.x no longer returns logprobs, so Easy FnB's "reject if confidence ≥ 0.6" rule rests on a weak signal. Small subjects, top-down or oblique views, and low light all hurt accuracy. More frames do not automatically help. Temporal context helps when the action looks the same as other actions in a single frame (like a hand raised vs stretching), and marking a target in context can beat cropping it out.

### Cited Findings
**Yes-bias and hallucination**
- [INDEP, Findings ACL 2026] VLMs show a "yes-bias", answering yes indiscriminately. It traces to system-modality attention in late decoder layers, and redistributing that attention suppresses it — [arXiv 2601.12430](https://arxiv.org/abs/2601.12430)
- [INDEP, 2023/24] HallusionBench measures yes/no bias with "Yes Percentage Difference" and a false-positive ratio — [arXiv 2310.14566](https://arxiv.org/pdf/2310.14566)
- [INDEP, EMNLP 2023] POPE: LVLMs hallucinate objects not in the image, especially objects that **appear often in training data or usually co-occur with objects in the image** — [arXiv 2305.10355](https://arxiv.org/abs/2305.10355). This is relevant to "leftover dishes on the table".
- [INDEP, ACM MM 2025] Models give confident answers even without relevant images (language priors), and a calibration step helps — [arXiv 2403.05262](https://arxiv.org/pdf/2403.05262v3)

**Confidence and calibration**
- [INDEP, 2024] LLMs and VLMs are overconfident most of the time when asked to state their uncertainty — [Groot & Valdenegro-Toro, arXiv 2405.02917](https://arxiv.org/pdf/2405.02917)
- [INDEP, EMNLP 2025] Miscalibration is widespread across VLMs. "Visual Confidence-Aware Prompting" (two-stage) improves calibration, and visual-reasoning models are better calibrated — [arXiv 2505.20236](https://arxiv.org/abs/2505.20236)
- [INDEP, arXiv Jul 2026] Test on Qwen2-VL-2B and SmolVLM:
  - Qwen2-VL's **stated confidence stayed at 0.87–0.90 in every condition**, and its error-detection AUROC was around 0.5 (chance).
  - Its **internal token-probability confidence reached AUROC 0.92–0.99**.
  - **Severe low light** dropped accuracy from 0.99 to 0.22 while both confidence signals barely moved.
  - Recommendations: do not defer on stated confidence, use token probability, and **add an image-quality check upstream** — [Ferdous, arXiv 2607.22034](https://www.alphaxiv.org/abs/2607.22034.md)
- [INDEP, ICML 2026 position] Verbalised confidence is "testimony, not measurement". In their probe, Claude Sonnet 4.6's confidence stayed near ceiling under mild image degradation — [ICML 2026](https://icml.cc/virtual/2026/77435)
- [Community/Google staff, 2026] Gemini 3.x models no longer return `logprobs` ("currently WAI, logprobs are no longer returned for 3.X models"), and the newer Interactions API does not expose them — [Google AI forum](https://discuss.ai.google.dev/t/missing-logprobs-support-in-the-newest-gemini-models-3-1-pro-3-6-flash-on-vertex-ai-and-ai-studio/176557); [Interactions API thread](https://discuss.ai.google.dev/t/missing-logprobs-support-in-next-gen-interactions-api-generationconfig-2/144837). This is not stated in official docs, so treat it as unconfirmed.

**Small subjects, crops, viewpoint**
- [INDEP, ICLR 2025] MLLM accuracy is "very sensitive to the size of the visual subject", and the effect is causal. The models still attend to the right region when they answer wrongly, and training-free "look closer" interventions improve accuracy on 7 VQA benchmarks — [arXiv 2502.17422](https://arxiv.org/abs/2502.17422)
- [INDEP, ICCV 2023] A drawn **red circle** directs a VLM to a region **while keeping the context a crop throws away**. It was the best marker tested for localisation. Caveat: a red circle made the model more likely to describe the person as a "criminal" or "missing person" — [Shtedritski et al.](https://openaccess.thecvf.com/content/ICCV2023/html/Shtedritski_What_does_CLIP_know_about_a_red_circle_Visual_prompt_ICCV_2023_paper.html)
- [INDEP, 2023] Coarse boxes and circles include noisy pixels, and segmentation-mask markers work better — [Fine-Grained Visual Prompting, arXiv 2306.04356](https://arxiv.org/pdf/2306.04356.pdf). ViP-LLaVA answers questions about "the person marked with the red arrow" or box — [par.nsf.gov PDF](https://par.nsf.gov//servlets/purl/10521933)
- [INDEP, NeurIPS 2026 poster] TDBench: VLMs are trained mostly on front views. In top-down images objects are small and depth cues weak, and accuracy across 60 VLMs drops 15–26 points under a rotation-consistency test — [arXiv 2504.03748](https://arxiv.org/abs/2504.03748v2). This is relevant to ceiling-mounted CCTV. I found no benchmark specific to oblique ceiling views of human actions.
- [INDEP, NeurIPS 2025 workshop] Zero-shot VLMs on UCF-Crime and RWF-2000: few-shot examples help some models but **"may increase false positives"**. Models handle simple, spatially obvious events and struggle with noisy spatial cues — [arXiv 2510.23190](https://arxiv.org/abs/2510.23190) (abstract only)

**Single frame vs clip**
- [INDEP, 2025] VisualActBench: for LLaVA-OV, going from 2 to 16 frames **lowered** F1 on single-event videos — [arXiv 2512.09907](https://arxiv.org/pdf/2512.09907)
- [INDEP] Many MVBench tasks can be solved from one frame (cited in TEMPCORE) — [arXiv 2509.01167](https://arxiv.org/pdf/2509.01167v2). A 2026 paper defines "multi-frame gain" as accuracy with all frames minus accuracy with one frame, a useful test design — [arXiv 2607.12304](https://arxiv.org/pdf/2607.12304)
- [INDEP, 2024] ActionAtlas: domain-specific actions "may appear identical in a single frame but become identifiable across multiple frames". The best model (GPT-4o) scored 45.52% — [arXiv 2410.05774](https://arxiv.org/html/2410.05774v3)
- [INDEP, 2024] IG-VLM: **tiling several frames into one image grid** and giving it to an image VLM beat existing methods on 9 of 10 zero-shot video-QA benchmarks — [arXiv 2403.18406](https://arxiv.org/abs/2403.18406)

**Video anomaly detection (VAD) with VLMs (background; these detect "abnormal vs normal", not service calls)**
- LAVAD (CVPR 2024): training-free. It captions frames, then an LLM aggregates over time and scores anomalies on UCF-Crime and XD-Violence — [arXiv 2404.01014](https://arxiv.org/abs/2404.01014v1)
- VERA (CVPR 2025): keeps the VLM frozen and **learns the guiding questions in the prompt** using only coarse video-level labels — [arXiv 2412.01095](https://arxiv.org/html/2412.01095v3)
- Holmes-VAD (2024): a fine-tuned multimodal LLM that explains anomalies — [arXiv 2406.12235](https://arxiv.org/abs/2406.12235v2)
- AnomalyRuler (ECCV 2024): rule induction then rule-based reasoning with an LLM — [arXiv 2407.10299](https://arxiv.org/pdf/2407.10299)
- Vad-R1 (NeurIPS 2025): perception-to-cognition chain-of-thought plus an RL method (AVA-GRPO). It claims to beat open and proprietary models — [NeurIPS 2025](https://neurips.cc/virtual/2025/poster/119777); Vad-R1-Plus (Jan 2026) — [emergentmind](https://www.emergentmind.com/papers/2601.10165)
- [DOCS] NVIDIA VSS lists VLM hallucination as a known source of wrong verdicts — [release notes](https://docs.nvidia.com/vss/latest/publicsafety-docs/Release-Notes.html)

### Inferences
- **Easy FnB's current threshold ("retract the call if Gemini rejects with confidence ≥ 0.6") rests on verbalised confidence**, which the 2024–2026 literature says carries little information, and Gemini 3.x gives no logprobs to replace it. A **categorical verdict with an explicit UNCERTAIN class**, plus an evidence checklist and an image-quality field, is a better gate than a numeric threshold.
- Yes-bias works in different directions for the two checks:
  - "Is this guest calling?": a yes-biased model tends to **confirm** false calls, so it helps recall but not precision.
  - "Does this table need clearing?": co-occurrence hallucination ("restaurant table → dishes") tends to produce false "needs clearing".
  - Wording questions so that "yes" is not always the alert answer (ask for a state from an enum instead of yes/no) reduces this bias.
- A **hand raised to call is ambiguous in one frame** (stretching, fixing hair, holding a phone up, toasting, pointing while talking, a staff member reaching up), which is exactly the ActionAtlas and SCB "visually similar classes" problem. A short sequence (raised and held, or waved) is what separates them, so a 3–4 frame grid is likely worth more than a higher-resolution single crop. **Table clearing is a static state**: the frames add little, but resolution and context (whole table, nearby people, personal belongings) matter more.
- With ceiling or oblique views plus small subjects (TDBench, ICLR 2025 size effect), very small crops should be upscaled and padded with context, or the full frame should be sent with a marker on the target.

### Gaps
- I found no study that directly compares one crop vs crop+context vs multi-frame vs marked frames **for gesture or hand-raise verification on CCTV**. Easy FnB would need to measure this itself.
- I found no published calibration study for Gemini 3.x / 3.5 Flash-Lite verbalised confidence specifically.
- I found no benchmark of VLMs on oblique ceiling-camera views of people specifically. TDBench is top-down imagery in general.

---

## Q3. Practical prompt and input designs that raise precision without losing recall

### Takeaway
Production designs converge on these rules:
- a **strict JSON schema with fixed labels**
- **written criteria plus explicit exclusions (negative cues)**
- **temperature 0**
- **per-entity reasoning** (one person, one table)
- a **short clip or frame strip** instead of one still
- a small labelled set (10–50 clips, half positive) to iterate the prompt

Gemini adds cheap levers: **per-part media resolution** (high-detail crop plus low-detail context), **video frames at about 70 tokens each**, and **box_2d output** for grounding.

### Cited Findings
- [DOCS] NVIDIA's prompt recipe for VLM verification:
  - role line ("You are an expert Industrial Safety Inspector…")
  - criteria, exclusions and edge cases written into the prompt
  - fixed output labels with a consistency line
  - **per-entity accounting** (the PPE rule must cover each worker's head and torso individually and forbids group statements)
  - **counterfactual "freeze test"** for near-miss events
  - `temperature 0.0`
  - Tuning loop: write a use-case brief, test on **10–50 labelled clips, half positive and half negative**, **add missed negative cues to the exclusion list**, and sharpen the criteria for false negatives. Light fine-tuning only if that is not enough — [NVIDIA alerting service](https://docs.nvidia.com/vss/vision-agent/agent-workflows/industry-specific-examples/warehouse-operations-blueprint/microservice-configuration/alerting-service.md)
- [DOCS, Gemini] Media resolution (Gemini 3 / 4 families):
  - Images: low = 280, medium = 560, high = 1120, ultra_high = 2240 tokens (unspecified default = 1120)
  - **Video: 70 tokens per frame at low/medium/default, 280 at high**
  - Resolution can be set **per media item**, for example high for the important image and low for a context image
  - Docs recommend `high` for most image analysis, `low` for cost/latency, and low/medium for general video action recognition — [Gemini media resolution](https://aistudio.google.com/docs/media-resolution)
- [DOCS, Gemini] Image understanding:
  - up to 3,600 images per request
  - 20 MB inline limit
  - **object detection returns `box_2d` as [ymin, xmin, ymax, xmax] normalised 0–1000**
  - structured JSON via a schema
  - for segmentation, set thinking to "minimal"
  - the fetched summary says to place the text prompt before the single image (not verified against the raw page) — [Gemini image understanding](https://aistudio.google.com/docs/image-understanding)
- [DOCS, Gemini] Video understanding:
  - inline video under 20 MB per request
  - default sampling 1 fps, adjustable with `fps` in `processing` (static mode)
  - clipping with `start_offset`/`end_offset`
  - low resolution costs about 100 tokens/s (66 per frame plus 32 for audio, so strip the audio track)
  - for a single video, put the text prompt *after* the video part
  - "agentic" processing is for long videos; use static mode for clips under 5 minutes
  - gemini-3.5-flash-lite is listed among models supporting agentic video — [Gemini video understanding](https://aistudio.google.com/docs/video-understanding). The image and video pages disagree on prompt placement.
- [DOCS, Gemini] Thinking: `gemini-3.5-flash-lite` defaults to **minimal** thinking (levels: minimal/low/medium/high). Minimal is recommended for simple classification. Thinking tokens are billed as output. Setting a small `max_output_tokens` can truncate the reply while still billing thinking tokens — [Gemini thinking](https://aistudio.google.com/docs/thinking)
- [INDEP] IG-VLM frame grid in one image — [arXiv 2403.18406](https://arxiv.org/abs/2403.18406). Red circle or marker in the full frame keeps context — [ICCV 2023](https://openaccess.thecvf.com/content/ICCV2023/html/Shtedritski_What_does_CLIP_know_about_a_red_circle_Visual_prompt_ICCV_2023_paper.html). Set-of-Mark prompting puts numbered marks on regions so the model can refer to them by ID — [Yang et al. 2023, arXiv 2310.11441](https://arxiv.org/abs/2310.11441) (not re-fetched this session)
- [INDEP] VERA learns the *questions* in the prompt from coarse labels — [arXiv 2412.01095](https://arxiv.org/html/2412.01095v3). AnomalyRuler induces explicit rules from a few examples — [arXiv 2407.10299](https://arxiv.org/pdf/2407.10299). Visual Confidence-Aware Prompting (two-stage) improves calibration — [arXiv 2505.20236](https://arxiv.org/abs/2505.20236)
- [INDEP, 2022] Self-consistency: sample several reasoning paths and take the majority answer — [Wang et al., arXiv 2203.11171](https://arxiv.org/abs/2203.11171) (an LLM text paper, not VLM-specific). Each extra sample multiplies cost.
- [INDEP] Few-shot exemplars can raise false positives for some VLMs — [arXiv 2510.23190](https://arxiv.org/abs/2510.23190). But few-shot calibration lifted fall detection from 92.5% to 100% in a small test — [Hertfordshire](https://researchprofiles.herts.ac.uk/en/publications/visionlanguage-model-for-fall-detection-in-socially-assistive-rob/). The evidence is mixed.
- [INDEP] Add an image-quality gate, because confidence does not drop when low light destroys accuracy — [arXiv 2607.22034](https://www.alphaxiv.org/abs/2607.22034.md)
- [DOCS/INDEP, persistence] Axis's "short-lived object filter" does not report an object until it has persisted for a set time, which suppresses headlights and shadows — [Axis troubleshooting guide (3rd-party)](https://scos.co.uk/troubleshooting/axis/axis-motion-detection-too-sensitive). Loitering analytics always use a delay: a short delay floods operators with false alerts, a long delay may miss rare real events — [IPVM forum](https://ipvm.com/forums/video-surveillance/topics/loitering-analytics). Older classroom hand-raise work reportedly used **how often the raised hand was detected over previous frames** to filter false positives — [MVA 2013 proceedings (unverified which paper)](https://www.mva-org.jp/Proceedings/2013USB/papers/04-07.pdf)

### Inferences (prompt and input design for Easy FnB)
1. **Inputs ("call" check)**:
   - **Image A**: a 2×2 (or 1×4) **frame strip** of the person crop over the last about 2 s, for example t−1.5 s, t−1 s, t−0.5 s, t. Pad the box about 30% for context, label each tile with its time, and optionally draw the YOLO-pose skeleton on the last tile only. Media resolution **medium**.
   - **Image B**: the **full frame or table zone** at **low** resolution, with a **red box or outline around the target person** and the table ID drawn in. This adds context (is the person standing as staff, is a waiter already there, which table).
   - Alternative to Image A: a 2-s MP4 at 2 fps with audio removed. That is about 4×70 tokens, cheapest, but each frame is low detail.
2. **Inputs ("needs clearing" check)**: one **whole-table crop at medium or high** (dishes are small objects, and the ICLR 2025 size effect applies) plus a low-resolution context frame. Optionally add the table crop from when the guests sat down or when it was last cleared, so the model can compare (a "what changed" prompt). Frames over time matter less here.
3. **Ask for a state, not yes/no.** Have the model fill an **evidence checklist before the verdict**, list alternatives explicitly, and include an UNCERTAIN class:
   - Call example: `verdict ∈ {GOI_PHUC_VU, KHONG_GOI, KHONG_CHAC}`; `alt ∈ {vuon_vai, chinh_toc, cam_dien_thoai, nang_ly_chuc_mung, chi_tay_khi_noi_chuyen, an_uong, nhan_vien, tre_em_choi, none}`; `hand_above_head: bool`; `held_or_waved_across_frames: bool`; `looking_toward_staff_or_aisle: bool`; `wearing_staff_uniform: bool`; `image_quality ∈ {ok, toi, mo, bi_che, qua_nho}`.
   - Clearing example: `table_state ∈ {TRONG_SACH, TRONG_CAN_DON, CO_KHACH, KHACH_RA_NGOAI_TAM, KHONG_CHAC}`; `items ∈ [chen_dia_ban, ly_chai, khan_giay_rac]`; `personal_belongings_present: bool` (bag, phone, jacket mean the guest is probably coming back, so don't clear); `people_within_1m: bool`.
4. **Write exclusions explicitly in the Vietnamese prompt** (NVIDIA's "negative cues"): stretching, adjusting hair or glasses, holding up a phone to take photos, toasting ("dô"), waving at a friend at the entrance, staff reaching up to shelves, children playing. Add every new false positive seen in testing to this list (NVIDIA loop).
5. **Per-entity rule**: "Only judge the person inside the red box. Do not infer from other people."
6. **Short output**: enums plus a reason of at most about 15 words. Output tokens cost about 8× input tokens on Flash-Lite (see Q5), so free-text reasoning is the costliest part.
7. Keep **temperature 0** (NVIDIA) and **thinking minimal** (the Flash-Lite default). For borderline cases (verdict KHONG_CHAC or a checklist that contradicts the verdict), optionally re-ask once with a different frame strip, i.e. 2-of-2 or 2-of-3 self-consistency, instead of trusting a confidence number.
8. **Few-shot**: be careful. One reference image of the **staff uniform** in the request is probably useful for staff vs customer, but full few-shot examples of calls and non-calls may raise false positives (arXiv 2510.23190). Test both on the labelled set.

### Gaps
- No public evidence specifically on whether **pose-skeleton overlays** help or hurt VLM gesture judgement. Needs an A/B test.
- The Gemini docs pages disagree on text-before vs text-after media placement. Test both.
- Whether the `box_2d` pointing output can make Gemini "show its evidence" (e.g. return the box of the raised hand or of the leftover dish) reliably on low-resolution CCTV is untested in the literature I found.

---

## Q4. Fail-open vs fail-closed: how do others decide?

### Takeaway
Mature alarm systems rarely use a binary pass/drop. They **downgrade**: an unverified alarm is still signalled, but at lower priority or with a different response. NVIDIA's VLM verifier keeps the original event, tagged `verification-failed`. AI-guardrail practice says to decide **per checkpoint by the cost of each error**, with graded fallbacks, a circuit breaker, and an explicit "unknown" state.

### Cited Findings
- [DOCS] NVIDIA VSS: a VLM error, VST timeout, missing video or unparseable reply produces **`verification-failed`, and the original event is preserved**, with the reason recorded in `info.verificationResponseCode/Status` — [NVIDIA alerting service](https://docs.nvidia.com/vss/vision-agent/agent-workflows/industry-specific-examples/warehouse-operations-blueprint/microservice-configuration/alerting-service.md). Verdicts: confirmed / rejected / unverified — [release notes](https://docs.nvidia.com/vss/latest/publicsafety-docs/Release-Notes.html)
- [INDEP standard] BS 8243: the first detector raises an **"unconfirmed activation"** (still signalled), and confirmation upgrades it — [BSI preview](https://webstore.ansi.org/preview-pages/BSI/preview_30411821.pdf). AVS-01: Level 1, "call for service with limited or no additional information", is still a call, just lower priority — [TMA presentation](https://tma.us/wp-content/uploads/2024/06/AVS-01-Standard-Generic-Presentation.pdf)
- [TRADE] Under verified-response policies, non-verified alarms get **lower police priority** rather than being ignored — [Security Today](https://securitytoday.com/Articles/2016/01/04/Alarm-Response.aspx)
- [Practitioner/VENDOR, 2026] AI guardrail design:
  - choose per checkpoint: fail-closed where downstream code acts on the output, fail-open with alerting for low-risk paths
  - degrade in steps (rules-only check → fixed reply → human handoff)
  - use **circuit breakers** so each request does not wait out a timeout — [iThome guide](https://ithelp.ithome.com.tw/articles/10409825)
  - "empty is not clean": when a check has no evidence, it must not count as passed — [DEV Community](https://dev.to/jeremy_longshore/empty-is-not-clean-five-fail-open-bugs-in-an-ai-agent-5fd8)
  - alerts should not close on partial or unavailable evidence — [NHI Mgmt Group](https://nhimg.org/articles/fail-open-ai-soc-design-is-changing-how-alerts-get-resolved/)
  - fail-open must still log the degraded decision and why — [DeepInspect](https://www.deepinspect.ai/blog/ai-gateway-fail-open-vs-fail-closed)

### Inferences
- **"Guest calling"**: a miss costs more (an unhappy guest waiting) than a false alarm (a waiter walks over). Keep **fail-open**, but make it a visible **third state** ("Chưa xác minh", shown in a different colour and icon), the same as NVIDIA's `verification-failed` and BS 8243's "unconfirmed activation". Add a **timeout of about 2–3 s and a circuit breaker**: after N consecutive Gemini errors, stop calling for 60 s and use the local rule fallback.
- **"Needs clearing"**: holding until confirmed is already a fail-closed choice, which is sensible because a delay of a few minutes costs little. On Gemini error, don't drop the alert forever. Downgrade to a **time-based fallback**: if the table zone has had no person for ≥ T minutes and the local leftover-items head is positive, show "Có thể cần dọn (chưa xác minh)".
- Log every decision with its path (confirmed / rejected / unverified-timeout / unverified-error / unverified-uncertain). These logs, plus staff "dismiss" taps, become the evaluation set.

### Gaps
- I found no published policy from a restaurant or hospitality CV vendor on fail-open vs fail-closed. The guardrail sources are opinion or vendor blogs, not standards.

---

## Q5. Concrete application to Easy FnB's Gemini step (what to send, prompt and schema, thresholds, multi-frame clip, local fallback), and effort before 14 Nov vs after

### Takeaway
Before the 14 Nov demo, the best changes are cheap and mostly prompt and plumbing:
- **k-of-n persistence on the edge** before calling Gemini
- **send a 4-frame strip plus a marked context frame** instead of one crop
- **switch the schema to enum verdict + checklist + image_quality + UNCERTAIN**, and drop the 0.6 verbalised-confidence threshold
- **three-state UI with fail-open "unverified"**
- a **50–100 clip labelled test** to show judges before/after precision and recall

My rough estimate is that this raises cost per call from about 10 to 15–16 VND (see Inferences). A local VLM fallback, fine-tuning and prompt optimisation are post-hackathon work.

### Cited Findings
- [DOCS] Gemini 3.5 Flash-Lite (`gemini-3.5-flash-lite`) pricing per 1M tokens:
  - Standard: **$0.30 input (text, image, video), $2.50 output including thinking**
  - **Batch: $0.15 / $1.25**; Flex: $0.15 / $1.25; Priority: $0.54 / $4.50
  - Context caching $0.03/1M plus $1.00/1M tokens per hour storage (not on the free tier)
  - Free tier: input and output free — [Gemini pricing](https://aistudio.google.com/docs/pricing)
- [DOCS] Token sizes (Gemini 3/4 table): image low 280 / medium 560 / high 1120; video frame 70 (low/medium) or 280 (high) — [media resolution](https://aistudio.google.com/docs/media-resolution). Default thinking for 3.5 Flash-Lite is minimal — [thinking](https://aistudio.google.com/docs/thinking)
- [Third-party, unverified] 3.5 Flash-Lite was released around 21 Jul 2026 at about 350 output tokens/s; no Google primary source was found — [Apidog](https://apidog.com/blog/what-is-gemini-3-5-flash-lite/)
- [DOCS] Docs also list newer `gemini-3.8-flash`, `gemini-3.6-flash` and "Gemini 4 Argon", which could be fallback or upgrade options — [video understanding](https://aistudio.google.com/docs/video-understanding)
- [Community] No logprobs on Gemini 3.x — [Google AI forum](https://discuss.ai.google.dev/t/missing-logprobs-support-in-the-newest-gemini-models-3-1-pro-3-6-flash-on-vertex-ai-and-ai-studio/176557)
- [DOCS/INDEP] Local small-VLM candidates and licences:
  - **Qwen3-VL-2B-Instruct**: Apache-2.0, 2B parameters, image and video input, "stronger 2D grounding", 98 quantised variants (llama.cpp, Ollama) — [HF model card](https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct)
  - **SmolVLM2**: 256M–2.2B, Apache-2.0, Feb 2025 — [Roboflow listing](https://playground.roboflow.com/models/hugging-face/smolvlm2). The smallest SmolVLM uses under 1 GB GPU memory — [SmolVLM paper arXiv 2504.05299](https://arxiv.org/html/2504.05299v1)
  - **Moondream 2**: Apache-2.0, about 2B parameters; Moondream 3 is Apache/BSL — [Roboflow](https://playground.roboflow.com/models/moondream-ai/moondream-2); [comparison](https://aiidelist.com/blog/on-device-vlm-comparison.md)
  - **Gemma 3n**: Gemma Terms (not Apache) — same comparison. Gemma 3n E4B needs about 4.5 GB at Q4_K_M (aggregator estimate) — [bestllmfor](https://bestllmfor.com/catalog/gemma3n-e4b/). Gemma 3 4B is about 3.4 GB at 4-bit (estimate) — [Roboflow compare](https://playground.roboflow.com/models/compare/gemma-3-4b-vs-smolvlm2)
  - At small model sizes, CPU-side image preprocessing and tokenisation often dominate latency — [arXiv 2603.16987](https://arxiv.org/html/2603.16987)
- [INDEP] Small local models expose token probabilities, and for Qwen2-VL-2B these are a far better error signal than stated confidence (AUROC 0.92–0.99 vs ~0.5) — [arXiv 2607.22034](https://www.alphaxiv.org/abs/2607.22034.md)
- [DOCS] NVIDIA recommends prompt tuning on 10–50 labelled clips first, then light fine-tuning of the VLM only if targets are missed — [NVIDIA alerting service](https://docs.nvidia.com/vss/vision-agent/agent-workflows/industry-specific-examples/warehouse-operations-blueprint/microservice-configuration/alerting-service.md)

### Inferences (recommendations; my own synthesis, not sourced facts)

**Cost check** (assumes about 26,000 VND/USD, about 500 prompt tokens since Vietnamese tokenises less efficiently, and about 60 output tokens):
- Current: input 280 (low crop) + 500 = 780 tokens = $0.000234; output 60 tokens = $0.00015; **total ≈ $0.00038 ≈ 10 VND**. That matches the user's "≈ 8 VND".
- **Output dominates.** Every 100 output tokens (e.g. a Vietnamese free-text reason) cost $0.00025 ≈ 6.5 VND, more than the whole image. Use enums and a short reason.
- Proposed "call" input: frame strip at medium (560) + context frame at low (280) + about 700 prompt tokens = 1,540 tokens = $0.00046; plus output 60 = $0.00015. **Total ≈ $0.00061 ≈ 16 VND**. With MP4 frames instead of the strip (4×70 = 280 tokens), **≈ 13 VND**.
- Re-asking only borderline cases (self-consistency) adds about 16 VND per borderline event.
- Offline evaluation through the Batch API halves the cost. The free tier is fine for development.

**Pipeline changes, in priority order:**
1. **Edge persistence (k-of-n) before calling Gemini.** For example, "hand above shoulder or head on the same tracked person in ≥ 6 of the last 10 pose frames (about 1–2 s)", with a per-person cooldown after an alert. This borrows the Axis short-lived filter, the classroom "frequency over previous frames" filter, and BS 8243 sequential confirmation (two independent signals inside a time window: the pose head plus the PE-Core/CLIP head, then Gemini as the third).
   - For **calls**, waiting longer only filters *transient* poses. It cannot tell *sustained* look-alikes (stretching, a phone held up, staff) from real calls. **That is where the VLM adds value**, so keep the persistence window short (≤ 2 s) to protect latency.
   - For **clearing**, waiting is cheap. Use a longer persistence (e.g. the table zone has no person for ≥ 60–120 s), then call Gemini once. Do not re-call on every frame.
2. **Ring buffer on the edge** (the last about 3 s of frames per camera, already in memory) so the event can carry a frame strip and a context frame.
3. **New request**: Image A (strip, medium) and Image B (marked full frame, low), using per-part resolution. Use the enum schema from Q3 with the Vietnamese exclusions list. Keep temperature 0 and thinking minimal.
4. **Decision rules in place of "confidence ≥ 0.6"**:
   - Call: **retract only if** `verdict = KHONG_GOI` **and** `image_quality = ok` **and** the checklist agrees (e.g. `hand_above_head = false` or `alt ≠ none` or `wearing_staff_uniform = true`). If `KHONG_CHAC` or quality is not ok, keep the alert as "Chưa xác minh".
   - Clearing: **show only if** `table_state = TRONG_CAN_DON` **and** `personal_belongings_present = false` **and** `people_within_1m = false`. `KHACH_RA_NGOAI_TAM` gives no alert; `KHONG_CHAC` gives a re-check after N minutes.
5. **Three-state UI and fail policy** (Q4): timeout about 2–3 s, circuit breaker, "Chưa xác minh" badge, and full logging.
6. **Staff vs customer**: add `wearing_staff_uniform` to the checklist and one fixed reference image of the restaurant's uniform (test it, since few-shot can backfire). Track staff IDs on the edge too, because Gemini should not be the only staff filter.
7. **Evaluation for the demo**: label 60–100 events from recorded footage (about half true, half false, including the hard negatives: stretching, phone, toasting, staff, a guest stepping away). Compare A = current single crop, B = crop + context, C = strip + context. Report precision, recall and cost per event. Use the Batch API or the free tier. NVIDIA's 10–50 clip guidance shows this sample size is normal practice for prompt tuning.

**Local fallback on the 4 GB RTX 3050** (it already runs YOLO26 and the PE-Core heads):
- VRAM is the constraint. Gemma 3n E4B (about 4.5 GB at Q4) does not fit alongside them, and Gemma 3 4B 4-bit (about 3.4 GB) is borderline.
- Realistic options: SmolVLM2-256M/500M (Apache-2.0, < 1 GB class) or Qwen3-VL-2B quantised (Apache-2.0; VRAM not measured in my sources). Or run the fallback on CPU only for rare Gemini outages.
- Advantage: local models give token probabilities, which are a real confidence signal (AUROC about 0.92–0.99 in the 2026 study), unlike Gemini 3.x.
- **For the 14 Nov demo, the rules-only fallback (persistence + "unverified" label) is enough. A local VLM is post-hackathon work.**

**Effort estimate (2 people, 9 days to the 14 Nov demo):**
- Must do (about 3–4 person-days total):
  - schema and prompt rewrite with enums, exclusions and an UNCERTAIN class (0.5 d)
  - edge k-of-n persistence and per-person cooldown (0.5 d)
  - ring buffer and frame-strip compositor with red-box context frame (1 d)
  - three-state UI, timeout and circuit breaker, decision logging (0.5–1 d)
  - labelling 60–100 events and an A/B/C evaluation script (1 d)
- Nice to have before the demo: the MP4-clip variant instead of the image strip (0.5 d); re-asking borderline cases (0.25 d); showing Gemini's short Vietnamese reason and `box_2d` evidence box on the staff app for judges (0.5 d).
- After the hackathon:
  - local VLM fallback with token-probability gating
  - fine-tuning a small verifier (Qwen3-VL-2B or SmolVLM2) on staff-feedback labels, as NVIDIA recommends after prompt tuning (licences are fine for non-commercial use)
  - cost-sensitive training that penalises missed calls, like AdaptiveDetector's asymmetric reward
  - VERA-style automatic prompt or question optimisation using the logged labels
  - Gemini context caching for a long fixed prompt plus reference images (check the minimum cacheable size first)
  - per-camera prompts for viewpoint differences
  - multi-camera confirmation (a second camera as the "independent detector", as in BS 8243)

### Gaps
- No measured Gemini 3.5 Flash-Lite latency (time to first token or end-to-end with images) from Google was found. Only a third-party throughput claim. Easy FnB should log p50/p95 itself.
- The minimum token size for Gemini explicit context caching on 3.5 Flash-Lite was not checked.
- I found no measured VRAM or latency for Qwen3-VL-2B, SmolVLM2 or Moondream on an RTX 3050 4 GB alongside other models. Benchmark locally.
- The token counts above assume 3.5 Flash-Lite follows the "Gemini 3/4" media-resolution table. The docs do not list 3.5 separately.
- I found no published accuracy figures for any restaurant hand-raise or table-clearing product, so there is no external baseline to compare Easy FnB against.
