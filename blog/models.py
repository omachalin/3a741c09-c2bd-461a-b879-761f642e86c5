from django.db import models
from casino.base_model import BaseModel
from django.conf import settings
from main.models import Attachment


class Blog(BaseModel):
    title = models.CharField('Заголовок', max_length=255)
    slug = models.SlugField('slug', unique=True)
    image_fk = models.ForeignKey(
        Attachment,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='blog_images'
    )
    content = models.TextField('Контент', max_length=5000)
    published_at = models.DateTimeField('Дата публикации')
    is_active = models.BooleanField('Опубликовано', default=False)
    author_fk = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='Автор',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='blogs'
    )

    class Meta:
        verbose_name = 'Новость'
        verbose_name_plural = 'Новости'
        ordering = ['-published_at']

    def __str__(self):
        return self.title
