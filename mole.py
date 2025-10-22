from os import getenv
from pusher import *
import env

# 摩尔庄园米饭签到
wechat_params = getenv("WECHAT_PARAMS").split(",")
mole_accounts = getenv("MOLE_ACCOUNTS").split("\n")


def main():
    pusher = WeChat("摩尔庄园", wechat_params)
    # 摩尔庄园签到
    success = False
    for mole_account in mole_accounts:
        username, password = mole_account.split(",")
        params = {
            "uid": username,
            "password": password
        }
        session.get("https://mifan.61.com/api/v1/login", params=params)
        response = session.get("https://mifan.61.com/api/v1/event/dailysign/", params=params)
        data = json.loads(response.text)["data"]
        sio.write(f"摩尔签到提示：{username}{data}，获得24金豆\n")
        if "成功" in data:
            success = True
    if success:
        pusher.push(sio.getvalue())


if __name__ == "__main__":
    main()
