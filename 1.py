import requests
import time
import re
from datetime import datetime

# ==========================================
# 1. 用户配置区 (请在此处填写你的参数)
# ==========================================

# 目标视频的 BV 号
BVID = "BV1Y26wBcERw"

# 你的账号鉴权信息 (抓包获取，必须填写)
SESSDATA = ""# Cookie中的SESSDATA字段
CSRF = ""  # Cookie中的bili_jct字段

# 评论的模板配置
# 将模板拆分为“前缀”和“后缀”，中间夹着我们要递增的数字
# 例如：唤炽心无双，（670/1000）秋同所向，一弦一调唤知己，山海风流鸣笙簧，乐鸣东方！
PREFIX = "唤炽心无双，（"
SUFFIX = "/1000）秋同所向，一弦一调唤知己，山海风流鸣笙簧，乐鸣东方！"

# 循环执行的间隔时间 (单位：小时)
INTERVAL_HOURS = 24 

# 进度上限 (当发送的数字大于此数字时，终止脚本)
MAX_LIMIT = 1000

# ==========================================
# 2. 核心逻辑功能区
# ==========================================

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
    'Cookie': f'SESSDATA={SESSDATA}; bili_jct={CSRF}'
}

def get_video_info(bvid):
    """根据 BV 号获取 aid 和 标题"""
    url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
    try:
        res = requests.get(url, headers=HEADERS).json()
        if res.get('code') == 0:
            aid = res['data']['aid']
            title = res['data']['title']
            return aid, title
        else:
            print(f"获取视频信息失败: {res.get('message')}")
            return None, None
    except Exception as e:
        print(f"网络请求错误: {e}")
        return None, None

def get_latest_comments(aid):
    """获取最新10条评论（按时间排序 sort=0）"""
    url = f"https://api.bilibili.com/x/v2/reply?type=1&oid={aid}&sort=0&ps=10&pn=1"
    try:
        res = requests.get(url, headers=HEADERS).json()
        comments = []
        if res.get('code') == 0 and 'replies' in res['data'] and res['data']['replies']:
            for reply in res['data']['replies']:
                comments.append(reply['content']['message'])
        return comments
    except Exception as e:
        print(f"获取评论区失败: {e}")
        return []

def post_comment(aid, message):
    """发送评论"""
    url = "https://api.bilibili.com/x/v2/reply/add"
    data = {
        'type': 1,
        'oid': aid,
        'message': message,
        'plat': 1,  # 1表示Web端
        'csrf': CSRF
    }
    try:
        res = requests.post(url, headers=HEADERS, data=data).json()
        return res
    except Exception as e:
        return {'code': -1, 'message': str(e)}

def log_action(content):
    """记录行为到本地 txt 留档"""
    log_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{log_time}] {content}"
    print(log_entry)
    with open("comment_record.txt", "a", encoding="utf-8") as f:
        f.write(log_entry + "\n")

# ==========================================
# 3. 主程序循环
# ==========================================

def main():
    print(f"正在初始化... 获取视频 {BVID} 的信息")
    aid, title = get_video_info(BVID)
    if not aid:
        print("初始化失败，请检查网络或 BV 号是否正确。")
        return
    
    print(f"获取成功！\n视频标题: {title}\n对应 AID: {aid}\n开始执行自动回复任务...")
    
    # 构建正则表达式，安全地转义前后缀中的特殊符号（如中文括号）
    pattern = re.compile(re.escape(PREFIX) + r"(\d+)" + re.escape(SUFFIX))

    while True:
        print("\n" + "="*40)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始本轮检测...")
        
        comments = get_latest_comments(aid)
        max_n = -1
        
        # 遍历最新的10条评论，寻找匹配我们模板的文本
        for msg in comments:
            match = pattern.search(msg)
            if match:
                current_n = int(match.group(1))
                if current_n > max_n:
                    max_n = current_n
                    
        if max_n == -1:
            log_action(f"未在最新 10 条评论中发现目标格式的进度。请确保评论区已有基础节点，本次跳过。")
        else:
            next_n = max_n + 1
            
            # 需求三：确保发出内容不会超出上限
            if next_n > MAX_LIMIT:
                log_action(f"计算得出的下一次进度 {next_n} 已超出设定的上限 {MAX_LIMIT}，任务圆满结束！")
                break
                
            # 拼接我们要发的新内容
            new_message = f"{PREFIX}{next_n}{SUFFIX}"
            
            # 发送评论
            res = post_comment(aid, new_message)
            
            # 需求二：留档记录，保留动作、内容和接口返回状态
            if res.get('code') == 0:
                log_action(f"发送成功! 当前进度: {next_n} | 完整内容: {new_message}")
            else:
                log_action(f"发送失败! 错误码: {res.get('code')} | 错误信息: {res.get('message')}")

        # 需求一：留一个循环执行的间隔时间，直接以小时为单位
        print(f"进入休眠，等待 {INTERVAL_HOURS} 小时后执行下一轮检索...")
        # 将小时转换为秒
        time.sleep(INTERVAL_HOURS * 3600)

if __name__ == "__main__":
    main()