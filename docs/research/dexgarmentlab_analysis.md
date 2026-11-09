# DexGarmentLab 源码分析与集成决策

研究时间：2026-11-06。参考仓库：`/root/gpufree-data/DexterousLab/research-repos/DexGarmentLab`（旧 `/root/gpufree-data/research-repos/` 为兼容链接）。commit `e4e298e696bae5d866ded3b31e0ae27becea5376`，分支 main，初始工作区干净。阅读文件、SHA256、真实类/函数名与行号见 `dexgarmentlab_source_manifest.json`。未执行上游安装、训练或资产下载脚本。

## 论文与代码边界

论文：[arXiv 2505.11032v3](https://arxiv.org/html/2505.11032v3)，[官方项目页](https://wayrise.github.io/DexGarmentLab/)。论文研究柔性衣物及双臂任务，HALO 将结构对应与轨迹生成分层。本项目只采用适合刚性抓取的实验组织思路，不移植衣物粒子系统，不声称复现 HALO/GAM/SADP。

源代码使用 Isaac Sim 4.5.0（README 和两个 shell 的实际解释器路径），其内置 Python 一般为 3.10；仓库未给独立 Python 锁文件，精确运行 Python 版本为 **UNVERIFIED**。本机为共享 Python3.12、Isaac Sim6.2、IsaacLab-Arena0.3。`requirements.txt` 固定 numpy1.23.5、numba0.56.4、hydra-core1.2、diffusers0.11.1、huggingface_hub0.25 等旧版本，不适合直接 sync 到本机。Open3D、Lula/RMPFlow、Leap Motion、Zarr、Dill、WandB、PointNet2/torch 还需逐模块核验。没有安装这些依赖。

仓库根目录未发现通用 LICENSE/COPYING；个别子文件有 NVIDIA 或第三方声明，不授予整个仓库的复制许可。**本轮不复制上游实现或模型权重，仅独立实现接口与实验基础设施，并保留源码依据。** 论文许可、代码许可和 Hugging Face 资产许可分别核查，不能互相替代。未经核实的资产许可标记 UNVERIFIED。

## 真实调用链与映射

以下路径均相对上述精确 commit，不能用名字相近的其他仓库替代。

| 原功能 | 真实文件/类/函数与调用链 | 输入 → 输出 | 依赖/兼容性与复用决定 | DexterousLab 目标 |
|---|---|---|---|---|
| 资产下载 | `Assets/assets_download.py` 顶层 `snapshot_download` | HF dataset `wayrise/DexGarmentLab`，allow_patterns 五个 ZIP → 当前目录下载文件 | huggingface_hub；不校验资产级许可/sha、不自行解压；README 手动 unzip。无统一外部资产根参数。仅借鉴分类，不执行整包下载 | 扩展现有 `assets/catalog.py`，统一查询/完整性检查 |
| 双臂构造 | `Env_Config/Robot/BimanualDex_Ur10e.py:Bimanual_Ur10e.__init__` → `DexLeft_Ur10e`、`DexRight_Ur10e` | World、左右位置/Euler角 → 两个 Robot | 旧 Isaac Sim World/Robot；本机用 Arena embodiment，必须改写，不直接继承 | 现有 `robots/shadow.py`、SceneBuilder |
| Shadow 载入 | `Env_Config/Robot/DexRight_Ur10e.py:DexRight_Ur10e.__init__/initialize` → `add_reference_to_stage` → Robot → 世界 reset 初始化 | `Assets/Robots/assembly/ur10e_shadow/ur10e_shadow_right_hand_glb.usd` → 6臂+24手坐标 | USD/mesh 在 Robots.zip，不在 clone；不是独立手。单独分离需要重新核验根、惯性及挂载关系，UNVERIFIED | 直接继续用已验证官方 Shadow USD，另记上游描述 |
| 左右/控制 | 上述 Left/Right `hand_dof_names` → `get_dof_index`；`Bimanual_Ur10e.set_both_hand_state` → ArticulationAction；`dense_move_both_ik` | 各24个手角/预定义 open,close,pinch,cradle,smooth → 控制动作 | 上游裸关节名 WRJ/FFJ/...；本机 rh_ 前缀，16直接坐标+4腱，不能将24值直接塞20动作。手姿数组不移植 | 命名关节姿态、显式动作映射、限位与腱约束检查 |
| 场景/步进 | `Env_StandAlone/Hang_Coat_Env.py` 顶层 SimulationApp → `HangCoat_Env(BaseEnv)`；`BaseEnv.__init__/reset/step` | 场景参数、衣物 USD、随机偏移 → GPU World/scene、render=True 步进 | 顶层启动的旧生命周期不能直接 import；物理配置偏衣物且接触池过大。继续用 ArenaEnvBuilder | `scenes/builder.py` 封装现有 tabletop，不另建引擎 |
| 随机化 | `Hang_Coat_Env.py:__main__` → 时间种子、uniform 位置/环境偏移、choice 资产 | 运行时标志 → 任务参数 | 种子依赖 wall time，不方便复现；改成逐候选明确 seed 并保存请求 | `evaluation/runner.py` 请求快照 |
| 记录 | `BaseEnv.record` → physics callback → `HangCoat_Env.record_callback` → `stop_record/record_to_npz` | 每5次 callback：左右关节拼接、RGB、点云、GAM特征 → stage_N 的 numpy object数组及初始衣物参数 | NPZ含对象，读取用allow_pickle=True；复制到本机有安全/格式耦合风险。独立实现纯数值NPZ+JSON+JSONL，失败同样保留 | `data_collection/collector.py`，复用 GraspCandidate/GraspDatasetWriter |
| 重放 | `BaseEnv.replay/_replay_callback` → 子类 `replay_callback`（父类只是pass） | stage_N object数组 → 每tick回调 | 不是通用刚体抓取验证器；保存状态不等于执行策略 | 新 evaluation worker，写入起始状态后真实步进，反馈关节目标跟踪 |
| 批量采集 | `Data_Collection.sh` → `Env_StandAlone/${task_name}_Env.py` | 目标数量 → 成功NPZ数增长 | 按目录文件数重试且吞stdout/stderr，失败可能无限循环；不直接复用 | 有限10条尝试、每条ID/日志/异常、逐项汇总 |
| 成功判定 | `Hang_Coat_Env.py:HangCoat` 与 `Env_Validation/Hang_Coat_HALO.py:Hang_Coat_Validation_HALO` | 最终衣物中心z → 0.50<z<2.0；成功才保存训练NPZ/视频 | 衣物挂衣成功，不等于刚体抓取，绝不复用阈值 | 接触+抬升+连续保持+速度阈值的明确测试标准，记录失败原因 |
| 多次评估 | `Validation.sh` → 每任务HALO → `validation_log.txt`、图片数计数 | checkpoint/次数 → 结果文本、视频 | shell反复计数可无限重试，阶段依任务hardcode；改写 | EvaluationRunner，加载数/运行数/成功数/失败数分开统计 |
| 遥操作 | `TeleOp_Env.py:TeleOp_Env` → `Listener.get_pose('right')` → `set_joint_positions` | LeapMotion观测 → 24手关节弧度 | 脚本打印姿态，没有通用抓取保存API；给左手写值时还使用right indices，应分别核验。传感器/实机UNVERIFIED，不移植监听依赖 | 从真实 ResearchState snapshot 保存命名关节及掌/物体坐标 |
| GAM | `Model_HALO/GAM/GAM_Encapsulation.py:GAM_Encapsulation.get_feature/get_manipulation_points` → `GAM_Model.forward` | Nx3点云 → Nx512特征；demo索引 → 余弦相似度 argmax 点/索引/相似矩阵 | PointNet2、CUDA、Open3D、类别checkpoint。归一化特征匹配思路可借鉴；未运行模型，UNVERIFIED | PolicyRegistry保留外部模型适配边界，不伪造GAM |
| SADP 推理 | `Model_HALO/SADP/SADP.py:SADP.get_action` → `RobotRunner.get_action` → `SADP.predict_action` | 时序点云/agent_pos/affordance → 动作段 | 历史deque、repeat padding、torch设备、checkpoint/dill。旧模型60维双臂动作，非当前Shadow20维 | `policies/registry.py` 统一reset/predict，先仅hold基线 |
| SADP 训练 | `Model_HALO/SADP/train.py:TrainSADPWorkspace.run` → policy `compute_loss`；`data2zarr_sadp.py:main` → RobotDataset | NPZ stage_N → Zarr data/meta episode_ends → 扩散噪声损失、checkpoint/EMA | 原转换器会rmtree既有目标；不执行。没有本机HALO训练结果 | 保留JSON/NPZ训练样本及算法注册，学习模型未实现 |
| DP/DP3 | `IL_Baselines/Diffusion_Policy/DP.py:DP.get_action`；`IL_Baselines/Diffusion_Policy_3D/DP3.py:DP3.get_action` → 各RobotRunner/predict_action、train workspace | RGB或点云+状态 → 双臂动作段 | 独立diffusion依赖、训练权重、数据转换需改写，运行UNVERIFIED | PolicyRegistry阻止加载未实现模型，不声称DP已集成 |

### 数学与数据维度

GAM 源码的迁移点索引是 `argmax_j <f_demo(i)/||f_demo(i)||, f_target(j)/||f_target(j)||>`，输出仍在输入点云坐标系，不能直接当作掌位姿或可执行抓取。SADP 的源码 `conditional_sample` 通过扩散scheduler迭代去噪，`compute_loss` 用预测噪声/目标动作的损失；HALO 对衣物的结构表示不能凭接口相同推广成刚体多手泛化模型。

`Model_HALO/SADP/.../config/task/default_task.yaml`：environment_point_cloud `[2048,6]`、garment_point_cloud `[2048,3]`、object_point_cloud `[2048,3]`、points_affordance_feature `[2048,2]`、agent_pos/action `[60]`。`data2zarr_sadp.py` 将当前状态作观测、下一时刻joint_state作动作，并写episode边界。我们用可变关节名和实际动作维数，绝不固定60维。

### Shadow 源资产核查

- 下载源：`https://huggingface.co/datasets/wayrise/DexGarmentLab/resolve/main/Robots.zip`，脚本仅下载压缩包。服务器访问HF API报网络不可达；浏览器已核对官方 dataset card 声明 Apache-2.0，列表 Robots.zip 约79MB、整个dataset约46.5GB。HF显示短修订 `2ba4092`，完整commit及归档内第三方声明仍UNVERIFIED。记录见 `dexgarmentlab_hf_access.json`。
- 左右路径：`Assets/Robots/assembly/ur10e_shadow/ur10e_shadow_left_hand_glb.usd` / `...right_hand_glb.usd`。组合模型6个UR10e关节+24个手关节，源码initialize列表已实读。
- 手关节顺序：WRJ2,WRJ1; FFJ4,3,2,1; MFJ4,3,2,1; RFJ4,3,2,1; LFJ5,4,3,2,1; THJ5,4,3,2,1。**这是源码显式控制列表，不是未下载USD的实际PhysX顺序**。
- 裸USD关节顺序、全部限位、惯性、碰撞和驱动参数、mesh授权：UNVERIFIED；构造脚本不足以证明。`Set_Drive.py:set_drive` 支持设定目标/刚度/阻尼/max_force，但不能据此捏造模型数值。
- 本轮不重复下载 Robots.zip，改为登记reference-only元数据。实验A—E使用我们已有的 `shadow_robot/dexterous_hand/right_isaaclab` 官方PhysX资产，明确不是DexGarmentLab的UR10e+Shadow复现。

## 集成范围与验收计划

以现有AssetCatalog/HandRegistry/ObjectRegistry/ArenaEnvBuilder/ResearchState/GraspCandidate为基础，新增薄封装AssetRegistry、SceneBuilder、DatasetCollector、PolicyRegistry、EvaluationRunner。默认Shadow、PhysX、一环境、小批量，记录JSON/NPZ及失败。保存→重读→重放使用自身真实观测姿态，不假定DexGarmentLab关节前缀、轴方向或掌坐标标定可通用。

实验B同时加载Cube和Sphere；只选择一个目标参与每次抓取评估，另一个是显式场景物体。实验C验证姿态数值还原与关节位置目标跟踪。实验D的10条候选明确是自有控制基线的扰动候选，不是DexGraspNet/GAM生成，不期待或伪造抓取成功。无法加载、步进失败、没有抬升、无持续接触、保持失败分别保留结果。

完整论文策略训练、GAM/SADP checkpoint运行、衣物系统、LeapMotion硬件、DexGarmentLab组合USD物理验收均UNVERIFIED/未移植。

## 补充核查

- `Env_Validation/Fold_Tops_HALO.py:FoldTops` 最后用 `judge_pcd(...threshold=0.12)`；`Fling_Tops_HALO.py:FlingTops` 用 `judge_fling(...threshold=0.2)`，成功条件随衣物任务变化，不能当成统一抓取率。
- `Env_Config/Camera/Recording_Camera.py:Recording_Camera` 提供RGB/depth点云与异步视频收集/MP4输出。我们本轮不移植线程采集与衣物点云管线，视频为可选、未生成。
- `IL_Baselines/Diffusion_Policy/data2zarr_dp.py` 用image和当前joint_state作观测、下一帧joint_state作动作；DP3的default_task配置为point_cloud `[2048,6]`、agent_pos/action `[60]`。
- `Model_HALO/GAM/` 当前树有模型/封装/checkpoints，未找到独立GAM训练入口。论文训练流程与公开可执行训练源码不能混为一谈；GAM训练复现UNVERIFIED。
- 旧Isaac Sim旋转工具/Robot接口需按其标量在前约定核验，本机已验证状态使用xyzw；不直接搬入其旋转数组。
- 当前额外Shadow描述文件：`assets/hands/shadow_robot/shadow_hand/dexgarmentlab_reference/metadata.yaml`，使用JSON语法的有效YAML1.2保存，不引入新依赖。`verified=false`仅指DexGarmentLab源组合资产未验证，不能据此否认已有官方Shadow的实测结果。
