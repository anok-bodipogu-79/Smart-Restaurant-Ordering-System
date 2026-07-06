import json
from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.contrib import admin
from django.core.management import call_command
from django.urls import reverse
from restaurant.models import Category, MenuItem, Order, OrderItem
from restaurant.forms import CheckoutForm, OrderTrackingForm


class CategoryModelTest(TestCase):
    def test_category_creation_and_fields(self):
        category = Category.objects.create(name="Appetizers")
        self.assertEqual(category.name, "Appetizers")
        self.assertEqual(category.icon, "bi-journal")

    def test_category_str_representation(self):
        category = Category.objects.create(name="Main Course")
        self.assertEqual(str(category), "Main Course")

    def test_category_name_uniqueness(self):
        Category.objects.create(name="Desserts")
        with self.assertRaises((IntegrityError, ValidationError)):
            Category.objects.create(name="Desserts")

    def test_category_ordering(self):
        Category.objects.create(name="Desserts")
        Category.objects.create(name="Appetizers")
        Category.objects.create(name="Beverages")
        categories = list(Category.objects.all())
        self.assertEqual(categories[0].name, "Appetizers")
        self.assertEqual(categories[1].name, "Beverages")
        self.assertEqual(categories[2].name, "Desserts")


class MenuItemModelTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Main Course")

    def test_menu_item_creation_and_defaults(self):
        item = MenuItem.objects.create(
            category=self.category,
            name="Chicken Biryani",
            description="Classic chicken biryani",
            price=Decimal("250.00")
        )
        self.assertEqual(item.name, "Chicken Biryani")
        self.assertEqual(item.description, "Classic chicken biryani")
        self.assertEqual(item.price, Decimal("250.00"))
        self.assertFalse(item.is_vegetarian)
        self.assertFalse(item.is_spicy)
        self.assertTrue(item.is_available)
        self.assertEqual(item.image_url, "https://via.placeholder.com/300x200")

    def test_menu_item_str_representation(self):
        item = MenuItem.objects.create(
            category=self.category,
            name="Paneer Tikka",
            description="Spicy paneer tikka",
            price=Decimal("180.50")
        )
        self.assertEqual(str(item), "Paneer Tikka ($180.50)")

    def test_menu_item_price_validation(self):
        # Positive price should pass
        item = MenuItem(
            category=self.category,
            name="Valid Item",
            description="Desc",
            price=Decimal("0.01")
        )
        item.full_clean()  # should not raise exception

        # Zero price should fail
        item.price = Decimal("0.00")
        with self.assertRaises(ValidationError):
            item.full_clean()

        # Negative price should fail
        item.price = Decimal("-10.00")
        with self.assertRaises(ValidationError):
            item.full_clean()


class OrderModelTest(TestCase):
    def test_order_creation_and_defaults(self):
        order = Order.objects.create(
            customer_name="John Doe",
            customer_phone="9876543210"
        )
        self.assertEqual(order.customer_name, "John Doe")
        self.assertEqual(order.customer_phone, "9876543210")
        self.assertIsNone(order.table_number)
        self.assertEqual(order.total_amount, Decimal("0.00"))
        self.assertEqual(order.status, "RECEIVED")
        self.assertEqual(order.get_status_display(), "Order Received")
        self.assertIsNotNone(order.created_at)

    def test_order_str_representation(self):
        order = Order.objects.create(
            customer_name="Jane Doe",
            customer_phone="9123456789",
            table_number=5
        )
        self.assertEqual(str(order), f"Order #{order.id} by Jane Doe (Order Received)")

    def test_order_total_amount_validation(self):
        order = Order(
            customer_name="John",
            customer_phone="123",
            total_amount=Decimal("0.00")
        )
        order.full_clean()  # zero is allowed

        order.total_amount = Decimal("100.50")
        order.full_clean()  # positive is allowed

        order.total_amount = Decimal("-0.01")
        with self.assertRaises(ValidationError):
            order.full_clean()  # negative total not allowed

    def test_order_table_number_validation(self):
        order = Order(
            customer_name="John",
            customer_phone="123",
            table_number=0
        )
        # Table number 0 is not positive, should fail MinValueValidator(1)
        with self.assertRaises(ValidationError):
            order.full_clean()

        order.table_number = 1
        order.full_clean()  # should pass


class OrderItemModelTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Main Course")
        self.menu_item = MenuItem.objects.create(
            category=self.category,
            name="Chicken Biryani",
            description="Desc",
            price=Decimal("250.00")
        )
        self.order = Order.objects.create(
            customer_name="John Doe",
            customer_phone="9876543210"
        )

    def test_order_item_creation_and_defaults(self):
        order_item = OrderItem.objects.create(
            order=self.order,
            menu_item=self.menu_item,
            price_at_order=Decimal("250.00")
        )
        self.assertEqual(order_item.order, self.order)
        self.assertEqual(order_item.menu_item, self.menu_item)
        self.assertEqual(order_item.quantity, 1)
        self.assertEqual(order_item.price_at_order, Decimal("250.00"))

    def test_order_item_str_representation(self):
        order_item = OrderItem.objects.create(
            order=self.order,
            menu_item=self.menu_item,
            quantity=2,
            price_at_order=Decimal("250.00")
        )
        self.assertEqual(str(order_item), "2x Chicken Biryani")

    def test_order_item_quantity_validation(self):
        # Quantity 1 is valid
        item = OrderItem(order=self.order, menu_item=self.menu_item, quantity=1, price_at_order=Decimal("100.00"))
        item.full_clean()

        # Quantity 20 is valid
        item.quantity = 20
        item.full_clean()

        # Quantity 0 is invalid
        item.quantity = 0
        with self.assertRaises(ValidationError):
            item.full_clean()

        # Quantity 21 is invalid
        item.quantity = 21
        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_order_item_price_validation(self):
        item = OrderItem(order=self.order, menu_item=self.menu_item, quantity=1, price_at_order=Decimal("0.01"))
        item.full_clean()

        # Zero is invalid
        item.price_at_order = Decimal("0.00")
        with self.assertRaises(ValidationError):
            item.full_clean()

        # Negative is invalid
        item.price_at_order = Decimal("-5.00")
        with self.assertRaises(ValidationError):
            item.full_clean()


class ModelRelationshipAndDataIntegrityTest(TestCase):
    def test_historical_price_preservation(self):
        category = Category.objects.create(name="Beverages")
        item = MenuItem.objects.create(
            category=category,
            name="Cold Coffee",
            description="Cold coffee",
            price=Decimal("120.00")
        )
        order = Order.objects.create(
            customer_name="Coffee Lover",
            customer_phone="9999999999"
        )
        order_item = OrderItem.objects.create(
            order=order,
            menu_item=item,
            quantity=1,
            price_at_order=item.price
        )
        
        # Verify initial price
        self.assertEqual(order_item.price_at_order, Decimal("120.00"))

        # Update MenuItem price
        item.price = Decimal("150.00")
        item.save()

        # Refresh OrderItem and verify price remains unchanged
        order_item.refresh_from_db()
        self.assertEqual(order_item.price_at_order, Decimal("120.00"))

    def test_category_cascade_deletion(self):
        category = Category.objects.create(name="Desserts")
        item = MenuItem.objects.create(
            category=category,
            name="Gulab Jamun",
            description="Warm gulab jamun",
            price=Decimal("80.00")
        )
        
        # Deleting category should cascade and delete menu item
        category.delete()
        self.assertFalse(MenuItem.objects.filter(id=item.id).exists())

    def test_order_cascade_deletion(self):
        category = Category.objects.create(name="Appetizers")
        item = MenuItem.objects.create(
            category=category,
            name="Spring Rolls",
            description="Veg spring rolls",
            price=Decimal("110.00")
        )
        order = Order.objects.create(
            customer_name="Alice",
            customer_phone="8888888888"
        )
        order_item = OrderItem.objects.create(
            order=order,
            menu_item=item,
            quantity=1,
            price_at_order=item.price
        )

        # Deleting order should cascade and delete order item
        order.delete()
        self.assertFalse(OrderItem.objects.filter(id=order_item.id).exists())
        # The MenuItem itself should still exist
        self.assertTrue(MenuItem.objects.filter(id=item.id).exists())


