# 安装与首次运行

DexterousLab复用 **IsaacLab-Arena的Python环境**。仓库包含代码、配置与文档；Isaac Sim、GPU驱动、机器人模型、数据集和资产缓存不随Git克隆下载。

## 1. 选择你的情况

| 情况 | 从哪里开始 |
|---|---|
| 当前GPUFree服务器，Arena与DexterousLab均已存在 | 第2节，跳过克隆 |
| 已有兼容的Arena `.venv`，尚未下载DexterousLab | 第2节，先克隆项目 |
| 全新Linux机器，没有Arena环境 | 第3节，再返回第2节 |

## 2. 复用已有环境（当前服务器已验证）

新用户首次获取代码：

```bash
cd /root/gpufree-data
git clone https://github.com/ShunZuo-AI/DexterousLab.git
```

已有 `/root/gpufree-data/DexterousLab` 时跳过上面的命令，直接运行：

```bash
cd /root/gpufree-data/DexterousLab
export DEXLAB_ARENA_ROOT=/root/gpufree-data/IsaacLab-Arena
export PATH="$PWD/scripts:$PATH"

# 检查解释器、依赖版本、GPU以及CUDA矩阵运算
dexlab doctor

# 查看配置，并在不启动仿真的情况下核对组合
dexlab assets list
dexlab scene run --hand allegro --object cube --physics physx --dry-run

# 单环境、20步零动作冒烟测试
dexlab scene run --hand allegro --object cube --physics physx --steps 20
```

`doctor` 应正常退出并输出 `ready: true`。冒烟测试应报告完成请求步数；这不表示抓取成功。首次场景运行可能需要联网下载官方USD及其依赖。

启动器 `scripts/dexlab` 会自动设置 `PYTHONPATH` 和Torch动态库路径，使用 `$DEXLAB_ARENA_ROOT/.venv/bin/python`。无需 `pip install -e .`、`uv sync` 或新建conda环境。当前包的 `dependencies=[]` 并不表示运行时没有依赖，而是依赖已有Arena环境；独立wheel安装尚未验收。

上述环境变量只对当前终端有效，换终端后重新执行两条 `export`。项目可放在其他目录，但资产清单中的本地路径与历史实验记录不会自动迁移；建议首先验证程序化Cube场景。

## 3. 全新机器：先准备Arena环境

这一节是依据所读上游源码整理的安装路线，**本轮未在全新机器上重做安装验收**。需要Linux、可用的NVIDIA GPU与驱动、Git和uv；显存、驱动及系统要求应以对应版本的Isaac Sim官方文档为准。

