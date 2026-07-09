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
    list_display = ("id", "customer_name", "customer_phone", "table_number", "tracking_token", "subtotal_amount", "tax_amount", "total_amount", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("id", "customer_name", "customer_phone", "tracking_token")
    ordering = ("-created_at",)
    readonly_fields = ("tracking_token", "subtotal_amount", "tax_amount", "tax_rate", "total_amount", "created_at")


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "menu_item", "item_name_at_order", "category_name_at_order", "quantity", "price_at_order")
    list_filter = ("menu_item__category", "category_name_at_order")
    search_fields = ("menu_item__name", "item_name_at_order", "category_name_at_order", "order__customer_name")
    readonly_fields = ("item_name_at_order", "category_name_at_order", "price_at_order")


from restaurant.models import AuditLog

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("id", "timestamp", "actor", "action", "target_type", "target_id", "description")
    list_filter = ("action", "target_type", "timestamp")
    search_fields = ("description", "actor__username", "target_id")
    ordering = ("-timestamp",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
