# Phòng chat của quán, kèm hoá đơn và chuyển khoản đọc bằng Gemini

Ngày: 13/11/2026. Trạng thái: **đã làm bản tối thiểu (mục 13.1)**, theo góp ý bản 3 dưới đây.

Bản 3 (đã làm):
- **Luôn có màn kết quả và nút "Xác nhận và gửi".** Không tự gửi, không tự đóng. Chưa bấm xác nhận thì chưa lưu gì.
- **Thanh tiến trình thật:** phần tải ảnh lên đo bằng tiến độ thật của XHR (0–30%), phần chờ đọc ảnh chạy chậm dần tới tối đa 94%, có kết quả thì lên 100%. Kèm vạch quét chạy trên ảnh và dòng chữ theo chặng.
- **Không hiện chữ "Gemini" ở bất cứ đâu trên giao diện** (không "Gemini đọc trong … giây", không "Gemini chưa chắc"). Đọc lỗi thì chỉ ghi "Chưa đọc được ảnh, nhập tay giúp".
- **Bàn chọn bằng một chạm**, vì hoá đơn thường không in số bàn: hàng nút bàn, bàn đã ăn xong lên đầu (ghi "ăn xong"), rồi bàn đang có khách, cuối cùng là "Mang về". Nếu đúng một bàn đang ở giai đoạn "ăn xong" thì chọn sẵn bàn đó; ảnh chuyển khoản có ghi bàn trong nội dung thì lấy bàn đó.
- Bàn **không bắt buộc**, để trống cũng được (đã bỏ nút "Mang về").
- Trợ lý trong phòng chat tên **Tam** (không dấu). Gọi bằng "@Tam" hoặc "Tam ơi"; "@AI" vẫn nhận. Chữ "tam" giữa câu hay "@Tâm" (tên nhân viên) thì không gọi.
- Chọn loại bằng ô chọn (Chuyển khoản, Hoá đơn, Phiếu thu, Ảnh thường), vì 4 nút liền không đủ chỗ trên điện thoại.

Bản 2:

Bản 2 sửa theo góp ý:
- AI **không đọc to** gì cả. Không có giọng đọc cho tin chat, cũng không có "bản ngắn để đọc".
- Ảnh chụp (hoá đơn, **ảnh chuyển khoản**, phiếu thu) được phân tích bằng OCR (Gemini nhìn ảnh). Màn hình có hiệu ứng quét đàng hoàng. Kết quả **gửi vào phòng chat** gồm ảnh và thẻ thông tin để mọi người đọc, đồng thời được lưu vào hệ thống.
- "Tiền chỉ tới chủ" để sau. Bản này không lọc người nhận.

Hai phần:
- **(a) Phòng chat** giữa nhân viên và chủ quán. AI ngồi trong phòng: tóm tắt, trả lời câu hỏi về ca, nhắc việc, nói gọn một tin khó hiểu. Chỉ hiện chữ, không đọc to.
- **(b) Ảnh thanh toán.** Nhân viên chụp hoá đơn, phiếu thu hoặc ảnh chuyển khoản. Gemini rút ra số tiền, giờ, bàn, món (hoá đơn) hoặc ngân hàng, người chuyển, nội dung, mã giao dịch (chuyển khoản). Ảnh và thẻ thông tin hiện trong phòng chat, số liệu vào phần doanh thu, đối chiếu được với lượt khách camera thấy (ví dụ: bàn 3 có khách 40 phút mà không có thanh toán nào).

---

## 1. Những gì đang có và sẽ dùng lại

| Đang có | Ở đâu | Dùng lại thế nào |
|---|---|---|
| Đẩy thay đổi về giao diện bằng SSE: `Hub.publish(event, data)` → mọi kết nối `GET /api/stream` | `server/hub.py:184`, `server/app.py:156` | Thêm sự kiện `chat` (tin mới hoặc tin đổi) |
| Dòng thời gian SQLite, ghi theo lô, nuốt lỗi | `server/timeline.py` | Học theo cách làm cho kho mới. Đọc sự kiện `stage` (seated → left, có `people`) để dựng **lượt khách** |
| Giai đoạn bữa ăn: seated, greeted, served, finished, left; nhắc "đã ăn xong khá lâu, có thể đang chờ tính tiền" | `server/giai_doan.py` | Lượt khách để đối chiếu với thanh toán |
| Gọi Gemini có ảnh và JSON schema: `Gemini.json(parts, schema, image=True)` | `server/gemini.py:241` | OCR ảnh thanh toán |
| Trợ lý chủ quán (Google ADK + Gemini, có đường "rules" khi không có AI) | `server/tro_ly.py` | AI trong phòng là một chế độ của `TroLy`, trả về chữ thuần |
| `Roll` (số lăn), `AnimatedList` (danh sách có hiệu ứng vào/ra) | `src/app/motion.tsx` | Số tiền lăn lên khi đọc xong; tin mới trượt vào phòng |
| App nhân viên: một màn hình danh sách việc | `src/app/StaffPhone.tsx` | Thêm thanh dưới 2 mục và nút chụp |
| Màn hình chủ: Quán lúc này, Trợ lý, Ca hôm nay, Cài đặt | `src/app/OwnerShell.tsx:22` | Thêm mục "Nhắn nhóm". Doanh thu là một phần của "Ca hôm nay" |

