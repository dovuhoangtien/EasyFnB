# Chạy Easy FnB

Ba phần nói chuyện với nhau qua mạng:

| Phần | Chạy ở đâu | Làm gì |
|---|---|---|
| Camera AI | laptop có GPU, thư mục `vision-test` | đọc video hoặc camera, nhận khách gọi, bàn cần dọn, khách mới; gửi sự kiện, ảnh cắt và hình trực tiếp lên máy chủ |
| Máy chủ + web | laptop (thư mục `easy-fnb`) hoặc Cloud Run | chia việc cho nhân viên, nhờ Gemini kiểm tra ảnh, phục vụ trang quản lý và app nhân viên |
| Điện thoại nhân viên | trình duyệt trên điện thoại | đọc to việc mới qua tai nghe, không cần bấm; camera thấy nhân viên đứng ở bàn (1 giây) thì tự đóng việc gọi và khách mới, và lấy lúc đó làm thời gian phản hồi; không thấy ai tới thì tự đóng sau 90 giây (báo cáo đếm riêng); việc dọn đóng khi camera thấy bàn sạch |

Hợp đồng giữa các phần: `server/API.md`.

## Chạy thử trên một máy

1. **Khoá LLM (không bắt buộc để chạy).** Cách gọn nhất: chép `easy-fnb\.env.example` thành `easy-fnb\.env`, điền khoá vào rồi chạy lại máy chủ (máy chủ tự đọc tệp này khi khởi động; tệp không lên git và không vào ảnh Docker). Hoặc đặt biến môi trường ở User variables rồi mở cửa sổ dòng lệnh mới. Có hai lựa chọn:
   - `KIE_API_KEY`: dùng kie.ai, model `deepseek-v4-1-flash` (đọc được ảnh). Đây là đường đang dùng vì chưa có khoá Gemini. Vì kie.ai chậm, mặc định chỉ dùng để hỏi đáp / tóm tắt ca.
   - `GEMINI_API_KEY`: dùng Gemini, model `gemini-3.5-flash-lite`. Chỉ dùng khi không đặt `KIE_API_KEY`.
   Không có khoá nào app vẫn chạy, chỉ thiếu bước kiểm tra ảnh và trợ lý AI.
2. **Máy chủ.** Bấm đúp `easy-fnb\chay_may_chu.bat`. Lần đầu nó tự cài thư viện và build web (vài phút). Cửa sổ in ra hai địa chỉ: một cho máy này, một cho điện thoại cùng wifi. Windows hỏi cho Python vào mạng thì chọn **Private network, Allow**; không thì điện thoại không vào được.
3. **Camera.** Bấm đúp `vision-test\chay_camera.bat`: chạy clip `01_phong_an_goc_cao.mp4` lặp lại như camera thật. Clip này có sẵn vùng bàn B1 đến B4 trong `zones.json`, camera tự đẩy lên máy chủ.
4. **Màn hình quản lý.** Mở `http://localhost:8080/`: hình camera trực tiếp, trạng thái bàn, hàng việc.
5. **Điện thoại nhân viên.** Mở `http://<địa chỉ wifi>:8080/nv/lan` (Lan, phục vụ); link đúng của từng người có sẵn ở trang Cài đặt, mục Nhân viên. Có sẵn `minh` (phục vụ) và `tu` (dọn bàn). Bấm **Bắt đầu ca** để điện thoại kêu, rung và đọc to khi có việc.

   **Nối bằng mã QR.** Ở màn hình quản lý, bấm **App nhân viên**, bấm biểu tượng QR cạnh tên từng người rồi để họ quét bằng camera điện thoại. Lần đầu bấm **Thêm vào màn hình chính** (Android trên Cloud Run có nút ngay trên trang, còn chạy ở quán qua wifi thì dùng menu ⋮ của trình duyệt; iPhone dùng nút Chia sẻ của Safari), lần sau chạm icon là vào đúng app của người đó. Vẫn phải bấm **Bắt đầu ca** mỗi lần mở: trình duyệt chỉ cho phát tiếng chuông và giọng đọc sau một lần chạm của người dùng.

   **Điện thoại làm camera.** Trang Cài đặt, mục Kết nối có mã QR cho `/phat?cam=cam1` (đổi sang cam2 đến cam4 bằng các nút). Trình duyệt chỉ cho dùng camera ở địa chỉ **https**: trên Cloud Run có sẵn; chạy ở quán thì khởi động máy chủ với `--https` (cổng 8443, trình duyệt cảnh báo chứng chỉ tự ký) để mã QR trỏ đúng cổng đó.
