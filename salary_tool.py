#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工资工具 - GUI版 v2.0
功能:
1. 维护员工花名册
2. 根据花名册生成三种格式的工资报表
3. 支持Excel/CSV导入导出
4. 现代化UI界面
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pandas as pd
import os
from datetime import datetime
import re
import json


# 版本信息
VERSION = "v2.0"
COPYRIGHT = "© 2026 惊鸿科技（济宁）有限公司"

# 配色方案
COLORS = {
    'primary': '#2196F3',
    'success': '#4CAF50',
    'warning': '#FF9800',
    'danger': '#F44336',
    'info': '#00BCD4',
    'bg': '#f5f5f5',
    'card': '#ffffff',
    'text': '#333333',
    'text_secondary': '#666666',
    'border': '#e0e0e0'
}


class ModernStyle:
    """现代化样式类"""
    
    @staticmethod
    def apply_style(root):
        """应用现代化样式"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # 配置全局字体
        root.option_add('*Font', '微软雅黑 10')
        
        # Notebook样式
        style.configure('Custom.TNotebook', background=COLORS['bg'], tabmargins=[2, 5, 2, 0])
        style.configure('Custom.TNotebook.Tab',
                       font=('微软雅黑', 11),
                       padding=[25, 12],
                       background='#e0e0e0')
        style.map('Custom.TNotebook.Tab',
                 background=[('selected', COLORS['primary']), ('!selected', '#e0e0e0')],
                 foreground=[('selected', 'white'), ('!selected', COLORS['text'])],
                 padding=[('selected', [25, 12]), ('!selected', [25, 12])],
                 font=[('selected', ('微软雅黑', 11, 'bold')), ('!selected', ('微软雅黑', 11))])
        
        # Treeview样式
        style.configure('Custom.Treeview',
                       font=('微软雅黑', 10),
                       rowheight=28,
                       background=COLORS['card'],
                       fieldbackground=COLORS['card'])
        style.configure('Custom.Treeview.Heading',
                       font=('微软雅黑', 10, 'bold'),
                       background=COLORS['primary'],
                       foreground='white')
        
        # 按钮样式
        style.configure('Action.TButton',
                       font=('微软雅黑', 10, 'bold'),
                       padding=[20, 8])
        
        # 进度条样式
        style.configure('Custom.Horizontal.TProgressbar',
                       thickness=20,
                       background=COLORS['success'])


class SalaryTool:
    """工资工具主类"""
    
    def __init__(self, root):
        self.root = root
        self.root.title(f"工资报表生成工具 {VERSION}")
        self.root.geometry("1400x900")
        self.root.minsize(1300, 800)
        self.root.configure(bg=COLORS['bg'])
        
        # 数据文件路径
        self.roster_file = "员工花名册.xlsx"
        self.config_file = "salary_tool_config.json"
        self.roster_df = None
        self.history = []
        
        # 加载配置
        self.load_config()
        
        # 加载花名册
        self.load_roster()
        
        # 应用样式
        ModernStyle.apply_style(root)
        
        # 创建界面
        self.create_widgets()
        
        # 绑定快捷键
        self.bind_shortcuts()
    
    def load_config(self):
        """加载配置"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.default_company = config.get('default_company', '惊鸿科技(济宁)有限公司')
                    self.history = config.get('history', [])
            except:
                self.default_company = '惊鸿科技(济宁)有限公司'
        else:
            self.default_company = '惊鸿科技(济宁)有限公司'
    
    def save_config(self):
        """保存配置"""
        try:
            config = {
                'default_company': self.company_var.get(),
                'history': self.history[-10:]  # 保留最近10条记录
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except:
            pass
    
    def load_roster(self):
        """加载员工花名册"""
        if os.path.exists(self.roster_file):
            try:
                self.roster_df = pd.read_excel(self.roster_file, dtype=str)
                self.roster_df = self.roster_df.fillna('')
            except Exception as e:
                messagebox.showerror("错误", f"加载花名册失败: {e}")
                self.roster_df = pd.DataFrame(columns=['姓名', '身份证号码', '手机号', '银行卡号', '联行号', '开户行'])
        else:
            self.roster_df = pd.DataFrame(columns=['姓名', '身份证号码', '手机号', '银行卡号', '联行号', '开户行'])
            self.save_roster()
    
    def save_roster(self):
        """保存员工花名册"""
        try:
            self.roster_df.to_excel(self.roster_file, index=False)
        except Exception as e:
            messagebox.showerror("错误", f"保存花名册失败: {e}")
    
    def create_widgets(self):
        """创建界面组件"""
        # 创建主容器
        main_container = tk.Frame(self.root, bg=COLORS['bg'])
        main_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # 顶部标题栏
        self.create_header(main_container)
        
        # 创建Notebook(标签页)
        notebook = ttk.Notebook(main_container, style='Custom.TNotebook')
        notebook.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # 标签页1:生成报表
        self.frame_generate = tk.Frame(notebook, bg=COLORS['bg'])
        notebook.add(self.frame_generate, text=" 生成报表 ")
        self.create_generate_tab()
        
        # 标签页2:维护花名册
        self.frame_roster = tk.Frame(notebook, bg=COLORS['bg'])
        notebook.add(self.frame_roster, text=" 维护花名册 ")
        self.create_roster_tab()
        
        # 标签页3:历史记录
        self.frame_history = tk.Frame(notebook, bg=COLORS['bg'])
        notebook.add(self.frame_history, text=" 历史记录 ")
        self.create_history_tab()
        
        # 标签页4:使用说明
        self.frame_help = tk.Frame(notebook, bg=COLORS['bg'])
        notebook.add(self.frame_help, text=" 使用说明 ")
        self.create_help_tab()
        
        # 底部状态栏 - 必须在create_roster_tab之前创建
        self.create_status_bar(main_container)
    
    def create_header(self, parent):
        """创建顶部标题栏"""
        header = tk.Frame(parent, bg=COLORS['primary'], height=70)
        header.pack(fill=tk.X, pady=(0, 10))
        header.pack_propagate(False)
        
        # 标题
        title = tk.Label(header, 
                        text="工资报表生成工具",
                        font=('微软雅黑', 20, 'bold'),
                        bg=COLORS['primary'],
                        fg='white')
        title.pack(side=tk.LEFT, padx=20, pady=10)
        
        # 版本信息
        version = tk.Label(header,
                          text=f"{VERSION}  {COPYRIGHT}",
                          font=('微软雅黑', 9),
                          bg=COLORS['primary'],
                          fg='white')
        version.pack(side=tk.RIGHT, padx=20, pady=10)
    
    def create_generate_tab(self):
        """创建生成报表标签页 - 两栏式布局"""
        # 主容器 - 左右两栏
        main_frame = tk.Frame(self.frame_generate, bg=COLORS['bg'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        # 左侧 - 工资数据输入区域（占主要空间）
        left_panel = tk.Frame(main_frame, bg=COLORS['bg'])
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 输入区域标题
        input_header = tk.Frame(left_panel, bg=COLORS['card'],
                               highlightbackground=COLORS['border'],
                               highlightthickness=1)
        input_header.pack(fill=tk.X, pady=(0, 5))

        tk.Label(input_header, text="📝 工资数据输入",
                font=('微软雅黑', 12, 'bold'),
                bg=COLORS['card'], fg=COLORS['text']).pack(side=tk.LEFT, padx=15, pady=10)

        tk.Label(input_header, text="格式: 姓名 工资金额 (支持从Excel直接粘贴)",
                font=('微软雅黑', 9),
                bg=COLORS['card'], fg=COLORS['text_secondary']).pack(side=tk.RIGHT, padx=15, pady=10)

        # 文本输入框
        text_frame = tk.Frame(left_panel, bg=COLORS['card'],
                             highlightbackground=COLORS['border'],
                             highlightthickness=1)
        text_frame.pack(fill=tk.BOTH, expand=True)

        self.salary_input = tk.Text(text_frame, height=25,
                                   font=('Consolas', 11),
                                   relief='flat',
                                   padx=10, pady=10,
                                   wrap=tk.NONE)
        self.salary_input.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=1, pady=1)

        # 滚动条
        vsb = ttk.Scrollbar(text_frame, orient="vertical",
                           command=self.salary_input.yview)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb = ttk.Scrollbar(left_panel, orient="horizontal",
                           command=self.salary_input.xview)
        hsb.pack(fill=tk.X, pady=(0, 5))

        self.salary_input.configure(yscrollcommand=vsb.set,
                                   xscrollcommand=hsb.set)

        # 示例文本
        self.salary_input.insert("1.0", "# 示例格式:\n# 张三 5000\n# 李四 6000\n# 王五 7000\n\n# 请在上面输入姓名和工资金额，用空格或制表符分隔\n# 也可以直接从Excel复制粘贴")

        # 统计信息
        self.input_stats = tk.Label(left_panel,
                                   text="已输入: 0 人",
                                   font=('微软雅黑', 10),
                                   bg=COLORS['bg'],
                                   fg=COLORS['text_secondary'])
        self.input_stats.pack(anchor='w', pady=5)

        # 绑定输入统计
        self.salary_input.bind('<KeyRelease>', self.update_input_stats)

        # 右侧 - 设置和按钮区域
        right_panel = tk.Frame(main_frame, bg=COLORS['bg'], width=350)
        right_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(15, 0))
        right_panel.pack_propagate(False)

        # 设置区域
        settings_frame = tk.Frame(right_panel, bg=COLORS['card'],
                                 highlightbackground=COLORS['border'],
                                 highlightthickness=1)
        settings_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Label(settings_frame, text="⚙️ 报表设置",
                font=('微软雅黑', 12, 'bold'),
                bg=COLORS['card'], fg=COLORS['text']).pack(anchor='w', padx=15, pady=10)

        # 公司名称
        tk.Label(settings_frame, text="公司名称:",
                font=('微软雅黑', 10),
                bg=COLORS['card'], fg=COLORS['text_secondary']).pack(anchor='w', padx=15)

        self.company_var = tk.StringVar(value=self.default_company)
        tk.Entry(settings_frame, textvariable=self.company_var,
                font=('微软雅黑', 11),
                relief='solid', bd=1).pack(fill=tk.X, padx=15, pady=(5, 10))

        # 发薪月份
        tk.Label(settings_frame, text="发薪月份:",
                font=('微软雅黑', 10),
                bg=COLORS['card'], fg=COLORS['text_secondary']).pack(anchor='w', padx=15)

        # 获取当前时间和上个月
        now = datetime.now()
        if now.month == 1:
            last_month = 12
            last_year = now.year - 1
        else:
            last_month = now.month - 1
            last_year = now.year

        month_frame = tk.Frame(settings_frame, bg=COLORS['card'])
        month_frame.pack(fill=tk.X, padx=15, pady=(5, 15))

        self.year_var = tk.StringVar(value=str(last_year))
        year_combo = ttk.Combobox(month_frame, textvariable=self.year_var,
                                 values=[str(y) for y in range(2020, 2030)],
                                 width=8, state='readonly', font=('微软雅黑', 10))
        year_combo.pack(side=tk.LEFT)
        tk.Label(month_frame, text="年", bg=COLORS['card'], font=('微软雅黑', 10)).pack(side=tk.LEFT, padx=5)

        self.month_var = tk.StringVar(value=str(last_month))
        month_combo = ttk.Combobox(month_frame, textvariable=self.month_var,
                                  values=[str(m) for m in range(1, 13)],
                                  width=6, state='readonly', font=('微软雅黑', 10))
        month_combo.pack(side=tk.LEFT, padx=(10, 0))
        tk.Label(month_frame, text="月", bg=COLORS['card'], font=('微软雅黑', 10)).pack(side=tk.LEFT, padx=5)

        # 快捷操作区域
        quick_frame = tk.Frame(right_panel, bg=COLORS['card'],
                              highlightbackground=COLORS['border'],
                              highlightthickness=1)
        quick_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Label(quick_frame, text="⚡ 快捷操作",
                font=('微软雅黑', 12, 'bold'),
                bg=COLORS['card'], fg=COLORS['text']).pack(anchor='w', padx=15, pady=10)

        tk.Button(quick_frame, text="📁 导入Excel/CSV",
                 command=self.import_salary_data,
                 font=('微软雅黑', 10),
                 bg=COLORS['info'], fg='white',
                 relief='flat', padx=15, pady=8,
                 cursor='hand2').pack(fill=tk.X, padx=15, pady=3)

        tk.Button(quick_frame, text="📋 粘贴Excel数据",
                 command=self.paste_excel_data,
                 font=('微软雅黑', 10),
                 bg='#9C27B0', fg='white',
                 relief='flat', padx=15, pady=8,
                 cursor='hand2').pack(fill=tk.X, padx=15, pady=3)

        # 操作按钮区域
        action_frame = tk.Frame(right_panel, bg=COLORS['card'],
                               highlightbackground=COLORS['border'],
                               highlightthickness=1)
        action_frame.pack(fill=tk.X)

        tk.Label(action_frame, text="🚀 操作",
                font=('微软雅黑', 12, 'bold'),
                bg=COLORS['card'], fg=COLORS['text']).pack(anchor='w', padx=15, pady=10)

        tk.Button(action_frame, text="🗑️ 清空数据",
                 command=self.clear_input,
                 font=('微软雅黑', 11),
                 bg='#757575', fg='white',
                 relief='flat', padx=15, pady=8,
                 cursor='hand2').pack(fill=tk.X, padx=15, pady=3)

        tk.Button(action_frame, text="👁️ 预览数据",
                 command=self.preview_data,
                 font=('微软雅黑', 11),
                 bg=COLORS['warning'], fg='white',
                 relief='flat', padx=15, pady=8,
                 cursor='hand2').pack(fill=tk.X, padx=15, pady=3)

        tk.Button(action_frame, text="✅ 生成报表",
                 command=self.generate_reports,
                 font=('微软雅黑', 13, 'bold'),
                 bg=COLORS['success'], fg='white',
                 relief='flat', padx=15, pady=12,
                 cursor='hand2').pack(fill=tk.X, padx=15, pady=(3, 15))
    
    def create_roster_tab(self):
        """创建维护花名册标签页"""
        # 顶部工具栏
        toolbar = tk.Frame(self.frame_roster, bg=COLORS['card'],
                          highlightbackground=COLORS['border'],
                          highlightthickness=1)
        toolbar.pack(fill=tk.X, padx=10, pady=10)
        
        # 搜索框
        search_frame = tk.Frame(toolbar, bg=COLORS['card'])
        search_frame.pack(side=tk.LEFT, padx=15, pady=10)
        
        tk.Label(search_frame, text="🔍 搜索:",
                font=('微软雅黑', 10),
                bg=COLORS['card']).pack(side=tk.LEFT)
        
        self.search_var = tk.StringVar()
        try:
            self.search_var.trace_add('write', self.search_roster)
        except AttributeError:
            self.search_var.trace('w', self.search_roster)
        
        search_entry = tk.Entry(search_frame, textvariable=self.search_var,
                               font=('微软雅黑', 11), width=30,
                               relief='solid', bd=1)
        search_entry.pack(side=tk.LEFT, padx=10)
        
        # 按钮组
        btn_frame = tk.Frame(toolbar, bg=COLORS['card'])
        btn_frame.pack(side=tk.RIGHT, padx=15, pady=10)
        
        tk.Button(btn_frame, text="➕ 添加员工",
                 command=self.add_employee,
                 font=('微软雅黑', 10),
                 bg=COLORS['primary'], fg='white',
                 relief='flat', padx=15, pady=6,
                 cursor='hand2').pack(side=tk.LEFT, padx=5)

        tk.Button(btn_frame, text="📋 智能粘贴",
                 command=self.smart_paste_employee,
                 font=('微软雅黑', 10),
                 bg='#9C27B0', fg='white',
                 relief='flat', padx=15, pady=6,
                 cursor='hand2').pack(side=tk.LEFT, padx=5)

        tk.Button(btn_frame, text="📥 批量导入",
                 command=self.import_roster,
                 font=('微软雅黑', 10),
                 bg=COLORS['info'], fg='white',
                 relief='flat', padx=15, pady=6,
                 cursor='hand2').pack(side=tk.LEFT, padx=5)

        tk.Button(btn_frame, text="📤 导出花名册",
                 command=self.export_roster,
                 font=('微软雅黑', 10),
                 bg=COLORS['success'], fg='white',
                 relief='flat', padx=15, pady=6,
                 cursor='hand2').pack(side=tk.LEFT, padx=5)
        
        # 员工列表
        list_frame = tk.Frame(self.frame_roster, bg=COLORS['card'],
                             highlightbackground=COLORS['border'],
                             highlightthickness=1)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Treeview
        columns = ('姓名', '身份证号码', '手机号', '银行卡号', '联行号', '开户行')
        self.tree = ttk.Treeview(list_frame, columns=columns,
                                show='headings', height=20,
                                style='Custom.Treeview')
        
        # 设置列宽和标题
        col_widths = {'姓名': 100, '身份证号码': 180, '手机号': 120,
                     '银行卡号': 200, '联行号': 150, '开户行': 250}
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=col_widths.get(col, 120), anchor='center')
        
        # 滚动条
        vsb = ttk.Scrollbar(list_frame, orient="vertical",
                           command=self.tree.yview)
        hsb = ttk.Scrollbar(list_frame, orient="horizontal",
                           command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set,
                           xscrollcommand=hsb.set)
        
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)
        
        # 右键菜单
        self.tree.bind('<Button-3>', self.show_context_menu)
        self.tree.bind('<Double-1>', lambda e: self.edit_employee())
        
        # 统计信息
        self.roster_info = tk.Label(self.frame_roster,
                                   text=f"共 {len(self.roster_df)} 名员工",
                                   font=('微软雅黑', 11, 'bold'),
                                   bg=COLORS['bg'],
                                   fg=COLORS['text'])
        self.roster_info.pack(anchor='w', padx=10, pady=5)
        
        # 刷新列表
        self.refresh_roster_list()
    
    def create_history_tab(self):
        """创建历史记录标签页"""
        # 工具栏
        toolbar = tk.Frame(self.frame_history, bg=COLORS['card'],
                          highlightbackground=COLORS['border'],
                          highlightthickness=1)
        toolbar.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(toolbar, text="📜 生成历史",
                font=('微软雅黑', 12, 'bold'),
                bg=COLORS['card']).pack(side=tk.LEFT, padx=15, pady=10)
        
        tk.Button(toolbar, text="🗑️ 清空历史",
                 command=self.clear_history,
                 font=('微软雅黑', 10),
                 bg=COLORS['danger'], fg='white',
                 relief='flat', padx=15, pady=6,
                 cursor='hand2').pack(side=tk.RIGHT, padx=15, pady=10)
        
        # 历史列表
        list_frame = tk.Frame(self.frame_history, bg=COLORS['card'],
                             highlightbackground=COLORS['border'],
                             highlightthickness=1)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        columns = ('时间', '公司名称', '发薪月份', '人数', '总金额', '文件')
        self.history_tree = ttk.Treeview(list_frame, columns=columns,
                                        show='headings', height=20,
                                        style='Custom.Treeview')
        
        col_widths = {'时间': 150, '公司名称': 250, '发薪月份': 100,
                     '人数': 80, '总金额': 120, '文件': 300}
        for col in columns:
            self.history_tree.heading(col, text=col)
            self.history_tree.column(col, width=col_widths.get(col, 100))
        
        vsb = ttk.Scrollbar(list_frame, orient="vertical",
                           command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=vsb.set)
        
        self.history_tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)
        
        # 刷新历史
        self.refresh_history_list()
    
    def create_help_tab(self):
        """创建使用说明标签页"""
        # 创建Text组件和滚动条
        text_frame = tk.Frame(self.frame_help, bg=COLORS['bg'])
        text_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        help_text = tk.Text(text_frame, wrap=tk.WORD, padx=20, pady=20,
                           font=('微软雅黑', 12),
                           bg=COLORS['card'], fg=COLORS['text'],
                           relief='flat', spacing1=5, spacing2=3)
        help_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(text_frame, orient="vertical",
                                 command=help_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        help_text.configure(yscrollcommand=scrollbar.set)

        # 鼠标滚轮支持
        def on_mousewheel(event):
            help_text.yview_scroll(int(-1*(event.delta/120)), "units")
        help_text.bind("<MouseWheel>", on_mousewheel)

        # 帮助内容
        help_content = f"""
工资报表生成工具 {VERSION} 使用说明

═══════════════════════════════════════════════════════════════

一、快速开始

1. 在"维护花名册"中添加员工信息
2. 切换到"生成报表"标签
3. 输入工资数据（格式：姓名 金额）
4. 点击"生成报表"按钮


二、输入工资数据

支持三种方式输入工资数据：

方式1 - 手动输入：
    张三 5000
    李四 6000
    王五 7000

方式2 - 从Excel粘贴：
    直接从Excel复制姓名和工资两列，粘贴到输入框中

方式3 - 导入文件：
    点击"导入Excel/CSV"按钮，选择工资数据文件


三、员工花名册管理

员工信息包含以下字段：

    姓名          - 必填，用于匹配工资数据
    身份证号码    - 用于个税报表
    手机号        - 联系方式
    银行卡号      - 工资发放账号
    联行号        - 银行大额支付行号（12位）
    开户行        - 完整的开户行名称

快捷操作：
    • 添加员工    - 手动添加单个员工
    • 智能粘贴    - 自动识别文本中的员工信息
    • 批量导入    - 从Excel/CSV文件批量导入
    • 导出花名册  - 备份员工信息


四、输出报表格式

程序会生成4种格式的报表文件：

1. 个税版式 (Excel)
   包含字段：姓名、身份证号码、手机号、工资总额

2. 莱商银行版式 (TXT, GBK编码)
   格式：竖线分隔，包含完整的转账信息
   用途：导入莱商银行代发工资系统

3. 农业银行本行版 (CSV)
   用途：农业银行卡对本行转账
   字段：编号、收款方账号、收款方户名、金额、备注

4. 农业银行跨行版 (CSV)
   用途：农业银行卡对他行转账
   字段：编号、收款方账号、收款方户名、开户银行、开户行大额行号、开户行支行名称、金额、用途


五、重名处理

当花名册中存在同名员工时，程序会弹出选择对话框，显示：
    • 员工姓名和工资金额
    • 身份证号码（脱敏显示）
    • 银行卡号
    • 开户行信息

请根据以上信息选择正确的员工。


六、快捷键

    Ctrl+N    添加新员工
    Ctrl+E    编辑选中员工
    Ctrl+D    删除选中员工
    Ctrl+R    刷新列表
    Ctrl+G    生成报表
    Ctrl+P    预览数据
    F1        使用说明


七、注意事项

    • 员工姓名必须与花名册中的姓名完全一致
    • 银行卡号和联行号请预先在花名册中维护好
    • 莱商银行版为TXT文件，使用GBK编码
    • 生成的文件会自动加上日期后缀（YYYYMMDD）
    • 建议定期备份员工花名册文件
    • 如遇到重名员工，请仔细核对信息后选择


八、常见问题

Q: 员工找不到怎么办？
A: 请先在"维护花名册"中添加该员工信息，确保姓名完全一致。

Q: 银行卡号显示为科学计数法？
A: 在Excel中选中该列，右键→设置单元格格式→文本。

Q: 莱商银行TXT打开乱码？
A: 用记事本打开，选择"另存为"→编码选择"ANSI"或"GBK"。

Q: 支持哪些银行？
A: 程序会自动识别：农业银行、莱商银行、工商银行、建设银行、
   中国银行、交通银行、邮政储蓄银行、招商银行、平安银行等。


═══════════════════════════════════════════════════════════════

工资报表生成工具 {VERSION}
{COPYRIGHT}

技术支持：如有问题请联系开发团队
"""

        help_text.insert(tk.END, help_content)
        help_text.config(state=tk.DISABLED)
    
    def create_status_bar(self, parent):
        """创建状态栏"""
        status_frame = tk.Frame(parent, bg=COLORS['card'],
                               highlightbackground=COLORS['border'],
                               highlightthickness=1)
        status_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.status_label = tk.Label(status_frame,
                                    text="就绪",
                                    font=('微软雅黑', 10),
                                    bg=COLORS['card'],
                                    fg=COLORS['text_secondary'],
                                    anchor='w')
        self.status_label.pack(side=tk.LEFT, padx=15, pady=8)
        
        # 花名册状态
        self.roster_status = tk.Label(status_frame,
                                     text=f"花名册: {len(self.roster_df)}人",
                                     font=('微软雅黑', 10),
                                     bg=COLORS['card'],
                                     fg=COLORS['text_secondary'])
        self.roster_status.pack(side=tk.RIGHT, padx=15, pady=8)
    
    def bind_shortcuts(self):
        """绑定快捷键"""
        self.root.bind('<Control-n>', lambda e: self.add_employee())
        self.root.bind('<Control-e>', lambda e: self.edit_employee())
        self.root.bind('<Control-d>', lambda e: self.delete_employee())
        self.root.bind('<Control-r>', lambda e: self.refresh_roster_list())
        self.root.bind('<Control-g>', lambda e: self.generate_reports())
        self.root.bind('<Control-p>', lambda e: self.preview_data())
        self.root.bind('<F1>', lambda e: self.show_help())
    
    def update_input_stats(self, event=None):
        """更新输入统计"""
        text = self.salary_input.get("1.0", tk.END).strip()
        lines = [l for l in text.split('\n') if l.strip() and not l.strip().startswith('#')]
        count = len(lines)
        self.input_stats.config(text=f"已输入: {count} 人")
    
    def import_salary_data(self):
        """导入工资数据"""
        file_path = filedialog.askopenfilename(
            title="选择工资数据文件",
            filetypes=[
                ("Excel文件", "*.xlsx *.xls"),
                ("CSV文件", "*.csv"),
                ("所有文件", "*.*")
            ]
        )
        if file_path:
            try:
                if file_path.endswith('.csv'):
                    df = pd.read_csv(file_path, dtype=str)
                else:
                    df = pd.read_excel(file_path, dtype=str)
                
                # 尝试识别姓名和工资列
                name_col = None
                salary_col = None
                
                for col in df.columns:
                    col_lower = col.lower()
                    if any(keyword in col_lower for keyword in ['姓名', '名字', 'name', '员工']):
                        name_col = col
                    if any(keyword in col_lower for keyword in ['工资', '金额', 'salary', 'money', '薪资']):
                        salary_col = col
                
                # 如果没找到，使用前两列
                if name_col is None:
                    name_col = df.columns[0]
                if salary_col is None and len(df.columns) > 1:
                    salary_col = df.columns[1]
                
                # 生成输入文本
                lines = []
                for _, row in df.iterrows():
                    name = str(row.get(name_col, '')).strip()
                    salary = str(row.get(salary_col, '')).strip()
                    if name and salary:
                        lines.append(f"{name} {salary}")
                
                # 清空并插入
                self.salary_input.delete("1.0", tk.END)
                self.salary_input.insert("1.0", '\n'.join(lines))
                self.update_input_stats()
                
                messagebox.showinfo("成功", f"已导入 {len(lines)} 条工资数据")
                self.status_label.config(text=f"已导入: {file_path}")
                
            except Exception as e:
                messagebox.showerror("错误", f"导入失败: {e}")
    
    def paste_excel_data(self):
        """粘贴Excel数据"""
        try:
            # 获取剪贴板内容
            clipboard = self.root.clipboard_get()
            if clipboard:
                self.salary_input.delete("1.0", tk.END)
                self.salary_input.insert("1.0", clipboard)
                self.update_input_stats()
                messagebox.showinfo("成功", "已粘贴剪贴板数据")
        except:
            messagebox.showwarning("提示", "剪贴板中没有数据")
    
    def show_context_menu(self, event):
        """显示右键菜单"""
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="编辑", command=self.edit_employee)
        menu.add_command(label="删除", command=self.delete_employee)
        menu.add_separator()
        menu.add_command(label="刷新", command=self.refresh_roster_list)
        menu.post(event.x_root, event.y_root)
    
    def show_help(self):
        """显示帮助"""
        messagebox.showinfo("快捷键",
                           "Ctrl+N - 添加新员工\n"
                           "Ctrl+E - 编辑选中员工\n"
                           "Ctrl+D - 删除选中员工\n"
                           "Ctrl+R - 刷新列表\n"
                           "Ctrl+G - 生成报表\n"
                           "Ctrl+P - 预览数据\n"
                           "F1 - 使用说明")
    
    def import_roster(self):
        """批量导入花名册"""
        file_path = filedialog.askopenfilename(
            title="选择花名册文件",
            filetypes=[
                ("Excel文件", "*.xlsx *.xls"),
                ("CSV文件", "*.csv")
            ]
        )
        if file_path:
            try:
                if file_path.endswith('.csv'):
                    df = pd.read_csv(file_path, dtype=str)
                else:
                    df = pd.read_excel(file_path, dtype=str)
                
                # 检查必需列
                required_cols = ['姓名', '身份证号码', '手机号', '银行卡号', '联行号', '开户行']
                missing_cols = [col for col in required_cols if col not in df.columns]
                
                if missing_cols:
                    messagebox.showwarning("警告",
                                         f"缺少以下列: {', '.join(missing_cols)}\n\n"
                                         f"现有列: {', '.join(df.columns)}")
                    return
                
                # 合并数据
                self.roster_df = pd.concat([self.roster_df, df[required_cols]],
                                          ignore_index=True)
                # 去重（按姓名）
                self.roster_df = self.roster_df.drop_duplicates(subset=['姓名'],
                                                               keep='last')
                self.save_roster()
                self.refresh_roster_list()
                
                messagebox.showinfo("成功", f"成功导入 {len(df)} 名员工")
                self.status_label.config(text=f"已导入花名册: {file_path}")
                
            except Exception as e:
                messagebox.showerror("错误", f"导入失败: {e}")
    
    def refresh_history_list(self):
        """刷新历史列表"""
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        
        for record in reversed(self.history):
            self.history_tree.insert('', tk.END, values=(
                record.get('time', ''),
                record.get('company', ''),
                record.get('period', ''),
                record.get('count', ''),
                f"{record.get('total', 0):.2f}",
                record.get('files', '')
            ))
    
    def add_history(self, company, period, count, total, files):
        """添加历史记录"""
        record = {
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'company': company,
            'period': period,
            'count': count,
            'total': total,
            'files': files
        }
        self.history.append(record)
        self.save_config()
        self.refresh_history_list()
    
    def clear_history(self):
        """清空历史"""
        if messagebox.askyesno("确认", "确定要清空所有历史记录吗？"):
            self.history = []
            self.save_config()
            self.refresh_history_list()
            messagebox.showinfo("成功", "历史记录已清空")
    
    def clear_input(self):
        """清空输入"""
        if messagebox.askyesno("确认", "确定要清空所有输入数据吗？"):
            self.salary_input.delete("1.0", tk.END)
            self.update_input_stats()
    
    def preview_data(self):
        """预览数据"""
        input_text = self.salary_input.get("1.0", tk.END).strip()
        lines = [line.strip() for line in input_text.split('\n')
                if line.strip() and not line.strip().startswith('#')]
        
        if not lines:
            messagebox.showwarning("提示", "没有输入数据")
            return
        
        data, errors = self.parse_salary_data(lines)
        
        # 显示预览窗口
        preview_window = tk.Toplevel(self.root)
        preview_window.title("数据预览")
        preview_window.geometry("900x600")
        preview_window.configure(bg=COLORS['bg'])
        
        # 标题
        tk.Label(preview_window, text="📊 数据预览",
                font=('微软雅黑', 16, 'bold'),
                bg=COLORS['bg'],
                fg=COLORS['text']).pack(pady=15)
        
        # 统计信息
        stats_frame = tk.Frame(preview_window, bg=COLORS['card'],
                              highlightbackground=COLORS['border'],
                              highlightthickness=1)
        stats_frame.pack(fill=tk.X, padx=20, pady=5)
        
        tk.Label(stats_frame,
                text=f"✅ 有效数据: {len(data)} 人    ❌ 错误: {len(errors)} 条",
                font=('微软雅黑', 12),
                bg=COLORS['card'],
                fg=COLORS['text']).pack(padx=15, pady=10)
        
        # 内容区域
        content_frame = tk.Frame(preview_window, bg=COLORS['bg'])
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # 有效数据
        if data:
            data_frame = tk.LabelFrame(content_frame, text="有效数据",
                                      font=('微软雅黑', 11, 'bold'),
                                      bg=COLORS['card'])
            data_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
            
            tree = ttk.Treeview(data_frame,
                               columns=('姓名', '工资', '银行卡号', '开户行'),
                               show='headings', height=10)
            for col in ('姓名', '工资', '银行卡号', '开户行'):
                tree.heading(col, text=col)
                tree.column(col, width=150)
            
            for item in data:
                tree.insert('', tk.END, values=(
                    item['姓名'],
                    f"{item['工资']:.2f}",
                    item.get('银行卡号', '未找到'),
                    item.get('开户行', '未找到')
                ))
            
            tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 错误信息
        if errors:
            error_frame = tk.LabelFrame(content_frame, text="错误信息",
                                       font=('微软雅黑', 11, 'bold'),
                                       bg=COLORS['card'],
                                       fg=COLORS['danger'])
            error_frame.pack(fill=tk.X)
            
            error_text = tk.Text(error_frame, height=5, font=('微软雅黑', 10))
            error_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            for err in errors[:20]:
                error_text.insert(tk.END, f"• {err}\n")
            if len(errors) > 20:
                error_text.insert(tk.END, f"...还有 {len(errors)-20} 条错误\n")
            
            error_text.config(state=tk.DISABLED)
        
        # 关闭按钮
        tk.Button(preview_window, text="关闭",
                 command=preview_window.destroy,
                 font=('微软雅黑', 11),
                 bg=COLORS['primary'], fg='white',
                 relief='flat', padx=30, pady=8).pack(pady=15)
    
    def parse_salary_data(self, lines):
        """解析工资数据"""
        data = []
        errors = []
        
        for line in lines:
            parts = re.split(r'\s+', line.strip())
            if len(parts) >= 2:
                name = parts[0]
                try:
                    salary = float(parts[1])
                    if salary <= 0:
                        errors.append(f"{name}: 工资金额必须大于0")
                        continue
                    
                    emp = self.roster_df[self.roster_df['姓名'] == name]
                    if len(emp) > 0:
                        # 处理重名情况
                        if len(emp) > 1:
                            # 弹出选择对话框
                            dialog = DuplicateNameDialog(self.root, name, salary, emp)
                            if dialog.selected_employee is not None:
                                selected_idx = dialog.selected_employee
                                # 使用 iloc 通过位置索引获取
                                selected_emp = emp.iloc[selected_idx]
                                data.append({
                                    '姓名': name,
                                    '工资': salary,
                                    '身份证号码': selected_emp.get('身份证号码', ''),
                                    '手机号': selected_emp.get('手机号', ''),
                                    '银行卡号': selected_emp.get('银行卡号', ''),
                                    '联行号': selected_emp.get('联行号', ''),
                                    '开户行': selected_emp.get('开户行', '')
                                })
                            else:
                                errors.append(f"'{name}': 未选择员工（重名）")
                        else:
                            data.append({
                                '姓名': name,
                                '工资': salary,
                                '身份证号码': emp.iloc[0].get('身份证号码', ''),
                                '手机号': emp.iloc[0].get('手机号', ''),
                                '银行卡号': emp.iloc[0].get('银行卡号', ''),
                                '联行号': emp.iloc[0].get('联行号', ''),
                                '开户行': emp.iloc[0].get('开户行', '')
                            })
                    else:
                        errors.append(f"'{name}': 不在花名册中")
                except ValueError:
                    errors.append(f"'{line}': 工资金额格式错误")
            else:
                errors.append(f"'{line}': 格式错误")
        
        return data, errors
    
    def generate_reports(self):
        """生成报表"""
        company_name = self.company_var.get().strip()
        if not company_name:
            messagebox.showwarning("提示", "请输入公司名称")
            return
        
        year = self.year_var.get()
        month = self.month_var.get()
        salary_period = f"{year}年{month}月"
        
        input_text = self.salary_input.get("1.0", tk.END).strip()
        lines = [line.strip() for line in input_text.split('\n')
                if line.strip() and not line.strip().startswith('#')]
        
        if not lines:
            messagebox.showwarning("提示", "没有输入工资数据")
            return
        
        salary_data, errors = self.parse_salary_data(lines)
        
        if errors:
            error_msg = "\n".join(errors[:10])
            if len(errors) > 10:
                error_msg += f"\n...还有{len(errors)-10}条错误"
            if not salary_data:
                messagebox.showerror("错误", f"数据处理失败:\n{error_msg}")
                return
            else:
                if not messagebox.askyesno("警告",
                                          f"存在 {len(errors)} 条错误，是否继续生成报表？\n\n"
                                          f"错误信息:\n{error_msg}"):
                    return
        
        if not salary_data:
            messagebox.showwarning("提示", "没有有效数据")
            return
        
        date_str = datetime.now().strftime("%Y%m%d")
        
        # 生成报表
        try:
            self.status_label.config(text="正在生成报表...")
            self.root.update()
            
            self.generate_tax_version(salary_data, company_name, salary_period, date_str)
            self.generate_laishang_version(salary_data, company_name, salary_period, date_str)
            self.generate_agricultural_version(salary_data, company_name, salary_period, date_str)
            
            # 添加历史记录
            files = f"{company_name}-{salary_period}-*.xlsx/csv/txt"
            self.add_history(company_name, salary_period,
                           len(salary_data),
                           sum(d['工资'] for d in salary_data),
                           files)
            
            # 保存默认公司名
            self.save_config()
            
            success_msg = f"✅ 报表生成成功！\n\n"
            success_msg += f"📊 公司名称: {company_name}\n"
            success_msg += f"📅 发薪月份: {salary_period}\n\n"
            success_msg += f"📁 生成文件:\n"
            success_msg += f"  • 个税版式: {company_name}-{salary_period}-个税版式-{date_str}.xlsx\n"
            success_msg += f"  • 莱商银行版式: {company_name}-{salary_period}-莱商银行版式-{date_str}.txt\n"
            success_msg += f"  • 农业银行本行: {company_name}-{salary_period}-农业银行本行-{date_str}.csv\n"
            success_msg += f"  • 农业银行跨行: {company_name}-{salary_period}-农业银行跨行-{date_str}.csv\n\n"
            success_msg += f"👥 共 {len(salary_data)} 人\n"
            success_msg += f"💰 总金额: {sum(d['工资'] for d in salary_data):.2f} 元"
            
            messagebox.showinfo("成功", success_msg)
            self.status_label.config(text=f"已生成报表: {company_name} {salary_period} ({len(salary_data)}人)")
            
        except Exception as e:
            messagebox.showerror("错误", f"生成报表失败: {e}")
            self.status_label.config(text="生成报表失败")
    
    def generate_tax_version(self, data, company_name, salary_period, date_str):
        """生成个税版"""
        df = pd.DataFrame(data)
        df_output = pd.DataFrame({
            '姓名': df['姓名'],
            '身份证号码': df['身份证号码'],
            '手机号': df['手机号'],
            '工资总额': df['工资']
        })
        output_file = f"{company_name}-{salary_period}-个税版式-{date_str}.xlsx"
        df_output.to_excel(output_file, index=False)
    
    def generate_laishang_version(self, data, company_name, salary_period, date_str):
        """生成莱商银行版"""
        lines = []
        lines.append(f"{len(data)}|{sum(d['工资'] for d in data):.2f}")
        lines.append("收款人账号|收款人名称|收款银行|收款账户开户行行号|行内行外(行外01,行内00)|转账金额|是否加急(普通0,加急1,实时2)|转账附言")
        
        for d in data:
            card = d['银行卡号']
            name = d['姓名']
            bank_name = d.get('开户行', '')
            interbank = d.get('联行号', '')
            interbank_clean = str(interbank).lstrip('0') if interbank else ''
            inner_type = '00' if '莱商' in bank_name else '01'
            amount = f"{d['工资']:.2f}"
            
            lines.append(f"{card}|{name}|{bank_name}|{interbank_clean}|{inner_type}|{amount}|0|工资")
        
        output_file = f"{company_name}-{salary_period}-莱商银行版式-{date_str}.txt"
        with open(output_file, 'w', encoding='gbk') as f:
            f.write('\n'.join(lines))
    
    def generate_agricultural_version(self, data, company_name, salary_period, date_str):
        """生成农业银行版"""
        benhang_lines = []
        kuahang_lines = []
        
        for d in data:
            card = d['银行卡号']
            name = d['姓名']
            bank_name = d.get('开户行', '')
            interbank = d.get('联行号', '')
            amount = f"{d['工资']:.2f}"
            
            if '农业银行' in bank_name:
                benhang_lines.append((card, name, amount))
            else:
                bank_code = self.extract_bank_code(bank_name)
                kuahang_lines.append((card, name, bank_code, interbank, bank_name, amount))
        
        if benhang_lines:
            benhang_file = f"{company_name}-{salary_period}-农业银行本行-{date_str}.csv"
            with open(benhang_file, 'w', encoding='utf-8') as f:
                for i, (card, name, amount) in enumerate(benhang_lines, 1):
                    f.write(f"{i},{card},{name},{amount},工资\n")
        
        if kuahang_lines:
            kuahang_file = f"{company_name}-{salary_period}-农业银行跨行-{date_str}.csv"
            with open(kuahang_file, 'w', encoding='utf-8') as f:
                for i, (card, name, bank_code, interbank, bank_name, amount) in enumerate(kuahang_lines, 1):
                    f.write(f"{i},{card},{name},{bank_code},{interbank},{bank_name},{amount},工资\n")
    
    def extract_bank_code(self, bank_name):
        """提取银行代码"""
        bank_mapping = [
            ('邮政', '中国邮政储蓄银行'),
            ('建设', '中国建设银行'),
            ('工商', '中国工商银行'),
            ('农业', '中国农业银行'),
            ('中国银行', '中国银行'),
            ('交通', '交通银行'),
            ('平安', '平安银行'),
            ('招商', '招商银行'),
            ('浦发', '浦发银行'),
            ('民生', '中国民生银行'),
            ('光大', '中国光大银行'),
            ('中信', '中信银行'),
            ('兴业', '兴业银行'),
            ('华夏', '华夏银行'),
        ]
        
        for keyword, code in bank_mapping:
            if keyword in bank_name:
                return code
        
        return bank_name[:10] if bank_name else ''
    
    def search_roster(self, *args):
        """搜索花名册"""
        keyword = self.search_var.get().strip()
        self.refresh_roster_list(keyword)
    
    def refresh_roster_list(self, keyword=''):
        """刷新员工列表"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        df = self.roster_df
        if keyword:
            mask = df['姓名'].str.contains(keyword, na=False, case=False) | \
                   df['身份证号码'].str.contains(keyword, na=False, case=False) | \
                   df['银行卡号'].str.contains(keyword, na=False, case=False) | \
                   df['开户行'].str.contains(keyword, na=False, case=False)
            df = df[mask]
        
        for _, row in df.iterrows():
            self.tree.insert('', tk.END, values=(
                row.get('姓名', ''),
                row.get('身份证号码', ''),
                row.get('手机号', ''),
                row.get('银行卡号', ''),
                row.get('联行号', ''),
                row.get('开户行', '')
            ))
        
        self.roster_info.config(text=f"共 {len(self.roster_df)} 名员工，显示 {len(df)} 条")
        if hasattr(self, 'roster_status'):
            self.roster_status.config(text=f"花名册: {len(self.roster_df)}人")
    
    def add_employee(self):
        """添加员工"""
        EmployeeDialog(self.root, self, "添加员工")
    
    def edit_employee(self):
        """编辑员工"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请选择要编辑的员工")
            return
        
        values = self.tree.item(selected[0])['values']
        name = values[0]
        emp = self.roster_df[self.roster_df['姓名'] == name]
        if len(emp) > 0:
            EmployeeDialog(self.root, self, "编辑员工", emp.iloc[0])
    
    def delete_employee(self):
        """删除员工"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请选择要删除的员工")
            return
        
        values = self.tree.item(selected[0])['values']
        name = values[0]
        
        if messagebox.askyesno("确认", f"确定要删除员工 '{name}' 吗？"):
            self.roster_df = self.roster_df[self.roster_df['姓名'] != name]
            self.save_roster()
            self.refresh_roster_list()
            messagebox.showinfo("成功", f"员工 '{name}' 已删除")
    
    def export_roster(self):
        """导出花名册"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel文件", "*.xlsx"), ("CSV文件", "*.csv")],
            initialfile=f"员工花名册_{datetime.now().strftime('%Y%m%d')}.xlsx"
        )
        if file_path:
            try:
                if file_path.endswith('.csv'):
                    self.roster_df.to_csv(file_path, index=False, encoding='utf-8-sig')
                else:
                    self.roster_df.to_excel(file_path, index=False)
                messagebox.showinfo("成功", f"花名册已导出到:\n{file_path}")
            except Exception as e:
                messagebox.showerror("错误", f"导出失败: {e}")

    def smart_paste_employee(self):
        """智能粘贴员工信息"""
        dialog = SmartPasteDialog(self.root, self)
        if dialog.parsed_data:
            data = dialog.parsed_data

            # 检查是否已存在
            existing = self.roster_df[self.roster_df['姓名'] == data['姓名']]
            if len(existing) > 0:
                if not messagebox.askyesno("确认",
                    f"员工 '{data['姓名']}' 已存在，是否更新信息？"):
                    return
                # 删除旧记录
                self.roster_df = self.roster_df[self.roster_df['姓名'] != data['姓名']]

            # 添加新记录
            new_row = pd.DataFrame([data])
            self.roster_df = pd.concat([self.roster_df, new_row], ignore_index=True)
            self.save_roster()
            self.refresh_roster_list()

            # 显示成功信息
            info = f"员工 '{data['姓名']}' 已{'更新' if len(existing) > 0 else '添加'}\n\n"
            info += f"身份证: {data['身份证号码'] or '未填写'}\n"
            info += f"银行卡: {data['银行卡号'] or '未填写'}\n"
            info += f"开户行: {data['开户行'] or '未填写'}"
            messagebox.showinfo("成功", info)


