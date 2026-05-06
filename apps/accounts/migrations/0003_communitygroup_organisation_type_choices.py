# Generated migration to add choices to organisation_type field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_communitygroup_restaurant'),  # Adjust based on latest migration
    ]

    operations = [
        migrations.AlterField(
            model_name='communitygroupprofile',
            name='organisation_type',
            field=models.CharField(
                choices=[
                    ('food_bank', 'Food Bank'),
                    ('school', 'School/Educational'),
                    ('community_center', 'Community Center'),
                    ('charity', 'Charity/Non-profit'),
                    ('restaurant', 'Restaurant/Catering'),
                    ('other', 'Other'),
                ],
                default='other',
                help_text='Type of organisation',
                max_length=100,
            ),
        ),
    ]
