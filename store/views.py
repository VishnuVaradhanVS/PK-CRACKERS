from decimal import Decimal
import secrets
from datetime import timedelta
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.db.models import F
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.urls import reverse
from django.conf import settings
import logging
import re
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
import re
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .forms import (CheckoutForm, SignupForm, ProductForm, StorePaymentSettingsForm, EmailOrUsernameAuthenticationForm)
from .models import Product, Order, OrderItem, StorePaymentSettings, CartItem, EmailVerificationOTP
from .whatsapp import send_admin_new_order, send_customer_order_confirmation, send_customer_order_update

logger = logging.getLogger(__name__)


def admin_whatsapp_recipients():
    """Return configured admin WhatsApp numbers in normalized international format."""
    raw = StorePaymentSettings.current().whatsapp_admin_numbers or ""
    recipients = []
    for number in re.split(r"[,;\s]+", raw):
        number = number.strip()
        if number and number not in recipients:
            recipients.append(number)
    return recipients


def admin_notification_recipients():
    """Return each configured admin address separately, regardless of separator."""
    raw = StorePaymentSettings.current().notification_emails or ""
    recipients = []
    for address in re.split(r"[,;\s]+", raw):
        address = address.strip()
        if not address:
            continue
        try:
            validate_email(address)
        except ValidationError:
            logger.warning("Skipping invalid admin notification email address: %s", address)
            continue
        if address.lower() not in {item.lower() for item in recipients}:
            recipients.append(address)
    return recipients

def send_branded_email(subject, template_name, context, recipients):
    """Send branded HTML and plain-text email without breaking an order operation."""
    recipients = list(dict.fromkeys(email.strip() for email in recipients if email and email.strip()))
    if not recipients:
        return
    try:
        context.setdefault("brand_name", "PK CRACKERS")
        context.setdefault("brand_logo_url", context.get("brand_logo_url", ""))
        context.setdefault("support_email", settings.DEFAULT_FROM_EMAIL)
        text_body = render_to_string(f"emails/{template_name}.txt", context)
        html_body = render_to_string(f"emails/{template_name}.html", context)
        email = EmailMultiAlternatives(subject, text_body, settings.DEFAULT_FROM_EMAIL, recipients)
        email.attach_alternative(html_body, "text/html")
        email.send(fail_silently=False)
    except Exception:
        logger.exception("Order notification email could not be sent.")


def order_status_label(value):
    return dict(Order.Status.choices).get(value, value)


def order_payment_label(value):
    return dict(Order.PaymentStatus.choices).get(value, value)


def order_email_context(order, request, **extra):
    payment_settings = StorePaymentSettings.current()
    qr_url = request.build_absolute_uri(payment_settings.qr_code.url) if payment_settings.qr_code else ""
    return {
        "order": order,
        "items": list(order.items.all()),
        "payment_settings": payment_settings,
        "payment_qr_url": qr_url,
        "order_url": request.build_absolute_uri(reverse("order_detail", args=[order.pk])),
        "staff_url": request.build_absolute_uri(reverse("dashboard")),
        "brand_logo_url": request.build_absolute_uri(static("store/images/pk-crackers-seal.jpg")),
        **extra,
    }


def home(request):
    products = Product.objects.filter(is_active=True, stock__gt=0)
    search_query = request.GET.get("q", "").strip()
    category_filter = request.GET.get("category", "").strip()
    if search_query:
        products = products.filter(name__icontains=search_query)
    if category_filter:
        products = products.filter(category__iexact=category_filter)
    categories = (
        Product.objects.filter(is_active=True, stock__gt=0)
        .exclude(category="")
        .order_by("category")
        .values_list("category", flat=True)
        .distinct()
    )
    return render(request, "store/home.html", {
        "products": products,
        "search_query": search_query,
        "categories": categories,
        "category_filter": category_filter,
    })

def _send_signup_otp(email, username, code):
    context = {"email": email, "username": username, "otp": code}
    subject = "PK CRACKERS | Verify your email address"
    text_body = render_to_string("registration/email_verification_otp.txt", context)
    html_body = render_to_string("registration/email_verification_otp.html", context)
    message = EmailMultiAlternatives(subject, text_body, settings.DEFAULT_FROM_EMAIL, [email])
    message.attach_alternative(html_body, "text/html")
    message.send(fail_silently=False)


