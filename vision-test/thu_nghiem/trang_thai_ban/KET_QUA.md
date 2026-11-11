# Thử bộ trạng thái bàn mới, không chạy lại model (5/11/2026)

Câu hỏi: đổi cách bàn chuyển trạng thái (trống / có khách / cần dọn) có bớt nhấp nháy và bớt báo "khách mới" 2–3 lần cho cùng một nhóm khách không, mà không làm sai thêm?

Cách làm: phát lại dữ liệu từng khung đã ghi (`out_v4/<clip>/chi_tiet.json`, và `out_v3` để kiểm tra chéo) qua từng biến thể. Không model nào chạy lại, chỉ dùng CPU.

## Trả lời ngắn

**Nên đưa vào bản demo, nhưng chỉ phần đơn giản:** "khách rời phải vắng liên tục 5 giây", "khách mới phải có mặt 1 giây", và độ bẩn có trễ (thành bẩn ở 0,5, chỉ thành sạch dưới 0,35). Thêm "sạch liên tục 3 giây mới báo đã dọn".

- Trên đáp án cũ (137 mốc), bản mới **không tệ hơn**: 128–130/137 chấm chặt (bản cũ 130), **137/137 cho trễ** (bản cũ 136). Hai mốc chấm chặt mất thêm là do đồng hồ của clip time-lapse, giải thích bên dưới.
- Điểm khác biệt nằm ở **video thường**, chỗ bộ chấm cũ không thấy:
  - Clip 06 (khách ngồi suốt, nhân viên che): bản cũ báo `khach_roi` ở giây 14,3 rồi `khach_moi` ở giây 15,6 cho **cùng hai người**. Bản mới: 0 sự kiện nhầm.
  - Nhiễu giả: chèn những lần "mất người" 1–4 giây vào bàn có khách. Sự kiện nhầm giảm từ **6,5 xuống 0,2 mỗi phút mỗi bàn** (bớt khoảng 30 lần).
- Cái giá: báo khách rời và cần dọn chậm hơn **5 giây**. Báo khách mới chậm hơn 1 giây. Báo đã dọn chậm hơn 3 giây.
- **Không nên đưa vào:** chặn theo mức che bàn, bắt buộc phải thấy nhân viên tới mới báo đã dọn, và gắn người vào bàn theo điểm nằm trong bàn. Lý do có ở bên dưới.

## Dữ liệu dùng để chấm, và giới hạn của nó

- **Có đáp án:** clip 01 (time-lapse, 4 bàn, 7 lần đổi trạng thái thật) và clip 02 (3 bàn, khách ngồi suốt, không đổi lần nào). Clip 02 không có khung nào mất người, nên không biến thể nào sai ở đó. Nghĩa là **toàn bộ phần đổi trạng thái thật chỉ dựa trên 7 lần đổi trong một clip time-lapse.**
- **Clip quay thường, không có đáp án:** 06, 07, 09. Khách ngồi suốt cả ba clip, nên mọi sự kiện đều là báo nhầm. Mình vẽ tay vùng bàn thô (`vung_ban_them.json`, chưa có người kiểm). Clip 07 và 09 máy quay lia nhẹ. Các clip này không có xác suất bàn bẩn, vì lúc chạy thật chúng chưa có vùng bàn.
- **Nhiễu giả** trên 7 bàn có khách của clip 02, 06, 07, 09:
  - Mất người 1–4 giây, trung bình một lần mỗi 15 giây.
  - Một bàn trống giả có người đứng tạm 0,5–3 giây, cũng trung bình một lần mỗi 15 giây.
  - Lặp 20 lần ngẫu nhiên.
- **Độ trễ:** đo trên một kịch bản giả, sạch, theo thời gian thật. Khách tới ở giây 10, khách đi để lại đồ ở giây 20, nhân viên dọn xong ở giây 38.
- **Đồng hồ của clip 01:** 0,5 giây video là 15–30 giây ngoài đời, tức nhanh gấp 30–60 lần. Thời gian giữ (giây ngoài đời) được chia cho hệ số này, bản chính lấy 30 và có thử lại với 60. Riêng phần lọc nhiễu vẫn tính theo `xac_nhan_s` của từng clip như cũ (clip 01 là 0,5 giây, video thường là 1 giây).
- v3 và v4 có cùng dữ liệu người (cùng YOLO, cùng bộ bám), chỉ khác model bàn bẩn (CLIP B/32 và PE-Core S/16). Vì vậy kiểm tra chéo v3/v4 chỉ kiểm phần độ bẩn.

