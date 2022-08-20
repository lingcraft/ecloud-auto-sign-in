import requests, time, re, rsa, json, base64, pytz, datetime, hashlib
from io import StringIO

# Python版本 3.6，Forked from "https://github.com/peng4740/Cloud189Checkin-Actions"
# 天翼云盘每日签到1次，抽奖2次
s = requests.Session()

# 账号
username = "13781850816"
password = "Caoyuze990318"

# 企业微信应用参数
corp_id = "ww1b63035144a6d2f1"
corp_secret = "kGJl9yYUy-mQXCO5hulxCId5L2sVaKW2HKeqyguhytg"
to_user = "@all"
agent_id = "1000002"
media_id = "2168tjb8CL3KTeit4o6wZrlFsKpdTdnkCirm9C-bBK97_-7JzKe7iEN362UAmp54P"

# 初始化日志
sio = StringIO()
sio.seek(0, 2)  # 将读写位置移动到结尾
tz = pytz.timezone('Asia/Shanghai')
time_now = datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
sio.write("--------------------------" + time_now + "----------------------------\n")


def main():
    if username == "" or password == "":
        sio.write('签到失败：用户名或密码为空，请设置\n')
        description = sio.getvalue()
        push_wechat(description)
        return None
    msg = login(username, password)
    if msg == "error":
        description = sio.getvalue()
        push_wechat(description)
        return None
    else:
        pass
    rand = str(round(time.time() * 1000))
    surl = f'https://api.cloud.189.cn/mkt/userSign.action?rand={rand}&clientType=TELEANDROID&version=8.6.3&model=SM-G930K'
    url = f'https://m.cloud.189.cn/v2/drawPrizeMarketDetails.action?taskId=TASK_SIGNIN&activityId=ACT_SIGNIN'
    url2 = f'https://m.cloud.189.cn/v2/drawPrizeMarketDetails.action?taskId=TASK_SIGNIN_PHOTOS&activityId=ACT_SIGNIN'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 5.1.1; SM-G930K Build/NRD90M; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/74.0.3729.136 Mobile Safari/537.36 Ecloud/8.6.3 Android/22 clientId/355325117317828 clientModel/SM-G930K imsi/460071114317824 clientChannelId/qq proVersion/1.0.6',
        "Referer": "https://m.cloud.189.cn/zhuanti/2016/sign/index.jsp?albumBackupOpened=1",
        "Host": "m.cloud.189.cn",
        "Accept-Encoding": "gzip, deflate",
    }
    # 签到
    response = s.get(surl, headers=headers)
    bonus = response.json()['netdiskBonus']
    if response.json()['isSign'] == "false":
        sio.write(f"签到提示：未签到，签到获得{bonus}M空间\n")
    else:
        sio.write(f"签到提示：已经签到过了，签到获得{bonus}M空间\n")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 5.1.1; SM-G930K Build/NRD90M; wv) AppleWebKit/537.36 (KHTML, '
                      'like Gecko) Version/4.0 Chrome/74.0.3729.136 Mobile Safari/537.36 Ecloud/8.6.3 Android/22 '
                      'clientId/355325117317828 clientModel/SM-G930K imsi/460071114317824 clientChannelId/qq '
                      'proVersion/1.0.6',
        "Referer": "https://m.cloud.189.cn/zhuanti/2016/sign/index.jsp?albumBackupOpened=1",
        "Host": "m.cloud.189.cn",
        "Accept-Encoding": "gzip, deflate",
    }
    # 第一次抽奖
    response = s.get(url, headers=headers)
    if "errorCode" in response.text:
        if response.json()['errorCode'] == "User_Not_Chance":
            sio.write("第一次抽奖：抽奖次数不足\n")
        else:
            sio.write("第一次抽奖失败\n")
            sio.write(response.text)
            sio.write("\n")
    else:
        prizeName = response.json()['prizeName']
        sio.write(f"第一次抽奖：抽奖获得{prizeName}\n")
    # 第二次抽奖
    response = s.get(url2, headers=headers)
    if "errorCode" in response.text:
        if response.json()['errorCode'] == "User_Not_Chance":
            sio.write("第二次抽奖：抽奖次数不足\n")
        else:
            sio.write("第二次抽奖失败\n")
            sio.write(response.text)
            sio.write("\n")
    else:
        prizeName = response.json()['prizeName']
        sio.write(f"第二次抽奖：抽奖获得{prizeName}\n")
    description = sio.getvalue()
    push_wechat(description)
    return description


BI_RM = list("0123456789abcdefghijklmnopqrstuvwxyz")


def int2char(a):
    return BI_RM[a]


b64map = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"


