# M3 资产聚合交付记录（2026-11-06）

此页保留第一批历史结果；最新覆盖范围见[第二批报告](expanded-report.md)和[逐厂商覆盖表](coverage.md)。

本轮完成来源索引、首批资产提取、URDF 导入、原生 USD 引用和真实 GPU 验证。**资产可加载、固定根位置保持、零动作步进均不代表抓取成功。**

## 目录及状态

- 参考源码：`/root/gpufree-data/research-repos/`，不执行其安装脚本。
- 模型：`/root/gpufree-data/dexlab-assets/hands/<manufacturer>/<model>/<variant>/`，包含 `raw/`、`processed/`、`isaaclab/`、`metadata.json`、`validation.json`。
- 物体：同一资产根下 `objects/{ycb,dexgraspnet,objaverse,maniskill,custom}/`。
- 缓存：`dexlab-assets/cache/`；旧 `/root/gpufree-data/assets/cache` 已原样移动并保留软链接。
- 项目内只保存小型索引：`assets/manifests/{hands,manufacturers,objects}.json`，以及两个 `*source_inventory.json`。

登记 **30 个厂商、143 条手型/版本记录、7 条物体或集合记录**。记录包括未解析来源的占位元数据，绝不能把登记数量解释为可用手型数量。未找到模型的记录中路径为 null，没有制造空 USD/URDF。

每条记录分别保存上游路径、commit、本地原始路径、转换后路径和 Isaac Lab 引用。`download_status`、`conversion_status`、`simulation_status` 独立更新。原生 USD 标记 `native_usd_no_conversion`，官方引用标记 `reference_recorded`，不冒充完成模型下载或转换。

## 实际验证

| 资产 ID | 实际来源 | 关节 | 本轮结果 |
|---|---|---:|---|
| `unitree/dex3_1/right` | 官方 URDF，Isaac Lab 导入 USD | 7 | 100 步 GPU PhysX，通过 |
| `leap/leap_hand_v1/right` | LEAP Sim URDF，导入 USD | 16 | 100 步 GPU PhysX，通过 |
| `wuji/hand_v1/right` | 厂商原生分层 USD | 20 | 100 步 GPU PhysX，通过 |
| `wonik/allegro/isaaclab_standalone` | 当前 Isaac Lab 官方独立 Allegro 配置 | 16 | 100 步 GPU PhysX，通过 |
| `shadow_robot/dexterous_hand/right_isaaclab` | 当前官方 Shadow PhysX 配置；自定义桌面 Cube 场景 | 24 物理 / 20 动作 | 100 环境步，通过 |
| `custom/cube` | 自有参数化几何；KUKA + Allegro 桌面 | 机器人 23 / 动作 23 | 100 环境步，通过 |
| `custom/cylinder` | 自有参数化几何；KUKA + Allegro 桌面 | 机器人 23 / 动作 23 | 100 环境步，通过 |
| `custom/sphere` | 自有网格及配置已生成 | — | 本轮未运行；明确 `not_run` |

资产专用验证逐步检查关节位置/速度及根姿态有限、关节和连杆确实加载、后端质量和惯性正定、存在启用的碰撞几何、USD 尺度合理；输出具体关节名、质量、惯性和包围盒。URDF 静态检查网格引用及 SHA256、网格尺度、关节轴/上下限、质量/惯性、碰撞几何。物体桌面验证沿用 M2 的真实动态刚体、质量、材料、惯性、尺寸和接触接口检查。

Wuji 首次验证真实失败：`right_finger1_joint1` 的下限为约 0.047 rad，全零初始化非法。已从原始 USD 关节限位推导合法初值，并固定根链接用于本轮资产检查；保留失败日志。所有新手使用的 3 N·m/rad 刚度、0.1 阻尼只是测试驱动参数，尚未做真实硬件标定。原始文件未修改。

机器可读结果及日志绝对路径见 [validation-summary.json](validation-summary.json)、[batch-results.json](batch-results.json)。每次运行目录中保存 `request.json`、`simulation.log`、`evidence.json`（桌面为 `simulation_result.json`）和 `result.json`；失败记录同样保留。

## 版本与许可

| 提取的参考仓库 | 实际 commit | 保存的许可 |
|---|---|---|
| unitreerobotics/unitree_ros | `41dec58c7a3ccb3050243ef16ac2ca74b2b0f9ca` | BSD-3-Clause / `SOURCE_LICENSE` |
| leap-hand/LEAP_Hand_Sim | `150bc3d4b61fd6619193ba5a8ef209f3609ced89` | MIT / `SOURCE_LICENSE.txt` |
| wuji-technology/wuji-description | `5c4dfa16917355d073e2e1d7e3d03897b6cf9508` | MIT / `SOURCE_LICENSE` |
| 本地 Isaac Lab | `e3f7d9ff1f5d7f8280de3ece9000b7117f66bcf4` | 配置代码 BSD；远程 NVIDIA 资产按其自身条款引用 |

