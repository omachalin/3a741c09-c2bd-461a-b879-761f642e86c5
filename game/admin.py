from django.contrib import admin
from .models import Game, GameCategory, GameConfig, ProvablyFairChain, GameHistory
from django.db import models
from casino.redis.client import redis_client
import json


@admin.register(GameHistory)
class GameHistoryAdmin(admin.ModelAdmin):
    list_display = (
        'user_fk',
        'game_fk',
        'pf_chain_fk',
        'nonce',
        'bet_amount',
        'payout',
        'game_status',
        'created_at',
    )
    search_fields = ('user_fk__username', 'game_fk__name', 'pf_chain_fk__server_seed_hash')
    ordering = ('-created_at',)
    autocomplete_fields = ('user_fk', 'game_fk', 'pf_chain_fk')


@admin.register(ProvablyFairChain)
class ProvablyFairChainAdmin(admin.ModelAdmin):
    list_display = (
        'user_fk',
        'short_server_seed_hash',
        'short_client_seed',
        'revealed_at',
        'created_at',
    )
    search_fields = (
        'user_fk__username',
        'user_fk__email',
        'server_seed_hash',
        'client_seed',
    )
    list_filter = ('revealed_at',)
    autocomplete_fields = ('user_fk',)
    ordering = ('-created_at',)

    def short_server_seed_hash(self, obj):
        return obj.server_seed_hash[:20] + '...'

    def short_client_seed(self, obj):
        return obj.client_seed[:20] + '...'

    short_server_seed_hash.short_description = 'server_seed_hash'
    short_client_seed.short_description = 'client_seed'

@admin.register(GameCategory)
class GameCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'order', 'created_at')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('order',)


class GameConfigInline(admin.TabularInline):
    model = GameConfig
    extra = 1
    fields = ('key', 'value', 'description', 'is_public')
    formfield_overrides = {
        models.TextField: {
            'widget': admin.widgets.AdminTextareaWidget(attrs={'rows': 2})
        },
    }
    verbose_name = 'Конфиг'
    verbose_name_plural = 'Конфиги игры'


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'category_fk', 'is_active', 'is_demo_available', 'order', 'created_at')
    list_filter = ('is_active', 'is_demo_available', 'category_fk')
    search_fields = ('name', 'slug')
    autocomplete_fields = ('category_fk', 'image_fk',)
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('order',)

    inlines = [GameConfigInline]

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)

        game = form.instance
        fresh_config = dict(
            game.config.filter(is_public=True).values_list('key', 'value')
        )
        redis_client.set(f'game_config:{game.code}', json.dumps(fresh_config))
