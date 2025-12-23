@echo off
:: ================= 基础设置 =================
:: 防止中文乱码
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
title VideoLingo 自动化助手

echo.
echo =======================================================
echo           VideoLingo 自动化批处理脚本启动
echo =======================================================
echo.

:: ================= 第一步：文件迁移 =================
echo [1/5] 正在检查是否需要迁移旧文件...

if exist "E:\bilibili_dub\VideoLingo-3.0.0\VideoLingo-3.0.0\batch\output" (
    echo    - 发现旧版输出文件夹，正在迁移到 E:\output ...
    robocopy "E:\bilibili_dub\VideoLingo-3.0.0\VideoLingo-3.0.0\batch\output" "E:\output" /MOVE /E /NFL /NDL /NJH /NJS >nul
    echo    - [成功] 文件迁移完成。
) else (
    echo    - [跳过] 源路径不存在，无需迁移。
)

:: ================= 第二步：切换目录 =================
echo.
echo [2/5] 正在切换工作目录...
cd /d "E:\bilibili_dub\VideoLingo-3.0.0\VideoLingo-3.0.0"
echo    - 当前工作目录已锁定为:
echo    - %cd%

:: ================= 第三步：激活环境 =================
echo.
echo [3/5] 正在激活 Conda 环境 (videolingo2)...
call "%USERPROFILE%\miniforge3\Scripts\activate.bat" videolingo2
if %errorlevel% == 0 (
    echo    - [成功] 环境激活完成。
) else (
    echo    - [警告] 环境激活可能遇到问题，尝试继续运行...
)

:: ================= 第四步：设置路径 =================
echo.
echo [4/5] 配置 Python 运行环境...
:: 这一步是解决 "ModuleNotFoundError" 的关键
set PYTHONPATH=%cd%
echo    - 已将当前目录加入 PYTHONPATH，防止模块报错。

:: ================= 第五步：运行程序 =================
echo.
echo [5/5] 启动 Python 主程序 (Batch Processor)...
echo -------------------------------------------------------
echo.

:: 开始运行脚本
call python batch\utils\batch_processor.py

cd batch

:: 激活 conda 环境
call conda activate uploader

:: 执行 acc3.py 脚本
python acc3.py

:: 上传文件到 biliup
.\biliup.exe upload -c free_content.yaml
.\biliup.exe upload -c paid_content.yaml

echo.
echo -------------------------------------------------------
echo [完成] 所有任务执行完毕，您可以安全关闭此窗口。
pause