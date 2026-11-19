from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from .models import Product, Order, OrderItem

class StoreFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="buyer", password="StrongPass123!")
        self.product = Product.objects.create(name="Demo Sparkler", cost="100.00", stock=5, is_active=True)

    def test_customer_can_place_order_and_stock_decreases(self):
        self.client.login(username="buyer", password="StrongPass123!")
        session = self.client.session
        session["cart"] = {str(self.product.id): 2}
        session.save()
        response = self.client.post(reverse("checkout"), {
            "username": "Buyer", "contact": "9999999999", "address": "Test address"
        })
        self.assertEqual(response.status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(OrderItem.objects.get().quantity, 2)

    def test_order_is_private_to_owner(self):
        self.client.login(username="buyer", password="StrongPass123!")
        order = Order.objects.create(user=self.user, username="Buyer", contact="123", address="Somewhere")
        other = User.objects.create_user(username="other", password="StrongPass123!")
        self.client.logout()
        self.client.login(username="other", password="StrongPass123!")
        response = self.client.get(reverse("order_detail", args=[order.pk]))
        self.assertEqual(response.status_code, 404)

    def test_anonymous_customer_is_redirected_to_login(self):
        response = self.client.get(reverse("cart"))
        self.assertEqual(response.status_code, 302)
    def test_duplicate_username_shows_inline_error_without_redirect(self):
        response = self.client.post(reverse("signup"), {
            "username": "buyer",
            "email": "another@example.com",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "That username is already taken. Please choose a different username.")
        self.assertEqual(User.objects.filter(username__iexact="buyer").count(), 1)

    def test_duplicate_username_is_case_insensitive(self):
        response = self.client.post(reverse("signup"), {
            "username": "Buyer",
            "email": "another@example.com",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "That username is already taken.")
        self.assertEqual(User.objects.filter(username__iexact="buyer").count(), 1)

