# DexGarmentLab 研究与最小集成交付

2026-11-06，使用同一 Python3.12/Isaac Sim6.2/Isaac Lab/Arena 环境和 NVIDIA L40S。全部新文件位于 DexterousLab 内；没有修改官方 Arena/Isaac Lab 或参考仓库，没有安装依赖，没有删除用户数据，没有 GitHub push。

## 源码研究与设计依据

论文、源码和数据集分别核对。源码 commit **e4e298e696bae5d866ded3b31e0ae27becea5376**，已检查21个主要文件的真实类/函数调用链和内容哈希，补读了衣物任务成功判定、DP/DP3格式和视频工具。见 [源码分析与映射表](dexgarmentlab_analysis.md)、[源码清单](dexgarmentlab_source_manifest.json)。

可借鉴部分是资产分类与来源登记、场景/控制/策略分层、按阶段记录与重放、明确数据样本和任务结果。本机没有复制旧 World 生命周期、固定60维双臂动作、时间种子、无限重试采集、仅保留成功样本或覆盖目标数据的转换脚本。现有 HandRegistry、ObjectRegistry、AssetCatalog、ArenaEnvBuilder、ResearchState、GraspCandidate、GraspDatasetWriter 均继续使用。

GAM/SADP/DP/DP3的输入输出和训练推理源码已分析，学习算法、checkpoint兼容和训练效果 **UNVERIFIED/未集成**。当前注册的策略仅为hold位置控制。没有把局部随机扰动称作原论文自动数据生成算法。

## 新增接口与文件

| 接口 | 实现位置 | 已实现内容 |
|---|---|---|
| AssetRegistry | `src/dexterous_lab/assets/registry.py` | 复用AssetCatalog的注册/查询，模型引用、SHA256完整性核验 |
| SceneBuilder | `src/dexterous_lab/scenes/builder.py` | 复用tabletop+Arena，按配置选择手/主物体，显式额外Sphere |
| DatasetCollector | `src/dexterous_lab/data_collection/collector.py` | 命名关节、掌/基座/物体位姿、接触力/点、动作、JSON/NPZ、候选保存，保留失败 |
| EvaluationRunner | `src/dexterous_lab/evaluation/runner.py`、`worker.py` | 独立子进程capture/replay/batch、100步、限位/腱/位姿检查、统计及日志 |
| PolicyRegistry | `src/dexterous_lab/policies/registry.py` | 显式factory、load、reset/predict；只有hold基线，未实现算法明确拒绝 |

另外修改 `assets/primitives.py`、`scenes/tabletop.py` 支持命名的额外刚体；修改CLI增加experiment子命令；新增criteria单元检查、基线候选脚本和三个可运行示例。完整逐文件列表见 [dexgarmentlab_changed_files.json](dexgarmentlab_changed_files.json)。

## Shadow 来源和边界

本轮实际实验使用已有官方 `shadow_robot/dexterous_hand/right_isaaclab`，源配置 `isaaclab_assets.robots.shadow_hand:SHADOW_HAND_PHYSX_CFG`，24个物理关节、16个直接关节动作+4个腱动作。驱动和碰撞继续采用官方已核验PhysX/simplified配置。

DexGarmentLab源组合模型描述另存：

`/root/gpufree-data/DexterousLab/assets/hands/shadow_robot/shadow_hand/dexgarmentlab_reference/metadata.yaml`

该文件为合法YAML1.2的JSON表示，含name/manufacturer/source_repository/source_commit/source_asset_path/local_asset_path/license/format/joint_names/joint_count/verified。源码显示左右UR10e+Shadow组合USD及24手坐标，但未下载和检查79MB的Robots.zip，因此该描述 **verified=false、本地资产路径null**。不重复下载替换已有可用Shadow；也不把它说成已完成组合USD验证。HF官方dataset card声明Apache-2.0，归档内其他来源许可仍未核实；仓库根代码许可未找到。

## 实际实验结果

