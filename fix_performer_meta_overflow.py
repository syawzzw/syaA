#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据清洗脚本：修复 performer 字段 meta description 溢出污染
=============================================================

针对问题：
- meta description 被截断导致 _extract_field 提取到溢出内容
- performer 包含了【影片容量】、【是否有码】、番号、论坛名等

使用方法：
    python fix_performer_meta_overflow.py [--dry-run] [--live]
"""

import os
import re
import sqlite3
from pathlib import Path

# 项目路径
PROJECT_ROOT = Path(__file__).parent
DB_PATH = PROJECT_ROOT / "syaA.db"
SOURCE_DIR = PROJECT_ROOT / "output" / "高清中文字幕网页源文件"


def clean_html_value(val):
    """清理 HTML 标签和实体"""
    if not val:
        return ""
    val = re.sub(r'<[^>]+>', '', val)
    val = re.sub(r'&nbsp;', ' ', val)
    val = re.sub(r'\s+', ' ', val).strip()
    return val


def extract_performersafe_from_html(html):
    """
    安全地从 HTML 提取 performer。
    优先级：<font>标签 > 正文（短值） > 正文（长值）
    完全不使用 meta description！
    """
    candidates = []

    # 策略1: <font> 标签（最可靠）
    for m in re.finditer(r"<font[^>]*>\s*【出演女[优優]】[：:]\s*(.*?)\s*</font>", html, re.IGNORECASE | re.DOTALL):
        val = clean_html_value(m.group(1))
        if val and 0 < len(val) <= 30:
            candidates.append(('font_short', val))
        elif val and len(val) > 30:
            candidates.append(('font_long', val))

    # 策略2: 正文（以 <br 或 【 结尾的短值，最可靠）
    for m in re.finditer(r"【出演女[优優]】[：:]\s*(.*?)(?:<br\s*/?>|<BR\s*/?>)", html, re.IGNORECASE):
        val = clean_html_value(m.group(1))
        if val and 0 < len(val) <= 50:
            candidates.append(('body_br', val))

    # 策略3: 正文（以换行或下一个【结尾）
    for m in re.finditer(r"【出演女[优優]】[：:]\s*(.*?)(?:\n|【)", html, re.IGNORECASE):
        val = clean_html_value(m.group(1))
        if val and 0 < len(val) <= 50:
            candidates.append(('body_nl', val))

    if not candidates:
        return "unknown"

    # 排序优先级：font_short > body_br > body_nl > font_long
    priority_order = ['font_short', 'body_br', 'body_nl', 'font_long']
    candidates.sort(key=lambda x: priority_order.index(x[0]) if x[0] in priority_order else 99)

    best_source, best_val = candidates[0]

    # 额外安全检查：如果最佳候选仍然可疑，返回 unknown
    if len(best_val) > 30 and (re.search(r'[【】]', best_val) or re.search(r'\d+堂', best_val)):
        return "unknown"

    return best_val


def find_source_file(numbers_name):
    """查找 HTML 源文件"""
    # 按日期倒序查找（最新的在前）
    if not SOURCE_DIR.exists():
        return None

    date_dirs = sorted([d for d in SOURCE_DIR.iterdir() if d.is_dir()], reverse=True)
    for date_dir in date_dirs:
        source_file = date_dir / f"{numbers_name}.txt"
        if source_file.exists():
            return source_file

    return None


def is_meta_overflow_polluted(performer):
    """判断是否是 meta description 溢出污染"""
    if not performer or performer == "unknown":
        return False

    # 明确的溢出特征
    overflow_patterns = [
        r'【(影片|是否|番号|种子|下载)',   # 包含其他字段名
        r'\d+堂\[',                          # 包含论坛名
        r'"\s*/?\s*>',                       # 以 HTML 属性结束
        r'\.\.\.',                           # 包含省略号（截断标志）
    ]

    for pattern in overflow_patterns:
        if re.search(pattern, performer):
            return True

    return False


def main(dry_run=True):
    print("=" * 70)
    print("数据清洗：修复 performer 字段 meta description 溢出")
    print("=" * 70)
    print(f"数据库: {DB_PATH}")
    print(f"模式: {'DRY-RUN' if dry_run else 'LIVE'}")
    print("=" * 70)

    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    try:
        # 查找所有被污染的记录
        cur.execute('''
            SELECT numbers_name, performer FROM av
            WHERE (performer LIKE '%【%' OR performer LIKE '%98堂%')
            AND LENGTH(performer) > 30
            ORDER BY numbers_name
        ''')
        polluted = cur.fetchall()

        print(f"\n检测到被污染记录: {len(polluted)} 条\n")

        fixed = 0
        skipped_no_source = 0
        skipped_no_improve = 0
        errors = 0

        for i, (numbers_name, old_perf) in enumerate(polluted, 1):
            print(f"[{i}/{len(polluted)}] {numbers_name}")
            print(f"  OLD ({len(old_perf)}字符): {str(old_perf)[:60]}...")

            # 查找源文件
            source_file = find_source_file(numbers_name)
            if not source_file:
                print(f"  ⚠️  无源文件，跳过")
                skipped_no_source += 1
                continue

            # 读取并重新提取
            try:
                with open(source_file, 'r', encoding='utf-8') as f:
                    html = f.read()
            except Exception as e:
                print(f"  ❌ 读取失败: {e}")
                errors += 1
                continue

            new_perf = extract_performersafe_from_html(html)

            # 判断是否有改善
            old_clean = clean_html_value(old_perf)
            if new_perf == "unknown":
                print(f"  ⚠️  提取失败 (unknown)，保持原样")
                skipped_no_improve += 1
            elif len(new_perf) >= len(old_clean):
                print(f"  ➡️  无改善 (old={len(old_clean)}, new={len(new_perf)})")
                print(f"      new: {new_perf}")
                skipped_no_improve += 1
            else:
                if not dry_run:
                    cur.execute("UPDATE av SET performer = ? WHERE numbers_name = ?", (new_perf, numbers_name))
                print(f"  ✅ {'[DRY-RUN] ' if dry_run else ''}已更新:")
                print(f"      NEW ({len(new_perf)}字符): {new_perf}")
                fixed += 1

        # 提交
        if not dry_run and fixed > 0:
            conn.commit()
            print("\n" + "=" * 70)
            print(f"✅ 已提交 {fixed} 条修改")

        print(f"\n{'=' * 70}")
        print(f"统计:")
        print(f"  总计:     {len(polluted)}")
        print(f"  已修复:   {fixed}")
        print(f"  无源文件: {skipped_no_source}")
        print(f"  无改善:   {skipped_no_improve}")
        print(f"  错误:     {errors}")
        print("=" * 70)

    finally:
        conn.close()


if __name__ == "__main__":
    import sys
    dry_run = "--live" not in sys.argv
    main(dry_run=dry_run)
