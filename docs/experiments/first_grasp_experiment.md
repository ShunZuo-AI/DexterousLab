# 第一次多指桌面抓取实验：项目审计与执行报告

日期：2026-11-06（Asia/Shanghai）。项目 `/root/gpufree-data/DexterousLab`；唯一Python `/root/gpufree-data/IsaacLab-Arena/.venv/bin/python`；GPU NVIDIA L40S。目标是实际完成一次有动作的实验，不预设抓取成功。

## 1. 审计范围与实际实现

阅读了现有第一方代码、配置、示例、测试和研究文档，119份初始文件的内容哈希/实际符号清单保存在 `first_grasp_audit_inventory.json`。资产二进制不靠目录名判断，读取现有清单、原始哈希及真实加载结果；`research-repos/` 是参考资料，不当作已经集成的功能。工作区初始第一方文件均未跟踪，本次不提交、不清除或覆盖实验数据。

| 检查项 | 真实代码位置与结论 |
|---|---|
| 资产管理 | `assets/catalog.py`、`manager.py`、`registry.py` 可用。注册/查询/来源/哈希/有限提取与转换已实现；不是任意资产一键接入。官方引用留档文件及Cube原始包完整性检查通过，见 `first_grasp_asset_integrity.json`，这不等于官方USD整棵依赖树哈希审核；实际组合Allegro和Shadow根USD另外记录准确路径、存在性与SHA256 |
| Allegro加载 | `robots/allegro.py`调用Arena `kuka_allegro`；**桌面Allegro是KUKA+Allegro，不是独立手**。实际23关节、23增量位置动作；独立手资产预览是另一条路径 |
| Shadow加载 | `robots/shadow.py`复用 `SHADOW_HAND_PHYSX_CFG`，24物理关节、16直接关节+4腱动作，独立手，无机械臂 |
| Object Registry | `objects/registry.py`通过配置factory构建primitive或既有本地USD，Cube/Sphere/Cylinder可用；YCB/DexGraspNet/Objaverse/ManiSkill集合只是来源记录，没有可用批量物体库 |
| Scene Builder | `scenes/builder.py`/`tabletop.py`调用Arena Scene/Environment Factory/Builder，可构建桌面、物体、地面、光照和机器人；新手型仍需要控制适配 |
| Task | `tasks/lift.py`封装官方LiftObjectTask，具有目标高度/位置及进度和终止；**本身不提供接近、闭合和抬升控制器** |
| 抓取生成 | `GraspGenerator`是抽象接口。DexGraspNet energy/annealing/optimization存在数学实现和测试，但需要外部已初始化FK/SDF手物模型；没有完整可直接执行的端到端候选生成器。此次用显式人工设定的手掌目标和闭合角，不宣称论文生成 |
| 物理验证 | `GraspValidator`仍为抽象接口；`validate_loaded_scene`能核验加载与物理参数，既有 `evaluation.worker`仅有Shadow姿态保持和有限lift/contact判定。没有通用全碰撞/扰动抓取验证器；本次只做明确范围的单次物理实验 |
| 数据保存 | `ResearchState`、`DatasetCollector`、`GraspDatasetWriter`能保存实际状态/动作/命名关节/接触数据，JSON/JSONL/纯数值NPZ。候选持久化已可用，但不代表候选有效 |
| Isaac集成 | `runtime.py`共享解释器+Torch CUDA库路径，ArenaBuilder真创建PhysX环境；本次两种机器人均完成真实动作步进，不能只用import或历史zero_action作证 |

初始项目测试 **109 passed / 3.51 s**，见 `first_grasp_baseline_tests.log`。

## 2. 最小修复与实验入口

未重写架构、未新增平行注册系统。只新增一个实验脚本和一份配置：

