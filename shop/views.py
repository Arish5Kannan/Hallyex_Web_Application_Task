from django.shortcuts import render,redirect,get_object_or_404,reverse
from .models import *
from shop.forms import CustomUserForm
from django.contrib.auth import authenticate,login,logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
import json
from django.core.mail import send_mail
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

def home(request):
    prod = Product.objects.filter(trending=1)
    cate = Category.objects.all()
    prods = Product.objects.exclude(discount=0) 
      
    return render(request , "shop/index.html",{'prod':prod,'cate':cate,'prods':prods} )
def register(request):
    if request.method == "POST" and request.headers.get("X-Requested-With") == "XMLHttpRequest":
        form = CustomUserForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({"status": "success", "message": "Registration successful!"}, status=200)
        else:
            errors = {field: error.get_json_data()[0]['message'] for field, error in form.errors.items()}
            return JsonResponse({"status": "failure", "message": "Invalid values found", "errors": errors}, status=400)

    form = CustomUserForm()
    return render(request, "shop/register.html", {"form": form})
def logout_page(request):
    if request.user.is_authenticated:
        logout(request)   
        return redirect('/')
def login_page(request):   
    if  request.headers.get('x-requested-with')=='XMLHttpRequest':
            data = json.load(request)
            name = data["username"]
            pwd = data["password"]
            print(name,pwd)
            user = authenticate(request,username=name,password=pwd)
            if not User.objects.filter(username = name):
                return JsonResponse({'status':'You are not registered'},status=200)
            elif user is not None:
                
                login(request,user)
               
                return JsonResponse({'status':'Login success'},status=200)
            else:
                
                return JsonResponse({'status':'Invalid Username or Password'},status=200)

    return render(request,'shop/login.html')     
def collection(request):
    catagory = Category.objects.filter(status=0)
    category = Category.objects.filter(trending=1)
    prod = Product.objects.filter(trending=1)
    return render(request,"shop/collections.html",{"prods":prod,"catagory":catagory,"trending_category":category})
def products(request,name):
    if(Category.objects.filter(status=0,name=name)):
        prod = Product.objects.filter(category__name=name) 
        return render(request,"shop/products.html",{"prod":prod,"category_name":name})        
    else:
        
        return redirect('collections')
def product_details(request,cname,pname):
    if(Category.objects.filter(status=0,name=cname)):
        if(Product.objects.filter(status=0,name=pname)):
            product = Product.objects.filter(status=0,name=pname).first()    
            return render(request,"shop/product_details.html",{"prod":product})
        else :
            
            return redirect('collections')       
    else:
       
        return redirect('collections')
def add_to_cart(request):
    if request.headers.get('x-requested-with')=='XMLHttpRequest':
        if request.user.is_authenticated:
            data = json.load(request)
            product_id = data['pid']
            product_qty = data['product_qty']
            product_status = Product.objects.get(id=product_id)
            if product_status :
                if Cart.objects.filter(user=request.user.id,product_id=product_id):
                    return JsonResponse({'status':'Product is already in  cart'},status=200)
                else:
                    if product_status.quantity >= product_qty:
                        Cart.objects.create(user=request.user,product_id=product_id,product_qty=product_qty)
                        return JsonResponse({'status':'Product added to cart successfully..'},status=200) 
                    else :
                        return JsonResponse({'status':'Product out of stock..'},status=200)      
            return JsonResponse({'status':'Product added to cart successfully..'},status=200)
        else:
            return JsonResponse({'status':'Login to add Cart'},status=200)
    else :
        return JsonResponse({'status':'Invalid Access'},status=200) 

@login_required(login_url="/login/")
def cart(request):
    cartitems = Cart.objects.filter(user=request.user)
    return render(request,'shop/cart.html',{'carts':cartitems})  
def remove_cart(request):
   if request.user.is_authenticated: 
     data = json.load(request)
     print(data['cartid'])
     id = data['cartid']
     cartitem = Cart.objects.get(id=id)
     cartitem.delete()
     return JsonResponse({'status':'Product removed successfully'},status=200)
   else :
     return JsonResponse({'status':'Login to remove'},status=200)  
