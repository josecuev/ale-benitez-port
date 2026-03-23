"""
Management command: agrega PageViews de más de 90 días en PageViewMonthly
y luego los elimina para mantener la tabla liviana.

Uso:
    python manage.py cleanup_pageviews
    python manage.py cleanup_pageviews --dry-run

Cron recomendado (semanal los domingos a las 3 AM):
    0 3 * * 0 docker exec ab-django python manage.py cleanup_pageviews
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.utils import timezone
from datetime import timedelta

from app_analytics.models import PageView, PageViewMonthly


class Command(BaseCommand):
    help = 'Agrega PageViews de más de 90 días en PageViewMonthly y los elimina'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Muestra qué se haría sin ejecutar cambios',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        cutoff = timezone.now() - timedelta(days=90)

        old_views = PageView.objects.filter(timestamp__lt=cutoff)
        total_old = old_views.count()

        if total_old == 0:
            self.stdout.write('No hay registros con más de 90 días. Nada que hacer.')
            return

        self.stdout.write(f'Encontrados {total_old} registros con más de 90 días (hasta {cutoff:%Y-%m-%d}).')

        # Agregar por página, año y mes
        aggregated = (
            old_views
            .annotate(month_trunc=TruncMonth('timestamp'))
            .values('page', 'month_trunc')
            .annotate(
                total=Count('id'),
                unique=Count('ip_hash', distinct=True),
            )
        )

        if dry_run:
            self.stdout.write('[DRY RUN] Se agregarían los siguientes datos:')
            for row in aggregated:
                self.stdout.write(
                    f"  {row['page']} — {row['month_trunc']:%Y/%m}: "
                    f"{row['total']} vistas, {row['unique']} IPs únicas"
                )
            self.stdout.write(f'[DRY RUN] Se eliminarían {total_old} registros.')
            return

        with transaction.atomic():
            for row in aggregated:
                dt = row['month_trunc']
                obj, _ = PageViewMonthly.objects.get_or_create(
                    page=row['page'],
                    year=dt.year,
                    month=dt.month,
                    defaults={'total_views': 0, 'unique_visitors': 0},
                )
                obj.total_views += row['total']
                obj.unique_visitors += row['unique']
                obj.save()

            deleted_count, _ = old_views.delete()

        self.stdout.write(
            self.style.SUCCESS(
                f'Listo: {deleted_count} registros eliminados, datos agregados a histórico mensual.'
            )
        )
