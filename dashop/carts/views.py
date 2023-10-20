from django.core.cache import caches
from django.http import JsonResponse
from django.views import View

from dashop import settings
from goods.models import SKU
from utils.logging_dec import logging_check


class CartsView(View):
    @logging_check
    def post(self, request, username):
        """
        添加购物车视图逻辑
        Redis中存储的购物车数据结构如下:
        "carts_1": {
            "1": [3,1],
            "2": [2,0],
            "3": [5,1]
        }
        # Redis-key: carts_1 其中1代表用户id
        # "1" "2" "3" : 代表的是商品的sku_id
        # [3,1] : 3代表数量,1代表选中状态
        # 1代表选中状态,0代表未选中状态
        """
        data = request.mydata
        sku_id = data.get("sku_id")
        count = data.get("count")
        count = int(count)

        # 获取该用户原来购物车的数据
        user = request.myuser
        key = f"carts_{user.id}"
        # {"1":[5,1], "2":[3,0]}
        carts_dict = caches["carts"].get(key)
        # 如果为None,则赋值为空字典 {}
        if not carts_dict:
            carts_dict = {}

        # 判断商品种类数量是否超过100种
        if len(carts_dict) > 100:
            return JsonResponse({"code": 10302, "error": "最多添加100种商品"})

        if sku_id not in carts_dict:
            carts_dict[sku_id] = [count, 1]
        else:
            # 现在: "2" 加8个
            carts_dict[sku_id][0] += count
            carts_dict[sku_id][1] = 1

        # 把其他商品的选中状态都设置为0
        # {"1":[5,1], "2":[8,0],"6":[1,1]}
        for sid in carts_dict:
            if sid != sku_id:
                carts_dict[sid][1] = 0

        # 更新到Redis数据库
        caches["carts"].set(key, carts_dict)

        # 返回响应
        result = {
            "code": 200,
            "data": {
                "carts_count": len(carts_dict)
            },
            "base_url": settings.PIC_URL
        }

        return JsonResponse(result)

    @logging_check
    def get(self, request, username):
        """
        查询购物车视图逻辑
        1.从Redis中查询数据
        2.从MySQL中查询数据
        {"code":200,"skus_list":[],"base_url":"xxx"}
        """
        user_id = request.myuser.id
        # {"1":[3,1], "2":[5,0]}
        carts_dict = self.get_carts_dict(user_id)

        skus_list = []
        for sku_id in carts_dict:
            sku = SKU.objects.get(id=sku_id)
            values = sku.sale_attr_value.all()

            sku_dict = {
                "id": sku.id,
                "name": sku.name,
                "count": carts_dict[sku_id][0],
                "selected": carts_dict[sku_id][1],
                "default_image_url": str(sku.default_image_url),
                "price": sku.price,
                "sku_sale_attr_name": [i.spu_sale_attr.name for i in values],
                "sku_sale_attr_val": [i.name for i in values]
            }
            skus_list.append(sku_dict)

        result = {
            "code": 200,
            "data": skus_list,
            "base_url": settings.PIC_URL
        }

        return JsonResponse(result)

    @logging_check
    def delete(self, request, username):
        """
        删除购物车视图逻辑
        1.获取请求体数据(sku_id)
        2.获取购物车数据的字典,删除对应的key
        3.更新到Redis数据库
        4.返回响应
        """
        sku_id = request.mydata.get("sku_id")
        user_id = request.myuser.id
        # {"1":[3,1], "2":[5,0]}
        carts_dict = self.get_carts_dict(user_id)
        try:
            carts_dict.pop(str(sku_id))
        except Exception as e:
            return JsonResponse({"code": 10301, "error": "该商品不存在"})
        # 更新到Redis
        self.update_carts(user_id, carts_dict)

        # 返回响应
        result = {
            "code": 200,
            "data": {
                "carts_count": len(carts_dict)
            },
            "base_url": settings.PIC_URL
        }

        return JsonResponse(result)

    @logging_check
    def put(self, request, username):
        """
        修改购物车视图逻辑
        - +1操作：add
        - -1操作：del
        - 单选：select
        - 取消单选：unselect
        - 全选：selectall
        - 取消全选：unselectall
        """
        # 1.获取请求体数据
        data = request.mydata
        sku_id = data.get("sku_id")
        state = data.get("state")
        # 2.获取购物车数据字典[redis]
        # {"1":[3,1], "2":[5,0]}
        user_id = request.myuser.id
        carts_dict = self.get_carts_dict(user_id)
        # 3.修改字典,更新到redis数据库
        # sku_id:当为全选或取消全选时,它为None
        if sku_id and sku_id not in carts_dict:
            return JsonResponse({"code": 10303, "error": "该商品不存在"})

        # {"1":[3,1], "2":[5,0]}
        if state == "add":
            carts_dict[sku_id][0] += 1
        elif state == "del":
            carts_dict[sku_id][0] -= 1
        elif state == "select":
            carts_dict[sku_id][1] = 1
        elif state == "unselect":
            carts_dict[sku_id][1] = 0
        elif state == "selectall":
            # {"1":[3,1], "2":[5,0], "3":[4,0]}
            for sid in carts_dict:
                carts_dict[sid][1] = 1
        elif state == "unselectall":
            for sid in carts_dict:
                carts_dict[sid][1] = 0
        else:
            return JsonResponse({"code": 10304, "error": "违法请求"})

        # 更新到Redis数据库
        self.update_carts(user_id, carts_dict)

        # 4.返回响应
        return JsonResponse({"code": 200})

    @staticmethod
    def get_carts_dict(user_id):
        """
        功能函数:获取购物车数据的字典
        """
        key = f"carts_{user_id}"
        carts_dict = caches["carts"].get(key)
        if not carts_dict:
            return {}

        return carts_dict

    @staticmethod
    def update_carts(user_id, carts_dict):
        """
        功能函数:更新Redis中购物车数据
        """
        key = f"carts_{user_id}"
        caches["carts"].set(key, carts_dict)
