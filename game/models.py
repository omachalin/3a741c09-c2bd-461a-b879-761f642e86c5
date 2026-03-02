from django.db import models
from casino.base_model import BaseModel
from main.models import Attachment
from user.models import User, Currency
import json


class GameCategory(BaseModel):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    order = models.PositiveIntegerField('Порядок', default=0)

    class Meta():
        verbose_name = 'Категория игры'
        verbose_name_plural = 'Категории игр'
        ordering = ['order']

    def __str__(self):
        return self.name


class Game(BaseModel):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    code = models.CharField(max_length=200, db_index=True)
    category_fk = models.ForeignKey(GameCategory, on_delete=models.SET_NULL, null=True)
    image_fk = models.ForeignKey(
        Attachment,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='game_image'
    )
    # icon = models.TextField('Иконка игры', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_demo_available = models.BooleanField(default=True)
    order = models.PositiveIntegerField('Порядок', default=0)

    class Meta():
        verbose_name = 'Игра'
        verbose_name_plural = 'Игры'
        ordering = ['order']

    def __str__(self):
        return self.name


class GameConfig(BaseModel):
    game_fk = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='config')
    key = models.CharField(max_length=350)
    value = models.TextField(max_length=6000)
    is_public = models.BooleanField('Публичный ключ', default=True)
    description = models.TextField(max_length=1000)

    class Meta():
        verbose_name = 'Конфигурация игры'
        verbose_name_plural = 'Конфигурации игр'
        unique_together = ('game_fk', 'key')

    def __str__(self):
        return f"{self.game_fk.slug} → {self.key}"


class ProvablyFairChain(BaseModel):
    user_fk = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='fair_chains'
    )
    server_seed = models.CharField(max_length=128)
    server_seed_hash = models.CharField(max_length=128, db_index=True)
    client_seed = models.CharField(max_length=128, blank=True)
    revealed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Provably Fair Chain'
        verbose_name_plural = 'Provably Fair Chains'
        unique_together = ('user_fk', 'server_seed_hash')
        indexes = [
            models.Index(fields=['user_fk', '-created_at']),
            models.Index(fields=['server_seed_hash']),
        ]

    def __str__(self):
        relevated_at = 'current'
        if self.revealed_at:
            relevated_at = self.revealed_at

        return f"{self.user_fk.username} - {relevated_at}"


class GameStatus(models.TextChoices):
    ONGOING = 'ongoing', 'Ожидание'
    WIN = 'win', 'Победа'
    LOSE = 'lose', 'Проигрыш'
    DRAW = 'draw', 'Ничья'


class GameHistory(BaseModel):
    user_fk = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='user_game_history',
        db_index=True
    )

    pf_chain_fk = models.ForeignKey(
        ProvablyFairChain,
        on_delete=models.CASCADE,
        related_name='pf_chain_fk_game_history',
        db_index=True
    )

    nonce = models.BigIntegerField(
        db_index=True,
        default=0,
        help_text="Порядковый номер игры в текущей цепочке (начинается с 0)"
    )

    game_fk = models.ForeignKey(Game, on_delete=models.SET_NULL, null=True)

    currency_fk = models.ForeignKey(Currency, on_delete=models.CASCADE, help_text='Валюта')

    bet_amount = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        help_text='Сумма ставки в выбранной валюте'
    )

    payout = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        help_text="Выплата (0 если проигрыш)"
    )

    multiplier = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Множитель (например 2.00x)"
    )

    game_status = models.CharField(
        max_length=10,
        choices=GameStatus.choices,
        default=GameStatus.ONGOING,
        db_index=True
    )

    game_data = models.JSONField(
        default=dict,
        help_text="Выбор игрока, результат, стрик и т.д."
    )

    class Meta:
        verbose_name = 'История игры'
        verbose_name_plural = 'История игр'
        indexes = [
            models.Index(fields=['user_fk', '-created_at']),
            models.Index(fields=['pf_chain_fk', 'nonce']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['game_fk', '-payout']),
            models.Index(fields=['game_fk', '-multiplier']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['user_fk', 'pf_chain_fk', 'nonce'], name='unique_game_per_nonce')
        ]

    def __str__(self):
        return f"{self.user_fk.username} — {self.game_fk.id} — {self.bet_amount} → {self.payout}"