6. **Trợ lý.** Hỏi về ca làm ("bàn nào chờ lâu nhất?", "nhân viên nào làm tốt nhất?", "giờ nào bận nhất?"). Câu trả lời kèm chỉ số, biểu đồ, ảnh sự kiện, bảng. Có `GEMINI_API_KEY` thì trợ lý chạy bằng Google ADK trên Gemini (kể cả khi đang đặt `KIE_API_KEY`); không có khoá thì máy chủ tự tính và trả lời không dùng AI, vẫn đủ các khối hiển thị.

**Xem mọi thứ đã nối chưa.** Chấm **Trực tiếp** ở góc trên bên phải màn hình quản lý sáng xanh là trang đang nối được với máy chủ; mất kết nối thì chấm đổi màu và đầu trang hiện dòng báo. Trang **Cài đặt, mục Kết nối** có lệnh chạy camera đã điền sẵn địa chỉ máy chủ, và nút **Thử kết nối** gửi một câu hỏi thật tới Gemini để biết khoá có dùng được không. Máy khác muốn kiểm tra máy chủ còn sống thì gọi `GET /api/health`.

Đang sửa giao diện web thì chạy `npm run dev` trong `easy-fnb` và mở cổng 5173 (tự chuyển `/api` sang máy chủ 8080). Lúc demo chỉ cần cổng 8080.

## Giọng đọc tiếng Việt trên máy chủ

Điện thoại không có giọng Việt sẽ lấy file wav từ máy chủ (`/api/tts`). Máy chủ có hai bộ đọc, đều chạy trên CPU, không cần mạng sau lần đầu:

| Bộ đọc | Cài ở đâu | Ghi chú |
|---|---|---|
| `vieneu` (mặc định) | `C:\fnb-tts2` | VieNeu-TTS v3 Turbo, 48 kHz, giọng tự nhiên. Câu mới mất khoảng 1 đến 1,5 giây, nạp model lúc khởi động khoảng 7 đến 12 giây, chiếm khoảng 1,2 GB RAM. |
| `piper` (dự phòng) | `C:\fnb-tts` + `server\voices\vi_VN-vais1000-medium.onnx` | Giọng cũ, 22 kHz, câu mới 0,1 giây. Tự dùng khi VieNeu chưa cài hoặc không khởi động được. |

Cài trên laptop khác (phải để ở đường dẫn ngắn, đường dẫn dự án quá dài làm onnxruntime không nạp được DLL):

```
uv venv C:\fnb-tts2 --python 3.12
uv pip install --python C:\fnb-tts2\Scripts\python.exe vieneu
```

Lần chạy máy chủ đầu tiên cần internet để tải model (khoảng 580 MB từ Hugging Face, vào `HF_HOME` hoặc `%USERPROFILE%\.cache\huggingface`); các lần sau chạy không cần mạng. Không cần cài espeak-ng. Piper (không bắt buộc): `uv venv C:\fnb-tts --python 3.13` rồi `uv pip install --python C:\fnb-tts\Scripts\python.exe piper-tts`.

Biến môi trường (đặt trước khi chạy máy chủ):

- `TTS_ENGINE`: `vieneu`, `piper` hoặc `off`. Bỏ trống thì dùng VieNeu nếu có, không thì Piper, không có cả hai thì app vẫn chạy nhưng không có giọng.
- `VIENEU_VOICE`: tên giọng, gõ không dấu cũng được. Mặc định `Thiện Minh` (nam). Giọng cũ: `Thùy Dung` (nữ, giọng Nam, kiểu đọc tin). Thử thêm: `Mai Anh`, `Ngọc Huyền` (nữ Bắc), `Mỹ Duyên` (nữ Nam), `Minh Triết` (nam Nam). Đổi giọng thì các câu được đọc lại bằng giọng mới.
- `VIENEU_PYTHON`, `PIPER_PYTHON`, `PIPER_MODEL`: đường dẫn nếu cài chỗ khác.

