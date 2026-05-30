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

from src.test.test import pos_video

empty_book_sheet = ""

# 检查115时的白名单
white_list = ["电脑文件备份", "本地照片视频库", "手机备份", "手机相册"]

# 全局变量
is_add_zzz = False

def txt_to_table(inp_path):
    cookie = {}
    with open(inp_path, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.splitlines()
        for line in lines:
            pos1 = line.find('\t')
            key = line[0:pos1]
            line = line[pos1 + 1:]
            pos2 = line.find('\t')
            value = line[0:pos2]
            cookie[key] = value
            # print(line)
    return cookie


def get_url_txt(url_inp, cookie):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    # 获取源码
    html = requests.get(url_inp, allow_redirects=True, headers=headers, cookies=cookie)
    # 打印源码
    return html.text

def get_url_txt_without_cookie(url_inp):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    # 获取源码
    html = requests.get(url_inp, allow_redirects=True, headers=headers)
    # 打印源码
    return html.text

def get_page_info(min_page_value_in, new_page_value_in):
    # # 1.获取页面
    # root_url = root_url  # 主页面url
    cookie = txt_to_table("./output/youke.txt")
    # real_url_txt = get_url_txt(url_page, cookie)  # 获取页面源码
    # temp_size = len(real_url_txt)
    # if temp_size < 1500:
    #     return 1
    # #xpath_tab = re.findall("normalthread_[0-9]*", real_url_txt)
    # xpath_tab = re.findall("thread-[0-9]*", real_url_txt)

    # 定义最新页面值如：https://dmn12.vip/thread-3340123-1-1.html
    new_page_value = new_page_value_in
    # 定义要遍历到的最小值
    min_page_value = min_page_value_in

    while new_page_value > min_page_value:
        # curr_xpath = "//*[@id=\"" + thread + "\"]/tr/th/a[2]/"  # 当前视频的xpath
        # curr_xpath_name = curr_xpath + "text()"  # 视频的标题，也就是名字
        # curr_xpath_href = curr_xpath + "@href"  # 视频的点进去的链接
        # etree_html = etree.HTML(real_url_txt)  # 解析当前页面
        # next_href = etree_html.xpath(curr_xpath_href)[0]
        # next_name = etree_html.xpath(curr_xpath_name)[0]
        # next_url = root_url + next_href  # 下一级的网页的url
        next_url = "https://plwt.kpqq4.com/thread-" + str(new_page_value) + "-1-1.html"
        new_page_value = new_page_value - 1
        real_url_txt_next = get_url_txt(next_url, cookie)
        mag = re.findall("magnet:\\?xt=urn:btih:[a-zA-Z0-9]+", str(real_url_txt_next))

        pos1 = real_url_txt_next.find("<title>")
        pos2 = real_url_txt_next.find("</title>")
        title = real_url_txt_next[pos1 + 7:pos2]

        # # 找到番号
        pos1 = title.find("[")
        fanhao = title[:pos1 - 1].strip()
        designation = fanhao
        if "无码破解" in title:
            fanhao += "-UC"
        elif "自译征用" in title:
            fanhao += "-C"
        elif "自提征用" in title:
            fanhao += "-C"
        else:
            save_log("当前非中文跳过：" + title)
            continue

        # 找到热度
        hot_num = "0"
        try:
            hot_num = re.findall("热度: [0-9]+", real_url_txt_next)[0][4:]
        except(IndexError):
            pass
        hot_num = int(hot_num)

        # 找到出演演员
        performer = "unknown"
        for line in real_url_txt_next.splitlines():
            if performer != "unknown":
                break
            if "【出演女优】" in line:
                pos_video = line.find("影片容量")  # 查看是否都混到一行了
                pos = line.find("出演女优")
                if pos_video != -1:
                    performer = line[pos + 6:pos_video - 1].strip()
                else:
                    performer = line[7:].strip()[:-6].strip()

        # 找到影片大小
        size = "unknown"
        for line in real_url_txt_next.splitlines():
            if "【影片容量】" in line:
                size = line[7:].strip()[:-6].strip()

        # 是否有码
        mosaic = "unknown"
        for line in real_url_txt_next.splitlines():
            if "【是否有码】" in line:
                mosaic = line[7:].strip()[:-6].strip()

        # 搜集查看量与回复量
        view = "0"
        reply = "0"
        for line in real_url_txt_next.splitlines():
            if "查看:" in line:
                ret = re.findall(">[0-9]+<", line)
                if len(ret) < 2 :
                    break
                view = int(ret[0][1:-1])
                reply = int(ret[1][1:-1])

        # 获取影片的名称
        film_name = "unknown"
        try:
            for line in real_url_txt_next.splitlines():
                if "【影片名称】" in line:
                    film_name = line[7:].strip()[:-6].strip()
        except:
            pass

        # 新增已存在判断


        # 数据库已经稳定，增加新增下载
        try:
            time_stamp = time.time()
            local_time = time.localtime(time_stamp)
            day_name = time.strftime("%Y-%m-%d", local_time)
            with open('./output/magnet/' +  day_name + "-magnet.txt", 'a', encoding='utf-8') as f:
                if "-UC" not in fanhao:
                    if not judge_performer(performer):
                        f.write(mag[0] + '\n')
                    else:
                        save_log("[黑名单]当前演员在黑名单中：" + performer)
                        save_log("[黑名单]此视频不做磁力：" + title)
                else:
                    save_log("[无码]当前视频是无码的：" + performer)
                    save_log("[无码]此视频不做磁力：" + title)
        except:
            pass

        if judge_current_film_is_exist(fanhao):
            save_log("[已存在] 当前影片已存在，不添加：" + fanhao + " 演员为：" + performer + " 影片名称：" + film_name)
            continue

        # 记录当前日志
        save_log("[影片] 当前正在获取：" + fanhao + " 演员为：" + performer + " 影片名称：" + film_name)

        # 保存网页源文件
        try:
            with open('./output/高清中文字幕网页源文件/' + fanhao + '.txt', 'w', encoding='utf-8') as f:
                f.write(real_url_txt_next)
        except:
            pass

        with open('./output/磁力链接.txt', 'a') as f:
            try:
                out = (title + '\n' + mag[0] + '\n')
                link_db_cmd("INSERT INTO av (numbers_name, name, magnet, hot_num, performer, size, mosaic, view, reply, designation, film_name) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                            [fanhao, title, mag[0], hot_num, performer, size, mosaic, view, reply, designation, film_name])
                print(out, file=f)
            except (UnicodeEncodeError):
                print("异常  " + title)
                with open('./output/异常影片/' + fanhao + '.txt', 'w', encoding='utf-8') as f:
                    f.write(real_url_txt_next)
            except (pymysql.err.IntegrityError):
                pass
            except:
                pass

        #time.sleep(0.1)


def get_info_from_url(begin, end, thread_num):
    each_num = (end - begin) // thread_num
    for i in range(thread_num):
        curr_begin = begin + i * each_num
        curr_end = begin + (i + 1) * each_num
        thread = threading.Thread(target=get_page_info, args=(curr_begin, curr_end))
        print("thread:" + str(i) + " begin")
        thread.start()
    #get_page_info(begin, end)

    # for i in tqdm(range(begin, end)):  # 最大页数
    #     curr_url = "https://dmn12.vip/forum-103-" + str(i + 1) + ".html"
    #     save_log("[页面] 当前正在获取页面：" + str(i) + "  url:" + curr_url)
    #     ret = get_page_info(curr_url, "https://dmn12.vip/")
    #     if ret == 1:
    #         print("页面未成功获取！请检查")
    #         return

def save_log(log_info):
    print("log---" + log_info)
    time_stamp = time.time()
    local_time = time.localtime(time_stamp)
    file_name = time.strftime("%Y-%m-%d %H:%M:%S", local_time)
    day_name = time.strftime("%Y-%m-%d", local_time)
    with open('./output/log/' + day_name + '.txt', 'a', encoding='utf-8') as f:
        f.write("[" + file_name + ']  ' + log_info + '\n')

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

# 判断当前演员是否在黑名单中
def judge_performer_make_notag(performer):
    con = pymysql.connect(user='root', password="989796", host='localhost', port=3306)
    con.select_db("h_db")
    cur = con.cursor()
    cur.execute("delete from black_table where name = %s", (performer,))
    con.commit()
    cur.close()
    con.close()

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

# 将白名单演员转为notag
def judge_performer_is_good_make_notag(performer):
    con = pymysql.connect(user='root', password="989796", host='localhost', port=3306)
    con.select_db("h_db")
    cur = con.cursor()
    cur.execute("delete from good_performer where name = %s", (performer,))
    con.commit()
    cur.close()
    con.close()

# 判断当前影片是否已经添加
def judge_current_film_is_exist(numbers_name):
    con = pymysql.connect(user='root', password="989796", host='localhost', port=3306)
    con.select_db("h_db")
    cur = con.cursor()
    cur.execute("select * from av where numbers_name = %s", (numbers_name,))
    curr_record = cur.fetchone()
    if curr_record is not None:
        return True
    return False


def check_designation():
    con = pymysql.connect(user='root', password="989796", host='localhost', port=3306)
    con.select_db("h_db")
    cur = con.cursor()
    cur.execute("select * from av")
    curr_record = cur.fetchone()
    while curr_record is not None:
        temp = list(curr_record)
        true_fanhao = curr_record[9]
        fanhao = curr_record[0]
        ret = re.findall("[0-9a-zA-Z]+-[0-9a-zA-Z]+", true_fanhao)
        if ret == []:
            curr_record = cur.fetchone()
            continue
        ret = ret[0]
        if true_fanhao != ret:
            save_log("[错误]当前番号错误进行修改：" + true_fanhao + "(修改前)-" + ret + "(修改后)")
            temp[9] = ret
            curr_record = cur.fetchone()
            link_db_cmd("update av set designation = %s where numbers_name = %s", (ret, fanhao))
            continue
        curr_record = cur.fetchone()
    cur.close()
    con.close()


def check_115_file_exist(path):
    file_list = os.listdir(path)
    for file in file_list:
        save_log("[文件]正在处理：" + path + file)
        if file in white_list:
            continue
        if os.path.isdir(path + "/" + file):
            check_115_file_exist(path + file + "/")
            continue
        if "-UC" in file:
            continue
        ret = re.findall("[0-9a-zA-Z]+-[0-9a-zA-Z]+", file)
        if ret == []:
            continue
        for temp_ret in ret:
            con = pymysql.connect(user='root', password="989796", host='localhost', port=3306)
            con.select_db("h_db")
            cur = con.cursor()
            cur.execute("select * from av where designation = %s", (temp_ret, ))
            curr_record = cur.fetchone()
            while curr_record is not None:
                link_db_cmd("update av set exist_in_115 = %s where numbers_name = %s", (1, curr_record[0]))
                link_db_cmd("update av set local_path = %s where numbers_name = %s", (path + file, curr_record[0]))
                curr_record = cur.fetchone()
            cur.close()
            con.close()

class sub1_bt1_var:
    def __init__(self):
        self.sub1_bt1_video_path = ""
        self.sub1_bt1_fanhao = ""
        self.sub1_bt1_performer = ""
        self.sub1_bt1_video_name = ""
        self.sub1_bt1_video_key = ""
        self.sub1_bt1_grade = ""
        self.sub1_bt1_mosaic = ""

sub1_bt1_var_instance = sub1_bt1_var()

# 页面1：观看视频
def view_vide():
    sub1_window = tk.Tk()
    sub1_window.title("播放视频")
    sub1_window.geometry("800x400")
    sub1_text = tk.Text(sub1_window, width=75, height=20)
    sub1_text.place(x=200, y=30)
    sub1_text.delete(1.0, tk.END)
    sub1_text.insert(1.0, "番号：" + sub1_bt1_var_instance.sub1_bt1_fanhao + '\n')
    sub1_text.insert(1.0, "演员：" + sub1_bt1_var_instance.sub1_bt1_performer + '\n')
    sub1_text.insert(1.0, "码：" + sub1_bt1_var_instance.sub1_bt1_mosaic + '\n')
    sub1_text.insert(1.0, "影片名称：" + sub1_bt1_var_instance.sub1_bt1_video_name + '\n')
    sub1_text.insert(1.0, "路径：" + sub1_bt1_var_instance.sub1_bt1_video_path + '\n')

    sub1_bt1 = tk.Button(sub1_window, text="nozzz视频",
                         command=lambda :rand_db_no_grade_video(sub1_text, 0), width=10, height=1)
    sub1_bt1.place(x=10, y=10)

    sub1_bt2 = tk.Button(sub1_window, text="随机all视频",
                         command=lambda: rand_db_no_grade_video(sub1_text, 1), width=13, height=1)
    sub1_bt2.place(x=93, y=10)

    # 播放按钮
    sub1_bt2 = tk.Button(sub1_window, text="播放", command=lambda: play_video(sub1_text),
                         width=20, height=1)
    sub1_bt2.place(x=10, y=50)

    sub1_combobox1 = ttk.Combobox(sub1_window, width=7)
    sub1_combobox1.place(x=10, y=90)
    sub1_combobox1['values'] = ("10", "20", "30", "40", "50", "60", "70", "80", "90", "100")
    sub1_combobox1.current(5)

    # 评分按钮
    sub1_bt3 = tk.Button(sub1_window, text="评分", command=lambda: video_grade(sub1_combobox1, sub1_text),
                         width=7, height=1)
    sub1_bt3.place(x=100, y=87)

    # 删除按钮
    sub1_bt3 = tk.Button(sub1_window, text="删除当前视频，并更新数据库", command=lambda: delete_curr_viedo(sub1_text),
                         width=25, height=1)
    sub1_bt3.place(x=10, y=130)

    # 播放好看的视频
    sub1_bt4 = tk.Button(sub1_window, text="播放选择分数之上的随机视频", command=lambda: view_good_video(sub1_combobox1, sub1_text),
                         width=25, height=1)
    sub1_bt4.place(x=10, y=170)

    # 将此演员加入黑名单
    sub1_bt5 = tk.Button(sub1_window, text="将此演员加入黑名单",
                         command=lambda: put_performer_in_black_list(sub1_text),
                         width=25, height=1)
    sub1_bt5.place(x=10, y=210)

    # 将此演员从黑名单删除
    sub1_bt5 = tk.Button(sub1_window, text="将此演员从黑名单删除",
                         command=lambda: put_performer_in_black_list_to_notag(sub1_text),
                         width=25, height=1)
    sub1_bt5.place(x=10, y=240)

    # 将此演员加关注名单
    sub1_bt5 = tk.Button(sub1_window, text="将此演员加入关注名单",
                         command=lambda: put_performer_in_good_list(sub1_text),
                         width=25, height=1)
    sub1_bt5.place(x=10, y=300)

    # 将此演员从白名单移除
    sub1_bt5 = tk.Button(sub1_window, text="将此演员从白名单移除",
                         command=lambda: put_performer_in_good_list_to_notag(sub1_text),
                         width=25, height=1)
    sub1_bt5.place(x=10, y=330)

    return

def put_performer_in_black_list_to_notag(sub1_text):
    curr_per = sub1_bt1_var_instance.sub1_bt1_performer
    if not judge_performer(curr_per):
        sub1_text.insert(tk.INSERT, '当前演员不在黑名单\n')
        return
    judge_performer_make_notag(curr_per)
    sub1_text.insert(tk.INSERT, '已将 ' + curr_per + ' 从黑名单移除\n')
    return

def put_performer_in_good_list_to_notag(sub1_text):
    curr_per = sub1_bt1_var_instance.sub1_bt1_performer
    if not judge_performer_is_good(curr_per):
        sub1_text.insert(tk.INSERT, '当前演员不在白名单\n')
        return
    judge_performer_is_good_make_notag(curr_per)
    sub1_text.insert(tk.INSERT, '已将 ' + curr_per + ' 从白名单移除\n')
    return

# 将此演员加入关注名单
def put_performer_in_good_list(sub1_text):
    curr_per = sub1_bt1_var_instance.sub1_bt1_performer
    if curr_per == "":
        sub1_text.insert(tk.INSERT, '当前演员为空\n')
        return
    if judge_performer_is_good(curr_per):
        sub1_text.insert(tk.INSERT, '当前演员已在关注名单\n')
        return
    link_db_cmd("INSERT INTO good_performer (name) VALUES (%s)", (curr_per, ))
    sub1_text.insert(tk.INSERT, "已将：" + str(curr_per) + ' 加入关注名单\n')

# 将此演员加入黑名单
def put_performer_in_black_list(sub1_text):
    curr_per = sub1_bt1_var_instance.sub1_bt1_performer
    if curr_per == "":
        sub1_text.insert(tk.INSERT, '当前演员为空\n')
        return
    if judge_performer(curr_per):
        sub1_text.insert(tk.INSERT, '当前演员已在黑名单\n')
        return
    link_db_cmd("INSERT INTO black_table (name) VALUES (%s)", (curr_per, ))
    sub1_text.insert(tk.INSERT, "已将：" + str(curr_per) + ' 加入黑名单\n')

# 删除当前视频并更新数据库
def delete_curr_viedo(sub1_text):
    if sub1_bt1_var_instance.sub1_bt1_video_key == "":
        sub1_text.insert(1.0, "路径为空\n")
        return
    link_db_cmd("update av set local_path = NULL where numbers_name = %s",
                (sub1_bt1_var_instance.sub1_bt1_video_key))
    link_db_cmd("update av set exist_in_115 = NULL where numbers_name = %s",
                (sub1_bt1_var_instance.sub1_bt1_video_key))
    if os.path.exists(sub1_bt1_var_instance.sub1_bt1_video_path):
        os.remove(sub1_bt1_var_instance.sub1_bt1_video_path)
        sub1_text.insert(1.0, "删除文件成功\n")
    else:
        sub1_text.insert(1.0, "文件不存在，删除失败\n")

# 播放选择分数之上的随机视频
def view_good_video(sub1_combobox1, sub1_text):
    con = pymysql.connect(user='root', password="989796", host='localhost', port=3306)
    con.select_db("h_db")
    cur = con.cursor()
    ret = sub1_combobox1.get()
    ret = int(ret)
    cur.execute("select * from av where local_path is not null and grade >= %s order by RAND() limit 1", (ret))
    curr_record = cur.fetchone()
    sub1_bt1_var_instance.sub1_bt1_video_key = curr_record[0]
    sub1_bt1_var_instance.sub1_bt1_video_path = curr_record[14]
    sub1_bt1_var_instance.sub1_bt1_fanhao = curr_record[9]
    sub1_bt1_var_instance.sub1_bt1_performer = curr_record[4]
    sub1_bt1_var_instance.sub1_bt1_mosaic = curr_record[6]
    sub1_bt1_var_instance.sub1_bt1_video_name = curr_record[10]
    sub1_bt1_var_instance.sub1_bt1_grade = curr_record[11]
    cur.close()
    con.close()
    sub1_text.delete(1.0, tk.END)
    sub1_text.insert(tk.INSERT, "番号：" + sub1_bt1_var_instance.sub1_bt1_fanhao + '\n')
    sub1_text.insert(tk.INSERT, "演员：" + sub1_bt1_var_instance.sub1_bt1_performer + '\n')
    sub1_text.insert(tk.INSERT, "码：" + sub1_bt1_var_instance.sub1_bt1_mosaic + '\n')
    sub1_text.insert(tk.INSERT, "影片名称：" + sub1_bt1_var_instance.sub1_bt1_video_name + '\n')
    sub1_text.insert(tk.INSERT, "路径：" + sub1_bt1_var_instance.sub1_bt1_video_path + '\n')
    sub1_text.insert(tk.INSERT, "分数：" + str(sub1_bt1_var_instance.sub1_bt1_grade) + '\n')

    # 增加演员在不在黑名单的判断
    if judge_performer(sub1_bt1_var_instance.sub1_bt1_performer):
        sub1_text.insert(tk.INSERT, "[黑名单]当前演员在黑名单中：" + sub1_bt1_var_instance.sub1_bt1_performer + '\n')
    elif judge_performer_is_good(sub1_bt1_var_instance.sub1_bt1_performer):
        sub1_text.insert(tk.INSERT, "[白名单]当前演员在白名单中：" + sub1_bt1_var_instance.sub1_bt1_performer + '\n')
    else:
        sub1_text.insert(tk.INSERT, "[notag]当前演员notag\n")
    return

# 评分函数
def video_grade(sub1_combobox1, sub1_text):
    ret = sub1_combobox1.get()
    ret = int(ret)
    link_db_cmd("update av set grade = %s where numbers_name = %s",
                (ret, sub1_bt1_var_instance.sub1_bt1_video_key))
    sub1_text.insert(1.0, "评分完成\n")

def rand_db_no_grade_video(sub1_text, is_zzz):
    con = pymysql.connect(user='root', password="989796", host='localhost', port=3306)
    con.select_db("h_db")
    cur = con.cursor()
    if is_zzz:
        print("当前zzz为1")
        cur.execute("select * from av where local_path is not null and grade is null order by RAND() limit 1")
    else:
        print("当前zzz为0")
        cur.execute("select * from av where local_path is not null and grade is null and zzz is null order by RAND() limit 1")
    curr_record = cur.fetchone()
    sub1_bt1_var_instance.sub1_bt1_video_key = curr_record[0]
    sub1_bt1_var_instance.sub1_bt1_video_path = curr_record[14]
    sub1_bt1_var_instance.sub1_bt1_fanhao = curr_record[9]
    sub1_bt1_var_instance.sub1_bt1_performer = curr_record[4]
    sub1_bt1_var_instance.sub1_bt1_mosaic = curr_record[6]

    sub1_bt1_var_instance.sub1_bt1_video_name = curr_record[10]

    sub1_text.delete(1.0, tk.END)
    sub1_text.insert(tk.INSERT, "番号：" + sub1_bt1_var_instance.sub1_bt1_fanhao + '\n')
    sub1_text.insert(tk.INSERT, "演员：" + sub1_bt1_var_instance.sub1_bt1_performer + '\n')
    #sub1_text.insert(tk.INSERT, "码：" + sub1_bt1_var_instance.sub1_bt1_mosaic + '\n')
    sub1_text.insert(tk.INSERT, "影片名称：" + sub1_bt1_var_instance.sub1_bt1_video_name + '\n')
    sub1_text.insert(tk.INSERT, "路径：" + sub1_bt1_var_instance.sub1_bt1_video_path + '\n')

    # 查找当前剩余url数量与剩余未评分url数量
    cur.execute("select count(*) from av where local_path is not null")
    curr_record = cur.fetchone()
    sub1_text.insert(tk.INSERT, "剩余本地视频：" + str(curr_record[0]) + '\n')

    cur.execute("select count(*) from av where local_path is not null and grade is null")
    curr_record = cur.fetchone()
    sub1_text.insert(tk.INSERT, "剩余未评分本地视频：" + str(curr_record[0]) + '\n')

    cur.execute("select count(*) from av where local_path is not null and grade is null and zzz is null")
    curr_record = cur.fetchone()
    sub1_text.insert(tk.INSERT, "剩余未评分本地视频（nozzz）：" + str(curr_record[0]) + '\n')

    # 增加演员在不在黑名单的判断
    if judge_performer(sub1_bt1_var_instance.sub1_bt1_performer):
        sub1_text.insert(tk.INSERT, "[黑名单]当前演员在黑名单中：" + sub1_bt1_var_instance.sub1_bt1_performer + '\n')
    elif judge_performer_is_good(sub1_bt1_var_instance.sub1_bt1_performer):
        sub1_text.insert(tk.INSERT, "[白名单]当前演员在白名单中：" + sub1_bt1_var_instance.sub1_bt1_performer + '\n')
    else:
        sub1_text.insert(tk.INSERT, "[notag]当前演员notag\n")
    cur.close()
    con.close()
    return

# 清理数据库
def clean_data_base():
    save_log("[clean_data_base]正在清理视频")
    con = pymysql.connect(user='root', password="989796", host='localhost', port=3306)
    con.select_db("h_db")
    cur = con.cursor()
    cur.execute("select * from av where local_path is not null")
    curr_record = cur.fetchone()
    while curr_record is not None:
        curr_path = curr_record[14]
        curr_name = curr_record[0]
        if curr_path is None:
            curr_record = cur.fetchone()
            continue
        if not os.path.isfile(curr_path):
            link_db_cmd("update av set local_path = NULL where numbers_name = %s", (curr_name))
            link_db_cmd("update av set exist_in_115 = NULL where numbers_name = %s", (curr_name))
            save_log("[清理数据库]【删除】当前路径无效更新数据库：" + curr_path)
        curr_record = cur.fetchone()
    cur.close()
    con.close()

# 双版本视频，不看无码版本
def only_one_video_can_look():
    save_log("[only_one_video_can_look]正在清理无码视频")
    con = pymysql.connect(user='root', password="989796", host='localhost', port=3306)
    con.select_db("h_db")
    cur = con.cursor()
    cur.execute("select * from av where mosaic = %s", "无码")
    curr_record = cur.fetchone()
    while curr_record is not None:
        fanhao = curr_record[9]
        curr_path = curr_record[14]
        curr_name = curr_record[0]
        if curr_path is None:
            curr_record = cur.fetchone()
            continue

        cur2 = con.cursor()
        # 查找当前剩余url数量与剩余未评分url数量
        cur2.execute("select count(*) from av where designation = %s", (fanhao))
        nums = cur2.fetchone()[0]
        cur2.close()

        if nums > 1:
            link_db_cmd("update av set local_path = NULL where numbers_name = %s", (curr_name))
            save_log("[删除无码视频路径]【删除】当前路径无效更新数据库：" + curr_path)

        curr_record = cur.fetchone()

    cur.close()
    con.close()

# 视频提纯，不放在文件夹下，统一大文件夹
def video_to_set_dir(path, dst_path):
    file_list = os.listdir(path)
    for file in file_list:
        save_log("[视频提纯][文件]正在处理：" + path + file)
        if os.path.isdir(path + "/" + file):
            video_to_set_dir(path + file + "/", dst_path)
            continue
        if "mp4" not in file:
            continue
        source_path = path + file
        destination_path = dst_path + file
        shutil.move(source_path, destination_path)
        save_log("[视频提纯]【moving】[源地址]：" + source_path)
        save_log("[视频提纯]【moving】[目的地址]：" + destination_path)


def play_video(sub1_text):
    if not os.path.isfile(sub1_bt1_var_instance.sub1_bt1_video_path):
        link_db_cmd("update av set local_path = NULL where numbers_name = %s",
                    (sub1_bt1_var_instance.sub1_bt1_video_key))
        link_db_cmd("update av set exist_in_115 = NULL where numbers_name = %s",
                    (sub1_bt1_var_instance.sub1_bt1_video_key))
        sub1_text.insert(1.0, "路径下视频不可达，已更新数据库内路径，请检查")
        return
    os.startfile(sub1_bt1_var_instance.sub1_bt1_video_path)
    print(sub1_bt1_var_instance.sub1_bt1_video_path)

def gen_magnet_button(sub2_combobox1, sub2_text):
    con = pymysql.connect(user='root', password="989796", host='localhost', port=3306)
    con.select_db("h_db")
    cur = con.cursor()
    num = sub2_combobox1.get()
    num = int(num)
    cur.execute("select * from av where local_path is null and grade is null and magnet is not null order by RAND() limit %s", (num))
    curr_record = cur.fetchall()
    for record in curr_record:
        if "-UC" in record[0]:
            continue
        if judge_performer(record[4]):
            save_log("[黑名单]当前演员在黑名单中：" + record[4])
            save_log("[黑名单]此视频不做磁力：" + record[0])
            continue
        save_log("[磁力生成]当前视频非黑名单，可以生成磁力，演员：" + record[4] + " --- 影片名称：" + record[0])
        sub2_text.insert(1.0, record[2] + '\n')

def gen_magnet():
    sub2_window = tk.Tk()
    sub2_window.title("生成磁力")
    sub2_window.geometry("800x400")
    sub2_text = tk.Text(sub2_window, width=70, height=5)
    sub2_text.place(x=170, y=10)
    sub2_text.delete(1.0, tk.END)

    sub2_combobox1 = ttk.Combobox(sub2_window, width=10)
    sub2_combobox1.place(x=10, y=90)
    sub2_combobox1['values'] = ("10", "20", "30", "40", "50", "60", "70", "80", "90", "10")
    sub2_combobox1.current(5)

    sub2_bt1 = tk.Button(sub2_window, text="生成磁力(条)",
                         command=lambda: gen_magnet_button(sub2_combobox1, sub2_text), width=20, height=1)
    sub2_bt1.place(x=10, y=10)

    sub2_bt2 = tk.Button(sub2_window, text="清空",
                         command=lambda: sub2_bt2_func(sub2_text), width=20, height=1)
    sub2_bt2.place(x=10, y=50)

def sub2_bt2_func(sub2_text):
    sub2_text.delete(1.0, tk.END)


def gui():
    window = tk.Tk()
    window.title("瑟瑟")
    window.geometry("400x300")
    bt1 = tk.Button(window,
                    text="播放视频",
                    command=view_vide,
                    width=10,
                    height=1)
    bt1.place(x=10, y=10)

    # 批量生成未评分作品
    bt2 = tk.Button(window, text="生成下载视频磁力", command=gen_magnet, width=15, height=1)
    bt2.place(x=100, y=10)
    window.mainloop()

    return

def delete_gabage_file(path):
    file_list = os.listdir(path)
    del_file_name_list = ["x u u 6 2 . c o m.mp4",
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
                          "最 新 位 址 獲 取(1).txt"]
    for file in file_list:
        save_log("[文件]正在处理：" + path + file)
        if file in white_list:
            continue
        if os.path.isdir(path + file ):
            if len(os.listdir(path + file)) == 0:
                save_log("[文件]正在删除：空文件夹-" + path + file)
                os.rmdir(path + file)
                continue
            delete_gabage_file(path + file + "/")
            continue
        size = os.path.getsize(path + file)
        if size < 50000000:
            if os.path.exists(path + file):
                os.remove(path + file)
                save_log("[文件]正在删除：大小小于50M" + path + file)
            else:
                save_log("[文件]文件不存在，删除失败：" + path + file)

        if file in del_file_name_list:
            if os.path.exists(path + file):
                os.remove(path + file)
                save_log("[文件]正在删除：" + path + file)
            else:
                save_log("[文件]文件不存在，删除失败：" + path + file)

def delete_empty_file(path):
    file_list = os.listdir(path)
    for file in file_list:
        save_log("[文件]正在处理：" + path + file)
        if file in white_list:
            continue
        if os.path.isdir(path + file ):
            if len(os.listdir(path + file)) == 0:
                save_log("[文件]正在删除：空文件夹-" + path + file)
                os.rmdir(path + file)
                continue
            delete_empty_file(path + file + "/")
            continue
        # size = os.path.getsize(path + file)
        # if size < 50000000:
        #     if os.path.exists(path + file):
        #         os.remove(path + file)
        #         save_log("[文件]正在删除：大小小于50M" + path + file)
        #     else:
        #         save_log("[文件]文件不存在，删除失败：" + path + file)

def delete_small_file(path, size_inp):
    file_list = os.listdir(path)
    for file in file_list:
        save_log("[文件]正在处理：" + path + file)
        if file in white_list:
            continue
        if os.path.isdir(path + file ):
            if len(os.listdir(path + file)) == 0:
                continue
            delete_small_file(path + file + "/")
            continue
        size = os.path.getsize(path + file)
        if size < size_inp * 1000000:
            if os.path.exists(path + file):
                os.remove(path + file)
                save_log("[文件]正在删除：大小小于50M" + path + file)
            else:
                save_log("[文件]文件不存在，删除失败：" + path + file)

def rename_file(path):
    file_list = os.listdir(path)
    for file in file_list:
        save_log("[文件][重命名]正在处理：" + path + file)
        if os.path.isdir(path + file ):
            rename_file(path + file + "/")
            continue
        ret = re.findall("[0-9a-zA-Z]+-[0-9a-zA-Z]+", path)
        if ret == []:
            continue
        for temp_ret in ret:
            con = pymysql.connect(user='root', password="989796", host='localhost', port=3306)
            con.select_db("h_db")
            cur = con.cursor()
            cur.execute("select * from av where designation = %s", (temp_ret, ))
            curr_record = cur.fetchone()
            while curr_record is not None:
                new_name = curr_record[9] + "-" + curr_record[4] + "-" + curr_record[6] + "-" + curr_record[10] + ".mp4"
                save_log("[文件][重命名]正在重命名：" + path + file + " 到-》" + path + new_name)
                try:
                    os.rename(path + file, path + new_name)
                except:
                    pass
                curr_record = cur.fetchone()
            cur.close()
            con.close()

# 判断当前视频是外部视频，额外适配
def other_video(path):
    file_list = os.listdir(path)
    for file in file_list:
        cur_file_path = path + file

        con = pymysql.connect(user='root', password="989796", host='localhost', port=3306)
        con.select_db("h_db")
        cur = con.cursor()
        cur.execute("select * from av where local_path = %s", (cur_file_path, ))
        curr_record = cur.fetchone()
        cur.close()

        if curr_record is not None:
            continue

        save_log("[外部视频适配]当前视频数据库内没有，正在添加：" + cur_file_path)
        cur = con.cursor()
        cur.execute("select count(*) from av where zzz is not null")
        numbers = cur.fetchone()[0]
        cur.close()

        numbers_name = "zzz-" + str(numbers + 1)
        os.rename(cur_file_path, path + numbers_name + " " + file)
        new_path = path + numbers_name + " " + file

        zzz = numbers + 1
        name = file
        performer = "zzz"
        mosaic = "有码"
        designation = numbers_name
        file_name = numbers_name
        local_path = new_path

        link_db_cmd(
            "INSERT INTO av (numbers_name, name, performer, mosaic, designation, film_name, local_path, zzz) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            [numbers_name, name, performer, mosaic, designation, file_name, local_path, zzz])

        cur.close()

# 删除黑名单人视频
def delete_black_video():
    con = pymysql.connect(user='root', password="989796", host='localhost', port=3306)
    con.select_db("h_db")
    cur = con.cursor()
    cur.execute("select * from black_table")
    curr_record = cur.fetchone()
    while curr_record is not None:
        name = curr_record[0]
        cur2 = con.cursor()
        cur2.execute("select * from av where performer=%s", (name,))
        curr2 = cur2.fetchone()
        while curr2 is not None:
            key = curr2[0]
            path = curr2[14]
            film_name = curr2[1]
            if path is None:
                curr2 = cur2.fetchone()
                continue
            curr2 = cur2.fetchone()
            save_log("[删除！！！！]当前演员为黑名单演员：" + name)
            save_log("[删除！！！！]正在删除：" + film_name)
            link_db_cmd("update av set local_path = NULL where numbers_name = %s",
                        (key))
            link_db_cmd("update av set exist_in_115 = NULL where numbers_name = %s",
                        (key))
            if os.path.exists(path):
                os.remove(path)
            save_log("【删除完成】：" + film_name)
        cur2.close()
        curr_record = cur.fetchone()
    cur.close()
    con.close()

# 删除低分视频
def delete_low_grade_video(grade):
    con = pymysql.connect(user='root', password="989796", host='localhost', port=3306)
    con.select_db("h_db")
    cur = con.cursor()
    cur.execute("select * from av where grade <= %s and local_path is not NULL", (grade,))
    curr_record = cur.fetchone()
    while curr_record is not None:
        key = curr_record[0]
        path = curr_record[14]
        film_name = curr_record[1]
        save_log("[删除！！！！]当前删除低于分：" + str(grade) + " video")
        save_log("[删除！！！！]正在删除：" + film_name + " point:" + str(curr_record[11]))
        link_db_cmd("update av set local_path = NULL where numbers_name = %s",
                    (key))
        link_db_cmd("update av set exist_in_115 = NULL where numbers_name = %s",
                    (key))
        if os.path.exists(path):
            os.remove(path)
        save_log("【删除完成】：" + film_name)
        curr_record = cur.fetchone()

        # name = curr_record[0]
        # cur2 = con.cursor()
        # cur2.execute("select * from av where performer=%s", (name,))
        # curr2 = cur2.fetchone()
        # while curr2 is not None:
        #     key = curr2[0]
        #     path = curr2[14]
        #     film_name = curr2[1]
        #     if path is None:
        #         curr2 = cur2.fetchone()
        #         continue
        #     curr2 = cur2.fetchone()
        #     save_log("[删除！！！！]当前演员为黑名单演员：" + name)
        #     save_log("[删除！！！！]正在删除：" + film_name)
        #     link_db_cmd("update av set local_path = NULL where numbers_name = %s",
        #                 (key))
        #     link_db_cmd("update av set exist_in_115 = NULL where numbers_name = %s",
        #                 (key))
        #     if os.path.exists(path):
        #         os.remove(path)
        #     save_log("【删除完成】：" + film_name)
        # cur2.close()
        # curr_record = cur.fetchone()
    cur.close()
    con.close()

# 关键词删除
def keyword_delete_video(keyword):
    con = pymysql.connect(user='root', password="989796", host='localhost', port=3306)
    con.select_db("h_db")
    cur = con.cursor()
    keyword = '%' + keyword + '%'
    cur.execute("select * from av where name like %s", (keyword,))
    curr_record = cur.fetchone()
    while curr_record is not None:
        if curr_record[14] is None:
            curr_record = cur.fetchone()
            continue
        path = curr_record[14]
        numbers_name = curr_record[0]
        save_log("[删除！！！！]正在删除：" + path)
        link_db_cmd("update av set local_path = NULL where numbers_name = %s",
                    (numbers_name))
        link_db_cmd("update av set exist_in_115 = NULL where numbers_name = %s",
                    (numbers_name))
        if os.path.exists(path):
            os.remove(path)
        save_log("【删除完成】：" + path)
        curr_record = cur.fetchone()
    cur.close()
    con.close()

def bookget_book_main_url_get(sub_url, num):
    p = 1
    name = ""
    while True:
        curr_url = sub_url + "&p=" + str(p)
        current_text = ""
        try:
            current_text = get_url_txt_without_cookie(curr_url)
        except:
            save_log("[error] url:" + curr_url)
        lines_num = len(current_text.splitlines())
        if lines_num < 20:
            break
        p += 1

        # 获取名字
        for line in current_text.splitlines():
            left = line.find("《")
            right = line.find("》")
            name = line[left + 1 :right]
            break

        # 获取作者
        writer = current_text.splitlines()[1][3:].strip()

        # 创建目录
        time_stamp = time.time()
        local_time = time.localtime(time_stamp)
        day_name = time.strftime("%Y%m%d", local_time)
        if not os.path.isdir(".//output//book//" + day_name):
            os.mkdir(".//output//book//" + day_name)

        # 写入本地
        with open(".//output//book//" + day_name + "//" + str(num) + "-" + name + "-" + writer + ".txt", "a", encoding="utf-8") as f:
            f.write(current_text + "\n")

    #current_text = get_url_txt_without_cookie(sub_url)

    return

def bookget(root_url, page_num, start_page):
    save_log("[func] bookget begin..")
    current_url_inp = root_url
    i = start_page
    while i < page_num:
        bookget_book_main_url_get(root_url + "txt/?id=" + str(i), i)
        i += 1

    # current_text = get_url_txt_without_cookie(current_url_inp)
    # print(current_text)
    save_log("[func] bookget end.")

if __name__ == "__main__":
    # 1:gui , 2:刷新数据库中视频路径（更新） 3：爬取网页 4：检查数据库表项中番号等 5：删除指定路径垃圾文件
    # 6：重命名视频文件
    mode = 5
    is_add_zzz = False
    # gui画面
    if mode == 1:
        t = threading.Thread(target=gui, args=())
        t.start()

    # 判断115视频文件是否在数据库中,更新可刷新的视频
    if mode == 2:
        check_115_file_exist('Z:/115open/Hp/')
        only_one_video_can_look()
        other_video('Z:/115open/Hp/')
        #check_115_file_exist('Y:/sata1-15751829753/H/')
        #check_115_file_exist('Y:/nvme11-15751829753/')

    # 读取网页，生成的磁力文档，当前不会生成UC
    if mode == 3:
        save_log("\n\n\n\n\n\n\n\n\n\n\n\n\n")
        save_log("[指令]开始进行获取")
        get_info_from_url(3369770,3380551, 10)

    # sudugu小说
    if mode == 10:
        save_log("mode = 10, 小说获取中=")
        bookget("https://www.sudugu.org/", 99999, 45)

    # 检查表项,历史问题，新磁力不需整理
    if mode == 4:
        check_designation()

    # 删除垃圾文件
    if mode == 5:
        #keyword_delete_video("猫步毒药")
        delete_black_video()
        delete_low_grade_video(50)
        #delete_gabage_file('Z:/115open/云下载/')
        #delete_empty_file('Z:/115open/H/')

    # 日常清理数据库，删除无码视频
    if mode == 6:
        clean_data_base()
        only_one_video_can_look()

    # 云下载整理并刷新
    if mode == 7:
        save_log("[next]正在删除垃圾文件")
        delete_gabage_file('Z:/115open/云下载/')
        save_log("[next]正在重命名文件")
        rename_file('Z:/115open/云下载/')
        save_log("[next]开始搬运到Hp内")
        video_to_set_dir("Z:/115open/云下载/", "Z:/115open/Hp/")
        save_log("[next]打扫云下载")
        delete_empty_file('Z:/115open/云下载/')
        save_log("[next]录制115")
        check_115_file_exist('Z:/115open/Hp/')
        #only_one_video_can_look()
        delete_black_video()



    if mode == 8:
        video_to_set_dir("Z:/115open/H/", "Z:/115open/Hp/")

    # try:
    #     link_db_insert("INSERT INTO av (numbers_name, name, magnet) VALUES (%s, %s, %s)", ["aaa", "name_aaa", "magnetaaa"])
    # except (pymysql.err.IntegrityError):
    #     print("aaa加入db失败，因为已经有了")
    #     pass
    # with open('./output/磁力链接.txt', 'r', encoding='utf-8') as f:
    #     lines = f.read()
    #     for line in lines:
    #         line = line.de
    #         print(line)