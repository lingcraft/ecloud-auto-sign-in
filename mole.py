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
                set_retry(session)
                username, password = account.split(",")
                params = {
                    "uid": username,
                    "password": password
                }
                session.get("https://mifan.61.com/api/v1/login", params=params, timeout=5)  # 登录
                response = session.get("https://mifan.61.com/api/v1/event/dailysign/", timeout=5)  # 签到
                data = response.json().get("data")
                sio.write(f"摩尔签到提示：{username} {data}，获得24金豆\n")
                if "成功" in data:
                    success = True
                response = session.post("https://mifan.61.com/api/v1/profile", timeout=5)  # 账号信息
                gold = response.json().get("gold")  # 剩余米粒
                complement_times = gold // 1000  # 可补签次数
                if complement_times > 0:
                    # 获取账号最近40天未签到日期
                    response = session.get("https://mifan.61.com/api/v1/event/dailysign/recent", timeout=5)  # 签到信息
                    no_sign_date = [next(iter(item)) for item in response.json().get("data") if next(iter(item.values())) == 0]
                    # 获取账号补签数据的最新补签日期
                    if record_file.exists():
                        with record_file.open() as file:
                            latest_sign_dict = json.load(file)
                    else:
                        latest_sign_dict = {}
                    if account in latest_sign_dict:
                        next_date = latest_sign_dict.get(account)
                    else:
                        next_date = date(1970, 1, 1)
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
                    latest_sign_dict[account] = next_date
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
