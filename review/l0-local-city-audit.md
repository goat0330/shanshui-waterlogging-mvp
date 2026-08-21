# 本地全市三维资产与陆家嘴 AOI 可提取性审计

审计日期：2026-08-21  
范围：`D:\研究生作业\上海城市内涝_智慧平台\git\data\source\skp\上海市分区`、`D:\研究生作业\上海城市内涝_智慧平台\git\data\source\shp\上海市3Dshp`，以及本机可发现的 BimAngle CLI 只读入口。  
本轮没有启动任何浦东 SKP→GLB/3D Tiles 全量转换，没有生成运行时数据，也没有改动 source、前端、后端或主进度文档。

## 结论先行

- 盘点得到 18 个分区 SKP，共 `1,590,518,953` bytes（约 `1,516.84 MiB / 1.481 GiB`）。18 个文件都能从二进制头部读到 `SketchUp Model {13.0.1}`，并含完整的 SketchUp version-map 结构性标记；这属于“文件头/结构线索可读”，不是已经通过 SketchUp/BimAngle 完整打开的证明。
- SHP 目录得到 18 个同名组、144 个文件（每组 8 个 sidecar），总大小 `453,506,452` bytes（约 `432.50 MiB`）。18 个主 `.shp` 的 ESRI header 均为 file code `9994`、version `1000`、shape type `31`（MultiPatch），不是道路/水系/行政边界业务图层。
- `浦东新区.skp` 为 `376,362,684` bytes（约 `358.93 MiB`）；其头部只有默认 `Layer0` 及 SketchUp 类定义/GeoReference 字段名，全文原始字节检索没有 `陆家嘴`、`Lujiazui`、`Scene`、`Building`、`Block`、`Chunk`、`Tile`、`Grid`、`Spatial` 等可直接证明 AOI 场景或空间分块的命名线索。不能据此承诺“一键裁陆家嘴”。
- 本轮环境中 `BimAngle` 不在 PATH，也没有可调用的 `BimAngle --help`：命令返回“`BimAngle` is not recognized as an internal or external command”。因此 bbox、选中对象、DBID 过滤和按对象导出的能力均是 `NOT VERIFIED`；同时也没有证据可以断言它只能整文件导出。当前工具链首先缺的是可复核的 CLI 路径/版本/帮助输出，以及一个不做全量转换的筛选 smoke。
- 在线 Mars3D/OSM 只能作为 fallback，不能作为最终本地 MVP 的依赖。本地 MVP 的 L0/L1 仍应以经过坐标和可见性 smoke 的本地资产为准。

## 1. 全市分区 SKP 清单

实际目录：`D:\研究生作业\上海城市内涝_智慧平台\git\data\source\skp\上海市分区`。文件大小是当前磁盘字节数；MiB 按 `bytes / 2^20` 计算。

| 分区文件（相对项目根） | bytes | MiB | 头部版本 token |
|---|---:|---:|---|
| `git/data/source/skp/上海市分区/宝山区.skp` | 136,538,113 | 130.21 | 13.0.1 |
| `git/data/source/skp/上海市分区/崇明区.skp` | 25,107 | 0.02 | 13.0.1 |
| `git/data/source/skp/上海市分区/奉贤区.skp` | 19,181,783 | 18.29 | 13.0.1 |
| `git/data/source/skp/上海市分区/红桥区.skp` | 30,011,733 | 28.62 | 13.0.1 |
| `git/data/source/skp/上海市分区/虹口区.skp` | 38,146,837 | 36.38 | 13.0.1 |
| `git/data/source/skp/上海市分区/黄浦区.skp` | 42,947,659 | 40.96 | 13.0.1 |
| `git/data/source/skp/上海市分区/嘉定区.skp` | 147,294,094 | 140.47 | 13.0.1 |
| `git/data/source/skp/上海市分区/金山区.skp` | 661,961 | 0.63 | 13.0.1 |
| `git/data/source/skp/上海市分区/静安区.skp` | 19,337,552 | 18.44 | 13.0.1 |
| `git/data/source/skp/上海市分区/闵行区.skp` | 198,794,193 | 189.58 | 13.0.1 |
| `git/data/source/skp/上海市分区/浦东新区.skp` | 376,362,684 | 358.93 | 13.0.1 |
| `git/data/source/skp/上海市分区/普陀区.skp` | 74,686,044 | 71.23 | 13.0.1 |
| `git/data/source/skp/上海市分区/青浦区.skp` | 86,237,979 | 82.24 | 13.0.1 |
| `git/data/source/skp/上海市分区/松江区.skp` | 160,458,151 | 153.02 | 13.0.1 |
| `git/data/source/skp/上海市分区/徐汇区.skp` | 85,956,515 | 81.97 | 13.0.1 |
| `git/data/source/skp/上海市分区/杨浦区.skp` | 75,186,035 | 71.70 | 13.0.1 |
| `git/data/source/skp/上海市分区/闸北区.skp` | 41,652,959 | 39.72 | 13.0.1 |
| `git/data/source/skp/上海市分区/长宁区.skp` | 57,039,554 | 54.40 | 13.0.1 |
| **合计（18 个）** | **1,590,518,953** | **1,516.84** | — |

