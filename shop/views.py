from django.shortcuts import render,redirect,get_object_or_404
from .models import *
import csv
import io
import pandas as pd
from django.db.models import Count, Sum, F, Value
from django.db.models.functions import Coalesce
from shop.forms import *
from django.contrib.auth import authenticate,login,logout
from django.contrib.auth.decorators import login_required
from django.http import *
from django.contrib.auth import update_session_auth_hash
import json
from django.core.files.storage import FileSystemStorage
from shop.decorators import admin_required
from django.core.mail import send_mail
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
import razorpay
from django.views.decorators.csrf import *
import os
from django.contrib import messages
from razorpay.errors import BadRequestError, ServerError
from django.core.paginator import Paginator

#Authorize razorpay with API Keys
razorpay_client = razorpay.Client(auth=(
    settings.RAZOR_KEY_ID,settings.RAZOR_KEY_SECRET
))



def convert_to_subunit(amount, factor=100):
    subunit = int(round(amount * factor))
    return subunit


def cart(request):
    if request.user.is_authenticated:
        cartitems = Cart.objects.filter(user=request.user)
        favourites = Favourite.objects.filter(user=request.user)
        orders = Orders.objects.filter(user=request.user)
        total_price = sum(item.product.new_price * item.product_qty for item in cartitems)

        context = {
            'carts': cartitems,
            'cart_count': cartitems.count(),
            'Whishlist_count': favourites.count(),
            'Orders_count': orders.count()
        }

        if total_price > 0 and cartitems.exists():
            currency = 'INR'
            amount = convert_to_subunit(total_price)

            try:
                razorpay_order = razorpay_client.order.create(
                    dict(
                        amount=amount,
                        currency=currency,
                        payment_capture='0'
                    )
                )
                razorpay_order_id = razorpay_order['id']
                callback_url = '/paymenthandler/'

                context.update({
                    'razorpay_order_id': razorpay_order_id,
                    'razorpay_amount': amount,
                    'razorpay_merchant_key': settings.RAZOR_KEY_ID,
                    'currency': currency,
                    'callback_url': callback_url
                })

            except (BadRequestError, ServerError) as e:

                messages.error(request, "There was an issue initiating the payment. Please try again later.")
                print(f"Razorpay error: {e}")
            except (razorpay.errors.GatewayError, razorpay.errors.SignatureVerificationError) as e:

                messages.error(request, "Payment service is currently unavailable. Please try again later.")
                print(f"Razorpay generic error: {e}")
            except Exception as e:

                messages.error(request, "Something went wrong. Please try again later.")
                print(f"Unhandled error: {e}")

        return render(request, 'shop/cart.html', context)
    return render(request,"shop/cart.html")

@csrf_exempt
def paymenthandler(request):
    if request.method == "POST":
        try:
            cart_items = Cart.objects.filter(user=request.user)
            total_price = sum(item.product.new_price * item.product_qty for item in cart_items)

            payment_id = request.POST.get('razorpay_payment_id', '')
            razorpay_order_id = request.POST.get('razorpay_order_id', '')
            signature = request.POST.get('razorpay_signature', '')
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            }

            result = razorpay_client.utility.verify_payment_signature(params_dict)
            if result is not None:
                amount = convert_to_subunit(total_price)
                try:
                    razorpay_client.payment.capture(payment_id, amount)

                    # Get shipping address from session
                    shipping = request.session.get('shipping_address', {})
                    
                    order = Orders.objects.create(
                        user=request.user,
                        total_price=total_price,
                        address_line1=shipping.get('address_line1', ''),
                        address_line2=shipping.get('address_line2', ''),
                        city=shipping.get('city', ''),
                        state=shipping.get('state', ''),
                        zipcode=shipping.get('zipcode', ''),
                        country=shipping.get('country', ''),
                        phone=shipping.get('phone', '')
                    )

                    for cart_item in cart_items:
                        OrderItem.objects.create(
                            order=order,
                            product=cart_item.product,
                            quantity=cart_item.product_qty,
                            price=cart_item.product.new_price
                        )

                    cart_items.delete()
                    return render(request, 'shop/paymentsuccess.html')

                except Exception as e:
                    print("Error:", e)
                    return render(request, 'shop/paymentfail.html')
            else:
                return render(request, 'shop/paymentfail.html')
        except Exception as e:
            print("Exception:", e)
            return HttpResponseBadRequest()
    return HttpResponseBadRequest()
    

