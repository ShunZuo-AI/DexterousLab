<h1 align="center">
  <img src="docs/media/readme-style/wordmark.svg" alt="DexterousLab" width="820" />
</h1>

<p align="center">
  <strong>简体中文</strong> &nbsp; | &nbsp; <a href="README.en.md">English</a>
</p>

<p align="center">
  🔬 Research Preview &nbsp; · &nbsp; 🐍 Python 3.12 &nbsp; · &nbsp; ⚛️ PhysX &nbsp; · &nbsp; 🧩 配置驱动 &nbsp; · &nbsp; 🤖 IsaacLab-Arena
</p>

<p align="center">
  <img src="docs/media/dexterouslab-concept-cover.png" alt="DexterousLab 概念封面；实际支持范围见正文。" width="100%" /><br />
  <sub>概念封面 · <a href="docs/media/README.md">图片来源</a></sub>
</p>

<a id="news"></a>

## 📰 News

- **2026-11-11** — 新增三个 YCB 物体样本的下载与准备命令，完成真实 PhysX 仿真验证。[查看记录](docs/experiments/ycb_objects_20261111.md)
- **2026-11-10** — 发布 Allegro 与 Shadow 的真实仿真运动视频，每种手录制 16 秒。[查看视频](#motion-video)
- **2026-11-10** — 项目开源：提供代码、配置、使用文档与实验记录。

<a id="introduction"></a>

## 🧭 项目介绍

**DexterousLab** 是面向多指灵巧手抓取与仿真数据采集的开源研究框架，基于 NVIDIA Isaac Sim、Isaac Lab 和 IsaacLab-Arena。通过配置选择灵巧手、物体、桌面场景与任务，运行控制实验，并保存关节状态、物体状态、接触数据和实验结果，便于算法接入与对照研究。

<a id="installation"></a>

## 📦 安装

**运行要求：** Linux、NVIDIA GPU 与可用驱动、Git。首次安装 Arena 还需准备 `uv`。以下命令在同一终端执行。

### 1. 克隆项目

```bash
git clone https://github.com/ShunZuo-AI/DexterousLab.git
cd DexterousLab
export DEXLAB_ROOT="$PWD"
```

### 2. 指定 Arena 环境

**已有可用环境** → 设置 Arena 路径，直接进入第 3 步。当前服务器使用：

```bash
export DEXLAB_ARENA_ROOT=/root/gpufree-data/IsaacLab-Arena
```

**首次安装 Arena** → 在 DexterousLab 同级目录执行：

```bash
cd "$DEXLAB_ROOT/.."
git clone https://github.com/isaac-sim/IsaacLab-Arena.git
cd IsaacLab-Arena
git checkout 5fb3bd8a639578d46f4b5ed67b9b5239e1281b9a
git submodule update --init --recursive
uv sync --extra dev
export DEXLAB_ARENA_ROOT="$PWD"
```

> 首次安装路线尚未在空白机器验收；本机锁文件存在修改，固定源码版本不能保证依赖完全一致。已有可用环境请跳过 `uv sync`。[安装详情与版本记录](docs/installation.md)

### 3. 启用命令行

阅读并同意 Isaac Sim EULA 后执行：

```bash
cd "$DEXLAB_ROOT"
export OMNI_KIT_ACCEPT_EULA=YES ACCEPT_EULA=Y
export PATH="$DEXLAB_ROOT/scripts:$PATH"
dexlab doctor
```

`doctor` 应返回 `ready: true`。项目复用 Arena 的 `.venv`，启动器自动配置 Torch CUDA 动态库路径。

### 4. 验证场景

```bash
# 检查配置
dexlab scene run --hand allegro --object cube --physics physx --dry-run

# 执行 20 步零动作仿真
dexlab scene run --hand allegro --object cube --physics physx --steps 20
```

模型与缓存不随 Git 克隆下载，首次运行可能需要联网获取官方资产。完成 20 步表示环境可运行；抓取实验见下节。[常见问题](docs/installation.md#6-常见问题)

<a id="quick-start"></a>

## 🚀 快速开始

完成安装后，在项目目录运行。

### 切换灵巧手与物体

```bash
# Allegro + Cube
dexlab scene run --hand allegro --object cube --physics physx

# Allegro + Cylinder
dexlab scene run --hand allegro --object cylinder --physics physx

# Shadow + Cube
dexlab scene run --hand shadow --object cube --physics physx
```

默认运行 **1 个环境、100 步、无窗口**，用于零动作冒烟测试，不评价抓取能力。

### 下载真实物体

提供 YCB 的饼干盒、芥末瓶和杯子三个样本。下载包合计约 30 MB，包含网格与纹理，保存在项目内。

```bash
# 下载三个样本；重复执行会校验并复用已有文件
dexlab assets download-ycb --objects cracker_box mustard_bottle mug

# 使用现有 Isaac Lab 转换为 USD，并生成本地物体配置
dexlab assets prepare-ycb --objects cracker_box mustard_bottle mug

# 加载真实物体，执行 100 步零动作仿真
dexlab scene run --hand allegro --object ycb_mustard_bottle --physics physx --steps 100
dexlab scene run --hand allegro --object ycb_mug --physics physx --steps 100
```

原始文件位于 `assets/objects/ycb/`；准备命令生成 `configs/objects/ycb_*.toml`。模型与生成配置不随 Git 分发，首次使用需先完成以上两步。质量和摩擦为试验设定，零动作测试不表示抓取成功。[下载与验证记录](docs/experiments/ycb_objects_20261111.md) · [YCB 来源与许可](https://registry.opendata.aws/ycb-benchmarks/)

### 其他物体数据集下载

六类来源共用下载入口；大数据集按文件选择，不默认全量下载。

| 来源 | 命令 |
|---|---|
| YCB | `dexlab assets download ycb --files mug` |
| DexGraspNet | `dexlab assets download dexgraspnet --files meshdata.tar.gz` |
| GenDexGrasp / MultiDex | `dexlab assets download gendexgrasp --files data.zip` |
| DexGraspNet 2.0 | `dexlab assets download dexgraspnet2 --files meshdata.tar.gz` |
| OakInk | `dexlab assets download oakink --files shape/OakInkObjectsV2.zip` |
| Objaverse-XL | `dexlab assets download objaverse-xl --manifest selected-objects.json` |

使用 `--list-files` 查看可选包，`--dry-run` 查看下载计划。Hugging Face连接受限时可显式追加 `--hf-endpoint https://hf-mirror.com`。Objaverse需先准备带逐模型来源、许可和SHA-256的选择清单。除YCB外，下载归档不自动转成仿真资产。[脚本、清单格式与网络实测](docs/reference/asset-downloads.md)

### 执行抓取尝试

先按[资产准备说明](docs/installation.md#5-资产录制与测试)准备官方资产缓存，再选择一种手运行：

```bash
"$DEXLAB_ARENA_ROOT/.venv/bin/python" scripts/first_grasp_experiment.py --hand allegro
"$DEXLAB_ARENA_ROOT/.venv/bin/python" scripts/first_grasp_experiment.py --hand shadow
```

| 项目 | 说明 |
|---|---|
| 执行流程 | 接近 → 闭合 → 抬升 → 保持，共 480 个环境步 |
| 实验配置 | [configs/experiments/first_grasp.toml](configs/experiments/first_grasp.toml) |
| 数据保存 | 每次运行写入 `outputs/` 下的独立目录 |
| 录制视频 | 追加 `--record-video`，支持离屏录制 |
| 保存截图 | 在已配置的云桌面会话中追加 `--render` |

<a id="experiments"></a>

## 🧪 实验结果

**两种手均完成真实仿真与控制尝试，但本次均未达到 Cube 抬升并保持的成功标准。**

| 实验 | 环境步 / 物理步 | 抓取结果 |
|---|---|---|
| Allegro + KUKA · Cube | 480 / 1920 | 未成功抬升并保持 |
| Shadow · Cube | 480 / 1920 | 未成功抬升并保持 |

Allegro 搭载 KUKA 机械臂；Shadow 使用运动学基座路径。两组控制方式不同，结果用于记录当前基线。[实验报告与日志](docs/experiments/first_grasp_experiment.md)

<a id="motion-video"></a>

### 仿真运动视频

[![Allegro 与 Shadow 的真实仿真运动；两次抓取均未成功](docs/media/motion-20261110/preview.gif)](docs/media/motion-20261110/comparison.mp4)

[▶ 对照视频](docs/media/motion-20261110/comparison.mp4) &nbsp; · &nbsp; [Allegro](docs/media/motion-20261110/allegro.mp4) &nbsp; · &nbsp; [Shadow](docs/media/motion-20261110/shadow.mp4) &nbsp; · &nbsp; [录制说明](docs/experiments/motion-video-20261110.md)

每种手录制 **16 秒 · 15 FPS · 480 个环境步**，展示接近、闭合、抬升与保持过程。

### 闭合阶段截图

| Allegro + KUKA | Shadow |
|---|---|
| ![Allegro 闭合阶段，本次未成功抬升保持](docs/media/allegro-tabletop.jpg) | ![Shadow 闭合阶段，本次未成功抬升保持](docs/media/shadow-tabletop.jpg) |

单元测试记录：**174 passed**。[查看测试日志](docs/experiments/downloaders-20261111/tests.log)

<a id="documentation"></a>

## 📚 文档

| 文档 | 内容 |
|---|---|
| [安装指南](docs/installation.md) | 环境准备、版本记录与常见问题 |
| [使用参考](docs/reference/usage-details.md) | 运行命令与配置参数 |
| [框架与目录](docs/architecture.md) | 模块职责与扩展位置 |
| [开发指南](docs/development.md) | 代码规范、模块边界与测试方法 |
| [资产预览](docs/asset-preview.md) | 模型图形预览 |
| [数据采集与评测](docs/research/dexgarmentlab_usage.md) | 采集、重放与批量评测 |
| [数据契约](docs/data-contract.md) | 数据格式、单位与坐标约定 |
| [论文实现分析](docs/paper_reproductions/README.md) | 源码研究与算法迁移状态 |

第一方代码采用 [Apache 2.0](LICENSE)。第三方模型、论文组件与图片遵循各自许可：[算法归属](docs/paper_reproductions/ATTRIBUTION.md) · [图片来源](docs/media/official-products/README.md)。