- `scripts/first_grasp_experiment.py`：复用SceneBuilder/ArenaEnvBuilder/ResearchState/DatasetCollector，分别适配实际Allegro增量动作与Shadow关节/腱动作，执行阶段序列并记录真实结果。
- `configs/experiments/first_grasp.toml`：手掌目标、每手开闭角、时序、限速、补偿和成功标准。
- `tests/test_first_grasp_experiment.py`：防止把完成步进或短暂抬升计为成功，核验控制配置差异。

实验过程中发现并修正：

1. 机械臂开启重力但增量目标反馈不足，会明显下垂；本次机器人启用重力补偿（禁用机器人刚体重力），Cube重力和质量保持正常。不是施加物体附着力。
2. PhysX固定基座Jacobian不含根body，使用palm body index减1；按真实官方tutorial与data API修正，不臆造雅可比顺序。
3. 绕腕过大和基座高度不合适会导致限位/桌面干涉。按实测手掌局部轴保留Allegro约135度yaw，KUKA基座设在z=0.255m的安装高度；没有生成物理支架模型，基座本来固定。
4. 远程资产状态检查有一次超时，实验通过公开 `ISAACSIM_ASSET_ROOT` 设置指向已下载官方缓存。没有修改缓存模型字节或上游下载代码。
5. 为避免任务在达到目标时自动reset抹掉保持阶段，本实验关闭success自动终止，保留任务进度结构，使用下述明确结果标准；掉落/超时仍报错并保留轨迹。

早期调试/失败目录及各次request全部保留，不将后续调参结果覆盖为“首次成功”。最终启动还保存脚本副本及SHA256，配置快照在request中。

## 3. 实际命令

所有命令在项目根运行，没有安装依赖：

```bash
cd /root/gpufree-data/DexterousLab

# 加载探测（仅几何检查，不是抓取）
/root/gpufree-data/IsaacLab-Arena/.venv/bin/python scripts/first_grasp_experiment.py --hand allegro --probe
/root/gpufree-data/IsaacLab-Arena/.venv/bin/python scripts/first_grasp_experiment.py --hand shadow --probe

# 完整实验，每次新建唯一输出目录；--render在云桌面渲染并保存视口PNG
/root/gpufree-data/IsaacLab-Arena/.venv/bin/python scripts/first_grasp_experiment.py --hand allegro --render
/root/gpufree-data/IsaacLab-Arena/.venv/bin/python scripts/first_grasp_experiment.py --hand shadow --render

# 不需要图形界面时去掉--render，仍执行相同物理动作
/root/gpufree-data/IsaacLab-Arena/.venv/bin/python -m pytest -q
```

日志入口：`docs/experiments/allegro_final_command.log`、`shadow_final_command.log`。真实子进程命令及退出码在每次输出的 `launch_result.json`。脚本内部自动设置PYTHONPATH和LD_LIBRARY_PATH，不另建环境。默认配置限于单环境与一次候选，超时有界。

## 4. 统一配置与对照边界

- 目标物体：Cube，边长0.05m、质量0.1kg、摩擦0.7，初始世界位置 `[-0.55,0,0.285]`，xyzw单位四元数。
- 桌面：中心 `[-0.55,0,0.235]`，尺寸 `[0.8,1.0,0.04]`，顶面z=0.255m；Cube最初有约5mm下落至桌面。
- 物理：Isaac Lab PhysX，dt=1/120s、decimation4，环境步长1/30s，种子42。
- 阶段：settle15、approach150、descend90、close90、lift90、hold45，共 **480环境步/1920物理步，16秒仿真时间**。
- 控制目标：先到Cube上方12cm，再下降；按各手命名关节缓慢闭合；最后手掌上升10cm并保持。
- 判成功：相对初始Cube中心抬升至少3cm，至少两个指尖法向接触力分别超过0.01N，物体线速度≤0.1m/s，并在最后连续至少20环境步满足；单次尝试不报告具有统计意义的成功率。
- Allegro：真实KUKA7关节DLS IK，16手关节；官方驱动/摩擦不重新标定，增量命令经真实ActionManager执行。
- Shadow：24关节，16直接+4腱目标；**没有机械臂，基座沿明确规定的运动路径移动，属于运动学支撑台，不是自由漂浮/实机可执行的手腕轨迹**。其手掌路径跟踪更理想，因此不是同硬件的公平性能排名。
- 物体：从reset以后不写物体位姿/速度、不建立fixed joint/吸附/抓取附着，物体运动来自真实接触与重力。

