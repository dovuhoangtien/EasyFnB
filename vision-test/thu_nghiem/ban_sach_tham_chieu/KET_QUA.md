# Thử: so bàn hiện tại với ảnh "bàn sạch" của chính bàn đó (5/11/2026)

Ý tưởng: quản lý bấm "Chụp bàn sạch" một lần cho mỗi bàn. Sau đó, thay vì hỏi model "bàn này trông sạch hay bẩn", ta hỏi "bàn này khác ảnh sạch của nó bao nhiêu". Cách này lấy từ dò bất thường bằng vài ảnh mẫu (AnomalyDINO, WACV 2025) và dò đồ bị bỏ quên.

## Kết luận ngắn

**Không nên đưa vào bản demo 14/11.** Giữ bộ phân loại hiện tại (PE-Core S/16 so với câu mô tả, 84/91).

- **Dùng một mình, mọi cách so tham chiếu đều thua rõ.** Trên 78 ảnh của các bàn có ảnh sạch, cách tốt nhất đúng khoảng 65/78. Bộ phân loại hiện tại đúng 72/78. Tính cả 91 ảnh thì còn khoảng 77/91, so với 84/91.
- **Lý do chính không phải ánh sáng, mà là bàn sạch không đứng yên.** Nhân viên bày ly, trải khăn, đặt giấy lót, nên ảnh "sạch" lúc sau khác ảnh "sạch" lúc chụp. Mỗi bàn lại có mức "khác" bình thường riêng, nên một ngưỡng chung cho mọi bàn không dùng được. Nếu xếp hạng riêng trong từng bàn thì cách so tham chiếu tách rất tốt (AUC 0,99–1,0 với DINOv2), nhưng muốn đặt ngưỡng riêng cho từng bàn thì lại cần ảnh bàn bẩn của chính bàn đó.
- **Người che bàn làm cách so tham chiếu báo nhầm nhiều hơn hẳn.** Khi người hoặc tay che một phần mặt bàn sạch, cách so từng ô ảnh báo "bẩn" 14/16 lần. Bộ phân loại hiện tại báo nhầm 4/16.
- **Kết hợp với bộ phân loại không thắng có ý nghĩa.**
  - Hồi quy logistic (chừa một bàn khi học) tự bỏ khoảng cách đi, nên ra đúng 84/91 như cũ.
  - Lấy trung bình hai điểm thì có một tổ hợp đạt 87/91: ô ảnh PE lớp cuối, k = 5 ảnh sạch rút ngẫu nhiên. Nhưng McNemar cho p ≈ 0,25, và đây là tổ hợp tốt nhất trong khoảng 90 tổ hợp đã thử. Cùng tổ hợp đó với k = 1 hoặc 3 chỉ được 82–83/91. Với cách bấm "Chụp bàn sạch" một lần, nó còn 70,6/78, thua bộ phân loại (72/78).
  - Đây chỉ là tín hiệu nên thử lại khi có thêm clip, chưa phải bằng chứng.
- **Chi phí rất nhỏ.** Các ô ảnh PE có sẵn trong lần chạy PE-Core mà bộ phân loại đã làm, chỉ tốn thêm khoảng 0,5 ms mỗi bàn. Thêm DINOv2-S thì tốn khoảng 15 ms mỗi bàn và 111 MB GPU. Chỗ yếu là độ đúng, không phải tốc độ.

## Dữ liệu và cách chấm

- **Ảnh test:** đúng 91 ảnh của `danh_gia/anh_ban_test` (59 sạch, 32 bẩn).
  - Bàn B3 không có lúc nào trống và sạch trong clip 01 (đáp án chỉ có C, D, x).
  - Clip 03 là cả khung hình, không có ảnh sạch của cùng bàn.
  - Vì vậy 13 ảnh bẩn (5 của B3, 8 của clip 03) không có ảnh tham chiếu. Cách so tham chiếu được chấm trên **78 ảnh**: B1, B2, B4, gồm 59 sạch và 19 bẩn. Khi tính trên 91 ảnh, 13 ảnh kia dùng bộ phân loại (đúng 12/13).
