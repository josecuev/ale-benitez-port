import hashlib
from django.db import models
from django.utils import timezone


VALID_PAGES = [
    ('portfolio', 'Portfolio (React)'),
    ('links', 'Links'),
    ('fractalia_calendar', 'Calendario Fractalia'),
    ('fractalia_booking', 'Formulario de reserva'),
    ('fractalia_confirmation', 'Confirmación de reserva'),
]

VALID_PAGE_KEYS = {p[0] for p in VALID_PAGES}


class PageView(models.Model):
    """
    Registro individual de cada visita a una página.
    Se mantienen 90 días; luego se agregan a PageViewMonthly y se eliminan.
    """
    page = models.CharField(
        max_length=50,
        choices=VALID_PAGES,
        verbose_name='Página',
        db_index=True,
    )
    timestamp = models.DateTimeField(
        default=timezone.now,
        verbose_name='Fecha y hora',
        db_index=True,
    )
    # IP hasheada con SHA-256 — permite análisis de visitantes únicos sin
    # almacenar datos personales. No es reversible.
    ip_hash = models.CharField(
        max_length=64,
        verbose_name='IP (SHA-256)',
        db_index=True,
    )
    # Referrer hasheado para saber de dónde vienen (Instagram, Google, etc.)
    # Se almacena el dominio del referrer, no la URL completa.
    referrer = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name='Referrer',
    )
    # User-agent hash para análisis de dispositivos (móvil vs desktop)
    user_agent_hash = models.CharField(
        max_length=64,
        blank=True,
        default='',
        verbose_name='User-Agent (hash)',
    )

    class Meta:
        verbose_name = 'Vista de página'
        verbose_name_plural = 'Vistas de páginas'
        indexes = [
            models.Index(fields=['page', 'timestamp']),
            models.Index(fields=['ip_hash', 'timestamp']),
        ]
        ordering = ['-timestamp']

    def __str__(self):
        return f'{self.get_page_display()} — {self.timestamp:%Y-%m-%d %H:%M}'

    @staticmethod
    def hash_ip(ip: str) -> str:
        return hashlib.sha256(ip.encode('utf-8')).hexdigest()

    @staticmethod
    def extract_referrer_domain(referrer_url: str) -> str:
        """Extrae solo el dominio del referrer para no almacenar URLs completas."""
        if not referrer_url:
            return ''
        try:
            from urllib.parse import urlparse
            parsed = urlparse(referrer_url)
            return parsed.netloc[:100]
        except Exception:
            return ''


class PageViewMonthly(models.Model):
    """
    Agregado mensual: se crea cuando los PageView superan los 90 días.
    Permite ver tendencias históricas sin mantener millones de filas.
    """
    page = models.CharField(
        max_length=50,
        choices=VALID_PAGES,
        verbose_name='Página',
    )
    year = models.IntegerField(verbose_name='Año')
    month = models.IntegerField(verbose_name='Mes')
    total_views = models.IntegerField(default=0, verbose_name='Total vistas')
    unique_visitors = models.IntegerField(default=0, verbose_name='Visitantes únicos (IPs únicas)')

    class Meta:
        verbose_name = 'Vista mensual agregada'
        verbose_name_plural = 'Vistas mensuales agregadas'
        unique_together = ('page', 'year', 'month')
        ordering = ['-year', '-month']

    def __str__(self):
        page_label = dict(VALID_PAGES).get(self.page, self.page)
        return f'{page_label} — {self.year}/{self.month:02d}: {self.total_views} vistas'
