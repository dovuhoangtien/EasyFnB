# Bài toán tương tự ở ngành khác: phát hiện giơ tay / vẫy tay gọi người từ camera trên cao, cảnh đông người

Phạm vi: lớp học thông minh, tín hiệu cầu cứu ("Signal for Help", vẫy tay cho drone cứu hộ), phát hiện hành động không-thời gian (AVA, YOWO, open-vocabulary), và các nơi khác cần "gọi phục vụ" (bán lẻ, bệnh viện, cabin máy bay, gọi taxi/robotaxi, trọng tài, đấu giá, cứu đuối). Ghi chú này **không lặp lại** báo cáo "Nhận giơ tay theo khung xương" (GRU/ST-GCN++ trên keypoint, NTU-120 2D, BK-SAD, Bühler et al., SAV, Canon patent, Google Meet, máy trạng thái, late fusion). Những chỗ chạm tới các mục đó chỉ ghi tham chiếu.

Bối cảnh Easy FnB khi đọc ghi chú: YOLO26n-pose + YOLO26s + ByteTrack, đầu phân loại trên PE-Core/CLIP, luật giữ tay ≥0.6 s, Gemini xác minh crop, RTX 3050 4 GB, 12–22 fps, demo 14/11/2026 (còn 9 ngày tính từ 5/11).

## Câu hỏi 1: Phương pháp tốt nhất 2023–2026 cho giơ/vẫy tay trong cảnh đông, che khuất, góc nghiêng hoặc từ trên xuống. Cái nào chạy được trên GPU 4 GB, cái nào chỉ đẹp trên giấy?

### Takeaway
Ngoài ngành, có bốn họ phương pháp. (a) Detector một khung có lớp "giơ tay" (dòng SCB/YOLO trong lớp học) là cái thực dụng nhất và chạy được trên 4 GB, nhưng nhầm với hành động khác và trượt tay nhỏ. (b) Pipeline "track → crop tay → landmark tay → bộ phân loại" (Signal for Help) chạy nhẹ, nhưng cần bàn tay đủ điểm ảnh. (c) Detector hành động không-thời gian (YOWOv2/v3, AVA) chạy được dạng Nano/Tiny, nhưng mAP trên AVA chỉ khoảng 12–16 ở cỡ nhỏ. (d) Open-vocabulary STAD và VLM zero-shot thì mới chỉ đẹp trên giấy: chưa công bố tốc độ, và kém ở cấp từng người. Bằng chứng độc lập duy nhất so sánh trực tiếp (Käs et al. 2025) xếp skeleton (HD-GCN) đứng đầu, video foundation model (V-JEPA) sát sau, VLM zero-shot (Gemini Flash 2.0) đứng cuối.

### Cited Findings

