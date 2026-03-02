import uuid
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from casino.base_model import BaseModel
from django.conf import settings
from django_minio_backend import iso_date_prefix
from casino.storages import PrivateStorage, PublicStorage


class Page(BaseModel):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    meta = models.TextField('meta', default='{}', max_length=1000)

    class Meta:
        verbose_name = 'Страница'
        verbose_name_plural = 'Страницы'

    def __str__(self):
        return self.title


class TypeMenuItem(BaseModel):
    name = models.CharField('Наименование', max_length=255)
    code = models.CharField('Код', max_length=255)

    class Meta:
        verbose_name = 'Тип меню'
        verbose_name_plural = 'Типы меню'

    def __str__(self):
        return self.name


class MenuItem(BaseModel):
    name = models.CharField('Наименование', max_length=255)
    type_menu_fk = models.ForeignKey(
        TypeMenuItem,
        verbose_name='Тип меню',
        blank=True, null=True,
        on_delete=models.CASCADE
    )
    order = models.PositiveIntegerField('Порядок', default=0)
    page_fk = models.ForeignKey(Page, verbose_name='Страница', blank=True, null=True, on_delete=models.CASCADE)
    url = models.CharField('Внешняя ссылка', max_length=500, blank=True, null=True)
    icon = models.CharField('Иконка', max_length=555, null=True, blank=True)

    class Meta:
        verbose_name = 'Пункт меню'
        verbose_name_plural = 'Меню'
        ordering = ['order']

    def __str__(self):
        return self.name


class Attachment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    file = models.FileField(
        upload_to=iso_date_prefix,
        storage=PublicStorage(),
    )

    is_public = models.BooleanField(default=True)
    filesize = models.BigIntegerField(null=True, blank=True)
    original_name = models.CharField(max_length=255, blank=True)

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.UUIDField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.file and not self.filesize:
            self.filesize = self.file.size
        if self.file and not self.original_name:
            self.original_name = self.file.name.split('/')[-1]

        if self.file:
            if self.is_public:
                self.file.storage = PublicStorage()
            else:
                self.file.storage = PrivateStorage()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.original_name}"

    class Meta:
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
        ]
        ordering = ['-created_at']