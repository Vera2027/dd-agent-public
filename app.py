from __future__ import annotations

import streamlit as st

from ui.state import ensure_state, get_status_snapshot, reset_session_workspace
from ui.styles import big_classification_banner, inject_global_styles, panel_box, section_title, status_badge
from ui.views import render_input_view, render_output_view

st.set_page_config(
    page_title="DD Agent｜结构化尽调系统",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

ensure_state()
inject_global_styles()
status = get_status_snapshot()
classification = status["classification"]

with st.sidebar:
    st.markdown("<div class='sidebar-title'>DD Agent</div>", unsafe_allow_html=True)
    mode = st.radio("功能切换", ["概览", "输入", "输出"], index=0, label_visibility="collapsed")
    st.caption("公开演示版｜不预置材料与结果")
    if st.button("结束并清除本次会话", use_container_width=True):
        reset_session_workspace()
        st.rerun()

if mode == "概览":
    st.markdown(
        big_classification_banner(
            code=classification.get("code", "待生成"),
            short=classification.get("short", "待判断"),
            conclusion=classification.get("conclusion", "尚未生成判断结果"),
            desc=classification.get("reason") or classification.get("desc", ""),
            theme=classification.get("theme", "pending"),
        ),
        unsafe_allow_html=True,
    )

    st.markdown(section_title("产品流程"), unsafe_allow_html=True)
    st.markdown(
        panel_box(
            """
            <div class='summary-title'>上传材料 → 文档解析 → 本地检索 → 结构化分析 → 规则校验 → 报告导出</div>
            <div class='summary-sub'>支持 PDF、DOCX、TXT；结论保留原文定位，并显式展示信息缺口与追问方向。</div>
            """,
            variant="plain",
        ),
        unsafe_allow_html=True,
    )

    metric_1, metric_2, metric_3, metric_4 = st.columns(4)
    metric_1.metric("已保存材料", status["material_file_count"])
    metric_2.metric("知识库", "已完成" if status["kb_ready"] else "未构建")
    metric_3.metric("结构化报告", "已完成" if status["report_ready"] else "未生成")
    metric_4.metric("Word 导出", "可用" if status["report_docx_ready"] else "未生成")

    st.markdown(section_title("运行说明"), unsafe_allow_html=True)
    badge_html = "".join(
        [
            status_badge("会话隔离", "ok"),
            status_badge("临时存储", "ok"),
            status_badge("无预置数据", "ok"),
            status_badge("仅基于上传材料", "ok"),
        ]
    )
    st.markdown(panel_box(f"<div class='badge-row'>{badge_html}</div>", variant="plain"), unsafe_allow_html=True)
    st.warning("公共部署仅用于功能展示。请勿上传商业机密、个人敏感信息或受保密协议约束的文件。")

elif mode == "输入":
    st.markdown(section_title("输入"), unsafe_allow_html=True)
    render_input_view()
else:
    st.markdown(section_title("输出"), unsafe_allow_html=True)
    render_output_view()
