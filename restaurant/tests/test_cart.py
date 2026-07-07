from django.test import TestCase
from django.urls import reverse


class CartViewTest(TestCase):
    def test_cart_url_resolves(self):
        url = reverse("restaurant:cart")
        self.assertEqual(url, "/cart/")

    def test_cart_page_status_and_template(self):
        response = self.client.get(reverse("restaurant:cart"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "restaurant/cart.html")

    def test_cart_page_required_elements(self):
        response = self.client.get(reverse("restaurant:cart"))
        
        # Verify required container IDs and element hook handles
        self.assertContains(response, 'id="cart-items"')
        self.assertContains(response, 'id="empty-cart"')
        self.assertContains(response, 'id="cart-summary"')
        self.assertContains(response, 'id="cart-subtotal"')
        self.assertContains(response, 'id="cart-tax"')
        self.assertContains(response, 'id="cart-total"')
        self.assertContains(response, 'id="clear-cart-btn"')
        self.assertContains(response, 'id="checkout-btn"')
