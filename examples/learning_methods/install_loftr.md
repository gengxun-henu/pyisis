那就走CPU 优先、先跑通再说这条最稳路线。这样最不容易被 CUDA、驱动、版本配平这些“额外副本”绊住。

推荐做法
结合这个仓库的约定，建议你：

继续使用 asp360_new 环境
用 mamba/conda 安装 PyTorch CPU 版
用 pip 安装 kornia[loftr]
然后验证 LoFTR 导入是否成功
仓库里也明确偏向使用 asp360_new 作为解释器环境，见：

copilot-instructions.md
README.md
README.zh-CN.md

而你当前 loftr_simple.py 需要的核心依赖就是：

torch
from kornia.feature import LoFTR, default_cfg
直接照着执行
1) 激活目标环境
conda activate asp360_new

2) 安装 PyTorch CPU 版
如果你有 mamba，优先它：
mamba install pytorch cpuonly -c pytorch
如果没有 mamba，就用 conda：
conda install pytorch cpuonly -c pytorch
3) 安装 Kornia 的 LoFTR 支持
python -m pip install "kornia[loftr]"
4) 验证安装结果
python -c "import torch; print('torch ok:', torch.__version__)"
python -c "import kornia; print('kornia ok:', kornia.__version__)"
python -c "from kornia.feature import LoFTR, default_cfg; print('LoFTR ok')"

5) 再跑你的脚本
python /home/gengxun/PlanetaryMapping/asp360_new/pyisis/ISIS3-9.0.0-ext/isis_pybind_standalone/examples/experiment_methods/loftr_simple.py


最推荐的安装思路
优先建议这条：
mamba install --freeze-installed --override-channels -c pytorch -c conda-forge pytorch cpuonly kornia
这条命令的意义
--override-channels
这次安装只看你显式给出的频道
-c pytorch -c conda-forge
只用最小必需频道
--freeze-installed
尽量不要去动你已经装好的 ISIS / ASP / 其他包
pytorch cpuonly kornia
正好覆盖 LoFTR 当前最小依赖
为什么我推荐加 kornia
因为你这个仓库里的 LoFTR 不是单独外部脚本，而是直接走：

torch
kornia.feature.LoFTR
所以只装 pytorch 还不够，kornia 也要有。


## 使用双环境安装深度学习匹配算法，目前通过文件进行交互，不能同一进程使用。后期可以想办法解决这个问题


正确的安装姿势
根据你之前的对话和仓库结构，正确的安装逻辑应该是：

    基础环境（必须）：
    安装 Kornia，因为它包含了 LoFTR 和 SuperPoint 检测器。
    bash

    python -m pip install "kornia[loftr]"

    进阶环境（按需）：
    如果你后续想跑 SuperPoint + SuperGlue 或者 LightGlue，你需要额外安装这两个独立的库（因为它们不在 Kornia 里）。
    bash

    # 安装 SuperGlue (通常指 magicleap 的实现)
    python -m pip install superglue

    # 安装 LightGlue (通常指 ETH3D 的实现)
    python -m pip install lightglue

总结
Kornia 是“底座”，它自带了 LoFTR 和 SuperPoint。
但 SuperGlue 和 LightGlue 是“插件”，虽然能和 Kornia 配合使用，但需要单独安装。


## 
Plan: 双环境 PyISIS-Torch 协作
保留 asp360_new 作为 ISIS / ASP / isis_pybind 主环境，不在其中强行安装 torch；新建一个独立的 torch_env（推荐同样使用 Python 3.12）只负责 SuperPoint / LoFTR 推理。两边不要尝试在同一 Python 进程里跨环境互相 import；改用中间图像/数组文件和标准 .key 匹配点文件做桥接。这条路线最稳、最贴合当前仓库现状，也最容易先跑通。

Steps

Phase 1 — 固定环境职责

