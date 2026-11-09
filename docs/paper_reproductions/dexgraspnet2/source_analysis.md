# DexGraspNet2：源码与接口研究

根目录 `/root/gpufree-data/research-repos/DexGraspNet2`，commit
`26ecd76121e3c8218ad53db9840cf34f6b81b076`。
默认训练配置 `configs/network/train_dex_ours.yaml` 的robot是 **LEAP Hand**，joint_num=16，
不能把DexGraspNet1的Shadow和这个仓库默认手混为一谈。

## 调用链和模型

```text
src/train.py:main
  → GraspNetDataset / minkowski_collate_fn
  → src/network/model.py:get_model
  → GraspnessSample（graspness_diffusion / isa / cvae）
  → objectness/graspness预测 + 条件pose生成 → loss/backward

src/eval/predict_dexterous.py
  → 同一get_model加载checkpoint
  → GraspnessSample.sample / sample_grasp
  → sparseconv特征、graspness选择seed points、条件diffusion.sample
  → rot、trans、joints、log_prob → npz

src/eval/evaluate_dexterous.py
  → DataEvaluator / SimulationEvaluator.evaluate_data
  → _compute_waypoints(pregrasp,cover,grasp,squeeze,lift)
  → _check_collision + _reset_environments + _execute_waypoints
  → _get_sim_successes
  → pregrasp_valid AND sim_success
```

`src/network/graspness_sample.py:sample_grasp` 根据config解码sixd/SVD/quat/axis-angle等旋转；
joint坐标可来自diffusion欧式部分，也可来自joint_mlp；translation由seed voxel中心加预测偏移构成。
这不是原DexGraspNet的五项能量+退火优化器。

## 手几何、碰撞和资产处理

`src/utils/robot_model.py:RobotModel` 读取URDF/meta，建立joint顺序、FK、link几何和collision mask，
提供 `forward_kinematics`、`cal_distance`、`cal_self_distance`、`self_penetration`。
`src/utils/collision_checker.py:CollisionChecker.check_collision_batch` 计算手与场景点云/桌子的穿透距离。
`src/preprocess/refine_dataset.py:main` 读取场景、camera与table变换，通过 `PoseRefine.refine` 更新数据；
`src/preprocess/dex_graspness.py` 依照已有dex grasps、点云、碰撞阈值生成graspness训练标签。
这些脚本有加载/写数据和main执行副作用，本轮仅阅读，没有直接import执行。

## 验证协议

`src/utils/simulator/isaacgym_simulator.py:IsaacGymSimulator` 使用Isaac Gym/PhysX，不是Isaac Lab。
`SimulationEvaluator._execute_waypoints` 在前几段关闭物体重力，squeeze后打开，再lift。
`_get_sim_successes` 判断场景中**任一物体**最终比其初始高度高0.03m；
再与预抓取scene/table碰撞检查组合，不是指定目标物体的完整抗扰验证。
默认 `configs/data_evaluator/leap_hand/SimulationEvaluator.yaml` 四段时长40/20/20/60步。
`tests/visualize_*` 是依赖场景数据的可视化脚本，未发现对整个训练/仿真管线的独立单元测试套件。

## 依赖与迁移

README目标Python3.8、Torch2.0.1/CUDA11.7、PyTorch3D0.7.5、IsaacGym4、MinkowskiEngine、
TorchSDF、torchprimitivesdf、diffusers、nflows等；不能按原指令降级我们的环境。
部分依赖需本地CUDA/BLAS构建，当前并未安装。大型场景数据/checkpoint需要另外下载。
README声明工作和数据CC BY-NC4.0，模型/场景来源还有各自条件。

| 原实现 | 我们的接口 | 本轮状态 |
|---|---|---|
| GraspnessSample与diffusion | 后续学习式GraspGenerator | 已分析，未迁移、未训练、未加载网络 |
| RobotModel/CollisionChecker | 可微hand/object几何backend | 已分析；LEAP拓扑不能替换成Allegro/Shadow后宣称权重通用 |
| SimulationEvaluator | IsaacLab GraspValidator | 需独立适配waypoint和目标物体成功规则，不复用零动作判定 |
| candidate npz | GraspCandidate/Writer | 需要具名关节、坐标系/单位/模型版本与算法来源 |

DexGraspNet2完整复现未完成，本轮不复制它的复杂训练依赖或第三方资产。
