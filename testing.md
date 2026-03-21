# pyISIS testing guide

日期：2026-03-17  
作者：Geng Xun（默认元数据）

本文件聚焦 `isis_pybind_standalone` 的测试分层、验证顺序和环境约束。

## 1. 测试目标

`pybind11` 绑定层的测试目标不是只证明“函数能调用”，而是同时验证：

- Python 暴露接口是否正确
- C++ 语义是否被正确映射
- 异常是否稳定翻译到 Python
- 安装后是否仍可导入
- 环境依赖缺失时是否能正确 skip
- ABI 与运行时依赖是否与目标环境兼容

## 2. 推荐测试层级

### 2.1 Smoke test

适合放在：`tests/smoke_import.py`

职责：

- 模块导入成功
- 关键符号存在
- 少量最小可用路径可执行

不建议：

- 塞入大量细节断言
- 依赖复杂外部数据
- 替代 focused unit tests

### 2.2 Focused unit tests

适合放在：`tests/unitTest/`

优先覆盖：

- 值类型：`Angle`、`Distance`、`Latitude`、`Longitude`
- 资源/容器类型：`Cube`、`Buffer`、`Portal`、`Table`
- I/O：low-level / high-level cube IO、`ProcessImport`
- 工厂/插件：`CameraFactory`、`ProjectionFactory`
- 异常翻译：`ip.IException` 等 Python 侧异常行为
- Python-facing 接口：`repr`、`to_string()`、enum、list/array 输入输出

建议风格：

- 一个文件只负责一个绑定主题
- 使用 `_unit_test_support.py` 复用夹具和示例 PVL / 临时文件逻辑
- 失败信息尽量能直接定位到具体接口

### 2.3 Integration tests

适合验证：

- `Cube + CameraFactory`
- `ProjectionFactory + Pvl`
- `ProcessImport + 输入数据`
- 依赖 plugin / camera libs / kernels 的能力

原则：

- 明确与 unit tests 分层
- 环境不满足时优先 skip
- 不把环境问题误判为绑定回归

### 2.4 Install validation

必须同时验证：

1. build-tree import
2. install-tree import

原因：

很多 pybind 项目会出现“在 build 目录能导入，安装后失败”的情况。

## 3. 推荐验证顺序

每次修改绑定或测试后，建议按以下顺序执行：

1. 最小 focused unit test
2. 相关 unit test 组
3. `tests/smoke_import.py`
4. `cmake --install` 后的 install-tree import
5. 检查安装后的 `isis_pybind/LICENSE` 是否存在
6. 目标环境中的最小工作流

## 4. Python / ABI 约束

当前优先验证解释器：

`/home/gengxun/miniconda3/envs/asp360_new/bin/python`

原因：

- 当前扩展模块面向 CPython 3.12
- 若误用 `base` 或其他 Python 版本，可能出现 ABI 不匹配
- 若 `import isis_pybind` 成功但 `_isis_core` 缺失，先排查 ABI / Python 版本问题

## 5. 环境依赖型测试策略

以下能力可能依赖外部环境：

- leap second kernels
- SPICE / NAIF 数据
- `Camera.plugin`
- mission-specific camera libraries
- projection libraries
- 外部 cube / label / 原始输入数据

建议：

- 环境齐全时执行真实验证
- 环境缺失时使用 skip
- 在测试输出中明确记录缺失项

## 6. 建议维护的覆盖矩阵

### 构造行为

- 默认构造
- 合法构造
- 非法构造
- 枚举构造
- 工厂构造

### 核心行为

- getter / setter
- 数值转换
- 单位转换
- 基础计算
- 文件读写

### Python 侧接口

- `repr` / `str`
- list / array 输入输出
- 容器索引行为
- enum 暴露
- 类型检查

### 异常行为

- 参数错误
- 非法状态
- 文件不存在
- 标签不合法
- 运行时库缺失

### 集成行为

- 对象串联
- 工厂与插件加载
- 数据文件导入导出
- 环境数据依赖
- 安装后最小工作流

## 7. 什么时候测试算“够了”

以下条件同时满足时，才能认为测试达到较稳妥状态：

- smoke test 通过
- focused unit tests 通过
- install-tree 验证通过
- 环境依赖型测试的 skip / fail 分类清晰
- 目标解释器 ABI 匹配
- 至少在一个干净环境里完成安装与最小工作流验证

## 8. 相关文件

- `tests/smoke_import.py`
- `tests/unitTest/`
- `tests/unitTest/_unit_test_support.py`
- `pyisis-发布前检查清单.md`
- `pyisis-开发测试指标原则.md`