Kiểm tra: mở `http://localhost:8080/api/tts/status` (thấy `"engine":"vieneu"`) và `http://localhost:8080/api/tts?text=Bàn B1 gọi phục vụ`. Mã bàn và số được đọc thành chữ ("B1" thành "bê một"). File nghe thử so sánh hai giọng nằm ở `server\voices\so_sanh`.

## Cài môi trường cho camera (một lần mỗi máy)

Pipeline camera chạy bằng venv ở `%USERPROFILE%\.easy-fnb\venv` (đường dẫn ngắn, vì torch không nạp được DLL khi đường dẫn quá dài). **Đừng đặt venv trong thư mục Temp**: dọn ổ đĩa là mất.

```
uv venv %USERPROFILE%\.easy-fnb\venv --python 3.12
set PY=%USERPROFILE%\.easy-fnb\venv\Scripts\python.exe
uv pip install --python %PY% torch torchvision --index-url https://download.pytorch.org/whl/cu128
uv pip install --python %PY% ultralytics==8.4.202 opencv-python lap open_clip_torch scikit-learn timm "transformers<5" onnx onnxslim tensorrt-cu12 rtmlib safetensors
uv pip uninstall --python %PY% onnxruntime
uv pip install --python %PY% onnxruntime-gpu==1.23.2
%PY% vision-test\xuat_engine.py
```

- Dòng gỡ `onnxruntime` là cần thiết: rtmlib kéo bản CPU về và đè bản GPU.
- `xuat_engine.py` xuất lại 3 engine TensorRT (khoảng 5 phút). Engine chỉ chạy với đúng phiên bản TensorRT đã tạo ra nó, nên cài lại venv hay đổi máy thì phải chạy lại.
- Thỉnh thoảng camera tắt ngay lúc nạp model (lỗi safetensors trên Windows khi máy thiếu RAM): đóng bớt trình duyệt và chạy lại.

## Video tự quay hoặc camera thật

```
vision-test\chay_camera.bat <nguồn> [máy chủ] [mã camera]
```

- Nguồn là file video (tự chạy lặp), số webcam (`0`), hoặc `rtsp://...` của camera IP.
- **Mỗi góc quay một mã camera** (`cam1`, `cam2`...). Vùng bàn lưu theo mã camera, nên góc mới dùng mã mới, hoặc vẽ lại.
- Ví dụ: `chay_camera.bat du_lieu_quay\phien_01\video.mp4 http://localhost:8080 cam2`

**Vẽ vùng bàn:** mở `http://localhost:8080/cai-dat`, mục Vùng bàn, chọn camera, vẽ khung từng bàn trên ảnh camera gửi lên, bấm lưu. Camera đang chạy tự áp dụng sau khoảng 3 giây, không cần chạy lại. Vùng bàn cũng được lưu ở `vision-test\vung_ban_may_chu.json`: máy chủ khởi động lại (Cloud Run) thì camera đẩy lên lại.

**Camera hiểu gì về từng người** (để biết vì sao nó báo hoặc không báo):

- **Đứng hay ngồi** nhìn từ đùi trong khung xương. Người đứng không tính là khách của bàn và không được tính là "gọi phục vụ" (khách đứng dậy, người đi ngang).
- **Vươn vai**: hai tay cùng giơ quá đầu vài khung liền thì coi là vươn vai, không báo gọi trong 2 giây sau đó.
- **Tỉ lệ hành động** (`--hanh-dong`, `chay_camera.bat` đã bật sẵn): dưới nhãn mỗi người hiện 2 hành động có tỉ lệ cao nhất (ngồi ăn, uống, xem điện thoại, trò chuyện, giơ tay gọi, vươn vai, đi lại, đứng, bưng/phục vụ, dọn bàn). Không cần train: model ảnh-chữ PE-Core so ảnh người với câu mô tả, rồi gộp với khung xương và model nhân viên.
- **Kiểm tra chéo trước khi báo gọi**: bộ giơ tay thấy gọi nhưng model hành động cho "giơ tay gọi" dưới 25% thì không báo (trẻ con với tay, người với lên kệ). Đổi mức bằng `--hanh-dong-goi 0.3`, tắt bằng `--hanh-dong-goi 0`.
- Giới hạn: model chỉ nhìn từng khung hình, nên hành động phân biệt bằng chuyển động (ngáp) chưa chắc. Bước sau là train theo chuỗi khung xương.

