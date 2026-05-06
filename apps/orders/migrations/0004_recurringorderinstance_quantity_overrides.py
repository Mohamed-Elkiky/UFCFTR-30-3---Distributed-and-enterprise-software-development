# Generated migration to add quantity_overrides field to RecurringOrderInstance

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0003_recurringordertemplate_recurringorderitem'),  # Adjust based on latest migration
    ]

    operations = [
        migrations.AddField(
            model_name='recurringorderinstance',
            name='quantity_overrides',
            field=models.JSONField(blank=True, default=dict, help_text='Override quantities for this specific instance. Format: {product_id: quantity}'),
        ),
    ]