def b64tohex(a):
    d = ""
    e = 0
    c = 0
    for i in range(len(a)):
        if list(a)[i] != "=":
            v = b64map.index(list(a)[i])
            if 0 == e:
                e = 1
                d += int2char(v >> 2)
                c = 3 & v
            elif 1 == e:
                e = 2
                d += int2char(c << 2 | v >> 4)
                c = 15 & v
            elif 2 == e:
                e = 3
                d += int2char(c)
                d += int2char(v >> 2)
                c = 3 & v
            else:
                e = 0
                d += int2char(c << 2 | v >> 4)
                d += int2char(15 & v)
    if e == 1:
        d += int2char(c << 2)
    return d


def rsa_encode(j_rsakey, string):
    rsa_key = f"-----BEGIN PUBLIC KEY-----\n{j_rsakey}\n-----END PUBLIC KEY-----"
    pubkey = rsa.PublicKey.load_pkcs1_openssl_pem(rsa_key.encode())
    result = b64tohex((base64.b64encode(rsa.encrypt(f'{string}'.encode(), pubkey))).decode())
    return result


def calculate_md5_sign(params):
    return hashlib.md5('&'.join(sorted(params.split('&'))).encode('utf-8')).hexdigest()


def login(username, password):
    url = "https://cloud.189.cn/api/portal/loginUrl.action?redirectURL=https://cloud.189.cn/web/redirect.html"
    r = s.get(url)
    captchaToken = re.findall(r"captchaToken' value='(.+?)'", r.text)[0]
    lt = re.findall(r'lt = "(.+?)"', r.text)[0]
    returnUrl = re.findall(r"returnUrl = '(.+?)'", r.text)[0]
    paramId = re.findall(r'paramId = "(.+?)"', r.text)[0]
    j_rsakey = re.findall(r'j_rsaKey" value="(\S+)"', r.text, re.M)[0]
    s.headers.update({"lt": lt})

    username = rsa_encode(j_rsakey, username)
    password = rsa_encode(j_rsakey, password)
    url = "https://open.e.189.cn/api/logbox/oauth2/loginSubmit.do"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:74.0) Gecko/20100101 Firefox/76.0',
        'Referer': 'https://open.e.189.cn/',
    }
    data = {
        "appKey": "cloud",
        "accountType": '01',
        "userName": f"{{RSA}}{username}",
        "password": f"{{RSA}}{password}",
        "validateCode": "",
        "captchaToken": captchaToken,
        "returnUrl": returnUrl,
        "mailSuffix": "@189.cn",
        "paramId": paramId
    }
    r = s.post(url, data=data, headers=headers, timeout=5)
    if r.json()['result'] == 0:
        sio.write("登录提示：")
        sio.write(r.json()['msg'])
        sio.write("\n")
    else:
        msg = r.json()['msg']
        sio.write("签到失败：登录出错\n")
        sio.write("错误提示：\n")
        sio.write(msg)
        sio.write("\n")
        return "error"
    redirect_url = r.json()['toUrl']
    r = s.get(redirect_url)
    return s


def push_wechat(content: str = None) -> str:
    if '失败' in content:
        title = '天翼云盘签到失败'
    else:
        title = '天翼云盘签到成功'
    wx = WeChat(corp_id, corp_secret, agent_id)
    if media_id is not None:
        response = wx.send_mpnews(title, content, media_id, to_user)
    else:
        message = title + "\n" + content
        response = wx.send_text(message, to_user)
    return response


class WeChat:
    def __init__(self, corpid, corpsecret, agentid) -> None:
        self.corpid = corpid
        self.corpsecret = corpsecret
        self.agentid = agentid

    def get_token(self) -> str:
        url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={}&corpsecret={}".format(self.corpid,
                                                                                            self.corpsecret)
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()["access_token"]
        else:
            # log("Failed to get access_token.", level="error")
            return ""

    def send_text(self, message, touser="@all") -> str:
        url = "https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={}".format(self.get_token())
        data = {
            "touser": touser,
            "msgtype": "text",
            "agentid": self.agentid,
            "text": {
                "content": message
            },
            "safe": 0
        }
        send_msges = (bytes(json.dumps(data), 'utf-8'))
        response = requests.post(url, send_msges)
        return response

    def send_mpnews(self, title, message, media_id, touser="@all") -> str:
        url = "https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={}".format(self.get_token())
        if not message:
            message = title
        data = {
            "touser": touser,
            "msgtype": "mpnews",
            "agentid": self.agentid,
            "mpnews": {
                "articles": [
                    {
                        "title": title,
                        "thumb_media_id": media_id,
                        "content_source_url": "",
                        "content": message.replace('\n', '<br/>'),
                        "digest": message,
                    }
                ]
            },
            "safe": 0
        }
        send_msges = (bytes(json.dumps(data), 'utf-8'))
        response = requests.post(url, send_msges)
        return response


if __name__ == "__main__":
    main()
