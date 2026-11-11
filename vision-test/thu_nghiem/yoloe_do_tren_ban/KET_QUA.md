# YOLOE-26 nhìn đồ trên bàn: có đáng thêm vào demo không? (5/11/2026)

Câu hỏi: model hiện tại (yolo26s, 80 lớp COCO) không có lớp dĩa, đũa, khăn giấy, khay, đồ ăn thừa. YOLOE-26 tìm đồ theo chữ mình gõ (gõ "plate" thì tìm dĩa). Nó có thấy được những thứ COCO bỏ sót, và có giúp quyết định "bàn cần dọn" không? Đo trên laptop RTX 3050 4 GB, cùng 91 ảnh bàn đã dùng để chấm model bàn.

## Tóm tắt

- **YOLOE thấy nhiều đồ hơn COCO thật.** Ở clip 01 (camera góc cao), YOLOE-26s thấy dĩa, chai, khăn giấy, giấy lót trên bàn bẩn. COCO chỉ thấy chai và ly. Trên 24 ảnh bàn bẩn của clip 01, YOLOE bắt được 21, COCO bắt được 13.
- **Nhưng một mình YOLOE vẫn kém model bàn hiện tại.** Luật "thấy đồ là bẩn" với YOLOE-26s đúng 73/91, còn PE-Core S/16 đúng 84/91. YOLOE báo nhầm 15 bàn sạch, chủ yếu vì ly quán bày sẵn trên bàn trống.
- **Dùng YOLOE để xác nhận thì có ích, nhưng ít.** Chỉ báo "cần dọn" khi PE-Core nói bẩn VÀ YOLOE thấy đồ: đúng 85/91, và không báo nhầm bàn sạch nào (59/59). PE-Core một mình đúng 84/91 và báo nhầm 2 bàn. Chênh 1 ảnh có thể chỉ là may.
- **Không nên thay yolo26s, chỉ nên chạy kèm.** Cách chạy: một lần khi khách vừa rời bàn, rồi 5–10 giây một lần khi bàn đang "cần dọn". Không cần chạy mọi khung hình. Mỗi lần chạy tốn khoảng 30 ms và 250 MB VRAM; xuất sang TensorRT thì còn 20 ms.
- **Giá trị lớn nhất cho demo: máy nói được bàn còn gì**, ví dụ "bàn 3 còn 2 dĩa, 1 chai, khăn giấy". Đó là thứ COCO không làm được, và nhân viên dễ tin hơn một con số xác suất.
- **Câu nhắc tiếng Việt không dùng được:** chỉ 1/13 từ được hiểu đúng nghĩa ("lon"). Phải gõ tiếng Anh.
- **Bản không câu nhắc (-pf) không nên dùng:** đặt tên đồ rất lung tung (giấy lót thành "thiệp cưới", kẹo thành "viên nang", "tiramisu"). Ở cỡ 1280, nó tốn 1,2–1,4 GB VRAM.

## 1. Model đã tải

| File | Dung lượng | Dùng làm gì |
|---|---|---|
| `yoloe-26n-seg.pt` | 11,7 MB | YOLOE bản nhỏ nhất, có câu nhắc chữ |
| `yoloe-26s-seg.pt` | 31,1 MB | YOLOE bản s, có câu nhắc chữ (**bản nên dùng**) |
| `yoloe-26n-seg-pf.pt` | 16,3 MB | Bản không câu nhắc, có sẵn 4.585 tên đồ |
| `yoloe-26s-seg-pf.pt` | 40,0 MB | Như trên, bản s |
| `mobileclip2_b.ts` | 253,8 MB | Bộ mã hoá chữ của YOLOE-26. Chỉ cần lúc đổi câu nhắc; khi chạy thì không cần |
| `yoloe-26s-seg_21lop_384x640_fp16.engine` / `.onnx` | 25,2 / 41,7 MB | YOLOE-26s đã gắn sẵn 21 câu nhắc, xuất ra TensorRT/ONNX ở cỡ 640 |

