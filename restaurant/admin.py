from django.contrib import admin
from restaurant.models import Category, MenuItem, Order, OrderItem


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "icon")
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "category", "price", "is_vegetarian", "is_spicy", "is_available")
    list_filter = ("category", "is_vegetarian", "is_spicy", "is_available")
    search_fields = ("name", "description")
    ordering = ("category", "name")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer_name", "customer_phone", "table_number", "total_amount", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("id", "customer_name", "customer_phone")
    ordering = ("-created_at",)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "menu_item", "quantity", "price_at_order")
    list_filter = ("menu_item__category",)
    search_fields = ("menu_item__name", "order__customer_name")
