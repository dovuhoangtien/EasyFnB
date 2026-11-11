# Thử trên GPU: Bước 0, T1, T2, T3 (5/11/2026)

Máy: laptop RTX 3050 4 GB, cắm điện. Mỗi lần chỉ chạy một việc GPU. Code thử nằm trong `thu_nghiem/gpu/easyfnb_thu.py`, là bản sao của `easyfnb_test.py`. **File gốc chưa bị sửa.** Kết quả từng lần chạy nằm trong `thu_nghiem/gpu/out_*`. `out_v4` vẫn giữ nguyên.

## Tóm tắt

| Phép thử | Kết quả | Ghi chú |
|---|---|---|
| Bước 0: VRAM và khung xương | Xong | Bản nhạy chiếm tối đa ~1,45 GB, kể cả phần trình duyệt đang dùng, nên còn trống ~2,6 GB. `khung_xuong.npz` của cả 11 clip nằm trong `out_b0_nhay/` và `out_b0_nhanh/` |
| T2 (a): chỉ đổi tham số | **Không đạt** | Clip 10 chỉ lên ~11 fps. Bàn tụt còn 129/137 |
| T2 (b): RTMPose cho "ứng viên", tối đa K = 4 | **Không đạt** | Đạt 19 fps, nhưng trễ giơ tay lên 1,2 s, như bản nhanh |
| T2, cách thêm: RTMPose **theo lượt**, K = 4, kèm `--det-every 100 --staff-every 20` | **Đạt** | Clip 10 đạt 18–21 fps, bắt 5/7, trễ 0,42 s, bàn 130/137 |
| T1 đủ như danh sách rút gọn | **Không đạt** | Bắt 6/7, không báo nhầm, trễ tăng 0,24 s. Nhưng tốc độ giảm 4–15%, và ca em mép trái (đích của đường "chỉ RGB") vẫn sót. Đặt lên bản theo lượt thì còn 5/7 và báo nhầm 1 lần |
| T1 rút gọn: chỉ thêm "tích luỹ bằng chứng yếu" | **Đạt** | Bắt 6/7, không báo nhầm trên cả 9 clip âm, trễ +0,18 s, không tốn thêm tốc độ |
| T3: nhân viên theo gallery | **Không đạt** (nhãn rất mỏng) | Khách bị gắn nhân viên hàng loạt. Probe hiện tại cũng kém |

**Bản đề xuất** là bản theo lượt cộng tích luỹ. Đã chạy cả 11 clip:

- trạng thái bàn 130/137 (cho trễ 0,5 s: 136/137);
- giơ tay bắt 6/7, không báo nhầm trên cả 9 clip âm;
- trễ trung bình 0,59 s, theo cả `cham_diem.py` lẫn `cham_su_kien.py`;
- clip 10 đạt 21,0 fps thật, clip đông nhất (09) đạt 24,8.

Bản này qua cả bốn mốc của T2. Riêng mốc trễ 0,59 s chỉ vừa sát 0,6 s, vì lần bắt thêm có trễ 1,72 s. Phần sửa code ở cuối file, **chưa áp dụng**.

## Cách đo tốc độ, và vì sao số dao động

- **"fps thật"** = số khung ÷ thời gian chạy thật, tính từ khung thứ 5. Con số này gồm cả đọc video, model nhỏ và luật. Số `khung_moi_giay` cũ không tính model nhỏ, nên luôn cao hơn. Bản sao ghi thêm `fps_thuc` vào `su_kien.json`.
- **VRAM** lấy bằng `nvidia-smi` mỗi giây. Card dùng chế độ WDDM nên không xem được bộ nhớ của riêng từng chương trình. Số ghi dưới đây là tổng cả card, gồm cả phần trình duyệt (lúc nghỉ chiếm 190–830 MB, thay đổi theo thời điểm).
- **Cùng một cấu hình, chạy hai lần có thể lệch 10–15%.** Ví dụ v4 nhạy ở clip 10 có lần 7,0 fps, có lần 11,0. Nguyên nhân là laptop nóng (GPU 72–75 °C ngay cả lúc nghỉ) và các chương trình khác trên máy. Vì vậy so tốc độ bằng cách chạy xen kẽ các cấu hình trên clip 10, mỗi cấu hình 3 vòng (`bench_all.sh`, kết quả ở `bench_log.txt`).
- **Vòng 3 bị loại.** Lúc đó một chương trình khác đang dùng GPU: GPU bận 8–34% khi mình không chạy gì, VRAM nền lên 650–1150 MB. Ở vòng này bản theo lượt tụt còn 12,5 fps, T1 đủ còn 5,5 fps, và một lần chạy chết ngay lúc nạp model, không để lại log. Các bảng dưới chỉ dùng vòng 1–2, cộng các lần chạy để chấm điểm.

