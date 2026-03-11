#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打包脚本 - 将工资工具编译为exe
"""

import PyInstaller.__main__
import os
import sys

# 获取当前目录
current_dir = os.path.dirname(os.path.abspath(__file__))

# PyInstaller 参数
args = [
    'salary_tool.py',  # 主程序
    '--name=工资报表生成工具',  # 生成的exe名称
    '--windowed',  # 使用窗口模式（不显示控制台）
    '--onefile',  # 打包为单个文件
    '--icon=icon.ico',  # 图标文件
    '--add-data=icon.ico;.',  # 包含图标文件
    '--clean',  # 清理临时文件
    '--noconfirm',  # 不确认覆盖
    # 隐藏导入的模块
    '--hidden-import=pandas',
    '--hidden-import=openpyxl',
    '--hidden-import=tkinter',
    # 优化
    '--strip',
    '--noupx',
]

# 运行 PyInstaller
PyInstaller.__main__.run(args)

print("\n打包完成！")
print(f"生成的exe文件位于: {os.path.join(current_dir, 'dist', '工资报表生成工具.exe')}")
