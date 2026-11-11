# Tổng hợp ứng viên công nghệ từ năm báo cáo, đối chiếu với code (5/11/2026)

Mục đích: gom mọi kỹ thuật cụ thể trong năm báo cáo thành một danh sách không trùng, ghi rõ code đã làm tới đâu, cắm vào chỗ nào, và việc nào thử nhanh được trên laptop RTX 3050 4 GB trước khi cam kết. Chưa sửa dòng code nào.

## Ký hiệu

**Nguồn báo cáo**

| Mã | Báo cáo | Ghi chú khi đọc |
|---|---|---|
| CN | Công nghệ AI cho Easy FnB | Viết cho đội 4 người, hackathon 48 giờ, GPU RTX 3060/4060; không biết PE-Core, TensorRT, trang web điện thoại |
| PC | Easy FnB không mua phần cứng | Giả định máy thu ngân iGPU + OpenVINO, đội 3 người (có phương án 2 người) |
| MH | Mô hình mới thay YOLO CLIP | Giả định baseline cũ (CLIP B/32 PyTorch); phần lớn đề xuất A/B đã được làm ở v4 |
| KX | Nhận giơ tay theo khung xương | Giả định ~13 fps; tham số theo khung phải đổi sang giây |
| NK | Bài toán tương tự ngành khác | Mới nhất; có bảng 22 kỹ thuật, 11 việc trước 14/11, 12 việc sau, 10 chỗ vênh |

**File code** (đường dẫn tương đối từ ROOT): `easyfnb_test.py`, `gui_may_chu.py`, `clip_cls.py`, `fnb_common.py`, `KET_QUA.md` nằm trong `vision-test/`; `cham_diem.py`, `cham_su_kien.py`, `thu_gio_tay.py` trong `vision-test/danh_gia/`; `cu_chi.py`, `nhac_lenh.py`, `gan_nhan.py` trong `vision-test/quay/`; `hub.py`, `gemini.py`, `app.py` trong `easy-fnb/server/`; `text.ts`, `voice.ts`, `ZoneEditor.tsx` trong `easy-fnb/src/live/`; `LiveDashboard.tsx`, `LiveStaffPhone.tsx`, `LiveSetup.tsx` trong `easy-fnb/src/pages/live/`.

**Trạng thái**: *đã có* / *có một phần* / *chưa có* / *đã thử, kết quả âm* (đã đo ở v4 và bị bác).

## Những điều quan trọng thấy khi đối chiếu code

1. **Một số đề xuất đã được đo và cho kết quả âm.** Đổi tracker (TrackTrack, BoT-SORT + ReID, ByteTrack giữ track lâu hơn) không tăng điểm, TrackTrack còn bỏ sót người (`KET_QUA.md:36`). yolo26s-pose làm bàn tụt còn 121/137 (`KET_QUA.md:37`). RTMPose-s, hoặc RTMPose chỉ chạy cho người khó, không giúp hoặc tệ hơn (3/7) (`KET_QUA.md:39`). NK vẫn khuyên "thử RTMPose-s" và "đổi tracker", nhưng NK viết khi chưa thấy các số này.
2. **Ultralytics 8.4.202 đang cài** có sẵn các tracker bytetrack, botsort, tracktrack, fasttrack, ocsort, deepocsort. Trọng số YOLOE-26 và `yolo26*-reid.onnx` tải được. Đổi tracker chỉ là đổi `--tracker` (`easyfnb_test.py:636-637, 650-651`).
3. **Nguyên nhân "khách mới" lặp khác với NK đoán.** Server gộp sự kiện bàn theo *bàn* chứ không theo ID track: trùng bàn trong 20 s, hoặc việc cũ còn mở, thì gộp (`hub.py:230-243`, `dedup_s=20` ở dòng 32). Vì vậy sự kiện lặp chỉ lọt khi việc trước đã Xong/Huỷ và cách hơn 20 s. Gốc của nó là bàn nhấp nháy ở edge: có khách → (occ ≤ 0.2) → trống → (occ ≥ 0.8) → có khách (`easyfnb_test.py:258-263`). Cách sửa của NK (máy trạng thái có phiên) vẫn đúng.
4. **Dữ liệu chấm rất mỏng.**
   - Chỉ clip 01 và 02 có vùng bàn và đáp án bàn (`zones.json`, `dap_an.json`), tổng 137 mốc.
   - Clip 01 là time-lapse: 0.5 s trong clip ≈ 15–30 s ngoài đời (`cham_diem.py:25-26`). Mọi hằng số tính bằng giây phải nhân hệ số khi phát lại.
   - Giơ tay chỉ có 7 lần, trong clip 10 và 12; không clip nào có cử chỉ gây nhầm như vuốt tóc.
   - Chưa có footage tự quay (`KET_QUA.md:116`). Vì vậy phép thử trên máy chỉ chứng minh được "chạy được, không làm hỏng, đủ nhanh", không chứng minh được "giảm báo nhầm ngoài đời".
5. **Có thể thử nhiều thứ trên CPU mà không chạy lại model.** `out_v4/*/chi_tiet.json` (`--dump`) đã ghi từng người từng khung: box, điểm luật, độ nâng cổ tay, `ph`, `pst`, đang đi, bàn; và từng bàn: số người, `pd`, cờ có đồ. Thêm `--luu-khung-xuong` thì có cả 17 keypoint (`easyfnb_test.py:587-596`).
6. **Chưa có số VRAM nào trong repo.** Phải đo trước khi thêm model (bước 0).
7. **Không có Gemini API key.** Mọi thay đổi Gemini chỉ kiểm được phần dựng request, luật quyết định và timeout, không đo được độ chính xác. Code đang gọi AI Studio REST bằng `GEMINI_API_KEY` (`gemini.py:19, 59`), chưa đi qua Vertex.

---

## 1. Bảng ứng viên đã gộp trùng

Cột "Thử nhanh?" cho biết thử được trên máy này không, và thử thế nào. Công sức là ước tính cho người viết code; số của NK được ghi khi có.

### 1.1 Trạng thái bàn và tầng sự kiện bàn

