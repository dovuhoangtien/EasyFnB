# T4: Gói request Gemini, luật quyết định mới, timeout và circuit breaker

Ngày chạy: 5/11/2026. Chạy trên CPU, không gọi Gemini (chưa có key). Không sửa file nào trong `easy-fnb/server/`.

## Kết luận ngắn

Thiết kế xác minh mới chạy được về mặt cơ học. Phần chưa biết là độ chính xác của Gemini, vì việc đó cần key.

| Tiêu chí đạt (theo `tong_hop_ung_vien.md`, T4) | Kết quả |
|---|---|
| Request ≤ ~1,600 token vào | **Đạt.** Gọi phục vụ 1,166; cần dọn có ảnh bàn sạch 1,410; cần dọn không có ảnh bàn sạch 1,114 (cách tính: số ký tự / 4). Nếu tiếng Việt tốn 3 ký tự/token thì lần lượt là 1,275 / 1,506 / 1,206 |
| Cạnh dải ảnh ≤ ~1,024 px | **Đạt.** Dải 576×768 (người) hoặc 768×576 (bàn), JPEG 53–92 KB |
| Cả 6 dải có đúng người ở giữa | **5/6.** Sự kiện 06 (clip 12, người ở mép trái) không đặt được người vào giữa: người đó bị khung hình cắt, và người nổi nhất trong ô là anh áo đen ngồi trước |
| Tay giơ thấy trong ≥ 3/4 ô (5 sự kiện bắt đúng) | **Không đạt với cửa sổ t−1.5…t (0/5). Đạt 4/5 khi dời cửa sổ sang t−0.5…t+1.0.** Xem mục 3 |
| Chỉ `KHONG_GOI` + ảnh ok + checklist khớp mới huỷ việc | **Đạt.** Đã duyệt hết 3 × 5 × 2 × 2 × 2 × 10 = 1,200 tổ hợp đầu ra |
| Gemini treo: việc tới nhân viên ngay, chuyển "Chưa xác minh" trong ≤ 3 s | **Đạt.** Việc tới nhân viên sau ~3 ms; "Chưa xác minh" sau 2.51–2.54 s (timeout 2.5 s) |
| Sau 3 lỗi liên tiếp thì ngừng gọi 60 s rồi thử lại | **Đạt.** Lần 4 và 5 không gọi Gemini. Sau 59 s vẫn chưa gọi; tới 60 s thì cho một lần gọi thử. Thử được thì đóng breaker, thử hỏng thì mở lại thêm 60 s |
| Phép thử | **23/23 qua** trên bản thử. Áp diff đề xuất vào **bản sao** của server rồi chạy lại 22 phép thử: **22/22 qua** |

## 1. Đã dựng gì

Mọi file nằm trong `vision-test/thu_nghiem/gemini_goi_kiem_tra/`:

| File | Nội dung |
|---|---|
| `xac_minh_v2.py` | Bản thử của thiết kế mới: prompt, schema enum, dựng thân request với mức phân giải riêng cho từng ảnh, ước tính token và tiền, luật `decide()`, `CircuitBreaker`, `GeminiV2` (kế thừa `server.gemini.Gemini`) và `HubV2` (kế thừa `server.hub.Hub`, import thẳng `hub.py` thật) |
| `dung_goi.py` | Dựng 9 gói request từ sự kiện v4: 6 lần gọi (clip 10, 12) và 3 lần cần dọn (clip 01). Ghi JPEG và JSON, **không gửi** |
| `goi_mau/` | 9 thư mục gói và `tong_hop.json` (khung đã dùng, vùng cắt, số byte, token) |
| `kiem_thu.py` | 23 phép thử (unittest, ~10 s): luật quyết định, breaker, Hub thật với Gemini giả, client thật với mạng giả (`httpx.MockTransport`), kiểm gói đã dựng |
| `kiem_ban_va.py` | Chạy lại các phép thử đó trên một bản sao server đã áp diff |
| `de_xuat_server.patch` | Diff đề xuất cho `server/gemini.py`, `server/hub.py`, `server/app.py`. **Chưa áp.** `git apply --check` qua |
| `ket_qua_kiem_thu.txt`, `ket_qua_kiem_ban_va.txt` | Log lần chạy |

Chạy lại:

```
python dung_goi.py          # dựng lại goi_mau/ (~10 s CPU)
python kiem_thu.py          # 23 phép thử
# thử diff trên bản sao: chép easy-fnb/server sang thư mục X/server, áp patch vào đó, rồi
python kiem_ban_va.py X
```

## 2. Gói request

Mỗi gói gồm các phần sau:

- **Ảnh 1, dải 2×2** (`dai_2x2.jpg`), mức `MEDIUM` (560 token): 4 khung ở t−1.5, t−1, t−0.5 và t, có in giờ trên từng ô. Box của sự kiện được nới 30% (15% mỗi bên), rồi chỉ nới thêm cạnh ngắn cho đủ tỉ lệ ô: 3:4 cho người, 4:3 cho bàn. Ban đầu tôi cắt vuông, nhưng crop vuông quanh người ngồi kéo cả người bên cạnh, cũng đang giơ tay, vào giữa ô (sự kiện 03). Vì vậy đã bỏ cách cắt vuông.
- **Ảnh 2, toàn cảnh** (`toan_canh.jpg`), mức `LOW` (280 token): cả khung thu về 768×432, khung đỏ quanh người hoặc vùng bàn, kèm nhãn "nguoi can xet" hoặc "Ban B1".
- **Ảnh 3, bàn sạch** (`ban_sach.jpg`, chỉ có ở gói cần dọn), mức `LOW`: cùng vùng cắt, lấy ở mốc `T` (trống) trong `dap_an.json`.
- `request.json` là thân `generateContent` đầy đủ (base64, 126–197 KB). `request_xem.json` là cùng nội dung nhưng thay base64 bằng cỡ ảnh, để đọc.
- `xem_nhanh.jpg` ghép các ảnh lại cho người xem; file này không gửi đi.

Gói gọi phục vụ còn có biến thể `*_quanh` (khung t−0.5, t, t+0.5, t+1.0), giải thích ở mục 3.

