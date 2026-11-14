# Spec: Easy FnB giúp chủ quán kiếm thêm tiền và đỡ việc

Ngày: 13/11/2026 · Trạng thái: **bản nháp, chờ duyệt** · Chưa có dòng code nào.

Không thuộc spec này: phòng chat nhân viên, hoá đơn, an ninh, trợ lý tự cài đặt, khớp bàn (các phiên khác đang làm).

## 1. Bối cảnh ngắn

**Hệ thống đã có** (theo `docs/he-thong-hien-tai.md`):

| Dữ liệu | Có chưa | Lưu ở đâu |
|---|---|---|
| Trạng thái bàn (trống, có khách, cần dọn) và số người ở bàn | Có | Sự kiện `table` trong `timeline.db`, có `people` |
| Giai đoạn bữa ăn: mới ngồi → có người ra tiếp → có món → ăn xong → đã rời, kèm số giây ở bước trước | Có | Sự kiện `stage` (`prev`, `prev_s`, `seat`) |
| Lời nhắc mềm: chưa ai ra tiếp, chờ món lâu, chờ tính tiền | Có | Sự kiện `nudge` |
| Khách gọi, thời gian chờ, ai tới, bỏ lỡ | Có | Các sự kiện `alert_*` |
| Ai đang trong ca, theo giờ | Có | `attendance` trong RAM (ghi vào timeline khi vào/ra ca) |
| Gợi ý ca sau, bảng thiếu/thừa người theo giờ | Có, chỉ trong một ca | `goi_y.py` |
| Clip video từng việc | Có (cờ `--ghi-hinh`) | Máy camera |
| Dữ liệu qua nhiều ngày | Có | `timeline.db` + `GET /api/timeline/days` |
| Tiền: giá trị một lượt bàn, doanh thu | **Chưa** | Không có máy tính tiền nối vào |
| Khách quen nhận theo mặt | **Chưa** (chỉ có ảnh nhận dạng nhân viên) | |
| Khách đứng chờ ở cửa không có chỗ | **Chưa** (không có vùng "cửa ra vào") | |

**Từ việc tra web** (nguồn ở cuối):
- Sản phẩm nước ngoài (Presto Vision, TableWatch, Safari AI, Sciforce) đều bán cùng mấy thứ: đo vòng quay bàn, thời gian chờ, khách bỏ về, độ lấp chỗ ngồi. TableWatch tự nói tăng 5 đến 10% doanh thu nhờ quay bàn nhanh hơn (số của hãng, không kiểm chứng).
- Khoảng 1/3 khách Mỹ được hỏi (Lightspeed 2025) nói từng bỏ về vì chờ lâu, có người bỏ trước khi gọi món.
- Mời thêm món chung chung chỉ ăn 5% (số đo ở drive-thru); mời đúng lúc thì tốt hơn. Bepoz nhắc: giờ đông thì quay bàn quan trọng hơn mời thêm món.
- Xếp ca theo lượng khách: các hãng báo tiết kiệm 1 đến 12% tiền công, số độc lập chưa có. Thực tế nên tính "vài phần trăm".
- Việt Nam: hơn 50.000 quán ăn uống đóng cửa nửa đầu 2025 (iPOS qua VnEconomy); lãi mỏng; 66% nhân viên F&B nghỉ trong năm đầu. Chủ quán nhỏ không có thời gian đọc báo cáo dài.
- Mặt người là dữ liệu cá nhân nhạy cảm (Nghị định 13/2023; Luật Bảo vệ dữ liệu cá nhân 91/2025 có hiệu lực 1/1/2026, **cần kiểm lại điều khoản cụ thể**). Nhận khách quen theo mặt cần khách đồng ý rõ ràng.

**Một điều kiện chung cho mọi số tiền:** hệ thống không biết hoá đơn. Chủ quán nhập **một con số duy nhất** trong Cài đặt: "Một bàn khách thường trả khoảng bao nhiêu" (ví dụ 150.000đ). Mọi số tiền trên màn hình ghi là **ước tính** và lấy từ con số này. Khi phiên hoá đơn xong, thay con số này bằng tiền thật của từng lượt.

## 2. Danh sách ý, xếp theo lời/công

Điểm "Lời" là tiền thêm hoặc giờ tiết kiệm cho một quán 10 đến 20 bàn. Điểm "Công" là công làm (1 = nửa ngày, 5 = hơn một tuần). Xếp theo Lời chia Công.

