# DexGraspNet：源代码分析与 A–L 回答

根目录：`/root/gpufree-data/research-repos/DexGraspNet`；主分支 commit：
`bd1b13d7248729af117e1d46aaa6266b147a3c7b`。
下文路径相对于此目录。不是根据 README 推测，已逐个追踪下列函数。

## 真实调用链

```text
grasp_generation/scripts/generate_grasps.py:generate()（批量入口）
  ├─ utils.hand_model.HandModel(...shadow_hand_wrist_free.xml...)
  │   ├─ pk.build_chain_from_mjcf()
  │   ├─ contact_points.json / penetration_points.json
  │   └─ 按 link 构建 mesh、capsule 几何、关节上下限与候选索引
  ├─ utils.object_model.ObjectModel.initialize(object_codes)
  │   ├─ coacd/decomposed.obj
  │   └─ 稠密物体表面采样 → FPS → 2000 个物体表面点
  ├─ utils.initializations.initialize_convex_hull(hand, object, args)
  │   └─ HandModel.set_parameters(pose, indices) → Chain.forward_kinematics()
  ├─ utils.energy.cal_energy() → total.sum().backward()
  ├─ utils.optimizer.Annealing.try_step()
  ├─ cal_energy() → new_total.sum().backward()
  ├─ Annealing.accept_step() → 按候选接受/恢复 pose、索引、FK 与梯度
  └─ qpos / qpos_st / scale / 各能量 → object_code.npy

grasp_generation/scripts/validate_grasps.py（独立后处理入口）
  ├─ HandModel(n_surface_points=2000) + ObjectModel(num_samples=0)
  ├─ 近物体表面手采样点 → 法向偏移 → 一次关节梯度调整（除非 --no_force）
  ├─ IsaacValidator.set_asset() / add_env() → 每候选六种整体旋转
  ├─ IsaacValidator.run_sim() → 100 步后的 hand-object 接触存在性
  └─ 六方向全部通过 AND 保存的 E_pen < 0.001 → 输出 qpos 与 scale
```

`grasp_generation/main.py` 是实验入口，调用相同组件，但会清理同名实验 logs/results。
本次只读取，未执行它的清理或生成逻辑。

## A. 原始代码如何表达 Shadow Hand？

`utils/hand_model.py:HandModel.__init__` 读取 MJCF
`grasp_generation/mjcf/shadow_hand_wrist_free.xml`，使用仓库修改版
`thirdparty/pytorch_kinematics/pytorch_kinematics/mjcf.py:build_chain_from_mjcf`。
实际 XML worldbody 下有 **22 个 hinge 关节**：FF/MF/RF 各4，LF5，TH5；根 body 是 `robot0:palm`。
自由手掌的平移和旋转在 XML 外作为优化变量提供，不是当前 Isaac Lab 手的两个 wrist DOF。

`HandModel.set_parameters` 输入 `hand_pose[B,31] = [t(3), rot6d(6), joint(22)]`。
`rot6d.py:robust_compute_rotation_matrix_from_ortho6d` 输出 `R[B,3,3]`；
FK 作用于手局部 link，再通过 `point @ R.T + t` 变换到物体原点所在的合成坐标系。
`contact_points.json` 有 **140 个手选候选点**，`penetration_points.json` 有 **41 个自碰撞关键点**，
均按 link 储存局部坐标。碰撞近似主要是 capsule 和掌部/小指掌骨 chamfer mesh。

## B. 抓取姿态如何初始化？

`utils/initializations.py:initialize_convex_hull`：

1. 取物体凸包，按该物体批次的最大尺度缩放，将凸包顶点沿原点径向外推 0.2 m，再取凸包。
2. 从膨胀凸包稠密采样 `100 × batch_size_each` 点，再用 FPS 取初始手位置参考点。
3. 求到原凸包最近点，构造朝向物体的方向。
4. 采样距离（默认0.2–0.3）、锥角（默认±π/6）、过程角与自转角；组合全局、局部和手的 canonical 旋转。
5. 在手写的22维标准姿态附近用截断正态扰动，标准差为 `jitter_strength × (upper-lower)`。
6. 将旋转前两列串接成 rot6d，将整个位姿设为 `requires_grad=True`。

此初始化含 Shadow 特有的标准姿态与朝向，不能原样套用 Allegro。

## C. 物体接触点如何采样？

必须区分三类点：

| 点集 | 来源 | 用途 |
|---|---|---|
| 手上接触候选 | `mjcf/contact_points.json`，140个局部点 | 每候选默认随机抽4个索引，可重复；优化中重采样 |
| 物体表面点 | `ObjectModel.initialize`：200000稠密采样 → FPS取2000 | 对物体点计算手的穿透 |
| 初始化凸包点 | 膨胀凸包稠密采样 → FPS | 初始化手掌位置和方向 |

不是先在物体上随机选4个点再把它们当实际物理接触。
`ObjectModel.cal_distance(hand.contact_points)` 提供到物体的距离和法向信息；
`with_closest_points=True` 可另取最近物体点，但主能量调用未启用此选项。

## D–E. Energy Function 和梯度

`utils/energy.py:cal_energy` 共五项：force closure 残差、接触距离、物体穿入手、手自碰撞、关节越界。
默认加权 `E_fc + 100 E_dis + 100 E_pen + 10 E_spen + E_joints`。
逐项公式和梯度来源见 [mathematical_formulation.md](mathematical_formulation.md)。

