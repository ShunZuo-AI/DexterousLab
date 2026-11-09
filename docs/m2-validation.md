# M2 模块化桌面环境验收

日期：2026-11-06，北京时间约 14:13–14:20。输出目录名采用 UTC。

## 交付结果

M2 的三个目标组合均完成实际 GPU 运行。每个场景一个环境、100 个零动作环境步、
400 个 PhysX 物理子步；初始状态和每一步都检查关节、手掌、物体、接触力的有限性。
**这不是抓取策略或抓取成功验证，所有 `grasp_success` / `success` 保持 `null`。**

| 组合 | 结果 | 物理关节 | 动作维度 | 运行目录（相对项目根） |
|---|---|---:|---:|---|
| Allegro + Cube | 通过 100 步 | 23（含机械臂 7） | 23 | `outputs/m2/20261106T061834Z-scene-6ee14037` |
| Allegro + Cylinder | 通过 100 步 | 23（含机械臂 7） | 23 | `outputs/m2/20261106T061717Z-scene-8171b7f7` |
| Shadow + Cube | 通过 100 步 | 24 | 20（16 直接关节 + 4 腱） | `outputs/m2/20261106T061736Z-scene-aa2574d9` |

Allegro 明确使用官方 **KUKA iiwa7 + Allegro** 安装结构；未实现独立无臂 Allegro。
Shadow 使用官方 `SHADOW_HAND_PHYSX_CFG` 的固定基座右手，不带 KUKA。
Shadow 的层级 USD、24 个实际关节、五个指尖、四个腱动作均成功加载和核对；没有资产阻塞。
运行时的 `robot_mapping.json` 记录实际资产 URL、实际关节顺序、动作分段顺序和 body 名。

## 实际命令

```bash
cd /root/gpufree-data/DexterousLab
export PATH="$PWD/scripts:$PATH"

dexlab scene run --hand allegro --object cube --physics physx --output-dir outputs/m2 --timeout 240
dexlab scene run --hand allegro --object cylinder --physics physx --output-dir outputs/m2 --timeout 240
dexlab scene run --hand shadow --object cube --physics physx --output-dir outputs/m2 --timeout 240
```

场景默认步数已改为 100，无窗口、无相机。旧 `--backend` 参数和原来的
`TabletopEnvironment` 类名兼容保留，显式 `--steps 20` 仍可使用。

## 验证了什么

- 机器人、物体的实际 USD prim 存在，articulation 与 rigid object 都初始化完成。
- 物体是启用的动态刚体，不是静态/运动学替代物，存在启用的碰撞形状。
- 从实际 PhysX `root_view` 读取质量、材料和惯量；不是只回读 TOML。
  三个对象实际质量均为 `0.10000000149011612 kg`，静/动摩擦均约 `0.6999999881`，恢复系数为 0。
- 检查惯量有限且主对角线为正；USD 物体局部包围盒与配置尺寸相符。
  cube 为 0.05×0.05×0.05 m；cylinder 半径 0.025 m、高度 0.08 m。
- 真实动作坐标与配置的关节/腱集合相符，指尖 body 确实存在，关节张量形状与物理关节数一致。
- 初始状态加上 100 次状态检查，共 101 条有效状态记录；包含关节速度、掌姿态、物体姿态。
- 实际 ContactSensor 配置为物体对各指尖的独立过滤，Allegro 四个过滤体、Shadow 五个。
- cube 导出 8 顶点、12 三角形 OBJ；cylinder 导出 256 三角形 OBJ。
  所有导出网格经重新读取检查为闭合网格，以米为单位、在物体局部坐标 O 下，已应用尺度。

`docs/m2/artifact-audit.json` 保存对三个运行目录、101 条状态、物理属性和导出网格的独立读取检查结果。
三个零动作测试均没有检测到非零指尖接触，因此日志记录的是测得的零力和空接触点集。
没有声称验证了非零接触位置的物理精度、完整接触流形或抓取稳定性。

每个运行目录提供：

| 文件 | 作用 |
|---|---|
| `request.json` | 完整有效配置、seed、后端、步数 |
| `simulation.log` | 实际 Isaac Sim/Arena 日志与步进完成标记 |
| `simulation_result.json` | 步数、物理子步、运行环境与验证结果 |
| `result.json` | 子进程退出码与验收状态 |
| `robot_mapping.json` | 实际动作分段、关节、指尖和 USD 来源 |
| `scene_validation.json` | 实测质量、摩擦、惯量、碰撞、尺寸、接触过滤路径及网格信息 |
| `states.jsonl` | 初始及每一步状态，共 101 条 |
| `object_mesh.obj` | 算法可读取的物体局部网格 |

## 注册表与代码位置

环境构建类：`src/dexterous_lab/scenes/tabletop.py` 中的 `DexterousLabTabletopEnvironment`。
它复用 Arena `ArenaEnvironmentFactory`、`Scene`、`AssetRegistry`、embodiment、`LiftObjectTask` 和 `ArenaEnvBuilder`。

新增文件：

