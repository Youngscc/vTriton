#!/usr/bin/env python3
"""打印几组假 profiling 输入和瓶颈分析输出。"""

from __future__ import annotations

from pprint import pprint
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[1]))

from perfbound.extract.op_classifier import Component
from perfbound.model.component_model import ComponentBound
from perfbound.analyze.profile_utilization import (
    KernelProfileStats,
    ProfileComponentStats,
    WorkBreakdownItem,
    analyze_operator_bottleneck,
)


def main() -> None:
    profiles = [
        # _compute_bound_profile(),
        _insufficient_parallelism_profile(),
        # _inefficient_compute_profile(),
        # _inefficient_mte_profile(),
    ]

    for profile in profiles:
        component_bound = _component_bound_for_profile(profile)
        _print_case(profile, component_bound)


def _print_case(profile: KernelProfileStats, component_bound: ComponentBound) -> None:
    report = analyze_operator_bottleneck(
        profile,
        component_bound,
        u_threshold=0.80,
        r_threshold=0.50,
    )

    print(f"=== Profiling 输入: {profile.kernel_name} ===")
    pprint(profile)
    print()

    print("=== 算子级诊断输出 ===")
    print("diagnosis:", report.diagnosis)
    print("bound_kind:", report.bound_kind)
    print("dominant_component:", report.dominant_component)
    print("dominant_item:", report.dominant_item)
    print("dominant_share:", f"{report.dominant_share:.3f}")
    print("warnings:", report.warnings)
    print()

    print("=== Component 级 A/I/U/R/E ===")
    for name, result in report.component_results.items():
        print(f"[{name}]")
        print("  work_done:", result.work_done)
        print("  active_time_us:", result.active_time_us)
        print("  A actual_performance:", f"{result.actual_performance:.6f}")
        print("  I ideal_performance:", f"{result.ideal_performance:.6f}")
        print("  U utilization:", f"{result.u_utilization:.6f}")
        print("  R active_time_ratio:", f"{result.r_residency:.6f}")
        print("  E execution_efficiency:", f"{result.e_efficiency:.6f}")
        print("  dominant_item:", result.dominant_item)
        print("  dominant_share:", f"{result.dominant_share:.6f}")
        print("  warnings:", result.warnings)
    print()


def _compute_bound_profile() -> KernelProfileStats:
    """Cube 的 U 接近 ceiling，展示 Compute Bound。"""
    cube_items = [
        WorkBreakdownItem("fp16", 1640.5, 202.25),
        WorkBreakdownItem("bf16", 915.25, 176.5),
        WorkBreakdownItem("int8", 608.75, 392.125),
    ]
    mte_items = [
        WorkBreakdownItem("gm->ub", 3880.5, 980.0),
        WorkBreakdownItem("gm->l1", 1412.25, 760.75),
    ]
    cube_work = _work(cube_items)
    mte_work = _work(mte_items)
    cube_ideal = _ideal_rate(cube_items)
    mte_ideal = _ideal_rate(mte_items)
    elapsed = cube_work / (0.83 * cube_ideal)
    return KernelProfileStats(
        kernel_name="case_1_compute_bound",
        elapsed_time_us=elapsed,
        components=[
            ProfileComponentStats(
                Component.CUBE,
                cube_work,
                cube_work / (0.92 * cube_ideal),
                cube_items,
            ),
            ProfileComponentStats(
                Component.MTE_GM,
                mte_work,
                mte_work / (0.80 * mte_ideal),
                mte_items,
            ),
        ],
    )


def _insufficient_parallelism_profile() -> KernelProfileStats:
    """所有 component 的 R 都低，展示并行不足。"""
    cube_items = [
        WorkBreakdownItem("fp16", 922.5, 201.5),
        WorkBreakdownItem("bf16", 431.25, 171.25),
        WorkBreakdownItem("int8", 277.75, 384.5),
    ]
    mte_items = [
        WorkBreakdownItem("gm->ub", 2850.5, 226.25),
        WorkBreakdownItem("gm->l1", 1164.25, 166.5),
        WorkBreakdownItem("ub->gm", 708.75, 117.25),
    ]
    cube_work = _work(cube_items)
    mte_work = _work(mte_items)
    elapsed = max(
        cube_work / (0.18 * _ideal_rate(cube_items)),
        mte_work / (0.22 * _ideal_rate(mte_items)),
    )
    return KernelProfileStats(
        kernel_name="case_2_insufficient_parallelism",
        elapsed_time_us=elapsed,
        components=[
            ProfileComponentStats(Component.CUBE, cube_work, elapsed * 0.30, cube_items),
            ProfileComponentStats(Component.MTE_GM, mte_work, elapsed * 0.40, mte_items),
        ],
    )


