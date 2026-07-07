from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from restaurant.models import Category, MenuItem, Order, OrderItem


class KitchenViewsTest(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        from django.contrib.auth.models import Group
        User = get_user_model()
        
        # Create groups
        self.kitchen_group, _ = Group.objects.get_or_create(name='Kitchen Staff')
        
        # Create test users
        self.staff_user = User.objects.create_user(
            username="staff_chef",
            password="chefpassword123",
            is_staff=False
        )
        self.staff_user.groups.add(self.kitchen_group)
        
        self.customer_user = User.objects.create_user(
            username="customer_guy",
            password="custpassword123",
            is_staff=False
        )

        # Seeding data
        self.category = Category.objects.create(name="Mains", icon="bi-fire")
        self.menu_item_1 = MenuItem.objects.create(
            category=self.category,
            name="Chicken Biryani",
            price=Decimal("250.00"),
            is_available=True
        )
        self.menu_item_2 = MenuItem.objects.create(
            category=self.category,
            name="Cold Coffee",
            price=Decimal("110.00"),
            is_available=True
        )

        # Create active and completed orders
        self.order_received = Order.objects.create(
            customer_name="Alice Received",
            customer_phone="9876543210",
            table_number=2,
            total_amount=Decimal("262.50"),
            status="RECEIVED"
        )
        OrderItem.objects.create(
            order=self.order_received,
            menu_item=self.menu_item_1,
            quantity=1,
            price_at_order=Decimal("250.00")
        )

        self.order_preparing = Order.objects.create(
            customer_name="Bob Preparing",
            customer_phone="9876543210",
            table_number=3,
            total_amount=Decimal("115.50"),
            status="PREPARING"
        )
        OrderItem.objects.create(
            order=self.order_preparing,
            menu_item=self.menu_item_2,
            quantity=1,
            price_at_order=Decimal("110.00")
        )

        self.order_ready = Order.objects.create(
            customer_name="Charlie Ready",
            customer_phone="9876543210",
            table_number=4,
            total_amount=Decimal("378.00"),
            status="READY"
        )
        OrderItem.objects.create(
            order=self.order_ready,
            menu_item=self.menu_item_1,
            quantity=1,
            price_at_order=Decimal("250.00")
        )
        OrderItem.objects.create(
            order=self.order_ready,
            menu_item=self.menu_item_2,
            quantity=1,
            price_at_order=Decimal("110.00")
        )

        self.order_completed = Order.objects.create(
            customer_name="Completed Order User",
            customer_phone="9876543210",
            table_number=1,
            total_amount=Decimal("262.50"),
            status="COMPLETED"
        )
        OrderItem.objects.create(
            order=self.order_completed,
            menu_item=self.menu_item_1,
            quantity=1,
            price_at_order=Decimal("250.00")
        )

    def test_kitchen_login_page_renders(self):
        response = self.client.get(reverse("restaurant:kitchen_login"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "restaurant/kitchen_login.html")
        self.assertContains(response, "Username")
        self.assertContains(response, "Password")

    def test_valid_staff_login(self):
        payload = {
            "username": "staff_chef",
            "password": "chefpassword123"
        }
        response = self.client.post(reverse("restaurant:kitchen_login"), payload)
        # Should redirect to kitchen dashboard
        self.assertRedirects(response, reverse("restaurant:kitchen_dashboard"))

    def test_invalid_login(self):
        payload = {
            "username": "staff_chef",
            "password": "wrong_password"
        }
        response = self.client.post(reverse("restaurant:kitchen_login"), payload)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "restaurant/kitchen_login.html")
        self.assertContains(response, "Invalid credentials")

    def test_logout_post(self):
        # Authenticate staff
        self.client.login(username="staff_chef", password="chefpassword123")
        
        response = self.client.post(reverse("restaurant:kitchen_logout"))
        self.assertRedirects(response, reverse("restaurant:kitchen_login"))

        # Verify dashboard is no longer accessible
        response = self.client.get(reverse("restaurant:kitchen_dashboard"))
        self.assertRedirects(response, reverse("restaurant:kitchen_login"))

    def test_logout_get_restricted(self):
        self.client.login(username="staff_chef", password="chefpassword123")
        # GET request to logout view returns Method Not Allowed (405) in Django 5+
        response = self.client.get(reverse("restaurant:kitchen_logout"))
        self.assertEqual(response.status_code, 405)

    def test_anonymous_access_blocked(self):
        # Dashboard redirect
        response = self.client.get(reverse("restaurant:kitchen_dashboard"))
        self.assertRedirects(response, reverse("restaurant:kitchen_login"))

        # Detail page redirect
        response = self.client.get(reverse("restaurant:kitchen_order_detail", args=[self.order_received.id]))
        self.assertRedirects(response, reverse("restaurant:kitchen_login"))

        # Status update redirect
        response = self.client.post(
            reverse("restaurant:kitchen_order_status", args=[self.order_received.id]),
            {"status": "PREPARING"}
        )
        self.assertRedirects(response, reverse("restaurant:kitchen_login"))

    def test_authenticated_non_staff_blocked(self):
        self.client.login(username="customer_guy", password="custpassword123")

        # Dashboard -> 403 Forbidden
        response = self.client.get(reverse("restaurant:kitchen_dashboard"))
        self.assertEqual(response.status_code, 403)

        # Detail -> 403 Forbidden
        response = self.client.get(reverse("restaurant:kitchen_order_detail", args=[self.order_received.id]))
        self.assertEqual(response.status_code, 403)

        # Status update -> 403 Forbidden
        response = self.client.post(
            reverse("restaurant:kitchen_order_status", args=[self.order_received.id]),
            {"status": "PREPARING"}
        )
        self.assertEqual(response.status_code, 403)

    def test_staff_access_allowed(self):
        self.client.login(username="staff_chef", password="chefpassword123")

        # Dashboard -> 200
        response = self.client.get(reverse("restaurant:kitchen_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "restaurant/kitchen_dashboard.html")

        # Detail -> 200
        response = self.client.get(reverse("restaurant:kitchen_order_detail", args=[self.order_received.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "restaurant/kitchen_order_detail.html")

    def test_dashboard_active_orders_display(self):
        self.client.login(username="staff_chef", password="chefpassword123")
        response = self.client.get(reverse("restaurant:kitchen_dashboard"))
        
        # Verify active orders appear
        self.assertContains(response, "Alice Received")
        self.assertContains(response, "Bob Preparing")
        self.assertContains(response, "Charlie Ready")
        
        # Items and quantities check
        self.assertContains(response, "Chicken Biryani")
        self.assertContains(response, "Cold Coffee")
        self.assertContains(response, "1x")

        # Exclude completed orders check
        self.assertNotContains(response, "Completed Order User")

    def test_dashboard_ordering(self):
        # Received orders list in context should be sorted oldest first (created_at ascending)
        self.client.login(username="staff_chef", password="chefpassword123")
        response = self.client.get(reverse("restaurant:kitchen_dashboard"))
        
        received = response.context["received_orders"]
        # If we have multiple, verify chronological sequence
        order_received_2 = Order.objects.create(
            customer_name="Zack Received Later",
            customer_phone="9876543210",
            total_amount=Decimal("0.00"),
            status="RECEIVED"
        )
        
        # Refresh dashboard view
        response = self.client.get(reverse("restaurant:kitchen_dashboard"))
        received = response.context["received_orders"]
        self.assertEqual(len(received), 2)
        # Chronological sorting: oldest first
        self.assertEqual(received[0].customer_name, "Alice Received")
        self.assertEqual(received[1].customer_name, "Zack Received Later")

    def test_order_detail_view_parameters(self):
        self.client.login(username="staff_chef", password="chefpassword123")
        response = self.client.get(reverse("restaurant:kitchen_order_detail", args=[self.order_ready.id]))
        self.assertEqual(response.status_code, 200)
        
        # Context checks
        self.assertEqual(response.context["subtotal"], Decimal("360.00"))
        self.assertEqual(response.context["tax"], Decimal("18.00"))
        self.assertEqual(response.context["grand_total"], Decimal("378.00"))
        self.assertEqual(response.context["next_status"], "COMPLETED")

        # Display details check
        self.assertContains(response, "Charlie Ready")
        self.assertContains(response, "9876543210")
        self.assertContains(response, "Table #4")
        self.assertContains(response, "Ready for Pickup / Delivery")

    def test_status_update_post_only(self):
        self.client.login(username="staff_chef", password="chefpassword123")
        
        # GET on status update URL returns 405 Method Not Allowed
        response = self.client.get(reverse("restaurant:kitchen_order_status", args=[self.order_received.id]))
        self.assertEqual(response.status_code, 405)
        
        # Status remains RECEIVED
        self.order_received.refresh_from_db()
        self.assertEqual(self.order_received.status, "RECEIVED")

    def test_valid_transitions(self):
        self.client.login(username="staff_chef", password="chefpassword123")

        # 1. RECEIVED -> PREPARING
        response = self.client.post(
            reverse("restaurant:kitchen_order_status", args=[self.order_received.id]),
            {"status": "PREPARING"}
        )
        self.assertRedirects(response, reverse("restaurant:kitchen_dashboard"))
        self.order_received.refresh_from_db()
        self.assertEqual(self.order_received.status, "PREPARING")

        # 2. PREPARING -> READY
        response = self.client.post(
            reverse("restaurant:kitchen_order_status", args=[self.order_preparing.id]),
            {"status": "READY"}
        )
        self.assertRedirects(response, reverse("restaurant:kitchen_dashboard"))
        self.order_preparing.refresh_from_db()
        self.assertEqual(self.order_preparing.status, "READY")

        # 3. READY -> COMPLETED
        response = self.client.post(
            reverse("restaurant:kitchen_order_status", args=[self.order_ready.id]),
            {"status": "COMPLETED"}
        )
        self.assertRedirects(response, reverse("restaurant:kitchen_dashboard"))
        self.order_ready.refresh_from_db()
        self.assertEqual(self.order_ready.status, "COMPLETED")

        # Verify completed order disappears from active list
        response_dash = self.client.get(reverse("restaurant:kitchen_dashboard"))
        self.assertNotContains(response_dash, "Charlie Ready")

    def test_invalid_and_skipped_transitions(self):
        self.client.login(username="staff_chef", password="chefpassword123")

        # Skipped transition: RECEIVED to READY
        response = self.client.post(
            reverse("restaurant:kitchen_order_status", args=[self.order_received.id]),
            {"status": "READY"}
        )
        # Should redirect to detail with error message
        self.assertRedirects(response, reverse("restaurant:kitchen_order_detail", args=[self.order_received.id]))
        self.order_received.refresh_from_db()
        self.assertEqual(self.order_received.status, "RECEIVED")

        # Skipped transition: RECEIVED to COMPLETED
        response = self.client.post(
            reverse("restaurant:kitchen_order_status", args=[self.order_received.id]),
            {"status": "COMPLETED"}
        )
        self.order_received.refresh_from_db()
        self.assertEqual(self.order_received.status, "RECEIVED")

        # Skipped transition: PREPARING to COMPLETED
        response = self.client.post(
            reverse("restaurant:kitchen_order_status", args=[self.order_preparing.id]),
            {"status": "COMPLETED"}
        )
        self.order_preparing.refresh_from_db()
        self.assertEqual(self.order_preparing.status, "PREPARING")

    def test_backward_transitions(self):
        self.client.login(username="staff_chef", password="chefpassword123")

        # Backward: PREPARING to RECEIVED
        response = self.client.post(
            reverse("restaurant:kitchen_order_status", args=[self.order_preparing.id]),
            {"status": "RECEIVED"}
        )
        self.order_preparing.refresh_from_db()
        self.assertEqual(self.order_preparing.status, "PREPARING")

        # Backward: READY to PREPARING
        response = self.client.post(
            reverse("restaurant:kitchen_order_status", args=[self.order_ready.id]),
            {"status": "PREPARING"}
        )
        self.order_ready.refresh_from_db()
        self.assertEqual(self.order_ready.status, "READY")

        # Backward: COMPLETED to READY
        response = self.client.post(
            reverse("restaurant:kitchen_order_status", args=[self.order_completed.id]),
            {"status": "READY"}
        )
        self.order_completed.refresh_from_db()
        self.assertEqual(self.order_completed.status, "COMPLETED")

    def test_same_status_transition_rejection(self):
        self.client.login(username="staff_chef", password="chefpassword123")

        response = self.client.post(
            reverse("restaurant:kitchen_order_status", args=[self.order_received.id]),
            {"status": "RECEIVED"}
        )
        self.order_received.refresh_from_db()
        self.assertEqual(self.order_received.status, "RECEIVED")

    def test_unknown_status_rejection(self):
        self.client.login(username="staff_chef", password="chefpassword123")

        response = self.client.post(
            reverse("restaurant:kitchen_order_status", args=[self.order_received.id]),
            {"status": "INVALID_STATUS_CODE"}
        )
        self.order_received.refresh_from_db()
        self.assertEqual(self.order_received.status, "RECEIVED")

    def test_csrf_status_enforcement(self):
        from django.test import Client as TestClient
        csrf_client = TestClient(enforce_csrf_checks=True)
        csrf_client.login(username="staff_chef", password="chefpassword123")

        response = csrf_client.post(
            reverse("restaurant:kitchen_order_status", args=[self.order_received.id]),
            {"status": "PREPARING"}
        )
        # CSRF missing -> HTTP 403 Forbidden
        self.assertEqual(response.status_code, 403)
        self.order_received.refresh_from_db()
        self.assertEqual(self.order_received.status, "RECEIVED")

    def test_detail_page_historical_prices(self):
        # Display order detail page
        self.client.login(username="staff_chef", password="chefpassword123")
        
        # Change current MenuItem price in DB
        self.menu_item_1.price = Decimal("500.00")
        self.menu_item_1.save()

        response = self.client.get(reverse("restaurant:kitchen_order_detail", args=[self.order_received.id]))
        # The subtotal and template display must reflect the historical price (250.00), not the updated current price
        self.assertEqual(response.context["subtotal"], Decimal("250.00"))
        self.assertContains(response, "₹250.00")
        self.assertNotContains(response, "₹500.00")
