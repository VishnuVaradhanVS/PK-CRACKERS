from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("store", "0009_emailverificationotp"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="category",
            field=models.CharField(blank=True, db_index=True, default="", max_length=80),
        ),
    ]
