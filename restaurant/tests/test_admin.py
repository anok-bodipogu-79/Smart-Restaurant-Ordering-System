from django.test import TestCase
from django.contrib import admin
from restaurant.models import Category, MenuItem, Order, OrderItem


class AdminRegistrationTest(TestCase):
    def test_admin_registration(self):
        self.assertTrue(admin.site.is_registered(Category))
        self.assertTrue(admin.site.is_registered(MenuItem))
        self.assertTrue(admin.site.is_registered(Order))
        self.assertTrue(admin.site.is_registered(OrderItem))
