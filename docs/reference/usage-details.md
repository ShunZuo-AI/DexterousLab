# 使用细节与配置参考

面向多指灵巧抓取研究的配置驱动框架，基于本机已经安装的 Isaac Sim、Isaac Lab 和 IsaacLab-Arena。
第一版把环境构建、策略执行入口、运行证据和抓取数据接口分开。

第一次有动作的 Allegro/Shadow 桌面抓取实验已执行，结果均未达到有效抬升保持标准；完整审计、轨迹、截图和失败分析见 [首次抓取实验报告](../experiments/first_grasp_experiment.md)。

```bash
/root/gpufree-data/IsaacLab-Arena/.venv/bin/python scripts/first_grasp_experiment.py --hand allegro --render
/root/gpufree-data/IsaacLab-Arena/.venv/bin/python scripts/first_grasp_experiment.py --hand shadow --render
```

新增 Shadow 姿态采集、保存重放和批量候选验证入口，见 [使用说明与三个示例](../research/dexgarmentlab_usage.md)和[真实实验交付报告](../research/dexgarmentlab_results.md)。
其架构依据和未移植范围见 [DexGarmentLab 源码分析](../research/dexgarmentlab_analysis.md)。

```bash
./scripts/dexlab experiment capture --object cube --include-sphere --steps 100
./scripts/dexlab experiment replay --input <capture_run>/trial_000/candidate.json --include-sphere
./scripts/dexlab experiment batch --input <capture_run>/candidates10.jsonl --include-sphere
```

**`dexlab scene run` 执行的是 `zero_action` 冒烟测试；有动作的抓取实验使用独立脚本。场景加载或物理步进不等于抓取成功。**
M2 的 100 步验收、运行证据与代码位置见 [M2 报告](../m2-validation.md)。
早期 M0/M1 记录保留在 `docs/validation.md`。

M3 最新资产聚合、真实验证结果及缺失项见 [第二批资产报告](../asset_aggregation/expanded-report.md)和[逐厂商覆盖表](../asset_aggregation/coverage.md)。
当前 22 条型号/版本配置、17 个厂商通过 100 步物理验证；新增手的桌面控制器及机械耦合尚未完成专项验收。
来源索引覆盖 30 个厂商，登记条目与可用模型、完成仿真的模型分别记录。

```bash
export PATH="/root/gpufree-data/DexterousLab/scripts:$PATH"
dexlab assets manufacturers
dexlab assets hands --manufacturer unitree
dexlab assets inspect --id unitree/dex3_1/right
dexlab assets fetch --id unitree/dex3_1/right
dexlab assets convert --id unitree/dex3_1/right --format usd
dexlab assets validate --id unitree/dex3_1/right --steps 100
dexlab assets preview --id unitree/dex3_1/right
```

`fetch` 从已核验 commit 的参考仓库提取首批批准的模型；重复执行会校验原始文件 SHA256。
尚未审核许可或依赖的模型明确拒绝提取。`preview` 在服务器云桌面打开已验证手型，默认保持 10 分钟，详见[图形预览说明](../asset-preview.md)。
新模型通过资产级验证后仍需编写任务控制/接触映射，才可接入桌面任务；不自动复用 Allegro 控制器。

## 使用现有环境

代码和项目资产统一存放在 `/root/gpufree-data/DexterousLab/`，具体目录见 [存储布局](../storage-layout.md)。资产镜像与 USD 临时副本在
`/root/gpufree-data/DexterousLab/assets/cache`（项目外的旧路径保留兼容链接）；SDK/CUDA 缓存在 `.cache`；模型在 `models`；数据集在 `datasets`。
启动器为仿真子进程设置相应路径，Kit 使用数据盘上的 portable root。
官方资产 URL 仍作为来源，实际下载的资产副本保存在数据盘；这不代表完整官方资产库已离线下载。
`dexlab doctor` 会列出具体目录。旧资产与 SDK 缓存已迁移到数据盘，原路径保留兼容软链接；
没有删除旧数据。迁移清单为 `docs/storage-migration.json`。

唯一 Python 环境：`/root/gpufree-data/IsaacLab-Arena/.venv`。
不需要 `uv sync`、`pip install`、新的 venv/conda 或重新安装 Isaac Sim。

```bash
cd /root/gpufree-data/DexterousLab
export PATH="$PWD/scripts:$PATH"
dexlab doctor
dexlab assets list
dexlab scene list
```

`scripts/dexlab` 自动选用共享解释器，并在启动 Python **之前**将
`.venv/lib/python3.12/site-packages/torch/lib` 加入 `LD_LIBRARY_PATH`，保留已有路径。
doctor 检查实际 GPU、安装分发版本和 CUDA 矩阵求逆；不靠文档猜测版本。
移动 Arena checkout 时可设置 `DEXLAB_ARENA_ROOT`，仍只使用该 checkout 的 `.venv`。
当前采用源码目录执行方式；`pyproject.toml` 提供包结构及 console-script 声明，尚未验证独立 wheel 分发。

