from django.db import migrations


def forward(apps, schema_editor):
    FractaboxPackage = apps.get_model('app_fractalia', 'FractaboxPackage')
    FractaboxPackage.objects.filter(slots_to_block=2).update(label='1 h 30 min')


def reverse(apps, schema_editor):
    FractaboxPackage = apps.get_model('app_fractalia', 'FractaboxPackage')
    FractaboxPackage.objects.filter(slots_to_block=2).update(label='1.5 h')


class Migration(migrations.Migration):
    dependencies = [
        ('app_fractalia', '0012_booking_client_name'),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