asp360_new 只负责 isis_pybind / ISIS / ASP / Cube 读取、投影、导出和后续几何处理；不要再把“必须同进程 import torch”作为前提。该环境目前已经验证可直接 import isis_pybind，即使没有 torch 也能工作。
新建独立深度匹配环境，推荐命名为 torch_sp 或 torch_loftr，Python 版本与 asp360_new 保持一致为 3.12，减少未来脚本兼容和中间格式处理差异。推荐安装命令：conda create -n torch_sp python=3.12 -y，然后 conda activate torch_sp。
在 torch_sp 中安装 CPU 版 PyTorch 与基础依赖。推荐命令：conda install -n torch_sp -c pytorch -c conda-forge pytorch cpuonly torchvision torchaudio numpy scipy pillow matplotlib opencv -y。如果只做 SuperPoint/LoFTR，torchvision / torchaudio 不是绝对必需，但保留通常更省后续折腾。
在 torch_sp 中安装 Kornia / LoFTR 支持。推荐命令：python -m pip install "kornia[loftr]"。若后续要跑仓库里的 lightglue / superglue 路径，再按需追加 python -m pip install lightglue superglue-pretrained-network。当前你提到的是 SuperPoint，仓库现有实现优先复用 Kornia SuperPoint，因此不需要单独再找一个 SuperPoint 包。
Phase 2 — 定义双环境交换契约

推荐使用“图像输入 + .key 输出”的最小桥接格式。asp360_new 将左右 Cube 导出成 png / tif（或必要时导出 npy），torch_sp 读取这些标准文件跑深度匹配，再输出 left.key 和 right.key。
优先选择 .key 作为回写格式，因为仓库已有下游消费链路可复用，尤其是 isis_stereo_dem.py 的 from-key 路径。这样双环境之间的耦合最小，不需要在 Torch 环境中安装 isis_pybind。
若后续你需要保存更多置信度、尺度或方向信息，可在 .key 之外附加 .json / .npz sidecar；但首版最小闭环建议先只传二维点对。
Phase 3 — Env A (asp360_new) 的导出与回读

从 Cube 读取与导出时，优先复用仓库现有能力，不要发明新的文件约定。可复用 Isis.Cube / Isis.Brick 做数组读取，或复用高层导出器 Isis.TiffExporter / Isis.QtExporter 导出标准图像。 depends on 1
参考现有 image_match 与 controlnet_construct 中的 DOM/影像准备逻辑，定义一个固定输出目录，例如 runtime/dual_env_match/<pair_id>/exports/，包含 left.png、right.png、可选的 metadata.json。 parallel with step 3.3
匹配完成后，仍在 asp360_new 中读取 left.key / right.key，并将其交给已有几何/DEM/ControlNet 工作流；首选复用 examples/dem_extract/isis_stereo_dem.py from-key ...。 depends on 2
Phase 4 — Env B (torch_sp) 的深度匹配

在 torch_sp 中新建一个“只依赖标准图像文件”的匹配入口，输入为 left.png / right.png 或 left.tif / right.tif，输出为 .key 点对。该入口应只依赖 torch、kornia、opencv、numpy，不要依赖 isis_pybind。 depends on 1, 2
优先复用仓库现有深度匹配包装层：deep_frontends.py 中的 SuperPointFrontend、deep_matchers.py 中的 LoFTRMatcher，以及 deep_adapter.py 中的 DeepMatcherAdapter。这能避免重新写一套 torch 推理逻辑。 depends on 4.1
SuperPoint 工作流建议分两步：先用 SuperPointFrontend.extract() 产出左右关键点/描述子，再选择匹配器；若只要“SuperPoint + 简单匹配”，可以在 torch_sp 中加一个轻量 BF/NN 匹配层；若要端到端深度匹配，可直接改用仓库现成的 lightglue / superglue / loftr 路线。 depends on 4.2
把最终匹配点统一写成仓库下游可消费的 .key 文件；如需兼容 dem_extract，保持左/右点索引一一对应，不在回写阶段做跨文件顺序打乱。 depends on 4.3
Phase 5 — 验证与扩展决策

先验证两个环境都能独立工作：asp360_new 中验证 import isis_pybind 和 Cube 导出；torch_sp 中验证 import torch、from kornia.feature import LoFTR、以及 SuperPointFrontend / LoFTRMatcher 最小推理。 depends on 1, 4
再做最小闭环：Cube -> left/right image export -> torch_sp 深度匹配 -> left/right .key -> asp360_new from-key 消费。 depends on 3, 4
只有在这个双环境闭环稳定后，才评估是否值得做“统一环境版 PyISIS + torch 同进程方案”。这一步当前明确不在本次方案范围内。 depends on 5.2
Relevant files

