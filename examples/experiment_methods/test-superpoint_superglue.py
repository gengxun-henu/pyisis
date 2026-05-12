import torch
import cv2
import sys
import os
import numpy as np

# 将 SuperGlue 的项目路径加进去
sg_path = '/home/gengxun/PlanetaryMapping/asp360_new/SuperGluePretrainedNetwork-master'
if sg_path not in sys.path:
    sys.path.append(sg_path)


# 尝试导入 SuperPoint 和 SuperGlue 的类
# 注意：这是基于 magicleap/SuperGluePretrainedNetwork 项目的导入路径
try:
    from models.matching import Matching
    from models.utils import frame2tensor
    print("✅ 成功导入 SuperPoint & SuperGlue 核心模块")
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    print("提示：请确保你是在 SuperGluePretrainedNetwork 项目目录下，或者已经 pip install -e .")

# 检查 CUDA (虽然你是 CPU 环境，但代码通常会尝试调用 CUDA)
device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f"ℹ️ 当前运行设备: {device}")