Lưu ý: **số lượt khách (`seat`) đếm trong RAM**, khởi động lại thì đếm lại từ 1. Đối chiếu nhận diện lượt khách bằng (bàn, giờ ngồi), không bằng `seat`.

---

## 2. Luồng người dùng

### 2.1 Nhân viên (điện thoại)

Màn hình ca hiện tại giữ nguyên, thêm thanh dưới:

```
┌──────────────────────────────┐
│ (●) Lan · Phục vụ · 2 việc   │
│                              │
│  [ thẻ việc như hiện nay ]   │
│                              │
├──────────────────────────────┤
│  Việc (2)    Nhóm (3)   [📷] │   ← nút chụp luôn ở góc, một chạm
└──────────────────────────────┘
```

- **Việc**: như hiện nay, không đổi.
- **Nhóm**: phòng chat của quán. Số tin chưa đọc. Tin chat **không đọc to**, không kêu chuông việc. Chỉ rung nhẹ một lần khi có tin gửi đích danh mình (không rung với tin cả quán).
- **📷**: mở camera sau (`<input type="file" accept="image/*" capture="environment">`, chạy cả trên http). Trong mục Nhóm cũng có nút 📷 cạnh ô nhập.

**Chụp và gửi một ảnh thanh toán:**

```
1. Chụp xong                2. Đang quét (2–6 giây)        3. Xem lại rồi gửi
┌──────────────────┐       ┌──────────────────┐           ┌──────────────────────────┐
│  [ ảnh vừa chụp ]│       │ ┌──────────────┐ │           │ [ảnh nhỏ]  CHUYỂN KHOẢN  │
│                  │  →    │ │▓▓ vạch quét ▓│ │     →     │ Số tiền   245.000 đ      │
│ Bàn: [3 ▾] (tuỳ) │       │ │  khung chữ    │ │           │ Ngân hàng Vietcombank    │
│ [Quét] [Chụp lại]│       │ │  sáng dần     │ │           │ Người chuyển NGUYEN V A  │
└──────────────────┘       │ └──────────────┘ │           │ Nội dung  BAN 3          │
                           │ Đang đọc số tiền…│           │ Giờ       14:32          │
                           │ ▸ Số tiền 245.000│ (hiện dần)│ Bàn       [ 3 ▾]         │
                           └──────────────────┘           │ ⚠ Giờ trên ảnh mờ        │
                                                          │ [ Gửi vào nhóm ] [ Sửa ] │
                                                          └──────────────────────────┘
```

**Hiệu ứng ở bước 2** (làm bằng CSS, không thêm thư viện):
1. Ảnh thu vào khung bo góc, nền tối dần.
2. Một vạch sáng chạy từ trên xuống dưới ảnh, lặp lại cho tới khi có kết quả (1,2 giây mỗi lượt).
3. Dòng trạng thái đổi theo thời gian: "Đang tìm số tiền…" → "Đang đọc chi tiết…". Đây là chữ chờ, không giả vờ tiến độ thật.
4. Kết quả về: vạch dừng, các **khung sáng** hiện đúng vị trí chữ Gemini tìm thấy trên ảnh (Gemini trả toạ độ từng ô, xem 6.2). Các dòng thông tin trượt vào lần lượt, mỗi dòng cách nhau 80 ms. Số tiền lăn lên bằng `Roll`.
5. Ô chưa chắc viền vàng và hơi rung một lần.
6. `prefers-reduced-motion`: bỏ vạch quét và trượt, chỉ hiện chữ "Đang quét…" rồi hiện kết quả.

