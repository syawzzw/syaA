#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试 is_western_designation 对 Blacked.18.03.01.Evelyn.Claire 的识别"""
import re
import sys
sys.path.insert(0, 'src/url')

# 直接从 gui_app 导入
from gui_app import is_western_designation

test_cases = [
    # (input, expected, description)
    ("Blacked.18.03.01.Evelyn.Claire", True, "用户报告漏网的欧美片"),
    ("Blacked.18.03.01.Evelyn.Claire-C", True, "带-C后缀"),
    ("blacked.18.03.01.evelyn.claire", True, "全小写"),
    ("Blacked.22.03.26.nicole.doshi", True, "另一个欧美片格式"),
    ("Tushy.22.02.27.scarlett.jones", True, "Tushy厂牌"),
    ("Vixen.21.12.30.some.name", True, "Vixen厂牌"),
    ("Deeper.21.12.30.some.name", True, "Deeper厂牌"),
    ("ABP-171", False, "日文番号不应误判"),
    ("SSIS-062", False, "日文番号"),
    ("FC2-PPV-1234567", False, "FC2番号"),
    ("300mium-699", False, "日文番号(数字开头)"),
    ("BlackedRaw.20.05.01.test", True, "BlackedRaw厂牌"),
    ("[中文字幕]Blacked.18.03.01.Evelyn.Claire", True, "带前缀的完整标题"),
]

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
    print()

print(f"--- {passed} passed, {failed} failed ---")
