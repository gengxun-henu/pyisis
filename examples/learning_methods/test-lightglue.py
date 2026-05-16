"""LightGlue CPU 冒烟测试脚本。

Author: Geng Xun
Created: 2026-05-11
Updated: 2026-05-11  Geng Xun 改为默认自动选择 CPU，并将 SSL 下载失败提示写清楚
"""

from __future__ import annotations

import ssl
from pathlib import Path
from urllib.error import URLError

import torch
from lightglue import LightGlue, SuperPoint


def main() -> None:
	device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

	print(f"🔍 当前 PyTorch 版本: {torch.__version__}")
	print(f"🔍 当前设备: {device.type.upper()}")
	print("✅ 第一步：代码导入成功 (LightGlue / SuperPoint 已找到)")
	print(f"📦 LightGlue 包路径: {Path(__import__('lightglue').__file__).resolve()}")
	print(
		"📁 Torch 权重缓存目录: "
		f"{Path(torch.hub.get_dir()).resolve() / 'checkpoints'}"
	)

	try:
		extractor = SuperPoint(max_num_keypoints=2048).eval().to(device)
		matcher = LightGlue(features="superpoint").eval().to(device)
	except ssl.SSLCertVerificationError as exc:
		print("❌ 下载 LightGlue/SuperPoint 预训练权重时发生 SSL 证书校验失败。")
		print(f"   具体错误: {exc}")
		print("   这说明包已经找到了，但 Python 无法通过 HTTPS 验证远端证书。")
		print("   可行做法：")
		print("   1. 修复当前 conda 环境中的 CA 证书；")
		print("   2. 手动下载权重到 torch hub 的 checkpoints 目录；")
		print("   3. 若你本机已有权重缓存，确认文件名是否正确。")
		return
	except URLError as exc:
		print("❌ 初始化模型时网络下载失败。")
		print(f"   具体错误: {exc}")
		print("   包导入本身没有问题，失败发生在预训练权重下载阶段。")
		return
	except Exception as exc:
		print(f"❌ 初始化模型失败: {type(exc).__name__}: {exc}")
		return

	print("✅ 模型初始化成功。")
	print(f"   extractor 设备: {next(extractor.parameters()).device}")
	print(f"   matcher 设备: {next(matcher.parameters()).device}")
	print("🎉 当前脚本已按 CPU 路径就绪。")


if __name__ == "__main__":
	main()