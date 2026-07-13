import os
import re

# 148条DB记录中的路径
db_paths = {}
with open(r'F:\pycode\SyaA\syaA\invalid_paths_list.txt', 'r', encoding='utf-8') as f:
    for line in f:
        m = re.match(r'^(\S+)\s+(\d+)\s+(\S+)\s+(Z:[\\/].+\.mp4)$', line.strip())
        if m:
            designation = m.group(1)
            path = m.group(4)
            db_paths[designation] = path

# hhp/90分目录实际文件
hhp90_dir = r'Z:\115open\hhp\90分'
hhp90_files = set()
if os.path.exists(hhp90_dir):
    for f in os.listdir(hhp90_dir):
        if f.endswith('.mp4'):
            hhp90_files.add(f)

# 从文件名提取番号（简单规则）
def extract_designation(filename):
    # 去掉各种前缀
    name = filename
    for prefix in ['zzz-', '489155.com@', 'www.98T.la@']:
        if name.startswith(prefix):
            name = name[len(prefix):]
    # 提取番号（字母开头-数字格式）
    m = re.match(r'^([A-Za-z]+-\d+)', name)
    if m:
        return m.group(1).upper()
    return None

print("=" * 80)
print("DB记录在 hhp/90分 的路径 vs 实际文件对比")
print("=" * 80)

# DB中指向 hhp/90分 的记录
db_in_hhp90 = {k: v for k, v in db_paths.items() if 'hhp' in v.lower() and '90' in v}

found = 0
not_found = 0
for des, db_path in sorted(db_in_hhp90.items()):
    fname = os.path.basename(db_path)
    real_des = extract_designation(fname)
    
    # 在 hhp90_files 中搜索匹配的文件
    matched_file = None
    for hf in hhp90_files:
        hd = extract_designation(hf)
        if hd and (hd == des or hd.upper() == des.upper()):
            matched_file = hf
            break
    
    if matched_file:
        print(f"  OK {des}: DB记={fname}")
        print(f"     实际={matched_file}")
        found += 1
    else:
        print(f"  X  {des}: DB记={fname} -> 文件不存在于 hhp/90分")
        not_found += 1

print()
print(f"匹配: {found}, 缺失: {not_found}")

print()
print("=" * 80)
print("hhp/90分 中有但 DB 失效列表中没有的文件（可能路径有效但未被检测）")
print("=" * 80)
all_db_des = set(db_paths.keys())
for hf in sorted(hhp90_files):
    hd = extract_designation(hf)
    if hd and hd not in all_db_des:
        print(f"  ? {hf} (番号: {hd})")

# 也检查其他分数目录
for score_dir in ['100分', '85分', '80分']:
    dir_path = rf'Z:\115open\hhp\{score_dir}'
    if os.path.exists(dir_path):
        files = [f for f in os.listdir(dir_path) if f.endswith('.mp4')]
        print(f"\n=== hhp/{score_dir}: {len(files)} 个文件 ===")
        for f in files:
            hd = extract_designation(f)
            if hd:
                status = "在失效列表中" if hd in all_db_des else "不在失效列表中"
                print(f"  [{status}] {hd} -> {f[:60]}")
