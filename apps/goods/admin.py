from django.contrib import admin
from django.core.cache import cache

from apps.goods.models import *
from celery_tasks.tasks import *


class BaseAdmin(admin.ModelAdmin):
    """模型管理类"""

    # list_display = ['id']

    def save_model(self, request, obj, form, change):
        """管理后台新增或修改数据时调用"""
        super().save_model(request, obj, form, change)
        # obj表示要保存的对象，调用save(),将对象保存到数据库中
        obj.save()
        # 重新生成静态首页
        generate_static_index_html()
        # generate_static_index_html.delay()
        # 修改了数据库数据就需要删除缓存
        cache.delete("data")


    def delete_model(self, request, obj):
        """管理后台删除一条数据时调用"""
        super().delete_model(request, obj)
        obj.delete()
        # 重新生成静态首页
        generate_static_index_html()
        # generate_static_index_html.delay()
        cache.delete("data")


class GoodsCategoryAdmin(BaseAdmin):
    pass


class GoodsSPUAdmin(BaseAdmin):
    pass


class GoodsSKUAdmin(BaseAdmin):
    pass


class IndexSlideGoodsAdmin(BaseAdmin):
    pass


class IndexPromotionAdmin(BaseAdmin):
    pass


class IndexCategoryGoodsAdmin(BaseAdmin):
    pass


admin.site.register(GoodsCategory, GoodsCategoryAdmin)
admin.site.register(GoodsSPU, GoodsSPUAdmin)
admin.site.register(GoodsSKU, GoodsSKUAdmin)
admin.site.register(IndexSlideGoods, IndexSlideGoodsAdmin)
admin.site.register(IndexPromotion, IndexPromotionAdmin)
admin.site.register(IndexCategoryGoods, IndexCategoryGoodsAdmin)