关键实证：TorchSDF 0.1.0 的 `torchsdf/sdf.py:_UnbatchedTriangleDistanceCuda.forward`
将 signs、normals、closest_points 标记为 **non-differentiable**，backward 只返回 query points 梯度，
不返回 face vertices 梯度。因此原 `E_fc` 使用局部常量法向，不能声称其法向也完整反传。
MJCF link FK 与手掌变换本身由 PyTorch 建图；索引替换是离散采样，不反传。

## F. 优化如何更新手掌与关节？

`utils/optimizer.py:Annealing` 不是 Adam：

- `try_step` 对 `[t,rot6d,joint]` 全部连续变量作批次共享二阶矩归一化更新，步长分段衰减。
- 每个接触索引独立以默认0.5概率随机替换，不要求不同 link 或不同索引。
- 新能量求导后，`accept_step` 按 `rand < exp((E_old-E_new)/T)` 决定每个候选是否接受。
- 拒绝时恢复位姿、接触索引、手掌变换、FK/contact点和旧梯度；全局二阶矩与时间步不回滚。

源码中 `mu=0.98` 乘的是**当前批次均方梯度**，历史项乘 `1-mu`，不能凭 RMSProp 名称把系数倒过来。

## G. 穿透、自碰撞与关节限制

- 物体穿透：对2000个物体表面点计算手模型 inside-positive SDF，正值求和；不是精确网格交叠体积。
- 手自碰撞：41个关键点两两距离小于0.02 m的 hinge penalty；不是全网格自碰撞。
  排除几乎零距离的重合点，两两有序求和，不能无故改为只计上三角。
- 关节限制：越上下限的线性罚项；初始化有截断，但优化并非每步硬 clamp。
- Capsule 距离在 `HandModel.cal_distance` 使用 detach 后的最近轴线点；掌部等使用 TorchSDF。
  所有手 link 的 inside-positive 距离取最大值以近似并集，部分连接体被明确跳过。

## H. 怎样筛选有效抓取？

`utils/logger.py:Logger.log` 的阈值 `E_fc<0.3, E_dis<0.005, E_pen<0.001` 只是优化日志中的估计成功率。
批量 `scripts/generate_grasps.py:generate` 实际保存所有结果及能量，不按这三个阈值直接删除候选。

`scripts/validate_grasps.py` 最终使用：六次旋转试验全部有接触，且保存的 `E_pen < penetration_threshold`。
默认先作法向关节微调；模拟使用微调后的关节，但最终保存的 `qpos` 来自原输入记录。
此行为应在适配中显式决定是否保留，不能假定输出已经保存了微调后的状态。
脚本批处理循环使用 `batch_size // val_batch`，尾批未被完整覆盖，迁移不能照搬该调度。

## I. 原论文使用哪种仿真器？

代码为 **Isaac Gym + PhysX**，不是 Isaac Sim / Isaac Lab：
`utils/isaac_validator.py:IsaacValidator`，dt=1/60，substeps=2，手固定基座且不受重力，
手/物体摩擦默认3，物体密度500，位置驱动 stiffness=1000、damping=0。
每候选创建6个旋转试验，固定世界重力 `(0,-9.8,0)`，每个模拟100步，
`run_sim` 最后只检查 hand/object 刚体集合之间是否存在接触。
虽然构造器有 `threshold_dis=0.1`，`run_sim` 并未用它检查物体位移。
不能把此代码描述成六方向外力加载、抬升距离检查或全时段接触保持。

## J. 迁移到 Isaac Lab / Arena

离线可微几何优化和非可微动力学验证分开：数学组件进入 `grasp_generation/dexgraspnet`，
手/object backend 提供可微 FK 和 SDF；生成结果先变成 `GraspCandidate`，
再由 `GraspValidator` 的独立 Isaac Lab 实现检测碰撞/执行/抗扰。
M2 的 `ResearchState` 数据读取不提供 autograd FK，也不等于物理验证器。
坐标、Shadow腱约束和固定基座的具体差异见 [implementation_mapping.md](implementation_mapping.md)。

## K. 能否复用 Allegro？

有真实官方 `allegro` 分支，已 fetch 并以 `git show` 读取：
commit `6a48bc4cc612a471eb9c82183c6f888b08eee8e6`。
它使用 `allegro_hand_description/allegro_hand_description_right.urdf`、16维手关节、
独立 `contact_points.json`、不同 canonical rotation 和初始化均值。
`HandModel` 改为 URDF/box/sphere 几何，`self_penetration` 使用 link pair 距离和忽略项，
不是主分支 Shadow 的41点规则。
能量组合与退火思想可以复用，但当前 M2 Allegro 带7轴机械臂，任意手掌目标还需要 IK/可达性处理。
不能将7个机械臂角塞进原16维手关节向量。

## L. 原始资产流程与授权

`asset_process/README.md` 与实际脚本：
`extract.py` → `manifold.py`/ManifoldPlus → `normalize.py` → `decompose_list.py`/`decompose.py:export_urdf`。
normalization 使用包围盒中心和最大顶点半径×1.03归一化，并筛选 watertight、volume>0.05；
CoACD 输出 `decomposed.obj`、convex piece OBJ 和 `coacd.urdf`。
必须保存原网格到归一化坐标的变换以及后续0.06–0.15尺度，不能给已经是米制的 M2 cube 再盲目缩小。

README 声明工作和数据集为 **CC BY-NC 4.0**。OpenAI Shadow 资产目录另有 Apache-2.0/ShadowRobot 来源说明；
Allegro 分支 manifest 标注 BSD；ShapeNetCore/Sem、MuJoCo scanned objects、DDG 的原始资产各有独立来源条件。
不能从外层仓库许可推断所有模型、数据、权重都可任意再分发；本次未导入或重新发布这些资源到 src。
