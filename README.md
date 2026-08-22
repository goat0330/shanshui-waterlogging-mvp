# 山水智鉴｜城市内涝 MVP 机器仓库

这是主目录下的唯一 Git 仓库。主目录的 Markdown 面向决策人；本目录面向机器执行、验证和后续实现。

+## RC2 当前状态

当前版本是 `RC2 — Evidence-Backed Demo`，状态为 `CONDITIONAL / VISUAL_REVIEW`。它已经把 API/WS 遥测、VisionDepth 图片入口、4 个合格 MP4 的本地证据 smoke、Cesium geographic 事件/预测层和 Dashboard source labels 收到同一条演示链；不代表生产部署、官方实时上海数据、标定厘米水深或第三方素材的最终公开许可。

- RC2 总控进度：[review/rc2/MAIN_PROGRESS.md](review/rc2/MAIN_PROGRESS.md)
- 验收矩阵：[docs/RC2_ACCEPTANCE.md](docs/RC2_ACCEPTANCE.md)
- 来源策略：[docs/RC2_SOURCE_PROVENANCE_POLICY.md](docs/RC2_SOURCE_PROVENANCE_POLICY.md)
- 公开来源清单：[docs/RC2_SOURCE_MANIFEST.csv](docs/RC2_SOURCE_MANIFEST.csv)
- 视频下载边界：[docs/RC2_DOWNLOAD_INSTRUCTIONS.md](docs/RC2_DOWNLOAD_INSTRUCTIONS.md)
- 交付清单：[docs/06_DELIVERY_MANIFEST.md](docs/06_DELIVERY_MANIFEST.md)

最终发布使用 Git tag `rc2-evidence-demo`；原始 MP4、模型权重和运行时输出留在仓库外的本地 research MVP 目录。

## 机器侧入口

1. `AGENTS.md`
2. `docs/00_MASTER_BLUEPRINT.md`
3. `docs/01_PRODUCT_SPEC_MVP.md`
4. `docs/02_VISUAL_SCENE_SPEC.md`
5. `docs/03_ARCHITECTURE_OSS.md`
6. `contracts/openapi.yaml`
7. `contracts/schemas/`
8. `contracts/fixtures/`
9. `references/golden-dashboard.png`

原始控制包的短 README 已保留为 `docs/README_CONTROL_PACK.md`；本文件是本仓库的机器侧入口说明。

## 约束

- 先过 L1 Cesium、L2 Video、L3 API 三个薄 PoC，再进入正式前后端。
- `contracts/` 是接口约束；Frontend / Backend 不自行改语义。
- Runtime 先保持轻量：原生 CesiumJS、FixtureRepository、本地 MP4 + Canvas Overlay。
- 不提交 Secret；Cesium token、LLM key 等只通过环境变量处理。
- 交付状态必须使用 `PASS`、`CONDITIONAL` 或 `NOT VERIFIED`。

## 预留目录

- `spikes/cesium/`：上海三维底座对比 PoC
- `spikes/video/`：本地视频和 Canvas Overlay PoC
- `spikes/api/`：FastAPI 与 Contract smoke
- `frontend/`：正式前端；中央 `DigitalTwinScene` 已接入本地黄浦 Cesium L1
- `backend/`：正式后端
- `integration/`：适配、联调和 canonical 集成
- `review/`：验证输出，不作为完成证据的替代品
