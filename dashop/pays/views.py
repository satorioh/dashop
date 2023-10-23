from alipay import AliPay
from django.http import HttpResponse
from django.views import View

from dashop import settings
from orders.models import OrderInfo


class MyAlipay(View):
    def __init__(self):
        super().__init__()
        self.alipay = AliPay(
            # 应用ID:控制台获取
            appid=settings.ALIPAY_APPID,
            # 异步通知地址[有支付结果]
            app_notify_url=settings.ALIPAY_NOTIFY_URL,
            # 应用私钥[用于签名]
            app_private_key_string=open(settings.ALIPAY_KEY_DIR + "app_private_key.pem").read(),
            # 支付宝公钥[用于签名]
            alipay_public_key_string=open(settings.ALIPAY_KEY_DIR + "alipay_public_key.pem").read(),
            # 签名使用算法:非对称加密
            sign_type="RSA2",
            # False:线上环境,True:沙箱环境
            debug=True
        )


class ReturnUrlView(MyAlipay):
    def get(self, request):
        """
        同步通知地址:只有支付信息,没有支付结果
        调用主动查询接口,查询支付结果
        """
        data = request.GET
        out_trade_no = data.get("out_trade_no")
        trade_no = data.get("trade_no")

        # result:
        """
                "code": "10000",
        "msg": "Success",
        "trade_no": "2013112011001004330000121536",
        "out_trade_no": "6823789339978248",
        "open_id": "2088102122524333",
        "buyer_logon_id": "159****5620",
        "trade_status": "TRADE_CLOSED",
        "total_amount": "88.88",
        "trans_currency": "TWD",
        "settle_currency": "USD",
        "settle_amount": 2.96,
        "pay_currency": 1,
        "pay_amount": "8.88",
        "settle_trans_rate": "30.025",
        "trans_pay_rate": "0.264",
        "alipay_store_id": "2015040900077001000100001232",
        "buyer_pay_amount": "8.88",
        "point_amount": "10",
        "invoice_amount": "12.11",
        "send_pay_date": "2014-11-27 15:45:57",
        "receipt_amount": "15.25",
        "store_id": "NJ_S_001",
        "terminal_id": "NJ_T_001",
        "fund_bill_list": []
        """
        result = self.alipay.api_alipay_trade_query(
            out_trade_no=out_trade_no,
            trade_no=trade_no
        )
        # 获取支付结果
        pay_result = result.get("trade_status")
        if pay_result == "TRADE_SUCCESS":
            # 修改订单状态:1 ---> 2
            order = OrderInfo.objects.get(order_id=out_trade_no)
            order.status = 2
            order.save()
            # 返回响应
            return HttpResponse("GET请求:支付成功")
        else:
            return HttpResponse("GET请求:支付失败")
