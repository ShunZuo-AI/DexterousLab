# 数据盘存储约定

项目代码、项目使用的下载资产、模型、数据集和输出以 `/root/gpufree-data` 为存储根。

```text
/root/gpufree-data/
├── DexterousLab/          项目代码、配置、文档与 outputs
├── IsaacLab-Arena/        现有官方 checkout 与唯一 .venv
├── assets/cache/          官方资产 HTTP 镜像、重写后的 USD 依赖副本与临时文件
├── models/huggingface/    后续模型缓存（HF_HOME）
├── datasets/             后续数据集
├── .cache/               SDK、CUDA、Torch 缓存
│   ├── kit/              Kit portable root，包含其 cache/data/logs
│   ├── omniverse/        原 .nvidia-omniverse 数据
│   └── legacy/           保留的旧 SDK 缓存
├── .config/              子进程配置
├── .local/               子进程 data/state
└── .uv-cache/            现有 uv 包缓存
```

`runtime_environment()` 在启动仿真子进程之前设置 TMPDIR、XDG_*、CUDA_CACHE_PATH、
TORCH_HOME、HF_HOME、UV_CACHE_DIR 和 Omniverse Hub 缓存路径。
当前 Isaac Lab 的 `retrieve_file_path()` 默认使用 `tempfile.gettempdir()`，因此资产镜像和
重写后的 USD 副本都写入 `assets/cache`。没有修改上游函数。
Worker 通过已存在的 `kit_args` 接口指定数据盘上的 `--portable-root`。

56 个旧资产/SDK 缓存目录已从 `/tmp` 或 `/root` 迁移到数据盘。
原路径变为兼容软链接，保留旧 USD 的绝对引用；没有删除旧资产。
详细逐目录对应关系见 `storage-migration.json`。
此前生成的项目初版临时代码归档在 `code/dexlab-build-initial`，
此前临时日志归档在 `DexterousLab/docs/initial-session-artifacts`。
正式工作代码始终为 `DexterousLab/src`。

共享 `.venv` 保持不变，不迁移系统安装或系统 Python 基础解释器。
该 `.venv/bin/python` 原本指向 `/root/.local/share/uv/python/...` 的基础解释器；
它属于已有运行时，而不是新建的项目代码或新建 Python 环境。
没有更改 HOME，也没有把整个用户主目录搬到数据盘。

官方资产 URL 保留为来源；本次整理的是项目实际使用的下载副本，不代表完整 NVIDIA 官方资产库已离线下载。
手动启动官方脚本或其他程序不会自动应用 DexterousLab 的子进程配置。

存储配置修改后，Allegro+Cube 的 100 步仿真通过，Kit 实际创建了数据盘上的 cache/data/logs，
资产实际创建了数据盘上的 `isaaclab_usd_*` 副本；单元测试 70 项通过。
相关命令输出见 `storage-verification-command.log`，doctor 路径清单见 `storage-doctor.json`。
旧缓存迁移完成后，Shadow+Cube 的 20 步复验也通过，命令输出为 `storage-shadow-command.log`。