@csrf_exempt
def store_address_session(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            request.session['shipping_address'] = data
            return JsonResponse({'success': True})
        except:
            return JsonResponse({'success': False}, status=400)
    return JsonResponse({'error': 'Invalid method'}, status=405)


@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=CustomUser)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

def home(request):
    if request.user.is_authenticated and request.user.role=='admin':
        return redirect('admin_dashboard')
    prod = Product.objects.filter(trending=1)
    cate = Category.objects.all()
    prods = Product.objects.exclude(discount=0) 
    context = {
        
        'prod':prod,
        'cate':cate,
        'prods':prods}
    if request.user.is_authenticated :
            cartitems = Cart.objects.filter(user=request.user)
            favourites = Favourite.objects.filter(user=request.user)
            orders = Orders.objects.filter(user=request.user)
            context.update({
                'cart_count':cartitems.count(),
        'Whishlist_count':favourites.count(),
        'Orders_count':orders.count(),
        
            })
      
    return render(request , "shop/index.html", context)

def register(request):
    if request.method == "POST" and request.headers.get("x-requested-with") == "XMLHttpRequest":
        form = CustomUserForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password"])
            user.save()
            return JsonResponse({"status": "success", "message": "Registered successfully"}, status=200)
        else:
            errors = {field: error.get_json_data()[0]['message'] for field, error in form.errors.items()}
            return JsonResponse({"status": "failure", "errors": errors}, status=400)
    else:
        form = CustomUserForm()
    return render(request, "shop/register.html", {"form": form})


def logout_page(request):
    if request.user.is_authenticated:
        logout(request)   
        return redirect('/')

def login_page(request):   
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        data = json.load(request)
        email = data["email"]
        pwd = data["password"]
        user = authenticate(request, email=email, password=pwd)

        if not CustomUser.objects.filter(email=email).exists():
            return JsonResponse({'status': 'You are not registered'}, status=200)
        elif not CustomUser.objects.filter(is_active=True,email=email).exists():
            return JsonResponse({'status':'You have been blocked,Contact us for more details'})
        elif user is not None:
            login(request, user)
            
            if user.role == 'admin':
                return JsonResponse({'status': 'Login success', 'redirect_url': '/adminDashboard/'}, status=200)
            else:
                return JsonResponse({'status': 'Login success', 'redirect_url': '/'}, status=200)
        else:
            return JsonResponse({'status': 'Invalid Email or Password'}, status=200)

    return render(request, 'shop/login.html')  


def collection(request):
    catagory = Category.objects.filter(status=0)
    category = Category.objects.filter(trending=1)
    prod = Product.objects.filter(trending=1)
    context = {"prods":prod,"catagory":catagory,"trending_category":category}
    if request.user.is_authenticated :
            cartitems = Cart.objects.filter(user=request.user)
            favourites = Favourite.objects.filter(user=request.user)
            orders = Orders.objects.filter(user=request.user)
            context.update({
                'cart_count':cartitems.count(),
        'Whishlist_count':favourites.count(),
        'Orders_count':orders.count(),
            })
    return render(request,"shop/collections.html",context)

def products(request, name):
    if not Category.objects.filter(status=0, name=name).exists():
        return JsonResponse({'error': 'Category not found'}, status=404)

    products = Product.objects.filter(category__name=name)

    # Search
    search_query = request.GET.get('search')
    if search_query:
        products = products.filter(name__icontains=search_query)

    # Sort
    sort_by = request.GET.get('sort')
    if sort_by in ['new_price', '-new_price', 'name', '-name', 'old_price', '-old_price']:
        products = products.order_by(sort_by)

    # Pagination
    paginator = Paginator(products, 20)  # 8 products per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        # AJAX response
        data = []
        for product in page_obj:
            data.append({
                'id': product.id,
                'name': product.name,
                'old_price': product.old_price,
                'new_price': product.new_price,
                'discount': product.discount,
                'image_url': product.product_image.url if product.product_image else '/static/images/tick.jpeg',
                'details_url': f"/collections/{product.category.name}/{product.name}/"
            })
        return JsonResponse({
            'products': data,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'num_pages': paginator.num_pages,
            'current_page': page_obj.number
        })

    return render(request, "shop/products.html", {
        'category_name': name,
        'prod': page_obj,
    })
