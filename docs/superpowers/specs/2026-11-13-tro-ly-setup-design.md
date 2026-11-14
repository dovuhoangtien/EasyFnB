# Trợ lý cài đặt quán ngay trong khung chat

Ngày: 13/11/2026 · Trạng thái: đã làm (bản 2, đã bỏ khối tiến độ). Công cụ tìm bàn tên là `tu_tim_ban` (trong tools() đã có hàm `tim_ban` khác) · Phạm vi: `easy-fnb/server/tro_ly.py`, `easy-fnb/server/app.py`, `easy-fnb/src/app/` (khối chat)

## 1. Mục tiêu

Chủ quán nói muốn làm gì ("nối camera", "thêm Lan chạy bàn", "1 phút chưa ai nhận thì nhắc") thì trợ lý làm luôn trong khung chat. Không phải vào trang Cài đặt. Không có danh sách bước, không có thanh tiến độ: hỏi gì làm nấy.

Hai nguyên tắc:

1. **Model không tự sửa dữ liệu.** Công cụ của model chỉ dựng khối. Dữ liệu chỉ đổi khi chủ quán bấm **Lưu** trong khối.
2. **Không có AI vẫn làm được.** Đường không AI (`rules`) bắt các câu cài đặt chính và ra đúng các khối này. Mai demo, không để phụ thuộc mạng.

## 2. Dùng lại những gì có sẵn

- `tro_ly.py`: tác tử Google ADK. Công cụ "hiện" bỏ khối vào `box['blocks']`, dữ liệu trong khối do máy chủ điền. Lỗi thì rơi về `tra_loi_rules`.
- API: `PUT /api/staff`, `PUT /api/zones`, `POST /api/zones/suggest` (camera tự tìm bàn), `POST /api/staff/{id}/photos/camera`, `PUT /api/settings`, `GET /api/phone/{cam}/status`.
- `Settings.tsx` có sẵn cách dựng link mã QR camera và nhân viên, theo dõi điện thoại nào đang nối. Phần này chuyển ra `src/app/connect.tsx` để Cài đặt và chat dùng chung, không sao chép.

## 3. Cách làm

**Cách A, chọn.** Công cụ của model dựng khối có nút. Bấm **Lưu** thì giao diện gọi thẳng API cài đặt có sẵn (`PUT /api/staff`...) với dữ liệu trong khối. Không thêm route mới, không gọi lại Gemini khi bấm.
- Được: đơn giản nhất, model không có đường ghi dữ liệu, bấm là chạy ngay, đường không AI dùng chung khối.
- Mất: model không biết chủ quán đã bấm gì. Đỡ bằng cách lượt sau giao diện gửi kèm một dòng "đã lưu ..." (mục 6).

**Cách B.** Kho đề xuất trên máy chủ, có mã, hết hạn, kiểm phiên bản trước khi ghi. Chặt hơn nhưng thêm một module và một route. Để dành nếu sau này cần đăng nhập, phân quyền.

**Cách C.** Cho model công cụ ghi thật, dùng chế độ xác nhận của ADK. Phụ thuộc phiên bản ADK, mỗi lần bấm tốn một lượt Gemini, đường không AI không dùng được. Không hợp lúc sát demo.

## 4. Kịch bản mẫu

### Kịch bản 1. Nối camera rồi tìm bàn

> **Chủ quán:** giúp tôi nối camera
>
> **Trợ lý:** Mở camera điện thoại quét mã này, đặt máy nhìn bao quát các bàn.
> *[Mã QR camera cam1 · "Đang chờ điện thoại…"]*

Điện thoại quét xong, khối tự đổi thành hình camera đang chạy, "Đã nối", nút **Tìm bàn**.

> *(bấm Tìm bàn, nút gửi câu "tìm bàn ở cam1")*
>
> **Trợ lý:** Camera thấy 7 bàn, đặt tên B1 tới B7 từ trái sang phải.
> *[Ảnh camera vẽ 7 khung có tên · **Lưu 7 bàn** · Tìm lại · Sửa tay]*

Bấm Lưu → khối thu lại một dòng "Đã lưu 7 bàn cho cam1".

### Kịch bản 2. Thêm nhân viên

> **Chủ quán:** quán có Lan với Hoa chạy bàn, anh Tư dọn
>
> **Trợ lý:** Thêm 3 người, kiểm lại rồi bấm Lưu.
> *[Lan · phục vụ / Hoa · phục vụ / Tư · dọn bàn (sửa được) · **Lưu** · Huỷ]*

