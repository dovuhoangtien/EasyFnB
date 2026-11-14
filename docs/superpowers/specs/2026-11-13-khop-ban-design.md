# Khớp bàn chính xác hơn (spec, chưa code)

Ngày: 13/11/2026 · Nhánh: `gemini-decision` · Trạng thái: đã duyệt, đã làm (14/11), chưa commit. Kết quả: mục 10

## 1. Mục tiêu

Camera gán đúng người, đồ vật và sự kiện (khách ngồi, giơ tay gọi, cần dọn, còn đồ cá nhân) vào đúng bàn.
Sai bàn thì nhân viên đi nhầm chỗ, bàn trống bị tính "có khách", bàn có khách bị báo "cần dọn".

## 2. Hiện tại làm thế nào

Tất cả nằm trong `vision-test/easyfnb_test.py`.

| Việc | Cách làm | Chỗ trong code |
|---|---|---|
| Người thuộc bàn nào | Lấy một điểm neo ở giữa khung người, cách đỉnh 60% chiều cao khung. Chọn bàn có mép gần điểm đó nhất, nếu cách mép không quá 0,45 lần chiều cao khung. | `nearest_table`, dòng 1095 và 1178 |
| Chống nhảy bàn | Bàn mới phải là bàn gần nhất liên tục 0,4 s mới đổi. | `ban_on_dinh` |
| Đếm khách của bàn | Đếm người gán vào bàn, bỏ người đang đi, đang đứng, là nhân viên. | dòng 1235 |
| Nhân viên tới bàn | Nhân viên đứng ở bàn (theo cùng luật gán), vừa đi tới trong 15 s. | dòng 1239 |
| Đồ trên bàn | Tâm món đồ nằm sâu nhất trong bàn nào thì thuộc bàn đó, lệch mép tối đa 12 px. | dòng 1226 |
| Bàn bẩn | Model ảnh chấm ảnh cắt quanh vùng bàn, nới thêm 10% mỗi phía. | `table_crop` |
| Đồ cá nhân | Bàn gần nhất, và tâm đồ cách mép không quá một tỉ lệ cạnh ngắn của bàn. | `thuoc_ban` |
| Tự tìm bàn | Khung chữ nhật của lớp "dining table" (COCO). Mỗi bàn là một hình chữ nhật thẳng. | `thiet_lap.find_tables` |

Máy chủ (`hub.py`, `giai_doan.py`) chỉ nhận tên bàn camera gửi lên. Nó không tự kiểm lại bàn nào.

## 3. Lỗi có thật (đã xem bằng mắt)

Chạy luật hiện tại trên khung hình của các clip đã vẽ vùng bàn (`zones.json`), vẽ ra rồi xem từng người.

| Clip, giây | Chuyện gì xảy ra | Loại lỗi |
|---|---|---|
| `01_phong_an_goc_cao` giây 4 | Khách ngồi ở bàn B3, khung người cao và kéo dài xuống phía dưới, nên điểm neo rơi vào B4. B4 đang trống mà bị tính có khách. | Góc quay nghiêng, bàn sát nhau |
| `01` giây 2,5 và 4 | 6 trên 11 người có khoảng cách tới bàn gần nhất và bàn kế tiếp chênh dưới 0,3 lần chiều cao người. Gán gần như đoán. | Bàn sát nhau |
| `m08_quan_an_vn_nv_ao_den` giây 20 | Bàn B1 có 4 khách, máy chỉ đếm 2. Người áo sơ mi caro ngồi gần camera không thuộc bàn nào: khung người to, điểm neo nằm ngoài vùng. Người áo xám ngồi B1 bị gán sang B5. | Người ngồi lệch ra ngoài vùng vẽ |
| `m08` giây 20 | Nhân viên áo đen đứng sau lưng khách được gán B5. Vẫn đúng ý nếu model nhận ra nhân viên. Nếu không nhận ra thì người này thành khách B5. | Nhân viên |
| `m10_cafe_vn_khach_ve_nv_don_ban_6phut` giây 185 | Khách ngồi quay lưng ở B2, chỉ thấy đầu và vai ở mép dưới. Khung người ngắn, điểm neo nằm dưới mép bàn quá xa, nên không thuộc bàn nào. Nhân viên đứng cạnh B2 thì lại được gán B2. | Ngồi lệch vùng, khung người bị cắt |
| `m10` giây 185 | Khách vừa tới, đang đứng cạnh B1, được gán ngay vào B1. Lần này không sao vì đang đứng thì không đếm, nhưng nếu tư thế đọc sai thì bị đếm. | Người đứng cạnh bàn |
| `m01_bbq_vn_ban_an` giây 28 | Hai khách ngồi ở B1 (áo đỏ) không thuộc bàn nào, vì vùng B1 vẽ nhỏ hơn mặt bàn thật. | Vùng vẽ nhỏ |
| Ghi chép cũ (`thu_nghiem/trang_thai_ban/KET_QUA.md`) | Ở clip 01, khung người của bàn bên phủ lên bàn này 30–50% ngay cả khi bàn trống. | Bàn sát nhau |

