# T5. Làm mờ mặt khách từ khung xương (keypoint 0–4) trên ảnh rời máy

Ngày chạy: 05/11/2026. Chỉ dùng CPU, không đụng GPU. Chưa sửa code pipeline; bản vá đề xuất ở cuối file.

## Kết luận ngắn

- **Đạt cả ba tiêu chí** trên mẫu 101 khung (7 clip), với một điểm yếu rõ: người ở xa mà model pose bỏ sót (độ tin cậy dưới 0.3) thì không có khung xương, nên mặt không bị che.

| Tiêu chí | Ngưỡng | Kết quả | Đạt? |
|---|---|---|---|
| Mặt thấy được bị che kín | ≥ 90% | **~95%** (407/~429). Clip quán ăn 01, 06, 07, 08, 09: ~99% (234/236). Clip lớp học 10: ~81% (87/107) | Đạt (clip 10 thì không) |
| Tay giơ bị làm mờ | ≤ 5% | **1/89 = 1.1%** (lần giơ tay có nhãn × khung mẫu) | Đạt |
| Thời gian mỗi khung, CPU, ≤ 10 người | ≤ 2 ms | **0.8 ms** trung bình, p95 1.1 ms (làm thẳng trên ảnh đã copy để vẽ). Nếu tự copy ảnh 1280×720: trung bình 1.35 ms, p95 1.8 ms | Đạt |

- Ảnh hưởng tới người dùng: sẽ không ai thấy rõ mặt khách trên web, trong crop sự kiện hay trong ảnh gửi Gemini, còn tay giơ gọi phục vụ vẫn rõ. Mất ~1 ms CPU mỗi ảnh gửi đi, không thêm model, không thêm VRAM.
- Lỗ hổng còn lại và cách vá: chỗ hở chủ yếu là **người bị model pose bỏ sót** (19/22 ca là một bé ngồi xa trong clip 10). Chạy lại pose với ngưỡng 0.1 rồi làm mờ thêm những người này thì che được bé đó ở gần như mọi khung, tay giơ vẫn giữ nguyên (`anh/soi_27.jpg`). Bản vá cho phép bật việc này bằng `--mo-mat-conf 0.1`. Cách này tốn thêm một lần chạy pose trên mỗi ảnh gửi đi (khoảng 4 lần/giây). Cần đo VRAM ở Bước 0 trước khi bật mặc định.
- Chọn **pixel hoá** (khoảng 5 ô ngang đầu), không dùng Gaussian. Gaussian với kernel cỡ mặt mất 22 ms/khung, chậm gấp ~25 lần mà che cũng không kín hơn.
- YuNet: **chưa thử**. Phải tải file model (~340 KB, OpenCV Zoo) mà chưa được người dùng duyệt tải. Ngoài ra chỗ hở hiện nay là người không có khung xương, mặt chỉ 15–20 px, nhỏ hơn cỡ YuNet bắt tốt. Ngưỡng pose 0.1 xử lý được ca này mà không cần thêm model.

## Dữ liệu và cách đo

- **Không có khung xương lưu sẵn.** `out_v4/*/chi_tiet.json` chỉ có box, còn `out_b0` (Bước 0) chưa chạy. Vì vậy đã chạy `yolo26n-pose.pt` trên **CPU**, imgsz 960, conf 0.3 (giống pipeline) trên 101 khung (`lay_khung_xuong.py`):
  - clip 01 (14 khung), 06 (10), 07 (8), 08 (14), 09 (14), rải đều cả clip;
  - clip 10: 4 khung trước lúc giơ tay, rồi 16.5–21.5 s cứ 0.25 s một khung (21 khung);
  - clip 12: 2.0–3.3 s cứ 0.1 s một khung, cộng 3 khung ngoài khoảng đó (17 khung).
  - Tổng cộng 609 lượt người, tối đa 10 người/khung.
- **Mặt bị che:** xem bằng mắt các ảnh trong `anh/`:
  - `luoi_dau_00..12.jpg`: 609 ô, mỗi ô gồm đầu trước làm mờ (có vẽ elip) và sau làm mờ;
  - `sot_0..5.jpg`: 34 khung nguyên, đã làm mờ;
  - các ảnh phóng to `soi_*.jpg`.
  - "Mặt thấy được" ở người model bắt được tính theo khung xương: mũi hoặc mắt có độ tin cậy ≥ 0.5, được 407 người. Sau lần sửa cuối, xem lại không thấy ca nào trong số này còn hở mặt nhận ra được.
  - Người bị bỏ sót được tìm bằng cách chạy lại pose với conf 0.1 (`nguoi_bi_sot.py`), lấy người mới có điểm đầu, rồi xem từng ô (`anh/nguoi_bi_sot_a.jpg`, `_b.jpg`). Đếm được khoảng 22 mặt nhận ra được bị hở:
    - bé tóc búi ngồi xa (clip 10, chính là em "ngồi xa sau em áo đỏ" đang giơ tay): 19 khung;
    - cô giáo ở xa (10_0300): 1;
    - người ngồi sau ở clip 06 (06_0233): 1;
    - cô gái tóc đen ở clip 09 (09_0203): 1.
  - Số này do một người đếm bằng mắt nên chỉ là ước lượng, sai lệch khoảng ±1–2%.
