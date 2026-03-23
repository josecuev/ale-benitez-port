import os
from django.db import models
from PIL import Image

THUMBNAIL_MAX = (900, 900)


class Photo(models.Model):
    image = models.ImageField(upload_to='portfolio/', verbose_name='Imagen')
    thumbnail = models.ImageField(upload_to='portfolio/thumbnails/', blank=True, verbose_name='Thumbnail')
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

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.image and not self.thumbnail:
            self._generate_thumbnail()

    def _generate_thumbnail(self):
        try:
            img = Image.open(self.image.path)
            img.thumbnail(THUMBNAIL_MAX, Image.LANCZOS)

            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')

            thumb_dir = os.path.join(os.path.dirname(self.image.path), 'thumbnails')
            os.makedirs(thumb_dir, exist_ok=True)

            fname = os.path.basename(self.image.name)
            # Forzar extensión .jpg para el thumbnail
            fname_jpg = os.path.splitext(fname)[0] + '.jpg'
            thumb_path = os.path.join(thumb_dir, fname_jpg)

            img.save(thumb_path, 'JPEG', quality=85, optimize=True)

            thumb_field = f'portfolio/thumbnails/{fname_jpg}'
            Photo.objects.filter(pk=self.pk).update(thumbnail=thumb_field)
            self.thumbnail = thumb_field
        except Exception as e:
            print(f'Error generando thumbnail para {self.image.name}: {e}')
