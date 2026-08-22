# VisionDepth V2 LeanGuard progress

状态：`CONDITIONAL`

## 当前实现

本轮在独立 `backend/visiondepth_v2/` 中完成了最小 V2 证据边界：

- 复用现有 `vision.pipeline.run_pipeline` 和 `media.video_pipeline.run_video_pipeline`，没有建立第二套水域/参照物/水深逻辑。
- 增加本地 MP4 manifest/data gate：只接受授权、许可证字段明确、可解码、至少 30 帧的 `.mp4`。
- 增加逐帧 `frameId + timestampMs + observation` 包装、结果 JSON、mask 路径和 overlay metadata 汇总。
- `video_smoke` 现在遍历所有通过 gate 的输入，逐视频写 `video-result.json`、逐视频 summary 和总 summary。
- 增加 camera calibration guard。没有 calibrated CameraProfile 时，`estimatedDepthCm` 强制为 `null`，confidence 上限为 `0.45`，并增加 `CAMERA_UNCALIBRATED`。
- 增加 `runtime_profile: research_mvp`：只允许本地 OpenCV baseline；`license_review` 仍为 `pending`，外部模型、production 和 redistribution 仍被 gate 阻断。
- 本轮只下载指定的 6 个小 MP4 到 Git 外的 `data/visiondepth/videos/`，没有复制 V-FloodNet 源码/权重，也没有下载 Houston 268 MB 或完整数据集。
- 没有修改 `contracts/**`、`backend/app/**`、`vision/**`、`media/**`、前端或传感器状态。

固定 `VisionDepthObservation` contract 未改变。视频层只增加时间戳和 evidence packaging，不写入 `SensorState`，不覆盖 `FloodPoint.currentDepthCm`。

## 实际运行结果

运行目录：`backend/visiondepth_v2/`

| 命令 | 实际结果 |
|---|---|
| `python -m pytest -q` | `5 passed in 0.43s`（包含 runtime profile production gate 测试） |
| `python -m compileall -q backend/visiondepth_v2/src backend/visiondepth_v2/tools backend/visiondepth_v2/tests` | `PASS` |
| `python -m vision.smoke` | `PASS`，3 张既有图片；`flood_person level=3 estimate=25.4`，`flood_no_reference level=5 estimate=null`，`dry_street flood=false level=0` |
| `python -B backend/smoke.py` | `PASS`，既有 backend/contract/telemetry/vision boundary smoke |
| `python -m tools.data_gate --config configs/local.yaml` | `PASS`，4 个视频满足 `authorized + MVP_REVIEW + decodable + >=30 frames`；2 个 11 帧视频被正确排除 |
| `python -m tools.video_smoke --config configs/local.yaml` | `PASS`，4 个视频、25 个 sampled frames、`synthetic=false` |
| `python -m tools.check_third_party --config configs/local.yaml` | `PASS: RESEARCH_MVP_LOCAL_ONLY`；pending 条目仍禁止 production/redistribution/external model |
| artifact audit | `PASS`，25 个 frame JSON、25 个 water mask、timestampMs、overlay metadata 均可重读；每帧 `estimatedDepthCm=null` 且含 `CAMERA_UNCALIBRATED` |
| `git diff --check` | `PASS` |

总视频 smoke artifact（被 `.gitignore` 忽略，不作为产品数据提交）：

`backend/visiondepth_v2/outputs/smoke/smoke_summary.json`

它记录 `status=PASS`、`videoCount=4`、`sampledFrames=25`、`synthetic=false`；每个视频目录还包含 `video-result.json`、逐帧 observation JSON、PNG mask 和 overlay metadata。

## 下载清单与数据 gate

