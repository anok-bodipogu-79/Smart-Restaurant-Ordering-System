from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from restaurant.models import Category, MenuItem, Order, OrderItem


class ManagerOperationsTests(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User, Group
        
        self.managers_group, _ = Group.objects.get_or_create(name="Managers")
        
        self.manager_user = User.objects.create_user(
            username="manager1", password="managerpassword123"
        )
        self.manager_user.groups.add(self.managers_group)
        
        self.superuser = User.objects.create_superuser(
            username="super1", password="superpassword123"
        )
        
        self.kitchen_group, _ = Group.objects.get_or_create(name="Kitchen Staff")
        
        self.kitchen_user = User.objects.create_user(
            username="kitchen1", password="kitchenpassword123"
        )
        self.kitchen_user.groups.add(self.kitchen_group)
        
        self.customer_user = User.objects.create_user(
            username="customer1", password="customerpassword123"
        )
        
        self.category = Category.objects.create(name="Mains", icon="bi-fire")
        self.item_1 = MenuItem.objects.create(
            category=self.category,
            name="Chicken Biryani",
            price=Decimal("250.00"),
            is_available=True
        )
        self.item_2 = MenuItem.objects.create(
            category=self.category,
            name="Garlic Naan",
            price=Decimal("50.00"),
            is_available=True
        )
        
        self.order_completed = Order.objects.create(
            customer_name="Completed Cust",
            customer_phone="9876543210",
            table_number=1,
            subtotal_amount=Decimal("550.00"),
            tax_amount=Decimal("27.50"),
            tax_rate=Decimal("0.0500"),
            total_amount=Decimal("577.50"),
            status="COMPLETED"
        )
        OrderItem.objects.create(
            order=self.order_completed,
            menu_item=self.item_1,
            quantity=2,
            price_at_order=Decimal("250.00"),
            item_name_at_order="Chicken Biryani",
            category_name_at_order="Mains"
        )
        OrderItem.objects.create(
            order=self.order_completed,
            menu_item=self.item_2,
            quantity=1,
            price_at_order=Decimal("50.00"),
            item_name_at_order="Garlic Naan",
            category_name_at_order="Mains"
        )

        self.order_received = Order.objects.create(
            customer_name="Received Cust",
            customer_phone="9876543210",
            table_number=2,
            subtotal_amount=Decimal("50.00"),
            tax_amount=Decimal("2.50"),
            tax_rate=Decimal("0.0500"),
            total_amount=Decimal("52.50"),
            status="RECEIVED"
        )
        OrderItem.objects.create(
            order=self.order_received,
            menu_item=self.item_2,
            quantity=1,
            price_at_order=Decimal("50.00"),
            item_name_at_order="Garlic Naan",
            category_name_at_order="Mains"
        )

    def test_manager_dashboard_access_rules(self):
        # Anonymous redirects to login
        response = self.client.get(reverse("restaurant:manager_dashboard"))
        self.assertRedirects(response, reverse("restaurant:manager_login"))

        # Customer gets 403
        self.client.login(username="customer1", password="customerpassword123")
        response = self.client.get(reverse("restaurant:manager_dashboard"))
        self.assertEqual(response.status_code, 403)
        self.client.logout()

        # Kitchen-only gets 403
        self.client.login(username="kitchen1", password="kitchenpassword123")
        response = self.client.get(reverse("restaurant:manager_dashboard"))
        self.assertEqual(response.status_code, 403)
        self.client.logout()

        # Manager in Managers group gets 200
        self.client.login(username="manager1", password="managerpassword123")
        response = self.client.get(reverse("restaurant:manager_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.client.logout()

        # Superuser gets 200
        self.client.login(username="super1", password="superpassword123")
        response = self.client.get(reverse("restaurant:manager_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.client.logout()

    def test_manager_login_and_logout(self):
        # Invalid login
        response = self.client.post(reverse("restaurant:manager_login"), {
            "username": "manager1", "password": "wrongpassword"
        })
        self.assertEqual(response.status_code, 200)

        # Valid login redirect
        response = self.client.post(reverse("restaurant:manager_login"), {
            "username": "manager1", "password": "managerpassword123"
        })
        self.assertRedirects(response, reverse("restaurant:manager_dashboard"))

        # Logout via GET rejected with 405
        response = self.client.get(reverse("restaurant:manager_logout"))
        self.assertEqual(response.status_code, 405)

        # Logout via POST successful
        response = self.client.post(reverse("restaurant:manager_logout"))
        self.assertRedirects(response, reverse("restaurant:manager_login"))

    def test_manager_dashboard_metrics(self):
        self.client.login(username="manager1", password="managerpassword123")
        response = self.client.get(reverse("restaurant:manager_dashboard"), {"range": "today"})
        self.assertEqual(response.status_code, 200)
        
        self.assertEqual(response.context["total_orders"], 2)
        self.assertEqual(response.context["completed_revenue"], Decimal("577.50"))
        self.assertEqual(response.context["avg_order_value"], Decimal("577.50"))
        
        self.assertEqual(response.context["status_counts"]["received"], 1)
        self.assertEqual(response.context["status_counts"]["completed"], 1)
        
        top_items = list(response.context["top_items"])
        self.assertEqual(len(top_items), 2)
        self.assertEqual(top_items[0]["item_name_at_order"], "Chicken Biryani")

    def test_order_cancellation_rules(self):
        self.client.login(username="manager1", password="managerpassword123")
        
        # RECEIVED -> CANCELLED succeeds
        response = self.client.post(reverse("restaurant:manager_order_cancel", args=[self.order_received.id]))
        self.assertRedirects(response, reverse("restaurant:manager_order_detail", args=[self.order_received.id]))
        self.order_received.refresh_from_db()
        self.assertEqual(self.order_received.status, "CANCELLED")

        # CANCELLED -> CANCELLED rejected
        response = self.client.post(reverse("restaurant:manager_order_cancel", args=[self.order_received.id]))
        self.order_received.refresh_from_db()
        self.assertEqual(self.order_received.status, "CANCELLED")

        # COMPLETED -> CANCELLED rejected
        response = self.client.post(reverse("restaurant:manager_order_cancel", args=[self.order_completed.id]))
        self.order_completed.refresh_from_db()
        self.assertEqual(self.order_completed.status, "COMPLETED")

        # GET cancellation fails with 405
        response = self.client.get(reverse("restaurant:manager_order_cancel", args=[self.order_completed.id]))
        self.assertEqual(response.status_code, 405)

    def test_menu_management(self):
        self.client.login(username="manager1", password="managerpassword123")

        # Create Item
        payload = {
            "category": self.category.id,
            "name": "Butter Chicken",
            "description": "Butter chicken",
            "price": "280.00",
            "is_available": True,
            "is_vegetarian": False,
            "is_spicy": True
        }
        response = self.client.post(reverse("restaurant:manager_menu_create"), payload)
        self.assertRedirects(response, reverse("restaurant:manager_menu_list"))
        self.assertTrue(MenuItem.objects.filter(name="Butter Chicken").exists())

        # Toggle Availability
        item = MenuItem.objects.get(name="Butter Chicken")
        self.assertTrue(item.is_available)
        response = self.client.post(reverse("restaurant:manager_menu_availability", args=[item.id]))
        self.assertRedirects(response, reverse("restaurant:manager_menu_list"))
        item.refresh_from_db()
        self.assertFalse(item.is_available)