| Gói | Biến thể | Khung (giây trong clip) | Dải (px) | Dải KB | Toàn cảnh KB | Bàn sạch KB | Request KB | Token (÷4) | Token (÷3) |
|---|---|---|---|---|---|---|---|---|---|
| `01_10_16.48s_goi` | truoc | 14.98, 15.48, 15.98, 16.48 | 576×768 | 57 | 53 | — | 148 | 1,166 | 1,275 |
| `01_10_16.48s_goi` | quanh | 15.98, 16.48, 16.98, 17.48 | 576×768 | 59 | 53 | — | 151 | 1,166 | 1,275 |
| `02_10_17.32s_goi` | truoc | 15.82, 16.32, 16.82, 17.32 | 576×768 | 87 | 54 | — | 190 | 1,166 | 1,275 |
| `02_10_17.32s_goi` | quanh | 16.82, 17.32, 17.82, 18.32 | 576×768 | 88 | 54 | — | 191 | 1,166 | 1,275 |
| `03_10_17.98s_goi` | truoc | 16.48, 16.98, 17.48, 17.98 | 576×768 | 92 | 54 | — | 196 | 1,166 | 1,275 |
| `03_10_17.98s_goi` | quanh | 17.48, 17.98, 18.48, 18.98 | 576×768 | 92 | 54 | — | 197 | 1,166 | 1,275 |
| `04_10_20.65s_goi` | truoc | 19.15, 19.65, 20.15, 20.65 | 576×768 | 87 | 55 | — | 191 | 1,166 | 1,275 |
| `04_10_20.65s_goi` | quanh | 20.15, 20.65, 21.15, 21.44 | 576×768 | 87 | 55 | — | 191 | 1,166 | 1,275 |
| `05_12_02.56s_goi` | truoc | 1.06, 1.56, 2.06, 2.56 | 576×768 | 90 | 50 | — | 189 | 1,166 | 1,275 |
| `05_12_02.56s_goi` | quanh | 2.06, 2.56, 3.06, 3.56 | 576×768 | 88 | 50 | — | 186 | 1,166 | 1,275 |
| `06_12_02.72s_goi` | truoc | 1.22, 1.72, 2.22, 2.72 | 576×768 | 80 | 49 | — | 174 | 1,166 | 1,275 |
| `06_12_02.72s_goi` | quanh | 2.22, 2.72, 3.22, 3.72 | 576×768 | 81 | 49 | — | 174 | 1,166 | 1,275 |
| `07_01_00.46s_can_don_B1` | truoc | 0, 0.15, 0.31, 0.46 | 768×576 | 57 | 42 | 17 | 157 | 1,410 | 1,506 |
| `08_01_00.46s_can_don_B4` | truoc | 0, 0.15, 0.31, 0.46 | 768×576 | 57 | 43 | 14 | 153 | 1,410 | 1,506 |
| `09_01_03.04s_can_don_B3` | truoc | 1.54, 2.04, 2.54, 3.04 | 768×576 | 53 | 40 | — | 126 | 1,114 | 1,206 |

Ví dụ để xem bằng mắt:

- Gọi phục vụ: `goi_mau/01_10_16.48s_goi/xem_nhanh.jpg` và `xem_nhanh_quanh.jpg`; `goi_mau/05_12_02.56s_goi/xem_nhanh.jpg`
- Người ở mép hình: `goi_mau/06_12_02.72s_goi/xem_nhanh.jpg`
- Cần dọn có ảnh bàn sạch: `goi_mau/07_01_00.46s_can_don_B1/xem_nhanh.jpg`
- Cần dọn không có ảnh bàn sạch: `goi_mau/09_01_03.04s_can_don_B3/xem_nhanh.jpg`

Đoạn đầu của `request_xem.json` (gói 07):

```json
{"contents": [{"role": "user", "parts": [
  {"text": "Kiểm tra cảnh báo \"bàn cần dọn\" từ camera quán ăn. Ảnh 1: 4 khung trong 1,5 giây cắt quanh bàn B1. ..."},
  {"inline_data": {"mime_type": "image/jpeg", "data": "<JPEG 58061 byte, base64>"}, "mediaResolution": {"level": "MEDIA_RESOLUTION_MEDIUM"}},
  {"inline_data": {"mime_type": "image/jpeg", "data": "<JPEG 43024 byte, base64>"}, "mediaResolution": {"level": "MEDIA_RESOLUTION_LOW"}},
  {"inline_data": {"mime_type": "image/jpeg", "data": "<JPEG 17823 byte, base64>"}, "mediaResolution": {"level": "MEDIA_RESOLUTION_LOW"}}]}],
 "generationConfig": {"responseMimeType": "application/json", "responseJsonSchema": {...},
                      "thinkingConfig": {"thinkingLevel": "MINIMAL"}}}
```

### Prompt và schema

Prompt gọi phục vụ có 640 ký tự, gồm danh sách loại trừ bằng tiếng Việt:

> Kiểm tra cảnh báo từ camera quán ăn. Ảnh 1: 4 khung trong 1,5 giây (trái sang phải, trên xuống dưới), cắt quanh MỘT người. Ảnh 2: toàn cảnh, khung đỏ là người đó. Chỉ xét người trong khung đỏ.
> GOI: giơ tay ngang hoặc trên đầu, hướng ra quán để gọi nhân viên, giữ hoặc vẫy qua ít nhất 2 khung.
> KHONG_GOI nếu là: vươn vai, vuốt hoặc chỉnh tóc, gãi đầu, chỉnh kính hoặc mũ, uống hoặc ăn, nâng ly chúc, nghe hoặc chụp điện thoại, chỉ tay khi nói chuyện, chống cằm, vẫy chào bạn cùng bàn, nhân viên (đồng phục, bưng khay).
> KHONG_CHAC: ảnh không đủ rõ để kết luận. Không đoán.
> Điền checklist trước, rồi verdict. reason: tiếng Việt, tối đa 12 chữ.

Prompt cần dọn có cùng khung. Nó liệt kê đồ của quán không được tính (lọ gia vị, hộp giấy ăn, ống đũa, menu, ly úp sẵn) và định nghĩa `personal_belongings_present` (túi, điện thoại, áo khoác, ví). Khi có ảnh bàn sạch, prompt thêm câu "Ảnh 3: cùng bàn lúc sạch; chỉ tính đồ KHÔNG có trong ảnh 3".

Schema (`responseJsonSchema`) đặt checklist **trước** verdict, để mô hình điền bằng chứng rồi mới kết luận. Schema không có trường `confidence`.