**Bước 3:**
- **Gửi vào nhóm**: một chạm. Ảnh và thẻ thông tin thành một tin trong phòng (2.2). Ô chưa chắc vẫn gửi được, thẻ hiện dấu "chưa chắc" cho tới khi có người xác nhận.
- **Sửa**: chạm vào ô để sửa. Bàn chọn từ danh sách bàn.
- Gemini lỗi hoặc không có khoá: bước 3 hiện form trống 2 ô **Số tiền** và **Bàn**. Vẫn gửi được, thẻ ghi "nhập tay".
- Ảnh không phải thanh toán: "Ảnh này không giống hoá đơn hay chuyển khoản. Gửi như ảnh thường?" (gửi vào nhóm không có thẻ).

### 2.2 Phòng chat (cùng giao diện cho chủ và nhân viên)

```
┌────────────────────────────────────────────────────────────┐
│ Nhắn nhóm                                   [Tóm tắt ca]   │
├────────────────────────────────────────────────────────────┤
│ 14:02  Lan     Bàn 5 xin thêm đá                           │
│ 14:03  Chủ     @Minh mang đá ra bàn 5 giúp                 │
│ 14:32  Lan     ┌───────────────────────────────────────┐   │
│                │ [ảnh]  Chuyển khoản · 245.000 đ        │   │
│                │        Vietcombank · NGUYEN V A        │   │
│                │        "BAN 3" · 14:32 · Bàn 3         │   │
│                │        ✓ Khớp lượt khách bàn 3         │   │
│                └───────────────────────────────────────┘   │
│ 14:35  Hùng    ┌───────────────────────────────────────┐   │
│                │ [ảnh]  Hoá đơn #0127 · 1.180.000 đ     │   │
│                │        Bàn 7 · 9 món ▸                 │   │
│                │        ⚠ Tổng chưa chắc  [Xác nhận]    │   │
│                └───────────────────────────────────────┘   │
│ 14:40  Hùng    @AI bàn 3 vào lúc nào?                      │
│ 14:40  AI      Bàn 3 có khách từ 13:41, 4 người, đã có món.│
├────────────────────────────────────────────────────────────┤
│ Gửi tới: [Cả quán ▾]  [ nhập tin…             ] [📷] [Gửi] │
└────────────────────────────────────────────────────────────┘
```

- Chạm ảnh: xem to, có các khung sáng chỗ chữ đã đọc.
- Chạm thẻ: mở chi tiết (món, mã giao dịch, lịch sử sửa). Người gửi và chủ sửa được; ai sửa đều ghi lại, thẻ hiện "đã sửa".
- **Xác nhận**: bất kỳ ai trong ca bấm được; thẻ hết dấu "chưa chắc".
- Dòng cuối của thẻ là kết quả đối chiếu với camera, cập nhật trực tiếp: "✓ Khớp lượt khách bàn 3", "Camera không thấy khách bàn 9 (mang về?)", hoặc không có gì nếu chưa xác định.

### 2.3 Chủ quán: "Ca hôm nay" thêm phần "Tiền"

Dưới "Khách", trên "Nhân viên":

```
Tiền
┌─────────────┬─────────────┬─────────────┬────────────────┐
│ Đã thu      │ Thanh toán  │ TB mỗi khách│ Cần xem lại    │
│ 8.450.000 đ │ 41 (12 CK)  │ 96.000 đ    │ 3              │
└─────────────┴─────────────┴─────────────┴────────────────┘
[biểu đồ cột: tiền theo giờ, chồng lên số lượt khách theo giờ]

Cần xem lại
  Bàn 3 · 13:02–13:44 · 4 khách · chưa thấy thanh toán      [Xem lượt] [Gắn]
  Chuyển khoản 152.000 đ · bàn 9 · camera không thấy khách   [Xem]  (có thể là mang về)
  Hoá đơn #0127 · tổng chưa chắc, chưa ai xác nhận           [Xem]
```

- "Xem lượt" mở dòng thời gian của bàn đó (`GET /api/timeline?table=`).
- "Gắn" chọn một thanh toán chưa gắn ở gần giờ đó, hoặc đánh dấu "không thu tiền" kèm lý do. Xong thì dòng biến mất.
- Bấm một con số mở danh sách thanh toán của ngày, có ảnh, lọc theo nhân viên, bàn, loại.
- Trợ lý riêng của chủ hỏi được: "hôm nay thu bao nhiêu", "bàn nào chưa có thanh toán".

---

## 3. AI trong phòng chat: khi nào nói, nói gì

Nguyên tắc: **AI chỉ nói khi được gọi hoặc khi đã hẹn trước.** Chỉ bằng chữ trong phòng, không đọc to. Không bình luận tin của người khác, không tự nhắc việc camera (việc camera đã có thẻ việc và giọng đọc riêng).