Những lỗi chung rút ra:

1. **Điểm neo cố định ở 60% khung người không hợp mọi góc.** Camera cao nhìn xuống thì khung người ngồi kéo dài xuống bàn phía trước. Người bị che hay bị mép khung cắt thì 60% rơi lung tung.
2. **"Bàn gần nhất" không biết ghế ở đâu.** Khách ngồi ở ghế, ghế ở ngoài vùng bàn. Vùng bàn vẽ sát mặt bàn nên khách ở xa mép bị bỏ, còn bàn sát nhau thì khách bị chia nhầm.
3. **Không có khái niệm "không chắc".** Chênh 1 px vẫn chọn một bàn và tin luôn.
4. **Chỉ giữ bàn 0,4 s.** Khách đã ngồi 20 phút vẫn có thể bị đổi bàn khi tay với sang bàn bên.
5. **Ảnh cắt bàn để chấm bẩn nới 10%**, nên ly của bàn bên nằm sát mép có thể lọt vào.
6. **Bộ đo không chấm bàn của việc giơ tay.** `do_chinh_xac.py` chỉ so vị trí ngang của người giơ tay (`khop`, dòng 64). Gọi đúng người nhưng sai bàn vẫn tính là đúng.

## 4. Gemini Decision làm được gì ở đây

### Decision trả về gì

Gửi một hoặc vài ảnh kèm vài câu hỏi có/không. Nhận về xác suất "có" (0,01 đến 0,99) cho từng câu, không có chữ.
Mã đã dùng nó cho kiểm tra gọi phục vụ, cần dọn và nhìn quanh (`gemini.py`, `_verify_decision`, `_decide_probs`), và cho giai đoạn bữa ăn (`table_check`).

### Thử thật trên câu "người này ngồi ở bàn nào"

Cách hỏi: cắt ảnh quanh người và các bàn ứng viên, vẽ khung đỏ quanh người, vẽ mỗi bàn một màu viền.
Hỏi mỗi bàn một câu: "Người trong khung đỏ có đang ngồi ăn uống ở bàn viền cam không?". Thêm câu "có đang ngồi không" và "ảnh có đủ rõ không".
Chỉ dùng khung hình từ `vision-test/clips/` (clip 01 và 02). Ảnh từ `video_mang/` chỉ xem trên máy, không gửi đi.

| Ca | Luật cũ | Đáp án (xem bằng mắt) | Decision: bàn đúng / bàn kia | Thời gian |
|---|---|---|---|---|
| Clip 01 giây 4, khách ở B3 | B4 (sai) | B3 | **0,76** / 0,13 | 1,1 s |
| Clip 01 giây 4, khách ở B2 | B2 | B2 | 0,60 / 0,20 | 0,6 s |
| Clip 02 giây 5, khách ở B2 | B2 | B2 | 0,87 / 0,10 | 1,1 s |
| Clip 01, 3 ca khó nhìn | B2, B3, B3 | không chắc | 0,60 / 0,18; 0,87 / 0,09; 0,83 / 0,11 | 0,6–0,9 s |