- **Tay giơ:** có hai cách đo.
  - (a) Theo nhãn trong `danh_gia/dap_an.json`: 7 lần giơ tay ở clip 10 và 12, nhân với số khung mẫu nằm trong khoảng giơ tay, được 89 cặp. Mỗi cặp xem bằng mắt ở `anh/nhan_10_0..4.jpg` và `anh/nhan_12_0..1.jpg` (trước | sau). Có 1 cặp bàn tay bị mờ (12_0052, xem phần lỗi).
  - (b) Tự động trong `danh_gia.py`: lấy 56 cổ tay cao hơn vai rõ rệt và đo tỉ lệ vùng bàn tay nằm trong mặt nạ mờ. Có 2 ca trên 10%: một là 12_0052 ở trên; ca còn lại (10_0592) do khung xương đặt nhầm điểm cổ tay lên đỉnh đầu, còn bàn tay thật trên cao vẫn rõ (`anh/soi_8.jpg`).
- **Tốc độ:** mỗi khung chạy `blur_faces` 20 lần, lấy trung bình, trên CPU của máy này (đang có tải khác nên số dao động 0.6–0.95 ms giữa các lần chạy). Kết quả ghi trong `ket_qua_pixel.json`. Nếu tính thêm người conf 0.1–0.3 (trung bình 8.6, tối đa 19 người/khung) thì được 1.0 ms trung bình, p95 1.5 ms.

## Cách làm (`lam_mo_mat.py`, hàm `blur_faces`)

1. **Cỡ đầu `r`** lấy số **lớn nhất** trong các ước lượng có được:
   - 0.75 × khoảng cách hai tai;
   - 1.6 × khoảng cách hai mắt;
   - 0.6 × khoảng cách mũi–tai (mặt nghiêng);
   - 0.32 × bề ngang vai;
   - 0.08 × chiều cao box.

   Sau đó kẹp lại trong khoảng 0.05–0.25 × chiều cao box, và không quá 0.6 × bề ngang box.
2. **Tâm elip** đặt ở trung bình các điểm đầu có độ tin cậy ≥ 0.3:
   - thấy mặt thì dời xuống 0.25 r;
   - cúi đầu (mũi thấp hơn tai) thì dời thêm xuống.

   Elip có kích thước tối thiểu 1.2 r × 1.6 r và luôn **chứa mọi điểm đầu cộng thêm lề**.
3. **Dự phòng khi không thấy điểm đầu:**
   - thấy vai: đặt đầu phía trên vai;
   - box chỉ có chân (người ngồi sau bàn, model chỉ thấy chân dưới gầm bàn): bỏ qua, vì đầu đã bị che;
   - thấy tay mà box chạm mép ảnh: bỏ qua, vì đầu nằm ngoài khung và che phần trên box sẽ làm mờ đúng cánh tay đang giơ;
   - còn lại: che phần trên box.
4. **Chừa tay giơ:** cổ tay cao hơn đầu thì khoét khỏi mặt nạ một dải từ cổ tay kéo dài theo cẳng tay thêm 1 r, rộng 0.9 r. Dải này chỉ khoét elip của chính người giơ, hoặc elip đoán mò. Nếu bàn tay che ngang mặt một người khác mà mặt đó thấy rõ điểm đầu thì vẫn che mặt: ưu tiên riêng tư hơn bàn tay.
5. **Làm mờ:** pixel hoá riêng từng vùng đầu (thu nhỏ rồi phóng lại), dán theo mặt nạ elip. Chỉ xử lý ROI quanh đầu nên rất nhanh.

### Các vòng sửa (đều thấy trên ảnh)

| Bản | Vấn đề thấy được | Sửa |
|---|---|---|
| v1 (elip quanh trung bình điểm đầu) | Mặt nghiêng và người cúi đầu bị hở cằm, mũi (07 ông áo xanh, 12 cậu đeo kính chống cằm; `soi_16.jpg` là ảnh sau khi sửa) | Dời tâm xuống; elip luôn chứa mọi điểm đầu; thêm cỡ đầu theo mũi–tai |
| v2 | Tay giơ của bé hàng trước khoét mất một góc mặt cô giáo phía sau (`soi_14.jpg`) | Tay chỉ khoét elip của chính người giơ; dải tay hẹp lại |
| v3 | Clip 09: 28 "người" là chân dưới gầm bàn, dự phòng 20% trên box làm mờ mép bàn có chén dĩa. Clip 10: bé ở mép trái (đầu ngoài khung) bị mờ cả cánh tay đang giơ (`soi_11.jpg`) | Bỏ qua hai trường hợp này (bước 3) |