## Bước 0: VRAM, fps từng clip, khung xương

Lệnh: v4 nhạy và v4 nhanh trên cả 11 clip, có `--dump --luu-khung-xuong --no-video`. Thư mục: `out_b0_nhay/` và `out_b0_nhanh/`, trong đó có `vram.csv`.

| | v4 nhạy | v4 nhanh |
|---|---|---|
| VRAM cả card lúc chưa chạy | 299 MB | 353 MB |
| VRAM cả card cao nhất | **1452 MB** | **1274 MB** |
| Phần của pipeline (ước, lấy cao nhất trừ lúc chưa chạy) | ~1150 MB | ~920 MB |
| Còn trống (4096 − cao nhất) | **~2640 MB** | **~2820 MB** |
| Bộ nhớ PyTorch giữ (`max_memory_reserved`) | 622 MB | 622 MB |

Còn trống hơn 2,5 GB, xa mốc 500 MB, nên chưa phải gạch ứng viên nào vì thiếu bộ nhớ. Các lần chạy sau, kể cả lúc máy có chương trình khác dùng GPU, đều không vượt 1,9 GB cả card.

| Clip | Người trung bình / tối đa | Nhạy: fps cũ | Nhạy: **fps thật** | Nhanh: fps cũ | Nhanh: **fps thật** |
|---|---|---|---|---|---|
| 01 | 4,5 / 9 | 21,8 | 16,7 | 64,8 | 32,2 |
| 02 | 3,0 / 3 | 25,1 | 18,2 | 68,4 | 36,3 |
| 03 | 0,4 / 1 | 70,6 | 60,2 | 78,6 | 62,4 |
| 04 | 2,0 / 5 | 37,4 | 32,5 | 65,1 | 47,3 |
| 05 | 2,0 / 3 | 33,6 | 27,9 | 69,2 | 45,1 |
| 06 | 3,3 / 6 | 25,2 | 21,9 | 67,4 | 48,1 |
| 07 | 4,0 / 4 | 20,8 | 18,0 | 68,7 | 46,4 |
| 08 | 3,0 / 3 | 25,9 | 22,4 | 70,8 | 50,1 |
| 09 | 7,3 / 9 | 14,7 | 13,0 | 68,6 | 44,6 |
| 10 | 8,7 / 11 | 12,9 | **10,9** | 70,2 | 36,6 |
| 12 | 8,1 / 10 | 12,9 | 10,3 | 72,8 | 30,6 |

Điểm của hai bản giống hệt `out_v4`, tức chạy lại cho đúng kết quả cũ:

- bàn 130/137;
- bản nhạy bắt 5/7, trễ 0,40 s;
- bản nhanh bắt 5/7, trễ 1,17 s.

Ở clip 10, v4 nhạy có fps thật ~10–11, thấp hơn con số 13,6 trong `su_kien.json` cũ.

## T2: lấy lại tốc độ

Mốc đạt: clip 10 ≥ 18 fps thật, giơ tay ≥ 5/7, trễ trung bình ≤ 0,6 s, bàn ≥ 130/137.

