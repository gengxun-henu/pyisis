# tests/data/

这个目录放**测试运行时真正会读取的稳定输入数据**。

## 放这里

- unit test 直接打开的 `.cub`、`.lbl`、`.pvl`、表格等 fixture
- 从 upstream 测试样本裁剪出来的最小可复用数据
- `tests/smoke_import.py` 或 `ctest` 运行时依赖的数据
- mock ISISDATA 内容，例如 `tests/data/isisdata/mockup/`

## 重点目录

- `tests/data/isisdata/mockup/`
  - 本仓库测试使用的最小 ISISDATA mock 环境
- `tests/data/upstream_derived/`
  - 从 upstream 测试资产裁剪出的最小样本

## 不放这里

- 只是给人阅读或行为对照的材料
- 上游完整源码或上游测试源码
- 当前测试根本不会用到的大型数据
- 临时调试输出或依赖个人绝对路径的文件

这些通常更适合放在 `reference/`，或者根本不应提交。

## 路径约定

- 优先使用仓库相对路径，例如 `tests/data/...`
- 需要 ISISDATA mock 时，优先引用 `tests/data/isisdata/mockup/...`
- 不要在可复用说明中写死本机绝对路径

## 快速判断

新增数据前先问三句：

1. 这个文件会被测试在运行时直接读取吗？
   - 会：适合放这里
2. 能不能缩成更小、更稳定的样本？
   - 能：优先提交最小版本
3. 它是不是其实只是参考材料？
   - 是：改放 `reference/`

## 一句话

- 这里放“测试会读的”
- 不放“只是想留着参考的”