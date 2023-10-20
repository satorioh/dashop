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
