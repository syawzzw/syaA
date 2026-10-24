# -*- coding: utf-8 -*-
"""B站视频下载核心模块 —— 获取视频流地址、下载、合并"""

import os
import re
import sys
import json
import time
import asyncio
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, List, Dict, Callable
from dataclasses import dataclass, field

try:
    import aiohttp
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "aiohttp", "-q"])
    import aiohttp

from .wbi import get_wbi_signer, HEADERS

logger = logging.getLogger("bilibili_dl")

# ── DASH 视频流质量选择 ─────────────────────────────────
# 按优先级排列
VIDEO_QUALITY_ORDER = [125, 126, 127, 128, 120, 116, 112, 80, 64, 32, 16]
AUDIO_QUALITY_ORDER = [30251, 30250, 30280, 30232, 30216, 30206]


@dataclass
class VideoStream:
    """视频流信息"""
    url: str
    quality_id: int = 0
    quality_name: str = ""
    width: int = 0
    height: int = 0
    codec: str = ""
    size: int = 0
    mime_type: str = ""


@dataclass
class DownloadResult:
    """下载结果"""
    success: bool
    bvid: str = ""
    title: str = ""
    filepath: str = ""
    error: str = ""
    duration: float = 0
    file_size: int = 0


@dataclass
class DownloadConfig:
    """下载配置"""
    save_dir: str = ""
    download_video: bool = True
    download_audio: bool = True
    download_cover: bool = True
    download_subtitles: bool = False
    preferred_quality: str = "1080p"  # 360p/480p/720p/1080p/4k
    folder_style: bool = True        # 按视频建子目录
    concurrent: int = 3              # 并发下载数
    max_videos: int = 0              # 最大下载数 (0=不限)
    cookie: str = ""                 # SESSDATA cookie
    proxy: str = ""                  # 代理地址


# ════════════════════════════════════════════════════════
#  清理文件名
# ════════════════════════════════════════════════════════
def clean_filename(name: str, max_len: int = 100) -> str:
    """清理文件名，移除非法字符"""
    # 替换 Windows 非法字符
    name = re.sub(r'[\\/:*?"<>|\r\n]', '_', name)
    # 移除首尾空格和点
    name = name.strip(' .')
    # 截断长度
    if len(name) > max_len:
        name = name[:max_len].rstrip(' .')
    return name or "未命名"


# ════════════════════════════════════════════════════════
#  获取视频流地址
# ════════════════════════════════════════════════════════
async def get_video_streams(
    bvid: str,
    cid: int,
    cookie: str = "",
    quality: int = 125,  # 125=1080P+
) -> dict:
    """
    获取视频的 DASH 流地址

    返回:
        {
            "video": [VideoStream, ...],
            "audio": [VideoStream, ...],
            "dash": { ... }  # 原始 DASH 数据
        }
    """
    signer = await get_wbi_signer()
    session = signer._get_session()

    params = {
        "bvid": bvid,
        "cid": cid,
        "qn": quality,
        "fnver": 0,
        "fnval": 16,  # 请求 DASH 格式
        "fourk": 1,   # 允许4K
    }
    params = await signer.sign(params)

    headers = dict(HEADERS)
    if cookie:
        headers["Cookie"] = cookie

    async with session.get(
        "https://api.bilibili.com/x/player/wbi/playurl",
        params=params,
        headers=headers,
    ) as resp:
        data = await resp.json()

    if data.get("code") != 0:
        raise RuntimeError(f"获取视频流失败: {data.get('message', '')}")

    dash_data = data["data"].get("dash", {})
    if not dash_data:
        # 可能是 FLV 格式或无权限
        raise RuntimeError("无法获取 DASH 流数据，可能需要登录或视频已下架")

    videos = []
    for v in dash_data.get("video", []):
        videos.append(VideoStream(
            url=v["baseUrl"] or v.get("backupUrl", [""])[0],
            quality_id=v["id"],
            quality_name=v.get("description", ""),
            width=v.get("width", 0),
            height=v.get("height", 0),
            codec=v.get("codecid", 0),
            size=v.get("bandwidth", 0),
            mime_type=v.get("mimeType", ""),
        ))

    audios = []
    for a in dash_data.get("audio", []):
        audios.append(VideoStream(
            url=a["baseUrl"] or a.get("backupUrl", [""])[0],
            quality_id=a["id"],
            quality_name=a.get("description", ""),
            codec=a.get("codecid", 0),
            size=a.get("bandwidth", 0),
            mime_type=a.get("mimeType", ""),
        ))

    return {"video": videos, "audio": audios, "dash": dash_data}


