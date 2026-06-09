#!/usr/bin/env python3
"""Generate split Nature-style figures from the Phase 8 benchmark report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib as mpl

mpl.use("Agg", force=True)
import matplotlib.pyplot as plt
import numpy as np


PAIR_ORDER = [
    "M104311715LE",
    "M104311715RE",
    "M104318871LE",
    "M104318871RE",
]

METHOD_COLORS = {
    "pyisis": "#4C78A8",
    "cpp": "#F58518",
}


def load_results(run_dir: Path) -> list[dict]:
    summary_path = run_dir / "reports" / "summary.json"
    with summary_path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    return list(payload["results"])


def by_label_and_method(results: list[dict]) -> dict[str, dict[str, dict]]:
    grouped: dict[str, dict[str, dict]] = {}
    for row in results:
        grouped.setdefault(row["label"], {})[row["implementation"]] = row
    return grouped


def pair_id(label: str) -> str:
    return label.rsplit("_", 1)[-1]


def save_pub(fig: plt.Figure, output_base: Path) -> None:
    fig.savefig(f"{output_base}.svg", bbox_inches="tight")
    fig.savefig(f"{output_base}.pdf", bbox_inches="tight")
    fig.savefig(f"{output_base}.tiff", dpi=600, bbox_inches="tight")
    fig.savefig(f"{output_base}.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def setup_style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "font.size": 7,
            "axes.spines.right": False,
            "axes.spines.top": False,
            "axes.linewidth": 0.8,
            "legend.frameon": False,
            "xtick.major.size": 2.5,
            "ytick.major.size": 2.5,
        }
    )


def grouped_method_bars(
    ax: plt.Axes,
    labels: list[str],
    py_values: list[float],
    cpp_values: list[float],
    ylabel: str,
) -> None:
    x = np.arange(len(labels), dtype=float)
    width = 0.34
    ax.bar(x - width / 2, py_values, width=width, color=METHOD_COLORS["pyisis"], label="PyISIS")
    ax.bar(x + width / 2, cpp_values, width=width, color=METHOD_COLORS["cpp"], label="ISIS C++")
    ax.set_xticks(x, labels, rotation=25, ha="right")
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", color="#D9D9D9", linewidth=0.5)
    ax.set_axisbelow(True)
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0), borderaxespad=0.0)


def add_ratio_labels(ax: plt.Axes, labels: list[str], py_values: list[float], cpp_values: list[float]) -> None:
    ymax = max(py_values + cpp_values)
    ax.set_ylim(0, ymax * 1.20)
    for index, (py_value, cpp_value) in enumerate(zip(py_values, cpp_values, strict=True)):
        ratio = py_value / cpp_value if cpp_value else float("nan")
        ax.text(index, ymax * 1.08, f"{ratio:.2f}x", ha="center", va="bottom", fontsize=6.5, color="#333333")


def make_ori_dom_performance(grouped: dict[str, dict[str, dict]], out_dir: Path) -> None:
    labels = PAIR_ORDER
    py_values = [grouped[f"dom_ori_{label}"]["pyisis"]["ori_to_dom_seconds"] for label in labels]
    cpp_values = [grouped[f"dom_ori_{label}"]["cpp"]["ori_to_dom_seconds"] for label in labels]
    fig, ax = plt.subplots(figsize=(3.45, 2.35), constrained_layout=True)
    grouped_method_bars(ax, labels, py_values, cpp_values, "seconds per 1M ORI pixels")
    add_ratio_labels(ax, labels, py_values, cpp_values)
    ax.set_title("ORI->DOM projection performance", loc="left", fontweight="bold")
    save_pub(fig, out_dir / "fig01_ori_dom_performance")


def make_dom_ori_performance(grouped: dict[str, dict[str, dict]], out_dir: Path) -> None:
    labels = PAIR_ORDER
    py_values = [grouped[f"dom_ori_{label}"]["pyisis"]["dom_to_ori_seconds"] for label in labels]
    cpp_values = [grouped[f"dom_ori_{label}"]["cpp"]["dom_to_ori_seconds"] for label in labels]
    fig, ax = plt.subplots(figsize=(3.45, 2.35), constrained_layout=True)
    grouped_method_bars(ax, labels, py_values, cpp_values, "seconds per 1M DOM points")
    add_ratio_labels(ax, labels, py_values, cpp_values)
    ax.set_title("DOM->ORI back-projection performance", loc="left", fontweight="bold")
    save_pub(fig, out_dir / "fig02_dom_ori_performance")


def make_dom_ori_accuracy(grouped: dict[str, dict[str, dict]], out_dir: Path) -> None:
    labels = PAIR_ORDER
    metrics = [
        ("pixel_error_abs_mean", "mean"),
        ("pixel_error_abs_rms", "RMS"),
        ("pixel_error_abs_max", "max"),
    ]
    x = np.arange(len(labels), dtype=float)
    width = 0.22
    colors = ["#72B7B2", "#54A24B", "#E45756"]
    fig, (ax, rate_ax) = plt.subplots(
        2,
        1,
        figsize=(3.85, 2.95),
        gridspec_kw={"height_ratios": [4.0, 0.95]},
        constrained_layout=True,
    )
    for offset, (key, name), color in zip([-width, 0.0, width], metrics, colors, strict=True):
        values = [grouped[f"dom_ori_{label}"]["pyisis"][key] * 1_000.0 for label in labels]
        ax.bar(x + offset, values, width=width, label=name, color=color)
    success_values = [grouped[f"dom_ori_{label}"]["pyisis"]["roundtrip_success_rate"] for label in labels]
    ax.set_xticks(x, labels, rotation=25, ha="right")
    ax.set_ylabel("round-trip pixel error (x10^-3 px)")
    ax.set_title("DOM/ORI round-trip accuracy", loc="left", fontweight="bold")
    ax.grid(axis="y", color="#D9D9D9", linewidth=0.5)
    ax.set_axisbelow(True)
    ax.legend(loc="upper right", ncols=3, columnspacing=0.8, handlelength=1.0)

    rate_ax.set_xlim(-0.65, len(labels) - 0.35)
    rate_ax.set_ylim(0, 1)
    rate_ax.axis("off")
    rate_ax.text(
        0.5,
        0.18,
        "round-trip success rate",
        transform=rate_ax.transAxes,
        ha="center",
        va="center",
        fontsize=6.5,
        color="#333333",
    )
    for index, success in enumerate(success_values):
        rate_ax.text(index, 0.70, f"{success * 100:.4f}%", ha="center", va="center", fontsize=6.5)
    save_pub(fig, out_dir / "fig03_dom_ori_roundtrip_accuracy")


def make_solar_performance(grouped: dict[str, dict[str, dict]], out_dir: Path) -> None:
    labels = PAIR_ORDER
    py_values = [grouped[f"solar_{label}"]["pyisis"]["core_seconds"] for label in labels]
    cpp_values = [grouped[f"solar_{label}"]["cpp"]["core_seconds"] for label in labels]
    fig, ax = plt.subplots(figsize=(3.45, 2.35), constrained_layout=True)
    grouped_method_bars(ax, labels, py_values, cpp_values, "seconds per 1M pixels")
    add_ratio_labels(ax, labels, py_values, cpp_values)
    ax.set_title("Solar angle computation performance", loc="left", fontweight="bold")
    save_pub(fig, out_dir / "fig04_solar_performance")


def make_solar_accuracy(grouped: dict[str, dict[str, dict]], out_dir: Path) -> None:
    labels = PAIR_ORDER
    rows = []
    for label in labels:
        row = grouped[f"solar_{label}"]["pyisis"]
        rows.append(
            [
                row["azimuth_abs_max"],
                row["azimuth_abs_rms"],
                row["elevation_abs_max"],
                row["elevation_abs_rms"],
            ]
        )
    matrix = np.array(rows, dtype=float)
    max_value = float(np.nanmax(matrix)) if matrix.size else 0.0
    if max_value > 0.0:
        exponent = int(np.floor(np.log10(max_value)))
        scale_factor = 10.0 ** (-exponent) if exponent < 0 else 1.0
    else:
        scale_factor = 1.0
    matrix = matrix * scale_factor
    vmax = max(1.0e-12, float(np.nanmax(matrix)))
    if scale_factor == 1.0:
        unit_label = "deg"
    else:
        power = int(round(np.log10(scale_factor)))
        unit_label = f"x10^{power} deg"

    def save_panel(
        panel_matrix: np.ndarray,
        xticklabels: list[str],
        title: str,
        output_name: str,
    ) -> None:
        fig, ax = plt.subplots(figsize=(3.45, 2.35), constrained_layout=True)
        image = ax.imshow(panel_matrix, cmap="Blues", vmin=0.0, vmax=vmax)
        ax.set_xticks(np.arange(len(xticklabels)), xticklabels)
        ax.set_yticks(np.arange(len(labels)), labels)
        ax.set_title(title, loc="left", fontweight="bold")
        ax.set_xlabel(f"absolute error ({unit_label})")
        for row_index in range(panel_matrix.shape[0]):
            for col_index in range(panel_matrix.shape[1]):
                ax.text(col_index, row_index, f"{panel_matrix[row_index, col_index]:.3f}", ha="center", va="center")
        colorbar = fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
        colorbar.set_label(unit_label)
        save_pub(fig, out_dir / output_name)

    save_panel(
        matrix[:, :2],
        ["azimuth\nmax", "azimuth\nRMS"],
        "Solar azimuth numerical agreement",
        "fig05a_solar_azimuth_accuracy",
    )
    save_panel(
        matrix[:, 2:],
        ["elevation\nmax", "elevation\nRMS"],
        "Solar elevation numerical agreement",
        "fig05b_solar_elevation_accuracy",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=Path("work/isis_cpp_pyisis_benchmark_phase8_final_combined/lro_paper_use_pyisis_cpp_million_points_20260601"),
    )
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()

    setup_style()
    results = load_results(args.run_dir)
    grouped = by_label_and_method(results)
    out_dir = args.output_dir or args.run_dir / "reports" / "split_figures"
    out_dir.mkdir(parents=True, exist_ok=True)

    make_ori_dom_performance(grouped, out_dir)
    make_dom_ori_performance(grouped, out_dir)
    make_dom_ori_accuracy(grouped, out_dir)
    make_solar_performance(grouped, out_dir)
    make_solar_accuracy(grouped, out_dir)

    print(out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
