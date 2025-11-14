import base64, os, random, re, rsa, time
from loguru import logger
from pusher import *

# 天翼云盘签到1次，抽奖3次
wechat_params = os.getenv("WECHAT_PARAMS").split(",")
ecloud_account = os.getenv("ECLOUD_ACCOUNT").split(",")
session = requests.Session()


class Encoder:
    def rsa_encode(self, j_rsa_key, string):
        rsa_key = f"-----BEGIN PUBLIC KEY-----\n{j_rsa_key}\n-----END PUBLIC KEY-----"
        pubkey = rsa.PublicKey.load_pkcs1_openssl_pem(rsa_key.encode())
        result = self.b64tohex((base64.b64encode(rsa.encrypt(f"{string}".encode(), pubkey))).decode())
        return result

    def b64tohex(self, a):
        d = ""
        e = 0
        c = 0
        for i in range(len(a)):
            if list(a)[i] != "=":
                v = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/".index(list(a)[i])
                if 0 == e:
                    e = 1
                    d += self.int2char(v >> 2)
                    c = 3 & v
                elif 1 == e:
                    e = 2
                    d += self.int2char(c << 2 | v >> 4)
                    c = 15 & v
                elif 2 == e:
                    e = 3
                    d += self.int2char(c)
                    d += self.int2char(v >> 2)
                    c = 3 & v
                else:
                    e = 0
                    d += self.int2char(c << 2 | v >> 4)
                    d += self.int2char(15 & v)
        if e == 1:
            d += self.int2char(c << 2)
        return d

    def int2char(self, a):
        return list("0123456789abcdefghijklmnopqrstuvwxyz")[a]


def login(username, password):
    url = "https://m.cloud.189.cn/udb/udb_login.jsp?pageId=1&pageKey=default&clientType=wap&redirectURL=https://m.cloud.189.cn/zhuanti/2021/shakeLottery/index.html"
    response = session.get(url)
    pattern = r"https?://[^\s'\"]+"
    match = re.search(pattern, response.text)
    if match:
        url = match.group()
    else:
        sio.write("没有找到url\n")
        return None
    response = session.get(url)
    pattern = r"<a id=\"j-tab-login-link\"[^>]*href=\"([^\"]+)\""
    match = re.search(pattern, response.text)
    if match:
        href = match.group(1)
    else:
        sio.write("没有找到href链接\n")
        return None
    response = session.get(href)
    captcha_token = re.findall(r"captchaToken' value='(.+?)'", response.text)[0]
    lt = re.findall(r'lt = "(.+?)"', response.text)[0]
    return_url = re.findall(r"returnUrl= '(.+?)'", response.text)[0]
    param_id = re.findall(r'paramId = "(.+?)"', response.text)[0]
    j_rsa_key = re.findall(r'j_rsaKey" value="(\S+)"', response.text, re.M)[0]
    session.headers.update({"lt": lt})
    encoder = Encoder()
    username_rsa = encoder.rsa_encode(j_rsa_key, username)
    password_rsa = encoder.rsa_encode(j_rsa_key, password)
    url = "https://open.e.189.cn/api/logbox/oauth2/loginSubmit.do"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:74.0) Gecko/20100101 Firefox/76.0",
        "Referer": "https://open.e.189.cn/",
    }
    data = {
        "appKey": "cloud",
        "accountType": "01",
        "userName": f"{{RSA}}{username_rsa}",
        "password": f"{{RSA}}{password_rsa}",
        "validateCode": "",
        "captchaToken": captcha_token,
        "returnUrl": return_url,
        "mailSuffix": "@189.cn",
        "paramId": param_id
    }
    response = session.post(url, data=data, headers=headers, timeout=5)
    if response.json()["result"] == 0:
        redirect_url = response.json()["toUrl"]
        response = session.get(redirect_url)
        return response
    else:
        msg = response.json()["msg"]
        sio.write(f"签到失败：登录出错\n错误提示：\n{msg}\n")
        return None


def main():
    pusher = WeChat("天翼云盘", wechat_params)
    # 天翼云盘签到
    username, password = ecloud_account
    msg = login(username, password)
    if msg is None:
        pusher.push(sio.getvalue())
        return
    rand = str(round(time.time() * 1000))
    urls = [
        f"https://api.cloud.189.cn/mkt/userSign.action?rand={rand}&clientType=TELEANDROID&version=8.6.3&model=SM-G930K",
        f"https://m.cloud.189.cn/v2/drawPrizeMarketDetails.action?taskId=TASK_SIGNIN&activityId=ACT_SIGNIN"
        # f"https://m.cloud.189.cn/v2/drawPrizeMarketDetails.action?taskId=TASK_SIGNIN_PHOTOS&activityId=ACT_SIGNIN",
        # f"https://m.cloud.189.cn/v2/drawPrizeMarketDetails.action?taskId=TASK_2022_FLDFS_KJ&activityId=ACT_SIGNIN"
    ]
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 5.1.1; SM-G930K Build/NRD90M; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/74.0.3729.136 Mobile Safari/537.36 Ecloud/8.6.3 Android/22 clientId/355325117317828 clientModel/SM-G930K imsi/460071114317824 clientChannelId/qq proVersion/1.0.6",
        "Referer": "https://m.cloud.189.cn/zhuanti/2016/sign/index.jsp?albumBackupOpened=1",
        "Host": "m.cloud.189.cn",
        "Accept-Encoding": "gzip, deflate",
    }
    set_retry(session)
    success = False
    for i, url in enumerate(urls):
        try:
            response = session.get(url, headers=headers, timeout=5)
            # 签到
            if i == 0:
                bonus = response.json()["netdiskBonus"]
                success = not response.json()["isSign"]
                sio.write(f"签到提示：{"签到成功" if success else "已签到"}，获得{bonus}M空间\n")
            # 抽奖
            else:
                if "errorCode" not in response.json():
                    bonus = response.json()["prizeName"].replace("天翼云盘", "")
                    sio.write(f"抽奖第{i}次提示：抽奖成功，获得{bonus}\n")
                else:
                    if response.json()["errorCode"] == "User_Not_Chance":
                        sio.write(f"抽奖第{i}次提示：已抽奖，获得50M空间\n")
                    else:
                        sio.write(f"抽奖第{i}次提示：抽奖失败\n")
            if i != len(urls) - 1:
                time.sleep(random.randint(5, 10))
        except:
            logger.exception("请求错误：")
    if success:
        pusher.push(sio.getvalue())
    logger.info(sio.getvalue())


if __name__ == "__main__":
    main()
