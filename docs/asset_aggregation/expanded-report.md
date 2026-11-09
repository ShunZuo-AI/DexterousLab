# M3 第二批资产聚合结果（2026-11-06）

上一轮只验证了 3 种新增手，另有 Allegro/Shadow 官方引用验证，覆盖面不足。本轮已扩大到 **22 条型号/版本配置、17 个厂商通过 100 步实际 GPU PhysX 验证**。这表示真实资产加载及有限步物理验证通过，**不表示 22 套抓取控制器已实现，不表示关节耦合已复现，更不表示抓取成功**。

最新逐厂商数量、具体型号、关节数及日志路径见 [覆盖表](coverage.md)，机器可读证据见 [expanded-validation-summary.json](expanded-validation-summary.json)。原始第一批报告保留为历史记录。

## 已通过的覆盖范围

| 厂商 | 实际通过的手型/版本 |
|---|---|
| Wonik | Isaac Lab 独立 Allegro，16 关节 |
| Shadow Robot | 官方 Shadow PhysX，24 物理关节 / 20 动作；桌面 Cube |
| Unitree | DEX1-1、DEX2-5 右手、DEX3-1 右手、DEX5-1 右手 |
| Wuji | Hand v1 右手、Hand2.1 右手、Hand2.2 右手，使用原生 USD |
| LEAP | LEAP v1 右手 |
| BrainCo | Revo2 右手 |
| LinkerBot | L20 右手 |
| Sharpa | Wave 右手，无腕/法兰附加变体 |
| RobotEra | XHand 右手 |
| Tesollo | DG5F 右手 |
| PSYONIC | Ability 右手 large |
| SCHUNK | SVH 右手 |
| Barrett | bhand_model |
| ROBOTIS | HX5 D20 右手 |
| ORCA | v1 右手 |
| DexRobot | DexHand021 右手 |
| OYMotion | ROHand 右手 |

资产清单现有 **146 条手型/版本记录**；其中 **64 条完成原始包提取，2 条完成官方引用留档**。同一包的左右手或导出变体分别计数，不能把 146 或 64 解释为不同厂商或不同手型数量。仍未提取的索引条目保持 `not_downloaded`，没有填充虚假本地路径。

所有提取包保留精确 commit、许可文件和 SHA256；完整性复核结果见 [expanded-integrity.json](expanded-integrity.json)。模型和参考源码分别位于 `/root/gpufree-data/DexterousLab/assets/`、`/root/gpufree-data/DexterousLab/research-repos/`，没有向项目 Git 放入大型模型。

## 已排查的问题及真实剩余阻塞

- **BrainCo**：初次 1/120 s 步长下约第 40 步后出现非有限状态。当前测试配置为 1/240 s、刚度 0.3、阻尼 0.03、关闭自碰撞、PhysX solver 16/4，100 步通过。原始 URDF、质量及惯性未改；测试参数不是硬件标定结果。初次失败保留在原运行目录。
- **Fourier 6DoF**：左右原始包及 Mesh 已提取，静态检查和转换通过；右手在两次实际 PhysX 验证中出现非有限关节状态。记录 `simulation_status=failed`，未声称支持成功。部分源关节 effort/velocity 为零，mimic 和动力学仍需进一步核验；不为通过测试而捏造驱动力或质量。
- **XHand**：上游 URDF 写 `meshes/`，文件实际位于同包 `assets/`。在元数据保存逐条 mesh alias，并在独立的 `runs/.../import.urdf` 中展开绝对路径；原始文件不变。根许可证含非商业限制，资产保持单独管理，不并入项目代码许可证。
- **ORCA**：补齐 `v1/assets` 和仓库根 `assets`，保留 package 路径映射。质量为零、无几何且通过固定关节连接的指尖标记属于参考坐标系；静态检查明确区分它们与动态连杆。只对 ORCA 的导入配置启用 `merge_fixed_joints=True`，固定标记会合并，后续指尖坐标适配必须考虑此差异。没有给零质量动态连杆编造惯性。
- **DEX-EE**：已提取 4 个真实设备版本的 Xacro 和网格；当前唯一共享环境没有 `xacro`，还需处理 `$(find dx_description)` 等 ROS 替换，未安装依赖或伪造展开结果。
- **qb robotics**：已找到实际官方 Bitbucket 来源，补充 `qbhand`、`qbhand2m` 原始包、BSD 许可和 commit。也是 Xacro/ROS 替换阻塞，不能用之前 GitHub 地址查询失败来断言资产不存在。
- **Ruka**：原仓库提供的是 `assets/xml/hand_assembly.xml` 等 MJCF，并非 URDF；已补登记、提取 MIT 原始模型及依赖。MJCF 的腱、等式约束和控制器到 PhysX 的适配尚未实现，未冒充可仿真模型。
- **RoboParty**：已找到 DH116 / DH116S 的具体归档 URL、版本、大小及官方 SHA256，记录于 `repository-rechecks.json`。仓库资源清单明确写明 public redistribution 未批准，LICENSES.md 也没有给模型统一许可；本轮不提取该归档，记录许可阻塞。
- **Inspire RH56DFX-2LR**：真实型号及路径已索引；逐模型 Mesh 授权范围仍未确认。DexSuite 说明了模型改造来源，但不能把来源说明或父项目许可当成完整 Mesh 授权。
- **Seed Robotics**：重新检查官方文档链接后成功获取实际 ROS 驱动仓库并记录 commit；递归树未找到 URDF/Xacro/USD/STL/DAE 模型。驱动仓库存在与仿真模型存在是两回事。仍需独立模型来源。
- PaXini、Xynova、CasiaHand、Clone、AGILINK/AgiBot、UBTECH 独立手型仍保留具体检索范围与未确认项，详见覆盖表。没有把首次检索失败解释为不存在公开资产。

