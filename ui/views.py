from __future__ import annotations

import shutil
from pathlib import Path

import streamlit as st

from ui.helpers import export_markdown_to_word, read_json, reset_directory, save_uploaded_files
from ui.runner import build_kb, generate_report, preview_reader
from ui.state import (
    clear_generated_outputs,
    ensure_state,
    get_material_files,
    get_workspace_paths,
    reset_session_workspace,
    touch_build_status,
    touch_report_status,
)
from ui.styles import module_conclusion_card, panel_box

MAX_FILE_COUNT = 10
MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024
MAX_TOTAL_SIZE_BYTES = 60 * 1024 * 1024


def _validate_uploads(uploaded_files) -> list[str]:
    errors: list[str] = []
    if len(uploaded_files) > MAX_FILE_COUNT:
        errors.append(f"单次最多上传 {MAX_FILE_COUNT} 个文件。")
    total_size = sum(int(getattr(file, "size", 0) or 0) for file in uploaded_files)
    if total_size > MAX_TOTAL_SIZE_BYTES:
        errors.append("本次上传文件总大小不能超过 60 MB。")
    oversized = [file.name for file in uploaded_files if int(getattr(file, "size", 0) or 0) > MAX_FILE_SIZE_BYTES]
    if oversized:
        errors.append("以下文件超过单文件 25 MB 限制：" + "、".join(oversized))
    return errors


def _material_table(files: list[Path]) -> list[dict]:
    return [
        {
            "文件名": file.name,
            "格式": file.suffix.lower().lstrip(".").upper(),
            "大小（KB）": round(file.stat().st_size / 1024, 1),
        }
        for file in files
    ]


def render_input_view() -> None:
    ensure_state()
    paths = get_workspace_paths()

    st.info(
        "系统不预置任何材料或分析结果。请仅上传你有权处理的文件；公共演示环境不适合商业机密、个人敏感信息或受保密协议约束的材料。"
    )

    uploaded_files = st.file_uploader(
        "上传待分析材料",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True,
        help="支持 PDF、DOCX、TXT；最多 10 个文件，单文件不超过 25 MB，总计不超过 60 MB。",
    )

    save_col, parse_col, kb_col, clear_col = st.columns([1, 1, 1, 0.8])

    if save_col.button("保存本次材料", type="primary", use_container_width=True):
        if not uploaded_files:
            st.warning("请先选择文件。")
        else:
            errors = _validate_uploads(uploaded_files)
            if errors:
                for error in errors:
                    st.error(error)
            else:
                reset_directory(paths.materials)
                clear_generated_outputs()
                saved = save_uploaded_files(uploaded_files, paths.materials)
                st.success(f"已保存 {len(saved)} 个文件。")
                st.rerun()

    if parse_col.button("解析预览", use_container_width=True):
        files = get_material_files()
        if not files:
            st.warning("请先保存上传材料。")
        else:
            reset_directory(paths.parsed)
            with st.spinner("正在解析材料……"):
                result = preview_reader(
                    str(paths.materials),
                    show_units=5,
                    show_raw_chars=300,
                    export_dir=str(paths.parsed),
                )
            if result["ok"]:
                st.session_state["preview_output"] = result["stdout"]
                st.success("解析完成。")
            else:
                st.error("解析失败。")
                st.code(result["stderr"] or result["stdout"])

    if kb_col.button("构建知识库", use_container_width=True):
        files = get_material_files()
        if not files:
            st.warning("请先保存上传材料。")
        else:
            reset_directory(paths.kb)
            with st.spinner("正在构建本地知识库……"):
                result = build_kb(str(paths.materials), str(paths.kb), 600, 120, 80)
            if result["ok"]:
                st.session_state["last_build_summary"] = result["data"]
                touch_build_status()
                st.success("知识库构建完成。")
                st.rerun()
            else:
                st.error("知识库构建失败。")
                st.code(result["stderr"] or result["stdout"])

    if clear_col.button("清除数据", use_container_width=True):
        reset_session_workspace()
        st.rerun()

    files = get_material_files()
    st.markdown(
        panel_box(
            f"""
            <div class='summary-title'>本次会话材料</div>
            <div class='summary-sub'>已保存文件数：{len(files)}</div>
            <div class='summary-sub'>刷新、休眠或服务重启后，临时文件可能被清除。</div>
            """,
            variant="deep",
        ),
        unsafe_allow_html=True,
    )

    if files:
        st.dataframe(_material_table(files), use_container_width=True, hide_index=True)
    else:
        st.info("尚未保存材料。")

    preview_text = st.session_state.get("preview_output")
    if preview_text:
        with st.expander("查看解析结果", expanded=False):
            st.code(preview_text)


