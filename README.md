<h1 align="center">
  <img src="docs/media/readme-style/wordmark.svg" alt="DexterousLab" width="820" />
</h1>

<p align="center">
  <img src="docs/media/readme-badges.svg" alt="Research Preview · Python 3.12 · PhysX · Configuration driven · Built on IsaacLab-Arena" width="720" />
</p>

<p align="center">
  <a href="#news"><img src="docs/media/readme-style/button-news.svg" alt="📰 News" width="130" /></a>
  <a href="#introduction"><img src="docs/media/readme-style/button-introduction.svg" alt="🧭 项目介绍" width="130" /></a>
  <a href="#installation">📦 安装教程</a> &nbsp;
  <a href="#quick-start"><img src="docs/media/readme-style/button-quick-start.svg" alt="🚀 快速开始" width="130" /></a>
  <a href="#experiments"><img src="docs/media/readme-style/button-experiments.svg" alt="🧪 实验结果" width="130" /></a>
  <a href="#documentation"><img src="docs/media/readme-style/button-documentation.svg" alt="📚 文档" width="130" /></a>
</p>

<p align="center">
  <img src="docs/media/dexterouslab-concept-cover.png" alt="DexterousLab 概念封面；实际支持范围见正文。" width="100%" /><br />
  <sub>概念封面 · <a href="docs/media/README.md">图片来源</a></sub>
</p>

<a id="news"></a>

## 📰 News