### SKP 可读性与来源线索

对 18 个文件读取前 4 KiB/结构头，均命中以下模式：

- `SketchUp Model {13.0.1}`；原始 magic 开头均为 `ff fe ff 0e 53 00 6b 00 65 00 74 00 63 00 68`。
- version map 中可见 `CComponentDefinition`、`CComponentInstance`、`CGroup`、`CLayer`、`CPageList`、`CViewPage`、`End-Of-Version-Map` 等 SketchUp 类型表标记。
- 头部还可见 `GeoReference`、`Latitude`、`Longitude`、`ModelTranslationX/Y/Z`、`UsesGeoReferencing`、`LocationSource`、`Google Earth` 等字段名。它们是模型格式/属性名线索，不代表这些字段已经有正确上海坐标值。
- 大多数文件头保留了原始路径 `D:\01.SU素材整理\0102-上海市\上海市分区\<区名>.skp`；`杨浦区.skp` 的头部源路径为 `C:\Users\Administrator\Desktop\杨浦区.skp`，`黄浦区.skp` 为 `C:\Users\Administrator\Desktop\黄浦区.skp`。
- `崇明区.skp` 仅 25,107 bytes、`金山区.skp` 661,961 bytes，属于明显的小文件异常值；不能仅凭头部存在就假设内容完整，需另做小样本打开 smoke。`浦东新区.skp` 是本地清单中最大单文件。

上述证据只证明二进制头和版本表可识别；本轮没有对任何 SKP 启动完整导出或建立大型中间产物。

## 2. 全市 SHP sidecar 组、CRS、几何和字段

实际目录：`D:\研究生作业\上海城市内涝_智慧平台\git\data\source\shp\上海市3Dshp`。

### 2.1 Sidecar 结构

共有 18 个 basename 组、144 个文件，即每组 8 个：

```text
<区名>.shp
<区名>.shx
<区名>.dbf
<区名>.prj
<区名>.CPG
<区名>.sbn
<区名>.sbx
<区名>.shp.xml
```

以浦东为例，实际路径是：

```text
D:\研究生作业\上海城市内涝_智慧平台\git\data\source\shp\上海市3Dshp\浦东新区.shp
D:\研究生作业\上海城市内涝_智慧平台\git\data\source\shp\上海市3Dshp\浦东新区.shx
D:\研究生作业\上海城市内涝_智慧平台\git\data\source\shp\上海市3Dshp\浦东新区.dbf
D:\研究生作业\上海城市内涝_智慧平台\git\data\source\shp\上海市3Dshp\浦东新区.prj
D:\研究生作业\上海城市内涝_智慧平台\git\data\source\shp\上海市3Dshp\浦东新区.CPG
D:\研究生作业\上海城市内涝_智慧平台\git\data\source\shp\上海市3Dshp\浦东新区.sbn
D:\研究生作业\上海城市内涝_智慧平台\git\data\source\shp\上海市3Dshp\浦东新区.sbx
D:\研究生作业\上海城市内涝_智慧平台\git\data\source\shp\上海市3Dshp\浦东新区.shp.xml
```

