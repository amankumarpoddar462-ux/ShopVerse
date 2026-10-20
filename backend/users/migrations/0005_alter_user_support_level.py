from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_merge_20261019_1234'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='support_level',
            field=models.CharField(default='agent', max_length=20),
        ),
    ]