| id | Kỹ thuật | Nguồn | Trạng thái trong code | Chỗ cắm vào | Cần tải | Rủi ro VRAM/tốc độ | Công sức | Thử nhanh? |
|---|---|---|---|---|---|---|---|---|
| B01 | Máy trạng thái theo bàn có phiên: TRỐNG → CHỜ_ĐẾN (3–5 s) → CÓ_KHÁCH (phát "khách mới" đúng một lần, mở `session_id`; đổi số khách chỉ gửi cập nhật sau ≥10 s ổn định) → CHỜ_RỜI (30 s, chỉnh 20–60) → KHÁCH_RỜI → CẦN_DỌN; mọi thời gian tính bằng giây | NK (hạng 1); CN (FSM 10 trạng thái); KX (máy trạng thái) | Chưa có. `Table.update` chỉ có 3 trạng thái, bỏ phiếu trên cửa sổ 1 s, bật ở occ ≥ 0.8 và tắt ở ≤ 0.2, không có phiên (`easyfnb_test.py:236-269`, các dòng 258 và 261) | `Table.__init__/update`; nếu cần gắn phiên thì thêm vào `MayChu.event` (`gui_may_chu.py:150-157`) và `Hub.edge_event` (`hub.py:245`) | Không | 0 | NK: 2 ngày cho cả gói B01–B06 | **Đang thử ở nơi khác** (phát lại `out_v4` chi_tiet). Clip 01 cần hệ số thời gian |
| B02 | Cổng che khuất: phần bàn nhìn thấy = 1 − (box người ∩ polygon) / polygon; dưới 60–70% thì khung đó "không quan sát", không cập nhật điểm bẩn, đồng hồ tạm dừng | NK; PC (độ tin cậy theo bàn thay vì báo cứng) | Chưa có: `p_dirty` cập nhật bất kể có người che (`easyfnb_test.py:455-465`) | Vòng bàn trong `run_clip` (quanh dòng 458): mask `cv2.fillPoly` → cờ `visible` truyền vào `Table.update` | Không | Dưới 0.5 ms/bàn/khung (CPU) | 2–3 giờ | Nằm trong phép thử phát lại đang chạy |
| B03 | Điểm bẩn liên tục (EMA trên khung nhìn thấy được) + hysteresis: bẩn khi > 0.7 trong ≥3 s, sạch khi < 0.3 trong 5–10 s (CN: giữ 2–3 lần đo hoặc 5–10 s) | NK; CN | Có một phần: trung bình cửa sổ `win`, ngưỡng 0.5 (`easyfnb_test.py:245-251`) | `Table.update` | Không | 0 | Trong B01 | Như B01 |
| B04 | "Đã dọn" chỉ khi track nhân viên đã ghé bàn và bàn sạch 5–10 s (không có nhân viên ghé thì cần ≥10 s sạch, không bị che); "cần dọn" chỉ xuất hiện sau "khách rời" | NK; Canon (KX, NK); CN (xác nhận theo vị trí) | Chưa có: `da_don` chỉ cần hết bẩn và occ ≤ 0.2 (`easyfnb_test.py:266-268`). Biết người nào là nhân viên và ở bàn nào (`p['staff']`, `p['table']`, dòng 433) nhưng chưa dùng cho bàn | `run_clip` đếm nhân viên trong vùng bàn (cạnh dòng 459) → tham số `staff_near` | Không | 0 | 3–6 giờ | Một phần: clip 01 không có cảnh dọn bàn rõ ràng; cần footage tự quay |
| B05 | Còn đồ cá nhân (túi, áo, điện thoại) trên bàn hoặc ghế thì kéo dài CHỜ_RỜI tới vài phút | NK | Chưa có: `ITEMS` chỉ gồm đồ ăn và ly (`easyfnb_test.py:33-35`); COCO có backpack 24, handbag 26, cell phone 67 | `det.predict(classes=...)` (dòng 372); tách `owner` theo loại đồ (448-454) | Không | 0 (cùng detector) | 2–3 giờ | Không có clip có túi bỏ lại; cần tự quay |
| B06 | Gán người vào bàn bằng điểm giữa hông (keypoint 11, 12), dự phòng bằng giữa vai; thêm **vùng ghế** cho mỗi bàn; chỉ đếm người đang ngồi (góc hông–gối–cổ chân < 140°; CN: tâm người nằm trong polygon kiểu PETI) | NK; CN | Có một phần: điểm neo ở giữa box, cao 60% (`easyfnb_test.py:408`); gán bàn gần nhất trong 0.45 × chiều cao người (`easyfnb_test.py:432`, `easyfnb_test.py:216-223`); bỏ người đang đi (`easyfnb_test.py:422-423`). Web chỉ vẽ được polygon bàn (`ZoneEditor.tsx:14-17`) | `run_clip` (dòng 408 và 432); schema vùng: `zones.json`, `MayChu._scale` (`gui_may_chu.py:105-108`), `Hub.set_zones` (`hub.py:192-203`), `ZoneEditor.tsx` | Không | 0 | 3–4 giờ + vẽ lại vùng | Có: phần mở rộng của phép thử phát lại đang chạy, dùng `khung_xuong.npz` từ bước 0 |
| B07 | Crop vuông lấy cả viền ngữ cảnh quanh polygon bàn (ACPDS: thắng crop sát polygon ở mọi cấu hình) | NK | Có một phần: `table_crop` nới 10% (`easyfnb_test.py:125-127`), rồi `square()` đệm viền xám (`fnb_common.py:8-21`, gọi ở `clip_cls.py:129`), nên không có ngữ cảnh thật | `table_crop` | Không | 0 | 1 giờ | Có: cắt lại 91 ảnh bàn bằng `tao_anh_ban_test.py`, chấm bằng `clip_cls.py thu --backbone pe_core_s16`. Có thể gộp vào phép thử ảnh bàn sạch đang chạy |
| B08 | Danh sách đồ của quán lấy từ ảnh "bàn sạch" (nút "chụp bàn sạch"; bỏ box COCO trùng IoU cao với danh sách khi tính bẩn), bản rẻ | NK (hạng 8) | Chưa có | Phần tính `owner`/`obs` (`easyfnb_test.py:448-464`); nút trong `LiveSetup.tsx` + route mới trong `app.py` + `MayChu` | Không | 0 | 2–4 giờ | Ít giá trị cho bản demo: bàn đang chấm bằng PE-Core zero-shot (`obs = pd`, dòng 461-462), không đếm đồ |
| B09 | Bộ nhớ patch kiểu AnomalyDINO trên PE-Core S/16 hoặc DINOv2 ViT-S/14, 3–5 ảnh bàn sạch cho mỗi bàn | NK (hạng 11, "nếu dư") | Chưa có: `ClipCls` chỉ lấy embedding đã gộp (`clip_cls.py:125-133`) | Lớp mới trong `clip_cls.py`, nạp qua `load_small_model` (`easyfnb_test.py:92-105`) làm `table_m` | Không (PE-Core S/16 đã có trong cache) hoặc DINOv2-S ~85 MB (Apache-2.0); code AnomalyDINO chưa kiểm giấy phép | Thêm 0–50 MB; vài ms mỗi bàn mỗi giây | Bản thử 2–3 giờ, bản đủ 1.5 ngày | **Đang thử ở nơi khác** (`danh_gia/anh_ban_test`) |
| B10 | Gửi Gemini cặp ảnh "bàn sạch đã lưu" + ảnh hiện tại cho "cần dọn" (ý tưởng CYWS; bớt ảo giác "bàn ăn thì có bát đĩa" kiểu POPE) | NK | Chưa có: `Gemini.verify` nhận một ảnh (`gemini.py:109-118`) | `MayChu.event`, `app.edge_event` (`app.py:290-297`), `Hub.edge_event/_verify`, `Gemini.verify` | Không | Thêm khoảng 280–560 token mỗi lần gọi | 2–4 giờ (gộp với V01) | Chỉ kiểm được gói request (T4); độ chính xác chờ key |
| B11 | Phân loại thẳng bàn sạch/bẩn, đồ vật chỉ là bằng chứng phụ (CN: thang 3–4 mức đầy/dở/gần hết/hết) | NK; CN | **Đã có**: `--table-model clip`, PE-Core S/16 zero-shot (`easyfnb_test.py:456-462`; `KET_QUA.md:53, 63`) | — | — | — | — | Đã đo 84/91 |
| B12 | Bàn chạy ~1 fps; detector đồ vật mỗi 5–10 s hoặc ngay sau "khách rời"; đặt lịch theo giây chứ không theo khung (MH: detect mỗi 6 khung) | NK (hạng 4); PC; MH | Có một phần: `--det-every 3`, `--table-every 4` tính theo khung (`easyfnb_test.py:370, 456, 608, 625`) | Điều kiện ở dòng 370 và 456; gọi detector khi `Table.update` trả `khach_roi` | Không | Bớt tải (detector 9 ms, `KET_QUA.md:77`) | 2 giờ | Có, gần như không sửa code: chạy với tham số lớn (T2) |
| B13 | Bộ phân loại bàn 4 lớp fine-tune; VLM gắn nhãn 10 pha bữa ăn theo JSON; làm mượt HSMM | MH (sau demo); CN | Chưa có | `clip_cls.py train`; `Table` | Không | 0 | 2–4 ngày + dữ liệu | Không (thiếu nhãn) |
| B14 | YOLOE-26 prompt chữ ("plate, chopsticks, tissue, tray") để tự gán nhãn rồi fine-tune detector tập đóng; SAHI cắt vùng bàn độ phân giải cao cho đồ nhỏ; CN: Grounding DINO gán nhãn offline | NK (sau); MH (sau); CN | Chưa có | Công cụ offline trong `train/` | Trọng số YOLOE-26 (AGPL-3.0), tải qua Ultralytics | Không chạy trong vòng sống | ~1 tuần | **Đang thử ở nơi khác** (prompt chữ cho đồ trên bàn) |
| B15 | Ngưỡng theo ngữ cảnh (p75 nhắc, p90 báo, theo khung giờ và cỡ nhóm); bảng ngưỡng khởi điểm (chào khách 60/120/180 s…); điểm khẩn 0–100; tầng P1/P2/P3; mô hình sống sót; dự đoán giờ bàn trống | CN | Chưa có: ưu tiên cố định (`hub.py:22`), chuyển người sau 45 s (`hub.py:32, 437-462`) | `Hub.tick`, `Hub._assign` | Không | 0 | 1–3 ngày | Không (cần log nhiều ngày) |
| B16 | Nhu cầu thụ động (bàn ngồi X phút chưa có nhân viên ghé); nhóm khách (ngồi cùng bàn 2 phút) | NK (sau); CN (`seated_unattended`) | Chưa có | `Table` (cần B01 và B04 trước) | Không | 0 | 0.5–1 ngày | Không (clip ≤ 27 s) |
| B17 | Tín hiệu đồ vật: ly cạn, đĩa trống ở buffet, nồi lẩu cạn (cân hoặc công suất bếp từ), ăn xong chưa tính tiền, khách bỏ về | CN | Chưa có | — | — | — | Nhiều ngày | Không (sau hackathon) |

### 1.2 Bám người và khoá sự kiện

| id | Kỹ thuật | Nguồn | Trạng thái trong code | Chỗ cắm vào | Cần tải | Rủi ro VRAM/tốc độ | Công sức | Thử nhanh? |
|---|---|---|---|---|---|---|---|---|
| T01 | ByteTrack → TrackTrack (Track-Aware Initialization) hoặc BoT-SORT + ReID `model: auto`, `gmc_method: none`, `track_buffer` 3–5 s | MH; NK (hạng 9); CN (Roboflow `trackers`) | **Đã thử, kết quả âm** (`KET_QUA.md:36`). Cấu hình có sẵn trong `models/`: `botsort_reid.yaml`, `tracktrack_cam.yaml`, `tracktrack_thap.yaml`, `bytetrack_60.yaml`. Ultralytics 8.4.202 còn có fasttrack, ocsort, deepocsort | `--tracker` | `yolo26*-reid.onnx` nếu cần ReID riêng | Cần đo fps | 0.25 ngày | Không đề xuất thử lại. Chỉ nên đo lại nếu N03 (kế thừa nhãn) thất bại, và đo bằng số lần đổi ID trên người giơ tay hoặc nhân viên, không phải điểm bàn |
| T02 | Track mới phải qua "thử việc" (`probationAge` của NvDCF, hoặc ≥2 khung liên tiếp); giữ track bị mất tới 60 khung | NK | Có một phần: `min_track_len: 3` (tracktrack), `track_buffer: 60` (`bytetrack_60.yaml`) | File yaml | Không | 0 | 0.1 ngày | Đã nằm trong lần thử T01 |
| T03 | Khoá sự kiện gọi theo `table_id` kèm cooldown; gộp mọi track ở cùng bàn thành một yêu cầu | MH; KX; CN (gộp trong 60 s, một cảnh báo mở cho mỗi bàn mỗi nhu cầu) | Có một phần: cooldown 5 s theo track (`easyfnb_test.py:435, 611`); server gộp theo bàn 20 s (`hub.py:230-243`) | `run_clip` dòng 435: khoá theo `tb.name` khi người có bàn | Không | 0 | 1 giờ | Có, phát lại CPU; nhưng clip 10/12 không có vùng bàn |
| T04 | Roboflow `trackers` (Apache-2.0, sau demo vì AGPL); homography sàn + nối track nhiều camera (OSNet); tránh BoxMOT (AGPL) và Metropolis MTMC | CN; MH | Chưa có | — | `trackers`; OSNet 2.2M (trọng số học thuật) | — | 1–3 ngày | Không cần (một camera) |

### 1.3 Giơ tay gọi phục vụ

