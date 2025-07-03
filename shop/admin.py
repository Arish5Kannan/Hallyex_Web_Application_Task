from django.contrib import admin
from shop.models import *
# Register your models here.
admin.site.register(Category)
admin.site.register(Product)
admin.site.register(Cart)
admin.site.register(Favourite)
admin.site.register(Profile)
admin.site.register(Orders)

