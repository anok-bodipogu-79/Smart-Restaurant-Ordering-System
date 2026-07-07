import json
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User, Group
from restaurant.models import Category, MenuItem, Order, OrderItem


class WorkflowIntegrationTests(TestCase):
    def setUp(self):
        # Setup Groups
        self.managers_group, _ = Group.objects.get_or_create(name="Managers")
        
        # Setup Users
        self.manager_user = User.objects.create_user(
            username="testmanager", password="managerpassword123"
        )
        self.manager_user.groups.add(self.managers_group)
        
        self.kitchen_group, _ = Group.objects.get_or_create(name='Kitchen Staff')
        self.kitchen_user = User.objects.create_user(
            username="testkitchen", password="kitchenpassword123"
        )
        self.kitchen_user.groups.add(self.kitchen_group)
        
        # Setup Initial Menu Catalog
        self.category_mains = Category.objects.create(name="Mains", icon="bi-fire")
        self.menu_item_1 = MenuItem.objects.create(
            category=self.category_mains,
            name="Chicken Curry",
            price=Decimal("200.00"),
            is_available=True
        )
        self.menu_item_2 = MenuItem.objects.create(
            category=self.category_mains,
            name="Butter Naan",
            price=Decimal("40.00"),
            is_available=True
        )

    def test_customer_ordering_workflow(self):
        # 1. Fetch public menu catalog
        response = self.client.get(reverse("restaurant:menu"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Chicken Curry")
        
        # 2. Sync cart to session (authoritative pricing re-calculated)
        cart_payload = {
            "items": [
                {"id": str(self.menu_item_1.id), "quantity": 2, "price": "1.00"},  # client-side price manipulation
                {"id": str(self.menu_item_2.id), "quantity": 1}
            ]
        }
        response = self.client.post(
            reverse("restaurant:cart_sync"),
            data=json.dumps(cart_payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        # Authoritative prices returned: 200.00, not manipulated 1.00
        self.assertEqual(data["items"][0]["price"], "200.00")
        
        # 3. Post to checkout
        checkout_payload = {
            "customer_name": "Integrated Cust",
            "customer_phone": "9876543210",
            "table_number": 12
        }
        response = self.client.post(reverse("restaurant:checkout"), checkout_payload)
        
        # Verify order creation
        self.assertEqual(Order.objects.count(), 1)
        order = Order.objects.first()
        self.assertRedirects(response, reverse("restaurant:order_success", args=[order.tracking_token]))
        
        # Recalculated amount: (200*2 + 40) = 440 + 5% tax = 462.00
        self.assertEqual(order.total_amount, Decimal("462.00"))
        
        # 4. View Success Page
        response = self.client.get(reverse("restaurant:order_success", args=[order.tracking_token]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Integrated Cust")
        
        # 5. Access Customer tracking page
        response = self.client.get(reverse("restaurant:order_tracking_detail", args=[order.tracking_token]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Order Received")

    def test_kitchen_workflow(self):
        # Create an order in RECEIVED state
        order = Order.objects.create(
            customer_name="Kitchen Customer",
            customer_phone="9876543210",
            table_number=4,
            subtotal_amount=Decimal("200.00"),
            tax_amount=Decimal("10.00"),
            total_amount=Decimal("210.00"),
            status="RECEIVED"
        )
        OrderItem.objects.create(
            order=order,
            menu_item=self.menu_item_1,
            quantity=1,
            price_at_order=Decimal("200.00"),
            item_name_at_order="Chicken Curry",
            category_name_at_order="Mains"
        )
        
        # 1. Staff Login
        login_response = self.client.post(reverse("restaurant:kitchen_login"), {
            "username": "testkitchen",
            "password": "kitchenpassword123"
        })
        self.assertRedirects(login_response, reverse("restaurant:kitchen_dashboard"))
        
        # 2. Staff views dashboard
        dash_response = self.client.get(reverse("restaurant:kitchen_dashboard"))
        self.assertEqual(dash_response.status_code, 200)
        self.assertContains(dash_response, "Kitchen Customer")
        
        # 3. Advance to PREPARING
        response = self.client.post(reverse("restaurant:kitchen_order_status", args=[order.id]), {"status": "PREPARING"})
        self.assertRedirects(response, reverse("restaurant:kitchen_dashboard"))
        order.refresh_from_db()
        self.assertEqual(order.status, "PREPARING")
        
        # 4. Advance to READY
        response = self.client.post(reverse("restaurant:kitchen_order_status", args=[order.id]), {"status": "READY"})
        self.assertRedirects(response, reverse("restaurant:kitchen_dashboard"))
        order.refresh_from_db()
        self.assertEqual(order.status, "READY")
        
        # 5. Advance to COMPLETED
        response = self.client.post(reverse("restaurant:kitchen_order_status", args=[order.id]), {"status": "COMPLETED"})
        self.assertRedirects(response, reverse("restaurant:kitchen_dashboard"))
        order.refresh_from_db()
        self.assertEqual(order.status, "COMPLETED")
        
        # 6. Verify dashboard does NOT show completed order
        dash_response2 = self.client.get(reverse("restaurant:kitchen_dashboard"))
        self.assertNotContains(dash_response2, "Kitchen Customer")

    def test_manager_workflow(self):
        # Create aRECEIVED order
        order = Order.objects.create(
            customer_name="Manager Customer",
            customer_phone="9876543210",
            table_number=5,
            subtotal_amount=Decimal("40.00"),
            tax_amount=Decimal("2.00"),
            total_amount=Decimal("42.00"),
            status="RECEIVED"
        )
        OrderItem.objects.create(
            order=order,
            menu_item=self.menu_item_2,
            quantity=1,
            price_at_order=Decimal("40.00"),
            item_name_at_order="Butter Naan",
            category_name_at_order="Mains"
        )
        
        # 1. Manager Login
        login_response = self.client.post(reverse("restaurant:manager_login"), {
            "username": "testmanager",
            "password": "managerpassword123"
        })
        self.assertRedirects(login_response, reverse("restaurant:manager_dashboard"))
        
        # 2. Manager views dashboard
        dash_response = self.client.get(reverse("restaurant:manager_dashboard"))
        self.assertEqual(dash_response.status_code, 200)
        self.assertContains(dash_response, "Manager Customer")
        
        # 3. Manager cancels order
        cancel_response = self.client.post(reverse("restaurant:manager_order_cancel", args=[order.id]))
        self.assertRedirects(cancel_response, reverse("restaurant:manager_order_detail", args=[order.id]))
        
        # Status check
        order.refresh_from_db()
        self.assertEqual(order.status, "CANCELLED")
        
        # 4. Excluded from kitchen active orders
        self.client.logout()
        self.client.login(username="testkitchen", password="kitchenpassword123")
        dash_response = self.client.get(reverse("restaurant:kitchen_dashboard"))
        self.assertNotContains(dash_response, "Manager Customer")
        
        # 5. Customer status tracking returns terminal state
        self.client.logout()
        response = self.client.get(reverse("restaurant:order_tracking_status", args=[order.tracking_token]))
        data = response.json()
        self.assertEqual(data["status"], "CANCELLED")
        self.assertTrue(data["is_cancelled"])
        self.assertTrue(data["is_terminal"])

    def test_menu_management_workflow(self):
        # 1. Manager Login
        self.client.post(reverse("restaurant:manager_login"), {
            "username": "testmanager",
            "password": "managerpassword123"
        })
        
        # 2. Create MenuItem
        create_payload = {
            "category": self.category_mains.id,
            "name": "Kadhai Paneer",
            "description": "Spicy Kadhai Paneer",
            "price": "180.00",
            "is_available": True,
            "is_vegetarian": True,
            "is_spicy": True
        }
        response = self.client.post(reverse("restaurant:manager_menu_create"), create_payload)
        self.assertRedirects(response, reverse("restaurant:manager_menu_list"))
        self.assertTrue(MenuItem.objects.filter(name="Kadhai Paneer").exists())
        menu_item = MenuItem.objects.get(name="Kadhai Paneer")
        
        # 3. Edit MenuItem
        edit_payload = {
            "category": self.category_mains.id,
            "name": "Kadhai Paneer Special",
            "description": "Extremely Spicy Kadhai Paneer",
            "price": "190.00",
            "is_available": True,
            "is_vegetarian": True,
            "is_spicy": True
        }
        response = self.client.post(reverse("restaurant:manager_menu_edit", args=[menu_item.id]), edit_payload)
        self.assertRedirects(response, reverse("restaurant:manager_menu_list"))
        menu_item.refresh_from_db()
        self.assertEqual(menu_item.name, "Kadhai Paneer Special")
        self.assertEqual(menu_item.price, Decimal("190.00"))
        
        # 4. Toggle Availability
        response = self.client.post(reverse("restaurant:manager_menu_availability", args=[menu_item.id]))
        self.assertRedirects(response, reverse("restaurant:manager_menu_list"))
        menu_item.refresh_from_db()
        self.assertFalse(menu_item.is_available)
        
        # 5. Customer Menu reflects status (Sold Out / Unavailable)
        self.client.logout()
        response = self.client.get(reverse("restaurant:menu"))
        self.assertContains(response, "Kadhai Paneer Special")
        self.assertContains(response, "Sold Out")
