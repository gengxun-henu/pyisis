"""Minimal ISISDATA package for pyisis smoke tests."""

# Copyright (c) 2026 Geng Xun, Henan University
# SPDX-License-Identifier: MIT

from __future__ import annotations

from pathlib import Path


def data_path() -> Path:
    """Return the packaged minimal ISISDATA root."""

    return Path(__file__).resolve().parent / "data"


__all__ = ["data_path"]
