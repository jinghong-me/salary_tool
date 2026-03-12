#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工资工具 - 飞书风格版 v2.1
使用 ttkbootstrap 实现飞书风格 UI

功能:
1. 维护员工花名册
2. 根据花名册生成三种格式的工资报表
3. 支持Excel/CSV导入导出
4. 身份证校验功能
5. 银行卡校验功能
6. 飞书风格现代化UI

安装依赖:
    pip install ttkbootstrap pandas openpyxl
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.style import Style
from ttkbootstrap.widgets import DateEntry, Meter
import pandas as pd
import os
from datetime import datetime
import re
import json
import sqlite3
import shutil

# 修复Python 3.12+的SQLite datetime适配器警告
try:
    from sqlite3 import register_adapter, register_converter
    import datetime as dt_module

    def adapt_datetime(val):
        return val.isoformat()

    def convert_datetime(val):
        return dt_module.datetime.fromisoformat(val.decode())

    register_adapter(dt_module.datetime, adapt_datetime)
    register_converter("TIMESTAMP", convert_datetime)
except:
    pass


# 版本信息
VERSION = "v2.2"
COPYRIGHT = "2026 惊鸿科技（济宁）有限公司"


class DatabaseManager:
    """SQLite数据库管理类"""

    def __init__(self, db_file="salary_tool.db"):
        self.db_file = db_file
        self.init_database()

    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        return conn

    def init_database(self):
        """初始化数据库表结构"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # 员工花名册表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                id_card TEXT UNIQUE,
                phone TEXT,
                bank_card TEXT,
                interbank_code TEXT,
                bank_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 历史记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time TEXT NOT NULL,
                company TEXT NOT NULL,
                period TEXT NOT NULL,
                count INTEGER,
                total_amount REAL,
                output_dir TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 个税计算数据表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tax_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                id_card TEXT,
                phone TEXT,
                gross_salary REAL,
                social_insurance REAL DEFAULT 0,
                special_deduction REAL DEFAULT 0,
                taxable_income REAL,
                tax_rate REAL,
                quick_deduction REAL,
                tax_amount REAL,
                net_salary REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 应用配置表（替代原来的JSON配置文件）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS app_config (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 企业配置表（替代company_config.json）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS company_config (
                company_name TEXT PRIMARY KEY,
                report_types TEXT,  -- JSON格式存储
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 员工删除记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS deleted_employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_id INTEGER,
                name TEXT NOT NULL,
                id_card TEXT,
                phone TEXT,
                bank_card TEXT,
                interbank_code TEXT,
                bank_name TEXT,
                deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                delete_reason TEXT
            )
        ''')

        # 员工添加记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS added_employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER,
                name TEXT NOT NULL,
                id_card TEXT,
                phone TEXT,
                bank_card TEXT,
                interbank_code TEXT,
                bank_name TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                add_method TEXT
            )
        ''')

        conn.commit()
        conn.close()

    # ==================== 员工花名册操作 ====================

    def get_all_employees(self):
        """获取所有员工"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, name, id_card, phone, bank_card, interbank_code, bank_name
            FROM employees ORDER BY id
        ''')
        rows = cursor.fetchall()
        conn.close()

        # 转换为DataFrame格式保持兼容
        if rows:
            data = [{
                'id': row['id'],
                '姓名': row['name'],
                '身份证号码': row['id_card'] or '',
                '手机号': row['phone'] or '',
                '银行卡号': row['bank_card'] or '',
                '联行号': row['interbank_code'] or '',
                '开户行': row['bank_name'] or ''
            } for row in rows]
            return pd.DataFrame(data)
        return pd.DataFrame(columns=['id', '姓名', '身份证号码', '手机号', '银行卡号', '联行号', '开户行'])

    def add_employee(self, name, id_card='', phone='', bank_card='', interbank_code='', bank_name='', method='手动添加'):
        """添加员工"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO employees (name, id_card, phone, bank_card, interbank_code, bank_name, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (name, id_card, phone, bank_card, interbank_code, bank_name, datetime.now()))
            conn.commit()
            new_id = cursor.lastrowid

            # 记录添加操作
            cursor.execute('''
                INSERT INTO added_employees (employee_id, name, id_card, phone, bank_card, interbank_code, bank_name, add_method)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (new_id, name, id_card, phone, bank_card, interbank_code, bank_name, method))
            conn.commit()

            conn.close()
            return True, new_id
        except sqlite3.IntegrityError as e:
            conn.close()
            return False, f"身份证号已存在: {e}"
        except Exception as e:
            conn.close()
            return False, str(e)

    def update_employee(self, employee_id, name, id_card='', phone='', bank_card='', interbank_code='', bank_name=''):
        """更新员工信息"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE employees SET
                    name = ?, id_card = ?, phone = ?, bank_card = ?,
                    interbank_code = ?, bank_name = ?, updated_at = ?
                WHERE id = ?
            ''', (name, id_card, phone, bank_card, interbank_code, bank_name, datetime.now(), employee_id))
            conn.commit()
            conn.close()
            return True, None
        except sqlite3.IntegrityError as e:
            conn.close()
            return False, f"身份证号已存在: {e}"
        except Exception as e:
            conn.close()
            return False, str(e)

    def delete_employee(self, employee_id):
        """删除员工"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM employees WHERE id = ?', (employee_id,))
        conn.commit()
        conn.close()
        return True

    def delete_employee_by_name_id(self, name, id_card=''):
        """根据姓名和身份证号删除员工（兼容旧版本）"""
        conn = self.get_connection()
        cursor = conn.cursor()
        if id_card:
            cursor.execute('DELETE FROM employees WHERE name = ? AND id_card = ?', (name, id_card))
        else:
            cursor.execute('DELETE FROM employees WHERE name = ?', (name,))
        conn.commit()
        conn.close()
        return True

    # ==================== 删除记录操作 ====================

    def record_deleted_employee(self, employee_data, reason=''):
        """记录删除的员工信息"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO deleted_employees (original_id, name, id_card, phone, bank_card, interbank_code, bank_name, delete_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            employee_data.get('id'),
            employee_data.get('姓名', ''),
            employee_data.get('身份证号码', ''),
            employee_data.get('手机号', ''),
            employee_data.get('银行卡号', ''),
            employee_data.get('联行号', ''),
            employee_data.get('开户行', ''),
            reason
        ))
        conn.commit()
        conn.close()

    def get_deleted_employees(self):
        """获取所有删除记录"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, original_id, name, id_card, phone, bank_card, interbank_code, bank_name, deleted_at, delete_reason
            FROM deleted_employees ORDER BY deleted_at DESC
        ''')
        rows = cursor.fetchall()
        conn.close()
        return [{
            'id': row['id'],
            'original_id': row['original_id'],
            '姓名': row['name'],
            '身份证号码': row['id_card'] or '',
            '手机号': row['phone'] or '',
            '银行卡号': row['bank_card'] or '',
            '联行号': row['interbank_code'] or '',
            '开户行': row['bank_name'] or '',
            '删除时间': row['deleted_at'],
            '删除原因': row['delete_reason'] or ''
        } for row in rows]

    def restore_employee(self, deleted_id):
        """恢复删除的员工"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # 获取删除记录
        cursor.execute('''
            SELECT original_id, name, id_card, phone, bank_card, interbank_code, bank_name
            FROM deleted_employees WHERE id = ?
        ''', (deleted_id,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return False, "删除记录不存在"

        # 检查是否已存在同名或同身份证的员工
        cursor.execute('SELECT id FROM employees WHERE name = ?', (row['name'],))
        existing = cursor.fetchone()
        if existing:
            conn.close()
            return False, f"员工 '{row['name']}' 已存在，无法恢复"

        if row['id_card']:
            cursor.execute('SELECT id FROM employees WHERE id_card = ?', (row['id_card'],))
            existing = cursor.fetchone()
            if existing:
                conn.close()
                return False, f"身份证号 '{row['id_card']}' 已存在，无法恢复"

        # 恢复员工
        try:
            cursor.execute('''
                INSERT INTO employees (name, id_card, phone, bank_card, interbank_code, bank_name, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (row['name'], row['id_card'], row['phone'], row['bank_card'],
                  row['interbank_code'], row['bank_name'], datetime.now()))

            # 删除删除记录
            cursor.execute('DELETE FROM deleted_employees WHERE id = ?', (deleted_id,))

            conn.commit()
            conn.close()
            return True, None
        except sqlite3.IntegrityError as e:
            conn.close()
            return False, str(e)

    def clear_deleted_employees(self):
        """清空所有删除记录"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM deleted_employees')
        conn.commit()
        conn.close()

    # ==================== 添加记录操作 ====================

    def record_added_employee(self, employee_data, method='手动添加'):
        """记录添加的员工信息"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO added_employees (employee_id, name, id_card, phone, bank_card, interbank_code, bank_name, add_method)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            employee_data.get('id'),
            employee_data.get('姓名', ''),
            employee_data.get('身份证号码', ''),
            employee_data.get('手机号', ''),
            employee_data.get('银行卡号', ''),
            employee_data.get('联行号', ''),
            employee_data.get('开户行', ''),
            method
        ))
        conn.commit()
        conn.close()

    def get_added_employees(self):
        """获取所有添加记录"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, employee_id, name, id_card, phone, bank_card, interbank_code, bank_name, added_at, add_method
            FROM added_employees ORDER BY added_at DESC
        ''')
        rows = cursor.fetchall()
        conn.close()
        return [{
            'id': row['id'],
            'employee_id': row['employee_id'],
            '姓名': row['name'],
            '身份证号码': row['id_card'] or '',
            '手机号': row['phone'] or '',
            '银行卡号': row['bank_card'] or '',
            '联行号': row['interbank_code'] or '',
            '开户行': row['bank_name'] or '',
            '添加时间': row['added_at'],
            '添加方式': row['add_method'] or ''
        } for row in rows]

    def clear_added_employees(self):
        """清空所有添加记录"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM added_employees')
        conn.commit()
        conn.close()

    def find_employee_by_id(self, employee_id):
        """根据ID查找员工"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, name, id_card, phone, bank_card, interbank_code, bank_name
            FROM employees WHERE id = ?
        ''', (employee_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                'id': row['id'],
                '姓名': row['name'],
                '身份证号码': row['id_card'] or '',
                '手机号': row['phone'] or '',
                '银行卡号': row['bank_card'] or '',
                '联行号': row['interbank_code'] or '',
                '开户行': row['bank_name'] or ''
            }
        return None

    def find_employee_by_name(self, name):
        """根据姓名查找员工"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, name, id_card, phone, bank_card, interbank_code, bank_name
            FROM employees WHERE name = ?
        ''', (name,))
        rows = cursor.fetchall()
        conn.close()
        return [{
            'id': row['id'],
            '姓名': row['name'],
            '身份证号码': row['id_card'] or '',
            '手机号': row['phone'] or '',
            '银行卡号': row['bank_card'] or '',
            '联行号': row['interbank_code'] or '',
            '开户行': row['bank_name'] or ''
        } for row in rows]

    def find_employee_by_id_card(self, id_card):
        """根据身份证号查找员工"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, name, id_card, phone, bank_card, interbank_code, bank_name
            FROM employees WHERE id_card = ?
        ''', (id_card,))
        rows = cursor.fetchall()
        conn.close()
        return [{
            'id': row['id'],
            '姓名': row['name'],
            '身份证号码': row['id_card'] or '',
            '手机号': row['phone'] or '',
            '银行卡号': row['bank_card'] or '',
            '联行号': row['interbank_code'] or '',
            '开户行': row['bank_name'] or ''
        } for row in rows]

    def import_employees_from_df(self, df):
        """从DataFrame批量导入员工"""
        conn = self.get_connection()
        cursor = conn.cursor()
        imported = 0
        updated = 0

        for _, row in df.iterrows():
            name = row.get('姓名', '')
            id_card = row.get('身份证号码', '')
            phone = row.get('手机号', '')
            bank_card = row.get('银行卡号', '')
            interbank_code = row.get('联行号', '')
            bank_name = row.get('开户行', '')

            if not name:
                continue

            # 检查是否已存在（根据身份证号）
            if id_card:
                cursor.execute('SELECT id FROM employees WHERE id_card = ?', (id_card,))
                existing = cursor.fetchone()
                if existing:
                    # 更新
                    cursor.execute('''
                        UPDATE employees SET
                            name = ?, phone = ?, bank_card = ?,
                            interbank_code = ?, bank_name = ?, updated_at = ?
                        WHERE id = ?
                    ''', (name, phone, bank_card, interbank_code, bank_name, datetime.now(), existing['id']))
                    updated += 1
                    continue

            # 检查是否已存在（根据姓名）
            cursor.execute('SELECT id FROM employees WHERE name = ?', (name,))
            existing = cursor.fetchone()
            if existing:
                # 更新
                cursor.execute('''
                    UPDATE employees SET
                        id_card = ?, phone = ?, bank_card = ?,
                        interbank_code = ?, bank_name = ?, updated_at = ?
                    WHERE id = ?
                ''', (id_card, phone, bank_card, interbank_code, bank_name, datetime.now(), existing['id']))
                updated += 1
            else:
                # 新增
                try:
                    cursor.execute('''
                        INSERT INTO employees (name, id_card, phone, bank_card, interbank_code, bank_name, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (name, id_card, phone, bank_card, interbank_code, bank_name, datetime.now()))
                    imported += 1
                except sqlite3.IntegrityError:
                    pass

        conn.commit()
        conn.close()
        return imported, updated

    # ==================== 历史记录操作 ====================

    def add_history(self, time_str, company, period, count, total_amount, output_dir):
        """添加历史记录"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO history (time, company, period, count, total_amount, output_dir)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (time_str, company, period, count, total_amount, output_dir))
        conn.commit()
        conn.close()

    def get_all_history(self):
        """获取所有历史记录"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT time, company, period, count, total_amount, output_dir
            FROM history ORDER BY created_at DESC
        ''')
        rows = cursor.fetchall()
        conn.close()
        return [{
            'time': row['time'],
            'company': row['company'],
            'period': row['period'],
            'count': row['count'],
            'total_amount': row['total_amount'],
            'output_dir': row['output_dir']
        } for row in rows]

    def clear_history(self):
        """清空历史记录"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM history')
        conn.commit()
        conn.close()

    # ==================== 个税数据操作 ====================

    def save_tax_data(self, tax_records):
        """保存个税计算数据"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # 先清空旧数据
        cursor.execute('DELETE FROM tax_data')

        # 插入新数据
        for record in tax_records:
            cursor.execute('''
                INSERT INTO tax_data (
                    name, id_card, phone, gross_salary, social_insurance,
                    special_deduction, taxable_income, tax_rate, quick_deduction,
                    tax_amount, net_salary
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                record.get('姓名', ''),
                record.get('身份证号码', ''),
                record.get('手机号', ''),
                record.get('税前工资', 0),
                record.get('社保公积金', 0),
                record.get('专项附加扣除', 0),
                record.get('应纳税所得额', 0),
                record.get('税率', 0),
                record.get('速算扣除数', 0),
                record.get('个税', 0),
                record.get('税后工资', 0)
            ))

        conn.commit()
        conn.close()

    def get_tax_data(self):
        """获取所有个税数据"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT name, id_card, phone, gross_salary, social_insurance,
                   special_deduction, taxable_income, tax_rate, quick_deduction,
                   tax_amount, net_salary
            FROM tax_data ORDER BY id
        ''')
        rows = cursor.fetchall()
        conn.close()
        return [{
            '姓名': row['name'],
            '身份证号码': row['id_card'] or '',
            '手机号': row['phone'] or '',
            '税前工资': row['gross_salary'],
            '社保公积金': row['social_insurance'],
            '专项附加扣除': row['special_deduction'],
            '应纳税所得额': row['taxable_income'],
            '税率': row['tax_rate'],
            '速算扣除数': row['quick_deduction'],
            '个税': row['tax_amount'],
            '税后工资': row['net_salary']
        } for row in rows]

    def clear_tax_data(self):
        """清空个税数据"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM tax_data')
        conn.commit()
        conn.close()

    # ==================== 企业配置操作 ====================

    def get_company_config(self):
        """获取所有企业配置"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT company_name, report_types FROM company_config')
        rows = cursor.fetchall()
        conn.close()

        config = {}
        for row in rows:
            try:
                report_types = json.loads(row['report_types']) if row['report_types'] else []
            except:
                report_types = []
            config[row['company_name']] = {'report_types': report_types}
        return config

    def save_company_config(self, company_name, report_types):
        """保存企业配置"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO company_config (company_name, report_types, updated_at)
            VALUES (?, ?, ?)
        ''', (company_name, json.dumps(report_types), datetime.now()))
        conn.commit()
        conn.close()

    def delete_company_config(self, company_name):
        """删除企业配置"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM company_config WHERE company_name = ?', (company_name,))
        conn.commit()
        conn.close()

    # ==================== 应用配置操作 ====================

    def get_app_config(self, key, default=None):
        """获取应用配置"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM app_config WHERE key = ?', (key,))
        row = cursor.fetchone()
        conn.close()
        if row:
            try:
                return json.loads(row['value'])
            except:
                return row['value']
        return default

    def set_app_config(self, key, value):
        """设置应用配置"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO app_config (key, value, updated_at)
            VALUES (?, ?, ?)
        ''', (key, json.dumps(value) if isinstance(value, (list, dict)) else str(value), datetime.now()))
        conn.commit()
        conn.close()

    # ==================== 备份和恢复 ====================

    def backup_database(self, backup_path):
        """备份数据库"""
        shutil.copy2(self.db_file, backup_path)

    def restore_database(self, backup_path):
        """恢复数据库"""
        shutil.copy2(backup_path, self.db_file)


class Validator:
    """数据校验类"""

    # 银行BIN号数据库
    BANK_BINS = {
        '102100': '中国工商银行', '103100': '中国农业银行',
        '104100': '中国银行', '105100': '中国建设银行',
        '301100': '交通银行', '302100': '中信银行',
        '303100': '中国光大银行', '304100': '华夏银行',
        '305100': '中国民生银行', '306100': '广发银行',
        '308100': '招商银行', '309100': '兴业银行',
        '310100': '上海浦东发展银行', '403100': '中国邮政储蓄银行',
        '621483': '招商银行', '621485': '招商银行',
        '621486': '招商银行', '622202': '中国工商银行',
        '622203': '中国工商银行', '622208': '中国工商银行',
        '622848': '中国农业银行', '622845': '中国农业银行',
        '621700': '中国建设银行', '621288': '中国工商银行',
        '623668': '中国建设银行', '621661': '中国银行',
        '622260': '交通银行', '622262': '交通银行',
        '621098': '中国邮政储蓄银行', '622150': '中国邮政储蓄银行',
        '621799': '中国邮政储蓄银行', '622200': '中国工商银行',
        '621226': '中国工商银行', '621558': '中国工商银行',
        '621559': '中国工商银行', '621723': '中国工商银行',
        '621618': '中国工商银行', '622841': '中国农业银行',
        '623052': '中国农业银行', '621725': '中国银行',
        '621756': '中国银行', '621785': '中国银行',
        '621786': '中国银行', '621787': '中国银行',
        '621788': '中国银行', '621789': '中国银行',
        '621790': '中国银行', '622760': '中国银行',
        '621669': '中国建设银行', '621673': '中国建设银行',
        '623094': '中国建设银行', '623211': '中国建设银行',
        '621284': '中国建设银行', '436742': '中国建设银行',
        '621081': '中国建设银行', '621466': '中国建设银行',
        '621467': '中国建设银行', '621488': '中国建设银行',
        '621499': '中国建设银行', '621598': '中国建设银行',
        '621621': '中国建设银行', '622280': '中国建设银行',
        '622700': '中国建设银行', '622707': '中国建设银行',
        '622966': '中国建设银行', '622988': '中国建设银行',
        '402658': '招商银行', '410062': '招商银行',
        '468203': '招商银行', '512425': '招商银行',
        '524011': '招商银行', '622588': '招商银行',
        '622609': '招商银行', '623126': '招商银行',
        '623136': '招商银行', '621020': '莱商银行',
        '621379': '莱商银行', '623531': '莱商银行',
    }

    @staticmethod
    def validate_id_card(id_card):
        """校验身份证号码"""
        if not id_card:
            return True, None, None

        id_card = str(id_card).strip().upper()

        if len(id_card) != 18:
            return False, "身份证号码必须为18位", None

        if not re.match(r'^\d{17}[\dX]$', id_card):
            return False, "身份证号码格式错误", None

        birth_str = id_card[6:14]
        try:
            birth_date = datetime.strptime(birth_str, '%Y%m%d')
            if birth_date > datetime.now():
                return False, "出生日期不能晚于今天", None
            if birth_date.year < 1900:
                return False, "出生日期年份过早", None
        except ValueError:
            return False, "出生日期无效", None

        weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
        check_codes = ['1', '0', 'X', '9', '8', '7', '6', '5', '4', '3', '2']

        sum_value = sum(int(id_card[i]) * weights[i] for i in range(17))
        expected_check = check_codes[sum_value % 11]

        if id_card[17] != expected_check:
            return False, f"校验码错误，应为 {expected_check}", None

        gender_code = int(id_card[16])
        gender = "男" if gender_code % 2 == 1 else "女"
        age = datetime.now().year - birth_date.year

        info = {
            'gender': gender,
            'birth_date': birth_date.strftime('%Y-%m-%d'),
            'age': age
        }

        return True, None, info

    @staticmethod
    def check_id_card_duplicates(roster_df):
        """检查身份证号码重复"""
        if roster_df is None or roster_df.empty:
            return []

        valid_df = roster_df[roster_df['身份证号码'].notna() & (roster_df['身份证号码'] != '')]
        grouped = valid_df.groupby('身份证号码')

        duplicates = []
        for id_card, group in grouped:
            if len(group) > 1:
                duplicates.append((id_card, group))

        return duplicates

    @staticmethod
    def validate_bank_card(card_no):
        """校验银行卡号"""
        if not card_no:
            return True, None, None

        card_no = str(card_no).strip().replace(' ', '').replace('-', '')

        if len(card_no) < 13 or len(card_no) > 19:
            return False, f"银行卡号长度错误（当前{len(card_no)}位）", None

        if not card_no.isdigit():
            return False, "银行卡号必须为数字", None

        if not Validator.luhn_check(card_no):
            return False, "银行卡号校验失败", None

        bank_info = Validator.identify_bank(card_no)
        return True, None, bank_info

    @staticmethod
    def luhn_check(card_no):
        """Luhn算法校验"""
        digits = [int(d) for d in card_no]
        odd_digits = digits[-1::-2]
        even_digits = digits[-2::-2]

        total = sum(odd_digits)
        for d in even_digits:
            d *= 2
            if d > 9:
                d -= 9
            total += d

        return total % 10 == 0

    @staticmethod
    def identify_bank(card_no):
        """识别发卡银行"""
        bin6 = card_no[:6]
        if bin6 in Validator.BANK_BINS:
            return {
                'bank_name': Validator.BANK_BINS[bin6],
                'bin': bin6,
                'card_type': '借记卡'
            }

        bin3 = card_no[:3]
        for bin_code, bank_name in Validator.BANK_BINS.items():
            if bin_code.startswith(bin3):
                return {
                    'bank_name': bank_name,
                    'bin': bin_code,
                    'card_type': '借记卡'
                }

        return {'bank_name': '未知银行', 'bin': bin6, 'card_type': '未知'}

    @staticmethod
    def validate_interbank_code(code):
        """校验联行号"""
        if not code:
            return True, None

        code = str(code).strip()
        if len(code) != 12:
            return False, f"联行号必须为12位"
        if not code.isdigit():
            return False, "联行号必须为数字"
        return True, None

    @staticmethod
    def validate_phone(phone):
        """校验手机号"""
        if not phone:
            return True, None

        phone = str(phone).strip()
        if len(phone) != 11:
            return False, f"手机号必须为11位"
        if not phone.isdigit():
            return False, "手机号必须为数字"
        if not phone.startswith('1'):
            return False, "手机号必须以1开头"
        return True, None


class SalaryTool:
    """工资工具主类"""

    def __init__(self, root):
        self.root = root
        self.root.title(f"工资报表生成工具 {VERSION}")
        self.root.geometry("1600x1000")
        self.root.minsize(1500, 900)

        # 初始化数据库
        self.db = DatabaseManager("salary_tool.db")

        # 数据文件路径（保留Excel路径用于导入导出）
        self.roster_file = "员工花名册.xlsx"
        self.config_file = "salary_tool_config.json"  # 兼容旧版本
        self.company_config_file = "company_config.json"  # 兼容旧版本

        # 内存中的数据（从数据库加载）
        self.roster_df = None
        self.history = []
        self.company_config = {}
        self.tax_data = []  # 个税计算数据

        # 加载配置
        self.load_config()
        self.load_company_config()

        # 加载花名册
        self.load_roster()

        # 创建界面
        self.create_widgets()

        # 更新公司名称下拉框（在界面创建后）
        self.update_company_combo()

    def load_config(self):
        """加载配置（从数据库）"""
        self.default_company = self.db.get_app_config('default_company', '惊鸿科技(济宁)有限公司')
        self.history = self.db.get_app_config('history', [])

    def save_config(self):
        """保存配置（到数据库）"""
        try:
            self.db.set_app_config('default_company', self.company_var.get())
            self.db.set_app_config('history', self.history[-10:])
        except:
            pass

    def load_company_config(self):
        """加载企业报表配置（从数据库）"""
        self.company_config = self.db.get_company_config()

    def update_company_combo(self):
        """更新公司名称列表"""
        # 获取企业列表
        company_list = list(self.company_config.keys()) if self.company_config else []

        # 如果没有企业，添加默认企业
        if not company_list:
            company_list = ['惊鸿科技(济宁)有限公司']

        # 保存完整列表用于搜索
        self.all_companies = company_list

        # 设置当前值
        if self.default_company in company_list:
            self.company_var.set(self.default_company)
            if hasattr(self, 'selected_company_label'):
                self.selected_company_label.config(text=self.default_company)
        else:
            self.company_var.set(company_list[0])
            if hasattr(self, 'selected_company_label'):
                self.selected_company_label.config(text=company_list[0])

        # 刷新公司列表显示
        self.refresh_company_select_list()

    def refresh_company_select_list(self, filter_text=''):
        """刷新公司选择列表"""
        if not hasattr(self, 'company_select_tree'):
            return

        # 清空列表
        for item in self.company_select_tree.get_children():
            self.company_select_tree.delete(item)

        # 过滤并显示企业
        filter_text = filter_text.lower()
        for company in self.all_companies:
            if not filter_text or filter_text in company.lower():
                self.company_select_tree.insert('', 'end', values=(company,))

    def filter_company_list(self, event):
        """筛选公司列表"""
        filter_text = self.company_filter_var.get()
        self.refresh_company_select_list(filter_text)

    def on_company_select_from_list(self, event):
        """从列表双击选择公司"""
        self.select_company_from_list()

    def on_company_single_select(self, event):
        """单击选择公司（延迟执行，避免与双击冲突）"""
        self.root.after(150, self.select_company_from_list)

    def select_company_from_list(self):
        """从列表中选择公司"""
        selected = self.company_select_tree.selection()
        if not selected:
            return

        values = self.company_select_tree.item(selected[0])['values']
        company_name = values[0]

        # 更新选中的公司
        self.company_var.set(company_name)
        self.selected_company_label.config(text=company_name)

        # 高亮显示选中的行
        for item in self.company_select_tree.get_children():
            self.company_select_tree.item(item, tags=())
        self.company_select_tree.item(selected[0], tags=('selected',))
        self.company_select_tree.tag_configure('selected', background='#e8f4f8')

    def save_company_config(self):
        """保存企业报表配置（到数据库）"""
        # 单个企业配置在添加/编辑时已保存到数据库
        pass

    def get_company_report_types(self, company_name):
        """获取企业配置的报表类型"""
        if company_name in self.company_config:
            return self.company_config[company_name].get('report_types', ['tax', 'laishang', 'agricultural_benhang', 'agricultural_kuahang'])
        # 默认生成所有报表
        return ['tax', 'laishang', 'jining', 'agricultural_benhang', 'agricultural_kuahang']

    def load_roster(self):
        """加载员工花名册（从数据库）"""
        self.roster_df = self.db.get_all_employees()

    def create_empty_roster(self):
        """创建空的花名册"""
        return pd.DataFrame(columns=['id', '姓名', '身份证号码', '手机号', '银行卡号', '联行号', '开户行'])

    def save_roster(self):
        """保存员工花名册（数据库自动保存，此方法保留用于兼容）"""
        pass

    def create_widgets(self):
        """创建界面组件"""
        # 创建主容器
        main_container = ttk.Frame(self.root, padding=10)
        main_container.pack(fill=BOTH, expand=YES)

        # 顶部标题栏
        self.create_header(main_container)

        # 创建Notebook(标签页)
        self.notebook = ttk.Notebook(main_container, bootstyle="primary")
        self.notebook.pack(fill=BOTH, expand=YES, pady=10)

        # 标签页1:报表生成
        self.frame_generate = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.frame_generate, text=" 报表生成 ")
        self.create_generate_tab()

        # 标签页2:生成记录
        self.frame_history = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.frame_history, text=" 生成记录 ")
        self.create_history_tab()

        # 标签页3:员工花名册
        self.frame_roster = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.frame_roster, text=" 员工花名册 ")
        self.create_roster_tab()

        # 标签页4:增删记录
        self.frame_deleted = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.frame_deleted, text=" 增删记录 ")
        self.create_deleted_tab()

        # 标签页5:数据校验
        self.frame_validate = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.frame_validate, text=" 数据校验 ")
        self.create_validate_tab()

        # 标签页6:企业管理
        self.frame_company = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.frame_company, text=" 企业管理 ")
        self.create_company_tab()

        # 标签页7:联行号查询
        self.frame_bankcode = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.frame_bankcode, text=" 联行号查询 ")
        self.create_bankcode_tab()

        # 标签页8:个税工具
        self.frame_tax = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.frame_tax, text=" 个税工具 ")
        self.create_tax_tab()

        # 标签页9:备份恢复
        self.frame_backup = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.frame_backup, text=" 备份恢复 ")
        self.create_backup_tab()

        # 底部状态栏
        self.create_status_bar(main_container)

    def create_header(self, parent):
        """创建顶部标题栏"""
        header = ttk.Frame(parent, bootstyle="primary")
        header.pack(fill=X, pady=(0, 10))

        # 标题
        title_frame = ttk.Frame(header, padding=10)
        title_frame.pack(fill=X)

        title = ttk.Label(
            title_frame,
            text="💰 工资报表生成工具",
            font=('Microsoft YaHei', 22, 'bold'),
            bootstyle="inverse-primary"
        )
        title.pack(side=LEFT)

        # 版本标签
        version_label = ttk.Label(
            title_frame,
            text=VERSION,
            font=('Microsoft YaHei', 12),
            bootstyle="inverse-success"
        )
        version_label.pack(side=LEFT, padx=(12, 0))

        # 版权信息
        copyright_label = ttk.Label(
            title_frame,
            text=COPYRIGHT,
            font=('Microsoft YaHei', 11),
            bootstyle="inverse-primary"
        )
        copyright_label.pack(side=RIGHT)

    def create_generate_tab(self):
        """创建生成报表标签页"""
        # 主容器 - 左右两栏
        main_frame = ttk.Frame(self.frame_generate)
        main_frame.pack(fill=BOTH, expand=YES)

        # 左侧 - 工资数据输入区域
        left_panel = ttk.Frame(main_frame)
        left_panel.pack(side=LEFT, fill=BOTH, expand=YES, padx=(0, 10))

        # 输入区域卡片
        input_card = ttk.Labelframe(left_panel, text="📝 工资数据输入", padding=15)
        input_card.pack(fill=BOTH, expand=YES)

        # 说明标签
        ttk.Label(
            input_card,
            text="格式: 姓名 工资金额 (支持从Excel直接粘贴)",
            font=('Microsoft YaHei', 11),
            bootstyle="secondary"
        ).pack(anchor=W, pady=(0, 8))

        # 文本输入框
        self.salary_input = tk.Text(input_card, height=15, font=('Consolas', 12))
        self.salary_input.pack(fill=BOTH, expand=YES)
        self.salary_input.insert("1.0", "# 示例格式:\n# 张三 5000\n# 李四 6000\n# 王五 7000\n\n# 请在上面输入姓名和工资金额，用空格或制表符分隔\n# 也可以直接从Excel复制粘贴")

        # 快捷操作按钮（放在输入框下方）
        quick_btn_frame = ttk.Frame(input_card)
        quick_btn_frame.pack(fill=X, pady=(10, 0))

        ttk.Button(
            quick_btn_frame,
            text="📁 导入Excel/CSV",
            command=self.import_salary_data,
            bootstyle="info-outline",
            width=18
        ).pack(side=LEFT, padx=(0, 5))

        ttk.Button(
            quick_btn_frame,
            text="📋 粘贴Excel数据",
            command=self.paste_excel_data,
            bootstyle="info-outline",
            width=18
        ).pack(side=LEFT, padx=5)

        ttk.Button(
            quick_btn_frame,
            text="🗑️ 清空",
            command=self.clear_input,
            bootstyle="secondary-outline",
            width=12
        ).pack(side=LEFT, padx=5)

        # 统计信息
        self.input_stats = ttk.Label(
            input_card,
            text="已输入: 0 人",
            font=('Microsoft YaHei', 12),
            bootstyle="secondary"
        )
        self.input_stats.pack(anchor=W, pady=(10, 0))

        # 绑定输入统计
        self.salary_input.bind('<KeyRelease>', self.update_input_stats)

        # 右侧 - 设置和按钮区域
        right_panel = ttk.Frame(main_frame, width=380)
        right_panel.pack(side=RIGHT, fill=Y, padx=(10, 0))
        right_panel.pack_propagate(False)

        # 设置卡片
        settings_card = ttk.Labelframe(right_panel, text="⚙️ 报表设置", padding=10)
        settings_card.pack(fill=X, pady=(0, 10))

        # 公司名称 - 从企业管理中选择（表格方式）
        ttk.Label(settings_card, text="公司名称:", font=('Microsoft YaHei', 11)).pack(anchor=W)
        self.company_var = ttk.StringVar(value=self.default_company)

        # 显示当前选中的公司
        self.selected_company_label = ttk.Label(
            settings_card,
            text=self.default_company,
            font=('Microsoft YaHei', 11, 'bold'),
            bootstyle="primary"
        )
        self.selected_company_label.pack(anchor=W, pady=(3, 8))

        # 搜索框
        search_frame = ttk.Frame(settings_card)
        search_frame.pack(fill=X, pady=(0, 3))

        ttk.Label(search_frame, text="🔍", font=('Microsoft YaHei', 10)).pack(side=LEFT)
        self.company_filter_var = ttk.StringVar()
        self.company_filter_entry = ttk.Entry(
            search_frame,
            textvariable=self.company_filter_var,
            font=('Microsoft YaHei', 10),
            width=20
        )
        self.company_filter_entry.pack(side=LEFT, fill=X, expand=YES, padx=(3, 0))
        self.company_filter_entry.bind('<KeyRelease>', self.filter_company_list)

        # 公司列表表格
        company_list_frame = ttk.Frame(settings_card)
        company_list_frame.pack(fill=X, pady=(0, 8))

        # 创建Treeview显示公司列表
        self.company_select_tree = ttk.Treeview(
            company_list_frame,
            columns=('company_name',),
            show='headings',
            height=6,
            bootstyle="primary"
        )
        self.company_select_tree.heading('company_name', text='企业名称')
        self.company_select_tree.column('company_name', width=260, anchor='w')

        vsb = ttk.Scrollbar(company_list_frame, orient="vertical", command=self.company_select_tree.yview)
        self.company_select_tree.configure(yscrollcommand=vsb.set)

        self.company_select_tree.pack(side=LEFT, fill=BOTH, expand=YES)
        vsb.pack(side=RIGHT, fill=Y)

        # 双击选择公司
        self.company_select_tree.bind('<Double-1>', self.on_company_select_from_list)
        # 单击也选择
        self.company_select_tree.bind('<<TreeviewSelect>>', self.on_company_single_select)

        # 发薪月份
        ttk.Label(settings_card, text="发薪月份:", font=('Microsoft YaHei', 11)).pack(anchor=W)

        month_frame = ttk.Frame(settings_card)
        month_frame.pack(fill=X, pady=(5, 0))

        now = datetime.now()
        if now.month == 1:
            last_month = 12
            last_year = now.year - 1
        else:
            last_month = now.month - 1
            last_year = now.year

        self.year_var = ttk.StringVar(value=str(last_year))
        year_combo = ttk.Combobox(month_frame, textvariable=self.year_var, values=[str(y) for y in range(2020, 2030)], width=8, state='readonly')
        year_combo.pack(side=LEFT)
        ttk.Label(month_frame, text="年").pack(side=LEFT, padx=5)

        self.month_var = ttk.StringVar(value=str(last_month))
        month_combo = ttk.Combobox(month_frame, textvariable=self.month_var, values=[str(m) for m in range(1, 13)], width=6, state='readonly')
        month_combo.pack(side=LEFT, padx=(10, 0))
        ttk.Label(month_frame, text="月").pack(side=LEFT, padx=5)

        # 操作卡片
        action_card = ttk.Labelframe(right_panel, text="🚀 操作", padding=10)
        action_card.pack(fill=X, pady=(0, 10))

        ttk.Button(
            action_card,
            text="👁️ 预览数据",
            command=self.preview_data,
            bootstyle="warning-outline",
            width=15
        ).pack(fill=X, pady=3)

        ttk.Button(
            action_card,
            text="✅ 生成报表",
            command=self.generate_reports,
            bootstyle="success",
            width=15
        ).pack(fill=X, pady=(3, 0))

    def create_roster_tab(self):
        """创建维护花名册标签页"""
        # 顶部工具栏
        toolbar = ttk.Frame(self.frame_roster)
        toolbar.pack(fill=X, pady=(0, 10))

        # 搜索框
        search_frame = ttk.Frame(toolbar)
        search_frame.pack(side=LEFT)

        ttk.Label(search_frame, text="🔍 搜索:", font=('Microsoft YaHei', 12)).pack(side=LEFT)

        self.search_var = ttk.StringVar()
        self.search_var.trace_add('write', self.search_roster)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=35, font=('Microsoft YaHei', 11))
        search_entry.pack(side=LEFT, padx=12)

        # 按钮组
        btn_frame = ttk.Frame(toolbar)
        btn_frame.pack(side=RIGHT)

        ttk.Button(
            btn_frame,
            text="➕ 添加员工",
            command=self.add_employee,
            bootstyle="primary"
        ).pack(side=LEFT, padx=5)

        ttk.Button(
            btn_frame,
            text="📋 智能粘贴",
            command=self.smart_paste_employee,
            bootstyle="info"
        ).pack(side=LEFT, padx=5)

        ttk.Button(
            btn_frame,
            text="📥 批量导入",
            command=self.import_roster,
            bootstyle="info-outline"
        ).pack(side=LEFT, padx=5)

        ttk.Button(
            btn_frame,
            text="📤 导出花名册",
            command=self.export_roster,
            bootstyle="success-outline"
        ).pack(side=LEFT, padx=5)

        # 员工列表
        list_frame = ttk.Frame(self.frame_roster)
        list_frame.pack(fill=BOTH, expand=YES)

        # Treeview
        columns = ('姓名', '身份证号码', '手机号', '银行卡号', '联行号', '开户行')
        self.tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=25, bootstyle="primary")

        # 设置列宽和标题 - 增加宽度以适应更大的字体，使用 stretch 让列宽自适应
        col_widths = {'姓名': 120, '身份证号码': 240, '手机号': 160, '银行卡号': 260, '联行号': 160, '开户行': 400}
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=col_widths.get(col, 150), anchor='center', stretch=True)

        # 滚动条
        vsb = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(list_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')

        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        # 右键菜单
        self.tree.bind('<Button-3>', self.show_context_menu)
        self.tree.bind('<Double-1>', lambda e: self.edit_employee())

        # 统计信息
        self.roster_info = ttk.Label(
            self.frame_roster,
            text=f"共 {len(self.roster_df)} 名员工",
            font=('Microsoft YaHei', 13),
            bootstyle="secondary"
        )
        self.roster_info.pack(anchor=W, pady=(12, 0))

        # 刷新列表
        self.refresh_roster_list()

    def create_validate_tab(self):
        """创建数据校验标签页"""
        # 工具栏
        toolbar = ttk.Frame(self.frame_validate)
        toolbar.pack(fill=X, pady=(0, 10))

        ttk.Label(toolbar, text="🔍 数据校验工具", font=('Microsoft YaHei', 16, 'bold')).pack(side=LEFT)

        ttk.Button(
            toolbar,
            text="🔄 开始校验",
            command=self.run_validation,
            bootstyle="primary"
        ).pack(side=RIGHT, padx=5)

        ttk.Button(
            toolbar,
            text="📋 复制结果",
            command=self.copy_validation_result,
            bootstyle="outline"
        ).pack(side=RIGHT, padx=5)

        # 结果显示区域
        result_frame = ttk.Frame(self.frame_validate)
        result_frame.pack(fill=BOTH, expand=YES)

        self.validate_result = tk.Text(result_frame, wrap='word', padx=12, pady=12, font=('Microsoft YaHei', 12))
        self.validate_result.pack(side=LEFT, fill=BOTH, expand=YES)

        scrollbar = ttk.Scrollbar(result_frame, orient="vertical", command=self.validate_result.yview)
        scrollbar.pack(side=RIGHT, fill=Y)
        self.validate_result.configure(yscrollcommand=scrollbar.set)

        # 初始化显示提示
        self.show_validation_guide()

    def show_validation_guide(self):
        """显示校验指南"""
        guide = """# 数据校验工具使用说明

点击右上角「🔄 开始校验」按钮，系统将自动检查以下内容：

## 📋 校验项目

### 1. 身份证号码校验
- ✅ 格式校验（18位，数字+X结尾）
- ✅ 地区码有效性
- ✅ 出生日期有效性
- ✅ 校验码验证
- ✅ 重复检测（同一身份证多人使用）

### 2. 银行卡号校验
- ✅ 长度校验（13-19位）
- ✅ Luhn算法校验
- ✅ 发卡银行识别
- ✅ 卡号格式检查

### 3. 其他信息校验
- ✅ 手机号格式（11位）
- ✅ 联行号格式（12位数字）
- ✅ 必填项检查

## 🏷️ 结果标识

- 🟢 正常 - 数据校验通过
- 🟡 警告 - 数据存在问题但可继续使用
- 🔴 错误 - 数据严重错误，建议立即修正
"""
        self.validate_result.delete('1.0', 'end')
        self.validate_result.insert('1.0', guide)

    def run_validation(self):
        """运行数据校验"""
        if self.roster_df is None or self.roster_df.empty:
            messagebox.showwarning("提示", "员工花名册为空，请先添加员工")
            return

        results = []
        results.append("# 🔍 数据校验结果")
        results.append(f"\n校验时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        results.append(f"员工总数: {len(self.roster_df)} 人\n")
        results.append("=" * 60)

        total_errors = 0
        total_warnings = 0

        # 1. 身份证校验
        results.append("\n## 📋 一、身份证号码校验\n")
        id_card_issues = []
        for idx, row in self.roster_df.iterrows():
            name = row.get('姓名', '')
            id_card = row.get('身份证号码', '')
            if id_card:
                is_valid, error_msg, info = Validator.validate_id_card(id_card)
                if not is_valid:
                    id_card_issues.append({'name': name, 'id_card': id_card, 'error': error_msg})
                    total_errors += 1

        if id_card_issues:
            results.append(f"🔴 发现 {len(id_card_issues)} 条身份证错误:\n")
            for issue in id_card_issues:
                results.append(f"  • {issue['name']}: {issue['id_card']}")
                results.append(f"    错误: {issue['error']}\n")
        else:
            results.append("🟢 所有身份证号码格式正确\n")

        # 2. 身份证重复检测
        results.append("\n## 🔍 二、身份证重复检测\n")
        duplicates = Validator.check_id_card_duplicates(self.roster_df)
        if duplicates:
            results.append(f"🔴 发现 {len(duplicates)} 组重复身份证:\n")
            for id_card, group in duplicates:
                names = group['姓名'].tolist()
                results.append(f"\n  身份证: {id_card}")
                results.append(f"  涉及员工: {', '.join(names)}")
                if len(set(names)) == 1:
                    results.append(f"  ⚠️ 状态: 同一员工多条记录（建议合并）")
                else:
                    results.append(f"  🔴 状态: 不同员工使用同一身份证（严重错误！）")
                    total_errors += 1
                results.append("")
        else:
            results.append("🟢 未发现身份证重复\n")

        # 3. 银行卡校验
        results.append("\n## 💳 三、银行卡号校验\n")
        bank_card_issues = []
        bank_card_ok = []
        for idx, row in self.roster_df.iterrows():
            name = row.get('姓名', '')
            bank_card = row.get('银行卡号', '')
            if bank_card:
                is_valid, error_msg, bank_info = Validator.validate_bank_card(bank_card)
                if not is_valid:
                    bank_card_issues.append({'name': name, 'bank_card': bank_card, 'error': error_msg})
                    total_warnings += 1
                else:
                    bank_card_ok.append({'name': name, 'bank_card': bank_card, 'bank_info': bank_info})

        if bank_card_issues:
            results.append(f"🟡 发现 {len(bank_card_issues)} 条银行卡警告:\n")
            for issue in bank_card_issues:
                results.append(f"  • {issue['name']}: {issue['bank_card']}")
                results.append(f"    警告: {issue['error']}\n")

        if bank_card_ok:
            results.append(f"\n🟢 成功识别 {len(bank_card_ok)} 张银行卡:\n")
            for item in bank_card_ok[:20]:
                bank_name = item['bank_info']['bank_name'] if item['bank_info'] else '未知'
                results.append(f"  • {item['name']}: {bank_name}")
            if len(bank_card_ok) > 20:
                results.append(f"  ... 还有 {len(bank_card_ok) - 20} 张")

        # 4. 手机号校验
        results.append("\n## 📱 四、手机号校验\n")
        phone_issues = []
        for idx, row in self.roster_df.iterrows():
            name = row.get('姓名', '')
            phone = row.get('手机号', '')
            if phone:
                is_valid, error_msg = Validator.validate_phone(phone)
                if not is_valid:
                    phone_issues.append({'name': name, 'phone': phone, 'error': error_msg})
                    total_warnings += 1

        if phone_issues:
            results.append(f"🟡 发现 {len(phone_issues)} 条手机号警告:\n")
            for issue in phone_issues:
                results.append(f"  • {issue['name']}: {issue['phone']}")
                results.append(f"    警告: {issue['error']}\n")
        else:
            results.append("🟢 所有手机号格式正确\n")

        # 5. 联行号校验
        results.append("\n## 🏦 五、联行号校验\n")
        interbank_issues = []
        for idx, row in self.roster_df.iterrows():
            name = row.get('姓名', '')
            interbank = row.get('联行号', '')
            if interbank:
                is_valid, error_msg = Validator.validate_interbank_code(interbank)
                if not is_valid:
                    interbank_issues.append({'name': name, 'interbank': interbank, 'error': error_msg})
                    total_warnings += 1

        if interbank_issues:
            results.append(f"🟡 发现 {len(interbank_issues)} 条联行号警告:\n")
            for issue in interbank_issues:
                results.append(f"  • {issue['name']}: {issue['interbank']}")
                results.append(f"    警告: {issue['error']}\n")
        else:
            results.append("🟢 所有联行号格式正确\n")

        # 6. 必填项检查
        results.append("\n## 📝 六、必填项检查\n")
        missing_required = []
        for idx, row in self.roster_df.iterrows():
            name = row.get('姓名', '')
            missing_fields = []
            if not row.get('银行卡号'):
                missing_fields.append('银行卡号')
            if not row.get('开户行'):
                missing_fields.append('开户行')
            if not row.get('手机号'):
                missing_fields.append('手机号')
            if missing_fields:
                missing_required.append({'name': name, 'fields': missing_fields})

        if missing_required:
            results.append(f"🟡 发现 {len(missing_required)} 人缺少必填项:\n")
            for item in missing_required:
                results.append(f"  • {item['name']}: 缺少 {', '.join(item['fields'])}")
        else:
            results.append("🟢 所有员工必填项完整\n")

        # 汇总
        results.append("\n" + "=" * 60)
        results.append("\n## 📊 校验汇总\n")
        results.append(f"🔴 错误: {total_errors} 项")
        results.append(f"🟡 警告: {total_warnings} 项")

        if total_errors == 0 and total_warnings == 0:
            results.append("\n✅ 恭喜！所有数据校验通过，数据质量良好。")
        elif total_errors == 0:
            results.append("\n⚠️ 数据基本正常，但存在一些警告，建议检查。")
        else:
            results.append("\n❌ 数据存在错误，建议立即修正后再使用。")

        # 显示结果
        self.validate_result.delete('1.0', 'end')
        self.validate_result.insert('1.0', '\n'.join(results))
        self.validation_result_text = '\n'.join(results)

    def copy_validation_result(self):
        """复制校验结果到剪贴板"""
        if hasattr(self, 'validation_result_text'):
            self.root.clipboard_clear()
            self.root.clipboard_append(self.validation_result_text)
            messagebox.showinfo("成功", "校验结果已复制到剪贴板")
        else:
            messagebox.showwarning("提示", "请先运行校验")

    def create_history_tab(self):
        """创建历史记录标签页"""
        # 工具栏
        toolbar = ttk.Frame(self.frame_history)
        toolbar.pack(fill=X, pady=(0, 10))

        ttk.Label(toolbar, text="📜 生成历史", font=('Microsoft YaHei', 16, 'bold')).pack(side=LEFT)

        ttk.Button(
            toolbar,
            text="🗑️ 清空历史",
            command=self.clear_history,
            bootstyle="danger"
        ).pack(side=RIGHT)

        # 历史列表
        list_frame = ttk.Frame(self.frame_history)
        list_frame.pack(fill=BOTH, expand=YES)

        columns = ('时间', '公司名称', '发薪月份', '人数', '总金额', '文件')
        self.history_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=25, bootstyle="primary")

        col_widths = {'时间': 180, '公司名称': 280, '发薪月份': 120, '人数': 100, '总金额': 140, '文件': 350}
        for col in columns:
            self.history_tree.heading(col, text=col)
            self.history_tree.column(col, width=col_widths.get(col, 100))

        vsb = ttk.Scrollbar(list_frame, orient="vertical", command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=vsb.set)

        self.history_tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')

        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        # 刷新历史
        self.refresh_history_list()

    def create_tax_tab(self):
        """创建个税工具标签页"""
        # 工具栏
        toolbar = ttk.Frame(self.frame_tax)
        toolbar.pack(fill=X, pady=(0, 10))

        ttk.Label(toolbar, text="💰 个税计算器", font=('Microsoft YaHei', 16, 'bold')).pack(side=LEFT)

        # 左侧 - 数据导入和计算
        left_panel = ttk.Frame(self.frame_tax)
        left_panel.pack(side=LEFT, fill=BOTH, expand=YES, padx=(0, 10))

        # 导入区域
        import_card = ttk.Labelframe(left_panel, text="📁 导入工资数据", padding=15)
        import_card.pack(fill=X, pady=(0, 10))

        ttk.Label(import_card, text="导入个税版式工资表（含姓名、身份证号、工资总额）", 
                 font=('Microsoft YaHei', 10)).pack(anchor=W, pady=(0, 10))

        btn_frame = ttk.Frame(import_card)
        btn_frame.pack(fill=X)

        ttk.Button(btn_frame, text="📥 导入Excel", command=self.import_tax_data, 
                  bootstyle="primary").pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="🧮 计算个税", command=self.calculate_tax, 
                  bootstyle="success").pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="🔄 反算个税", command=self.reverse_calculate_tax, 
                  bootstyle="info").pack(side=LEFT, padx=5)

        # 计算结果显示区域
        result_card = ttk.Labelframe(left_panel, text="📊 计算结果", padding=15)
        result_card.pack(fill=BOTH, expand=YES)

        # 结果显示表格
        columns = ('姓名', '身份证号码', '税前工资', '应纳税所得额', '税率', '速算扣除数', '个税', '税后工资')
        self.tax_tree = ttk.Treeview(result_card, columns=columns, show='headings', height=20, bootstyle="primary")

        col_widths = {'姓名': 100, '身份证号码': 180, '税前工资': 120, '应纳税所得额': 120, 
                     '税率': 80, '速算扣除数': 100, '个税': 100, '税后工资': 120}
        for col in columns:
            self.tax_tree.heading(col, text=col)
            self.tax_tree.column(col, width=col_widths.get(col, 100), anchor='center')

        vsb = ttk.Scrollbar(result_card, orient="vertical", command=self.tax_tree.yview)
        hsb = ttk.Scrollbar(result_card, orient="horizontal", command=self.tax_tree.xview)
        self.tax_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tax_tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')

        result_card.grid_rowconfigure(0, weight=1)
        result_card.grid_columnconfigure(0, weight=1)

        # 右侧 - 个税设置和统计
        right_panel = ttk.Frame(self.frame_tax, width=350)
        right_panel.pack(side=RIGHT, fill=Y, padx=(10, 0))
        right_panel.pack_propagate(False)

        # 个税设置
        settings_card = ttk.Labelframe(right_panel, text="⚙️ 个税计算设置", padding=15)
        settings_card.pack(fill=X, pady=(0, 10))

        ttk.Label(settings_card, text="起征点（元）:", font=('Microsoft YaHei', 11)).pack(anchor=W)
        self.tax_threshold = ttk.Entry(settings_card, font=('Microsoft YaHei', 11))
        self.tax_threshold.insert(0, "5000")
        self.tax_threshold.pack(fill=X, pady=(5, 10))

        ttk.Label(settings_card, text="社保公积金扣除（元）:", font=('Microsoft YaHei', 11)).pack(anchor=W)
        self.social_insurance = ttk.Entry(settings_card, font=('Microsoft YaHei', 11))
        self.social_insurance.insert(0, "0")
        self.social_insurance.pack(fill=X, pady=(5, 10))

        ttk.Label(settings_card, text="专项附加扣除（元）:", font=('Microsoft YaHei', 11)).pack(anchor=W)
        self.special_deduction = ttk.Entry(settings_card, font=('Microsoft YaHei', 11))
        self.special_deduction.insert(0, "0")
        self.special_deduction.pack(fill=X, pady=(5, 10))

        # 统计信息
        stats_card = ttk.Labelframe(right_panel, text="📈 统计信息", padding=15)
        stats_card.pack(fill=X, pady=(0, 10))

        self.tax_stats_label = ttk.Label(stats_card, text="暂无数据", font=('Microsoft YaHei', 11))
        self.tax_stats_label.pack(anchor=W, pady=5)

        # 操作按钮
        action_card = ttk.Labelframe(right_panel, text="🚀 操作", padding=15)
        action_card.pack(fill=X)

        ttk.Button(action_card, text="💾 导出结果", command=self.export_tax_result, 
                  bootstyle="success").pack(fill=X, pady=5)
        ttk.Button(action_card, text="🗑️ 清空数据", command=self.clear_tax_data, 
                  bootstyle="secondary").pack(fill=X, pady=5)

        # 存储导入的数据
        self.tax_data = []

    def create_status_bar(self, parent):
        """创建状态栏"""
        status_frame = ttk.Frame(parent, relief='solid', borderwidth=1)
        status_frame.pack(fill=X, pady=(10, 0))

        self.status_label = ttk.Label(
            status_frame,
            text="就绪",
            font=('Microsoft YaHei', 12),
            bootstyle="secondary"
        )
        self.status_label.pack(side=LEFT, padx=20, pady=10)

        self.roster_status = ttk.Label(
            status_frame,
            text=f"花名册: {len(self.roster_df)}人",
            font=('Microsoft YaHei', 12),
            bootstyle="secondary"
        )
        self.roster_status.pack(side=RIGHT, padx=20, pady=10)

    def update_input_stats(self, event=None):
        """更新输入统计"""
        text = self.salary_input.get("1.0", 'end').strip()
        lines = [l for l in text.split('\n') if l.strip() and not l.strip().startswith('#')]
        count = len(lines)
        self.input_stats.config(text=f"已输入: {count} 人")

    def import_salary_data(self):
        """导入工资数据"""
        file_path = filedialog.askopenfilename(
            title="选择工资数据文件",
            filetypes=[("Excel文件", "*.xlsx *.xls"), ("CSV文件", "*.csv"), ("所有文件", "*.*")]
        )
        if file_path:
            try:
                if file_path.endswith('.csv'):
                    df = pd.read_csv(file_path, dtype=str)
                else:
                    df = pd.read_excel(file_path, dtype=str)

                name_col = None
                salary_col = None

                for col in df.columns:
                    col_lower = col.lower()
                    if any(keyword in col_lower for keyword in ['姓名', '名字', 'name', '员工']):
                        name_col = col
                    if any(keyword in col_lower for keyword in ['工资', '金额', 'salary', 'money', '薪资']):
                        salary_col = col

                if name_col is None:
                    name_col = df.columns[0]
                if salary_col is None and len(df.columns) > 1:
                    salary_col = df.columns[1]

                lines = []
                for _, row in df.iterrows():
                    name = str(row.get(name_col, '')).strip()
                    salary = str(row.get(salary_col, '')).strip()
                    if name and salary:
                        lines.append(f"{name} {salary}")

                self.salary_input.delete("1.0", 'end')
                self.salary_input.insert("1.0", '\n'.join(lines))
                self.update_input_stats()

                messagebox.showinfo("成功", f"已导入 {len(lines)} 条工资数据")
                self.status_label.config(text=f"已导入: {file_path}")

            except Exception as e:
                messagebox.showerror("错误", f"导入失败: {e}")

    def paste_excel_data(self):
        """粘贴Excel数据"""
        try:
            clipboard = self.root.clipboard_get()
            if clipboard:
                self.salary_input.delete("1.0", 'end')
                self.salary_input.insert("1.0", clipboard)
                self.update_input_stats()
                messagebox.showinfo("成功", "已粘贴剪贴板数据")
        except:
            messagebox.showwarning("提示", "剪贴板中没有数据")

    def clear_input(self):
        """清空输入"""
        if messagebox.askyesno("确认", "确定要清空所有输入数据吗？"):
            self.salary_input.delete("1.0", 'end')
            self.update_input_stats()

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
                        if len(emp) > 1:
                            # 处理重名情况
                            dialog = DuplicateNameDialog(self.root, name, salary, emp)
                            if dialog.selected_employee is not None:
                                selected_idx = dialog.selected_employee
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

    def preview_data(self):
        """预览数据"""
        input_text = self.salary_input.get("1.0", 'end').strip()
        lines = [line.strip() for line in input_text.split('\n')
                if line.strip() and not line.strip().startswith('#')]

        if not lines:
            messagebox.showwarning("提示", "没有输入数据")
            return

        data, errors = self.parse_salary_data(lines)

        # 创建预览窗口
        preview_window = tk.Toplevel(self.root)
        preview_window.title("数据预览")
        preview_window.geometry("900x600")

        # 标题
        ttk.Label(preview_window, text="📊 数据预览", font=('Microsoft YaHei', 16, 'bold')).pack(pady=15)

        # 统计信息
        stats_frame = ttk.Labelframe(preview_window, text="统计信息", padding=10)
        stats_frame.pack(fill=X, padx=20, pady=5)

        ttk.Label(stats_frame, text=f"✅ 有效数据: {len(data)} 人    ❌ 错误: {len(errors)} 条",
                 font=('Microsoft YaHei', 12)).pack()

        # 内容区域
        content_frame = ttk.Frame(preview_window)
        content_frame.pack(fill=BOTH, expand=YES, padx=20, pady=10)

        # 有效数据
        if data:
            data_frame = ttk.Labelframe(content_frame, text="有效数据", padding=10)
            data_frame.pack(fill=BOTH, expand=YES, pady=(0, 10))

            tree = ttk.Treeview(data_frame, columns=('姓名', '工资', '银行卡号', '开户行'), show='headings', height=10)
            for col in ('姓名', '工资', '银行卡号', '开户行'):
                tree.heading(col, text=col)
                tree.column(col, width=150)

            for item in data:
                tree.insert('', 'end', values=(
                    item['姓名'],
                    f"{item['工资']:.2f}",
                    item.get('银行卡号', '未找到'),
                    item.get('开户行', '未找到')
                ))

            tree.pack(fill=BOTH, expand=YES)

        # 错误信息
        if errors:
            error_frame = ttk.Labelframe(content_frame, text="错误信息", padding=10)
            error_frame.pack(fill=X)

            error_text = tk.Text(error_frame, height=5, font=('Microsoft YaHei', 10))
            error_text.pack(fill=BOTH, expand=YES)

            for err in errors[:20]:
                error_text.insert('end', f"• {err}\n")
            if len(errors) > 20:
                error_text.insert('end', f"...还有 {len(errors)-20} 条错误\n")

            error_text.config(state='disabled')

        # 关闭按钮
        ttk.Button(preview_window, text="关闭", command=preview_window.destroy, bootstyle="primary").pack(pady=15)

    def generate_reports(self):
        """生成报表"""
        company_name = self.company_var.get().strip()
        if not company_name:
            messagebox.showwarning("提示", "请输入公司名称")
            return

        year = self.year_var.get()
        month = self.month_var.get()
        salary_period = f"{year}年{month}月"

        input_text = self.salary_input.get("1.0", 'end').strip()
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
                if not messagebox.askyesno("警告", f"存在 {len(errors)} 条错误，是否继续生成报表？\n\n错误信息:\n{error_msg}"):
                    return

        if not salary_data:
            messagebox.showwarning("提示", "没有有效数据")
            return

        date_str = datetime.now().strftime("%Y%m%d")

        # 创建导出目录
        output_dir = os.path.join(os.getcwd(), "导出报表", f"{company_name}-{salary_period}-{date_str}")
        os.makedirs(output_dir, exist_ok=True)

        # 生成报表
        try:
            self.status_label.config(text="正在生成报表...")
            self.root.update()

            # 获取企业配置的报表类型
            report_types = self.get_company_report_types(company_name)

            generated_files = []

            # 根据配置生成报表
            if 'tax' in report_types:
                generated_files.append(self.generate_tax_version(salary_data, company_name, salary_period, date_str, output_dir))

            if 'laishang' in report_types:
                generated_files.append(self.generate_laishang_version(salary_data, company_name, salary_period, date_str, output_dir))

            if 'jining' in report_types:
                generated_files.append(self.generate_jining_version(salary_data, company_name, salary_period, date_str, output_dir))

            if 'agricultural_benhang' in report_types or 'agricultural_kuahang' in report_types:
                agri_files = self.generate_agricultural_version(
                    salary_data, company_name, salary_period, date_str, output_dir,
                    generate_benhang='agricultural_benhang' in report_types,
                    generate_kuahang='agricultural_kuahang' in report_types
                )
                generated_files.extend(agri_files)

            # 添加历史记录
            files = f"导出报表/{company_name}-{salary_period}-{date_str}/"
            self.add_history(company_name, salary_period, len(salary_data),
                           sum(d['工资'] for d in salary_data), files)

            # 保存默认公司名
            self.save_config()

            # 获取企业配置信息用于显示
            report_types = self.get_company_report_types(company_name)
            config_info = ""
            if company_name in self.company_config:
                config_info = "\n⚙️ 使用自定义报表配置"

            success_msg = f"✅ 报表生成成功！\n\n"
            success_msg += f"📊 公司名称: {company_name}\n"
            success_msg += f"📅 发薪月份: {salary_period}\n"
            success_msg += f"📂 导出目录: {output_dir}"
            success_msg += config_info + "\n\n"
            success_msg += f"📁 生成文件 ({len(generated_files)} 个):\n"
            for f in generated_files:
                success_msg += f"  • {os.path.basename(f)}\n"
            success_msg += f"\n👥 共 {len(salary_data)} 人\n"
            success_msg += f"💰 总金额: {sum(d['工资'] for d in salary_data):.2f} 元"

            messagebox.showinfo("成功", success_msg)
            self.status_label.config(text=f"已生成报表: {company_name} {salary_period} ({len(salary_data)}人)")
            
            # 自动打开文件夹
            self.open_folder(output_dir)

        except Exception as e:
            messagebox.showerror("错误", f"生成报表失败: {e}")
            self.status_label.config(text="生成报表失败")

    def generate_tax_version(self, data, company_name, salary_period, date_str, output_dir):
        """生成个税版"""
        df = pd.DataFrame(data)
        df_output = pd.DataFrame({
            '姓名': df['姓名'],
            '身份证号码': df['身份证号码'],
            '手机号': df['手机号'],
            '工资总额': df['工资']
        })
        output_file = os.path.join(output_dir, f"{company_name}-{salary_period}-个税版式-{date_str}.xlsx")
        df_output.to_excel(output_file, index=False)
        return output_file

    def generate_laishang_version(self, data, company_name, salary_period, date_str, output_dir):
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

        output_file = os.path.join(output_dir, f"{company_name}-{salary_period}-莱商银行版式-{date_str}.txt")
        with open(output_file, 'w', encoding='gbk') as f:
            f.write('\n'.join(lines))
        return output_file

    def generate_jining_version(self, data, company_name, salary_period, date_str, output_dir):
        """生成济宁银行版（格式与莱商银行相同，区别是行内行外判断）"""
        lines = []
        lines.append(f"{len(data)}|{sum(d['工资'] for d in data):.2f}")
        lines.append("收款人账号|收款人名称|收款银行|收款账户开户行行号|行内行外(行外01,行内00)|转账金额|是否加急(普通0,加急1,实时2)|转账附言")

        for d in data:
            card = d['银行卡号']
            name = d['姓名']
            bank_name = d.get('开户行', '')
            interbank = d.get('联行号', '')
            interbank_clean = str(interbank).lstrip('0') if interbank else ''
            # 济宁银行版式：判断是否济宁银行
            inner_type = '00' if '济宁银行' in bank_name else '01'
            amount = f"{d['工资']:.2f}"

            lines.append(f"{card}|{name}|{bank_name}|{interbank_clean}|{inner_type}|{amount}|0|工资")

        output_file = os.path.join(output_dir, f"{company_name}-{salary_period}-济宁银行版式-{date_str}.txt")
        with open(output_file, 'w', encoding='gbk') as f:
            f.write('\n'.join(lines))
        return output_file

    def generate_agricultural_version(self, data, company_name, salary_period, date_str, output_dir, generate_benhang=True, generate_kuahang=True):
        """生成农业银行版

        参数:
            generate_benhang: 是否生成本行报表
            generate_kuahang: 是否生成跨行报表
        """
        benhang_lines = []
        kuahang_lines = []
        generated_files = []

        for d in data:
            card = d['银行卡号']
            name = d['姓名']
            bank_name = d.get('开户行', '')
            interbank = d.get('联行号', '')
            amount = f"{d['工资']:.2f}"

            if '农业银行' in bank_name:
                if generate_benhang:
                    benhang_lines.append((card, name, amount))
            else:
                if generate_kuahang:
                    bank_code = self.extract_bank_code(bank_name)
                    kuahang_lines.append((card, name, bank_code, interbank, bank_name, amount))

        if benhang_lines:
            benhang_file = os.path.join(output_dir, f"{company_name}-{salary_period}-农业银行本行-{date_str}.csv")
            with open(benhang_file, 'w', encoding='utf-8') as f:
                for i, (card, name, amount) in enumerate(benhang_lines, 1):
                    f.write(f"{i},{card},{name},{amount},工资\n")
            generated_files.append(benhang_file)

        if kuahang_lines:
            kuahang_file = os.path.join(output_dir, f"{company_name}-{salary_period}-农业银行跨行-{date_str}.csv")
            with open(kuahang_file, 'w', encoding='utf-8') as f:
                for i, (card, name, bank_code, interbank, bank_name, amount) in enumerate(kuahang_lines, 1):
                    f.write(f"{i},{card},{name},{bank_code},{interbank},{bank_name},{amount},工资\n")
            generated_files.append(kuahang_file)

        return generated_files

    def open_folder(self, folder_path):
        """自动打开文件夹"""
        try:
            if os.name == 'nt':  # Windows
                os.startfile(folder_path)
            elif os.name == 'posix':  # macOS 和 Linux
                import subprocess
                subprocess.call(['open', folder_path])
        except Exception as e:
            print(f"打开文件夹失败: {e}")

    def extract_bank_code(self, bank_name):
        """提取银行代码"""
        bank_mapping = [
            ('邮政', '中国邮政储蓄银行'), ('建设', '中国建设银行'),
            ('工商', '中国工商银行'), ('农业', '中国农业银行'),
            ('中国银行', '中国银行'), ('交通', '交通银行'),
            ('平安', '平安银行'), ('招商', '招商银行'),
            ('浦发', '浦发银行'), ('民生', '中国民生银行'),
            ('光大', '中国光大银行'), ('中信', '中信银行'),
            ('兴业', '兴业银行'), ('华夏', '华夏银行'),
        ]

        for keyword, code in bank_mapping:
            if keyword in bank_name:
                return code

        return bank_name[:10] if bank_name else ''

    def add_history(self, company, period, count, total, files):
        """添加历史记录（使用数据库）"""
        time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        output_dir = files[0] if files else ''

        # 保存到数据库
        self.db.add_history(time_str, company, period, count, total, output_dir)

        # 刷新内存中的历史记录
        self.history = self.db.get_all_history()
        self.refresh_history_list()

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

        for idx, row in df.iterrows():
            self.tree.insert('', 'end', iid=str(idx), values=(
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
        dialog = EmployeeDialog(self.root, self, "添加员工")

    def edit_employee(self):
        """编辑员工"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请选择要编辑的员工")
            return

        # 使用iid获取原始DataFrame索引
        iid = selected[0]
        try:
            idx = int(iid)
            if idx in self.roster_df.index:
                EmployeeDialog(self.root, self, "编辑员工", self.roster_df.loc[idx])
                return
        except (ValueError, IndexError):
            pass

        # 兼容旧版本：按姓名查找（可能找到多个）
        values = self.tree.item(selected[0])['values']
        name = values[0]
        id_card = values[1] if len(values) > 1 else ''

        # 优先使用身份证号精确定位
        if id_card:
            emp = self.roster_df[self.roster_df['身份证号码'] == id_card]
            if len(emp) > 0:
                EmployeeDialog(self.root, self, "编辑员工", emp.iloc[0])
                return

        # 最后按姓名查找
        emp = self.roster_df[self.roster_df['姓名'] == name]
        if len(emp) > 0:
            EmployeeDialog(self.root, self, "编辑员工", emp.iloc[0])

    def show_context_menu(self, event):
        """显示右键菜单"""
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="编辑", command=self.edit_employee)
        menu.add_command(label="删除", command=self.delete_employee)
        menu.post(event.x_root, event.y_root)

    def delete_employee(self):
        """删除员工（使用数据库，记录删除历史）"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请选择要删除的员工")
            return

        # 使用iid获取员工ID进行精确删除
        iid = selected[0]
        try:
            employee_id = int(iid)
            employee = self.db.find_employee_by_id(employee_id)
            if employee:
                name = employee['姓名']
                id_card = employee['身份证号码']
                id_card_display = id_card if id_card else ''

                if messagebox.askyesno("确认", f"确定要删除员工 '{name}' 吗？\n\n身份证号: {id_card_display}\n\n删除后可在删除记录中恢复"):
                    # 先记录删除信息
                    self.db.record_deleted_employee(employee, '用户手动删除')
                    # 再删除员工
                    self.db.delete_employee(employee_id)
                    self.load_roster()
                    self.refresh_roster_list()
                    messagebox.showinfo("成功", f"员工 '{name}' 已删除，可在删除记录中恢复")
                return
        except (ValueError, IndexError, KeyError):
            pass

        messagebox.showerror("错误", "无法删除员工，请重试")

    def smart_paste_employee(self):
        """智能粘贴员工信息（使用数据库）"""
        dialog = SmartPasteDialog(self.root, self)
        if dialog.parsed_data:
            data = dialog.parsed_data
            name = data['姓名']

            # 检查是否已存在
            existing = self.db.find_employee_by_name(name)
            is_update = len(existing) > 0

            if is_update:
                if not messagebox.askyesno("确认", f"员工 '{name}' 已存在，是否更新信息？"):
                    return
                # 更新第一个匹配的员工
                employee_id = existing[0]['id']
                self.db.update_employee(
                    employee_id,
                    name,
                    data['身份证号码'],
                    data['手机号'],
                    data['银行卡号'],
                    data['联行号'],
                    data['开户行']
                )
            else:
                # 添加新员工
                self.db.add_employee(
                    name,
                    data['身份证号码'],
                    data['手机号'],
                    data['银行卡号'],
                    data['联行号'],
                    data['开户行']
                )

            self.load_roster()
            self.refresh_roster_list()

            info = f"员工 '{name}' 已{'更新' if is_update else '添加'}\n\n"
            info += f"身份证: {data['身份证号码'] or '未填写'}\n"
            info += f"银行卡: {data['银行卡号'] or '未填写'}\n"
            info += f"开户行: {data['开户行'] or '未填写'}"
            messagebox.showinfo("成功", info)

    def import_roster(self):
        """批量导入花名册（使用数据库）"""
        file_path = filedialog.askopenfilename(
            title="选择花名册文件",
            filetypes=[("Excel文件", "*.xlsx *.xls"), ("CSV文件", "*.csv")]
        )
        if file_path:
            try:
                if file_path.endswith('.csv'):
                    df = pd.read_csv(file_path, dtype=str)
                else:
                    df = pd.read_excel(file_path, dtype=str)

                required_cols = ['姓名', '身份证号码', '手机号', '银行卡号', '联行号', '开户行']
                missing_cols = [col for col in required_cols if col not in df.columns]

                if missing_cols:
                    messagebox.showwarning("警告", f"缺少以下列: {', '.join(missing_cols)}\n\n现有列: {', '.join(df.columns)}")
                    return

                # 使用数据库导入
                imported, updated = self.db.import_employees_from_df(df)
                self.load_roster()
                self.refresh_roster_list()

                messagebox.showinfo("成功", f"导入完成！新增 {imported} 名员工，更新 {updated} 名员工")
                self.status_label.config(text=f"已导入花名册: {file_path}")

            except Exception as e:
                messagebox.showerror("错误", f"导入失败: {e}")

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

    # ==================== 个税工具方法 ====================
    
    def import_tax_data(self):
        """导入个税工资数据（使用数据库）"""
        file_path = filedialog.askopenfilename(
            title="选择个税版式工资表",
            filetypes=[("Excel文件", "*.xlsx *.xls"), ("CSV文件", "*.csv"), ("所有文件", "*.*")]
        )
        if not file_path:
            return

        try:
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path, dtype=str)
            else:
                df = pd.read_excel(file_path, dtype=str)

            # 查找工资列
            salary_col = None
            name_col = None
            id_col = None

            for col in df.columns:
                col_lower = col.lower()
                if any(keyword in col_lower for keyword in ['工资', '金额', 'salary', '总额']):
                    salary_col = col
                if any(keyword in col_lower for keyword in ['姓名', '名字', 'name']):
                    name_col = col
                if any(keyword in col_lower for keyword in ['身份证', 'id']):
                    id_col = col

            if not salary_col:
                # 默认使用第4列（索引3）作为工资
                if len(df.columns) >= 4:
                    salary_col = df.columns[3]
                else:
                    messagebox.showerror("错误", "无法识别工资列，请确保表格包含工资数据")
                    return

            if not name_col:
                name_col = df.columns[0]
            if not id_col and len(df.columns) > 1:
                id_col = df.columns[1]

            # 清空之前的数据
            self.tax_data = []

            for _, row in df.iterrows():
                try:
                    salary = float(str(row[salary_col]).replace(',', ''))
                    self.tax_data.append({
                        '姓名': str(row.get(name_col, '')),
                        '身份证号码': str(row.get(id_col, '')) if id_col else '',
                        '税前工资': salary,
                        '应纳税所得额': 0,
                        '税率': 0,
                        '速算扣除数': 0,
                        '个税': 0,
                        '税后工资': salary
                    })
                except (ValueError, TypeError):
                    continue

            # 保存到数据库
            self.db.save_tax_data(self.tax_data)

            # 显示导入的数据（未计算个税）
            self.refresh_tax_table()
            self.update_tax_stats()
            messagebox.showinfo("成功", f"已导入 {len(self.tax_data)} 条工资数据")

        except Exception as e:
            messagebox.showerror("错误", f"导入失败: {e}")
    
    def calculate_tax(self):
        """计算个税（正向计算）"""
        self.tax_data = self.db.get_tax_data()
        if not self.tax_data:
            messagebox.showwarning("提示", "请先导入工资数据")
            return

        try:
            threshold = float(self.tax_threshold.get() or 5000)
            social = float(self.social_insurance.get() or 0)
            special = float(self.special_deduction.get() or 0)
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")
            return

        calculator = TaxCalculator()
        for item in self.tax_data:
            taxable, rate, quick, tax, net = calculator.calculate_tax(
                item['税前工资'], threshold, social, special
            )
            item['应纳税所得额'] = round(taxable, 2)
            item['税率'] = f"{rate*100:.0f}%"
            item['速算扣除数'] = quick
            item['个税'] = round(tax, 2)
            item['税后工资'] = round(net, 2)

        # 保存计算结果到数据库
        self.db.save_tax_data(self.tax_data)

        self.refresh_tax_table()
        self.update_tax_stats()
        messagebox.showinfo("成功", "个税计算完成！")
    
    def reverse_calculate_tax(self):
        """反算个税（根据税后工资反推税前工资）"""
        self.tax_data = self.db.get_tax_data()
        if not self.tax_data:
            messagebox.showwarning("提示", "请先导入工资数据")
            return

        # 询问用户确认
        result = messagebox.askyesno(
            "确认反算",
            '反算个税将把当前"税前工资"视为"税后工资"来反推税前工资和个税。\n\n是否继续？'
        )
        if not result:
            return

        try:
            threshold = float(self.tax_threshold.get() or 5000)
            social = float(self.social_insurance.get() or 0)
            special = float(self.special_deduction.get() or 0)
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")
            return

        calculator = TaxCalculator()
        for item in self.tax_data:
            # 将当前税前工资视为税后工资进行反算
            gross, taxable, rate, quick, tax = calculator.reverse_calculate_tax(
                item['税前工资'], threshold, social, special
            )
            item['税前工资'] = round(gross, 2)
            item['应纳税所得额'] = round(taxable, 2)
            item['税率'] = f"{rate*100:.0f}%"
            item['速算扣除数'] = quick
            item['个税'] = round(tax, 2)
            item['税后工资'] = round(item['税前工资'] - tax - social, 2)

        # 保存计算结果到数据库
        self.db.save_tax_data(self.tax_data)

        self.refresh_tax_table()
        self.update_tax_stats()
        messagebox.showinfo("成功", "个税反算完成！")
    
    def refresh_tax_table(self):
        """刷新个税计算结果表格"""
        # 从数据库加载最新数据
        self.tax_data = self.db.get_tax_data()

        # 清空表格
        for item in self.tax_tree.get_children():
            self.tax_tree.delete(item)

        # 插入数据
        for item in self.tax_data:
            self.tax_tree.insert('', 'end', values=(
                item['姓名'],
                item['身份证号码'],
                f"{item['税前工资']:.2f}",
                f"{item['应纳税所得额']:.2f}",
                item['税率'],
                item['速算扣除数'],
                f"{item['个税']:.2f}",
                f"{item['税后工资']:.2f}"
            ))
    
    def update_tax_stats(self):
        """更新个税统计信息"""
        # 从数据库加载最新数据
        self.tax_data = self.db.get_tax_data()

        if not self.tax_data:
            self.tax_stats_label.config(text="暂无数据")
            return

        total_gross = sum(item['税前工资'] for item in self.tax_data)
        total_tax = sum(item['个税'] for item in self.tax_data)
        total_net = sum(item['税后工资'] for item in self.tax_data)

        stats_text = f"""📊 统计汇总:
👥 人数: {len(self.tax_data)} 人
💰 税前工资总额: {total_gross:,.2f} 元
🏦 个税总额: {total_tax:,.2f} 元
💵 税后工资总额: {total_net:,.2f} 元
📈 平均税率: {(total_tax/total_gross*100) if total_gross > 0 else 0:.2f}%"""

        self.tax_stats_label.config(text=stats_text)
    
    def export_tax_result(self):
        """导出个税计算结果"""
        if not self.tax_data:
            messagebox.showwarning("提示", "没有数据可导出")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel文件", "*.xlsx"), ("CSV文件", "*.csv")],
            initialfile=f"个税计算结果_{datetime.now().strftime('%Y%m%d')}.xlsx"
        )
        if not file_path:
            return
        
        try:
            df = pd.DataFrame(self.tax_data)
            if file_path.endswith('.csv'):
                df.to_csv(file_path, index=False, encoding='utf-8-sig')
            else:
                df.to_excel(file_path, index=False)
            messagebox.showinfo("成功", f"结果已导出到:\n{file_path}")
        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {e}")
    
    def clear_tax_data(self):
        """清空个税数据（使用数据库）"""
        self.tax_data = self.db.get_tax_data()
        if not self.tax_data:
            return

        result = messagebox.askyesno("确认", "确定要清空所有个税计算数据吗？")
        if result:
            self.db.clear_tax_data()
            self.tax_data = []
            self.refresh_tax_table()
            self.update_tax_stats()

    def create_company_tab(self):
        """创建企业管理标签页"""
        # 工具栏
        toolbar = ttk.Frame(self.frame_company)
        toolbar.pack(fill=X, pady=(0, 10))

        ttk.Label(toolbar, text="🏢 企业管理", font=('Microsoft YaHei', 16, 'bold')).pack(side=LEFT)

        btn_frame = ttk.Frame(toolbar)
        btn_frame.pack(side=RIGHT)

        ttk.Button(
            btn_frame,
            text="➕ 添加企业",
            command=self.add_company,
            bootstyle="primary"
        ).pack(side=LEFT, padx=5)

        ttk.Button(
            btn_frame,
            text="🗑️ 删除企业",
            command=self.delete_company,
            bootstyle="danger"
        ).pack(side=LEFT, padx=5)

        ttk.Button(
            btn_frame,
            text="📥 导入",
            command=self.import_company_config,
            bootstyle="info"
        ).pack(side=LEFT, padx=5)

        ttk.Button(
            btn_frame,
            text="📤 导出",
            command=self.export_company_config,
            bootstyle="info"
        ).pack(side=LEFT, padx=5)

        ttk.Button(
            btn_frame,
            text="📋 格式说明",
            command=self.show_company_format_help,
            bootstyle="secondary"
        ).pack(side=LEFT, padx=5)

        # 说明文字
        info_frame = ttk.Frame(self.frame_company)
        info_frame.pack(fill=X, pady=(0, 10))

        ttk.Label(
            info_frame,
            text="💡 提示：为每个企业配置需要生成的报表类型，生成报表时将自动跳过未选中的报表。支持导入导出企业配置。",
            font=('Microsoft YaHei', 11),
            bootstyle="secondary"
        ).pack(anchor=W)

        # 企业列表
        list_frame = ttk.Frame(self.frame_company)
        list_frame.pack(fill=BOTH, expand=YES)

        # 创建表格
        columns = ('企业名称', '个税版式', '莱商银行版式', '济宁银行版式', '农行本行版式', '农行跨行版式')
        self.company_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=20, bootstyle="primary")

        col_widths = {'企业名称': 350, '个税版式': 100, '莱商银行版式': 100, '济宁银行版式': 100, '农行本行版式': 100, '农行跨行版式': 100}
        for col in columns:
            self.company_tree.heading(col, text=col)
            self.company_tree.column(col, width=col_widths.get(col, 120), anchor='center')

        vsb = ttk.Scrollbar(list_frame, orient="vertical", command=self.company_tree.yview)
        hsb = ttk.Scrollbar(list_frame, orient="horizontal", command=self.company_tree.xview)
        self.company_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.company_tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')

        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        # 双击编辑
        self.company_tree.bind('<Double-1>', lambda e: self.edit_company())

        # 刷新列表
        self.refresh_company_list()

    def refresh_company_list(self):
        """刷新企业列表"""
        for item in self.company_tree.get_children():
            self.company_tree.delete(item)

        for company_name, config in self.company_config.items():
            report_types = config.get('report_types', [])
            self.company_tree.insert('', 'end', values=(
                company_name,
                '✓' if 'tax' in report_types else '✗',
                '✓' if 'laishang' in report_types else '✗',
                '✓' if 'jining' in report_types else '✗',
                '✓' if 'agricultural_benhang' in report_types else '✗',
                '✓' if 'agricultural_kuahang' in report_types else '✗'
            ))

    def add_company(self):
        """添加企业"""
        dialog = CompanyDialog(self.root, self, "添加企业")
        if dialog.result:
            self.load_company_config()
            self.refresh_company_list()
            # 刷新首页公司名称下拉框
            self.update_company_combo()

    def edit_company(self):
        """编辑企业"""
        selected = self.company_tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请选择要编辑的企业")
            return

        values = self.company_tree.item(selected[0])['values']
        company_name = values[0]

        if company_name in self.company_config:
            dialog = CompanyDialog(self.root, self, "编辑企业", company_name, self.company_config[company_name])
            if dialog.result:
                self.load_company_config()
                self.refresh_company_list()
                # 刷新首页公司名称下拉框
                self.update_company_combo()

    def delete_company(self):
        """删除企业（使用数据库）"""
        selected = self.company_tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请选择要删除的企业")
            return

        values = self.company_tree.item(selected[0])['values']
        company_name = values[0]

        if messagebox.askyesno("确认", f"确定要删除企业 '{company_name}' 吗？"):
            self.db.delete_company_config(company_name)
            self.load_company_config()
            self.refresh_company_list()
            # 刷新首页公司名称下拉框
            self.update_company_combo()
            messagebox.showinfo("成功", f"企业 '{company_name}' 已删除")

    def import_company_config(self):
        """导入企业配置"""
        file_path = filedialog.askopenfilename(
            title="选择企业配置文件",
            filetypes=[("JSON文件", "*.json"), ("Excel文件", "*.xlsx *.xls"), ("CSV文件", "*.csv"), ("所有文件", "*.*")]
        )
        if not file_path:
            return

        try:
            imported_count = 0
            updated_count = 0

            if file_path.endswith('.json'):
                # JSON格式导入
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                for company_name, config in data.items():
                    report_types = config.get('report_types', [])
                    if company_name in self.company_config:
                        updated_count += 1
                    else:
                        imported_count += 1
                    self.db.save_company_config(company_name, report_types)

            elif file_path.endswith('.csv'):
                # CSV格式导入
                df = pd.read_csv(file_path, dtype=str)
                required_cols = ['企业名称']
                if not all(col in df.columns for col in required_cols):
                    messagebox.showerror("错误", f"CSV文件缺少必要列: {required_cols}\n当前列: {list(df.columns)}")
                    return

                for _, row in df.iterrows():
                    company_name = row.get('企业名称', '').strip()
                    if not company_name:
                        continue

                    report_types = []
                    if row.get('个税版式', '').strip() in ['1', '是', 'TRUE', 'True', 'true', 'YES', 'Yes', 'yes']:
                        report_types.append('tax')
                    if row.get('莱商银行版式', '').strip() in ['1', '是', 'TRUE', 'True', 'true', 'YES', 'Yes', 'yes']:
                        report_types.append('laishang')
                    if row.get('济宁银行版式', '').strip() in ['1', '是', 'TRUE', 'True', 'true', 'YES', 'Yes', 'yes']:
                        report_types.append('jining')
                    if row.get('农行本行版式', '').strip() in ['1', '是', 'TRUE', 'True', 'true', 'YES', 'Yes', 'yes']:
                        report_types.append('agricultural_benhang')
                    if row.get('农行跨行版式', '').strip() in ['1', '是', 'TRUE', 'True', 'true', 'YES', 'Yes', 'yes']:
                        report_types.append('agricultural_kuahang')

                    if company_name in self.company_config:
                        updated_count += 1
                    else:
                        imported_count += 1
                    self.db.save_company_config(company_name, report_types)

            elif file_path.endswith(('.xlsx', '.xls')):
                # Excel格式导入
                df = pd.read_excel(file_path, dtype=str)
                required_cols = ['企业名称']
                if not all(col in df.columns for col in required_cols):
                    messagebox.showerror("错误", f"Excel文件缺少必要列: {required_cols}\n当前列: {list(df.columns)}")
                    return

                for _, row in df.iterrows():
                    company_name = row.get('企业名称', '').strip()
                    if not company_name:
                        continue

                    report_types = []
                    if row.get('个税版式', '').strip() in ['1', '是', 'TRUE', 'True', 'true', 'YES', 'Yes', 'yes']:
                        report_types.append('tax')
                    if row.get('莱商银行版式', '').strip() in ['1', '是', 'TRUE', 'True', 'true', 'YES', 'Yes', 'yes']:
                        report_types.append('laishang')
                    if row.get('济宁银行版式', '').strip() in ['1', '是', 'TRUE', 'True', 'true', 'YES', 'Yes', 'yes']:
                        report_types.append('jining')
                    if row.get('农行本行版式', '').strip() in ['1', '是', 'TRUE', 'True', 'true', 'YES', 'Yes', 'yes']:
                        report_types.append('agricultural_benhang')
                    if row.get('农行跨行版式', '').strip() in ['1', '是', 'TRUE', 'True', 'true', 'YES', 'Yes', 'yes']:
                        report_types.append('agricultural_kuahang')

                    if company_name in self.company_config:
                        updated_count += 1
                    else:
                        imported_count += 1
                    self.db.save_company_config(company_name, report_types)

            else:
                messagebox.showerror("错误", "不支持的文件格式，请使用 JSON、Excel 或 CSV 文件")
                return

            # 刷新数据
            self.load_company_config()
            self.refresh_company_list()
            self.update_company_combo()

            messagebox.showinfo("成功", f"导入完成！\n新增企业: {imported_count} 个\n更新企业: {updated_count} 个")

        except Exception as e:
            messagebox.showerror("错误", f"导入失败: {e}")

    def export_company_config(self):
        """导出企业配置"""
        if not self.company_config:
            messagebox.showwarning("提示", "没有企业配置可导出")
            return

        # 选择导出格式
        export_format = messagebox.askquestion("选择格式", "请选择导出格式:\n\n'是' - Excel格式 (.xlsx)\n'否' - JSON格式 (.json)")

        try:
            if export_format == 'yes':
                # Excel格式导出
                file_path = filedialog.asksaveasfilename(
                    defaultextension=".xlsx",
                    filetypes=[("Excel文件", "*.xlsx")],
                    initialfile=f"企业配置导出_{datetime.now().strftime('%Y%m%d')}.xlsx"
                )
                if not file_path:
                    return

                data = []
                for company_name, config in self.company_config.items():
                    report_types = config.get('report_types', [])
                    data.append({
                        '企业名称': company_name,
                        '个税版式': 1 if 'tax' in report_types else 0,
                        '莱商银行版式': 1 if 'laishang' in report_types else 0,
                        '济宁银行版式': 1 if 'jining' in report_types else 0,
                        '农行本行版式': 1 if 'agricultural_benhang' in report_types else 0,
                        '农行跨行版式': 1 if 'agricultural_kuahang' in report_types else 0
                    })

                df = pd.DataFrame(data)
                df.to_excel(file_path, index=False)

            else:
                # JSON格式导出
                file_path = filedialog.asksaveasfilename(
                    defaultextension=".json",
                    filetypes=[("JSON文件", "*.json")],
                    initialfile=f"企业配置导出_{datetime.now().strftime('%Y%m%d')}.json"
                )
                if not file_path:
                    return

                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.company_config, f, ensure_ascii=False, indent=2)

            messagebox.showinfo("成功", f"企业配置已导出到:\n{file_path}")

        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {e}")

    def show_company_format_help(self):
        """显示企业配置格式说明"""
        help_text = """📋 企业配置导入格式说明

支持三种格式导入：JSON、Excel、CSV

═══════════════════════════════════════

📄 一、JSON格式（推荐）

文件扩展名：.json

格式示例：
{
  "惊鸿科技（济宁）有限公司": {
    "report_types": ["tax", "laishang", "jining", "agricultural_benhang", "agricultural_kuahang"]
  },
  "山东示例公司": {
    "report_types": ["tax", "laishang"]
  }
}

说明：
• report_types 为数组，包含需要生成的报表类型
• 可选值：tax(个税)、laishang(莱商银行)、jining(济宁银行)、agricultural_benhang(农行本行)、agricultural_kuahang(农行跨行)

═══════════════════════════════════════

📊 二、Excel格式

文件扩展名：.xlsx 或 .xls

必需列：
• 企业名称 - 企业完整名称

可选列（使用1或0标记）：
• 个税版式 - 1(生成) 或 0(不生成)
• 莱商银行版式 - 1(生成) 或 0(不生成)
• 济宁银行版式 - 1(生成) 或 0(不生成)
• 农行本行版式 - 1(生成) 或 0(不生成)
• 农行跨行版式 - 1(生成) 或 0(不生成)

格式示例：
┌─────────────────────┬──────────┬────────────┬────────────┬────────────┬────────────┐
│ 企业名称            │ 个税版式 │莱商银行版式│济宁银行版式│农行本行版式│农行跨行版式│
├─────────────────────┼──────────┼────────────┼────────────┼────────────┼────────────┤
│ 惊鸿科技（济宁）    │    1     │     1      │     1      │     1      │     1      │
│ 山东示例公司        │    1     │     1      │     0      │     0      │     0      │
└─────────────────────┴──────────┴────────────┴────────────┴────────────┴────────────┘

═══════════════════════════════════════

📃 三、CSV格式

文件扩展名：.csv

列结构与Excel格式相同，使用逗号分隔。
建议使用Excel编辑后另存为CSV格式。

CSV示例：
企业名称,个税版式,莱商银行版式,济宁银行版式,农行本行版式,农行跨行版式
惊鸿科技（济宁）有限公司,1,1,1,1,1
山东示例公司,1,1,0,0,0

═══════════════════════════════════════

💡 提示：
• 导入时会自动识别文件格式
• 已存在的企业配置会被更新
• 建议先导出一份作为模板编辑
• 数字1表示生成该报表，0表示不生成
• 也支持使用：是/否、YES/NO、TRUE/FALSE
"""

        # 创建帮助对话框
        help_dialog = tk.Toplevel(self.root)
        help_dialog.title("企业配置格式说明")
        help_dialog.geometry("700x600")
        help_dialog.transient(self.root)
        help_dialog.grab_set()

        # 居中显示
        help_dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 700) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 600) // 2
        help_dialog.geometry(f"700x600+{x}+{y}")

        # 文本区域
        text_frame = ttk.Frame(help_dialog, padding=10)
        text_frame.pack(fill=BOTH, expand=YES)

        text_widget = tk.Text(text_frame, wrap=tk.WORD, font=('Consolas', 10), padx=10, pady=10)
        text_widget.pack(side=LEFT, fill=BOTH, expand=YES)

        scrollbar = ttk.Scrollbar(text_frame, command=text_widget.yview)
        scrollbar.pack(side=RIGHT, fill=Y)
        text_widget.config(yscrollcommand=scrollbar.set)

        text_widget.insert('1.0', help_text)
        text_widget.config(state='disabled')

        # 关闭按钮
        ttk.Button(help_dialog, text="关闭", command=help_dialog.destroy, width=15).pack(pady=10)

    def create_bankcode_tab(self):
        """创建联行号查询标签页"""
        # 工具栏
        toolbar = ttk.Frame(self.frame_bankcode)
        toolbar.pack(fill=X, pady=(0, 10))

        ttk.Label(toolbar, text="🏦 联行号查询", font=('Microsoft YaHei', 16, 'bold')).pack(side=LEFT)

        # 搜索区域
        search_frame = ttk.Frame(self.frame_bankcode)
        search_frame.pack(fill=X, pady=10)

        ttk.Label(search_frame, text="搜索关键词:", font=('Microsoft YaHei', 12)).pack(side=LEFT, padx=(0, 10))

        self.bankcode_search_var = ttk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.bankcode_search_var, width=50, font=('Microsoft YaHei', 12))
        search_entry.pack(side=LEFT, padx=(0, 10), fill=X, expand=YES)

        ttk.Button(search_frame, text="🔍 查询", command=self.search_bankcode,
                  bootstyle="primary", width=10).pack(side=LEFT, padx=5)

        ttk.Button(search_frame, text="🔄 重置", command=self.reset_bankcode_search,
                  bootstyle="secondary", width=10).pack(side=LEFT, padx=5)

        ttk.Button(search_frame, text="📋 复制选中", command=self.copy_selected_bankcode,
                  bootstyle="info", width=12).pack(side=LEFT, padx=5)

        # 说明文字
        info_frame = ttk.Frame(self.frame_bankcode)
        info_frame.pack(fill=X, pady=(0, 10))

        ttk.Label(
            info_frame,
            text="💡 提示：支持模糊查询，例如输入 \"济宁银行 汶上\" 可以匹配到济宁银行在汶上的支行",
            font=('Microsoft YaHei', 11),
            bootstyle="secondary"
        ).pack(anchor=W)

        # 结果显示区域
        result_frame = ttk.Frame(self.frame_bankcode)
        result_frame.pack(fill=BOTH, expand=YES)

        # 创建表格
        columns = ('联行号', '银行名称', '省份', '地区')
        self.bankcode_tree = ttk.Treeview(result_frame, columns=columns, show='headings', height=20, bootstyle="primary")

        col_widths = {'联行号': 150, '银行名称': 500, '省份': 100, '地区': 150}
        for col in columns:
            self.bankcode_tree.heading(col, text=col)
            self.bankcode_tree.column(col, width=col_widths.get(col, 120), anchor='center')

        vsb = ttk.Scrollbar(result_frame, orient="vertical", command=self.bankcode_tree.yview)
        hsb = ttk.Scrollbar(result_frame, orient="horizontal", command=self.bankcode_tree.xview)
        self.bankcode_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.bankcode_tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')

        result_frame.grid_rowconfigure(0, weight=1)
        result_frame.grid_columnconfigure(0, weight=1)

        # 双击复制联行号
        self.bankcode_tree.bind('<Double-1>', self.copy_bankcode)

        # 右键菜单
        self.bankcode_tree.bind('<Button-3>', self.show_bankcode_context_menu)

        # 状态栏
        self.bankcode_status = ttk.Label(self.frame_bankcode, text="就绪", font=('Microsoft YaHei', 10), bootstyle="secondary")
        self.bankcode_status.pack(anchor=W, pady=(10, 0))

        # 加载联行号数据
        self.load_bankcode_data()

    def load_bankcode_data(self):
        """加载联行号数据"""
        self.bankcode_df = None
        bankcode_file = "net_bank_code.csv"

        if os.path.exists(bankcode_file):
            try:
                self.bankcode_df = pd.read_csv(bankcode_file, dtype=str)
                # 确保列名正确
                if 'NET_BANK_CODE' in self.bankcode_df.columns:
                    self.bankcode_df = self.bankcode_df.rename(columns={
                        'NET_BANK_CODE': '联行号',
                        'BANK_NAME': '银行名称',
                        'PROVINCE_CODE': '省份代码',
                        'AREA': '地区',
                        'BANKCODE': '银行代码'
                    })
                # 添加省份列（从银行名称或省份代码解析）
                if '省份' not in self.bankcode_df.columns and '省份代码' in self.bankcode_df.columns:
                    province_map = {
                        '北京': '北京', '天津': '天津', '河北': '河北', '山西': '山西', '内蒙古': '内蒙古',
                        '辽宁': '辽宁', '吉林': '吉林', '黑龙江': '黑龙江', '上海': '上海', '江苏': '江苏',
                        '浙江': '浙江', '安徽': '安徽', '福建': '福建', '江西': '江西', '山东': '山东',
                        '河南': '河南', '湖北': '湖北', '湖南': '湖南', '广东': '广东', '广西': '广西',
                        '海南': '海南', '重庆': '重庆', '四川': '四川', '贵州': '贵州', '云南': '云南',
                        '西藏': '西藏', '陕西': '陕西', '甘肃': '甘肃', '青海': '青海', '宁夏': '宁夏',
                        '新疆': '新疆'
                    }
                    self.bankcode_df['省份'] = self.bankcode_df['省份代码'].map(province_map).fillna('')

                self.bankcode_status.config(text=f"已加载 {len(self.bankcode_df)} 条联行号数据")
            except Exception as e:
                self.bankcode_status.config(text=f"加载联行号数据失败: {e}")
        else:
            self.bankcode_status.config(text=f"未找到联行号数据文件: {bankcode_file}")

    def search_bankcode(self):
        """搜索联行号"""
        if self.bankcode_df is None or self.bankcode_df.empty:
            messagebox.showwarning("提示", "联行号数据未加载")
            return

        keyword = self.bankcode_search_var.get().strip()
        if not keyword:
            messagebox.showwarning("提示", "请输入搜索关键词")
            return

        # 清空现有结果
        for item in self.bankcode_tree.get_children():
            self.bankcode_tree.delete(item)

        # 分割关键词（支持空格分隔的多个关键词）
        keywords = keyword.split()

        # 模糊搜索
        mask = pd.Series([True] * len(self.bankcode_df), index=self.bankcode_df.index)
        for kw in keywords:
            kw_mask = (
                self.bankcode_df['银行名称'].str.contains(kw, na=False, case=False) |
                self.bankcode_df['联行号'].str.contains(kw, na=False, case=False) |
                self.bankcode_df['地区'].str.contains(kw, na=False, case=False) |
                self.bankcode_df.get('省份', '').str.contains(kw, na=False, case=False)
            )
            mask = mask & kw_mask

        results = self.bankcode_df[mask]

        # 显示结果
        for _, row in results.head(500).iterrows():  # 最多显示500条
            self.bankcode_tree.insert('', 'end', values=(
                row.get('联行号', ''),
                row.get('银行名称', ''),
                row.get('省份', ''),
                row.get('地区', '')
            ))

        self.bankcode_status.config(text=f"搜索 \"{keyword}\" 找到 {len(results)} 条结果，显示前 {min(len(results), 500)} 条")

    def reset_bankcode_search(self):
        """重置搜索"""
        self.bankcode_search_var.set('')
        for item in self.bankcode_tree.get_children():
            self.bankcode_tree.delete(item)
        self.bankcode_status.config(text="已重置搜索")

    def copy_bankcode(self, event):
        """双击复制联行号到剪贴板"""
        selected = self.bankcode_tree.selection()
        if not selected:
            return

        values = self.bankcode_tree.item(selected[0])['values']
        bankcode = values[0]
        bank_name = values[1]

        # 复制到剪贴板
        self.root.clipboard_clear()
        self.root.clipboard_append(bankcode)
        self.bankcode_status.config(text=f"已复制联行号: {bankcode} ({bank_name})")

    def create_deleted_tab(self):
        """创建增删记录标签页"""
        # 工具栏
        toolbar = ttk.Frame(self.frame_deleted)
        toolbar.pack(fill=X, pady=(0, 10))

        ttk.Label(toolbar, text="📋 增删记录", font=('Microsoft YaHei', 16, 'bold')).pack(side=LEFT)

        btn_frame = ttk.Frame(toolbar)
        btn_frame.pack(side=RIGHT)

        ttk.Button(
            btn_frame,
            text="🔄 恢复选中",
            command=self.restore_employee,
            bootstyle="success"
        ).pack(side=LEFT, padx=5)

        ttk.Button(
            btn_frame,
            text="🗑️ 清空记录",
            command=self.clear_all_records,
            bootstyle="danger"
        ).pack(side=LEFT, padx=5)

        ttk.Button(
            btn_frame,
            text="🔄 刷新",
            command=self.refresh_all_records,
            bootstyle="info"
        ).pack(side=LEFT, padx=5)

        # 创建Notebook用于切换添加记录和删除记录
        self.record_notebook = ttk.Notebook(self.frame_deleted, bootstyle="secondary")
        self.record_notebook.pack(fill=BOTH, expand=YES, pady=10)

        # 添加记录标签页
        self.frame_added_records = ttk.Frame(self.record_notebook, padding=10)
        self.record_notebook.add(self.frame_added_records, text=" 添加记录 ")
        self.create_added_records_tab()

        # 删除记录标签页
        self.frame_deleted_records = ttk.Frame(self.record_notebook, padding=10)
        self.record_notebook.add(self.frame_deleted_records, text=" 删除记录 ")
        self.create_deleted_records_tab()

        # 状态栏
        self.deleted_status = ttk.Label(self.frame_deleted, text="就绪", font=('Microsoft YaHei', 10), bootstyle="secondary")
        self.deleted_status.pack(anchor=W, pady=(10, 0))

    def create_added_records_tab(self):
        """创建添加记录标签页"""
        # 说明文字
        info_frame = ttk.Frame(self.frame_added_records)
        info_frame.pack(fill=X, pady=(0, 10))

        ttk.Label(
            info_frame,
            text="💡 显示所有添加的员工记录",
            font=('Microsoft YaHei', 11),
            bootstyle="secondary"
        ).pack(anchor=W)

        # 添加记录列表
        list_frame = ttk.Frame(self.frame_added_records)
        list_frame.pack(fill=BOTH, expand=YES)

        # 创建表格
        columns = ('姓名', '身份证号', '手机号', '银行卡号', '开户行', '添加方式', '添加时间')
        self.added_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=18, bootstyle="primary")

        col_widths = {'姓名': 100, '身份证号': 140, '手机号': 100, '银行卡号': 160, '开户行': 200, '添加方式': 100, '添加时间': 140}
        for col in columns:
            self.added_tree.heading(col, text=col)
            self.added_tree.column(col, width=col_widths.get(col, 120), anchor='center')

        vsb = ttk.Scrollbar(list_frame, orient="vertical", command=self.added_tree.yview)
        hsb = ttk.Scrollbar(list_frame, orient="horizontal", command=self.added_tree.xview)
        self.added_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.added_tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')

        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        # 加载数据
        self.refresh_added_list()

    def create_deleted_records_tab(self):
        """创建删除记录标签页"""
        # 说明文字
        info_frame = ttk.Frame(self.frame_deleted_records)
        info_frame.pack(fill=X, pady=(0, 10))

        ttk.Label(
            info_frame,
            text="💡 提示：删除的员工会保留在这里，可以一键恢复到花名册中",
            font=('Microsoft YaHei', 11),
            bootstyle="secondary"
        ).pack(anchor=W)

        # 删除记录列表
        list_frame = ttk.Frame(self.frame_deleted_records)
        list_frame.pack(fill=BOTH, expand=YES)

        # 创建表格
        columns = ('姓名', '身份证号', '手机号', '银行卡号', '开户行', '删除时间')
        self.deleted_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=18, bootstyle="primary")

        col_widths = {'姓名': 100, '身份证号': 140, '手机号': 100, '银行卡号': 160, '开户行': 200, '删除时间': 140}
        for col in columns:
            self.deleted_tree.heading(col, text=col)
            self.deleted_tree.column(col, width=col_widths.get(col, 120), anchor='center')

        vsb = ttk.Scrollbar(list_frame, orient="vertical", command=self.deleted_tree.yview)
        hsb = ttk.Scrollbar(list_frame, orient="horizontal", command=self.deleted_tree.xview)
        self.deleted_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.deleted_tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')

        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        # 加载数据
        self.refresh_deleted_list()

    def refresh_added_list(self):
        """刷新添加记录列表"""
        if not hasattr(self, 'added_tree'):
            return

        for item in self.added_tree.get_children():
            self.added_tree.delete(item)

        added_employees = self.db.get_added_employees()

        for emp in added_employees:
            self.added_tree.insert('', 'end', iid=str(emp['id']), values=(
                emp['姓名'],
                emp['身份证号码'],
                emp['手机号'],
                emp['银行卡号'],
                emp['开户行'],
                emp['添加方式'],
                emp['添加时间']
            ))

    def refresh_deleted_list(self):
        """刷新删除记录列表"""
        if not hasattr(self, 'deleted_tree'):
            return

        for item in self.deleted_tree.get_children():
            self.deleted_tree.delete(item)

        deleted_employees = self.db.get_deleted_employees()

        for emp in deleted_employees:
            self.deleted_tree.insert('', 'end', iid=str(emp['id']), values=(
                emp['姓名'],
                emp['身份证号码'],
                emp['手机号'],
                emp['银行卡号'],
                emp['开户行'],
                emp['删除时间']
            ))

    def refresh_all_records(self):
        """刷新所有记录"""
        self.refresh_added_list()
        self.refresh_deleted_list()
        added_count = len(self.db.get_added_employees())
        deleted_count = len(self.db.get_deleted_employees())
        self.deleted_status.config(text=f"添加记录: {added_count} 条, 删除记录: {deleted_count} 条")

    def clear_all_records(self):
        """清空所有记录"""
        if messagebox.askyesno("确认", "确定要清空所有添加和删除记录吗？\n\n注意：清空删除记录后将无法恢复这些员工！"):
            self.db.clear_added_employees()
            self.db.clear_deleted_employees()
            self.refresh_all_records()
            messagebox.showinfo("成功", "所有记录已清空")

    def restore_employee(self):
        """恢复选中的员工"""
        selected = self.deleted_tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请选择要恢复的员工")
            return

        deleted_id = int(selected[0])

        # 获取员工信息用于显示
        item = self.deleted_tree.item(selected[0])
        values = item['values']
        name = values[0]

        if messagebox.askyesno("确认", f"确定要恢复员工 '{name}' 吗？"):
            success, error = self.db.restore_employee(deleted_id)
            if success:
                self.load_roster()
                self.refresh_roster_list()
                self.refresh_deleted_list()
                messagebox.showinfo("成功", f"员工 '{name}' 已恢复到花名册")
            else:
                messagebox.showerror("错误", f"恢复失败: {error}")

    def clear_deleted_records(self):
        """清空删除记录"""
        deleted_employees = self.db.get_deleted_employees()
        if not deleted_employees:
            messagebox.showinfo("提示", "没有删除记录")
            return

        if messagebox.askyesno("确认", f"确定要清空所有 {len(deleted_employees)} 条删除记录吗？\n\n注意：清空后将无法恢复这些员工！"):
            self.db.clear_deleted_employees()
            self.refresh_deleted_list()
            messagebox.showinfo("成功", "删除记录已清空")

    def create_backup_tab(self):
        """创建备份恢复标签页"""
        # 工具栏
        toolbar = ttk.Frame(self.frame_backup)
        toolbar.pack(fill=X, pady=(0, 10))

        ttk.Label(toolbar, text="💾 备份恢复", font=('Microsoft YaHei', 16, 'bold')).pack(side=LEFT)

        # 主内容区
        content = ttk.Frame(self.frame_backup)
        content.pack(fill=BOTH, expand=YES)

        # 备份区域
        backup_frame = ttk.Labelframe(content, text=" 数据备份 ", padding=20, bootstyle="info")
        backup_frame.pack(fill=X, pady=10)

        ttk.Label(backup_frame, text="备份数据库文件到指定位置", font=('Microsoft YaHei', 11)).pack(anchor=W, pady=(0, 10))

        ttk.Button(
            backup_frame,
            text="📦 一键备份",
            command=self.backup_database,
            bootstyle="info",
            width=20
        ).pack(pady=10)

        # 恢复区域
        restore_frame = ttk.Labelframe(content, text=" 数据恢复 ", padding=20, bootstyle="warning")
        restore_frame.pack(fill=X, pady=10)

        ttk.Label(restore_frame, text="从备份文件恢复数据", font=('Microsoft YaHei', 11)).pack(anchor=W, pady=(0, 10))

        ttk.Button(
            restore_frame,
            text="📂 选择备份文件恢复",
            command=self.restore_database,
            bootstyle="warning",
            width=20
        ).pack(pady=10)

        # 说明区域
        info_frame = ttk.Labelframe(content, text=" 说明 ", padding=20)
        info_frame.pack(fill=BOTH, expand=YES, pady=10)

        info_text = """💡 备份恢复功能说明：

1. 一键备份：将当前所有数据（员工花名册、历史记录、个税数据、企业配置等）打包备份

2. 数据恢复：从之前的备份文件恢复数据，恢复前请确保已备份当前数据

3. 数据文件位置：
   - 数据库文件：salary_tool.db
   - 联行号数据：net_bank_code.csv

⚠️ 注意：恢复数据将覆盖当前所有数据，请谨慎操作！"""

        ttk.Label(info_frame, text=info_text, font=('Microsoft YaHei', 10), justify=LEFT).pack(anchor=W)

        # 状态栏
        self.backup_status = ttk.Label(self.frame_backup, text="就绪", font=('Microsoft YaHei', 10), bootstyle="secondary")
        self.backup_status.pack(anchor=W, pady=(10, 0))

    def backup_database(self):
        """备份数据库"""
        try:
            # 选择备份位置
            backup_path = filedialog.asksaveasfilename(
                defaultextension=".db",
                filetypes=[("数据库文件", "*.db"), ("所有文件", "*.*")],
                initialfile=f"salary_tool_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            )
            if not backup_path:
                return

            # 备份数据库
            self.db.backup_database(backup_path)

            self.backup_status.config(text=f"备份成功: {backup_path}")
            messagebox.showinfo("成功", f"数据库已备份到:\n{backup_path}")
        except Exception as e:
            messagebox.showerror("错误", f"备份失败: {e}")
            self.backup_status.config(text=f"备份失败: {e}")

    def restore_database(self):
        """恢复数据库"""
        try:
            # 选择备份文件
            backup_path = filedialog.askopenfilename(
                title="选择备份文件",
                filetypes=[("数据库文件", "*.db"), ("所有文件", "*.*")]
            )
            if not backup_path:
                return

            # 确认恢复
            if not messagebox.askyesno("确认", "恢复数据将覆盖当前所有数据，确定要继续吗？\n\n建议先备份当前数据！"):
                return

            # 恢复数据库
            self.db.restore_database(backup_path)

            # 重新加载数据
            self.load_roster()
            self.refresh_roster_list()
            self.load_company_config()
            self.refresh_company_list()
            self.refresh_deleted_list()

            self.backup_status.config(text=f"恢复成功: {backup_path}")
            messagebox.showinfo("成功", "数据库已恢复，所有数据已重新加载")
        except Exception as e:
            messagebox.showerror("错误", f"恢复失败: {e}")
            self.backup_status.config(text=f"恢复失败: {e}")

    def copy_selected_bankcode(self):
        """一键复制选中的联行号"""
        selected = self.bankcode_tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请先选择一条记录")
            return

        values = self.bankcode_tree.item(selected[0])['values']
        bankcode = values[0]
        bank_name = values[1]

        # 复制到剪贴板
        self.root.clipboard_clear()
        self.root.clipboard_append(bankcode)
        self.bankcode_status.config(text=f"已复制联行号: {bankcode} ({bank_name})")
        messagebox.showinfo("成功", f"联行号已复制到剪贴板:\n{bankcode}")

    def show_bankcode_context_menu(self, event):
        """显示右键菜单"""
        # 选中右键点击的行
        item = self.bankcode_tree.identify_row(event.y)
        if item:
            self.bankcode_tree.selection_set(item)

            menu = tk.Menu(self.root, tearoff=0)
            menu.add_command(label="📋 复制联行号", command=self.copy_selected_bankcode)
            menu.add_command(label="📋 复制银行名称", command=lambda: self.copy_bank_name())
            menu.add_separator()
            menu.add_command(label="📋 复制整行", command=lambda: self.copy_bankcode_row())
            menu.post(event.x_root, event.y_root)

    def copy_bank_name(self):
        """复制银行名称"""
        selected = self.bankcode_tree.selection()
        if not selected:
            return

        values = self.bankcode_tree.item(selected[0])['values']
        bank_name = values[1]

        self.root.clipboard_clear()
        self.root.clipboard_append(bank_name)
        self.bankcode_status.config(text=f"已复制银行名称: {bank_name}")

    def copy_bankcode_row(self):
        """复制整行信息"""
        selected = self.bankcode_tree.selection()
        if not selected:
            return

        values = self.bankcode_tree.item(selected[0])['values']
        row_text = f"{values[0]}\t{values[1]}\t{values[2]}\t{values[3]}"

        self.root.clipboard_clear()
        self.root.clipboard_append(row_text)
        self.bankcode_status.config(text=f"已复制整行信息")

    def refresh_history_list(self):
        """刷新历史列表"""
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)

        for record in reversed(self.history):
            self.history_tree.insert('', 'end', values=(
                record.get('time', ''),
                record.get('company', ''),
                record.get('period', ''),
                record.get('count', ''),
                f"{record.get('total', 0):.2f}",
                record.get('files', '')
            ))

    def clear_history(self):
        """清空历史（使用数据库）"""
        if messagebox.askyesno("确认", "确定要清空所有历史记录吗？"):
            self.db.clear_history()
            self.history = []
            self.refresh_history_list()
            messagebox.showinfo("成功", "历史记录已清空")


class CompanyDialog:
    """企业配置对话框"""

    def __init__(self, parent, main_app, title, company_name=None, config=None):
        self.main_app = main_app
        self.company_name = company_name
        self.config = config or {}
        self.is_edit = company_name is not None
        self.result = None

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("600x600")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.resizable(False, False)

        # 相对于主窗体居中显示
        self.dialog.update_idletasks()
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        dialog_width = 600
        dialog_height = 600
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")

        self.create_widgets()

        if self.is_edit:
            self.load_data()

        self.dialog.wait_window(self.dialog)

    def create_widgets(self):
        """创建对话框组件"""
        # 标题
        header = ttk.Frame(self.dialog, bootstyle="primary")
        header.pack(fill=X)

        title_text = "编辑企业" if self.is_edit else "添加企业"
        ttk.Label(header, text=title_text, font=('Microsoft YaHei', 16, 'bold'),
                 bootstyle="inverse-primary").pack(pady=18)

        # 表单区域
        form_frame = ttk.Frame(self.dialog, padding=20)
        form_frame.pack(fill=BOTH, expand=YES)

        # 企业名称
        name_frame = ttk.Frame(form_frame)
        name_frame.pack(fill=X, pady=8)

        ttk.Label(name_frame, text="企业名称:", width=12, font=('Microsoft YaHei', 12)).pack(side=LEFT)

        self.name_var = ttk.StringVar()
        self.name_entry = ttk.Entry(name_frame, textvariable=self.name_var, width=40, font=('Microsoft YaHei', 12))
        self.name_entry.pack(side=LEFT, padx=10, fill=X, expand=YES)

        # 报表类型选择
        ttk.Label(form_frame, text="选择需要生成的报表类型:", font=('Microsoft YaHei', 13, 'bold')).pack(anchor=W, pady=(15, 8))

        # 报表类型选项
        self.report_vars = {}
        report_options = [
            ('tax', '个税版式', '生成包含姓名、身份证号、手机号、工资总额的个税申报表'),
            ('laishang', '莱商银行版式', '生成莱商银行批量转账文件'),
            ('jining', '济宁银行版式', '生成济宁银行批量转账文件'),
            ('agricultural_benhang', '农行本行版式', '生成农业银行本行转账CSV文件'),
            ('agricultural_kuahang', '农行跨行版式', '生成农业银行跨行转账CSV文件')
        ]

        for key, label, desc in report_options:
            frame = ttk.Frame(form_frame)
            frame.pack(fill=X, pady=6)

            var = ttk.BooleanVar(value=True)
            self.report_vars[key] = var

            cb = ttk.Checkbutton(frame, text=label, variable=var, bootstyle="primary-round-toggle")
            cb.pack(side=LEFT)

            ttk.Label(frame, text=f" - {desc}", font=('Microsoft YaHei', 10), bootstyle="secondary").pack(side=LEFT, padx=(10, 0))

        # 按钮区域 - 固定在底部
        btn_frame = ttk.Frame(self.dialog, padding=20)
        btn_frame.pack(fill=X, side=BOTTOM)

        ttk.Button(btn_frame, text="取消", command=self.dialog.destroy,
                  bootstyle="secondary", width=15).pack(side=LEFT, padx=10)

        ttk.Button(btn_frame, text="保存", command=self.save,
                  bootstyle="success", width=15).pack(side=RIGHT, padx=10)

    def load_data(self):
        """加载企业数据"""
        if self.company_name:
            self.name_var.set(self.company_name)
            self.name_entry.config(state='disabled')  # 编辑时禁止修改名称

        report_types = self.config.get('report_types', [])
        for key in self.report_vars:
            self.report_vars[key].set(key in report_types)

    def save(self):
        """保存企业配置"""
        name = self.name_var.get().strip()

        if not name:
            messagebox.showwarning("提示", "企业名称不能为空", parent=self.dialog)
            return

        # 获取选中的报表类型
        selected_reports = [key for key, var in self.report_vars.items() if var.get()]

        if not selected_reports:
            messagebox.showwarning("提示", "请至少选择一种报表类型", parent=self.dialog)
            return

        # 如果是新增，检查是否已存在
        if not self.is_edit:
            existing_config = self.main_app.db.get_company_config()
            if name in existing_config:
                messagebox.showwarning("提示", f"企业 '{name}' 已存在", parent=self.dialog)
                return

        # 如果是编辑且改名了，删除旧的
        if self.is_edit and name != self.company_name:
            self.main_app.db.delete_company_config(self.company_name)

        # 保存配置到数据库
        self.main_app.db.save_company_config(name, selected_reports)
        self.main_app.load_company_config()

        self.result = True
        messagebox.showinfo("成功", f"企业 '{name}' 已{'更新' if self.is_edit else '添加'}",
                           parent=self.dialog)
        self.dialog.destroy()


class EmployeeDialog:
    """员工信息对话框"""

    def __init__(self, parent, main_app, title, employee=None):
        self.main_app = main_app
        self.employee = employee
        self.is_edit = employee is not None

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("550x580")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # 相对于主窗体居中显示
        self.dialog.update_idletasks()
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        dialog_width = 550
        dialog_height = 580
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")

        self.create_widgets()

        if employee is not None:
            self.load_data()

        self.dialog.wait_window(self.dialog)

    def create_widgets(self):
        """创建对话框组件"""
        # 标题
        header = ttk.Frame(self.dialog, bootstyle="primary")
        header.pack(fill=X)

        title_text = "编辑员工" if self.is_edit else "添加员工"
        ttk.Label(header, text=title_text, font=('Microsoft YaHei', 16, 'bold'),
                 bootstyle="inverse-primary").pack(pady=18)

        # 表单区域
        form_frame = ttk.Frame(self.dialog, padding=25)
        form_frame.pack(fill=BOTH, expand=YES)

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
            row = ttk.Frame(form_frame)
            row.pack(fill=X, pady=10)

            ttk.Label(row, text=label_text, width=12, font=('Microsoft YaHei', 11)).pack(side=LEFT)

            var = ttk.StringVar()
            self.vars[var_name] = var

            entry = ttk.Entry(row, textvariable=var, width=35, font=('Microsoft YaHei', 11))
            entry.pack(side=LEFT, padx=10, fill=X, expand=YES)

        # 按钮区域
        btn_frame = ttk.Frame(self.dialog, padding=25)
        btn_frame.pack(fill=X)

        ttk.Button(btn_frame, text="取消", command=self.dialog.destroy,
                  bootstyle="secondary", width=10).pack(side=LEFT, padx=5)

        ttk.Button(btn_frame, text="保存", command=self.save,
                  bootstyle="success", width=10).pack(side=RIGHT, padx=5)

    def load_data(self):
        """加载员工数据"""
        data_map = {
            'name': self.employee.get('姓名', ''),
            'id_card': self.employee.get('身份证号码', ''),
            'phone': self.employee.get('手机号', ''),
            'bank_card': self.employee.get('银行卡号', ''),
            'interbank': self.employee.get('联行号', ''),
            'bank_name': self.employee.get('开户行', '')
        }

        for var_name, value in data_map.items():
            if value:
                self.vars[var_name].set(value)

    def save(self):
        """保存员工信息（使用数据库）"""
        name = self.vars['name'].get().strip()

        if not name:
            messagebox.showwarning("提示", "姓名不能为空", parent=self.dialog)
            return

        id_card = self.vars['id_card'].get().strip()
        phone = self.vars['phone'].get().strip()
        bank_card = self.vars['bank_card'].get().strip()
        interbank = self.vars['interbank'].get().strip()
        bank_name = self.vars['bank_name'].get().strip()

        if not bank_card:
            messagebox.showwarning("提示", "银行卡号不能为空", parent=self.dialog)
            return
        if not bank_name:
            messagebox.showwarning("提示", "开户行不能为空", parent=self.dialog)
            return

        if self.is_edit:
            # 更新现有员工
            employee_id = self.employee.get('id')
            success, error = self.main_app.db.update_employee(
                employee_id, name, id_card, phone, bank_card, interbank, bank_name
            )
            if success:
                self.main_app.load_roster()
                self.main_app.refresh_roster_list()
                messagebox.showinfo("成功", f"员工 '{name}' 已更新", parent=self.dialog)
                self.dialog.destroy()
            else:
                messagebox.showerror("错误", f"更新失败: {error}", parent=self.dialog)
        else:
            # 添加新员工
            success, result = self.main_app.db.add_employee(
                name, id_card, phone, bank_card, interbank, bank_name
            )
            if success:
                self.main_app.load_roster()
                self.main_app.refresh_roster_list()
                messagebox.showinfo("成功", f"员工 '{name}' 已添加", parent=self.dialog)
                self.dialog.destroy()
            else:
                messagebox.showerror("错误", f"添加失败: {result}", parent=self.dialog)


class DuplicateNameDialog:
    """重名选择对话框"""

    def __init__(self, parent, name, salary, employees):
        self.selected_employee = None

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("选择员工")
        self.dialog.geometry("700x450")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # 居中显示
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() - 700) // 2
        y = (self.dialog.winfo_screenheight() - 450) // 2
        self.dialog.geometry(f"700x450+{x}+{y}")

        # 标题
        header = ttk.Frame(self.dialog, bootstyle="warning")
        header.pack(fill=X)

        ttk.Label(header, text=f"⚠️ 发现重名员工: {name}",
                 font=('Microsoft YaHei', 16, 'bold'),
                 bootstyle="inverse-warning").pack(pady=(15, 5))

        ttk.Label(header, text=f"工资金额: {salary:.2f} 元",
                 font=('Microsoft YaHei', 12),
                 bootstyle="inverse-warning").pack(pady=(0, 15))

        # 说明文字
        ttk.Label(self.dialog, text="请选择对应的员工（根据身份证后4位或银行卡号区分）：",
                 font=('Microsoft YaHei', 11)).pack(anchor=W, padx=20, pady=15)

        # 员工列表
        list_frame = ttk.Frame(self.dialog, padding=20)
        list_frame.pack(fill=BOTH, expand=YES)

        columns = ('姓名', '身份证', '银行卡号', '开户行')
        self.tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=8)

        col_widths = {'姓名': 100, '身份证': 180, '银行卡号': 200, '开户行': 150}
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=col_widths.get(col, 120), anchor='center')

        vsb = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')

        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        # 插入数据 - 显示完整身份证号便于区分重名员工
        for pos_idx, (df_idx, emp) in enumerate(employees.iterrows()):
            id_card = emp.get('身份证号码', '')
            # 显示完整身份证号，不隐藏，方便用户区分重名员工
            id_display = id_card if id_card else ''

            self.tree.insert('', 'end', values=(
                emp.get('姓名', ''),
                id_display,
                emp.get('银行卡号', ''),
                emp.get('开户行', '')
            ), tags=(str(pos_idx),))

        # 按钮
        btn_frame = ttk.Frame(self.dialog, padding=20)
        btn_frame.pack(fill=X)

        ttk.Button(btn_frame, text="取消", command=self.dialog.destroy,
                  bootstyle="secondary").pack(side=LEFT)

        ttk.Button(btn_frame, text="确认选择", command=self.confirm_selection,
                  bootstyle="success").pack(side=RIGHT)

        # 双击选择
        self.tree.bind('<Double-1>', lambda e: self.confirm_selection())

        self.dialog.wait_window(self.dialog)

    def confirm_selection(self):
        """确认选择"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请选择一个员工", parent=self.dialog)
            return

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
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # 相对于主窗体居中显示
        self.dialog.update_idletasks()
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        dialog_width = 750
        dialog_height = 850
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        self.dialog.minsize(700, 700)

        # 标题
        header = ttk.Frame(self.dialog, bootstyle="info")
        header.pack(fill=X)

        ttk.Label(header, text="📋 智能粘贴员工信息",
                 font=('Microsoft YaHei', 16, 'bold'),
                 bootstyle="inverse-info").pack(pady=15)

        # 主内容区域
        content_frame = ttk.Frame(self.dialog)
        content_frame.pack(fill=BOTH, expand=YES, padx=20, pady=10)

        # 说明
        ttk.Label(content_frame, text="请粘贴包含员工信息的文本，程序会自动识别：",
                 font=('Microsoft YaHei', 11)).pack(anchor=W, pady=(0, 10))

        # 示例
        example_frame = ttk.Labelframe(content_frame, text="示例格式", padding=10)
        example_frame.pack(fill=X, pady=(0, 10))

        example_text = """1.姓名：张三
2.身份证号码：370830200510031731
3.银行卡号：6214 8318 3028 5166
4.开户行行号：308290003298
5.开户行名称：上海天山支行
6.手机号：18608075173"""

        ttk.Label(example_frame, text=example_text,
                 font=('Microsoft YaHei', 10),
                 bootstyle="secondary").pack(anchor=W)

        # 输入框
        ttk.Label(content_frame, text="粘贴内容：", font=('Microsoft YaHei', 11)).pack(anchor=W, pady=(10, 5))
        
        self.text_input = tk.Text(content_frame, height=12, font=('Microsoft YaHei', 12))
        self.text_input.pack(fill=BOTH, expand=YES)

        # 解析按钮 - 固定在底部
        btn_frame = ttk.Frame(self.dialog, padding=15)
        btn_frame.pack(fill=X, side=BOTTOM)

        ttk.Button(btn_frame, text="取消", command=self.dialog.destroy,
                  bootstyle="secondary", width=12).pack(side=LEFT, padx=5)

        ttk.Button(btn_frame, text="🔍 智能解析", command=self.parse_text,
                  bootstyle="info", width=12).pack(side=RIGHT, padx=5)

        self.dialog.wait_window(self.dialog)

    def parse_text(self):
        """解析文本"""
        text = self.text_input.get("1.0", 'end').strip()
        if not text:
            messagebox.showwarning("提示", "请输入内容", parent=self.dialog)
            return

        data = {
            '姓名': '',
            '身份证号码': '',
            '手机号': '',
            '银行卡号': '',
            '联行号': '',
            '开户行': ''
        }

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
                if field == '银行卡号':
                    value = re.sub(r'\s+', '', value)
                data[field] = value

        if not data['姓名']:
            messagebox.showwarning("提示", "未能识别到姓名，请检查输入格式", parent=self.dialog)
            return

        self.parsed_data = data
        self.dialog.destroy()


def main():
    """主函数"""
    # 创建应用
    app = ttk.Window(
        title=f"工资报表生成工具 {VERSION}",
        themename="flatly",  # 飞书风格使用 flatly 主题（白色背景+蓝色主色）
        size=(1600, 1000),
        minsize=(1400, 900)
    )

    # 设置全局字体缩放
    style = ttk.Style()
    style.configure('.', font=('Microsoft YaHei', 11))
    
    # 设置 Treeview 行高和字体 - 增加行高让汉字显示更舒展
    # 需要为不同 bootstyle 设置对应的样式
    for style_name in ['Treeview', 'primary.Treeview', 'info.Treeview', 'success.Treeview', 'warning.Treeview', 'danger.Treeview']:
        style.configure(style_name, rowheight=42, font=('Microsoft YaHei', 11))
    for style_name in ['Treeview.Heading', 'primary.Treeview.Heading', 'info.Treeview.Heading']:
        style.configure(style_name, font=('Microsoft YaHei', 12, 'bold'))

    # 创建主应用
    salary_tool = SalaryTool(app)

    # 运行应用
    app.mainloop()


class TaxCalculator:
    """个税计算器"""
    
    # 2024年个税税率表（综合所得适用）
    TAX_BRACKETS = [
        (0, 36000, 0.03, 0),
        (36000, 144000, 0.10, 2520),
        (144000, 300000, 0.20, 16920),
        (300000, 420000, 0.25, 31920),
        (420000, 660000, 0.30, 52920),
        (660000, 960000, 0.35, 85920),
        (960000, float('inf'), 0.45, 181920)
    ]
    
    @staticmethod
    def calculate_tax(gross_salary, threshold=5000, social_insurance=0, special_deduction=0):
        """
        计算个税（正向计算）
        
        参数:
            gross_salary: 税前工资
            threshold: 起征点（默认5000）
            social_insurance: 社保公积金扣除
            special_deduction: 专项附加扣除
            
        返回:
            (应纳税所得额, 税率, 速算扣除数, 个税, 税后工资)
        """
        # 应纳税所得额 = 税前工资 - 起征点 - 社保公积金 - 专项附加扣除
        taxable_income = gross_salary - threshold - social_insurance - special_deduction
        
        if taxable_income <= 0:
            return 0, 0, 0, 0, gross_salary
        
        # 查找适用税率
        for low, high, rate, quick_deduction in TaxCalculator.TAX_BRACKETS:
            if low < taxable_income <= high:
                tax = taxable_income * rate - quick_deduction
                net_salary = gross_salary - tax - social_insurance
                return taxable_income, rate, quick_deduction, tax, net_salary
        
        return 0, 0, 0, 0, gross_salary
    
    @staticmethod
    def reverse_calculate_tax(net_salary, threshold=5000, social_insurance=0, special_deduction=0):
        """
        反算个税（根据税后工资反推税前工资）
        使用二分查找算法，确保收敛
        
        参数:
            net_salary: 税后工资（实际到手）
            threshold: 起征点（默认5000）
            social_insurance: 社保公积金扣除
            special_deduction: 专项附加扣除
            
        返回:
            (税前工资, 应纳税所得额, 税率, 速算扣除数, 个税)
        """
        # 如果税后工资小于起征点+扣除项，则不需要缴税
        min_gross = threshold + social_insurance + special_deduction
        if net_salary <= min_gross - social_insurance:
            return net_salary + social_insurance, 0, 0, 0, 0
        
        # 二分查找税前工资
        # 下限：税后工资 + 社保（至少这么多）
        low = net_salary + social_insurance
        # 上限：税后工资 * 2（应该足够大了）
        high = net_salary * 2 + social_insurance
        
        for _ in range(100):  # 最多迭代100次
            mid = (low + high) / 2
            _, _, _, tax, calculated_net = TaxCalculator.calculate_tax(
                mid, threshold, social_insurance, special_deduction
            )
            
            # 检查误差
            error = calculated_net - net_salary
            if abs(error) < 0.001:
                # 找到精确解，调整税前工资使税后工资精确匹配
                mid = mid - error  # 微调税前工资
                taxable = mid - threshold - social_insurance - special_deduction
                if taxable <= 0:
                    return net_salary + social_insurance, 0, 0, 0, 0
                # 重新计算获取正确的税率信息
                for low_b, high_b, rate, quick in TaxCalculator.TAX_BRACKETS:
                    if low_b < taxable <= high_b:
                        tax = taxable * rate - quick
                        return mid, taxable, rate, quick, tax
                return mid, 0, 0, 0, 0
            
            if error > 0:
                # 计算的税后工资太高，需要降低税前工资
                high = mid
            else:
                # 计算的税后工资太低，需要提高税前工资
                low = mid
        
        # 返回最接近的结果
        mid = (low + high) / 2
        taxable = mid - threshold - social_insurance - special_deduction
        for low_b, high_b, rate, quick in TaxCalculator.TAX_BRACKETS:
            if low_b < taxable <= high_b:
                tax = taxable * rate - quick
                return mid, taxable, rate, quick, tax
        
        return net_salary + social_insurance, 0, 0, 0, 0


if __name__ == "__main__":
    main()