deep_frontends.py — 现有 SuperPointFrontend、LoFTRFrontend 与可选 torch 依赖处理。
deep_matchers.py — 现有 LoFTRMatcher / LightGlueMatcher / SuperGlueMatcher 包装层。
deep_adapter.py — 深度前端与匹配器路由入口，适合作为 Torch 环境匹配脚本的核心复用点。
loftr_simple.py — 最小 LoFTR 示例，可作为 torch_sp 安装验证样板。
isis_stereo_dem.py — 已有 from-key 消费链路，是 .key 桥接格式的最佳下游目标。
image_match.py — 现有影像匹配 CLI，总体流程和输出组织可作为 Env A 导出/消费的参考。
bind_low_level_cube_io.cpp — Isis.Cube / Isis.Brick / Isis.Buffer 绑定来源，用于确认 Cube 数组导出能力。
bind_high_level_cube_io.cpp — TiffExporter / QtExporter 绑定来源，用于确认标准图像导出能力。
Verification

在 asp360_new 中验证基础能力：运行 /home/gengxun/miniconda3/envs/asp360_new/bin/python -c "import isis_pybind as ip; print(hasattr(ip, 'Cube'), hasattr(ip, 'TiffExporter'))"，确认不依赖 torch 也能读 Cube / 导出图。
在 torch_sp 中验证深度能力：运行 python -c "import torch, kornia; from kornia.feature import LoFTR; print(torch.__version__, kornia.__version__)"。
用 loftr_simple.py 在 torch_sp 中做最小演示，确认新环境本身能完成一对普通图像匹配。
用一个真实左右 Cube 样本在 asp360_new 中导出 left.png / right.png，再在 torch_sp 中生成 left.key / right.key，最后在 asp360_new 中走 examples/dem_extract/isis_stereo_dem.py from-key ... 做端到端最小闭环。
若首版只做 SuperPoint 而非 LoFTR，额外验证关键点数量、匹配点数量和回写 .key 后的左右点数一致，避免下游几何阶段因为点对错位失败。
Decisions

采用“双环境 + 文件桥接”，不采用“跨环境直接 import 另一个 conda 环境的包”。
新 Torch 环境推荐与 asp360_new 使用相同 Python minor 版本 3.12，以降低兼容风险；这不是硬性要求，但属于推荐默认。
桥接格式优先使用仓库现有 .key，而不是自定义数据库、socket 或跨环境 Python RPC。
本次方案包含具体安装命令与流程设计，不包含直接改仓库代码实现新的导出/匹配 CLI。
本次方案默认 CPU-first；GPU 版可以后续在同一流程上替换 PyTorch 安装命令，不影响双环境边界设计。
Further Considerations

若你最终目标是“同一个 Python 脚本里 PyISIS 读 Cube 后立即调用 SuperPoint”，那双环境方案只是过渡；长期推荐做一个新的统一环境，而不是继续强行扩容现有 asp360_new。推荐选项：先按双环境方案跑通闭环，再决定是否做统一环境。
如果你需要的不只是 .key 点对，而是还要保留置信度、描述子或匹配分数，建议在 .key 之外并行输出 .json 或 .npz sidecar，但不要让下游几何流程依赖这些扩展字段。
若后续要让 Torch 环境直接复用仓库 Python 包，优先把“导出图像 -> 深度匹配 -> 写 .key”包装成一个明确的独立脚本，而不是让 torch_sp 直接 import 大而全的高层 pipeline。
安装命令汇总
推荐的双环境安装命令就是这组：

conda create -n torch_sp python=3.12 -y
conda activate torch_sp
conda install -n torch_sp -c pytorch -c conda-forge pytorch cpuonly torchvision torchaudio numpy scipy pillow matplotlib opencv -y
python -m pip install "kornia[loftr]"
如果你只想先验证 SuperPoint / LoFTR，这组就够了。
如果后面还想跑仓库里的 lightglue / superglue 路径，再额外安装：

python -m pip install lightglue superglue-pretrained-network
当前状态
 核对 LoFTR 依赖路径
 确认 asp360_new Python 环境
 安装 Torch 与 Kornia
 验证 LoFTR 可导入
 汇总安装结果与用法
