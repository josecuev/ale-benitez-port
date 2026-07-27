"""
Relevamiento de uso del MCP y de las necesidades que todavía no cubre.

Dos cosas distintas, a propósito:

  UsoTool   — se llena solo, en cada llamada. Responde "qué se usa de verdad".
  Necesidad — la carga el asistente cuando algo no se puede hacer. Responde
              "qué falta". Es la que sirve para decidir el próximo desarrollo.
"""
from django.db import models


class UsoTool(models.Model):
    """Una fila por llamada. Se escribe sola, no hay que acordarse de nada."""

    tool = models.CharField(max_length=60, db_index=True, verbose_name='Herramienta')
    usuario = models.CharField(max_length=150, blank=True, default='',
                               verbose_name='Usuario')
    exito = models.BooleanField(default=True, verbose_name='Salió bien')
    detalle_error = models.TextField(blank=True, default='', verbose_name='Error')
    duracion_ms = models.PositiveIntegerField(null=True, blank=True,
                                              verbose_name='Duración (ms)')
    momento = models.DateTimeField(auto_now_add=True, db_index=True,
                                   verbose_name='Cuándo')

    class Meta:
        verbose_name = 'Uso de herramienta'
        verbose_name_plural = 'Uso de herramientas'
        ordering = ('-momento',)
        indexes = [models.Index(fields=['tool', 'momento'])]

    def __str__(self):
        return f'{self.tool} — {self.momento:%Y-%m-%d %H:%M}'


class Necesidad(models.Model):
    """
    Algo que el encargado quiso hacer y el MCP no permitió.

    Se agrupa por descripción normalizada: si la misma necesidad vuelve a
    aparecer, sube el contador en vez de duplicar la fila. Así la lista queda
    ordenada por cuánto duele de verdad, no por cuántas veces se escribió.
    """

    CATEGORIAS = [
        ('falta_tool', 'Falta una herramienta'),
        ('falta_dato', 'Falta un dato que el sistema no guarda'),
        ('friccion', 'Se puede, pero cuesta más de lo que debería'),
        ('error', 'Algo no funcionó como se esperaba'),
        ('otro', 'Otro'),
    ]

    ESTADOS = [
        ('nueva', 'Nueva'),
        ('en_analisis', 'En análisis'),
        ('planificada', 'Planificada'),
        ('implementada', 'Implementada'),
        ('descartada', 'Descartada'),
    ]

    descripcion = models.TextField(
        verbose_name='Qué necesitaba hacer',
        help_text='En palabras del encargado, no en términos técnicos.')
    clave = models.CharField(max_length=200, db_index=True, editable=False,
                             verbose_name='Clave de agrupación')
    categoria = models.CharField(max_length=20, choices=CATEGORIAS,
                                 default='falta_tool', verbose_name='Tipo')
    contexto = models.TextField(
        blank=True, default='', verbose_name='En qué estaba',
        help_text='Qué se estaba haciendo cuando apareció la necesidad.')
    tool_relacionada = models.CharField(
        max_length=60, blank=True, default='', verbose_name='Herramienta usada',
        help_text='La que se intentó usar, si hubo alguna.')
    veces = models.PositiveIntegerField(default=1, verbose_name='Veces que apareció')
    usuario = models.CharField(max_length=150, blank=True, default='',
                               verbose_name='Reportada por')
    estado = models.CharField(max_length=20, choices=ESTADOS, default='nueva',
                              db_index=True, verbose_name='Estado')
    nota_equipo = models.TextField(blank=True, default='',
                                   verbose_name='Nota del equipo')
    primera_vez = models.DateTimeField(auto_now_add=True, verbose_name='Primera vez')
    ultima_vez = models.DateTimeField(auto_now=True, verbose_name='Última vez')

    class Meta:
        verbose_name = 'Necesidad no cubierta'
        verbose_name_plural = 'Necesidades no cubiertas'
        ordering = ('-veces', '-ultima_vez')

    def __str__(self):
        return f'[{self.get_estado_display()}] {self.descripcion[:60]}'

    @staticmethod
    def normalizar(texto: str) -> str:
        """
        Clave de agrupación: minúsculas, sin acentos, sin puntuación ni espacios
        de más.

        Los acentos importan: nadie escribe dos veces la misma frase con la
        misma tilde, y sin quitarlos "pagó" y "pago" quedaban como necesidades
        distintas.
        """
        import re
        import unicodedata
        t = (texto or '').lower().strip()
        t = unicodedata.normalize('NFKD', t)
        t = ''.join(c for c in t if not unicodedata.combining(c))
        t = re.sub(r'[^\w\s]', ' ', t)
        return ' '.join(t.split())[:200]

    @classmethod
    def registrar(cls, descripcion, categoria='falta_tool', contexto='',
                  tool_relacionada='', usuario=''):
        """Crea la necesidad, o suma una aparición si ya estaba registrada."""
        clave = cls.normalizar(descripcion)
        obj = cls.objects.filter(clave=clave).first()
        if obj:
            obj.veces = models.F('veces') + 1
            if contexto and contexto not in obj.contexto:
                obj.contexto = f'{obj.contexto}\n---\n{contexto}'.strip()
            # Si ya se había cerrado y vuelve a aparecer, se reabre.
            if obj.estado in ('descartada', 'implementada'):
                obj.estado = 'nueva'
            obj.save()
            obj.refresh_from_db()
            return obj, False
        return cls.objects.create(
            descripcion=descripcion.strip(), clave=clave, categoria=categoria,
            contexto=contexto.strip(), tool_relacionada=tool_relacionada,
            usuario=usuario,
        ), True
