from django.db import migrations


def add_fractabox(apps, schema_editor):
    Resource = apps.get_model('app_fractalia', 'Resource')
    WeeklyAvailability = apps.get_model('app_fractalia', 'WeeklyAvailability')

    estudio = Resource.objects.filter(active=True).first()
    if not estudio:
        return

    fractabox, created = Resource.objects.get_or_create(
        name='FractaBox',
        defaults={
            'active': True,
            'whatsapp_number': estudio.whatsapp_number,
        }
    )

    if created:
        for avail in WeeklyAvailability.objects.filter(resource=estudio):
            WeeklyAvailability.objects.get_or_create(
                resource=fractabox,
                weekday=avail.weekday,
                defaults={
                    'start_time': avail.start_time,
                    'end_time': avail.end_time,
                }
            )


def remove_fractabox(apps, schema_editor):
    Resource = apps.get_model('app_fractalia', 'Resource')
    Resource.objects.filter(name='FractaBox').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('app_fractalia', '0006_booking_client_phone_pendingbooking_client_phone_and_more'),
    ]

    operations = [
        migrations.RunPython(add_fractabox, remove_fractabox),
    ]
