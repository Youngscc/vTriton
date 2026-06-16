"""C++ reference cases for HIVM Bottleneck Diagnosis.

The fixture data is intentionally shaped like programming-contest test data:
each case has a fake DES-like input and the expected C++ branch result derived
from HIVMBottleneckDiagnosis.cpp.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).parents[2]))

from perfbound.analyze.hivm_bottleneck_diagnosis import (  # noqa: E402
    diagnose_hivm_bottleneck_from_des_ops,
)
from perfbound.calibration.calib_loader import load_calibration  # noqa: E402
from perfbound.extract.op_classifier import Precision  # noqa: E402


_ROOT = Path(__file__).parents[2]
_CASES = _ROOT / "tests" / "perfbound" / "fixtures" / "hivm_bottleneck" / "cpp_reference_cases.json"
_CALIBRATION = _ROOT / "data" / "profile_utilization_inputs" / "calib_fake_full.json"


def _load_cases() -> list[dict]:
    with open(_CASES) as f:
        return json.load(f)["cases"]


def _precision_from_elem_type(elem_type: str):
    try:
        return Precision(elem_type)
    except ValueError:
        return None


def _op_from_fixture(raw: dict) -> SimpleNamespace:
    return SimpleNamespace(
        op_id=raw["id"],
        op_name=raw["name"],
        pipe=raw["pipe"],
        bytes_transferred=raw["bytes"],
        elements=raw["elements"],
        flops=raw["flops"],
        duration_cycles=raw["duration"],
        loop_multiplier=raw["loop_multiplier"],
        start_cycle=raw["start_cycle"],
        end_cycle=raw["end_cycle"],
        src_space=raw["src_space"],
        dst_space=raw["dst_space"],
        precision=_precision_from_elem_type(raw["elem_type"]),
    )


@pytest.mark.parametrize("case", _load_cases(), ids=lambda case: case["name"])
def test_hivm_bottleneck_matches_cpp_reference_cases(case: dict):
    """Compare Python diagnosis against branch-level C++ expected outputs."""

    operations = [_op_from_fixture(raw) for raw in case["operations"]]
    des_metadata = {int(raw["id"]): raw for raw in case["operations"]}
    report = diagnose_hivm_bottleneck_from_des_ops(
        operations,
        load_calibration(_CALIBRATION),
        des_metadata=des_metadata,
        top_k=100,
    )

    expected = case["expected"]
    assert report.warnings == []
    assert report.global_root_cause == expected["global_root_cause"]
    assert report.pipeline_diagnosis is not None
    assert report.pipeline_diagnosis.root_cause == expected["pipeline_root_cause"]
    assert report.pipeline_diagnosis.bottleneck_pipe == expected["pipeline_bottleneck"]

    if "pipeline_imbalance_ratio" in expected:
        assert report.pipeline_diagnosis.imbalance_ratio == pytest.approx(
            expected["pipeline_imbalance_ratio"]
        )
    if "sync_overhead_ratio" in expected:
        assert report.sync_overhead_ratio == pytest.approx(expected["sync_overhead_ratio"])
    if "barrier_overhead_ratio" in expected:
        assert report.barrier_overhead_ratio == pytest.approx(expected["barrier_overhead_ratio"])

    actual_op_roots = {
        str(diag.op_id): diag.root_cause
        for diag in sorted(report.op_diagnoses, key=lambda item: item.op_id)
    }
    assert actual_op_roots == expected["op_root_causes"]
