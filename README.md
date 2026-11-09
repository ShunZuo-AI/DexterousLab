<h1 align="center">
  <img src="docs/media/readme-style/wordmark.svg" alt="DexterousLab" width="820" />
</h1>

<p align="center">
  <strong>基于 Isaac Sim · Isaac Lab · IsaacLab-Arena 的多指灵巧抓取研究框架</strong>
</p>

<p align="center">
  <img src="docs/media/readme-badges.svg" alt="Research Preview · Python 3.12 · PhysX · Configuration driven · Built on IsaacLab-Arena" width="720" />
</p>

<p align="center">
  <a href="#news">📰 News</a> &nbsp; · &nbsp;
  <a href="#introduction">🧭 项目介绍</a> &nbsp; · &nbsp;
  <a href="#features">✨ 当前能力</a> &nbsp; · &nbsp;
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

其核心作用是提供统一的实验基础：管理多手型资产、构建桌面仿真、执行控制尝试，并保存状态、接触和结果，为抓取算法接入、对照研究与数据集构建提供支持。当前实现范围见下表。

<a id="features"></a>

## ✨ 当前能力

| 模块 | 已实现内容 |
|---|---|
| 🖐️ 灵巧手资产 | 22 个配置通过资产级物理验证，覆盖 17 个厂商 / 项目；支持查询、转换与预览 |
| 🧩 桌面环境 | Allegro + KUKA、Shadow；Cube / Cylinder / Sphere；通过配置切换 |
| 📊 数据记录 | 关节、手掌、物体和指尖接触状态；配置快照、JSONL / NPZ、日志与截图 |
| 🔬 抓取研究 | 候选与数据接口；DexGraspNet 能量和退火优化组件，完整生成与验证闭环仍待接通 |

工作流：**配置选择 → 场景构建 → 动作执行 → 状态采集 → 结果评测**。

资产级验证不等于桌面抓取适配；当前桌面任务支持 **Allegro 和 Shadow**。[查看手型清单](docs/asset_aggregation/coverage.md)。

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
