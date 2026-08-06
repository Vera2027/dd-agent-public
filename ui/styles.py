from __future__ import annotations

import streamlit as st

UI_FONT = '"STKaiti", "STKaiti SC", "华文楷体", "KaiTi", "楷体", serif'


def inject_global_styles() -> None:
    st.markdown(
        f"""
        <style>
        html, body, [class*="css"] {{ font-family: {UI_FONT}; }}
        #MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"], header[data-testid="stHeader"] {{ display: none !important; }}
        .stApp {{
            background:
                radial-gradient(circle at 15% 12%, rgba(91, 72, 210, 0.18), transparent 24%),
                radial-gradient(circle at 86% 10%, rgba(32, 90, 190, 0.18), transparent 22%),
                linear-gradient(180deg, #07101F 0%, #091731 56%, #081120 100%);
            color: #F4F6FF;
        }}
        .block-container {{ max-width: 1200px; padding-top: 1.2rem; padding-bottom: 2rem; }}
        [data-testid="stSidebar"] {{
            background: linear-gradient(180deg, rgba(8,16,31,0.99) 0%, rgba(7,15,30,0.99) 100%);
            border-right: 1px solid rgba(116, 129, 212, 0.18);
        }}
        .sidebar-title {{ font-size: 24px; font-weight: 800; color: #F7F8FF; margin: .4rem 0 .8rem 0; }}
        div[role="radiogroup"] label {{
            background: rgba(15, 24, 48, 0.96);
            border: 1px solid rgba(129, 143, 222, 0.18);
            border-radius: 14px;
            padding: .55rem .8rem;
            margin-bottom: .5rem;
        }}
        .judge-banner {{
            border-radius: 28px;
            padding: 28px 32px;
            margin-bottom: 18px;
            box-shadow: 0 18px 42px rgba(0,0,0,0.34);
            border: 1px solid rgba(255,255,255,0.08);
            color: #fffdf8;
            overflow: hidden;
            position: relative;
        }}
        .judge-banner::after {{
            content: "";
            position: absolute;
            right: -80px;
            top: -90px;
            width: 250px;
            height: 250px;
            background: radial-gradient(circle, rgba(255,255,255,.18) 0%, rgba(255,255,255,.02) 64%, transparent 74%);
        }}
        .judge-banner.pending {{ background: linear-gradient(135deg, #44267B 0%, #6E46C6 56%, #D0A34C 100%); }}
        .judge-banner.a {{ background: linear-gradient(135deg, #3D2575 0%, #6E42D8 54%, #D7AD4A 100%); }}
        .judge-banner.b {{ background: linear-gradient(135deg, #40276F 0%, #7A4CC0 52%, #C88D2E 100%); }}
        .judge-banner.c {{ background: linear-gradient(135deg, #3A215B 0%, #7E468F 50%, #B76D2F 100%); }}
        .judge-top {{ font-size: 12px; letter-spacing: .16em; text-transform: uppercase; opacity: .92; }}
        .judge-main {{ display: flex; align-items: center; gap: 14px; margin-top: 10px; flex-wrap: wrap; }}
        .judge-code {{ font-size: 34px; font-weight: 800; }}
        .judge-short {{ font-size: 17px; padding: 7px 14px; border-radius: 999px; background: rgba(255,255,255,.14); border: 1px solid rgba(255,255,255,.16); }}
        .judge-conclusion {{ font-size: 24px; font-weight: 800; margin-top: 14px; }}
        .judge-desc {{ font-size: 15px; line-height: 1.85; margin-top: 8px; max-width: 980px; }}
        .section-title {{ font-size: 24px; font-weight: 800; margin: 12px 0 12px 0; color: #F8FAFF; }}
        .panel-box {{
            border-radius: 22px;
            padding: 20px 22px;
            box-shadow: 0 12px 30px rgba(0,0,0,.22);
            border: 1px solid rgba(123, 139, 214, .14);
        }}
        .panel-box.deep {{ background: linear-gradient(180deg, rgba(14,23,46,.98) 0%, rgba(10,18,36,.99) 100%); }}
        .panel-box.plain {{ background: linear-gradient(180deg, rgba(15,25,48,.94) 0%, rgba(10,18,36,.98) 100%); }}
        .summary-title {{ font-size: 15px; color: #B6C4EF; margin-bottom: 8px; }}
        .summary-sub {{ font-size: 16px; color: #EEF2FF; line-height: 1.9; }}
        .path-text, .env-line {{ word-break: break-all; line-height: 1.9; color: #EEF2FF; font-size: 16px; }}
        .badge-row {{ display: flex; gap: 8px; flex-wrap: wrap; }}
        .badge {{ display: inline-flex; align-items: center; padding: 7px 11px; border-radius: 999px; font-size: 12px; font-weight: 700; border: 1px solid transparent; }}
        .badge.ok {{ background: rgba(16,185,129,.18); color: #BDF4E2; border-color: rgba(16,185,129,.28); }}
        .badge.warn {{ background: rgba(245,158,11,.18); color: #F8D38E; border-color: rgba(245,158,11,.28); }}
        .module-card {{
            background: linear-gradient(180deg, rgba(16,25,49,.96) 0%, rgba(10,18,36,.98) 100%);
            border: 1px solid rgba(127, 140, 221, 0.14);
            border-radius: 20px;
            padding: 16px 18px;
            margin-bottom: 12px;
            color: #F2F5FF;
        }}
        .module-title {{ font-size: 20px; font-weight: 800; margin-bottom: 8px; }}
        .module-judgment {{ display:inline-block; padding: 5px 10px; border-radius: 999px; background: rgba(112, 99, 245, 0.16); border: 1px solid rgba(112, 99, 245, 0.18); font-size: 13px; margin-bottom: 10px; }}
        .module-text {{ font-size: 16px; line-height: 1.85; color: #E9EEFF; }}
        .stButton>button, .stDownloadButton>button {{
            width: 100%; border-radius: 14px; border: 1px solid rgba(124,143,255,.24);
            background: linear-gradient(135deg, rgba(88,72,212,.96), rgba(33,107,202,.94));
            color: #fff; font-weight: 700; padding: .68rem 1rem;
        }}
        .stButton>button:hover, .stDownloadButton>button:hover {{
            background: linear-gradient(135deg, rgba(102,86,225,.98), rgba(49,122,221,.96)); color: #fff;
        }}
        div[data-testid="stTextInput"] input, div[data-testid="stTextArea"] textarea {{
            background: rgba(13,21,40,.92); color: #F4F7FF; border-radius: 14px;
        }}
        div[data-testid="stFileUploader"] section {{ background: rgba(13,21,40,.82); border-radius: 16px; }}
        .stAlert {{ background: rgba(18, 44, 78, 0.86); color: #EAF2FF; border: 1px solid rgba(102, 144, 223, 0.25); }}
        .question-list {{ margin: 10px 0 0 18px; padding-left: 4px; color: #E9EEFF; line-height: 1.85; font-size: 16px; }}
        .question-list li {{ margin-bottom: 4px; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def big_classification_banner(code: str, short: str, conclusion: str, desc: str, theme: str = "pending") -> str:
    return f"""
    <div class='judge-banner {theme}'>
        <div class='judge-top'>overall screening classification</div>
        <div class='judge-main'>
            <div class='judge-code'>{code}</div>
            <div class='judge-short'>{short}</div>
        </div>
        <div class='judge-conclusion'>{conclusion}</div>
        <div class='judge-desc'>{desc}</div>
    </div>
    """


def section_title(title: str) -> str:
    return f"<div class='section-title'>{title}</div>"


def panel_box(content: str, variant: str = "plain") -> str:
    return f"<div class='panel-box {variant}'>{content}</div>"


def status_badge(text: str, status: str) -> str:
    return f"<span class='badge {status}'>{text}</span>"


def module_conclusion_card(title: str, judgment: str, conclusion: str) -> str:
    safe_title = title.replace("<", "&lt;").replace(">", "&gt;")
    safe_judgment = (judgment or "").replace("<", "&lt;").replace(">", "&gt;")
    safe_conclusion = (conclusion or "").replace("<", "&lt;").replace(">", "&gt;")
    judgment_html = f"<div class='module-judgment'>{safe_judgment}</div>" if safe_judgment else ""
    return f"""
    <div class='module-card'>
        <div class='module-title'>{safe_title}</div>
        {judgment_html}
        <div class='module-text'>{safe_conclusion}</div>
    </div>
    """
