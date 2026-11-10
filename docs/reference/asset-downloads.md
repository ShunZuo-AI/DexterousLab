# 物体资产下载脚本

统一入口：`dexlab assets download <source>`。不安装数据集的环境，不执行论文安装脚本，不默认下载全库。现有 `download-ycb`、`prepare-ycb` 命令保持兼容。

| 来源 | 下载命令 | 下载内容 |
|---|---|---|
| YCB | `dexlab assets download ycb --files cracker_box mustard_bottle mug` | 已验证的三个小样本，含解包与清单注册 |
| DexGraspNet | `dexlab assets download dexgraspnet --files meshdata.tar.gz` | 从作者镜像文件索引选择物体包 |
| GenDexGrasp | `dexlab assets download gendexgrasp --files data.zip` | 作者README指向的物体与机器人数据包 |
| DexGraspNet 2.0 | `dexlab assets download dexgraspnet2 --files meshdata.tar.gz` | 作者Hugging Face物体包 |
| OakInk | `dexlab assets download oakink --files shape/OakInkObjectsV2.zip` | 交互物体包；虚拟物体可另选 |
| Objaverse-XL | `dexlab assets download objaverse-xl --manifest selected-objects.json` | 由带许可、来源和SHA-256的清单选定的单个模型文件 |

## 独立脚本入口

所有来源共用一个脚本，避免六套重复下载逻辑。参数与CLI相同，使用项目已有Python：

```bash
"$DEXLAB_ARENA_ROOT/.venv/bin/python" scripts/download_object_assets.py dexgraspnet --list-files
"$DEXLAB_ARENA_ROOT/.venv/bin/python" scripts/download_object_assets.py oakink --files shape/metaV2.zip
```

源码：`scripts/download_object_assets.py`、`src/dexterous_lab/assets/downloads.py`。来源地址和文件ID集中在 `configs/downloads/sources.json`，不是在下载实现中散落硬编码。

## 先列文件，再选择

```bash
dexlab assets download dexgraspnet --list-files
dexlab assets download gendexgrasp --list-files
dexlab assets download dexgraspnet2 --list-files
dexlab assets download oakink --list-files

dexlab assets download dexgraspnet2 --files meshdata.tar.gz --dry-run
```

`--list-files`和`--dry-run`会获取索引，但不传输模型正文。除YCB小样本外，必须显式选择文件或Objaverse清单，不会隐式拉取全部数据。`--max-gb 8`是默认单文件上限；大于上限会失败。已知文件大小时按实际大小检查空间，未知大小时按上限预留，并额外保留2 GiB。

GenDexGrasp的 `data.zip` 是物体和手型资源；`MultiDex.zip` 是抓取数据；`env.zip` 是原Isaac Gym任务与资产。下载它们不表示这些旧任务已经兼容Isaac Lab。

## 网络与镜像

默认使用Hugging Face官方域名。当前服务器直连连接重置，已显式使用 `hf-mirror.com` 验证索引与小文件传输。需要镜像时：

```bash
dexlab assets download dexgraspnet2 --hf-endpoint https://hf-mirror.com --files meshdata.tar.gz
dexlab assets download oakink --hf-endpoint https://hf-mirror.com --files shape/OakInkObjectsV2.zip
```

也可设置 `HF_ENDPOINT`。脚本记录镜像地址、官方规范地址、固定commit和上游SHA-256；没有静默切换镜像。Hugging Face索引会先固定当前版本，再用相同版本列文件与下载，避免下载过程中main变化。

DexGraspNet镜像通过其前端实际使用的 `/files/dl-release/DexGraspNet-ICRA2023/` JSON API读取列表。若作者改版，可从官方页面取得具体文件链接，用 `--url`和一个明确文件名指定，不猜测文件路径：

```text
dexlab assets download dexgraspnet --files meshdata.tar.gz --url <official-archive-https-url>
```

GenDexGrasp处理Google Drive公开下载的确认表单。登录、配额或无权限页面会报错，不能把HTML存成zip；本机Google Drive当前网络不可达。`--url`也可为GenDexGrasp指定作者提供的可直接下载链接；网盘分享页、百度提取码页不等于二进制直链。脚本不会绕过身份或权限限制。

## Objaverse-XL：选择物体再下载

Objaverse-XL来自多个站点，单个物体各有许可。先用[官方工具和元数据](https://github.com/allenai/objaverse-xl)选择物体并取得真实文件链接、SHA-256、作者页面与单模型许可，再导出如下JSON。以下是字段模板，不含可执行的示例资产：

```json
[
  {
    "name": "selected-object.glb",
    "url": "https://<real-host>/<actual-model-file>",
    "sha256": "<64-character-sha256-from-official-metadata>",
    "license": "<license-of-this-object>",
    "source_page": "https://<original-author-page>",
    "bytes": 12345
  }
]
```

`bytes`可省略，其他字段必须填写真实值。文件名相对于下载目录；不得使用绝对路径或`..`。执行：

```bash
dexlab assets download objaverse-xl --manifest selected-objects.json --dry-run
dexlab assets download objaverse-xl --manifest selected-objects.json --max-gb 1
```

这是Objaverse-XL**选定模型的直接下载适配**，不是官方SDK全量metadata采集器。它不解析parquet、不替用户申请Polycam权限、不自动克隆整仓库、不合并多文件依赖。带外部纹理的模型需把依赖一起列入清单；GLB等自包含模型更便于首批验证。没有清单时明确报错，绝不下载随机模型冒充选定数据。

## 保存位置与校验

YCB沿用 `assets/objects/ycb/<物体>/raw`，可继续用 `prepare-ycb`与`scene run`。

其他来源默认保存到 `assets/objects/<source>/downloads/<文件名>.download/`。每个目录包含：

- `payload`：原始文件字节，未解压，扩展名可从目录名得知。
- `provenance.json`：请求、许可、来源、固定版本、字节数、SHA-256和下载时间。

下载未完成时写入独立临时目录，失败只清理本次临时目录。只有长度及可用的上游校验和通过后才发布目录。重复执行会核对本地哈希和请求；已有用户文件、改动过的模型或不同版本不会覆盖。上游没有SHA-256时明确记录仅测量本地哈希，不能称为通过发布者校验。

可以用 `--output-dir`指定项目内另一个保存目录。YCB小样本复用既有目录，不接受该参数。不支持断点续传，失败后重新执行；没有把不完整数据计为成功。新来源的归档不会自动解压或注册为仿真资产，避免把下载成功与可仿真混为一谈。

## 许可与验证边界

YCB为CC BY 4.0；DexGraspNet系列为CC BY-NC 4.0；OakInk数据页为CC BY-NC-SA 3.0；Objaverse-XL整体数据库与逐模型许可分别记录。GenDexGrasp公开包未找到统一数据许可，仍需保留YCB、ContactDB及其他上游归属。工具代码许可不覆盖这些模型与数据。

[2026-11-11实测记录](../experiments/asset_downloaders_20261111.md)区分实际下载、只读取索引、网络阻塞和离线测试。本次没有运行这些新数据集的GPU仿真；YCB三个样本的已有仿真结果见[报告](../experiments/ycb_objects_20261111.md)。
