from django.http import JsonResponse
from dashop import settings
from goods.models import Catalog, SPU, SKU


# Create your views here.
def index_view(request):
    """
    商品模块首页展示
    {"code":200,"data":[],"base_url":""}
    """
    data = []
    # 1.查询所有类别:<QuerySet [..,..,..]>
    all_cata = Catalog.objects.all()
    for cata in all_cata:
        # 组装每个类别下的3个sku的列表
        sku_list = []
        spus = SPU.objects.filter(catalog=cata)
        skus = SKU.objects.filter(spu__in=spus)[:3]
        for sku in skus:
            sku_dict = {
                "skuid": sku.id,
                "caption": sku.caption,
                "name": sku.name,
                "price": sku.price,
                "image": str(sku.default_image_url)
            }
            sku_list.append(sku_dict)

        cata_dict = {
            "catalog_id": cata.id,
            "catalog_name": cata.name,
            "sku": sku_list
        }
        data.append(cata_dict)

    result = {
        "code": 200,
        "data": data,
        "base_url": settings.PIC_URL
    }

    return JsonResponse(result)
