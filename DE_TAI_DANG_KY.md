# Nội dung đăng ký Mini Hackathon GDG DevFest MienTrung 2026

Bản Claude soạn ngày 03/11/2026 để điền vào form đăng ký. Đây là bản nháp cuối cùng trong cuộc trò chuyện, không phải bản chụp từ form: câu chữ thật đã nộp có thể khác chút nếu lúc dán có sửa tay.

- **Tên ý tưởng / nhóm:** Easy FnB
- **Chủ đề:** Tiện ích doanh nghiệp
- **Trưởng nhóm:** Đỗ Vũ Hoàng Tiến, Đại học FPT Đà Nẵng
- **Ngôn ngữ lập trình:** Python, TypeScript, SQL, C#, Java, Ruby

## Mô tả ý tưởng

Easy FnB biến camera an ninh quán đã lắp sẵn thành một "quản lý ca" AI không bao giờ rời mắt khỏi quán.

**Bài toán:** Quán ăn đang vận hành bằng mắt và trí nhớ của một quản lý ca, người chỉ nhìn được một góc. Khách cần gì phải tự gọi, bàn dọn chậm nên khách ở cửa bỏ về, nhân viên người quá tải người đứng rảnh. Chủ quán không biết ca vừa rồi đã xảy ra chuyện gì, ai làm tốt, khách nào hay quay lại. Thuê thêm người thì tốn kém, chuông gọi hay QR thì không giải quyết được gốc.

**Giải pháp:**
- **Hiểu cả quán:** AI theo dõi từng bàn trong suốt bữa ăn và nhận ra khách cần gì (gọi phục vụ, tính tiền, thêm nước, hết món, cần dọn, khách chờ ở cửa, sự cố) trước khi khách phải gọi.
- **Điều phối:** giao mỗi việc cho đúng một nhân viên phù hợp nhất, đọc thẳng vào tai nghe Bluetooth qua app điện thoại, camera tự xác nhận khi đã xong.
- **Quản lý nhân viên và khách quen:** chấm công, hiệu suất từng người; nhận ra khách quen (có đồng ý) để chào đúng tên, nhớ sở thích.
- **AI agent cho chủ quán:** hỏi bất cứ điều gì camera đã ghi lại, kèm mốc giờ và clip; cuối ca tự tóm tắt và gợi ý cách vận hành tốt hơn.

**Đối tượng:** quán ăn, nhà hàng từ khoảng 15 bàn trở lên và các chuỗi F&B. Quán vừa và nhỏ phục vụ kịp mọi bàn mà không phải thuê thêm người; nhà hàng lớn và chuỗi theo dõi được nhiều khu, nhiều chi nhánh trên cùng một màn hình. Easy FnB dùng lại camera an ninh có sẵn, nhận diện khuôn mặt chạy ngay tại quán và chỉ với khách đã đồng ý.

## Công nghệ Google sẽ dùng

Gemini API (xác minh tín hiệu từ camera, mô tả cảnh), Gemini + Google ADK (AI agent cho chủ quán), Gemini Embedding (tìm kiếm lại video), Cloud Text-to-Speech Chirp 3 HD (đọc thông báo vào tai nghe nhân viên), Firebase Cloud Messaging (đẩy việc tới app nhân viên), Cloud Run (triển khai hệ thống)

## Câu hỏi đã soạn cho ban tổ chức

1. Nhóm đã có bản demo giao diện chạy bằng dữ liệu mô phỏng, chưa có phần AI. Như vậy có được tính là dưới 30% không?
2. Tại địa điểm thi, nhóm có được mang camera IP và máy có GPU để demo trực tiếp không?