Tất cả nằm trong `weights/`. Ultralytics cần gói `clip` để tách chữ, nhưng venv không có. Để không cài gì vào venv dùng chung, `chung.py` mượn bộ tách chữ của `open_clip` (cùng file từ vựng của OpenAI CLIP).

Câu nhắc dùng (21 từ): plate, bowl, cup, glass, bottle, can, chopsticks, spoon, fork, knife, napkin, tissue, tray, food, leftovers, phone, bag, menu, teapot, paper, wrapper.
Luật "bẩn" theo đề bài: thấy một trong {plate, bowl, cup, glass, bottle, chopsticks, napkin, tray, food, leftovers} với độ tin ≥ 0,25.
Với bản -pf, luật dùng các tên cùng nghĩa (dish, mug, wine glass, leftover...), đặt trước khi xem kết quả.

## 2. Nhìn bằng mắt (ảnh trong `anh_mau/`)

Mỗi ảnh có ba tầng: YOLOE-26s có câu nhắc / YOLOE-26s-pf / yolo26s COCO của pipeline, cùng cỡ 1280, độ tin ≥ 0,25. Danh sách đầy đủ: `ket_qua/so_sanh_khung.json`.

| Khung | Đáp án | YOLOE-26s (câu nhắc) | yolo26s COCO |
|---|---|---|---|
| 01 @0,25 s, B1 | cần dọn | 2 chai, 1 dĩa | 2 chai |
| 01 @0,25 s, B4 | cần dọn (giấy lót, khăn) | 2 giấy, 2 khăn giấy | **không thấy gì** |
| 01 @2,75 s, B3 | cần dọn | 4 ly/cốc, dao | 2 ly |
| 01 @6,25 s, B2 | cần dọn | 1 chai, **4 dĩa** | ly rượu, chai, cốc |
| 01 @6,25 s, B4 | trống (ly bày sẵn) | 2 glass (0,27–0,28) | 3 ly rượu (0,53–0,74) |
| 01 @7,75 s, B4 | trống (ly bày sẵn) | 1 glass (0,26) | 6 ly rượu |
| 01 @10,25 s, B1, B2 | trống | không có gì | B2: 1 ly rượu |
| 03 @0,5 s | bàn ăn xong | dĩa (thật ra là khay), chai (thật ra là ly vại), chén, dao | **không thấy gì** |
| 03 @4,5 s | bàn ăn xong | 4 dĩa, 2 chén, chai, **leftovers 0,57**, wrapper | 2 chén, bánh |
| 09 @1 s | có khách, bàn tròn | 6 dĩa lót, 2 bình trà, 4 tách, chén, giấy | 6 tách |

Nhận xét:

- YOLOE thấy đúng loại đồ mà COCO thiếu: dĩa, khăn giấy, giấy lót, bình trà, đồ ăn thừa. Ở clip 09, nó còn tách được dĩa lót và bình trà mà COCO gộp hết thành "cup".
- Tên đồ không phải lúc nào cũng đúng (khay thành "plate", ly vại thành "bottle"). Với luật "có đồ là bẩn" thì sai tên không sao, nhưng câu thông báo cho nhân viên sẽ sai.
- Đồ nhỏ như gói snack, kẹo M&M ở clip 03 không được gọi là "food" hay "wrapper" lúc 0,5 s. Lúc 4,5 s mới thấy "leftovers".
- Ly quán bày sẵn trên bàn trống: YOLOE cho độ tin thấp (0,26–0,29), sát ngưỡng 0,25. COCO cho độ tin cao (0,5–0,7) nên còn tệ hơn.

## 3. Chấm trên 91 ảnh bàn (59 sạch, 32 bẩn)

Mỗi ảnh bàn được chạy trên cả khung hình gốc ở cùng thời điểm. Đồ thuộc bàn nào thì xét theo tâm đồ nằm trong vùng bàn nào, giống pipeline (cách "full"). Cách "crop" là cắt riêng vùng bàn rồi phóng lên 640. Ngưỡng 0,25 được chọn trước khi xem điểm. Cột "tốt nhất" là ngưỡng chọn sau khi xem chính 91 ảnh này, nên đẹp hơn thực tế. AUC không phụ thuộc ngưỡng (1 = tách sạch/bẩn hoàn hảo).

