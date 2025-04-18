from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0005_auto_20250418_1459'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='oauthprovider',
            name='is_anonymous_user',
        ),
        migrations.AddField(
            model_name='user',
            name='is_anonymous_user',
            field=models.BooleanField(default=False, verbose_name='是否为匿名用户'),
        ),
    ]
