# PyISIS 仓库专用自托管 Actions 设计

## 目标

在当前 Ubuntu 26.04 x86_64 主机上部署一个仅供
`gengxun-henu/pyisis` 使用的 GitHub Actions self-hosted runner，复用本机
Conda/ISIS 安装，以 16 个并行编译任务加速日常 PR 验证，并通过持久 CMake
构建树和 `ccache` 缩短重复构建时间。

发布验证最终覆盖以下 8 个目标：

- ISIS 9 × Ubuntu 22.04、Ubuntu 24.04、Ubuntu 26.04、Windows Server 2022；
- ISIS 10 × Ubuntu 22.04、Ubuntu 24.04、Ubuntu 26.04、Windows Server 2022。

第一阶段只启用已安装且可验证的 ISIS 9。ISIS 10 使用独立的 Python 3.13
Conda 环境，在该环境完成安装和预检后通过一个显式配置开关启用。日常 CI
可以在 ISIS 10 尚未就绪时继续运行，但正式发布必须通过全部 8 个目标。

## 已知环境

- 主机：Ubuntu 26.04 LTS，Linux x86_64；
- CPU：24 个物理核心、32 个逻辑线程；
- 内存：约 61 GiB；
- 根文件系统可用空间：约 242 GiB；
- ISIS 9 环境：`/home/gengxun/miniconda3/envs/asp360_new`；
- ISIS 9 环境 ABI：ISIS 9.0.0、CPython 3.12；
- 当前未检测到 GitHub Actions runner 服务、Docker 或 `ccache`；
- 仓库已有 self-hosted workflow、持久 build tree 和 `ccache` 接入逻辑，但通用
  构建当前会用 `nproc` 选择全部 32 个逻辑线程；
- 仓库是公开仓库，不能让未经信任的 fork PR 在持久自托管主机上执行代码。

## 架构选择

### 单个原生 Linux runner

第一阶段只运行一个仓库级、持久、原生 Linux runner 服务。每个 runner 服务
一次只接收一个 job；每个 CMake/Ninja 构建固定最多使用 16 个并行任务。这样
既能明显加速编译，又不会因两个并发构建同时占满 32 个逻辑线程而影响主机
交互使用。

runner 使用独立的低权限系统账户、独立工作目录和独立缓存目录。它注册到
`gengxun-henu/pyisis`，不注册到用户或组织层级。第一阶段标签为：

```text
self-hosted,linux,x64,pyisis,ubuntu-26.04,isis9
```

ISIS 10 环境通过预检后再添加 `isis10` 标签。工作流必须要求 `pyisis` 及具体
能力标签，不能只要求宽泛的 `self-hosted` 标签。

当前 `/home/gengxun` 仅允许所有者和所属组穿越。实施时对 runner 账户使用
路径级 ACL，只授予穿越 Miniconda 父目录以及读取/执行目标 Conda 环境所需的
权限；不把 runner 账户加入 `gengxun` 个人用户组，也不开放整个 home 目录。
runner 写入自己的 HOME、workspace 和缓存目录，不修改预配 Conda 环境。

runner 通过出站 HTTPS 长连接访问 GitHub，不需要开放公网入站端口，也不要求
把本机配置成 SSH 服务器。远程登录主机不属于本设计范围。

### 暂不部署第二个 runner

不为 ISIS 9 和 ISIS 10 分别启动两个 runner 服务。两个服务可能同时各用 16
线程，造成 CPU、内存和磁盘 I/O 峰值竞争。只有在单 runner 队列时间成为明确
瓶颈后，才评估第二服务及其独立工作目录、缓存目录和资源限额。

## CI 分层

### 日常 PR 精简验证

可信的同仓库分支 PR 使用 Ubuntu 26.04 自托管 runner：

1. ISIS 9 + CPython 3.12：第一阶段必跑；
2. ISIS 10 + CPython 3.13：独立环境就绪后启用；
3. 执行 CMake configure、16 路增量构建、smoke import 和相关单元测试；
4. Windows ISIS 9 现有 workflow 保留路径过滤，只在 C++、打包、运行时或
   Windows 相关文件变化时使用 GitHub 托管 Windows runner。

来自 fork 的 PR 不得调度到自托管 runner。它们可以运行 GitHub 托管的轻量
检查，或者在维护者审阅并把变更带入可信分支后运行自托管验证。不得使用
`pull_request_target` 检出并执行外部 PR 代码。

### `main` 与发布验证

Linux wheel 每个 ISIS 大版本只在受控 `manylinux_2_28_x86_64` 环境构建一次，
然后分别在 Ubuntu 22.04、24.04、26.04 环境安装并运行验证。Windows Server
2022 使用 GitHub 托管 runner，分别构建并测试 ISIS 9 和 ISIS 10。

