# 项目存储布局

代码、项目资产、参考源码和运行数据统一存放在 `/root/gpufree-data/DexterousLab/`：

```text
DexterousLab/
  src/                    DexterousLab 自有代码
  configs/                机器人、物体、场景和实验配置
  scripts/                启动与资产管理脚本
  assets/
    manifests/            可纳入 Git 的资产清单
    hands/                按厂商、型号、版本保存的手资产
    objects/              物体资产
    cache/                USD 下载和导入缓存
  research-repos/         第三方参考源码，不运行其安装脚本
  models/                 模型与权重
  datasets/               数据集
  outputs/                实验运行目录
  .cache/                 Kit、CUDA、Torch、Warp、Omniverse 缓存
  .config/                项目进程使用的配置
  .local/                 项目进程使用的数据及状态
  docs/                   文档、测试结果和迁移记录
  tests/                  项目测试
```

唯一共享 Python 环境仍为 `/root/gpufree-data/IsaacLab-Arena/.venv`；官方 Arena/Isaac Lab 源码保持原位置。`research-repos/IsaacLab-Arena` 和 `research-repos/IsaacLab` 是指向这两项共享依赖的链接，不是重新复制或安装的仓库。

本次在同一数据盘内移动资产和参考源码，没有删除模型文件。旧的 `/root/gpufree-data/dexlab-assets`、`research-repos`、`models`、`datasets` 和原先的缓存/配置目录保留兼容链接。历史 USD、导入配置、日志与哈希文件中的绝对路径因此继续有效；没有批量改写原始文件或历史证据。当前资产清单和 Isaac Lab 集成配置使用项目内新路径。

迁移映射见 [storage-layout-migration.json](storage-layout-migration.json)，测试日志见 [storage-migration-tests.log](storage-migration-tests.log)，真实启动日志见 [storage-migration-simulation.log](storage-migration-simulation.log)。资产、缓存、参考源码、数据集和权重目录已加入 `.gitignore`，清单与自有代码继续保留在项目 Git 范围内。

```bash
cd /root/gpufree-data/DexterousLab
./scripts/dexlab doctor
./scripts/dexlab assets inspect --id unitree/dex3_1/right
./scripts/dexlab assets validate --id unitree/dex3_1/right --steps 100
```