def select_best_video(videos: List[VideoStream]) -> Optional[VideoStream]:
    """按质量优先级选择最佳视频流"""
    for qid in VIDEO_QUALITY_ORDER:
        for v in videos:
            if v.quality_id == qid:
                return v
    return videos[0] if videos else None


def select_best_audio(audios: List[VideoStream]) -> Optional[VideoStream]:
    """按质量优先级选择最佳音频流"""
    for qid in AUDIO_QUALITY_ORDER:
        for a in audios:
            if a.quality_id == qid:
                return a
    return audios[0] if audios else None


def quality_name_to_id(name: str) -> int:
    """质量名称转 quality id"""
    mapping = {
        "4k": 125, "2160p": 125,
        "1080p+": 125, "1080p高码率": 125,
        "1080p": 116,
        "720p": 112,
        "480p": 80,
        "360p": 64,
    }
    return mapping.get(name.lower(), 116)


# ════════════════════════════════════════════════════════
#  下载文件
# ════════════════════════════════════════════════════════
async def download_file(
    url: str,
    filepath: str,
    cookie: str = "",
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> bool:
    """
    下载文件（支持进度回调）

    参数:
        url:              下载链接
        filepath:         保存路径
        cookie:           Cookie
        progress_callback: 进度回调 fn(downloaded_bytes, total_bytes)

    返回:
        是否成功
    """
    headers = dict(HEADERS)
    headers["Referer"] = "https://www.bilibili.com"
    if cookie:
        headers["Cookie"] = cookie

    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"HTTP {resp.status}")

                total = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                last_report = 0

                Path(filepath).parent.mkdir(parents=True, exist_ok=True)

                with open(filepath, "wb") as f:
                    async for chunk in resp.content.iter_chunked(1024 * 64):
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback:
                            progress_callback(downloaded, total)
                        # 每 2MB 上报一次字节进度
                        if downloaded - last_report >= 2 * 1024 * 1024:
                            last_report = downloaded
                            progress_callback(downloaded, total)

        if progress_callback:
            progress_callback(downloaded, total)
        return True
    except Exception as e:
        logger.error(f"下载失败: {url[:80]}... -> {e}")
        # 删除不完整文件
        if os.path.exists(filepath):
            os.remove(filepath)
        return False


