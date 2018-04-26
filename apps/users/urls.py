from django.conf.urls import url

from apps.users import views

urlpatterns = [
    # 测试
    url(r"^show_login$", views.show_login),
    url(r"^do_login$", views.do_login),
    # 注册
    url(r"^Register$", views.RegisterView.as_view(), name="Register"),
    # 激活
    url(r'^active/(.+)$', views.ActiveView.as_view(), name='active'),
    # 登陆
    url(r'^login$', views.Login_View.as_view(), name='login'),
    # 用户中心-个人信息
    url(r'^center_info$', views.Center_Info.as_view(), name='info'),
    # 用户中心-全部订单
    url(r'^center_order$', views.Center_Order.as_view(), name='order'),
    # 用户中心-收货地址
    url(r'^center_site$', views.Center_Site.as_view(), name='site'),
]
