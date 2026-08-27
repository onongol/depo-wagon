from django.db import migrations


def create_email_addresses(apps, schema_editor) -> None:
    """Give every pre-existing user a verified allauth EmailAddress.

    ``ACCOUNT_EMAIL_VERIFICATION = "mandatory"`` locks out any account that has
    no verified EmailAddress row, and users created before allauth was adopted
    have none — without this backfill every existing employee would land on the
    "confirm your email" page and be unable to leave it.

    Marking them verified rather than sending confirmations is right here: each
    of these accounts was created by the Telegram bot only after an emailed OTP
    proved the person reads mail at that address, which is the same fact a
    confirmation link establishes.
    """
    User = apps.get_model("users", "CustomUser")
    EmailAddress = apps.get_model("account", "EmailAddress")

    existing = set(
        EmailAddress.objects.values_list("user_id", flat=True).distinct()
    )
    EmailAddress.objects.bulk_create(
        [
            EmailAddress(
                user_id=user.pk, email=user.email, verified=True, primary=True
            )
            for user in User.objects.exclude(email="").exclude(email=None)
            if user.pk not in existing
        ]
    )


def drop_email_addresses(apps, schema_editor) -> None:
    """Reversing only makes sense as a no-op.

    Deleting rows here would also delete addresses added through allauth after
    this migration ran, so leave the table alone; the rows are harmless without
    allauth's verification enforcement.
    """


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0001_initial"),
        ("account", "0009_emailaddress_unique_primary_email"),
    ]

    operations = [
        migrations.RunPython(create_email_addresses, drop_email_addresses),
    ]
