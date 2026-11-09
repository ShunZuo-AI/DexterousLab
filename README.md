<h1 align="center">
  <img src="docs/media/readme-style/wordmark.svg" alt="DexterousLab" width="820" />
</h1>

<p align="center">
  <img src="docs/media/readme-badges.svg" alt="Research Preview · Python 3.12 · PhysX · Configuration driven · Built on IsaacLab-Arena" width="720" />
</p>

<p align="center">
  <a href="#news">📰 News</a> &nbsp; · &nbsp;
  <a href="#introduction">🧭 项目介绍</a> &nbsp; · &nbsp;
  <a href="#features">✨ 核心功能</a> &nbsp; · &nbsp;
  <a href="#quick-start">🚀 快速开始</a> &nbsp; · &nbsp;
  <a href="#experiments">🧪 实验结果</a> &nbsp; · &nbsp;
  <a href="#documentation">📚 文档</a>
</p>

<p align="center">
  <img src="docs/media/dexterouslab-concept-cover.png" alt="DexterousLab 概念封面；实际支持范围见正文。" width="100%" /><br />
  <sub>概念封面 · <a href="docs/media/README.md">图片来源</a></sub>
</p>

<a id="news"></a>

## 📰 News

- **2026-11-10** — DexterousLab 已发布到 GitHub，开放项目代码、配置、文档与实验记录。

<a id="introduction"></a>

## 🧭 项目介绍

**DexterousLab** 是基于 **NVIDIA Isaac Sim、Isaac Lab 和 IsaacLab-Arena** 的开源模块化科研框架，面向多指灵巧手抓取、操作控制与仿真数据采集。

项目将**灵巧手、物体、场景、任务和实验记录**统一组织，通过配置组合实验条件，减少重复搭建环境和处理资产的工作，让研究者专注于算法开发与实验分析。

其核心作用是提供统一的实验基础：管理多手型资产、构建桌面仿真、执行控制尝试，并保存状态、接触和结果，为抓取算法接入、对照研究与数据集构建提供支持。

<a id="features"></a>

## ✨ 核心功能

### 🖐️ 多手型资产管理

统一查询手型、来源与许可，校验模型文件，将已接入的URDF转换为USD，并在云桌面预览、运行资产级物理检查。已有 **22个配置、17个厂商 / 项目**通过验证。入口：`dexlab assets`。[手型清单](docs/asset_aggregation/coverage.md) · [模型预览](docs/asset-preview.md)。

### 🧩 配置驱动的场景构建

通过配置选择灵巧手、物体和桌面任务，调整物体位姿、尺寸、质量与摩擦参数，无需为每个组合重写环境。桌面场景已接入 **Allegro + KUKA、Shadow**，支持 **立方体、圆柱、球体**。入口：`dexlab scene run`。[配置说明](docs/reference/usage-details.md)。

### 🎮 抓取动作与仿真执行

执行接近、下降、手指闭合、抬升和保持，记录不同阶段的物理响应与结果。Allegro通过KUKA机械臂运动，Shadow使用规定的基座路径及独立关节 / 腱控制；当前为人工配置的抓取基线。入口：`scripts/first_grasp_experiment.py`。[实验参数](configs/experiments/first_grasp.toml)。

### 📊 状态采集与实验记录

采集关节位置 / 速度、动作、手掌与物体姿态、指尖接触力和接触点，保存 **JSONL、数值NPZ、配置快照与日志**；渲染模式可保存阶段截图。每次运行独立建目录，成功与失败记录都保留，便于分析和复核。[数据约定](docs/data-contract.md)。

### 🔁 姿态重放与批量评测

保存仿真实测姿态，恢复机器人与物体状态后重放，或批量运行候选文件，统计已评估结果与失败原因。当前支持 **Shadow + Cube / Sphere / Cylinder**，入口为 `dexlab experiment` 下的 `capture`、`replay`、`batch`。[操作示例](docs/research/dexgarmentlab_usage.md)。

### 🔬 抓取算法接入与研究

提供统一的抓取候选、生成器 / 验证器抽象接口和数据写入接口；已迁移 **DexGraspNet能量函数与退火优化核心组件**。完整候选生成、通用物理验证和学习式执行策略仍待接通。[源码分析与迁移状态](docs/paper_reproductions/README.md)。

**实验流程：资产选择 → 场景构建 → 动作执行 → 数据采集 → 重放与评测。** 资产级验证不代表已适配桌面抓取；当前桌面任务手型仍为Allegro和Shadow。

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
| [运行命令与配置参考](docs/reference/usage-details.md) | [框架逻辑与目录职责](docs/architecture.md) |
| [模型图形预览](docs/asset-preview.md) | [论文源码分析与迁移状态](docs/paper_reproductions/README.md) |
| [采集、重放与批量评测](docs/research/dexgarmentlab_usage.md) | [数据与坐标契约](docs/data-contract.md) |

第一方代码采用 [Apache 2.0](LICENSE)；第三方模型、论文组件和图片保留各自许可。[算法归属](docs/paper_reproductions/ATTRIBUTION.md) · [官方商品图来源](docs/media/official-products/README.md)。