def orders(request):
    orders = Orders.objects.filter(user=request.user).prefetch_related("items__product")
    return render(request, "shop/orders.html", {"orders": orders})
def fav_page(request):
   if request.headers.get('x-requested-with')=='XMLHttpRequest':
    if request.user.is_authenticated:
      data=json.load(request)
      product_id=data['pid']
      product_status=Product.objects.get(id=product_id)
      if product_status:
         if Favourite.objects.filter(user=request.user.id,product_id=product_id):
          return JsonResponse({'status':'Product Already in Favourite'}, status=200)
         else:
          Favourite.objects.create(user=request.user,product_id=product_id)
          return JsonResponse({'status':'Product Added to Favourite successfully..'}, status=200)
    else:
      return JsonResponse({'status':'Login to Add Favourite'}, status=200)
   else:
    return JsonResponse({'status':'Invalid Access'}, status=200)

@login_required(login_url="/login/")
def profile(request):
    profile = Profile.objects.get(user = request.user)
    return render(request,"shop/profile.html",{'profile':profile})
def cancel_order(request, order_id):
    if request.method == "POST":
        order = get_object_or_404(Orders, id=order_id)

        # Update order status
        order.order_status = "Cancelled"
        order.delete()

        return JsonResponse({"success": 'Congratulations!', "message": "Order has been cancelled successfully."})
    
    return JsonResponse({"success": False, "message": "Invalid request."}, status=400)
def edit_profile(request, id):
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' and request.method == 'POST':
        try:
            data = json.loads(request.body)  
            Name = data.get('name')
            Email = data.get('mail')
            Contact = data.get('contact')
            Address = data.get('address')
            try:
                profile = Profile.objects.get(user=request.user)  
                profile.user.username = Name
                profile.user.email = Email
                profile.contact = Contact
                profile.address = Address
                profile.user.save()
                profile.save()
                return JsonResponse({'info': 'Congratulations!', 'status': 'Profile has been updated successfully'}, status=200)
            except Profile.DoesNotExist:
                return JsonResponse({'info': 'Profile not found', 'status': 'error'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'info': 'Invalid JSON data', 'status': 'error'}, status=400)
    else:
        return JsonResponse({'info': 'Oops! sorry', 'status': 'Invalid Access'}, status=400)
def reset_password(request,id):
    return render(request,"shop/reset_password.html",{'id':id})
def reset_password_id(request):
    if request.headers.get('x-requested-with')=='XMLHttpRequest' and request.method == 'POST':
      data=json.load(request)
      id=data['id']
      password = data['password']
      user = User.objects.get(id=id)
      user1 = User.objects.get(username=user)
      user1.set_password(password)
      user1.save()
      return JsonResponse({'info':'Congratulations!','status':'Password has been updated successfully'},status=200)
    else:
        return JsonResponse({'info':'Oops! sorry','status':'Invalid Access'}, status=400)

def forgot_password(request):
    return render(request,"shop/forgot_password.html")

@login_required(login_url="/login/")
def favview(request):
    favourite = Favourite.objects.filter(user=request.user)
    return render(request,'shop/favourite.html',{'fav':favourite})

def remove_fav(request):
   if request.user.is_authenticated:
    data = json.load(request)  
    id = data["fid"]  
    favourite = Favourite.objects.get(id=id)
    favourite.delete()
    return JsonResponse({'status':'Favourite product has been removed successfully'},status=200)

def place_order(request):
    if request.method == "POST":
        cart_items = Cart.objects.filter(user=request.user)

        if not cart_items:
            return redirect('cart')  # Redirect if cart is empty

        # Calculate total order price
        total_price = sum(item.product.new_price * item.product_qty for item in cart_items)

        # Create an Order
        order = Orders.objects.create(user=request.user, total_price=total_price)

        # Move Cart items to OrderItem
        for cart_item in cart_items:
            OrderItem.objects.create(
            order=order,
            product=cart_item.product,
            quantity=cart_item.product_qty,
            price=cart_item.product.new_price
        )

        # Clear Cart
        cart_items.delete()

        return JsonResponse({"status":"Your order has been placed successfully"},status=200)
    return JsonResponse({"status": "error", "message": "Invalid request!"},status=200)  
