from django.db import migrations


def lowercase(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    taken = set(User.objects.values_list("email", flat=True))
    for user in User.objects.all().only("id", "email"):
        clean = user.email.strip().casefold()
        if clean == user.email or clean in taken:
            continue
        taken.discard(user.email)
        taken.add(clean)
        User.objects.filter(pk=user.pk).update(email=clean)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0008_uniq_user_email_ci"),
    ]

    operations = [
        migrations.RunPython(lowercase, migrations.RunPython.noop),
    ]
