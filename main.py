# 校园广播站音频处理系统

import _thread as thread
import re
import logging
import datetime
import os
import random
import time

import dashscope
import base64
import hashlib
import hmac
import json
import ssl
import websocket
import requests
import platform

import wsgiref.handlers
from pydub import AudioSegment
from http import HTTPStatus
from time import mktime
from urllib.parse import urlencode
from urllib.parse import urlparse

if platform.system() == 'Windows':
    from pywebio.input import *
    from pywebio.output import *

# 设置日志级别
logging.basicConfig(level=logging.DEBUG)

# 设置日志格式
formatter = logging.Formatter('DEBUG: %(message)s')

# 获取根记录器
root_logger = logging.getLogger()

# 移除所有现有的处理程序
root_logger.handlers = []

# 创建一个新的处理程序并设置格式
handler = logging.StreamHandler()
handler.setFormatter(formatter)

# 将处理程序添加到根记录器
root_logger.addHandler(handler)


def custom_print(msg):
    if platform.system() == 'Windows':
        def windows_popup():
            popup("提示", msg)
            time.sleep(1.5)

        windows_popup()
    else:
        print(msg)


def custom_put_text(msg):
    if platform.system() == 'Windows':
        def windows_popup():
            # 获取或创建一个名为'popup_scope'的scope
            with use_scope('popup_scope', clear=True):  # 清除并进入scope
                clear()
                put_text(msg)
                time.sleep(1.5)

        windows_popup()
    else:
        print(msg)