- Ca luật cũ sai, Decision sửa đúng và khá chắc.
- Ảnh trên cao, nhỏ, mờ: câu "ảnh đủ rõ" chỉ 0,49–0,80. Nên câu này không dùng để bỏ kết quả, chỉ dùng ngưỡng thấp như `giai_doan.CLEAR_MIN`.
- Mỗi lần hỏi khoảng 830–850 token đầu vào (khoảng 300 chữ, 550 ảnh), 0 token đầu ra. Ảnh 26–88 KB.
- Thời gian 0,6–1,1 s, gọi từ laptop. Khớp với số đo cũ trong `docs/he-thong-hien-tai.md` (0,5–1,5 s).
- **Giá:** chưa tìm được bảng giá chính thức của Decisions API. Tính theo token: nếu giá cỡ Flash-Lite (khoảng 0,10 USD cho 1 triệu token đầu vào) thì 1.000 lần hỏi tốn khoảng 0,085 USD. Phải xem lại trang giá của Google trước khi ước tính cho quán thật.
- Chỉ có 6 ca. Đủ để biết cách hỏi này dùng được, chưa đủ để chọn ngưỡng.

## 5. Ba cách làm

### Cách A: Sửa hình học, không gọi AI

> **Cập nhật khi làm (13/11):** thử trên 67 khách có nhãn, neo theo hông **kém hơn** neo 60% khung (đúng 48–62 so
> với 58–66), vì người ngồi sau bàn hay bị che hông. Đã bỏ ý 1, giữ neo cũ. Thứ có ích là ý 2 làm đơn giản: nới
> khoảng cách cho người không đứng từ 0,45 lên 0,6 lần cỡ người, và cỡ người lấy cả theo bề ngang khi khung bị
> che chỉ còn đầu vai. Ý 5 (tô xám bàn bên khi chấm bẩn) chưa làm: model bàn bẩn học trên ảnh thường, tô xám có
> thể làm nó lệch, cần đo riêng.

1. **Điểm neo theo khung xương.** Đã có 17 điểm khung xương của mỗi người. Thấy rõ hông thì neo ở giữa hai hông. Không thấy hông thì lấy vai rồi dời xuống một đoạn bằng chiều dài thân trung bình. Không thấy cả hai thì mới dùng 60% khung như bây giờ.
2. **Vùng ngồi cho mỗi bàn.** Tự sinh từ vùng bàn: nới đa giác bàn ra mọi phía một khoảng theo cỡ bàn. Ở chỗ hai vùng ngồi chồng nhau thì chia đôi theo đường giữa hai bàn. Chủ quán không phải vẽ thêm gì.
3. **Điểm cho từng cặp người–bàn.** Gộp khoảng cách điểm neo tới bàn, việc điểm neo có nằm trong vùng ngồi không, và tư thế (ngồi được cộng, đứng bị trừ). Bàn điểm cao nhất thắng. Nếu bàn thứ hai sát điểm quá một mức thì đánh dấu "không chắc".
4. **Giữ bàn lâu hơn khi đang ngồi.** Người đã ngồi ở một bàn quá 5 s thì chỉ đổi bàn khi đứng dậy và đi. Người đang đứng vẫn giữ 0,4 s như cũ.
5. **Đồ và ảnh bàn.** Ảnh cắt bàn để chấm bẩn thì tô xám phần thuộc bàn bên. Đồ cá nhân trên ghế thì tính theo vùng ngồi, không theo vùng bàn.

- **Được:** không tốn tiền, không trễ, chạy ở mọi khung hình, không phụ thuộc mạng.
- **Mất:** vẫn đoán ở ca thật sự khó, ví dụ hai bàn sát nhau nhìn từ góc thấp. Có thêm vài hằng số phải chỉnh.

### Cách B: Cách A, cộng hỏi Decision khi không chắc (đề xuất)

Giữ toàn bộ cách A. Thêm một bước: khi một người **đang ngồi** bị đánh dấu "không chắc" giữa hai hoặc ba bàn quá 2 s, hỏi Decision một lần.