| # | Ý | Lời cho chủ quán | Dữ liệu cần | Đã có? | Lời | Công |
|---|---|---|---|---|---|---|
| 1 | **Khách bỏ về** | Thấy được tiền mất vì khách ngồi rồi đi mà chưa có món; sửa đúng chỗ | `stage`: `seated`/`greeted` → `left` không qua `served` | Có | 4 | 1 |
| 2 | **Bàn ngồi không ra tiền** (thời gian chết của bàn) | Biết bàn mất bao nhiêu phút ở mỗi bước: chờ người ra tiếp, chờ món, chờ tính tiền, bàn bẩn chưa dọn. Rút ngắn giờ cao điểm = thêm lượt khách | `stage` + `prev_s`, `table` | Có | 5 | 2 |
| 3 | **Mời thêm đúng lúc** | Giờ vắng: khách ăn xong ngồi lâu → nhắc nhân viên mời nước/tráng miệng. Giờ đông: thôi mời, ưu tiên tính tiền | `stage=finished` + thời gian ngồi + độ đông của quán | Có | 4 | 2 |
| 4 | Bản tin sáng 3 dòng | Chủ quán không phải mở báo cáo; mỗi sáng biết hôm qua mất gì, nên đổi gì | Timeline hôm qua, gợi ý sẵn có | Có | 3 | 1 |
| 5 | Xếp ca theo tuần | Từ 2 đến 4 tuần dữ liệu cùng thứ, đề xuất số người từng khung giờ cho tuần sau | `alert_*`, `table` theo ngày; `xep_ca` đã có cho một ca | Có, cần đủ ngày | 4 | 3 |
| 6 | Chỗ ngồi bị phí | Bàn 4 chỉ 1 người ngồi lâu giờ đông; bàn nào gần như không ai ngồi → sắp lại bàn | `people` theo bàn, số ghế từng bàn | Thiếu số ghế từng bàn | 3 | 2 |
| 7 | Giờ vắng để chạy khuyến mãi | Chỉ ra khung giờ vắng nhất trong tuần để làm "giờ vàng" | Số lượt ngồi theo giờ, nhiều ngày | Có | 2 | 1 |
| 8 | Khách đứng chờ ở cửa rồi đi | Đếm khách tới mà không có chỗ | Vùng cửa, đếm người vào/ra | Chưa | 4 | 4 |
| 9 | Khách quen nhận theo mặt | Chào tên, nhớ món quen | Nhận diện mặt, đồng ý của khách | Chưa, rủi ro luật | 3 | 5 |

Đề xuất làm trước: **#1, #2, #3**. Ba ý này dùng đúng dữ liệu đã có, cùng một đường tính (đọc sự kiện `stage` trong timeline), và nói thẳng bằng tiền. #4 làm ngay sau vì rẻ và dùng lại số của ba ý đầu.

## 3. Ba ý làm trước

Cả ba dùng chung một mô-đun tính mới ở máy chủ, ví dụ `server/luot_ban.py`: đọc sự kiện `stage` và `table` trong `timeline.db`, ghép thành **lượt bàn** (một nhóm khách từ lúc ngồi tới lúc rời). Không gọi AI để tính số. Gemini chỉ dùng để nói lại cho dễ nghe (trợ lý, bản tin).

```
Lượt bàn = { bàn, giờ ngồi, giờ rời, số người lớn nhất,
             giây ở từng bước: chờ ra tiếp, chờ món, ăn, sau khi ăn xong, chờ dọn,
             có món hay không, kết thúc: bình thường | bỏ về | chưa xong }
```

### 3.1. Khách bỏ về

**Định nghĩa.** Một lượt bàn kết thúc (`left`) mà chưa từng tới `served`, và đã ngồi ít nhất 2 phút (loại người ngồi nhầm, đứng lên đổi bàn). Chia hai loại:
- **Không ai ra tiếp:** chưa qua `greeted`.
- **Chờ món rồi bỏ:** đã có người tới nhưng chưa có món.

Lượt "khách tạm rời, còn đồ" không tính là bỏ về (giai đoạn đã giữ lượt cũ).

**Số liệu:**
- Số lượt bỏ về trong ca / hôm nay, và tỉ lệ trên tổng lượt.
- Tiền ước tính mất = số lượt × giá trị một bàn.
- Lúc nào hay xảy ra (khung giờ), bàn nào, đã chờ bao lâu.

**Màn hình.** Không thêm trang. Ở **Ca hôm nay**, thêm một thẻ nhỏ ở hàng số liệu:

```
Khách bỏ về    3 bàn  ·  khoảng 450.000đ
2 bàn chưa ai ra tiếp, 1 bàn chờ món      [Xem]
```