## Ví dụ lỗi còn lại

1. **Người bị model pose bỏ sót thì không bị che.** Bé tóc búi ngồi xa ở clip 10 có độ tin cậy 0.10–0.25 ở hầu hết các khung, mặt chỉ khoảng 15–20 px. Ảnh: `anh/nguoi_bi_sot_a.jpg` (các ô "10_05xx") và `anh/soi_27.jpg` (trái: hiện tại; phải: thêm người conf ≥ 0.1, mặt đã bị che, tay vẫn rõ). Các ca lẻ khác: người ngồi sau ở 06_0233, cô gái ở 09_0203, cô giáo ở 10_0300.
2. **Bàn tay chạm ngang mặt người khác thì bị mờ theo.** 12_0052: người mép trái vừa bắt đầu giơ tay, bàn tay ngang mặt cậu ngồi cạnh (`anh/soi_24.jpg`, ô đầu dòng 2). Đây là lựa chọn có chủ ý: chỉ một khung, các khung sau tay lên cao và rõ.
3. **Điểm cổ tay đặt nhầm lên đầu** (10_0592, em áo xanh dương). Phần chừa tay nằm sai chỗ, nhưng bàn tay thật cao hơn hẳn đầu nên vẫn không bị mờ (`anh/soi_8.jpg`).
4. **Mặt rất nhỏ ở góc cao** (clip 01, người ở cuối quán): elip đúng chỗ, nhưng pixel hoá 5 ô trên mặt 12 px gần như không đổi gì. Ở cỡ đó mặt vốn đã không nhận ra được.
5. **Không thử trên Gemini** (chưa có key). Phần A/B "crop gốc và crop mờ" vẫn để chờ. Gemini cần tay, tư thế, bàn; không cần mặt.

## Bản vá đề xuất (chưa áp dụng)

`gui_may_chu.py` **không cần sửa**: lớp `MayChu` không có khung xương, nên mọi ảnh phải được làm mờ trước khi gọi `mc.event`, `mc.frame_live` và `mc.frame_raw`. Phần sửa nằm trong `fnb_common.py` và `easyfnb_test.py`. Ảnh sự kiện lưu tại chỗ (`anh_su_kien/`) vẫn để nguyên để còn soát lỗi. Video kết quả và khung live thì vẽ trên ảnh đã làm mờ, nên video demo cũng không lộ mặt.

**1. `fnb_common.py`:** chép nguyên phần thân của `thu_nghiem/lam_mo_mat/lam_mo_mat.py` vào cuối file (từ dòng `NOSE, LEYE, ...` tới hết `blur_faces`; `cv2` và `numpy` đã được import sẵn).

**2. `easyfnb_test.py`:**