| Cấu hình | Clip 10, fps thật (vòng 1; vòng 2) | Giơ tay | Trễ TB | Bàn | Đạt? |
|---|---|---|---|---|---|
| v4 nhạy (trước) | 9,9; 10,2 | 5/7, 0 nhầm | 0,40 s | 130 | — |
| (a) `--det-every 100 --table-every 20 --staff-every 20` | 10,9; 11,4 | 5/7, 0 nhầm | 0,40 s | **129** | Không |
| (b) `--refine-mode ung_vien` (K = 4) + `--det-every 100 --staff-every 20` | 18,6; 19,8 | 5/7, 0 nhầm | **1,20 s** | 130 | Không |
| Thêm: `--refine-mode luot` (K = 4), chưa đổi tham số | 15,7 (một lần) | 5/7, 0 nhầm | 0,42 s | 130 | Không, thiếu fps |
| Thêm: `luot` + `--det-every 100 --staff-every 20` | 18,7; 18,0 | 5/7, 0 nhầm | 0,42 s | 130 (lần chạy kèm `--table-every 20`: 129) | **Có**, sát mốc fps |
| Bản đề xuất: như trên + `--tich-luy` | 18,9; 19,7 (lần chấm 11 clip: 21,0) | 6/7, 0 nhầm | 0,59 s | 130 | **Có** |

Thư mục: `out_t2a`, `out_t2b`, `out_t2b_luot`, `out_t2ab_luot`, `out_de_xuat`, `out_de_xuat_11clip`.

**Vì sao (a) không đủ.**

- Clip 10 không có vùng bàn, nên `--table-every` không ảnh hưởng gì tới clip này.
- Với `--table-model clip`, trạng thái bàn không dùng kết quả của model đồ vật, nên `--det-every 100` không làm sai gì. Nhưng nó cũng chỉ bớt ~3,5 ms mỗi khung.
- Phần tốn nhất vẫn là RTMPose chạy lần lượt cho từng người: 9–11 người, khoảng 8 ms mỗi người.
- `--table-every 20` làm hỏng một mốc "cần dọn" ở clip 01, vì clip này là time-lapse với cửa sổ xác nhận 0,5 s. Ra 129/137, cho trễ 0,5 s còn 133. **Nên giữ `--table-every` như cũ.**

**Vì sao (b) không đạt.** Tiêu chí chọn người dựa trên khung xương YOLO, mà YOLO lại không thấy chính cánh tay đang giơ:

- em áo xanh dương (x ≈ 950) đang giơ tay, nhưng YOLO cho độ nâng cổ tay −2,3 suốt lúc giơ;
- em áo xám (x ≈ 630) có độ nâng quanh −0,5 đến −0,8, nằm sát ngưỡng −0,6;
- nên hai em này không được chọn, mất lợi thế của RTMPose. Trễ ở hai lần đó lên 2,65 s và 2,15 s, giống hệt bản nhanh.

Đây cũng là lý do `gan_vai` từng chỉ bắt 3/7.

**Cách thêm, "theo lượt" (`refine_luot`):**

- Mỗi khung chạy RTMPose cho 4 người lâu chưa được chạy nhất. Người đạt tiêu chí "ứng viên" được cộng 2 lượt ưu tiên.
- Người không tới lượt dùng lại khung xương RTMPose lần trước, dời và co giãn theo box hiện tại. Khung xương cũ chỉ dùng nếu chưa quá 6 khung.
- Ở clip 10, mỗi người được chạy lại khoảng mỗi 2–3 khung (~0,1 s), nên không ai bị bỏ quên như (b).

## T1: báo giơ tay

Mốc đạt: ≥ 6/7, 0 báo nhầm trên 02/08/09, trễ tăng ≤ 0,3 s, tốc độ giảm ≤ 10%.