| Khi | AI làm gì |
|---|---|
| Tin có `@AI` (hoặc bắt đầu bằng "AI ơi") | Trả lời một tin, tối đa khoảng 3 câu |
| Bấm **Tóm tắt ca** | Một tin tóm tắt: lượt khách, tổng đã thu, chờ lâu nhất, việc còn mở, các tin đáng chú ý trong phòng |
| "@AI nhắc Minh 15:00 kiểm kho đá" | AI xác nhận "Sẽ nhắc Minh lúc 15:00"; tới giờ gửi tin nhắc đích danh Minh |
| Có người bấm **Nói gọn** trên một tin | AI viết lại tin đó thành một câu tiếng Việt rõ ý (tin dài, viết tắt, lẫn tiếng khác). Chỉ người bấm thấy |

Không có trường hợp nào khác. AI **không** đăng gì khi có ảnh thanh toán (thẻ thông tin do máy chủ dựng, không phải tin của AI). Giới hạn cứng: AI tự gửi (nhắc đã hẹn) tối đa 6 tin/giờ.

**Làm thế nào:**
- `TroLy` chạy **chế độ phòng**: một phiên ADK cho mỗi ngày (`phong-YYYY-MM-DD`), công cụ đọc ca (`so_lieu_ca`, `trang_thai_ban`, `ban_dang_the_nao`, `dong_thoi_gian`, `tim_su_kien`), thêm `thanh_toan_hom_nay()` và `hen_nhac(nguoi, gio, viec)`. Không có công cụ hiển thị khối; trả chữ thuần.
- Ngữ cảnh kèm theo: 20 tin gần nhất (chữ và thẻ thanh toán dạng chữ, không gửi ảnh), tên và vai trò người hỏi.
- Không có AI (thiếu khoá, kie.ai, ADK lỗi): `@AI` trả lời bằng `tra_loi_rules` có sẵn (cắt còn chữ). Tóm tắt dùng `tom_tat(hub)`. "Nói gọn" tắt.
- Nhắc đã hẹn lưu trong kho, `Hub.tick` (mỗi giây) gửi khi tới giờ; khởi động lại không mất.

---

## 4. Dữ liệu

Một tệp SQLite mới `DATA_DIR/quan.db`, cùng cách với `timeline.db` (mở, ghi, đóng; lỗi in một lần, không làm hỏng Hub). Tách khỏi `timeline.db` vì tin và thanh toán **sửa được**, còn dòng thời gian chỉ thêm.

Ảnh: `DATA_DIR/chat/YYYY-MM-DD/<id>.jpg`, điện thoại thu nhỏ còn cạnh dài 1600 px, JPEG 0,85 (khoảng 250 KB).

### 4.1 Tin nhắn `messages`

| Trường | Kiểu | Ghi chú |
|---|---|---|
| id | int tự tăng | Cũng là con trỏ cho `since` |
| ts, day | ms, 'YYYY-MM-DD' | Giờ máy chủ, ngày theo giờ Việt Nam |
| sender | text | id nhân viên, `chu` hoặc `ai` |
| to | text JSON | `["*"]` cả quán, hoặc danh sách id |
| kind | text | `text`, `photo` (ảnh thường), `payment`, `summary`, `reminder`, `ai` |
| text | text | ≤ 1000 ký tự; với `payment` là dòng tóm tắt để tìm kiếm |
| image | text \| null | Tên tệp ảnh |
| payment_id | int \| null | Trỏ sang `payments` |
| reply_to | int \| null | |

### 4.2 Thanh toán `payments`

| Trường | Kiểu | Ghi chú |
|---|---|---|
| id | int | |
| ts, day | | Lúc gửi |
| staff | text | Người chụp |
| status | text | `scanning` → `unsure` (có ô chưa chắc) hoặc `ok`; `void` khi huỷ (không xoá) |
| type | text | `chuyen_khoan`, `hoa_don`, `phieu_thu`, `khac` |
| amount | int \| null | Đồng |
| paid_at | text \| null | 'HH:MM' trên ảnh |
| table | text \| null | Tên bàn trong vùng bàn |
| items | JSON | Hoá đơn: `[{name, qty, price}]` |
| bank, sender_name, memo, txn_id | text \| null | Chuyển khoản: ngân hàng, tên người chuyển, nội dung, mã giao dịch |
| receipt_no | text \| null | Số hoá đơn |
| boxes | JSON | Toạ độ chữ trên ảnh cho từng ô (để vẽ khung sáng) |
| ocr | JSON | Kết quả Gemini **nguyên gốc** + độ chắc từng ô + `ms`, `model` |
| visit | text \| null | Lượt khách đã gắn: `"<bàn>@<giờ ngồi ms>"` |
| visit_by | text \| null | `auto` hoặc người gắn tay |
| confirmed_by, note | text \| null | |

