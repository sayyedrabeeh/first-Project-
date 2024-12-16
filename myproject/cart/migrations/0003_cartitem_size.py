# Generated by Django 5.1.3 on 2024-11-16 10:56

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cart', '0002_initial'),
        ('products', '0003_remove_product_stock_size_stock_alter_product_price'),
    ]

    operations = [
        migrations.AddField(
            model_name='cartitem',
            name='size',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='products.size'),
        ),
    ]