| id | Kỹ thuật | Nguồn | Trạng thái trong code | Chỗ cắm vào | Cần tải | Rủi ro VRAM/tốc độ | Công sức | Thử nhanh? |
|---|---|---|---|---|---|---|---|---|
| G01 | **Cổng mềm**: mở khi cổ tay > vai, hoặc khuỷu > vai, hoặc cổ tay > mũi, hoặc box chạm mép khung mà mất vai. Thêm **đường "chỉ RGB"** cho track ở mép hình: chạy head PE-Core vài khung một lần, ngưỡng cao hơn, giữ lâu hơn | KX (P0) | Có một phần: chế độ `hop` chỉ hỏi head khi `hand_lift > 0.3` (`easyfnb_test.py:385-393`), mà `hand_lift` trả None khi không thấy vai hoặc cổ tay (`easyfnb_test.py:168-169`). Vì vậy người bị cắt ở mép không bao giờ được hỏi; đó là một trong hai ca sót (`KET_QUA.md:27`) | `run_clip` dòng 387-388 (thêm cờ "box chạm mép") | Không | Thêm vài lần chạy head B/16 mỗi giây | 0.5 ngày | **Có (T1)** |
| G02 | Giữ tay hai mức: 0.6 s khi tín hiệu rõ, 1.5–2 s khi mơ hồ; ngưỡng biên độ theo chiều cao box. Các mốc khác: CN ≥0.8 s trong ≥70% khung; PC ≥1 s; KX báo 0.3–0.5 s sau đỉnh và không xuống dưới 0.40 s | NK (hạng 6); CN; PC; KX | Có một phần: một mức `--hand-s 0.6`, tỉ lệ ≥0.7 (`easyfnb_test.py:418-431, 610`); biên độ `lift > 0.6` theo bề ngang vai (`easyfnb_test.py:154`) | `run_clip` dòng 430-431 | Không | 0 | 2–3 giờ | **Có (T1, phần CPU)**. Clip stock không có cử chỉ gây nhầm, nên chỉ chứng minh được "không mất recall, không tăng trễ" |
| G03 | Cổng ngữ cảnh: chỉ xét người đang ngồi trong vùng ghế của một bàn; không báo nếu nhân viên đang ở vùng bàn đó; hướng đầu (mũi, tai) chỉ ghi log. CN: 6DRepNet360 nằm trong danh sách cắt | NK (hạng 6); Canon; CN | Có một phần: đã bỏ nhân viên (`easyfnb_test.py:431`) và người đang đi (`easyfnb_test.py:423`); chưa có vùng ghế, chưa xét nhân viên đứng ở bàn | `run_clip` dòng 431 (cần B06) | Không | 0 | 0.5 ngày | Một phần (cần vùng ghế + footage có nhân viên ở bàn) |
| G04 | Máy trạng thái theo track: IDLE → CANDIDATE → ALERT → COOLDOWN; lọc trung vị 3–5 khung; giữ N khung; báo sớm khi P(gọi) − max P(gây nhầm) ≥ 0.4; T_off < T_on; khoá 5–10 s; nội suy chỗ hở ≤3 khung. CN: EMA + hysteresis, cooldown 60 s mỗi bàn hoặc tới khi nhân viên vào | KX; CN | Có một phần: lịch sử 0.6 s + cooldown 5 s theo track (`easyfnb_test.py:418-437`) | Lớp `HandFSM` gọi trong `run_clip` | Không | 0 | 0.5–1 ngày | Có, phát lại CPU (cùng T1); nhánh báo sớm cần đầu ra nhiều lớp (G05) |
| G05 | GRU 2 lớp ~22k tham số trên cửa sổ nhân quả 1–1.5 s. Chuẩn hoá theo tâm và bề ngang vai; 7 lớp (gọi, vẫy, chạm đầu/tóc, uống/ăn, chỉ, vươn vai, khác); nhãn theo pha A/S/D; tăng cường (che thân dưới, rơi 10–20% khớp, xoay ±15–30°, tốc độ 0.5–2×, lật trái/phải); chạy chế độ chỉ ghi log. CN: GRU, 1D-CNN hoặc LightGBM | KX (P1); MH; CN | Có một phần, chỉ phần hạ tầng: lưu khung xương (`easyfnb_test.py:404-405, 587-596`), chương trình nhắc lệnh (`nhac_lenh.py`), công cụ gán nhãn A/S/D (`gan_nhan.py`), danh sách cử chỉ (`cu_chi.py:8-24`). Chưa có model, chưa có footage (`KET_QUA.md:116-118`) | Module mới (vd `gio_tay_gru.py`), gọi sau dòng 418 | Không, nếu chỉ dùng footage tự quay | Dưới 1 ms mỗi track trên CPU (ước tính) | 1.5–2 ngày + quay và gán nhãn | **Không**: chỉ có 7 lần giơ tay có nhãn. KX cũng nói GRU không chữa được hai ca sót hiện tại |
| G06 | Tiền huấn luyện trên NTU-120 2D + BK-SAD; ST-GCN++ fine-tune từ NTU-60 2D (MMAction2, đóng băng các block đầu); MotionBERT-Lite; PoseC3D | KX (P1/P3); MH (sau); CN (PoseC3D bị cắt) | Chưa có | Như G05 | `ntu120_2d.pkl` 1.24 GB (chỉ học thuật), BK-SAD (không ghi giấy phép), checkpoint ST-GCN++ (Apache-2.0). **Cần người dùng duyệt tải dataset** | ST-GCN++ "vài ms" CPU (ngoại suy) | 1–2 ngày | Không |
| G07 | Trộn muộn bằng hồi quy logistic 5 đầu vào (log-odds GRU, log-odds head đã làm mượt, cờ "head có chạy", độ tin cậy khớp tay, log chiều cao box); không đưa điểm PE-Core vào GRU trước demo | KX; NK (chốt trộn muộn) | Chưa có: đang là luật OR `score > 0 or ph ≥ th` (`easyfnb_test.py:417`) | `run_clip` dòng 410-417 | Không | 0 | 0.5 ngày | Không, tới khi có G05 và dữ liệu |
| G08 | Tích luỹ bằng chứng yếu: điểm crop 0.25 giữ khoảng 1 s cộng hình học rõ thì đủ báo | KX | Chưa có: một ngưỡng `--hand-th` (`easyfnb_test.py:618`), demo dùng 0.35 (`KET_QUA.md:64`) | `run_clip` dòng 417 | Không | 0 | 2 giờ | **Có (T1)** |
| G09 | RTMPose chỉ cho track qua cổng mềm hoặc box nhỏ, tối đa K crop mỗi khung; thử bản s thay bản m | NK (hạng 4); MH (RTMPose-t/s trên track nhỏ); KX (RTMPose-m cho track nhỏ); PC | **Đã thử, kết quả âm** với tiêu chí cũ: chế độ `yeu`/`gan_vai` (`easyfnb_test.py:194-213`) và RTMPose-s đều chỉ bắt 3/7 (`KET_QUA.md:39`). Bản demo chạy RTMPose-m cho mọi người (`KET_QUA.md:103`), xuống 11 fps ở clip đông (`KET_QUA.md:19`) | `refine_pose`: tiêu chí chọn mới (box < ~150 px, hoặc thiếu vai/cổ tay, hoặc `hand_lift > −0.6`) + giới hạn K, giữ bản **m** | Đã có (rtmlib tự tải ONNX) | Chính là phần tốn fps | 0.5 ngày | **Có (T2)**, nhưng chỉ với tiêu chí mới; không thử lại bản s |
| G10 | Nâng lên yolo26s-pose | MH | **Đã thử, kết quả âm**: bàn tụt còn 121/137 (`KET_QUA.md:37`) | — | — | — | — | Không |
| G11 | RTMO-s một tầng qua rtmlib (Apache-2.0) thay YOLO26-pose | CN (giờ 4–16); MH (sau demo) | Chưa có | `run_clip` dòng 359-366 | RTMO-s ONNX (Apache-2.0) | Chưa đo trên 3050 | 1 ngày | Đo tốc độ được, nhưng đổi lõi pipeline trước demo thì rủi ro |
| G12 | Crop độ phân giải cao từ luồng chính cho người ở xa (robotaxi: lidar rồi camera; PC: luồng 720p thứ ba, hoặc crop luồng chính 1–2 fps) | NK; PC | Chưa có: một nguồn ảnh (`easyfnb_test.py:303`) | `run_clip` + nguồn thứ hai | Không | Thêm một luồng giải mã | 1 ngày | Không (clip chỉ có 720p) |
| G13 | Thẻ trên bàn: "Giơ tay, giữ 1 giây để gọi phục vụ" | NK | Chưa có (không phải code) | In ấn | Không | 0 | Vài giờ | Không cần thử trên máy |
| G14 | Thêm cử chỉ gây nhầm: chụp món bằng điện thoại, cụng ly "dô", đưa đồ cho người khác, nhân viên giơ khay, chỉ bàn, vẫy đồng nghiệp | NK; KX; CN | Có một phần: `cu_chi.py:8-24` đã có 10 cử chỉ (vuốt tóc, gãi đầu, uống, chỉ tay, vươn vai, nghe điện thoại, chỉnh kính, lau mặt, chống cằm, vẫy bạn) | Thêm mã vào `cu_chi.py` | Không | 0 | 0.5 giờ | Không cần |
| G15 | Luật cử chỉ khác: vẫy (≥2 chu kỳ trong 1.5 s), đứng dậy tại bàn, giơ ly rỗng (cổ tay trên vai + box ly chồng lên cổ tay), nhìn quanh tìm nhân viên. Quyết định sản phẩm: vẫy chào hay vẫy gọi | CN; KX | Chưa có | `hand_up` (`easyfnb_test.py:132-156`) | Không | 0 | 0.5–1 ngày | Không đáng làm trước demo |
| G16 | Mô hình RGB khác: detector "người giơ tay" fine-tune trên SCB; RTMW 133 điểm, crop tay HaGRIDv2, MediaPipe Gesture (lòng bàn tay mở hay đang cầm ly); MoViNet-A0, YOWOv2-Tiny, LART, V-JEPA | CN (SCB "song song đáng làm"); MH, KX, NK (sau) | Có một phần: ảnh SCB đã dùng để train head crop (`train/build_hand_v2.py`, `train/train_tay_clip.py`) | — | HaGRIDv2 (CC BY-SA), RTMW ONNX, YOWOv2 (giấy phép mâu thuẫn) | Nặng hơn | 3–5 ngày mỗi hướng | Không |
| G17 | Dữ liệu tổng hợp: MDM text-to-motion đổi sang COCO-17 với camera giả 2.5–3.5 m nghiêng 20–60°; hoặc video sinh bằng Wan 2.2 (kiểu OmniFall) | KX (sau); NK (sau) | Chưa có | — | Mô hình sinh vài GB | GPU nặng | 1–2 tuần | Không |

### 1.4 Nhân viên hay khách

