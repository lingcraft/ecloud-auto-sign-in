import os, time
from loguru import logger
from datetime import date, timedelta
from pusher import *

# 摩尔庄园米饭签到
wechat_params = os.getenv("WECHAT_PARAMS").split(",")
mole_accounts = os.getenv("MOLE_ACCOUNTS").split("\n")


def main():
    pusher = WeChat("摩尔庄园", wechat_params)
    # 摩尔庄园签到
    success = False
    for account in mole_accounts:
        with requests.Session() as session:
            set_retry(session)
            username, password = account.split(",")
            params = {
                "uid": username,
                "password": password
            }
            try:
                session.get("https://mifan.61.com/api/v1/login", params=params, timeout=5)  # 登录
                response = session.get("https://mifan.61.com/api/v1/event/dailysign/", timeout=5)  # 签到
                data = response.json().get("data")
                sio.write(f"摩尔签到提示：{username} {data}，获得24金豆\n")
                if "成功" in data:
                    success = True
                response = session.post("https://mifan.61.com/api/v1/profile", timeout=5)
                gold = response.json().get("gold")  # 剩余米粒
                complement_times = gold // 1000  # 可补签次数
                if complement_times > 0:
                    response = session.get("https://mifan.61.com/api/v1/event/dailysign/recent", timeout=5)
                    no_sign_data = [next(iter(item)) for item in response.json().get("data") if next(iter(item.values())) == 0]
                    start_date = date(1970, 1, 1)
                    one_day = timedelta(days=1)
                    i = 0
                    while i < complement_times:
                        if len(no_sign_data) > 0:
                            sign_date = no_sign_data.pop()
                            is_plus_day = False
                        else:
                            sign_date = start_date
                            is_plus_day = True
                        params = {
                            "complement_date": sign_date
                        }
                        response = session.get("https://mifan.61.com/api/v1/event/dailysign/complement", params=params, timeout=5)
                        data = response.json().get("data")
                        if "成功" in data:
                            sio.write(f"摩尔补签提示：{username} {sign_date} {data}，获得24金豆\n")
                            i += 1
                        if is_plus_day:
                            start_date += one_day
                        time.sleep(1)
            except:
                logger.exception("请求错误：")
        time.sleep(1)
    if success:
        pusher.push(sio.getvalue().strip())
    logger.info(sio.getvalue().strip())


if __name__ == "__main__":
    main()
