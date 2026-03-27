from django.db import migrations, models


def set_duration_minutes(apps, schema_editor):
    FractaboxPackage = apps.get_model('app_fractalia', 'FractaboxPackage')
    # Mapeo basado en los paquetes definidos en migraciones 0010 y 0014
    duration_map = {
        1: 45,   # 45 min
        2: 90,   # 1h 30min
        3: 180,  # 3h
    }
    for slots, minutes in duration_map.items():
        FractaboxPackage.objects.filter(slots_to_block=slots).update(duration_minutes=minutes)


def reverse_duration_minutes(apps, schema_editor):
    FractaboxPackage = apps.get_model('app_fractalia', 'FractaboxPackage')
    FractaboxPackage.objects.all().update(duration_minutes=None)


class Migration(migrations.Migration):

    dependencies = [
        ('app_fractalia', '0017_product_descriptions'),
    ]

    operations = [
        migrations.AddField(
            model_name='fractaboxpackage',
            name='duration_minutes',
            field=models.PositiveIntegerField(
                null=True,
                blank=True,
                verbose_name='Duración (minutos)',
                help_text='Duración real del paquete en minutos, para mostrar la hora de fin correctamente.',
            ),
        ),
        migrations.RunPython(set_duration_minutes, reverse_duration_minutes),
    ]
