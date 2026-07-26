"""Promote one ranked ISIS APP wave into the tracked Windows manifest."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--priority-csv", type=Path, required=True)
    parser.add_argument("--wave", required=True)
    parser.add_argument("--expected-additions", type=int, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    with args.priority_csv.open(encoding="utf-8", newline="") as priority_file:
        selected_rows = [
            row
            for row in csv.DictReader(priority_file)
            if row["recommended_wave"] == args.wave
        ]

    if len(selected_rows) != args.expected_additions:
        raise ValueError(
            f"expected {args.expected_additions} additions for {args.wave}, "
            f"found {len(selected_rows)}"
        )

    apps = {app["name"]: app for app in manifest["apps"]}
    duplicates = sorted(row["app"] for row in selected_rows if row["app"] in apps)
    if duplicates:
        raise ValueError(f"wave contains existing manifest APPs: {duplicates}")

    for row in selected_rows:
        name = row["app"]
        module = row["module"]
        apps[name] = {
            "name": name,
            "component": f"apps-{module}",
            "source_dir": row["source_dir"],
            "xml": f"{row['source_dir']}/{name}.xml",
            "smoke_tier": "startup",
            "selection_wave": args.wave,
            "versions": {
                "9.0.0": {
                    "status": "supported",
                    "build_status": "compiled_installed",
                    "smoke_status": "not_individually_recorded",
                    "linux_comparison": "pending",
                },
                "10.0.0": {
                    "status": "experimental",
                    "build_status": "implementation_ready",
                    "smoke_status": "pending",
                    "linux_comparison": "pending",
                },
            },
            "release_component": f"apps-{module}",
        }

    manifest["apps"] = [apps[name] for name in sorted(apps)]
    args.manifest.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"promoted {len(selected_rows)} APPs from {args.wave}; "
        f"manifest total is {len(apps)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
