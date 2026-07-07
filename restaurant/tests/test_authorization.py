from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from restaurant.models import Category, MenuItem, Order

User = get_user_model()

class AuthorizationAccessMatrixTests(TestCase):
    def setUp(self):
        # Create Groups
        self.kitchen_group, _ = Group.objects.get_or_create(name='Kitchen Staff')
        self.manager_group, _ = Group.objects.get_or_create(name='Managers')

        # Create Users
        self.customer = Client()  # Anonymous client
        
        self.kitchen_user = User.objects.create_user(username='kitchen', password='password123')
        self.kitchen_user.groups.add(self.kitchen_group)
        self.kitchen_client = Client()
        self.kitchen_client.login(username='kitchen', password='password123')
        
        self.manager_user = User.objects.create_user(username='manager', password='password123')
        self.manager_user.groups.add(self.manager_group)
        self.manager_client = Client()
        self.manager_client.login(username='manager', password='password123')
        
        self.superuser = User.objects.create_superuser(username='admin', email='admin@test.com', password='password123')
        self.admin_client = Client()
        self.admin_client.login(username='admin', password='password123')

        # Create basic data for endpoints requiring PKs
        self.category = Category.objects.create(name="Test Category")
        self.menu_item = MenuItem.objects.create(name="Test Item", price=10.00, category=self.category)
        self.order = Order.objects.create(
            customer_name="Test", customer_phone="1234567890", total_amount=10.00
        )

    # ----------------------------------------------------
    # KITCHEN DASHBOARD AUTHORIZATION
    # ----------------------------------------------------
    def test_kitchen_dashboard_anonymous_denied(self):
        response = self.customer.get(reverse('restaurant:kitchen_dashboard'))
        self.assertRedirects(response, reverse('restaurant:kitchen_login'))

    def test_kitchen_dashboard_manager_denied(self):
        response = self.manager_client.get(reverse('restaurant:kitchen_dashboard'))
        self.assertEqual(response.status_code, 403)

    def test_kitchen_dashboard_kitchen_allowed(self):
        response = self.kitchen_client.get(reverse('restaurant:kitchen_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_kitchen_dashboard_superuser_allowed(self):
        response = self.admin_client.get(reverse('restaurant:kitchen_dashboard'))
        self.assertEqual(response.status_code, 200)

    # ----------------------------------------------------
    # KITCHEN ORDER STATUS POST AUTHORIZATION
    # ----------------------------------------------------
    def test_kitchen_status_post_manager_denied(self):
        url = reverse('restaurant:kitchen_order_status', kwargs={'pk': self.order.id})
        response = self.manager_client.post(url, {'status': 'PREPARING'})
        self.assertEqual(response.status_code, 403)
        
    def test_kitchen_status_post_kitchen_allowed(self):
        url = reverse('restaurant:kitchen_order_status', kwargs={'pk': self.order.id})
        response = self.kitchen_client.post(url, {'status': 'PREPARING'})
        # Should redirect to kitchen dashboard on success
        self.assertEqual(response.status_code, 302)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'PREPARING')

    # ----------------------------------------------------
    # MANAGER DASHBOARD AUTHORIZATION
    # ----------------------------------------------------
    def test_manager_dashboard_anonymous_denied(self):
        response = self.customer.get(reverse('restaurant:manager_dashboard'))
        self.assertRedirects(response, reverse('restaurant:manager_login'))

    def test_manager_dashboard_kitchen_denied(self):
        response = self.kitchen_client.get(reverse('restaurant:manager_dashboard'))
        self.assertEqual(response.status_code, 403)

    def test_manager_dashboard_manager_allowed(self):
        response = self.manager_client.get(reverse('restaurant:manager_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_manager_dashboard_superuser_allowed(self):
        response = self.admin_client.get(reverse('restaurant:manager_dashboard'))
        self.assertEqual(response.status_code, 200)

    # ----------------------------------------------------
    # MANAGER ORDER CANCEL POST AUTHORIZATION
    # ----------------------------------------------------
    def test_manager_cancel_kitchen_denied(self):
        url = reverse('restaurant:manager_order_cancel', kwargs={'pk': self.order.id})
        response = self.kitchen_client.post(url)
        self.assertEqual(response.status_code, 403)

    def test_manager_cancel_manager_allowed(self):
        url = reverse('restaurant:manager_order_cancel', kwargs={'pk': self.order.id})
        response = self.manager_client.post(url)
        self.assertEqual(response.status_code, 302)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'CANCELLED')

    # ----------------------------------------------------
    # DJANGO ADMIN AUTHORIZATION
    # ----------------------------------------------------
    def test_admin_kitchen_denied(self):
        response = self.kitchen_client.get(reverse('admin:index'))
        # Should redirect to admin login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response.url)

    def test_admin_manager_denied(self):
        response = self.manager_client.get(reverse('admin:index'))
        # Should redirect to admin login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response.url)

    def test_admin_superuser_allowed(self):
        response = self.admin_client.get(reverse('admin:index'))
        self.assertEqual(response.status_code, 200)
