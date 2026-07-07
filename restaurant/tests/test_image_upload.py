import os
import shutil
import tempfile
from decimal import Decimal
from django.test import TestCase, override_settings, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from restaurant.models import Category, MenuItem, validate_image_file
from restaurant.forms import MenuItemForm

# Create a temporary directory for media files during testing
TEMP_MEDIA_ROOT = tempfile.mkdtemp()

@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class MenuItemImageUploadTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.category = Category.objects.create(name="Beverages", icon="bi-cup-hot")
        cls.managers_group, _ = Group.objects.get_or_create(name="Managers")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.manager_user = User.objects.create_user(
            username="testmanager", password="managerpassword123"
        )
        self.manager_user.groups.add(self.managers_group)
        self.client = Client()
        self.client.login(username="testmanager", password="managerpassword123")

    def get_simple_image(self, name="test.png", size_bytes=None, content_type="image/png"):
        from io import BytesIO
        from PIL import Image as PILImage
        file_obj = BytesIO()
        img = PILImage.new("RGB", (1, 1), color="red")
        img.save(file_obj, format="PNG")
        file_obj.seek(0)
        data = file_obj.read()
        if size_bytes and size_bytes > len(data):
            data += b'\x00' * (size_bytes - len(data))
        return SimpleUploadedFile(name, data, content_type=content_type)

    def test_validate_image_file_valid_png(self):
        valid_file = self.get_simple_image()
        # Should not raise any validation error
        try:
            validate_image_file(valid_file)
        except ValidationError:
            self.fail("validate_image_file raised ValidationError unexpectedly for a valid PNG.")

    def test_validate_image_file_oversized(self):
        # 5MB + 1 byte
        oversized_file = self.get_simple_image(size_bytes=5 * 1024 * 1024 + 1)
        with self.assertRaises(ValidationError) as context:
            validate_image_file(oversized_file)
        self.assertIn("Image size exceeds 5MB limit.", str(context.exception))

    def test_validate_image_file_invalid_format(self):
        invalid_file = SimpleUploadedFile("test.txt", b"plain_text_is_not_an_image", content_type="text/plain")
        with self.assertRaises(ValidationError) as context:
            validate_image_file(invalid_file)
        self.assertIn("Invalid image file.", str(context.exception))

    def test_validate_image_file_unsupported_image_format(self):
        # A mock GIF which is not in our supported (JPEG, PNG, WebP) list
        gif_data = b'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
        unsupported_file = SimpleUploadedFile("test.gif", gif_data, content_type="image/gif")
        with self.assertRaises(ValidationError) as context:
            validate_image_file(unsupported_file)
        self.assertIn("Unsupported format.", str(context.exception))

    def test_display_image_url_fallback(self):
        # Option 1: Both uploaded image and external URL exist -> Uploaded image takes precedence
        item = MenuItem.objects.create(
            category=self.category,
            name="Espresso",
            price=Decimal("150.00"),
            image_url="https://external.com/espresso.jpg",
            image=self.get_simple_image()
        )
        self.assertTrue(item.display_image_url.startswith("/media/menu_items/"))

        # Option 2: Only external URL exists
        item_external = MenuItem.objects.create(
            category=self.category,
            name="Latte",
            price=Decimal("180.00"),
            image_url="https://external.com/latte.jpg"
        )
        self.assertEqual(item_external.display_image_url, "https://external.com/latte.jpg")

        # Option 3: Neither exists -> default placeholder fallback
        item_placeholder = MenuItem.objects.create(
            category=self.category,
            name="Cappuccino",
            price=Decimal("190.00"),
            image_url=""
        )
        self.assertEqual(item_placeholder.display_image_url, "https://via.placeholder.com/300x200")

    def test_form_validation_valid_upload(self):
        form_data = {
            "category": self.category.id,
            "name": "Mocha",
            "description": "Rich espresso with chocolate",
            "price": "220.00",
            "image_url": "",
            "is_available": True,
            "is_vegetarian": True,
            "is_spicy": False
        }
        file_data = {
            "image": self.get_simple_image()
        }
        form = MenuItemForm(data=form_data, files=file_data)
        self.assertTrue(form.is_valid())

    def test_form_validation_invalid_upload(self):
        form_data = {
            "category": self.category.id,
            "name": "Mocha",
            "description": "Rich espresso with chocolate",
            "price": "220.00",
            "image_url": "",
            "is_available": True,
            "is_vegetarian": True,
            "is_spicy": False
        }
        file_data = {
            "image": SimpleUploadedFile("malicious.exe", b"not_an_image", content_type="application/octet-stream")
        }
        form = MenuItemForm(data=form_data, files=file_data)
        self.assertFalse(form.is_valid())
        self.assertIn("image", form.errors)

    def test_manager_menu_create_view_with_upload(self):
        payload = {
            "category": self.category.id,
            "name": "Cold Brew",
            "description": "24 hour slow steeped",
            "price": "180.00",
            "image_url": "",
            "is_available": True,
            "is_vegetarian": True,
            "is_spicy": False,
            "image": self.get_simple_image(name="cold_brew.png")
        }
        response = self.client.post(reverse("restaurant:manager_menu_create"), payload)
        self.assertEqual(response.status_code, 302)
        # Verify MenuItem was created and image was saved
        item = MenuItem.objects.get(name="Cold Brew")
        self.assertTrue(item.image)
        self.assertTrue(item.image.name.endswith("cold_brew.png"))
        self.assertTrue(os.path.exists(item.image.path))

    def test_manager_menu_edit_view_preserves_image(self):
        # Create item with image
        item = MenuItem.objects.create(
            category=self.category,
            name="Green Tea",
            price=Decimal("120.00"),
            image=self.get_simple_image(name="greentea.png")
        )
        old_image_path = item.image.path
        self.assertTrue(os.path.exists(old_image_path))

        # Edit item details without uploading a new image
        payload = {
            "category": self.category.id,
            "name": "Matcha Green Tea",
            "description": "Premium ceremonial grade matcha",
            "price": "130.00",
            "image_url": "",
            "is_available": True,
            "is_vegetarian": True,
            "is_spicy": False,
        }
        response = self.client.post(reverse("restaurant:manager_menu_edit", args=[item.id]), payload)
        self.assertEqual(response.status_code, 302)

        item.refresh_from_db()
        self.assertEqual(item.name, "Matcha Green Tea")
        self.assertEqual(item.price, Decimal("130.00"))
        # Verify old image is still preserved and not deleted or blanked out
        self.assertTrue(item.image)
        self.assertEqual(item.image.path, old_image_path)
        self.assertTrue(os.path.exists(old_image_path))

    def test_manager_menu_edit_view_replaces_image(self):
        # Create item with initial image
        item = MenuItem.objects.create(
            category=self.category,
            name="Black Coffee",
            price=Decimal("90.00"),
            image=self.get_simple_image(name="black_coffee.png")
        )
        old_image_path = item.image.path

        # Edit item and upload replacement image
        payload = {
            "category": self.category.id,
            "name": "Americano",
            "description": "Espresso with hot water",
            "price": "100.00",
            "image_url": "",
            "is_available": True,
            "is_vegetarian": True,
            "is_spicy": False,
            "image": self.get_simple_image(name="americano.png")
        }
        response = self.client.post(reverse("restaurant:manager_menu_edit", args=[item.id]), payload)
        self.assertEqual(response.status_code, 302)

        item.refresh_from_db()
        self.assertEqual(item.name, "Americano")
        self.assertTrue(item.image)
        self.assertTrue(item.image.name.endswith("americano.png"))
        self.assertTrue(os.path.exists(item.image.path))
