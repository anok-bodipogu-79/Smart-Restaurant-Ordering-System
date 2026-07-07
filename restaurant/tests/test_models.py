from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from restaurant.models import Category, MenuItem, Order, OrderItem


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

    def test_menu_item_deletion_preserves_order_item(self):
        category = Category.objects.create(name="Drinks")
        item = MenuItem.objects.create(
            category=category,
            name="Lemonade",
            price=Decimal("50.00")
        )
        order = Order.objects.create(
            customer_name="Bob",
            customer_phone="7777777777",
            subtotal_amount=Decimal("50.00"),
            tax_amount=Decimal("2.50"),
            tax_rate=Decimal("0.0500"),
            total_amount=Decimal("52.50")
        )
        order_item = OrderItem.objects.create(
            order=order,
            menu_item=item,
            quantity=1,
            price_at_order=Decimal("50.00"),
            item_name_at_order=item.name
        )
        
        # Deleting MenuItem should set ForeignKey to NULL but keep OrderItem & name/price intact
        item.delete()
        order_item.refresh_from_db()
        self.assertIsNone(order_item.menu_item)
        self.assertEqual(order_item.item_name_at_order, "Lemonade")
        self.assertEqual(order_item.price_at_order, Decimal("50.00"))
        self.assertEqual(str(order_item), "1x Lemonade")

    def test_financial_snapshot_consistency(self):
        order = Order.objects.create(
            customer_name="Charlie",
            customer_phone="6666666666",
            subtotal_amount=Decimal("100.00"),
            tax_amount=Decimal("5.00"),
            tax_rate=Decimal("0.0500"),
            total_amount=Decimal("105.00")
        )
        self.assertEqual(order.subtotal_amount + order.tax_amount, order.total_amount)