Mỗi lần sửa thêm một dòng `payment_edits(payment_id, ts, by, field, old, new)`.

### 4.3 Khác

- `reminders(id, at, to, text, made_by, sent_at, cancelled)`.
- `visit_notes(visit, by, reason, ts)`: lượt khách đánh dấu "không thu tiền".
- **Lượt khách không có bảng riêng**: dựng từ `timeline` (kind `stage`): `seated` mở lượt, `left` đóng lượt. Lượt gồm bàn, giờ ngồi, giờ rời, số khách lớn nhất, đã tới `finished` chưa.

---

## 5. API

Dưới `/api`, trả JSON; ghi thêm vào `server/API.md` khi làm.

| Phương thức | Đường dẫn | Mô tả |
|---|---|---|
| GET | `/chat?since=<id>&limit=50` | Tin hôm nay sau id đó, kèm thẻ thanh toán nếu có |
| POST | `/chat` | `{from, text, to?, reply_to?}` → tin đã lưu. Có `@AI` thì máy chủ trả lời sau (không chặn) |
| POST | `/chat/scan?staff=<id>&table=<bàn?>` | Thân là ảnh JPEG (≤ 3 MB). OCR chạy luôn, **chờ tối đa 20 giây**, trả `{scan_id, payment}` để điện thoại hiện bước 3. Chưa đăng vào phòng |
| POST | `/chat/scan/{scan_id}/send` | `{from, to?, sửa?: {...}}` → đăng tin `payment` (hoặc `photo`) vào phòng |
| GET | `/chat/image/{name}` | Ảnh |
| PATCH | `/payments/{id}` | `{by, amount?, table?, paid_at?, ..., confirm?: true}` → sửa và/hoặc xác nhận; phát lại tin để thẻ cập nhật |
| POST | `/payments/{id}/void` | `{by, reason}` |
| POST | `/chat/{id}/gon` | `{by}` → `{short}` |
| POST | `/chat/summary` | AI đăng tin tóm tắt |
| GET / DELETE | `/chat/reminders[/{id}]` | Xem, huỷ nhắc |
| GET | `/revenue?day=` | Tổng, theo giờ, theo loại, theo nhân viên, danh sách "Cần xem lại" |
| POST | `/visits/{visit}/note` | `{by, reason}` hoặc `{payment_id}` gắn tay |

Ảnh đã quét mà không gửi: giữ 1 giờ rồi xoá.

**SSE:** thêm sự kiện `chat` với `{message, payment?}`. Dùng cho tin mới, thẻ sửa/xác nhận, và kết quả đối chiếu đổi. Gửi tới mọi kết nối (chưa lọc người nhận, để sau). Không gửi tin cũ trong `snapshot`; app gọi `GET /chat` khi mở mục Nhóm và sau mỗi lần kết nối lại.

---

## 6. OCR bằng Gemini

### 6.1 Gọi thế nào

- Một lần `Gemini.json([prompt, ảnh], PAYMENT_SCHEMA, image=True)`, ảnh mức **HIGH**. Model mặc định của máy chủ; cho phép đặt riêng bằng `GEMINI_OCR_MODEL` nếu đo thấy cần.
- Quá 20 giây hoặc lỗi: trả form nhập tay. Có `CircuitBreaker` riêng (3 lỗi liền thì ngừng 60 giây) để lỗi OCR không chặn việc kiểm tra cảnh báo camera.
- kie.ai: chưa hỗ trợ ở bản này, đi đường nhập tay.

### 6.2 Schema trả về

```json
{
  "loai": "chuyen_khoan | hoa_don | phieu_thu | khac",
  "so_tien":      {"gia_tri": 245000,         "chac": "ro | mo | khong_thay", "box": [y0, x0, y1, x1]},
  "gio":          {"gia_tri": "14:32",         "chac": "...", "box": [...]},
  "ban":          {"gia_tri": "3",             "chac": "...", "box": [...]},
  "ngan_hang":    {"gia_tri": "Vietcombank",   "chac": "...", "box": [...]},
  "nguoi_chuyen": {"gia_tri": "NGUYEN VAN A",  "chac": "...", "box": [...]},
  "noi_dung":     {"gia_tri": "BAN 3",         "chac": "...", "box": [...]},
  "ma_giao_dich": {"gia_tri": "FT2431...",     "chac": "...", "box": [...]},
  "so_hoa_don":   {"gia_tri": "0127",          "chac": "...", "box": [...]},
  "mon": [{"ten": "Cà phê sữa", "sl": 2, "gia": 30000}]
}
```

