import json
import hashlib
import time
from datetime import datetime

import jwt
from django.db import transaction
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
         查询收货地址视图逻辑
        1.查询该用户所有的收货地址
        2.组装数据返回响应
        {"code":200,"addresslist":[{},{},{},{},{}]}
        """
        addr_query = Address.objects.filter(user_profile=request.myuser, is_delete=False)
        addr_list = list(
            addr_query.values('id', 'address', 'receiver', 'receiver_mobile', 'tag', 'postcode', 'is_default'))

        result = {
            "code": 200,
            "addresslist": addr_list
        }
        return JsonResponse(result)

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
    def put(self, request, username: str, id) -> JsonResponse:
        """
        修改地址视图逻辑
        1.获取请求体数据
        2.一查二改三保存
        3.返回响应
        """
        user = request.myuser
        try:
            addr = Address.objects.filter(user_profile=user, id=id, is_delete=False)
        except Exception as e:
            print(e)
            return JsonResponse({"code": 10106, "error": "地址不存在"})

        data = request.mydata
        data.pop("id")
        data["updated_time"] = datetime.now()
        addr.update(**data)
        return JsonResponse({"code": 200, "data": "地址修改成功"})

    @logging_check
    def delete(self, request, username: str, id) -> JsonResponse:
        """
        删除地址视图逻辑
        伪删除:一查二改三保存
        """
        user = request.myuser
        try:
            addr = Address.objects.get(user_profile=user, id=id, is_delete=False)
        except Exception as e:
            print(e)
            return JsonResponse({"code": 10106, "error": "地址不存在"})
        addr.is_delete = True
        addr.save()
        return JsonResponse({"code": 200, "data": "地址删除成功"})


class DefaultAddressView(View):
    @logging_check
    def post(self, request, username):
        """
        设置默认地址视图逻辑
        1.获取请求体数据[id]
        2.把原来的默认地址取消默认
        3.把现在的地址设置为默认
        4.返回响应
        """
        id = request.mydata.get("id")
        user = request.myuser

        # 开启事务
        with transaction.atomic():
            # 创建存储点
            sid = transaction.savepoint()
            try:
                # 把原来的默认地址取消默认
                # <QuerySet [<AddrObject>]>
                old_query = Address.objects.filter(is_default=True, user_profile=user, is_delete=False)
                if old_query:
                    old_addr = old_query[0]
                    old_addr.is_default = False
                    old_addr.save()

                # 现在的地址设置为默认
                new_addr = Address.objects.get(id=id, user_profile=user, is_delete=False)
                new_addr.is_default = True
                new_addr.save()
            except Exception as e:
                # 回滚+返回
                transaction.savepoint_rollback(sid)
                return JsonResponse({"code": 10107, "error": "设置默认地址失败"})

            # 提交事务
            transaction.savepoint_commit(sid)

        return JsonResponse({"code": 200, "data": "设置默认地址成功"})


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