def get_audio_duration(file_path):
    # 加载音频文件
    audio = AudioSegment.from_file(file_path)

    # 获取音频时长（以毫秒为单位）
    duration_in_ms = len(audio)

    # 将毫秒转换为分钟、秒、毫秒
    minutes, seconds = divmod(duration_in_ms // 1000, 60)

    # 返回格式化后的字符串
    return f"{minutes:02d}:{seconds:02d}.{duration_in_ms % 1000:03d}"


# 获取当前时间
current_time = datetime.datetime.now()

# 格式化时间为指定格式
formatted_time = current_time.strftime("%a, %d %b %Y %H:%M:%S GMT")

# 获取明天的日期并格式化
tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
formatted_tomorrow_date = tomorrow.strftime('%y%m%d')

# 输出格式化后的时间
print("程序运行 Date:", formatted_time)

# 选择一言生成模型 可选qianwen xinghuo 否则使用公共API获取
use_model = ""

qianwenapi = ""

# xinghuo api
appid = ""
api_secret = ""
api_key = ""

# 程序初始化 获取API
if platform.system() == 'Windows':

    choice = select("请选择一言生成API：", ["通义千问", "讯飞星火大模型", "公共API"])

    if choice == "通义千问":
        popup('你选择了 通义千问API', '请在下方输入在控制台获取的API 格式为sk-xxx')
        qianwenapi = input("请输入通义千问API")
        use_model = "qianwen"
    elif choice == "讯飞星火大模型":
        popup('你选择了 讯飞星火大模型API', '请在下方输入在控制台获取的密钥信息 共三条')
        appid = input("请输入APPID 信息")
        api_secret = input("请输入APISecret 信息")
        api_key = input("请输入APIKey 信息")
        use_model = "xinghuo"
    else:
        use_model = ""
else:
    choice = input("请选择一言生成API（通义千问：1；讯飞星火大模型：2；公共API：3）：")

    if choice == "1":
        print('你选择了 通义千问API 请输入在控制台获取的API 格式为sk-xxx')
        qianwenapi = input("请输入通义千问API")
        use_model = "qianwen"
    elif choice == "2":
        print('你选择了 讯飞星火大模型API 请在输入在控制台获取的密钥信息 共三条')
        appid = input("请输入APPID 信息")
        api_secret = input("请输入APISecret 信息")
        api_key = input("请输入APIKey 信息")
    else:
        use_model = ""

# 获取运行目录下"夜自修前"文件夹内的所有mp3文件，并按照用户输入的顺序排列
audio_files = sorted([os.path.join("夜自修前", f) for f in os.listdir("夜自修前") if f.endswith('.mp3')])
sorted_audio_files_before = []

if len(audio_files) == 1:
    # 如果只有一个文件，则直接拼接
    custom_print("目录下只有一首音频文件，直接拼接")
    sorted_audio_files_before.append(audio_files[0])
    audio_segment = AudioSegment.from_file(audio_files[0])
    combined_audio = audio_segment.set_frame_rate(44100)
else:
    file_orders = []

    for index, audio_file in enumerate(audio_files):
        custom_put_text(f"这是第{index + 1}个音频文件：{audio_file}")
        user_input = int(input(f"请输入这个文件在最终音频中的顺序（例如：如果是第1个，请输入1）："))
        file_orders.append((user_input - 1, audio_file))  # 转换为0索引

    custom_put_text("开始处理")

    # 按照用户指定的顺序对音频文件列表排序
    sorted_audio_files_before = [audio_file for order, audio_file in sorted(file_orders)]

    # 拼接音频
    combined_audio = AudioSegment.empty()
    for audio_file in sorted_audio_files_before:
        audio_part = AudioSegment.from_file(audio_file)
        combined_audio += audio_part

# # 测试代码
# # 加载两个音频文件
# audio_1 = AudioSegment.from_file("夜自修前/南极白熊 - 蝉证序.mp3")
# audio_2 = AudioSegment.from_file("夜自修前/熊大 (配音：张伟),熊二 (配音：张秉君),光头强 (配音：谭笑) - 再次与你同行.mp3")
#
# # 拼接两段音频
# combined_audio = audio_1 + audio_2

# 设置输出的采样率为44100Hz（如果原始音频不是这个采样率，将会重新采样）
out_audio = combined_audio.set_frame_rate(44100)

# 拼接最终输出文件名
output_filename_prefix = f"{formatted_tomorrow_date} 夜自修前-"

# output_filenames = []
#
# for file in sorted_audio_files_later:
#     # 使用 os.path.splitext 获取不带扩展名的文件名
#     filename = os.path.splitext(os.path.basename(file))[0].replace('.mp3', '').split(" - ")[-1]
#
#     # 将非中文、英文和空格字符(非法字符)替换为"_"
#     cleaned_name = re.sub(r'[^\u4e00-\u9fa5a-zA-Z\s]', '_', filename)
#     output_filenames.append(cleaned_name)

output_filenames = [re.sub(r'[^\u4e00-\u9fa5a-zA-Z\s]', '_',
                           os.path.splitext(os.path.basename(file))[0].replace('.mp3', '').split(" - ")[-1]) for file in
                    sorted_audio_files_before]

# 将多个音频文件名连接起来
joined_output_name = output_filename_prefix + '-'.join(output_filenames) + ".mp3"

# 音量调整为-4dB，并输出合并后的音频文件
out_file = joined_output_name
out_audio.export(out_file, format="mp3", parameters=["-af", "volume=-4dB"])

# # 音量调整为-4dB，并输出合并后的音频文件
# out_file = "output.mp3"
# out_audio.export(out_file, format="mp3", parameters=["-af", "volume=-4dB"])

logging.debug(f"Combined audio exported to {out_file}")

before_music_time = get_audio_duration(out_file)

# 获取运行目录下"夜自修后"文件夹内的所有mp3文件，并按照用户输入的顺序排列
audio_files = sorted([os.path.join("夜自修后", f) for f in os.listdir("夜自修后") if f.endswith('.mp3')])
sorted_audio_files_after = []

if len(audio_files) == 1:
    # 如果只有一个文件，则直接拼接
    custom_print("目录下只有一首音频文件，直接拼接")
    sorted_audio_files_after.append(audio_files[0])
    audio_segment = AudioSegment.from_file(audio_files[0])
    combined_audio = audio_segment.set_frame_rate(44100)
else:
    file_orders = []

    for index, audio_file in enumerate(audio_files):
        custom_put_text(f"这是第{index + 1}个音频文件：{audio_file}")
        user_input = int(input(f"请输入这个文件在最终音频中的顺序（例如：如果是第1个，请输入1）："))
        file_orders.append((user_input - 1, audio_file))  # 转换为0索引

    custom_put_text("开始处理")

    # 按照用户指定的顺序对音频文件列表排序
    sorted_audio_files_after = [audio_file for order, audio_file in sorted(file_orders)]

    # 拼接音频
    combined_audio = AudioSegment.empty()
    for audio_file in sorted_audio_files_after:
        audio_part = AudioSegment.from_file(audio_file)
        combined_audio += audio_part

# 设置输出的采样率为44100Hz（如果原始音频不是这个采样率，将会重新采样）
out_audio = combined_audio.set_frame_rate(44100)

# 获取明天的日期并格式化
tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
formatted_tomorrow_date = tomorrow.strftime('%y%m%d')

# 拼接最终输出文件名
output_filename_prefix = f"{formatted_tomorrow_date} 夜自修前-"

# output_filenames = []
#
# for file in sorted_audio_files_before:
#     # 使用 os.path.splitext 获取不带扩展名的文件名
#     filename = os.path.splitext(os.path.basename(file))[0].replace('.mp3', '').split(" - ")[-1]
#
#     # 将非中文、英文和空格字符(非法字符)替换为"_"
#     cleaned_name = re.sub(r'[^\u4e00-\u9fa5a-zA-Z\s]', '_', filename)
#     output_filenames.append(cleaned_name)

output_filenames = [re.sub(r'[^\u4e00-\u9fa5a-zA-Z\s]', '_',
                           os.path.splitext(os.path.basename(file))[0].replace('.mp3', '').split(" - ")[-1]) for file in
                    sorted_audio_files_after]

# 将多个音频文件名连接起来
joined_output_name = output_filename_prefix + '-'.join(output_filenames) + ".mp3"

# 音量调整为-4dB，并输出合并后的音频文件
out_file = joined_output_name
out_audio.export(out_file, format="mp3", parameters=["-af", "volume=-4dB"])

# # 音量调整为-4dB，并输出合并后的音频文件
# out_file = "output.mp3"
# out_audio.export(out_file, format="mp3", parameters=["-af", "volume=-4dB"])

logging.debug(f"Combined audio exported to {out_file}")

after_music_time = get_audio_duration(out_file)

# def get_max_dB(input_file):
#     # Load the audio file
#     audio = AudioSegment.from_file(input_file)
#
#     # Calculate the maximum dBFS (decibels full scale) level
#     max_dBFS = audio.max_dBFS
#
#     custom_print(f"Maximum dBFS level: {max_dBFS} dBFS")
#
# # Replace 'input_audio.wav' with your file path
# get_max_dB('output.mp3')

before_song = []
# 遍历询问夜自修前每一首歌是谁点的，默认是 "每日推荐"
if len(sorted_audio_files_before) > 0:

    # 遍历询问每一首歌是谁点的，默认是 "每日推荐"
    for index, audio_file in enumerate(sorted_audio_files_before):
        user_input = input(f"请问 {audio_file} 是谁点的？（默认是 '每日推荐'）：")
        artist_name = user_input.strip() if user_input else "每日推荐"

        # 获取歌曲信息
        filename = os.path.splitext(os.path.basename(audio_file))[0].replace('.mp3', '').split(" - ")[-1]

        # 输出歌曲信息
        before_song.append(f"\n{os.path.splitext(os.path.basename(audio_file))[0].replace('.mp3', '')} - {artist_name}\n")

after_song = []
# 遍历询问夜自修后每一首歌是谁点的，默认是 "每日推荐"
if len(sorted_audio_files_after) > 0:

    # 遍历询问每一首歌是谁点的，默认是 "每日推荐"
    for index, audio_file in enumerate(sorted_audio_files_after):
        user_input = input(f"请问 {audio_file} 是谁点的？（默认是 '每日推荐'）：")
        artist_name = user_input.strip() if user_input else "每日推荐"

        # 获取歌曲信息
        filename = os.path.splitext(os.path.basename(audio_file))[0].replace('.mp3', '').split(" - ")[-1]

        # 输出歌曲信息
        after_song.append(f"\n{os.path.splitext(os.path.basename(audio_file))[0].replace('.mp3', '')} - {artist_name}\n")

temp_text = ""


def get_a_word_from_aliyun():
    messages = [{'role': 'system',
                 'content': 'You are a sentence generator, please output the content I want directly, do not output '
                            'any extra content, only output one sentence at a time.'},
                {'role': 'user', 'content': '写一句一言 用中文 两个小句子以上 要有创新 有深度 只要一句 一行输出'}]
    # noinspection PyTypeChecker
    response = dashscope.Generation.call(
        dashscope.Generation.Models.qwen_turbo,
        messages=messages,
        # set the random seed, optional, default to 1234 if not set
        seed=random.randint(1, 10000),
        result_format='message',  # set the result to be "message" format.
        api_key='sk-xxx'  # 此处填写自己的APIKey
    )
    if response.status_code == HTTPStatus.OK:
        # custom_print(response)
        content = response['output']['choices'][0]['message']['content']
        return content
    else:
        custom_print('Request id: %s, Status code: %s, error code: %s, error message: %s' % (
            response.request_id, response.status_code,
            response.code, response.message
        ))
        return None


answer = ""


class Ws_Param(object):
    # 初始化
    def __init__(self, APPID, APIKey, APISecret, Spark_url):
        self.APPID = APPID
        self.APIKey = APIKey
        self.APISecret = APISecret
        self.host = urlparse(Spark_url).netloc
        self.path = urlparse(Spark_url).path
        self.Spark_url = Spark_url

    # 生成url
    def create_url(self):
        # 生成RFC1123格式的时间戳
        now = datetime.datetime.now()
        date = wsgiref.handlers.format_date_time(mktime(now.timetuple()))

        # 拼接字符串
        signature_origin = "host: " + self.host + "\n"
        signature_origin += "date: " + date + "\n"
        signature_origin += "GET " + self.path + " HTTP/1.1"

        # 进行hmac-sha256进行加密
        signature_sha = hmac.new(self.APISecret.encode('utf-8'), signature_origin.encode('utf-8'),
                                 digestmod=hashlib.sha256).digest()

        signature_sha_base64 = base64.b64encode(signature_sha).decode(encoding='utf-8')

        authorization_origin = (f'api_key="{self.APIKey}", algorithm="hmac-sha256", headers="host date request-line", '
                                f'signature="{signature_sha_base64}"')

        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')

        # 将请求的鉴权参数组合为字典
        v = {
            "authorization": authorization,
            "date": date,
            "host": self.host
        }
        # 拼接鉴权参数，生成url
        url = self.Spark_url + '?' + urlencode(v)
        # 此处打印出建立连接时候的url,参考本demo的时候可取消上方打印的注释，比对相同参数时生成的url与自己代码生成的url是否一致
        return url


# 收到websocket错误的处理
def on_error(ws, error):
    pass


# 收到websocket关闭的处理
def on_close(ws, one, two):
    custom_print(" ")


# 收到websocket连接建立的处理
def on_open(ws):
    thread.start_new_thread(run, (ws,))


def run(ws, *args):
    data = json.dumps(gen_params(appid=ws.appid, domain=ws.domain, question=ws.question))
    ws.send(data)


# 收到websocket消息的处理
result = ""


def on_message(ws, message):
    global result  # 声明在此函数中使用的是全局变量 result
    data = json.loads(message)
    code = data['header']['code']
    if code != 0:
        custom_print(f'请求错误: {code}, {data}')
        ws.close()
    else:
        choices = data["payload"]["choices"]
        status = choices["status"]
        content = choices["text"][0]["content"]
        result += content  # 累积结果
        if status == 2:
            ws.close()


def gen_params(appid, domain, question):
    """
    通过appid和用户的提问来生成请参数
    """
    data = {
        "header": {
            "app_id": appid,
            "uid": "1234"
        },
        "parameter": {
            "chat": {
                "domain": domain,
                "temperature": 0.5,
                "max_tokens": 2048
            }
        },
        "payload": {
            "message": {
                "text": question
            }
        }
    }
    return data


def main(appid, api_key, api_secret, Spark_url, domain, question):
    wsParam = Ws_Param(appid, api_key, api_secret, Spark_url)
    websocket.enableTrace(False)
    wsUrl = wsParam.create_url()
    ws = websocket.WebSocketApp(wsUrl, on_message=on_message, on_error=on_error, on_close=on_close, on_open=on_open)
    ws.appid = appid
    ws.question = question
    ws.domain = domain
    ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
    return result


# 用于配置大模型版本
domain = "generalv3.5"  # v3.5版本
# 云端环境的服务地址
Spark_url = "ws://spark-api.xf-yun.com/v3.5/chat"

text = []


# length = 0

def getText(role, content):
    jsoncon = {"role": role, "content": content}
    text.append(jsoncon)
    return text


def getlength(text):
    length = 0
    for content in text:
        temp = content["content"]
        leng = len(temp)
        length += leng
    return length


def checklen(text):
    while getlength(text) > 8000:
        del text[0]
    return text


# 调用函数 获取一言
if use_model == "qianwen":
    temp_text = get_a_word_from_aliyun()
elif use_model == "xinghuo":
    text.clear()
    Input = "写一句一言 用中文 两个小句子以上 要有创新 有深度 只要一句 一行输出"
    question = checklen(getText("user", Input))
    answer = (
        "You are a sentence generator, please output the content I want directly, do not output any extra content, "
        "only output one sentence at a time.")
    temp_text = main(appid, api_key, api_secret, Spark_url, domain, question)
    getText("assistant", answer)
else:
    # 默认调用API来获取一句一言
    # 发送GET请求
    response = requests.get('https://v1.hitokoto.cn/?c=f&encode=text')

    # 检查请求是否成功
    if response.status_code == 200:
        # 获取并保存响应内容到变量中
        content = response.text
        temp_text = content
    else:
        custom_print(f"请求失败，状态码：{response.status_code}")

custom_print("以下为示例推送内容：\n")

# 清空文本
custom_put_text('')

# 获取今天的日期并格式化
today = datetime.datetime.now()
formatted_today_date = today.strftime('%y/%m/%d')

# 定义要倒计时的事件和日期（以字典形式存储）
events = {
    "2024 春节": "2024-02-10",
    "寒假开始": "2024-02-02",
    "浙江省2024年初中学业水平考试": "2024-02-26",
    "2025 年": "2025-01-01"
}

events_list = []

# 计算并输出倒计时信息
for event_name, event_date_str in events.items():
    # 将日期字符串转换为datetime对象
    event_date = datetime.datetime.strptime(event_date_str, "%Y-%m-%d")

    days_to_event = (event_date - today).days

    if days_to_event > 0:
        events_list.append(f"距 {event_name} 还有 {days_to_event} 天\n")

# 获取明天的日期并格式化
tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
formatted_tomorrow_date = tomorrow.strftime('%y/%m/%d')
day_of_week = tomorrow.strftime('%A')

# 映射英文星期到中文
weekday_translation = {
    'Monday': '周一',
    'Tuesday': '周二',
    'Wednesday': '周三',
    'Thursday': '周四',
    'Friday': '周五'
    # 周末不放歌 没有实际作用
    # 'Saturday': '周六',
    # 'Sunday': '周日'
}

# 获取中文星期
chinese_day_of_week = weekday_translation.get(day_of_week, day_of_week)

markdown_content = f"""

## 今天是 {formatted_today_date}

### 一言
{temp_text}

{' '.join(events_list)}

### {formatted_tomorrow_date} {chinese_day_of_week}

### 中午放学

午餐提示 固定

### 夜自修前

{' '.join(before_song)}  
注：标准化为 -4dB 时间为：{before_music_time}

### 夜自修后

{' '.join(after_song)}  
注：标准化为 -4dB 时间为：{after_music_time}

https://blog.lao-shui.top/

"""

if platform.system() == 'Windows':
    put_markdown(markdown_content)
else:
    print(f"\n今天是 {formatted_today_date} \n")

    for events in events_list:
        print(events)

    print(f"一言\n{temp_text}")

    # 输出日期和星期
    print(f"\n{formatted_tomorrow_date} {chinese_day_of_week}")

    # 中午放学
    print("\n中午放学\n")

    print("午餐提示 固定\n")

    # 夜自修前
    print("夜自修前")

    # 打印夜自修前歌单
    for song in before_song:
        print(song, end=' ')

    print(f"\n注：标准化为 -4dB 时间为:{before_music_time}\n")

    # 夜自修后
    print("夜自修后")

    # 打印夜自修后歌单
    for song in after_song:
        print(song, end=' ')

    print(f"\n注：标准化为 -4dB 时间为:{after_music_time}\n")

    # 输出相关网站链接
    print("https://blog.lao-shui.top/\n")
