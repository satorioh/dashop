import base64
import hashlib
import random
import time
import jwt

from django.core.cache import caches
from dashop import settings


def md5_string(s):
    """
    功能函数:md5加密
    """
    m = hashlib.md5()
    m.update(s.encode())
    return m.hexdigest()


def make_token(username, expire=3600 * 24):
    """
    功能函数:签发token
    """
    payload = {"exp": time.time() + expire, "username": username}
    key = settings.JWT_TOKEN_KEY
    return jwt.encode(payload, key, algorithm="HS256")


def get_verify_url(username):
    """
    功能函数:生成邮件激活链接
    """
    rand_code = random.randint(1000, 9999)
    # 1016_liying
    code_str = f"{rand_code}_{username}"
    code = base64.b64encode(code_str.encode()).decode()

    verify_url = f"http://127.0.0.1:7000/dadashop/templates/active.html?code={code}"

    # 将随机数存入Redis
    # {"active_liying": 1016}
    key = f"active_{username}"
    caches["default"].set(key, rand_code, 86400 * 3)

    return verify_url
