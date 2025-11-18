import os, time
from loguru import logger
from datetime import date, timedelta
from pathlib import Path
from pusher import *

# 摩尔庄园米饭签到
wechat_params = os.getenv("WECHAT_PARAMS").split(",")
mole_accounts = os.getenv("MOLE_ACCOUNTS").split("\n")


def main():
    pusher = WeChat("摩尔庄园", wechat_params)
    record_file = Path("mole.json")
    # 摩尔庄园签到
    success = False
    for i, account in enumerate(mole_accounts):
        try:
            with requests.Session() as session:
                # 请求参数、账号信息
                set_retry(session)
                username, password = account.split(",")
                params = {
                    "uid": username,
                    "password": password
                }
                # 签到
                session.get("https://mifan.61.com/api/v1/login", params=params, timeout=5)  # 登录
                response = session.get("https://mifan.61.com/api/v1/event/dailysign/", timeout=5)  # 签到
                data = response.json().get("data")
                sio.write(f"摩尔签到提示：{username} {data}，获得24金豆\n")
                if "成功" in data:
                    success = True
                # 点赞
                data = {
                    "type": "latest",
                    "offset": -1,
                    "count": 15,
                    "timestamp": datetime.now().timestamp()
                }
                article_id = session.post("https://mifan.61.com/api/v1/feed", data=data).json().get("data").get("current_page")[0].get("data").get("article_id")  # 最新帖子ID
                j = 0
                while j < 20:
                    try:
                        response = session.post(f"https://mifan.61.com/api/v1/article/likes/{article_id}/", timeout=5)  # 点赞
                        response.raise_for_status()
                    except:
                        logger.exception(f"点赞帖子{article_id}错误：")
                    else:
                        data, gold = (response.json().get(key) for key in ("data", "gold"))
                        session.post(f"https://mifan.61.com/api/v1/article/likes/{article_id}/", data={"cancel": 1}, timeout=5)  # 取消点赞
                        if data == 0:
                            if gold > 0:
                                j += 1
                            else:
                                if j > 0:
                                    sio.write(f"摩尔点赞提示：{username} 点赞成功，获得{j * 5}米粒\n")
                                break
                        article_id -= 1
                # 评论
                data = {
                    "comment_article_id": 741965,
                    "post_text": 1,
                    "post_atcount": 0
                }
                j = 0
                while j < 10:
                    try:
                        response = session.post("https://mifan.61.com/api/v1/article/comment", data=data, timeout=10)  # 评论
                        response.raise_for_status()
                    except:
                        logger.exception(f"评论内容\"{data.get("post_text")}\"错误：")
                    else:
                        code, gold, comment_id = (response.json().get(key) for key in ("code", "gold", "comment_id"))
                        session.post(f"https://mifan.61.com/api/v1/article/comment/delete/{comment_id}/", timeout=5)  # 删除评论
                        if code == 200:
                            if gold > 0:
                                j += 1
                            else:
                                if j > 0:
                                    sio.write(f"摩尔评论提示：{username} 评论成功，获得{j * 5}米粒\n")
                                break
                        else:
                            data["post_text"] += 1
                # 补签
                response = session.post("https://mifan.61.com/api/v1/profile", timeout=5)  # 账号信息
                gold = response.json().get("gold")  # 剩余米粒
                complement_times = gold // 1000  # 可补签次数
                if complement_times > 0:
                    # 获取账号最近40天未签到日期
                    response = session.get("https://mifan.61.com/api/v1/event/dailysign/recent", timeout=5)  # 最近签到信息
                    no_sign_date = [key for item in response.json().get("data") for key, value in item.items() if value == 0]
                    # 获取账号补签数据的最新补签日期
                    if record_file.exists():
                        with record_file.open() as file:
                            latest_sign_dict = json.load(file)
                    else:
                        latest_sign_dict = {}
                    next_date = latest_sign_dict.get(username, date(1970, 1, 1))
                    one_day = timedelta(days=1)
                    j = 0
                    # 开始补签
                    while j < complement_times:
                        # 先补签最近40天未签到日期
                        if len(no_sign_date) > 0:
                            sign_date = no_sign_date.pop()
                            is_plus_day = False
                        # 再从最新补签日期开始补签
                        else:
                            sign_date = next_date
                            is_plus_day = True
                        params = {
                            "complement_date": sign_date
                        }
                        response = session.get("https://mifan.61.com/api/v1/event/dailysign/complement", params=params, timeout=5)  # 补签
                        data = response.json().get("data")
                        if "成功" in data:
                            sio.write(f"摩尔补签提示：{username} {sign_date} {data}，获得24金豆\n")
                            j += 1
                        if is_plus_day:
                            next_date += one_day
                        if j != complement_times - 1:
                            time.sleep(1)
                    # 记录补签数据
                    latest_sign_dict[username] = next_date
                    with record_file.open("w") as file:
                        json.dump(latest_sign_dict, file, indent=2)
            if i != len(mole_accounts) - 1:
                time.sleep(1)
        except:
            logger.exception("请求错误：")
    if success:
        pusher.push(sio.getvalue().strip())
    logger.info(sio.getvalue().strip())


if __name__ == "__main__":
    main()
