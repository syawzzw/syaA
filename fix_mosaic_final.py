"""修复最后 2 条特殊脏数据并验证最终结果"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'syaA.db')

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# 1. 修复 '有5码' → '有码' (明显是 OCR/输入错误)
cursor.execute("UPDATE av SET mosaic = '有码' WHERE mosaic = '有5码'")
print(f"修复 '有5码' → '有码': {cursor.rowcount} 条")

# 2. 'unknown' 这条需要查看详情决定
cursor.execute("""
    SELECT numbers_name, designation, mosaic, local_path 
    FROM av WHERE mosaic = 'unknown'
""")
row = cursor.fetchone()
if row:
    print(f"\n'munknown' 记录详情:")
    print(f"  numbers_name: {row[0]}")
    print(f"  designation: {row[1]}")
    print(f"  local_path: {row[3]}")
    
    # 检查是否有本地文件
    if row[3] and os.path.exists(row[3]):
        filename = os.path.basename(row[3])
        print(f"  文件名: {filename}")
        # 从文件名判断
        fn_lower = filename.lower()
        if any(kw in fn_lower for kw in ['无码', 'uncen', 'uc', 'uncensored']):
            cursor.execute("UPDATE av SET mosaic = '无码' WHERE numbers_name = ?", (row[0],))
            print(f"  → 已修复为: 无码")
        elif any(kw in fn_lower for kw in ['有码', 'censored']):
            cursor.execute("UPDATE av SET mosaic = '有码' WHERE numbers_name = ?", (row[0],))
            print(f"  → 已修复为: 有码")
        else:
            print(f"  ⚠️ 无法从文件名判断，保持 unknown")
    else:
        # 尝试从番号推断
        name = row[0]
        if '-UC' in name or '-C' in name:
            cursor.execute("UPDATE av SET mosaic = '无码' WHERE numbers_name = ?", (name,))
            print(f"  → 根据后缀修复为: 无码")
        else:
            print(f"  ⚠️ 无源文件且无法推断，保持 unknown")

conn.commit()

# 3. 验证最终结果
print("\n" + "=" * 60)
print(" 【最终验证】")
print("=" * 60)

cursor.execute("""
    SELECT COUNT(*) FROM av 
    WHERE mosaic NOT IN ('有码', '无码')
""")
remaining = cursor.fetchone()[0]
print(f"\n剩余脏数据: {remaining} 条")

# 显示 mosaic 分布
cursor.execute("""
    SELECT mosaic, COUNT(*) as cnt 
    FROM av 
    GROUP BY mosaic 
    ORDER BY cnt DESC
""")
rows = cursor.fetchall()
print('\n当前 mosaic 字段分布:')
total = 0
for row in rows:
    print(f"  {row[0]:<8}: {row[1]:>6,} 条 ({row[1]/31321*100:.1f}%)" if total > 0 else f"  {row[0]:<8}: {row[1]:>6,} 条")
    total += row[1]

print(f"\n{'─'*40}")
print(f"  总计:     {total:,} 条")

conn.close()
