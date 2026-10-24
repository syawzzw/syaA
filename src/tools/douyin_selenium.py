#!/usr/bin/env python3
"""
抖音视频下载器 - Selenium 版本
无需登录，通过浏览器自动化获取视频
用法: python douyin_selenium.py "视频链接" [下载数量]

核心改进：通过浏览器内 fetch() 直接调用抖音分页 API /aweme/v1/web/aweme/post/，获取用户全部视频
"""

import os
import sys
import time
import json
import subprocess
import argparse
import re
from collections import Counter

# 强制设置标准输出为 UTF-8 避免 GBK 编码问题
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests

# 默认保存目录
DEFAULT_OUTPUT_DIR = r"D:\抖音视频"

def sanitize_filename(name):
    """清理文件名中的非法字符"""
    # 替换所有换行符、制表符等空白字符为空格
    safe = re.sub(r'[\r\n\t\x00-\x1f]', ' ', name)
    # 替换其他非法字符
    safe = re.sub(r'[<>:"/\\|?*]', '_', safe)
    # 删除 emoji 等非 ASCII 字符（会导致 GBK 编码失败）
    safe = re.sub(r'[^\u0000-\u024f\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]', '', safe)
    # 去除连续空格
    safe = re.sub(r'\s+', ' ', safe)
    safe = safe.strip()[:50]
    return safe

