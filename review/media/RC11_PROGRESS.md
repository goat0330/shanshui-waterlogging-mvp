# RC1.1 VisionDepth + Video Evidence Progress

更新时间：2026-08-23

Worktree：`D:/研究生作业/上海城市内涝_智慧平台/worktrees/vision-video-rc11`

Branch：`worker/rc11-vision-video`
基线：`f16e18b81e4e800bd11b0a5880a69931076045a3`

## 当前结论

P0 已实现：离线本地 MP4 → OpenCV 顺序采样 → 复用现有
`vision.pipeline.run_pipeline` → 每帧独立 VisionDepth JSON、PNG 水域 mask、
时间戳和 metadata-only overlay 证据。视频层没有复制水域识别、参照物识别或
深度等级逻辑，也没有写入 SensorState 或 FloodPoint。

当前 worktree 没有可追溯的本地 MP4；没有下载视频、使用 frontend CCTV
placeholder，或伪造 CCTV/LIVE 结果。因此真实视频 smoke 的状态明确为
`VIDEO_SOURCE_REQUIRED`。为验证采样器本身，另跑了一个临时合成 MP4 adapter
check；该结果全部标记 `synthetic=true` / `SYNTHETIC_INPUT`，不是现实证据。

## 实现与输出

- `media/video_pipeline.py`：仅负责 MP4 校验、OpenCV frame stride、timestamp、
  frame PNG 落盘和逐帧调用 `vision.pipeline.run_pipeline`。
- `media/cli.py`：`python -m media.cli --input <local.mp4>`，拒绝网页、URL、
  非 MP4 和不存在文件；默认 `NOT_VERIFIED` 记录源许可状态。
- `media/smoke.py`：无本地 MP4 时写出缺源结果；可选
  `--synthetic-check` 只验证 adapter，不冒充真实视频。
- 每帧保存完整的既有 VisionDepth observation，包含 `referenceObjects`、
  `depth.level/rangeCm/estimatedDepthCm/confidence`、`method`、
  `qualityFlags`、`waterMaskPath`；另有 `overlay.status=METADATA_ONLY`、
  `rendered=false`、参考物 bbox 和 mask/result 路径。

## 实际 smoke 输出

### 图片 V1 回归

`python -m vision.smoke`：PASS，3 张既有图片均可重新推理并重新读取 JSON。

| 图片 | floodDetected | level | estimatedDepthCm | rangeCm | method | confidence |
| --- | --- | ---: | ---: | --- | --- | ---: |
| `flood_person` | true | 3 | 25.4 | `[20, 30]` | `PERSON_REFERENCE` | 0.424 |
| `flood_no_reference` | true | 5 | `null` | `[50, null]` | `NO_REFERENCE` | 0.400 |
| `dry_street` | false | 0 | `null` | `[0, 0]` | `VISUAL_RANGE` | 0.289 |

### 视频缺源与结构 smoke

- `python -m media.smoke`：PASS；输出
  `media/artifacts/video-smoke.json`，状态为
  `VIDEO_SOURCE_REQUIRED`，`frames=[]`，`synthetic=false`，没有虚构观测。
- `python -m media.smoke --synthetic-check`：PASS；临时 MP4 采样 3 帧，时间戳
  为 0、250、500 ms。输出
  `media/artifacts/video-smoke-synthetic.json`，`synthetic=true`。
- 合成 adapter 的帧 JSON：
  `media/artifacts/VIDEO-SMOKE-SYNTHETIC-F000000.json`、
  `media/artifacts/VIDEO-SMOKE-SYNTHETIC-F000002.json`、
  `media/artifacts/VIDEO-SMOKE-SYNTHETIC-F000004.json`。
- 对应水域 mask：上述三个文件名的 `-water-mask.png`；采样帧 PNG 在
  `media/artifacts/VIDEO-SMOKE-SYNTHETIC-frames/`。
- 合成帧验证了 JSON 可重新读取、mask 存在、confidence 在 `[0,1]`、
  `NO_REFERENCE` 时 `estimatedDepthCm=null`，以及 overlay metadata 可回溯。

## 运行与依赖

```text
python -m media.cli --input path/to/clip.mp4 --output media/artifacts/video-result.json
python -m media.smoke
python -m media.smoke --synthetic-check
python -m vision.smoke
python -m compileall -q vision media
```

G0 记录：Python 3.11.5；import 的 OpenCV 4.13.0、NumPy 1.26.4、Pillow
11.3.0、requests 2.32.3；torch 2.6.0+cu118 且 CUDA 1 卡可见，但本轮没有
使用 torch、CUDA、Transformers 或 Ultralytics，也没有下载权重或安装依赖。
smoke 有既存 `RequestsDependencyWarning`，不影响退出码；依赖版本治理未在
本轮扩展。

模型/许可边界：当前使用既有 OpenCV baseline（水域 mask、HOG 人体和保守颜色
候选），没有外部模型权重。V-FloodNet 只作为水域→参照物→淹没分析→深度的
架构参考，未复制源码；既有 V1 README 记录其 license metadata undeclared。
RC1.1 没有完成外部模型或视频源的 license clearance，不能据此宣称生产可用。

## 可输出范围与后续接口建议

有可靠参照物时，沿用 V1 的粗粒度 `estimatedDepthCm`；没有参照物时保持
`estimatedDepthCm=null`，只能输出固定 level/range，低 confidence 并带
`NO_REFERENCE`。视频只是在时间轴上保留这些独立图像证据，没有跨帧融合、
相机标定、光流水线或真实厘米测量。

后续 Backend 最小接缝建议是新增只读视觉证据资源（例如
`POST /api/v1/vision-depth/observations`），逐帧接收 `videoId`、
`frameIndex`、`timestampMs`、原始 `observation` 和 artifact paths；保留
source/license/synthetic/quality 字段，查询时与 SensorState、FloodPoint
分域展示。视觉证据不得覆盖 `FloodPoint.currentDepthCm`，也不得直接写入
传感器实测值。本轮未改 contracts/backend。

## NOT VERIFIED / blockers

1. `VIDEO_SOURCE_REQUIRED`：没有合法、明确来源的短 MP4，真实视频帧级输出、
   视频源许可和 CCTV/LIVE 运行状态均未验证。
2. 合成 adapter 只验证代码路径，不验证真实场景准确性；合成数据已显式标记，
   不得用来报告 MAE、F1、召回率或生产效果。
3. 没有 labeled video split，没有 Macro F1、Balanced Accuracy、Recall 或
   Ordinal Error；没有训练和没有外部权重许可，因此 P1 模型升级暂缓。
4. 当前仍是 LOW-confidence OpenCV baseline；颜色、夜间、遮挡、反光、相机
   视角和远距离参照物会造成明显误检/漏检。没有 temporal smoothing、相机标定、
   真实车体检测或可视化 overlay video，overlay 仅为 metadata。
5. `RequestsDependencyWarning` 说明环境依赖版本存在警告；本轮未修改环境，
   也未将此 warning 伪装成通过的依赖治理结论。

Checkpoint commit：PENDING（代码提交后回填实际 SHA）。
