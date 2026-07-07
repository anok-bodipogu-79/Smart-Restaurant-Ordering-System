import json
import uuid
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from restaurant.models import Category, MenuItem, Order, OrderItem


class OrderTrackingTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        from django.contrib.auth.models import Group
        self.kitchen_group, _ = Group.objects.get_or_create(name='Kitchen Staff')
        self.staff_user = User.objects.create_user(
            username="staff_chef_track",
            password="chefpassword123",
            is_staff=False
        )
        self.staff_user.groups.add(self.kitchen_group)

        self.category = Category.objects.create(name="Drinks", icon="bi-cup-hot")
        self.menu_item = MenuItem.objects.create(
            category=self.category,
            name="Lemon Tea",
            price=Decimal("60.00"),
            is_available=True
        )

        self.order = Order.objects.create(
            customer_name="Track Customer",
            customer_phone="9876543210",
            table_number=5,
            subtotal_amount=Decimal("120.00"),
            tax_amount=Decimal("6.00"),
            tax_rate=Decimal("0.0500"),
            total_amount=Decimal("126.00"),
            status="RECEIVED"
        )
        self.order_item = OrderItem.objects.create(
            order=self.order,
            menu_item=self.menu_item,
            quantity=2,
            price_at_order=Decimal("60.00"),
            item_name_at_order="Lemon Tea"
        )

    def test_tracking_search_page_renders(self):
        response = self.client.get(reverse("restaurant:order_tracking"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "restaurant/order_tracking.html")
        self.assertContains(response, "Track Your Order")
        self.assertContains(response, "id_tracking_token")

    def test_valid_tracking_search_redirects(self):
        payload = {"tracking_token": str(self.order.tracking_token)}
        response = self.client.post(reverse("restaurant:order_tracking"), payload)
        self.assertRedirects(response, reverse("restaurant:order_tracking_detail", args=[self.order.tracking_token]))

    def test_nonexistent_tracking_search_shows_error(self):
        payload = {"tracking_token": str(uuid.uuid4())}
        response = self.client.post(reverse("restaurant:order_tracking"), payload)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "restaurant/order_tracking.html")
        self.assertContains(response, "No order was found with that Tracking ID.")

    def test_invalid_tracking_search_shows_field_errors(self):
        payload = {"tracking_token": "invalid-uuid-string"}
        response = self.client.post(reverse("restaurant:order_tracking"), payload)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please enter a valid Tracking ID (UUID).")

    def test_tracking_detail_page(self):
        response = self.client.get(reverse("restaurant:order_tracking_detail", args=[self.order.tracking_token]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "restaurant/order_tracking_detail.html")
        
        self.assertContains(response, f"Order Number #{self.order.id}")
        self.assertContains(response, "Lemon Tea")
        self.assertContains(response, "2")  # Quantity
        self.assertContains(response, "₹60.00")  # Price at order
        self.assertContains(response, "₹120.00")  # Line total
        self.assertContains(response, "₹126.00")  # Grand total
        
        # Privacy check: Customer phone should NOT be exposed publicly on tracking page
        self.assertNotContains(response, "9876543210")

    def test_tracking_detail_404(self):
        response = self.client.get(reverse("restaurant:order_tracking_detail", args=[uuid.uuid4()]))
        self.assertEqual(response.status_code, 404)

    def test_historical_price_on_tracking_detail(self):
        # Alter current MenuItem price in database
        self.menu_item.price = Decimal("100.00")
        self.menu_item.save()

        response = self.client.get(reverse("restaurant:order_tracking_detail", args=[self.order.tracking_token]))
        self.assertEqual(response.status_code, 200)
        # Detail must reflect historical 60.00 price, not current 100.00
        self.assertContains(response, "₹60.00")
        self.assertNotContains(response, "₹100.00")

    def test_status_display_workflow_renders(self):
        # RECEIVED status
        response = self.client.get(reverse("restaurant:order_tracking_detail", args=[self.order.tracking_token]))
        self.assertContains(response, "Order Received")
        self.assertContains(response, 'data-current-status="RECEIVED"')

        # PREPARING status
        self.order.status = "PREPARING"
        self.order.save()
        response = self.client.get(reverse("restaurant:order_tracking_detail", args=[self.order.tracking_token]))
        self.assertContains(response, "In Kitchen - Preparing")
        self.assertContains(response, 'data-current-status="PREPARING"')

        # READY status
        self.order.status = "READY"
        self.order.save()
        response = self.client.get(reverse("restaurant:order_tracking_detail", args=[self.order.tracking_token]))
        self.assertContains(response, "Ready for Pickup / Delivery")
        self.assertContains(response, 'data-current-status="READY"')

        # COMPLETED status
        self.order.status = "COMPLETED"
        self.order.save()
        response = self.client.get(reverse("restaurant:order_tracking_detail", args=[self.order.tracking_token]))
        self.assertContains(response, "Completed")
        self.assertContains(response, 'data-current-status="COMPLETED"')

    def test_json_status_endpoint(self):
        response = self.client.get(reverse("restaurant:order_tracking_status", args=[self.order.tracking_token]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertEqual(response["Cache-Control"], "no-store, no-cache, must-revalidate, max-age=0")
        
        data = json.loads(response.content)
        self.assertTrue(data["success"])
        self.assertEqual(data["tracking_token"], str(self.order.tracking_token))
        self.assertEqual(data["status"], "RECEIVED")
        self.assertEqual(data["status_display"], "Order Received")
        self.assertTrue(data["success"])
        self.assertFalse(data["is_completed"])

        # Data minimization: ensure phone, name, and internal ID are NOT in JSON payload
        self.assertNotIn("customer_phone", data)
        self.assertNotIn("customer_name", data)
        self.assertNotIn("order_id", data)

    def test_json_status_completed(self):
        self.order.status = "COMPLETED"
        self.order.save()
        
        response = self.client.get(reverse("restaurant:order_tracking_status", args=[self.order.tracking_token]))
        data = json.loads(response.content)
        self.assertTrue(data["is_completed"])
        self.assertEqual(data["status"], "COMPLETED")

    def test_json_status_404(self):
        response = self.client.get(reverse("restaurant:order_tracking_status", args=[uuid.uuid4()]))
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.content)
        self.assertFalse(data["success"])
        self.assertEqual(data["error"], "Order not found.")

    def test_json_status_post_rejection(self):
        response = self.client.post(reverse("restaurant:order_tracking_status", args=[self.order.tracking_token]))
        self.assertEqual(response.status_code, 405)

    def test_order_success_page_has_track_order_link(self):
        response = self.client.get(reverse("restaurant:order_success", args=[self.order.tracking_token]))
        self.assertEqual(response.status_code, 200)
        # Must display Track Order button linking to detail page using UUID
        self.assertContains(response, reverse("restaurant:order_tracking_detail", args=[self.order.tracking_token]))

    def test_kitchen_to_tracking_integration(self):
        # 1. Initially RECEIVED
        response = self.client.get(reverse("restaurant:order_tracking_status", args=[self.order.tracking_token]))
        self.assertEqual(json.loads(response.content)["status"], "RECEIVED")

        # 2. Staff updates order using kitchen dashboard URL
        self.client.login(username="staff_chef_track", password="chefpassword123")
        self.client.post(
            reverse("restaurant:kitchen_order_status", args=[self.order.id]),
            {"status": "PREPARING"}
        )

        # 3. Customer tracking status reflects changes automatically
        response = self.client.get(reverse("restaurant:order_tracking_status", args=[self.order.tracking_token]))
        self.assertEqual(json.loads(response.content)["status"], "PREPARING")

    def test_custom_error_pages_exist(self):
        # 404 page checks
        response = self.client.get("/nonexistent-page-url/")
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "404.html")
        self.assertContains(response, "404 - Page Not Found", status_code=404)

        # 403 page checks
        self.client.login(username="staff_chef_track", password="chefpassword123")
        self.staff_user.groups.remove(self.kitchen_group)
        self.staff_user.save()
        response = self.client.get(reverse("restaurant:kitchen_dashboard"))
        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, "403.html")
        self.assertContains(response, "403 - Access Denied", status_code=403)
