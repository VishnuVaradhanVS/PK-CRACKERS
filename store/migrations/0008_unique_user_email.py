from django.conf import settings
from django.db import migrations, models
from django.db.models.functions import Lower


INDEX_NAME = "auth_user_email_ci_unique_nonempty"


def enforce_case_insensitive_email_uniqueness(apps, schema_editor):
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    duplicates = (
        User.objects.exclude(email="")
        .annotate(normalized_email=Lower("email"))
        .values("normalized_email")
        .annotate(total=models.Count("id"))
        .filter(total__gt=1)
    )
    if duplicates.exists():
        examples = ", ".join(item["normalized_email"] for item in duplicates[:10])
        raise RuntimeError(
            "Cannot enforce unique account emails because duplicate email addresses "
            f"already exist: {examples}. Resolve these accounts before retrying migrations."
        )

    if schema_editor.connection.vendor not in {"postgresql", "sqlite"}:
        raise RuntimeError(
            "The case-insensitive email uniqueness migration currently supports PostgreSQL and SQLite."
        )

    table = schema_editor.quote_name(User._meta.db_table)
    email_column = schema_editor.quote_name(User._meta.get_field("email").column)
    index = schema_editor.quote_name(INDEX_NAME)
    schema_editor.execute(
        f"CREATE UNIQUE INDEX {index} ON {table} (LOWER({email_column})) "
        f"WHERE {email_column} <> ''"
    )


def remove_email_unique_index(apps, schema_editor):
    index = schema_editor.quote_name(INDEX_NAME)
    schema_editor.execute(f"DROP INDEX IF EXISTS {index}")


class Migration(migrations.Migration):
    dependencies = [
        ("store", "0007_whatsapp_notifications"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(
            enforce_case_insensitive_email_uniqueness,
            remove_email_unique_index,
        ),
    ]
