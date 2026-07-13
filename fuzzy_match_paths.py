"""
模糊匹配修正失效路径 - 先扫描hhp目录建立索引，再与DB失效路径做匹配
输出：匹配报告 + 可执行的SQL（不自动执行）
"""
import sqlite3
import os
import re
from pathlib import Path
from collections import defaultdict

# ============ 配置 ============
DB_PATH = os.path.join(os.path.dirname(__file__), 'syaA.db')
HHP_BASE = r'Z:\115open\hhp'  # 高分收集根目录

# 分数子目录列表
SCORE_DIRS = ['100分', '95分', '90分', '85分', '80分']

OUTPUT_REPORT = os.path.join(os.path.dirname(__file__), 'path_fix_report.txt')
OUTPUT_SQL = os.path.join(os.path.dirname(__file__), 'path_fix.sql')

# ============ 工具函数 ============

def extract_designation_from_filename(filename: str) -> str | None:
    """从文件名中提取番号（大小写不敏感）"""
    # 常见番号格式：ABC-123, IPZZ-641, FC2PPV-3363283, SSIS-241 等
    # 文件名格式通常是：番号-标题-其他信息.mp4 或 zzz-XXXX 番号-标题.mp4
    name = filename
    
    # 先去掉常见前缀
    for prefix in ['zzz-', '489155.com@']:
        if name.lower().startswith(prefix.lower()):
            name = name[len(prefix):]
    
    # 尝试匹配番号正则（字母+数字+连字符+数字）
    m = re.match(r'^([A-Za-z]{2,}[-]?\d{2,})', name, re.IGNORECASE)
    if m:
        return m.group(1).upper()  # 统一转大写
    return None


def normalize_designation(raw: str) -> str:
    """标准化番号用于比较：大写、去空格"""
    return raw.strip().upper()


def build_hhp_index(hhp_base: str, score_dirs: list) -> dict[str, str]:
    """
    扫描 hhp 目录下所有分数子目录中的视频文件，
    返回 {标准化番号: 实际文件完整路径} 的字典
    """
    index = {}
    
    for score_dir in score_dirs:
        dir_path = os.path.join(hhp_base, score_dir)
        if not os.path.isdir(dir_path):
            print(f"  [跳过] 目录不存在: {dir_path}")
            continue
        
        files = [f for f in os.listdir(dir_path) if f.endswith('.mp4')]
        print(f"  [{score_dir}] 找到 {len(files)} 个文件")
        
        for fname in files:
            desig = extract_designation_from_filename(fname)
            if desig:
                full_path = os.path.join(dir_path, fname)
                norm_desig = normalize_designation(desig)
                
                # 如果同一个番号有多个文件，保留第一个找到的
                if norm_desig not in index:
                    index[norm_desig] = full_path
                else:
                    print(f"    [重复] {norm_desig} 已存在，跳过: {fname}")
    
    return index


