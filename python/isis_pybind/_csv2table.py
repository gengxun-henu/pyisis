"""Cross-platform Python facade for the ISIS 10 csv2table application."""

# Copyright (c) 2026 Geng Xun, Henan University
# SPDX-License-Identifier: MIT

from __future__ import annotations

import os
from os import PathLike
from typing import Sequence

from ._app_runner import _run_isis_app


_ALLOWED_COLTYPES = {"Double", "Integer", "Float", "Text"}


def _is_windows() -> bool:
    return os.name == "nt"


def _build_csv2table_arguments(
    csv: str | PathLike[str],
    to: str | PathLike[str],
    tablename: str,
    *,
    label: str | PathLike[str] | None = None,
    coltypes: Sequence[str] | None = None,
) -> list[str]:
    if not isinstance(tablename, str) or not tablename.strip():
        raise ValueError("tablename must be a non-empty string")

    arguments = [
        f"CSV={os.fspath(csv)}",
        f"TO={os.fspath(to)}",
        f"TABLENAME={tablename}",
    ]
    if label is not None:
        arguments.append(f"LABEL={os.fspath(label)}")
    if coltypes is not None:
        values = list(coltypes)
        invalid = [value for value in values if value not in _ALLOWED_COLTYPES]
        if invalid:
            raise ValueError(f"Unsupported COLTYPES value: {invalid[0]}")
        if values:
            arguments.append(f"COLTYPES=({','.join(values)})")
    return arguments


def _native_csv2table(arguments: Sequence[str]) -> None:
    from ._isis_core import _csv2table_native

    _csv2table_native(list(arguments))


def csv2table(
    csv: str | PathLike[str],
    to: str | PathLike[str],
    tablename: str,
    *,
    label: str | PathLike[str] | None = None,
    coltypes: Sequence[str] | None = None,
) -> None:
    """Attach CSV rows as an ISIS table using the native ISIS 10 implementation."""

    arguments = _build_csv2table_arguments(
        csv,
        to,
        tablename,
        label=label,
        coltypes=coltypes,
    )
    try:
        if _is_windows():
            _run_isis_app("csv2table", arguments)
        else:
            _native_csv2table(arguments)
    except Exception as error:
        raise RuntimeError(f"csv2table failed: {error}") from error
