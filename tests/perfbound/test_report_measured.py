# Tests for report.py three-level rendering (A.6.1)
#
# Validates KernelReport text rendering with Reachability Hierarchy,
# bound violation labels, component match, and to_dict reachability block.
#
# Source spec: .omc/plans/a6_validation_harness.md §7

import pytest

from perfbound.combine.report import KernelReport
from perfbound.combine.bound_combiner import BoundResult, BindingTier, Attribution
from perfbound.combine.two_limit import TwoLimitResult
from perfbound.extract.op_classifier import Component


def _make_bound_result(
    kernel_name: str = "test_kernel",
    t_bound_us: float = 1000.0,
    binding_component: Component = Component.CUBE,
) -> BoundResult:
    return BoundResult(
        kernel_name=kernel_name,
        t_bound_us=t_bound_us,
        t_grid_floor_us=800.0,
        t_core_floor_us=900.0,
        t_serial_irreducible_us=100.0,
        binding_tier=BindingTier.COMPONENT,
        binding_component=binding_component,
        attribution=Attribution(),
    )


def test_author_headroom_flows_through():
    """t_measured_us=5000.0 → KernelReport.author_headroom_us correct."""
    br = _make_bound_result(t_bound_us=1000.0)
    two_limit = TwoLimitResult(
        kernel_name="test_kernel",
        t_bound_hivm_us=800.0,
        t_bound_dsl_us=1000.0,
        t_measured_us=5000.0,
    )
    report = KernelReport.from_bound(br, two_limit=two_limit)
    # author_headroom = t_measured - t_bound_dsl = 5000 - 1000 = 4000
    assert report.author_headroom_us == 4000.0


def test_to_text_three_levels():
    """Reachability Hierarchy section present in text output."""
    br = _make_bound_result()
    two_limit = TwoLimitResult(
        kernel_name="test_kernel",
        t_bound_hivm_us=800.0,
        t_bound_dsl_us=1000.0,
    )
    report = KernelReport.from_bound(br, two_limit=two_limit)
    text = report.to_text()
    assert "Reachability Hierarchy" in text


def test_to_text_not_measured():
    """not yet measured when t_measured_us=None."""
    br = _make_bound_result()
    two_limit = TwoLimitResult(
        kernel_name="test_kernel",
        t_bound_hivm_us=800.0,
        t_bound_dsl_us=1000.0,
    )
    report = KernelReport.from_bound(br, two_limit=two_limit)
    text = report.to_text()
    assert "not yet measured" in text


def test_to_text_bound_violation():
    """BOUND VIOLATION when T_bound > T_measured."""
    br = _make_bound_result(t_bound_us=1500.0)
    two_limit = TwoLimitResult(
        kernel_name="test_kernel",
        t_bound_hivm_us=1200.0,
        t_bound_dsl_us=1500.0,
        t_measured_us=1100.0,  # T_bound > T_measured
    )
    report = KernelReport.from_bound(br, two_limit=two_limit)
    text = report.to_text()
    assert "BOUND VIOLATION" in text


def test_to_text_shows_source_and_n_invocations():
    """Source path + n=N invocations shown when measured."""
    br = _make_bound_result()
    two_limit = TwoLimitResult(
        kernel_name="test_kernel",
        t_bound_hivm_us=800.0,
        t_bound_dsl_us=1000.0,
        t_measured_us=1200.0,
    )
    report = KernelReport.from_bound(br, two_limit=two_limit)
    report.msprof_source = "/tmp/op_summary.csv"
    report.n_invocations = 12
    text = report.to_text()
    assert "source: /tmp/op_summary.csv" in text
    assert "n=12 invocations" in text


def test_to_text_shows_component_match():
    """match=✓ / match=✗ rendered when component_match is set."""
    br = _make_bound_result(binding_component=Component.CUBE)
    two_limit = TwoLimitResult(
        kernel_name="test_kernel",
        t_bound_hivm_us=800.0,
        t_bound_dsl_us=1000.0,
        t_measured_us=1200.0,
    )
    report = KernelReport.from_bound(br, two_limit=two_limit)
    report.component_match = True
    text = report.to_text()
    assert "match=✓" in text

    report.component_match = False
    text = report.to_text()
    assert "match=✗" in text