def get_edge_driver_path():
    """获取 Edge WebDriver 路径"""
    try:
        result = subprocess.run(['where', 'msedgedriver'], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip().split('\n')[0]
    except:
        pass
    
    common_paths = [
        os.path.expanduser(r'~\AppData\Local\Programs\Microsoft Edge\msedgedriver.exe'),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedgedriver.exe",
    ]
    
    for path in common_paths:
        if os.path.exists(path):
            return path
    
    return None

def setup_driver():
    """配置 Edge 浏览器驱动"""
    edge_options = Options()
    edge_options.add_argument('--headless')
    edge_options.add_argument('--disable-gpu')
    edge_options.add_argument('--no-sandbox')
    edge_options.add_argument('--disable-dev-shm-usage')
    edge_options.add_argument('--disable-blink-features=AutomationControlled')
    edge_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver_path = get_edge_driver_path()
    
    if driver_path:
        service = Service(executable_path=driver_path)
        driver = webdriver.Edge(service=service, options=edge_options)
    else:
        driver = webdriver.Edge(options=edge_options)
    
    return driver

def resolve_short_link(url):
    """解析抖音短链接"""
    if 'v.douyin.com' in url:
        try:
            import urllib.request
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            response = urllib.request.urlopen(req, timeout=10)
            return response.geturl()
        except:
            pass
    return url

def get_aweme_id_from_url(url):
    """从URL中提取视频ID"""
    match = re.search(r'/video/(\d+)', url)
    if match:
        return match.group(1)
    return None

def extract_video_url(driver, url, owner_sec_uid=None):
    """
    访问视频页面，提取视频URL、用户名和视频ID。
    返回 (video_url, user_name, aweme_id, sec_uid, is_owner_video)
    """
    driver.get(url)
    time.sleep(4)  # 等待页面加载
    
    current_url = driver.current_url
    aweme_id = get_aweme_id_from_url(current_url)
    
    page_source = driver.page_source
    video_url = None
    
    # 方法1: 从 video > source 提取
    try:
        videos = driver.find_elements(By.TAG_NAME, 'video')
        for video in videos:
            # 检查 video 本身的 src
            src = video.get_attribute('src')
            if src and ('douyinvod' in src or 'aweme/v1/play' in src):
                video_url = src
                break
            
            # 检查 source 子元素
            sources = video.find_elements(By.TAG_NAME, 'source')
            for source in sources:
                src = source.get_attribute('src')
                if src and ('douyinvod' in src or 'aweme/v1/play' in src):
                    video_url = src
                    break
            
            if video_url:
                break
    except:
        pass
    
    # 获取视频标题
    video_title = ""
    try:
        title = driver.title
        if title and ' - 抖音' in title:
            video_title = title.replace(' - 抖音', '').strip()
        elif title:
            video_title = title.strip()
    except:
        pass
    
    # 从页面获取 sec_uid（作者用户ID）
    user_name = "抖音用户"
    sec_uid = None
    
    # 匹配 JSON-LD 中的 @item 或 anchor href 中的 user/SEC_UID 格式
    # 找出出现次数最多的 sec_uid（作者页面会出现多次）
    all_sec_uids = re.findall(r'douyin\.com/user/(MS4wLjABAAAA[^"\'&\\?/]+)', page_source)
    
    if all_sec_uids:
        # 统计出现次数，最多的是作者
        from collections import Counter
        counter = Counter(all_sec_uids)
        sec_uid = counter.most_common(1)[0][0]
        print(f"[找到sec_uid] {sec_uid}")
    
    # 判断是否为目标用户的视频
    is_owner_video = False
    if owner_sec_uid and sec_uid:
        is_owner_video = (owner_sec_uid == sec_uid)
    
    # 获取用户名 - 通过访问用户主页
    if sec_uid and user_name == "抖音用户":
        # 从 JSON-LD 结构数据获取作者名
        author_match = re.search(r'"name":\s*"([^"]+)"', page_source)
        if author_match:
            user_name = author_match.group(1)
        
        # 或者从 meta 标签获取
        if user_name == "抖音用户":
            meta_match = re.search(r'<meta[^>]*name="author"[^>]*content="([^"]+)"', page_source)
            if meta_match:
                user_name = meta_match.group(1)
    
    # 从 JSON-LD 脚本中找作者名
    if user_name == "抖音用户":
        ld_scripts = driver.find_elements(By.CSS_SELECTOR, 'script[type="application/ld+json"]')
        for script in ld_scripts:
            try:
                ld_data = json.loads(script.get_attribute('innerHTML'))
                if isinstance(ld_data, dict):
                    # 查找 author 字段
                    def find_author(obj):
                        if isinstance(obj, dict):
                            if 'author' in obj:
                                author = obj['author']
                                if isinstance(author, dict) and 'name' in author:
                                    return author['name']
                                if isinstance(author, str):
                                    return author
                            for v in obj.values():
                                result = find_author(v)
                                if result:
                                    return result
                        elif isinstance(obj, list):
                            for item in obj:
                                result = find_author(item)
                                if result:
                                    return result
                        return None
                    
                    author_name = find_author(ld_data)
                    if author_name:
                        user_name = author_name
                        break
            except:
                pass
    
    return video_url, video_title or user_name, aweme_id, sec_uid, is_owner_video


def get_user_home_videos(driver, user_url_or_secuid, limit=0):
    """
    获取用户主页所有视频 ID 列表。
    
    核心策略：直接在浏览器中通过 fetch() 调用抖音 API /aweme/v1/web/aweme/post/
    使用分页游标 max_cursor 逐步获取全部视频。
    """
    if user_url_or_secuid.startswith('http'):
        user_url = user_url_or_secuid
        sec_uid_match = re.search(r'/user/([^/?#]+)', user_url)
        owner_sec_uid = sec_uid_match.group(1) if sec_uid_match else None
    else:
        owner_sec_uid = user_url_or_secuid
        user_url = f"https://www.douyin.com/user/{user_url_or_secuid}"
    
    print(f"[访问用户主页] {user_url}")
    driver.get(user_url)
    
    # 等待页面加载
    print("[等待] 页面加载中...")
    time.sleep(5)
    
    # 尝试从页面提取 sec_uid
    if not owner_sec_uid:
        page_source = driver.page_source
        uid_match = re.search(r'"sec_uid"\s*:\s*"([^"]+)"', page_source)
        if uid_match:
            owner_sec_uid = uid_match.group(1)
    
    if not owner_sec_uid:
        print("[错误] 无法获取 sec_uid")
        return []
    
    print(f"[sec_uid] {owner_sec_uid}")
    
    all_video_ids = set()
    
    # 方法1: 从页面初始数据提取
    print("[方法1] 从页面初始数据提取视频...")
    
    js_extract = """
    var result = {
        ids: [],
        hasMore: false,
        maxCursor: 0
    };
    
    // 从 __INITIAL_STATE__ 提取
    if (window.__INITIAL_STATE__) {
        try {
            var state = window.__INITIAL_STATE__;
            // 查找用户的视频列表
            if (state.user && state.user.post) {
                var post = state.user.post;
                if (post.aweme_list) {
                    post.aweme_list.forEach(function(item) {
                        if (item.aweme_id) result.ids.push(item.aweme_id);
                    });
                }
                result.hasMore = post.has_more === 1;
                result.maxCursor = post.max_cursor || 0;
            }
        } catch(e) {
            console.log('Error in __INITIAL_STATE__:', e);
        }
    }
    
    // 从 RENDER_DATA 提取
    if (result.ids.length === 0) {
        var renderData = document.querySelector('script[id="RENDER_DATA"]');
        if (renderData) {
            try {
                var decoded = decodeURIComponent(renderData.textContent);
                var data = JSON.parse(decoded);
                
                // 查找 aweme_list
                function findAwemeList(obj) {
                    if (typeof obj !== 'object' || obj === null) return null;
                    if (obj.aweme_list && Array.isArray(obj.aweme_list)) {
                        return obj;
                    }
                    for (var key in obj) {
                        var found = findAwemeList(obj[key]);
                        if (found) return found;
                    }
                    return null;
                }
                
                var awemeData = findAwemeList(data);
                if (awemeData && awemeData.aweme_list) {
                    awemeData.aweme_list.forEach(function(item) {
                        if (item.aweme_id) result.ids.push(item.aweme_id);
                    });
                    result.hasMore = awemeData.has_more === 1 || awemeData.hasMore === 1;
                    result.maxCursor = awemeData.max_cursor || awemeData.maxCursor || 0;
                }
            } catch(e) {
                console.log('Error in RENDER_DATA:', e);
            }
        }
    }
    
    // 从 DOM 链接提取
    if (result.ids.length === 0) {
        var links = document.querySelectorAll('a[href*="/video/"]');
        links.forEach(function(link) {
            var match = link.href.match(/\\/video\\/(\\d+)/);
            if (match && result.ids.indexOf(match[1]) === -1) {
                result.ids.push(match[1]);
            }
        });
    }
    
    return result;
    """
    
    try:
        result = driver.execute_script(js_extract)
        if result and result.get('ids'):
            all_video_ids.update(result['ids'])
            print(f"[页面提取] 获取到 {len(result['ids'])} 个视频 ID")
            has_more = result.get('hasMore', False)
            max_cursor = result.get('maxCursor', 0)
        else:
            has_more = True
            max_cursor = 0
    except Exception as e:
        print(f"[页面提取失败] {e}")
        has_more = True
        max_cursor = 0
    
    # 方法2: 通过浏览器 fetch 调用 API 获取更多视频
    print("[方法2] 通过 API 获取更多视频...")
    
    page_num = 0
    max_pages = 20  # 最多获取20页
    
    while has_more and page_num < max_pages:
        page_num += 1
        
        # 使用同步方式调用 API
        api_script = f"""
        var callback = arguments[arguments.length - 1];
        
        (async function() {{
            try {{
                // 构建 API URL
                var baseUrl = 'https://www.douyin.com/aweme/v1/web/aweme/post/';
                var params = new URLSearchParams({{
                    'sec_user_id': '{owner_sec_uid}',
                    'max_cursor': {max_cursor},
                    'count': 18,
                    'platform': 'PC',
                    'downlink': 10
                }});
                
                var apiUrl = baseUrl + '?' + params.toString();
                
                var response = await fetch(apiUrl, {{
                    method: 'GET',
                    headers: {{
                        'Accept': 'application/json',
                        'Referer': 'https://www.douyin.com/',
                        'User-Agent': navigator.userAgent
                    }},
                    credentials: 'include'
                }});
                
                var data = await response.json();
                callback({{success: true, data: data}});
            }} catch(e) {{
                callback({{success: false, error: e.message}});
            }}
        }})();
        """
        
        try:
            # 使用较短的超时
            api_result = driver.execute_async_script(api_script)
            
            if api_result and api_result.get('success') and api_result.get('data'):
                data = api_result['data']
                
                if data.get('aweme_list'):
                    new_ids = []
                    for item in data['aweme_list']:
                        if item.get('aweme_id'):
                            new_ids.append(item['aweme_id'])
                    
                    before = len(all_video_ids)
                    all_video_ids.update(new_ids)
                    after = len(all_video_ids)
                    
                    print(f"[API 第{page_num}页] 获取 {len(new_ids)} 个，累计 {after} 个")
                    
                    # 更新分页状态
                    has_more = data.get('has_more') == 1
                    max_cursor = data.get('max_cursor', 0)
                    
                    if not has_more or max_cursor == 0:
                        print("[API] 没有更多视频了")
                        break
                else:
                    print(f"[API 第{page_num}页] 返回数据为空")
                    break
            else:
                error_msg = api_result.get('error', 'Unknown error') if api_result else 'No result'
                print(f"[API 第{page_num}页] 调用失败: {error_msg}")
                break
                
        except Exception as e:
            print(f"[API 第{page_num}页] 执行失败: {e}")
            break
        
        # 等待一下再请求下一页
        time.sleep(1)
    
    # 方法3: 如果API方法获取的视频太少，尝试滚动页面
    if len(all_video_ids) < 30:
        print("[方法3] 滚动页面获取更多视频...")
        
        last_count = len(all_video_ids)
        no_new_count = 0
        
        for scroll_round in range(30):
            driver.execute_script('window.scrollTo(0, document.body.scrollHeight)')
            time.sleep(2)
            
            # 从 DOM 提取新链接
            dom_script = """
            var ids = [];
            var links = document.querySelectorAll('a[href*="/video/"]');
            links.forEach(function(link) {
                var match = link.href.match(/\\/video\\/(\\d+)/);
                if (match) ids.push(match[1]);
            });
            return ids;
            """
            
            try:
                new_ids = driver.execute_script(dom_script)
                if new_ids:
                    before = len(all_video_ids)
                    all_video_ids.update(new_ids)
                    after = len(all_video_ids)
                    if after > before:
                        print(f"[滚动 {scroll_round + 1}] 新增 {after - before} 个，累计 {after} 个")
            except:
                pass
            
            current_count = len(all_video_ids)
            if current_count > last_count:
                last_count = current_count
                no_new_count = 0
            else:
                no_new_count += 1
                if no_new_count >= 5:
                    print(f"[滚动完成] 连续 {no_new_count} 次无新增")
                    break
    
    result = list(all_video_ids)
    print(f"\n[完成] 共收集到 {len(result)} 个视频 ID")
    
    return result


def download_video(video_url, output_path, title="video"):
    """下载视频到本地"""
    if not video_url:
        return False
    
    print(f"[下载] {title}")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.douyin.com/',
        }
        
        response = requests.get(video_url, headers=headers, stream=True, timeout=120)
        
        if response.status_code == 200:
            total_size = int(response.headers.get('content-length', 0))
            print(f"[大小] {total_size / (1024*1024):.2f} MB")
            
            downloaded = 0
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            print(f"\r[进度] {progress:.1f}%", end='', flush=True)
            
            print(f"\n[完成] {output_path}")
            return True
        else:
            print(f"[失败] HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"[错误] {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='抖音视频下载器 - Selenium版本')
    parser.add_argument('link', help='抖音视频链接')
    parser.add_argument('count', nargs='?', default='0', help='下载数量 (0=全部)')
    parser.add_argument('-o', '--output', default=DEFAULT_OUTPUT_DIR, help='输出目录')
    
    args = parser.parse_args()
    
    video_link = args.link
    count = int(args.count) if args.count.isdigit() else 0
    output_dir = args.output
    
    # 解析短链接
    print("[解析链接...]")
    resolved_url = resolve_short_link(video_link)
    print(f"[实际URL] {resolved_url}")
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    print("\n[启动浏览器...]")
    driver = None
    
    try:
        driver = setup_driver()
        
        # 获取第一个视频的URL和用户信息
        video_url, video_title, aweme_id, sec_uid, _ = extract_video_url(driver, video_link)
        
        # 如果有sec_uid，从用户主页获取用户名
        user_name = "抖音用户"
        if sec_uid:
            # 直接访问用户主页获取用户名
            driver.get(f"https://www.douyin.com/user/{sec_uid}")
            time.sleep(2)
            try:
                page_title = driver.title
                if page_title:
                    # 格式通常是: 用户名的抖音 | 用户名
                    if '的抖音' in page_title:
                        user_name = page_title.split('的抖音')[0].strip()
                    elif ' | ' in page_title:
                        user_name = page_title.split(' | ')[0].strip()
                    elif ' - ' in page_title:
                        user_name = page_title.split(' - ')[0].strip()
            except:
                pass
        
        print(f"[用户] {user_name}")
        
        # 清理用户名中的非法字符
        safe_user_name = sanitize_filename(user_name)
        
        # 创建用户目录
        user_dir = os.path.join(output_dir, safe_user_name)
        os.makedirs(user_dir, exist_ok=True)
        print(f"[保存目录] {user_dir}")
        
        if count == 1 or (not sec_uid):
            # 只下载单个视频
            if video_url:
                output_file = os.path.join(user_dir, f"video_{aweme_id}.mp4")
                
                # 避免重复下载
                if os.path.exists(output_file):
                    print(f"[跳过] 文件已存在: {output_file}")
                else:
                    success = download_video(video_url, output_file)
                    if success:
                        print(f"\n[成功] 已保存到: {output_file}")
                    else:
                        print("\n[失败] 下载失败")
            else:
                print("[错误] 无法提取视频URL")
        else:
            # 获取该用户的所有视频
            if sec_uid:
                aweme_ids = get_user_home_videos(driver, sec_uid, limit=count)
            else:
                # 尝试从用户主页 URL 提取
                aweme_ids = [aweme_id] if aweme_id else []
            
            print(f"[收集] 共获取到 {len(aweme_ids)} 个视频")
            
            # 下载视频
            download_count = 0
            skipped_count = 0
            for idx, vid_id in enumerate(aweme_ids):
                if count > 0 and download_count >= count:
                    break
                
                print(f"\n[视频 {download_count+1}/{len(aweme_ids) if not count else count}] ID={vid_id}")
                
                # 获取视频URL，同时检查是否为目标用户的视频
                vid_url, _, _, vid_sec_uid, is_owner_video = extract_video_url(driver, f"https://www.douyin.com/video/{vid_id}", owner_sec_uid=sec_uid)
                
                # 如果不是目标用户的视频，跳过
                if sec_uid and vid_sec_uid and not is_owner_video:
                    print(f"[跳过] 非目标用户视频 (sec_uid: {vid_sec_uid})")
                    skipped_count += 1
                    continue
                
                if vid_url:
                    output_file = os.path.join(user_dir, f"video_{vid_id}.mp4")
                    
                    if os.path.exists(output_file):
                        print(f"[跳过] 文件已存在")
                        download_count += 1
                        continue
                    
                    success = download_video(vid_url, output_file)
                    if success:
                        download_count += 1
                else:
                    print(f"[跳过] 无法获取视频URL")
                
                time.sleep(1)
            
            print(f"\n[完成] 共下载 {download_count} 个视频，跳过 {skipped_count} 个非目标用户视频")
            
    except Exception as e:
        print(f"[错误] {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if driver:
            driver.quit()

if __name__ == '__main__':
    main()