- **2026-11-10** — 新增 Allegro / Shadow 真实仿真运动视频，每种手录制16秒，支持离屏录制。[查看视频](#motion-video)。
- **2026-11-10** — DexterousLab 已发布到 GitHub，开放项目代码、配置、文档与实验记录。

<a id="introduction"></a>

## 🧭 项目介绍

**DexterousLab** 是基于 **NVIDIA Isaac Sim、Isaac Lab 和 IsaacLab-Arena** 的开源模块化科研框架，面向多指灵巧手抓取、操作控制与仿真数据采集。

项目将**灵巧手、物体、场景、任务和实验记录**统一组织，通过配置组合实验条件，减少重复搭建环境和处理资产的工作，让研究者专注于算法开发与实验分析。

其核心作用是提供统一的实验基础：管理多手型资产、构建桌面仿真、执行控制尝试，并保存状态、接触和结果，为抓取算法接入、对照研究与数据集构建提供支持。

<a id="installation"></a>

## 📦 安装

需要Linux、可用的NVIDIA GPU与驱动、Git；首次准备Arena环境还需要uv。以下命令在同一终端执行，先进入你希望存放项目的可写目录。

### 1. 克隆 DexterousLab

```bash
git clone https://github.com/ShunZuo-AI/DexterousLab.git
cd DexterousLab
export DEXLAB_ROOT="$PWD"
```

### 2. 准备仿真环境

**已有Arena环境**：指定其目录，跳过下面的首次安装步骤。当前GPUFree服务器使用：

```bash
export DEXLAB_ARENA_ROOT=/root/gpufree-data/IsaacLab-Arena
```

**全新机器首次安装**：在项目旁创建Arena目录，仅使用Arena的 `.venv`。

```bash
cd "$DEXLAB_ROOT/.."
git clone https://github.com/isaac-sim/IsaacLab-Arena.git
cd IsaacLab-Arena
git checkout 5fb3bd8a639578d46f4b5ed67b9b5239e1281b9a
git submodule update --init --recursive
uv sync --extra dev
export DEXLAB_ARENA_ROOT="$PWD"
```

已有可用环境时不要重新执行 `uv sync`。上述全新安装路线依据上游文档整理，尚未在空白机器验收；本机锁文件存在修改，固定源码commit不保证依赖与本机完全一致。[版本与安装详情](docs/installation.md)。

### 3. 启用项目并检查环境

阅读并同意Isaac Sim EULA后，在当前终端运行：

```bash
cd "$DEXLAB_ROOT"
export OMNI_KIT_ACCEPT_EULA=YES ACCEPT_EULA=Y
export PATH="$PWD/scripts:$PATH"
dexlab doctor
dexlab scene run --hand allegro --object cube --physics physx --dry-run
```

`doctor` 应输出 `ready: true`；启动器自动使用Arena的Python并设置Torch动态库路径，无需再创建环境或执行 `pip install -e .`。模型和缓存不随Git克隆下载，首次场景运行可能联网获取官方资产。

### 4. 验证首次仿真

```bash
dexlab scene run --hand allegro --object cube --physics physx --steps 20
```

确认完成20步后，再运行下方实验。已有项目目录时跳过克隆，设置 `DEXLAB_ROOT` 为实际项目路径即可。[常见问题](docs/installation.md#6-常见问题)。

<a id="quick-start"></a>

## 🚀 快速开始

完成上方安装与环境设置后，在项目目录执行以下命令。

### 1. 检查环境与加载场景

```bash
cd "$DEXLAB_ROOT"
export PATH="$PWD/scripts:$PATH"

dexlab doctor
dexlab scene run --hand allegro --object cube --physics physx
dexlab scene run --hand allegro --object cylinder --physics physx
dexlab scene run --hand shadow --object cube --physics physx
```

`scene run` 默认单环境、100 步、无窗口，执行零动作冒烟测试；启动器自动设置 Torch CUDA 动态库路径。

### 2. 执行抓取尝试

```bash
"$DEXLAB_ARENA_ROOT/.venv/bin/python" scripts/first_grasp_experiment.py --hand allegro
"$DEXLAB_ARENA_ROOT/.venv/bin/python" scripts/first_grasp_experiment.py --hand shadow
```

抓取脚本要求项目内已有官方资产缓存，准备方式见[资产说明](docs/installation.md#5-资产录制与测试)。每次执行接近、闭合、抬升与保持，共 **480 个环境步**。在已配置的云桌面会话中追加 `--render` 可保存截图；参数位于 [first_grasp.toml](configs/experiments/first_grasp.toml)，结果写入 `outputs/` 的独立运行目录。

<a id="experiments"></a>

## 🧪 实验结果

<a id="motion-video"></a>

### 两种灵巧手的真实仿真运动

[![Allegro与Shadow真实运动对照，均未达到抓取成功标准](docs/media/motion-20261110/preview.gif)](docs/media/motion-20261110/comparison.mp4)

[对照视频 MP4](docs/media/motion-20261110/comparison.mp4) · [Allegro](docs/media/motion-20261110/allegro.mp4) · [Shadow](docs/media/motion-20261110/shadow.mp4) · [录制说明与证据](docs/experiments/motion-video-20261110.md)

每段16秒、15 FPS，真实运行480个环境步；运动包含接近、闭合、抬升与保持。两次均未成功抓起并保持Cube。追加 `--record-video` 可离屏录制，无需打开云桌面窗口。

| 首次抓取基线 | 仿真步进 | 抓取结果 |
|---|---|---|
| Allegro + KUKA / Cube | 完成 480 环境步、1920 物理步 | 未达到抬升保持标准 |
| Shadow / Cube | 完成 480 环境步、1920 物理步 | 未达到抬升保持标准 |

Shadow 使用运动学基座路径，两组不作为同硬件性能排名。当前尚无成功抓取基准。[实验报告与日志](docs/experiments/first_grasp_experiment.md)。

### 真实仿真截图（闭合阶段）

| Allegro + KUKA | Shadow |
|---|---|
| ![Allegro闭合阶段，本次未成功抬升保持](docs/media/allegro-tabletop.jpg) | ![Shadow闭合阶段，本次未成功抬升保持](docs/media/shadow-tabletop.jpg) |

单元测试记录：**111 passed**。[测试日志](docs/experiments/first_grasp_final_tests.log)。

<a id="documentation"></a>

## 📚 文档

| 使用与配置 | 研究与扩展 |
|---|---|
| [安装与环境准备](docs/installation.md) | [框架逻辑与目录职责](docs/architecture.md) |
| [运行命令与配置参考](docs/reference/usage-details.md) | [框架逻辑与目录职责](docs/architecture.md) |
| [模型图形预览](docs/asset-preview.md) | [论文源码分析与迁移状态](docs/paper_reproductions/README.md) |
| [采集、重放与批量评测](docs/research/dexgarmentlab_usage.md) | [数据与坐标契约](docs/data-contract.md) |

第一方代码采用 [Apache 2.0](LICENSE)；第三方模型、论文组件和图片保留各自许可。[算法归属](docs/paper_reproductions/ATTRIBUTION.md) · [官方商品图来源](docs/media/official-products/README.md)。
