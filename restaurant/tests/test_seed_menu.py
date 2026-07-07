from decimal import Decimal
from django.test import TestCase
from django.core.management import call_command
from restaurant.models import Category, MenuItem


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