class EmployeeDialog:
    """员工信息对话框"""
    
    def __init__(self, parent, main_app, title, employee=None):
        self.main_app = main_app
        self.employee = employee
        self.is_edit = employee is not None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("500x450")
        self.dialog.configure(bg=COLORS['bg'])
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 居中显示
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() - 500) // 2
        y = (self.dialog.winfo_screenheight() - 450) // 2
        self.dialog.geometry(f"500x450+{x}+{y}")
        
        self.create_widgets()
        
        if employee is not None:
            self.load_data()
        
        self.dialog.wait_window(self.dialog)
    
    def create_widgets(self):
        """创建对话框组件"""
        # 标题
        header = tk.Frame(self.dialog, bg=COLORS['primary'], height=50)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        title_text = "编辑员工" if self.is_edit else "添加员工"
        tk.Label(header, text=title_text,
                font=('微软雅黑', 14, 'bold'),
                bg=COLORS['primary'],
                fg='white').pack(pady=10)
        
        # 表单区域
        form_frame = tk.Frame(self.dialog, bg=COLORS['card'],
                             highlightbackground=COLORS['border'],
                             highlightthickness=1)
        form_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 表单字段
        fields = [
            ('姓名 *', 'name', '请输入员工姓名'),
            ('身份证号码', 'id_card', '18位身份证号'),
            ('手机号', 'phone', '11位手机号码'),
            ('银行卡号 *', 'bank_card', '工资卡号'),
            ('联行号', 'interbank', '12位联行号'),
            ('开户行 *', 'bank_name', '完整的开户行名称')
        ]
        
        self.vars = {}
        for i, (label_text, var_name, placeholder) in enumerate(fields):
            row = tk.Frame(form_frame, bg=COLORS['card'])
            row.pack(fill=tk.X, padx=15, pady=8)
            
            tk.Label(row, text=label_text,
                    font=('微软雅黑', 10),
                    bg=COLORS['card'],
                    fg=COLORS['text'],
                    width=12, anchor='e').pack(side=tk.LEFT)
            
            var = tk.StringVar()
            self.vars[var_name] = var
            
            entry = tk.Entry(row, textvariable=var,
                           font=('微软雅黑', 11),
                           relief='solid', bd=1,
                           width=35)
            entry.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
            entry.insert(0, placeholder)
            entry.config(fg='gray')
            
            # 占位符处理
            entry.bind('<FocusIn>', lambda e, ent=entry, ph=placeholder:
                      self.on_entry_focus_in(e, ent, ph))
            entry.bind('<FocusOut>', lambda e, ent=entry, ph=placeholder:
                      self.on_entry_focus_out(e, ent, ph))
        
        # 按钮区域
        btn_frame = tk.Frame(self.dialog, bg=COLORS['bg'])
        btn_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        tk.Button(btn_frame, text="取消",
                 command=self.dialog.destroy,
                 font=('微软雅黑', 11),
                 bg='#757575', fg='white',
                 relief='flat', padx=25, pady=8,
                 cursor='hand2').pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_frame, text="保存",
                 command=self.save,
                 font=('微软雅黑', 11, 'bold'),
                 bg=COLORS['success'], fg='white',
                 relief='flat', padx=25, pady=8,
                 cursor='hand2').pack(side=tk.RIGHT, padx=5)
    
    def on_entry_focus_in(self, event, entry, placeholder):
        """输入框获得焦点"""
        if entry.get() == placeholder:
            entry.delete(0, tk.END)
            entry.config(fg=COLORS['text'])
    
    def on_entry_focus_out(self, event, entry, placeholder):
        """输入框失去焦点"""
        if not entry.get():
            entry.insert(0, placeholder)
            entry.config(fg='gray')
    
    def load_data(self):
        """加载员工数据"""
        placeholders = {
            'name': '请输入员工姓名',
            'id_card': '18位身份证号',
            'phone': '11位手机号码',
            'bank_card': '工资卡号',
            'interbank': '12位联行号',
            'bank_name': '完整的开户行名称'
        }
        
        data_map = {
            'name': self.employee.get('姓名', ''),
            'id_card': self.employee.get('身份证号码', ''),
            'phone': self.employee.get('手机号', ''),
            'bank_card': self.employee.get('银行卡号', ''),
            'interbank': self.employee.get('联行号', ''),
            'bank_name': self.employee.get('开户行', '')
        }
        
        for var_name, value in data_map.items():
            if value and value != placeholders.get(var_name, ''):
                self.vars[var_name].set(value)
    
    def save(self):
        """保存员工信息"""
        name = self.vars['name'].get().strip()
        placeholders = ['请输入员工姓名', '18位身份证号', '11位手机号码',
                       '工资卡号', '12位联行号', '完整的开户行名称']
        
        if not name or name in placeholders:
            messagebox.showwarning("提示", "姓名不能为空", parent=self.dialog)
            return
        
        # 获取数据（排除占位符）
        def get_value(var_name):
            val = self.vars[var_name].get().strip()
            return '' if val in placeholders else val
        
        data = {
            '姓名': name,
            '身份证号码': get_value('id_card'),
            '手机号': get_value('phone'),
            '银行卡号': get_value('bank_card'),
            '联行号': get_value('interbank'),
            '开户行': get_value('bank_name')
        }
        
        # 检查必填项
        if not data['银行卡号']:
            messagebox.showwarning("提示", "银行卡号不能为空", parent=self.dialog)
            return
        if not data['开户行']:
            messagebox.showwarning("提示", "开户行不能为空", parent=self.dialog)
            return
        
        # 如果是编辑，先删除旧记录
        if self.is_edit:
            old_name = self.employee.get('姓名', '')
            self.main_app.roster_df = self.main_app.roster_df[self.main_app.roster_df['姓名'] != old_name]
        
        # 检查是否已存在
        if not self.is_edit and name in self.main_app.roster_df['姓名'].values:
            messagebox.showwarning("提示", f"员工 '{name}' 已存在", parent=self.dialog)
            return
        
        # 添加新记录
        new_row = pd.DataFrame([data])
        self.main_app.roster_df = pd.concat([self.main_app.roster_df, new_row], ignore_index=True)
        self.main_app.save_roster()
        self.main_app.refresh_roster_list()
        
        messagebox.showinfo("成功", f"员工 '{name}' 已{'更新' if self.is_edit else '添加'}",
                           parent=self.dialog)
        self.dialog.destroy()


