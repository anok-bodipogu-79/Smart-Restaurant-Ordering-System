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
    tracking_token = forms.UUIDField(
        label="Tracking ID",
        required=True,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Enter your Tracking ID (UUID)",
            "id": "id_tracking_token"
        }),
        error_messages={
            "required": "Please enter a Tracking ID.",
            "invalid": "Please enter a valid Tracking ID (UUID)."
        }
    )


from restaurant.models import Category, MenuItem

class DateRangeFilterForm(forms.Form):
    period = forms.ChoiceField(
        choices=[
            ("today", "Today"),
            ("7days", "Last 7 Days"),
            ("30days", "Last 30 Days"),
            ("custom", "Custom Range"),
        ],
        required=False,
        initial="today"
    )
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"})
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"})
    )

    def clean(self):
        cleaned_data = super().clean()
        period_val = cleaned_data.get("period")
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if period_val == "custom":
            if not start_date or not end_date:
                raise ValidationError("Both Start Date and End Date are required for a custom range.")
            if start_date > end_date:
                raise ValidationError("Start Date cannot be after End Date.")
        return cleaned_data


class MenuItemForm(forms.ModelForm):
    class Meta:
        model = MenuItem
        fields = ["category", "name", "description", "price", "is_available", "image_url", "image", "is_vegetarian", "is_spicy"]
        widgets = {
            "category": forms.Select(attrs={"class": "form-select"}),
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Item name"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Item description"}),
            "price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "placeholder": "0.00"}),
            "image_url": forms.URLInput(attrs={"class": "form-control", "placeholder": "Image URL (optional)"}),
            "image": forms.FileInput(attrs={"class": "form-control", "id": "id_image", "accept": "image/*"}),
            "is_available": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_vegetarian": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_spicy": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "icon"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Category name (e.g. Desserts)"}),
            "icon": forms.TextInput(attrs={"class": "form-control", "placeholder": "Bootstrap icon name (e.g. bi-cake2)"}),
        }
