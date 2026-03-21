# pyISIS 发布前检查清单

日期：2026-03-17  
作者：Geng Xun（默认元数据）

适用范围：`isis_pybind_standalone`

> 用法建议：每次准备发布、共享二进制产物、切换 Python 版本、升级 ISIS 版本或调整打包方式前，按顺序逐项勾选。  
> 原则只有一句话：**能编译 ≠ 能发布，能导入 ≠ 用户能稳定使用。**

## 1. 解释器与 ABI

- [ ] 使用的验证解释器与扩展模块 ABI 匹配（当前优先 `/home/gengxun/miniconda3/envs/asp360_new/bin/python`）
- [ ] 已确认不是误用 `base` 或其他不兼容 Python 版本
- [ ] 已确认 Python 主版本、`pybind11`、C++ runtime 与目标环境兼容
- [ ] 若升级 Python 版本，已重新构建并重新验证 `_isis_core`

## 2. 构建产物检查

- [ ] `_isis_core` 已成功构建
- [ ] `build/python/isis_pybind/` 下包结构完整
- [ ] `__init__.py` 与扩展模块都在预期位置
- [ ] `build/python/isis_pybind/LICENSE` 已生成
- [ ] 构建日志中没有未处理的链接警告或缺失库提示

## 3. Smoke Test

- [ ] `tests/smoke_import.py` 运行通过
- [ ] 基本符号存在性检查通过
- [ ] 最小跨模块调用链可执行
- [ ] smoke test 未被塞入过多详细行为断言，仍保持快速稳定

## 4. Focused Unit Tests

- [ ] 值类型测试通过：如 `Angle`、`Distance`、`Latitude`、`Longitude`
- [ ] 资源/容器类测试通过：如 `Cube`、`Buffer`、`Portal`、`Table`
- [ ] I/O 类测试通过：如 low-level / high-level cube IO、`ProcessImport`
- [ ] 工厂/插件相关测试通过：如 `CameraFactory`、`ProjectionFactory`
- [ ] 异常翻译测试通过：C++ 异常可稳定转成 Python 异常
- [ ] Python-facing 接口测试通过：`repr`、`to_string()`、enum、list/array 输入输出

## 5. 安装后验证

- [ ] build-tree import 验证通过
- [ ] `cmake --install` 后 install-tree import 验证通过
- [ ] `import isis_pybind` 在真实 `site-packages` 中成功
- [ ] 安装后的 `isis_pybind` 包目录中存在 `LICENSE`
- [ ] `_isis_core` 安装后能正常加载
- [ ] 安装后最小功能调用通过，而非仅仅 import 成功

## 6. 运行时依赖

- [ ] `libisis.so` 可被正确解析
- [ ] `Camera.plugin` 路径有效
- [ ] 需要的 camera/projection 动态库可解析
- [ ] Qt / Bullet / 其他运行时依赖不存在缺失或串库问题
- [ ] RPATH / 运行时搜索路径在目标环境中有效

## 7. 环境依赖型能力

- [ ] 依赖 kernels / SPICE / leap seconds 的测试在环境齐全时通过
- [ ] 环境不齐全时相关测试采用 skip，而不是误报绑定回归
- [ ] 已区分“环境缺失”与“绑定实现问题”
- [ ] 外部 cube / label / 测试数据路径清晰可复现

## 8. 版本与兼容矩阵

- [ ] 已记录当前支持的 Python 版本
- [ ] 已记录当前支持的 ISIS 版本范围
- [ ] 若作为独立包发布，已明确 `isis` 依赖约束
- [ ] 版本号、构建号、变更说明与产物一致

## 9. 打包与分发方式

- [ ] 已优先选择可重复安装的分发方式（推荐 conda 包）
- [ ] 未将“手工拷贝 `.so`/包目录”作为正式发布方案
- [ ] 若发布为独立 conda 包，recipe 已表达必要依赖与 pinning
- [ ] GitHub Releases 若存在，仅作为预览版/试用版，而非唯一正式分发渠道

## 10. 干净环境安装验证

- [ ] 在干净 conda 环境中完成安装
- [ ] 安装后普通 `import isis_pybind` 成功
- [ ] 已执行最小可用工作流，而不只是 import smoke
- [ ] 用户侧安装说明与真实安装过程一致

## 11. 文档同步

- [ ] `README.md` 中的构建、安装、测试说明仍然准确
- [ ] 若增加了新测试入口或新依赖，文档已同步更新
- [ ] 若支持范围有变化，已更新兼容矩阵与限制说明
- [ ] 已将已知限制写清楚，避免用户踩“隐形坑”

## 12. 最终发布判断

只有当以下条件同时满足时，才建议对外正式发布：

- [ ] smoke test 通过
- [ ] focused unit tests 通过
- [ ] install-tree 验证通过
- [ ] 运行时依赖解析通过
- [ ] 干净环境安装验证通过
- [ ] 文档与版本信息一致

## 不建议发布的信号

出现以下任一情况时，建议暂停发布：

- [ ] 仅在 build tree 中可导入，安装后失败
- [ ] 仅开发机可用，干净环境失败
- [ ] 依赖库解析不稳定
- [ ] Python 版本切换后未重新构建仍试图复用旧产物
- [ ] 依赖外部 kernels/插件的数据型功能没有区分环境缺失与实现回归
- [ ] 打算让用户通过手工拷贝方式承担 ABI 风险

## 建议命令记录（可选）

- [ ] 记录本次使用的 Python 路径
- [ ] 记录本次测试命令
- [ ] 记录本次对应的 ISIS 版本 / conda 环境
- [ ] 记录本次构建 commit 或 tag

---

如果某一项未通过，请优先判断其属于以下哪类问题：

1. 绑定实现问题  
2. ABI / Python 版本问题  
3. 动态库 / 安装路径问题  
4. 外部环境数据缺失问题  
5. 打包 recipe / 发布流程问题
