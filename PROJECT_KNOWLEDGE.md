# SyaA 项目知识库

> 整理日期：2026-06-14 | 用途：AI 工具切换时无缝过渡

---

## 一、项目概况

| 项目 | 内容 |
|------|------|
| 仓库 | git@github.com:syawzzw/syaA.git |
| 本地路径 | F:\pycode\SyaA\syaA |
| 技术栈 | Python + Tkinter GUI + SQLite (syaA.db) |
| 启动方式 | `start.bat` 或 `python main.py`（入口：`src/url/gui_app.py` → `SyaApp`） |
| 主文件 | `src/url/gui_app.py`（~7000+ 行），SyaApp 类包含 6 个 Tab |
| 配置文件 | `gui_config.json`（自动保存/加载所有输入框值） |
| 数据库 | SQLite，DB_PATH = 项目根目录/syaA.db |
| 备份 | `syaA.db.bak`（项目根目录） |
| pip 镜像 | 阿里云：`pip install -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com` |
| 清华镜像 | 当前返回 403，不可用 |

---

## 二、数据库结构

### 表
- `av` — 主表，视频信息
- `black_table` — 黑名单演员（单列 `name`）
- `good_performer` — 白名单/关注演员（单列 `name`）

### av 表关键字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `numbers_name` | TEXT | **主键**（非自增，含标题后缀，如 `ABP-171 标题`） |
| `designation` | TEXT | 番号（如 `ABP-171`） |
| `mosaic` | TEXT | 码制：`有码` / `无码` |
| `grade` | INTEGER | 评分（0-100） |
| `performer` | TEXT | 演员名 |
| `film_name` | TEXT | 影片名 |
| `local_path` | TEXT | 本地文件路径 |
| `magnet` | TEXT | 主磁力链接 |
| `magnet_extra` | TEXT | 额外磁力链接+UC版local_path |
| `size` | TEXT | 影片容量 |
| `views` | TEXT | 查看数 |
| `created_at` | TEXT | 入库时间 |
| `updated_at` | TEXT | 最后更新时间 |
| `last_action` | TEXT | 最后操作类型标签 |
| `is_115` | TEXT | 115网盘标记 |

### magnet_extra 格式
- `[码制] numbers_name|||magnet链接`，多条换行分隔
- 也可能有 `[local_path:码制] numbers_name|||路径` 格式
- 来源：数据库去重时合并的额外记录

### 代码中的列索引常量
- `AV_COLUMNS` 常量 + `IDX_*` 索引常量（如 `IDX_LOCAL_PATH=13`、`IDX_GRADE=4` 等）
- **重要**：MySQL→SQLite 迁移后，`performer_grade` 列不再存在，所有硬编码索引改为命名常量

---

## 三、6 个 Tab 功能概览

### Tab1：论坛爬取
- 输入起止页+线程数+Cookie文件路径
- 11步过滤+入库：磁力提取→番号判断→中文筛选→欧美跳过→查重→入库
- Cookie失效检测（连续3次登录页→终止）
- 番号提取：跳过 `[中文字幕]`/`[无码]` 等前缀标签，>80字符跳过
- 欧美片识别：`is_western_designation()` 函数，70+品牌词库
- 按钮互斥：普通爬取和离线爬取同时只能运行一个
- 快捷按钮：爬100页/500页/1000页+自定义页数

### Tab2：播放视频
- 随机/播放/评分/删除/撤销/搜索/黑名单/关注
- 底部状态栏：左侧番号/演员/评分，中间标签状态(⚠黑/★关注/○无)，右侧全局统计
- 暗色/亮色主题切换
- 窗口大小/位置持久化

### Tab3：磁力生成
- 条件下推到 SQL 层：有码/无码、演员搜索、最小大小、排除-UC
- 排序：随机/热度/查看/最新入库
- "显示影片信息"复选框、复制/保存到文件
- "全部白名单磁力"按钮
- SQL 中 `%U` 被 pymysql 当格式占位符，需写 `%%-UC`（历史遗留，已迁移SQLite但仍保留写法）

### Tab4：数据库管理
- 清理数据库/查重/评分统计/数据库操作
- 统计仪表盘：码制比例、评分分布、TOP15演员
- MySQL→SQLite 迁移功能（密码用环境变量 `SYAA_MYSQL_PASSWORD`）

### Tab5：文件整理
- 一键整理流水线（5步）
- 高分收集：评分≥阈值→复制/移动到指定目录，按分数分子目录
- 115网盘路径检测
- 番号格式修正/路径清理/无效路径清理/批量删除

### Tab6：小说爬取
- 全量爬取/全站爬取/更新小说 三种模式
- 流式单阶段：爬一页立刻下载该页的书
- 双层增量检测：分卷级(TXT直链) + 章节级(逐章下载)
- 完结检测：`<title>` 标签含"完结"→跳过
- 反爬防御：AntiCaptchaRedirect、指数退避、随机延迟、连接池清理
- 索引文件：`output/book/book_index.json`

