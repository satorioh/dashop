import base64
import json
from datetime import datetime
import random
import requests

from django.db import transaction
from django.http import JsonResponse, HttpRequest
from django.views import View
from django.core.cache import caches

from users.models import UserProfile, Address, WeiboProfile
from dashop import settings
from users.tasks import async_send_active_email, async_send_message
from utils.logging_dec import logging_check
from utils.helper import md5_string, make_token, get_verify_url


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

    # 短信验证码校验
    key2 = f"sms_{phone}"
    redis_code = caches["sms"].get(key2)
    if not redis_code:
        return JsonResponse({"code": 10110, "error": "验证码已过期,请重新获取"})

    if str(redis_code) != verify:
        return JsonResponse({"code": 10111, "error": "验证码错误,请重新输入"})

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

    # 发送激活邮件
    verify_url = get_verify_url(username)
    async_send_active_email.delay(email, username, verify_url)

    # 签发token
    token = make_token(username)

    # 清除短信验证码,释放内存
    caches["sms"].delete(key2)

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


def active_view(request):
    """
    邮件激活视图逻辑
    1.获取查询参数:code
    2.校验
    3.激活用户:一查二改三保存
    # request.GET:获取查询参数
    # request.POST:获取请求体[form表单]
    # request.body:获取请求体[json]
    # request.headers:获取请求头
    """
    # code:OTgyNl9qaW5namluZw==
    code = request.GET.get("code")
    # code_str:1016_liying
    code_str = base64.b64decode(code.encode()).decode()
    code_num, username = code_str.split("_")
    # Redis中获取随机数
    key = f"active_{username}"
    redis_num = caches["default"].get(key)

    if str(redis_num) != code_num:
        return JsonResponse({"code:": 10108, "error": "激活失败"})

    # 激活用户
    try:
        user = UserProfile.objects.get(username=username)
    except Exception as e:
        print(e)
        return JsonResponse({"code:": 10109, "error": "服务器繁忙，请稍后再试"})

    user.is_active = True
    user.save()

    return JsonResponse({"code": 200, "data": "激活成功"})


def sms_view(request):
    """
    发送短信验证码视图逻辑
    1.获取请求体数据[手机号]
    2.发短信[调接口]
    3.返回响应
    """
    mobile = json.loads(request.body).get("phone")
    # Redis: {"sms_13603263409": 1016}
    # 判断1分钟之内是否发过
    key1 = f"sms_ex_{mobile}"
    r = caches["sms"].get(key1)
    if r:
        return JsonResponse({"code": 10109, "error": "发送过于频繁"})

    code = random.randint(1000, 9999)
    datas = (code, 5)
    # celery异步发送短信验证码
    async_send_message.delay("1", mobile, datas)

    # 存入Redis数据库
    # 60s:用于控制短信发送频率
    caches["sms"].set(key1, code, 60)
    # 300s:用于短信验证码的校验
    key2 = f"sms_{mobile}"
    caches["sms"].set(key2, code, 300)

    return JsonResponse({"code": 200, "data": "验证码发送成功"})


class WeiboCodeView(View):
    def get(self, request):
        """
        获取授权码code视图逻辑
        API文档:微博API文档
        响应: {"code":200, "oauth_url":"xxx"}
        """
        oauth_url = f"https://api.weibo.com/oauth2/authorize?client_id={settings.WEIBO_CLIENT_ID}&redirect_uri={settings.WEIBO_REDIRECT_URI}&response_type=code"

        result = {
            "code": 200,
            "oauth_url": oauth_url
        }

        return JsonResponse(result)


