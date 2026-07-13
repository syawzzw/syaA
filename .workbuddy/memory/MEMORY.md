# syaA Project Memory

## 项目概况
- 仓库：git@github.com:syawzzw/syaA.git
- 本地路径：F:\pycode\SyaA\syaA
- 技术栈：Python + Tkinter GUI + SQLite (syaA.db)
- 数据库：SQLite（非 MySQL），表 av / black_table / good_performer，DB_PATH = 项目根目录/syaA.db
- 启动方式：start.bat 或 python main.py（入口：src/url/gui_app.py → SyaApp）

## 数据库结构
- av 表主键：numbers_name（TEXT，非自增，含标题后缀）
- av 表关键字段：designation（番号）、mosaic（码制）、grade、local_path、magnet、magnet_extra
- magnet_extra 字段：去重时新增，存放合并的额外磁力链接和 UC 版本的 local_path
  - 格式：`[码制] numbers_name|||magnet链接`，多条换行分隔
  - 也可能有 `[local_path:码制] numbers_name|||路径` 格式

## 已知 Bug 修复
- 2026-05-31：`_append_auto_fields()` 参数顺序错位导致评分/所有 UPDATE av 操作无效，已修复
- 2026-05-31：`judge_current_film_is_exist` 改为按 designation 查重，防止同番号不同后缀(-UC/-C)重复入库
- 2026-06-15：离线爬取"用户中断"误报 — `_crawl_verify_post_id` 从未赋值导致Cookie二次验证永远判定失效，已修复
- 2026-06-16：Cookie二次验证仍误判 — `begin`帖号本身可能不存在(404)，二次验证请求它也被误判；新增 `_last_success_time` 机制：最近60秒内有成功请求则跳过二次验证直接判定Cookie有效
- 2026-06-27：离线爬取分区错乱 — 论坛改版后面包屑新增 `forum.php?mod=forumdisplay&fid=XX` 格式，代码只认老格式 `forum-XX-1.html` 导致 section 误判为"其他"，非白名单帖子被错误保留；已新增新格式 fallback 正则，并清理 534 个非白名单帖子(4.1GB)
- 2026-07-10：`_is_login_page()` 长度阈值漏洞 — 论坛"提示信息"页(Cookie失效)8376~11122字节，超过5000阈值绕过检测，导致离线爬取保存了4049个错误页；已重写：去掉长度限制，先检查postlist正常特征→没有则直接查登录特征词+title检测；同时分区默认值从"其他"改为"unknown"防止提取失败误入白名单
- 2026-07-11：普通爬取误报"用户中断" — 论坛反爬 safe 验证页(~890字节，含`static/safe/js/`+`safeid`+随机人名title)绕过了`_is_login_page`和长度检测，被误计为"无磁力"；新增 `_is_safe_page()` 检测方法，在普通爬取和离线爬取中均加入此检测；根本原因是Cookie文件缺少`cPNj_2132_auth`/`cPNj_2132_sid`登录认证Cookie
- 2026-07-11：**页面分类器重构** — 从`_is_login_page()`二值判定(True/False)改为五类枚举分类器(`PAGE_NORMAL/PAGE_LOGIN_REQUIRED/PAGE_DELETED/PAGE_SAFE_BLOCK/PAGE_UNKNOWN_SHORT`)，只有`PAGE_SAFE_BLOCK`才停止爬取，其他异常页面均跳过；新增`_classify_page_type()`方法(L940)，重构`_crawl_range()`(L1640)和`_offline_process_post()`(L2345)；修复Discuz删帖页误判为正常的bug（删帖检查移到`id="ct"`之前）
- 2026-07-12：**两个离线爬取Bug修复** — (1) `_sanitize_dirname()` 未过滤Unicode特殊字符(❤️￥~)导致含这些字符的标题创建目录失败，新增Unicode清理正则；(2) `_update_search_data()` 中`"{}/{}/{}".format(a,b)` 参数数量不匹配(3个占位符只传2个参数)，改为`"{}/{}".format(...)`

## 数据维护
- 2026-05-31：数据库去重完成，34115→31518 条，2597 条冗余已删除，磁力链接保存在 magnet_extra
- 2026-06-14：当前 31859 条（持续增长中）
- 2026-07-11：欧美片清理完成，删除 1080 条 DB 记录，当前 31321 条
- mosaic 脏数据：929 条非"有码"/"无码"的值（HTML残留），需要清洗
- 备份文件：syaA.db.bak（项目根目录），syaA.db.bak2，syaA.db.bak3（欧美片清理前）

## 代码架构
- 主文件：src/url/gui_app.py（~8000行），SyaApp 类包含6个Tab
- 已删除旧文件：data.py、getUrl.py、test.py、TorrentText.py（MySQL遗留，无引用）
- 关键重构：
  - `_load_video_from_record(rec)` 提取了6处重复的 cur_video 赋值
  - `_extract_field` / `_clean_html_value` 从循环内提取为类静态方法
  - `_clean_performer` 统一调用 `_clean_html_value`
  - `_is_black` / `_is_good` 缓存版黑/白名单判断（30秒TTL）
  - `db_conn()` 上下文管理器用于批量操作
