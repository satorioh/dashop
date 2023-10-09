import json
import hashlib
import time

import jwt
from django.http import JsonResponse, HttpRequest
from users.models import UserProfile
from dashop import settings


def register(request: HttpRequest) -> JsonResponse:
    """
    注册功能视图逻辑
    1.获取请求体数据
    2.数据合法性校验
    3.确认用户名是否被占用
      3.1 被占用:直接返回
      3.2 未被占用:存入数据表
          签发token,返回响应[接口文档]
    """
    data = json.loads(request.body)
    print(data)
    username = data.get("uname")
    password = data.get("password")
    email = data.get("email")
    phone = data.get("phone")
    verify = data.get("verify")

    # 2.数据合法性校验
    if len(username) < 6 or len(username) > 11:
        return JsonResponse({"code": 10100, "error": "用户名不合法"})

    if len(password) < 6 or len(password) > 12:
        return JsonResponse({"code": 10101, "error": "密码不合法"})

    if len(phone) != 11:
        return JsonResponse({"code": 10102, "error": "手机号不合法"})

    # 3.确认用户名是否被占用
    user_query = UserProfile.objects.filter(username=username)
    print(f"user_query -> {user_query}")
    # 被占用
    if user_query:
        return JsonResponse({"code": 10103, "error": "用户名已被占用"})

    # 存入数据表
    try:
        user = UserProfile.objects.create(username=username, password=md5_string(password), email=email, phone=phone)
        print(f"user -> {user}")
    except Exception as e:
        print(e)

    # 签发token
    token = make_token(username)

    # 返回响应
    result = {
        "code": 200,
        "username": username,
        "token": token,
        "carts_count": 0
    }

    return JsonResponse(result)


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
