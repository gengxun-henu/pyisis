#!/usr/bin/env python3
"""Prepare reduced LRO polar cubes and 10 m DOMs for routing benchmarks."""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import shlex
import subprocess
import sys
import time
from typing import Any


DEFAULT_SOURCE_ROOT = Path(
    "/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/"
    "texture_lighting_pair_selection/original_gsd"
)
DEFAULT_OUTPUT_ROOT = Path("work/lro_polar_adaptive_routing_preprocess")
DEFAULT_REDUCE_SSCALE = 10
DEFAULT_REDUCE_LSCALE = 10
DEFAULT_DOM_RESOLUTION_METERS = 10.0


@dataclass(frozen=True, slots=True)
class CubeProduct:
    product_id: str
    source_cube: Path
    reduced_cube: Path
    dom_cube: Path


@dataclass(frozen=True, slots=True)
class CommandRecord:
    product_id: str
    stage: str
    command: list[str]
    output_path: str
    skipped: bool = False
    return_code: int | None = None
    seconds: float | None = None


def _product_id_from_echo_cal(path: Path) -> str:
    suffix = ".echo.cal.cub"
    name = path.name
    if not name.endswith(suffix):
        raise ValueError(f"Expected *.echo.cal.cub input, got: {path}")
    return name[: -len(suffix)]


def _read_path_list(list_path: Path, *, base_dir: Path) -> list[Path]:
    if not list_path.exists():
        raise FileNotFoundError(f"List file not found: {list_path}")
    paths: list[Path] = []
    for raw_line in list_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        path = Path(line)
        if not path.is_absolute():
            path = base_dir / path
        paths.append(path.resolve())
    return paths


def _build_products(
    *,
    source_root: Path,
    output_root: Path,
    max_cubes: int | None,
) -> list[CubeProduct]:
    source_work_dir = source_root / "work"
    original_list = source_work_dir / "original_images.lis"
    source_cubes = _read_path_list(original_list, base_dir=source_work_dir)
    if max_cubes is not None:
        source_cubes = source_cubes[: max(0, max_cubes)]
    if not source_cubes:
        raise ValueError("No source cubes selected.")

    reduced_dir = output_root / "reduced_cubes"
    dom_dir = output_root / "doms_10m"
    products: list[CubeProduct] = []
    for source_cube in source_cubes:
        if not source_cube.exists():
            raise FileNotFoundError(f"Source cube not found: {source_cube}")
        product_id = _product_id_from_echo_cal(source_cube)
        products.append(
            CubeProduct(
                product_id=product_id,
                source_cube=source_cube,
                reduced_cube=reduced_dir / f"REDUCED_{source_cube.name}",
                dom_cube=dom_dir / f"dom_REDUCED_{product_id}.cub",
            )
        )
    return products


def _reduce_command(product: CubeProduct, *, sscale: int, lscale: int) -> list[str]:
    return [
        "reduce",
        f"from={product.source_cube}",
        f"to={product.reduced_cube}",
        f"sscale={sscale}",
        f"lscale={lscale}",
    ]


def _cam2map_command(product: CubeProduct, *, map_path: Path, resolution_meters: float) -> list[str]:
    return [
        "cam2map",
        f"from={product.reduced_cube}",
        f"map={map_path}",
        f"to={product.dom_cube}",
        "interp=bilinear",
        "warpalgorithm=forwardpatch",
        "patchsize=21",
        "pixres=mpp",
        f"resolution={resolution_meters:g}",
    ]


def _shell_join(command: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in command)


def _run_command(command: list[str]) -> tuple[int, float]:
    start = time.perf_counter()
    completed = subprocess.run(command, check=False)
    return completed.returncode, time.perf_counter() - start


def _write_list(path: Path, values: list[Path]) -> None:
    path.write_text("\n".join(str(value) for value in values) + "\n", encoding="utf-8")


def _copy_map_with_resolution_note(source_map: Path, target_map: Path, *, resolution_meters: float) -> None:
    target_map.write_text(source_map.read_text(encoding="utf-8"), encoding="utf-8")
    (target_map.parent / "map_resolution_note.txt").write_text(
        "The copied map is unchanged. This benchmark sets DOM resolution through "
        f"cam2map pixres=mpp resolution={resolution_meters:g}.\n",
        encoding="utf-8",
    )


def _write_reduced_pair_manifest(
    *,
    source_pair_csv: Path,
    output_pair_csv: Path,
    product_by_id: dict[str, CubeProduct],
    include_unselected: bool,
) -> None:
    if not source_pair_csv.exists():
        raise FileNotFoundError(f"Selected-pair CSV not found: {source_pair_csv}")
    with source_pair_csv.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError(f"Selected-pair CSV is empty: {source_pair_csv}")

    fieldnames = [
        "pair_folder",
        "side",
        "product_id",
        "source_echo_cal_cube",
        "echo_cal_cube",
        "source_dom_cube",
        "dom_cube",
        "all_exist",
    ]
    output_pair_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_pair_csv.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            product_id = str(row["product_id"])
            product = product_by_id.get(product_id)
            if product is None:
                if include_unselected:
                    continue
                raise ValueError(
                    f"Pair manifest references product {product_id!r}, "
                    "but it was not selected for preprocessing."
                )
            writer.writerow(
                {
                    "pair_folder": row["pair_folder"],
                    "side": row["side"],
                    "product_id": product_id,
                    "source_echo_cal_cube": row.get("echo_cal_cube", ""),
                    "echo_cal_cube": str(product.reduced_cube),
                    "source_dom_cube": row.get("dom_cube", ""),
                    "dom_cube": str(product.dom_cube),
                    "all_exist": str(product.reduced_cube.exists() and product.dom_cube.exists()),
                }
            )