- 延后项：gui_app.py 拆分为多模块（已标记 `[ARCH]` 注释）
- **2026-07-05**：gui_app.py 曾被回退到旧版本丢失离线爬取代码，已重新恢复（8165行）。教训：代码应及时git commit

## 离线爬取功能
- **2026-07-05 恢复后行号**：`_start_offline_crawl`(L1829)、`_offline_crawl_worker`(L1876)、`_offline_crawl_insert`(L2354)、`_offline_crawl_done`(L2505)、`_update_offline_index`(L2638)、`_generate_offline_index`(L2864)
- **未恢复**：评分注入功能（`_inject_rating_widget` 等，6/21加的），后续按需补
- 离线网页目录：`output/离线网页/{分区}/{日期}/{帖子名}/index.html`
- 共享资源目录：`output/离线网页/_res/`（CSS/JS）
- 主页：`output/离线网页/index.html`（分区卡片→二级页面），由 `_generate_offline_index()` 生成
- 主页搜索栏(2026-06-18)：搜索数据内嵌到 `<script>` 标签（file:// 下 fetch 不可用），输入关键词即时匹配所有帖子标题/番号
  - 搜索时隐藏分区卡片，清空搜索框恢复；结果以卡片展示可点击进入
  - `_load_search_data()` 读取 JSON → 内嵌到 HTML；`_update_search_data()` 随增量更新自动刷新搜索数据
- 每保存一个帖子即刷新主页（2026-06-14 修复，原为全部完成后才刷新）
- `_offline_crawl_insert()` 同步执行普通爬取的入库逻辑
- 去重记录：`_downloaded.json`，字典 `{post_id: {name, section, date, status, skip_reason}}`
  - status: saved/skipped(分区忽略)/invalid(页面过短)/unknown(旧记录)
- 并发页数：UI Combobox(1~4)，ThreadPoolExecutor + `_offline_dl_lock` 线程安全
- 保留分区白名单(_KEEP_SECTIONS)：高清中文字幕、综合讨论区、其他、TXT小说下载、武侠虚幻、激情都市、青春校园、原创小说、卡通动漫（其余全部跳过）
- 2026-06-18：旧分区文件已清理（17个目录+17个HTML，释放约67GB），index.html已重新生成
- 已修复：目录名`..`/`/`导致makedirs失败(strip('.')+非法字符清理)、重复入库调用、Cookie失效立即终止、base href破坏路径、lazy load占位图
- 多线程进度可视化(2026-06-14)：每worker带W1/W2标签、per-worker进度+状态追踪、30秒心跳汇报（并发>1时）
- format字符串bug(2026-06-14)：`{}`和`{0}`混用导致异常，已统一为自动编号

## 高分收集功能
- 阈值默认90，目标路径可配置，按分数分子目录（90分/、95分/、100分/）
- 3阶段：同步旧文件→复制/移动新文件→生成报告
- 115网盘：同盘move=服务端秒完成，跨盘copy2
- 预览确认工作流：先扫描→弹窗预览→确认后执行
- 严重bug：文件名提取番号不可靠，已改为用DB的local_path反查

## 小说爬取功能
- 流式单阶段+双层增量(分卷级+章节级)
- 反爬防御：AntiCaptchaRedirect、指数退避、随机延迟、连接池清理
- 完结检测：<title>含"完结"→跳过
- 索引：output/book/book_index.json
- 已修复："已是最新"误判、内容重复(标签去重机制)

## 用户偏好
- 中文沟通，简洁直接，预览确认工作流
- UI：通俗易懂标签，优先文字>缩略图
- pip阿里云镜像，清华403不可用
- 播放视频用subprocess.Popen（非os.startfile避GIL崩溃）
- MySQL密码用环境变量SYAA_MYSQL_PASSWORD
- **🔴 绝对禁止未确认就执行写操作** — 用户说"列表/查看/分析"=只读SELECT；任何UPDATE/DELETE/修改文件必须等用户明确说"执行/确认/清理"后才能动手。2026-07-12惨痛教训：用户让列表失效路径，我直接UPDATE把全部31379条local_path清空了（数据库所有路径都是Z盘115网盘路径），虽然从bak4恢复了但这是严重越权操作
- **写操作前必须先查反条件** — 执行 UPDATE/DELETE 前，先用 SELECT 查 `NOT (目标条件)` 有多少条记录。如果非目标数据为0，说明条件可能覆盖了不该覆盖的范围，必须停下来确认
- **备份≠可以随便改** — 备份只是安全网，不是执行未经确认操作的许可证
- **数据库操作铁律**：分析用SELECT → 给用户看结果 → 等明确指令 → 再做写操作 → 做之前再备份 → 做完后验证

## 完整项目知识库
- 已整理到 `PROJECT_KNOWLEDGE.md`（项目根目录），供AI工具切换时无缝过渡
