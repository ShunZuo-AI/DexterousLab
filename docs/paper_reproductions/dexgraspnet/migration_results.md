# 已迁移组件与实际验收

本轮顺序：先clone并阅读原始源码、提交本目录五份技术报告和其他仓库报告，再实现下列库组件。
参考源码保持原样，未运行其安装脚本，也未创建任何环境。

## 已实现，不是只有接口

| 新代码 | 实际能力 | 依据与状态 |
|---|---|---|
| `src/dexterous_lab/grasp_generation/dexgraspnet/energy.py` | 五项能量、默认权重、自碰撞关键点罚项、原model API适配 | 主分支energy.py与hand_model.py数学组件移植；不含SDF/FK |
| `src/dexterous_lab/grasp_generation/dexgraspnet/optimizer.py` | 连续位姿提案、离散索引重采样、温度/步长衰减、Metropolis接受与回滚 | 原Annealing行为；默认保留原图历史；显式可切换leaf模式 |
| `src/dexterous_lab/grasp_generation/dexgraspnet/optimization.py` | 给定已初始化可微hand/object模型，执行完整能量优化循环并输出轨迹/最终状态 | 生成脚本中的优化核心；初始化和模型backend仍由调用方提供 |
| `src/dexterous_lab/grasp_execution/dexgraspnet_adapter.py` | 原qpos → 显式frame/joint映射 → GraspCandidate | 位置/坐标适配；不是物理验证器或已校准Shadow控制器 |

无任何“缺失几何就返回零距离/固定法向”的生产fallback，也没有用随机候选冒充完整生成算法。

## 原源码对照结果

`tests/test_dexgraspnet_source_parity.py` 在内存读取并执行固定参考仓库的纯Torch
`energy.py:cal_energy`、`optimizer.py:Annealing`，没有import破坏性入口，也没有在参考目录写pycache。
参考文件SHA256必须与先前分析manifest相符，否则测试失败。

已通过：

- CPU与CUDA：逐项能量、加权总能量、对手参数的梯度与原源码对照，容差rtol/atol=2e-5。
- 六次连续迭代：接触不切换/全部切换两种场景，比较q、索引、梯度、均方历史、accept掩码、energy、温度与步长。
- 明确覆盖reject路径中的原梯度累积；不是只测试能量下降后就声称优化器等价。
- double有限差分验证力矩/接触几何变量的梯度，原法向detach行为单独验证。
- 关键点有序对求和、重合点排除、非有限输入拒绝、异常提案回滚。
- 完整三步模型API调用循环与最终hand/contact状态一致。
- 手掌frame旋转/平移组合、xyzw输出、关节映射覆盖、限位、额外wrist和缺失校准拒绝。

以上使用解析**测试夹具**隔离数学行为，不是实际Shadow FK、mesh SDF、完整接触或仿真成功证明。

## 两种图历史模式

原源码保留旧计算图并存储旧 `.grad` 引用，reject恢复梯度可能包含新backward累加。
迁移时对照测试发现并记录了此细节：

- `preserve_source_graph=True`（默认）：保留源行为，原实现多步对照通过；内存会随图历史增长。
- `preserve_source_graph=False`：每步使用新的leaf提案，避免跨步图历史；行为显式不同，不能称逐步轨迹完全复现。

此外，新组件可保留输入float64作gradcheck，源代码部分项固定float32；float32路径用于源码对照。
随机数使用独立 `torch.Generator`，不重设全进程随机种子。

## 在库中使用

下面是对已初始化backend的接口示例，不是一条目前可直接生成真实Shadow抓取的命令：

```python
from dexterous_lab.grasp_generation.dexgraspnet.optimization import optimize_models
from dexterous_lab.grasp_generation.dexgraspnet.optimizer import AnnealingConfig

result = optimize_models(
    hand_model,
    object_model,
    iterations=100,
    config=AnnealingConfig(preserve_source_graph=True),
    seed=42,
)
```

`hand_model` 必须提供 `set_parameters`、`cal_distance`、`self_penetration`、
`hand_pose[B,9+J]`、`contact_point_indices`、`n_contact_candidates`、`contact_points`、关节limits。
`object_model` 必须提供 `cal_distance`、`object_scale_tensor` 和未应用尺度的 `surface_points_tensor`。
例如原ObjectModel的内部正SDF和法向detach契约必须保持；M2已缩放的米制mesh不能再盲目乘原数据尺度。
`result` 不带物理success，也不直接写入稳定抓取数据集。

## 测试命令和证据

```bash
cd /root/gpufree-data/DexterousLab
TMPDIR=/root/gpufree-data/assets/cache \
PYTHONDONTWRITEBYTECODE=1 \
LD_LIBRARY_PATH=/root/gpufree-data/IsaacLab-Arena/.venv/lib/python3.12/site-packages/torch/lib:${LD_LIBRARY_PATH:-} \
/root/gpufree-data/IsaacLab-Arena/.venv/bin/python -m pytest \
  -q -p no:cacheprovider --junitxml=docs/paper_reproductions/library-tests.xml
```

全库 **92项通过**，包括真实CUDA上的小批次数学对照。完整日志/JUnit：
`../library-tests.log`、`../library-tests.xml`；先前21项组件测试的日志另存于本目录。
本轮没有运行GPU动力学抓取试验，因为物理抓取验证器未实现。

## 完整复现仍缺少什么

1. 用当前可兼容模块实现/适配完整手部可微FK和碰撞几何，与原MJCF/Allegro分支按关键点校准。
2. 原TorchSDF行为的兼容距离backend，含距离符号、法向detach、近表面epsilon与梯度对照。
3. 原初始化流程、完整资产处理/尺度还原，以及实际Shadow/Allegro候选生成验证。
4. 当前Shadow的腱耦合可执行性；源22关节与目标24物理关节/20电机不能直接按名称对应就当作等价。
5. Allegro手掌目标到KUKA的IK、可达性和安装frame处理。
6. IsaacLab独立物理执行/验证协议；若改用抬升/外力保持，必须记录与原六方向最终接触协议的差异。

所以当前状态是**原始算法组件的可验证迁移**，不是完整DexGraspNet复现，也不是完整M3/M4闭环完成。