手掌目标因手的局部坐标与尺寸不同而分开设置，不能以相同世界四元数强行比较两手。

## 5. 实际资产路径

共用缓存根：
`/root/gpufree-data/DexterousLab/assets/cache/https/omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/6.2/`

- Allegro组合：`Isaac/IsaacLab/Robots/KukaAllegro/kuka.usd`。
- Shadow：`Isaac/Robots_Multiphysics/ShadowRobot/ShadowHandMultiPhysics_v0/right_hand/right_hand.usda`，PhysX/simplified变体。
- Cube、Table：本项目 `assets/primitives.py` 的动态Cuboid和运动学桌面，仿真时生成；Cube离线网格位于 `assets/objects/custom/cube/raw/mesh.obj`，仿真碰撞实际来自CuboidCfg。
- 地面：同一缓存根下 `Isaac/IsaacLab/Environments/Grid/default_ground_plane_checker_v1/default_ground_plane.usda`；光照为Arena现有灯光。

每次 `robot_mapping.json` 中是加载后的准确路径，`scene_validation.json` 保存实际Cube质量、材料、惯性、碰撞路径和尺寸。

## 6. 结果、原因与证据

两只手均真实完成 **480环境步、1920物理步**，关节/物体/接触状态保持有限。最终单次结果如下，**两次都没有成功抓起并保持Cube**：

| 指标 | Allegro + KUKA | Shadow（运动学支撑台） |
|---|---:|---:|
| 物理关节 / 动作 | 23 / 23 | 24 / 20 |
| 实际加载与有限步物理 | 通过 | 通过 |
| 关节控制 | 有实际响应，手掌存在动态跟踪误差 | 关节/腱有实际响应，存在稳态误差 |
| 最后闭合直接关节的最大目标误差 | 0.08080 rad | 0.12658 rad |
| 最后腱坐标和的最大目标误差 | 不适用 | 0.03697 rad |
| 最多同时有力的指尖过滤对 | 3 | 3 |
| 峰值指尖法向力 | 28.50999 N | 0.51537 N |
| 相对初始化中心的最大上升 | 2.074 mm | 0 mm（最大值以0为下界） |
| 最后连续满足抬升保持的步数 | 0 | 0 |
| 是否达到3cm抬升+20步多指保持 | 否 | 否 |
| 指尖—物体最大测得穿入 | 0.1160 mm | 0.01537 mm |
| Cube底面低于桌面顶面的最大量 | 0.00242 mm | 0.00580 mm |

两轮失败类型均为 `no_lift`，不是模型加载失败。Allegro在close末有两指接触，但开始lift后接触消失；Shadow在close末有三指接触，同样在lift阶段丢失。**实际观察是未形成可持续持物的接触关系**。开环闭合角、拇指对指位置与运动学跟踪误差是下一步待检验的原因，不能仅凭峰值接触力声称已实现有效夹持。

Allegro在approach末手掌位置误差约30.6mm、descend末约64.2mm，close后约6.0mm，hold末约1.1mm；这说明闭合开始时尚未完全到位，应增加接近完成门槛和接触反馈。Shadow路径是规定的基座运动，不能把其更理想的目标跟踪解释为控制器优于KUKA。Shadow的J1/J2对由腱耦合，实际控制的是和坐标，不把两个关节分别到达0.8rad作为已实现的控制能力。

最终运行目录：