Bấm "Xem" mở danh sách 3 lượt, mỗi lượt có giờ, bàn, chờ bao lâu, nút xem clip (đã có `clip.mp4` theo khoảng thời gian). Ở **Quán lúc này**, không thêm gì: lời nhắc "chưa ai ra tiếp" đã có. Chỉ thêm một dòng nhỏ vào nhật ký khi có lượt bỏ về.

**Giọng đọc cho nhân viên:** không đọc. Khách đã đi, đọc lúc đó không giúp gì và gây ồn.

**Trợ lý nói gì** (công cụ mới `khach_bo_ve(ngay)`):

> Hôm nay có 3 bàn khách bỏ về, ước khoảng 450 nghìn. Hai bàn không ai ra chào, cả hai đều trong khoảng 12 giờ đến 12 giờ rưỡi, lúc đó chỉ có 1 người phục vụ. Anh xem lại clip bàn 5 nhé.

Kèm khối sự kiện có clip (khối đã có).

**Gợi ý ca sau** (thêm vào `goi_y.py`, cùng kiểu các gợi ý cũ): "3 bàn bỏ về quãng 12:00 đến 12:30 → ca sau thêm một người ra chào khách quãng này."

**Đo hiệu quả.** Theo dõi tỉ lệ bỏ về theo tuần. Mục tiêu sau 2 tuần dùng: giảm một nửa. Trên trang Ca hôm nay hiện so với trung bình 7 ngày trước ("ít hơn tuần trước 2 bàn").

**Kiểm tra độ đúng trước khi tin số:** xem lại 20 lượt "bỏ về" đầu tiên bằng clip, đếm bao nhiêu là thật. Dưới 70% đúng thì chưa hiện số tiền, chỉ hiện "có thể bỏ về".

### 3.2. Bàn ngồi không ra tiền

**Ý chính.** Một lượt bàn có phần khách đang ăn uống (ra tiền) và phần chết: chờ người ra tiếp, chờ món, chờ tính tiền, bàn bẩn chờ dọn, bàn sạch nhưng không ai ngồi giờ đông. Giờ cao điểm, mỗi phút chết là phút không bán được cho nhóm khách sau.

**Số liệu (theo ca, và chỉ tính trong giờ đông):**

| Số | Cách tính | Dữ liệu |
|---|---|---|
| Thời gian ngồi trung bình một lượt | giờ rời − giờ ngồi | `stage` |
| Lượt bàn trên mỗi bàn (vòng quay) | số lượt / số bàn, theo khung giờ | `stage` |
| Phút chờ ra tiếp, chờ món, chờ tính tiền | `prev_s` của bước tương ứng | `stage` |
| Phút bàn bẩn chưa dọn | từ `can_don` tới `da_don`/`trong` | `table` |
| **Giờ đông** | khung 30 phút có ít nhất 80% bàn có khách | `table` |
| Lượt khách có thể thêm (ước tính) | tổng phút chết trong giờ đông / thời gian ngồi trung bình | tính ra |

Con số cuối là con số chủ quán quan tâm: "Nếu bớt được nửa phần chờ trong giờ đông, quán có thể đón thêm khoảng **4 bàn**, tức khoảng **600.000đ** mỗi ngày". Luôn dùng "nửa phần chờ", không hứa bỏ hết.

**Màn hình.** Ở **Ca hôm nay**, thay vì nhiều biểu đồ, một thẻ dạng thanh ngang chia đoạn cho một lượt bàn trung bình:

```
Một bàn trung bình giờ đông: 52 phút
[chờ chào 4][chờ món 11][ ăn uống 27 ][chờ tính tiền 6][chờ dọn 4]
Chậm nhất: chờ món. Bớt nửa phần chờ ≈ thêm 4 bàn, khoảng 600.000đ/ngày
```

Đoạn chờ tô màu cảnh báo, đoạn ăn uống tô màu trung tính. Chỉ nêu **một** chỗ chậm nhất. Bấm vào một đoạn thì hiện 3 lượt tệ nhất của đoạn đó kèm clip.

Ở Quán lúc này: không thêm gì.

**Trợ lý nói gì** (công cụ mới `thoi_gian_chet(ngay)`):

> Giờ trưa nay mỗi bàn mất trung bình 11 phút chờ món, lâu nhất trong các bước. Nếu bếp ra món nhanh hơn chừng 5 phút thì trưa có thể đón thêm khoảng 4 bàn. Bàn 3 và bàn 7 chờ món lâu nhất.

Câu hỏi gợi ý mới trong Trợ lý: "Trưa nay bàn chậm ở đâu?"

