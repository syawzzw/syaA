#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试脚本：验证 _classify_page_type() 对两个样本文件的分类结果是否正确

样本文件说明:
- post_3598785 (培根): safe反爬验证页 → 应分类为 PAGE_SAFE_BLOCK
- post_3597548 (提示信息): 删帖提示页 → 应分类为 PAGE_DELETED
"""

import os
import sys

# ============================================================
#  页面类型常量（从 gui_app.py 复制，用于独立测试）
# ============================================================
PAGE_NORMAL = "normal"
PAGE_LOGIN_REQUIRED = "login_required"
PAGE_DELETED = "deleted"
PAGE_SAFE_BLOCK = "safe_block"
PAGE_UNKNOWN_SHORT = "unknown_short"


def _is_safe_page(html):
    """检测是否为论坛反爬 safe 验证页（JS验证页）。"""
    if not html:
        return False
    if "static/safe/js/" in html and "safeid" in html:
        return True
    if "mainv2.js" in html and len(html) < 2000:
        return True
    return False


def _extract_title(html):
    """从 HTML 中提取 <title> 标签内容"""
    pos1 = html.find("<title>")
    pos2 = html.find("</title>")
    if pos1 != -1 and pos2 != -1:
        return html[pos1 + 7:pos2].strip()
    return ""


def _classify_page_type(html):
    """
    精确分类页面类型（与 gui_app.py 中的实现保持一致）
    
    核心原则：只有 safe 反爬验证页才算真正的 Cookie 失效需要停止！
    其他异常页面（登录页、删帖、短页面）全部跳过即可。
    """
    if not html:
        return PAGE_UNKNOWN_SHORT

    # ✅ 正常帖子特征 → 直接返回正常
    # 包含 Discuz 帖子列表区域或帖子内容区域
    if "postlist" in html or 'id="post_' in html or "ajaxdialog" in html:
        return PAGE_NORMAL
    # 包含磁力链接格式 → 正常帖子内容
    if "magnet:?xt=urn:btih:" in html:
        return PAGE_NORMAL

    # 🛑 safe验证页 → 这是真正的Cookie失效！
    if _is_safe_page(html):
        return PAGE_SAFE_BLOCK

    # ⚠️ 删帖/不存在提示 → 跳过即可（必须在 id="ct" 检查之前！
    #   因为 Discuz 的删帖/权限提示页也包含 id="ct" 和 viewthread）
    delete_signs = [
        "指定的主题不存在",
        "已被删除",
        "正在被审核",
        "不存在或已被删除",
    ]
    for sign in delete_signs:
        if sign in html:
            return PAGE_DELETED

    # 包含 Discuz 典型帖子 DOM 结构（此时已排除删帖页，可安全判定为正常）
    if 'id="ct"' in html and ("viewthread" in html or "mod=viewthread" in html):
        return PAGE_NORMAL

    # ⚠️ 需要登录的帖子 / 权限不足页面 → 跳过即可
    title = _extract_title(html)
    login_signs = ["member.php?mod=logging", "请先登录", "您需要登录", "loginform"]
    has_login_signs = any(s in html for s in login_signs)

    if has_login_signs and (title == "提示信息" or title.startswith("提示信息")):
        # 进一步区分是"删帖提示"还是"需要登录"
        if any(s in html for s in delete_signs):
            return PAGE_DELETED
        return PAGE_LOGIN_REQUIRED

    # 其他情况根据 title 判断
    if title == "提示信息" or title.startswith("提示信息"):
        if has_login_signs:
            return PAGE_LOGIN_REQUIRED
        return PAGE_DELETED  # 默认归为删帖

    # 服务器错误
    if "502 Bad Gateway" in title or "503 Service" in title:
        return PAGE_DELETED

    # 页面过短但没匹配到任何特征
    if len(html) < 500:
        return PAGE_UNKNOWN_SHORT

    return PAGE_NORMAL  # 兜底：默认当正常处理


def run_tests():
    """运行测试用例"""
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # 样本文件路径
    safe_file = os.path.join(
        base_dir, "..", "..", "output", "离线网页", "其他", "未知日期",
        "post_3598785_培根_培根", "index.html"
    )
    delete_file = os.path.join(
        base_dir, "..", "..", "output", "离线网页", "其他", "未知日期",
        "post_3597548_提示信息 -  98_提示信息 - 98堂[原色花堂] - Powered by",
        "index.html"
    )

    print("=" * 60)
    print("页面类型分类器测试")
    print("=" * 60)
    print()

    all_passed = True

    # ---- 测试1: Safe 验证页（真正的 Cookie 失效）----
    print("-" * 60)
    print("测试1: Safe 反爬验证页 (post_3598785)")
    print("-" * 60)
    try:
        with open(safe_file, 'r', encoding='utf-8') as f:
            safe_html = f.read()

        safe_result = _classify_page_type(safe_html)
        expected = PAGE_SAFE_BLOCK
        passed = (safe_result == expected)

        print("  文件大小: {} 字节".format(len(safe_html)))
        print("  Title: {}".format(_extract_title(safe_html)))
        print("  含 safeid: {}".format("'safeid'" in safe_html))
        print("  含 mainv2.js: {}".format("'mainv2.js'" in safe_html))
        print("  分类结果: {}".format(safe_result))
        print("  期望结果: {}".format(expected))
        print("  状态: {} {}".format("✅ PASS" if passed else "❌ FAIL", "(这是真正的Cookie失效)" if passed else ""))

        if not passed:
            all_passed = False
    except FileNotFoundError:
        print("  ❌ 文件未找到: {}".format(safe_file))
        all_passed = False
    except Exception as e:
        print("  ❌ 异常: {}".format(e))
        all_passed = False

    print()

    # ---- 测试2: 删帖提示页（不是 Cookie 失效！）----
    print("-" * 60)
    print("测试2: 删帖/不存在提示页 (post_3597548)")
    print("-" * 60)
    try:
        with open(delete_file, 'r', encoding='utf-8') as f:
            delete_html = f.read()

        delete_result = _classify_page_type(delete_html)
        expected = PAGE_DELETED
        passed = (delete_result == expected)

        print("  文件大小: {} 字节".format(len(delete_html)))
        print("  Title: {}".format(_extract_title(delete_html)))
        print("  含删帖文字: {}".format("'指定的主题不存在'在HTML中"))
        print("  含登录表单: {}".format("'member.php?mod=logging'在HTML中"))
        print("  分类结果: {}".format(delete_result))
        print("  期望结果: {}".format(expected))
        print("  状态: {} {}".format("✅ PASS" if passed else "❌ FAIL", "(这不是Cookie失效，应跳过)" if passed else ""))

        if not passed:
            all_passed = False
    except FileNotFoundError:
        print("  ❌ 文件未找到: {}".format(delete_file))
        all_passed = False
    except Exception as e:
        print("  ❌ 异常: {}".format(e))
        all_passed = False

    print()

    # ---- 测试3: 边界情况测试 ----
    print("-" * 60)
    print("测试3: 边界情况测试")
    print("-" * 60)

    edge_cases = [
        ("空字符串 (None)", None, PAGE_UNKNOWN_SHORT),
        ("空字符串 ('')", "", PAGE_UNKNOWN_SHORT),
        ("提示信息+请先登录", "<html><head><title>提示信息</title></head><body>您需要登录</body></html>", PAGE_LOGIN_REQUIRED),
        ("提示信息+删帖文字", "<html><head><title>提示信息</title></head><body>指定的主题不存在</body></html>", PAGE_DELETED),
        ("含磁力链接", "<html><body>magnet:?xt=urn:btih:abc123</body></html>", PAGE_NORMAL),
        ("长HTML无特征(兜底normal)", "<html>" + "<p>x</p>" * 100 + "</html>", PAGE_NORMAL),
        ("502错误页", "<html><head><title>502 Bad Gateway</title></head></html>", PAGE_DELETED),
    ]

    for i, (desc, input_data, expected) in enumerate(edge_cases):
        try:
            result = _classify_page_type(input_data)
            passed = (result == expected)

            status = "✅ PASS" if passed else "❌ FAIL"
            print("  [{}] {}: result={} expected={} -> {}".format(i + 1, desc, result, expected, status))

            if not passed:
                all_passed = False
        except Exception as e:
            print("  [{}] {}: ❌ 异常: {}".format(i + 1, desc, e))
            all_passed = False

    print()
    print("=" * 60)
    if all_passed:
        print("🎉 所有测试通过！")
    else:
        print("⚠️  部分测试失败，请检查上面的输出")
    print("=" * 60)

    return all_passed


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
