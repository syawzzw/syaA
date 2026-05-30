# syaA Project Memory

## 项目概况
- 仓库：git@github.com:syawzzw/syaA.git
- 本地路径：D:\workspace\syaA
- 技术栈：Python + Tkinter GUI + SQLite (syaA.db)
- 数据库：SQLite（非 MySQL），表 av / black_table / good_performer，DB_PATH = 项目根目录/syaA.db
- 启动方式：start.bat 或 python main.py（入口：src/url/gui_app.py → SyaApp）

## 已知 Bug 修复
- 2026-05-31：`_append_auto_fields()` 参数顺序错位导致评分/所有 UPDATE av 操作无效，已修复

## 注意事项
- pip 需用阿里云镜像：`pip install -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com`
- 清华镜像当前返回 403，不可用
