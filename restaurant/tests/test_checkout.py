from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from restaurant.models import Category, MenuItem, Order, OrderItem
from restaurant.forms import CheckoutForm


class CartCheckoutViewTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Mains", icon="bi-fire")
        self.item_1 = MenuItem.objects.create(
            category=self.category,
            name="Chicken Biryani",
            price=Decimal("250.00"),
            is_available=True
        )
        self.item_2 = MenuItem.objects.create(
            category=self.category,
            name="Cold Coffee",
            price=Decimal("110.00"),
            is_available=True
        )
        self.item_unavailable = MenuItem.objects.create(
            category=self.category,
            name="Sold Out Item",
            price=Decimal("80.00"),
            is_available=False
        )

    def test_checkout_url_resolves(self):
        url = reverse("restaurant:checkout")
        self.assertEqual(url, "/checkout/")

    def test_checkout_get_empty_cart(self):
        response = self.client.get(reverse("restaurant:checkout"))
        # Should redirect to cart page
        self.assertRedirects(response, reverse("restaurant:cart"))

    def test_checkout_get_valid_cart(self):
        session = self.client.session
        session["cart"] = {
            str(self.item_1.id): {"quantity": 2},
            str(self.item_2.id): {"quantity": 1}
        }
        session.save()

        response = self.client.get(reverse("restaurant:checkout"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "restaurant/checkout.html")
        
        # Verify calculated Decimal totals are in context
        self.assertEqual(response.context["subtotal"], Decimal("610.00"))
        self.assertEqual(response.context["tax"], Decimal("30.50"))
        self.assertEqual(response.context["grand_total"], Decimal("640.50"))
        self.assertIn("form", response.context)
        self.assertIsInstance(response.context["form"], CheckoutForm)

    def test_checkout_post_empty_cart(self):
        payload = {
            "customer_name": "Jane Doe",
            "customer_phone": "9876543210",
            "table_number": 4
        }
        response = self.client.post(reverse("restaurant:checkout"), payload)
        self.assertRedirects(response, reverse("restaurant:cart"))
        self.assertEqual(Order.objects.count(), 0)

    def test_checkout_post_valid(self):
        session = self.client.session
        session["cart"] = {
            str(self.item_1.id): {"quantity": 2},
            str(self.item_2.id): {"quantity": 1}
        }
        session.save()

        payload = {
            "customer_name": "Jane Doe",
            "customer_phone": "9876543210",
            "table_number": 4
        }
        response = self.client.post(reverse("restaurant:checkout"), payload)
        
        # Check order was created and redirected
        self.assertEqual(Order.objects.count(), 1)
        order = Order.objects.first()
        self.assertRedirects(response, reverse("restaurant:order_success", args=[order.tracking_token]))
        
        # Check order parameters
        self.assertEqual(order.customer_name, "Jane Doe")
        self.assertEqual(order.customer_phone, "+919876543210")
        self.assertEqual(order.table_number, 4)
        self.assertEqual(order.total_amount, Decimal("640.50"))
        self.assertEqual(order.status, "RECEIVED")

        # Check order items
        order_items = list(order.items.all())
        self.assertEqual(len(order_items), 2)
        
        # Preserved historical prices check
        self.assertEqual(order_items[0].menu_item, self.item_1)
        self.assertEqual(order_items[0].quantity, 2)
        self.assertEqual(order_items[0].price_at_order, Decimal("250.00"))
        
        self.assertEqual(order_items[1].menu_item, self.item_2)
        self.assertEqual(order_items[1].quantity, 1)
        self.assertEqual(order_items[1].price_at_order, Decimal("110.00"))

        # Verify Django session cart was cleared
        self.assertEqual(self.client.session.get("cart"), {})

    def test_checkout_post_invalid_form_preserves_cart(self):
        session = self.client.session
        session["cart"] = {
            str(self.item_1.id): {"quantity": 2}
        }
        session.save()

        payload = {
            "customer_name": "",  # Invalid empty name
            "customer_phone": "not-a-phone",
            "table_number": 4
        }
        response = self.client.post(reverse("restaurant:checkout"), payload)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "restaurant/checkout.html")
        
        # No order created
        self.assertEqual(Order.objects.count(), 0)
        # Session cart preserved
        self.assertEqual(self.client.session.get("cart"), {str(self.item_1.id): {"quantity": 2}})

    def test_database_price_authority(self):
        session = self.client.session
        # Price in session/localStorage won't be sent anyway, but we check if view recalculates from DB
        session["cart"] = {
            str(self.item_1.id): {"quantity": 1}
        }
        session.save()

        # Update DB price to 300.00
        self.item_1.price = Decimal("300.00")
        self.item_1.save()

        payload = {
            "customer_name": "Jane Doe",
            "customer_phone": "9876543210",
            "table_number": 4
        }
        response = self.client.post(reverse("restaurant:checkout"), payload)
        
        order = Order.objects.first()
        # Grand total: 300.00 + 15.00 tax = 315.00
        self.assertEqual(order.total_amount, Decimal("315.00"))
        order_item = order.items.first()
        self.assertEqual(order_item.price_at_order, Decimal("300.00"))

    def test_historical_price_preservation(self):
        session = self.client.session
        session["cart"] = {
            str(self.item_1.id): {"quantity": 1}
        }
        session.save()

        payload = {
            "customer_name": "Jane Doe",
            "customer_phone": "9876543210",
            "table_number": 4
        }
        self.client.post(reverse("restaurant:checkout"), payload)
        order = Order.objects.first()
        order_item = order.items.first()
        self.assertEqual(order_item.price_at_order, Decimal("250.00"))

        # Update MenuItem price in DB
        self.item_1.price = Decimal("400.00")
        self.item_1.save()

        # Fetch OrderItem again, it must preserve the original order price (250.00)
        order_item_refresh = OrderItem.objects.get(id=order_item.id)
        self.assertEqual(order_item_refresh.price_at_order, Decimal("250.00"))

    def test_revalidation_removes_unavailable_items(self):
        session = self.client.session
        session["cart"] = {
            str(self.item_1.id): {"quantity": 2},
            str(self.item_unavailable.id): {"quantity": 1}  # Unavailable
        }
        session.save()

        payload = {
            "customer_name": "Jane Doe",
            "customer_phone": "9876543210",
            "table_number": 4
        }
        self.client.post(reverse("restaurant:checkout"), payload)
        
        order = Order.objects.first()
        order_items = list(order.items.all())
        # Only item_1 should be in order, item_unavailable is omitted
        self.assertEqual(len(order_items), 1)
        self.assertEqual(order_items[0].menu_item, self.item_1)
        # Total amount uses only item_1: 250.00 * 2 = 500.00 + 25.00 tax = 525.00
        self.assertEqual(order.total_amount, Decimal("525.00"))

    def test_revalidation_out_of_bounds_quantities(self):
        session = self.client.session
        session["cart"] = {
            str(self.item_1.id): {"quantity": 25},  # Exceeds max 20 -> capped at 20
            str(self.item_2.id): {"quantity": 0}    # Invalid positive -> discarded
        }
        session.save()

        payload = {
            "customer_name": "Jane Doe",
            "customer_phone": "9876543210",
            "table_number": 4
        }
        self.client.post(reverse("restaurant:checkout"), payload)
        
        order = Order.objects.first()
        order_items = list(order.items.all())
        # Only item_1 should be in order with quantity 20
        self.assertEqual(len(order_items), 1)
        self.assertEqual(order_items[0].menu_item, self.item_1)
        self.assertEqual(order_items[0].quantity, 20)

    def test_transaction_rollback(self):
        from unittest.mock import patch
        
        session = self.client.session
        session["cart"] = {str(self.item_1.id): {"quantity": 2}}
        session.save()
        
        initial_order_count = Order.objects.count()
        initial_order_item_count = OrderItem.objects.count()
        
        payload = {
            "customer_name": "Rollback Test",
            "customer_phone": "9876543210",
            "table_number": 5
        }
        
        # Force OrderItem bulk_create operation to crash to check transaction safety
        with patch("restaurant.models.OrderItem.objects.bulk_create", side_effect=Exception("Simulated db write failure")):
            response = self.client.post(reverse("restaurant:checkout"), payload)
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, "restaurant/checkout.html")
            
        # Verify rollback - no Order or OrderItems should be saved
        self.assertEqual(Order.objects.count(), initial_order_count)
        self.assertEqual(OrderItem.objects.count(), initial_order_item_count)
        
        # Verify the session cart was preserved so customer doesn't lose items
        self.assertEqual(self.client.session.get("cart"), {str(self.item_1.id): {"quantity": 2}})

    def test_order_success_page(self):
        order = Order.objects.create(
            customer_name="John Success",
            customer_phone="+919876543210",
            table_number=3,
            subtotal_amount=Decimal("250.00"),
            tax_amount=Decimal("12.50"),
            tax_rate=Decimal("0.0500"),
            total_amount=Decimal("262.50")
        )
        OrderItem.objects.create(
            order=order,
            menu_item=self.item_1,
            quantity=1,
            price_at_order=Decimal("250.00"),
            item_name_at_order="Chicken Biryani"
        )

        response = self.client.get(reverse("restaurant:order_success", args=[order.tracking_token]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "restaurant/order_success.html")
        self.assertContains(response, "Order Confirmed!")
        self.assertContains(response, f"Order Number: #{order.id}")
        self.assertContains(response, "John Success")
        self.assertContains(response, "Table #3")
        self.assertContains(response, "₹250.00")  # Historical price display

    def test_csrf_enforcement_checkout(self):
        from django.test import Client as TestClient
        csrf_client = TestClient(enforce_csrf_checks=True)
        
        session = csrf_client.session
        session["cart"] = {str(self.item_1.id): {"quantity": 1}}
        session.save()

        payload = {
            "customer_name": "CSRF Hacker",
            "customer_phone": "9876543210",
            "table_number": 4
        }
        # POST without CSRF token must fail with 403 Forbidden
        response = csrf_client.post(reverse("restaurant:checkout"), payload)
        self.assertEqual(response.status_code, 403)
