import json
import jwt
from dashop import settings
from django.http import JsonResponse, HttpRequest
from users.models import UserProfile


def logging_check(func):
    """
    token校验的逻辑
    1.获取token
    2.校验token
      2.1 失败:则直接返回
      2.2 成功:执行视图func(...)
    """

    def wrapper(self, request, username, *args, **kwargs):
        token = request.headers.get("Authorization")
        print(f"token -> {token}, {username}")

        try:
            payload = jwt.decode(token, settings.JWT_TOKEN_KEY, algorithms="HS256")
        except Exception as e:
            print(e)
            # token有问题
            return JsonResponse({"code": 403})

        payload_username = payload.get("username")
        if username != payload_username:
            # 用户名不匹配
            return JsonResponse({"code": 403})

        user = UserProfile.objects.get(username=username)
        request.myuser = user

        # 封装mydata属性:请求体数据
        request_data = request.body
        if request_data:
            request.mydata = json.loads(request_data)

        return func(self, request, username, *args, **kwargs)

    return wrapper
