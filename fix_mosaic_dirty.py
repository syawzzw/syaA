"""修复 mosaic 脏数据 - 增强版 LIVE 模式

策略优先级：
1. 从本地文件名提取（最准确）
2. 从 numbers_name 后缀判断：-UC/-C 结尾 → 无码
3. 从原始脏数据值本身提取：包含"有码"/"无码"关键词
4. 从番号前缀推断：FC2PPV → 无码
"""
import sqlite3
import os
import re

DB_PATH = os.path.join(os.path.dirname(__file__), 'syaA.db')

def get_local_path_from_record(rec):
    """从记录中获取本地文件路径（优先用 magnet_extra）"""
    local_path = rec['local_path'] or ''
    magnet_extra = rec.get('magnet_extra') or ''
    
    # 如果主路径存在，直接返回
    if local_path and os.path.exists(local_path):
        return local_path
    
    # 尝试从 magnet_extra 中提取备用路径
    if magnet_extra:
        for line in magnet_extra.split('\n'):
            line = line.strip()
            m = re.match(r'\[local_path:[^\]]*\]\s+(.+?)\|\|\|(.+)', line)
            if m:
                backup_path = m.group(2).strip()
                if backup_path and os.path.exists(backup_path):
                    return backup_path
    
    return None

def extract_mosaic_from_filename(filepath):
    """从文件名中提取码制信息"""
    if not filepath:
        return None, None
    
    filename = os.path.basename(filepath)
    
    # 常见无码关键词（更全面的列表）
    uncensored_patterns = [
        r'无码', r'uncensored', r'uncen', r'\buc\b', 
        r'无修正', r'无码破解', r'无修正破解'
    ]
    # 常见有码关键词
    censored_patterns = [
        r'有码', r'censored', r'mosaic'
    ]
    
    filename_lower = filename.lower()
    
    for pattern in uncensored_patterns:
        if re.search(pattern, filename_lower, re.IGNORECASE):
            return '无码', pattern
    
    for pattern in censored_patterns:
        if re.search(pattern, filename_lower, re.IGNORECASE):
            return '有码', pattern
    
    return None, None

def guess_mosaic_from_numbers_name(numbers_name):
    """从 numbers_name 推断码制"""
    if not numbers_name:
        return None, None
    
    name_upper = numbers_name.upper()
    
    # -UC 或 -C 结尾 → 无码（这是去重标记）
    if re.search(r'-UC$', name_upper) or re.search(r'-C$', name_upper):
        return '无码', 'suffix_UC/C'
    
    # FC2PPV 番号 → 通常是无码/素人
    if re.match(r'^FC2PPV-', name_upper):
        return '无码', 'prefix_FC2PPV'
    
    # 259LUXU / 300MIUM / 390JAC 等素人番号 → 无码
    amateur_prefixes = ['259LUXU', '300MIUM', '390JAC', '420HOI', '459TEN']
    for prefix in amateur_prefixes:
        if name_upper.startswith(prefix):
            return '无码', f'prefix_{prefix}'
    
    return None, None

