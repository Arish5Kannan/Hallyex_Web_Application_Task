from django.db import models
from django.contrib.auth.models import User
import os
import datetime

User._meta.get_field('email')._unique = True

def getFilename(request,filename):
    now = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    new_filename = '%s%s'%(now,filename)
    return os.path.join('uploads/',new_filename)

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_photo = models.ImageField(upload_to=getFilename,blank=True,null=True)
    fullname =models.CharField( max_length=50,blank=True,null=True)
    contact = models.CharField(max_length=15, blank=True, null=True)
    address = models.CharField(max_length=250, blank=True, null=True)
    def __str__(self):
        return self.user.username


class Category(models.Model):
    name = models.CharField(max_length=150,null=False,blank=False)  
    image = models.ImageField(upload_to=getFilename,null=True,blank=True) 
    description = models.TextField(max_length=500,null=False,blank=False) 
    status = models.BooleanField(default=False,help_text='0-show,1-hidden')
    trending = models.BooleanField(default=False,help_text='0-show,1-hidden')
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.name

class Product(models.Model):
    category = models.ForeignKey(Category,on_delete=models.CASCADE)
    name = models.CharField(max_length=150,null=False,blank=False)  
    vendor = models.CharField(max_length=150,null=False,blank=False) 
    quantity = models.IntegerField(null=False,blank=False) 
    old_price = models.FloatField(null=False,blank=False)
    new_price =  models.FloatField(null=False,blank=False)
    product_image = models.ImageField(upload_to=getFilename,null=False,blank=False) 
    description = models.TextField(max_length=500,null=False,blank=False) 
    status = models.BooleanField(default=False,help_text='0-show,1-hidden')
    trending = models.BooleanField(default=False,help_text='0-default,1-trending')
    discount = models.FloatField(default=0,null=False,blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.name    
class Cart(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE)  
    product = models.ForeignKey(Product,on_delete=models.CASCADE)  
    product_qty = models.IntegerField(blank=False,null=False)   
    created_at = models.DateTimeField(auto_now_add=True) 

    @property
    def total(self):
        return self.product_qty*self.product.new_price  
class Favourite(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE)  
    product = models.ForeignKey(Product,on_delete=models.CASCADE)     
    created_at = models.DateTimeField(auto_now_add=True)   
class Orders(models.Model):
    STATUS_CHOICES = [
        ('Pending','Pending'),
        ('Processing','Processing'),
        ('Shipped','Shipped'),
        ('Delivered','Delivered'),
        ('Cancelled','Cancelled')
    ]
    user = models.ForeignKey(User,on_delete=models.CASCADE)  
    order_status = models.CharField(max_length=50,default="Pending",choices=STATUS_CHOICES)
    total_price = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True) 
    def __str__(self):
        return f"order {self.id} - {self.user.username} - {self.order_status}"

class OrderItem(models.Model):
    order = models.ForeignKey(Orders, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    price = models.FloatField()  # Price at the time of purchase

    def __str__(self):
        return f"{self.quantity} x {self.product.name} (Order {self.order.id})"       