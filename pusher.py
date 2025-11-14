import json, requests, io, datetime, pytz
from urllib3 import Retry
from requests.adapters import HTTPAdapter

sio = io.StringIO()
sio.seek(0, 2)
now = datetime.datetime.now(pytz.timezone("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S")
sio.write("-----------" + now + "----------\n")


class WeChat:
    def __init__(self, way, params):
        self.way = way
        self.corp_id, self.corp_secret, self.to_user, self.agent_id, self.media_id = params

    def push(self, content: str = None):
        if "失败" in content:
            title = f"{self.way}签到失败"
        else:
            title = f"{self.way}签到成功"
        if self.media_id is not None:
            response = self.send_news(title, content)
        else:
            message = title + "\n" + content
            response = self.send_text(message)
        return response

    def get_token(self):
        url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={}&corpsecret={}".format(self.corp_id,
                                                                                            self.corp_secret)
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()["access_token"]
        else:
            return ""

    def send_text(self, message):
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

    def send_news(self, title, message):
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


def set_retry(session):
    retry = Retry(
        total=5,
        status_forcelist=[429, 500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
