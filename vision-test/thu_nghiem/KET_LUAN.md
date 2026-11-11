# Lấy gì từ các báo cáo nghiên cứu: đã thử thật trên máy (5/11/2026)

Gom từ 5 báo cáo được khoảng 75 kỹ thuật (`research_notes/Bài toán tương tự ngành khác/tong_hop_ung_vien.md`). Những cái đáng nhất được thử thật trên laptop RTX 3050 4 GB, với 11 clip test và nhãn sẵn có. Nhãn còn mỏng (7 lần giơ tay, 137 mốc bàn, phần lớn ở clip time-lapse), nên "đạt" ở đây nghĩa là chạy được, không làm hỏng gì, đủ nhanh. Chưa chứng minh được là ít báo nhầm hơn ở quán thật.

## Nên đưa vào bản demo

| Kỹ thuật | Lấy từ ngành | Kết quả đo | Chi tiết và bản sửa |
|---|---|---|---|
| Máy trạng thái bàn: chờ 5 s mới coi là khách rời, chờ 1 s mới coi là khách tới, bàn bẩn ≥ 0,5 mới bật và < 0,35 mới tắt, giữ sạch 3 s | Bãi đỗ xe, hàng chờ sân bay | Bàn 137/137 (cho trễ 0,5 s), cũ 136. Sự kiện sai khi người bị che 1–4 s: 6,5 → 0,2 mỗi bàn mỗi phút. Hết lỗi "khách mới" lặp (tái hiện ở clip 06). Đổi lại: "khách rời" báo chậm hơn khoảng 5 s | `trang_thai_ban/KET_QUA.md` |
| RTMPose theo lượt (4 người mỗi khung) + tích luỹ bằng chứng giơ tay yếu | Kiểu Frigate/LookDeep: phần chậm chạy thưa | Clip 10: 10 → 19–21 fps. Giơ tay 5/7 → 6/7, 0 báo nhầm, trễ 0,40 → 0,59 s. Bàn 130/137 giữ nguyên | `gpu/KET_QUA.md`, `gpu/de_xuat.diff` |
| Gemini xem dải 4 khung + toàn cảnh khoanh đỏ, nhãn cố định có "không chắc", timeout 2,5 s, ngắt mạch sau 3 lỗi | Trung tâm xác minh báo động, NVIDIA VSS | 23/23 kiểm thử đạt. Khoảng 1.170–1.410 token, 13–15 đ mỗi lần gọi. Gửi khung từ 1 s sau sự kiện thì thấy tay đang giơ (4/5 so với 0/5). Chưa đo độ đúng (chưa có khoá Gemini) | `gemini_goi_kiem_tra/KET_QUA.md`, `de_xuat_server.patch` |
| Làm mờ mặt từ keypoint đầu trước khi gửi khỏi máy | Phân tích bán lẻ giữ quyền riêng tư | Che 95% mặt (99% ở clip quán ăn), che nhầm 1/89 tay giơ, 0,8 ms mỗi khung trên CPU | `lam_mo_mat/KET_QUA.md` |
| YOLOE-26s nhận đồ trên bàn bằng chữ, chạy một lần sau khi khách rời | Phát hiện đồ bỏ quên, phát hiện vật bằng chữ | Một mình 73/91, kém classifier (84/91). Kết hợp "classifier nói bẩn và YOLOE thấy đồ" được 85/91, 0 bàn sạch bị báo. Liệt kê được đồ còn lại cho nhân viên. TensorRT 11–20 ms | `yoloe_do_tren_ban/KET_QUA.md` |

## Không nên làm (đã đo, không có lợi)

| Kỹ thuật | Kết quả |
|---|---|
| So bàn với ảnh bàn sạch (kiểu AnomalyDINO, PE-Core hoặc DINOv2) | 62–65/78, kém classifier (72/78). Không có ngưỡng chung cho các bàn. Người che tay lên bàn thì báo bẩn 14/16 |
| Bỏ phiếu bẩn khi người che bàn; bắt nhân viên phải ghé mới cho "đã dọn" | Ở góc trên cao, box của người bàn bên che 30–50% bàn trống. Bộ nhận nhân viên hiếm khi vượt 0,5 |
| Gallery nhân viên đăng ký theo ca | Gắn nhầm khách thành nhân viên (4–6/6 khách ở clip 06). Ảnh giống nhau vì cùng cảnh, không vì quần áo. Cần footage thật có đồng phục rõ |
| RTMPose chỉ cho "ứng viên" | Trễ 1,2 s vì YOLO không thấy chính cánh tay đang giơ |
| Đổi tracker, RTMPose-s (đã thử từ trước) | Không lợi |

## Chưa thử được trên máy này

- Độ đúng của Gemini với gói mới, và Gemini trên ảnh đã làm mờ mặt: cần khoá Gemini.
- Camera điện thoại qua RTSP, đo trễ từ lúc giơ tay đến lúc điện thoại nhân viên kêu: cần điện thoại thật.
- Lớp theo thời gian (GRU) và ảnh SCB cho bộ nhận giơ tay: cần footage nhóm tự quay, hoặc tải dataset (cần đồng ý).