- **Ảnh tham chiếu:** cắt từ clip 01, cứ 0,125 s một khung, trong các đoạn đáp án T của từng bàn. Kiểu cắt giống hệt ảnh test. Cắt lại 83 ảnh test để kiểm thì lệch trung bình 0,78/255, tức là khung hình khớp.
  - Bỏ 18 khung có người che hoặc đang dọn dở. Ngoài đời, quản lý sẽ không bấm chụp lúc đó.
  - Còn lại B1 có 96 ảnh, B2 có 60, B4 có 57.
- **Không bao giờ dùng chính ảnh test,** và luôn bỏ các khung cách thời điểm test dưới 1 s.
- **Hai cách chọn ảnh tham chiếu:**
  - *Rải:* k ảnh rút ngẫu nhiên trong các lúc sạch của bàn, rút 50 lần rồi lấy trung bình.
  - *Một lần bấm:* k khung liền nhau từ một lần bấm, thử mọi thời điểm bấm hợp lệ. Cách này sát thực tế hơn.
- **Ngưỡng:** chừa một bàn. Ngưỡng cho B1 chỉ học từ ảnh test của B2 và B4, và tương tự cho hai bàn kia. Bộ phân loại hiện tại giữ ngưỡng 0,5 như trong pipeline.
- **Các cách đo khoảng cách:**
  - *toàn ảnh:* 1 − cos giữa vector PE-Core S/16 của ảnh test và ảnh sạch gần nhất. Vector này chính là thứ bộ phân loại đang tính.
  - *ô PE lớp cuối / lớp 8:* các ô ảnh 24×24 của PE-Core S/16. Mỗi ô của mặt bàn test tìm ô gần nhất trong bộ nhớ ô của các ảnh sạch. Điểm của ảnh là trung bình 1% ô xa nhất, như AnomalyDINO. Chỉ chấm các ô nằm trong vùng bàn đã vẽ.
  - *ô DINOv2-S:* giống trên nhưng dùng DINOv2-S/14 ở 448×448 (32×32 ô), như bài AnomalyDINO. Bản "trọn" bỏ mặt nạ vùng bàn, giống AnomalyDINO gốc.
  - *+ phân loại:* kết hợp theo hai cách: trung bình (xác suất bẩn chia 0,5, cộng khoảng cách chia ngưỡng của nó, chia đôi) hoặc hồi quy logistic, cả hai đều học kiểu chừa một bàn.
  - *chuẩn hoá:* chia khoảng cách cho độ khác trung bình giữa các ảnh sạch của bàn đó. Cách này không giúp, xem `ket_qua.json`.

## Kết quả chính

### 1. Kiểm lại số cũ

PE-Core S/16 không train đúng **84/91** (sạch 57/59, bẩn 27/32), khớp `KET_QUA.md`. Hai cách tính (code `so_clip.py` và code thử nghiệm này) lệch xác suất nhiều nhất 0,0002.

### 2. So tham chiếu dùng một mình

Cách chọn *rải*, số là trung bình 50 lần rút.

| Cách | k | Đúng /78 | Sạch đúng /59 | Bẩn đúng /19 | AUC | Đúng /91 | McNemar với phân loại |
|---|---|---|---|---|---|---|---|
| **Bộ phân loại hiện tại** | – | **72** | 57 | 15 | **0,979** | **84** | – |
| toàn ảnh | 1 | 61,8 | 51,3 | 10,5 | 0,819 | 73,8 | thua, p ≈ 0,007 |
| toàn ảnh | 3 | 63,3 | 54,5 | 8,8 | 0,853 | 75,3 | thua, p ≈ 0,02 |
| toàn ảnh | 5 | 65,1 | 56,8 | 8,3 | 0,884 | 77,1 | thua, p ≈ 0,07 |
| ô PE lớp cuối | 5 | 57,6 | 49,0 | 8,6 | 0,888 | 69,6 | thua, p ≈ 0,003 |
| ô PE lớp 8 | 1 | 65,1 | 51,7 | 13,4 | 0,915 | 77,1 | thua, p ≈ 0,04 |
| ô PE lớp 8 | 3 | 63,2 | 49,9 | 13,3 | 0,935 | 75,2 | thua, p ≈ 0,004 |
| ô PE lớp 8 | 5 | 64,8 | 51,3 | 13,6 | 0,943 | 76,8 | thua, p ≈ 0,02 |
| ô DINOv2-S | 3 | 62,2 | 48,0 | 14,2 | 0,899 | 74,2 | thua, p ≈ 0,006 |
| ô DINOv2-S | 5 | 63,4 | 49,7 | 13,7 | 0,929 | 75,4 | thua, p ≈ 0,01 |
| ô DINOv2-S trọn (AnomalyDINO gốc) | 5 | 64,9 | 51,3 | 13,5 | 0,921 | 76,9 | thua, p ≈ 0,03 |

