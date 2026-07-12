import os, re

def is_western_designation(designation):
    if not designation:
        return False
    des = designation.strip()
    des_lower = des.lower()
    if re.match(r'^[A-Z]{2,6}-\d{2,6}', des):
        return False
    if re.match(r'^FC2', des, re.IGNORECASE):
        return False
    if re.match(r'^[a-z]{3,}\.\d{2}\.\d{2}', des_lower):
        return True
    if re.match(r'^[a-z]{4,}\.', des_lower):
        return True
    if re.match(r'^\d{5,}$', des):
        return True
    western_brands = [
        'brazzers', 'bangbros', 'realitykings', 'naughtyamerica', 'mofos',
        'deeper', 'vixen', 'tushy', 'blacked', 'blackedraw', 'tushyraw',
        'evilangel', 'wicked', 'sweetheart', 'girlsway', 'adulttime',
        'bangbrosclips', 'bangbus', 'bbcpie', 'babes',
        'allanal', 'analvids', 'analmom', 'analonly',
        'bigtitcreampie', 'bananafever', 'archangel',
        'daddy4k', 'cum4k', 'tiny4k', 'holed', 'exotic4k',
        'puremature', 'pornpros', 'passion-hd',
        'shoplyfter', 'shoplyft', 'mylf', 'pervmom', 'pervcity',
        'sislovesme', 'brolovesme', 'daughterswap', 'momswap', 'dadcrush',
        'sexart', 'joymii', 'thewhiteboxxx', 'porndoe', 'letsdoeit',
        'fakehub', 'fakehostel', 'propertysex', 'publicsex',
        'clubseventeen', 'julesjordan', 'teamskeet',
        'helplessteens', 'hussie', 'hussiemit', 'aziani',
        'castingcouch-x', 'backroomcastingcouch', 'netgirl', 'netvideo',
        'blacked-', 'blackedraw-', 'tushy-', 'tushyraw-', 'vixen-',
        'deeper-', 'bangbros-', 'bangbus-',
    ]
    for brand in western_brands:
        if des_lower.startswith(brand):
            return True
    if re.match(r'^[A-Z][a-z]+(\s+[A-Z][a-z]+){2,}', des):
        if not re.search(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff]', des):
            return True
    western_indicators = [
        'stepmom', 'stepdad', 'step-mom', 'step-dad',
        'step-sister', 'step-brother', 'stepsister', 'stepbrother',
        'mommy', 'milf', 'daddy4k',
    ]
    for w in western_indicators:
        if w in des_lower:
            return True
    return False

video_exts = ('.mp4', '.avi', '.mkv', '.wmv', '.flv', '.mov', '.m4v', '.ts', '.webm')
prefix_tags = ['[中文字幕]', '[无码]', '[高清]', '[原档]', '[破解]', '[字幕]', '[无码破解]', '[FC2]', '489155.com@']

hp_path = 'Z:/115open/Hp'
to_delete = []

for f in os.listdir(hp_path):
    fp = os.path.join(hp_path, f)
    if not os.path.isfile(fp) or not f.lower().endswith(video_exts):
        continue
    fname_no_ext = os.path.splitext(f)[0]
    # 原始判断
    if is_western_designation(f) or is_western_designation(fname_no_ext):
        continue  # 已被识别（不会到这里，之前已删）
    # 去掉前缀后再判断
    cleaned = f
    for tag in prefix_tags:
        if cleaned.startswith(tag):
            cleaned = cleaned[len(tag):].strip()
    cleaned_no_ext = os.path.splitext(cleaned)[0]
    if is_western_designation(cleaned) or is_western_designation(cleaned_no_ext):
        to_delete.append(fp)

total = len(to_delete)
total_size = sum(os.path.getsize(fp) for fp in to_delete)

def fmt_size(n):
    if n >= 1024**4:
        return f'{n/1024**4:.2f} TB'
    elif n >= 1024**3:
        return f'{n/1024**3:.2f} GB'
    elif n >= 1024**2:
        return f'{n/1024**2:.2f} MB'
    else:
        return f'{n/1024:.1f} KB'

print(f'待删除漏网欧美文件: {total} 个, {fmt_size(total_size)}')
print('开始删除...')

deleted = 0
failed = 0
for i, fp in enumerate(to_delete):
    try:
        os.remove(fp)
        deleted += 1
        if (i + 1) % 50 == 0:
            print(f'  进度: {i+1}/{total}')
    except Exception as e:
        failed += 1
        print(f'  [失败] {os.path.basename(fp)[:60]} | {e}')

print(f'\n删除完成: 成功 {deleted}, 失败 {failed}, 释放 {fmt_size(total_size)}')

# 验证
remaining = [f for f in os.listdir(hp_path) if os.path.isfile(os.path.join(hp_path, f)) and f.lower().endswith(video_exts)]
print(f'Hp目录剩余视频: {len(remaining)}')