**Đo hiệu quả.** Hai số theo tuần: vòng quay bàn trong giờ đông, và phút chờ trung bình mỗi lượt. Chủ quán đổi một thứ (thêm người, dọn nhanh hơn) thì trợ lý so tuần trước và tuần này. Không tự kết luận đổi gì gây ra thay đổi, chỉ nêu số.

**Giới hạn cần nói rõ:** "chờ món" chỉ có khi Gemini Decision đọc ảnh bàn (`--chup-ban`). Tắt thì thanh chỉ có 3 đoạn: chờ chào, ngồi, chờ dọn.

### 3.3. Mời thêm đúng lúc

**Ý chính.** Lời nhắc mềm mới cho nhân viên, chỉ bật khi quán **không đông**:

| Quán đang | Bàn ở bước | Ngồi quá | Nhắc nhân viên |
|---|---|---|---|
| Vắng (dưới 60% bàn có khách) | `finished` (ăn xong) | `upsell_s`, mặc định 8 phút | "Bàn 4 ăn xong một lúc rồi, mời thêm nước hoặc tráng miệng" |
| Vắng, quán cà phê | `served` | `refill_s`, mặc định 60 phút, và ảnh thấy cốc đã cạn | "Bàn 2 ngồi lâu, cốc đã cạn, mời ly thứ hai" |
| Đông (từ 80% bàn có khách) | `finished` | `wait_bill_s` (đã có) | Không mời thêm. Giữ lời nhắc "có thể chờ tính tiền" như hiện nay |

Giữa 60% và 80%: không nhắc gì thêm. Mỗi lượt bàn chỉ nhắc mời thêm **một lần**.

"Cốc đã cạn" cần thêm một câu hỏi cho Gemini Decision khi đọc ảnh bàn (`drinks_empty`). Chưa có câu hỏi này thì chỉ dùng nhánh `finished`.

**Cho nhân viên.** Hiện như một việc nhẹ trên app nhân viên (không chuông, không rung, đọc một lần, chậm, ngắn: "Bàn bốn, mời thêm món"). Việc có hai nút thay cho "Xong":
- **Khách gọi thêm**
- **Khách không gọi**

Không bấm sau 5 phút thì tự đóng, không tính gì. Đây là cách duy nhất để đo kết quả khi chưa có hoá đơn.

**Cài đặt.** Một công tắc "Nhắc mời thêm món khi quán vắng" trong mục Kết nối, quy tắc báo việc, tắt mặc định. Hai ô số `upsell_s`, `refill_s` nằm dưới công tắc, chỉ hiện khi bật.

**Trợ lý nói gì** (thêm vào công cụ báo cáo ca):

> Hôm nay nhắc mời thêm 9 lần, khách gọi thêm 4 lần. Nếu mỗi lần thêm khoảng 30 nghìn thì được khoảng 120 nghìn. Chị Lan mời 5 lần được 3.

Số tiền mỗi lần mời thêm là ô nhập thứ hai trong Cài đặt ("Một lần gọi thêm thường khoảng bao nhiêu", mặc định 30.000đ).

**Đo hiệu quả.** Tỉ lệ "khách gọi thêm" trên số lần nhắc có người bấm. Dưới 10% sau 2 tuần thì lời nhắc đang làm phiền, đề xuất chủ quán tắt. Quan sát thêm: số lời nhắc bị bỏ qua (không bấm), nếu trên một nửa thì giảm số lần nhắc.

## 4. Những gì phải thêm, gom lại

| Phần | Thêm gì |
|---|---|
| Máy chủ | `luot_ban.py` (ghép lượt bàn từ timeline); 2 công cụ trợ lý; 2 gợi ý mới trong `goi_y.py`; lời nhắc `upsell` trong `giai_doan.py`; loại việc nhẹ `upsell` với kết quả `yes`/`no` |
| Cài đặt | `avg_ticket` (giá trị một bàn), `upsell_value`, công tắc `upsell_on`, `upsell_s`, `refill_s` |
| Gemini Decision | Một câu hỏi mới `drinks_empty` khi đọc ảnh bàn (không bắt buộc cho bản đầu) |
| Giao diện | Ca hôm nay: thẻ "Khách bỏ về", thẻ "Một bàn trung bình"; app nhân viên: hai nút "Khách gọi thêm / không gọi"; Cài đặt: 2 ô tiền, 1 công tắc |
| Test | Ghép lượt bàn từ chuỗi sự kiện giả; định nghĩa bỏ về; ngưỡng đông/vắng; nhắc mời thêm chỉ một lần mỗi lượt |

Không thêm trang mới, không thêm biểu đồ mới ngoài thanh chia đoạn.

