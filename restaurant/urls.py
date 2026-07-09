from django.urls import path
from restaurant.views import (
    MenuListView, CartView, cart_sync, CartCheckoutView, OrderSuccessView,
    KitchenLoginView, KitchenLogoutView, KitchenDashboardView, 
    KitchenOrderDetailView, KitchenOrderStatusUpdateView,
    OrderTrackingView, OrderTrackingDetailView, OrderTrackingStatusView,
    ManagerLoginView, ManagerLogoutView, ManagerDashboardView,
    ManagerOrderListView, ManagerOrderDetailView, ManagerOrderCancelView,
    ManagerMenuItemListView, ManagerMenuItemCreateView, ManagerMenuItemUpdateView,
    ManagerMenuItemAvailabilityView, ManagerCategoryListView, ManagerCategoryCreateView,
    ManagerCategoryUpdateView, ManagerCSVExportView, ManagerAuditLogListView,
    OrderReceiptView, ManagerOrderReceiptView, StaffAccessView
)

app_name = "restaurant"

urlpatterns = [
    path("", MenuListView.as_view(), name="menu"),
    path("cart/", CartView.as_view(), name="cart"),
    path("cart/sync/", cart_sync, name="cart_sync"),
    path("checkout/", CartCheckoutView.as_view(), name="checkout"),
    path("orders/<uuid:tracking_token>/success/", OrderSuccessView.as_view(), name="order_success"),
    path("kitchen/login/", KitchenLoginView.as_view(), name="kitchen_login"),
    path("kitchen/logout/", KitchenLogoutView.as_view(), name="kitchen_logout"),
    path("kitchen/", KitchenDashboardView.as_view(), name="kitchen_dashboard"),
    path("kitchen/orders/<int:pk>/", KitchenOrderDetailView.as_view(), name="kitchen_order_detail"),
    path("kitchen/orders/<int:pk>/status/", KitchenOrderStatusUpdateView.as_view(), name="kitchen_order_status"),
    path("track/", OrderTrackingView.as_view(), name="order_tracking"),
    path("track/<uuid:tracking_token>/", OrderTrackingDetailView.as_view(), name="order_tracking_detail"),
    path("track/<uuid:tracking_token>/status/", OrderTrackingStatusView.as_view(), name="order_tracking_status"),
    
    # Digital Receipt Customer Route
    path("receipt/<uuid:tracking_token>/", OrderReceiptView.as_view(), name="order_receipt"),

    # Manager Routes
    path("manager/login/", ManagerLoginView.as_view(), name="manager_login"),
    path("manager/logout/", ManagerLogoutView.as_view(), name="manager_logout"),
    path("manager/", ManagerDashboardView.as_view(), name="manager_dashboard"),
    path("manager/orders/", ManagerOrderListView.as_view(), name="manager_order_list"),
    path("manager/orders/<int:pk>/", ManagerOrderDetailView.as_view(), name="manager_order_detail"),
    path("manager/orders/<int:pk>/cancel/", ManagerOrderCancelView.as_view(), name="manager_order_cancel"),
    path("manager/orders/<int:pk>/receipt/", ManagerOrderReceiptView.as_view(), name="manager_order_receipt"),
    path("manager/analytics/export/", ManagerCSVExportView.as_view(), name="manager_csv_export"),
    path("manager/audit-logs/", ManagerAuditLogListView.as_view(), name="manager_audit_logs"),
    path("manager/menu/", ManagerMenuItemListView.as_view(), name="manager_menu_list"),
    path("manager/menu/add/", ManagerMenuItemCreateView.as_view(), name="manager_menu_create"),
    path("manager/menu/<int:pk>/edit/", ManagerMenuItemUpdateView.as_view(), name="manager_menu_edit"),
    path("manager/menu/<int:pk>/availability/", ManagerMenuItemAvailabilityView.as_view(), name="manager_menu_availability"),
    path("manager/categories/", ManagerCategoryListView.as_view(), name="manager_category_list"),
    path("manager/categories/add/", ManagerCategoryCreateView.as_view(), name="manager_category_create"),
    path("manager/categories/<int:pk>/edit/", ManagerCategoryUpdateView.as_view(), name="manager_category_edit"),
    path("staff-access/", StaffAccessView.as_view(), name="staff_access"),
]
