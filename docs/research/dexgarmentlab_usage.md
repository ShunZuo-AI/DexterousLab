# Shadow 姿态采集、重放与批量验证

源码研究与接口映射先于实现完成，见 [dexgarmentlab_analysis.md](dexgarmentlab_analysis.md)。本轮适配实验组织、明确的输入/输出与按次记录方式，不复制 DexGarmentLab 控制或模型源码，不复现衣物任务、GAM 或 SADP。

所有代码、参考源码、资产和数据保存在 `/root/gpufree-data/DexterousLab/` 下，沿用已有唯一 Arena Python 环境。旧项目外路径是兼容链接。不要执行上游 requirements 安装。

## 三个最小示例

### A：加载 Shadow

```bash
cd /root/gpufree-data/DexterousLab
export PATH="$PWD/scripts:$PATH"
dexlab assets validate --id shadow_robot/dexterous_hand/right_isaaclab --steps 100

# 在服务器云桌面查看
dexlab assets preview --id shadow_robot/dexterous_hand/right_isaaclab

# 等价 Python 示例，运行真实验证而非只 import
PYTHONPATH=src /root/gpufree-data/IsaacLab-Arena/.venv/bin/python examples/load_shadow.py
```

此资产来自本机官方 Isaac Lab PhysX 配置，不是 DexGarmentLab 的 UR10e+Shadow 组合USD。DexGarmentLab 来源登记位于 `assets/hands/shadow_robot/shadow_hand/dexgarmentlab_reference/metadata.yaml`，`verified=false`、本地模型路径为 null。

### B：保存姿态，再重读和重放

```bash
dexlab experiment capture --object cube --include-sphere --steps 100
```

输出JSON中的 `run_directory` 是这次唯一目录。复制该路径，替换下面的 `<capture_run>`：

```bash
dexlab experiment replay --object cube --include-sphere \
  --input <capture_run>/trial_000/candidate.json --steps 100

# 一次完成采集和重放的可运行示例
PYTHONPATH=src /root/gpufree-data/IsaacLab-Arena/.venv/bin/python examples/capture_replay.py
```

capture 用0.15 rad的小幅拇指位置指令验证驱动响应，再保存实际测量姿态。掌位姿和关节均来自仿真状态，不是预填模板。随后重放先检查全部物理关节、限位和四个腱坐标，再恢复起始机器人/物体状态，用20维实际动作经 Arena action manager 继续步进。直接关节最终跟踪误差 ≤0.03 rad 才标记 `pose_replay_passed`，该标记与 `success`（物体是否达到抬升保持标准）分别保存。

当前只支持已配置的Shadow，目标物体支持cube/sphere/cylinder。`--include-sphere` 在Cube场景中额外放置Sphere，Cube是被评估目标，Sphere是第二个独立刚体；不代表两个物体同时抓取。输入姿态必须匹配所选物体与版本，物体必须从桌面附近开始，不能用已被人为抬起的初始物体冒充成功。

### C：生成10条明确标记的基线候选并验证

```bash
PYTHONPATH=src /root/gpufree-data/IsaacLab-Arena/.venv/bin/python \
  scripts/make_replay_candidates.py \
  --input <capture_run>/trial_000/candidate.json \
  --output <capture_run>/candidates10.jsonl --seed 42

dexlab experiment batch --object cube --include-sphere \
  --input <capture_run>/candidates10.jsonl --steps 100

# Python 示例，输入同一候选文件
PYTHONPATH=src /root/gpufree-data/IsaacLab-Arena/.venv/bin/python \
  examples/batch_validate.py --input <capture_run>/candidates10.jsonl
```

10条数据来自测量姿态和水平±1cm平移扰动，**不是DexGraspNet、GenDexGrasp、GAM或HALO生成结果**。这是验证基础设施的简单对照输入，没有闭合/抬手策略，预期不会产生有效抓取。脚本独占创建候选文件，重复命令不会覆盖已有数据。

## 输出与统计

每次输出到 `outputs/<时间>-capture|replay|batch-<唯一编号>/`：

- `request.json`：场景配置、明确seed、候选、策略、成功标准。
- `simulation.log`、`launch_result.json`：真实子进程命令、退出码和日志。
- `robot_mapping.json`、`scene_validation.json`：实际关节/腱/指尖、动作维数和刚体检查。
- `trial_000/metadata.json`：对象和手配置、实际动作映射、版本、仿真步长、seed和来源依据。
- `trial_000/states.jsonl`、`trajectory.npz`：实际关节、关节速度、掌和机器人基座位姿、物体位姿、动作、接触力及接触点。
- capture还输出 `candidate.json`、`candidates.jsonl`；每条trial都有 `result.json`，失败同样保留。
- `trials.json`、`report.json`：加载数量、运行数量、已评估数量、成功数量、成功率和失败原因。

NPZ全为数值/字符串数组，用 `np.load(path, allow_pickle=False)` 读取。接触点为指尖过滤后的平均接触位置，使用 `contact_points`+`contact_offsets` 保存变长点集；不冒充完整接触流形。世界坐标W，四元数xyzw，米、弧度。`hand_root_pose`明确是配置的 `rh_palm`，与 `robot_base_pose`分开。

默认成功标准是：物体高于配置的初始桌面位置至少0.03m、测得指尖法向接触力至少0.01N、物体线速度≤0.1m/s，最后连续保持至少20个环境步。没有做完整穿透、自碰撞、扰动抗性或力闭合验证，因此不将此评估器冒充完整 GraspValidator，也不把结果回填为满足更强语义的 `GraspCandidate.success=true`。

batch 的 `completed=true` 只表示有限次数实验流程完成；要看 `summary.simulation_completed` 和逐条trial判断运行数。单次capture/replay出现控制或恢复失败，入口返回非零。损坏的JSON或 schema 数据会在启动GPU前拒绝；加载后的关节/限位/状态失败按trial保留。

## 新增接口

- `assets.registry.AssetRegistry`：继承并复用 AssetCatalog，可 register/get/model_path/verify_integrity，不另建资产数据库。
- `scenes.builder.SceneBuilder`：复用原 `DexterousLabTabletopEnvironment`、HandRegistry、ObjectRegistry和ArenaEnvBuilder。
- `data_collection.collector.DatasetCollector`：实际观测写入、GraspCandidate保存、无pickle的NPZ输出、失败记录。
- `evaluation.runner.EvaluationRunner`：隔离子进程启动capture/replay/batch，保留退出码和证据。
- `policies.registry.PolicyRegistry`：reset/predict/factory接口；目前只有hold位置控制基线。HALO、GAM、SADP、DP、DP3均未实现加载，未知名称明确报错。

当前不提供通用模型训练、衣物仿真、LeapMotion硬件遥操作、所有手型的抓取控制和视频录制；这些边界不会因示例可运行而被隐去。
