from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("store", "0002_product_image_order_payment_status_and_more")]

    operations = [
        migrations.AddField(
            model_name="product",
            name="video_file",
            field=models.FileField(blank=True, upload_to="product_videos/"),
        ),
    ]