| Cách | Đúng | Bàn sạch đúng | Bàn bẩn đúng | Bẩn clip 01 | AUC | Tốt nhất (ngưỡng) |
|---|---|---|---|---|---|---|
| **PE-Core S/16 (đang dùng)** | **84/91** | 57/59 | 27/32 | 19/24 | **0,974** | — |
| **YOLOE-26s, khung 1280** | 73/91 | 44/59 | **29/32** | **21/24** | 0,930 | 82/91 (0,32) |
| YOLOE-26s, khung 640 | 70/91 | 54/59 | 16/32 | 8/24 | 0,794 | 70/91 |
| YOLOE-26s, cắt bàn 640 | 58/91 | 37/59 | 21/32 | 13/24 | 0,750 | 77/91 |
| YOLOE-26n, khung 1280 | 53/91 | 39/59 | 14/32 | 6/24 | 0,649 | 69/91 |
| YOLOE-26n, khung 640 | 62/91 | 54/59 | 8/32 | 0/24 | 0,686 | 67/91 |
| YOLOE-26s-pf, khung 1280 | 64/91 | 36/59 | 28/32 | 20/24 | 0,677 | 65/91 |
| YOLOE-26n-pf, khung 1280 | 46/91 | 36/59 | 10/32 | 6/24 | 0,507 | 58/91 |
| yolo26s COCO, khung 1280 (luật pipeline) | 59/91 | 39/59 | 20/32 | 13/24 | 0,597 | 61/91 |
| yolo26s COCO, khung 640 | 64/91 | 53/59 | 11/32 | 3/24 | 0,689 | 66/91 |

Đọc bảng:

- **Bản n và cỡ 640 không dùng được** cho camera góc cao: đồ trên bàn chỉ to 10–30 pixel. YOLOE-26n ở 640 không bắt được ảnh bẩn nào của clip 01.
- **Cắt bàn rồi phóng to không giúp**, còn tệ hơn chạy cả khung hình 1280. Ảnh phóng to bị mờ, và model mất ngữ cảnh xung quanh.
- 8 ảnh của clip 03 (bàn chụp gần từ trên) thì gần như mọi cách đều bắt đủ 8/8. Khó là ở camera góc cao.

### Đồ thấy trên bàn sạch: đồ của quán

YOLOE-26s ở 1280, độ tin ≥ 0,25, đếm số ảnh có loại đồ đó:

- **Bàn sạch:** glass 10, plate 2, cup 2, bottle 1, bowl 1.
- **Bàn bẩn:** plate 15, bottle 13, napkin 9, cup 8, bowl 7, leftovers 6.

"Glass" gần như chỉ đến từ ly quán bày sẵn. Thử bỏ "glass" khỏi luật thì YOLOE-26s đúng 82/91 (53/59 sạch, 29/32 bẩn). COCO bỏ "wine glass" thì đúng 79/91 (59/59 sạch, 20/32 bẩn). **Lưu ý:** cách bỏ này nghĩ ra sau khi xem số, nên chưa chắc đúng ở quán khác.

### Danh sách "đồ của quán" học từ một ảnh chụp bàn sạch

Mỗi bàn chụp một ảnh lúc sạch. Đồ thấy trong ảnh đó được coi là đồ của quán và bỏ qua khi chấm. Có hai cách so:

- **Theo vị trí:** đồ ở cùng chỗ trong ảnh chụp (trùng khung từ 30% trở lên) thì bỏ qua.
- **Theo loại đồ:** loại đồ đã có trong ảnh chụp thì bỏ qua, ở đâu cũng vậy.

Bỏ 6 ảnh dùng làm ảnh chụp, chấm 85 ảnh còn lại (53 sạch, 32 bẩn):

| Cách | YOLOE-26s 1280 | yolo26s COCO 1280 | YOLOE-26s-pf 1280 |
|---|---|---|---|
| Không có danh sách | 69/85 | 55/85 | 61/85 |
| Ảnh chụp **đầu** clip, theo vị trí | 69/85 | 55/85 | 65/85 |
| Ảnh chụp **cuối** clip, theo vị trí | **78/85** (49/53, 29/32) | 73/85 (53/53, 20/32) | 77/85 |
| Ảnh chụp cuối, theo loại đồ | 78/85 | 73/85 | 79/85 |
| PE-Core S/16 (không cần ảnh chụp) | 78/85 (51/53, 27/32) | | |