Thêm tham số cho camera sau 3 tham số trên, ví dụ chạy không GPU: `chay_camera.bat 0 http://localhost:8080 cam1 --device cpu` (cần model `.pt` hoặc OpenVINO thay cho engine TensorRT, xem `vision-test\KET_QUA.md`).

## Không có camera: dùng video CCTV tải trên mạng

Khi chưa quay được quán thật, dùng bộ 17 clip trong `vision-test\video_mang\` (nguồn ghi ở `video_mang\NGUON.md`):

```
vision-test\chay_video_mau.bat 1
vision-test\chay_video_mau.bat 3 http://172.21.1.8:8080
```

- Số 1–17 chọn clip: 1 BBQ Việt có nhân viên và khách giơ tay, 2 BBQ Hàn rất đông, 3 cà phê sân vườn, 4 cà phê quầy pha chế, 5 nhà hàng PTZ, 6 bàn ăn nhìn từ trên cao, 7 CCTV đen trắng, 8 quán ăn Việt nhân viên áo đen, 9 quán cơm đông 7 phút, **10 cà phê Việt: khách về, nhân viên áo đỏ dọn bàn (6 phút, hợp demo nhất)**, 11 cà phê nhân viên áo xanh bưng nước, 12 quán nhậu rất đông ban đêm, 13 quán ăn Đà Nẵng, 14 bàn bẩn chưa dọn, 15 khách ngồi yên (không được báo gì), 16 bàn trống người đi ngang, 17 quán nhỏ. Ghi chú từng clip ở `video_mang\GHI_CHU_CLIP_MOI.md`.
- Clip chạy lặp lại liên tục để demo tại chỗ, gửi lên máy chủ như camera thật. Khi video quay lại đầu clip, các bàn dựng lại trạng thái trong im lặng khoảng 4 giây nên không báo "khách rời"/"đã dọn" hàng loạt mỗi vòng.
- Mỗi clip là một góc quay khác nhau, nên **phải vẽ vùng bàn cho đúng góc đó** ở `cai-dat` (vùng cũ của clip khác sẽ không khớp). Vài clip đã có vùng mẫu trong `zones.json` (m01–m04, m08, m10, m11, m13, m15) để chạy offline không cần vẽ lại.
- Clip có đoạn giới thiệu ở đầu thì khai `bat_dau_s` (số giây bỏ qua) cho clip đó trong `zones.json`; m01 đã khai 12,5 giây. Không bỏ thì lúc cảnh quán hiện ra, mọi bàn cùng báo "khách mới".
- Đây là video của người khác, chỉ dùng nội bộ để thử máy, không đưa vào sản phẩm hay video dự thi.

## Điện thoại làm camera (cùng Wi-Fi, không cần internet)

iPhone/Android chỉ cho trang web dùng camera khi địa chỉ là `https`. Máy chủ có sẵn chế độ https tự ký, chạy hoàn toàn trong mạng LAN:

1. Chạy `easy-fnb\mo_https_lan.bat`. Cửa sổ in ra hai địa chỉ, ví dụ `https://172.21.1.8:8443`.
2. Trên điện thoại làm camera, mở `https://172.21.1.8:8443/phat?cam=cam1`, bấm **Bắt đầu phát**, cho phép camera.
   - Lần đầu iPhone cảnh báo chứng chỉ: **Show details → visit this website → Visit Website**. Sau đó máy nhớ luôn.
   - Đổi Wi-Fi (đổi IP máy chủ) thì chứng chỉ tự tạo lại: điện thoại sẽ hỏi lại một lần.
3. Trên máy chủ, chạy pipeline đọc luồng của điện thoại:

   ```
   vision-test\chay_camera_dien_thoai.bat cam1 https://172.21.1.8:8443
   ```

4. Vẽ vùng bàn ở `https://172.21.1.8:8443/cai-dat`; nhân viên mở `https://172.21.1.8:8443/nv/lan`.