Cách chọn *một lần bấm*, k = 3:

| Cách | Đúng /78 | AUC |
|---|---|---|
| toàn ảnh | 60,6 | 0,81 |
| ô PE lớp 8 | 63,6 | 0,92 |
| ô DINOv2 | 62,5 | 0,83 |

Thêm ảnh tham chiếu giúp ít, và cách *một lần bấm* tệ hơn cách *rải*. Cả hai cho thấy vấn đề là bàn được bày lại khác đi, không phải thiếu ảnh.

AUC trong từng bàn (rải, k = 3) cho thấy chỗ hỏng nằm ở ngưỡng, không phải ở thứ tự điểm:

| Cách | B1 | B2 | B4 | Gộp 3 bàn |
|---|---|---|---|---|
| toàn ảnh | 0,979 | 0,738 | 0,993 | 0,869 |
| ô PE lớp 8 | 0,921 | 1,000 | 0,926 | 0,941 |
| ô DINOv2-S | 0,993 | 1,000 | 0,993 | 0,942 |

Ví dụ với DINOv2: ảnh sạch "xa" nhất của B1 có điểm 0,66, còn ảnh bẩn "gần" nhất của B2 có điểm 0,52. Không ngưỡng chung nào tách được cả hai.

### 3. Kết hợp với bộ phân loại

| Cách | k | Đúng /91 (thấp nhất–cao nhất qua 50 lần rút) | Mới đúng mà cũ sai / cũ đúng mà mới sai | p |
|---|---|---|---|---|
| Bộ phân loại hiện tại | – | 84 | – | – |
| mọi cách + phân loại, hồi quy logistic | 1–5 | 83,5–84,6 | ≈ 0 / 0 | 1,0 |
| ô PE lớp 8 + phân loại, trung bình | 5 | 83,8 (83–84) | 0 / 0,2 | 1,0 |
| ô DINOv2 + phân loại, trung bình | 5 | 82,9 (81–84) | 0 / 1,1 | 1,0 |
| ô PE lớp cuối + phân loại, trung bình | 1 / 3 | 82,0 / 83,0 | – | – |
| **ô PE lớp cuối + phân loại, trung bình** | **5** | **87,2 (87–88)** | **3,2 / 0** | **0,25** |

Về dòng 87/91:

- Nó bắt được 3 ảnh bẩn của B2 mà bộ phân loại bỏ sót (6,35 s, 6,475 s, 6,6 s).
- Nhưng nó là tổ hợp tốt nhất trong khoảng 90 tổ hợp, không đạt mức ý nghĩa thống kê, và mất lợi thế ở k = 1, k = 3 và cách *một lần bấm* (70,6/78, thua 72/78 của bộ phân loại).
- Không đủ để đưa vào demo.

### 4. Độ bền

Số là ảnh sai trên 78 ảnh, cách *rải* k = 3. "Báo nhầm" là bàn sạch bị báo bẩn, "sót" là bàn bẩn không bị báo.

| Tình huống | Bộ phân loại | Toàn ảnh | Ô PE lớp 8 | Ô DINOv2 | Ô PE cuối + phân loại, k = 5 |
|---|---|---|---|---|---|
| Ánh sáng như lúc chụp | 2 nhầm / 4 sót | 4,5 / 10,2 | 9,1 / 5,7 | 11 / 4,8 | 1,8 / 1,0 |
| Tối đi 40% | 1 / 6 | 3,9 / 9,3 | 9,6 / 5,3 | 8,9 / 4,8 | 1,3 / 1,0 |
| Sáng lên 40% | 1 / 5 | 4,2 / 8,0 | 8,5 / 5,7 | 11,2 / 4,8 | 2,1 / 1,8 |
| Đèn vàng | 1 / 7 | 4,5 / 9,1 | 11,4 / 3,7 | 9,4 / 5,2 | 1,0 / 3,6 |
| Tối và vàng | 1 / 7 | 5,2 / 7,5 | 12,0 / 3,1 | 9,3 / 5,0 | 1,0 / 2,2 |

