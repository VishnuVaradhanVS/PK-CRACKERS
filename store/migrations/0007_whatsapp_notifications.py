from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("store", "0006_payment_notification_emails"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="whatsapp_opt_in",
            field=models.BooleanField(default=False, help_text="Customer agreed to receive transactional WhatsApp updates for this order."),
        ),
        migrations.AddField(
            model_name="storepaymentsettings",
            name="whatsapp_admin_numbers",
            field=models.TextField(blank=True, help_text="Admin WhatsApp numbers with country code, separated by commas, semicolons, or new lines. Add only recipients who have opted in."),
        ),
    ]