| id | Kỹ thuật | Nguồn | Trạng thái trong code | Chỗ cắm vào | Cần tải | Rủi ro VRAM/tốc độ | Công sức | Thử nhanh? |
|---|---|---|---|---|---|---|---|---|
| N01 | **Gallery nhân viên đăng ký theo ca.** Nút "Đăng ký nhân viên ca này"; mỗi người đứng hoặc đi 10–20 s → 30–100 crop. Embedding PE-Core trên phần giữa box (60% bề ngang × 70% chiều cao từ trên xuống), lấy trung bình theo tracklet. Điểm = giống nhất với gallery nhân viên − giống nhất với kho mẫu khách; probe cũ làm phiếu thứ hai. Khi demo, nhân viên mặc tạp dề hoặc đội mũ màu đậm nhưng không tối. CN thay bằng histogram HSV thân áo + vùng chỉ nhân viên vào + ArUco/số in | NK (hạng 5); CN | Có một phần: probe `nhanvien_clip_v1.pt` chạy mỗi 6 khung trên crop cả box (`easyfnb_test.py:384, 395, 628`), trung bình 3 s, ngưỡng 0.5 (`easyfnb_test.py:424-429`). Chưa có gallery, chưa có nút | Lớp mới trong `clip_cls.py`; gọi ở `run_clip` dòng 395; nút trong `LiveSetup.tsx` + route trong `app.py`; edge nhận gallery qua vòng `_run` của `MayChu` (`gui_may_chu.py:195-215`) | Không (dùng lại bộ mã hoá đã nạp) | 0 VRAM thêm; vài ms mỗi crop | 1–1.5 ngày | **Có (T3)** |
| N02 | Điểm hành vi: cộng khi track đi qua vùng bếp/quầy hoặc ghé ≥3 bàn trong 2 phút; trừ khi ngồi > 5 s. Ban đêm camera hồng ngoại mất màu nên phải dựa vào hành vi | NK; CN | Chưa có; web chưa có loại vùng bếp/quầy | `run_clip` theo track; schema vùng như B06 | Không | 0 | 0.5 ngày | Không (clip ngắn, không có bếp) |
| N03 | Nhãn dính theo track (vào khi p > 0.8, ra khi p < 0.3) + kế thừa nhãn khi ByteTrack tạo ID mới gần vị trí cũ (so embedding; có thể dùng `yolo26*-reid.onnx`) | NK | Có một phần: trung bình 3 s, ngưỡng 0.5, không trễ, không kế thừa (`easyfnb_test.py:424-429`) | `run_clip` dòng 424-429 | Không, hoặc `yolo26n-reid.onnx` (nhỏ) | ~0 | 2–4 giờ | **Có (T3)** |
| N04 | Xét nhân viên **trước** luật giơ tay; bỏ mọi cử chỉ của track nhân viên; không đếm nhân viên vào số khách | NK; Canon | **Đã có**: `calling = not staff and …` (`easyfnb_test.py:431`); đếm khách bỏ nhân viên (`easyfnb_test.py:459`) | — | — | — | — | — |
| N05 | Các phương án khác: KMeans embedding kiểu thể thao (chỉ làm slide); YOLO26n-reid 2.8M; tự phát hiện nhân viên qua danh tính lặp lại; thẻ BLE/UWB (CN bác); nhận mặt nhân viên kiểu Hikvision (NK bác: dữ liệu sinh trắc) | NK; CN | Chưa có | — | — | — | — | Không |
| N06 | Gửi kèm Gemini một ảnh mẫu đồng phục (ví dụ few-shot duy nhất NK cho phép) | NK | Chưa có | `Gemini.verify` | Không | Thêm ~280 token | 1 giờ | Chờ key |

### 1.5 Xác minh bằng Gemini

| id | Kỹ thuật | Nguồn | Trạng thái trong code | Chỗ cắm vào | Cần tải | Rủi ro VRAM/tốc độ | Công sức | Thử nhanh? |
|---|---|---|---|---|---|---|---|---|
| V01 | **Đầu vào nhiều frame.** Ring buffer khoảng 3 s ở edge. Ảnh A: dải 2×2 crop người ở t−1.5, t−1, t−0.5 và t (nới box ~30%, in giờ lên từng ô), độ phân giải `medium`. Ảnh B: toàn cảnh hoặc vùng bàn ở `low`, khung đỏ quanh người cần xét kèm số bàn. MH đề xuất 3 crop `low` + 1 cảnh `medium` (~1,400 token); CN đề xuất 4–8 frame tới 768 px | NK (hạng 3); MH; CN | Chưa có: mỗi sự kiện chỉ gửi một crop (`easyfnb_test.py:441-443`; `gui_may_chu.py:150-157`); `mediaResolution` LOW cho mọi ảnh (`gemini.py:74-75`) | `run_clip`: deque crop theo track; `MayChu.event` thêm `images[]`; `app.edge_event`; `Hub.edge_event` lưu nhiều ảnh (`hub.py:267-270`); `Gemini._body/verify` đặt độ phân giải cho từng ảnh | Không | Giữ cả khung 720p trong 3 s ≈ 160 MB RAM, nên chỉ giữ crop theo track hoặc khung thu nhỏ; 0 VRAM | 1–1.5 ngày | **Một phần (T4)**: dựng gói request offline; độ chính xác chờ key |
| V02 | **Schema enum có `KHONG_CHAC`.** Thêm `alt` (lý do khác), checklist (`hand_above_head`, `held_or_waved_across_frames`, `wearing_staff_uniform`), `image_quality`, lý do ≤15 từ. Luật mới: chỉ rút cảnh báo khi `KHONG_GOI` + ảnh ok + checklist khớp; `KHONG_CHAC` hoặc ảnh kém thì giữ cảnh báo, gắn nhãn "Chưa xác minh"; bỏ ngưỡng tự tin 0.6, `confidence` chỉ ghi log. Schema của MH vẫn có `confidence` | NK (hạng 3); MH | Có một phần: schema boolean + confidence (`gemini.py:38-45`); rút khi bác với confidence ≥ 0.6 (`hub.py:319-320`) | `VERIFY_SCHEMA`, `Gemini.verify` (`gemini.py:109-118`); `Hub._verify` (`hub.py:293-327`) | Không | 0 | 0.5 ngày | **Một phần (T4)**: kiểm luật quyết định bằng phản hồi giả |
| V03 | Schema bàn: `TRONG_SACH / TRONG_CAN_DON / CO_KHACH / KHACH_RA_NGOAI_TAM / KHONG_CHAC` + `items_vs_clean_reference`, `personal_belongings_present`, `people_within_1m`; chỉ báo khi `TRONG_CAN_DON`, không có đồ cá nhân, không có người trong 1 m; crop bàn ở `medium` hoặc `high`. CN: crop ≤384 px (258 token), gộp nhiều bàn vào một request | NK; MH; CN | Có một phần: boolean `needs_clearing` (`gemini.py:31-36, 42-44`) | Như V02 | Không | 0 | 2–3 giờ | Như V02 |
| V04 | Prompt theo công thức NVIDIA: một dòng vai trò, tiêu chí, danh sách loại trừ bằng tiếng Việt, xét từng người một, `temperature 0`; mỗi kiểu báo nhầm mới gặp được thêm vào danh sách loại trừ; chỉnh trên 10–50 clip có nhãn | NK | Có một phần: prompt đã có danh sách loại trừ (`gemini.py:25-28`); chưa đặt temperature | `VERIFY_PROMPT`, `Gemini._body` (`gemini.py:69-78`) | Không | 0 | 2 giờ | Chờ key |
| V05 | Timeout 2–3 s + circuit breaker (sau N lỗi liên tiếp thì ngừng gọi 60 s và dùng luật cục bộ) + ghi đường đi của từng cảnh báo (xác nhận/bác/hết giờ/lỗi/không chắc). MH đề xuất 3–5 s; NVIDIA mặc định 5 s | NK (hạng 7); MH | Có một phần: timeout httpx 25 s (`gemini.py:61`); khi lỗi thì mở lại việc cho nhân viên (`hub.py:299-307`); trạng thái `error` hiện "Gemini lỗi, chưa kiểm tra" (`text.ts:113-114`) | `Gemini.generate`; `Hub._verify` (bọc `asyncio.wait_for`) | Không | 0 | 2–3 giờ | **Có (T4, CPU)** |
| V06 | Hiển thị ba trạng thái: "Chưa xác minh" có màu và biểu tượng riêng trên app và dashboard; "cần dọn" không chắc chỉ hiện trên dashboard, không đẩy thông báo | NK (hạng 7) | Có một phần: `verifyBadge` có 5 nhãn (`text.ts:105-117`); điện thoại có chip "Gemini đang kiểm tra" (`LiveStaffPhone.tsx:115`) | `text.ts`, `LiveStaffPhone.tsx`, `LiveDashboard.tsx` | Không | 0 | 2–3 giờ | Có (`npm run dev` + sự kiện giả) |
| V07 | Báo trước, xác minh sau: đẩy cảnh báo ngay, Gemini bác thì rút; "cần dọn" chờ xác nhận | MH; PC; CN; NK | **Đã có** (`hub.py:271-291`; `hold_until_verified` chỉ gồm `needs_clearing`, dòng 31) | — | — | — | — | — |
| V08 | Đặt `media_resolution` riêng cho từng ảnh: `low` 280, `medium` 560, `high` 1120 token | MH; PC; NK | Có một phần: LOW cho cả request (`gemini.py:74-75`) | `Gemini._body` | Không | — | 1 giờ | Trong V01 |
| V09 | Thinking `MINIMAL`; A/B với `low` trên tập âm khó; không thêm ví dụ few-shot gọi/không gọi | NK; MH | **Đã có** `MINIMAL` (`gemini.py:76-77`) | — | — | — | — | A/B chờ key |
| V10 | A/B ba kiểu đầu vào (crop đơn / crop + ngữ cảnh / dải + ngữ cảnh), dải `medium` so với `high`, crop gốc so với crop mờ; chạy qua Batch API trên 60–100 sự kiện có nhãn | NK (hạng 3, 10) | Chưa có | Script mới trong `danh_gia/`, dùng `server/gemini.py` | Không | Dưới 0.1 USD | 0.5 ngày | **Không** (chưa có key); chuẩn bị sẵn bộ ảnh ở T4 |
| V11 | Chọn model `gemini-3.5-flash-lite` (MH, NK, CN) hay `gemini-3.1-flash-lite` rẻ hơn (PC); bỏ các ID 2.5 và 2.0 | MH; NK; CN; PC | **Đã có**: mặc định 3.5-flash-lite, đổi bằng `GEMINI_MODEL` (`gemini.py:60`) | — | — | — | — | — |
| V12 | Gọi qua Vertex / Agent Platform (`google-genai`, `vertexai=True`, tài khoản dịch vụ của Cloud Run) để dùng được credit và không lộ khoá | MH; PC | Chưa có: REST AI Studio + khoá (`gemini.py:19, 59, 86-87`) | Nhánh Vertex trong `Gemini` | `google-genai` (pip) | 0 | 0.5 ngày | Không trên máy này (cần dự án GCP) |
| V13 | Đọc `usage_metadata` để biết chi phí thật; đặt budget alert | MH; PC | Chưa có: `_text` bỏ phần usage (`gemini.py:138-147`) | `Gemini.generate` | Không | 0 | 1 giờ | Chờ key |
| V14 | VLM tại chỗ làm dự phòng (Qwen3-VL-2B, SmolVLM2, Gemma 4 E2B/E4B, PaliGemma 2), quyết định bằng xác suất token; fine-tune verifier với thưởng bất đối xứng | NK (sau); MH (sau); CN (cần GPU 24 GB) | Chưa có | Nhánh dự phòng trong `Hub._verify` | Qwen3-VL-2B ~4–5 GB (Apache-2.0) | **Không vừa** 4 GB khi chạy cùng pipeline (MH: Gemma 4 E2B 4-bit ~3 GB đã "chật") | 3–5 ngày | Không trước demo |
| V15 | Xem clip 10–30 s bằng `gemini-3.8-flash`; tóm tắt ca qua Batch; mô tả sự kiện + embedding để tìm kiếm | CN; PC | Có một phần: trợ lý hỏi đáp dựa trên nhật ký và tóm tắt ca (`gemini.py:120-135`; `app.py:241, 278`) | `app.py`, `gemini.py` | Không | 0 | 1–3 ngày | Không cần cho lõi demo |