def product_details(request,cname,pname):
    context = {}
    if request.user.is_authenticated:
            cartitems = Cart.objects.filter(user=request.user)
            favourites = Favourite.objects.filter(user=request.user)
            orders = Orders.objects.filter(user=request.user)
            context.update({
                'cart_count':cartitems.count(),
        'Whishlist_count':favourites.count(),
        'Orders_count':orders.count(),
            })
        
    if(Category.objects.filter(status=0,name=cname)):
        if(Product.objects.filter(status=0,name=pname)):
            product = Product.objects.filter(status=0,name=pname).first()   
            context.update({"prod":product})
            return render(request,"shop/product_details.html",context)
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
                    return JsonResponse({'status':'Product has added already into the cart..'},status=200)
                else:
                    if product_status.quantity >= product_qty:
                        Cart.objects.create(user=request.user,product_id=product_id,product_qty=product_qty)
                        return JsonResponse({'status':'Product has been added to cart successfully..'},status=200) 
                    else :
                        return JsonResponse({'status':'Currently product is in out of stock..'},status=200)      
            return JsonResponse({'status':'Product has been added to cart successfully..'},status=200)
        else:
            return JsonResponse({'status':'Login to add Cart'},status=200)
    else :
        return JsonResponse({'status':'Invalid Access'},status=200) 

 
def remove_cart(request):
   if request.user.is_authenticated: 
     data = json.load(request)
     print(data['cartid'])
     id = data['cartid']
     cartitem = Cart.objects.get(id=id)
     cartitem.delete()
     return JsonResponse({'status':'Product has been removed successfully'},status=200)
   else :
     return JsonResponse({'status':'Login to remove'},status=200)  

def orders(request):
    context = {}
    cartitems = Cart.objects.filter(user=request.user)
    favourites = Favourite.objects.filter(user=request.user)
    orders = Orders.objects.filter(user=request.user)
    orders1 = Orders.objects.filter(user=request.user).prefetch_related("items__product")
    context.update({
                'cart_count':cartitems.count(),
        'Whishlist_count':favourites.count(),
        'Orders_count':orders.count(),
        'orders':orders1
            })
    
    return render(request, "shop/orders.html", context)

def fav_page(request):
   if request.headers.get('x-requested-with')=='XMLHttpRequest':
    if request.user.is_authenticated:
      data=json.load(request)
      product_id=data['pid']
      product_status=Product.objects.get(id=product_id)
      if product_status:
         if Favourite.objects.filter(user=request.user.id,product_id=product_id):
          return JsonResponse({'status':'Product has added Already in whishlist..'}, status=200)
         else:
          Favourite.objects.create(user=request.user,product_id=product_id)
          return JsonResponse({'status':'Product has been added to whishlist successfully..'}, status=200)
    else:
      return JsonResponse({'status':'Login to Add Favourite'}, status=200)
   else:
    return JsonResponse({'status':'Invalid Access'}, status=200)

@login_required(login_url="/login/")
def profile(request):
    profile = Profile.objects.get(user = request.user)
    favourites = Favourite.objects.filter(user=request.user)
    cartitems = Cart.objects.filter(user=request.user)
    orders = Orders.objects.filter(user=request.user)
    return render(request,"shop/profile.html",{
        'profile':profile,
        'cart_count':cartitems.count(),
        'Whishlist_count':favourites.count(),
        'Orders_count':orders.count()
        
        })

def cancel_order(request, order_id):
    if request.method == "POST":
        order = get_object_or_404(Orders, id=order_id)

        # Update order status
        order.order_status = "Cancelled"
        
        order.save()
        return JsonResponse({"success": 'Congratulations!', "message": "Order has been cancelled successfully."})
    
    return JsonResponse({"success": False, "message": "Invalid request."}, status=400)

