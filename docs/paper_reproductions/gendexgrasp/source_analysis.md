# GenDexGrasp：真实调用链

根目录 `/root/gpufree-data/research-repos/GenDexGrasp`；commit
`29fe7efc558b8cc3ce2d8e67c9c22b014adc21c7`。

## 训练、推理、手姿态与验证

```text
train_cvae.py
  → utils_data/CMapDataset.py:CMapDataset.__getitem__ (object xyz+normal+contact target)
  → utils_model/PointNetCVAE.py:PointNetCVAE.forward
  → train_cvae_criterion.py:VAEAttnCriterion.forward

inf_cvae.py
  → 原物体STL表面采样2048点+面法向
  → 指定checkpoint目录的PointNetCVAE.inference(xyz,z~N(0,I))
  → pre_process_contact_map_goal → cmap_id.pt / cmap_ood.pt

run_grasp_gen.py
  → 读取推理cmap，合成contact_map_goal[N,7]=xyz+normal+value
  → utils_model/AdamGrasp.py:AdamGrasp.run_adam
  → utils_model/CMapAdam.py:CMapAdam.reset
  → utils/get_models.py:get_handmodel → data/urdf/urdf_assets_meta.json
  → utils_model/HandModel.py:HandModel → modified pk.build_chain_from_urdf
  → CMapAdam.step → update_kinematics → compute_energy_* → backward → torch.optim.Adam.step
  → q_tra[B,T,9+J]、energy → .pt

run_grasp_test.py
  → envs/tasks/grasp_test_force_shadowhand.py:IsaacGraspTestForce_shadowhand
  → 固定手姿态驱动、六方向物体外力 → is_obj_stable
```

## 接触表示和能量

CVAE预测的是**物体表面点上的接近程度标量场**，不是离散手候选索引，也不是力向量。
推理时网络只吃xyz和潜变量；物体法向保留给后续接触图对齐优化。
`HandModel.update_kinematics` 的q也是translation3+rotation6d6+URDF关节。
手表面点由每link几何采样再FK变换；另有由contact JSON基底和softmax权重构造接触点的API，
但本次 `CMapAdam` 主路径使用表面点，不应把未调用的接触基底API当成主优化器。

`CMapAdam.compute_energy_euclidean_dist`：
`d_o=min_h ||p_o-p_h||`，`c(q)=2-2 sigmoid(100 d_o)`，接触图L1均值。
`compute_energy_align_dist`：
`a=((p_h-p_o)·n_o)/(||p_h-p_o||+1e-5)`；
`d_o=sqrt(min_h(||p_h-p_o|| exp(2(1-a))))`；`c(q)=2-2 sigmoid(10 d_o)`。
穿透项使用手表面点到最近物体点的距离和法向dot符号，是点云近似，不是闭合网格精确SDF。
返回用于反传的能量是contact L1 + 100×penetration。

**重要实现差异**：两个compute_energy函数给 `self.energy` 加入了关节罚项（部分手有特殊分支），
但返回的变量 `energy` 没有加该项。`step` 对返回值求mean.backward，因此日志/选优能量与实际优化目标不完全一致。
迁移若修复此行为，必须注明差异，不能一边修复一边声称逐步轨迹严格复现。

CVAE的 `VAEAttnCriterion` 使用KL项和 `exp(alpha*gt_contact)` 加权重建RMSE。
不能省去网络训练/预训练权重、只保留Adam拟合后叫“GenDexGrasp完整复现”。

## 物理验证与资产

`envs/tasks/grasp_test_force.yaml`：先驱动200步，再按±x/±y/±z加载50步外力，
力强度按体积×5000，允许位移0.02m，物体/手摩擦10；不同于DexGraspNet的最终接触存在性协议。
`run_grasp_test.py` 此commit只分发shadowhand/barrett/ezgripper，其他手直接NotImplementedError，
尽管生成/训练代码支持Allegro，不能声称此commit已给出Allegro验证入口。

README的数据与资产包是外部下载：data.zip、MultiDex、contact-map dataset、env.zip。
本地已带四份小型checkpoint，但没有配齐data/urdf、物体、完整仿真资产，未加载执行pickle checkpoint。
requirements.yaml包含Python3.8.13、Torch1.12/CUDA11.3.1、numpy1.22.3、usd-core22.8，
不能直接安装到现有Python3.12/Torch2.11/IsaacSim6.2环境。
源码还有过期 `Rotation.as_dcm()` 和带对象的旧torch.load行为，需要有针对性适配。

测试目录主要是vendored pytorch_kinematics的kinematics/jacobian/transform测试；
`run_grasp_test.py` 是需要真实资产的仿真评估程序，不是无需依赖的单元测试。
没有运行其安装、训练或验证脚本。

## 许可

此commit未找到tracked的LICENSE/COPYING/NOTICE，README也未给出代码许可条款。
公开可读不等于已授予任意再分发许可；本轮只分析该仓库，不直接复制源码或权重到src。
数据来源YCB/ContactDB、手URDF和checkpoint的许可需要单独确认。