每种扩展名均有 18 个：`.shp/.shx/.dbf/.prj/.CPG/.sbn/.sbx/.shp.xml` 各 18 个。主 `.shp` 合计 `444,037,052` bytes，整个 SHP 目录合计 `453,506,452` bytes。

`.CPG` 内容为 `UTF-8`。18 个 `.prj` 内容一致，核心声明为：

```text
PROJCS["WGS_1984_UTM_Zone_49N", ...
PROJECTION["Transverse_Mercator"]
PARAMETER["False_Easting",500000.0]
PARAMETER["Central_Meridian",111.0]
PARAMETER["Scale_Factor",0.9996]
PARAMETER["Latitude_Of_Origin",0.0]
UNIT["Meter",1.0]
```

GDAL/OSR 读取浦东时解析为 WGS 84 / UTM zone 49N（EPSG:32649 语义），单位米；原始 `.prj` 本身没有写出一个显式 `AUTHORITY["EPSG",32649]`。`浦东新区.shp.xml` 为 656 bytes，记录 `CreaDate=20220528`，并保留了 `file://\\DESKTOP\C$\Users\zhangsir\Desktop\sandi3\zxs\上海市\浦东新区` 等历史来源路径。

### 2.2 每组实际数字

所有行的 ESRI header 都是 `file code=9994`、`version=1000`、`shape type=31`（MultiPatch）。GDAL `ogrinfo -al -so` 对 MultiPatch 图层显示 `Geometry: Unknown (any)`，但原始 SHP header 的 type `31` 是直接的格式证据。`shx` 大小与 DBF 记录数一致，例如浦东 `985,332 = 100 + 8 × 123,154`。

| 区名（主文件） | `.shp` bytes | `.dbf` bytes | `.shx` bytes | DBF 记录数 | bbox（Xmin,Ymin — Xmax,Ymax，米） | 字段 / Floor 范围 |
|---|---:|---:|---:|---:|---|---|
| `嘉定区.shp` | 40,385,916 | 396 | 340 | 30 | 1,465,818.336, 3,501,593.833 — 1,490,337.006, 3,520,567.142 | `Floor`；1–35 |
| `奉贤区.shp` | 5,381,960 | 341 | 300 | 25 | 1,494,476.281, 3,464,710.536 — 1,529,284.260, 3,476,571.491 | `Floor`；1–40 |
| `宝山区.shp` | 37,524,872 | 385 | 332 | 29 | 1,484,564.729, 3,506,430.282 — 1,503,197.275, 3,522,576.901 | `Floor`；1–30 |
| `崇明区.shp` | 4,652 | 110 | 132 | 4 | 1,518,553.471, 3,521,699.534 — 1,518,813.713, 3,521,789.008 | `Floor`；1–10 |
| `徐汇区.shp` | 23,148,468 | 528 | 436 | 42 | 1,492,385.521, 3,488,391.808 — 1,500,131.230, 3,501,726.988 | `Floor`；1–53 |
| `普陀区.shp` | 20,101,684 | 462 | 388 | 36 | 1,484,823.615, 3,501,006.673 — 1,497,199.969, 3,510,036.202 | `Floor`；1–41 |
| `杨浦区.shp` | 20,689,444 | 440 | 372 | 34 | 1,499,881.797, 3,505,543.764 — 1,507,994.038, 3,516,238.453 | `Floor`；1–35 |
| `松江区.shp` | 43,870,928 | 341 | 300 | 25 | 1,460,936.534, 3,462,489.073 — 1,491,345.593, 3,493,628.137 | `Floor`；1–30 |
| `浦东新区.shp` | 112,784,444 | 7,266,248 | 985,332 | 123,154 | 1,499,129.020, 3,469,295.055 — 1,537,068.367, 3,521,038.326 | `Id`、`Floor`、`Shape_Leng`、`Shape_Area`；Floor 1–118 |
| `红桥区.shp` | 8,161,288 | 429 | 364 | 33 | 1,029,027.056, 4,350,440.698 — 1,034,809.629, 4,355,851.915 | `Floor`；1–40 |
| `虹口区.shp` | 10,443,164 | 506 | 420 | 40 | 1,497,743.046, 3,504,477.147 — 1,503,503.176, 3,512,560.853 | `Floor`；1–66 |
| `金山区.shp` | 222,076 | 176 | 180 | 10 | 1,458,888.774, 3,461,259.924 — 1,492,092.365, 3,464,578.642 | `Floor`；1–20 |
| `长宁区.shp` | 15,273,556 | 528 | 436 | 42 | 1,486,811.126, 3,496,368.516 — 1,496,459.359, 3,503,258.775 | `Floor`；1–58 |
| `闵行区.shp` | 54,012,056 | 429 | 364 | 33 | 1,477,570.244, 3,475,215.179 — 1,509,465.606, 3,503,230.685 | `Floor`；1–48 |
| `闸北区.shp` | 11,437,624 | 473 | 396 | 37 | 1,493,630.782, 3,503,784.996 — 1,500,308.998, 3,513,108.205 | `Floor`；1–50 |
| `青浦区.shp` | 23,852,724 | 308 | 276 | 22 | 1,456,777.927, 3,473,576.577 — 1,485,756.292, 3,506,442.589 | `Floor`；1–30 |
| `静安区.shp` | 5,223,704 | 605 | 492 | 49 | 1,495,195.685, 3,500,918.366 — 1,499,031.119, 3,504,207.292 | `Floor`；1–76 |
| `黄浦区.shp` | 11,518,492 | 594 | 484 | 48 | 1,498,067.694, 3,498,684.853 — 1,503,090.509, 3,504,655.219 | `Floor`；1–60 |

