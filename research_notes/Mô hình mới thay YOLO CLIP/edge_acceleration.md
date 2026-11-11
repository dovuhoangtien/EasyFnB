# Edge acceleration for Easy FnB's multi-camera vision pipeline (runtimes, quantization, decoding, camera counts, cloud cost), as of Nov 2026

Baseline from the brief (Easy FnB's own measurements, PyTorch). RTX 3050 4 GB laptop: about 31 fps total (pose 22 ms, detect 26 ms at 960 px). Ryzen 7 6800H CPU, FP32: about 8–9 fps total (pose ~75 ms, detect ~138 ms, CLIP ~40 ms per crop). Workload per camera at 5 fps: yolo26n-pose at 960 px on every frame, yolo26s detect at 960–1280 px on every 3rd–6th frame, and CLIP ViT-B/32 on a few crops per second.

## Q1. Runtimes: how much faster than PyTorch, and do they work on Windows?

### Takeaway
On Intel hardware, OpenVINO is by far the biggest lever. Ultralytics' own 2026 tables (OpenVINO 2026.2.1) show YOLO26n going from about 27–33 ms in PyTorch-CPU to 3.3–9 ms with OpenVINO, and YOLO26s going from 59–71 ms to 4–16 ms, on Core Ultra laptops. On NVIDIA, TensorRT FP16 cuts YOLO26n to about 1.7–1.8 ms on a T4 and about 4.6 ms on a Jetson Orin Nano Super, against 15.6 ms in PyTorch. For AMD, Windows options are weaker. ROCm on Windows is a preview for newer Radeon parts only, and the Ryzen AI NPU path (Vitis AI EP) needs a quantized model. CPU ONNX Runtime or DirectML is the realistic fallback.

### Cited Findings
**Ultralytics YOLO26 reference speeds (640 px, COCO)**
- YOLO26 detect, CPU ONNX / T4 TensorRT10 (ms): n 38.9 / 1.7 (2.4 M params, 5.5 GFLOPs, mAP 40.9); s 87.2 / 2.5 (9.5 M, 20.9 GFLOPs, mAP 48.6); m 220.0 / 4.7. The page does not name the CPU used for the "CPU ONNX" column. — [Ultralytics YOLO26 docs](https://docs.ultralytics.com/models/yolo26/)
- YOLO26 pose, CPU ONNX / T4 TensorRT10 (ms): n-pose 40.3 / 1.8 (mAP-pose50-95 57.2, 7.6 GFLOPs); s-pose 85.3 / 2.7 (63.0, 24.1 GFLOPs); m-pose 218.0 / 5.0 (68.8). — [Ultralytics Pose task docs](https://docs.ultralytics.com/tasks/pose/)
- Ultralytics cites the YOLO26 paper's claim of "up to 43% faster CPU ONNX inference" for YOLO26n versus YOLO11n, measured on an Intel Xeon @ 2.00 GHz (vendor claim). The paper also reports up to +7.2 pose AP over YOLO11. YOLO26 drops DFL, and its one-to-one head allows NMS-free (`nms=False`) export, which simplifies export to TensorRT, ONNX, CoreML, LiteRT and OpenVINO. — [Ultralytics YOLO26 docs](https://docs.ultralytics.com/models/yolo26/)
- Export supports a `quantize` argument for ONNX, OpenVINO, TensorRT, CoreML, NCNN, RKNN, Hailo, Xilinx and others. `nms=False` selects the NMS-free head where the format supports it. — [Ultralytics Pose task docs](https://docs.ultralytics.com/tasks/pose/)

**Intel OpenVINO (Ultralytics benchmark tables, openvino 2026.2.1, page updated about Nov 2026; per-image inference ms)**
- **Core Ultra 7 155H (Meteor Lake).** YOLO26n: PyTorch-CPU 33.19 → OV FP32 9.13 → FP16 9.07 → INT8 5.79. YOLO26s: 70.92 → 16.37 → 16.65 → 9.27. YOLO26m: 192.45 → 34.47 → INT8 15.46. — [Ultralytics OpenVINO integration](https://docs.ultralytics.com/integrations/openvino/)
- **Core Ultra 7 258V (Lunar Lake).** YOLO26n: 27.33 → FP32 3.33 → FP16 3.34 → INT8 3.46. YOLO26s: 60.20 → 4.66 → 4.65 → INT8 3.99. YOLO26m: 152.87 → 9.03 → INT8 5.70. — [Ultralytics OpenVINO integration](https://docs.ultralytics.com/integrations/openvino/)
- **Core Ultra X7 358H (Panther Lake).** YOLO26n: 29.28 → FP32 4.09 → FP16 4.03 → INT8 4.24. YOLO26s: 59.32 → 5.08 → 5.14 → INT8 4.47. YOLO26x: 379.75 → FP16 12.98 → INT8 8.74. — [Ultralytics OpenVINO integration](https://docs.ultralytics.com/integrations/openvino/)
- Caveat: the tables do not say which device each row ran on. Section captions list the iGPU, CPU and NPU for each chip. The page's headline claim is "up to 3x" CPU speed-up, so the 7–8× ratios above most likely reflect the iGPU (the ratios are my arithmetic, not the page's). — [Ultralytics OpenVINO integration](https://docs.ultralytics.com/integrations/openvino/)
- NPU: "YOLO26 models on NPU are only supported on Intel Core Ultra systems with 2xxV series and 3xx series and above." Meteor Lake (1xxH) NPUs are therefore excluded for YOLO26. INT8 export uses `quantize=8`, which replaces the deprecated `half`/`int8` flags, and needs calibration `data`/`fraction`. — [Ultralytics OpenVINO integration](https://docs.ultralytics.com/integrations/openvino/)
- Windows: the Ultralytics page does not state Windows support explicitly. One Windows user reported an export/inference crash, and the maintainer suggested updating drivers and OpenVINO. — [Ultralytics OpenVINO integration](https://docs.ultralytics.com/integrations/openvino/)

**ONNX Runtime / Windows ML / DirectML (Windows)**
- Windows ML ships the CPU and DirectML ("legacy") execution providers in-box. Vendor EPs, including OpenVINO (EP 1.8.69.0 with OpenVINO 2026.0, and 1.8.79.0 with OpenVINO 2026.1 listed as upcoming), are downloaded on demand. Hardware-optimized EPs for NPUs and specific GPUs require Windows 11 24H2 (build 26100) or later. — [Microsoft Learn: Windows ML supported EPs](https://learn.microsoft.com/en-us/windows/ai/new-windows-ml/supported-execution-providers)
- Microsoft says DirectML remains supported, but new feature work has moved to Windows ML. For new projects it recommends the vendor GPU/NPU EPs that Windows ML installs. — [microsoft/WindowsML GitHub](https://github.com/microsoft/WindowsML); [Microsoft Learn](https://learn.microsoft.com/en-us/windows/ai/new-windows-ml/supported-execution-providers)
- The ONNX Runtime DirectML EP docs still list DirectML 1.15.2 / opset 20 and look stale. — [ONNX Runtime DirectML EP](https://onnxruntime.ai/docs/execution-providers/DirectML-ExecutionProvider.html)

**NVIDIA TensorRT**
- YOLOv8n on consumer GPUs (RTX 3080 12 GB / 3060 12 GB / 2060 6 GB; the page gives one combined set; **Windows 10**, TensorRT 10.0.0b6, ultralytics 8.2.4; an older 2024-era result): batch-8 predict FP32 1.06 ms, FP16 0.62 ms, INT8 0.52 ms per image. mAP50-95 is 0.37 for FP32/FP16 and 0.33 for INT8. This confirms TensorRT works on Windows through Ultralytics. — [Ultralytics TensorRT integration](https://docs.ultralytics.com/integrations/tensorrt/)
- Caveats from the same page:
  - Engines are tied to the GPU they were built on, so they must be built on the deployment GPU.
  - INT8 calibration should use at least 500 representative images (NVIDIA guideline).
  - On TensorRT 11, INT8 goes through NVIDIA ModelOpt explicit quantization, and the `IInt8Calibrator` interface was removed.
  - TensorRT 11.2.1 does not support JetPack, and TensorRT 10.7 is the last release with DLA.
  - `dynamic=True` allows batches smaller than the export batch size.

  — [Ultralytics TensorRT integration](https://docs.ultralytics.com/integrations/tensorrt/)
- Jetson Orin Nano Super, YOLO26n at 640 (Ultralytics 8.4.33, JP6.1), mAP50-95 / ms: PyTorch 0.4790 / 15.60; ONNX 0.4760 / 15.76; TRT FP32 0.4770 / 7.53; **TRT FP16 0.4800 / 4.57**; TRT INT8 0.4490 / 3.80. On Orin NX 16 GB, TRT FP16 is 4.13 ms and INT8 3.49 ms. Times exclude pre- and post-processing. — [Ultralytics Jetson guide](https://docs.ultralytics.com/guides/nvidia-jetson/)

**Frigate detector benchmarks (YOLOv9/YOLO-NAS/RF-DETR, not YOLO26; Linux/Docker)**
- Iris Xe (OpenVINO): YOLOv9 t-320 6 ms, t-640 14 ms, s-320 8 ms, s-640 16 ms; YOLO-NAS 640 ~20 ms; RF-DETR 320-n 33 ms. — [Frigate hardware docs](https://docs.frigate.video/frigate/hardware)
- Intel NPU: YOLOv9 s-320 11 ms, s-640 30 ms; RF-DETR 320-n 40 ms. Arc A310: YOLOv9 s-640 15 ms. UHD 770: YOLOv9 s-640 ~40 ms. UHD 730: s-640 65 ms. N100: YOLOv9 s-320 30 ms (one instance only). N150: YOLOv9 t-320 16 ms. — [Frigate hardware docs](https://docs.frigate.video/frigate/hardware)
- RTX 3050 (ONNX + CUDA Graphs, not TensorRT): YOLOv9 t-320 8 ms, s-320 10 ms, s-640 28 ms. RTX 5060 Ti: s-640 22 ms. — [Frigate hardware docs](https://docs.frigate.video/frigate/hardware)
- AMD 780M iGPU (ROCm, Linux): YOLOv9 t-320 ~14 ms, s-320 20 ms. AMD Ryzen AI XDNA2 NPU (Strix Halo): YOLOv9 s-320 ~9.0 ms, s-640 ~20.0 ms. Apple M3 Pro: YOLOv9 s-640 20 ms. Jetson: typically 20–40 ms. — [Frigate hardware docs](https://docs.frigate.video/frigate/hardware)

**AMD on Windows**
- AMD's PyTorch-on-Windows ROCm is a public preview (ROCm 6.4.4, 2025). It covers Radeon 9000 and select 7000 series plus Ryzen AI Max 300 and select AI 300 APUs. — [AMD blog: Road to ROCm on Radeon for Windows and Linux](https://www.amd.com/en/blogs/2025/the-road-to-rocm-on-radeon-for-windows-and-linux.html)
- The 780M (gfx1103) is not officially supported on Windows, and `HSA_OVERRIDE_GFX_VERSION` does not work there. Community "TheRock" nightly builds enable gfx1103 but report hangs and device-enumeration bugs (2025 community reports). — [Habr article](https://habr.com/en/articles/967998); [community setup guide](https://scbz4learning.github.io/Capstone/Environment_Setup/Windows/0.pytorch)
- The Ryzen AI NPU is reached through the Vitis AI Execution Provider in ONNX Runtime, and models generally have to be quantized first. The Ryzen AI Model Zoo on Hugging Face offers quantized YOLOv8. AMD's only pipeline number I found is a 2024 multi-model pipeline (object detection plus super-resolution on the NPU, Stable Diffusion on the iGPU), not isolated YOLO throughput. — [AMD: model pipelining on NPU and GPU](https://www.amd.com/de/developer/resources/technical-articles/model-pipelining-on-npu-and-gpu-using-ryzen-ai-software.html)

**CLIP / ViT on OpenVINO**
- A community OpenVINO conversion of CLIP ViT-B/32 reports only a ~1.12× speed-up over PyTorch (about 0.46 s vs 0.52 s mean). Hardware and precision are not stated, so this is a weak data point. — [scaleflex/clip-vit-base-patch32-openvino](https://huggingface.co/scaleflex/clip-vit-base-patch32-openvino)
- The official OpenVINO notebook converts CLIP (openai/clip-vit-base-patch16) to IR and applies NNCF post-training INT8 quantization. The steps are said to apply to other CLIP-family models. I could not extract its measured numbers. — [OpenVINO CLIP zero-shot notebook (2025)](https://docs.openvino.ai/2025/notebooks/clip-zero-shot-classification-with-output.html)

### Inferences
- **Where the speed-ups come from.** The OpenVINO ratios are 3.6× (155H, FP32) to about 8× (258V/358H) for YOLO26n, and 4–15× for YOLO26s. These are far larger than any PyTorch-side tuning, so a restaurant PC with an Intel iGPU should move to OpenVINO first. On Lunar and Panther Lake, OpenVINO FP16 is already about as fast as INT8 for the nano model (3.34 vs 3.46 ms; 4.03 vs 4.24 ms). INT8 pays off mainly on older or weaker devices (155H: 1.6–1.8× over FP16) and on larger models.
- **Scaling the published numbers to 960 px.** Compute scales roughly with pixel count, so 960 px costs about (960/640)² ≈ 2.25× the 640-px figures. Pose-n is about 1.4× detect-n in FLOPs (7.6 vs 5.5 GFLOPs). Rough per-run estimates at 960 px (my extrapolations, not measurements):
  - 155H OpenVINO INT8: pose-n ~18 ms, detect-s ~21 ms.
  - 258V FP16: pose-n ~10 ms, detect-s ~10 ms.
  - Compare the 6800H PyTorch baseline: pose 75 ms, detect 138 ms.
- **AMD Ryzen 7 6800H machines.** The 6800H (Rembrandt) has no XDNA NPU (general knowledge; verify), and its Radeon 680M (gfx1035) is not in AMD's Windows ROCm preview list. The realistic options are:
  - ONNX Runtime CPU, or OpenVINO's CPU plugin (it runs on x86 AVX2 CPUs, but I found no AMD benchmark).
  - DirectML / Windows ML on the 680M. DirectML is in sustained engineering and I found no YOLO26 numbers for it.
- **TensorRT on Windows laptops.** TensorRT works on Windows. Because engines are device-specific, the installer has to build the engine on each restaurant's GPU at first run (or ship per-GPU engines).
- **The NVIDIA bottleneck after TensorRT.** The Easy FnB RTX 3050 numbers (22–26 ms) are far above T4-TensorRT model times (1.8–2.7 ms at 640, about 4–6 ms scaled to 960). Most of the current GPU latency is probably PyTorch/Python overhead plus pre- and post-processing, which TensorRT FP16 plus GPU-side preprocessing would remove.

### Gaps
- I found no published YOLO26 or YOLO11 benchmark on 12th–14th-gen Core i5 Iris Xe through OpenVINO, other than Frigate's YOLOv9 numbers.
- I found none on RTX 3050 or 4060 with TensorRT for YOLO26 specifically.
- I found none on the Radeon 680M/780M with DirectML.
- The Intel OEP tutorial with YOLO11s CPU/GPU/NPU benchmark_app results returned 404.
- I found no authoritative OpenVINO or ONNX Runtime latency for CLIP ViT-B/32 image-encoder FP16 vs INT8 on a named CPU or iGPU. The OpenVINO notebook output could not be parsed, and the 1.12× figure is from an unverified community model card.
- I could not confirm whether the OpenVINO CPU plugin is officially supported or tuned on AMD Ryzen.

## Q2. Quantization: INT8 and FP16 speed-up and accuracy cost (YOLO detect/pose, CLIP)

### Takeaway
FP16 is essentially free in accuracy on GPUs and iGPUs. For example, YOLO26n on Orin Nano TensorRT FP16 scored mAP 0.4800 vs 0.4770 for FP32, and OpenVINO FP16 matches FP32. INT8 typically costs about 1.3–3 mAP points on YOLO detect: OpenVINO 1.3–1.9 points on YOLO26n/s, TensorRT about 3 points on YOLO26n on Jetson and 4 points on YOLOv8n. I found no published YOLO-pose INT8 keypoint-accuracy measurement. Evidence from detection heads and one posture paper suggests the regression/keypoint head is the fragile part, so pose should run in FP16, or in INT8 with the head kept at higher precision.

### Cited Findings
- OpenVINO INT8 accuracy (Ultralytics tables; the mAP values are on Ultralytics' small benchmark val set, not full COCO):
  - 155H: YOLO26n 0.4758 → 0.4573 (−1.85 pts); YOLO26s 0.5616 → 0.5450 (−1.66).
  - 258V: YOLO26n 0.4764 → 0.4634 (−1.3); YOLO26s 0.5616 → 0.5462 (−1.5); YOLO26l 0.6203 → 0.5938 (−2.65).
  - FP16 equals FP32 to four decimals.

  — [Ultralytics OpenVINO integration](https://docs.ultralytics.com/integrations/openvino/)
- OpenVINO INT8 speed vs FP16 for YOLO26n: 155H 9.07 → 5.79 ms (1.57×); 258V 3.34 → 3.46 ms (no gain); 358H 4.03 → 4.24 ms (no gain). For YOLO26s: 155H 16.65 → 9.27 (1.8×); 258V 4.65 → 3.99 (1.17×). — [Ultralytics OpenVINO integration](https://docs.ultralytics.com/integrations/openvino/)
- TensorRT on Jetson, YOLO26n mAP: Orin Nano Super FP16 0.4800 → INT8 0.4490 (−3.1 pts) for 4.57 → 3.80 ms (1.2×); AGX Orin −1.5 pts. INT8 calibration should be done on the target device. — [Ultralytics Jetson guide](https://docs.ultralytics.com/guides/nvidia-jetson/)
- TensorRT YOLOv8n (older 2024 result): mAP50-95 0.37 → 0.33 with INT8 on A100 and consumer GPUs, and 0.32 on Orin NX. Consumer-GPU latency is FP16 0.62 → INT8 0.52 ms (1.2×). The page warns that INT8 "decreases in evaluation metrics" are likely, and that small calibration batches give inaccurate scaling. — [Ultralytics TensorRT integration](https://docs.ultralytics.com/integrations/tensorrt/)
- One Android study reports INT8 costing about 6.5 mAP points on average across YOLO sizes. A TensorRT study reports about 3–7% mAP50-95 drop for static INT8 (search-snippet level; not fully read). — [arXiv 2511.13453](https://arxiv.org/pdf/2511.13453); [arXiv 2508.19600](https://arxiv.org/html/2508.19600v2)
- Why YOLO INT8 can collapse: pixel-coordinate outputs and class scores have very different ranges. Keeping the final detection head in FP32 raised yolov8n INT8 (TFLite) from 32.9 to 35.2 mAP50-95, and per-channel quantization also helped. — [Cloudflight engineering: Quantized YOLO for Edge](https://engineering.cloudflight.io/quantized-yolo-for-edge-solutions)
- Pose-adjacent evidence: in a sitting-posture study, a two-stage keypoint pipeline lost 10.4% accuracy after edge quantization because of "distortions to the keypoint outputs," versus a 5.2% drop for a single-stage model. — [LSP-YOLO, arXiv 2511.14322](https://arxiv.org/pdf/2511.14322)
- OpenVINO/NNCF offers accuracy-controlled quantization, which keeps the most sensitive operations at original precision. — [OpenVINO YOLOv8 accuracy-control notebook (2024)](https://docs.openvino.ai/2024/notebooks/yolov8-quantization-with-accuracy-control-with-output.html)
- The OpenVINO CLIP notebook applies NNCF post-training INT8 to the CLIP model using a subset of data for calibration (no numbers extracted). — [OpenVINO CLIP notebook](https://docs.openvino.ai/2025/notebooks/clip-zero-shot-classification-with-output.html)

### Inferences
- **Recommended precision per device:**
  - GPU or iGPU: FP16 (TensorRT FP16 / OpenVINO FP16) for both pose and detect. It is free in accuracy and close to INT8 in speed on modern parts.
  - CPU-only or older iGPUs (Meteor Lake class or older): INT8 for the detector (yolo26s), where the gain is 1.6–1.8×.
- **INT8 for pose.** If pose goes to INT8, quantize the backbone and neck but keep the keypoint/box head in FP16/FP32. NNCF supports this through ignored scopes or accuracy-control mode (feature names from general knowledge; verify). Validate OKS keypoint AP and the downstream behaviour metrics on restaurant footage before shipping.
- **INT8 for CLIP.** CLIP embeddings are matched by cosine similarity against prompts or galleries, so INT8 drift shows up as threshold changes. Re-tune similarity thresholds after quantizing, or keep CLIP in FP16.

### Gaps
- I found no published YOLO26-pose or YOLO11-pose INT8 keypoint mAP numbers on OpenVINO or TensorRT.
- I found no published INT8 vs FP16 latency or zero-shot accuracy numbers for CLIP ViT-B/32 on OpenVINO, ONNX Runtime or TensorRT. The OpenVINO notebook output exists but could not be extracted.

## Q3. Video decoding and pipeline: hardware decode, batching, frame skipping, motion gating

### Takeaway
Decoding can become the bottleneck before inference. Every frame of an H.264/H.265 stream has to be decoded even if only 5 fps are analysed, so the biggest cheap win is to pull the NVR/camera **substream** at low resolution and frame rate, and to use hardware decode (Quick Sync / NVDEC). The fixed decode blocks have hard limits: Orin Nano decodes about 2× 4K30 H.265, and Orin NX 18× 1080p30 H.265. Motion gating and per-camera frame skipping are the standard ways NVRs like Frigate stretch capacity.

### Cited Findings
- Frigate guidance:
  - Hardware-accelerated decoding ("hwaccel") helps, and Coral accelerators do not help decoding.
  - Lowering resolution and frame rate on the camera reduces decode load.
  - Use multiple substreams so detection, live view and recording each get an appropriate resolution without re-encoding.
  - H.264 + AAC gives the most compatibility.
  - Tune motion masks before adding accelerators when detection fps nears the ceiling.

  — [Frigate hardware docs](https://docs.frigate.video/frigate/hardware)
- Frigate does not list Windows as a supported host. The page notes that mini PCs often ship with Windows and you will need to install Linux, and that Apple Silicon cannot run Frigate inside a container. — [Frigate hardware docs](https://docs.frigate.video/frigate/hardware)
- NVIDIA Jetson decode limits:
  - Orin Nano spec: 2× 4K30 H.265 decode (NVIDIA forum).
  - Orin NX 16 GB datasheet: 2× 4K60, 4× 4K30, 9× 1080p60 or 18× 1080p30 (H.265). NVDEC max clock is the same across power modes.

  — [NVIDIA forum: 4K on Jetson](https://forums.developer.nvidia.com/t/processing-4k-images-with-deepstream-on-jetson/302069); [NVIDIA forum: Orin NX NVDEC capacity](https://forums.developer.nvidia.com/t/orin-nx-16gb-nvdec-capacity-for-4x-2560x1440-h-265-streams-and-super-mode-impact/380328)
- A forum user estimated from NVIDIA's support matrices that an RTX 3090 can decode about 18 1080p30 H.264 or about 40 HEVC streams. Others note that real NVDEC capacity depends on codec, bitrate, GOP/key-frame interval and clocks. Near the limit, per-stream fps silently drops below 30. NVIDIA suggests testing with parallel `gst-launch-1.0` decode pipelines while watching NVDEC utilisation. — [NVIDIA forum: 1080p30 per NVDEC](https://forums.developer.nvidia.com/t/how-much-1080-30fps-can-be-run-in-one-nvdec/376889); [NVIDIA forum: >12 streams in DeepStream](https://forums.developer.nvidia.com/t/cant-able-able-run-more-than-12-stream-in-deepstream/233718)
- Anecdote (ARM board, not x86): decoding 4 RTSP streams at 30 fps used about 6% CPU with hardware decode, versus an estimated >25% in software. A valid test must actually decode (`-hwaccel …` with `-f null -`), not stream-copy. — [Pine64 forum](https://forum.pine64.org/showthread.php?pid=105542)
- Intel guidance for Quick Sync throughput: keep frames in video memory, build GPU-only pipelines and run stages asynchronously. One older Core i3 user handled 8× 1080p30 Quick Sync *encodes* at once. — [Intel community: FFmpeg QSV optimisation](https://community.intel.com/t5/Media-Intel-Video-Processing/FFMPEG-Quick-Sync-Acceleration-Performance-Optimization/td-p/1149970)
- A CCTV software (Shinobi) project post reports mixed VA-API/VDPAU results and Quick Sync crashing FFmpeg. This is a low-quality source, but it shows driver/setup fragility. — [Freelancer project post](https://www.freelancer.hk/projects/bash-scripting/hardware-acceleration-for-shinobi-cctv)
- DeepStream suits multi-stream pipelines with TensorRT models. Ultralytics staff suggest JetPack 6.1 + DeepStream 7.1 for Orin Nano, native install first and Docker later. — [Ultralytics Jetson guide](https://docs.ultralytics.com/guides/nvidia-jetson/)
- Frigate's server-capacity guidance:
  - Beelink EQ13 runs detection on "several 1080p cameras with low-to-medium activity."
  - "Intel 1120p" handles many 1080p cameras with high activity.
  - Intel 125H handles "a significant number of 1080p cameras with high activity."

  These are qualitative; Frigate runs detection only where there is motion and uses small detector inputs (320/640). — [Frigate hardware docs](https://docs.frigate.video/frigate/hardware)

### Inferences
- **Decode budget.** Suppose the NVR delivers 1080p at 25 fps. Each camera then costs 25 decoded 1080p frames per second, even though inference runs at 5 fps. Software decode of 4–8 such streams on a Core i3/i5 is likely to consume a large share of the CPU, which hurts CPU-only inference badly (I found no clean x86 benchmark; see Gaps).
- **Use the substream.** Point Easy FnB at the NVR substream: 720p or 640×480/D1, with the substream fps set to 5–10. This reduces decode cost several-fold. 720p (1280 px wide) is still enough for a 960-px model input. Reserve the main stream for snapshots or evidence crops only.
- **Hardware decode per platform:**
  - Intel PCs: FFmpeg/OpenCV with `-hwaccel qsv` or `d3d11va` on Windows. Better still is a GStreamer/DL Streamer-style pipeline that keeps frames on the iGPU and feeds OpenVINO GPU tensors with zero copy.
  - NVIDIA: NVDEC (FFmpeg `-hwaccel cuda`, PyNvVideoCodec, or DeepStream on Linux/Jetson).
- **Gating and skipping:**
  - Motion gating: run detect/pose only when frame-difference or background-subtraction motion exceeds a threshold.
  - Adaptive fps: drop to 1–2 fps on idle cameras (empty tables or kitchen at night).
  - CLIP only on new or changed tracks rather than on fixed crops per second.
  - In restaurants, many cameras are idle much of the day, so this multiplies effective capacity, as in Frigate's motion-first design.
- **Batching.** Batching frames from N cameras into one inference call (batch = N) improves GPU/iGPU utilisation. YOLO26's NMS-free head keeps post-processing cheap per batch. TensorRT needs a dynamic or fixed batch at export (`dynamic=True` allows smaller-than-max batches). OpenVINO offers async infer requests and throughput hints (general knowledge).
- **Windows constraint.** DeepStream and Frigate are Linux-first. On Windows, the practical stack is FFmpeg/PyAV/OpenCV with hardware decode, plus OpenVINO / ONNX Runtime / TensorRT in-process. A WSL2 or Linux mini-PC appliance is the alternative.

### Gaps
- I found no reliable published benchmark of CPU utilisation for software vs Quick Sync decode of 4–8 1080p H.264/H.265 RTSP streams on Intel Core i3/i5 or N100 under Windows.
- I found no NVDEC stream-count figure for RTX 3050/4060 laptop GPUs; the NVIDIA Video Codec SDK support matrix was not retrieved.
- I found no Intel DL Streamer or Roboflow Inference multi-stream density numbers in this pass.

## Q4. Realistic camera counts per device class

### Takeaway
There are no published per-camera numbers for this exact pipeline (pose at 960 px plus detect plus CLIP at 5 fps), so counts must be extrapolated from detector benchmarks. At the current 960-px settings, my rough estimates are:

| Device class | Estimated cameras |
|---|---|
| N100 | ~1–2 (needs 640 px and fewer pose frames) |
| Iris Xe i5 (12th–14th gen) | ~3–5 |
| Core Ultra 2xxV/3xx | ~6–12 |
| RTX 3050 laptop with TensorRT FP16 | ~10–15 |
| Jetson Orin Nano Super | ~6–10 |

In practice, decode, Python overhead and CLIP will set the ceiling. The single most effective knob is dropping pose input from 960 to 640 px, which cuts compute about 2.25×.

### Cited Findings (inputs to the estimates)
- Intel N100/N150 (Frigate, OpenVINO iGPU): YOLOv9 s-320 30 ms on N100 (one instance only); YOLOv9 t-320 16 ms and s-320 24 ms on N150. — [Frigate hardware docs](https://docs.frigate.video/frigate/hardware)
- LattePanda Mu, YOLO11n on the iGPU via OpenVINO: about 21 FPS detect and 15 FPS pose, several times the CPU-only rate. The board is N100-based according to LattePanda, but this was not confirmed in the fetched text. — [DigiKey Maker.io: YOLO11 7× with OpenVINO on LattePanda Mu](https://www.digikey.com/en/maker/tutorials/2025/yolo11-speed-boosted-by-7x-with-openvino-on-lattepanda-mu); [LattePanda blog](https://lattepanda.com/blog-323240.html)
- Iris Xe (Frigate): YOLOv9 t-640 14 ms, s-640 16 ms. UHD 770 (desktop 12th–14th gen): YOLOv9 s-640 ~40 ms. Intel NPU: s-640 30 ms. — [Frigate hardware docs](https://docs.frigate.video/frigate/hardware)
- Core Ultra OpenVINO, YOLO26 at 640: 155H n-INT8 5.79 ms and s-INT8 9.27 ms; 258V n-FP16 3.34 ms and s-INT8 3.99 ms; 358H n-FP16 4.03 ms and s-INT8 4.47 ms. — [Ultralytics OpenVINO integration](https://docs.ultralytics.com/integrations/openvino/)
- RTX 3050 (Frigate, ONNX + CUDA Graphs): YOLOv9 s-640 28 ms. T4 TensorRT10: YOLO26n-pose 1.8 ms, YOLO26s 2.5 ms at 640. — [Frigate hardware docs](https://docs.frigate.video/frigate/hardware); [Ultralytics Pose docs](https://docs.ultralytics.com/tasks/pose/); [Ultralytics YOLO26 docs](https://docs.ultralytics.com/models/yolo26/)
- Jetson Orin Nano Super: YOLO26n TRT FP16 4.57 ms and INT8 3.80 ms at 640, excluding pre- and post-processing. NVDEC is about 2× 4K30 H.265. — [Ultralytics Jetson guide](https://docs.ultralytics.com/guides/nvidia-jetson/); [NVIDIA forum](https://forums.developer.nvidia.com/t/processing-4k-images-with-deepstream-on-jetson/302069)
- AMD: 780M iGPU (ROCm, Linux) YOLOv9 s-320 20 ms; Ryzen AI XDNA2 NPU (Strix Halo) s-640 ~20 ms; 8700G ~40 ms at 640. — [Frigate hardware docs](https://docs.frigate.video/frigate/hardware)
- Frigate qualitative capacity: Beelink EQ13 handles "several 1080p cameras with low-to-medium activity," and Intel 125H "a significant number … with high activity." — [Frigate hardware docs](https://docs.frigate.video/frigate/hardware)

### Inferences (my arithmetic; treat as order-of-magnitude, to be confirmed by measuring on target devices)
Per-camera load at the current settings, in 640-px-equivalent runs per second:
- Pose-n: 5 runs/s × 2.25 (960-px scale) ≈ 11.3 runs/s. Each pose run costs about 1.4× a detect-n run.
- Detect-s every 3rd frame: about 1.67 runs/s × 2.25 ≈ 3.75 runs/s.
- CLIP: about 3 crops/s.

The camera count is (1000 ms × target utilisation) divided by the per-camera ms. A 60–70% utilisation leaves room for decode, tracking and Python. Model-only times exclude pre- and post-processing, so real throughput will be lower.

- **Ryzen 7 6800H, PyTorch CPU (measured baseline).** About 375 ms pose + 230 ms detect + 120 ms CLIP ≈ 725 ms per camera-second, so about 1–1.5 cameras. This matches the measured 8–9 fps total. ONNX Runtime or OpenVINO-CPU INT8 might plausibly give 2–3× on the CPU, which would mean about 3 cameras (no AMD benchmark found).
- **N100 (iGPU, OpenVINO).** Pose-n at 960 is about 9× the 320-px cost: roughly 16 ms × 9 ≈ 140 ms per run, or ~700 ms per camera-second for pose alone. That is about 1 camera at current settings. At 640 px, pose every frame and detect every 6th frame, it is about 2–3 cameras. Frigate's "one instance only" note means no parallel detectors.
- **Core i5/i7 12th–13th gen with Iris Xe (OpenVINO GPU).** Pose about 14 ms × 2.25 ≈ 31 ms per run, so ~160 ms per camera-second. Detect-s about 36 ms per run, so ~60 ms per camera-second. Total about 220 ms + CLIP (put CLIP on the CPU), giving about 3–4 cameras, or 6–8 at 640 px. Desktop UHD 770 iGPUs are about 2.5× slower than Iris Xe, so about 1–2 cameras at 960 px.
- **Core Ultra 2xxV / 3xx (Lunar/Panther Lake, OpenVINO iGPU plus NPU).** Pose about 3.3 × 2.25 × 1.4 ≈ 10.5 ms per run (~53 ms per camera-second). Detect-s about 9 ms per run (~15 ms per camera-second). That suggests about 10–14 cameras on inference alone, so realistically 6–12 once decode and Python overhead are included. Offloading detect or CLIP to the NPU frees iGPU time; in Frigate's numbers the NPU is slower than the iGPU but still useful as a second engine. On 155H Meteor Lake the YOLO26 NPU path is unsupported and the iGPU is slower: about 18 ms pose and 21 ms detect per run, giving about 4–6 cameras.
- **RTX 3050 4 GB laptop (TensorRT FP16).** Model-only time is about 4–8 ms per pose run at 960 and 6–10 ms per detect-s run, so about 30–40 ms pose plus 15 ms detect per camera-second. That allows roughly 15–20 cameras on inference alone. The ceiling will then be NVDEC, CPU preprocessing and 4 GB of VRAM (multiple engines plus CLIP), so 10–15 is a realistic target versus about 6 today (31 fps ÷ 5). RTX 4060 (laptop or desktop) would be roughly 1.5–2× more.
- **Jetson Orin Nano Super (TRT FP16).** Pose about 4.57 × 2.25 × 1.4 ≈ 14 ms per run (~72 ms per camera-second). Detect-s is about 6.9 ms at 640 if one assumes T4-like s/n ratios, or ~15 ms at 960 (~26 ms per camera-second). That gives about 7–10 cameras, but NVDEC (~8× 1080p30) caps it unless low-fps or low-resolution substreams are used.
- **Ryzen with Radeon 680M/780M on Windows.** No reliable accelerated path for YOLO26 on Windows was found. Plan for CPU-only capacity (about 2–3 cameras after optimisation) unless DirectML/Windows ML proves workable in testing.
- **Biggest knobs, in order:**
  - Runtime switch (OpenVINO or TensorRT): 3–8×.
  - Pose input 960 → 640 px: 2.25×.
  - Detect every 6th instead of every 3rd frame: 2× on detect.
  - Motion/occupancy gating: depends on scene; often several × off-peak.
  - FP16 or INT8 on top: 1.2–1.8×.

### Gaps
- I found no published end-to-end camera-count benchmark for a YOLO-pose + tracker + CLIP pipeline on any of these devices. All counts above are extrapolations from single-model latencies, mostly measured at 320/640 px and excluding pre- and post-processing.
- I found no RTX 4060 YOLO26 TensorRT figures, and no Jetson Orin Nano Super YOLO26s or pose-specific figures.

## Q5. Cloud alternative: Cloud Run GPU (NVIDIA L4) cost per camera-hour, and Vietnam bandwidth

### Takeaway
Cloud Run GPUs are available in Singapore (asia-southeast1: L4 24 GB and RTX PRO 6000) with about 5 s cold starts. However, they require instance-based billing, so a continuously streaming deployment pays for the whole instance all the time. That is roughly $0.67–1.05 per GPU-hour for the L4 before CPU and memory charges (Singapore rate not confirmed). For 24/7 or open-hours CCTV, an existing PC or a one-time edge device is almost certainly cheaper unless one L4 is shared across many restaurants. Vietnamese fixed broadband (Hanoi median upload about 199 Mbps, Aug 2026) can technically carry several substreams per site.

### Cited Findings
- Cloud Run GPU types and limits:
  - L4 (24 GB) and RTX PRO 6000 Blackwell (96 GB), one GPU per instance, driver 580.x (CUDA 13.0).
  - Singapore asia-southeast1 supports both. Mumbai L4 is by invitation; Delhi has RTX PRO 6000 only.
  - L4 minimum 4 vCPU / 16 GiB (8 vCPU / 32 GiB recommended); RTX PRO 6000 minimum 20 vCPU / 80 GiB.
  - Instance-based billing is mandatory and there are no per-request fees.
  - Scale-to-zero is possible, but minimum instances are billed at the full rate.

  — [Cloud Run GPU docs](https://docs.cloud.google.com/run/docs/configuring/services/gpu)
- Zonal redundancy is on by default and costs more per GPU-second; turning it off gives best-effort failover at a lower price. The default quota on first deployment in a region is 3 GPUs with zonal redundancy off. GPU instances with pre-installed drivers start in about 5 s. — [Cloud Run GPU docs](https://docs.cloud.google.com/run/docs/configuring/services/gpu)
- Price (the official pricing page could not be rendered by the fetch tool; figures come from search results):
  - Official page, Phoenix (us-west8) example: L4 $0.0001867/GPU-s without zonal redundancy (≈ $0.67/h) and $0.0002909/GPU-s with it (≈ $1.05/h).
  - A third-party mirror lists L4 at $0.0002796/GPU-s (≈ $1.01/h) for Tier-2 regions and groups Singapore in Tier 2. Unverified and possibly outdated.
  - Hourly conversions are my arithmetic. CPU and memory charges come on top and were not retrieved.

  — [Cloud Run pricing (official, via search snippet)](https://cloud.google.com/run/pricing); [third-party mirror (unverified)](https://siteproxy.yy6.workers.dev/https/cloud.google.com/run/pricing)
- Cloud Run also offers GPU support for worker pools (non-HTTP background workers), which fits a design that pulls RTSP streams continuously. — [Cloud Run worker pools GPU docs](https://docs.cloud.google.com/run/docs/configuring/workerpools/gpu?authuser=2)
- Vietnam bandwidth (Speedtest-based news reports):
  - Hanoi fixed broadband, Aug 2026: median 251.94 Mbps down, 199.35 Mbps up, 4 ms latency.
  - Vietnam national fixed broadband, July 2026: median download ~255.87 Mbps, 7th globally.
  - I found no national median upload figure. A browser-based tester (SpeedOf.Me, all connection types) reports a 33.6 Mbps median upload for Vietnam, which is not comparable.

  — [VietNamNet (Hanoi, Oct 2026)](https://vietnamnet.vn/en/hanoi-becomes-world-s-fifth-fastest-city-for-mobile-internet-2564633); [The Star / ANN (Oct 2026)](https://www.thestar.com.my/aseanplus/aseanplus-news/2026/10/14/hanoi-becomes-world039s-fifth-fastest-city-for-mobile-internet); [Việt Nam News](https://vietnamnews.vn/Sci-Tech/1798899/viet-nam-enters-global-top-10-for-mobile-and-fixed-broadband-speeds.html); [SpeedOf.Me](https://speedof.me/internet-speed/vietnam)

### Inferences (my arithmetic and judgement)
- **Single-restaurant instance, open hours.** One always-on L4 instance for 12 h/day × 30 days = 360 h, so about $240–380/month in GPU charges alone ($0.67–1.05/h), plus vCPU and memory for at least 4 vCPU / 16 GiB. For one restaurant with 4–8 cameras, that is about $0.08–0.26 per camera-hour.
- **Multi-tenant sharing.** If one L4 serves ~20–30 cameras across several restaurants, GPU cost falls to about $0.02–0.05 per camera-hour. That needs a shared, always-on fleet and reliable ingest.
- **Is the L4 itself the limit?** With TensorRT FP16, an L4 should handle far more than 20 cameras of this workload on compute alone; the L4 has more NVDEC capacity than a T4 (general knowledge, verify). Decode and network ingest, not the GPU, would likely set the count.
- **Bandwidth per site.** A 1080p H.264 CCTV main stream is typically about 2–4 Mbps, and a 720p or D1 substream about 0.5–1 Mbps (general knowledge, not sourced here). Eight substreams therefore need about 4–8 Mbps of sustained upload, and eight main streams about 16–32 Mbps. Both are well within Hanoi's median, but they compete with the restaurant's POS/Wi-Fi traffic.
- **Cross-border risks.** International connectivity from Vietnam to Singapore adds latency and is exposed to submarine-cable incidents (general knowledge, not sourced here). Real-time alerts would degrade during outages. Sending video off-site also raises privacy and consent questions.
- **Hybrid recommendation.** Do pose, tracking and detection on the edge PC. Send only events, crops or embeddings to the cloud, and use a cloud GPU only for occasional heavier models (re-ranking, VLM review). This keeps cloud cost to pennies per camera-day.

### Gaps
- I could not confirm the official Cloud Run L4 per-second price for asia-southeast1 (Singapore), its tier, or the vCPU/GiB-second instance-billing rates, because the pricing page would not render in the fetch tool. These must be checked on the live pricing page or the Cloud Billing SKU catalog.
- I found no official Ookla national median fixed-upload figure for Vietnam in 2026, and no data on restaurant-tier (SME) ISP plan upload caps.
- I found no source on Vietnam-to-Singapore latency or cable-outage frequency in 2026.