- **Danh sách đồ của quán có ích, nhưng chỉ khi ảnh chụp là lúc bàn đã bày xong.** Ở clip 01, quán bày ly ra bàn B4 lúc khoảng 4 giây. Ảnh chụp lúc 1,25 giây (bàn còn trơn) không có ly, nên không gỡ được báo nhầm nào.
- Vì vậy ảnh chụp phải được cập nhật mỗi khi nhân viên dọn xong và bày lại bàn. Pipeline đã có sự kiện "bàn đã dọn" (`da_don`) để làm việc này. Bộ test hiện tại không đủ để chấm cách cập nhật đó.
- Ngay cả với ảnh chụp tốt nhất, YOLOE + danh sách chỉ ngang PE-Core (78/85), chưa hơn.

### Kết hợp với PE-Core S/16

| Cách | Đúng | Bàn sạch đúng | Bàn bẩn đúng |
|---|---|---|---|
| PE-Core một mình | 84/91 | 57/59 | 27/32 |
| **PE-Core nói bẩn VÀ YOLOE-26s 1280 thấy đồ** | **85/91** | **59/59** | 26/32 |
| PE-Core nói bẩn HOẶC YOLOE thấy đồ | 72/91 | 42/59 | 30/32 |
| PE-Core VÀ COCO yolo26s 1280 | 76/91 | 59/59 | 17/32 |

Hai cách chỉ cùng sai 2 ảnh: `ban/c01_B3_3.100` và `ban/c01_B4_1.000`. Cả hai là khung bẩn cuối cùng, sát lúc bàn chuyển trạng thái.

## 4. Tốc độ và bộ nhớ GPU (RTX 3050 4 GB)

`model.predict` tính cả chuẩn bị ảnh, xử lý kết quả và mặt nạ. Mỗi số là trung bình 40 khung clip 01. VRAM là đỉnh bộ nhớ PyTorch giữ; tiến trình còn tốn thêm khoảng 300 MB cho CUDA. GPU đang dùng chung với một thử nghiệm khác, nên số có thể lệch vài ms.

| Model | 640 | 1280 | VRAM ở 640 / 1280 |
|---|---|---|---|
| YOLOE-26n câu nhắc, PyTorch FP16 | 24,8 ms | 26,1 ms | 68 / 222 MB |
| **YOLOE-26s câu nhắc, PyTorch FP16** | 28,0 ms | **30,0 ms** | 108 / **242 MB** |
| YOLOE-26n-pf | 29,0 ms | 66,1 ms | 362 / 1.244 MB |
| YOLOE-26s-pf | 29,7 ms | 39,7 ms | 292 / 1.368 MB |
| yolo26s COCO, PyTorch FP16 | 18,6 ms | 18,9 ms | 76 / 148 MB |
| **YOLOE-26s, 21 câu nhắc gắn sẵn, TensorRT FP16 736x1280** | | **20,5 ms** | |
| YOLOE-26s, gắn sẵn, TensorRT FP16 384x640 | 11,5 ms | | |
| YOLOE-26s, gắn sẵn, ONNX Runtime | 15,5 ms | 88,8 ms | |