def signup(request):
    if request.user.is_authenticated:
        return redirect("home")

    pending_key = "pending_signup"
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].strip().lower()
            username = form.cleaned_data["username"].strip()
            if User.objects.filter(email__iexact=email).exists():
                form.add_error("email", "An account with this email address already exists. Please log in or reset your password.")
            elif User.objects.filter(username__iexact=username).exists():
                form.add_error("username", "This username is already in use. Please choose another username.")
            else:
                code = f"{secrets.randbelow(1_000_000):06d}"
                record, created = EmailVerificationOTP.objects.get_or_create(
                    email=email,
                    defaults={
                        "code_hash": make_password(code),
                        "expires_at": timezone.now() + timedelta(minutes=10),
                    },
                )
                if not created and record.created_at > timezone.now() - timedelta(seconds=60):
                    form.add_error(None, "A verification code was sent recently. Please wait one minute before trying again.")
                else:
                    if not created:
                        record.code_hash = make_password(code)
                        record.expires_at = timezone.now() + timedelta(minutes=10)
                        record.created_at = timezone.now()
                        record.attempts = 0
                        record.save(update_fields=["code_hash", "expires_at", "created_at", "attempts"])
                    request.session[pending_key] = {
                        "username": username,
                        "email": email,
                        "password_hash": make_password(form.cleaned_data["password1"]),
                    }
                    try:
                        _send_signup_otp(email, username, code)
                    except Exception:
                        logger.exception("Signup email OTP could not be sent.")
                        EmailVerificationOTP.objects.filter(email=email).delete()
                        request.session.pop(pending_key, None)
                        form.add_error(None, "We couldn't send a verification email. Please try again later.")
                    else:
                        request.session.modified = True
                        messages.success(request, f"We sent a 6-digit verification code to {email}. It expires in 10 minutes.")
                        return redirect("verify_signup_email")
    else:
        form = SignupForm()
    return render(request, "registration/signup.html", {"form": form})


def verify_signup_email(request):
    if request.user.is_authenticated:
        return redirect("home")
    pending_key = "pending_signup"
    pending = request.session.get(pending_key)
    if not pending:
        messages.info(request, "Please start by creating your account.")
        return redirect("signup")

    if request.method == "POST" and request.POST.get("action") == "resend":
        record = EmailVerificationOTP.objects.filter(email=pending["email"]).first()
        if record and record.created_at > timezone.now() - timedelta(seconds=60):
            messages.error(request, "Please wait one minute before requesting another code.")
        else:
            code = f"{secrets.randbelow(1_000_000):06d}"
            EmailVerificationOTP.objects.update_or_create(
                email=pending["email"],
                defaults={
                    "code_hash": make_password(code),
                    "expires_at": timezone.now() + timedelta(minutes=10),
                    "created_at": timezone.now(),
                    "attempts": 0,
                },
            )
            try:
                _send_signup_otp(pending["email"], pending["username"], code)
                messages.success(request, "A new verification code has been sent.")
            except Exception:
                logger.exception("Signup OTP resend failed.")
                messages.error(request, "We couldn't send a new code. Please try again later.")
        return redirect("verify_signup_email")

    if request.method == "POST":
        code = request.POST.get("otp", "").strip()
        record = EmailVerificationOTP.objects.filter(email=pending["email"]).first()
        if not record:
            request.session.pop(pending_key, None)
            messages.error(request, "Your verification session has expired. Please start signup again.")
            return redirect("signup")
        if record.expires_at <= timezone.now():
            record.delete()
            request.session.pop(pending_key, None)
            messages.error(request, "That verification code has expired. Please create your account again.")
            return redirect("signup")
        if record.attempts >= 5:
            record.delete()
            request.session.pop(pending_key, None)
            messages.error(request, "Too many incorrect attempts. Please start signup again.")
            return redirect("signup")

        record.attempts += 1
        record.save(update_fields=["attempts"])
        if not (len(code) == 6 and code.isdigit() and check_password(code, record.code_hash)):
            messages.error(request, "The verification code is incorrect. Please try again.")
            return render(request, "registration/verify_email_otp.html", {"email": pending["email"]})

        try:
            with transaction.atomic():
                if User.objects.filter(email__iexact=pending["email"]).exists():
                    raise ValueError("An account with this email address already exists. Please log in.")
                if User.objects.filter(username__iexact=pending["username"]).exists():
                    raise ValueError("This username is already in use. Please choose another username.")
                user = User(username=pending["username"], email=pending["email"])
                user.password = pending["password_hash"]
                user.save()
                record.delete()
        except (IntegrityError, ValueError) as exc:
            record.delete()
            request.session.pop(pending_key, None)
            messages.error(request, str(exc) or "We couldn't create your account. Please try again.")
            return redirect("signup")

        request.session.pop(pending_key, None)
        login(request, user)
        merge_session_cart(user, request)
        messages.success(request, "Your email has been verified and your PK CRACKERS account is ready.")
        return redirect("home")

    return render(request, "registration/verify_email_otp.html", {"email": pending["email"]})



