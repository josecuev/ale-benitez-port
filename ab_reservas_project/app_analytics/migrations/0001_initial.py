from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='PageView',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('page', models.CharField(
                    choices=[
                        ('portfolio', 'Portfolio (React)'),
                        ('links', 'Links'),
                        ('fractalia_calendar', 'Calendario Fractalia'),
                        ('fractalia_booking', 'Formulario de reserva'),
                        ('fractalia_confirmation', 'Confirmación de reserva'),
                    ],
                    db_index=True,
                    max_length=50,
                    verbose_name='Página',
                )),
                ('timestamp', models.DateTimeField(
                    db_index=True,
                    default=django.utils.timezone.now,
                    verbose_name='Fecha y hora',
                )),
                ('ip_hash', models.CharField(db_index=True, max_length=64, verbose_name='IP (SHA-256)')),
                ('referrer', models.CharField(blank=True, default='', max_length=100, verbose_name='Referrer')),
                ('user_agent_hash', models.CharField(blank=True, default='', max_length=64, verbose_name='User-Agent (hash)')),
            ],
            options={
                'verbose_name': 'Vista de página',
                'verbose_name_plural': 'Vistas de páginas',
                'ordering': ['-timestamp'],
                'indexes': [
                    models.Index(fields=['page', 'timestamp'], name='app_analyti_page_ts_idx'),
                    models.Index(fields=['ip_hash', 'timestamp'], name='app_analyti_ip_ts_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='PageViewMonthly',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('page', models.CharField(
                    choices=[
                        ('portfolio', 'Portfolio (React)'),
                        ('links', 'Links'),
                        ('fractalia_calendar', 'Calendario Fractalia'),
                        ('fractalia_booking', 'Formulario de reserva'),
                        ('fractalia_confirmation', 'Confirmación de reserva'),
                    ],
                    max_length=50,
                    verbose_name='Página',
                )),
                ('year', models.IntegerField(verbose_name='Año')),
                ('month', models.IntegerField(verbose_name='Mes')),
                ('total_views', models.IntegerField(default=0, verbose_name='Total vistas')),
                ('unique_visitors', models.IntegerField(default=0, verbose_name='Visitantes únicos (IPs únicas)')),
            ],
            options={
                'verbose_name': 'Vista mensual agregada',
                'verbose_name_plural': 'Vistas mensuales agregadas',
                'ordering': ['-year', '-month'],
                'unique_together': {('page', 'year', 'month')},
            },
        ),
    ]