## Bước 1: phát lại khớp bản chạy thật

`phat_lai.py` chép nguyên `class Table` rồi phát lại trên dump. Kết quả khớp **từng khung và từng sự kiện** với `su_kien.json` của cả v4 và v3, ở clip 01 và 02 (v4: 130/137 chặt, 136/137 cho trễ). Không có chỗ lệch:

- Khung không có `pd` (model bàn chỉ chạy mỗi 4 khung) đã là `None` trong dump, giống pipeline.
- Thời điểm tính lại bằng số thứ tự khung chia fps, không dùng số đã làm tròn.

`BanMoi` với tham số mặc định cũng cho ra đúng như bản cũ, trên mọi clip.

## Bảng kết quả

Cột:

- **Chặt / trễ:** đúng trên 137 mốc (v4, clip 01 nhanh gấp 30 lần).
- **Đổi (thừa, sót):** số lần máy đổi trạng thái, so với 7 lần đổi thật. Lần đổi không khớp lần đổi thật nào là thừa; lần đổi thật mà máy không đổi theo là sót.
- **KM thừa:** khach_moi thừa trong một phiên có khách, ở clip có đáp án.
- **Clip tĩnh:** số sự kiện nhầm ở 06/07/09.
- **Nhiễu giả:** sự kiện nhầm mỗi phút mỗi bàn khi mất người, và khach_moi ảo mỗi phút khi có người đứng tạm ở bàn trống.
- **Trễ vào / ra / dọn:** độ trễ, tính bằng giây thật.

| Biến thể | Chặt | Trễ | Đổi (thừa, sót) | KM thừa | Clip tĩnh | Nhiễu giả: mất người / KM ảo | Trễ vào / ra / dọn |
|---|---|---|---|---|---|---|---|
| **Bản cũ** | 130 | 136 | 7 (0, 1) | 0 | 2 (1 KM) | 6,46 / 3,30 | 0,8 / 0,8 / 0,4 |
| a1 EMA có khách | 130 | 136 | 6 (0, 1) | 0 | 2 | 6,44 / 3,28 | 0,8 / 0,8 / 0,4 |
| a2 EMA độ bẩn | 130 | 136 | 6 (0, 1) | 0 | 2 | 6,53 / 3,30 | 0,8 / 0,8 / 0,3 |
| a3 trễ độ bẩn 0,5/0,35 | 128 | 137 | 7 (0, 0) | 0 | 2 | 6,46 / 3,30 | 0,8 / 0,8 / 0,6 |
| **a4 EMA độ bẩn + trễ** | 130 | **137** | 7 (0, **0**) | 0 | 2 | 6,51 / 3,30 | 0,8 / 0,8 / 0,4 |
| a5 trung vị độ bẩn + trễ | 130 | 137 | 7 (0, 0) | 0 | 2 | 6,49 / 3,30 | 0,8 / 0,8 / 0,5 |
| a6 EMA cả hai + trễ | 130 | 137 | 7 (0, 0) | 0 | 2 | 6,49 / 3,28 | 0,8 / 0,8 / 0,4 |
| b1 ra chậm 5 s | 130 | 135 | 6 (0, 2) | 0 | **0** | **0,21** / 2,53 | 0,8 / 5,8 / 0,4 |
| b3 vào 1 s, ra 10 s | 131 | 135 | 4 (0, 3) | 0 | 0 | 0,07 / 1,88 | 1,8 / 10,8 / 0,4 |
| b4 vào 2 s, ra 20 s | 130 | 135 | 4 (0, 3) | 0 | 0 | 0,07 / 0,60 | 2,8 / 20,8 / – |
| c1 che > 30% | 130 | 136 | 7 (0, 1) | 0 | 2 | 6,37 / 3,30 | 0,8 / 0,8 / 2,0 |
| c2 che > 50% (c3 > 70%: giống hệt) | 130 | 136 | 7 (0, 1) | 0 | 2 | 6,37 / 3,30 | 0,8 / 0,8 / 0,4 |
| c4 che > 50% + xét đồ sau khi khách rời | 130 | 136 | 7 (0, 1) | 0 | 2 | 6,37 / 3,30 | 0,8 / 0,8 / 0,4 |
| d1 sạch liên tục 5 s | 129 | 136 | 6 (0, 1) | 0 | 2 | 6,42 / 3,30 | 0,8 / 0,8 / 5,4 |
| d3 phải có người tới bàn | 124 | 131 | 6 (1, 2) | 0 | 2 | 6,42 / 3,30 | – |
| d4 phải có nhân viên tới | **87** | 93 | 4 (0, 3) | 0 | 2 | 6,42 / 3,30 | – |
| d6 = d3, không ai tới thì sạch 30 s | 128 | 135 | 6 (1, 2) | 0 | 2 | 6,42 / 3,30 | – |
| e1 điểm neo trong bàn | 112 | 119 | 10 (5, 3) | 1 | 2 | – | – |
| e2 khung người phủ ≥ 15% bàn | 121 | 130 | 13 (7, 2) | 2 | 6 (3 KM) | – | – |
| K1 a4 + vào 1 s, ra 10 s | 131 | 135 | 4 (0, 3) | 0 | 0 | 0,07 / 1,88 | 1,8 / 10,8 / 0,4 |
| **K6 a4 + vào 1 s, ra 5 s** | 130 | **137** | 7 (0, 0) | 0 | **0** | **0,21** / 2,05 | 1,8 / 5,8 / 0,4 |
| **Đề xuất: K6 + sạch 3 s** | 128 (130 nếu nhanh gấp 60) | **137** | 7 (0, 0) | 0 | **0** | **0,21** / 2,05 | 1,8 / 5,8 / 3,4 |

