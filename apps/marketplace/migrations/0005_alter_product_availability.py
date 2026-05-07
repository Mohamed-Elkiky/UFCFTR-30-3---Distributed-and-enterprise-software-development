from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("marketplace", "0004_surplus_deal"),
    ]

    operations = [
        migrations.AlterField(
            model_name="product",
            name="availability",
            field=models.CharField(
                choices=[
                    ("in_season", "In Season"),
                    ("available_year_round", "Available Year Round"),
                    ("out_of_season", "Out of Season"),
                    ("unavailable", "Unavailable"),
                ],
                default="available_year_round",
                max_length=32,
            ),
        ),
    ]