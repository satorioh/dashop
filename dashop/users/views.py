import json

from django.http import JsonResponse, HttpRequest


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

    return JsonResponse({"code": 10100, "errmsg": ""})