```
call:           checklist{hand_above_head, held_or_waved_across_frames, wearing_staff_uniform},
                alt ∈ {vuon_vai, chinh_toc, uong_an, nang_ly, dien_thoai, chi_tay, vay_ban, nhan_vien, khac, none},
                image_quality ∈ {ok, toi, mo, bi_che, qua_nho}, verdict ∈ {GOI, KHONG_GOI, KHONG_CHAC}, reason
needs_clearing: checklist{used_items_left, people_at_table, differs_from_clean_ref},
                personal_belongings_present, image_quality, verdict ∈ {CAN_DON, SACH, KHONG_CHAC}, reason
```

Một câu trả lời mẫu dài 217 ký tự, tức khoảng 55 token ra.

## 3. Điều thấy được khi xem gói bằng mắt

**Cửa sổ t−1.5…t chủ yếu chụp lúc tay còn chưa giơ.** Pipeline chỉ báo khi tay đã giữ được 0.6 s (`--hand-s 0.6`), nên ở t−1.5 và t−1 tay thường còn ở dưới. Số ô có tay của người cần xét đang giơ:

| Sự kiện | Ai (`dap_an.json`) | t−1.5…t | t−0.5…t+1.0 |
|---|---|---|---|
| 01 clip 10, 16.48 s | em áo xanh đậm cạnh bảng | 1/4 | 3/4 |
| 02 clip 10, 17.32 s | em áo xanh dương phía trước | 2/4 | 3/4 (ô đầu đang giơ dở) |
| 03 clip 10, 17.98 s | em áo xám giữa lớp | 2/4 | 4/4 |
| 04 clip 10, 20.65 s | em áo xanh dương (lần báo thứ hai, sau khi đổi ID) | 4/4 | 4/4 |
| 05 clip 12, 2.56 s | cô tóc vàng, giơ nhanh | 2/4 | 2/4 (hạ tay sau 2.75 s) |
| 06 clip 12, 2.72 s | người mép trái (bị cắt) | 2/4 | 3/4, nhưng người không ở giữa |

Năm sự kiện bắt đúng là 01, 02, 03, 05 và 06; sự kiện 04 là báo lặp. Trong năm sự kiện này, cửa sổ cũ có 0/5 sự kiện đạt ≥ 3/4 ô, còn cửa sổ mới có 4/5. Đề xuất: **edge chờ 1 s sau sự kiện rồi mới gửi gói xác minh**, với khung t−0.5, t, t+0.5, t+1.0. Cảnh báo gọi vẫn được đẩy ngay ("báo trước, xác minh sau"), nên nhân viên không phải đợi thêm. Chỉ việc rút cảnh báo nhầm chậm thêm 1 s. Prompt không phải sửa, vì cả hai cửa sổ đều dài 1.5 s.

Những điều khác:

- **Sự kiện 04 trùng với 02**: cùng một em, nhưng track bị đổi ID (7 thành 38). `Hub._dedup` sẽ gộp hai lần này: tâm box cùng ô 150 px và cách nhau 3.3 s, dưới mức 20 s. Vì vậy thực tế chỉ có 5 lần gọi Gemini.
- **Người ở mép hình (06)**: box của pose gồm cả anh áo đen ngồi trước lẫn cánh tay áo be của người ở mép. Gemini có thể xét nhầm người. Lớp bảo vệ trong thiết kế là: nếu Gemini trả `KHONG_GOI` mà checklist vẫn nói tay giơ, kết quả thành "Chưa xác minh" chứ không huỷ việc. Đây là đúng loại ca khó mà G01 ("cổng mềm" cho người ở mép) nhắm tới.
- **Clip 01 là time-lapse**: 1.5 s trong clip là nhiều phút ngoài đời, và ở t = 0.46 s chưa đủ 1.5 s lịch sử, nên 4 khung được rải đều trong 0…0.46 s. Với bàn ở quán thật, dải nên trải dài hơn (ví dụ 4 khung trong 30–60 s gần nhất), vì bàn đổi trạng thái theo phút.
- **Ảnh bàn sạch**: B1 và B4 lấy ở 1.25 s, tức **sau** sự kiện. Ảnh này chỉ đứng thay cho ảnh mà quản lý chụp sẵn bằng nút "chụp bàn sạch" (B10). B3 không có lúc nào được gán `T` trong `dap_an.json`, nên gói 09 không có ảnh 3. Luồng vẫn chạy được: prompt bỏ câu về ảnh 3, và request rẻ hơn 296 token.
- Ở B1 và B4, thứ khiến bàn bị coi là "cần dọn" là các tờ lót giấy trắng. Nhìn ảnh, không rõ đó là giấy lót bày sẵn hay đồ đã dùng. Ảnh bàn sạch (bàn trơn) giúp Gemini so sánh, nhưng chưa có key để biết nó trả lời gì.

## 4. Token và chi phí mỗi lần gọi

Giá gemini-3.5-flash-lite: $0.30 cho mỗi 1M token vào, $2.50 cho mỗi 1M token ra, 26,000 đồng/USD. Token ảnh tính theo tài liệu Gemini 3: low 280, medium 560, high 1120. Token chữ tính bằng (ký tự prompt + ký tự schema) / 4. Token ra lấy 60 (một câu trả lời mẫu dài khoảng 55 token).

| Loại request | Token ảnh | Token chữ | Tổng vào | Ra | USD/lần | **Đồng/lần** | Nếu 3 ký tự/token |
|---|---|---|---|---|---|---|---|
| Hiện tại: 1 crop LOW, schema boolean + confidence | 280 | 154 | 434 | ~40 | 0.00023 | **~6.0** | — |
| Gọi phục vụ: dải MEDIUM + toàn cảnh LOW | 840 | 326 | **1,166** | 60 | 0.00050 | **13.0** | 1,275 tok, 13.8 đ |
| Cần dọn: dải + toàn cảnh + bàn sạch LOW | 1,120 | 290 | **1,410** | 60 | 0.00057 | **14.9** | 1,506 tok, 15.6 đ |
| Cần dọn, chưa có ảnh bàn sạch | 840 | 274 | **1,114** | 60 | 0.00048 | **12.6** | 1,206 tok, 13.3 đ |
| (Để so) gọi phục vụ với dải HIGH | 1,400 | 326 | 1,726 | 60 | 0.00067 | 17.4 | vượt mức 1,600 |

Phần tiền token ra chiếm 0.00015 USD, khoảng 30% mỗi lần gọi, dù chỉ có 60 token. Vì vậy `reason` phải ngắn. Nếu `thinkingLevel: MINIMAL` vẫn sinh vài token suy nghĩ, phần đó cũng tính giá token ra. Ví dụ: 300 lần xác minh mỗi ngày ở mức ~14 đồng/lần là khoảng 4,200 đồng/ngày cho một quán.