def get_invalid_records(db_path: str) -> list[dict]:
    """从数据库获取所有 local_path 失效的记录"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
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
            invalid.append({
                'numbers_name': row['numbers_name'],
                'designation': row['designation'],
                'grade': row['grade'],
                'local_path': lp,
                'mosaic': row['mosaic'],
            })
    
    conn.close()
    return invalid


# ============ 主流程 ============

print("=" * 80)
print(" 第一步：扫描 hhp 高分目录建立文件索引")
print("=" * 80)

hhp_index = build_hhp_index(HHP_BASE, SCORE_DIRS)
print(f"\n索引建立完成: 共 {len(hhp_index)} 个唯一番号")

print("\n" + "=" * 80)
print(" 第二步：从数据库读取失效路径记录")
print("=" * 80)

invalid_records = get_invalid_records(DB_PATH)
print(f"共 {len(invalid_records)} 条失效路径记录\n")

print("\n" + "=" * 80)
print(" 第三步：执行模糊匹配")
print("=" * 80)

matched = []      # 匹配成功
unmatched = []     # 未匹配到
ambiguous = []     # 需要人工确认的

for rec in invalid_records:
    db_desig = normalize_designation(rec['designation'] or '')
    
    # 也尝试从文件名中提取番号（有些记录的 designation 可能是 zzz-1186 这种）
    fname = os.path.basename(rec['local_path'] or '')
    fname_desig = extract_designation_from_filename(fname) or ''
    fname_desig_norm = normalize_designation(fname_desig)
    
    # 优先用 DB 的 designation 匹配
    found_path = None
    match_source = ''
    
    if db_desig and db_desig in hhp_index:
        found_path = hhp_index[db_desig]
        match_source = f"DB番号[{db_desig}]"
    elif fname_desig_norm and fname_desig_norm in hhp_index:
        found_path = hhp_index[fname_desig_norm]
        match_source = f"文件名番号[{fname_desig_norm}]"
    
    if found_path:
        matched.append({**rec, 'new_path': found_path, 'match_source': match_source})
    else:
        unmatched.append(rec)

# ============ 输出报告 ============

report_lines = []
report_lines.append("=" * 100)
report_lines.append(f" 路径模糊匹配修复报告")
report_lines.append(f" 生成时间: 2026-07-12")
report_lines.append(f" HHP 索引覆盖: {len(hhp_index)} 个唯一番号")
report_lines.append(f" DB 失效记录: {len(invalid_records)} 条")
report_lines.append(f" 匹配成功: {len(matched)} 条")
report_lines.append(f" 未匹配: {len(unmatched)} 条")
report_lines.append("=" * 100)
report_lines.append("")

if matched:
    report_lines.append(f"{'='*100}")
    report_lines.append(f" ✅ 匹配成功 ({len(matched)} 条) — 将更新为 hhp 中的实际路径")
    report_lines.append(f"{'='*100}")
    report_lines.append("")
    report_lines.append(f"{'DB番号':<16} {'评分':>4} {'匹配来源':<22} {'新路径'}")
    report_lines.append(f"{'-'*100}")
    
    for m in matched:
        new_p = m['new_path']
        display = new_p if len(new_p) <= 70 else new_p[:35] + '...' + new_p[-30:]
        grade = f"{m['grade']:.0f}" if m['grade'] is not None else '-'
        report_lines.append(
            f"{(m['designation'] or ''):<16} {grade:>4} {m['match_source']:<22} {display}"
        )
    
    report_lines.append("")

if unmatched:
    report_lines.append(f"{'='*100}")
    report_lines.append(f" ❌ 未匹配 ({len(unmatched)} 条) — 在 hhp 中未找到对应文件")
    report_lines.append(f"   建议: 清空 local_path (设为 NULL)")
    report_lines.append(f"{'='*100}")
    report_lines.append("")
    report_lines.append(f"{'DB番号':<16} {'评分':>4} {'原路径'}")
    report_lines.append(f"{'-'*100}")
    
    for u in unmatched:
        old_p = u['local_path'] or ''
        display = old_p if len(old_p) <= 70 else old_p[:35] + '...' + old_p[-30:]
        grade = f"{u['grade']:.0f}" if u['grade'] is not None else '-'
        report_lines.append(
            f"{(u['designation'] or ''):<16} {grade:>4} {display}"
        )

report_lines.append("")
report_lines.append("=" * 100)
report_lines.append(" 【分类统计】")
report_lines.append("=" * 100)

# 按原路径前缀统计匹配情况
stats = defaultdict(lambda: {'total': 0, 'matched': 0})
for m in matched:
    lp = m['local_path']
    if lp.startswith('Z:\\115open\\hhp') or '/hhp' in lp.replace('\\', '/'):
        key = 'hhp高分目录'
    elif 'zzz-' in lp:
        key = 'zzz标记'
    else:
        key = 'Hp主目录'
    stats[key]['total'] += 1
    stats[key]['matched'] += 1

for u in unmatched:
    lp = u['local_path']
    if lp.startswith('Z:\\115open\\hhp') or '/hhp' in lp.replace('\\', '/'):
        key = 'hhp高分目录'
    elif 'zzz-' in lp:
        key = 'zzz标记'
    else:
        key = 'Hp主目录'
    stats[key]['total'] += 1

for key, val in sorted(stats.items()):
    report_lines.append(f"  {key}: 共 {val['total']} 条, 匹配 {val.get('matched', 0)} 条, 未匹配 {val['total'] - val.get('matched', 0)} 条")

# 写入报告文件
with open(OUTPUT_REPORT, 'w', encoding='utf-8') as f:
    f.write('\n'.join(report_lines))
    f.write('\n')

print('\n'.join(report_lines))
print(f"\n报告已写入: {OUTPUT_REPORT}")

# ============ 生成 SQL ============

sql_lines = []
sql_lines.append("-- ======================================================")
sql_lines.append("-- 自动生成的路径修复SQL (由 fuzzy_match_paths.py 生成)")
sql_lines.append("-- 生成时间: 2026-07-12")
sql_lines.append("-- 匹配成功: {} 条 | 未匹配(清空): {} 条".format(len(matched), len(unmatched)))
sql_lines.append("-- ⚠️  请先检查报告确认无误后再执行！")
sql_lines.append("-- ======================================================")
sql_lines.append("")
sql_lines.append("BEGIN TRANSACTION;")
sql_lines.append("")

if matched:
    sql_lines.append("-- ---------- 匹配成功: 更新为 hhp 实际路径 ----------")
    for m in matched:
        new_path = m['new_path'].replace('\\', '\\\\')  # SQL 转义反斜杠
        sql_lines.append(
            "UPDATE av SET local_path = '{}' WHERE numbers_name = '{}';"
            .format(new_path, m['numbers_name'])
        )
    sql_lines.append("")

if unmatched:
    sql_lines.append("-- ---------- 未匹配: 清空失效路径 ----------")
    for u in unmatched:
        sql_lines.append(
            "UPDATE av SET local_path = NULL WHERE numbers_name = '{}';"
            .format(u['numbers_name'])
        )
    sql_lines.append("")

sql_lines.append("COMMIT;")

with open(OUTPUT_SQL, 'w', encoding='utf-8') as f:
    f.write('\n'.join(sql_lines))
    f.write('\n')

print(f"\nSQL已写入: {OUTPUT_SQL}")
print(f"\n⚠️  请先查看 {os.path.basename(OUTPUT_REPORT)} 确认匹配结果正确后，再决定是否执行 SQL！")
