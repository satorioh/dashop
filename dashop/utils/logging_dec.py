import jwt
from dashop import settings
from django.http import JsonResponse, HttpRequest


def logging_check(func):
    """
    token校验的逻辑
    1.获取token
    2.校验token
      2.1 失败:则直接返回
      2.2 成功:执行视图func(...)
    """

    def wrapper(self, request, *args, **kwargs):
        token = request.headers.get("Authorization")
        print(f"token -> {token}")

        try:
            payload = jwt.decode(token, settings.JWT_TOKEN_KEY, algorithms="HS256")
        except Exception as e:
            print(e)
            # token有问题
            return JsonResponse({"code": 403})
        return func(self, request, *args, **kwargs)

    return wrapper