### 1.6 Điều phối, cảnh báo, app nhân viên

| id | Kỹ thuật | Nguồn | Trạng thái trong code | Chỗ cắm vào | Cần tải | Rủi ro VRAM/tốc độ | Công sức | Thử nhanh? |
|---|---|---|---|---|---|---|---|---|
| D01 | Tự đóng cảnh báo gọi khi track nhân viên bước vào vùng bàn (Canon). CN: chuyển ARRIVED khi nhân viên ở trong ~1–1.5 m ≥2 s; nếu người khác tới trước thì đóng việc cho người đó | NK (hạng 7); KX; CN | Chưa có: chỉ "cần dọn" tự đóng khi camera thấy `da_don` (`hub.py:254-258`); "gọi" chỉ đóng bằng nút | Edge: sự kiện mới `nhan_vien_toi` từ `run_clip`; server: `EDGE_KIND` + `Hub.edge_event` (`hub.py:16-17, 245-259`) | Không | 0 | 3–4 giờ | **Có (T3)**: vẽ vùng bàn cho clip 06/07 |
| D02 | Nút "Đúng/đã xử lý" bên cạnh "Báo nhầm" + kho mẫu âm khó (crop, các frame, embedding, đặc trưng luật, đầu ra Gemini) | NK (hạng 7); CN; PC; MH; KX | Có một phần: "Báo nhầm" chỉ có trên dashboard (`LiveDashboard.tsx:95-98` → `Hub.cancel`, `hub.py:377-381`); điện thoại chỉ có Nhận và Xong (`LiveStaffPhone.tsx:125-139`); crop của mọi cảnh báo đã lưu (`hub.py:267-270`) nhưng nhãn chưa được ghi ra file | `Hub.cancel/done` ghi JSONL vào `data/`; thêm nút trên `LiveStaffPhone.tsx` | Không | 0 | 2–3 giờ | Có (server cục bộ, không cần phép thử riêng) |
| D03 | Hàm chi phí giao việc + Hungarian (`scipy`/OR-Tools) + thang leo T0, +20, +45, +90, +180 s; giới hạn tần suất mỗi nhân viên; việc P3 không rung, không nói | CN; PC | Có một phần: giao theo vai trò và ít việc mở nhất (`hub.py:145-161`); chuyển người sau 45 s, tối đa 2 lần (`hub.py:437-462`) | `Hub._assign`, `Hub.tick` | Không | 0 | 1 ngày | Thử được nhưng không ưu tiên |
| D04 | App Android gốc (Kotlin hoặc Flutter): foreground service, WebSocket LAN, FCM high-priority dự phòng, câu thoại Chirp 3 HD tạo sẵn, chuông 0.3–0.5 s trước lời, A2DP; iOS dùng âm thanh thông báo riêng; PWA chỉ dùng cho màn quầy | CN; PC | Chưa có: trang web điện thoại dùng Web Speech (`voice.ts:7, 82-95`), rung (`voice.ts:73-75`), giữ sáng màn hình (`LiveStaffPhone.tsx:216-220`) | App mới; hoặc bản rẻ: phát file âm thanh tạo sẵn trong `voice.ts` | Chirp 3 HD qua Cloud TTS (cần dự án GCP) | 0 | App 3–5 ngày (không vừa sức 2 người); bản rẻ 0.5 ngày | Bản rẻ thử được trên trình duyệt; Chirp cần GCP |
| D05 | Firestore `onSnapshot` thay SSE; đặt hub WebSocket ở máy tại quán; Zalo ZNS hoặc Telegram chỉ làm kênh phụ | PC; CN | Khác thiết kế: SSE `/api/stream` (`app.py:80-104`); Cloud Run 1 instance (`easy-fnb/HUONG_DAN.md:63-64`) | — | — | — | — | Không cần trước demo |
| D06 | Câu cảnh báo giải thích được ("Bàn 7: chậm 2.1× so với thường lệ") | CN | Chưa có | Text trong `Hub` | Không | 0 | 0.5 ngày (cần B15) | Không |

### 1.7 Đo lường

| id | Kỹ thuật | Nguồn | Trạng thái trong code | Chỗ cắm vào | Cần tải | Rủi ro VRAM/tốc độ | Công sức | Thử nhanh? |
|---|---|---|---|---|---|---|---|---|
| M01 | Bộ chấm kiểu SzCORE: dung sai thời gian, gộp sự kiện, báo nhầm theo bàn-giờ có khách (đếm sau Gemini, trước nhân viên), trễ trung vị + p90, phễu theo tầng (luật → head → Gemini → nhân viên), % thời gian trạng thái bàn đúng, % lượt khách đến được bắt trong ±15 s, khoảng tin cậy Poisson chính xác cho báo nhầm/giờ | NK (hạng 2); KX; CN; MH | Có một phần: `cham_su_kien.py` đã có recall + Wilson, trễ trung bình/trung vị/p90, báo trùng, báo nhầm/giờ, quy tắc số 3, chia theo cỡ người (`cham_su_kien.py:32-43, 179-201`); `cham_diem.py` chấm bàn theo mốc (`cham_diem.py:24-63`). Thiếu: phễu, chuẩn hoá theo bàn-giờ, Poisson, sự kiện đến/rời, đếm nhấp nháy | `cham_su_kien.py`, `cham_diem.py` | Không | CPU | 0.5–1 ngày | Có; là điều kiện chung, không cần phép thử khả thi |
| M02 | Bộ dữ liệu tự quay: thêm 3–6 người; ghế gần, xa, mép; ≥150 lần giơ tay, ≥300 cử chỉ gây nhầm, ≥1 giờ ăn bình thường; cảnh bàn (khách để lại đồ, nhân viên dọn, đứng dậy tạm, túi trên ghế); chia theo người và ghế | KX (P0); NK (hạng 2); CN; MH | Có một phần: công cụ đã sẵn (`nhac_lenh.py`, `gan_nhan.py`, `vision-test/quay/KICH_BAN_QUAY.md`); chưa có dữ liệu | `du_lieu_quay/` | Không | — | 1–1.5 ngày | Không phải phép thử; là điều kiện của mọi số đo thật |
| M03 | Chế độ "chỉ ghi log" (shadow) cho mọi thay đổi chưa đạt; luật chốt định trước: chỉ bật khi giảm báo nhầm theo bàn-giờ mà không mất sự kiện thật nào | KX; NK | Chưa có cờ chung | Một tham số mới trong `easyfnb_test.py`: ghi vào `su_kien.json` nhưng không gọi `mc.event` | Không | 0 | 2 giờ | Có |
| M04 | Bảng ablation (luật / + head / + Gemini / + GRU / + máy trạng thái); vùng hoạt động theo chiều cao người | KX; CN; MH | Có một phần (`KET_QUA.md:9-20, 43-66`; `cham_su_kien.py:42-43`) | — | — | — | 0.5 ngày | Có |
| M05 | Đếm ứng viên sai mỗi camera mỗi giờ (biến quyết định chi phí Gemini); đo trễ đầu-cuối từ cử chỉ tới điện thoại | PC; CN; MH | Chưa có trong `Hub.report` (`hub.py:465-496`) | `Hub.report` | Không | 0 | 2 giờ | **Có (T6)** |
| M06 | A/B bộ mã hoá ảnh + McNemar; trộn logit zero-shot với probe (α chỉnh trên 20–50 crop CCTV); prompt ensemble | MH | **Đã có** A/B 10 model + McNemar (`danh_gia/so_clip.py`, `kiem_mcnemar.py`; `KET_QUA.md:41-66`); prompt ensemble đã có (`clip_cls.py:41-47, 91-93`); trộn logit chưa có | `ClipCls.p_pos` (`clip_cls.py:136-143`) | Không | 0 | 2 giờ | Có, nhưng ít giá trị khi chưa có crop CCTV thật |

### 1.8 Tốc độ và runtime

| id | Kỹ thuật | Nguồn | Trạng thái trong code | Chỗ cắm vào | Cần tải | Rủi ro VRAM/tốc độ | Công sức | Thử nhanh? |
|---|---|---|---|---|---|---|---|---|
| R01 | TensorRT FP16 cho YOLO trên GPU; OpenVINO trên CPU | MH; PC | **Đã có** (`models/*_fp16.engine`, `*_openvino_model`; `KET_QUA.md:34-35`) | — | — | — | — | Đã đo |
| R02 | Lọc chuyển động kiểu Frigate; giảm fps cho camera vắng; NVDEC, gộp batch nhiều camera, DeepStream | PC; MH; NK; CN | Chưa có | `run_clip` trước dòng 359 | Không | Giảm tải | 1–2 ngày | Không cần cho demo một camera |
| R03 | INT8 (giữ head keypoint ở FP16); pose 960 → 640; ONNX + CUDA Graphs | MH | Chưa có | `danh_gia/do_toc_do.py xuat` | Không | Có thể mất người nhỏ | 0.5–1 ngày | Sau demo (MH: không làm INT8 trước demo) |
| R04 | Cache theo track: chỉ chạy bộ mã hoá khi có track mới hoặc trạng thái đổi; text embedding tính sẵn | MH | Có một phần: text tính sẵn (`clip_cls.py:91-99`); nhân viên mỗi 6 khung (`easyfnb_test.py:395`); head tay chỉ cho ứng viên (`easyfnb_test.py:387-388`) | `run_clip` dòng 395 | Không | Bớt vài ms mỗi khung | 2 giờ | Có (trong T2) |
| R05 | Đo VRAM thật của pipeline v4: pose + det + 3 bộ mã hoá + RTMPose ORT CUDA | (ràng buộc phần cứng) | Chưa có số nào; chỉ biết PE-Core L/14 tràn bộ nhớ (`KET_QUA.md:69`) | `nvidia-smi` chạy song song | Không | — | 10 phút | **Có (bước 0)** |