| Cấu hình | Bắt | Nhầm | Trễ TB (từng lần) | Clip 10, fps thật (vòng 1; vòng 2) | Đạt? |
|---|---|---|---|---|---|
| v4 nhạy (trước) | 5/7 | 0 | 0,40 s (−0,02; 0,32; 0,48; 0,67; 0,56) | 9,9; 10,2 | — |
| T1 đủ (`--cong-mem`) trên v4 nhạy | 6/7 | 0 | 0,64 s (−0,08; 0,28; 0,38; **1,72**; 0,99; 0,52) | 9,5; 8,7 (−4%; −15%) | **Không**: fps, và vẫn sót em mép trái |
| T1 đủ trên bản theo lượt | **5/7** | **1** (clip 12, 3,84 s) | 0,58 s | — | Không |
| T1 rút gọn (`--tich-luy`) trên v4 nhạy | 6/7 | 0 | 0,58 s (−0,08; 0,28; 0,38; 1,72; 0,67; 0,52) | 10,2; 9,1 (không thêm việc, chỉ là dao động) | **Có** |
| T1 rút gọn trên bản theo lượt (bản đề xuất) | 6/7 | 0, trên cả 9 clip âm | 0,59 s | 18,9; 19,7 | **Có** |

Thư mục: `out_t1`, `out_t12_ketop`, `out_t1_tichluy`, `out_de_xuat_11clip`.

**T1 đủ** làm đúng theo danh sách rút gọn:

- **cổng mềm**: hỏi model khi cổ tay lên trên vai, hoặc khuỷu tay lên trên vai, hoặc cổ tay lên trên mũi;
- **đường "chỉ RGB"**: dành cho box chạm mép trái/phải mà không thấy vai, hoặc không tính được độ nâng cổ tay. Hỏi model mỗi 3 khung, ngưỡng 0,6, giữ 1,0 s;
- **giữ hai mức**: tín hiệu "rõ" (luật thấy giơ và model ≥ 0,6) giữ 0,6 s; tín hiệu "mơ hồ" giữ 1,5 s;
- **tích luỹ**: trung bình xác suất model trong 1 s ≥ 0,25, khi cổ tay đã lên trên vai.

Kết quả:

- **Lần bắt thêm là em ngồi xa sau em áo đỏ** (trễ 1,72 s), không phải em mép trái. Nó đến từ phần tích luỹ.
- **Em mép trái vẫn sót.** Trong khung hình chỉ thấy một cánh tay thò vào mép trái (đã xem ảnh khung 20,0 s và 20,8 s). YOLO không tìm ra người đó: lúc tìm ra thì box là người ngồi trước. Model cho xác suất giơ tay chỉ 0,02–0,05, và từ 20,6 s đến 21,3 s không có box nào ở mép trái. Đường "chỉ RGB" không có gì để chạy. **Ca này không sửa bằng luật được.** Phải đặt camera cho bàn nằm trọn trong khung, như KX đã nói.
- **Cổng mềm tốn tốc độ thật.** Thời gian model nhỏ ở clip 10 tăng từ 12–14 ms lên 22–25 ms mỗi khung, vì phải hỏi model cho nhiều người hơn. Tốc độ giảm khoảng 10–15%.
- **Quy tắc "rõ" chặt hơn quy tắc cũ, nên dễ vỡ.** Người mép trái ở clip 12 có luật thấy giơ, nhưng model < 0,6, nên chuyển sang giữ 1,5 s: trễ từ 0,67 s lên 0,99 s. Trên bản theo lượt, người này bị báo muộn 3,84 s, quá hạn chấm, nên tính thành một lần sót cộng một lần nhầm.

**Phát lại không cần GPU** (`thu_gio_tay2.py`, đọc `chi_tiet.json` của `out_t1`, kết quả ở `out_t1/thu_gio_tay2.json`) để xem phần nào có tác dụng:

| Biến thể | Bắt | Nhầm | Trễ TB |
|---|---|---|---|
| v4 | 5/7 | 0 | 0,41 s |
| v4 + cổng mềm, giữ như cũ | 6/7 | 0 | 0,72 s (lần bắt thêm trễ 2,55 s) |
| T1 đủ | 6/7 | 0 | 0,64 s |
| T1 bỏ tích luỹ | **4/7** | 0 | 0,70 s |
| T1 bỏ đường RGB | 6/7 | 0 | 0,64 s (đường RGB không bắt được gì) |
| **v4 + chỉ tích luỹ, cổng cũ** | 6/7 | 0 | **0,58 s** |
| v4 + chỉ tích luỹ, ngưỡng 0,30 | 6/7 | 0 | 0,83 s |
| v4 + chỉ tích luỹ, ngưỡng 0,20 | 6/7 | 0 | 0,50 s |

