from django.contrib import admin

# Register your models here.
from django.contrib import admin
from apps.users.models import Test

admin.site.register(Test)