Ghi chú về bảng:

- Đo bằng `bien_the.py` (log ở `chay_bien_the.log`, số đầy đủ ở `ket_qua.json`). Dòng đề xuất đo riêng (`kiem_de_xuat.log`).
- Với v3 (model bàn khác), các biến thể xếp hạng giống v4: bản cũ 129/134, a4 và K6 129/135, đề xuất 129/135.
- 4 trong 7 lỗi chặt của mọi biến thể là mốc 0,25 s đầu clip 01, lúc máy chưa đủ dữ liệu để kết luận ("?"). Ở camera chạy liên tục, lỗi này không có.
- "Sự kiện cần" theo đáp án là 12. Bản cũ ra 10, a4/K6 ra 11, b3/K1 ra 6. Ở các clip có đáp án, bản cũ sai vì **thiếu** sự kiện chứ không thừa: thiếu `can_don` của bàn B2 lúc 6,25 s.

## Từng ý tưởng

**a. Lọc và trễ (hysteresis):**

- Phần có khách: bản cũ đã có trễ sẵn (vào ở 0,8, ra ở 0,2), nên đổi sang EMA gần như không khác gì.
- Phần độ bẩn: bản cũ chỉ có một ngưỡng 0,5, và đây là chỗ hỏng thật.
  - Bàn B2 (clip 01) lúc khách đi có `pd` lưng chừng (0,41, 0,31, 0,48), nên bản cũ cho thành "trống" thay vì "cần dọn" → sót.
  - Bàn B3 thì "cần dọn" rồi "đã dọn" sau 0,17 s video.
- Có trễ (bẩn từ 0,5, sạch dưới 0,35): bàn đã bẩn trong bữa ăn vẫn bẩn lúc khách rời. Hết sót, cho trễ lên 137/137.
- Ngưỡng sạch nằm trong 0,25–0,4 đều cho 137/137. Ngưỡng 0,45–0,5 sót lại.
- EMA và trung vị trượt như nhau. Chọn EMA vì không phải giữ danh sách.

**b. Giữ lệch (vào nhanh, ra chậm):** đây là phần sửa được "khach_moi 2–3 lần".