def edit_profile(request, id):
    if request.method == 'POST':
        try:
             
            Name = request.POST.get('name')
            Email = request.POST.get('mail')
            Contact = request.POST.get('contact')
            Address = request.POST.get('address')
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            
            image = request.FILES.get('profileImage')
            try:
                profile = Profile.objects.get(user=request.user)  
                profile.fullname = Name
                if image is not None:
                    profile.profile_photo = image
                profile.user.email = Email
                profile.user.first_name= first_name
                profile.user.last_name = last_name
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





@login_required(login_url="/login/")
def reset_password_profile(request):
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        try:
            data = json.loads(request.body)
            current_password = data.get('current_password')
            new_password = data.get('password')

            user = request.user

            if user.check_password(current_password):
                user.set_password(new_password)
                user.save()

                update_session_auth_hash(request, user)

                return JsonResponse({
                    'info': 'Congratulations!',
                    'status': 'Password has been updated successfully'
                }, status=200)
            else:
                return JsonResponse({
                    'info': 'Oops! sorry',
                    'status': 'Current password is incorrect'
                }, status=400)

        except Exception as e:
            return JsonResponse({
                'info': 'Error occurred',
                'status': str(e)
            }, status=500)

    return render(request,"shop/reset_password1.html")

def reset_password(request,id):
    return render(request,"shop/reset_password.html",{'id':id})
def reset_password_id(request):
    if request.headers.get('x-requested-with')=='XMLHttpRequest' and request.method == 'POST':
      data=json.load(request)
      id=data['id']
      password = data['password']
      user = CustomUser.objects.get(id=id)
      user1 = CustomUser.objects.get(email=user)
      user1.set_password(password)
      user1.save()
      return JsonResponse({'info':'Congratulations!','status':'Password has been updated successfully'},status=200)
    else:
      return JsonResponse({'info':'Oops! sorry','status':'Invalid Access'}, status=400)

def forgot_password(request):
    return render(request,"shop/forgot_password.html")


def favview(request):
    if request.user.is_authenticated:
        favourite = Favourite.objects.filter(user=request.user)
        favourites = Favourite.objects.filter(user=request.user)
        cartitems = Cart.objects.filter(user=request.user)
        orders = Orders.objects.filter(user=request.user)
        return render(request,'shop/favourite.html',{'fav':favourite,'cart_count':cartitems.count(),
        'Whishlist_count':favourites.count(),
        'Orders_count':orders.count()})
    return render(request,"shop/favourite.html")

def remove_fav(request):
   if request.user.is_authenticated:
    data = json.load(request)  
    id = data["fid"]  
    favourite = Favourite.objects.get(id=id)
    favourite.delete()
    return JsonResponse({'status':'Whishlist product has been removed successfully..'},status=200)

def delete_fav(request):
    if request.user.is_authenticated:
        favs = Favourite.objects.filter(user=request.user)  
        if favs.exists():  
            favs.delete()  
            return JsonResponse({'status': 'Whishlist has been cleared successfully..'}, status=200)
        return JsonResponse({'status': 'No favourites found'}, status=404)
    return JsonResponse({'status': 'Unauthorized'}, status=401)

def delete_cart(request):
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user)  
        if cart.exists():  
            cart.delete()  
            return JsonResponse({'status': 'Cart has been cleared successfully..'}, status=200)
        return JsonResponse({'status': 'No Cart items  found'}, status=404)
    return JsonResponse({'status': 'Unauthorized'}, status=401)


def forgot_password_processing(request):
    if request.method == 'POST':
        data = json.load(request)
        email = data['email']
        users = CustomUser.objects.filter(email=email).values_list('id', flat=True)
        users = list(users)
        if users:
            id = users[0]
            user = CustomUser.objects.filter(email=email).first()
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
            return JsonResponse({'info':'Oops! sorry','status':f'{e}'},status=200)
    else :
        return JsonResponse({'status':'Invalid Access'},status=200)
    
def google_login_redirect(request):
    return redirect("/accounts/google/login/?process=login")