---

## 四、离线爬取功能（重点，近期大量开发）

### 目录结构
```
output/离线网页/
├── index.html                    # 主页（分区卡片，8KB）
├── {分区名}.html                  # 各分区二级页面（日期分组帖子卡片）
├── _res/                         # 共享 CSS/JS 资源
├── _downloaded.json              # 下载记录（去重用）
├── {分区}/{日期}/{帖子名}/
│   ├── index.html                # 帖子本地页
│   └── img/                      # 帖子图片
```

### 关键文件
- `_downloaded.json`：字典格式 `{post_id: {name, section, date, status, skip_reason}}`
  - `status`：saved(正常保存) / skipped(分区忽略) / invalid(页面过短) / unknown(旧记录)
  - 所有 status 都算已处理，去重时跳过不重复请求
- `_generate_offline_index()`：生成两级导航页面
  - 主页：分区卡片（名称+帖子数+最新日期），链接到各分区页面
  - 分区页：按日期倒序分组，帖子卡片链接到 index.html

### 爬取参数
- 并发页数：UI Combobox（1~4），范围拆分为N段，每段一个 ThreadPoolExecutor worker
- 每个 worker 内部 4 线程下载图片
- 线程安全：`_offline_dl_lock` 保护 shared_ctx 中的 downloaded_ids/meta/JSON写入

### 跳过分区（_SKIP_SECTIONS）
求片问答悬赏区、欧洲性爱、欧美风情、欧美无码、日韩有码、日韩无码、投诉建议区、国产自拍、剧情三级、亚洲性爱、乱伦人妻、中文字幕

### 关键 Bug 修复
- **目录名 `..` 导致 makedirs 失败**：标题如"中出.."末尾的 `..` 被 Windows 解析为上级目录 → `page_name.strip('.')` 和 `section_dir.strip('.')`
- **目录名 `/` 导致递归目录**：标题含 `/` 被解析为路径分隔符 → 统一 `re.sub(r'[\\/:*?"<>|\r\n\t]', '_', page_name)`
- **主页不更新**：原只在全部爬取完成后才刷新主页 → 改为每保存一个帖子就刷新
- **重复入库**：`_offline_crawl_insert()` 被调用两次 → 删除重复调用
- **Cookie失效不终止**：离线爬取遇到Cookie失效立即终止（不等3次）
- **base href破坏相对路径**：删除 `<base href="/">` 标签
- **Discuz lazy load**：图片 src 是占位图 `none.gif`，真实图在 `zoomfile`/`file` 属性 → 替换 src 为本地路径
- **static/ 无前导斜杠**：统一改写为绝对URL
- **format字符串混用**：`{}` 和 `{0}` 不能共存，导致 `cannot switch from automatic field numbering to manual field specification` → 统一自动编号

### 多线程进度可视化（2026-06-14）
- 每个并发 worker 分配标签（W1/W2/W3/W4），日志前缀 `[离线-W1]`
- per-worker 进度：`>> 处理 post=123 (15/200)`
- 状态追踪：请求页面→下载图片(N张)→下载CSS/JS→保存HTML→入库→已完成
- 心跳汇报线程（并发>1时每30秒）：输出各 worker 进度/当前post/状态
- 去掉冗余 `[DEBUG]` 日志，关键状态由心跳统一汇报

### 同步入库
- 离线爬取保存完 index.html + 源文件后，调用 `_offline_crawl_insert()` 同步执行普通爬取的入库逻辑
- 不符合条件的帖子静默跳过（不影响离线保存），日志用 `[离线+入库]` 标识

---

## 五、高分收集功能

### 流程（3阶段）
1. **同步旧文件**：用 DB 的 local_path 精确匹配（非文件名猜番号），评分变更的移到正确子目录，降至阈值的移回原始目录
2. **复制/移动新文件**：同盘用 `shutil.move`（115网盘服务端操作秒完成），跨盘用 `shutil.copy2`
3. **生成报告**：HTML 目录清单 + M3U 播放列表

### 115网盘特性
- `shutil.move` 同盘 = 服务端操作（6GB文件0.3秒）
- `shutil.copy2` 同盘 = 本地IO（会卡死）
- `os.link` 硬链接 = 不支持（WinError 50）

### 预览确认
- 点击"高分收集"→ 先扫描所有动作 → 弹窗预览（摘要+Treeview列表+颜色标签） → 确认后执行

### 严重 Bug 记录
- **文件名提取番号匹配不可靠**：阶段1从文件名提取番号匹配DB导致80个文件被错误"降级删除"。已改为用 DB 的 local_path 反查

---

## 六、代码架构与重构

### 已删除旧文件
`data.py`、`getUrl.py`、`test.py`、`TorrentText.py`（MySQL遗留，无引用）

