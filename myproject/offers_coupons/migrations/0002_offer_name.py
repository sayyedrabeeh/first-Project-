# Generated by Django 5.1.3 on 2024-11-24 07:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('offers_coupons', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='offer',
            name='name',
            field=models.CharField(default='offer', max_length=255),
        ),
    ]