- **Ánh sáng** (giả lập trên ảnh test, ảnh tham chiếu giữ nguyên): không phải điểm yếu chính. Cách so tham chiếu vốn đã kém, đổi đèn chỉ làm báo nhầm tăng nhẹ. Bộ phân loại sót thêm 1–3 ảnh bẩn khi đổi đèn. Clip 01 không có lúc đổi đèn thật, nên đây chỉ là giả lập (nhân độ sáng, đổi màu), không đo được bóng đổ hay ánh nắng thật.
- **Người che bàn:** 16 khung bàn sạch có người hoặc tay che mặt bàn (người xem chọn), và 215 khung sạch không bị che.

  | | Bị che: báo nhầm /16 | Không che: báo nhầm /215 |
  |---|---|---|
  | Bộ phân loại | 4 | 2 |
  | Toàn ảnh | 1,8 | 14,5 |
  | Ô PE lớp 8 | 14,6 | 27,4 |
  | Ô DINOv2 | 14,2 | 24,3 |
  | Ô PE cuối + phân loại (k = 5) | 6,1 | 2,6 |

  Cách so từng ô coi tay áo, lưng người là "thứ lạ trên bàn". Đó đúng là điều nó được thiết kế để làm, nên nó báo nhầm gần như mọi lần. Pipeline có trung bình xác suất bẩn trong một cửa sổ thời gian (0,5 s ở clip 01), nên che thoáng qua đỡ hơn. Nhưng nhân viên đứng lau bàn lâu thì vẫn bị báo.
- **Khung vuông lấy cảnh thật, so với khung sát + viền xám:** bộ phân loại tụt từ 72 xuống 70/78 (AUC 0,979 xuống 0,963). Cách so tham chiếu gần như không đổi (ô PE lớp 8 từ 63,2 lên 64,4, DINOv2 từ 62,2 lên 64,8). Không có lý do đổi: giữ khung sát như pipeline.

### 5. Tốc độ (RTX 3050 Laptop, FP16, 4 bàn một lượt, k = 5 ảnh tham chiếu)

| | ms cho 4 bàn | ms mỗi bàn | GPU thêm |
|---|---|---|---|
| Bộ phân loại hiện tại (PE-Core S/16 384×384) | 34 | 8,5 | 92 MB (cả model) |
| + khoảng cách toàn ảnh | +0 | +0 | 5 vector/bàn, không đáng kể |
| + bộ nhớ ô PE (lớp 8) | +2 | +0,5 | 2,1 MB/bàn |
| + DINOv2-S/14 448 + bộ nhớ ô | +58 | +14,6 | +111 MB |

Lúc đo, GPU đang chạy chung với một thử nghiệm khác, nên số ms chỉ để so tương đối. Khi tính đặc trưng cho cả thử nghiệm, GPU dùng đỉnh 1,33 GB (cả hai model và bộ nhớ ô của 3 bàn).

## Nếu sau này vẫn muốn làm (không phải cho demo 14/11)

Cách cắm vào pipeline nếu có thêm dữ liệu chứng minh nó có ích:

1. **Màn hình cài đặt:** thêm nút **"Chụp bàn sạch"** cạnh mỗi vùng bàn.
   - Mỗi lần bấm lưu 3–5 ảnh cắt (kiểu `table_crop` hiện có) vào `models/ban_sach/<camera>/<bàn>/`.
   - Từ chối nếu có người trong vùng bàn.
   - Nên bấm lại mỗi khi bày bàn kiểu khác (có ly, không ly, có khăn), và giữ nhiều kiểu bày cùng lúc.
