from __future__ import annotations

import json
import shutil
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SESSION_BASE_DIR = Path(tempfile.gettempdir()) / "dd_agent_public_sessions"


@dataclass(frozen=True)
class WorkspacePaths:
    root: Path
    materials: Path
    parsed: Path
    kb: Path
    report: Path
    fact_fields: Path
    analysis_fields: Path
    evidence_packs: Path


CLASSIFICATION_MAP = {
    "建议进入下一轮沟通": {
        "code": "A 类判断",
        "short": "建议推进",
        "theme": "a",
        "desc": "当前材料支持继续进入下一轮沟通。",
    },
    "信息不足，建议补充材料后再判断": {
        "code": "B 类判断",
        "short": "补材再议",
        "theme": "b",
        "desc": "当前证据不够，建议补充材料后再判断。",
    },
    "存在明显风险，谨慎推进": {
        "code": "C 类判断",
        "short": "谨慎推进",
        "theme": "c",
        "desc": "当前材料已出现明显风险信号。",
    },
}

PENDING_CLASSIFICATION = {
    "code": "待生成",
    "short": "待判断",
    "theme": "pending",
    "desc": "上传材料并生成报告后显示判断结果。",
}


def _session_id() -> str:
    if "session_id" not in st.session_state:
        st.session_state["session_id"] = uuid.uuid4().hex
    return str(st.session_state["session_id"])


def get_workspace_paths() -> WorkspacePaths:
    root = SESSION_BASE_DIR / _session_id()
    return WorkspacePaths(
        root=root,
        materials=root / "materials",
        parsed=root / "parsed",
        kb=root / "kb",
        report=root / "report",
        fact_fields=root / "fact_fields",
        analysis_fields=root / "analysis_fields",
        evidence_packs=root / "evidence_packs",
    )


def ensure_workspace() -> WorkspacePaths:
    paths = get_workspace_paths()
    for path in (
        paths.root,
        paths.materials,
        paths.parsed,
        paths.kb,
        paths.report,
        paths.fact_fields,
        paths.analysis_fields,
        paths.evidence_packs,
    ):
        path.mkdir(parents=True, exist_ok=True)
    return paths


def ensure_state() -> None:
    ensure_workspace()
    defaults = {
        "last_build_summary": None,
        "last_report_summary": None,
        "last_error": None,
        "last_build_at": None,
        "last_report_at": None,
        "preview_output": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def reset_session_workspace() -> None:
    current_root = get_workspace_paths().root
    shutil.rmtree(current_root, ignore_errors=True)
    preserved_keys = {"session_id"}
    for key in list(st.session_state.keys()):
        if key not in preserved_keys:
            del st.session_state[key]
    st.session_state["session_id"] = uuid.uuid4().hex
    ensure_state()


def clear_generated_outputs() -> None:
    paths = ensure_workspace()
    for path in (
        paths.parsed,
        paths.kb,
        paths.report,
        paths.fact_fields,
        paths.analysis_fields,
        paths.evidence_packs,
    ):
        shutil.rmtree(path, ignore_errors=True)
        path.mkdir(parents=True, exist_ok=True)
    st.session_state["last_build_summary"] = None
    st.session_state["last_report_summary"] = None
    st.session_state["last_build_at"] = None
    st.session_state["last_report_at"] = None
    st.session_state["preview_output"] = None


def _now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def touch_build_status() -> None:
    st.session_state["last_build_at"] = _now_text()


def touch_report_status() -> None:
    st.session_state["last_report_at"] = _now_text()


def get_material_files() -> list[Path]:
    paths = ensure_workspace()
    files: list[Path] = []
    for ext in ("*.pdf", "*.docx", "*.txt"):
        files.extend(paths.materials.glob(ext))
    return sorted(files, key=lambda item: item.name.lower())


def safe_read_json(path: str | Path):
    file_path = Path(path)
    if not file_path.exists():
        return None
    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def get_classification_meta(payload: dict | None = None) -> dict:
    paths = ensure_workspace()
    if payload is None:
        payload = safe_read_json(paths.report / "structured_results.json")
    if not payload:
        return PENDING_CLASSIFICATION.copy()
    conclusion = payload.get("overall_screening_conclusion")
    meta = CLASSIFICATION_MAP.get(conclusion, PENDING_CLASSIFICATION).copy()
    meta["conclusion"] = conclusion or "待判断"
    meta["reason"] = payload.get("overall_screening_reason", "")
    return meta


def _kb_files_exist(paths: WorkspacePaths) -> bool:
    return any(
        (
            (paths.kb / "chunks.jsonl").exists(),
            (paths.kb / "kb_metadata.json").exists(),
            (paths.kb / "chunks.json").exists(),
            (paths.kb / "metadata.json").exists(),
        )
    )


def get_status_snapshot() -> dict:
    paths = ensure_workspace()
    report_md = paths.report / "structured_results.md"
    report_json = paths.report / "structured_results.json"
    report_docx = paths.report / "structured_results.docx"
    class_meta = get_classification_meta(safe_read_json(report_json))
    return {
        "material_file_count": len(get_material_files()),
        "kb_ready": _kb_files_exist(paths),
        "report_ready": report_md.exists(),
        "report_docx_ready": report_docx.exists(),
        "kb_status_text": st.session_state.get("last_build_at") or ("已完成" if _kb_files_exist(paths) else "未构建"),
        "report_status_text": st.session_state.get("last_report_at") or ("已完成" if report_md.exists() else "未生成"),
        "classification": class_meta,
    }