- `src/dexterous_lab/registry.py`：配置发现、严格名称查找和惰性 factory 导入。
- `src/dexterous_lab/robots/registry.py`：`HandRegistry`。
- `src/dexterous_lab/objects/registry.py`：`ObjectRegistry`。
- `src/dexterous_lab/robots/allegro.py`：官方组合手适配器。
- `src/dexterous_lab/objects/factories.py`：物体构建适配器。
- `src/dexterous_lab/objects/mesh.py`：`get_object_mesh()`。
- `src/dexterous_lab/integrations/isaaclab/state.py`：`ResearchState` 实时数据接口。
- `src/dexterous_lab/integrations/isaaclab/contact_paths.py`：从官方 USD 实际层级解析逐个指尖路径。
- `src/dexterous_lab/integrations/isaaclab/validation.py`：运行时物理与场景检查。
- `src/dexterous_lab/evaluation/smoke.py`：实测物理属性的数值校验。
- `tests/test_registries.py`、`test_m2_physics.py`、`test_research_state.py`：新增测试。

更新文件：

- `config.py`：注册表驱动加载、factory 和掌 frame 参数，移除手型白名单硬编码。
- `cli.py`：`--physics`、兼容 `--backend`，自定义场景默认 100 步。
- `runtime.py`：相对输出目录转换成绝对路径，修复子进程更换 cwd 后找不到 request 的问题。
- `scenes/tabletop.py`：通过两个注册表创建组件，注册独立对象接触传感器。
- `robots/shadow.py`：Shadow factory 和官方坐标配置校验。
- `assets/primitives.py`：启用真实物体接触报告。
- `integrations/arena/worker.py`：逐步验证、逐步状态记录、物理属性报告和网格导出。
- `configs/robots/{allegro,shadow}.toml`、`configs/objects/{cube,cylinder,sphere}.toml`：组件 factory、掌 frame、Arena 注册键。
- `tests/test_runtime.py`：相对输出路径回归测试。
- `README.md`、`docs/architecture.md`、`docs/data-contract.md` 和本报告。

后续增加手时可增加配置和自己的 factory，环境构建类不需要增加按手名分支。
未知配置名不会退回 Allegro 或 Cube。未知物理后端明确拒绝。

## 测试与 M0/M1 回归

原有 38 项测试先通过，新增后共 **68 项单元测试全部通过（2.23 s）**。

```bash
cd /root/gpufree-data/DexterousLab
/root/gpufree-data/IsaacLab-Arena/.venv/bin/python -m pytest \
  -q -p no:cacheprovider --junitxml=docs/m2/unit-tests.xml
```

覆盖注册表扩展、未知名称、配置不串改、CLI 别名、几何网格、错误物理值拒绝、
接触点 NaN 哨兵处理、错误力数据拒绝、缺失手掌拒绝、相对输出目录和原有数据接口。

官方场景使用更新后的统一入口重新验证：

```bash
dexlab arena run cube_goal_pose --steps 20 --physics physx --output-dir outputs/m2 --timeout 240
dexlab arena run dexsuite_lift --steps 100 --physics physx --output-dir outputs/m2 --timeout 240
```

两个均通过，目录分别为：

- `outputs/m2/20261106T061853Z-arena-e72fbbb3`：cube_goal_pose，20 步，7 维动作。
- `outputs/m2/20261106T061911Z-arena-4ac264e2`：dexsuite_lift，100 步，23 维动作。

命令输出另保存在 `docs/m2/official-cube-command.log`、`official-dexsuite-command.log`。

再次使用用户指定的同一 native `.venv` 执行官方
`isaaclab_arena/tests/test_arena_env_builder_cfg.py`：**14 passed，35 warnings，10.04 s**。
日志和 JUnit 为 `docs/m2/arena-regression.log`、`arena-regression.xml`。
没有运行完整官方三阶段测试套件，不将这一文件通过解释为所有官方测试通过。
doctor 结果在 `docs/m2/doctor.json`，L40S、CUDA 和矩阵求逆均正常。

## 调试中发现并修复的问题

失败记录全部保留，不覆盖旧日志：

1. `20261106T061310Z-scene-e5b1079d`：原运行器给子进程传相对 request 路径，子进程 cwd 改变后找不到文件；改为绝对路径并加入回归测试。
2. `20261106T061329Z-scene-c5bb292f`：PhysX 不接受一个 filter pattern 匹配多个 robot body；改为逐个解析真实 USD 指尖路径。
3. `20261106T061540Z-scene-36c3731b`：Arena `open_stage` 是 context manager；修正为 `with open_stage(...)`，随后 Allegro 与 Shadow 都实测通过。

最初的 Allegro+Cube 通过目录 `20261106T061618Z-scene-c7f579fd` 也保留。
之后加入更严格的接触有限性检查，再次完成最终 Allegro+Cube 的 100 步验收。

## 边界

只有环境与研究数据接口达到本次 M2 验收；尚未集成 DexGraspNet、抓取生成、
执行闭环、完整接触流形、抗扰稳定性测试或抓取成功率评估。
本轮没有声称完成自定义 Newton、外部 USD、URDF/Mesh 转换或独立无臂 Allegro 的验收。
球体原有功能仍保留，并有网格与配置单元测试；本轮 GPU 验收集中在要求的三个组合。

没有新增依赖、安装 Isaac Sim、创建 Python 环境、修改上游源码、提交或推送 Git。
Arena 工作树在本轮前后保持同一组原有用户修改，未覆盖这些修改。
