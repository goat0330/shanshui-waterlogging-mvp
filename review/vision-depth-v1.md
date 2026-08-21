# VisionDepth V1 交付审查

状态：`CONDITIONAL`

本轮交付的是可运行的首版图片证据闭环，不是生产级视觉测深服务。图片输入、mask、参照物证据和独立 JSON 已在本地 smoke 中跑通；真实上海图片泛化、厘米准确性和后端接入仍为 `NOT VERIFIED`。

## 1. 当前实现

输入链路：

```text
本地 JPEG/PNG/WebP 或 HTTP/HTTPS 图片 URL
  → 严格解码与尺寸/大小校验
  → OpenCV 水域候选 mask
  → OpenCV HOG 行人证据 + 保守的红/橙色块候选
  → 水域重叠/水线/参照物先验
  → 固定 Level、rangeCm、可选 estimatedDepthCm
  → 独立 VisionDepthObservation JSON + water mask PNG
```

已实现：

- `vision/ingest.py`：只接受 JPEG、PNG、WebP；本地路径支持 Windows 盘符；URL 只接受 HTTP/HTTPS，带连接/读取超时、重定向复核、MIME/解码校验、15 MB 文件限制和 20 MP 像素限制。
- `vision/water_segmentation.py`：OpenCV HSV/color、下半幅场景先验、梯度/形态学和连通域 baseline；输出独立灰度 water mask。
- `vision/reference_detection.py`：OpenCV 内置 HOG 行人检测；红/橙紧凑色块只作为低置信度交通标志候选。普通检测框不会直接变成水深。
- `vision/depth_estimation.py`：固定 Level 0–5；无可靠参照物时 `estimatedDepthCm=null`、`method=NO_REFERENCE`、`NO_REFERENCE` flag 和低置信度；有可靠行人重叠证据时才输出粗粒度厘米值。
- `vision/pipeline.py` / `vision/schema.py`：保持视觉结果为独立证据对象，不写入 `SensorState`，不覆盖 `FloodPoint.currentDepthCm`。
- `vision/cli.py`：支持用户要求的 CLI；V1 始终在 JSON 同目录保存 mask，`--save-mask` 保留为显式开关。
- `vision/smoke.py`：三张真实图片、JSON 重读、mask 存在、置信度范围和 Level 断言。

## 2. 模型、依赖和许可证

本轮没有下载或训练大型模型，也没有可用的预训练权重被假装成已使用模型。

| 组件 | 实际用途 | 运行版本/许可证 |
|---|---|---|
| OpenCV | HSV/形态学/连通域、内置 HOG 行人检测器 | `cv2 4.13.0`；OpenCV Apache-2.0 |
| Pillow | 安全解码、格式校验、mask PNG 写出 | `11.3.0`；Pillow HPND/PIL license |
| NumPy | 图像数组与统计 | `1.26.4`；BSD-3-Clause |
| requests | URL 下载 | `2.32.3`；Apache-2.0 |

环境中虽然能 import `torch`、`transformers`、`ultralytics`，但 V1 未使用它们：没有本地权重、没有训练、没有引入额外 requirements 文件。`geometrySupport` 固定输出 `none`；Depth Anything V2 没有被当作厘米预测器。

V-FloodNet 只作为架构参考：

```text
Water Segmentation → Reference Object → Waterline/Submersion → Coarse Depth
```

没有复制其源码。仓库架构文档记录其许可证元数据未声明，因此不作为 runtime 依赖。

## 3. 运行命令

从 `git/` 仓库根目录运行：

```text
python -m vision.cli --input path/to/image.jpg
python -m vision.cli --input path/to/image.jpg --output vision/artifacts/result.json --save-mask
python -m vision.cli --input https://example.org/image.jpg --output vision/artifacts/result.json
python -m vision.smoke
python -m compileall vision
```

失败输入不会返回伪造 JSON：

- `ftp://...`：拒绝，实际 CLI 返回码 2；
- `https://example.com/`：识别为 `text/html`，拒绝，实际 CLI 返回码 2；
- 外部 Wikimedia 直链在重复验证时被 CDN 返回 429，CLI 明确报告下载失败且没有写结果文件；本地 HTTP 图片 URL 正向链路已通过。

