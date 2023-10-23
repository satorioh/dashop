import time

from django.db import transaction
from django.http import JsonResponse
from django.views import View

from carts.views import CartsView
from dashop import settings
from goods.models import SKU
from orders.models import OrderInfo, OrderGoods
from users.models import Address
from utils.logging_dec import logging_check


# Create your views here.
class OrdersAdvanceView(View):
    @logging_check
    def get(self, request, username):
        """
        订单确认页视图逻辑
        1.获取查询参数
        2.查数据
          2.1 所有的收货地址
          2.2 商品的相关信息
        3.返回响应
        {"code": 200,
         "data:{"addresses":[],"sku_list":[]},
         "base_url":"xxx"
        }
        """
        buy_num = 0
        sku_id = 0

        settle = request.GET.get("settlement_type")
        if settle not in ["0", "1"]:
            return JsonResponse({"code": 10400, "error": "违法请求"})

        # 1.查询收货地址相关信息
        addresses = []
        user = request.myuser
        addrs = Address.objects.filter(user_profile=user, is_delete=False)
        for addr in addrs:
            addr_dict = {
                "id": addr.id,
                "name": addr.receiver,
                "mobile": addr.receiver_mobile,
                "title": addr.tag,
                "address": addr.address
            }
            # 默认地址要放在列表中的第1个元素
            if addr.is_default:
                addresses.insert(0, addr_dict)
            else:
                addresses.append(addr_dict)

        # 2.查询商品相关信息
        sku_list = []
        if settle == "0":
            # 购物车链接
            # Redis中查询数据字典
            # {"1":[3,1], "2":[5,1]}
            carts_dict = CartsView().get_carts_dict(user.id)
            carts_dict_select = {k: v for k, v in carts_dict.items() if v[1] == 1}
            skus = SKU.objects.filter(id__in=carts_dict_select)
            for sku in skus:
                vals = sku.sale_attr_value.all()
                sku_dict = {
                    "id": sku.id,
                    "name": sku.name,
                    # {"1":[3,1], "2":[5,1]}
                    "count": carts_dict_select[str(sku.id)][0],
                    "selected": 1,
                    "default_image_url": str(sku.default_image_url),
                    "price": sku.price,
                    "sku_sale_attr_name": [i.spu_sale_attr.name for i in vals],
                    "sku_sale_attr_val": [i.name for i in vals]
                }
                sku_list.append(sku_dict)
        else:
            # 立即购买链条
            sku_id = request.GET.get("sku_id")
            buy_num = request.GET.get("buy_num")
            buy_num = int(buy_num)

            try:
                sku = SKU.objects.get(id=sku_id, is_launched=True)
            except Exception as e:
                return JsonResponse({"code": 10402, "error": "该商品已下架"})

            vals = sku.sale_attr_value.all()
            sku_list = [{
                "id": sku.id,
                "name": sku.name,
                "count": buy_num,
                "selected": 1,
                "default_image_url": str(sku.default_image_url),
                "price": sku.price,
                "sku_sale_attr_name": [i.spu_sale_attr.name for i in vals],
                "sku_sale_attr_val": [i.name for i in vals]
            }]

        result = {
            "code": 200,
            "data": {
                "addresses": addresses,
                "sku_list": sku_list,
                "buy_count": buy_num,
                "sku_id": sku_id,
            },
            "base_url": settings.PIC_URL
        }

        return JsonResponse(result)


