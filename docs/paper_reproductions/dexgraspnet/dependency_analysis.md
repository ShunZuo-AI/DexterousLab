# 依赖、资产与许可分析

源码依赖清单来自 `grasp_generation/README.md`、`asset_process/README.md`、
`thirdparty/pytorch_kinematics/setup.py` 与真实 imports。
当前环境实测版本和模块可发现性见 `../dependency_inventory.json`，没有执行安装命令。

| 模块 | 原始环境/用途 | 本机情况与迁移策略 |
|---|---|---|
| Python/PyTorch/CUDA | README约Python3.7、Torch1.10、CUDA11.3 | 现有Python3.12/Torch2.11+cu130，保持不变；数学组件仅用已有Torch |
| modified pytorch_kinematics | MJCF/URDF FK；vendored setup标为0.3.0/MIT | 未安装；不能假定当前PyPI版同接口或批处理性能；先保留backend边界 |
| PyTorch3D | Meshes、表面采样、FPS | 未安装；不安装旧CUDA wheel到当前环境 |
| TorchSDF0.1.0 | CUDA点-三角形距离、自定义query梯度 | 未安装；已额外clone读源码，未编译；旧CUDA扩展不能假定兼容Torch2.11/CUDA13 |
| transforms3d | Euler/rot6d保存与初始化 | 未安装；适配层优先已有Torch/SciPy，旋转约定必须对照 |
| urdf_parser_py | Allegro分支URDF/几何 | 未安装；未来需要解析兼容性检查，不能直接装完整论文环境 |
| trimesh/scipy/numpy | 凸包、最近点、网格 | 已有4.11.1/1.17.0/2.3.1；旧remove_degenerate_faces、np.bool8等调用需适配 |
| Isaac Gym | 独立PhysX验证器 | 未安装，也不为了复现创建旧环境；用Arena/Isaac Lab重写验证协议并标差异 |
| ManifoldPlus/CoACD | manifold修复与凸分解 | 不运行其构建/安装；本轮M2程序化物体不需要这些完整数据流程 |

## 资产获取范围

论文代码及随仓库带入的MJCF/mesh/小型checkpoint保留在 research-repos，不复制进 src。
未下载完整DexGraspNet/ShapeNet/MultiDex数据集，没有运行资产转换脚本。
GenDexGrasp 已有约2.8MB的四份checkpoint，但其外部 `data/urdf`、物体和完整IsaacGym资产包未随源码下载齐全。
DexGraspNet2 的数据、场景和训练checkpoint需要另外下载，本轮未执行。
缺失模块不等于资产缺失，两种阻塞分别记录。

## 授权与归属记录

| 来源 | 已看到的许可证据 | 对迁移的实际约束 |
|---|---|---|
| DexGraspNet | README License：工作与数据CC BY-NC4.0；主要Python文件有作者声明 | 不将其代码/数据重新标成Apache/MIT或声称商用授权；组件文档保留作者、固定commit和来源 |
| GenDexGrasp | 此commit的tracked文件未找到LICENSE/COPYING/NOTICE，README没有许可条款 | 有公开源码不等于明确再分发授权；本轮只分析，不直接复制其源码或权重到src |
| DexGraspNet2 | README License：工作与数据CC BY-NC4.0 | 不移植整套训练/权重并混入通用许可；先记录算法与依赖差异 |
| TorchSDF0.1.0 | 根LICENSE是Apache2.0；README说明源自Kaolin | 若以后复制其CUDA代码，应逐文件检查版权/第三方片段并保留许可证/归属；本轮未复制或编译 |
| vendored pytorch_kinematics | setup.py写MIT | setup元数据不能替代逐文件license与修改归属核查；本轮不复制其整包 |
| OpenAI Shadow模型 | `grasp_generation/open_ai_assets/LICENSE.md`：ShadowRobot来源，含Vikash Kumar Apache2.0声明 | 保留独立模型来源；不能据此替其他目录的全部mesh作许可保证 |
| Allegro分支模型 | `allegro_hand_description/manifest.xml`标BSD | 具体mesh出处及完整BSD文本仍需逐项确认；不在本轮再分发模型 |
| ShapeNetCore/Sem、MuJoCo scanned objects、DDG | asset_process README链接到各原始来源 | 原始资源条件独立于生成代码许可，不自动打包资产进入我们的开源仓库 |
| 当前NVIDIA USD | 官方Isaac Sim资产来源 | 继续使用现有下载缓存与来源信息；不从源码许可证推断模型再分发许可 |

这是本次源码许可记录，不替代针对具体发布/商业用途的许可核验。
算法公式的独立实现与复制代码需区分，且不能仅因重写就宣称脱离所有原始授权限制。