async def download_with_multipart(
    url: str,
    filepath: str,
    cookie: str = "",
    progress_callback: Optional[Callable[[int, int], None]] = None,
    parts: int = 4,
) -> bool:
    """
    分片并发下载（大文件加速），HEAD 失败时回退普通下载
    """
    headers = dict(HEADERS)
    headers["Referer"] = "https://www.bilibili.com"
    if cookie:
        headers["Cookie"] = cookie

    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            # 先获取文件大小
            try:
                async with session.head(url) as resp:
                    if resp.status == 200:
                        total = int(resp.headers.get("Content-Length", 0))
                    else:
                        total = 0
            except Exception:
                total = 0

            if total <= 1024:
                return await download_file(url, filepath, cookie, progress_callback)

            Path(filepath).parent.mkdir(parents=True, exist_ok=True)

            # 共享下载量计数
            total_downloaded = 0
            last_report = [0.0]
            report_lock = asyncio.Lock()

            # 分片下载
            part_size = total // parts
            temp_paths = []

            async def download_part(idx: int):
                nonlocal total_downloaded
                start = idx * part_size
                end = start + part_size - 1 if idx < parts - 1 else total - 1
                temp_path = f"{filepath}.part{idx}"
                temp_paths.append(temp_path)

                range_headers = {**headers, "Range": f"bytes={start}-{end}"}

                async with session.get(url, headers=range_headers) as resp:
                    if resp.status not in (200, 206):
                        return False

                    part_downloaded = 0
                    with open(temp_path, "wb") as f:
                        async for chunk in resp.content.iter_chunked(1024 * 64):
                            f.write(chunk)
                            part_downloaded += len(chunk)
                            total_downloaded += len(chunk)

                    # 上报进度（节流：每 0.3 秒）
                    if progress_callback:
                        async with report_lock:
                            now = time.time()
                            if now - last_report[0] >= 0.3:
                                last_report[0] = now
                                progress_callback(total_downloaded, total)

                return True

            results = await asyncio.gather(*[download_part(i) for i in range(parts)])

            if not all(results):
                for tp in temp_paths:
                    if os.path.exists(tp):
                        os.remove(tp)
                return False

            # 合并分片
            with open(filepath, "wb") as f:
                for tp in temp_paths:
                    with open(tp, "rb") as pf:
                        f.write(pf.read())
                    os.remove(tp)

            if progress_callback:
                progress_callback(total, total)

            return True

    except Exception as e:
        logger.error(f"分片下载失败: {e}")
        return False




# ════════════════════════════════════════════════════════
#  合并音视频 (ffmpeg)
# ════════════════════════════════════════════════════════
def find_ffmpeg() -> Optional[str]:
    """查找系统中的 ffmpeg"""
    # 检查 PATH
    for name in ["ffmpeg", "ffmpeg.exe"]:
        path = shutil.which(name)
        if path:
            return path

    # 检查常见路径
    common_paths = [
        r"C:\software\ffmpeg-master-latest-win64-gpl-shared\ffmpeg-master-latest-win64-gpl-shared\bin\ffmpeg.exe",
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"D:\ffmpeg\bin\ffmpeg.exe",
        os.path.expanduser(r"~\ffmpeg\bin\ffmpeg.exe"),
    ]
    for p in common_paths:
        if os.path.isfile(p):
            return p

    # 兜底：使用 imageio-ffmpeg（moviepy 依赖）自带的 ffmpeg
    try:
        import imageio_ffmpeg  # type: ignore
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.isfile(exe):
            return exe
    except Exception:
        pass

    return None