来源目录：[V-FloodNet `water_videos_for_test`](https://huggingface.co/xmlyqing00/V-FloodNet/tree/main/water_videos_for_test)。

下载到：`data/visiondepth/videos/`；manifest：`data/visiondepth/manifests/video_manifest.csv`。

| 文件 | bytes | OpenCV frames | fps | gate |
|---|---:|---:|---:|---|
| `LSU-20200526-Label-1.mp4` | 1,374,552 | 11 | 3 | `REJECT: <30` |
| `LSU-20200526-Label-2.mp4` | 920,051 | 11 | 3 | `REJECT: <30` |
| `LSU-20200624-Label-1.mp4` | 3,594,443 | 38 | 3 | `PASS` |
| `LSU-20200624-Label-2.mp4` | 3,569,908 | 38 | 3 | `PASS` |
| `boston_2019_01_19-20.mp4` | 6,132,879 | 106 | 10 | `PASS` |
| `boston_2019_01_21-23.mp4` | 9,400,420 | 161 | 10 | `PASS` |

6 个文件都存在且 sequential decode 成功；但官方样本中 2 个 LSU 20200526 文件真实只有 11 帧，因此本轮不能宣称“6 个视频均满足 >=30 帧”。没有插帧、复制帧或把 11 帧伪装成合格视频。`houston_2019.mp4`（约 268 MB）未下载。

manifest 使用 `license=MVP_REVIEW`、`authorized=true`。这里的 `authorized=true` 只表示责任人允许文件进入本地研究 MVP pipeline，不是最终版权许可；当前约束是 local-only、no redistribution，最终公开使用许可 deferred。`scenario` 为 smoke 用的 provisional metadata，不作为算法标签或精度证据。

## 依赖、模型和许可证

- 已使用环境中的 Python 3.11、OpenCV、NumPy、Pillow、PyYAML、pytest；没有新增大型训练栈。
- V1 的水域/参照物实现仍是 OpenCV baseline，模型权重为 `not_used`，因此结果只能作为低置信度视觉证据。
- Depth Anything V2 未接入；不把单目深度直接当作厘米水深。
- V-FloodNet registry 保持 `license_review: pending`。其公开 README 标注 “All rights are reserved”；本轮只使用指定 test videos 做本地研究 smoke，不把本地 MVP 授权描述为最终版权许可，也不下载第三方源码/权重。来源：[V-FloodNet README](https://github.com/xmlyqing00/V-FloodNet/blob/main/README.md?plain=1)、[V-FloodNet repository](https://github.com/xmlyqing00/V-FloodNet)。
- `requirements-mvp.txt` 只记录轻量运行依赖；正式发布前仍需按实际锁定环境复核各依赖许可证。

## 哪些结果能输出厘米

当前默认配置没有 calibrated CameraProfile，因此视频和 V2 guard 均不允许输出厘米值：`estimatedDepthCm: null`。只有后续提供合法相机标定资料并通过单独校准/验证，才可讨论 `FIXED_CAMERA_REFERENCE` 或其他参照物的厘米估计；当前不能用普通检测框直接换算真实水深。

无可靠参照物的图片仍只能输出 level/range，且保留 `NO_REFERENCE`、低置信度约束。无标签 split，未输出 MAE、F1、Balanced Accuracy 或任何准确率结论。

## NOT VERIFIED

- 指定 6 个视频全部满足 `>=30 frames`：其中 2 个官方文件只有 11 帧，故 6 路全量 gate 未通过。
- 两个 11 帧视频尚未进入当前 `>=30` gate；没有为它们生成“合格输入”的伪证据。
- 真实视频中的水域分割、参照物识别、level/range 和厘米估计质量。
- 任何 V-FloodNet/flood-water-segmentation 权重、模型效果和最终公开/再分发许可证。
- CameraProfile 标定参数、几何校准以及厘米尺度误差。
- overlay 的真实像素渲染；当前是 overlay metadata，未生成渲染视频。
- 有标签评估 split 和指标。
- Backend/FastAPI/前端接入；本轮有意未做。

## 最小下一步

1. 若验收必须是 6 路 `>=30` 帧，需由数据责任人提供替代/补充授权视频，或确认放宽验收阈值；不能修改原始 11 帧文件来满足阈值。
2. 对新增输入补写 manifest 后运行 `python -m tools.data_gate --config configs/local.yaml`，再运行 `python -m tools.video_smoke --config configs/local.yaml`。
3. 仅在 license/weights/数据授权明确且真实 smoke 通过后，评估一个轻量外部 segmentation/reference adapter；否则继续使用 OpenCV baseline 并保持低置信度。

## RC2 Evidence-Backed Demo Release addendum

### Baseline and ownership

- Canonical Main baseline audited: `595457063e2a1f304ca657695ef86dc76162be3e`。
- This worker fast-forwarded its own worktree to that baseline; Main 工作树未修改。
- RC2 tracked change is limited to this report. Runtime MP4、manifest、hashes and ignored outputs remain outside Git.

### P1 feasibility gate and selected route

本轮只选择路线 A：`water/grounded segmentation adapter`。没有同时启动 flooded-vehicle classifier。

`MODEL_UPGRADE=NOT_VERIFIED`，原因是：

- 环境有 `torch 2.6.0+cu118`、CUDA device 1、`transformers`、`ultralytics`、`timm`、`torchvision`、`onnxruntime`，但没有已登记且可复现的 water-segmentation checkpoint。
- `mmsegmentation`、`detectron2`、`segment_anything` 未安装；本地没有 `.pt/.pth/.onnx/.safetensors/.ckpt` 权重。
- `data/visiondepth/gt_masks`、`depth_gt`、labels split 均不存在，因此不具备 IoU/F1/MAE 或 classifier 指标验证条件。
- 按 20 分钟规则不下载权重/完整数据集、不训练大模型；保持 OpenCV baseline 作为唯一可复现实验路径。

### RC2 evidence and source manifest

`data/visiondepth/manifests/video_manifest.csv` 已增加 `project`、`licenseReview`、`researchMvp`、`production`、`redistribution`、`localPath`、`sha256` 字段。6 行 SHA256 与本地文件复核结果为 `manifest_hash_audit=PASS rows=6`。

字段语义：`licenseReview=pending`、`researchMvp=true`、`production=false`、`redistribution=false`。这是本地 evidence-backed demo 的 provenance 记录，不是公开发布/再分发许可。

真实 baseline comparison（无 GT，只记录观察结果）：

- `VF-LSU-20200624-1/2`：各 3 frames，baseline `flood=true`、`level=5`、`estimatedDepthCm=null`。
- `VF-BOSTON-20190119-20`：8 frames，baseline `flood=false`、`level=0`。
- `VF-BOSTON-20190121-23`：11 frames，baseline `flood=false`、`level=0`。
- 总计 4 个合格视频、25 个 sampled frame JSON、25 个 water mask、25 组 timestamp/overlay metadata；所有视频保持 `synthetic=false`，所有帧保留 `CAMERA_UNCALIBRATED` 和 null 厘米值。

这些 level/flood 值是 OpenCV baseline 的证据输出，不是准确率、生产结论或真实厘米测量。

### RC2 blockers and NOT VERIFIED

- 指定 6 个源视频中 2 个只有 11 frames，未满足现有 `>=30` gate；不能通过插帧、复制帧或修改原文件补齐。
- Water/grounded segmentation adapter 的权重、GT、复现依赖和效果均 `NOT VERIFIED`。
- 未验证厘米尺度、相机标定、真实 overlay 像素渲染、公开/再分发许可和任何模型指标。
- 下一步只需提供替代/补充的 `>=30` 帧授权视频并更新外置 manifest；不需要修改主链或 contracts。

## Checkpoint

- 上一实现 checkpoint：`61fae2b`（`feat(visiondepth): add guarded video evidence scaffold`）。
- 本轮代码 checkpoint：`6e93c45538da6964bffab597fd63a93329d1bf2e`（`feat(visiondepth): enable research MVP video smoke`）。本报告随后单独提交；runtime MP4、manifest 和 outputs 不进入 Git。
- RC2 report checkpoint：`bee38d5aa5d0492cf919cdbefef893945ff1ebfa`（本报告内容已提交；本行将随最终 docs commit 固化）。