class WeiboTokenView(View):
    def get(self, request):
        """
        获取访问令牌access_token视图逻辑
        1.获取授权码code
        2.利用code获取访问令牌access_token
        """
        code = request.GET.get("code")
        print(f"weibo code -> {code}")
        # 访问令牌微博接口文档
        url = "https://api.weibo.com/oauth2/access_token"
        data = {
            "client_id": settings.WEIBO_CLIENT_ID,
            "client_secret": settings.WEIBO_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.WEIBO_REDIRECT_URI
        }
        resp = requests.post(url=url, data=data).json()
        print(f"weibo token resp -> {resp}")
        """
        resp返回格式如下：
               {
               "access_token": "ACCESS_TOKEN",
               "expires_in": "7200",
               "remind_in": "7200",
               "uid": "1404376560"
               }
        """
        wuid = resp.get("uid")
        access_token = resp.get("access_token")

        """
        情况1:
            第一次扫码登录，即完全无记录的：把wuid和微博token存入微博表，然后跳转到绑定注册页面[201]
        情况2:
            有授权，但未绑定的（有wuid和微博token，没有user_profile的）：跳转到绑定注册页面[201]
        情况3：
            已经和正式账号绑定过：生成本系统的token，返回前端，跳转首页[200]

        200响应:{"code":200, "token":token, "username":username"}
        201响应:{"code":201,"uid": wuid} 
        """
        try:
            wuser = WeiboProfile.objects.get(wuid=wuid)
        except Exception as e:
            # 第一次扫码登录
            print("第一次扫码登录")
            WeiboProfile.objects.create(wuid=wuid, access_token=access_token)
            return JsonResponse({"code": 201, "uid": wuid})

        user = wuser.user_profile
        if not user:
            # 没有和正式用户绑定过
            print("没有和正式用户绑定过")
            return JsonResponse({"code": 201, "uid": wuid})

        # 已经正式绑定过
        username = user.username
        token = make_token(username)

        return JsonResponse({"code": 200, "token": token, "username": username})

    def post(self, request):
        """
           第三方微博登录
           没有账号,请注册的视图逻辑
           1.获取请求体数据
           2.合法性校验
           3.校验用户名是否被占用
           4.发送激活邮件
           5.绑定并返回响应
        """
        data = json.loads(request.body)
        username = data.get("username")
        password = data.get("password")
        email = data.get("email")
        phone = data.get("phone")
        wuid = data.get("uid")

        # 2.数据合法性校验
        if len(username) < 6 or len(username) > 11:
            return JsonResponse({"code": 10113, "error": "用户名不合法"})

        if len(password) < 6 or len(password) > 12:
            return JsonResponse({"code": 10114, "error": "密码不合法"})

        if len(phone) != 11:
            return JsonResponse({"code": 10115, "error": "手机号不合法"})

        # 校验用户名是否被占用
        user_query = UserProfile.objects.filter(username=username)
        if user_query:
            # 被占用
            return JsonResponse({"code": 10116, "error": "用户名被占用"})

        with transaction.atomic():
            # 1.创建存储点
            sid = transaction.savepoint()
            try:
                # 存入数据表
                user = UserProfile.objects.create(username=username, password=md5_string(password), email=email,
                                                  phone=phone)
                # 绑定
                wuser = WeiboProfile.objects.get(wuid=wuid)
                wuser.user_profile = user
                wuser.save()
            except Exception as e:
                transaction.savepoint_rollback(sid)
                return JsonResponse({"code": 10117, "error": "微博服务器繁忙,请稍后再试"})

            # 提交事务
            transaction.savepoint_commit(sid)

        # 发送激活邮件
        verify_url = get_verify_url(username)
        async_send_active_email.delay(email, username, verify_url)

        token = make_token(username)

        return JsonResponse({"code": 200, "token": token, "username": username})


class BindUserView(View):
    def post(self, request):
        """
        已有账号,请绑定视图逻辑
        1.获取请求体数据
        2.校验用户名和密码
        3.绑定并返回响应
        """
        data = json.loads(request.body)
        username = data.get("username")
        password = data.get("password")
        wuid = data.get("uid")

        try:
            user = UserProfile.objects.get(username=username, password=md5_string(password))
        except Exception as e:
            return JsonResponse({"code": 10111, "error": "用户名或密码错误"})

        # 微博用户和正式用户进行绑定
        # 一查二改三保存
        try:
            wuser = WeiboProfile.objects.get(wuid=wuid)
        except Exception as e:
            return JsonResponse({"code": 10112, "error": "微博服务器繁忙,请稍后再试"})

        wuser.user_profile = user
        wuser.save()

        token = make_token(username)

        return JsonResponse({"code": 200, "token": token, "username": username})
