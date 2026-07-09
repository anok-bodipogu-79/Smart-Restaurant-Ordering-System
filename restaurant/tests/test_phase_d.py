from decimal import Decimal
from django.contrib.auth.models import User, Group
from django.test import TestCase
from django.urls import reverse
from restaurant.models import Order, OrderItem, Category, MenuItem

class PhaseDTests(TestCase):
    def setUp(self):
        # Create users & groups
        self.manager_group, _ = Group.objects.get_or_create(name="Managers")
        self.manager_user = User.objects.create_user(username="manager", password="password123")
        self.manager_user.groups.add(self.manager_group)
        
        self.category = Category.objects.create(name="Beverages", icon="bi-cup")
        self.menu_item = MenuItem.objects.create(
            category=self.category,
            name="Lemonade",
            description="Fresh lemonade",
            price=Decimal("50.00"),
            is_available=True
        )
        
        # Create Order
        self.order = Order.objects.create(
            customer_name="John Doe",
            customer_phone="+919876543210",
            subtotal_amount=Decimal("100.00"),
            tax_amount=Decimal("5.00"),
            total_amount=Decimal("105.00"),
            status="RECEIVED"
        )
        self.order_item = OrderItem.objects.create(
            order=self.order,
            menu_item=self.menu_item,
            quantity=2,
            price_at_order=Decimal("50.00"),
            item_name_at_order="Lemonade",
            category_name_at_order="Beverages",
            special_instructions="No ice please"
        )
        
    def test_customer_receipt_secure_routing(self):
        url = reverse("restaurant:order_receipt", kwargs={"tracking_token": self.order.tracking_token})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "John Doe")
        self.assertContains(response, "Lemonade")
        self.assertContains(response, "No ice please")
        
    def test_manager_receipt_authentication(self):
        url = reverse("restaurant:manager_order_receipt", kwargs={"pk": self.order.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        
        self.client.login(username="manager", password="password123")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "John Doe")
        
    def test_receipt_immutability(self):
        self.menu_item.price = Decimal("60.00")
        self.menu_item.save()
        
        url = reverse("restaurant:order_receipt", kwargs={"tracking_token": self.order.tracking_token})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "₹50.00")
        self.assertNotContains(response, "₹60.00")