- [Arena安装源码文档（本项目参考commit）](https://github.com/isaac-sim/IsaacLab-Arena/blob/5fb3bd8a639578d46f4b5ed67b9b5239e1281b9a/docs/pages/quickstart/installation.rst)
- [Isaac Sim 6.2硬件与系统要求](https://docs.isaacsim.omniverse.nvidia.com/6.2.0/installation/requirements.html)
- [uv官方安装说明](https://docs.astral.sh/uv/getting-started/installation/)

仅在**没有现成Arena环境的新目录**中执行以下命令。普通用户可将工作目录改为自己的可写数据盘路径：

```bash
mkdir -p /root/gpufree-data
cd /root/gpufree-data
git clone https://github.com/isaac-sim/IsaacLab-Arena.git
cd IsaacLab-Arena

# 固定源码接口版本，避免跟随main的API变化
git checkout 5fb3bd8a639578d46f4b5ed67b9b5239e1281b9a
git submodule update --init --recursive

# 仅供首次安装，会下载较大的SDK与依赖并创建Arena/.venv
uv sync --extra dev
```

阅读并同意Isaac Sim EULA后，按照上游指引验证环境：

```bash
cd /root/gpufree-data/IsaacLab-Arena
export OMNI_KIT_ACCEPT_EULA=YES ACCEPT_EULA=Y
export LD_LIBRARY_PATH="$PWD/.venv/lib/python3.12/site-packages/torch/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
.venv/bin/python -c "import isaaclab_arena; print(isaaclab_arena.__file__)"
.venv/bin/python isaaclab_arena/evaluation/policy_runner.py \
  --policy_type zero_action --num_steps 20 cube_goal_pose
```

通过后返回第2节获取DexterousLab，始终复用这个 `.venv`。**不要在当前已验证的GPUFree环境重新执行上述同步步骤**；它可能改变现有Torch与仿真依赖。Docker用户请遵循同一commit的上游Docker指引，本文默认DexterousLab启动脚本的原生 `.venv` 路线。

## 4. 当前已验证环境记录

以下为2026-11-10对本机的读取结果，不是对任意机器的自动兼容承诺：

| 项目 | 本机记录 |
|---|---|
| 系统 / GPU | Ubuntu 22.04.5 / NVIDIA L40S |
| Python | 3.12，Arena `.venv` |
| Isaac Sim分发版本 | `6.2.0.0` |
| Isaac Lab源码commit | `e3f7d9ff1f5d7f8280de3ece9000b7117f66bcf4` |
| Arena源码commit | `5fb3bd8a639578d46f4b5ed67b9b5239e1281b9a` |
| PyTorch | `2.11.0+cu130` |
| 包元数据 | `isaaclab=28.0.0`、`isaaclab_arena=0.3.0` |

源码README描述Isaac Lab 3.0接口，但本机安装包元数据返回 `28.0.0`；保留两项实测信息，不能仅按包版本号判断接口兼容。当前Arena checkout的锁文件存在本地修改，因此“固定上游commit后执行uv sync”不保证得到与本机完全相同的依赖集。遇到安装差异，应先检查实际版本和导入路径，不直接降级或替换现有Torch。

## 5. 资产、录制与测试

- `assets/manifests/` 是来源与历史状态清单，不是已下载模型。克隆仓库不会获得 `assets/hands/`、`assets/objects/`、`assets/cache/`、`research-repos/`、`models/`、`datasets/` 或 `outputs/`。
- 初始Allegro / Shadow场景使用官方资产与程序化物体。其他厂商资产的提取、许可、转换和验证见 [资产报告](asset_aggregation/expanded-report.md)。清单里的 `passed` 是已有服务器记录，不证明新机器资产存在。
- 抓取实验脚本当前要求项目内已有官方资产缓存；先跑通场景并核对缓存，不要直接复制其他机器的绝对路径。
- `--record-video` 需要系统 `ffmpeg`，使用Kit离屏渲染；合成对照视频还需要 `ffprobe`。[实际录制命令](experiments/motion-video-20261110.md)。
- `assets preview` 和单独的 `--render` 桌面预览需要有效的图形会话 / DISPLAY。

```bash
cd /root/gpufree-data/DexterousLab
export DEXLAB_ARENA_ROOT=/root/gpufree-data/IsaacLab-Arena
export LD_LIBRARY_PATH="$DEXLAB_ARENA_ROOT/.venv/lib/python3.12/site-packages/torch/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
"$DEXLAB_ARENA_ROOT/.venv/bin/python" -m pytest -q -p no:cacheprovider
```

共享环境已有pytest等测试依赖。本机111项测试通过；参考仓库不存在时，部分源码对照测试会跳过。测试通过不替代GPU场景验收。

## 6. 常见问题

| 现象 | 处理 |
|---|---|
| `dexlab: command not found` | 在项目根执行 `export PATH="$PWD/scripts:$PATH"`，或使用 `./scripts/dexlab` |
| 找不到共享解释器 | 检查 `DEXLAB_ARENA_ROOT` 是否指向含 `.venv/bin/python` 的Arena目录 |
| CUDA矩阵运算 / 动态库错误 | 优先通过启动器运行；直接调用Python时设置上文Torch `LD_LIBRARY_PATH` |
| 官方资产下载失败 | 检查网络、USD依赖与本地缓存；场景加载失败不能记为验证通过 |
| 其他手型有清单但运行不了 | 先核验本地资产与转换状态；桌面控制目前只适配Allegro和Shadow |
| 云桌面窗口崩溃 | 运动录制使用 `--record-video` 离屏路径；保留日志，不更换驱动或重装SDK碰运气 |

下一步：[运行与配置](reference/usage-details.md) · [实验报告](experiments/first_grasp_experiment.md) · [视频录制](experiments/motion-video-20261110.md)。
