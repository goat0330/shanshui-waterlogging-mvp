# Frontend Component Gallery

状态：`IMPLEMENTED` / `VISUAL_REVIEW`（Dashboard Composition Refinement V0.3）

本文件记录本轮 React 组件实现和人工视觉 review 入口；视觉验收由用户本人完成。

## 1. Source

- 主要视觉目标：`D:\Edge Downloads\ChatGPT Image 2026年8月20日 23_56_43.png`
- 冻结对照：`git/references/golden-dashboard.png`
- 视觉组合修正规范：`C:\Users\WangChi\.codex\attachments\d893708c-ca67-4463-87e7-b926b13b0a54\pasted-text.txt`
- 视觉修正 Prompt：`D:\Edge Downloads\frontend-worker-visual-refinement-prompt-v0.2.md`
- Contract 读取说明：仓库内 `docs/04_FRONTEND_COMPONENT_VISUAL_CONTRACT.md` 当前缺失，本轮以用户提供的 `D:\Edge Downloads\04_FRONTEND_COMPONENT_VISUAL_CONTRACT.md` 作为只读冻结参考，未复制或修改 Contract。
- 产品/布局依据：`git/docs/01_PRODUCT_SPEC_MVP.md`、`git/docs/02_VISUAL_SCENE_SPEC.md`
- Contract fixture：`git/contracts/fixtures/`

## 2. Target / Region

- Target：山水智鉴｜上海城市内涝智能防控中心首页核心视觉骨架与可复用 React 组件
- Region：1920×1080 Dashboard 全页；顶部导航、左侧三面板、中央 DigitalTwinScene、选中事件浮层、右侧三面板、底部 Timeline；Gallery 中的单组件与组合状态
- 明确不包含：Cesium PoC 改造、backend/contracts 修改、真实视频流、实时预测模型；本轮只消费现有前端 API 数据形状
- 新增合法 placeholder 素材：`frontend/public/mock/shanghai-scene-placeholder.webp`、`frontend/public/mock/cctv-placeholder.webp`

## 3. Viewport / States

- 主视口：`1920 × 1080`
- 单组件状态：`default`、`high-risk` / `critical`、`NOW`、`+30 active`、`heavy-rain`、`live + AI overlay`、`offline`、`loading`、`empty`
- Full Dashboard：`A Default`、`B High Risk`、`C Forecast +30`

## 4. Gallery Entry / Run Command

```text
http://localhost:5173/gallery
```

全屏 Dashboard review 入口：

```text
http://localhost:5173/?state=default
http://localhost:5173/?state=high-risk
http://localhost:5173/?state=plus30
```

在 `frontend/` 执行：

```bash
npm install
npm run typecheck
npm run build
npm run dev
```

## 5. Component Inventory

- `AppShell`
- `TopNav`
- `StatusPanel`
- `RainfallPanel`
- `RankingPanel`
- `DigitalTwinScene`
- `LayerToolbar`
- `DepthLegend`
- `EventPanel`
- `SceneEventCard`
- `AIAnalysisPanel`
- `ForecastPreview`
- `CctvCard`
- `TimelineBar`

展示组件采用 `data in + events out`；fixture 读取与状态组合在 `src/data/homeFixtures.ts` / `src/App.tsx`，组件不 fetch、不读取 backend URL。

## 6. Required States / Implemented States

| Component | Required states | Implemented states |
|---|---|---|
| `StatusPanel` | default / high-risk / empty | default / high-risk / empty |
| `RainfallPanel` | default / heavy-rain / loading / empty | default / heavy-rain / loading / empty |
| `RankingPanel` | default / empty | default / empty |
| `EventPanel` | selected-high-risk / critical / loading / empty | selected-high-risk / critical / loading / empty |
| `SceneEventCard` | selected / high-risk / sensor evidence / actions | selected / high-risk / sensor evidence / actions |
| `ForecastPreview` | NOW / +30 / loading / empty | NOW / +30 / loading / empty |
| `CctvCard` | live-overlay / offline / loading / empty | live-overlay / offline / loading / empty |
| `TimelineBar` | realtime / playback / forecast | realtime / playback / forecast |
| Full Dashboard | default / selected-event / +30 forecast | A Default / B High Risk / C Forecast +30 |

## 7. Visual Refinement Changes

