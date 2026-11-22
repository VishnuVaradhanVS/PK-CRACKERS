from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0005_cartitem"),
    ]

    operations = [
        migrations.AddField(
            model_name="storepaymentsettings",
            name="notification_emails",
            field=models.TextField(
                blank=True,
                help_text="Comma-, semicolon-, or line-separated email addresses notified when a new order is placed.",
            ),
        ),
    ]
