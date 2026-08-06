from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
PYTHON_EXECUTABLE = sys.executable


def _env() -> dict:
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    return env


def _run_json_script(script_name: str, args: list[str]) -> dict:
    script_path = SCRIPTS_DIR / script_name
    cmd = [PYTHON_EXECUTABLE, str(script_path), *args]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=_env())
    if result.returncode != 0:
        return {
            "ok": False,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "data": None,
            "cmd": cmd,
        }
    try:
        data = json.loads(result.stdout)
    except Exception:
        data = result.stdout
    return {
        "ok": True,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "data": data,
        "cmd": cmd,
    }


def _run_text_script(script_name: str, args: list[str]) -> dict:
    script_path = SCRIPTS_DIR / script_name
    cmd = [PYTHON_EXECUTABLE, str(script_path), *args]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=_env())
    return {
        "ok": result.returncode == 0,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "data": result.stdout,
        "cmd": cmd,
    }


def preview_reader(target: str, show_units: int = 5, show_raw_chars: int = 0, export_dir: str = "") -> dict:
    args = [target, "--show-units", str(show_units), "--show-raw-chars", str(show_raw_chars)]
    if export_dir:
        args.extend(["--export-dir", export_dir])
    return _run_text_script("preview_reader.py", args)


def build_kb(target: str, output_dir: str, max_chars: int, overlap_chars: int, min_chunk_chars: int) -> dict:
    return _run_json_script(
        "build_kb.py",
        [
            target,
            "--output-dir", output_dir,
            "--max-chars", str(max_chars),
            "--overlap-chars", str(overlap_chars),
            "--min-chunk-chars", str(min_chunk_chars),
        ],
    )


def query_kb(index_dir: str, query: str, top_k: int = 5) -> dict:
    return _run_json_script("query_kb.py", [index_dir, query, "--top-k", str(top_k)])


def build_field_evidence(index_dir: str, output_dir: str, top_k_per_query: int = 8, final_top_k: int = 5) -> dict:
    return _run_json_script(
        "build_field_evidence_packs.py",
        [index_dir, "--output-dir", output_dir, "--top-k-per-query", str(top_k_per_query), "--final-top-k", str(final_top_k)],
    )


def process_fact_fields(index_dir: str, output_dir: str, top_k_per_query: int = 8, final_top_k: int = 5) -> dict:
    return _run_json_script(
        "process_fact_fields.py",
        [index_dir, "--output-dir", output_dir, "--top-k-per-query", str(top_k_per_query), "--final-top-k", str(final_top_k)],
    )


def process_analysis_fields(index_dir: str, output_dir: str, top_k_per_query: int = 8, final_top_k: int = 5) -> dict:
    return _run_json_script(
        "process_analysis_fields.py",
        [index_dir, "--output-dir", output_dir, "--top-k-per-query", str(top_k_per_query), "--final-top-k", str(final_top_k)],
    )


def generate_report(index_dir: str, output_dir: str, top_k_per_query: int = 8, final_top_k: int = 5) -> dict:
    return _run_json_script(
        "generate_structured_results.py",
        [index_dir, "--output-dir", output_dir, "--top-k-per-query", str(top_k_per_query), "--final-top-k", str(final_top_k)],
    )
