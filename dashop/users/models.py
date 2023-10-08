from django.db import models


class UserProfile(models.Model):
    """
    用户表
    用户名、密码、邮箱、手机号、是否激活、创建时间、更新时间
    """
    username = models.CharField(max_length=11, verbose_name="用户名", unique=True)
    password = models.CharField(max_length=32, verbose_name="密码")
    email = models.EmailField(verbose_name="邮箱", unique=True)
    phone = models.CharField(max_length=11, verbose_name="手机号", unique=True)
    is_active = models.BooleanField(default=False, verbose_name="是否激活")
    created_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_time = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        # 表名: 应用名_类名非驼峰
        db_table = "users_user_profile"
