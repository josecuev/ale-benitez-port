from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('app_fractalia', '0014_exact_fractabox_labels'),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='reservation_code',
            field=models.CharField(blank=True, max_length=4, null=True, unique=True, verbose_name='Código'),
        ),
    ]
