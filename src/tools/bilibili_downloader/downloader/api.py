# -*- coding: utf-8 -*-
"""B站用户空间 API —— 获取用户视频列表"""

from typing import Optional
from .wbi import get_wbi_signer, HEADERS


async def get_user_info(mid: int) -> dict:
    """获取用户基本信息"""
    signer = await get_wbi_signer()
    params = await signer.sign({"mid": mid})
    session = signer._get_session()

    async with session.get(
        "https://api.bilibili.com/x/space/wbi/acc/info",
        params=params,
    ) as resp:
        data = await resp.json()

    if data.get("code") != 0:
        raise RuntimeError(f"获取用户信息失败: {data.get('message', '')}")
    return data["data"]


async def get_video_list(
    mid: int,
    page: int = 1,
    page_size: int = 30,
    order: str = "pubdate",
    keyword: str = "",
    wbi: bool = True,
) -> dict:
    """
    获取用户投稿视频列表（分页）

    参数:
        mid:       用户 UID
        page:      页码 (从1开始)
        page_size: 每页数量 (默认30，最大50)
        order:     排序方式 pubdate/click/stow
        keyword:   关键词筛选
        wbi:       是否使用 WBI 签名

    返回:
        {
            "code": 0,
            "message": "0",
            "data": {
                "page": { "pn": 1, "ps": 30, "count": 100 },
                "list": { "vlist": [...] }
            }
        }
    """
    signer = await get_wbi_signer()
    params = {
        "mid": mid,
        "ps": min(page_size, 50),
        "pn": page,
        "order": order,
    }
    if keyword:
        params["keyword"] = keyword

    if wbi:
        params = await signer.sign(params)

    session = signer._get_session()

    # 尝试 WBI 签名接口
    url = "https://api.bilibili.com/x/space/wbi/arc/search" if wbi else \
          "https://api.bilibili.com/x/space/arc/search"

    async with session.get(url, params=params) as resp:
        data = await resp.json()

    # 如果 WBI 失败（-412），回退到无签名接口
    if data.get("code") == -412 and wbi:
        return await get_video_list(mid, page, page_size, order, keyword, wbi=False)

    if data.get("code") != 0:
        raise RuntimeError(f"获取视频列表失败: {data.get('message', '')}")

    return data


async def get_all_videos(
    mid: int,
    order: str = "pubdate",
    max_count: int = 0,
    page_size: int = 30,
    progress_callback=None,
) -> list:
    """
    获取用户所有视频（自动翻页）

    参数:
        mid:              用户 UID
        order:            排序方式
        max_count:        最大下载数量 (0=不限)
        page_size:        每页数量
        progress_callback: 进度回调 fn(current, total)

    返回:
        视频信息列表
    """
    all_videos = []
    page = 1
    total = None

    while True:
        result = await get_video_list(mid, page=page, page_size=page_size, order=order)
        page_data = result["data"]
        vlist = page_data["list"]["vlist"]

        if total is None:
            total = page_data["page"]["count"]

        if not vlist:
            break

        for v in vlist:
            all_videos.append(v)
            if max_count > 0 and len(all_videos) >= max_count:
                if progress_callback:
                    progress_callback(len(all_videos), total)
                return all_videos[:max_count]

        if progress_callback:
            progress_callback(len(all_videos), total)

        # 检查是否还有下一页
        pn = page_data["page"]["pn"]
        ps = page_data["page"]["ps"]
        count = page_data["page"]["count"]
        if pn * ps >= count:
            break

        page += 1

    return all_videos


async def get_video_detail(bvid: str) -> dict:
    """
    获取单个视频的详细信息（含各分P的 cid）

    返回:
        {
            "bvid": "BV...",
            "aid": 12345,
            "title": "...",
            "pic": "...",
            "owner": {"name": "...", "mid": ...},
            "cid": 12345,
            "pages": [{"cid": 12345, "part": "P1", "duration": 100}, ...],
            "duration": 1000,
            "desc": "...",
        }
    """
    signer = await get_wbi_signer()
    session = signer._get_session()

    async with session.get(
        "https://api.bilibili.com/x/web-interface/view",
        params={"bvid": bvid},
    ) as resp:
        data = await resp.json()

    if data.get("code") != 0:
        raise RuntimeError(f"获取视频详情失败: {data.get('message', '')}")

    info = data["data"]
    return {
        "bvid": info.get("bvid", ""),
        "aid": info.get("aid", 0),
        "title": info.get("title", ""),
        "pic": info.get("pic", ""),
        "owner": {
            "name": info.get("owner", {}).get("name", ""),
            "mid": info.get("owner", {}).get("mid", 0),
        },
        "cid": info.get("cid", 0),
        "pages": [
            {
                "cid": p.get("cid", 0),
                "part": p.get("part", ""),
                "duration": p.get("duration", 0),
            }
            for p in info.get("pages", [])
        ],
        "duration": info.get("duration", 0),
        "desc": info.get("desc", ""),
    }


def parse_space_url(url: str) -> Optional[int]:
    """
    从 B 站空间 URL 中提取 UID

    支持格式:
        https://space.bilibili.com/123456
        https://space.bilibili.com/123456/video
        https://space.bilibili.com/123456/dynamic
    """
    import re
    m = re.search(r"space\.bilibili\.com/(\d+)", url)
    if m:
        return int(m.group(1))
    return None


def parse_video_url(url: str) -> Optional[str]:
    """
    从 B 站视频 URL 中提取 BV 号

    支持格式:
        https://www.bilibili.com/video/BV1xx411c7mD
        https://b23.tv/xxxx (短链不处理，返回 None)
        BV1xx411c7mD
    """
    import re
    m = re.search(r"(BV[\w]+)", url)
    if m:
        return m.group(1)
    return None
