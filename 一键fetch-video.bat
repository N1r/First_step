@echo off

:: 获取当前脚本所在的目录
set "SCRIPT_DIR=%~dp0"

:: 移动文件到 E:\old 目录
robocopy "%SCRIPT_DIR%batch\output" "E:\old" /MOVE /E

:: 激活 Miniforge 基础环境
call "%USERPROFILE%\miniforge3\Scripts\activate.bat"

:: 切换到当前脚本所在的目录
cd /d "%SCRIPT_DIR%"

:: 激活 videolingo2 环境
call conda activate uploader

:: 运行 Python 脚本
python fetch_video.py
pause