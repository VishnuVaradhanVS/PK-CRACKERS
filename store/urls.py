from django.urls import path
from . import views
urlpatterns = [
    path("", views.home, name="home"),
    path("signup/", views.signup, name="signup"),
    path("signup/verify-email/", views.verify_signup_email, name="verify_signup_email"),
    path("cart/", views.cart, name="cart"),
    path("cart/add/<int:product_id>/", views.add_to_cart, name="add_to_cart"),
    path("cart/update/<int:product_id>/", views.update_cart, name="update_cart"),
    path("checkout/", views.checkout, name="checkout"),
    path("orders/", views.my_orders, name="my_orders"),
    path("orders/<uuid:order_id>/", views.order_detail, name="order_detail"),
    path("staff/", views.dashboard, name="dashboard"),
    path("staff/products/create/", views.create_product, name="create_product"),
    path("staff/payment-settings/", views.update_payment_settings, name="update_payment_settings"),
    path("staff/orders/<uuid:order_id>/payment/", views.update_payment_status, name="update_payment_status"),
    path("staff/orders/<uuid:order_id>/status/", views.update_order_status, name="update_order_status"),
]
