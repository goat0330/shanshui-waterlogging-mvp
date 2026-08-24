# RC2.1 Browser Video Evidence Bundle

更新时间：2026-08-24

基线：Main `b0a41d1`（`rc2-evidence-demo`）

## 结论

已完成最小 synthetic-only 浏览器视频证据包，没有新增算法、模型权重、真实
CCTV 或待授权 MP4。视频分析仍只复用 `media/video_pipeline.py`，由它顺序
解码并调用既有 `vision.pipeline.run_pipeline`；本轮新增的 MP4 只是浏览器
播放 artifact，overlay 是 metadata-only，不是像素渲染结果。

## 交付文件与字节数

| 文件 | bytes | 说明 |
| --- | ---: | --- |
| `frontend/public/demo/video/flood_cam_017.mp4` | 2,419 | H.264 baseline、320×240、3 fps、3 frames、约 1 s |
| `frontend/public/demo/video/flood_cam_017.overlay.json` | 4,262 | 稳定浏览器 overlay contract |

MP4 由已跟踪的 synthetic PNG frame 生成：

- `media/artifacts/VIDEO-SMOKE-SYNTHETIC-frames/VIDEO-SMOKE-SYNTHETIC-F000000.png`
- `media/artifacts/VIDEO-SMOKE-SYNTHETIC-frames/VIDEO-SMOKE-SYNTHETIC-F000002.png`
- `media/artifacts/VIDEO-SMOKE-SYNTHETIC-frames/VIDEO-SMOKE-SYNTHETIC-F000004.png`

overlay 记录 `videoId=flood_cam_017`、`status=SYNTHETIC_DEMO`、
`sourceType=VISION_VIDEO`、`synthetic=true`、`licenseReview=not_required`、
`runtimePolicy=research_mvp`，并明确 `production=false`、
`redistribution=false`。没有 LIVE、official CCTV 或外部来源声明。

## 每帧语义

帧索引为 `0, 1, 2`，时间戳为 `0.0, 333.333, 666.667 ms`。3 帧均为既有
OpenCV baseline 的 `floodDetected=false`、`level=0`、`rangeCm=[0,0]`，
`confidence` 在 `[0,1]`；每帧 `estimatedDepthCm=null`，并带
`CAMERA_UNCALIBRATED` 与 `SYNTHETIC_DEMO`。参照物和 reference boxes 为空，
不会从普通检测框推导厘米值。

`waterMaskPath` 只引用已有 tracked synthetic smoke mask：
`F000000 → F000000-water-mask.png`、`F000002 → F000002-water-mask.png`、
`F000004 → F000004-water-mask.png`。为遵守本轮“只新增 MP4 与 overlay JSON”
边界，没有复制新的 mask 文件；overlay 的 `rendered=false` 保持证据边界。

## 实际验证

| 命令/检查 | 结果 |
| --- | --- |
| overlay JSON reload + contract invariants | PASS；3 frames、timestamps、source/provenance、null cm、mask paths 均可读 |
| OpenCV sequential decode | PASS；3 frames，320×240 |
| Chrome headless browser decode | PASS；`readyState=4`、320×240、`duration=1`、`error=null` |
| `python -m media.smoke --synthetic-check` | PASS；`VIDEO_SOURCE_REQUIRED`，synthetic adapter 3 frames；未把 demo clip 当真实源 |
| `python -m vision.smoke` | PASS；3 images，既有结果保持通过 |
| `python -m compileall -q vision media` | PASS |
| `git diff --check` | PASS |

`media/smoke.py` 仅增加了 discovery guard：默认 smoke 跳过
`frontend/public/demo/**`，避免 browser synthetic artifact 被误报为
`synthetic=false` 的真实视频输入。没有改变视频处理引擎。

## 依赖、来源与许可

未安装新依赖、未下载模型或数据集。MP4 编码使用环境已有的
`imageio-ffmpeg` bundled executable 的 `libx264`，分析仍由仓库内既有
`media/video_pipeline.py` 完成。输入资产全部是仓库已有 synthetic smoke
frames；本 bundle 不包含 V-FloodNet、pending-license MP4、权重或原始用户数据。
synthetic artifact 的 `licenseReview=not_required` 仅表示它是本地生成演示，
不构成任何真实数据授权或生产许可。

## NOT VERIFIED / 上限

- 未验证真实视频、真实 CCTV/LIVE 播放、真实洪涝场景识别或 source license。
- 未验证前端源码接入；本轮没有修改 `frontend/src/**`，只提供 public media seam。
- overlay 仍是 metadata-only；没有把 mask 逐像素绘制到视频，也没有验证
  `waterMaskPath` 作为前端静态 URL 的服务配置。
- CameraProfile 未标定，因此没有任何厘米值；不能据此报告 MAE、F1、IoU、
  生产可用性或真实深度准确率。
- 当前 OpenCV baseline、合成内容和空参照物只证明 wiring/contract/decode，
  不证明算法效果。
