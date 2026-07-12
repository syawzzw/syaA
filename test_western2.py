#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试修复后的 is_western_designation"""
import os, re, sys
sys.path.insert(0, 'src/url')
from gui_app import is_western_designation

# --- 1. 基本用例 ---
test_cases = [
    # 之前漏网的欧美片
    ("Blacked.18.03.01.Evelyn.Claire", True, "Blacked大写开头"),
    ("Beauty4k.25.08.03.dragon.fruit", True, "Beauty4k大写开头"),
    ("Hunt4k.24.03.04.maya.sinn", True, "Hunt4k大写开头"),
    ("Cuck4k.23.12.18.hazel.moore", True, "Cuck4k大写开头"),
    ("489155.com@tushy.16.06.30.anya.olsen", True, "水印前缀+tushy"),
    ("489155.com@vixen.18.04.04.meggan.mallone.4k", True, "水印前缀+vixen"),
    ("b.15.10.08.jade.nile.and.chanel.preston", True, "短前缀b."),
    ("dm.19.03.19.michele.james", True, "短前缀dm."),
    ("nb.16.09.19.alexa.grace.4k", True, "短前缀nb."),
    ("gdp.e242.18.years.old.4k", True, "短前缀gdp."),
    ("pc.20.10.12.blake.blossom", True, "短前缀pc."),
    ("jp.18.07.09.emily.willis", True, "短前缀jp."),
    ("SinfulXXX.26.06.04.Angelica", True, "SinfulXXX厂牌"),
    ("Dorcelclub.26.05.25.emily.pink", True, "Dorcelclub厂牌"),
    ("ImmoralLive.26.06.17", True, "ImmoralLive厂牌"),
    ("BrattyMILF 26 06 13 Jessica", True, "BrattyMILF厂牌"),
    ("ToughLoveX.19.12.26.Andi.James", True, "ToughLoveX厂牌"),
    ("NewSensations.24.09.21.aviana", True, "NewSensations厂牌"),
    ("MyFriendsHotMom.25.01.28", True, "MyFriendsHotMom厂牌"),
    ("KinkyFamily.19.11.20.Kyler.Quinn", True, "KinkyFamily厂牌"),
    ("MyFamilyPies.20.02.02.Chloe", True, "MyFamilyPies厂牌"),
    ("PrincessCum.22.07.01.Alyx.Star", True, "PrincessCum厂牌"),
    ("LegalPorno.23.07.25.Anna.De.Ville", True, "LegalPorno厂牌"),
    ("Bellesaplus.e222.melody.marks", True, "Bellesaplus厂牌"),
    # 日文片不应误判
    ("ABP-171", False, "日文番号"),
    ("SSIS-062", False, "日文番号"),
    ("FC2-PPV-1234567", False, "FC2番号"),
    ("FC2PPV-2800788", False, "FC2PPV番号"),
    ("300mium-699", False, "日文番号数字开头"),
    ("116shh-024", False, "日文番号"),
    ("435mfc-111", False, "日文番号"),
    ("SSIS-189", False, "日文番号"),
    ("IPZZ-435", False, "日文番号"),
    ("FSDSS-361", False, "日文番号"),
    ("START-255", False, "日文番号"),
    ("CWPBD-097", False, "日文番号"),
]

print("=" * 60)
print("基本测试用例")
print("=" * 60)
passed = 0
failed = 0
for des, expected, desc in test_cases:
    result = is_western_designation(des)
    status = "PASS" if result == expected else "FAIL"
    if result == expected:
        passed += 1
    else:
        failed += 1
        print(f"[{status}] {desc}")
        print(f"  input:    {des}")
        print(f"  expected: {expected}, got: {result}")
print(f"{passed} passed, {failed} failed")
print()

# --- 2. 对 Hp 目录全面测试 ---
print("=" * 60)
print("Hp 目录全面测试")
print("=" * 60)
files = sorted(os.listdir('Z:/115open/Hp'))
western_files = []
non_western_files = []
for f in files:
    name = os.path.splitext(f)[0]
    if is_western_designation(name):
        western_files.append(f)
    else:
        non_western_files.append(f)

print(f"总文件: {len(files)}")
print(f"识别为欧美: {len(western_files)}")
print(f"未识别为欧美: {len(non_western_files)}")
print()

# 检查未识别的里面有没有漏网的欧美片
print("--- 未识别为欧美的文件（检查是否有漏网）---")
suspicious = []
for f in non_western_files:
    name = os.path.splitext(f)[0].lower()
    # 这些前缀几乎确定是欧美
    western_hints = ['4k.', 'gloryhole', 'nfbusty', 'therealworkout', 'beauty4k',
                     'bride4k', 'cuck4k', 'debt4k', 'facials4k', 'hunt4k',
                     'loan4k', 'mature4k', 'pie4k', 'rim4k', 'swap4k', 'tutor4k',
                     'tushy', 'vixen', 'blacked', 'deeper', 'brazzers', 'bangbros',
                     'gdp', 'familystrokes', 'doctoradventures', 'pure18',
                     'immorallive', 'brattymilf', 'toughlovex', 'sinfulxxx',
                     'dorcelclub', 'newsensations', 'legallporno', 'private.',
                     'roccosiffredi', 'bellesaplus', 'princesscum',
                     'kinkyfamily', 'myfamilypies', 'myfriendshotmom',
                     'anissa kate', 'ava sinclaire', 'lolly small', 'adelle unicorn']
    for hint in western_hints:
        if hint in name:
            suspicious.append(f)
            break

if suspicious:
    print(f"  可疑漏网: {len(suspicious)} 个")
    for f in suspicious:
        print(f"    {f}")
else:
    print("  无明显漏网 ✓")

print()
print("--- 未识别文件列表（前30个）---")
for f in non_western_files[:30]:
    print(f"  {f}")
if len(non_western_files) > 30:
    print(f"  ... 还有 {len(non_western_files) - 30} 个")
