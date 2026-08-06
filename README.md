# DD Agent｜结构化尽调系统

一个基于本地材料运行的结构化尽调 Web 应用。系统支持上传 PDF、DOCX、TXT 文件，完成文档解析、TF-IDF 知识库构建、结构化字段分析、信息缺口识别、追问清单生成以及 Word / Markdown 报告导出。

## 在线运行逻辑

1. 上传并保存待分析材料。
2. 解析文档并保留页码、段落号或行号定位。
3. 构建当前会话的本地知识库。
4. 生成结构化尽调结论和报告。
5. 下载 Word 或 Markdown 文件。

## 数据与隐私

- 仓库不包含任何预置材料、历史项目、分析结果或生成报告。
- 每个浏览器会话使用独立临时目录。
- 临时文件可能在页面刷新、应用休眠或服务重启后被清除。
- 公共部署仅用于功能展示，请勿上传商业机密、个人敏感信息或受保密协议约束的材料。
- 系统不会联网补充事实，输出仅基于用户本次上传的文件。

## 本地运行

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## 部署到 Streamlit Community Cloud

1. 将本目录上传到 GitHub 仓库。
2. 登录 Streamlit Community Cloud 并连接 GitHub。
3. 创建应用，选择仓库和 `main` 分支。
4. Main file path 填写 `app.py`。
5. 部署后在 Sharing 设置中确认应用为公开访问。

## 项目结构

```text
.
├── app.py
├── requirements.txt
├── .streamlit/config.toml
├── ui/
├── scripts/
└── src/dd_agent/
```

## 重要说明

本项目用于信息整理和初步研究辅助，不构成投资建议、法律意见、审计意见或其他专业结论。用户应对输入材料的合法性、保密义务及最终判断负责。