def _extract_question_items(modules: list[dict]) -> list[dict]:
    for module in modules:
        if module.get("module_name") == "追问清单":
            items = []
            for field in module.get("field_results", []):
                value = field.get("value")
                if isinstance(value, list):
                    questions = [str(item) for item in value if str(item).strip()]
                elif value is None:
                    questions = []
                else:
                    questions = [str(value)]
                items.append(
                    {
                        "title": field.get("field_name", "未命名问题"),
                        "questions": questions,
                    }
                )
            return items
    return []


def render_output_view() -> None:
    ensure_state()
    paths = get_workspace_paths()
    report_json = paths.report / "structured_results.json"
    report_md = paths.report / "structured_results.md"
    report_docx = paths.report / "structured_results.docx"

    if st.button("生成结构化结论与 Word 报告", type="primary", use_container_width=True):
        if not (paths.kb / "kb_metadata.json").exists() and not (paths.kb / "chunks.jsonl").exists():
            st.warning("请先在“输入”页面构建知识库。")
        else:
            reset_directory(paths.report)
            with st.spinner("正在生成结构化结果……"):
                result = generate_report(str(paths.kb), str(paths.report), top_k_per_query=8, final_top_k=5)
            if result["ok"]:
                if report_md.exists():
                    export_markdown_to_word(report_md, report_docx, title="结构化尽调结果")
                st.session_state["last_report_summary"] = result.get("data")
                touch_report_status()
                st.success("报告已生成。")
                st.rerun()
            else:
                st.error("报告生成失败。")
                st.code(result["stderr"] or result["stdout"])

    payload = read_json(report_json) if report_json.exists() else None
    modules = payload.get("modules", []) if payload else []
    question_items = _extract_question_items(modules)

    left, right = st.columns([1.45, 0.55])
    with left:
        st.markdown(panel_box("<div class='summary-title'>结构化结论</div>", variant="plain"), unsafe_allow_html=True)
        if modules:
            for module in modules:
                st.markdown(
                    module_conclusion_card(
                        module.get("module_name", "未知模块"),
                        module.get("preliminary_judgment", ""),
                        module.get("core_conclusion", ""),
                    ),
                    unsafe_allow_html=True,
                )
        else:
            st.info("尚未生成结论。")

        if question_items:
            st.markdown(panel_box("<div class='summary-title'>追问清单</div>", variant="plain"), unsafe_allow_html=True)
            for item in question_items:
                title = item["title"]
                questions = item["questions"]
                question_html = "".join(
                    f"<li>{question.replace('<', '&lt;').replace('>', '&gt;')}</li>" for question in questions
                ) or "<li>暂无问题</li>"
                st.markdown(
                    panel_box(
                        f"<div class='summary-sub'><strong>{title}</strong></div><ul class='question-list'>{question_html}</ul>",
                        variant="deep",
                    ),
                    unsafe_allow_html=True,
                )

    with right:
        st.markdown(panel_box("<div class='summary-title'>报告下载</div>", variant="plain"), unsafe_allow_html=True)
        if report_docx.exists():
            st.download_button(
                "下载 Word 报告",
                data=report_docx.read_bytes(),
                file_name="structured_due_diligence_report.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )
        else:
            st.info("Word 报告尚未生成。")

        if report_md.exists():
            st.download_button(
                "下载 Markdown 报告",
                data=report_md.read_bytes(),
                file_name="structured_due_diligence_report.md",
                mime="text/markdown",
                use_container_width=True,
            )
