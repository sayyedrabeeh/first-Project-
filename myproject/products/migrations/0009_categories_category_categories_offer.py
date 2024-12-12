# Generated by Django 5.1.3 on 2024-11-30 10:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0008_wishlist'),
    ]

    operations = [
        migrations.AddField(
            model_name='categories',
            name='category',
            field=models.CharField(default='none', max_length=100),
        ),
        migrations.AddField(
            model_name='categories',
            name='offer',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=8),
        ),
    ]
