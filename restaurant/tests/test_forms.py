import uuid
from django.test import TestCase
from restaurant.forms import CheckoutForm, OrderTrackingForm


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


class OrderTrackingFormTest(TestCase):
    def test_tracking_form_valid(self):
        token = uuid.uuid4()
        form = OrderTrackingForm(data={"tracking_token": str(token)})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["tracking_token"], token)

    def test_tracking_form_invalid_format(self):
        form = OrderTrackingForm(data={"tracking_token": "not-a-uuid"})
        self.assertFalse(form.is_valid())
        self.assertIn("tracking_token", form.errors)

    def test_tracking_form_invalid_empty(self):
        form = OrderTrackingForm(data={"tracking_token": ""})
        self.assertFalse(form.is_valid())
        self.assertIn("tracking_token", form.errors)
