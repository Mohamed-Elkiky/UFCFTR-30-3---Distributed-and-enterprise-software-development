from django.db import migrations


def backfill_customer_profiles(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    CustomerProfile = apps.get_model("accounts", "CustomerProfile")

    for user in User.objects.filter(role="customer"):
        has_profile = CustomerProfile.objects.filter(user=user).exists()
        if not has_profile:
            default_name = (
                user.email.split("@")[0].replace(".", " ").replace("_", " ").title()
                if user.email else "Customer"
            )

            CustomerProfile.objects.create(
                user=user,
                full_name=default_name,
                street="",
                city="",
                state="",
                postcode="",
                country="",
            )


def reverse_backfill_customer_profiles(apps, schema_editor):
    # Intentionally do nothing on reverse to avoid deleting real profiles.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_remove_customerprofile_delivery_address_and_more"),
    ]

    operations = [
        migrations.RunPython(
            backfill_customer_profiles,
            reverse_backfill_customer_profiles,
        ),
    ]