### 1.9 Camera, triển khai, demo

| id | Kỹ thuật | Nguồn | Trạng thái trong code | Chỗ cắm vào | Cần tải | Rủi ro VRAM/tốc độ | Công sức | Thử nhanh? |
|---|---|---|---|---|---|---|---|---|
| C01 | go2rtc kéo mỗi luồng một lần rồi phát lại; bảng URL RTSP theo hãng (Hikvision, Dahua/KBVision, EZVIZ, Imou, Tapo, Yoosee, Xiaomi); trình cài đặt ONVIF; luồng phụ H.264 640×360 5–10 fps; tính DORI; chỉ kết nối từ quán đi ra | PC | Chưa có: OpenCV đọc thẳng nguồn (`easyfnb_test.py:303`) | Ngoài pipeline | go2rtc (MIT) | 0 | 1–2 ngày | Không cần cho demo |
| C02 | Luồng đọc riêng chỉ giữ khung mới nhất + watchdog tự nối lại có backoff | PC; CN | Chưa có: đọc hỏng là dừng (`easyfnb_test.py:345-350`); `--lap` chỉ dùng cho file (`easyfnb_test.py:346-348`) | `run_clip` dòng 303-350 | Không | 0 | 2–3 giờ | **Có (T6)** |
| C03 | Điện thoại làm camera (IP Webcam qua RTSP; Larix → MediaMTX), đặt cao 2–2.5 m nghiêng 30–45°, khoá nét và phơi sáng; dùng hotspot điện thoại thay Wi-Fi hội trường | PC; CN | Có một phần: nhận `rtsp://`, `http://`, số webcam (`easyfnb_test.py:602, 655-656`) | — | App điện thoại | — | 1 giờ | Có (T6) |
| C04 | Footage dàn dựng phát lặp làm nguồn dự phòng; video demo dự phòng; nút chế độ mô phỏng | PC; CN | **Đã có**: `--lap`, `--thoi-gian-thuc` (`easyfnb_test.py:335-348, 642-644`); `demo_v4.mp4`; `easy-fnb/src/sim/engine.ts` | — | — | — | — | — |
| C05 | Một container Cloud Run (FastAPI + `dist`) ở asia-southeast1, min-instances 1 hôm demo | PC; CN | **Đã có** (`easy-fnb/Dockerfile`; `easy-fnb/HUONG_DAN.md:63-64`) | — | — | — | — | — |
| C06 | Agent chủ quán bằng ADK với bộ tool có kiểu; video RAG 5 lớp; pgvector hoặc Firestore vector; `gemini-embedding-2`; clip sự kiện lên Cloud Storage; MCP; luật chống bịa (backend tạo mốc giờ và link); báo cáo ca xác định + kiểm số bằng regex | CN; PC | Có một phần: trợ lý dựa trên nhật ký chữ + refs (`gemini.py:120-127`; `app.py:241`), báo cáo số (`hub.py:465-496`), tóm tắt ca (`gemini.py:129-135`) | `app.py`, `gemini.py` | `google-adk` | 0 | 2–4 ngày; riêng kiểm số bằng regex 0.5 giờ | Không cần cho lõi demo |

### 1.10 Riêng tư, pháp lý, khuôn mặt

| id | Kỹ thuật | Nguồn | Trạng thái trong code | Chỗ cắm vào | Cần tải | Rủi ro VRAM/tốc độ | Công sức | Thử nhanh? |
|---|---|---|---|---|---|---|---|---|
| P01 | Làm mờ mặt bằng hình elip quanh keypoint 0–4 trên mọi thứ rời khỏi máy (crop gửi Gemini, khung live, ảnh log); YuNet làm lưới dự phòng cho người quay lưng; không làm mờ cả người; A/B 50–100 crop gốc và mờ | NK (hạng 10); PC | Chưa có: crop và khung live gửi nguyên ảnh (`gui_may_chu.py:150-157, 165-187`) | Hàm mới trong `fnb_common.py`, gọi ở `run_clip` trước `mc.event` (dòng 443, 469) và `mc.frame_live` (dòng 544), chỉ trên bản sao gửi đi | Không (YuNet ONNX vài trăm KB, MIT, tuỳ chọn) | 1–2 ms mỗi khung trên CPU; 0 VRAM | 0.5 ngày + A/B | **Có (T5)**; A/B Gemini chờ key |
| P02 | Biển thông báo camera; slide quyền riêng tư; xin đồng ý; hồ sơ đánh giá tác động theo mẫu 09/10 (Nghị định 356/2025); xoá crop sau khi xác minh | NK; PC; CN | Chưa có (không phải code) | — | — | — | 0.5 ngày | Không |
| P03 | Nhận diện khách quen ở camera cửa: YuNet + SFace → căn 112×112 → lọc chất lượng → template từ 3–5 ảnh → so 1:N chỉ với người đã đồng ý; vùng giữa thì hỏi "Có thể là…?". InsightFace buffalo_l chỉ dùng cho demo; AuraFace và OFIQ để sau; gom cụm kiểu Apple Photos + màn "People" | MH (9–10/11); PC (cắt đầu tiên nếu chỉ 2 người); CN (giờ 36–44, cắt nếu trễ) | Chưa có (`KET_QUA.md:119`) | Module mới + camera thứ hai | YuNet vài trăm KB + SFace ~37 MB (OpenCV Zoo) | CPU vài chục ms mỗi mặt | 1.5–2 ngày | Về kỹ thuật thì thử được, nhưng NK không xếp vào việc trước 14/11 → đề xuất cắt |

### 1.11 Các thứ chính các báo cáo đã loại

| Nhóm | Đã loại | Nguồn |
|---|---|---|
| Model ảnh | YOLO27 (chưa phát hành), YOLO-NAS (phi thương mại), Sapiens, SAM 3, Grounding DINO chạy trong vòng sống, TinyCLIP, MetaCLIP 2 (NC), Tip-Adapter/CLIP-Adapter, DINOv3 lúc này | MH, CN |
| Khung xương | Các SOTA chỉ có checkpoint 3D (ProtoGCN, Hyper-GCN, SkateFormer, nhánh Mamba), HD-GCN, EfficientGCN, CTR-GCN (code CC BY-NC), RGBPoseConv3D, Kinetics skeleton, zero-shot bằng định nghĩa chữ, bộ mã hoá tự giám sát 3D (MAMP, S-JEPA…), SOfA, LoRA cho MDM | KX |
| Cử chỉ/hành động | SiA, OV-STAD, YOLO lớp học trên 40M tham số (CSSA-YOLO); MediaPipe trên cả khung; model hướng nhìn | NK, CN |
| Tracker | CAMELTrack, MOTIP (học đầu-cuối); BoxMOT (AGPL); Metropolis MTMC | NK, CN |
| Gemini | Live API; cho VLM xem liên tục hoặc ghép mosaic; GPU L4 trên Cloud Run cho một quán; thinking dài | MH, PC, CN, NK |
| Runtime | ROCm, DirectML, NPU trên AMD; INT8 trước demo; DeepStream cho dưới 8–16 camera | MH, CN |
| Danh tính | Trọng số mặt phi thương mại trong sản phẩm (LVFace, AdaFace, EdgeFace, SCRFD, YOLO11n-face); dùng Gemini để nhận danh tính; nhận mặt trên camera trần; gom cụm mọi khách | MH, PC, CN |
| Khác | BLE/UWB, Kafka, CP-SAT, Coral, Jetson (đắt hơn); PWA/Web Push làm kênh thoại cho nhân viên (CN, PC — mâu thuẫn với trang web đang dùng, xem mục 2) | CN, PC, NK |

---

## 2. Chỗ các báo cáo vênh nhau