class DuplicateNameDialog:
    """重名选择对话框"""
    
    def __init__(self, parent, name, salary, employees):
        self.selected_employee = None

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("选择员工")
        self.dialog.geometry("700x420")
        self.dialog.configure(bg=COLORS['bg'])
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # 居中显示
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() - 700) // 2
        y = (self.dialog.winfo_screenheight() - 420) // 2
        self.dialog.geometry(f"700x420+{x}+{y}")

        # 标题
        header = tk.Frame(self.dialog, bg=COLORS['warning'], height=80)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        tk.Label(header, text=f"⚠️ 发现重名员工: {name}",
                font=('微软雅黑', 16, 'bold'),
                bg=COLORS['warning'],
                fg='white').pack(pady=(15, 5))

        tk.Label(header, text=f"工资金额: {salary:.2f} 元",
                font=('微软雅黑', 12),
                bg=COLORS['warning'],
                fg='white').pack()

        # 说明文字
        tk.Label(self.dialog,
                text="请选择对应的员工（根据身份证后4位或银行卡号区分）：",
                font=('微软雅黑', 11),
                bg=COLORS['bg'],
                fg=COLORS['text']).pack(anchor='w', padx=20, pady=15)
        
        # 员工列表
        list_frame = tk.Frame(self.dialog, bg=COLORS['card'],
                             highlightbackground=COLORS['border'],
                             highlightthickness=1)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        columns = ('姓名', '身份证', '银行卡号', '开户行')
        self.tree = ttk.Treeview(list_frame, columns=columns,
                                show='headings', height=8,
                                style='Custom.Treeview')
        
        col_widths = {'姓名': 100, '身份证': 180, '银行卡号': 200, '开户行': 150}
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=col_widths.get(col, 120), anchor='center')
        
        vsb = ttk.Scrollbar(list_frame, orient="vertical",
                           command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)
        
        # 插入数据 - 使用 enumerate 获取位置索引
        for pos_idx, (df_idx, emp) in enumerate(employees.iterrows()):
            id_card = emp.get('身份证号码', '')
            id_display = f"{id_card[:14]}****{id_card[-4:]}" if len(id_card) >= 18 else id_card
            
            self.tree.insert('', tk.END, values=(
                emp.get('姓名', ''),
                id_display,
                emp.get('银行卡号', ''),
                emp.get('开户行', '')
            ), tags=(str(pos_idx),))
        
        # 按钮
        btn_frame = tk.Frame(self.dialog, bg=COLORS['bg'])
        btn_frame.pack(fill=tk.X, padx=20, pady=15)
        
        tk.Button(btn_frame, text="取消",
                 command=self.dialog.destroy,
                 font=('微软雅黑', 11),
                 bg='#757575', fg='white',
                 relief='flat', padx=25, pady=8).pack(side=tk.LEFT)
        
        tk.Button(btn_frame, text="确认选择",
                 command=self.confirm_selection,
                 font=('微软雅黑', 11, 'bold'),
                 bg=COLORS['success'], fg='white',
                 relief='flat', padx=25, pady=8).pack(side=tk.RIGHT)
        
        # 双击选择
        self.tree.bind('<Double-1>', lambda e: self.confirm_selection())
        
        self.dialog.wait_window(self.dialog)
    
    def confirm_selection(self):
        """确认选择"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请选择一个员工", parent=self.dialog)
            return
        
        # 获取选中行的tag（即原始索引）
        item = self.tree.item(selected[0])
        idx = int(item['tags'][0])
        self.selected_employee = idx
        self.dialog.destroy()


class SmartPasteDialog:
    """智能粘贴对话框"""
    
    def __init__(self, parent, main_app):
        self.main_app = main_app
        self.parsed_data = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("智能粘贴员工信息")
        self.dialog.geometry("600x550")
        self.dialog.configure(bg=COLORS['bg'])
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # 居中显示
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() - 600) // 2
        y = (self.dialog.winfo_screenheight() - 500) // 2
        self.dialog.geometry(f"600x500+{x}+{y}")
        
        # 标题
        header = tk.Frame(self.dialog, bg=COLORS['info'], height=60)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(header, text="📋 智能粘贴员工信息",
                font=('微软雅黑', 14, 'bold'),
                bg=COLORS['info'],
                fg='white').pack(pady=15)
        
        # 说明
        tk.Label(self.dialog,
                text="请粘贴包含员工信息的文本，程序会自动识别：",
                font=('微软雅黑', 10),
                bg=COLORS['bg'],
                fg=COLORS['text_secondary']).pack(anchor='w', padx=20, pady=10)
        
        # 示例
        example_text = """示例格式：
