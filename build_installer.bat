@echo off
chcp 65001 >nul
title 工资报表生成工具 - 打包安装程序
echo.
echo ============================================
echo    工资报表生成工具 v2.1 - 打包脚本
echo ============================================
echo.

:: 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

:: 检查并安装依赖
echo [1/5] 检查并安装依赖...
pip install -q pyinstaller pandas openpyxl ttkbootstrap
if errorlevel 1 (
    echo [错误] 依赖安装失败
    pause
    exit /b 1
)
echo [OK] 依赖检查完成
echo.

:: 清理旧的构建文件
echo [2/5] 清理旧的构建文件...
if exist "dist" rd /s /q "dist"
if exist "build" rd /s /q "build"
if exist "installer" rd /s /q "installer"
echo [OK] 清理完成
echo.

:: 使用 PyInstaller 打包 EXE
echo [3/5] 使用 PyInstaller 打包程序...
pyinstaller --noconfirm --onefile --windowed ^
    --name "工资报表生成工具" ^
    --icon "icon.ico" ^
    --add-data "icon.ico;." ^
    --clean ^
    salary_tool_feishu.py

if errorlevel 1 (
    echo [错误] PyInstaller 打包失败
    pause
    exit /b 1
)
echo [OK] EXE 打包完成
echo.

:: 创建安装程序目录
echo [4/5] 准备安装程序文件...
mkdir "installer" 2>nul
echo [OK] 准备完成
echo.

:: 检查 Inno Setup
echo [5/5] 检查 Inno Setup...
set INNO_PATH="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

if not exist %INNO_PATH% (
    set INNO_PATH="C:\Program Files\Inno Setup 6\ISCC.exe"
)

if not exist %INNO_PATH% (
    echo [警告] 未检测到 Inno Setup 6
    echo.
    echo 请按以下步骤操作：
    echo 1. 下载 Inno Setup 6：https://jrsoftware.org/isdl.php
    echo 2. 安装 Inno Setup 6
    echo 3. 重新运行此脚本
    echo.
    echo 或者手动打包：
    echo 1. 打开 Inno Setup Compiler
    echo 2. 打开 setup.iss 文件
    echo 3. 点击 Build ^> Compile
    echo.
    pause
    exit /b 1
)

echo [OK] 检测到 Inno Setup 6
echo.
echo 正在编译安装程序...
%INNO_PATH% setup.iss

if errorlevel 1 (
    echo [错误] 安装程序编译失败
    pause
    exit /b 1
)

echo.
echo ============================================
echo    打包完成！
echo ============================================
echo.
echo 输出文件：
echo   - EXE 程序：dist\工资报表生成工具.exe
echo   - 安装包：installer\工资报表生成工具_v2.1_安装包.exe
echo.
echo 安装包功能：
echo   - 自动创建桌面快捷方式
echo   - 自动创建开始菜单快捷方式
echo   - 支持卸载功能
echo   - 自动创建导出报表目录
echo.
pause
