# Generated by Django 5.1.3 on 2024-11-24 11:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0006_remove_product_offer_product_discount_percentage'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='product',
            name='discount_percentage',
        ),
        migrations.AddField(
            model_name='product',
            name='offer',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=8),
        ),
        migrations.AddField(
            model_name='product',
            name='original_price',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=8),
        ),
    ]
