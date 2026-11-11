# Reusing restaurants' existing CCTV in Vietnam (and zero-cost demo cameras) — Easy FnB

Research date: 2026-11-04. Several sources are forum posts or vendor blogs; reliability is flagged inline. Items marked "(snippet)" were read in search-result summaries, not fetched in full.

## 1. Which CCTV brands dominate small business / restaurant installs in Vietnam?

### Takeaway
Chinese brands from two groups dominate: **Hikvision (+ its consumer brand EZVIZ)** and **Dahua (+ its consumer brand Imou, + OEM rebrands such as KBVision)**. Xiaomi, Yoosee and TP-Link (Tapo/VIGI) cover the cheap Wi‑Fi end, and FPT Camera / Viettel Camera lead the ISP-bundled cloud-camera segment. No reliable brand-by-brand share table for Vietnam exists publicly; the evidence is import data, industry quotes and surveys.

### Cited Findings
- Vietnam imports about 3.2 million security cameras a year, more than 16 million over five years, and 96.3% come from China. Popular brands named: HikVision, Ezviz, Dahua, iMou, KBVision, Xiaomi (VnExpress, 29 Aug 2024, citing the Ministry of Information and Communications) — [VnExpress](https://e.vnexpress.net/news/news/surveillance-cameras-proliferate-most-imported-from-china-4783072.html)
- An industry figure quoted by VIR said Dahua, Hikvision and their subsidiaries held "nearly 90 per cent" of a camera market worth about USD 175 million in 2023 (snippet) — [VIR](https://vir.com.vn/cooperation-crucial-to-claim-camera-market-slice-111528.html)
- From FY2024 customs data, asmag puts Vietnam's security market at more than USD 280 million, with Wi‑Fi cameras such as Imou and EZVIZ at more than USD 100 million and "solution" brands such as Hikvision and Dahua in the rest (snippet) — [asmag](https://www.asmag.com/mobile/article_detail_amp.aspx?aid=35153)
- EZVIZ says it had more than 52% of Vietnam's camera import value in 2021, citing a B&Company report. This is the vendor's own claim — [EZVIZ VN newsroom](https://www.ezviz.com/vn/newsroom/idc%3A+ezviz+ti%E1%BA%BFp+t%E1%BB%A5c+d%E1%BA%ABn+%C4%91%E1%BA%A7u+th%E1%BB%8B+tr%C6%B0%E1%BB%9Dng+camera+an+ninh+trong+q42024/1103)
- A Metric e-commerce study counted 341 camera brands on Vietnamese e-commerce sites, mostly Chinese. Yoosee was among the top 3 by units sold (31.9%), and no Vietnamese brand was among the best sellers (snippet) — [VietNamNet](https://vietnamnet.vn/en/chinese-cameras-flooding-e-commerce-sites-in-vietnam-2282798.html)
- In cloud-storage cameras, an FPT-cited survey says FPT Camera is used by 46.6% of users and Viettel Camera by 28.2%. This is FPT's own publication (snippet) — [FPT](https://fpt.com/en/news/fpt-camera-dominates-vietnams-cloud-storage-camera-market)
- Retail comparison articles describe Imou and EZVIZ as the two most popular mass-market Wi‑Fi brands in Vietnam, with EZVIZ better known — [Điện Máy Xanh](https://www.dienmayxanh.com/kinh-nghiem-hay/so-sanh-camera-imou-va-ezviz-1595511); [FPT Shop](https://fptshop.com.vn/tin-tuc/dien-may/so-sanh-camera-imou-va-ezviz-162201)
- Third-party OEM directories list **KBVision as a Dahua OEM**. Dahua OEM products "use the same protocols and port numbers", including TCP 37777 — [IPVM Dahua OEM directory](https://ipvm.com/reports/dahua-oem); [learncctv Dahua OEM list](https://learncctv.com/dahua-oem-list-updated/). A Vietnamese retailer describes KBVision as an "American technology" brand with HD‑CVI and IP lines and does not mention the OEM link — [Mytour](https://mytour.vn/vi/blog/bai-viet/top-5-thuong-hieu-camera-giam-sat-gia-re-tai-vienthonggiarecom.html)
- A Hoàng Hà Mobile blog says Dahua has about 20% of Vietnam's market in 2026. The figures are unsourced and appear to be global shares, so they are low reliability — [Hoàng Hà Mobile](https://hoanghamobile.com/tin-tuc/camera-dahua/)
- Market-size estimates disagree: IMARC gives USD 516.43M for 2024 CCTV, and Ken Research gives about USD 1.2B for video surveillance. Both are paywalled summaries without brand splits — [IMARC](https://www.imarcgroup.com/vietnam-cctv-camera-market); [Ken Research](https://www.kenresearch.com/vietnam-video-surveillance-market)

### Inferences
- For product planning, two stream "dialects" cover most of the wired installed base: **Hikvision-style** (Hikvision, EZVIZ, often HiLook) and **Dahua-style** (Dahua, KBVision, Imou, other Dahua OEMs). The long tail is cloud-first Wi‑Fi cameras (EZVIZ, Imou, Tapo, Xiaomi, Yoosee) and ISP cloud cameras (FPT, Viettel).
- Restaurants with 4–16 cameras are more likely to have a wired NVR/DVR from Hikvision, Dahua or KBVision fitted by a local installer. Small cafés and street-food shops are more likely to have 1–4 Wi‑Fi cameras (EZVIZ, Imou, Xiaomi, Yoosee, FPT Camera). This split is a reasoned guess; I found no data on it.

### Gaps
- No public Vietnam brand-share data by unit or by segment (restaurants/SMEs vs homes). Data from IDC, Counterpoint or Metric was not accessible.
- Little information on Vantech and Questek (Vietnamese/Taiwanese-labelled brands sold locally): no share data and no RTSP documentation found.

## 2. Per brand: RTSP/ONVIF availability, URL formats, cloud-first enabling, models with no RTSP

### Takeaway
Wired Hikvision, Dahua and KBVision cameras and NVRs expose RTSP and ONVIF with well-known URL patterns, and the substream can be chosen in the URL. Cloud-first brands usually still have RTSP, but it is gated behind a local credential (Tapo "camera account", the EZVIZ verification code, the Imou safety code) or a toggle. Xiaomi Mi Home cameras generally have no RTSP; the only open-source route is go2rtc's `xiaomi` source (local P2P, but a Xiaomi cloud login is needed for keys). ISP cloud cameras (FPT, Viettel) are an unknown and could be the biggest blocker.

### Cited Findings
**URL patterns (`rtsp://USER:PASS@IP:554/...`)**

| Brand | Main stream | Substream | Notes |
|---|---|---|---|
| Hikvision (camera) | `/Streaming/Channels/101` | `/Streaming/Channels/102` (low-res); `/103` third stream on higher-end models | Newer models may need RTSP/WEB auth set to digest/basic and digest algorithm MD5 — [Frigate camera-specific docs](https://docs.frigate.video/configuration/camera_specific/) |
| Hikvision NVR | channel×100+1, e.g. `/Streaming/Channels/201` = ch2 main | channel×100+2, e.g. `202` | Third-party guide, Jul 2026 — [SmartRTSP](https://www.smartrtsp.com/ja/guides/hikvision-nvr-rtsp-channel-101-102) |
| Dahua / Amcrest (and Dahua OEMs) | `/cam/realmonitor?channel=1&subtype=0` | `subtype=1` (low-res); `subtype=2/3` mid-res on higher-end models | [Frigate camera-specific docs](https://docs.frigate.video/configuration/camera_specific/); go2rtc calls Dahua the "reference implementation… high stream quality, multiple streaming clients" — [go2rtc README](https://github.com/AlexxIT/go2rtc) |
| EZVIZ (Hikvision) | `/h264/ch1/main/av_stream` | `/h264/ch1/sub/av_stream` | User `admin`; password = 6-capital-letter verification code on the label. Local RTSP must be switched on in the app. Model and firmware dependent; some models have no local RTSP — [Home Assistant EZVIZ integration](https://www.home-assistant.io/integrations/ezviz/); [HA community thread](https://community.home-assistant.io/t/ezviz-camera-connection-to-ha/83878?page=5); [iSpy EZVIZ](https://www.ispyconnect.com/camera/ezviz). go2rtc: EZVIZ has an "awful RTSP protocol implementation, many bugs in SDP" — [go2rtc README](https://github.com/AlexxIT/go2rtc) |
| Imou (Dahua) | `/cam/realmonitor?channel=1&subtype=0&unicast=true&proto=Onvif` | `subtype=1` | User `admin`; password = Safety Code on the camera's underside (forum: the code stays the same after an app password change, a security concern). ONVIF is only partly compatible. Dahua removed the web UI from Imou firmware on newer models, and some models, e.g. a later IPC‑A42PD v2, reportedly don't work — [ipcamtalk Imou Ranger 2 thread](https://www.ipcamtalk.com/goto/post?id=392258); [ipcamtalk](https://www.ipcamtalk.net/goto/post?id=394977) (forum sources) |
| TP-Link Tapo | `/stream1` (HQ) | `/stream2` (SD); dual-lens telephoto `/stream6`, `/stream7` | You must first create a **Camera Account** in the Tapo app (Device Settings → Advanced Settings → Camera Account), separate from the cloud login, 6–32 characters. Default port 554. Battery cameras and doorbells generally have no RTSP. If Tapo Care cloud, local and NAS/NVR recording are all enabled, NAS/NVR/ONVIF recording is turned off automatically. Tapo advises LAN/VPN only — [Tapo FAQ 34](https://www.tapo.com/en/faq/34/) |
| TP-Link VIGI | (not found) | (not found) | Frigate: set the main stream to H.264 with Smart Coding off, or playback breaks — [Frigate camera-specific docs](https://docs.frigate.video/configuration/camera_specific/). go2rtc has a dedicated "TP-Link Vigi" source — [go2rtc README](https://github.com/AlexxIT/go2rtc) |
| Yoosee | `/onvif1` | `/onvif2` (lower res) | Port 554. An RTSP password is set in the Yoosee app and cannot be left blank. Some models use `/11` or `/live.sdp` — [Camlytics Yoosee](https://camlytics.com/camera/yoosee); [iSpy Yoosee](https://www.ispyconnect.com/camera/yoosee); [HA community](https://community.home-assistant.io/t/trying-to-get-ip-camera-to-work-yoosee/32842?page=2); [ipcamtalk](https://ipcamtalk.com/goto/post?id=397249) |
| Xiaomi (Mi Home) | No standard RTSP | — | go2rtc ≥ **v1.9.13** has a `xiaomi` source. You log in with your Xiaomi account in the go2rtc WebUI (may need an email/SMS code or captcha). Video runs over P2P (`cs2+udp/tcp`, `tutk`) and the "connection to the camera is local only", but Internet is needed to fetch encryption keys. Most `xiaomi/mess` + cs2 cameras work well; legacy cameras may have issues; TUTK "works terribly". Quality is set with `subtype` (hd/sd/auto). The supported-model list is in go2rtc issue #1982 — [go2rtc xiaomi README](https://github.com/AlexxIT/go2rtc/blob/master/internal/xiaomi/README.md) |
| Xiaomi with hacked firmware / cheap no-name | often `/live/ch00_1` | — | go2rtc: "awful but usable RTSP… low stream quality, few settings, packet loss?" — [go2rtc README](https://github.com/AlexxIT/go2rtc) |

- go2rtc lists private-protocol sources for cameras without good RTSP: Tapo, TP-Link Vigi, Xiaomi, Tuya, Wyze, Hikvision ISAPI (two-way audio), DVRIP (XMeye/Sofia, used by many cheap no-name DVRs), Kasa, Ring, Nest and others. It also supports ONVIF, RTSP, RTMP and MJPEG sources — [go2rtc README](https://github.com/AlexxIT/go2rtc)
- go2rtc brand notes: TP-Link "few streaming clients, packet loss?"; Reolink "some models have an awful, unusable RTSP implementation"; Hikvision "a lot of proprietary streaming technologies" — [go2rtc README](https://github.com/AlexxIT/go2rtc)
- Some Hikvision NVR integration guides show the substream configured as **MJPEG** at 640×480/30 fps/512 kbps — [RTI Hikvision tech note (PDF)](https://www.rticontrol.com/pub/media/wysiwyg/dealer/technote/RTI_How_to_Configure_Hikvision.pdf). Frigate notes that MJPEG sources must be re-encoded to H.264 for restreaming, at significantly higher CPU cost — [Frigate camera-specific docs](https://docs.frigate.video/configuration/camera_specific/)

### Inferences
- An onboarding wizard can auto-detect most of the base by trying ONVIF discovery first, then known RTSP templates (Hikvision `/Streaming/Channels/X02`, Dahua `realmonitor…subtype=1`, Tapo `/stream2`, EZVIZ `/h264/ch1/sub/av_stream`, Yoosee `/onvif2`), and the go2rtc `xiaomi` source for Xiaomi.
- Cloud-first cameras need the owner to take one action: read the label code (EZVIZ/Imou) or create a Tapo camera account. The setup UX should walk them through it with screenshots.
- Practical obstacles to plan for: (a) the owner often doesn't know the NVR admin password because the installer holds it; (b) Hikvision firmware auth quirks (digest/MD5); (c) H.265/"smart codec" main streams; (d) MJPEG substreams on some NVR setups; (e) Tapo's storage-mode conflict; (f) the Imou/EZVIZ label code acting as a fixed, shared password (a security risk worth telling the owner about).
- Cameras plugged into an NVR's built-in PoE ports usually sit on the NVR's internal subnet and can't be reached directly from the LAN, so streams must be pulled from the NVR. This is general installer knowledge, not verified in this research.

### Gaps
- No official VIGI, KBVision, Vantech or Questek RTSP documentation found. KBVision probably uses the Dahua format given the OEM status, but this is unconfirmed.
- No information on whether FPT Camera or Viettel Camera (cloud cameras with large user shares) expose RTSP/ONVIF to third parties. This could be the biggest blocker for "no new hardware" and needs a direct question to FPT/Viettel or a hands-on test.
- The exact Xiaomi models supported (go2rtc issue #1982) were not reviewed.
- Imou has no official RTSP documentation; the forum evidence conflicts by model and firmware.

## 3. Pulling streams from the NVR/DVR: channel numbering, substream specs, concurrency limits, analog cameras

### Takeaway
Pulling from the NVR/DVR is usually the easiest path: one IP and one credential, with channels picked by number (Hikvision `/Streaming/Channels/{ch}02`, Dahua/KBVision `channel={ch}&subtype=1`). Typical substreams are 640×360/640×480 at about 512 kbps. NVRs cap total remote connections (for example 128 on one Hikvision model), and cheap cameras allow only a few clients, so take **one connection per stream and restream it** through go2rtc or MediaMTX.

### Cited Findings
- Hikvision NVR numbering: stream ID = channel × 100 + stream type, e.g. ch1 main 101, sub 102; ch2 main 201, sub 202 (third-party guide, Jul 2026) — [SmartRTSP](https://www.smartrtsp.com/ja/guides/hikvision-nvr-rtsp-channel-101-102)
- Dahua-style URLs select the channel with `channel=` and the stream with `subtype=` (0 = main, 1 = sub 1, 2 = sub 2) — [getscw RTSP URL list](https://www.getscw.com/decoding/rtsp); [Frigate camera-specific docs](https://docs.frigate.video/configuration/camera_specific/)
- Hikvision: going over a device's connection limit produces a "maximum number of streams" error. The per-device remote-connection cap is in the spec sheet (128 for the example NVR), and remote connections are a separate limit from bandwidth — [Hikvision US support](https://supportusa.hikvision.com/support/solutions/articles/17000135582-how-to-see-the-number-of-streams-from-an-nvr-error-maximum-number-of-streams)
- A forum user with a 32-channel Hikvision NVR had random stream errors well below bandwidth capacity, and attributed them to the "Network Remote Connection 128-ch" limit (forum) — [ipcamtalk](https://www.ipcamtalk.net/goto/post?id=620186)
- Recommended Hikvision substream bitrates: 320×240 → 256 kbps; 640×360 → 512 kbps; 640×480 → 512 kbps (recommendations, not confirmed factory defaults) — [learncctv](https://learncctv.com/?p=28741); [SecurityCamCenter](https://securitycamcenter.com/hikvision-recommended-video-settings/). A forum recommendation: 640×480, VBR, 15 fps, 512 kbps, H.264, I-frame 15 — [ipcamtalk](https://ipcamtalk.com/threads/enabling-a-hikvision-substream.60849/latest)
- Frigate: the Dahua/Hikvision substream "typically supports only low resolutions", and the third stream (Hikvision 103, Dahua subtype=2) gives mid resolution on higher-end models. Frigate's example Dahua config sets Sub Stream 2 to H.264, 1280×720, 5 fps, with I-frame interval 5 — [Frigate camera-specific](https://docs.frigate.video/configuration/camera_specific/); [Frigate camera setup](https://docs.frigate.video/frigate/camera_setup/)
- Frigate advises matching the aspect ratios of the detect and record streams (e.g. 640×360 with a 16:9 main stream, not 640×480) — [Frigate camera setup](https://docs.frigate.video/frigate/camera_setup/)
- Frigate/go2rtc restream exists for cameras that "support only one active connection". Without a separate substream, one camera connection feeds detect and record; with one, two camera connections are made — [Frigate restream docs](https://docs.frigate.video/configuration/restream/)
- KBVision sells both HD‑CVI (analog-HD) and IP lines — [Mytour](https://mytour.vn/vi/blog/bai-viet/top-5-thuong-hieu-camera-giam-sat-gia-re-tai-vienthonggiarecom.html)

### Inferences
- **Analog cameras (HDCVI/AHD/TVI) behind a DVR/XVR:** the cameras have no network stack, so the DVR is the only source. Hybrid DVRs from Hikvision, Dahua and KBVision expose per-channel RTSP in the same URL format as their NVRs. Cheap no-name DVRs (XMeye/"Sofia") can use go2rtc's DVRIP source. This is plausible from the go2rtc source list but was not verified on a real KBVision XVR.
- DVR substreams on older analog systems are often CIF/D1-class (≈352×288 to 704×576). That is enough for table-state and person detection but weak for faces (see Q5). Not verified with a source.
- Budget per restaurant: 1 connection per camera substream into the edge restreamer (plus an optional on-demand main-stream connection for face crops). That stays well under NVR caps and leaves the NVR's own recording and the owner's phone app untouched.
- Changing substream settings (resolution, codec H.264, I-frame interval ≈ fps) on the NVR is free but needs admin access. This is a one-time installer/owner step.

### Gaps
- No source confirmed factory-default substream settings for Dahua or KBVision (D1/CIF), or the concurrency limits of cheap Wi‑Fi cameras (Tapo, EZVIZ, Imou). go2rtc only says TP-Link has "few streaming clients".
- No source tested RTSP from an HDCVI/AHD DVR specifically.

## 4. Open-source tools to ingest, restream and normalize: go2rtc, MediaMTX, Frigate, FFmpeg, WebRTC

### Takeaway
Use **go2rtc** as the per-site ingest and normalization layer: multi-brand sources (RTSP, ONVIF, Tapo, Xiaomi, DVRIP…), one camera connection fanned out to many consumers, and WebRTC/MSE for low-latency browser viewing. Use **MediaMTX** where phones or browsers need to *push* streams (SRT/RTMP/WebRTC). Frigate's pattern is the reference design: go2rtc restream, a low-res substream for detection at about 5 fps, and the main stream left to the NVR for recording.

### Cited Findings
- go2rtc sources: RTSP, ONVIF, RTMP, MJPEG, WebRTC/WHEP, HomeKit, DVRIP, Hikvision ISAPI, Tapo, TP-Link Vigi, Xiaomi, Tuya, Wyze, FFmpeg (incl. USB devices), V4L2/ALSA, exec, and push ingest into an empty stream via RTSP/RTMP/WebRTC/MPEG-TS/FLV/MJPEG. Outputs: WebRTC, MSE (MP4), RTSP, HLS, MJPEG, FLV, RTMP, MPEG-TS, ONVIF and JPEG snapshots. It claims "zero-delay for many supported protocols". Its codec table rates WebRTC best and HLS "the worst technology for live streaming" — [go2rtc README](https://github.com/AlexxIT/go2rtc)
- WebRTC via go2rtc adds about 100–200 ms on top of the raw RTSP stream (vendor blog) — [SmartRTSP RTSP-to-WebRTC](https://www.smartrtsp.com/guides/rtsp-to-webrtc). The go2rtc web UI on port 1984 has no password by default — same source
- Frigate uses go2rtc for restream and MSE/WebRTC. The restream lets detection and Home Assistant live view share one camera connection, with no re-encoding. Config pattern: define main and sub in go2rtc, point Frigate inputs at `rtsp://127.0.0.1:8554/<name>` with `preset-rtsp-restream`, give `record` to main and `detect` to sub — [Frigate restream docs](https://docs.frigate.video/configuration/restream/)
- Frigate lessons: only the detect stream is decoded. The detector runs at 320×320, so higher resolution only helps when objects are small. Keep `detect.fps` at 5 (max 10; reposition the camera rather than raise fps). H.264 has the best compatibility, and H.265 has browser/profile limits. Placement matters more than fps — [Frigate camera setup](https://docs.frigate.video/frigate/camera_setup/)
- Frigate brand quirks: Hikvision digest/MD5 auth; Reolink better over http-flv than RTSP; VIGI Smart Coding off; Annke H.265-only; MJPEG cameras need H.264 re-encoding (CPU heavy); UDP-only cameras need `preset-rtsp-udp` — [Frigate camera-specific docs](https://docs.frigate.video/configuration/camera_specific/)
- MediaMTX: publish via SRT, WebRTC, RTSP, RTMP, HLS, MPEG-TS, RTP and Media-over-QUIC (including from web browsers, FFmpeg, GStreamer, OBS, Raspberry Pi cameras); read via SRT/WebRTC/RTSP/RTMP/(LL-)HLS; automatic protocol conversion; can proxy other servers; records to fMP4/MPEG-TS — [MediaMTX GitHub](https://github.com/bluenviron/mediamtx)

### Inferences
- Reference pipeline: `NVR/cameras → go2rtc (edge box/mini-PC already in the restaurant, or the POS PC) → (a) WebRTC/MSE to the staff dashboard; (b) local RTSP restream → FFmpeg/OpenCV frame sampler at 3–5 fps → detector`. Fetch main-stream frames or JPEG snapshots on demand (go2rtc snapshot endpoint) only for face-recognition crops.
- Normalize everything to H.264 substreams at the camera/NVR where possible to avoid CPU-heavy transcoding on a no-GPU edge PC. Transcode only MJPEG/H.265 outliers.
- Never expose go2rtc or MediaMTX ports to the Internet (no auth by default). Use an outbound tunnel or VPN (Tapo also recommends VPN over public exposure) — [Tapo FAQ 34](https://www.tapo.com/en/faq/34/)

### Gaps
- No measured latency benchmarks for go2rtc vs MediaMTX WebRTC were found, beyond the vendor's 100–200 ms estimate.
- MediaMTX's `sourceOnDemand`/RTSP-proxy specifics and WHIP endpoint paths were not confirmed (the README didn't detail them; check mediamtx.org).

## 5. Are typical restaurant camera placements usable? Resolution needed for faces vs person/pose detection

### Takeaway
A 2MP wide-angle corner camera is fine for **person/table-occupancy detection** across a typical dining room, even on a 640×360 substream. It is marginal for **raised-hand/pose and empty-glass** detection beyond a few metres on the substream, and it **cannot do face recognition from the substream** except very close. Face ID needs main-stream (1080p) crops near the entrance, about ≤3 m from a 2MP camera with a wide lens.

### Cited Findings
- IEC 62676-4 DORI thresholds (16 cm face width): Detection 25 px/m (4 px/face), Observation 63 px/m (10 px/face), Recognition 125 px/m (20 px/face), Identification 250 px/m (40 px/face). Lighting, optics and compression also affect results. The standard has a 2025 edition, which may differ — [Axis whitepaper](https://whitepapers.axis.com/en-us/pixel-density-based-on-iec-62676-4-2014); [TP-Link/VIGI DORI FAQ](https://www.vigi.com/hu/support/faq/4098/)
- Pixel density formula: px/m = H_pixels / (2·d·tan(HFOV/2)). Using it with 1920 px and a 90° HFOV, identification (250 px/m) holds up to about 3.8 m (my calculation with the Axis method; the whitepaper explains the method and does not give this number) — [Axis whitepaper](https://whitepapers.axis.com/pixel-density-and-dori)
- Frigate: detection runs on 320×320 crops, so higher resolution only helps for small/far objects. Aim cameras where objects move toward them — [Frigate camera setup](https://docs.frigate.video/frigate/camera_setup/)

### Inferences
- Worked numbers for a typical 2MP camera with a 2.8 mm lens (HFOV assumed ≈100°, tan 50° ≈ 1.19; my own calculation):
  - **Main stream 1920 px:** px/m ≈ 806/d → identification (250) to ≈3.2 m; recognition (125) to ≈6.4 m; observation (63) to ≈12.8 m.
  - **Substream 640 px:** px/m ≈ 269/d → identification only to ≈1.1 m; recognition ≈2.1 m; observation ≈4.3 m; detection (25) ≈10.7 m.
  - A seated adult (~1.3 m visible height) at 8 m on a 640-px substream is ≈43 px tall. That's enough for "person present" but too small for reliable keypoints (hand above head) or for spotting an empty glass. Use the 1280×720 third stream (Hikvision `103`, Dahua `subtype=2`) where available, or crop main-stream frames per table region at a lower rate (1–2 fps).
- Face-recognition embedding models usually work on roughly 112×112 aligned face crops (general knowledge, not sourced here). Upscaling a 20–40 px face loses identity information, so put "regular customer" recognition on the camera nearest the entrance/cashier, using main-stream frames.
- High corner mounts see tops of heads and occlude far tables behind near diners. Map each table to the camera with the best view during setup (per-camera table polygons). Fisheye/360° cameras need dewarping before standard detectors, and edge distortion lowers effective px/m.
- Night/IR mode (grayscale, IR glare on glasses and tables) and dim restaurant lighting will hurt glass and face detection. Plan to report confidence per table instead of hard alarms.

### Gaps
- No source quantified the pixels needed for pose/raised-hand detection or small-object (glass) detection in CCTV footage. The figures above are derived estimates.
- No data on typical camera counts, mounting heights or lens choices in Vietnamese restaurants.

## 6. Network: upload bandwidth for N substreams (cloud processing) and Vietnamese business upload speeds

### Takeaway
At about 0.5 Mbps per 640×360 substream (≈1–2 Mbps at 720p), even 16 cameras need only 8–32 Mbps of sustained upload. Vietnamese fixed broadband is fast (national median download ≈300 Mbps; Hanoi median fixed upload ≈199 Mbps, Aug 2026), so raw bandwidth is not the bottleneck. NAT/no inbound access, shared uplinks and reliability are. An edge agent that pushes outbound, or on-site inference sending only events, is the safer design.

### Cited Findings
- Ookla Speedtest Global Index, Aug 2026: Vietnam fixed broadband median download 301.48 Mbps (ranked 8th). Hanoi fixed: 251.94 Mbps down, **199.35 Mbps up**, 4 ms latency (30th city). Coverage of the July index gives conflicting national figures (255.87 vs 307.11 Mbps) — [The Star / Vietnam News](https://www.thestar.com.my/aseanplus/aseanplus-news/2026/10/14/hanoi-becomes-world039s-fifth-fastest-city-for-mobile-internet); [Vietnam News](https://vietnamnews.vn/society/1798899/viet-nam-enters-global-top-10-for-mobile-and-fixed-broadband-speeds)
- In April 2025, FPT, Viettel and VNPT doubled their minimum home plan speeds to 300 Mbps without raising prices — [Lao Động](https://news.laodong.vn/kinh-doanh/gia-internet-co-dinh-dong-loat-tang-1665000.ldo)
- FPT business plans (older 2023 article): Super 500 / LUX 500 / LUX 800 at 500–800 Mbps. Static IP is an optional add-on — [VTC News 2023](https://vtcnews.vn/dang-ky-goi-cuoc-internet-fpt-doanh-nghiep-va-khach-hang-vip-mang-fpt-ar772757.html); [Hoàng Hà Mobile](https://hoanghamobile.com/tin-tuc/goi-wifi-fpt/). 2026 business price lists found were contradictory (an agent site lists the same 2 Gbps tier at 1.0M and at 4.5M VND/month) — [chogia.vn](https://chogia.vn/cap-nhat-bang-gia-lap-mang-internet-cap-quang-hom-nay-ngay-thang-nam-49979/)
- Substream bitrate reference: 640×360/640×480 ≈ 512 kbps — [learncctv](https://learncctv.com/?p=28741)

### Inferences
- Upload needed (sustained, video only): 4 cams × 0.5 = 2 Mbps; 8 cams = 4 Mbps; 16 cams = 8 Mbps; at 720p/1.5 Mbps, 16 cams ≈ 24 Mbps. That fits under 10–20% of a typical ≥100 Mbps upload, but the link is shared with POS, ordering apps and guest Wi‑Fi.
- Sending JPEG frames instead of H.264 is *less* efficient: a ~30–50 KB 640×360 JPEG at 4 fps is ≈1–1.6 Mbps per camera, 2–3× the H.264 substream. Forward the H.264 substream, or run inference on site and send only events/metadata.
- Most SME lines have no static IP and may sit behind CGNAT, so cloud processing must use an **outbound** connection from an on-site agent (go2rtc/MediaMTX pushing via RTSP/SRT/WebRTC, or a VPN/tunnel), not inbound pulls to the NVR.
- Recommended split for the hackathon story: detection on the edge (an existing PC/laptop at the cashier counts as "no new hardware"), with cloud fallback for heavier models.

### Gaps
- No official 2026 FPT/Viettel/VNPT business plan pages with explicit upload speeds or static-IP pricing were retrieved. No national-level fixed upload median for Vietnam (only Hanoi) was found.
- No data on CGNAT prevalence on Vietnamese residential/SME lines.

## 7. Zero-cost cameras for the hackathon demo (phones, iPhones, laptop webcams)

### Takeaway
For the demo, use team members' Android phones as RTSP/MJPEG cameras (IP Webcam, DroidCam) or as push sources (Larix Broadcaster → MediaMTX/go2rtc over SRT/RTMP/WebRTC), plus laptop webcams through FFmpeg/go2rtc. Feed them into the same go2rtc → detector pipeline the real restaurant NVR would use, so the demo proves the production path.

### Cited Findings
- IP Webcam (Android) exposes RTSP at `rtsp://<phone-ip>:8080/h264_ulaw.sdp` with audio. It is listed as a supported source in the AlexxIT WebRTC Camera docs (mirror) — [AlexxIT WebRTC docs](https://docsearch.algolia.com/mcp/docs/repo/alexxit/webrtc)
- DroidCam offers MJPEG "IP web camera" access in a browser; default port 4747; USB is lower latency than Wi‑Fi (blog). Its OBS plugin negotiates H.264 (forum logs) — [android.com.pl](https://android.com.pl/apps/droidcam/); [OBS DroidCam guide](https://obs-versions.com/blog/droidcam-obs-setup-guide); [OBS forum](https://obsproject.com/forum/threads/droidcam-obs-camera.145220/page-16)
- LocalCam (open source, Android) serves H.264/AAC at `rtsp://<device-ip>:8554/live`. It is early-stage and "might crash sometimes" — [LocalCam release](https://github.com/TheRyanMajd/LocalCam/releases/tag/v1.0.0)
- The "RTSP Camera" Android app runs an on-phone RTSP server (rated 2.2/5 from 4 reviews) — [appwisp listing](https://appwisp.com/app/android/video.surveillance.rtsp.camera)
- Larix Broadcaster (Android and iOS) publishes via SRT (caller/listener/rendezvous), RTMP/RTMPS and WebRTC (WHIP) — [Larix iOS](https://softvelum.com/larix/ios/); [App Store](https://apps.apple.com/gt/app/id1042474385?l=es-mx); [Dolby.io blog](https://dolby.io/blog/broadcasting-mobile-native-webrtc-streams-with-the-larix-broadcaster). MediaMTX accepts SRT/RTMP/WebRTC publishing and converts to RTSP/WebRTC — [MediaMTX](https://github.com/bluenviron/mediamtx)
- go2rtc can ingest local webcams via FFmpeg (USB devices) and V4L2 on Linux, and accepts pushed streams into empty sources — [go2rtc README](https://github.com/AlexxIT/go2rtc)
- RTSP latency: typically 2–3 s by default, 1–2 s tuned (vendor blog) — [Fora Soft](https://www.forasoft.com/blog/article/integrate-android-apps-ip-cameras); WebRTC through go2rtc adds about 100–200 ms (vendor blog) — [SmartRTSP](https://www.smartrtsp.com/guides/rtsp-to-webrtc)

### Inferences
- Demo kit: 2–3 Android phones (IP Webcam or Larix → MediaMTX), one laptop webcam (FFmpeg/go2rtc), one laptop running go2rtc + detector, and the team's own phone hotspot or a travel router so venue Wi‑Fi isolation doesn't block phone-to-laptop traffic. Venue Wi‑Fi at hackathons often blocks client-to-client traffic; test early.
- Simulating a ceiling camera: mount the phone high (tripod, monopod or clamp on a shelf/door frame, ~2–2.5 m) in landscape, tilted ~30–45° down, using the ultrawide (0.5×) lens to mimic a 2.8 mm CCTV lens. Lock focus and exposure, keep it plugged in, disable screen sleep/battery optimization for the app, and set a low resolution (640×360 or 1280×720, 5–15 fps) to mimic a substream. Optionally record footage of a staged "restaurant" (tables, cups, team acting as guests) and replay it as a looping RTSP source (FFmpeg/go2rtc file source) as a backup in case live streaming fails on stage.
- For the face-recognition demo, use a separate phone close to the "entrance" at eye height, consistent with the DORI numbers in Q5.
- iPhones: Larix (push over SRT/RTMP/WHIP) is the open, free route. Background streaming on iOS is less reliable because the app must stay in the foreground (general knowledge, not sourced).

### Gaps
- No official docs or measured latency/reliability comparisons for IP Webcam, DroidCam or Larix were retrieved. The latency figures come from vendor blogs.
- No verified free iOS app that serves RTSP (pull) was found.

## 8. Privacy/legal practicalities in Vietnam (only where it changes technical choices)

### Takeaway
Vietnam's **Personal Data Protection Law (91/2025/QH15)** and **Decree 356/2025/NĐ‑CP**, both in force from **1 Jan 2026** (Decree 356 replaces Decree 13/2023), treat biometric data as sensitive with extra safeguards. That points Easy FnB toward opt-in face enrollment, on-premise processing, storing embeddings rather than face images, and visible notices. Occupancy/pose analytics without identification carry lower risk.

### Cited Findings
- Law 91/2025/QH15 on Personal Data Protection was passed 26/6/2025 and takes effect 1/1/2026. It has a dedicated article (Art. 31) on location and biometric data — [Hệ thống pháp luật](https://hethongphapluat.com/luat-bao-ve-du-lieu-ca-nhan-2025/khoan-1-dieu-3); [LSVN](https://lsvn.vn/bao-ve-du-lieu-ca-nhan-doi-voi-du-lieu-vi-tri-ca-nhan-du-lieu-sinh-trac-hoc-a161208.html); [G&V legal alert (PDF)](https://gvlawyers.com.vn/wp-content/uploads/2025/09/VN_Legal-alert-_Law-on-PDP-2025.pdf)
- Organizations processing biometric data must apply physical security, restrict access and notify data subjects if processing causes harm (analysis article) — [LSVN](https://lsvn.vn/bao-ve-du-lieu-ca-nhan-doi-voi-du-lieu-vi-tri-ca-nhan-du-lieu-sinh-trac-hoc-a161208.html)
- Decree 356/2025/NĐ‑CP takes effect 1/1/2026, replaces Decree 13/2023, and lists sensitive data including biometric data — [Decree 356 text (MOJ)](https://vbpl.moj.gov.vn/TW/Lists/vbpq/Attachments/187276/ND.356.2025.doc); [Thư viện pháp luật](https://thuvienphapluat.vn/phap-luat/chu-de/bao-ve-du-lieu-ca-nhan)
- Camera security in Vietnam: leaked camera footage is sold on social media for VND 200k–1M. In 2021, about 1 million Vietnamese IPs a month appeared in botnets, 5% linked to camera malware. A 2024 MIC draft technical regulation for IP cameras requires unique default passwords (≥8 chars, mixed) and patching of security flaws within 3 days. It was still a draft at publication, with no effective date given — [VnExpress (Aug 2024)](https://e.vnexpress.net/news/news/surveillance-cameras-proliferate-most-imported-from-china-4783072.html); [VietNamNet](https://vietnamnet.vn/en/cybersecurity-regulations-for-surveillance-cameras-to-be-proposed-2286090.html)

### Inferences
- Technical choices this drives: (1) keep raw video on site, since the NVR already records; Easy FnB should process transiently and keep only events; (2) face recognition opt-in only (e.g. loyalty enrollment via QR/Zalo with explicit consent), storing encrypted embeddings with deletion on request; (3) per-camera "analytics off" zones (e.g. restrooms and staff areas, which should not be filmed anyway); (4) a visible notice sign at the entrance; (5) never open NVR ports to the Internet; change shared label codes (EZVIZ/Imou) where possible.
- Staff-position tracking is employee monitoring and should be disclosed in employment policies (general practice, not verified for Vietnamese labour law).

### Gaps
- The exact wording of Art. 31 and Decree 356 on CCTV in commercial premises, notice signs and consent exceptions was not read in full. Get a legal review before production.
- Whether the 2024 MIC IP-camera technical regulation was finalized, and its effective date, was not confirmed.
