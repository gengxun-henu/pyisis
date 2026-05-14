"""LoFTR 简单匹配与结果可视化示例。

Author: Geng Xun
Created: 2026-05-11
Updated: 2026-05-11  Geng Xun 添加匹配结果绘图与输出保存逻辑
"""

# users should install kornia with loftr support: pip install kornia[loftr]
import cv2
import numpy as np
import torch
from kornia.feature import LoFTR, default_cfg


def resize_to_8(img):
    """将图像尺寸裁到可被 8 整除，满足 LoFTR 输入要求。"""
    h, w = img.shape
    new_h = (h // 8) * 8
    new_w = (w // 8) * 8
    return cv2.resize(img, (new_w, new_h))


def draw_matches(img0, img1, mkpts0, mkpts1, mconf, out_path="result.png"):
    """将两幅灰度图的 LoFTR 匹配结果绘制到同一画布并保存。"""
    h0, w0 = img0.shape
    h1, w1 = img1.shape

    canvas = np.zeros((max(h0, h1), w0 + w1, 3), dtype=np.uint8)
    canvas[:h0, :w0] = cv2.cvtColor(img0, cv2.COLOR_GRAY2BGR)
    canvas[:h1, w0:w0 + w1] = cv2.cvtColor(img1, cv2.COLOR_GRAY2BGR)

    if len(mkpts0) == 0:
        cv2.imwrite(out_path, canvas)
        print(f"未找到匹配点，已输出空白拼接图到: {out_path}")
        return

    confidence = np.asarray(mconf, dtype=np.float32)
    conf_min = float(confidence.min())
    conf_max = float(confidence.max())
    if conf_max > conf_min:
        normalized = (confidence - conf_min) / (conf_max - conf_min)
    else:
        normalized = np.ones_like(confidence, dtype=np.float32)

    color_values = np.clip((normalized * 255).astype(np.uint8), 0, 255).reshape(-1, 1)
    colors = cv2.applyColorMap(color_values, cv2.COLORMAP_JET).reshape(-1, 3)

    for i, (pt0, pt1) in enumerate(zip(mkpts0, mkpts1)):
        x0, y0 = int(round(pt0[0])), int(round(pt0[1]))
        x1, y1 = int(round(pt1[0])), int(round(pt1[1]))
        color = tuple(int(channel) for channel in colors[i])

        cv2.line(canvas, (x0, y0), (x1 + w0, y1), color, 1)
        cv2.circle(canvas, (x0, y0), 2, (0, 255, 0), -1)
        cv2.circle(canvas, (x1 + w0, y1), 2, (0, 255, 0), -1)

    cv2.imwrite(out_path, canvas)
    print(f"结果已保存至 {out_path}")

# 自动选择设备：优先 GPU，无 GPU 时回退到 CPU
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"当前推理设备: {device}")

# 1. 初始化模型
# 可选 'outdoor' 或 'indoor' 预训练权重
matcher = LoFTR(config=default_cfg).to(device)
matcher.eval()

# 2. 读取图像 (建议使用灰度图)
IMG1="/media/gengxun/Elements/data/lro/test_controlnet_python/pipe_test/dom_M104318871RE.tif"
IMG2="/media/gengxun/Elements/data/lro/test_controlnet_python/pipe_test/dom_M104311715RE.tif"
img0 = cv2.imread(IMG1, cv2.IMREAD_GRAYSCALE)
img1 = cv2.imread(IMG2, cv2.IMREAD_GRAYSCALE)

# 基础输入检查，避免后续在 shape 上直接炸掉
if img0 is None:
    raise FileNotFoundError(f"无法读取图像: {IMG1}")
if img1 is None:
    raise FileNotFoundError(f"无法读取图像: {IMG2}")

# 3. 数据预处理
# LoFTR 要求输入尺寸必须能被 8 整除

img0_resized = resize_to_8(img0)
img1_resized = resize_to_8(img1)

# 转换为 Tensor 并归一化到 [0, 1]
img0_tensor = (torch.from_numpy(img0_resized)[None][None].float() / 255.0).to(device)
img1_tensor = (torch.from_numpy(img1_resized)[None][None].float() / 255.0).to(device)

# 4. 推理匹配
with torch.no_grad():
    batch = {'image0': img0_tensor, 'image1': img1_tensor}
    matcher(batch)

# 5. 获取结果
# mkpts0 和 mkpts1 分别是两张图上的匹配点坐标
mkpts0 = batch['mkpts0_f'].cpu().numpy()
mkpts1 = batch['mkpts1_f'].cpu().numpy()
confidence = batch['mconf'].cpu().numpy()

print(f"找到 {len(mkpts0)} 对匹配点")
draw_matches(
    img0_resized,
    img1_resized,
    mkpts0,
    mkpts1,
    confidence,
    out_path="loftr_matches.png",
)