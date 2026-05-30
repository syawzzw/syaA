import requests
from lxml import etree
import re
import time
import pymysql
from tqdm import tqdm
import os
import tkinter as tk
import threading
from tkinter import ttk
import hashlib
import shutil


class GUI:
    def __init__(self):
        #---- 实例定义
        #---- 主窗口
        self.main_window = None
        self.main_bt1 = None
        self.main_bt2 = None

        #---- click1
        self.click1_window = None
        self.click1_sub1_text = None
        self.click1_bt1_video_path = ""
        self.click1_bt1_fanhao = ""
        self.click1_bt1_performer = ""
        self.click1_bt1_video_name = ""
        self.click1_bt1_video_key = ""
        self.click1_bt1_grade = ""
        self.click1_bt1_mosaic = ""

        #---- click2

        #---- 其他
        self.main()


    def main(self):
        self.main_window = tk.Tk()  # 初始化主窗口
        self.main_window.title("瑟瑟")
        self.main_window.geometry("400x300")

        self.main_bt1 = tk.Button(self.main_window,
                        text="播放视频",
                        command=self.click1,
                        width=10,
                        height=1)
        self.main_bt1.place(x=10, y=10)

        # 批量生成未评分作品
        self.main_bt2 = tk.Button(self.main_window,
                        text="生成下载视频磁力",
                        command=self.click2,
                        width=15,
                        height=1)
        self.main_bt2.place(x=100, y=10)

        self.main_window.mainloop()

    def callback_mainwindow(self, window):
        self.main_window.deiconify()
        window.destroy()

    def click1(self):
        self.main_window.withdraw()
        self.click1_window = tk.Tk()
        self.click1_window.protocol("WM_DELETE_WINDOW", lambda: self.callback_mainwindow(self.click1_window))
        self.click1_window.title("播放视频")
        self.click1_window.geometry("800x400")
        self.click1_sub1_text = tk.Text(self.click1_window, width=75, height=20)
        self.click1_sub1_text.place(x=200, y=30)
        self.click1_sub1_text.delete(1.0, tk.END)
        self.click1_sub1_text.insert(1.0, "番号：" + self.click1_bt1_fanhao + '\n')
        self.click1_sub1_text.insert(1.0, "演员：" + self.click1_bt1_performer + '\n')
        self.click1_sub1_text.insert(1.0, "码：" + self.click1_bt1_mosaic + '\n')
        self.click1_sub1_text.insert(1.0, "影片名称：" + self.click1_bt1_video_name + '\n')
        self.click1_sub1_text.insert(1.0, "路径：" + self.click1_bt1_video_path + '\n')

        sub1_bt1 = tk.Button(self.click1_window, text="nozzz视频",
                             command=lambda: self.click1_rand_db_no_grade_video(0), width=10, height=1)
        sub1_bt1.place(x=10, y=10)

        sub1_bt2 = tk.Button(self.click1_window, text="随机all视频",
                             command=lambda: self.click1_rand_db_no_grade_video(1), width=13, height=1)
        sub1_bt2.place(x=93, y=10)

        # 播放按钮
        sub1_bt2 = tk.Button(self.click1_window,
                             text="播放",
                             command=lambda: self.click1_play_video(self.click1_sub1_text),
                             width=20,
                             height=1)
        sub1_bt2.place(x=10, y=50)

        sub1_combobox1 = ttk.Combobox(self.click1_window, width=7)
        sub1_combobox1.place(x=10, y=90)
        sub1_combobox1['values'] = ("10", "20", "30", "40", "50", "60", "70", "80", "90", "100")
        sub1_combobox1.current(5)

        # 评分按钮
        sub1_bt3 = tk.Button(self.click1_window,
                             text="评分",
                             command=lambda: self.click1_video_grade(sub1_combobox1, self.click1_sub1_text),
                             width=7, height=1)
        sub1_bt3.place(x=100, y=87)

        # 删除按钮
        sub1_bt3 = tk.Button(self.click1_window, text="删除当前视频，并更新数据库",
                             command=lambda: self.click1_delete_curr_viedo(self.click1_sub1_text),
                             width=25, height=1)
        sub1_bt3.place(x=10, y=130)

        # 播放好看的视频
        sub1_bt4 = tk.Button(self.click1_window, text="播放选择分数之上的随机视频",
                             command=lambda: self.click1_view_good_video(sub1_combobox1, self.click1_sub1_text),
                             width=25, height=1)
        sub1_bt4.place(x=10, y=170)

        # 将此演员加入黑名单
        sub1_bt5 = tk.Button(self.click1_window, text="将此演员加入黑名单",
                             command=lambda: self.click1_put_performer_in_black_list(self.click1_sub1_text),
                             width=25, height=1)
        sub1_bt5.place(x=10, y=210)

        # 将此演员从黑名单删除
        sub1_bt5 = tk.Button(self.click1_window, text="将此演员从黑名单删除",
                             command=lambda: self.click1_put_performer_in_black_list_to_notag(self.click1_sub1_text),
                             width=25, height=1)
        sub1_bt5.place(x=10, y=240)

        # 将此演员加关注名单
        sub1_bt5 = tk.Button(self.click1_window, text="将此演员加入关注名单",
                             command=lambda: self.click1_put_performer_in_good_list(self.click1_sub1_text),
                             width=25, height=1)
        sub1_bt5.place(x=10, y=300)

        # 将此演员从白名单移除
        sub1_bt5 = tk.Button(self.click1_window, text="将此演员从白名单移除",
                             command=lambda: self.click1_put_performer_in_good_list_to_notag(self.click1_sub1_text),
                             width=25, height=1)
        sub1_bt5.place(x=10, y=330)

        return

    def click1_rand_db_no_grade_video(self, is_zzz):
        con = pymysql.connect(user='root', password="989796", host='localhost', port=3306)
        con.select_db("h_db")
        cur = con.cursor()
        if is_zzz:
            print("当前zzz为1")
            cur.execute("select * from av where local_path is not null and grade is null order by RAND() limit 1")
        else:
            print("当前zzz为0")
            cur.execute(
                "select * from av where local_path is not null and grade is null and zzz is null order by RAND() limit 1")
        curr_record = cur.fetchone()
        self.click1_bt1_video_key = curr_record[0]
        self.click1_bt1_video_path = curr_record[14]
        self.click1_bt1_fanhao = curr_record[9]
        self.click1_bt1_performer = curr_record[4]
        self.click1_bt1_mosaic = curr_record[6]

        self.click1_bt1_video_name = curr_record[10]

        self.click1_sub1_text.delete(1.0, tk.END)
        self.click1_sub1_text.insert(tk.INSERT, "番号：" + self.click1_bt1_fanhao + '\n')
        self.click1_sub1_text.insert(tk.INSERT, "演员：" + self.click1_bt1_performer + '\n')
        # sub1_text.insert(tk.INSERT, "码：" + self.click1_bt1_mosaic + '\n')
        self.click1_sub1_text.insert(tk.INSERT, "影片名称：" + self.click1_bt1_video_name + '\n')
        self.click1_sub1_text.insert(tk.INSERT, "路径：" + self.click1_bt1_video_path + '\n')

        # 查找当前剩余url数量与剩余未评分url数量
        cur.execute("select count(*) from av where local_path is not null")
        curr_record = cur.fetchone()
        self.click1_sub1_text.insert(tk.INSERT, "剩余本地视频：" + str(curr_record[0]) + '\n')

        cur.execute("select count(*) from av where local_path is not null and grade is null")
        curr_record = cur.fetchone()
        self.click1_sub1_text.insert(tk.INSERT, "剩余未评分本地视频：" + str(curr_record[0]) + '\n')

        cur.execute("select count(*) from av where local_path is not null and grade is null and zzz is null")
        curr_record = cur.fetchone()
        self.click1_sub1_text.insert(tk.INSERT, "剩余未评分本地视频（nozzz）：" + str(curr_record[0]) + '\n')

        # 增加演员在不在黑名单的判断
        if judge_performer(self.click1_bt1_performer):
            self.click1_sub1_text.insert(tk.INSERT, "[黑名单]当前演员在黑名单中：" + self.click1_bt1_performer + '\n')
        elif judge_performer_is_good(self.click1_bt1_performer):
            self.click1_sub1_text.insert(tk.INSERT, "[白名单]当前演员在白名单中：" + self.click1_bt1_performer + '\n')
        else:
            self.click1_sub1_text.insert(tk.INSERT, "[notag]当前演员notag\n")
        cur.close()
        con.close()
        return

    def click1_play_video(self, sub1_text):
        if not os.path.isfile(self.click1_bt1_video_path):
            link_db_cmd("update av set local_path = NULL where numbers_name = %s",
                        (self.click1_bt1_video_key))
            link_db_cmd("update av set exist_in_115 = NULL where numbers_name = %s",
                        (self.click1_bt1_video_key))
            sub1_text.insert(1.0, "路径下视频不可达，已更新数据库内路径，请检查")
            return
        os.startfile(self.click1_bt1_video_path)
        print(self.click1_bt1_video_path)

    # 评分函数
    def click1_video_grade(self, sub1_combobox1, sub1_text):
        ret = sub1_combobox1.get()
        ret = int(ret)
        link_db_cmd("update av set grade = %s where numbers_name = %s",
                    (ret, self.click1_bt1_video_key))
        sub1_text.insert(1.0, "评分完成\n")

    # 删除当前视频并更新数据库
    def click1_delete_curr_viedo(self, sub1_text):
        if self.click1_bt1_video_key == "":
            sub1_text.insert(1.0, "路径为空\n")
            return
        link_db_cmd("update av set local_path = NULL where numbers_name = %s",
                    (self.click1_bt1_video_key))
        link_db_cmd("update av set exist_in_115 = NULL where numbers_name = %s",
                    (self.click1_bt1_video_key))
        if os.path.exists(self.click1_bt1_video_path):
            os.remove(self.click1_bt1_video_path)
            sub1_text.insert(1.0, "删除文件成功\n")
        else:
            sub1_text.insert(1.0, "文件不存在，删除失败\n")

    # 播放选择分数之上的随机视频
    def click1_view_good_video(self, sub1_combobox1, sub1_text):
        con = pymysql.connect(user='root', password="989796", host='localhost', port=3306)
        con.select_db("h_db")
        cur = con.cursor()
        ret = sub1_combobox1.get()
        ret = int(ret)
        cur.execute("select * from av where local_path is not null and grade >= %s order by RAND() limit 1", (ret))
        curr_record = cur.fetchone()
        self.click1_bt1_video_key = curr_record[0]
        self.click1_bt1_video_path = curr_record[14]
        self.click1_bt1_fanhao = curr_record[9]
        self.click1_bt1_performer = curr_record[4]
        self.click1_bt1_mosaic = curr_record[6]
        self.click1_bt1_video_name = curr_record[10]
        self.click1_bt1_grade = curr_record[11]
        cur.close()
        con.close()
        sub1_text.delete(1.0, tk.END)
        sub1_text.insert(tk.INSERT, "番号：" + self.click1_bt1_fanhao + '\n')
        sub1_text.insert(tk.INSERT, "演员：" + self.click1_bt1_performer + '\n')
        sub1_text.insert(tk.INSERT, "码：" + self.click1_bt1_mosaic + '\n')
        sub1_text.insert(tk.INSERT, "影片名称：" + self.click1_bt1_video_name + '\n')
        sub1_text.insert(tk.INSERT, "路径：" + self.click1_bt1_video_path + '\n')
        sub1_text.insert(tk.INSERT, "分数：" + str(self.click1_bt1_grade) + '\n')

        # 增加演员在不在黑名单的判断
        if judge_performer(self.click1_bt1_performer):
            sub1_text.insert(tk.INSERT, "[黑名单]当前演员在黑名单中：" + self.click1_bt1_performer + '\n')
        elif judge_performer_is_good(self.click1_bt1_performer):
            sub1_text.insert(tk.INSERT, "[白名单]当前演员在白名单中：" + self.click1_bt1_performer + '\n')
        else:
            sub1_text.insert(tk.INSERT, "[notag]当前演员notag\n")
        return

    # 将此演员加入黑名单
    def click1_put_performer_in_black_list(self, sub1_text):
        curr_per = self.click1_bt1_performer
        if curr_per == "":
            sub1_text.insert(tk.INSERT, '当前演员为空\n')
            return
        if judge_performer(curr_per):
            sub1_text.insert(tk.INSERT, '当前演员已在黑名单\n')
            return
        link_db_cmd("INSERT INTO black_table (name) VALUES (%s)", (curr_per,))
        sub1_text.insert(tk.INSERT, "已将：" + str(curr_per) + ' 加入黑名单\n')

    def click1_put_performer_in_black_list_to_notag(self, sub1_text):
        curr_per = self.click1_bt1_performer
        if not judge_performer(curr_per):
            sub1_text.insert(tk.INSERT, '当前演员不在黑名单\n')
            return
        judge_performer_make_notag(curr_per)
        sub1_text.insert(tk.INSERT, '已将 ' + curr_per + ' 从黑名单移除\n')
        return

    # 将此演员加入关注名单
    def click1_put_performer_in_good_list(self, sub1_text):
        curr_per = self.click1_bt1_performer
        if curr_per == "":
            sub1_text.insert(tk.INSERT, '当前演员为空\n')
            return
        if judge_performer_is_good(curr_per):
            sub1_text.insert(tk.INSERT, '当前演员已在关注名单\n')
            return
        link_db_cmd("INSERT INTO good_performer (name) VALUES (%s)", (curr_per,))
        sub1_text.insert(tk.INSERT, "已将：" + str(curr_per) + ' 加入关注名单\n')

    def click1_put_performer_in_good_list_to_notag(self, sub1_text):
        curr_per = self.click1_bt1_performer
        if not judge_performer_is_good(curr_per):
            sub1_text.insert(tk.INSERT, '当前演员不在白名单\n')
            return
        judge_performer_is_good_make_notag(curr_per)
        sub1_text.insert(tk.INSERT, '已将 ' + curr_per + ' 从白名单移除\n')
        return

    def click2(self):
        self.main_window.withdraw()
        self.sub2_window = tk.Tk()
        self.sub2_window.protocol("WM_DELETE_WINDOW", lambda: self.callback_mainwindow(self.sub2_window))
        self.sub2_window.title("生成磁力")
        self.sub2_window.geometry("800x400")
        sub2_text = tk.Text(self.sub2_window, width=70, height=5)
        sub2_text.place(x=170, y=10)
        sub2_text.delete(1.0, tk.END)

        sub2_combobox1 = ttk.Combobox(self.sub2_window, width=10)
        sub2_combobox1.place(x=10, y=150)
        sub2_combobox1['values'] = ("10", "20", "30", "40", "50", "60", "70", "80", "90", "10")
        sub2_combobox1.current(5)

        # 选择是否生成关注列表对应磁力
        # self.sub2_var1 = tk.IntVar()
        # self.sub2_is_white_button = tk.Checkbutton(self.sub2_window,
        #                                            text="是否仅生成关注清单内视频",
        #                                            variable=self.sub2_var1,
        #                                            onvalue=0, offvalue=1,
        #                                            command=self.click2_sub2_var1)
        # self.sub2_is_white_button.place(x=10, y=140)

        sub2_bt1 = tk.Button(self.sub2_window, text="生成磁力(条)",
                             command=lambda: self.click2_gen_magnet_button(sub2_combobox1, sub2_text, False), width=20, height=1)
        sub2_bt1.place(x=10, y=10)

        sub2_bt3 = tk.Button(self.sub2_window, text="生成磁力仅关注(条)",
                             command=lambda: self.click2_gen_magnet_button(sub2_combobox1, sub2_text, True), width=20,
                             height=1)
        sub2_bt3.place(x=10, y=50)

        sub2_bt2 = tk.Button(self.sub2_window, text="清空",
                             command=lambda: sub2_bt2_func(sub2_text), width=20, height=1)
        sub2_bt2.place(x=10, y=100)

        return

    def click2_gen_magnet_button(self, sub2_combobox1, sub2_text, is_white):
        con = pymysql.connect(user='root', password="989796", host='localhost', port=3306)
        con.select_db("h_db")
        cur = con.cursor()
        num = sub2_combobox1.get()
        num = int(num)
        cur.execute(
            "select * from av where local_path is null and grade is null and magnet is not null order by RAND() limit %s",
            (num))
        curr_record = cur.fetchall()
        for record in curr_record:
            if "-UC" in record[0]:
                continue
            if judge_performer(record[4]):
                save_log("[磁力生成][fail]当前演员在黑名单中,此视频不做磁力：" + record[0])
                continue
            if not judge_performer_is_good(record[4]) and is_white:
                save_log("[磁力生成][fail]当前只要白名单演员，此视频不做磁力：" + record[0])
                continue
            save_log("[磁力生成][success]，演员：" + record[4] + " --- 影片名称：" + record[0])
            sub2_text.insert(1.0, record[2] + '\n')

