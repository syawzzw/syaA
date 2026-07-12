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

# 测试问题文件名
test = '[中文字幕]Blacked.18.03.01.Evelyn.Claire-C'
print(f'文件名: {test}')
print(f'  is_western(fname):       {is_western_designation(test)}')
print(f'  is_western(fname_no_ext): {is_western_designation(test)}')
print(f'  des_lower: {test.lower()}')
print(f'  startswith blacked: {test.lower().startswith("blacked")}')
# 问题在于 [中文字幕] 前缀导致 startswith("blacked") 为 False

# 扫描 Hp 目录，找出所有带 [中文字幕] 前缀但实际是欧美的文件
video_exts = ('.mp4', '.avi', '.mkv', '.wmv', '.flv', '.mov', '.m4v', '.ts', '.webm')
hp_path = 'Z:/115open/Hp'

# 策略：去掉常见前缀后再判断
prefix_tags = ['[中文字幕]', '[无码]', '[高清]', '[原档]', '[破解]', '[字幕]', '[无码破解]', '[FC2]', '489155.com@']

missed = []
for f in os.listdir(hp_path):
    fp = os.path.join(hp_path, f)
    if not os.path.isfile(fp) or not f.lower().endswith(video_exts):
        continue
    # 原始判断
    fname_no_ext = os.path.splitext(f)[0]
    if is_western_designation(f) or is_western_designation(fname_no_ext):
        continue  # 已被识别
    # 去掉前缀后再判断
    cleaned = f
    for tag in prefix_tags:
        if cleaned.startswith(tag):
            cleaned = cleaned[len(tag):].strip()
    cleaned_no_ext = os.path.splitext(cleaned)[0]
    if is_western_designation(cleaned) or is_western_designation(cleaned_no_ext):
        size = os.path.getsize(fp)
        missed.append((f, size))

def fmt_size(n):
    if n >= 1024**3:
        return f'{n/1024**3:.2f} GB'
    elif n >= 1024**2:
        return f'{n/1024**2:.2f} MB'
    else:
        return f'{n/1024:.1f} KB'

print(f'\n=== 漏网欧美视频 (去掉前缀后命中) ===')
print(f'共 {len(missed)} 个, 总大小 {fmt_size(sum(s for _, s in missed))}')
for f, s in missed:
    print(f'  [{fmt_size(s):>10}] {f[:80]}')
