from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("game", "0023_seed_gear_slots"),
    ]

    operations = [
        migrations.AddField(
            model_name="character",
            name="vault_gold",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
