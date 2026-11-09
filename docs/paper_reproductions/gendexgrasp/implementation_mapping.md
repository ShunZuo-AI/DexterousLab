# GenDexGrasp 与统一接口

| 原接口 | 输入/输出 | 对应DexterousLab | 状态与差异 |
|---|---|---|---|
| `PointNetCVAE.inference` | xyz[B,N,3], z[B,128] → contact[B,N] | 后续学习式 `GraspGenerator` 的contact-map阶段 | 尚未迁移；需要训练配置、权重许可和归一化匹配 |
| `CMapDataset` | object点云+法向+contact_gt | 后续dataset输入schema | 原始contact标量与我们的物理contact_points分开储存 |
| `HandModel.update_kinematics` | q[B,9+J] → FK与表面点 | 可微hand backend | 必须适配独立手几何/URDF，不是M2实时状态张量的autograd |
| `CMapAdam.compute_energy_*` | contact_map_goal[N,7], q → 拟合/穿透能量 | 独立GenDexGrasp能量组件 | 不借用DexGraspNet名字；关节罚项返回值差异应记录 |
| `AdamGrasp.run_adam` | 多particle → q轨迹、energy | `GraspGenerator.generate`内部 | 实现算法后才可构造GraspCandidate；现在只分析 |
| `is_obj_stable`与六方向force任务 | 初末位置、外力 → 稳定bool | 独立IsaacLab `GraspValidator`协议 | dt、外力、摩擦、保持时长和位移阈值必须版本化 |
| `.pt`轨迹与选优结果 | q_tra、energy、object_name | 候选与运行元数据 | pose转xyzw，具名关节，不把标量接触图当世界坐标接触点 |

当前统一候选格式不包含完整网络输入、target cmap或整条优化轨迹，
这些应作为独立实验artifact保存并通过ID关联，而不是塞进success或contact_points字段。
本仓库没有明确代码再分发许可，暂不直接复制源码；算法复述和接口研究不算完整实现。
