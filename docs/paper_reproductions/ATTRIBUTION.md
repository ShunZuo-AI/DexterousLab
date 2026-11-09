# 原实现依据与归属

本轮没有把论文仓库整体复制到DexterousLab/src，也没有复制第三方mesh、checkpoint、CUDA或FK包到src。
迁入库中的算法组件根据下列已读取代码与数学行为重新组织，明确保留研究来源。
这份记录没有把参考作品重新许可为Apache/MIT，也不声称商用授权。

## DexGraspNet

论文：Ruicheng Wang、Jialiang Zhang、Jiayi Chen、Yinzhen Xu、Puhao Li、Tengyu Liu、He Wang，
“DexGraspNet: A Large-Scale Robotic Dexterous Grasp Dataset for General Objects Based on Simulation”。
原仓库：https://github.com/PKU-EPIC/DexGraspNet ，主分支commit
`bd1b13d7248729af117e1d46aaa6266b147a3c7b`。

| 新文件 | 依据的原始文件与作者声明 |
|---|---|
| `grasp_generation/dexgraspnet/energy.py` | `utils/energy.py`（Jialiang Zhang）；`utils/hand_model.py:self_penetration`（Jialiang Zhang、Ruicheng Wang） |
| `grasp_generation/dexgraspnet/optimizer.py` | `utils/optimizer.py:Annealing`（Jialiang Zhang） |
| `grasp_generation/dexgraspnet/optimization.py` | `scripts/generate_grasps.py:generate`与main.py优化调用顺序 |
| `grasp_execution/dexgraspnet_adapter.py` | main.py qpos序列化；scripts/validate_grasps.py原姿态解码 |

这些utils路径均位于原仓库的 `grasp_generation/` 下。
源码README明确声明work/dataset为CC BY-NC4.0，原作者和条款链接应保留：
https://creativecommons.org/licenses/by-nc/4.0/ 。
具体发布时应继续保留来源、修改说明，不能因重写了矩阵计算就声称参考实现的所有授权问题已解决。

对照测试仅在运行时读取固定参考文件，在内存执行纯Torch函数；不修改参考文件，不执行生成/安装入口。
测试使用解析夹具，不使用受独立许可约束的完整模型或数据。

## 其他已阅读实现

- GenDexGrasp：原仓库 https://github.com/tengyu-liu/GenDexGrasp ，此commit未见明确代码许可证。
  仅分析，没有复制网络/Adam/权重代码到src。
- DexGraspNet2：https://github.com/PKU-EPIC/DexGraspNet2 ，README为CC BY-NC4.0。
  仅分析，没有移植训练网络或数据。
- TorchSDF0.1.0：https://github.com/wrc042/TorchSDF ，根LICENSE为Apache2.0。
  用于确认query梯度和法向detach，不复制或编译CUDA实现。
- 当前Arena与IsaacLab：继续调用已有公开扩展接口，参考代码不修改。

完整commit、原文件SHA256和函数行号见 `source_manifest.json`；资产和其他第三方许可见各依赖报告。
