# 六类物体来源下载入口验证 · 2026-11-11

新增 `dexlab assets download <source>`，支持YCB、DexGraspNet、GenDexGrasp、DexGraspNet2、OakInk、Objaverse-XL。独立脚本 `scripts/download_object_assets.py`复用同一个实现。未安装额外依赖，未运行论文安装脚本，未修改仿真或抓取算法。

## 实际执行

| 来源 | 本机执行及结果 | 未完成的验证 |
|---|---|---|
| YCB | 新统一命令对已有Mug执行校验，返回already_present | 本次未重新传输既有模型 |
| DexGraspNet | 实际读取作者镜像JSON索引，找到 `meshdata.tar.gz` 345,939,166字节；Range请求取得开头1024字节，HTTP206且gzip文件头正确；dry-run通过 | 未下载完整345.9 MB归档 |
| GenDexGrasp | 按作者README的Google Drive ID列出 `data.zip`、`MultiDex.zip`、`env.zip`；CLI与独立脚本均能列出并生成计划 | Google Drive本机返回Network is unreachable；未下载真实包。确认表单与错误HTML拒绝由离线测试覆盖 |
| DexGraspNet2 | 官方域名连接重置；显式使用hf-mirror.com取得固定版本、21项仓库条目中的归档及LFS哈希，meshdata计划成功 | 未下载4.62 GB模型归档 |
| OakInk | 显式使用镜像获取固定版本；实际下载 `shape/metaV2.zip` 15,447字节，匹配上游SHA-256；重复执行返回already_present | 下载的是元数据，不是物体网格；未下载约1 GB物体包 |
| Objaverse-XL | 强制显式选择清单；真实传输逻辑用模拟文件测试，验证逐模型许可、来源、预期哈希和防覆盖 | 未从真实Objaverse元数据选择或下载任何新模型；未实现官方SDK全量采集 |

OakInk实际版本：`c15950e6ceefb1b7ac3a82acc6318ef0f680d71c`。

实际下载文件SHA-256：`8c6ec8ebb98821c589170d98b73ccc84bf1543781b9ac3e4d1e6f01084e73bef`。

保存位置：`assets/objects/oakink/downloads/shape/metaV2.zip.download/payload`；旁边的 `provenance.json`保留官方规范地址、显式镜像URL、固定版本、来源、许可和验证结果。

DexGraspNet2实际版本：`b7dbc0ce452d5ab2eda66016ba22d6a1e25e71a4`。从API取得的文件列表已保存在[证据目录](downloaders-20261111/dexgraspnet2-files.json)。

## 命令

```bash
dexlab assets download ycb --files mug
dexlab assets download dexgraspnet --list-files
dexlab assets download dexgraspnet --files meshdata.tar.gz --dry-run
dexlab assets download gendexgrasp --files data.zip --dry-run
dexlab assets download dexgraspnet2 --hf-endpoint https://hf-mirror.com --list-files
dexlab assets download dexgraspnet2 --hf-endpoint https://hf-mirror.com --files meshdata.tar.gz --dry-run
dexlab assets download oakink --hf-endpoint https://hf-mirror.com --list-files
dexlab assets download oakink --hf-endpoint https://hf-mirror.com --files shape/metaV2.zip --max-gb 1
"$DEXLAB_ARENA_ROOT/.venv/bin/python" scripts/download_object_assets.py gendexgrasp --list-files
```

没有给Objaverse填入虚构的模型ID。清单格式与使用方式见[下载指南](../reference/asset-downloads.md#objaverse-xl选择物体再下载)。

## 测试范围

**174 passed，3.27秒**。[完整单元测试日志](downloaders-20261111/tests.log)包括：

- 六类来源的CLI参数和计划，HF固定版本及镜像规范地址，作者镜像API解析和GenDexGrasp文件ID。
- 二进制保存、上游哈希、长度与大小上限、空文件、被改动文件与已有用户文件的保护。
- HTML登录/错误页与错误标记的HTML内容拒绝，公开Google Drive确认表单处理。
- Objaverse逐模型字段、选择清单下载适配、输出路径及符号链接检查。
- 既有项目配置、候选数据与论文数学组件测试继续运行。

本次不涉及仿真逻辑，因此没有新增GPU运行。网络不可达、索引读取、元数据下载、模型下载、物理验证与抓取成功分别记录，不能互相替代。

新下载器按文件下载原始字节并存储provenance，不解压大型归档、不自动转USD、不自动更新物理验证状态。YCB继续走既有专用下载和准备链路。
