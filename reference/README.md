# reference/

这个目录放**参考材料**，主要给维护者阅读、对照、理解实现，不作为当前测试的主要运行时输入。

## 放这里

- 上游 USGS ISIS 源码镜像：`reference/upstream_isis/`
- 上游测试源码、调用示例、阅读材料
- 本仓库的行为分析、生命周期总结、设计笔记

## 不放这里

- 会被 `tests/unitTest/`、`tests/smoke_import.py`、`ctest` 直接读取的数据
- 大体积 mission 产品或整包 upstream 测试数据
- 临时日志、调试输出、崩溃产物

这些通常应放到 `tests/data/`，或者不应提交进仓库。

## 推荐子目录

- `reference/upstream_isis/`：上游 ISIS 源码和上游测试代码镜像
- `reference/analysis/`：行为分析、绑定设计说明
- `reference/notes/`：较轻量的阅读笔记

## 路径约定

- 优先使用仓库相对路径，例如 `reference/upstream_isis/...`
- 不要在可复用说明里写 `/home/...` 这类本机绝对路径

## 快速判断

新增文件前先问两句：

1. 这个文件主要是给人看和对照的吗？
  - 是：放 `reference/`
2. 这个文件会被测试直接读取吗？
  - 是：放 `tests/data/`

如果两者都像，优先拆分：
- 参考源码/说明放 `reference/`
- 最小运行时样本放 `tests/data/`

## 一句话

- `reference/` = 给人看的参考材料
- `tests/data/` = 给测试跑的输入数据