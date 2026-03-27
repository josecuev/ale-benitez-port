from django.db import migrations


def migrate_data(apps, schema_editor):
    Resource = apps.get_model('app_fractalia', 'Resource')
    WeeklyAvailability = apps.get_model('app_fractalia', 'WeeklyAvailability')
    Booking = apps.get_model('app_fractalia', 'Booking')
    PendingBooking = apps.get_model('app_fractalia', 'PendingBooking')
    Product = apps.get_model('app_fractalia', 'Product')
    FractaboxPackage = apps.get_model('app_fractalia', 'FractaboxPackage')

    # Recurso principal (el estudio físico)
    main_resource = Resource.objects.filter(active=True).order_by('id').first()
    if not main_resource:
        return

    # Consolidar recurso FractaBox duplicado (creado por migración 0007)
    fractabox_resource = Resource.objects.filter(name='FractaBox').exclude(id=main_resource.id).first()
    if fractabox_resource:
        Booking.objects.filter(resource=fractabox_resource).update(resource=main_resource)
        PendingBooking.objects.filter(resource=fractabox_resource).update(resource=main_resource)
        WeeklyAvailability.objects.filter(resource=fractabox_resource).delete()
        fractabox_resource.delete()

    # Crear los 3 productos
    Product.objects.create(
        resource=main_resource,
        name='Alquiler de Estudio',
        product_type='ALQUILER',
        is_public=True,
        is_active=True,
    )
    fractabox_product = Product.objects.create(
        resource=main_resource,
        name='Fractabox',
        product_type='FRACTABOX',
        is_public=True,
        is_active=True,
    )
    Product.objects.create(
        resource=main_resource,
        name='Sesión Fotográfica',
        product_type='FOTO',
        is_public=False,
        is_active=True,
    )

    # Crear los 3 paquetes de Fractabox
    FractaboxPackage.objects.create(product=fractabox_product, label='45 minutos', slots_to_block=1, order=1, is_active=True)
    FractaboxPackage.objects.create(product=fractabox_product, label='1:30 horas', slots_to_block=2, order=2, is_active=True)
    FractaboxPackage.objects.create(product=fractabox_product, label='3 horas', slots_to_block=3, order=3, is_active=True)


def rollback_data(apps, schema_editor):
    Product = apps.get_model('app_fractalia', 'Product')
    Product.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ('app_fractalia', '0009_add_products'),
    ]

    operations = [
        migrations.RunPython(migrate_data, rollback_data),
    ]
