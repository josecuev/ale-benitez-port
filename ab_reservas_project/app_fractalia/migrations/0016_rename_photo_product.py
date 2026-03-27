from django.db import migrations


def forward(apps, schema_editor):
    Product = apps.get_model('app_fractalia', 'Product')
    Product.objects.filter(product_type='FOTO').update(name='Sesion de fotos con Ale B.')


def reverse(apps, schema_editor):
    Product = apps.get_model('app_fractalia', 'Product')
    Product.objects.filter(product_type='FOTO').update(name='Sesión Fotográfica')


class Migration(migrations.Migration):
    dependencies = [
        ('app_fractalia', '0015_booking_reservation_code'),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
