import json
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from restaurant.models import Category, MenuItem


class CartSyncViewTest(TestCase):
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
            name="Sold Out Ice Cream",
            price=Decimal("80.00"),
            is_available=False
        )

    def test_cart_sync_url_resolves(self):
        url = reverse("restaurant:cart_sync")
        self.assertEqual(url, "/cart/sync/")

    def test_sync_post_only(self):
        # GET is not allowed, returns 405
        response = self.client.get(reverse("restaurant:cart_sync"))
        self.assertEqual(response.status_code, 405)

        # POST is allowed
        response = self.client.post(
            reverse("restaurant:cart_sync"),
            data=json.dumps({"items": []}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)

    def test_malformed_json(self):
        # Invalid JSON string
        response = self.client.post(
            reverse("restaurant:cart_sync"),
            data="not-a-json",
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("error", data)

    def test_missing_items_field(self):
        # Missing items field
        response = self.client.post(
            reverse("restaurant:cart_sync"),
            data=json.dumps({"other_field": []}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_invalid_items_type(self):
        # Items field is not a list
        response = self.client.post(
            reverse("restaurant:cart_sync"),
            data=json.dumps({"items": "not-a-list"}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_empty_cart_sync(self):
        response = self.client.post(
            reverse("restaurant:cart_sync"),
            data=json.dumps({"items": []}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["items"], [])
        
        # Verify session cart is empty
        self.assertEqual(self.client.session.get("cart"), {})

    def test_valid_sync(self):
        payload = {
            "items": [
                {"id": str(self.item_1.id), "quantity": 2},
                {"id": str(self.item_2.id), "quantity": 3}
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
        
        # Output items should contain db prices and preserved order
        self.assertEqual(len(data["items"]), 2)
        self.assertEqual(data["items"][0]["id"], str(self.item_1.id))
        self.assertEqual(data["items"][0]["price"], "250.00")
        self.assertEqual(data["items"][0]["quantity"], 2)
        
        self.assertEqual(data["items"][1]["id"], str(self.item_2.id))
        self.assertEqual(data["items"][1]["price"], "110.00")
        self.assertEqual(data["items"][1]["quantity"], 3)

        # Verify session storage
        session_cart = self.client.session.get("cart")
        self.assertIsNotNone(session_cart)
        self.assertEqual(session_cart[str(self.item_1.id)]["quantity"], 2)
        self.assertEqual(session_cart[str(self.item_2.id)]["quantity"], 3)
        # Ensure no browser names or prices are stored in session
        self.assertNotIn("name", session_cart[str(self.item_1.id)])
        self.assertNotIn("price", session_cart[str(self.item_1.id)])

    def test_nonexistent_and_unavailable_items(self):
        payload = {
            "items": [
                {"id": str(self.item_1.id), "quantity": 1},
                {"id": "999999", "quantity": 1},  # Nonexistent
                {"id": str(self.item_unavailable.id), "quantity": 1}  # Unavailable
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
        
        # Only the valid available item should be returned and in session
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["items"][0]["id"], str(self.item_1.id))
        
        session_cart = self.client.session.get("cart")
        self.assertEqual(list(session_cart.keys()), [str(self.item_1.id)])

    def test_database_price_authority(self):
        # Client tries to manipulate price or name in payload
        payload = {
            "items": [
                {"id": str(self.item_1.id), "quantity": 2, "price": "1.00", "name": "Fake Name"}
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
        
        # Verify returned data uses authoritative database values
        self.assertEqual(data["items"][0]["name"], "Chicken Biryani")
        self.assertEqual(data["items"][0]["price"], "250.00")
        
        session_cart = self.client.session.get("cart")
        # Session must not store name or price
        self.assertNotIn("name", session_cart[str(self.item_1.id)])
        self.assertNotIn("price", session_cart[str(self.item_1.id)])

    def test_quantity_min_max(self):
        payload = {
            "items": [
                {"id": str(self.item_1.id), "quantity": 0},   # Invalid (non-positive) -> ignored/discarded
                {"id": str(self.item_2.id), "quantity": -5},  # Invalid (negative) -> ignored/discarded
                {"id": str(self.item_2.id), "quantity": 25}   # Valid but above 20 -> capped at 20
            ]
        }
        response = self.client.post(
            reverse("restaurant:cart_sync"),
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Only item_2 should be in cart with quantity 20
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["items"][0]["id"], str(self.item_2.id))
        self.assertEqual(data["items"][0]["quantity"], 20)

        session_cart = self.client.session.get("cart")
        self.assertNotIn(str(self.item_1.id), session_cart)
        self.assertEqual(session_cart[str(self.item_2.id)]["quantity"], 20)

    def test_boolean_quantity_rejection(self):
        payload = {
            "items": [
                {"id": str(self.item_1.id), "quantity": True},  # Boolean -> rejected/discarded
                {"id": str(self.item_2.id), "quantity": False}  # Boolean -> rejected/discarded
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
        self.assertEqual(data["items"], [])

        session_cart = self.client.session.get("cart")
        self.assertEqual(session_cart, {})

    def test_duplicate_item_ids_merge(self):
        payload = {
            "items": [
                {"id": str(self.item_1.id), "quantity": 5},
                {"id": str(self.item_1.id), "quantity": 10},  # Merges to 15
                {"id": str(self.item_2.id), "quantity": 15},
                {"id": str(self.item_2.id), "quantity": 10}   # Merges to 25 -> caps at 20
            ]
        }
        response = self.client.post(
            reverse("restaurant:cart_sync"),
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(len(data["items"]), 2)
        
        # Verify item 1 has quantity 15
        self.assertEqual(data["items"][0]["id"], str(self.item_1.id))
        self.assertEqual(data["items"][0]["quantity"], 15)
        
        # Verify item 2 has quantity 20 (capped)
        self.assertEqual(data["items"][1]["id"], str(self.item_2.id))
        self.assertEqual(data["items"][1]["quantity"], 20)

        session_cart = self.client.session.get("cart")
        self.assertEqual(session_cart[str(self.item_1.id)]["quantity"], 15)
        self.assertEqual(session_cart[str(self.item_2.id)]["quantity"], 20)

    def test_session_replacement(self):
        # First sync contains item_1
        payload_1 = {
            "items": [
                {"id": str(self.item_1.id), "quantity": 2}
            ]
        }
        response = self.client.post(
            reverse("restaurant:cart_sync"),
            data=json.dumps(payload_1),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(str(self.item_1.id), self.client.session.get("cart"))

        # Second sync contains item_2 only
        payload_2 = {
            "items": [
                {"id": str(self.item_2.id), "quantity": 3}
            ]
        }
        response = self.client.post(
            reverse("restaurant:cart_sync"),
            data=json.dumps(payload_2),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        
        # Verify session contains ONLY item_2 (completely replaced, not accumulated)
        session_cart = self.client.session.get("cart")
        self.assertNotIn(str(self.item_1.id), session_cart)
        self.assertEqual(session_cart[str(self.item_2.id)]["quantity"], 3)

    def test_csrf_enforcement(self):
        from django.test import Client as TestClient
        # Create client enforcing CSRF checks
        csrf_client = TestClient(enforce_csrf_checks=True)
        payload = {
            "items": [{"id": str(self.item_1.id), "quantity": 1}]
        }
        
        # POST without CSRF token should return 403 Forbidden
        response = csrf_client.post(
            reverse("restaurant:cart_sync"),
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 403)
