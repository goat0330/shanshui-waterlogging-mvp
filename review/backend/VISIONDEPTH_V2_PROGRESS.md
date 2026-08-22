# VisionDepth V2 LeanGuard progress

状态：`CONDITIONAL`

## 当前实现

本轮在独立 `backend/visiondepth_v2/` 中完成了最小 V2 证据边界：

- 复用现有 `vision.pipeline.run_pipeline` 和 `media.video_pipeline.run_video_pipeline`，没有建立第二套水域/参照物/水深逻辑。
- 增加本地 MP4 manifest/data gate：只接受授权、许可证字段明确、可解码、至少 30 帧的 `.mp4`。
- 增加逐帧 `frameId + timestampMs + observation` 包装、结果 JSON、mask 路径和 overlay metadata 汇总。
- 增加 camera calibration guard。没有 calibrated CameraProfile 时，`estimatedDepthCm` 强制为 `null`，confidence 上限为 `0.45`，并增加 `CAMERA_UNCALIBRATED`。
- 增加 external-command adapter，但默认被 license gate 阻断；没有复制 V-FloodNet 源码、权重、数据或视频。
- 没有修改 `contracts/**`、`backend/app/**`、`vision/**`、`media/**`、前端或传感器状态。

固定 `VisionDepthObservation` contract 未改变。视频层只增加时间戳和 evidence packaging，不写入 `SensorState`，不覆盖 `FloodPoint.currentDepthCm`。

## 实际运行结果

运行目录：`backend/visiondepth_v2/`

| 命令 | 实际结果 |
|---|---|
| `python -m pytest -q` | `3 passed in 0.27s` |
| `python -m compileall -q src tools tests` | `PASS`（从 package 目录运行） |
| `python -m vision.smoke` | `PASS`，3 张既有图片；`flood_person level=3 estimate=25.4`，`flood_no_reference level=5 estimate=null`，`dry_street flood=false level=0` |
| `python -m tools.data_gate --config configs/local.yaml` | exit `2`，`VIDEO_SOURCE_REQUIRED`；manifest 不存在 |
| `python -m tools.video_smoke --config configs/local.yaml` | exit `2`，`VIDEO_SOURCE_REQUIRED`；未创建伪造帧/伪造 CCTV 结果 |
| `python -m tools.check_third_party` | exit `2`，V-FloodNet 和 flood-water-segmentation 仍为 `license_review: pending` |
| `git diff --check` | `PASS` |

无视频时生成的明确状态 artifact（被 `.gitignore` 忽略，不作为产品数据提交）：

`backend/visiondepth_v2/outputs/smoke/VIDEO_SOURCE_REQUIRED/smoke_summary.json`

它记录 `sampledFrames: 0`、`synthetic: false`，以及 `real_video_evidence` / `per_frame_inference` 为 `notVerified`。

## 当前缺少的输入

当前项目和外置数据根都没有可用 MP4；本轮未下载大型数据集，也未下载模型权重。data gate 期望：

`data/visiondepth/manifests/video_manifest.csv`

以及 manifest 中指向的本地视频。建议至少提供 3 个已授权、可解码、每个不少于 30 帧的短视频：`flood_with_reference`、`flood_without_reference`、`non_flood`。每行还应记录 `source_url`、`license`、`authorized`、`captured_at`、`camera_id`、`scenario`。

因此本轮能完成的是 pipeline/data gate/拒绝路径验证；不能宣称真实视频逐帧 smoke 已通过。

## 依赖、模型和许可证

- 已使用环境中的 Python 3.11、OpenCV、NumPy、Pillow、PyYAML、pytest；没有新增大型训练栈。
- V1 的水域/参照物实现仍是 OpenCV baseline，模型权重为 `not_used`，因此结果只能作为低置信度视觉证据。
- Depth Anything V2 未接入；不把单目深度直接当作厘米水深。
- V-FloodNet 只登记为外部研究参考/未来 adapter。其公开 README 标注 “All rights are reserved”，在完成许可证和数据/权重授权审核前不下载、不 vendoring、不运行。来源：[V-FloodNet README](https://github.com/xmlyqing00/V-FloodNet/blob/main/README.md?plain=1)、[V-FloodNet repository](https://github.com/xmlyqing00/V-FloodNet)。
- `requirements-mvp.txt` 只记录轻量运行依赖；正式发布前仍需按实际锁定环境复核各依赖许可证。

## 哪些结果能输出厘米

当前默认配置没有 calibrated CameraProfile，因此视频和 V2 guard 均不允许输出厘米值：`estimatedDepthCm: null`。只有后续提供合法相机标定资料并通过单独校准/验证，才可讨论 `FIXED_CAMERA_REFERENCE` 或其他参照物的厘米估计；当前不能用普通检测框直接换算真实水深。

无可靠参照物的图片仍只能输出 level/range，且保留 `NO_REFERENCE`、低置信度约束。无标签 split，未输出 MAE、F1、Balanced Accuracy 或任何准确率结论。

## NOT VERIFIED

- 真实授权 MP4 的解码、至少 3 帧逐帧推理、每帧 mask 和 timestamped JSON。
- 真实视频中的水域分割、参照物识别、level/range 和厘米估计质量。
- 任何 V-FloodNet/flood-water-segmentation 权重、模型效果和许可证可运行性。
- CameraProfile 标定参数、几何校准以及厘米尺度误差。
- overlay 的真实像素渲染；当前是 overlay metadata，未生成渲染视频。
- 有标签评估 split 和指标。
- Backend/FastAPI/前端接入；本轮有意未做。

## 最小下一步

1. 由数据责任人放置已授权短 MP4 和 `video_manifest.csv`，不要把原始视频提交 Git。
2. 运行 `python -m tools.data_gate --config configs/local.yaml`，通过后运行 `python -m tools.video_smoke --config configs/local.yaml`。
3. 仅在 license/weights/数据授权明确且真实 smoke 通过后，评估一个轻量外部 segmentation/reference adapter；否则继续使用 OpenCV baseline 并保持低置信度。

## Checkpoint

- 实现 checkpoint：`61fae2b`（`feat(visiondepth): add guarded video evidence scaffold`）。
- 本文件作为后续文档提交；主 worker 合并时应保留该 checkpoint 和本报告。
