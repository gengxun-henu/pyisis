# ISIS 10 新增绑定候选目录

本目录只记录 ISIS 10.0.0 相对 ISIS 9.0.0 新增、且值得评估的非 GUI 类和
函数。它与既有 `todo_pybind11.csv` 和 `class_bind_methods_details/` 分开，
避免把“ISIS 10 新增能力”误写成 ISIS 9 绑定迁移或影响现有完成率。

## 目录结构

- `classes_inventory_summary.csv`：ISIS 10 新增类的优先级、安装面、风险和
  推荐策略。
- `class_details/*_methods.csv`：沿用 ISIS 9 台账格式的逐类公开 API 明细。
- `functions_inventory.csv`：ISIS 10 新增应用函数的最终处理边界；原生 APP
  项不提供 Python binding 或 helper。
- `excluded_new_headers.csv`：已发现但不应进入公共绑定面的新头文件及原因。

通过以下命令重新生成：

```bash
python tools/dev/generate_isis10_bind_inventory.py \
  --isis9-prefix "$ISIS9_PREFIX" \
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

第二批当前进度：

1. `OsirisRexOcamsOpenCVDistortionMap`：已完成条件绑定、Camera 生命周期、
   QString 转换、双版本构建和聚焦测试。
2. `ImageIoHandler` 与 `GdalIoHandler`：已完成抽象基类注册和 Python
   友好 facade；构造时预检文件及波段，通过 `PixelType` 选择输出类型，
   默认只读，并排除 `GDALDataset*`、Qt mutex 和不明确的裸所有权。
3. `csv2table`、`ocams2isis`、`eisstitch`：所有 ISIS 9/10 和 Linux/Windows
   支持单元均采用原生 ISIS APP 执行边界；不绑定 `UserInterface`，也不新增
   逐程序 Python wrapper 或 helper。Python 编排如有需要可直接使用标准库
   `subprocess`。

## 边界

- 默认排除 QWidget/qisis、signals/slots、测试 fixture 和第三方内部实现。
- 原生 APP 不构成 PyISIS 公共 API；PyISIS 不提供 `csv2table` helper。
- `IEndian.h` 是 `Endian.h` 的重命名兼容项，不属于 ISIS 10 新功能。
- 目录中的 `N` 表示待绑定候选，不表示已经承诺进入首个 ISIS 10 release。
- 真正实施前仍需阅读实际 prefix 头文件、上游 `.cpp`、上游用例，并核实
  运行库导出符号。
