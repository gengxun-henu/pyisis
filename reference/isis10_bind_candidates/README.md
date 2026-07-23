# ISIS 10 新增绑定候选目录

本目录只记录 ISIS 10.0.0 相对 ISIS 9.0.0 新增、且值得评估的非 GUI 类和
函数。它与既有 `todo_pybind11.csv` 和 `class_bind_methods_details/` 分开，
避免把“ISIS 10 新增能力”误写成 ISIS 9 绑定迁移或影响现有完成率。

## 目录结构

- `classes_inventory_summary.csv`：ISIS 10 新增类的优先级、安装面、风险和
  推荐策略。
- `class_details/*_methods.csv`：沿用 ISIS 9 台账格式的逐类公开 API 明细。
- `functions_inventory.csv`：ISIS 10 新增的可评估应用函数及 Python facade
  建议。
- `excluded_new_headers.csv`：已发现但不应进入公共绑定面的新头文件及原因。

通过以下命令重新生成：

```bash
python tools/dev/generate_isis10_bind_inventory.py \
  --isis10-prefix "$ISIS10_PREFIX"
```

上游源码用于判断版本差异和阅读实现；`asp370` 等实际 ISIS 10 prefix 的
头文件和库仍是编译与链接判断的最终依据。

## 当前建议顺序

第一批已完成绑定（仅在 ISIS 10 构建中导出）：

1. `IProj`：通用 PROJ 投影，用户覆盖面最大。
2. `Chandrayaan2OhrcCamera`：小而稳定的任务相机模型。
3. `Chandrayaan2TmcCamera`：小而稳定的任务相机模型。

实现位于 `src/bind_isis10.cpp`，并由 `PYISIS_ISIS10_API` 条件编译保护。
同一源码在 ISIS 9 中不导出这些类，在 ISIS 10 中导出并由
`tests/unitTest/isis10_api_unit_test.py` 验证。

第二批建议评估：

1. `OsirisRexOcamsOpenCVDistortionMap`：对 OSIRIS-REx 数据有明确价值，
   但需要 Camera 生命周期和 QString 包装。
2. `csv2table`：通用价值高，但应设计 Python 参数 facade，而不是暴露
   `UserInterface`。
3. `ocams2isis`、`eisstitch`：任务价值明确，但依赖输入产品和运行数据。

`GdalIoHandler` 值得保留在候选池中，但原始 API 包含 `GDALDataset*`、
`QList*` 和所有权问题，应先设计 Python 友好 facade。`ImageIoHandler`
主要作为其抽象基类注册，不建议直接提供构造器。

## 边界

- 默认排除 QWidget/qisis、signals/slots、测试 fixture 和第三方内部实现。
- `IEndian.h` 是 `Endian.h` 的重命名兼容项，不属于 ISIS 10 新功能。
- 目录中的 `N` 表示待绑定候选，不表示已经承诺进入首个 ISIS 10 release。
- 真正实施前仍需阅读实际 prefix 头文件、上游 `.cpp`、上游用例，并核实
  运行库导出符号。
