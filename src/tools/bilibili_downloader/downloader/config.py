# -*- coding: utf-8 -*-
"""配置管理模块"""

import json
from pathlib import Path
from typing import Optional

DEFAULT_SAVE_DIR = "Downloaded"
CONFIG_FILE = "bilibili_config.json"
HISTORY_FILE = "bilibili_history.json"


def get_base_dir() -> Path:
    """获取程序基础目录"""
    import sys
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后
        import ctypes
        buf = ctypes.create_unicode_buffer(260)
        ctypes.windll.kernel32.GetModuleFileNameW(0, buf, 260)
        return Path(buf.value).parent
    else:
        return Path(__file__).parent.parent


def get_config_path() -> Path:
    return get_base_dir() / CONFIG_FILE


def get_history_path() -> Path:
    return get_base_dir() / HISTORY_FILE


def get_default_save_dir() -> Path:
    return get_base_dir() / DEFAULT_SAVE_DIR


def load_config() -> dict:
    """加载配置"""
    path = get_config_path()
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    # 默认配置
    base = get_base_dir()
    return {
        "save_dir": str(get_default_save_dir()),
        "cookie": "",
        "quality": "1080p",
        "folder_style": True,
        "download_cover": True,
        "download_subtitles": False,
        "concurrent": 3,
        "max_videos": 0,
        "proxy": "",
        "order": "pubdate",
    }


def save_config(cfg: dict):
    """保存配置"""
    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def load_history() -> list:
    """加载历史记录"""
    path = get_history_path()
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_history(history: list):
    """保存历史记录"""
    path = get_history_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def add_history_item(url: str, nickname: str = ""):
    """添加历史记录"""
    from datetime import datetime
    history = load_history()

    for item in history:
        if item.get("url") == url:
            item["last_download"] = datetime.now().isoformat()
            if nickname:
                item["nickname"] = nickname
            save_history(history)
            return

    history.append({
        "url": url,
        "nickname": nickname or "未知用户",
        "first_download": datetime.now().isoformat(),
        "last_download": datetime.now().isoformat(),
    })
    save_history(history)


def remove_history_item(url: str):
    """删除历史记录"""
    history = load_history()
    history = [item for item in history if item.get("url") != url]
    save_history(history)
