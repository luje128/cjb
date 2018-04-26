import re

from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.db import IntegrityError

from django.http import HttpResponse
from django.shortcuts import render, redirect

# Create your views here.
from django.views.generic import View
from django_redis import get_redis_connection
from itsdangerous import SignatureExpired, TimedJSONWebSignatureSerializer

from Mix.Login import LoginRequiredMixin
from apps.goods.models import GoodsSKU
from apps.users.models import User, Address
from dailyfresh import settings
from celery_tasks import tasks


# 测试一
def show_login(request):
    return render(request, "login.html")


# 测试二
def do_login(request):
    username = request.POST.get("username")
    password = request.POST.get("password")
    if username != "admin" and password != 12345:
        return render(request, "login.html")
    return HttpResponse("go")


# 注册类
class RegisterView(View):
    def get(self, request):
        # 进入页面
        return render(request, "register.html")

    def post(self, request):
        # 实现注册
        username = request.POST.get("username")
        password = request.POST.get("password")
        password2 = request.POST.get("password2")
        email = request.POST.get("email")
        allow = request.POST.get("allow")
        if not all([username, password, password2, email]):
            return render(request, "register.html", {"what": "您有信息未填写完整!", "isalert": 1})
        if password != password2:
            return render(request, "register.html", {"what": "密码错误，请重新输入!"})
        if allow != "on":
            return render(request, "register.html", {"what": "请点击同意用户协议!"})
        if not re.match(r"^[a-zA-Z0-9_.-]+@[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*\.[a-zA-Z0-9]{2,6}$", email):
            return render(request, "register.html", {"what": "邮箱格式错误，请重新输入！"})
        try:
            user = User.objects.create_user(username=username, password=password, email=email)
            # 默认激活，现在更改为未激活
            user.is_active = False
            # 保存
            user.save()
        except IntegrityError:
            return render(request, 'register.html', {'what': '用户名已存在'})

        # todo:发送激活邮件
        token = user.generate_active_token()
        # 同步发送会阻塞
        RegisterView.send_active_email(username, email, token)
        # celery异步发送
        # tasks.send_active_email.delay(username, email, token)

        return redirect("/users/login")

    @staticmethod
    def send_active_email(username, receiver, token):
        """发送激活邮件"""
        subject = "天天生鲜用户激活"  # 标题, 不能为空，否则报错
        message = ""  # 邮件正文(纯文本)
        sender = settings.EMAIL_FROM  # 发件人
        receivers = [receiver]  # 接收人, 需要是列表
        # 邮件正文(带html样式)
        html_message = ('<h3>尊敬的%s：感谢注册天天生鲜</h3>'
                        '请点击以下链接激活您的帐号:<br/>'
                        '<a href="http://127.0.0.1:8000/users/active/%s">'
                        'http://127.0.0.1:8000/users/active/%s</a>'
                        ) % (username, token, token)
        send_mail(subject, message, sender, receivers,
                  html_message=html_message)


# 数据加密类
class ActiveView(View):
    def get(self, request, token: str):
        """
        激活注册用户
        :param request:
        :param token: 对{'confirm':用户id}字典进行加密后的结果
        :return:
        """
        # 解密数据，得到字典
        dict_data = None
        try:
            s = TimedJSONWebSignatureSerializer(
                settings.SECRET_KEY, 3600 * 24)
            dict_data = s.loads(token.encode())  # type: dict
        except SignatureExpired:
            # 激活链接已经过期
            return HttpResponse('激活链接已经过期')

        # 获取用id
        user_id = dict_data.get('confirm')

        # 激活用户，修改表字段is_active=True
        User.objects.filter(id=user_id).update(is_active=True)

        # 响应请求
        return HttpResponse('激活成功，进入登录界面')


# 登陆类
class Login_View(View):
    def get(self, request):
        return render(request, "login.html")

    def post(self, request):
        username = request.POST.get("username")
        password = request.POST.get("password")
        remember = request.POST.get("remember")
        if not all([username, password]):
            return render(request, "login.html", {"content": "输入不完整"})
        # 判断用户名和密码是否正确
        user = authenticate(username=username, password=password)
        if user is None:
            return render(request, "login.html", {"content": "输入有误"})
        if user.is_active is False:
            return render(request, "login.html", {"content": "账号未激活"})
        login(request, user)
        if remember == "on":
            request.session.set_expiry(None)
        else:
            request.session.set_expiry(0)

        next = request.GET.get('next')
        if next is None:
            # 如果是直接登陆成功，就重定向到首页
            return redirect(reverse('goods:index'))
        else:
            # 如果是用户中心重定向到登陆页面，就回到用户中心
            return redirect(next)


# 用户中心-个人信息
class Center_Info(LoginRequiredMixin, View):
    def get(self, request):
        # 获取用户对象
        user = request.user

        # 查询用户最新添加的地址
        try:
            address = user.address_set.latest('create_time')
        except Address.DoesNotExist:
            address = None

        # 从redis查询出用户的商品浏览记录，返回的是列表例:a=[a1,a2]
        strict_redis = get_redis_connection("default")
        # 设置用户的id为键名
        key = "history_%s" % request.user.id
        # 最多5条记录，例：[1,2,3,4]
        goods_ids = strict_redis.lrange(key, 0, 4)
        # 真正的商品浏览顺序为原来保存在redis中的顺序
        # 手动排序，逐个查询，逐个添加
        skus = []
        for id in goods_ids:
            try:
                skus.append(GoodsSKU.objects.get(id=id))
            except GoodsSKU.DoesNotExist:
                pass

        # 定义模板数据
        data = {
            # 不需要主动传，django会传
            # 'user': user,
            'page': 1,
            'address': address,
            "skus": skus,
        }

        # 响应请求,返回html界面
        return render(request, 'user_center_info.html', data)


# 用户中心-全部订单
class Center_Order(LoginRequiredMixin, View):
    def get(self, request):
        data = {
            "page": 2
        }
        return render(request, "user_center_order.html", data)


# 用户中心-收货地址
class Center_Site(LoginRequiredMixin, View):
    def get(self, request):
        """显示用户地址"""
        user = request.user
        try:
            # 查询用户地址：根据创建时间排序，最近的时间在最前，取第1个地址
            address = Address.objects.filter(user=request.user) \
                .order_by('-create_time')[0]  # IndexError
            # IndexError
            # address = request.user.address_set.order_by('-create_time')[0]
            address = user.address_set.latest('create_time')
        except Exception:
            address = None

        data = {
            # 不需要主动传, django会自动传
            # 'user':user,
            'address': address,
            'page': 3
        }
        return render(request, 'user_center_site.html', data)

    def post(self, request):
        """"新增一个地址"""

        # 获取用户请求参数
        receiver = request.POST.get('receiver')
        address = request.POST.get('address')
        zip_code = request.POST.get('zip_code')
        mobile = request.POST.get('mobile')
        # 登录后django用户认证模块默认
        # 会保存user对象到request中
        user = request.user  # 当前登录用户

        # 校验参数合法性
        if not all([receiver, address, zip_code, mobile]):
            return render(request, 'user_center_site.html', {'error': '参数不完整'})

        # 保存地址到数据库中
        Address.objects.create(
            receiver_name=receiver,
            receiver_mobile=mobile,
            detail_addr=address,
            zip_code=zip_code,
            user=user
        )

        # 响应请求，刷新当前界面
        return redirect(reverse('users:site'))
