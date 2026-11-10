# 开发指南

优先让一次实验的调用链清晰，复用已有模块。新需求先判断能否用配置表达，再决定是否需要增加代码。

## 模块边界

- `cli.py` 只做参数解析、分发和输出，不编写仿真逻辑。
- `config.py` 与各 Registry 负责配置校验和发现，不启动仿真。
- `runtime.py` 负责共享环境、子进程生命周期和运行证据，不判断抓取成功。
- `scenes/`、`robots/`、`objects/`、`tasks/` 实现各自的仿真组件；第三方 API 适配放在 `integrations/`。
- 生成、执行、记录与评测分开，复用现有 GraspCandidate、DatasetCollector 和 EvaluationRunner。
- `scripts/` 保留命令入口、资产工具和实验工具；通用业务逻辑放在 `src/`，不在多个脚本中复制。

## 写简单的代码

1. 一个函数完成一个明确操作；按功能拆分长函数，不为每一行增加包装函数。
2. 使用具体名称与清晰的 `if` 分支，避免嵌套三元表达式、复杂推导式和动态分发技巧。
3. 多行字典与调用按字段换行；不把赋值、循环和异常处理挤在一行。
4. 只提取真正重复的逻辑。例如子进程等待与退出统一使用 `runtime.wait_for_process()`，各运行器保留自己的结果判定。
5. 为公共入口说明输入与结果；注释解释坐标、物理含义或兼容性原因，不重复代码。
6. 保持现有命令、配置字段和数据格式兼容。未知手型、物体或后端明确报错，不静默替换。
7. 重构与算法行为变化分别说明。不要在整理代码时修改成功判据或物理参数。

## 数据与仿真约定

长度、角度、四元数顺序与坐标系遵循 [数据契约](data-contract.md)。手型动作维度来自各自配置，不能假设 Allegro 与 Shadow 相同。不要用 Python 索引代替稳定的关节名称契约。

所有仿真导入必须发生在 SimulationApp 启动后。只使用已安装的 Arena 环境，不修改上游源码，不在重构过程中同步或重新安装依赖。子进程超时或中断后要终止并回收进程。

## 验证修改

在项目根目录，使用已安装的 Arena Python：

```bash
PYTHONDONTWRITEBYTECODE=1 "$DEXLAB_ARENA_ROOT/.venv/bin/python" -m pytest -q -p no:cacheprovider

dexlab scene run --hand allegro --object cube --physics physx --dry-run
dexlab scene run --hand allegro --object cylinder --physics physx --dry-run
dexlab scene run --hand shadow --object cube --physics physx --dry-run
```

纯配置、分发或进程管理重构优先通过单元测试和 dry-run 验证。修改场景、控制或物理行为时，再运行对应的小规模 GPU 测试，并保留命令、日志及结果。dry-run 不启动仿真，不能当作资产加载或抓取成功的证据。

当前没有安装或新增代码格式化依赖；本指南约定的是后续修改方式，不表示所有历史代码已经统一格式化。
