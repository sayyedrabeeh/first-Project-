# Generated by Django 5.1.3 on 2024-12-19 05:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0007_order_payment'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='payment',
            field=models.CharField(default='Failure', max_length=20),
        ),
    ]