async def merge_av(
    video_path: str,
    audio_path: str,
    output_path: str,
) -> bool:
    """用 ffmpeg 合并音视频"""
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        logger.warning("未找到 ffmpeg，将保留分离的音视频文件")
        return False

    # shared 版本的 ffmpeg 需要 DLL，把 bin 目录加到 PATH
    ffmpeg_dir = os.path.dirname(ffmpeg)
    env = os.environ.copy()
    env["PATH"] = ffmpeg_dir + os.pathsep + env.get("PATH", "")

    cmd = [
        ffmpeg, "-y",
        "-i", video_path,
        "-i", audio_path,
        "-c:v", "copy",
        "-c:a", "copy",
        "-movflags", "+faststart",
        output_path,
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=300
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            logger.error("ffmpeg 合并超时")
            return False

        if proc.returncode != 0:
            logger.error(f"ffmpeg 合并失败: {stderr.decode(errors='replace')[-200:]}")
            return False
        return True
    except Exception as e:
        logger.error(f"ffmpeg 合并失败: {e}")
        return False


# ════════════════════════════════════════════════════════
#  下载封面
# ════════════════════════════════════════════════════════
async def download_cover(pic_url: str, save_path: str) -> bool:
    """下载视频封面图"""
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(pic_url) as resp:
                if resp.status != 200:
                    return False
                Path(save_path).parent.mkdir(parents=True, exist_ok=True)
                with open(save_path, "wb") as f:
                    f.write(await resp.read())
        return True
    except Exception as e:
        logger.error(f"下载封面失败: {e}")
        return False


# ════════════════════════════════════════════════════════
#  核心下载流程
# ════════════════════════════════════════════════════════
async def download_single_video(
    bvid: str,
    config: DownloadConfig,
    log_fn: Callable[[str], None] = None,
    progress_fn: Callable[[int, int], None] = None,
) -> DownloadResult:
    """
    下载单个视频（含所有分P）

    参数:
        bvid:       BV 号
        config:     下载配置
        log_fn:     日志回调
        progress_fn: 进度回调 fn(current_index, total_videos)

    返回:
        DownloadResult
    """
    if log_fn is None:
        log_fn = lambda x: print(x)
    if progress_fn is None:
        progress_fn = lambda a, b: None

    def log(msg: str):
        log_fn(msg)
        logger.info(msg)

    try:
        # 1. 获取视频详情
        log(f"[INFO] 获取视频详情: {bvid}")
        detail = await get_video_detail(bvid)

        title = detail["title"]
        clean_title = clean_filename(title)
        author = detail["owner"]["name"]
        pages = detail["pages"]
        pic_url = detail["pic"]

        if not pic_url.startswith("http"):
            pic_url = "https:" + pic_url

        log(f"[USER_INFO] {author}")
        log(f"[INFO] 视频: {title} ({len(pages)}P)")

        # 2. 准备目录
        if config.folder_style:
            base_dir = Path(config.save_dir) / clean_filename(f"{author} - {clean_title}")
        else:
            base_dir = Path(config.save_dir)

        base_dir.mkdir(parents=True, exist_ok=True)

        # 3. 下载封面
        if config.download_cover:
            cover_path = base_dir / "cover.jpg"
            if not cover_path.exists():
                await download_cover(pic_url, str(cover_path))

        # 4. 下载每个分P
        results = []
        for idx, page in enumerate(pages):
            cid = page["cid"]
            page_title = clean_filename(page["part"]) or f"P{idx+1}"

            log(f"[PROGRESS] ITEM|{idx+1}/{len(pages)}|下载分P: {page_title}")

            result = await _download_single_page(
                bvid=bvid,
                cid=cid,
                page_title=page_title,
                page_index=idx + 1,
                total_pages=len(pages),
                base_dir=base_dir,
                clean_title=clean_title,
                config=config,
                log_fn=log,
            )
            results.append(result)

        # 汇总结果
        success = all(r.success for r in results)
        filepaths = [r.filepath for r in results if r.filepath]
        total_size = sum(r.file_size for r in results)

        return DownloadResult(
            success=success,
            bvid=bvid,
            title=title,
            filepath=filepaths[0] if len(filepaths) == 1 else str(base_dir),
            duration=detail["duration"],
            file_size=total_size,
        )

    except Exception as e:
        log(f"[ERROR] {e}")
        return DownloadResult(
            success=False, bvid=bvid,
            title="", error=str(e),
        )


async def _download_single_page(
    bvid: str,
    cid: int,
    page_title: str,
    page_index: int,
    total_pages: int,
    base_dir: Path,
    clean_title: str,
    config: DownloadConfig,
    log_fn: Callable[[str], None],
) -> DownloadResult:
    """下载单个分P"""
    def log(msg: str):
        log_fn(msg)

    # 字节级进度上报
    _dl_start = [0.0]
    _dl_last = [0.0]
    def dl_progress(downloaded: int, total: int, desc: str = ""):
        now = time.time()
        if now - _dl_last[0] < 0.3 and downloaded < total:
            return
        _dl_last[0] = now
        if _dl_start[0] == 0:
            _dl_start[0] = now
        elapsed = now - _dl_start[0]
        speed = downloaded / elapsed / 1024 / 1024 if elapsed > 0.01 else 0
        pct = downloaded / total * 100 if total > 0 else 0
        d_mb = downloaded / 1024 / 1024
        t_mb = total / 1024 / 1024
        if speed > 0 and downloaded < total:
            eta = (total - downloaded) / (speed * 1024 * 1024)
            if eta >= 60:
                eta_str = f"{int(eta // 60)}m{int(eta % 60)}s"
            else:
                eta_str = f"{int(eta)}s"
        else:
            eta_str = ""
        eta_part = f" 剩余{eta_str}" if eta_str else ""
        log(f"[PROGRESS] DL_BYTES|{downloaded}|{total}|{desc} {d_mb:.1f}/{t_mb:.1f}MB {pct:.0f}% {speed:.1f}MB/s{eta_part}")

    try:
        # 获取视频流
        qn = quality_name_to_id(config.preferred_quality)
        streams = await get_video_streams(bvid, cid, cookie=config.cookie, quality=qn)

        video = select_best_video(streams["video"])
        audio = select_best_audio(streams["audio"]) if config.download_audio else None

        if not video:
            raise RuntimeError("未找到可用的视频流")

        log(f"  [PROGRESS] STEP|画质选择|{video.quality_name} ({video.width}x{video.height})")

        # 确定输出文件名
        if total_pages > 1:
            output_name = f"{clean_title}_{page_title}"
        else:
            output_name = clean_title

        # 临时文件
        tmp_dir = Path(tempfile.mkdtemp())
        video_tmp = tmp_dir / "video.m4s"
        audio_tmp = tmp_dir / "audio.m4s"

        has_video = False
        has_audio = False

        # 下载视频
        if config.download_video and video:
            log(f"  [PROGRESS] STEP|下载视频流|{video.quality_name}")
            _dl_start[0] = 0
            _dl_last[0] = 0
            has_video = await download_with_multipart(
                video.url, str(video_tmp), config.cookie,
                progress_callback=lambda d, t: dl_progress(d, t, "视频"),
            )

        # 下载音频
        if config.download_audio and audio:
            log(f"  [PROGRESS] STEP|下载音频流|{audio.quality_name}")
            _dl_start[0] = 0
            _dl_last[0] = 0
            has_audio = await download_with_multipart(
                audio.url, str(audio_tmp), config.cookie,
                progress_callback=lambda d, t: dl_progress(d, t, "音频"),
            )

        output_path = base_dir / f"{output_name}.mp4"

        if output_path.exists():
            log(f"  [INFO] 已存在，跳过: {output_name}.mp4")
            _cleanup(tmp_dir, video_tmp, audio_tmp)
            return DownloadResult(
                success=True, bvid=bvid,
                filepath=str(output_path),
                file_size=output_path.stat().st_size,
            )

        if has_video and has_audio:
            # 合并音视频
            log(f"  [PROGRESS] STEP|合并音视频|ffmpeg")
            merged = await merge_av(str(video_tmp), str(audio_tmp), str(output_path))
            if not merged:
                # ffmpeg 不可用，只保存视频
                shutil.copy2(str(video_tmp), str(base_dir / f"{output_name}_video.mp4"))
                log(f"  [WARN] 未找到 ffmpeg，已保存为分离文件")
        elif has_video:
            shutil.copy2(str(video_tmp), str(output_path))
        elif has_audio:
            shutil.copy2(str(audio_tmp), str(base_dir / f"{output_name}.m4s"))

        _cleanup(tmp_dir, video_tmp, audio_tmp)

        file_size = output_path.stat().st_size if output_path.exists() else 0
        log(f"  [INFO] 完成: {output_name}.mp4 ({file_size / 1024 / 1024:.1f} MB)")

        return DownloadResult(
            success=True, bvid=bvid,
            filepath=str(output_path),
            file_size=file_size,
        )

    except Exception as e:
        log_fn(f"  [ERROR] 分P {page_title} 下载失败: {e}")
        return DownloadResult(
            success=False, bvid=bvid,
            error=str(e),
        )


def _cleanup(tmp_dir: Path, *files: Path):
    """清理临时文件"""
    try:
        for f in files:
            if f.exists():
                f.unlink()
        if tmp_dir.exists():
            tmp_dir.rmdir()
    except Exception:
        pass


async def get_video_detail(bvid: str) -> dict:
    """获取视频详情（从 api 模块调用）"""
    from .api import get_video_detail as _get_detail
    return await _get_detail(bvid)


# ════════════════════════════════════════════════════════
#  批量下载
# ════════════════════════════════════════════════════════
async def download_user_videos(
    mid: int,
    config: DownloadConfig,
    log_fn: Callable[[str], None] = None,
    progress_fn: Optional[Callable[[int, int], None]] = None,
) -> List[DownloadResult]:
    """
    下载用户的所有视频

    参数:
        mid:        用户 UID
        config:     下载配置
        log_fn:     日志回调
        progress_fn: 进度回调 fn(current, total)

    返回:
        下载结果列表
    """
    if log_fn is None:
        log_fn = lambda x: print(x)

    def log(msg: str):
        log_fn(msg)

    # 1. 获取用户信息
    log("[PROGRESS] STEP|获取用户信息|")
    from .api import get_user_info
    user = await get_user_info(mid)
    log(f"[USER_INFO] {user.get('name', '')}")
    log(f"[INFO] 用户: {user.get('name', '')} (UID: {mid})")
    log(f"[INFO] 粉丝: {user.get('follower', 0)} 作品: {user.get('video_count', 0)}")

    # 2. 获取视频列表
    log("[PROGRESS] STEP|获取视频列表|")
    from .api import get_all_videos
    videos = await get_all_videos(
        mid,
        order="pubdate",
        max_count=config.max_videos,
        progress_callback=lambda c, t: log(
            f"[PROGRESS] ITEM_TOTAL|{t}|已获取 {c} 个视频信息"
        ),
    )

    total = len(videos)
    if total == 0:
        log("[INFO] 该用户暂无投稿视频")
        return []

    log(f"[INFO] 共找到 {total} 个视频")
    if config.max_videos > 0:
        videos = videos[:config.max_videos]

    # 3. 逐个下载
    results = []
    success_count = 0
    fail_count = 0
    skip_count = 0

    for idx, video_info in enumerate(videos):
        bvid = video_info.get("bvid", "")
        title = video_info.get("title", "")
        log(f"[PROGRESS] ITEM|{idx+1}/{len(videos)}|{title}")

        if not bvid:
            log(f"  [WARN] 跳过无效视频")
            skip_count += 1
            continue

        # 检查是否已下载（通过目录判断）
        clean_title = clean_filename(title)
        author_name = user.get("name", "")
        if config.folder_style:
            check_dir = Path(config.save_dir) / clean_filename(f"{author_name} - {clean_title}")
        else:
            check_dir = Path(config.save_dir) / f"{clean_title}.mp4"

        if check_dir.exists():
            log(f"  [INFO] 已存在，跳过: {title}")
            skip_count += 1
            if progress_fn:
                progress_fn(idx + 1, len(videos))
            continue

        result = await download_single_video(
            bvid=bvid,
            config=config,
            log_fn=log,
        )

        results.append(result)
        if result.success:
            success_count += 1
        else:
            fail_count += 1

        if progress_fn:
            progress_fn(idx + 1, len(videos))

    # 4. 输出统计
    log("")
    log("=" * 50)
    log(f"[INFO] 下载完成！成功: {success_count} 失败: {fail_count} 跳过: {skip_count}")
    log("=" * 50)

    return results
