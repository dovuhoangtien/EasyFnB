# Kết quả "mắt tại quán": v4 so với v3 (5/11/2026)

Bản v4 thử các công nghệ tốt nhất tìm được trong báo cáo nghiên cứu, rồi chấm lại trên đúng 11 clip test và các tập ảnh kiểm tra cũ. Mọi thứ đo trên laptop RTX 3050 4 GB.

Điểm chi tiết: [danh_gia/diem_v4.json](danh_gia/diem_v4.json). Video kết quả (`demo_v4.mp4`, `out_v4/<clip>/video_ket_qua.mp4`) không nằm trong repo vì có hình người trong clip gốc.

## Tóm tắt

| | v3 | v4 nhanh | v4 nhạy (bản demo) |
|---|---|---|---|
| Trạng thái bàn, chấm chặt | 129/137 | **130/137** | **130/137** |
| Trạng thái bàn, cho trễ 0,5 s | 134/137 | **136/137** | **136/137** |
| Nhìn bàn sạch hay bẩn (clip 01) | 55/64 | **62/64** | **62/64** |
| Bàn sạch không bị nhìn thành bẩn | 52/59 | **58/59** | **58/59** |
| Khách giơ tay: bắt được | 5/7 | 5/7 | 5/7 |
| Khách giơ tay: báo nhầm | 0 | 0 | 0 |
| Khách giơ tay: trễ trung bình | 1,41 s | 1,37 s | **0,40 s** |
| Tốc độ GPU, cả pipeline | 25 khung/giây | **57** | 24 |
| Tốc độ ở clip đông người nhất | 20 | 35 | 11 |
| Ước số camera (5 khung/giây mỗi camera) | ~5 | **~11** | ~5, chỉ 2 nếu quán rất đông |

Độ trễ giơ tay chấm bằng bộ chấm theo sự kiện mới (`danh_gia/cham_su_kien.py --dap-an-cu`). Bộ chấm cũ cho một lần báo được tính cho hai người cùng giơ tay ở clip 10, nên ra 1,21 s và 1,17 s, thấp hơn thực tế.

- **v4 nhanh:** model ảnh mới, chạy YOLO bằng TensorRT. Hợp với nhiều camera.
- **v4 nhạy:** thêm RTMPose để lấy khung xương từng người. Báo giơ tay nhanh gấp 3, nhưng chậm khi đông người. Hợp cho demo một hai camera.

Hai lần giơ tay vẫn bị sót ở mọi bản, đều trong clip 10: em ngồi xa và em bị cắt ở mép hình.

## Đã thử gì, giữ gì

| Thử | Kết quả | Giữ |
|---|---|---|
| 10 bộ mã hoá ảnh thay CLIP cũ (chi tiết bên dưới) | PE-Core S/16 nhìn bàn tốt hơn hẳn; PE-Core B/16 giảm một nửa báo nhầm giơ tay; nhân viên/khách không model nào hơn | Có, mỗi việc một model |
| TensorRT FP16 cho YOLO trên GPU | Nhanh 2,4–2,8 lần, kết quả y hệt | Có |
| OpenVINO cho YOLO trên CPU | Nhanh 1,6–2 lần | Có, khi chạy CPU |
| Bộ bám người TrackTrack, BoT-SORT + ReID, ByteTrack giữ track lâu hơn | Không tăng điểm; TrackTrack ít track hơn 28% nhưng bỏ sót người | Không, giữ ByteTrack |
| yolo26s-pose (khung xương lớn hơn) | Thấy cả người ở bàn trống, trạng thái bàn tụt còn 121/137 | Không |
| RTMPose-m trên từng người | Giơ tay báo sau 0,4 s thay vì 1,4 s; chậm hơn | Có, ở bản nhạy |
| RTMPose-s, hoặc RTMPose chỉ cho người khó | Không giúp, hoặc tệ hơn (3/7) | Không |

### Bộ mã hoá ảnh: 10 model, cùng dữ liệu, cùng cách chấm

| Model | Bàn sạch/bẩn, không train (91 ảnh) | Nhân viên/khách (105 ảnh) | Giơ tay: bắt được, khi chỉ 1% ảnh "không giơ" bị báo (26 ca) |
|---|---|---|---|
| CLIP B/32 LAION (v3) | 75 | 101 | 19 |
| CLIP B/32 DataComp | 75 | 96 | 18 |
| SigLIP 2 B/32 | 75 | 100 | 21 |
| SigLIP 2 B/16 | 74 | 102 | 20 |
| MobileCLIP2-S0 | 72 | 98 | 11 |
| MobileCLIP2-S2 | 80 | 102 | 13 |
| MobileCLIP2-B | 78 | 99 | 12 |
| DFN CLIP B/16 | 77 | 101 | 11 |
| **PE-Core S/16** | **84** | 97 | 9 |
| **PE-Core B/16** | 71 | 98 | **22** |

Kiểm định McNemar so với CLIP cũ trên cùng ảnh:

- **Bàn, PE-Core S/16:** 13 ảnh mới đúng mà cũ sai, 4 ảnh ngược lại (p = 0,049).
- **Giơ tay, PE-Core B/16:** khi bắt cùng 22/26 ca như bản cũ, ảnh "không giơ" bị báo nhầm giảm từ 46 xuống 16 trên 1.668 ảnh.

Bản dùng:

- **Bàn:** PE-Core S/16, không train.
- **Giơ tay:** lớp nhỏ mới trên PE-Core B/16, ngưỡng 0,35. Ngưỡng chọn trên tập kiểm tra của dữ liệu train, không dùng clip test: ở đó vẫn bắt 22/26, báo nhầm 22 thay vì 46.
- **Nhân viên/khách:** giữ lớp nhỏ CLIP cũ. Lớp mới trên PE-Core B/16 chỉ đúng 98/105.

