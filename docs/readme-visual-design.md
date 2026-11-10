# README 视觉设计

本版参考CVPR研究项目README的内容组织方式：居中品牌与导航、醒目的展示图、快速开始、实验图表、折叠细节与来源记录。字体和图标为DexterousLab独立设计，没有复制参考项目的标识或研究图像，也不表示本项目已被CVPR录用。

当前首页包含News、项目介绍、核心功能、快速开始、实验结果和文档入口。主标题使用此前的居中蓝色艺术字图片，导航使用可点击的蓝白圆角胶囊按钮，章节使用文字标题；详细说明通过docs链接查阅。

## 更新News

在根目录README的 `## 📰 News` 下按日期倒序添加真实消息，格式为 `- **YYYY-MM-DD** — 消息内容。`。优先记录版本发布、实验进展、数据或论文更新，不把计划写成已完成事项。

## 参考项目

| 项目 | 实际阅读的README | 文件版本（Git blob SHA） |
|---|---|---|
| facebookresearch/vggt | [README](https://github.com/facebookresearch/vggt/blob/main/README.md) | `fc04f23891e77e71b6c2b6c8e6716ee573dd8fa1` |
| naver/dust3r | [README](https://github.com/naver/dust3r/blob/main/README.md) | `858d00b9dad1289f30c3e3533875a6a9808b92f8` |
| CUT3R/CUT3R | [README](https://github.com/CUT3R/CUT3R/blob/main/README.md) | `2d06fbcfdde95d7e25173f41efc1efedb82e7307` |

## 视觉规范

- 正标题：顶部居中的 `readme-style/wordmark.svg` 艺术字图片，采用衬线斜体和深浅蓝配色，背景为直角。
- 子标题：全部使用可选择、可复制的Markdown文字，主要章节配简洁图标；步骤标题也使用文字，不使用标题图片。
- 图标：项目内绘制的轨道、火箭、灵巧手、烧瓶、层级、盾牌和书籍线条图标。
- 配色：深蓝 `#173d68`、强调蓝 `#4d88c6`、灰蓝 `#7893ae`、浅蓝白底。
- 排版：章节标题、数字概览和页脚使用文字；快捷导航使用独立SVG圆角按钮，由外层链接跳转至对应章节。图标、技术徽章、封面与实验图片继续保留。

## GitHub显示

主标题使用本地SVG字形路径，不依赖访客字体；带DexterousLab替代文字。所有章节子标题仍使用普通文字。

圆角导航按钮采用本地SVG，带alt说明与独立章节链接。此前生成的正标题和章节装饰SVG保留为历史素材，仅正标题引用wordmark.svg，子标题不使用图片。

概念封面和厂商商品图继续分别维护来源，见 [视觉素材说明](media/README.md)。事实统计、失败实验结果、算法实现状态和原有启动命令保持原义。

## 历史矢量素材生成方式

```bash
cd /root/gpufree-data/DexterousLab
/root/gpufree-data/IsaacLab-Arena/.venv/bin/python scripts/build_readme_style.py
```

生成器使用共享环境已有的Matplotlib和系统Noto字体；不增加仿真运行依赖。字体只用于创建字形轮廓，不打包字体文件。已生成的SVG位于 `docs/media/readme-style/`。