## 4. Smoke 图片来源与实际输出

三张图片均为公开 Wikimedia Commons 真实照片，人工查看后选择；没有使用 synthetic 数据，没有下载完整数据集，也没有把项目 fixture 数字作为视觉输出。

| imageId | 本地样本 | 图片来源/许可证 | 人工筛选语义 |
|---|---|---|---|
| `IMG-00001` | `vision/artifacts/smoke_inputs/flood_person.jpg` | [A person stranded on how to walk through murky waters](https://commons.wikimedia.org/wiki/File:A_person_stranded_on_how_to_walk_through_murky_waters.jpg)，Queen Asali，CC BY-SA 4.0 | 真实积水；画面包含行人/靴子尺度线索 |
| `IMG-00002` | `vision/artifacts/smoke_inputs/flood_no_reference.jpg` | [Flooded Country Road](https://commons.wikimedia.org/wiki/File:Flooded_Country_Road.jpg)，Michael J. Bennett，CC BY-SA 3.0 | 真实积水；没有被算法确认的可靠尺度参照物 |
| `IMG-00003` | `vision/artifacts/smoke_inputs/dry_street.jpg` | [City street (2)](https://commons.wikimedia.org/wiki/File:City_street_%282%29.jpg)，Chris Spielmann / National Cancer Institute，Public Domain 标记 | 真实非积水城市街景 |

### IMG-00001：有参照物

实际 JSON 核心字段：

```json
{
  "imageId": "IMG-00001",
  "source": {"type": "local", "value": ".../flood_person.jpg"},
  "floodDetected": true,
  "depth": {
    "level": 3,
    "estimatedDepthCm": 25.4,
    "rangeCm": [20, 30],
    "confidence": 0.424
  },
  "method": "PERSON_REFERENCE",
  "waterMaskPath": "artifacts/IMG-00001-water-mask.png",
  "quality": "LOW",
  "qualityFlags": ["BASELINE_ONLY", "MODEL_WEIGHT_MISSING"],
  "synthetic": false
}
```

可靠行人证据为 HOG 框 `x=739,y=235,width=105,height=209`，HOG evidence confidence `0.695`，mask overlap `0.149`。`25.4 cm` 是参照物高度先验与局部 mask 重叠生成的粗粒度 V1 估计，不是实测值。

### IMG-00002：无可靠参照物

实际 JSON 核心字段：

```json
{
  "imageId": "IMG-00002",
  "source": {"type": "local", "value": ".../flood_no_reference.jpg"},
  "floodDetected": true,
  "depth": {
    "level": 5,
    "estimatedDepthCm": null,
    "rangeCm": [50, null],
    "confidence": 0.4
  },
  "method": "NO_REFERENCE",
  "waterMaskPath": "artifacts/IMG-00002-water-mask.png",
  "quality": "LOW",
  "qualityFlags": ["BASELINE_ONLY", "MODEL_WEIGHT_MISSING", "NO_REFERENCE"],
  "synthetic": false
}
```

该图片只能输出视觉等级/区间，不能输出厘米值；低分 HOG 框和色块候选均被保留为 `reliable=false` 证据，不参与测深。

### IMG-00003：非积水

实际 JSON 核心字段：

```json
{
  "imageId": "IMG-00003",
  "source": {"type": "local", "value": ".../dry_street.jpg"},
  "floodDetected": false,
  "depth": {
    "level": 0,
    "estimatedDepthCm": null,
    "rangeCm": [0, 0],
    "confidence": 0.289
  },
  "method": "VISUAL_RANGE",
  "waterMaskPath": "artifacts/IMG-00003-water-mask.png",
  "quality": "LOW",
  "qualityFlags": ["BASELINE_ONLY", "MODEL_WEIGHT_MISSING", "NO_WATER", "NO_REFERENCE"],
  "synthetic": false
}
```

完整可重读文件和 mask：

```text
vision/artifacts/IMG-00001.json
vision/artifacts/IMG-00001-water-mask.png
vision/artifacts/IMG-00002.json
vision/artifacts/IMG-00002-water-mask.png
vision/artifacts/IMG-00003.json
vision/artifacts/IMG-00003-water-mask.png
vision/artifacts/smoke-summary.json
```

## 5. 实际验证结果

```text
python -m vision.smoke       PASS
  3 images completed
  with-reference estimatedDepthCm=25.4, method=PERSON_REFERENCE
  no-reference estimatedDepthCm=null, method=NO_REFERENCE, NO_REFERENCE present
  non-flood floodDetected=false, level=0

python -m compileall vision  PASS
JSON re-read + required-field validation  PASS
3 water masks exist and are readable  PASS
local CLI input  PASS
local HTTP image URL input  PASS
invalid scheme / HTML response rejection  PASS
```

## 6. 哪些图片能输出厘米估计

- 能：`IMG-00001`，因为有通过门槛的 `PERSON_REFERENCE` 和 mask overlap 证据。
- 不能：`IMG-00002`，没有可靠尺度参照物；只输出 Level 5 / `[50,null]`。
- 不能：`IMG-00003`，未检测到明显积水；输出 Level 0。

## 7. 当前准确性限制

1. 这是 OpenCV baseline，不是经过 FloodNet/Shanghai 数据训练和验证的模型；没有正式 Accuracy、MAE、IoU 或 ±2 cm 结论。
2. 为避免本轮样本中的干燥路面误报，baseline 使用了下半幅棕/蓝色差门槛；中性灰积水、夜景、强色偏、反光玻璃和低照度场景可能漏检。
3. 单张图片没有可靠相机内参、地面平面、目标真实尺寸和标定点；`25.4 cm` 依赖行人高度先验和局部重叠比例，不能作为传感器读数。
4. OpenCV HOG 会产生候选误检；只有 `reliable=true` 的对象可以参与估计，候选框本身不代表水深。
5. `TRAFFIC_SIGN_REFERENCE` 当前仅为保守色块候选；本轮没有通过交通标志输出厘米值的样本。
6. `VEHICLE_REFERENCE`、`FIXED_CAMERA_REFERENCE` 的方法枚举和深度先验已留在独立 schema/estimator 边界，但本轮没有车辆模型权重或相机标定数据，因此没有激活对应检测路径。

## 8. Synthetic 数据声明

`synthetic=false`。Smoke 使用公开真实照片的下载副本，经过人工筛选；没有生成合成积水图、没有使用项目 CCTV fixture 的 `waterDepthCm`，也没有把 backend `FloodPoint`/Forecast 数字写入视觉输出。

## 9. 后续接入 Backend 的最小接口建议

保持视觉结果作为独立 evidence collection，不写入现有 `SensorState`：

```text
POST /api/v1/vision/observations
body: VisionDepthObservation (本报告中的固定 JSON)
```

最小后端处理只需：

1. 校验 `imageId/source/depth/method/quality/model` 和 mask artifact 引用；
2. 保留原始 source、推理时间、算法版本和 `synthetic` 标记；
3. 用显式的业务关联字段（后续另定 `floodPointId`/`eventId`）查询证据，不把视觉深度投影为传感器深度；
4. 前端或分析服务按证据质量选择是否展示，不能覆盖 `FloodPoint.currentDepthCm`。

本轮没有修改 Backend、Frontend、Cesium、Contract 或传感器代码。

## 10. NOT VERIFIED

- 未在上海真实 CCTV/互联网图片分布上做正式召回率、精度、MAE、IoU 或跨相机评估。
- 未取得或验证专用水域分割/车辆检测/Depth Anything 权重。
- 未验证 `VEHICLE_REFERENCE` 和 `FIXED_CAMERA_REFERENCE` 的真实厘米估计。
- 未验证夜间、灰色积水、遮挡、运动模糊、强反光、鱼眼镜头和多水面场景。
- 未接入 FastAPI、WebSocket、Cesium、传感器融合、CloudBase 或生产推理服务。
- 外部 Wikimedia URL 在重复请求时受 429 限流；本地 HTTP URL 的协议与图片解码链路已验证，公网稳定性仍不作为生产保证。
- 未把本轮结果写入任何现有传感器或 FloodPoint 字段。