Kết luận T1: chỉ có phần **tích luỹ bằng chứng yếu** có tác dụng.

- Giữ ngưỡng 0,25 như danh sách rút gọn. Không chọn 0,20, dù 0,20 đẹp hơn trên chính tập test.
- Lưu ý: bản rút gọn được chọn sau khi đã xem điểm 7 lần giơ tay, nên đẹp hơn thực tế một chút.
- Clip stock không có cử chỉ gây nhầm (vuốt tóc, nghe điện thoại), nên "0 báo nhầm" mới chỉ được chứng minh trên 9 clip ăn uống bình thường, tổng 2,3 phút. Cần kiểm lại trên footage tự quay.

## T3: nhân viên theo gallery, nhãn dính, "nhân viên tới bàn"

Script: `thu_gallery_nv.py`. Kết quả: `t3_*.txt` và `t3_*.json`; `tom_t3.py` in bảng gọn.

**Nhãn do mình tự ghi khi xem ảnh có vẽ mã track:**

- **Nhân viên** (`nv_that.json`): clip 06 có track #4 (phục vụ đeo tạp dề). Clip 07 có #6 (phục vụ cầm máy tính tiền) và #8 (bóng áo tạp dề phía sau quầy, 15–19 s; mình đoán là cùng người phục vụ).
- **Vùng bàn** (`zones_t3.json`): vẽ bằng mắt. Clip 07 có camera trượt nhẹ, nên vùng bàn cố định chỉ đúng gần đúng.
- **Lúc nhân viên tới bàn** (`nv_toi.json`): clip 06 lúc 4,5 s, clip 07 lúc 3,5 s.

Tức là **chỉ có 3 track nhân viên và 2 lần tới bàn**. Nhãn quá mỏng để kết luận chắc, chỉ đủ để thấy cách làm có hỏng rõ ràng hay không.

Cách làm theo danh sách rút gọn:

- cắt phần giữa box (60% bề ngang × 70% chiều cao từ trên);
- gallery là ảnh cắt trong 2 s đầu track nhân viên;
- kho khách là ảnh cắt của clip 02 và 09 (khi chấm chính 02 hay 09 thì bỏ clip đó khỏi kho);
- điểm = giống nhất với gallery − giống nhất với kho khách, đổi về 0..1 bằng sigmoid(điểm / 0,03);
- nhãn dính: vào khi > 0,8, ra khi < 0,3, dùng trung bình 1 s;
- chỉ tính track có từ 5 ảnh trở lên.

