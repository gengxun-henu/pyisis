"""Fit polynomial disparity models from sparse keypoint pairs.

Author: Geng Xun
Created: 2026-05-10
Last Modified: 2026-05-10
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .key_pairs import KeyPointPair


@dataclass(frozen=True)
class DisparityModel:
    dx_coeffs: np.ndarray
    dy_coeffs: np.ndarray
    order: int
    dx_r_squared: float
    dy_r_squared: float
    prior_fallback: str | None = None

    def eval_dx(self, s: float, l: float) -> float:
        return float(_eval_poly(self.dx_coeffs, self.order, s, l))

    def eval_dy(self, s: float, l: float) -> float:
        return float(_eval_poly(self.dy_coeffs, self.order, s, l))


def _term_count(order: int) -> int:
    if order <= 0:
        return 1
    if order == 1:
        return 3
    if order == 2:
        return 6
    raise ValueError(f"Unsupported polynomial order: {order}")


def _build_design_matrix(samples: np.ndarray, lines: np.ndarray, order: int) -> np.ndarray:
    """Build the polynomial design matrix.

    For order=2 the term ordering is [1, s, l, s^2, s*l, l^2].
    For order=1 it is [1, s, l]. For order=0 it is [1].
    """
    rows = [np.ones_like(samples)]
    if order >= 1:
        rows.append(samples)
        rows.append(lines)
    if order >= 2:
        rows.append(samples ** 2)
        rows.append(samples * lines)
        rows.append(lines ** 2)
    return np.column_stack(rows)


def _eval_poly(coeffs: np.ndarray, order: int, s: float, l: float) -> float:
    terms = [1.0]
    if order >= 1:
        terms.append(s)
        terms.append(l)
    if order >= 2:
        terms.append(s * s)
        terms.append(s * l)
        terms.append(l * l)
    return float(np.dot(coeffs[: len(terms)], terms))


def _compute_r_squared(actual: np.ndarray, predicted: np.ndarray) -> float:
    ss_res = float(np.sum((actual - predicted) ** 2))
    ss_tot = float(np.sum((actual - np.mean(actual)) ** 2))
    if ss_tot == 0.0:
        return 1.0
    return 1.0 - ss_res / ss_tot


def fit_disparity_model(
    pairs: list[KeyPointPair],
    order: int = 2,
    min_points: int = 20,
) -> DisparityModel:
    """Fit dx/dy disparity polynomials from sparse keypoint pairs.

    If fewer than ``min_points`` pairs are available, falls back to mean
    disparity (constant term only).
    """
    if not pairs:
        raise ValueError("fit_disparity_model requires at least one keypoint pair.")

    samples = np.array([p.left_sample for p in pairs], dtype=np.float64)
    lines = np.array([p.left_line for p in pairs], dtype=np.float64)
    dx_vals = np.array([p.right_sample - p.left_sample for p in pairs], dtype=np.float64)
    dy_vals = np.array([p.right_line - p.left_line for p in pairs], dtype=np.float64)

    n_terms = _term_count(order)

    if len(pairs) < min_points:
        mean_dx = float(np.mean(dx_vals))
        mean_dy = float(np.mean(dy_vals))
        dx_coeffs = np.zeros(n_terms, dtype=np.float64)
        dy_coeffs = np.zeros(n_terms, dtype=np.float64)
        dx_coeffs[0] = mean_dx
        dy_coeffs[0] = mean_dy
        return DisparityModel(
            dx_coeffs=dx_coeffs,
            dy_coeffs=dy_coeffs,
            order=order,
            dx_r_squared=0.0,
            dy_r_squared=0.0,
            prior_fallback="mean_disparity",
        )

    A = _build_design_matrix(samples, lines, order)
    dx_coeffs, _, _, _ = np.linalg.lstsq(A, dx_vals, rcond=None)
    dy_coeffs, _, _, _ = np.linalg.lstsq(A, dy_vals, rcond=None)

    dx_r_squared = _compute_r_squared(dx_vals, A @ dx_coeffs)
    dy_r_squared = _compute_r_squared(dy_vals, A @ dy_coeffs)

    return DisparityModel(
        dx_coeffs=dx_coeffs,
        dy_coeffs=dy_coeffs,
        order=order,
        dx_r_squared=dx_r_squared,
        dy_r_squared=dy_r_squared,
    )
