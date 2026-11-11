# Quay dữ liệu giơ tay gọi phục vụ

Dữ liệu này dùng cho hai việc: **đo** bản hiện tại (bắt bao nhiêu lần gọi, báo nhầm mỗi giờ, trễ bao lâu) và **train** lớp theo thời gian (GRU). Cùng một lần quay phục vụ cả hai.

## Mục tiêu

| | Tối thiểu | Vì sao |
|---|---|---|
| Số người diễn | 5 (2 bạn trong nhóm + 3 bạn khác), tốt hơn 6–8 | Chỉ 2 người thì model học thuộc hai người đó, không học cử chỉ |
| Lần giơ tay gọi | 150 | Bộ cũ chỉ có 7 lần: bắt 5/7 nghĩa là tỉ lệ thật ở đâu đó từ 36% đến 92% |
| Cử chỉ dễ nhầm | 300 | Vuốt tóc, gãi đầu, uống nước, chỉ tay, vươn vai, nghe điện thoại... |
| Ăn uống bình thường | 1 giờ | Để đếm báo nhầm mỗi giờ. Không báo nhầm lần nào trong 1 giờ chỉ chứng minh được "dưới 3 lần/giờ" |

Khoảng 2 giờ quay cho cả nhóm: 8 phiên có lệnh × 5 phút và 4 phiên ăn uống bình thường × 15 phút.

## Trước khi quay

- **Mọi người trong khung hình phải đồng ý được quay.** Video có mặt người. Không quay khách lạ, không đưa video lên mạng.
- **Camera đặt cao, chúc xuống như camera trần:** nóc tủ, giá treo, hoặc chân máy kéo cao hết cỡ, cao ít nhất 2,2 m. Nếu quán có camera thật thì dùng luôn camera đó.
  - Quay ngang, 720p hoặc 1080p, 25–30 khung/giây.
  - Khoá lấy nét và phơi sáng nếu điện thoại cho phép.
  - Không zoom, không chạm vào camera trong lúc quay.
- **Chỗ ngồi:** 3–6 ghế có người, ở 2–3 bàn.
  - Ít nhất một ghế **gần** camera, một ghế **xa** (người trong hình nhỏ), một ghế **sát mép** khung hình (người bị cắt một phần).
  - Đó là ba loại ghế khi khai báo: `gan`, `xa`, `mep`.
- **Bày ly nước, chén đĩa thật trên bàn**, để có cử chỉ uống và để bàn che phần thân dưới như ở quán.
- **Laptop chạy chương trình nhắc lệnh** đặt ngoài khung hình, chỗ mọi người nhìn thấy. Bật loa để nghe tiếng bíp.
- Nếu được, một người đóng vai **phục vụ** (tạp dề hoặc áo đồng phục) đi lại, bưng khay, ghi món trong vài phiên.

## Phiên có lệnh (5 phút)

1. Đặt tên phiên `<ngày tháng>_p<số>`, ví dụ `0711_p01`.
2. Trên laptop, khai báo ghế theo dạng `mã=tên:loại ghế`:

   ```
   python quay/nhac_lenh.py --phien 0711_p01 --ghe G1=Tien:gan G2=Lan:xa G3=Minh:mep
   ```

3. Bấm quay trên camera, rồi bấm SPACE trên laptop. Màn hình đếm 3-2-1 rồi hiện "VỖ TAY": **mọi người vỗ tay một cái trước ngực**. Cái vỗ tay này để khớp giờ của lịch lệnh với video.
4. **Khi màn hình gọi đúng ghế mình, làm cử chỉ đó** một cách tự nhiên, như đang ở quán. Giữa các lệnh: ăn, nói chuyện, xem điện thoại bình thường.
5. Hết giờ, dừng quay. Chép video vào `du_lieu_quay/0711_p01/0711_p01.mp4`. Chương trình đã tạo sẵn thư mục này, cùng `lich.json` và `phien.json`.
6. **Giữa các phiên, đổi chỗ ngồi** (người ghế gần sang ghế xa, ghế mép...), đổi tay hay dùng, cởi hoặc mặc áo khoác.

Mỗi phiên có khoảng 58 lệnh, trong đó khoảng 20 lệnh gọi phục vụ. Lệnh bốc ngẫu nhiên nên không ai đoán trước được.

Chỉ muốn xem lịch (để một người đọc to thay cho laptop): thêm `--chi-in`.

## Phiên ăn uống bình thường (15 phút)

