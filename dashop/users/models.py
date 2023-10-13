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


class Address(models.Model):
    """收货地址表"""
    # 外键
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name="用户")
    # 收件人、地址、邮编、手机号
    receiver = models.CharField(max_length=10, verbose_name="收件人")
    address = models.CharField(max_length=100, verbose_name="地址")
    postcode = models.CharField(max_length=6, verbose_name="邮编")
    receiver_mobile = models.CharField(max_length=11, verbose_name="手机号")
    # 标签[家、公司、宿舍]
    tag = models.CharField(verbose_name="标签", max_length=10)
    # 是否为默认地址
    is_default = models.BooleanField(default=False, verbose_name="默认地址")
    # 伪删除[0-未删除,1-删除]
    is_delete = models.BooleanField(default=False, verbose_name="伪删除")
    # 创建时间 更新时间
    created_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_time = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        # 修改表名: 应用名_类名非驼峰
        db_table = "users_address"


class WeiboProfile(models.Model):
    """
    微博表:和用户表是一对一关系
    """
    # null=True:用户到绑定注册页后直接关闭页面,没有执行绑定注册流程
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, null=True)
    wuid = models.CharField(max_length=10, unique=True, db_index=True)
    access_token = models.CharField(max_length=32)

    class Meta:
        db_table = "users_weibo_profile"