## 5. Luật quyết định (đã kiểm)

| Đầu ra Gemini | Gọi phục vụ (báo ngay, xác minh sau) | Cần dọn (giữ tới khi xác minh) |
|---|---|---|
| `GOI` / `CAN_DON` + ok + checklist khớp, không đồ cá nhân | Xác nhận, cảnh báo giữ nguyên | Mở việc, giao người |
| `KHONG_GOI` / `SACH` + ok + checklist khớp | **Huỷ việc** (Gemini bác) | Huỷ việc |
| `KHONG_GOI` nhưng checklist nói tay giơ, giữ qua các khung, không đồng phục, `alt` = none hoặc khac | "Chưa xác minh", giữ cảnh báo | — |
| `CAN_DON` + có đồ cá nhân | — | "Chưa xác minh" (có thể khách ra ngoài tạm), vẫn giao việc |
| Ảnh `toi`, `mo`, `bi_che`, `qua_nho` | "Chưa xác minh" | "Chưa xác minh", giao việc |
| `KHONG_CHAC`, hoặc JSON thiếu hay lạ | "Chưa xác minh" | "Chưa xác minh", giao việc |
| Quá 2.5 s, lỗi HTTP, lỗi JSON | "Chưa xác minh", breaker đếm một lỗi | "Chưa xác minh", giao việc, breaker đếm một lỗi |
| Breaker đang mở | "Chưa xác minh", không gọi Gemini | như bên trái, giao việc |

Bỏ ngưỡng `confidence ≥ 0.6` và bỏ luôn trường `confidence`. Với "cần dọn", "Chưa xác minh" vẫn mở việc, giống cách server đang xử lý khi Gemini lỗi. Phần "chỉ hiện trên dashboard, không đẩy thông báo" (V06) thuộc về giao diện, chưa làm ở đây. Mỗi cảnh báo ghi đường đi của nó vào `verify.path`, một trong: `confirmed`, `rejected`, `uncertain`, `poor_image`, `inconsistent`, `belongings`, `timeout`, `error`, `breaker_open`. `Hub.report()` có thêm số `unverified`.

## 6. Kết quả phép thử

`python kiem_thu.py`: **23 phép thử, tất cả qua** (9.98 s). Danh sách:

- `TestDecide` (3): bảng ca gọi phục vụ (12 ca), duyệt hết 1,200 tổ hợp đầu ra, bảng ca cần dọn (9 ca).
- `TestBreaker` (2): mở sau 3 lỗi; vẫn chặn ở 59.9 s; tới 60 s cho đúng một lần thử; thử hỏng thì mở lại, thử được thì đóng; một lần thành công thì đếm lỗi lại từ đầu.
- `TestHubVerdicts` (10), chạy trên `Hub` thật với Gemini giả. `GOI` thì xác nhận, và việc đã tới nhân viên trước khi có kết quả xác minh. `KHONG_GOI` + ok + `chinh_toc` thì huỷ. `KHONG_GOI` + ảnh tối, `KHONG_GOI` không khớp checklist, và `KHONG_CHAC` đều giữ cảnh báo ở "Chưa xác minh", có dòng nhật ký. Cần dọn: `CAN_DON` thì từ `verifying` sang mở việc và giao người; `SACH` thì huỷ; có đồ cá nhân thì "Chưa xác minh". Ba ảnh tới Gemini đúng vai trò. Edge cũ chỉ gửi một crop vẫn chạy.
- `TestHubResilience` (4). Gemini treo 30 s: việc gọi tới nhân viên sau 3.7 ms và thành "Chưa xác minh" sau **2.52 s**. Việc cần dọn mở sau **2.53 s**. Năm lỗi liên tiếp: chỉ 3 lần gọi Gemini, lần 4 và 5 là `breaker_open`; ở +59 s vẫn không gọi; ở +60 s gọi thử, thành công, breaker đóng. Quá hạn cũng được đếm là lỗi, và lần thử hỏng thì breaker mở lại.
- `TestClient` (3), dùng client HTTP thật với mạng giả. Thân request có mức `MEDIUM`/`LOW` trên từng ảnh và schema enum. Nếu API trả 400 vì `mediaResolution` theo từng ảnh, client tự gửi lại với một mức chung `MEDIUM`. Khi client thật bị treo, Hub vẫn chuyển "Chưa xác minh" trong ≤ 3 s.
- `TestPackages` (1): 9 gói chính và 6 biến thể đều ≤ 1,600 token, dải ≤ 1,024 px, mức phân giải đúng.

`python kiem_ban_va.py <bản sao đã vá>`: **22/22 qua** (9.92 s). Đây là cùng các phép thử trên, trừ phép thử gói ảnh, nhưng chạy trên `server/gemini.py` và `server/hub.py` sau khi áp diff ở mục 8. Như vậy diff đề xuất đã được kiểm đúng như bản thử.

## 7. Những gì chưa chắc

- **Cách đặt mức phân giải theo từng ảnh trong `generateContent`.** Tôi dùng `"mediaResolution": {"level": "MEDIA_RESOLUTION_MEDIUM"}` đặt cạnh `inline_data`. Trang tài liệu hiện tại (aistudio.google.com/docs/media-resolution) chỉ có ví dụ cho Interactions API: `"resolution": "medium"` trên từng ảnh. Tham chiếu API (mục Part) thì cho thấy `mediaResolution.level` nằm trong `partMetadata`. Tôi chưa kiểm được dạng nào `generateContent` chấp nhận. Client đã có đường lui: gặp lỗi 400 nhắc tới "resolution" thì bỏ mức theo từng ảnh và đặt `generationConfig.mediaResolution = MEDIUM`. Khi đó cả hai ảnh tính 560 token, gói gọi phục vụ lên khoảng 1,446 token, vẫn dưới 1,600. Lần gọi đầu tiên khi có key sẽ cho biết dạng nào đúng; nên chạy `python -m server.gemini goi_mau/.../dai_2x2.jpg call` và đọc `usage_metadata` (V13).
- Số token ảnh 280/560/1120 lấy theo tài liệu Gemini 3; trang này không liệt kê riêng 3.5 Flash-Lite. Còn cách tính "ký tự / 4" có thể thấp với tiếng Việt có dấu, nên bảng có thêm cột 3 ký tự/token.
- Chưa đặt `temperature`. V04 đề xuất đặt 0. Tôi không nhớ chắc tài liệu Gemini 3 có khuyên giữ mặc định hay không, nên chưa đổi; việc này để A/B khi có key.
- Độ chính xác của Gemini với dải 2×2, ảnh toàn cảnh và ảnh bàn sạch chưa đo (V10). Các gói trong `goi_mau/` có thể dùng ngay khi có key.
- Ảnh bàn sạch trong phép thử lấy từ thời điểm sau sự kiện. Ngoài đời, ảnh này phải được chụp trước (B10).

