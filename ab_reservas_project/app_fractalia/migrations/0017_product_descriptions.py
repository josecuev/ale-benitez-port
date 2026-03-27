from django.db import migrations, models


FRACTABOX_DESCRIPTION = (
    'Un estudio privado de mirror content donde creás tus propias fotos con control total, '
    'sin fotógrafo y con visualización en tiempo real. Ideal para creadores y profesionales '
    'que buscan una experiencia autónoma, rápida y enfocada en producir contenido de alto nivel.'
)

ALQUILER_DESCRIPTION = (
    'Un espacio creativo multidisciplinario con luz natural, arquitectura abierta y ambientaciones '
    'versátiles, diseñado para potenciar producciones fotográficas, audiovisuales y colaborativas. '
    'Más que un estudio, es un entorno pensado para inspirar y adaptarse a distintos proyectos creativos.'
)


def forward(apps, schema_editor):
    Product = apps.get_model('app_fractalia', 'Product')
    Product.objects.filter(product_type='FRACTABOX').update(description=FRACTABOX_DESCRIPTION)
    Product.objects.filter(product_type='ALQUILER').update(description=ALQUILER_DESCRIPTION)


def reverse(apps, schema_editor):
    Product = apps.get_model('app_fractalia', 'Product')
    Product.objects.filter(product_type='FRACTABOX').update(description='')
    Product.objects.filter(product_type='ALQUILER').update(description='')


class Migration(migrations.Migration):
    dependencies = [
        ('app_fractalia', '0016_rename_photo_product'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='description',
            field=models.TextField(blank=True, default='', verbose_name='Descripción'),
        ),
        migrations.RunPython(forward, reverse),
    ]
