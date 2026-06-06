from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('desk', '0012_loginattempt'),
    ]

    operations = [
        migrations.RenameField(
            model_name='loginattempt',
            old_name='username',
            new_name='username_or_phone',
        ),
    ]
