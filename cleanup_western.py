#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""清理欧美片离线网页目录 + 数据库记录（带误判排除）"""
import os
import re
import sys
import json
import shutil
import sqlite3

sys.path.insert(0, 'src/url')
from gui_app import is_western_designation

OFFLINE_ROOT = "output/离线网页"
DB_PATH = "syaA.db"

# 误判排除列表 — 这些虽然匹配了规则但实际不是欧美片
FALSE_POSITIVES = {
    "azato making shokai genteiban",  # 日文同人3D游戏
    "bienenstich im liebesnest",      # 德国经典电影(1975)
    "plwt.kpqq4.com",                  # 垃圾URL
}

def extract_fanhao_from_dirname(dirname):
    """从目录名中提取番号"""
    name = dirname
    name = re.sub(r'^post_\d+_', '', name)
    prefix_tags = ["[中文字幕]", "[无码]", "[高清]", "[原档]", "[破解]", "[字幕]", "[无码破解]", "[FC2]",
                   "【听译】", "【转译】", "【磁力链接】", "【115ED2K】", "【115ED2k】", "【整理】", "【锦鲤原创图文】"]
    for tag in prefix_tags:
        if name.startswith(tag):
            name = name[len(tag):].strip()
    if name.endswith("-UC"):
        name = name[:-3]
    elif name.endswith("-C"):
        name = name[:-2]
    if " - " in name:
        name = name.split(" - ")[0].strip()
    for i, c in enumerate(name):
        if '\u4e00' <= c <= '\u9fff' or '\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff':
            name = name[:i].strip()
            break
    return name

def is_false_positive(fanhao):
    """检查是否是已知的误判"""
    fl = fanhao.lower().strip()
    for fp in FALSE_POSITIVES:
        if fp in fl:
            return True
    return False

def scan_western_dirs():
    """扫描所有欧美片离线网页目录"""
    western_dirs = []
    for root, dirs, files in os.walk(OFFLINE_ROOT):
        for d in dirs:
            if d.startswith('_') or d in ['css', 'js']:
                continue
            fanhao = extract_fanhao_from_dirname(d)
            if fanhao and is_western_designation(fanhao):
                if is_false_positive(fanhao):
                    continue
                full_path = os.path.join(root, d)
                size = 0
                for r2, d2, f2 in os.walk(full_path):
                    for ff in f2:
                        try:
                            size += os.path.getsize(os.path.join(r2, ff))
                        except:
                            pass
                western_dirs.append({
                    'path': full_path,
                    'dirname': d,
                    'fanhao': fanhao,
                    'size': size,
                })
    return western_dirs

def scan_western_db_records():
    """扫描数据库中欧美片记录"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT numbers_name, designation, name FROM av")
    records = []
    for row in cur.fetchall():
        numbers_name, designation, name = row
        if is_false_positive(designation or '') or is_false_positive(name or ''):
            continue
        if is_western_designation(designation) or is_western_designation(name):
            records.append({
                'numbers_name': numbers_name,
                'designation': designation,
                'name': (name or '')[:60],
            })
    conn.close()
    return records

def delete_western_dirs(western_dirs, dry_run=True):
    """删除欧美片离线网页目录"""
    total_size = 0
    for d in western_dirs:
        total_size += d['size']
        if not dry_run:
            try:
                shutil.rmtree(d['path'])
                print(f"  [DELETED] {d['path']}")
            except Exception as e:
                print(f"  [ERROR] {d['path']}: {e}")
        else:
            print(f"  [DRY-RUN] {d['path']}")
    return total_size

def delete_western_db_records(records, dry_run=True):
    """删除数据库中欧美片记录"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    deleted = 0
    for r in records:
        if not dry_run:
            cur.execute("DELETE FROM av WHERE numbers_name = ?", (r['numbers_name'],))
            if cur.rowcount > 0:
                deleted += 1
        else:
            deleted += 1
    if not dry_run:
        conn.commit()
    conn.close()
    return deleted

def update_downloaded_json(western_post_ids, dry_run=True):
    """更新 _downloaded.json"""
    json_path = os.path.join(OFFLINE_ROOT, "_downloaded.json")
    if not os.path.exists(json_path):
        return 0
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    updated = 0
    for pid, info in data.items():
        if pid in western_post_ids and info.get('status') == 'saved':
            info['status'] = 'skipped'
            info['skip_reason'] = 'western_video_cleanup'
            updated += 1
    if not dry_run:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    return updated

def regenerate_offline_index():
    """重新生成离线网页主页索引"""
    # 这里只标记需要重新生成，实际生成由 GUI 的 _generate_offline_index() 完成
    print("  [NOTE] 离线网页主页索引需要重新生成（在 GUI 中点击'生成主页'或下次爬取时自动更新）")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute', action='store_true', help='实际执行删除（默认dry-run）')
    args = parser.parse_args()
    dry_run = not args.execute

    mode = "DRY-RUN（预览）" if dry_run else "EXECUTE（实际执行）"
    print(f"模式: {mode}")
    print()

    # 1. 扫描离线网页目录
    print("=" * 60)
    print("1. 扫描欧美片离线网页目录")
    print("=" * 60)
    western_dirs = scan_western_dirs()
    total_size = sum(d['size'] for d in western_dirs)
    print(f"找到 {len(western_dirs)} 个欧美片目录，总大小 {total_size / 1024 / 1024:.1f} MB")
    print()

    # 2. 扫描数据库记录
    print("=" * 60)
    print("2. 扫描数据库中欧美片记录")
    print("=" * 60)
    db_records = scan_western_db_records()
    print(f"找到 {len(db_records)} 条欧美片数据库记录")
    print()

    # 3. 更新 _downloaded.json
    print("=" * 60)
    print("3. 更新 _downloaded.json")
    print("=" * 60)
    western_post_ids = set()
    for d in western_dirs:
        m = re.search(r'post_(\d+)_', d['dirname'])
        if m:
            western_post_ids.add(m.group(1))
    updated = update_downloaded_json(western_post_ids, dry_run=dry_run)
    print(f"将更新 {updated} 条 _downloaded.json 记录")
    print()

    # 4. 执行删除
    print("=" * 60)
    print("4. 删除离线网页目录")
    print("=" * 60)
    deleted_size = delete_western_dirs(western_dirs, dry_run=dry_run)
    print(f"{'将删除' if dry_run else '已删除'} {len(western_dirs)} 个目录，{deleted_size / 1024 / 1024:.1f} MB")
    print()

    print("=" * 60)
    print("5. 删除数据库记录")
    print("=" * 60)
    deleted_db = delete_western_db_records(db_records, dry_run=dry_run)
    print(f"{'将删除' if dry_run else '已删除'} {deleted_db} 条数据库记录")
    print()

    print("=" * 60)
    print("6. 重新生成索引")
    print("=" * 60)
    regenerate_offline_index()
    print()

    print("=" * 60)
    print("总结")
    print("=" * 60)
    print(f"  离线网页目录: {len(western_dirs)} 个 ({total_size / 1024 / 1024:.1f} MB)")
    print(f"  数据库记录: {len(db_records)} 条")
    print(f"  _downloaded.json: {updated} 条更新")
    if dry_run:
        print()
        print("  这是预览模式。确认无误后运行:")
        print(f"  python cleanup_western.py --execute")