- 中央场景从抽象城市 SVG 改为目标图中央城市区域导出的本地 placeholder，保留 `DigitalTwinScene` mount boundary；React overlay 继续负责风险点、积水范围、Popup、Toolbar 和 Legend。
- Panel 分为 Strong（城市态势 / 事件）、Soft（雨情 / 排行 / 预测 / CCTV）和 Scene Overlay 三层，减少二级 KPI、排行行和 Forecast preview 的可见边框。
- 收敛 cyan 使用，降低 metadata 对比度，放大事件核心数字和城市态势数字；橙色/红色仅保留给风险焦点。
- CCTV 使用目标图中的现场证据区域作为明确标注的 placeholder 背景，叠加 Props 驱动的少量 overlay。
- V0.3 将顶部导航压至 76px；左右栏收敛为 360px / 370px，并压缩 Status、Rainfall、Ranking、Event、Forecast、CCTV 的纵向占位，避免面板拼装感。
- DigitalTwinScene placeholder 扩展为主体连续场景背景；Toolbar、DepthLegend、Selected Popup 作为 Scene Overlay 保留，其中 Popup 缩小并用轻量遮罩覆盖目标图中烘焙的旧 callout。
- EventPanel 去除首页组合中的 AI 研判展开条占位，保留 `AIAnalysisPanel` 组件与 Props；Forecast 改为更轻的控制器摘要，CCTV 作为低权重证据区。
- 新增 `SceneEventCard`：点击 Cesium 点位后，在中央场景上叠加截图风格的事件详情卡；消费 `FloodEvent`、`SensorState`、`AIAnalysis`，展示位置、当前水深、上涨速度、对应传感器和处置建议；重复点击当前点位可收起，不使用 `×` 关闭按钮。
- `/gallery` 保留组件验收用途，并增加三种全屏 Dashboard review 链接；Gallery 不作为最终高级感判断依据。

## 8. Known Deviations / NOT VERIFIED

- `DigitalTwinScene` 仍是明确标注的本地静态 placeholder，未接 Cesium，未验证真实三维城市、FlyTo 或性能指标；背景素材来自用户提供目标图的非破坏性裁切，不能代表 live Cesium。当前为全幅拉伸 placeholder 以保持场景连续，真实 Cesium 接入时需重新校准空间比例。
- placeholder 背景本身保留了目标图中的部分静态场景标记；动态风险点、积水、Popup 与 Toolbar 仍由 React overlay 提供，Popup 背后的烘焙 callout 通过 CSS 轻量遮罩降权，后续接 Cesium 时应移除该遮罩并复核重叠关系。
- `CctvCard` 当前使用目标图现场区域的 placeholder 与 Props 驱动 overlay；fixture 中的 MP4 路径没有随仓库提供的本地媒体文件，未验证真实视频播放和 Canvas 同步。
- `RankingPanel` 的首页 fixture 没有按站点的雨强字段，本轮以现有 `FloodPoint.depthCm` 做“重点区域排行”，并在面板脚注中明确数据语义；未伪造站点雨强来源。
- 目标图的真实字体、城市影像材质、图标集和 Cesium 场景尚未逐像素对照；本轮只做骨架、层级、比例和可复用状态。
- Gallery 的完整 Dashboard 仍以组件验收入口为主，三种全屏入口在 `/` 下 review；Gallery 缩略预览不作为首页高级感结论。
- `SceneEventCard` 的视觉目标为用户本轮提供的事件浮层截图：源文件 `C:\Users\WangChi\AppData\Local\Temp\codex-clipboard-bb6ba540-ef50-407b-956f-0398a439da93.png`，目标视口约 `351 × 525`，目标状态 `selected / high-risk / sensor + actions`；Gallery 使用目标图风格的场景背景进行组件对照。
- 本地 `typecheck` / `build` 与 Chrome headless 三种 1920×1080 review 截图已验证；真实视频、后端联调、Cesium、性能和用户视觉验收仍为 `NOT VERIFIED`。

## 9. Review Artifacts / Current Review Status

已生成：

- `frontend/review/dashboard-default-1920x1080.png`
- `frontend/review/dashboard-high-risk-1920x1080.png`
- `frontend/review/dashboard-plus30-1920x1080.png`

## 10. V0.3 Self-check Evidence

| source | target | region | viewport | state | status |
|---|---|---|---|---|---|
| local React dashboard | 用户目标图 + Golden Reference | full Dashboard | 1920 × 1080 | Default / NOW | VISUAL_REVIEW |
| local React dashboard | 用户目标图 + Golden Reference | full Dashboard | 1920 × 1080 | High Risk / NOW | VISUAL_REVIEW |
| local React dashboard | 用户目标图 + Golden Reference | full Dashboard | 1920 × 1080 | Forecast +30 | VISUAL_REVIEW |
| 用户事件浮层截图 | `SceneEventCard` | 事件详情浮层 | 约 351 × 525 | selected / high-risk | VISUAL_REVIEW |

- Self-check round 1：render → screenshot → compare；确认左右栏过宽、中心 placeholder 卡片边界、Event/Forecast 内容裁切和 Selected Popup 过大。
- Self-check round 2：收窄左右栏、压缩面板内部节奏、扩展连续场景、降低 CCTV/Toolbar/Legend 权重、缩小 Popup；三种状态重新截图。
- Self-check round 3：针对 placeholder 烘焙 callout 加轻量 CSS 遮罩，再次生成三种 1920 × 1080 review 截图；DOM 检查无横向/纵向页面溢出。

`IMPLEMENTED`：V0.3 组合视觉调整、核心组件、Mock 传递、Gallery 入口和全屏 review 资产已实现。

`VISUAL_REVIEW`：等待用户对目标图与 Golden Reference 进行视觉 review；本轮不声明视觉验收完成。