- **Xuất sang TensorRT/ONNX với câu nhắc cố định chạy được.** Cách làm: `set_classes(...)` rồi `export(format='engine', half=True, imgsz=[736,1280])`. Ultralytics gắn luôn câu nhắc vào model, nên khi chạy không cần bộ mã hoá chữ 254 MB.
- Đã so 10 khung: số đồ và tên đồ khớp bản PyTorch ở 9/10 khung, khung còn lại lệch 1 món.
- Dựng engine mất khoảng 5 phút mỗi cỡ. Muốn đổi câu nhắc thì phải dựng lại. Có thể dùng `save_prompt_embeddings` để lưu vector câu nhắc ra file thay cho bộ mã hoá chữ.
- **Engine 736x1280 không còn trong `weights/`:** lần xuất cỡ 640 sau đó đã ghi đè lên nó. Muốn dùng thì chạy lại `do_toc_do.py xuat`.
- Ở cỡ 1280, YOLOE-26s chậm hơn yolo26s COCO khoảng 11 ms với PyTorch, và chỉ khoảng 11 ms nếu cả hai cùng chạy TensorRT (20,5 so với 9,1 ms đo trước đây).
- **Lần chạy chấm 91 ảnh đầu tiên lên tới 3,3 GB VRAM**, vượt mức 1,5 GB đã hẹn với thử nghiệm kia. Nguyên do: bản -pf ở cỡ 1280 và 4 model nạp lần lượt trong một tiến trình. Các lần đo sau đã chặn PyTorch ở 1,5 GB, và mọi cấu hình đều chạy được dưới mức đó.

## 5. Nên dùng thế nào

**Bổ sung, không thay thế.** yolo26s vẫn cần cho người, và việc báo "cần dọn" vẫn dựa vào PE-Core S/16 (tốt nhất: 84/91). YOLOE-26s chỉ làm hai việc:

1. **Xác nhận:** chỉ báo "cần dọn" khi PE-Core nói bẩn và YOLOE thấy ít nhất một món trong luật. Trên bộ test, cách này bỏ hết báo nhầm bàn sạch.
2. **Giải thích:** liệt kê đồ còn trên bàn trong thông báo cho nhân viên (dĩa, chai, khăn giấy...).

**Chạy khi nào:** không chạy mọi khung hình. Đề xuất:

- 1–2 giây sau sự kiện "khách rời bàn", chạy một lần ở cỡ 1280 trên cả khung hình.
- Khi bàn đang "cần dọn", chạy 5–10 giây một lần để biết lúc nào đã dọn xong.
- Không chạy khi bàn có khách: đồ ăn trên bàn có khách là bình thường.

Mỗi lần khoảng 30 ms (PyTorch) hoặc 20 ms (TensorRT) cho cả khung hình, dùng chung cho mọi bàn trong camera. Tốn dưới 1% GPU, và chỉ thêm 250 MB VRAM.

**Đồ của quán:** bỏ "glass" khỏi luật, hoặc chụp lại danh sách đồ của từng bàn mỗi lần có sự kiện "bàn đã dọn". Nếu quán bày sẵn chén, đũa, ống đũa, hộp khăn giấy trên bàn thì càng cần làm, vì YOLOE thấy được chúng.

**Cho demo 14/11:** đáng thêm, ở dạng "chạy khi khách vừa đi + liệt kê đồ trong thông báo". Đây là phần dễ thấy nhất mà COCO không làm được. Cần làm thêm:

- Dùng YOLOE-26s ở cỡ 1280, không dùng bản n hay cỡ 640.
- Ghép tên tiếng Anh sang tiếng Việt khi hiển thị: plate → dĩa, bowl → chén/tô, napkin → khăn giấy...
- Chạy thử trên footage quán Việt mà bạn đang quay. Bộ test hiện tại là quán Tây, chưa có đũa, chén Việt hay ống đũa.

Đừng hứa độ chính xác cao hơn bản hiện tại: chênh 84 → 85 là 1 ảnh.

## 6. Ca sai (YOLOE-26s 1280, ngưỡng 0,25)

**Báo nhầm bàn sạch (15 ảnh):**

- B4 từ 4,25 đến 8,25 giây (9 ảnh): ly quán bày sẵn, YOLOE gọi là "glass" với độ tin 0,26–0,29.
- B2 lúc 8,75–14,75 giây (5 ảnh): khăn trải bàn sẫm màu và ly bày sẵn bị gọi là "bowl" (0,50), "plate", "cup".
- B1 lúc 7,25 giây: hai thứ bị gọi là "bottle" (0,39). Khung 7,75 giây cho thấy nhân viên đang dọn bàn này, nên có thể là đồ trên tay nhân viên.

**Sót bàn bẩn (3 ảnh):**