最终目标矩阵为：

| ISIS | Python | Ubuntu 22.04 | Ubuntu 24.04 | Ubuntu 26.04 | Windows 2022 |
|---|---|---:|---:|---:|---:|
| 9 | 3.12 | 必过 | 必过 | 必过 | 必过 |
| 10 | 3.13 | 必过 | 必过 | 必过 | 必过 |

Linux 发布流水线允许将构建与安装验证拆成多个 job：两个 manylinux 构建 job
产出 wheelhouse，六个 Ubuntu 目标消费对应 wheelhouse。矩阵的“8 项”指最终
平台/ISIS 组合的验证结果，不要求在三个 Ubuntu 版本重复完整编译。

`manylinux_2_28` 是 Linux wheel 的 glibc 兼容基线，不是 Ubuntu 发行版。
它用于限制发布二进制所需的最低 glibc 版本；Ubuntu 容器安装测试仍然保留，
因为 manylinux 标签本身不能证明 ISIS 数据、动态库打包和运行时行为正确。

## ISIS 环境模型

ISIS 9 和 ISIS 10 必须使用独立 Conda 环境，禁止原地升级
`asp360_new`：

- ISIS 9：`asp360_new`，ISIS 9.0.0，CPython 3.12；
- ISIS 10：新建专用环境，ISIS 10.x，CPython 3.13；
- 每个 job 显式解析 `ISIS_PREFIX`、Python 可执行文件、Conda prefix 和
  `ISISDATA`；
- 预检必须核对实际 ISIS 版本和 Python ABI，不能仅根据环境目录名推断；
- ISIS 10 未启用时，日常 summary 显示“未配置/未启用”，不能显示成功；
- 发布 workflow 请求完整矩阵时，缺少任一环境或目标都必须失败。

## 容器与 Windows 边界

Ubuntu 26.04 主机可以运行 Ubuntu 22.04、24.04 和 manylinux Linux 容器，
但需要先安装 Docker，并让 runner 服务账户具备运行容器的最小权限。发布镜像
使用固定版本，并在落地时记录或固定镜像摘要，降低上游镜像漂移风险。

Linux 容器不能模拟 Windows 内核，因此不使用 Wine、MinGW 交叉编译或普通
Docker Linux 容器替代 Windows 验证。Windows 目标继续使用
`windows-2022` GitHub 托管 runner。未来只有在成本或时长成为瓶颈时，才另行
设计 KVM Windows 虚拟机和 Windows self-hosted runner。

## 缓存设计

### Conda 环境

本机 Conda 环境是预配资产，不在每次 workflow 中重建。workflow 只读取和
使用它；依赖升级由显式维护流程完成，避免并发 job 修改环境。

### `ccache`

- 通过 Conda 安装 `ccache`，不引入 pip 或 npm 依赖流程；
- 最大容量为 20 GiB，启用压缩；
- 缓存目录属于 runner 服务账户；
- key/namespace 至少区分仓库、ISIS 大版本、Python ABI、编译器身份和目标
  平台；
- 每次构建在 Actions Summary 中报告命中率、命中数量和缓存大小。

### CMake/Ninja build tree

- 保留仓库现有的跨 run 持久 build tree 机制；
- build tree 指纹纳入 ISIS prefix/版本、Python ABI、编译器版本、CMake 关键
  参数、runner 身份和目标平台；
- ISIS 9、ISIS 10、manylinux、Ubuntu 安装验证和 Windows 不共享 build tree；
- 默认删除超过 7 天的陈旧 build tree；
- 清理范围严格限制在 runner 专用缓存根目录，不能触碰源码 checkout、Conda
  环境或用户其他文件。

### 容器和 GitHub 托管缓存

- manylinux 构建镜像与 Ubuntu 验证镜像按固定版本拉取；
- 容器内依赖缓存使用 runner 专用 Docker 存储和必要的只读/专用卷；
- Windows 继续使用 GitHub Actions/micromamba 缓存，并为 ISIS 9 与 ISIS 10
  使用不同 key；
- 发布产物通过 GitHub artifact 在 build job 与验证 job 之间传递，不依赖
  某个临时 workspace 恰好仍存在。

## 安全模型

- 使用独立 runner 系统账户，不授予日常用户 sudo 权限或访问个人密钥；
- 通过最小路径 ACL 只读使用预配 Conda 环境，不继承 `gengxun` 用户组权限；
- runner job 默认 `permissions: contents: read`；发布权限只放在独立发布 job；
- 自托管构建 job 不读取发布 token、SSH 私钥或 TestPyPI/PyPI 密钥；
- 禁止 fork PR、Dependabot 等不可信上下文直接运行自托管 job；
- 第三方 action 固定到明确版本，关键发布路径后续可固定到 commit SHA；
- checkout 后清除可能污染传输方式的仓库级 Git 配置，并保留现有安全 checkout
  诊断；