`box` theo quy ước của Gemini (0–1000, `[y0, x0, y1, x1]`), dùng để vẽ khung sáng; thiếu thì bỏ khung, không ảnh hưởng gì khác.

Prompt nói rõ: tiền Việt Nam, dấu chấm phân cách nghìn ("245.000" là 245000). Hoá đơn: lấy dòng "Tổng cộng / Thành tiền / Khách trả", không lấy "Tiền khách đưa" hay "Tiền thừa". Chuyển khoản: lấy số tiền **đã chuyển**, không lấy số dư; bàn đọc từ nội dung chuyển khoản nếu có ("BAN 3", "b3"). Ô nào không thấy thì `null`, **không đoán**.

### 6.3 Máy chủ tự kiểm

`status = ok` chỉ khi đủ tất cả:
1. `so_tien` có, `chac = ro`, trong khoảng 5.000 đ – 50.000.000 đ.
2. Hoá đơn có món: tổng các món lệch số tiền không quá 2%.
3. `ban` (nếu có) là tên một bàn đã khai.
4. Không trùng: chưa có thanh toán cùng `ma_giao_dich` hoặc `so_hoa_don` trong ngày, hoặc cùng số tiền và cùng bàn trong 3 phút. Trùng thì cảnh báo ngay ở bước 3 ("Có thể đã gửi rồi lúc 14:30") nhưng vẫn cho gửi.

Thiếu điều nào thì `unsure` kèm lý do hiện trên thẻ.

---

## 7. Đối chiếu với camera

Chạy mỗi khi có thanh toán mới hoặc sửa, mỗi khi một lượt khách đóng, và khi mở "Ca hôm nay".

**Gắn thanh toán vào lượt khách**, theo thứ tự:
1. Có bàn: lượt của bàn đó mà khoảng [giờ ngồi − 5 phút, giờ rời + 15 phút] chứa giờ trên ảnh (hoặc giờ gửi). Nhiều lượt khớp thì lấy lượt rời gần nhất.
2. Không có bàn: chỉ gắn khi đúng **một** lượt rời trong ±10 phút và lượt đó chưa có thanh toán.
3. Một lượt nhiều thanh toán được (tách bill, nửa tiền mặt nửa chuyển khoản). Một thanh toán chỉ thuộc một lượt.
4. Người gắn tay luôn thắng máy.

**Danh sách "Cần xem lại":**

| Loại | Điều kiện | Câu hiện |
|---|---|---|
| Lượt không thấy thanh toán | Lượt dài ≥ `visit_min_s` (mặc định 10 phút), đã rời ≥ 15 phút, không có thanh toán, chưa đánh dấu "không thu tiền" | "Bàn 3 · 13:02–13:44 · 4 khách · chưa thấy thanh toán" |
| Thanh toán không thấy khách | Có bàn nhưng không lượt nào khớp | "camera không thấy khách (có thể là mang về)" |
| Chưa chắc | `unsure` quá 30 phút chưa ai xác nhận | "tổng chưa chắc, chưa ai xác nhận" |

Thêm: tiền trung bình mỗi khách, tiền theo giờ đặt cạnh lượt khách theo giờ, tỉ lệ chuyển khoản.

Chữ trung tính: "chưa thấy thanh toán", không dùng "thất thoát" hay "gian lận". Camera vẫn sót và lượt khách có thể bị tách đôi khi người che; người quyết định là chủ. Danh sách này không đăng vào phòng chat.

---

## 8. Ba cách làm

### Cách A: thanh toán là một tin trong phòng chat, dữ liệu có cấu trúc đi kèm (**chọn**)
Chụp → quét → gửi vào phòng thành một tin có ảnh và thẻ. Thẻ trỏ sang bảng `payments` có cấu trúc, dùng cho doanh thu và đối chiếu.
- **Được:** đúng cách quán đang làm (chụp chuyển khoản gửi nhóm Zalo), mọi người thấy ngay ai thu gì; một luồng duy nhất; dùng lại SSE, TroLy, `Gemini.json`, timeline.
- **Mất:** quán đông có thể 100+ thanh toán mỗi ngày, phòng nhiều thẻ. Giảm bằng thẻ gọn (2 dòng) và nút lọc "Chỉ tin nhắn" trong phòng. Số tiền ai trong nhóm cũng thấy (đã đồng ý để sau).