def merge_session_cart(user, request):
    """Import any pre-upgrade session cart into the customer's persistent cart."""
    legacy = request.session.get("cart", {})
    if not isinstance(legacy, dict) or not legacy:
        return
    for raw_id, raw_qty in legacy.items():
        if not str(raw_id).isdigit():
            continue
        try:
            product = Product.objects.get(pk=int(raw_id), is_active=True)
            quantity = max(0, min(int(raw_qty), 99, product.stock))
        except (Product.DoesNotExist, TypeError, ValueError):
            continue
        if quantity:
            item, created = CartItem.objects.get_or_create(user=user, product=product, defaults={"quantity": quantity})
            if not created:
                item.quantity = min(item.quantity + quantity, product.stock, 99)
                item.save(update_fields=["quantity", "updated_at"])
    request.session.pop("cart", None)
    request.session.modified = True


class PersistentLoginView(LoginView):
    template_name = "registration/login.html"
    authentication_form = EmailOrUsernameAuthenticationForm

    def form_valid(self, form):
        merge_session_cart(form.get_user(), self.request)
        self.request.session["show_supreme_court_notice"] = True
        return super().form_valid(form)


@login_required
def cart(request):
    merge_session_cart(request.user, request)
    items = CartItem.objects.filter(user=request.user, product__is_active=True).select_related("product")
    rows, total = [], Decimal("0.00")
    for item in items:
        quantity = min(item.quantity, item.product.stock, 99)
        if quantity < 1:
            item.delete()
            continue
        if quantity != item.quantity:
            item.quantity = quantity
            item.save(update_fields=["quantity", "updated_at"])
        line_total = item.product.cost * quantity
        rows.append({"product": item.product, "quantity": quantity, "line_total": line_total})
        total += line_total
    return render(request, "store/cart.html", {"rows": rows, "total": total})

@login_required
@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    try:
        quantity = int(request.POST.get("quantity", "1"))
    except (TypeError, ValueError):
        quantity = 0
    if quantity < 1 or quantity > 99:
        messages.error(request, "Choose a quantity between 1 and 99.")
    else:
        merge_session_cart(request.user, request)
        with transaction.atomic():
            item = CartItem.objects.select_for_update().filter(user=request.user, product=product).first()
            new_qty = quantity + (item.quantity if item else 0)
            if new_qty > product.stock:
                messages.error(request, f"Only {product.stock} currently available.")
            elif item:
                item.quantity = new_qty
                item.save(update_fields=["quantity", "updated_at"])
                messages.success(request, "Cart updated and saved to your account.")
            else:
                CartItem.objects.create(user=request.user, product=product, quantity=new_qty)
                messages.success(request, "Added to your saved cart.")
    return redirect("home")

