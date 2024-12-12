# Generated by Django 5.1.3 on 2024-11-16 12:44

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0004_alter_orderitem_size'),
        ('products', '0003_remove_product_stock_size_stock_alter_product_price'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orderitem',
            name='size',
            field=models.ForeignKey( on_delete=django.db.models.deletion.CASCADE, related_name='order_items', to='products.size'),
        ),
    ]