## 复现官方场景

```bash
dexlab arena run cube_goal_pose --steps 20 --num-envs 1 --backend physx
dexlab arena run dexsuite_lift --steps 100 --num-envs 1 --backend physx
```

入口直接调用当前 checkout 的官方环境 factory、ArenaEnvBuilder 和 Gym 环境接口，
使用自己的有限步循环保存可核验的完成证据。没有复制或修改官方 factory，
也没有声称运行了官方 `policy_runner.py` 的完整实验工作流。
`dexsuite_lift` 官方默认后端是 Newton，这里显式选择已有验证基础的 PhysX。

## 自定义桌面场景

```bash
dexlab scene run --hand allegro --object cube --physics physx
dexlab scene run --hand allegro --object cylinder --physics physx
dexlab scene run --hand shadow --object cube --physics physx
dexlab scene run --hand allegro --object sphere --steps 10
```

默认无可视化、无相机，适合云服务器。当前本地 Arena 的 AppLauncher 使用 `visualizer=None`
表示 headless；没有向官方脚本传入不存在的 `--headless` 参数。
DexterousLab 接受自己的 `--headless` 标志，但它只是明确默认行为，不切换底层模式。
此 scene CLI 的 GUI、相机策略和 Newton 自定义场景尚未接入（资产预览和实验脚本另有渲染入口），未知参数或后端会明确报错。
每次最多 4 个并行环境、1000 步；自定义场景默认 1 个环境、100 步、300 秒子进程超时。
`--backend` 保留为 `--physics` 的兼容别名；官方 `arena run` 默认步数仍为 20。

### Allegro 的安装方式

`--hand allegro` 明确表示官方 **KUKA iiwa7 + Allegro** 组合：7 个机械臂关节与 16 个手指关节，
总动作维度 23。不是独立漂浮的 Allegro，也没有实现独立 Allegro 的自由根位姿控制。
手与机械臂的安装变换来自官方组合 USD；配置中的机器人 pose 设置机械臂根坐标系，
日志中的 `hand_root_pose` 则读取实际 `palm_link`，两者不能互换。

### Shadow 的边界

使用当前 Isaac Lab 的 `SHADOW_HAND_PHYSX_CFG`，是独立固定基座手，不带 KUKA。
配置明确区分 24 个物理关节、16 个直接关节电机和 4 个固定腱控制量，动作维度 20。
掌坐标系为 `rh_palm`；五指接触映射与 Allegro 的四指映射分开。
实际资产可用性和小规模仿真结论见验证报告；没有就绪的抓取执行器、训练策略或成功率基准。

### 配置如何连接

```text
configs/experiments/tabletop.toml
    ├── robots/allegro.toml       机器人、控制坐标和指尖映射
    ├── objects/cube.toml         形状、质量、摩擦、位姿和尺度
    ├── scenes/tabletop.toml      桌子、灯光和时间步
    └── tasks/lift.toml           抬升目标、容差和超时
                    ↓
       HandRegistry + ObjectRegistry
                    ↓
       DexterousLabTabletopEnvironment.build()
                    ↓
     Arena Scene + Embodiment + LiftObjectTask
                    ↓
            ArenaEnvBuilder
                    ↓
         reset / zero-action step / 状态日志
```

先查看有效配置，不启动 Isaac Sim：

```bash
dexlab scene run --hand allegro --object cube --dry-run
dexlab scene run --config configs/experiments/posed_cube.toml --dry-run
dexlab scene run --config configs/experiments/posed_cube.toml --steps 20
```

在实验的 `[object_overrides]` 中修改 `position_xyz`、`rotation_xyzw` 和 `scale`，
原始物体配置保持不变。示例使用 45 度绕 Z 轴旋转及 1.2 倍尺度。
几何尺寸真正传到程序化 spawner；不是只修改一个未被消费的配置字段。

`HandRegistry` 和 `ObjectRegistry` 从各自配置目录发现名称，`factory="模块:函数"` 选择组件适配器，
`registry_name` 选择 Arena 组件；手掌 body 使用 `palm_frame` 配置。
环境构建器中不再按 Allegro/Shadow 名称分支选择机器人。
旧的 `TabletopEnvironment` Python 名称保留为新类的兼容别名。
配置会选择 Python factory，应该像项目代码一样只使用可信配置。

支持 cube/sphere/cylinder 程序化形状。球要求均匀尺度；圆柱要求 x/y 一致，非支持的椭圆变形会报错。
自定义桌面任务复用 Arena `LiftObjectTask` 的固定位置目标与掉落/超时规则，**没有声称提供 RL 训练奖励**。
KUKA 原始观测依赖官方任务的 `object_pose` 指令，新场景使用自己的关节与物体状态观测解除此耦合。
官方原始场景仍保留其自身观测、任务与控制配置。

### 外部资产

