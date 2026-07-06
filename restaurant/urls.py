from django.urls import path
from restaurant.views import (
    MenuListView, CartView, cart_sync, CartCheckoutView, OrderSuccessView,
    KitchenLoginView, KitchenLogoutView, KitchenDashboardView, 
    KitchenOrderDetailView, KitchenOrderStatusUpdateView,
    OrderTrackingView, OrderTrackingDetailView, OrderTrackingStatusView
)

app_name = "restaurant"

urlpatterns = [
    path("", MenuListView.as_view(), name="menu"),
    path("cart/", CartView.as_view(), name="cart"),
    path("cart/sync/", cart_sync, name="cart_sync"),
    path("checkout/", CartCheckoutView.as_view(), name="checkout"),
    path("orders/<int:order_id>/success/", OrderSuccessView.as_view(), name="order_success"),
    path("kitchen/login/", KitchenLoginView.as_view(), name="kitchen_login"),
    path("kitchen/logout/", KitchenLogoutView.as_view(), name="kitchen_logout"),
    path("kitchen/", KitchenDashboardView.as_view(), name="kitchen_dashboard"),
    path("kitchen/orders/<int:pk>/", KitchenOrderDetailView.as_view(), name="kitchen_order_detail"),
    path("kitchen/orders/<int:pk>/status/", KitchenOrderStatusUpdateView.as_view(), name="kitchen_order_status"),
    path("track/", OrderTrackingView.as_view(), name="order_tracking"),
    path("track/<int:order_id>/", OrderTrackingDetailView.as_view(), name="order_tracking_detail"),
    path("track/<int:order_id>/status/", OrderTrackingStatusView.as_view(), name="order_tracking_status"),
]