### Cách B: thanh toán có chỗ riêng, không vào phòng
- **Được:** phòng chat sạch, tiền riêng tư ngay.
- **Mất:** không đúng mong muốn "gửi vô để họ đọc được"; thêm một màn hình cho nhân viên.

### Cách C: dịch vụ ngoài (Firestore realtime, Document AI)
- **Được:** đồng bộ nhiều máy chủ, mẫu hoá đơn có sẵn.
- **Mất:** cài thêm gói, thêm tài nguyên cloud và khoá; Document AI không phải Gemini (cuộc thi bắt buộc Gemini); chưa chắc đọc ảnh chuyển khoản tiếng Việt tốt hơn. Không kịp, không cần ở quy mô một quán.

**Chọn A.** Khớp thói quen của quán, ít màn hình nhất, không thêm gói.

---

## 9. Quyền riêng tư và an toàn

- **Tiền chưa giới hạn người xem** (để sau theo yêu cầu). Mọi người trong phòng thấy thẻ thanh toán. Hệ thống vẫn chưa có đăng nhập (ADR-0007): ai có địa chỉ máy chủ đều đọc được phòng chat và ảnh. Việc kế tiếp nên là mã PIN của quán.
- **Ảnh chuyển khoản có tên và đôi khi số tài khoản của khách.** Chỉ gửi cho Gemini, không gửi đâu khác. Thẻ trong phòng chỉ hiện tên người chuyển, không hiện số tài khoản (Gemini không trả số tài khoản). Ảnh giữ 90 ngày rồi xoá, số liệu giữ lại.
- **Gói Gemini miễn phí** có thể dùng dữ liệu để cải thiện model. Ảnh thanh toán thật nên chạy bằng khoá trả phí hoặc Vertex AI. Ghi vào hướng dẫn cài đặt.
- **"Chưa thấy thanh toán" không gắn tên nhân viên** và không đăng vào phòng.
- Chat giữ 30 ngày. Không ghi khoá Gemini ra nhật ký hay tin nhắn.

---

## 10. Cách test

**Máy chủ (pytest, Gemini giả như các test hiện có):**
- `test_chat.py`: gửi, lấy `since`, đích danh/cả quán; `@AI` gọi TroLy chế độ phòng; AI không tự đăng khi có ảnh thanh toán; hẹn nhắc tới giờ có tin `reminder`; khởi động lại không mất nhắc; tối đa 6 tin/giờ.
- `test_quet.py`: Gemini giả trả: chuyển khoản đủ và chắc → `ok`; hoá đơn tổng lệch món → `unsure`; trùng mã giao dịch → cảnh báo; lấy nhầm số dư thay số tiền (schema có cả hai) → máy chủ giữ đúng ô; lỗi hoặc quá giờ → form nhập tay; ngắt mạch sau 3 lỗi; sửa ghi `payment_edits`; huỷ là `void`; ảnh quét không gửi bị xoá sau 1 giờ.
- `test_doi_chieu.py`: dòng thời gian giả (bàn 3 ngồi 13:02, rời 13:44), không thanh toán → "chưa thấy thanh toán"; thêm chuyển khoản nội dung "BAN 3" lúc 13:40 → hết; lượt 5 phút bỏ qua; bàn 9 không lượt → "không thấy khách"; tách bill; khởi động lại (seat đếm lại) vẫn khớp đúng lượt.

**Đo độ chính xác OCR** (giống `vision-test/do_chinh_xac.py`): 30 ảnh thật gồm ảnh chuyển khoản của 5–6 ngân hàng/ví phổ biến, hoá đơn in nhiệt, phiếu viết tay, ảnh nghiêng, tối. Mỗi ảnh có đáp án tay. Đo tỉ lệ đúng số tiền, đúng bàn, và **tỉ lệ sai mà vẫn báo `ro`**. Mục tiêu: số tiền đúng ≥ 95%, sai-mà-chắc ≤ 2%. Không đạt thì mọi thẻ đều phải xác nhận tay.

**Giao diện:** Android thật qua wifi (http): chụp, xem hiệu ứng quét, sửa, gửi; bật "giảm chuyển động" của máy; mất mạng giữa lúc quét; nhận tin khi đang ở mục Việc (không làm mất thẻ việc, không phát tiếng). Màn chủ: sáng/tối, rộng 375 px.

