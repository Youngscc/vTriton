#!/usr/bin/env python3
"""Run profile_utilization end-to-end on the bundled inputs."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import textwrap

sys.path.insert(0, str(Path(__file__).parents[1]))

from perfbound.analyze.hivm_bottleneck_diagnosis import hivm_bottleneck_report_to_dict
from perfbound.analyze.profile_utilization import OperatorBottleneckReport, run_from_files
from perfbound.calibration.calib_loader import DEFAULT_CALIB_PATH


ROOT = Path(__file__).parents[1]
REPORT_WIDTH = 88
INPUT_DIR = ROOT / "data" / "profile_utilization_inputs"
CALIBRATION = DEFAULT_CALIB_PATH
CASE_DIR = INPUT_DIR / "cases"
ACTIVE_CASE = "real_data_2"
IGNORE_SCALAR = True
SHOW_WARNINGS = False
KERNEL_DISPLAY_NAMES = {
    "chunk_kda_bwd_kernel_wy_dqkg_fused_opt_v2": (
        "Chunk KDA backward fused kernel (dq/dk/dg/db/dA)"
    ),
}
DEMO_CASES: dict[str, tuple[Path, Path, Path]] = {
    "default_fake": (
        INPUT_DIR / "op_summary_fake.csv",
        INPUT_DIR / "des_fake.json",
        INPUT_DIR / "profile_utilization_report.json",
    ),
    "compute_bound": (
        CASE_DIR / "compute_bound" / "op_summary.csv",
        CASE_DIR / "compute_bound" / "des.json",
        CASE_DIR / "compute_bound" / "profile_utilization_report.json",
    ),
    "inefficient_compute": (
        CASE_DIR / "inefficient_compute" / "op_summary.csv",
        CASE_DIR / "inefficient_compute" / "des.json",
        CASE_DIR / "inefficient_compute" / "profile_utilization_report.json",
    ),
    "inefficient_mte": (
        CASE_DIR / "inefficient_mte" / "op_summary.csv",
        CASE_DIR / "inefficient_mte" / "des.json",
        CASE_DIR / "inefficient_mte" / "profile_utilization_report.json",
    ),
    "insufficient_parallelism": (
        CASE_DIR / "insufficient_parallelism" / "op_summary.csv",
        CASE_DIR / "insufficient_parallelism" / "des.json",
        CASE_DIR / "insufficient_parallelism" / "profile_utilization_report.json",
    ),
    "sync_overhead": (
        CASE_DIR / "sync_overhead" / "op_summary.csv",
        CASE_DIR / "sync_overhead" / "des.json",
        CASE_DIR / "sync_overhead" / "profile_utilization_report.json",
    ),
    "real_data": (
        CASE_DIR / "real_data" / "op_summary_20260610082013.csv",
        CASE_DIR / "real_data" / "des_graph.json",
        CASE_DIR / "real_data" / "profile_utilization_report.json",
    ),
    "real_data_2": (
        CASE_DIR / "real_data_2" / "op_summary_20260610082013.csv",
        CASE_DIR / "real_data_2" / "chunk_des.json",
        CASE_DIR / "real_data_2" / "profile_utilization_report.json",
    ),
}


def main() -> None:
    op_summary, des_graph, output_file = _active_case_paths()
    payload = run_profile_utilization_to_json(
        op_summary,
        des_graph,
        CALIBRATION,
        output_path=output_file,
        ignore_scalar=IGNORE_SCALAR,
    )
    _print_report_summary(ACTIVE_CASE, payload, op_summary, des_graph, output_file)


def _active_case_paths() -> tuple[Path, Path, Path]:
    try:
        return DEMO_CASES[ACTIVE_CASE]
    except KeyError as exc:
        choices = ", ".join(sorted(DEMO_CASES))
        raise SystemExit(
            f"Unknown ACTIVE_CASE={ACTIVE_CASE!r}. Available cases: {choices}"
        ) from exc


def run_profile_utilization_to_json(
    op_summary_path: str | Path,
    desgraph_path: str | Path,
    calibration_path: str | Path | None = None,
    *,
    output_path: str | Path | None = None,
    **kwargs,
) -> dict:
    """Run analysis and convert the result object to a JSON-ready report."""

    report = run_from_files(
        op_summary_path,
        desgraph_path,
        calibration_path,
        **kwargs,
    )
    payload = report_to_dict(report)
    if output_path is not None:
        Path(output_path).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        )
    return payload


def report_to_dict(report: OperatorBottleneckReport) -> dict:
    """把分析结果对象转成可 JSON 序列化的 dict。"""

    return {
        "kernel_name": report.kernel_name,
        "elapsed_time_us": report.elapsed_time_us,
        "diagnosis": report.diagnosis,
        "bound_kind": report.bound_kind,
        "dominant_component": (
            report.dominant_component.value if report.dominant_component else None
        ),
        "dominant_item": report.dominant_item,
        "dominant_share": report.dominant_share,
        "ignore_scalar": report.ignore_scalar,
        "exposed_control_frac_model": report.exposed_control_frac_model,
        "exposed_control_frac_measured": report.exposed_control_frac_measured,
        "exposed_control_deficit_pts": report.exposed_control_deficit_pts,
        "exposed_control_deficit_us": report.exposed_control_deficit_us,
        "n_sync_ops": report.n_sync_ops,
        "hivm_bottleneck": hivm_bottleneck_report_to_dict(report.hivm_bottleneck),
        "components": {
            key: {
                "component": result.component.value,
                "work_done": result.work_done,
                "bound_work": result.bound_work,
                "elapsed_time_us": result.elapsed_time_us,
                "active_time_us": result.active_time_us,
                "actual_performance": result.actual_performance,
                "ideal_performance": result.ideal_performance,
                "u_utilization": result.u_utilization,
                "r_residency": result.r_residency,
                "e_efficiency": result.e_efficiency,
                "dominant_item": result.dominant_item,
                "dominant_share": result.dominant_share,
                "warnings": result.warnings,
            }
            for key, result in report.component_results.items()
        },
        "warnings": report.warnings,
    }


def _print_report_summary(
    name: str,
    report: dict,
    op_summary: Path,
    des_graph: Path,
    output_file: Path,
) -> None:
    hivm = report.get("hivm_bottleneck") or {}
    pipeline = hivm.get("pipeline_diagnosis") or {}
    components = report.get("components") or {}
    dominant = _dominant_component(report)

    _print_case_card(name, report, hivm, pipeline, output_file)
    print()

    _print_section("1", "Primary diagnosis")
    print(f"Operator result : {report.get('diagnosis', '-')}")
    print(f"First check     : {_first_place_to_look(report, hivm, pipeline)}")
    print(f"Dominant        : {_dominant_label(report)}")
    print(f"Evidence        : {_primary_evidence(report, dominant)}")
    print()

    _print_section("2", "Component profile evidence")
    if components:
        _print_component_table(components, report.get("dominant_component"))
    else:
        print("No component metrics were produced.")
    print()

    _print_section("3", "HIVM structure evidence")
    _print_hivm_summary(hivm, pipeline)
    _print_pipe_table(hivm.get("weighted_pipe_cycles") or {})
    print()

    op_diagnoses = hivm.get("op_diagnoses") or []
    _print_section("4", "Top op-level causes")
    if op_diagnoses:
        for index, diag in enumerate(op_diagnoses[:3], start=1):
            print(_format_op_diagnosis(index, diag))
    else:
        print("No op-level diagnoses were produced.")
    print()

    suggestions = _collect_suggestions(report, hivm, pipeline)
    if suggestions:
        _print_section("5", "下一步建议")
        for item in suggestions:
            _print_wrapped_bullet("->", item)
        print()

    warnings = report.get("warnings") or []
    if SHOW_WARNINGS and warnings:
        _print_section("!", "Warnings")
        for warning in warnings:
            _print_wrapped_bullet("!", warning)
        print()

    _print_section("i", "Inputs")
    mode = (
        "Compute/MTE only (Scalar ignored)"
        if report.get("ignore_scalar")
        else "All components"
    )
    print(f"mode      : {mode}")
    print(f"op_summary: {_rel(op_summary)}")
    print(f"des_graph : {_rel(des_graph)}")
    print()


def _rule(char: str, width: int = REPORT_WIDTH) -> str:
    return char * width


def _box_top(width: int = REPORT_WIDTH) -> str:
    return "+" + "-" * (width - 2) + "+"


def _box_bottom(width: int = REPORT_WIDTH) -> str:
    return _box_top(width)


def _fit(text: str, width: int) -> str:
    if len(text) <= width:
        return text
    if width <= 3:
        return text[:width]
    return text[: width - 3] + "..."


def _box_line(text: str, width: int = REPORT_WIDTH) -> str:
    inner = width - 4
    return f"| {_fit(text, inner):<{inner}} |"


def _wrapped(text: str, width: int, subsequent_indent: str = "") -> list[str]:
    return textwrap.wrap(
        str(text),
        width=width,
        subsequent_indent=subsequent_indent,
        break_long_words=False,
        break_on_hyphens=False,
    ) or [""]


def _print_wrapped_bullet(prefix: str, text: str) -> None:
    first_prefix = f"{prefix} "
    next_prefix = " " * len(first_prefix)
    lines = _wrapped(text, REPORT_WIDTH - len(first_prefix), next_prefix)
    print(first_prefix + lines[0])
    for line in lines[1:]:
        print(line)


def _print_section(number: str, title: str) -> None:
    print(f"[{number}] {title}")
    print(_rule("-"))


def _print_case_card(
    name: str,
    report: dict,
    hivm: dict,
    pipeline: dict,
    output_file: Path,
) -> None:
    diagnosis = report.get("diagnosis", "-")
    first_check = _first_place_to_look(report, hivm, pipeline)
    kernel = report.get("kernel_name", "-")
    op_name = _display_kernel_name(kernel)
    elapsed = _fmt_us(report.get("elapsed_time_us"))

    print(_box_top())
    print(_box_line(f"CASE   {name}"))
    print(_box_line(f"RESULT {diagnosis}"))
    print(_box_line(f"CHECK  {first_check}"))
    print(_box_line(f"OP     {op_name}"))
    print(_box_line(f"KERNEL {kernel}"))
    print(_box_line(f"TIME   {elapsed}    OUTPUT {_rel(output_file)}"))
    print(_box_bottom())


def _display_kernel_name(kernel: str) -> str:
    return KERNEL_DISPLAY_NAMES.get(kernel, kernel)


def _print_hivm_summary(hivm: dict, pipeline: dict) -> None:
    print(
        f"{'global':<11}{_fmt_value(hivm.get('global_root_cause')):<20}"
        f"{'pipeline':<11}{_fmt_value(pipeline.get('root_cause')):<20}"
        f"{'pipe':<6}{_fmt_value(pipeline.get('bottleneck_pipe'))}"
    )
    print(
        f"{'imbalance':<11}{_fmt_ratio(pipeline.get('imbalance_ratio')):<20}"
        f"{'sync':<11}{_fmt_pct_value(hivm.get('sync_overhead_ratio')):<20}"
        f"{'barrier':<8}{_fmt_pct_value(hivm.get('barrier_overhead_ratio'))}"
    )
    print(
        f"{'cycles':<11}"
        f"one_iter={_fmt_cycles(hivm.get('one_iteration_cycles')):<14} "
        f"weighted={_fmt_cycles(hivm.get('weighted_cycles'))}"
    )


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _fmt_value(value) -> str:
    return "-" if value in (None, "") else str(value)


def _fmt_num(value, digits: int = 3) -> str:
    if value in (None, ""):
        return "-"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if abs(number) >= 1000:
        return f"{number:.0f}"
    return f"{number:.{digits}f}".rstrip("0").rstrip(".")


def _fmt_us(value) -> str:
    formatted = _fmt_num(value)
    return "-" if formatted == "-" else f"{formatted} us"


def _fmt_cycles(value) -> str:
    formatted = _fmt_num(value)
    return "-" if formatted == "-" else f"{formatted} cyc"


def _fmt_pct_fraction(value) -> str:
    if value in (None, ""):
        return "-"
    return f"{float(value) * 100.0:.1f}%"


def _fmt_pct_value(value) -> str:
    if value in (None, ""):
        return "-"
    return f"{float(value):.1f}%"


def _fmt_ratio(value) -> str:
    if value in (None, ""):
        return "-"
    return f"{float(value):.1f}x"


def _bar(value, width: int = 12) -> str:
    if value in (None, ""):
        return "[" + "?" * width + "]"
    fraction = max(0.0, min(float(value), 1.0))
    filled = int(round(fraction * width))
    return "[" + "#" * filled + "-" * (width - filled) + "]"


def _dominant_component(report: dict) -> dict | None:
    component = report.get("dominant_component")
    if not component:
        return None
    return (report.get("components") or {}).get(component)


def _dominant_label(report: dict) -> str:
    component = report.get("dominant_component")
    item = report.get("dominant_item")
    share = report.get("dominant_share")
    if not component:
        return "none selected"
    label = component
    if item:
        label += f" / {item}"
    if share not in (None, ""):
        label += f" ({_fmt_pct_fraction(share)} of component work)"
    return label


def _primary_evidence(report: dict, dominant: dict | None) -> str:
    diagnosis = report.get("diagnosis", "-")
    if dominant is not None:
        return (
            f"U={_fmt_pct_fraction(dominant.get('u_utilization'))}, "
            f"R={_fmt_pct_fraction(dominant.get('r_residency'))}, "
            f"E={_fmt_pct_fraction(dominant.get('e_efficiency'))}; "
            f"active={_fmt_us(dominant.get('active_time_us'))}"
        )
    components = list((report.get("components") or {}).values())
    if components:
        max_r = max(components, key=lambda item: item.get("r_residency") or 0.0)
        max_u = max(components, key=lambda item: item.get("u_utilization") or 0.0)
        return (
            f"no dominant component; max R={max_r.get('component')} "
            f"{_fmt_pct_fraction(max_r.get('r_residency'))}, "
            f"max U={max_u.get('component')} "
            f"{_fmt_pct_fraction(max_u.get('u_utilization'))}"
        )
    return f"{diagnosis}; no component evidence available"


def _first_place_to_look(report: dict, hivm: dict, pipeline: dict) -> str:
    diagnosis = report.get("diagnosis")
    dominant = report.get("dominant_component")
    item = report.get("dominant_item")
    global_root = hivm.get("global_root_cause")
    bottleneck_pipe = pipeline.get("bottleneck_pipe")

    if diagnosis in ("Compute Bound", "Inefficient Compute") and dominant:
        return f"{dominant} compute path" + (f" ({item})" if item else "")
    if diagnosis in ("MTE Bound", "Inefficient MTE") and dominant:
        return f"{dominant} transfer path" + (f" ({item})" if item else "")
    if global_root == "SyncOverhead":
        return "sync/barrier timeline"
    if global_root == "PipelineImbalance" and bottleneck_pipe:
        return f"pipeline balance around {bottleneck_pipe}"
    if bottleneck_pipe:
        return f"HIVM bottleneck pipe {bottleneck_pipe}"
    if dominant:
        return dominant
    return "parallelism / overlap"


def _print_component_table(components: dict, dominant_component: str | None) -> None:
    rows = sorted(
        components.values(),
        key=lambda item: (
            item.get("component") == dominant_component,
            item.get("u_utilization") or 0.0,
            item.get("r_residency") or 0.0,
            item.get("active_time_us") or 0.0,
        ),
        reverse=True,
    )
    for item in rows:
        marker = "*" if item.get("component") == dominant_component else " "
        component = f"{marker} {item.get('component', '-')}"
        dominant_item = item.get("dominant_item") or "-"
        print(
            f"{component:<13}"
            f"U {_fmt_pct_fraction(item.get('u_utilization')):>7} "
            f"{_bar(item.get('u_utilization'))}  "
            f"R {_fmt_pct_fraction(item.get('r_residency')):>7} "
            f"{_bar(item.get('r_residency'))}  "
            f"E {_fmt_pct_fraction(item.get('e_efficiency')):>7} "
            f"{_bar(item.get('e_efficiency'))}"
        )
        print(
            f"{'':<13}"
            f"active={_fmt_us(item.get('active_time_us')):<12} "
            f"work={_fmt_num(item.get('work_done')):<12} "
            f"item={dominant_item}"
        )
    if dominant_component:
        print()
        print("* dominant component selected by operator-level diagnosis")


def _print_pipe_table(weighted_pipe_cycles: dict) -> None:
    if not weighted_pipe_cycles:
        print("Weighted pipes : none")
        return

    total = sum(float(value) for value in weighted_pipe_cycles.values())
    rows = sorted(
        weighted_pipe_cycles.items(),
        key=lambda item: float(item[1]),
        reverse=True,
    )
    print("Weighted pipes :")
    for pipe, cycles in rows[:5]:
        share = float(cycles) / total if total > 0 else 0.0
        print(
            f"  {pipe:<14} {_fmt_cycles(cycles):>12} "
            f"{_bar(share)} {_fmt_pct_fraction(share):>7}"
        )


def _format_op_diagnosis(index: int, diag: dict) -> str:
    line = diag.get("line_number")
    location = f"line {line}" if line not in (None, "") else "line -"
    header = (
        f"{index}. {diag.get('root_cause', '-'):<16} "
        f"{diag.get('op_name', '-')} [{diag.get('pipe', '-')}] ({location})"
    )
    metrics = (
        f"   duration={_fmt_cycles(diag.get('actual_cycles')):<10} "
        f"min={_fmt_cycles(diag.get('theoretical_min_cycles')):<10} "
        f"overhead={_fmt_pct_fraction(diag.get('overhead_ratio'))}"
    )
    evidence = diag.get("evidence")
    if evidence:
        wrapped = _wrapped(
            evidence,
            REPORT_WIDTH - len("   evidence: "),
            " " * len("   evidence: "),
        )
        evidence_text = "   evidence: " + wrapped[0]
        if len(wrapped) > 1:
            evidence_text += "\n" + "\n".join(wrapped[1:])
        return f"{header}\n{metrics}\n{evidence_text}"
    return f"{header}\n{metrics}"


def _collect_suggestions(report: dict, hivm: dict, pipeline: dict) -> list[str]:
    suggestions: list[str] = []
    diagnosis = report.get("diagnosis")
    if diagnosis == "Compute Bound":
        suggestions.append("计算侧已接近理论上限，优先减少计算量、调整精度或优化 tile 形状。")
    elif diagnosis == "MTE Bound":
        suggestions.append("搬运侧已接近理论上限，优先减少 bytes 或增加片上复用。")
    elif diagnosis == "Inefficient Compute":
        suggestions.append("计算单元驻留高但效率低，检查 vector/cube 形状、mask/repeat 和小 tile。")
    elif diagnosis == "Inefficient MTE":
        suggestions.append("MTE 驻留高但效率低，检查传输路径、对齐、burst size 和 packet size。")
    elif diagnosis == "Insufficient Parallelism":
        suggestions.append("有效计算/搬运单元驻留不足，优先检查 overlap、pipeline depth 和暴露等待。")

    for source in (hivm, pipeline):
        for item in source.get("global_suggestions", []) or source.get("suggestions", []) or []:
            item = _translate_suggestion(item)
            if item not in suggestions:
                suggestions.append(item)
    return suggestions[:4]


def _translate_suggestion(text: str) -> str:
    replacements = {
        "提高 arithmetic intensity": "提高算术强度",
        "融合相邻 compute ops 以减少启动和同步开销": "融合相邻计算 op，减少启动和同步开销",
        "提高 compute-to-data ratio": "提高计算/数据搬运比例",
        "减少 data movement 或增加 tile reuse": "减少数据搬运，或增加 tile 复用",
        "用 software pipeline 将 transfer 与 compute 重叠": "用软件流水让搬运和计算重叠",
        "增加 software pipeline depth 填充 idle pipe slots": "增加软件流水深度，填充空闲 pipe 槽",
        "减少数据搬运或提高 tile reuse": "减少数据搬运，或提高 tile 复用",
        "增加 multi-buffer pipeline depth 以隐藏同步等待": "增加 multi-buffer pipeline 深度，隐藏同步等待",
    }
    return replacements.get(text, text)


if __name__ == "__main__":
    main()
