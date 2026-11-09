# 首版交付与实测报告

验证日期：2026-11-06，Asia/Shanghai。输出目录名称采用 UTC，约为北京时间 13:44–13:55。

## 阶段 0：服务器和已有项目

- 起始工作区：`/root/gpufree-data/IsaacLab-Arena`。
- 检查时 `/root/gpufree-data/DexterousLab` 不存在，没有可以继承的项目代码或单元测试。
  因此从官方扩展 API 和本次新增源码创建独立项目，没有覆盖既有 DexterousLab。
- 沙箱内 `nvidia-smi` 无法连接驱动；沙箱外验证得到 NVIDIA L40S，显存 46068 MiB。
- Python：`/root/gpufree-data/IsaacLab-Arena/.venv/bin/python`，3.12.16。
- 实际安装分发版本：Isaac Sim `6.2.0.0`、Isaac Lab `28.0.0`、Arena `0.3.0`、
  PyTorch `2.11.0+cu130`、pytest `9.1.1`。
  注意安装元数据中的 Isaac Lab 版本确实是 `28.0.0`，没有用 README 中的 `3.0.0` 代替实测值。
- doctor 在共享环境中验证了 CUDA 可用，以及 `torch.linalg.inv(torch.eye(3, device='cuda'))` 能完成。
- 未执行安装、`uv sync`、包升级、驱动修改或创建新 Python 环境。
- 已阅读 README、环境 factory/description/builder、Object/Scene/EmbodimentBase、KUKA+Allegro、
  Dexsuite 示例、Shadow 官方资产和腱动作 API。
- Arena 原仓库已有用户修改：两个环境文件、GR00T HDF5、两个 submodule 工作树、`uv.lock`，
  以及未跟踪的 `uv.lock.official.backup`。完成后状态列表一致，没有修改官方源码。
  检查 Git 状态时禁用 LFS clean filter，以免只读 `.git/lfs` 导致普通 status 失败。

运行前选定的 Arena 基线：`test_arena_env_builder_cfg.py -k 'not applies'`，**13 passed，1 deselected**。
证据：`dexlab-arena-baseline.log` 和 `.xml`。

## 阶段 1：项目骨架和 CLI

已实现 `doctor`、`assets list`、`scene list`、`scene run`、`arena run`。
对象、机器人、场景、任务和实验使用 TOML；未知字段、未知资产、未支持后端和超预算请求明确失败。
没有依赖新增。新增 **38 项单元测试全部通过**，目标项目目录再次运行结果也是 38 passed。
JUnit：`docs/dexlab-unit-tests.xml`。

## 阶段 2–4：实际 GPU 仿真

以下全部使用共享 Python、PhysX、`cuda:0`、一个环境、零动作、无相机、headless。
除完成标记外，入口还检查进程退出码与完成步数；自定义场景检查真实动作维度、关节和指尖 body 名。

| 运行 | 步数 | 结果 | `outputs/` 下证据目录 |
|---|---:|---|---|
| 官方 `cube_goal_pose` | 20 | 通过，动作维度 7 | `20261106T054456Z-arena-6f1a2f45` |
| 官方 `dexsuite_lift` | 100 | 通过，动作维度 23 | `20261106T054602Z-arena-b5cf7838` |
| 自定义 Allegro + cube | 20 | 通过，动作维度 23 | `20261106T054859Z-scene-ab59ed97` |
| 自定义 Shadow + cube | 20 | 通过，动作维度 20 | `20261106T054927Z-scene-7a8c7c79` |
| Allegro + cube 位姿/尺度配置 | 20 | 通过 | `20261106T055004Z-scene-3da16b5b` |
| Allegro + sphere | 10 | 通过，实际半径 0.025 m | `20261106T055437Z-scene-5c70e15f` |
| Allegro + cylinder | 10 | 通过，半径 0.025 m，高度 0.08 m | `20261106T055452Z-scene-cc64be04` |
| 配置 cube 的实际 spawner 参数复验 | 20 | 通过，实际尺寸 0.06×0.06×0.06 m | `20261106T055507Z-scene-33425705` |

最后一次 cube 复验的实际初始位置为 `[-0.5, 0.05, 0.3]`，四元数
`[0, 0, 0.3826834323650898, 0.9238795325112867]`；几何尺寸证明 1.2 倍缩放确实被消费。
自定义场景保留初始、第 1 步、最后一步的真实世界坐标与关节状态。

