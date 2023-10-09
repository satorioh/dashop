import json
import hashlib
import time

import jwt
from django.http import JsonResponse, HttpRequest
from django.views import View

from users.models import UserProfile, Address
from dashop import settings
from utils.logging_dec import logging_check


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


def login(request: HttpRequest) -> JsonResponse:
    """
       登录功能视图逻辑
       1.获取请求体数据
       2.校验用户名和密码是否正确
         2.1 错误:直接返回
         2.2 正确:生成token,然后返回
       """
    data = json.loads(request.body)
    print(f"login data ->{data}")
    username = data.get("username")
    password = data.get("password")
    user_query = UserProfile.objects.filter(username=username, password=md5_string(password))
    print(f"login user_query -> {user_query}")

    if not user_query:
        return JsonResponse({"code": 10104, "error": "用户名或密码错误"})

    # 返回响应
    result = {
        "code": 200,
        "username": username,
        "token": make_token(username),
        "carts_count": 0
    }
    return JsonResponse(result)


class AddressView(View):
    """
    用户地址视图类
    """

    @logging_check
    def get(self, request: HttpRequest, username: str) -> JsonResponse:
        """
        获取用户地址
        """
        print(f"获取用户地址 -> {request.myuser}")
        return JsonResponse({"code": 200})

    @logging_check
    def post(self, request: HttpRequest, username: str) -> JsonResponse:
        """
        新增收货地址视图逻辑
        1.获取请求体数据
        2.存入地址表
          第一个地址:添加并设置为默认地址
          非第一个地址:添加地址
        """
        data = json.loads(request.body)
        receiver = data.get("receiver")
        receiver_phone = data.get("receiver_phone")
        address = data.get("address")
        postcode = data.get("postcode")
        tag = data.get("tag")
        user = request.myuser

        # 查询该用户是否有收货地址
        address_query = Address.objects.filter(user_profile=user, is_delete=False)
        is_default = False if address_query else True

        Address.objects.create(user_profile=user, receiver=receiver, receiver_mobile=receiver_phone, address=address,
                               postcode=postcode, tag=tag, is_default=is_default)

        return JsonResponse({"code": 200, "data": "新增地址成功"})

    @logging_check
    def put(self, request: HttpRequest, username: str) -> JsonResponse:
        """
        修改用户地址
        """
        return JsonResponse({"code": 200, "username": username})

    @logging_check
    def delete(self, request: HttpRequest, username: str) -> JsonResponse:
        """
        删除用户地址
        """
        return JsonResponse({"code": 200, "username": username})


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
