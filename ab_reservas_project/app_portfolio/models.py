from django.db import models


class Photo(models.Model):
    image = models.ImageField(upload_to='portfolio/', verbose_name='Imagen')
    title = models.CharField(max_length=200, blank=True, verbose_name='Título')
    order = models.PositiveIntegerField(default=0, verbose_name='Orden')
    active = models.BooleanField(default=True, verbose_name='Activo')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']
        verbose_name = 'Foto'
        verbose_name_plural = 'Fotos'

    def __str__(self):
        return self.title or f'Foto #{self.order}'