Ghi chú:

- Trang `/phat` gửi khoảng 6 khung/giây, rộng 960 px, qua một kết nối WebSocket; máy chủ phát lại thành luồng MJPEG ở `/api/phone/cam1/mjpeg`, pipeline đọc y như camera IP.
- Trong LAN, độ trễ thêm chỉ vài chục ms. Nếu cần xem từ ngoài quán thì mới phải dùng đường hầm: `easy-fnb\mo_https_cho_dien_thoai.bat` (địa chỉ `trycloudflare.com` đổi mỗi lần chạy, và mỗi ảnh đi vòng qua internet nên chậm hơn nhiều).
- Điện thoại phải cắm sạc và để màn hình sáng; Safari có thể tạm dừng trang khi khoá máy.

## Kiểm tra LLM (Gemini hoặc kie.ai)

Trong `easy-fnb`, với khoá đã đặt:

```
.venv\Scripts\python -m server.gemini
.venv\Scripts\python -m server.gemini <ảnh.jpg> call
.venv\Scripts\python -m server.llm
.venv\Scripts\python -m server.llm <ảnh.jpg> call
```

Hai lệnh đầu dùng Gemini, hai lệnh sau dùng kie.ai (`KIE_API_KEY`). Lệnh không có ảnh chỉ hỏi một câu để thử khoá; lệnh có ảnh gửi một ảnh cắt và in LLM nghĩ có đúng là khách đang gọi không (`call` hoặc `needs_clearing`).

Thử riêng trợ lý ADK với Gemini thật (cần `GEMINI_API_KEY`), trên một ca giả nhỏ, in câu trả lời và các khối:

```
.venv\Scripts\python -X utf8 -m server.tro_ly "Bàn nào chờ lâu nhất?"
```

Mỗi câu in `[adk, <model>, <ms>]` nếu Gemini đã trả lời qua ADK; `[rules, None, ...]` là ADK lỗi (xem dòng cảnh báo ngay trên) và máy chủ đã tự trả lời.

kie.ai chậm hơn Gemini nhiều: mỗi lượt 20–80 giây vì model luôn suy luận. Vì vậy mặc định máy chủ chỉ dùng kie.ai để **hỏi đáp và tóm tắt ca**; việc báo nhân viên do camera tự quyết ngay trên máy (YOLO + vùng bàn), không chờ AI. Muốn bật lại kiểm tra ảnh thì tích trong Cài đặt trực tiếp — khi đó máy chủ nới hạn xác minh lên 100 giây, cảnh báo vẫn hiện ngay và AI xác nhận/huỷ sau.

## Đưa lên Cloud Run

> Có cách làm bằng mã Terraform (khoá nằm trong Secret Manager, bucket dữ liệu, cảnh báo ngân sách): xem `infra/README.md` và `docs/infra-design.md`. Các lệnh `gcloud` dưới đây vẫn dùng được khi chỉ cần thử nhanh.