@login_required
@require_POST
def update_cart(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    try:
        quantity = int(request.POST.get("quantity", "0"))
    except (TypeError, ValueError):
        quantity = -1
    item = get_object_or_404(CartItem, user=request.user, product=product)
    if quantity <= 0:
        item.delete()
    elif quantity <= product.stock and quantity <= 99:
        item.quantity = quantity
        item.save(update_fields=["quantity", "updated_at"])
    else:
        messages.error(request, f"Quantity exceeds available stock ({product.stock}).")
    return redirect("cart")

@login_required
def checkout(request):
    merge_session_cart(request.user, request)
    cart_items = list(CartItem.objects.filter(user=request.user).select_related("product"))
    form = CheckoutForm(request.POST or None, initial={"username": request.user.get_full_name() or request.user.username, "contact": "", "address": ""})
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                order = Order.objects.create(
                    user=request.user, username=form.cleaned_data["username"],
                    contact=form.cleaned_data["contact"], address=form.cleaned_data["address"],
                    whatsapp_opt_in=form.cleaned_data.get("whatsapp_opt_in", False),
                )
                total = Decimal("0.00")
                for cart_item in cart_items:
                    product_id, quantity = cart_item.product_id, cart_item.quantity
                    if quantity < 1 or quantity > 99:
                        raise ValueError("Invalid cart quantity.")
                    product = Product.objects.select_for_update().get(pk=product_id, is_active=True)
                    if product.stock < quantity:
                        raise ValueError(f"Insufficient stock for {product.name}.")
                    Product.objects.filter(pk=product.pk).update(stock=F("stock") - quantity)
                    line_total = product.cost * quantity
                    OrderItem.objects.create(order=order, product=product, product_name=product.name, unit_price=product.cost, quantity=quantity, line_total=line_total)
                    total += line_total
                if not order.items.exists():
                    raise ValueError("Your cart is empty.")
                order.total_amount = total
                order.save(update_fields=["total_amount"])
                CartItem.objects.filter(user=request.user).delete()
            context = order_email_context(order, request)
            send_branded_email(
                f"PK CRACKERS | Order confirmation · #{str(order.pk)[:8].upper()}",
                "customer_order_confirmation", context,
                [request.user.email] if request.user.email else [],
            )
            send_branded_email(
                f"PK CRACKERS | New order received · #{str(order.pk)[:8].upper()}",
                "admin_new_order", context, admin_notification_recipients(),
            )
            # WhatsApp delivery is deliberately isolated from checkout/email failures.
            try:
                send_customer_order_confirmation(order)
                send_admin_new_order(order, admin_whatsapp_recipients())
            except Exception:
                logger.exception("WhatsApp new-order notifications failed unexpectedly.")
            messages.success(request, "Your order request has been placed.")
            return redirect("order_detail", order_id=order.pk)
        except (Product.DoesNotExist, ValueError) as exc:
            messages.error(request, str(exc) or "A product is no longer available.")
            return redirect("cart")
    return render(request, "store/checkout.html", {"form": form, "payment_settings": StorePaymentSettings.current()})

@login_required
def my_orders(request):
    return render(request, "store/orders.html", {"orders": Order.objects.filter(user=request.user)})

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order.objects.prefetch_related("items"), pk=order_id, user=request.user)
    return render(request, "store/order_detail.html", {"order": order})

def staff_required(user):
    return user.is_authenticated and user.is_staff

@user_passes_test(staff_required, login_url="login")
def dashboard(request):
    product_query = request.GET.get("product_q", "").strip()
    order_status_filter = request.GET.get("order_status", "").strip()
    active_tab = request.GET.get("tab", "inventory")
    if active_tab not in {"inventory", "orders", "payments"}:
        active_tab = "inventory"

    products = Product.objects.all()
    if product_query:
        products = products.filter(name__icontains=product_query)

    orders = Order.objects.prefetch_related("items").all()
    valid_statuses = {choice[0] for choice in Order.Status.choices}
    if order_status_filter in valid_statuses:
        orders = orders.filter(status=order_status_filter)
    else:
        order_status_filter = ""

    edit_product = None
    edit_id = request.GET.get("edit", "").strip()
    if edit_id.isdigit():
        edit_product = Product.objects.filter(pk=int(edit_id)).first()
        if edit_product:
            active_tab = "inventory"

    payment_settings = StorePaymentSettings.current()
    return render(request, "store/dashboard.html", {
        "products": products,
        "orders": orders[:200],
        "order_count": Order.objects.count(),
        "status_choices": Order.Status.choices,
        "payment_choices": Order.PaymentStatus.choices,
        "product_form": ProductForm(instance=edit_product),
        "edit_product": edit_product,
        "product_query": product_query,
        "order_status_filter": order_status_filter,
        "active_tab": active_tab,
        "payment_settings": payment_settings,
        "payment_settings_form": StorePaymentSettingsForm(instance=payment_settings),
    })

@user_passes_test(staff_required, login_url="login")
@require_POST
def create_product(request):
    product_id = request.POST.get("product_id", "").strip()
    instance = get_object_or_404(Product, pk=product_id) if product_id.isdigit() else None
    form = ProductForm(request.POST, request.FILES, instance=instance)
    if form.is_valid():
        product = form.save()
        messages.success(request, f"{product.name} {'updated' if instance else 'added'} successfully.")
        return redirect(f"/staff/?tab=inventory#inventory-panel")
    messages.error(request, "Please correct the product form errors: " + "; ".join(
        f"{field}: {', '.join(errors)}" for field, errors in form.errors.items()
    ))
    return redirect(f"/staff/?tab=inventory&edit={product_id}#inventory-panel" if instance else "/staff/?tab=inventory#inventory-panel")

