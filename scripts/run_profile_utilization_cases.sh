#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON:-python3}"
INPUT_DIR="${ROOT_DIR}/data/profile_utilization_inputs"
CASE_DIR="${INPUT_DIR}/cases"
CALIBRATION="${INPUT_DIR}/calib_fake_full.json"

run_case() {
  local name="$1"
  local op_summary="$2"
  local des_graph="$3"
  local output_file="$4"

  echo "=== ${name} ==="
  PYTHONPATH="${ROOT_DIR}" "${PYTHON_BIN}" -c \
    'import sys
from scripts.demo_profile_utilization import run_profile_utilization_to_json
run_profile_utilization_to_json(sys.argv[1], sys.argv[2], sys.argv[3], output_path=sys.argv[4])' \
    "${op_summary}" \
    "${des_graph}" \
    "${CALIBRATION}" \
    "${output_file}"
  echo "wrote ${output_file}"
  echo
}

cd "${ROOT_DIR}"

run_case \
  "default_fake" \
  "${INPUT_DIR}/op_summary_fake.csv" \
  "${INPUT_DIR}/des_fake.json" \
  "${INPUT_DIR}/profile_utilization_report.json"

run_case \
  "compute_bound" \
  "${CASE_DIR}/compute_bound/op_summary.csv" \
  "${CASE_DIR}/compute_bound/des.json" \
  "${CASE_DIR}/compute_bound/profile_utilization_report.json"

run_case \
  "inefficient_compute" \
  "${CASE_DIR}/inefficient_compute/op_summary.csv" \
  "${CASE_DIR}/inefficient_compute/des.json" \
  "${CASE_DIR}/inefficient_compute/profile_utilization_report.json"

run_case \
  "inefficient_mte" \
  "${CASE_DIR}/inefficient_mte/op_summary.csv" \
  "${CASE_DIR}/inefficient_mte/des.json" \
  "${CASE_DIR}/inefficient_mte/profile_utilization_report.json"

run_case \
  "insufficient_parallelism" \
  "${CASE_DIR}/insufficient_parallelism/op_summary.csv" \
  "${CASE_DIR}/insufficient_parallelism/des.json" \
  "${CASE_DIR}/insufficient_parallelism/profile_utilization_report.json"

run_case \
  "sync_overhead" \
  "${CASE_DIR}/sync_overhead/op_summary.csv" \
  "${CASE_DIR}/sync_overhead/des.json" \
  "${CASE_DIR}/sync_overhead/profile_utilization_report.json"