Ba bộ mã hoá cùng chạy được vì mỗi model chỉ giữ phần ảnh ở FP16 trên GPU, còn phần chữ (to hơn phần ảnh ở PE-Core) bỏ đi sau khi tính sẵn câu mô tả.

Không thử: SigLIP 2 L/16 và PE-Core L/14. Hai model này quá to để chạy cùng YOLO trên card 4 GB; PE-Core L/14 tràn bộ nhớ GPU ngay khi thử.

## Tốc độ từng model (clip 08, khung thật, tính cả chuẩn bị ảnh và xử lý kết quả)

| Model | GPU PyTorch | GPU TensorRT FP16 | CPU PyTorch | CPU ONNX Runtime | CPU OpenVINO |
|---|---|---|---|---|---|
| yolo26n-pose @960 | 18,3 ms | **7,5 ms** | 51 ms | 41 ms | **26 ms** |
| yolo26s-pose @960 | 19,1 ms | 8,0 ms | 107 ms | 101 ms | 68 ms |
| yolo26s đồ vật @1280 | 25,3 ms | **9,1 ms** | 165 ms | 189 ms | 112 ms |
| yolo26s đồ vật @960 | 16,5 ms | 7,3 ms | 101 ms | 95 ms | **60 ms** |

Máy chỉ có CPU (Ryzen 7 6800H) nên dùng OpenVINO. Model ảnh mới chậm hơn CLIP cũ trên CPU: PE-Core B/16 tốn khoảng 3 lần CLIP B/32. Vì vậy, trên máy chỉ có CPU, nên chỉ hỏi model giơ tay khi cổ tay đã lên trên vai (pipeline đang làm vậy), và xét bàn khoảng 1 lần mỗi giây. Chưa đo cả pipeline v4 trên CPU.

## Lưu ý khi đọc số

- Bộ test nhỏ: 7 lần giơ tay, 64 mốc nhìn bàn, 91 ảnh bàn. Chênh 1–2 ca có thể chỉ là may.
- **Model bàn chọn trên chính 91 ảnh bàn của clip test 01:** model tốt nhất trong 10 model thì dễ đẹp hơn thực tế. Lần này mình không chỉnh câu mô tả theo điểm; bộ câu mô tả viết thêm còn kém hơn bộ cũ nên không dùng.
- **Cách kết hợp giơ tay vẫn là cách đã chọn ở v3** sau khi xem điểm 7 lần giơ tay.
- Tất cả vẫn là clip stock. Cần footage thật của quán để biết chắc.

## Chạy lại

```bash
venv\Scripts\pip install ultralytics opencv-python lap open_clip_torch scikit-learn timm "transformers<5" onnx onnxslim openvino tensorrt-cu12 "onnxruntime-gpu==1.23.2" rtmlib

:: xuất YOLO sang TensorRT (GPU) và ONNX, OpenVINO (CPU), rồi đo tốc độ
venv\Scripts\python danh_gia/do_toc_do.py xuat --gpu --cpu
venv\Scripts\python danh_gia/do_toc_do.py do --gpu --cpu

:: v4 nhạy (bản demo). Bỏ hai tham số --pose-refine, --refine-mode là thành v4 nhanh
venv\Scripts\python easyfnb_test.py clips/ --out out_v4 --dump ^
  --hand-model giotay_pe_b16.pt --hand-th 0.35 --staff-model nhanvien_clip_v1.pt ^
  --table-model clip --clip-backbone pe_core_s16 ^
  --pose-models yolo26n-pose_544x960_fp16.engine --det-models yolo26s_736x1280_fp16.engine ^
  --pose-refine rtmpose-m --refine-mode tat_ca
venv\Scripts\python danh_gia/cham_diem.py out_v4 --ten v4
venv\Scripts\python danh_gia/nhin_ban.py out_v4
venv\Scripts\python lam_video_demo.py out_v4 demo_v4.mp4
```

- **So bộ mã hoá ảnh:** `danh_gia/so_clip.py --data <thư mục data> --cache <thư mục lưu đặc trưng>`, rồi `danh_gia/kiem_mcnemar.py`.
- **Train lớp nhỏ trên bộ mã hoá khác:** `clip_cls.py train ... --backbone pe_core_b16` và `train/train_tay_clip.py ... --backbone pe_core_b16`. File lớp nhỏ tự nhớ nó được train trên bộ mã hoá nào.
- **Engine TensorRT gắn với GPU đã build ra nó.** Sang máy khác phải chạy lại `do_toc_do.py xuat`.
- **Chạy thêm tham số `--no-video` khi chỉ cần chấm điểm,** đỡ tốn RAM và thời gian. Máy 16 GB đang mở trình duyệt và app Claude thì đừng chạy hai việc nặng cùng lúc: thiếu RAM sẽ làm crash lúc nạp model.

## Còn thiếu

1. **Footage thật của quán Việt** (bạn đang quay). Cách quay, gán nhãn và chấm theo sự kiện: [quay/KICH_BAN_QUAY.md](quay/KICH_BAN_QUAY.md).
2. **Gemini xác minh ảnh cắt.** Cần API key. Model nên dùng: `gemini-3.5-flash-lite`, ảnh `low`, trả JSON.
3. **Nhận cử chỉ theo chuỗi khung xương 1–1,5 giây** (GRU nhỏ). Có thể sửa được ca vuốt tóc và ca giơ tay ngắn, nhưng cần clip có nhãn theo thời gian: footage tự quay, hoặc bộ BK-SAD.
4. **Nhận diện khách quen.** Chưa thử vì chưa có ảnh mặt người đồng ý tham gia.
