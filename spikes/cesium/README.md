# L1 Cesium PoC

状态：`CONDITIONAL PASS（L1 薄 PoC）`

## 当前实现

- Native CesiumJS + Vite，不引入整套 Mars3D 工程。
- 首选 `https://data.mars3d.cn/3dtiles/jzw-shanghai/tileset.json` 上海 3D Tiles。
- 已捕获核心演示机位的 Shanghai AOI 本地缓存，入口为 `/data/tiles/shanghai-aoi/tileset.json`。
- `Shanghai Core Local` 已接入黄浦真实模型入口 `/data/runtime/shanghai-core/tileset.json`；原始 BimAngle 锚点在运行时按黄浦 SHP bbox 中心做范围级映射，加载后自动 FlyTo。
- 提供两个互斥的运行时材质模式：`uniform blue-gray` 基线和 `blue-gray shader` 预览；Shader 只负责运行时统一调色，不等同于五类真实 PBR 材质。
- 可选 Cesium OSM Buildings fallback，需要通过 `VITE_CESIUM_ION_TOKEN` 注入 token。
- 外部上海 Tiles 不可达时自动切换 `Local Demo Blocks`，保证 PoC 可运行；本地模型不代表真实上海建筑。
- 已包含上海机位、蓝灰建筑样式、场景水系、NOW/+10/+30 积水面、风险点、FlyTo 和图层开关。
- 演示水系、积水面和风险点使用 `Scenario geometry / Demo Scenario Data`，不宣称为上海官方实时数据。

## 运行

```bash
npm install
npm run typecheck
npm run build
npm run dev
# 另开终端执行浏览器烟测
python -u scripts/l1_browser_smoke.py
# 严格离线检查本地缓存
python -u scripts/local_cache_offline_smoke.py
```

默认地址：`http://127.0.0.1:4173/`

## L1 验收输出

- [x] 上海 3D Tiles 加载成功截图：`review/l1-shanghai.png`
- [x] Cesium `CustomShader` 蓝灰预览：`review/l1-shanghai-shader.png`
- [x] 建筑统一材质截图：`review/l1-shanghai.png`
- [x] NOW/+10/+30 中央积水范围变化：烟测验证 `28.6 → 35.2 → 52.4 cm`
- [x] FlyTo 与风险点截图：`review/l1-event.png`
- [x] 外部地址不可用时本地兜底：`review/l1-local-fallback.png`
- [x] 核心视口本地缓存：`public/data/tiles/shanghai-aoi/manifest.json`、`review/l1-local-tiles.png`
- [x] 远程阻断后本地缓存仍可加载：`review/l1-local-offline.png`
- [x] `Shanghai Core Local`：`review/l1-core-not-ready.png` 已更新为黄浦本地真实建筑可见截图；5 个 `.b3dm` 子瓦片在浏览器 smoke 中返回 200
- [x] 图层开关：烟测验证城市建筑图层隐藏/显示
- [ ] OSM fallback 与 token/License 记录
- [x] 浏览器 console/network 无致命错误：烟测 `bad_responses=[]`、`page_errors=[]`

## 当前边界

- 上海 Tiles 是外部 PoC 数据源；本轮未完成 FPS 基准、长期稳定性和正式授权审查。
- 本地缓存是固定 1920×1080 总览 + 风险点 FlyTo 的可见 Tile 缓存；当前 manifest 为 94 个文件、约 6.39 MB，数量会随 LOD 调度变化，不是完整 2–5 km² 几何 AOI，也不是全上海离线镜像；缓存目录已加入 `.gitignore`。
- 本地缓存只包含 `tileset.json`、分层 `tileset_*.json` 与 `.b3dm`；当前 PoC 没有下载地形、影像或 OSM Buildings。
- 当前核心 runtime 只完成黄浦区；18 个 SKP 的全市 L0 转换尚未完成，浦东陆家嘴 AOI 裁剪能力为 `NOT PROVEN`。
- 该 PoC 证明的是“上海城市三维场景 + 内涝演示图层”的最小闭环，不等于官方完整 CIM、实时 IoT、排水管网或预测模型。