## 8. Diff đề xuất (chưa áp)

Nội dung giống file `de_xuat_server.patch`. Kiểm bằng `git apply --check`: qua. Cách áp: `git apply vision-test/thu_nghiem/gemini_goi_kiem_tra/de_xuat_server.patch`, chạy từ thư mục gốc.

Điểm chính:

- `gemini.py`: prompt và schema enum mới; `verify(kind, images, table)` nhận nhiều ảnh, mỗi ảnh một mức phân giải, và vẫn nhận `bytes` như cũ; khi API không nhận mức theo từng ảnh thì lùi về một mức chung `MEDIUM`; thêm hàm thuần `decide()`.
- `hub.py`: `CircuitBreaker` (3 lỗi, 60 s), `VERIFY_TIMEOUT_S = 2.5` bọc bằng `asyncio.wait_for`, `self.media` giữ ảnh cho Gemini, `_unverified()`, `_verify()` viết lại theo `decide()`, thêm `report().unverified`, nhật ký có "chưa xác minh".
- `app.py` (3 dòng): giải mã `images: [{role, jpeg_b64}]` từ edge. Edge cũ chỉ gửi `crop_jpeg_b64` vẫn chạy.

```diff
--- a/easy-fnb/server/gemini.py
+++ b/easy-fnb/server/gemini.py
@@ -18,30 +18,61 @@
 
 URL = 'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'
 
+# Mỗi request xác minh gồm nhiều ảnh, mỗi ảnh một vai trò và một mức phân giải riêng:
+#   strip     dải 2x2 bốn khung quanh sự kiện (crop người hoặc bàn)   MEDIUM (~560 token)
+#   overview  toàn cảnh thu nhỏ, khung đỏ quanh người/bàn cần xét       LOW    (~280 token)
+#   clean_ref (chỉ "cần dọn") cùng bàn lúc sạch                         LOW    (~280 token)
+ROLE_RES = {'strip': 'MEDIUM', 'overview': 'LOW', 'clean_ref': 'LOW'}
+LOAI_TRU_GOI = ('vươn vai, vuốt hoặc chỉnh tóc, gãi đầu, chỉnh kính hoặc mũ, uống hoặc ăn, nâng ly chúc, '
+                'nghe hoặc chụp điện thoại, chỉ tay khi nói chuyện, chống cằm, vẫy chào bạn cùng bàn, '
+                'nhân viên (đồng phục, bưng khay)')
+DO_CUA_QUAN = 'lọ gia vị, hộp giấy ăn, ống đũa, menu, ly úp sẵn'
 VERIFY_PROMPT = {
     'call': (
-        'Ảnh cắt từ camera trong một quán ăn, người cần xét ở giữa ảnh. '
-        'Người này có đang GIƠ TAY ĐỂ GỌI NHÂN VIÊN PHỤC VỤ không? '
-        'Gọi phục vụ: tay đưa cao ngang hoặc trên đầu, hướng ra phía quán, giữ yên hoặc vẫy. '
-        'KHÔNG phải gọi: vuốt tóc, gãi đầu, chỉnh kính hoặc mũ, uống nước, ăn, nghe điện thoại, '
-        'chỉ tay, vươn vai, chống cằm, vẫy chào bạn, nhân viên đang bưng đồ. '
-        'Nếu không chắc, trả lời calling=false với confidence thấp. '
-        'Lý do: tiếng Việt, tối đa 12 chữ.'
+        'Kiểm tra cảnh báo từ camera quán ăn. Ảnh 1: 4 khung trong 1,5 giây (trái sang phải, trên xuống dưới), '
+        'cắt quanh MỘT người. Ảnh 2: toàn cảnh, khung đỏ là người đó. Chỉ xét người trong khung đỏ.\n'
+        'GOI: giơ tay ngang hoặc trên đầu, hướng ra quán để gọi nhân viên, giữ hoặc vẫy qua ít nhất 2 khung.\n'
+        f'KHONG_GOI nếu là: {LOAI_TRU_GOI}.\n'
+        'KHONG_CHAC: ảnh không đủ rõ để kết luận. Không đoán.\n'
+        'Điền checklist trước, rồi verdict. reason: tiếng Việt, tối đa 12 chữ.'
     ),
     'needs_clearing': (
-        'Ảnh cắt một bàn trong quán ăn, chụp từ camera trên cao. Bàn này có CẦN DỌN không? '
-        'Cần dọn: khách đã đi nhưng còn bát đĩa, ly đã dùng, thức ăn thừa, giấy ăn bẩn, rác. '
-        'Không cần dọn: bàn trống sạch, chỉ có lọ gia vị, hộp giấy ăn, ly úp sẵn, menu; hoặc khách vẫn đang ngồi ăn. '
-        'Lý do: tiếng Việt, tối đa 12 chữ.'
+        'Kiểm tra cảnh báo "bàn cần dọn" từ camera quán ăn. Ảnh 1: 4 khung trong 1,5 giây cắt quanh bàn {ban}. '
+        'Ảnh 2: toàn cảnh, khung đỏ là bàn đó.{ref} Chỉ xét bàn trong khung đỏ.\n'
+        'CAN_DON: không ai ngồi, còn chén đĩa, ly đã dùng, thức ăn thừa, giấy bẩn.\n'
+        f'SACH: không còn đồ đã dùng. Đồ của quán không tính: {DO_CUA_QUAN}.\n'
+        'personal_belongings_present: túi, điện thoại, áo khoác, ví của khách còn trên bàn hoặc ghế.\n'
+        'KHONG_CHAC: ảnh không đủ rõ. Không đoán.\n'
+        'Điền checklist trước, rồi verdict. reason: tiếng Việt, tối đa 12 chữ.'
     ),
 }
+REF_SENTENCE = ' Ảnh 3: cùng bàn lúc sạch; chỉ tính đồ KHÔNG có trong ảnh 3.'
+QUALITY = ['ok', 'toi', 'mo', 'bi_che', 'qua_nho']
+ALT_CALL = ['vuon_vai', 'chinh_toc', 'uong_an', 'nang_ly', 'dien_thoai', 'chi_tay', 'vay_ban', 'nhan_vien',
+            'khac', 'none']
 VERIFY_SCHEMA = {
     'call': {'type': 'object', 'properties': {
-        'calling': {'type': 'boolean'}, 'confidence': {'type': 'number'}, 'reason': {'type': 'string'}},
-        'required': ['calling', 'confidence', 'reason']},
+        'checklist': {'type': 'object', 'properties': {
+            'hand_above_head': {'type': 'boolean'},
+            'held_or_waved_across_frames': {'type': 'boolean'},
+            'wearing_staff_uniform': {'type': 'boolean'}},
+            'required': ['hand_above_head', 'held_or_waved_across_frames', 'wearing_staff_uniform']},
+        'alt': {'type': 'string', 'enum': ALT_CALL},
+        'image_quality': {'type': 'string', 'enum': QUALITY},
+        'verdict': {'type': 'string', 'enum': ['GOI', 'KHONG_GOI', 'KHONG_CHAC']},
+        'reason': {'type': 'string'}},
+        'required': ['checklist', 'alt', 'image_quality', 'verdict', 'reason']},
     'needs_clearing': {'type': 'object', 'properties': {
-        'needs_clearing': {'type': 'boolean'}, 'confidence': {'type': 'number'}, 'reason': {'type': 'string'}},
-        'required': ['needs_clearing', 'confidence', 'reason']},
+        'checklist': {'type': 'object', 'properties': {
+            'used_items_left': {'type': 'boolean'},
+            'people_at_table': {'type': 'boolean'},
+            'differs_from_clean_ref': {'type': 'boolean'}},
+            'required': ['used_items_left', 'people_at_table']},
+        'personal_belongings_present': {'type': 'boolean'},
+        'image_quality': {'type': 'string', 'enum': QUALITY},
+        'verdict': {'type': 'string', 'enum': ['CAN_DON', 'SACH', 'KHONG_CHAC']},
+        'reason': {'type': 'string'}},
+        'required': ['checklist', 'personal_belongings_present', 'image_quality', 'verdict', 'reason']},
 }
 ANSWER_SCHEMA = {'type': 'object', 'properties': {
     'answer': {'type': 'string'},
@@ -71,8 +102,10 @@
         if schema is not None:
             gc['responseMimeType'] = 'application/json'
             gc['responseSchema' if 'jsonSchema' in self.drop else 'responseJsonSchema'] = schema
-        if image and 'mediaResolution' not in self.drop:
-            gc['mediaResolution'] = 'MEDIA_RESOLUTION_LOW'
+        if image and 'mediaResolution' in self.drop:
+            # API không nhận mức phân giải theo từng ảnh: bỏ ở từng ảnh, đặt một mức chung
+            parts = [{k: v for k, v in p.items() if k != 'mediaResolution'} for p in parts]
+            gc['mediaResolution'] = 'MEDIA_RESOLUTION_MEDIUM'
         if 'thinkingConfig' not in self.drop:
             gc['thinkingConfig'] = {'thinkingLevel': 'MINIMAL'}
         return {'contents': [{'role': 'user', 'parts': parts}], 'generationConfig': gc}
@@ -106,16 +139,24 @@
     async def json(self, parts, schema, image=False):
         return _parse_json(await self.generate(parts, schema, image))
 
-    async def verify(self, kind, jpeg):
+    async def verify(self, kind, images, table=None):
+        """images: list[dict(role, jpeg)] (strip, overview, clean_ref) hoặc bytes (một crop, kiểu cũ).
+        Trả JSON của Gemini (verdict, checklist, image_quality, ...) kèm ms. Quyết định nằm ở decide()."""
+        if isinstance(images, (bytes, bytearray)):
+            images = [{'role': 'strip', 'jpeg': bytes(images)}]
         t0 = time.perf_counter()
-        parts = [{'text': VERIFY_PROMPT[kind]},
-                 {'inline_data': {'mime_type': 'image/jpeg', 'data': base64.b64encode(jpeg).decode()}}]
+        prompt = VERIFY_PROMPT[kind]
+        if kind == 'needs_clearing':
+            has_ref = any(im['role'] == 'clean_ref' for im in images)
+            prompt = prompt.format(ban=table or '', ref=REF_SENTENCE if has_ref else '')
+        parts = [{'text': prompt}]
+        for im in images:
+            parts.append({'inline_data': {'mime_type': 'image/jpeg', 'data': base64.b64encode(im['jpeg']).decode()},
+                          'mediaResolution': {'level': f"MEDIA_RESOLUTION_{ROLE_RES.get(im['role'], 'LOW')}"}})
         d = await self.json(parts, VERIFY_SCHEMA[kind], image=True)
-        ok = bool(d.get('calling' if kind == 'call' else 'needs_clearing'))
-        conf = d.get('confidence')
-        conf = None if conf is None else max(0.0, min(1.0, float(conf)))
-        return dict(ok=ok, confidence=conf, reason=str(d.get('reason') or '')[:120],
-                    ms=int((time.perf_counter() - t0) * 1000))
+        d['reason'] = str(d.get('reason') or '')[:120]
+        d['ms'] = int((time.perf_counter() - t0) * 1000)
+        return d
 
     async def answer(self, question, context):
         prompt = (
@@ -135,6 +176,37 @@
         return (await self.generate([{'text': prompt}])).strip()
 
 
+def decide(kind, d):
+    """Luật quyết định từ JSON của Gemini. Trả (action, path); action: confirm | reject | unverified.
+    Gọi phục vụ: chỉ rút khi KHONG_GOI + ảnh ok + checklist có lý do bác. Cần dọn: chỉ giao việc khi
+    CAN_DON + ảnh ok + còn đồ đã dùng + không người + không đồ cá nhân; chỉ huỷ khi SACH + ok + checklist khớp.
+    Không dùng confidence."""
+    v, q, c = d.get('verdict'), d.get('image_quality'), d.get('checklist') or {}
+    if kind == 'call':
+        if v == 'GOI':
+            return 'confirm', 'confirmed'
+        if v == 'KHONG_GOI':
+            if q != 'ok':
+                return 'unverified', 'poor_image'
+            why = (c.get('hand_above_head') is False or c.get('held_or_waved_across_frames') is False
+                   or c.get('wearing_staff_uniform') is True or d.get('alt') not in (None, 'none', 'khac'))
+            return ('reject', 'rejected') if why else ('unverified', 'inconsistent')
+        return 'unverified', 'uncertain'
+    if q != 'ok' and v in ('CAN_DON', 'SACH'):
+        return 'unverified', 'poor_image'
+    if v == 'CAN_DON':
+        if d.get('personal_belongings_present'):
+            return 'unverified', 'belongings'
+        if c.get('used_items_left') is True and c.get('people_at_table') is False:
+            return 'confirm', 'confirmed'
+        return 'unverified', 'inconsistent'
+    if v == 'SACH':
+        if c.get('used_items_left') is False and c.get('people_at_table') is False:
+            return 'reject', 'rejected'
+        return 'unverified', 'inconsistent'
+    return 'unverified', 'uncertain'
+
+
 def _text(resp):
     try:
         parts = resp['candidates'][0]['content']['parts']
@@ -167,7 +239,7 @@
     if len(sys.argv) >= 2:
         kind = sys.argv[2] if len(sys.argv) > 2 else 'call'
         r = await g.verify(kind, open(sys.argv[1], 'rb').read())
-        print(r)
+        print(r, decide(kind, r))
     else:
         print(await g.generate([{'text': 'Trả lời đúng một chữ: xin chào bằng tiếng Việt.'}]))
     print('bỏ trường:', g.drop or 'không')
--- a/easy-fnb/server/hub.py
+++ b/easy-fnb/server/hub.py
@@ -11,6 +11,8 @@
 from datetime import datetime, timedelta, timezone
 from pathlib import Path
 
+from .gemini import decide
+
 VN = timezone(timedelta(hours=7))
 
 EDGE_KIND = {'goi_phuc_vu': 'call', 'can_don': 'needs_clearing', 'khach_moi': 'new_guest',
@@ -30,6 +32,39 @@
 ]
 DEFAULT_SETTINGS = dict(verify_kinds=['call', 'needs_clearing'], hold_until_verified=['needs_clearing'],
                         escalate_s=45, dedup_s=20)
+VERIFY_TIMEOUT_S = 2.5          # Gemini chậm hơn thế thì cảnh báo thành "Chưa xác minh"
+UNVERIFIED_VI = {'uncertain': 'Gemini không chắc', 'poor_image': 'ảnh kém', 'inconsistent': 'trả lời không khớp',
+                 'belongings': 'còn đồ cá nhân, có thể khách ra ngoài tạm', 'timeout': 'Gemini quá hạn',
+                 'error': 'Gemini lỗi', 'breaker_open': 'tạm ngừng gọi Gemini sau nhiều lỗi liên tiếp'}
+
+
+class CircuitBreaker:
+    """Sau `fails` lỗi liên tiếp (lỗi hoặc quá hạn) thì ngừng gọi trong `cooldown_s`, rồi cho thử đúng một lần."""
+
+    def __init__(self, fails=3, cooldown_s=60.0, clock=time.monotonic):
+        self.fails, self.cooldown_s, self.clock = fails, cooldown_s, clock
+        self.n, self.opened_at, self.trial = 0, None, False
+
+    @property
+    def state(self):
+        if self.opened_at is None:
+            return 'closed'
+        return 'half_open' if self.clock() - self.opened_at >= self.cooldown_s else 'open'
+
+    def allow(self):
+        st = self.state
+        if st == 'half_open' and not self.trial:
+            self.trial = True
+            return True
+        return st == 'closed'
+
+    def success(self):
+        self.n, self.opened_at, self.trial = 0, None, False
+
+    def failure(self):
+        self.n += 1
+        if self.trial or self.n >= self.fails:
+            self.opened_at, self.trial = self.clock(), False
 
 
 def now_ms():
@@ -63,6 +98,8 @@
         self.tables = {}     # "cam/table" -> TableState
         self.alerts = {}     # id -> Alert (giữ cả ca, theo thứ tự tạo)
         self.crops = {}      # alert id -> jpeg bytes
+        self.media = {}      # alert id -> [dict(role, jpeg)] gửi cho Gemini (dải 2x2, toàn cảnh, bàn sạch)
+        self.breaker = CircuitBreaker()
         self.log = deque(maxlen=500)
         self.subs = set()
         self.online = Counter()
@@ -268,6 +305,7 @@
         if crop:
             self.crops[aid] = crop
             (self.data / 'crops' / f'{aid}.jpg').write_bytes(crop)
+        self.media[aid] = list(ev.get('images') or []) or ([{'role': 'strip', 'jpeg': crop}] if crop else [])
         check = self.gemini.enabled and kind in self.settings['verify_kinds'] and crop is not None
         hold = check and kind in self.settings['hold_until_verified']
         a = dict(id=aid, kind=kind, table=table, camera=cam, created_at=now_ms(), video_t=ev.get('video_t'),
@@ -290,40 +328,52 @@
             asyncio.get_running_loop().create_task(self._verify(aid))
         return aid
 
+    def _unverified(self, a, path, detail=None):
+        """Không đủ căn cứ để rút hay xác nhận: giữ cảnh báo, gắn "Chưa xác minh"; việc đang giữ thì giao luôn."""
+        a['verify'].update(state='unverified', path=path, reason=detail or UNVERIFIED_VI.get(path, path))
+        if a['status'] == 'verifying':
+            a['status'] = 'open'
+            self._assign(a)
+        self.add_log('verify', f'Chưa xác minh {where_l(a["table"], a["camera"])} {KIND_VI[a["kind"]]}: '
+                               f'{UNVERIFIED_VI.get(path, path)}', a['table'], a['camera'], a['id'])
+        self._pub_alert(self._public(a))
+
     async def _verify(self, aid):
         a = self.alerts.get(aid)
         if a is None:
             return
+        if not self.breaker.allow():
+            return self._unverified(a, 'breaker_open')
         try:
-            r = await self.gemini.verify(a['kind'], self.crops[aid])
-        except Exception as e:  # lỗi mạng hay lỗi API: không chặn việc, cứ báo cho nhân viên
-            a['verify'].update(state='error', reason=str(e)[:160])
-            if a['status'] == 'verifying':
-                a['status'] = 'open'
-                self._assign(a)
-            self.add_log('verify', f'Gemini lỗi khi kiểm tra {where_l(a["table"], a["camera"])}: '
-                                   f'{str(e)[:80]}', a['table'], a['camera'], aid)
-            self._pub_alert(self._public(a))
-            return
-        a['verify'].update(state='confirmed' if r['ok'] else 'rejected', confidence=r['confidence'],
-                           reason=r['reason'], ms=r['ms'])
-        if r['ok']:
+            r = await asyncio.wait_for(self.gemini.verify(a['kind'], self.media[aid], a['table']), VERIFY_TIMEOUT_S)
+        except asyncio.TimeoutError:
+            self.breaker.failure()
+            return self._unverified(a, 'timeout', f'Gemini quá {VERIFY_TIMEOUT_S:g} giây')
+        except Exception as e:  # lỗi mạng, lỗi API, JSON hỏng: không chặn việc
+            self.breaker.failure()
+            return self._unverified(a, 'error', f'Gemini lỗi: {str(e)[:120]}')
+        self.breaker.success()
+        action, path = decide(a['kind'], r)
+        a['verify'].update(verdict=r.get('verdict'), image_quality=r.get('image_quality'),
+                           checklist=r.get('checklist'), reason=r.get('reason'), ms=r.get('ms'), path=path)
+        if action == 'unverified':
+            return self._unverified(a, path, r.get('reason'))
+        if action == 'confirm':
+            a['verify']['state'] = 'confirmed'
+            extra = ''
             if a['status'] == 'verifying':
                 a['status'] = 'open'
                 s = self._assign(a)
                 extra = f', giao cho {s["name"]}' if s else ''
-            else:
-                extra = ''
             self.add_log('verify', f'Gemini xác nhận: {where_l(a["table"], a["camera"])} {KIND_VI[a["kind"]]}{extra}',
                          a['table'], a['camera'], aid)
-        elif (r['confidence'] or 0) >= 0.6 and a['status'] in ('verifying', 'open'):
-            self._close(a, 'cancelled', 'gemini', f'Gemini: {r["reason"] or "báo nhầm"}', publish=False)
         else:
-            self.add_log('verify', f'Gemini nghi báo nhầm ({r["reason"]}), nhưng nhân viên đã nhận việc',
-                         a['table'], a['camera'], aid)
-            if a['status'] == 'verifying':
-                a['status'] = 'open'
-                self._assign(a)
+            a['verify']['state'] = 'rejected'
+            if a['status'] in ('verifying', 'open'):
+                self._close(a, 'cancelled', 'gemini', f'Gemini: {r.get("reason") or "báo nhầm"}', publish=False)
+            else:
+                self.add_log('verify', f'Gemini cho là báo nhầm ({r.get("reason")}), nhưng nhân viên đã nhận việc',
+                             a['table'], a['camera'], aid)
         self._pub_alert(self._public(a))
 
     # ------------------------------------------------------------ thao tác của nhân viên, quản lý
@@ -418,6 +468,7 @@
     def reset(self):
         self.alerts.clear()
         self.crops.clear()
+        self.media.clear()
         self.tables.clear()
         self.log.clear()
         for f in (self.data / 'crops').glob('*.jpg'):
@@ -492,6 +543,7 @@
                     counts={k: sum(1 for a in al if a['kind'] == k) for k in TASK_KINDS},
                     cancelled=sum(1 for a in al if a['status'] == 'cancelled'),
                     rejected_by_gemini=sum(1 for a in al if a['verify']['state'] == 'rejected'),
+                    unverified=sum(1 for a in al if a['verify']['state'] == 'unverified'),
                     response_s=st, done_s={k: v for k, v in stats(done).items() if k != 'p90'},
                     escalated=sum(1 for a in al if a['escalated']), per_staff=per_staff, per_table=per_table)}
 
@@ -501,8 +553,9 @@
         for a in self.alerts.values():
             r = f", nhận sau {(a['acked_at'] - a['created_at']) / 1000:.0f} giây" if a['acked_at'] else ''
             v = a['verify']
-            vv = '' if v['state'] in ('skipped', 'pending') else \
-                f", Gemini {'xác nhận' if v['state'] == 'confirmed' else 'bác bỏ' if v['state'] == 'rejected' else 'lỗi'}"
+            vv = '' if v['state'] in ('skipped', 'pending') else ', ' + {
+                'confirmed': 'Gemini xác nhận', 'rejected': 'Gemini bác bỏ',
+                'unverified': f"chưa xác minh ({UNVERIFIED_VI.get(v.get('path'), 'không rõ')})"}.get(v['state'], 'Gemini lỗi')
             lines.append(f"[{a['id']}] {clock(a['created_at'])} {where(a['table'], a['camera'])} "
                          f"{KIND_VI[a['kind']]}; trạng thái {a['status']}{r}"
                          f"{', người nhận ' + self._staff_name(a['acked_by']) if a['acked_by'] else ''}{vv}"
--- a/easy-fnb/server/app.py
+++ b/easy-fnb/server/app.py
@@ -292,6 +292,9 @@
     b64 = body.get('crop_jpeg_b64')
     try:
         body['crop_jpeg'] = base64.b64decode(b64) if b64 else None
+        # nhiều ảnh cho Gemini: [{"role": "strip"|"overview"|"clean_ref", "jpeg_b64": "..."}]
+        body['images'] = [dict(role=str(im['role']), jpeg=base64.b64decode(im['jpeg_b64']))
+                          for im in body.get('images') or []]
         return dict(alert_id=hub.edge_event(body))
     except (KeyError, ValueError) as e:
         raise HTTPException(400, str(e))
```

### Việc kèm theo, chưa làm

- **Giao diện** (`easy-fnb/src/live/types.ts`, `text.ts`): thêm `'unverified'` vào `VerifyState`, và trong `verifyBadge` thêm `case 'unverified': return { label: 'Chưa xác minh', cls: 'chip chip--warn' };` (cần thêm lớp màu `chip--warn`). Nếu chưa sửa, giao diện hiện "Chưa kiểm tra" cho trạng thái này, sai chữ nhưng không vỡ.
- **Edge** (`easyfnb_test.py`, `gui_may_chu.py`): giữ một deque crop theo track khoảng 2.5 s, dùng vùng cắt cố định lấy từ box lúc sự kiện. Sau sự kiện 1 s thì ghép dải t−0.5…t+1.0 (mục 3) và gửi `images=[strip, overview, clean_ref?]`, dùng dải làm `crop_jpeg_b64` để dashboard hiện luôn dải. Mã dựng ảnh có sẵn trong `dung_goi.py` (`grow_box`, `make_strip`, `make_overview`).
