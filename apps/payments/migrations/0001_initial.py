# Generated migration for TC-007 / TC-012 payment schema

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("accounts", "0001_initial"),
        ("orders", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CommissionPolicy",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("rate_bp", models.IntegerField(help_text="Rate in basis points; 500 = 5%")),
                ("valid_from", models.DateField()),
                ("valid_to", models.DateField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-valid_from"], "verbose_name_plural": "Commission policies"},
        ),
        migrations.CreateModel(
            name="SettlementWeek",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("week_start", models.DateField(unique=True)),
                ("week_end", models.DateField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-week_start"]},
        ),
        migrations.CreateModel(
            name="PaymentTransaction",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("provider", models.CharField(max_length=50)),
                ("provider_ref", models.CharField(max_length=255)),
                ("status", models.CharField(
                    choices=[
                        ("initiated", "Initiated"),
                        ("authorised", "Authorised"),
                        ("captured", "Captured"),
                        ("failed", "Failed"),
                        ("refunded", "Refunded"),
                    ],
                    default="initiated",
                    max_length=20,
                )),
                ("amount_pence", models.IntegerField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("customer_order", models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="payment",
                    to="orders.customerorder",
                )),
            ],
        ),
        migrations.CreateModel(
            name="OrderCommission",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("gross_pence", models.IntegerField()),
                ("commission_pence", models.IntegerField()),
                ("net_pence", models.IntegerField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("customer_order", models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="commission",
                    to="orders.customerorder",
                )),
                ("commission_policy", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="order_commissions",
                    to="payments.commissionpolicy",
                )),
            ],
        ),
        migrations.CreateModel(
            name="ProducerSettlement",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("commission_pence", models.IntegerField(default=0)),
                ("payout_pence", models.IntegerField(default=0)),
                ("status", models.CharField(
                    choices=[("pending", "Pending"), ("processed", "Processed")],
                    default="pending",
                    max_length=20,
                )),
                ("processed_ref", models.CharField(blank=True, default="", max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("settlement_week", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="producer_settlements",
                    to="payments.settlementweek",
                )),
                ("producer", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="settlements",
                    to="accounts.producerprofile",
                )),
            ],
            options={"ordering": ["-created_at"], "unique_together": {("settlement_week", "producer")}},
        ),
        migrations.CreateModel(
            name="ProducerOrderSettlementLink",
            fields=[
                ("producer_order", models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    primary_key=True,
                    related_name="settlement_link",
                    serialize=False,
                    to="orders.producerorder",
                )),
                ("producer_settlement", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="order_links",
                    to="payments.producersettlement",
                )),
            ],
        ),
    ]