| Thời gian giữ khi khách rời | Sự kiện nhầm do nhiễu (mỗi phút mỗi bàn) | Clip tĩnh |
|---|---|---|
| 0 s | 6,4 | 2 |
| 2 s | 3,7 | 0 |
| 3 s | 1,0 | 0 |
| 5 s | 0,2 | 0 |
| 8–10 s | 0,1 | 0 |

- Ở clip 01, giữ từ 8 s trở lên gộp mất hai nhóm khách liền nhau của bàn B3. Nhóm sau tới trong khoảng 30–60 giây ngoài đời, và vài khung còn sót người làm bộ đếm giờ khởi động lại. Kết quả là sót 3 lần đổi, cho trễ còn 135.
- Vì vậy chọn **5 s**: an toàn với cả hệ số 30 lẫn 60.
- Khách mới: giữ 1 s chỉ bớt khach_moi ảo từ 2,2 xuống 1,9 mỗi phút. Giữ 3 s bớt xuống 0,14 nhưng báo trễ 3,8 s.
- Mình chọn 1 s cho demo, vì người đứng tạm ở bàn thường là nhân viên, và việc đó nên để nhận diện nhân viên lo.

**c. Chặn khi bàn bị che:** không có tác dụng.

- Tính bằng phần đa giác bàn bị khung người phủ. Trong clip 01 nhìn từ trên cao, khung người ở bàn bên cạnh phủ lên bàn này 30–50% ngay cả khi bàn trống, nên số đo này rất nhiễu.
- Ngưỡng 50–70% gần như không bao giờ chặn. Ngưỡng 30% chặn cả lúc nhân viên đang dọn, làm báo đã dọn chậm (trễ 2 s trong kịch bản giả).
- Thêm "xét đồ trên bàn sau khi khách rời" cũng không đổi kết quả.
- Muốn làm đúng phải có mặt nạ người (segmentation), không làm bằng khung chữ nhật được.

**d. Luật theo phiên:**

- "Cần dọn chỉ sau khi khách rời, hoặc đầu clip": bản cũ đã làm vậy. Không có đường nào từ trống sang cần dọn.
- "Một khach_moi mỗi phiên": đạt được nhờ giữ khi khách rời (mục b), không cần luật riêng.
- "Phải thấy nhân viên tới mới báo đã dọn": **hỏng nặng** (87/137). Model nhân viên gần như không bao giờ vượt 0,5 ở góc cao của clip 01 (pst cao nhất 0,65 cho từng khung, trung bình 3 giây thì không qua).
- Bản nới "ai tới bàn cũng được" vẫn tệ hơn (124). Ở bàn B4, đồ biến mất giữa hai khung time-lapse mà không thấy ai tới.
- Luật này có thể đúng ở camera thật, nhưng không kiểm được bằng dữ liệu hiện có, nên không dùng.
- "Sạch liên tục N giây" thì giữ, với N = 3 s:
  - Ở clip 01 với hệ số 30, nó làm hai mốc 1,25 s thành báo trễ một chút (mất 2 điểm chặt, cho trễ vẫn đủ). Với hệ số 60 thì không mất.
  - Ở camera thật, nó chặn kiểu "cần dọn rồi đã dọn sau 1 giây" khi người đứng che bàn làm model bàn thấy sạch thoáng qua.

**e. Gắn người vào bàn theo hông:**

- **Không làm được trên dump:** dump chỉ có khung người, không có khung xương.
- Thử hai cách thay bằng khung người thì đều tệ hơn hẳn (112 và 121/137).
  - Cách 1: điểm neo phải nằm trong đa giác bàn.
  - Cách 2: khung người phải phủ ít nhất 15% bàn.
- Lý do: vùng bàn vẽ trên mặt bàn. Người ngồi cạnh bàn có hông nằm ngoài mặt bàn, nhất là ở góc thấp như clip 06 và 07, nơi cách 1 cho bàn trống suốt.
- Muốn thử bằng hông thật phải chạy lại với `--luu-khung-xuong` và vẽ vùng bàn gồm cả ghế. Cách gán hiện tại (bàn gần nhất trong 0,45 chiều cao người) nên giữ.