**Lớp học thông minh: detector một khung có lớp "giơ tay"**
- SCB-Dataset (Fan Yang, 2023, sửa tới v7 tháng 8/2025): 4,003 ảnh, 11,248 nhãn, trọng tâm là giơ tay. Baseline YOLOv7 đạt mAP tối đa 85.3%. Bản mở rộng SCB-Dataset5 có 7,428 ảnh, 106,830 nhãn, 20 lớp (gồm giơ tay, đọc, viết, dùng điện thoại) — [arXiv 2304.02488](https://arxiv.org/pdf/2304.02488)
- Bài "Improved YOLOv7" trên SCB (18.4k nhãn, 4.2k ảnh; 3 lớp giơ tay/đọc/viết) ghi rõ YOLOv7 gốc **nhận nhầm hành động khác thành giơ tay** và **bỏ sót giơ tay cỡ nhỏ**. Cách sửa là thêm Wise-IoU và attention BiFormer — [arXiv 2306.03318](https://arxiv.org/html/2306.03318v2)
- SCB-Dataset3 (2023): 5,686 ảnh, 45,578 nhãn, 6 hành vi (giơ tay, đọc, viết, dùng điện thoại, cúi đầu, nằm bò ra bàn). YOLOv5/v7/v8 đạt mAP tối đa 80.3% — [arXiv 2310.02522](https://arxiv.org/abs/2310.02522)
- CSSA-YOLO (Sensors, 5/2025), trên SCB03-S (5,015 ảnh, 25,810 nhãn, nhiều vật thể nhỏ): mAP50 tổng **76.0% so với 74.8% của YOLOv8m** (+1.2 điểm). AP50 lớp giơ tay **83.2%** (các mục khác trong bài ghi 84.2–84.9%, số không nhất quán). Mô hình 46.75M tham số, 297 GFLOPs, 78 FPS trên **RTX 4090**. Dù tên có chữ "spatiotemporal", phần đọc được chỉ cho thấy xử lý từng ảnh, không có module nhiều khung. Tác giả thừa nhận độ chính xác "dao động mạnh" khi bố cục lớp học thay đổi vượt một ngưỡng — [PMC12116009](https://pmc.ncbi.nlm.nih.gov/articles/PMC12116009/)
- Benchmark AIRO (đăng 7/4/2026): 3,373 ảnh, 5 hành vi chú ý, có lớp "Raising Hand", lấy từ nhiều bố cục lớp, góc camera và mức che khác nhau. So YOLOv8→YOLOv12 với RT-DETR: YOLOv8m mAP@0.5 = 0.920, YOLOv11s/m mAP@0.5:0.95 = 0.726. Số liệu lấy từ snippet tìm kiếm, vì toàn văn trả 403 nên chưa đọc được kết quả RT-DETR và AP từng lớp — [EUDL AIRO 11141](https://eudl.eu/doi/10.4108/airo.11141)
- ALC-YOLOv8s (30/4/2026): +1.8 mAP50 so với YOLOv8s trong "lớp học thật" có mục tiêu dày, nhỏ, hay bị che. Abstract không ghi dataset, lớp hay FPS — [arXiv 2604.27293](https://arxiv.org/abs/2604.27293)

**Tín hiệu cầu cứu: pipeline track → crop tay → phân loại**
- "Signal for Help" là cử chỉ do Canadian Women's Foundation tạo năm 2020 để nạn nhân cầu cứu không lời — [Polito IRIS 2024](https://iris.polito.it/handle/11583/2992954)
- Politecnico di Torino (IEEE ISC2 2024) dùng YOLOv7 + DeepSORT theo dõi người, MediaPipe trích đặc trưng tay, rồi một bộ phân loại quyết định có cầu cứu hay không. Báo **91%** độ chính xác và real-time trên thiết bị yếu. Đây là số tự báo, chưa đọc được toàn văn — [Polito IRIS 2992954](https://iris.polito.it/handle/11583/2992954)
- Nhóm Polito trước đó (ISTAS 2023) làm phiên bản edge với hai CNN nhẹ (phát hiện lòng bàn tay, phân loại cử chỉ) và công bố bộ video 200 clip "Signal for Help". Mô hình tốn khoảng 4 lần ít tài nguyên hơn SOTA, đổi lại mất khoảng 3% độ chính xác validation — [Polito IRIS 2981724](https://iris.polito.it/retrieve/handle/11583/2981724/666403); [Polito IRIS 2974541](https://iris.polito.it/handle/11583/2974541)
- Nghiên cứu sớm (ATU, 2022) phải tự dựng 112 ảnh vì không có dataset công khai — [ATU](https://pure.atu.ie/en/publications/using-cnn-and-tensorflow-to-recognise-signal-for-help-hand-gestur-3/)

**Drone cứu hộ: vẫy tay như tín hiệu**
- Liu & Szirányi (Sensors 2021) dùng hai cử chỉ động làm lõi: "Attention" (vẫy hai tay, tức set) và "Cancel" (vẫy một tay, tức reset). Bộ 10 cử chỉ quay từ camera UAV, độ chính xác test **99.09%**. Có cảnh báo "help" khi người dùng vẫy về phía drone — [Sensors 21(6):2180](https://www.mdpi.com/1424-8220/21/6/2180/htm); [SZTAKI eprint](https://eprints.sztaki.hu/10220/)
- UAV-GESTURE (2019): 119 video HD (24.78 phút), 13 cử chỉ lấy từ hiệu lệnh điều khiển máy bay/trực thăng, có nhãn khớp cơ thể — [arXiv 1901.02602](https://arxiv.org/pdf/1901.02602)

**Phát hiện hành động không-thời gian (STAD)**
- YOWOv2 (repo yjh0410), trên AVA v2.2 với FPS đo trên **RTX 3090** (batch 1, gồm NMS): Nano 12.6–12.7 mAP @40 fps; Tiny 14.9–15.6 mAP @49 fps; Medium 18.4 @40–41 fps; Large 20.2–21.7 @22–29 fps. Trên UCF101-24: Nano **3.5M tham số, 1.3 GFLOPs**, F-mAP 78.8; Tiny 10.9M tham số, 2.9 GFLOPs, F-mAP 80.5 — [YOWOv2 GitHub](https://github.com/yjh0410/YOWOv2)
- YOWOv3 (arXiv 2408.02623): 88.33% mAP UCF101-24, 20.31% AVA v2.2, 59.8M tham số, 39.8 GFLOPs. Bài **không ghi FPS** — [arXiv 2408.02623](https://arxiv.org/pdf/2408.02623). Lưu ý có một "YOWOv3" khác (IEEE TCSVT 2024) dùng temporal shift chỉ 2D để tránh 3D conv khó chạy trên edge — [AMiner](https://www.aminer.cn/pub/6619f47013fb2c6cf6a280ff/yowov-a-lightweight-spatio-temporal-joint-network-for-video-action-detection)
- YOWO gốc (2019): 34 fps với clip 16 khung, 62 fps với clip 8 khung — [arXiv 1911.06644](https://arxiv.org/pdf/1911.06644)
- Danh sách lớp AVA: có **"hand wave" (ID 69)**, "point to (an object)" (43), "give/serve (an object) to (a person)" (65), eat (29), drink (27), sit (11), stand (12), talk to (79). **Không có lớp "raise hand"** — [MMAction2 AVA label_map](https://raw.githubusercontent.com/open-mmlab/mmaction2/main/tools/data/ava/label_map.txt)
- AVA-Kinetics: lớp người–vật khó nhất, lớp tư thế (pose) điểm cao hơn — [arXiv 2005.00214](https://arxiv.org/pdf/2005.00214)
- LART (CVPR 2023) nhận dạng hành động theo tracklet, ghép pose 3D với ngoại hình: bản chỉ dùng pose hơn SOTA trước **+10.0 mAP**, bản ghép hơn **+2.8 mAP** trên AVA v2.2. Code có trên trang dự án — [arXiv 2304.01199](https://arxiv.org/abs/2304.01199)
- EdgeOAR (12/2024) nhận dạng hành động online trên edge với early-exit, báo giảm 99.23% độ trễ trên UCF-101. Nó chỉ phân loại, không định vị — [arXiv 2412.01267](https://arxiv.org/html/2412.01267v1)

**Open-vocabulary STAD và VLM**
- OV-STAD (Wu et al., 5/2024) dựng OV-AVA (60 lớp) và fine-tune VLM video trên cặp vùng–văn bản — [arXiv 2405.10832](https://arxiv.org/html/2405.10832v1)
- SiA (Sia & Rawat, UCF, 4/2025) dùng backbone ViCLIP-B16, encoder-only, 100 detection token, không cần detector người riêng. Cross-dataset (train AVA-Kinetics) đạt UCF-101-24 **42.6** f-mAP và **MultiSports chỉ 0.8**. Closed-set MultiSports 28.8, so với 59.3 của STAR. **Không báo tốc độ, tham số hay phần cứng**, và không thấy link code/weights. Bài theo giấy phép CC BY-NC-ND 4.0 — [arXiv 2504.03096](https://arxiv.org/html/2504.03096v1)
- Käs et al. (6/2025), cử chỉ trong HRI (dataset NUGGET, kho vận): **HD-GCN (skeleton) tốt nhất**, V-JEPA + đầu phân loại đơn giản sát sau, còn **Gemini Flash 2.0 zero-shot khó phân biệt cử chỉ chỉ từ mô tả văn bản** — [arXiv 2506.20795](https://arxiv.org/abs/2506.20795)
- SocialGesture (CVPR 2025; 9,889 clip, 2–10 người mỗi video, cử chỉ chỉ trỏ/đưa/cho/với). Phân biệt có cử chỉ hay không đạt tốt nhất 84.43% (UniFormerV2-B/16). VQA zero-shot "gesture detection" chỉ đạt 69.6–75.7% (Qwen2.5-VL-72B 75.69, Claude 3.7 Sonnet 69.64, GPT-4o-mini 73.67). "Target localization" (ai cử chỉ với ai) tốt nhất **29.37%** — [arXiv 2504.02244](https://arxiv.org/html/2504.02244v1); [CVF](https://openaccess.thecvf.com/content/CVPR2025/html/Cao_SocialGesture_Delving_into_Multi-person_Gesture_Understanding_CVPR_2025_paper.html)
- VLM zero-shot trong lớp học (CV4Edu @ CVPR 2026): ở cấp từng học sinh, Cohen's κ **không vượt 0.10**. Ở cấp cả cảnh (SCB), CLIP và GPT-4o đạt κ≈0.60. Đổi cách diễn đạt prompt trên cùng ảnh làm độ chính xác lệch tới **32 điểm %**. Có "class collapse": 85–100% dự đoán dồn vào một mức — [arXiv 2606.21861](https://arxiv.org/abs/2606.21861)

### Inferences
- Thứ thực dụng trên 4 GB: (1) detector/classifier một khung kiểu SCB, vốn Easy FnB đã có dưới dạng crop classifier PE-Core; (2) YOWOv2-Nano/Tiny (3.5–10.9M tham số, 1.3–2.9 GFLOPs) có thể chạy song song YOLO26 trên RTX 3050 về mặt tính toán. Đây là ngoại suy, vì FPS chỉ đo trên 3090. Nhưng mAP AVA 12–16 cho thấy STAD cỡ nhỏ yếu ở hành động hiếm, nên nó không đáng thay pipeline pose + crop trước demo.
- Chỉ đẹp trên giấy với Easy FnB: SiA/OV-STAD (không có số tốc độ, cross-dataset tụt mạnh, MultiSports gần 0), VideoMAE V2 / InternVideo2 cỡ lớn, và các YOLO lớp học cỡ 40M+ tham số với ~300 GFLOPs (CSSA-YOLO) mà mức tăng chỉ +1 điểm trên chính dataset của họ.
- Bằng chứng xếp hạng skeleton > video FM > VLM zero-shot (Käs 2025) củng cố hướng của báo cáo trước. Nó cũng gợi ý Gemini nên làm bộ lọc phụ, không phải bộ quyết định chính.

### Gaps
- Không tìm thấy AP riêng của lớp "hand wave" trên AVA ở bất kỳ mô hình nào (YOWOv2, VideoMAE V2, LART). Số AVA tổng của VideoMAE V2 / InternVideo2 trong kết quả tìm kiếm không nhất quán (43.9 so với 18.24), nên không dùng được.
- Không có số FPS của YOWOv2/v3 trên GPU 4 GB (RTX 3050) hay trên Jetson.
- Không tìm thấy phương pháp 2023–2026 nào đánh giá riêng góc nhìn trần nhà / thẳng đứng cho giơ tay trong nhà hàng hoặc quán cà phê.

## Câu hỏi 2: Số liệu thực tế (độ chính xác, báo nhầm, độ trễ, phần cứng). Tách số vendor tự báo với đo độc lập

### Takeaway
Gần như mọi con số cao (91–99%) đều do tác giả hoặc vendor tự báo trên dữ liệu có kịch bản và cùng phân phối. Đo độc lập ngoài thực địa thì cực hiếm, còn báo nhầm theo giờ thì hầu như không ai công bố. Ở mọi ngành tương tự (lớp học, cứu đuối, bán lẻ, bệnh viện), báo nhầm mới là rào cản triển khai, và các thử nghiệm thật đều ghi nhận hệ thống bị dừng hoặc chưa có kết quả.

### Cited Findings
- **Tự báo, dữ liệu kịch bản:** UAV rescue gesture 99.09% test — [Sensors 2021](https://www.mdpi.com/1424-8220/21/6/2180/htm); Signal for Help 91% — [Polito 2024](https://iris.polito.it/handle/11583/2992954); trọng tài bóng rổ HOG+SVM 97.5% (2018), LBP+SVM 95.6% (2020), ORSNet cảm biến đeo 65 tín hiệu 95.3% — [review thể thao arXiv 2203.02281](https://arxiv.org/pdf/2203.02281); [ORSNet](https://mislab.cs.nthu.edu.tw/project-pages/ORSNet.html)
- **Lớp học (tác giả tự báo, dataset công khai):** giơ tay AP50 khoảng 83–85% (CSSA-YOLO, RTX 4090) — [PMC12116009](https://pmc.ncbi.nlm.nih.gov/articles/PMC12116009/). Một blog CSDN nói hệ YOLO + LLM đạt "92.3%" ở một trường trung học, nhưng **không có test set, cỡ mẫu hay cách đo** nên không dùng được — [CSDN](https://aicoding.csdn.net/6a6869a4662f9a54cb9512f0.html)
- **Triển khai lớp học thật (Hikvision, Trường số 11 Hàng Châu, 2018):** 3 camera trên bảng đen quét mỗi 30 giây, ghi nhận đọc, viết, giơ tay, đứng dậy, nghe giảng, nằm bò ra bàn — [Security Magazine](https://securitymagazine.com/articles/89036-chinese-school-uses-facial-recognition-to-monitor-student-behavior); [TechSpot](https://www.techspot.com/news/74719-chinese-school-using-facial-recognition-analyze-students-emotions.html). Theo LA Times (IPVM dẫn lại), hệ chỉ chạy với lớp 10 khoảng hai tháng rồi bị tạm dừng giữa chỉ trích về quyền riêng tư và vì "chưa được chứng minh" — [IPVM](https://ipvm.com/discussions/los-angeles-times-criticize-hikvision-s-classroom-behavior-management-system); [Caixin 2019](https://www.caixinglobal.com/2019-04-06/pilot-programs-are-spying-on-kids-in-the-classroom-part-two-101401105.html). Không có số độ chính xác công bố.
- **Bán lẻ (vendor):** Aeon Retail + Buddycom (2021) dùng AI camera "nhận ra khách cần phục vụ" và báo qua bộ đàm, dự kiến khoảng 80 cửa hàng. Bài **không nêu tiêu chí phát hiện và không có số độ chính xác** — [Buddycom](https://buddycom.net/en/articles/news/20210528.html). Indyme AutoAssist dùng camera chống trộm sẵn có, theo dõi khách ở khu hàng giá trị cao; khi đạt tiêu chí "interested shopper" thì báo nhân viên. Nguồn là thông cáo báo chí, không có số đo độc lập — [PRNewswire](https://prnewswire.com/news-releases/using-ai-to-identify-conversion-opportunities-in-brick-and-mortar-retail-301210814.html)
- **Cứu đuối (vendor so với độc lập):** bằng sáng chế mô tả cách dùng camera trên cao theo dõi chuyển động bơi là tạo nhiều bỏ sót/báo nhầm tới mức thiếu thực tế — [US 11580838](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11580838). Vendor CamerEye tuyên bố "loại bỏ báo nhầm" mà không có dữ liệu — [CamerEye](https://camereye.ai/?p=235). Chính vendor Lynxight viết rằng tỉ lệ phát hiện vô nghĩa nếu không nêu điều kiện (độ sâu, mật độ người, chói, góc camera) — [Lynxight](https://www.lynxight.com/content/do-ai-drowning-detection-systems-work-in-crowded-pools). Brisbane chỉ mới thử ở 2 hồ, chưa có kết quả — [Kurrant](https://kurrant.com/?p=47549)
- **VLM xác minh cảnh báo (vendor):** Milestone báo "tới 40%" giảm báo nhầm khi có AI + xác minh ngữ cảnh, nhưng chỉ qua blog bên thứ ba, không có phương pháp — [visionplatform.ai](https://visionplatform.ai/?p=9522). Nghiên cứu độc lập (10/2025) với VLM zero-shot làm bộ phát hiện bất thường: few-shot giúp nhưng có thể phản tác dụng, và bộ lọc quyền riêng tư làm giảm độ chính xác — [arXiv 2510.23190](https://www.emergentmind.com/papers/2510.23190)
- **VLM với khuôn mặt:** GPT-4o từ chối 98% yêu cầu chain-of-thought liên quan khuôn mặt học sinh — [arXiv 2606.21861](https://arxiv.org/abs/2606.21861)
- **Phần cứng của các số được báo:** YOWOv2 đo trên RTX 3090 — [YOWOv2](https://github.com/yjh0410/YOWOv2); CSSA-YOLO đo trên RTX 4090 — [PMC12116009](https://pmc.ncbi.nlm.nih.gov/articles/PMC12116009/)

### Inferences
- Hội đồng giám khảo sẽ gặp đúng kiểu số như các ngành trên: một con số "accuracy" cao trên clip diễn. Easy FnB sẽ nổi bật nếu báo thêm **số báo nhầm mỗi giờ trên footage âm tính** và **độ trễ từ lúc giơ tay tới lúc cảnh báo**. Đây là thứ không ngành nào công bố.
- Bài học Hikvision: một hệ "quan sát người" bị dừng vì quyền riêng tư, không phải vì kỹ thuật. Easy FnB nên nói rõ: xử lý tại chỗ, không lưu mặt, chỉ gửi crop sự kiện cho Gemini (hoặc làm mờ mặt).

### Gaps
- Không tìm thấy đánh giá độc lập nào về báo nhầm theo giờ của hệ thương mại phát hiện giơ/vẫy tay.
- Không tìm được số độ chính xác của sản phẩm Aeon/Buddycom, Indyme, hay hệ lớp học Hikvision.
- Kết quả thử nghiệm Brisbane (cứu đuối) chưa công bố.

## Câu hỏi 3: Sản phẩm thương mại, dự án mã nguồn mở và bài báo chính

### Takeaway
Không có sản phẩm thương mại công khai nào bán riêng chức năng "phát hiện vẫy tay gọi phục vụ" kèm số đo. Phần lớn chỉ là bằng sáng chế (bệnh viện, cabin máy bay, robotaxi, cầu cứu) hoặc thông cáo vendor. Bán lẻ dùng tín hiệu thụ động (dwell, "interested shopper") thay vì cử chỉ. Phần mở thật sự hữu ích là repo SCB, YOWOv2, HaGRIDv2, LART và PYSKL/MMAction2 (PYSKL/MMAction2 đã nêu ở báo cáo trước).

### Cited Findings
**Bệnh viện**
- Họ bằng sáng chế "Video monitoring system": giơ tay **hơn 5 giây** sẽ kích hoạt nurse call; có cả giao diện nút chiếu lên mà bệnh nhân bấm bằng cử động tay — [US 10368039](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10368039); [US 9204823](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/9204823); [US 10904492](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10904492)
- UrgentCare-AI (gist GitHub) ghép keyword "help", phát hiện vẫy tay và nhận diện có người trên giường. Độ chín chưa kiểm chứng — [gist samy101](https://gist.github.com/samy101)
- WACV 2025: điều khiển định vị bệnh nhân MRI bằng cử chỉ tay của kỹ thuật viên qua camera RGB-D, kiểm tra trên HaGRID. Trang abstract không có số — [arXiv 2407.14903](https://www.arxiv.org/abs/2407.14903)

**Cabin máy bay**
- Bằng sáng chế (Schalla et al.): camera chụp hành khách, cử chỉ không chạm điều khiển đèn đọc, **nút gọi tiếp viên**, cửa gió — [US 10372231](https://patents.google.com/patent/US10372231); [US 10146320](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10146320)
- Giám sát cabin nghỉ: lưu một bộ "cử chỉ nguy cấp", khớp thì báo lên màn hình tiếp viên — [US 11136137](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11136137)
- Không tìm thấy hãng bay nào công bố đã triển khai — [kết quả tìm kiếm patent](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12153738)

**Gọi taxi / robotaxi (người đứng giữa đám đông giơ tay)**
- MDPI Sensors 2023: coi "vẫy taxi rõ ràng" là tổ hợp **cử chỉ + vị trí người so với lề đường + hướng đầu**. Dataset tự quay từ taxi ở Tunis. Tác giả nói chỉ có hai công trình trước đó — [Sensors 23(10):4796](https://mdpi.com/1424-8220/23/10/4796); [PMC10224332](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10224332/)
- Bằng sáng chế lidar: phát hiện cử chỉ vẫy xe ở khoảng 40 m bằng lidar, lại gần rồi **xác nhận bằng ảnh camera** — [US 11079767](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11079767); thêm "intended passenger detection" — [US 10088846](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10088846)
- PGR-Net (Leeds, 2026) ánh xạ lại nhãn Jester thành Stop / Go / Greeting-Thanking cho xe tự lái. WIVW có hơn 1000 video FHD cử chỉ người đi bộ — [arXiv 2602.08479](https://arxiv.org/abs/2602.08479); [White Rose](https://eprints.whiterose.ac.uk/id/eprint/239277/)

**Cầu cứu qua camera giám sát**
- Bằng sáng chế "Method and system for detecting a request for distress assistance": nhận cử chỉ kín đáo qua camera, kết hợp ngữ cảnh để định mức khẩn, rồi thông báo người được chỉ định — [US 12387498](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12387498)
- Đơn sáng chế Trung Quốc về phát hiện tín hiệu cầu cứu trong bắt nạt học đường (CN112926407A) chỉ có metadata — [UTB catalog](https://vufind-test.katalog.k.utb.cz/SummonRecord/FETCH-epo_espacenet_CN112926407A3)

**Bán lẻ**
- Aeon Retail + Buddycom — [Buddycom](https://buddycom.net/en/articles/news/20210528.html); Indyme AutoAssist — [PRNewswire](https://prnewswire.com/news-releases/using-ai-to-identify-conversion-opportunities-in-brick-and-mortar-retail-301210814.html); bằng sáng chế CV dự đoán "khách cần hỗ trợ tại vị trí X" rồi báo nhân viên, dựa trên chuyển động và hành vi chứ không phải cử chỉ vẫy — [ipiq 1636898](https://ipiq.io/patents/1636898)

**Thể thao / trọng tài**
- Nhận dạng tín hiệu trọng tài bóng rổ từ video (HOG/LBP + SVM, 2018/2020) và từ cảm biến (ORSNet) — [arXiv 2203.02281](https://arxiv.org/pdf/2203.02281); [ORSNet](https://mislab.cs.nthu.edu.tw/project-pages/ORSNet.html). Chalearn (Kinect) có tín hiệu trọng tài bóng chuyền/vật — [KTU](https://epubl.ktu.edu/object/elaba:27919047/27919047.pdf). FERA (2025, đấu kiếm) dùng RTMPose + RTMDet rồi suy luận theo luật — [arXiv 2509.18527](https://arxiv.org/html/2509.18527v3)

**Đấu giá**
- Không tìm thấy hệ thị giác máy tính nào nhận giơ biển đấu giá. Ngành dùng biển điện tử có nút bấm, hoặc người điều hành quan sát bằng mắt — [Justia 20040044614](https://patents.justia.com/patent/20040044614); [Trea](https://trea.com/information/mobile-device-auction-paddle/patentapplication/d6be149f-909c-47db-9392-934e07f9786d)

**Mã nguồn mở / bài báo chính khác**
- SCB-dataset + mô hình — [GitHub Whiffe/SCB-dataset](https://github.com/Whiffe/SCB-dataset); YOWOv2 — [GitHub](https://github.com/yjh0410/YOWOv2); LART — [arXiv 2304.01199](https://arxiv.org/abs/2304.01199); HaGRIDv2 — [GitHub hukenovs/hagrid](https://github.com/hukenovs/hagrid); SocialGesture — [arXiv 2504.02244](https://arxiv.org/html/2504.02244v1)

### Inferences
- Thiết kế ngành bệnh viện ("giơ tay >5 s → gọi y tá") và robotaxi ("phát hiện thô ở xa → xác nhận bằng camera độ phân giải cao khi gần") đều là **cascade có ngưỡng thời gian**, giống v4 của Easy FnB. Khác biệt là họ chọn ngưỡng dài (5 s) để đổi lấy ít báo nhầm.
- Bán lẻ cho thấy một tín hiệu bổ sung mà Easy FnB chưa dùng: **nhu cầu thụ động**. Ví dụ: bàn đã ngồi X phút mà chưa có nhân viên tới, hoặc khách quay đầu nhìn quanh hay về quầy lâu. Tín hiệu này rẻ vì đã có track và trạng thái bàn.

### Gaps
- Không xác minh được bên sở hữu hay tình trạng hiệu lực của các bằng sáng chế. Không tìm thấy sản phẩm Hikvision/Dahua hiện hành có sự kiện "giơ tay/vẫy tay cầu cứu" kèm thông số; tìm bằng tiếng Trung không ra nguồn chính thức.
- Không lấy được số precision/recall của bài taxi Tunis: cả MDPI và PMC đều chặn (403/captcha).

## Câu hỏi 4: Dataset và mô hình pretrained tải được (kèm giấy phép)

### Takeaway
Nguồn dương "giơ tay từ camera cao trong phòng đông" tải được ngay nhiều nhất là SCB (phi thương mại). AVA cho lớp "hand wave" nhưng là cảnh phim. HaGRIDv2 cho crop tay lòng bàn tay/"stop"/"call" (CC BY-SA 4.0 biến thể), nhưng ở khoảng cách 0.5–4 m. Signal for Help và UAV rescue có dataset nhỏ, giấy phép chưa rõ. Mọi thứ đều dùng được cho hackathon; với thương mại thì SCB và SocialGesture bị cấm hoặc cần xin phép.

### Cited Findings
| Dataset / model | Nội dung liên quan | Giấy phép | Nguồn |
|---|---|---|---|
| SCB-dataset (các bản 1→5, SCB03-S) | Ảnh lớp học có box "giơ tay" + đọc/viết/…; tải qua Baidu (mã SCB5) và HF `wintonYF/SCB-Dataset`; có trọng số YOLO trên Baidu nhưng README không ghi mAP | **Học thuật/phi thương mại**; thương mại cần xin phép bằng văn bản | [GitHub](https://github.com/Whiffe/SCB-dataset) |
| Các tập lớp học khác (STBD-08, ClaBehavior, SCBehavior, UK_Datasets) | Chính tác giả SCB ghi nhận box không chuẩn, nhãn sai, số ảnh không khớp bài báo, ảnh hỏng | Không rõ | [GitHub SCB](https://github.com/Whiffe/SCB-dataset) |
| AVA v2.2 / AVA-Kinetics | Lớp "hand wave" (69), "point to" (43), "give/serve" (65); cảnh phim | (giấy phép AVA chưa kiểm trong phiên này) | [label_map](https://raw.githubusercontent.com/open-mmlab/mmaction2/main/tools/data/ava/label_map.txt); [AVA download](https://research.google.com/ava/download.html) |
| YOWOv2 checkpoints (UCF24, AVA; Nano→Large; 16/32 khung) | STAD real-time | **Mâu thuẫn**: README nói chưa có license, sidebar ghi MIT | [GitHub](https://github.com/yjh0410/YOWOv2) |
| HaGRIDv2 | 1,086,158 ảnh FullHD, 33 cử chỉ gồm `palm`, `stop`, `call`, có `no_gesture`; người cách camera 0.5–4 m; detector YOLOv10n cử chỉ mAP 88.2, YOLOv10n tay 87.9 | Biến thể **CC BY-SA 4.0** | [GitHub hagrid](https://github.com/hukenovs/hagrid) |
| Signal for Help (Polito) | 200 video | Chưa rõ | [Polito IRIS](https://iris.polito.it/handle/11583/2974541) |
| UAV rescue gestures (Liu & Szirányi) | 10 cử chỉ gồm vẫy 1 tay / 2 tay, quay từ UAV | Không thấy công bố công khai | [Sensors 2021](https://www.mdpi.com/1424-8220/21/6/2180/htm) |
| UAV-GESTURE | 119 video, 13 cử chỉ hiệu lệnh, có khớp | (chưa kiểm) | [arXiv 1901.02602](https://arxiv.org/pdf/1901.02602) |
| SocialGesture | 9,889 clip nhiều người, cử chỉ chỉ trỏ/đưa/cho/với (không có vẫy) | **CC BY-NC 3.0** | [arXiv 2504.02244](https://arxiv.org/html/2504.02244v1) |
| LART | Code nhận dạng hành động theo tracklet | Không ghi license code | [arXiv 2304.01199](https://arxiv.org/abs/2304.01199) |
| SiA (OV action detection) | Không thấy code/weights | Bài: CC BY-NC-ND 4.0 | [arXiv 2504.03096](https://arxiv.org/html/2504.03096v1) |

(BK-SAD, NTU-120 2D, UAV-Human, Toyota Smarthome, ST-GCN++ và PYSKL đã được liệt kê với giấy phép trong báo cáo "Nhận giơ tay theo khung xương".)

### Inferences
- SCB có lợi thế so với BK-SAD ở chỗ là **ảnh có box tay giơ** trong phòng đông. Nó hợp để tăng dữ liệu dương cho crop classifier PE-Core (tạo crop người từ box), nhưng góc camera chủ yếu nhìn từ phía bảng về học sinh, không phải trần nhà nghiêng.
- HaGRIDv2 chỉ có ích nếu crop tay đủ lớn. Ở CCTV quán, bàn tay người ngồi xa có thể chỉ vài chục pixel, xa ngoài miền 0.5–4 m của HaGRID.

### Gaps
- Chưa kiểm giấy phép chính xác của AVA và UAV-GESTURE trong phiên này.
- Không tìm thấy dataset công khai 2024–2026 nào có lớp "vẫy tay cầu cứu" nhìn từ trên xuống. Bài UAV IJCNN 2024 về cử chỉ đa khoảng cách chỉ có metadata — [OpenAlex](https://api.openalex.org/works/doi:10.1109%2FIJCNN60899.2024.10651436).

## Câu hỏi 5: Cạm bẫy (góc camera, người sát nhau, che khuất, cử chỉ giống, ánh sáng)

### Takeaway
Các ngành gặp cùng một bộ lỗi: tay giơ nhỏ, bị trượt; hành động khác bị nhận nhầm là giơ tay; độ chính xác tụt khi đổi bố cục hoặc góc camera; không xác định được ai giơ tay với ai trong đám đông; VLM bất ổn theo prompt. Ngành nào cũng tự thiết kế cử chỉ (Signal for Help, Attention/Cancel của drone, hiệu lệnh trọng tài) để giảm nhầm, và đây là bài học quan trọng.

### Cited Findings
- **Nhận nhầm và bỏ sót tay nhỏ:** YOLOv7 nhận nhầm hành động khác thành giơ tay và trượt giơ tay cỡ nhỏ — [arXiv 2306.03318](https://arxiv.org/html/2306.03318v2)
- **Đổi bố cục:** CSSA-YOLO "dao động mạnh" khi bố cục lớp học thay đổi vượt ngưỡng — [PMC12116009](https://pmc.ncbi.nlm.nih.gov/articles/PMC12116009/)
- **Che khuất và mục tiêu dày đặc:** được nêu là thách thức chính ở lớp học thật — [arXiv 2604.27293](https://arxiv.org/abs/2604.27293); [PMC12116009](https://pmc.ncbi.nlm.nih.gov/articles/PMC12116009/)
- **Nhiều người, ai làm gì với ai:** trong SocialGesture, xác định đích cử chỉ tốt nhất chỉ 29.37% zero-shot. Người chồng lấp, bị che một phần, ra khỏi khung — [arXiv 2504.02244](https://arxiv.org/html/2504.02244v1)
- **Nhiều người làm hỏng pseudo-label:** lỗi gán nhãn yếu của SiA chủ yếu đến từ video nhiều người — [arXiv 2504.03096](https://arxiv.org/html/2504.03096v1)
- **Ngữ cảnh phân biệt cử chỉ giống nhau:** vẫy taxi cần cử chỉ + vị trí so với lề đường + hướng đầu, vì cùng cử chỉ có thể là chào bạn — [Sensors 2023](https://mdpi.com/1424-8220/23/10/4796)
- **Cử chỉ được thiết kế:** Signal for Help là cử chỉ được tạo có chủ đích — [Polito 2024](https://iris.polito.it/handle/11583/2992954); drone cứu hộ dùng cặp Attention (2 tay) / Cancel (1 tay) — [Sensors 2021](https://www.mdpi.com/1424-8220/21/6/2180/htm); UAV-GESTURE lấy từ hiệu lệnh điều khiển máy bay — [arXiv 1901.02602](https://arxiv.org/pdf/1901.02602)
- **Ánh sáng và nền chuyển động:** các hệ bệnh viện dạng webcam/OpenCV nhạy với ánh sáng và chuyển động nền; một dự án chỉ nhận được lòng bàn tay mở — [Pitt project](https://people.cs.pitt.edu/~chang/231/y15/231finZhao.pdf); [LACCEI 2017](https://laccei.org/LACCEI2017-BocaRaton/full_papers/FP223.pdf)
- **VLM:** prompt lệch 32 điểm %, class collapse, từ chối khi có mặt người — [arXiv 2606.21861](https://arxiv.org/abs/2606.21861). VLM zero-shot ở lớp học phát hiện được giơ tay nhưng không phân biệt giơ tay để hỏi hay để phát biểu — [VISTA arXiv 2609.04550](https://arxiv.org/pdf/2609.04550). VLM kém ở suy luận không gian tinh trên bàn tay (HandVQA, 3/2026) — [arXiv 2603.26362](https://arxiv.org/html/2603.26362v1)
- **Điều kiện test:** tỉ lệ phát hiện vô nghĩa nếu không nêu mật độ người, chói, góc camera — [Lynxight](https://www.lynxight.com/content/do-ai-drowning-detection-systems-work-in-crowded-pools)

### Inferences
- Danh sách cử chỉ gây nhầm cho Easy FnB nên mở rộng từ các ngành trên: vẫy chào bạn mới tới (giống vẫy taxi), chỉ trỏ (AVA "point to"), đưa đồ cho người cùng bàn (AVA "give/serve"), giơ điện thoại chụp ảnh món ăn, vươn vai, chỉnh tóc, uống nước (đã có ở báo cáo trước). Ba cái đầu là nhầm *có ngữ cảnh*: hướng đầu hướng vào người cùng bàn hay ra lối đi.
- Bài học "cử chỉ được thiết kế": nhà hàng có thể đặt thẻ trên bàn ghi "Giơ tay, giữ 1 giây để gọi phục vụ". Cách này đẩy hành vi khách về một cử chỉ chuẩn, như Signal for Help hay hiệu lệnh trọng tài, nên giảm cả bỏ sót lẫn báo nhầm mà không phải sửa mô hình.

### Gaps
- Không tìm thấy nghiên cứu định lượng riêng về giơ tay khi camera đặt ở trần (≥60°) và người ngồi quay lưng về camera.

## Câu hỏi 6: Áp dụng cụ thể vào pipeline Easy FnB (thay hoặc thêm vào bước nào), công sức trước 14/11 và sau

### Takeaway
Trước demo nên lấy năm thứ rẻ, đều là suy luận của người nghiên cứu, ước lượng công sức: (1) đặc trưng ngữ cảnh kiểu robotaxi (hướng đầu, ngồi hay đứng, nhân viên đã ở bàn chưa) đưa vào cổng/máy trạng thái; (2) crop lại từ khung gốc độ phân giải cao cho người ở xa, theo kiểu cascade lidar → camera; (3) thêm ảnh SCB làm dữ liệu dương cho crop classifier; (4) ép Gemini thành bộ phủ quyết có hiệu chỉnh, chạy bất đồng bộ, đo riêng precision của nó; (5) thẻ bàn "cử chỉ chuẩn" và ngưỡng thời gian hai mức. Để sau demo: YOWOv2-Tiny fine-tune lớp "giơ tay", bộ crop bàn tay HaGRIDv2, tín hiệu nhu cầu thụ động kiểu bán lẻ, LART-style tracklet fusion.

### Cited Findings (nền cho từng đề xuất)
- Ngữ cảnh (vị trí + hướng đầu) là thành phần của nhận dạng vẫy taxi — [Sensors 2023](https://mdpi.com/1424-8220/23/10/4796)
- Cascade phát hiện thô ở xa rồi xác nhận bằng camera — [US 11079767](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11079767)
- Ngưỡng giữ tay >5 s cho nurse call — [US 10368039](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10368039)
- Track → crop tay → MediaPipe → bộ phân loại (Signal for Help) — [Polito 2024](https://iris.polito.it/handle/11583/2992954)
- SCB có box giơ tay, phi thương mại — [GitHub SCB](https://github.com/Whiffe/SCB-dataset)
- VLM zero-shot kém ở cấp cá nhân và nhạy prompt — [arXiv 2606.21861](https://arxiv.org/abs/2606.21861); Gemini Flash 2.0 khó phân biệt cử chỉ zero-shot — [arXiv 2506.20795](https://arxiv.org/abs/2506.20795); few-shot có thể giúp hoặc phản tác dụng — [arXiv 2510.23190](https://www.emergentmind.com/papers/2510.23190)
- YOWOv2-Tiny 10.9M tham số / 2.9 GFLOPs, AVA 14.9–15.6 mAP — [YOWOv2](https://github.com/yjh0410/YOWOv2)
- Bán lẻ báo nhân viên theo tiêu chí hành vi chứ không theo cử chỉ — [PRNewswire Indyme](https://prnewswire.com/news-releases/using-ai-to-identify-conversion-opportunities-in-brick-and-mortar-retail-301210814.html)
- Theo dõi theo tracklet + pose cải thiện AVA (+2.8 / +10 mAP) — [LART](https://arxiv.org/abs/2304.01199)
- V-JEPA + đầu phân loại đơn giản sát skeleton, có thể làm backbone đa tác vụ — [arXiv 2506.20795](https://arxiv.org/abs/2506.20795)

### Inferences (đề xuất; công sức là ước lượng của người nghiên cứu, chưa kiểm chứng)
| # | Kỹ thuật mượn từ | Chèn vào bước nào | Làm gì | Trước 14/11? | Công sức ước tính |
|---|---|---|---|---|---|
| 1 | Robotaxi (cử chỉ + vị trí + hướng đầu) | Cổng luật + máy trạng thái | Thêm đặc trưng từ keypoint sẵn có: người đang ngồi ở ghế của bàn (box ∩ vùng bàn), hướng mũi/tai (ra lối đi hay về người cùng bàn), nhân viên (đã phân loại staff) đang đứng cạnh bàn thì chặn cảnh báo. Giảm nhầm "vẫy chào bạn", "đưa đồ" | Có | 0.5–1 ngày |
| 2 | Lidar → camera cascade | Giữa cổng và crop classifier | Khi cổng mở cho người có box nhỏ, cắt crop từ **khung gốc độ phân giải đầy đủ** (không phải ảnh đã resize cho detector), có thể chạy PE-Core B/16 thay S/16 cho riêng ca này. Nhắm vào lỗi "người ở xa thiếu điểm ảnh" | Có | 0.5 ngày (nếu stream gốc ≥1080p) |
| 3 | Lớp học (SCB) | Dữ liệu huấn luyện crop classifier giơ tay | Cắt crop người có/không giơ tay từ box SCB làm dương/âm phụ, cân bằng với crop quán thật; tách test theo nguồn để thấy domain shift | Có, nếu tải được HF | 0.5–1 ngày |
| 4 | Bệnh viện (5 s) + VLM alarm verification | Máy trạng thái + Gemini | Ngưỡng hai mức: 0.6 s khi điểm trộn cao (tay duỗi thẳng, lòng bàn tay), 1.5–2 s khi mơ hồ. Gemini chạy bất đồng bộ, chỉ được phủ quyết. Prompt cố định, đầu ra JSON, crop có khung đánh dấu người cần xét + 2–3 khung theo thời gian; đo precision/recall riêng của Gemini trên tập đánh giá; kiểm tra tỉ lệ từ chối khi crop có mặt | Có | 0.5–1 ngày |
| 5 | Cử chỉ được thiết kế (Signal for Help, UAV Attention/Cancel) | Ngoài mô hình (UX) | Thẻ bàn hướng dẫn "giơ tay giữ 1 giây". Nhân viên xác nhận trên app sẽ tắt cảnh báo (vai trò "Cancel") | Có | Vài giờ |
| 6 | STAD (YOWOv2-Tiny) | Thay/bổ sung luồng crop + GRU | Fine-tune từ checkpoint AVA với lớp "raise hand/hand wave" trên clip quán; chạy mỗi N khung trên ROI bàn | Không, để sau | 3–5 ngày + đo VRAM trên 3050 |
| 7 | Signal for Help / HaGRIDv2 | Thêm bước sau cổng | Crop vùng cổ tay → detector tay YOLOv10n HaGRIDv2 → phân biệt `palm/stop` với cầm ly hay chạm tóc. Chỉ có ích khi tay ≥ khoảng vài chục px | Không, thử sau | 1–2 ngày thử khả thi |
| 8 | Bán lẻ (nhu cầu thụ động) | Logic trạng thái bàn | Cảnh báo mềm "bàn ngồi >X phút chưa có nhân viên tới / khách nhìn quanh lâu", tách khỏi cảnh báo giơ tay | Có thể làm bản đơn giản | 0.5–1 ngày |
| 9 | LART / V-JEPA | Kiến trúc dài hạn | Đặc trưng theo tracklet (pose + ngoại hình) cho mọi hành vi (giơ tay, ăn xong, đứng dậy rời bàn) thay vì nhiều đầu riêng | Không | Tuần+ |

- Không nên đưa vào trước demo: SiA/OV-STAD (không có tốc độ, không thấy weights), VideoMAE V2 / InternVideo2 cỡ lớn (vượt 4 GB khi chạy chung YOLO26 + PE-Core), YOLO lớp học cỡ 40M+ tham số (mức tăng +1 điểm không đáng chi phí).
- Thông điệp trình bày: nhấn mạnh rằng các ngành có cùng bài toán (lớp học, cứu đuối, bán lẻ) đều thất bại hoặc bị dừng vì báo nhầm và quyền riêng tư, rồi trình bày số báo nhầm mỗi giờ và chính sách không lưu mặt của Easy FnB như điểm khác biệt.

### Gaps
- Chưa có số đo nào cho thấy đặc trưng hướng đầu từ YOLO26-pose (mũi, tai) đủ ổn định ở góc trần nghiêng. Cần đo trên footage của nhóm.
- Chưa có benchmark Gemini (bất kỳ phiên bản nào) cho riêng crop giơ tay CCTV. Mọi đánh giá về Gemini ở đây là suy từ Gemini Flash 2.0 trên cử chỉ HRI và từ VLM khác trong lớp học.
- Chưa biết camera thật của quán stream ở độ phân giải nào. Đề xuất #2 phụ thuộc vào điều này.
