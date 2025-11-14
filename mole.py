import os
from loguru import logger
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
                session.get("https://mifan.61.com/api/v1/login", params=params, timeout=5)
                response = session.get("https://mifan.61.com/api/v1/event/dailysign/", params=params, timeout=5)
                data = response.json().get("data")
                sio.write(f"摩尔签到提示：{username} {data}，获得24金豆\n")
                if "成功" in data:
                    success = True
            except:
                logger.exception("请求错误：")
    if success:
        pusher.push(sio.getvalue().strip())
    logger.info(sio.getvalue().strip())


if __name__ == "__main__":
    main()
