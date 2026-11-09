# 复现状态

## 原论文完整复现：未完成

没有执行完整Shadow/Allegro候选生成，没有下载完整物体数据，没有运行原IsaacGym验证器，
也没有产生可宣称为DexGraspNet的稳定抓取数据集或论文可比较成功率。

## 源码研究：已完成本轮要求

已追踪生成、初始化、可微手/物体模型、五项能量、退火优化、后处理、六方向验证、
资产提取/归一化/凸分解、可视化测试和vendored FK测试。
已读取allegro分支以及TorchSDF0.1.0的forward/backward，记录固定commit和工作树状态。
额外核对GenDexGrasp、DexGraspNet2和本机Arena/IsaacLab接入接口。

## 算法组件迁移：在技术报告之后进行

本报告先建立源码依据，再实现组件；具体完成的迁移文件、对照测试和边界记录在
同目录 `migration_results.md`（若尚不存在，说明仍未完成组件迁移验收）。
只允许把经实际数值/梯度/随机接受对照的内容记为已迁移。

## 与只有接口的区别

原来的 `GraspGenerator`、`GraspValidator` 是抽象接口，不含完整算法。
新数学组件即使与原能量/提案一致，也不自动意味着hand/object几何backend和物理验证已完成。
M2零动作加载成功与几何采样结果保持单独命名，不能覆盖此状态表。
