"""
syaA GUI 统一界面
基于 getUrl.py 所有功能重写的 Tkinter GUI 应用
所有耗时操作均在子线程中运行，不会阻塞 UI
"""

import requests
import requests.adapters as adapters
import re
import time
import sqlite3
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import shutil
import queue
import json
import random
import math
import io



# ============================================================
#  全局配置
# ============================================================

# 配置文件路径
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "gui_config.json")

# 默认配置（首次启动或配置文件丢失时使用）
DEFAULT_CONFIG = {
    "base_url": "plwt.kpqq4.com",
    "crawl_begin": "3369770",
    "crawl_end": "3380551",
    "crawl_threads": "10",
    "cookie_path": "F:/workbuddy/视频下载器_tengxun/10dd.7qxz7.net_cookies.txt",
    "db_115_path": "Z:/115open/Hp/",
    "file_path": "Z:/115open/云下载/",
    "small_file_mb": "50",
    "file_dst_path": "Z:/115open/Hp/",
    "low_grade_val": "50",
    "keyword_val": "",
    "collect_grade": "90",
    "collect_dst_path": "",
    "book_root": "https://www.sudugu.org/",
    "book_start": "45",
    "book_end": "99999",
    "theme": "light",
    "window_geometry": "",
}

# ============================================================
#  主题配色方案（功能12：暗色主题）
# ============================================================
THEMES = {
    "light": {
        "bg": "#F0F0F0",
        "fg": "#000000",
        "frame_bg": "#F0F0F0",
        "text_bg": "#FFFFFF",
        "text_fg": "#000000",
        "button_bg": "#E1E1E1",
        "button_fg": "#000000",
        "entry_bg": "#FFFFFF",
        "entry_fg": "#000000",
        "log_bg": "#FFFFFF",
        "log_fg": "#000000",
        "separator": "#C0C0C0",
        "accent": "#3366CC",
        "section_title": "#3366CC",
        "tag_black": "#CC3333",
        "tag_good": "#00AA00",
        "tag_none": "#888888",
    },
    "dark": {
        "bg": "#1E1E1E",
        "fg": "#D4D4D4",
        "frame_bg": "#252526",
        "text_bg": "#1E1E1E",
        "text_fg": "#D4D4D4",
        "button_bg": "#3C3C3C",
        "button_fg": "#D4D4D4",
        "entry_bg": "#3C3C3C",
        "entry_fg": "#D4D4D4",
        "log_bg": "#1E1E1E",
        "log_fg": "#D4D4D4",
        "separator": "#555555",
        "accent": "#569CD6",
        "section_title": "#569CD6",
        "tag_black": "#F44747",
        "tag_good": "#6A9955",
        "tag_none": "#808080",
    },
}

# 小说下载索引文件（记录每本书的已下载状态，用于增量更新）
BOOK_INDEX_FILE = os.path.join(".", "output", "book", "book_index.json")


def load_config():
    """加载配置文件，返回字典"""
    config_path = os.path.normpath(CONFIG_FILE)
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                saved = json.load(f)
            # 合并：已保存的值覆盖默认值，新增字段用默认值
            merged = dict(DEFAULT_CONFIG)
            merged.update(saved)
            return merged
        except Exception:
            pass
    return dict(DEFAULT_CONFIG)


def save_config(config_dict):
    """保存配置到文件"""
    config_path = os.path.normpath(CONFIG_FILE)
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_dict, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

# SQLite 数据库路径（放云盘上，其他电脑也能访问）
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "syaA.db")

# 115 文件白名单
WHITE_LIST = ["电脑文件备份", "本地照片视频库", "手机备份", "手机相册"]

# 垃圾文件名列表
DEL_FILE_NAME_LIST = [
    "x u u 6 2 . c o m.mp4",
    "台 妹 子 線 上 現 場 直 播 各 式 花 式 表 演.mp4",
    "最 新 位 址 獲 取.txt",
    "社 區 最 新 情 報.mp4",
    "聚 合 全 網 H 直 播.html",
    "uur9 3.com.mp4",
    "鮑_魚_直_播_盒_子_，聚_合_全_网_H_直_播_和_高_清_視_頻.html",
    "新 片 首 發 每 天 更 新 同 步 日 韓.mp4",
    "最 新 位 址 獲 取.txt",
    "楼风最全资源.html",
    "安卓二维码.png",
    "鲍鱼直播盒子，免费探花直播和高清视频.html",
    "社区最新情报.mp4",
    "有趣的台湾妹妹直播.mp4",
    "最新地址获取.txt",
    "有 趣 的 臺 灣 妹 妹 直 播.mp4",
    "社 區 最 新 情 報(1).mp4",
    "鮑 魚 直 播 盒 子，免 費 探 花 直 播 和 高 清 視 頻(1).html",
    "有 趣 的 臺 灣 妹 妹 直 播(1).mp4",
    "最 新 位 址 獲 取(1).txt",
]

# ============================================================
#  数据库工具函数
# ============================================================

# 显式列名常量，避免 SELECT * 导致的列索引偏移问题
AV_COLUMNS = "numbers_name, name, magnet, hot_num, performer, size, mosaic, view, reply, designation, film_name, grade, exist_in_115, local_path, zzz, created_at, updated_at, last_action"
# 列索引常量，按 AV_COLUMNS 顺序
IDX_NUMBERS_NAME = 0
IDX_NAME = 1
IDX_MAGNET = 2
IDX_HOT_NUM = 3
IDX_PERFORMER = 4
IDX_SIZE = 5
IDX_MOSAIC = 6
IDX_VIEW = 7
IDX_REPLY = 8
IDX_DESIGNATION = 9
IDX_FILM_NAME = 10
IDX_GRADE = 11
IDX_EXIST_IN_115 = 12
IDX_LOCAL_PATH = 13
IDX_ZZZ = 14
IDX_CREATED_AT = 15
IDX_UPDATED_AT = 16
IDX_LAST_ACTION = 17

