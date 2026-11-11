# Hướng dẫn gán nhãn

Mỗi bảng ảnh có 25 ô đánh số 1 đến 25 (đọc từ trái sang phải, trên xuống dưới). Bảng cuối có thể ít hơn 25 ô; ô trắng thì bỏ qua. Mỗi ô là một ảnh cắt tự động bởi YOLO, nên đôi khi cắt sai.

## Ảnh bàn (bảng `ban_*.jpg`)

Câu hỏi: **nếu không có ai ngồi, bàn này có cần dọn không?** Chỉ nhìn mặt bàn, không quan tâm có người hay không.

| Nhãn | Khi nào |
|---|---|
| `s` (sạch) | Mặt bàn trống, hoặc chỉ có đồ bày sẵn cho khách mới: khăn trải, giấy lót, ly sạch úp hoặc chưa rót, dao nĩa xếp gọn, khăn ăn gấp, menu, ống đũa, chai nước chấm, hộp giấy, lọ hoa, nến, đồ trang trí |
| `b` (bẩn) | Có đồ ăn, chén dĩa đã dùng hoặc đang dùng, đồ ăn thừa, ly có nước uống dở, cốc cà phê đang uống, khăn giấy vo, vỏ hộp, rác, vụn thức ăn |
| `x` (bỏ) | Không phải bàn ăn (bàn làm việc với laptop, sách vở, quầy bar nhìn từ xa), không thấy rõ mặt bàn, bị che gần hết, quá mờ, hoặc không chắc |

Khi phân vân giữa `s` và `b`: một ly nước còn đầy hoặc cốc cà phê đang uống là `b` (khách dùng rồi). Chỉ ly sạch chưa có gì mới là `s`.

## Ảnh người (bảng `nguoi_*.jpg`)

Câu hỏi: **người này là nhân viên quán hay khách?**

| Nhãn | Khi nào |
|---|---|
| `n` (nhân viên) | Đeo tạp dề, mặc đồng phục phục vụ (áo sơ mi trắng với gile hoặc tạp dề đen), đang bưng khay hay đĩa đến bàn, cầm sổ ghi order, đưa máy tính tiền, đứng sau quầy pha chế, đầu bếp |
| `k` (khách) | Ngồi ăn uống, trò chuyện, xem điện thoại, đi vào quán, đứng chờ, mặc đồ thường và không làm việc phục vụ |
| `x` (bỏ) | Không phải trong quán ăn (lớp học, văn phòng, đường phố), bị cắt quá ít người, quá mờ, hoặc không chắc |

## Cách trả kết quả

Mỗi bảng một dòng: tên bảng, dấu hai chấm, rồi 25 ký tự nhãn theo thứ tự ô (ít hơn nếu bảng chưa đủ 25 ô). Ví dụ:

```
ban_001: ssbbxbsbbbssxbbbsbbbbsbsb
```
