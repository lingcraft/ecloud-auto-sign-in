import os, re, rsa, time
from urllib.parse import urlparse, parse_qs
from loguru import logger
from pusher import *

# 天翼云盘签到
wechat_params = os.getenv("WECHAT_PARAMS").split(",")
ecloud_account = os.getenv("ECLOUD_ACCOUNT").split(",")
session = requests.Session()
set_retry(session)


def rsa_encode(j_rsa_key, content):
    rsa_key = f"-----BEGIN PUBLIC KEY-----\n{j_rsa_key}\n-----END PUBLIC KEY-----"
    pub_key = rsa.PublicKey.load_pkcs1_openssl_pem(rsa_key.encode())
    return rsa.encrypt(content.encode(), pub_key).hex()


def login(username, password):
    res = session.get(
        "https://m.cloud.189.cn/udb/udb_login.jsp",
        params={
            "pageId": 1,
            "pageKey": "default",
            "clientType": "wap",
            "redirectURL": "https://m.cloud.189.cn/zhuanti/2021/shakeLottery/index.html",
        },
        timeout=10
    )
    if not (match := re.search(r"href\s*=\s*'([^']*autoLogin[^']*)'", res.text)):
        sio.write("未找到动态登录页\n")
        return False
    url = match.group(1)
    session.get(url)
    params = {key: value[0] for key, value in parse_qs(urlparse(url).query).items()}

    res = session.post(
        "https://open.e.189.cn/api/logbox/oauth2/wap/appConf.do",
        params=params,
        timeout=10
    )
    if res.json().get("result") != "0":
        sio.write("获取登录配置失败\n")
        return False
    lt, return_url, param_id, account_type = [res.json().get("data").get(key) for key in ("lt", "returnUrl", "paramId", "accountType")]

    res = session.get(
        "https://open.e.189.cn/api/logbox/separate/wap/login.html",
        params=params,
        timeout=10
    )
    if not (match := re.search(r"id=\"j_rsaKey\"\s+value=\"([^\"]+)\"", res.text)):
        sio.write("获取RSA密钥失败\n")
        return False
    j_rsa_key = match.group(1)

    res = session.post(
        "https://open.e.189.cn/api/logbox/oauth2/loginSubmit.do",
        data={
            "appKey": "cloud",
            "accountType": account_type,
            "userName": f"{{RSA}}{rsa_encode(j_rsa_key, username)}",
            "password": f"{{RSA}}{rsa_encode(j_rsa_key, password)}",
            "validateCode": "",
            "captchaToken": "",
            "returnUrl": return_url,
            "mailSuffix": "@189.cn",
            "paramId": param_id
        },
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:74.0) Gecko/20100101 Firefox/76.0",
            "Referer": "https://open.e.189.cn/",
            "lt": lt
        },
        timeout=10
    )
    if res.json().get("result") == 0:
        session.get(res.json().get("toUrl"), timeout=10)
        return True
    else:
        sio.write(f"签到失败：登录出错\n错误提示：\n{res.json().get("msg")}\n")
        return False


def main():
    pusher = WeChat("天翼云盘", wechat_params)
    username, password = ecloud_account
    is_success = False
    with logger.catch():
        # 登录
        if not login(username, password):
            pusher.push(sio.getvalue())
            return
        res = session.get(
            "https://api.cloud.189.cn/mkt/userSign.action",
            params={
                "rand": str(round(time.time() * 1000)),
                "clientType": "TELEANDROID",
                "version": "8.6.3",
                "model": "SM-G930K",
            },
            headers={
                "User-Agent": "Mozilla/5.0 (Linux; Android 5.1.1; SM-G930K Build/NRD90M; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/74.0.3729.136 Mobile Safari/537.36 Ecloud/8.6.3 Android/22 clientId/355325117317828 clientModel/SM-G930K imsi/460071114317824 clientChannelId/qq proVersion/1.0.6",
                "Referer": "https://m.cloud.189.cn/zhuanti/2016/sign/index.jsp?albumBackupOpened=1",
                "Host": "m.cloud.189.cn",
            },
            timeout=10
        )
        res.raise_for_status()
        # 签到
        is_success = not res.json().get("isSign")
        tip = "签到成功" if is_success else "已签到"
        bonus = res.json().get("netdiskBonus")
        sio.write(f"签到提示：{tip}，获得{bonus}M空间\n")
    if is_success:
        pusher.push(sio.getvalue().strip())
    logger.info(sio.getvalue().strip())


if __name__ == "__main__":
    main()