# Bài toán tương tự ngành khác: phát hiện sự kiện hiếm của con người từ camera với rất ít báo nhầm (fall detection, bed-exit, CCTV anomaly) — bài học cho Easy FnB

Phạm vi: các bài toán "sự kiện hiếm, mỗi báo nhầm tốn sự chú ý của nhân viên, bỏ sót cũng có hại" ở chăm sóc người già, bệnh viện, an ninh CCTV, hồ bơi, lớp học, nhà hàng; cách họ giữ báo nhầm thấp; cách đánh giá; và cách Easy FnB mượn lại.
Ngày nghiên cứu: 5/11/2026. Ghi chú: phần lớn số liệu "giảm X% báo nhầm" là **vendor claim**; tôi đánh dấu rõ [VENDOR], [ĐỘC LẬP/PEER-REVIEWED], [PREPRINT], [CÓ XUNG ĐỘT LỢI ÍCH].

---

## 1. Fall detection bằng camera (chăm sóc người già/bệnh viện): giải ra sao, chạy thật tốt đến đâu

### Takeaway
Hệ thống fall-detection bằng video sống sót được ngoài đời (SafelyYou, Kepler Night Nurse, Inspiren AUGi) đều **không** dựa vào một model "đủ tốt": họ dùng AI nhạy (high-sensitivity) + một tầng xác minh (người ở call-center, hoặc logic tư thế/thời gian) + clip video để nhân viên tự xem. Số liệu độc lập hiếm và kém hơn nhiều so với vendor claim (ví dụ pilot Baycrest: 16/27 alert là ngã thật, bỏ sót ~20% ngã), trong khi model học thuật huấn luyện trên dữ liệu dàn dựng tụt mạnh khi gặp video thật (F1 ngã ~52–66% trên OOPS-Fall).