class AdminRegistrationTest(TestCase):
    def test_admin_registration(self):
        self.assertTrue(admin.site.is_registered(Category))
        self.assertTrue(admin.site.is_registered(MenuItem))
        self.assertTrue(admin.site.is_registered(Order))
        self.assertTrue(admin.site.is_registered(OrderItem))


class SeedMenuCommandTest(TestCase):
    def test_seed_menu_execution_and_accuracy(self):
        # Database should be empty initially (except what is created in TestCase structure, which is empty by default)
        self.assertEqual(Category.objects.count(), 0)
        self.assertEqual(MenuItem.objects.count(), 0)

        # Run command
        call_command("seed_menu")

        # Verify category and item counts
        self.assertEqual(Category.objects.count(), 4)
        self.assertEqual(MenuItem.objects.count(), 16)

        # Verify Appetizers
        appetizers = Category.objects.get(name="Appetizers")
        self.assertEqual(appetizers.icon, "bi-egg-fried")
        paneer_tikka = MenuItem.objects.get(name="Paneer Tikka", category=appetizers)
        self.assertTrue(paneer_tikka.is_vegetarian)
        self.assertTrue(paneer_tikka.is_spicy)
        self.assertEqual(paneer_tikka.price, Decimal("220.00"))

        # Verify Main Course
        main_course = Category.objects.get(name="Main Course")
        self.assertEqual(main_course.icon, "bi-fire")
        biryani = MenuItem.objects.get(name="Chicken Biryani", category=main_course)
        self.assertFalse(biryani.is_vegetarian)
        self.assertTrue(biryani.is_spicy)
        self.assertEqual(biryani.price, Decimal("350.00"))

        # Verify Desserts
        desserts = Category.objects.get(name="Desserts")
        self.assertEqual(desserts.icon, "bi-cake")
        gulab_jamun = MenuItem.objects.get(name="Gulab Jamun", category=desserts)
        self.assertTrue(gulab_jamun.is_vegetarian)
        self.assertFalse(gulab_jamun.is_spicy)
        self.assertEqual(gulab_jamun.price, Decimal("90.00"))

        # Verify Beverages
        beverages = Category.objects.get(name="Beverages")
        self.assertEqual(beverages.icon, "bi-cup-straw")
        cold_coffee = MenuItem.objects.get(name="Cold Coffee", category=beverages)
        self.assertTrue(cold_coffee.is_vegetarian)
        self.assertFalse(cold_coffee.is_spicy)
        self.assertEqual(cold_coffee.price, Decimal("110.00"))

    def test_seed_menu_idempotency(self):
        # Run command once
        call_command("seed_menu")
        cat_count_1 = Category.objects.count()
        item_count_1 = MenuItem.objects.count()

        # Run command twice
        call_command("seed_menu")
        cat_count_2 = Category.objects.count()
        item_count_2 = MenuItem.objects.count()

        # Counts must remain identical
        self.assertEqual(cat_count_1, cat_count_2)
        self.assertEqual(item_count_1, item_count_2)
        self.assertEqual(cat_count_1, 4)
        self.assertEqual(item_count_1, 16)

    def test_seed_menu_preserves_existing_data(self):
        # Create unrelated data
        specials_category = Category.objects.create(name="Specials", icon="bi-star")
        unrelated_item = MenuItem.objects.create(
            category=specials_category,
            name="Chef Special Kebab",
            description="Special kebab",
            price=Decimal("400.00")
        )

        # Run seed command
        call_command("seed_menu")

        # Verify seed data exists along with unrelated data
        self.assertEqual(Category.objects.count(), 5)  # 4 seeded + Specials
        self.assertEqual(MenuItem.objects.count(), 17)  # 16 seeded + Chef Special Kebab
        self.assertTrue(Category.objects.filter(name="Specials").exists())
        self.assertTrue(MenuItem.objects.filter(name="Chef Special Kebab").exists())


