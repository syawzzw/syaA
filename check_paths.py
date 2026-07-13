import os
import re

exists = 0
not_exists = 0
exists_list = []
not_exists_list = []

with open(r'F:\pycode\SyaA\syaA\invalid_paths_list.txt', 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        # Match paths starting with Z: and ending with .mp4
        m = re.search(r'(Z:[/\\].+\.mp4)', line)
        if m:
            path = m.group(1)
            # Normalize to backslash for Windows
            test_path = path.replace('/', '\\')
            if os.path.exists(test_path):
                exists += 1
                exists_list.append(path)
            else:
                not_exists += 1
                not_exists_list.append(path)

print(f"========== 验证结果 ==========")
print(f"文件存在: {exists}")
print(f"文件不存在: {not_exists}")
print(f"总计检查: {exists + not_exists}")
print()

if not_exists_list:
    print(f"========== 文件不存在的路径 ({len(not_exists_list)}条) ==========")
    for p in not_exists_list:
        print(f"  X {p}")

print()

if exists_list:
    print(f"========== 文件存在的路径 ({len(exists_list)}条) ==========")
    for p in exists_list:
        print(f"  OK {p}")