Lưu xong, khối hiện mã QR cho từng người mở app nhân viên, chấm xanh khi người đó đã mở.

### Kịch bản 3. Đổi luật báo, và lỗi

> **Chủ quán:** 1 phút chưa ai nhận thì nhắc người khác, dọn bàn thì báo luôn đừng chờ AI
>
> *[Nhắc lại khi chưa ai nhận: tắt → 60 giây · Chờ AI rồi mới báo dọn: bật → tắt · **Lưu** · Huỷ]*

> **Chủ quán:** tìm bàn giúp tôi *(camera chưa nối)*
>
> **Trợ lý:** Camera chưa gửi hình về nên chưa tìm được. Quét mã này để nối, xong bấm Tìm bàn.
> *[Mã QR camera cam1]*

## 5. Công cụ mới cho tác tử

Không công cụ nào ghi dữ liệu.

| Công cụ | Làm gì |
|---|---|
| `noi_camera(camera='cam1')` | Khối `qr` cho camera. Đã nối rồi thì khối hiện luôn hình đang chạy. |
| `tim_ban(camera='cam1')` | Nhờ máy camera tìm bàn (như `/api/zones/suggest`), đặt tên theo thứ tự đọc như ZoneEditor. Ra khối `ban`. Camera chưa chạy hoặc không trả lời thì trả lý do, model gọi tiếp `noi_camera`. |
| `sua_nhan_vien(them, bo, doi)` | `them`: dòng "Tên \| vai trò"; `bo`: tên người bỏ; `doi`: "tên \| tên mới \| vai trò mới". Máy chủ tạo mã không dấu, không trùng, đổi vai trò tiếng Việt ra `serve/clean/cashier`. Ra khối `xac_nhan` chứa **cả danh sách sau khi sửa** (để Lưu gửi thẳng `PUT /api/staff`). |
| `ma_qr_nhan_vien(ten='')` | Khối `qr` cho app nhân viên, rỗng là mọi người. |
| `doi_luat_bao(...)` | Tham số có tên, chỉ đưa cái muốn đổi: `kiem_tra_khach_goi`, `kiem_tra_don_ban`, `cho_ai_roi_moi_bao_don`, `nhac_lai_sau_giay`, `tu_dong_sau_giay`, `nhac_chua_tiep_phut`, `nhac_cho_mon_phut`, `nhac_tinh_tien_phut`. Kiểm giới hạn ngay. Ra khối `xac_nhan` dạng "trước → sau". |
| `chup_anh_nhan_vien(ten, camera='cam1')` | Khối `chup`. |

Lời dặn thêm một đoạn ngắn: chủ quán muốn cài, nối, thêm, đổi gì thì gọi đúng công cụ và nói "bấm Lưu để áp dụng", **không bao giờ nói "đã lưu"**; không nhận khoá API trong chat. "Giúp tôi setup" chung chung thì trả lời một câu kèm gợi ý bấm: Nối camera · Tìm bàn · Thêm nhân viên · Đổi luật báo (dùng ô gợi ý có sẵn của câu trả lời, không thêm khối).

Đường không AI: thêm nhánh trước các nhánh số liệu, bắt `cai dat, setup, thiet lap, noi camera, ket noi camera, tim ban, them nhan vien, ma qr, luat bao`. "Thêm nhân viên Lan phục vụ" bắt bằng mẫu câu; không bắt được thì ra khối `xac_nhan` có ô trống để tự điền. Luật báo ra khối có sẵn các ô hiện tại để chỉnh.

## 6. Khối mới và cách xác nhận

Bốn khối, dùng `Button`, `Switch`, `NumberInput`, `TextInput`, `Selector`, `Banner`, `StatusDot`, `QrCode` của Astryx. Mỗi khối một nút chính, chữ ngắn.

