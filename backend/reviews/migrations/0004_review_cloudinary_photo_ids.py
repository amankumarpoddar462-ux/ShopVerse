from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reviews', '0003_review_order'),
    ]

    operations = [
        migrations.AddField(
            model_name='review',
            name='photo_public_id_1',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='review',
            name='photo_public_id_2',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='review',
            name='photo_public_id_3',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
    ]