可新建 `configs/objects/my_object.toml`，设置 `kind="usd"` 和已有本地 `usd_path`，
再用 `--object my_object`。资产必须含兼容的单刚体、碰撞和质量属性；YCB饼干盒、芥末瓶和杯子已通过此入口的100步PhysX冒烟测试；其他外部资产仍需逐个验证，见[下载与验证记录](../experiments/ycb_objects_20261111.md)。
程序不会自动将 URDF/Mesh 转成 USD，不会把未注册的 cup 静默替换成 cube。
杯子、URDF、Mesh 转换与复杂碰撞处理留作后续实现。

## 日志与结果

每次运行都新建 `outputs/<UTC时间>-<类型>-<唯一后缀>/`，不会覆盖旧实验：

| 文件 | 内容 |
|---|---|
| `request.json` | 有效配置、seed、运行步数和后端 |
| `simulation.log` | 真实 Isaac Sim/Arena 输出与逐段步数标记 |
| `simulation_result.json` | 成功完成所有步数后生成的证据 |
| `result.json` | 退出码、超时状态和是否通过冒烟验收 |
| `robot_mapping.json` | 自定义场景的实际关节、body、动作分段和 USD 路径 |
| `states.jsonl` | 自定义场景初始及每一步的关节位置/速度、掌姿态、物体姿态和接触测量 |
| `scene_validation.json` | 实际 PhysX 质量/摩擦/惯量、USD 动态刚体/碰撞与尺寸、接触过滤路径 |
| `object_mesh.obj` | 物体局部坐标 O 下、以米为单位且已应用尺度的三角网格 |
| `episode_results.jsonl` | Arena 写出的完整回合结果；未完成回合时可能没有此文件 |

`passed=true` 需要退出码为 0，且完成证据中的步数等于请求步数。
即使 Isaac Sim 意外返回 0，没有完成文件也会判定失败。
`grasp_success` 始终为 `null`，因为此入口没有执行抓取验证。
子进程调用 Arena 已有的 `ISAACLAB_ARENA_FORCE_EXIT_ON_COMPLETE` 清理路径，
先关闭环境、写出结果，再退出 Kit，避免 native shutdown 掩盖异常。

## 抓取数据接口

已提供：

- `grasp_synthesis.candidate.GraspCandidate`：版本化候选数据。
- `grasp_generation.base.GraspGenerator`：候选生成抽象接口。
- `grasp_execution.base.GraspValidator`：物理验证抽象接口。
- `datasets.writer.GraspDatasetWriter`：独占创建 JSONL，不覆盖已有数据。
- `evaluation.grasp.GraspEvaluator`：仅对实际赋值的成功/失败结果统计成功率。

坐标、字段语义和后续物理验证要求见 `docs/data-contract.md`。
DexGraspNet 已完成原源码研究及能量/退火优化核心组件迁移，详见
[源码报告](../paper_reproductions/README.md)。完整可微手/物体几何backend、候选生成与物理验证尚未接通；
GenDexGrasp、DexGraspNet2、Fast-Grasp'D、学习式生成和抓取执行策略尚未实现。
没有引入论文仓库的安装依赖，也不把组件移植称为完整论文复现。
当前状态日志是仿真遥测，**不会自动转换成已验证抓取数据集**。

### 给抓取算法提供的实时接口

在 SimulationApp 启动并创建环境后，可以使用：

```python
from dexterous_lab.integrations.isaaclab.state import ResearchState
from dexterous_lab.objects.mesh import get_object_mesh

state = ResearchState(env, specification["robot"])
joint_state = state.joint_state()
T_W_H = state.palm_pose()
T_W_O = state.object_pose()
contacts = state.contacts()
mesh_O = get_object_mesh(object_configuration)
```

`object_configuration` 是 `ObjectRegistry().get("cube")` 返回的 `ObjectConfig`。
cube 网格精确表示方盒；sphere/cylinder 为明确标记的曲面三角化近似，不伪称解析曲面。
接触来自实际 Isaac Lab ContactSensor，按配置中的指尖过滤，返回世界系法向力与每个过滤刚体的平均接触点。
它不提供完整接触流形；无接触时返回空点集，缺失位置的 NaN 哨兵不会写入 JSON。
关节、手掌、物体和接触力每一步均检查有限性。没有执行抓取、抗扰动或成功判定。

## 测试

```bash
cd /root/gpufree-data/DexterousLab
/root/gpufree-data/IsaacLab-Arena/.venv/bin/python -m pytest -q -p no:cacheprovider
```

这些单元测试覆盖配置、非法选项、尺度换算、数据契约、未知结果统计及运行完成判定。
实际 GPU 环境构建和步进用上面的 CLI 命令单独验收，保留日志。
官方 Arena 回归测试的范围与结果见 `docs/m2-validation.md`，没有把选定文件通过声称为整个官方测试套件通过。

项目目录说明见 `docs/architecture.md`。项目现已配置独立 GitHub 仓库 `ShunZuo-AI/DexterousLab`；仿真继续复用原有共享 Python 环境，发布过程未安装额外 Python 依赖。