## 5. Rủi ro

| Rủi ro | Hậu quả | Cách giảm |
|---|---|---|
| Camera bỏ sót hoặc nhầm giai đoạn (ngưỡng mới chỉnh trên 1 clip) | Báo "bỏ về" sai, số tiền sai, chủ quán mất tin | Gắn clip với từng số; kiểm 20 lượt đầu; dưới 70% đúng thì giấu số tiền |
| Một nhóm đổi bàn | Bị tính là bỏ về | Ngồi dưới 2 phút không tính; bàn bên cạnh có lượt mới trong 1 phút sau thì không tính |
| Số tiền là ước tính từ một con số | Chủ quán hiểu là doanh thu thật | Luôn ghi "khoảng", "ước tính"; thay bằng hoá đơn khi có |
| Mời thêm làm phiền khách và nhân viên | Khách khó chịu, nhân viên bỏ qua lời nhắc | Tắt mặc định, chỉ khi vắng, một lần mỗi lượt, đo tỉ lệ và đề xuất tắt |
| Trạng thái giai đoạn nằm trong RAM | Máy chủ khởi động lại thì lượt đang dở bị cắt đôi | Lượt cắt đôi đánh dấu "chưa xong", không tính vào bỏ về |
| Dùng số để trách nhân viên | Không khí xấu, nhân viên nghỉ (66% nghỉ năm đầu) | Nêu số theo khung giờ và bàn trước; theo người chỉ ở chi tiết, và chỉ với số tích cực (mời thêm thành công) |
| Demo là 14/11 | Không kịp làm cả ba | Nếu làm trước demo: chỉ #1 và thẻ "Một bàn trung bình" của #2, chạy trên clip mẫu |

## 6. Ngoài phạm vi

- Nhận khách quen theo mặt (#9): cần đồng ý rõ của khách theo luật dữ liệu cá nhân; để sau, cần ý kiến luật.
- Đếm khách ở cửa (#8): cần thêm vùng cửa và cách đếm vào/ra.
- Xếp ca theo tuần (#5), chỗ ngồi bị phí (#6), giờ vàng (#7): làm sau khi có 2 tuần dữ liệu thật.
- Tiền thật từ hoá đơn, món bán chạy: thuộc phiên hoá đơn.
- Theo dõi nhân viên đứng không, dùng điện thoại: không làm (đụng an ninh và quyền riêng tư nhân viên).
- Gửi bản tin qua Zalo hay thông báo đẩy: ý #4, spec riêng.

## 7. Câu hỏi cần chủ quán/người dùng trả lời

1. Có muốn làm gì trước demo 14/11 không, hay spec này là việc sau demo?
2. "Mời thêm" có hợp với quán thử nghiệm không (quán cà phê hay quán ăn)?
3. Đồng ý dùng một con số "giá trị một bàn" để ước tính tiền cho tới khi có hoá đơn?

## Nguồn

- Presto Vision, khách bỏ về: https://presto.com/?p=3083
- TableWatch (DifiNative): https://embeddedcomputing.com/technology/iot/edge-computing/transforming-restaurant-operations-with-ai-tablewatch-from-difinative-powered-by-intel-edge-processing
- Sciforce, vùng bàn cố định trên camera: https://www.sciforce.solutions/case-studies/computer-vision-restaurant-service-optimization
- Safari AI: https://getsafari.ai/post/computer-vision-restaurants
- Lightspeed 2025, khách bỏ về vì chờ: https://www.lightspeedhq.com/news/dinner-never-mind-a-third-of-diners-are-walking-out-before-the-meal-arrives-due-to-inconsistent-service/
- Mời thêm món ở drive-thru: https://www.fastcasual.com/blogs/your-drive-thru-isnt-broken-its-invisible/
- Quay bàn hay tráng miệng: https://bepoz.com/?p=220
- Vòng quay bàn và doanh thu: https://buttondown.com/ringfoods/archive/table-turn-rate-and-the-phone-bottleneck-what-the/
- Xếp ca theo dự báo: https://www.casestudies.com/company/fourth/case-study/how-pf-changs-reduced-their-labor-cost-by-1-percent-across-more-than-200-locations
- F&B Việt Nam 2025: https://vneconomy.vn/doanh-nghiep-fb-doi-mat-voi-giai-doan-thanh-loc-tu-nhien.htm
- Dữ liệu sinh trắc học là dữ liệu nhạy cảm: https://luatminhkhue.vn/du-lieu-ve-sinh-trac-hoc-la-dlcn-nhay-cam-hay-dlcn-co-ban.aspx
