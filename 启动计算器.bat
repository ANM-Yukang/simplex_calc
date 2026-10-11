@echo off
rem ============================================================
rem  启动计算器.bat —— 双击即启动网页版单纯形法计算器
rem  双击后自动定位 Python、启动 web_app.py，浏览器会自动打开。
rem  也可以在命令行带参数运行，例如：启动计算器.bat 8080 --no-browser
rem ============================================================
cd /d "%~dp0"

rem ---- 依次探测 python、py -3、python3（用 where 查找并实际运行验证） ----
set "PYEXE="
where python >nul 2>nul
if not errorlevel 1 python -c "pass" >nul 2>nul
if not errorlevel 1 set "PYEXE=python"
if defined PYEXE goto launch

where py >nul 2>nul
if not errorlevel 1 py -3 -c "pass" >nul 2>nul
if not errorlevel 1 set "PYEXE=py -3"
if defined PYEXE goto launch

where python3 >nul 2>nul
if not errorlevel 1 python3 -c "pass" >nul 2>nul
if not errorlevel 1 set "PYEXE=python3"
if defined PYEXE goto launch

goto nopython

:launch
rem ---- 启动网页版计算器，参数（端口号、--no-browser 等）原样透传 ----
echo 正在启动网页版计算器，请稍候...
%PYEXE% web_app.py %*
set "RC=%errorlevel%"

rem ---- 只有异常退出才停留，方便看清报错；正常退出（含 Ctrl+C）不额外停留 ----
if "%RC%"=="0" exit /b 0
echo.
echo [错误] 程序异常退出，退出码 %RC%，请查看上面的报错信息。
pause
exit /b %RC%

:nopython
echo.
echo [提示] 没有找到可用的 Python 解释器。
echo 请先安装 Python 3.7+ 并勾选加入 PATH
echo 安装完成后重新双击本文件即可启动。
pause
exit /b 1