def _init_db():
    """初始化 SQLite 数据库：建表（如果不存在）"""
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS av (
            numbers_name TEXT PRIMARY KEY,
            name TEXT,
            magnet TEXT,
            hot_num INTEGER,
            performer TEXT,
            size TEXT,
            mosaic TEXT,
            view INTEGER,
            reply INTEGER,
            designation TEXT,
            film_name TEXT,
            grade INTEGER,
            exist_in_115 INTEGER,
            local_path TEXT,
            zzz INTEGER,
            created_at TEXT,
            updated_at TEXT,
            last_action TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS black_table (
            name TEXT PRIMARY KEY
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS good_performer (
            name TEXT PRIMARY KEY
        )
    """)
    # 为常用查询创建索引
    cur.execute("CREATE INDEX IF NOT EXISTS idx_av_performer ON av(performer)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_av_designation ON av(designation)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_av_local_path ON av(local_path)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_av_grade ON av(grade)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_av_mosaic ON av(mosaic)")
    # 为旧数据库添加新字段（已存在则跳过）
    try:
        cur.execute("ALTER TABLE av ADD COLUMN created_at TEXT")
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE av ADD COLUMN updated_at TEXT")
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE av ADD COLUMN last_action TEXT")
    except Exception:
        pass
    con.commit()
    cur.close()
    con.close()


def get_db_conn(timeout=30):
    """获取 SQLite 数据库连接，timeout 为等待锁的超时秒数"""
    con = sqlite3.connect(DB_PATH, timeout=timeout, check_same_thread=False)
    con.row_factory = None  # 使用默认 tuple
    return con


def _append_auto_fields(sql, val, action=None):
    """对 UPDATE av 语句自动追加 updated_at = 当前时间 和 last_action = 动作，返回 (新sql, 新val)。
    如果语句已包含 updated_at 或不是 UPDATE av，则原样返回。
    action: 可选的动作标签字符串，如 "评分"、"删除"、"移动" 等。
    """
    if not sql.strip().upper().startswith("UPDATE AV "):
        return sql, val
    if "updated_at" in sql:
        return sql, val
    sql_upper = sql.upper()
    where_pos = sql_upper.rfind(" WHERE ")
    if where_pos > 0:
        additions = ", updated_at = ?"
        add_vals = [time.strftime("%Y-%m-%d %H:%M:%S")]
        if action:
            additions += ", last_action = ?"
            add_vals.append(action)
        sql = sql[:where_pos] + additions + sql[where_pos:]
        val = tuple(list(val) + add_vals)
    return sql, val


def link_db_cmd(sql, val=(), retries=3, action=None):
    """执行单条 SQL 并返回结果，带重试机制。
    对于 UPDATE av 语句，自动追加 updated_at = 当前时间 和 last_action = 动作。
    action: 可选的动作标签字符串。
    """
    sql, val = _append_auto_fields(sql, val, action=action)
    for attempt in range(retries):
        try:
            con = get_db_conn(timeout=30)
            cur = con.cursor()
            cur.execute(sql, val)
            ret = cur.fetchall()
            con.commit()
            cur.close()
            con.close()
            return ret
        except sqlite3.OperationalError as e:
            if "locked" in str(e) and attempt < retries - 1:
                import time
                time.sleep(0.5 * (attempt + 1))  # 递增等待
                continue
            raise



# ============================================================
#  操作历史记录（功能9：评分历史/撤销）
# ============================================================

class ActionHistory:
    """记录最近的操作，支持撤销。"""

    def __init__(self, max_size=50):
        self._history = []
        self._max_size = max_size

    def push(self, action_type, key, old_data):
        """记录一条操作。
        action_type: 'grade', 'delete', 'black_add', 'black_remove', 'good_add', 'good_remove'
        key: numbers_name
        old_data: 撤销所需的数据（dict），如 {'grade': old_grade, 'local_path': old_path, ...}
        """
        self._history.append({
            "action": action_type,
            "key": key,
            "old_data": dict(old_data),
            "time": time.strftime("%H:%M:%S"),
        })
        if len(self._history) > self._max_size:
            self._history.pop(0)

    def pop(self):
        """弹出最近一条操作记录，用于撤销。"""
        if self._history:
            return self._history.pop()
        return None

    def last(self):
        """查看最近一条操作，不弹出。"""
        if self._history:
            return self._history[-1]
        return None

    def is_empty(self):
        return len(self._history) == 0


def _clean_performer(performer_raw):
    """清理 performer 字段中的 HTML 残留"""
    if not performer_raw:
        return ""
    return re.sub(r'&nbsp;|<[^>]+>', '', performer_raw).strip()


def judge_performer(performer):
    """判断演员是否在黑名单（精确匹配，不拆分多演员）"""
    con = get_db_conn()
    cur = con.cursor()
    clean = _clean_performer(performer)
    # 先用清理后的名字匹配
    cur.execute("SELECT * FROM black_table WHERE name = ?", (clean,))
    record = cur.fetchone()
    if record is not None:
        cur.close()
        con.close()
        return True
    # 再用原始名字匹配（黑名单可能存了含 HTML 残留的脏数据）
    if performer and performer.strip() != clean:
        cur.execute("SELECT * FROM black_table WHERE name = ?", (performer.strip(),))
        record = cur.fetchone()
        if record is not None:
            cur.close()
            con.close()
            return True
    cur.close()
    con.close()
    return False


def judge_performer_is_good(performer):
    """判断演员是否在关注名单（精确匹配，不拆分多演员）"""
    con = get_db_conn()
    cur = con.cursor()
    clean = _clean_performer(performer)
    cur.execute("SELECT * FROM good_performer WHERE name = ?", (clean,))
    record = cur.fetchone()
    if record is not None:
        cur.close()
        con.close()
        return True
    if performer and performer.strip() != clean:
        cur.execute("SELECT * FROM good_performer WHERE name = ?", (performer.strip(),))
        record = cur.fetchone()
        if record is not None:
            cur.close()
            con.close()
            return True
    cur.close()
    con.close()
    return False


def judge_current_film_is_exist(numbers_name):
    """判断影片是否已存在"""
    con = get_db_conn()
    cur = con.cursor()
    cur.execute("SELECT 1 FROM av WHERE numbers_name = ?", (numbers_name,))
    record = cur.fetchone()
    cur.close()
    con.close()
    return record is not None


# ============================================================
#  Cookie / HTTP 工具
# ============================================================

def txt_to_table(inp_path):
    """从 tab 分隔的 txt 读取 cookie（旧格式）"""
    cookie = {}
    with open(inp_path, "r", encoding="utf-8") as f:
        for line in f.read().splitlines():
            pos1 = line.find("\t")
            if pos1 == -1:
                continue
            key = line[:pos1]
            rest = line[pos1 + 1:]
            pos2 = rest.find("\t")
            value = rest[:pos2] if pos2 != -1 else rest
            cookie[key] = value
    return cookie


def parse_cookie_file(inp_path):
    """
    自动识别并解析 Cookie 文件，支持两种格式：
    1. Netscape HTTP Cookie 格式（浏览器导出）：
       域名 \t 子域 \t 路径 \t 安全 \t 过期 \t key \t value
    2. 旧版 tab 分隔格式：key \t value \t ...
    """
    cookie = {}
    with open(inp_path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    # 判断是否为 Netscape 格式：第一行是否以 # 开头或含有多 tab 且第一列是域名
    is_netscape = False
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split("\t")
        # Netscape 格式至少7列，且第6列是 cookie name，第7列是 value
        if len(parts) >= 7:
            is_netscape = True
            break
        # 旧格式只有2-3列
        if len(parts) >= 2:
            break

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split("\t")
        if is_netscape and len(parts) >= 7:
            # Netscape: 域名 / 子域 / 路径 / 安全 / 过期 / key / value
            key = parts[5].strip()
            value = parts[6].strip()
            if key:
                cookie[key] = value
        elif len(parts) >= 2:
            # 旧格式: key / value [/ ...]
            key = parts[0].strip()
            value = parts[1].strip()
            if key:
                cookie[key] = value

    return cookie


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}

# ============================================================
#  网络层：独立 Session + 连接池管理 + SSL 错误恢复
# ============================================================

# 模块级 Session（替代 requests.get() 全局连接池）
# 好处：
#   1. 可在 SSL 错误时主动清理连接池，避免复用陈旧连接
#   2. 可统一配置 pool_connections / pool_maxsize / retries
#   3. 连接状态可观测、可控
_http_session = requests.Session()
# 连接池：同一主机最多保持2个连接，总池大小10（单线程够用）
_http_session.mount('https://', adapters.HTTPAdapter(
    pool_connections=10, pool_maxsize=10, max_retries=0))
_http_session.mount('http://', adapters.HTTPAdapter(
    pool_connections=10, pool_maxsize=10, max_retries=0))

# SSL 错误风暴计数器（跨请求共享）
_ssl_error_streak = 0       # 连续 SSL 错误次数
_last_ssl_error_time = 0    # 上次 SSL 错误时间戳


def _classify_error(e):
    """对异常进行分类，返回 (分类名称, 是否为SSL/连接级错误) 元组。
    
    用于日志输出和自动恢复决策：
    - SSL/连接级错误 → 需要清理连接池 + 可能冷却
    - 超时 → 重试即可
    - HTTP 错误 → 服务端问题
    """
    e_str = str(e)
    err_type = type(e).__name__

    # SSL / 连接池陈旧
    if 'SSLError' in err_type or 'SSLEOFError' in err_type:
        return 'SSL连接错误', True
    if 'IncompleteRead' in err_type:
        return 'IncompleteRead(连接中断)', True
    if 'Connection broken' in e_str:
        return '连接断开(Connection broken)', True
    if 'NewConnectionError' in err_type or 'ConnectionRefused' in e_str:
        return '连接被拒绝', True
    # 反爬重定向
    if 'AntiCaptchaRedirect' in err_type:
        return '反爬重定向(验证码/Google)', True
    if 'ConnectTimeoutError' in err_type or 'timeout' in err_type.lower():
        return '连接超时', False
    if 'ReadTimeout' in err_type or 'read timed out' in e_str:
        return '读取超时', False
    # HTTP 状态码类
    if hasattr(e, 'response') and e.response is not None:
        return 'HTTP {}'.format(e.response.status_code), False
    return '{}'.format(err_type), False


def _cleanup_stale_connections():
    """关闭 Session 连接池中所有陈旧连接。
    
    在检测到 SSL/连接断开后调用，强制下次请求建立全新连接。
    """
    try:
        _http_session.close()
    except Exception:
        pass


def _get_cooldown_seconds():
    """根据连续 SSL 错误情况计算冷却秒数。
    
    策略：
      - 前2次：正常重试间隔（由调用方控制）
      - 第3次起：每次额外加 3s（3s → 6s → 9s ... 上限15s）
      - 距离上次 SSL 错误超过 60s 则重置计数器
    """
    global _ssl_error_streak, _last_ssl_error_time
    now = time.time()

    # 超过60s没有SSL错误，重置计数
    if now - _last_ssl_error_time > 60:
        _ssl_error_streak = 0

    _ssl_error_streak += 1
    _last_ssl_error_time = now

    if _ssl_error_streak <= 2:
        return 0  # 前两次不额外冷却
    extra = min((_ssl_error_streak - 2) * 3, 15)
    return extra


def get_url_txt(url_inp, cookie):
    return _http_session.get(url_inp, allow_redirects=True,
                              headers=HEADERS, cookies=cookie).text


def get_url_txt_without_cookie(url_inp):
    """普通页面请求（非流式）。

    内部自动处理 SSL 错误恢复：连续 SSL 失败时会清理连接池并适当冷却。
    新增反爬检测：检测到可疑重定向（google.com/验证码/cf挑战）时抛出 AntiCaptchaRedirect 异常。
    """
    global _ssl_error_streak
    for attempt in range(3):
        try:
            resp = _http_session.get(
                url_inp, allow_redirects=True, headers=HEADERS, timeout=30)
            resp.raise_for_status()

            # === 反爬重定向检测 ===
            # 检查重定向链：如果最终URL不是目标域名，可能是被反爬重定向了
            final_url = resp.url.lower()
            suspicious_hosts = ['google.com', 'google', 'challenges.cloudflare.com']
            for host in suspicious_hosts:
                if host in final_url:
                    redirect_chain = [r.url for r in resp.history] + [resp.url]
                    raise AntiCaptchaRedirect(
                        "检测到反爬重定向: {} → 最终: {}".format(
                            url_inp, resp.url))

            # 成功则重置计数
            _ssl_error_streak = 0
            return resp.text
        except AntiCaptchaRedirect:
            raise  # 直接抛出，不重试（反爬重试也没用）
        except Exception as e:
            cat, is_conn = _classify_error(e)
            if is_conn:
                _cleanup_stale_connections()
            cooldown = _get_cooldown_seconds() if is_conn else 0
            wait = max(2, cooldown)

            if attempt < 2:
                tag = "[SSL风暴+{}s冷却]".format(cooldown) if cooldown > 0 else ""
                print("[网络] get_url 请求失败(第{}/3次) | {} | {} | {}s后重试...".format(
                    attempt + 1, cat, e, wait))
                time.sleep(wait)
            else:
                print("[网络] get_url 彻底失败(3次) | {} | URL: {} | {}".format(
                    cat, url_inp, e))
                raise
    return ""  # 不应到达


class AntiCaptchaRedirect(Exception):
    """反爬重定向异常：被网站防护系统重定向到验证码/google等页面"""
    pass


def get_url_txt_streaming(url_inp, timeout=120, progress_callback=None):
    """流式下载大文件TXT，分块读取避免连接中断导致IncompleteRead。

    适用于 sudugu.org 等 TXT 直链下载场景（单文件可达数MB）。
    参数:
        url_inp: 下载地址
        timeout: 读超时(秒)，两次数据包间的最大等待时间。默认120秒。
                实测该站 ~12KB/s，8KB块约0.7s/块，120s足够容忍短暂卡顿。
        progress_callback: 可选回调函数 fn(downloaded_bytes, elapsed_sec)，
                          每读取一个chunk后调用。用于实时汇报下载进度。
    返回:
        str: 文本内容
    抛出:
        requests.RequestException: 连接/读取失败
    """
    # connect_timeout=30s 给服务端足够响应时间（实测TTFB约2.7s）
    # read_timeout 控制在两次chunk之间，只要持续有数据就不会触发
    resp = _http_session.get(
        url_inp,
        allow_redirects=True,
        headers=HEADERS,
        timeout=(30, timeout),
        stream=True,
    )
    resp.raise_for_status()

    # === 反爬重定向检测（与 get_url_txt_without_cookie 一致）===
    final_url = resp.url.lower()
    for host in ['google.com', 'google', 'challenges.cloudflare.com']:
        if host in final_url:
            raise AntiCaptchaRedirect(
                "检测到反爬重定向(流式): {} → 最终: {}".format(
                    url_inp, resp.url))

    chunks = []
    total = 0
    t0 = time.time()
    for chunk in resp.iter_content(chunk_size=8192):
        if chunk:
            chunks.append(chunk)
            total += len(chunk)
            if progress_callback:
                progress_callback(total, time.time() - t0)
    raw = b''.join(chunks)
    return raw.decode('utf-8', errors='replace')


# ============================================================
#  主 GUI 类
# ============================================================

class SyaApp:
    def __init__(self):
        # 初始化 SQLite 数据库（自动建表）
        _init_db()

        self.root = tk.Tk()
        self.root.title("syaA 工具箱")

        # 加载持久化配置
        self.config = load_config()

        # 恢复窗口大小和位置
        win_geom = self.config.get("window_geometry", "")
        if win_geom:
            try:
                self.root.geometry(win_geom)
            except Exception:
                self.root.geometry("1100x750")
        else:
            self.root.geometry("1100x750")
        self.root.minsize(900, 600)

        # 主题（功能12：暗色主题）
        self.current_theme = self.config.get("theme", "light")
        self.theme_colors = THEMES.get(self.current_theme, THEMES["light"])
        self._apply_theme()

        # 窗口关闭时保存配置
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # 当前视频状态（播放视频 Tab 用）
        self.cur_video = {
            "key": "",
            "path": "",
            "fanhao": "",
            "performer": "",
            "video_name": "",
            "mosaic": "",
            "grade": "",
        }

        # 操作历史（功能9：撤销）
        self.action_history = ActionHistory(max_size=50)

        # 日志队列：子线程写，主线程读
        self.log_queue = queue.Queue()

        # 运行标志：用于中断爬虫
        self.crawl_running = False

        # 小说爬取运行标志
        self.book_running = False

        # 爬取统计
        self.crawl_stats = {"new": 0, "exist": 0, "non_cn": 0, "no_magnet": 0, "fail": 0, "other": 0}

        # Cookie失效检测：连续遇到登录页的计数（线程共享）
        self._cookie_invalid_count = 0
        self._cookie_invalid_lock = threading.Lock()
        self._cookie_invalid_threshold = 3  # 连续3次登录页则判定失效

        # 爬取进度追踪（线程安全）
        self._crawl_processed = 0  # 已处理帖子数
        self._crawl_total = 0  # 总帖子数
        self._crawl_processed_lock = threading.Lock()

        self._build_ui()
        self._poll_log()

    # --------------------------------------------------------
    #  主题管理（功能12：暗色主题）
    # --------------------------------------------------------
    def _apply_theme(self):
        """应用当前主题到 Tk 根窗口"""
        c = self.theme_colors
        style = ttk.Style()
        style.theme_use("clam")  # clam 主题支持自定义颜色

        style.configure(".", background=c["bg"], foreground=c["fg"])
        style.configure("TFrame", background=c["frame_bg"])
        style.configure("TLabel", background=c["frame_bg"], foreground=c["fg"])
        style.configure("TButton", background=c["button_bg"], foreground=c["button_fg"])
        style.map("TButton",
                  background=[("active", c["accent"]), ("pressed", c["accent"])],
                  foreground=[("active", "#FFFFFF"), ("pressed", "#FFFFFF")])
        style.configure("TEntry", fieldbackground=c["entry_bg"], foreground=c["entry_fg"])
        style.configure("TCombobox", fieldbackground=c["entry_bg"], foreground=c["entry_fg"])
        style.configure("TLabelframe", background=c["frame_bg"], foreground=c["fg"])
        style.configure("TLabelframe.Label", background=c["frame_bg"], foreground=c["fg"])
        style.configure("TNotebook", background=c["bg"])
        style.configure("TNotebook.Tab", background=c["button_bg"], foreground=c["fg"], padding=[8, 4])
        style.map("TNotebook.Tab",
                  background=[("selected", c["bg"])],
                  foreground=[("selected", c["accent"])])
        style.configure("TCheckbutton", background=c["frame_bg"], foreground=c["fg"])
        style.configure("TSeparator", background=c["separator"])
        style.configure("TProgressbar", troughcolor=c["entry_bg"], background=c["accent"])

        self.root.configure(bg=c["bg"])

    def _toggle_theme(self):
        """切换亮/暗主题"""
        if self.current_theme == "light":
            self.current_theme = "dark"
        else:
            self.current_theme = "light"
        self.theme_colors = THEMES.get(self.current_theme, THEMES["light"])
        self._apply_theme()

        # 更新所有 ScrolledText 的颜色
        c = self.theme_colors
        for widget_name in ["log_text", "vid_info", "db_result", "magnet_text", "book_result", "crawl_result"]:
            w = getattr(self, widget_name, None)
            if w:
                try:
                    w.configure(bg=c["text_bg"], fg=c["text_fg"],
                                insertbackground=c["text_fg"],
                                selectbackground=c["accent"])
                except Exception:
                    pass

        # 更新视频标签样式
        if hasattr(self, "vid_info"):
            self.vid_info.tag_configure("section_title", foreground=c["section_title"],
                                        font=("Consolas", 10, "bold"))
            self.vid_info.tag_configure("tag_black", foreground=c["tag_black"],
                                        font=("Consolas", 10, "bold"))
            self.vid_info.tag_configure("tag_good", foreground=c["tag_good"],
                                        font=("Consolas", 10, "bold"))
            self.vid_info.tag_configure("tag_none", foreground=c["tag_none"],
                                        font=("Consolas", 10))
            self.vid_info.tag_configure("sep", foreground=c["separator"])
            self.vid_info.tag_configure("extra_msg", foreground="#CC6600",
                                        font=("Consolas", 10, "bold"))

        self._log("[主题] 切换为{}主题".format("暗色" if self.current_theme == "dark" else "亮色"))

        # 更新主题按钮文字
        if hasattr(self, "btn_theme"):
            theme_text = "🌙 暗色" if self.current_theme == "light" else "☀ 亮色"
            self.btn_theme.configure(text=theme_text)

    # --------------------------------------------------------
    #  UI 构建
    # --------------------------------------------------------
    def _build_ui(self):
        # 顶部 Notebook
        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill=tk.BOTH, expand=True, padx=6, pady=(6, 0))

        self._build_crawl_tab()
        self._build_video_tab()
        self._build_magnet_tab()
        self._build_db_tab()
        self._build_file_tab()
        self._build_book_tab()

        # 底部日志区
        log_frame = ttk.LabelFrame(self.root, text="运行日志")
        log_frame.pack(fill=tk.BOTH, padx=6, pady=6)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, state=tk.DISABLED,
                                                   font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)

        btn_clear_log = ttk.Button(log_frame, text="清空日志", command=self._clear_log)
        btn_clear_log.pack(anchor=tk.E, pady=2)

        # 状态栏
        self._build_statusbar()

    # --------------------------------------------------------
    #  状态栏
    # --------------------------------------------------------
    def _build_statusbar(self):
        """构建底部状态栏"""
        bar = ttk.Frame(self.root, relief=tk.SUNKEN)
        bar.pack(side=tk.BOTTOM, fill=tk.X, padx=0, pady=0)

        self._sb_video = tk.StringVar(value="当前: 无")
        self._sb_tag = tk.StringVar(value="")
        self._sb_stats = tk.StringVar(value="")

        # 左侧：当前视频信息
        ttk.Label(bar, textvariable=self._sb_video, width=35, anchor=tk.W,
                  font=("Consolas", 9)).pack(side=tk.LEFT, padx=(6, 2))
        ttk.Separator(bar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=2)

        # 中部：演员标签状态
        self._sb_tag_label = ttk.Label(bar, textvariable=self._sb_tag, width=18, anchor=tk.W,
                                        font=("Consolas", 9, "bold"))
        self._sb_tag_label.pack(side=tk.LEFT, padx=(4, 2))
        ttk.Separator(bar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=2)

        # 右侧：全局统计
        ttk.Label(bar, textvariable=self._sb_stats, anchor=tk.E,
                  font=("Consolas", 9)).pack(side=tk.RIGHT, padx=(2, 6))

        # 初始刷新
        self._refresh_statusbar()

    def _refresh_statusbar(self):
        """刷新状态栏内容"""
        v = self.cur_video
        # 当前视频
        if v.get("fanhao"):
            info = "当前: {}".format(v["fanhao"])
            if v.get("performer"):
                info += " | {}".format(v["performer"])
            if v.get("grade"):
                info += " | {}分".format(v["grade"])
            self._sb_video.set(info)
        else:
            self._sb_video.set("当前: 无")

        # 演员标签
        if v.get("performer"):
            if judge_performer(v["performer"]):
                self._sb_tag.set("⚠ 黑名单")
                # 使用红色前景
                try:
                    self._sb_tag_label.configure(foreground="#CC3333")
                except Exception:
                    pass
            elif judge_performer_is_good(v["performer"]):
                self._sb_tag.set("★ 关注")
                try:
                    self._sb_tag_label.configure(foreground="#00AA00")
                except Exception:
                    pass
            else:
                self._sb_tag.set("○ 无标签")
                try:
                    self._sb_tag_label.configure(foreground="#888888")
                except Exception:
                    pass
        else:
            self._sb_tag.set("")
            try:
                self._sb_tag_label.configure(foreground=self.theme_colors.get("fg", "#000000"))
            except Exception:
                pass

        # 全局统计
        try:
            con = get_db_conn()
            cur = con.cursor()
            cur.execute("SELECT count(*) FROM av WHERE local_path IS NOT NULL")
            total = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM av WHERE local_path IS NOT NULL AND grade IS NULL")
            ungraded = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM av WHERE local_path IS NOT NULL AND grade IS NULL AND zzz IS NULL")
            nozzz = cur.fetchone()[0]
            cur.close()
            con.close()
            self._sb_stats.set("本地:{} | 未评:{} | NoZZZ未评:{}".format(total, ungraded, nozzz))
        except Exception:
            self._sb_stats.set("")

    # ============ Tab 1: 论坛爬取 ============
    def _build_crawl_tab(self):
        tab = ttk.Frame(self.nb)
        self.nb.add(tab, text="论坛爬取")

        row = ttk.Frame(tab)
        row.pack(fill=tk.X, padx=10, pady=6)

        ttk.Label(row, text="起始帖号:").pack(side=tk.LEFT)
        self.crawl_begin = ttk.Entry(row, width=12)
        self.crawl_begin.insert(0, self.config.get("crawl_begin", "3369770"))
        self.crawl_begin.pack(side=tk.LEFT, padx=(2, 10))

        ttk.Label(row, text="结束帖号:").pack(side=tk.LEFT)
        self.crawl_end = ttk.Entry(row, width=12)
        self.crawl_end.insert(0, self.config.get("crawl_end", "3380551"))
        self.crawl_end.pack(side=tk.LEFT, padx=(2, 10))

        ttk.Label(row, text="线程数:").pack(side=tk.LEFT)
        self.crawl_threads = ttk.Entry(row, width=5)
        self.crawl_threads.insert(0, self.config.get("crawl_threads", "10"))
        self.crawl_threads.pack(side=tk.LEFT, padx=(2, 10))

        row_url = ttk.Frame(tab)
        row_url.pack(fill=tk.X, padx=10, pady=2)

        ttk.Label(row_url, text="目标网站:").pack(side=tk.LEFT)
        self.base_url = ttk.Entry(row_url, width=35)
        self.base_url.insert(0, self.config.get("base_url", "plwt.kpqq4.com"))
        self.base_url.pack(side=tk.LEFT, padx=2)
        ttk.Label(row_url, text="(URL格式: https://域名/thread-{帖号}-1-1.html)", foreground="gray").pack(side=tk.LEFT, padx=4)

        row2 = ttk.Frame(tab)
        row2.pack(fill=tk.X, padx=10, pady=2)

        ttk.Label(row2, text="Cookie文件:").pack(side=tk.LEFT)
        self.cookie_path = ttk.Entry(row2, width=55)
        self.cookie_path.insert(0, self.config.get("cookie_path", "F:/workbuddy/视频下载器_tengxun/10dd.7qxz7.net_cookies.txt"))
        self.cookie_path.pack(side=tk.LEFT, padx=2)
        ttk.Button(row2, text="选择Cookie文件...", command=self._browse_cookie).pack(side=tk.LEFT, padx=4)

        row3 = ttk.Frame(tab)
        row3.pack(fill=tk.X, padx=10, pady=6)

        self.btn_crawl_start = ttk.Button(row3, text="开始爬取", command=self._start_crawl)
        self.btn_crawl_start.pack(side=tk.LEFT, padx=4)

        self.btn_crawl_stop = ttk.Button(row3, text="停止", command=self._stop_crawl, state=tk.DISABLED)
        self.btn_crawl_stop.pack(side=tk.LEFT, padx=4)

        ttk.Separator(row3, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)
        ttk.Button(row3, text="爬100页", command=lambda: self._quick_crawl(100)).pack(side=tk.LEFT, padx=3)
        ttk.Button(row3, text="爬500页", command=lambda: self._quick_crawl(500)).pack(side=tk.LEFT, padx=3)
        ttk.Button(row3, text="爬1000页", command=lambda: self._quick_crawl(1000)).pack(side=tk.LEFT, padx=3)
        ttk.Label(row3, text="自定义:").pack(side=tk.LEFT, padx=(8, 0))
        self.crawl_custom_pages = ttk.Entry(row3, width=6)
        self.crawl_custom_pages.pack(side=tk.LEFT, padx=2)
        ttk.Button(row3, text="爬取", command=self._custom_crawl).pack(side=tk.LEFT, padx=2)

        # 爬取进度条
        self.crawl_status = tk.StringVar(value="就绪")
        ttk.Label(row3, textvariable=self.crawl_status).pack(side=tk.LEFT, padx=(20, 4))
        self.crawl_progress = ttk.Progressbar(row3, length=250, mode="determinate")
        self.crawl_progress.pack(side=tk.LEFT, padx=4)
        self.crawl_progress_label = tk.StringVar(value="")
        ttk.Label(row3, textvariable=self.crawl_progress_label).pack(side=tk.LEFT, padx=4)

        # 爬取结果区
        res_frame = ttk.LabelFrame(tab, text="爬取统计")
        res_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

        self.crawl_result = scrolledtext.ScrolledText(res_frame, height=12, font=("Consolas", 9))
        self.crawl_result.pack(fill=tk.BOTH, expand=True)

    def _browse_cookie(self):
        path = filedialog.askopenfilename(
            title="选择Cookie文件",
            filetypes=[
                ("Cookie文件", "*.txt"),
                ("Cookie文件", "*.cookies"),
                ("所有文件", "*.*"),
            ],
        )
        if path:
            self.cookie_path.delete(0, tk.END)
            self.cookie_path.insert(0, path)

    def _custom_crawl(self):
        """自定义页数爬取"""
        try:
            pages = int(self.crawl_custom_pages.get())
        except ValueError:
            messagebox.showerror("输入错误", "请输入有效的整数页数")
            return
        if pages <= 0:
            messagebox.showerror("输入错误", "页数必须大于0")
            return
        self._quick_crawl(pages)

    def _quick_crawl(self, pages):
        """快捷爬取：将结束贴号填入开始贴号，结束贴号+pages，然后开始爬取"""
        try:
            cur_end = int(self.crawl_end.get())
        except ValueError:
            messagebox.showerror("输入错误", "当前结束帖号不是有效整数")
            return
        self.crawl_begin.delete(0, tk.END)
        self.crawl_begin.insert(0, str(cur_end))
        self.crawl_end.delete(0, tk.END)
        self.crawl_end.insert(0, str(cur_end + pages))
        self._start_crawl()

    def _start_crawl(self):
        try:
            begin = int(self.crawl_begin.get())
            end = int(self.crawl_end.get())
            threads = int(self.crawl_threads.get())
        except ValueError:
            messagebox.showerror("输入错误", "帖号和线程数必须为整数")
            return

        if begin >= end:
            messagebox.showerror("输入错误", "起始帖号必须小于结束帖号")
            return

        self.crawl_running = True
        self.crawl_stats = {"new": 0, "exist": 0, "non_cn": 0, "no_magnet": 0, "fail": 0, "other": 0}
        self._cookie_invalid_count = 0
        self._crawl_processed = 0
        self._crawl_total = end - begin
        self.btn_crawl_start.config(state=tk.DISABLED)
        self.btn_crawl_stop.config(state=tk.NORMAL)
        self.crawl_status.set("爬取中...")
        self.crawl_progress["value"] = 0
        self.crawl_progress_label.set("0/{}".format(self._crawl_total))

        # 清空统计区域
        self.crawl_result.config(state=tk.NORMAL)
        self.crawl_result.delete(1.0, tk.END)
        self.crawl_result.insert(tk.END, "爬取中，请等待完成...\n")
        self.crawl_result.config(state=tk.DISABLED)

        t = threading.Thread(target=self._crawl_worker, args=(begin, end, threads), daemon=True)
        t.start()

    def _stop_crawl(self):
        self.crawl_running = False
        self.crawl_status.set("正在停止...")

    def _crawl_worker(self, begin, end, thread_num):
        total = end - begin
        self._log("开始爬取：{} - {}，共 {} 个帖子，线程数：{}".format(begin, end, total, thread_num))
        try:
            cookie = parse_cookie_file(self.cookie_path.get())
            self._log("Cookie 读取成功，共 {} 条".format(len(cookie)))
        except Exception as e:
            self._log("读取 Cookie 失败：{}".format(e))
            self.root.after(0, self._crawl_done)
            return

        # 爬取前验证 Cookie 是否有效：访问一个帖子，检查是否被重定向到登录页
        self._log("正在验证 Cookie 有效性...")
        try:
            test_url = "https://{}/thread-{}-1-1.html".format(self.base_url.get().strip().rstrip("/"), begin)
            test_html = get_url_txt(test_url, cookie)
            if self._is_login_page(test_html):
                self._log("[Cookie无效] 测试页面返回登录页，Cookie已失效！请更新Cookie后重试")
                self._log("[Cookie无效] 终止爬取，未处理任何帖子")
                self.root.after(0, self._crawl_done)
                return
            self._log("Cookie 验证通过")
        except Exception as e:
            self._log("[Cookie验证] 请求失败：{}，将继续尝试爬取".format(e))

        # 智能分配线程：实际线程数不超过帖子数
        actual_threads = min(thread_num, total)
        if actual_threads < thread_num:
            self._log("帖子数({})小于线程数({})，调整为 {} 个线程".format(total, thread_num, actual_threads))

        each_num = total // actual_threads
        remainder = total % actual_threads
        threads = []
        curr = begin
        for i in range(actual_threads):
            # 前 remainder 个线程多分配1个帖子，确保不遗漏
            curr_begin = curr
            curr_end = curr + each_num + (1 if i < remainder else 0)
            curr = curr_end
            t = threading.Thread(
                target=self._crawl_range,
                args=(curr_begin, curr_end, cookie),
                daemon=True,
            )
            threads.append(t)
            t.start()
            self._log("线程 {} 启动：{} - {}（共{}个）".format(i, curr_begin, curr_end, curr_end - curr_begin))

        for t in threads:
            t.join()

        # 判断终止原因
        cookie_invalid = self._cookie_invalid_count >= self._cookie_invalid_threshold

        # 输出统计
        self._log("=" * 50)
        if cookie_invalid:
            self._log("[Cookie失效] 爬取因Cookie失效而终止！")
            self._log("[Cookie失效] 请更新Cookie文件后重新爬取")
        elif not self.crawl_running:
            self._log("[用户中断] 爬取被用户手动停止")
        else:
            self._log("爬取完成！")
        self._log("新增: {} | 跳过已存在: {} | 非中文: {} | 无磁力: {} | 请求失败: {} | 其他跳过: {}".format(
            self.crawl_stats["new"],
            self.crawl_stats["exist"],
            self.crawl_stats["non_cn"],
            self.crawl_stats["no_magnet"],
            self.crawl_stats["fail"],
            self.crawl_stats["other"],
        ))
        self._log("进度: {}/{} ({}个帖子已处理)".format(
            sum(self.crawl_stats.values()), total, sum(self.crawl_stats.values())))
        self.root.after(0, self._crawl_done)

    def _crawl_range(self, begin, end, cookie):
        """爬取一个范围的帖子"""
        thread_id = threading.current_thread().name
        processed = 0

        for post_id in range(begin, end):
            if not self.crawl_running:
                self._log("[{}] 爬取被用户中断".format(thread_id))
                return

            processed += 1
            # 更新整体进度（线程安全）
            with self._crawl_processed_lock:
                self._crawl_processed += 1
                done = self._crawl_processed
                total = self._crawl_total
            pct = done * 100 // total if total > 0 else 0
            self.root.after(0, self._update_progress, pct, done, total)

            next_url = "https://{}/thread-{}-1-1.html".format(self.base_url.get().strip().rstrip("/"), post_id)

            # 1. 请求页面
            self._log("[{}] >> 处理 post={} | {}".format(thread_id, post_id, next_url))
            try:
                html = get_url_txt(next_url, cookie)
            except Exception as e:
                self._log("[{}] [FAIL] 请求失败 | {} | 错误: {}".format(thread_id, next_url, e))
                self.crawl_stats["fail"] += 1
                continue

            # 检查页面是否有效（太短说明被拦截或404）
            if len(html) < 500:
                # 先检查是否是登录页（Cookie失效）
                if self._is_login_page(html):
                    self._report_cookie_invalid(thread_id, next_url)
                    if not self.crawl_running:
                        self._log("[{}] Cookie已失效，终止爬取 | 已处理 {} 个帖子".format(thread_id, processed))
                        return
                else:
                    self._log("[{}] [FAIL] 页面无效 | {} | 仅{}字节，可能404或被拦截".format(thread_id, next_url, len(html)))
                self.crawl_stats["other"] += 1
                continue

            # 检查是否被重定向到登录页（页面较长但内容是登录）
            if self._is_login_page(html):
                self._report_cookie_invalid(thread_id, next_url)
                self.crawl_stats["other"] += 1
                if not self.crawl_running:
                    self._log("[{}] Cookie已失效，终止爬取 | 已处理 {} 个帖子".format(thread_id, processed))
                    return
                continue

            # 2. 提取磁力链接
            # 页面有效（到达此步说明非登录页），重置Cookie失效计数
            with self._cookie_invalid_lock:
                self._cookie_invalid_count = 0

            mag = re.findall(r"magnet:\?xt=urn:btih:[a-zA-Z0-9]+", str(html))
            if not mag:
                self._log("[{}] [SKIP] 无磁力链接 | {}".format(thread_id, next_url))
                self.crawl_stats["no_magnet"] += 1
                continue

            # 3. 提取标题
            pos1 = html.find("<title>")
            pos2 = html.find("</title>")
            if pos1 == -1 or pos2 == -1:
                self._log("[{}] [SKIP] 无标题标签 | {}".format(thread_id, next_url))
                self.crawl_stats["other"] += 1
                continue
            title = html[pos1 + 7:pos2]

            # 4. 番号判断
            # 标题格式通常: [中文字幕]番号 描述 [自译征用] - 板块 - 站点
            # 需要跳过 [中文/无码/高清] 等前缀标签，提取真正的番号
            # 先去掉所有前缀方括号标签
            cleaned_title = title
            prefix_tags = ["[中文字幕]", "[无码]", "[高清]", "[原档]", "[破解]", "[字幕]", "[无码破解]", "[FC2]"]
            for tag in prefix_tags:
                if cleaned_title.startswith(tag):
                    cleaned_title = cleaned_title[len(tag):].strip()

            # 在清理后的标题中找第一个 [ ，前面就是番号
            pos1 = cleaned_title.find("[")
            if pos1 == -1:
                # 没有方括号了，整个 cleaned_title 作为番号
                fanhao = cleaned_title.split(" - ")[0].strip()
                if not fanhao:
                    self._log("[{}] [SKIP] 无法提取番号 | {} | 标题: {}".format(thread_id, next_url, title[:80]))
                    self.crawl_stats["other"] += 1
                    continue
            else:
                fanhao = cleaned_title[:pos1 - 1].strip()

            # 番号太长（>80字符）说明提取有误，跳过
            if len(fanhao) > 80:
                self._log("[{}] [SKIP] 番号异常过长({}字符) | {} | 番号: {}".format(thread_id, len(fanhao), next_url, fanhao[:80]))
                self.crawl_stats["other"] += 1
                continue

            designation = fanhao
            cn_type = ""
            if "无码破解" in title:
                fanhao += "-UC"
                cn_type = "无码破解"
            elif "自译征用" in title:
                fanhao += "-C"
                cn_type = "自译征用"
            elif "自提征用" in title:
                fanhao += "-C"
                cn_type = "自提征用"
            else:
                self._log("[非中文] [SKIP] 跳过 | {} | 标题: {}".format(next_url, title[:80]))
                self.crawl_stats["non_cn"] += 1
                continue

            # 5. 热度
            hot_num = 0
            try:
                hot_num = int(re.findall(r"热度: [0-9]+", html)[0][4:])
            except (IndexError, ValueError):
                pass

            # 通用字段提取函数：从 HTML 中提取【字段名】：值
            # 已知的字段名列表（用于判断值的终止位置）
            _known_fields = ["影片名称", "出演女优", "影片容量", "是否有码", "种子期限", "下载工具"]

            def extract_field(field_name, default="unknown"):
                """从HTML中提取【字段名】：值，兼容纯文本和带HTML标签的格式"""
                # 策略1: 从正文 <font> 标签区域提取（每个字段独占一行，最可靠）
                # 匹配 <font...>【字段名】：值</font>  其中值内部可以包含【】
                pat_font = r"<font[^>]*>\s*【{}】[：:]\s*(.*?)\s*</font>".format(field_name)
                ret = re.findall(pat_font, html, re.DOTALL)
                if ret:
                    val = ret[0].strip()
                    val = re.sub(r"<[^>]+>", "", val).strip()
                    if val:
                        return val

                # 策略2: 从 meta description 提取（字段紧凑排列，用下一个已知字段名作为终止）
                other_fields = [f for f in _known_fields if f != field_name]
                stop_pattern = "|".join(re.escape("【" + f + "】") for f in other_fields)
                if stop_pattern:
                    pat_meta = r"【{}】[：:]\s*((?:(?!{}).)*)".format(field_name, stop_pattern)
                    ret = re.findall(pat_meta, html)
                    if ret:
                        val = ret[0].strip()
                        val = re.sub(r"<[^>]+>", "", val).strip()
                        val = val.rstrip('"').strip()
                        if val:
                            return val

                # 策略3: 简单兜底
                pat_simple = r"【{}】[：:]\s*([^<\"]+)".format(field_name)
                ret = re.findall(pat_simple, html)
                if ret:
                    val = ret[0].strip()
                    val = re.sub(r"<[^>]+>", "", val).strip()
                    val = val.rstrip('"').strip()
                    if val:
                        return val

                return default

            # 6. 演员
            performer = extract_field("出演女优", "unknown")

            # 7. 大小
            size = extract_field("影片容量", "unknown")

            # 8. 有码
            mosaic = extract_field("是否有码", "unknown")

            # 9. 查看 / 回复
            view, reply = 0, 0
            for line in html.splitlines():
                if "查看:" in line:
                    ret = re.findall(r">[0-9]+<", line)
                    if len(ret) >= 2:
                        view = int(ret[0][1:-1])
                        reply = int(ret[1][1:-1])

            # 10. 影片名称
            film_name = extract_field("影片名称", "unknown")

            # 提取到的信息汇总日志
            self._log("[{}] [INFO] 番号={} | 类型={} | 演员={} | 影片={} | 大小={} | 码={} | 热度={} | 查看/回复={}/{} | 磁力={}".format(
                thread_id, fanhao, cn_type, performer, film_name[:30], size, mosaic, hot_num, view, reply, mag[0]))

            # 11. 写磁力文件
            try:
                day_name = time.strftime("%Y-%m-%d")
                os.makedirs("./output/magnet", exist_ok=True)
                with open("./output/magnet/{}-magnet.txt".format(day_name), "a", encoding="utf-8") as f:
                    if "-UC" not in fanhao:
                        if not judge_performer(performer):
                            f.write(mag[0] + "\n")
                        else:
                            self._log("[黑名单] [SKIP] 演员在黑名单，跳过磁力写入 | {} | 演员: {}".format(next_url, performer))
                    else:
                        self._log("[无码] [SKIP] 跳过磁力写入 | {} | 番号: {}".format(next_url, fanhao))
            except Exception as e:
                self._log("[磁力] 写入磁力文件失败 | {} | 错误: {}".format(next_url, e))

            # 12. 判断已存在
            if judge_current_film_is_exist(fanhao):
                self._log("[已存在] [SKIP] 跳过入库 | {} | 番号: {} | 演员: {} | 影片: {}".format(next_url, fanhao, performer, film_name[:30]))
                self.crawl_stats["exist"] += 1
                continue

            # 13. 保存源文件
            try:
                os.makedirs("./output/高清中文字幕网页源文件", exist_ok=True)
                with open("./output/高清中文字幕网页源文件/{}.txt".format(fanhao), "w", encoding="utf-8") as f:
                    f.write(html)
            except Exception as e:
                self._log("[源文件] 保存失败 | {} | 错误: {}".format(next_url, e))

            # 14. 写数据库
            try:
                os.makedirs("./output", exist_ok=True)
                with open("./output/磁力链接.txt", "a", encoding="utf-8") as f:
                    out = title + "\n" + mag[0] + "\n"
                    now_str = time.strftime("%Y-%m-%d %H:%M:%S")
                    db_params = [fanhao, title, mag[0], hot_num, performer, size, mosaic, view, reply, designation, film_name, now_str, now_str]
                    link_db_cmd(
                        "INSERT INTO av (numbers_name, name, magnet, hot_num, performer, size, mosaic, view, reply, designation, film_name, created_at, updated_at) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        db_params,
                    )
                    f.write(out)
                    self._log("[NEW] 入库成功 | {}".format(next_url))
                    self._log("  +---- 入库参数 -----------------------------------------------------------")
                    self._log("  | numbers_name = {}".format(fanhao))
                    self._log("  | name(title)  = {}".format(title[:80]))
                    self._log("  | magnet       = {}".format(mag[0]))
                    self._log("  | hot_num      = {}".format(hot_num))
                    self._log("  | performer    = {}".format(performer))
                    self._log("  | size         = {}".format(size))
                    self._log("  | mosaic       = {}".format(mosaic))
                    self._log("  | view/reply   = {}/{}".format(view, reply))
                    self._log("  | designation  = {}".format(designation))
                    self._log("  | film_name    = {}".format(film_name[:60]))
                    self._log("  +-------------------------------------------------------------------------")
                    self.crawl_stats["new"] += 1
            except sqlite3.IntegrityError:
                self._log("[DUP] 数据库已有 | {} | 番号: {}".format(next_url, fanhao))
                self.crawl_stats["exist"] += 1
            except UnicodeEncodeError:
                self._log("[编码异常] [FAIL] | {} | 标题: {}".format(next_url, title[:40]))
                try:
                    os.makedirs("./output/异常影片", exist_ok=True)
                    with open("./output/异常影片/{}.txt".format(fanhao), "w", encoding="utf-8") as f:
                        f.write(html)
                except Exception:
                    pass
                self.crawl_stats["other"] += 1
            except Exception as e:
                self._log("[DB错误] [FAIL] 写入失败 | {} | 番号={} | 错误: {}".format(next_url, fanhao, e))
                self.crawl_stats["other"] += 1

        self._log("[{}] 完成，处理了 {} 个帖子".format(thread_id, processed))

    def _is_login_page(self, html):
        """检测页面是否为登录页（Cookie失效的标志）"""
        if not html:
            return True
        # Discuz 论坛登录页特征
        login_signs = [
            "member.php?mod=logging",
            "action=login",
            "登录",
            "请先登录",
            "您需要登录",
            "loginform",
            "type=login",
        ]
        # 如果页面很短且包含登录特征，判定为登录页
        if len(html) < 2000:
            for sign in login_signs:
                if sign in html:
                    return True
        # 正常帖子页面特征：有帖子内容区域
        if "postlist" in html or "pid" in html or "ajaxdialog" in html:
            return False
        # 页面不太短但没有帖子内容，也检查登录特征
        if len(html) < 5000:
            for sign in login_signs:
                if sign in html:
                    return True
        return False

    def _report_cookie_invalid(self, thread_id, next_url):
        """报告Cookie失效，连续达到阈值则终止所有线程"""
        with self._cookie_invalid_lock:
            self._cookie_invalid_count += 1
            count = self._cookie_invalid_count

        if count >= self._cookie_invalid_threshold:
            self._log("[Cookie无效] 连续{}次遇到登录页，判定Cookie已失效！终止爬取".format(count))
            self.crawl_running = False  # 通知所有线程停止
        else:
            self._log("[Cookie可疑] 第{}次遇到登录页 | {} | 继续观察...".format(count, next_url))

    def _update_progress(self, pct, done, total):
        """在主线程更新进度条（由 root.after 调用）"""
        self.crawl_progress["value"] = pct
        self.crawl_progress_label.set("{}/{} ({}%)".format(done, total, pct))

    def _crawl_done(self):
        self.btn_crawl_start.config(state=tk.NORMAL)
        self.btn_crawl_stop.config(state=tk.DISABLED)
        self.crawl_status.set("就绪")
        self.crawl_progress["value"] = 100
        self.crawl_progress_label.set("{}/{} (100%)".format(self._crawl_processed, self._crawl_total))

        # 写入爬取统计区域
        self.crawl_result.config(state=tk.NORMAL)
        self.crawl_result.delete(1.0, tk.END)
        total = sum(self.crawl_stats.values())
        stats_text = (
            "=" * 50 + "\n"
            "爬取统计报告\n"
            "=" * 50 + "\n"
            "处理总数:       {}\n"
            "新增入库:       {}\n"
            "跳过(已存在):   {}\n"
            "跳过(非中文):   {}\n"
            "跳过(无磁力):   {}\n"
            "请求失败:       {}\n"
            "其他跳过:       {}\n"
            "=" * 50 + "\n"
            "时间: {}\n"
        ).format(
            total,
            self.crawl_stats["new"],
            self.crawl_stats["exist"],
            self.crawl_stats["non_cn"],
            self.crawl_stats["no_magnet"],
            self.crawl_stats["fail"],
            self.crawl_stats["other"],
            time.strftime("%Y-%m-%d %H:%M:%S"),
        )
        self.crawl_result.insert(tk.END, stats_text)
        self.crawl_result.config(state=tk.DISABLED)

    # ============ Tab 2: 播放视频 ============
    def _build_video_tab(self):
        tab = ttk.Frame(self.nb)
        self.nb.add(tab, text="播放视频")

        # 左侧控制面板
        left = ttk.Frame(tab, width=240)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=6, pady=6)
        left.pack_propagate(False)

        # ── 随机 + 播放 ──
        row_rand = ttk.Frame(left)
        row_rand.pack(fill=tk.X, pady=1)
        ttk.Button(row_rand, text="随机NoZZZ", command=lambda: self._rand_video(False)).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0,2))
        ttk.Button(row_rand, text="随机All", command=lambda: self._rand_video(True)).pack(side=tk.LEFT, expand=True, fill=tk.X)

        row_play = ttk.Frame(left)
        row_play.pack(fill=tk.X, pady=1)
        ttk.Button(row_play, text="播放视频", command=self._play_video).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0,2))
        ttk.Button(row_play, text="播放≥分数", command=self._play_good_video).pack(side=tk.LEFT, expand=True, fill=tk.X)

        # ── 评分 ──
        sf = ttk.Frame(left)
        sf.pack(fill=tk.X, pady=1)
        ttk.Label(sf, text="分数:").pack(side=tk.LEFT)
        self.vid_grade_combo = ttk.Combobox(sf, width=5, values=[str(i) for i in range(10, 110, 10)])
        self.vid_grade_combo.set("60")
        self.vid_grade_combo.pack(side=tk.LEFT, padx=2)
        ttk.Button(sf, text="评分", command=self._grade_video).pack(side=tk.LEFT, padx=2)

        # ── 删除 + 撤销 ──
        row_del = ttk.Frame(left)
        row_del.pack(fill=tk.X, pady=1)
        ttk.Button(row_del, text="删除视频", command=self._delete_video).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0,2))
        self.btn_undo = ttk.Button(row_del, text="↩撤销", command=self._undo_last_action)
        self.btn_undo.pack(side=tk.LEFT, expand=True, fill=tk.X)
        self.undo_status = tk.StringVar(value="")
        ttk.Label(left, textvariable=self.undo_status, font=("Consolas", 8)).pack(anchor=tk.W, padx=4)

        ttk.Separator(left, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=4)

        # ── 黑名单/关注（加入/移出并排） ──
        row_black = ttk.Frame(left)
        row_black.pack(fill=tk.X, pady=1)
        ttk.Button(row_black, text="⚠加黑名单", command=lambda: self._toggle_performer("black", True)).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0,2))
        ttk.Button(row_black, text="移出黑名单", command=lambda: self._toggle_performer("black", False)).pack(side=tk.LEFT, expand=True, fill=tk.X)

        row_good = ttk.Frame(left)
        row_good.pack(fill=tk.X, pady=1)
        ttk.Button(row_good, text="★加关注", command=lambda: self._toggle_performer("good", True)).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0,2))
        ttk.Button(row_good, text="移出关注", command=lambda: self._toggle_performer("good", False)).pack(side=tk.LEFT, expand=True, fill=tk.X)

        ttk.Separator(left, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=4)

        # ── 搜索（搜索框 + 类型一行，按钮同行） ──
        search_frame = ttk.Frame(left)
        search_frame.pack(fill=tk.X, padx=4, pady=1)
        self.vid_search_entry = ttk.Entry(search_frame, width=12)
        self.vid_search_entry.pack(side=tk.LEFT, padx=(0, 2))
        self.vid_search_entry.bind("<Return>", lambda e: self._search_video())
        self.vid_search_type = ttk.Combobox(search_frame, width=5,
                                             values=["番号", "演员", "片名", "关键词"])
        self.vid_search_type.set("番号")
        self.vid_search_type.pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(search_frame, text="🔍", width=3, command=self._search_video).pack(side=tk.LEFT)

        self.vid_search_result_label = tk.StringVar(value="")
        ttk.Label(left, textvariable=self.vid_search_result_label,
                  font=("Consolas", 8)).pack(anchor=tk.W, padx=4)

        # ── 主题切换 ──
        theme_text = "🌙 暗色" if self.current_theme == "light" else "☀ 亮色"
        self.btn_theme = ttk.Button(left, text=theme_text, command=self._toggle_theme)
        self.btn_theme.pack(fill=tk.X, pady=(4, 1))

        # 右侧信息区
        right = ttk.Frame(tab)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6, pady=6)

        # 文字信息区
        self.vid_info = scrolledtext.ScrolledText(right, font=("Consolas", 10), height=12)
        self.vid_info.pack(fill=tk.BOTH, expand=True)

    def _update_video_info(self, extra=""):
        """刷新右侧视频信息"""
        SEP = "-" * 40
        self.vid_info.delete(1.0, tk.END)
        self.vid_info.config(state=tk.NORMAL)
        v = self.cur_video

        # 区块标签样式
        self.vid_info.tag_configure("section_title", foreground="#3366CC", font=("Consolas", 10, "bold"))
        self.vid_info.tag_configure("tag_black", foreground="#CC3333", font=("Consolas", 10, "bold"))
        self.vid_info.tag_configure("tag_good", foreground="#00AA00", font=("Consolas", 10, "bold"))
        self.vid_info.tag_configure("tag_none", foreground="#888888", font=("Consolas", 10))
        self.vid_info.tag_configure("sep", foreground="#AAAAAA")
        self.vid_info.tag_configure("extra_msg", foreground="#CC6600", font=("Consolas", 10, "bold"))

        # ========== 区块1: 视频信息 ==========
        self.vid_info.insert(tk.END, "[ 视频信息 ]\n", "section_title")
        self.vid_info.insert(tk.END, "番号：{}\n".format(v["fanhao"]))
        self.vid_info.insert(tk.END, "演员：{}\n".format(v["performer"]))
        self.vid_info.insert(tk.END, "码：{}\n".format(v["mosaic"]))
        self.vid_info.insert(tk.END, "影片名称：{}\n".format(v["video_name"]))
        self.vid_info.insert(tk.END, "路径：{}\n".format(v["path"]))
        if v["grade"]:
            self.vid_info.insert(tk.END, "分数：{}\n".format(v["grade"]))
        if v.get("created_at"):
            self.vid_info.insert(tk.END, "存入：{}\n".format(v["created_at"]))
        if v.get("updated_at"):
            action_suffix = ""
            if v.get("last_action"):
                action_suffix = " ({})".format(v["last_action"])
            self.vid_info.insert(tk.END, "更新：{}{}\n".format(v["updated_at"], action_suffix))

        # 演员标签（带颜色）
        if v["performer"]:
            if judge_performer(v["performer"]):
                self.vid_info.insert(tk.END, "[黑名单] ", "tag_black")
                self.vid_info.insert(tk.END, "当前演员在黑名单中：{}\n".format(v["performer"]))
            elif judge_performer_is_good(v["performer"]):
                self.vid_info.insert(tk.END, "[关注] ", "tag_good")
                self.vid_info.insert(tk.END, "当前演员在关注名单中：{}\n".format(v["performer"]))
            else:
                self.vid_info.insert(tk.END, "[无标签] ", "tag_none")
                self.vid_info.insert(tk.END, "当前演员 notag\n")

        # ========== 区块2: 当前演员统计 ==========
        if v["performer"]:
            try:
                clean_p = _clean_performer(v["performer"])
                con2 = get_db_conn()
                cur2 = con2.cursor()
                cur2.execute(
                    "SELECT grade, count(*) FROM av WHERE performer = ? AND grade IS NOT NULL "
                    "GROUP BY grade ORDER BY grade DESC", (clean_p,))
                p_grades = cur2.fetchall()
                cur2.execute("SELECT count(*) FROM av WHERE performer = ? AND local_path IS NOT NULL", (clean_p,))
                p_local = cur2.fetchone()[0]
                cur2.execute("SELECT count(*) FROM av WHERE performer = ?", (clean_p,))
                p_total = cur2.fetchone()[0]
                cur2.close()
                con2.close()

                self.vid_info.insert(tk.END, SEP + "\n", "sep")
                self.vid_info.insert(tk.END, "[ {} - 演员统计 ]\n".format(clean_p), "section_title")

                if p_grades:
                    p_buckets = {}
                    below_60 = 0
                    for g, cnt in p_grades:
                        if g < 60:
                            below_60 += cnt
                        else:
                            band = (g // 10) * 10
                            p_buckets[band] = p_buckets.get(band, 0) + cnt
                    max_cnt = max(max(p_buckets.values()), below_60) if p_buckets else below_60
                    if max_cnt == 0:
                        max_cnt = 1

                    for band in sorted(p_buckets.keys(), reverse=True):
                        label = "100分" if band >= 100 else "{}-{}分".format(band, band + 9)
                        cnt = p_buckets[band]
                        bar_len = max(1, int(cnt / max_cnt * 20))
                        bar = "|" + "=" * bar_len
                        color = self._grade_color(band)
                        tag_name = "pgrade_{}".format(band)
                        self.vid_info.tag_configure(tag_name, foreground=color, font=("Consolas", 10, "bold"))
                        self.vid_info.insert(tk.END, "  {:>8s} ".format(label))
                        self.vid_info.insert(tk.END, bar, tag_name)
                        self.vid_info.insert(tk.END, " {}部\n".format(cnt))
                    if below_60 > 0:
                        bar_len = max(1, int(below_60 / max_cnt * 20))
                        bar = "|" + "=" * bar_len
                        tag_name = "pgrade_below60"
                        self.vid_info.tag_configure(tag_name, foreground="#CC3333", font=("Consolas", 10, "bold"))
                        self.vid_info.insert(tk.END, "  {:>8s} ".format("60分以下"))
                        self.vid_info.insert(tk.END, bar, tag_name)
                        self.vid_info.insert(tk.END, " {}部\n".format(below_60))

                self.vid_info.insert(tk.END, "本地视频：{}部 | 全量视频：{}部\n".format(p_local, p_total))
            except Exception:
                pass

        # ========== 区块3: 全局统计 ==========
        try:
            con = get_db_conn()
            cur = con.cursor()
            cur.execute("SELECT count(*) FROM av WHERE local_path IS NOT NULL")
            total = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM av WHERE local_path IS NOT NULL AND grade IS NULL")
            ungraded = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM av WHERE local_path IS NOT NULL AND grade IS NULL AND zzz IS NULL")
            nozzz = cur.fetchone()[0]
            cur.execute(
                "SELECT grade, count(*) FROM av WHERE local_path IS NOT NULL AND grade IS NOT NULL AND grade >= 60 "
                "GROUP BY grade ORDER BY grade DESC")
            grade_dist = cur.fetchall()
            cur.close()
            con.close()

            self.vid_info.insert(tk.END, SEP + "\n", "sep")
            self.vid_info.insert(tk.END, "[ 全局统计 ]\n", "section_title")
            self.vid_info.insert(tk.END, "本地视频：{} | 未评分：{} | NoZZZ未评分：{}\n".format(total, ungraded, nozzz))
            if grade_dist:
                buckets = {}
                for g, cnt in grade_dist:
                    band = (g // 10) * 10
                    buckets[band] = buckets.get(band, 0) + cnt
                max_cnt = max(buckets.values()) if buckets else 1
                if max_cnt == 0:
                    max_cnt = 1
                for band in sorted(buckets.keys(), reverse=True):
                    label = "100分" if band >= 100 else "{}-{}分".format(band, band + 9)
                    cnt = buckets[band]
                    bar_len = max(1, int(cnt / max_cnt * 20))
                    bar = "|" + "=" * bar_len
                    color = self._grade_color(band)
                    tag_name = "ggrade_{}".format(band)
                    self.vid_info.tag_configure(tag_name, foreground=color, font=("Consolas", 10, "bold"))
                    self.vid_info.insert(tk.END, "  {:>8s} ".format(label))
                    self.vid_info.insert(tk.END, bar, tag_name)
                    self.vid_info.insert(tk.END, " {}部\n".format(cnt))
        except Exception:
            pass

        # ========== 额外提示 ==========
        if extra:
            self.vid_info.insert(tk.END, SEP + "\n", "sep")
            self.vid_info.insert(tk.END, extra + "\n", "extra_msg")

        # 刷新状态栏
        self._refresh_statusbar()

    @staticmethod
    def _grade_color(band):
        """评分段对应颜色：高分绿色，中分黄色，低分红色"""
        if band >= 90:
            return "#00AA00"
        elif band >= 80:
            return "#66AA00"
        elif band >= 70:
            return "#CC9900"
        else:
            return "#CC3333"

    def _rand_video(self, include_zzz):
        try:
            con = get_db_conn()
            cur = con.cursor()
            if include_zzz:
                cur.execute("SELECT {} FROM av WHERE local_path IS NOT NULL AND grade IS NULL ORDER BY RANDOM() LIMIT 1".format(AV_COLUMNS))
            else:
                cur.execute("SELECT {} FROM av WHERE local_path IS NOT NULL AND grade IS NULL AND zzz IS NULL ORDER BY RANDOM() LIMIT 1".format(AV_COLUMNS))
            rec = cur.fetchone()
            cur.close()
            con.close()
            if rec is None:
                self._update_video_info("没有符合条件的视频")
                return
            self.cur_video["key"] = rec[IDX_NUMBERS_NAME]
            self.cur_video["path"] = rec[IDX_LOCAL_PATH]
            self.cur_video["fanhao"] = rec[IDX_DESIGNATION]
            self.cur_video["performer"] = rec[IDX_PERFORMER]
            self.cur_video["mosaic"] = rec[IDX_MOSAIC]
            self.cur_video["video_name"] = rec[IDX_FILM_NAME]
            self.cur_video["grade"] = rec[IDX_GRADE] if len(rec) > IDX_GRADE else ""
            self.cur_video["created_at"] = rec[IDX_CREATED_AT] if len(rec) > IDX_CREATED_AT and rec[IDX_CREATED_AT] else ""
            self.cur_video["updated_at"] = rec[IDX_UPDATED_AT] if len(rec) > IDX_UPDATED_AT and rec[IDX_UPDATED_AT] else ""
            self.cur_video["last_action"] = rec[IDX_LAST_ACTION] if len(rec) > IDX_LAST_ACTION and rec[IDX_LAST_ACTION] else ""
            self._update_video_info()
        except Exception as e:
            self._update_video_info("数据库错误：{}".format(e))

    # --------------------------------------------------------
    #  搜索功能（功能10）
    # --------------------------------------------------------
    def _search_video(self):
        """按番号/演员/片名/关键词搜索视频"""
        keyword = self.vid_search_entry.get().strip()
        if not keyword:
            return
        search_type = self.vid_search_type.get()
        try:
            con = get_db_conn()
            cur = con.cursor()
            if search_type == "番号":
                cur.execute("SELECT {} FROM av WHERE designation LIKE ? LIMIT 50".format(AV_COLUMNS),
                            ("%{}%".format(keyword),))
            elif search_type == "演员":
                cur.execute("SELECT {} FROM av WHERE performer LIKE ? LIMIT 50".format(AV_COLUMNS),
                            ("%{}%".format(keyword),))
            elif search_type == "片名":
                cur.execute("SELECT {} FROM av WHERE film_name LIKE ? LIMIT 50".format(AV_COLUMNS),
                            ("%{}%".format(keyword),))
            else:  # 关键词（搜全部）
                cur.execute(
                    "SELECT {} FROM av WHERE designation LIKE ? OR performer LIKE ? OR film_name LIKE ? OR name LIKE ? LIMIT 50".format(AV_COLUMNS),
                    ("%{}%".format(keyword),) * 4)
            results = cur.fetchall()
            cur.close()
            con.close()
        except Exception as e:
            self._log("[搜索] 失败：{}".format(e))
            return

        if not results:
            self.vid_search_result_label.set("无结果")
            self._update_video_info("搜索「{}」无结果".format(keyword))
            return

        self.vid_search_result_label.set("{}条".format(len(results)))

        # 如果只有一条结果，直接选中
        if len(results) == 1:
            rec = results[0]
            self.cur_video["key"] = rec[IDX_NUMBERS_NAME]
            self.cur_video["path"] = rec[IDX_LOCAL_PATH] or ""
            self.cur_video["fanhao"] = rec[IDX_DESIGNATION]
            self.cur_video["performer"] = rec[IDX_PERFORMER]
            self.cur_video["mosaic"] = rec[IDX_MOSAIC]
            self.cur_video["video_name"] = rec[IDX_FILM_NAME]
            self.cur_video["grade"] = rec[IDX_GRADE] if rec[IDX_GRADE] is not None else ""
            self.cur_video["created_at"] = rec[IDX_CREATED_AT] if len(rec) > IDX_CREATED_AT and rec[IDX_CREATED_AT] else ""
            self.cur_video["updated_at"] = rec[IDX_UPDATED_AT] if len(rec) > IDX_UPDATED_AT and rec[IDX_UPDATED_AT] else ""
            self.cur_video["last_action"] = rec[IDX_LAST_ACTION] if len(rec) > IDX_LAST_ACTION and rec[IDX_LAST_ACTION] else ""
            self._update_video_info()
            return

        # 多条结果，在 vid_info 中显示列表
        self.vid_info.delete(1.0, tk.END)
        self.vid_info.config(state=tk.NORMAL)
        self.vid_info.tag_configure("section_title", foreground=self.theme_colors["section_title"],
                                     font=("Consolas", 10, "bold"))
        self.vid_info.insert(tk.END, "[ 搜索结果: {} ] 共{}条\n".format(keyword, len(results)), "section_title")

        for i, rec in enumerate(results[:30]):
            fanhao = rec[IDX_DESIGNATION] or rec[IDX_NUMBERS_NAME]
            performer = rec[IDX_PERFORMER] or ""
            grade = rec[IDX_GRADE] if rec[IDX_GRADE] is not None else "未评"
            has_path = "✓" if rec[IDX_LOCAL_PATH] else "✗"
            line = "{:>2}. [{}] {} | {} | 分:{}\n".format(i + 1, has_path, fanhao,
                                                            performer[:15], grade)
            self.vid_info.insert(tk.END, line)

        if len(results) > 30:
            self.vid_info.insert(tk.END, "... 还有{}条结果\n".format(len(results) - 30))

        self.vid_info.insert(tk.END, "\n提示: 双击列表中的番号可选中该视频\n")
        self.vid_info.config(state=tk.DISABLED)

        # 保存搜索结果供双击选择
        self._search_results = results

        # 绑定双击事件
        self.vid_info.bind("<Double-Button-1>", self._on_search_result_click)

    def _on_search_result_click(self, event):
        """双击搜索结果选中视频"""
        if not hasattr(self, "_search_results") or not self._search_results:
            return
        # 获取点击的行号
        index = self.vid_info.index("@{0},{1}".format(event.x, event.y))
        line_num = int(index.split(".")[0])
        # 搜索结果从第2行开始（第1行是标题）
        result_index = line_num - 2
        if 0 <= result_index < len(self._search_results):
            rec = self._search_results[result_index]
            self.cur_video["key"] = rec[IDX_NUMBERS_NAME]
            self.cur_video["path"] = rec[IDX_LOCAL_PATH] or ""
            self.cur_video["fanhao"] = rec[IDX_DESIGNATION]
            self.cur_video["performer"] = rec[IDX_PERFORMER]
            self.cur_video["mosaic"] = rec[IDX_MOSAIC]
            self.cur_video["video_name"] = rec[IDX_FILM_NAME]
            self.cur_video["grade"] = rec[IDX_GRADE] if rec[IDX_GRADE] is not None else ""
            self.cur_video["created_at"] = rec[IDX_CREATED_AT] if len(rec) > IDX_CREATED_AT and rec[IDX_CREATED_AT] else ""
            self.cur_video["updated_at"] = rec[IDX_UPDATED_AT] if len(rec) > IDX_UPDATED_AT and rec[IDX_UPDATED_AT] else ""
            self.cur_video["last_action"] = rec[IDX_LAST_ACTION] if len(rec) > IDX_LAST_ACTION and rec[IDX_LAST_ACTION] else ""
            self.vid_info.unbind("<Double-Button-1>")
            self._update_video_info()

    # --------------------------------------------------------
    #  撤销功能（功能9）
    # --------------------------------------------------------
    def _undo_last_action(self):
        """撤销最近一次操作"""
        record = self.action_history.pop()
        if not record:
            self.undo_status.set("无可撤销")
            return

        action = record["action"]
        key = record["key"]
        old = record["old_data"]

        try:
            if action == "grade":
                # 撤销评分
                if old.get("grade") is not None and old["grade"] != "":
                    link_db_cmd("UPDATE av SET grade = ? WHERE numbers_name = ?",
                                (old["grade"], key), action="撤销评分")
                else:
                    link_db_cmd("UPDATE av SET grade = NULL WHERE numbers_name = ?", (key,), action="撤销评分")
                self._log("[撤销] 评分已恢复：{} => {}".format(key, old.get("grade", "NULL")))

            elif action == "delete":
                # 撤销删除（恢复 local_path 和 exist_in_115）
                if old.get("local_path"):
                    link_db_cmd("UPDATE av SET local_path = ? WHERE numbers_name = ?",
                                (old["local_path"], key), action="撤销删除")
                if old.get("exist_in_115") is not None:
                    link_db_cmd("UPDATE av SET exist_in_115 = ? WHERE numbers_name = ?",
                                (old["exist_in_115"], key), action="撤销删除")
                self._log("[撤销] 删除已恢复：{} (路径恢复，但文件已被物理删除)".format(key))

            elif action == "black_add":
                link_db_cmd("DELETE FROM black_table WHERE name = ?", (old.get("name", ""),))
                self._log("[撤销] 黑名单已移除：{}".format(old.get("name", "")))

            elif action == "black_remove":
                link_db_cmd("INSERT OR IGNORE INTO black_table (name) VALUES (?)", (old.get("name", ""),))
                self._log("[撤销] 黑名单已恢复：{}".format(old.get("name", "")))

            elif action == "good_add":
                link_db_cmd("DELETE FROM good_performer WHERE name = ?", (old.get("name", ""),))
                self._log("[撤销] 关注已移除：{}".format(old.get("name", "")))

            elif action == "good_remove":
                link_db_cmd("INSERT OR IGNORE INTO good_performer (name) VALUES (?)", (old.get("name", ""),))
                self._log("[撤销] 关注已恢复：{}".format(old.get("name", "")))

            # 如果撤销的是当前视频的操作，刷新显示
            if key == self.cur_video.get("key"):
                # 重新从数据库加载当前视频信息
                con = get_db_conn()
                cur = con.cursor()
                cur.execute("SELECT {} FROM av WHERE numbers_name = ?".format(AV_COLUMNS), (key,))
                rec = cur.fetchone()
                cur.close()
                con.close()
                if rec:
                    self.cur_video["key"] = rec[IDX_NUMBERS_NAME]
                    self.cur_video["path"] = rec[IDX_LOCAL_PATH] or ""
                    self.cur_video["fanhao"] = rec[IDX_DESIGNATION]
                    self.cur_video["performer"] = rec[IDX_PERFORMER]
                    self.cur_video["mosaic"] = rec[IDX_MOSAIC]
                    self.cur_video["video_name"] = rec[IDX_FILM_NAME]
                    self.cur_video["grade"] = rec[IDX_GRADE] if rec[IDX_GRADE] is not None else ""
                    self.cur_video["created_at"] = rec[IDX_CREATED_AT] if len(rec) > IDX_CREATED_AT and rec[IDX_CREATED_AT] else ""
                    self.cur_video["updated_at"] = rec[IDX_UPDATED_AT] if len(rec) > IDX_UPDATED_AT and rec[IDX_UPDATED_AT] else ""
                    self.cur_video["last_action"] = rec[IDX_LAST_ACTION] if len(rec) > IDX_LAST_ACTION and rec[IDX_LAST_ACTION] else ""
                    self._update_video_info("已撤销：{}".format(action))

            self.undo_status.set("")
        except Exception as e:
            self._log("[撤销] 失败：{}".format(e))
            self.undo_status.set("撤销失败")

    def _play_video(self):
        path = self.cur_video["path"]
        if not path or not os.path.isfile(path):
            link_db_cmd("UPDATE av SET local_path = NULL WHERE numbers_name = ?", (self.cur_video["key"],), action="路径不可达")
            link_db_cmd("UPDATE av SET exist_in_115 = NULL WHERE numbers_name = ?", (self.cur_video["key"],), action="路径不可达")
            link_db_cmd("UPDATE av SET grade = 10 WHERE numbers_name = ?", (self.cur_video["key"],), action="路径不可达")
            self.cur_video["grade"] = 10
            self._update_video_info("路径不可达，已更新数据库，评分设为10")
            return
        # 使用 subprocess 替代 os.startfile，避免 GIL 崩溃
        import subprocess
        subprocess.Popen(["cmd", "/c", "start", "", path], shell=False)

    def _grade_video(self):
        try:
            grade = int(self.vid_grade_combo.get())
        except ValueError:
            messagebox.showerror("错误", "分数必须是整数")
            return
        if not self.cur_video["key"]:
            self._update_video_info("当前没有选中视频")
            return
        # 记录操作历史（功能9）
        old_grade = self.cur_video.get("grade", "")
        self.action_history.push("grade", self.cur_video["key"], {"grade": old_grade})
        self.undo_status.set("可撤销: 评分")
        link_db_cmd("UPDATE av SET grade = ? WHERE numbers_name = ?", (grade, self.cur_video["key"]), action="评分")
        self.cur_video["grade"] = grade
        self._update_video_info("评分完成：{}".format(grade))

    def _play_good_video(self):
        try:
            grade = int(self.vid_grade_combo.get())
        except ValueError:
            messagebox.showerror("错误", "分数必须是整数")
            return
        try:
            con = get_db_conn()
            cur = con.cursor()
            cur.execute("SELECT {} FROM av WHERE local_path IS NOT NULL AND grade >= ? ORDER BY RANDOM() LIMIT 1".format(AV_COLUMNS), (grade,))
            rec = cur.fetchone()
            cur.close()
            con.close()
            if rec is None:
                self._update_video_info("没有>={}分的视频".format(grade))
                return
            self.cur_video["key"] = rec[IDX_NUMBERS_NAME]
            self.cur_video["path"] = rec[IDX_LOCAL_PATH]
            self.cur_video["fanhao"] = rec[IDX_DESIGNATION]
            self.cur_video["performer"] = rec[IDX_PERFORMER]
            self.cur_video["mosaic"] = rec[IDX_MOSAIC]
            self.cur_video["video_name"] = rec[IDX_FILM_NAME]
            self.cur_video["grade"] = rec[IDX_GRADE] if len(rec) > IDX_GRADE else ""
            self.cur_video["created_at"] = rec[IDX_CREATED_AT] if len(rec) > IDX_CREATED_AT and rec[IDX_CREATED_AT] else ""
            self.cur_video["updated_at"] = rec[IDX_UPDATED_AT] if len(rec) > IDX_UPDATED_AT and rec[IDX_UPDATED_AT] else ""
            self.cur_video["last_action"] = rec[IDX_LAST_ACTION] if len(rec) > IDX_LAST_ACTION and rec[IDX_LAST_ACTION] else ""
            self._update_video_info()
        except Exception as e:
            self._update_video_info("数据库错误：{}".format(e))

    def _delete_video(self):
        key = self.cur_video["key"]
        path = self.cur_video["path"]
        if not key:
            self._update_video_info("当前没有选中视频")
            return
        # 确认弹窗
        if not messagebox.askyesno("确认删除", "确定要删除当前视频吗？\n番号: {}".format(self.cur_video.get("fanhao", key))):
            return
        # 记录操作历史（功能9）
        self.action_history.push("delete", key, {
            "local_path": path,
            "exist_in_115": 1,
        })
        self.undo_status.set("可撤销: 删除(文件不可恢复)")
        link_db_cmd("UPDATE av SET local_path = NULL WHERE numbers_name = ?", (key,), action="删除")
        link_db_cmd("UPDATE av SET exist_in_115 = NULL WHERE numbers_name = ?", (key,), action="删除")
        if path and os.path.exists(path):
            os.remove(path)
            self._update_video_info("已删除文件并更新数据库")
        else:
            self._update_video_info("文件不存在，已更新数据库")

    def _toggle_performer(self, list_type, add):
        performer = self.cur_video["performer"]
        if not performer:
            self._update_video_info("当前演员为空")
            return
        # 清理 HTML 残留，避免脏数据入库
        clean_name = _clean_performer(performer)
        if list_type == "black":
            if add:
                if judge_performer(performer):
                    self._update_video_info("演员已在黑名单中")
                    return
                if judge_performer_is_good(performer):
                    self._update_video_info("请先删除白名单：{}".format(clean_name))
                    return
                link_db_cmd("INSERT INTO black_table (name) VALUES (?)", (clean_name,))
                self.action_history.push("black_add", self.cur_video["key"], {"name": clean_name})
                self.undo_status.set("可撤销: +黑名单")
                self._update_video_info("已加入黑名单：{}".format(clean_name))
            else:
                if not judge_performer(performer):
                    self._update_video_info("演员不在黑名单中")
                    return
                # 同时删除清理后和原始的名字，确保脏数据也能清理
                link_db_cmd("DELETE FROM black_table WHERE name = ?", (clean_name,))
                if performer.strip() != clean_name:
                    link_db_cmd("DELETE FROM black_table WHERE name = ?", (performer.strip(),))
                self.action_history.push("black_remove", self.cur_video["key"], {"name": clean_name})
                self.undo_status.set("可撤销: -黑名单")
                self._update_video_info("已从黑名单移除：{}".format(clean_name))
        elif list_type == "good":
            if add:
                if judge_performer_is_good(performer):
                    self._update_video_info("演员已在关注名单中")
                    return
                link_db_cmd("INSERT INTO good_performer (name) VALUES (?)", (clean_name,))
                self.action_history.push("good_add", self.cur_video["key"], {"name": clean_name})
                self.undo_status.set("可撤销: +关注")
                self._update_video_info("已加入关注名单：{}".format(clean_name))
            else:
                if not judge_performer_is_good(performer):
                    self._update_video_info("演员不在关注名单中")
                    return
                link_db_cmd("DELETE FROM good_performer WHERE name = ?", (clean_name,))
                if performer.strip() != clean_name:
                    link_db_cmd("DELETE FROM good_performer WHERE name = ?", (performer.strip(),))
                self.action_history.push("good_remove", self.cur_video["key"], {"name": clean_name})
                self.undo_status.set("可撤销: -关注")
                self._update_video_info("已从关注名单移除：{}".format(clean_name))

    # ============ Tab 3: 磁力生成 ============
    def _build_magnet_tab(self):
        tab = ttk.Frame(self.nb)
        self.nb.add(tab, text="磁力生成")

        # 第一行：数量 + 排序 + 筛选
        row1 = ttk.Frame(tab)
        row1.pack(fill=tk.X, padx=10, pady=4)

        ttk.Label(row1, text="生成数量:").pack(side=tk.LEFT)
        self.magnet_num = ttk.Combobox(row1, width=6, values=[str(i) for i in range(10, 210, 10)])
        self.magnet_num.set("60")
        self.magnet_num.pack(side=tk.LEFT, padx=4)

        ttk.Label(row1, text="排序:").pack(side=tk.LEFT, padx=(10, 0))
        self.magnet_sort = ttk.Combobox(row1, width=12, values=["随机", "热度降序", "查看降序", "最新入库"])
        self.magnet_sort.set("随机")
        self.magnet_sort.pack(side=tk.LEFT, padx=4)

        self.magnet_white_only = tk.BooleanVar(value=False)
        ttk.Checkbutton(row1, text="仅白名单演员", variable=self.magnet_white_only).pack(side=tk.LEFT, padx=10)

        self.magnet_show_info = tk.BooleanVar(value=True)
        ttk.Checkbutton(row1, text="显示影片信息", variable=self.magnet_show_info).pack(side=tk.LEFT, padx=10)

        # 第二行：演员搜索 + 类型筛选
        row2 = ttk.Frame(tab)
        row2.pack(fill=tk.X, padx=10, pady=4)

        ttk.Label(row2, text="演员搜索:").pack(side=tk.LEFT)
        self.magnet_performer = ttk.Entry(row2, width=15)
        self.magnet_performer.pack(side=tk.LEFT, padx=4)

        ttk.Label(row2, text="类型:").pack(side=tk.LEFT, padx=(10, 0))
        self.magnet_mosaic = ttk.Combobox(row2, width=10, values=["全部", "有码", "无码"])
        self.magnet_mosaic.set("全部")
        self.magnet_mosaic.pack(side=tk.LEFT, padx=4)

        ttk.Label(row2, text="最小大小:").pack(side=tk.LEFT, padx=(10, 0))
        self.magnet_min_size = ttk.Entry(row2, width=6)
        self.magnet_min_size.insert(0, "0")
        self.magnet_min_size.pack(side=tk.LEFT, padx=4)
        ttk.Label(row2, text="GB").pack(side=tk.LEFT)

        # 第三行：操作按钮
        row3 = ttk.Frame(tab)
        row3.pack(fill=tk.X, padx=10, pady=4)

        ttk.Button(row3, text="生成磁力", command=self._gen_magnet).pack(side=tk.LEFT, padx=4)
        ttk.Button(row3, text="全部白名单磁力", command=self._gen_magnet_whitelist).pack(side=tk.LEFT, padx=4)
        ttk.Button(row3, text="复制磁力链接", command=self._copy_magnet).pack(side=tk.LEFT, padx=4)
        ttk.Button(row3, text="保存到文件", command=self._save_magnet).pack(side=tk.LEFT, padx=4)
        ttk.Button(row3, text="清空", command=lambda: self.magnet_text.delete(1.0, tk.END)).pack(side=tk.LEFT, padx=4)

        # 结果区
        self.magnet_text = scrolledtext.ScrolledText(tab, font=("Consolas", 10))
        self.magnet_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

    def _gen_magnet(self):
        try:
            num = int(self.magnet_num.get())
        except ValueError:
            messagebox.showerror("错误", "数量必须是整数")
            return

        white_only = self.magnet_white_only.get()
        show_info = self.magnet_show_info.get()
        performer_kw = self.magnet_performer.get().strip()
        mosaic_filter = self.magnet_mosaic.get()
        sort_by = self.magnet_sort.get()
        try:
            min_size_gb = float(self.magnet_min_size.get())
        except ValueError:
            min_size_gb = 0

        try:
            con = get_db_conn()
            cur = con.cursor()

            # 构建 SQL：把过滤条件尽量下推到 SQL 层
            conditions = ["local_path IS NULL", "grade IS NULL", "magnet IS NOT NULL"]
            params = []

            # 排除无码破解（-UC 后缀）
            conditions.append("numbers_name NOT LIKE '%%-UC'")

            # 有码/无码筛选
            if mosaic_filter == "有码":
                conditions.append("mosaic = '有码'")
            elif mosaic_filter == "无码":
                conditions.append("mosaic = '无码'")

            # 演员搜索
            if performer_kw:
                conditions.append("performer LIKE ?")
                params.append("%{}%".format(performer_kw))

            # 最小大小（解析 GB）
            # SQLite 不支持 REGEXP_REPLACE，大小过滤移到 Python 层处理
            # min_size_gb 过滤在结果返回后用 Python 实现

            where_clause = " AND ".join(conditions)

            # 排序
            if sort_by == "热度降序":
                order_clause = "hot_num DESC"
            elif sort_by == "查看降序":
                order_clause = "view DESC"
            elif sort_by == "最新入库":
                order_clause = "zzz DESC"
            else:
                order_clause = "RANDOM()"

            sql = "SELECT numbers_name, performer, magnet, size, hot_num, film_name, mosaic FROM av WHERE {} ORDER BY {} LIMIT ?".format(
                where_clause, order_clause
            )
            params.append(num)

            cur.execute(sql, params)
            records = cur.fetchall()
            cur.close()
            con.close()

            # 生成结果
            self.magnet_text.delete(1.0, tk.END)
            magnets_only = []  # 纯磁力链接列表（用于复制）
            skipped_blacklist = 0
            skipped_white = 0

            for rec in records:
                fanhao, performer, magnet, size, hot_num, film_name, mosaic = rec

                # Python 层大小过滤（SQLite 不支持 REGEXP_REPLACE）
                if min_size_gb > 0:
                    try:
                        num_str = re.sub(r'[^0-9.]', '', size or '0')
                        size_val = float(num_str)
                        # 判断单位：M 还是 G
                        if size and ('M' in size.upper()):
                            size_val = size_val / 1024  # MB → GB
                        if size_val < min_size_gb:
                            continue
                    except (ValueError, ZeroDivisionError):
                        pass

                # 黑名单过滤
                if judge_performer(performer):
                    skipped_blacklist += 1
                    continue

                # 白名单过滤
                if white_only and not judge_performer_is_good(performer):
                    skipped_white += 1
                    continue

                magnets_only.append(magnet)

                if show_info:
                    # 带信息格式：磁力链接 + 影片信息
                    info_line = "{} | {} | {} | {} | 热度:{}".format(
                        fanhao, performer, size, film_name[:25] if film_name else "", hot_num
                    )
                    self.magnet_text.insert(tk.END, magnet + "\n")
                    self.magnet_text.insert(tk.END, "  >> " + info_line + "\n\n")
                else:
                    self.magnet_text.insert(tk.END, magnet + "\n")

            # 保存纯磁力列表供复制用
            self._magnets_list = magnets_only

            # 统计汇报
            self._log("[磁力] 查询到 {} 条，黑名单过滤 {} 条，非白名单过滤 {} 条，最终 {} 条".format(
                len(records), skipped_blacklist, skipped_white, len(magnets_only)))

        except Exception as e:
            self._log("[磁力] 生成失败：{}".format(e))

    def _copy_magnet(self):
        """复制纯磁力链接（不含影片信息）到剪贴板"""
        if hasattr(self, '_magnets_list') and self._magnets_list:
            text = "\n".join(self._magnets_list)
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self._log("[磁力] 已复制 {} 条磁力链接到剪贴板".format(len(self._magnets_list)))
        else:
            # 兜底：从文本框提取
            text = self.magnet_text.get(1.0, tk.END).strip()
            if text:
                # 只提取 magnet:? 开头的行
                lines = [l.strip() for l in text.splitlines() if l.strip().startswith("magnet:")]
                if lines:
                    self.root.clipboard_clear()
                    self.root.clipboard_append("\n".join(lines))
                    self._log("[磁力] 已复制 {} 条磁力链接到剪贴板".format(len(lines)))

    def _gen_magnet_whitelist(self):
        """遍历数据库所有记录，仅返回白名单演员的磁力链接"""
        show_info = self.magnet_show_info.get()

        try:
            con = get_db_conn()
            cur = con.cursor()

            # 查询所有有磁力链接且未下载/未评分的记录，排除-UC
            sql = (
                "SELECT numbers_name, performer, magnet, size, hot_num, film_name, mosaic "
                "FROM av WHERE local_path IS NULL AND grade IS NULL AND magnet IS NOT NULL "
                "AND numbers_name NOT LIKE '%%-UC'"
            )
            cur.execute(sql)
            records = cur.fetchall()
            cur.close()
            con.close()

            self.magnet_text.delete(1.0, tk.END)
            magnets_only = []
            skipped_blacklist = 0
            skipped_not_white = 0

            for rec in records:
                fanhao, performer, magnet, size, hot_num, film_name, mosaic = rec

                # 黑名单过滤
                if judge_performer(performer):
                    skipped_blacklist += 1
                    continue

                # 非白名单过滤
                if not judge_performer_is_good(performer):
                    skipped_not_white += 1
                    continue

                magnets_only.append(magnet)

                if show_info:
                    info_line = "{} | {} | {} | {} | 热度:{}".format(
                        fanhao, performer, size, film_name[:25] if film_name else "", hot_num
                    )
                    self.magnet_text.insert(tk.END, magnet + "\n")
                    self.magnet_text.insert(tk.END, "  >> " + info_line + "\n\n")
                else:
                    self.magnet_text.insert(tk.END, magnet + "\n")

            # 保存纯磁力列表供复制用
            self._magnets_list = magnets_only

            self._log("[白名单磁力] 共 {} 条记录，黑名单过滤 {} 条，非白名单过滤 {} 条，最终 {} 条".format(
                len(records), skipped_blacklist, skipped_not_white, len(magnets_only)))

        except Exception as e:
            self._log("[白名单磁力] 生成失败：{}".format(e))

    def _save_magnet(self):
        """保存磁力链接到文件"""
        text = self.magnet_text.get(1.0, tk.END).strip()
        if not text:
            self._log("[磁力] 没有内容可保存")
            return

        fpath = filedialog.asksaveasfilename(
            title="保存磁力链接",
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
            initialfile="magnet-{}.txt".format(time.strftime("%Y-%m-%d")),
        )
        if fpath:
            try:
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(text)
                self._log("[磁力] 已保存到：{}".format(fpath))
            except Exception as e:
                self._log("[磁力] 保存失败：{}".format(e))

    # ============ Tab 4: 数据库管理 ============
    def _build_db_tab(self):
        tab = ttk.Frame(self.nb)
        self.nb.add(tab, text="数据库管理")

        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill=tk.X, padx=10, pady=6)

        ttk.Button(btn_frame, text="刷新115文件到数据库", command=self._run_check_115).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="校验番号格式", command=self._run_check_designation).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="清理无效路径", command=self._run_clean_db).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="去重无码版本", command=self._run_only_one).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="外部视频入库", command=self._run_other_video).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="查看统计", command=self._show_db_stats).pack(side=tk.LEFT, padx=4)

        # 第二行：JSON 导入导出 + MySQL 迁移
        btn_frame2 = ttk.Frame(tab)
        btn_frame2.pack(fill=tk.X, padx=10, pady=2)

        ttk.Button(btn_frame2, text="导出JSON", command=self._export_json).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame2, text="导入JSON", command=self._import_json).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame2, text="从MySQL迁移", command=self._migrate_from_mysql).pack(side=tk.LEFT, padx=4)

        # 路径输入
        path_frame = ttk.Frame(tab)
        path_frame.pack(fill=tk.X, padx=10, pady=2)
        ttk.Label(path_frame, text="115路径:").pack(side=tk.LEFT)
        self.db_115_path = ttk.Entry(path_frame, width=50)
        self.db_115_path.insert(0, self.config.get("db_115_path", "Z:/115open/Hp/"))
        self.db_115_path.pack(side=tk.LEFT, padx=4)

        self.db_result = scrolledtext.ScrolledText(tab, font=("Consolas", 10))
        self.db_result.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

    def _run_in_thread(self, func):
        """在子线程中运行函数，避免阻塞 UI"""
        t = threading.Thread(target=func, daemon=True)
        t.start()

    def _run_check_115(self):
        path = self.db_115_path.get().strip()
        if not path:
            messagebox.showerror("错误", "请输入115路径")
            return
        self._log("开始扫描115文件：{}".format(path))
        self._run_in_thread(lambda: self._check_115_worker(path))

    def _check_115_worker(self, path):
        try:
            # 批量操作：复用同一连接，减少锁竞争
            con = get_db_conn(timeout=30)
            self._check_115_recursive(path, con)
            con.commit()
            con.close()
            self._log("115文件扫描完成")
        except Exception as e:
            self._log("扫描失败：{}".format(e))

    def _check_115_recursive(self, path, con):
        try:
            file_list = os.listdir(path)
        except PermissionError:
            return
        for file in file_list:
            self._log("[文件] 处理：{}".format(path + file))
            if file in WHITE_LIST:
                continue
            if os.path.isdir(path + "/" + file):
                self._check_115_recursive(path + file + "/", con)
                continue
            if "-UC" in file:
                continue
            ret = re.findall(r"[0-9a-zA-Z]+-[0-9a-zA-Z]+", file)
            if not ret:
                continue
            for temp_ret in ret:
                try:
                    cur = con.cursor()
                    cur.execute("SELECT {} FROM av WHERE designation = ?".format(AV_COLUMNS), (temp_ret,))
                    rec = cur.fetchone()
                    while rec is not None:
                        cur2 = con.cursor()
                        s, v = _append_auto_fields("UPDATE av SET exist_in_115 = ? WHERE numbers_name = ?", (1, rec[IDX_NUMBERS_NAME]), action="检测115")
                        cur2.execute(s, v)
                        s, v = _append_auto_fields("UPDATE av SET local_path = ? WHERE numbers_name = ?", (path + file, rec[IDX_NUMBERS_NAME]), action="检测115")
                        cur2.execute(s, v)
                        cur2.close()
                        rec = cur.fetchone()
                    cur.close()
                    # 每100个文件提交一次，平衡性能和锁持有时间
                    if not hasattr(self, '_check_115_count'):
                        self._check_115_count = 0
                    self._check_115_count += 1
                    if self._check_115_count % 100 == 0:
                        con.commit()
                        self._log("[115扫描] 已处理 {} 个文件，已提交".format(self._check_115_count))
                except Exception as e:
                    self._log("数据库错误：{}".format(e))

    def _run_check_designation(self):
        self._log("开始校验番号格式...")
        self._run_in_thread(self._check_designation_worker)

    def _check_designation_worker(self):
        try:
            con = get_db_conn()
            cur = con.cursor()
            cur.execute("SELECT {} FROM av".format(AV_COLUMNS))
            rec = cur.fetchone()
            fixed = 0
            while rec is not None:
                true_fanhao = rec[IDX_DESIGNATION]
                fanhao = rec[IDX_NUMBERS_NAME]
                ret = re.findall(r"[0-9a-zA-Z]+-[0-9a-zA-Z]+", true_fanhao)
                if ret and ret[0] != true_fanhao:
                    self._log("[修正] {} => {}".format(true_fanhao, ret[0]))
                    link_db_cmd("UPDATE av SET designation = ? WHERE numbers_name = ?", (ret[0], fanhao), action="番号修正")
                    fixed += 1
                rec = cur.fetchone()
            cur.close()
            con.close()
            self._log("番号校验完成，修正 {} 条".format(fixed))
        except Exception as e:
            self._log("校验失败：{}".format(e))

    def _run_clean_db(self):
        self._log("开始清理无效路径...")
        self._run_in_thread(self._clean_db_worker)

    def _clean_db_worker(self):
        try:
            con = get_db_conn()
            cur = con.cursor()
            cur.execute("SELECT {} FROM av WHERE local_path IS NOT NULL".format(AV_COLUMNS))
            rec = cur.fetchone()
            cleaned = 0
            while rec is not None:
                curr_path = rec[IDX_LOCAL_PATH]
                curr_name = rec[IDX_NUMBERS_NAME]
                if curr_path and not os.path.isfile(curr_path):
                    link_db_cmd("UPDATE av SET local_path = NULL WHERE numbers_name = ?", (curr_name,), action="路径清理")
                    link_db_cmd("UPDATE av SET exist_in_115 = NULL WHERE numbers_name = ?", (curr_name,), action="路径清理")
                    self._log("[清理] 路径无效：{}".format(curr_path))
                    cleaned += 1
                rec = cur.fetchone()
            cur.close()
            con.close()
            self._log("清理完成，共清理 {} 条".format(cleaned))
        except Exception as e:
            self._log("清理失败：{}".format(e))

    def _run_only_one(self):
        self._log("开始去重无码版本...")
        self._run_in_thread(self._only_one_worker)

    def _only_one_worker(self):
        try:
            con = get_db_conn()
            cur = con.cursor()
            cur.execute("SELECT {} FROM av WHERE mosaic = ?".format(AV_COLUMNS), ("无码",))
            rec = cur.fetchone()
            removed = 0
            while rec is not None:
                fanhao = rec[IDX_DESIGNATION]
                curr_path = rec[IDX_LOCAL_PATH]
                curr_name = rec[IDX_NUMBERS_NAME]
                if curr_path is not None:
                    cur2 = con.cursor()
                    cur2.execute("SELECT count(*) FROM av WHERE designation = ?", (fanhao,))
                    nums = cur2.fetchone()[0]
                    cur2.close()
                    if nums > 1:
                        link_db_cmd("UPDATE av SET local_path = NULL WHERE numbers_name = ?", (curr_name,), action="去重清理")
                        self._log("[去重] 移除无码版本路径：{}".format(curr_path))
                        removed += 1
                rec = cur.fetchone()
            cur.close()
            con.close()
            self._log("去重完成，移除 {} 条".format(removed))
        except Exception as e:
            self._log("去重失败：{}".format(e))

    def _run_other_video(self):
        path = self.db_115_path.get().strip()
        if not path:
            messagebox.showerror("错误", "请输入路径")
            return
        self._log("开始扫描外部视频：{}".format(path))
        self._run_in_thread(lambda: self._other_video_worker(path))

    def _other_video_worker(self, path):
        try:
            file_list = os.listdir(path)
            added = 0
            for file in file_list:
                cur_file_path = path + file
                con = get_db_conn()
                cur = con.cursor()
                cur.execute("SELECT 1 FROM av WHERE local_path = ?", (cur_file_path,))
                rec = cur.fetchone()
                cur.close()
                con.close()
                if rec is not None:
                    continue
                self._log("[外部视频] 添加：{}".format(cur_file_path))
                con = get_db_conn()
                cur2 = con.cursor()
                cur2.execute("SELECT count(*) FROM av WHERE zzz IS NOT NULL")
                numbers = cur2.fetchone()[0]
                cur2.close()
                con.close()
                numbers_name = "zzz-{}".format(numbers + 1)
                try:
                    os.rename(cur_file_path, path + numbers_name + " " + file)
                except Exception:
                    continue
                new_path = path + numbers_name + " " + file
                now_str = time.strftime("%Y-%m-%d %H:%M:%S")
                link_db_cmd(
                    "INSERT INTO av (numbers_name, name, performer, mosaic, designation, film_name, local_path, zzz, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [numbers_name, file, "zzz", "有码", numbers_name, numbers_name, new_path, numbers + 1, now_str, now_str],
                )
                added += 1
            self._log("外部视频入库完成，新增 {} 条".format(added))
        except Exception as e:
            self._log("外部视频入库失败：{}".format(e))

    def _show_db_stats(self):
        """查看统计（功能11：可视化仪表盘）"""
        try:
            con = get_db_conn()
            cur = con.cursor()

            # 基础统计
            stats = {}
            queries = [
                ("total", "SELECT count(*) FROM av"),
                ("local", "SELECT count(*) FROM av WHERE local_path IS NOT NULL"),
                ("ungraded", "SELECT count(*) FROM av WHERE grade IS NULL"),
                ("has_magnet", "SELECT count(*) FROM av WHERE magnet IS NOT NULL"),
                ("blacklist", "SELECT count(*) FROM black_table"),
                ("whitelist", "SELECT count(*) FROM good_performer"),
                ("mosaic_yes", "SELECT count(*) FROM av WHERE mosaic = '有码'"),
                ("mosaic_no", "SELECT count(*) FROM av WHERE mosaic = '无码'"),
            ]
            for key, sql in queries:
                cur.execute(sql)
                stats[key] = cur.fetchone()[0]

            # 评分分布
            cur.execute(
                "SELECT grade, count(*) FROM av WHERE grade IS NOT NULL AND grade >= 0 "
                "GROUP BY grade ORDER BY grade DESC")
            grade_dist = cur.fetchall()

            # TOP 演员
            cur.execute(
                "SELECT performer, count(*) as cnt FROM av "
                "WHERE performer IS NOT NULL AND performer != '' "
                "GROUP BY performer ORDER BY cnt DESC LIMIT 15")
            top_performers = cur.fetchall()

            # 月度入库趋势（按 numbers_name 中的日期部分或按记录顺序近似）
            cur.execute("SELECT count(*) FROM av WHERE local_path IS NOT NULL AND grade IS NOT NULL")
            graded_local = cur.fetchone()[0]

            cur.close()
            con.close()

            # === 生成可视化图表 ===
            self.db_result.delete(1.0, tk.END)
            self.db_result.config(state=tk.NORMAL)

            # 颜色方案
            c = self.theme_colors
            title_fg = c.get("accent", "#3366CC")
            bar_good = "#2ECC71"
            bar_warn = "#F39C12"
            bar_bad = "#E74C3C"
            bar_blue = "#3498DB"
            bar_purple = "#9B59B6"
            bar_teal = "#1ABC9C"

            # 标题
            self.db_result.tag_configure("title", foreground=title_fg, font=("Consolas", 12, "bold"))
            self.db_result.tag_configure("subtitle", foreground=title_fg, font=("Consolas", 10, "bold"))
            self.db_result.tag_configure("bar_g", foreground=bar_good, font=("Consolas", 10, "bold"))
            self.db_result.tag_configure("bar_w", foreground=bar_warn, font=("Consolas", 10, "bold"))
            self.db_result.tag_configure("bar_b", foreground=bar_bad, font=("Consolas", 10, "bold"))
            self.db_result.tag_configure("bar_bl", foreground=bar_blue, font=("Consolas", 10, "bold"))
            self.db_result.tag_configure("bar_p", foreground=bar_purple, font=("Consolas", 10, "bold"))
            self.db_result.tag_configure("bar_t", foreground=bar_teal, font=("Consolas", 10, "bold"))
            self.db_result.tag_configure("sep", foreground="#AAAAAA")

            self.db_result.insert(tk.END, "╔══════════════════════════════════════╗\n", "title")
            self.db_result.insert(tk.END, "║       syaA 数据统计仪表盘           ║\n", "title")
            self.db_result.insert(tk.END, "╚══════════════════════════════════════╝\n\n", "title")

            # --- 概览卡片 ---
            self.db_result.insert(tk.END, "▎ 总览\n", "subtitle")
            self.db_result.insert(tk.END, "  全量视频: {}  |  本地视频: {}  |  已评分: {}\n".format(
                stats["total"], stats["local"], graded_local))
            self.db_result.insert(tk.END, "  未评分: {}  |  有磁力: {}  |  黑名单: {}  |  关注: {}\n\n".format(
                stats["ungraded"], stats["has_magnet"], stats["blacklist"], stats["whitelist"]))

            # --- 码制比例 ---
            self.db_result.insert(tk.END, "▎ 码制比例\n", "subtitle")
            total_mosaic = stats["mosaic_yes"] + stats["mosaic_no"]
            if total_mosaic > 0:
                yes_pct = stats["mosaic_yes"] / total_mosaic * 100
                no_pct = stats["mosaic_no"] / total_mosaic * 100
                yes_bar_len = max(1, int(yes_pct / 100 * 30))
                no_bar_len = max(1, int(no_pct / 100 * 30))
                self.db_result.insert(tk.END, "  有码 ", "bar_bl")
                self.db_result.insert(tk.END, "█" * yes_bar_len, "bar_bl")
                self.db_result.insert(tk.END, " {} ({:.1f}%)\n".format(stats["mosaic_yes"], yes_pct))
                self.db_result.insert(tk.END, "  无码 ", "bar_t")
                self.db_result.insert(tk.END, "█" * no_bar_len, "bar_t")
                self.db_result.insert(tk.END, " {} ({:.1f}%)\n\n".format(stats["mosaic_no"], no_pct))

            # --- 评分分布图 ---
            self.db_result.insert(tk.END, "▎ 评分分布\n", "subtitle")
            if grade_dist:
                buckets = {}
                below_60 = 0
                for g, cnt in grade_dist:
                    if g < 60:
                        below_60 += cnt
                    else:
                        band = (g // 10) * 10
                        buckets[band] = buckets.get(band, 0) + cnt
                max_cnt = max(max(buckets.values()), below_60) if buckets else below_60
                if max_cnt == 0:
                    max_cnt = 1

                for band in sorted(buckets.keys(), reverse=True):
                    label = "100分" if band >= 100 else "{}-{}分".format(band, band + 9)
                    cnt = buckets[band]
                    bar_len = max(1, int(cnt / max_cnt * 25))
                    if band >= 90:
                        tag = "bar_g"
                    elif band >= 70:
                        tag = "bar_w"
                    else:
                        tag = "bar_b"
                    self.db_result.insert(tk.END, "  {:>8s} ".format(label))
                    self.db_result.insert(tk.END, "█" * bar_len, tag)
                    self.db_result.insert(tk.END, " {}部\n".format(cnt))
                if below_60 > 0:
                    bar_len = max(1, int(below_60 / max_cnt * 25))
                    self.db_result.insert(tk.END, "  {:>8s} ".format("60分以下"))
                    self.db_result.insert(tk.END, "█" * bar_len, "bar_b")
                    self.db_result.insert(tk.END, " {}部\n".format(below_60))

            self.db_result.insert(tk.END, "\n")

            # --- TOP 演员 ---
            self.db_result.insert(tk.END, "▎ TOP 15 演员（按视频数量）\n", "subtitle")
            if top_performers:
                max_cnt = top_performers[0][1] if top_performers else 1
                for i, (name, cnt) in enumerate(top_performers):
                    bar_len = max(1, int(cnt / max_cnt * 20))
                    clean_name = _clean_performer(name) if name else "?"
                    display_name = clean_name[:12] + (".." if len(clean_name) > 12 else "")
                    self.db_result.insert(tk.END, "  {:>2}. {:<14s}".format(i + 1, display_name))
                    self.db_result.insert(tk.END, "█" * bar_len, "bar_p")
                    self.db_result.insert(tk.END, " {}部\n".format(cnt))

            self.db_result.insert(tk.END, "\n" + "─" * 40 + "\n", "sep")
            self.db_result.insert(tk.END, "生成时间: {}\n".format(time.strftime("%Y-%m-%d %H:%M:%S")))

            self.db_result.config(state=tk.DISABLED)

        except Exception as e:
            self._log("统计查询失败：{}".format(e))

    # ============ JSON 导出/导入 + MySQL 迁移 ============
    def _export_json(self):
        """将数据库导出为 JSON 文件"""
        fpath = filedialog.asksaveasfilename(
            title="导出JSON",
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")],
            initialfile="syaA_export_{}.json".format(time.strftime("%Y%m%d_%H%M%S")),
        )
        if not fpath:
            return
        self._log("开始导出JSON：{}".format(fpath))
        self._run_in_thread(lambda: self._export_json_worker(fpath))

    def _export_json_worker(self, fpath):
        try:
            con = get_db_conn()
            cur = con.cursor()

            # 导出 av 表
            cur.execute("SELECT * FROM av")
            av_cols = [desc[0] for desc in cur.description]
            av_rows = cur.fetchall()
            av_list = [dict(zip(av_cols, row)) for row in av_rows]

            # 导出 black_table
            cur.execute("SELECT * FROM black_table")
            bt_cols = [desc[0] for desc in cur.description]
            bt_rows = cur.fetchall()
            bt_list = [dict(zip(bt_cols, row)) for row in bt_rows]

            # 导出 good_performer
            cur.execute("SELECT * FROM good_performer")
            gp_cols = [desc[0] for desc in cur.description]
            gp_rows = cur.fetchall()
            gp_list = [dict(zip(gp_cols, row)) for row in gp_rows]

            cur.close()
            con.close()

            data = {
                "export_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "version": 1,
                "av": av_list,
                "black_table": bt_list,
                "good_performer": gp_list,
            }

            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            self._log("[JSON] 导出完成：av {} 条, black_table {} 条, good_performer {} 条".format(
                len(av_list), len(bt_list), len(gp_list)))
            self._log("[JSON] 文件：{}".format(fpath))
        except Exception as e:
            self._log("[JSON] 导出失败：{}".format(e))

    def _import_json(self):
        """从 JSON 文件导入数据到 SQLite"""
        fpath = filedialog.askopenfilename(
            title="导入JSON",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")],
        )
        if not fpath:
            return
        self._log("开始导入JSON：{}".format(fpath))
        self._run_in_thread(lambda: self._import_json_worker(fpath))

    def _import_json_worker(self, fpath):
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)

            con = get_db_conn()
            cur = con.cursor()

            # av 表字段
            av_cols = ["numbers_name", "name", "magnet", "hot_num", "performer",
                       "size", "mosaic", "view", "reply", "designation",
                       "film_name", "grade", "exist_in_115", "local_path", "zzz"]
            av_inserted = 0
            av_skipped = 0
            for row in data.get("av", []):
                # 只导入字典中存在的字段
                vals = [row.get(col) for col in av_cols]
                try:
                    cur.execute(
                        "INSERT OR IGNORE INTO av ({}) VALUES ({})".format(
                            ", ".join(av_cols), ", ".join(["?"] * len(av_cols))
                        ), vals
                    )
                    if cur.rowcount > 0:
                        av_inserted += 1
                    else:
                        av_skipped += 1
                except Exception as e:
                    self._log("[JSON] av 跳过(错误)：{} | {}".format(row.get("numbers_name", "?"), e))
                    av_skipped += 1

            # black_table
            bt_inserted = 0
            bt_skipped = 0
            for row in data.get("black_table", []):
                name = row.get("name", "")
                if not name:
                    continue
                try:
                    cur.execute("INSERT OR IGNORE INTO black_table (name) VALUES (?)", (name,))
                    if cur.rowcount > 0:
                        bt_inserted += 1
                    else:
                        bt_skipped += 1
                except Exception:
                    bt_skipped += 1

            # good_performer
            gp_inserted = 0
            gp_skipped = 0
            for row in data.get("good_performer", []):
                name = row.get("name", "")
                if not name:
                    continue
                try:
                    cur.execute("INSERT OR IGNORE INTO good_performer (name) VALUES (?)", (name,))
                    if cur.rowcount > 0:
                        gp_inserted += 1
                    else:
                        gp_skipped += 1
                except Exception:
                    gp_skipped += 1

            con.commit()
            cur.close()
            con.close()

            self._log("[JSON] 导入完成：av 新增{}/跳过{}, black_table 新增{}/跳过{}, good_performer 新增{}/跳过{}".format(
                av_inserted, av_skipped, bt_inserted, bt_skipped, gp_inserted, gp_skipped))
        except Exception as e:
            self._log("[JSON] 导入失败：{}".format(e))

    def _migrate_from_mysql(self):
        """从 MySQL 数据库迁移数据到当前 SQLite"""
        # 先检查 SQLite 是否已有数据
        try:
            con = get_db_conn()
            cur = con.cursor()
            cur.execute("SELECT count(*) FROM av")
            cnt = cur.fetchone()[0]
            cur.close()
            con.close()
            if cnt > 0:
                if not messagebox.askyesno("确认",
                    "当前 SQLite 数据库已有 {} 条 av 记录。\n迁移前会先清空 SQLite 数据，是否继续？".format(cnt)):
                    return
        except Exception:
            pass
        self._log("开始从 MySQL 迁移数据到 SQLite...")
        self._run_in_thread(self._migrate_mysql_worker)

    def _migrate_mysql_worker(self):
        try:
            import pymysql
        except ImportError:
            self._log("[MySQL迁移] 未安装 pymysql，请先：pip install pymysql")
            return
        try:
            mysql_con = pymysql.connect(
                user="root",
                password="989796",
                host="localhost",
                port=3306,
                database="h_db",
            )
        except Exception as e:
            self._log("[MySQL迁移] 连接 MySQL 失败：{}".format(e))
            return

        try:
            mysql_cur = mysql_con.cursor()

            # ===== 清空 SQLite 数据，确保干净迁移 =====
            sqlite_con = get_db_conn()
            sqlite_cur = sqlite_con.cursor()
            sqlite_cur.execute("DELETE FROM av")
            sqlite_cur.execute("DELETE FROM black_table")
            sqlite_cur.execute("DELETE FROM good_performer")
            sqlite_con.commit()
            self._log("[MySQL迁移] 已清空 SQLite 旧数据")

            # ===== 获取 SQLite 表结构，用于列名映射 =====
            sqlite_cur.execute("PRAGMA table_info(av)")
            sqlite_av_cols = [row[1] for row in sqlite_cur.fetchall()]
            self._log("[MySQL迁移] SQLite av 表列名：{}".format(sqlite_av_cols))

            # ===== 迁移 av 表 =====
            mysql_cur.execute("SELECT * FROM av")
            mysql_av_cols = [desc[0] for desc in mysql_cur.description]
            mysql_av_rows = mysql_cur.fetchall()
            self._log("[MySQL迁移] av 表：读取 {} 条，MySQL列名：{}".format(len(mysql_av_rows), mysql_av_cols))

            # 只取两边都有的列
            common_av_cols = [c for c in mysql_av_cols if c in sqlite_av_cols]
            self._log("[MySQL迁移] av 表：公共列({})= {}".format(len(common_av_cols), common_av_cols))
            if len(common_av_cols) == 0:
                self._log("[MySQL迁移] av 表：无公共列，跳过！")
            else:
                mysql_col_indices = [mysql_av_cols.index(c) for c in common_av_cols]
                av_inserted = 0
                av_skipped = 0
                av_errors = 0
                first_error = ""
                for row in mysql_av_rows:
                    vals = [row[i] for i in mysql_col_indices]
                    try:
                        sqlite_cur.execute(
                            "INSERT OR IGNORE INTO av ({}) VALUES ({})".format(
                                ", ".join(common_av_cols), ", ".join(["?"] * len(common_av_cols))
                            ), vals
                        )
                        if sqlite_cur.rowcount > 0:
                            av_inserted += 1
                        else:
                            av_skipped += 1
                    except Exception as e:
                        av_errors += 1
                        if not first_error:
                            first_error = str(e)
                self._log("[MySQL迁移] av 表：新增 {} 条，跳过(重复) {} 条，错误 {} 条".format(
                    av_inserted, av_skipped, av_errors))
                if first_error:
                    self._log("[MySQL迁移] av 表首条错误：{}".format(first_error))

            # 迁移 black_table
            mysql_cur.execute("SELECT * FROM black_table")
            bt_cols = [desc[0] for desc in mysql_cur.description]
            bt_rows = mysql_cur.fetchall()
            bt_inserted = 0
            for row in bt_rows:
                name = row[0]
                if name:
                    try:
                        sqlite_cur.execute("INSERT OR IGNORE INTO black_table (name) VALUES (?)", (name,))
                        if sqlite_cur.rowcount > 0:
                            bt_inserted += 1
                    except Exception:
                        pass
            self._log("[MySQL迁移] black_table：读取 {} 条，新增 {} 条".format(len(bt_rows), bt_inserted))

            # 迁移 good_performer
            mysql_cur.execute("SELECT * FROM good_performer")
            gp_rows = mysql_cur.fetchall()
            gp_inserted = 0
            for row in gp_rows:
                name = row[0]
                if name:
                    try:
                        sqlite_cur.execute("INSERT OR IGNORE INTO good_performer (name) VALUES (?)", (name,))
                        if sqlite_cur.rowcount > 0:
                            gp_inserted += 1
                    except Exception:
                        pass
            self._log("[MySQL迁移] good_performer：读取 {} 条，新增 {} 条".format(len(gp_rows), gp_inserted))

            sqlite_con.commit()
            sqlite_cur.close()
            sqlite_con.close()
            mysql_cur.close()
            mysql_con.close()

            self._log("[MySQL迁移] 迁移完成！")
        except Exception as e:
            self._log("[MySQL迁移] 迁移失败：{}".format(e))

    # ============ Tab 5: 文件整理 ============
    def _build_file_tab(self):
        tab = ttk.Frame(self.nb)
        self.nb.add(tab, text="文件整理")

        row1 = ttk.Frame(tab)
        row1.pack(fill=tk.X, padx=10, pady=6)

        ttk.Label(row1, text="操作路径:").pack(side=tk.LEFT)
        self.file_path = ttk.Entry(row1, width=50)
        self.file_path.insert(0, self.config.get("file_path", "Z:/115open/云下载/"))
        self.file_path.pack(side=tk.LEFT, padx=4)
        ttk.Button(row1, text="浏览...", command=self._browse_file_path).pack(side=tk.LEFT, padx=2)

        row2 = ttk.Frame(tab)
        row2.pack(fill=tk.X, padx=10, pady=2)

        ttk.Button(row2, text="删除垃圾文件", command=lambda: self._run_file_task("garbage")).pack(side=tk.LEFT, padx=4)
        ttk.Button(row2, text="删除空文件夹", command=lambda: self._run_file_task("empty")).pack(side=tk.LEFT, padx=4)

        ttk.Label(row2, text="小文件阈值(MB):").pack(side=tk.LEFT, padx=(10, 2))
        self.small_file_mb = ttk.Entry(row2, width=6)
        self.small_file_mb.insert(0, self.config.get("small_file_mb", "50"))
        self.small_file_mb.pack(side=tk.LEFT, padx=2)
        ttk.Button(row2, text="删除小文件", command=lambda: self._run_file_task("small")).pack(side=tk.LEFT, padx=4)

        row3 = ttk.Frame(tab)
        row3.pack(fill=tk.X, padx=10, pady=2)

        ttk.Button(row3, text="重命名视频", command=lambda: self._run_file_task("rename")).pack(side=tk.LEFT, padx=4)

        ttk.Label(row3, text="目标路径:").pack(side=tk.LEFT, padx=(10, 2))
        self.file_dst_path = ttk.Entry(row3, width=40)
        self.file_dst_path.insert(0, self.config.get("file_dst_path", "Z:/115open/Hp/"))
        self.file_dst_path.pack(side=tk.LEFT, padx=2)
        ttk.Button(row3, text="搬运视频", command=lambda: self._run_file_task("move")).pack(side=tk.LEFT, padx=4)

        row4 = ttk.Frame(tab)
        row4.pack(fill=tk.X, padx=10, pady=6)

        ttk.Button(row4, text="删除黑名单演员视频", command=lambda: self._run_file_task("black")).pack(side=tk.LEFT, padx=4)
        ttk.Label(row4, text="低分阈值:").pack(side=tk.LEFT, padx=(10, 2))
        self.low_grade_val = ttk.Entry(row4, width=6)
        self.low_grade_val.insert(0, self.config.get("low_grade_val", "50"))
        self.low_grade_val.pack(side=tk.LEFT, padx=2)
        ttk.Button(row4, text="删除低分视频", command=lambda: self._run_file_task("lowgrade")).pack(side=tk.LEFT, padx=4)

        ttk.Label(row4, text="关键词:").pack(side=tk.LEFT, padx=(10, 2))
        self.keyword_val = ttk.Entry(row4, width=15)
        self.keyword_val.pack(side=tk.LEFT, padx=2)
        ttk.Button(row4, text="关键词删除", command=lambda: self._run_file_task("keyword")).pack(side=tk.LEFT, padx=4)

        row5 = ttk.Frame(tab)
        row5.pack(fill=tk.X, padx=10, pady=2)
        ttk.Button(row5, text="一键整理流水线(云下载=>Hp)", command=lambda: self._run_file_task("pipeline")).pack(side=tk.LEFT, padx=4)

        row6 = ttk.Frame(tab)
        row6.pack(fill=tk.X, padx=10, pady=2)

        ttk.Label(row6, text="高分阈值:").pack(side=tk.LEFT)
        self.collect_grade = ttk.Entry(row6, width=6)
        self.collect_grade.insert(0, self.config.get("collect_grade", "90"))
        self.collect_grade.pack(side=tk.LEFT, padx=2)
        ttk.Label(row6, text="收集到:").pack(side=tk.LEFT, padx=(8, 2))
        self.collect_dst_path = ttk.Entry(row6, width=40)
        self.collect_dst_path.insert(0, self.config.get("collect_dst_path", ""))
        self.collect_dst_path.pack(side=tk.LEFT, padx=2)
        ttk.Button(row6, text="浏览...", command=self._browse_collect_path).pack(side=tk.LEFT, padx=2)
        ttk.Button(row6, text="高分收集", command=lambda: self._run_file_task("collect_preview")).pack(side=tk.LEFT, padx=4)

    def _browse_collect_path(self):
        path = filedialog.askdirectory()
        if path:
            self.collect_dst_path.delete(0, tk.END)
            self.collect_dst_path.insert(0, path.replace("/", "\\") + "\\")

    def _browse_file_path(self):
        path = filedialog.askdirectory()
        if path:
            self.file_path.delete(0, tk.END)
            self.file_path.insert(0, path.replace("/", "\\") + "\\")

    def _run_file_task(self, task_type):
        src_path = self.file_path.get().strip()
        dst_path = self.file_dst_path.get().strip()

        if task_type == "pipeline":
            self._log("开始一键整理流水线...")
            self._run_in_thread(lambda: self._pipeline_worker(src_path, dst_path))
            return

        if task_type == "collect_preview":
            try:
                grade = int(self.collect_grade.get())
            except ValueError:
                messagebox.showerror("错误", "分数阈值必须是整数")
                return
            dst = self.collect_dst_path.get().strip()
            if not dst:
                messagebox.showerror("错误", "请输入收集目标路径")
                return
            self._log("正在预览高分收集（≥{}分）=> {}...".format(grade, dst))
            self._run_in_thread(lambda: self._collect_preview_worker(grade, dst))
            return

        if not src_path and task_type != "black" and task_type != "keyword":
            messagebox.showerror("错误", "请输入路径")
            return

        if task_type == "garbage":
            self._log("开始删除垃圾文件：{}".format(src_path))
            self._run_in_thread(lambda: self._delete_garbage_worker(src_path))
        elif task_type == "empty":
            self._log("开始删除空文件夹：{}".format(src_path))
            self._run_in_thread(lambda: self._delete_empty_worker(src_path))
        elif task_type == "small":
            try:
                mb = int(self.small_file_mb.get())
            except ValueError:
                messagebox.showerror("错误", "阈值必须是整数")
                return
            self._log("开始删除小文件（<{}MB）：{}".format(mb, src_path))
            self._run_in_thread(lambda: self._delete_small_worker(src_path, mb))
        elif task_type == "rename":
            self._log("开始重命名：{}".format(src_path))
            self._run_in_thread(lambda: self._rename_worker(src_path))
        elif task_type == "move":
            if not dst_path:
                messagebox.showerror("错误", "请输入目标路径")
                return
            self._log("开始搬运：{} => {}".format(src_path, dst_path))
            self._run_in_thread(lambda: self._move_worker(src_path, dst_path))
        elif task_type == "black":
            self._log("开始删除黑名单演员视频...")
            self._run_in_thread(self._delete_black_worker)
        elif task_type == "lowgrade":
            try:
                grade = int(self.low_grade_val.get())
            except ValueError:
                messagebox.showerror("错误", "分数必须是整数")
                return
            self._log("开始删除低分视频（<={}分）...".format(grade))
            self._run_in_thread(lambda: self._delete_lowgrade_worker(grade))
        elif task_type == "keyword":
            kw = self.keyword_val.get().strip()
            if not kw:
                messagebox.showerror("错误", "请输入关键词")
                return
            self._log("开始关键词删除：{}".format(kw))
            self._run_in_thread(lambda: self._delete_keyword_worker(kw))

    def _delete_garbage_worker(self, path):
        try:
            self._delete_garbage_recursive(path)
            self._log("垃圾文件清理完成")
        except Exception as e:
            self._log("垃圾文件清理失败：{}".format(e))

    def _delete_garbage_recursive(self, path):
        try:
            file_list = os.listdir(path)
        except PermissionError:
            return
        for file in file_list:
            self._log("[文件] 处理：{}".format(path + file))
            if file in WHITE_LIST:
                continue
            if os.path.isdir(path + file):
                try:
                    if len(os.listdir(path + file)) == 0:
                        os.rmdir(path + file)
                        self._log("[删除] 空文件夹：{}".format(path + file))
                        continue
                except PermissionError:
                    pass
                self._delete_garbage_recursive(path + file + "/")
                continue
            try:
                size = os.path.getsize(path + file)
                if size < 50000000:
                    os.remove(path + file)
                    self._log("[删除] 小于50M：{}".format(path + file))
                    continue
            except FileNotFoundError:
                continue
            if file in DEL_FILE_NAME_LIST:
                try:
                    os.remove(path + file)
                    self._log("[删除] 垃圾文件：{}".format(path + file))
                except FileNotFoundError:
                    pass

    def _delete_empty_worker(self, path):
        try:
            self._delete_empty_recursive(path)
            self._log("空文件夹清理完成")
        except Exception as e:
            self._log("空文件夹清理失败：{}".format(e))

    def _delete_empty_recursive(self, path):
        try:
            file_list = os.listdir(path)
        except PermissionError:
            return
        for file in file_list:
            if file in WHITE_LIST:
                continue
            if os.path.isdir(path + file):
                try:
                    if len(os.listdir(path + file)) == 0:
                        os.rmdir(path + file)
                        self._log("[删除] 空文件夹：{}".format(path + file))
                        continue
                except PermissionError:
                    pass
                self._delete_empty_recursive(path + file + "/")

    def _delete_small_worker(self, path, mb):
        try:
            self._delete_small_recursive(path, mb)
            self._log("小文件清理完成")
        except Exception as e:
            self._log("小文件清理失败：{}".format(e))

    def _delete_small_recursive(self, path, mb):
        try:
            file_list = os.listdir(path)
        except PermissionError:
            return
        for file in file_list:
            if file in WHITE_LIST:
                continue
            if os.path.isdir(path + file):
                try:
                    if len(os.listdir(path + file)) == 0:
                        continue
                except PermissionError:
                    pass
                self._delete_small_recursive(path + file + "/", mb)
                continue
            try:
                size = os.path.getsize(path + file)
                if size < mb * 1000000:
                    os.remove(path + file)
                    self._log("[删除] 小于{}MB：{}".format(mb, path + file))
            except FileNotFoundError:
                pass

    def _rename_worker(self, path):
        try:
            con = get_db_conn(timeout=30)
            self._rename_recursive(path, con)
            con.close()
            self._log("重命名完成")
        except Exception as e:
            self._log("重命名失败：{}".format(e))

    def _rename_recursive(self, path, con):
        try:
            file_list = os.listdir(path)
        except PermissionError:
            return
        for file in file_list:
            if os.path.isdir(path + file):
                self._rename_recursive(path + file + "/", con)
                continue
            ret = re.findall(r"[0-9a-zA-Z]+-[0-9a-zA-Z]+", file)
            if not ret:
                continue
            for temp_ret in ret:
                try:
                    cur = con.cursor()
                    cur.execute("SELECT {} FROM av WHERE designation = ?".format(AV_COLUMNS), (temp_ret,))
                    rec = cur.fetchone()
                    if rec is not None:
                        new_name = "{}-{}-{}-{}.mp4".format(rec[IDX_DESIGNATION], rec[IDX_PERFORMER], rec[IDX_MOSAIC], rec[IDX_FILM_NAME])
                        old = path + file
                        new = path + new_name
                        self._log("[重命名] {} => {}".format(file, new_name))
                        try:
                            os.rename(old, new)
                        except Exception:
                            pass
                    cur.close()
                except Exception as e:
                    self._log("重命名数据库查询失败：{}".format(e))

    def _move_worker(self, src, dst):
        try:
            self._move_recursive(src, dst)
            self._log("搬运完成")
        except Exception as e:
            self._log("搬运失败：{}".format(e))

    def _move_recursive(self, src, dst):
        try:
            file_list = os.listdir(src)
        except PermissionError:
            return
        for file in file_list:
            self._log("[搬运] 处理：{}".format(src + file))
            if os.path.isdir(src + "/" + file):
                self._move_recursive(src + file + "/", dst)
                continue
            if "mp4" not in file:
                continue
            source_path = src + file
            destination_path = dst + file
            try:
                shutil.move(source_path, destination_path)
                self._log("[搬运] {} => {}".format(source_path, destination_path))
            except Exception as e:
                self._log("[搬运] 失败：{}".format(e))

    def _delete_black_worker(self):
        try:
            con = get_db_conn(timeout=30)
            cur = con.cursor()
            cur.execute("SELECT * FROM black_table")
            rec = cur.fetchone()
            deleted = 0
            skipped = 0
            multi_performer = 0
            high_grade_skipped = 0
            whitelist_skipped = 0
            # 收集跳过信息，最后统一汇报
            skip_reasons = []  # [(演员名, 原因, 详情), ...]
            while rec is not None:
                name = rec[0]
                # 清理黑名单名中的 HTML 残留（&nbsp; / </td> 等）
                clean_name = re.sub(r'&nbsp;|<[^>]+>', '', name).strip()
                self._log("[黑名单] 检查演员：{}".format(clean_name))
                # 先检查该演员是否在白名单中
                cur_w = con.cursor()
                cur_w.execute("SELECT * FROM good_performer WHERE name = ?", (clean_name,))
                in_whitelist = cur_w.fetchone() is not None
                cur_w.close()
                if in_whitelist:
                    # 黑名单名字有 HTML 残留与白名单不一致时，自动清理黑名单脏数据
                    if name != clean_name:
                        cur_del = con.cursor()
                        cur_del.execute("DELETE FROM black_table WHERE name = ?", (name,))
                        cur_del.close()
                        skip_reasons.append((clean_name, "白名单冲突(已自动清理)",
                            "黑名单[{}]与白名单[{}]实际为同一人，已从黑名单移除脏数据".format(name, clean_name)))
                    else:
                        skip_reasons.append((clean_name, "白名单冲突",
                            "同时在白名单中，请确认黑白名单"))
                    whitelist_skipped += 1
                    rec = cur.fetchone()
                    continue
                # 再查该演员是否有 90 分及以上的独演视频
                cur3 = con.cursor()
                cur3.execute(
                    "SELECT numbers_name, grade, film_name FROM av WHERE performer = ? AND grade IS NOT NULL AND grade >= 90",
                    (clean_name,))
                high_grade_recs = cur3.fetchall()
                cur3.close()
                if high_grade_recs:
                    detail = "、".join("{}({}分)".format(hgr[2] or hgr[0], hgr[1]) for hgr in high_grade_recs)
                    skip_reasons.append((clean_name, "高分保护", "共{}部评分>=90：{}".format(len(high_grade_recs), detail)))
                    high_grade_skipped += 1
                    rec = cur.fetchone()
                    continue
                # 无保护触发，正常执行删除
                cur2 = con.cursor()
                # 用 LIKE 粗筛
                cur2.execute("SELECT {} FROM av WHERE performer LIKE ?".format(AV_COLUMNS), ("%" + clean_name + "%",))
                rec2 = cur2.fetchone()
                found = 0
                while rec2 is not None:
                    key = rec2[IDX_NUMBERS_NAME]
                    path = rec2[IDX_LOCAL_PATH]
                    film_name = rec2[IDX_NAME]
                    performer_raw = rec2[IDX_PERFORMER] if rec2[IDX_PERFORMER] else ""
                    # 清理 performer 字段中的 HTML 残留
                    performer_clean = re.sub(r'&nbsp;|<[^>]+>', '', performer_raw).strip()
                    # 只删除独演影片：performer 清理后必须完全等于黑名单演员名
                    # 多演员影片跳过，需要手动用"关键词删除"处理
                    if performer_clean != clean_name:
                        rec2 = cur2.fetchone()
                        multi_performer += 1
                        continue
                    if path is not None:
                        cur_upd = con.cursor()
                        s, v = _append_auto_fields("UPDATE av SET local_path = NULL WHERE numbers_name = ?", (key,), action="黑名单删除")
                        cur_upd.execute(s, v)
                        s, v = _append_auto_fields("UPDATE av SET exist_in_115 = NULL WHERE numbers_name = ?", (key,), action="黑名单删除")
                        cur_upd.execute(s, v)
                        cur_upd.close()
                        if os.path.exists(path):
                            os.remove(path)
                        self._log("[删除] 黑名单演员 {}：{}".format(clean_name, film_name))
                        deleted += 1
                        found += 1
                    rec2 = cur2.fetchone()
                cur2.close()
                if found == 0:
                    skipped += 1
                rec = cur.fetchone()
            con.commit()
            cur.close()
            con.close()
            # 统一汇报
            self._log("黑名单视频删除完成，共删除 {} 条独演，{} 个演员无匹配视频，{} 条多演员影片跳过".format(
                deleted, skipped, multi_performer))
            if skip_reasons:
                self._log("===== 以下演员被跳过，请手动判断 =====")
                for name, reason, detail in skip_reasons:
                    self._log("[跳过] {} - {} - {}".format(name, reason, detail))
                self._log("===== 共 {} 个演员被跳过（白名单冲突 {} 个，高分保护 {} 个）=====".format(
                    len(skip_reasons), whitelist_skipped, high_grade_skipped))
        except Exception as e:
            self._log("黑名单删除失败：{}".format(e))

    def _delete_lowgrade_worker(self, grade):
        try:
            con = get_db_conn(timeout=30)
            cur = con.cursor()
            cur.execute("SELECT {} FROM av WHERE grade <= ? AND local_path IS NOT NULL".format(AV_COLUMNS), (grade,))
            rec = cur.fetchone()
            deleted = 0
            while rec is not None:
                key = rec[IDX_NUMBERS_NAME]
                path = rec[IDX_LOCAL_PATH]
                film_name = rec[IDX_NAME]
                cur_upd = con.cursor()
                s, v = _append_auto_fields("UPDATE av SET local_path = NULL WHERE numbers_name = ?", (key,), action="低分删除")
                cur_upd.execute(s, v)
                s, v = _append_auto_fields("UPDATE av SET exist_in_115 = NULL WHERE numbers_name = ?", (key,), action="低分删除")
                cur_upd.execute(s, v)
                cur_upd.close()
                if path and os.path.exists(path):
                    os.remove(path)
                self._log("[删除] 低分({})：{}".format(rec[IDX_GRADE], film_name))
                deleted += 1
                rec = cur.fetchone()
            con.commit()
            cur.close()
            con.close()
            self._log("低分视频删除完成，共 {} 条".format(deleted))
        except Exception as e:
            self._log("低分删除失败：{}".format(e))

    def _delete_keyword_worker(self, keyword):
        try:
            con = get_db_conn(timeout=30)
            cur = con.cursor()
            kw = "%" + keyword + "%"
            cur.execute("SELECT {} FROM av WHERE name LIKE ?".format(AV_COLUMNS), (kw,))
            rec = cur.fetchone()
            deleted = 0
            while rec is not None:
                path = rec[IDX_LOCAL_PATH]
                numbers_name = rec[IDX_NUMBERS_NAME]
                if path is not None:
                    cur_upd = con.cursor()
                    s, v = _append_auto_fields("UPDATE av SET local_path = NULL WHERE numbers_name = ?", (numbers_name,), action="关键词删除")
                    cur_upd.execute(s, v)
                    s, v = _append_auto_fields("UPDATE av SET exist_in_115 = NULL WHERE numbers_name = ?", (numbers_name,), action="关键词删除")
                    cur_upd.execute(s, v)
                    cur_upd.close()
                    if os.path.exists(path):
                        os.remove(path)
                    self._log("[删除] 关键词匹配：{}".format(path))
                    deleted += 1
                rec = cur.fetchone()
            con.commit()
            cur.close()
            con.close()
            self._log("关键词删除完成，共 {} 条".format(deleted))
        except Exception as e:
            self._log("关键词删除失败：{}".format(e))

    def _pipeline_worker(self, src, dst):
        """一键整理流水线：删垃圾=>重命名=>搬运=>清空=>入库=>删黑名单"""
        try:
            self._log("=== 步骤1：删除垃圾文件 ===")
            self._delete_garbage_recursive(src)
            self._log("=== 步骤2：重命名文件 ===")
            con_rename = get_db_conn(timeout=30)
            self._rename_recursive(src, con_rename)
            con_rename.close()
            self._log("=== 步骤3：搬运视频 ===")
            self._move_recursive(src, dst)
            self._log("=== 步骤4：清理空文件夹 ===")
            self._delete_empty_recursive(src)
            self._log("=== 步骤5：录入115 ===")
            self._check_115_count = 0
            con = get_db_conn(timeout=30)
            self._check_115_recursive(dst, con)
            con.commit()
            con.close()
            self._log("=== 步骤6：删除黑名单视频 ===")
            self._delete_black_worker()
            self._log("=== 流水线全部完成 ===")
        except Exception as e:
            self._log("流水线失败：{}".format(e))

    def _collect_preview_worker(self, grade, dst_path):
        """预览高分收集：扫描所有将执行的动作，然后弹窗让用户确认"""
        try:
            con = get_db_conn(timeout=30)
            cur = con.cursor()
            cur.execute(
                "SELECT {} FROM av WHERE grade >= ? AND local_path IS NOT NULL AND local_path != '' ORDER BY grade DESC, numbers_name".format(AV_COLUMNS),
                (grade,)
            )
            rows = cur.fetchall()
            cur.close()
            con.close()

            total = len(rows)
            if total == 0:
                self._log("未找到评分 >= {} 的视频".format(grade))
                return

            # 扫描旧文件
            old_files = self._scan_highgrade_dir(dst_path)

            # ---- 收集所有预览动作 ----
            actions = []  # list of dict: {type, detail, numbers_name, src, dst, grade}
            dst_drive = os.path.splitdrive(dst_path)[0].upper()

            # 阶段1：检查旧文件变更
            # 关键：只处理子目录与当前评分不匹配的文件，而不是把所有 < 当前阈值的文件都移走
            # 例如：用80分收集的80分文件在80分/目录下是正确的，用90分收集时不应移动
            # 同番号多条记录时（如一条80分一条90分），如果文件在高分子目录且高分记录指向此路径，不应移走
            if old_files:
                con2 = get_db_conn(timeout=30)
                cur2 = con2.cursor()
                for filepath, old_subdir in old_files.items():
                    filename = os.path.basename(filepath)
                    cur2.execute(
                        "SELECT numbers_name, grade, local_path FROM av WHERE local_path = ?",
                        (filepath,)
                    )
                    rec2 = cur2.fetchone()
                    if rec2 is None:
                        fanhao_part = filename.split("-")[0] if "-" in filename else os.path.splitext(filename)[0]
                        cur2.execute(
                            "SELECT numbers_name, grade, local_path FROM av WHERE (numbers_name = ? OR designation = ?)",
                            (fanhao_part, fanhao_part)
                        )
                        rec2 = cur2.fetchone()
                        if rec2 is None:
                            actions.append({"type": "跳过", "detail": "DB未匹配，不处理", "numbers_name": filename[:40], "src": filepath, "dst": "", "grade": "?"})
                            continue
                    new_grade = rec2[1]
                    db_local_path = rec2[2]

                    # 提取文件当前所在子目录的分数
                    old_subdir_grade = None
                    try:
                        old_subdir_grade = int(old_subdir.replace("分", ""))
                    except (ValueError, AttributeError):
                        pass

                    # 情况0：子目录分数与DB当前评分一致 → 文件在正确位置，不动
                    if old_subdir_grade is not None and new_grade is not None and old_subdir_grade == new_grade:
                        continue

                    # 情况0.5：同番号多条记录时，文件虽与当前记录评分不匹配，
                    # 但如果有另一条评分==子目录分数的记录也指向此文件，则文件位置正确，不动
                    # 例：SONE-153有80分和90分两条记录，文件在90分/下，匹配到80分记录时不该移走
                    if old_subdir_grade is not None:
                        cur2.execute(
                            "SELECT COUNT(*) FROM av WHERE local_path = ? AND grade = ?",
                            (filepath, old_subdir_grade)
                        )
                        higher_match = cur2.fetchone()[0]
                        if higher_match > 0:
                            # 有评分==子目录分数的记录指向此文件，位置正确，不动
                            continue

                    # 情况2：DB评分变更，但仍在阈值内 → 移到正确子目录
                    if new_grade is not None and new_grade >= grade:
                        correct_subdir = "{}分".format(new_grade)
                        if old_subdir != correct_subdir:
                            correct_dir = os.path.join(dst_path, correct_subdir)
                            new_path = os.path.join(correct_dir, filename)
                            actions.append({
                                "type": "评分变更",
                                "detail": "{} => {}".format(old_subdir, correct_subdir),
                                "numbers_name": rec2[0],
                                "src": filepath,
                                "dst": new_path,
                                "grade": new_grade
                            })
                        continue

                    # 情况3：DB评分为None或降到了子目录分数以下 → 真正的降级，移回原目录
                    # 只有评分比子目录分数还低才是"降级"（说明之前是高分现在降了）
                    if new_grade is None or (old_subdir_grade is not None and new_grade < old_subdir_grade):
                        if db_local_path and not db_local_path.startswith(dst_path):
                            orig_dir = os.path.dirname(db_local_path)
                        else:
                            orig_dir = os.path.dirname(filepath).rsplit(os.sep, 1)[0] + os.sep + "Hp"
                        new_path = os.path.join(orig_dir, filename)
                        actions.append({
                            "type": "降级移回",
                            "detail": "评分{}从{}移回原始目录".format(new_grade if new_grade is not None else "无", old_subdir),
                            "numbers_name": rec2[0],
                            "src": filepath,
                            "dst": new_path,
                            "grade": new_grade
                        })
                    # 其他情况（如80分文件在90分目录但评分仍是80 → 评分变更移到80分目录）
                    elif new_grade is not None:
                        correct_subdir = "{}分".format(new_grade)
                        if old_subdir != correct_subdir:
                            correct_dir = os.path.join(dst_path, correct_subdir)
                            if not os.path.exists(correct_dir):
                                os.makedirs(correct_dir, exist_ok=True)
                            new_path = os.path.join(correct_dir, filename)
                            actions.append({
                                "type": "评分变更",
                                "detail": "{} => {}".format(old_subdir, correct_subdir),
                                "numbers_name": rec2[0],
                                "src": filepath,
                                "dst": new_path,
                                "grade": new_grade
                            })
                cur2.close()
                con2.close()

            # 阶段2：新文件操作
            for rec in rows:
                numbers_name = rec[IDX_NUMBERS_NAME]
                rec_grade = rec[IDX_GRADE]
                local_path = rec[IDX_LOCAL_PATH]

                if not local_path or not os.path.exists(local_path):
                    actions.append({
                        "type": "跳过",
                        "detail": "文件不存在",
                        "numbers_name": numbers_name,
                        "src": local_path or "(空)",
                        "dst": "",
                        "grade": rec_grade
                    })
                    continue

                filename = os.path.basename(local_path)
                grade_dir = os.path.join(dst_path, "{}分".format(rec_grade))
                dst_file = os.path.join(grade_dir, filename)

                # 已存在且大小相同 → 跳过
                if os.path.exists(dst_file):
                    try:
                        src_size = os.path.getsize(local_path)
                        dst_size = os.path.getsize(dst_file)
                        if src_size == dst_size:
                            actions.append({
                                "type": "跳过",
                                "detail": "已存在且大小相同",
                                "numbers_name": numbers_name,
                                "src": local_path,
                                "dst": dst_file,
                                "grade": rec_grade
                            })
                            continue
                    except Exception:
                        pass

                # 判断操作类型
                src_drive = os.path.splitdrive(local_path)[0].upper()
                if src_drive == dst_drive:
                    op_type = "同盘移动"
                    op_detail = "move（源文件移走，DB路径更新）"
                else:
                    op_type = "跨盘复制"
                    op_detail = "copy2（源文件保留）"

                actions.append({
                    "type": op_type,
                    "detail": op_detail,
                    "numbers_name": numbers_name,
                    "src": local_path,
                    "dst": dst_file,
                    "grade": rec_grade
                })

            # ---- 弹出预览窗口 ----
            self.root.after(0, lambda: self._show_collect_preview(grade, dst_path, actions, rows))

        except Exception as e:
            self._log("高分收集预览失败：{}".format(e))

    def _show_collect_preview(self, grade, dst_path, actions, db_rows):
        """显示高分收集预览窗口，列出所有将执行的动作"""
        win = tk.Toplevel(self.root)
        win.title("高分收集预览 (≥{}分)".format(grade))
        win.geometry("900x600")
        win.transient(self.root)
        win.grab_set()

        # ---- 顶部摘要 ----
        summary_frame = ttk.Frame(win)
        summary_frame.pack(fill=tk.X, padx=10, pady=8)

        # 按类型统计
        type_counts = {}
        for a in actions:
            t = a["type"]
            type_counts[t] = type_counts.get(t, 0) + 1

        summary_text = "阈值：≥{}分 | 目标：{} | 共 {} 条操作".format(grade, dst_path, len(actions))
        for t in ["同盘移动", "跨盘复制", "评分变更", "降级移回", "跳过"]:
            if t in type_counts:
                label = t
                if t == "同盘移动":
                    label = "同盘移动(源文件移走)"
                elif t == "跨盘复制":
                    label = "跨盘复制(源文件保留)"
                summary_text += " | {}：{}".format(label, type_counts[t])

        ttk.Label(summary_frame, text=summary_text, wraplength=860, font=("Microsoft YaHei", 10)).pack(anchor=tk.W)

        # 特别警告
        move_count = type_counts.get("同盘移动", 0)
        downgrade_count = type_counts.get("降级移回", 0)
        if move_count > 0 or downgrade_count > 0:
            warn_text = ""
            if move_count > 0:
                warn_text += "⚠ 同盘移动：源目录文件将移走，DB路径将更新到新位置；"
            if downgrade_count > 0:
                warn_text += "⚠ 降级移回：评分低于阈值的文件将移回原始目录；"
            ttk.Label(summary_frame, text=warn_text, foreground="red", wraplength=860, font=("Microsoft YaHei", 9)).pack(anchor=tk.W, pady=(4, 0))

        # ---- 动作列表（Treeview） ----
        tree_frame = ttk.Frame(win)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)

        columns = ("type", "numbers_name", "grade", "detail", "src_short", "dst_short")
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="extended")
        tree.heading("type", text="操作")
        tree.heading("numbers_name", text="番号")
        tree.heading("grade", text="评分")
        tree.heading("detail", text="说明")
        tree.heading("src_short", text="来源")
        tree.heading("dst_short", text="目标")

        tree.column("type", width=80, minwidth=60)
        tree.column("numbers_name", width=120, minwidth=80)
        tree.column("grade", width=50, minwidth=40)
        tree.column("detail", width=180, minwidth=100)
        tree.column("src_short", width=200, minwidth=80)
        tree.column("dst_short", width=200, minwidth=80)

        # 颜色标签
        tree.tag_configure("move", foreground="#CC6600")
        tree.tag_configure("copy", foreground="#0066CC")
        tree.tag_configure("change", foreground="#009900")
        tree.tag_configure("downgrade", foreground="#CC0000")
        tree.tag_configure("skip", foreground="#888888")

        type_tag_map = {
            "同盘移动": "move",
            "跨盘复制": "copy",
            "评分变更": "change",
            "降级移回": "downgrade",
            "跳过": "skip",
        }

        for a in actions:
            tag = type_tag_map.get(a["type"], "")
            src_short = a["src"]
            dst_short = a["dst"]
            # 截断过长的路径，只显示关键部分
            if len(src_short) > 60:
                src_short = "..." + src_short[-57:]
            if len(dst_short) > 60:
                dst_short = "..." + dst_short[-57:]
            tree.insert("", tk.END, values=(
                a["type"], a["numbers_name"], a["grade"], a["detail"], src_short, dst_short
            ), tags=(tag,))

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # ---- 底部按钮 ----
        btn_frame = ttk.Frame(win)
        btn_frame.pack(fill=tk.X, padx=10, pady=8)

        result = {"confirmed": False}

        def on_confirm():
            result["confirmed"] = True
            win.destroy()

        def on_cancel():
            win.destroy()

        ttk.Button(btn_frame, text="确认执行", command=on_confirm).pack(side=tk.RIGHT, padx=4)
        ttk.Button(btn_frame, text="取消", command=on_cancel).pack(side=tk.RIGHT, padx=4)

        # 等待窗口关闭
        win.wait_window()

        if result["confirmed"]:
            self._log("用户确认，开始高分收集（≥{}分）=> {}（同盘将移动文件并更新数据库路径）...".format(grade, dst_path))
            self._run_in_thread(lambda: self._collect_highgrade_worker(grade, dst_path))
        else:
            self._log("高分收集已取消")

    def _collect_highgrade_worker(self, grade, dst_path):
        """高分收集：将评分 >= grade 的视频复制到目标目录（按分数分子目录），并生成 HTML 目录清单

        增量更新逻辑：
        - 已存在且大小相同的文件跳过，不重复复制
        - 评分变更的文件自动移动到正确子目录
        - 评分降至阈值以下的文件自动删除
        - 同盘使用 move+move 回（服务端操作，秒完成），跨盘回退 shutil.copy2
        """
        try:
            # 确保目标目录存在
            if not os.path.exists(dst_path):
                os.makedirs(dst_path, exist_ok=True)

            con = get_db_conn(timeout=30)
            cur = con.cursor()
            cur.execute(
                "SELECT {} FROM av WHERE grade >= ? AND local_path IS NOT NULL AND local_path != '' ORDER BY grade DESC, numbers_name".format(AV_COLUMNS),
                (grade,)
            )
            rows = cur.fetchall()
            cur.close()
            con.close()

            total = len(rows)
            if total == 0:
                self._log("未找到评分 >= {} 的视频".format(grade))
                return

            self._log("找到 {} 条评分 >= {} 的视频，开始处理...".format(total, grade))

            # ---- 阶段1：同步旧文件（处理评分变更/降级） ----
            # 安全策略：只处理子目录与DB评分不匹配的文件
            # 关键：80分文件在80分/目录下是正确的，即使当前阈值是90也不应移动
            # 只有真正评分变更（如90→80）或从高分降级才需要处理
            moved = 0
            removed = 0
            old_files = self._scan_highgrade_dir(dst_path)
            if old_files:
                self._log("[收集] 阶段1：同步旧文件（共{}个，检查评分变更/降级）...".format(len(old_files)))
                con2 = get_db_conn(timeout=30)
                cur2 = con2.cursor()
                for filepath, old_subdir in old_files.items():
                    filename = os.path.basename(filepath)
                    # 用 DB 的 local_path 字段反查，而非从文件名猜测番号（更可靠）
                    cur2.execute(
                        "SELECT numbers_name, grade, local_path FROM av WHERE local_path = ?",
                        (filepath,)
                    )
                    rec2 = cur2.fetchone()
                    if rec2 is None:
                        # DB 中没有指向此路径的记录，可能是重命名后路径变了
                        # 尝试用文件名匹配（fallback，但不删除）
                        fanhao_part = filename.split("-")[0] if "-" in filename else os.path.splitext(filename)[0]
                        cur2.execute(
                            "SELECT numbers_name, grade, local_path FROM av WHERE (numbers_name = ? OR designation = ?)",
                            (fanhao_part, fanhao_part)
                        )
                        rec2 = cur2.fetchone()
                        if rec2 is None:
                            self._log("[收集] 跳过(DB未匹配)：{}".format(filename[:60]))
                            continue
                    new_grade = rec2[1]
                    db_local_path = rec2[2]

                    # 提取文件当前所在子目录的分数
                    old_subdir_grade = None
                    try:
                        old_subdir_grade = int(old_subdir.replace("分", ""))
                    except (ValueError, AttributeError):
                        pass

                    # 子目录分数与DB评分一致 → 文件在正确位置，不动
                    if old_subdir_grade is not None and new_grade is not None and old_subdir_grade == new_grade:
                        continue

                    # 同番号多条记录时，文件虽与当前记录评分不匹配，
                    # 但如果有另一条评分==子目录分数的记录也指向此文件，则位置正确，不动
                    # 例：SONE-153有80分和90分两条，文件在90分/下，匹配到80分那条时不该移走
                    if old_subdir_grade is not None:
                        cur2.execute(
                            "SELECT COUNT(*) FROM av WHERE local_path = ? AND grade = ?",
                            (filepath, old_subdir_grade)
                        )
                        higher_match = cur2.fetchone()[0]
                        if higher_match > 0:
                            continue

                    # DB评分变更，仍在阈值内 → 移到正确子目录
                    if new_grade is not None and new_grade >= grade:
                        correct_subdir = "{}分".format(new_grade)
                        if old_subdir != correct_subdir:
                            correct_dir = os.path.join(dst_path, correct_subdir)
                            if not os.path.exists(correct_dir):
                                os.makedirs(correct_dir, exist_ok=True)
                            new_path = os.path.join(correct_dir, filename)
                            try:
                                shutil.move(filepath, new_path)
                                try:
                                    link_db_cmd("UPDATE av SET local_path = ? WHERE numbers_name = ?", (new_path, rec2[0]), action="高分收集-评分变更")
                                except Exception:
                                    pass
                                moved += 1
                                self._log("[收集] 评分变更：{} {} => {} ({}分→{}分)".format(filename[:60], old_subdir, correct_subdir, old_subdir.replace("分", ""), new_grade))
                            except Exception as e:
                                self._log("[收集] 移动失败：{} - {}".format(filename[:60], e))
                        continue

                    # DB评分为None或比子目录分数还低 → 真正的降级，移回原始目录
                    if new_grade is None or (old_subdir_grade is not None and new_grade < old_subdir_grade):
                        try:
                            if db_local_path and not db_local_path.startswith(dst_path):
                                orig_dir = os.path.dirname(db_local_path)
                            else:
                                orig_dir = os.path.dirname(filepath).replace(os.sep + old_subdir, "")
                                if orig_dir == os.path.dirname(filepath):
                                    orig_dir = os.path.dirname(filepath).rsplit(os.sep, 1)[0] + os.sep + "Hp"
                            if not os.path.exists(orig_dir):
                                os.makedirs(orig_dir, exist_ok=True)
                            new_path = os.path.join(orig_dir, filename)
                            if os.path.exists(new_path):
                                self._log("[收集] 降级跳过(目标已存在)：{}".format(filename[:60]))
                                continue
                            shutil.move(filepath, new_path)
                            removed += 1
                            try:
                                link_db_cmd("UPDATE av SET local_path = ? WHERE numbers_name = ?", (new_path, rec2[0]), action="高分收集-降级移回")
                            except Exception:
                                pass
                            self._log("[收集] 降级移回：{} (当前{}分，从{}移回{})".format(filename[:60], new_grade, old_subdir, orig_dir))
                        except Exception as e:
                            self._log("[收集] 降级处理失败：{} - {}".format(filename[:60], e))
                    elif new_grade is not None:
                        # 其他情况：如90分文件在80分目录（不在阈值内但子目录不对）→ 移到正确子目录
                        correct_subdir = "{}分".format(new_grade)
                        if old_subdir != correct_subdir:
                            correct_dir = os.path.join(dst_path, correct_subdir)
                            if not os.path.exists(correct_dir):
                                os.makedirs(correct_dir, exist_ok=True)
                            new_path = os.path.join(correct_dir, filename)
                            try:
                                shutil.move(filepath, new_path)
                                try:
                                    link_db_cmd("UPDATE av SET local_path = ? WHERE numbers_name = ?", (new_path, rec2[0]), action="高分收集-评分变更")
                                except Exception:
                                    pass
                                moved += 1
                                self._log("[收集] 评分变更：{} {} => {}".format(filename[:60], old_subdir, correct_subdir))
                            except Exception as e:
                                self._log("[收集] 移动失败：{} - {}".format(filename[:60], e))
                cur2.close()
                con2.close()
                self._clean_empty_subdirs(dst_path)

            if moved > 0 or removed > 0:
                self._log("[收集] 阶段1完成：评分移动 {} 条，降级移回 {} 条".format(moved, removed))
            else:
                self._log("[收集] 阶段1完成：无旧文件需同步")

            # ---- 阶段2：复制新文件 ----
            self._log("[收集] 阶段2：复制文件（共{}条）...".format(total))
            copied = 0
            move_copy = 0  # 同盘 move+move 回
            skipped_no_file = 0
            skipped_exists = 0
            failed = 0
            records = []  # 用于生成 HTML 报告
            total_bytes = 0
            t_start = time.time()

            # 检测源盘和目标盘是否同盘
            dst_drive = os.path.splitdrive(dst_path)[0].upper()

            for i, rec in enumerate(rows):
                numbers_name = rec[IDX_NUMBERS_NAME]
                film_name = rec[IDX_FILM_NAME] or rec[IDX_NAME] or ""
                performer = rec[IDX_PERFORMER] or ""
                rec_grade = rec[IDX_GRADE]
                local_path = rec[IDX_LOCAL_PATH]
                mosaic = rec[IDX_MOSAIC] or ""
                designation = rec[IDX_DESIGNATION] or ""

                records.append({
                    "numbers_name": numbers_name,
                    "designation": designation,
                    "film_name": film_name,
                    "performer": performer,
                    "grade": rec_grade,
                    "mosaic": mosaic,
                    "local_path": local_path,
                })

                if not local_path or not os.path.exists(local_path):
                    skipped_no_file += 1
                    self._log("[收集] [{}/{}] 跳过(文件不存在)：{}".format(i + 1, total, local_path or numbers_name))
                    continue

                filename = os.path.basename(local_path)
                grade_dir = os.path.join(dst_path, "{}分".format(rec_grade))
                if not os.path.exists(grade_dir):
                    os.makedirs(grade_dir, exist_ok=True)
                dst_file = os.path.join(grade_dir, filename)

                # 已存在且大小相同 → 跳过
                if os.path.exists(dst_file):
                    src_size = os.path.getsize(local_path)
                    dst_size = os.path.getsize(dst_file)
                    if src_size == dst_size:
                        skipped_exists += 1
                        continue

                # 获取文件大小
                src_size = os.path.getsize(local_path)
                size_mb = src_size / 1024 / 1024
                t_copy_start = time.time()
                copy_method = ""

                try:
                    src_drive = os.path.splitdrive(local_path)[0].upper()
                    if src_drive == dst_drive:
                        # 同盘：115网盘等服务端文件系统，shutil.move是服务端操作（秒完成）
                        # shutil.copy2是本地IO（极慢），os.link不支持
                        # 所以同盘只能move，源目录文件会被移走
                        shutil.move(local_path, dst_file)
                        # 同盘move后更新数据库中的local_path
                        try:
                            link_db_cmd("UPDATE av SET local_path = ? WHERE numbers_name = ?", (dst_file, numbers_name), action="高分收集-移动")
                        except Exception as db_err:
                            self._log("[收集] DB路径更新失败：{} - {}".format(numbers_name, db_err))
                        copy_method = "同盘移动"
                        move_copy += 1
                    else:
                        # 跨盘：copy2
                        shutil.copy2(local_path, dst_file)
                        copy_method = "跨盘复制"
                        copied += 1

                    total_bytes += src_size
                    t_copy_end = time.time()
                    elapsed = t_copy_end - t_copy_start

                    if elapsed > 0.1:
                        speed_mbps = size_mb / elapsed
                        self._log("[收集] [{}/{}] {} {} => {}分/{} ({:.0f}MB, {:.1f}s, {:.0f}MB/s)".format(
                            i + 1, total, copy_method, numbers_name, rec_grade, filename, size_mb, elapsed, speed_mbps))
                    else:
                        self._log("[收集] [{}/{}] {} {} => {}分/{} ({:.0f}MB, {:.1f}s)".format(
                            i + 1, total, copy_method, numbers_name, rec_grade, filename, size_mb, elapsed))

                except Exception as e:
                    failed += 1
                    self._log("[收集] [{}/{}] 失败：{} - {}".format(i + 1, total, numbers_name, e))

            # ---- 阶段2汇总 ----
            t_total = time.time() - t_start
            total_mb = total_bytes / 1024 / 1024
            if t_total > 0:
                avg_speed = total_mb / t_total
                self._log("[收集] 阶段2完成：共处理 {:.0f}MB，耗时 {:.1f}s，平均 {:.0f}MB/s".format(total_mb, t_total, avg_speed))
            else:
                self._log("[收集] 阶段2完成：共处理 {:.0f}MB，耗时 {:.1f}s".format(total_mb, t_total))

            # ---- 阶段3：生成报告 ----
            html_path = os.path.join(dst_path, "highgrade_catalog.html")
            try:
                self._generate_catalog_html(records, grade, html_path)
                self._log("[收集] HTML目录清单已生成：{}".format(html_path))
            except Exception as e:
                self._log("[收集] HTML清单生成失败：{}".format(e))

            m3u_path = os.path.join(dst_path, "highgrade_playlist.m3u")
            try:
                self._generate_m3u(records, m3u_path, dst_path)
                self._log("[收集] M3U播放列表已生成：{}".format(m3u_path))
            except Exception as e:
                self._log("[收集] M3U生成失败：{}".format(e))

            self._log("===== 高分收集完成 ===== 总计 {} 条 | 同盘移动 {} | 跨盘复制 {} | 已存在跳过 {} | 文件不存在 {} | 失败 {} | 评分移动 {} | 降级删除 {} | 总大小 {:.0f}MB | 耗时 {:.1f}s".format(
                total, move_copy, copied, skipped_exists, skipped_no_file, failed, moved, removed, total_mb, t_total))

        except Exception as e:
            self._log("高分收集失败：{}".format(e))

    def _scan_highgrade_dir(self, dst_path):
        """扫描高分收集目录，返回 {文件绝对路径: 所在子目录名} 的映射
        子目录名格式为 'XX分'，如 '90分'、'95分'、'100分'
        """
        result = {}
        if not os.path.exists(dst_path):
            return result
        for entry in os.listdir(dst_path):
            sub = os.path.join(dst_path, entry)
            if not os.path.isdir(sub):
                continue
            # 只处理 "XX分" 格式的子目录
            if not entry.endswith("分"):
                continue
            for f in os.listdir(sub):
                fp = os.path.join(sub, f)
                if os.path.isfile(fp) and f.endswith(".mp4"):
                    result[fp] = entry
        return result

    def _clean_empty_subdirs(self, dst_path):
        """清理目标目录下空的 'XX分' 子目录"""
        if not os.path.exists(dst_path):
            return
        for entry in os.listdir(dst_path):
            sub = os.path.join(dst_path, entry)
            if not os.path.isdir(sub):
                continue
            if not entry.endswith("分"):
                continue
            try:
                # 如果目录为空，删除
                if not os.listdir(sub):
                    os.rmdir(sub)
                    self._log("[收集] 清理空目录：{}".format(entry))
            except Exception:
                pass

    def _generate_catalog_html(self, records, grade, html_path):
        """生成高分视频 HTML 目录清单"""
        import datetime
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

        # 按评分分组（每分一组，与子目录对应）
        grade_groups = {}
        for r in records:
            g = r["grade"]
            band = "{}分".format(g)
            if band not in grade_groups:
                grade_groups[band] = []
            grade_groups[band].append(r)

        html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>高分视频目录 (≥{}分)</title>
<style>
body {{ font-family: "Microsoft YaHei", "Segoe UI", sans-serif; margin: 20px; background: #1a1a2e; color: #e0e0e0; }}
h1 {{ color: #e94560; border-bottom: 2px solid #e94560; padding-bottom: 10px; }}
h2 {{ color: #0f3460; background: #16213e; padding: 8px 16px; border-radius: 6px; margin-top: 24px; }}
.summary {{ background: #16213e; padding: 12px 20px; border-radius: 8px; margin: 16px 0; }}
.summary span {{ color: #e94560; font-weight: bold; }}
table {{ width: 100%; border-collapse: collapse; margin: 12px 0; }}
th {{ background: #0f3460; color: #fff; padding: 10px 12px; text-align: left; }}
td {{ padding: 8px 12px; border-bottom: 1px solid #2a2a4a; }}
tr:hover {{ background: #16213e; }}
.grade {{ font-weight: bold; font-size: 16px; }}
.grade-100 {{ color: #ffd700; }}
.grade-90 {{ color: #e94560; }}
.grade-80 {{ color: #ff8c00; }}
.performer {{ color: #53a8b6; }}
a {{ color: #e94560; text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
</style>
</head>
<body>
<h1>★ 高分视频目录 (≥{}分)</h1>
<div class="summary">
生成时间：{} | 共 <span>{}</span> 部 |
""".format(grade, grade, now, len(records))

        for band in sorted(grade_groups.keys(), reverse=True):
            html += ' {} <span>{}</span> 部'.format(band, len(grade_groups[band]))

        html += """
</div>
"""

        for band in sorted(grade_groups.keys(), reverse=True):
            group = grade_groups[band]
            html += '<h2>{} ({}部)</h2>\n'.format(band, len(group))
            html += '<table>\n<tr><th>评分</th><th>番号</th><th>演员</th><th>片名</th><th>码制</th></tr>\n'
            for r in group:
                grade_class = "grade-100" if r["grade"] == 100 else ("grade-90" if r["grade"] >= 90 else "grade-80")
                html += '<tr><td class="grade {}">{}</td><td>{}</td><td class="performer">{}</td><td>{}</td><td>{}</td></tr>\n'.format(
                    grade_class, r["grade"], r["designation"] or r["numbers_name"],
                    r["performer"], r["film_name"], r["mosaic"]
                )
            html += '</table>\n'

        html += """
</body>
</html>"""

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)

    def _generate_m3u(self, records, m3u_path, dst_path):
        """生成 M3U 播放列表（使用相对路径，含子目录）"""
        with open(m3u_path, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for r in records:
                if not r["local_path"] or not os.path.exists(r["local_path"]):
                    continue
                filename = os.path.basename(r["local_path"])
                grade_dir = "{}分".format(r["grade"])
                # 检查目标目录中是否有该文件
                dst_file = os.path.join(dst_path, grade_dir, filename)
                if os.path.exists(dst_file):
                    f.write("#EXTINF:{},{} - {}\n".format(r["grade"], r["designation"] or r["numbers_name"], r["performer"]))
                    f.write("{}/{}\n".format(grade_dir, filename))

    # ============ Tab 6: 小说爬取 ============
    def _build_book_tab(self):
        tab = ttk.Frame(self.nb)
        self.nb.add(tab, text="小说爬取")

        row1 = ttk.Frame(tab)
        row1.pack(fill=tk.X, padx=10, pady=6)

        ttk.Label(row1, text="网站根URL:").pack(side=tk.LEFT)
        self.book_root = ttk.Entry(row1, width=40)
        self.book_root.insert(0, self.config.get("book_root", "https://www.sudugu.org/"))
        self.book_root.pack(side=tk.LEFT, padx=4)

        row2 = ttk.Frame(tab)
        row2.pack(fill=tk.X, padx=10, pady=2)

        ttk.Label(row2, text="起始ID:").pack(side=tk.LEFT)
        self.book_start = ttk.Entry(row2, width=10)
        self.book_start.insert(0, self.config.get("book_start", "45"))
        self.book_start.pack(side=tk.LEFT, padx=4)

        ttk.Label(row2, text="结束ID:").pack(side=tk.LEFT)
        self.book_end = ttk.Entry(row2, width=10)
        self.book_end.insert(0, self.config.get("book_end", "99999"))
        self.book_end.pack(side=tk.LEFT, padx=4)

        self.btn_book_start = ttk.Button(row2, text="开始爬取", command=self._start_book)
        self.btn_book_start.pack(side=tk.LEFT, padx=4)

        self.btn_book_fullsite = ttk.Button(row2, text="全站爬取", command=self._start_book_fullsite)
        self.btn_book_fullsite.pack(side=tk.LEFT, padx=4)

        self.btn_book_update = ttk.Button(row2, text="更新小说", command=self._start_book_update)
        self.btn_book_update.pack(side=tk.LEFT, padx=4)

        self.book_skip_existing = tk.BooleanVar(value=True)
        ttk.Checkbutton(row2, text="跳过已有卷", variable=self.book_skip_existing).pack(side=tk.LEFT, padx=4)

        self.btn_book_stop = ttk.Button(row2, text="停止", command=self._stop_book, state=tk.DISABLED)
        self.btn_book_stop.pack(side=tk.LEFT, padx=4)

        self.book_status = tk.StringVar(value="就绪")
        ttk.Label(row2, textvariable=self.book_status).pack(side=tk.LEFT, padx=10)

        # 进度条
        self.book_progress = ttk.Progressbar(row2, length=200, mode="determinate")
        self.book_progress.pack(side=tk.LEFT, padx=4)
        self.book_progress_label = tk.StringVar(value="")
        ttk.Label(row2, textvariable=self.book_progress_label).pack(side=tk.LEFT, padx=4)

        self.book_result = scrolledtext.ScrolledText(tab, font=("Consolas", 10))
        self.book_result.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

    def _start_book(self):
        try:
            start = int(self.book_start.get())
            end = int(self.book_end.get())
        except ValueError:
            messagebox.showerror("错误", "ID必须是整数")
            return
        root_url = self.book_root.get().strip()
        if not root_url:
            messagebox.showerror("错误", "请输入网站根URL")
            return

        self.book_running = True
        self.book_stats = {"success": 0, "empty": 0, "fail": 0, "retry_ok": 0, "skip": 0}
        self._book_processed = 0
        self._book_total = end - start

        self.btn_book_start.config(state=tk.DISABLED)
        self.btn_book_fullsite.config(state=tk.DISABLED)
        self.btn_book_update.config(state=tk.DISABLED)  # 同时禁用更新按钮
        self.btn_book_stop.config(state=tk.NORMAL)
        self.book_status.set("爬取中...")
        self.book_progress["value"] = 0
        self.book_progress_label.set("0/{}".format(self._book_total))

        t = threading.Thread(target=self._book_worker, args=(root_url, start, end), daemon=True)
        t.start()

    def _start_book_update(self):
        """基于本地索引更新已下载的小说（无需输入ID范围）"""
        root_url = self.book_root.get().strip()
        if not root_url:
            messagebox.showerror("错误", "请输入网站根URL")
            return

        skip_existing = self.book_skip_existing.get()

        # 加载本地索引，获取所有已记录的小说
        index = self._load_book_index()
        books_to_update = []
        for k, v in index.items():
            if k.isdigit():
                books_to_update.append((int(k), v))

        if not books_to_update:
            messagebox.showinfo('提示', '本地暂无已下载的小说记录\n请先使用「下载小说」功能下载几本')
            return

        # 按 ID 排序，保证顺序一致
        books_to_update.sort(key=lambda x: x[0])

        self.book_running = True
        self.book_stats = {"success": 0, "empty": 0, "fail": 0, "retry_ok": 0, "skip": 0}
        self._book_processed = 0
        self._book_total = len(books_to_update)

        self.btn_book_start.config(state=tk.DISABLED)
        self.btn_book_fullsite.config(state=tk.DISABLED)
        self.btn_book_update.config(state=tk.DISABLED)
        self.btn_book_stop.config(state=tk.NORMAL)
        mode_label = "强制全下" if not skip_existing else "跳过已有卷"
        self.book_status.set("更新中({})...".format(mode_label))
        self.book_progress["value"] = 0
        self.book_progress_label.set("0/{}".format(len(books_to_update)))

        self._log("=" * 50)
        self._log("[更新小说] 基于本地索引 | 共{}本待检查 | 模式: {}".format(
            len(books_to_update),
            "跳过已有卷" if skip_existing else "重新下载所有卷"))
        # 列出要更新的书
        for bid, entry in books_to_update:
            name = entry.get("book_name", "?")
            parts = entry.get("downloaded_parts", [])
            ch_num = entry.get("latest_chapter_num", 0) or 0
            completed = entry.get("is_completed", False)
            status = "✓完结" if completed else "连载"
            self._log("   - [id={}] {} | {} | {}/?卷 | 第{}章".format(
                bid, name, status, len(parts), ch_num))
        self._log("=" * 50)

        t = threading.Thread(
            target=self._book_update_worker,
            args=(root_url, books_to_update, skip_existing),
            daemon=True,
        )
        t.start()

    def _book_update_worker(self, root_url, books_to_update, skip_existing):
        """基于本地索引的增量更新工作线程

        参数:
            root_url: 网站根URL
            books_to_update: [(book_id, entry_dict), ...] 从本地索引加载
            skip_existing: True=跳过已有卷, False=强制重新下载
        """
        total = len(books_to_update)
        self._log("开始小说更新：共{}本书 | 模式: {}".format(
            total, "跳过已有卷" if skip_existing else "强制全下"))
        self._log("策略: 逐本访问详情页 → 对比分卷/章节 → 只下载新增内容 → 追加合并")

        for idx, (book_id, entry) in enumerate(books_to_update):
            if not self.book_running:
                self._log("[更新] 用户中断")
                break

            # 更新进度
            self._book_processed = idx + 1
            pct = self._book_processed * 100 // total if total > 0 else 0
            self.root.after(0, self._update_book_progress, pct,
                            self._book_processed, total)

            id_start_time = time.time()

            # 从 entry 获取已存储信息
            stored_book_name = entry.get("book_name", "未知")
            stored_author = entry.get("author", "")
            already_parts = set(entry.get("downloaded_parts", []))
            existing_fpath = entry.get("file_path")
            stored_detail_url = entry.get("detail_url", "")
            stored_latest_chapter = entry.get("latest_chapter_num", 0) or 0
            stored_is_completed = entry.get("is_completed", False)

            self._log(">> [id={}/第{}/{}] {}".format(
                book_id, idx + 1, total, stored_book_name))

            # ===== 第1步：访问详情页获取最新元数据 =====
            detail_url = stored_detail_url or (root_url.rstrip("/") + "/" + str(book_id) + "/txt.html")
            book_name, author, parts_info, latest_chapter, is_completed = self._fetch_book_meta(
                detail_url, book_id)

            if book_name is None:
                self.book_stats["fail"] += 1
                cost_sec = round(time.time() - id_start_time, 1)
                self._log("<< [id={}] 失败 | 无法访问详情页 | 耗时{}s".format(book_id, cost_sec))
                continue

            if not parts_info:
                self.book_stats["empty"] += 1
                self._log("<< [id={}] 无分卷链接，跳过".format(book_id))
                continue

            total_parts = len(parts_info)

            # ===== 判断是否跳过（已完结）=====
            if is_completed or stored_is_completed:
                self._update_book_entry(
                    book_id, book_name, author, total_parts,
                    list(already_parts), existing_fpath, detail_url,
                    latest_chapter or 0, is_completed=True)
                self.book_stats["skip"] += 1
                cost_sec = round(time.time() - id_start_time, 1)
                self._log("<< [id={}] 已完结，跳过 | {} | {}s".format(
                    book_id, book_name, cost_sec))
                continue

            # ===== 准备新增内容 =====
            new_part_count = total_parts - len(already_parts)
            need_chapter_update = False
            if latest_chapter and latest_chapter > stored_latest_chapter:
                need_chapter_update = True
                self._log("   [id={}] ⚠ 新章节! 第{}章 > 本地第{}章 (+{})".format(
                    book_id, latest_chapter, stored_latest_chapter,
                    latest_chapter - stored_latest_chapter))

            # 无新内容 → 秒跳
            should_skip = (new_part_count == 0 and not need_chapter_update)
            if should_skip:
                self._update_book_entry(
                    book_id, book_name, author, total_parts,
                    list(already_parts), existing_fpath, detail_url,
                    latest_chapter, is_completed)
                self.book_stats["skip"] += 1
                cost_sec = round(time.time() - id_start_time, 1)
                self._log("<< [id={}] 已是最新，跳过 | {}/{}卷 | {}s".format(
                    book_id, book_name, len(already_parts), total_parts, cost_sec))
                continue

            # ===== 第2步：下载新增分卷 =====
            self._log("   [id={}] 增量 | 共{}卷 需下{}卷...".format(
                book_id, total_parts, new_part_count))

            downloaded_parts = []
            newly_downloaded_nums = []

            # 如果 skip_existing=False，重新下载所有卷
            if not skip_existing:
                parts_to_process = parts_info
            else:
                parts_to_process = [
                    (pl, pu) for i, (pl, pu) in enumerate(parts_info, 1)
                    if i not in already_parts
                ]

            for part_idx, (part_label, part_url) in enumerate(parts_to_process, 1):
                if not self.book_running:
                    break

                content = self._download_txt_with_retry(part_url, book_id, part_idx)
                if content is not None:
                    downloaded_parts.append((part_label, content))
                    # 提取卷号用于追踪
                    part_no = 0
                    m = re.search(r'\(?(\d+)\s*[-~]', part_label)
                    if m:
                        part_no = int(m.group(1))
                    else:
                        m2 = re.search(r'第?(\d+)卷', part_label)
                        if m2:
                            part_no = int(m2.group(1))
                    if part_no > 0:
                        newly_downloaded_nums.append(part_no)

                # 分卷间延迟
                if part_idx < len(parts_to_process):
                    time.sleep(random.uniform(1.0, 2.0))

            if not self.book_running and not downloaded_parts:
                continue

            # ===== 第3步：写入文件 + 章节增量 =====
            all_downloaded = sorted(set(list(already_parts) + newly_downloaded_nums))
            final_chapter = latest_chapter or stored_latest_chapter
            total_bytes = 0
            chap_append_count = 0

            if downloaded_parts or (need_chapter_update and existing_fpath):
                try:
                    if (existing_fpath and os.path.exists(existing_fpath)):
                        fpath = existing_fpath
                        write_mode = "a"
                    else:
                        # 需要创建新文件
                        day_name = time.strftime("%Y%m%d")
                        book_dir = os.path.join(".", "output", "book", day_name)
                        os.makedirs(book_dir, exist_ok=True)
                        fname = "{}-{}-{}.txt".format(book_id, book_name, author or "未知")
                        fname = re.sub(r'[\\/:*?"<>|]', '_', fname)
                        fpath = os.path.join(book_dir, fname)
                        write_mode = "w"

                    with open(fpath, write_mode, encoding="utf-8") as f:
                        if write_mode == "w":
                            f.write("=" * 50 + "\n")
                            f.write("书名: {}\n".format(book_name))
                            f.write("作者: {}\n".format(author or "未知"))
                            f.write("来源: {}\n".format(detail_url))
                            f.write("分卷数: {}/{}\n".format(
                                len(all_downloaded), total_parts))
                            f.write("爬取时间: {}\n".format(
                                time.strftime("%Y-%m-%d %H:%M:%S")))
                            f.write("=" * 50 + "\n\n")
                        else:
                            f.write("\n\n")
                            f.write("=" * 50 + "\n")
                            f.write("--- 增量更新: {} ---\n".format(
                                time.strftime("%Y-%m-%d %H:%M:%S")))
                            f.write("=" * 50 + "\n\n")

                        for plabel, pcontent in downloaded_parts:
                            f.write("\n" + "=" * 50 + "\n")
                            f.write("--- 分卷: {} ---\n".format(plabel))
                            f.write("=" * 50 + "\n\n")
                            f.write(pcontent)
                            f.write("\n")
                            total_bytes += len(pcontent)

                    self._update_book_entry(
                        book_id, book_name, author, total_parts,
                        all_downloaded, fpath, detail_url,
                        final_chapter, is_completed)

                    # ===== 章节级增量 =====
                    if need_chapter_update and stored_latest_chapter > 0:
                        self._log("   [id={}] 章节增量 (第{}→{}章)...".format(
                            book_id, stored_latest_chapter, latest_chapter))
                        root_m = re.match(r'(https?://[^/]+)', root_url)
                        base_root = root_m.group(1) if root_m else root_url
                        new_chaps = self._fetch_directory_chapters(
                            base_root, book_id, known_max=stored_latest_chapter)
                        if new_chaps:
                            try:
                                with open(fpath, "a", encoding="utf-8") as f:
                                    f.write("\n\n")
                                    f.write("=" * 50 + "\n")
                                    f.write("--- 增量更新: 新增 {} 章 ---\n".format(
                                        len(new_chaps)))
                                    f.write("更新时间: {}\n".format(
                                        time.strftime("%Y-%m-%d %H:%M:%S")))
                                    f.write("=" * 50 + "\n\n")

                                    for ci, (cn, ct, cu) in enumerate(new_chaps, 1):
                                        if not self.book_running:
                                            break
                                        clabel = "第{}章 {}".format(cn, ct) if cn > 0 else ct
                                        ch_text = self._download_single_chapter(
                                            cu, book_id, clabel)
                                        if ch_text:
                                            f.write("\n## {}\n\n{}\n\n".format(
                                                clabel, ch_text))
                                            total_bytes += len(ch_text.encode('utf-8'))
                                            chap_append_count += 1

                                mx = max([c[0] for c in new_chaps if c[0] > 0],
                                         default=0)
                                final_chapter = max(final_chapter, mx)
                                self._update_book_entry(
                                    book_id, book_name, author, total_parts,
                                    all_downloaded, fpath, detail_url,
                                    final_chapter, is_completed)
                            except Exception as e:
                                self._log("   [id={}] 章节追加失败: {}".format(
                                    book_id, e))

                    cost_sec = round(time.time() - id_start_time, 1)
                    mtag = ""
                    if downloaded_parts:
                        mtag = "[+{}卷]".format(len(downloaded_parts))
                    if chap_append_count > 0:
                        mtag += "[+{}章]".format(chap_append_count)
                    self._log("<< [id={}] 完成{} | {} | {}/{}卷 | {}字节 | {}s".format(
                        book_id, mtag, book_name, len(all_downloaded),
                        total_parts, total_bytes, cost_sec))
                    self.book_stats["success"] += 1

                except Exception as e:
                    self._log("   [id={}] 写入失败: {}".format(book_id, e))
                    self.book_stats["fail"] += 1
            else:
                cost_sec = round(time.time() - id_start_time, 1)
                self._log("<< [id={}] 所有操作均失败 | {}s".format(book_id, cost_sec))
                self.book_stats["fail"] += 1

        # ===== 汇总统计 =====
        self._log("=" * 50)
        if not self.book_running:
            self._log("[用户中断] 小说更新被手动停止")
        else:
            self._log("小说更新完成！")
        sk = self.book_stats.get("skip", 0)
        sl = ("成功: {} | 无分卷: {} | 失败: {}".format(
                self.book_stats["success"],
                self.book_stats["empty"],
                self.book_stats["fail"]))
        if sk > 0:
            sl += " | 跳过(含完结): {}".format(sk)
        sl += " | 总计: {}/{}".format(self._book_processed, total)
        self._log(sl)
        self._log("=" * 50)

        # 恢复UI
        self.root.after(0, lambda: [
            self.btn_book_start.config(state=tk.NORMAL),
            self.btn_book_fullsite.config(state=tk.NORMAL),
            self.btn_book_update.config(state=tk.NORMAL),
            self.btn_book_stop.config(state=tk.DISABLED),
            self.book_status.set("就绪"),
            self.book_progress.config(value=100),
        ])

    def _start_book_fullsite(self):
        """全站爬取：先从列表页采集全站小说ID，再逐本下载/增量更新"""
        root_url = self.book_root.get().strip()
        if not root_url:
            messagebox.showerror("错误", "请输入网站根URL")
            return

        self.btn_book_start.config(state=tk.DISABLED)
        self.btn_book_fullsite.config(state=tk.DISABLED)
        self.btn_book_update.config(state=tk.DISABLED)
        self.book_running = True
        self.btn_book_stop.config(state=tk.NORMAL)

        self._log("=" * 50)
        self._log("[全站爬取] 开始采集全站小说列表...")
        self._log("[全站爬取] 目标: {}".format(root_url))
        self.book_status.set("正在采集全站列表...")

        t = threading.Thread(target=self._fullsite_phase1_discover, args=(root_url,), daemon=True)
        t.start()

    def _fullsite_phase1_discover(self, root_url):
        """流式全站爬取：边采集列表页边下载小说。
        
        流程：
          1. 加载本地索引（用于判断新书/已完结跳过）
          2. 爬取第N页列表 → 提取书籍ID → 立即逐本下载
          3. 继续第N+1页，直到全部完成或用户中断
        """
        list_base = root_url.rstrip("/") + "/zuixin"
        total_pages = 0
        full_start = time.time()

        # ===== 预加载本地索引 =====
        book_index = self._load_book_index()
        self._log("[全站] 本地索引已加载: {}本".format(len(book_index)))

        # ===== 初始化统计 & 进度 =====
        self.book_stats = {"success": 0, "empty": 0, "fail": 0, "retry_ok": 0, "skip": 0}
        self._book_processed = 0
        self._book_total = 0  # 流式模式下总数未知
        seen_ids = set()      # 本次会话已处理的ID（跨页去重）

        try:
            first_url = list_base + "/1.html"
            self._log("[全站] 第1页: {}".format(first_url))
            html = get_url_txt_without_cookie(first_url)
            if not html or len(html) < 200:
                self._log("[全站] ✗ 列表页请求失败，无法获取书籍列表")
                self.root.after(0, lambda: [
                    self.btn_book_start.config(state=tk.NORMAL),
                    self.btn_book_fullsite.config(state=tk.NORMAL),
                    self.btn_book_update.config(state=tk.NORMAL),
                    self.book_status.set("就绪"),
                ])
                return

            # 提取总页数：从分页区域找 "末页" 链接或 "1/408" 格式
            # 限定分页上下文，避免匹配到日期(2026/06)等无关数字
            page_match = re.search(r'(?:页\s*|page\s*|共\s*)(\d+)/(\d+)', html, re.I)
            if page_match:
                total_pages = int(page_match.group(2))
                # 合理性校验：单站不可能超过10万页，匹配到异常值则忽略
                if total_pages > 100000:
                    self._log("[全站] ⚠ 页数异常({})，跳过正则匹配".format(total_pages))
                    total_pages = 0
            else:
                last_match = re.search(r'href=["\'].*?/zuixin/(\d+)\.html["\'][^>]*>[^<]*末', html, re.I)
                if last_match:
                    total_pages = int(last_match.group(1))

            if total_pages == 0:
                # 尝试从 "末页" 或最后一页链接推断
                page_nums = re.findall(r'/zuixin/(\d+)\.html', html)
                if page_nums:
                    total_pages = max(int(p) for p in page_nums)

            if total_pages == 0:
                total_pages = 1  # 至少有第1页
            self._log("[全站] 检测到共 {} 页（每页约10本） | 模式: 流式(边采边下)".format(total_pages))

            # 处理第1页的书籍
            ids_from_page = self._extract_book_ids_from_list(html)
            self._log("[全站] 第1页 → 发现{}本".format(len(ids_from_page)))
            self._process_page_books(root_url, ids_from_page, book_index, seen_ids)

            # 继续抓取剩余页面（流式模式：每页采集后立即下载）
            # 反爬策略：
            #   1. 基础延迟 2~4s 随机（避免固定间隔被识别）
            #   2. 连续失败自动加长冷却（指数退避，上限 30s）
            #   3. 检测反爬重定向/验证码页面，触发长冷却
            #   4. 每采集 50 页额外暂停 5s（模拟人类休息）
            _consecutive_fails = 0   # 连续失败计数（列表页级别）
            _base_delay = 2.5        # 基础秒数

            for page in range(2, total_pages + 1):
                if not self.book_running:
                    self._log("[全站] 用户中断")
                    break

                page_url = list_base + "/{}.html".format(page)

                # === 自适应延迟（本次请求前）===
                if _consecutive_fails > 0:
                    # 指数退避：失败越多等越久
                    fail_delay = min(_base_delay * (2 ** _consecutive_fails), 30)
                else:
                    fail_delay = 0

                # 基础随机延迟 2~4s + 失败惩罚延迟
                rand_delay = _base_delay + random.uniform(-0.8, 1.5) + fail_delay
                time.sleep(rand_delay)

                try:
                    page_html = get_url_txt_without_cookie(page_url)
                    if page_html and len(page_html) > 200:
                        # === 反爬检测（强信号优先） ===
                        lower_html = page_html.lower()
                        anticrawl_signals = []

                        if 'google.com' in page_html or 'google' in lower_html[:500]:
                            anticrawl_signals.append("重定向到Google")
                        if 'captcha' in lower_html or '验证码' in page_html:
                            anticrawl_signals.append("验证码页面")
                        if 'cloudflare' in lower_html:
                            anticrawl_signals.append("Cloudflare防护")
                        if '人机' in page_html or 'robot' in lower_html:
                            anticrawl_signals.append("人机检测")
                        if ('just a moment' in lower_html
                                or 'attention required' in lower_html):
                            anticrawl_signals.append("CF挑战页")

                        # 强信号命中 → 直接判反爬，无需尝试解析
                        if anticrawl_signals:
                            _consecutive_fails += 1
                            signal_str = " | ".join(anticrawl_signals)
                            cooldown = min(_consecutive_fails * 10, 60)
                            self._log("[全站] ⚠ 第{}页 触发反爬! [{}] | 冷却{}s...".format(
                                page, signal_str, cooldown))
                            _cleanup_stale_connections()
                            time.sleep(cooldown)
                            continue

                        # 无强信号 → 先尝试提取书籍列表（避免 /txt.html 误报）
                        page_ids = self._extract_book_ids_from_list(page_html)
                        if page_ids:
                            # 正常页面：成功提取到书籍
                            _consecutive_fails = 0
                            self._log("[全站] 第{}页 → 发现{}本".format(page, len(page_ids)))
                            # ★ 流式核心：立即处理这页的书籍
                            self._process_page_books(root_url, page_ids, book_index, seen_ids)
                        else:
                            # 提取失败：可能是异常页，记录内容预览便于排查
                            content_preview = page_html[:200].replace('\n', ' ').strip()
                            has_txt_link = '/txt.html' in page_html
                            self._log("[全站] 🔍 第{}页 提取到0本书 | 含/txt.html链接={} | 内容预览: {}... (共{}字节)".format(
                                page, has_txt_link, content_preview, len(page_html)))
                            # 如果既没有 /txt.html 链接也提取不到书，才算异常
                            if not has_txt_link:
                                anticrawl_signals.append("非列表页内容")
                                _consecutive_fails += 1
                                cooldown = min(_consecutive_fails * 10, 60)
                                self._log("[全站] ⚠ 第{}页 可疑页面! [{}] | 冷却{}s...".format(
                                    page, " | ".join(anticrawl_signals), cooldown))
                                _cleanup_stale_connections()
                                time.sleep(cooldown)
                                continue
                            else:
                                # 有 /txt.html 但提取不到书，可能只是空页/末页，不算反爬
                                _consecutive_fails += 1
                                self._log("[全站] 第{}页 列表为空(有链接但无数据) [连续失败#{}]".format(
                                    page, _consecutive_fails))
                    else:
                        # 空内容或过短
                        _consecutive_fails += 1
                        self._log("[全站] 第{}页 内容为空或过短({}字节) [连续失败#{}]".format(
                            page, len(page_html) if page_html else 0,
                            _consecutive_fails))

                except Exception as e:
                    cat, is_conn = _classify_error(e)
                    _consecutive_fails += 1
                    if is_conn:
                        _cleanup_stale_connections()
                    self._log("[全站] 第{}页请求失败: [{}] | {} [连续失败#{}]".format(
                        page, cat, e, _consecutive_fails))

                # 每50页额外暂停（模拟人类浏览节奏）
                if page % 50 == 0 and page < total_pages:
                    self._log("[全站] 已采集{}页，短暂休息5s...".format(page))
                    time.sleep(5)

                # 每10页汇报一次进度
                if page % 10 == 0 or page == total_pages:
                    elapsed = round(time.time() - full_start, 1)
                    self._log("[全站] 进度: {}/{}页 | 已处理{}本书 | 耗时{}s{}".format(
                        page, total_pages, self._book_processed, elapsed,
                        " | ⚠连续失败#{}".format(_consecutive_fails) if _consecutive_fails > 2 else ""))

        except Exception as e:
            self._log("[全站] ✗ 过程异常: {}".format(e))

        # ===== 最终汇总 =====
        elapsed_total = round(time.time() - full_start, 1)
        self._log("=" * 50)
        if not self.book_running:
            self._log("[用户中断] 全站爬取被停止")
        else:
            self._log("全站爬取完成！")
        sk = self.book_stats.get("skip", 0)
        sl = ("成功: {} | 无分卷: {} | 失败: {}"
              .format(self.book_stats["success"],
                      self.book_stats["empty"],
                      self.book_stats["fail"]))
        if sk > 0:
            sl += " | 跳过(含完结): {}".format(sk)
        sl += " | 共处理: {}本 | 总耗时: {}s".format(self._book_processed, elapsed_total)
        self._log(sl)
        self._log("=" * 50)

        self.root.after(0, lambda: [
            self.btn_book_start.config(state=tk.NORMAL),
            self.btn_book_fullsite.config(state=tk.NORMAL),
            self.btn_book_update.config(state=tk.NORMAL),
            self.btn_book_stop.config(state=tk.DISABLED),
            self.book_status.set("就绪"),
        ])

    def _process_page_books(self, root_url, page_book_ids, book_index, seen_ids):
        """处理一页列表中发现的书籍：逐本判断并下载。

        Args:
            root_url: 站点根URL
            page_book_ids: 本页提取到的书籍ID列表 [int, ...]
            book_index: 本地索引字典
            seen_ids: 本次会话已处理过的ID集合（跨页去重），会被就地修改
        """
        for book_id in page_book_ids:
            if not self.book_running:
                return

            # 跨页去重（同一本书可能出现在多页）
            if book_id in seen_ids:
                continue
            seen_ids.add(book_id)

            self._book_processed += 1
            self._book_total = max(self._book_total, self._book_processed)

            id_start_time = time.time()
            is_known = str(book_id) in book_index

            # 日志标签
            if is_known:
                entry = book_index[str(book_id)]
                stored_name = entry.get("book_name", "未知")
                status = "✓完结" if entry.get("is_completed") else "连载"
                tag = "[已知/{}]".format(status)
            else:
                stored_name = "?"
                tag = "[NEW]"

            # 更新进度条
            pct = min(self._book_processed * 100 // max(self._book_total, 1), 100)
            self.root.after(0, self._update_book_progress, pct,
                            self._book_processed, self._book_total or self._book_processed)

            self._log(">> [id={}/第{}本] {} 开始 | {}".format(
                book_id, self._book_processed, tag, stored_name))

            # ===== 第1步：访问详情页 =====
            detail_url = root_url.rstrip("/") + "/" + str(book_id) + "/txt.html"
            if is_known and book_index[str(book_id)].get("detail_url"):
                detail_url = book_index[str(book_id)]["detail_url"]

            book_name, author, parts_info, latest_chapter, is_completed = self._fetch_book_meta(
                detail_url, book_id)

            if book_name is None:
                self.book_stats["fail"] += 1
                cost_sec = round(time.time() - id_start_time, 1)
                self._log("<< [id={}] 失败 | 无法访问详情页 | 耗时{}s".format(
                    book_id, cost_sec))
                continue

            if not parts_info:
                self.book_stats["empty"] += 1
                self._log("   [id={}] 无分卷链接，跳过".format(book_id))
                continue

            total_parts = len(parts_info)

            # ===== 判断是否跳过（已完结）=====
            if is_completed or (is_known and book_index[str(book_id)].get("is_completed")):
                already_parts = set()
                existing_fpath = None
                if is_known:
                    e = book_index[str(book_id)]
                    already_parts = set(e.get("downloaded_parts", []))
                    existing_fpath = e.get("file_path")
                self._update_book_entry(
                    book_id, book_name, author, total_parts,
                    list(already_parts), existing_fpath, detail_url,
                    latest_chapter or 0, is_completed=True)
                self.book_stats["skip"] += 1
                cost_sec = round(time.time() - id_start_time, 1)
                self._log("<< [id={}] 已完结，跳过 | {} | {}s".format(
                    book_id, book_name, cost_sec))
                continue

            # ===== 准备已下载信息 =====
            already_parts = set()
            already_labels = set()  # 已下载的分卷标签（用于标签去重）
            existing_fpath = None
            stored_latest_chapter = 0
            if is_known:
                entry = book_index[str(book_id)]
                already_parts = set(entry.get("downloaded_parts", []))
                already_labels = set(entry.get("downloaded_labels", []))
                existing_fpath = entry.get("file_path")
                stored_latest_chapter = entry.get("latest_chapter_num", 0) or 0

            new_part_count = total_parts - len(already_parts)
            need_chapter_update = False
            if latest_chapter and latest_chapter > stored_latest_chapter:
                need_chapter_update = True
                self._log("   [id={}] ⚠ 新章节! 第{}章 > 本地第{}章 (+{})".format(
                    book_id, latest_chapter, stored_latest_chapter,
                    latest_chapter - stored_latest_chapter))

            # 已知书 + 无新内容 → 秒跳
            should_skip = (is_known and new_part_count == 0
                           and not need_chapter_update)
            if should_skip:
                self._update_book_entry(
                    book_id, book_name, author, total_parts,
                    list(already_parts), existing_fpath, detail_url,
                    latest_chapter, is_completed)
                self.book_stats["skip"] += 1
                cost_sec = round(time.time() - id_start_time, 1)
                self._log("<< [id={}] 已是最新，跳过 | {}/{}卷 | {}s".format(
                    book_id, book_name, len(already_parts), total_parts, cost_sec))
                continue

            # ===== 第2步：下载分卷 =====
            dl_label = "全量" if not is_known else "增量(+{}卷)".format(new_part_count)
            self._log("   [id={}] {} | 共{}卷 需下{}卷...".format(
                book_id, dl_label, total_parts,
                new_part_count if is_known else total_parts))

            downloaded_parts = []
            newly_downloaded_nums = []
            newly_downloaded_labels = []  # 记录新下载的标签，用于保存到索引
            for part_idx, (part_label, part_url) in enumerate(parts_info, 1):
                if not self.book_running:
                    break
                if part_idx in already_parts:
                    continue
                # ★ 标签去重：防止站方调整分卷结构导致重复下载
                clean_label = part_label.lower().replace('.txt', '').strip()
                if any(clean_label == al.lower().replace('.txt', '').strip()
                       for al in already_labels):
                    self._log("   [id={}/卷{}] 标签重复跳过: '{}'".format(
                        book_id, part_idx, part_label))
                    continue
                content = self._download_txt_with_retry(part_url, book_id, part_idx)
                if content is not None:
                    downloaded_parts.append((part_label, content))
                    newly_downloaded_nums.append(part_idx)
                    newly_downloaded_labels.append(part_label)

                if part_idx < len(parts_info):
                    time.sleep(random.uniform(1.0, 2.0))

            if not self.book_running and not downloaded_parts:
                continue

            # ===== 第3步：写入文件 + 第4步：章节增量 =====
            all_downloaded = sorted(already_parts | set(newly_downloaded_nums))
            final_chapter = latest_chapter or stored_latest_chapter
            total_bytes = 0
            chap_append_count = 0

            if downloaded_parts or (need_chapter_update and existing_fpath):
                try:
                    day_name = time.strftime("%Y%m%d")
                    book_dir = os.path.join(".", "output", "book", day_name)
                    os.makedirs(book_dir, exist_ok=True)

                    if (existing_fpath and os.path.exists(existing_fpath)):
                        fpath = existing_fpath
                    else:
                        fname = "{}-{}-{}.txt".format(
                            book_id, book_name, author or "未知")
                        fname = re.sub(r'[\\/:*?"<>|]', '_', fname)
                        fpath = os.path.join(book_dir, fname)

                    write_mode = "a" if (
                        is_known and existing_fpath
                        and os.path.exists(existing_fpath)) else "w"

                    with open(fpath, write_mode, encoding="utf-8") as f:
                        if write_mode == "w":
                            f.write("=" * 50 + "\n")
                            f.write("书名: {}\n".format(book_name))
                            f.write("作者: {}\n".format(author or "未知"))
                            f.write("来源: {}\n".format(detail_url))
                            f.write("分卷数: {}/{}\n".format(
                                len(all_downloaded), total_parts))
                            f.write("爬取时间: {}\n".format(
                                time.strftime("%Y-%m-%d %H:%M:%S")))
                            if is_known and newly_downloaded_nums:
                                f.write("备注: 全站增量追加{}个新卷\n".format(
                                    len(downloaded_parts)))
                            f.write("=" * 50 + "\n\n")

                        for plabel, pcontent in downloaded_parts:
                            f.write("\n" + "=" * 50 + "\n")
                            f.write("--- 分卷: {} ---\n".format(plabel))
                            f.write("=" * 50 + "\n\n")
                            f.write(pcontent)
                            f.write("\n")
                            total_bytes += len(pcontent)

                    # 合并已下载标签（旧 + 新）
                    all_labels = list(set(already_labels) | set(newly_downloaded_labels))
                    self._update_book_entry(
                        book_id, book_name, author, total_parts,
                        all_downloaded, fpath, detail_url,
                        final_chapter, is_completed,
                        downloaded_part_labels=all_labels)

                    # ===== 章节级增量 =====
                    if need_chapter_update and stored_latest_chapter > 0:
                        self._log("   [id={}] 章节增量 (第{}→{}章)...".format(
                            book_id, stored_latest_chapter, latest_chapter))
                        chap_start = time.time()
                        chap_timeout = 300  # 章节增量总超时5分钟（大长篇目录页多）
                        root_m = re.match(r'(https?://[^/]+)', root_url)
                        base_root = root_m.group(1) if root_m else root_url
                        try:
                            new_chaps = self._fetch_directory_chapters(
                                base_root, book_id, known_max=stored_latest_chapter)
                            chap_fetch_cost = round(time.time() - chap_start, 1)

                            if not new_chaps:
                                self._log("   [id={}] 目录未发现新章节 (耗时{}s)".format(
                                    book_id, chap_fetch_cost))
                            else:
                                self._log("   [id={}] 目录找到 {} 个新章 (耗时{}s)，开始下载...".format(
                                    book_id, len(new_chaps), chap_fetch_cost))

                                with open(fpath, "a", encoding="utf-8") as f:
                                    f.write("\n\n")
                                    f.write("=" * 50 + "\n")
                                    f.write("--- 全站增量: 新增 {} 章 ---\n".format(
                                        len(new_chaps)))
                                    f.write("更新时间: {}\n".format(
                                        time.strftime("%Y-%m-%d %H:%M:%S")))
                                    f.write("=" * 50 + "\n\n")

                                    for ci, (cn, ct, cu) in enumerate(new_chaps, 1):
                                        # 超时检查
                                        if time.time() - chap_start > chap_timeout:
                                            self._log("   [id={}] ⚠ 章节增量超时({}s)，已下{}/{}章".format(
                                                book_id, chap_timeout, ci, len(new_chaps)))
                                            break
                                        if not self.book_running:
                                            break
                                        clabel = "第{}章 {}".format(
                                            cn, ct) if cn > 0 else ct
                                        ch_text = self._download_single_chapter(
                                            cu, book_id, clabel)
                                        if ch_text:
                                            f.write("\n## {}\n\n{}\n\n".format(
                                                clabel, ch_text))
                                            total_bytes += len(ch_text.encode('utf-8'))
                                            chap_append_count += 1

                                        if ci < len(new_chaps):
                                            time.sleep(random.uniform(1.5, 3.0))

                                mx = max([c[0] for c in new_chaps if c[0] > 0],
                                         default=0)
                                final_chapter = max(final_chapter, mx)
                                self._update_book_entry(
                                    book_id, book_name, author, total_parts,
                                    all_downloaded, fpath, detail_url,
                                    final_chapter, is_completed,
                                    downloaded_part_labels=all_labels)

                                chap_total_cost = round(time.time() - chap_start, 1)
                                self._log("   [id={}] 章节增量完成: +{}章 | 总耗时{}s".format(
                                    book_id, chap_append_count, chap_total_cost))

                        except Exception as e:
                            self._log("   [id={}] 章节追加失败: {}".format(
                                book_id, e))

                    cost_sec = round(time.time() - id_start_time, 1)
                    mtag = ""
                    if not is_known:
                        mtag = "[NEW]"
                    elif downloaded_parts:
                        mtag = "[+{}卷]".format(len(downloaded_parts))
                    if chap_append_count > 0:
                        mtag += "[+{}章]".format(chap_append_count)
                    self._log("<< [id={}] 完成{} | {} | {}/{}卷 | {}字节 | {}s".format(
                        book_id, mtag, book_name, len(all_downloaded),
                        total_parts, total_bytes, cost_sec))
                    self.book_stats["success"] += 1

                except Exception as e:
                    self._log("   [id={}] 写入失败: {}".format(book_id, e))
                    self.book_stats["fail"] += 1
            else:
                cost_sec = round(time.time() - id_start_time, 1)
                self._log("<< [id={}] 所有操作均失败 | {}s".format(book_id, cost_sec))
                self.book_stats["fail"] += 1

            # 书籍间延迟
            if self.book_running:
                time.sleep(random.uniform(2.0, 4.0))

    def _extract_book_ids_from_list(self, html):
        """从列表页HTML中提取所有书籍ID。
        匹配模式: href="/{数字}/" 形式的书籍链接
        返回: [int, ...] 有序ID列表
        """
        # 匹配 /{数字}/ 格式的链接（书籍主页链接）
        ids = re.findall(r'href=["\']\/(\d+)\/["\']', html)
        # 过滤掉明显不是书籍ID的（比如太小的数字可能是其他导航链接）
        result = []
        for sid in ids:
            iid = int(sid)
            if iid >= 2:  # 书籍ID一般 >= 2
                result.append(iid)
        return result
        """基于本地索引的增量更新工作线程

        参数:
            root_url: 网站根URL（用于构造章节目录等）
            books_to_update: [(book_id, entry_dict), ...] 从本地索引加载的待更新列表
            skip_existing: True=跳过已有卷号(默认), False=强制重新下载所有卷
        """
        total = len(books_to_update)
        mode_label = "跳过已有卷" if skip_existing else "强制全下"
        self._log("开始小说更新：基于本地索引，共{}本书 | 模式: {}".format(total, mode_label))
        self._log("策略: 逐本访问详情页 → 对比分卷/章节 → 只下载新增内容 → 追加合并")

        for idx, (book_id, entry) in enumerate(books_to_update):
            if not self.book_running:
                self._log("[更新] 用户中断")
                break

            # 更新进度（本粒度）
            self._book_processed = idx + 1
            pct = self._book_processed * 100 // total if total > 0 else 0
            self.root.after(0, self._update_book_progress, pct,
                            self._book_processed, total)

            id_start_time = time.time()
            stored_book_name = entry.get("book_name", "未知")
            stored_author = entry.get("author", "")
            already_parts = set(entry.get("downloaded_parts", []))
            existing_fpath = entry.get("file_path")
            stored_detail_url = entry.get("detail_url", "")
            stored_latest_chapter = entry.get("latest_chapter_num", 0) or 0
            stored_total_parts = entry.get("total_parts", 0)

            self._log(">> [id={}/第{}本] 开始检查 | {}".format(
                book_id, idx + 1, stored_book_name))

            # ===== 第1步：重新访问详情页获取最新元数据 =====
            # 优先使用存储的 detail_url，如果没有则用 root_url 拼接
            detail_url = stored_detail_url
            if not detail_url:
                detail_url = root_url.rstrip("/") + "/" + str(book_id) + "/txt.html"

            self._log("   [id={}] 步骤1/3 访问详情页: {}".format(book_id, detail_url))

            book_name, author, parts_info, latest_chapter, is_completed = self._fetch_book_meta(
                detail_url, book_id)

            if book_name is None:
                # 详情页请求失败 — 跳过这本书
                self.book_stats["fail"] += 1
                cost_sec = round(time.time() - id_start_time, 1)
                self._log("<< [id={}] 失败 | 无法访问详情页 | 耗时{}秒 | 可能网站不可达或ID失效".format(
                    book_id, cost_sec))
                continue

            if not parts_info:
                self._log("   [id={}] 详情页无分卷链接，跳过".format(book_id))
                self.book_stats["empty"] += 1
                continue

            total_parts = len(parts_info)
            status_tag = "✓已完结" if is_completed else "连载中"
            self._log("   [id={}] 元数据 | 书名:{} | 作者:{} | {}卷 | 第{}章 | {}".format(
                book_id, book_name, author or "未知", total_parts,
                latest_chapter or "?", status_tag))

            # 已完结的小说跳过更新（不会再有新内容）
            if is_completed:
                # 同步更新索引中的完结状态和元数据
                self._update_book_entry(
                    book_id, book_name, author,
                    total_parts,
                    list(already_parts), existing_fpath, detail_url,
                    latest_chapter or stored_latest_chapter, is_completed=True)
                self.book_stats["skip"] += 1
                cost_sec = round(time.time() - id_start_time, 1)
                self._log("<< [id={}] 已完结，跳过 | {} | 耗时{}s".format(
                    book_id, book_name, cost_sec))
                continue

            # ===== 第2步：对比本地记录，计算需要下载的内容 =====
            if not skip_existing:
                # 强制全下模式：清空已有集合
                already_parts = set()

            new_part_count = total_parts - len(already_parts)

            # 检测是否有新章节（即使分卷数没变）
            need_chapter_update = False
            if latest_chapter and latest_chapter > stored_latest_chapter:
                need_chapter_update = True
                self._log("   [id={}] ⚠ 检测到新章节! 站上第{}章 > 本地第{}章 (+{}章)".format(
                    book_id, latest_chapter, stored_latest_chapter,
                    latest_chapter - stored_latest_chapter))

            # 全部已是最新 → 跳过
            should_skip = (skip_existing and new_part_count == 0
                           and not need_chapter_update)
            if should_skip:
                # 同步更新索引中的元数据（保持 total_parts 和 latest_chapter 最新）
                self._update_book_entry(
                    book_id, book_name, author, total_parts,
                    list(already_parts), existing_fpath, detail_url,
                    latest_chapter, is_completed)
                self.book_stats["skip"] += 1
                cost_sec = round(time.time() - id_start_time, 1)
                self._log("<< [id={}] 已是最新 | {}/{}卷 | 第{}章 | 耗时{}s".format(
                    book_id, len(already_parts), total_parts,
                    stored_latest_chapter, cost_sec))
                continue

            dl_label = "增{}卷".format(new_part_count) if new_part_count > 0 else ""
            if need_chapter_update:
                dl_label += " +新章节"
            self._log("   [id={}] 步骤2/3 需下载: {} (共{}卷, 缺{}卷)...".format(
                book_id, dl_label or "仅章节更新", total_parts, new_part_count))

            # ===== 第3步：逐卷下载缺失的分卷 =====
            downloaded_parts = []
            newly_downloaded_nums = []

            for part_idx, (part_label, part_url) in enumerate(parts_info, 1):
                if not self.book_running:
                    self._log("   [id={}] 中断，已下{}/{}卷".format(
                        book_id, part_idx - 1, total_parts))
                    break

                if part_idx in already_parts:
                    continue

                self._log("   [id={}/卷{}/{}] {}".format(
                    book_id, part_idx, total_parts, part_url))

                content = self._download_txt_with_retry(part_url, book_id, part_idx)
                if content is not None:
                    downloaded_parts.append((part_label, content))
                    newly_downloaded_nums.append(part_idx)
                    self._log("   [id={}/卷{}/{}] OK | {} | {}字节".format(
                        book_id, part_idx, total_parts, part_label, len(content)))
                else:
                    self._log("   [id={}/卷{}/{}] 失败(已重试3次)，跳过".format(
                        book_id, part_idx, total_parts))

                # 分卷间延迟
                if part_idx < len(parts_to_process):
                    time.sleep(random.uniform(1.0, 2.0))

            if not self.book_running and not downloaded_parts:
                continue

            # ===== 合并写入文件 =====
            all_downloaded = sorted(already_parts | set(newly_downloaded_nums))
            final_chapter = latest_chapter or stored_latest_chapter
            total_bytes = 0
            chap_append_count = 0

            if downloaded_parts or (need_chapter_update and existing_fpath):
                try:
                    day_name = time.strftime("%Y%m%d")
                    book_dir = os.path.join(".", "output", "book", day_name)
                    os.makedirs(book_dir, exist_ok=True)

                    # 文件路径：优先用已有的，否则新建
                    if existing_fpath and os.path.exists(existing_fpath):
                        fpath = existing_fpath
                    else:
                        fname = "{}-{}-{}.txt".format(
                            book_id, book_name, author or "未知")
                        fname = re.sub(r'[\\/:*?"<>|]', '_', fname)
                        fpath = os.path.join(book_dir, fname)

                    is_append = (skip_existing and existing_fpath
                                 and os.path.exists(existing_fpath)
                                 and not newly_downloaded_nums)
                    # 有新卷下载时总是追加（除非文件不存在）
                    write_mode = "a" if (is_append or (
                        existing_fpath and os.path.exists(existing_fpath))) else "w"

                    with open(fpath, write_mode, encoding="utf-8") as f:
                        if write_mode == "w":
                            # 新建文件写头
                            f.write("=" * 50 + "\n")
                            f.write("书名: {}\n".format(book_name))
                            f.write("作者: {}\n".format(author or "未知"))
                            f.write("来源: {}\n".format(detail_url))
                            f.write("分卷数: {}/{}\n".format(
                                len(all_downloaded), total_parts))
                            f.write("爬取时间: {}\n".format(
                                time.strftime("%Y-%m-%d %H:%M:%S")))
                            if newly_downloaded_nums:
                                f.write("备注: 增量追加{}个新卷\n".format(
                                    len(downloaded_parts)))
                            f.write("=" * 50 + "\n\n")

                        for part_label, content in downloaded_parts:
                            f.write("\n" + "=" * 50 + "\n")
                            f.write("--- 分卷: {} ---\n".format(part_label))
                            f.write("=" * 50 + "\n\n")
                            f.write(content)
                            f.write("\n")
                            total_bytes += len(content)

                    # 更新索引
                    self._update_book_entry(
                        book_id, book_name, author, total_parts,
                        all_downloaded, fpath, detail_url, final_chapter,
                        is_completed)

                    # ===== 第4步：章节级增量追加 =====
                    if need_chapter_update and stored_latest_chapter > 0:
                        self._log("   [id={}] 步骤4 章节增量 (第{}→{}章)...".format(
                            book_id, stored_latest_chapter, latest_chapter))
                        root_match = re.match(r'(https?://[^/]+)', root_url)
                        base_root = root_match.group(1) if root_match else root_url
                        new_chapters = self._fetch_directory_chapters(
                            base_root, book_id, known_max=stored_latest_chapter)

                        if new_chapters:
                            self._log("   [id={}] 发现{}个新章，逐章下载...".format(
                                book_id, len(new_chapters)))
                            try:
                                with open(fpath, "a", encoding="utf-8") as f:
                                    f.write("\n\n")
                                    f.write("=" * 50 + "\n")
                                    f.write("--- 增量更新: 新增 {} 章 (第{}~{}章) ---\n".format(
                                        len(new_chapters),
                                        new_chapters[0][0] if new_chapters[0][0] > 0 else "?",
                                        new_chapters[-1][0] if new_chapters[-1][0] > 0 else "?"))
                                    f.write("更新时间: {}\n".format(
                                        time.strftime("%Y-%m-%d %H:%M:%S")))
                                    f.write("=" * 50 + "\n\n")

                                    for ch_idx, (ch_num, ch_title, ch_url) in enumerate(new_chapters, 1):
                                        if not self.book_running:
                                            break
                                        label = "第{}章 {}".format(
                                            ch_num, ch_title) if ch_num > 0 else ch_title
                                        self._log("   [id={}/新章{}/{}] {}".format(
                                            book_id, ch_idx, len(new_chapters), label))
                                        ch_text = self._download_single_chapter(
                                            ch_url, book_id, label)
                                        if ch_text:
                                            f.write("\n## {}\n\n{}\n\n".format(
                                                label, ch_text))
                                            total_bytes += len(ch_text.encode('utf-8'))
                                            chap_append_count += 1
                                        else:
                                            self._log("   [id={}/新章{}/{}] 失败，跳过".format(
                                                book_id, ch_idx, len(new_chapters)))

                                        # 章节间延迟，避免连续请求触发反爬
                                        if ch_idx < len(new_chapters):
                                            time.sleep(random.uniform(1.5, 3.0))

                                max_new_ch = max(
                                    [c[0] for c in new_chapters if c[0] > 0],
                                    default=0)
                                final_chapter = max(final_chapter, max_new_ch)
                                self._update_book_entry(
                                    book_id, book_name, author, total_parts,
                                    all_downloaded, fpath, detail_url,
                                    final_chapter, is_completed)
                                self._log("   [id={}] 章节追加完毕: {}/{}章成功".format(
                                    book_id, chap_append_count, len(new_chapters)))

                            except Exception as e:
                                self._log("   [id={}] 章节追加失败: {}".format(
                                    book_id, e))
                        else:
                            self._log("   [id={}] 目录页未找到新章节".format(book_id))

                    elif need_chapter_update and not downloaded_parts:
                        # 无新卷但需章节更新（全部卷已有）
                        self._log("   [id={}] 仅章节增量 (第{}→{}章)...".format(
                            book_id, stored_latest_chapter, latest_chapter))
                        root_match = re.match(r'(https?://[^/]+)', root_url)
                        base_root = root_match.group(1) if root_match else root_url
                        use_fpath = existing_fpath or fpath

                        new_chapters = self._fetch_directory_chapters(
                            base_root, book_id, known_max=stored_latest_chapter)

                        if new_chapters and os.path.exists(use_fpath):
                            try:
                                with open(use_fpath, "a", encoding="utf-8") as f:
                                    f.write("\n\n")
                                    f.write("=" * 50 + "\n")
                                    f.write("--- 增量更新: 新增 {} 章 ---\n".format(
                                        len(new_chapters)))
                                    f.write("更新时间: {}\n".format(
                                        time.strftime("%Y-%m-%d %H:%M:%S")))
                                    f.write("=" * 50 + "\n\n")

                                    for ch_idx, (ch_num, ch_title, ch_url) in enumerate(new_chapters, 1):
                                        if not self.book_running:
                                            break
                                        label = "第{}章 {}".format(
                                            ch_num, ch_title) if ch_num > 0 else ch_title
                                        self._log("   [id={}/新章{}/{}] {}".format(
                                            book_id, ch_idx, len(new_chapters), label))
                                        ch_text = self._download_single_chapter(
                                            ch_url, book_id, label)
                                        if ch_text:
                                            f.write("\n## {}\n\n{}\n\n".format(
                                                label, ch_text))
                                            total_bytes += len(ch_text.encode('utf-8'))
                                            chap_append_count += 1

                                        # 章节间延迟
                                        if ch_idx < len(new_chapters):
                                            time.sleep(random.uniform(1.5, 3.0))

                                max_new_ch = max(
                                    [c[0] for c in new_chapters if c[0] > 0],
                                    default=0)
                                self._update_book_entry(
                                    book_id, book_name, author, total_parts,
                                    list(already_parts), use_fpath,
                                    detail_url,
                                    max(stored_latest_chapter, max_new_ch),
                                    is_completed)
                            except Exception as e:
                                self._log("   [id={}] 章节追加失败: {}".format(
                                    book_id, e))

                    # 单本完成日志
                    cost_sec = round(time.time() - id_start_time, 1)
                    mode_tag = ""
                    if downloaded_parts:
                        mode_tag += "[+{}卷]".format(len(downloaded_parts))
                    if chap_append_count > 0:
                        mode_tag += "[+{}章]".format(chap_append_count)
                    self._log("<< [id={}] 完成{} | {} | {}/{}卷 | {}字节 | {}s".format(
                        book_id, mode_tag, book_name,
                        len(all_downloaded), total_parts,
                        total_bytes, cost_sec))
                    self.book_stats["success"] += 1

                except Exception as e:
                    self._log("   [id={}] 写入失败 | 错误:{}".format(book_id, e))
                    self.book_stats["fail"] += 1
            else:
                cost_sec = round(time.time() - id_start_time, 1)
                self._log("<< [id={}] 所有操作均失败 | 耗时{}s".format(
                    book_id, cost_sec))
                self.book_stats["fail"] += 1

        # ===== 输出统计汇总 =====
        self._log("=" * 50)
        if not self.book_running:
            self._log("[用户中断] 小说更新被手动停止")
        else:
            self._log("小说更新完成！")
        skip_count = self.book_stats.get("skip", 0)
        stats_line = ("成功: {} | 无分卷: {} | 失败: {}"
                      .format(self.book_stats["success"],
                              self.book_stats["empty"],
                              self.book_stats["fail"]))
        if skip_count > 0:
            stats_line += " | 已是最新: {}".format(skip_count)
        stats_line += " | 处理总数: {}/{}".format(self._book_processed, total)
        self._log(stats_line)
        self._log("=" * 50)

        # 恢复UI状态
        self.root.after(0, lambda: [
            self.btn_book_start.config(state=tk.NORMAL),
            self.btn_book_update.config(state=tk.NORMAL),
            self.btn_book_stop.config(state=tk.DISABLED),
            self.book_status.set("就绪"),
        ])

    def _book_fullsite_worker(self, root_url, book_ids, book_index):
        """全站爬取第二阶段工作线程：逐本处理采集到的书籍ID列表。

        对每本书自动判断：
        - 新书（索引中无记录）→ 全量下载所有分卷
        - 已记录 + 连载中 → 增量更新（跳过已有卷 + 章节追加）
        - 已记录 + 已完结 → 跳过
        """
        total = len(book_ids)
        self._log("开始全站爬取第二阶段：共{}本书 | 策略: 新书全下 / 已知增量 / 完结跳过".format(total))

        for idx, book_id in enumerate(book_ids):
            if not self.book_running:
                self._log("[全站] 用户中断")
                break

            # 更新进度
            self._book_processed = idx + 1
            pct = self._book_processed * 100 // total if total > 0 else 0
            self.root.after(0, self._update_book_progress, pct,
                            self._book_processed, total)

            id_start_time = time.time()
            is_known = str(book_id) in book_index

            # 日志标签：已知/新书/完结
            if is_known:
                entry = book_index[str(book_id)]
                stored_name = entry.get("book_name", "未知")
                status = "✓完结" if entry.get("is_completed") else "连载"
                tag = "[已知/{}]".format(status)
            else:
                stored_name = "?"
                tag = "[NEW]"

            self._log(">> [id={}/第{}/{}] {} 开始 | {}".format(
                book_id, idx + 1, total, tag, stored_name))

            # ===== 第1步：访问详情页 =====
            detail_url = root_url.rstrip("/") + "/" + str(book_id) + "/txt.html"
            if is_known and book_index[str(book_id)].get("detail_url"):
                detail_url = book_index[str(book_id)]["detail_url"]

            book_name, author, parts_info, latest_chapter, is_completed = self._fetch_book_meta(
                detail_url, book_id)

            if book_name is None:
                self.book_stats["fail"] += 1
                cost_sec = round(time.time() - id_start_time, 1)
                self._log("<< [id={}] 失败 | 无法访问详情页 | 耗时{}s".format(
                    book_id, cost_sec))
                continue

            if not parts_info:
                self.book_stats["empty"] += 1
                self._log("   [id={}] 无分卷链接，跳过".format(book_id))
                continue

            total_parts = len(parts_info)

            # ===== 判断是否跳过（已完结）=====
            if is_completed or (is_known and book_index[str(book_id)].get("is_completed")):
                already_parts = set()
                existing_fpath = None
                if is_known:
                    e = book_index[str(book_id)]
                    already_parts = set(e.get("downloaded_parts", []))
                    existing_fpath = e.get("file_path")
                self._update_book_entry(
                    book_id, book_name, author, total_parts,
                    list(already_parts), existing_fpath, detail_url,
                    latest_chapter or 0, is_completed=True)
                self.book_stats["skip"] += 1
                cost_sec = round(time.time() - id_start_time, 1)
                self._log("<< [id={}] 已完结，跳过 | {} | {}s".format(
                    book_id, book_name, cost_sec))
                continue

            # ===== 准备已下载信息（已知书才有）=====
            already_parts = set()
            existing_fpath = None
            stored_latest_chapter = 0
            if is_known:
                entry = book_index[str(book_id)]
                already_parts = set(entry.get("downloaded_parts", []))
                existing_fpath = entry.get("file_path")
                stored_latest_chapter = entry.get("latest_chapter_num", 0) or 0

            new_part_count = total_parts - len(already_parts)
            need_chapter_update = False
            if latest_chapter and latest_chapter > stored_latest_chapter:
                need_chapter_update = True
                self._log("   [id={}] ⚠ 新章节! 第{}章 > 本地第{}章 (+{})".format(
                    book_id, latest_chapter, stored_latest_chapter,
                    latest_chapter - stored_latest_chapter))

            # 已知书 + 无新内容 → 秒跳
            should_skip = (is_known and new_part_count == 0
                           and not need_chapter_update)
            if should_skip:
                self._update_book_entry(
                    book_id, book_name, author, total_parts,
                    list(already_parts), existing_fpath, detail_url,
                    latest_chapter, is_completed)
                self.book_stats["skip"] += 1
                cost_sec = round(time.time() - id_start_time, 1)
                self._log("<< [id={}] 已是最新，跳过 | {}/{}卷 | {}s".format(
                    book_id, book_name, len(already_parts), total_parts, cost_sec))
                continue

            # ===== 第2步：下载分卷 =====
            dl_label = "全量" if not is_known else "增量(+{}卷)".format(new_part_count)
            self._log("   [id={}] {} | 共{}卷 需下{}卷...".format(
                book_id, dl_label, total_parts,
                new_part_count if is_known else total_parts))

            downloaded_parts = []
            newly_downloaded_nums = []
            for part_idx, (part_label, part_url) in enumerate(parts_info, 1):
                if not self.book_running:
                    break
                if part_idx in already_parts:
                    continue
                content = self._download_txt_with_retry(part_url, book_id, part_idx)
                if content is not None:
                    downloaded_parts.append((part_label, content))
                    newly_downloaded_nums.append(part_idx)

                # 分卷间延迟
                if part_idx < len(parts_info):
                    time.sleep(random.uniform(1.0, 2.0))

            if not self.book_running and not downloaded_parts:
                continue

            # ===== 第3步：写入文件 + 第4步：章节增量 =====
            all_downloaded = sorted(already_parts | set(newly_downloaded_nums))
            final_chapter = latest_chapter or stored_latest_chapter
            total_bytes = 0
            chap_append_count = 0

            if downloaded_parts or (need_chapter_update and existing_fpath):
                try:
                    day_name = time.strftime("%Y%m%d")
                    book_dir = os.path.join(".", "output", "book", day_name)
                    os.makedirs(book_dir, exist_ok=True)

                    if (existing_fpath and os.path.exists(existing_fpath)):
                        fpath = existing_fpath
                    else:
                        fname = "{}-{}-{}.txt".format(
                            book_id, book_name, author or "未知")
                        fname = re.sub(r'[\\/:*?"<>|]', '_', fname)
                        fpath = os.path.join(book_dir, fname)

                    write_mode = "a" if (
                        is_known and existing_fpath
                        and os.path.exists(existing_fpath)) else "w"

                    with open(fpath, write_mode, encoding="utf-8") as f:
                        if write_mode == "w":
                            f.write("=" * 50 + "\n")
                            f.write("书名: {}\n".format(book_name))
                            f.write("作者: {}\n".format(author or "未知"))
                            f.write("来源: {}\n".format(detail_url))
                            f.write("分卷数: {}/{}\n".format(
                                len(all_downloaded), total_parts))
                            f.write("爬取时间: {}\n".format(
                                time.strftime("%Y-%m-%d %H:%M:%S")))
                            if is_known and newly_downloaded_nums:
                                f.write("备注: 全站增量追加{}个新卷\n".format(
                                    len(downloaded_parts)))
                            f.write("=" * 50 + "\n\n")

                        for plabel, pcontent in downloaded_parts:
                            f.write("\n" + "=" * 50 + "\n")
                            f.write("--- 分卷: {} ---\n".format(plabel))
                            f.write("=" * 50 + "\n\n")
                            f.write(pcontent)
                            f.write("\n")
                            total_bytes += len(pcontent)

                    self._update_book_entry(
                        book_id, book_name, author, total_parts,
                        all_downloaded, fpath, detail_url,
                        final_chapter, is_completed)

                    # ===== 章节级增量 =====
                    if need_chapter_update and stored_latest_chapter > 0:
                        self._log("   [id={}] 章节增量 (第{}→{}章)...".format(
                            book_id, stored_latest_chapter, latest_chapter))
                        root_m = re.match(r'(https?://[^/]+)', root_url)
                        base_root = root_m.group(1) if root_m else root_url
                        new_chaps = self._fetch_directory_chapters(
                            base_root, book_id, known_max=stored_latest_chapter)
                        if new_chaps:
                            try:
                                with open(fpath, "a", encoding="utf-8") as f:
                                    f.write("\n\n")
                                    f.write("=" * 50 + "\n")
                                    f.write("--- 全站增量: 新增 {} 章 ---\n".format(
                                        len(new_chaps)))
                                    f.write("更新时间: {}\n".format(
                                        time.strftime("%Y-%m-%d %H:%M:%S")))
                                    f.write("=" * 50 + "\n\n")

                                    for ci, (cn, ct, cu) in enumerate(new_chaps, 1):
                                        if not self.book_running:
                                            break
                                        clabel = "第{}章 {}".format(
                                            cn, ct) if cn > 0 else ct
                                        ch_text = self._download_single_chapter(
                                            cu, book_id, clabel)
                                        if ch_text:
                                            f.write("\n## {}\n\n{}\n\n".format(
                                                clabel, ch_text))
                                            total_bytes += len(ch_text.encode('utf-8'))
                                            chap_append_count += 1

                                        # 章节间延迟
                                        if ci < len(new_chaps):
                                            time.sleep(random.uniform(1.5, 3.0))

                                mx = max([c[0] for c in new_chaps if c[0] > 0],
                                         default=0)
                                final_chapter = max(final_chapter, mx)
                                self._update_book_entry(
                                    book_id, book_name, author, total_parts,
                                    all_downloaded, fpath, detail_url,
                                    final_chapter, is_completed)
                            except Exception as e:
                                self._log("   [id={}] 章节追加失败: {}".format(
                                    book_id, e))

                    cost_sec = round(time.time() - id_start_time, 1)
                    mtag = ""
                    if not is_known:
                        mtag = "[NEW]"
                    elif downloaded_parts:
                        mtag = "[+{}卷]".format(len(downloaded_parts))
                    if chap_append_count > 0:
                        mtag += "[+{}章]".format(chap_append_count)
                    self._log("<< [id={}] 完成{} | {} | {}/{}卷 | {}字节 | {}s".format(
                        book_id, mtag, book_name, len(all_downloaded),
                        total_parts, total_bytes, cost_sec))
                    self.book_stats["success"] += 1

                except Exception as e:
                    self._log("   [id={}] 写入失败: {}".format(book_id, e))
                    self.book_stats["fail"] += 1
            else:
                cost_sec = round(time.time() - id_start_time, 1)
                self._log("<< [id={}] 所有操作均失败 | {}s".format(book_id, cost_sec))
                self.book_stats["fail"] += 1

            # 书籍间延迟：避免连续请求触发反爬
            if idx + 1 < total and self.book_running:
                time.sleep(random.uniform(2.0, 4.0))

        # ===== 汇总统计 =====
        self._log("=" * 50)
        if not self.book_running:
            self._log("[用户中断] 全站爬取被停止")
        else:
            self._log("全站爬取完成！")
        sk = self.book_stats.get("skip", 0)
        sl = ("成功: {} | 无分卷: {} | 失败: {}"
              .format(self.book_stats["success"],
                      self.book_stats["empty"],
                      self.book_stats["fail"]))
        if sk > 0:
            sl += " | 跳过(含完结): {}".format(sk)
        sl += " | 总计: {}/{}".format(self._book_processed, total)
        self._log(sl)
        self._log("=" * 50)

        self.root.after(0, lambda: [
            self.btn_book_start.config(state=tk.NORMAL),
            self.btn_book_fullsite.config(state=tk.NORMAL),
            self.btn_book_update.config(state=tk.NORMAL),
            self.btn_book_stop.config(state=tk.DISABLED),
            self.book_status.set("就绪"),
        ])

    def _stop_book(self):
        self.book_running = False
        self.book_status.set("正在停止...")

    # --------------------------------------------------------
    #  小说索引管理（增量更新）
    # --------------------------------------------------------

    def _load_book_index(self):
        """加载 book_index.json，返回 dict 或空字典"""
        try:
            if os.path.exists(BOOK_INDEX_FILE):
                with open(BOOK_INDEX_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            self._log("[索引] 加载失败: {}".format(e))
        return {}

    def _save_book_index(self, index):
        """保存索引到文件"""
        try:
            os.makedirs(os.path.dirname(BOOK_INDEX_FILE), exist_ok=True)
            with open(BOOK_INDEX_FILE, "w", encoding="utf-8") as f:
                json.dump(index, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self._log("[索引] 保存失败: {}".format(e))

    def _update_book_entry(self, book_id, book_name, author, total_parts,
                           downloaded_part_nums, file_path, detail_url,
                           latest_chapter_num=None, is_completed=None,
                           downloaded_part_labels=None):
        """更新/新增一本书的索引条目"""
        index = self._load_book_index()
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        entry = {
            "id": book_id,
            "name": book_name,
            "author": author or "未知",
            "file_path": file_path,
            "total_parts": total_parts,
            "downloaded_parts": sorted(downloaded_part_nums),
            "last_update": now_str,
            "detail_url": detail_url,
        }
        if downloaded_part_labels is not None:
            entry["downloaded_labels"] = downloaded_part_labels
        if latest_chapter_num is not None:
            entry["latest_chapter_num"] = latest_chapter_num
        if is_completed is not None:
            entry["is_completed"] = is_completed
        # 保留旧值（如果新值为空则不覆盖）
        old_entry = index.get(str(book_id), {})
        for k, v in entry.items():
            if v is not None:
                old_entry[k] = v
        index[str(book_id)] = old_entry
        self._save_book_index(index)

    def _book_worker(self, root_url, start_page, page_num, update_mode=False,
                      skip_existing=True):
        """小说爬取工作线程

        参数:
            root_url: 网站根URL
            start_page: 起始ID
            page_num: 结束ID（不包含）
            update_mode: True=增量更新模式
            skip_existing: True=跳过已有卷号(默认), False=强制重新下载所有卷
                          仅在 update_mode=True 时生效
        """
        total = page_num - start_page
        mode_label = "【增量更新】" if update_mode else "【全量下载】"
        self._log("开始小说爬取：{} id={}-{}，共{}个 {}".format(root_url, start_page, page_num, total, mode_label))
        self._log("目标网站: {} | 起止ID: {}~{} | 总计: {}个ID".format(root_url, start_page, page_num - 1, total))
        if update_mode:
            self._log("策略: 检索本地索引 → 对比站上分卷 → 只下载缺失/新增卷 → 追加合并")
        else:
            self._log("策略: 遍历ID范围 | 本地已有记录的书自动走更新流程(跳过已下卷+章节增量) | 新书正常全量下载")

        # 始终加载本地索引（全量模式下用于检测"这本书是否已爬过"）
        book_index = self._load_book_index()

        i = start_page
        while i < page_num:
            if not self.book_running:
                self._log("[小说] 用户中断爬取")
                break

            # 更新进度（id粒度）
            self._book_processed += 1
            done = self._book_processed
            pct = done * 100 // total if total > 0 else 0
            self.root.after(0, self._update_book_progress, pct, done, total)

            id_start_time = time.time()
            self._log(">> [id={}] 开始处理".format(i))

            # ===== 第1步：访问详情页获取元数据 =====
            detail_url = root_url.rstrip("/") + "/" + str(i) + "/txt.html"
            self._log("   [id={}] 步骤1/3 获取详情页: {}".format(i, detail_url))

            book_name, author, parts_info, latest_chapter, is_completed = self._fetch_book_meta(detail_url, i)

            if book_name is None:
                # 详情页请求失败或页面无效
                self.book_stats["fail"] += 1
                cost_sec = round(time.time() - id_start_time, 1)
                self._log("<< [id={}] 失败 | 无法获取详情页 | 耗时{}秒".format(i, cost_sec))
                i += 1
                continue

            if not parts_info:
                self._log("   [id={}] 详情页无下载分卷链接，跳过此ID".format(i))
                self.book_stats["empty"] += 1
                i += 1
                continue

            total_parts = len(parts_info)
            self._log("   [id={}] 元数据获取成功 | 书名:{} | 作者:{} | 共{}个分卷".format(
                i, book_name, author or "未知", total_parts))

            # ===== 检查本地索引：这本书是否已爬取过？ =====
            already_parts = set()  # 已下载的卷号（需要跳过的）
            existing_fpath = None
            is_known_book = str(i) in book_index

            if is_known_book:
                entry = book_index[str(i)]
                # 全量模式下已有记录的书 → 自动走更新流程（等同 skip_existing=True）
                already_parts = set(entry.get("downloaded_parts", []))
                existing_fpath = entry.get("file_path")
                self._log("   [id={}] [本地已记录] {} | 已下{}/{}卷 | 第{}章 | {}".format(
                    i, book_name, len(already_parts), total_parts,
                    entry.get("latest_chapter_num", 0) or "?",
                    "✓完结" if entry.get("is_completed") else "连载"))

            # 已完结的直接跳过（全量/增量统一处理）
            if is_completed or (is_known_book and book_index[str(i)].get("is_completed")):
                self._update_book_entry(i, book_name, author, total_parts,
                                        list(already_parts), existing_fpath,
                                        detail_url, latest_chapter or 0, is_completed=True)
                self.book_stats["skip"] += 1
                cost_sec = round(time.time() - id_start_time, 1)
                mode_tag = "[全量]" if not update_mode else ""
                self._log("<< [id={}] {}已完结，跳过 | {} | 耗时{}s".format(
                    i, mode_tag, book_name, cost_sec))
                i += 1
                continue

            # ===== 第2步：逐卷下载TXT直链（跳过已下载的卷） =====
            new_part_count = total_parts - len(already_parts)

            # 检查章节级更新（即使分卷没变，章节可能变了）— 对所有已记录的书都生效
            need_chapter_update = False
            stored_latest_chapter = 0
            if is_known_book:
                stored_entry = book_index[str(i)]
                stored_latest_chapter = stored_entry.get("latest_chapter_num", 0) or 0
                if latest_chapter and latest_chapter > stored_latest_chapter:
                    need_chapter_update = True
                    self._log("   [id={}] [章节级] ⚠ 检测到新章节! 站上第{}章 > 本地第{}章 (+{}章)".format(
                        i, latest_chapter, stored_latest_chapter,
                        latest_chapter - stored_latest_chapter))

            # 已记录且无新分卷的书 → 不在此处跳过，交由后续章节增量步骤通过目录爬取做真实检测
            # 原因：详情页的 latest_chapter_num（正则取max第X章）未必准确反映TXT实际内容更新情况
            #       若此处跳过，章节增量代码永远不会执行，导致新内容漏下载
            if is_known_book and new_part_count == 0:
                # 无新分卷 → 跳过分卷下载循环（全部已下），直接进入章节增量检测
                self._log("   [id={}] [检测] 全{}卷已下载，跳过分卷下载，进入章节增量校验...".format(
                    i, total_parts))
                downloaded_parts = []
                newly_downloaded_nums = []

            _chapter_only_mode = (is_known_book and new_part_count == 0)

            if _chapter_only_mode:
                dl_label = "目录校验(无新卷)"
            else:
                dl_label = "增量({}新卷)".format(new_part_count) if is_known_book else ("增量下载({}新卷)".format(new_part_count) if update_mode else "全量下载")
            self._log("   [id={}] 步骤2/3 {} (共{}卷, 需下载{}卷)...".format(
                i, dl_label, total_parts, new_part_count if (is_known_book or update_mode) and not _chapter_only_mode else total_parts))

            downloaded_parts = []  # [(part_label, content), ...]
            newly_downloaded_nums = []  # 本次新下成功的卷号（用于更新索引）

            if not _chapter_only_mode:
                for part_idx, (part_label, part_url) in enumerate(parts_info, 1):
                    if not self.book_running:
                        self._log("   [id={}] 中断下载，已下载{}/{}卷".format(i, part_idx - 1, total_parts))
                        break

                    # 增量模式下跳过已下载的卷
                    if update_mode and part_idx in already_parts:
                        continue

                    self._log("   [id={}/卷{}/{}] 下载: {}".format(i, part_idx, total_parts, part_url))

                    content = self._download_txt_with_retry(part_url, i, part_idx)
                    if content is not None:
                        downloaded_parts.append((part_label, content))
                        newly_downloaded_nums.append(part_idx)
                        self._log("   [id={}/卷{}/{}] 下载成功 | 标签:{} | 大小:{}字节".format(
                            i, part_idx, total_parts, part_label, len(content)))
                    else:
                        self._log("   [id={}/卷{}/{}] 下载失败（已重试3次），跳过该卷".format(
                            i, part_idx, total_parts))

                    # 分卷间延迟（TXT直链也是连续请求）
                    if part_idx < len(parts_info):
                        time.sleep(random.uniform(1.0, 2.0))
            # end: if not _chapter_only_mode (跳过分卷下载循环)

            if not self.book_running and not downloaded_parts:
                # 已记录且无新分卷的书需要继续执行章节增量检测（不在此处短路）
                if not (is_known_book and new_part_count == 0):
                    i += 1
                    continue

            # ===== 第3步：合并为整本文件 =====
            if downloaded_parts:
                day_name = time.strftime("%Y%m%d")
                book_dir = os.path.join(".", "output", "book", day_name)
                os.makedirs(book_dir, exist_ok=True)

                fname = "{}-{}-{}.txt".format(i, book_name, author or "未知")
                fname = re.sub(r'[\\/:*?"<>|]', '_', fname)
                fpath = os.path.join(book_dir, fname)

                try:
                    total_bytes = 0
                    # 已记录的书(全量自动增量/增量模式) → 追加；全新书 → 覆盖写入
                    is_append = (is_known_book or update_mode) and existing_fpath and os.path.exists(existing_fpath)
                    write_mode = "a" if is_append else "w"

                    with open(fpath, write_mode, encoding="utf-8") as f:
                        if write_mode == "w":
                            # 全新模式：写入元信息头
                            f.write("=" * 50 + "\n")
                            f.write("书名: {}\n".format(book_name))
                            f.write("作者: {}\n".format(author or "未知"))
                            f.write("来源: {}\n".format(detail_url))
                            f.write("分卷数: {}/{}\n".format(
                                len(downloaded_parts) + len(already_parts), total_parts))
                            f.write("爬取时间: {}\n".format(time.strftime("%Y-%m-%d %H:%M:%S")))
                            if (update_mode or is_known_book) and already_parts:
                                f.write("备注: 增量追加{}个新卷\n".format(len(downloaded_parts)))
                            f.write("=" * 50 + "\n\n")

                        for part_label, content in downloaded_parts:
                            f.write("\n" + "=" * 50 + "\n")
                            f.write("--- 分卷: {} ---\n".format(part_label))
                            f.write("=" * 50 + "\n\n")
                            f.write(content)
                            f.write("\n")
                            total_bytes += len(content)

                    # 更新索引：合并已有的 + 新下的卷号
                    all_downloaded = sorted(already_parts | set(newly_downloaded_nums))
                    final_chapter = latest_chapter or stored_latest_chapter
                    self._update_book_entry(i, book_name, author, total_parts,
                                            all_downloaded, fpath, detail_url,
                                            final_chapter, is_completed)

                    # ===== 第4步：章节级增量追加（如有新章节） =====
                    chap_append_count = 0
                    if need_chapter_update and stored_latest_chapter > 0:
                        self._log("   [id={}] 步骤4 章节级增量 (本地第{}章 → 最新第{}章)...".format(
                            i, stored_latest_chapter, latest_chapter))
                        root_match = re.match(r'(https?://[^/]+)', root_url)
                        base_root = root_match.group(1) if root_match else root_url
                        new_chapters = self._fetch_directory_chapters(
                            base_root, i, known_max=stored_latest_chapter)

                        if new_chapters:
                            self._log("   [id={}] [章节] 发现{}个新章，开始逐章下载...".format(
                                i, len(new_chapters)))
                            try:
                                with open(fpath, "a", encoding="utf-8") as f:
                                    f.write("\n\n")
                                    f.write("=" * 50 + "\n")
                                    f.write("--- 增量更新: 新增 {} 章 (第{}~{}章) ---\n".format(
                                        len(new_chapters),
                                        new_chapters[0][0] if new_chapters[0][0] > 0 else "?",
                                        new_chapters[-1][0] if new_chapters[-1][0] > 0 else "?"))
                                    f.write("更新时间: {}\n".format(time.strftime("%Y-%m-%d %H:%M:%S")))
                                    f.write("=" * 50 + "\n\n")

                                    for ch_idx, (ch_num, ch_title, ch_url) in enumerate(new_chapters, 1):
                                        if not self.book_running:
                                            break
                                        label = "第{}章 {}".format(ch_num, ch_title) if ch_num > 0 else ch_title
                                        self._log("   [id={}/新章{}/{}] {}".format(
                                            i, ch_idx, len(new_chapters), label))
                                        ch_text = self._download_single_chapter(ch_url, i, label)
                                        if ch_text:
                                            f.write("\n## {}\n\n{}\n\n".format(label, ch_text))
                                            total_bytes += len(ch_text.encode('utf-8'))
                                            chap_append_count += 1
                                        else:
                                            self._log("   [id={}/新章{}/{}] 下载失败，跳过".format(
                                                i, ch_idx, len(new_chapters)))

                                        # 章节间延迟
                                        if ch_idx < len(new_chapters):
                                            time.sleep(random.uniform(1.5, 3.0))

                                # 更新最终章节号
                                max_new_ch = max([c[0] for c in new_chapters if c[0] > 0], default=0)
                                final_chapter = max(final_chapter, max_new_ch)
                                self._update_book_entry(i, book_name, author, total_parts,
                                                        all_downloaded, fpath, detail_url,
                                                        final_chapter, is_completed)
                                self._log("   [id={}] [章节] 追加完毕: {}/{}章成功".format(
                                    i, chap_append_count, len(new_chapters)))

                            except Exception as e:
                                self._log("   [id={}] [章节] 追加失败: {}".format(i, e))
                        else:
                            self._log("   [id={}] [章节] 目录页未找到新章节（可能目录页结构变化）".format(i))

                    cost_sec = round(time.time() - id_start_time, 1)
                    mode_tag = "[增量+{}卷]".format(len(downloaded_parts)) if (update_mode or is_known_book) else ""
                    if chap_append_count > 0:
                        mode_tag += "[+{}章]".format(chap_append_count)
                    self._log("<< [id={}] 完成{} | 书名:{} | 成功{}/{}卷 | 整本大小:{}字节 | 文件:{} | 耗时{}秒".format(
                        i, mode_tag, book_name, len(all_downloaded), total_parts,
                        total_bytes, fpath, cost_sec))
                    self.book_stats["success"] += 1

                except Exception as e:
                    self._log("   [id={}] 合并写入失败 | 路径:{} | 错误:{}".format(i, fpath, e))
                    self.book_stats["fail"] += 1
            elif need_chapter_update or (is_known_book and new_part_count == 0):
                # ===== 分卷全部已有，做章节级增量追加 =====
                # 触发条件：
                #   1) need_chapter_update=True：详情页章节数 > 本地记录（常规增量）
                #   2) 已记录书+无新分卷：详情页章节数可能不准（如同源正则），仍需通过目录爬取做真实检测
                chap_mode = "目录校验" if not need_chapter_update else "章节增量"
                self._log("   [id={}] 步骤4 [{}] (本地第{}章→站上第{}章)...".format(
                    i, chap_mode, stored_latest_chapter, latest_chapter or "?"))
                root_match = re.match(r'(https?://[^/]+)', root_url)
                base_root = root_match.group(1) if root_match else root_url
                use_fpath = existing_fpath or fpath  # 优先用已有文件路径

                new_chapters = self._fetch_directory_chapters(
                    base_root, i, known_max=stored_latest_chapter)
                chap_append_count = 0
                total_bytes = 0

                if new_chapters and os.path.exists(use_fpath):
                    try:
                        with open(use_fpath, "a", encoding="utf-8") as f:
                            f.write("\n\n")
                            f.write("=" * 50 + "\n")
                            f.write("--- 增量更新: 新增 {} 章 ---\n".format(len(new_chapters)))
                            f.write("更新时间: {}\n".format(time.strftime("%Y-%m-%d %H:%M:%S")))
                            f.write("=" * 50 + "\n\n")

                            for ch_idx, (ch_num, ch_title, ch_url) in enumerate(new_chapters, 1):
                                if not self.book_running:
                                    break
                                label = "第{}章 {}".format(ch_num, ch_title) if ch_num > 0 else ch_title
                                self._log("   [id={}/新章{}/{}] {}".format(
                                    i, ch_idx, len(new_chapters), label))
                                ch_text = self._download_single_chapter(ch_url, i, label)
                                if ch_text:
                                    f.write("\n## {}\n\n{}\n\n".format(label, ch_text))
                                    total_bytes += len(ch_text.encode('utf-8'))
                                    chap_append_count += 1

                                # 章节间延迟
                                if ch_idx < len(new_chapters):
                                    time.sleep(random.uniform(1.5, 3.0))

                        max_new_ch = max([c[0] for c in new_chapters if c[0] > 0], default=0)
                        self._update_book_entry(i, book_name, author, total_parts,
                                                list(already_parts), use_fpath,
                                                detail_url, max(stored_latest_chapter, max_new_ch),
                                                is_completed)
                    except Exception as e:
                        self._log("   [id={}] [章节] 追加失败: {}".format(i, e))

                cost_sec = round(time.time() - id_start_time, 1)
                tag = "[+{}章]".format(chap_append_count) if chap_append_count > 0 else ""
                self._log("<< [id={}] 完成{} | 书名:{} | 新增{}章 | 文件:{} | 耗时{}秒".format(
                    i, tag, book_name, chap_append_count, use_fpath, cost_sec))
                if chap_append_count > 0:
                    self.book_stats["success"] += 1
                else:
                    self.book_stats["skip"] += 1
            else:
                cost_sec = round(time.time() - id_start_time, 1)
                self._log("<< [id={}] 所有分卷均下载失败 | 耗时{}秒".format(i, cost_sec))
                self.book_stats["fail"] += 1

            i += 1

            # ID间延迟：避免连续请求详情页触发反爬
            if i < page_num and self.book_running:
                time.sleep(random.uniform(2.0, 4.0))

        # 输出统计
        self._log("=" * 50)
        if not self.book_running:
            self._log("[用户中断] 小说爬取被手动停止")
        else:
            self._log("小说{}完成！".format("更新" if update_mode else "爬取"))
        skip_count = self.book_stats.get("skip", 0)
        stats_line = "成功: {} | 空内容(无分卷): {} | 请求失败: {}".format(
            self.book_stats["success"],
            self.book_stats["empty"],
            self.book_stats["fail"])
        if skip_count > 0:
            stats_line += " | 已是最新(跳过): {}".format(skip_count)
        stats_line += " | 处理总数: {}/{}".format(self._book_processed, total)
        self._log(stats_line)
        self._log("=" * 50)

    def _fetch_book_meta(self, detail_url, book_id):
        """
        访问详情页 /{id}/txt.html，提取：
        - 书名、作者
        - 所有 TXT 分卷的下载链接列表
        - 最新章节号（用于增量更新检测）
        - 是否已完结（True=完结 False=连载中 None=未知）
        返回: (book_name, author, [(part_label, download_url), ...], latest_chapter_num, is_completed)
               如果详情页不可用返回 (None, None, [], None, None)
        """
        html = ""
        for retry in range(3):
            try:
                html = get_url_txt_without_cookie(detail_url)
                break
            except AntiCaptchaRedirect as e:
                cooldown = min((retry + 1) * 20, 60)
                _cleanup_stale_connections()
                if retry < 2:
                    self._log("   [id={}] 详情页被反爬拦截(第{}/3次): [{}] | 冷却{}s...".format(
                        book_id, retry + 1, _classify_error(e)[0], cooldown))
                    time.sleep(cooldown)
                else:
                    self._log("   [id={}] 详情页被反爬拦截(3次): URL: {}".format(
                        book_id, detail_url))
                    return None, None, [], None, None
            except Exception as e:
                cat, is_conn = _classify_error(e)
                if is_conn:
                    _cleanup_stale_connections()
                wait = max(3, (_get_cooldown_seconds() if is_conn else 0) + 2)
                if retry < 2:
                    self._log("   [id={}] 详情页请求失败(第{}/3次): {} [{}] | {}s后重试...".format(
                        book_id, retry + 1, e, cat, wait))
                    time.sleep(wait)
                else:
                    self._log("   [id={}] 详情页请求彻底失败(3次重试用尽): [{}] | URL: {}".format(
                        book_id, cat, detail_url))
                    return None, None, [], None, None

        if not html or len(html) < 200:
            self._log("   [id={}] 详情页内容异常({}字节)，可能是无效ID或404".format(book_id, len(html) if html else 0))
            return None, None, [], None, None

        # 提取书名：从 <a href="#dir">书名</a> 或 <h1> 标签中提取
        book_name = ""
        name_match = re.search(r'href=["\']#dir["\'][^>]*>([^<]+)</a>', html)
        if name_match:
            book_name = name_match.group(1).strip()
        if not book_name:
            h1_match = re.search(r'<h1[^>]*>([^<]+)', html)
            if h1_match:
                book_name = h1_match.group(1).strip()

        # 提取作者
        author = ""
        # 模式: 作者：xxx 或 作者: xxx
        author_match = re.search(r'作者[：:]\s*<a[^>]*>([^<]+)</a>', html)
        if author_match:
            author = author_match.group(1).strip()
        if not author:
            author_match2 = re.search(r'作者[：:]\s*([^<\n]+)', html)
            if author_match2:
                author = author_match2.group(1).strip()

        # 提取所有 TXT 分卷下载链接
        # 模式: <a href="/txt/?id=X&p=Y">书名(章节范围).txt</a>
        parts_info = []
        txt_links = re.findall(r'<a\s+href=["\'](/txt/\?id=\d+&p=\d+)["\'][^>]*>([^<]+\.txt)</a>', html, re.I)

        # 从详情页提取根域名（用于拼接绝对路径）
        # 例如 https://www.sudugu.org/2/txt.html → https://www.sudugu.org
        root_match = re.match(r'(https?://[^/]+)', detail_url)
        base_root = root_match.group(1) if root_match else detail_url

        for link_href, link_text in txt_links:
            # 补全URL（相对路径转绝对路径）
            if link_href.startswith("/"):
                # /txt/?id=... 是站内绝对路径，拼上域名根即可
                full_url = base_root + link_href
            else:
                full_url = link_href
            # 清理标签中的HTML实体
            label = re.sub(r'<[^>]+>', '', link_text).strip()
            parts_info.append((label, full_url))

        # 提取当前最新章节号（用于增量更新检测）
        latest_chapter = self._extract_latest_chapter_num(html, book_id)

        # 检测是否完结：精确匹配 <title> 标签和书名区域，避免页面其他位置（推荐/广告/侧栏）的"完结"干扰
        title_match = re.search(r'<title>([^<]+)</title>', html, re.I)
        page_title = title_match.group(1) if title_match else ""
        # 完结小说标题特征："全集已完结"、"已完结xxx"
        is_completed = bool(re.search(r'完结', page_title))
        if is_completed:
            self._log("   [id={}] [状态] 已完结 ✓ | 标题:{}".format(
                book_id, page_title[:60]))
        else:
            self._log("   [id={}] [状态] 连载中 | 标题:{}".format(
                book_id, page_title[:60]))

        return book_name or "未知书名", author, parts_info, latest_chapter, is_completed

    # --------------------------------------------------------
    #  章节级操作（用于增量更新的细粒度控制）
    # --------------------------------------------------------

    def _extract_latest_chapter_num(self, html, book_id):
        """从详情页HTML中提取最新章节号。
        模式匹配: '第XXXX章 ...' 或 '最新章节'区域中的最大章节号
        返回: int（章节号）或 None
        """
        # 方案1: 从"最新更新"区域提取第一个章节号
        # 页面结构中通常有: 第1449章 xxx → 链接
        matches = re.findall(r'第(\d+)章', html)
        if matches:
            # 取最大的那个（排除公告等非正文章节的干扰）
            nums = [int(m) for m in matches if int(m) > 0]
            if nums:
                latest = max(nums)
                self._log("   [id={}] [章节检测] 详情页解析到{}个章节标记，最新: 第{}章".format(
                    book_id, len(matches), latest))
                return latest
        return None

    def _fetch_directory_chapters(self, base_url, book_id, known_max=0):
        """爬取目录页，获取全部或新增的章节信息。

        参数:
            base_url: 域名根 (如 https://www.sudugu.org)
            book_id: 书籍ID
            known_max: 已知最大章节号，只返回 > 此值的章节（用于增量）

        返回:
            [(chapter_num, chapter_title, full_url), ...]
            chapter_num 可能为0（非正文章节如公告）
        """
        dir_url = base_url.rstrip("/") + "/" + str(book_id) + "/"
        root_match = re.match(r'(https?://[^/]+)', base_url)
        base_root = root_match.group(1) if root_match else base_url

        all_chapters = []
        page_idx = 1
        max_pages = 50  # 安全上限（大长篇可能有很多页目录）

        while page_idx <= max_pages:
            if not self.book_running:
                break
            # 目录页进度日志（每5页或第1页汇报一次，大长篇可能要翻很多页）
            if page_idx == 1 or page_idx % 5 == 0:
                mode_tag = "增量(>{0}章)".format(known_max) if known_max > 0 else "全量"
                self._log("   [id={}] 目录页 {}/{} [{}]...".format(
                    book_id, page_idx, max_pages, mode_tag))
            if page_idx == 1:
                page_url = dir_url.rstrip("/") + "/"
            else:
                page_url = dir_url.rstrip("/") + "/p-{}.html".format(page_idx)

            try:
                page_html = get_url_txt_without_cookie(page_url)
            except AntiCaptchaRedirect as e:
                self._log("   [id={}] 目录页第{}页被反爬拦截: [{}] | 冷却30s...".format(
                    book_id, page_idx, _classify_error(e)[0]))
                _cleanup_stale_connections()
                time.sleep(30)
                continue  # 不 break，冷却后重试当前页
            except Exception as e:
                cat, is_conn = _classify_error(e)
                if is_conn:
                    _cleanup_stale_connections()
                self._log("   [id={}] 目录页第{}页获取失败: [{}] | {}".format(
                    book_id, page_idx, cat, e))
                break

            if not page_html or len(page_html) < 100:
                break

            # 提取章节链接: <a href="/2/3114270.html">第1449章 标题</a>
            # 注意：URL中的数字是文章ID，不是章节号
            chap_links = re.findall(
                r'<a\s+href=["\'](/\d+/(\d+)\.html)["\'][^>]*>([^<]*(?:第(\d+)章)[^<]*)</a>',
                page_html, re.I,
            )

            if not chap_links:
                # 尝试更宽泛的模式（不含"第X章"约束）
                chap_links2 = re.findall(
                    r'<a\s+href=["\'](/\d+/(\d+)\.html)["\'][^>]*>(第(\d+)章[^<]*)</a>',
                    page_html, re.I,
                )
                if not chap_links2:
                    break  # 没有更多章节了
                chap_links = chap_links2

            page_found_any = False
            for href, article_id, raw_title, ch_num in chap_links:
                ch_num_int = int(ch_num) if ch_num and ch_num.isdigit() else 0
                title = re.sub(r'<[^>]+>', '', raw_title).strip()

                # 增量模式：跳过已知章节
                if known_max > 0 and 0 < ch_num_int <= known_max:
                    continue

                full_url = base_root + href if href.startswith("/") else href
                all_chapters.append((ch_num_int, title, full_url))
                page_found_any = True

            if not page_found_any and page_idx > 1:
                break  # 这一页没有新章节了，停止翻页

            # 检查是否有下一页
            if not re.search(r'p-{}\.html'.format(page_idx + 1), page_html) and \
               not re.search(r'下一[页页]', page_html) and page_idx >= 2:
                break

            page_idx += 1

            # 目录翻页间延迟（目录页也是连续请求）
            time.sleep(random.uniform(1.0, 2.0))

        # 按章节号排序（确保顺序正确）
        all_chapters.sort(key=lambda x: x[0] if x[0] > 0 else 999999)

        return all_chapters

    def _download_single_chapter(self, chap_url, book_id, chap_label):
        """下载单章内容并提取纯文本正文。

        参数:
            chap_url: 单章页面URL
            book_id: 书籍ID（用于日志）
            chap_label: 章节标签（用于日志显示）

        返回: str（纯文本）或 None
        """
        for retry in range(3):
            try:
                html = get_url_txt_without_cookie(chap_url)
                # 提取正文内容 — 通常在一个特定class/div中
                # 常见模式：<div id="content"> 或 <div class="content">
                text = ""
                # 尝试多种常见正文容器模式
                content_patterns = [
                    r'<div[^>]*id=["\']content["\'][^>]*>(.*?)</div>',
                    r'<div[^>]*class=["\'][^"\']*content[^"\']*["\'][^>]*>(.*?)</div>',
                    r'<div[^>]*class=["\'][^"\']*chapter-content[^"\']*["\'][^>]*>(.*?)</div>',
                    r'<div[^>]*class=["\'][^"\']*read-content[^"\']*["\'][^>]*>(.*?)</div>',
                ]
                for pat in content_patterns:
                    m = re.search(pat, html, re.DOTALL | re.I)
                    if m:
                        text = m.group(1)
                        break

                if not text:
                    # 兜底：取 <body> 内主要内容区（去掉导航、推荐等）
                    body_match = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL | re.I)
                    if body_match:
                        raw = body_match.group(1)
                        # 去掉 script/style/nav/header/footer
                        raw = re.sub(r'<script[^>]*>.*?</script>', '', raw, flags=re.DOTALL | re.I)
                        raw = re.sub(r'<style[^>]*>.*?</style>', '', raw, flags=re.DOTALL | re.I)
                        raw = re.sub(r'<nav[^>]*>.*?</nav>', '', raw, flags=re.DOTALL | re.I)
                        raw = re.sub(r'<header[^>]*>.*?</header>', '', raw, flags=re.DOTALL | re.I)
                        raw = re.sub(r'<footer[^>]*>.*?</footer>', '', raw, flags=re.DOTALL | re.I)
                        text = raw

                # 清理HTML标签
                text = re.sub(r'<br\s*/?\s*>', '\n', text)
                text = re.sub(r'</p>', '\n', text)
                text = re.sub(r'<[^>]+>', '', text)
                # 清理多余空白
                lines = [l.strip() for l in text.split('\n') if l.strip()]
                text = '\n'.join(lines)

                if len(text) < 50:
                    if retry < 2:
                        time.sleep(1)
                        continue
                    return None

                return text

            except AntiCaptchaRedirect as e:
                # 反爬重定向 → 长冷却 + 不频繁重试（重试也没用）
                cooldown = min((retry + 1) * 20, 60)  # 第1次20s, 第2次40s, 上限60s
                _cleanup_stale_connections()
                if retry < 2:
                    self._log("   [id={}/{}] 单章被反爬拦截(第{}/3次): [{}] | 冷却{}s...".format(
                        book_id, chap_label, retry + 1,
                        _classify_error(e)[0], cooldown))
                    time.sleep(cooldown)
                else:
                    self._log("   [id={}/{}] 单章被反爬拦截(3次): URL: {}".format(
                        book_id, chap_label, chap_url))
                return None  # 反爬不继续重试浪费资源

            except Exception as e:
                cat, is_conn = _classify_error(e)
                if is_conn:
                    _cleanup_stale_connections()
                # 连接级错误用较长冷却，普通错误用短冷却
                wait = max(3, (_get_cooldown_seconds() if is_conn else 0) + 2)
                if retry < 2:
                    tag = " | [SSL风暴+{}s]".format(_get_cooldown_seconds()) if is_conn and _ssl_error_streak > 2 else ""
                    self._log("   [id={}/{}] 单章下载失败(第{}/3次): [{}] | {}{} | {}s后重试...".format(
                        book_id, chap_label, retry + 1, cat, e, tag, wait))
                    time.sleep(wait)
                else:
                    self._log("   [id={}/{}] 单章下载失败: [{}] | URL: {}".format(
                        book_id, chap_label, cat, chap_url))
                    return None
        return None

    def _download_txt_with_retry(self, url, book_id, part_idx):
        """
        下载单个TXT分卷，带3次重试机制。
        使用流式下载(stream=True)避免大文件IncompleteRead。
        返回: 文本内容(str) 或 None(全部失败)
        """
        content = None
        req_start = time.time()
        # 进度汇报状态（用list以便在嵌套函数中修改）
        last_progress_report = [req_start]

        def _on_progress(downloaded_bytes, elapsed_sec):
            """流式下载进度回调，每约10秒打印一次"""
            now = time.time()
            if now - last_progress_report[0] >= 10:
                speed = downloaded_bytes / elapsed_sec / 1024 if elapsed_sec > 0 else 0
                self._log("   [id={}/卷{}] 下载中... {}KB | {}KB/s | 已耗时{}s".format(
                    book_id, part_idx,
                    round(downloaded_bytes / 1024),
                    round(speed, 1),
                    round(elapsed_sec)))
                last_progress_report[0] = now

        for retry in range(3):
            try:
                content = get_url_txt_streaming(url, progress_callback=_on_progress)
                req_cost = round((time.time() - req_start) * 1000)
                text_len = len(content) if content else 0
                # 最终完成汇总（含速度）
                speed = text_len / (req_cost / 1000) / 1024 if req_cost > 0 else 0
                self._log("   [id={}/卷{}] 下载{} | {}KB | {}KB/s | 总耗时{}ms".format(
                    book_id, part_idx,
                    "成功" if retry == 0 else "重试{}成功".format(retry + 1),
                    round(text_len / 1024),
                    round(speed, 1),
                    req_cost))
                # 0字节视为无效响应，当失败处理（可能URL错误或被拦截）
                if text_len == 0:
                    self._log("   [id={}/卷{}] 响应为空(0字节)，视为失败 | URL: {}".format(
                        book_id, part_idx, url))
                    content = None
                    if retry < 2:
                        time.sleep(2)
                        req_start = time.time()
                        continue
                return content
            except AntiCaptchaRedirect as e:
                # 反爬重定向 → 长冷却（流式下载被拦截说明问题严重）
                req_cost = round((time.time() - req_start) * 1000)
                cooldown = min((retry + 1) * 25, 60)  # 第1次25s, 第2次50s, 上限60s
                _cleanup_stale_connections()
                if retry < 2:
                    self._log("   [id={}/卷{}] 被反爬拦截(第{}/3次): [{}] | 冷却{}s...".format(
                        book_id, part_idx, retry + 1,
                        _classify_error(e)[0], cooldown))
                    time.sleep(cooldown)
                    req_start = time.time()
                else:
                    self._log("   [id={}/卷{}] 被反爬拦截(3次): URL: {} | [{}]".format(
                        book_id, part_idx, url, _classify_error(e)[0]))
            except Exception as e:
                req_cost = round((time.time() - req_start) * 1000)
                cat, is_conn = _classify_error(e)

                if is_conn:
                    _cleanup_stale_connections()

                cooldown = _get_cooldown_seconds() if is_conn else 0
                wait = max(2, cooldown)

                if retry < 2:
                    tag = ""
                    if cooldown > 0:
                        tag = " | [SSL风暴#{} +{}s冷却]".format(
                            _ssl_error_streak, cooldown)
                    self._log("   [id={}/卷{}] 下载失败(第{}/3次) | 耗时{}ms | {} | {}{} | {}s后重试...".format(
                        book_id, part_idx, retry + 1, req_cost,
                        cat, e, tag, wait))
                    time.sleep(wait)
                    req_start = time.time()  # 重置计时
                else:
                    tag = " | [SSL风暴#{}]".format(_ssl_error_streak) if _ssl_error_streak > 2 else ""
                    self._log("   [id={}/卷{}] 下载彻底失败(3次重试用尽) | 耗时{}ms | URL: {} | {} | {}{}".format(
                        book_id, part_idx, req_cost, url, cat, e, tag))
        return None

        self.root.after(0, self._book_done)

    def _update_book_progress(self, pct, done, total):
        """在主线程更新小说爬取进度条"""
        self.book_progress["value"] = pct
        self.book_progress_label.set("{}/{} ({}%)".format(done, total, pct))

    def _book_done(self):
        self.btn_book_start.config(state=tk.NORMAL)
        self.btn_book_update.config(state=tk.NORMAL)
        self.btn_book_stop.config(state=tk.DISABLED)
        self.book_status.set("就绪")
        self.book_progress["value"] = 100

    # --------------------------------------------------------
    #  日志系统
    # --------------------------------------------------------
    def _on_close(self):
        """窗口关闭时保存所有输入框的值到配置文件"""
        try:
            self.config["base_url"] = self.base_url.get()
            self.config["crawl_begin"] = self.crawl_begin.get()
            self.config["crawl_end"] = self.crawl_end.get()
            self.config["crawl_threads"] = self.crawl_threads.get()
            self.config["cookie_path"] = self.cookie_path.get()
            self.config["db_115_path"] = self.db_115_path.get()
            self.config["file_path"] = self.file_path.get()
            self.config["small_file_mb"] = self.small_file_mb.get()
            self.config["file_dst_path"] = self.file_dst_path.get()
            self.config["low_grade_val"] = self.low_grade_val.get()
            self.config["keyword_val"] = self.keyword_val.get()
            self.config["collect_grade"] = self.collect_grade.get()
            self.config["collect_dst_path"] = self.collect_dst_path.get()
            self.config["book_root"] = self.book_root.get()
            self.config["book_start"] = self.book_start.get()
            self.config["book_end"] = self.book_end.get()
            self.config["theme"] = self.current_theme  # 保存主题偏好
            # 保存窗口大小和位置
            try:
                self.config["window_geometry"] = self.root.geometry()
            except Exception:
                pass
            save_config(self.config)
        except Exception:
            pass
        self.root.destroy()

    def _log(self, msg):
        """线程安全的日志写入"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_queue.put("[{}] {}".format(timestamp, msg))
        # 同时写文件日志
        try:
            day_name = time.strftime("%Y-%m-%d")
            os.makedirs("./output/log", exist_ok=True)
            with open("./output/log/{}.txt".format(day_name), "a", encoding="utf-8") as f:
                full_time = time.strftime("%Y-%m-%d %H:%M:%S")
                f.write("[{}] {}\n".format(full_time, msg))
        except Exception:
            pass

    def _poll_log(self):
        """主线程定时从队列取日志刷新到 Text"""
        while True:
            try:
                msg = self.log_queue.get_nowait()
            except queue.Empty:
                break
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, msg + "\n")
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)
        self.root.after(200, self._poll_log)

    def _clear_log(self):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)

    # --------------------------------------------------------
    #  启动
    # --------------------------------------------------------
    def run(self):
        self.root.mainloop()


# ============================================================
#  入口
# ============================================================
if __name__ == "__main__":
    app = SyaApp()
    app.run()
