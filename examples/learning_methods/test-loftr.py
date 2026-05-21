"""LoFTR 导入与初始化冒烟测试脚本。

Author: Geng Xun
Created: 2026-05-21
Updated: 2026-05-21  Geng Xun 将脚本整理为仅验证 LoFTR 是否可引入并成功初始化。
"""

from __future__ import annotations

import ssl
from pathlib import Path
from urllib.error import URLError

import torch
from kornia.feature import LoFTR


def main() -> None:
	device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

	print(f"🔍 当前 PyTorch 版本: {torch.__version__}")
	print(f"🔍 当前设备: {device.type.upper()}")
	print("✅ 第一步：代码导入成功 (Kornia LoFTR 已找到)")
	print(f"📦 kornia 包路径: {Path(__import__('kornia').__file__).resolve()}")
	print(
		"📁 Torch 权重缓存目录: "
		f"{Path(torch.hub.get_dir()).resolve() / 'checkpoints'}"
	)

	try:
		matcher = LoFTR(pretrained="outdoor").eval().to(device)
	except ssl.SSLCertVerificationError as exc:
		print("❌ 初始化 LoFTR 预训练权重时发生 SSL 证书校验失败。")
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
	print(f"   matcher 设备: {next(matcher.parameters()).device}")
	print("🎉 当前脚本已按 LoFTR smoke test 路径就绪。")


if __name__ == "__main__":
	main()