@login_required(login_url="/login/")
@admin_required
def admin_dashboard(request):
    total_products = Product.objects.count()
    total_categorys = Category.objects.count()
    total_customers = CustomUser.objects.filter(role='customer').count()
    pending_orders = Orders.objects.filter(order_status='pending').count()
    processing_orders = Orders.objects.filter(order_status='processing').count()
    shipped_orders = Orders.objects.filter(order_status='shipped').count()

    context = {
        'total_products': total_products,
        'total_customers': total_customers,
        'pending_orders': pending_orders,
        'processing_orders': processing_orders,
        'shipped_orders': shipped_orders,
        'total_categorys':total_categorys
    }
    return render(request, 'shop/admin/dashboard.html', context)


@admin_required
@login_required(login_url='/login/')
def admin_manage_products(request):
    products = Product.objects.all()
    categories = Category.objects.all()
    return render(request, "shop/admin/manageProducts.html", {
        "products": products,
        "categories": categories
    })

@admin_required
@login_required(login_url='/login/')
def add_product(request):
    if request.method == 'POST':
        name = request.POST['name']
        vendor = request.POST['vendor']
        quantity = request.POST['quantity']
        old_price = request.POST['old_price']
        new_price = request.POST['new_price']
        discount = request.POST['discount']
        status = request.POST.get('status') == 'True'
        trending = request.POST.get('trending') == 'True'
        description = request.POST['description']
        category = Category.objects.get(id=request.POST['category'])
        product_image = request.FILES.get('product_image')

        Product.objects.create(
            name=name,
            vendor=vendor,
            quantity=quantity,
            old_price=old_price,
            new_price=new_price,
            discount=discount,
            status=status,
            trending=trending,
            description=description,
            category=category,
            product_image=product_image
        )
        return redirect('admin_products')
@admin_required
@login_required(login_url='/login/')
def edit_product(request, id):
    product = get_object_or_404(Product, id=id)
    if request.method == 'POST':
        product.name = request.POST['name']
        product.vendor = request.POST['vendor']
        product.quantity = request.POST['quantity']
        product.old_price = request.POST['old_price']
        product.new_price = request.POST['new_price']
        product.discount = request.POST['discount']
        product.status = request.POST.get('status') == 'True'
        product.trending = request.POST.get('trending') == 'True'
        product.description = request.POST['description']
        product.save()
        return redirect('admin_products')

@admin_required
@login_required(login_url='/login/')
def delete_product(request, id):
    product = get_object_or_404(Product, id=id)
    if request.method == 'POST':
        product.delete()
        return redirect('admin_products')



@admin_required
@login_required(login_url='/login/')
def admin_manage_customers(request):
    customers = CustomUser.objects.filter(role='customer')
    return render(request, "shop/admin/manageCustomers.html", {'customers': customers})