18 个 DBF 组的记录数合计为 `123,693`；其中浦东单组占 `123,154` 条。

字段细节：除浦东外，其余 17 组 DBF 都只有 `Floor`（Numeric, width 10, decimals 0）。浦东的 `Id` 是 Integer width 10 且实际值范围为 `0..0`，`Floor` 为 Integer width 10，`Shape_Leng` 为 Real width 19/11，`Shape_Area` 为 Real width 19/11；浦东第一条记录示例为 `Id=0, Floor=2, Shape_Leng=46.7606815299, Shape_Area=121.86625536`。

两个数据质量风险已经由数字直接暴露：

- `红桥区.shp` 的 bbox 是 `X≈1.03M, Y≈4.35M`，而其余上海组大致位于 `X≈1.46–1.54M, Y≈3.46–3.52M`；不能把它无审计地当作上海红桥区背景。
- `闸北区` 是历史区名，不能在没有边界/来源确认时自动与静安区合并。`崇明`、`金山` 的 SHP/SKP 也都是明显小样本，应单独 smoke。

## 3. 浦东 SKP 的陆家嘴 AOI 可提取性

目标文件：`D:\研究生作业\上海城市内涝_智慧平台\git\data\source\skp\上海市分区\浦东新区.skp`，大小 `376,362,684` bytes。

### 3.1 文件内部线索

对完整 376,362,684 bytes 做了只读原始字节检索；关键结果如下：

| 检查项 | 证据 | 判断 |
|---|---|---|
| SketchUp 头 | `SketchUp Model {13.0.1}` | 结构头可识别 |
| 原始来源路径 | `D:\01.SU素材整理\0102-上海市\上海市分区\浦东新区.skp` | 有来源字符串 |
| 类定义 | `CComponentDefinition` @ byte 441、`CComponentInstance` @ 489、`CGroup` @ 1085、`CPageList` @ 1263、`CViewPage` @ 1803 | 只是 version-map/类表，不等于已找到可筛选对象 |
| 层线索 | `CLayer` @ 1125/1145、`Layer0` @ 123588/123619、`Layer_Layer0` @ 123607 | 目前只看到默认层及类/属性名 |
| GeoReference 字段 | `GeoReference` @ 122815/122843，`Latitude` @ 122900，`Longitude` @ 122990，`ModelTranslationX/Y/Z` @ 123021/123068/123115，`UsesGeoReferencing` @ 123189 | 只看到字段名，未从此处证明已写入正确值 |
| AOI 名称 | `陆家嘴` 0 次，`Lujiazui` 0 次 | 没有直接命名证据 |
| 场景/空间分块名 | `Scene`、`Building`、`Block`、`Chunk`、`Tile`、`Grid`、`Spatial`、`Floor` 均 0 次；`道路`、`水系`、`黄浦江`也为 0 次 | 没有可复核的命名分块证据 |