2. **Lúc chạy:** đúng nhịp `--table-every` hiện tại. Lấy vector PE-Core đã tính cho bộ phân loại, tính thêm khoảng cách. Kết hợp với xác suất bẩn chỉ khi điểm kết hợp vượt ngưỡng.
3. **Tự học ngưỡng riêng từng bàn:** đây là phần thiếu nhất.
   - Ghi khoảng cách những lúc pipeline đã chắc bàn trống và sạch, ví dụ ngay sau sự kiện "đã dọn".
   - Đặt ngưỡng theo phân bố đó, ví dụ phân vị 99% cộng một khoảng an toàn.
   - Không có bước này thì điểm của bàn này không so được với bàn khác.
4. **Bỏ qua khung có người che bàn:** dùng khung người YOLO đè lên vùng bàn. Đây là điều kiện bắt buộc nếu dùng cách so từng ô.

Thứ có thể dùng ngay mà không rủi ro: hiện ảnh "bàn lúc sạch" cạnh ảnh hiện tại trong thông báo "bàn cần dọn", để nhân viên tự nhìn. Việc này không đổi quyết định của model.

## Ảnh lỗi

- [anh_loi/sach_bi_cham_la.jpg](anh_loi/sach_bi_cham_la.jpg): 5 ảnh sạch bị cách so ô PE chấm "lạ" nhất. Mỗi dòng gồm ảnh test, ảnh sạch gần nhất và bản đồ độ lạ từng ô (đỏ là khác).
  - Hai trường hợp người đi ngang che bàn (B1 6,25 s và 7,75 s) cũng là hai ảnh sạch duy nhất mà bộ phân loại hiện tại sai.
  - B4 1,25 s là mặt bàn vừa lau còn vệt ướt.
  - B4 2,25 s gần như y hệt ảnh tham chiếu mà vẫn điểm cao. Trên mặt bàn tối, trơn, ít vân và ảnh video nén, các ô ảnh bị "nhiễu", nên tạo nhiều báo nhầm.
- [anh_loi/nguoi_che.jpg](anh_loi/nguoi_che.jpg): bàn sạch có người hoặc tay che. Cách so ô thấy "lạ" đúng chỗ người.
- [anh_loi/ban_vi_du.jpg](anh_loi/ban_vi_du.jpg): ví dụ bàn bẩn (B1 có giấy, B2 còn chén, B4 có giấy lót và thực đơn).

## Hạn chế của thử nghiệm

- **Dữ liệu ít:** chỉ 1 clip, 3 bàn, 19 ảnh bẩn có tham chiếu, đến từ 4 lần bàn bẩn ngắn.
- **Clip là time-lapse:** 1 s trong clip là nhiều phút ngoài đời, nên bàn được bày lại liên tục. Quán thật có thể ổn định hơn, nhưng cũng có đổi đèn ngày/đêm thật mà ở đây chỉ giả lập.
- **Ngưỡng học từ 2 bàn còn lại:** nhiều bàn hơn thì ngưỡng chung có thể ổn hơn, nhưng sự khác nhau giữa các bàn (xem AUC từng bàn) sẽ vẫn còn.
- **Lớp giữa của PE và kích thước ảnh DINOv2** chọn trước khi chạy, không dò theo điểm. Ngược lại, dòng 87/91 là chọn sau khi xem điểm.

## Tệp

Script chạy theo thứ tự, từ thư mục `vision-test`:

| Bước | Script | Việc làm |
|---|---|---|
| 1 | `cat_anh.py` | Cắt ảnh tham chiếu và ảnh khung vuông, ghi `anh/` và `anh_meta.json` |
| 2 | `tinh_dac_trung.py` | Tính PE-Core và DINOv2, kiểm lại số 84/91, lưu khoảng cách vào `_cache/` (khoảng 440 MB, xoá được, chạy lại mất khoảng 1 phút) |
| 3 | `danh_gia.py` | Ghi `ket_qua.json`: mọi cách, mọi k, độ bền, McNemar |
| 4 | `chan_doan.py` | Ghi AUC từng bàn vào `chan_doan.json` và vẽ ảnh lỗi vào `anh_loi/` |
| 5 | `do_toc_do.py` | Đo tốc độ, ghi `toc_do.json` |

`chung.py` chứa danh sách khung người che bàn, các kiểu đổi ánh sáng và các hàm dùng chung. Thử nghiệm không sửa `easyfnb_test.py`, `clip_cls.py` hay máy chủ. Model mới tải về: DINOv2-S/14 (timm, Apache-2.0, 88 MB).
