import json, requests, io, pytz
from datetime import datetime
from urllib3 import Retry
from requests.adapters import HTTPAdapter

sio = io.StringIO()
sio.seek(0, 2)
now = datetime.now(pytz.timezone("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S")
sio.write("-----------" + now + "----------\n")


class WeChat:
    def __init__(self, way, params):
        self.way = way
        self.corp_id, self.corp_secret, self.to_user, self.agent_id, self.media_id = params

    def push(self, message):
        tip = "失败" if "失败" in message else "成功"
        title = f"{self.way}签到{tip}"
        if self.media_id is not None:
            return self.send_news(title, message)
        else:
            return self.send_text(title, message)

    def get_token(self):
        response = requests.get(
            "https://qyapi.weixin.qq.com/cgi-bin/gettoken",
            params={
                "corpid": self.corp_id,
                "corpsecret": self.corp_secret
            }
        )
        if response.status_code == 200:
            return response.json().get("access_token")
        else:
            return ""

    def send_text(self, title, message):
        return requests.post(
            "https://qyapi.weixin.qq.com/cgi-bin/message/send",
            params={
                "access_token": self.get_token(),
            },
            json={
                "touser": self.to_user,
                "msgtype": "text",
                "agentid": self.agent_id,
                "text": {
                    "content": f"{title}\n{message}"
                },
                "safe": 0
            }
        )

    def send_news(self, title, message):
        if not message:
            message = title
        return requests.post(
            "https://qyapi.weixin.qq.com/cgi-bin/message/send",
            params={
                "access_token": self.get_token(),
            },
            json={
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
        )


def set_retry(session):
    retry = Retry(
        total=5,
        backoff_factor=0.5,
        status_forcelist=[400, 429, 500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
