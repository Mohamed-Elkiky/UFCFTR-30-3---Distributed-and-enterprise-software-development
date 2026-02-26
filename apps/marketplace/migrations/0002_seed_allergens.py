# apps/marketplace/migrations/0002_seed_allergens.py
"""
Data migration to seed the 14 UK major allergens required by food safety law.
Required for TC-015 (allergen display on product detail).
"""

from django.db import migrations


ALLERGENS = [
    "Celery",
    "Cereals containing gluten (wheat, rye, barley, oats)",
    "Crustaceans",
    "Eggs",
    "Fish",
    "Lupin",
    "Milk",
    "Molluscs",
    "Mustard",
    "Nuts (almonds, hazelnuts, walnuts, cashews, pecans, Brazil nuts, pistachios, macadamia nuts)",
    "Peanuts",
    "Sesame",
    "Soybeans",
    "Sulphur dioxide and sulphites",
]


def seed_allergens(apps, schema_editor):
    Allergen = apps.get_model("marketplace", "Allergen")
    for name in ALLERGENS:
        Allergen.objects.get_or_create(name=name)


def reverse_seed_allergens(apps, schema_editor):
    Allergen = apps.get_model("marketplace", "Allergen")
    Allergen.objects.filter(name__in=ALLERGENS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("marketplace", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_allergens, reverse_seed_allergens),
    ]