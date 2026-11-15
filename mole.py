from base64 import b64decode, b64encode
from datetime import date, timedelta
from json import dumps, loads
from loguru import logger
from os import environ
from pusher import *
from random import sample
from requests import get, put
from time import sleep
try:
    import env
except ImportError:
    pass

# 摩尔庄园米饭签到
wechat_params = environ["WECHAT_PARAMS"].split(",")
mole_accounts = environ["MOLE_ACCOUNTS"].split("|")


def pull_record():
    """读取仓库里的 mole.json，返回 (记录, 文件 sha)。"""
    res = get(
        "https://api.github.com/repos/lingcraft/ecloud-auto-sign-in/contents/mole.json",
        headers={
            "Authorization": f"Bearer {environ["GITHUB_TOKEN"]}",
            "Accept": "application/vnd.github+json",
        },
        params={"ref": "master"},
        timeout=30
    )
    res.raise_for_status()
    body = res.json()
    return loads(b64decode(body["content"])), body["sha"]


def push_record(record, sha):
    """写回 mole.json，返回新的 sha。"""
    res = put(
        "https://api.github.com/repos/lingcraft/ecloud-auto-sign-in/contents/mole.json",
        headers={
            "Authorization": f"Bearer {environ["GITHUB_TOKEN"]}",
            "Accept": "application/vnd.github+json",
        },
        timeout=30,
        json={
            "message": "更新补签数据",
            "content": b64encode(dumps(record, indent=2, ensure_ascii=False).encode()).decode(),
            "branch": "master",
            "sha": sha,
            "author": {
                "name": "github-actions[bot]",
                "email": "41898282+github-actions[bot]@users.noreply.github.com",
            },
            "committer": {
                "name": "github-actions[bot]",
                "email": "41898282+github-actions[bot]@users.noreply.github.com",
            },
        },
    )
    res.raise_for_status()
    return res.json()["content"]["sha"]


def main():
    pusher = WeChat("摩尔庄园", wechat_params)
    record, sha = pull_record()
    before = dict(record)
    # 摩尔庄园签到
    success = False
    for index, account in enumerate(mole_accounts):
        with logger.catch():
            with Session() as session:
                # 请求参数、账号信息
                username, password = account.split(",")
                params = {
                    "uid": username,
                    "password": password
                }
                # 签到
                session.get("https://mifan.61.com/api/v1/login", params=params)  # 登录
                res = session.get("https://mifan.61.com/api/v1/event/dailysign/")  # 签到
                data = res.json()["data"]
                sio.write(f"摩尔签到提示：{username} {data}，获得24金豆\n")
                if "成功" in data:
                    success = True
                # 点赞20次
                data = {
                    "type": "latest",
                    "offset": -1,
                    "count": 15,
                    "timestamp": datetime.now().timestamp()
                }
                article_id = session.post("https://mifan.61.com/api/v1/feed", data=data).json()["data"]["current_page"][0]["data"]["article_id"]  # 最新帖子ID
                success_times = 0
                while success_times < 20:
                    res = session.post(f"https://mifan.61.com/api/v1/article/likes/{article_id}/")  # 点赞
                    data, gold = [res.json()[key] for key in ("data", "gold")]
                    session.post(f"https://mifan.61.com/api/v1/article/likes/{article_id}/", data={"cancel": 1})  # 取消点赞
                    if data == 0:
                        if gold > 0:
                            success_times += 1
                        else:  # 米粒达到上限
                            break
                    article_id -= 1
                if success_times > 0:
                    sio.write(f"摩尔点赞提示：{username} 点赞成功，获得{success_times * 5}米粒\n")
                # 评论10次
                article_id = session.get("https://mifan.61.com/api/v1/article/home").json()["data"]["current_page"][0]["data"]["article_id"]  # 个人帖子ID
                text = sample(range(100), 20)
                data = {
                    "comment_article_id": article_id,
                    "post_text": text.pop(),
                    "post_atcount": 0
                }
                success_times = 0
                while success_times < 10:
                    try:
                        res = session.post("https://mifan.61.com/api/v1/article/comment", data=data, timeout=30)  # 评论
                        res.raise_for_status()
                    except:
                        data["post_text"] = text.pop()
                    else:
                        code, gold = [res.json()[key] for key in ("code", "gold")]
                        if code == 200:
                            if gold > 0:
                                success_times += 1
                            else:  # 米粒达到上限
                                break
                        data["post_text"] = text.pop()
                if success_times > 0:
                    sio.write(f"摩尔评论提示：{username} 评论成功，获得{success_times * 5}米粒\n")
                # 删除评论
                comments = session.get(f"https://mifan.61.com/api/v1/article/comment/{article_id}/").json()["data"]  # 获取评论
                while len(comments) > 0:
                    comment_id = comments.pop()["cid"]
                    session.post(f"https://mifan.61.com/api/v1/article/comment/delete/{comment_id}/")  # 删除
                # 补签
                res = session.post("https://mifan.61.com/api/v1/profile")  # 账号信息
                gold = res.json()["gold"]  # 剩余米粒
                complement_times = gold // 1000  # 可补签次数
                if complement_times > 0:
                    # 获取账号最近40天未签到日期
                    res = session.get("https://mifan.61.com/api/v1/event/dailysign/recent")  # 最近签到信息
                    no_sign_date = [key for item in res.json()["data"] for key, value in item.items() if value == 0]
                    # 获取账号补签数据的最新补签日期
                    next_date = date.fromisoformat(record.get(username, "1970-01-01"))
                    one_day = timedelta(days=1)
                    success_times = 0
                    # 开始补签
                    while success_times < complement_times:
                        # 先补签最近40天未签到日期
                        if len(no_sign_date) > 0:
                            sign_date = no_sign_date.pop()
                            is_plus_day = False
                        # 再从最新补签日期开始补签
                        else:
                            sign_date = next_date.isoformat()
                            is_plus_day = True
                        params = {
                            "complement_date": sign_date
                        }
                        res = session.get("https://mifan.61.com/api/v1/event/dailysign/complement", params=params)  # 补签
                        data = res.json()["data"]
                        if "成功" in data:
                            success_times += 1
                        if is_plus_day:
                            next_date += one_day
                    if success_times > 0:
                        sio.write(f"摩尔补签提示：{username} {data}，获得{success_times * 24}金豆\n")
                    # 记录补签数据
                    record[username] = next_date.isoformat()
        if index < len(mole_accounts) - 1:
            sleep(5)
    # 更新补签数据
    if record != before:
        push_record(record, sha)
    if success:
        pusher.push(sio.getvalue().strip())
    logger.info(sio.getvalue().strip())


if __name__ == "__main__":
    main()
