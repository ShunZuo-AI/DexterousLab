# Allegro / Shadow 真实仿真运动视频

2026-11-10，GPUFree NVIDIA L40S，使用已有Arena `.venv`。本轮复用首次抓取实验的机器人、控制与物理配置，增加离屏帧录制，不安装依赖、不修改上游。

## 成果

- [左右对照视频](../media/motion-20261110/comparison.mp4)：1920×690、15 FPS、16秒。
- [Allegro原始录制](../media/motion-20261110/allegro.mp4)与[Shadow原始录制](../media/motion-20261110/shadow.mp4)：960×540、15 FPS、各16秒。
- [README动态预览](../media/motion-20261110/preview.gif)：960×345、10 FPS，完整16秒的抽帧预览。
- [结果、来源与视频编码命令](../media/motion-20261110/evidence.json)。

视频来自当前实际运行的Isaac Lab / PhysX RGB帧，不是静态截图轮播或生成式动画。每2个环境步读取一帧，环境步长1/30秒，MP4按15 FPS播放，保持1倍仿真时间。采集与编码耗时不代表实时仿真速度。

## 实际命令

```bash
cd /root/gpufree-data/DexterousLab
/root/gpufree-data/IsaacLab-Arena/.venv/bin/python scripts/first_grasp_experiment.py --hand allegro --record-video
/root/gpufree-data/IsaacLab-Arena/.venv/bin/python scripts/first_grasp_experiment.py --hand shadow --record-video

/root/gpufree-data/IsaacLab-Arena/.venv/bin/python scripts/compose_motion_video.py \
  --allegro outputs/20261110T070333Z-first-grasp-allegro-8de52169 \
  --shadow outputs/20261110T070638Z-first-grasp-shadow-8a649e8a \
  --output outputs/motion-comparison-new
```

组合脚本要求输出目录尚不存在，避免覆盖已有视频。参数来自 `configs/experiments/first_grasp.toml`。

## 运行证据

| 检查项 | Allegro + KUKA | Shadow |
|---|---:|---:|
| 环境步 / PhysX子步 | 480 / 1920 | 480 / 1920 |
| 轨迹状态帧（含初始状态） | 481 | 481 |
| MP4帧数 / 不同PNG哈希数 | 240 / 240 | 240 / 240 |
| 物理关节 / 动作维度 | 23 / 23 | 24 / 20 |
| 实测运动幅度超过0.01 rad的关节 | 23 | 19 |
| 最大关节位置变化 | 2.1191 rad | 1.3086 rad |
| 最大物体抬升（相对初始化） | 2.074 mm | 0 mm（下界） |
| 抓取结果 | no_lift | no_lift |

全部关节位置、物体姿态为有限值。Shadow没有机械臂，使用规定的运动学基座轨迹；Allegro通过KUKA实际关节驱动。两组不是公平硬件性能排名。机器人刚体重力按既有实验配置关闭，Cube保持真实重力和接触；没有物体附着或reset之后的物体位姿写入。

录像完成不等于抓取成功：判定仍要求3cm抬升、多指接触与最终20步稳定保持，两组均未达标。关节幅度统计不表示所有关节都能独立控制，Shadow仍包含腱耦合。

成功运行目录（位于项目根 `outputs/`，不纳入Git）：

- `20261110T070333Z-first-grasp-allegro-8de52169`
- `20261110T070638Z-first-grasp-shadow-8a649e8a`

目录内保存 `simulation.log`、`request.json`、`script_snapshot.py`、`result.json`、`robot_mapping.json`、`scene_validation.json`、`video_frames.json`、240张PNG及 `trajectory/` 数值数据。成功运行的日志、配置、关键元数据另复制到本报告相邻的 `motion-20261110/` 供仓库查看。

## 录制适配与失败记录

首次有窗口启动在NVIDIA GLX驱动处崩溃；随后离屏模式缺少viewport扩展；再一次viewport文件捕获超时。这三次失败均保留，未计为成功录制：

- `20261110T065547Z-first-grasp-allegro-8cb23e69`：退出139。
- `20261110T065804Z-first-grasp-allegro-d3d78f80`：viewport模块不可用。
- `20261110T070015Z-first-grasp-allegro-687a4b6f`：首帧捕获超时。

最终依据本地 `isaaclab_visualizers/kit/kit_visualizer.py` 的 `render_rgb_array()` API读取离屏图像，并明确配置 `KitVisualizerCfg(headless=True, window_width=960, window_height=540)`。录制时只额外渲染，不推进物理；空白启动帧进行有界重试。ffmpeg生成H.264/yuv420p MP4，完整源帧保留供核查。

## 验证

全套项目单元测试111项通过；组合脚本核验帧数、采样步号、关节状态有限性及运动幅度、源PNG差异和ffprobe视频属性。此次验证未重复运行完整上游测试套件，也未新增手型控制器。
