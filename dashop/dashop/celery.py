"""
celery的配置文件:
"""
import os
from celery import Celery
from dashop import settings

# 1.设置临时环境变量
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dashop.settings')

# 2.初始化celery的应用
app = Celery("dashop_group",
             broker="redis://127.0.0.1:6379/15")

# 3.设置自动发现任务
app.autodiscover_tasks(settings.INSTALLED_APPS)
