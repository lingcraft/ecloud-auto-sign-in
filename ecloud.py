import base64, datetime, io, json, os, pytz, random, re, requests, rsa, time

# 天翼云盘每日签到1次，抽奖3次；摩尔庄园米饭签到

# 企业微信推送参数
wechat_params = os.getenv("PUSHER_WECHAT").split(",")

# 初始化
session = requests.Session()
sio = io.StringIO()
sio.seek(0, 2)
现在 = datetime.datetime.now(pytz.timezone("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S")
sio.write("-----------" + now + "----------\n")


def main():
    pusher = WeChat(wechat_params)
    # 天翼云盘签到
    username, password = os.getenv("ECLOUD_ACCOUNT").split(",")
    msg = login(username, password)
    if msg is None:
        pusher.push(sio.getvalue())
        return None
    rand = str(round(time.time() * 1000))
    urls = [
        f"https://api.cloud.189.cn/mkt/userSign.action?rand={rand}&clientType=TELEANDROID&version=8.6.3&model=SM-G930K",
        f"https://m.cloud.189.cn/v2/drawPrizeMarketDetails.action?taskId=TASK_SIGNIN&activityId=ACT_SIGNIN",
        f"https://m.cloud.189.cn/v2/drawPrizeMarketDetails.action?taskId=TASK_SIGNIN_PHOTOS&activityId=ACT_SIGNIN",
        f"https://m.cloud.189.cn/v2/drawPrizeMarketDetails.action?taskId=TASK_2022_FLDFS_KJ&activityId=ACT_SIGNIN"
    ]
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 5.1.1; SM-G930K Build/NRD90M; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/74.0.3729.136 Mobile Safari/537.36 Ecloud/8.6.3 Android/22 clientId/355325117317828 clientModel/SM-G930K imsi/460071114317824 clientChannelId/qq proVersion/1.0.6",
        "Referer": "https://m.cloud.189.cn/zhuanti/2016/sign/index.jsp?albumBackupOpened=1",
        "Host": "m.cloud.189.cn",
        "Accept-Encoding": "gzip, deflate",
    }
    for i in range(len(urls)):
        url = urls[i]
        response = session.get(url, headers=headers)
        if i == 0:
            bonus = response.json()["netdiskBonus"]
            if not response.json()["isSign"]:
                sio.write(f"签到提示：签到成功，获得{bonus}M空间\n")
            else:
                sio.write(f"签到提示：已签到，获得{bonus}M空间\n")
        else:
            if "errorCode" in response.text:
                if response.json()["errorCode"] == "User_Not_Chance":
                    sio.write(f"第{i}次抽奖提示：已抽奖，获得50M空间\n")
                else:
                    sio.write(f"第{i}次抽奖提示：抽奖失败\n")
                    sio.write(response.text)
                    sio.write("\n")
            else:
                bonus = response.json()["prizeName"].replace("天翼云盘", "")
                sio.write(f"第{i}次抽奖提示：抽奖成功，获得{bonus}\n")
        time.sleep(random.randint(5, 10))
    # 摩尔庄园签到
    username, password = os.getenv("MOLE_ACCOUNT").split(",")
    params = {
        "uid": username,
        "password": password
    }
    session.get("https://mifan.61.com/api/v1/login", params=params)
    response = session.get("https://mifan.61.com/api/v1/event/dailysign/", params=params)
    sio.write(f"米饭签到提示：{json.loads(response.text)["data"]}")
    pusher.push(sio.getvalue())


def login(username, password):
    url = "https://m.cloud.189.cn/udb/udb_login.jsp?pageId=1&pageKey=default&clientType=wap&redirectURL=https://m.cloud.189.cn/zhuanti/2021/shakeLottery/index.html"
    r = session.get(url)
    pattern = r"https?://[^\s'\"]+"
    match = re.search(pattern, r.text)
    if match:
        url = match.group()
    else:
        sio.write("没有找到url\n")
        return None
    r = session.get(url)
    pattern = r"<a id=\"j-tab-login-link\"[^>]*href=\"([^\"]+)\""
    match = re.search(pattern, r.text)
    if match:
        href = match.group(1)
    else:
        sio.write("没有找到href链接\n")
        return None
    r = session.get(href)
    captchaToken = re.findall(r"captchaToken' value='(.+?)'", r.text)[0]
    lt = re.findall(r'lt = "(.+?)"', r.text)[0]
    returnUrl = re.findall(r"returnUrl= '(.+?)'", r.text)[0]
    paramId = re.findall(r'paramId = "(.+?)"', r.text)[0]
    j_rsakey = re.findall(r'j_rsaKey" value="(\S+)"', r.text, re.M)[0]
    session.headers.update({"lt": lt})
    encoder = Encoder()
    username_rsa = encoder.rsa_encode(j_rsakey, username)
    password_rsa = encoder.rsa_encode(j_rsakey, password)
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
        "captchaToken": captchaToken,
        "returnUrl": returnUrl,
        "mailSuffix": "@189.cn",
        "paramId": paramId
    }
    r = session.post(url, data=data, headers=headers, timeout=5)
    if r.json()["result"] != 0:
        msg = r.json()["msg"]
        sio.write("签到失败：登录出错\n")
        sio.write("错误提示：\n")
        sio.write(msg)
        sio.write("\n")
        return None
    redirect_url = r.json()["toUrl"]
    r = session.get(redirect_url)
    return session


class Encoder:
    def rsa_encode(self, j_rsakey, string):
        rsa_key = f"-----BEGIN PUBLIC KEY-----\n{j_rsakey}\n-----END PUBLIC KEY-----"
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


class WeChat:
    def __init__(self, params) -> None:
        self.corp_id = params[0]
        self.corp_secret = params[1]
        self.to_user = params[2]
        self.agent_id = params[3]
        self.media_id = params[4]

    def push(self, content: str = None) -> str:
        if "失败" in content:
            title = "天翼云盘签到失败"
        else:
            title = "天翼云盘签到成功"
        if self.media_id is not None:
            response = self.send_news(title, content)
        else:
            message = title + "\n" + content
            response = self.send_text(message)
        return response

    def get_token(self) -> str:
        url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={}&corpsecret={}".format(self.corp_id,
                                                                                            self.corp_secret)
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()["access_token"]
        else:
            return ""

    def send_text(self, message) -> str:
        url = "https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={}".format(self.get_token())
        data = {
            "touser": self.to_user,
            "msgtype": "text",
            "agentid": self.agent_id,
            "text": {
                "content": message
            },
            "safe": 0
        }
        msg = (bytes(json.dumps(data), "utf-8"))
        response = requests.post(url, msg)
        return response

    def send_news(self, title, message) -> str:
        url = "https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={}".format(self.get_token())
        if not message:
            message = title
        data = {
            "touser": self.to_user,
            "msgtype": "mpnews",
            "agentid": self.agent_id,
            "mpnews": {
                "articles": [
                    {
                        "title": title,
                        "thumb_media_id": self.media_id,
                        "content_source_url": "",
                        "content": message.replace("\n", "<br/>"),
                        "digest": message,
                    }
                ]
            },
            "safe": 0
        }
        msg = (bytes(json.dumps(data), "utf-8"))
        response = requests.post(url, msg)
        return response


if __name__ == "__main__":
    main()