1. Camera cắt ảnh như phần thử ở trên: khung đỏ quanh người, mỗi bàn ứng viên một màu. Dùng ảnh đã làm mờ mặt (`an_danh()`), như các ảnh sự kiện đang gửi.
2. Camera gửi ảnh lên máy chủ. Máy chủ gọi Decision, vì khoá Gemini chỉ nằm ở máy chủ. Máy chủ trả xác suất về cho camera.
3. Một bàn đạt từ 0,7 trở lên và mọi bàn khác từ 0,3 trở xuống thì chốt người đó vào bàn này cho tới khi người đó đứng dậy và đi. Còn lưng chừng thì giữ kết quả hình học và không hỏi lại người đó trong 60 s.
4. Trong lúc chờ (khoảng 1 s), người đó vẫn theo bàn của cách A. Việc gọi phục vụ **không đợi** Decision: gửi ngay với bàn tạm. Nếu Decision đổi bàn thì gửi bổ sung qua đường gửi ảnh chứng cứ đã có (`edge_evidence`), máy chủ sửa bàn của việc đó.
5. Giới hạn: mỗi camera tối đa 1 câu hỏi mỗi 10 s. Mất mạng, hết hạn mức hay lỗi thì dùng kết quả cách A, giống cách đang làm với kiểm tra ảnh (`_unverified`).

- **Được:** sửa đúng loại ca khó mà hình học không gỡ được. Ít lần gọi, vì hầu hết người được cách A gán chắc. Dùng Gemini đúng chỗ, hợp yêu cầu cuộc thi.
- **Mất:** thêm một đường camera → máy chủ → Gemini. Trễ khoảng 1 s cho ca không chắc. Tốn tiền, dù ít. Decision sai thì sai cả lượt ngồi đó, vì đã chốt.

### Cách C: Bản đồ mặt sàn hoặc tự học chỗ ngồi

Chủ quán chấm 4 điểm trên sàn để máy đổi ảnh camera sang mặt bằng nhìn từ trên. Hoặc máy tự ghi lại những chỗ khách hay ngồi lâu rồi dùng làm chỗ ghế.

- **Được:** đúng nhất về lâu dài, không lệ thuộc góc quay.
- **Mất:** thêm bước thiết lập cho chủ quán. Khách ngồi thì chân bị bàn che, nên chiếu điểm chân xuống sàn cũng sai. Tự học cần nhiều giờ quay. Không kịp trước ngày demo 14/11.

## 6. Chọn cách B

Làm theo hai bước, đo sau mỗi bước:

1. **Bước 1, cách A.** Đo. Nếu đã đủ tốt thì dừng ở đây.
2. **Bước 2, thêm Decision.** Chỉ cho người đang ngồi bị đánh dấu "không chắc". Đo lại, và đếm số lần gọi mỗi giờ.

Lý do: phần lớn lỗi ở bảng mục 3 là do điểm neo và vùng vẽ (người ngồi bị bỏ, người bị đẩy sang bàn trống). Cách A sửa được mà không tốn gì. Decision dành cho phần còn lại, nơi ảnh cho thấy rõ còn hình học thì không.

Việc cần sửa (dự kiến, chờ duyệt):

| Tệp | Sửa gì |
|---|---|
| `vision-test/easyfnb_test.py` | Điểm neo theo khung xương, vùng ngồi, điểm người–bàn, cờ "không chắc", giữ bàn khi ngồi, tô xám bàn bên trong ảnh chấm bẩn. Thay `nearest_table` và `ban_on_dinh`, không viết lại cả tệp. |
| `vision-test/gui_may_chu.py` | Gửi câu hỏi "người này ở bàn nào" kèm ảnh, nhận xác suất về. |
| `easy-fnb/server/gemini.py` | Thêm một hàm hỏi bàn, cùng kiểu với `table_check`. |
| `easy-fnb/server/app.py`, `hub.py` | Một đường API nhận câu hỏi bàn. Cho phép sự kiện gửi bổ sung đổi bàn của việc. |
| `vision-test/do_chinh_xac.py` | Chấm bàn (mục 7). |
| Test | Test cho điểm neo, vùng ngồi, cờ không chắc, giới hạn số lần hỏi, Decision lỗi thì về cách A. |

