# syaA Project Memory

## 项目概况
- 仓库：git@github.com:syawzzw/syaA.git
- 本地路径：D:\workspace\syaA
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

## 数据维护
- 2026-05-31：数据库去重完成，34115→31518 条，2597 条冗余已删除，磁力链接保存在 magnet_extra
- 备份文件：syaA.db.bak（项目根目录）

## 代码架构
- 主文件：src/url/gui_app.py（~7000行），SyaApp 类包含6个Tab
- 已删除旧文件：data.py、getUrl.py、test.py、TorrentText.py（MySQL遗留，无引用）
- 关键重构：
  - `_load_video_from_record(rec)` 提取了6处重复的 cur_video 赋值
  - `_extract_field` / `_clean_html_value` 从循环内提取为类静态方法
  - `_clean_performer` 统一调用 `_clean_html_value`
  - `_is_black` / `_is_good` 缓存版黑/白名单判断（30秒TTL）
  - `db_conn()` 上下文管理器用于批量操作
- 延后项：gui_app.py 拆分为多模块（已标记 `[ARCH]` 注释）

## 注意事项
- pip 需用阿里云镜像：`pip install -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com`
- 清华镜像当前返回 403，不可用