class OrdersView(View):
    @logging_check
    def post(self, request, username):
        """
        创建订单视图逻辑
        1.获取请求体数据
        2.3个ORM操作
          2.1 订单表中插入数据
          2.2 订单商品表中插入数据
          2.3 更新sku的库存和销量
        3.返回响应[API文档]
        """
        data = request.mydata
        addr_id = data.get("address_id")
        settle = data.get("settlement_type")

        if settle not in ["0", "1"]:
            return JsonResponse({"code": 10404, "error": "违法请求"})

        user = request.myuser
        # 订单编号:20230815104500+用户ID
        order_id = time.strftime("%Y%m%d%H%M%S") + str(user.id)
        total_amount = 0
        total_count = 0
        # 收货地址
        try:
            addr = Address.objects.get(id=addr_id, is_delete=False)
        except Exception as e:
            return JsonResponse({"code": 10405, "error": "收货地址不存在"})

        # 购物车链条
        # 开启事务
        with transaction.atomic():
            # 创建存储点
            sid = transaction.savepoint()
            # 1.订单表中插入数据
            order = OrderInfo.objects.create(
                user_profile=user,
                order_id=order_id,
                total_amount=total_amount,
                total_count=total_count,
                pay_method=1,
                freight=0,
                status=1,
                receiver=addr.receiver,
                address=addr.address,
                receiver_mobile=addr.receiver_mobile,
                tag=addr.tag,
            )
            carts_dict = CartsView().get_carts_dict(user.id)
            if settle == "0":
                # 购物车链条
                # 2.更新sku的库存和销量
                # {"1":[3,1],"2":[5,1]}
                carts_dict_1 = {k: v for k, v in carts_dict.items() if v[1] == 1}
                for skuid in carts_dict_1:
                    # 校验上下架状态
                    try:
                        sku = SKU.objects.get(id=skuid, is_launched=True)
                    except Exception as e:
                        # 回滚+返回
                        transaction.savepoint_rollback(sid)
                        return JsonResponse({"code": 10406, "error": "该商品已下架"})

                    # 校验库存
                    # {"1":[3,1],"2":[5,1]}
                    count = carts_dict_1[skuid][0]
                    if count > sku.stock:
                        # 回滚+返回
                        transaction.savepoint_rollback(sid)
                        return JsonResponse({"code": 10407, "error": f"{sku.name}库存不足,仅剩{sku.stock}件"})

                    # 更新库存和销量[一查二改三保存]
                    sku.stock -= count
                    sku.sales += count
                    sku.save()

                    # 3.订单商品表中插入数据
                    OrderGoods.objects.create(
                        order_info=order,
                        sku=sku,
                        count=count,
                        price=sku.price,
                    )

                    # 处理总金额和总销量
                    total_amount += sku.price * count
                    total_count += count

                # 更新总金额和总销量
                order.total_amount = total_amount
                order.total_count = total_count
                order.save()

                # 提交事务
                transaction.savepoint_commit(sid)
            else:
                # 立即购买链条
                buy_count = int(data.get("buy_count"))
                sku_id = data.get("sku_id")
                # 2.更新sku的库存和销量
                try:
                    sku = SKU.objects.get(id=sku_id, is_launched=True)
                except Exception as e:
                    # 回滚+返回
                    transaction.savepoint_rollback(sid)
                    return JsonResponse({"code": 10408, "error": "该商品已下架"})

                if buy_count > sku.stock:
                    return JsonResponse({"code": 10409, "error": "库存不足"})

                sku.stock -= buy_count
                sku.sales += buy_count
                sku.save()
                # 3.订单商品表中插入数据
                OrderGoods.objects.create(
                    order_info=order,
                    sku=sku,
                    count=buy_count,
                    price=sku.price,
                )
                total_amount += sku.price * buy_count
                total_count += buy_count

                order.total_amount = total_amount
                order.total_count = total_count
                order.save()

                transaction.savepoint_commit(sid)

        if settle == "0":
            # 删除购物车中选中状态为1的商品
            carts_dict_0 = {k: v for k, v in carts_dict.items() if v[1] == 0}
            # 更新到Redis数据库
            CartsView().update_carts(user.id, carts_dict_0)
            carts_count = len(carts_dict_0)
        else:
            carts_count = len(carts_dict)

        # 返回响应
        result = {
            "code": 200,
            "data": {
                "saller": "达达商城",
                "total_amount": total_amount,
                "order_id": order_id,
                # 第三方支付的路由
                "pay_url": self.get_pay_url(order_id, float(total_amount)),
                "carts_count": carts_count
            }
        }

        return JsonResponse(result)
