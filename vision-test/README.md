# vision-test: edge vision pipeline

The part of [Easy FnB](../README.md) that watches the camera. It reads a video file, webcam or RTSP stream, works out what is happening at each table, and sends events, cropped images and live frames to the server.

| File | Role |
|---|---|
| `easyfnb_test.py` | The pipeline: detection, tracking, pose, table state machine, face blurring |
| `fnb_common.py`, `clip_cls.py`, `hanh_dong.py` | Shared helpers, image-encoder classifiers, action scoring |
| `khop_ban.py`, `nhin_quanh.py`, `an_ninh.py` | Person-to-table matching, "looking around" signal, security alerts |
| `gui_may_chu.py` | Client that pushes events and frames to the server |
| `xuat_engine.py` | Exports the TensorRT engines (must be re-run on each machine) |
| `danh_gia/`, `do_chinh_xac.py` | Labels and scoring scripts |
| `thu_nghiem/` | Experiments: what was tried, what was kept |
| `train/`, `models/` | Training scripts and the small classifier heads (a few KB each) |
| `test_*.py` | Unit tests for the pure-logic parts |

Videos and large model weights are not in the repository. Base weights download on first use; the footage sources are listed in `clips/NGUON.md` and `video_mang/NGUON.md`.

## Run

Needs an NVIDIA GPU and a one-time environment setup, described in [`../easy-fnb/HUONG_DAN.md`](../easy-fnb/HUONG_DAN.md).

```
chay_camera.bat <source> [server] [camera id]
```

`<source>` is a video file, a webcam number or an `rtsp://` URL.

## Results

- [KET_QUA.md](KET_QUA.md): accuracy and speed, with method
- [thu_nghiem/KET_LUAN.md](thu_nghiem/KET_LUAN.md): experiments and conclusions
