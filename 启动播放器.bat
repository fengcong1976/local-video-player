@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo            本地视频播放器 启动中...
echo ============================================
echo.

set "PY=%~dp0venv\Scripts\pythonw.exe"
if not exist "%PY%" (
    echo 未找到虚拟环境 venv。
    echo 请先在本目录执行：
    echo     python -m venv venv
    echo     venv\Scripts\pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

rem 支持把视频文件/文件夹直接拖到本 bat 上打开
if "%~1"=="" (
    start "" "%PY%" "%~dp0main.py"
) else (
    start "" "%PY%" "%~dp0main.py" %*
)
exit /b 0
