"""Small, optional integration for Meta's official WhatsApp Cloud API."""
import json
import logging
import re
import urllib.error
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)


def normalize_phone(value):
    """Return E.164 digits (without +), using configured country code for local numbers."""
    compact = re.sub(r"[\s().-]", "", str(value or ""))
    if compact.startswith("00"):
        compact = compact[2:]
    digits = re.sub(r"\D", "", compact)
    if len(digits) == 10 and getattr(settings, "WHATSAPP_DEFAULT_COUNTRY_CODE", ""):
        digits = f"{settings.WHATSAPP_DEFAULT_COUNTRY_CODE}{digits}"
    if not (8 <= len(digits) <= 15):
        return ""
    return digits


def _enabled():
    return bool(
        getattr(settings, "WHATSAPP_ENABLED", False)
        and getattr(settings, "WHATSAPP_ACCESS_TOKEN", "")
        and getattr(settings, "WHATSAPP_PHONE_NUMBER_ID", "")
        and getattr(settings, "WHATSAPP_API_VERSION", "")
    )


def send_template(recipient, template_name, body_parameters, *, language=None):
    """Send one approved template. Failures are logged and never raised to checkout."""
    if not _enabled():
        logger.info("WhatsApp is not configured/enabled; skipped template %s.", template_name)
        return False
    phone = normalize_phone(recipient)
    if not phone:
        logger.warning("WhatsApp message skipped because recipient phone number is invalid.")
        return False

    version = settings.WHATSAPP_API_VERSION.strip()
    if not version.startswith("v"):
        version = "v" + version
    url = f"https://graph.facebook.com/{version}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": phone,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language or settings.WHATSAPP_TEMPLATE_LANGUAGE},
            "components": [{
                "type": "body",
                "parameters": [{"type": "text", "text": str(value)[:1024]} for value in body_parameters],
            }],
        },
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            result = json.loads(response.read().decode("utf-8"))
        message_id = (result.get("messages") or [{}])[0].get("id", "")
        logger.info("WhatsApp template %s accepted for recipient ending %s; message id=%s", template_name, phone[-4:], message_id)
        return True
    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8")[:1500]
        except Exception:
            detail = str(exc)
        logger.error("WhatsApp API rejected template %s (HTTP %s): %s", template_name, exc.code, detail)
    except Exception:
        logger.exception("WhatsApp template %s could not be sent.", template_name)
    return False


def _items_summary(order):
    parts = []
    for item in order.items.all():
        parts.append(f"{item.product_name} x {item.quantity} (Rs. {item.line_total})")
    summary = "; ".join(parts) or "Order items unavailable"
    return summary[:1024]


def send_customer_order_confirmation(order):
    if not getattr(settings, "WHATSAPP_NOTIFY_CUSTOMERS", False) or not order.whatsapp_opt_in:
        return False
    return send_template(
        order.contact,
        settings.WHATSAPP_TEMPLATE_ORDER_CONFIRMATION,
        [order.username, str(order.pk)[:8].upper(), _items_summary(order), f"Rs. {order.total_amount}"],
    )


def send_admin_new_order(order, recipients):
    if not getattr(settings, "WHATSAPP_NOTIFY_ADMINS", False):
        return
    params = [
        order.username,
        str(order.pk)[:8].upper(),
        order.contact,
        order.address[:1024],
        _items_summary(order),
        f"Rs. {order.total_amount}",
        order.get_status_display(),
        order.get_payment_status_display(),
    ]
    for recipient in recipients:
        send_template(recipient, settings.WHATSAPP_TEMPLATE_ADMIN_NEW_ORDER, params)


def send_customer_order_update(order, changes):
    if not getattr(settings, "WHATSAPP_NOTIFY_CUSTOMERS", False) or not order.whatsapp_opt_in:
        return False
    summary = "; ".join(
        f"{change['label']}: {change['old_value']} -> {change['new_value']}" for change in changes
    ) or "Your order details have been updated."
    return send_template(
        order.contact,
        settings.WHATSAPP_TEMPLATE_ORDER_UPDATE,
        [order.username, str(order.pk)[:8].upper(), summary, order.get_status_display(), order.get_payment_status_display()],
    )