def extract_mosaic_from_dirty_value(dirty_value):
    """从脏数据值本身提取码制信息（这些是 HTML 残留）"""
    if not dirty_value:
        return None, None
    
    value_str = str(dirty_value)
    
    # 匹配 "【是否有码】：有码" 或 "【是否有码】：无码"
    m = re.search(r'【是否有码】[：:]\s*(有码|无码)', value_str)
    if m:
        return m.group(1), 'html_dirty_value'
    
    # 匹配独立的 有码/无码 关键词
    if '无码' in value_str and '有码' not in value_str:
        return '无码', 'dirty_contains_无码'
    elif '有码' in value_str and '无码' not in value_str:
        return '有码', 'dirty_contains_有码'
    
    # 如果同时包含两者，看哪个在前面（通常是有码为主）
    if '有码' in value_str and '无码' in value_str:
        pos_y = value_str.index('有码')
        pos_w = value_str.index('无码')
        if pos_w < pos_y:
            return '无码', 'dirty_prefer_无码'
        else:
            return '有码', 'dirty_prefer_有码'
    
    return None, None

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("=" * 70)
    print(" mosaic 脏数据清理 - 增强版 LIVE 模式")
    print("=" * 70)
    
    # 统计
    cursor.execute("""
        SELECT COUNT(*) FROM av 
        WHERE mosaic NOT IN ('有码', '无码')
    """)
    total_dirty = cursor.fetchone()[0]
    print(f"\n待处理脏数据: {total_dirty} 条\n")
    
    # 获取所有被污染的记录
    cursor.execute("""
        SELECT numbers_name, designation, mosaic, local_path, magnet_extra 
        FROM av 
        WHERE mosaic NOT IN ('有码', '无码')
    """)
    dirty_records = cursor.fetchall()
    
    stats = {
        'from_file': 0,      # 从文件名提取
        'from_suffix': 0,    # 从后缀推断
        'from_value': 0,     # 从脏值提取
        'from_prefix': 0,    # 从番号前缀推断
        'no_source': 0,      # 完全无法判断
        'error': 0
    }
    fixes = []
    failures = []
    
    for rec in dirty_records:
        try:
            numbers_name = rec['numbers_name']
            old_mosaic = rec['mosaic']
            new_mosaic = None
            method = None
            
            # === 策略1: 从本地文件名提取（最可靠）===
            filepath = get_local_path_from_record(dict(rec))
            if filepath:
                new_mosaic, method = extract_mosaic_from_filename(filepath)
                if new_mosaic:
                    stats['from_file'] += 1
            
            # === 策略2: 从 numbers_name 后缀推断 ===
            if not new_mosaic:
                new_mosaic, method = guess_mosaic_from_numbers_name(numbers_name)
                if new_mosaic:
                    stats['from_suffix' if 'suffix' in method else 'from_prefix'] += 1
            
            # === 策略3: 从脏数据值本身提取 ===
            if not new_mosaic:
                new_mosaic, method = extract_mosaic_from_dirty_value(old_mosaic)
                if new_mosaic:
                    stats['from_value'] += 1
            
            # 执行修复或记录失败
            if new_mosaic:
                cursor.execute(
                    "UPDATE av SET mosaic = ? WHERE numbers_name = ?",
                    (new_mosaic, numbers_name)
                )
                fixes.append({
                    'designation': rec['designation'] or numbers_name[:20],
                    'old': old_mosaic[:40] + '...' if len(str(old_mosaic)) > 40 else old_mosaic,
                    'new': new_mosaic,
                    'method': method
                })
            else:
                stats['no_source'] += 1
                failures.append({
                    'name': numbers_name,
                    'mosaic': old_mosaic[:60]
                })
                
        except Exception as e:
            stats['error'] += 1
            print(f"  ❌ 错误: {rec['numbers_name']} | {e}")
    
    conn.commit()
    
    # 输出结果
    print("=" * 70)
    print(" 【修复完成】")
    print("=" * 70)
    print(f"  ✅ 从文件名提取: {stats['from_file']} 条")
    print(f"  ✅ 从后缀(-UC/-C): {stats['from_suffix']} 条")
    print(f"  ✅ 从番号前缀:   {stats['from_prefix']} 条")
    print(f"  ✅ 从脏数据值:   {stats['from_value']} 条")
    print(f"  ────────────────────────────────")
    total_fixed = stats['from_file'] + stats['from_suffix'] + stats['from_prefix'] + stats['from_value']
    print(f"  📊 总计已修复:   {total_fixed} 条")
    print(f"  ⚠️ 无法判断:     {stats['no_source']} 条 (保留原值)")
    print(f"  ❌ 错误:         {stats['error']} 条")
    
    if fixes:
        print(f"\n【修复详情 - 按方法分组】")
        
        # 按方法分组展示
        by_method = {}
        for f in fixes:
            method_key = f['method']
            if method_key not in by_method:
                by_method[method_key] = []
            by_method[method_key].append(f)
        
        for method, items in sorted(by_method.items(), key=lambda x: -len(x[1])):
            print(f"\n  📌 via {method} ({len(items)} 条)")
            for item in items[:10]:
                print(f"     {item['designation']:<20} | {item['old']!r:>25} → {item['new']}")
            if len(items) > 10:
             print(f"     ... 还有 {len(items)-10} 条")
    
    if failures:
        print(f"\n⚠️ 无法判断的记录 (共 {len(failures)} 条):")
        for f in failures[:15]:
            print(f"  {f['name']:<30} | mosaic={f['mosaic']!r}")
        if len(failures) > 15:
            print(f"  ... 还有 {len(failures)-15} 条")
    
    # 验证
    cursor.execute("""
        SELECT COUNT(*) FROM av 
        WHERE mosaic NOT IN ('有码', '无码')
    """)
    remaining = cursor.fetchone()[0]
    print(f"\n【验证】剩余脏数据: {remaining} 条")
    
    # 显示剩余脏数据的分布
    if remaining > 0:
        cursor.execute("""
            SELECT mosaic, COUNT(*) as cnt 
            FROM av 
            WHERE mosaic NOT IN ('有码', '无码') 
            GROUP BY mosaic ORDER BY cnt DESC LIMIT 10
        """)
        rows = cursor.fetchall()
        print("  剩余分布:")
        for row in rows:
            val = row['mosaic']
            display_val = (val[:50] + '...') if len(str(val)) > 50 else val
            print(f"    {display_val!r}: {row['cnt']} 条")
    
    conn.close()

if __name__ == '__main__':
    main()