因此，当前可以说“文件里存在 SketchUp 的组件/组/层/页面类型定义”，不能说“文件已经按陆家嘴、场景、楼栋或空间块组织”。负向结果来自原始字符串和头部结构审计，不是完整 SketchUp 实体语义解析；它足以阻止一键裁剪承诺，但不能替代后续小样本打开 smoke。

### 3.2 SHP 能否直接帮浦东裁陆家嘴

不能直接做到。浦东 SHP 是一个 123,154 记录的全区 MultiPatch 组，bbox 为 `1,499,129.020, 3,469,295.055 — 1,537,068.367, 3,521,038.326`，DBF 没有 AOI/街道/楼栋名称字段，且 `Id` 全为 0。它可用于全区坐标/范围/楼层范围校准，不能仅凭当前字段定位陆家嘴对象。

要从 SKP 快速得到陆家嘴，至少需要以下一项已证实能力：

1. BimAngle/转换器按 bbox 对实体做空间相交筛选；
2. 按选中对象或稳定 DBID 过滤并导出；
3. 文件内部已有可枚举的命名层/场景/组件集合，并能在导出前选择集合。

本轮三项都没有可复核证据。结论是：**当前不能证明可以快速裁陆家嘴；“一键裁剪”状态为 NOT PROVEN。**

### 3.3 BimAngle CLI 能力审计

> 主线程补充：父线程已确认本机实际入口为
> `C:\ProgramData\Bimangle\Bimangle.ForgeEngine.Skp\CLI\ForgeEngineSkpCLI.exe`，版本 `2026.8.5`；本 worker 会话未继承该路径，因此下面“不可调用”只表示 worker 会话内的 PATH 未发现，不否定该绝对路径的存在。父线程已用该入口完成黄浦最小转换和 Cesium 可见性 smoke。

本机只读检查结果：

```text
where BimAngle       -> 无结果
BimAngle --help      -> 'BimAngle' is not recognized as an internal or external command,
                        operable program or batch file.
```

同时未在当前 PATH、用户 profile 的可发现文件名及常见安装根目录中找到可调用的 `bimangle.exe`/`bimangle-cli.exe`。因此本轮没有可信的 CLI `--help`、版本、配置或命令 schema 可用来确认 `bbox`、`selection`、`DBID`、`layer` 或 `scene` 参数。不能把“当前只支持整文件导出”当成事实；准确表述是：**BimAngle 的入口和筛选能力在本审计环境中均未验证，工具链缺少可执行路径和无转换的筛选探针。**

## 4. 本地 L0/L1 运行时建议

### L0：全市背景

- 保留 18 个 SKP 原始文件作为 source manifest，不合并为一个约 1.48 GiB 的单体运行时文件。
- 运行时按“区级根 tileset → 区内 LOD → 需要时才做 AOI 子树”组织，例如 `shanghai/l0/<district>/tileset.json`；每区独立加载、独立失败，不让浦东拖住全市首屏。
- L0 先用低/中 LOD 白模背景。区级根可用 3D Tiles 做流式组织，内容可以是经验证的 GLB/B3DM；在没有空间分块能力前，不要假装已经拥有自动 tile subdivision。浦东、闵行、松江、嘉定等大文件应优先做小样本/低 LOD smoke，再排全量任务。
- `红桥区` 的空间 bbox 与其他上海组不一致，`闸北区` 是历史区名；二者在 manifest 中先标记 `QUARANTINE/LEGACY`，不应直接进入“上海全市已校准”集合。

### L1：黄浦和陆家嘴，以及 GLB/Tiles 边界

| 使用场景 | 推荐格式 | 边界 |
|---|---|---|
| 黄浦已选定的小范围、固定镜头或转换 smoke | 单个 GLB 可作为交付/可见性探针 | GLB 是内容文件，不包含可替代的空间层级；必须配套坐标、bbox、来源和对象数记录 |
| 黄浦多个街区或陆家嘴后续需要按视野流式加载 | 3D Tiles 根 + 子 tile 内容（GLB/B3DM） | 只有在转换器能按空间/对象切分并通过 Cesium 可见性 smoke 后才进入 L1 |
| 全浦东原始 SKP | 暂不转换 | 358.93 MiB 原文件加上 123,154 条 SHP 记录，当前没有 AOI 过滤证据，不应以“先全量转再裁”替代筛选审计 |

