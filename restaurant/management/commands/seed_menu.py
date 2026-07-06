from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from restaurant.models import Category, MenuItem


class Command(BaseCommand):
    help = "Seeds the database with realistic categories and menu items."

    def handle(self, *args, **options):
        self.stdout.write("Starting menu database seeding...")

        categories_data = [
            {"name": "Appetizers", "icon": "bi-egg-fried"},
            {"name": "Main Course", "icon": "bi-fire"},
            {"name": "Desserts", "icon": "bi-cake"},
            {"name": "Beverages", "icon": "bi-cup-straw"},
        ]

        menu_items_data = [
            # Appetizers
            {
                "category_name": "Appetizers",
                "name": "Paneer Tikka",
                "description": "Succulent chunks of paneer marinated in spiced yogurt and grilled in a tandoor.",
                "price": Decimal("220.00"),
                "is_vegetarian": True,
                "is_spicy": True,
                "is_available": True,
                "image_url": "https://via.placeholder.com/300x200",
            },
            {
                "category_name": "Appetizers",
                "name": "Chicken 65",
                "description": "Crispy, deep-fried spicy chicken chunks marinated in yogurt and curry leaves.",
                "price": Decimal("260.00"),
                "is_vegetarian": False,
                "is_spicy": True,
                "is_available": True,
                "image_url": "https://via.placeholder.com/300x200",
            },
            {
                "category_name": "Appetizers",
                "name": "Vegetable Spring Rolls",
                "description": "Crispy pastry wraps filled with seasoned stir-fried vegetables.",
                "price": Decimal("150.00"),
                "is_vegetarian": True,
                "is_spicy": False,
                "is_available": True,
                "image_url": "https://via.placeholder.com/300x200",
            },
            {
                "category_name": "Appetizers",
                "name": "Gobi Manchurian",
                "description": "Crispy cauliflower florets tossed in a tangy and spicy Indo-Chinese sauce.",
                "price": Decimal("180.00"),
                "is_vegetarian": True,
                "is_spicy": True,
                "is_available": True,
                "image_url": "https://via.placeholder.com/300x200",
            },
            # Main Course
            {
                "category_name": "Main Course",
                "name": "Chicken Biryani",
                "description": "Aromatic basmati rice cooked with tender chicken, spices, and fresh herbs.",
                "price": Decimal("350.00"),
                "is_vegetarian": False,
                "is_spicy": True,
                "is_available": True,
                "image_url": "https://via.placeholder.com/300x200",
            },
            {
                "category_name": "Main Course",
                "name": "Paneer Butter Masala",
                "description": "Rich and creamy curry made with paneer chunks, tomatoes, butter, and cashew paste.",
                "price": Decimal("280.00"),
                "is_vegetarian": True,
                "is_spicy": False,
                "is_available": True,
                "image_url": "https://via.placeholder.com/300x200",
            },
            {
                "category_name": "Main Course",
                "name": "Vegetable Fried Rice",
                "description": "Fluffy rice stir-fried with finely chopped vegetables and mild soy sauce.",
                "price": Decimal("200.00"),
                "is_vegetarian": True,
                "is_spicy": False,
                "is_available": True,
                "image_url": "https://via.placeholder.com/300x200",
            },
            {
                "category_name": "Main Course",
                "name": "Butter Chicken",
                "description": "Tender tandoori chicken cooked in a rich, buttery, and creamy tomato gravy.",
                "price": Decimal("380.00"),
                "is_vegetarian": False,
                "is_spicy": False,
                "is_available": True,
                "image_url": "https://via.placeholder.com/300x200",
            },
            # Desserts
            {
                "category_name": "Desserts",
                "name": "Gulab Jamun",
                "description": "Soft and spongy milk-solid balls soaked in warm sugar syrup flavored with cardamom.",
                "price": Decimal("90.00"),
                "is_vegetarian": True,
                "is_spicy": False,
                "is_available": True,
                "image_url": "https://via.placeholder.com/300x200",
            },
            {
                "category_name": "Desserts",
                "name": "Chocolate Brownie",
                "description": "Warm, fudgy chocolate brownie served with chocolate drizzle.",
                "price": Decimal("140.00"),
                "is_vegetarian": True,
                "is_spicy": False,
                "is_available": True,
                "image_url": "https://via.placeholder.com/300x200",
            },
            {
                "category_name": "Desserts",
                "name": "Vanilla Ice Cream",
                "description": "Creamy vanilla bean ice cream scoop.",
                "price": Decimal("80.00"),
                "is_vegetarian": True,
                "is_spicy": False,
                "is_available": True,
                "image_url": "https://via.placeholder.com/300x200",
            },
            {
                "category_name": "Desserts",
                "name": "Rasmalai",
                "description": "Soft cottage cheese patties soaked in sweetened, saffron-infused milk.",
                "price": Decimal("120.00"),
                "is_vegetarian": True,
                "is_spicy": False,
                "is_available": True,
                "image_url": "https://via.placeholder.com/300x200",
            },
            # Beverages
            {
                "category_name": "Beverages",
                "name": "Masala Soda",
                "description": "Refreshing and tangy spiced soda with black salt, cumin, and mint.",
                "price": Decimal("70.00"),
                "is_vegetarian": True,
                "is_spicy": True,
                "is_available": True,
                "image_url": "https://via.placeholder.com/300x200",
            },
            {
                "category_name": "Beverages",
                "name": "Fresh Lime Juice",
                "description": "Freshly squeezed lime juice with ice, sugar, and salt.",
                "price": Decimal("60.00"),
                "is_vegetarian": True,
                "is_spicy": False,
                "is_available": True,
                "image_url": "https://via.placeholder.com/300x200",
            },
            {
                "category_name": "Beverages",
                "name": "Cold Coffee",
                "description": "Chilled blend of rich coffee, milk, and chocolate syrup.",
                "price": Decimal("110.00"),
                "is_vegetarian": True,
                "is_spicy": False,
                "is_available": True,
                "image_url": "https://via.placeholder.com/300x200",
            },
            {
                "category_name": "Beverages",
                "name": "Mango Lassi",
                "description": "Thick and creamy yogurt drink blended with fresh sweet mango pulp.",
                "price": Decimal("100.00"),
                "is_vegetarian": True,
                "is_spicy": False,
                "is_available": True,
                "image_url": "https://via.placeholder.com/300x200",
            },
        ]

        try:
            with transaction.atomic():
                # Track counts of items created or updated
                cats_created = 0
                cats_updated = 0
                items_created = 0
                items_updated = 0

                # 1. Seed Categories
                category_objs = {}
                for cat_data in categories_data:
                    cat, created = Category.objects.update_or_create(
                        name=cat_data["name"],
                        defaults={"icon": cat_data["icon"]}
                    )
                    category_objs[cat.name] = cat
                    if created:
                        cats_created += 1
                    else:
                        cats_updated += 1

                # 2. Seed Menu Items
                for item_data in menu_items_data:
                    category = category_objs[item_data["category_name"]]
                    item, created = MenuItem.objects.update_or_create(
                        category=category,
                        name=item_data["name"],
                        defaults={
                            "description": item_data["description"],
                            "price": item_data["price"],
                            "is_vegetarian": item_data["is_vegetarian"],
                            "is_spicy": item_data["is_spicy"],
                            "is_available": item_data["is_available"],
                            "image_url": item_data["image_url"],
                        }
                    )
                    if created:
                        items_created += 1
                    else:
                        items_updated += 1

            self.stdout.write(self.style.SUCCESS(
                f"Menu seeding completed successfully.\n"
                f"Categories: {cats_created} created, {cats_updated} updated/existing.\n"
                f"Menu Items: {items_created} created, {items_updated} updated/existing."
            ))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error seeding menu database: {str(e)}"))
            raise e