def delete_fav(request):
    if request.user.is_authenticated:
        favs = Favourite.objects.filter(user=request.user)  
        if favs.exists():  
            favs.delete()  
            return JsonResponse({'status': 'Favourites have been removed successfully'}, status=200)
        return JsonResponse({'status': 'No favourites found'}, status=404)
    return JsonResponse({'status': 'Unauthorized'}, status=401)

def delete_cart(request):
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user)  
        if cart.exists():  
            cart.delete()  
            return JsonResponse({'status': 'Cart have been removed successfully'}, status=200)
        return JsonResponse({'status': 'No Cart items  found'}, status=404)
    return JsonResponse({'status': 'Unauthorized'}, status=401)


def forgot_password_processing(request):
    if request.method == 'POST':
        data = json.load(request)
        email = data['email']
        users = User.objects.filter(email=email).values_list('id', flat=True)
        users = list(users)
        if users:
            id = users[0]
            user = User.objects.filter(email=email).first()
        else:
            return JsonResponse({'status':'Email has not been registered so far.'},status=200)
        link = f"""
        http://127.0.0.1:8000/reset_password/{id}/
        
        """
        subject = 'Password Reset Request'
        message = 'You have requested to reset your password. Please check your email for further instructions.'
        from_email = settings.EMAIL_HOST_USER
        recipient_list = [email]

        html_message = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Password Reset Request</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f4f7fc;
            }}
            .email-container {{
                width: 100%;
                max-width: 600px;
                margin: 0 auto;
                background-color: #ffffff;
                border-radius: 8px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                overflow: hidden;
            }}
            .header {{
                background-color: #0099cc;
                padding: 20px;
                text-align: center;
                color: white;
            }}
            .header h1 {{
                margin: 0;
                font-size: 24px;
            }}
            .content {{
                padding: 20px;
                color: #333;
            }}
            .content h2 {{
                color: #0099cc;
            }}
            .button {{
                display: inline-block;
                background-color: #0099cc;
                color: #fff;
                padding: 12px 20px;
                text-decoration: none;
                border-radius: 5px;
                font-weight: bold;
                margin-top: 20px;
            }}
            .footer {{
                background-color: #f1f1f1;
                text-align: center;
                padding: 10px;
                font-size: 14px;
                color: #888;
            }}
            .footer a {{
                color: #0099cc;
                text-decoration: none;
            }}
            @media only screen and (max-width: 600px) {{
                .email-container {{
                    width: 100% !important;
                    padding: 10px;
                }}
                .header h1 {{
                    font-size: 20px;
                }}
                .content h2 {{
                    font-size: 18px;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="email-container">
            <div class="header">
                <h1>Password Reset Request</h1>
            </div>
            <div class="content">
                <h2>Hello {user},</h2>
                <p>We received a request to reset your password. Click the button below to reset it:</p>
                <p><a href="{link}" class="button">Reset Your Password</a></p>
                <p>If you did not request a password reset, please ignore this email. Your password will remain unchanged.</p>
                <p>For security reasons, this link will expire in 24 hours.</p>
            </div>
            <div class="footer">
                <p>&copy; 2024 Your Company Name. All rights reserved.</p>
                <p>For support, <a href="mailto:support@example.com">contact us</a>.</p>
            </div>
        </div>
    </body>
    </html>
    
    """    
        try :
            send_mail(subject, message, from_email, recipient_list, html_message=html_message)
            return JsonResponse({'info':'Congratulations!','status':'Password reset link has been sent to you successfully'},status=200)    
        except Exception as e:
            print(e)
            return JsonResponse({'info':'Oops! sorry','status':'Something went wrong'},status=200)
    else :
        return JsonResponse({'status':'Invalid Access'},status=200)
    
def google_login_redirect(request):
    return redirect("/accounts/google/login/?process=login")
    