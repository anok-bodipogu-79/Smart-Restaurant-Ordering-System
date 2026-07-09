from decimal import Decimal
import json
from django.test import TestCase, Client
from django.urls import reverse
from restaurant.models import Category, MenuItem, Order, OrderItem

class PhaseAModelTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Starters", icon="bi-star")
        self.item = MenuItem.objects.create(
            category=self.category,
            name="Samosa",
            description="Crispy pastry",
            price=Decimal("50.00"),
            is_vegetarian=True,
            is_spicy=True,
            is_available=True
        )
        self.order = Order.objects.create(
            customer_name="Alice",
            customer_phone="+919876543210",
            table_number=5,
            subtotal_amount=Decimal("50.00"),
            tax_amount=Decimal("2.50"),
            total_amount=Decimal("52.50")
        )

    def test_order_item_default_instructions(self):
        order_item = OrderItem.objects.create(
            order=self.order,
            menu_item=self.item,
            quantity=1,
            price_at_order=self.item.price,
            item_name_at_order=self.item.name,
            category_name_at_order=self.category.name
        )
        self.assertEqual(order_item.special_instructions, "")

    def test_order_item_custom_instructions(self):
        order_item = OrderItem.objects.create(
            order=self.order,
            menu_item=self.item,
            quantity=1,
            price_at_order=self.item.price,
            item_name_at_order=self.item.name,
            category_name_at_order=self.category.name,
            special_instructions="Extra crispy, less spicy"
        )
        self.assertEqual(order_item.special_instructions, "Extra crispy, less spicy")


class PhaseAMenuPopularityTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Mains", icon="bi-egg")
        # Create 5 available menu items
        self.items = []
        for i in range(1, 6):
            self.items.append(
                MenuItem.objects.create(
                    category=self.category,
                    name=f"Dish {i}",
                    description="Delicious dish",
                    price=Decimal("100.00"),
                    is_vegetarian=True,
                    is_available=True
                )
            )

    def test_popular_items_calculation(self):
        # Create a completed order with Dish 1 (qty 10), Dish 2 (qty 5), Dish 3 (qty 2)
        completed_order = Order.objects.create(
            customer_name="Bob",
            customer_phone="+919876543210",
            status="COMPLETED",
            subtotal_amount=Decimal("1700.00"),
            total_amount=Decimal("1785.00")
        )
        OrderItem.objects.create(order=completed_order, menu_item=self.items[0], quantity=10, price_at_order=Decimal("100.00"), item_name_at_order="Dish 1")
        OrderItem.objects.create(order=completed_order, menu_item=self.items[1], quantity=5, price_at_order=Decimal("100.00"), item_name_at_order="Dish 2")
        OrderItem.objects.create(order=completed_order, menu_item=self.items[2], quantity=2, price_at_order=Decimal("100.00"), item_name_at_order="Dish 3")

        # Create an incomplete (RECEIVED) order with Dish 4 (qty 20) -> should NOT count towards popularity
        received_order = Order.objects.create(
            customer_name="Charlie",
            customer_phone="+919876543210",
            status="RECEIVED",
            subtotal_amount=Decimal("2000.00"),
            total_amount=Decimal("2100.00")
        )
        OrderItem.objects.create(order=received_order, menu_item=self.items[3], quantity=20, price_at_order=Decimal("100.00"), item_name_at_order="Dish 4")

        # Call menu view and get popular ids from context
        client = Client()
        response = client.get(reverse("restaurant:menu"))
        self.assertEqual(response.status_code, 200)
        
        popular_ids = response.context["popular_ids"]
        # Top 3 should be Dish 1, Dish 2, Dish 3
        self.assertEqual(len(popular_ids), 3)
        self.assertIn(self.items[0].id, popular_ids)
        self.assertIn(self.items[1].id, popular_ids)
        self.assertIn(self.items[2].id, popular_ids)
        self.assertNotIn(self.items[3].id, popular_ids) # Dish 4 is not completed

    def test_popular_items_tie_breaking(self):
        # Create a completed order where Dish 2 (qty 5) and Dish 3 (qty 5) tie
        completed_order = Order.objects.create(
            customer_name="Bob",
            customer_phone="+919876543210",
            status="COMPLETED"
        )
        # Dish 2 (qty 5)
        OrderItem.objects.create(order=completed_order, menu_item=self.items[1], quantity=5, price_at_order=Decimal("100.00"))
        # Dish 3 (qty 5)
        OrderItem.objects.create(order=completed_order, menu_item=self.items[2], quantity=5, price_at_order=Decimal("100.00"))
        # Dish 1 (qty 10)
        OrderItem.objects.create(order=completed_order, menu_item=self.items[0], quantity=10, price_at_order=Decimal("100.00"))

        client = Client()
        response = client.get(reverse("restaurant:menu"))
        popular_ids = response.context["popular_ids"]

        # Expected top 3 ordered by completed quantity desc, then MenuItem ID asc:
        # 1. Dish 1 (qty 10)
        # 2. Dish 2 (qty 5, lower ID)
        # 3. Dish 3 (qty 5, higher ID)
        self.assertEqual(popular_ids, [self.items[0].id, self.items[1].id, self.items[2].id])

    def test_popular_items_zero_sales(self):
        # No completed orders
        client = Client()
        response = client.get(reverse("restaurant:menu"))
        popular_ids = response.context["popular_ids"]
        self.assertEqual(popular_ids, [])


class PhaseACartSyncTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Desserts", icon="bi-cake")
        self.item = MenuItem.objects.create(
            category=self.category,
            name="Ice Cream",
            price=Decimal("120.00"),
            is_available=True
        )
        self.client = Client()

    def test_cart_sync_valid_instructions(self):
        payload = {
            "items": [
                {
                    "id": self.item.id,
                    "quantity": 2,
                    "special_instructions": "No cherry, extra syrup"
                }
            ]
        }
        response = self.client.post(
            reverse("restaurant:cart_sync"),
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["items"][0]["special_instructions"], "No cherry, extra syrup")
        
        # Verify stored in session
        session_cart = self.client.session.get("cart")
        self.assertEqual(session_cart[str(self.item.id)]["special_instructions"], "No cherry, extra syrup")

    def test_cart_sync_oversized_instructions(self):
        long_instr = "A" * 300
        payload = {
            "items": [
                {
                    "id": self.item.id,
                    "quantity": 1,
                    "special_instructions": long_instr
                }
            ]
        }
        response = self.client.post(
            reverse("restaurant:cart_sync"),
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["items"][0]["special_instructions"]), 250)
        self.assertEqual(data["items"][0]["special_instructions"], "A" * 250)

    def test_cart_sync_missing_instructions(self):
        payload = {
            "items": [
                {
                    "id": self.item.id,
                    "quantity": 1
                }
            ]
        }
        response = self.client.post(
            reverse("restaurant:cart_sync"),
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["items"][0]["special_instructions"], "")


class PhaseACheckoutTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Drinks", icon="bi-cup")
        self.item = MenuItem.objects.create(
            category=self.category,
            name="Mango Lassi",
            price=Decimal("80.00"),
            is_available=True
        )
        self.client = Client()

    def test_checkout_saves_instructions(self):
        # 1. Sync cart with instructions
        payload = {
            "items": [
                {
                    "id": self.item.id,
                    "quantity": 2,
                    "special_instructions": "Less sugar, no ice"
                }
            ]
        }
        self.client.post(
            reverse("restaurant:cart_sync"),
            data=json.dumps(payload),
            content_type="application/json"
        )

        # 2. Post checkout form
        form_data = {
            "customer_name": "Dave Miller",
            "customer_phone": "9876543210",  # Will normalize to +919876543210
            "table_number": 4
        }
        response = self.client.post(reverse("restaurant:checkout"), data=form_data)
        
        # Check order exists
        order = Order.objects.filter(customer_name="Dave Miller").first()
        self.assertIsNotNone(order)
        
        # Check order item instructions are saved correctly
        order_item = order.items.filter(menu_item=self.item).first()
        self.assertIsNotNone(order_item)
        self.assertEqual(order_item.special_instructions, "Less sugar, no ice")