class MenuViewTest(TestCase):
    def setUp(self):
        self.cat_appetizers = Category.objects.create(name="Appetizers", icon="bi-egg-fried")
        self.cat_mains = Category.objects.create(name="Main Course", icon="bi-fire")
        
        self.item_veg = MenuItem.objects.create(
            category=self.cat_appetizers,
            name="Paneer Tikka",
            description="Marinated paneer chunks",
            price=Decimal("220.00"),
            is_vegetarian=True,
            is_spicy=True,
            is_available=True
        )
        self.item_nonveg_unavailable = MenuItem.objects.create(
            category=self.cat_mains,
            name="Butter Chicken",
            description="Creamy tomato gravy chicken",
            price=Decimal("380.00"),
            is_vegetarian=False,
            is_spicy=False,
            is_available=False
        )

    def test_menu_url_resolves(self):
        url = reverse("restaurant:menu")
        self.assertEqual(url, "/")

    def test_menu_page_status_and_template(self):
        response = self.client.get(reverse("restaurant:menu"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "restaurant/menu.html")

    def test_menu_context_data(self):
        response = self.client.get(reverse("restaurant:menu"))
        self.assertIn("menu_items", response.context)
        self.assertIn("categories", response.context)
        self.assertEqual(len(response.context["categories"]), 2)
        self.assertEqual(len(response.context["menu_items"]), 2)

    def test_menu_item_display(self):
        response = self.client.get(reverse("restaurant:menu"))
        # Verify text elements are rendered
        self.assertContains(response, "Paneer Tikka")
        self.assertContains(response, "Marinated paneer chunks")
        self.assertContains(response, "₹220.00")
        self.assertContains(response, "Appetizers")

    def test_multiple_category_display(self):
        response = self.client.get(reverse("restaurant:menu"))
        # In the default unfiltered state, items from all categories appear
        self.assertContains(response, "Paneer Tikka")
        self.assertContains(response, "Butter Chicken")

    def test_category_filtering(self):
        # Filter for Appetizers
        response = self.client.get(reverse("restaurant:menu"), {"category": self.cat_appetizers.id})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Paneer Tikka")
        self.assertNotContains(response, "Butter Chicken")

        # Filter for Mains
        response = self.client.get(reverse("restaurant:menu"), {"category": self.cat_mains.id})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Butter Chicken")
        self.assertNotContains(response, "Paneer Tikka")

    def test_invalid_category_filtering(self):
        # Query parameter category is an invalid string
        response = self.client.get(reverse("restaurant:menu"), {"category": "abc"})
        self.assertEqual(response.status_code, 200)
        # Should gracefully fall back to showing all items
        self.assertContains(response, "Paneer Tikka")
        self.assertContains(response, "Butter Chicken")

        # Query parameter is a nonexistent category ID
        response = self.client.get(reverse("restaurant:menu"), {"category": 999999})
        self.assertEqual(response.status_code, 200)
        # Fall back to showing all items
        self.assertContains(response, "Paneer Tikka")
        self.assertContains(response, "Butter Chicken")

    def test_veg_badge_display(self):
        response = self.client.get(reverse("restaurant:menu"))
        # Paneer Tikka is vegetarian -> should render Veg badge
        self.assertContains(response, "Veg")
        # Butter Chicken is non-vegetarian -> should render Non-Veg badge
        self.assertContains(response, "Non-Veg")

    def test_spicy_badge_display(self):
        response = self.client.get(reverse("restaurant:menu"))
        # Paneer Tikka is spicy -> should render Spicy badge
        self.assertContains(response, "Spicy")

    def test_item_availability_behavior(self):
        response = self.client.get(reverse("restaurant:menu"))
        
        # Available item: should have "Add to Cart" button UI with data attributes
        self.assertContains(response, 'data-item-id="' + str(self.item_veg.id) + '"')
        self.assertContains(response, 'data-item-name="Paneer Tikka"')
        self.assertContains(response, 'data-item-price="220.00"')
        
        # Unavailable item: should show Sold Out overlay and disabled button
        self.assertContains(response, "Sold Out")
        self.assertContains(response, "Unavailable")
        # The add button for this item should not have data-item-id attribute
        self.assertNotContains(response, 'data-item-id="' + str(self.item_nonveg_unavailable.id) + '"')

    def test_empty_menu_state(self):
        # Empty all items in DB
        MenuItem.objects.all().delete()
        response = self.client.get(reverse("restaurant:menu"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No Menu Items Found")
        self.assertContains(response, "No items are currently available in this category. Please check back later!")

    def test_base_template_structure(self):
        response = self.client.get(reverse("restaurant:menu"))
        # Navigation Brand check
        self.assertContains(response, "SmartDine")
        # Cart indicator check
        self.assertContains(response, 'id="cart-count"')
        # Custom CSS inclusion check
        self.assertContains(response, "/static/restaurant/css/style.css")
        # Custom JS inclusion check
        self.assertContains(response, "/static/restaurant/js/cart.js")
        # Navbar cart link check
        self.assertContains(response, 'href="' + reverse("restaurant:cart") + '"')


class CartViewTest(TestCase):
    def test_cart_url_resolves(self):
        url = reverse("restaurant:cart")
        self.assertEqual(url, "/cart/")

    def test_cart_page_status_and_template(self):
        response = self.client.get(reverse("restaurant:cart"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "restaurant/cart.html")

    def test_cart_page_required_elements(self):
        response = self.client.get(reverse("restaurant:cart"))
        
        # Verify required container IDs and element hook handles
        self.assertContains(response, 'id="cart-items"')
        self.assertContains(response, 'id="empty-cart"')
        self.assertContains(response, 'id="cart-summary"')
        self.assertContains(response, 'id="cart-subtotal"')
        self.assertContains(response, 'id="cart-tax"')
        self.assertContains(response, 'id="cart-total"')
        self.assertContains(response, 'id="clear-cart-btn"')
        self.assertContains(response, 'id="checkout-btn"')


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
        # Note: duplicate ID for item_2 in payload is resolved in sequence. 
        # If item_2: -5 is discarded first, then item_2: 25 is added, quantity should cap at 20.
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


class CheckoutFormTest(TestCase):
    def test_form_valid_data(self):
        form = CheckoutForm(data={
            "customer_name": "John Doe",
            "customer_phone": "9876543210",
            "table_number": 5
        })
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["customer_name"], "John Doe")
        self.assertEqual(form.cleaned_data["customer_phone"], "+919876543210")
        self.assertEqual(form.cleaned_data["table_number"], 5)

    def test_form_whitespace_only_name(self):
        form = CheckoutForm(data={
            "customer_name": "   ",
            "customer_phone": "9876543210",
            "table_number": 5
        })
        self.assertFalse(form.is_valid())
        self.assertIn("customer_name", form.errors)

    def test_form_short_name(self):
        form = CheckoutForm(data={
            "customer_name": "A",
            "customer_phone": "9876543210",
            "table_number": 5
        })
        self.assertFalse(form.is_valid())
        self.assertIn("customer_name", form.errors)

    def test_form_invalid_phone(self):
        # Alphabetic characters
        form = CheckoutForm(data={
            "customer_name": "John Doe",
            "customer_phone": "987abc3210",
            "table_number": 5
        })
        self.assertFalse(form.is_valid())
        self.assertIn("customer_phone", form.errors)

        # Too short
        form = CheckoutForm(data={
            "customer_name": "John Doe",
            "customer_phone": "98765",
            "table_number": 5
        })
        self.assertFalse(form.is_valid())

        # Too long
        form = CheckoutForm(data={
            "customer_name": "John Doe",
            "customer_phone": "987654321012345",
            "table_number": 5
        })
        self.assertFalse(form.is_valid())

    def test_form_table_number_bounds(self):
        # Blank table number is valid (None)
        form = CheckoutForm(data={
            "customer_name": "John Doe",
            "customer_phone": "9876543210",
            "table_number": ""
        })
        self.assertTrue(form.is_valid())
        self.assertIsNone(form.cleaned_data["table_number"])

        # Negative is invalid
        form = CheckoutForm(data={
            "customer_name": "John Doe",
            "customer_phone": "9876543210",
            "table_number": -1
        })
        self.assertFalse(form.is_valid())

        # Zero is invalid
        form = CheckoutForm(data={
            "customer_name": "John Doe",
            "customer_phone": "9876543210",
            "table_number": 0
        })
        self.assertFalse(form.is_valid())

        # Exceeding maximum 999 is invalid
        form = CheckoutForm(data={
            "customer_name": "John Doe",
            "customer_phone": "9876543210",
            "table_number": 1000
        })
        self.assertFalse(form.is_valid())


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
        self.assertRedirects(response, reverse("restaurant:order_success", args=[order.id]))
        
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
            total_amount=Decimal("262.50")
        )
        OrderItem.objects.create(
            order=order,
            menu_item=self.item_1,
            quantity=1,
            price_at_order=Decimal("250.00")
        )

        response = self.client.get(reverse("restaurant:order_success", args=[order.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "restaurant/order_success.html")
        self.assertContains(response, "Order Confirmed!")
        self.assertContains(response, f"Order ID: #{order.id}")
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


class KitchenViewsTest(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Create test users
        self.staff_user = User.objects.create_user(
            username="staff_chef",
            password="chefpassword123",
            is_staff=True
        )
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


class OrderTrackingTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        self.staff_user = User.objects.create_user(
            username="staff_chef_track",
            password="chefpassword123",
            is_staff=True
        )

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
            total_amount=Decimal("126.00"),
            status="RECEIVED"
        )
        self.order_item = OrderItem.objects.create(
            order=self.order,
            menu_item=self.menu_item,
            quantity=2,
            price_at_order=Decimal("60.00")
        )

    def test_tracking_form_valid(self):
        form = OrderTrackingForm(data={"order_id": 15})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["order_id"], 15)

    def test_tracking_form_invalid_negative_and_zero(self):
        form = OrderTrackingForm(data={"order_id": 0})
        self.assertFalse(form.is_valid())
        self.assertIn("order_id", form.errors)

        form = OrderTrackingForm(data={"order_id": -5})
        self.assertFalse(form.is_valid())
        self.assertIn("order_id", form.errors)

    def test_tracking_form_invalid_text_and_empty(self):
        form = OrderTrackingForm(data={"order_id": "abc"})
        self.assertFalse(form.is_valid())

        form = OrderTrackingForm(data={"order_id": ""})
        self.assertFalse(form.is_valid())

    def test_tracking_search_page_renders(self):
        response = self.client.get(reverse("restaurant:order_tracking"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "restaurant/order_tracking.html")
        self.assertContains(response, "Track Your Order")
        self.assertContains(response, "id_order_id")

    def test_valid_tracking_search_redirects(self):
        payload = {"order_id": self.order.id}
        response = self.client.post(reverse("restaurant:order_tracking"), payload)
        self.assertRedirects(response, reverse("restaurant:order_tracking_detail", args=[self.order.id]))

    def test_nonexistent_tracking_search_shows_error(self):
        payload = {"order_id": 9999}
        response = self.client.post(reverse("restaurant:order_tracking"), payload)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "restaurant/order_tracking.html")
        self.assertContains(response, "No order was found with that Order ID.")

    def test_invalid_tracking_search_shows_field_errors(self):
        payload = {"order_id": -10}
        response = self.client.post(reverse("restaurant:order_tracking"), payload)
        self.assertEqual(response.status_code, 200)
        # Form should complain about positive ID bounds
        self.assertContains(response, "Order ID must be a positive number.")

    def test_tracking_detail_page(self):
        response = self.client.get(reverse("restaurant:order_tracking_detail", args=[self.order.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "restaurant/order_tracking_detail.html")
        
        self.assertContains(response, f"Order #{self.order.id}")
        self.assertContains(response, "Lemon Tea")
        self.assertContains(response, "2")  # Quantity
        self.assertContains(response, "₹60.00")  # Price at order
        self.assertContains(response, "₹120.00")  # Line total
        self.assertContains(response, "₹126.00")  # Grand total
        
        # Privacy check: Customer phone should NOT be exposed publicly on tracking page
        self.assertNotContains(response, "9876543210")

    def test_tracking_detail_404(self):
        response = self.client.get(reverse("restaurant:order_tracking_detail", args=[9999]))
        self.assertEqual(response.status_code, 404)

    def test_historical_price_on_tracking_detail(self):
        # Alter current MenuItem price in database
        self.menu_item.price = Decimal("100.00")
        self.menu_item.save()

        response = self.client.get(reverse("restaurant:order_tracking_detail", args=[self.order.id]))
        self.assertEqual(response.status_code, 200)
        # Detail must reflect historical 60.00 price, not current 100.00
        self.assertContains(response, "₹60.00")
        self.assertNotContains(response, "₹100.00")

    def test_status_display_workflow_renders(self):
        # RECEIVED status
        response = self.client.get(reverse("restaurant:order_tracking_detail", args=[self.order.id]))
        self.assertContains(response, "Order Received")
        self.assertContains(response, 'data-current-status="RECEIVED"')

        # PREPARING status
        self.order.status = "PREPARING"
        self.order.save()
        response = self.client.get(reverse("restaurant:order_tracking_detail", args=[self.order.id]))
        self.assertContains(response, "In Kitchen - Preparing")
        self.assertContains(response, 'data-current-status="PREPARING"')

        # READY status
        self.order.status = "READY"
        self.order.save()
        response = self.client.get(reverse("restaurant:order_tracking_detail", args=[self.order.id]))
        self.assertContains(response, "Ready for Pickup / Delivery")
        self.assertContains(response, 'data-current-status="READY"')

        # COMPLETED status
        self.order.status = "COMPLETED"
        self.order.save()
        response = self.client.get(reverse("restaurant:order_tracking_detail", args=[self.order.id]))
        self.assertContains(response, "Completed")
        self.assertContains(response, 'data-current-status="COMPLETED"')

    def test_json_status_endpoint(self):
        response = self.client.get(reverse("restaurant:order_tracking_status", args=[self.order.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        
        data = json.loads(response.content)
        self.assertTrue(data["success"])
        self.assertEqual(data["order_id"], self.order.id)
        self.assertEqual(data["status"], "RECEIVED")
        self.assertEqual(data["status_display"], "Order Received")
        self.assertFalse(data["is_completed"])

        # Data minimization: ensure phone and name are NOT in JSON payload
        self.assertNotIn("customer_phone", data)
        self.assertNotIn("customer_name", data)

    def test_json_status_completed(self):
        self.order.status = "COMPLETED"
        self.order.save()
        
        response = self.client.get(reverse("restaurant:order_tracking_status", args=[self.order.id]))
        data = json.loads(response.content)
        self.assertTrue(data["is_completed"])
        self.assertEqual(data["status"], "COMPLETED")

    def test_json_status_404(self):
        response = self.client.get(reverse("restaurant:order_tracking_status", args=[9999]))
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.content)
        self.assertFalse(data["success"])
        self.assertEqual(data["error"], "Order not found.")

    def test_json_status_post_rejection(self):
        response = self.client.post(reverse("restaurant:order_tracking_status", args=[self.order.id]))
        self.assertEqual(response.status_code, 405)

    def test_order_success_page_has_track_order_link(self):
        response = self.client.get(reverse("restaurant:order_success", args=[self.order.id]))
        self.assertEqual(response.status_code, 200)
        # Must display Track Order button linking to detail page
        self.assertContains(response, reverse("restaurant:order_tracking_detail", args=[self.order.id]))

    def test_kitchen_to_tracking_integration(self):
        # 1. Initially RECEIVED
        response = self.client.get(reverse("restaurant:order_tracking_status", args=[self.order.id]))
        self.assertEqual(json.loads(response.content)["status"], "RECEIVED")

        # 2. Staff updates order using kitchen dashboard URL
        self.client.login(username="staff_chef_track", password="chefpassword123")
        self.client.post(
            reverse("restaurant:kitchen_order_status", args=[self.order.id]),
            {"status": "PREPARING"}
        )

        # 3. Customer tracking status reflects changes automatically
        response = self.client.get(reverse("restaurant:order_tracking_status", args=[self.order.id]))
        self.assertEqual(json.loads(response.content)["status"], "PREPARING")





