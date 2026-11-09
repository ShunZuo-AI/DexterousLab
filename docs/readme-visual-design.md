# README 视觉设计

本版参考CVPR研究项目README的内容组织方式：居中品牌与导航、醒目的展示图、快速开始、实验图表、折叠细节与来源记录。字体和图标为DexterousLab独立设计，没有复制参考项目的标识或研究图像，也不表示本项目已被CVPR录用。

## 参考项目

| 项目 | 实际阅读的README | 文件版本（Git blob SHA） |
|---|---|---|
| facebookresearch/vggt | [README](https://github.com/facebookresearch/vggt/blob/main/README.md) | `fc04f23891e77e71b6c2b6c8e6716ee573dd8fa1` |
| naver/dust3r | [README](https://github.com/naver/dust3r/blob/main/README.md) | `858d00b9dad1289f30c3e3533875a6a9808b92f8` |
| CUT3R/CUT3R | [README](https://github.com/CUT3R/CUT3R/blob/main/README.md) | `2d06fbcfdde95d7e25173f41efc1efedb82e7307` |

## 视觉规范

- 正标题：顶部居中的DexterousLab使用Unicode花体文字 `𝓓𝓮𝔁𝓽𝓮𝓻𝓸𝓾𝓼𝓛𝓪𝓫`，不使用图片；标题的title属性保留常规拼写。
- 子标题：全部使用可选择、可复制的Markdown文字，主要章节配简洁图标；步骤标题也使用文字，不使用标题图片。
- 图标：项目内绘制的轨道、火箭、灵巧手、烧瓶、层级、盾牌和书籍线条图标。
- 配色：深蓝 `#173d68`、强调蓝 `#4d88c6`、灰蓝 `#7893ae`、浅蓝白底。
- 排版：章节标题、数字概览、快捷导航和页脚使用文字；小型图标、技术徽章、封面与实验图片继续保留。

## GitHub显示

正标题是实际Unicode文字，使用HTML h1的align属性居中，具体字形由读者设备字体呈现。Unicode NFKC归一化后的拼写为DexterousLab，正文也保留常规拼写供搜索。每张展示图保留alt说明，文字章节保留显式锚点。README使用GitHub可呈现的文字标题、图片、链接、表格、Mermaid和details，未依赖README内自定义CSS。此前生成的正标题和章节装饰SVG保留为历史素材，当前README不再引用这些标题图片。

概念封面和厂商商品图继续分别维护来源，见 [视觉素材说明](media/README.md)。事实统计、失败实验结果、算法实现状态和原有启动命令保持原义。

## 历史矢量素材生成方式

```bash
cd /root/gpufree-data/DexterousLab
/root/gpufree-data/IsaacLab-Arena/.venv/bin/python scripts/build_readme_style.py
```

生成器使用共享环境已有的Matplotlib和系统Noto字体；不增加仿真运行依赖。字体只用于创建字形轮廓，不打包字体文件。已生成的SVG位于 `docs/media/readme-style/`。