| Cách | Clip 06 (1 NV, 6 khách) | Clip 07 (2 NV, 3 khách) | 02 + 09 (13 khách) | Đổi nhãn |
|---|---|---|---|---|
| Probe hiện tại (`pst` trung bình 3 s ≥ 0,5) | NV đúng ở cuối track 0/1 (đúng 52% thời gian); khách bị gắn NV 0/6 | NV đúng ở cuối track 0/2 (70% thời gian); khách bị gắn NV 1/3 (khách #1 ở quầy, 91% thời gian) | khách bị gắn NV 2/13 | 9 |
| Gallery, CLIP B/32 | NV 1/1; **khách bị gắn NV 6/6** | NV 2/2; khách 0/3 | khách bị gắn NV 7/13 | 7 |
| Gallery, PE-Core B/16 | NV 1/1; **khách bị gắn NV 4/6** | NV 2/2; khách 1/3 | khách bị gắn NV 6/13 | 4 |
| Gallery + kho khách lấy cả khách cùng clip (có dùng nhãn: cận trên, không làm được ngoài đời), PE-Core B/16 | NV ở cuối track bị ghi thành khách (đúng 74% thời gian); khách 0/6 | NV 2/2; khách 0/3 | khách bị gắn NV 6/13 | 2 |
| Như trên, gallery lấy 2 s **cuối** track (giả lập đăng ký trước ca), PE-Core B/16 | NV đúng chỉ 5% thời gian | NV 2/2; khách 1/3 | 6/13 | 1 |

"Nhân viên tới bàn" (cần ≤ 2 s và không phát cho khách):

| Cách | Clip 06 | Clip 07 |
|---|---|---|
| Probe | trễ 9,0 s | trễ 1,6 s; thêm 1 lần phát cho khách |
| Gallery, CLIP B/32 | trễ 2,2 s; thêm 6 lần phát cho khách | trễ 1,6 s; không phát cho khách |
| Gallery, PE-Core B/16 | trễ 2,2 s; thêm 4 lần phát cho khách | trễ 1,6 s; thêm 1 lần phát cho khách |
| Gallery + kho cùng clip, PE-Core B/16 | trễ 2,2 s; không phát cho khách | trễ 1,6 s; không phát cho khách |

**Kết luận T3: không đạt.**

- Bản theo danh sách rút gọn gắn nhãn nhân viên cho gần hết khách ngồi cùng phòng với nhân viên.
- Lý do: ảnh cắt giống nhau chủ yếu vì cùng cảnh, cùng ánh sáng, chứ không vì quần áo. Gallery và khách ở clip 06 cùng một phòng, còn kho khách lấy từ quán khác. Độ giống trung bình với gallery là 0,66–0,81, với kho khách là 0,58–0,78, hai khoảng chồng lên nhau.
- Kho khách cùng camera làm số đẹp hơn hẳn, nhưng ngoài đời không có nhãn khách, nên đây chỉ là cận trên. Kể cả vậy, nhân viên ở clip 06 vẫn bị ghi thành khách ở cuối track.
- Probe hiện tại cũng kém: nhân viên đúng 52–70% thời gian, đổi nhãn 9 lần, và gắn nhân viên cho một khách đứng ở quầy clip 07.
- Cần dữ liệu thật mới làm tiếp được: nhân viên quán thật mặc đồng phục, đăng ký ở chính camera đó, và nhiều ca hơn 3 track.
- Hướng nên thử khi có footage: kho khách tự động từ những người ngồi yên ở bàn lâu (gần như chắc là khách), cùng camera, cùng ánh sáng.

## Phần sửa đề xuất cho `easyfnb_test.py` (chưa áp dụng)

Chỉ gồm những phần đạt: RTMPose theo lượt (T2) và tích luỹ bằng chứng yếu (T1 rút gọn). Mặc định không đổi gì. Chỉ có tác dụng khi bật `--refine-mode luot` hoặc `--tich-luy`. Cùng nội dung có trong file `thu_nghiem/gpu/de_xuat.diff`.

```diff
--- a/vision-test/easyfnb_test.py
+++ b/vision-test/easyfnb_test.py
@@ -213,6 +213,42 @@
     return kps, kcs
 
 
+def refine_luot(rtm, frame, boxes, ids, kps, kcs, cache, fi, k_max=4, max_age=6):
+    """RTMPose theo lượt: mỗi khung chỉ chạy RTMPose cho tối đa K người. Người lâu chưa được chạy nhất đi trước;
+    người nhỏ (box cao < 150 px), thiếu vai/cổ tay, hoặc cổ tay đã lên gần vai được cộng 2 lượt ưu tiên.
+    Người không tới lượt dùng lại khung xương RTMPose lần trước (dời, co giãn theo box hiện tại) nếu chưa quá
+    `max_age` khung; không thì giữ khung xương YOLO."""
+    if rtm is None or not len(boxes):
+        return kps, kcs
+    pri = []
+    for k in range(len(boxes)):
+        tid = int(ids[k])
+        age = fi - cache[tid][0] if tid in cache else 99
+        hl = hand_lift(kps[k], kcs[k], boxes[k])
+        crit = (boxes[k][3] - boxes[k][1]) < 150 or hl is None or hl > -0.6
+        pri.append((age + (2 if crit else 0), k))
+    sel = [k for _, k in sorted(pri, reverse=True)[:k_max]]
+    kps, kcs = kps.copy(), kcs.copy()
+    if sel:
+        kp2, sc2 = rtm(frame, bboxes=[list(map(float, boxes[k])) for k in sel])
+        for j, k in enumerate(sel):
+            kps[k] = kp2[j]
+            kcs[k] = np.clip(sc2[j], 0, 1)
+            cache[int(ids[k])] = (fi, boxes[k].copy(), kps[k].copy(), kcs[k].copy())
+    for k in range(len(boxes)):
+        tid = int(ids[k])
+        if k in sel or tid not in cache or fi - cache[tid][0] > max_age:
+            continue
+        _, b0, kp0, kc0 = cache[tid]
+        b = boxes[k]
+        s = (b[3] - b[1]) / max(1.0, b0[3] - b0[1])
+        c0 = np.array([(b0[0] + b0[2]) / 2, (b0[1] + b0[3]) / 2])
+        c1 = np.array([(b[0] + b[2]) / 2, (b[1] + b[3]) / 2])
+        kps[k] = (kp0 - c0) * s + c1
+        kcs[k] = kc0
+    return kps, kcs
+
+
 def nearest_table(tables, pt, scale):
     """Bàn gần điểm pt nhất, nếu cách mép bàn không quá `scale` pixel."""
     best, bd = None, -1e9
@@ -319,6 +355,8 @@
     fp16 = dict(half=True) if args.half else {}  # chỉ truyền khi bật, Ultralytics mới báo half là tham số cũ
 
     hist = {}        # track id -> deque[(t, điểm giơ tay, tâm, chiều cao)]
+    weak_hist = {}   # track id -> deque[(t, xác suất giơ tay khi cổ tay đã lên trên vai, không thì 0)]
+    rtm_cache = {}   # --refine-mode luot: track id -> (khung, box, khung xương RTMPose lần trước)
     last_call = {}   # track id -> lúc báo gọi gần nhất
     events, banner = [], []
     ms_pose, ms_det, people_per_frame = [], [], []
@@ -363,7 +401,10 @@
         kps = r.keypoints.xy.cpu().numpy() if r.keypoints is not None else np.zeros((len(boxes), 17, 2))
         kcs = r.keypoints.conf.cpu().numpy() if r.keypoints is not None and r.keypoints.conf is not None \
             else np.ones((len(boxes), 17))
-        kps, kcs = refine_pose(rtm, frame, boxes, kps, kcs, args.refine_mode)
+        if args.refine_mode == 'luot':
+            kps, kcs = refine_luot(rtm, frame, boxes, ids, kps, kcs, rtm_cache, i, args.refine_k)
+        else:
+            kps, kcs = refine_pose(rtm, frame, boxes, kps, kcs, args.refine_mode)
         dt_pose = (time.perf_counter() - t0) * 1000
 
         new_items = None
@@ -429,6 +470,16 @@
             staff = bool(sq) and np.mean([v for _, v in sq]) >= 0.5
             recent = [u for tt, u, *_ in q if tt >= t - args.hand_s]
             calling = (not staff and q[-1][0] - q[0][0] >= 0.8 * args.hand_s and np.mean(recent) >= 0.7)
+            if args.tich_luy and hand_mode == 'hop':
+                # tích luỹ bằng chứng yếu: model chỉ hơi tin (trung bình 1 s >= weak-th) nhưng cổ tay vẫn trên vai
+                nang = hand_lift(kp, kc, b)
+                wq = weak_hist.setdefault(tid, deque())
+                wq.append((t, (ph or 0) if (nang is not None and nang > 0.3) else 0.0))
+                while wq and wq[0][0] < t - 1.0:
+                    wq.popleft()
+                if (not calling and not staff and nang is not None and nang > 0.3 and wq[-1][0] - wq[0][0] >= 0.8
+                        and np.mean([v for _, v in wq]) >= args.weak_th):
+                    calling = True
             tb = nearest_table(tables, anchor, 0.45 * h) if tables else None
             persons.append(dict(id=tid, box=b, kp=kp, kc=kc, walking=walking, staff=staff,
                                 calling=calling, score=score if hand_mode == 'luat' else (ph or 0), table=tb))
@@ -630,9 +681,15 @@
     ap.add_argument('--no-video', action='store_true', help='không ghi video kết quả (chỉ cần chấm điểm)')
     ap.add_argument('--pose-refine', choices=list(RTMPOSE), default=None,
                     help='chạy thêm RTMPose trên từng người để có khung xương tốt hơn')
-    ap.add_argument('--refine-mode', choices=['tat_ca', 'yeu', 'gan_vai'], default='tat_ca',
+    ap.add_argument('--refine-mode', choices=['tat_ca', 'yeu', 'gan_vai', 'luot'], default='tat_ca',
                     help='tat_ca: mọi người; yeu: chỉ người YOLO không thấy rõ vai/cổ tay; '
-                         'gan_vai: thêm người có cổ tay đã lên gần vai')
+                         'gan_vai: thêm người có cổ tay đã lên gần vai; '
+                         'luot: tối đa --refine-k người mỗi khung theo lượt, người khác dùng lại khung xương lần trước')
+    ap.add_argument('--refine-k', type=int, default=4, help='luot: số người chạy RTMPose mỗi khung')
+    ap.add_argument('--tich-luy', action='store_true',
+                    help='thêm đường báo giơ tay khi model chỉ hơi tin nhưng kéo dài: trung bình 1 s >= --weak-th '
+                         'với cổ tay đã lên trên vai')
+    ap.add_argument('--weak-th', type=float, default=0.25, help='ngưỡng của --tich-luy')
     ap.add_argument('--tracker', default='bytetrack.yaml',
                     help='bộ bám người: bytetrack.yaml, botsort.yaml, tracktrack.yaml... hoặc file .yaml trong models/')
     ap.add_argument('--may-chu', default=None,
```

Muốn bản demo dùng cấu hình mới thì sửa thêm dòng cuối của `chay_camera.bat`, giữ nguyên `--table-every`:

```diff
-  --pose-refine rtmpose-m --refine-mode tat_ca %REST%
+  --pose-refine rtmpose-m --refine-mode luot --det-every 100 --staff-every 20 --tich-luy %REST%
```

Lưu ý khi áp dụng:

- `--staff-every 20` nghĩa là xét nhân viên/khách khoảng 1,2 lần mỗi giây, trong cửa sổ trung bình 3 s. Điểm không đổi trên các clip này, nhưng nhãn nhân viên sẽ ổn định chậm hơn lúc người mới xuất hiện.
- `--det-every 100` chỉ an toàn khi bàn dùng `--table-model clip`, vì trạng thái bàn khi đó không dùng model đồ vật. Model đồ vật chỉ còn để vẽ khung.

## Chạy lại

Chạy trong `vision-test/`, bằng Git Bash, mỗi lần một lệnh.

```bash
thu_nghiem/gpu/run_gpu.sh out_x clips/ --no-video --dump --luu-khung-xuong \
  --hand-model giotay_pe_b16.pt --hand-th 0.35 --staff-model nhanvien_clip_v1.pt \
  --table-model clip --clip-backbone pe_core_s16 \
  --pose-models yolo26n-pose_544x960_fp16.engine --det-models yolo26s_736x1280_fp16.engine \
  --pose-refine rtmpose-m --refine-mode luot --det-every 100 --staff-every 20 --tich-luy
python danh_gia/cham_diem.py thu_nghiem/gpu/out_x
python danh_gia/cham_su_kien.py thu_nghiem/gpu/out_x --dap-an-cu
python thu_nghiem/gpu/thu_gio_tay2.py thu_nghiem/gpu/out_t1          # phát lại T1, không cần GPU
thu_nghiem/gpu/bench_all.sh                                          # so fps xen kẽ trên clip 10
python thu_nghiem/gpu/thu_gallery_nv.py thu_nghiem/gpu/out_b0_nhay --nhan thu_nghiem/gpu/nv_that.json \
  --vung thu_nghiem/gpu/zones_t3.json --toi thu_nghiem/gpu/nv_toi.json [--kho-cung] [--gallery-cuoi]
```

`run_gpu.sh` tự lấy mẫu `nvidia-smi` mỗi giây vào `<out>/vram.csv`. `xem_track.py` vẽ ảnh tờ có mã track, để người xem ghi nhãn nhân viên.
