from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("store", "0003_product_video_file")]

    operations = [
        migrations.CreateModel(
            name="StorePaymentSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("instructions", models.TextField(blank=True, default="Please scan the QR code to pay. Include your order number in the payment note and share the payment confirmation with our team.", help_text="Shown to customers during checkout. Do not include confidential account credentials.")),
                ("qr_code", models.ImageField(blank=True, upload_to="payment_qr/")),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"verbose_name": "Store payment settings", "verbose_name_plural": "Store payment settings"},
        ),
    ]
