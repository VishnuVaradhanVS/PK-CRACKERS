from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ("store", "0008_unique_user_email"),
    ]

    operations = [
        migrations.CreateModel(
            name="EmailVerificationOTP",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("email", models.EmailField(max_length=254, unique=True)),
                ("code_hash", models.CharField(max_length=256)),
                ("expires_at", models.DateTimeField()),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("attempts", models.PositiveSmallIntegerField(default=0)),
            ],
            options={
                "verbose_name": "Email verification code",
                "verbose_name_plural": "Email verification codes",
            },
        ),
    ]
