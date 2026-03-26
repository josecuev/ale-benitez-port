from django.db import migrations


def forward(apps, schema_editor):
    FractaboxPackage = apps.get_model('app_fractalia', 'FractaboxPackage')
    FractaboxPackage.objects.filter(slots_to_block=1).update(label='45 min')
    FractaboxPackage.objects.filter(slots_to_block=2).update(label='1 h 30 min')
    FractaboxPackage.objects.filter(slots_to_block=3).update(label='3 h')


def reverse(apps, schema_editor):
    FractaboxPackage = apps.get_model('app_fractalia', 'FractaboxPackage')
    FractaboxPackage.objects.filter(slots_to_block=1).update(label='45 minutos')
    FractaboxPackage.objects.filter(slots_to_block=2).update(label='1.5 h')
    FractaboxPackage.objects.filter(slots_to_block=3).update(label='3h')


class Migration(migrations.Migration):
    dependencies = [
        ('app_fractalia', '0013_fix_fractabox_label_2'),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