- Docker group 等价于较高主机权限，因此只把专用 runner 账户加入该组，并且
  仍只允许运行可信代码；
- 注册 token 是一次性、短时令牌，不写入仓库、日志或设计文档。

## 配置与工作流边界

仓库配置继续以 `.github/runner-config.yml` 为入口，扩展为包含：

- 专属 runner 标签；
- `build_jobs: 16`；
- `ccache_max_size: 20G`；
- ISIS 9 prefix；
- ISIS 10 prefix 与显式启用状态；
- 日常 PR 与完整发布两种策略。

共享 resolver 将这些值输出给 reusable workflows。构建并行度不得在多个
workflow 中重复硬编码；统一 reusable build wrapper 必须把配置值传入
self-hosted 构建。现有 GitHub-hosted fallback 保留，避免本机离线时所有仓库
维护操作都停止。

发布矩阵使用独立 workflow 或清晰隔离的 reusable workflow，不能把 Windows
PowerShell、manylinux 构建和 Ubuntu 安装验证塞进一个难以审查的 job。

## 失败处理和可观测性

runner 注册前提供本机预检，至少核对：

- 操作系统、架构、可用 CPU/内存/磁盘；
- Conda prefix、ISIS 版本、Python ABI、CMake、Ninja 和 Conda C++ 编译器；
- `ccache`、Docker daemon 和 runner 服务账户权限；
- GitHub HTTPS 连通性；
- runner 标签和目标仓库。

每次自托管构建在 Actions Summary 输出：

- runner 名称、操作系统和所选 ISIS 环境；
- 请求及实际构建并行度；
- build tree 是否复用以及未复用原因；
- `ccache` 统计；
- smoke/unit 验证结果；
- ISIS 10 是否启用。

环境缺失、版本不符、缓存元数据不匹配或 Docker 不可用时应尽早失败并给出
具体原因。缓存失效本身不是构建失败条件：workflow 应回退到干净构建，并在
summary 中说明原因。

## 验证策略

仓库修改按以下顺序验证：

1. workflow/config 解析和现有 workflow 单元测试；
2. YAML/action 静态检查；
3. `asp360_new` 下的 `tests/smoke_import.py`；
4. 使用 16 路构建执行一次干净 ISIS 9 本机构建；
5. 再次构建，验证 build tree 与 `ccache` 命中；
6. runner 注册后手动触发 host sanity check；
7. 手动触发日常 ISIS 9 自托管 workflow；
8. Docker 就绪后验证 manylinux 构建和 Ubuntu 22.04/24.04/26.04 安装测试；
9. ISIS 10 独立环境就绪后启用并验证相同路径；
10. Windows Server 2022 上分别验证 ISIS 9 和 ISIS 10；
11. 只有 8 个最终目标全部成功时，完整发布 gate 才通过。

## 成功标准

- GitHub 仓库页面显示一个在线的仓库专用 Linux x64 runner；
- 自托管 job 只能匹配 `pyisis` 专属标签，fork PR 无法调度它；
- ISIS 9 日常 PR 构建固定使用 16 个并行任务并通过 smoke/相关单元测试；
- 第二次等价构建报告有效的 build tree 或 `ccache` 命中；
- 主机离线时，轻量仓库维护 workflow 仍可使用 GitHub-hosted runner；
- ISIS 10 未启用时不会被误报为通过；启用后使用独立 Python 3.13 环境和缓存；
- 发布 gate 最终呈现并强制执行 8 个 ISIS/平台验证目标；
- Linux 发布 wheel 通过 manylinux 审计，并在三个 Ubuntu 目标完成安装和运行时
  验证；
- Windows 目标在真实 Windows Server 2022 runner 上完成，不依赖 Linux
  交叉模拟。

## 非目标

- 本阶段不安装或配置第二个并发 runner 服务；
- 不把 runner 提升为组织级共享资源；
- 不开放公网 SSH 或配置通用远程开发主机；
- 不在 Linux 上模拟 Windows 构建；
- 不在第一阶段原地升级或替换 `asp360_new`；
- 不在 ISIS 10 环境未验证前强行启用 ISIS 10 发布单元。

## 参考

- [GitHub self-hosted runners reference](https://docs.github.com/en/actions/reference/runners/self-hosted-runners)
- [Adding self-hosted runners](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/add-runners)
- [Running jobs in a container](https://docs.github.com/en/actions/how-tos/write-workflows/choose-where-workflows-run/run-jobs-in-a-container)
- [Python Packaging platform compatibility tags](https://packaging.python.org/en/latest/specifications/platform-compatibility-tags/)
- [PyPA manylinux images](https://github.com/pypa/manylinux)
