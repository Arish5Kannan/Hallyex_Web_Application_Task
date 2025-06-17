from django.urls import path
from . import views
urlpatterns = [
    path('',views.home,name="home"),
    path('google-login-direct/',views.google_login_redirect,name="google-login-direct"),
    path('register/',views.register,name="register"),
    path('collection/',views.collection,name="collections"),
    path('collections/<str:name>/',views.products,name="collections"),
    path('collections/<str:cname>/<str:pname>/',views.product_details,name="product_details"),
    path('login/',views.login_page,name='login'),
    path('logout/',views.logout_page,name='logout'),
    path('add_to_cart',views.add_to_cart,name='add_to_cart'),
    path('remove_cart/',views.remove_cart,name='remove_cart'),
    path('cart',views.cart,name='cart'),
    path('fav',views.fav_page,name="fav"),
    path('favview',views.favview,name='favview'),
    path('remove_fav/',views.remove_fav,name='remove_fav'),
    path("place_order/",views.place_order, name="place_order"),
    path("orders/", views.orders, name="orders"),
    path("reset_password/<int:id>/",views.reset_password,name="reset_password"),
    path("reset_password_id/",views.reset_password_id,name="reset_password_id"),
    path("forgot_password/",views.forgot_password, name="forgot_password"),
    path("profile/",views.profile,name="profile"),
    path("delete_cart/",views.delete_cart, name="delete_cart"),
    path("delete_favourite/",views.delete_fav,name="delete_favourite"),
    path('cancel-order/<int:order_id>/', views.cancel_order, name='cancel_order'),
    path("edit_profile/<int:id>/",views.edit_profile,name="edit_profile"),
    path("forgot_password_processing/",views.forgot_password_processing,name="forgot_password_processing")
]