#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据清洗脚本：修复 performer 字段溢出污染问题
===========================================

问题描述：
- meta description 被截断导致 _extract_field 提取到溢出内容
- performer 字段包含了其他字段的内容（如【影片容量】、【是否有码】等）

解决方案：
1. 从已保存的 HTML 源文件重新提取正确的字段值
2. 如果源文件不存在，使用启发式规则清洗现有数据

使用方法：
    python fix_performer_overflow.py [--dry-run] [--verbose]

参数：
    --dry-run   只显示需要修复的记录，不实际修改数据库
    --verbose   显示详细的处理过程
"""

import os
import re
import sys
import sqlite3
import argparse
from pathlib import Path

# 项目路径配置
PROJECT_ROOT = Path(__file__).parent
DB_PATH = PROJECT_ROOT / "syaA.db"
SOURCE_DIR = PROJECT_ROOT / "output" / "高清中文字幕网页源文件"
OFFLINE_DIR = PROJECT_ROOT / "output" / "离线网页"


def clean_html_value(val):
    """清理 HTML 标签和实体"""
    if not val:
        return ""
    # 去除 HTML 标签
    val = re.sub(r'<[^>]+>', '', val)
    # 去除 HTML 实体
    val = re.sub(r'&nbsp;', ' ', val)
    val = re.sub(r'&lt;', '<', val)
    val = re.sub(r'&gt;', '>', val)
    val = re.sub(r'&amp;', '&', val)
    val = re.sub(r'&quot;', '"', val)
    # 去除多余空白
    val = re.sub(r'\s+', ' ', val).strip()
    return val


def extract_field_from_html(html, field_name, default="unknown"):
    """从 HTML 中提取字段值（简化版，用于数据清洗）"""
    candidates = []

    # 策略1: <font> 标签区域（优先级最高，最准确）
    pat_font = r"<font[^>]*>\s*【{}】[：:]\s*(.*?)\s*</font>".format(field_name)
    for m in re.findall(pat_font, html, re.DOTALL | re.IGNORECASE):
        val = clean_html_value(m)
        if val and len(val) <= 80:
            candidates.append(('font', val))

    # 策略2: 正文纯文本（第二优先级）
    pat_body = r"【{}】[：:]\s*(.*?)(?:<br|<BR|\n|【)".format(field_name)
    for m in re.findall(pat_body, html, re.IGNORECASE):
        val = clean_html_value(m)
        if val and len(val) <= 80:
            candidates.append(('body', val))

    # 策略3: meta description（最后选择，因为可能被截断）
    other_fields = ["出演女优", "影片名称", "影片容量", "是否有码", "番号", "种子期限", "下载工具"]
    other_fields = [f for f in other_fields if f != field_name]
    stop_pattern = "|".join(re.escape("【" + f + "】") for f in other_fields)
    if stop_pattern:
        pat_meta = r"【{}】[：:]\s*((?:(?!{}).)*)".format(field_name, stop_pattern)
        for m in re.findall(pat_meta, html, re.IGNORECASE):
            val = clean_html_value(m)
            if val:
                candidates.append(('meta', val))

    if not candidates:
        return default

    # 优先选择策略1和2的结果（更可靠）
    for source, val in candidates:
        if source in ('font', 'body'):
            return val

    # 最后才选择 meta
    return candidates[0][1] if candidates else default


def find_source_file(designation):
    """查找 HTML 源文件路径"""
    # 在高清中文字幕网页源文件目录查找
    for date_dir in sorted(SOURCE_DIR.iterdir(), reverse=True):
        if not date_dir.is_dir():
            continue
        source_file = date_dir / f"{designation}.txt"
        if source_file.exists():
            return source_file

    return None


def find_offline_file(designation):
    """查找离线网页文件"""
    # 支持多种后缀 (-UC, -C 等)
    for suffix in ['', '-UC', '-C']:
        pattern = f"**/{designation}{suffix}/index.html"
        for match in OFFLINE_DIR.glob(pattern):
            return match

    return None


def is_performer_polluted(performer):
    """判断 performer 是否被污染"""
    if not performer or performer == "unknown":
        return False

    # 特征1: 包含其他字段名
    if re.search(r'【(影片|是否|番号|种子|下载)', performer):
        return True

    # 特征2: 超过30字符且包含 HTML 残留
    if len(performer) > 30 and re.search(r'[</>\'\"]', performer):
        return True

    # 特征3: 包含典型的 meta description 溢出特征
    if '...' in performer and len(performer) > 40:
        return True

    # 特征4: 以 meta description 结尾模式结束
    if re.search(r'\d+堂\[.*?\]"\s*/?\s*>?$', performer):
        return True

    # 特征5: 超长（正常演员名不会超过20字符）
    if len(performer) > 50:
        return True

    return False


def fix_single_record(cur, numbers_name, performer, dry_run=False, verbose=False):
    """修复单条记录的 performer 字段"""
    designation = numbers_name.rsplit('-', 1)[0] if '-' in numbers_name else numbers_name

    # 查找源文件
    source_file = find_source_file(numbers_name)
    offline_file = find_offline_file(designation) if not source_file else None

    html_file = source_file or offline_file
    if not html_file:
        if verbose:
            print(f"  ⚠️  未找到源文件: {numbers_name}")
        return False, "未找到源文件"

    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            html = f.read()
    except Exception as e:
        if verbose:
            print(f"  ❌ 读取失败: {html_file} | 错误: {e}")
        return False, f"读取失败: {e}"

    # 重新提取 performer
    new_performer = extract_field_from_html(html, "出演女优", "unknown")

    # 清洗 new_performer
    if new_performer and new_performer != "unknown":
        # 基本清洗
        new_performer = re.sub(r"^【[^】]*】[：:]\s*", "", new_performer)
        if not new_performer.startswith("【"):
            new_performer = re.sub(r"【[^】]*】.*$", "", new_performer).strip()
        new_performer = re.sub(r'["\']?\s*/?>\s*$', '', new_performer).strip()
        new_performer = new_performer.lstrip("-").strip()
        new_performer = re.sub(r"[、，,\t　]", " ", new_performer)
        new_performer = performer.rstrip(".;。、,，/\\")
        new_performer = re.sub(r"\s+", " ", new_performer).strip()

        # 长度检查：如果还是太长，说明提取有问题
        if len(new_performer) > 30:
            if verbose:
                print(f"  ⚠️  重新提取后仍然过长 ({len(new_performer)}字符)，保持原样")
            return False, "重新提取后仍然过长"

    # 检查是否有改善
    old_clean_len = len(clean_html_value(performer))
    new_clean_len = len(new_performer)

    if new_performer == "unknown" or new_clean_len >= old_clean_len:
        if verbose:
            print(f"  ➡️  无改善 (old={old_clean_len}, new={new_clean_len})")
        return False, "无改善"

    if dry_run:
        if verbose:
            print(f"  ✅ [DRY-RUN] 将更新:")
            print(f"     old: {str(performer)[:60]}...")
            print(f"     new: {new_performer}")
        return True, new_performer
    else:
        try:
            cur.execute(
                "UPDATE av SET performer = ? WHERE numbers_name = ?",
                (new_performer, numbers_name)
            )
            if verbose:
                print(f"  ✅ 已更新:")
                print(f"     old: {str(performer)[:60]}...")
                print(f"     new: {new_performer}")
            return True, new_performer
        except Exception as e:
            if verbose:
                print(f"  ❌ 更新失败: {e}")
            return False, f"更新失败: {e}"


def main():
    parser = argparse.ArgumentParser(description='修复 performer 字段溢出污染问题')
    parser.add_argument('--dry-run', action='store_true', help='只显示需要修复的记录，不实际修改数据库')
    parser.add_argument('--verbose', action='store_true', help='显示详细的处理过程')
    args = parser.parse_args()

    print("=" * 70)
    print("数据清洗工具：修复 performer 字段溢出污染问题")
    print("=" * 70)
    print(f"数据库: {DB_PATH}")
    print(f"源文件目录: {SOURCE_DIR}")
    print(f"离线网页目录: {OFFLINE_DIR}")
    print(f"模式: {'DRY-RUN (不修改数据库)' if args.dry_run else 'LIVE (将修改数据库)'}")
    print("=" * 70)

    # 连接数据库
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    try:
        # 统计总数
        cur.execute('SELECT COUNT(*) FROM av')
        total = cur.fetchone()[0]
        print(f"\n总记录数: {total}")

        # 查找所有被污染的记录
        cur.execute('SELECT numbers_name, performer FROM av WHERE performer IS NOT NULL AND performer != "" AND performer != "unknown"')
        all_records = cur.fetchall()

        polluted_records = []
        for numbers_name, performer in all_records:
            if is_performer_polluted(performer):
                polluted_records.append((numbers_name, performer))

        print(f"检测到被污染的记录数: {len(polluted_records)}")

        if not polluted_records:
            print("\n🎉 所有记录都是干净的，无需修复！")
            return

        print(f"\n开始处理 {'(模拟模式)' if args.dry_run else ''}...")
        print("-" * 70)

        # 限制处理数量以便快速测试（正式运行时去掉这个限制）
        max_process = min(50, len(polluted_records))  # 先只处理前50条测试
        records_to_process = polluted_records[:max_process]

        fixed_count = 0
        skipped_count = 0
        error_count = 0

        for i, (numbers_name, performer) in enumerate(records_to_process, 1):
            if i % 100 == 0:
                print(f"\n⏳ 进度: {i}/{len(records_to_process)} ({i*100//len(records_to_process)}%)")

            if args.verbose or (i <= 20):  # 始终显示前20条
                print(f"\n[{i}/{len(records_to_process)}] {numbers_name}")
                print(f"  当前 performer: {str(performer)[:60]}...")

            success, result = fix_single_record(
                cur, numbers_name, performer,
                dry_run=args.dry_run,
                verbose=args.verbose or (i <= 20)
            )

            if success:
                fixed_count += 1
            elif result.startswith("未") or result.startswith("无") or "过长" in result:
                skipped_count += 1
            else:
                error_count += 1

        # 提交事务（如果不是 dry-run）
        if not args.dry_run and fixed_count > 0:
            conn.commit()
            print("\n" + "=" * 70)
            print(f"✅ 已提交 {fixed_count} 条修改到数据库")
        elif args.dry_run:
            print("\n" + "=" * 70)
            print(f"📋 DRY-RUN 完成：将修复 {fixed_count} 条记录")

        print(f"\n统计结果:")
        print(f"  - 需要修复: {len(polluted_records)}")
        print(f"  - 成功修复: {fixed_count}")
        print(f"  - 跳过: {skipped_count}")
        print(f"  - 失败: {error_count}")

    finally:
        conn.close()

    print("\n" + "=" * 70)
    print("完成！")
    print("=" * 70)


if __name__ == "__main__":
    main()
