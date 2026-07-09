import csv
from datetime import timedelta
from decimal import Decimal
from django.contrib.auth.models import User, Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from restaurant.models import Order, OrderItem, Category, MenuItem, AuditLog

class PhaseCTests(TestCase):
    def setUp(self):
        # Create users & groups
        self.manager_group, _ = Group.objects.get_or_create(name="Managers")
        self.manager_user = User.objects.create_user(username="manager", password="password123")
        self.manager_user.groups.add(self.manager_group)
        
        self.regular_user = User.objects.create_user(username="customer", password="password123")
        
        # Create category & items
        self.category = Category.objects.create(name="Appetizers", icon="bi-star")
        self.menu_item = MenuItem.objects.create(
            category=self.category,
            name="Garlic Bread",
            description="Tasty bread",
            price=Decimal("120.00"),
            is_available=True
        )
        
        # Create COMPLETED order
        self.order_completed = Order.objects.create(
            customer_name="Completed Cust",
            customer_phone="+919876543210",
            subtotal_amount=Decimal("120.00"),
            tax_amount=Decimal("6.00"),
            total_amount=Decimal("126.00"),
            status="COMPLETED",
            completed_at=timezone.now()
        )
        OrderItem.objects.create(
            order=self.order_completed,
            menu_item=self.menu_item,
            quantity=1,
            price_at_order=Decimal("120.00"),
            item_name_at_order="Garlic Bread",
            category_name_at_order="Appetizers"
        )
        
        # Create CANCELLED order
        self.order_cancelled = Order.objects.create(
            customer_name="Cancelled Cust",
            customer_phone="+919876543210",
            subtotal_amount=Decimal("120.00"),
            tax_amount=Decimal("6.00"),
            total_amount=Decimal("126.00"),
            status="CANCELLED"
        )
        
    def test_manager_dashboard_metrics(self):
        self.client.login(username="manager", password="password123")
        response = self.client.get(reverse("restaurant:manager_dashboard"))
        self.assertEqual(response.status_code, 200)
        
        # Revenue should be 126.00 (from completed orders only)
        self.assertEqual(response.context["completed_revenue"], Decimal("126.00"))
        # Total orders count: 2 (completed + cancelled)
        self.assertEqual(response.context["total_orders"], 2)
        # Cancellation rate: (1 / 2) * 100 = 50.0%
        self.assertEqual(response.context["cancellation_rate"], 50.0)
        
    def test_manager_csv_export_view(self):
        self.client.login(username="manager", password="password123")
        response = self.client.get(reverse("restaurant:manager_csv_export"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        
        # Verify CSV contents
        content = response.content.decode("utf-8-sig") # Remove BOM
        csv_reader = csv.reader(content.splitlines())
        rows = list(csv_reader)
        self.assertGreater(len(rows), 1)
        headers = rows[0]
        self.assertIn("Order ID", headers)
        self.assertIn("Subtotal (INR)", headers)

    def test_csv_export_formula_injection_escaping(self):
        self.client.login(username="manager", password="password123")
        # Create order with formula injection name
        order_inject = Order.objects.create(
            customer_name="=SUM(A1:A5)",
            customer_phone="+919876543210",
            status="COMPLETED"
        )
        response = self.client.get(reverse("restaurant:manager_csv_export"))
        content = response.content.decode("utf-8-sig")
        self.assertIn("'=SUM(A1:A5)", content) # Should be prefixed with a single quote

    def test_menu_item_creation_audit_logging(self):
        self.client.login(username="manager", password="password123")
        create_url = reverse("restaurant:manager_menu_create")
        data = {
            "category": self.category.id,
            "name": "New Fries",
            "description": "Tasty fries",
            "price": "80.00",
            "is_available": "on"
        }
        response = self.client.post(create_url, data)
        self.assertEqual(response.status_code, 302)
        
        # Verify AuditLog created
        self.assertTrue(AuditLog.objects.filter(
            action="MENU_ITEM_CREATE",
            target_type="MenuItem"
        ).exists())
        
    def test_order_cancellation_audit_logging(self):
        self.client.login(username="manager", password="password123")
        order_to_cancel = Order.objects.create(
            customer_name="Active Cust",
            customer_phone="+919876543210",
            status="RECEIVED"
        )
        url = reverse("restaurant:manager_order_cancel", kwargs={"pk": order_to_cancel.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        
        # Verify order cancelled and log generated
        order_to_cancel.refresh_from_db()
        self.assertEqual(order_to_cancel.status, "CANCELLED")
        self.assertTrue(AuditLog.objects.filter(
            action="ORDER_CANCEL",
            target_type="Order",
            target_id=str(order_to_cancel.id)
        ).exists())
