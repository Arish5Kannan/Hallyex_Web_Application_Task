import os
import datetime
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.conf import settings

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field is required")
        email = self.normalize_email(email)
        extra_fields.setdefault('is_active', True)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')
        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = (
        ('customer', 'Customer'),
        ('admin', 'Admin'),
    )

    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    def __str__(self):
        return self.email


def getFilename(request,filename):
    now = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    new_filename = '%s%s'%(now,filename)
    return os.path.join('new_uploads/',new_filename)




class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    profile_photo = models.ImageField(upload_to=getFilename, blank=True, null=True)
    fullname = models.CharField(max_length=50, blank=True, null=True)
    contact = models.CharField(max_length=15, blank=True, null=True)
    address = models.CharField(max_length=250, blank=True, null=True)

    def __str__(self):
        return self.user.email

class Category(models.Model):
    name = models.CharField(max_length=150,null=False,blank=False)  
    image = models.ImageField(upload_to=getFilename,null=True,blank=True) 
    description = models.TextField(max_length=500,null=False,blank=False) 
    status = models.BooleanField(default=False,help_text='0-show,1-hidden')
    trending = models.BooleanField(default=False,help_text='0-normal,1-trending')
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
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.name    

class Cart(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)  
    product = models.ForeignKey(Product,on_delete=models.CASCADE)  
    product_qty = models.IntegerField(blank=False,null=False)   
    created_at = models.DateTimeField(auto_now_add=True) 

    @property
    def total(self):
        return self.product_qty*self.product.new_price  

class Favourite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)  
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
    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)  
    order_status = models.CharField(max_length=50,default="Pending",choices=STATUS_CHOICES)
    total_price = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True) 
    def __str__(self):
        return f"order {self.id} - {self.user.first_name}{self.user.last_name} - {self.order_status}"

class OrderItem(models.Model):
    order = models.ForeignKey(Orders, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    price = models.FloatField()  # Price at the time of purchase

    def __str__(self):
        return f"{self.quantity} x {self.product.name} (Order {self.order.id})"       