## 7. Đo trước và sau

### Bổ sung bộ đo (làm trước khi sửa gì)

1. **Nhãn người–bàn.** Tệp mới `vision-test/nhan_ban_nguoi.json`. Mỗi clip đã vẽ bàn (01, 02, m01, m08, m10, m11, m13, m15), lấy 3–5 khung. Mỗi người trong khung ghi: khung người, và một trong các nhãn: tên bàn, `dung` (đứng hoặc đi), `nhan_vien`, `ngoai` (không thuộc bàn đã vẽ). Khoảng 150 người. Gán bằng cách xem ảnh như ở mục 3.
2. **Chấm khớp bàn.** `do_chinh_xac.py` đọc tệp `--dump` (đã có bàn của từng người ở mỗi khung), ghép người theo khung gần nhất về thời gian và độ chồng khung (từ 0,5). In ra:
   - tỉ lệ người ngồi gán đúng bàn,
   - số người ngồi bị bỏ (không thuộc bàn nào),
   - số người bị gán sang bàn khác,
   - số người đứng hoặc nhân viên bị đếm là khách,
   - với bước 2: số lần hỏi Decision mỗi phút video, và tỉ lệ Decision đổi đúng hay đổi sai.
3. **Chấm bàn của việc gọi.** Thêm `ban` vào nhãn `goi_phuc_vu` của các clip có vùng bàn. Hàm `khop` kiểm thêm bàn khi nhãn có `ban`. Hai clip lớp học (10, 12) không có bàn nên giữ như cũ.

### Cách chạy

```bash
python do_chinh_xac.py --out out_do/khop_goc
```

```bash
python do_chinh_xac.py --out out_do/khop_a
```

```bash
python do_chinh_xac.py --so out_do/khop_goc out_do/khop_a
```

Bước 2 chạy thêm một lần với Decision bật, máy chủ thử ở cổng 8094 và `DATA_DIR` trong thư mục tạm, không đụng máy chủ đang chạy ở 8080/8443.

### Mức chấp nhận

- Không loại sự kiện nào trong bảng `do_chinh_xac` tệ đi quá 1 ca so với lần đo gốc.
- Người ngồi gán đúng bàn tăng rõ, và số người ngồi bị bỏ giảm.
- Với bước 2: trung bình dưới 2 lần hỏi mỗi phút cho mỗi camera.
- Bộ clip nhỏ. Như ghi chú trong `do_chinh_xac.py`, chênh 1–2 ca có thể chỉ là may. Không chỉnh ngưỡng theo đúng bộ này.

## 8. Rủi ro

| Rủi ro | Cách giảm |
|---|---|
| Vùng ngồi tự sinh nuốt cả lối đi, người đi ngang bị tính vào bàn | Vẫn bỏ người đang đi và đang đứng như bây giờ. Nới vùng theo cỡ bàn, có giới hạn trên. |
| Giữ bàn lâu làm khách đổi chỗ bị tính sai bàn | Chỉ giữ khi đang ngồi. Đứng dậy và đi là mở lại. |
| Decision nhầm màu viền, hoặc nhầm khi người che bàn | Chỉ chốt khi một bàn từ 0,7 trở lên và các bàn khác từ 0,3 trở xuống. Dùng màu khác hẳn nhau. Bộ đo đếm số lần Decision đổi sai. |
| Gửi ảnh khách ra ngoài | Dùng ảnh đã làm mờ mặt, như các ảnh sự kiện hiện nay. Chỉ gửi ca không chắc. |
| Trễ mạng hoặc hết hạn mức | Không đợi Decision cho việc gọi. Lỗi thì về cách A. Giới hạn 1 câu hỏi mỗi 10 s mỗi camera. |
| Giá chưa rõ | Bộ đo in số lần hỏi và số token. Xem trang giá trước khi bật cho quán thật. |
| Bộ nhãn nhỏ, gán bằng mắt | Ghi rõ độ tin cậy trong tệp nhãn. Không chỉnh ngưỡng theo bộ này. |
| Sửa `easyfnb_test.py` đụng việc của phiên khác | Chỉ thay các hàm nêu trên. Chạy lại test cũ trước khi xong. |

