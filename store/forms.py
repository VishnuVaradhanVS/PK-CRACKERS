from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm
from django.contrib.auth.models import User
from pathlib import Path
import re
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from .models import Order, Product, StorePaymentSettings

class CheckoutForm(forms.Form):
    username = forms.CharField(max_length=120, label="Full name")
    contact = forms.CharField(max_length=40, label="Contact number", help_text="Include your country code (for example, +91) for WhatsApp updates.")
    address = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), label="Delivery address")
    whatsapp_opt_in = forms.BooleanField(
        required=False,
        label="I agree to receive order and payment updates from PK CRACKERS on WhatsApp at this number.",
        widget=forms.CheckboxInput(attrs={"class": "whatsapp-opt-in-checkbox"}),
    )



class EmailOrUsernameAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="Email address or username",
        widget=forms.TextInput(attrs={
            "autofocus": True,
            "autocomplete": "username",
            "placeholder": "Email address or username",
        }),
    )

    def clean(self):
        identifier = self.cleaned_data.get("username", "").strip()
        if identifier and "@" in identifier:
            matched = User._default_manager.filter(email__iexact=identifier).first()
            if matched:
                self.cleaned_data["username"] = matched.get_username()
        return super().clean()


class ExistingAccountPasswordResetForm(PasswordResetForm):
    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if not User._default_manager.filter(email__iexact=email, is_active=True).exists():
            raise forms.ValidationError(
                "No active PK CRACKERS account is associated with this email address. "
                "Check the address or create an account."
            )
        return email


class SignupForm(forms.Form):
    username = forms.CharField(max_length=150, strip=True)
    email = forms.EmailField()
    password1 = forms.CharField(widget=forms.PasswordInput, min_length=10, label="Password")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm password")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User._default_manager.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "An account with this email address already exists. Please log in or reset your password."
            )
        return email

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        # Treat usernames case-insensitively to avoid confusing duplicates.
        if User._default_manager.filter(username__iexact=username).exists():
            raise forms.ValidationError(
                "This username is already in use. Please choose another username."
            )
        return username

    def clean(self):
        data = super().clean()
        if data.get("password1") and data.get("password2") and data["password1"] != data["password2"]:
            self.add_error("password2", "Passwords do not match.")
        return data


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["name", "category", "description", "cost", "image", "image_url", "video_file", "stock", "is_active"]
        widgets = {
            "image": forms.FileInput(attrs={"accept": "image/*"}),
            "video_file": forms.FileInput(attrs={"accept": "video/mp4,video/webm,video/ogg,.mp4,.webm,.ogv,.ogg"}),
        }

    def clean_video_file(self):
        video = self.cleaned_data.get("video_file")
        if not video:
            return video
        allowed_extensions = {".mp4", ".webm", ".ogv", ".ogg"}
        extension = Path(video.name).suffix.lower()
        if extension not in allowed_extensions:
            raise forms.ValidationError("Upload an MP4, WebM or Ogg video file.")
        if video.size > 100 * 1024 * 1024:
            raise forms.ValidationError("Video files must be 100 MB or smaller.")
        return video


class StorePaymentSettingsForm(forms.ModelForm):
    notification_emails = forms.CharField(
        required=False,
        label="Admin notification email addresses",
        help_text="Enter one or more addresses separated by commas, semicolons, or new lines.",
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "admin@example.com, orders@example.com"}),
    )
    whatsapp_admin_numbers = forms.CharField(
        required=False,
        label="Admin WhatsApp numbers",
        help_text="Include country code, e.g. +919876543210. Separate multiple numbers with commas, semicolons, or new lines. Add only admins who have agreed to receive alerts.",
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "+919876543210, +919812345678"}),
    )

    class Meta:
        model = StorePaymentSettings
        fields = ["instructions", "qr_code", "notification_emails", "whatsapp_admin_numbers"]
        widgets = {
            "instructions": forms.Textarea(attrs={"rows": 5, "placeholder": "Enter UPI/payment instructions for customers"}),
            "qr_code": forms.FileInput(attrs={"accept": "image/*"}),
        }

    def clean_notification_emails(self):
        raw = self.cleaned_data.get("notification_emails", "")
        addresses = [part.strip() for part in re.split(r"[,;\n]+", raw) if part.strip()]
        invalid = []
        for address in addresses:
            try:
                validate_email(address)
            except ValidationError:
                invalid.append(address)
        if invalid:
            raise forms.ValidationError("Invalid email address(es): " + ", ".join(invalid))
        # Deduplicate without changing the entered case/order.
        unique = list(dict.fromkeys(addresses))
        return "\n".join(unique)

    def clean_whatsapp_admin_numbers(self):
        raw = self.cleaned_data.get("whatsapp_admin_numbers", "")
        numbers = [part.strip() for part in re.split(r"[,;\n]+", raw) if part.strip()]
        normalized = []
        invalid = []
        for number in numbers:
            compact = re.sub(r"[\s().-]", "", number)
            if compact.startswith("00"):
                compact = "+" + compact[2:]
            if compact.startswith("+"):
                digits = compact[1:]
            else:
                digits = compact
            if not digits.isdigit() or not (8 <= len(digits) <= 15):
                invalid.append(number)
                continue
            value = "+" + digits
            if value not in normalized:
                normalized.append(value)
        if invalid:
            raise forms.ValidationError("Invalid WhatsApp number(s): " + ", ".join(invalid) + ". Include country code, e.g. +919876543210.")
        return "\n".join(normalized)

    def clean_qr_code(self):
        image = self.cleaned_data.get("qr_code")
        if image and image.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Payment QR images must be 5 MB or smaller.")
        return image