如果你认可这个方案，我下一步可以继续帮你把它细化成更落地的一版——例如直接给你一份“Env A 导出什么文件、Env B 回写什么字段、目录怎么组织”的执行蓝图。

正确的安装命令（CPU 版）
请使用以下命令代替：
bash


##$ 推荐方案：使用 Python 3.10
为了保证你提到的所有库（LoFTR, SuperPoint, SuperGlue, LightGlue）都能一键安装、稳定运行，请使用 Python 3.10。

# 1. 创建环境 (指定 python=3.10)
mamba create -n vision python=3.10 -y
mamba activate vision

# 2. 安装 PyTorch (CUDA 11.8)
mamba install pytorch torchvision torchaudio pytorch-cuda=11.8 -c pytorch -c nvidia -y

# 3. 安装 Kornia (含 LoFTR 和 SuperPoint)
pip install "kornia[loftr]"

# 4. 安装 LightGlue 和 SuperGlue
# 先安装编译工具，防止报错
mamba install -c conda-forge ninja setuptools -y
# 再安装算法库 (Python 3.10 下成功率最高)
pip install lightglue superglue


# CPU 版本，无ＣＵＤＡ
既然你的机器没有 CUDA（即没有 NVIDIA 显卡，或者无法使用 GPU 加速），安装带有 pytorch-cuda=11.8 的版本不仅浪费磁盘空间（会下载几个 G 的无用 CUDA 库文件），还可能导致在导入 PyTorch 时出现不必要的警告或错误。
你应该安装 CPU 版本。
✅ 正确的安装命令（CPU 版）
请使用以下命令代替：

mamba install pytorch torchvision torchaudio cpuonly -c pytorch -y

# 使用国内镜像
pip install "kornia[loftr]" -i https://pypi.tuna.tsinghua.edu.cn/simple

python -m pip install lightglue superglue-pretrained-network \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    --timeout 1000 \
    --prefer-binary

    方案 B：分步安装（绕过依赖冲突）
不要一次性安装两个包，先安装基础依赖，再安装主包。
bash


＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃
## 安装ＰＹＴＯＲＣＨ

# 1. 先安装 torch (确保基础环境干净)
pip install torch torchvision torchaudio -i https://pypi.tuna.tsinghua.edu.cn/simple

# 2. 再尝试安装 lightglue (分开装能看清楚到底是哪个依赖卡住了)
pip install lightglue -i https://pypi.tuna.tsinghua.edu.cn/simple --prefer-binary

方案 C：使用 Conda/Mamba 安装（推荐）
既然你之前用过 Mamba，Conda 通常能更好地处理复杂的 C++/CUDA 依赖。
bash

# LightGlue 官方推荐的安装方式（如果 conda-forge 已收录）
conda install -c conda-forge lightglue

# 或者使用 mamba (速度更快)
mamba install -c conda-forge lightglue

3. 补充建议

    忽略 superglue-pretrained-network：这个库已经比较老了，且与 LightGlue 的环境需求可能冲突。如果你已经安装了 LightGlue，通常不需要再装这个，LightGlue 自带预训练模型。
    终极方案：如果必须用 Python 3.12，你可能需要从源码编译（非常麻烦，需要配置 CUDA 环境），建议直接降级 Python。

总结：大概率是 Python 版本问题。请先运行 python --version 确认，如果是 3.12，请换用 3.10 环境。


# 安装ＳＵＥＰＲＰＯＩＮＴ＋ＳＵＰＥＲＧＬＵＥ
# 1. 克隆官方仓库
git clone https://github.com/magicleap/SuperGluePretrainedNetwork.git

# 2. 进入目录
cd SuperGluePretrainedNetwork

# 3. 安装依赖
# 使用清华源加速安装 requirements.txt 中的包
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple






## 





## 安装至conda asp360_new，保证兼容。
# 直接使用 Pip 安装 (不依赖 Conda 的频道配置，最稳妥)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

pip install kornia

pip install albumentations -i https://pypi.tuna.tsinghua.edu.cn/simple

pip install ray -i https://pypi.tuna.tsinghua.edu.cn/simple