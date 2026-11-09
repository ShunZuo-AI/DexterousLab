# 统一接口映射与适配差异

| 原模块 | 原输入 → 输出 | DexterousLab位置/接口 | 迁移要求 |
|---|---|---|---|
| `HandModel.set_parameters` | `[B,3+6+J]`、`[B,C]`索引 → FK/contact_points | 离线可微hand backend | 保留优化图，不能用IsaacLab非可微状态读取代替 |
| `ObjectModel.initialize/cal_distance` | 归一化mesh/scale、query `[B,C,3]` → inside-positive距离/法向 | `objects.mesh.get_object_mesh` + distance backend | 明确米制尺度；法向原行为detach；保存法向符号约定 |
| `initialize_convex_hull` | mesh、手型canonical姿态、参数 → q,z | `GraspGenerator`内部初始化 | 不是完整生成器；Shadow和Allegro使用不同均值/朝向 |
| `cal_energy` | contact、SDF、self点、joint limits → 五项与加权总能量 | `grasp_generation/dexgraspnet/energy.py` | 以组件级算法移植标注；保持query梯度、n.detach、inside-positive与双向点对求和 |
| `Annealing` | q梯度、旧/新能量、contact索引 → 接受掩码与新状态 | `grasp_generation/dexgraspnet/optimizer.py` | 保持批次共享v、原mu语义与时序；明确回滚状态 |
| 生成脚本中的优化循环 | 已初始化hand/object模型 → 优化后q,z与轨迹 | `grasp_generation/dexgraspnet/optimization.py:optimize_models` | 已迁移核心循环；不提供假FK/SDF或随机采样替代品 |
| qpos保存 | Euler/WRJT、22关节、scale → npy | `GraspCandidate` / `GraspDatasetWriter` | 写为xyzw、米、具名关节、T_W_H和T_W_O；能量不是success |
| `IsaacValidator` | 六个整体旋转/固定手 → 最后接触bool | 后续IsaacLab `GraspValidator`实现 | 必须另写动力学adapter，不把M2零动作入口改名为validator |
| 结果筛选 | six-contact AND E_pen阈值 → qpos/scale | `GraspEvaluator`和验证元数据 | 记录协议版本、摩擦、重力、时长；未知为None，不混入分母 |

## 坐标必须先做显式变换

原合成中物体在原点，输出手掌相对物体的位姿 `T_O_H`。
M2物体实际在世界中的 `T_W_O` 由 `ResearchState.object_pose()` 提供，因此：

`T_W_H = T_W_O @ T_O_H`。

如果源手掌frame与目标USD掌frame有固定偏移，必须另给已验证的 `T_Hsrc_Hdst`，
使用 `T_W_Hdst = T_W_O @ T_O_Hsrc @ T_Hsrc_Hdst`，不能默认为identity后宣称校准完成。
源优化rotation6d是旋转前两列，保存Euler是transforms3d默认`sxyz`；我们的四元数是xyzw。
当前本机IsaacLab `utils/math.py` 的matrix_from_quat也明确使用xyzw，不能沿用旧版本的wxyz记忆。

## Shadow并非“去掉robot0:前缀”即可

源模型22个手指关节，当前USD有24个物理关节（多2个wrist）、16个直接电机与4个固定腱坐标。
按序号加1的名称对应（例如FFJ3→rh_FFJ4、THJ0→rh_THJ1）只能作为待核验的语义对应，
不能证明轴向、正负号、原点和关节限位都相同。
四个非拇指的J2/J1在当前手里经腱耦合，J0=J1+J2；源优化允许独立设置这两个关节。
因此把两角相加虽然能给出腱目标，却丢失独立角信息，不能保证几何姿态可达。
实际执行前必须校验coupling可实现性，并通过FK/关键点对照求出固定frame转换。

## Allegro + KUKA

官方allegro分支确认可优化16维手角，但当前env.action_dim=23包含7轴机械臂。
输出候选时保持16维hand关节与手掌目标分开；执行器根据基座和工具安装变换求IK，再组合23维控制。
不可通过改变KUKA根位姿、把物体瞬移到掌上或静默固定机械臂角来伪造任意掌位姿可达。

## 有意保留的实现边界

本轮可先迁移可对照测试的五项能量聚合与退火提案/接受逻辑。
未装TorchSDF/modified FK/PyTorch3D，不能把缺失SDF或FK替成常数零并称为完整DexGraspNet。
若只对球体/方盒解析SDF或自写采样验证数学组件，标为测试夹具或简化backend，不输出论文复现成功率。
GenDexGrasp和DexGraspNet2的映射另见各目录，不能把三个方法混成同一算法名。

已提供 `grasp_execution/dexgraspnet_adapter.py:source_qpos_to_candidate`：
强制调用方提供完整joint_map、额外关节值、目标限位和 `T_Hsource_Htarget`，
将原extrinsic xyz Euler和物体局部手姿态转换到世界系xyzw候选。
它只是显式数据/坐标适配，不会求解KUKA IK、校准掌frame或确认Shadow腱约束。
