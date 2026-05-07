"""Tests for gpu_sift.py — fallback and parameter mapping.

Author: Geng Xun
Created: 2026-05-07
Last Modified: 2026-05-07
Updated: 2026-05-07  Geng Xun added GPU SIFT match stats and dynamic batch policy coverage.
"""

import importlib.util
from pathlib import Path

import numpy as np
import pytest

# Import gpu_sift.py directly to avoid triggering controlnet_construct/__init__.py
# (which requires isis_pybind native module).
_GPU_SIFT_PATH = Path(__file__).resolve().parents[2] / "examples" / "controlnet_construct" / "gpu_sift.py"
_spec = importlib.util.spec_from_file_location("gpu_sift", _GPU_SIFT_PATH)
_gpu_sift_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_gpu_sift_module)

HAS_GPU_SIFT = _gpu_sift_module.HAS_GPU_SIFT
GpuSiftBatch = _gpu_sift_module.GpuSiftBatch


class TestHasGpuSift:
    def test_has_gpu_sift_is_bool(self):
        assert isinstance(HAS_GPU_SIFT, bool)


class TestGpuSiftBatchFallback:
    """When HAS_GPU_SIFT is False, execute() should fallback to CPU SIFT."""

    @pytest.mark.skipif(HAS_GPU_SIFT, reason="requires no GPU SIFT")
    def test_execute_returns_empty_when_unavailable(self):
        batch = GpuSiftBatch(batch_size=4)
        img = np.zeros((64, 64), dtype=np.uint8)
        mask = np.ones((64, 64), dtype=np.uint8) * 255
        batch.add(img, mask)
        results = batch.execute()
        # Should fallback to CPU SIFT when GPU unavailable
        assert len(results) == 1
        assert isinstance(results[0], tuple)

    def test_execute_cpu_produces_results(self):
        """CPU fallback should produce (keypoints, descriptors) tuples."""
        batch = GpuSiftBatch(batch_size=4)
        img = np.random.randint(0, 255, (128, 128), dtype=np.uint8)
        mask = np.ones((128, 128), dtype=np.uint8) * 255
        batch.add(img, mask)
        batch.add(img, mask)
        results = batch.execute()
        assert len(results) == 2
        for kp, desc in results:
            assert isinstance(kp, (list, tuple))
            if desc is not None:
                assert desc.shape[1] == 128


class TestGpuSiftBatchParams:
    """Verify SIFT parameters are passed through correctly."""

    def test_custom_params(self):
        batch = GpuSiftBatch(
            batch_size=4,
            nfeatures=200,
            contrastThreshold=0.05,
            edgeThreshold=12.0,
            sigma=1.8,
        )
        assert batch._batch_size == 4
        assert batch._sift_kwargs["nfeatures"] == 200
        assert batch._sift_kwargs["contrastThreshold"] == 0.05

    def test_default_params(self):
        batch = GpuSiftBatch()
        assert batch._batch_size == 32
        assert batch._sift_kwargs["nfeatures"] == 0
        assert batch._sift_kwargs["nOctaveLayers"] == 3
        assert batch._sift_kwargs["contrastThreshold"] == 0.04
        assert batch._sift_kwargs["edgeThreshold"] == 10.0
        assert batch._sift_kwargs["sigma"] == 1.6


class TestGpuSiftBatchHelpers:
    """Test is_full and count helpers."""

    def test_count_and_is_full(self):
        batch = GpuSiftBatch(batch_size=2)
        img = np.zeros((64, 64), dtype=np.uint8)
        mask = np.ones((64, 64), dtype=np.uint8) * 255
        assert batch.count() == 0
        assert not batch.is_full()
        batch.add(img, mask)
        assert batch.count() == 1
        assert not batch.is_full()
        batch.add(img, mask)
        assert batch.count() == 2
        assert batch.is_full()

    def test_execute_clears_buffer(self):
        batch = GpuSiftBatch(batch_size=4)
        img = np.random.randint(0, 255, (64, 64), dtype=np.uint8)
        mask = np.ones((64, 64), dtype=np.uint8) * 255
        batch.add(img, mask)
        batch.execute()
        assert batch.count() == 0
        assert not batch.is_full()

    def test_empty_execute(self):
        batch = GpuSiftBatch(batch_size=4)
        assert batch.execute() == []


class TestGpuSiftMatchResult:
    def test_match_result_tracks_cpu_fallback_flag(self):
        result = _gpu_sift_module.GpuSiftMatchResult(
            left_keypoints=[],
            right_keypoints=[],
            matches=[],
            used_gpu=True,
            used_cpu_fallback=False,
            failure_reason=None,
        )

        assert result.used_gpu is True
        assert result.used_cpu_fallback is False
        assert result.failure_reason is None

    def test_match_stats_counts_fallbacks_and_batches(self):
        stats = _gpu_sift_module.GpuSiftStats()
        stats.record_batch(batch_size=4, used_gpu=True)
        stats.record_pair_result(used_cpu_fallback=False)
        stats.record_pair_result(used_cpu_fallback=True)

        assert stats.gpu_batch_count == 1
        assert stats.gpu_pair_count == 2
        assert stats.cpu_fallback_pair_count == 1
        assert stats.batch_size_histogram == {4: 1}


class TestDynamicBatchController:
    def test_starts_at_initial_batch_and_clamps_to_limits(self):
        controller = _gpu_sift_module.DynamicGpuBatchController(
            initial_batch_size=4,
            min_batch_size=2,
            max_batch_size=16,
        )

        assert controller.current_batch_size == 4

    def test_reduces_batch_after_pressure_signal(self):
        controller = _gpu_sift_module.DynamicGpuBatchController(
            initial_batch_size=8,
            min_batch_size=2,
            max_batch_size=16,
        )

        controller.record_batch(success=True, memory_pressure=True, elapsed_seconds=0.5)

        assert controller.current_batch_size == 4

    def test_increases_batch_after_stable_successes(self):
        controller = _gpu_sift_module.DynamicGpuBatchController(
            initial_batch_size=4,
            min_batch_size=2,
            max_batch_size=16,
            stable_successes_to_grow=2,
        )

        controller.record_batch(success=True, memory_pressure=False, elapsed_seconds=0.5)
        controller.record_batch(success=True, memory_pressure=False, elapsed_seconds=0.5)

        assert controller.current_batch_size == 8