## 9. Ngoài phạm vi

- Gộp người giữa nhiều camera và nhận lại cùng một người khi đi qua camera khác.
- Bản đồ mặt sàn và tự học chỗ ngồi (cách C).
- Huấn luyện lại model người, khung xương hay nhân viên.
- Sửa giao diện vẽ vùng. Vùng ngồi chỉ sinh tự động, chưa hiện trên web.
- Đếm khách bằng Decision (Decision chỉ trả có/không, không trả con số).

## 10. Kết quả khi làm (14/11/2026)

### Đã làm

| Tệp | Việc |
|---|---|
| `vision-test/khop_ban.py` (mới) | `GanBan`: gán khách vào bàn, cờ "không chắc", giữ bàn khi ngồi lâu, chốt theo Decision. `HoiBan`: gửi câu hỏi lên máy chủ ở luồng riêng, tối đa 1 câu mỗi 10 s. |
| `vision-test/easyfnb_test.py` | Khách dùng `GanBan`; **nhân viên giữ luật cũ** (xem dưới). Thêm `p['ban_chac']` cho an ninh dùng lại. Thêm cờ `--khop-cu`, `--hoi-ban URL`, `--khong-hoi-ban`. Ảnh gửi Decision luôn che mặt (`che_luon`). |
| `vision-test/nhan_ban_nguoi.json` (mới) | 112 người ở 18 khung, 8 clip, gán bằng mắt. |
| `vision-test/do_chinh_xac.py` | Chấm khớp bàn từ `chi_tiet.json`; nhãn gọi phục vụ có `ban` thì kiểm cả bàn. |
| `easy-fnb/server/hoi_ban.py` (mới), `app.py`, `hub.py`, `gemini.py`, `API.md` | `POST /api/edge/table-ask`; `Gemini.table_ask`. Mỗi camera tối đa 1 câu mỗi 8 s, quá 4 s thì bỏ, có ngắt mạch riêng. |
| Test | `vision-test/test_khop_ban.py` (22), `server/tests/test_hoi_ban.py` (8). |

### Khác với kế hoạch

- **Neo theo hông bị bỏ**: kém hơn neo 60% khung (mục 5).
- **Chỉ áp cho khách, nhân viên giữ luật cũ.** Áp cho cả nhân viên thì báo "nhân viên tới" nhầm tăng 10 → 13. Nguyên nhân chính là lỗi có sẵn ở khâu nối mã người: hai người cùng một mã trong một khung (ví dụ m11 giây 69,6). Luật cũ tình cờ né được ca đó.
- **Tô xám bàn bên khi chấm bẩn: chưa làm** (mục 5).
- Tìm thêm một lỗi khi đo: bản đầu nhận bàn ngay khi người từ "không bàn" bước vào mép bàn. Đã sửa: cũng phải chờ 0,4 s như luật cũ.

### Số đo (`do_chinh_xac.py`, 8 clip có vùng bàn, 13,4 phút video)

| | Gốc (`out_do/khop_goc`) | Bước 1 (`out_do/khop_a4`) |
|---|---|---|
| Khách ngồi gán đúng bàn | 50/55 | **53/55** |
| Khách ngồi bị bỏ sót | 5 | **2** |
| Gán sai bàn | 0 | 0 |
| Đứng/nhân viên/ngoài bị đếm là khách | 1/25 | 1/25 |
| Trạng thái bàn theo mốc | 126/137 | **128/137** |
| Báo nhầm cần dọn | 1 | **0** |
| Báo nhầm khách mới | 4 | 5 (em bé đứng sau sofa B2 giờ được tính vào B2) |
| Nhân viên tới: đúng / nhầm | 8 / 10 | 8 / 10 |
| Đã dọn, gọi phục vụ | như cũ | như cũ |