```diff
@@ import
-from fnb_common import pad_box, rect_size, square
+from fnb_common import blur_faces, pad_box, rect_size, square

@@ def run_clip(...): sau dòng `fp16 = dict(half=True) if args.half else {}`
     fp16 = dict(half=True) if args.half else {}  # chỉ truyền khi bật, Ultralytics mới báo half là tham số cũ
+    # làm mờ mặt trên mọi ảnh rời máy (crop sự kiện, khung live, khung gốc) và trên video kết quả
+    mo_mat = not args.khong_mo_mat
+    anon_pose = None
+    if mo_mat and mc is not None and args.mo_mat_conf < 0.3:
+        # bản pose thứ hai, chỉ để tìm thêm người mờ/xa (conf thấp) trên ảnh gửi đi; không đụng bộ bám người
+        anon_pose, _ = load_model(args.pose_models)

@@ trong vòng lặp, ngay sau `kps, kcs = refine_pose(...)` và `dt_pose = ...`
         dt_pose = (time.perf_counter() - t0) * 1000
+        anon = None  # khung đã làm mờ mặt: chỉ tính (một lần) khi có ảnh cần gửi đi hoặc cần vẽ
+
+        def an_danh():
+            nonlocal anon
+            if anon is None:
+                if not mo_mat:
+                    anon = frame
+                else:
+                    kp2, kc2, bx2 = kps, kcs, boxes
+                    if anon_pose is not None:
+                        q = anon_pose.predict(frame, classes=[0], conf=args.mo_mat_conf, imgsz=pose_sz,
+                                              device=args.device, verbose=False, **fp16)[0]
+                        if q.keypoints is not None and q.keypoints.conf is not None and len(q.boxes):
+                            kp2 = np.concatenate([kps, q.keypoints.xy.cpu().numpy()])
+                            kc2 = np.concatenate([kcs, q.keypoints.conf.cpu().numpy()])
+                            bx2 = np.concatenate([boxes, q.boxes.xyxy.cpu().numpy()])
+                    anon = blur_faces(frame, kp2, kc2, bx2)
+            return anon

@@ sự kiện gọi phục vụ
                 if mc is not None:
-                    mc.event(events[-1], events[-1]['_crop'])
+                    mc.event(events[-1], crop(an_danh(), x1, y1, x2, y2, 0.15 * h))

@@ sự kiện bàn
                 if mc is not None:
-                    mc.event(events[-1], events[-1]['_crop'])
+                    mc.event(events[-1], crop(an_danh(), x, y, x + w_, y + h_, 80))

@@ khung gốc gửi lên web để vẽ vùng bàn
             if now_w - last_raw >= 30:  # ảnh gốc không vẽ gì, để vẽ vùng bàn trên web
-                mc.frame_raw(frame, source=src_name)
+                mc.frame_raw(an_danh(), source=src_name)

@@ vẽ
         # --- vẽ
-        vis = frame.copy()
+        vis = an_danh().copy()

@@ def main(): thêm tham số, cạnh --may-chu
+    ap.add_argument('--khong-mo-mat', action='store_true',
+                    help='không làm mờ mặt khách trên ảnh gửi máy chủ / video kết quả (chỉ để soát lỗi)')
+    ap.add_argument('--mo-mat-conf', type=float, default=0.3,
+                    help='ngưỡng người để làm mờ mặt. 0.3: chỉ người đang bám (không tốn thêm gì); '
+                         '0.1: chạy thêm pose trên mỗi ảnh gửi đi để che cả người ở xa (cần đo VRAM trước)')
```

Ghi chú cho bản vá:

- `an_danh()` dùng `nonlocal anon`. Việc này hợp lệ vì `anon` là biến cục bộ của `run_clip`. Hàm chỉ được gọi trong cùng vòng lặp với `frame`, `kps`, `boxes` của khung đó.
- Chi phí khi `--mo-mat-conf 0.3` (mặc định): khoảng 1 ms CPU cho mỗi khung có gửi ảnh hoặc ghi video. Không có model hay VRAM mới. Khi chỉ chấm điểm (`--no-video`, không có máy chủ) thì không chạy gì cả.
- Chi phí khi `--mo-mat-conf 0.1`: mỗi ảnh gửi đi chạy thêm một lần pose. Theo `danh_gia/toc_do.json`, TensorRT FP16 mất 7.5 ms một lần, tức khoảng 30 ms GPU mỗi giây ở 4 khung live/giây. Ngoài ra phải nạp engine thứ hai, VRAM tăng **chưa đo**. Phải dùng một bản `YOLO` riêng, vì gọi `predict` trên chính model đang `track` sẽ chạy cả callback của bộ bám.
- Điểm cắm khớp với gợi ý ở mục P01 của `tong_hop_ung_vien.md` (các lệnh `mc.event` ở dòng 443 và 470, `mc.frame_live` ở dòng 544, `mc.frame_raw` ở dòng 497). Cuối cùng chọn làm mờ `vis` thay vì `bgr`, để khung chữ nhật và nhãn vẽ đè lên vẫn rõ.

## Tệp

- `lay_khung_xuong.py`: lấy khung xương trên CPU, kết quả ở `_cache/khung_xuong.json` cùng các khung `.jpg`.
- `lam_mo_mat.py`: `blur_faces`, `head_ellipse`, `raised_hand_zones`.
- `danh_gia.py [pixel|gauss]`: đo tốc độ và tay giơ, ghép lưới ảnh, ghi `ket_qua_<che_do>.json`. Lưu ý: chạy chế độ `gauss` sẽ ghi đè các ảnh trong `anh/`; chạy lại `pixel` để có lại ảnh pixel hoá.
- `dai_nhan.py`: dải ảnh theo từng lần giơ tay có nhãn (`anh/nhan_*.jpg`).
- `nguoi_bi_sot.py`: người conf 0.1–0.3 có điểm đầu (`anh/nguoi_bi_sot*.jpg`, `_cache/nguoi_conf_thap.json`).
- `soi.py`: phóng to một vài người, ví dụ `python soi.py anh/x.jpg 07_0315#1 12_0050#5`.
- `anh/`: lưới đầu (`luoi_dau_*`), lưới tay (`luoi_tay_*`), khung nguyên (`khung_*`, `sot_*`), ảnh soi lỗi (`soi_*`). Các ảnh này chứa mặt người trong clip mẫu nên chỉ để trên máy, không đưa lên đâu.
