from django.conf.urls import url

from apps.goods import views

urlpatterns = [
    url("^index$", views.Goods_View.as_view(), name="index"),
    url("^logout$", views.Logout_View.as_view(), name="logout"),
    url(r'^detail/(?P<sku_id>\d+)$', views.DetailView.as_view(), name='detail'),
]