- "Không thấy người 32": model người của pipeline (cỡ 544×960) không phát hiện 32 người có nhãn. Đây là lỗi phát hiện người, không phải khớp bàn, và nằm ngoài phạm vi.
- Số trên chấm trên đúng bộ nhãn đã dùng để chọn bán kính 0,6 (chọn thô trong 3 mức 0,45 / 0,6 / 0,8), nên có thể đẹp hơn thực tế.

### Bước 2, Decision (`out_do/khop_b`, máy chủ thử cổng 8094)

| Lần hỏi | Kết quả | Thời gian | Token |
|---|---|---|---|
| Clip 01, khách giữa B3/B2 | B3 0,82 / B2 0,12 → chốt B3 | 0,70 s | 833 |
| Clip 01, khách khác giữa B3/B2 | B3 0,89 / B2 0,08 → chốt B3 | 3,64 s | 836 |
| Thử tay, ca B3/B4 đã biết đáp án, đổi thứ tự màu | B3 0,55 / B4 0,19 → chưa chắc, giữ hình học | 0,75 s | 858 |

- Trên các khung có nhãn, bước 1 đã đúng hết nên Decision chưa sửa thêm được ca nào đo được. Bước 2 an toàn (chỉ chốt khi chắc, lỗi thì về hình học) nhưng **chưa chứng minh được lợi ích** trên bộ nhỏ này.
- Kết quả phụ thuộc thứ tự màu: cùng ca B3/B4, bàn đúng viền cam được 0,76, viền xanh dương chỉ được 0,55.
- Mỗi lần hỏi khoảng 830–860 token đầu vào, 0 token đầu ra, 0,7–3,6 s. Clip 01 (tua nhanh 30 lần) hỏi 2 lần.
- **Sự cố:** bộ lọc `--clip 01_` khớp luôn `m01_bbq_vn_ban_an` (video trên mạng). Vì vậy 2 ảnh của clip đó (đã che mặt) bị gửi lên Gemini, trái với yêu cầu chỉ dùng ảnh `clips/`. Đã tắt máy chủ thử ngay. Lần sau lọc bằng tên đủ (`01_phong`).

## 11. Chỗ khác trong sản phẩm Decision làm tốt hơn hiện tại

Xếp theo lợi ích so với công làm. Tất cả cùng kiểu: camera làm trước, chỉ hỏi Decision khi không chắc.

1. **Giữ chỗ vì còn đồ cá nhân.** Bây giờ dùng YOLOE và model đồ vật tìm túi, điện thoại quanh bàn khi khách vừa rời. Đồ trên ghế thì hay sót, ly của quán thì hay bị nhầm là đồ. Đã có sẵn câu `personal_belongings_present` trong phần kiểm tra cần dọn. Đem câu đó ra hỏi ngay lúc khách vừa rời, thay cho luật YOLOE, để quyết định giữ chỗ hay báo dọn.
2. **Nhân viên hay khách khi model lưng chừng.** Điểm nhân viên trung bình nằm giữa 0,32 và 0,40 (giữa hai ngưỡng tắt và bật) quá 10 s thì hỏi Decision một lần câu `wearing_staff_uniform` rồi nhớ theo người đó. Khách bị nhận nhầm là nhân viên thì không gọi được, nhân viên bị nhận nhầm là khách thì làm bàn có khách giả.
3. **Kiểm "đã dọn xong".** Bàn chuyển từ cần dọn sang trống chỉ dựa vào model bẩn. Người đứng che bàn có thể làm nó tưởng sạch. Hỏi `used_items_left` một lần trước khi báo đã dọn, giống kiểm tra cần dọn hiện nay.
4. **Tự tìm bàn.** Hỏi từng khung tìm được: "Đây có phải bàn khách ngồi ăn không?" Loại quầy, tủ, kệ trước khi đưa cho chủ quán xem.
5. **Khách mới.** Hỏi "có người đang ngồi ở bàn này không" khi bàn chuyển sang có khách mà số người dao động (khách đứng chờ, nhân viên lau bàn). Câu `people_at_table` đã có trong `TABLE_CHECK_QUESTIONS`.

Mục 1 và 2 nên làm ngay sau khớp bàn. Mục 3 đến 5 để sau.