@user_passes_test(staff_required, login_url="login")
@require_POST
def update_payment_status(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    new_status = request.POST.get("payment_status")
    allowed = {choice[0] for choice in Order.PaymentStatus.choices}
    if new_status not in allowed:
        messages.error(request, "Invalid payment status.")
    else:
        old_payment_status = order.payment_status
        order.payment_status = new_status
        order.payment_note = request.POST.get("payment_note", "")[:250]
        order.save(update_fields=["payment_status", "payment_note"])
        if old_payment_status != new_status:
            payment_changes = [{
                "label": "Payment status",
                "old_value": order_payment_label(old_payment_status),
                "new_value": order.get_payment_status_display(),
            }]
            if order.user.email:
                send_branded_email(
                    f"PK CRACKERS | Payment update · #{str(order.pk)[:8].upper()}",
                    "customer_order_update",
                    order_email_context(order, request, changes=payment_changes),
                    [order.user.email],
                )
            try:
                send_customer_order_update(order, payment_changes)
            except Exception:
                logger.exception("WhatsApp payment update notification failed unexpectedly.")
        messages.success(request, "Manual payment status updated.")
    return redirect("dashboard")

@user_passes_test(staff_required, login_url="login")
@require_POST
def update_order_status(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    new_status = request.POST.get("status")
    new_payment_status = request.POST.get("payment_status")
    allowed_statuses = {choice[0] for choice in Order.Status.choices}
    allowed_payment = {choice[0] for choice in Order.PaymentStatus.choices}
    if new_status not in allowed_statuses or new_payment_status not in allowed_payment:
        messages.error(request, "Please select valid order and payment statuses.")
        return redirect("/staff/?tab=orders#orders-panel")
    with transaction.atomic():
        locked = Order.objects.select_for_update().get(pk=order_id)
        old_status = locked.status
        old_payment_status = locked.payment_status
        if old_status == Order.Status.CANCELLED and new_status != Order.Status.CANCELLED:
            messages.error(request, "Cancelled orders cannot be reopened; create a new order instead.")
            return redirect("/staff/?tab=orders#orders-panel")
        if old_status != Order.Status.CANCELLED and new_status == Order.Status.CANCELLED:
            for item in locked.items.all():
                Product.objects.filter(pk=item.product_id).update(stock=F("stock") + item.quantity)
        locked.status = new_status
        locked.payment_status = new_payment_status
        locked.payment_note = request.POST.get("payment_note", "")[:250]
        locked.save(update_fields=["status", "payment_status", "payment_note"])
        updated_order = locked
    if old_status != new_status or old_payment_status != new_payment_status:
        changes = []
        if old_status != new_status:
            changes.append({
                "label": "Order status",
                "old_value": order_status_label(old_status),
                "new_value": updated_order.get_status_display(),
            })
        if old_payment_status != new_payment_status:
            changes.append({
                "label": "Payment status",
                "old_value": order_payment_label(old_payment_status),
                "new_value": updated_order.get_payment_status_display(),
            })
        if updated_order.user.email:
            send_branded_email(
                f"PK CRACKERS | Order update · #{str(updated_order.pk)[:8].upper()}",
                "customer_order_update",
                order_email_context(updated_order, request, changes=changes),
                [updated_order.user.email],
            )
        try:
            send_customer_order_update(updated_order, changes)
        except Exception:
            logger.exception("WhatsApp order update notification failed unexpectedly.")
    messages.success(request, "Order and payment information updated.")
    return redirect("/staff/?tab=orders#orders-panel")


@user_passes_test(staff_required, login_url="login")
@require_POST
def update_payment_settings(request):
    settings_obj = StorePaymentSettings.current()
    form = StorePaymentSettingsForm(request.POST, request.FILES, instance=settings_obj)
    if form.is_valid():
        form.save()
        messages.success(request, "Checkout payment instructions updated.")
    else:
        # Surface the exact validation problem instead of hiding it behind a generic message.
        details = []
        for field, errors in form.errors.items():
            label = "General" if field == "__all__" else form.fields.get(field, None)
            label = getattr(label, "label", None) or ("General" if field == "__all__" else field.replace("_", " ").title())
            details.append(f"{label}: {', '.join(str(error) for error in errors)}")
        message = "Could not update payment settings."
        if details:
            message += " " + " | ".join(details)
        messages.error(request, message)
    return redirect("/staff/?tab=payments#payments-panel")
