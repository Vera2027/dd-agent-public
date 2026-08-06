# 公开部署操作

## GitHub 网页上传

1. 在 GitHub 新建一个 Public repository，例如 `dd-agent-public`。
2. 不要勾选自动生成 README、`.gitignore` 或 License，避免与本目录文件冲突。
3. 在仓库页面选择 **Add file → Upload files**。
4. 解压本项目压缩包，将解压后的全部文件拖入上传区域。
5. 提交信息填写 `Initial public release`，然后点击 **Commit changes**。

## Streamlit Community Cloud

1. 使用 GitHub 账号登录 Streamlit Community Cloud。
2. 选择 **Create app**。
3. Repository 选择刚创建的仓库。
4. Branch 选择 `main`。
5. Main file path 填写 `app.py`。
6. 选择公开的 `streamlit.app` 子域名并部署。
7. 打开应用的 Share / Sharing 设置，确认任何拥有链接的人都能访问。

## Git 命令行发布

在解压目录中执行：

```bash
git init
git add .
git commit -m "Initial public release"
git branch -M main
git remote add origin <YOUR_GITHUB_REPOSITORY_URL>
git push -u origin main
```

不要将 GitHub Token、密码或 Streamlit 密钥写入仓库文件。