对本轮提取包保存原始许可和所有原始文件 SHA256，不重新授权第三方模型。官方 USD 通过配置引用与数据盘缓存使用，不整库复制或再分发。其他索引中发现 LICENSE 不等于模型 Mesh 已获得逐项授权；未经审核的下载明确拒绝。

## 命令与实现

```bash
cd /root/gpufree-data/DexterousLab
export PATH="$PWD/scripts:$PATH"
dexlab assets manufacturers
dexlab assets hands --manufacturer unitree
dexlab assets inspect --id unitree/dex3_1/right
dexlab assets fetch --id unitree/dex3_1/right
dexlab assets convert --id unitree/dex3_1/right --format usd
dexlab assets validate --id unitree/dex3_1/right --steps 100
dexlab assets validate --id leap/leap_hand_v1/right --steps 100
dexlab assets validate --id wuji/hand_v1/right --steps 100
dexlab assets validate --id wonik/allegro/isaaclab_standalone --steps 100
dexlab assets validate --id shadow_robot/dexterous_hand/right_isaaclab --steps 100
/root/gpufree-data/IsaacLab-Arena/.venv/bin/python docs/asset_aggregation/run-batch.py
/root/gpufree-data/IsaacLab-Arena/.venv/bin/python -m pytest -q
```

`fetch` 从本地精确 commit 的已审查参考 checkout 提取包，校验许可和磁盘余量；重复提取校验 SHA256。首次准备使用 `git clone --depth 1 --filter=blob:none --sparse`，只稀疏拉取 Unitree DEX3-1、LEAP `assets/leap_hand`、Wuji v1 右手的 USD/网格及 URDF 依赖。不会隐式更新参考仓库。`scripts/index_asset_sources.py` 只查询提交与目录树；`scripts/build_asset_catalog.py` 拒绝覆盖已经存在的状态清单。

源码位于 `src/dexterous_lab/assets/{catalog,checks,manager,worker}.py`；CLI 在 `cli.py`；缓存配置在 `storage.py`；自动化测试在 `tests/test_asset_catalog.py`。共享环境保持不变，未运行 pip/uv/conda 安装。本轮不修改 Arena/Isaac Lab 源码，也不更改其已有用户修改。

## 限制及缺失项

- `preview` 尚未实现，返回明确非零错误。`fetch` 尚不负责自动克隆任意新仓库；需要已核验 commit 的参考 checkout。xacro 展开、闭链/腱驱动专项适配、任务控制标定尚未实现。
- Unitree 左右手和腕部变体分开登记；只验证 DEX3-1 右手。Wuji Hand2.1 与 Hand2.2 分开登记，本轮仅验证 v1 右手。Linker 各实际目录型号分别登记，不合并成通用手。RH56 只保留真实型号路径，不将不同型号混用。
- LEAP Isaac Lab 仓库扫描中未发现 LICENSE，首批选取有 MIT 文件的 Sim URDF；不是声称其原生 USD 不可使用。
- 指定的 `renesas-rdk/inspire_rh56_hand_description` 在本次 API 查询不可用；替代路径仅索引 ManiSkill 的具体 RH56 型号，Mesh 许可仍需核验。
- RoboParty 仓库目录树未找到独立 USD/URDF；其 README 的压缩包/发布资源仍待进一步核验，不伪造模型。
- PaXini、Xynova、CasiaHand 本轮没有确认可下载的具体模型；Seed、qb robotics、Clone 的候选仓库未解析成功。AGILINK SDK 发现线索，但未核验具体模型；UBTECH 找到整机描述，尚未确认独立手型。均只是首轮检索结论，不代表厂商从未发布公开模型。
- BrainCo、Sharpa、XHand、DEX-EE、Tesollo、PSYONIC、SCHUNK、Barrett、ROBOTIS、ORCA，以及 DexRobot、OYMotion、Ruka、Fourier 已记录实际源码路径；本轮未做许可/转换/仿真全流程审核。
- YCB、DexGraspNet、Objaverse、ManiSkill 是来源集合元数据，未批量下载数据集；每个物体 Mesh、尺度、许可及物理参数仍需单独审核。
- 新增 Unitree/LEAP/Wuji 仅完成资产级加载验证；尚未注册成桌面任务可选控制器，也未实现专用掌坐标、指尖接触映射或抓取策略。既有 Allegro/Shadow 桌面入口保持原有行为，不静默替换机器人。
- 单元测试 **97 passed（3.28 s）**，记录于 `unit-tests.log`；重复 fetch 的文件完整性检查也通过。本轮没有重跑完整上游 Arena pytest 三阶段；实际运行使用现有原生共享环境，未引入 Docker/新环境。

上游全部扫描 commit、真实文件路径及请求失败信息见两个来源 inventory；未把 API 查询失败解释为不存在模型。不存在抓取成功率结果；M3 资产工程不等于 DexGraspNet 算法复现。
