# Generated by Django 3.2.15 on 2023-02-13 18:35

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('foodcartapp', '0058_auto_20230128_1855'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orderkit',
            name='order',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='order_kits', to='foodcartapp.order', verbose_name='заказ'),
        ),
        migrations.AlterField(
            model_name='orderkit',
            name='product',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='order_kits', to='foodcartapp.product', verbose_name='продукт'),
        ),
    ]
