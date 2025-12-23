@echo off
:: 解决中文乱码
chcp 65001 >nul
set PYTHONIOENCODING=utf-8

title VideoLingo 自动化批处理

:: 1. 移动文件
if exist "E:\Bilinew\VideoLingo-main\batch\output" (
    robocopy "E:\Bilinew\VideoLingo-main\batch\output" "E:\output" /MOVE /E /NFL /NDL /NJH /NJS >nul
    echo [1/3] 文件迁移完成。
)

:: 2. 切换目录并激活环境
cd /d "E:\bilibili_dub\VideoLingo-3.0.0\VideoLingo-3.0.0"

echo [2/3] 激活环境...
call "%USERPROFILE%\miniforge3\Scripts\activate.bat" videolingo2

:: 3. 运行脚本
echo [3/3] 开始运行...
echo ------------------------------------------

:: --- 关键修复在这里 ---
set PYTHONPATH=%cd%
call python batch\utils\batch_processor.py

echo ------------------------------------------
pause