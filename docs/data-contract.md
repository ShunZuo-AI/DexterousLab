# 抓取数据契约 1.0

`GraspCandidate` 包含：`object_id`、`hand_id`、`hand_root_pose`、`joint_positions`、
`object_pose`、`contact_points`、`collision`、`stability`、`success`、`seed`、`algorithm`、`asset_version`。
另含 `schema_version`、`frame`、`hand_root_frame`、`quaternion_order`、`length_unit`、`joint_unit` 和 `tendon_positions`。

## 坐标和单位

- 所有长度单位为米，关节角和腱角坐标单位为弧度。
- 位姿格式固定 `[x, y, z, qx, qy, qz, qw]`，四元数必须归一化。
- `frame="W"`，世界坐标，Z 向上；变换采用主动目标-源记号。
- `hand_root_pose=T_W_H`：手掌根坐标 H 到世界 W；不是 KUKA 机械臂根。
- `object_pose=T_W_O`：物体局部坐标 O 到世界 W。
- `hand_root_frame` 必须说明实际掌 body 名，例如 `palm_link` 或 `rh_palm`。
- `contact_points` 为世界坐标点 `[x,y,z]`。未测量为 `None`，测量后没有接触才是空列表。
- `joint_positions` 按物理关节名称保存；Shadow 的腱控制值单独放 `tendon_positions`。
  不假设两种手相同 DOF，也不依赖张量索引在不同后端相同。
- 多环境状态日志以批次记录真实世界坐标，包含各环境 origin 偏移；不能当成环境局部坐标。

## 结果语义

- `collision=None`：尚未检测禁止的碰撞；`False` 表示完成检测并无禁止碰撞。
  合法的手-物体接触不应自动算作禁止碰撞。
- `stability=None`：尚未测量；非空值是 `[0,1]` 稳定性分数。
  本版没有规定或实现其物理测量协议，后续验证器必须连同协议版本保存元数据。
- `success=None`：未验证；`False`：验证失败；`True`：验证通过。
- `success=True` 的记录要求提供 `collision=False` 和非空稳定性分数，
  这只是字段一致性约束，无法替代对验证器与测量协议的审查。
- `algorithm` 记录候选生成方法和版本，`asset_version` 记录资产版本或内容哈希。

## 尚未实现的物理验证

将来需要显式实现：候选根位姿与关节目标设置、接近/闭合过程、穿透判定、
完整接触流形提取、抬升保持、扰动力测试、回合隔离、随机种子重放。
无接触的自由落体、zero_action、仅物体高度达标或仅成功加载均不能替代这些步骤。

M2 已通过 `ResearchState.contacts()` 提供物体对配置指尖的真实法向力与平均接触位置。
这是 ContactSensor 的聚合测量，不是所有接触点组成的完整流形。
运行状态按环境分组记录这些数据；候选数据结构仍需要算法/验证器显式填入。
测得没有接触时是空点集，而不是未知；碰撞合规性、稳定性和抓取成功仍然未知。

## 使用接口

```python
from dexterous_lab.grasp_synthesis.candidate import GraspCandidate
from dexterous_lab.datasets.writer import GraspDatasetWriter
from dexterous_lab.evaluation.grasp import GraspEvaluator

candidate = GraspCandidate(
    object_id="cube", hand_id="allegro",
    hand_root_pose=(0, 0, 0.5, 0, 0, 0, 1),
    joint_positions={"index_joint_0": 0.0},
    object_pose=(0, 0, 0.3, 0, 0, 0, 1),
    seed=42, algorithm="manual-example", asset_version="procedural-cube-v1",
)
# 此示例只展示数据格式，既不是完整机器人关节映射，也不是可执行抓取。
with GraspDatasetWriter("new_candidates.jsonl") as writer:
    writer.write(candidate)
assert GraspEvaluator().evaluate([candidate])["success_rate"] is None
```

写入器只独占创建新文件，已有文件会报错，调用方必须选择新的数据集路径。