Cần cài [Google Cloud CLI](https://cloud.google.com/sdk/docs/install) và một project có bật thanh toán (tài khoản dùng thử có 300 USD). Không cần Docker trên máy: Cloud Build build giúp từ `Dockerfile`.

Mở PowerShell trong thư mục `easy-fnb`:

```powershell
gcloud auth login
gcloud config set project <PROJECT_ID>
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com

# khoá riêng giữa camera và máy chủ, để người lạ không gửi sự kiện giả
$k = [guid]::NewGuid().ToString('N'); setx EDGE_KEY $k; $env:EDGE_KEY = $k

gcloud run deploy easy-fnb --source . --region asia-southeast1 --allow-unauthenticated `
  --max-instances 1 --min-instances 1 --no-cpu-throttling --timeout 3600 --memory 512Mi `
  --set-env-vars "GEMINI_API_KEY=$env:GEMINI_API_KEY,EDGE_KEY=$env:EDGE_KEY"
```

Lệnh này lấy khoá từ biến môi trường của cửa sổ đang mở, nên đặt `$env:GEMINI_API_KEY = '<khoá>'` trước khi chạy. Tệp `.env` trên máy không được đưa lên Cloud Run. (Đang dùng kie.ai thì thay `GEMINI_API_KEY` bằng `KIE_API_KEY`; có cả hai thì việc kiểm tra ảnh đi qua kie.ai, trợ lý vẫn dùng Gemini.)

Chưa có khoá lúc triển khai cũng không sao: app chạy đủ, sau đó thêm khoá mà không phải build lại:

```powershell
gcloud run services update easy-fnb --region asia-southeast1 --update-env-vars "GEMINI_API_KEY=<khoá>"
```

Xong nó in ra địa chỉ dạng `https://easy-fnb-....run.app`. Kiểm tra theo thứ tự:

1. Mở `https://easy-fnb-....run.app/api/health`, phải thấy `"ok": true`.
2. Mở trang quản lý, vào **Cài đặt, mục Kết nối**, bấm **Thử kết nối**. Thấy tên model và số mili giây là Gemini đã nối.
3. Chép lệnh chạy camera ngay trong mục đó (đã điền sẵn địa chỉ Cloud Run) và chạy trên máy camera, ở cửa sổ mới để có `EDGE_KEY`:

```
vision-test\chay_camera.bat clips\01_phong_an_goc_cao.mp4 https://easy-fnb-....run.app cam1
```

Vì sao các tham số này:

- `--max-instances 1`: việc và trạng thái bàn nằm trong bộ nhớ một máy, hai máy sẽ chia đôi dữ liệu.
- `--min-instances 1` và `--no-cpu-throttling`: không bị ngủ, bộ đếm chuyển việc vẫn chạy khi không ai mở trang. Tốn khoảng 2 đến 3 USD mỗi ngày; sau demo đổi về 0: `gcloud run services update easy-fnb --region asia-southeast1 --min-instances 0`.
- `--timeout 3600`: luồng sự kiện trực tiếp (SSE) giữ kết nối lâu; hết giờ trình duyệt tự nối lại.
- Dữ liệu ca (việc, nhật ký) mất khi máy chủ khởi động lại. Vùng bàn thì camera đẩy lại được.

Muốn giấu khoá kỹ hơn thì dùng Secret Manager: `--set-secrets GEMINI_API_KEY=<tên secret>:latest` thay cho phần trong `--set-env-vars`.

Muốn giữ vùng bàn, danh sách nhân viên và cài đặt qua mỗi lần khởi động lại thì gắn một bucket Cloud Storage làm thư mục dữ liệu (thêm vào lệnh deploy):

```powershell
  --add-volume "name=du-lieu,type=cloud-storage,bucket=<TÊN BUCKET>" `
  --add-volume-mount "volume=du-lieu,mount-path=/data" `
  --execution-environment gen2
```

và thêm `DATA_DIR=/data` vào chuỗi `--set-env-vars` ở trên. Tài khoản dịch vụ của Cloud Run cần quyền ghi vào bucket đó.

## Trước giờ demo

- Chạy `chay_may_chu.bat` và `chay_camera.bat` một lượt ở nơi demo, kiểm tra điện thoại vào được (cùng wifi, đã cho phép tường lửa). Wifi sự kiện chặn máy nói chuyện với nhau thì dùng Cloud Run, hoặc phát hotspot từ laptop.
- Để dự án ở đường dẫn ngắn (ví dụ `D:\EasyFnB`). Đường dẫn quá dài thì PyTorch báo `WinError 206 ... too long` khi nạp thư viện GPU.
- Bản demo (v5) chạy khoảng 15 đến 20 khung/giây trên laptop RTX 3050 khi gửi lên máy chủ (góc trên phải màn hình camera). Chậm hơn nhiều thì bỏ `--pose-refine rtmpose-m --refine-mode luot` trong `chay_camera.bat`.
- Engine TensorRT gắn với GPU đã build ra nó. Đổi laptop thì chạy lại `danh_gia\do_toc_do.py xuat --gpu`.
- Mở sẵn: màn hình quản lý trên laptop (`/`), điện thoại Lan và Tú (`/nv/lan`, `/nv/tu`), tab trợ lý. Chấm **Trực tiếp** ở góc trên bên phải sáng xanh là đã nối máy chủ.
- Muốn làm lại từ đầu ca: nút đặt lại trên trang Cài đặt (gọi `POST /api/reset`).
