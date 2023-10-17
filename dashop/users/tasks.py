"""
users/tasks.py
存放用户模块应用下所有的异步任务
"""
from django.core import mail
from dashop import settings
from dashop.celery import app
from utils.sms_api import send_sms


@app.task
def async_send_active_email(email, username, verify_url):
    """
    功能函数:发送激活邮件
    """
    subject = "达达商城激活邮件"
    message = f"""
    尊敬的 {username} 你好,请点击激活链接进行激活: {verify_url}
    """

    mail.send_mail(
        # 标题、正文、发件人、收件人
        subject=subject,
        message=message,
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[email]
    )


@app.task
def async_send_message(tid, mobile, datas):
    send_sms(tid, mobile, datas)
