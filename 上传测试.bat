@echo off

:: 获取当前脚本所在的目录
set "SCRIPT_DIR=%~dp0"

:: 激活 Miniforge 基础环境
call "%USERPROFILE%\miniforge3\Scripts\activate.bat"

:: 切换到当前脚本所在的目录
cd /d "%SCRIPT_DIR%"

cd batch

:: 激活 conda 环境
call conda activate uploader

:: 执行 acc3.py 脚本
python acc3.py

pause