## Có khớp đáp án quá không

Tham số không chọn bằng cách dò cho điểm cao nhất:

- 0,35 là điểm giữa `pd` của bàn bẩn khi không có khách (trung vị 0,63) và bàn sạch (90% dưới 0,3).
- 5 s là mức nhỏ nhất làm hết nhiễu giả.
- 1 s và 3 s là chọn tròn.

Độ nhạy (`do_nhay.py`, `do_nhay.log`):

- Ngưỡng sạch trong 0,25–0,4 cho cùng kết quả cho trễ.
- Thời gian giữ khi khách rời trong 2–5 s cho cùng kết quả trên đáp án.

Chấm tách đôi bàn clip 01 (B1+B3 và B2+B4, mỗi nửa cộng clip 02): K6 không tệ hơn bản cũ ở nửa nào, cả v4 lẫn v3.

| Nửa | Bản cũ (v4) | K6 (v4) |
|---|---|---|
| B1+B3 | 75/79 chặt, 79 cho trễ | 75, 79 |
| B2+B4 | 76/79 chặt, 78 cho trễ | 76, **79** |

Nói thẳng: trên đáp án hiện có, bản mới chỉ hơn **1 mốc** (cho trễ). Lợi ích chính được đo trên clip không đáp án và nhiễu giả.

## Điểm yếu của bản đề xuất

1. **Báo khách rời và cần dọn chậm 5 giây.** Với nhà hàng thì chấp nhận được. Nhưng lúc demo, người xem sẽ thấy bàn vẫn "có khách" vài giây sau khi khách đã đứng dậy.
2. **Người đứng tạm ở bàn trống vẫn thành khách mới** nếu đứng quá khoảng 1,8 s: 2,05 khach_moi ảo mỗi phút trong nhiễu giả, bản cũ 3,3. Đây là việc của nhận diện nhân viên (đang yếu), không phải của bộ trạng thái.
3. **Hai nhóm khách nối nhau trong dưới 5 giây bị gộp thành một phiên.** Ngoài đời hiếm khi xảy ra.
4. Clip 01 là time-lapse, nên phải khai `toc` (hệ số tua, ví dụ 30) trong zones.json. Nếu không khai, clip 01 sẽ giữ 5 s video (2,5–5 phút ngoài đời) và gộp sai nhiều phiên.
5. Chưa có video thật nào có đáp án cho cảnh khách đến, khách đi, nhân viên dọn theo thời gian thật. Số "nhiễu giả" là mô phỏng, chưa phải đo trên quán thật.

## Đề xuất thay `class Table`

File thử: `ban_de_xuat.py`. Đã kiểm tra nó cho ra đúng từng khung như biến thể "K6 + sạch 3 s" trên mọi clip.

Muốn dùng thì sửa hai chỗ trong `easyfnb_test.py`:

1. Thay class.
2. Tạo bàn bằng `Table(k, v, toc=float(cfg.get('toc', 1.0)))`, cả chỗ tạo bàn lúc vẽ lại vùng trên web.

Rồi thêm `"toc": 30` cho clip `01_phong_an_goc_cao` trong `zones.json`. Lời gọi `update(t, n, dirty_obs, win)` giữ nguyên.

