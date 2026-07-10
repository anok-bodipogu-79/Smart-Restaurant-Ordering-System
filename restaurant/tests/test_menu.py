from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from restaurant.models import Category, MenuItem


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
        self.assertEqual(url, "/menu/")

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