## 工程变更

- `assets/catalog.py`：安全新增记录、拒绝覆盖同 ID，按当前记录动态计算厂商提取/通过/失败/阻塞数量。
- `assets/manager.py`：支持仓库根包、独立包名前缀、排除 `.git`、保留多份不重名许可文件、按资产配置固定关节合并及原始路径映射。
- `assets/checks.py`：识别合法的无质量固定参考系，仍拒绝无质量动态连杆；导入副本保留原始关节、mimic、尺度和源文件字节；路径越界与缺失 Mesh 明确失败。
- `assets/worker.py`：使用实际 Isaac Lab 导入器，保留单独导入副本；支持按配置调整测试步长、驱动及 PhysX solver 参数。
- `cli.py`：`assets manufacturers` 显示实时覆盖数量，不再只展示来源索引数量。
- `scripts/prepare_asset_references.py`、`expand_asset_batch.py`、`repair_asset_paths.py`、`validate_asset_batch.py`、`record_asset_blockers.py`、`report_asset_coverage.py`：分离来源准备、审核后提取、显式路径适配、逐个 GPU 验证、阻塞登记及证据汇总。

新增测试覆盖：源文件不被改写、mimic/尺度保留、alias 越界拒绝、根包提取不复制 `.git`、许可保留、重复注册拒绝、固定参考系与动态零质量连杆的区别。完整项目测试 **101 passed（3.21 s）**，见 [expanded-unit-tests.log](expanded-unit-tests.log)。Arena/Isaac Lab 原有用户修改保持原样，未安装依赖、未创建环境、未 push。

## 使用命令与边界

```bash
cd /root/gpufree-data/DexterousLab
export PATH="$PWD/scripts:$PATH"
dexlab assets manufacturers
dexlab assets hands --manufacturer robotis
dexlab assets inspect --id robotis/hx5/urdf_hx5_d20_right
dexlab assets validate --id robotis/hx5/urdf_hx5_d20_right --steps 100
dexlab assets inspect --id brainco/revo2/revo2_right_hand
dexlab assets inspect --id shadow_robot/dex_ee/0x02000105

# 已审查的来源包提取、逐个验证及覆盖报告
PYTHONPATH=src /root/gpufree-data/IsaacLab-Arena/.venv/bin/python scripts/expand_asset_batch.py
PYTHONPATH=src /root/gpufree-data/IsaacLab-Arena/.venv/bin/python scripts/validate_asset_batch.py
PYTHONPATH=src /root/gpufree-data/IsaacLab-Arena/.venv/bin/python scripts/report_asset_coverage.py
```

实际转换/验证命令参数在每次运行的 `request.json`、`result.json` 中保留，逐项结果在 `expanded-simulation-results.json`，失败后修复的历史也保留。GPU 测试串行运行，每次只加载一只手，100 步；桌面已有结果保持独立。

这些新增手尚未接入 `scene run --hand ...` 桌面控制入口。掌坐标、指尖映射、动作空间、腱/联动及接触策略要逐手开发；命令不会静默替换为 Allegro。当前导入器对部分 URDF 的 mimic 写出 Newton 专属 schema，不能凭 PhysX 冒烟通过宣称原有机械耦合正确。固定基座位置保持与真正灵巧抓取执行是后续不同验收项。

参考来源的原始 commit、许可及文件路径均在各资产 `metadata.json` 与清单中。qb 官方仓库为 [qbhand-ros](https://bitbucket.org/qbrobotics/qbhand-ros)，Seed 的仓库线索来自[官方 ROS 文档](https://kb.seedrobotics.com/doku.php?id=apisandframeworks:ros)；模型是否存在以本轮实际源码树检查为准。
