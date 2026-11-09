# 原始实现研究与迁移

研究对象在 `/root/gpufree-data/research-repos`，没有放入 DexterousLab/src，没有执行安装脚本或修改参考源码。
已有 Arena 和 Isaac Lab 通过同名软链接复用本机 checkout，避免重复下载。
源码读取以固定 commit 和实际函数为依据，算法移植前先完成本报告。

| 仓库 | 本地位置 | 本次 commit |
|---|---|---|
| DexGraspNet 主分支 | `/root/gpufree-data/research-repos/DexGraspNet` | `bd1b13d7248729af117e1d46aaa6266b147a3c7b` |
| DexGraspNet allegro 分支 | 同仓库，使用 `git show FETCH_HEAD:路径` 读取，没有切换或覆盖主分支源码 | `6a48bc4cc612a471eb9c82183c6f888b08eee8e6` |
| GenDexGrasp | `/root/gpufree-data/research-repos/GenDexGrasp` | `29fe7efc558b8cc3ce2d8e67c9c22b014adc21c7` |
| DexGraspNet2 | `/root/gpufree-data/research-repos/DexGraspNet2` | `26ecd76121e3c8218ad53db9840cf34f6b81b076` |
| TorchSDF 0.1.0 | `/root/gpufree-data/research-repos/TorchSDF` | `f2e82262f03809c40d81ec6c6933e08e4ee5600d` |
| 本机 Arena | `/root/gpufree-data/IsaacLab-Arena` | `5fb3bd8a639578d46f4b5ed67b9b5239e1281b9a` |
| 本机 Isaac Lab | `/root/gpufree-data/IsaacLab-Arena/submodules/IsaacLab` | `e3f7d9ff1f5d7f8280de3ece9000b7117f66bcf4` |

Arena/Isaac Lab 原来已有用户修改，因此 commit 本身不等于当前工作树的完整快照。
`source_manifest.json` 另外记录实际读取文件的 SHA256、函数/类位置和工作树状态。
前三个论文仓库和 TorchSDF 的工作树保持干净。

## 报告入口

- [DexGraspNet 源码与 A–L 问题](dexgraspnet/source_analysis.md)
- [实际数学公式和梯度](dexgraspnet/mathematical_formulation.md)
- [依赖与资产许可](dexgraspnet/dependency_analysis.md)
- [统一接口和 Isaac Lab 迁移](dexgraspnet/implementation_mapping.md)
- [复现状态与验收边界](dexgraspnet/reproduction_status.md)
- [GenDexGrasp 源码](gendexgrasp/source_analysis.md) / [迁移映射](gendexgrasp/implementation_mapping.md)
- [DexGraspNet2 源码与迁移](dexgraspnet2/source_analysis.md)

**完整原论文复现、组件级算法迁移、简化算法、只有接口，分别标注。**
几何采样、随机手姿态、零动作仿真或一次能量下降不构成 DexGraspNet 完整复现。