GLB 与 Tiles 不是二选一的同层概念：GLB 适合一个已经确定边界的小资产，3D Tiles 负责层级、裁剪和流式调度，GLB/B3DM 可以是 Tiles 的内容。陆家嘴若最终采用 Tiles，仍需先解决 AOI 几何、SKP 实体筛选、坐标变换和稳定 ID；当前没有任何一项可以从这批 source 自动推导完成。

### SHP 的职责

- 用 `.prj` 声明的 WGS 84 / UTM zone 49N（米制）做第一层坐标校准：读取 bbox/要素范围，转换到应用使用的 WGS84/引擎坐标，再与本地 3D 资产的变换矩阵和已知控制点比对；不要把字段名 `GeoReference` 当作已经校准。
- 用 MultiPatch 的 bbox、记录数、`Floor` 范围和 `Shape_Leng/Shape_Area` 做建筑资产范围/楼层合理性检查。浦东 `Id=0` 全部重复，不能直接作为点选或 tile 级稳定主键。
- 当前这些 SHP 是建筑 MultiPatch 组，不承担道路、水系、行政边界或陆家嘴 AOI 边界。道路/水系/区界/AOI 应以独立 2D 业务图层提供，并在同一 CRS 规范下转换、记录来源和误差；不能把 `Floor` 字段误用成道路/水系语义。

## 5. 已证实、仍需 smoke 与最短执行清单

### 已证实

- 18 个 SKP 的实际路径、大小、`SketchUp Model {13.0.1}` 头部 token 和结构性 version-map 线索。
- 18 个 SHP basename 组、144 个 sidecar、每组 8 件的实际结构；主文件字节数、DBF 记录数、bbox、shape type 31、CRS 文本和字段范围。
- 浦东 SKP 大小、默认 `Layer0`/类表/GeoReference 字段名，以及没有“陆家嘴”命名和明确场景/块命名的原始字节证据。
- 浦东 SHP 是全区级 123,154 记录、`Id` 全 0，不能单凭它快速指认陆家嘴对象。
- 本 worker 没有启动大转换、没有写 runtime、没有改 source。

### 未证实 / 下一步最短清单

1. 由拥有转换环境的主线程提供 BimAngle 的**准确可执行路径和版本**；只运行 `--help/--version` 或等价只读命令，记录是否有 bbox、selection、DBID、layer/scene 过滤。没有这一步，不得写“可快速裁陆家嘴”。
2. 先确定陆家嘴 AOI 的独立边界和 CRS；用该边界与浦东 SHP 做只读相交统计，确认候选数量/范围，不做全浦东转换。
3. 若 CLI 有空间或 DBID 过滤，选一个极小 bbox/少量对象做 GLB smoke，再生成最小 Tiles smoke；检查输出大小、对象数、坐标和 Cesium 可见性。
4. 对 `崇明区.skp`、`金山区.skp`、`红桥区.skp`、`闸北区.skp` 做单文件可读性/坐标异常 smoke；通过后才纳入 L0 manifest。
5. 仅在 1–4 通过后，制定按区/LOD 的全市转换排期；本报告不授权、也没有执行全浦东转换。

### 未决风险

- `13.0.1` 是文件内部版本 token；本轮没有把它外推为具体 SketchUp 产品年份。
- 无可调用 BimAngle CLI，SKP 的实体语义、实际 layer/page/component 内容、bbox/DBID 导出能力仍未验证。
- 所有 SHP `.prj` 都声明 UTM 49N，但 `红桥区` bbox 明显偏离其他上海组；这既可能是错区文件，也可能是来源/坐标异常，需单独确认。
- 本地 3D 资产最终能否在 Cesium 中正确可见，仍取决于主线程的坐标校准和真实运行时 smoke；本报告不把 header 或 copy 检查升级为可见性验收。