| 实验 | 实际结果 |
|---|---|
| A，Shadow加载/读关节/控制 | 实际24物理关节、20动作；拇指指令0.15 rad，实测从0到约0.138307 rad；100环境步 |
| B，桌面+Cube+Sphere | 同一Arena场景真实加载主Cube和额外`secondary_sphere`；100环境步、Cube动态质量/碰撞/材料/惯性/尺寸检查通过；Sphere另做100步全物理检查 |
| C，保存/重读/重放 | 保存实际观测而非模板；重新从JSON加载；关节、掌位置、掌朝向和物体位置恢复误差均0；直接关节最终跟踪误差约2.1319e-12 rad；100环境步 |
| D，10条候选 | attempted=10，loaded=10，simulation_completed=10，evaluated=10，successful=0；100步/条；失败原因`no_lift:10` |
| E，数据输出 | capture、replay与10条trial共12份真实轨迹，每份101帧；JSON/JSONL/NPZ/元数据/日志齐全；无pickle、有限值校验通过；未录视频 |

上述0/10是有意使用简单保持/平移扰动基线的真实结果，不是论文方法的成功率。`pose_replay_passed=true`只证明姿态/控制链路，不等于抓取成功。当前有限物理评估标准为3cm抬升、0.01N指尖法向接触、速度≤0.1m/s、最后连续20步保持；尚未检查完整碰撞穿透、力闭合或外力扰动鲁棒性，不能将其包装成完整物理GraspValidator。

最终实测目录：

- capture：`outputs/20261106T095524Z-capture-225febf4/`
- replay：`outputs/20261106T095617Z-replay-23d7d4db/`
- batch：`outputs/20261106T095635Z-batch-e55f347a/`
- Sphere：`assets/objects/custom/sphere/runs/20261106T095348Z-scene-9bc1c816/`

这些路径相对 `/root/gpufree-data/DexterousLab`。逐次请求、真实启动命令、子进程退出码与物理日志在对应目录；聚合证据见 [dexgarmentlab_verification.json](dexgarmentlab_verification.json)，NPZ逐条检查见 [dexgarmentlab_npz_checks.json](dexgarmentlab_npz_checks.json)。较早试运行的目录全部保留。

## 本轮执行命令

```bash
cd /root/gpufree-data/DexterousLab
./scripts/dexlab experiment capture --object cube --include-sphere --steps 100

./scripts/dexlab experiment replay --object cube --include-sphere --steps 100 \
  --input outputs/20261106T095524Z-capture-225febf4/trial_000/candidate.json

PYTHONPATH=src /root/gpufree-data/IsaacLab-Arena/.venv/bin/python \
  scripts/make_replay_candidates.py \
  --input outputs/20261106T095524Z-capture-225febf4/trial_000/candidate.json \
  --output outputs/20261106T095524Z-capture-225febf4/candidates10.jsonl

./scripts/dexlab experiment batch --object cube --include-sphere --steps 100 \
  --input outputs/20261106T095524Z-capture-225febf4/candidates10.jsonl

./scripts/dexlab assets validate --id custom/sphere --steps 100
/root/gpufree-data/IsaacLab-Arena/.venv/bin/python -m pytest -q
```

候选输出文件已存在，重复生成会明确拒绝覆盖；重做实验请使用新capture运行目录。最终replay/batch通过同一个EvaluationRunner执行，真实命令还保留在各目录的launch_result.json。

项目单元测试：**109 passed（3.52s）**，见 [dexgarmentlab-tests.log](dexgarmentlab-tests.log)。GPU实验为单环境串行有限步，未运行完整上游Arena三阶段pytest、未训练策略。新测试覆盖数值NPZ/候选往返、已有目录保护、未知算法拒绝、成功条件必须同时满足、失败和未知统计区分、资产哈希核验及额外Sphere配置。

完整使用说明和三个示例见 [dexgarmentlab_usage.md](dexgarmentlab_usage.md)：`examples/load_shadow.py`、`examples/capture_replay.py`、`examples/batch_validate.py`。

## 未完成部分

- DexGarmentLab组合USD内容、原模型具体关节限位、驱动和网格授权仍UNVERIFIED；没有使用未核验模型冒充实验结果。
- GAM/SADP/DP/DP3/GraspQP等策略和训练权重没有迁移；没有完整论文复现或泛化性能结果。
- 没有真正的自动闭合、接近、抬升策略；本轮提供能承载这些策略的数据与验证链路，基线抓取成功为0。
- 姿态执行适配当前仅支持官方Shadow；其他手型需要单独的动作、腱和掌坐标适配，禁止静默复用。
- 视频可选未实现于这条评估入口；没有移植衣物仿真或LeapMotion硬件监听。
- 输入格式损坏时在GPU前明确拒绝；单条仿真异常会保留原因和已写帧。完整批量崩溃恢复、长时间训练、外力扰动测试及复杂物体接入仍待开发。
