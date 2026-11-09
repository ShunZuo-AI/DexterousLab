# 与实际代码一致的公式与梯度

来源：DexGraspNet 主分支 `utils/{energy,hand_model,object_model,optimizer,rot6d}.py`，
版本见上级 source_manifest。这里重述实际代码运算，不声称复述了论文所有理论条件。

## 变量与坐标

对批次候选 b，连续变量 `q_b=(t_b,a_b,theta_b)`，维度3+6+22；离散接触索引 `z_bi`，默认4个。
`a` 是旋转前两列的6维表示，经过 robust 正交化变成 R。
手局部候选点经过 link FK 和掌变换：

\[
c_{bi}=R_b\,T_{H,L(z_{bi})}(\theta_b)\,p_{z_{bi}}+t_b.
\]

物体位于合成坐标原点，按 s 缩放。距离统一为**内部正、外部负**：
`ObjectModel.cal_distance` 实际取 `s * sqrt(squared_distance + 1e-8) * (-sign)`。
返回的 `normal` 为 TorchSDF 查询方向乘 sign，不能与内部正 SDF 的梯度符号混淆。

## 五项能量

\[
E=E_{fc}+100E_{dis}+100E_{pen}+10E_{spen}+E_{joints}.
\]

| 项 | 实际公式 | 梯度路径和边界 |
|---|---|---|
| 接触距离 | `E_dis = sum_i abs(phi_O(c_i))` | TorchSDF的query梯度 → c_i → FK、R、t；不对sign、面顶点或离散索引求导 |
| 力闭合残差 | `E_fc = ||sum_i n_i||² + ||sum_i c_i × n_i||²` | 原实现n_i是detach的局部常量；力项此步没有法向变化梯度，力矩项仍对c_i求导 |
| 物体穿入手 | `E_pen = sum_j max(phi_H(s p_j),0)` | 物体采样点固定；手SDF经过逆FK、逆掌变换对手参数求导 |
| 手自碰撞 | `E_spen = sum_(k,l) max(0.02 - ||u_k-u_l||,0)`，排除距离<1e-6的项 | u经过FK；有序点对求和，不是全网格碰撞体积 |
| 关节越界 | `sum_d max(theta_d-upper_d,0)+max(lower_d-theta_d,0)` | 分段线性，对theta直接求导；不是clamp或平方罚 |

`energy.py` 使用堆叠 identity/skew blocks 的矩阵乘法表达力与力矩；
由于它采用行向量，力矩符号可与列向量叉乘写法相反，但平方范数相同。
这是 force-closure 的可微残差代理，不是严格摩擦锥扳手空间/正张成的完整证明。
没有从此公式得到真实接触力、摩擦系数或抓取成功概率。

## SDF 的实际梯度

补充读取 `/root/gpufree-data/research-repos/TorchSDF` 的0.1.0版本。
`torchsdf/sdf.py:_UnbatchedTriangleDistanceCuda` 返回顺序为
`(squared_distance, sign, normal, closest_point)`，以实际代码为准。
forward 明确 `mark_non_differentiable(sign, normals, closest_points)`；backward 仅输出点坐标梯度，
`grad_face_vertices=None`。
所以若新 backend 提供可微法向，默认需要 detach 它以保持原行为；打开法向梯度必须单独标记为算法差异。

HandModel 的 capsule 分支先构造 detach 后的最近轴线点，然后计算 `radius - norm(x-nearest)`；
掌部 mesh 也通过 query 的逆变换把距离梯度送回手的关节，而不是求 mesh 顶点梯度。
`max` union、`abs`、hinge 和最近三角形切换处只有分段梯度；自碰撞在重合点附近有特殊屏蔽。

## 原优化器，而不是标准 Adam/RMSProp 默认值

记第k次提案前梯度为g，v是全批次共享的每坐标均方值：

\[
v_k=\mu\,\operatorname{mean}_b(g_{kb}^{2})+(1-\mu)v_{k-1},\quad\mu=0.98.
\]
\[
\eta_k=0.005\,0.95^{\lfloor k/50\rfloor},\qquad
q'_b=q_b-\eta_k\,g_b/(\sqrt{v_k}+10^{-6}).
\]

提案后 step 增1，再计算温度：

\[
T=18\,0.95^{\lfloor(k+1)/30\rfloor},\qquad
P(accept)=\min(1,\exp((E_b-E'_b)/T)).
\]

源码没有显式min，但与rand∈[0,1)比较时效果等价（极端值可能overflow）。
接触索引以0.5概率从全部手候选随机重选；连续参数更新不含额外高斯噪声。
拒绝时恢复该样本的q、z、掌变换、contact点、旧梯度，并重新FK；不回滚v或时间。
批次共享v意味着改变batch size会改变轨迹，不能在“等价复现”中随意改成每样本独立v。

## 对照测试发现的图历史细节

原 `Annealing.try_step` 将 `old_grad_hand_pose` 直接绑定到旧pose的 `.grad`，不是clone。
提案也没有detach，新的backward仍经过旧pose，因此旧 `.grad` 会被累加。
在reject路径，源码恢复的所谓旧梯度可能已经包含新反传的累积值。
原实验脚本的 `retain_graph=True` 与这一行为相配套。
我们的 `AnnealingConfig.preserve_source_graph=True` 默认保留它，并用多步原源码对照验证。
设为False会使用leaf提案、避免跨步图历史；这是**显式算法实现差异**，不宣称逐步轨迹等价。

新数学组件保留输入tensor精度，便于double有限差分测试；原energy.py会强制部分项为float32。
float32路径作原源码数值/梯度对照，double路径只用于我们组件的数值梯度检查。

## 筛选与动力学边界

Logger几何阈值与最终Isaac Gym六方向接触筛选是两层不同东西。
验证代码最后的接触存在性、默认摩擦3和额外关节微调构成协议的一部分。
替换成Isaac Lab抬升/保持/外力试验可以更适合我们的研究，但必须标为适配后的验证协议，不能声称与原成功率直接等价。
