from django.db import migrations
import datetime


def create_default_commission_policy(apps, schema_editor):
    CommissionPolicy = apps.get_model("payments", "CommissionPolicy")

    exists = CommissionPolicy.objects.filter(
        rate_bp=500,
        valid_from=datetime.date(2020, 1, 1),
        valid_to__isnull=True,
    ).exists()

    if not exists:
        CommissionPolicy.objects.create(
            rate_bp=500,
            valid_from=datetime.date(2020, 1, 1),
            valid_to=None,
        )


def remove_default_commission_policy(apps, schema_editor):
    CommissionPolicy = apps.get_model("payments", "CommissionPolicy")
    CommissionPolicy.objects.filter(
        rate_bp=500,
        valid_from=datetime.date(2020, 1, 1),
        valid_to__isnull=True,
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            create_default_commission_policy,
            remove_default_commission_policy,
        ),
    ]