| # | Chỗ vênh | Các bên nói gì | NK chốt | Ghi chú từ code và KET_QUA |
|---|---|---|---|---|
| 1 | Gemini quyết định bằng gì | MH: schema có `confidence`; code rút cảnh báo khi bác với confidence ≥ 0.6 | Bỏ ngưỡng 0.6; quyết định bằng enum + checklist + chất lượng ảnh; `confidence` chỉ để log | Phải sửa `hub.py:319` |
| 2 | Bố cục ảnh gửi Gemini | MH: 3 crop `low` + 1 cảnh `medium`. CN: 4–8 frame tới 768 px. PC: 1 crop `medium`. Code: 1 crop `low` | Dải 2×2 ở `medium` + toàn cảnh `low` có khung đỏ; A/B `medium` và `high` | — |
| 3 | Model dùng để xác minh | PC: `gemini-3.1-flash-lite` (rẻ hơn). MH, CN: `gemini-3.5-flash-lite` | `gemini-3.5-flash-lite` | Code đã theo (`gemini.py:60`) |
| 4 | Khi Gemini trả "không chắc" | Ghi chú sự kiện hiếm: chỉ hiện trên dashboard. Ghi chú xác minh: vẫn đẩy thông báo | Cảnh báo gọi: vẫn thông báo, gắn "Chưa xác minh". "Cần dọn" không chắc: chỉ hiện dashboard | — |
| 5 | Timeout Gemini | MH 3–5 s; NVIDIA 5 s; code 25 s | 2–3 s + circuit breaker | `gemini.py:61` |
| 6 | Giữ tay bao lâu | CN ≥0.8 s trong 70% khung; PC ≥1 s; KX báo 0.3–0.5 s sau đỉnh, không xuống dưới 0.40 s; bệnh viện > 5 s; code 0.6 s | Hai mức: 0.6 s khi rõ, 1.5–2 s khi mơ hồ | — |
| 7 | Làm mượt trạng thái bàn | CN: FSM 10 trạng thái + HSMM, giữ 2–3 lần đo hoặc 5–10 s. Code: bỏ phiếu 1 s, 0.8/0.2 | FSM có phiên + cổng che + EMA 0.7/0.3; mọi thời gian tính bằng giây | Đang phát lại ở nơi khác |
| 8 | Bao lâu thì coi là khách rời | RestoMan-AI 5 s; các ghi chú 10–20 s, 20–60 s, 60–120 s | 30 s (chỉnh 20–60), rồi ≥3 s nhìn thấy được mới gọi Gemini, một lần | Clip 01 là time-lapse nên phải nhân hệ số |
| 9 | Chạy pose cho ai | SCB: pose không dùng được ở phòng quá đông. PC: đừng chạy pose cho mọi người. CN: RTMO-s. MH: yolo26s-pose + RTMPose-t/s cho track nhỏ. KX: RTMPose-m cho track nhỏ | Giữ cả pose lẫn crop, trộn muộn; RTMPose chỉ cho ứng viên, thử bản s | **Số đo của nhóm ngược với NK**: yolo26s-pose tụt bàn, RTMPose-s hoặc RTMPose chỉ cho người khó → 3/7 (`KET_QUA.md:37, 39`). Chỉ còn đáng thử tiêu chí chọn mới với bản m (T2) |
| 10 | Tracker | MH: đổi sang TrackTrack/BoT-SORT là việc hiệu quả. CN: Roboflow `trackers` ByteTrack. NK: đổi tracker, 0.25 ngày, hạng 9 | Hạ tầm quan trọng vì sự kiện bàn đã theo phiên, không theo ID | **Đã đo, kết quả âm** (`KET_QUA.md:36`) → giữ ByteTrack |
| 11 | Khoá sự kiện gọi | CN: 60 s mỗi bàn. KX: khoá 5–10 s theo track + gộp theo bàn. MH: N giây theo bàn. Code: 5 s theo track + server gộp 20 s | Tự đóng khi nhân viên tới; không nêu con số | Đề xuất: khoá theo bàn tới khi nhân viên tới hoặc hết 60 s |
| 12 | Detector | CN: RF-DETR-S ngay, YOLO26 chỉ là dự phòng ở giờ 8. MH: giữ YOLO26 cho demo, RF-DETR/D-FINE để sau. PC: YOLOv9 + OpenVINO trên iGPU | Không bàn detector người; YOLOE chỉ để sau | Giữ YOLO26 TensorRT (đã đo, `KET_QUA.md:34`); lý do đổi là giấy phép, để sau demo |
| 13 | Nhân viên hay khách | CN: HSV thân áo + vùng chỉ nhân viên + ArUco. MH: 97% đã gần trần, đổi backbone không lợi | Gallery theo ca trên PE-Core + điểm hành vi + nhãn dính | KET_QUA: probe PE-Core B/16 kém hơn CLIP (98 so với 101/105) → gallery nên thử trên cả hai bộ mã hoá |
| 14 | GRU giơ tay | KX: việc chính P1 (7–8/11). MH: bước 4 trước 14/11. CN: giờ 24–36 | **Không xếp vào 11 việc trước 14/11**, chỉ dẫn sang báo cáo khung xương | Không có footage → GRU chỉ nên chạy ở chế độ ghi log nếu kịp quay |
| 15 | Khách quen bằng khuôn mặt | MH: làm 9–10/11. CN: buffalo_l cho demo. PC: cắt đầu tiên nếu chỉ 2 người | Không có trong danh sách; tránh nhận mặt (sinh trắc), bán ý "không nhận diện khuôn mặt" | Coi như cắt |
| 16 | Kênh báo cho nhân viên | CN, PC: phải là app Android gốc (trang web không nói được khi tắt màn hình). Code: trang web dùng Web Speech | Không bàn | Chưa chốt. Đề xuất: demo bằng trang web với màn hình luôn sáng (wakeLock), nói rõ hạn chế |
| 17 | Gọi Gemini qua đâu | MH, PC: Vertex / Agent Platform để dùng credit (credit trial không trả cho khoá AI Studio sau 2/3/2026). Code: khoá AI Studio | Không bàn | Chưa chốt, và đang chặn mọi phép đo Gemini |
| 18 | Làm mờ mặt khi Gemini cần đọc hướng nhìn | Ghi chú edge: làm mờ mọi thứ rời máy. Ghi chú xác minh: checklist cần hướng nhìn | Chỉ làm mờ mặt; A/B 50–100 crop trước khi bật | — |
| 19 | Suy luận dài, few-shot, số frame | Flash-Cascade cần CoT; Red Sift: thêm suy luận không giúp. Few-shot tăng/giảm báo nhầm tuỳ bài. 2 frame hay 16 frame | Thinking minimal + checklist; không few-shot (trừ một ảnh đồng phục); 4 frame cho gọi, 1 crop cao + ảnh sạch cho bàn | — |
| 20 | Tham số tính theo khung | KX giả định ~13 fps (giữ 4–6 khung, cửa sổ 16 khung). Thực tế 11–57 fps (`KET_QUA.md:18-19`) | Mọi thời gian tính bằng giây | — |
| 21 | VLM chạy tại chỗ | CN cần GPU 24 GB; MH: Gemma 4 E2B sau demo; NK: Qwen3-VL-2B sau | Đồng thuận: sau hackathon | Không vừa 4 GB |

---

## 3. Danh sách rút gọn để thử trên máy này

**Không lặp lại ba phép thử đang chạy ở nơi khác:**
- phát lại máy trạng thái bàn trên `out_v4/*/chi_tiet.json` (B01–B04, có thể mở rộng sang B06 điểm hông);
- chấm bàn bằng ảnh "bàn sạch" kiểu AnomalyDINO trên `danh_gia/anh_ban_test` (B09; có thể gộp B07 crop có viền);
- YOLOE-26 prompt chữ cho đồ trên bàn (B14).

**Cũng không thử lại** những gì `KET_QUA.md` đã cho kết quả âm: đổi tracker, yolo26s-pose, RTMPose-s, RTMPose chỉ cho người khó theo tiêu chí cũ.

Các phép thử dưới đây không cần tải dataset. Thời gian ghi là thời gian chạy; công viết script ghi riêng. Lệnh viết cho cmd trong `vision-test/`, dùng `venv\Scripts\python` như `KET_QUA.md`.

### Bước 0 (chung, ~10 phút GPU, chạy một lần): đo VRAM và lấy dữ liệu khung xương

Bước này cung cấp dữ liệu cho T1, T3, T5 và cho phần mở rộng điểm hông của phép thử phát lại bàn.

1. Mở một cửa sổ khác:
   ```
   nvidia-smi --query-gpu=timestamp,memory.used,utilization.gpu --format=csv -lms 500 > out_b0_vram.csv
   ```
2. Chạy v4 nhạy và lưu cả chi tiết lẫn khung xương:
   ```
   venv\Scripts\python easyfnb_test.py clips/ --out out_b0 --no-video --dump --luu-khung-xuong ^
     --hand-model giotay_pe_b16.pt --hand-th 0.35 --staff-model nhanvien_clip_v1.pt ^
     --table-model clip --clip-backbone pe_core_s16 ^
     --pose-models yolo26n-pose_544x960_fp16.engine --det-models yolo26s_736x1280_fp16.engine ^
     --pose-refine rtmpose-m --refine-mode tat_ca
   ```
3. Chạy lại một lần không có hai tham số `--pose-refine`/`--refine-mode` (v4 nhanh) để có VRAM của bản nhanh.

**Kết quả cần ghi:**
- VRAM đỉnh của từng bản, suy ra **phần còn trống = 4096 MB − đỉnh**;
- `khung_moi_giay` của từng clip;
- `khung_xuong.npz` của mọi clip.

Nếu phần trống dưới ~500 MB thì gạch mọi ứng viên cần thêm model lên GPU.

### T1. Cổng mềm, đường "chỉ RGB" cho người mép hình, giữ tay hai mức, tích luỹ bằng chứng yếu (G01, G02, G08; ~10 phút)

- **Đầu vào:** clip 10 và 12 (7 lần giơ tay có nhãn, trong đó có ca "em mép trái" 19.5–21.5 s, x 0–140); clip 02, 08, 09 làm âm; `out_b0` cho phần CPU.
- **Phần A (CPU, ~2 phút).** Thêm vào `danh_gia/thu_gio_tay.py` một hàm `simulate2`:
  - Giữ hai mức: "rõ" (`luat > 0` và `ph ≥ 0.6`) giữ 0.6 s; "mơ hồ" giữ 1.5 s.
  - Tích luỹ: trung bình `ph` ≥ 0.25 trong 1 s, với `nang > 0.3`.
  - Chạy `venv\Scripts\python danh_gia/thu_gio_tay.py out_b0 --chi-tiet`.
- **Phần B (GPU, ~5 phút).** Sau khoảng 20 dòng sửa ở `easyfnb_test.py:387-388`, sau cờ mới `--cong-mem`:
  - Đưa thêm vào `sel` người có box chạm mép (x1 < 5 hoặc x2 > W − 5) mà không thấy vai, và người có `hand_lift` là None.
  - Với nhóm này, dùng ngưỡng 0.6 và giữ 1.0 s.
  - Chạy clip 10, 12, 02, 08, 09 với cấu hình v4 nhạy cộng `--dump --cong-mem --out out_t1`, rồi `venv\Scripts\python danh_gia/cham_diem.py out_t1`.
- **Thước đo:** số lần bắt được trên 7; báo nhầm trên các clip âm; trễ trung bình và từng lần; fps.
- **Đạt khi:**
  - Phần A: vẫn ≥ 5/7, 0 báo nhầm, trễ trung bình ≤ 0.70 s (tăng không quá 0.3 s, mốc của NK).
  - Phần B: ≥ 6/7 (bắt được em mép trái), 0 báo nhầm trên 02/08/09, fps giảm không quá 10%.
- **Không đạt khi:** phần B báo nhầm trên clip âm. Khi đó đường "chỉ RGB" chỉ chạy ở chế độ ghi log, và trên demo nói rõ giới hạn "bàn phải nằm trọn trong khung" (KX).
- **Lưu ý:** clip stock không có cử chỉ gây nhầm, nên lợi ích của giữ hai mức chỉ đo được trên footage tự quay.
- **Công viết:** ~2 giờ.

### T2. Lấy lại fps: bàn theo giây, detector hiếm, RTMPose-m chọn lọc (B12, G09, R04; ~15 phút GPU)

1. **Không sửa code (~5 phút).** Chạy v4 nhạy trên clip 09, 10, 12, 01 thêm `--det-every 100 --table-every 20 --staff-every 20 --no-video`. Bọc mỗi lần chạy trong `Measure-Command` (PowerShell) để lấy fps thực = số khung / thời gian, vì `khung_moi_giay` không tính thời gian của model nhỏ. Ghi VRAM như bước 0.
2. **Sửa ~30 dòng trong `refine_pose` (~5 phút chạy).** Thêm chế độ `ung_vien`:
   - chọn người có box < 150 px, hoặc thiếu vai/cổ tay, hoặc `hand_lift > −0.6`;
   - tối đa K = 4 người, ưu tiên `hand_lift` lớn;
   - giữ RTMPose-**m**.
   
   Chạy clip 01, 02, 09, 10, 12 rồi `cham_diem.py`.
