from datetime import timedelta
from decimal import Decimal
from django.contrib.auth.models import User, Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from restaurant.models import Order, AuditLog

class PhaseBTests(TestCase):
    def setUp(self):
        # Create users & groups
        self.kitchen_group, _ = Group.objects.get_or_create(name="Kitchen Staff")
        self.kitchen_user = User.objects.create_user(username="kitchen", password="password123")
        self.kitchen_user.groups.add(self.kitchen_group)
        
        self.manager_group, _ = Group.objects.get_or_create(name="Managers")
        self.manager_user = User.objects.create_user(username="manager", password="password123")
        self.manager_user.groups.add(self.manager_group)
        
        self.regular_user = User.objects.create_user(username="customer", password="password123")
        
        # Create base order
        self.order = Order.objects.create(
            customer_name="Test Customer",
            customer_phone="+919876543210",
            table_number=5,
            subtotal_amount=Decimal("100.00"),
            tax_amount=Decimal("5.00"),
            total_amount=Decimal("105.00"),
            status="RECEIVED",
            priority="NORMAL"
        )
        
    def test_estimated_prep_time_validators(self):
        from django.core.exceptions import ValidationError
        self.order.estimated_preparation_minutes = 4
        with self.assertRaises(ValidationError):
            self.order.full_clean()
            
        self.order.estimated_preparation_minutes = 181
        with self.assertRaises(ValidationError):
            self.order.full_clean()
            
        self.order.estimated_preparation_minutes = 15
        self.order.full_clean()
        
    def test_is_delayed_property(self):
        self.assertFalse(self.order.is_delayed)
        
        self.order.estimated_preparation_minutes = 10
        self.order.save()
        self.assertFalse(self.order.is_delayed)
        
        Order.objects.filter(id=self.order.id).update(
            created_at=timezone.now() - timedelta(minutes=11)
        )
        
        self.order.refresh_from_db()
        self.assertTrue(self.order.is_delayed)
        
        self.order.status = "COMPLETED"
        self.order.save()
        self.assertFalse(self.order.is_delayed)
        
    def test_kitchen_staff_priority_update(self):
        self.client.login(username="kitchen", password="password123")
        url = reverse("restaurant:kitchen_order_status", kwargs={"pk": self.order.id})
        
        response = self.client.post(url, {"action": "priority", "priority": "URGENT"})
        self.assertEqual(response.status_code, 302)
        
        self.order.refresh_from_db()
        self.assertEqual(self.order.priority, "URGENT")
        
        self.assertTrue(AuditLog.objects.filter(
            action="PRIORITY_CHANGE",
            target_type="Order",
            target_id=str(self.order.id)
        ).exists())

    def test_kitchen_staff_prep_time_update(self):
        self.client.login(username="kitchen", password="password123")
        url = reverse("restaurant:kitchen_order_status", kwargs={"pk": self.order.id})
        
        response = self.client.post(url, {"action": "prep_time", "estimated_preparation_minutes": "30"})
        self.assertEqual(response.status_code, 302)
        
        self.order.refresh_from_db()
        self.assertEqual(self.order.estimated_preparation_minutes, 30)
        
        self.assertTrue(AuditLog.objects.filter(
            action="PREP_TIME_CHANGE",
            target_type="Order",
            target_id=str(self.order.id)
        ).exists())

    def test_kitchen_dashboard_sorting(self):
        self.client.login(username="kitchen", password="password123")
        order_new = Order.objects.create(
            customer_name="New Order", customer_phone="+919876543210", status="RECEIVED", priority="NORMAL"
        )
        order_priority = Order.objects.create(
            customer_name="Priority Order", customer_phone="+919876543210", status="RECEIVED", priority="PRIORITY"
        )
        order_urgent = Order.objects.create(
            customer_name="Urgent Order", customer_phone="+919876543210", status="RECEIVED", priority="URGENT"
        )
        
        response = self.client.get(reverse("restaurant:kitchen_dashboard"))
        orders = response.context["orders"]
        self.assertEqual(orders[0].id, self.order.id)
        
        response = self.client.get(reverse("restaurant:kitchen_dashboard"), {"sort": "priority"})
        orders = response.context["orders"]
        self.assertEqual(orders[0].id, order_urgent.id)
        self.assertEqual(orders[1].id, order_priority.id)
