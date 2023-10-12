from django.urls import path
from . import views

urlpatterns = [
    # 注册功能:v1/users/register
    path("register", views.register),
    # 登录功能:v1/users/login
    path("login", views.login),
    # 收货地址[新增和查询]:v1/users/<username>/address
    path("<str:username>/address", views.AddressView.as_view()),
    # 收货地址[修改和删除]:v1/users/<username>/address/<id>
    path("<str:username>/address/<int:id>", views.AddressView.as_view()),
    # 默认地址:v1/users/<username>/address/default
    path("<str:username>/address/default", views.DefaultAddressView.as_view()),
    # 邮件激活:v1/users/activation
    path("activation", views.active_view),
]