```
python quay/nhac_lenh.py --phien 0711_bt01 --ghe G1=Tien:gan G2=Lan:xa G3=Minh:mep --binh-thuong --phut 15
```

Không có lệnh. Mọi người ăn uống, nói chuyện, vuốt tóc, uống nước tự nhiên, **không gọi phục vụ**. Lỡ có người gọi thì nhớ giờ để gán nhãn.

## Gán nhãn

```
python quay/gan_nhan.py du_lieu_quay/0711_p01
```

1. Tua tới lúc vỗ tay (thường trong 30 giây đầu), bấm **C**. Máy biến mọi lệnh trong lịch thành sự kiện nháp, đặt sẵn đúng ghế, đúng loại cử chỉ.
2. Bấm **]** để nhảy tới sự kiện tiếp theo, rồi xem người ở ghế đó.
   - **A** tại khung tay bắt đầu nhấc, **S** tại khung tay lên cao nhất, **D** tại khung tay hạ xong. Dùng **,** **.** để lùi/tiến từng khung, **J** **L** từng giây.
   - Lần đầu gặp mỗi ghế: **kéo chuột vẽ khung** quanh người đó. Các sự kiện sau cùng ghế tự dùng lại khung này.
   - **Enter** để xác nhận. **X** nếu người đó không làm theo lệnh.
   - Người đó làm sai cử chỉ: **K** để đổi loại cho đúng việc họ đã làm.
3. Có cử chỉ ngoài lịch (ai đó tự gọi, tự vuốt tóc): **N** tạo sự kiện mới, **K** đổi loại, **G** đổi ghế.

Độ chính xác cần có:

- **Giơ tay gọi:** S phải đúng khung tay lên đỉnh, vì độ trễ được đo từ đó.
- **Cử chỉ dễ nhầm:** chỉ cần A và D bao trọn cử chỉ.

Khoảng 10–15 giây cho mỗi sự kiện, tức 10–15 phút cho mỗi phiên 5 phút.

**Phiên ăn uống bình thường:** chỉ cần bấm C lúc vỗ tay rồi Q. Nếu có ai lỡ gọi thật thì thêm sự kiện bằng N.

Nhãn lưu tự động vào `nhan.json` mỗi lần xác nhận. Mở lại thì tiếp tục từ chỗ cũ.

## Chạy và chấm

```
python easyfnb_test.py du_lieu_quay --out out_quay --no-video --luu-khung-xuong ^
  --hand-model giotay_pe_b16.pt --hand-th 0.35 --staff-model nhanvien_clip_v1.pt ^
  --table-model clip --clip-backbone pe_core_s16 ^
  --pose-models yolo26n-pose_544x960_fp16.engine --det-models yolo26s_736x1280_fp16.engine
python danh_gia/cham_su_kien.py out_quay --ten v4_nhanh
```

Thêm `--pose-refine rtmpose-m --refine-mode tat_ca` cho bản nhạy.

`--luu-khung-xuong` ghi `khung_xuong.npz` cho từng phiên: 17 điểm khung xương của từng người ở từng khung. Đây là dữ liệu để train GRU.

Bộ chấm in ra:

- **Bắt được bao nhiêu lần gọi**, kèm khoảng tin cậy 95%. Chia theo loại gọi, loại ghế (gần, xa, mép), cỡ người trong hình và từng người diễn.
- **Trễ** từ lúc tay lên đỉnh tới lúc máy báo: trung bình, trung vị, và mức mà 90% số lần nằm dưới.
- **Báo nhầm mỗi giờ.** Riêng phiên ăn uống bình thường được đếm tách ra. Bộ chấm cũng ghi mỗi cử chỉ dễ nhầm bị báo bao nhiêu lần trên số lần được làm, ví dụ "vuot_toc 2/40".
- **Báo trùng:** một lần gọi mà máy báo nhiều lần.

Chấm lại bộ 11 clip cũ theo cùng cách:

```
python danh_gia/cham_su_kien.py out_v4 --dap-an-cu
```

## Luật quyết định cho demo

GRU (hoặc ST-GCN++) chỉ thay luật hiện tại khi, trên người và ghế mà nó chưa thấy lúc train:

- báo nhầm do cử chỉ dễ nhầm giảm;
- không bỏ sót thêm lần gọi nào;
- không trễ hơn.

Nếu không đạt, demo chạy bản hiện tại. GRU khi đó chạy song song, chỉ ghi lại kết quả, và được trình bày là lớp đang học thêm.