第一次自定义 Allegro 尝试失败，目录 `20261106T054621Z-scene-ef3db0a6`：
官方 KUKA 观测中的 `generated_commands('object_pose')` 依赖官方专用任务指令。
修复位于新项目 `integrations/isaaclab/observations.py`：采用自己的关节和物体状态观测。
没有修改官方代码，失败日志和失败 `result.json` 也保留。

### Shadow 的真实结论

当前安装中存在官方 `isaaclab_assets.robots.shadow_hand.SHADOW_HAND_PHYSX_CFG`，
其源文件是 `submodules/IsaacLab/source/isaaclab_assets/isaaclab_assets/robots/shadow_hand.py`。
实际加载的官方资产：

```text
https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/6.2/Isaac/Robots_Multiphysics/ShadowRobot/ShadowHandMultiPhysics_v0/right_hand/right_hand.usda
```

实际运行得到 24 个物理关节，16 个直接关节控制量 + 4 个腱控制量，五个指尖和 `rh_palm` 掌 body。
具体名称、实际动作向量分段顺序和 USD 路径见该运行的 `robot_mapping.json`。
这证明最小加载与零动作步进可用，不证明抓取能力、腱闭环性能或长期物理稳定性。
没有复制或重新分发 USD，后续分发资产需遵循原资产条款。

### 官方回归范围

实现后在用户明确要求的**已有 native `.venv`**运行：

```bash
cd /root/gpufree-data/IsaacLab-Arena
LD_LIBRARY_PATH="$PWD/.venv/lib/python3.12/site-packages/torch/lib:${LD_LIBRARY_PATH:-}" \
OMNI_KIT_ACCEPT_EULA=YES ACCEPT_EULA=Y PYTHONDONTWRITEBYTECODE=1 \
ISAACLAB_ARENA_FORCE_EXIT_ON_COMPLETE=1 \
.venv/bin/python -m pytest -q -p no:cacheprovider \
  isaaclab_arena/tests/test_arena_env_builder_cfg.py
```

结果：**14 passed，35 warnings，9.76 s**，包括其 SimulationApp 内测试。
证据：`docs/dexlab-arena-regression.log` 和 `.xml`。
当前用户明确要求复用 native 环境，因此未依照仓库 Docker 测试技能重新创建容器。
没有运行全部三阶段官方测试套件，不能据此声称官方所有测试全部通过。
警告主要来自现有 Isaac Lab/Arena 物理配置 API 的弃用提示。

## 阶段 5：接口完成度

已实现候选记录、生成器和验证器抽象接口、无覆盖 JSONL 写入器和结果统计器。
已覆盖四元数单位、有限数值、未知结果、字段一致性与文件覆盖保护测试。
生成器和物理验证器不可直接实例化，没有伪装成可用抓取算法。

尚未实现：DexGraspNet、GenDexGrasp、Fast-Grasp'D 算法、学习式生成、抓取执行闭环、
完整物理验证、真实接触点提取、抗扰稳定性协议、杯子模型、URDF/Mesh 转换、
外部 USD 场景验收、自定义 Newton 场景、GUI/相机流程、独立 Allegro 无臂安装与 RL 训练入口。

**所有本次运行均为环境冒烟验证，`grasp_success=null`；没有报告抓取成功率。**

## 交付文件

完整文件清单在 `docs/files.txt`，核心文件为：

- `pyproject.toml`、`.gitignore`、`README.md`：项目与使用说明。
- `scripts/dexlab`：唯一解释器启动、库路径设置。
- `src/dexterous_lab/cli.py`、`config.py`、`runtime.py`：CLI、配置校验和有证据的运行封装。
- `assets/primitives.py`、`objects/geometry.py`：注册资产、尺寸计算。
- `scenes/tabletop.py`、`tasks/lift.py`：自定义 factory 和官方任务复用。
- `robots/shadow.py`：独立 Shadow 关节/腱动作。
- `integrations/arena/worker.py`、`integrations/isaaclab/observations.py`：实际仿真与状态观测。
- `grasp_synthesis/candidate.py`、`grasp_generation/base.py`、`grasp_execution/base.py`、
  `datasets/writer.py`、`evaluation/grasp.py`：数据与研究扩展接口。
- `configs/`：9 个配置文件；`tests/`：4 个测试文件。
- `docs/architecture.md`、`data-contract.md`、本报告、JUnit 与基线/回归日志。

所有新增实现均在 DexterousLab。没有修改官方源码、增加依赖或执行 GitHub push。
README 提供实际运行命令与限制说明。
