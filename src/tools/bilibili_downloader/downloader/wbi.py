# -*- coding: utf-8 -*-
"""B站 WBI 签名 & HTTP 请求封装"""

import time
import hashlib
import os
import urllib.parse
from pathlib import Path
from functools import reduce
from typing import Optional, Tuple

try:
    import aiohttp
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "aiohttp", "-q"])
    import aiohttp

# ── WBI 签名混淆表 ───────────────────────────────────────
MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
    27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
    37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4,
    22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 34, 44, 52,
]

# ── 全局 UA ──────────────────────────────────────────────
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)
HEADERS = {
    "User-Agent": UA,
    "Referer": "https://www.bilibili.com",
    "Origin": "https://www.bilibili.com",
}


def _get_base_dir() -> Path:
    """获取程序基础目录"""
    import sys
    if getattr(sys, 'frozen', False):
        import ctypes
        buf = ctypes.create_unicode_buffer(260)
        ctypes.windll.kernel32.GetModuleFileNameW(0, buf, 260)
        return Path(buf.value).parent
    else:
        # 脚本模式：向上找到项目根目录
        return Path(__file__).parent.parent.parent


def load_netscape_cookie_file(filepath: str) -> dict:
    """
    加载 Netscape 格式的 Cookie 文件（浏览器导出格式）

    返回 dict，用于设置到 session cookies
    """
    cookies = {}
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) >= 7:
                name, value = parts[5], parts[6]
                cookies[name] = value
    return cookies


def _auto_load_cookie() -> dict:
    """
    自动查找并加载 Cookie 文件。
    查找顺序：
    1. 基础目录下所有 *cookie*.txt 文件
    2. 基础目录下 cookies.txt
    """
    base = _get_base_dir()
    # 查找 *cookie*.txt
    for f in base.glob("*cookie*.txt"):
        try:
            return load_netscape_cookie_file(str(f))
        except Exception:
            continue
    # 查找 cookies.txt
    for f in base.glob("cookies.txt"):
        try:
            return load_netscape_cookie_file(str(f))
        except Exception:
            continue
    return {}


# ════════════════════════════════════════════════════════
#  WBI 签名
# ════════════════════════════════════════════════════════
class WBISigner:
    """B站 WBI 签名器，自动获取并缓存密钥"""

    def __init__(self):
        self._img_key: Optional[str] = None
        self._sub_key: Optional[str] = None
        self._mixin_key: Optional[str] = None
        self._fetch_time: float = 0
        self._session: Optional[aiohttp.ClientSession] = None
        self._initialized = False

    def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(headers=HEADERS)
            # 自动加载 Cookie 文件
            cookies = _auto_load_cookie()
            if cookies:
                for name, value in cookies.items():
                    self._session.cookie_jar.update_cookies({name: value})
        return self._session

    async def _ensure_initialized(self):
        """首次使用时访问B站主页获取必要的Cookie"""
        if self._initialized:
            return
        session = self._get_session()
        try:
            async with session.get("https://www.bilibili.com", allow_redirects=True) as resp:
                await resp.read()
        except Exception:
            pass
        self._initialized = True

    async def _get_keys(self) -> Tuple[str, str]:
        """从 nav 接口获取 img_key 和 sub_key"""
        now = time.time()
        # 密钥缓存 1 小时
        if self._img_key and (now - self._fetch_time) < 3600:
            return self._img_key, self._sub_key

        # 首次使用先访问主页获取Cookie
        await self._ensure_initialized()

        session = self._get_session()
        async with session.get(
            "https://api.bilibili.com/x/web-interface/nav",
        ) as resp:
            data = await resp.json()

        # 未登录时 code=-101，但 data 中仍有 wbi_img，不需要登录也能获取密钥
        resp_data = data.get("data", {})
        if not resp_data or "wbi_img" not in resp_data:
            raise RuntimeError(f"获取 WBI 密钥失败: {data.get('message', '无 data')}")

        wbi = resp_data["wbi_img"]
        img_url = wbi["img_url"]
        sub_url = wbi["sub_url"]
        self._img_key = img_url.rsplit("/", 1)[1].split(".")[0]
        self._sub_key = sub_url.rsplit("/", 1)[1].split(".")[0]
        self._fetch_time = now
        return self._img_key, self._sub_key

    @staticmethod
    def _get_mixin_key(raw: str) -> str:
        """根据混淆表重排并截取前32字符"""
        return reduce(lambda s, i: s + raw[i], MIXIN_KEY_ENC_TAB, "")[:32]

    async def sign(self, params: dict) -> dict:
        """为请求参数添加 WBI 签名"""
        img_key, sub_key = await self._get_keys()
        mixin_key = self._get_mixin_key(img_key + sub_key)

        params = dict(params)  # 不修改原始 dict
        params["wts"] = int(time.time())
        params = dict(sorted(params.items()))
        # 过滤特殊字符
        params = {
            k: "".join(ch for ch in str(v) if ch not in "!'()*")
            for k, v in params.items()
        }
        query = urllib.parse.urlencode(params)
        w_rid = hashlib.md5((query + mixin_key).encode()).hexdigest()
        params["w_rid"] = w_rid
        return params

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()


# 全局单例
_wbi_signer: Optional[WBISigner] = None


async def get_wbi_signer() -> WBISigner:
    global _wbi_signer
    if _wbi_signer is None:
        _wbi_signer = WBISigner()
    return _wbi_signer


async def close_wbi_signer():
    global _wbi_signer
    if _wbi_signer:
        await _wbi_signer.close()
        _wbi_signer = None
