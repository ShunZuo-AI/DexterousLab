# 灵巧抓取物体资产来源

核查日期：2026-11-11。这里收集的是**被抓取物体**，不是灵巧手模型。公开下载、许可允许使用、完成物理配置、通过仿真验证是不同状态。

## 优先来源

| 来源 | 内容与适用实验 | 获取入口 | 许可与限制 |
|---|---|---|---|
| YCB | 真实日用品扫描网格与纹理，适合杯子、瓶子、盒子、工具等桌面抓取 | [官方模型页](https://www.ycbbenchmarks.com/object-models/) · [官方AWS条目](https://registry.opendata.aws/ycb-benchmarks/) | AWS发布条目标注CC BY 4.0；保留对象来源和归属 |
| DexGraspNet | 5,355个物体、132万Shadow抓取；资产处理流程提供凸分解网格和URDF，适合候选合成与论文对齐 | [项目页](https://pku-epic.github.io/DexGraspNet/) · [作者链接的下载入口](https://mirrors.pku.edu.cn/dl-release/DexGraspNet-ICRA2023/) | 作品与数据集标注CC BY-NC 4.0；原始物体来自多个数据源，仍需保留上游归属 |
| GenDexGrasp / MultiDex | 从YCB与ContactDB选取58个日用品，配套Allegro、Shadow等5种手；适合多手型对照 | [官方README](https://github.com/tengyu-liu/GenDexGrasp#data-preparation) | 本地检出未找到根LICENSE，README未明确统一数据许可；不能直接按本项目Apache 2.0重新发布 |
| DexGraspNet 2.0 | 物体网格、杂乱场景与抓取数据；适合后续杂乱场景研究 | [官方代码](https://github.com/PKU-EPIC/DexGraspNet2) · [作者数据页](https://huggingface.co/datasets/lhrlhr/DexGraspNet2.0/tree/main) | 官方代码和数据页标注CC BY-NC 4.0；仍需保留原始物体来源 |
| OakInk | 手物交互物体网格和人手抓取，适合接触学习及人手到机器人重定向 | [项目页](https://oakink.net/) · [官方数据页](https://huggingface.co/datasets/oakink/OakInk-v1) · [格式说明](https://github.com/oakink/OakInk/blob/main/docs/datasets.md) | 数据页标注CC BY-NC-SA 3.0；人体手模型及第三方物体条款分别核查 |
| Objaverse / Objaverse-XL | 大规模通用3D形状来源，适合筛选后扩大物体多样性 | [官方文档](https://objaverse.allenai.org/docs/intro/) · [XL官方代码与许可说明](https://github.com/allenai/objaverse-xl#license) | XL整体数据库采用ODC-By 1.0，单个模型各有许可；需逐物体筛选，不是统一Apache资产包 |

上述数量以作者页面为准，不能相加作为本项目已集成物体数量；不同数据集可能复用相同原始物体。

## 应下载哪个文件

### YCB

先选少量 `google_16k` 网格与纹理包，避免下载全部RGB-D帧。建议首批对象：`003_cracker_box`、`005_tomato_soup_can`、`006_mustard_bottle`、`011_banana`、`025_mug`、`035_power_drill`。这些是候选选择，不表示已经导入本项目。

### DexGraspNet

优先取得处理后的物体网格，抓取姿态包单独管理。本地已读源码：

- `research-repos/DexGraspNet/asset_process/README.md`：过滤、归一化、凸分解与导出流程。
- `research-repos/DexGraspNet/asset_process/decompose.py`：CoACD调用与URDF导出。
- `research-repos/DexGraspNet/grasp_generation/utils/object_model.py`：`ObjectModel.initialize()`读取 `meshdata/<object_code>/coacd/decomposed.obj` 并采样表面点。

处理结果还包括 `coacd.urdf` 与 `coacd_convex_piece_*.obj`。物体坐标和尺度应结合抓取记录确认，不能把归一化模型直接当作真实米制日用品。

本地研究源码commit：`bd1b13d7248729af117e1d46aaa6266b147a3c7b`。

### GenDexGrasp

官方README区分了不同包：

- `data.zip`：包含 `data/object/ycb`、`data/object/contactdb` 等物体资源。
- `env.zip`：Isaac Gym任务与资产包，不能直接当作Isaac Lab环境使用。
- `MultiDex.zip`：按手型组织的抓取数据，不等同于物体模型包。

具体Google Drive和百度网盘链接见官方README；本次没有下载或检验这些压缩包内容。

### DexGraspNet 2.0

作者数据页当前列出 `meshdata.tar.gz` 约4.62 GB；只收集物体时优先检查该包，无需把约222 GB的整个数据仓库下载下来。大小是网页显示值，可能随发布变化。

本地研究源码commit：`26ecd76121e3c8218ad53db9840cf34f6b81b076`。官方README将 `data/models` 链接至 `data/meshdata`。

### OakInk

只研究物体时先查看 `OakInkObjectsV2`、`OakInkVirtualObjectsV2` 与配套meta，而非整套视频。官方格式说明区分原始交互物体、虚拟迁移物体和MANO抓取参数；人手姿态不能直接当作Allegro或Shadow关节目标。

## 接入DexterousLab

建议从YCB小批量物体开始，再处理DexGraspNet的归一化资产。原始模型、处理结果、来源和校验和沿用项目现有资产目录，均放在项目根目录下。

1. 保存原始网格、纹理、下载地址、版本、校验和与许可归属。
2. 确认单位、物体坐标和尺寸；区分视觉网格与碰撞网格。
3. 设置质量、惯量、摩擦、刚体与碰撞。杯子等凹形物体需保留凹部，不能只用一个封闭凸包替代全部碰撞几何。
4. 用现有USD物体接口接入，先验证加载、质量、碰撞及小规模步进，再执行抓取。
5. 分别记录资产可加载、仿真可运行和抓取结果，不沿用原论文成功率。

当前Cube、Cylinder、Sphere已通过程序化场景物理冒烟测试，另有三个YCB样本完成下载、USD准备与真实仿真验证，见[样本验证报告](../experiments/ycb_objects_20261111.md)。集合级来源记录不表示全量下载；DexGraspNet、Objaverse、ManiSkill等其他集合仍未下载。外部USD入口已验证这三个YCB样本，其他物体仍需逐个验收。

## 本机下载入口连通性

2026-11-11使用HTTP HEAD探测，未下载模型正文：

| 入口 | 本机结果 |
|---|---|
| [YCB Mug · google_16k](https://ycb-benchmarks.s3.amazonaws.com/data/google/025_mug_google_16k.tgz) | HTTP 200，Content-Length 7,658,239字节 |
| [YCB Mustard Bottle · google_16k](https://ycb-benchmarks.s3.amazonaws.com/data/google/006_mustard_bottle_google_16k.tgz) | HTTP 200，Content-Length 10,703,139字节 |
| [DexGraspNet2 meshdata.tar.gz](https://huggingface.co/datasets/lhrlhr/DexGraspNet2.0/resolve/main/meshdata.tar.gz) | 数据列表可浏览，但本机HEAD请求连接重置；未验证大文件下载成功 |

DexGraspNet1的作者镜像目录可定位，但浏览器未解析出文件列表，尚未验证具体网格包的下载。可见的项目页面与实际模型下载连通性应分别记录。
