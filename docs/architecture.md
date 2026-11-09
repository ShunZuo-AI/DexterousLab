# 架构与扩展位置

| 目录 | 职责 |
|---|---|
| `configs/robots` | 每种手独立的坐标、关节、电机、腱和指尖映射 |
| `configs/objects` | 物体几何、尺度、质量、摩擦和位姿 |
| `configs/scenes` | 桌面布局和仿真时间设置 |
| `configs/tasks` | 任务目标、容差、超时 |
| `configs/experiments` | 各组件选择和物体参数覆盖 |
| `src/dexterous_lab/assets` | 通过 Arena `register_asset` 注册的程序化资产 |
| `robots` | Shadow 独立 embodiment；Allegro 复用官方 KUKA+Allegro |
| `robots/registry.py` | HandRegistry：配置发现、手型标识校验和 factory 分发 |
| `objects/registry.py` | ObjectRegistry：物体发现、参数覆盖和 factory 分发 |
| `objects` | 与仿真导入无关的物体几何计算 |
| `scenes` | Arena factory、Scene 和组件组装 |
| `tasks` | 任务适配，当前复用固定目标 LiftObjectTask |
| `integrations/arena` | 官方场景接入和隔离的 headless worker |
| `integrations/isaaclab` | 自定义状态观测，不依赖官方 RL 任务指令 |
| `integrations/isaaclab/state.py` | 实时关节、掌姿态、物体姿态和指尖接触数据 |
| `integrations/isaaclab/validation.py` | 实际后端物理属性、动态刚体、碰撞和几何检查 |
| `objects/mesh.py` | 抓取算法使用的物体局部坐标网格 |
| `grasp_synthesis` | 候选数据结构 |
| `grasp_generation` | 生成器抽象接口，待接算法 |
| `grasp_execution` | 物理验证器抽象接口，待实现执行与稳定性测试 |
| `datasets` | 无覆盖的数据集写入 |
| `evaluation` | 候选结果统计 |
| `scripts` | 使用共享 Python 的启动脚本 |
| `tests` | 不启动 Isaac Sim 的单元测试 |
| `outputs` | 真实运行日志和测量结果，Git 默认忽略 |

## 扩展原则

1. 先增加独立配置，再实现特定组件；未知类型立即失败。
2. Simulator 模块只在 SimulationApp 启动后导入。CLI、数据接口、配置测试不导入 USD。
3. 复用 Arena 的资产注册、环境注册、Scene、EmbodimentBase、任务、录制器和 Environment Builder。
4. 共享环境不安装新依赖；第三方论文算法先抽取必要逻辑，兼容性确认后再决定依赖。
5. 手的电机坐标与物理关节分开；动作向量的真实顺序以运行时 action IO descriptor 为准。
6. 所有候选在验证前的碰撞、稳定性与成功字段保持未知。

M2 的 factory 类为 `DexterousLabTabletopEnvironment`，`TabletopEnvironment` 保留为兼容别名。
100 个环境步对应当前配置的 400 个 PhysX 子步；验证报告明确区分两者。

## 已确认的本地 API

- `ArenaEnvironmentFactory.build(cfg)` 返回 `IsaacLabArenaEnvironment`，不是 Gym 环境。
- `Scene(assets=[...])` 组织资产；`AssetRegistry.get_asset_by_name(name)` 返回组件类。
- `Object(..., spawner_cfg=..., object_type=ObjectType.RIGID)` 支持程序化物体。
- `ArenaEnvBuilder(description, ArenaEnvBuilderCfg(...)).make_registered()` 创建 Gym 包装环境。
- 使用 `env.unwrapped` 获取 `scene`、`device`、`step_dt`、`action_manager` 等 Isaac Lab 属性。
- `SimulationAppContext` 使用官方解析器的 Namespace；`visualizer=None` 表示无窗口。
- `LiftObjectTask` 按固定目标位置判定任务完成；此检查不验证抓取接触和抗扰稳定性。
