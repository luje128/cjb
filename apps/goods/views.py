from django.contrib.auth import logout
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.shortcuts import render, redirect

# Create your views here.
from django.views.generic import View
from django_redis import get_redis_connection

from apps.goods.models import IndexCategoryGoods, IndexPromotion, IndexSlideGoods, GoodsCategory, GoodsSKU


class BaseCartView(View):
    def get_cart_count(self, request):
        """获取购物车中商品的数量"""
        cart_count = 0
        # 如果用户登录，就获取购物车数据
        if request.user.is_authenticated():
            # 获取 StrictRedis 对象
            strict_redis = get_redis_connection()  # type: StrictRedis
            # 获取用户id
            user_id = request.user.id
            key = 'cart_%s' % user_id
            # 从redis中获取购物车数据，返回字典
            cart_dict = strict_redis.hgetall(key)
            # 遍历购物车字典的值，累加购物车的值
            for c in cart_dict.values():
                cart_count += int(c)
        return cart_count


class Goods_View(BaseCartView):
    def get(self, request):
        """显示首页"""
        # 读取缓存：键=值
        context = cache.get("data")
        print(context)
        if not context:
            print("缓存为空，从mysql数据库读取")

            # 查询商品类别数据
            categories = GoodsCategory.objects.all()

            # 查询商品轮播轮数据
            # index为表示显示先后顺序的一个字段，值小的会在前面
            slide_skus = IndexSlideGoods.objects.all().order_by('index')

            # 查询商品促销活动数据
            promotions = IndexPromotion.objects.all().order_by('index')

            # 查询类别商品数据
            for category in categories:
                # 查询某一类别下的文字类别商品
                text_skus = IndexCategoryGoods.objects.filter(
                    category=category, display_type=0).order_by('index')
                # 查询某一类别下的图片类别商品
                img_skus = IndexCategoryGoods.objects.filter(
                    category=category, display_type=1).order_by('index')

                # 动态地给类别新增实例属性
                category.text_skus = text_skus
                # 动态地给类别新增实例属性
                category.img_skus = img_skus

            # 查询购物车中的商品数量
            cart_count = 0

            # 定义模板数据
            context = {
                # 商品类别
                'categories': categories,
                # 商品轮播
                'slide_skus': slide_skus,
                # 促销活动
                'promotions': promotions,
                # 购物车商品数量
                'cart_count': cart_count,
            }
            # 保存字典数据到Redis缓存中
            # 参数1: 键名
            # 参数2: 缓存的字典数据
            # 参数3: 缓存失效时间1分钟,单位秒
            cache.set("data", context, 10)
        else:
            print("使用缓存")
        # 获取首页购物车的总数
        cart_count = self.get_cart_count(request)
        # 字典新增一个属性和值
        context.update(cart_count=cart_count)
        # 响应请求，返回html界面
        return render(request, 'index.html', context)


class Logout_View(View):
    def get(self, request):
        logout(request)
        return redirect(reverse("goods:index"))


class DetailView(BaseCartView):
    def get(self, request, sku_id):

        # 查询商品详情信息
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            # 查询不到商品则跳转到首页
            # return HttpResponse('商品不存在')
            return redirect(reverse('goods:index'))

        # 获取所有的类别数据
        categories = GoodsCategory.objects.all()

        # 获取最新推荐
        new_skus = GoodsSKU.objects.filter(
            category=sku.category).order_by('-create_time')[0:2]

        # 查询其它规格的商品
        other_skus = sku.spu.goodssku_set.exclude(id=sku.id)

        # 获取购物车中的商品数量
        cart_count = self.get_cart_count(request)
        # 如果是登录的用户
        if request.user.is_authenticated():
            # 获取用户id
            user_id = request.user.id
            # 从redis中获取购物车信息
            redis_conn = get_redis_connection("default")
            # 保存用户的历史浏览记录
            # history_用户id: [3, 1, 2]
            # 移除现有的商品浏览记录
            key = 'history_%s' % request.user.id
            redis_conn.lrem(key, 0, sku.id)
            # 从左侧添加新的商品浏览记录
            redis_conn.lpush(key, sku.id)
            # 控制历史浏览记录最多只保存5项(包含头尾)
            redis_conn.ltrim(key, 0, 4)

        # 定义模板数据
        context = {
            'categories': categories,
            'sku': sku,
            'new_skus': new_skus,
            'cart_count': cart_count,
            'other_skus': other_skus,
        }

        # 响应请求,返回html界面
        return render(request, 'detail.html', context)