| Khối | Hiện gì | Bấm |
|---|---|---|
| `qr` | Mã QR, nút chép link, trạng thái tự cập nhật mỗi 2 giây. Nối xong: camera hiện hình, nhân viên hiện chấm xanh. Link http trên điện thoại thì báo trước như trang Cài đặt. | Camera đã nối: **Tìm bàn**. |
| `ban` | Ảnh camera, các khung bàn vẽ bằng SVG, tên ở góc. Đã có vùng thì ghi "Đang có 6 bàn, camera thấy 7". | **Lưu** (khi đã có vùng: Thay hết / Chỉ thêm bàn mới), Tìm lại, Sửa tay (mở Cài đặt đúng camera). |
| `xac_nhan` | Các dòng thay đổi, sửa được tại chỗ. Bỏ người có ảnh nhận dạng thì ghi "ảnh của Minh sẽ bị xoá". | **Lưu** · Huỷ. |
| `chup` | Hình camera đang chạy, "Nhờ Lan đứng giữa khung hình", công tắc "Lan đồng ý cho camera nhận dạng" (phải bật mới chụp). | Chụp; sau đó Giữ · Chụp lại. |

Xác nhận:

1. Bấm **Lưu** → giao diện gọi API có sẵn (`PUT /api/staff`, `PUT /api/zones`, `PUT /api/settings`) với dữ liệu trong khối. Máy chủ đã kiểm hợp lệ ở các route này; lỗi thì khối hiện `Banner` lỗi tại chỗ.
2. Thành công → khối thu lại một dòng ("Đã lưu 3 nhân viên"), chat không dài thêm.
3. Lượt hỏi kế tiếp, giao diện gửi kèm dòng ngắn `[đã lưu 3 nhân viên: Lan, Hoa, Tư]` để model biết.
4. Chống ghi đè: trước khi Lưu, khối so với dữ liệu đang có (giao diện đã nhận `staff`, `zones`, `settings` qua SSE). Nếu ai đó vừa sửa ở trang Cài đặt sau khi khối được dựng thì báo "Dữ liệu vừa đổi, hỏi lại để làm mới", không ghi.
5. Chụp ảnh: bấm Chụp chính là xác nhận (`POST /api/staff/{id}/photos/camera`); Chụp lại thì xoá ảnh vừa chụp.

Việc không đổi dữ liệu (mã QR, tìm bàn để xem) không cần xác nhận.

## 7. Test

Máy chủ, tệp mới `server/tests/test_tro_ly_setup.py`, chạy cùng bộ test hiện có:

- Gọi từng công cụ rồi kiểm `hub.staff`, `hub.zones`, `hub.settings` **không đổi**.
- `sua_nhan_vien`: tên có dấu ra mã không dấu, tên trùng ra mã khác, vai trò tiếng Việt đúng, danh sách sau sửa gửi được vào `PUT /api/staff`.
- `doi_luat_bao`: ngoài giới hạn bị từ chối, "trước → sau" đúng, phút ra giây đúng.
- `tim_ban`: camera chưa chạy thì trả lý do; giả máy camera trả kết quả (`hub.job_result`) thì ra khối `ban` đúng tên, đúng thứ tự.
- Đường không AI: "nối camera", "thêm nhân viên Lan phục vụ", "tìm bàn" ra đúng khối; các test số liệu cũ không đổi.

Model thật (chạy tay): khoảng 10 câu cài đặt qua `python -m server.tro_ly`, ghi lại công cụ được gọi, kiểm không câu nào nói "đã lưu".

Giao diện: `tsc`, `vite build` sạch; vite dev (không đụng tiến trình cổng 8080), đi hết 3 kịch bản trên trình duyệt, thử khổ 375 px.

## 8. Rủi ro

- **Thời gian**, mai demo. Làm trước: `noi_camera`, `tim_ban`, `sua_nhan_vien` (chỉ thêm), `ma_qr_nhan_vien`. Sau: luật báo, chụp ảnh, bỏ/đổi nhân viên.
- **Flash-lite chọn sai công cụ hoặc nói như đã xong.** Khối luôn nói trạng thái thật; đường không AI bắt các câu chính.
- **Tìm bàn chờ tới 12 giây** trong lượt 30 giây: đủ, nhưng chữ chờ phải đổi thành "Đang làm…".
- **Không có đăng nhập:** không mở thêm lỗ nào so với trang Cài đặt hiện tại.
- **Ảnh nhân viên:** chỉ chụp khi đã bật đồng ý.

## 9. Ngoài phạm vi

Danh sách bước / tiến độ cài đặt; nhập khoá Gemini trong chat; thêm camera IP/RTSP; vẽ bàn bằng tay trong chat; bắt đầu ca mới qua chat; xác nhận bằng giọng nói; lưu lịch sử chat qua lần tải lại trang.
