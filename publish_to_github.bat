@echo off
if "%~1"=="" (
  echo Usage: publish_to_github.bat ^<github-repository-url^>
  exit /b 1
)

git init
git add .
git commit -m "Initial public release"
git branch -M main
git remote remove origin 2>nul
git remote add origin %1
git push -u origin main
