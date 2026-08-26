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

## RC2.3 research training checkpoint — water segmentation candidate

状态：`CONDITIONAL`。本节是算法历史证据，不替代 `docs/06_DELIVERY_MANIFEST.md` 的当前发布状态。

### G0 environment and acquisition

- Baseline environment: Python 3.11.5, OpenCV 4.13.0, Pillow 11.3.0, NumPy 1.26.4, PyTorch 2.6.0+cu118, CUDA available, `transformers`, `torchvision`, `scikit-learn`, `ultralytics` and `segmentation_models_pytorch` importable. No package was installed in this checkpoint.
- D: drive free space at G0: approximately 164 GB.
- No reusable Torch/HuggingFace checkpoint, GT mask directory, depth label split or STURM artifact existed before acquisition. TinyCamML (13.3 GB), V-FloodNet WaterDataset/records, Eawag weights and model weights were not downloaded.
- Acquired locally outside Git: Urban Flood Image Dataset HydroShare bag (`103.5 MB`, SHA256 `59826F76D8541B7A4C52E09060A033481374D7610681FE6594102DE16C83CD38`), declared `CC BY 4.0`, rights review `DEFERRED_TO_USER`; extracted pairs: Deepflood `1040`, Sazara `253`, WebCOOS `35`.
- Also acquired and MD5-verified HKFlood-SMDepth (`HKFlood-SMDepth.zip`, MD5 `6E5C9DE418BA11808F32926C0FC6ACE5`, 62 labelled images, declared Zenodo `CC BY 4.0`). It was not mixed into this segmentation training run and remains a future metric-depth experiment asset.

Runtime paths are under `data/visiondepth/research/` at the project root and are not Git artifacts. The source archive, extracted images/masks and learned checkpoint are not committed.

### Selected route and split

Only one learned route was run: a small pixel-level Logistic Regression water-mask candidate. It uses RGB/HSV, normalized image coordinates and gradient features; it is not a foundation model and does not infer centimetres.

The split is source-archive-level, not random pixels: Deepflood + Sazara (`1293` images) for training and WebCOOS (`35` images) as a held-out camera/source domain. `496,512` balanced training pixels were sampled deterministically with seed `23`. No same image crosses the split. The OpenCV baseline is evaluated on exactly the same WebCOOS holdout.

### Actual training/evaluation

```text
python -m vision.train_water_segmenter --data-root D:\研究生作业\上海城市内涝_智慧平台\data\visiondepth\research\Urban-Flood-Image-Dataset\extracted --model-out D:\研究生作业\上海城市内涝_智慧平台\data\visiondepth\research\Urban-Flood-Image-Dataset\candidate-water-segmentation.joblib --metrics-out vision/artifacts/urban-flood-segmentation-metrics.json --examples-dir D:\研究生作业\上海城市内涝_智慧平台\data\visiondepth\research\Urban-Flood-Image-Dataset\candidate-examples
WATER_SEGMENTATION_CANDIDATE_PASS train=1293 test=35 candidate_iou=0.648314 baseline_iou=0.395276
```

Held-out mask results, reported for this split only:

| method | IoU | Dice | precision | recall | images |
|---|---:|---:|---:|---:|---:|
| learned pixel Logistic Regression | 0.648314 | 0.781130 | 0.778333 | 0.810439 | 35 |
| OpenCV baseline | 0.395276 | 0.562605 | 0.584075 | 0.564646 | 35 |

The small JSON evidence is tracked at `vision/artifacts/urban-flood-segmentation-metrics.json`. Three candidate/baseline/truth example masks and the joblib checkpoint remain local-only. The numbers are not a Shanghai accuracy claim and have no temporal-video interpretation.

### Runtime boundary

`vision.learned_segmentation.predict_water_mask()` is an explicit local-checkpoint adapter. The default `vision.pipeline` and MP4 → frame → same image pipeline remain OpenCV, so existing image/video smoke stays reproducible without a model file. The candidate outputs only a water mask; it does not set `estimatedDepthCm`, does not use `level -> cm`, does not treat relative depth as metric depth, and does not write SensorState/Forecast. Candidate checkpoint activation in product/video inference remains gated until provenance, domain transfer and end-to-end evidence are reviewed.

### NOT VERIFIED / blockers

- No Shanghai-labelled water masks, video ground truth, STURM ordinal artifact or aligned V-FloodNet metric-depth GT was available locally. STURM vehicle ordinal training and HKFlood + V-FloodNet continuous-depth fusion were not run in this checkpoint.
- The holdout contains 35 WebCOOS frames from one source archive/camera sequence; cross-city, cross-weather, true event-level and temporal generalization remain `NOT VERIFIED`.
- No learned candidate is wired as the default production image/video model. Real V-FloodNet video smoke remains OpenCV baseline with `estimatedDepthCm=null` under the uncalibrated guard.
- Metric depth MAE/RMSE, within-5/10 cm, ordinal metrics, temporal jump rate and any product decision improvement are `NOT VERIFIED`.
- Final public-use/redistribution decisions remain user-owned; local research data and checkpoint are not in Git. HydroShare acquisition succeeded; the source's declared license and rights handoff still require final project review.

## RC2.3 MVP Evidence Policy reconciliation

本节按冻结的 RC2.3 MVP Evidence Policy 对研究运行时状态做收敛，不改变
VisionDepth contract、默认推理链或 Delivery Manifest。

- Urban Flood Image Dataset 的声明许可证为 `CC BY 4.0`；基于 Deepflood +
  Sazara 训练、WebCOOS 留出集验证的 pixel Logistic Regression 候选固定为
  `VERIFIED_FOR_RESEARCH_MVP`。留出集 IoU 为 `0.648314`，同一留出集的
  OpenCV baseline IoU 为 `0.395276`。该状态只适用于 water segmentation
  research MVP，不等于上海生产准确率、metric centimetre depth 或生产模型。
- `vision/artifacts/urban-flood-segmentation-metrics.json` 保留
  `rightsReview=DEFERRED_TO_USER`，并单独记录 `mvpVerification`；这表示
  研究 MVP 可复现实验状态已冻结，但最终公开/再分发决定仍未完成。
- V-FloodNet 在 registry 中标为 `allowed_in_mvp=true`，范围严格为
  `local_research_video_evidence_only`。`license_review` 仍为 `pending`，
  `external_execution_allowed=false`、`production_allowed=false`、
  `redistribution_allowed=false`。因此本地视频 evidence gate 可通过，
  但不构成第三方模型、公开发布或再分发许可。
- 现有 6 个本地 MP4 中只有 4 个通过 `>=30` 帧 gate，实际视频 smoke 为
  4 个视频、25 个 sampled frames；2 个 11 帧文件仍被拒绝，未插帧、未复制
  帧。所有逐帧视频结果仍为 `estimatedDepthCm=null` 并含
  `CAMERA_UNCALIBRATED`。

本节之后的边界仍保持：默认 image/video 链路使用 OpenCV baseline；候选模型
只输出水域 mask，不输出厘米，不写 SensorState/Forecast；无上海标签、相机
标定、视频时序 GT、STURM 车辆 ordinal 或 V-FloodNet 公制深度对齐数据时，
厘米精度、时序稳定性、跨城市泛化和生产部署继续 `NOT VERIFIED`。
