# 历史USD渲染展示说明（不再作为当前顶图）

以下为此前版本记录。文中的“当前”指当时版本，现行图片来源以 [厂商官方图片说明](official-products/README.md) 为准。

# README 灵巧手展示图来源

当前README顶部使用 `dexterouslab-lightblue.png`：22个已记录通过资产级验证的真实USD配置，覆盖17个厂商。采用白底与浅蓝氛围、珍珠白外壳、蓝灰机械结构及深色指尖，使用1200像素透明底源图重新渲染；采用远近交错、朝向中心物体的空间构图，保留真实手模型几何与USD静态装配变换；模型方向、尺寸和相对位置按封面构图调整，材质与光照为视觉展示设置。

- 当前主图：[白底浅蓝群手构图](dexterouslab-lightblue.png)，2800 × 1600。
- 每个配置的源路径、哈希、许可、显示方向与主图放置参数：[22个配置完整来源](lightblue-provenance.json)。
- 原始清单中的22个 `simulation_status=passed` 配置与封面配置逐一比对，不重复充数。
- 中心立方体是示意元素，不是物体抓取成功的仿真截图。
- 18款带名称的精选模型图 `dexterouslab-collection.png` 保留在资产章节供查询。
- 旧版 `dexterouslab-kinetic.png`、`dexterouslab-cover.png`、`dexterouslab-hands.png` 留档，不再用于README顶部。

这是一组离线模型渲染，不是Isaac Sim仿真截图、实际关节控制或抓取成功证据；展示姿态来自USD的静态装配。
选取的是已记录通过资产级验证的配置；新的桌面控制器仍需独立适配。

下面18款精选模型的源路径与许可记录见 [精选来源清单](hand-gallery-provenance.json)。当前顶部全部22个配置见 [完整封面来源](lightblue-provenance.json)。

| 展示名称 | 资产ID | 原始来源 | 许可记录 |
|---|---|---|---|
| Allegro Hand | `wonik/allegro/isaaclab_standalone` | https://github.com/isaac-sim/IsaacLab | NVIDIA asset terms; config code BSD-3-Clause |
| Shadow Hand | `shadow_robot/dexterous_hand/right_isaaclab` | https://github.com/isaac-sim/IsaacLab | NVIDIA asset terms; config code BSD-3-Clause |
| LEAP Hand | `leap/leap_hand_v1/right` | https://github.com/leap-hand/LEAP_Hand_Sim | MIT |
| Dex5-1 | `unitree/dex5_1/right` | https://github.com/unitreerobotics/unitree_ros | BSD-3-Clause |
| Wuji Hand V1 | `wuji/hand_v1/right` | https://github.com/wuji-technology/wuji-description | MIT |
| Wuji Hand V2.2 | `wuji/hand_v2/2_2_right` | https://github.com/wuji-technology/wuji-description | MIT |
| Revo2 | `brainco/revo2/revo2_right_hand` | https://github.com/BrainCoTech/revo2_description | Apache-2.0 |
| XHand | `robotera/xhand/xhand_right` | https://github.com/facebookresearch/spider | LicenseRef-Meta-CC-BY-NC |
| DG5F | `tesollo/dg5f/dg5f_right` | https://github.com/tesollodelto/dg5f_ros2 | BSD-3-Clause |
| Ability Hand | `psyonic/ability_hand/ability_hand_right_large` | https://github.com/psyonicinc/ability-hand-api | MIT |
| SVH | `schunk/svh/schunk_svh_hand_right` | https://github.com/dexsuite/dex-urdf | GPL-3.0 |
| Barrett Hand | `barrett/barrett_hand/bhand_model` | https://github.com/dexsuite/dex-urdf | MIT AND BSD-2-Clause |
| HX5 | `robotis/hx5/urdf_hx5_d20_right` | https://github.com/whats-lab/dexterous-hand-urdf | Apache-2.0 |
| ORCA Hand | `orca/orca_hand/v1_models_urdf_orcahand_right` | https://github.com/orcahand/orcahand_description | MIT |
| DexHand021 | `dexrobot/dexhand021/dexhand021_right` | https://github.com/DexRobot/dexrobot_urdf | Apache-2.0 |
| ROHand | `oymotion/rohand/urdf_rohand_right` | https://github.com/oymotion/rohand_urdf_ros1 | MIT |
| LinkerHand L20 | `linkerbot/linkerhand_l20/right_linkerhand_l20_right` | https://github.com/linker-bot/linkerhand-urdf | Apache-2.0 |
| Sharpa Wave | `sharpa/sharpa_wave_wave_01/right_sharpa_wave_right_sharpa_wave` | https://github.com/sharpa-robotics/sharpa-urdf-usd-xml | Apache-2.0 |

各模型仍受原始作者及资产提供方的许可约束，项目不对第三方资产重新授权。XHand记录为非商业许可；NVIDIA资产遵循其资产条款。
完整资产提取包中的原始LICENSE/NOTICE保持原样；本目录只保存展示用渲染图，不打包源网格。

重新生成（使用当前共享环境已有的pxr、VTK和Pillow，不安装依赖）：

```bash
/root/gpufree-data/IsaacLab-Arena/.venv/bin/python scripts/build_lightblue_cover.py
```