---

## 11. Rủi ro

| Rủi ro | Giảm thế nào |
|---|---|
| OCR đọc sai số tiền mà tự tin, hoặc lấy số dư thay số tiền chuyển | Prompt tách rõ; máy chủ tự kiểm (6.3); khung sáng cho người xem thấy chữ nào đã lấy; lưu kết quả gốc và mọi lần sửa; bộ đo ở mục 10 |
| Ảnh chuyển khoản giả hoặc sửa ảnh | Ngoài khả năng của OCR. Thẻ ghi "theo ảnh", không phải "đã nhận tiền". Đối soát với sao kê ngân hàng nằm ngoài phạm vi |
| Đối chiếu báo nhầm (camera tách lượt, ghép bàn, đổi bàn) | Ngưỡng 10 phút + chờ 15 phút sau khi rời; chữ trung tính; chủ đánh dấu một chạm; không đăng vào phòng |
| Phòng ngập thẻ thanh toán giờ cao điểm | Thẻ gọn 2 dòng; nút lọc "Chỉ tin nhắn"; tin chat không phát tiếng |
| Chờ OCR lâu (Gemini 2–6 giây, có lúc hơn) | Hiệu ứng quét che thời gian chờ; quá 20 giây chuyển sang nhập tay; nhân viên có thể bấm "Gửi luôn, sửa sau" |
| SQLite trên bucket gắn làm `DATA_DIR` ở Cloud Run | Một instance (đã vậy); mở-ghi-đóng ngắn như `timeline.db`. Nhiều quán thì chuyển Firestore (ADR mới) |
| Đụng code các phiên khác (`hub.py`, `tro_ly.py`, `StaffPhone.tsx`) | Code mới ở tệp riêng (`server/chat.py`, `server/quet.py`, `server/doi_chieu.py`, `src/app/Team.tsx`, `src/app/Scan.tsx`); chỉ sửa nhỏ chỗ nối vào `app.py`, `Hub.tick`, thanh dưới của `StaffPhone`, nav của `OwnerShell`, phần "Tiền" của `Shift` |
| Demo ngày 14/11 (ngày mai) | Xem 13.1 |

---

## 12. Ngoài phạm vi

- Giới hạn ai thấy số tiền, đăng nhập, mã PIN (để sau).
- Đọc to tin chat hoặc thông tin thanh toán.
- Đối soát với sao kê ngân hàng, nhận biết ảnh chuyển khoản giả, nối API ngân hàng hay VietQR.
- Nhiều phòng, nhắn riêng 1-1, thả cảm xúc, sửa/xoá tin chữ.
- Thông báo đẩy khi app đóng (FCM).
- Nối máy POS, hoá đơn điện tử, thuế, chi phí, tồn kho, lãi lỗ.
- OCR bằng kie.ai.
- Chấm điểm hay cảnh báo nhân viên dựa trên thanh toán.

---

## 13. Thứ tự làm (sau khi duyệt)

### 13.1 Bản tối thiểu cho demo (nếu muốn kịp 14/11)
1. Phòng chat chữ: gửi, nhận qua SSE, lưu `quan.db`. Mục Nhóm trên điện thoại, mục Nhắn nhóm cho chủ.
2. Chụp → quét có hiệu ứng → sửa → gửi vào phòng thành thẻ. Lưu `payments`.
3. `@AI` trả lời câu hỏi ca trong phòng.
4. Thẻ hiện dòng đối chiếu "✓ Khớp lượt khách bàn 3", và phần "Tiền" ở "Ca hôm nay" với 4 con số và loại "lượt không thấy thanh toán".

### 13.2 Phần còn lại
5. Khung sáng chỗ chữ trên ảnh (nếu `box` của Gemini đủ chuẩn).
6. Nhắc việc hẹn giờ, Nói gọn, Tóm tắt ca.
7. Công cụ doanh thu cho Trợ lý riêng của chủ.
8. Bộ đo độ chính xác OCR, chỉnh prompt và ngưỡng.
9. Cập nhật `API.md`, `docs/he-thong-hien-tai.md`.

---

## 14. Cần chốt khi duyệt

1. Đồng ý cách A (thanh toán là thẻ trong phòng chat)?
2. Làm bản tối thiểu 13.1 cho demo ngày mai, hay để sau demo?
3. Ngưỡng "lượt không thấy thanh toán": khách ngồi ≥ 10 phút, rời ≥ 15 phút. Có hợp với quán demo không?
