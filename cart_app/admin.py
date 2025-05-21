from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, RFIDCard, Product, Cart, CartItem, Order, OrderItem

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'phone_number')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2'),
        }),
    )

@admin.register(RFIDCard)
class RFIDCardAdmin(admin.ModelAdmin):
    list_display = ('card_id', 'is_active', 'created_at')
    search_fields = ('card_id',)
    list_filter = ('is_active',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'rfid_card', 'created_at')
    search_fields = ('name', 'rfid_card__card_id')
    list_filter = ('created_at',)


