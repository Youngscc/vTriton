#!/usr/bin/env python3
"""Run profile_utilization end-to-end on the bundled fake inputs."""

from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[1]))

from perfbound.analyze.profile_utilization import report_to_dict, run_from_files


ROOT = Path(__file__).parents[1]
INPUT_DIR = ROOT / "data" / "profile_utilization_inputs"
OP_SUMMARY = INPUT_DIR / "op_summary_fake.csv"
DES_GRAPH = INPUT_DIR / "des_fake.json"
CALIBRATION = INPUT_DIR / "calib_fake_full.json"
OUTPUT_FILE = INPUT_DIR / "profile_utilization_report.json"
CASE_DIR = INPUT_DIR / "cases"
DEMO_CASES = [
    ("default_fake", OP_SUMMARY, DES_GRAPH, OUTPUT_FILE),
    (
        "compute_bound",
        CASE_DIR / "compute_bound" / "op_summary.csv",
        CASE_DIR / "compute_bound" / "des.json",
        CASE_DIR / "compute_bound" / "profile_utilization_report.json",
    ),
    (
        "inefficient_compute",
        CASE_DIR / "inefficient_compute" / "op_summary.csv",
        CASE_DIR / "inefficient_compute" / "des.json",
        CASE_DIR / "inefficient_compute" / "profile_utilization_report.json",
    ),
    (
        "inefficient_mte",
        CASE_DIR / "inefficient_mte" / "op_summary.csv",
        CASE_DIR / "inefficient_mte" / "des.json",
        CASE_DIR / "inefficient_mte" / "profile_utilization_report.json",
    ),
    (
        "insufficient_parallelism",
        CASE_DIR / "insufficient_parallelism" / "op_summary.csv",
        CASE_DIR / "insufficient_parallelism" / "des.json",
        CASE_DIR / "insufficient_parallelism" / "profile_utilization_report.json",
    ),
    (
        "sync_overhead",
        CASE_DIR / "sync_overhead" / "op_summary.csv",
        CASE_DIR / "sync_overhead" / "des.json",
        CASE_DIR / "sync_overhead" / "profile_utilization_report.json",
    ),
]


def main() -> None:
    print("=== profile_utilization end-to-end demo ===")
    print("calibration:", CALIBRATION)
    print()

    for name, op_summary, des_graph, output_file in DEMO_CASES:
        report = run_from_files(
            op_summary,
            des_graph,
            CALIBRATION,
        )
        payload = report_to_dict(report)
        output_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        _print_report_summary(name, payload, op_summary, des_graph, output_file)


def _print_report_summary(
    name: str,
    report: dict,
    op_summary: Path,
    des_graph: Path,
    output_file: Path,
) -> None:
    hivm = report.get("hivm_bottleneck") or {}
    pipeline = hivm.get("pipeline_diagnosis") or {}

    print(f"=== Case: {name} ===")
    print("op_summary:", op_summary)
    print("des_graph:", des_graph)
    print("output_file:", output_file)
    print("kernel_name:", report["kernel_name"])
    print("diagnosis:", report["diagnosis"])
    print("bound_kind:", report["bound_kind"])
    print("dominant_component:", report["dominant_component"])
    print("dominant_item:", report["dominant_item"])
    print("global_root_cause:", hivm.get("global_root_cause"))
    print("pipeline_root_cause:", pipeline.get("root_cause"))
    print("pipeline_bottleneck:", pipeline.get("bottleneck_pipe"))
    print("sync_overhead_ratio:", hivm.get("sync_overhead_ratio"))
    print("barrier_overhead_ratio:", hivm.get("barrier_overhead_ratio"))
    warnings = report["warnings"] or []
    if warnings:
        print("warnings:", warnings)
    print()


if __name__ == "__main__":
    main()
