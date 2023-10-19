from django.http import JsonResponse
from django.views.decorators.cache import cache_page

from dashop import settings
from goods.models import Catalog, SPU, SKU, SKUImage, SPUSaleAttr, SaleAttrValue, SPUSpecValue


# Create your views here.
@cache_page(60 * 5, cache="index")
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


@cache_page(300, cache="detail")
def detail_view(request, sku_id):
    """
    详情页展示视图逻辑
    {"code":200,"data":{},"base_url":"xxx"}
    """
    try:
        sku = SKU.objects.get(id=sku_id, is_launched=True)
    except Exception as e:
        return JsonResponse({"code": 10200, "error": "该商品已下架"})

    data = {}

    # 类1:类别id 类别name
    cata = sku.spu.catalog
    data["catalog_id"] = cata.id
    data["catalog_name"] = cata.name

    # 类2：SKU
    data["name"] = sku.name
    data["caption"] = sku.caption
    data["price"] = sku.price
    data["image"] = str(sku.default_image_url)
    data["spu"] = sku.spu.id

    # 类3：详情图片
    imgs = SKUImage.objects.filter(sku=sku)
    data["detail_image"] = str(imgs[0].image) if imgs else ""

    # 类4：销售属性
    attr_values = sku.sale_attr_value.all()
    data["sku_sale_attr_id"] = [i.spu_sale_attr.id for i in attr_values]
    data["sku_sale_attr_names"] = [i.spu_sale_attr.name for i in attr_values]

    # 类5：销售属性值
    data["sku_sale_attr_val_id"] = [i.id for i in attr_values]
    data["sku_sale_attr_val_names"] = [i.name for i in attr_values]

    # 销售属性和销售属性值的对应关系
    """
    "sku_all_sale_attr_vals_id": {
        "7": [11, 12],
        "8": [13]
    },
    "sku_all_sale_attr_vals_name": {
        "7": ["18寸", "19寸"],
        "8": ["蓝色"]
    },
    """
    dic1 = {}
    dic2 = {}

    sale_attrs = SPUSaleAttr.objects.filter(spu=sku.spu)
    # ids: [7, 8]
    ids = [i.id for i in sale_attrs]
    for id in ids:
        # id对应的销售属性值的<QuerySet []>
        values = SaleAttrValue.objects.filter(spu_sale_attr=id)
        dic1[id] = [i.id for i in values]
        dic2[id] = [i.name for i in values]

    data["sku_all_sale_attr_vals_id"] = dic1
    data["sku_all_sale_attr_vals_name"] = dic2

    # 类6和类7：规格属性名和规格属性值
    spec = {}
    # specs:规格属性值的<QuerySet []>
    specs = SPUSpecValue.objects.filter(sku=sku)
    for spe in specs:
        # key: 规格属性的名字
        key = spe.spu_spec.name
        # value: 规格属性值的名字
        value = spe.name
        spec[key] = value

    data["spec"] = spec

    result = {
        "code": 200,
        "data": data,
        "base_url": settings.PIC_URL
    }

    return JsonResponse(result)
