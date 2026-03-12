#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建安装程序的 Python 脚本
替代批处理文件，避免编码问题
"""

import os
import subprocess
import sys

def check_python():
    """检查 Python 是否安装"""
    print("[1/5] 检查 Python...")
    try:
        result = subprocess.run(['python', '--version'], capture_output=True, text=True)
        print(f"[OK] {result.stdout.strip()}")
        return True
    except:
        print("[错误] 未检测到 Python，请先安装 Python 3.8+")
        return False

def install_dependencies():
    """安装依赖"""
    print("\n[2/5] 检查并安装依赖...")
    deps = ['pyinstaller', 'pandas', 'openpyxl', 'ttkbootstrap', 'pillow']
    for dep in deps:
        print(f"  安装 {dep}...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', dep])
    print("[OK] 依赖安装完成")

def clean_old_build():
    """清理旧的构建文件"""
    print("\n[3/5] 清理旧的构建文件...")
    dirs = ['dist', 'build', 'installer']
    for d in dirs:
        if os.path.exists(d):
            import shutil
            shutil.rmtree(d)
            print(f"  删除 {d}/")
    print("[OK] 清理完成")

def build_exe():
    """使用 PyInstaller 打包 EXE"""
    print("\n[4/5] 使用 PyInstaller 打包程序...")
    
    cmd = [
        'pyinstaller',
        '--noconfirm',
        '--onefile',
        '--windowed',
        '--name', '工资报表生成工具',
        '--icon', 'icon.ico',
        '--add-data', 'icon.ico;.',
        '--add-data', 'net_bank_code.csv;.',
        '--clean',
        'salary_tool_feishu.py'
    ]
    
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("[错误] PyInstaller 打包失败")
        return False
    
    print("[OK] EXE 打包完成")
    return True

def build_installer():
    """使用 Inno Setup 创建安装程序"""
    print("\n[5/5] 检查 Inno Setup...")
    
    # 查找 Inno Setup
    inno_paths = [
        r'C:\Program Files (x86)\Inno Setup 6\ISCC.exe',
        r'C:\Program Files\Inno Setup 6\ISCC.exe',
    ]
    
    inno_path = None
    for path in inno_paths:
        if os.path.exists(path):
            inno_path = path
            break
    
    if not inno_path:
        print("[警告] 未检测到 Inno Setup 6")
        print("\n请按以下步骤操作：")
        print("1. 下载 Inno Setup 6：https://jrsoftware.org/isdl.php")
        print("2. 安装 Inno Setup 6")
        print("3. 重新运行此脚本")
        print("\n或者手动打包：")
        print("1. 打开 Inno Setup Compiler")
        print("2. 打开 setup.iss 文件")
        print("3. 点击 Build > Compile")
        return False
    
    print(f"[OK] 检测到 Inno Setup 6")
    
    # 检查本地中文语言文件
    if os.path.exists('ChineseSimplified.isl'):
        print("[OK] 检测到本地中文语言文件")
        # 复制到 Inno Setup 目录
        inno_dir = os.path.dirname(inno_path)
        chn_lang = os.path.join(inno_dir, 'Languages', 'ChineseSimplified.isl')
        try:
            import shutil
            os.makedirs(os.path.dirname(chn_lang), exist_ok=True)
            shutil.copy('ChineseSimplified.isl', chn_lang)
            print("[OK] 中文语言文件已复制到 Inno Setup")
        except Exception as e:
            print(f"[警告] 复制中文语言文件失败: {e}")
    
    print("\n正在编译安装程序...")
    
    # 创建 installer 目录
    os.makedirs('installer', exist_ok=True)
    
    result = subprocess.run([inno_path, 'setup.iss'])
    if result.returncode != 0:
        print("[错误] 安装程序编译失败")
        return False
    
    print("[OK] 安装程序编译完成")
    return True

def main():
    """主函数"""
    print("=" * 50)
    print("   工资报表生成工具 v2.2 - 打包脚本")
    print("=" * 50)
    print()
    
    # 检查步骤
    if not check_python():
        input("\n按回车键退出...")
        return
    
    install_dependencies()
    clean_old_build()
    
    if not build_exe():
        input("\n按回车键退出...")
        return
    
    build_installer()
    
    # 完成提示
    print("\n" + "=" * 50)
    print("   打包完成！")
    print("=" * 50)
    print()
    print("输出文件：")
    if os.path.exists(r'dist\工资报表生成工具.exe'):
        print("  - EXE 程序：dist\\工资报表生成工具.exe")
    if os.path.exists(r'installer\工资报表生成工具_v2.2_安装包.exe'):
        print("  - 安装包：installer\\工资报表生成工具_v2.2_安装包.exe")
    print()
    print("安装包功能：")
    print("  - 自动创建桌面快捷方式")
    print("  - 自动创建开始菜单快捷方式")
    print("  - 支持卸载功能")
    print("  - 自动创建导出报表目录")
    print()
    input("按回车键退出...")

if __name__ == '__main__':
    main()
