from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Currency, UserBalance
from casino.redis.client import redis_client


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'created_at')
    search_fields = ('code', 'name')

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        for key in redis_client.keys("user:*:balances"):
            redis_client.delete(key)


@admin.register(UserBalance)
class UserBalanceAdmin(admin.ModelAdmin):
    list_display = ('user_fk', 'currency_fk', 'amount', 'created_at')
    list_filter = ('currency_fk',)
    search_fields = ('user_fk__username', 'currency_fk__code')
    autocomplete_fields = ('user_fk',)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        redis_key = f"user:{obj.user_fk.id}:balances"

        import json
        current_data = redis_client.get(redis_key)

        if current_data:
            try:
                data = json.loads(current_data)
                code = obj.currency_fk.code
                if code in data:
                    data[code]['amount'] = str(obj.amount)

                    redis_client.set(redis_key, json.dumps(data))
            except Exception:
                redis_client.delete(redis_key)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    model = User
    list_display = ('username', 'email', 'date_joined', 'updated_at', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')

    readonly_fields = ('updated_at',)

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'avatar_fk')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'updated_at')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username', 'email', 'password1', 'password2', 'is_staff', 'is_active'
            )}
        ),
    )
    search_fields = ('username', 'email')
    ordering = ('username',)
    autocomplete_fields = ('avatar_fk',)