### Cited Findings
**SafelyYou (memory care, Mỹ) — kiến trúc AI + human-in-the-loop**
- Kiến trúc theo hồ sơ grant NIH: camera gắn tường phát hiện ngã tự động; hệ thống "identifies and pre-filters falls with high sensitivity", sau đó "a human who confirms the fall with high specificity"; người xác minh (HIL) "is operating from a call center, confirms the fall detection alerts"; một chuyên viên trị liệu nghề (OT) xem lại video ngã để đề xuất phòng ngừa. Thử nghiệm RCT dự kiến n=460. — [NIH grant abstract](https://api.ai-analytics.org/grant/nih/10020322)
- RCT đăng ký NCT03685240 (randomized wait-list control) — trạng thái "Unknown", không tìm thấy kết quả công bố. — [ClinicalTrials.gov NCT03685240](https://clinicaltrials.gov/study/NCT03685240)
- Pilot 2017 (JMIR, peer-reviewed nhưng [CÓ XUNG ĐỘT LỢI ÍCH]: tác giả sở hữu cổ phần/bằng sáng chế SafelyYou): 1 cơ sở memory care ở California, camera ở khu chung và 10/40 phòng ngủ, 3 tháng (7–9/2016), ghi được 16 cú ngã; tỷ lệ ngã giảm ở tháng cuối; chấp nhận tốt. Thiết kế quan sát, không đối chứng. — [Bayen et al., JMIR 2017](https://jmir.org/2017/10/e339)
- Pilot 2019 (AJMC) [CÓ XUNG ĐỘT LỢI ÍCH]: 6 cơ sở, 55 cư dân sa sút trí tuệ, 6–8/2018, không ngẫu nhiên. Nhóm chứng 147 cú ngã → 52 (35,4%) gọi EMT, 36 (24,5%) vào cấp cứu; nhóm can thiệp 83 cú ngã → 13 (15,7%) EMT, 7 (8,3%) cấp cứu. Bài báo **không** báo cáo số alert, false positive, sensitivity hay thời gian phát hiện — tức không đánh giá được hiệu năng phát hiện từ bài này. (Lưu ý: mức giảm tương đối "75%/80%" trong bài không khớp với tỷ lệ thô ~56%/66%.) — [AJMC 2019](https://www.ajmc.com/view/realtime-video-detection-of-falls-in-dementia-care-facility-and-reduced-emergency-care)
- **Đánh giá độc lập duy nhất tìm được** (Baycrest/CABHI, tóm tắt dự án giải thưởng 2018, không peer-reviewed): nhân viên nhận 27 alert, chỉ 16 là ngã thật ("very high false alarm rate, requiring staff to validate detected falls as true or false"); hệ thống bỏ sót ~20% cú ngã thật (mục tiêu 99%); nhưng video ghi được diễn biến trước cú ngã 81% số lần, giúp lâm sàng lập kế hoạch phòng ngừa. — [CABHI project page](https://www.cabhi.com/?p=21829) (lưu ý: tôi lấy các con số qua trích đoạn kết quả tìm kiếm; khi mở trực tiếp trang này chỉ hiện số liệu tổng quan CABHI, nên cần đối chiếu báo cáo đầy đủ)
- Vendor claim trái ngược: CEO SafelyYou nói hệ thống tạo "on the order of one false alarm per year" (bài phỏng vấn tài trợ) — [Senior Housing News](https://seniorhousingnews.com/?p=37035); một testimonial khách hàng (Carlton) ghi "1 false alert per camera every 19 days" — [Direct Supply PDF](https://www.directsupply.com/wp-content/uploads/2020/06/SafelyYou-Testimonial-Carlton.pdf) (con số lấy từ trích đoạn tìm kiếm; tôi không mở được nội dung PDF). [VENDOR]
- Press release: một nghiên cứu "NIH-sponsored" ở 11 cộng đồng memory care cho 41% ít ngã hơn và 69% ít lượt cấp cứu do ngã hơn — không có thiết kế/cỡ mẫu/thống kê trong release; không tìm thấy bản peer-reviewed. — [SafelyYou press release via AJMC](https://www.ajmc.com/press-release/safelyyou-new-research-reveals-safelyyous-aienabled-fall-detection-reduces-need-for-emergency-service-care-in-dementia-care-facilities) [VENDOR]
- Eskaton: 93% giảm lượt ER do ngã sau 3 tháng, nhưng chỉ 35 người ở 3 cộng đồng. — [PR Newswire](https://prnewswire.com/news-releases/safelyyou-helps-eskaton-reduce-er-visits-caused-by-dementia-related-resident-falls-by-93-300938829.html) [VENDOR]

**Kepler Vision Night Nurse (Hà Lan/EU)**
- Claim "loại bỏ 99% báo nhầm" (do mèo nhảy lên giường, rèm bay, gối rơi) so với cảm biến chuyển động, thảm giường, thiết bị đeo; CEO có lúc nói 99,9% / "nhỏ hơn 1000 lần". Không tìm thấy nghiên cứu độc lập nào. — [AI Business](https://aibusiness.com/verticals/kepler-vision-launches-edge-box-enabling-ai-to-watch-over-the-elderly); [HTWorld](https://new.htworld.co.uk/?p=5014) [VENDOR]
- Kiến trúc: một cảm biến quang + phần mềm chạy trên server on-premise hoặc nhúng trên camera (Mobotix C71, có "privacy mode" không truyền video); đăng ký thiết bị y tế EU tháng 10/2020; khách hàng: Domidep (Pháp), Oktober (Hà Lan); năm 2023 ra module phát hiện tư thế nằm (lying position). — [AI Business](https://aibusiness.com/verticals/kepler-vision-launches-edge-box-enabling-ai-to-watch-over-the-elderly); [Digital Health 2023](https://digitalhealth.net/2023/11/kepler-vision-technologies-unveils-new-lying-position-detection-module)

**Inspiren AUGi (senior living)**
- Paper hội nghị (Sun & Burke, 3 cơ sở assisted living, có tác giả thuộc Inspiren): giảm trung bình 64% ngã (p<0,01) và ngã có chấn thương (p=0,05); tự nhận là sơ bộ. — [IOS Press SHTI240274 (2024)](https://ebooks.iospress.nl/doi/10.3233/SHTI240274)
- Claim khách hàng: Solera/Lumina Las Vegas (10 tháng, memory care) 48% ít ngã, 54% ít nhập viện, thời gian phản hồi nhân viên giảm 50% — [Lumina Las Vegas](https://luminalasvegas.com/solera-senior-living-achieves-major-gains-in-safety-and-care-outcomes-at-lumina-las-vegas-with-inspiren/); Heritage Communities: 68% giảm ngã có chấn thương trong phòng ngủ ở 6 cơ sở — [Norfolk Daily News](https://norfolkdailynews.com/select/how-ai-is-preventing-falls-at-heritage-communities-and-transforming-senior-care/article_ab31bd68-a58e-407a-b70b-8ea77d34c1ae.html). Không có số liệu báo nhầm/bed-exit. [VENDOR/KHÁCH HÀNG]

**Radar (so sánh: Vayyar, mmWave)**
- Vayyar: trang ROI nói giảm alarm fatigue, "confirmed true falls in real time" nhưng không có số báo nhầm. — [Vayyar](https://vayyar.com/care-pages/why/) [VENDOR]. Case Stowford House: nhân viên có **hai nút "xác nhận ngã" / "xóa báo nhầm"** (mẫu feedback giống nút "báo nhầm") nhưng không báo cáo tỷ lệ. — [Vayyar blog, 06/2026](https://vayyar.com/blog/elderly-care/no-one-should-lie-on-the-floor-for-an-hour-how-stowford-house-closed-the-gap-with-vayyar)
- Học thuật (lab): mmFall đạt 98% phát hiện trên 50 cú ngã với 2 báo nhầm — [mmFall arXiv 2003.02386 (2020; TASE 2022)](https://www.arxiv.org/pdf/2003.02386); bài SPIE 2024 4D mmWave: 97,5% chính xác, tỷ lệ báo nhầm 0,4% (không rõ có phải thực địa) — [SPIE 2024](https://nanophotonics.spiedigitallibrary.org/conference-proceedings-of-spie/13091/1309112/A-robust-fall-detection-approach-based-on-4D-imaging-millimeter/10.1117/12.3022783.full); nghiên cứu nhiều người cho thấy false negative tăng theo số người do che khuất — [mmFall/Arizona](https://experts.arizona.edu/en/publications/mmfall-fall-detection-using-4-d-mmwave-radar-and-a-hybrid-variati/) (theo trích đoạn tìm kiếm); bài 2026 về phát hiện "nằm sàn sau ngã" bằng mmWave giá rẻ ở cơ sở chăm sóc dài hạn nói triển khai thực tế "can remain challenging". — [arXiv 2601.17710](https://arxiv.org/html/2601.17710v1)

**Học thuật 2025–2026: khoảng cách lab → đời thật**
- OmniFall (KIT, 2025; v2): gộp 8 dataset dàn dựng (CMDFall, UP-Fall, Le2i, GMDCSA24, EDF, OCCU, MCFD, CAUCAFall; ~14 h single-view, 101 người, 29 góc camera), tập test "in-the-wild" OF-ItW (818 video tai nạn thật từ OOPS, 2,65 h), và tập tổng hợp OF-Syn (12k video, ~17 h, sinh bằng **Wan 2.2**, 1280×720, 15 fps), taxonomy 16 lớp (fall, fallen, sit_down, lie_down, …). — [OmniFall arXiv 2505.19889v2](https://arxiv.org/html/2505.19889v2)
- Kết quả trên video thật (VideoMAE-K400 fine-tune, lớp Fall): train trên CMDFall: F1 52,3% (sens 51,1%, spec 86,9%); train trên toàn bộ staged: F1 ~61%; train **chỉ trên synthetic**: F1 64,2% (sens 72,0%, spec 84,6%); staged + synthetic: F1 65,6% (sens 72,9%, spec 85,4%) — tốt nhất. Tác giả: "carefully designed synthetic data can match or surpass real staged footage on cross-domain transfer"; embedding thiên về appearance (SigLIP2) hưởng lợi nhiều nhất từ synthetic. — [OmniFall v2](https://arxiv.org/html/2505.19889v2)
- Với backbone đóng băng, khoảng cách lab→wild rất lớn (ví dụ VideoMAE-K400 frozen chỉ sens 0,21 trên OOPS-Fall). — [OmniFall v1](https://arxiv.org/html/2505.19889v1)
- VLM zero-shot cho fall: một nghiên cứu 2026 (robot hỗ trợ xã hội) dùng mô hình kiểu CLIP: zero-shot 92,5% accuracy, few-shot calibration 100% — nhưng chỉ trên 40 video một người, cân bằng lớp → rất sơ bộ. — [Univ. of Hertfordshire 2026](https://researchprofiles.herts.ac.uk/en/publications/visionlanguage-model-for-fall-detection-in-socially-assistive-rob/)

### Inferences
- Mẫu thiết kế sống sót ngoài đời: **AI nhạy cao (chấp nhận nhiều candidate) → tầng xác minh đặc hiệu cao → alert**. SafelyYou dùng người ở call-center làm tầng 2; Easy FnB dùng Gemini làm tầng 2 — cùng kiến trúc, chỉ thay người bằng VLM. Bài học: tầng 2 phải được đo riêng (precision/recall của verifier), vì chính nó quyết định báo nhầm.
- Video clip kèm alert có giá trị ngay cả khi detection chưa hoàn hảo (Baycrest: video giúp hiểu nguyên nhân 81% số lần) → Easy FnB nên gửi kèm crop/clip ngắn trong alert để nhân viên tự loại báo nhầm trong 1 giây, thay vì chỉ "Bàn 7 gọi".
- Kết quả OmniFall cho thấy dữ liệu tổng hợp bằng mô hình sinh video (Wan 2.2) có thể thay thế dữ liệu dàn dựng → hướng sau hackathon: sinh clip "giơ tay gọi phục vụ" từ góc CCTV trần nhà để làm hard-negative/positive cho head PE-Core.
- Sự chênh lệch "1 báo nhầm/năm" (vendor) vs "11/27 alert là sai" (độc lập) cho thấy định nghĩa báo nhầm khác nhau (trước hay sau human review). Easy FnB phải định nghĩa rõ: FA đo **sau** Gemini và **trước** khi tới nhân viên.

### Gaps
- Không tìm thấy kết quả công bố của RCT SafelyYou (NCT03685240) hay nghiên cứu 11 cộng đồng; không có số FA/resident-night độc lập cho SafelyYou, Kepler, Inspiren.
- Không tìm thấy nghiên cứu thực địa nào báo cáo FA/ngày cho radar (Vayyar) trong viện dưỡng lão.
- Không tìm thấy benchmark GPT-4o/Gemini zero-shot cho fall detection trên video người già quy mô lớn.

---

## 2. Bed-exit / patient-at-risk: virtual sitter, video monitoring trong bệnh viện

### Takeaway
Bài học lớn nhất từ bệnh viện là **báo động nhiều mà không chính xác thì vô dụng**: RCT bed-alarm (2012) tăng sử dụng alarm 36 lần mà không giảm ngã, một phần vì báo nhầm khiến điều dưỡng phớt lờ. Hệ thống video hiện đại (LookDeep, AvaSure) chạy ở tần số thấp (1 fps), làm mượt theo thời gian, phân loại vai trò người (bệnh nhân/nhân viên) ngay trong detector, và dùng người quan sát từ xa; nhưng dữ liệu công khai về FA/giờ của chính các alert bed-exit gần như không có.

### Cited Findings
**LookDeep Health (2024, 2026 — [CÓ XUNG ĐỘT LỢI ÍCH]: tác giả là nhân viên LookDeep)**
- Triển khai ở 11 bệnh viện / 3 bang trong một mạng lưới; >300 bệnh nhân nguy cơ ngã cao; 1.466 patient-days trong dataset phát hành; >40.000 frame gán nhãn; test 10.000 frame. — [arXiv 2412.13152](https://arxiv.org/html/2412.13152v1)
- Phần cứng/pipeline: thiết bị LookDeep Video Unit (CPU + NPU Rockchip RKNN), camera trên xe đẩy, RGB hoặc hồng ngoại gần tùy ánh sáng; **1 fps**; ảnh 1088×612, detector input 608×608; detector YOLOv4 (khởi tạo COCO, fine-tune); **phân loại vai trò (patient/staff/other) được huấn luyện như một phần của detector**; chuyển động bằng optical flow Farnebäck trong ROI, có "safety zone" cho việc vượt biên; logic "patient alone / supervised by staff"; **bộ lọc làm mượt 5 giây** trên các dự đoán logic; xu hướng theo giờ. — [arXiv 2412.13152](https://arxiv.org/html/2412.13152v1)
- Hiệu năng (model v5): detection mọi lớp precision 0,97 / F1 0,92 (baseline YOLOv4 F1 0,59); person precision 0,96 / F1 0,91; **vai trò bệnh nhân F1 0,98**; "patient alone" F1 0,92 (baseline 0,28); làm mờ mặt không làm giảm F1 (0,89 vs 0,91). Độ chính xác xu hướng "alone" ban đêm thấp hơn ban ngày (0,80 vs 0,84). Không báo cáo ngưỡng alert hay FA rate; bed-exit/fall chỉ là động cơ, không có metric. Dataset ẩn danh: github.com/lookdeep/ai-norms-2024 (không ghi license). — [arXiv 2412.13152](https://arxiv.org/html/2412.13152v1)
- Bài 2026 (hồi cứu, 8/2024–12/2025, 3.980 monitor đủ điều kiện, 292.914 dòng theo giờ): alert thời gian thực dạng "nudge_state" **xanh/vàng/đỏ** (cảnh báo phân cấp, không phải nhị phân); 17,8 cú ngã/1.000 giờ ngồi ghế vs 4,3/1.000 giờ trên giường; phát hiện ngã: **precision 1,000, recall 0,733** (≈1/4 cú ngã bị bỏ sót) trên số sự kiện nhỏ (43 cú ngã được xét duyệt); nhãn tư thế yếu (macro F1 0,528, ECE 0,450). Không báo cáo tổng số alert. — [arXiv 2603.22785](https://arxiv.org/html/2603.22785v1)

**AvaSure / virtual sitter**
- Nghiên cứu 2015: 828 bệnh nhân, 9 tháng, giám sát video từ xa + quy trình chuẩn → ngã giảm ~35%; tác giả chính là phó chủ tịch AvaSure, release do công ty phát hành. — [Becker's](https://www.beckershospitalreview.com/quality/video-patient-monitoring-reduces-falls-by-35/); [BusinessWire](https://businesswire.com/news/home/20150413005248/en/Video-Monitoring-Reduces-Patient-Falls-by-35-Percent-Study-Shows) [VENDOR]
- Số liệu 2019 do bên thứ ba trích: thời gian phản hồi alarm trung bình 15,8 giây trên 71 bệnh viện / 15.021 bệnh nhân; 1,50 ngã/1.000 ngày giám sát. — [yespress.io/avasure](https://yespress.io/avasure) (nguồn thứ cấp, chưa xác minh)
- Một tổng quan hệ thống (tài liệu lưu trữ ĐH Maryland): bằng chứng mức trung bình rằng giám sát video liên tục giảm dùng sitter, nhưng một số nghiên cứu không thấy thay đổi về ngã. — [UMaryland archive](https://archive.hshsl.umaryland.edu/server/api/core/bitstreams/3175eba5-d7f2-41f1-a2d9-2a773840da3e/content) (theo trích đoạn tìm kiếm)

**Bed alarm truyền thống — bằng chứng "alarm nhiều ≠ an toàn hơn"**
- RCT cụm Shorr et al. (Annals of Internal Medicine, 2012): 16 khoa, 349 giường, 18 tháng; nhóm khuyến khích dùng bed alarm dùng nhiều hơn ~36 lần nhưng **không** giảm ngã hay chấn thương do ngã (5,76 vs 4,56 ngã/1.000 patient-days, khác biệt không ý nghĩa); Shorr giải thích một phần do **báo nhầm thường xuyên khiến điều dưỡng phớt lờ**, và alarm thường kêu khi bệnh nhân đã bắt đầu ngã. — [UF News 2012](https://archive.news.ufl.edu/articles/2012/11/bed-alarms-not-proven-to-prevent-patient-falls-in-hospitals-uf-researchers-say.html); [GeriPal](https://geripal.org/bed-alarms-in-hospitalized-patients/)
- Alarm fatigue lâm sàng: 72%–99,4% alarm lâm sàng là báo nhầm/không cần hành động (Sendelbach & Funk 2013, qua tổng quan thứ cấp) — [Systematic review on academia.edu](https://www.academia.edu/98739208/Nurses_Attitudes_Related_To_Alarm_Fatigue_in_Critical_Care_Units_A_Systematic_Review); CHOP: báo nhầm chiếm 99,0% alarm ở bệnh nhân khoa thường (monitor sinh lý, không phải video) — [CHOP/ECRI 2015](https://www.research.chop.edu/sites/default/files/wp-content/uploads/2015/02/ecri_HDaward_20150204_CHOP.pdf)
- Nghiên cứu cảm nhận điều dưỡng (monitor sinh lý): để giảm báo nhầm cần đào tạo và **tùy chỉnh alarm theo tình trạng từng bệnh nhân** (≈ hiệu chỉnh theo site/bối cảnh). — [Comillas repository (2022)](https://repositorio.comillas.edu/xmlui/handle/11531/70958) (theo trích đoạn tìm kiếm)
- Tổng quan hệ thống 2024 (BMC Medicine) về công nghệ giám sát (gồm CCTV) trong nội trú tâm thần: quan điểm của bệnh nhân/nhân viên "mixed and complex". — [PubMed 39614242](https://pubmed.ncbi.nlm.nih.gov/39614242/) (liên kết lấy từ kết quả tìm kiếm, chưa mở)

### Inferences
- LookDeep là analogue gần nhất về kỹ thuật với Easy FnB: camera cố định góc chéo, detector YOLO + **lớp vai trò staff/patient trong detector** (≈ staff/customer), logic zone (≈ zone bàn), **làm mượt 5 s**, 1 fps cho trạng thái chậm (≈ trạng thái bàn trống/có khách/cần dọn). Easy FnB có thể chạy trạng thái bàn ở 1 fps và chỉ chạy pose tần số cao cho phát hiện giơ tay.
- "nudge_state" xanh/vàng/đỏ gợi ý **alert phân cấp**: chỉ "đỏ" mới đẩy thông báo; "vàng" chỉ hiện trên dashboard → giảm chi phí chú ý của báo nhầm.
- RCT bed alarm cho thấy chỉ số đúng không phải "số alert" mà là "alert có được hành động không" → Easy FnB nên log **tỷ lệ alert được nhân viên xử lý** và **thời gian từ alert tới khi nhân viên tới bàn**.

### Gaps
- Không tìm thấy số FA/giờ hoặc PPV công khai cho alert bed-exit của AvaSure, CareView, LookDeep hay Inspiren; không tìm thấy nghiên cứu CareView riêng.
- Không xác minh được tổng quan scoping nói "điều dưỡng thấy video monitoring hiệu quả nhưng vẫn thích người trông trực tiếp" (chỉ thấy trong trích đoạn tìm kiếm, không rõ nguồn gốc).
- Không tìm thấy cách các vendor virtual sitter đặt ngưỡng alarm (tài liệu kỹ thuật không công khai).

---

## 3. Abnormal/violent behaviour detection trong CCTV an ninh (VAD) và xác minh alarm

### Takeaway
Học thuật VAD (weakly-supervised, VLM-based như LAVAD/VERA/Holmes-VAU) đạt ~87–91% AUC trên UCF-Crime, nhưng các bài audit 2025–2026 cho thấy AUC theo frame che giấu điểm vận hành: ở 90% recall, báo nhầm có thể lên hàng chục nghìn/giờ, và đặc trưng đóng băng (CLIP/DINOv2) "học camera chứ không học khái niệm bất thường" (AUC chéo dataset ~0,5). Ngoài đời, ngành an ninh giải bằng **xác minh alarm**: detector người/xe + bộ lọc AI + người vận hành, với claim giảm 50–95% báo nhầm (gần như toàn bộ là vendor/khách hàng).

### Cited Findings
**Phương pháp 2024–2025 (VLM/LLM)**
- LAVAD (CVPR 2024): training-free; VLM captioner mô tả từng frame, LLM chấm điểm bất thường, dùng tương đồng cross-modal để làm sạch caption và tinh chỉnh điểm; vượt các phương pháp unsupervised/one-class trên UCF-Crime và XD-Violence; tác giả tự chỉ ra ví dụ báo nhầm ở đoạn đầu/cuối bình thường. — [LAVAD arXiv 2404.01014](https://arxiv.org/html/2404.01014v1); [project page](https://lucazanella.github.io/lavad)
- VERA (CVPR 2025): VLM đóng băng, học các "câu hỏi dẫn dắt" bằng verbalized learning giữa VLM learner/optimizer với nhãn thô; inference cho điểm theo đoạn rồi fusion ngữ cảnh cảnh/thời gian thành điểm theo frame; SOTA VAD có giải thích trên UCF-Crime, XD-Violence. — [VERA arXiv 2412.01095](https://arxiv.org/html/2412.01095v3); [CVPR 2025 poster](https://cvpr.thecvf.com/virtual/2025/poster/33523)
- Holmes-VAU (CVPR 2025): benchmark HIVAU-70k (video lấy từ train set UCF-Crime và XD-Violence), code/model công khai tại github.com/pipixin321/HolmesVAU (license chưa kiểm tra). — [CVPR 2025 open access](https://openaccess.thecvf.com/content/CVPR2025/html/Zhang_Holmes-VAU_Towards_Long-term_Video_Anomaly_Understanding_at_Any_Granularity_CVPR_2025_paper.html)
- Weakly-supervised SOTA: DeSC (preprint 3/2026) 89,37% AUC UCF-Crime, xây trên VadCLIP/STPrompt — [arXiv 2603.19780](https://arxiv.org/html/2603.19780); dual-encoder (preprint 11/2025) tự báo 90,7% — [arXiv 2511.13276](https://arxiv.org/html/2511.13276v1); mốc cũ: Dual Memory Units 86,97% (2023) — [arXiv 2302.05160](https://arxiv.org/pdf/2302.05160); real-time WSVAD 86,94% (WACV 2024) — [WACV 2024](https://openaccess.thecvf.com/content/WACV2024/html/Karim_Real-Time_Weakly_Supervised_Video_Anomaly_Detection_WACV_2024_paper.html)

**Audit: benchmark ≠ triển khai**
- "Benchmark AUC Is Not Deployable Reliability" [PREPRINT, 28/6/2026, một tác giả]: 4 dataset (UCSD Ped1/Ped2, Avenue, ShanghaiTech), 4 backbone đóng băng (CLIP ViT-B/32, DINOv2 ViT-S/14, ResNet-50, EfficientNet-B0), kNN cosine với embedding bình thường. AUC cùng dataset trung bình 0,704; **chéo dataset 0,499 (ngẫu nhiên)**; tệ nhất 0,340. DINOv2 tốt nhất cùng-dataset nhưng tụt nhiều nhất khi chéo; tác giả: representation "has learned the camera, not the concept of anomaly". Ở **90% frame recall (giả định 10 fps) ≈ 31.931 báo nhầm/giờ** (~9 alarm/giây). Khuyến nghị: báo cáo kết quả chéo dataset, báo cáo alarms/giờ ở một điểm vận hành, test-time adaptation bằng đoạn footage ngắn từ camera mới. — [arXiv 2606.29506](https://arxiv.org/html/2606.29506v1)
- "Rethinking Metrics and Benchmarks of VAD" (2025): AUC/AP nhạy với thiên lệch của một người gán nhãn và bỏ qua độ trễ phát hiện; đề xuất AUC/AP xác suất trung bình và metric có tính độ trễ (LaAP); các phương pháp hiện có có tỷ lệ báo nhầm cao trên benchmark "hard-normal" mới. — [arXiv 2505.19022](https://arxiv.org/html/2505.19022v2)
- "From Frames to Events" (2026, VAD lấy người làm trung tâm/pose): model SOTA có frame-AUC cao nhưng **precision mức sự kiện <10% ngay cả ở tIoU=0,2**. — [newx.sg tóm tắt](https://newx.sg/paper/detail/fc68de23-3813-11f1-b84c-00163e10baa7) (aggregator)
- Audit frame-AUC trong WSVAD (2026): AUC gộp không dự đoán được khả năng định vị trong video và không đủ độ phân giải để chứng minh các khoảng cách SOTA nhỏ. — [takara.ai tóm tắt arXiv 2608.11985](https://tldr.takara.ai/p/2608.11985) (aggregator)
- Survey VAD single-scene: EER có thể gây hiểu nhầm khi sự kiện bất thường rất hiếm (đúng bối cảnh thực tế); AUC trên dataset nhỏ đã bão hòa. — [arXiv 2004.05993](https://arxiv.org/pdf/2004.05993)

**Xác minh alarm trong an ninh thương mại (alarm verification)**
- Calipsa (đã bị Motorola Solutions mua): "false alarm reduction rate of 93%", alarm thật được đẩy cho người xác minh — [Calipsa Detect](https://calipsa.io/product/calipsa-pro-analytics/calipsa-detect) [VENDOR]; "up to 95%", lọc mất ~1 giây/alarm — [SecurityInfoWatch 2022](https://www.securityinfowatch.com/alarms-monitoring/press-release/21263164/calipsa-calipsa-announces-technology-integration-with-sureview-systems) [VENDOR]; thử nghiệm khách hàng ~50% — [IFSEC](https://www.ifsecglobal.com/video-surveillance/calipsas-remote-monitoring-platform-slash-false-security-alarms-50-trials-show/amp/); G4S UK&I 84% — [Pelco case study](https://www.pelco.com/pt/case-studies/g4s-uk-ireland); Prosegur 60–90% tùy site — [Pelco case study](https://www.pelco.com/it/case-studies/prosegur-security) [KHÁCH HÀNG, đăng trên trang vendor]. → biên độ 50–95% tùy site/camera/masking.
- Ambient.ai: claim giảm 90–95% báo nhầm; giữ **human-in-the-loop 24/7 cho alert độ tin cậy thấp**; feedback của operator cải thiện model theo thời gian. — [Ambient.ai llms.txt](https://www.ambient.ai/llms.txt); [Summify](https://summify.io/discover/building-the-see-something-say-something-ai-for-every-camera) [VENDOR]
- Verkada: cho phép feedback trong app về kết quả, input người dùng đưa vào tinh chỉnh model; dùng phát hiện người để sàng lọc báo nhầm. — [Security Systems News 11/2025](https://www.securitysystemsnews.com/article/verkadaone-2025-inside-the-push-toward-proactive-predictive-security); [Security Journal Americas](https://securityjournalamericas.com/verkada-solution-minimize-false-alarms/) [VENDOR]

**MLLM làm tầng xác minh (cascade detector → MLLM)**
- Flash-Cascade (preprint 2025, báo cháy bằng ảnh): MLLM làm bộ lọc thứ cấp sau detector; 97,79% accuracy, F1 0,9767 trên benchmark có hard negative thực tế, hơn detector DEIMv2 14,64 điểm; **MLLM không có hướng dẫn chain-of-thought có thể "sụp" trên mẫu âm**. — [Sciety / Research Square rs-8847038](https://sciety.org/articles/activity/10.21203/rs.3.rs-8847038/v1) [PREPRINT]
- Red Sift (blog 2/2025): LMM kiểm tra từng detection của model có sẵn để giảm false positive; tăng reasoning lúc test không giúp, còn giảm nhẹ accuracy. — [Red Sift blog](https://redsift.com/blog/enhanced-logo-detection-with-ai-a-hybrid-approach) [VENDOR BLOG]

### Inferences
- Bài học kép cho Easy FnB: (1) đừng dùng anomaly score không giám sát trên embedding toàn cảnh — nó "học camera"; hãy dùng sự kiện định nghĩa rõ (giơ tay, ghế trống) + verifier; (2) head nhỏ trên PE-Core/CLIP huấn luyện ở một nhà hàng có nguy cơ không chuyển sang nhà hàng khác → phải đánh giá chéo camera/chéo nhà hàng và hiệu chỉnh ngưỡng theo site.
- Pattern "AI lọc + người xác minh + feedback từ người vận hành" (Calipsa/Ambient/Verkada) là đúng mẫu Easy FnB: YOLO candidate → head → Gemini → nhân viên bấm "báo nhầm" → quay lại huấn luyện.
- Hai kết quả về MLLM verifier mâu thuẫn nhẹ (Flash-Cascade: cần CoT để không sụp trên mẫu âm; Red Sift: reasoning thêm không giúp) → nên thử A/B prompt có/không reasoning ngắn trên tập hard-negative của chính Easy FnB, không giả định.

### Gaps
- Không tìm thấy báo cáo độc lập (không phải vendor) về FA/giờ của hệ thống VAD/violence detection triển khai thực tế.
- Không kiểm tra được license HIVAU-70k/Holmes-VAU, VERA, LAVAD code; UCF-Crime/XD-Violence license chưa kiểm tra trong phiên này.
- Không tìm thấy bài peer-reviewed về dùng Gemini/GPT-4o làm verifier cho alert CCTV về hành vi người (chỉ có báo cháy, logo).

---

## 4. Analogue khác: hồ bơi (đuối nước), lớp học (giơ tay), nhà hàng (gọi phục vụ), y khoa (động kinh)

### Takeaway
Các analogue này xác nhận ba điểm: (1) **cửa sổ thời gian dài hơn → ít báo nhầm nhưng chậm hơn** (Poseidon chọn 10 s); (2) phát hiện giơ tay thật trong lớp học đông người chỉ đạt F1 ~0,76 với pose + mô hình thời gian, và tác giả SCB cho rằng pose khó trong lớp đông → nên kết hợp pose với classifier ảnh; (3) bài toán "gọi phục vụ" trong nhà hàng mới ở mức PoC/patent, chưa có sản phẩm công bố số liệu — Easy FnB có khoảng trống để định nghĩa chuẩn đánh giá.

### Cited Findings
**Đuối nước (Poseidon, Lynxight, AngelEye-type)**
- Poseidon (2016): alarm đặt sau **10 giây** nạn nhân bất động ở đáy; công ty nói cửa sổ ngắn hơn sẽ gửi quá nhiều alert; claim 250 hồ ở 15 nước. — [Computer Vision News 7/2016](https://www.rsipvision.com/ComputerVisionNews-2016July/15) [VENDOR, 2016]
- Lynxight (dự án EU): phát hiện giai đoạn sớm khi người bơi còn tỉnh trên mặt nước, thay vì chờ ~10 s bất động ở đáy. — [CORDIS](https://cordis.europa.eu/project/id/854423/es); hướng dẫn mua của Lynxight: con số accuracy/false alarm chỉ có nghĩa khi vendor định nghĩa false positive là gì và đo trong điều kiện nào (loại hồ, độ sâu, mật độ người). — [Lynxight](https://www.lynxight.com/content/what-should-fitness-centres-ask-ai-drowning-detection-vendors) [VENDOR]
- Brisbane (2026) thử nghiệm Lynxight ở 2 hồ công cộng như bước thu thập bằng chứng; phân tích học thuật được trích nói giá trị alert phụ thuộc việc người vận hành có tin và hành động theo alert hay không. — [Kurrant](https://kurrant.com/?p=47549)

**Giơ tay trong lớp học (analogue gần nhất cho "khách giơ tay gọi")**
- Bühler et al. (AIED 2023): embedding pose cơ thể + mô hình thời gian, 36 video lớp học thật, 127 học sinh lớp 5–12, **2.442 sự kiện giơ tay** gán nhãn thủ công; **F1 0,76**; nhấn mạnh bất biến góc nhìn và bền với che khuất. — [ECR Hub](https://ecrhub.org/publications/automated-hand-raising-detection-classroom-videos-view-invariant-and-occlusion-robust)
- SCB-Dataset: ~4.003 ảnh / 11.248 nhãn giơ tay, YOLOv7 mAP tới 85,3%; tác giả cho rằng phương pháp dựa pose "not applicable for behavior detection in overcrowded classrooms"; bản mở rộng 7.428 ảnh / 106.830 nhãn / 20 lớp. — [SCB-Dataset arXiv 2304.02488](https://arxiv.org/pdf/2304.02488v3)
- 2026: so sánh YOLOv8–YOLOv12 và RT-DETR trên 3.373 ảnh / 9.659 instance từ lớp học thật, đa dạng ánh sáng, góc, mức che khuất; có lớp "Raising Hand". — [EAI AI & Robotics 2026](https://publications.eai.eu/index.php/airo/article/download/11141/4006/29591)

**Nhà hàng: gọi phục vụ**
- eKonobar Vision (PoC, Croatia): phát hiện "staff call" trong nhà hàng bằng TensorFlow Lite + MediaPipe trên cloud; khó khăn chính là **biến đổi ánh sáng và phân biệt cử chỉ gọi với chuyển động không liên quan**. — [Pangea case study](https://pangea.ai/agencies/boopro-technology/case-studies/ekonobar-vision-case-study)
- Patent US 2024/0153315: ước lượng skeleton khách từ video, coi cử chỉ tay/mặt là gọi nhân viên; **cử chỉ nhỏ dưới ngưỡng "noticeability" không tạo thông báo**. — [Justia](https://patents.justia.com/patent/20240153315)
- Patent USPTO 10984249: đăng ký khách đang yêu cầu hỗ trợ, theo dõi họ trong footage và **kiểm tra nhân viên có thực sự phản hồi hay không** (đóng vòng alert). — [USPTO 10984249](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10984249)
- Dữ liệu mở nhỏ: Roboflow "waiter calling" (~146 ảnh) — [Roboflow](https://universe.roboflow.com/skin-condition-detection/waiter-calling); project GitHub YOLOv8 tìm người giơ tay (bài thi tuyển dụng) — [awesome.ecosyste.ms](https://awesome.ecosyste.ms/projects/github.com%2Falhadikhan%2Fwaiter-calling---hand-raise-detection-challenge)

**Động kinh (EEG) — chuẩn đánh giá sự kiện hiếm trưởng thành nhất**
- SzCORE (2024): khuyến nghị báo cáo cả scoring theo sample và **theo sự kiện**; quy tắc gộp sự kiện, **dung sai trước/sau sự kiện**, độ dài tối đa (sự kiện >5 phút bị chia); báo nhầm tính là **số sự kiện FP quy đổi trên ngày**; tác giả thừa nhận các tham số hơi tùy ý. — [SzCORE arXiv 2402.13005](https://arxiv.org/html/2402.13005v3)
- SzCORE challenge 2025: top-5 có 1,34–14 FP/ngày, sensitivity 30–58%; đội dẫn đầu: F1 32%, sens 37%, precision 29%, 1,34 FP/ngày — minh họa khoảng cách tổng quát hóa khi đánh giá trung thực. — [arXiv 2505.18191](https://arxiv.org/html/2505.18191v1)

### Inferences
- Patent US 2024/0153315 + Poseidon cho Easy FnB hai núm vặn: **biên độ cử chỉ** (cổ tay cao hơn vai/đầu bao nhiêu, chuẩn hóa theo chiều cao bbox) và **thời lượng** (giữ bao lâu). Cả hai đều đổi recall lấy FA.
- Patent 10984249 gợi ý tính năng "tự đóng alert khi track nhân viên vào zone bàn" — vừa giảm alert lặp, vừa sinh nhãn yếu (alert được nhân viên tới = có khả năng đúng).
- F1 0,76 của Bühler trên 2.442 sự kiện thật là mốc tham chiếu thực tế cho "giơ tay trong cảnh đông, bị che" — nếu demo Easy FnB báo F1 > 0,9 trên video tự quay, cần nói rõ khác biệt điều kiện.
- SzCORE là khuôn mẫu tốt để Easy FnB viết "giao thức đánh giá" (event merging, tolerance, FA/giờ).

### Gaps
- Không tìm thấy sản phẩm thương mại "gọi phục vụ bằng camera" nào công bố accuracy/FA.
- Không tìm thấy license của SCB-Dataset và dữ liệu Bühler (có thể không công khai do quyền riêng tư học sinh).
- Không tìm thấy số FA/giờ độc lập cho hệ thống đuối nước.

---

## 5. Các design pattern giảm báo nhầm (cascade, persistence, cooldown, HITL, hiệu chỉnh theo site)

### Takeaway
Các hệ thống ngoài đời giảm báo nhầm chủ yếu bằng **kiến trúc và vận hành**, không bằng model đơn lẻ: (a) cascade nhạy→đặc hiệu (AI → người/VLM), (b) cửa sổ thời gian/làm mượt (5 s ở LookDeep, 10 s ở Poseidon), (c) logic ngữ cảnh/zone và vai trò người, (d) alert phân cấp, (e) nút xác nhận/xóa và feedback vào model, (f) tùy chỉnh theo site/bệnh nhân.

### Cited Findings
- Cascade AI nhạy cao → người đặc hiệu cao (SafelyYou). — [NIH grant](https://api.ai-analytics.org/grant/nih/10020322)
- Cascade AI → human verification cho alarm thật (Calipsa); HITL cho alert độ tin cậy thấp (Ambient.ai). — [Calipsa](https://calipsa.io/product/calipsa-pro-analytics/calipsa-detect); [Ambient.ai](https://www.ambient.ai/llms.txt)
- Cascade detector → MLLM verifier, cần CoT để không sụp trên mẫu âm. — [Flash-Cascade](https://sciety.org/articles/activity/10.21203/rs.3.rs-8847038/v1)
- Làm mượt theo thời gian 5 s, 1 fps; vai trò staff/patient trong detector; safety zone. — [LookDeep 2024](https://arxiv.org/html/2412.13152v1)
- Đánh đổi cửa sổ thời gian vs số alert (10 s). — [Poseidon 2016](https://www.rsipvision.com/ComputerVisionNews-2016July/15)
- Ngưỡng biên độ cử chỉ ("noticeability") trước khi thông báo. — [US 2024/0153315](https://patents.justia.com/patent/20240153315)
- Alert phân cấp xanh/vàng/đỏ. — [LookDeep 2026](https://arxiv.org/html/2603.22785v1)
- Nút xác nhận ngã / xóa báo nhầm cho nhân viên. — [Vayyar Stowford House](https://vayyar.com/blog/elderly-care/no-one-should-lie-on-the-floor-for-an-hour-how-stowford-house-closed-the-gap-with-vayyar)
- Feedback trong app đưa vào tinh chỉnh model. — [Verkada / Security Systems News](https://www.securitysystemsnews.com/article/verkadaone-2025-inside-the-push-toward-proactive-predictive-security)
- Kết quả lọc báo nhầm biến thiên lớn theo site (Prosegur 60–90%). — [Pelco/Prosegur](https://www.pelco.com/it/case-studies/prosegur-security)
- Tùy chỉnh alarm theo tình trạng từng bệnh nhân để giảm báo nhầm. — [Comillas](https://repositorio.comillas.edu/xmlui/handle/11531/70958)
- Test-time adaptation với đoạn footage ngắn từ camera mới (đề xuất, chưa kiểm chứng). — [arXiv 2606.29506](https://arxiv.org/html/2606.29506v1)
- Hard negatives: benchmark "hard-normal" làm lộ báo nhầm cao của các phương pháp VAD hiện có. — [arXiv 2505.19022](https://arxiv.org/html/2505.19022v2)

### Inferences
- Thứ tự ưu tiên cho Easy FnB (rẻ → đắt): zone/ngữ cảnh (người đang ngồi ở bàn, không phải nhân viên) → persistence N-of-M frame → per-track/per-table cooldown → head PE-Core → Gemini (nhiều frame) → dedup server → alert phân cấp → nút "báo nhầm".
- "Precision tại recall cố định" và "ngân sách alert/giờ" nên được đặt như hợp đồng sản phẩm: ví dụ chọn ngưỡng sao cho FA ≤ 1/giờ/nhà hàng trên tập validation, rồi báo recall đạt được tại ngưỡng đó (thay vì báo F1 tối đa).
- Active learning thực tế: mỗi lần nhân viên bấm "báo nhầm" → lưu crop + embedding + đặc trưng rule → đưa vào hard-negative bank cho head PE-Core và vào few-shot negative examples của prompt Gemini.

### Gaps
- Không tìm thấy tài liệu công khai mô tả chính xác cách vendor (Verkada/Ambient/Kepler) dùng nút dismiss để retrain hay chỉnh ngưỡng (tự động hay thủ công, tần suất).
- Không tìm thấy nghiên cứu định lượng so sánh "cooldown/per-track dedup" trong hệ thống camera thương mại.

---

## 6. Phương pháp đánh giá sự kiện hiếm trong thực tế

### Takeaway
Các lĩnh vực trưởng thành (động kinh, VAD gần đây) đã chuyển từ metric theo frame/sample sang **metric theo sự kiện + FA theo thời gian (giờ/ngày) + độ trễ phát hiện**, với quy tắc gộp sự kiện và dung sai thời gian được ghi rõ; AUC/EER theo frame bị chỉ trích là gây hiểu nhầm cho sự kiện hiếm.

### Cited Findings
- Scoring theo sự kiện với tolerance trước/sau, gộp sự kiện, FP/ngày; khuyến nghị báo cáo cả sample-based và event-based. — [SzCORE](https://arxiv.org/html/2402.13005v3)
- Báo alarms/giờ ở một điểm vận hành cụ thể, kèm đánh giá chéo dataset; AUC không phải tuyên bố về khả năng triển khai. — [arXiv 2606.29506](https://arxiv.org/html/2606.29506v1)
- Metric có tính độ trễ (LaAP) và trung bình nhiều người gán nhãn. — [arXiv 2505.19022](https://arxiv.org/html/2505.19022v2)
- Precision mức sự kiện (tIoU) có thể <10% dù frame-AUC cao. — [From Frames to Events (aggregator)](https://newx.sg/paper/detail/fc68de23-3813-11f1-b84c-00163e10baa7)
- EER gây hiểu nhầm khi sự kiện hiếm. — [Survey arXiv 2004.05993](https://arxiv.org/pdf/2004.05993)
- Định nghĩa false positive và điều kiện đo phải được nêu rõ khi báo accuracy. — [Lynxight](https://www.lynxight.com/content/what-should-fitness-centres-ask-ai-drowning-detection-vendors)
- Fall detection: OmniFall báo sensitivity/specificity/F1 cho lớp Fall và F1@50 cho phân đoạn thời gian, tách staged vs wild. — [OmniFall v2](https://arxiv.org/html/2505.19889v2)
- Trong nghiên cứu lâm sàng, outcome thường là sự kiện/1.000 patient-days hoặc /1.000 exposure-hours (chuẩn hóa theo phơi nhiễm). — [LookDeep 2026](https://arxiv.org/html/2603.22785v1); [GeriPal/Shorr](https://geripal.org/bed-alarms-in-hospitalized-patients/)

### Inferences
- Easy FnB đã đi đúng hướng (event-level, Wilson CI, FA/giờ). Bổ sung đề xuất: **Wilson CI chỉ dành cho tỷ lệ** (recall, precision); **FA/giờ là tỷ lệ Poisson** → dùng khoảng tin cậy Poisson chính xác (Garwood); nếu 0 báo nhầm trong T giờ thì cận trên 95% ≈ 3/T mỗi giờ ("rule of three") — ví dụ 2 giờ video không báo nhầm chỉ chứng minh FA ≤ ~1,5/giờ. (Suy luận thống kê chuẩn, không có nguồn riêng trong phiên này.)
- Nên chuẩn hóa theo phơi nhiễm như y khoa: FA/giờ/nhà hàng **và** FA/100 bàn-giờ có khách (vì số bàn có khách thay đổi theo giờ cao điểm).
- Viết "giao thức đánh giá" kiểu SzCORE: (1) sự kiện ground truth = khoảng [onset, offset] của cử chỉ; (2) alert đúng nếu rơi trong [onset − 1 s, offset + X s]; (3) nhiều alert cho cùng sự kiện = 1 TP (các alert thừa đếm riêng là "duplicate"); (4) alert ngoài mọi sự kiện = FA; (5) báo median & p90 time-to-alert; (6) funnel số candidate/giờ qua từng tầng (rule → head → Gemini → dedup).
- Báo metric theo **từng tầng** của cascade để biết tầng nào sinh FA và tầng nào giết TP (giống phân biệt "trước/sau human review" của SafelyYou).

### Gaps
- Không tìm thấy giá trị tolerance cụ thể của SzCORE trong các trích đoạn đã đọc (cần đọc toàn văn).
- Không tìm thấy chuẩn công nghiệp cho "FA/giờ chấp nhận được" trong vận hành nhà hàng; mọi ngưỡng cho Easy FnB là đề xuất.

---

## 7. Dataset và model pretrained (kèm license)

### Takeaway
Cho fall detection có nhiều dataset với license hỗn hợp (MIT, CC BY, CC BY-NC-SA, "cần xin phép"); OmniFall gom chúng lại kèm tập wild và synthetic. Cho bối cảnh nhà hàng/gọi phục vụ gần như không có dataset công khai đáng kể — dữ liệu gần nhất là lớp học (SCB) và vài dataset Roboflow nhỏ.

### Cited Findings
- Le2i: CC BY-NC-SA 3.0; GMDCSA-24: MIT; CAUCAFall: CC BY 4.0; OOPS: CC BY-NC-SA 4.0; CMDFall, UP-Fall, EDF/OCCU, MCFD: dùng với sự cho phép của tác giả (theo phụ lục OmniFall — nguồn thứ cấp, cần đối chiếu trang gốc). — [OmniFall v2](https://arxiv.org/html/2505.19889v2)
- OmniFall trên Hugging Face (simplexsigil2/omnifall), README liệt kê CC BY-NC-SA 4.0; code: GitHub simplexsigil/omnifall-experiments. — [HF README](https://huggingface.co/datasets/simplexsigil2/omnifall/blob/main/README.md)
- GMDCSA-24 (dataset ngã trong video, 2024). — [PMC11416611](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11416611/)
- UP-Fall (đa phương thức). — [PMC6539235](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6539235/)
- LookDeep ai-norms-2024 (ảnh bệnh viện ẩn danh; license không ghi trong paper). — [arXiv 2412.13152](https://arxiv.org/html/2412.13152v1)
- Holmes-VAU / HIVAU-70k (code + model công khai; license chưa kiểm tra; video gốc từ UCF-Crime/XD-Violence). — [CVPR 2025](https://openaccess.thecvf.com/content/CVPR2025/html/Zhang_Holmes-VAU_Towards_Long-term_Video_Anomaly_Understanding_at_Any_Granularity_CVPR_2025_paper.html)
- SCB-Dataset (giơ tay lớp học). — [arXiv 2304.02488](https://arxiv.org/pdf/2304.02488v3)
- Roboflow "waiter calling" (~146 ảnh). — [Roboflow](https://universe.roboflow.com/skin-condition-detection/waiter-calling)

### Inferences
- Vì Easy FnB chỉ dùng cho hackathon (non-commercial OK), có thể dùng OOPS/OmniFall/Le2i làm **hard-negative "ngã/cúi/vươn người"** cho classifier giơ tay, nhưng giá trị trực tiếp thấp; dữ liệu tự quay ở góc CCTV nhà hàng thật vẫn quan trọng nhất.
- Nguồn hard-negative hữu ích nhất cho "giơ tay" là các cử chỉ trông giống: vươn vai, chỉnh tóc, nghe điện thoại, gắp đồ ăn xa, giơ ly cụng ly, chỉ tay vào menu, nhân viên giơ khay — nên gán nhãn rõ các lớp này (giống taxonomy 16 lớp của OmniFall tách fall vs lie_down vs sit_down).

### Gaps
- Không xác minh license UR Fall, SCB-Dataset, ShanghaiTech, UBnormal, UCF-Crime, XD-Violence trong phiên này.
- Không tìm thấy model pretrained công khai riêng cho "hand-raise/waiter-call" từ góc trần nhà có đánh giá đáng tin.

---

## 8. Pitfalls (che khuất, hành động giống nhau, góc camera, ánh sáng/ban đêm, domain shift, alarm fatigue)

### Takeaway
Các thất bại lặp lại qua mọi ngành: look-alike actions (nằm xuống vs ngã; nhân viên cúi nhặt đồ bị tính là ngã), che khuất trong cảnh đông (FN tăng theo số người), ban đêm/ánh sáng kém, domain shift giữa site/camera (AUC chéo dataset ~0,5), và alarm fatigue làm vô hiệu hóa cả hệ thống đúng.

### Cited Findings
- Look-alike: trong pilot Baycrest, một số "ngã thật" thực ra không phải cư dân ngã (ví dụ nhân viên cúi nhặt đồ). — [CABHI](https://www.cabhi.com/?p=21829) (qua trích đoạn tìm kiếm); taxonomy OmniFall nhằm tách "lie_down vs. fall". — [OmniFall v2](https://arxiv.org/html/2505.19889v2); hệ SafelyYou giúp phân biệt ngã nghiêm trọng với việc cư dân tự hạ mình xuống sàn (không có tỷ lệ). — [AJMC 2019](https://www.ajmc.com/view/realtime-video-detection-of-falls-in-dementia-care-facility-and-reduced-emergency-care)
- Che khuất/đông người: FN tăng theo số người do che khuất (radar). — [mmFall/Arizona](https://experts.arizona.edu/en/publications/mmfall-fall-detection-using-4-d-mmwave-radar-and-a-hybrid-variati/); pose khó dùng trong lớp học quá đông. — [SCB-Dataset](https://arxiv.org/pdf/2304.02488v3); LookDeep không phân tích che khuất, người khó thấy được đánh dấu ngoại lệ. — [arXiv 2412.13152](https://arxiv.org/html/2412.13152v1)
- Ban đêm/ánh sáng: độ chính xác ban đêm thấp hơn, một bệnh nhân bị dự đoán "một mình" quá mức ban đêm. — [LookDeep 2024](https://arxiv.org/html/2412.13152v1); biến đổi ánh sáng là khó khăn chính của PoC gọi phục vụ nhà hàng. — [eKonobar](https://pangea.ai/agencies/boopro-technology/case-studies/ekonobar-vision-case-study)
- Góc camera: vị trí camera thay đổi không được kiểm soát trong train/eval. — [LookDeep 2024](https://arxiv.org/html/2412.13152v1)
- Domain shift: AUC chéo dataset 0,499; "learned the camera". — [arXiv 2606.29506](https://arxiv.org/html/2606.29506v1); staged→wild tụt mạnh. — [OmniFall](https://arxiv.org/html/2505.19889v2)
- Alarm fatigue: bed alarm không giảm ngã, báo nhầm khiến điều dưỡng phớt lờ. — [UF News](https://archive.news.ufl.edu/articles/2012/11/bed-alarms-not-proven-to-prevent-patient-falls-in-hospitals-uf-researchers-say.html); 72–99% alarm lâm sàng là báo nhầm. — [academia.edu review](https://www.academia.edu/98739208/Nurses_Attitudes_Related_To_Alarm_Fatigue_in_Critical_Care_Units_A_Systematic_Review)
- Bằng chứng nhiễu lợi ích: hầu hết nghiên cứu SafelyYou/AvaSure/Inspiren/LookDeep có tác giả thuộc công ty. — [AJMC 2019](https://www.ajmc.com/view/realtime-video-detection-of-falls-in-dementia-care-facility-and-reduced-emergency-care); [Becker's](https://www.beckershospitalreview.com/quality/video-patient-monitoring-reduces-falls-by-35/); [LookDeep 2026](https://arxiv.org/html/2603.22785v1)

### Inferences
- Với Easy FnB, look-alike quan trọng nhất là **nhân viên** (giơ khay, chỉ bàn, vẫy đồng nghiệp) → bộ phân loại staff/customer phải chạy *trước* rule giơ tay; LookDeep cho thấy lớp vai trò trong detector đạt F1 0,98 trong bệnh viện (đồng phục rõ ràng).
- Che khuất ở nhà hàng: cổ tay bị che bởi người ngồi đối diện/đồ trang trí → nên cho phép "bằng chứng một phần" (ví dụ khuỷu tay + cổ tay trên vai với confidence keypoint) và để Gemini xử lý ca mơ hồ, thay vì hạ ngưỡng keypoint toàn cục.
- Demo trên footage của một quán duy nhất có nguy cơ overfit vào camera đó → nói rõ trong pitch rằng triển khai thật cần hiệu chỉnh theo site (zone bàn, ngưỡng, few-shot negatives).

### Gaps
- Không có số liệu định lượng về độ chính xác ban đêm/hồng ngoại cho bài toán cử chỉ tay.

---

## 9. Áp dụng cụ thể cho Easy FnB (stage nào, ngưỡng/metric nào, vòng feedback "báo nhầm", effort trước/sau 14/11)

### Takeaway
Easy FnB đã có đúng "xương sống" của các hệ thống sống sót ngoài đời (detector nhạy → head → Gemini verifier → dedup → alert). Trước 14/11, đầu tư nên tập trung vào: persistence + ngữ cảnh + cooldown/auto-resolve, prompt Gemini đa frame có lý do ngắn và tập negative, nút "báo nhầm" ghi log, và một báo cáo đánh giá kiểu SzCORE (event-level, FA/giờ với Poisson CI, time-to-alert, funnel theo tầng). Active learning, hiệu chỉnh theo site, dữ liệu tổng hợp và mô hình thời gian để sau hackathon.

### Cited Findings
(Các nguồn làm căn cứ cho mapping bên dưới — chi tiết ở các mục 1–8)
- Cascade AI nhạy → xác minh đặc hiệu: [SafelyYou NIH grant](https://api.ai-analytics.org/grant/nih/10020322); [Calipsa](https://calipsa.io/product/calipsa-pro-analytics/calipsa-detect); [Flash-Cascade](https://sciety.org/articles/activity/10.21203/rs.3.rs-8847038/v1)
- Làm mượt 5 s, 1 fps, vai trò staff/patient trong detector, zone: [LookDeep 2024](https://arxiv.org/html/2412.13152v1)
- Alert phân cấp: [LookDeep 2026](https://arxiv.org/html/2603.22785v1)
- Cửa sổ thời gian vs số alert: [Poseidon 2016](https://www.rsipvision.com/ComputerVisionNews-2016July/15)
- Ngưỡng biên độ cử chỉ & kiểm tra nhân viên đã phản hồi: [US 2024/0153315](https://patents.justia.com/patent/20240153315); [USPTO 10984249](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10984249)
- Nút xác nhận/xóa, feedback trong app: [Vayyar Stowford House](https://vayyar.com/blog/elderly-care/no-one-should-lie-on-the-floor-for-an-hour-how-stowford-house-closed-the-gap-with-vayyar); [Verkada](https://securityjournalamericas.com/verkada-solution-minimize-false-alarms/)
- Đánh giá event-level, FA theo thời gian, tolerance: [SzCORE](https://arxiv.org/html/2402.13005v3); alarms/giờ ở điểm vận hành: [arXiv 2606.29506](https://arxiv.org/html/2606.29506v1); latency-aware: [arXiv 2505.19022](https://arxiv.org/html/2505.19022v2)
- Pose + mô hình thời gian cho giơ tay thật (F1 0,76): [Bühler et al. AIED 2023](https://ecrhub.org/publications/automated-hand-raising-detection-classroom-videos-view-invariant-and-occlusion-robust)
- Dữ liệu tổng hợp (Wan 2.2) chuyển giao tốt sang wild: [OmniFall v2](https://arxiv.org/html/2505.19889v2)

### Inferences
**Mapping theo tầng (đề xuất, chưa kiểm chứng trên dữ liệu Easy FnB):**

| Tầng | Mượn từ | Đề xuất cụ thể cho Easy FnB |
|---|---|---|
| 0. Tracking + vai trò | LookDeep (role trong detector) | Phân loại staff/customer theo track (đa số phiếu qua nhiều frame), chạy *trước* rule giơ tay; loại toàn bộ cử chỉ của track staff. |
| 1. Rule candidate + persistence | Poseidon (cửa sổ), patent "noticeability" | Cổ tay cao hơn vai (và/hoặc mũi) một biên độ chuẩn hóa theo chiều cao bbox; giữ ≥ N/M frame trong ~1–2 s (ví dụ 8/12 frame ở 6–8 fps); chỉ áp dụng cho người được gán vào zone bàn và đang ngồi. Sweep N/M & biên độ trên video quay thật để vẽ đường FA/giờ–recall. |
| 2. Head PE-Core/CLIP | hard-negative mining | Classifier crop thân trên: hand-raise vs {vươn vai, chỉnh tóc, nghe điện thoại, cụng ly, chỉ menu, gắp xa}; huấn luyện lại với negatives từ nút "báo nhầm". |
| 3. Gemini verifier | SafelyYou HIL, Calipsa, Flash-Cascade | Gửi 3–4 frame trải ~2 s (trước/trong cử chỉ) + crop bàn; prompt có định nghĩa, ví dụ âm, yêu cầu lý do ngắn + JSON {is_call, confidence, who}; "không chắc" → hạ xuống mức vàng (dashboard) chứ không đẩy thông báo. A/B có/không reasoning (kết quả tài liệu mâu thuẫn). |
| 4. Dedup + cooldown + auto-resolve | patent 10984249, LookDeep smoothing | Cooldown theo bàn (ví dụ 60–120 s) và theo track; tự đóng alert khi track staff vào zone bàn; gộp alert trong cooldown thành 1 sự kiện. |
| 5. Alert phân cấp | LookDeep nudge_state | Đỏ = đẩy thông báo; vàng = badge trên dashboard; xanh = chỉ log. |
| 6. Feedback "báo nhầm" | Vayyar nút clear, Verkada/Ambient feedback | Lưu {crop, frames, embedding, đặc trưng rule, output Gemini, timestamp, bàn}; dùng làm (a) few-shot negative trong prompt, (b) hard-negative cho head, (c) thống kê FA theo bàn để siết ngưỡng theo bàn/zone ("nuisance zones" — bàn gần cửa, quầy). Thêm nút "đúng/đã xử lý" để có nhãn dương. |

**Metric/ngưỡng đề xuất cho demo:**
- Định nghĩa "ngân sách": ví dụ FA ≤ 1/giờ/nhà hàng (đo sau Gemini, trước nhân viên); báo recall và precision (Wilson CI) **tại** ngưỡng đó; FA/giờ với Poisson CI; median/p90 time-to-alert (từ onset cử chỉ đến thông báo).
- Funnel theo tầng: candidates/giờ → sau head → sau Gemini → sau dedup; recall giữ lại qua từng tầng.
- Báo cáo riêng: video tự quay (dàn dựng) vs video quán thật (wild) — bài học OmniFall; nếu có ≥2 camera/quán, báo cáo chéo camera (bài học audit 2026).
- Tối thiểu thời lượng: để khẳng định FA ≤ 1/giờ với 95% tin cậy khi quan sát 0 FA cần ~3 giờ video có khách (rule of three).

**Effort (2 người, 5/11 → 14/11):**
- Trước 14/11 (khả thi, ~1–2 ngày công mỗi mục): (1) persistence N-of-M + biên độ chuẩn hóa + gating staff/zone; (2) cooldown + auto-resolve khi staff tới bàn; (3) prompt Gemini đa frame + JSON + mức vàng/đỏ; (4) nút "báo nhầm/đúng" ghi log + replay vào few-shot negatives; (5) script đánh giá event-level (tolerance, merging, FA/giờ Poisson CI, time-to-alert, funnel) và slide/dashboard funnel. 
- Sau hackathon: active learning định kỳ cho head PE-Core từ log báo nhầm; hiệu chỉnh ngưỡng theo site/bàn tự động; mô hình thời gian trên chuỗi keypoint (kiểu Bühler) hoặc video model nhỏ; sinh dữ liệu tổng hợp góc CCTV bằng mô hình sinh video (kiểu OmniFall/Wan 2.2); đánh giá ban đêm/ánh sáng yếu; thử test-time adaptation cho camera mới.

### Gaps
- Không có dữ liệu công khai về tần suất "khách giơ tay gọi" thực tế mỗi giờ trong nhà hàng → không thể ước lượng PPV kỳ vọng từ base rate; Easy FnB cần tự đo trên footage thật.
- Các ngưỡng cụ thể (N/M, 60–120 s cooldown, FA ≤ 1/giờ) là đề xuất kỹ thuật, chưa có nguồn ngành F&B xác nhận.
- Chưa có nghiên cứu nào về chấp nhận/alarm fatigue của nhân viên phục vụ nhà hàng với alert từ camera (chỉ có bằng chứng từ điều dưỡng/an ninh).