- **Thước đo:** fps ở clip 10 (v4 nhạy hiện 13.6 theo `su_kien.json`; 11 fps ở clip đông nhất theo `KET_QUA.md:19`); số lần bắt được trên 7; trễ trung bình; điểm bàn trên 137; VRAM.
- **Đạt khi:** fps clip 10 ≥ 18 (mục tiêu của NK), ≥ 5/7, trễ trung bình ≤ 0.6 s, bàn ≥ 130/137.
- **Không đạt khi:** chế độ mới lại rơi về 3/7 như `gan_vai`. Khi đó giữ v4 nhạy cho demo một camera, v4 nhanh cho nhiều camera, và chỉ áp dụng phần (1).
- **Công viết:** ~1.5 giờ.

### T3. Nhân viên: gallery theo ca, nhãn dính, tự đóng khi nhân viên tới bàn (N01, N03, D01; ~15 phút)

- **Đầu vào:**
  - clip 06 (nhân viên đeo tạp dề ghi món), clip 07 (nhân viên mang máy tính tiền);
  - clip 02 và 09 làm kho khách (chỉ có khách);
  - `out_b0/*/khung_xuong.npz` (box, `pst` từng track);
  - khung ảnh đọc lại từ video bằng cv2.
- **Chuẩn bị (5 phút):**
  - Xem `out_v4/06…/video_ket_qua.mp4` và `out_v4/07…/video_ket_qua.mp4`, ghi mã track của nhân viên vào `nv_that.json`.
  - Vẽ polygon bàn cho clip 06/07 (bằng web `LiveSetup` hoặc thêm vào `zones.json`).
- **Script `danh_gia/thu_gallery_nv.py` (~120 dòng):**
  1. Crop phần giữa box: 60% bề ngang × 70% chiều cao từ trên.
  2. Gallery = crop của track nhân viên trong 2 s đầu track đó xuất hiện; chỉ chấm phần sau 2 s.
  3. Kho khách = crop từ clip 02, 09.
  4. Mã hoá bằng CLIP B/32 **và** PE-Core B/16 (đều đã có trong cache).
  5. Điểm track = trung bình (giống nhất với gallery − giống nhất với kho khách).
  6. Nhãn dính: vào > 0.8, ra < 0.3 (sau khi đổi điểm về 0..1).
  7. So với probe hiện tại (`pst` trung bình 3 s, ngưỡng 0.5).
  8. Sự kiện "nhân viên tới bàn": track nhân viên có điểm hông hoặc điểm neo trong polygon ≥ 2 s.
- **Thước đo:**
  - ma trận nhầm nhân viên/khách theo track trên 06, 07, 02, 09;
  - số lần đổi nhãn mỗi track (gallery + dính so với probe);
  - độ trễ từ lúc nhân viên vào vùng bàn tới sự kiện; số sự kiện sai do khách.
- **Đạt khi:**
  - mọi track nhân viên đúng sau 2 s;
  - 0 khách bị gắn nhân viên;
  - số lần đổi nhãn ≤ probe;
  - "nhân viên tới" phát trong ≤ 2 s và không phát cho khách.
- **Lưu ý:** gallery và tập chấm cùng clip nên kết quả lạc quan, nhưng đúng với cách dùng thật (đăng ký đầu ca).
- **Công viết:** ~2–3 giờ.

### T4. Gói request Gemini, luật quyết định mới, timeout và circuit breaker, không cần key (V01, V02, V03, V05, B10; ~10 phút CPU)

**Phần A: dựng gói.** Script `danh_gia/dung_goi_gemini.py`:
- Đọc 6 sự kiện gọi trong `out_v4/10…`, `out_v4/12…` và 3 sự kiện "cần dọn" trong `out_v4/01…`.
- Đọc khung ở t − 1.5, −1, −0.5, t từ clip; crop box nới 30%; ghép dải 2×2 có in giờ.
- Dựng ảnh toàn cảnh có khung đỏ và số bàn; với bàn, ghép thêm ảnh bàn sạch lấy từ mốc T trong `dap_an.json`.
- Ghi JPEG và thân request JSON, **không gửi**.

**Phần B: luật quyết định và lỗi mạng.** Script gọi `Hub` trực tiếp, với một đối tượng Gemini giả:
- (a) trả các JSON mẫu `GOI_PHUC_VU`, `KHONG_GOI` + ảnh ok, `KHONG_GOI` + ảnh tối, `KHONG_CHAC`;
- (b) treo 30 s;
- (c) báo lỗi 5 lần liên tiếp.

**Thước đo:**
- cỡ ảnh dải (cạnh ≤ ~1024 px), số byte JPEG;
- token ước tính: medium 560 + low 280 + ~700 token chữ, cộng ≤ 60 token trả về;
- bằng mắt: tay giơ thấy trong ≥ 3/4 ô với 5 sự kiện bắt đúng;
- trạng thái việc sau mỗi phản hồi giả; thời gian tới khi việc ở trạng thái "Chưa xác minh" khi Gemini treo; breaker mở và đóng lại.

**Đạt khi:**
- cả 6 dải đúng người ở giữa;
- request ≤ ~1,600 token vào (≈ 16 đồng/lần theo NK);
- chỉ trường hợp `KHONG_GOI` + ok + checklist khớp mới huỷ việc;
- khi Gemini treo, việc vẫn tới nhân viên ngay và chuyển "Chưa xác minh" trong ≤ 3 s;
- sau 3 lỗi liên tiếp thì ngừng gọi trong 60 s rồi thử lại.

**Phần chờ key (V10):** chạy cùng các gói này trên 60–100 sự kiện có nhãn, so crop đơn / crop + ngữ cảnh / dải + ngữ cảnh.

**Công viết:** ~3 giờ (phần lớn là code thật của V01/V02/V05).

### T5. Làm mờ mặt từ keypoint 0–4 trên ảnh rời máy (P01; ~5 phút CPU)

- **Đầu vào:** `out_b0/{06,07,10,12}/khung_xuong.npz` + khung video.
- **Script ~60 dòng:**
  - Với 50 crop người ngẫu nhiên và 6 crop sự kiện: elip làm mờ tâm ở trung bình các keypoint 0–4 có độ tin cậy > 0.3.
  - Trục elip theo khoảng cách hai tai; dự phòng 0.18 × chiều cao box.
  - Không thấy điểm đầu nào thì làm mờ 20% trên của box (YuNet chỉ là phương án sau nếu tỉ lệ này cao).
  - Ghép lưới trước/sau để xem bằng mắt; đo ms mỗi khung.
- **Thước đo:** % mặt bị che kín; % tay giơ bị mờ theo (phải gần 0, vì Gemini cần thấy tay); ms mỗi khung với ≤ 10 người.
- **Đạt khi:** ≥ 90% mặt kín, ≤ 5% tay giơ bị mờ, ≤ 2 ms mỗi khung.
- **Phần chờ key:** A/B Gemini trên crop gốc và crop mờ.
- **Công viết:** ~1 giờ.

### T6. Nguồn điện thoại thật: watchdog nối lại và trễ đầu-cuối (C02, C03, M05; ~15 phút, GPU nhẹ)

- **Đầu vào:** điện thoại Android chạy IP Webcam (`rtsp://<ip>:8080/h264_ulaw.sdp`), nối qua hotspot; server chạy cục bộ (`python -m server`); trang điện thoại nhân viên mở trên một máy khác.
- **Sửa ~40 dòng ở `easyfnb_test.py:303-350`:** luồng đọc riêng chỉ giữ khung mới nhất; khi đọc lỗi thì thử nối lại với backoff 1, 2, 4 s thay vì `break`.
- **Kịch bản:**
  - Chạy `easyfnb_test.py rtsp://… --may-chu http://localhost:8080 …`.
  - Tắt app camera 10 s rồi bật lại; lặp 3 lần.
  - Giơ tay 10 lần trước camera, mỗi lần bấm giờ bằng đồng hồ trên màn hình điện thoại thứ hai đặt trong khung hình (ghi lúc tay lên đỉnh và lúc điện thoại nhân viên kêu).
- **Thước đo:** pipeline có tự nối lại không (3/3); thời gian từ lúc camera sống lại tới khi có khung mới; trễ từ tay lên đỉnh tới khi điện thoại kêu (trung vị, p90); fps và VRAM.
- **Đạt khi:** 3/3 tự nối lại trong ≤ 10 s mà không khởi động lại script; trễ trung vị ≤ 1.5 s khi không có Gemini (mốc của CN và PC).
- **Lưu ý:** đây cũng là buổi tập demo thật đầu tiên.
- **Công viết:** ~2 giờ.

### Không thử nhanh được trên máy này

| Ứng viên | Lý do | Điều kiện để thử |
|---|---|---|
| G05/G06/G07 (GRU, ST-GCN++, trộn muộn) | Chỉ có 7 lần giơ tay có nhãn; NTU và BK-SAD cần người dùng duyệt tải | Footage tự quay theo `KICH_BAN_QUAY.md` (M02) |
| V04, V09, V10, V13 (độ chính xác và chi phí Gemini) | Chưa có key | Key hoặc Vertex (V12); gói request từ T4 dùng lại ngay |
| V14 (VLM tại chỗ) | Không vừa 4 GB cùng pipeline | Sau demo |
| D04 (app Android, Chirp 3 HD) | Quá sức 2 người trước 14/11; Chirp cần GCP | Sau demo |
| P03 (khách quen bằng mặt) | NK không xếp vào việc trước 14/11; rủi ro pháp lý | Sau demo, với người đã đồng ý |
| T01, G09 bản s, G10 | Đã có kết quả âm (`KET_QUA.md:36-39`) | Chỉ đo lại nếu N03 thất bại (T01) |

**Luật chốt dùng chung** (theo NK và KX): một thay đổi chỉ được bật trong demo khi bộ chấm cho thấy nó không làm mất sự kiện thật nào và không tăng báo nhầm. Nếu không đạt, thay đổi chạy ở chế độ chỉ ghi log và được trình bày là "phần đang học". Phép thử trên clip stock chỉ là cổng khả thi. Bằng chứng thật là footage tự quay và bộ chấm M01.
