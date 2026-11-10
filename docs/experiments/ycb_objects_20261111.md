# YCB 物体下载与仿真验证

2026-11-11，在现有 Arena `.venv` 与 L40S 上下载、准备并验证三个真实日用品模型。三种物体均可加载到 DexterousLab 桌面环境并进行物理步进；尚未执行这些物体的主动抓取实验。

## 样本与结果

| YCB物体 | CLI物体名 | 原始尺寸 X × Y × Z（mm） | 碰撞近似 | 真实仿真 |
|---|---|---|---|---|
| 003_cracker_box | `ycb_cracker_box` | 71.8 × 164.0 × 213.4 | convexHull | Allegro：100环境步 / 400物理步 |
| 006_mustard_bottle | `ycb_mustard_bottle` | 97.2 × 66.6 × 191.3 | convexHull | Allegro：100环境步 / 400物理步 |
| 025_mug | `ycb_mug` | 117.0 × 93.1 × 81.3 | convexDecomposition | Allegro与Shadow：各100环境步 / 400物理步 |

每次仅1个环境。Allegro使用KUKA + Allegro，动作维度23；Shadow动作维度20。各运行完成101次状态采样，机器人、动态物体、碰撞、正惯量和有限状态检查通过。后端实测质量约0.1 kg、静/动摩擦约0.7；这些是试验设定，不是物体真实质量与摩擦的测量。

网格保留原始米制尺寸，仅将包围盒中心移到物体局部原点。场景姿态采用xyzw四元数，Z轴朝上，初始物体底部高于桌面3 mm。转换前后尺寸一致，USD单位为米，材质存在且纹理引用指向真实文件。

压缩包合计29,796,271字节，约29.8 MB。官方来源与CC BY 4.0说明见 [YCB AWS条目](https://registry.opendata.aws/ycb-benchmarks/)。各物体保留原始包、网格、纹理、下载地址、归属、许可链接、下载时间与SHA-256；哈希为本机首次下载测量，并非发布者提供的独立校验值。

## 复现命令

先按README完成安装和PATH设置，在项目目录执行：

```bash
dexlab assets download-ycb --objects cracker_box mustard_bottle mug
dexlab assets prepare-ycb --objects cracker_box mustard_bottle mug

dexlab assets validate --id ycb/003_cracker_box --steps 100
dexlab assets validate --id ycb/006_mustard_bottle --steps 100
dexlab assets validate --id ycb/025_mug --steps 100
dexlab scene run --hand shadow --object ycb_mug --physics physx --steps 100
```

也可直接用场景入口，例如 `dexlab scene run --hand allegro --object ycb_mustard_bottle --physics physx --steps 100`。`assets validate`同时更新资产清单的验证状态，`scene run`保留独立运行结果。

- 下载入口：`src/dexterous_lab/assets/ycb.py`，4个并发请求、128 KiB分块，逐块校验范围与长度，限制包大小并拒绝不安全的压缩包条目。
- 准备入口：`src/dexterous_lab/assets/ycb_prepare.py`、`ycb_worker.py`，通过独立SimulationApp子进程调用Isaac Lab官方MeshConverter。
- 场景组装：沿用 `scenes/tabletop.py`、`objects/factories.py` 的Arena Object接口，没有新建一套场景框架。
- 下载位置：`assets/objects/ycb/<YCB名称>/raw/`；USD与纹理位于同物体的 `processed/<准备运行名>/`。
- 配置位置：`configs/objects/ycb_*.toml`，准备命令本地生成，USD路径相对项目根目录解析，不依赖运行时工作目录。

模型、纹理与生成配置不提交Git。全新克隆后，已有资产清单但无本地模型时，下载命令会下载文件并更新对应清单，避免重复注册。重复下载会校验已有文件，重复准备会核查派生文件与配置校验和；发现用户修改时拒绝覆盖。准备失败的输出与日志保留用于排查。

## 实际日志

四次仿真的请求、结果、关节映射及完整仿真日志已复制至 [证据目录](ycb-20261111/summary.json)：

| 运行 | 原始运行目录 |
|---|---|
| Allegro / Cracker Box | `assets/objects/ycb/003_cracker_box/runs/20261110T162144Z-scene-8aedba3a` |
| Allegro / Mustard Bottle | `assets/objects/ycb/006_mustard_bottle/runs/20261110T162343Z-scene-30f542a2` |
| Allegro / Mug | `assets/objects/ycb/025_mug/runs/20261110T162724Z-scene-2fb2932b` |
| Shadow / Mug | `outputs/20261110T162817Z-scene-d57121c6` |

目录名为UTC时间，对应上海时间2026-11-11。原始运行目录还保留逐步状态和算法用物体局部坐标网格。证据目录保存三个物体的来源与准备报告；没有录制本批物体的截图或视频。

单元测试：**141 passed，3.37秒**。[测试日志](ycb-20261111/tests.log)。已验证重复下载不重新联网、已有文件校验、不完整包拒绝、路径穿越与符号链接拒绝、分块顺序、克隆后重新下载、法线修复和相对USD路径。

## 问题与限制

- 普通整包传输在本机明显缓慢，改为有限并发分块下载后完成全部样本；未下载图像帧或大型完整数据集。
- 首次纹理检查只检查 `inputs:file`，误判转换后丢失纹理。已改为检查所有图像asset属性并核实文件存在，兼容当前转换器输出的材质。
- 杯子原始OBJ含1条 `vn nan nan nan`，官方转换器拒绝导入。仅在派生副本移除导入法线与法线索引，保留顶点、面顶点索引和UV索引，由导入器重新生成法线；原始文件和校验和保持不变。转换器还会合并顶点、清除部分退化面，因此不要假设导出网格的顶点/面索引与原始OBJ完全相同。
- 对逐帧视觉网格与桌面做补充检查：饼干盒最大约1.37 mm交叠，芥末瓶最大约1.89 mm交叠；杯子在两种手的运行中未测到负间隙。芥末瓶最后20帧仍有约3.1 mm范围的平面漂移。故没有宣称所有物体已完全无穿透或充分静稳；详细数值见各运行的 `geometry_support_check.json`。
- 杯子采用凸分解，当前未专门验证杯柄与内腔的碰撞精度。接触数据仅覆盖配置的指尖，不是所有链接的完整碰撞审计。
- 所有运行均为zero_action，`grasp_success=null`。本次没有证明抓取成功、抗扰稳定性或策略可泛化；首次抓取脚本仍以Cube为基线。
- 未安装新依赖、未创建Python环境、未修改Isaac Lab或Arena上游源码。使用的是当前已安装的配置API，运行日志有弃用提示，尚未迁移到未来版本API。
