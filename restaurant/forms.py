import re
from django import forms
from django.core.exceptions import ValidationError

class CheckoutForm(forms.Form):
    customer_name = forms.CharField(
        label="Customer Name",
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Enter your full name",
            "id": "id_customer_name"
        })
    )
    customer_phone = forms.CharField(
        label="Customer Phone",
        max_length=15,
        required=True,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Enter 10-digit phone number",
            "id": "id_customer_phone"
        })
    )
    table_number = forms.IntegerField(
        label="Table Number",
        required=False,
        min_value=1,
        max_value=999,
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "placeholder": "Enter table number (optional)",
            "id": "id_table_number"
        })
    )

    def clean_customer_name(self):
        name = self.cleaned_data.get("customer_name")
        if name:
            name = name.strip()
            if len(name) < 2:
                raise ValidationError("Name must be at least 2 characters long.")
            if not name:
                raise ValidationError("Name cannot be empty or only whitespace.")
        return name

    def clean_customer_phone(self):
        phone = self.cleaned_data.get("customer_phone")
        if phone:
            phone = phone.strip()
            # Indian mobile numbers: 10 digits, optional spaces/hyphens, optional +91 or 91 prefix
            # Remove non-digits
            digits = re.sub(r"\D", "", phone)
            
            # If phone starts with 91 and has 12 digits, extract last 10 digits
            if digits.startswith("91") and len(digits) == 12:
                digits = digits[2:]
                
            if len(digits) != 10:
                raise ValidationError("Please enter a valid 10-digit Indian phone number.")
            
            # Normalize to +91XXXXXXXXXX
            return f"+91{digits}"
        return phone


class OrderTrackingForm(forms.Form):
    order_id = forms.IntegerField(
        label="Order ID",
        required=True,
        min_value=1,
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "placeholder": "Enter your Order ID (e.g. 15)",
            "id": "id_order_id"
        }),
        error_messages={
            "required": "Please enter an Order ID.",
            "invalid": "Please enter a valid integer Order ID.",
            "min_value": "Order ID must be a positive number."
        }
    )