def _inefficient_compute_profile() -> KernelProfileStats:
    """Vector 的 R 高但 E 低，展示 Inefficient Compute。"""
    vector_items = [
        WorkBreakdownItem("fp32", 731.5, 82.75),
        WorkBreakdownItem("fp16", 618.25, 166.5),
        WorkBreakdownItem("int8", 294.75, 332.25),
    ]
    mte_items = [
        WorkBreakdownItem("gm->ub", 1101.5, 221.25),
        WorkBreakdownItem("ub->gm", 553.75, 116.0),
    ]
    vector_work = _work(vector_items)
    mte_work = _work(mte_items)
    elapsed = vector_work / (0.24 * _ideal_rate(vector_items))
    return KernelProfileStats(
        kernel_name="case_3_inefficient_compute",
        elapsed_time_us=elapsed,
        components=[
            ProfileComponentStats(Component.VECTOR, vector_work, elapsed * 0.78, vector_items),
            ProfileComponentStats(
                Component.MTE_GM,
                mte_work,
                mte_work / (0.64 * _ideal_rate(mte_items)),
                mte_items,
            ),
        ],
    )


def _inefficient_mte_profile() -> KernelProfileStats:
    """MTE 的 R 高但 E 低，展示 Inefficient MTE。"""
    cube_items = [
        WorkBreakdownItem("fp16", 402.5, 188.5),
        WorkBreakdownItem("bf16", 318.25, 154.75),
        WorkBreakdownItem("int8", 144.75, 367.25),
    ]
    mte_items = [
        WorkBreakdownItem("ub->gm", 2524.5, 118.75),
        WorkBreakdownItem("gm->ub", 1046.25, 214.5),
        WorkBreakdownItem("l1->ub", 682.75, 136.25),
    ]
    cube_work = _work(cube_items)
    mte_work = _work(mte_items)
    elapsed = mte_work / (0.25 * _ideal_rate(mte_items))
    return KernelProfileStats(
        kernel_name="case_4_inefficient_mte",
        elapsed_time_us=elapsed,
        components=[
            ProfileComponentStats(
                Component.CUBE,
                cube_work,
                cube_work / (0.58 * _ideal_rate(cube_items)),
                cube_items,
            ),
            ProfileComponentStats(Component.MTE_UB, mte_work, elapsed * 0.80, mte_items),
        ],
    )


def _component_bound_for_profile(profile: KernelProfileStats) -> ComponentBound:
    total_ops: dict[str, float] = {}
    total_bytes: dict[str, float] = {}
    per_component_us: dict[str, float] = {}

    for stats in profile.components:
        comp_key = stats.component.value
        if stats.component in (Component.CUBE, Component.VECTOR, Component.SCALAR):
            total_ops[comp_key] = stats.work_done
        else:
            total_bytes[comp_key] = stats.work_done
        per_component_us[comp_key] = stats.work_done / _ideal_rate(stats.work_breakdown)

    binding_key, t_core_floor = max(per_component_us.items(), key=lambda item: item[1])
    return ComponentBound(
        t_core_floor_us=t_core_floor,
        binding_component=Component(binding_key),
        total_ops=total_ops,
        total_bytes=total_bytes,
        per_component_us=per_component_us,
    )


def _ideal_rate(items: list[WorkBreakdownItem]) -> float:
    return _work(items) / sum(item.work / item.peak_rate for item in items)


def _work(items: list[WorkBreakdownItem]) -> float:
    return sum(item.work for item in items)


if __name__ == "__main__":
    main()
