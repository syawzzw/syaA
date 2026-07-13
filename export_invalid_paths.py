"""导出所有失效路径的完整列表（148条）"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'syaA.db')
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), 'invalid_paths_list.txt')

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# 查询所有有 local_path 的记录
cursor.execute("""
    SELECT numbers_name, designation, grade, local_path, mosaic
    FROM av 
    WHERE local_path IS NOT NULL AND local_path != '' AND local_path != 'None'
    ORDER BY designation
""")

rows = cursor.fetchall()
invalid = []

for row in rows:
    lp = row['local_path']
    if lp and not os.path.exists(lp):
        invalid.append(row)

# 写入文件并输出到控制台
lines = []
lines.append(f"{'='*120}")
lines.append(f" 失效本地路径完整列表 (共 {len(invalid)} 条)")
lines.append(f" 检查时间: 2026-07-12")
lines.append(f"{'='*120}")
lines.append('')
lines.append(f"{'番号':<16} {'评分':>4} {'码制':<6} {'路径'}")
lines.append(f"{'-'*120}")

for r in invalid:
    lp = r['local_path'] or ''
    # 截断过长的路径显示
    display_path = lp if len(lp) <= 85 else lp[:42] + '...'+lp[-40:]
    grade = f"{r['grade']:.0f}" if r['grade'] is not None else '-'
    mosaic = (r['mosaic'] or '-')[:6]
    
    lines.append(f"{(r['designation'] or ''):<16} {grade:>4} {mosaic:<6} {display_path}")

# 分类统计
lines.append('')
lines.append(f"{'='*120}")
lines.append(" 【分类统计】")
lines.append(f"{'='*120}")

# 按路径前缀分类
prefix_stats = {}
for r in invalid:
    lp = r['local_path'] or ''
    if lp.startswith('Z:/115open/Hp/'):
        prefix = 'Z:/115open/Hp/ (115网盘主目录)'
    elif lp.startswith('Z:\\115open\\hhp'):
        prefix = 'Z:\\115open\\hhp (高分收集目录)'
    elif 'zzz-' in lp:
        prefix = '含 zzz- 前缀 (标记文件)'
    elif '&nbsp;' in lp or '&amp;' in lp:
        prefix = '含 HTML 实体编码'
    else:
        prefix = '其他'
    prefix_stats[prefix] = prefix_stats.get(prefix, 0) + 1

for prefix, count in sorted(prefix_stats.items(), key=lambda x: -x[1]):
    lines.append(f"  {prefix}: {count} 条")

# 内容写入文件
with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))
    f.write('\n')

# 同时输出到控制台
print('\n'.join(lines))
print(f"\n\n已导出到: {OUTPUT_FILE}")

conn.close()