- Allegro：`/root/gpufree-data/DexterousLab/outputs/20261106T122416Z-first-grasp-allegro-b8586ceb/`
- Shadow：`/root/gpufree-data/DexterousLab/outputs/20261106T122645Z-first-grasp-shadow-863d5980/`

逐步曲线见 [first_grasp_metrics.png](first_grasp_metrics.png)，机器可读结果及全部调试轮次见 [first_grasp_results.json](first_grasp_results.json)。两个最终轨迹各481帧，已用 `allow_pickle=False` 重读，关节、关节速度、手掌/物体位姿、动作和接触数组均通过有限值检查。

可视化均来自实际仿真视口：

- [Allegro闭合截图](../../outputs/20261106T122416Z-first-grasp-allegro-b8586ceb/close.png)、[抬升后截图](../../outputs/20261106T122416Z-first-grasp-allegro-b8586ceb/lift.png)、[六阶段概览GIF](../../outputs/20261106T122416Z-first-grasp-allegro-b8586ceb/phase_storyboard.gif)。
- [Shadow闭合截图](../../outputs/20261106T122645Z-first-grasp-shadow-863d5980/close.png)、[抬升后截图](../../outputs/20261106T122645Z-first-grasp-shadow-863d5980/lift.png)、[六阶段概览GIF](../../outputs/20261106T122645Z-first-grasp-shadow-863d5980/phase_storyboard.gif)。

GIF是六张实际阶段截图拼接的概览，不是连续实时视频；本轮未录制连续MP4。

最终项目测试 **111 passed / 3.25 s**，见 [first_grasp_final_tests.log](first_grasp_final_tests.log)；未运行完整上游Arena三阶段pytest。原有Arena的两份环境文件及uv.lock用户修改保持原样，Isaac Lab工作区未改变。本轮自有src架构文件未修改，只增加实验脚本、配置、两项必要结果判定测试及报告/分析产物。

数据文件：每次唯一运行目录含 `request.json`、`script_snapshot.py`（最终版本）、`simulation.log`、`result.json`、`launch_result.json`、`robot_mapping.json`、`geometry_probe.json`、`scene_validation.json`、`contact_api.json`、`phase_metrics.json`；`trajectory/` 保存metadata、逐步JSONL和不含pickle的NPZ。渲染运行另有六阶段PNG，GIF若生成则仅为阶段截图概览，不是连续实时视频。

穿模测量范围：直接读取PhysX detailed normal contact的separation buffer，依据count/start提取实际指尖—物体接触，记录负距离；另外用Cube实际姿态计算底面到桌面的垂直间隙。**没有全面检测所有手连杆—物体、机械臂—桌面、自碰撞或连续时间穿透**；没有接触的过滤对也不能由此证明无穿模。

## 7. 当前缺失与下一步

1. 抓取生成器尚未与当前手的运动学、碰撞模型和执行器连成闭环。当前预抓取与闭合角是人工基线，不能称DexGraspNet完整复现。
2. Allegro需要更可靠的可达性检查、手掌姿态/指尖包络标定及接近路径；在接触前检查IK误差，并在误差超限时判为失败或重新规划，而不是盲目闭合。
3. 当前手指闭合是开环角度目标，未依据实际接触调节拇指对指位置或夹持力；大接触力不等于能稳定持物。
4. Shadow基座路径是仿真支撑台控制，不是机械臂控制；后续若做手型性能比较，应提供相同的受限手腕运动装置或各自真实机械臂。
5. 完整碰撞穿透、关节驱动误差/腱约束、外力扰动保持、掉落与失败分类仍需加强。此次有范围的接触深度不能替代完整GraspValidator。
6. 对单个Cube的单次尝试不能说明泛化能力或成功率；先得到可复现的有效抓取，再固定参数做多seed与多物体统计。
7. 本轮不扩充物体库、不安装策略训练依赖、不添加新架构；所有改动为实际实验所需。
