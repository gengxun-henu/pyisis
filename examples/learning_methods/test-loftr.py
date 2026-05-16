import torch
import kornia as K
from kornia.feature import LoFTR

# 初始化模型 (首次运行会自动下载权重，约 44MB)
# 使用 pretrained="outdoor" 或 "indoor"
matcher = LoFTR(pretrained='outdoor') 

print("LoFTR 安装成功！")