def link_db_cmd(inseert_str, val=()):
    con = pymysql.connect(user='root', password="989796", host='localhost', port=3306)
    con.select_db("h_db")
    cur = con.cursor()
    cur.execute(inseert_str, val)
    ret = cur.fetchall()
    con.commit()
    cur.close()
    con.close()
    return ret

# 将当前演员从黑名单移除
def judge_performer(performer):
    con = pymysql.connect(user='root', password="989796", host='localhost', port=3306)
    con.select_db("h_db")
    cur = con.cursor()
    cur.execute("select * from black_table where name = %s", (performer,))
    curr_record = cur.fetchone()
    cur.close()
    con.close()
    if curr_record is not None:
        return True
    return False

# 判断当前演员是否在关注中
def judge_performer_is_good(performer):
    con = pymysql.connect(user='root', password="989796", host='localhost', port=3306)
    con.select_db("h_db")
    cur = con.cursor()
    cur.execute("select * from good_performer where name = %s", (performer,))
    curr_record = cur.fetchone()
    if curr_record is not None:
        return True
    return False

# 判断当前演员是否在黑名单中
def judge_performer_make_notag(performer):
    con = pymysql.connect(user='root', password="989796", host='localhost', port=3306)
    con.select_db("h_db")
    cur = con.cursor()
    cur.execute("delete from black_table where name = %s", (performer,))
    con.commit()
    cur.close()
    con.close()

# 将白名单演员转为notag
def judge_performer_is_good_make_notag(performer):
    con = pymysql.connect(user='root', password="989796", host='localhost', port=3306)
    con.select_db("h_db")
    cur = con.cursor()
    cur.execute("delete from good_performer where name = %s", (performer,))
    con.commit()
    cur.close()
    con.close()

def save_log(log_info):
    print("log---" + log_info)
    time_stamp = time.time()
    local_time = time.localtime(time_stamp)
    file_name = time.strftime("%Y-%m-%d %H:%M:%S", local_time)
    day_name = time.strftime("%Y-%m-%d", local_time)
    with open('./output/log/' + day_name + '.txt', 'a', encoding='utf-8') as f:
        f.write("[" + file_name + ']  ' + log_info + '\n')

def sub2_bt2_func(sub2_text):
    sub2_text.delete(1.0, tk.END)

if __name__ == "__main__":
    gui = GUI()