- B3 lúc 3,1 giây: không thấy gì. Đây là cuối đoạn bẩn, mốc 3,25 giây ngay sau đã là "đang đổi".
- B4 lúc 1,0 giây: chỉ thấy "napkin" 0,08. Đây là khung bẩn cuối, 0,25 giây sau bàn đã trống.
- B1 lúc 0,5 giây: chỉ thấy "plate" 0,15.

**Tên sai** (không ảnh hưởng luật, nhưng thông báo sẽ sai):

- Khay giấy ở clip 03 bị gọi là "plate", ly vại bị gọi là "bottle".
- Giấy lót bàn ở B4 bị gọi là "paper". Đúng thì cũng là đồ cần dọn.
- Bản -pf đặt tên lung tung: "wedding invitation", "capsule", "tiramisu", "kebab", "squeeze".

## 7. Câu nhắc tiếng Việt

Bộ mã hoá chữ MobileCLIP2 chỉ học tiếng Anh. So 13 từ Việt với từ Anh cùng nghĩa:

- Chỉ "lon" → "can" là đúng. 10 từ (dĩa, đĩa, chén, tô, ly, cốc, chai, đũa, muỗng, khay) đều giống "can" nhất; "khăn giấy" và "đồ ăn thừa" giống "chopsticks" nhất. Có lẽ vì chữ có dấu bị tách thành mảnh byte vô nghĩa.
- Chạy thật với câu nhắc tiếng Việt: clip 01 lúc 0,25 giây không thấy gì cả. Clip 03 chỉ thấy "chai".

**Phải dùng câu nhắc tiếng Anh**, rồi dịch tên khi hiển thị.

## 8. Giấy phép

- **YOLOE-26 và Ultralytics dùng AGPL-3.0**, giống yolo26s/yolo26-pose mà pipeline đang dùng, nên không thêm ràng buộc mới.
- Demo hackathon thì không vấn đề. Nếu Easy FnB thành sản phẩm đóng mã hoặc chạy dịch vụ cho khách, AGPL đòi công khai mã nguồn của cả phần dùng model. Nếu không muốn công khai thì phải mua Ultralytics Enterprise License.
- Bộ mã hoá chữ `mobileclip2_b.ts` là trọng số MobileCLIP2 của Apple, có giấy phép riêng. Nên đọc trước khi dùng thương mại. Nếu xuất engine với câu nhắc gắn sẵn thì không cần mang file này theo sản phẩm.

## 9. Chạy lại

```bat
cd vision-test\thu_nghiem\yoloe_do_tren_ban
set PYTHONIOENCODING=utf-8
:: 1. chạy các model trên 91 ảnh bàn, lưu ket_qua/phat_hien.json
..\..\venv\Scripts\python chay_yoloe.py
:: 2. kết quả từng ảnh của PE-Core S/16 (đặc trưng ảnh đã lưu từ danh_gia/so_clip.py --cache)
..\..\venv\Scripts\python pe_core_tung_anh.py --cache <thư mục feats>
:: 3. chấm điểm, danh sách đồ của quán, kết hợp
..\..\venv\Scripts\python cham_91.py
:: 4. ảnh mẫu và so sánh với COCO
..\..\venv\Scripts\python ve_khung.py
:: 5. tốc độ, VRAM, xuất TensorRT/ONNX
..\..\venv\Scripts\python do_toc_do.py do
..\..\venv\Scripts\python do_toc_do.py xuat
:: 6. câu nhắc tiếng Việt
..\..\venv\Scripts\python chay_yoloe.py --tieng-viet
```

(venv nằm ở chỗ khác thì đổi đường dẫn python.) Số liệu gốc: `ket_qua/diem_91.json`, `ket_qua/toc_do.json`, `ket_qua/so_sanh_khung.json`, `ket_qua/tieng_viet.json`.

**Lưu ý khi đọc số:**

- Bộ test nhỏ: 91 ảnh, phần lớn từ một clip quán Tây quay time-lapse.
- PE-Core S/16 được chọn trên chính 91 ảnh này, nên số của nó cũng hơi đẹp.
- Cách bỏ "glass" và cách chụp ảnh cuối clip đều nghĩ ra sau khi xem kết quả.
