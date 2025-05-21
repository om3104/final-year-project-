from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

urlpatterns = [
    # Authentication URLs
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', LogoutView.as_view(next_page='home'), name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/change-password/', views.change_password_view, name='change_password'),
    path('profile/delete-account/', views.delete_account_view, name='delete_account'),
    
    # Product and Cart URLs
    path('', views.product_list_view, name='home'),
    path('products/', views.product_list_view, name='products'),
    path('cart/', views.cart_view, name='cart'),
    path('cart/update-quantity/', views.update_quantity, name='update_quantity'),
    path('cart/add/', views.add_to_cart, name='add_to_cart'),
    path('checkout/', views.checkout_view, name='checkout'),
    path('verify-payment/', views.verify_payment, name='verify_payment'),
    path('order-confirmation/<int:order_id>/', views.order_confirmation_view, name='order_confirmation'),
    
    # RFID Scanning API
    path('api/scan_product/', views.scan_product, name='scan_product'),
    path('api/product/<int:product_id>/', views.get_product_details, name='get_product_details'),
    path('api/cart/check/<int:product_id>/', views.check_cart_item, name='check_cart_item'),
    path('api/check_weight/', views.check_weight, name='check_weight'),
    path('api/get_cart_weight/', views.get_cart_weight, name='get_cart_weight'),
] 