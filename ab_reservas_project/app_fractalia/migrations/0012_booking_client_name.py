from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('app_fractalia', '0011_normalize_fractabox_package_labels'),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='client_name',
            field=models.CharField(blank=True, max_length=100, verbose_name='Cliente'),
        ),
    ]
