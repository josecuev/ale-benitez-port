from django.db import migrations


def normalize_labels(apps, schema_editor):
    FractaboxPackage = apps.get_model('app_fractalia', 'FractaboxPackage')

    label_map = {
        1: '45 min',
        2: '1 h 30 min',
        3: '3 h',
    }

    for slots_to_block, label in label_map.items():
        FractaboxPackage.objects.filter(slots_to_block=slots_to_block).update(label=label)


def reverse_labels(apps, schema_editor):
    FractaboxPackage = apps.get_model('app_fractalia', 'FractaboxPackage')

    label_map = {
        1: '45 min',
        2: '1 h 30 min',
        3: '3 h',
    }

    for slots_to_block, label in label_map.items():
        FractaboxPackage.objects.filter(slots_to_block=slots_to_block).update(label=label)


class Migration(migrations.Migration):
    dependencies = [
        ('app_fractalia', '0010_data_migration'),
    ]

    operations = [
        migrations.RunPython(normalize_labels, reverse_labels),
    ]