### 关键重构
| 重构 | 说明 |
|------|------|
| `_load_video_from_record(rec)` | 提取了6处重复的 cur_video 赋值 |
| `_extract_field` / `_clean_html_value` | 从循环内提取为类静态方法 |
| `_clean_performer` | 统一调用 `_clean_html_value` |
| `_is_black` / `_is_good` | 缓存版黑/白名单判断（30秒TTL） |
| `db_conn()` | 上下文管理器，自动关闭连接 |
| `AV_COLUMNS` + `IDX_*` | 命名常量替代硬编码索引（MySQL→SQLite后关键修复） |

### 延后项
- gui_app.py 拆分为多模块（已标记 `[ARCH]` 注释）

### last_action 标签汇总
评分、撤销评分、撤销删除、删除、路径不可达、黑名单删除、低分删除、关键词删除、检测115、番号修正、路径清理、去重清理、高分收集-移动、高分收集-评分变更、高分收集-降级移回

---

## 七、已知 Bug 修复记录

| 日期 | Bug | 修复 |
|------|-----|------|
| 2026-05-24 | MySQL→SQLite 列索引偏移（`performer_grade` 列不存在） | `AV_COLUMNS` + `IDX_*` 命名常量 |
| 2026-05-31 | `_append_auto_fields()` 参数顺序错位 | 改为按 SET/WHERE 分段插入参数 |
| 2026-05-31 | `judge_current_film_is_exist` 按 numbers_name 查重 | 改为按 designation 查重 |
| 2026-05-26 | SQLite "database is locked" | timeout=30 + 批量操作复用连接 + 事务 |
| 2026-05-26 | `os.startfile()` GIL 崩溃 | 改用 `subprocess.Popen(["cmd","/c","start","",path])` |
| 2026-06-14 | 主页不自动更新 | 每保存一个帖子就调用 `_generate_offline_index()` |
| 2026-06-14 | 目录名 `..` 导致 makedirs 失败 | `strip('.')` |
| 2026-06-14 | 目录名 `/` 导致递归目录 | 统一清理非法字符 |
| 2026-06-14 | `_offline_crawl_insert` 重复调用 | 删除重复行 |

---

## 八、小说爬取模块要点

### 架构
- 流式单阶段：爬一页列表→立刻下载该页所有书
- 双层增量检测：分卷级(TXT直链 ~12KB/s) + 章节级(逐章 ~1KB/章)
- 完结检测：`<title>` 标签含"完结"

### 反爬防御
- `AntiCaptchaRedirect` 异常类：检测重定向到 google.com/cloudflare
- `_classify_error()` 错误分类：SSL/IncompleteRead/连接断开/超时/反爬/其他
- `_get_cooldown_seconds()`：连续SSL错误指数退避(3→6→9...上限15s)
- 延迟策略：列表页 2.5±随机 / 书籍间 2~4s / 目录翻页 1~2s / 分卷 1~2s / 章节 1.5~3s
- 连接池清理：`_cleanup_stale_connections()`
- 模块级 `_http_session` 替代 `requests.get()`

### 增量更新 Bug
- **"已是最新"误判**：`latest_chapter_num` 和本地存储值同源比较永远相等 → 改为始终通过目录爬取做真实检测
- **内容重复**：分卷结构变化导致同一标签卷被重新追加 → 新增标签去重机制(`downloaded_part_labels`)

### 关键方法
- `_fetch_book_meta()` → (书名, 作者, 分卷列表, 最新章节号, 是否完结)
- `_download_txt_with_retry()` → 分卷下载(3次重试+冷却)
- `_fetch_directory_chapters()` → 目录翻页提取章节列表
- `_download_single_chapter()` → 单章下载(多模式匹配+兜底清理)
- `get_url_txt_streaming()` → 流式下载(chunk_size=8192, progress_callback)

---

## 九、用户偏好与注意事项

- 沟通语言：中文，偏好简洁直接
- UI 设计：通俗易懂标签，优先文字信息而非缩略图
- Bug 报告：直接描述现象，期望 AI 主动排查修复
- 操作习惯：预览确认工作流（先展示操作内容和前后对比，确认后再执行）
- pip 镜像：阿里云（清华 403）
- Windows 编码：日志中 Unicode 特殊符号需替换为 ASCII
- 播放视频：`subprocess.Popen` 方式（非 `os.startfile`，避免 GIL 崩溃）
- 跨平台：播放视频加 `sys.platform` 判断，支持 Windows/macOS/Linux
- MySQL 密码：用环境变量 `SYAA_MYSQL_PASSWORD`，不硬编码

---

## 十、文件清单

| 文件 | 说明 |
|------|------|
| `src/url/gui_app.py` | 主文件，~7000+行，SyaApp 类 |
| `main.py` | 入口 |
| `start.bat` | Windows 启动脚本 |
| `syaA.db` / `syaA.db.bak` | 数据库 / 备份 |
| `gui_config.json` | GUI 配置持久化 |
| `GUIDE.md` | 使用指南 |
| `output/离线网页/` | 离线爬取输出目录 |
| `output/高清中文字幕网页源文件/` | HTML 源文件（按日期分目录） |
| `output/book/` | 小说下载 + `book_index.json` 索引 |
