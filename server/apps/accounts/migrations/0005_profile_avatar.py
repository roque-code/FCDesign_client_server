from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0004_user_email_confirmed"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="avatar",
            field=models.BinaryField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="profile",
            name="avatar_type",
            field=models.CharField(blank=True, max_length=16),
        ),
    ]
