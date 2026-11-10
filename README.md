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

**已有可用的Arena环境：** 克隆项目后设置路径即可，不需要创建第二个Python环境。

```bash
# 新用户首次获取项目；当前服务器已有目录时跳过clone
cd /root/gpufree-data
git clone https://github.com/ShunZuo-AI/DexterousLab.git
cd DexterousLab
export DEXLAB_ARENA_ROOT=/root/gpufree-data/IsaacLab-Arena
export PATH="$PWD/scripts:$PATH"
dexlab doctor
```

**全新机器：** 先准备兼容的Isaac Sim / Isaac Lab / Arena环境，再执行上述项目步骤。[完整安装教程、版本说明与排错](docs/installation.md)。

<a id="quick-start"></a>

## 🚀 快速开始

以下命令使用当前服务器已有的 Arena Python 环境，无需新建环境或重新安装 Isaac Sim。

### 1. 检查环境与加载场景

```bash
cd /root/gpufree-data/DexterousLab
export PATH="$PWD/scripts:$PATH"

dexlab doctor
dexlab scene run --hand allegro --object cube --physics physx
dexlab scene run --hand allegro --object cylinder --physics physx
dexlab scene run --hand shadow --object cube --physics physx
```

`scene run` 默认单环境、100 步、无窗口，执行零动作冒烟测试；启动器自动设置 Torch CUDA 动态库路径。

### 2. 执行抓取尝试

```bash
/root/gpufree-data/IsaacLab-Arena/.venv/bin/python scripts/first_grasp_experiment.py --hand allegro
/root/gpufree-data/IsaacLab-Arena/.venv/bin/python scripts/first_grasp_experiment.py --hand shadow
```

每次执行接近、闭合、抬升与保持，共 **480 个环境步**。在已配置的云桌面会话中追加 `--render` 可保存截图；参数位于 [first_grasp.toml](configs/experiments/first_grasp.toml)，结果写入 `outputs/` 的独立运行目录。

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
