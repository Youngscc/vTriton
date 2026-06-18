"""Shared calibration-rate helpers for analysis modules."""

from __future__ import annotations

from ..calibration.constants import CalibrationDB, DType


def cube_peak_rate_ops_per_us(label: str, db: CalibrationDB) -> float:
    """Return cube throughput for ``label`` in ops/us."""

    try:
        dtype = DType.from_str(label)
    except KeyError:
        return 0.0
    tflops = db.cube.throughput.get(dtype, 0.0)
    return tflops * 1e6 if tflops > 0 else 0.0


def vector_peak_rate_ops_per_us(
    label: str,
    db: CalibrationDB,
    *,
    unknown_as_fp16: bool = False,
) -> float:
    """Return vector throughput for ``label`` in ops/us."""

    try:
        dtype = DType.from_str(label)
    except KeyError:
        if not unknown_as_fp16:
            return 0.0
        dtype = DType.FP16
    if dtype in (DType.FP16, DType.BF16):
        tflops = db.vector.throughput_fp16_tflops
    else:
        tflops = db.vector.throughput_fp32_tflops
    return tflops * 1e6 if tflops > 0 else 0.0