def test_to_dict_reachability_key():
    """to_dict()[reachability][t_bound_dsl_us] present."""
    br = _make_bound_result()
    two_limit = TwoLimitResult(
        kernel_name="test_kernel",
        t_bound_hivm_us=800.0,
        t_bound_dsl_us=1000.0,
    )
    report = KernelReport.from_bound(br, two_limit=two_limit)
    d = report.to_dict()
    assert "reachability" in d
    assert d["reachability"]["t_bound_dsl_us"] == 1000.0


def test_to_dict_is_violation_flag():
    """is_violation=True when T_bound > T_measured."""
    br = _make_bound_result(t_bound_us=1500.0)
    two_limit = TwoLimitResult(
        kernel_name="test_kernel",
        t_bound_hivm_us=1200.0,
        t_bound_dsl_us=1500.0,
        t_measured_us=1100.0,
    )
    report = KernelReport.from_bound(br, two_limit=two_limit)
    d = report.to_dict()
    assert d["reachability"]["is_violation"] is True


def test_to_dict_msprof_source_and_n_invocations():
    """reachability[msprof_source] and reachability[n_invocations] present."""
    br = _make_bound_result()
    two_limit = TwoLimitResult(
        kernel_name="test_kernel",
        t_bound_hivm_us=800.0,
        t_bound_dsl_us=1000.0,
        t_measured_us=1200.0,
    )
    report = KernelReport.from_bound(br, two_limit=two_limit)
    report.msprof_source = "/tmp/op_summary.csv"
    report.n_invocations = 12
    d = report.to_dict()
    assert d["reachability"]["msprof_source"] == "/tmp/op_summary.csv"
    assert d["reachability"]["n_invocations"] == 12


# ── merge_validation bridge tests ──────────────────────────────────────


def test_merge_validation_sets_provenance_fields():
    """merge_validation copies t_measured, msprof_source, n_invocations, component_match."""
    br = _make_bound_result()
    two_limit = TwoLimitResult(
        kernel_name="test_kernel",
        t_bound_hivm_us=800.0,
        t_bound_dsl_us=1000.0,
    )
    report = KernelReport.from_bound(br, two_limit=two_limit)
    assert report.msprof_source is None
    assert report.n_invocations is None
    assert report.component_match is None

    report.merge_validation(
        t_measured_us=1500.0,
        msprof_source="/tmp/op_summary.csv",
        n_invocations=5,
        component_match=True,
    )

    assert report.t_measured_us == 1500.0
    assert report.msprof_source == "/tmp/op_summary.csv"
    assert report.n_invocations == 5
    assert report.component_match is True
    # author_headroom = t_measured - t_bound_dsl = 1500 - 1000 = 500
    assert report.author_headroom_us == 500.0


def test_merge_validation_from_csv_end_to_end():
    """_merge_validation_from_csv populates provenance from fixture CSV."""
    from pathlib import Path
    from perfbound.combine.run_report import _merge_validation_from_csv

    fixture = Path(__file__).parent / "fixtures" / "op_summary_sample.csv"

    br = _make_bound_result(kernel_name="target_kernel", t_bound_us=500.0)
    two_limit = TwoLimitResult(
        kernel_name="target_kernel",
        t_bound_hivm_us=400.0,
        t_bound_dsl_us=500.0,
    )
    report = KernelReport.from_bound(br, two_limit=two_limit)
    assert report.t_measured_us is None

    _merge_validation_from_csv(report, fixture, "target_kernel", n_warmup=0)

    # target_kernel has durations 1000, 1050, 5000 → median=1050 (no warmup)
    assert report.t_measured_us == 1050.0
    assert report.msprof_source == str(fixture)
    assert report.n_invocations == 3
    # AI_CORE dominates (7050 vs AI_CPU 800) → matches CUBE prediction
    assert report.component_match is True
    # author_headroom = 1050 - 500 = 550
    assert report.author_headroom_us == 550.0