def _write_manifest(
    *,
    output_root: Path,
    source_root: Path,
    source_map: Path,
    copied_map: Path,
    products: list[CubeProduct],
    commands: list[CommandRecord],
    args: argparse.Namespace,
) -> None:
    payload: dict[str, Any] = {
        "source_root": str(source_root),
        "output_root": str(output_root),
        "source_map": str(source_map),
        "copied_map": str(copied_map),
        "reduce": {"sscale": args.sscale, "lscale": args.lscale},
        "cam2map": {"resolution_meters": args.dom_resolution_meters},
        "execute": bool(args.execute),
        "skip_existing": bool(args.skip_existing),
        "products": [asdict(product) for product in products],
        "commands": [asdict(record) for record in commands],
    }
    (output_root / "preprocess_manifest.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
    shell_lines = [_shell_join(record.command) for record in commands if not record.skipped]
    (output_root / "preprocess_commands.sh").write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\n\n" + "\n".join(shell_lines) + "\n",
        encoding="utf-8",
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--sscale", type=int, default=DEFAULT_REDUCE_SSCALE)
    parser.add_argument("--lscale", type=int, default=DEFAULT_REDUCE_LSCALE)
    parser.add_argument("--dom-resolution-meters", type=float, default=DEFAULT_DOM_RESOLUTION_METERS)
    parser.add_argument("--max-cubes", type=int, default=None)
    parser.add_argument("--execute", action="store_true", help="Run reduce and cam2map. Default is dry-run.")
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument(
        "--allow-partial-pairs",
        action="store_true",
        help="Write only pair rows whose products were selected by --max-cubes.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    source_root = args.source_root.expanduser().resolve()
    output_root = args.output_root.expanduser().resolve()
    source_work_dir = source_root / "work"
    source_map = source_work_dir / "lunar_polarstereographic.map"
    source_pair_csv = source_root / "selected_pair_original_gsd_paths.csv"
    if not source_map.exists():
        raise FileNotFoundError(f"Map file not found: {source_map}")

    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "reduced_cubes").mkdir(parents=True, exist_ok=True)
    (output_root / "doms_10m").mkdir(parents=True, exist_ok=True)
    copied_map = output_root / "lunar_polarstereographic_source.map"
    _copy_map_with_resolution_note(source_map, copied_map, resolution_meters=args.dom_resolution_meters)

    products = _build_products(source_root=source_root, output_root=output_root, max_cubes=args.max_cubes)
    commands: list[CommandRecord] = []
    for product in products:
        reduce_command = _reduce_command(product, sscale=args.sscale, lscale=args.lscale)
        reduce_skipped = args.skip_existing and product.reduced_cube.exists()
        reduce_record = CommandRecord(
            product_id=product.product_id,
            stage="reduce",
            command=reduce_command,
            output_path=str(product.reduced_cube),
            skipped=reduce_skipped,
        )
        if args.execute and not reduce_skipped:
            return_code, seconds = _run_command(reduce_command)
            reduce_record = CommandRecord(
                product_id=product.product_id,
                stage="reduce",
                command=reduce_command,
                output_path=str(product.reduced_cube),
                skipped=False,
                return_code=return_code,
                seconds=seconds,
            )
            if return_code != 0:
                commands.append(reduce_record)
                _write_manifest(
                    output_root=output_root,
                    source_root=source_root,
                    source_map=source_map,
                    copied_map=copied_map,
                    products=products,
                    commands=commands,
                    args=args,
                )
                return return_code
        commands.append(reduce_record)

        cam2map_command = _cam2map_command(product, map_path=source_map, resolution_meters=args.dom_resolution_meters)
        cam2map_skipped = args.skip_existing and product.dom_cube.exists()
        cam2map_record = CommandRecord(
            product_id=product.product_id,
            stage="cam2map",
            command=cam2map_command,
            output_path=str(product.dom_cube),
            skipped=cam2map_skipped,
        )
        if args.execute and not cam2map_skipped:
            return_code, seconds = _run_command(cam2map_command)
            cam2map_record = CommandRecord(
                product_id=product.product_id,
                stage="cam2map",
                command=cam2map_command,
                output_path=str(product.dom_cube),
                skipped=False,
                return_code=return_code,
                seconds=seconds,
            )
            if return_code != 0:
                commands.append(cam2map_record)
                _write_manifest(
                    output_root=output_root,
                    source_root=source_root,
                    source_map=source_map,
                    copied_map=copied_map,
                    products=products,
                    commands=commands,
                    args=args,
                )
                return return_code
        commands.append(cam2map_record)

    _write_list(output_root / "reduced_original_images.lis", [product.reduced_cube for product in products])
    _write_list(output_root / "reduced_doms.lis", [product.dom_cube for product in products])
    _write_reduced_pair_manifest(
        source_pair_csv=source_pair_csv,
        output_pair_csv=output_root / "reduced_selected_pair_paths.csv",
        product_by_id={product.product_id: product for product in products},
        include_unselected=args.allow_partial_pairs,
    )
    _write_manifest(
        output_root=output_root,
        source_root=source_root,
        source_map=source_map,
        copied_map=copied_map,
        products=products,
        commands=commands,
        args=args,
    )
    print(json.dumps({"output_root": str(output_root), "product_count": len(products)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
