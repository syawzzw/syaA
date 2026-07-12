#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""分析 Z:/115open/Hp 目录下剩余文件为何没被录入数据库"""
import os
import re
import sys
import sqlite3

sys.path.insert(0, 'src/url')
from gui_app import is_western_designation

HP_DIR = "Z:/115open/Hp"
DB_PATH = "syaA.db"

def extract_fanhao(filename):
    """模拟 _check_115_recursive 的番号提取逻辑"""
    name = os.path.splitext(filename)[0]
    # 跟代码里一样：re.findall(r"[0-9a-zA-Z]+-[0-9a-zA-Z]+", file)
    candidates = re.findall(r"[0-9a-zA-Z]+-[0-9a-zA-Z]+", name)
    return candidates

def main():
    files = sorted(os.listdir(HP_DIR))
    print(f"Hp 目录文件总数: {len(files)}")
    print()

    # 加载数据库中所有 designation
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT designation, numbers_name, local_path FROM av")
    db_designations = {}
    db_local_paths = set()
    for row in cur.fetchall():
        des, nn, lp = row
        if des:
            db_designations[des.lower()] = (des, nn, lp)
        if lp:
            db_local_paths.add(lp)
    conn.close()
    print(f"数据库 designation 总数: {len(db_designations)}")
    print()

    # 分类统计
    categories = {
        'western_skip': [],        # 欧美片，会被 is_western_designation 跳过
        'no_fanhao': [],           # 提取不出候选番号
        'fanhao_not_in_db': [],    # 有候选番号但不在数据库
        'in_db_wrong_path': [],    # 在数据库但 local_path 不指向 Hp
        'in_db_correct': [],       # 在数据库且 local_path 指向 Hp
    }

    for f in files:
        filepath = os.path.join(HP_DIR, f).replace('\\', '/')
        candidates = extract_fanhao(f)

        # 检查是否在数据库中（按 local_path）
        if filepath in db_local_paths:
            categories['in_db_correct'].append(f)
            continue

        # 检查是否欧美片
        name_without_ext = os.path.splitext(f)[0]
        if is_western_designation(name_without_ext):
            categories['western_skip'].append(f)
            continue

        # 检查候选番号
        if not candidates:
            categories['no_fanhao'].append(f)
            continue

        # 检查候选番号是否在数据库
        found_in_db = False
        for c in candidates:
            if c.lower() in db_designations:
                des, nn, lp = db_designations[c.lower()]
                categories['in_db_wrong_path'].append((f, c, lp or '(空)'))
                found_in_db = True
                break
        if found_in_db:
            continue

        # 有候选番号但不在数据库
        categories['fanhao_not_in_db'].append((f, candidates[:3]))

    # 打印结果
    print("=" * 70)
    print("分类统计")
    print("=" * 70)
    for cat, items in categories.items():
        print(f"\n--- {cat}: {len(items)} 个 ---")

    print("\n" + "=" * 70)
    print("1. 欧美片（is_western_designation 判定）")
    print("=" * 70)
    for f in categories['western_skip'][:20]:
        print(f"  {f}")
    if len(categories['western_skip']) > 20:
        print(f"  ... 还有 {len(categories['western_skip']) - 20} 个")

    print("\n" + "=" * 70)
    print("2. 提取不出候选番号（文件名中没有 字母-数字 格式）")
    print("=" * 70)
    for f in categories['no_fanhao'][:30]:
        print(f"  {f}")
    if len(categories['no_fanhao']) > 30:
        print(f"  ... 还有 {len(categories['no_fanhao']) - 30} 个")

    print("\n" + "=" * 70)
    print("3. 有候选番号但不在数据库中")
    print("=" * 70)
    for f, cands in categories['fanhao_not_in_db'][:30]:
        print(f"  {f}")
        print(f"    候选番号: {cands}")
    if len(categories['fanhao_not_in_db']) > 30:
        print(f"  ... 还有 {len(categories['fanhao_not_in_db']) - 30} 个")

    print("\n" + "=" * 70)
    print("4. 在数据库中但 local_path 不指向 Hp")
    print("=" * 70)
    for f, cand, lp in categories['in_db_wrong_path'][:20]:
        print(f"  文件: {f}")
        print(f"    匹配番号: {cand} | DB中的local_path: {lp}")
    if len(categories['in_db_wrong_path']) > 20:
        print(f"  ... 还有 {len(categories['in_db_wrong_path']) - 20} 个")

    print("\n" + "=" * 70)
    print("5. 在数据库中且 local_path 正确指向 Hp")
    print("=" * 70)
    print(f"  共 {len(categories['in_db_correct'])} 个")

    # 汇总
    print("\n" + "=" * 70)
    print("汇总")
    print("=" * 70)
    print(f"  总文件数:                    {len(files)}")
    print(f"  欧美片(会被跳过):             {len(categories['western_skip'])}")
    print(f"  提取不出番号:                 {len(categories['no_fanhao'])}")
    print(f"  有番号但不在DB:               {len(categories['fanhao_not_in_db'])}")
    print(f"  在DB但local_path不指向Hp:     {len(categories['in_db_wrong_path'])}")
    print(f"  在DB且local_path正确:         {len(categories['in_db_correct'])}")

if __name__ == '__main__':
    main()