```python
class Table:
    """Trạng thái một bàn. So với bản cũ: độ bẩn lọc mũ và có trễ (bẩn từ 0,5, sạch dưới 0,35);
    khách mới phải có mặt 1 s, khách rời phải vắng liên tục 5 s (trong lúc chờ bàn vẫn "có khách"),
    đã dọn phải sạch liên tục 3 s. Thời gian giữ là giây ngoài đời; toc = giây ngoài đời / giây video."""
    GIU_VAO, GIU_RA, GIU_SACH = 1.0, 5.0, 3.0
    BAN, SACH, TAU = 0.5, 0.35, 0.5  # ngưỡng bẩn vào / ra, hằng số EMA (bội số của win)

    def __init__(self, name, pts, toc=1.0):
        self.name = name
        self.poly = np.array(pts, np.float32)
        self.toc = toc
        self.state = None
        self.people = deque()  # (t, số người ngồi)
        self.n_now = 0
        self.dirty_now = None
        self.dirty_f = None
        self.t_dirty = None
        self.is_dirty = False
        self.t_vao = self.t_ra = self.t_sach = None

    def update(self, t, n, dirty_obs, win):
        """Cập nhật một khung hình, trả về danh sách (loại sự kiện, chi tiết)."""
        self.n_now = n
        self.people.append((t, n))
        while self.people and self.people[0][0] < t - win:
            self.people.popleft()
        if dirty_obs is not None:
            self.dirty_now = dirty_obs
            if self.dirty_f is None:
                self.dirty_f = dirty_obs
            else:
                a = 1 - math.exp(-(t - self.t_dirty) / (self.TAU * win))
                self.dirty_f += a * (dirty_obs - self.dirty_f)
            self.t_dirty = t
            if self.is_dirty and self.dirty_f < self.SACH:
                self.is_dirty = False
            elif not self.is_dirty and self.dirty_f >= self.BAN:
                self.is_dirty = True
        if t - self.people[0][0] < 0.9 * win:
            return []  # chưa đủ một cửa sổ để kết luận

        occ = np.mean([k > 0 for _, k in self.people])
        dirty = self.is_dirty
        heads = int(np.median([k for _, k in self.people if k > 0] or [0]))
        held = lambda t0, s: t - t0 >= s / self.toc - 1e-9
        ev = []
        if self.state is None:  # đầu clip: chỉ ghi nhận trạng thái
            self.state = 'co_khach' if occ >= 0.5 else ('can_don' if dirty else 'trong')
            if self.state == 'can_don':
                ev.append(('can_don', 'đầu clip đã có đồ trên bàn, không có khách'))
            return ev
        if self.state != 'co_khach':
            if occ >= 0.8:
                self.t_vao = t if self.t_vao is None else self.t_vao
                if held(self.t_vao, self.GIU_VAO):
                    self.state = 'co_khach'
                    self.t_vao = self.t_ra = self.t_sach = None
                    return [('khach_moi', f'{heads} người')]
            else:
                self.t_vao = None
        if self.state == 'co_khach':
            if occ <= 0.2:
                self.t_ra = t if self.t_ra is None else self.t_ra
                if held(self.t_ra, self.GIU_RA):
                    ev.append(('khach_roi', ''))
                    self.state = 'can_don' if dirty else 'trong'
                    self.t_ra = self.t_sach = None
                    if dirty:
                        ev.append(('can_don', 'còn đồ trên bàn sau khi khách đi'))
            else:
                self.t_ra = None
        elif self.state == 'can_don':
            if not dirty and occ <= 0.2:
                self.t_sach = t if self.t_sach is None else self.t_sach
                if held(self.t_sach, self.GIU_SACH):
                    self.state = 'trong'
                    self.t_sach = None
                    ev.append(('da_don', ''))
            else:
                self.t_sach = None
        return ev
```

Cần thêm `import math` ở đầu `easyfnb_test.py`. Sau khi sửa, chạy lại `danh_gia/cham_diem.py` trên một lần chạy mới để xác nhận: dự kiến 128/137 chặt nếu `toc` = 30 (130 nếu `toc` = 60), và 137/137 cho trễ.

## Chạy lại

```bash
venv\Scripts\python thu_nghiem/trang_thai_ban/phat_lai.py     # kiểm tra phát lại khớp bản chạy thật
venv\Scripts\python thu_nghiem/trang_thai_ban/bien_the.py     # mọi biến thể, ~2 phút CPU, ghi ket_qua.json
venv\Scripts\python thu_nghiem/trang_thai_ban/do_nhay.py      # độ nhạy tham số, chấm tách đôi bàn
```

Các file:

- `phat_lai.py`: đọc dump, `Table` cũ, chấm điểm.
- `ban_moi.py`: bộ trạng thái bật/tắt từng ý tưởng.
- `bien_the.py`: danh sách biến thể, clip tĩnh, nhiễu giả, độ trễ.
- `ban_de_xuat.py`: bản đề xuất.
- `vung_ban_them.json`: vùng bàn vẽ thô cho clip 06, 07, 09.
