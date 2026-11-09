# GitHub 项目发布说明

## 仓库范围

DexterousLab 作为独立仓库发布。代码、配置、测试、README、研究文档、资产来源清单和展示图片属于版本管理范围。

以下内容由 `.gitignore` 排除，继续保留在当前服务器：

- 机器人与物体的原始 / 转换资产：`assets/hands/`、`assets/objects/`。
- 仿真缓存与SDK缓存：`assets/cache/`、`.cache/`、`.local/`。
- 模型、数据集、运行输出：`models/`、`datasets/`、`outputs/`。
- 论文参考仓库：`research-repos/`。
- Python环境、本地编辑器配置、环境变量文件和私钥。

独立克隆只包含源代码与文档，不包含共享 Isaac Sim / Isaac Lab 环境，也不包含大型资产。清单中的 `passed` 表示已有服务器实验记录，不证明克隆后本机已经拥有相应资产。

## 首次上传

先确认 GitHub 仓库地址、可见性及提交者身份。创建空仓库时不额外初始化README，以便保留本项目的已有文件。

GitHub认证由服务器本地凭据管理器、GitHub CLI登录或SSH提供。不要把访问令牌放入远端URL、项目文件或聊天消息。

准备好的文件可用以下命令复核：

```bash
git status --short
git diff --cached --stat
git diff --cached --check
```

仓库尚无首次提交时，确认身份后执行：

```bash
git config --local user.name "YOUR_NAME"
git config --local user.email "YOUR_GITHUB_EMAIL_OR_NOREPLY_EMAIL"
git branch -m main
git commit -s -m "Initialize DexterousLab research framework"
git remote add origin git@github.com:YOUR_GITHUB_USERNAME/DexterousLab.git
git push -u origin main
```

这些命令针对首次发布；若已有 `origin` 或已有提交，应先检查当前状态，不能重复覆盖或强制推送。

## 研究状态与来源

README 保留当前实验结果与功能边界。共享环境下的测试不等于全新机器的安装验收；参考源码缺失时，相关源码对照测试会跳过。

第一方代码尚未指定独立根许可证。第三方模型、论文组件和官方商品图片各自保留来源与许可说明，不能因上传到GitHub就将它们统一声明为MIT或Apache许可证。相关记录见 [算法归属](paper_reproductions/ATTRIBUTION.md) 与 [商品图片来源](media/official-products/README.md)。
