# 在云桌面查看灵巧手

从 GPUFree 的云桌面进入服务器，打开终端。预览窗口显示在服务器桌面，不会自动出现在本地浏览器的新网页中。

```bash
cd /root/gpufree-data/DexterousLab
export PATH="$PWD/scripts:$PATH"

# 默认预览 10 分钟；关闭窗口可提前退出
dexlab assets preview --id wonik/allegro/isaaclab_standalone

# 关闭前一个窗口后，再选择另一只手
dexlab assets preview --id shadow_robot/dexterous_hand/right_isaaclab
dexlab assets preview --id unitree/dex3_1/right
dexlab assets preview --id leap/leap_hand_v1/right
dexlab assets preview --id wuji/hand_v2/2_2_right
dexlab assets preview --id brainco/revo2/revo2_right_hand
dexlab assets preview --id robotis/hx5/urdf_hx5_d20_right

# 自定义时间：1 到 3600 秒
dexlab assets preview --id unitree/dex5_1/right --seconds 300
```

鼠标在视口中使用 Isaac Sim 导航：Alt + 鼠标左键环绕、Alt + 中键平移、滚轮缩放。窗口自动按模型尺寸设置观察位置。如果桌面窗口仍为黑色，先查看当前运行目录的 `simulation.log`，首次 RTX 着色器编译可能持续数分钟，编译期间视口可能为黑色；具体进度在 `.cache/kit/logs/Kit/IsaacLab/3.0/` 的当前 Kit 日志中。

CLI 返回 `starting`、PID 和运行目录，表示已经启动进程；该目录的 `ready.json` 才表示模型、物理及视口初始化完成。日志路径为 `assets/hands/<厂商>/<型号>/<版本>/runs/<时间>-preview-<编号>/simulation.log`。预览状态不会改写资产仿真验收结果。

当前预览只允许已经通过物理验证的手型，使用固定根关节位置保持。它用于查看模型、旋转视角及观察有限时间的物理步进，不包含抓取策略或通用关节控制界面。建议一次只打开一个预览，避免多个 RTX 窗口占用 GPU。

`assets manufacturers` 和 `assets hands --manufacturer unitree` 可列出资产 ID；完整列表见 [资产覆盖表](asset_aggregation/coverage.md)。项目只使用既有 Arena Python 环境；没有另外安装 Isaac Sim。
