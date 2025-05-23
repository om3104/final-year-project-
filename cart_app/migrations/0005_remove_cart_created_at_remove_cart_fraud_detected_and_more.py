# Generated by Django 4.2.3 on 2025-05-05 15:53

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('cart_app', '0004_cart_fraud_detected_cart_fraud_message_cartweight'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='cart',
            name='created_at',
        ),
        migrations.RemoveField(
            model_name='cart',
            name='fraud_detected',
        ),
        migrations.RemoveField(
            model_name='cart',
            name='fraud_message',
        ),
        migrations.RemoveField(
            model_name='cart',
            name='is_active',
        ),
        migrations.RemoveField(
            model_name='cart',
            name='updated_at',
        ),
        migrations.AddField(
            model_name='cart',
            name='user_cart',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='items', to='cart_app.cartitem'),
            preserve_default=False,
        ),
    ]