@admin_required
def delete_customer(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    if request.method == "POST":      
        messages.success(request,f"User {user.first_name}{user.last_name} deleted successfully")
        user.delete()
        return redirect('/adminDashboard/')
    return HttpResponseForbidden()


@admin_required
def reset_customer_password(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    temp_password = CustomUser.objects.make_random_password()
    user.set_password(temp_password)
    user.save()

    send_mail(
        'Temporary Password',
        f'Hello {user.first_name}, your temporary password is: {temp_password}',
        settings.EMAIL_HOST_USER,
        [user.email]
    )

    messages.success(request, f'Temporary password sent to {user.email}')
    return redirect('admin_customers')

@admin_required
def toggle_customer_status(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id, role='customer')
    user.is_active = not user.is_active
    user.save()
    block = 'Unblocked' if user.is_active else "Blocked"
    messages.success(request, f'{user.first_name}{user.last_name} has been {block}')
    return redirect('admin_customers')

@admin_required
def admin_add_or_update_user(request):
    user_id = request.POST.get("user_id")
    email = request.POST.get("email")
    first_name = request.POST.get("first_name")
    last_name = request.POST.get("last_name")
    password = request.POST.get("password")

    if user_id:
        user = get_object_or_404(CustomUser, id=user_id)
        user.email = email
        user.first_name = first_name
        user.last_name = last_name
        if password:
            user.set_password(password)
        user.save()
        messages.success(request, f"Customer {user.first_name}{user.last_name} updated.")
    else:
        CustomUser.objects.create_user(
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=password,
            role="customer"
        )
        messages.success(request, "New Customer added.")

    return redirect("admin_customers")

@admin_required
@login_required(login_url='/login/')
def admin_manage_settings(request):
    settings_instance = BrandingSettings.objects.first() or BrandingSettings()

    if request.method == 'POST':
        form = BrandingSettingsForm(request.POST, request.FILES, instance=settings_instance)
        if form.is_valid():
            form.save()
            messages.success(request, "Branding settings updated successfully.")
            return redirect('admin_settings')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = BrandingSettingsForm(instance=settings_instance)

    font_choices = ["Roboto", "Arial", "Georgia", "Helvetica", "Times New Roman", "Courier New"]
    
    return render(request, "shop/admin/settings.html", {
        "form": form,
        "settings": settings_instance,
        "font_choices": font_choices
    })

@admin_required
def impersonate_customer(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id, role='customer')
    request.session['impersonate_id'] = user.id
    return redirect('/')

def stop_impersonation(request):
    if 'impersonate_id' in request.session:
        del request.session['impersonate_id']
        messages.info(request, "Impersonation ended.")
    return redirect('/adminDashboard/')

@admin_required
def customer_profile(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    profile = getattr(user, 'profile', None)
    return render(request, 'shop/partials/customer_profile.html', {'user': user, 'profile': profile})

@admin_required
def customer_orders(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    orders = Orders.objects.filter(user=user).prefetch_related('items', 'items__product')
    return render(request, 'shop/partials/customer_orders.html', {'user': user, 'orders': orders})

@admin_required
def admin_update_profile(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    profile, _ = Profile.objects.get_or_create(user=user)
    if request.method == 'POST':

        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.save()

        profile.fullname = request.POST.get('fullname', '')
        profile.contact = request.POST.get('contact', '')
        profile.address = request.POST.get('address', '')

        # Handle file upload
        if 'profile_photo' in request.FILES:
            profile.profile_photo = request.FILES['profile_photo']

        profile.save()
        messages.success(request, "Profile updated successfully.")
        return redirect('admin_customers') 

    return redirect('admin_customers')

@admin_required
def manage_orders(request):
    orders = Orders.objects.select_related('user').all()

    # Filters
    from_date = request.GET.get('from')
    to_date = request.GET.get('to')
    customer_email = request.GET.get('customer')
    status = request.GET.get('status')

    if from_date:
        orders = orders.filter(created_at__date__gte=from_date)
    if to_date:
        orders = orders.filter(created_at__date__lte=to_date)
    if customer_email:
        orders = orders.filter(user__email__icontains=customer_email)
    if status:
        orders = orders.filter(order_status__iexact=status)

    return render(request, "shop/admin/manageOrders.html", {'orders': orders})

@admin_required
def get_order_status(request, order_id):
    order = get_object_or_404(Orders, id=order_id)
    return JsonResponse({'status': order.order_status})


@csrf_exempt
@admin_required
def update_order_status(request, order_id):
    if request.method == 'POST' :
        order = get_object_or_404(Orders, id=order_id)
        data = json.loads(request.body)
        new_status = data.get('status')

        if new_status:
            order.order_status = new_status
            order.save()
            return JsonResponse({'message': 'Order status updated.'}, status=200)
        return JsonResponse({'message': 'Invalid status.'}, status=400)
    return JsonResponse({'message': 'Invalid request.'}, status=400)

@admin_required
def order_details(request, order_id):
    order = get_object_or_404(Orders, id=order_id)
    items = OrderItem.objects.filter(order=order).select_related('product')

    return render(request, "shop/partials/order_details_partial.html", {
        'order': order,
        'items': items
    })

@csrf_protect
@admin_required
def delete_order(request, order_id):
    if request.method == 'POST':
        order = get_object_or_404(Orders, id=order_id)
        order.delete()
        messages.success(request,'Order has been deleted.')
        return redirect('admin_manage_orders')
    



@admin_required
@login_required
def grouped_order_report(request):
    group_by = request.GET.get('group_by')
    export_format = request.GET.get('export')  # 'csv' or 'excel'
    report = []

    if group_by == "customer":
        report = Orders.objects.values(
            'user__email',
            'user__profile__fullname',
            'user__profile__contact'
        ).annotate(
            total_orders=Count('id'),
            total_amount=Sum('total_price'),
            total_quantity=Sum('items__quantity')
        )
        headers = ['Full Name', 'Email', 'Contact', 'Total Orders', 'Total Quantity', 'Total Amount (₹)']
        rows = [
            [
                r['user__profile__fullname'],
                r['user__email'],
                r['user__profile__contact'],
                r['total_orders'],
                r['total_quantity'],
                r['total_amount'],
            ]
            for r in report
        ]

    elif group_by == "product":
        report = OrderItem.objects.values(
            'product__name',
            'product__vendor'
        ).annotate(
            total_quantity=Sum('quantity'),
            total_amount=Sum('price'),
            total_orders=Count('order', distinct=True)
        )
        headers = ['Product Name', 'Vendor', 'Total Orders', 'Total Quantity', 'Total Amount (₹)']
        rows = [
            [
                r['product__name'],
                r['product__vendor'],
                r['total_orders'],
                r['total_quantity'],
                r['total_amount'],
            ]
            for r in report
        ]

    # Export logic
    if export_format == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename=report_{group_by}.csv'

        writer = csv.writer(response)
        writer.writerow(headers)
        writer.writerows(rows)
        return response

    elif export_format == 'excel':
        df = pd.DataFrame(rows, columns=headers)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Report')
        buffer.seek(0)

        response = HttpResponse(buffer.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename=report_{group_by}.xlsx'
        return response

    return render(request, "shop/grouped_report.html", {'report': report, 'group_by': group_by})


@csrf_exempt
@admin_required
def edit_order_items(request, order_id):
    order = get_object_or_404(Orders, id=order_id)
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            items = data.get('items', [])

            for item_data in items:
                item_id = item_data['id']
                quantity = int(item_data['quantity'])

                order_item = OrderItem.objects.select_related('product').get(id=item_id, order=order)
                product = order_item.product

                if quantity < 1 or quantity > product.quantity:
                    return JsonResponse({'error': f"Invalid quantity for {product.name}"}, status=400)

                order_item.quantity = quantity
                order_item.price = quantity * product.new_price
                order_item.save()

            # Optionally update total order price
            total_price = sum(i.price for i in order.items.all())
            order.total_price = total_price
            order.save()

            return JsonResponse({'message': 'Order items updated successfully'})

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'Invalid request'}, status=400)

def get_shipping_details(request, order_id):
    try:
        order = Orders.objects.get(id=order_id)
        shipping_details = {
            'address_line1': order.address_line1,
            'address_line2': order.address_line2,
            'city': order.city,
            'state': order.state,
            'zipcode': order.zipcode,
            'country': order.country,
            'phone': order.phone,
        }
        return JsonResponse(shipping_details)
    except Orders.DoesNotExist:
        return JsonResponse({'error': 'Order not found'}, status=404)


@csrf_exempt
@admin_required
def edit_shipping_address(request, order_id):
    order = get_object_or_404(Orders, id=order_id)
    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            order.address_line1 = data.get('address_line1', '')
            order.address_line2 = data.get('address_line2', '')
            order.city = data.get('city', '')
            order.state = data.get('state', '')
            order.zipcode = data.get('zipcode', '')
            order.country = data.get('country', '')
            order.phone = data.get('phone', '')
            order.save()

            return JsonResponse({'message': 'Shipping address updated successfully'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'Invalid request'}, status=400)


def get_order_items_json(request, order_id):
    items = OrderItem.objects.filter(order_id=order_id).select_related('product')
    data = []

    for item in items:
        data.append({
            'id': item.id,
            'name': item.product.name,
            'image':item.product.product_image.url,
            'qty': item.quantity,
            'max': item.product.quantity,
        })

    return JsonResponse({'items': data})