1.姓名：张三
2.身份证号码：370830200510031731
3.银行卡号：6214 8318 3028 5166
4.开户行行号：308290003298
5.开户行名称：上海天山支行
6.手机号：18608075173"""
        
        tk.Label(self.dialog, text=example_text,
                font=('微软雅黑', 9),
                bg=COLORS['bg'],
                fg=COLORS['text_secondary'],
                justify=tk.LEFT).pack(anchor='w', padx=20)
        
        # 输入框
        input_frame = tk.Frame(self.dialog, bg=COLORS['card'],
                              highlightbackground=COLORS['border'],
                              highlightthickness=1)
        input_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        self.text_input = tk.Text(input_frame, height=10,
                                 font=('微软雅黑', 11),
                                 relief='flat', padx=10, pady=10)
        self.text_input.pack(fill=tk.BOTH, expand=True)
        
        # 解析按钮
        btn_frame = tk.Frame(self.dialog, bg=COLORS['bg'])
        btn_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Button(btn_frame, text="取消",
                 command=self.dialog.destroy,
                 font=('微软雅黑', 11),
                 bg='#757575', fg='white',
                 relief='flat', padx=20, pady=8).pack(side=tk.LEFT)
        
        tk.Button(btn_frame, text="🔍 智能解析",
                 command=self.parse_text,
                 font=('微软雅黑', 11, 'bold'),
                 bg=COLORS['info'], fg='white',
                 relief='flat', padx=20, pady=8).pack(side=tk.RIGHT)
        
        self.dialog.wait_window(self.dialog)
    
    def parse_text(self):
        """解析文本"""
        text = self.text_input.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("提示", "请输入内容", parent=self.dialog)
            return
        
        # 解析字段
        data = {
            '姓名': '',
            '身份证号码': '',
            '手机号': '',
            '银行卡号': '',
            '联行号': '',
            '开户行': ''
        }
        
        # 定义匹配模式
        patterns = [
            (r'(?:姓名|名字|员工姓名)[：:\s]*([^\n]+)', '姓名'),
            (r'(?:身份证号码|身份证号|身份证)[：:\s]*(\d{17}[\dXx])', '身份证号码'),
            (r'(?:手机号码|手机号|电话|手机)[：:\s]*(1\d{10})', '手机号'),
            (r'(?:银行卡号|卡号|银行账号)[：:\s]*([\d\s]+)', '银行卡号'),
            (r'(?:开户行行号|联行号|行号)[：:\s]*(\d{12})', '联行号'),
            (r'(?:开户行名称|开户行|银行)[：:\s]*([^\n]+)', '开户行'),
        ]
        
        for pattern, field in patterns:
            match = re.search(pattern, text)
            if match:
                value = match.group(1).strip()
                # 清理银行卡号中的空格
                if field == '银行卡号':
                    value = re.sub(r'\s+', '', value)
                data[field] = value
        
        # 检查是否解析到姓名
        if not data['姓名']:
            messagebox.showwarning("提示", "未能识别到姓名，请检查输入格式", parent=self.dialog)
            return
        
        self.parsed_data = data
        self.dialog.destroy()


def main():
    """主函数"""
    root = tk.Tk()
    app = SalaryTool(root)
    root.mainloop()


if __name__ == "__main__":
    main()
