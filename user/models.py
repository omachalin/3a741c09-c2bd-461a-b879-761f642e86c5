from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from casino.base_model import BaseModel
from main.models import Attachment
import uuid


class Currency(BaseModel):
    code = models.CharField('Код', max_length=10, unique=True)
    name = models.CharField('Наименование', max_length=50)
    balance_decimal_places = models.PositiveBigIntegerField(
        'Знаков после точки в балансе',
        default=2
    )
    payout_decimal_places  = models.PositiveBigIntegerField(
        'Знаков после точки при куше',
        default=2
    )

    icon = models.CharField('Иконка', max_length=200, null=True, blank=True)

    class Meta():
        verbose_name = 'Валюта'
        verbose_name_plural = 'Валюты'

    def __str__(self):
        return self.code


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    groups = models.ManyToManyField(
        Group,
        related_name='custom_user_set',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )

    user_permissions = models.ManyToManyField(
        Permission,
        related_name='custom_user_permissions_set',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

    avatar_fk = models.ForeignKey(
        Attachment,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='user_avatar'
    )

    updated_at = models.DateTimeField(auto_now=True)


class UserBalance(BaseModel):
    user_fk = models.ForeignKey(User, on_delete=models.CASCADE, related_name='balances')
    currency_fk = models.ForeignKey(Currency, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=20, decimal_places=12, default=0)

    class Meta:
        verbose_name = 'Баланс пользователя'
        verbose_name_plural = 'Баланс пользователей'
        unique_together = ('user_fk', 'currency_fk')

    def __str__(self):
        return f"{self.user_fk.username} — {self.currency_fk.code}: {self.amount}"
