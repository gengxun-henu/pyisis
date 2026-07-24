# ISIS 9 / ISIS 10 兼容性审计

本目录记录当前 PyISIS bindings 在 ISIS 9.0.0 与 ISIS 10.0.0 之间的源码级
兼容性基线。

## 文件

- `isis9-isis10-header-matrix.csv`：当前 `src/` 中每个 binding-header 引用
  在两个上游源码树中的位置、状态和文本比较结果。
- `isis9-isis10-symbol-report.md`：需要人工复核的头文件摘要。
- `isis9-isis10-conda-header-matrix.csv`：对当前实际 conda include prefix
  生成的矩阵。
- `isis9-isis10-conda-report.md`：`asp360_new` 与 `asp370` 的实际安装面
  差异摘要。

上述四个文件由 `tools/dev/audit_isis_api.py` 生成。上游源码目录本身不进入
Git。

## 生成方式

```bash
python tools/dev/sync_upstream_isis.py --isis-version 9.0.0
python tools/dev/sync_upstream_isis.py --isis-version 10.0.0
python tools/dev/audit_isis_api.py
```

不带 `--isis-version` 的同步命令继续选择 ISIS 9，但使用版本化目的地
`reference/upstream_isis/9.0.0/`。旧的 `reference/upstream_isis.lock.json`
仍保留，可在需要检查旧式本地快照时通过 `--lock-file` 显式选择。

重新生成后应检查差异：

```bash
git diff -- \
  reference/compatibility/isis9-isis10-header-matrix.csv \
  reference/compatibility/isis9-isis10-symbol-report.md
```

实际 conda prefix 审计使用相同工具，并通过 label 避免把机器绝对路径写入
报告：

```bash
python tools/dev/audit_isis_api.py \
  --isis9-root "$ISIS9_PREFIX/include/isis" \
  --isis10-root "$ISIS10_PREFIX/include/isis" \
  --isis9-label "asp360_new: ISIS 9.0.0 h1f94ec8_0, Python 3.12.2" \
  --isis10-label "asp370: ISIS 10.0.0 asp_4, Python 3.13.14" \
  --output-csv reference/compatibility/isis9-isis10-conda-header-matrix.csv \
  --output-report reference/compatibility/isis9-isis10-conda-report.md
```

## 结果解释

- `identical_text`：两个锁定源码树中的头文件内容一致。
- `changed_review_required`：内容不同，需要继续比较公开声明、链接符号和
  行为；不能直接推断 ABI 已破坏。
- `renamed_review_required`：当前 include 在 ISIS 10 缺失，但已识别候选
  替代头文件，仍需通过真实 ISIS 10 prefix 编译验证。
- `missing_in_isis9` / `missing_in_isis10`：一侧没有找到头文件。
- `ambiguous_header`：同一源码树存在多个同名候选，需要人工指定。
- `qt_observer_review`：类包含 Qt observer 元数据；稳定数据 API 可以继续
  审阅，但 signals/slots 默认不绑定。

## 已处理的首要兼容项

ISIS 9 的 `Endian.h` 在 ISIS 10 中对应 `IEndian.h`。其 `ByteOrder` 等公共
定义仍可在 ISIS 10 源码中找到；当前 binding 已按安装头文件选择 include，
并在 ISIS 9/10 实际 prefix 中通过编译验证。

`JP2Error.h`曾存在于锁定的 ISIS 10 源码树、但未安装进当时的
`asp370/include/isis`。2026-07-24刷新安装面后，该头文件已经存在且与
ISIS 9文本一致。这一变化说明源码级矩阵不能替代prefix级矩阵；
`src/bind_high_level_cube_io.cpp`仍按目标安装面条件编译Kakadu/JP2Error
接口，使缺少该安装头的ISIS 10构建继续可用。

## ISIS 10 构建验证

2026-07-23 使用两个实际 conda prefix 验证同一源码：

- `asp360_new`：Python 3.12、ISIS 9、Qt5，`_isis_core` 编译和导入通过。
- `asp370`：Python 3.13、ISIS 10、Qt6/Core5Compat，`_isis_core` 编译和
  导入通过。
- CMake 从所选 `Python3_EXECUTABLE` 查找 pybind11，目标环境缺失时直接
  失败，不再静默回退到另一 conda 环境。
- Qt 主版本从目标 ISIS prefix 的安装面选择，也可通过
  `PYISIS_QT_MAJOR=5|6` 显式指定。
- 两个环境的 low/high-level Cube I/O 聚焦测试均为 64 项通过、2 项按既有
  原因跳过。

仍需继续推进：

1. 将本机双版本构建转换为 GitHub Actions Linux 矩阵。
2. 增加构建时 ISIS 版本元数据和 runtime 主版本不匹配检测。
3. 按 `reference/isis10_bind_candidates/` 分批实施 ISIS 10 新增绑定。
4. 单独验证 benchmark 和更广泛的双版本单元测试。

## 边界

本审计只建立源码级候选清单。实际可绑定签名以目标 conda 或 Windows ISIS
prefix 中的头文件为准；链接可用性以相应运行库导出符号为准。
